"""
PHASE-4 Stage 2: Old vs New Comparison Analysis
================================================
Compares old baseline data with new rerun results for all experiments.
Outputs comparison tables and summary statistics.
"""

from __future__ import annotations
import sys
import json
import os
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"

# ============================================================
# 1. Define new data files (latest rerun for each experiment)
# ============================================================

NEW_DATA_FILES = {
    "E01": DATA_DIR / "v2_fixed/e01/e01_phase_transition_v2_20260611_195450.csv",
    "E02": DATA_DIR / "v2_fixed/e02/e02_entanglement_density_v2_20260611_191816.csv",
    "E04": DATA_DIR / "v2_fixed/e04/e04_algorithm_comparison_v2_20260611_194858.csv",
    "E05": DATA_DIR / "v2_fixed/e05/e05_landscape_v2_20260611_191723.csv",
    "E10": DATA_DIR / "v3_extended/e10/e10_phase1_vs_phase2_20260611_191634.csv",
    "E11": DATA_DIR / "v4/e11/e11_real_circuit_benchmark_e11_smoke_20260611_112720.csv",
    "E12": DATA_DIR / "v4/e12/e12_compiler_baseline_e12_smoke_20260611_114801.csv",
    "E13": DATA_DIR / "v4/e13/e13_structural_ceiling_e13_smoke_20260611_113526.csv",
    "E14": DATA_DIR / "v5/e14/e14_extended_benchmark_e14_smoke_20260611_113330.csv",
    "E16": DATA_DIR / "v5/e16/e16_window_scaling_e16_smoke_20260611_114805.csv",
    "E18": DATA_DIR / "v5/e18/e18_clifford_t_e18_smoke_20260611_114802.csv",
}

# Also check for E03 (may still be running)
E03_DIR = DATA_DIR / "v2_fixed/e03"
e03_files = sorted(E03_DIR.glob("e03_scaling_v2_2026061*.csv"))
if e03_files:
    NEW_DATA_FILES["E03"] = e03_files[-1]

# Old data files
OLD_DATA_FILES = {
    "E01": DATA_DIR / "v2_fixed/e01/e01_phase_transition_v2_20260607_091313.csv",
    "E02": DATA_DIR / "v2_fixed/e02/e02_entanglement_density_v2_20260607_090644.csv",
    "E03": DATA_DIR / "v2_fixed/e03/e03_scaling_v2_20260607_091030.csv",
    "E04": DATA_DIR / "v2_fixed/e04/e04_algorithm_comparison_v2_20260607_092340.csv",
    "E05": DATA_DIR / "v2_fixed/e05/e05_landscape_v2_20260607_091444.csv",
    "E10": DATA_DIR / "v3_extended/e10/e10_phase1_vs_phase2_20260607_090606.csv",
    "E11": DATA_DIR / "v4/e11/e11_real_circuit_benchmark_e11_full_20260609_043144.csv",
    "E14": DATA_DIR / "v5/e14/e14_extended_benchmark_e14_full_20260610_135053.csv",
    "E16": DATA_DIR / "v5/e16/e16_window_scaling_e16_full_20260610_142547.csv",
    "E18": DATA_DIR / "v5/e18/e18_clifford_t_e18_smoke_20260610_075051.csv",
}

# Also look for old E12, E13, E15, E17
for eid, pattern, subdir in [
    ("E12", "e12_compiler_baseline_e12_*_*.csv", "v4/e12"),
    ("E13", "e13_structural_ceiling_e13_*_*.csv", "v4/e13"),
    ("E15", "e15_multi_compiler_e15_*_*.csv", "v5/e15"),
    ("E17", "e17_connectivity_e17_*_*.csv", "v5/e17"),
]:
    d = DATA_DIR / subdir
    files = sorted(d.glob(pattern))
    if files:
        OLD_DATA_FILES[eid] = files[-1]


def compute_summary(df: pd.DataFrame, group_cols=None) -> dict:
    """Compute summary statistics for a dataframe."""
    result = {"total_rows": len(df)}
    
    if "reduction" in df.columns:
        result["mean_reduction"] = float(df["reduction"].mean())
        result["std_reduction"] = float(df["reduction"].std()) if len(df) > 1 else 0.0
        result["median_reduction"] = float(df["reduction"].median())
        result["min_reduction"] = float(df["reduction"].min())
        result["max_reduction"] = float(df["reduction"].max())
    
    if "fidelity" in df.columns:
        result["mean_fidelity"] = float(df["fidelity"].mean())
    
    if "success" in df.columns:
        result["success_rate"] = float(df["success"].mean())
    elif "reduction" in df.columns:
        result["success_rate"] = float((df["reduction"] > 0.20).mean())
    
    if group_cols:
        available_groups = [c for c in group_cols if c in df.columns]
        if available_groups:
            grouped = df.groupby(available_groups)
            per_group = {}
            for name, group_df in grouped:
                key = str(name) if not isinstance(name, tuple) else " | ".join(str(n) for n in name)
                per_group[key] = compute_summary(group_df)
            result["per_group"] = per_group
    
    return result


def main():
    print("=" * 80)
    print("PHASE-4 SCIENTIFIC REVALIDATION: Old vs New Comparison")
    print(f"Generated: {datetime.now().isoformat()}")
    print("=" * 80)
    
    all_results = {}
    comparison_rows = []
    
    for eid in sorted(set(list(NEW_DATA_FILES.keys()) + list(OLD_DATA_FILES.keys()))):
        old_path = OLD_DATA_FILES.get(eid)
        new_path = NEW_DATA_FILES.get(eid)
        
        print(f"\n{'='*60}")
        print(f"EXPERIMENT {eid}")
        print(f"{'='*60}")
        
        old_summary = None
        new_summary = None
        
        # Determine group columns based on experiment type
        group_cols_map = {
            "E01": ["depth"],
            "E02": ["entanglement_density"],
            "E03": ["n_qubits"],
            "E04": ["optimizer"],
            "E05": ["n_qubits", "depth"],
            "E10": ["circuit_type", "optimizer"],
            "E11": ["circuit_family", "optimizer"],
            "E12": ["compiler", "optimizer"],
            "E13": ["circuit_family"],
            "E14": ["circuit_family", "optimizer"],
            "E15": ["compiler", "optimizer"],
            "E16": ["optimizer", "window_size"],
            "E17": ["topology", "optimizer"],
            "E18": ["optimizer"],
        }

        # Read old data
        if old_path and old_path.exists():
            try:
                old_df = pd.read_csv(old_path)
                group_cols = group_cols_map.get(eid)
                old_summary = compute_summary(old_df, group_cols)
                print(f"  OLD: {old_path.name}")
                print(f"    Rows: {old_summary['total_rows']}, "
                      f"Mean reduction: {old_summary.get('mean_reduction', 'N/A'):.6f}, "
                      f"Success: {old_summary.get('success_rate', 'N/A'):.2%}")
            except Exception as e:
                print(f"  OLD: Error reading {old_path.name}: {e}")
        
        # Read new data
        if new_path and new_path.exists():
            try:
                new_df = pd.read_csv(new_path)
                group_cols = group_cols_map.get(eid)
                new_summary = compute_summary(new_df, group_cols)
                print(f"  NEW: {new_path.name}")
                print(f"    Rows: {new_summary['total_rows']}, "
                      f"Mean reduction: {new_summary.get('mean_reduction', 'N/A'):.6f}, "
                      f"Success: {new_summary.get('success_rate', 'N/A'):.2%}")
            except Exception as e:
                print(f"  NEW: Error reading {new_path.name}: {e}")
        
        # Comparison
        if old_summary and new_summary:
            old_mean = old_summary.get("mean_reduction", 0)
            new_mean = new_summary.get("mean_reduction", 0)
            delta = new_mean - old_mean
            pct_change = (delta / abs(old_mean) * 100) if old_mean != 0 else (float("inf") if delta != 0 else 0)
            
            old_sr = old_summary.get("success_rate", 0)
            new_sr = new_summary.get("success_rate", 0)
            
            verdict = "UNCHANGED" if abs(delta) < 1e-8 else ("IMPROVED" if delta > 0 else "DEGRADED")
            
            comparison_rows.append({
                "experiment": eid,
                "old_rows": old_summary["total_rows"],
                "new_rows": new_summary["total_rows"],
                "old_mean_reduction": old_mean,
                "new_mean_reduction": new_mean,
                "delta": delta,
                "pct_change": pct_change,
                "old_success_rate": old_sr,
                "new_success_rate": new_sr,
                "verdict": verdict,
            })
            
            print(f"\n  COMPARISON:")
            print(f"    Delta: {delta:+.6f} ({pct_change:+.2f}%)")
            print(f"    Success rate: {old_sr:.2%} -> {new_sr:.2%}")
            print(f"    Verdict: {verdict}")
            
            # Show per-group comparison if available
            if "per_group" in old_summary and "per_group" in new_summary:
                old_groups = old_summary["per_group"]
                new_groups = new_summary["per_group"]
                all_groups = sorted(set(list(old_groups.keys()) + list(new_groups.keys())))
                
                print(f"\n  PER-GROUP BREAKDOWN:")
                print(f"    {'Group':<40} {'Old Mean':>10} {'New Mean':>10} {'Delta':>10}")
                print(f"    {'-'*70}")
                for g in all_groups:
                    og = old_groups.get(g, {})
                    ng = new_groups.get(g, {})
                    om = og.get("mean_reduction", float("nan"))
                    nm = ng.get("mean_reduction", float("nan"))
                    d = nm - om if not (np.isnan(om) or np.isnan(nm)) else float("nan")
                    print(f"    {g:<40} {om:>10.6f} {nm:>10.6f} {d:>+10.6f}")
        else:
            status = "NEW DATA MISSING" if not new_summary else "OLD DATA MISSING"
            print(f"  STATUS: {status}")
            comparison_rows.append({
                "experiment": eid,
                "old_rows": old_summary["total_rows"] if old_summary else "N/A",
                "new_rows": new_summary["total_rows"] if new_summary else "N/A",
                "old_mean_reduction": old_summary.get("mean_reduction", "N/A") if old_summary else "N/A",
                "new_mean_reduction": new_summary.get("mean_reduction", "N/A") if new_summary else "N/A",
                "delta": "N/A",
                "pct_change": "N/A",
                "old_success_rate": old_summary.get("success_rate", "N/A") if old_summary else "N/A",
                "new_success_rate": new_summary.get("success_rate", "N/A") if new_summary else "N/A",
                "verdict": status,
            })
        
        all_results[eid] = {
            "old": old_summary,
            "new": new_summary,
        }
    
    # ============================================================
    # SUMMARY TABLE
    # ============================================================
    print("\n" + "=" * 80)
    print("SUMMARY COMPARISON TABLE")
    print("=" * 80)
    print(f"{'Exp':<6} {'Old Rows':>8} {'New Rows':>8} {'Old Mean':>10} {'New Mean':>10} {'Delta':>10} {'Old SR':>8} {'New SR':>8} {'Verdict':<15}")
    print("-" * 95)
    for row in comparison_rows:
        old_mr = row["old_mean_reduction"]
        new_mr = row["new_mean_reduction"]
        delta = row["delta"]
        old_sr = row["old_success_rate"]
        new_sr = row["new_success_rate"]
        
        old_mr_s = f"{old_mr:.4f}" if isinstance(old_mr, float) else str(old_mr)
        new_mr_s = f"{new_mr:.4f}" if isinstance(new_mr, float) else str(new_mr)
        delta_s = f"{delta:+.4f}" if isinstance(delta, float) else str(delta)
        old_sr_s = f"{old_sr:.1%}" if isinstance(old_sr, float) else str(old_sr)
        new_sr_s = f"{new_sr:.1%}" if isinstance(new_sr, float) else str(new_sr)
        
        print(f"{row['experiment']:<6} {str(row['old_rows']):>8} {str(row['new_rows']):>8} "
              f"{old_mr_s:>10} {new_mr_s:>10} {delta_s:>10} {old_sr_s:>8} {new_sr_s:>8} {row['verdict']:<15}")
    
    # ============================================================
    # CRITICAL FINDINGS
    # ============================================================
    print("\n" + "=" * 80)
    print("CRITICAL FINDINGS")
    print("=" * 80)
    
    improved = [r for r in comparison_rows if r["verdict"] == "IMPROVED"]
    degraded = [r for r in comparison_rows if r["verdict"] == "DEGRADED"]
    unchanged = [r for r in comparison_rows if r["verdict"] == "UNCHANGED"]
    missing = [r for r in comparison_rows if "MISSING" in r["verdict"]]
    
    print(f"\n  IMPROVED results: {len(improved)}")
    for r in improved:
        print(f"    {r['experiment']}: {r['old_mean_reduction']:.6f} -> {r['new_mean_reduction']:.6f} "
              f"(+{r['delta']:.6f})")
    
    print(f"\n  DEGRADED results: {len(degraded)}")
    for r in degraded:
        print(f"    {r['experiment']}: {r['old_mean_reduction']:.6f} -> {r['new_mean_reduction']:.6f} "
              f"({r['delta']:.6f})")
    
    print(f"\n  UNCHANGED results: {len(unchanged)}")
    for r in unchanged:
        print(f"    {r['experiment']}: {r['old_mean_reduction']:.6f} (no change)")
    
    print(f"\n  MISSING data: {len(missing)}")
    for r in missing:
        print(f"    {r['experiment']}: {r['verdict']}")
    
    # Save results
    output = {
        "generated": datetime.now().isoformat(),
        "experiments": all_results,
        "comparison": comparison_rows,
    }
    
    output_path = DATA_DIR / "phase4_comparison.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
