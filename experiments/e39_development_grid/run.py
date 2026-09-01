"""Run and select the preregistered E39 CGL development configuration.

Only the frozen 391-input E31 development set is used.  The six main
configurations vary beam width and candidate cap under the conservative
commutation model.  E39 selects an algorithmic configuration; it is not a
confirmatory result.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing
import os
import queue as queue_module
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from qiskit import QuantumCircuit

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor
from src.optimisation.rewrite_exposure import (
    DependenceModel,
    ExposureConfig,
    _certify_prepared,
    _prepare_exposure,
    materialize_cgl_listing,
)


EXPERIMENT_ID = "E39_DEVELOPMENT_GRID_V1"
SOURCE_MANIFEST = REPO_ROOT / "data" / "v11" / "e31_factorial_pareto" / "design_manifest.csv"
SOURCE_METADATA = REPO_ROOT / "data" / "v11" / "e31_factorial_pareto" / "design_metadata.json"
OUTPUT_ROOT = REPO_ROOT / "data" / "v12" / "e39_development_grid"
FIDELITY_THRESHOLD = 0.9999999999
CONFIGS = [
    {"config_id": f"b{beam}_c{cap}", "beam_width": beam, "candidate_cap": cap}
    for cap in (64, 256)
    for beam in (1, 8, 32)
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_unique_inputs() -> list[dict[str, str]]:
    seen: dict[str, dict[str, str]] = {}
    with SOURCE_MANIFEST.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            seen.setdefault(row["input_circuit_sha256"], row)
    inputs = list(seen.values())
    if len(inputs) != 391:
        raise RuntimeError(f"expected_391_unique_inputs:{len(inputs)}")
    if len({row["circuit_family"] for row in inputs}) != 15:
        raise RuntimeError("expected_15_input_families")
    return inputs


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        atomic_write(path, "")
        return
    fields = list(rows[0])
    lines = []
    import io
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(path, buffer.getvalue())


def protocol_payload(inputs: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "status": "DEVELOPMENT_ONLY",
        "source_manifest": str(SOURCE_MANIFEST.relative_to(REPO_ROOT)).replace("\\", "/"),
        "source_manifest_sha256": sha256_file(SOURCE_MANIFEST),
        "source_metadata": str(SOURCE_METADATA.relative_to(REPO_ROOT)).replace("\\", "/"),
        "source_metadata_sha256": sha256_file(SOURCE_METADATA),
        "unique_input_count": len(inputs),
        "family_count": len({row["circuit_family"] for row in inputs}),
        "dependence_model_main": DependenceModel.CONSERVATIVE_COMMUTATION_V1.value,
        "dependence_model_ablation": DependenceModel.WIRE_ORDER_V1.value,
        "beam_width_grid": [1, 8, 32],
        "candidate_cap_grid": [64, 256],
        "exact_candidate_limit": 24,
        "exact_node_budget": 1_000_000,
        "overlap_check_budget": 20_000_000,
        "downstream_optimizer": "GreedyGateCancellation(max_iterations=50)",
        "fidelity_threshold": FIDELITY_THRESHOLD,
        "workers": 1,
        "cell_timeout_seconds": 60,
        "selection_rule": [
            "leave_one_family_out_effects_are_reported",
            "maximize_complete_development_input_mean_effect_pp",
            "retain_configs_within_0.25_pp_of_best",
            "choose_lowest_median_cgl_total_runtime",
            "tie_break_beam_width_then_candidate_cap_ascending",
        ],
        "configurations": CONFIGS,
    }


def run_one(circuit: QuantumCircuit, prepared, config: dict[str, Any]) -> dict[str, Any]:
    exposure_config = ExposureConfig(
        dependence_model=DependenceModel.CONSERVATIVE_COMMUTATION_V1,
        beam_width=config["beam_width"],
        candidate_cap=config["candidate_cap"],
        exact_node_budget=1_000_000,
        overlap_check_budget=20_000_000,
    )
    started = time.perf_counter()
    certificate = _certify_prepared(circuit, exposure_config, prepared)
    certificate_seconds = time.perf_counter() - started
    cgl_input = materialize_cgl_listing(circuit, certificate.listing_order)
    optimizer = GreedyGateCancellation(
        max_iterations=50,
        fidelity_threshold=FIDELITY_THRESHOLD,
        success_reduction=0.0,
        wire_traversal=False,
    )
    started = time.perf_counter()
    result = optimizer.optimize(cgl_input)
    greedy_seconds = time.perf_counter() - started
    original_size = circuit.size()
    reduction = (
        1.0 - result.optimized_size / original_size
        if original_size else 0.0
    )
    return {
        "config_id": config["config_id"],
        "beam_width": config["beam_width"],
        "candidate_cap": config["candidate_cap"],
        "status": "success",
        "certificate_status": certificate.status,
        "certificate_ub": certificate.matching_upper_bound,
        "certificate_lb": certificate.constructive_lower_bound,
        "certificate_candidate_count": certificate.candidate_count,
        "certificate_discarded_candidate_count": certificate.discarded_candidate_count,
        "certificate_fallback_reason": certificate.fallback_reason or "",
        "certificate_seconds": certificate_seconds,
        "greedy_seconds": greedy_seconds,
        "cgl_total_seconds": certificate_seconds + greedy_seconds,
        "input_gate_count": original_size,
        "output_gate_count": result.optimized_size,
        "reduction": reduction,
        "equivalence_evidence": "not_run_in_development_grid",
    }


def error_row(circuit: QuantumCircuit, config: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "config_id": config["config_id"],
        "beam_width": config["beam_width"],
        "candidate_cap": config["candidate_cap"],
        "status": reason,
        "certificate_status": "unavailable",
        "certificate_ub": 0,
        "certificate_lb": 0,
        "certificate_candidate_count": 0,
        "certificate_discarded_candidate_count": 0,
        "certificate_fallback_reason": "",
        "certificate_seconds": 0.0,
        "greedy_seconds": 0.0,
        "cgl_total_seconds": 0.0,
        "input_gate_count": circuit.size(),
        "output_gate_count": circuit.size(),
        "reduction": 0.0,
        "equivalence_evidence": "not_run_in_development_grid",
    }


def _isolated_cell_worker(
    qasm_path: str,
    config: dict[str, Any],
    queue,
) -> None:
    try:
        circuit = QuantumCircuit.from_qasm_file(qasm_path)
        preparation_config = ExposureConfig(
            dependence_model=DependenceModel.CONSERVATIVE_COMMUTATION_V1,
            candidate_cap=256,
            beam_width=8,
        )
        prepared = _prepare_exposure(circuit, preparation_config)
        queue.put(run_one(circuit, prepared, config))
    except Exception as exc:  # pragma: no cover - exercised by cell guard
        queue.put({"error": f"error:{type(exc).__name__}"})


def run_config_cell(
    circuit: QuantumCircuit,
    qasm_path: str,
    prepared,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Run a heavy cell in a cold process with the registered 60s limit."""
    estimated_work = (
        len(prepared.ranked_candidates)
        * config["beam_width"]
        * max(1, len(circuit.data))
    )
    if estimated_work <= 1_000_000:
        return run_one(circuit, prepared, config)
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    process = context.Process(
        target=_isolated_cell_worker,
        args=(qasm_path, config, queue),
    )
    process.start()
    process.join(60)
    if process.is_alive():
        process.terminate()
        process.join(5)
        return error_row(circuit, config, "timeout:cell_timeout_60s")
    try:
        result = queue.get(timeout=1)
    except queue_module.Empty:
        return error_row(circuit, config, "error:isolated_cell_no_receipt")
    if "error" not in result:
        return result
    return error_row(circuit, config, result["error"])


def run(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    inputs = load_unique_inputs()
    protocol = protocol_payload(inputs)
    atomic_write(output_root / "protocol.json", json.dumps(protocol, indent=2, sort_keys=True) + "\n")
    write_csv(output_root / "inputs.csv", inputs)
    all_rows: list[dict[str, Any]] = []
    baseline_rows: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(inputs, start=1):
        print(f"starting {index}/{len(inputs)} {source['circuit_id']}", flush=True)
        circuit = QuantumCircuit.from_qasm_file(str(REPO_ROOT / source["qasm_path"]))
        source_hash = source["input_circuit_sha256"]
        wcl_started = time.perf_counter()
        wcl_circuit = WireTraversalPreprocessor().preprocess(circuit)
        wcl_prepare_seconds = time.perf_counter() - wcl_started
        optimizer = GreedyGateCancellation(
            max_iterations=50,
            fidelity_threshold=FIDELITY_THRESHOLD,
            success_reduction=0.0,
            wire_traversal=False,
        )
        wcl_started = time.perf_counter()
        wcl_result = optimizer.optimize(wcl_circuit)
        wcl_greedy_seconds = time.perf_counter() - wcl_started
        original_size = circuit.size()
        wcl_reduction = 1.0 - wcl_result.optimized_size / original_size if original_size else 0.0
        baseline_rows[source_hash] = {
            "input_circuit_sha256": source_hash,
            "circuit_id": source["circuit_id"],
            "circuit_family": source["circuit_family"],
            "n_qubits": source["n_qubits"],
            "input_gate_count": original_size,
            "wcl_output_gate_count": wcl_result.optimized_size,
            "wcl_reduction": wcl_reduction,
            "wcl_total_seconds": wcl_prepare_seconds + wcl_greedy_seconds,
        }
        preparation_config = ExposureConfig(
            dependence_model=DependenceModel.CONSERVATIVE_COMMUTATION_V1,
            candidate_cap=256,
            beam_width=8,
        )
        prepared = _prepare_exposure(circuit, preparation_config)
        for config in CONFIGS:
            try:
                row = run_config_cell(
                    circuit,
                    str(REPO_ROOT / source["qasm_path"]),
                    prepared,
                    config,
                )
            except Exception as exc:  # ITT: error reduction is defined as zero
                row = error_row(circuit, config, f"error:{type(exc).__name__}")
            row.update(baseline_rows[source_hash])
            row["input_circuit_sha256"] = source_hash
            row["circuit_id"] = source["circuit_id"]
            row["circuit_family"] = source["circuit_family"]
            row["n_qubits"] = source["n_qubits"]
            row["effect_pp"] = 100.0 * (float(row["reduction"]) - wcl_reduction)
            row["opportunity_positive"] = int(int(row["certificate_ub"]) > 0)
            all_rows.append(row)
        if index % 10 == 0:
            print(f"evaluated {index}/{len(inputs)} inputs", flush=True)

    write_csv(output_root / "grid_results.csv", all_rows)
    baseline_list = list(baseline_rows.values())
    write_csv(output_root / "wcl_baseline.csv", baseline_list)

    loo_rows: list[dict[str, Any]] = []
    for config in CONFIGS:
        config_rows = [row for row in all_rows if row["config_id"] == config["config_id"]]
        complete_effect = statistics.fmean(float(row["effect_pp"]) for row in config_rows)
        median_runtime = statistics.median(float(row["cgl_total_seconds"]) for row in config_rows)
        for family in sorted({row["circuit_family"] for row in config_rows}):
            held_in = [row for row in config_rows if row["circuit_family"] != family]
            loo_rows.append({
                "config_id": config["config_id"],
                "beam_width": config["beam_width"],
                "candidate_cap": config["candidate_cap"],
                "left_out_family": family,
                "left_out_input_count": len(held_in),
                "loo_mean_effect_pp": statistics.fmean(float(row["effect_pp"]) for row in held_in),
                "complete_mean_effect_pp": complete_effect,
                "median_cgl_total_seconds": median_runtime,
            })
    write_csv(output_root / "leave_one_family_out.csv", loo_rows)

    summaries = []
    for config in CONFIGS:
        config_rows = [row for row in all_rows if row["config_id"] == config["config_id"]]
        summaries.append({
            **config,
            "input_count": len(config_rows),
            "error_count": sum(not str(row["status"]).startswith("success") for row in config_rows),
            "opportunity_positive_count": sum(int(row["opportunity_positive"]) for row in config_rows),
            "complete_mean_effect_pp": statistics.fmean(float(row["effect_pp"]) for row in config_rows),
            "median_effect_pp": statistics.median(float(row["effect_pp"]) for row in config_rows),
            "median_cgl_total_seconds": statistics.median(float(row["cgl_total_seconds"]) for row in config_rows),
        })
    best_effect = max(row["complete_mean_effect_pp"] for row in summaries)
    eligible = [row for row in summaries if row["complete_mean_effect_pp"] >= best_effect - 0.25]
    selected = min(
        eligible,
        key=lambda row: (
            row["median_cgl_total_seconds"], row["beam_width"], row["candidate_cap"]
        ),
    )
    selection = {
        "experiment_id": EXPERIMENT_ID,
        "status": "DEVELOPMENT_ONLY",
        "best_complete_mean_effect_pp": best_effect,
        "effect_tolerance_pp": 0.25,
        "eligible_config_ids": [row["config_id"] for row in eligible],
        "selected_config": selected,
        "selection_is_frozen_for_e40": True,
        "no_e40_result_used": True,
    }
    atomic_write(output_root / "config_summaries.json", json.dumps(summaries, indent=2, sort_keys=True) + "\n")
    atomic_write(output_root / "selection.json", json.dumps(selection, indent=2, sort_keys=True) + "\n")
    frozen_config = {
        "experiment_id": EXPERIMENT_ID,
        "status": "FROZEN_FOR_E40",
        "selected_config": selected,
        "selected_config_id": selected["config_id"],
        "dependence_model": DependenceModel.CONSERVATIVE_COMMUTATION_V1.value,
        "rule_library": "pair_v1",
        "candidate_cap": int(selected["candidate_cap"]),
        "beam_width": int(selected["beam_width"]),
        "exact_candidate_limit": 24,
        "exact_node_budget": 1_000_000,
        "overlap_check_budget": 20_000_000,
        "fidelity_threshold": FIDELITY_THRESHOLD,
        "downstream_optimizer": "GreedyGateCancellation(max_iterations=50)",
        "source_module": "src/optimisation/rewrite_exposure.py",
        "source_module_sha256": sha256_file(REPO_ROOT / "src" / "optimisation" / "rewrite_exposure.py"),
        "selection_rule": protocol["selection_rule"],
        "no_e40_result_used": True,
    }
    atomic_write(output_root / "frozen_algorithm_config.json", json.dumps(frozen_config, indent=2, sort_keys=True) + "\n")
    receipt = {
        "status": "verified_development_grid",
        "experiment_id": EXPERIMENT_ID,
        "protocol_sha256": sha256_file(output_root / "protocol.json"),
        "inputs_sha256": sha256_file(output_root / "inputs.csv"),
        "grid_results_sha256": sha256_file(output_root / "grid_results.csv"),
        "leave_one_family_out_sha256": sha256_file(output_root / "leave_one_family_out.csv"),
        "frozen_algorithm_config_sha256": sha256_file(output_root / "frozen_algorithm_config.json"),
        "input_count": len(inputs),
        "family_count": len({row["circuit_family"] for row in inputs}),
        "configuration_count": len(CONFIGS),
        "result_rows": len(all_rows),
        "selection": selection,
    }
    atomic_write(output_root / "receipt.json", json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    receipt = run(args.output_root)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
