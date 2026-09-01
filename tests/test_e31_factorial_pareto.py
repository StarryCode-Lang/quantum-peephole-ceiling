"""Design and analysis gates for E31 factorial/Pareto pre-registration."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from qiskit import QuantumCircuit

import analysis.e31_factorial_pareto_analysis as e31_analysis
from analysis.e31_factorial_pareto_analysis import (
    add_pareto_flags, family_blocked_randomization_p, fit_full_factorial_model,
    normalized_pareto_hypervolume, primary_dual_estimand, run_order_temporal_diagnostics,
    posthoc_marginal_contrasts, pareto_aggregation_sensitivity,
    summarize_pareto_aggregation_sensitivity,
    secondary_outcome_availability,
    stratified_input_bootstrap_ci, summarize_equal_budget,
    validate_host_environment_gate, validate_method_erratum_gate,
    validate_transitive_source_gate, validate_pareto_aggregation_gate,
    validate_contrast_expansion_gate,
    validate_power_gate, validate_results,
)
from analysis.e31_family_cluster_power import simulate_power
from experiments.e31_factorial_pareto_design import (
    build_design, file_sha256, load_unique_inputs, validate_design,
)
from experiments.e31_resource_smoke import select_smoke_cells
from src.circuits.real_benchmarks import circuit_sha256
from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "experiments" / "e31_factorial_pareto_protocol.json"


def _protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def _inputs() -> pd.DataFrame:
    return pd.DataFrame({
        "circuit_id": ["a", "b"], "circuit_family": ["fam_a", "fam_b"],
        "n_qubits": [4, 6], "input_circuit_sha256": ["a" * 64, "b" * 64],
        "qasm_path": ["a.qasm", "b.qasm"], "source_rows_collapsed": [1, 1],
    })


def test_design_is_complete_reproducible_and_uses_hash_as_unit():
    protocol = _protocol()
    first = build_design(_inputs(), protocol, "c" * 64)
    second = build_design(_inputs(), protocol, "c" * 64)
    pd.testing.assert_frame_equal(first, second)
    validate_design(first, protocol)
    assert len(first) == 2 * 3 * 2 * 3 * 4
    assert first.groupby("input_circuit_sha256").size().eq(72).all()


def test_duplicate_seed_rows_collapse_to_one_independent_input(tmp_path: Path):
    manifest = pd.DataFrame({
        "circuit_id": ["same_0", "same_1"], "circuit_family": ["fam", "fam"],
        "n_qubits": [4, 4], "trial": [0, 1], "seed": [10, 11],
        "input_circuit_sha256": ["d" * 64, "d" * 64],
        "qasm_sha256": ["e" * 64, "e" * 64],
        "qasm_path": ["same0.qasm", "same1.qasm"],
    })
    path = tmp_path / "manifest.csv"
    manifest.to_csv(path, index=False)
    unique, audit = load_unique_inputs(path)
    assert len(unique) == 1
    assert audit == {"source_rows": 2, "unique_input_hashes": 1, "collapsed_repeated_rows": 1}
    assert unique.loc[0, "source_rows_collapsed"] == 2


def _results_from_design(design: pd.DataFrame) -> pd.DataFrame:
    result = design[["run_id", "input_circuit_sha256", "circuit_id", "circuit_family",
                     "listing_model", "rule_set", "window_gates", "budget_seconds",
                     "run_order", "primary_pair_orientation"]].copy()
    result["protocol_sha256"] = design["protocol_sha256"].to_numpy()
    result["design_manifest_sha256"] = "f" * 64
    result["status"] = "success"
    result["valid_equivalent_output"] = True
    result["exact_fidelity"] = 1.0
    result["output_circuit_sha256"] = "e" * 64
    result["original_common_basis_gate_count"] = 1_000_000
    result["optimized_common_basis_gate_count"] = 950_000
    result["common_basis_gate_reduction_pct"] = 5.0
    result["wall_seconds_end_to_end"] = 0.5
    result["peak_rss_mb"] = 100.0
    return result


def _synchronize_gate_counts(result: pd.DataFrame) -> None:
    """Keep synthetic fixture counts bound to its chosen reduction response."""
    original = 1_000_000
    reduction = pd.to_numeric(result["common_basis_gate_reduction_pct"], errors="raise")
    result["original_common_basis_gate_count"] = original
    result["optimized_common_basis_gate_count"] = np.rint(
        original * (1.0 - reduction / 100.0)
    ).astype(int)


def test_result_gate_requires_complete_schedule_and_zeroes_invalid_itt():
    protocol = _protocol()
    design = build_design(_inputs().iloc[:1], protocol, "c" * 64)
    results = _results_from_design(design)
    results.loc[0, ["status", "valid_equivalent_output",
                    "common_basis_gate_reduction_pct"]] = ["timeout", False, 99.0]
    validated = validate_results(design, results, protocol)
    assert validated.loc[validated.run_id == results.loc[0, "run_id"],
                         "common_basis_gate_reduction_pct_itt"].item() == 0.0
    with pytest.raises(ValueError, match="missing=1"):
        validate_results(design, results.iloc[1:], protocol)
    with pytest.raises(ValueError, match="not bound"):
        validate_results(design, results, protocol, formal=True,
                         design_sha256="f" * 64)
    corrupted = results.copy()
    corrupted.loc[0, "valid_equivalent_output"] = "corrupt"
    with pytest.raises(ValueError, match="invalid serialized boolean"):
        validate_results(design, corrupted, protocol)
    corrupted = results.copy()
    corrupted.loc[1, "valid_equivalent_output"] = False
    with pytest.raises(ValueError, match="every successful run must be marked valid"):
        validate_results(design, corrupted, protocol)
    corrupted = results.copy()
    corrupted.loc[1, "exact_fidelity"] = 1.01
    with pytest.raises(ValueError, match="frozen threshold"):
        validate_results(design, corrupted, protocol)
    corrupted = results.copy()
    corrupted.loc[1, "optimized_common_basis_gate_count"] = 949_999.5
    with pytest.raises(ValueError, match="non-negative integer"):
        validate_results(design, corrupted, protocol)
    corrupted = results.copy()
    corrupted.loc[1, "common_basis_gate_reduction_pct"] += 0.01
    with pytest.raises(ValueError, match="does not match the sealed gate counts"):
        validate_results(design, corrupted, protocol)


def test_equal_budget_summary_and_pareto_flag_are_deterministic():
    protocol = _protocol()
    design = build_design(_inputs().iloc[:1], protocol, "c" * 64)
    validated = validate_results(design, _results_from_design(design), protocol)
    summary = summarize_equal_budget(validated)
    frontier = add_pareto_flags(summary)
    assert len(summary) == 72
    assert frontier["pareto_nondominated"].all()
    assert frontier["pareto_dominance_rate"].eq(0).all()


def test_pareto_aggregation_sensitivity_covers_all_four_frozen_schemes():
    protocol = _protocol()
    design = build_design(_inputs(), protocol, "c" * 64)
    results = _results_from_design(design)
    second_input = results["input_circuit_sha256"].eq("b" * 64)
    results.loc[second_input, "wall_seconds_end_to_end"] = 5.0
    results.loc[second_input, "peak_rss_mb"] = 900.0
    winner = (
        results["listing_model"].eq("LBL")
        & results["rule_set"].eq("COMMUTATION_ONLY")
        & results["window_gates"].eq(4)
        & results["budget_seconds"].eq(1)
    )
    results.loc[winner, "common_basis_gate_reduction_pct"] = 6.0
    _synchronize_gate_counts(results)
    validated = validate_results(design, results, protocol)
    sensitivity = pareto_aggregation_sensitivity(validated)
    assert len(sensitivity) == 288
    assert sensitivity.groupby(
        ["wall_aggregation", "memory_aggregation"]
    ).size().eq(72).all()
    assert set(sensitivity["wall_aggregation"]) == {"median", "p95"}
    assert set(sensitivity["memory_aggregation"]) == {"median", "p95"}
    first_cell = sensitivity[
        sensitivity["listing_model"].eq("LBL")
        & sensitivity["rule_set"].eq("COMMUTATION_ONLY")
        & sensitivity["window_gates"].eq(4)
        & sensitivity["budget_seconds"].eq(1)
    ]
    wall_selected = first_cell.groupby("wall_aggregation")["selected_wall_seconds"].first()
    memory_selected = first_cell.groupby("memory_aggregation")["selected_peak_rss_mb"].first()
    assert wall_selected["median"] == pytest.approx(2.75)
    assert wall_selected["p95"] == pytest.approx(4.775)
    assert memory_selected["median"] == pytest.approx(500.0)
    assert memory_selected["p95"] == pytest.approx(860.0)
    assert first_cell["pareto_nondominated"].all()
    assert first_cell["dominates_n"].eq(71).all()
    dominated_cell = sensitivity[
        sensitivity["listing_model"].eq("WCL")
        & sensitivity["rule_set"].eq("COMMUTATION_ONLY")
        & sensitivity["window_gates"].eq(4)
        & sensitivity["budget_seconds"].eq(1)
    ]
    assert dominated_cell["pareto_nondominated"].eq(False).all()
    assert dominated_cell["dominated_by_n"].ge(1).all()
    summary = summarize_pareto_aggregation_sensitivity(sensitivity)
    assert summary["frontier_membership_agreement_all_schemes"] is True
    assert summary["bounded_aggregation_invariant_frontier_claim_allowed"] is True
    serialized = sensitivity.copy()
    serialized["pareto_nondominated"] = serialized["pareto_nondominated"].map(
        {True: "True", False: "False"}
    )
    assert summarize_pareto_aggregation_sensitivity(serialized) == summary
    corrupted = sensitivity.copy()
    corrupted.loc[0, "pareto_nondominated"] = "corrupt"
    with pytest.raises(ValueError, match="invalid serialized boolean"):
        summarize_pareto_aggregation_sensitivity(corrupted)


def test_shared_engine_rule_treatments_are_isolated_without_templates():
    circuit = QuantumCircuit(2)
    circuit.x(0)
    circuit.x(0)
    circuit.rz(0.1, 1)
    circuit.rz(0.2, 1)
    outputs = []
    for enabled in (False, True):
        engine = Phase2bTemplateMatcher(
            gather_window=4, template_enabled=enabled, collect_trace=True
        )
        outputs.append(engine.optimize_full_pipeline(circuit, target=circuit))
    assert circuit_sha256(outputs[0].optimized_circuit) == circuit_sha256(outputs[1].optimized_circuit)
    assert outputs[0].metadata["trace"] == outputs[1].metadata["trace"]
    assert outputs[0].metadata["template_enabled"] is False
    assert outputs[1].metadata["template_enabled"] is True


def test_shared_engine_template_flag_changes_only_a_matching_template_treatment():
    circuit = QuantumCircuit(2)
    circuit.h(1)
    circuit.cx(0, 1)
    circuit.h(1)
    disabled = Phase2bTemplateMatcher(
        gather_window=4, template_enabled=False, collect_trace=True
    ).optimize_full_pipeline(circuit, target=circuit)
    enabled = Phase2bTemplateMatcher(
        gather_window=4, template_enabled=True, collect_trace=True
    ).optimize_full_pipeline(circuit, target=circuit)
    assert disabled.optimized_size == 3
    assert enabled.optimized_size == 1
    assert disabled.metadata["cz_conversions"] == 0
    assert enabled.metadata["cz_conversions"] == 1


def test_resource_smoke_selects_two_inputs_and_four_cells_each():
    protocol = _protocol()
    design = build_design(_inputs(), protocol, "c" * 64)
    selected = select_smoke_cells(design)
    assert len(selected) == 8
    assert selected.groupby("input_circuit_sha256").size().eq(4).all()


def test_family_cluster_power_increases_with_effect_size():
    sizes = np.array([20] * 15)
    low = simulate_power(0.5, sizes, 2.0, 5.0, 0.05 / 24,
                         simulations=2000, seed=42)
    high = simulate_power(3.0, sizes, 2.0, 5.0, 0.05 / 24,
                          simulations=2000, seed=42)
    assert high > low


def test_protocol_freezes_one_primary_without_changing_one_pp_mcid():
    protocol = _protocol()
    assert protocol["power_gate"]["mcid_pp"] == 1.0
    assert protocol["power_gate"]["planned_primary_contrasts"] == 1
    assert protocol["design_status"] == "FROZEN_BEFORE_EXECUTION"
    assert protocol["power_gate"]["new_family_generalized_decision"] == "BLOCK"
    design_path = ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv"
    assert validate_power_gate(protocol, file_sha256(design_path))["decision"]["fixed_benchmark_A"] == "PASS"
    gate = validate_method_erratum_gate(file_sha256(PROTOCOL_PATH), file_sha256(design_path))
    assert gate["checkpoint_boundary"]["primary_contrast_computed_before_erratum"] is False
    assert gate["changes_to_frozen_execution"] is False
    provenance = validate_transitive_source_gate(
        file_sha256(PROTOCOL_PATH), file_sha256(design_path)
    )
    assert provenance["complete_cryptographic_prerun_source_closure"] is False
    assert provenance["omitted_source_count"] == 16
    pareto_gate = validate_pareto_aggregation_gate(
        file_sha256(PROTOCOL_PATH), file_sha256(design_path)
    )
    assert pareto_gate["aggregation_functionals_preregistered_in_protocol"] is False
    assert pareto_gate["required_sensitivity_grid"]["expected_schemes"] == 4
    contrast_gate = validate_contrast_expansion_gate(
        file_sha256(PROTOCOL_PATH), file_sha256(design_path)
    )
    assert contrast_gate["fully_preregistered_scalar_contrast_family"] is False
    assert contrast_gate["multiplicity_family"]["size"] == 30


def test_dual_estimand_primary_uses_all_twelve_grid_cells():
    protocol = _protocol()
    design = build_design(_inputs(), protocol, "c" * 64)
    results = _results_from_design(design)
    # Inject a constant 1pp listing-by-rule-set interaction.
    plus_wcl = (results.listing_model.eq("WCL")
                & results.rule_set.eq("COMMUTATION_PLUS_TEMPLATES"))
    results.loc[plus_wcl, "common_basis_gate_reduction_pct"] = 6.0
    _synchronize_gate_counts(results)
    validated = validate_results(design, results, protocol)
    report = primary_dual_estimand(validated)
    assert report["fixed_benchmark_A"]["estimate_pp"] == pytest.approx(1.0)
    assert report["fixed_benchmark_A"]["design_based_p_value"] is None
    assert report["fixed_benchmark_A"]["design_based_confidence_interval"] is None
    assert report["fixed_benchmark_A"]["meets_or_exceeds_mcid"] is True
    assert report["fixed_benchmark_A"]["stability_interval_role"] == (
        "EMPIRICAL_SENSITIVITY_NOT_DESIGN_BASED_CI"
    )
    assert report["new_family_generalized_B"]["n_independent_family_clusters"] == 2


def test_invalid_randomization_interpretation_is_refused():
    with pytest.raises(RuntimeError, match="no randomized treatment-assignment"):
        family_blocked_randomization_p(pd.DataFrame({"primary_did_pp": [1.0]}))


def test_stratified_bootstrap_is_seeded_and_preserves_constant_family_values():
    frame = pd.DataFrame({
        "circuit_family": ["a", "a", "b", "b"],
        "primary_did_pp": [1.0, 1.0, 3.0, 3.0],
    })
    assert stratified_input_bootstrap_ci(frame, replicates=100, seed=4) == [2.0, 2.0]


def test_full_factorial_model_respects_input_blocks_and_analysis_hierarchy():
    protocol = _protocol()
    inputs = pd.concat([_inputs()] * 3, ignore_index=True)
    inputs["circuit_id"] = [f"c{i}" for i in range(len(inputs))]
    inputs["input_circuit_sha256"] = [f"{i:064x}" for i in range(len(inputs))]
    design = build_design(inputs, protocol, "c" * 64)
    results = _results_from_design(design)
    results["common_basis_gate_reduction_pct"] = (
        5.0 + ((results["run_order"] * 37) % 17) / 10.0
    )
    _synchronize_gate_counts(results)
    validated = validate_results(design, results, protocol)
    coefficients, diagnostics = fit_full_factorial_model(validated)
    assert len(coefficients) == 71
    assert set(coefficients["inference_role"]) == {
        "EXPLORATORY_PARAMETERIZATION_DIAGNOSTIC"
    }
    assert not coefficients["confirmatory_primary_contrast"].any()
    assert diagnostics["n_input_clusters"] == 6
    assert diagnostics["design_matrix_rank"] == diagnostics["design_matrix_columns"]
    assert diagnostics["posthoc_marginal_contrast_file"] == "posthoc_marginal_contrasts.csv"


def test_posthoc_marginal_contrasts_are_exactly_the_disclosed_supportive_family():
    protocol = _protocol()
    inputs = pd.DataFrame({
        "circuit_id": [f"input-{index:03d}" for index in range(391)],
        "circuit_family": [f"family-{index % 15:02d}" for index in range(391)],
        "n_qubits": [4] * 391,
        "input_circuit_sha256": [f"{index:064x}" for index in range(391)],
        "qasm_path": [f"input-{index:03d}.qasm" for index in range(391)],
        "source_rows_collapsed": [1] * 391,
    })
    design = build_design(inputs, protocol, "c" * 64)
    results = _results_from_design(design)
    wcl = results["listing_model"].eq("WCL").astype(float)
    plus = results["rule_set"].eq("COMMUTATION_PLUS_TEMPLATES").astype(float)
    window_16 = results["window_gates"].eq(16).astype(float)
    budget_10 = results["budget_seconds"].eq(10).astype(float)
    results["common_basis_gate_reduction_pct"] = (
        1.0 + 2.0 * wcl + 3.0 * plus + 4.0 * wcl * plus
        + 5.0 * window_16 * budget_10
    )
    _synchronize_gate_counts(results)
    validated = validate_results(design, results, protocol)
    contrasts = posthoc_marginal_contrasts(validated)
    assert len(contrasts) == 30
    assert set(contrasts["inference_role"]) == {
        "SUPPORTIVE_POSTHOC_OPERATIONALIZATION_OF_FROZEN_CLASS"
    }
    assert contrasts["multiplicity_family_id"].eq("E31_POSTHOC_MARGINAL_30").all()
    assert contrasts["multiplicity_family_size"].eq(30).all()
    gate = json.loads(e31_analysis.CONTRAST_EXPANSION_GATE.read_text(encoding="utf-8"))
    assert contrasts["coefficient"].tolist() == gate["contrast_labels"]
    assert set(contrasts["interaction_order"]) == {1, 2}
    assert not contrasts["confirmatory_primary_contrast"].any()
    assert not contrasts["coefficient"].str.contains(
        r"listing_model\[WCL-vs-LBL\]:rule_set\[COMMUTATION_PLUS_TEMPLATES"
    ).any()
    wcl_main = contrasts.loc[
        contrasts["coefficient"].eq("MARGINAL::listing_model[WCL-vs-LBL]"),
        "estimate_pp",
    ].item()
    window_budget = contrasts.loc[
        contrasts["coefficient"].eq(
            "MARGINAL::window_gates[16-vs-4]:budget_seconds[10-vs-1]"
        ),
        "estimate_pp",
    ].item()
    assert wcl_main == pytest.approx(4.0)
    assert window_budget == pytest.approx(5.0)


def test_unrecorded_anytime_secondary_outcomes_are_not_imputed():
    protocol = _protocol()
    design = build_design(_inputs().iloc[:1], protocol, "c" * 64)
    validated = validate_results(design, _results_from_design(design), protocol)
    availability = secondary_outcome_availability(validated)
    assert availability["time_to_first_valid_seconds"]["status"] == (
        "NOT_MEASURED_IN_FROZEN_RUN"
    )
    assert availability["time_to_best_seconds"]["usable_success_rows"] == 0


def test_hypervolume_is_seeded_and_deduplicates_failure_axis():
    summary = pd.DataFrame({
        "quality_itt_mean": [0.0, 1.0, 1.0],
        "valid_rate": [0.0, 1.0, 0.5],
        "failure_rate": [1.0, 0.0, 0.5],
        "wall_seconds_median": [3.0, 2.0, 1.0],
        "peak_rss_mb_p95": [3.0, 2.0, 1.0],
    })
    frontier = add_pareto_flags(summary)
    first = normalized_pareto_hypervolume(frontier, draws=10_000, seed=9)
    second = normalized_pareto_hypervolume(frontier, draws=10_000, seed=9)
    assert first == second
    assert first["deduplicated_protocol_objective"]["removed"] == "failure_rate"
    assert 0.0 <= first["hypervolume"] <= 1.0


def test_temporal_host_diagnostic_is_complete_but_never_claims_exclusivity():
    protocol = _protocol()
    design = build_design(_inputs().iloc[:1], protocol, "c" * 64)
    validated = validate_results(design, _results_from_design(design), protocol)
    temporal, audit = run_order_temporal_diagnostics(validated, blocks=6)
    assert len(temporal) == 6
    assert temporal["rows"].sum() == len(validated)
    assert audit["continuous_host_exclusivity_verified"] is False
    assert audit["continuous_host_telemetry_recorded"] is False
    assert audit["material_drift_thresholds"]["quality_itt"] == 1.0
    assert audit["material_drift_screen_decision"] in {
        "REVIEW_REQUIRED", "NO_THRESHOLD_EXCEEDED",
    }


def test_host_environment_gate_is_bound_and_discloses_shared_host():
    design_path = ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv"
    gate = validate_host_environment_gate(
        file_sha256(PROTOCOL_PATH), file_sha256(design_path),
    )
    assert gate["checkpoint_boundary"]["rows"] < 28_152
    assert gate["aggregate_treatment_effects_inspected"] is False
    assert gate["row_exclusion_or_rerun_authorized"] is False
    assert gate["continuous_host_exclusivity_verified"] is False
    assert gate["continuous_host_telemetry_recorded"] is False


def test_host_environment_gate_rejects_false_exclusivity_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    gate = json.loads(e31_analysis.HOST_LIMITATION_GATE.read_text(encoding="utf-8"))
    gate["continuous_host_exclusivity_verified"] = True
    tampered = tmp_path / "host_environment_limitation_gate.json"
    tampered.write_text(json.dumps(gate), encoding="utf-8")
    monkeypatch.setattr(e31_analysis, "HOST_LIMITATION_GATE", tampered)
    with pytest.raises(ValueError, match="host-environment limitation gate is invalid"):
        validate_host_environment_gate(
            gate["protocol_sha256"], gate["design_manifest_sha256"],
        )


def test_transitive_source_gate_rejects_retroactive_prerun_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    gate = json.loads(e31_analysis.TRANSITIVE_SOURCE_GATE.read_text(encoding="utf-8"))
    gate["complete_cryptographic_prerun_source_closure"] = True
    tampered = tmp_path / "transitive_source_provenance_gate.json"
    tampered.write_text(json.dumps(gate), encoding="utf-8")
    monkeypatch.setattr(e31_analysis, "TRANSITIVE_SOURCE_GATE", tampered)
    with pytest.raises(ValueError, match="transitive-source provenance gate is invalid"):
        validate_transitive_source_gate(
            gate["protocol_sha256"], gate["design_manifest_sha256"],
        )


def test_pareto_aggregation_gate_rejects_false_preregistration_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    gate = json.loads(e31_analysis.PARETO_AGGREGATION_GATE.read_text(encoding="utf-8"))
    gate["aggregation_functionals_preregistered_in_protocol"] = True
    tampered = tmp_path / "posthoc_pareto_aggregation_gate.json"
    tampered.write_text(json.dumps(gate), encoding="utf-8")
    monkeypatch.setattr(e31_analysis, "PARETO_AGGREGATION_GATE", tampered)
    with pytest.raises(ValueError, match="Pareto aggregation limitation gate is invalid"):
        validate_pareto_aggregation_gate(
            gate["protocol_sha256"], gate["design_manifest_sha256"],
        )


def test_contrast_expansion_gate_rejects_false_preregistration_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    gate = json.loads(e31_analysis.CONTRAST_EXPANSION_GATE.read_text(encoding="utf-8"))
    gate["fully_preregistered_scalar_contrast_family"] = True
    tampered = tmp_path / "posthoc_contrast_expansion_gate.json"
    tampered.write_text(json.dumps(gate), encoding="utf-8")
    monkeypatch.setattr(e31_analysis, "CONTRAST_EXPANSION_GATE", tampered)
    with pytest.raises(ValueError, match="contrast-expansion limitation gate is invalid"):
        validate_contrast_expansion_gate(
            gate["protocol_sha256"], gate["design_manifest_sha256"],
        )
