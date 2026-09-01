"""Confirmatory RQ3 analysis for the frozen 520-circuit tool benchmark."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.provenance import file_sha256

KEY = ["circuit_id", "trial", "seed", "input_circuit_sha256"]
TOOLS = ("custom", "qiskit", "cirq", "tket")
BOOTSTRAP_REPLICATES = 10000
BOOTSTRAP_SEED = 20260809
ALPHA = 0.05
TARGET_POWER = 0.80

RESOURCE_COLUMNS = (
    "optimizer_cpu_seconds",
    "optimizer_peak_rss_bytes",
    "parse_elapsed_seconds",
    "input_normalization_elapsed_seconds",
    "verification_elapsed_seconds",
    "output_normalization_elapsed_seconds",
    "result_serialization_elapsed_seconds",
    "pipeline_elapsed_seconds",
    "common_baseline_two_q_depth",
    "common_optimized_two_q_depth",
)


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _as_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().eq("true")


def _holm(values: list[float]) -> list[float]:
    result = [float("nan")] * len(values)
    finite = sorted(((i, float(p)) for i, p in enumerate(values) if np.isfinite(p)),
                    key=lambda pair: pair[1])
    running = 0.0
    for rank, (index, p_value) in enumerate(finite):
        running = max(running, (len(finite) - rank) * p_value)
        result[index] = min(1.0, running)
    return result


def _rank_biserial(differences: np.ndarray) -> float:
    differences = np.asarray(differences, dtype=float)
    differences = differences[np.isfinite(differences) & (differences != 0)]
    if not len(differences):
        return 0.0
    ranks = stats.rankdata(np.abs(differences), method="average")
    positive = float(ranks[differences > 0].sum())
    negative = float(ranks[differences < 0].sum())
    return (positive - negative) / (positive + negative)


def _hodges_lehmann(differences: np.ndarray) -> float:
    values = np.asarray(differences, dtype=float)
    values = values[np.isfinite(values)]
    i, j = np.triu_indices(len(values))
    return float(np.median((values[i] + values[j]) / 2.0))


def _nested_bootstrap(values: pd.DataFrame, value_column: str,
                      replicates: int, seed: int) -> np.ndarray:
    if "input_circuit_sha256" in values.columns:
        values = (values.groupby(
            ["circuit_family", "input_circuit_sha256"], as_index=False
        )[value_column].mean())
    families = np.asarray(sorted(values.circuit_family.unique()), dtype=object)
    groups = {family: values.loc[
        values.circuit_family == family, value_column
    ].to_numpy(float) for family in families}
    rng = np.random.default_rng(seed)
    result = np.empty(replicates, dtype=float)
    for index in range(replicates):
        sampled_families = rng.choice(families, size=len(families), replace=True)
        sampled = [rng.choice(groups[family], size=len(groups[family]), replace=True)
                   for family in sampled_families]
        result[index] = float(np.mean(np.concatenate(sampled)))
    return result


def _cluster_permutation(differences: pd.DataFrame, replicates: int,
                         seed: int) -> float:
    if "input_circuit_sha256" in differences.columns:
        differences = (differences.groupby(
            ["circuit_family", "input_circuit_sha256"], as_index=False
        )["difference"].mean())
    cluster_sums = differences.groupby("circuit_family")["difference"].sum().to_numpy(float)
    total_n = len(differences)
    observed = abs(float(cluster_sums.sum() / total_n))
    if len(cluster_sums) <= 16:
        # Enumerate the full randomization distribution when feasible. The
        # frozen designs have at most 16 family clusters, so Monte Carlo noise
        # must not decide a result near alpha.
        masks = np.arange(1 << len(cluster_sums), dtype=np.uint32)[:, None]
        bits = (masks >> np.arange(len(cluster_sums), dtype=np.uint32)) & 1
        signs = bits.astype(float) * 2.0 - 1.0
        permuted = np.abs(np.sum(signs * cluster_sums, axis=1) / total_n)
        return float(np.mean(permuted >= observed - 1e-15))
    rng = np.random.default_rng(seed)
    signs = rng.choice((-1.0, 1.0), size=(replicates, len(cluster_sums)))
    permuted = np.abs(np.sum(signs * cluster_sums, axis=1) / total_n)
    return float((1 + np.sum(permuted >= observed)) / (replicates + 1))


def _normal_approx_mde(bootstrap: np.ndarray, alpha: float = ALPHA,
                       power: float = TARGET_POWER) -> float:
    """Approximate two-sided MDE from the cluster-bootstrap standard error."""
    standard_error = float(np.std(np.asarray(bootstrap, dtype=float), ddof=1))
    return float((stats.norm.ppf(1.0 - alpha / 2.0)
                  + stats.norm.ppf(power)) * standard_error)


def _load(path: Path, tool: str, manifest_sha: str, expected_keys: set[tuple],
          expected_key_families: set[tuple]) -> pd.DataFrame:
    frame = pd.read_csv(path.resolve())
    if len(frame) != 520 or frame.duplicated(KEY).any():
        raise RuntimeError(f"{tool}: row/key integrity failure")
    keys = set(map(tuple, frame[KEY].itertuples(index=False, name=None)))
    if keys != expected_keys:
        raise RuntimeError(f"{tool}: paired key set differs from manifest")
    key_families = set(map(tuple, frame[KEY + ["circuit_family"]].itertuples(
        index=False, name=None)))
    if key_families != expected_key_families:
        raise RuntimeError(f"{tool}: circuit-family metadata differs from manifest")
    if set(frame.benchmark_manifest_sha256.astype(str)) != {manifest_sha}:
        raise RuntimeError(f"{tool}: manifest SHA mismatch")
    allowed = {"exact", "unavailable"}
    if not set(frame.fidelity_source.astype(str)).issubset(allowed):
        raise RuntimeError(f"{tool}: unapproved fidelity source")
    exact = frame.fidelity_source.eq("exact")
    fidelity = pd.to_numeric(frame.fidelity, errors="coerce")
    bad_exact = exact & (~np.isfinite(fidelity) | (fidelity < 0.9999999999))
    if bad_exact.any():
        raise RuntimeError(f"{tool}: exact fidelity missing or below threshold")
    frame["valid"] = _as_bool(frame.valid_equivalent_output).astype(int)
    if (frame.valid.eq(1) & ~exact).any():
        raise RuntimeError(f"{tool}: valid output lacks exact fidelity")
    frame["common_reduction_itt"] = pd.to_numeric(
        frame.analysis_common_gate_reduction_pct_itt, errors="raise")
    if not np.isfinite(frame.common_reduction_itt.to_numpy(float)).all():
        raise RuntimeError(f"{tool}: non-finite ITT reduction")
    invalid_nonzero = frame.valid.eq(0) & ~np.isclose(frame.common_reduction_itt, 0.0)
    if invalid_nonzero.any():
        raise RuntimeError(f"{tool}: invalid output has nonzero ITT reduction")
    frame["tool_label"] = tool
    frame["instance_key"] = frame[KEY].astype(str).agg("|".join, axis=1)
    # Schema 1.1 adds resource and stage-timing fields.  Historical evidence is
    # not backfilled: absence is represented by NaN and an explicit availability
    # flag so downstream reports cannot confuse "not measured" with zero cost.
    for column in RESOURCE_COLUMNS:
        if column not in frame.columns:
            frame[column] = np.nan
        else:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["resource_instrumentation_status"] = np.where(
        frame[["optimizer_cpu_seconds", "optimizer_peak_rss_bytes"]].notna().all(axis=1),
        "available", "unavailable_historical_schema")
    return frame


def _pareto_tables(long: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build per-input quality-runtime frontiers without imputing missing cost.

    Quality is ITT common-basis gate reduction (larger is better); cost is
    optimizer wall time (smaller is better).  Invalid outputs and rows without a
    finite runtime remain visible but are ineligible for frontier membership.
    """
    records: list[dict] = []
    pair_counts = {(first, second): {"comparable": 0, "dominates": 0}
                   for first, second in itertools.permutations(TOOLS, 2)}
    for _, group in long.groupby(KEY, sort=False):
        runtime = pd.to_numeric(group.optimizer_elapsed_seconds, errors="coerce")
        quality = pd.to_numeric(group.common_reduction_itt, errors="coerce")
        eligible = (group.valid.eq(1) & np.isfinite(runtime) & (runtime >= 0)
                    & np.isfinite(quality))
        local = group.assign(_runtime=runtime, _quality=quality, _eligible=eligible)
        eligible_rows = local[local._eligible]
        for _, row in local.iterrows():
            status = "unavailable_invalid_or_runtime"
            dominated = False
            if row["_eligible"]:
                others = eligible_rows[eligible_rows.tool_label != row["tool_label"]]
                dominates_row = ((others._quality >= row["_quality"])
                                 & (others._runtime <= row["_runtime"])
                                 & ((others._quality > row["_quality"])
                                    | (others._runtime < row["_runtime"])))
                dominated = bool(dominates_row.any())
                status = "dominated" if dominated else "frontier"
            records.append({
                **{key: row[key] for key in KEY},
                "circuit_family": row["circuit_family"],
                "tool": row["tool_label"],
                "valid": int(row["valid"]),
                "common_reduction_pct_itt": row["_quality"],
                "optimizer_elapsed_seconds": row["_runtime"],
                "pareto_status": status,
            })
        by_tool = {str(row.tool_label): row for _, row in eligible_rows.iterrows()}
        for first, second in pair_counts:
            if first not in by_tool or second not in by_tool:
                continue
            a, b = by_tool[first], by_tool[second]
            pair_counts[(first, second)]["comparable"] += 1
            if (a["_quality"] >= b["_quality"] and a["_runtime"] <= b["_runtime"]
                    and (a["_quality"] > b["_quality"] or a["_runtime"] < b["_runtime"])):
                pair_counts[(first, second)]["dominates"] += 1
    frontier = pd.DataFrame(records)
    summary_rows = []
    for tool, group in frontier.groupby("tool", sort=True):
        eligible = group.pareto_status.isin(["frontier", "dominated"])
        summary_rows.append({
            "tool": tool,
            "n_rows": len(group),
            "pareto_eligible_n": int(eligible.sum()),
            "pareto_frontier_n": int(group.pareto_status.eq("frontier").sum()),
            "pareto_frontier_rate": (
                float(group.pareto_status.eq("frontier").sum() / eligible.sum())
                if eligible.any() else float("nan")
            ),
            "unavailable_n": int((~eligible).sum()),
        })
    pairwise = pd.DataFrame([
        {
            "tool_first": first, "tool_second": second,
            "comparable_inputs": counts["comparable"],
            "first_dominates_n": counts["dominates"],
            "first_dominates_rate": (
                counts["dominates"] / counts["comparable"]
                if counts["comparable"] else float("nan")
            ),
        }
        for (first, second), counts in pair_counts.items()
    ])
    return frontier, pd.DataFrame(summary_rows), pairwise


def analyze(manifest_path: Path, paths: dict[str, Path], output_dir: Path) -> Path:
    manifest_path = manifest_path.resolve()
    manifest = pd.read_csv(manifest_path)
    if len(manifest) != 520 or manifest.duplicated(KEY).any():
        raise RuntimeError("frozen manifest row/key integrity failure")
    manifest_sha = file_sha256(manifest_path)
    expected_keys = set(map(tuple, manifest[KEY].itertuples(index=False, name=None)))
    expected_key_families = set(map(tuple, manifest[KEY + ["circuit_family"]].itertuples(
        index=False, name=None)))
    frames = {tool: _load(paths[tool], tool, manifest_sha, expected_keys,
                          expected_key_families) for tool in TOOLS}
    long = pd.concat(frames.values(), ignore_index=True)

    bootstrap_records: list[dict] = []
    summary_rows = []
    for tool_index, tool in enumerate(TOOLS):
        frame = frames[tool]
        unique_frame = (frame.groupby(
            ["circuit_family", "input_circuit_sha256"], as_index=False
        ).agg(valid=("valid", "mean"),
              common_reduction_itt=("common_reduction_itt", "mean")))
        valid_boot = _nested_bootstrap(
            frame, "valid", BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED + tool_index)
        reduction_boot = _nested_bootstrap(
            frame, "common_reduction_itt", BOOTSTRAP_REPLICATES,
            BOOTSTRAP_SEED + 100 + tool_index)
        for replicate, (valid_value, reduction_value) in enumerate(
                zip(valid_boot, reduction_boot)):
            bootstrap_records.append({
                "analysis": "tool_summary", "contrast": tool,
                "replicate": replicate, "valid_rate": valid_value,
                "common_reduction_pct_itt": reduction_value,
            })
        summary_rows.append({
            "tool": tool, "n_execution_rows": len(frame),
            "n_unique_inputs": len(unique_frame),
            "valid_equivalent_execution_rows": int(frame.valid.sum()),
            "valid_rate": float(unique_frame.valid.mean()),
            "valid_rate_ci95_lower": float(np.percentile(valid_boot, 2.5)),
            "valid_rate_ci95_upper": float(np.percentile(valid_boot, 97.5)),
            "valid_rate_bootstrap_precision_halfwidth": float(np.percentile(
                np.abs(valid_boot - valid_boot.mean()), 95.0)),
            "common_reduction_pct_itt_mean": float(unique_frame.common_reduction_itt.mean()),
            "common_reduction_ci95_lower": float(np.percentile(reduction_boot, 2.5)),
            "common_reduction_ci95_upper": float(np.percentile(reduction_boot, 97.5)),
            "common_reduction_bootstrap_precision_halfwidth_pp": float(np.percentile(
                np.abs(reduction_boot - reduction_boot.mean()), 95.0)),
            "timeout_n": int((frame.compiler_status == "timeout").sum()),
            "error_n": int(frame.compiler_status.astype(str).str.contains("error").sum()),
        })

    pair_rows = []
    pair_data: list[tuple[pd.DataFrame, np.ndarray, np.ndarray]] = []
    for pair_index, (first, second) in enumerate(itertools.combinations(TOOLS, 2)):
        left = frames[first][KEY + ["circuit_family", "valid", "common_reduction_itt"]]
        right = frames[second][KEY + ["valid", "common_reduction_itt"]]
        paired = left.merge(right, on=KEY, validate="one_to_one", suffixes=("_first", "_second"))
        valid_difference = paired.valid_first.to_numpy(float) - paired.valid_second.to_numpy(float)
        reduction_difference = (
            paired.common_reduction_itt_first.to_numpy(float)
            - paired.common_reduction_itt_second.to_numpy(float)
        )
        valid_df = paired[["circuit_family", "input_circuit_sha256"]].copy()
        valid_df["difference"] = valid_difference
        reduction_df = paired[["circuit_family", "input_circuit_sha256"]].copy()
        reduction_df["difference"] = reduction_difference
        unique_valid_df = (valid_df.groupby(
            ["circuit_family", "input_circuit_sha256"], as_index=False
        ).difference.mean())
        unique_reduction_df = (reduction_df.groupby(
            ["circuit_family", "input_circuit_sha256"], as_index=False
        ).difference.mean())
        valid_difference = unique_valid_df.difference.to_numpy(float)
        reduction_difference = unique_reduction_df.difference.to_numpy(float)
        valid_boot = _nested_bootstrap(
            unique_valid_df.rename(columns={"difference": "value"}), "value",
            BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED + 200 + pair_index)
        reduction_boot = _nested_bootstrap(
            unique_reduction_df.rename(columns={"difference": "value"}), "value",
            BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED + 300 + pair_index)
        discordant = int(np.sum(valid_difference != 0))
        first_only = int(np.sum(valid_difference > 0))
        mcnemar_p = (stats.binomtest(first_only, discordant, 0.5).pvalue
                     if discordant else 1.0)
        if np.allclose(reduction_difference, 0):
            wilcoxon_p = 1.0
        else:
            wilcoxon_p = float(stats.wilcoxon(
                reduction_difference, alternative="two-sided", zero_method="pratt"
            ).pvalue)
        pair_rows.append({
            "tool_first": first, "tool_second": second,
            "valid_rate_difference_pp": float(100.0 * valid_difference.mean()),
            "valid_rate_difference_ci95_lower_pp": float(100.0 * np.percentile(valid_boot, 2.5)),
            "valid_rate_difference_ci95_upper_pp": float(100.0 * np.percentile(valid_boot, 97.5)),
            "valid_rate_difference_mde_80pct_power_pp": float(
                100.0 * _normal_approx_mde(valid_boot)),
            "mcnemar_exact_p_two_sided": float(mcnemar_p),
            "valid_cluster_permutation_p": _cluster_permutation(
                unique_valid_df, BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED + 400 + pair_index),
            "common_reduction_difference_pp_mean": float(reduction_difference.mean()),
            "common_reduction_difference_ci95_lower_pp": float(np.percentile(reduction_boot, 2.5)),
            "common_reduction_difference_ci95_upper_pp": float(np.percentile(reduction_boot, 97.5)),
            "common_reduction_difference_mde_80pct_power_pp": _normal_approx_mde(
                reduction_boot),
            "common_reduction_hodges_lehmann_pp": _hodges_lehmann(reduction_difference),
            "common_reduction_rank_biserial": _rank_biserial(reduction_difference),
            "common_reduction_wilcoxon_p_two_sided": wilcoxon_p,
            "common_reduction_cluster_permutation_p": _cluster_permutation(
                unique_reduction_df, BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED + 500 + pair_index),
            "discordant_valid_pairs": discordant,
        })
        for replicate, (valid_value, reduction_value) in enumerate(
                zip(valid_boot, reduction_boot)):
            bootstrap_records.append({
                "analysis": "pairwise_difference",
                "contrast": f"{first}_minus_{second}", "replicate": replicate,
                "valid_rate": valid_value,
                "common_reduction_pct_itt": reduction_value,
            })
        pair_data.append((paired, valid_difference, reduction_difference))
    pairwise = pd.DataFrame(pair_rows)
    pairwise["mcnemar_p_holm"] = _holm(pairwise.mcnemar_exact_p_two_sided.tolist())
    pairwise["valid_cluster_permutation_p_holm"] = _holm(
        pairwise.valid_cluster_permutation_p.tolist())
    pairwise["common_reduction_wilcoxon_p_holm"] = _holm(
        pairwise.common_reduction_wilcoxon_p_two_sided.tolist())
    pairwise["common_reduction_cluster_permutation_p_holm"] = _holm(
        pairwise.common_reduction_cluster_permutation_p.tolist())

    model_status: dict[str, object] = {
        "primary_binary_model": "family-clustered nested bootstrap plus cluster sign permutation",
        "primary_binary_model_reason": (
            "valid-output rates are boundary concentrated; the preregistered nonparametric fallback "
            "avoids separation and singular random-effect estimates"
        ),
    }
    try:
        import statsmodels.formula.api as smf
        model = smf.mixedlm(
            "common_reduction_itt ~ C(tool_label)", long,
            groups=long["circuit_family"],
            vc_formula={
                "instance": "0 + C(instance_key)",
                "seed": "0 + C(seed)",
            },
            re_formula="1",
        ).fit(reml=True, method="lbfgs", maxiter=1000)
        model_status.update({
            "continuous_mixed_model_converged": bool(model.converged),
            "continuous_mixed_model_formula": "common_reduction_itt ~ C(tool)",
            "continuous_mixed_model_random_effects": "family + instance + seed intercepts",
            "continuous_mixed_model_parameters": {
                str(k): float(v) for k, v in model.params.items()
            },
        })
        _atomic_text(output_dir / "continuous_mixed_model.txt", model.summary().as_text())
    except Exception as exc:
        model_status.update({
            "continuous_mixed_model_converged": False,
            "continuous_mixed_model_error": f"{type(exc).__name__}: {exc}",
            "continuous_fallback": "family-clustered nested bootstrap plus cluster sign permutation",
        })

    summary = pd.DataFrame(summary_rows)
    pareto_frontier, pareto_summary, pareto_pairwise = _pareto_tables(long)
    bootstrap_frame = pd.DataFrame(bootstrap_records)
    family = (long.groupby(["circuit_family", "tool_label"], as_index=False)
              .agg(n=("valid", "size"), valid_rate=("valid", "mean"),
                   common_reduction_pct_itt_mean=("common_reduction_itt", "mean"),
                   timeout_n=("compiler_status", lambda x: int((x == "timeout").sum()))))
    lofo_rows = []
    for left_out in sorted(long.circuit_family.unique()):
        subset = long[long.circuit_family != left_out]
        for tool, group in subset.groupby("tool_label", sort=True):
            lofo_rows.append({
                "left_out_family": left_out, "tool": tool,
                "valid_rate": float(group.valid.mean()),
                "common_reduction_pct_itt_mean": float(group.common_reduction_itt.mean()),
            })
    lofo = pd.DataFrame(lofo_rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths_out = {
        "tool_summary.csv": summary,
        "pairwise_contrasts.csv": pairwise,
        "family_tool_diagnostics.csv": family,
        "bootstrap_source_10000.csv": bootstrap_frame,
        "leave_one_family_out.csv": lofo,
        "quality_runtime_pareto_frontier.csv": pareto_frontier,
        "quality_runtime_pareto_summary.csv": pareto_summary,
        "quality_runtime_pareto_pairwise.csv": pareto_pairwise,
    }
    for name, frame in paths_out.items():
        _atomic_text(output_dir / name, frame.to_csv(index=False))
    audit = {
        "status": "complete",
        "n_manifest": len(manifest), "tools": list(TOOLS),
        "pair_key": KEY, "manifest_sha256": manifest_sha,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "outer_cluster": "circuit_family",
        "inner_unit": "unique input_circuit_sha256 within family",
        "estimand": "unique-input-weighted mean; repeated executions remain operational rows",
        "multiple_testing": "Holm within endpoint across six tool pairs",
        "power_analysis": {
            "type": "normal approximation using cluster-bootstrap standard error",
            "alpha_two_sided": ALPHA, "target_power": TARGET_POWER,
            "scope": "paired tool contrasts; descriptive tool summaries report precision, not MDE",
        },
        "model_status": model_status,
        "input_sha256": {tool: file_sha256(paths[tool].resolve()) for tool in TOOLS},
        "output_sha256": {name: file_sha256(output_dir / name) for name in paths_out},
        "source_sha256": file_sha256(Path(__file__).resolve()),
        "protocol_sha256": file_sha256(PROJECT_ROOT / "experiments" / "prepaper_protocol.json"),
    }
    audit_path = output_dir / "audit.json"
    _atomic_text(audit_path, json.dumps(audit, indent=2, sort_keys=True))
    print(summary.to_string(index=False))
    print(pairwise.to_string(index=False))
    return audit_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    for tool in TOOLS:
        parser.add_argument(f"--{tool}", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.manifest, {tool: getattr(args, tool) for tool in TOOLS},
            args.output_dir.resolve())


if __name__ == "__main__":
    main()
