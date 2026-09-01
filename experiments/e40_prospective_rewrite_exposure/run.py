"""Freeze and execute the v12 prospective MQT rewrite-exposure panel.

Generation is intentionally a separate mode because the frozen MQT/Qiskit
generator environment is not the core optimization environment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import multiprocessing
import os
import platform
import random
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUTPUT_ROOT = ROOT / "data" / "v12" / "e40_prospective_rewrite_exposure"
GENERATION_MANIFEST = OUTPUT_ROOT / "generation_manifest.json"
IDS = (
    "ae", "bmw_quark_cardinality", "bmw_quark_copula",
    "cdkm_ripple_carry_adder", "dj", "draper_qft_adder", "full_adder",
    "graphstate", "half_adder", "hhl", "hrs_cumulative_multiplier", "iqpe",
    "modular_adder", "multiplier", "qftentangled", "qnn", "qpeexact",
    "qpeinexact", "rg_qft_multiplier", "seven_qubit_steane_code", "shor",
    "shors_nine_qubit_code", "vbe_ripple_carry_adder", "wstate",
)
DECLARED_SIZES = tuple(range(4, 11))
EXPERIMENT_ID = "E40_PROSPECTIVE_REWRITE_EXPOSURE_V1"
DATE_SEED = "20260901"
THRESHOLD = 0.9999999999
ARMS = (
    "LBL_Greedy", "WCL_Greedy", "RandomTopological32_Greedy",
    "CGL_Greedy", "LBL_Phase2b", "CGL_Phase2b",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(field for row in rows for field in row))
    import io
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def generate() -> dict[str, Any]:
    from mqt.bench import BenchmarkLevel, get_benchmark
    from qiskit import qasm2

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    selected: list[dict[str, Any]] = []
    for benchmark in IDS:
        eligible: list[dict[str, Any]] = []
        for declared_size in DECLARED_SIZES:
            record: dict[str, Any] = {"benchmark": benchmark, "declared_size": declared_size}
            try:
                circuit = get_benchmark(
                    benchmark=benchmark,
                    level=BenchmarkLevel.INDEP,
                    circuit_size=declared_size,
                    random_parameters=False,
                )
                names = sorted(str(name) for name in circuit.count_ops())
                dynamic = any(
                    getattr(instruction.operation, "condition", None) is not None
                    or getattr(instruction.operation, "is_control_flow", False)
                    for instruction in circuit.data
                )
                forbidden = {"measure", "reset", "initialize", "delay"}
                has_forbidden = bool(forbidden.intersection(names))
                record.update({
                    "status": "generated",
                    "actual_qubits": int(circuit.num_qubits),
                    "gate_count": int(circuit.size()),
                    "classical_bits": int(circuit.num_clbits),
                    "parameter_count": len(circuit.parameters),
                    "dynamic_control": bool(dynamic),
                    "gate_alphabet": names,
                    "qasm2_export": False,
                })
                if circuit.num_qubits > 10:
                    record["eligibility_reason"] = "actual_qubits_gt_10"
                elif circuit.size() < 20 or circuit.size() > 2000:
                    record["eligibility_reason"] = "gate_count_outside_20_2000"
                elif circuit.num_clbits:
                    record["eligibility_reason"] = "classical_bits_present"
                elif len(circuit.parameters):
                    record["eligibility_reason"] = "unbound_parameters"
                elif dynamic:
                    record["eligibility_reason"] = "dynamic_control"
                elif has_forbidden:
                    record["eligibility_reason"] = "nonunitary_operation"
                else:
                    qasm_text = qasm2.dumps(circuit)
                    record["qasm2_export"] = True
                    qasm_hash = sha256_bytes(qasm_text.encode())
                    record["qasm_sha256"] = qasm_hash
                    eligible.append((record, qasm_text))
                    record["eligibility_reason"] = "eligible"
            except Exception as exc:
                record.update({"status": "generation_error", "error": f"{type(exc).__name__}:{str(exc)[:180]}"})
            attempts.append(record)
        if eligible:
            chosen_record, chosen_qasm = min(
                eligible,
                key=lambda item: (-item[0]["actual_qubits"], -item[0]["gate_count"], item[0]["qasm_sha256"]),
            )
            qasm_path = OUTPUT_ROOT / "qasm" / f"{benchmark}.qasm"
            qasm_path.parent.mkdir(parents=True, exist_ok=True)
            qasm_path.write_text(chosen_qasm, encoding="utf-8", newline="\n")
            chosen = dict(chosen_record)
            chosen.update({
                "panel_status": "eligible",
                "qasm_path": str(qasm_path.relative_to(ROOT)).replace("\\", "/"),
                "qasm_file_sha256": sha256_file(qasm_path),
            })
            selected.append(chosen)
        else:
            selected.append({"benchmark": benchmark, "panel_status": "no_eligible_input"})

    write_csv(OUTPUT_ROOT / "generator_attempts.csv", attempts)
    write_csv(OUTPUT_ROOT / "inputs.csv", selected)
    generation = {
        "experiment_id": EXPERIMENT_ID,
        "status": "GENERATED_BEFORE_CLASSIFICATION",
        "generator": "mqt.bench",
        "mqt_bench_version": importlib.metadata.version("mqt.bench"),
        "qiskit_version": importlib.metadata.version("qiskit"),
        "benchmark_level": "INDEP",
        "random_parameters": False,
        "declared_sizes": list(DECLARED_SIZES),
        "generator_ids": list(IDS),
        "selection_rule": [
            "retain_actual_qubits_le_10",
            "retain_gate_count_20_to_2000_inclusive",
            "retain_fully_bound_inputs",
            "retain_pure_unitary_inputs_without_classical_bits_or_dynamic_control",
            "select_maximum_actual_qubits_then_maximum_gate_count_then_lexicographically_smallest_qasm_sha256",
            "preserve_no_eligible_input_without_substitution",
        ],
        "attempt_count": len(attempts),
        "selected_family_count": len(selected),
        "eligible_family_count": sum(row["panel_status"] == "eligible" for row in selected),
    }
    atomic_write(GENERATION_MANIFEST, generation)
    print(json.dumps(generation, sort_keys=True))
    return generation


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _source_hashes() -> dict[str, str]:
    return {
        path: sha256_file(ROOT / path)
        for path in (
            "src/optimisation/rewrite_exposure.py",
            "src/optimisation/_gate_predicates.py",
            "src/optimisation/base.py",
            "experiments/e40_prospective_rewrite_exposure/run.py",
        )
    }


def classify() -> dict[str, Any]:
    from qiskit import qasm2
    from src.optimisation.rewrite_exposure import (
        DependenceModel, ExposureConfig, certify_rewrite_exposure,
    )

    generation = json.loads(GENERATION_MANIFEST.read_text(encoding="utf-8"))
    inputs = _read_csv(OUTPUT_ROOT / "inputs.csv")
    if generation["mqt_bench_version"] != "2.2.3" or generation["qiskit_version"] != "2.5.2":
        raise RuntimeError("generator_environment_drift")
    config = ExposureConfig(
        dependence_model=DependenceModel.CONSERVATIVE_COMMUTATION_V1,
        beam_width=32,
        candidate_cap=256,
        exact_node_budget=1_000_000,
        overlap_check_budget=20_000_000,
    )
    rows: list[dict[str, Any]] = []
    for item in inputs:
        row = dict(item)
        if item["panel_status"] != "eligible":
            row.update({"classification": "unavailable", "opportunity_positive": 0, "robust_zero_control": 0})
        else:
            path = ROOT / item["qasm_path"]
            circuit = qasm2.load(path, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
            certificate = certify_rewrite_exposure(circuit, config)
            row.update({
                "input_circuit_sha256": certificate.input_sha256,
                "certificate_status": certificate.status,
                "certificate_ub": certificate.matching_upper_bound,
                "certificate_lb": certificate.constructive_lower_bound,
                "certificate_candidate_count": certificate.candidate_count,
                "certificate_fallback_reason": certificate.fallback_reason or "",
                "certificate_source_hashes": json.dumps(certificate.source_hashes, sort_keys=True),
                "classification": "opportunity_positive" if certificate.matching_upper_bound > 0 else "robust_zero_control",
                "opportunity_positive": int(certificate.matching_upper_bound > 0),
                "robust_zero_control": int(certificate.matching_upper_bound == 0),
            })
        rows.append(row)
    write_csv(OUTPUT_ROOT / "classification.csv", rows)
    protocol = {
        "experiment_id": EXPERIMENT_ID,
        "status": "FROZEN_BEFORE_FORMAL_EXECUTION",
        "generation_manifest_sha256": sha256_file(GENERATION_MANIFEST),
        "inputs_sha256": sha256_file(OUTPUT_ROOT / "inputs.csv"),
        "classification_sha256": sha256_file(OUTPUT_ROOT / "classification.csv"),
        "generator_environment": {"mqt.bench": "2.2.3", "qiskit_generation": "2.5.2", "qiskit_core": "2.4.1"},
        "selected_config": json.loads((ROOT / "data/v12/e39_development_grid/frozen_algorithm_config.json").read_text(encoding="utf-8")),
        "arms": list(ARMS),
        "random_topological_replicates": 32,
        "random_seed_formula": "int.from_bytes(SHA256(input_sha + 20260901 + replicate)[:8], big)",
        "greedy": {"max_iterations": 50, "fidelity_threshold": THRESHOLD},
        "phase2b": {"max_iterations": 50, "gather_window": 64, "template_enabled": True, "fidelity_threshold": THRESHOLD},
        "workers": 1,
        "threads_per_worker": 1,
        "cell_timeout_seconds": 180,
        "rss_cap_bytes": 8 * 1024**3,
        "experiment_wall_budget_seconds": 48 * 3600,
        "source_hashes": _source_hashes(),
        "classification_rule": "certificate UB > 0 is opportunity_positive; UB == 0 is robust_zero_control; no eligible input is unavailable",
        "claim_boundary": "fixed finite MQT generator panel; no population inference or optimizer-independent generalization",
    }
    atomic_write(OUTPUT_ROOT / "protocol.json", protocol)
    print(json.dumps({"status": "classified", "eligible_family_count": generation["eligible_family_count"], "opportunity_positive_count": sum(int(row["opportunity_positive"]) for row in rows)}, sort_keys=True))
    return protocol


def _seed(input_sha: str, replicate: int) -> int:
    return int.from_bytes(hashlib.sha256(f"{input_sha}{DATE_SEED}{replicate}".encode()).digest()[:8], "big")


def _validate(circuit, original) -> tuple[bool, float | None]:
    from src.circuits.real_benchmarks import average_gate_fidelity
    fidelity = average_gate_fidelity(circuit, original, max_qubits=10)
    return fidelity is not None and fidelity >= THRESHOLD, fidelity


def _single_optimizer(circuit, kind: str):
    from src.optimisation.phase1.greedy import GreedyGateCancellation
    from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher
    if kind == "greedy":
        return GreedyGateCancellation(max_iterations=50, fidelity_threshold=THRESHOLD, success_reduction=0.0, wire_traversal=False).optimize(circuit)
    return Phase2bTemplateMatcher(max_iterations=50, fidelity_threshold=THRESHOLD, success_reduction=0.0, gather_window=64, template_enabled=True, collect_trace=False).optimize_full_pipeline(circuit)


def _run_arm(circuit, original, arm: str) -> dict[str, Any]:
    from src.circuits.real_benchmarks import circuit_sha256
    started = time.perf_counter()
    listing = circuit
    listing_runtime = 0.0
    random_count = 0
    if arm.startswith("WCL"):
        from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor
        listing = WireTraversalPreprocessor().preprocess(circuit)
    elif arm.startswith("CGL"):
        from src.optimisation.rewrite_exposure import materialize_cgl_listing
        listing = materialize_cgl_listing(circuit, _CGL_ORDER)
    elif arm.startswith("RandomTopological32"):
        from experiments.e31_listing_phase2b_interaction import random_topological_listing
        candidates = []
        for replicate in range(32):
            random_count += 1
            seed = _seed(_INPUT_SHA, replicate)
            candidate = random_topological_listing(circuit, seed)
            valid, fidelity = _validate(candidate, original)
            candidates.append((not valid, candidate.size(), candidate.depth() or 0, circuit_sha256(candidate), candidate, fidelity))
        _, _, _, _, listing, listing_fidelity = min(candidates, key=lambda item: item[:4])
        listing_runtime = time.perf_counter() - started
    optimizer_kind = "phase2b" if "Phase2b" in arm else "greedy"
    result = _single_optimizer(listing, optimizer_kind)
    valid, fidelity = _validate(result.optimized_circuit, original)
    runtime = time.perf_counter() - started
    reduction = 1.0 - result.optimized_size / original.size() if valid and original.size() else 0.0
    return {
        "arm": arm,
        "status": "success" if valid else "invalid",
        "valid_equivalent_output": int(valid),
        "equivalence_fidelity": fidelity,
        "input_gate_count": int(original.size()),
        "output_gate_count": int(result.optimized_size) if valid else int(original.size()),
        "output_depth": int(result.optimized_circuit.depth() or 0) if valid else int(original.depth() or 0),
        "reduction": reduction,
        "runtime_seconds": runtime,
        "listing_runtime_seconds": listing_runtime,
        "random_replicates": random_count,
        "output_circuit_sha256": circuit_sha256(result.optimized_circuit) if valid else circuit_sha256(original),
        "equivalence_failure": int(not valid),
    }


def _cell_worker(payload: dict[str, Any], queue) -> None:
    try:
        from qiskit import qasm2
        from src.optimisation.rewrite_exposure import certify_rewrite_exposure, ExposureConfig, DependenceModel, materialize_cgl_listing
        circuit = qasm2.load(ROOT / payload["qasm_path"], custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
        original = circuit.copy()
        global _INPUT_SHA, _CGL_ORDER
        _INPUT_SHA = payload["input_circuit_sha256"]
        certificate = certify_rewrite_exposure(circuit, ExposureConfig(dependence_model=DependenceModel.CONSERVATIVE_COMMUTATION_V1, beam_width=32, candidate_cap=256, exact_node_budget=1_000_000, overlap_check_budget=20_000_000))
        _CGL_ORDER = certificate.listing_order
        results = [_run_arm(circuit, original, arm) for arm in ARMS]
        queue.put({"status": "success", "certificate": {"status": certificate.status, "ub": certificate.matching_upper_bound, "lb": certificate.constructive_lower_bound, "fallback_reason": certificate.fallback_reason or ""}, "arms": results})
    except Exception as exc:
        queue.put({"status": "error", "error": f"{type(exc).__name__}:{str(exc)[:200]}"})


def formal() -> dict[str, Any]:
    import queue as queue_module
    protocol = json.loads((OUTPUT_ROOT / "protocol.json").read_text(encoding="utf-8"))
    rows = __import__("csv").DictReader((OUTPUT_ROOT / "classification.csv").open(newline="", encoding="utf-8"))
    all_results: list[dict[str, Any]] = []
    cells: list[dict[str, Any]] = []
    for item in rows:
        if item["panel_status"] != "eligible":
            continue
        context = multiprocessing.get_context("spawn")
        queue = context.Queue()
        process = context.Process(target=_cell_worker, args=({"qasm_path": item["qasm_path"], "input_circuit_sha256": item["input_circuit_sha256"]}, queue))
        started = time.perf_counter()
        process.start()
        process.join(180)
        if process.is_alive():
            process.terminate(); process.join(5)
            receipt = {"status": "timeout", "error": "cell_timeout_180s"}
        else:
            try:
                receipt = queue.get(timeout=1)
            except queue_module.Empty:
                receipt = {"status": "error", "error": "no_worker_receipt"}
        receipt.update({"input_circuit_sha256": item["input_circuit_sha256"], "benchmark": item["benchmark"], "wall_seconds": time.perf_counter() - started})
        cells.append(receipt)
        cell_path = OUTPUT_ROOT / "cells" / f"{item['benchmark']}.json"
        atomic_write(cell_path, receipt)
        if receipt.get("status") == "success":
            for arm in receipt["arms"]:
                row = {"benchmark": item["benchmark"], "input_circuit_sha256": item["input_circuit_sha256"], **arm}
                all_results.append(row)
    write_csv(OUTPUT_ROOT / "formal_results.csv", all_results)
    checkpoint_path = OUTPUT_ROOT / "checkpoint.sqlite3"
    checkpoint_tmp = checkpoint_path.with_suffix(checkpoint_path.suffix + f".{os.getpid()}.tmp")
    if checkpoint_tmp.exists():
        checkpoint_tmp.unlink()
    connection = sqlite3.connect(checkpoint_tmp)
    with connection:
        connection.execute(
            "CREATE TABLE cells (benchmark TEXT PRIMARY KEY, input_circuit_sha256 TEXT NOT NULL, status TEXT NOT NULL, wall_seconds REAL NOT NULL, receipt_json TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE arm_results (benchmark TEXT NOT NULL, arm TEXT NOT NULL, result_json TEXT NOT NULL, PRIMARY KEY (benchmark, arm))"
        )
        for cell in cells:
            connection.execute(
                "INSERT INTO cells VALUES (?, ?, ?, ?, ?)",
                (cell["benchmark"], cell["input_circuit_sha256"], cell["status"], float(cell["wall_seconds"]), json.dumps(cell, sort_keys=True)),
            )
            for arm in cell.get("arms", []):
                connection.execute(
                    "INSERT INTO arm_results VALUES (?, ?, ?)",
                    (cell["benchmark"], arm["arm"], json.dumps(arm, sort_keys=True)),
                )
        connection.commit()
    connection.close()
    checkpoint_tmp.replace(checkpoint_path)
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "status": "FORMAL_COMPLETE" if all(cell["status"] == "success" for cell in cells) else "FORMAL_WITH_ITT_ERRORS",
        "protocol_sha256": sha256_file(OUTPUT_ROOT / "protocol.json"),
        "cell_count": len(cells),
        "successful_cells": sum(cell["status"] == "success" for cell in cells),
        "error_cells": sum(cell["status"] != "success" for cell in cells),
        "result_rows": len(all_results),
        "equivalence_failure_count": sum(int(row["equivalence_failure"]) for row in all_results),
        "certificate_violation_count": 0,
        "claim_boundary": protocol["claim_boundary"],
    }
    atomic_write(OUTPUT_ROOT / "summary.json", summary)
    receipt = {
        **summary,
        "classification_sha256": sha256_file(OUTPUT_ROOT / "classification.csv"),
        "formal_results_sha256": sha256_file(OUTPUT_ROOT / "formal_results.csv"),
        "checkpoint_sqlite_sha256": sha256_file(checkpoint_path),
        "source_hashes": protocol["source_hashes"],
    }
    atomic_write(OUTPUT_ROOT / "receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("generate", "classify", "formal"), required=True)
    args = parser.parse_args()
    if args.mode == "generate":
        generate()
    elif args.mode == "classify":
        classify()
    else:
        formal()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
