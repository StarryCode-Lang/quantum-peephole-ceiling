"""
Summarize effect sizes across all experiments.

Reads analysis/figures/fdr_correction_results.csv and writes
analysis/figures/effect_sizes_summary.csv with the key comparisons.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    fdr_path = PROJECT_ROOT / "analysis" / "figures" / "fdr_correction_results.csv"
    output_path = PROJECT_ROOT / "analysis" / "figures" / "effect_sizes_summary.csv"

    if not fdr_path.exists():
        print(f"FDR results not found at {fdr_path}; run analysis/generate_figures.py first.")
        return

    df = pd.read_csv(fdr_path)

    # Keep rows with non-null effect sizes.
    summary = df[df["Cliffs_delta"].notna() | df["Hedges_g"].notna()].copy()
    summary = summary[[
        "Test", "Raw_p_value", "Adjusted_p_value_BH", "Significant_at_0.05",
        "Cliffs_delta", "Cliffs_delta_CI95", "Hedges_g", "Hedges_g_CI95",
        "Effect_size_note",
    ]]

    summary.to_csv(output_path, index=False)
    print(f"Effect-size summary written to {output_path}")
    print(f"  {len(summary)} comparisons with effect sizes")


if __name__ == "__main__":
    main()
