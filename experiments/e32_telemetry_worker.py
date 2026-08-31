"""One-cell worker for the bounded E32 optimizer telemetry panel.

The sealed E31 worker and its results are read-only inputs to the design.  This
worker independently instruments the Phase-2b public pipeline by invoking the
same protected rewrite primitives in the same order.  Every outer-iteration
candidate is independently checked with exact average-gate fidelity (the
frozen panel is limited to at most eight qubits) before it can become an
incumbent or contribute a timing outcome.
"""

from __future__ import annotations

CELL_ORIGIN_NS = __import__("time").perf_counter_ns()

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

from qiskit import qasm2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.e31_listing_phase2b_interaction import random_topological_listing
from src.circuits.real_benchmarks import average_gate_fidelity, circuit_sha256
from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor
from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _listed(circuit, model: str, seed: int):
    if model == "LBL":
        return circuit.copy()
    if model == "WCL":
        return WireTraversalPreprocessor().preprocess(circuit)
    if model == "RANDOM_TOPOLOGICAL":
        return random_topological_listing(circuit, seed)
    raise ValueError(f"unsupported listing model: {model}")


class EventRecorder:
    def __init__(self, origin_ns: int) -> None:
        self.origin_ns = int(origin_ns)
        self.events: list[dict[str, Any]] = []
        self._last_elapsed_ns = -1

    def add(self, event: str, **fields: Any) -> dict[str, Any]:
        elapsed_ns = time.perf_counter_ns() - self.origin_ns
        if elapsed_ns < self._last_elapsed_ns:
            raise RuntimeError("perf_counter_ns moved backwards")
        self._last_elapsed_ns = elapsed_ns
        record = {
            "event_index": len(self.events),
            "event": event,
            "elapsed_ns": int(elapsed_ns),
            "elapsed_seconds": elapsed_ns / 1_000_000_000.0,
            **fields,
        }
        self.events.append(record)
        return record


def execute(payload: dict[str, Any]) -> dict[str, Any]:
    recorder = EventRecorder(CELL_ORIGIN_NS)
    recorder.add("cell_python_started")

    qasm_path = Path(str(payload["qasm_path"]))
    if not qasm_path.is_absolute():
        qasm_path = PROJECT_ROOT / qasm_path
    qasm_path = qasm_path.resolve()
    if not qasm_path.is_relative_to(PROJECT_ROOT) or not qasm_path.is_file():
        raise ValueError("input QASM is absent or outside the project")
    if file_sha256(qasm_path) != str(payload["qasm_file_sha256"]):
        raise ValueError("input QASM byte hash differs from frozen payload")

    original = qasm2.load(
        qasm_path, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS
    )
    parsed_hash = circuit_sha256(original)
    if parsed_hash != str(payload["input_circuit_sha256"]):
        raise ValueError("parsed input circuit hash differs from frozen payload")
    if original.num_qubits > int(payload["maximum_exact_qubits"]):
        raise ValueError("panel input exceeds frozen exact-verification limit")
    recorder.add(
        "input_loaded",
        input_circuit_sha256=parsed_hash,
        input_gate_count=int(original.size()),
        n_qubits=int(original.num_qubits),
    )

    listed = _listed(
        original, str(payload["listing_model"]), int(payload["listing_seed"])
    )
    listed_fidelity = average_gate_fidelity(
        listed, original, max_qubits=int(payload["maximum_exact_qubits"])
    )
    if listed_fidelity < float(payload["fidelity_threshold"]):
        raise ValueError("listing transformation failed exact equivalence")
    recorder.add(
        "listing_validated",
        listed_circuit_sha256=circuit_sha256(listed),
        listed_gate_count=int(listed.size()),
        exact_fidelity=float(listed_fidelity),
    )

    template_enabled = str(payload["rule_set"]) == "COMMUTATION_PLUS_TEMPLATES"
    if str(payload["rule_set"]) not in {
        "COMMUTATION_ONLY",
        "COMMUTATION_PLUS_TEMPLATES",
    }:
        raise ValueError("unsupported rule set")
    engine = Phase2bTemplateMatcher(
        max_iterations=int(payload["max_iterations"]),
        fidelity_threshold=float(payload["fidelity_threshold"]),
        success_reduction=0.0,
        gather_window=int(payload["window_gates"]),
        template_enabled=template_enabled,
        collect_trace=False,
    )
    recorder.add("optimizer_initialized")

    optimized = listed.copy()
    total_counts = engine._zero_counters()
    valid_candidates: list[dict[str, Any]] = []
    for iteration in range(engine.max_iterations):
        counts = engine._zero_counters()
        engine._gather_h_sandwiches(optimized, counts)
        engine._gather_commuting_pairs(optimized, counts)
        if engine.template_enabled:
            engine._apply_all_templates(optimized, counts)
        engine._cancel_inverse_pairs(optimized, counts)
        engine._merge_phase_gates(optimized, counts)
        engine._accumulate(total_counts, counts)

        fidelity = average_gate_fidelity(
            optimized, original, max_qubits=int(payload["maximum_exact_qubits"])
        )
        valid = bool(fidelity >= float(payload["fidelity_threshold"]))
        event = recorder.add(
            "iteration_candidate_validated",
            iteration=int(iteration),
            gate_count=int(optimized.size()),
            output_circuit_sha256=circuit_sha256(optimized),
            exact_fidelity=float(fidelity),
            valid_equivalent_output=valid,
            rewrite_counts={name: int(value) for name, value in counts.items()},
            no_progress=bool(engine._no_progress(counts)),
        )
        if valid:
            valid_candidates.append(event)
        if engine._no_progress(counts):
            break

    if valid_candidates:
        minimum_gate_count = min(int(event["gate_count"]) for event in valid_candidates)
        first_valid = valid_candidates[0]
        best = next(
            event
            for event in valid_candidates
            if int(event["gate_count"]) == minimum_gate_count
        )
        time_to_first_valid_ns: int | None = int(first_valid["elapsed_ns"])
        time_to_best_ns: int | None = int(best["elapsed_ns"])
        first_valid_event_index: int | None = int(first_valid["event_index"])
        best_event_index: int | None = int(best["event_index"])
        status = "success"
    else:
        minimum_gate_count = None
        time_to_first_valid_ns = None
        time_to_best_ns = None
        first_valid_event_index = None
        best_event_index = None
        status = "invalid"

    recorder.add("cell_finished", status=status)
    return {
        "schema_version": "1.0.0",
        "run_id": str(payload["run_id"]),
        "run_order": int(payload["run_order"]),
        "status": status,
        "valid_equivalent_output": bool(valid_candidates),
        "input_circuit_sha256": parsed_hash,
        "circuit_family": str(payload["circuit_family"]),
        "n_qubits": int(original.num_qubits),
        "listing_model": str(payload["listing_model"]),
        "rule_set": str(payload["rule_set"]),
        "window_gates": int(payload["window_gates"]),
        "budget_seconds": float(payload["budget_seconds"]),
        "measurement_clock": "time.perf_counter_ns",
        "measurement_origin": "first executed Python instruction in worker module",
        "timing_includes": [
            "module imports",
            "QASM parsing",
            "listing construction and exact validation",
            "optimizer setup",
            "rewrite iterations",
            "per-iteration exact candidate validation",
        ],
        "time_to_first_valid_ns": time_to_first_valid_ns,
        "time_to_first_valid_seconds": (
            None if time_to_first_valid_ns is None
            else time_to_first_valid_ns / 1_000_000_000.0
        ),
        "time_to_best_ns": time_to_best_ns,
        "time_to_best_seconds": (
            None if time_to_best_ns is None else time_to_best_ns / 1_000_000_000.0
        ),
        "first_valid_event_index": first_valid_event_index,
        "best_event_index": best_event_index,
        "best_valid_gate_count": minimum_gate_count,
        "input_gate_count": int(original.size()),
        "best_valid_reduction_pct_itt": (
            0.0
            if minimum_gate_count is None or original.size() == 0
            else 100.0 * (1.0 - minimum_gate_count / original.size())
        ),
        "event_count": len(recorder.events),
        "events": recorder.events,
        "total_rewrite_counts": {
            name: int(value) for name, value in total_counts.items()
        },
        "worker_environment": {
            "python_executable": str(Path(sys.executable).resolve()),
            "python_version": sys.version,
            "platform": platform.platform(),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.payload.resolve().read_text(encoding="utf-8"))
    result = execute(payload)
    atomic_json(args.result.resolve(), result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
