"""Oracles and fail-closed tests for the E31 family-inference correction."""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import t as student_t

from analysis.e31_factorial_pareto_analysis import fit_full_factorial_model
from analysis.e31_posthoc_family_inference import (
    DEFAULT_CONTRAST_GATE,
    DEFAULT_CORRECTION_GATE,
    DEFAULT_PROTOCOL,
    LEGACY_INVALID_FIELDS,
    effect_matrices,
    fixed_panel_descriptive,
    supportive_family_inference,
    validate_complete_panel,
    validate_correction_gate,
    wild_cluster_bootstrap_t_pvalues,
)


ROOT = Path(__file__).resolve().parents[1]


def _protocol() -> dict:
    return json.loads(DEFAULT_PROTOCOL.read_text(encoding="utf-8"))


def _synthetic_panel(
    family_effects: list[float], *, inputs_per_family: list[int] | None = None,
) -> pd.DataFrame:
    protocol = _protocol()
    if inputs_per_family is None:
        inputs_per_family = [1] * len(family_effects)
    rows: list[dict[str, object]] = []
    input_index = 0
    for family_index, (family_effect, n_inputs) in enumerate(
        zip(family_effects, inputs_per_family)
    ):
        for _ in range(n_inputs):
            input_hash = f"{input_index:064x}"
            input_index += 1
            for listing, rule, window, budget in product(
                protocol["factors"]["listing_model"],
                protocol["factors"]["rule_set"],
                protocol["factors"]["window_gates"],
                protocol["factors"]["budget_seconds"],
            ):
                wcl = float(listing == "WCL")
                plus = float(rule == "COMMUTATION_PLUS_TEMPLATES")
                value = family_index / 10.0 + family_effect * wcl + 3.0 * plus + 4.0 * wcl * plus
                rows.append({
                    "input_circuit_sha256": input_hash,
                    "circuit_family": f"family-{family_index:02d}",
                    "listing_model": listing,
                    "rule_set": rule,
                    "window_gates": window,
                    "budget_seconds": budget,
                    "common_basis_gate_reduction_pct_itt": value,
                })
    return pd.DataFrame(rows)


def _matrices(frame: pd.DataFrame, *, expected_inputs: int | None = None) -> dict[str, object]:
    pivot, metadata, levels = validate_complete_panel(
        frame, _protocol(), expected_inputs=expected_inputs,
        expected_families=len(frame["circuit_family"].unique()),
    )
    return effect_matrices(pivot, metadata, levels)


def test_factorial_and_marginal_point_estimate_oracle_and_legacy_fields_removed():
    source = _synthetic_panel([2.0] * 15)
    matrices = _matrices(source, expected_inputs=15)
    assert len(matrices["factorial_labels"]) == 71
    assert len(matrices["marginal_labels"]) == 30
    factorial = fixed_panel_descriptive(
        matrices["input_71"], matrices["factorial_labels"], role="test"
    )
    marginal = fixed_panel_descriptive(
        matrices["input_30"], matrices["marginal_labels"], role="test"
    )
    wcl = factorial.loc[
        factorial["coefficient"].eq("C(listing_model)[T.WCL]"),
        "fixed_391_input_weighted_estimate_pp",
    ].item()
    interaction = factorial.loc[
        factorial["coefficient"].eq(
            "C(listing_model)[T.WCL]:C(rule_set)[T.COMMUTATION_PLUS_TEMPLATES]"
        ),
        "fixed_391_input_weighted_estimate_pp",
    ].item()
    marginal_wcl = marginal.loc[
        marginal["coefficient"].eq("MARGINAL::listing_model[WCL-vs-LBL]"),
        "fixed_391_input_weighted_estimate_pp",
    ].item()
    assert wcl == pytest.approx(2.0)
    assert interaction == pytest.approx(4.0)
    assert marginal_wcl == pytest.approx(4.0)  # 2 + mean_rule(4 * indicator) = 4
    assert factorial["legacy_input_cluster_inference_status"].eq(
        "INVALID_WRONG_OUTER_CLUSTER"
    ).all()
    assert marginal["invalid_legacy_fields"].eq("|".join(LEGACY_INVALID_FIELDS)).all()
    assert not set(LEGACY_INVALID_FIELDS).intersection(factorial.columns)
    assert factorial["design_based_p_value"].isna().all()
    assert factorial["design_based_confidence_interval"].isna().all()
    # The correction preserves, rather than silently redefines, the legacy 71
    # point estimates. Only the old uncertainty columns are invalidated.
    legacy_points, _ = fit_full_factorial_model(source)
    merged = factorial.merge(
        legacy_points[["coefficient", "estimate_pp"]], on="coefficient",
        validate="one_to_one",
    )
    assert len(merged) == 71
    assert np.allclose(
        merged["fixed_391_input_weighted_estimate_pp"], merged["estimate_pp"],
        atol=1e-10, rtol=0.0,
    )


def test_fixed_panel_input_weighting_is_not_equal_family_weighting():
    effects = [10.0] + [0.0] * 14
    frame = _synthetic_panel(effects, inputs_per_family=[2] + [1] * 14)
    matrices = _matrices(frame, expected_inputs=16)
    label = "C(listing_model)[T.WCL]"
    fixed = float(matrices["input_71"][label].mean())
    equal_family = float(matrices["family_71"][label].mean())
    assert fixed == pytest.approx(20.0 / 16.0)
    assert equal_family == pytest.approx(10.0 / 15.0)
    assert fixed != pytest.approx(equal_family)


def test_t14_hand_oracle_and_reproducible_wild_cluster_sensitivity():
    # The integers -7..7 have mean 0 and sum of squares 280; adding one gives
    # mean 1, sample variance 20, SE sqrt(20/15), and t=sqrt(3)/2.
    values = np.arange(-7.0, 8.0) + 1.0
    frame = pd.DataFrame({"circuit_family": [f"f{i}" for i in range(15)], "x": values})
    result = supportive_family_inference(
        frame, ["x"], role="test", multiplicity_id="test",
        bootstrap_replicates=999, bootstrap_seed=123,
    ).iloc[0]
    expected_se = np.sqrt(20.0 / 15.0)
    expected_t = 1.0 / expected_se
    expected_p = 2.0 * student_t.sf(abs(expected_t), 14)
    critical = student_t.ppf(0.975, 14)
    assert result["equal_family_estimate_pp"] == pytest.approx(1.0)
    assert result["family_cluster_se_pp"] == pytest.approx(expected_se)
    assert result["family_cluster_df"] == 14
    assert result["t14_p_value_model_based"] == pytest.approx(expected_p)
    assert result["t14_ci95_low_pp"] == pytest.approx(1.0 - critical * expected_se)
    first = wild_cluster_bootstrap_t_pvalues(values[:, None], replicates=999, seed=123)
    second = wild_cluster_bootstrap_t_pvalues(values[:, None], replicates=999, seed=123)
    assert first.tolist() == second.tolist()
    assert result["wild_cluster_bootstrap_t_p_value"] == pytest.approx(first[0])
    assert 1.0 / 1000.0 <= first[0] <= 1.0


def test_constant_effect_oracle_handles_zero_family_variance_without_nan():
    frame = pd.DataFrame({"circuit_family": [f"f{i}" for i in range(15)], "x": [4.0] * 15})
    result = supportive_family_inference(
        frame, ["x"], role="test", multiplicity_id="test",
        bootstrap_replicates=99, bootstrap_seed=7,
    ).iloc[0]
    assert result["equal_family_estimate_pp"] == 4.0
    assert result["family_cluster_se_pp"] == 0.0
    assert result["t14_p_value_model_based"] == 0.0
    assert result["t14_ci95_low_pp"] == 4.0
    assert result["t14_ci95_high_pp"] == 4.0
    assert np.isfinite(result["wild_cluster_bootstrap_t_p_value"])


def test_complete_panel_and_family_df_fail_closed_on_pseudoreplication():
    incomplete = _synthetic_panel([1.0] * 15).iloc[:-1].copy()
    with pytest.raises(ValueError, match="complete 72-cell panel"):
        validate_complete_panel(
            incomplete, _protocol(), expected_inputs=15, expected_families=15
        )
    thirteen = pd.DataFrame({
        "circuit_family": [f"f{i}" for i in range(13)],
        "x": np.arange(13, dtype=float),
    })
    with pytest.raises(ValueError, match="exactly 15 family clusters"):
        supportive_family_inference(
            thirteen, ["x"], role="test", multiplicity_id="test",
            bootstrap_replicates=9,
        )


def test_gate_binds_protocol_contrasts_disclosure_and_all_invalid_fields():
    gate = json.loads(DEFAULT_CORRECTION_GATE.read_text(encoding="utf-8"))
    protocol = _protocol()
    contrast_gate = json.loads(DEFAULT_CONTRAST_GATE.read_text(encoding="utf-8"))
    validate_correction_gate(gate, protocol, contrast_gate)
    tampered = dict(gate)
    tampered["legacy_invalid_fields"] = LEGACY_INVALID_FIELDS[:-1]
    with pytest.raises(ValueError, match="does not invalidate every legacy field"):
        validate_correction_gate(tampered, protocol, contrast_gate)
    tampered = dict(gate)
    tampered["outer_inference_cluster"] = "input_circuit_sha256"
    with pytest.raises(ValueError, match="semantically invalid"):
        validate_correction_gate(tampered, protocol, contrast_gate)


def test_gate_primary_roles_forbid_confirmatory_unseen_family_claim():
    gate = json.loads(DEFAULT_CORRECTION_GATE.read_text(encoding="utf-8"))
    primary = gate["primary_estimand_validity"]
    assert primary["A_fixed_panel_point_estimate"] == "VALID_FROM_SEALED_COMPLETE_PANEL"
    assert primary["A_design_based_p_value"] is None
    assert primary["A_design_based_confidence_interval"] is None
    assert primary["B_t14_interval_and_test"] == "SUPPORTIVE_MODEL_BASED_ONLY"
    assert gate["unseen_family_generalization_status"] == "BLOCKED"
    assert gate["confirmatory_relabeling_authorized"] is False


def test_frozen_marginal_member_order_may_differ_from_protocol_level_order():
    source = _synthetic_panel([2.0] * 15)
    matrices = _matrices(source, expected_inputs=15)
    gate = json.loads(DEFAULT_CORRECTION_GATE.read_text(encoding="utf-8"))
    computed = list(matrices["marginal_labels"])
    frozen = list(gate["marginal_contrast_labels"])
    assert computed != frozen
    assert set(computed) == set(frozen)
    reordered = matrices["input_30"].reindex(
        columns=["input_circuit_sha256", "circuit_family", *frozen]
    )
    assert reordered.columns.tolist()[2:] == frozen
    assert reordered[frozen].notna().all().all()
