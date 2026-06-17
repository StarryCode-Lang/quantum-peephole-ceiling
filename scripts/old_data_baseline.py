#!/usr/bin/env python3
"""Compute baseline summary statistics for old experiment CSV data.

Reads 10 experiment CSV files, computes per-experiment summary statistics
(total rows, mean/std reduction, mean fidelity, success rate), and
per-group breakdowns where requested.  Saves everything to
D:\\Desktop\\Q-research\\data\\old_baseline_summary.json.
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
OUT_PATH = DATA_ROOT / "old_baseline_summary.json"

SUCCESS_THRESHOLD = 0.20  # reduction >= this counts as success

# ---------------------------------------------------------------------------
# Experiment definitions
# ---------------------------------------------------------------------------
EXPERIMENTS = {
    "E01": {
        "path": DATA_ROOT / "v2_fixed" / "e01" / "e01_phase_transition_v2_20260607_091313.csv",
        "reduction_col": "reduction",
        "fidelity_col": "fidelity",
        "success_col": "success",
    },
    "E02": {
        "path": DATA_ROOT / "v2_fixed" / "e02" / "e02_entanglement_density_v2_20260607_090644.csv",
        "reduction_col": "reduction",
        "fidelity_col": "fidelity",
        "success_col": "success",
    },
    "E03": {
        "path": DATA_ROOT / "v2_fixed" / "e03" / "e03_scaling_v2_20260607_091030.csv",
        "reduction_col": "reduction",
        "fidelity_col": "fidelity",
        "success_col": "success",
    },
    "E04": {
        "path": DATA_ROOT / "v2_fixed" / "e04" / "e04_algorithm_comparison_v2_20260607_092340.csv",
        "reduction_col": "reduction",
        "fidelity_col": "fidelity",
        "success_col": "success",
    },
    "E05": {
        "path": DATA_ROOT / "v2_fixed" / "e05" / "e05_landscape_v2_20260607_091444.csv",
        "reduction_col": "reduction",
        "fidelity_col": "fidelity",
        "success_col": "success",
    },
    "E10": {
        "path": DATA_ROOT / "v3_extended" / "e10" / "e10_phase1_vs_phase2_20260607_090606.csv",
        "reduction_col": "reduction",
        "fidelity_col": "fidelity",
        "success_col": "success",
    },
    "E11": {
        "path": DATA_ROOT / "v4" / "e11" / "e11_real_circuit_benchmark_e11_full_20260609_043144.csv",
        "reduction_col": "reduction",
        "fidelity_col": "fidelity",
        "success_col": "success",
    },
    "E14": {
        "path": DATA_ROOT / "v5" / "e14" / "e14_extended_benchmark_e14_full_20260610_135053.csv",
        "reduction_col": "reduction",
        "fidelity_col": "fidelity",
        "success_col": "success",
    },
    "E16": {
        "path": DATA_ROOT / "v5" / "e16" / "e16_window_scaling_e16_full_20260610_142547.csv",
        "reduction_col": "reduction",
        "fidelity_col": "fidelity",
        "success_col": "success",
    },
    "E18": {
        "path": DATA_ROOT / "v5" / "e18" / "e18_clifford_t_e18_smoke_20260610_075051.csv",
        "reduction_col": "reduction",
        "fidelity_col": "fidelity",
        "success_col": "success",
    },
}


def safe_float(val):
    """Convert numpy types to plain Python float for JSON serialisation."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return round(float(val), 6)


def compute_overall(df: pd.DataFrame, red_col: str, fid_col: str, suc_col: str):
    """Compute overall summary statistics for one experiment."""
    total = len(df)
    red = df[red_col]
    fid = df[fid_col]
    # For success_col, parse string 'True'/'False' if necessary
    if df[suc_col].dtype == object:
        success_vals = df[suc_col].astype(str).str.lower().isin(["true", "1"])
    else:
        success_vals = df[suc_col].astype(bool)

    # Threshold-based success rate (reduction >= 0.20)
    threshold_success = (red >= SUCCESS_THRESHOLD).mean()

    return {
        "total_rows": total,
        "mean_reduction": safe_float(red.mean()),
        "std_reduction": safe_float(red.std()),
        "mean_fidelity": safe_float(fid.mean()),
        "success_rate": safe_float(success_vals.mean()),
        "threshold_success_rate_0.20": safe_float(threshold_success),
        "min_reduction": safe_float(red.min()),
        "max_reduction": safe_float(red.max()),
        "median_reduction": safe_float(red.median()),
    }


def compute_group(df: pd.DataFrame, red_col: str, fid_col: str, suc_col: str,
                  group_cols: list) -> dict:
    """Group-by summary statistics."""
    results = {}
    grouped = df.groupby(group_cols)
    for name, group in grouped:
        if isinstance(name, tuple):
            key = " | ".join(str(n) for n in name)
        else:
            key = str(name)
        results[key] = compute_overall(group, red_col, fid_col, suc_col)
    return results


def main():
    summary = {}

    for exp_name, cfg in EXPERIMENTS.items():
        path = cfg["path"]
        red_col = cfg["reduction_col"]
        fid_col = cfg["fidelity_col"]
        suc_col = cfg["success_col"]

        print(f"Reading {exp_name}: {path}")
        df = pd.read_csv(path)
        print(f"  -> {len(df)} rows, columns: {list(df.columns)}")

        entry = {}
        entry["file"] = str(path.relative_to(DATA_ROOT))
        entry["overall"] = compute_overall(df, red_col, fid_col, suc_col)

        # ---- Per-group breakdowns ----

        # E01: per-depth
        if exp_name == "E01" and "depth" in df.columns:
            entry["per_depth"] = compute_group(df, red_col, fid_col, suc_col, ["depth"])

        # E02: per-density
        if exp_name == "E02" and "entanglement_density" in df.columns:
            entry["per_entanglement_density"] = compute_group(
                df, red_col, fid_col, suc_col, ["entanglement_density"]
            )

        # E04: per-optimizer
        if exp_name == "E04" and "optimizer" in df.columns:
            entry["per_optimizer"] = compute_group(
                df, red_col, fid_col, suc_col, ["optimizer"]
            )

        # E10: per-family, per-optimizer
        if exp_name == "E10":
            if "circuit_family" in df.columns and "optimizer" in df.columns:
                entry["per_family_optimizer"] = compute_group(
                    df, red_col, fid_col, suc_col, ["circuit_family", "optimizer"]
                )

        # E14: per-family, per-optimizer
        if exp_name == "E14":
            if "circuit_family" in df.columns and "optimizer" in df.columns:
                entry["per_family_optimizer"] = compute_group(
                    df, red_col, fid_col, suc_col, ["circuit_family", "optimizer"]
                )

        summary[exp_name] = entry

    # ---- Write JSON ----
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to {OUT_PATH}")

    # ---- Print human-readable summary ----
    print("\n" + "=" * 80)
    print("OLD EXPERIMENT BASELINE SUMMARY")
    print("=" * 80)
    for exp_name, entry in summary.items():
        ov = entry["overall"]
        print(f"\n--- {exp_name} ({entry['file']}) ---")
        print(f"  Total rows             : {ov['total_rows']}")
        print(f"  Mean reduction         : {ov['mean_reduction']}")
        print(f"  Std reduction          : {ov['std_reduction']}")
        print(f"  Mean fidelity          : {ov['mean_fidelity']}")
        print(f"  Success rate           : {ov['success_rate']}")
        print(f"  Threshold success(>=0.20): {ov['threshold_success_rate_0.20']}")
        print(f"  Reduction range        : [{ov['min_reduction']}, {ov['max_reduction']}]")

        for group_key in ["per_depth", "per_entanglement_density", "per_optimizer",
                          "per_family_optimizer"]:
            if group_key in entry:
                print(f"\n  [{group_key}]")
                for gname, gstats in entry[group_key].items():
                    print(f"    {gname}: rows={gstats['total_rows']}, "
                          f"mean_red={gstats['mean_reduction']}, "
                          f"std_red={gstats['std_reduction']}, "
                          f"mean_fid={gstats['mean_fidelity']}, "
                          f"success={gstats['success_rate']}, "
                          f"thresh_success={gstats['threshold_success_rate_0.20']}")


if __name__ == "__main__":
    main()
