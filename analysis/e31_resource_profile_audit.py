"""Run and audit a bounded, non-confirmatory E31 resource profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import psutil

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DESIGN = ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv"
PROTOCOL = ROOT / "experiments/e31_factorial_pareto_protocol.json"
WORKER = ROOT / "experiments/e31_resource_profile_worker.py"
DEFAULT_OUTPUT_DIR = (
    ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _directory_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def select_profile_cells(design: pd.DataFrame) -> pd.DataFrame:
    units = (
        design.sort_values(["circuit_family", "n_qubits", "circuit_id"])
        .drop_duplicates("input_circuit_sha256")
    )
    family_inputs = units.drop_duplicates("circuit_family")
    family_hashes = set(family_inputs["input_circuit_sha256"])
    family_panel = design[
        design["input_circuit_sha256"].isin(family_hashes)
        & design["listing_model"].isin(["LBL", "WCL"])
        & design["rule_set"].eq("COMMUTATION_PLUS_TEMPLATES")
        & design["window_gates"].eq(16)
        & design["budget_seconds"].eq(10)
    ]
    scale_inputs = (
        units.sort_values(["n_qubits", "circuit_id"])
        .drop_duplicates("n_qubits")
    )
    scale_panel = design[
        design["input_circuit_sha256"].isin(set(scale_inputs["input_circuit_sha256"]))
        & design["listing_model"].eq("LBL")
        & design["rule_set"].eq("COMMUTATION_PLUS_TEMPLATES")
        & design["window_gates"].eq(16)
        & design["budget_seconds"].eq(10)
    ]
    panel = pd.concat([family_panel, scale_panel], ignore_index=True).drop_duplicates("run_id")
    if family_panel["circuit_family"].nunique() != 15:
        raise ValueError("resource profile does not cover all 15 families")
    if set(scale_panel["n_qubits"]) != set(range(4, 11)):
        raise ValueError("resource profile does not cover qubits 4 through 10")
    return panel.sort_values(["n_qubits", "circuit_family", "listing_model"]).reset_index(drop=True)


def _payload(row: pd.Series, protocol: dict) -> dict:
    return {
        **row.to_dict(),
        "fidelity_threshold": protocol["semantic_contract"]["fidelity_threshold"],
        "common_basis": protocol["semantic_contract"]["common_basis"],
    }


def run_profile_cell(
    row: pd.Series,
    protocol: dict,
    output_dir: Path,
    label: str,
    repeats: int = 1,
    timeout_seconds: float = 30.0,
) -> list[dict]:
    cell_dir = output_dir / "raw" / label / str(row.run_id)
    cell_dir.mkdir(parents=True, exist_ok=True)
    payload_path = cell_dir / "payload.json"
    result_path = cell_dir / "result.json"
    payload_path.write_text(
        json.dumps(_payload(row, protocol), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    result_path.unlink(missing_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "RAYON_NUM_THREADS": "1",
        }
    )
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    start = time.perf_counter()
    process = subprocess.Popen(
        [
            sys.executable,
            str(WORKER),
            "--payload",
            str(payload_path),
            "--result",
            str(result_path),
            "--repeats",
            str(repeats),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        creationflags=creationflags,
    )
    peak_rss = 0
    while process.poll() is None:
        if time.perf_counter() - start > timeout_seconds:
            try:
                parent = psutil.Process(process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except psutil.Error:
                pass
            raise TimeoutError(f"profile cell timed out: {row.run_id}")
        try:
            tree = [psutil.Process(process.pid)] + psutil.Process(process.pid).children(recursive=True)
            peak_rss = max(
                peak_rss,
                sum(item.memory_info().rss for item in tree if item.is_running()),
            )
        except psutil.Error:
            pass
        time.sleep(0.01)
    stdout, stderr = process.communicate(timeout=5)
    wall = time.perf_counter() - start
    (cell_dir / "stdout.log").write_text(stdout, encoding="utf-8")
    (cell_dir / "stderr.log").write_text(stderr, encoding="utf-8")
    if process.returncode != 0 or not result_path.is_file():
        raise RuntimeError(f"profile worker failed: {row.run_id}: {stderr}")
    packet = json.loads(result_path.read_text(encoding="utf-8"))
    if packet.get("status") != "RESOURCE_PROFILE_NONCONFIRMATORY":
        raise RuntimeError("profile worker returned an unexpected status")
    directory_bytes = _directory_bytes(cell_dir)
    rows = []
    for repetition in packet["repetitions"]:
        phase_wall = repetition["phase_wall_seconds"]
        phase_cpu = repetition["phase_cpu_seconds"]
        rows.append(
            {
                "profile_label": label,
                "run_id": row.run_id,
                "circuit_id": row.circuit_id,
                "circuit_family": row.circuit_family,
                "n_qubits": int(row.n_qubits),
                "input_circuit_sha256": row.input_circuit_sha256,
                "listing_model": row.listing_model,
                "rule_set": row.rule_set,
                "window_gates": int(row.window_gates),
                "budget_seconds": int(row.budget_seconds),
                "repeat_index": int(repetition["repeat_index"]),
                "status": repetition["status"],
                "valid_equivalent_output": bool(repetition["valid_equivalent_output"]),
                "output_circuit_sha256": repetition["output_circuit_sha256"],
                "original_common_basis_gate_count": int(
                    repetition["original_common_basis_gate_count"]
                ),
                "optimized_common_basis_gate_count": int(
                    repetition["optimized_common_basis_gate_count"]
                ),
                "common_basis_gate_reduction_pct": float(
                    repetition["common_basis_gate_reduction_pct"]
                ),
                "process_wall_seconds": float(wall),
                "execute_wall_seconds": float(repetition["execute_wall_seconds"]),
                "execute_cpu_seconds": float(repetition["execute_cpu_seconds"]),
                "import_initialization_wall_seconds": float(
                    packet["import_initialization_wall_seconds"]
                ),
                "import_initialization_cpu_seconds": float(
                    packet["import_initialization_cpu_seconds"]
                ),
                "payload_parsing_wall_seconds": float(packet["payload_parsing_wall_seconds"]),
                "payload_parsing_cpu_seconds": float(packet["payload_parsing_cpu_seconds"]),
                "qasm_parsing_wall_seconds": float(phase_wall["qasm_parsing"]),
                "qasm_parsing_cpu_seconds": float(phase_cpu["qasm_parsing"]),
                "listing_wall_seconds": float(phase_wall["listing"]),
                "listing_cpu_seconds": float(phase_cpu["listing"]),
                "engine_initialization_wall_seconds": float(
                    phase_wall["engine_initialization"]
                ),
                "engine_initialization_cpu_seconds": float(
                    phase_cpu["engine_initialization"]
                ),
                "optimization_wall_seconds": float(phase_wall["optimization"]),
                "optimization_cpu_seconds": float(phase_cpu["optimization"]),
                "verification_wall_seconds": float(phase_wall["exact_verification"]),
                "verification_cpu_seconds": float(phase_cpu["exact_verification"]),
                "basis_conversion_wall_seconds": float(phase_wall["basis_conversion"]),
                "basis_conversion_cpu_seconds": float(phase_cpu["basis_conversion"]),
                "serialization_probe_wall_seconds": float(
                    repetition["serialization_probe_wall_seconds"]
                ),
                "serialization_probe_cpu_seconds": float(
                    repetition["serialization_probe_cpu_seconds"]
                ),
                "peak_rss_mb": float(peak_rss / (1024 * 1024)),
                "phase_boundary_peak_rss_mb": float(
                    repetition["phase_boundary_peak_rss_bytes"] / (1024 * 1024)
                ),
                "process_disk_read_bytes": int(packet["process_disk_read_bytes"]),
                "process_disk_write_bytes_before_result": int(
                    packet["process_disk_write_bytes_before_result"]
                ),
                "final_profile_directory_bytes": int(directory_bytes),
            }
        )
    return rows


def _memory_scaling(panel: pd.DataFrame, replicates: int = 2000) -> dict:
    scale = panel[
        panel["profile_label"].eq("main")
        & panel["listing_model"].eq("LBL")
    ].sort_values("n_qubits").drop_duplicates("n_qubits")
    if set(scale.n_qubits) != set(range(4, 11)):
        raise ValueError("memory scaling panel lacks qubits 4 through 10")
    x = np.log(scale.n_qubits.to_numpy(dtype=float))
    y = np.log(scale.peak_rss_mb.to_numpy(dtype=float))
    slope = float(np.polyfit(x, y, 1)[0])
    rng = np.random.default_rng(20260829)
    slopes = []
    for _ in range(replicates):
        take = rng.integers(0, len(scale), len(scale))
        if len(np.unique(x[take])) < 2:
            continue
        slopes.append(float(np.polyfit(x[take], y[take], 1)[0]))
    low, high = np.percentile(slopes, [2.5, 97.5])
    return {
        "model": "log(peak_RSS_MB) = intercept + exponent * log(n_qubits)",
        "n_scale_points": int(len(scale)),
        "qubit_range": [4, 10],
        "exponent": slope,
        "bootstrap_replicates_finite": int(len(slopes)),
        "bootstrap_ci95": [float(low), float(high)],
        "limitation": "diagnostic worker RSS includes Python/Qiskit interpreter overhead",
    }


def build_audit(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict:
    design = pd.read_csv(DESIGN)
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    panel = select_profile_cells(design)
    output_dir.mkdir(parents=True, exist_ok=True)
    main_rows = []
    for _, row in panel.iterrows():
        main_rows.extend(run_profile_cell(row, protocol, output_dir, "main"))
    main = pd.DataFrame(main_rows)
    if not main.valid_equivalent_output.all():
        raise ValueError("resource profile contains a non-equivalent output")

    sensitivity_source = panel.head(8).copy()
    worker_rows = []
    for workers in (1, 2, 4):
        started = time.perf_counter()
        outputs = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    run_profile_cell,
                    row,
                    protocol,
                    output_dir,
                    f"workers_{workers}",
                )
                for _, row in sensitivity_source.iterrows()
            ]
            for future in as_completed(futures):
                outputs.extend(future.result())
        elapsed = time.perf_counter() - started
        worker_frame = pd.DataFrame(outputs)
        if not worker_frame.valid_equivalent_output.all():
            raise ValueError("worker sensitivity contains invalid output")
        worker_rows.append(
            {
                "workers": workers,
                "tasks": int(len(worker_frame)),
                "batch_wall_seconds": float(elapsed),
                "throughput_tasks_per_second": float(len(worker_frame) / elapsed),
                "median_task_process_wall_seconds": float(
                    worker_frame.process_wall_seconds.median()
                ),
                "peak_task_rss_mb": float(worker_frame.peak_rss_mb.max()),
                "output_hash_set_sha256": hashlib.sha256(
                    "\n".join(sorted(worker_frame.output_circuit_sha256)).encode("utf-8")
                ).hexdigest(),
            }
        )
    workers = pd.DataFrame(worker_rows)
    if workers.output_hash_set_sha256.nunique() != 1:
        raise ValueError("worker count changed deterministic output hashes")

    cache_source = panel.iloc[0]
    cache = pd.DataFrame(
        run_profile_cell(
            cache_source,
            protocol,
            output_dir,
            "same_process_repeats",
            repeats=5,
            timeout_seconds=60,
        )
    )
    if cache.output_circuit_sha256.nunique() != 1:
        raise ValueError("same-process repetitions changed output hash")

    main_path = output_dir / "resource_profile_cells.csv"
    workers_path = output_dir / "worker_sensitivity.csv"
    cache_path = output_dir / "same_process_cache_repeats.csv"
    main.to_csv(main_path, index=False)
    workers.to_csv(workers_path, index=False)
    cache.to_csv(cache_path, index=False)
    numeric_required = [
        "execute_cpu_seconds",
        "process_disk_read_bytes",
        "process_disk_write_bytes_before_result",
        "final_profile_directory_bytes",
        "import_initialization_wall_seconds",
        "qasm_parsing_wall_seconds",
        "basis_conversion_wall_seconds",
        "verification_wall_seconds",
        "serialization_probe_wall_seconds",
        "peak_rss_mb",
    ]
    if not np.isfinite(main[numeric_required].to_numpy(dtype=float)).all():
        raise ValueError("resource profile contains non-finite measurements")
    memory = _memory_scaling(main)
    cache_first = float(cache.iloc[0].execute_wall_seconds)
    cache_warm = float(cache.iloc[1:].execute_wall_seconds.median())
    report = {
        "schema_version": "1.0.0",
        "status": "PASS_BOUNDED_E31_RESOURCE_PROFILE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "non-confirmatory diagnostic panel; 15 families, qubits 4-10, fixed 10-second design cells",
        "source_bindings": {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in (DESIGN, PROTOCOL, WORKER, Path(__file__).resolve())
        },
        "main_panel": {
            "rows": int(len(main)),
            "families": int(main.circuit_family.nunique()),
            "qubit_range": [int(main.n_qubits.min()), int(main.n_qubits.max())],
            "all_semantically_valid": True,
            "cpu_seconds_range": [
                float(main.execute_cpu_seconds.min()),
                float(main.execute_cpu_seconds.max()),
            ],
            "disk_read_bytes_range": [
                int(main.process_disk_read_bytes.min()),
                int(main.process_disk_read_bytes.max()),
            ],
            "disk_write_bytes_range": [
                int(main.process_disk_write_bytes_before_result.min()),
                int(main.process_disk_write_bytes_before_result.max()),
            ],
            "profile_directory_bytes_range": [
                int(main.final_profile_directory_bytes.min()),
                int(main.final_profile_directory_bytes.max()),
            ],
            "peak_rss_mb_range": [float(main.peak_rss_mb.min()), float(main.peak_rss_mb.max())],
        },
        "memory_scaling": memory,
        "worker_sensitivity": {
            "worker_counts": [1, 2, 4],
            "tasks_per_condition": 8,
            "deterministic_output_hashes_across_conditions": True,
            "throughput_range_tasks_per_second": [
                float(workers.throughput_tasks_per_second.min()),
                float(workers.throughput_tasks_per_second.max()),
            ],
        },
        "cache_sensitivity": {
            "repetitions_same_process": 5,
            "first_execute_wall_seconds": cache_first,
            "median_subsequent_execute_wall_seconds": cache_warm,
            "warm_to_first_ratio": float(cache_warm / cache_first) if cache_first else None,
            "output_hash_stable": True,
            "limitation": "same-process warm-state diagnostic; operating-system caches were not flushed",
        },
        "metric_dispositions": {
            "10.02": "PASS: process CPU time is directly measured for every bounded resource-profile cell",
            "10.05": "PASS: process disk read and write bytes are directly measured for every bounded profile cell",
            "10.06": "PARTIAL: managed per-cell profiling-directory storage is measured, but operating-system temporary storage is not captured",
            "10.09": "PASS: cold-process import initialization wall and CPU time are directly measured",
            "10.10": "PASS: payload and QASM parsing wall and CPU time are directly measured",
            "10.11": "PASS: common-basis conversion wall and CPU time are directly measured",
            "10.13": "PASS: exact semantic verification wall and CPU time are directly measured",
            "10.14": "PASS: substantive result JSON serialization time and byte size are directly probed",
            "10.24": "PASS: a 4-10 qubit diagnostic peak-RSS scaling exponent with bootstrap interval is reported",
            "10.33": "PASS: identical tasks are compared at 1, 2, and 4 workers with deterministic output-hash agreement",
            "10.34": "PARTIAL: first versus repeated same-process execution is measured, but operating-system caches are not forcibly flushed",
        },
        "claim_boundary": (
            "These measurements characterize the current Windows host and diagnostic panel; "
            "they do not retroactively decompose the sealed E31 formal run, establish energy "
            "or monetary cost, or generalize resource scaling beyond qubits 4-10."
        ),
    }
    report["artifacts"] = {
        path.name: {"sha256": sha256(path), "rows": int(len(pd.read_csv(path)))}
        for path in (main_path, workers_path, cache_path)
    }
    report_path = output_dir / "resource_profile_audit.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = build_audit(args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
