"""Run the official Quasar v3 artifact on the frozen common-basis inputs.

The official ``ibm_new`` parser accepts {rz, sx, x, cx}, not the original
mixed QASM gate set.  ``prepare`` therefore materializes a semantics-preserving
optimization-level-0 normalization of the same 520 circuits.  ``run`` invokes
the unmodified artifact in its isolated environment and independently checks
exact equivalence with Qiskit.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit import qasm2, transpile
from qiskit.quantum_info import Operator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import circuit_sha256
from src.provenance import file_sha256

COMMON_BASIS = ["rz", "sx", "x", "cx"]
DEFAULT_ROOT = PROJECT_ROOT / "data" / "v10" / "prepaper" / "external_baselines" / "quasar"
ARTIFACT_DIR = DEFAULT_ROOT / "quasar-artifact"
ARTIFACT_PYTHON = ARTIFACT_DIR / ".venv" / "Scripts" / "python.exe"
ENTRY = ARTIFACT_DIR / "seq-eg" / "entry.py"
PROTOCOL_PATH = PROJECT_ROOT / "experiments" / "prepaper_protocol.json"


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    # Windows can briefly deny ReplaceFile/MoveFileEx while a read-only audit
    # process still holds the destination.  Preserve atomicity and retry only
    # that sharing failure; all other exceptions remain fail-fast.
    for attempt in range(10):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.05 * (2 ** attempt))


def _metrics(circuit) -> dict:
    return {
        "gate_count": int(circuit.size()),
        "two_q_count": int(sum(inst.operation.num_qubits == 2 for inst in circuit.data)),
        "depth": int(circuit.depth() or 0),
    }


def _terminate_process_tree(proc: subprocess.Popen) -> str:
    """Terminate exactly one artifact process tree after an outer timeout."""
    if proc.poll() is not None:
        return "already_exited"
    if os.name == "nt":
        cleanup = subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            text=True, capture_output=True, timeout=30,
        )
        return (f"taskkill_returncode={cleanup.returncode}; "
                f"stdout={cleanup.stdout[-500:]}; stderr={cleanup.stderr[-500:]}")
    proc.kill()
    return "proc.kill"


def prepare(source_manifest: Path, output_root: Path) -> Path:
    source = pd.read_csv(source_manifest.resolve())
    input_dir = output_root / "shared_520" / "inputs"
    qasm_dir = input_dir / "qasm"
    qasm_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for row in source.to_dict(orient="records"):
        source_qasm = PROJECT_ROOT / str(row["qasm_path"])
        circuit = qasm2.loads(source_qasm.read_text(encoding="utf-8"),
                              custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
        common = transpile(
            circuit, basis_gates=COMMON_BASIS, optimization_level=0,
            seed_transpiler=int(row["seed"]),
        )
        common_sha = circuit_sha256(common)
        path = qasm_dir / f"{row['circuit_id']}_t{int(row['trial']):02d}_{common_sha[:12]}.qasm"
        _atomic_text(path, qasm2.dumps(common))
        rows.append({
            **row,
            "original_manifest_sha256": file_sha256(source_manifest.resolve()),
            "original_input_circuit_sha256": row["input_circuit_sha256"],
            "input_circuit_sha256": common_sha,
            "qasm_path": path.relative_to(PROJECT_ROOT).as_posix(),
            "qasm_sha256": file_sha256(path),
            "normalization_basis": ",".join(COMMON_BASIS),
            "normalization_optimization_level": 0,
        })
    manifest = pd.DataFrame(rows)
    if len(manifest) != 520 or manifest.duplicated(
        ["circuit_id", "trial", "seed", "input_circuit_sha256"]
    ).any():
        raise RuntimeError("Quasar common-input manifest integrity failure")
    path = input_dir / "benchmark_manifest.csv"
    _atomic_text(path, manifest.to_csv(index=False))
    metadata = {
        "status": "prepared_common_basis_inputs",
        "n_rows": len(manifest), "basis": COMMON_BASIS,
        "source_manifest_sha256": file_sha256(source_manifest.resolve()),
        "manifest_sha256": file_sha256(path),
        "source_sha256": file_sha256(Path(__file__).resolve()),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
    }
    _atomic_text(input_dir / "metadata.json", json.dumps(metadata, indent=2, sort_keys=True))
    print(f"Prepared Quasar common-basis manifest: {len(manifest)} -> {path}")
    return path


def _run_one(row: dict, output_root: Path, timeout_seconds: float) -> dict:
    circuit_id = str(row["circuit_id"])
    trial = int(row["trial"])
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in circuit_id)
    run_dir = output_root / "shared_520" / "outputs" / f"t{trial:02d}_{safe}"
    run_dir.mkdir(parents=True, exist_ok=True)
    input_path = PROJECT_ROOT / str(row["qasm_path"])
    output_path = run_dir / "optimized.qasm"
    tmp_path = run_dir / "working.qasm"
    timeline_path = run_dir / "timeline.csv"
    # A formal attempt must never consume an output left by an invalidated or
    # timed-out attempt using the same deterministic directory.
    output_path.unlink(missing_ok=True)
    tmp_path.unlink(missing_ok=True)
    timeline_path.unlink(missing_ok=True)
    command = [
        str(ARTIFACT_PYTHON), str(ENTRY),
        "--init", str(input_path), "--final", str(output_path),
        "--tmp", str(tmp_path), "--timeline-csv", str(timeline_path),
        "--step", "8", "--iters", "3", "--max-step", "8",
        "--no-escalate", "--no-ilp", "--time-limit", str(timeout_seconds),
    ]
    start = time.perf_counter()
    child_env = os.environ.copy()
    # Prevent nested BLAS thread pools from turning executor-level concurrency
    # into resource-dependent failures.  This changes scheduling only, not the
    # optimizer, search budget, or input circuit.
    child_env.update({
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    })
    proc = subprocess.Popen(
        command, cwd=ARTIFACT_DIR, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=child_env,
    )
    returncode: int | None = None
    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds + 20)
        elapsed = time.perf_counter() - start
        returncode = proc.returncode
        status = "ok" if returncode == 0 and output_path.exists() else "error"
        error = "" if status == "ok" else (stderr or stdout)[-2000:]
        stdout_tail = stdout[-2000:]
    except subprocess.TimeoutExpired as exc:
        cleanup = _terminate_process_tree(proc)
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", ""
        elapsed = time.perf_counter() - start
        returncode = proc.returncode
        status = "outer_timeout"
        error = f"{exc}; process_tree_cleanup={cleanup}"
        stdout_tail = (stdout or "")[-2000:]

    result = {
        "tool": "quasar_seq_eg", "tool_config": "step8_iters3_noilp",
        "circuit_id": circuit_id, "circuit_family": str(row["circuit_family"]),
        "trial": trial, "seed": int(row["seed"]),
        "source_manifest_sha256": str(row["original_manifest_sha256"]),
        "input_circuit_sha256": str(row["input_circuit_sha256"]),
        "status": status, "returncode": returncode,
        "runtime_seconds": elapsed,
        "internal_budget_exhausted": "[timeout]" in stdout_tail,
        "error": error, "stdout_tail": stdout_tail,
        "output_qasm_path": output_path.relative_to(PROJECT_ROOT).as_posix() if output_path.exists() else "",
        "output_qasm_sha256": file_sha256(output_path) if output_path.exists() else "",
        "exact_equivalent": False, "fidelity_source": "unavailable",
        "valid_equivalent_output": False,
        "analysis_gate_reduction_pct_itt": 0.0,
    }
    try:
        original = qasm2.loads(input_path.read_text(encoding="utf-8"),
                               custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
        orig_m = _metrics(original)
        result.update({f"input_{k}": v for k, v in orig_m.items()})
        if status == "ok":
            optimized = qasm2.loads(output_path.read_text(encoding="utf-8"),
                                    custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
            opt_m = _metrics(optimized)
            result.update({f"output_{k}": v for k, v in opt_m.items()})
            equivalent = bool(Operator(original).equiv(Operator(optimized)))
            reduction = 100.0 * (1.0 - opt_m["gate_count"] / orig_m["gate_count"])
            result.update({
                "exact_equivalent": equivalent, "fidelity_source": "exact",
                "valid_equivalent_output": equivalent,
                "gate_reduction_pct": reduction,
                "analysis_gate_reduction_pct_itt": reduction if equivalent else 0.0,
            })
    except Exception as exc:
        result["verification_error"] = f"{type(exc).__name__}: {exc}"
    return result


def run(manifest_path: Path, output_root: Path, workers: int, timeout_seconds: float) -> Path:
    if not ARTIFACT_PYTHON.exists() or not ENTRY.exists():
        raise RuntimeError("Quasar artifact environment is not installed")
    manifest_path = manifest_path.resolve()
    manifest = pd.read_csv(manifest_path)
    if len(manifest) != 520:
        raise RuntimeError("Quasar confirmatory manifest must contain 520 rows")
    run_root = output_root / "shared_520"
    checkpoint = run_root / "quasar_checkpoint.csv"
    rows = pd.read_csv(checkpoint).to_dict(orient="records") if checkpoint.exists() else []
    completed = {(r["circuit_id"], int(r["trial"]), int(r["seed"])) for r in rows}
    pending = [r for r in manifest.to_dict(orient="records")
               if (r["circuit_id"], int(r["trial"]), int(r["seed"])) not in completed]
    if workers == 1:
        # The confirmatory contract is single-worker.  Do not pre-submit every
        # input: if an atomic checkpoint ever fails, the process must stop
        # immediately instead of silently running uncheckpointed futures while
        # ThreadPoolExecutor waits during exception unwinding.
        for row in pending:
            rows.append(_run_one(row, output_root, timeout_seconds))
            _atomic_text(checkpoint, pd.DataFrame(rows).to_csv(index=False))
            if len(rows) % 10 == 0:
                print(f"Quasar checkpoint: {len(rows)}/520", flush=True)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_run_one, row, output_root, timeout_seconds): row
                for row in pending
            }
            for future in concurrent.futures.as_completed(futures):
                rows.append(future.result())
                _atomic_text(checkpoint, pd.DataFrame(rows).to_csv(index=False))
                if len(rows) % 10 == 0:
                    print(f"Quasar checkpoint: {len(rows)}/520", flush=True)
    frame = pd.DataFrame(rows).sort_values(["trial", "circuit_family", "circuit_id"])
    if len(frame) != 520 or frame.duplicated(["circuit_id", "trial", "seed"]).any():
        raise RuntimeError("Quasar result key integrity failure")
    output = run_root / "quasar_shared_520.csv"
    _atomic_text(output, frame.to_csv(index=False))
    checkpoint.unlink(missing_ok=True)
    metadata = {
        "status": "complete", "n_rows": len(frame), "workers": workers,
        "blas_threads_per_worker": 1,
        "timeout_seconds": timeout_seconds, "step": 8, "iters": 3,
        "max_step": 8, "escalate": False, "ilp": False,
        "manifest_sha256": file_sha256(manifest_path),
        "result_sha256": file_sha256(output),
        "artifact_archive_md5": "ff3a49973c97316bca0fb2d347ea5478",
        "artifact_record": "https://zenodo.org/records/19571754",
        "source_sha256": file_sha256(Path(__file__).resolve()),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "n_valid_equivalent_outputs": int(frame.valid_equivalent_output.astype(bool).sum()),
        "n_outer_timeouts": int((frame.status == "outer_timeout").sum()),
    }
    segments = run_root / "execution_segments.json"
    if segments.exists():
        metadata["execution_segments_sha256"] = file_sha256(segments)
    _atomic_text(run_root / "metadata.json", json.dumps(metadata, indent=2, sort_keys=True))
    print(f"Quasar complete: {len(frame)} -> {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["prepare", "run"], required=True)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    if args.phase == "prepare":
        if args.source_manifest is None:
            parser.error("prepare requires --source-manifest")
        prepare(args.source_manifest, args.output_root.resolve())
    else:
        if args.manifest is None:
            parser.error("run requires --manifest")
        run(args.manifest, args.output_root.resolve(), args.workers, args.timeout)


if __name__ == "__main__":
    main()
