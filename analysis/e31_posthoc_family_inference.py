"""Post-hoc E31 inference correction at the protocol's family-cluster level.

This module is intentionally separate from the frozen execution sources and from
``e31_factorial_pareto_analysis.py``.  It does not change any executed row.  It
reclassifies the legacy 71/30 input-cluster inferential fields as invalid while
preserving their fixed-panel point estimates, and computes a distinct,
equal-family-weighted supportive analysis using the 15 circuit families.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations, product
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from statsmodels.stats.multitest import multipletests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "experiments/e31_factorial_pareto_protocol.json"
DEFAULT_DESIGN = ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv"
DEFAULT_CORRECTION_GATE = (
    ROOT / "data/v11/e31_factorial_pareto/posthoc_family_inference_correction_gate.json"
)
DEFAULT_CONTRAST_GATE = (
    ROOT / "data/v11/e31_factorial_pareto/posthoc_contrast_expansion_gate.json"
)

FACTORS = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
RESPONSE = "common_basis_gate_reduction_pct_itt"
LEGACY_INVALID_FIELDS = [
    "cluster_robust_se_pp",
    "ci95_low_pp",
    "ci95_high_pp",
    "p_value_model_based",
    "holm_adjusted_p_within_role",
]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_bool(series: pd.Series, *, label: str) -> pd.Series:
    values: list[bool] = []
    for value in series.tolist():
        if isinstance(value, (bool, np.bool_)):
            values.append(bool(value))
            continue
        if isinstance(value, (int, np.integer)) and value in (0, 1):
            values.append(bool(value))
            continue
        if isinstance(value, str) and value.strip().lower() in {"true", "false", "1", "0"}:
            values.append(value.strip().lower() in {"true", "1"})
            continue
        raise ValueError(f"{label} contains a non-canonical boolean value: {value!r}")
    return pd.Series(values, index=series.index, dtype=bool)


def prepare_itt_response(results: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with the fail-closed ITT response derived when necessary."""
    frame = results.copy()
    if RESPONSE in frame.columns:
        response = pd.to_numeric(frame[RESPONSE], errors="coerce")
        if response.isna().any() or not np.isfinite(response.to_numpy(float)).all():
            raise ValueError("E31 ITT response contains non-finite values")
        frame[RESPONSE] = response.astype(float)
        return frame
    needed = {"valid_equivalent_output", "common_basis_gate_reduction_pct"}
    missing = needed.difference(frame.columns)
    if missing:
        raise ValueError(f"cannot derive E31 ITT response; missing {sorted(missing)}")
    valid = _strict_bool(frame["valid_equivalent_output"], label="valid_equivalent_output")
    reduction = pd.to_numeric(frame["common_basis_gate_reduction_pct"], errors="coerce")
    if reduction.isna().any() or not np.isfinite(reduction.to_numpy(float)).all():
        raise ValueError("common_basis_gate_reduction_pct contains non-finite values")
    frame[RESPONSE] = np.where(valid, reduction.astype(float), 0.0)
    return frame


def canonical_levels(protocol: dict[str, object]) -> dict[str, list[object]]:
    factors = protocol.get("factors")
    if not isinstance(factors, dict):
        raise ValueError("protocol lacks factor levels")
    levels = {factor: list(factors[factor]) for factor in FACTORS}
    if any(not values for values in levels.values()):
        raise ValueError("protocol contains an empty factor")
    return levels


def validate_complete_panel(
    results: pd.DataFrame,
    protocol: dict[str, object],
    *,
    expected_inputs: int | None = 391,
    expected_families: int | None = 15,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, list[object]]]:
    """Validate and return (input-by-cell response, input metadata, levels)."""
    frame = prepare_itt_response(results)
    required = {"input_circuit_sha256", "circuit_family", RESPONSE, *FACTORS}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"E31 family correction lacks columns: {sorted(missing)}")
    levels = canonical_levels(protocol)
    for factor in FACTORS:
        observed = set(frame[factor].tolist())
        expected = set(levels[factor])
        if observed != expected:
            raise ValueError(f"E31 factor level drift for {factor}")
    identity = ["input_circuit_sha256", *FACTORS]
    if frame.duplicated(identity).any():
        raise ValueError("E31 correction panel contains duplicate input-by-cell rows")
    family_counts = frame.groupby("input_circuit_sha256")["circuit_family"].nunique()
    if not family_counts.eq(1).all():
        raise ValueError("an E31 input hash maps to multiple circuit families")
    metadata = (
        frame[["input_circuit_sha256", "circuit_family"]]
        .drop_duplicates()
        .sort_values("input_circuit_sha256", kind="stable")
        .reset_index(drop=True)
    )
    if expected_inputs is not None and len(metadata) != expected_inputs:
        raise ValueError(f"E31 correction requires {expected_inputs} unique inputs")
    n_families = metadata["circuit_family"].nunique()
    if expected_families is not None and n_families != expected_families:
        raise ValueError(f"E31 correction requires {expected_families} circuit families")
    cells = pd.MultiIndex.from_product(
        [levels[factor] for factor in FACTORS], names=FACTORS
    )
    pivot = frame.pivot(index="input_circuit_sha256", columns=FACTORS, values=RESPONSE)
    pivot = pivot.reindex(index=metadata["input_circuit_sha256"], columns=cells)
    if pivot.isna().any().any() or pivot.shape[1] != 72:
        raise ValueError("E31 correction requires one complete 72-cell panel per input")
    expected_rows = len(metadata) * len(cells)
    if len(frame) != expected_rows:
        raise ValueError("E31 correction panel has rows outside the complete factorial")
    return pivot.astype(float), metadata, levels


def _factorial_design(
    levels: dict[str, list[object]],
) -> tuple[pd.MultiIndex, np.ndarray, list[str]]:
    cells = pd.MultiIndex.from_product([levels[factor] for factor in FACTORS], names=FACTORS)
    cell_frame = cells.to_frame(index=False)
    columns: list[np.ndarray] = [np.ones(len(cells), dtype=float)]
    labels = ["Intercept"]
    for order in range(1, len(FACTORS) + 1):
        for selected_factors in combinations(FACTORS, order):
            alternatives = [levels[factor][1:] for factor in selected_factors]
            for selected_values in product(*alternatives):
                indicator = np.ones(len(cells), dtype=float)
                pieces: list[str] = []
                for factor, value in zip(selected_factors, selected_values):
                    indicator *= cell_frame[factor].eq(value).to_numpy(float)
                    pieces.append(f"C({factor})[T.{value}]")
                columns.append(indicator)
                labels.append(":".join(pieces))
    matrix = np.column_stack(columns)
    if matrix.shape != (72, 72) or np.linalg.matrix_rank(matrix) != 72:
        raise ValueError("E31 treatment-coded factorial matrix is not saturated")
    return cells, matrix, labels


def _marginal_contrast_matrix(
    levels: dict[str, list[object]],
) -> tuple[pd.MultiIndex, np.ndarray, list[str]]:
    cells = pd.MultiIndex.from_product([levels[factor] for factor in FACTORS], names=FACTORS)
    cell_lookup = {tuple(cell): index for index, cell in enumerate(cells.tolist())}
    vectors: list[np.ndarray] = []
    labels: list[str] = []
    for order in (1, 2):
        for factor_indices in combinations(range(len(FACTORS)), order):
            alternatives = [levels[FACTORS[index]][1:] for index in factor_indices]
            for selected_values in product(*alternatives):
                selected = dict(zip(factor_indices, selected_values))
                if (order == 2 and selected.get(0) == "WCL"
                        and selected.get(1) == "COMMUTATION_PLUS_TEMPLATES"):
                    continue
                nuisance_indices = [
                    index for index in range(len(FACTORS)) if index not in selected
                ]
                nuisance_cells = list(product(*[
                    levels[FACTORS[index]] for index in nuisance_indices
                ]))
                vector = np.zeros(len(cells), dtype=float)
                for nuisance_values in nuisance_cells:
                    nuisance = dict(zip(nuisance_indices, nuisance_values))
                    for subset_size in range(order + 1):
                        for subset in combinations(factor_indices, subset_size):
                            active = set(subset)
                            cell = tuple(
                                selected[index] if index in active
                                else levels[factor][0] if index in selected
                                else nuisance[index]
                                for index, factor in enumerate(FACTORS)
                            )
                            sign = -1.0 if (order - subset_size) % 2 else 1.0
                            vector[cell_lookup[cell]] += sign / len(nuisance_cells)
                label = ":".join(
                    f"{FACTORS[index]}[{selected[index]}-vs-{levels[FACTORS[index]][0]}]"
                    for index in factor_indices
                )
                vectors.append(vector)
                labels.append(f"MARGINAL::{label}")
    if len(labels) != 30:
        raise ValueError("E31 marginal contrast family must contain exactly 30 members")
    return cells, np.column_stack(vectors), labels


def effect_matrices(
    input_cells: pd.DataFrame,
    metadata: pd.DataFrame,
    levels: dict[str, list[object]],
) -> dict[str, object]:
    """Compute per-input and per-family effects for the 71 and 30 families."""
    factorial_cells, design, factorial_labels = _factorial_design(levels)
    marginal_cells, marginal_matrix, marginal_labels = _marginal_contrast_matrix(levels)
    aligned = input_cells.reindex(columns=factorial_cells)
    if not factorial_cells.equals(marginal_cells) or aligned.isna().any().any():
        raise ValueError("E31 cell ordering drifted during inference correction")
    responses = aligned.to_numpy(float)
    inverse_design = np.linalg.inv(design)
    per_input_71 = responses @ inverse_design.T
    per_input_71 = per_input_71[:, 1:]
    per_input_30 = responses @ marginal_matrix
    family_names = metadata["circuit_family"].astype(str).to_numpy()

    def aggregate(values: np.ndarray, labels: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
        input_effects = pd.DataFrame(values, columns=labels)
        input_effects.insert(0, "circuit_family", family_names)
        input_effects.insert(0, "input_circuit_sha256", metadata["input_circuit_sha256"].to_numpy())
        family_effects = (
            input_effects.groupby("circuit_family", sort=True)[labels]
            .mean()
            .reset_index()
        )
        return input_effects, family_effects

    input_71, family_71 = aggregate(per_input_71, factorial_labels[1:])
    input_30, family_30 = aggregate(per_input_30, marginal_labels)
    return {
        "factorial_labels": factorial_labels[1:],
        "marginal_labels": marginal_labels,
        "input_71": input_71,
        "family_71": family_71,
        "input_30": input_30,
        "family_30": family_30,
    }


def wild_cluster_bootstrap_t_pvalues(
    effects: np.ndarray,
    *,
    replicates: int = 19_999,
    seed: int = 20260826,
) -> np.ndarray:
    """Restricted Rademacher wild-cluster bootstrap-t sensitivity p-values.

    Rows are independent circuit-family clusters and columns are effects.  The
    bootstrap imposes the zero-mean null and is a small-cluster *sensitivity*,
    not a design-based test; validity additionally relies on an exchangeable,
    approximately sign-symmetric family-effect model.
    """
    values = np.asarray(effects, dtype=float)
    if values.ndim != 2 or values.shape[0] < 2:
        raise ValueError("wild cluster bootstrap requires at least two family clusters")
    if not np.isfinite(values).all() or replicates < 1:
        raise ValueError("wild cluster bootstrap received invalid values or replicate count")
    clusters = values.shape[0]
    observed_se = values.std(axis=0, ddof=1) / np.sqrt(clusters)
    observed_mean = values.mean(axis=0)
    observed_fallback = np.zeros_like(observed_mean, dtype=float)
    observed_fallback[observed_mean > 0.0] = np.inf
    observed_fallback[observed_mean < 0.0] = -np.inf
    observed_t = np.divide(
        observed_mean, observed_se,
        out=observed_fallback,
        where=observed_se > 0.0,
    )
    rng = np.random.default_rng(seed)
    weights = rng.choice(np.array([-1.0, 1.0]), size=(replicates, clusters))
    boot_values = weights[:, :, None] * values[None, :, :]
    boot_mean = boot_values.mean(axis=1)
    boot_se = boot_values.std(axis=1, ddof=1) / np.sqrt(clusters)
    boot_fallback = np.zeros_like(boot_mean, dtype=float)
    boot_fallback[boot_mean > 0.0] = np.inf
    boot_fallback[boot_mean < 0.0] = -np.inf
    boot_t = np.divide(
        boot_mean, boot_se,
        out=boot_fallback,
        where=boot_se > 0.0,
    )
    exceed = np.sum(np.abs(boot_t) >= (np.abs(observed_t)[None, :] - 1e-12), axis=0)
    return (exceed + 1.0) / (replicates + 1.0)


def supportive_family_inference(
    family_effects: pd.DataFrame,
    labels: Iterable[str],
    *,
    role: str,
    multiplicity_id: str,
    alpha: float = 0.05,
    bootstrap_replicates: int = 19_999,
    bootstrap_seed: int = 20260826,
) -> pd.DataFrame:
    """Compute equal-family t(14) inference plus wild-cluster sensitivity."""
    labels = list(labels)
    values = family_effects[labels].to_numpy(float)
    clusters = values.shape[0]
    if clusters != 15:
        raise ValueError("supportive E31 inference requires exactly 15 family clusters")
    estimates = values.mean(axis=0)
    standard_errors = values.std(axis=0, ddof=1) / np.sqrt(clusters)
    statistic_fallback = np.zeros_like(estimates, dtype=float)
    statistic_fallback[estimates > 0.0] = np.inf
    statistic_fallback[estimates < 0.0] = -np.inf
    t_statistics = np.divide(
        estimates, standard_errors,
        out=statistic_fallback,
        where=standard_errors > 0.0,
    )
    df = clusters - 1
    p_values = 2.0 * student_t.sf(np.abs(t_statistics), df)
    critical = float(student_t.ppf(1.0 - alpha / 2.0, df))
    wild_p = wild_cluster_bootstrap_t_pvalues(
        values, replicates=bootstrap_replicates, seed=bootstrap_seed,
    )
    output = pd.DataFrame({
        "coefficient": labels,
        "equal_family_estimate_pp": estimates,
        "family_cluster_se_pp": standard_errors,
        "family_cluster_df": df,
        "t14_ci95_low_pp": estimates - critical * standard_errors,
        "t14_ci95_high_pp": estimates + critical * standard_errors,
        "t14_p_value_model_based": p_values,
        "wild_cluster_bootstrap_t_p_value": wild_p,
        "wild_cluster_bootstrap_replicates": bootstrap_replicates,
        "wild_cluster_bootstrap_seed": bootstrap_seed,
        "inference_role": role,
        "confirmatory_claim_allowed": False,
        "probability_sample_of_families": False,
        "unseen_family_generalization_status": "BLOCKED",
        "multiplicity_family_id": multiplicity_id,
        "multiplicity_family_size": len(labels),
    })
    output["holm_adjusted_t14_p"] = multipletests(p_values, method="holm")[1]
    output["holm_adjusted_wild_cluster_p"] = multipletests(wild_p, method="holm")[1]
    return output


def fixed_panel_descriptive(
    input_effects: pd.DataFrame,
    labels: Iterable[str],
    *,
    role: str,
) -> pd.DataFrame:
    """Preserve point estimates and explicitly omit invalid legacy inference."""
    labels = list(labels)
    values = input_effects[labels].to_numpy(float)
    return pd.DataFrame({
        "coefficient": labels,
        "fixed_391_input_weighted_estimate_pp": values.mean(axis=0),
        "population": "FROZEN_391_INPUT_FIXED_PANEL",
        "estimate_role": role,
        "inference_status": "DESCRIPTIVE_POINT_ESTIMATE_ONLY",
        "legacy_input_cluster_inference_status": "INVALID_WRONG_OUTER_CLUSTER",
        "invalid_legacy_fields": "|".join(LEGACY_INVALID_FIELDS),
        "design_based_p_value": None,
        "design_based_confidence_interval": None,
    })


def _primary_vector(levels: dict[str, list[object]]) -> tuple[pd.MultiIndex, np.ndarray]:
    cells = pd.MultiIndex.from_product([levels[factor] for factor in FACTORS], names=FACTORS)
    frame = cells.to_frame(index=False)
    vector = np.zeros(len(cells), dtype=float)
    for rule_set, listing_model, sign in (
        ("COMMUTATION_PLUS_TEMPLATES", "WCL", 1.0),
        ("COMMUTATION_PLUS_TEMPLATES", "LBL", -1.0),
        ("COMMUTATION_ONLY", "WCL", -1.0),
        ("COMMUTATION_ONLY", "LBL", 1.0),
    ):
        mask = frame["rule_set"].eq(rule_set) & frame["listing_model"].eq(listing_model)
        vector[mask.to_numpy()] = sign / 12.0
    return cells, vector


def primary_validity_audit(
    input_cells: pd.DataFrame,
    metadata: pd.DataFrame,
    levels: dict[str, list[object]],
    *,
    alpha: float,
    bootstrap_replicates: int,
    bootstrap_seed: int,
) -> dict[str, object]:
    cells, vector = _primary_vector(levels)
    effects = input_cells.reindex(columns=cells).to_numpy(float) @ vector
    table = pd.DataFrame({
        "circuit_family": metadata["circuit_family"].astype(str).to_numpy(),
        "effect": effects,
    })
    family = table.groupby("circuit_family", sort=True)["effect"].mean().to_numpy(float)
    inference = supportive_family_inference(
        pd.DataFrame({"circuit_family": sorted(table["circuit_family"].unique()),
                      "primary": family}),
        ["primary"],
        role="SUPPORTIVE_MODEL_BASED_EXTRAPOLATION_NO_CONFIRMATORY_CLAIM",
        multiplicity_id="E31_PRIMARY_B_SINGLE_SUPPORTIVE",
        alpha=alpha,
        bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed,
    ).iloc[0]
    return {
        "primary_contrast": "grid-averaged listing-by-rule-set interaction",
        "fixed_benchmark_A": {
            "estimate_pp": float(effects.mean()),
            "point_estimate_status": "VALID_EXACT_FIXED_PANEL_DESCRIPTION",
            "confirmatory_mcid_decision_status": "VALID_IF_COMPUTED_FROM_SEALED_COMPLETE_PANEL",
            "design_based_p_value": None,
            "design_based_confidence_interval": None,
            "inference_status": "NOT_IDENTIFIED_NO_TREATMENT_RANDOMIZATION",
        },
        "new_family_generalized_B": {
            "estimate_pp": float(inference["equal_family_estimate_pp"]),
            "family_cluster_se_pp": float(inference["family_cluster_se_pp"]),
            "family_cluster_df": int(inference["family_cluster_df"]),
            "t14_ci95": [float(inference["t14_ci95_low_pp"]),
                          float(inference["t14_ci95_high_pp"])],
            "t14_p_value_model_based": float(inference["t14_p_value_model_based"]),
            "wild_cluster_bootstrap_t_p_value": float(
                inference["wild_cluster_bootstrap_t_p_value"]
            ),
            "point_estimate_status": "VALID_EQUAL_FAMILY_DESCRIPTION",
            "inference_role": "SUPPORTIVE_MODEL_BASED_EXTRAPOLATION_NO_CONFIRMATORY_CLAIM",
            "confirmatory_claim_allowed": False,
            "unseen_family_generalization_status": "BLOCKED",
            "probability_sample_of_families": False,
        },
    }


def validate_correction_gate(
    gate: dict[str, object],
    protocol: dict[str, object],
    contrast_gate: dict[str, object],
    *,
    protocol_path: Path = DEFAULT_PROTOCOL,
    design_path: Path = DEFAULT_DESIGN,
) -> None:
    """Fail closed on the method-correction contract before reading results."""
    expected = {
        "status": "POSTHOC_FAMILY_INFERENCE_CORRECTION_FROZEN_BEFORE_FORMAL_RESULT_SEAL",
        "changes_to_frozen_execution": False,
        "outer_inference_cluster": "circuit_family",
        "n_independent_family_clusters": 15,
        "family_cluster_degrees_of_freedom": 14,
        "fixed_panel_point_estimates_retained": True,
        "legacy_input_cluster_inference_valid": False,
        "unseen_family_generalization_status": "BLOCKED",
        "confirmatory_relabeling_authorized": False,
    }
    if any(gate.get(key) != value for key, value in expected.items()):
        raise ValueError("E31 family inference correction gate is semantically invalid")
    if gate.get("protocol_sha256") != file_sha256(protocol_path):
        raise ValueError("E31 family inference correction protocol hash mismatch")
    if gate.get("design_manifest_sha256") != file_sha256(design_path):
        raise ValueError("E31 family inference correction design hash mismatch")
    if gate.get("contrast_expansion_gate_sha256") != file_sha256(DEFAULT_CONTRAST_GATE):
        raise ValueError("E31 family inference correction contrast-gate hash mismatch")
    if gate.get("legacy_invalid_fields") != LEGACY_INVALID_FIELDS:
        raise ValueError("E31 family inference correction does not invalidate every legacy field")
    wild = gate.get("small_cluster_sensitivity")
    if not isinstance(wild, dict) or wild.get("method") != "RESTRICTED_RADEMACHER_WILD_CLUSTER_BOOTSTRAP_T":
        raise ValueError("E31 family inference correction lacks the wild-cluster sensitivity")
    if wild.get("seed") != 20260826 or wild.get("replicates") != 19_999:
        raise ValueError("E31 family inference correction bootstrap is not reproducibly frozen")
    if protocol.get("outer_inference_cluster") != "circuit_family":
        raise ValueError("E31 protocol no longer identifies circuit_family as outer cluster")
    if protocol.get("power_gate", {}).get("new_family_generalized_decision") != "BLOCK":
        raise ValueError("E31 generalized-family claim is no longer blocked by protocol")
    if contrast_gate.get("contrast_labels") != gate.get("marginal_contrast_labels"):
        raise ValueError("E31 family correction marginal contrast membership drifted")
    disclosure = ROOT / str(gate.get("disclosure_path", ""))
    if not disclosure.is_file() or gate.get("disclosure_sha256") != file_sha256(disclosure):
        raise ValueError("E31 family inference correction disclosure hash mismatch")
    implementation = ROOT / str(gate.get("implementation_path", ""))
    if (not implementation.is_file()
            or gate.get("implementation_sha256") != file_sha256(implementation)):
        raise ValueError("E31 family inference correction implementation hash mismatch")
    test_path = ROOT / str(gate.get("oracle_test_path", ""))
    if not test_path.is_file() or gate.get("oracle_test_sha256") != file_sha256(test_path):
        raise ValueError("E31 family inference correction oracle-test hash mismatch")


def write_correction_packet(
    results: pd.DataFrame,
    output_dir: Path,
    *,
    protocol: dict[str, object],
    gate: dict[str, object],
    contrast_gate: dict[str, object],
    results_sha256: str | None = None,
) -> dict[str, object]:
    """Compute and write the complete correction packet from a sealed result panel."""
    validate_correction_gate(gate, protocol, contrast_gate)
    input_cells, metadata, levels = validate_complete_panel(results, protocol)
    matrices = effect_matrices(input_cells, metadata, levels)
    gate_marginal_labels = list(gate["marginal_contrast_labels"])
    computed_marginal_labels = list(matrices["marginal_labels"])
    if (len(set(computed_marginal_labels)) != len(computed_marginal_labels)
            or set(computed_marginal_labels) != set(gate_marginal_labels)):
        raise ValueError("computed E31 marginal labels differ from the correction gate")
    # The protocol order is authoritative for the mathematics, while the
    # contrast gate independently freezes presentation/multiplicity order.
    # Reindex by member label instead of requiring those orderings to coincide.
    matrices["input_30"] = matrices["input_30"].reindex(
        columns=["input_circuit_sha256", "circuit_family", *gate_marginal_labels]
    )
    matrices["family_30"] = matrices["family_30"].reindex(
        columns=["circuit_family", *gate_marginal_labels]
    )
    matrices["marginal_labels"] = gate_marginal_labels
    fixed_71 = fixed_panel_descriptive(
        matrices["input_71"], matrices["factorial_labels"],
        role="EXPLORATORY_PARAMETERIZATION_DIAGNOSTIC_FIXED_PANEL_DESCRIPTION",
    )
    fixed_30 = fixed_panel_descriptive(
        matrices["input_30"], matrices["marginal_labels"],
        role="SUPPORTIVE_POSTHOC_FIXED_PANEL_DESCRIPTION",
    )
    wild = gate["small_cluster_sensitivity"]
    family_71 = supportive_family_inference(
        matrices["family_71"], matrices["factorial_labels"],
        role="EXPLORATORY_EQUAL_FAMILY_MODEL_BASED_SENSITIVITY",
        multiplicity_id="E31_POSTHOC_FACTORIAL_71",
        bootstrap_replicates=int(wild["replicates"]), bootstrap_seed=int(wild["seed"]),
    )
    family_30 = supportive_family_inference(
        matrices["family_30"], matrices["marginal_labels"],
        role="SUPPORTIVE_EQUAL_FAMILY_MODEL_BASED_SENSITIVITY",
        multiplicity_id="E31_POSTHOC_MARGINAL_30",
        bootstrap_replicates=int(wild["replicates"]), bootstrap_seed=int(wild["seed"]),
    )
    primary = primary_validity_audit(
        input_cells, metadata, levels, alpha=0.05,
        bootstrap_replicates=int(wild["replicates"]), bootstrap_seed=int(wild["seed"]),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "fixed_panel_factorial_71_descriptive.csv": fixed_71,
        "fixed_panel_marginal_30_descriptive.csv": fixed_30,
        "family_supportive_factorial_71.csv": family_71,
        "family_supportive_marginal_30.csv": family_30,
        "per_family_factorial_71_effects.csv": matrices["family_71"],
        "per_family_marginal_30_effects.csv": matrices["family_30"],
    }
    for filename, table in files.items():
        table.to_csv(output_dir / filename, index=False)
    (output_dir / "primary_estimand_validity.json").write_text(
        json.dumps(primary, indent=2, sort_keys=True), encoding="utf-8"
    )
    artifact_names = sorted([*files, "primary_estimand_validity.json"])
    artifacts = {}
    for name in artifact_names:
        path = output_dir / name
        record: dict[str, object] = {
            "sha256": file_sha256(path),
            "bytes": path.stat().st_size,
        }
        if name in files:
            record["rows"] = len(files[name])
            record["columns"] = list(files[name].columns)
        artifacts[name] = record
    audit = {
        "status": "PASS_POSTHOC_FAMILY_INFERENCE_CORRECTION",
        "results_sha256": results_sha256,
        "correction_gate_sha256": file_sha256(DEFAULT_CORRECTION_GATE),
        "n_input_hashes": len(metadata),
        "n_independent_family_clusters": metadata["circuit_family"].nunique(),
        "family_cluster_degrees_of_freedom": 14,
        "factorial_descriptive_parameters": len(fixed_71),
        "marginal_descriptive_contrasts": len(fixed_30),
        "legacy_input_cluster_inference_valid": False,
        "legacy_invalid_fields": LEGACY_INVALID_FIELDS,
        "fixed_benchmark_A_point_and_mcid_decision_retained": True,
        "generalized_B_confirmatory_claim_allowed": False,
        "unseen_family_generalization_status": "BLOCKED",
        "implementation_sha256": file_sha256(Path(__file__).resolve()),
        "artifacts": artifacts,
        "written_files": artifact_names,
    }
    (output_dir / "family_inference_correction_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8"
    )
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--correction-gate", type=Path, default=DEFAULT_CORRECTION_GATE)
    parser.add_argument("--contrast-gate", type=Path, default=DEFAULT_CONTRAST_GATE)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.resolve().read_text(encoding="utf-8"))
    gate = json.loads(args.correction_gate.resolve().read_text(encoding="utf-8"))
    contrast_gate = json.loads(args.contrast_gate.resolve().read_text(encoding="utf-8"))
    results_path = args.results.resolve()
    audit = write_correction_packet(
        pd.read_csv(results_path), args.output_dir.resolve(), protocol=protocol,
        gate=gate, contrast_gate=contrast_gate, results_sha256=file_sha256(results_path),
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
