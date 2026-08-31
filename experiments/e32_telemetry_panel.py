"""Checkpointed orchestrator for the bounded E32 telemetry panel.

Dry-run is the default.  ``--formal`` is required to execute the complete
frozen 15-family x 6-treatment schedule.  Every cell runs in a fresh process;
timeout, error, and invalid outcomes remain in the ITT denominator and never
receive imputed timing outcomes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import psutil
from qiskit import qasm2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import circuit_sha256

DEFAULT_PROTOCOL = PROJECT_ROOT / "experiments/e32_telemetry_protocol.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/v11/e32_telemetry"
WORKER = PROJECT_ROOT / "experiments/e32_telemetry_worker.py"
FREEZER = PROJECT_ROOT / "scripts/freeze_e32_telemetry_protocol.py"
VERIFIER = PROJECT_ROOT / "scripts/verify_e32_telemetry_panel.py"
THREAD_ENV = {
    "OPENBLAS_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "RAYON_NUM_THREADS": "1",
}
RESULT_COLUMNS = [
    "run_id", "run_order", "circuit_family", "input_circuit_sha256",
    "n_qubits", "listing_model", "rule_set", "window_gates",
    "budget_seconds", "status", "valid_equivalent_output",
    "time_to_first_valid_seconds", "time_to_best_seconds",
    "first_valid_event_index", "best_event_index", "event_count",
    "input_gate_count", "best_valid_gate_count",
    "best_valid_reduction_pct_itt", "cell_receipt_sha256",
]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def canonical_run_id(input_hash: str, listing: str, rule_set: str, window: int) -> str:
    material = f"E32|{input_hash}|{listing}|{rule_set}|{window}".encode("utf-8")
    return "e32-" + hashlib.sha256(material).hexdigest()[:24]


def load_and_validate_protocol(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    protocol = json.loads(path.resolve().read_text(encoding="utf-8"))
    if protocol.get("design_status") != "FROZEN_BEFORE_EXECUTION":
        raise ValueError("E32 protocol is not frozen before execution")
    if protocol.get("experiment_id") != "E32_TELEMETRY_V1":
        raise ValueError("unexpected E32 experiment_id")
    source_hashes = protocol.get("source_sha256", {})
    expected_sources = {
        "experiments/e32_telemetry_worker.py": WORKER,
        "experiments/e32_telemetry_panel.py": Path(__file__).resolve(),
        "scripts/freeze_e32_telemetry_protocol.py": FREEZER,
        "scripts/verify_e32_telemetry_panel.py": VERIFIER,
    }
    if set(source_hashes) != set(expected_sources):
        raise ValueError("protocol source closure is incomplete or contains foreign paths")
    for relative, source in expected_sources.items():
        if file_sha256(source) != str(source_hashes[relative]):
            raise ValueError(f"source hash drift: {relative}")

    inputs = protocol.get("inputs", [])
    if len(inputs) != 15 or len({row["circuit_family"] for row in inputs}) != 15:
        raise ValueError("formal panel requires exactly one input from each of 15 families")
    maximum_qubits = int(protocol["verification_contract"]["maximum_exact_qubits"])
    for row in inputs:
        qasm_path = (PROJECT_ROOT / str(row["qasm_path"])).resolve()
        if not qasm_path.is_relative_to(PROJECT_ROOT) or not qasm_path.is_file():
            raise ValueError(f"missing or foreign QASM: {qasm_path}")
        if file_sha256(qasm_path) != str(row["qasm_file_sha256"]):
            raise ValueError(f"QASM byte hash drift: {qasm_path}")
        circuit = qasm2.load(
            qasm_path, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS
        )
        if circuit_sha256(circuit) != str(row["input_circuit_sha256"]):
            raise ValueError(f"parsed circuit hash drift: {qasm_path}")
        if circuit.num_qubits != int(row["n_qubits"]) or circuit.num_qubits > maximum_qubits:
            raise ValueError(f"qubit contract failure: {qasm_path}")

    factors = protocol["factors"]
    cells = [
        (listing, rule_set, int(window))
        for listing in factors["listing_model"]
        for rule_set in factors["rule_set"]
        for window in factors["window_gates"]
    ]
    if len(cells) != 6 or len(set(cells)) != 6:
        raise ValueError("formal E32 treatment schedule must contain six unique cells")
    schedule: list[dict[str, Any]] = []
    for input_row in sorted(inputs, key=lambda row: str(row["circuit_family"])):
        for listing, rule_set, window in cells:
            run_id = canonical_run_id(
                str(input_row["input_circuit_sha256"]), listing, rule_set, window
            )
            schedule.append({
                **input_row,
                "run_id": run_id,
                "run_order": len(schedule),
                "listing_model": listing,
                "rule_set": rule_set,
                "window_gates": window,
                "listing_seed": int(protocol["listing_seed"]),
                "budget_seconds": float(protocol["resource_contract"]["cell_timeout_seconds"]),
                "max_iterations": int(protocol["optimizer_contract"]["max_iterations"]),
                "fidelity_threshold": float(protocol["verification_contract"]["fidelity_threshold"]),
                "maximum_exact_qubits": maximum_qubits,
            })
    if len(schedule) != 90 or len({row["run_id"] for row in schedule}) != 90:
        raise ValueError("formal E32 schedule must contain 90 unique cells")
    return protocol, schedule


def _run_cell(row: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    cell_dir = output_dir / "cells"
    payload_path = cell_dir / f"{row['run_id']}.payload.json"
    receipt_path = cell_dir / f"{row['run_id']}.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        bound_fields = (
            "run_id", "run_order", "circuit_family", "input_circuit_sha256",
            "n_qubits", "listing_model", "rule_set", "window_gates",
            "budget_seconds",
        )
        if any(receipt.get(key) != row[key] for key in bound_fields):
            raise ValueError(f"foreign or drifted checkpoint receipt: {receipt_path}")
        return receipt
    atomic_json(payload_path, row)
    environment = os.environ.copy()
    environment.update(THREAD_ENV)
    command = [
        sys.executable, str(WORKER), "--payload", str(payload_path),
        "--result", str(receipt_path),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=float(row["budget_seconds"]),
            check=False,
        )
        if completed.returncode == 0 and receipt_path.is_file():
            return json.loads(receipt_path.read_text(encoding="utf-8"))
        status = "error"
        diagnostic = {
            "returncode": int(completed.returncode),
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        status = "timeout"
        diagnostic = {
            "timeout_seconds": float(row["budget_seconds"]),
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
        }
    receipt = {
        "schema_version": "1.0.0",
        **{key: row[key] for key in (
            "run_id", "run_order", "circuit_family", "input_circuit_sha256",
            "n_qubits", "listing_model", "rule_set", "window_gates", "budget_seconds",
        )},
        "status": status,
        "valid_equivalent_output": False,
        "time_to_first_valid_ns": None,
        "time_to_first_valid_seconds": None,
        "time_to_best_ns": None,
        "time_to_best_seconds": None,
        "first_valid_event_index": None,
        "best_event_index": None,
        "event_count": 0,
        "events": [],
        "input_gate_count": None,
        "best_valid_gate_count": None,
        "best_valid_reduction_pct_itt": 0.0,
        "diagnostic": diagnostic,
    }
    atomic_json(receipt_path, receipt)
    return receipt


def _result_row(receipt: dict[str, Any], receipt_path: Path) -> dict[str, Any]:
    return {
        key: (file_sha256(receipt_path) if key == "cell_receipt_sha256" else receipt.get(key))
        for key in RESULT_COLUMNS
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=RESULT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _finite(values: list[Any]) -> np.ndarray:
    return np.asarray([float(value) for value in values if value not in (None, "")], dtype=float)


def build_summary(receipts: list[dict[str, Any]], protocol_sha256: str) -> dict[str, Any]:
    status_counts = Counter(str(row["status"]) for row in receipts)
    first = _finite([row.get("time_to_first_valid_seconds") for row in receipts])
    best = _finite([row.get("time_to_best_seconds") for row in receipts])
    groups: list[dict[str, Any]] = []
    for listing in sorted({str(row["listing_model"]) for row in receipts}):
        for rule_set in sorted({str(row["rule_set"]) for row in receipts}):
            subset = [
                row for row in receipts
                if row["listing_model"] == listing and row["rule_set"] == rule_set
            ]
            first_values = _finite([row.get("time_to_first_valid_seconds") for row in subset])
            best_values = _finite([row.get("time_to_best_seconds") for row in subset])
            groups.append({
                "listing_model": listing,
                "rule_set": rule_set,
                "itt_n": len(subset),
                "timing_available_n": int(len(first_values)),
                "failure_timeout_invalid_n": int(len(subset) - len(first_values)),
                "time_to_first_valid_median_seconds": (
                    None if not len(first_values) else float(np.median(first_values))
                ),
                "time_to_first_valid_p95_seconds": (
                    None if not len(first_values) else float(np.percentile(first_values, 95))
                ),
                "time_to_best_median_seconds": (
                    None if not len(best_values) else float(np.median(best_values))
                ),
                "time_to_best_p95_seconds": (
                    None if not len(best_values) else float(np.percentile(best_values, 95))
                ),
            })
    return {
        "schema_version": "1.0.0",
        "status": "FORMAL_BOUNDED_PANEL_COMPLETE" if len(receipts) == 90 else "INCOMPLETE",
        "protocol_sha256": protocol_sha256,
        "itt_scheduled_n": 90,
        "itt_observed_n": len(receipts),
        "outer_family_n": len({str(row["circuit_family"]) for row in receipts}),
        "status_counts": dict(sorted(status_counts.items())),
        "timing_available_n": int(len(first)),
        "timing_unavailable_n": int(len(receipts) - len(first)),
        "time_to_first_valid": {
            "estimand": "elapsed time to first independently exact-valid post-iteration candidate",
            "median_seconds_available_cases": None if not len(first) else float(np.median(first)),
            "p95_seconds_available_cases": None if not len(first) else float(np.percentile(first, 95)),
        },
        "time_to_best": {
            "estimand": "elapsed time to earliest exact-valid candidate attaining the observed minimum gate count",
            "median_seconds_available_cases": None if not len(best) else float(np.median(best)),
            "p95_seconds_available_cases": None if not len(best) else float(np.percentile(best, 95)),
        },
        "itt_contract": (
            "all 90 scheduled cells remain in denominator; timeout/error/invalid have unavailable "
            "timing and zero optimization benefit, never survivor imputation"
        ),
        "treatment_summaries": groups,
        "claim_scope": (
            "descriptive fixed-panel evidence for the 15 selected <=8-qubit families, six "
            "Phase-2b treatments, this host, and this source/environment only"
        ),
        "not_supported": [
            "sealed E31 timing reconstruction",
            "unseen-family generalization",
            "cross-machine timing generalization",
            "real-QPU time-to-solution",
            "optimizer-independent timing claims",
        ],
    }


def environment_record(protocol_path: Path) -> dict[str, Any]:
    packages = {}
    for name in ("qiskit", "numpy", "psutil"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": file_sha256(protocol_path),
        "python_executable": str(Path(sys.executable).resolve()),
        "python_executable_sha256": file_sha256(Path(sys.executable).resolve()),
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpu_count": psutil.cpu_count(),
        "physical_cpu_count": psutil.cpu_count(logical=False),
        "physical_ram_bytes": psutil.virtual_memory().total,
        "thread_limits": THREAD_ENV,
        "packages": packages,
        "cold_process_per_cell": True,
    }


def write_artifact_manifest(output_dir: Path, protocol: Path) -> Path:
    manifest_path = output_dir / "artifact_manifest.json"
    paths = [
        protocol,
        WORKER,
        Path(__file__).resolve(),
        output_dir / "results.csv",
        output_dir / "summary.json",
        output_dir / "environment.json",
    ] + sorted((output_dir / "cells").glob("*.json"))
    payload = {
        "schema_version": "1.0.0",
        "artifact_count": len(paths),
        "artifacts": [
            {
                "path": str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
            for path in paths
        ],
    }
    atomic_json(manifest_path, payload)
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--formal", action="store_true")
    args = parser.parse_args()
    protocol_path = args.protocol.resolve()
    output_dir = args.output_dir.resolve()
    _, schedule = load_and_validate_protocol(protocol_path)
    if not args.formal:
        print(json.dumps({
            "status": "DRY_RUN_ONLY",
            "scheduled_cells": len(schedule),
            "outer_families": len({row["circuit_family"] for row in schedule}),
            "protocol_sha256": file_sha256(protocol_path),
        }, indent=2, sort_keys=True))
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(output_dir / "environment.json", environment_record(protocol_path))
    receipts = []
    for row in schedule:
        receipt = _run_cell(row, output_dir)
        receipts.append(receipt)
        print(
            f"[{len(receipts):02d}/{len(schedule)}] {row['run_id']} {receipt['status']}",
            flush=True,
        )
    rows = [
        _result_row(receipt, output_dir / "cells" / f"{receipt['run_id']}.json")
        for receipt in receipts
    ]
    _write_csv(output_dir / "results.csv", rows)
    summary = build_summary(receipts, file_sha256(protocol_path))
    atomic_json(output_dir / "summary.json", summary)
    manifest = write_artifact_manifest(output_dir, protocol_path)
    print(json.dumps({
        "status": summary["status"],
        "results": str(output_dir / "results.csv"),
        "summary": str(output_dir / "summary.json"),
        "artifact_manifest": str(manifest),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
