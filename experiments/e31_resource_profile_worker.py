"""Isolated phase-timing worker for the non-confirmatory E31 resource profile.

This module intentionally does not replace or modify the sealed formal worker.
It reuses the same optimizer and semantic contract while adding diagnostic
timers and process counters that were not captured in the formal run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

MODULE_WALL_START = time.perf_counter()
MODULE_CPU_START = time.process_time()

import psutil
from qiskit import qasm2, transpile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.e31_listing_phase2b_interaction import random_topological_listing
from src.circuits.real_benchmarks import average_gate_fidelity, circuit_sha256
from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor
from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher

IMPORT_INITIALIZATION_WALL_SECONDS = time.perf_counter() - MODULE_WALL_START
IMPORT_INITIALIZATION_CPU_SECONDS = time.process_time() - MODULE_CPU_START


def _measure(callable_):
    wall = time.perf_counter()
    cpu = time.process_time()
    value = callable_()
    return value, time.perf_counter() - wall, time.process_time() - cpu


def _listing(circuit, model: str, seed: int):
    if model == "LBL":
        return circuit.copy()
    if model == "WCL":
        return WireTraversalPreprocessor().preprocess(circuit)
    if model == "RANDOM_TOPOLOGICAL":
        return random_topological_listing(circuit, seed)
    raise ValueError(f"unknown listing model: {model}")


def execute(payload: dict) -> dict:
    process = psutil.Process()
    phase_rss = [process.memory_info().rss]
    qasm_path = Path(payload["qasm_path"])
    if not qasm_path.is_absolute():
        qasm_path = PROJECT_ROOT / qasm_path
    original, qasm_wall, qasm_cpu = _measure(
        lambda: qasm2.load(
            qasm_path,
            custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
        )
    )
    phase_rss.append(process.memory_info().rss)
    listed, listing_wall, listing_cpu = _measure(
        lambda: _listing(
            original,
            str(payload["listing_model"]),
            int(payload["listing_seed"]),
        )
    )
    phase_rss.append(process.memory_info().rss)
    template_enabled = str(payload["rule_set"]) == "COMMUTATION_PLUS_TEMPLATES"
    if str(payload["rule_set"]) not in {
        "COMMUTATION_ONLY",
        "COMMUTATION_PLUS_TEMPLATES",
    }:
        raise ValueError(f"unknown rule set: {payload['rule_set']}")
    engine, setup_wall, setup_cpu = _measure(
        lambda: Phase2bTemplateMatcher(
            max_iterations=100,
            fidelity_threshold=float(payload["fidelity_threshold"]),
            success_reduction=0.0,
            gather_window=int(payload["window_gates"]),
            template_enabled=template_enabled,
            collect_trace=True,
        )
    )
    optimized, optimization_wall, optimization_cpu = _measure(
        lambda: engine.optimize_full_pipeline(listed, target=original)
    )
    phase_rss.append(process.memory_info().rss)
    fidelity, verification_wall, verification_cpu = _measure(
        lambda: average_gate_fidelity(
            optimized.optimized_circuit,
            original,
            max_qubits=original.num_qubits,
        )
    )
    phase_rss.append(process.memory_info().rss)
    basis = list(payload["common_basis"])
    basis_start_wall = time.perf_counter()
    basis_start_cpu = time.process_time()
    normalized_input = transpile(listed, basis_gates=basis, optimization_level=0)
    normalized_output = transpile(
        optimized.optimized_circuit,
        basis_gates=basis,
        optimization_level=0,
    )
    basis_wall = time.perf_counter() - basis_start_wall
    basis_cpu = time.process_time() - basis_start_cpu
    phase_rss.append(process.memory_info().rss)
    initial = normalized_input.size()
    reduction = 100.0 * (1.0 - normalized_output.size() / initial) if initial else 0.0
    valid = bool(fidelity >= float(payload["fidelity_threshold"]))
    result = {
        "status": "success" if valid else "invalid",
        "valid_equivalent_output": valid,
        "exact_fidelity": float(fidelity),
        "output_circuit_sha256": circuit_sha256(optimized.optimized_circuit),
        "common_basis_gate_reduction_pct": float(reduction),
        "optimizer_reported_runtime_seconds": float(optimized.runtime_seconds),
        "original_common_basis_gate_count": int(initial),
        "optimized_common_basis_gate_count": int(normalized_output.size()),
        "n_qubits": int(original.num_qubits),
        "template_enabled": template_enabled,
        "trace_iterations": int(len(optimized.metadata.get("trace", []))),
        "phase_wall_seconds": {
            "qasm_parsing": qasm_wall,
            "listing": listing_wall,
            "engine_initialization": setup_wall,
            "optimization": optimization_wall,
            "exact_verification": verification_wall,
            "basis_conversion": basis_wall,
        },
        "phase_cpu_seconds": {
            "qasm_parsing": qasm_cpu,
            "listing": listing_cpu,
            "engine_initialization": setup_cpu,
            "optimization": optimization_cpu,
            "exact_verification": verification_cpu,
            "basis_conversion": basis_cpu,
        },
        "phase_boundary_peak_rss_bytes": int(max(phase_rss)),
    }
    serialization_start_wall = time.perf_counter()
    serialization_start_cpu = time.process_time()
    probe = json.dumps(result, sort_keys=True)
    result["serialization_probe_wall_seconds"] = (
        time.perf_counter() - serialization_start_wall
    )
    result["serialization_probe_cpu_seconds"] = (
        time.process_time() - serialization_start_cpu
    )
    result["serialization_probe_bytes"] = len(probe.encode("utf-8"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    if args.repeats < 1:
        raise ValueError("repeats must be positive")
    process = psutil.Process()
    io_start = process.io_counters()
    payload_start_wall = time.perf_counter()
    payload_start_cpu = time.process_time()
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    payload_wall = time.perf_counter() - payload_start_wall
    payload_cpu = time.process_time() - payload_start_cpu
    repetitions = []
    for index in range(args.repeats):
        start_wall = time.perf_counter()
        start_cpu = time.process_time()
        result = execute(payload)
        result["repeat_index"] = index
        result["execute_wall_seconds"] = time.perf_counter() - start_wall
        result["execute_cpu_seconds"] = time.process_time() - start_cpu
        repetitions.append(result)
    io_end = process.io_counters()
    packet = {
        "status": "RESOURCE_PROFILE_NONCONFIRMATORY",
        "import_initialization_wall_seconds": IMPORT_INITIALIZATION_WALL_SECONDS,
        "import_initialization_cpu_seconds": IMPORT_INITIALIZATION_CPU_SECONDS,
        "payload_parsing_wall_seconds": payload_wall,
        "payload_parsing_cpu_seconds": payload_cpu,
        "process_disk_read_bytes": int(io_end.read_bytes - io_start.read_bytes),
        "process_disk_write_bytes_before_result": int(io_end.write_bytes - io_start.write_bytes),
        "repetitions": repetitions,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, args.result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
