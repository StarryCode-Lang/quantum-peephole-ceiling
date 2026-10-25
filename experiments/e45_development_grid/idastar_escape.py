"""Run the v14 IDA* escape-depth development panel.

This package is complementary to the compact full-landscape package.  It
proves the shortest improving path when the IDA* state/time budget completes;
it does not claim that the complete finite-horizon state set was enumerated.
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

from experiments.e45_development_grid.exact_development import (  # noqa: E402
    RULE_SCOPE,
    atomic_text,
    fixed_panel,
    selected_config,
    write_csv,
)
from experiments.e45_development_grid.run import (  # noqa: E402
    E39_INPUTS,
    E44_INPUTS,
    EXPERIMENT_ID,
    MAX_BASELINE_GATES,
    RULE_LIBRARY,
    circuit_from_row,
    normalize_circuit,
    state_from_circuit,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.certified_landscape import (  # noqa: E402
    replay_actions,
    search_escape_idastar,
)


OUTPUT_ROOT = ROOT / "data" / "v14" / "e45_idastar_escape"
SCREENING_MANIFEST = ROOT / "data" / "v14" / "e45_development_grid" / "normalization_manifest.csv"
EXPERIMENT_ID_IDASTAR = "E45_CERTIFIED_ESCAPE_IDASTAR_V14"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def result_row(
    source: dict[str, Any],
    config: dict[str, Any],
    certificate: dict[str, Any],
    runtime: float,
    replay_status: str,
) -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID_IDASTAR,
        "source_id": source["source_id"],
        "source_kind": source["source_kind"],
        "circuit_id": source["circuit_id"],
        "circuit_family": source["circuit_family"],
        "n_qubits": source["n_qubits"],
        "input_circuit_sha256": source["normalized_sha256"],
        "config_id": config["config_id"],
        "horizon": config["horizon"],
        "state_budget": config["state_budget"],
        "barrier_cap": config["barrier_cap"],
        "arm": "idastar_escape",
        "status": certificate.get("status", "ERROR"),
        "semantic_status": replay_status,
        "resource_reason": certificate.get("resource_reason", ""),
        "baseline_gate_count": certificate.get("baseline_cost", ""),
        "escape_depth": certificate.get("escape_depth", ""),
        "states_seen": certificate.get("states_seen", 0),
        "expanded": certificate.get("expanded", 0),
        "pruned": certificate.get("pruned", 0),
        "depth_iterations": certificate.get("depth_iterations", 0),
        "runtime_seconds": runtime,
        "resource_status": certificate.get("resource_status", ""),
        "exactness_status": certificate.get("exactness_status", ""),
        "witness_step_count": len(certificate.get("witnesses", {}).get("escape", [])),
    }


def run(
    output_root: Path = OUTPUT_ROOT,
    time_budget_seconds: float = 30.0,
    source_limit: int | None = None,
) -> dict[str, Any]:
    config = selected_config()
    sources = fixed_panel()
    if source_limit is not None:
        if source_limit < 1 or source_limit > len(sources):
            raise ValueError("source_limit_out_of_range")
        sources = sources[:source_limit]
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    qasm_dir = output_root / "qasm"
    manifest: list[dict[str, Any]] = []
    prepared: list[tuple[dict[str, Any], Any]] = []
    for index, source in enumerate(sources, start=1):
        raw = circuit_from_row(source)
        normalized, metadata = normalize_circuit(raw)
        if normalized is None:
            raise RuntimeError(f"unsupported_fixed_panel_input:{source['source_id']}")
        payload = qasm2.dumps(normalized)
        normalized_sha256 = hashlib.sha256(payload.encode()).hexdigest()
        normalized_path = qasm_dir / (
            f"{index:04d}_{source['source_kind']}_{source['circuit_id']}_"
            f"{normalized_sha256[:12]}.qasm"
        )
        atomic_text(normalized_path, payload)
        source["normalized_sha256"] = normalized_sha256
        source["normalized_path"] = normalized_path.relative_to(ROOT).as_posix()
        manifest.append(
            {
                key: source[key]
                for key in (
                    "source_id",
                    "source_kind",
                    "circuit_id",
                    "circuit_family",
                    "n_qubits",
                    "source_path",
                    "source_sha256",
                )
            }
            | metadata
            | {
                "normalized_path": source["normalized_path"],
                "normalized_sha256": normalized_sha256,
            }
        )
        prepared.append((source, normalized))
    write_csv(output_root / "normalization_manifest.csv", manifest)

    rows: list[dict[str, Any]] = []
    certificates: list[dict[str, Any]] = []
    for index, (source, circuit) in enumerate(prepared, start=1):
        if circuit.size() > MAX_BASELINE_GATES:
            baseline = circuit
        else:
            baseline = GreedyGateCancellation(
                max_iterations=50,
                fidelity_threshold=1.0,
                success_reduction=0.0,
            ).optimize(circuit).optimized_circuit
        root_state = state_from_circuit(baseline)
        started = time.perf_counter()
        certificate = search_escape_idastar(
            root_state,
            RULE_LIBRARY,
            int(config["horizon"]),
            state_budget=int(config["state_budget"]),
            rule_scope=RULE_SCOPE,
            time_budget_seconds=time_budget_seconds,
        )
        runtime = time.perf_counter() - started
        witness = certificate.get("witnesses", {}).get("escape", [])
        if witness:
            replay = replay_actions(root_state, witness, RULE_LIBRARY, RULE_SCOPE)
            replay_status = "REPLAY_PASS" if replay.get("accepted") else "REPLAY_FAIL"
            if replay_status == "REPLAY_FAIL":
                raise RuntimeError(f"idastar_witness_replay_failed:{source['source_id']}:{replay.get('reason')}")
        else:
            replay_status = "NO_WITNESS"
        rows.append(result_row(source, config, certificate, runtime, replay_status))
        certificates.append(
            {
                "source_id": source["source_id"],
                "source_sha256": source["source_sha256"],
                "normalized_sha256": source["normalized_sha256"],
                "config_id": config["config_id"],
                "certificate": certificate,
                "witness_replay_status": replay_status,
            }
        )
        if index % 8 == 0:
            print(f"idastar escape development {index}/{len(prepared)}", flush=True)

    write_csv(output_root / "grid_results.csv", rows)
    atomic_text(
        output_root / "certificates.jsonl",
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in certificates),
    )
    exact_statuses = {"EXACT_ESCAPE", "EXACT_LOCAL_OPTIMUM"}
    resource_statuses = {"WITNESS_CERTIFIED_SEARCH_INCOMPLETE", "RESOURCE_BOUNDED_NO_WITNESS"}
    summary = {
        **config,
        "experiment_id": EXPERIMENT_ID_IDASTAR,
        "arm": "idastar_escape",
        "row_count": len(rows),
        "exact_count": sum(row["status"] in exact_statuses for row in rows),
        "resource_bounded_count": sum(row["status"] in resource_statuses for row in rows),
        "replay_failure_count": sum(row["semantic_status"] == "REPLAY_FAIL" for row in rows),
        "median_runtime_seconds": statistics.median(float(row["runtime_seconds"]) for row in rows),
        "p95_runtime_seconds": sorted(float(row["runtime_seconds"]) for row in rows)[max(0, int(0.95 * len(rows) + 0.999999) - 1)],
        "resource_or_error_rate": sum(row["status"] in resource_statuses or row["status"] == "ERROR" for row in rows) / len(rows),
    }
    atomic_text(output_root / "config_summaries.json", json.dumps([summary], indent=2, sort_keys=True) + "\n")
    selection = {
        "experiment_id": EXPERIMENT_ID_IDASTAR,
        "phase": "full_development" if source_limit is None else "smoke",
        "status": "COMPLETE_WITH_RESOURCE_BOUNDARY" if summary["resource_bounded_count"] else "COMPLETE",
        "source_count": len(rows),
        "configuration_count": 1,
        "selected_config": config,
        "selection_is_frozen_for_e48": False,
        "future_panel_access": "E46_AND_LATER_NOT_READ",
    }
    atomic_text(output_root / "selection.json", json.dumps(selection, indent=2, sort_keys=True) + "\n")
    protocol = {
        "experiment_id": EXPERIMENT_ID_IDASTAR,
        "status": "DEVELOPMENT_ONLY",
        "phase": selection["phase"],
        "source_contract": {
            "screening_manifest": SCREENING_MANIFEST.relative_to(ROOT).as_posix(),
            "screening_manifest_sha256": sha256(SCREENING_MANIFEST),
            "source_count": len(rows),
            "fixed_panel": "same 128-source v14 screening order" if source_limit is None else f"prefix of same 128-source v14 screening order (limit={source_limit})",
            "e39_path": E39_INPUTS.relative_to(ROOT).as_posix(),
            "e44_path": E44_INPUTS.relative_to(ROOT).as_posix(),
        },
        "configuration_grid": [config],
        "arms": ["idastar_escape"],
        "rule_scope": RULE_SCOPE,
        "search_method": {
            "id": "idastar_escape_v1",
            "objective": "minimum path length to a state with cost < initial cost",
            "lower_bound": "ceil(gate_count_deficit / maximum_single_step_reduction)",
            "transposition_policy": "memoize fully explored failures by (state_hash, remaining_depth); finite-depth repetitions are allowed",
            "resource_status": "EXACT only when every depth bound through H completes",
            "reverse_edges": "not used; rank-increasing reverse Quartz parameter-splitting remains illegal",
        },
        "cell_limits": {
            "state_budget": config["state_budget"],
            "time_budget_seconds": time_budget_seconds,
        },
        "future_panel_access": "E46_AND_LATER_NOT_READ",
    }
    atomic_text(output_root / "protocol.json", json.dumps(protocol, indent=2, sort_keys=True) + "\n")
    receipt = {
        "status": selection["status"],
        "experiment_id": EXPERIMENT_ID_IDASTAR,
        "phase": selection["phase"],
        "protocol_sha256": sha256(output_root / "protocol.json"),
        "normalization_manifest_sha256": sha256(output_root / "normalization_manifest.csv"),
        "grid_results_sha256": sha256(output_root / "grid_results.csv"),
        "config_summaries_sha256": sha256(output_root / "config_summaries.json"),
        "certificates_sha256": sha256(output_root / "certificates.jsonl"),
        "selection_sha256": sha256(output_root / "selection.json"),
        "source_count": len(rows),
        "normalized_count": len(rows),
        "result_rows": len(rows),
        "configuration_count": 1,
        "arm_count": 1,
        "selected_config": config,
        "summary": summary,
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
        globals()["EXPERIMENT_ID_IDASTAR"] = args.experiment_id
    print(json.dumps(run(args.output_root, args.time_budget_seconds, args.source_limit), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
