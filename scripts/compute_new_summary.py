"""
Compute summary statistics for new experiment data files and write to new_results_summary.json.
"""
import json
import os
import sys
from pathlib import Path

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("ERROR: pandas and numpy are required. Install with: pip install pandas numpy")
    sys.exit(1)

BASE_DIR = str(Path(__file__).resolve().parents[1] / "data")

def compute_stats(df, group_col, experiment_name):
    """Compute per-group and overall statistics for a dataframe."""
    result = {}
    
    # Overall stats
    overall = {}
    overall["total_rows"] = int(len(df))
    overall["mean_reduction"] = float(df["reduction"].mean())
    overall["std_reduction"] = float(df["reduction"].std()) if len(df) > 1 else 0.0
    overall["mean_fidelity"] = float(df["fidelity"].mean())
    
    # Success rate: use 'success' column if boolean, else reduction > 0.20
    if "success" in df.columns and df["success"].dtype in [bool, "bool"]:
        overall["success_rate"] = float(df["success"].mean())
    else:
        overall["success_rate"] = float((df["reduction"] > 0.20).mean())
    
    overall["threshold_success_rate_0.20"] = float((df["reduction"] > 0.20).mean())
    overall["min_reduction"] = float(df["reduction"].min())
    overall["max_reduction"] = float(df["reduction"].max())
    overall["median_reduction"] = float(df["reduction"].median())
    
    result["overall"] = overall
    
    # Per-group stats
    if group_col and group_col in df.columns:
        per_group = {}
        for name, group in df.groupby(group_col):
            g = {}
            g["total_rows"] = int(len(group))
            g["mean_reduction"] = float(group["reduction"].mean())
            g["std_reduction"] = float(group["reduction"].std()) if len(group) > 1 else 0.0
            g["mean_fidelity"] = float(group["fidelity"].mean())
            
            if "success" in group.columns and group["success"].dtype in [bool, "bool"]:
                g["success_rate"] = float(group["success"].mean())
            else:
                g["success_rate"] = float((group["reduction"] > 0.20).mean())
            
            g["threshold_success_rate_0.20"] = float((group["reduction"] > 0.20).mean())
            g["min_reduction"] = float(group["reduction"].min())
            g["max_reduction"] = float(group["reduction"].max())
            g["median_reduction"] = float(group["reduction"].median())
            
            per_group[str(name)] = g
        
        result[f"per_{group_col}"] = per_group
    
    return result


def main():
    summary = {}
    
    # ===== E01 - Phase Transition =====
    print("Processing E01 - Phase Transition...")
    e01_path = os.path.join(BASE_DIR, "v2_fixed", "e01", "e01_phase_transition_v2_20260611_195450.csv")
    df_e01 = pd.read_csv(e01_path)
    summary["E01"] = compute_stats(df_e01, "depth", "E01")
    summary["E01"]["file"] = os.path.basename(e01_path)
    print(f"  Total rows: {summary['E01']['overall']['total_rows']}")
    print(f"  Groups (depth): {len(summary['E01'].get('per_depth', {}))}")
    
    # ===== E02 - Entanglement Density =====
    print("Processing E02 - Entanglement Density...")
    e02_path = os.path.join(BASE_DIR, "v2_fixed", "e02", "e02_entanglement_density_v2_20260611_191816.csv")
    df_e02 = pd.read_csv(e02_path)
    summary["E02"] = compute_stats(df_e02, "entanglement_density", "E02")
    summary["E02"]["file"] = os.path.basename(e02_path)
    print(f"  Total rows: {summary['E02']['overall']['total_rows']}")
    print(f"  Groups (entanglement_density): {len(summary['E02'].get('per_entanglement_density', {}))}")
    
    # ===== E04 - Algorithm Comparison =====
    print("Processing E04 - Algorithm Comparison...")
    e04_path = os.path.join(BASE_DIR, "v2_fixed", "e04", "e04_algorithm_comparison_v2_20260611_194858.csv")
    df_e04 = pd.read_csv(e04_path)
    summary["E04"] = compute_stats(df_e04, "optimizer", "E04")
    summary["E04"]["file"] = os.path.basename(e04_path)
    print(f"  Total rows: {summary['E04']['overall']['total_rows']}")
    print(f"  Groups (optimizer): {len(summary['E04'].get('per_optimizer', {}))}")
    
    # ===== E05 - Landscape =====
    print("Processing E05 - Landscape...")
    e05_path = os.path.join(BASE_DIR, "v2_fixed", "e05", "e05_landscape_v2_20260611_191723.csv")
    df_e05 = pd.read_csv(e05_path)
    summary["E05"] = compute_stats(df_e05, "circuit_id", "E05")
    summary["E05"]["file"] = os.path.basename(e05_path)
    print(f"  Total rows: {summary['E05']['overall']['total_rows']}")
    print(f"  Groups (circuit_id): {len(summary['E05'].get('per_circuit_id', {}))}")
    
    # ===== E10 - Phase1 vs Phase2 =====
    print("Processing E10 - Phase1 vs Phase2...")
    e10_path = os.path.join(BASE_DIR, "v3_extended", "e10", "e10_phase1_vs_phase2_20260611_191634.csv")
    df_e10 = pd.read_csv(e10_path)
    
    # Create combined family+optimizer group key
    df_e10["family_optimizer"] = df_e10["circuit_family"] + " | " + df_e10["optimizer"]
    summary["E10"] = compute_stats(df_e10, "family_optimizer", "E10")
    summary["E10"]["file"] = os.path.basename(e10_path)
    print(f"  Total rows: {summary['E10']['overall']['total_rows']}")
    print(f"  Groups (family_optimizer): {len(summary['E10'].get('per_family_optimizer', {}))}")
    
    # ===== E12 - Compiler Baseline =====
    print("Processing E12 - Compiler Baseline...")
    e12_path = os.path.join(BASE_DIR, "v4", "e12", "e12_compiler_baseline_e12_smoke_20260611_114801.csv")
    df_e12 = pd.read_csv(e12_path)
    summary["E12"] = compute_stats(df_e12, "circuit_family", "E12")
    summary["E12"]["file"] = os.path.basename(e12_path)
    print(f"  Total rows: {summary['E12']['overall']['total_rows']}")
    print(f"  Groups (circuit_family): {len(summary['E12'].get('per_circuit_family', {}))}")
    
    # ===== E13 - Structural Ceiling =====
    print("Processing E13 - Structural Ceiling...")
    e13_path = os.path.join(BASE_DIR, "v4", "e13", "e13_structural_ceiling_e13_smoke_20260611_113526.csv")
    df_e13 = pd.read_csv(e13_path)
    
    # E13 uses observed_best_reduction as the reduction metric
    # Rename for consistency
    df_e13["reduction"] = df_e13["observed_best_reduction"]
    # bug #16 fix: E13 has no fidelity column. Do NOT assume fidelity=1.0
    # (that would mask any functionality-preservation failures). Record NaN
    # instead and exclude these rows from fidelity aggregates below.
    df_e13["fidelity"] = np.nan
    df_e13["success"] = df_e13["reduction"] > 0.0

    summary["E13"] = {}
    summary["E13"]["file"] = os.path.basename(e13_path)
    # Fidelity aggregation: use nanmean over non-missing entries; report how
    # many rows were excluded due to missing fidelity (bug #16 fix).
    _e13_fid_valid = df_e13["fidelity"].notna()
    _e13_fid_n_valid = int(_e13_fid_valid.sum())
    _e13_fid_n_excluded = int(len(df_e13) - _e13_fid_n_valid)
    _e13_mean_fid = float(df_e13["fidelity"].mean()) if _e13_fid_n_valid > 0 else float("nan")
    summary["E13"]["overall"] = {
        "total_rows": int(len(df_e13)),
        "mean_reduction": float(df_e13["reduction"].mean()),
        "std_reduction": float(df_e13["reduction"].std()) if len(df_e13) > 1 else 0.0,
        "mean_fidelity": _e13_mean_fid,
        "fidelity_note": (f"n={_e13_fid_n_excluded} excluded due to missing fidelity"
                          if _e13_fid_n_excluded > 0 else "all rows have fidelity"),
        "success_rate": float(df_e13["success"].mean()),
        "threshold_success_rate_0.20": float((df_e13["reduction"] > 0.20).mean()),
        "min_reduction": float(df_e13["reduction"].min()),
        "max_reduction": float(df_e13["reduction"].max()),
        "median_reduction": float(df_e13["reduction"].median()),
    }

    # Per circuit family
    per_cf = {}
    for name, group in df_e13.groupby("circuit_family"):
        _g_valid = group["fidelity"].notna()
        _g_n_valid = int(_g_valid.sum())
        _g_n_excluded = int(len(group) - _g_n_valid)
        _g_mean_fid = float(group["fidelity"].mean()) if _g_n_valid > 0 else float("nan")
        per_cf[str(name)] = {
            "total_rows": int(len(group)),
            "mean_reduction": float(group["reduction"].mean()),
            "std_reduction": float(group["reduction"].std()) if len(group) > 1 else 0.0,
            "mean_fidelity": _g_mean_fid,
            "fidelity_note": (f"n={_g_n_excluded} excluded due to missing fidelity"
                              if _g_n_excluded > 0 else "all rows have fidelity"),
            "success_rate": float(group["success"].mean()),
            "threshold_success_rate_0.20": float((group["reduction"] > 0.20).mean()),
            "min_reduction": float(group["reduction"].min()),
            "max_reduction": float(group["reduction"].max()),
            "median_reduction": float(group["reduction"].median()),
        }
    summary["E13"]["per_circuit_family"] = per_cf
    print(f"  Total rows: {summary['E13']['overall']['total_rows']}")
    print(f"  Groups (circuit_family): {len(summary['E13']['per_circuit_family'])}")
    
    # ===== E16 - Window Scaling =====
    print("Processing E16 - Window Scaling...")
    e16_path = os.path.join(BASE_DIR, "v5", "e16", "e16_window_scaling_e16_smoke_20260611_114805.csv")
    df_e16 = pd.read_csv(e16_path)
    summary["E16"] = compute_stats(df_e16, "window_size", "E16")
    summary["E16"]["file"] = os.path.basename(e16_path)
    print(f"  Total rows: {summary['E16']['overall']['total_rows']}")
    print(f"  Groups (window_size): {len(summary['E16'].get('per_window_size', {}))}")
    
    # Write output
    output_path = os.path.join(BASE_DIR, "new_results_summary.json")
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nSummary written to: {output_path}")
    print(f"Experiments processed: {list(summary.keys())}")
    
    return summary


if __name__ == "__main__":
    main()
