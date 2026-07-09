"""
Paired statistical analysis of E21 ceiling-aware vs naive pipeline.

Reads data/v6/e21/ceiling_aware_comparison.csv and writes
    data/v6/e21/e21_paired_statistics.csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def wilcoxon_safe(before, after):
    """Run Wilcoxon signed-rank test, returning NaN if all differences are zero."""
    diff = np.array(before) - np.array(after)
    if np.allclose(diff, 0):
        return float('nan'), float('nan')
    try:
        res = stats.wilcoxon(before, after, alternative='two-sided')
        return float(res.statistic), float(res.pvalue)
    except Exception:
        return float('nan'), float('nan')


def cohens_d(before, after):
    """Paired Cohen's d for runtime comparison."""
    diff = np.array(before) - np.array(after)
    mean_diff = diff.mean()
    std_diff = diff.std(ddof=1)
    if std_diff == 0:
        return 0.0 if mean_diff == 0 else float('inf')
    return float(mean_diff / std_diff)


def analyze():
    csv_path = PROJECT_ROOT / "data/v6/e21/ceiling_aware_comparison.csv"
    df = pd.read_csv(csv_path)

    rows = []
    for (family, n_qubits), group in df.groupby(["family", "n_qubits"]):
        naive = group[group["strategy_name"] == "naive"]
        ca = group[group["strategy_name"] == "ceiling_aware"]
        if len(naive) == 0 or len(ca) == 0:
            continue

        # Align by trial_idx to ensure pairing
        merged = naive.merge(ca, on="trial_idx", suffixes=("_naive", "_ca"))
        if len(merged) == 0:
            continue

        stat, pvalue = wilcoxon_safe(
            merged["total_time_ms_naive"].values,
            merged["total_time_ms_ca"].values,
        )

        rows.append({
            "family": family,
            "n_qubits": n_qubits,
            "n_pairs": len(merged),
            "mean_time_naive_ms": merged["total_time_ms_naive"].mean(),
            "mean_time_ca_ms": merged["total_time_ms_ca"].mean(),
            "speedup": merged["total_time_ms_naive"].mean() / max(merged["total_time_ms_ca"].mean(), 1e-9),
            "wilcoxon_statistic": stat,
            "wilcoxon_pvalue": pvalue,
            "cohens_d_time": cohens_d(
                merged["total_time_ms_naive"].values,
                merged["total_time_ms_ca"].values,
            ),
            "mean_reduction_naive": merged["gate_reduction_naive"].mean(),
            "mean_reduction_ca": merged["gate_reduction_ca"].mean(),
            "reduction_diff": (merged["gate_reduction_naive"] - merged["gate_reduction_ca"]).mean(),
            "mean_fidelity_naive": merged["fidelity_naive"].mean(),
            "mean_fidelity_ca": merged["fidelity_ca"].mean(),
        })

    stats_df = pd.DataFrame(rows)
    out_path = PROJECT_ROOT / "data/v6/e21/e21_paired_statistics.csv"
    stats_df.to_csv(out_path, index=False)

    # Aggregate across all circuits
    all_merged_rows = []
    for _, group in df.groupby(["family", "n_qubits"]):
        naive = group[group["strategy_name"] == "naive"]
        ca = group[group["strategy_name"] == "ceiling_aware"]
        merged = naive.merge(ca, on="trial_idx", suffixes=("_naive", "_ca"))
        all_merged_rows.append(merged)
    all_merged = pd.concat(all_merged_rows, ignore_index=True)

    stat_all, p_all = wilcoxon_safe(
        all_merged["total_time_ms_naive"].values,
        all_merged["total_time_ms_ca"].values,
    )

    summary = {
        "total_pairs": int(len(all_merged)),
        "mean_time_naive_ms": float(all_merged["total_time_ms_naive"].mean()),
        "mean_time_ca_ms": float(all_merged["total_time_ms_ca"].mean()),
        "overall_speedup": float(all_merged["total_time_ms_naive"].mean() / max(all_merged["total_time_ms_ca"].mean(), 1e-9)),
        "wilcoxon_statistic_all": stat_all,
        "wilcoxon_pvalue_all": p_all,
        "mean_reduction_naive": float(all_merged["gate_reduction_naive"].mean()),
        "mean_reduction_ca": float(all_merged["gate_reduction_ca"].mean()),
        "mean_fidelity_naive": float(all_merged["fidelity_naive"].mean()),
        "mean_fidelity_ca": float(all_merged["fidelity_ca"].mean()),
    }

    summary_path = PROJECT_ROOT / "data/v6/e21/e21_paired_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Paired statistics: {out_path}")
    print(f"Overall speedup: {summary['overall_speedup']:.2f}x")
    print(f"Wilcoxon p-value (runtime): {p_all:.2e}")
    return stats_df, summary


if __name__ == "__main__":
    analyze()
