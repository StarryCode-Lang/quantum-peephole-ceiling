"""Isolated, checkpointed Quartz benchmark on the frozen 520 logical inputs.

The official Quartz optimizer accepts the Nam basis {rz, h, x, cx}.  ``prepare``
performs a semantics-checked, optimization-level-0 basis conversion from the
already frozen Quasar/common-basis manifest.  ``run`` invokes a thin I/O adapter
around Quartz's unmodified ``Graph::optimize`` search and evaluates outputs in
the original common analysis basis {rz, sx, x, cx} with exact equivalence.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
from qiskit import qasm2, transpile
from qiskit.quantum_info import Operator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_ROOT = (PROJECT_ROOT / "data" / "v10" / "prepaper" /
                "external_baselines" / "quartz")
PROTOCOL_PATH = PROJECT_ROOT / "experiments" / "prepaper_protocol.json"
NAM_BASIS = ["rz", "h", "x", "cx"]
COMMON_BASIS = ["rz", "sx", "x", "cx"]

from src.provenance import file_sha256


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    for attempt in range(10):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.05 * (2 ** attempt))


def _metrics(circuit) -> dict[str, int]:
    return {
        "gate_count": int(circuit.size()),
        "two_qubit_gate_count": int(sum(
            instruction.operation.num_qubits == 2 for instruction in circuit.data
        )),
        "depth": int(circuit.depth() or 0),
    }


def _load_qasm(path: Path):
    return qasm2.loads(path.read_text(encoding="utf-8"),
                       custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)


def prepare(source_manifest: Path, output_root: Path) -> Path:
    source_manifest = source_manifest.resolve()
    source = pd.read_csv(source_manifest)
    if len(source) != 520 or source.duplicated(
            ["circuit_id", "trial", "seed", "input_circuit_sha256"]).any():
        raise RuntimeError("source common-basis manifest integrity failure")
    input_dir = output_root / "shared_520" / "inputs"
    qasm_dir = input_dir / "qasm"
    qasm_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for row in source.to_dict(orient="records"):
        source_path = PROJECT_ROOT / str(row["qasm_path"])
        logical = _load_qasm(source_path)
        normalized = transpile(
            logical, basis_gates=NAM_BASIS, optimization_level=0,
            seed_transpiler=0,
        )
        if not Operator(logical).equiv(Operator(normalized)):
            raise RuntimeError(f"Nam-basis conversion changed {row['circuit_id']}")
        qasm_text = qasm2.dumps(normalized)
        name = (f"{row['circuit_id']}_t{int(row['trial']):02d}_"
                f"{str(row['input_circuit_sha256'])[:12]}.qasm")
        path = qasm_dir / name
        _atomic_text(path, qasm_text)
        record = dict(row)
        record.update({
            "source_common_manifest_sha256": file_sha256(source_manifest),
            "source_common_qasm_sha256": file_sha256(source_path),
            "source_common_qasm_path": source_path.relative_to(PROJECT_ROOT).as_posix(),
            "quartz_input_qasm_sha256": file_sha256(path),
            "quartz_input_qasm_path": path.relative_to(PROJECT_ROOT).as_posix(),
            "quartz_basis": ",".join(NAM_BASIS),
            "basis_conversion_optimization_level": 0,
            "basis_conversion_exact_equivalent": True,
        })
        rows.append(record)
    manifest = pd.DataFrame(rows)
    path = input_dir / "benchmark_manifest.csv"
    _atomic_text(path, manifest.to_csv(index=False))
    metadata = {
        "status": "prepared", "n_rows": len(manifest),
        "logical_source": "frozen Quasar/common-basis 520 manifest",
        "source_manifest_sha256": file_sha256(source_manifest),
        "manifest_sha256": file_sha256(path),
        "quartz_basis": NAM_BASIS, "analysis_basis": COMMON_BASIS,
        "basis_conversion_optimization_level": 0,
        "source_sha256": file_sha256(Path(__file__).resolve()),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
    }
    _atomic_text(input_dir / "metadata.json",
                 json.dumps(metadata, indent=2, sort_keys=True))
    print(f"Prepared Quartz manifest: {len(manifest)} -> {path}")
    return path


def _run_one(row: dict, output_root: Path, executable: Path, eqset: Path,
             timeout_seconds: float, runtime_python_dir: Path) -> dict:
    circuit_id = str(row["circuit_id"])
    trial = int(row["trial"])
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_"
                   for ch in circuit_id)
    run_dir = output_root / "shared_520" / "outputs" / f"t{trial:02d}_{safe}"
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / "optimized.qasm"
    output_path.unlink(missing_ok=True)
    input_path = PROJECT_ROOT / str(row["quartz_input_qasm_path"])
    command = [str(executable), input_path.as_posix(), circuit_id,
               eqset.as_posix(), output_path.as_posix()]
    child_env = os.environ.copy()
    child_env.update({
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
    })
    child_env["PATH"] = str(runtime_python_dir) + os.pathsep + child_env.get("PATH", "")
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            command, cwd=executable.parent, text=True, capture_output=True,
            timeout=timeout_seconds, env=child_env,
        )
        elapsed = time.perf_counter() - start
        status = "ok" if proc.returncode == 0 and output_path.exists() else "error"
        error = "" if status == "ok" else (proc.stderr or proc.stdout)[-2000:]
        stdout_tail = proc.stdout[-2000:]
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - start
        status, error, stdout_tail = "timeout", str(exc), ""

    result = {
        "tool": "quartz_graph_optimize", "tool_config": "nam_5_3_default_search",
        "circuit_id": circuit_id, "circuit_family": str(row["circuit_family"]),
        "trial": trial, "seed": int(row["seed"]),
        "source_common_manifest_sha256": str(row["source_common_manifest_sha256"]),
        "source_common_input_circuit_sha256": str(row["input_circuit_sha256"]),
        "quartz_input_qasm_sha256": str(row["quartz_input_qasm_sha256"]),
        "status": status, "runtime_seconds": elapsed, "error": error,
        "stdout_tail": stdout_tail,
        "output_qasm_path": (output_path.relative_to(PROJECT_ROOT).as_posix()
                             if output_path.exists() else ""),
        "output_qasm_sha256": file_sha256(output_path) if output_path.exists() else "",
        "exact_equivalent": False, "fidelity_source": "unavailable",
        "valid_equivalent_output": False,
        "analysis_common_gate_reduction_pct_itt": 0.0,
        "analysis_common_two_qubit_reduction_pct_itt": 0.0,
        "analysis_common_depth_reduction_pct_itt": 0.0,
    }
    try:
        source_common = _load_qasm(PROJECT_ROOT / str(row["source_common_qasm_path"]))
        quartz_input = _load_qasm(input_path)
        result.update({f"quartz_input_{k}": v for k, v in _metrics(quartz_input).items()})
        common_input_metrics = _metrics(source_common)
        result.update({f"analysis_common_input_{k}": v
                       for k, v in common_input_metrics.items()})
        if status == "ok":
            optimized = _load_qasm(output_path)
            result.update({f"quartz_output_{k}": v for k, v in _metrics(optimized).items()})
            equivalent = bool(Operator(source_common).equiv(Operator(optimized)))
            common_output = transpile(
                optimized, basis_gates=COMMON_BASIS, optimization_level=0,
                seed_transpiler=0,
            )
            common_output_metrics = _metrics(common_output)
            result.update({f"analysis_common_output_{k}": v
                           for k, v in common_output_metrics.items()})
            reductions = {
                metric: 100.0 * (1.0 - common_output_metrics[metric]
                                 / common_input_metrics[metric])
                if common_input_metrics[metric] else 0.0
                for metric in ("gate_count", "two_qubit_gate_count", "depth")
            }
            result.update({
                "exact_equivalent": equivalent,
                "fidelity_source": "exact",
                "valid_equivalent_output": equivalent,
                "analysis_common_gate_reduction_pct": reductions["gate_count"],
                "analysis_common_two_qubit_reduction_pct": reductions["two_qubit_gate_count"],
                "analysis_common_depth_reduction_pct": reductions["depth"],
                "analysis_common_gate_reduction_pct_itt": reductions["gate_count"] if equivalent else 0.0,
                "analysis_common_two_qubit_reduction_pct_itt": reductions["two_qubit_gate_count"] if equivalent else 0.0,
                "analysis_common_depth_reduction_pct_itt": reductions["depth"] if equivalent else 0.0,
            })
    except Exception as exc:
        result["verification_error"] = f"{type(exc).__name__}: {exc}"
    return result


def run(manifest_path: Path, output_root: Path, executable: Path, eqset: Path,
        workers: int, timeout_seconds: float, artifact_commit: str,
        adapter_patch: Path, runtime_python_dir: Path) -> Path:
    manifest_path = manifest_path.resolve()
    executable, eqset = executable.resolve(), eqset.resolve()
    runtime_python_dir = runtime_python_dir.resolve()
    runtime_python_dll = runtime_python_dir / "python311.dll"
    if not executable.exists() or not eqset.exists() or not runtime_python_dll.exists():
        raise RuntimeError("Quartz executable, ECC set, or Python runtime DLL missing")
    manifest = pd.read_csv(manifest_path)
    key = ["circuit_id", "trial", "seed", "quartz_input_qasm_sha256"]
    if len(manifest) != 520 or manifest.duplicated(key).any():
        raise RuntimeError("Quartz confirmatory manifest integrity failure")
    run_root = output_root / "shared_520"
    checkpoint = run_root / "quartz_checkpoint.csv"
    rows = pd.read_csv(checkpoint).to_dict(orient="records") if checkpoint.exists() else []
    completed = {(r["circuit_id"], int(r["trial"]), int(r["seed"]),
                  r["quartz_input_qasm_sha256"]) for r in rows}
    pending = [r for r in manifest.to_dict(orient="records")
               if (r["circuit_id"], int(r["trial"]), int(r["seed"]),
                   r["quartz_input_qasm_sha256"]) not in completed]
    if workers == 1:
        for row in pending:
            rows.append(_run_one(row, output_root, executable, eqset,
                                 timeout_seconds, runtime_python_dir))
            _atomic_text(checkpoint, pd.DataFrame(rows).to_csv(index=False))
            if len(rows) % 10 == 0:
                print(f"Quartz checkpoint: {len(rows)}/520", flush=True)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_run_one, row, output_root, executable, eqset,
                            timeout_seconds, runtime_python_dir): row
                for row in pending
            }
            for future in concurrent.futures.as_completed(futures):
                rows.append(future.result())
                _atomic_text(checkpoint, pd.DataFrame(rows).to_csv(index=False))
                if len(rows) % 10 == 0:
                    print(f"Quartz checkpoint: {len(rows)}/520", flush=True)
    frame = pd.DataFrame(rows).sort_values(["trial", "circuit_family", "circuit_id"])
    if len(frame) != 520 or frame.duplicated(key).any():
        raise RuntimeError("Quartz result key integrity failure")
    output = run_root / "quartz_shared_520.csv"
    _atomic_text(output, frame.to_csv(index=False))
    checkpoint.unlink(missing_ok=True)
    metadata = {
        "status": "complete", "n_rows": len(frame), "workers": workers,
        "timeout_seconds": timeout_seconds, "blas_threads_per_worker": 1,
        "manifest_sha256": file_sha256(manifest_path),
        "result_sha256": file_sha256(output),
        "artifact_commit": artifact_commit,
        "eqset_sha256": file_sha256(eqset),
        "adapter_patch_sha256": file_sha256(adapter_patch.resolve()),
        "executable_sha256": file_sha256(executable),
        "runtime_python_dir": str(runtime_python_dir),
        "runtime_python_dll_sha256": file_sha256(runtime_python_dll),
        "source_sha256": file_sha256(Path(__file__).resolve()),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "n_valid_equivalent_outputs": int(
            frame.valid_equivalent_output.astype(str).str.lower().eq("true").sum()),
        "n_timeouts": int((frame.status == "timeout").sum()),
    }
    segments = run_root / "execution_segments.json"
    if segments.exists():
        metadata["execution_segments_sha256"] = file_sha256(segments)
    _atomic_text(run_root / "metadata.json",
                 json.dumps(metadata, indent=2, sort_keys=True))
    print(f"Quartz complete: {len(frame)} -> {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["prepare", "run"], required=True)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--eqset", type=Path)
    parser.add_argument("--adapter-patch", type=Path)
    parser.add_argument("--runtime-python-dir", type=Path)
    parser.add_argument("--artifact-commit", default="c4abf876608b111b2900d59a3c4efd7982063c20")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    if args.phase == "prepare":
        if args.source_manifest is None:
            parser.error("prepare requires --source-manifest")
        prepare(args.source_manifest, args.output_root.resolve())
    else:
        required = (args.manifest, args.executable, args.eqset, args.adapter_patch,
                    args.runtime_python_dir)
        if any(value is None for value in required):
            parser.error("run requires manifest, executable, eqset, and adapter-patch")
        run(args.manifest, args.output_root.resolve(), args.executable,
            args.eqset, args.workers, args.timeout, args.artifact_commit,
            args.adapter_patch, args.runtime_python_dir)


if __name__ == "__main__":
    main()
