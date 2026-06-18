"""
Phase 5: Comprehensive Feature Extraction from ALL Available Experiment Data
============================================================================
Reads all 12 CSV files, computes detailed statistics per circuit family,
generates pivot tables, structural ceiling analysis, correlational analysis,
and identifies zero-reduction families.

Output: <project_root>/analysis/phase5_data_profile.json
"""

import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from collections import OrderedDict
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────
# 0. Configuration
# ──────────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = str(Path(__file__).parent.parent.resolve())
DATA_ROOT = os.path.join(_PROJECT_ROOT, "data")
OUTPUT_PATH = os.path.join(_PROJECT_ROOT, "analysis", "phase5_data_profile.json")

REDUCTION_THRESHOLD = 0.20   # success rate threshold


def _latest_csv(directory: str, prefix: str) -> str:
    """Dynamically resolve the latest CSV in ``directory`` whose name starts
    with ``prefix``. Prefers ``_full_`` runs over ``_smoke_`` runs so the
    script does not break when fresh timestamped data files are generated.
    """
    dirp = Path(directory)
    candidates = sorted(dirp.glob(f"{prefix}*.csv"))
    if not candidates:
        return os.path.join(directory, f"{prefix}_NOT_FOUND.csv")
    full_runs = [f for f in candidates if "_full_" in f.name]
    return str((full_runs or candidates)[-1])


# File manifest — paths resolved dynamically via _latest_csv() so that newly
# generated timestamped data files are picked up automatically.
FILES = OrderedDict([
    ("E01", {
        "path": _latest_csv(os.path.join(DATA_ROOT, "v2_fixed", "e01"), "e01_phase_transition_v2"),
        "version": "v2_fixed", "desc": "Phase Transition"
    }),
    ("E02", {
        "path": _latest_csv(os.path.join(DATA_ROOT, "v2_fixed", "e02"), "e02_entanglement_density_v2"),
        "version": "v2_fixed", "desc": "Entanglement Density"
    }),
    ("E03_old", {
        "path": _latest_csv(os.path.join(DATA_ROOT, "v2_fixed", "e03"), "e03_scaling_v2"),
        "version": "v2_fixed (pre-fix)", "desc": "Scaling (OLD - pre-fix)"
    }),
    ("E04", {
        "path": _latest_csv(os.path.join(DATA_ROOT, "v2_fixed", "e04"), "e04_algorithm_comparison_v2"),
        "version": "v2_fixed", "desc": "Algorithm Comparison"
    }),
    ("E05", {
        "path": _latest_csv(os.path.join(DATA_ROOT, "v2_fixed", "e05"), "e05_landscape_v2"),
        "version": "v2_fixed", "desc": "Landscape"
    }),
    ("E10", {
        "path": _latest_csv(os.path.join(DATA_ROOT, "v3_extended", "e10"), "e10_phase1_vs_phase2"),
        "version": "v3_extended", "desc": "Phase1 vs Phase2"
    }),
    ("E11", {
        "path": _latest_csv(os.path.join(DATA_ROOT, "v4", "e11"), "e11_real_circuit_benchmark_e11_full"),
        "version": "v4", "desc": "Real Circuit Benchmark"
    }),
    ("E13", {
        "path": _latest_csv(os.path.join(DATA_ROOT, "v4", "e13"), "e13_structural_ceiling_e13_full"),
        "version": "v4", "desc": "Structural Ceiling"
    }),
    ("E14", {
        "path": _latest_csv(os.path.join(DATA_ROOT, "v5", "e14"), "e14_extended_benchmark_e14_full"),
        "version": "v5", "desc": "Extended Benchmark"
    }),
    ("E16", {
        "path": _latest_csv(os.path.join(DATA_ROOT, "v5", "e16"), "e16_window_scaling_e16_full"),
        "version": "v5", "desc": "Window Scaling"
    }),
    ("E17", {
        "path": _latest_csv(os.path.join(DATA_ROOT, "v5", "e17"), "e17_connectivity_e17_full"),
        "version": "v5", "desc": "Connectivity"
    }),
    ("E18", {
        "path": _latest_csv(os.path.join(DATA_ROOT, "v5", "e18"), "e18_clifford_t_e18_full"),
        "version": "v5", "desc": "Clifford+T"
    }),
])

# ──────────────────────────────────────────────────────────────────────────
# 1. Read all CSV files
# ──────────────────────────────────────────────────────────────────────────
print("=" * 90)
print("PHASE 5: COMPREHENSIVE FEATURE EXTRACTION")
print("=" * 90)

dfs = OrderedDict()
for key, info in FILES.items():
    try:
        df = pd.read_csv(info["path"])
        dfs[key] = df
        print(f"\n[{key}] {info['desc']} ({info['version']})")
        print(f"  Path:     {info['path']}")
        print(f"  Rows:     {len(df)}")
        print(f"  Columns:  {len(df.columns)}")
        print(f"  Columns:  {list(df.columns)}")
    except Exception as e:
        print(f"\n[{key}] ERROR reading {info['path']}: {e}")

print(f"\nTotal experiments loaded: {len(dfs)}")

# ──────────────────────────────────────────────────────────────────────────
# 2. Normalise column names across experiments for unified analysis
# ──────────────────────────────────────────────────────────────────────────
# Map heterogeneous column names to canonical names
COLUMN_MAP = {
    "gate_count": "gate_count",
    "gate_count_total": "gate_count",
    "original_size": "original_size",
    "baseline_gate_count": "original_size",
    "optimized_size": "optimized_size",
    "optimized_gate_count": "optimized_size",
    "entanglement_entropy": "entanglement_entropy",
    "normalized_entropy": "normalized_entropy",
    "n_qubits": "n_qubits",
    "depth": "depth",
    "reduction": "reduction",
    "fidelity": "fidelity",
    "success": "success",
    "runtime_seconds": "runtime_seconds",
    "circuit_family": "circuit_family",
    "circuit_type": "circuit_type",
    "optimizer": "optimizer",
    "entanglement_density": "entanglement_density",
}

# Canonical numeric features we want for correlation analysis
NUMERIC_FEATURES = [
    "n_qubits", "depth", "gate_count", "entanglement_entropy",
    "normalized_entropy", "original_size", "optimized_size",
    "entanglement_density", "gate_count_total", "gate_count_1q",
    "gate_count_2q", "gate_count_multiq", "baseline_gate_count",
    "optimized_gate_count", "window_size", "n_edges",
    "baseline_t_count", "optimized_t_count",
]

# ──────────────────────────────────────────────────────────────────────────
# 3. Per-file column listing (detailed)
# ──────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("SECTION 1: COLUMNS PER FILE")
print("=" * 90)

file_columns = {}
for key, df in dfs.items():
    print(f"\n--- {key} ---")
    cols = list(df.columns)
    dtypes = {c: str(df[c].dtype) for c in cols}
    file_columns[key] = {"columns": cols, "dtypes": dtypes}
    for c in cols:
        n_unique = df[c].nunique()
        n_null = df[c].isnull().sum()
        print(f"  {c:40s}  dtype={str(df[c].dtype):10s}  unique={n_unique:<6d}  nulls={n_null}")

# ──────────────────────────────────────────────────────────────────────────
# 4. Determine circuit_family availability and assign families
# ──────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("SECTION 2: CIRCUIT FAMILY AVAILABILITY PER EXPERIMENT")
print("=" * 90)

family_availability = {}
for key, df in dfs.items():
    if "circuit_family" in df.columns:
        families = sorted(df["circuit_family"].dropna().unique().tolist())
        has_family = True
    else:
        # For experiments without circuit_family, we use experiment key as pseudo-family
        families = [f"_{key}_synthetic"]
        has_family = False
    family_availability[key] = {"has_circuit_family": has_family, "families": families}
    print(f"  {key}: has_circuit_family={has_family}, families={families}")

# ──────────────────────────────────────────────────────────────────────────
# 5. Build a unified DataFrame with circuit_family tag
# ──────────────────────────────────────────────────────────────────────────
# We add experiment_id and circuit_family columns for cross-experiment grouping
unified_frames = []
for key, df in dfs.items():
    d = df.copy()
    d["_experiment"] = key
    if "circuit_family" not in d.columns:
        d["circuit_family"] = f"_{key}_synthetic"
    # Ensure reduction is numeric
    if "reduction" in d.columns:
        d["reduction"] = pd.to_numeric(d["reduction"], errors="coerce")
    unified_frames.append(d)

# We cannot simply concat because columns differ; we use a subset of common columns
# for the unified analysis
common_cols = ["_experiment", "circuit_family", "n_qubits", "depth", "reduction", "fidelity"]
# Add optional columns if they exist
all_optional = [
    "gate_count", "gate_count_total", "original_size", "baseline_gate_count",
    "optimized_size", "optimized_gate_count", "entanglement_entropy",
    "normalized_entropy", "success", "runtime_seconds", "optimizer",
    "circuit_type", "entanglement_density", "window_size", "n_edges",
    "baseline_t_count", "optimized_t_count", "topology", "gate_set",
]

# Collect union of all optional columns that exist in at least one frame
available_optional = set()
for d in unified_frames:
    available_optional.update(set(d.columns) & set(all_optional))

# For concat, we only use common + available optional
concat_cols = list(set(common_cols) | available_optional)
trimmed = [d[[c for c in concat_cols if c in d.columns]] for d in unified_frames]
unified = pd.concat(trimmed, ignore_index=True, sort=False)

# Normalise gate_count: pick the first available of gate_count, gate_count_total, baseline_gate_count
for col in ["gate_count", "gate_count_total", "baseline_gate_count"]:
    if col in unified.columns:
        unified["gate_count_unified"] = unified["gate_count_unified"] if "gate_count_unified" in unified.columns else pd.NA
        mask = unified["gate_count_unified"].isna() if "gate_count_unified" in unified.columns else pd.Series([True]*len(unified))
        unified.loc[mask, "gate_count_unified"] = unified.loc[mask, col]

# Normalise original_size
for col in ["original_size", "baseline_gate_count"]:
    if col in unified.columns:
        if "original_size_unified" not in unified.columns:
            unified["original_size_unified"] = pd.NA
        mask = unified["original_size_unified"].isna()
        unified.loc[mask, "original_size_unified"] = unified.loc[mask, col]

# Normalise optimized_size
for col in ["optimized_size", "optimized_gate_count"]:
    if col in unified.columns:
        if "optimized_size_unified" not in unified.columns:
            unified["optimized_size_unified"] = pd.NA
        mask = unified["optimized_size_unified"].isna()
        unified.loc[mask, "optimized_size_unified"] = unified.loc[mask, col]

print(f"\nUnified DataFrame: {len(unified)} rows, {len(unified.columns)} columns")
print(f"Unique circuit families across all experiments: {sorted(unified['circuit_family'].dropna().unique().tolist())}")

# ──────────────────────────────────────────────────────────────────────────
# 6. Per-family statistics (across ALL experiments)
# ──────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("SECTION 3: GLOBAL CIRCUIT FAMILY STATISTICS")
print("=" * 90)

STATS_COLS = ["reduction", "fidelity", "n_qubits", "depth",
              "entanglement_entropy", "normalized_entropy",
              "gate_count_unified", "original_size_unified", "optimized_size_unified",
              "runtime_seconds"]

# Filter to only those present
stats_cols_present = [c for c in STATS_COLS if c in unified.columns]

def compute_stats(group, cols):
    """Compute mean/std/median/min/max for numeric columns, plus success rate and count."""
    result = {"count": int(len(group))}
    for c in cols:
        if c in group.columns:
            s = pd.to_numeric(group[c], errors="coerce").dropna()
            if len(s) > 0:
                result[f"{c}_mean"] = float(s.mean())
                result[f"{c}_std"] = float(s.std())
                result[f"{c}_median"] = float(s.median())
                result[f"{c}_min"] = float(s.min())
                result[f"{c}_max"] = float(s.max())
            else:
                result[f"{c}_mean"] = None
                result[f"{c}_std"] = None
                result[f"{c}_median"] = None
                result[f"{c}_min"] = None
                result[f"{c}_max"] = None
    # Success rate: fraction of rows with reduction > threshold
    if "reduction" in group.columns:
        red = pd.to_numeric(group["reduction"], errors="coerce").dropna()
        if len(red) > 0:
            result["success_rate_gt20pct"] = float((red > REDUCTION_THRESHOLD).sum() / len(red))
            result["mean_reduction"] = float(red.mean())
            result["any_positive_reduction"] = bool((red > 0).any())
        else:
            result["success_rate_gt20pct"] = None
            result["mean_reduction"] = None
            result["any_positive_reduction"] = None
    return result

family_stats = {}
for fam, grp in unified.groupby("circuit_family"):
    fam_stats = compute_stats(grp, stats_cols_present)
    # Also list which experiments contribute
    fam_stats["experiments"] = sorted(grp["_experiment"].unique().tolist())
    family_stats[fam] = fam_stats

# Print
for fam in sorted(family_stats.keys()):
    s = family_stats[fam]
    print(f"\n  Family: {fam}")
    print(f"    Count: {s['count']}, Experiments: {s['experiments']}")
    if s.get("mean_reduction") is not None:
        print(f"    Reduction:  mean={s['reduction_mean']:.6f}  std={s['reduction_std']:.6f}  "
              f"median={s['reduction_median']:.6f}  min={s['reduction_min']:.6f}  max={s['reduction_max']:.6f}")
        print(f"    Success rate (>20%): {s['success_rate_gt20pct']:.4f}")
    if s.get("fidelity_mean") is not None:
        print(f"    Fidelity:   mean={s['fidelity_mean']:.10f}  std={s['fidelity_std']:.10f}")
    if s.get("n_qubits_mean") is not None:
        print(f"    N_qubits:   mean={s['n_qubits_mean']:.2f}  median={s['n_qubits_median']:.0f}  "
              f"min={s['n_qubits_min']:.0f}  max={s['n_qubits_max']:.0f}")
    if s.get("depth_mean") is not None:
        print(f"    Depth:      mean={s['depth_mean']:.2f}  median={s['depth_median']:.0f}  "
              f"min={s['depth_min']:.0f}  max={s['depth_max']:.0f}")
    if s.get("gate_count_unified_mean") is not None:
        print(f"    Gate_count: mean={s['gate_count_unified_mean']:.2f}  "
              f"min={s['gate_count_unified_min']:.0f}  max={s['gate_count_unified_max']:.0f}")
    if s.get("entanglement_entropy_mean") is not None:
        print(f"    Entropy:    mean={s['entanglement_entropy_mean']:.6f}  std={s['entanglement_entropy_std']:.6f}")
    if s.get("normalized_entropy_mean") is not None:
        print(f"    Norm_entr:  mean={s['normalized_entropy_mean']:.6f}  std={s['normalized_entropy_std']:.6f}")

# ──────────────────────────────────────────────────────────────────────────
# 7. Per-family stats broken down by experiment
# ──────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("SECTION 4: PER-FAMILY STATISTICS BY EXPERIMENT")
print("=" * 90)

family_by_exp = {}
for (fam, exp), grp in unified.groupby(["circuit_family", "_experiment"]):
    key = f"{fam}@{exp}"
    family_by_exp[key] = compute_stats(grp, stats_cols_present)

for key in sorted(family_by_exp.keys()):
    s = family_by_exp[key]
    fam, exp = key.split("@")
    print(f"\n  {fam} @ {exp}  (n={s['count']})")
    if s.get("mean_reduction") is not None:
        print(f"    Reduction: mean={s['reduction_mean']:.6f}  std={s['reduction_std']:.6f}  "
              f"med={s['reduction_median']:.6f}  min={s['reduction_min']:.6f}  max={s['reduction_max']:.6f}")
        print(f"    Success(>20%): {s['success_rate_gt20pct']:.4f}")

# ──────────────────────────────────────────────────────────────────────────
# 8. Pivot tables: E10 and E14 (circuit_family x optimizer -> mean reduction)
# ──────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("SECTION 5: PIVOT TABLES (circuit_family x optimizer -> mean_reduction)")
print("=" * 90)

pivot_results = {}

for exp_key in ["E10", "E14"]:
    if exp_key not in dfs:
        print(f"  {exp_key}: not loaded, skipping")
        continue
    df = dfs[exp_key]
    if "circuit_family" not in df.columns or "optimizer" not in df.columns:
        print(f"  {exp_key}: missing circuit_family or optimizer column, skipping")
        continue

    df["reduction"] = pd.to_numeric(df["reduction"], errors="coerce")
    pivot = df.pivot_table(index="circuit_family", columns="optimizer",
                           values="reduction", aggfunc="mean")
    print(f"\n--- {exp_key}: Mean Reduction by (circuit_family, optimizer) ---")
    print(pivot.to_string())

    # Also compute max reduction
    pivot_max = df.pivot_table(index="circuit_family", columns="optimizer",
                               values="reduction", aggfunc="max")
    print(f"\n--- {exp_key}: Max Reduction by (circuit_family, optimizer) ---")
    print(pivot_max.to_string())

    # Success rate pivot
    df["_success_gt20"] = (df["reduction"] > REDUCTION_THRESHOLD).astype(float)
    pivot_sr = df.pivot_table(index="circuit_family", columns="optimizer",
                              values="_success_gt20", aggfunc="mean")
    print(f"\n--- {exp_key}: Success Rate (>20%) by (circuit_family, optimizer) ---")
    print(pivot_sr.to_string())

    pivot_results[exp_key] = {
        "mean_reduction": pivot.to_dict(),
        "max_reduction": pivot_max.to_dict(),
        "success_rate": pivot_sr.to_dict(),
    }

# Also do E04 which has optimizer but no circuit_family
if "E04" in dfs:
    df04 = dfs["E04"].copy()
    df04["reduction"] = pd.to_numeric(df04["reduction"], errors="coerce")
    print(f"\n--- E04: Mean Reduction by optimizer (no circuit_family) ---")
    opt_stats = df04.groupby("optimizer")["reduction"].agg(["mean", "std", "median", "min", "max", "count"])
    print(opt_stats.to_string())
    pivot_results["E04_optimizer_summary"] = opt_stats.to_dict()

# ──────────────────────────────────────────────────────────────────────────
# 9. E13 Structural Ceiling Analysis
# ──────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("SECTION 6: E13 STRUCTURAL CEILING ANALYSIS")
print("=" * 90)

e13_ceiling = {}
if "E13" in dfs:
    df13 = dfs["E13"].copy()
    for c in ["structural_upper_bound_reduction", "observed_best_reduction",
              "ceiling_gap", "ceiling_gap_pct", "gate_count_total",
              "structural_lower_bound", "observed_best_gate_count",
              "cancellable_pair_count", "mergeable_rotation_count",
              "commuting_block_count", "adjacent_commuting_pairs"]:
        if c in df13.columns:
            df13[c] = pd.to_numeric(df13[c], errors="coerce")

    if "circuit_family" in df13.columns:
        ceiling_table = df13.groupby("circuit_family").agg({
            "structural_upper_bound_reduction": ["mean", "min", "max"],
            "observed_best_reduction": ["mean", "min", "max"],
            "ceiling_gap": ["mean", "min", "max"],
            "ceiling_gap_pct": ["mean", "min", "max"],
            "n_qubits": ["min", "max"],
        })
        print("\nStructural Upper Bound vs Observed Best Reduction per family:")
        print(ceiling_table.to_string())

        # Detailed per-row
        detail_cols = ["circuit_id", "circuit_family", "n_qubits", "depth",
                       "gate_count_total", "structural_upper_bound_reduction",
                       "observed_best_reduction", "ceiling_gap", "ceiling_gap_pct",
                       "best_optimizer", "cancellable_pair_count",
                       "mergeable_rotation_count"]
        detail_cols_present = [c for c in detail_cols if c in df13.columns]
        print("\nDetailed per-circuit ceiling analysis:")
        print(df13[detail_cols_present].to_string(index=False))

        # Build JSON-friendly structure
        for _, row in df13.iterrows():
            cid = str(row.get("circuit_id", "unknown"))
            e13_ceiling[cid] = {
                "circuit_family": str(row.get("circuit_family", "")),
                "n_qubits": int(row["n_qubits"]) if pd.notna(row.get("n_qubits")) else None,
                "depth": int(row["depth"]) if pd.notna(row.get("depth")) else None,
                "gate_count_total": int(row["gate_count_total"]) if pd.notna(row.get("gate_count_total")) else None,
                "structural_upper_bound_reduction": float(row["structural_upper_bound_reduction"]) if pd.notna(row.get("structural_upper_bound_reduction")) else None,
                "observed_best_reduction": float(row["observed_best_reduction"]) if pd.notna(row.get("observed_best_reduction")) else None,
                "ceiling_gap": float(row["ceiling_gap"]) if pd.notna(row.get("ceiling_gap")) else None,
                "ceiling_gap_pct": float(row["ceiling_gap_pct"]) if pd.notna(row.get("ceiling_gap_pct")) else None,
                "best_optimizer": str(row.get("best_optimizer", "")),
                "cancellable_pair_count": int(row["cancellable_pair_count"]) if pd.notna(row.get("cancellable_pair_count")) else None,
                "mergeable_rotation_count": int(row["mergeable_rotation_count"]) if pd.notna(row.get("mergeable_rotation_count")) else None,
            }

        # Summary: families where ceiling_gap > 0 (room for improvement)
        print("\n\nFamilies with ceiling_gap > 0 (room for improvement):")
        gap_df = df13[df13["ceiling_gap"] > 0.001]
        if len(gap_df) > 0:
            for _, row in gap_df.iterrows():
                print(f"  {row['circuit_id']:20s} family={row['circuit_family']:20s} "
                      f"upper_bound={row['structural_upper_bound_reduction']:.4f}  "
                      f"observed={row['observed_best_reduction']:.4f}  "
                      f"gap={row['ceiling_gap']:.4f}")
        else:
            print("  None - all families have reached their structural ceiling")
else:
    print("  E13 not loaded, skipping")

# ──────────────────────────────────────────────────────────────────────────
# 10. Correlational Analysis: reduction vs all numeric features
# ──────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("SECTION 7: CORRELATIONAL ANALYSIS (Pearson r with reduction)")
print("=" * 90)

correlation_results = {}

# Global correlation across unified dataset
print("\n--- Global Correlation (all experiments combined) ---")
for feat in NUMERIC_FEATURES:
    if feat in unified.columns:
        vals = pd.to_numeric(unified[feat], errors="coerce")
        red = pd.to_numeric(unified["reduction"], errors="coerce")
        mask = vals.notna() & red.notna()
        if mask.sum() > 2:
            r = vals[mask].corr(red[mask])
            n = int(mask.sum())
            correlation_results[feat] = {"r": float(r) if not np.isnan(r) else None, "n": n}
            print(f"  {feat:30s}  r = {r:+.6f}  (n={n})")

# Per-experiment correlation
print("\n--- Per-Experiment Correlation ---")
per_exp_corr = {}
for key, df in dfs.items():
    red = pd.to_numeric(df["reduction"], errors="coerce") if "reduction" in df.columns else None
    if red is None:
        continue
    exp_corr = {}
    for feat in NUMERIC_FEATURES:
        if feat in df.columns:
            vals = pd.to_numeric(df[feat], errors="coerce")
            mask = vals.notna() & red.notna()
            if mask.sum() > 2:
                r = vals[mask].corr(red[mask])
                n = int(mask.sum())
                exp_corr[feat] = {"r": float(r) if not np.isnan(r) else None, "n": n}
    if exp_corr:
        per_exp_corr[key] = exp_corr
        print(f"\n  [{key}]")
        for feat, info in exp_corr.items():
            r_str = f"{info['r']:+.6f}" if info['r'] is not None else "N/A"
            print(f"    {feat:30s}  r = {r_str}  (n={info['n']})")

# Per-family correlation (for families with enough data)
print("\n--- Per-Family Correlation (families with >=10 rows in unified) ---")
per_fam_corr = {}
for fam, grp in unified.groupby("circuit_family"):
    if len(grp) < 10:
        continue
    red = pd.to_numeric(grp["reduction"], errors="coerce")
    fam_corr = {}
    for feat in NUMERIC_FEATURES:
        if feat in grp.columns:
            vals = pd.to_numeric(grp[feat], errors="coerce")
            mask = vals.notna() & red.notna()
            if mask.sum() > 2:
                r = vals[mask].corr(red[mask])
                n = int(mask.sum())
                fam_corr[feat] = {"r": float(r) if not np.isnan(r) else None, "n": n}
    if fam_corr:
        per_fam_corr[fam] = fam_corr
        print(f"\n  [{fam}] (n={len(grp)})")
        for feat, info in fam_corr.items():
            r_str = f"{info['r']:+.6f}" if info['r'] is not None else "N/A"
            print(f"    {feat:30s}  r = {r_str}  (n={info['n']})")

# ──────────────────────────────────────────────────────────────────────────
# 11. Identify circuit families with ZERO reduction across ALL experiments
# ──────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("SECTION 8: CIRCUIT FAMILIES WITH ZERO REDUCTION (ALL EXPERIMENTS, ALL OPTIMIZERS)")
print("=" * 90)

zero_reduction_families = {}
for fam, grp in unified.groupby("circuit_family"):
    red = pd.to_numeric(grp["reduction"], errors="coerce").dropna()
    if len(red) == 0:
        continue
    max_red = float(red.max())
    mean_red = float(red.mean())
    any_positive = bool((red > 0.001).any())  # small tolerance
    if not any_positive:
        zero_reduction_families[fam] = {
            "max_reduction": max_red,
            "mean_reduction": mean_red,
            "count": int(len(red)),
            "experiments": sorted(grp["_experiment"].unique().tolist()),
        }
        print(f"\n  ZERO-REDUCTION FAMILY: {fam}")
        print(f"    Max reduction: {max_red:.8f}")
        print(f"    Mean reduction: {mean_red:.8f}")
        print(f"    Observations: {len(red)}")
        print(f"    Experiments: {sorted(grp['_experiment'].unique().tolist())}")
        # Show optimizer breakdown if available
        if "optimizer" in grp.columns:
            for opt, og in grp.groupby("optimizer"):
                ored = pd.to_numeric(og["reduction"], errors="coerce").dropna()
                print(f"      optimizer={opt}: mean_red={ored.mean():.8f}, max_red={ored.max():.8f}, n={len(ored)}")

if not zero_reduction_families:
    print("\n  No circuit families have strictly zero reduction across ALL experiments.")
    # Relax: show families with very low reduction
    print("\n  Families with mean_reduction < 0.001 (near-zero):")
    for fam, grp in unified.groupby("circuit_family"):
        red = pd.to_numeric(grp["reduction"], errors="coerce").dropna()
        if len(red) > 0 and red.mean() < 0.001:
            print(f"    {fam}: mean={red.mean():.8f}, max={red.max():.8f}, n={len(red)}")
            zero_reduction_families[fam] = {
                "max_reduction": float(red.max()),
                "mean_reduction": float(red.mean()),
                "count": int(len(red)),
                "experiments": sorted(grp["_experiment"].unique().tolist()),
            }

# Also: per-experiment zero-reduction families
print("\n--- Per-Experiment Zero-Reduction Families ---")
per_exp_zero = {}
for key, df in dfs.items():
    if "circuit_family" not in df.columns or "reduction" not in df.columns:
        continue
    df_red = pd.to_numeric(df["reduction"], errors="coerce")
    for fam, grp in df.groupby("circuit_family"):
        fred = pd.to_numeric(grp["reduction"], errors="coerce").dropna()
        if len(fred) > 0 and fred.max() < 0.001:
            per_exp_zero.setdefault(key, []).append(fam)
            print(f"  {key}/{fam}: max_reduction={fred.max():.8f}, n={len(fred)}")

# ──────────────────────────────────────────────────────────────────────────
# 12. Additional analyses
# ──────────────────────────────────────────────────────────────────────────

# E18 Clifford+T specific analysis
print("\n" + "=" * 90)
print("SECTION 9: E18 CLIFFORD+T SPECIFIC ANALYSIS")
print("=" * 90)

e18_analysis = {}
if "E18" in dfs:
    df18 = dfs["E18"].copy()
    for c in ["reduction", "t_count_reduction", "baseline_t_count",
              "optimized_t_count", "baseline_gate_count", "optimized_gate_count",
              "depth_reduction", "two_qubit_reduction", "cnot_reduction"]:
        if c in df18.columns:
            df18[c] = pd.to_numeric(df18[c], errors="coerce")

    if "circuit_family" in df18.columns:
        t_pivot = df18.pivot_table(index="circuit_family", columns="optimizer",
                                   values="reduction", aggfunc="mean")
        print("\nE18: Mean reduction by (family, optimizer) in Clifford+T basis:")
        print(t_pivot.to_string())

        if "t_count_reduction" in df18.columns:
            t_red_pivot = df18.pivot_table(index="circuit_family", columns="optimizer",
                                           values="t_count_reduction", aggfunc="mean")
            print("\nE18: Mean T-count reduction by (family, optimizer):")
            print(t_red_pivot.to_string())

        # Gate counts summary
        for fam, grp in df18.groupby("circuit_family"):
            bl = grp["baseline_gate_count"].dropna()
            opt = grp["optimized_gate_count"].dropna()
            print(f"\n  {fam}: baseline_gates mean={bl.mean():.0f}, optimized_gates mean={opt.mean():.0f}")

# E17 Connectivity analysis
print("\n" + "=" * 90)
print("SECTION 10: E17 CONNECTIVITY ANALYSIS")
print("=" * 90)

e17_analysis = {}
if "E17" in dfs:
    df17 = dfs["E17"].copy()
    df17["reduction"] = pd.to_numeric(df17["reduction"], errors="coerce")
    if "topology" in df17.columns and "circuit_family" in df17.columns:
        topo_pivot = df17.pivot_table(index="circuit_family", columns="topology",
                                      values="reduction", aggfunc="mean")
        print("\nE17: Mean reduction by (family, topology):")
        print(topo_pivot.to_string())

        topo_max = df17.pivot_table(index="circuit_family", columns="topology",
                                     values="reduction", aggfunc="max")
        print("\nE17: Max reduction by (family, topology):")
        print(topo_max.to_string())

# E16 Window Scaling analysis
print("\n" + "=" * 90)
print("SECTION 11: E16 WINDOW SCALING ANALYSIS")
print("=" * 90)

e16_analysis = {}
if "E16" in dfs:
    df16 = dfs["E16"].copy()
    df16["reduction"] = pd.to_numeric(df16["reduction"], errors="coerce")
    if "window_size" in df16.columns and "circuit_family" in df16.columns:
        ws_pivot = df16.pivot_table(index="circuit_family", columns="window_size",
                                    values="reduction", aggfunc="mean")
        print("\nE16: Mean reduction by (family, window_size):")
        print(ws_pivot.to_string())

# ──────────────────────────────────────────────────────────────────────────
# 13. Build and write JSON output
# ──────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("SECTION 12: WRITING JSON OUTPUT")
print("=" * 90)

def safe_json(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return str(obj)
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif pd.isna(obj):
        return None
    return obj

def deep_convert(obj):
    """Recursively convert numpy types."""
    if isinstance(obj, dict):
        return {str(k): deep_convert(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [deep_convert(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    return obj

output = {
    "metadata": {
        "generated_at": datetime.now().isoformat(),
        "description": "Phase 5 comprehensive feature extraction from all experiment data",
        "reduction_threshold": REDUCTION_THRESHOLD,
        "total_experiments": len(dfs),
        "total_rows": int(sum(len(d) for d in dfs.values())),
    },
    "file_inventory": {k: {"path": v["path"], "desc": v["desc"], "version": v["version"],
                            "rows": int(len(dfs[k])) if k in dfs else 0,
                            "columns": file_columns.get(k, {}).get("columns", [])}
                       for k, v in FILES.items()},
    "file_columns": deep_convert(file_columns),
    "family_availability": deep_convert(family_availability),
    "global_family_stats": deep_convert(family_stats),
    "family_by_experiment": deep_convert(family_by_exp),
    "pivot_tables": deep_convert(pivot_results),
    "e13_structural_ceiling": deep_convert(e13_ceiling),
    "correlation_global": deep_convert(correlation_results),
    "correlation_per_experiment": deep_convert(per_exp_corr),
    "correlation_per_family": deep_convert(per_fam_corr),
    "zero_reduction_families": deep_convert(zero_reduction_families),
    "per_experiment_zero_reduction_families": deep_convert(per_exp_zero),
    "e18_clifford_t_analysis": {},
    "e17_connectivity_analysis": {},
    "e16_window_scaling_analysis": {},
}

# Add E18/E17/E16 specific results to output
if "E18" in dfs and "circuit_family" in dfs["E18"].columns:
    df18 = dfs["E18"]
    for fam, grp in df18.groupby("circuit_family"):
        bl = grp["baseline_gate_count"].dropna()
        opt = grp["optimized_gate_count"].dropna()
        output["e18_clifford_t_analysis"][fam] = {
            "baseline_gates_mean": float(bl.mean()) if len(bl) > 0 else None,
            "optimized_gates_mean": float(opt.mean()) if len(opt) > 0 else None,
            "mean_reduction": float(pd.to_numeric(grp["reduction"], errors="coerce").mean()),
            "max_reduction": float(pd.to_numeric(grp["reduction"], errors="coerce").max()),
            "n_obs": int(len(grp)),
        }

if "E17" in dfs and "topology" in dfs["E17"].columns and "circuit_family" in dfs["E17"].columns:
    df17 = dfs["E17"]
    for (fam, topo), grp in df17.groupby(["circuit_family", "topology"]):
        key = f"{fam}@{topo}"
        output["e17_connectivity_analysis"][key] = {
            "mean_reduction": float(pd.to_numeric(grp["reduction"], errors="coerce").mean()),
            "max_reduction": float(pd.to_numeric(grp["reduction"], errors="coerce").max()),
            "n_obs": int(len(grp)),
        }

if "E16" in dfs and "window_size" in dfs["E16"].columns and "circuit_family" in dfs["E16"].columns:
    df16 = dfs["E16"]
    for (fam, ws), grp in df16.groupby(["circuit_family", "window_size"]):
        key = f"{fam}@ws{int(ws)}"
        output["e16_window_scaling_analysis"][key] = {
            "mean_reduction": float(pd.to_numeric(grp["reduction"], errors="coerce").mean()),
            "max_reduction": float(pd.to_numeric(grp["reduction"], errors="coerce").max()),
            "n_obs": int(len(grp)),
        }

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w") as f:
    json.dump(output, f, indent=2, default=safe_json)

print(f"\nJSON output written to: {OUTPUT_PATH}")
print(f"File size: {os.path.getsize(OUTPUT_PATH):,} bytes")

# ──────────────────────────────────────────────────────────────────────────
# 14. Summary
# ──────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("SUMMARY")
print("=" * 90)
print(f"  Experiments loaded:     {len(dfs)}")
print(f"  Total data rows:        {sum(len(d) for d in dfs.values()):,}")
all_fams = set()
for df in dfs.values():
    if "circuit_family" in df.columns:
        all_fams.update(df["circuit_family"].dropna().unique())
print(f"  Unique circuit families (real): {len(all_fams)} -> {sorted(all_fams)}")
print(f"  Zero-reduction families:       {len(zero_reduction_families)}")
print(f"  E13 ceiling entries:           {len(e13_ceiling)}")
print(f"  Global correlations computed:  {len(correlation_results)} features")
print(f"  JSON output:                   {OUTPUT_PATH}")
print("\nDone.")
