"""Freeze the bounded E32 event-telemetry protocol before formal execution."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from qiskit import qasm2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_MANIFEST = PROJECT_ROOT / "data/v10/prepaper/sota/inputs/benchmark_manifest.csv"
OUTPUT = PROJECT_ROOT / "experiments/e32_telemetry_protocol.json"
SOURCE_PATHS = (
    "experiments/e32_telemetry_worker.py",
    "experiments/e32_telemetry_panel.py",
    "scripts/freeze_e32_telemetry_protocol.py",
    "scripts/verify_e32_telemetry_panel.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    # Local import avoids changing sys.path or silently accepting a different copy.
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.circuits.real_benchmarks import circuit_sha256

    with INPUT_MANIFEST.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    eligible = [row for row in rows if int(row["n_qubits"]) <= 8]
    families = sorted({row["circuit_family"] for row in eligible})
    if len(families) != 15:
        raise ValueError(f"expected 15 eligible families, observed {len(families)}")
    inputs = []
    for family in families:
        candidates = [row for row in eligible if row["circuit_family"] == family]
        # Maximum eligible width, then stable input hash, prevents outcome-based selection.
        selected = sorted(
            candidates,
            key=lambda row: (-int(row["n_qubits"]), row["input_circuit_sha256"]),
        )[0]
        qasm_path = PROJECT_ROOT / selected["qasm_path"]
        circuit = qasm2.load(qasm_path, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
        parsed_hash = circuit_sha256(circuit)
        if parsed_hash != selected["input_circuit_sha256"]:
            raise ValueError(f"parsed input hash drift: {qasm_path}")
        inputs.append({
            "circuit_family": family,
            "circuit_id": selected["circuit_id"],
            "n_qubits": int(selected["n_qubits"]),
            "qasm_path": selected["qasm_path"].replace("\\", "/"),
            "qasm_file_sha256": sha256(qasm_path),
            "input_circuit_sha256": parsed_hash,
        })
    payload = {
        "schema_version": "1.0.0",
        "experiment_id": "E32_TELEMETRY_V1",
        "design_status": "FROZEN_BEFORE_EXECUTION",
        "freeze_date": "2026-08-31",
        "selection_rule": "one maximum-width <=8-qubit input per each of 15 pre-existing E31 families; ties resolved by input_circuit_sha256 before outcomes",
        "source_manifest": str(INPUT_MANIFEST.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "source_manifest_sha256": sha256(INPUT_MANIFEST),
        "source_sha256": {relative: sha256(PROJECT_ROOT / relative) for relative in SOURCE_PATHS},
        "inputs": inputs,
        "factors": {
            "listing_model": ["LBL", "WCL", "RANDOM_TOPOLOGICAL"],
            "rule_set": ["COMMUTATION_ONLY", "COMMUTATION_PLUS_TEMPLATES"],
            "window_gates": [16],
        },
        "listing_seed": 20260831,
        "optimizer_contract": {"max_iterations": 50},
        "resource_contract": {"cell_timeout_seconds": 60.0, "cold_process_per_cell": True, "threads_per_worker": 1},
        "verification_contract": {"method": "exact_average_gate_fidelity_per_iteration", "maximum_exact_qubits": 8, "fidelity_threshold": 0.9999999999},
        "responses": {
            "time_to_first_valid_seconds": "elapsed monotonic time from first worker instruction to first independently exact-valid post-iteration candidate",
            "time_to_best_seconds": "elapsed monotonic time to earliest independently exact-valid candidate attaining the observed minimum gate count",
        },
        "failure_semantics": "all 90 cells retained; timeout/error/invalid timings remain unavailable and benefit is zero under ITT",
        "claim_scope": "fixed descriptive 15-family <=8-qubit panel on this host and source/environment only",
        "not_supported": ["reconstruction of sealed E31 timing", "unseen-family generalization", "cross-host timing", "real-QPU timing", "optimizer-independent timing"],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(OUTPUT), "inputs": len(inputs), "cells": len(inputs) * 6}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
