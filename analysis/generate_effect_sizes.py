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


def safe_load(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")
    return pd.read_csv(path)


def compute_comparison(comparison_name, experiment, metric, x, y):
    """Compute one row of effect-size statistics."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

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

    # Bootstrap CI on the difference of means (10,000 resamples).
    _, ci_low, ci_high = bootstrap_mean_diff_ci(x, y, n_bootstrap=10_000, random_seed=42)

    return {
        "comparison": comparison_name,
        "experiment": experiment,
        "metric": metric,
        "mean_1": float(np.mean(x)),
        "mean_2": float(np.mean(y)),
        "cohens_d": d_val,
        "hedges_g": g_val,
        "cliffs_delta": delta_val,
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
    baseline = df.loc[df["optimizer"] == "greedy", "reduction"].values
    for opt in ("rls", "sa", "ga"):
        other = df.loc[df["optimizer"] == opt, "reduction"].values
        rows.append(
            compute_comparison(
                comparison_name=f"Greedy vs {opt.upper()}",
                experiment="E4",
                metric="reduction",
                x=baseline,
                y=other,
            )
        )
    return rows


def comparisons_e10():
    """E10: phase-1 (greedy_phase1) vs phase-2a (commutation_phase2)."""
    df = safe_load(DATA_DIR / "v5" / "e10" / "e10_expanded_phase1_vs_phase2_20260613_131601.csv")
    df = df.dropna(subset=["reduction"])
    phase1 = df.loc[df["optimizer"] == "greedy_phase1", "reduction"].values
    phase2 = df.loc[df["optimizer"] == "commutation_phase2", "reduction"].values
    return [
        compute_comparison(
            comparison_name="Phase-1 vs Phase-2a",
            experiment="E10",
            metric="reduction",
            x=phase1,
            y=phase2,
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
    wcl = df.loc[df["listing_model"] == "WCL", "reduction"].values
    lbl = df.loc[df["listing_model"] == "LBL", "reduction"].values
    return [
        compute_comparison(
            comparison_name="WCL vs LBL",
            experiment="E19",
            metric="reduction",
            x=wcl,
            y=lbl,
        )
    ]


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "comparison",
    "experiment",
    "metric",
    "mean_1",
    "mean_2",
    "cohens_d",
    "hedges_g",
    "cliffs_delta",
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
        "difference of means, with Cohen's d (parametric) and Cliff's delta "
        "(non-parametric). Positive Cohen's d / positive bootstrap difference "
        "means group 1 has the larger mean reduction."
    )
    lines.append("")
    lines.append(f"Source data: `{csv_path.name}`")
    lines.append("")

    lines.append("## Key Comparisons")
    lines.append("")
    header = (
        "| Comparison | Exp | mean_1 | mean_2 | Cohen's d | Hedges' g | "
        "Cliff's delta | Bootstrap 95% CI (diff) | n_1 | n_2 |"
    )
    sep = "|---|---|---|---|---|---|---|---|---|---|"
    lines.append(header)
    lines.append(sep)
    for _, r in key_df.iterrows():
        ci = f"[{r['bootstrap_ci_lower']:+.4f}, {r['bootstrap_ci_upper']:+.4f}]"
        lines.append(
            f"| {r['comparison']} | {r['experiment']} | "
            f"{r['mean_1']:.4f} | {r['mean_2']:.4f} | "
            f"{r['cohens_d']:+.3f} ({r['cohens_magnitude']}) | "
            f"{r['hedges_g']:+.3f} | "
            f"{r['cliffs_delta']:+.3f} ({r['cliffs_magnitude']}) | "
            f"{ci} | {r['n_1']} | {r['n_2']} |"
        )

    lines.append("")
    lines.append("## Magnitude conventions")
    lines.append("")
    lines.append("- **Cohen's d / Hedges' g**: negligible < 0.2, small 0.2-0.5, medium 0.5-0.8, large >= 0.8")
    lines.append("- **Cliff's delta**: negligible < 0.147, small 0.147-0.33, medium 0.33-0.474, large >= 0.474")
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
                f"| {r['comparison']} | {r['experiment']} | "
                f"{r['mean_1']:.4f} | {r['mean_2']:.4f} | "
                f"{r['cohens_d']:+.3f} | {r['hedges_g']:+.3f} | "
                f"{r['cliffs_delta']:+.3f} | {ci} | {r['n_1']} | {r['n_2']} |"
            )
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote summary -> {md_path}")


def main():
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
    key_cols = ["comparison", "experiment", "cohens_d", "cliffs_delta", "bootstrap_ci_lower", "bootstrap_ci_upper"]
    key_names = {"Greedy vs RLS", "Greedy vs SA", "Greedy vs GA", "Phase-1 vs Phase-2a", "WCL vs LBL", "Random vs Structured"}
    print(key_df[key_df["comparison"].isin(key_names)][key_cols].to_string(index=False))


if __name__ == "__main__":
    main()
