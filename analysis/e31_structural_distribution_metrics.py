"""Derive post-seal structural and distributional metrics from E31 certificates."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit import qpy

ROOT = Path(__file__).resolve().parents[1]
E31 = ROOT / "data/v11/e31_factorial_pareto"
DEFAULT_RESULTS = E31 / "formal_run/final/formal_results.csv"
DEFAULT_DESIGN = E31 / "design_manifest.csv"
DEFAULT_REPLAY = E31 / "formal_run/semantic_replay/semantic_replay_manifest.json"
DEFAULT_OUTPUT = E31 / "formal_run/postseal_structural_distribution_metrics"
IGNORED_DIRECTIVES = {"barrier", "delay"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def circuit_structural_metrics(circuit) -> dict[str, int | float | bool]:
    """Measure the exact logical QPY representation, without hardware synthesis."""
    active: set[int] = set()
    interaction_edges: set[tuple[int, int]] = set()
    counts = {
        "multi_qubit_gate_count": 0,
        "two_qubit_gate_count": 0,
        "measurement_count": 0,
        "reset_count": 0,
        "swap_count": 0,
        "toffoli_ccz_count": 0,
        "logical_t_tdg_count": 0,
    }
    for item in circuit.data:
        name = str(item.operation.name).lower()
        qubits = [circuit.find_bit(qubit).index for qubit in item.qubits]
        if name not in IGNORED_DIRECTIVES:
            active.update(qubits)
        if name == "measure":
            counts["measurement_count"] += 1
        if name == "reset":
            counts["reset_count"] += 1
        if name == "swap":
            counts["swap_count"] += 1
        if name in {"ccx", "ccz", "toffoli"}:
            counts["toffoli_ccz_count"] += 1
        if name in {"t", "tdg"}:
            counts["logical_t_tdg_count"] += 1
        if name not in IGNORED_DIRECTIVES and name not in {"measure", "reset"}:
            if len(qubits) >= 2:
                counts["multi_qubit_gate_count"] += 1
            if len(qubits) == 2:
                counts["two_qubit_gate_count"] += 1
            for left, right in combinations(sorted(set(qubits)), 2):
                interaction_edges.add((left, right))
    possible_edges = circuit.num_qubits * (circuit.num_qubits - 1) // 2
    two_qubit_depth = circuit.depth(
        filter_function=lambda item: (
            item.operation.name not in IGNORED_DIRECTIVES
            and len(item.qubits) == 2
        )
    )
    logical_t_depth = circuit.depth(
        filter_function=lambda item: str(item.operation.name).lower() in {"t", "tdg"}
    )
    return {
        "declared_qubits": int(circuit.num_qubits),
        "ancilla_qubits": int(circuit.num_ancillas),
        "active_qubits_static": len(active),
        "logical_gate_count": int(circuit.size()),
        "logical_depth": int(circuit.depth()),
        **counts,
        "two_qubit_depth": int(two_qubit_depth),
        "logical_t_tdg_layer_depth": int(logical_t_depth),
        "interaction_graph_pair_edges": len(interaction_edges),
        "interaction_graph_density": (
            float(len(interaction_edges) / possible_edges) if possible_edges else 0.0
        ),
        "contains_non_clifford_t_operations": any(
            str(item.operation.name).lower()
            not in {
                "barrier", "delay", "id", "x", "y", "z", "h", "s", "sdg",
                "t", "tdg", "cx", "cz", "swap", "measure", "reset",
            }
            for item in circuit.data
        ),
    }


def distributional_metrics(
    results: pd.DataFrame, design: pd.DataFrame,
) -> tuple[dict[str, object], pd.DataFrame]:
    success = results.loc[results["status"].eq("success")].copy()
    reductions = pd.to_numeric(
        success["common_basis_gate_reduction_pct"], errors="raise"
    )
    if reductions.isna().any():
        raise ValueError("successful E31 rows contain missing reductions")
    itt = np.where(
        results["status"].eq("success"),
        pd.to_numeric(results["common_basis_gate_reduction_pct"], errors="coerce").fillna(0.0),
        0.0,
    )
    thresholds = [1.0, 5.0, 10.0, 25.0]
    input_inventory = (
        design[["input_circuit_sha256", "circuit_id", "circuit_family"]]
        .drop_duplicates()
        .sort_values("input_circuit_sha256")
    )
    diversity = success.groupby("input_circuit_sha256").agg(
        successful_rows=("run_id", "size"),
        unique_output_circuits=("output_circuit_sha256", "nunique"),
    ).reset_index()
    diversity = input_inventory.merge(diversity, on="input_circuit_sha256", how="left")
    for column in ("successful_rows", "unique_output_circuits"):
        diversity[column] = diversity[column].fillna(0).astype(int)
    quantiles = [0.01, 0.05, 0.10, 0.25, 0.50]
    return ({
        "formal_rows": int(len(results)),
        "success_rows": int(len(success)),
        "non_success_rows": int(len(results) - len(success)),
        "success_only_reduction_quantiles_pp": {
            f"q{int(q * 100):02d}": float(reductions.quantile(q)) for q in quantiles
        },
        "itt_zero_for_non_success_reduction_quantiles_pp": {
            f"q{int(q * 100):02d}": float(pd.Series(itt).quantile(q)) for q in quantiles
        },
        "successful_regression_probability": float((reductions < 0.0).mean()),
        "successful_regression_count": int((reductions < 0.0).sum()),
        "catastrophic_expansion_operationalization": (
            "post-seal sensitivity grid: common-basis gate-count increase at or above each "
            "listed percentage, conditional on a successful valid output"
        ),
        "successful_expansion_probability_by_threshold": {
            f"increase_ge_{int(threshold)}pct": float((reductions <= -threshold).mean())
            for threshold in thresholds
        },
        "solution_diversity": {
            "input_count": int(len(diversity)),
            "inputs_with_any_success": int((diversity["successful_rows"] > 0).sum()),
            "unique_output_circuits_global": int(success["output_circuit_sha256"].nunique()),
            "per_input_unique_output_min": int(diversity["unique_output_circuits"].min()),
            "per_input_unique_output_median": float(
                diversity["unique_output_circuits"].median()
            ),
            "per_input_unique_output_max": int(diversity["unique_output_circuits"].max()),
        },
    }, diversity)


def derive(
    results_path: Path = DEFAULT_RESULTS,
    design_path: Path = DEFAULT_DESIGN,
    replay_path: Path = DEFAULT_REPLAY,
    output_dir: Path = DEFAULT_OUTPUT,
) -> dict[str, object]:
    results = pd.read_csv(results_path)
    design = pd.read_csv(design_path)
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    cells = replay.get("semantic_cells")
    if (replay.get("status") != "PASS"
            or replay.get("all_success_rows_passed") is not True
            or replay.get("success_rows_verified_and_bound") != 20_314
            or not isinstance(cells, list) or len(cells) != 6_858
            or len(results) != 28_152):
        raise ValueError("sealed E31 sources do not satisfy the derivation boundary")
    rows: list[dict[str, object]] = []
    for binding in cells:
        qpy_path = ROOT / str(binding["qpy_path"])
        if sha256(qpy_path) != binding["qpy_sha256"]:
            raise ValueError(f"QPY hash drift: {binding['semantic_cell_id']}")
        with qpy_path.open("rb") as stream:
            circuits = qpy.load(stream)
        if len(circuits) != 1:
            raise ValueError(f"QPY inventory drift: {binding['semantic_cell_id']}")
        key = binding["semantic_cell_key"]
        rows.append({
            "semantic_cell_id": binding["semantic_cell_id"],
            "input_circuit_sha256": key["input_circuit_sha256"],
            "listing_model": key["listing_model"],
            "rule_set": key["rule_set"],
            "window_gates": key["window_gates"],
            "successful_budget_count": len(binding["successful_budget_seconds"]),
            "formal_success_rows_bound": binding["formal_success_rows_bound"],
            "qpy_sha256": binding["qpy_sha256"],
            **circuit_structural_metrics(circuits[0]),
        })
    structural = pd.DataFrame(rows).sort_values("semantic_cell_id").reset_index(drop=True)
    distribution, diversity = distributional_metrics(results, design)
    output_dir.mkdir(parents=True, exist_ok=True)
    structural_path = output_dir / "semantic_cell_structural_metrics.csv"
    diversity_path = output_dir / "solution_diversity_by_input.csv"
    summary_path = output_dir / "distributional_risk_summary.json"
    structural.to_csv(structural_path, index=False)
    diversity.to_csv(diversity_path, index=False)
    summary = {
        "schema_version": "1.0.0",
        "status": "PASS_POSTSEAL_DERIVED_DISTRIBUTIONAL_METRICS",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "sealed E31 fixed panel; structural metrics use exact logical QPY outputs; "
            "no hardware-native, scheduled-duration, or fault-tolerant synthesis claim"
        ),
        "results_sha256": sha256(results_path),
        "design_manifest_sha256": sha256(design_path),
        "semantic_replay_manifest_sha256": sha256(replay_path),
        "structural_semantic_cells": int(len(structural)),
        "structural_metric_representation": "logical replayed QPY before hardware synthesis",
        "peak_live_qubits_status": (
            "NOT_MEASURED; active_qubits_static is reported only as a static upper-bound proxy"
        ),
        "t_depth_status": (
            "NOT_FAULT_TOLERANT_T_DEPTH; logical T/TDG layers are descriptive only when arbitrary "
            "non-Clifford+T operations are present"
        ),
        **distribution,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    audit = {
        "schema_version": "1.0.0",
        "status": "PASS_POSTSEAL_STRUCTURAL_DISTRIBUTIONAL_AUDIT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "derivation_script": Path(__file__).relative_to(ROOT).as_posix(),
        "derivation_script_sha256": sha256(Path(__file__)),
        "source_bindings": {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in (results_path, design_path, replay_path)
        },
        "artifacts": {
            path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
            for path in (structural_path, diversity_path, summary_path)
        },
        "rows": {
            structural_path.name: int(len(structural)),
            diversity_path.name: int(len(diversity)),
        },
        "limitations": [
            "structural counts are representation-bound to replayed logical QPY outputs",
            "active_qubits_static is not a dynamic peak-live-qubit measurement",
            "logical T/TDG layer depth is not fault-tolerant T-depth without synthesis",
            "catastrophic expansion thresholds are post-seal descriptive sensitivities",
        ],
    }
    audit_path = output_dir / "structural_distribution_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(derive(args.results, args.design, args.replay, args.output_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
