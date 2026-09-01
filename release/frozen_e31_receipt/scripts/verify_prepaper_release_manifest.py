"""Independently verify every file pinned by the pre-paper release manifest."""

from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
from itertools import combinations, product
import json
import math
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
from scipy.stats import norm, t as student_t

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expect_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _hash(path) != str(expected):
        raise RuntimeError(f"cross-artifact hash mismatch: {label} -> {path}")


def _strict_bool_series(values: pd.Series, *, label: str) -> pd.Series:
    """Accept only bool or explicit true/false/1/0 serialization; reject corruption."""
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
            raise RuntimeError(
                f"invalid serialized boolean in {label} at index {index}: {value!r}"
            )
    return pd.Series(parsed, index=values.index, dtype=bool)


def _verify_nested_audits() -> int:
    """Verify hashes asserted inside analysis and figure audit records."""
    checked = 0
    analysis_root = PROJECT_ROOT / "data" / "v10" / "prepaper" / "analysis"
    rq1_names = {
        "family_contrasts": "family_contrasts.csv",
        "leave_one_family_out": "leave_one_family_out.csv",
        "bootstrap_source": "bootstrap_source_10000.csv",
    }
    for analysis in ("rq1", "rq3", "external"):
        base = analysis_root / analysis
        audit = json.loads((base / "audit.json").read_text(encoding="utf-8"))
        for name, expected in audit.get("output_sha256", {}).items():
            filename = rq1_names.get(name, name)
            _expect_hash(base / filename, expected, f"{analysis}:{name}")
            checked += 1

    figure_root = PROJECT_ROOT / "data" / "v10" / "prepaper" / "figures"
    figure_audit = json.loads(
        (figure_root / "figure_audit.json").read_text(encoding="utf-8")
    )
    if figure_audit.get("status") != "mechanically_verified":
        raise RuntimeError("figure audit is not mechanically verified")
    for record in figure_audit.get("figures", []):
        for suffix in ("pdf", "svg", "png"):
            _expect_hash(
                figure_root / f"{record['stem']}.{suffix}",
                record[f"{suffix}_sha256"], f"figure:{record['stem']}:{suffix}",
            )
            checked += 1
    for record in figure_audit.get("source_data", []):
        _expect_hash(
            figure_root / "source_data" / record["file"], record["sha256"],
            f"figure-source:{record['file']}",
        )
        checked += 1
    return checked


def _verify_external_lineage() -> int:
    """Cross-check raw/revalidated external files and execution metadata."""
    root = PROJECT_ROOT / "data" / "v10" / "prepaper" / "external_baselines"
    audit = json.loads(
        (root / "exact_fidelity_revalidation.json").read_text(encoding="utf-8")
    )
    if audit.get("status") != "complete" or not audit.get("raw_results_preserved"):
        raise RuntimeError("external exact-fidelity audit is incomplete")
    if audit.get("rule") != "frozen exact full-operator average gate fidelity >= 1 - 1e-10":
        raise RuntimeError("external exact-fidelity rule drift")
    source = PROJECT_ROOT / "analysis" / "revalidate_external_exact_fidelity.py"
    _expect_hash(source, audit["source_sha256"], "external-fidelity:source")
    checked = 1
    for record in audit.get("records", []):
        method = str(record["method"])
        base = root / method / "shared_520"
        raw = base / f"{method}_shared_520.csv"
        revalidated = base / f"{method}_shared_520_revalidated.csv"
        input_manifest = base / "inputs" / "benchmark_manifest.csv"
        _expect_hash(raw, record["raw_sha256"], f"{method}:raw")
        _expect_hash(revalidated, record["revalidated_sha256"],
                     f"{method}:revalidated")
        _expect_hash(input_manifest, record["manifest_sha256"],
                     f"{method}:input-manifest")
        frame = pd.read_csv(revalidated)
        if len(frame) != int(record["rows"]):
            raise RuntimeError(f"{method} revalidated row-count mismatch")
        validity_column = "valid_equivalent_output"
        if validity_column not in frame.columns:
            raise RuntimeError(
                f"{method} revalidated file lacks {validity_column}"
            )
        valid_n = int(_strict_bool_series(
            frame[validity_column], label=f"{method}:{validity_column}"
        ).sum())
        if valid_n != int(record["revalidated_valid_n"]):
            raise RuntimeError(f"{method} revalidated valid-count mismatch")
        metadata = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("status") != "complete":
            raise RuntimeError(f"{method} execution metadata is incomplete")
        for key, path in {
            "result_sha256": raw,
            "manifest_sha256": input_manifest,
            "execution_segments_sha256": base / "execution_segments.json",
        }.items():
            _expect_hash(path, metadata[key], f"{method}:metadata:{key}")
        driver = PROJECT_ROOT / "experiments" / f"external_{method}_benchmark.py"
        _expect_hash(driver, metadata["source_sha256"], f"{method}:driver")
        checked += 7
    return checked


def _recompute_e31_temporal_diagnostics(results: pd.DataFrame, blocks: int = 20) -> pd.DataFrame:
    """Independently reconstruct the temporal source table from sealed rows."""
    factors = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    required = {
        "run_order", "input_circuit_sha256", "status", "valid_equivalent_output",
        "common_basis_gate_reduction_pct", "wall_seconds_end_to_end", "peak_rss_mb",
        *factors,
    }
    missing = required.difference(results.columns)
    if missing:
        raise RuntimeError(f"E31 sealed results lack temporal inputs: {sorted(missing)}")
    frame = results.sort_values("run_order", kind="stable").reset_index(drop=True).copy()
    frame["temporal_block"] = [index * blocks // len(frame) for index in range(len(frame))]
    frame["treatment_cell"] = frame[factors].astype(str).agg("|".join, axis=1)
    valid = _strict_bool_series(
        frame["valid_equivalent_output"], label="E31 temporal valid_equivalent_output"
    )
    quality = pd.to_numeric(frame["common_basis_gate_reduction_pct"], errors="raise").where(
        valid & frame["status"].eq("success"), 0.0
    )
    budget = pd.to_numeric(frame["budget_seconds"], errors="raise")
    if (budget <= 0).any():
        raise RuntimeError("E31 sealed results contain a non-positive budget")
    outcomes = {
        "quality_itt": quality.astype(float),
        "valid": valid.astype(float),
        "timeout": frame["status"].eq("timeout").astype(float),
        "wall_seconds": pd.to_numeric(frame["wall_seconds_end_to_end"], errors="raise"),
        "wall_budget_fraction": (
            pd.to_numeric(frame["wall_seconds_end_to_end"], errors="raise") / budget
        ),
        "peak_rss_mb": pd.to_numeric(frame["peak_rss_mb"], errors="raise"),
    }
    grouped = frame.groupby("temporal_block", sort=True, observed=True)
    rebuilt = grouped["run_order"].agg(
        rows="size", run_order_min="min", run_order_max="max"
    )
    for name, values in outcomes.items():
        source = f"_verify_{name}"
        residual_source = f"_verify_{name}_residual"
        frame[source] = values
        cell_mean = frame.groupby("treatment_cell", observed=True)[source].transform("mean")
        input_mean = frame.groupby("input_circuit_sha256", observed=True)[source].transform("mean")
        frame[residual_source] = values - cell_mean - input_mean + float(values.mean())
        grouped = frame.groupby("temporal_block", sort=True, observed=True)
        rebuilt[f"{name}_raw_mean"] = grouped[source].mean()
        rebuilt[f"{name}_adjusted_residual_mean"] = grouped[residual_source].mean()
        rebuilt[f"{name}_adjusted_residual_sem"] = grouped[residual_source].sem()
    return rebuilt.reset_index()


def _recompute_e31_primary_estimand(
    results: pd.DataFrame, *, alpha: float, bootstrap_replicates: int,
    bootstrap_seed: int,
) -> dict[str, object]:
    """Independently rebuild the frozen four-cell interaction from sealed rows."""
    frame = results.copy()
    valid = _strict_bool_series(
        frame["valid_equivalent_output"], label="E31 primary valid_equivalent_output"
    )
    frame["quality_itt"] = pd.to_numeric(
        frame["common_basis_gate_reduction_pct"], errors="raise"
    ).where(valid, 0.0)
    subset = frame[frame["listing_model"].isin(["LBL", "WCL"])]
    keys = ["input_circuit_sha256", "circuit_family", "window_gates", "budget_seconds"]
    try:
        pivot = subset.pivot(
            index=keys, columns=["rule_set", "listing_model"], values="quality_itt"
        )
    except ValueError as error:
        raise RuntimeError("E31 primary contrast contains duplicate treatment cells") from error
    needed = [
        ("COMMUTATION_PLUS_TEMPLATES", "WCL"),
        ("COMMUTATION_PLUS_TEMPLATES", "LBL"),
        ("COMMUTATION_ONLY", "WCL"),
        ("COMMUTATION_ONLY", "LBL"),
    ]
    if any(column not in pivot for column in needed) or pivot[needed].isna().any().any():
        raise RuntimeError("E31 primary contrast lacks a complete paired four-cell grid")
    did = (
        (pivot[needed[0]] - pivot[needed[1]])
        - (pivot[needed[2]] - pivot[needed[3]])
    ).rename("primary_did_pp").reset_index()
    per_input = did.groupby(
        ["input_circuit_sha256", "circuit_family"], as_index=False
    ).agg(primary_did_pp=("primary_did_pp", "mean"), grid_cells=("primary_did_pp", "size"))
    if len(per_input) != 391 or not per_input["grid_cells"].eq(12).all():
        raise RuntimeError("E31 primary contrast does not contain 12 grid cells per input")
    point_a = float(per_input["primary_did_pp"].mean())
    family_means = per_input.groupby("circuit_family", sort=True)["primary_did_pp"].mean()
    estimate_b = float(family_means.mean())
    se_b = float(family_means.std(ddof=1) / math.sqrt(len(family_means)))
    critical_b = float(student_t.ppf(1 - alpha / 2, len(family_means) - 1))
    lofo = {
        str(family): float(per_input.loc[
            per_input["circuit_family"].ne(family), "primary_did_pp"
        ].mean())
        for family in family_means.index
    }
    rng = np.random.default_rng(bootstrap_seed)
    bootstrap_draws = np.zeros(bootstrap_replicates, dtype=float)
    for _, group in per_input.groupby("circuit_family", sort=True):
        values = group["primary_did_pp"].to_numpy(float)
        indices = rng.integers(0, len(values), size=(bootstrap_replicates, len(values)))
        bootstrap_draws += values[indices].sum(axis=1)
    bootstrap_draws /= len(per_input)
    def sign(value: float) -> int:
        return int((value > 0) - (value < 0))
    return {
        "n_input_hashes": 391,
        "families": int(len(family_means)),
        "estimate_a": point_a,
        "estimate_b": estimate_b,
        "se_b": se_b,
        "ci_b": [estimate_b - critical_b * se_b, estimate_b + critical_b * se_b],
        "family_means": {str(key): float(value) for key, value in family_means.items()},
        "worst_family": str(family_means.idxmin()),
        "worst_family_estimate": float(family_means.min()),
        "lofo": lofo,
        "lofo_sign_stable": bool(all(sign(value) == sign(point_a) for value in lofo.values())),
        "quantiles": {
            str(q): float(per_input["primary_did_pp"].quantile(q))
            for q in (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)
        },
        "bootstrap_interval": [
            float(value) for value in np.quantile(
                bootstrap_draws, [alpha / 2, 1 - alpha / 2]
            )
        ],
    }


def _recompute_e31_pareto_summary(results: pd.DataFrame) -> pd.DataFrame:
    """Independently rebuild the 72-cell ITT/resource Pareto table."""
    factors = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    frame = results.copy()
    valid = _strict_bool_series(
        frame["valid_equivalent_output"], label="E31 Pareto valid_equivalent_output"
    )
    frame["quality_itt"] = pd.to_numeric(
        frame["common_basis_gate_reduction_pct"], errors="raise"
    ).where(valid, 0.0)
    frame["valid"] = valid
    frame["failure"] = (~valid).astype(int)
    summary = frame.groupby(factors, as_index=False, sort=True).agg(
        n_scheduled=("run_id", "size"),
        n_unique_inputs=("input_circuit_sha256", "nunique"),
        quality_itt_mean=("quality_itt", "mean"),
        quality_itt_median=("quality_itt", "median"),
        valid_rate=("valid", "mean"),
        failure_rate=("failure", "mean"),
        wall_seconds_median=("wall_seconds_end_to_end", "median"),
        wall_seconds_p95=("wall_seconds_end_to_end", lambda values: float(np.quantile(values, .95))),
        peak_rss_mb_median=("peak_rss_mb", "median"),
        peak_rss_mb_p95=("peak_rss_mb", lambda values: float(np.quantile(values, .95))),
    )
    if (len(summary) != 72
            or not summary["n_scheduled"].eq(391).all()
            or not summary["n_unique_inputs"].eq(391).all()):
        raise RuntimeError("E31 Pareto summary does not contain 72 complete treatment cells")
    return _e31_pareto_flags_independent(
        summary, wall_column="wall_seconds_median", memory_column="peak_rss_mb_p95",
    )


def _e31_pareto_flags_independent(
    summary: pd.DataFrame, *, wall_column: str, memory_column: str,
) -> pd.DataFrame:
    """Independently evaluate tolerance-stable dominance for one scheme."""
    output = summary.copy().reset_index(drop=True)
    maximize = ["quality_itt_mean", "valid_rate"]
    minimize = [wall_column, memory_column, "failure_rate"]
    nondominated: list[bool] = []
    dominates_n: list[int] = []
    dominated_by_n: list[int] = []
    records = output.to_dict(orient="records")
    tolerance = 1e-12
    def dominates_relation(left: dict[str, object], right: dict[str, object]) -> bool:
        no_worse = (
            all(float(left[c]) >= float(right[c]) - tolerance for c in maximize)
            and all(float(left[c]) <= float(right[c]) + tolerance for c in minimize)
        )
        strictly_better = (
            any(float(left[c]) > float(right[c]) + tolerance for c in maximize)
            or any(float(left[c]) < float(right[c]) - tolerance for c in minimize)
        )
        return no_worse and strictly_better
    for index, row in enumerate(records):
        dominates = 0
        dominated_by = 0
        for other_index, challenger in enumerate(records):
            if index == other_index:
                continue
            challenger_dominates = dominates_relation(challenger, row)
            row_dominates = dominates_relation(row, challenger)
            dominated_by += int(challenger_dominates)
            dominates += int(row_dominates)
        nondominated.append(dominated_by == 0)
        dominates_n.append(dominates)
        dominated_by_n.append(dominated_by)
    output["pareto_nondominated"] = nondominated
    output["dominates_n"] = dominates_n
    output["dominated_by_n"] = dominated_by_n
    output["pareto_dominance_rate"] = output["dominates_n"] / 71.0
    output["pareto_dominated_by_rate"] = output["dominated_by_n"] / 71.0
    return output


def _recompute_e31_pareto_aggregation_sensitivity(results: pd.DataFrame) -> pd.DataFrame:
    """Independently rebuild all four disclosed time/memory aggregation frontiers."""
    primary = _recompute_e31_pareto_summary(results)
    flag_columns = {
        "pareto_nondominated", "dominates_n", "dominated_by_n",
        "pareto_dominance_rate", "pareto_dominated_by_rate",
    }
    base = primary.drop(columns=sorted(flag_columns))
    factors = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    outputs: list[pd.DataFrame] = []
    for wall_stat, memory_stat in product(("median", "p95"), repeat=2):
        wall_column = f"wall_seconds_{wall_stat}"
        memory_column = f"peak_rss_mb_{memory_stat}"
        flagged = _e31_pareto_flags_independent(
            base, wall_column=wall_column, memory_column=memory_column,
        )
        flagged.insert(len(factors), "wall_aggregation", wall_stat)
        flagged.insert(len(factors) + 1, "memory_aggregation", memory_stat)
        flagged["selected_wall_seconds"] = flagged[wall_column]
        flagged["selected_peak_rss_mb"] = flagged[memory_column]
        outputs.append(flagged)
    output = pd.concat(outputs, ignore_index=True)
    if len(output) != 288:
        raise RuntimeError("E31 Pareto aggregation sensitivity does not contain 288 rows")
    return output


def _summarize_e31_pareto_aggregation_sensitivity(
    sensitivity: pd.DataFrame,
) -> dict[str, object]:
    """Independently enforce the four-scheme aggregation-invariance claim rule."""
    factors = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    frame = sensitivity.copy()
    frame["pareto_nondominated"] = _strict_bool_series(
        frame["pareto_nondominated"],
        label="E31 Pareto sensitivity summary pareto_nondominated",
    )
    frame["scheme"] = (
        frame[["wall_aggregation", "memory_aggregation"]]
        .astype(str).agg("|".join, axis=1)
    )
    schemes = ["median|median", "median|p95", "p95|median", "p95|p95"]
    membership = frame.pivot(
        index=factors, columns="scheme", values="pareto_nondominated"
    ).sort_index()
    if membership.shape != (72, 4) or list(membership.columns) != schemes:
        raise RuntimeError("E31 Pareto sensitivity membership grid is incomplete")
    disagreements: list[dict[str, object]] = []
    for factor_values, values in membership.iterrows():
        flags = {scheme: bool(values[scheme]) for scheme in schemes}
        if len(set(flags.values())) != 1:
            factor_tuple = factor_values if isinstance(factor_values, tuple) else (factor_values,)
            disagreements.append({
                **{
                    name: value.item() if isinstance(value, np.generic) else value
                    for name, value in zip(factors, factor_tuple)
                },
                "nondominated_by_scheme": flags,
            })
    agreement = not disagreements
    return {
        "status": "FOUR_SCHEME_FRONTIER_MEMBERSHIP_AUDITED",
        "schemes": schemes,
        "treatment_cells": 72,
        "frontier_sizes": {
            scheme: int(membership[scheme].astype(bool).sum()) for scheme in schemes
        },
        "frontier_membership_agreement_all_schemes": agreement,
        "disagreement_cell_count": len(disagreements),
        "disagreement_cells": disagreements,
        "bounded_aggregation_invariant_frontier_claim_allowed": agreement,
        "claim_scope": "only the four frozen post-hoc aggregation schemes",
    }


def _recompute_e31_hypervolume(
    frontier: pd.DataFrame, *, draws: int = 200_000, seed: int = 20260811,
) -> dict[str, object]:
    """Reproduce the seeded observed-range-normalized hypervolume."""
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
    points = normalized[frontier["pareto_nondominated"].astype(bool).to_numpy()]
    samples = np.random.default_rng(seed).random((draws, len(objectives)))
    dominated = np.zeros(draws, dtype=bool)
    for point in points:
        dominated |= np.all(samples <= point, axis=1)
    estimate = float(dominated.mean())
    return {
        "method": "SEEDED_MONTE_CARLO_UNIT_HYPERCUBE",
        "normalization": "observed range; reference point is zero, ideal point is one",
        "hypervolume": estimate,
        "monte_carlo_standard_error": float(math.sqrt(estimate * (1.0 - estimate) / draws)),
        "draws": draws,
        "seed": seed,
        "pareto_points": int(len(points)),
        "independent_objectives": list(objectives),
        "objective_ranges": ranges,
    }


@lru_cache(maxsize=None)
def _balanced_factorial_condition_number(
    n_clusters: int, level_counts: tuple[int, ...],
) -> float:
    """Condition number of the complete input-FE by saturated-cell design."""
    cells = list(product(*(range(count) for count in level_counts)))
    selections = [
        choice for choice in product(*(range(count) for count in level_counts))
        if any(level != 0 for level in choice)
    ]
    treatment = np.asarray([
        [
            float(all(selected == 0 or cell[index] == selected
                      for index, selected in enumerate(selection)))
            for selection in selections
        ]
        for cell in cells
    ])
    n_cells = len(cells)
    n_treatment = len(selections)
    size = n_clusters + n_treatment
    cross = np.zeros((size, size), dtype=float)
    cross[0, 0] = n_clusters * n_cells
    cross[0, 1:n_clusters] = n_cells
    cross[1:n_clusters, 0] = n_cells
    cross[1:n_clusters, 1:n_clusters] = np.eye(n_clusters - 1) * n_cells
    sums = treatment.sum(axis=0)
    cross[0, n_clusters:] = n_clusters * sums
    cross[n_clusters:, 0] = n_clusters * sums
    cross[1:n_clusters, n_clusters:] = sums
    cross[n_clusters:, 1:n_clusters] = sums[:, None]
    cross[n_clusters:, n_clusters:] = n_clusters * treatment.T @ treatment
    eigenvalues = np.linalg.eigvalsh(cross)
    if eigenvalues[0] <= 0:
        raise RuntimeError("E31 factorial design matrix is not full rank")
    return float(math.sqrt(eigenvalues[-1] / eigenvalues[0]))


def _holm_adjusted(values: np.ndarray) -> np.ndarray:
    """Independently apply Holm's step-down family-wise correction."""
    output = np.full(len(values), np.nan)
    finite_indices = np.flatnonzero(np.isfinite(values))
    if not len(finite_indices):
        return output
    order = finite_indices[np.argsort(values[finite_indices], kind="stable")]
    running = 0.0
    total = len(order)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (total - rank) * float(values[index])))
        output[index] = running
    return output


def _recompute_e31_factorial_model(
    results: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Rebuild the balanced saturated factorial model without statsmodels."""
    factors = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    frame = results.copy()
    valid = _strict_bool_series(
        frame["valid_equivalent_output"], label="E31 factorial valid_equivalent_output"
    )
    frame["quality_itt"] = pd.to_numeric(
        frame["common_basis_gate_reduction_pct"], errors="raise"
    ).where(valid, 0.0)
    levels: dict[str, list[object]] = {
        factor: sorted(frame[factor].unique().tolist()) for factor in factors
    }
    expected_counts = {"listing_model": 3, "rule_set": 2, "window_gates": 3, "budget_seconds": 4}
    if any(len(levels[factor]) != count for factor, count in expected_counts.items()):
        raise RuntimeError("E31 factorial model does not contain the frozen factor levels")
    pivot = frame.pivot(
        index="input_circuit_sha256", columns=factors, values="quality_itt"
    ).sort_index()
    if pivot.shape != (391, 72) or pivot.isna().any().any():
        raise RuntimeError("E31 factorial model lacks the complete 391 by 72 panel")
    alternatives = [levels[factor][1:] for factor in factors]
    selections = [
        selection for selection in product(*([None, *values] for values in alternatives))
        if any(value is not None for value in selection)
    ]
    records: list[dict[str, object]] = []
    cluster_contrasts: list[np.ndarray] = []
    for selection in selections:
        selected = [(index, value) for index, value in enumerate(selection) if value is not None]
        contrast = np.zeros(len(pivot), dtype=float)
        for subset_size in range(len(selected) + 1):
            for subset in combinations(selected, subset_size):
                active = dict(subset)
                cell = tuple(active.get(index, levels[factor][0]) for index, factor in enumerate(factors))
                sign = -1.0 if (len(selected) - subset_size) % 2 else 1.0
                contrast += sign * pivot[cell].to_numpy(float)
        coefficient = ":".join(
            f"C({factors[index]})[T.{value}]"
            for index, value in selected
        )
        cluster_contrasts.append(contrast)
        records.append({
            "coefficient": coefficient,
            "estimate_pp": float(contrast.mean()),
            "interaction_order": len(selected),
            "inference_role": "EXPLORATORY_PARAMETERIZATION_DIAGNOSTIC",
            "confirmatory_primary_contrast": False,
        })
    coefficients = pd.DataFrame(records)
    contrasts = np.column_stack(cluster_contrasts)
    n_rows = len(frame)
    n_clusters = len(pivot)
    rank = n_clusters + len(coefficients)
    coefficients["cluster_robust_se_pp"] = np.nan
    coefficients["ci95_low_pp"] = np.nan
    coefficients["ci95_high_pp"] = np.nan
    coefficients["p_value_model_based"] = np.nan
    coefficients["holm_adjusted_p_within_role"] = np.nan
    ordered_columns = [
        "coefficient", "estimate_pp", "cluster_robust_se_pp", "ci95_low_pp",
        "ci95_high_pp", "p_value_model_based", "interaction_order", "inference_role",
        "holm_adjusted_p_within_role", "confirmatory_primary_contrast",
    ]
    coefficients = coefficients[ordered_columns]
    input_means = frame.groupby("input_circuit_sha256")["quality_itt"].transform("mean")
    cell_means = frame.groupby(factors)["quality_itt"].transform("mean")
    residual = frame["quality_itt"] - input_means - cell_means + frame["quality_itt"].mean()
    formula = (
        "common_basis_gate_reduction_pct_itt ~ C(input_circuit_sha256) + "
        "C(listing_model) * C(rule_set) * C(window_gates) * C(budget_seconds)"
    )
    diagnostics = {
        "formula": formula,
        "response": "common_basis_gate_reduction_pct_itt",
        "covariance": "NONE_FIXED_PANEL_DESCRIPTION_WRONG_OUTER_CLUSTER_INVALIDATED",
        "n_rows": n_rows,
        "n_input_clusters": n_clusters,
        "n_outer_families_not_used_as_input_df": int(frame["circuit_family"].nunique()),
        "design_matrix_rank": rank,
        "design_matrix_columns": rank,
        "condition_number": _balanced_factorial_condition_number(
            n_clusters, tuple(len(levels[factor]) for factor in factors)
        ),
        "residual_quantiles": {
            str(q): float(np.quantile(residual.to_numpy(float), q))
            for q in (0.0, 0.01, 0.05, 0.5, 0.95, 0.99, 1.0)
        },
        "zero_inflated_response_rate": float(frame["quality_itt"].eq(0).mean()),
        "p_value_interpretation": (
            "legacy 391-input-cluster SE/CI/p-values are invalid and intentionally null; "
            "supportive inference is reported separately at the 15-family outer-cluster level"
        ),
        "treatment_parameter_interpretation": (
            "baseline-conditional parameterization diagnostics, not marginal main effects"
        ),
        "posthoc_marginal_contrast_file": "posthoc_marginal_contrasts.csv",
    }
    return coefficients, diagnostics


def _recompute_e31_posthoc_marginal_contrasts(results: pd.DataFrame) -> pd.DataFrame:
    """Independently rebuild the disclosed post-hoc marginal operationalization."""
    factors = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    frame = results.copy()
    valid = _strict_bool_series(
        frame["valid_equivalent_output"],
        label="E31 post-hoc marginal valid_equivalent_output",
    )
    frame["quality_itt"] = pd.to_numeric(
        frame["common_basis_gate_reduction_pct"], errors="raise"
    ).where(valid, 0.0)
    levels = {factor: sorted(frame[factor].unique().tolist()) for factor in factors}
    if {factor: len(values) for factor, values in levels.items()} != {
        "listing_model": 3, "rule_set": 2, "window_gates": 3, "budget_seconds": 4,
    }:
        raise RuntimeError("E31 post-hoc marginal contrasts lack the frozen factor levels")
    pivot = frame.pivot(
        index="input_circuit_sha256", columns=factors, values="quality_itt"
    ).sort_index()
    if pivot.shape != (391, 72) or pivot.isna().any().any():
        raise RuntimeError("E31 post-hoc marginal contrasts lack the complete 391 by 72 panel")

    records: list[dict[str, object]] = []
    cluster_values: list[np.ndarray] = []
    for order in (1, 2):
        for chosen_indices in combinations(range(4), order):
            nonreference_levels = [levels[factors[index]][1:] for index in chosen_indices]
            for chosen_levels in product(*nonreference_levels):
                chosen = dict(zip(chosen_indices, chosen_levels))
                if (chosen_indices == (0, 1)
                        and chosen[0] == "WCL"
                        and chosen[1] == "COMMUTATION_PLUS_TEMPLATES"):
                    continue
                nuisance_indices = tuple(index for index in range(4) if index not in chosen)
                nuisance_grid = list(product(*(
                    levels[factors[index]] for index in nuisance_indices
                )))
                per_input = np.zeros(len(pivot), dtype=float)
                for nuisance_levels in nuisance_grid:
                    nuisance = dict(zip(nuisance_indices, nuisance_levels))
                    for active_mask in product((False, True), repeat=order):
                        cell: list[object] = []
                        for index, factor in enumerate(factors):
                            if index in chosen:
                                position = chosen_indices.index(index)
                                cell.append(chosen[index] if active_mask[position] else levels[factor][0])
                            else:
                                cell.append(nuisance[index])
                        sign = -1.0 if (order - sum(active_mask)) % 2 else 1.0
                        per_input += sign * pivot[tuple(cell)].to_numpy(float)
                per_input /= len(nuisance_grid)
                label = ":".join(
                    f"{factors[index]}[{chosen[index]}-vs-{levels[factors[index]][0]}]"
                    for index in chosen_indices
                )
                records.append({
                    "coefficient": f"MARGINAL::{label}",
                    "estimate_pp": float(per_input.mean()),
                    "interaction_order": order,
                    "inference_role": "SUPPORTIVE_POSTHOC_OPERATIONALIZATION_OF_FROZEN_CLASS",
                    "confirmatory_primary_contrast": False,
                })
                cluster_values.append(per_input)
    if (len(records) != 30
            or [str(record["coefficient"]) for record in records]
            != _expected_e31_posthoc_marginal_labels()):
        raise RuntimeError(f"E31 post-hoc marginal contrast count drifted: {len(records)}")
    output = pd.DataFrame(records)
    output["cluster_robust_se_pp"] = np.nan
    output["ci95_low_pp"] = np.nan
    output["ci95_high_pp"] = np.nan
    output["p_value_model_based"] = np.nan
    output["holm_adjusted_p_within_role"] = np.nan
    output["multiplicity_family_id"] = "E31_POSTHOC_MARGINAL_30"
    output["multiplicity_family_size"] = 30
    return output[[
        "coefficient", "estimate_pp", "cluster_robust_se_pp", "ci95_low_pp",
        "ci95_high_pp", "p_value_model_based", "interaction_order", "inference_role",
        "holm_adjusted_p_within_role", "confirmatory_primary_contrast",
        "multiplicity_family_id", "multiplicity_family_size",
    ]]


def _recompute_e31_family_effect_matrices(
    results: pd.DataFrame, protocol: dict,
) -> dict[str, object]:
    """Independently rebuild per-input/per-family 71- and 30-effect matrices."""
    factors = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    levels = {factor: list(protocol["factors"][factor]) for factor in factors}
    frame = results.copy()
    valid = _strict_bool_series(
        frame["valid_equivalent_output"], label="E31 family valid_equivalent_output"
    )
    frame["quality_itt"] = pd.to_numeric(
        frame["common_basis_gate_reduction_pct"], errors="raise"
    ).where(valid, 0.0)
    metadata = (
        frame[["input_circuit_sha256", "circuit_family"]]
        .drop_duplicates()
        .sort_values("input_circuit_sha256", kind="stable")
        .reset_index(drop=True)
    )
    if (len(metadata) != 391 or metadata["circuit_family"].nunique() != 15
            or frame.groupby("input_circuit_sha256")["circuit_family"].nunique().max() != 1):
        raise RuntimeError("E31 family effect metadata lacks the frozen 391/15 hierarchy")
    cells = pd.MultiIndex.from_product([levels[factor] for factor in factors], names=factors)
    pivot = frame.pivot(
        index="input_circuit_sha256", columns=factors, values="quality_itt"
    ).reindex(index=metadata["input_circuit_sha256"], columns=cells)
    if pivot.shape != (391, 72) or pivot.isna().any().any():
        raise RuntimeError("E31 family effects lack the complete 391 by 72 panel")
    cell_frame = cells.to_frame(index=False)
    design_columns: list[np.ndarray] = [np.ones(len(cells), dtype=float)]
    factorial_labels = ["Intercept"]
    for order in range(1, 5):
        for selected_factors in combinations(factors, order):
            for selected_values in product(*[levels[factor][1:] for factor in selected_factors]):
                indicator = np.ones(len(cells), dtype=float)
                pieces: list[str] = []
                for factor, value in zip(selected_factors, selected_values):
                    indicator *= cell_frame[factor].eq(value).to_numpy(float)
                    pieces.append(f"C({factor})[T.{value}]")
                design_columns.append(indicator)
                factorial_labels.append(":".join(pieces))
    design = np.column_stack(design_columns)
    if design.shape != (72, 72) or np.linalg.matrix_rank(design) != 72:
        raise RuntimeError("E31 independent factorial reconstruction is not saturated")
    input_71_values = pivot.to_numpy(float) @ np.linalg.inv(design).T
    input_71_values = input_71_values[:, 1:]
    factorial_labels = factorial_labels[1:]

    cell_lookup = {tuple(cell): index for index, cell in enumerate(cells.tolist())}
    marginal_vectors: list[np.ndarray] = []
    marginal_labels: list[str] = []
    for order in (1, 2):
        for factor_indices in combinations(range(4), order):
            for selected_values in product(*[levels[factors[index]][1:] for index in factor_indices]):
                selected = dict(zip(factor_indices, selected_values))
                if (order == 2 and selected.get(0) == "WCL"
                        and selected.get(1) == "COMMUTATION_PLUS_TEMPLATES"):
                    continue
                nuisance_indices = [index for index in range(4) if index not in selected]
                nuisance_cells = list(product(*[levels[factors[index]] for index in nuisance_indices]))
                vector = np.zeros(len(cells), dtype=float)
                for nuisance_values in nuisance_cells:
                    nuisance = dict(zip(nuisance_indices, nuisance_values))
                    for active_mask in product((False, True), repeat=order):
                        cell = tuple(
                            selected[index] if index in selected and active_mask[
                                factor_indices.index(index)
                            ]
                            else levels[factor][0] if index in selected
                            else nuisance[index]
                            for index, factor in enumerate(factors)
                        )
                        sign = -1.0 if (order - sum(active_mask)) % 2 else 1.0
                        vector[cell_lookup[cell]] += sign / len(nuisance_cells)
                label = ":".join(
                    f"{factors[index]}[{selected[index]}-vs-{levels[factors[index]][0]}]"
                    for index in factor_indices
                )
                marginal_vectors.append(vector)
                marginal_labels.append(f"MARGINAL::{label}")
    if len(marginal_labels) != 30:
        raise RuntimeError("E31 independent marginal reconstruction does not have 30 members")
    input_30_values = pivot.to_numpy(float) @ np.column_stack(marginal_vectors)

    def tables(values: np.ndarray, labels: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
        inputs = pd.DataFrame(values, columns=labels)
        inputs.insert(0, "circuit_family", metadata["circuit_family"].astype(str).to_numpy())
        inputs.insert(0, "input_circuit_sha256", metadata["input_circuit_sha256"].to_numpy())
        families = inputs.groupby("circuit_family", sort=True)[labels].mean().reset_index()
        return inputs, families

    input_71, family_71 = tables(input_71_values, factorial_labels)
    input_30, family_30 = tables(input_30_values, marginal_labels)
    return {
        "factorial_labels": factorial_labels,
        "marginal_labels": marginal_labels,
        "input_71": input_71,
        "family_71": family_71,
        "input_30": input_30,
        "family_30": family_30,
    }


def _wild_cluster_pvalues_independent(
    values: np.ndarray, *, replicates: int, seed: int,
) -> np.ndarray:
    """Recompute restricted Rademacher bootstrap-t without 3-D allocation."""
    values = np.asarray(values, dtype=float)
    clusters = values.shape[0]
    means = values.mean(axis=0)
    ses = values.std(axis=0, ddof=1) / math.sqrt(clusters)
    observed = np.divide(
        means, ses,
        out=np.where(means > 0, np.inf, np.where(means < 0, -np.inf, 0.0)),
        where=ses > 0,
    )
    rng = np.random.default_rng(seed)
    weights = rng.choice(np.array([-1.0, 1.0]), size=(replicates, clusters))
    bootstrap_means = weights @ values / clusters
    sums_of_squares = np.sum(values * values, axis=0)
    bootstrap_variance = (
        sums_of_squares[None, :] - clusters * bootstrap_means * bootstrap_means
    ) / (clusters - 1)
    bootstrap_variance = np.maximum(bootstrap_variance, 0.0)
    bootstrap_ses = np.sqrt(bootstrap_variance) / math.sqrt(clusters)
    bootstrap_t = np.divide(
        bootstrap_means, bootstrap_ses,
        out=np.where(
            bootstrap_means > 0, np.inf,
            np.where(bootstrap_means < 0, -np.inf, 0.0),
        ),
        where=bootstrap_ses > 0,
    )
    exceed = np.sum(np.abs(bootstrap_t) >= np.abs(observed)[None, :] - 1e-12, axis=0)
    return (exceed + 1.0) / (replicates + 1.0)


def _assert_numeric_columns_close(
    observed: pd.DataFrame, expected: pd.DataFrame, columns: list[str], *, label: str,
) -> None:
    for column in columns:
        left = pd.to_numeric(observed[column], errors="raise").to_numpy(float)
        right = pd.to_numeric(expected[column], errors="raise").to_numpy(float)
        if not np.allclose(left, right, rtol=5e-10, atol=1e-12, equal_nan=True):
            raise RuntimeError(f"{label} differs: {column}")


def _verify_e31_family_inference(
    root: Path, results: pd.DataFrame, protocol: dict, completion: dict,
) -> int:
    """Independently recompute the 15-family correction tables and statistics."""
    family_dir = root / "formal_run/analysis/family_inference"
    audit = json.loads((family_dir / "family_inference_correction_audit.json").read_text(
        encoding="utf-8"
    ))
    correction_gate_path = root / "posthoc_family_inference_correction_gate.json"
    correction_gate = json.loads(correction_gate_path.read_text(encoding="utf-8"))
    if (audit.get("status") != "PASS_POSTHOC_FAMILY_INFERENCE_CORRECTION"
            or audit.get("results_sha256") != _hash(root / "formal_run/final/formal_results.csv")
            or audit.get("correction_gate_sha256") != _hash(correction_gate_path)
            or audit.get("n_input_hashes") != 391
            or audit.get("n_independent_family_clusters") != 15
            or audit.get("family_cluster_degrees_of_freedom") != 14
            or audit.get("legacy_input_cluster_inference_valid") is not False
            or audit.get("unseen_family_generalization_status") != "BLOCKED"
            or correction_gate.get("outer_inference_cluster") != "circuit_family"
            or correction_gate.get("legacy_input_cluster_inference_valid") is not False
            or correction_gate.get("confirmatory_relabeling_authorized") is not False):
        raise RuntimeError("E31 family-inference correction audit is semantically invalid")
    matrices = _recompute_e31_family_effect_matrices(results, protocol)
    frozen_marginal_labels = list(correction_gate.get("marginal_contrast_labels", []))
    computed_marginal_labels = list(matrices["marginal_labels"])
    if (len(frozen_marginal_labels) != 30
            or len(set(frozen_marginal_labels)) != 30
            or set(frozen_marginal_labels) != set(computed_marginal_labels)):
        raise RuntimeError("E31 independently reconstructed marginal family differs")
    # The correction gate freezes presentation/multiplicity order.  The independent
    # reconstruction deliberately derives the members from the factorial protocol,
    # then aligns by label only after proving exact set equality.
    matrices["input_30"] = matrices["input_30"].reindex(
        columns=["input_circuit_sha256", "circuit_family", *frozen_marginal_labels]
    )
    matrices["family_30"] = matrices["family_30"].reindex(
        columns=["circuit_family", *frozen_marginal_labels]
    )
    matrices["marginal_labels"] = frozen_marginal_labels
    checked = 1
    for suffix, labels in (("factorial_71", matrices["factorial_labels"]),
                           ("marginal_30", matrices["marginal_labels"])):
        expected_family = matrices["family_71" if suffix == "factorial_71" else "family_30"]
        observed_family = pd.read_csv(family_dir / f"per_family_{suffix}_effects.csv")
        if (list(observed_family.columns) != list(expected_family.columns)
                or observed_family["circuit_family"].astype(str).tolist()
                != expected_family["circuit_family"].astype(str).tolist()):
            raise RuntimeError(f"E31 per-family {suffix} metadata differs")
        _assert_numeric_columns_close(
            observed_family, expected_family, list(labels), label=f"E31 per-family {suffix}",
        )
        input_table = matrices["input_71" if suffix == "factorial_71" else "input_30"]
        fixed = pd.read_csv(family_dir / f"fixed_panel_{suffix}_descriptive.csv")
        if (fixed["coefficient"].astype(str).tolist() != list(labels)
                or not fixed["legacy_input_cluster_inference_status"].eq(
                    "INVALID_WRONG_OUTER_CLUSTER"
                ).all()
                or not fixed["inference_status"].eq("DESCRIPTIVE_POINT_ESTIMATE_ONLY").all()
                or fixed["design_based_p_value"].notna().any()
                or fixed["design_based_confidence_interval"].notna().any()):
            raise RuntimeError(f"E31 fixed-panel {suffix} semantics differ")
        expected_fixed = pd.DataFrame({
            "fixed_391_input_weighted_estimate_pp": input_table[list(labels)].mean(axis=0)
        })
        _assert_numeric_columns_close(
            fixed, expected_fixed, ["fixed_391_input_weighted_estimate_pp"],
            label=f"E31 fixed-panel {suffix}",
        )
        supportive = pd.read_csv(family_dir / f"family_supportive_{suffix}.csv")
        values = expected_family[list(labels)].to_numpy(float)
        estimates = values.mean(axis=0)
        ses = values.std(axis=0, ddof=1) / math.sqrt(15)
        t_stats = np.divide(
            estimates, ses,
            out=np.where(estimates > 0, np.inf, np.where(estimates < 0, -np.inf, 0.0)),
            where=ses > 0,
        )
        p_values = 2.0 * student_t.sf(np.abs(t_stats), 14)
        critical = float(student_t.ppf(0.975, 14))
        replicates = int(correction_gate["small_cluster_sensitivity"]["replicates"])
        seed = int(correction_gate["small_cluster_sensitivity"]["seed"])
        wild = _wild_cluster_pvalues_independent(values, replicates=replicates, seed=seed)
        expected_supportive = pd.DataFrame({
            "equal_family_estimate_pp": estimates,
            "family_cluster_se_pp": ses,
            "t14_ci95_low_pp": estimates - critical * ses,
            "t14_ci95_high_pp": estimates + critical * ses,
            "t14_p_value_model_based": p_values,
            "wild_cluster_bootstrap_t_p_value": wild,
            "holm_adjusted_t14_p": _holm_adjusted(p_values),
            "holm_adjusted_wild_cluster_p": _holm_adjusted(wild),
        })
        if (supportive["coefficient"].astype(str).tolist() != list(labels)
                or not supportive["family_cluster_df"].eq(14).all()
                or not supportive["confirmatory_claim_allowed"].eq(False).all()
                or not supportive["probability_sample_of_families"].eq(False).all()
                or not supportive["unseen_family_generalization_status"].eq("BLOCKED").all()
                or not supportive["wild_cluster_bootstrap_replicates"].eq(replicates).all()
                or not supportive["wild_cluster_bootstrap_seed"].eq(seed).all()):
            raise RuntimeError(f"E31 supportive family {suffix} semantics differ")
        _assert_numeric_columns_close(
            supportive, expected_supportive, list(expected_supportive.columns),
            label=f"E31 supportive family {suffix}",
        )
        checked += 3
    return checked


def _verify_e31_snapshot(
    snapshot: Path, results: pd.DataFrame, design: pd.DataFrame, completion: dict,
) -> None:
    """Cross-check the sealed SQLite source against CSV, design, and manifest."""
    connection = sqlite3.connect(f"file:{snapshot.resolve()}?mode=ro", uri=True, timeout=30)
    try:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("E31 sealed SQLite snapshot failed integrity_check")
        records = connection.execute(
            "SELECT run_id, run_order, result_json, committed_utc FROM results ORDER BY run_order"
        ).fetchall()
    except sqlite3.DatabaseError as error:
        raise RuntimeError("E31 sealed SQLite snapshot is unreadable or malformed") from error
    finally:
        connection.close()
    if len(records) != 28152:
        raise RuntimeError("E31 sealed SQLite snapshot does not contain 28,152 rows")
    snapshot_keys = [(str(row[0]), int(row[1])) for row in records]
    csv_keys = list(zip(results["run_id"].astype(str), results["run_order"].astype(int)))
    design_keys = list(zip(design["run_id"].astype(str), design["run_order"].astype(int)))
    if snapshot_keys != csv_keys or snapshot_keys != design_keys:
        raise RuntimeError("E31 SQLite, CSV, and frozen design identities differ")
    payloads: list[dict] = []
    for run_id, run_order, payload_text, _ in records:
        try:
            payload = json.loads(payload_text)
        except (TypeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"E31 SQLite result JSON is malformed at run_order={run_order}") from error
        if str(payload.get("run_id")) != str(run_id) or int(payload.get("run_order", -1)) != int(run_order):
            raise RuntimeError(f"E31 SQLite payload identity drift at run_order={run_order}")
        payloads.append(payload)
    snapshot_statuses = pd.Series(
        [str(payload.get("status")) for payload in payloads], dtype="object"
    )
    if not snapshot_statuses.equals(results["status"].astype(str).reset_index(drop=True)):
        raise RuntimeError("E31 SQLite and CSV status sequences differ")
    payload_frame = pd.DataFrame(payloads).sort_values(
        "run_order", kind="stable"
    ).reset_index(drop=True)
    string_fields = [
        "run_id", "protocol_sha256", "design_manifest_sha256", "input_circuit_sha256",
        "circuit_id", "circuit_family", "listing_model", "rule_set", "status",
        "output_circuit_sha256",
    ]
    integer_fields = ["run_order", "window_gates", "budget_seconds", "primary_pair_orientation"]
    numeric_fields = [
        "exact_fidelity", "common_basis_gate_reduction_pct",
        "wall_seconds_end_to_end", "peak_rss_mb",
    ]
    required_payload_fields = {
        *string_fields, *integer_fields, *numeric_fields, "valid_equivalent_output",
    }
    missing_payload_fields = required_payload_fields.difference(payload_frame.columns)
    if missing_payload_fields:
        raise RuntimeError(
            f"E31 SQLite payload schema is incomplete: {sorted(missing_payload_fields)}"
        )
    def normalize_string(value: object) -> str:
        return "" if pd.isna(value) else str(value)
    for field in string_fields:
        snapshot_values = payload_frame[field].map(normalize_string)
        csv_values = results[field].map(normalize_string).reset_index(drop=True)
        if not snapshot_values.equals(csv_values):
            raise RuntimeError(f"E31 SQLite and CSV field differ: {field}")
    for field in integer_fields:
        if not pd.to_numeric(payload_frame[field], errors="raise").astype(int).equals(
            pd.to_numeric(results[field], errors="raise").astype(int).reset_index(drop=True)
        ):
            raise RuntimeError(f"E31 SQLite and CSV field differ: {field}")
    for field in numeric_fields:
        snapshot_values = pd.to_numeric(payload_frame[field], errors="coerce")
        csv_values = pd.to_numeric(results[field], errors="coerce").reset_index(drop=True)
        equal = [
            (pd.isna(left) and pd.isna(right))
            or (not pd.isna(left) and not pd.isna(right)
                and math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12))
            for left, right in zip(snapshot_values, csv_values)
        ]
        if not all(equal):
            raise RuntimeError(f"E31 SQLite and CSV field differ: {field}")
    snapshot_valid = _strict_bool_series(
        payload_frame["valid_equivalent_output"], label="E31 SQLite valid_equivalent_output"
    )
    csv_valid = _strict_bool_series(
        results["valid_equivalent_output"], label="E31 CSV valid_equivalent_output"
    ).reset_index(drop=True)
    if not snapshot_valid.equals(csv_valid):
        raise RuntimeError("E31 SQLite and CSV field differ: valid_equivalent_output")
    status_counts = {str(key): int(value) for key, value in snapshot_statuses.value_counts().items()}
    if status_counts != completion.get("status_counts"):
        raise RuntimeError("E31 completion status counts differ from the sealed SQLite source")
    committed = [str(row[3]) for row in records]
    try:
        committed_times = [datetime.fromisoformat(value) for value in committed]
    except ValueError as error:
        raise RuntimeError("E31 SQLite contains a malformed commit timestamp") from error
    if any(
        committed_times[index] < committed_times[index - 1]
        for index in range(1, len(committed_times))
    ):
        raise RuntimeError("E31 SQLite commit timestamps are not monotonic")
    if (completion.get("first_committed_utc") != committed[0]
            or completion.get("last_committed_utc") != committed[-1]):
        raise RuntimeError("E31 completion commit-time bounds differ from the sealed SQLite source")


def _verified_repo_relative_path(relative: object, *, label: str) -> Path:
    """Resolve a manifest path while refusing absolute/path-escape records."""
    if not isinstance(relative, str) or not relative:
        raise RuntimeError(f"{label} path is missing")
    candidate = (PROJECT_ROOT / relative).resolve()
    root = PROJECT_ROOT.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"{label} path escapes the project root") from error
    return candidate


def _verify_e31_semantic_replay(
    root: Path, results: pd.DataFrame, completion: dict,
) -> int:
    """Independently verify every success-row replay certificate and saved QPY."""
    replay_dir = root / "formal_run/semantic_replay"
    completion_replay = completion.get("semantic_replay", {})
    success = results.loc[results["status"].astype(str).eq("success")].sort_values(
        "run_order", kind="stable"
    ).reset_index(drop=True)
    if (completion_replay.get("status") != "PASS"
            or completion_replay.get("success_rows_verified_and_bound") != len(success)):
        raise RuntimeError("E31 completion does not bind the full semantic replay")
    expected_artifacts = {"semantic_replay_gate.json", "semantic_replay_manifest.json"}
    records = completion_replay.get("artifacts", {})
    if set(records) != expected_artifacts:
        raise RuntimeError("E31 semantic replay top-level inventory is incomplete")
    checked = 0
    for name, record in records.items():
        path = replay_dir / name
        if path.stat().st_size != int(record["bytes"]):
            raise RuntimeError(f"E31 semantic replay artifact size mismatch: {name}")
        _expect_hash(path, str(record["sha256"]), f"e31-semantic-replay:{name}")
        checked += 1
    gate_path = replay_dir / "semantic_replay_gate.json"
    manifest_path = replay_dir / "semantic_replay_manifest.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cells = manifest.get("semantic_cells", [])
    bindings = manifest.get("row_bindings", [])
    boundary = manifest.get("formal_checkpoint_boundary", {})
    if (gate.get("status") != "PASS"
            or gate.get("gate") != "E31_ALL_SUCCESS_ROWS_INDEPENDENT_SEMANTIC_REPLAY"
            or gate.get("semantic_method") != "exact dense operator, not sampled fidelity"
            or gate.get("manifest_sha256") != _hash(manifest_path)
            or manifest.get("status") != "PASS"
            or manifest.get("all_success_rows_passed") is not True
            or manifest.get("budget_dimension_collapsed_only_after_exact_group_invariant_check")
            is not True
            or manifest.get("formal_rows") != len(results)
            or manifest.get("success_rows_verified_and_bound") != len(success)
            or gate.get("success_rows_verified_and_bound") != len(success)
            or manifest.get("non_success_rows_not_semantically_replayed")
            != len(results) - len(success)
            or manifest.get("protocol_sha256")
            != _hash(PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json")
            or manifest.get("design_manifest_sha256") != _hash(root / "design_manifest.csv")
            or boundary.get("committed_rows") != len(results)
            or boundary.get("min_run_order") != 0
            or boundary.get("max_run_order") != len(results) - 1
            or boundary.get("unique_run_ids") != len(results)
            or boundary.get("unique_run_orders") != len(results)
            or boundary.get("status_counts") != completion.get("status_counts")):
        raise RuntimeError("E31 semantic replay gate or checkpoint boundary is invalid")
    if not isinstance(bindings, list) or len(bindings) != len(success):
        raise RuntimeError("E31 semantic replay lacks one binding per success row")
    if not isinstance(cells, list) or len(cells) != gate.get("unique_semantic_cells_replayed"):
        raise RuntimeError("E31 semantic replay cell inventory is incomplete")
    cell_by_id = {str(record.get("semantic_cell_id")): record for record in cells}
    if len(cell_by_id) != len(cells):
        raise RuntimeError("E31 semantic replay contains duplicate semantic cells")

    cell_certificates: dict[str, dict] = {}
    qpy_hashes: dict[Path, str] = {}
    for cell_id, record in cell_by_id.items():
        certificate_path = _verified_repo_relative_path(
            record.get("cell_certificate_path"), label="E31 cell certificate",
        )
        _expect_hash(
            certificate_path, str(record.get("cell_certificate_sha256")),
            f"e31-semantic-cell:{cell_id}",
        )
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        qpy_path = _verified_repo_relative_path(record.get("qpy_path"), label="E31 QPY")
        qpy_sha = str(record.get("qpy_sha256"))
        if qpy_path in qpy_hashes and qpy_hashes[qpy_path] != qpy_sha:
            raise RuntimeError("E31 semantic replay assigns conflicting hashes to one QPY")
        qpy_hashes[qpy_path] = qpy_sha
        reduction = float(certificate.get("replayed_common_basis_gate_reduction_pct"))
        original = int(certificate.get("replayed_original_common_basis_gate_count"))
        optimized = int(certificate.get("replayed_optimized_common_basis_gate_count"))
        expected_reduction = 0.0 if original == 0 else 100.0 * (1.0 - optimized / original)
        if (certificate.get("status") != "PASS"
                or certificate.get("semantic_cell_id") != cell_id
                or certificate.get("qpy_path") != record.get("qpy_path")
                or certificate.get("qpy_sha256") != qpy_sha
                or certificate.get("qpy_roundtrip_logical_hash_verified") is not True
                or certificate.get("cross_budget_semantic_identity_verified") is not True
                or certificate.get("replayed_output_circuit_sha256")
                != certificate.get("recorded_output_circuit_sha256")
                or original < 0 or optimized < 0
                or not math.isclose(reduction, expected_reduction, rel_tol=0.0, abs_tol=1e-12)
                or not math.isclose(
                    reduction,
                    float(certificate.get("recorded_common_basis_gate_reduction_pct")),
                    rel_tol=0.0, abs_tol=1e-12,
                )
                or float(certificate.get("independent_trace_average_gate_fidelity"))
                < float(certificate.get("fidelity_threshold"))
                or float(certificate.get("phase_aligned_identity_relative_frobenius_norm"))
                > 1e-6):
            raise RuntimeError(f"E31 semantic cell certificate is invalid: {cell_id}")
        cell_certificates[cell_id] = certificate
        checked += 1
    for qpy_path, expected in qpy_hashes.items():
        _expect_hash(qpy_path, expected, f"e31-semantic-qpy:{qpy_path.name}")
        checked += 1

    seen_rows: set[tuple[str, int]] = set()
    bound_per_cell: dict[str, int] = {cell_id: 0 for cell_id in cell_by_id}
    for expected_row, record in zip(success.to_dict(orient="records"), bindings):
        row_key = (str(record.get("run_id")), int(record.get("run_order", -1)))
        expected_key = (str(expected_row["run_id"]), int(expected_row["run_order"]))
        if row_key != expected_key or row_key in seen_rows:
            raise RuntimeError("E31 semantic replay row identity/order differs from sealed results")
        seen_rows.add(row_key)
        certificate_path = _verified_repo_relative_path(
            record.get("certificate_path"), label="E31 row certificate",
        )
        _expect_hash(
            certificate_path, str(record.get("certificate_sha256")),
            f"e31-semantic-row:{row_key[1]}",
        )
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        cell_id = str(certificate.get("semantic_cell_id"))
        cell_certificate = cell_certificates.get(cell_id)
        cell_record = cell_by_id.get(cell_id, {})
        if (certificate.get("status") != "PASS"
                or certificate.get("audit_role")
                != "E31_SUCCESS_ROW_TO_DETERMINISTIC_SEMANTIC_CELL_BINDING"
                or certificate.get("run_id") != expected_key[0]
                or certificate.get("run_order") != expected_key[1]
                or certificate.get("cross_budget_semantic_identity_verified") is not True
                or cell_certificate is None
                or certificate.get("cell_certificate_path")
                != cell_record.get("cell_certificate_path")
                or certificate.get("cell_certificate_sha256")
                != cell_record.get("cell_certificate_sha256")
                or certificate.get("qpy_path") != record.get("qpy_path")
                or certificate.get("qpy_sha256") != record.get("qpy_sha256")
                or certificate.get("qpy_path") != cell_record.get("qpy_path")
                or certificate.get("qpy_sha256") != cell_record.get("qpy_sha256")
                or int(certificate.get("budget_seconds"))
                != int(expected_row["budget_seconds"])
                or certificate.get("recorded_output_circuit_sha256")
                != str(expected_row["output_circuit_sha256"])
                or not math.isclose(
                    float(certificate.get("recorded_exact_fidelity")),
                    float(expected_row["exact_fidelity"]), rel_tol=1e-12, abs_tol=1e-12,
                )
                or int(certificate.get("recorded_original_common_basis_gate_count"))
                != int(expected_row["original_common_basis_gate_count"])
                or int(certificate.get("recorded_optimized_common_basis_gate_count"))
                != int(expected_row["optimized_common_basis_gate_count"])
                or not math.isclose(
                    float(certificate.get("recorded_common_basis_gate_reduction_pct")),
                    float(expected_row["common_basis_gate_reduction_pct"]),
                    rel_tol=0.0, abs_tol=1e-12,
                )):
            raise RuntimeError(f"E31 semantic row certificate is invalid: {expected_key[1]}")
        bound_per_cell[cell_id] += 1
        checked += 1
    for cell_id, record in cell_by_id.items():
        if (bound_per_cell[cell_id] != int(record.get("formal_success_rows_bound", -1))
                or bound_per_cell[cell_id]
                != int(cell_certificates[cell_id].get("formal_success_rows_bound", -1))):
            raise RuntimeError(f"E31 semantic-cell row cardinality differs: {cell_id}")
    return checked


def _verify_e31_runtime_environment(root: Path, protocol_sha: str, design_sha: str) -> int:
    """Verify the seven directly frozen sources and the recorded runtime evidence."""
    environment_path = root / "formal_run/environment.json"
    release_gate_path = root / "formal_release_gate.json"
    power_path = root / "dual_estimand_power.json"
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    release_gate = json.loads(release_gate_path.read_text(encoding="utf-8"))
    power_sha = _hash(power_path)
    expected_sources = {
        "experiments/e31_formal_orchestrator.py",
        "experiments/e31_listing_phase2b_interaction.py",
        "experiments/e31_resource_smoke.py",
        "experiments/e31_shared_rule_worker.py",
        "src/circuits/real_benchmarks.py",
        "src/optimisation/phase1/wire_traversal.py",
        "src/optimisation/phase2/template_matcher.py",
    }
    if (environment.get("protocol_sha256") != protocol_sha
            or environment.get("design_manifest_sha256") != design_sha
            or environment.get("power_sha256") != power_sha
            or environment.get("cold_process_per_cell") is not True
            or environment.get("qasm_preflight", {}).get("unique_qasm_inputs_parsed") != 391
            or environment.get("release_gate") != release_gate
            or set(environment.get("source_sha256", {})) != expected_sources
            or environment.get("thread_limits") != {
                "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
                "RAYON_NUM_THREADS": "1",
            }):
        raise RuntimeError("E31 frozen runtime environment is incomplete or hash-drifted")
    resource_plan = environment.get("resource_plan_at_start", {})
    if (resource_plan.get("workers") != 1 or resource_plan.get("total_rows") != 28152
            or resource_plan.get("pending_rows") != 28152
            or resource_plan.get("completed_rows") != 0
            or resource_plan.get("per_worker_memory_cap_mb") != 3072
            or resource_plan.get("aggregate_memory_cap_mb") != 3072):
        raise RuntimeError("E31 frozen start-time resource plan differs from the formal contract")
    packages = environment.get("packages", {})
    if not {"numpy", "pandas", "psutil", "qiskit", "scipy"}.issubset(packages):
        raise RuntimeError("E31 frozen runtime package inventory is incomplete")
    executable_sha = str(environment.get("python_executable_sha256", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", executable_sha):
        raise RuntimeError("E31 Python executable hash is absent or malformed")
    executable = Path(str(environment.get("python_executable", "")))
    if executable.is_file() and _hash(executable) != executable_sha:
        raise RuntimeError("E31 recorded Python executable has hash-drifted on the current host")
    source_hashes = environment["source_sha256"]
    for relative, expected in source_hashes.items():
        _expect_hash(PROJECT_ROOT / relative, expected, f"e31-runtime-source:{relative}")
    if (release_gate.get("status") != "COMPLETE"
            or release_gate.get("guoq_status") != "COMPLETE"
            or release_gate.get("heldout_status") != "COMPLETE"
            or release_gate.get("protocol_sha256") != protocol_sha
            or release_gate.get("design_manifest_sha256") != design_sha
            or release_gate.get("power_sha256") != power_sha
            or not release_gate.get("guoq_evidence_sha256")
            or not release_gate.get("heldout_evidence_sha256")):
        raise RuntimeError("E31 formal release gate is incomplete or not bound to the design")
    checked = len(source_hashes) + 1
    for relative, expected in release_gate["guoq_evidence_sha256"].items():
        _expect_hash(PROJECT_ROOT / relative, expected, f"e31-guoq-gate:{relative}")
        checked += 1
    heldout_root = PROJECT_ROOT / "data/v10/prepaper"
    for relative, expected in release_gate["heldout_evidence_sha256"].items():
        _expect_hash(heldout_root / relative, expected, f"e31-heldout-gate:{relative}")
        checked += 1
    return checked


def _verify_e31_transitive_source_gate(
    root: Path, protocol_sha: str, design_sha: str,
) -> tuple[dict, int]:
    """Verify the disclosed post-hoc import closure without treating it as pre-run proof."""
    gate_path = root / "transitive_source_provenance_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    boundary = gate.get("checkpoint_boundary", {})
    closure = gate.get("omitted_first_party_import_closure", {})
    expected_closure = {
        "experiments/e31_factorial_pareto_design.py",
        "src/circuits/__init__.py",
        "src/circuits/generator_v2.py",
        "src/equivalence.py",
        "src/optimisation/__init__.py",
        "src/optimisation/_gate_predicates.py",
        "src/optimisation/base.py",
        "src/optimisation/ceiling_aware.py",
        "src/optimisation/constants.py",
        "src/optimisation/phase1/__init__.py",
        "src/optimisation/phase1/genetic_algorithm.py",
        "src/optimisation/phase1/greedy.py",
        "src/optimisation/phase1/random_local_search.py",
        "src/optimisation/phase1/simulated_annealing.py",
        "src/optimisation/phase2/__init__.py",
        "src/optimisation/phase2/commutation_rewriter.py",
    }
    environment_path = PROJECT_ROOT / str(gate.get("environment_path", ""))
    disclosure_path = PROJECT_ROOT / str(gate.get("disclosure_path", ""))
    if (gate.get("status")
            != "POSTHOC_TRANSITIVE_SOURCE_LIMITATION_FROZEN_BEFORE_AGGREGATE_ANALYSIS"
            or gate.get("protocol_sha256") != protocol_sha
            or gate.get("design_manifest_sha256") != design_sha
            or gate.get("direct_frozen_source_count") != 7
            or gate.get("omitted_source_count") != 16
            or set(closure) != expected_closure
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
            or boundary.get("committed_rows", 28152) >= 28152
            or boundary.get("min_run_order") != 0
            or boundary.get("max_run_order") != boundary.get("committed_rows", 0) - 1
            or boundary.get("unique_run_ids") != boundary.get("committed_rows")
            or boundary.get("unique_run_orders") != boundary.get("committed_rows")
            or boundary.get("sqlite_integrity") != "ok"
            or sum(boundary.get("status_counts_only", {}).values())
            != boundary.get("committed_rows")):
        raise RuntimeError("E31 transitive-source provenance limitation gate is invalid")
    try:
        created = datetime.fromisoformat(str(gate.get("created_utc", "")))
        last_boundary = datetime.fromisoformat(str(boundary.get("last_committed_utc", "")))
    except ValueError as error:
        raise RuntimeError("E31 transitive-source gate timestamp is invalid") from error
    if created <= last_boundary:
        raise RuntimeError("E31 transitive-source gate predates its checkpoint boundary")
    _expect_hash(environment_path, gate.get("environment_sha256", ""),
                 "e31-transitive:environment")
    _expect_hash(disclosure_path, gate.get("disclosure_sha256", ""),
                 "e31-transitive:disclosure")
    first_commit = datetime.fromisoformat(str(boundary["first_committed_utc"]))
    for relative, record in closure.items():
        _expect_hash(PROJECT_ROOT / relative, record.get("sha256", ""),
                     f"e31-transitive-source:{relative}")
        try:
            last_write = datetime.fromisoformat(str(record["last_write_local"]))
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(f"E31 transitive source timestamp is invalid: {relative}") from error
        if last_write >= first_commit:
            raise RuntimeError(f"E31 transitive source was not recorded before row 0: {relative}")
    return gate, len(closure) + 2


def _verify_e31_pareto_aggregation_gate(
    root: Path, protocol_sha: str, design_sha: str,
) -> tuple[dict, int]:
    """Verify the post-hoc aggregation disclosure without upgrading its role."""
    gate_path = root / "posthoc_pareto_aggregation_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    boundary = gate.get("checkpoint_boundary", {})
    sensitivity = gate.get("required_sensitivity_grid", {})
    expected_interpretation = (
        "Pareto results are exploratory and aggregation-conditional; disagreement across "
        "the four frozen post-hoc schemes blocks an aggregation-invariant frontier claim."
    )
    if (gate.get("status")
            != "POSTHOC_PARETO_AGGREGATION_FROZEN_BEFORE_AGGREGATE_ANALYSIS"
            or gate.get("protocol_sha256") != protocol_sha
            or gate.get("design_manifest_sha256") != design_sha
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
        raise RuntimeError("E31 Pareto aggregation limitation gate is invalid")
    try:
        created = datetime.fromisoformat(str(gate.get("created_utc", "")))
        last_boundary = datetime.fromisoformat(str(boundary.get("last_committed_utc", "")))
    except ValueError as error:
        raise RuntimeError("E31 Pareto aggregation gate timestamp is invalid") from error
    if created <= last_boundary:
        raise RuntimeError("E31 Pareto aggregation gate predates its checkpoint boundary")
    disclosure = PROJECT_ROOT / str(gate.get("disclosure_path", ""))
    _expect_hash(disclosure, gate.get("disclosure_sha256", ""), "e31-pareto-aggregation")
    return gate, 1


def _expected_e31_posthoc_marginal_labels() -> list[str]:
    factors = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    levels: dict[str, list[object]] = {
        "listing_model": ["LBL", "RANDOM_TOPOLOGICAL", "WCL"],
        "rule_set": ["COMMUTATION_ONLY", "COMMUTATION_PLUS_TEMPLATES"],
        "window_gates": [4, 16, 64],
        "budget_seconds": [1, 10, 30, 120],
    }
    labels: list[str] = []
    for order in (1, 2):
        for chosen_indices in combinations(range(4), order):
            for chosen_levels in product(*[levels[factors[index]][1:] for index in chosen_indices]):
                chosen = dict(zip(chosen_indices, chosen_levels))
                if (chosen_indices == (0, 1) and chosen[0] == "WCL"
                        and chosen[1] == "COMMUTATION_PLUS_TEMPLATES"):
                    continue
                labels.append("MARGINAL::" + ":".join(
                    f"{factors[index]}[{chosen[index]}-vs-{levels[factors[index]][0]}]"
                    for index in chosen_indices
                ))
    return labels


def _verify_e31_contrast_expansion_gate(
    root: Path, protocol_sha: str, design_sha: str,
) -> tuple[dict, int]:
    """Verify the post-hoc scalar expansion and its exact Holm family."""
    gate_path = root / "posthoc_contrast_expansion_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    boundary = gate.get("checkpoint_boundary", {})
    expected_labels = _expected_e31_posthoc_marginal_labels()
    if (gate.get("status")
            != "POSTHOC_CONTRAST_EXPANSION_FROZEN_BEFORE_AGGREGATE_ANALYSIS"
            or gate.get("created_date") != "2026-08-24"
            or gate.get("disclosure_path")
            != "docs/review/e31_contrast_expansion_limitation_2026-08-24.md"
            or gate.get("protocol_sha256") != protocol_sha
            or gate.get("design_manifest_sha256") != design_sha
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
        raise RuntimeError("E31 contrast-expansion limitation gate is invalid")
    try:
        created = datetime.fromisoformat(str(gate.get("created_utc", "")))
        last_boundary = datetime.fromisoformat(str(boundary.get("last_committed_utc", "")))
    except ValueError as error:
        raise RuntimeError("E31 contrast-expansion gate timestamp is invalid") from error
    if created <= last_boundary:
        raise RuntimeError("E31 contrast-expansion gate predates its checkpoint boundary")
    disclosure = PROJECT_ROOT / str(gate.get("disclosure_path", ""))
    _expect_hash(disclosure, gate.get("disclosure_sha256", ""), "e31-contrast-expansion")
    return gate, 1


def _verify_e31_formal() -> int:
    """Independently verify the sealed E31 schedule, hashes, and analysis gates."""
    root = PROJECT_ROOT / "data/v11/e31_factorial_pareto"
    final = root / "formal_run/final"
    completion = json.loads((final / "formal_completion_manifest.json").read_text(encoding="utf-8"))
    if completion.get("status") != "FORMAL_COMPLETE_PENDING_INDEPENDENT_RELEASE_VERIFICATION":
        raise RuntimeError("E31 completion manifest is not awaiting independent verification")
    if (completion.get("independent_release_verification_required") is not True
            or completion.get("independent_release_verification_embedded_in_completion") is not False):
        raise RuntimeError("E31 completion does not preserve the independent verification boundary")
    if (completion.get("source_provenance_rating") != "PARTIAL"
            or completion.get("complete_cryptographic_prerun_source_closure") is not False
            or completion.get("static_first_party_source_closure_count") != 23
            or completion.get("dynamic_imports_not_proven") is not True
            or completion.get("temporal_gate_provenance_rating") != "PARTIAL"
            or completion.get("release_eligibility_qualification")
            != "eligible only with the full semantic replay and bound post-hoc transitive-source, contrast-expansion, Pareto-aggregation, and family-inference-correction limitations disclosed"):
        raise RuntimeError("E31 completion manifest overstates transitive source provenance")
    if (completion.get("marginal_contrast_inference_role")
            != "SUPPORTIVE_POSTHOC_OPERATIONALIZATION_OF_FROZEN_CLASS"
            or completion.get("marginal_contrast_family_fully_preregistered") is not False
            or completion.get("marginal_contrast_multiplicity_family_size") != 30):
        raise RuntimeError("E31 completion manifest overstates marginal contrast preregistration")
    if (completion.get("legacy_input_cluster_inference_valid") is not False
            or completion.get("family_inference_outer_cluster") != "circuit_family"
            or completion.get("family_inference_n_independent_clusters") != 15
            or completion.get("family_inference_degrees_of_freedom") != 14
            or completion.get("family_inference_correction_status")
            != "PASS_POSTHOC_FAMILY_INFERENCE_CORRECTION"
            or completion.get("unseen_family_generalization_status") != "BLOCKED"):
        raise RuntimeError("E31 completion does not enforce the 15-family inference correction")
    if (completion.get("pareto_inference_role") != "EXPLORATORY_POSTHOC_AGGREGATION"
            or completion.get("pareto_aggregation_functionals_preregistered") is not False):
        raise RuntimeError("E31 completion manifest overstates Pareto aggregation status")
    if (completion.get("rows") != 28152 or completion.get("scheduled_rows") != 28152
            or completion.get("unique_input_hashes") != 391
            or completion.get("outer_families") != 15):
        raise RuntimeError("E31 completion cardinalities differ from the frozen design")
    checked = 0
    artifacts = completion.get("artifacts", {})
    if set(artifacts) != {"formal_results.csv", "checkpoint_final.sqlite3"}:
        raise RuntimeError("E31 completion manifest has an invalid sealed artifact inventory")
    for name, record in artifacts.items():
        path = final / name
        if path.stat().st_size != int(record["bytes"]):
            raise RuntimeError(f"E31 sealed artifact size mismatch: {name}")
        _expect_hash(path, record["sha256"], f"e31-final:{name}")
        checked += 1
    if completion.get("formal_analysis_gate_passed") is not True:
        raise RuntimeError("E31 completion manifest does not assert a passed formal analysis")
    analysis_dir = root / "formal_run/analysis"
    analysis_artifacts = completion.get("analysis_artifacts", {})
    expected_analysis = {
        "equal_budget_pareto_summary.csv",
        "full_factorial_model_coefficients.csv",
        "full_factorial_model_diagnostics.json",
        "posthoc_marginal_contrasts.csv",
        "pareto_aggregation_sensitivity.csv",
        "pareto_hypervolume_audit.json",
        "analysis_gate_audit.json",
        "run_order_temporal_diagnostics.csv",
        "host_environment_audit.json",
    }
    if set(analysis_artifacts) != expected_analysis:
        raise RuntimeError("E31 completion manifest has an incomplete analysis inventory")
    for name, record in analysis_artifacts.items():
        path = analysis_dir / name
        if path.stat().st_size != int(record["bytes"]):
            raise RuntimeError(f"E31 analysis artifact size mismatch: {name}")
        _expect_hash(path, record["sha256"], f"e31-analysis:{name}")
        checked += 1
    family_dir = analysis_dir / "family_inference"
    family_artifacts = completion.get("family_inference_artifacts", {})
    expected_family_artifacts = {
        "fixed_panel_factorial_71_descriptive.csv",
        "fixed_panel_marginal_30_descriptive.csv",
        "family_supportive_factorial_71.csv",
        "family_supportive_marginal_30.csv",
        "per_family_factorial_71_effects.csv",
        "per_family_marginal_30_effects.csv",
        "primary_estimand_validity.json",
        "family_inference_correction_audit.json",
    }
    if set(family_artifacts) != expected_family_artifacts:
        raise RuntimeError("E31 family-inference correction inventory is incomplete")
    for name, record in family_artifacts.items():
        path = family_dir / name
        if path.stat().st_size != int(record["bytes"]):
            raise RuntimeError(f"E31 family-inference artifact size mismatch: {name}")
        _expect_hash(path, record["sha256"], f"e31-family-inference:{name}")
        checked += 1
    bindings = completion["bindings"]
    for key, path in {
        "protocol_sha256": PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json",
        "design_manifest_sha256": root / "design_manifest.csv",
        "environment_sha256": root / "formal_run/environment.json",
        "formal_release_gate_sha256": root / "formal_release_gate.json",
        "preanalysis_method_erratum_gate_sha256": root / "preanalysis_method_erratum_gate.json",
        "host_environment_limitation_gate_sha256": root / "host_environment_limitation_gate.json",
        "transitive_source_provenance_gate_sha256": root / "transitive_source_provenance_gate.json",
        "posthoc_pareto_aggregation_gate_sha256": root / "posthoc_pareto_aggregation_gate.json",
        "posthoc_contrast_expansion_gate_sha256": root / "posthoc_contrast_expansion_gate.json",
        "posthoc_family_inference_correction_gate_sha256": (
            root / "posthoc_family_inference_correction_gate.json"
        ),
        "temporal_gate_binding_audit_sha256": (
            PROJECT_ROOT / "release/e31_temporal_gate_binding_audit.json"
        ),
    }.items():
        _expect_hash(path, bindings[key], f"e31-binding:{key}")
        checked += 1
    checked += _verify_e31_runtime_environment(
        root,
        _hash(PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json"),
        _hash(root / "design_manifest.csv"),
    )
    transitive_gate, transitive_checked = _verify_e31_transitive_source_gate(
        root,
        _hash(PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json"),
        _hash(root / "design_manifest.csv"),
    )
    checked += transitive_checked
    pareto_gate, pareto_gate_checked = _verify_e31_pareto_aggregation_gate(
        root,
        _hash(PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json"),
        _hash(root / "design_manifest.csv"),
    )
    checked += pareto_gate_checked
    contrast_gate, contrast_gate_checked = _verify_e31_contrast_expansion_gate(
        root,
        _hash(PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json"),
        _hash(root / "design_manifest.csv"),
    )
    checked += contrast_gate_checked
    try:
        completion_created = datetime.fromisoformat(str(completion.get("created_utc", "")))
        limitation_gate_created = max(
            datetime.fromisoformat(str(pareto_gate["created_utc"])),
            datetime.fromisoformat(str(contrast_gate["created_utc"])),
            datetime.fromisoformat(str(transitive_gate["created_utc"])),
        )
    except (KeyError, ValueError) as error:
        raise RuntimeError("E31 completion or limitation-gate timestamp is invalid") from error
    if completion_created <= limitation_gate_created:
        raise RuntimeError("E31 completion predates a bound post-hoc limitation gate")
    method_gate_path = root / "preanalysis_method_erratum_gate.json"
    method_gate = json.loads(method_gate_path.read_text(encoding="utf-8"))
    method_boundary = method_gate.get("checkpoint_boundary", {})
    method_rows = method_boundary.get("committed_rows")
    if (method_gate.get("status")
            != "PREANALYSIS_MATHEMATICAL_ERRATUM_FROZEN_BEFORE_AGGREGATE_EFFECT_ANALYSIS"
            or method_gate.get("created_date") != "2026-08-24"
            or not isinstance(method_rows, int) or not 0 < method_rows < 28152
            or method_boundary.get("max_run_order") != method_rows - 1
            or method_boundary.get("inspected_aggregate_fields")
            != ["status", "run_order", "committed_utc"]
            or method_boundary.get("primary_contrast_computed_before_erratum") is not False
            or method_gate.get("changes_to_frozen_execution") is not False
            or method_gate.get("invalid_inference_removed")
            != "family-restricted artificial-sign randomization p-value"
            or method_gate.get("replacement")
            != "exact finite-population contrast plus explicitly non-design-based stratified stability interval"
            or method_gate.get("unmeasured_secondary_outcomes")
            != ["time_to_first_valid_seconds", "time_to_best_seconds"]
            or method_gate.get("erratum_path")
            != "docs/review/e31_preanalysis_method_erratum_2026-08-24.md"
            or method_gate.get("protocol_sha256") != _hash(
                PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json"
            )
            or method_gate.get("design_manifest_sha256") != _hash(root / "design_manifest.csv")):
        raise RuntimeError("E31 pre-analysis method erratum gate is incomplete or inconsistent")
    erratum_path = PROJECT_ROOT / str(method_gate.get("erratum_path", ""))
    _expect_hash(erratum_path, method_gate.get("erratum_sha256", ""), "e31-method-erratum")
    checked += 1
    host_gate_path = root / "host_environment_limitation_gate.json"
    host_gate = json.loads(host_gate_path.read_text(encoding="utf-8"))
    host_disclosure = PROJECT_ROOT / str(host_gate.get("disclosure_path", ""))
    if (host_gate.get("status") != "PREANALYSIS_HOST_LIMITATION_FROZEN"
            or host_gate.get("aggregate_treatment_effects_inspected") is not False
            or host_gate.get("row_exclusion_or_rerun_authorized") is not False
            or host_gate.get("continuous_host_exclusivity_verified") is not False
            or host_gate.get("continuous_host_telemetry_recorded") is not False
            or host_gate.get("protocol_sha256") != _hash(
                PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json"
            )
            or host_gate.get("design_manifest_sha256") != _hash(root / "design_manifest.csv")
            or host_gate.get("material_drift_thresholds") != {
                "quality_itt": 1.0, "valid": 0.05, "timeout": 0.05,
                "wall_budget_fraction": 0.05, "peak_rss_mb": 128.0,
            }
            or host_gate.get("temporal_blocks") != 20
            or host_gate.get("disclosure_path")
            != "docs/review/e31_host_environment_limitation_2026-08-24.md"
            or host_gate.get("interpretation")
            != "Thresholds were frozen before formal aggregate treatment analysis; the diagnostic can reveal temporal drift but cannot prove its absence."
            or host_gate.get("checkpoint_boundary", {}).get("rows", 28152) >= 28152
            or host_gate.get("checkpoint_boundary", {}).get("max_run_order")
            != host_gate.get("checkpoint_boundary", {}).get("rows", 0) - 1):
        raise RuntimeError("E31 host limitation was not frozen before aggregate analysis")
    _expect_hash(host_disclosure, host_gate["disclosure_sha256"], "e31-host-disclosure")
    checked += 1
    results = pd.read_csv(final / "formal_results.csv")
    design = pd.read_csv(root / "design_manifest.csv").sort_values(
        "run_order", kind="stable"
    ).reset_index(drop=True)
    if len(results) != 28152 or results["run_order"].tolist() != list(range(28152)):
        raise RuntimeError("E31 sealed result schedule is incomplete or noncontiguous")
    host_boundary_rows = int(host_gate["checkpoint_boundary"]["rows"])
    boundary_status_counts = {
        str(key): int(value) for key, value in results.iloc[:host_boundary_rows]["status"]
        .astype(str).value_counts().items()
    }
    if host_gate["checkpoint_boundary"].get("status_counts_only") != boundary_status_counts:
        raise RuntimeError("E31 host limitation checkpoint counts differ from sealed rows")
    transitive_boundary = transitive_gate["checkpoint_boundary"]
    transitive_rows = int(transitive_boundary["committed_rows"])
    transitive_status_counts = {
        str(key): int(value) for key, value in results.iloc[:transitive_rows]["status"]
        .astype(str).value_counts().items()
    }
    if transitive_boundary.get("status_counts_only") != transitive_status_counts:
        raise RuntimeError("E31 transitive-source checkpoint counts differ from sealed rows")
    pareto_boundary = pareto_gate["checkpoint_boundary"]
    pareto_rows = int(pareto_boundary["committed_rows"])
    pareto_status_counts = {
        str(key): int(value) for key, value in results.iloc[:pareto_rows]["status"]
        .astype(str).value_counts().items()
    }
    if pareto_boundary.get("status_counts_only") != pareto_status_counts:
        raise RuntimeError("E31 Pareto aggregation checkpoint counts differ from sealed rows")
    contrast_boundary = contrast_gate["checkpoint_boundary"]
    contrast_rows = int(contrast_boundary["committed_rows"])
    contrast_status_counts = {
        str(key): int(value) for key, value in results.iloc[:contrast_rows]["status"]
        .astype(str).value_counts().items()
    }
    if contrast_boundary.get("status_counts_only") != contrast_status_counts:
        raise RuntimeError("E31 contrast-expansion checkpoint counts differ from sealed rows")
    with sqlite3.connect(
        f"file:{(final / 'checkpoint_final.sqlite3').resolve()}?mode=ro", uri=True, timeout=30,
    ) as connection:
        method_timestamp = connection.execute(
            "SELECT committed_utc FROM results WHERE run_order = ?", (method_rows - 1,)
        ).fetchone()
        transitive_timestamp = connection.execute(
            "SELECT committed_utc FROM results WHERE run_order = ?", (transitive_rows - 1,)
        ).fetchone()
        pareto_timestamp = connection.execute(
            "SELECT committed_utc FROM results WHERE run_order = ?", (pareto_rows - 1,)
        ).fetchone()
        contrast_timestamp = connection.execute(
            "SELECT committed_utc FROM results WHERE run_order = ?", (contrast_rows - 1,)
        ).fetchone()
        first_timestamp = connection.execute(
            "SELECT committed_utc FROM results WHERE run_order = 0"
        ).fetchone()
    if (method_timestamp is None
            or method_boundary.get("last_committed_utc") != str(method_timestamp[0])):
        raise RuntimeError("E31 method erratum checkpoint timestamp differs from sealed rows")
    if (transitive_timestamp is None or first_timestamp is None
            or transitive_boundary.get("last_committed_utc") != str(transitive_timestamp[0])
            or transitive_boundary.get("first_committed_utc") != str(first_timestamp[0])):
        raise RuntimeError(
            "E31 transitive-source checkpoint timestamps differ from sealed rows"
        )
    if (pareto_timestamp is None or first_timestamp is None
            or pareto_boundary.get("last_committed_utc") != str(pareto_timestamp[0])
            or pareto_boundary.get("first_committed_utc") != str(first_timestamp[0])):
        raise RuntimeError(
            "E31 Pareto aggregation checkpoint timestamps differ from sealed rows"
        )
    if (contrast_timestamp is None or first_timestamp is None
            or contrast_boundary.get("last_committed_utc") != str(contrast_timestamp[0])
            or contrast_boundary.get("first_committed_utc") != str(first_timestamp[0])):
        raise RuntimeError(
            "E31 contrast-expansion checkpoint timestamps differ from sealed rows"
        )
    if results["run_id"].duplicated().any() or design["run_id"].duplicated().any():
        raise RuntimeError("E31 sealed results or frozen design contain duplicate run IDs")
    if (design["input_circuit_sha256"].nunique() != 391
            or design["circuit_family"].nunique() != 15):
        raise RuntimeError("E31 frozen design cardinalities do not match the completion manifest")
    if list(zip(results["run_id"].astype(str), results["run_order"].astype(int))) != list(
        zip(design["run_id"].astype(str), design["run_order"].astype(int))
    ):
        raise RuntimeError("E31 sealed result identities differ from the frozen design")
    factors = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    metadata_columns = [
        "input_circuit_sha256", "circuit_id", "circuit_family", *factors,
        "primary_pair_orientation",
    ]
    required_result_columns = {
        "run_id", "run_order", "protocol_sha256", "design_manifest_sha256", "status",
        "valid_equivalent_output", "exact_fidelity", "output_circuit_sha256",
        "original_common_basis_gate_count", "optimized_common_basis_gate_count",
        "common_basis_gate_reduction_pct", "wall_seconds_end_to_end", "peak_rss_mb",
        *metadata_columns,
    }
    missing_result_columns = required_result_columns.difference(results.columns)
    if missing_result_columns:
        raise RuntimeError(
            f"E31 sealed result schema is incomplete: {sorted(missing_result_columns)}"
        )
    for column in metadata_columns:
        if column not in design or not results[column].astype(str).equals(design[column].astype(str)):
            raise RuntimeError(f"E31 sealed result metadata differs from design: {column}")
    protocol_path = PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json"
    design_path = root / "design_manifest.csv"
    protocol_sha = _hash(protocol_path)
    design_sha = _hash(design_path)
    if (results["protocol_sha256"].astype(str).nunique() != 1
            or results["protocol_sha256"].astype(str).iloc[0] != protocol_sha
            or results["design_manifest_sha256"].astype(str).nunique() != 1
            or results["design_manifest_sha256"].astype(str).iloc[0] != design_sha):
        raise RuntimeError("E31 sealed rows are not bound to the frozen protocol and design")
    allowed_status = {"success", "timeout", "error", "invalid", "unavailable", "oom"}
    statuses = results["status"].astype(str)
    if not set(statuses).issubset(allowed_status) or len(statuses) != 28152:
        raise RuntimeError("E31 status accounting does not cover the full ITT denominator")
    valid = _strict_bool_series(
        results["valid_equivalent_output"], label="E31 sealed valid_equivalent_output"
    )
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    fidelity = pd.to_numeric(results["exact_fidelity"], errors="coerce")
    threshold = float(protocol["semantic_contract"]["fidelity_threshold"])
    output_hashes = results["output_circuit_sha256"].fillna("").astype(str)
    if (valid & statuses.ne("success")).any():
        raise RuntimeError("E31 marks a non-success row as semantically valid")
    if (statuses.eq("success") & ~valid).any():
        raise RuntimeError("E31 marks a successful row as semantically invalid")
    if (valid & (
            fidelity.isna() | ~np.isfinite(fidelity) | fidelity.lt(threshold)
            | fidelity.gt(1.0 + 1e-12)
    )).any():
        raise RuntimeError("E31 valid row lacks fidelity at the frozen threshold")
    if (valid & ~output_hashes.map(lambda value: bool(re.fullmatch(r"[0-9a-f]{64}", value)))).any():
        raise RuntimeError("E31 valid row lacks a canonical output SHA-256")
    original_count = pd.to_numeric(
        results["original_common_basis_gate_count"], errors="coerce"
    )
    optimized_count = pd.to_numeric(
        results["optimized_common_basis_gate_count"], errors="coerce"
    )
    success = statuses.eq("success")
    if (success & (
            original_count.isna() | optimized_count.isna()
            | original_count.lt(0) | optimized_count.lt(0)
            | original_count.mod(1).ne(0) | optimized_count.mod(1).ne(0)
    )).any():
        raise RuntimeError("E31 successful row lacks valid common-basis gate counts")
    if (success & original_count.eq(0) & optimized_count.ne(0)).any():
        raise RuntimeError("E31 zero original gate count has a nonzero optimized count")
    expected_reduction = pd.Series(np.nan, index=results.index, dtype=float)
    positive_original = success & original_count.gt(0)
    expected_reduction.loc[positive_original] = 100.0 * (
        1.0 - optimized_count.loc[positive_original] / original_count.loc[positive_original]
    )
    both_zero = success & original_count.eq(0) & optimized_count.eq(0)
    expected_reduction.loc[both_zero] = 0.0
    observed_reduction = pd.to_numeric(
        results["common_basis_gate_reduction_pct"], errors="coerce"
    )
    if (success & ~np.isclose(
            observed_reduction, expected_reduction, rtol=0.0, atol=1e-12,
            equal_nan=False,
    )).any():
        raise RuntimeError("E31 common-basis reduction differs from sealed gate counts")
    numeric_columns = [
        "common_basis_gate_reduction_pct", "wall_seconds_end_to_end", "peak_rss_mb"
    ]
    if any(
        not math.isfinite(float(value))
        for column in numeric_columns
        for value in results[column]
    ):
        raise RuntimeError("E31 sealed primary/resource values contain non-finite values")
    wall = pd.to_numeric(results["wall_seconds_end_to_end"], errors="raise")
    peak = pd.to_numeric(results["peak_rss_mb"], errors="raise")
    budget = pd.to_numeric(results["budget_seconds"], errors="raise")
    if (wall.lt(0).any() or peak.lt(0).any()
            or (success & wall.gt(
                budget + float(protocol["resource_contract"]["timeout_grace_seconds"])
            )).any()
            or (success & peak.gt(
                float(protocol["resource_contract"]["memory_budget_mb_per_worker"])
            )).any()):
        raise RuntimeError("E31 sealed rows violate the frozen resource contract")
    observed_status_counts = {
        str(key): int(value) for key, value in statuses.value_counts().items()
    }
    if observed_status_counts != completion.get("status_counts"):
        raise RuntimeError("E31 completion status counts differ from the sealed CSV")
    _verify_e31_snapshot(
        final / "checkpoint_final.sqlite3", results, design, completion,
    )
    checked += _verify_e31_semantic_replay(root, results, completion)
    checked += _verify_e31_family_inference(root, results, protocol, completion)
    analysis = json.loads((analysis_dir / "analysis_gate_audit.json").read_text(
        encoding="utf-8"
    ))
    primary = analysis.get("dual_estimand_primary", {}).get("fixed_benchmark_A", {})
    generalized = analysis.get("dual_estimand_primary", {}).get("new_family_generalized_B", {})
    if (analysis.get("result_rows") != 28152 or analysis.get("formal_requested") is not True
            or primary.get("n_input_hashes") != 391
            or primary.get("design_based_p_value", "missing") is not None
            or primary.get("design_based_confidence_interval", "missing") is not None
            or generalized.get("confirmatory_claim_allowed") is not False
            or analysis.get("pareto_inference_role")
            != "EXPLORATORY_POSTHOC_AGGREGATION"):
        raise RuntimeError("E31 formal analysis gate violates the pre-analysis correction")
    alpha = float(protocol["analysis_contract"]["alpha_two_sided"])
    mcid = float(protocol["power_gate"]["mcid_pp"])
    bootstrap_replicates = int(protocol["analysis_contract"]["bootstrap_replicates"])
    bootstrap_seed = int(protocol["analysis_contract"]["bootstrap_seed"])
    recomputed_primary = _recompute_e31_primary_estimand(
        results,
        alpha=alpha,
        bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed,
    )

    def close(left: object, right: float) -> bool:
        try:
            return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
        except (TypeError, ValueError):
            return False

    dual = analysis.get("dual_estimand_primary", {})
    if (dual.get("primary_contrast") != "grid-averaged listing-by-rule-set interaction"
            or primary.get("population") != "frozen unique input hashes"
            or primary.get("estimand_type") != "exact finite-population contrast"
            or primary.get("design_based_inference_status")
            != "NOT_IDENTIFIED_NO_TREATMENT_RANDOMIZATION"
            or primary.get("stability_interval_role")
            != "EMPIRICAL_SENSITIVITY_NOT_DESIGN_BASED_CI"
            or primary.get("bootstrap_replicates") != bootstrap_replicates
            or primary.get("bootstrap_seed") != bootstrap_seed
            or generalized.get("population") != "potentially unseen families"
            or generalized.get("inference_role")
            != "SUPPORTIVE_MODEL_BASED_EXTRAPOLATION_NO_CONFIRMATORY_CLAIM"):
        raise RuntimeError("E31 primary estimand semantics differ from the frozen analysis contract")
    observed_bootstrap = primary.get("stratified_input_bootstrap_stability_interval", [])
    if (len(observed_bootstrap) != 2 or any(
        not close(value, expected)
        for value, expected in zip(observed_bootstrap, recomputed_primary["bootstrap_interval"])
    )):
        raise RuntimeError("E31 bootstrap stability interval differs from sealed rows")
    if (primary.get("families_as_fixed_blocks") != recomputed_primary["families"]
            or not close(primary.get("estimate_pp"), recomputed_primary["estimate_a"])
            or not close(primary.get("mcid_pp"), mcid)
            or not close(
                primary.get("distance_from_mcid_pp"),
                float(recomputed_primary["estimate_a"]) - mcid,
            )
            or primary.get("meets_or_exceeds_mcid") is not (
                float(recomputed_primary["estimate_a"]) >= mcid
            )
            or primary.get("worst_family") != recomputed_primary["worst_family"]
            or not close(
                primary.get("worst_family_estimate_pp"),
                float(recomputed_primary["worst_family_estimate"]),
            )
            or primary.get("lofo_sign_stable") is not recomputed_primary["lofo_sign_stable"]):
        raise RuntimeError("E31 fixed-benchmark primary summary differs from sealed rows")
    for field, expected in (
        ("family_means_pp", recomputed_primary["family_means"]),
        ("leave_one_family_out_estimates_pp", recomputed_primary["lofo"]),
        ("input_quantiles_pp", recomputed_primary["quantiles"]),
    ):
        observed = primary.get(field, {})
        if set(observed) != set(expected) or any(
            not close(observed[key], float(value)) for key, value in expected.items()
        ):
            raise RuntimeError(f"E31 fixed-benchmark field differs from sealed rows: {field}")
    expected_ci = recomputed_primary["ci_b"]
    observed_ci = generalized.get("ci", [])
    if (generalized.get("n_independent_family_clusters") != recomputed_primary["families"]
            or generalized.get("probability_sample_of_families") is not False
            or not close(generalized.get("estimate_pp"), recomputed_primary["estimate_b"])
            or not close(generalized.get("family_cluster_se_pp"), recomputed_primary["se_b"])
            or len(observed_ci) != 2
            or any(not close(value, expected) for value, expected in zip(observed_ci, expected_ci))):
        raise RuntimeError("E31 supportive new-family summary differs from sealed rows")
    recomputed_coefficients, recomputed_diagnostics = _recompute_e31_factorial_model(results)
    observed_coefficients = pd.read_csv(
        analysis_dir / "full_factorial_model_coefficients.csv"
    )
    if (set(observed_coefficients.columns) != set(recomputed_coefficients.columns)
            or len(observed_coefficients) != 71):
        raise RuntimeError("E31 factorial coefficient table has an invalid schema or row count")
    observed_coefficients = observed_coefficients.sort_values(
        "coefficient", kind="stable"
    ).reset_index(drop=True)
    recomputed_coefficients = recomputed_coefficients.sort_values(
        "coefficient", kind="stable"
    ).reset_index(drop=True)
    for column in (
        "coefficient", "interaction_order", "inference_role", "confirmatory_primary_contrast",
    ):
        if column == "confirmatory_primary_contrast":
            observed_values = _strict_bool_series(
                observed_coefficients[column],
                label="E31 factorial confirmatory_primary_contrast",
            )
            matches = observed_values.equals(recomputed_coefficients[column].astype(bool))
        else:
            matches = observed_coefficients[column].astype(str).equals(
                recomputed_coefficients[column].astype(str)
            )
        if not matches:
            raise RuntimeError(f"E31 factorial coefficient metadata differs: {column}")
    for column in (
        "estimate_pp", "cluster_robust_se_pp", "ci95_low_pp", "ci95_high_pp",
        "p_value_model_based", "holm_adjusted_p_within_role",
    ):
        observed_values = pd.to_numeric(observed_coefficients[column], errors="coerce").to_numpy()
        expected_values = pd.to_numeric(recomputed_coefficients[column], errors="coerce").to_numpy()
        if not np.allclose(
            observed_values, expected_values, rtol=5e-8, atol=1e-10, equal_nan=True,
        ):
            raise RuntimeError(f"E31 factorial coefficient differs from sealed rows: {column}")
    recomputed_marginal = _recompute_e31_posthoc_marginal_contrasts(results).sort_values(
        "coefficient", kind="stable"
    ).reset_index(drop=True)
    observed_marginal = pd.read_csv(
        analysis_dir / "posthoc_marginal_contrasts.csv"
    ).sort_values("coefficient", kind="stable").reset_index(drop=True)
    if (set(observed_marginal.columns) != set(recomputed_marginal.columns)
            or len(observed_marginal) != 30):
        raise RuntimeError("E31 post-hoc marginal table has an invalid schema or row count")
    for column in (
        "coefficient", "interaction_order", "inference_role", "confirmatory_primary_contrast",
        "multiplicity_family_id", "multiplicity_family_size",
    ):
        if column == "confirmatory_primary_contrast":
            observed_values = _strict_bool_series(
                observed_marginal[column],
                label="E31 post-hoc marginal confirmatory_primary_contrast",
            )
            matches = observed_values.equals(recomputed_marginal[column].astype(bool))
        else:
            matches = observed_marginal[column].astype(str).equals(
                recomputed_marginal[column].astype(str)
            )
        if not matches:
            raise RuntimeError(f"E31 post-hoc marginal metadata differs: {column}")
    for column in (
        "estimate_pp", "cluster_robust_se_pp", "ci95_low_pp", "ci95_high_pp",
        "p_value_model_based", "holm_adjusted_p_within_role",
    ):
        observed_values = pd.to_numeric(observed_marginal[column], errors="coerce").to_numpy()
        expected_values = pd.to_numeric(recomputed_marginal[column], errors="coerce").to_numpy()
        if not np.allclose(
            observed_values, expected_values, rtol=5e-8, atol=1e-10, equal_nan=True,
        ):
            raise RuntimeError(f"E31 post-hoc marginal contrast differs from sealed rows: {column}")
    observed_diagnostics = json.loads(
        (analysis_dir / "full_factorial_model_diagnostics.json").read_text(encoding="utf-8")
    )
    def model_close(left: object, right: float) -> bool:
        try:
            return math.isclose(float(left), float(right), rel_tol=5e-8, abs_tol=1e-10)
        except (TypeError, ValueError):
            return False
    exact_diagnostic_fields = (
        "formula", "response", "covariance", "n_rows", "n_input_clusters",
        "n_outer_families_not_used_as_input_df", "design_matrix_rank",
        "design_matrix_columns", "p_value_interpretation",
        "treatment_parameter_interpretation", "posthoc_marginal_contrast_file",
    )
    if any(
        observed_diagnostics.get(field) != recomputed_diagnostics[field]
        for field in exact_diagnostic_fields
    ):
        raise RuntimeError("E31 factorial model diagnostics differ from sealed rows")
    for field in ("condition_number", "zero_inflated_response_rate"):
        if not model_close(observed_diagnostics.get(field), recomputed_diagnostics[field]):
            raise RuntimeError(f"E31 factorial diagnostic differs from sealed rows: {field}")
    observed_quantiles = observed_diagnostics.get("residual_quantiles", {})
    expected_quantiles = recomputed_diagnostics["residual_quantiles"]
    if set(observed_quantiles) != set(expected_quantiles) or any(
        not model_close(observed_quantiles[key], value)
        for key, value in expected_quantiles.items()
    ):
        raise RuntimeError("E31 factorial residual diagnostics differ from sealed rows")
    if analysis.get("factorial_model") != observed_diagnostics:
        raise RuntimeError("E31 analysis gate and factorial diagnostics are inconsistent")
    factor_columns = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    recomputed_pareto = _recompute_e31_pareto_summary(results).sort_values(
        factor_columns, kind="stable"
    ).reset_index(drop=True)
    observed_pareto = pd.read_csv(
        analysis_dir / "equal_budget_pareto_summary.csv"
    ).sort_values(factor_columns, kind="stable").reset_index(drop=True)
    if set(observed_pareto.columns) != set(recomputed_pareto.columns) or len(observed_pareto) != 72:
        raise RuntimeError("E31 Pareto table has an invalid schema or cell count")
    exact_pareto_columns = {
        *factor_columns, "n_scheduled", "n_unique_inputs", "pareto_nondominated",
        "dominates_n", "dominated_by_n",
    }
    for column in recomputed_pareto.columns:
        if column in exact_pareto_columns:
            if column == "pareto_nondominated":
                observed_values = _strict_bool_series(
                    observed_pareto[column], label="E31 Pareto pareto_nondominated"
                )
                matches = observed_values.equals(recomputed_pareto[column].astype(bool))
            else:
                matches = observed_pareto[column].astype(str).equals(
                    recomputed_pareto[column].astype(str)
                )
        else:
            difference = (
                pd.to_numeric(observed_pareto[column], errors="raise")
                - pd.to_numeric(recomputed_pareto[column], errors="raise")
            ).abs()
            matches = bool(difference.le(1e-12).all())
        if not matches:
            raise RuntimeError(f"E31 Pareto table differs from sealed rows: {column}")
    sensitivity_keys = [
        "wall_aggregation", "memory_aggregation", *factor_columns,
    ]
    recomputed_sensitivity = _recompute_e31_pareto_aggregation_sensitivity(
        results
    ).sort_values(sensitivity_keys, kind="stable").reset_index(drop=True)
    observed_sensitivity = pd.read_csv(
        analysis_dir / "pareto_aggregation_sensitivity.csv"
    ).sort_values(sensitivity_keys, kind="stable").reset_index(drop=True)
    if (set(observed_sensitivity.columns) != set(recomputed_sensitivity.columns)
            or len(observed_sensitivity) != 288
            or observed_sensitivity.groupby(
                ["wall_aggregation", "memory_aggregation"], sort=True
            ).size().tolist() != [72, 72, 72, 72]):
        raise RuntimeError("E31 Pareto aggregation sensitivity has invalid coverage")
    exact_sensitivity_columns = {
        *factor_columns, "wall_aggregation", "memory_aggregation",
        "n_scheduled", "n_unique_inputs", "pareto_nondominated",
        "dominates_n", "dominated_by_n",
    }
    for column in recomputed_sensitivity.columns:
        if column == "pareto_nondominated":
            matches = _strict_bool_series(
                observed_sensitivity[column],
                label="E31 Pareto sensitivity pareto_nondominated",
            ).equals(recomputed_sensitivity[column].astype(bool))
        elif column in exact_sensitivity_columns:
            matches = observed_sensitivity[column].astype(str).equals(
                recomputed_sensitivity[column].astype(str)
            )
        else:
            observed_values = pd.to_numeric(
                observed_sensitivity[column], errors="raise"
            ).to_numpy(float)
            expected_values = pd.to_numeric(
                recomputed_sensitivity[column], errors="raise"
            ).to_numpy(float)
            matches = bool(np.allclose(
                observed_values, expected_values, rtol=1e-12, atol=1e-12,
            ))
        if not matches:
            raise RuntimeError(
                f"E31 Pareto aggregation sensitivity differs from sealed rows: {column}"
            )
    expected_sensitivity_summary = _summarize_e31_pareto_aggregation_sensitivity(
        recomputed_sensitivity
    )
    if analysis.get("pareto_aggregation_sensitivity") != expected_sensitivity_summary:
        raise RuntimeError(
            "E31 Pareto aggregation-invariance claim gate differs from sealed rows"
        )
    if (completion.get("pareto_frontier_membership_agreement_all_schemes")
            is not expected_sensitivity_summary["frontier_membership_agreement_all_schemes"]
            or completion.get("pareto_aggregation_invariant_claim_allowed")
            is not expected_sensitivity_summary[
                "bounded_aggregation_invariant_frontier_claim_allowed"
            ]
            or completion.get("pareto_aggregation_disagreement_cell_count")
            != expected_sensitivity_summary["disagreement_cell_count"]):
        raise RuntimeError("E31 completion Pareto claim gate differs from sealed rows")
    recomputed_hypervolume = _recompute_e31_hypervolume(recomputed_pareto)
    hypervolume = json.loads((analysis_dir / "pareto_hypervolume_audit.json").read_text(
        encoding="utf-8"
    ))
    observed_ranges = hypervolume.get("objective_ranges", {})
    expected_ranges = recomputed_hypervolume["objective_ranges"]
    ranges_match = (
        isinstance(observed_ranges, dict)
        and set(observed_ranges) == set(expected_ranges)
        and all(
            observed_ranges[name].get("direction") == expected["direction"]
            and close(observed_ranges[name].get("observed_min"), expected["observed_min"])
            and close(observed_ranges[name].get("observed_max"), expected["observed_max"])
            for name, expected in expected_ranges.items()
        )
    )
    if (hypervolume.get("method") != recomputed_hypervolume["method"]
            or hypervolume.get("normalization") != recomputed_hypervolume["normalization"]
            or hypervolume.get("draws") != recomputed_hypervolume["draws"]
            or hypervolume.get("seed") != recomputed_hypervolume["seed"]
            or hypervolume.get("pareto_points") != recomputed_hypervolume["pareto_points"]
            or hypervolume.get("independent_objectives")
            != recomputed_hypervolume["independent_objectives"]
            or not close(hypervolume.get("hypervolume"), recomputed_hypervolume["hypervolume"])
            or not close(
                hypervolume.get("monte_carlo_standard_error"),
                recomputed_hypervolume["monte_carlo_standard_error"],
            )
            or not ranges_match
            or hypervolume.get("deduplicated_protocol_objective", {}).get("removed")
            != "failure_rate"):
        raise RuntimeError("E31 hypervolume audit differs from the independently rebuilt frontier")
    if analysis.get("pareto_hypervolume") != hypervolume:
        raise RuntimeError("E31 analysis gate and hypervolume audit are inconsistent")
    availability = analysis.get("secondary_outcome_availability", {})
    for name in ("time_to_first_valid_seconds", "time_to_best_seconds"):
        if availability.get(name, {}).get("status") != "NOT_MEASURED_IN_FROZEN_RUN":
            raise RuntimeError(f"E31 unmeasured secondary was not disclosed: {name}")
    host_audit = json.loads((analysis_dir / "host_environment_audit.json").read_text(
        encoding="utf-8"
    ))
    if (host_audit.get("status") != "OBSERVATIONAL_TEMPORAL_SENSITIVITY_ONLY"
            or host_audit.get("continuous_host_exclusivity_verified") is not False
            or host_audit.get("continuous_host_telemetry_recorded") is not False
            or host_audit.get("material_drift_thresholds") != {
                "quality_itt": 1.0, "valid": 0.05, "timeout": 0.05,
                "wall_budget_fraction": 0.05, "peak_rss_mb": 128.0,
            }
            or host_audit.get("material_drift_screen_decision") not in {
                "REVIEW_REQUIRED", "NO_THRESHOLD_EXCEEDED",
            }):
        raise RuntimeError("E31 host-environment limitation was not preserved")
    temporal = pd.read_csv(analysis_dir / "run_order_temporal_diagnostics.csv")
    expected_temporal_columns = {"temporal_block", "rows", "run_order_min", "run_order_max"}
    for outcome in (
        "quality_itt", "valid", "timeout", "wall_seconds",
        "wall_budget_fraction", "peak_rss_mb",
    ):
        expected_temporal_columns.update({
            f"{outcome}_raw_mean", f"{outcome}_adjusted_residual_mean",
            f"{outcome}_adjusted_residual_sem",
        })
    if (len(temporal) != 20 or int(temporal["rows"].sum()) != 28152
            or not expected_temporal_columns.issubset(temporal.columns)):
        raise RuntimeError("E31 temporal diagnostics do not cover the formal ITT denominator")
    temporal = temporal.sort_values("temporal_block", kind="stable").reset_index(drop=True)
    rebuilt_temporal = _recompute_e31_temporal_diagnostics(results)
    for column in sorted(expected_temporal_columns):
        observed = pd.to_numeric(temporal[column], errors="raise")
        rebuilt = pd.to_numeric(rebuilt_temporal[column], errors="raise")
        if column in {"temporal_block", "rows", "run_order_min", "run_order_max"}:
            matches = observed.astype(int).equals(rebuilt.astype(int))
        else:
            matches = bool(((observed - rebuilt).abs() <= 1e-12).all())
        if not matches:
            raise RuntimeError(f"E31 temporal diagnostic differs from sealed results: {column}")
    if temporal["temporal_block"].astype(int).tolist() != list(range(20)):
        raise RuntimeError("E31 temporal diagnostics have missing or duplicate block identities")
    starts = temporal["run_order_min"].astype(int).tolist()
    ends = temporal["run_order_max"].astype(int).tolist()
    sizes = temporal["rows"].astype(int).tolist()
    if (starts[0] != 0 or ends[-1] != 28151
            or any(end - start + 1 != size for start, end, size in zip(starts, ends, sizes))
            or any(starts[index] != ends[index - 1] + 1 for index in range(1, 20))):
        raise RuntimeError("E31 temporal blocks are not a contiguous partition of run_order")
    numeric_columns = sorted(expected_temporal_columns - {"temporal_block", "rows"})
    if any(
        not math.isfinite(float(value))
        for column in numeric_columns
        for value in temporal[column]
    ):
        raise RuntimeError("E31 temporal diagnostics contain non-finite values")
    thresholds = host_audit["material_drift_thresholds"]
    recomputed_exceeded = {
        outcome: bool(
            temporal[f"{outcome}_adjusted_residual_mean"].astype(float).abs().max()
            > float(threshold)
        )
        for outcome, threshold in thresholds.items()
    }
    expected_decision = (
        "REVIEW_REQUIRED" if any(recomputed_exceeded.values()) else "NO_THRESHOLD_EXCEEDED"
    )
    if (host_audit.get("blocks") != 20 or host_audit.get("rows") != 28152
            or host_audit.get("material_drift_threshold_exceeded") != recomputed_exceeded
            or host_audit.get("material_drift_screen_decision") != expected_decision):
        raise RuntimeError("E31 host drift decision does not match the temporal source data")
    outcome_names = (
        "quality_itt", "valid", "timeout", "wall_seconds",
        "wall_budget_fraction", "peak_rss_mb",
    )
    outcome_audit = host_audit.get("outcomes", {})
    if set(outcome_audit) != set(outcome_names):
        raise RuntimeError("E31 host audit outcome inventory is incomplete")
    for outcome in outcome_names:
        values = temporal[f"{outcome}_adjusted_residual_mean"].astype(float)
        recorded = outcome_audit.get(outcome, {})
        expected_max = float(values.abs().max())
        expected_delta = float(values.iloc[-1] - values.iloc[0])
        try:
            recorded_max = float(recorded["max_absolute_block_adjusted_residual_mean"])
            recorded_delta = float(recorded["last_minus_first_adjusted_residual_mean"])
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(f"E31 host audit outcome is malformed: {outcome}") from error
        if (not math.isclose(
                recorded_max,
                expected_max, rel_tol=1e-12, abs_tol=1e-12,
            ) or not math.isclose(
                recorded_delta,
                expected_delta, rel_tol=1e-12, abs_tol=1e-12,
            )):
            raise RuntimeError(f"E31 host audit outcome does not match temporal data: {outcome}")
    return checked + 5


def _verify_e31_independent_receipt(
    receipt_path: Path | None = None,
) -> int:
    """Validate the durable receipt without treating it as proof by assertion."""
    path = receipt_path or (
        PROJECT_ROOT / "release/e31_independent_release_verification_receipt.json"
    )
    receipt = json.loads(path.read_text(encoding="utf-8"))
    expected_scalars = {
        "schema_version": "1.0.0",
        "status": "PASS_E31_INDEPENDENT_RELEASE_VERIFICATION",
        "formal_rows": 28_152,
        "success_rows_semantically_replayed": 20_314,
        "unique_semantic_cells_replayed": 6_858,
        "outer_inference_cluster": "circuit_family",
        "n_independent_family_clusters": 15,
        "family_cluster_degrees_of_freedom": 14,
        "legacy_input_cluster_inference_valid": False,
        "unseen_family_generalization_status": "BLOCKED",
        "source_provenance_rating": "PARTIAL",
        "temporal_gate_provenance_rating": "PARTIAL",
    }
    for field, expected in expected_scalars.items():
        if receipt.get(field) != expected:
            raise RuntimeError(f"E31 independent receipt field mismatch: {field}")
    if int(receipt.get("checked_artifact_count", -1)) < 34_000:
        raise RuntimeError("E31 independent receipt has incomplete artifact coverage")
    identity = str(receipt.get("semantic_identity_check", "")).lower()
    if not all(term in identity for term in ("phase-aligned", "identity norm", "fidelity")):
        raise RuntimeError("E31 independent receipt lacks the exact semantic identity contract")

    artifacts = receipt.get("artifacts")
    required_artifacts = {
        "formal_completion_manifest",
        "formal_results",
        "analysis_gate",
        "family_inference_correction_audit",
        "semantic_replay_gate",
        "semantic_replay_manifest",
        "temporal_gate_binding_audit",
        "independent_verifier_source",
    }
    if not isinstance(artifacts, dict) or set(artifacts) != required_artifacts:
        raise RuntimeError("E31 independent receipt artifact inventory mismatch")
    checked = 0
    for name, record in artifacts.items():
        if not isinstance(record, dict):
            raise RuntimeError(f"E31 independent receipt artifact is malformed: {name}")
        artifact_path = PROJECT_ROOT / str(record.get("path", ""))
        if not artifact_path.is_file():
            raise RuntimeError(f"E31 independent receipt artifact is missing: {name}")
        if (artifact_path.stat().st_size != int(record.get("bytes", -1))
                or _hash(artifact_path) != record.get("sha256")):
            raise RuntimeError(f"E31 independent receipt artifact drift: {name}")
        checked += 1

    completion_path = PROJECT_ROOT / str(
        artifacts["formal_completion_manifest"]["path"]
    )
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    if completion.get("status") != "FORMAL_COMPLETE_PENDING_INDEPENDENT_RELEASE_VERIFICATION":
        raise RuntimeError("E31 independent receipt points to an invalid completion seal")
    try:
        receipt_time = datetime.fromisoformat(str(receipt["created_utc"]))
        completion_time = datetime.fromisoformat(str(completion["created_utc"]))
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("E31 independent receipt timestamps are malformed") from error
    if receipt_time.tzinfo is None or completion_time.tzinfo is None:
        raise RuntimeError("E31 independent receipt timestamps must be timezone-aware")
    if receipt_time < completion_time:
        raise RuntimeError("E31 independent receipt predates the sealed completion manifest")
    return checked + len(expected_scalars) + 4


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path,
                        default=PROJECT_ROOT / "release" / "prepaper_release_manifest.json")
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise RuntimeError("pre-paper manifest does not assert complete status")
    entries = (list(manifest.get("evidence", []))
               + list(manifest.get("project_evidence", []))
               + list(manifest.get("source_files", [])))
    paths = [str(entry["file"]) for entry in entries]
    if len(paths) != len(set(paths)):
        raise RuntimeError("duplicate file path in pre-paper release manifest")
    verified_rows = 0
    numeric_columns = 0
    for entry in entries:
        path = PROJECT_ROOT / str(entry["file"])
        if not path.is_file():
            raise RuntimeError(f"missing pinned file: {entry['file']}")
        if path.stat().st_size != int(entry["bytes"]) or _hash(path) != entry["sha256"]:
            raise RuntimeError(f"byte/hash mismatch: {entry['file']}")
        if path.suffix.lower() == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() == ".csv":
            frame = pd.read_csv(path)
            if len(frame) != int(entry["rows"]) or list(frame.columns) != entry["columns"]:
                raise RuntimeError(f"CSV schema/row mismatch: {entry['file']}")
            numeric = frame.select_dtypes(include="number")
            numeric_columns += len(numeric.columns)
            if numeric.map(lambda value: math.isinf(float(value)) if pd.notna(value) else False).any().any():
                raise RuntimeError(f"numeric infinity in {entry['file']}")
            verified_rows += len(frame)
    expected = manifest.get("counts", {})
    if int(expected.get("evidence_files", -1)) != len(manifest.get("evidence", [])):
        raise RuntimeError("evidence-file count mismatch")
    if int(expected.get("source_files", -1)) != len(manifest.get("source_files", [])):
        raise RuntimeError("source-file count mismatch")
    if int(expected.get("project_evidence_files", -1)) != len(
        manifest.get("project_evidence", [])
    ):
        raise RuntimeError("project-evidence-file count mismatch")
    nested_hashes = _verify_nested_audits()
    external_lineage_hashes = _verify_external_lineage()
    e31_formal_checks = _verify_e31_formal()
    e31_receipt_checks = _verify_e31_independent_receipt()
    from scripts.verify_e31_structural_distribution_metrics import verify as verify_structural
    e31_structural = verify_structural()
    from scripts.verify_metric_audit_ledger import verify as verify_metric_ledger
    metric_ledger = verify_metric_ledger(
        PROJECT_ROOT / "docs/review/metric_audit_ledger_2026-08-24.csv",
        PROJECT_ROOT / "docs/review/metric_audit_summary_2026-08-24.json",
        PROJECT_ROOT / "docs/review/metric_catalog_2026-08-11.md",
    )
    from scripts.audit_direct_dependencies import audit as audit_direct_dependencies
    dependency_audit = audit_direct_dependencies(
        PROJECT_ROOT / "requirements.txt", PROJECT_ROOT
    )
    print(json.dumps({
        "status": "verified", "files": len(entries), "csv_rows": verified_rows,
        "numeric_columns_checked_for_infinity": numeric_columns,
        "nested_audit_hashes_verified": nested_hashes,
        "external_lineage_checks": external_lineage_hashes,
        "e31_formal_checks": e31_formal_checks,
        "e31_independent_receipt_checks": e31_receipt_checks,
        "e31_structural_semantic_cells_recomputed": (
            e31_structural["semantic_cells_recomputed"]
        ),
        "metric_ledger_rows_verified": metric_ledger["rows"],
        "python_files_dependency_audited": dependency_audit["scanned_python_files"],
        "manifest_sha256": _hash(manifest_path),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
