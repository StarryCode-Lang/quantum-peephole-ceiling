"""Validation and descriptive Pareto analysis for the E31 factorial contract.

Formal inference is deliberately gated: a pre-freeze or smoke packet can be
validated and summarized, but cannot be labelled confirmatory.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from itertools import combinations, product
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, t
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

METHOD_ERRATUM_GATE = (
    PROJECT_ROOT / "data/v11/e31_factorial_pareto/preanalysis_method_erratum_gate.json"
)
HOST_LIMITATION_GATE = (
    PROJECT_ROOT / "data/v11/e31_factorial_pareto/host_environment_limitation_gate.json"
)
TRANSITIVE_SOURCE_GATE = (
    PROJECT_ROOT / "data/v11/e31_factorial_pareto/transitive_source_provenance_gate.json"
)
PARETO_AGGREGATION_GATE = (
    PROJECT_ROOT / "data/v11/e31_factorial_pareto/posthoc_pareto_aggregation_gate.json"
)
CONTRAST_EXPANSION_GATE = (
    PROJECT_ROOT / "data/v11/e31_factorial_pareto/posthoc_contrast_expansion_gate.json"
)
TRANSITIVE_SOURCE_PATHS = {
    "experiments/e31_factorial_pareto_design.py",
    "src/circuits/__init__.py", "src/circuits/generator_v2.py",
    "src/equivalence.py", "src/optimisation/__init__.py",
    "src/optimisation/_gate_predicates.py", "src/optimisation/base.py",
    "src/optimisation/ceiling_aware.py", "src/optimisation/constants.py",
    "src/optimisation/phase1/__init__.py",
    "src/optimisation/phase1/genetic_algorithm.py",
    "src/optimisation/phase1/greedy.py",
    "src/optimisation/phase1/random_local_search.py",
    "src/optimisation/phase1/simulated_annealing.py",
    "src/optimisation/phase2/__init__.py",
    "src/optimisation/phase2/commutation_rewriter.py",
}

from experiments.e31_factorial_pareto_design import file_sha256, treatment_cells, validate_design

RESULT_COLUMNS = {
    "run_id", "protocol_sha256", "design_manifest_sha256", "input_circuit_sha256",
    "circuit_id", "circuit_family",
    "listing_model", "rule_set", "window_gates", "budget_seconds", "run_order",
    "primary_pair_orientation",
    "status", "valid_equivalent_output", "exact_fidelity", "output_circuit_sha256",
    "original_common_basis_gate_count", "optimized_common_basis_gate_count",
    "common_basis_gate_reduction_pct",
    "wall_seconds_end_to_end", "peak_rss_mb",
}
ALLOWED_STATUS = {"success", "timeout", "error", "invalid", "unavailable", "oom"}
FACTOR_COLUMNS = ["listing_model", "rule_set", "window_gates", "budget_seconds"]


def _strict_bool_series(values: pd.Series, *, label: str) -> pd.Series:
    """Accept only bool or explicit true/false/1/0 serialization; fail closed otherwise."""
    parsed: list[bool] = []
    for index, value in values.items():
        if isinstance(value, (bool, np.bool_)):
            parsed.append(bool(value))
            continue
        normalized = str(value).strip().lower()
        if normalized in {"true", "1"}:
            parsed.append(True)
        elif normalized in {"false", "0"}:
            parsed.append(False)
        else:
            raise ValueError(
                f"invalid serialized boolean in {label} at index {index}: {value!r}"
            )
    return pd.Series(parsed, index=values.index, dtype=bool)


def validate_method_erratum_gate(protocol_sha256: str, design_sha256: str) -> dict:
    """Bind formal inference to the pre-analysis mathematical correction."""
    if not METHOD_ERRATUM_GATE.is_file():
        raise ValueError("formal analysis lacks the pre-analysis method erratum gate")
    gate = json.loads(METHOD_ERRATUM_GATE.read_text(encoding="utf-8"))
    if gate.get("status") != (
        "PREANALYSIS_MATHEMATICAL_ERRATUM_FROZEN_BEFORE_AGGREGATE_EFFECT_ANALYSIS"
    ):
        raise ValueError("method erratum gate has an invalid status")
    if gate.get("protocol_sha256") != protocol_sha256:
        raise ValueError("method erratum gate protocol SHA mismatch")
    if gate.get("design_manifest_sha256") != design_sha256:
        raise ValueError("method erratum gate design SHA mismatch")
    erratum = PROJECT_ROOT / str(gate["erratum_path"])
    if not erratum.is_file() or file_sha256(erratum) != gate.get("erratum_sha256"):
        raise ValueError("method erratum document is absent or hash-drifted")
    if gate.get("changes_to_frozen_execution") is not False:
        raise ValueError("method erratum gate must not alter frozen execution")
    return gate


def validate_host_environment_gate(protocol_sha256: str, design_sha256: str) -> dict:
    """Require the pre-analysis shared-host disclosure and frozen drift thresholds."""
    if not HOST_LIMITATION_GATE.is_file():
        raise ValueError("formal analysis lacks the host-environment limitation gate")
    gate = json.loads(HOST_LIMITATION_GATE.read_text(encoding="utf-8"))
    boundary = gate.get("checkpoint_boundary", {})
    if (gate.get("status") != "PREANALYSIS_HOST_LIMITATION_FROZEN"
            or gate.get("protocol_sha256") != protocol_sha256
            or gate.get("design_manifest_sha256") != design_sha256
            or gate.get("aggregate_treatment_effects_inspected") is not False
            or gate.get("row_exclusion_or_rerun_authorized") is not False
            or gate.get("continuous_host_exclusivity_verified") is not False
            or gate.get("continuous_host_telemetry_recorded") is not False
            or boundary.get("rows", 28152) >= 28152
            or boundary.get("max_run_order") != boundary.get("rows", 0) - 1
            or gate.get("material_drift_thresholds") != {
                "quality_itt": 1.0, "valid": 0.05, "timeout": 0.05,
                "wall_budget_fraction": 0.05, "peak_rss_mb": 128.0,
            }):
        raise ValueError("host-environment limitation gate is invalid")
    disclosure = PROJECT_ROOT / str(gate.get("disclosure_path", ""))
    if not disclosure.is_file() or file_sha256(disclosure) != gate.get("disclosure_sha256"):
        raise ValueError("host-environment disclosure is absent or hash-drifted")
    return gate


def validate_transitive_source_gate(protocol_sha256: str, design_sha256: str) -> dict:
    """Require the post-hoc import-closure disclosure without upgrading it to pre-run evidence."""
    if not TRANSITIVE_SOURCE_GATE.is_file():
        raise ValueError("formal analysis lacks the transitive-source provenance gate")
    gate = json.loads(TRANSITIVE_SOURCE_GATE.read_text(encoding="utf-8"))
    boundary = gate.get("checkpoint_boundary", {})
    closure = gate.get("omitted_first_party_import_closure", {})
    if (gate.get("status")
            != "POSTHOC_TRANSITIVE_SOURCE_LIMITATION_FROZEN_BEFORE_AGGREGATE_ANALYSIS"
            or gate.get("protocol_sha256") != protocol_sha256
            or gate.get("design_manifest_sha256") != design_sha256
            or gate.get("aggregate_treatment_effects_inspected") is not False
            or gate.get("row_exclusion_or_rerun_authorized") is not False
            or gate.get("historical_environment_rewritten") is not False
            or gate.get("complete_cryptographic_prerun_source_closure") is not False
            or gate.get("timestamp_evidence_is_cryptographic_commitment") is not False
            or gate.get("created_date") != "2026-08-24"
            or gate.get("environment_path")
            != "data/v11/e31_factorial_pareto/formal_run/environment.json"
            or gate.get("disclosure_path")
            != "docs/review/e31_transitive_source_provenance_limitation_2026-08-24.md"
            or gate.get("interpretation")
            != "Conditional release eligibility with a PARTIAL provenance rating; the post-hoc gate cannot be represented as a complete cryptographic pre-run source freeze."
            or gate.get("direct_frozen_source_count") != 7
            or gate.get("omitted_source_count") != 16
            or set(closure) != TRANSITIVE_SOURCE_PATHS
            or boundary.get("committed_rows", 28152) >= 28152
            or boundary.get("min_run_order") != 0
            or boundary.get("max_run_order") != boundary.get("committed_rows", 0) - 1
            or boundary.get("unique_run_ids") != boundary.get("committed_rows")
            or boundary.get("unique_run_orders") != boundary.get("committed_rows")
            or boundary.get("sqlite_integrity") != "ok"
            or sum(boundary.get("status_counts_only", {}).values())
            != boundary.get("committed_rows")):
        raise ValueError("transitive-source provenance gate is invalid")
    try:
        created = datetime.fromisoformat(str(gate.get("created_utc", "")))
        last_boundary = datetime.fromisoformat(str(boundary.get("last_committed_utc", "")))
    except ValueError as error:
        raise ValueError("transitive-source provenance timestamp is invalid") from error
    if created <= last_boundary:
        raise ValueError("transitive-source provenance gate predates its checkpoint boundary")
    environment = PROJECT_ROOT / str(gate.get("environment_path", ""))
    disclosure = PROJECT_ROOT / str(gate.get("disclosure_path", ""))
    if (not environment.is_file()
            or file_sha256(environment) != gate.get("environment_sha256")
            or not disclosure.is_file()
            or file_sha256(disclosure) != gate.get("disclosure_sha256")):
        raise ValueError("transitive-source provenance evidence is absent or hash-drifted")
    first_commit = datetime.fromisoformat(str(boundary.get("first_committed_utc", "")))
    for relative, record in closure.items():
        source = PROJECT_ROOT / relative
        if not source.is_file() or file_sha256(source) != record.get("sha256"):
            raise ValueError(f"post-hoc transitive source hash drift: {relative}")
        if datetime.fromisoformat(str(record.get("last_write_local", ""))) >= first_commit:
            raise ValueError(f"post-hoc transitive source timestamp is not pre-row-0: {relative}")
    return gate


def validate_pareto_aggregation_gate(protocol_sha256: str, design_sha256: str) -> dict:
    """Bind formal Pareto output to the disclosed post-hoc aggregation sensitivity."""
    if not PARETO_AGGREGATION_GATE.is_file():
        raise ValueError("formal analysis lacks the Pareto aggregation limitation gate")
    gate = json.loads(PARETO_AGGREGATION_GATE.read_text(encoding="utf-8"))
    boundary = gate.get("checkpoint_boundary", {})
    sensitivity = gate.get("required_sensitivity_grid", {})
    expected_interpretation = (
        "Pareto results are exploratory and aggregation-conditional; disagreement across "
        "the four frozen post-hoc schemes blocks an aggregation-invariant frontier claim."
    )
    if (gate.get("status")
            != "POSTHOC_PARETO_AGGREGATION_FROZEN_BEFORE_AGGREGATE_ANALYSIS"
            or gate.get("protocol_sha256") != protocol_sha256
            or gate.get("design_manifest_sha256") != design_sha256
            or gate.get("aggregate_treatment_effects_inspected") is not False
            or gate.get("changes_to_frozen_execution") is not False
            or gate.get("row_exclusion_or_rerun_authorized") is not False
            or gate.get("aggregation_functionals_preregistered_in_protocol") is not False
            or gate.get("primary_pareto_inference_role")
            != "EXPLORATORY_POSTHOC_AGGREGATION"
            or gate.get("created_date") != "2026-08-24"
            or gate.get("disclosure_path")
            != "docs/review/e31_pareto_aggregation_limitation_2026-08-24.md"
            or gate.get("primary_descriptive_aggregation") != {
                "quality_itt": "mean", "valid_rate": "mean",
                "wall_seconds": "median", "peak_rss_mb": "p95",
            }
            or sensitivity.get("wall_seconds") != ["median", "p95"]
            or sensitivity.get("peak_rss_mb") != ["median", "p95"]
            or sensitivity.get("expected_schemes") != 4
            or sensitivity.get("expected_treatment_cells_per_scheme") != 72
            or sensitivity.get("artifact")
            != "data/v11/e31_factorial_pareto/formal_run/analysis/pareto_aggregation_sensitivity.csv"
            or gate.get("redundant_objective") != {
                "removed_from_hypervolume": "failure_rate",
                "reason": "failure_rate equals 1 - valid_rate exactly under the frozen row contract",
            }
            or gate.get("interpretation") != expected_interpretation
            or boundary.get("committed_rows", 28152) >= 28152
            or boundary.get("min_run_order") != 0
            or boundary.get("max_run_order") != boundary.get("committed_rows", 0) - 1
            or boundary.get("unique_run_ids") != boundary.get("committed_rows")
            or boundary.get("unique_run_orders") != boundary.get("committed_rows")
            or boundary.get("sqlite_integrity") != "ok"
            or sum(boundary.get("status_counts_only", {}).values())
            != boundary.get("committed_rows")):
        raise ValueError("Pareto aggregation limitation gate is invalid")
    try:
        created = datetime.fromisoformat(str(gate.get("created_utc", "")))
        last_boundary = datetime.fromisoformat(str(boundary.get("last_committed_utc", "")))
    except ValueError as error:
        raise ValueError("Pareto aggregation gate timestamp is invalid") from error
    if created <= last_boundary:
        raise ValueError("Pareto aggregation gate was not created after its checkpoint boundary")
    disclosure = PROJECT_ROOT / str(gate.get("disclosure_path", ""))
    if not disclosure.is_file() or file_sha256(disclosure) != gate.get("disclosure_sha256"):
        raise ValueError("Pareto aggregation disclosure is absent or hash-drifted")
    return gate


def _expected_posthoc_marginal_labels() -> list[str]:
    factors = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    levels: dict[str, list[object]] = {
        "listing_model": ["LBL", "RANDOM_TOPOLOGICAL", "WCL"],
        "rule_set": ["COMMUTATION_ONLY", "COMMUTATION_PLUS_TEMPLATES"],
        "window_gates": [4, 16, 64],
        "budget_seconds": [1, 10, 30, 120],
    }
    labels: list[str] = []
    for order in (1, 2):
        for factor_indices in combinations(range(4), order):
            for selected_values in product(*[levels[factors[index]][1:] for index in factor_indices]):
                selected = dict(zip(factor_indices, selected_values))
                if (factor_indices == (0, 1) and selected[0] == "WCL"
                        and selected[1] == "COMMUTATION_PLUS_TEMPLATES"):
                    continue
                labels.append("MARGINAL::" + ":".join(
                    f"{factors[index]}[{selected[index]}-vs-{levels[factors[index]][0]}]"
                    for index in factor_indices
                ))
    return labels


def validate_contrast_expansion_gate(protocol_sha256: str, design_sha256: str) -> dict:
    """Require the honest post-hoc scalar expansion of the frozen contrast class."""
    if not CONTRAST_EXPANSION_GATE.is_file():
        raise ValueError("formal analysis lacks the contrast-expansion limitation gate")
    gate = json.loads(CONTRAST_EXPANSION_GATE.read_text(encoding="utf-8"))
    boundary = gate.get("checkpoint_boundary", {})
    expected_labels = _expected_posthoc_marginal_labels()
    if (gate.get("status")
            != "POSTHOC_CONTRAST_EXPANSION_FROZEN_BEFORE_AGGREGATE_ANALYSIS"
            or gate.get("created_date") != "2026-08-24"
            or gate.get("disclosure_path")
            != "docs/review/e31_contrast_expansion_limitation_2026-08-24.md"
            or gate.get("protocol_sha256") != protocol_sha256
            or gate.get("design_manifest_sha256") != design_sha256
            or gate.get("aggregate_treatment_effects_inspected") is not False
            or gate.get("changes_to_frozen_execution") is not False
            or gate.get("row_exclusion_or_rerun_authorized") is not False
            or gate.get("fully_preregistered_scalar_contrast_family") is not False
            or gate.get("inference_role")
            != "SUPPORTIVE_POSTHOC_OPERATIONALIZATION_OF_FROZEN_CLASS"
            or gate.get("factor_order")
            != ["listing_model", "rule_set", "window_gates", "budget_seconds"]
            or gate.get("reference_levels") != {
                "listing_model": "LBL", "rule_set": "COMMUTATION_ONLY",
                "window_gates": 4, "budget_seconds": 1,
            }
            or gate.get("nuisance_weighting")
            != "equal weight over every level combination of all non-contrast factors and equal weight over 391 frozen input hashes"
            or gate.get("multiplicity_family") != {
                "id": "E31_POSTHOC_MARGINAL_30", "method": "Holm", "size": 30,
            }
            or gate.get("contrast_labels") != expected_labels
            or gate.get("excluded_primary_contrast")
            != "MARGINAL::listing_model[WCL-vs-LBL]:rule_set[COMMUTATION_PLUS_TEMPLATES-vs-COMMUTATION_ONLY]"
            or gate.get("generalized_estimand_b") != {
                "included_in_multiplicity_family": False,
                "role": "SUPPORTIVE_MODEL_BASED_EXTRAPOLATION_NO_CONFIRMATORY_CLAIM",
                "reason": "same separately frozen primary contrast under a different population extrapolation",
            }
            or boundary.get("committed_rows", 28152) >= 28152
            or boundary.get("min_run_order") != 0
            or boundary.get("max_run_order") != boundary.get("committed_rows", 0) - 1
            or boundary.get("unique_run_ids") != boundary.get("committed_rows")
            or boundary.get("unique_run_orders") != boundary.get("committed_rows")
            or boundary.get("sqlite_integrity") != "ok"
            or sum(boundary.get("status_counts_only", {}).values())
            != boundary.get("committed_rows")):
        raise ValueError("contrast-expansion limitation gate is invalid")
    try:
        created = datetime.fromisoformat(str(gate.get("created_utc", "")))
        last_boundary = datetime.fromisoformat(str(boundary.get("last_committed_utc", "")))
    except ValueError as error:
        raise ValueError("contrast-expansion gate timestamp is invalid") from error
    if created <= last_boundary:
        raise ValueError("contrast-expansion gate was not created after its checkpoint boundary")
    disclosure = PROJECT_ROOT / str(gate.get("disclosure_path", ""))
    if not disclosure.is_file() or file_sha256(disclosure) != gate.get("disclosure_sha256"):
        raise ValueError("contrast-expansion disclosure is absent or hash-drifted")
    return gate


def validate_power_gate(protocol: dict, design_sha256: str) -> dict:
    """Require the prospective fixed-benchmark decision; never borrow B's df."""
    report_path = PROJECT_ROOT / protocol["formal_gate"]["required_power_report"]
    if not report_path.exists():
        raise ValueError("confirmatory analysis lacks the frozen dual-estimand power report")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if float(report["mcid_pp"]) != float(protocol["power_gate"]["mcid_pp"]):
        raise ValueError("power report MCID differs from the frozen protocol")
    protocol_path = PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json"
    if report.get("protocol_sha256") != file_sha256(protocol_path):
        raise ValueError("power report is not bound to the frozen protocol")
    if report.get("design_manifest_sha256") != design_sha256:
        raise ValueError("power report is not bound to this design manifest")
    required = protocol["formal_gate"]["required_fixed_benchmark_power_decision"]
    if report["decision"]["fixed_benchmark_A"] != required:
        raise ValueError("fixed-benchmark prospective power gate is not PASS")
    return report


def family_blocked_randomization_p(*args, **kwargs) -> float:
    """Refuse an invalid design-randomization interpretation.

    E31 is a complete repeated-measures factorial: every input receives both
    listing treatments. ``primary_pair_orientation`` never assigned treatment,
    so permuting it cannot generate the design's treatment-assignment mechanism.
    See the pre-analysis method erratum dated 2026-08-24.
    """
    raise RuntimeError(
        "E31 has no randomized treatment-assignment mechanism; a design-based "
        "randomization p-value is not identified"
    )


def stratified_input_bootstrap_ci(
    per_input: pd.DataFrame, *, replicates: int = 10_000,
    seed: int = 20260811, alpha: float = 0.05,
) -> list[float]:
    """Empirical stability interval preserving the frozen family composition.

    This resamples input hashes within each observed family. It is deliberately
    labelled a sensitivity interval, not a design-based confidence interval.
    """
    if replicates < 1:
        raise ValueError("bootstrap replicates must be positive")
    rng = np.random.default_rng(seed)
    draws = np.zeros(replicates, dtype=float)
    for _, group in per_input.groupby("circuit_family", sort=True):
        values = group["primary_did_pp"].to_numpy(float)
        indices = rng.integers(0, len(values), size=(replicates, len(values)))
        draws += values[indices].sum(axis=1)
    draws /= len(per_input)
    return [float(value) for value in np.quantile(draws, [alpha / 2, 1 - alpha / 2])]


def primary_dual_estimand(
    validated: pd.DataFrame, *, alpha: float = 0.05, mcid_pp: float = 1.0,
    bootstrap_replicates: int = 10_000, bootstrap_seed: int = 20260811,
) -> dict[str, object]:
    """Estimate the single frozen interaction for populations A and B."""
    subset = validated[validated["listing_model"].isin(["LBL", "WCL"])].copy()
    keys = ["input_circuit_sha256", "circuit_family", "window_gates", "budget_seconds"]
    pivot = subset.pivot(index=keys, columns=["rule_set", "listing_model"],
                         values="common_basis_gate_reduction_pct_itt")
    needed = [("COMMUTATION_PLUS_TEMPLATES", "WCL"),
              ("COMMUTATION_PLUS_TEMPLATES", "LBL"),
              ("COMMUTATION_ONLY", "WCL"), ("COMMUTATION_ONLY", "LBL")]
    if any(column not in pivot.columns for column in needed) or pivot[needed].isna().any().any():
        raise ValueError("primary interaction lacks a complete paired four-cell contrast")
    did = ((pivot[needed[0]] - pivot[needed[1]])
           - (pivot[needed[2]] - pivot[needed[3]])).rename("primary_did_pp").reset_index()
    per_input = did.groupby(["input_circuit_sha256", "circuit_family"], as_index=False).agg(
        primary_did_pp=("primary_did_pp", "mean"), grid_cells=("primary_did_pp", "size"))
    if not per_input["grid_cells"].eq(12).all():
        raise ValueError("primary interaction must average exactly 3 x 4 grid cells per input")
    point_a = float(per_input["primary_did_pp"].mean())
    n, families = len(per_input), per_input["circuit_family"].nunique()
    family_means = per_input.groupby("circuit_family", sort=True)["primary_did_pp"].mean()
    lofo = {
        str(family): float(per_input.loc[per_input["circuit_family"].ne(family),
                                         "primary_did_pp"].mean())
        for family in family_means.index
    }
    point_b = float(family_means.mean())
    se_b = float(family_means.std(ddof=1) / np.sqrt(len(family_means)))
    critical_b = float(t.ppf(1 - alpha / 2, len(family_means) - 1))
    return {
        "primary_contrast": "grid-averaged listing-by-rule-set interaction",
        "fixed_benchmark_A": {
            "population": "frozen unique input hashes",
            "n_input_hashes": int(n), "families_as_fixed_blocks": int(families),
            "estimate_pp": point_a,
            "estimand_type": "exact finite-population contrast",
            "mcid_pp": float(mcid_pp),
            "distance_from_mcid_pp": point_a - float(mcid_pp),
            "meets_or_exceeds_mcid": bool(point_a >= float(mcid_pp)),
            "design_based_p_value": None,
            "design_based_confidence_interval": None,
            "design_based_inference_status": "NOT_IDENTIFIED_NO_TREATMENT_RANDOMIZATION",
            "stratified_input_bootstrap_stability_interval": stratified_input_bootstrap_ci(
                per_input, replicates=bootstrap_replicates, seed=bootstrap_seed, alpha=alpha,
            ),
            "stability_interval_role": "EMPIRICAL_SENSITIVITY_NOT_DESIGN_BASED_CI",
            "bootstrap_replicates": int(bootstrap_replicates),
            "bootstrap_seed": int(bootstrap_seed),
            "input_quantiles_pp": {
                str(q): float(per_input["primary_did_pp"].quantile(q))
                for q in (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)
            },
            "family_means_pp": {str(key): float(value) for key, value in family_means.items()},
            "worst_family": str(family_means.idxmin()),
            "worst_family_estimate_pp": float(family_means.min()),
            "leave_one_family_out_estimates_pp": lofo,
            "lofo_sign_stable": bool(all(np.sign(value) == np.sign(point_a) for value in lofo.values())),
        },
        "new_family_generalized_B": {
            "population": "potentially unseen families",
            "n_independent_family_clusters": int(len(family_means)),
            "estimate_pp": point_b, "family_cluster_se_pp": se_b,
            "ci": [point_b - critical_b * se_b, point_b + critical_b * se_b],
            "confirmatory_claim_allowed": False,
            "inference_role": "SUPPORTIVE_MODEL_BASED_EXTRAPOLATION_NO_CONFIRMATORY_CLAIM",
            "probability_sample_of_families": False,
        },
    }


def validate_results(design: pd.DataFrame, results: pd.DataFrame,
                     protocol: dict, *, formal: bool = False,
                     design_sha256: str | None = None,
                     allow_incomplete_smoke: bool = False) -> pd.DataFrame:
    """Validate exact schedule coverage, factor identity, and ITT semantics."""
    validate_design(design, protocol)
    missing = RESULT_COLUMNS.difference(results.columns)
    if missing:
        raise ValueError(f"result packet lacks columns: {sorted(missing)}")
    if results["run_id"].duplicated().any():
        raise ValueError("result packet contains duplicate run_id values")
    if results["protocol_sha256"].astype(str).nunique() != 1 or (
            results["protocol_sha256"].astype(str).iloc[0]
            != design["protocol_sha256"].astype(str).iloc[0]):
        raise ValueError("result packet protocol SHA differs from schedule")
    if results["design_manifest_sha256"].astype(str).nunique() != 1:
        raise ValueError("result packet has multiple design manifest hashes")
    if (design_sha256 is not None
            and results["design_manifest_sha256"].astype(str).iloc[0] != design_sha256):
        raise ValueError("result packet design manifest SHA mismatch")
    expected_ids = set(design["run_id"].astype(str))
    observed_ids = set(results["run_id"].astype(str))
    coverage_ok = (observed_ids.issubset(expected_ids) if allow_incomplete_smoke
                   else observed_ids == expected_ids)
    if not coverage_ok:
        missing_n = len(expected_ids - observed_ids)
        extra_n = len(observed_ids - expected_ids)
        raise ValueError(f"result packet does not equal schedule: missing={missing_n}, extra={extra_n}")
    joined = design[["run_id", "input_circuit_sha256", "circuit_id", "circuit_family",
                     *FACTOR_COLUMNS, "run_order", "primary_pair_orientation"]].merge(
        results, on="run_id", suffixes=("_design", ""), validate="one_to_one"
    )
    for column in ["input_circuit_sha256", "circuit_id", "circuit_family",
                   *FACTOR_COLUMNS, "run_order", "primary_pair_orientation"]:
        if not joined[column].astype(str).equals(joined[f"{column}_design"].astype(str)):
            raise ValueError(f"result metadata drift for {column}")
    if not set(joined["status"].astype(str)).issubset(ALLOWED_STATUS):
        raise ValueError("result packet contains an unknown status")
    numeric = ["common_basis_gate_reduction_pct", "wall_seconds_end_to_end", "peak_rss_mb"]
    if not np.isfinite(joined[numeric].to_numpy(float)).all():
        raise ValueError("result packet contains non-finite primary/resource values")
    if (joined["wall_seconds_end_to_end"].astype(float) < 0).any() or (
            joined["peak_rss_mb"].astype(float) < 0).any():
        raise ValueError("runtime and memory must be non-negative")
    valid = _strict_bool_series(
        joined["valid_equivalent_output"], label="E31 valid_equivalent_output"
    )
    if (valid & joined["status"].ne("success")).any():
        raise ValueError("only successful runs may be marked valid")
    if (joined["status"].eq("success") & ~valid).any():
        raise ValueError("every successful run must be marked valid")
    fidelity = pd.to_numeric(joined["exact_fidelity"], errors="coerce")
    threshold = float(protocol["semantic_contract"]["fidelity_threshold"])
    if (valid & (
            fidelity.isna() | ~np.isfinite(fidelity) | fidelity.lt(threshold)
            | fidelity.gt(1.0 + 1e-12)
    )).any():
        raise ValueError("valid row lacks exact fidelity at the frozen threshold")
    output_hash = joined["output_circuit_sha256"].fillna("").astype(str)
    if (valid & ~output_hash.str.fullmatch(r"[0-9a-f]{64}")).any():
        raise ValueError("valid row lacks an output circuit SHA-256")
    original_count = pd.to_numeric(
        joined["original_common_basis_gate_count"], errors="coerce"
    )
    optimized_count = pd.to_numeric(
        joined["optimized_common_basis_gate_count"], errors="coerce"
    )
    success = joined["status"].eq("success")
    invalid_counts = success & (
        original_count.isna() | optimized_count.isna()
        | original_count.lt(0) | optimized_count.lt(0)
        | original_count.mod(1).ne(0) | optimized_count.mod(1).ne(0)
    )
    if invalid_counts.any():
        raise ValueError("successful row lacks non-negative integer common-basis gate counts")
    impossible_zero = success & original_count.eq(0) & optimized_count.ne(0)
    if impossible_zero.any():
        raise ValueError("zero original gate count cannot have a nonzero optimized count")
    expected_reduction = pd.Series(np.nan, index=joined.index, dtype=float)
    positive_original = success & original_count.gt(0)
    expected_reduction.loc[positive_original] = 100.0 * (
        1.0 - optimized_count.loc[positive_original] / original_count.loc[positive_original]
    )
    both_zero = success & original_count.eq(0) & optimized_count.eq(0)
    expected_reduction.loc[both_zero] = 0.0
    observed_reduction = pd.to_numeric(
        joined["common_basis_gate_reduction_pct"], errors="coerce"
    )
    if (success & ~np.isclose(
            observed_reduction, expected_reduction, rtol=0.0, atol=1e-12,
            equal_nan=False,
    )).any():
        raise ValueError("common-basis reduction does not match the sealed gate counts")
    grace = float(protocol["resource_contract"]["timeout_grace_seconds"])
    if (joined["status"].eq("success")
            & joined["wall_seconds_end_to_end"].gt(joined["budget_seconds"] + grace)).any():
        raise ValueError("successful run exceeded budget plus timeout grace")
    memory_cap = float(protocol["resource_contract"]["memory_budget_mb_per_worker"])
    if (joined["status"].eq("success") & joined["peak_rss_mb"].gt(memory_cap)).any():
        raise ValueError("successful run exceeded the frozen memory budget")
    joined["valid_equivalent_output"] = valid
    joined["common_basis_gate_reduction_pct_itt"] = np.where(
        valid, joined["common_basis_gate_reduction_pct"].astype(float), 0.0
    )
    joined["failure"] = (~valid).astype(int)
    if formal:
        if design_sha256 is None:
            raise ValueError("confirmatory analysis requires the design file SHA")
        if protocol["design_status"] != protocol["formal_gate"]["required_design_status"]:
            raise ValueError("confirmatory analysis forbidden until protocol is frozen before execution")
        validate_power_gate(protocol, design_sha256)
        validate_method_erratum_gate(
            str(results["protocol_sha256"].iloc[0]), design_sha256,
        )
        validate_host_environment_gate(
            str(results["protocol_sha256"].iloc[0]), design_sha256,
        )
        provenance_gate = validate_transitive_source_gate(
            str(results["protocol_sha256"].iloc[0]), design_sha256,
        )
        provenance_rows = int(provenance_gate["checkpoint_boundary"]["committed_rows"])
        provenance_counts = {
            str(key): int(value)
            for key, value in results.sort_values("run_order", kind="stable")
            .iloc[:provenance_rows]["status"].astype(str).value_counts().items()
        }
        if provenance_counts != provenance_gate["checkpoint_boundary"]["status_counts_only"]:
            raise ValueError("transitive-source checkpoint counts differ from formal rows")
        pareto_gate = validate_pareto_aggregation_gate(
            str(results["protocol_sha256"].iloc[0]), design_sha256,
        )
        pareto_rows = int(pareto_gate["checkpoint_boundary"]["committed_rows"])
        pareto_counts = {
            str(key): int(value)
            for key, value in results.sort_values("run_order", kind="stable")
            .iloc[:pareto_rows]["status"].astype(str).value_counts().items()
        }
        if pareto_counts != pareto_gate["checkpoint_boundary"]["status_counts_only"]:
            raise ValueError("Pareto aggregation checkpoint counts differ from formal rows")
        contrast_gate = validate_contrast_expansion_gate(
            str(results["protocol_sha256"].iloc[0]), design_sha256,
        )
        contrast_rows = int(contrast_gate["checkpoint_boundary"]["committed_rows"])
        contrast_counts = {
            str(key): int(value)
            for key, value in results.sort_values("run_order", kind="stable")
            .iloc[:contrast_rows]["status"].astype(str).value_counts().items()
        }
        if contrast_counts != contrast_gate["checkpoint_boundary"]["status_counts_only"]:
            raise ValueError("contrast-expansion checkpoint counts differ from formal rows")
    return joined


def summarize_equal_budget(validated: pd.DataFrame) -> pd.DataFrame:
    """Summarize ITT quality and resource objectives for every treatment cell."""
    return (validated.groupby(FACTOR_COLUMNS, as_index=False, sort=True)
            .agg(n_scheduled=("run_id", "size"),
                 n_unique_inputs=("input_circuit_sha256", "nunique"),
                 quality_itt_mean=("common_basis_gate_reduction_pct_itt", "mean"),
                 quality_itt_median=("common_basis_gate_reduction_pct_itt", "median"),
                 valid_rate=("valid_equivalent_output", "mean"),
                 failure_rate=("failure", "mean"),
                 wall_seconds_median=("wall_seconds_end_to_end", "median"),
                 wall_seconds_p95=("wall_seconds_end_to_end", lambda x: float(np.quantile(x, .95))),
                 peak_rss_mb_median=("peak_rss_mb", "median"),
                 peak_rss_mb_p95=("peak_rss_mb", lambda x: float(np.quantile(x, .95)))))


def secondary_outcome_availability(validated: pd.DataFrame) -> dict[str, dict[str, object]]:
    """Audit preregistered secondary outcomes without inventing missing timings."""
    success = validated["status"].eq("success")
    output: dict[str, dict[str, object]] = {}
    for column in (
        "wall_seconds_end_to_end", "peak_rss_mb", "optimizer_runtime_seconds",
        "original_common_basis_gate_count", "optimized_common_basis_gate_count",
    ):
        present = column in validated.columns
        usable = int(pd.to_numeric(validated.loc[success, column], errors="coerce").notna().sum()) \
            if present else 0
        output[column] = {
            "status": "MEASURED" if present and usable == int(success.sum()) else "INCOMPLETE",
            "usable_success_rows": usable,
            "expected_success_rows": int(success.sum()),
        }
    for column in ("time_to_first_valid_seconds", "time_to_best_seconds"):
        output[column] = {
            "status": "NOT_MEASURED_IN_FROZEN_RUN",
            "usable_success_rows": 0,
            "expected_success_rows": int(success.sum()),
            "reason": "worker trace has no per-iteration timestamps",
        }
    return output


def fit_full_factorial_model(validated: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    """Fit fixed-panel coefficients and invalidate the wrong-cluster inference.

    Inputs are repeated blocks, not the protocol's independent outer clusters.
    The 391-input sandwich SE/CI/p-values formerly emitted here therefore cannot
    support inference.  Point estimates and residual diagnostics remain useful;
    valid supportive inference is written by ``e31_posthoc_family_inference`` at
    the 15-family level.
    """
    frame = validated.copy()
    formula = (
        "common_basis_gate_reduction_pct_itt ~ C(input_circuit_sha256) + "
        "C(listing_model) * C(rule_set) * C(window_gates) * C(budget_seconds)"
    )
    result = smf.ols(formula, data=frame).fit(
        cov_type="cluster",
        cov_kwds={"groups": frame["input_circuit_sha256"], "use_correction": True},
    )
    coefficients = pd.DataFrame({
        "coefficient": result.params.index,
        "estimate_pp": result.params.to_numpy(float),
        "cluster_robust_se_pp": np.nan,
        "ci95_low_pp": np.nan,
        "ci95_high_pp": np.nan,
        "p_value_model_based": np.nan,
    })
    treatment = coefficients[
        ~coefficients["coefficient"].eq("Intercept")
        & ~coefficients["coefficient"].str.startswith("C(input_circuit_sha256)")
    ].copy().reset_index(drop=True)
    treatment["interaction_order"] = treatment["coefficient"].str.count(":") + 1
    treatment["inference_role"] = "EXPLORATORY_PARAMETERIZATION_DIAGNOSTIC"
    treatment["holm_adjusted_p_within_role"] = np.nan
    treatment["confirmatory_primary_contrast"] = False
    residual = np.asarray(result.resid, dtype=float)
    diagnostics = {
        "formula": formula,
        "response": "common_basis_gate_reduction_pct_itt",
        "covariance": "NONE_FIXED_PANEL_DESCRIPTION_WRONG_OUTER_CLUSTER_INVALIDATED",
        "n_rows": int(result.nobs),
        "n_input_clusters": int(frame["input_circuit_sha256"].nunique()),
        "n_outer_families_not_used_as_input_df": int(frame["circuit_family"].nunique()),
        "design_matrix_rank": int(result.model.rank),
        "design_matrix_columns": int(result.model.exog.shape[1]),
        "condition_number": float(result.condition_number),
        "residual_quantiles": {
            str(q): float(np.quantile(residual, q))
            for q in (0.0, 0.01, 0.05, 0.5, 0.95, 0.99, 1.0)
        },
        "zero_inflated_response_rate": float(
            frame["common_basis_gate_reduction_pct_itt"].eq(0).mean()
        ),
        "p_value_interpretation": (
            "legacy 391-input-cluster SE/CI/p-values are invalid and intentionally null; "
            "supportive inference is reported separately at the 15-family outer-cluster level"
        ),
        "treatment_parameter_interpretation": (
            "baseline-conditional parameterization diagnostics, not marginal main effects"
        ),
        "posthoc_marginal_contrast_file": "posthoc_marginal_contrasts.csv",
    }
    return treatment, diagnostics


def posthoc_marginal_contrasts(validated: pd.DataFrame) -> pd.DataFrame:
    """Describe fixed-panel marginal contrasts; omit wrong-cluster inference."""
    factors = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    levels = {factor: sorted(validated[factor].unique().tolist()) for factor in factors}
    pivot = validated.pivot(
        index="input_circuit_sha256", columns=factors,
        values="common_basis_gate_reduction_pct_itt",
    ).sort_index()
    if pivot.shape != (391, 72) or pivot.isna().any().any():
        raise ValueError("post-hoc marginal contrasts require the complete 391 by 72 panel")
    records: list[dict[str, object]] = []
    cluster_contrasts: list[np.ndarray] = []
    for order in (1, 2):
        for factor_indices in combinations(range(len(factors)), order):
            alternatives = [levels[factors[index]][1:] for index in factor_indices]
            for selected_values in product(*alternatives):
                selected = dict(zip(factor_indices, selected_values))
                if (order == 2 and selected.get(0) == "WCL"
                        and selected.get(1) == "COMMUTATION_PLUS_TEMPLATES"):
                    continue
                nuisance_indices = [
                    index for index in range(len(factors)) if index not in selected
                ]
                contrast = np.zeros(len(pivot), dtype=float)
                nuisance_cells = list(product(*[
                    levels[factors[index]] for index in nuisance_indices
                ]))
                for nuisance_values in nuisance_cells:
                    nuisance = dict(zip(nuisance_indices, nuisance_values))
                    for subset_size in range(order + 1):
                        for subset in combinations(factor_indices, subset_size):
                            active = set(subset)
                            cell = tuple(
                                selected[index] if index in active
                                else levels[factor][0] if index in selected
                                else nuisance[index]
                                for index, factor in enumerate(factors)
                            )
                            sign = -1.0 if (order - subset_size) % 2 else 1.0
                            contrast += sign * pivot[cell].to_numpy(float)
                contrast /= len(nuisance_cells)
                label = ":".join(
                    f"{factors[index]}[{selected[index]}-vs-{levels[factors[index]][0]}]"
                    for index in factor_indices
                )
                cluster_contrasts.append(contrast)
                records.append({
                    "coefficient": f"MARGINAL::{label}",
                    "estimate_pp": float(contrast.mean()),
                    "interaction_order": order,
                    "inference_role": "SUPPORTIVE_POSTHOC_OPERATIONALIZATION_OF_FROZEN_CLASS",
                    "confirmatory_primary_contrast": False,
                })
    output_labels = [str(record["coefficient"]) for record in records]
    if len(records) != 30 or output_labels != _expected_posthoc_marginal_labels():
        raise ValueError("post-hoc marginal contrast membership drifted")
    output = pd.DataFrame(records)
    output["cluster_robust_se_pp"] = np.nan
    output["ci95_low_pp"] = np.nan
    output["ci95_high_pp"] = np.nan
    output["p_value_model_based"] = np.nan
    output["multiplicity_family_id"] = "E31_POSTHOC_MARGINAL_30"
    output["multiplicity_family_size"] = 30
    output["holm_adjusted_p_within_role"] = np.nan
    return output[[
        "coefficient", "estimate_pp", "cluster_robust_se_pp", "ci95_low_pp",
        "ci95_high_pp", "p_value_model_based", "interaction_order", "inference_role",
        "holm_adjusted_p_within_role", "confirmatory_primary_contrast",
        "multiplicity_family_id", "multiplicity_family_size",
    ]]


def _add_pareto_flags_for_aggregation(
    summary: pd.DataFrame, *, wall_column: str, memory_column: str,
) -> pd.DataFrame:
    """Flag treatment cells under one explicit time/memory aggregation scheme.

    Comparisons use a 1e-12 numerical tolerance so CSV round-tripping cannot
    turn an analytically tied objective into a spurious dominance relation.
    """
    frame = summary.copy().reset_index(drop=True)
    maximize = ["quality_itt_mean", "valid_rate"]
    minimize = [wall_column, memory_column, "failure_rate"]
    nondominated = np.ones(len(frame), dtype=bool)
    dominates_n = np.zeros(len(frame), dtype=int)
    dominated_by_n = np.zeros(len(frame), dtype=int)
    tolerance = 1e-12
    def dominates_relation(left: pd.Series, right: pd.Series) -> bool:
        no_worse = (
            all(float(left[c]) >= float(right[c]) - tolerance for c in maximize)
            and all(float(left[c]) <= float(right[c]) + tolerance for c in minimize)
        )
        strictly_better = (
            any(float(left[c]) > float(right[c]) + tolerance for c in maximize)
            or any(float(left[c]) < float(right[c]) - tolerance for c in minimize)
        )
        return no_worse and strictly_better
    for i, row in frame.iterrows():
        for j, challenger in frame.iterrows():
            if i == j:
                continue
            challenger_dominates = dominates_relation(challenger, row)
            row_dominates = dominates_relation(row, challenger)
            if challenger_dominates:
                nondominated[i] = False
                dominated_by_n[i] += 1
            if row_dominates:
                dominates_n[i] += 1
    frame["pareto_nondominated"] = nondominated
    frame["dominates_n"] = dominates_n
    frame["dominated_by_n"] = dominated_by_n
    denominator = max(len(frame) - 1, 1)
    frame["pareto_dominance_rate"] = dominates_n / denominator
    frame["pareto_dominated_by_rate"] = dominated_by_n / denominator
    return frame


def add_pareto_flags(summary: pd.DataFrame) -> pd.DataFrame:
    """Apply the disclosed primary exploratory median-wall/P95-memory frontier."""
    return _add_pareto_flags_for_aggregation(
        summary, wall_column="wall_seconds_median", memory_column="peak_rss_mb_p95",
    )


def pareto_aggregation_sensitivity(validated: pd.DataFrame) -> pd.DataFrame:
    """Recompute dominance under all four frozen post-hoc aggregation schemes."""
    summary = summarize_equal_budget(validated)
    outputs: list[pd.DataFrame] = []
    for wall_stat, memory_stat in product(("median", "p95"), repeat=2):
        wall_column = f"wall_seconds_{wall_stat}"
        memory_column = f"peak_rss_mb_{memory_stat}"
        flagged = _add_pareto_flags_for_aggregation(
            summary, wall_column=wall_column, memory_column=memory_column,
        )
        flagged.insert(len(FACTOR_COLUMNS), "wall_aggregation", wall_stat)
        flagged.insert(len(FACTOR_COLUMNS) + 1, "memory_aggregation", memory_stat)
        flagged["selected_wall_seconds"] = flagged[wall_column]
        flagged["selected_peak_rss_mb"] = flagged[memory_column]
        outputs.append(flagged)
    output = pd.concat(outputs, ignore_index=True)
    if len(output) != 288:
        raise ValueError("Pareto aggregation sensitivity must contain four 72-cell schemes")
    return output


def summarize_pareto_aggregation_sensitivity(sensitivity: pd.DataFrame) -> dict[str, object]:
    """Turn the four-scheme frontier comparison into a machine-enforced claim gate."""
    scheme_columns = ["wall_aggregation", "memory_aggregation"]
    scheme_labels = (
        sensitivity[scheme_columns].astype(str).agg("|".join, axis=1)
    )
    frame = sensitivity.copy()
    frame["pareto_nondominated"] = _strict_bool_series(
        frame["pareto_nondominated"], label="Pareto sensitivity pareto_nondominated"
    )
    frame["scheme"] = scheme_labels
    expected_schemes = ["median|median", "median|p95", "p95|median", "p95|p95"]
    if sorted(frame["scheme"].unique().tolist()) != expected_schemes:
        raise ValueError("Pareto sensitivity summary lacks the four frozen schemes")
    membership = frame.pivot(
        index=FACTOR_COLUMNS, columns="scheme", values="pareto_nondominated"
    ).sort_index()
    if membership.shape != (72, 4) or membership.isna().any().any():
        raise ValueError("Pareto sensitivity membership grid is incomplete")
    disagreements: list[dict[str, object]] = []
    for factor_values, row in membership.iterrows():
        flags = {scheme: bool(row[scheme]) for scheme in expected_schemes}
        if len(set(flags.values())) > 1:
            factor_tuple = factor_values if isinstance(factor_values, tuple) else (factor_values,)
            disagreements.append({
                **{
                    name: value.item() if isinstance(value, np.generic) else value
                    for name, value in zip(FACTOR_COLUMNS, factor_tuple)
                },
                "nondominated_by_scheme": flags,
            })
    agreement = not disagreements
    return {
        "status": "FOUR_SCHEME_FRONTIER_MEMBERSHIP_AUDITED",
        "schemes": expected_schemes,
        "treatment_cells": 72,
        "frontier_sizes": {
            scheme: int(membership[scheme].astype(bool).sum())
            for scheme in expected_schemes
        },
        "frontier_membership_agreement_all_schemes": agreement,
        "disagreement_cell_count": len(disagreements),
        "disagreement_cells": disagreements,
        "bounded_aggregation_invariant_frontier_claim_allowed": agreement,
        "claim_scope": "only the four frozen post-hoc aggregation schemes",
    }


def normalized_pareto_hypervolume(
    frontier: pd.DataFrame, *, draws: int = 200_000, seed: int = 20260811,
) -> dict[str, object]:
    """Estimate observed-range-normalized hypervolume on independent objectives."""
    if draws < 1:
        raise ValueError("hypervolume draws must be positive")
    objectives = {
        "quality_itt_mean": "maximize",
        "valid_rate": "maximize",
        "wall_seconds_median": "minimize",
        "peak_rss_mb_p95": "minimize",
    }
    normalized = np.empty((len(frontier), len(objectives)), dtype=float)
    ranges: dict[str, dict[str, float | str]] = {}
    for index, (column, direction) in enumerate(objectives.items()):
        values = frontier[column].to_numpy(float)
        low, high = float(values.min()), float(values.max())
        if high == low:
            scaled = np.ones(len(values), dtype=float)
        elif direction == "maximize":
            scaled = (values - low) / (high - low)
        else:
            scaled = (high - values) / (high - low)
        normalized[:, index] = scaled
        ranges[column] = {"direction": direction, "observed_min": low, "observed_max": high}
    points = normalized[frontier["pareto_nondominated"].to_numpy(bool)]
    rng = np.random.default_rng(seed)
    samples = rng.random((draws, len(objectives)))
    dominated = np.zeros(draws, dtype=bool)
    for point in points:
        dominated |= np.all(samples <= point, axis=1)
    estimate = float(dominated.mean())
    standard_error = float(np.sqrt(estimate * (1.0 - estimate) / draws))
    return {
        "method": "SEEDED_MONTE_CARLO_UNIT_HYPERCUBE",
        "normalization": "observed range; reference point is zero, ideal point is one",
        "hypervolume": estimate,
        "monte_carlo_standard_error": standard_error,
        "draws": int(draws),
        "seed": int(seed),
        "pareto_points": int(len(points)),
        "independent_objectives": list(objectives),
        "objective_ranges": ranges,
        "deduplicated_protocol_objective": {
            "removed": "failure_rate",
            "reason": "failure_rate equals 1 - valid_rate exactly and is not an independent axis",
        },
        "interpretation": "relative to observed treatment-cell ranges, not an absolute cross-study metric",
    }


def design_audit(design: pd.DataFrame, protocol: dict) -> dict[str, object]:
    """Return machine-readable coverage and worst-case compute requirements."""
    validate_design(design, protocol)
    budgets = [int(value) for value in protocol["factors"]["budget_seconds"]]
    nonbudget_cells = (len(protocol["factors"]["listing_model"])
                       * len(protocol["factors"]["rule_set"])
                       * len(protocol["factors"]["window_gates"]))
    unique_inputs = int(design["input_circuit_sha256"].nunique())
    worst_seconds = unique_inputs * nonbudget_cells * sum(budgets)
    return {
        "design_status": protocol["design_status"],
        "formal_results_allowed_for_fixed_benchmark_A": (
            protocol["design_status"] == protocol["formal_gate"]["required_design_status"]
            and protocol["power_gate"]["fixed_benchmark_decision"] == "PASS"
        ),
        "formal_new_family_claim_allowed": (
            protocol["power_gate"]["new_family_generalized_decision"] == "PASS"
        ),
        "scheduled_rows": int(len(design)),
        "unique_inputs": unique_inputs,
        "outer_families": int(design["circuit_family"].nunique()),
        "factorial_cells_per_input": len(treatment_cells(protocol)),
        "worst_case_worker_seconds": int(worst_seconds),
        "worst_case_worker_hours": float(worst_seconds / 3600.0),
    }


def run_order_temporal_diagnostics(
    validated: pd.DataFrame, *, blocks: int = 20,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Diagnose temporal host drift after saturated treatment/input adjustment.

    This is an observational sensitivity analysis. It cannot prove host
    exclusivity because the frozen runner recorded no continuous host telemetry.
    """
    if blocks < 2:
        raise ValueError("temporal diagnostics require at least two blocks")
    frame = validated.sort_values("run_order", kind="stable").copy()
    if len(frame) < blocks:
        raise ValueError("fewer result rows than requested temporal blocks")
    frame["temporal_block"] = np.minimum(
        np.arange(len(frame), dtype=int) * blocks // len(frame), blocks - 1
    )
    frame["treatment_cell"] = frame[FACTOR_COLUMNS].astype(str).agg("|".join, axis=1)
    outcomes = {
        "quality_itt": frame["common_basis_gate_reduction_pct_itt"].astype(float),
        "valid": frame["valid_equivalent_output"].astype(float),
        "timeout": frame["status"].eq("timeout").astype(float),
        "wall_seconds": frame["wall_seconds_end_to_end"].astype(float),
        "wall_budget_fraction": (
            frame["wall_seconds_end_to_end"].astype(float)
            / frame["budget_seconds"].astype(float)
        ),
        "peak_rss_mb": frame["peak_rss_mb"].astype(float),
    }
    grouped = frame.groupby("temporal_block", sort=True, observed=True)
    result = grouped["run_order"].agg(rows="size", run_order_min="min", run_order_max="max")
    outcome_summary: dict[str, object] = {}
    for name, values in outcomes.items():
        column = f"_temporal_{name}"
        frame[column] = values
        cell_mean = frame.groupby("treatment_cell", observed=True)[column].transform("mean")
        input_mean = frame.groupby("input_circuit_sha256", observed=True)[column].transform("mean")
        residual = values - cell_mean - input_mean + float(values.mean())
        residual_column = f"_temporal_{name}_adjusted_residual"
        frame[residual_column] = residual
        grouped = frame.groupby("temporal_block", sort=True, observed=True)
        result[f"{name}_raw_mean"] = grouped[column].mean()
        result[f"{name}_adjusted_residual_mean"] = grouped[residual_column].mean()
        result[f"{name}_adjusted_residual_sem"] = grouped[residual_column].sem()
        residual_means = result[f"{name}_adjusted_residual_mean"]
        outcome_summary[name] = {
            "max_absolute_block_adjusted_residual_mean": float(residual_means.abs().max()),
            "last_minus_first_adjusted_residual_mean": float(
                residual_means.iloc[-1] - residual_means.iloc[0]
            ),
        }
    result = result.reset_index()
    cell_counts = frame.groupby(["temporal_block", "treatment_cell"], observed=True).size()
    thresholds = {
        "quality_itt": 1.0,
        "valid": 0.05,
        "timeout": 0.05,
        "wall_budget_fraction": 0.05,
        "peak_rss_mb": 128.0,
    }
    exceeded = {
        name: bool(outcome_summary[name]["max_absolute_block_adjusted_residual_mean"] > threshold)
        for name, threshold in thresholds.items()
    }
    return result, {
        "status": "OBSERVATIONAL_TEMPORAL_SENSITIVITY_ONLY",
        "blocks": int(blocks),
        "rows": int(len(frame)),
        "continuous_host_exclusivity_verified": False,
        "startup_overlap_guard_only": True,
        "continuous_host_telemetry_recorded": False,
        "adjustment": "saturated 72-cell treatment mean plus input-hash fixed mean",
        "treatment_cell_count_per_block_min": int(cell_counts.min()),
        "treatment_cell_count_per_block_max": int(cell_counts.max()),
        "outcomes": outcome_summary,
        "material_drift_thresholds": thresholds,
        "material_drift_threshold_exceeded": exceeded,
        "material_drift_screen_decision": (
            "REVIEW_REQUIRED" if any(exceeded.values()) else "NO_THRESHOLD_EXCEEDED"
        ),
        "threshold_role": "predeclared descriptive sensitivity thresholds, not hypothesis tests",
        "interpretation": (
            "Run-order diagnostics can reveal temporal drift but cannot prove its absence; "
            "runtime, timeout, and memory findings remain conditional on the recorded shared host."
        ),
    }


FORMAL_ANALYSIS_FILENAMES = (
    "equal_budget_pareto_summary.csv",
    "full_factorial_model_coefficients.csv",
    "full_factorial_model_diagnostics.json",
    "posthoc_marginal_contrasts.csv",
    "pareto_aggregation_sensitivity.csv",
    "pareto_hypervolume_audit.json",
    "analysis_gate_audit.json",
    "run_order_temporal_diagnostics.csv",
    "host_environment_audit.json",
)


def write_analysis_packet(
    design: pd.DataFrame,
    validated: pd.DataFrame,
    protocol: dict,
    output_dir: Path | None,
    *,
    formal: bool,
    smoke: bool,
) -> dict[str, object]:
    """Compute and write one internally consistent analysis packet."""
    audit = design_audit(design, protocol)
    frontier = add_pareto_flags(summarize_equal_budget(validated))
    hypervolume = normalized_pareto_hypervolume(frontier) if not smoke else None
    dual = None if smoke else primary_dual_estimand(
        validated,
        alpha=float(protocol["analysis_contract"]["alpha_two_sided"]),
        mcid_pp=float(protocol["power_gate"]["mcid_pp"]),
        bootstrap_replicates=int(protocol["analysis_contract"]["bootstrap_replicates"]),
        bootstrap_seed=int(protocol["analysis_contract"]["bootstrap_seed"]),
    )
    factorial_coefficients = None
    factorial_diagnostics = None
    pareto_sensitivity_summary = None
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        frontier.to_csv(output_dir / "equal_budget_pareto_summary.csv", index=False)
    if not smoke and output_dir is not None:
        factorial_coefficients, factorial_diagnostics = fit_full_factorial_model(validated)
        factorial_coefficients.to_csv(
            output_dir / "full_factorial_model_coefficients.csv", index=False
        )
        posthoc_marginal_contrasts(validated).to_csv(
            output_dir / "posthoc_marginal_contrasts.csv", index=False
        )
        pareto_sensitivity = pareto_aggregation_sensitivity(validated)
        pareto_sensitivity.to_csv(
            output_dir / "pareto_aggregation_sensitivity.csv", index=False
        )
        pareto_sensitivity_summary = summarize_pareto_aggregation_sensitivity(
            pareto_sensitivity
        )
        (output_dir / "full_factorial_model_diagnostics.json").write_text(
            json.dumps(factorial_diagnostics, indent=2, sort_keys=True), encoding="utf-8"
        )
        (output_dir / "pareto_hypervolume_audit.json").write_text(
            json.dumps(hypervolume, indent=2, sort_keys=True), encoding="utf-8"
        )
        temporal, host_audit = run_order_temporal_diagnostics(validated)
        temporal.to_csv(output_dir / "run_order_temporal_diagnostics.csv", index=False)
        (output_dir / "host_environment_audit.json").write_text(
            json.dumps(host_audit, indent=2, sort_keys=True), encoding="utf-8"
        )
    gate = {
        **audit,
        "result_rows": len(validated),
        "formal_requested": bool(formal),
        "dual_estimand_primary": dual,
        "pareto_hypervolume": hypervolume,
        "pareto_inference_role": "EXPLORATORY_POSTHOC_AGGREGATION",
        "pareto_aggregation_sensitivity": pareto_sensitivity_summary,
        "secondary_outcome_availability": secondary_outcome_availability(validated),
        "factorial_model": factorial_diagnostics,
    }
    if output_dir is not None:
        (output_dir / "analysis_gate_audit.json").write_text(
            json.dumps(gate, indent=2, sort_keys=True), encoding="utf-8"
        )
    return gate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--formal", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    protocol = json.loads(args.protocol.resolve().read_text(encoding="utf-8"))
    design = pd.read_csv(args.design.resolve())
    audit = design_audit(design, protocol)
    if args.results is None:
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0
    validated = validate_results(
        design, pd.read_csv(args.results.resolve()), protocol, formal=args.formal,
        design_sha256=file_sha256(args.design.resolve()),
        allow_incomplete_smoke=args.smoke,
    )
    summary = write_analysis_packet(
        design, validated, protocol, args.output_dir,
        formal=bool(args.formal), smoke=bool(args.smoke),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
