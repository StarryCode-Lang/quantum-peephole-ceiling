"""Independently recompute and verify post-seal E31 structural metrics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit import qpy

ROOT = Path(__file__).resolve().parents[1]
E31 = ROOT / "data/v11/e31_factorial_pareto"
RESULTS = E31 / "formal_run/final/formal_results.csv"
DESIGN = E31 / "design_manifest.csv"
REPLAY = E31 / "formal_run/semantic_replay/semantic_replay_manifest.json"
OUTPUT = E31 / "formal_run/postseal_structural_distribution_metrics"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _independent_metrics(circuit) -> dict[str, int | float | bool]:
    ignored = {"barrier", "delay"}
    active: set[int] = set()
    edges: set[tuple[int, int]] = set()
    multi = two = measurements = resets = swaps = toffoli = t_count = 0
    non_clifford_t = False
    allowed = {
        "barrier", "delay", "id", "x", "y", "z", "h", "s", "sdg", "t", "tdg",
        "cx", "cz", "swap", "measure", "reset",
    }
    for instruction in circuit.data:
        name = str(instruction.operation.name).lower()
        indices = tuple(circuit.find_bit(bit).index for bit in instruction.qubits)
        if name not in ignored:
            active.update(indices)
        measurements += int(name == "measure")
        resets += int(name == "reset")
        swaps += int(name == "swap")
        toffoli += int(name in {"ccx", "ccz", "toffoli"})
        t_count += int(name in {"t", "tdg"})
        non_clifford_t = non_clifford_t or name not in allowed
        if name not in ignored | {"measure", "reset"}:
            multi += int(len(indices) >= 2)
            two += int(len(indices) == 2)
            edges.update(combinations(sorted(set(indices)), 2))
    possible = math.comb(circuit.num_qubits, 2) if circuit.num_qubits >= 2 else 0
    return {
        "declared_qubits": int(circuit.num_qubits),
        "ancilla_qubits": int(circuit.num_ancillas),
        "active_qubits_static": len(active),
        "logical_gate_count": int(circuit.size()),
        "logical_depth": int(circuit.depth()),
        "multi_qubit_gate_count": multi,
        "two_qubit_gate_count": two,
        "measurement_count": measurements,
        "reset_count": resets,
        "swap_count": swaps,
        "toffoli_ccz_count": toffoli,
        "logical_t_tdg_count": t_count,
        "two_qubit_depth": int(circuit.depth(
            filter_function=lambda item: (
                str(item.operation.name).lower() not in ignored and len(item.qubits) == 2
            )
        )),
        "logical_t_tdg_layer_depth": int(circuit.depth(
            filter_function=lambda item: str(item.operation.name).lower() in {"t", "tdg"}
        )),
        "interaction_graph_pair_edges": len(edges),
        "interaction_graph_density": float(len(edges) / possible) if possible else 0.0,
        "contains_non_clifford_t_operations": non_clifford_t,
    }


def verify(
    output_dir: Path = OUTPUT,
    results_path: Path = RESULTS,
    design_path: Path = DESIGN,
    replay_path: Path = REPLAY,
) -> dict[str, object]:
    audit_path = output_dir / "structural_distribution_audit.json"
    structural_path = output_dir / "semantic_cell_structural_metrics.csv"
    diversity_path = output_dir / "solution_diversity_by_input.csv"
    summary_path = output_dir / "distributional_risk_summary.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS_POSTSEAL_STRUCTURAL_DISTRIBUTIONAL_AUDIT":
        raise RuntimeError("E31 structural audit status is invalid")
    sources = {results_path, design_path, replay_path}
    expected_source_bindings = {
        path.relative_to(ROOT).as_posix(): sha256(path) for path in sources
    }
    if audit.get("source_bindings") != expected_source_bindings:
        raise RuntimeError("E31 structural audit source binding drift")
    for path in (structural_path, diversity_path, summary_path):
        record = audit.get("artifacts", {}).get(path.name, {})
        if (record.get("sha256") != sha256(path)
                or record.get("bytes") != path.stat().st_size):
            raise RuntimeError(f"E31 structural artifact drift: {path.name}")

    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    cells = replay.get("semantic_cells", [])
    observed = pd.read_csv(structural_path)
    if len(cells) != 6_858 or len(observed) != 6_858 \
            or observed["semantic_cell_id"].nunique() != 6_858:
        raise RuntimeError("E31 structural semantic-cell inventory differs")
    indexed = observed.set_index("semantic_cell_id", verify_integrity=True)
    integer_fields = [
        "declared_qubits", "ancilla_qubits", "active_qubits_static",
        "logical_gate_count", "logical_depth", "multi_qubit_gate_count",
        "two_qubit_gate_count", "measurement_count", "reset_count", "swap_count",
        "toffoli_ccz_count", "logical_t_tdg_count", "two_qubit_depth",
        "logical_t_tdg_layer_depth", "interaction_graph_pair_edges",
    ]
    checked = 0
    for binding in cells:
        cell_id = str(binding["semantic_cell_id"])
        if cell_id not in indexed.index:
            raise RuntimeError(f"E31 structural cell is missing: {cell_id}")
        qpy_path = ROOT / str(binding["qpy_path"])
        if sha256(qpy_path) != binding["qpy_sha256"]:
            raise RuntimeError(f"E31 structural QPY drift: {cell_id}")
        with qpy_path.open("rb") as stream:
            circuits = qpy.load(stream)
        if len(circuits) != 1:
            raise RuntimeError(f"E31 structural QPY inventory differs: {cell_id}")
        expected = _independent_metrics(circuits[0])
        row = indexed.loc[cell_id]
        key = binding["semantic_cell_key"]
        metadata = {
            "input_circuit_sha256": key["input_circuit_sha256"],
            "listing_model": key["listing_model"],
            "rule_set": key["rule_set"],
            "window_gates": int(key["window_gates"]),
            "successful_budget_count": len(binding["successful_budget_seconds"]),
            "formal_success_rows_bound": int(binding["formal_success_rows_bound"]),
            "qpy_sha256": binding["qpy_sha256"],
        }
        for field, value in metadata.items():
            if str(row[field]) != str(value):
                raise RuntimeError(f"E31 structural metadata differs: {cell_id}.{field}")
        for field in integer_fields:
            if int(row[field]) != int(expected[field]):
                raise RuntimeError(f"E31 structural metric differs: {cell_id}.{field}")
        if not math.isclose(
            float(row["interaction_graph_density"]),
            float(expected["interaction_graph_density"]),
            rel_tol=1e-12, abs_tol=1e-12,
        ):
            raise RuntimeError(f"E31 interaction density differs: {cell_id}")
        observed_bool = str(row["contains_non_clifford_t_operations"]).lower()
        if observed_bool not in {"true", "false"} \
                or (observed_bool == "true") is not bool(
                    expected["contains_non_clifford_t_operations"]
                ):
            raise RuntimeError(f"E31 structural boolean differs: {cell_id}")
        checked += 1

    results = pd.read_csv(results_path)
    design = pd.read_csv(design_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    success = results.loc[results["status"].eq("success")]
    reductions = pd.to_numeric(success["common_basis_gate_reduction_pct"], errors="raise")
    itt = pd.Series(np.where(
        results["status"].eq("success"),
        pd.to_numeric(results["common_basis_gate_reduction_pct"], errors="coerce").fillna(0.0),
        0.0,
    ))
    for prefix, values in (
        ("success_only_reduction_quantiles_pp", reductions),
        ("itt_zero_for_non_success_reduction_quantiles_pp", itt),
    ):
        for quantile in (0.01, 0.05, 0.10, 0.25, 0.50):
            key = f"q{int(quantile * 100):02d}"
            if not math.isclose(
                float(summary[prefix][key]), float(values.quantile(quantile)),
                rel_tol=1e-12, abs_tol=1e-12,
            ):
                raise RuntimeError(f"E31 distribution quantile differs: {prefix}.{key}")
    if (summary.get("status") != "PASS_POSTSEAL_DERIVED_DISTRIBUTIONAL_METRICS"
            or summary.get("formal_rows") != 28_152
            or summary.get("success_rows") != 20_314
            or summary.get("successful_regression_count") != int((reductions < 0).sum())
            or not math.isclose(
                float(summary["successful_regression_probability"]),
                float((reductions < 0).mean()), abs_tol=1e-15,
            )):
        raise RuntimeError("E31 distribution summary differs")
    for threshold in (1.0, 5.0, 10.0, 25.0):
        key = f"increase_ge_{int(threshold)}pct"
        expected = float((reductions <= -threshold).mean())
        if not math.isclose(
            float(summary["successful_expansion_probability_by_threshold"][key]),
            expected, abs_tol=1e-15,
        ):
            raise RuntimeError(f"E31 expansion probability differs: {key}")

    diversity = pd.read_csv(diversity_path).sort_values("input_circuit_sha256").reset_index(drop=True)
    inventory = (
        design[["input_circuit_sha256", "circuit_id", "circuit_family"]]
        .drop_duplicates().sort_values("input_circuit_sha256").reset_index(drop=True)
    )
    expected_counts = success.groupby("input_circuit_sha256").agg(
        successful_rows=("run_id", "size"),
        unique_output_circuits=("output_circuit_sha256", "nunique"),
    ).reset_index()
    expected_diversity = inventory.merge(
        expected_counts, on="input_circuit_sha256", how="left"
    ).fillna({"successful_rows": 0, "unique_output_circuits": 0})
    for field in ("successful_rows", "unique_output_circuits"):
        expected_diversity[field] = expected_diversity[field].astype(int)
    try:
        pd.testing.assert_frame_equal(diversity, expected_diversity, check_dtype=False)
    except AssertionError as error:
        raise RuntimeError("E31 solution-diversity table differs") from error
    expected_diversity_summary = {
        "input_count": 391,
        "inputs_with_any_success": int((expected_diversity["successful_rows"] > 0).sum()),
        "unique_output_circuits_global": int(success["output_circuit_sha256"].nunique()),
        "per_input_unique_output_min": int(expected_diversity["unique_output_circuits"].min()),
        "per_input_unique_output_median": float(
            expected_diversity["unique_output_circuits"].median()
        ),
        "per_input_unique_output_max": int(expected_diversity["unique_output_circuits"].max()),
    }
    if summary.get("solution_diversity") != expected_diversity_summary:
        raise RuntimeError("E31 solution-diversity summary differs")
    if (not str(summary.get("peak_live_qubits_status", "")).startswith("NOT_MEASURED")
            or not str(summary.get("t_depth_status", "")).startswith(
                "NOT_FAULT_TOLERANT_T_DEPTH"
            )):
        raise RuntimeError("E31 structural limitations were weakened")
    return {
        "status": "VERIFIED_INDEPENDENT_POSTSEAL_STRUCTURAL_DISTRIBUTIONAL",
        "semantic_cells_recomputed": checked,
        "formal_rows_rechecked": int(len(results)),
        "input_diversity_rows_rechecked": int(len(diversity)),
        "artifact_hashes_rechecked": 3,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(verify(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
