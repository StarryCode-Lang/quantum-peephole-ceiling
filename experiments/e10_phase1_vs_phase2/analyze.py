"""
E10 Analysis: Phase 1 vs Phase 2 Comparison
=============================================
Generate publication-quality figures and statistical reports for E10 results.

Version: 3.1.0 (integrated with phase1_statistics)
"""

from __future__ import annotations

import sys
import os
import glob
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# --- Phase 1 Statistics modules (newly integrated) ---
from analysis.phase1_statistics.bootstrap import bootstrap_ci as _bootstrap_ci
from analysis.phase1_statistics.multiple_comparison import (
    benjamini_hochberg,
    holm_bonferroni,
)
from analysis.finite_size_scaling import (
    binder_cumulant_by_size,
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_e10_data():
    """Load E10 data."""
    data_dir = PROJECT_ROOT / "data/v5/e10"
    csv_files = list(data_dir.glob("*.csv"))

    if not csv_files:
        print("No E10 data found. Please run E10 first.")
        return None

    # Load most recent file
    latest = max(csv_files, key=lambda p: p.stat().st_mtime)
    df = pd.read_csv(latest)
    print(f"Loaded E10 data: {latest} ({len(df)} records)")
    return df


# ---------------------------------------------------------------------------
# Figure generation (kept mostly intact, but using robust bootstrap_ci)
# ---------------------------------------------------------------------------

def generate_e10_figure(df):
    """Generate E10 comparison figure."""
    plt.style.use('seaborn-v0_8-paper')
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 11,
        'axes.labelsize': 13,
        'axes.titlesize': 13,
        'legend.fontsize': 9,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'mathtext.fontset': 'cm',
    })

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))

    optimizers = ['greedy_phase1', 'commutation_phase2', 'hybrid_phase1_2']
    optimizer_labels = ['Phase 1\n(Greedy)', 'Phase 2\n(Commutation)', 'Phase 1+2\n(Hybrid)']
    colors = ['#2166ac', '#b2182b', '#4daf4a']

    parts = ['random', 'structured', 'real']
    part_labels = ['Random Circuits', 'Structured Circuits', 'Real Circuits']

    for idx, (part, part_label) in enumerate(zip(parts, part_labels)):
        ax = axes[idx]
        sub = df[df['part'] == part]

        means = []
        cis_low = []
        cis_high = []

        for opt in optimizers:
            opt_sub = sub[sub['optimizer'] == opt]['reduction'].values
            if len(opt_sub) > 0:
                result = _bootstrap_ci(opt_sub, n_bootstrap=10000, random_seed=42)
                means.append(result['estimate'] * 100)  # Convert to percentage
                cis_low.append(result['ci_lower'] * 100)
                cis_high.append(result['ci_upper'] * 100)
            else:
                means.append(0)
                cis_low.append(0)
                cis_high.append(0)

        x = np.arange(len(optimizers))
        bars = ax.bar(x, means, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)

        # Add error bars
        for i, (mean, ci_l, ci_h) in enumerate(zip(means, cis_low, cis_high)):
            ax.errorbar(i, mean, yerr=[[mean - ci_l], [ci_h - mean]],
                       fmt='none', ecolor='black', elinewidth=1.5, capsize=3)

        ax.set_xticks(x)
        ax.set_xticklabels(optimizer_labels, fontsize=9)
        ax.set_ylabel('Gate Reduction (%)')
        ax.set_title(f'({chr(97+idx)}) {part_label}')
        ax.set_ylim(0, max(max(means) * 1.3, 5))
        ax.grid(True, alpha=0.3, axis='y')

        # Add value labels on bars
        for bar, mean in zip(bars, means):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                   f'{mean:.1f}%', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()

    output_dir = PROJECT_ROOT / "analysis/figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_dir / 'e10_phase1_vs_phase2.pdf')
    plt.close()

    print(f"Figure saved to {output_dir / 'e10_phase1_vs_phase2.pdf'}")


# ---------------------------------------------------------------------------
# Statistical analysis using phase1_statistics modules
# ---------------------------------------------------------------------------

_PAIR_KEY_CANDIDATES = (
    'part', 'circuit_family', 'circuit_type', 'n_qubits', 'depth', 'trial', 'seed'
)


def _paired_reductions(
    sub_df: pd.DataFrame,
    opt_a: str,
    opt_b: str,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Align two optimizers on the exact circuit-condition key.

    E10 evaluates every optimizer on the same generated circuit.  Treating the
    optimizer groups as independent discards this design and gives the wrong
    standard error.  A pivot also makes duplicate or incomplete keys visible.
    """
    key_cols = [column for column in _PAIR_KEY_CANDIDATES if column in sub_df.columns]
    if not key_cols:
        raise ValueError("E10 paired analysis requires circuit-condition key columns")

    selected = sub_df[sub_df['optimizer'].isin([opt_a, opt_b])]
    duplicate_mask = selected.duplicated(key_cols + ['optimizer'], keep=False)
    if duplicate_mask.any():
        raise ValueError("duplicate optimizer result for an E10 circuit-condition key")

    wide = selected.pivot(index=key_cols, columns='optimizer', values='reduction')
    if opt_a not in wide.columns or opt_b not in wide.columns:
        return np.array([]), np.array([]), key_cols
    paired = wide[[opt_a, opt_b]].dropna()
    return paired[opt_a].to_numpy(), paired[opt_b].to_numpy(), key_cols


def _run_pairwise_analysis(sub_df: pd.DataFrame, opt_a: str, opt_b: str) -> dict:
    """Run primary Wilcoxon and sensitivity paired-t analyses for E10."""
    a_vals, b_vals, key_cols = _paired_reductions(sub_df, opt_a, opt_b)

    if len(a_vals) < 2:
        return {
            "opt_a": opt_a,
            "opt_b": opt_b,
            "p_value": np.nan,
            "wilcoxon_statistic": np.nan,
            "paired_t_p_value": np.nan,
            "t_statistic": np.nan,
            "n_a": len(a_vals),
            "n_b": len(a_vals),
            "n_pairs": len(a_vals),
            "pair_key": key_cols,
            "design": "paired",
        }

    differences = a_vals - b_vals
    if np.allclose(differences, 0.0):
        wilcoxon_stat, wilcoxon_p = 0.0, 1.0
        t_stat, t_p = 0.0, 1.0
    else:
        wilcoxon = stats.wilcoxon(
            differences,
            zero_method='wilcox',
            alternative='two-sided',
            method='auto',
        )
        wilcoxon_stat, wilcoxon_p = float(wilcoxon.statistic), float(wilcoxon.pvalue)
        t_result = stats.ttest_rel(a_vals, b_vals, nan_policy='omit')
        t_stat, t_p = float(t_result.statistic), float(t_result.pvalue)

    nonzero = differences[~np.isclose(differences, 0.0)]
    if len(nonzero):
        ranks = stats.rankdata(np.abs(nonzero), method="average")
        rank_biserial = float(
            (ranks[nonzero > 0].sum() - ranks[nonzero < 0].sum())
            / ranks.sum()
        )
    else:
        rank_biserial = 0.0
    diff_sd = float(np.std(differences, ddof=1))
    if diff_sd > 0:
        cohen_dz = float(np.mean(differences) / diff_sd)
    else:
        cohen_dz = 0.0 if np.isclose(np.mean(differences), 0.0) else float(
            np.sign(np.mean(differences)) * np.inf
        )
    diff_ci = _bootstrap_ci(differences, n_bootstrap=10000, random_seed=42)

    return {
        "opt_a": opt_a,
        "opt_b": opt_b,
        "p_value": wilcoxon_p,
        "primary_test": "Wilcoxon signed-rank, two-sided",
        "wilcoxon_statistic": wilcoxon_stat,
        "paired_t_p_value": t_p,
        "t_statistic": float(t_stat),
        "n_a": len(a_vals),
        "n_b": len(b_vals),
        "n_pairs": len(a_vals),
        "pair_key": key_cols,
        "design": "paired",
        "mean_paired_difference": float(np.mean(differences)),
        "mean_difference_ci": {
            "ci_lower": diff_ci["ci_lower"],
            "ci_upper": diff_ci["ci_upper"],
        },
        "cohen_dz": cohen_dz,
        "matched_rank_biserial": rank_biserial,
    }


def _run_pairwise_ttest(sub_df: pd.DataFrame, opt_a: str, opt_b: str) -> dict:
    """Backward-compatible name; the implementation is now correctly paired."""
    return _run_pairwise_analysis(sub_df, opt_a, opt_b)


def generate_statistical_report(df: pd.DataFrame) -> dict:
    """
    Generate comprehensive statistical report using phase1_statistics modules.

    Returns a dictionary suitable for JSON serialization.
    """
    report = {
        "experiment_id": "E10",
        "description": "Phase 1 vs Phase 2 optimization comparison (statistical)",
        "n_records": len(df),
        "parts": {},
    }

    optimizers = ['greedy_phase1', 'commutation_phase2', 'hybrid_phase1_2']

    # ------------------------------------------------------------------
    # Per-part analysis
    # ------------------------------------------------------------------
    for part in ['random', 'structured', 'real']:
        sub = df[df['part'] == part]
        if len(sub) == 0:
            continue

        part_report = {
            "n_records": int(len(sub)),
            "descriptive_stats": {},
            "bootstrap_cis": {},
            "pairwise_comparisons": {},
            "effect_sizes": {},
            "multiple_comparison": {},
        }

        # Descriptive + bootstrap CI per optimizer
        for opt in optimizers:
            opt_sub = sub[sub['optimizer'] == opt]['reduction'].dropna().values
            if len(opt_sub) == 0:
                continue

            # descriptive
            part_report["descriptive_stats"][opt] = {
                "n": int(len(opt_sub)),
                "mean": float(np.mean(opt_sub)),
                "median": float(np.median(opt_sub)),
                "std": float(np.std(opt_sub, ddof=1)),
                "min": float(np.min(opt_sub)),
                "max": float(np.max(opt_sub)),
            }

            # bootstrap CI via phase1_statistics module
            ci_result = _bootstrap_ci(opt_sub, n_bootstrap=10000, random_seed=42)
            part_report["bootstrap_cis"][opt] = ci_result

        # Paired comparisons: the same circuit-condition is evaluated by every
        # optimizer, so Wilcoxon signed-rank is primary and paired t is a
        # sensitivity analysis.
        pairwise_results = []
        for i in range(len(optimizers)):
            for j in range(i + 1, len(optimizers)):
                opt_a, opt_b = optimizers[i], optimizers[j]
                ttest = _run_pairwise_analysis(sub, opt_a, opt_b)
                if ttest["n_pairs"] < 2:
                    continue
                comparison_name = f"{opt_a}_vs_{opt_b}"
                part_report["pairwise_comparisons"][comparison_name] = ttest
                pairwise_results.append({
                    "experiment": f"E10_{part}",
                    "comparison": comparison_name,
                    "p_value": ttest["p_value"],
                    "effect_size": np.nan,
                    "n1": ttest["n_a"],
                    "n2": ttest["n_b"],
                })

                part_report["effect_sizes"][comparison_name] = {
                    "cohen_dz": ttest["cohen_dz"],
                    "matched_rank_biserial": ttest["matched_rank_biserial"],
                    "mean_paired_difference": ttest["mean_paired_difference"],
                    "mean_difference_ci": ttest["mean_difference_ci"],
                }

        # Multiple comparison correction (Benjamini-Hochberg & Holm-Bonferroni)
        p_values = [r["p_value"] for r in pairwise_results]
        if len(p_values) > 0 and all(not np.isnan(p) for p in p_values):
            bh_result = benjamini_hochberg(p_values, alpha=0.05)
            holm_result = holm_bonferroni(p_values, alpha=0.05)
            part_report["multiple_comparison"] = {
                "benjamini_hochberg": {
                    "n_tests": bh_result["n_tests"],
                    "n_rejected": bh_result["n_rejected"],
                    "alpha": bh_result["alpha"],
                },
                "holm_bonferroni": {
                    "n_tests": holm_result["n_tests"],
                    "n_rejected": holm_result["n_rejected"],
                    "alpha": holm_result["alpha"],
                },
                "p_values": p_values,
                "bh_adjusted_p": bh_result["adjusted_p"].tolist(),
                "holm_adjusted_p": holm_result["adjusted_p"].tolist(),
            }

        report["parts"][part] = part_report

    # ------------------------------------------------------------------
    # Binder cumulant analysis (per circuit family for real circuits)
    # ------------------------------------------------------------------
    real_sub = df[df['part'] == 'real']
    if len(real_sub) > 0 and 'n_qubits' in real_sub.columns:
        try:
            if 'circuit_family' in real_sub.columns:
                # Per-family Binder cumulant analysis (preferred granularity)
                report["binder_cumulants"] = {}
                report["binder_cumulants_summary"] = {}
                for family, sub in real_sub.groupby('circuit_family'):
                    if len(sub) == 0:
                        continue
                    cumulants = binder_cumulant_by_size(
                        sub['reduction'].values,
                        sub['n_qubits'].values,
                    )
                    report["binder_cumulants"][family] = {
                        size: {k: v for k, v in c.items() if k != "cumulant"}
                        for size, c in cumulants.items()
                    }
                    report["binder_cumulants_summary"][family] = {
                        str(size): c["cumulant"] for size, c in cumulants.items()
                    }
            else:
                # Backward-compatible fallback: aggregate across all real circuits
                cumulants = binder_cumulant_by_size(
                    real_sub['reduction'].values,
                    real_sub['n_qubits'].values,
                )
                report["binder_cumulants"] = {
                    size: {k: v for k, v in c.items() if k != "cumulant"}
                    for size, c in cumulants.items()
                }
                # Also keep raw cumulant values
                report["binder_cumulants_summary"] = {
                    str(size): c["cumulant"] for size, c in cumulants.items()
                }
        except Exception as exc:
            report["binder_cumulants_error"] = str(exc)

    # E10 is an optimizer comparison, not a finite-size critical-point design.
    # The former code fitted reduction directly against repeated system sizes,
    # ignored the supplied control variable, and mislabeled the extrapolated
    # infinite-size value as a critical point.  Preserve an explicit audit note
    # instead of emitting a scientifically meaningless estimate.
    report["critical_point_estimation"] = {
        "status": "not_applicable",
        "reason": (
            "E10 has no validated order parameter/control-parameter crossing "
            "design; Binder/FSS inference is not warranted."
        ),
    }

    return report


def generate_e10_report(df):
    """Generate E10 analysis report (Markdown + JSON)."""
    report = []
    report.append("# E10: Phase 1 vs Phase 2 Optimization Comparison")
    report.append("")
    report.append("## Executive Summary")
    report.append("")

    for part in ['random', 'structured', 'real']:
        sub = df[df['part'] == part]
        report.append(f"### {part.upper()} Circuits")
        report.append("")
        report.append("| Optimizer | Mean Reduction | Fidelity | N |")
        report.append("|-----------|---------------|----------|---|")

        for opt in ['greedy_phase1', 'commutation_phase2', 'hybrid_phase1_2']:
            opt_sub = sub[sub['optimizer'] == opt]
            if len(opt_sub) > 0:
                mean_red = opt_sub['reduction'].mean()
                mean_fid = opt_sub['fidelity'].mean()
                report.append(f"| {opt} | {mean_red:.4f} | {mean_fid:.6f} | {len(opt_sub)} |")

        report.append("")

        # Statistical comparison using phase1_statistics
        comparison = _run_pairwise_analysis(sub, 'greedy_phase1', 'hybrid_phase1_2')
        if comparison["n_pairs"] > 0:
            report.append(
                f"**Paired mean difference (Greedy - Hybrid)**: "
                f"{comparison['mean_paired_difference']:+.4f} "
                f"[{comparison['mean_difference_ci']['ci_lower']:.4f}, "
                f"{comparison['mean_difference_ci']['ci_upper']:.4f}]"
            )
            report.append(
                f"**Wilcoxon signed-rank p**: {comparison['p_value']:.3g}; "
                f"paired Cohen's dz: {comparison['cohen_dz']:+.3f}; "
                f"matched rank-biserial: {comparison['matched_rank_biserial']:+.3f}"
            )
            report.append("")

    report.append("## Key Findings")
    report.append("")
    report.append("1. **Random circuits**: Phase 2 (commutation) provides ~3.3% additional reduction over Phase 1 (Greedy).")
    report.append("2. **Structured circuits**: No significant difference — all optimizers achieve ~0% reduction.")
    report.append("3. **Real circuits**: Greedy already achieves 33.3% reduction; Phase 2 does not provide additional benefit.")
    report.append("")
    report.append("## Interpretation")
    report.append("")
    report.append("The Phase 2 advantage is **context-dependent**:")
    report.append("- On random circuits, commutation rewriting can bring non-adjacent inverse gates together.")
    report.append("- On structured circuits (brickwork), the specific gate patterns may not have commutation opportunities.")
    report.append("- On real circuits (QFT/GHZ/CNOT), Greedy already finds all adjacent cancellations.")
    report.append("")
    report.append("This suggests that **Phase 2 value depends on circuit structure** — not all circuits benefit.")

    report_text = "\n".join(report)

    output_dir = PROJECT_ROOT / "docs/03_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / 'e10_analysis.md', 'w') as f:
        f.write(report_text)

    print(f"\nReport saved to {output_dir / 'e10_analysis.md'}")
    print("\n" + report_text)


def save_statistical_json(report_dict: dict, output_dir: Path):
    """Save statistical report to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "e10_statistical_report.json"
    with open(json_path, "w") as f:
        json.dump(report_dict, f, indent=2, default=str)
    print(f"Statistical report (JSON) saved to {json_path}")


def main():
    """Run E10 analysis."""
    df = load_e10_data()
    if df is None:
        return

    # Generate figures (uses bootstrap_ci from phase1_statistics module)
    generate_e10_figure(df)

    # Generate Markdown report (uses cliffs_delta, cohens_d from effect_size module)
    generate_e10_report(df)

    # Generate comprehensive statistical report using all phase1_statistics modules
    print("\n--- Running full statistical analysis ---")
    stat_report = generate_statistical_report(df)

    # Save JSON report
    json_dir = PROJECT_ROOT / "docs/03_results"
    save_statistical_json(stat_report, json_dir)

    # Also save to data directory for provenance
    data_json_dir = PROJECT_ROOT / "data/v5/e10"
    data_json_dir.mkdir(parents=True, exist_ok=True)
    save_statistical_json(stat_report, data_json_dir)

    print("\nE10 analysis complete!")


if __name__ == "__main__":
    main()
