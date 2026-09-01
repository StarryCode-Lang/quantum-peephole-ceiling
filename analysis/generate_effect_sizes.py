"""Generate effect size reports (Bootstrap CI + Cohen's d + Cliff's delta).

Loads experiment CSVs (E1, E4, E10, E14, E19), computes pairwise effect
sizes on the ``reduction`` metric, and writes:

  * analysis/figures/effect_sizes.csv         - machine-readable table
  * analysis/figures/effect_sizes_summary.md  - formatted Markdown report

Uses the canonical implementations in analysis.phase1_statistics.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.phase1_statistics.effect_size import (
    cliffs_delta,
    cohens_d,
    glass_delta,
    interpret_effect_size,
)

DATA_DIR = PROJECT_ROOT / "data"
OUT_DIR = PROJECT_ROOT / "analysis" / "figures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def bootstrap_mean_diff_ci(x, y, n_bootstrap=10_000, ci=95.0, random_seed=42):
    """Two-sample percentile bootstrap CI on the difference of means.

    Resamples each group independently with replacement, computes the mean
    difference for each replicate, returns (point_estimate, ci_lower, ci_upper).
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    nx, ny = len(x_arr), len(y_arr)
    if nx == 0 or ny == 0:
        raise ValueError("Both samples must be non-empty for bootstrap CI.")
    rng = np.random.default_rng(random_seed)
    diffs = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        xs = rng.choice(x_arr, size=nx, replace=True)
        ys = rng.choice(y_arr, size=ny, replace=True)
        diffs[i] = xs.mean() - ys.mean()
    point = float(x_arr.mean() - y_arr.mean())
    alpha = (100.0 - ci) / 2.0
    ci_lower = float(np.percentile(diffs, alpha))
    ci_upper = float(np.percentile(diffs, 100.0 - alpha))
    return point, ci_lower, ci_upper


def bootstrap_paired_diff_ci(x, y, n_bootstrap=10_000, ci=95.0, random_seed=42):
    """Percentile bootstrap CI for a paired mean difference."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if x_arr.shape != y_arr.shape or x_arr.size == 0:
        raise ValueError("Paired samples must be non-empty and have equal shape.")
    differences = x_arr - y_arr
    rng = np.random.default_rng(random_seed)
    indices = rng.integers(0, differences.size, size=(n_bootstrap, differences.size))
    boot = differences[indices].mean(axis=1)
    alpha = (100.0 - ci) / 2.0
    return (
        float(differences.mean()),
        float(np.percentile(boot, alpha)),
        float(np.percentile(boot, 100.0 - alpha)),
    )


def matched_rank_biserial(x, y):
    """Matched-pairs rank-biserial correlation, excluding zero differences."""
    from scipy.stats import rankdata

    differences = np.asarray(x, dtype=float) - np.asarray(y, dtype=float)
    differences = differences[differences != 0]
    if differences.size == 0:
        return 0.0
    ranks = rankdata(np.abs(differences), method="average")
    denominator = float(ranks.sum())
    return float((ranks[differences > 0].sum() - ranks[differences < 0].sum()) / denominator)


def safe_load(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")
    return pd.read_csv(path)


def paired_values(df, group_col, group_1, group_2, keys, value_col="reduction"):
    """Return strictly aligned paired values; reject duplicates or missing mates."""
    subset = df[df[group_col].isin([group_1, group_2])]
    duplicated = subset.duplicated(keys + [group_col], keep=False)
    if duplicated.any():
        raise ValueError(f"Duplicate rows violate paired keys {keys + [group_col]}")
    wide = subset.pivot(index=keys, columns=group_col, values=value_col)
    if group_1 not in wide or group_2 not in wide:
        raise ValueError(f"Missing comparison groups: {group_1}, {group_2}")
    if wide[[group_1, group_2]].isna().any().any():
        raise ValueError("Paired comparison contains unmatched rows.")
    return wide[group_1].to_numpy(), wide[group_2].to_numpy()


def compute_comparison(comparison_name, experiment, metric, x, y, *, paired=False):
    """Compute one row of effect-size statistics."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if paired and x.shape != y.shape:
        raise ValueError("Paired comparisons require equal-length aligned samples.")

    # Cohen's d (and Hedges' g) - canonical module.
    # Guard against zero pooled variance (degenerate samples).
    try:
        d_res = cohens_d(x, y)
        d_val = float(d_res["d"])
        g_val = float(d_res["g"])
        cohens_mag = interpret_effect_size(d_res["g"], metric="cohens_d")
    except ValueError:
        d_val = float("nan")
        g_val = float("nan")
        cohens_mag = "undefined (zero variance)"

    # Glass's Delta - canonical module (statistical protocol item 2:
    # required for zero-variance comparisons where Cohen's d is undefined).
    # control="auto" uses group 2 (y) as the baseline denominator, falling
    # back to group 1 when y has zero variance.
    try:
        gd_res = glass_delta(x, y, control="auto")
        gd_val = float(gd_res["delta"])
    except ValueError:
        gd_val = float("nan")

    # Cliff's delta - canonical module.
    try:
        cd_res = cliffs_delta(x, y)
        delta_val = float(cd_res["delta"])
        cliffs_mag = cd_res["magnitude"]
        cliffs_ci_low = float(cd_res["ci_lower"])
        cliffs_ci_high = float(cd_res["ci_upper"])
    except ValueError:
        delta_val = float("nan")
        cliffs_mag = "undefined (empty sample)"
        cliffs_ci_low = float("nan")
        cliffs_ci_high = float("nan")

    if paired:
        differences = x - y
        diff_sd = float(np.std(differences, ddof=1)) if len(differences) > 1 else 0.0
        cohens_dz = float(np.mean(differences) / diff_sd) if diff_sd > 0 else float("nan")
        rank_biserial = matched_rank_biserial(x, y)
        _, ci_low, ci_high = bootstrap_paired_diff_ci(
            x, y, n_bootstrap=10_000, random_seed=42
        )
        # Independent-sample standardized effects are not valid for this design.
        d_val = g_val = gd_val = delta_val = float("nan")
        cohens_mag = cliffs_mag = "not applicable (paired design)"
    else:
        cohens_dz = float("nan")
        rank_biserial = float("nan")
        _, ci_low, ci_high = bootstrap_mean_diff_ci(
            x, y, n_bootstrap=10_000, random_seed=42
        )

    return {
        "comparison": comparison_name,
        "experiment": experiment,
        "metric": metric,
        "design": "paired" if paired else "independent",
        "mean_1": float(np.mean(x)),
        "mean_2": float(np.mean(y)),
        "cohens_d": d_val,
        "hedges_g": g_val,
        "glass_delta": gd_val,
        "cliffs_delta": delta_val,
        "cohens_dz": cohens_dz,
        "matched_rank_biserial": rank_biserial,
        "bootstrap_ci_lower": ci_low,
        "bootstrap_ci_upper": ci_high,
        "n_1": int(len(x)),
        "n_2": int(len(y)),
        "cliffs_magnitude": cliffs_mag,
        "cohens_magnitude": cohens_mag,
    }


# ---------------------------------------------------------------------------
# Per-experiment comparison builders
# ---------------------------------------------------------------------------

def comparisons_e1():
    """E1: Phase-1 reduction on random circuits.

    Loaded for context/verification. E1 is a single-optimizer phase-transition
    experiment; its reduction column is identically zero across all 25,000 rows
    (greedy Phase-1 does not reduce random circuits below the phase-transition
    threshold), so no meaningful pairwise effect-size comparison is produced.
    """
    df = safe_load(DATA_DIR / "v2_fixed" / "e01" / "e01_phase_transition_v2_20260613_132653.csv")
    df = df.dropna(subset=["reduction"])
    red = df["reduction"].values
    print(
        f"  E1 reference: n={len(red)}, mean reduction={red.mean():.6f}, "
        f"std={red.std():.6f} (single-optimizer, no pairwise comparison)"
    )
    return []


def comparisons_e4():
    """E4: algorithm comparison (greedy vs rls/sa/ga)."""
    df = safe_load(DATA_DIR / "v2_fixed" / "e04" / "e04_algorithm_comparison_v2_20260613_132653.csv")
    df = df.dropna(subset=["reduction"])
    rows = []
    for opt in ("rls", "sa", "ga"):
        keys = [c for c in ("seed_index", "seed_base", "trial", "seed") if c in df.columns]
        baseline, other = paired_values(df, "optimizer", "greedy", opt, keys)
        rows.append(
            compute_comparison(
                comparison_name=f"Greedy vs {opt.upper()}",
                experiment="E4",
                metric="reduction",
                x=baseline,
                y=other,
                paired=True,
            )
        )
    return rows


def comparisons_e10():
    """E10: phase-1 (greedy_phase1) vs phase-2a (commutation_phase2)."""
    df = safe_load(DATA_DIR / "v5" / "e10" / "e10_expanded_phase1_vs_phase2_20260613_131601.csv")
    df = df.dropna(subset=["reduction"])
    keys = ["part", "circuit_family", "circuit_type", "n_qubits", "depth", "trial", "seed"]
    phase1, phase2 = paired_values(
        df, "optimizer", "greedy_phase1", "commutation_phase2", keys
    )
    return [
        compute_comparison(
            comparison_name="Phase-1 vs Phase-2a",
            experiment="E10",
            metric="reduction",
            x=phase1,
            y=phase2,
            paired=True,
        )
    ]


def comparisons_e14():
    """E14: random vs structured circuit families.

    random = {random_clifford, haar_random}; structured = all others.
    Reports the aggregate comparison plus per-family comparisons.
    """
    df = safe_load(DATA_DIR / "v5" / "e14" / "e14_extended_benchmark_e14_full_20260611_114726.csv")
    df = df.dropna(subset=["reduction"])

    random_mask = df["circuit_type"].isin(["random_clifford", "haar_random"])
    random_red = df.loc[random_mask, "reduction"].values
    structured_red = df.loc[~random_mask, "reduction"].values

    rows = [
        compute_comparison(
            comparison_name="Random vs Structured",
            experiment="E14",
            metric="reduction",
            x=random_red,
            y=structured_red,
        )
    ]

    structured_families = (
        df.loc[~random_mask, "circuit_family"].drop_duplicates().sort_values().tolist()
    )
    for family in structured_families:
        fam_red = df.loc[df["circuit_family"] == family, "reduction"].values
        if len(fam_red) < 2:
            continue
        rows.append(
            compute_comparison(
                comparison_name=f"Random vs {family}",
                experiment="E14",
                metric="reduction",
                x=random_red,
                y=fam_red,
            )
        )
    return rows


def comparisons_e19():
    """E19: WCL vs LBL listing models."""
    df = safe_load(DATA_DIR / "v6" / "e19" / "e19_wcl_listing_full_e19_full_20260620_123825.csv")
    df = df.dropna(subset=["reduction"])
    keys = ["n_qubits", "depth", "trial", "seed"]
    wcl, lbl = paired_values(df, "listing_model", "WCL", "LBL", keys)
    return [
        compute_comparison(
            comparison_name="WCL vs LBL",
            experiment="E19",
            metric="reduction",
            x=wcl,
            y=lbl,
            paired=True,
        )
    ]


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "comparison",
    "experiment",
    "metric",
    "design",
    "mean_1",
    "mean_2",
    "cohens_d",
    "hedges_g",
    "glass_delta",
    "cliffs_delta",
    "cohens_dz",
    "matched_rank_biserial",
    "bootstrap_ci_lower",
    "bootstrap_ci_upper",
    "n_1",
    "n_2",
    "cliffs_magnitude",
    "cohens_magnitude",
]


def write_csv(rows, out_path):
    df = pd.DataFrame(rows)[CSV_COLUMNS]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, float_format="%.6f")
    print(f"Wrote {len(df)} rows -> {out_path}")


def write_summary_md(rows, csv_path, md_path):
    df = pd.DataFrame(rows)
    key_names = {
        "Greedy vs RLS",
        "Greedy vs SA",
        "Greedy vs GA",
        "Phase-1 vs Phase-2a",
        "WCL vs LBL",
        "Random vs Structured",
    }
    key_df = df[df["comparison"].isin(key_names)].copy()

    lines = []
    lines.append("# Effect Size Report")
    lines.append("")
    lines.append(
        "Bootstrap 95% CIs (10,000 resamples, percentile method) on the "
        "difference of means. Paired experiments resample within-circuit "
        "differences and report Cohen's dz plus matched rank-biserial; "
        "independent experiments report Cohen's d and Cliff's delta."
    )
    lines.append("")
    lines.append(f"Source data: `{csv_path.name}`")
    lines.append("")

    lines.append("## Key Comparisons")
    lines.append("")
    header = (
        "| Comparison | Exp | Design | mean_1 | mean_2 | Cohen's d/dz | "
        "Cliff's/matched rank-biserial | Bootstrap 95% CI (diff) | n_1 | n_2 |"
    )
    sep = "|---|---|---|---|---|---|---|---|---|---|"
    lines.append(header)
    lines.append(sep)
    for _, r in key_df.iterrows():
        ci = f"[{r['bootstrap_ci_lower']:+.4f}, {r['bootstrap_ci_upper']:+.4f}]"
        standardized = r['cohens_dz'] if r['design'] == 'paired' else r['cohens_d']
        ordinal = r['matched_rank_biserial'] if r['design'] == 'paired' else r['cliffs_delta']
        lines.append(
            f"| {r['comparison']} | {r['experiment']} | "
            f"{r['design']} | "
            f"{r['mean_1']:.4f} | {r['mean_2']:.4f} | "
            f"{standardized:+.3f} | {ordinal:+.3f} | "
            f"{ci} | {r['n_1']} | {r['n_2']} |"
        )

    lines.append("")
    lines.append("## Magnitude conventions")
    lines.append("")
    lines.append("- **Cohen's d / Hedges' g / Glass's Delta**: negligible < 0.2, small 0.2-0.5, medium 0.5-0.8, large >= 0.8")
    lines.append("- **Cliff's delta**: negligible < 0.147, small 0.147-0.33, medium 0.33-0.474, large >= 0.474")
    lines.append("- **Glass's Delta denominator**: SD of group 2 (baseline); falls back to group 1 SD when group 2 has zero variance (e.g., LBL Phase-1).")
    lines.append("")

    other_df = df[~df["comparison"].isin(key_names)]
    if len(other_df) > 0:
        lines.append("## Supplementary Comparisons (E14 per-family)")
        lines.append("")
        lines.append(header)
        lines.append(sep)
        for _, r in other_df.iterrows():
            ci = f"[{r['bootstrap_ci_lower']:+.4f}, {r['bootstrap_ci_upper']:+.4f}]"
            lines.append(
                f"| {r['comparison']} | {r['experiment']} | {r['design']} | "
                f"{r['mean_1']:.4f} | {r['mean_2']:.4f} | "
                f"{r['cohens_d']:+.3f} | {r['cliffs_delta']:+.3f} | "
                f"{ci} | {r['n_1']} | {r['n_2']} |"
            )
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote summary -> {md_path}")


def main(out_dir=None):
    if out_dir is not None:
        global OUT_DIR
        OUT_DIR = Path(out_dir)

    rows = []
    rows.extend(comparisons_e1())
    rows.extend(comparisons_e4())
    rows.extend(comparisons_e10())
    rows.extend(comparisons_e14())
    rows.extend(comparisons_e19())

    csv_path = OUT_DIR / "effect_sizes.csv"
    md_path = OUT_DIR / "effect_sizes_summary.md"
    write_csv(rows, csv_path)
    write_summary_md(rows, csv_path, md_path)

    print("\n=== Key comparison summary ===")
    key_df = pd.DataFrame(rows)
    key_cols = [
        "comparison", "experiment", "design", "cohens_d", "cohens_dz",
        "cliffs_delta", "matched_rank_biserial", "bootstrap_ci_lower",
        "bootstrap_ci_upper",
    ]
    key_names = {"Greedy vs RLS", "Greedy vs SA", "Greedy vs GA", "Phase-1 vs Phase-2a", "WCL vs LBL", "Random vs Structured"}
    print(key_df[key_df["comparison"].isin(key_names)][key_cols].to_string(index=False))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate effect size reports.")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory (default: analysis/figures). Use an alternate "
             "directory for verification runs that must not touch the "
             "canonical figure artifacts.",
    )
    args = parser.parse_args()
    main(out_dir=args.out_dir)
