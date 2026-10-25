"""Run the selected v14 E45 configuration with the compact exact engine.

The screening grid remains immutable.  This entrypoint writes a separate
full-development package for the same fixed 128-source panel and records an
exact finite-horizon certificate when the state/time budget is complete.  A
truncated cell remains explicitly incomplete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from qiskit import qasm2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e45_development_grid.run import (
    ARM_NAMES,
    E39_INPUTS,
    E44_INPUTS,
    EXPERIMENT_ID,
    MAX_BASELINE_GATES,
    RULE_LIBRARY,
    beam_search,
    circuit_from_row,
    load_e39_rows,
    load_e44_rows,
    normalize_circuit,
    run_baseline_arms,
    select_screening,
    state_from_circuit,
)
from src.optimisation.certified_landscape import search_landscape_horizons_compact


OUTPUT_ROOT = ROOT / "data" / "v14" / "e45_full_development"
SCREENING_MANIFEST = ROOT / "data" / "v14" / "e45_development_grid" / "normalization_manifest.csv"
RULE_SCOPE = "e44_core_v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        atomic_text(path, "")
        return
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(path, buffer.getvalue())


def fixed_panel() -> list[dict[str, Any]]:
    all_sources = load_e39_rows() + load_e44_rows()
    sources = select_screening([row for row in all_sources if row["source_kind"] == "e39"], 96)
    e44 = [row for row in all_sources if row["source_kind"] == "e44"]
    sources.extend(sorted(e44, key=lambda row: row["source_id"])[:32])
    return sources


def result_row(
    source: dict[str, Any],
    config: dict[str, Any],
    arm: str,
    original_count: int,
    output_count: int,
    runtime: float,
    status: str,
    semantic_status: str,
    certificate: dict[str, Any] | None = None,
    reason: str = "",
) -> dict[str, Any]:
    reduction = 1.0 - output_count / original_count if original_count else 0.0
    return {
        "experiment_id": EXPERIMENT_ID,
        "source_id": source["source_id"],
        "source_kind": source["source_kind"],
        "circuit_id": source["circuit_id"],
        "circuit_family": source["circuit_family"],
        "n_qubits": source["n_qubits"],
        "input_circuit_sha256": source["normalized_sha256"],
        "config_id": config["config_id"],
        "horizon": config["horizon"],
        "beam_width": config["beam_width"],
        "state_budget": config["state_budget"],
        "barrier_cap": config["barrier_cap"],
        "arm": arm,
        "status": status,
        "semantic_status": semantic_status,
        "resource_reason": reason,
        "input_gate_count": original_count,
        "output_gate_count": int(output_count),
        "reduction": reduction,
        "reduction_pp": 100.0 * reduction,
        "runtime_seconds": runtime,
        "states_seen": certificate.get("states_seen", 0) if certificate else 0,
        "expanded": certificate.get("expanded", 0) if certificate else 0,
        "pruned": certificate.get("pruned", 0) if certificate else 0,
        "escape_depth": certificate.get("escape_depth") if certificate else "",
        "barrier_height": certificate.get("barrier_height") if certificate else "",
        "exposure_calls": 0,
        "certificate_status": certificate.get("status", "NOT_APPLICABLE") if certificate else "NOT_APPLICABLE",
        "witness_step_count": len(certificate.get("witnesses", {}).get("escape", [])) if certificate else 0,
    }


def selected_config() -> dict[str, Any]:
    selection_path = ROOT / "data" / "v14" / "e45_development_grid" / "selection.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    selected = selection.get("selected_config")
    required = ("config_id", "horizon", "beam_width", "state_budget", "barrier_cap")
    if (
        not isinstance(selected, dict)
        or selected.get("arm") != "certificate_guided_escape"
        or selection.get("eligible_config_count", 0) < 1
        or any(key not in selected for key in required)
    ):
        raise RuntimeError("selected_config_missing_from_screening_choice")
    return {
        key: selected[key]
        for key in required
    }


def run(output_root: Path = OUTPUT_ROOT, time_budget_seconds: float = 30.0, source_limit: int | None = None) -> dict[str, Any]:
    config = selected_config()
    sources = fixed_panel()
    output_root = output_root.resolve()
    if source_limit is not None:
        if source_limit < 1 or source_limit > len(sources):
            raise ValueError("source_limit_out_of_range")
        sources = sources[:source_limit]
    output_root.mkdir(parents=True, exist_ok=True)
    qasm_dir = output_root / "qasm"
    prepared: list[tuple[dict[str, Any], Any]] = []
    manifest: list[dict[str, Any]] = []
    for index, source in enumerate(sources, start=1):
        raw = circuit_from_row(source)
        normalized, metadata = normalize_circuit(raw)
        if normalized is None:
            raise RuntimeError(f"unsupported_fixed_panel_input:{source['source_id']}")
        payload = qasm2.dumps(normalized)
        normalized_path = qasm_dir / f"{index:04d}_{source['source_kind']}_{source['circuit_id']}_{hashlib.sha256(payload.encode()).hexdigest()[:12]}.qasm"
        atomic_text(normalized_path, payload)
        source["normalized_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
        source["normalized_path"] = normalized_path.relative_to(ROOT).as_posix()
        manifest.append({
            key: source[key]
            for key in ("source_id", "source_kind", "circuit_id", "circuit_family", "n_qubits", "source_path", "source_sha256")
        } | metadata | {
            "normalized_path": source["normalized_path"],
            "normalized_sha256": source["normalized_sha256"],
        })
        prepared.append((source, normalized))
    write_csv(output_root / "normalization_manifest.csv", manifest)

    rows: list[dict[str, Any]] = []
    certificates: list[dict[str, Any]] = []
    for index, (source, circuit) in enumerate(prepared, start=1):
        original_count = int(circuit.size())
        if original_count > MAX_BASELINE_GATES:
            baselines = {
                arm: (circuit, 0.0, "RESOURCE_BOUNDED_NO_WITNESS:baseline_gate_budget")
                for arm in ("greedy", "wcl_greedy", "v12_cgl_greedy", "phase2b_greedy")
            }
        else:
            baselines = run_baseline_arms(circuit)
        for arm in ("greedy", "wcl_greedy", "v12_cgl_greedy", "phase2b_greedy"):
            output, runtime, semantic = baselines[arm]
            status = "RESOURCE_BOUNDED_NO_WITNESS" if semantic.startswith("RESOURCE_BOUNDED") else "SUCCESS"
            rows.append(result_row(source, config, arm, original_count, int(output.size()), runtime, status, semantic, reason=semantic if status.startswith("RESOURCE") else ""))

        root_state = state_from_circuit(baselines["greedy"][0])
        started = time.perf_counter()
        beam = beam_search(root_state, RULE_LIBRARY, config, False)
        rows.append(result_row(source, config, "unguided_beam", original_count, beam.state.cost, time.perf_counter() - started, beam.status, beam.semantic_status, {
            "status": beam.status,
            "states_seen": beam.states_seen,
            "expanded": beam.expanded,
            "pruned": beam.pruned,
            "escape_depth": beam.escape_depth,
            "barrier_height": beam.barrier_height,
            "witnesses": {"escape": [action.to_dict() for action in beam.path]},
        }, beam.resource_reason))

        started = time.perf_counter()
        exact = search_landscape_horizons_compact(
            root_state,
            RULE_LIBRARY,
            (int(config["horizon"]),),
            state_budget=int(config["state_budget"]),
            rule_scope=RULE_SCOPE,
            time_budget_seconds=time_budget_seconds,
        )[str(config["horizon"])]
        rows.append(result_row(source, config, "certificate_guided_escape", original_count, exact["best_cost"], time.perf_counter() - started, exact["status"], exact["semantic_status"], exact, exact.get("resource_reason", "")))
        certificates.append({
            "source_id": source["source_id"],
            "source_sha256": source["source_sha256"],
            "normalized_sha256": source["normalized_sha256"],
            "config_id": config["config_id"],
            "certificate": exact,
        })
        if index % 8 == 0:
            print(f"exact development {index}/{len(prepared)}", flush=True)
    write_csv(output_root / "grid_results.csv", rows)
    atomic_text(output_root / "certificates.jsonl", "".join(json.dumps(item, sort_keys=True) + "\n" for item in certificates))

    summaries: list[dict[str, Any]] = []
    for arm in ARM_NAMES:
        selected = [row for row in rows if row["arm"] == arm]
        valid = [row for row in selected if row["status"] in {"SUCCESS", "WITNESS_CERTIFIED_SEARCH_INCOMPLETE", "EXACT_ESCAPE", "EXACT_H_LOCAL_OPTIMUM", "RESOURCE_BOUNDED_NO_WITNESS"}]
        resource_or_error = {"WITNESS_CERTIFIED_SEARCH_INCOMPLETE", "RESOURCE_BOUNDED_NO_WITNESS", "ERROR"}
        summaries.append({
            **config,
            "arm": arm,
            "row_count": len(selected),
            "valid_row_count": len(valid),
            "semantic_failure_count": sum(row["semantic_status"] in {"SEMANTIC_FAILURE", "NOT_AVAILABLE"} for row in selected),
            "resource_bounded_count": sum(row["status"] in resource_or_error for row in selected),
            "resource_or_error_rate": sum(row["status"] in resource_or_error for row in selected) / len(selected) if selected else 1.0,
            "family_mean_paired_itt_pp": statistics.fmean(float(row["reduction_pp"]) for row in valid) if valid else 0.0,
            "median_runtime_seconds": statistics.median(float(row["runtime_seconds"]) for row in selected) if selected else float("inf"),
            "p95_runtime_seconds": sorted(float(row["runtime_seconds"]) for row in selected)[max(0, int(0.95 * len(selected) + 0.999999) - 1)] if selected else float("inf"),
        })
    atomic_text(output_root / "config_summaries.json", json.dumps(summaries, indent=2, sort_keys=True) + "\n")
    exact_rows = [row for row in summaries if row["arm"] == "certificate_guided_escape"]
    exact_summary = exact_rows[0]
    status = "DEVELOPMENT_COMPLETE" if exact_summary["resource_or_error_rate"] == 0 and exact_summary["semantic_failure_count"] == 0 else "DEVELOPMENT_COMPLETE_WITH_RESOURCE_BOUNDARY"
    selection = {
        "experiment_id": EXPERIMENT_ID,
        "phase": "full_development" if source_limit is None else "smoke",
        "status": status,
        "source_count": len(sources),
        "configuration_count": 1,
        "selected_config": config,
        "selection_is_frozen_for_e48": False,
        "future_panel_access": "E46_AND_LATER_NOT_READ",
    }
    atomic_text(output_root / "selection.json", json.dumps(selection, indent=2, sort_keys=True) + "\n")
    protocol = {
        "experiment_id": EXPERIMENT_ID,
        "status": "DEVELOPMENT_ONLY",
        "phase": selection["phase"],
        "source_contract": {
            "screening_manifest": SCREENING_MANIFEST.relative_to(ROOT).as_posix(),
            "screening_manifest_sha256": sha256(SCREENING_MANIFEST),
            "source_count": len(sources),
            "fixed_panel": "same 128-source v14 screening order" if source_limit is None else f"prefix of same 128-source v14 screening order (limit={source_limit})",
            "e39_path": E39_INPUTS.relative_to(ROOT).as_posix(),
            "e44_path": E44_INPUTS.relative_to(ROOT).as_posix(),
        },
        "configuration_grid": [config],
        "arms": list(ARM_NAMES),
        "rule_scope": RULE_SCOPE,
        "search_method": {
            "id": "exact_compact_bfs_v2",
            "state_key": "complete_ordered_normalized_listing_sha256",
            "barrier_method": "layered_minimax_peak_cost",
            "action_matching": "first_operation_indexed_rule_locations",
            "state_hash_generation": "canonical_byte_splice_with_lazy_child_spans",
            "resource_status": "EXACT only when state and time budgets are complete",
            "reverse_edges": "not used; rank-increasing reverse Quartz parameter-splitting remains illegal",
        },
        "cell_limits": {
            "state_budget": config["state_budget"],
            "time_budget_seconds": time_budget_seconds,
            "baseline_gate_limit": MAX_BASELINE_GATES,
        },
        "future_panel_access": "E46_AND_LATER_NOT_READ",
    }
    atomic_text(output_root / "protocol.json", json.dumps(protocol, indent=2, sort_keys=True) + "\n")
    receipt = {
        "status": status,
        "experiment_id": EXPERIMENT_ID,
        "phase": selection["phase"],
        "protocol_sha256": sha256(output_root / "protocol.json"),
        "normalization_manifest_sha256": sha256(output_root / "normalization_manifest.csv"),
        "grid_results_sha256": sha256(output_root / "grid_results.csv"),
        "config_summaries_sha256": sha256(output_root / "config_summaries.json"),
        "certificates_sha256": sha256(output_root / "certificates.jsonl"),
        "selection_sha256": sha256(output_root / "selection.json"),
        "source_count": len(sources),
        "normalized_count": len(prepared),
        "result_rows": len(rows),
        "configuration_count": 1,
        "arm_count": len(ARM_NAMES),
        "selected_config": config,
        "guided_summary": exact_summary,
    }
    atomic_text(output_root / "receipt.json", json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--time-budget-seconds", type=float, default=30.0)
    parser.add_argument("--source-limit", type=int)
    parser.add_argument("--experiment-id")
    args = parser.parse_args()
    if args.experiment_id:
        globals()["EXPERIMENT_ID"] = args.experiment_id
    print(json.dumps(run(args.output_root, args.time_budget_seconds, args.source_limit), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
