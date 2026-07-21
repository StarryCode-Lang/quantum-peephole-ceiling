"""Fidelity distribution report: full five-number distribution per experiment.

Statistical protocol item 5 (README): "Fidelity Distribution: Full
distribution reported (min, 25%, median, 75%, max)."

The canonical modules (``analysis/phase1_statistics/core.py:fidelity_summary``
and ``fidelity_distribution.py``) implement the statistics, and fig06 plots
histograms, but no script emits the full distribution as a tabular artifact
across all experiments (``statistical_summary.csv`` carries only
``Mean_Fidelity``). This driver closes that reporting gap using the canonical
implementations only.

Usage:
    python analysis/fidelity_distribution_report.py [--out-dir docs/review/wave1/data]

Outputs:
    fidelity_distribution.csv  - one row per experiment with the full
                                 distribution (n, min, q1, median, q3, max,
                                 mean, std, iqr, skewness, kurtosis, missing,
                                 out-of-range counts)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.phase1_statistics.fidelity_distribution import fidelity_summary

DEFAULT_OUT_DIR = PROJECT_ROOT / "docs" / "review" / "wave1" / "data"

CANON = {
    "E1": "data/v2_fixed/e01/e01_phase_transition_v2_20260613_132653.csv",
    "E2": "data/v2_fixed/e02/e02_entanglement_density_v2_20260613_130455.csv",
    "E3": "data/v2_fixed/e03/e03_scaling_v2_20260611_224540.csv",
    "E4": "data/v2_fixed/e04/e04_algorithm_comparison_v2_20260613_132653.csv",
    "E5": "data/v2_fixed/e05/e05_landscape_v2_20260613_130355.csv",
    "E10": "data/v5/e10/e10_expanded_phase1_vs_phase2_20260613_131601.csv",
    "E11": "data/v4/e11/e11_merged_powered.csv",
    "E12": "data/v4/e12/e12_compiler_baseline_e12_full_20260626_000134_nocoupling.csv",
    "E14": "data/v5/e14/e14_extended_benchmark_e14_full_20260611_114726.csv",
    "E15": "data/v5/e15/e15_multi_compiler_e15_full_20260611_150934.csv",
    "E16": "data/v5/e16/e16_window_scaling_e16_full_20260610_142547.csv",
    "E17": "data/v5/e17/e17_connectivity_e17_full_20260610_150935.csv",
    "E18": "data/v5/e18/e18_clifford_t_e18_full_20260610_052140.csv",
    "E19": "data/v6/e19/e19_wcl_listing_full_e19_full_20260620_123825.csv",
    "E23": "data/v7/e23",
    "E24": "data/v7/e24/e24_theorem7_results.csv",
}


def _load(exp: str, rel: str) -> pd.DataFrame | None:
    path = PROJECT_ROOT / rel
    if path.is_dir():
        csvs = sorted(path.glob("*.csv"))
        if not csvs:
            return None
        path = csvs[-1]
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if "fidelity" not in df.columns:
        return None
    return df


def main() -> int:
    parser = argparse.ArgumentParser(description="Fidelity distribution report (protocol item 5).")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for exp, rel in CANON.items():
        df = _load(exp, rel)
        if df is None:
            rows.append({"experiment": exp, "error": "no fidelity column or missing data"})
            continue
        s = fidelity_summary(df, "fidelity")
        fid = pd.to_numeric(df["fidelity"], errors="coerce")
        s.update({
            "experiment": exp,
            "source": rel,
            "n_below_0.999999": int((fid < 0.999999).sum()),
            "n_below_0.99": int((fid < 0.99).sum()),
            "n_equal_0": int((fid == 0).sum()),
            "n_out_of_range": int(((fid < 0) | (fid > 1)).sum()),
        })
        rows.append(s)

    out = pd.DataFrame(rows)
    cols = ["experiment", "source", "n", "min", "q1", "median", "q3", "max",
            "mean", "std", "iqr", "skewness", "kurtosis", "missing",
            "n_below_0.999999", "n_below_0.99", "n_equal_0", "n_out_of_range"]
    cols = [c for c in cols if c in out.columns] + [c for c in out.columns if c not in cols]
    out = out[cols]

    tmp = out_dir / "fidelity_distribution.csv.tmp"
    out.to_csv(tmp, index=False, float_format="%.8f")
    os.replace(tmp, out_dir / "fidelity_distribution.csv")

    pd.set_option("display.width", 220)
    show = [c for c in ["experiment", "n", "min", "q1", "median", "q3", "max",
                        "mean", "n_equal_0", "n_below_0.99"] if c in out.columns]
    print(out[show].to_string(index=False))
    print(f"\nWrote {out_dir / 'fidelity_distribution.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
