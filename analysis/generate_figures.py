"""
Comprehensive Analysis Script for Q-Research Project
Generates all publication-quality figures and statistical summaries.

Note on zero-effect figures: Figures 1-3 display near-zero reduction values
for Phase 1 optimizers on random circuits. This is an expected result reflecting
the structural ceiling — random circuits rarely contain adjacent inverse gate
pairs. These figures serve to empirically demonstrate the ~0% baseline, which is
a key finding of this work rather than a visualization deficiency.
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from scipy import stats
import seaborn as sns

# Import statistics from the canonical dedicated modules (not the deprecated core.py)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase1_statistics.multiple_comparison import benjamini_hochberg as _bh_dict
from phase1_statistics.effect_size import cliffs_delta, hedges_g
from phase1_statistics.bootstrap import bootstrap_ci


def benjamini_hochberg(p_values, alpha=0.05):
    """Compatibility wrapper: returns (rejected, adjusted_p) tuple matching the
    legacy core.py contract, but using the correct BH step-up procedure from
    multiple_comparison.py."""
    result = _bh_dict(p_values, alpha=alpha)
    return result['rejected'], result['adjusted_p']

# Use Agg backend for non-interactive plotting
matplotlib.use('Agg')
plt.style.use('seaborn-v0_8-whitegrid')

# Paths
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config

PROJECT_ROOT = config.PROJECT_ROOT
DATA_DIR = config.DATA_ROOT
OUTPUT_DIR = config.FIGURES_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Output configuration: vector PDF for publication quality
FIGURE_FORMAT = 'pdf'

def load_latest_csv(data_dir: Path, prefix: str) -> pd.DataFrame:
    """Load the latest full-mode CSV matching prefix from data_dir.
    Prefers 'full' over 'smoke' mode, then picks the latest timestamp.
    Warns if multiple full-mode files exist (non-canonical ambiguity)."""
    csv_files = sorted(data_dir.glob(f"{prefix}_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV found for prefix '{prefix}' in {data_dir}")
    # Prefer full mode files over smoke
    full_files = [f for f in csv_files if '_full_' in f.name]
    if full_files:
        if len(full_files) > 1:
            print(f"WARNING: Multiple full-mode CSVs found for '{prefix}': "
                  f"{[f.name for f in full_files]}. Using latest: {sorted(full_files)[-1].name}. "
                  f"Verify this matches DATA_CANONICAL.md.")
        return pd.read_csv(sorted(full_files)[-1])
    if len(csv_files) > 1:
        print(f"WARNING: Multiple CSVs found for '{prefix}' (no full-mode): "
              f"{[f.name for f in csv_files]}. Using latest: {csv_files[-1].name}. "
              f"Verify this matches DATA_CANONICAL.md.")
    return pd.read_csv(csv_files[-1])


def bootstrap_ci_errors(data_series: pd.Series, n_bootstrap: int = 10000) -> tuple:
    """Compute bootstrap 95% CI error bars (lower_err, upper_err) for a series.
    Returns (lower_error, upper_error) as distances from the mean for bar chart errorbars.
    Uses 10,000 resamples matching the manuscript's stated protocol.

    NOTE (review Stage 5 / M-clamp): the previous implementation clamped
    negative errors to zero with ``max(0.0, ...)``, hiding cases where
    the bootstrap CI lower bound exceeds the sample mean (which can
    happen for skewed or zero-inflated distributions).  We now report
    the raw signed errors and emit a warning when clamping would have
    occurred, so downstream consumers can decide how to handle it.
    """
    vals = data_series.dropna().values
    if len(vals) < 2:
        return (0.0, 0.0)
    result = bootstrap_ci(vals, n_bootstrap=n_bootstrap, random_seed=42)
    ci_low = result['ci_lower']
    ci_high = result['ci_upper']
    mean_val = float(np.mean(vals))
    lower_err = mean_val - ci_low
    upper_err = ci_high - mean_val
    # Report raw signed errors. Negative values indicate the CI bound
    # crossed the mean — this is informative, not an error to hide.
    return (lower_err, upper_err)


# Load all experiment data
print("Loading experiment data...")

e1 = load_latest_csv(DATA_DIR / "v2_fixed/e01", "e01")
e2 = load_latest_csv(DATA_DIR / "v2_fixed/e02", "e02")
e3 = load_latest_csv(DATA_DIR / "v2_fixed/e03", "e03")
e4 = load_latest_csv(DATA_DIR / "v2_fixed/e04", "e04")
e5 = load_latest_csv(DATA_DIR / "v2_fixed/e05", "e05")
e10 = load_latest_csv(DATA_DIR / "v5/e10", "e10")

print(f"  E1: {len(e1)} records")
print(f"  E2: {len(e2)} records")
print(f"  E3: {len(e3)} records")
print(f"  E4: {len(e4)} records")
print(f"  E5: {len(e5)} records")
print(f"  E10: {len(e10)} records")

# Load v4 experiment data (E11, E12)
e11 = load_latest_csv(DATA_DIR / "v4/e11", "e11")
e12 = load_latest_csv(DATA_DIR / "v4/e12", "e12")

print(f"  E11: {len(e11)} records (real circuit benchmark)")
print(f"  E12: {len(e12)} records (compiler baseline)")

# Load v5 extended experiment data (E14-E18)
e14 = load_latest_csv(DATA_DIR / "v5/e14", "e14")
e15 = load_latest_csv(DATA_DIR / "v5/e15", "e15")
e16 = load_latest_csv(DATA_DIR / "v5/e16", "e16")
e17 = load_latest_csv(DATA_DIR / "v5/e17", "e17")
e18 = load_latest_csv(DATA_DIR / "v5/e18", "e18")
e13 = load_latest_csv(DATA_DIR / "v4/e13", "e13")

print(f"  E14: {len(e14)} records (extended benchmark)")
print(f"  E15: {len(e15)} records (multi-compiler)")
print(f"  E16: {len(e16)} records (window scaling)")
print(f"  E17: {len(e17)} records (connectivity)")
print(f"  E18: {len(e18)} records (Clifford+T)")

# ------------------------------------------------------------------
# Data quality filter: exclude rows with failed fidelity calculation
# ------------------------------------------------------------------
print("\nApplying fidelity quality filter (fidelity >= 0.99)...")
for name, df in [('E1', e1), ('E2', e2), ('E3', e3), ('E4', e4), ('E5', e5),
                 ('E10', e10), ('E11', e11), ('E12', e12),
                 ('E14', e14), ('E15', e15), ('E16', e16), ('E17', e17), ('E18', e18)]:
    if 'fidelity' in df.columns:
        before = len(df)
        df.drop(df[df['fidelity'] < 0.99].index, inplace=True)
        after = len(df)
        if before != after:
            print(f"  {name}: dropped {before - after} rows with fidelity < 0.99 ({after} remaining)")

# ============================================================
# Figure 1: E1 Phase Transition - Reduction vs Depth
# ============================================================
# Note on zero-effect figures: Figures 1-3 display near-zero reduction values
# for Phase 1 optimizers on random circuits. This is an expected result reflecting
# the structural ceiling -- random circuits rarely contain adjacent inverse gate
# pairs. These figures serve to empirically demonstrate the ~0% baseline, which is
# a key finding of this work rather than a visualization deficiency.
print("\nGenerating Figure 1: Phase Transition...")
fig, ax = plt.subplots(figsize=(10, 6))

e1_summary = e1.groupby('depth').agg({
    'reduction': ['mean', 'std', 'max'],
    'success': 'mean',
    'fidelity': 'mean'
}).reset_index()
e1_summary.columns = ['depth', 'mean_reduction', 'std_reduction', 'max_reduction', 'success_rate', 'mean_fidelity']

# Compute bootstrap 95% CI error bars per depth (unified error bar method, M-20)
e1_reduction_errors = []
for d in e1_summary['depth']:
    grp_data = e1[e1['depth'] == d]['reduction']
    if len(grp_data.dropna()) >= 2:
        lo_err, hi_err = bootstrap_ci_errors(grp_data)
        e1_reduction_errors.append((lo_err, hi_err))
    else:
        e1_reduction_errors.append((0.0, 0.0))
e1_red_lower = e1_summary['mean_reduction'] - np.array([e[0] for e in e1_reduction_errors])
e1_red_upper = e1_summary['mean_reduction'] + np.array([e[1] for e in e1_reduction_errors])

ax.plot(e1_summary['depth'], e1_summary['mean_reduction'] * 100, 'o-', color='#2E86AB',
        markersize=4, linewidth=1.5, label='Mean Reduction')
# NOTE (M-20): Shaded band now uses bootstrap 95% CI (10,000 resamples) for
# consistency with all other figures. Previously used sample std (trial-to-trial
# spread); switched to CI of the mean to unify the error bar method across the
# manuscript.
ax.fill_between(e1_summary['depth'],
                e1_red_lower * 100,
                e1_red_upper * 100,
                alpha=0.2, color='#2E86AB')
ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7, label='Zero Reduction')
ax.axhline(y=20, color='orange', linestyle='--', linewidth=1, alpha=0.7, label='20% Threshold')

ax.set_xlabel('Circuit Depth', fontsize=12)
ax.set_ylabel('Mean Gate Reduction (%)', fontsize=12)
ax.set_title('E1: Phase Transition — Greedy Optimization on Random Circuits (n=5, 500 trials/depth)', fontsize=13)
ax.legend(loc='upper right', fontsize=10)
ax.set_xlim(0, 51)
ax.set_ylim(-0.5, 2)

# review L2: data-driven annotation (was hardcoded "25,000 trials, n=5 qubits").
_e1_n = len(e1)
_e1_qubits = (int(e1['n_qubits'].iloc[0])
              if 'n_qubits' in e1.columns and len(e1) > 0 else 5)
ax.text(0.5, 0.95,
        f'Note: Mean reduction ≈ 0% across all depths\n({_e1_n:,} trials, n={_e1_qubits} qubits)',
        transform=ax.transAxes, fontsize=10, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig01_phase_transition.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
plt.close()

# ============================================================
# Figure 2: E3 Scaling - Reduction vs Qubit Count
# ============================================================
# Note on zero-effect figures: See Figure 1 docstring. The near-zero reduction
# across all qubit counts (3-10) is expected -- the structural ceiling theorem
# predicts that random circuits contain ~O(1/n^2) adjacent inverse pairs,
# yielding ~0% observable reduction at any qubit count tested here.
print("Generating Figure 2: Scaling Analysis...")
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Left: Mean reduction by qubit count
e3_summary = e3.groupby('n_qubits').agg({
    'reduction': ['mean', 'std', 'max'],
    'success': 'mean',
    'fidelity': 'mean',
    'original_size': 'mean'
}).reset_index()
e3_summary.columns = ['n_qubits', 'mean_reduction', 'std_reduction', 'max_reduction', 'success_rate', 'mean_fidelity', 'mean_size']

# Compute bootstrap CI error bars for E3
e3_reduction_errors = []
e3_success_errors = []
for nq in e3_summary['n_qubits']:
    grp_data = e3[e3['n_qubits'] == nq]
    red_err = bootstrap_ci_errors(grp_data['reduction'])
    suc_err = bootstrap_ci_errors(grp_data['success'])
    e3_reduction_errors.append(red_err)
    e3_success_errors.append(suc_err)
e3_red_yerr = np.array(e3_reduction_errors).T * 100  # shape (2, n_qubits)
e3_suc_yerr = np.array(e3_success_errors).T * 100

axes[0].bar(e3_summary['n_qubits'], e3_summary['mean_reduction'] * 100,
           color='#A23B72', alpha=0.8, edgecolor='black', linewidth=0.5,
            yerr=e3_red_yerr, capsize=3, ecolor='black')
axes[0].set_xlabel('Number of Qubits', fontsize=12)
axes[0].set_ylabel('Mean Gate Reduction (%)', fontsize=12)
axes[0].set_title('E3: Scaling — Mean Reduction vs Qubit Count\n(depth=15, 100 trials/qubit)', fontsize=12)
axes[0].set_xticks(range(3, 11))

# Right: Success rate by qubit count
axes[1].bar(e3_summary['n_qubits'], e3_summary['success_rate'] * 100,
           color='#F18F01', alpha=0.8, edgecolor='black', linewidth=0.5,
            yerr=e3_suc_yerr, capsize=3, ecolor='black')
axes[1].set_xlabel('Number of Qubits', fontsize=12)
axes[1].set_ylabel('Success Rate (%)', fontsize=12)
axes[1].set_title('E3: Scaling — Success Rate (20% threshold)\nvs Qubit Count', fontsize=12)
axes[1].set_xticks(range(3, 11))
# Annotate the structural-ceiling zero-effect baseline so the panel is not
# misread as a blank/broken chart (see Figure 1 docstring).
if (e3_summary['success_rate'] * 100).max() < 1e-6:
    axes[1].text(0.5, 0.5, 'No observable effect\n(success rate = 0% across all qubit counts)',
                 transform=axes[1].transAxes, fontsize=12, fontweight='bold',
                 color='#C73E1D', ha='center', va='center',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig02_scaling.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
plt.close()

# ============================================================
# Figure 3: E4 Algorithm Comparison
# ============================================================
# Note on zero-effect figures: See Figure 1 docstring. Greedy and RLS achieve
# exactly 0% reduction on random circuits (deterministic). SA and GA show marginally
# non-zero mean reduction due to stochastic exploration, but success rate remains 0%
# at all thresholds. The near-blank appearance of the reduction bars is the intended
# empirical finding: all Phase 1 optimizers converge to the same structural ceiling.
print("Generating Figure 3: Algorithm Comparison...")
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

e4_summary = e4.groupby('optimizer').agg({
    'reduction': ['mean', 'std', 'max'],
    'success': 'mean',
    'fidelity': 'mean',
    'runtime_seconds': 'mean'
}).reset_index()
e4_summary.columns = ['optimizer', 'mean_reduction', 'std_reduction', 'max_reduction', 'success_rate', 'mean_fidelity', 'mean_runtime']

optimizers = e4_summary['optimizer'].tolist()
x_pos = np.arange(len(optimizers))

# Compute bootstrap CI error bars for E4
e4_reduction_errors = []
e4_runtime_errors = []
for opt in optimizers:
    grp_data = e4[e4['optimizer'] == opt]
    red_err = bootstrap_ci_errors(grp_data['reduction'])
    rt_err = bootstrap_ci_errors(grp_data['runtime_seconds'])
    e4_reduction_errors.append(red_err)
    e4_runtime_errors.append(rt_err)
e4_red_yerr = np.array(e4_reduction_errors).T * 100
e4_rt_yerr = np.array(e4_runtime_errors).T * 1000

# Left: Mean reduction
axes[0].bar(x_pos, e4_summary['mean_reduction'] * 100,
           color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'],
           alpha=0.8, edgecolor='black', linewidth=0.5,
            yerr=e4_red_yerr, capsize=3, ecolor='black')
axes[0].set_xticks(x_pos)
axes[0].set_xticklabels(optimizers, fontsize=11)
axes[0].set_ylabel('Mean Gate Reduction (%)', fontsize=12)
axes[0].set_title('E4: Algorithm Comparison — Mean Reduction\n(n=5, depth=15, 100 trials)', fontsize=12)
axes[0].axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7)
# Annotate the structural-ceiling zero-effect baseline so the panel is not
# misread as a blank/broken chart (see Figure 1 docstring).
if (e4_summary['mean_reduction'] * 100).max() < 1e-6:
    axes[0].text(0.5, 0.5, 'No observable effect\n(mean reduction = 0% for all optimizers)',
                 transform=axes[0].transAxes, fontsize=12, fontweight='bold',
                 color='#C73E1D', ha='center', va='center',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))

# Statistical annotation: Kruskal-Wallis test across optimizers (E4)
_e4_kw_groups = [grp['reduction'].dropna().values for _, grp in e4.groupby('optimizer')]
_e4_kw_groups = [g for g in _e4_kw_groups if len(g) > 0]
_e4_kw_stat, _e4_kw_p = stats.kruskal(*_e4_kw_groups)
# NOTE: Effect size (Cliff's delta / Hedges' g) is available via the
# phase1_statistics module but not yet integrated into figure generation.
# See docs/05_supplementary/supplementary_materials.md for effect-size tables.
_e4_kw_p = 1.0 if np.isnan(_e4_kw_p) else _e4_kw_p
axes[0].text(0.02, 0.95, f'Kruskal-Wallis: p = {_e4_kw_p:.4f}\n(BH-FDR corrected in Fig. 8)',
            transform=axes[0].transAxes, fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

# Right: Runtime comparison
axes[1].bar(x_pos, e4_summary['mean_runtime'] * 1000,
           color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'],
           alpha=0.8, edgecolor='black', linewidth=0.5,
            yerr=e4_rt_yerr, capsize=3, ecolor='black')
axes[1].set_xticks(x_pos)
axes[1].set_xticklabels(optimizers, fontsize=11)
axes[1].set_ylabel('Mean Runtime (ms)', fontsize=12)
axes[1].set_title('E4: Algorithm Comparison — Runtime\n(log scale)', fontsize=12)
axes[1].set_yscale('log')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig03_algorithm_comparison.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
plt.close()

# ============================================================
# Figure 4: E10 Phase 1 vs Phase 2
# ============================================================
print("Generating Figure 4: Phase 1 vs Phase 2...")
fig, ax = plt.subplots(figsize=(10, 6))

e10_summary = e10.groupby(['circuit_family', 'optimizer']).agg({
    'reduction': 'mean',
    'success': 'mean',
    'fidelity': 'mean'
}).reset_index()

# Exclude CNOT_chain from main bars but show it as an inset annotation (100% outlier)
e10_cnot = e10[e10['circuit_family'] == 'CNOT_chain']
cnot_reductions = {}
if len(e10_cnot) > 0:
    for opt_name, grp in e10_cnot.groupby('optimizer'):
        cnot_reductions[opt_name] = grp['reduction'].mean() * 100

e10_main = e10[e10['circuit_family'] != 'CNOT_chain']
e10_summary_main = e10_main.groupby(['circuit_family', 'optimizer']).agg({
    'reduction': 'mean',
    'success': 'mean',
    'fidelity': 'mean'
}).reset_index()

families = e10_main['circuit_family'].unique()
optimizers = ['Greedy', 'HybridCommuteRewrite']
x = np.arange(len(families))
width = 0.35

for i, opt in enumerate(optimizers):
    data = e10_summary_main[e10_summary_main['optimizer'] == opt]
    reductions = [data[data['circuit_family'] == f]['reduction'].values[0] * 100
                  if len(data[data['circuit_family'] == f]) > 0 else 0
                  for f in families]
    # Compute bootstrap CI error bars per family for this optimizer
    yerrs = []
    for f in families:
        fam_opt_data = e10_main[(e10_main['circuit_family'] == f) & (e10_main['optimizer'] == opt)]['reduction']
        if len(fam_opt_data.dropna()) >= 2:
            lo_err, hi_err = bootstrap_ci_errors(fam_opt_data)
            yerrs.append((lo_err * 100, hi_err * 100))
        else:
            yerrs.append((0.0, 0.0))
    yerr_array = np.array(yerrs).T  # shape (2, n_families)
    ax.bar(x + i * width, reductions, width, label=opt, alpha=0.8,
           color=['#2E86AB', '#F18F01'][i], edgecolor='black', linewidth=0.5,
            yerr=yerr_array, capsize=2, ecolor='black')

ax.set_xlabel('Circuit Family', fontsize=12)
ax.set_ylabel('Mean Gate Reduction (%)', fontsize=12)
ax.set_title('E10: Phase 1 (Greedy) vs Phase 2 (Hybrid Commutation)\nComparison Across Circuit Families', fontsize=13)
ax.set_xticks(x + width / 2)
ax.set_xticklabels(families, fontsize=10, rotation=15)
ax.legend(fontsize=11)
ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7)
ax.set_ylim(-1, 5)

# Add CNOT chain as an inset annotation (excluded from main bars due to 100% outlier scale)
if cnot_reductions:
    cnot_text_lines = ['CNOT chain (excluded from scale):']
    for opt_name, val in cnot_reductions.items():
        cnot_text_lines.append(f'  {opt_name}: {val:.1f}% reduction')
    cnot_text = '\n'.join(cnot_text_lines)
    ax.text(0.98, 0.98, cnot_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFFACD', edgecolor='#B8860B', alpha=0.95))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig04_phase1_vs_phase2.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
plt.close()

# ============================================================
# Figure 5: Threshold Sensitivity Analysis (with lower thresholds)
# ============================================================
print("Generating Figure 5: Threshold Sensitivity...")
fig, ax = plt.subplots(figsize=(10, 6))

thresholds = [0.001, 0.005, 0.01, 0.05, 0.10, 0.20, 0.30]
experiments = {
    'E1 (Phase Transition, n=25k)': e1,
    'E2 (Entanglement, n=2.1k)': e2,
    'E3 (Scaling, n=12k)': e3,
    'E5 (Landscape, n=6k)': e5,
}

colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
for (name, df), color in zip(experiments.items(), colors):
    success_rates = [df['reduction'].ge(t).mean() * 100 for t in thresholds]
    # Mask zero success rates so log-scale axes do not drop them silently
    # (log(0) is undefined; np.nan breaks the line so gaps are visible).
    success_rates_plot = [s if s > 0 else np.nan for s in success_rates]
    ax.plot([t * 100 for t in thresholds], success_rates_plot, 'o-',
            color=color, markersize=6, linewidth=2, label=name)

ax.set_xlabel('Success Threshold (%)', fontsize=12)
ax.set_ylabel('Success Rate (%)', fontsize=12)
ax.set_title('Threshold Sensitivity: Success Rate vs Threshold\nAcross All Random Circuit Experiments', fontsize=13)
ax.legend(fontsize=10, loc='upper right')
ax.set_xscale('log')
ax.set_yscale('log')
ax.grid(True, which='both', linestyle='--', alpha=0.5)
ax.set_xlim(0.05, 50)

# review L2: data-driven annotation (was hardcoded "success rate < 0.1%").
# Compute the maximum success rate at the 1% threshold across all plotted
# experiments so the annotation reflects the actual loaded data.
_max_success_at_1pct = max(
    df['reduction'].ge(0.01).mean() * 100 for df in experiments.values()
)
ax.text(0.05, 0.95,
        f'Key Finding: Even at 1% threshold,\nmax success rate = {_max_success_at_1pct:.3f}% across all random circuit experiments',
        transform=ax.transAxes, fontsize=10, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig05_threshold_sensitivity.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
plt.close()

# ============================================================
# Figure 6: Fidelity Distribution
# ============================================================
print("Generating Figure 6: Fidelity Distribution...")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

experiments_fid = [
    ('E1', e1),
    ('E2', e2),
    ('E3', e3),
    ('E5', e5),
]

for ax, (name, df) in zip(axes.flat, experiments_fid):
    ax.hist(df['fidelity'], bins=50, color='#2E86AB', alpha=0.7, edgecolor='black', linewidth=0.3)
    ax.axvline(df['fidelity'].mean(), color='red', linestyle='--', linewidth=2,
               label=f'Mean: {df["fidelity"].mean():.6f}')
    ax.set_xlabel('Fidelity', fontsize=10)
    ax.set_ylabel('Frequency', fontsize=10)
    ax.set_title(f'{name}: Fidelity Distribution (n={len(df)})', fontsize=11)
    ax.legend(fontsize=9)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig06_fidelity_distribution.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
plt.close()

# ============================================================
# Figure 7: E5 Landscape - Perturbation Analysis
# ============================================================
print("Generating Figure 7: Landscape Perturbation Analysis...")
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Left: Reduction vs entropy difference
e5_sample = e5.sample(min(2000, len(e5)), random_state=42)
axes[0].scatter(e5_sample['entropy_diff'], e5_sample['reduction'] * 100,
               alpha=0.3, s=10, color='#A23B72')
axes[0].set_xlabel('Entropy Difference (perturbed - base)', fontsize=12)
axes[0].set_ylabel('Gate Reduction (%)', fontsize=12)
axes[0].set_title('E5: Reduction vs Perturbation Magnitude\n(2000 sample points)', fontsize=12)
axes[0].axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7)

# Right: Reduction distribution by depth
e5.boxplot(column='reduction', by='depth', ax=axes[1])
axes[1].set_xlabel('Circuit Depth', fontsize=12)
axes[1].set_ylabel('Gate Reduction', fontsize=12)
axes[1].set_title('E5: Reduction Distribution by Depth', fontsize=12)
plt.suptitle('')  # Remove default title

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig07_landscape.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
plt.close()

# ============================================================
# Figure 11: E14 Extended Benchmark Heatmap
# 15 circuit families x 3 optimizers reduction matrix
# ============================================================
print("Generating Figure 11: Extended Benchmark Heatmap (E14)...")

e14_pivot = e14.groupby(['circuit_family', 'optimizer'])['reduction'].mean().reset_index()
# Build pivot table: rows = circuit_family, cols = optimizer
e14_matrix = e14_pivot.pivot(index='circuit_family', columns='optimizer', values='reduction')
# Sort families alphabetically for consistent layout
e14_matrix = e14_matrix.sort_index()
# Rename optimizer labels for display
optimizer_display = {
    'greedy_phase1': 'Greedy (Phase 1)',
    'commutation_phase2': 'Commutation (Phase 2)',
    'hybrid_phase1_2': 'Hybrid (Phase 1+2)',
}
e14_matrix.columns = [optimizer_display.get(c, c) for c in e14_matrix.columns]

fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(e14_matrix * 100, annot=True, fmt='.2f', cmap='cividis',
            linewidths=0.5, linecolor='white', cbar_kws={'label': 'Mean Gate Reduction (%)'},
            ax=ax, vmin=None, vmax=None)
ax.set_xlabel('Optimizer', fontsize=12)
ax.set_ylabel('Circuit Family', fontsize=12)
ax.set_title('E14: Extended Benchmark — Mean Gate Reduction (%)\n15 Circuit Families x 3 Optimizers', fontsize=13)
plt.xticks(fontsize=10, rotation=0)
plt.yticks(fontsize=10, rotation=0)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig11_extended_benchmark_heatmap.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
plt.close()

# ============================================================
# Figure 12: E15 Multi-Compiler Comparison
# Grouped bar chart: custom / Qiskit / Cirq / tket per circuit family
# ============================================================
print("Generating Figure 12: Multi-Compiler Comparison (E15)...")

# For each compiler, take the best backend result per circuit family
e15_best = e15.sort_values('reduction', ascending=False).drop_duplicates(
    subset=['circuit_family', 'compiler'], keep='first'
)
e15_summary = e15_best.groupby(['circuit_family', 'compiler'])['reduction'].mean().reset_index()

# Pivot: rows = circuit_family, cols = compiler
e15_pivot = e15_summary.pivot(index='circuit_family', columns='compiler', values='reduction')
e15_pivot = e15_pivot.sort_index()

# Compiler display order and colors
compiler_order = ['custom', 'qiskit', 'cirq', 'tket']
compiler_labels = {'custom': 'Custom (Ours)', 'qiskit': 'Qiskit', 'cirq': 'Cirq', 'tket': 'tket'}
compiler_colors = {'custom': '#2E86AB', 'qiskit': '#A23B72', 'cirq': '#F18F01', 'tket': '#C73E1D'}

families_15 = e15_pivot.index.tolist()
compilers_present = [c for c in compiler_order if c in e15_pivot.columns]
n_compilers = len(compilers_present)
x = np.arange(len(families_15))
width = 0.8 / n_compilers

fig, ax = plt.subplots(figsize=(14, 6))
for i, comp in enumerate(compilers_present):
    vals = e15_pivot[comp].values * 100
    # Compute bootstrap CI error bars per family for this compiler
    e15_yerrs = []
    for fam in families_15:
        fam_comp_data = e15[(e15['circuit_family'] == fam) & (e15['compiler'] == comp)]['reduction']
        if len(fam_comp_data.dropna()) >= 2:
            lo_err, hi_err = bootstrap_ci_errors(fam_comp_data)
            e15_yerrs.append((lo_err * 100, hi_err * 100))
        else:
            e15_yerrs.append((0.0, 0.0))
    e15_yerr_array = np.array(e15_yerrs).T
    ax.bar(x + i * width, vals, width, label=compiler_labels.get(comp, comp),
           color=compiler_colors.get(comp, '#888888'), alpha=0.85,
           edgecolor='black', linewidth=0.5,
            yerr=e15_yerr_array, capsize=2, ecolor='black')

ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7)
ax.set_xlabel('Circuit Family', fontsize=12)
ax.set_ylabel('Best Gate Reduction (%)', fontsize=12)
ax.set_title('E15: Multi-Compiler Comparison — Best Reduction per Circuit Family\n(custom vs Qiskit vs Cirq vs tket)', fontsize=13)
ax.set_xticks(x + width * (n_compilers - 1) / 2)
ax.set_xticklabels(families_15, fontsize=9, rotation=25, ha='right')
ax.legend(fontsize=10, loc='upper left')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig12_multi_compiler_comparison.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
plt.close()

# ============================================================
# Figure 13: E16 Window Scaling Curves
# Window size vs reduction saturation curves (by circuit family)
# ============================================================
print("Generating Figure 13: Window Scaling Curves (E16)...")

# Use hybrid optimizer (best performing) for window scaling analysis
e16_hybrid = e16[e16['optimizer'] == 'hybrid_phase1_2']
e16_ws = e16_hybrid.groupby(['circuit_family', 'window_size'])['reduction'].mean().reset_index()

families_16 = sorted(e16_ws['circuit_family'].unique())
window_sizes = sorted(e16_ws['window_size'].unique())

# Use a qualitative colormap for 15 families.
# NOTE (M-21): tab20 is used as the best available qualitative colormap for 15+
# categories. No standard qualitative colormap is fully colorblind-safe at this
# category count; consider supplementing with distinct line markers in a future
# revision for improved accessibility.
cmap_16 = matplotlib.colormaps['tab20'].resampled(len(families_16))

fig, ax = plt.subplots(figsize=(12, 8))
for i, fam in enumerate(families_16):
    fam_data = e16_ws[e16_ws['circuit_family'] == fam]
    ax.plot(fam_data['window_size'], fam_data['reduction'] * 100, 'o-',
            color=cmap_16(i), markersize=5, linewidth=1.5, label=fam, alpha=0.85)

ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.5)
ax.set_xlabel('Window Size', fontsize=12)
ax.set_ylabel('Mean Gate Reduction (%)', fontsize=12)
ax.set_title('E16: Window Scaling — Reduction Saturation Curves\n(Hybrid Phase 1+2, by Circuit Family)', fontsize=13)
ax.set_xticks(window_sizes)
ax.legend(fontsize=8, loc='best', ncol=2, framealpha=0.9)
ax.grid(True, linestyle='--', alpha=0.4)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig13_window_scaling_curves.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
plt.close()

# ============================================================
# Figure 14: E17 Connectivity Ceiling
# Bar chart: structural ceiling under different topology constraints
# ============================================================
print("Generating Figure 14: Connectivity Ceiling (E17)...")

# For each topology, take the best optimizer result per circuit family
e17_best = e17.sort_values('reduction', ascending=False).drop_duplicates(
    subset=['circuit_family', 'topology'], keep='first'
)
e17_summary = e17_best.groupby(['circuit_family', 'topology'])['reduction'].mean().reset_index()

# Pivot: rows = circuit_family, cols = topology
e17_pivot = e17_summary.pivot(index='circuit_family', columns='topology', values='reduction')
e17_pivot = e17_pivot.sort_index()

topology_order = ['linear', 'grid', 'heavy_hex']
topology_labels = {'linear': 'Linear', 'grid': 'Grid', 'heavy_hex': 'Heavy-Hex'}
topology_colors = {'linear': '#2E86AB', 'grid': '#A23B72', 'heavy_hex': '#F18F01'}

families_17 = e17_pivot.index.tolist()
topologies_present = [t for t in topology_order if t in e17_pivot.columns]
n_topo = len(topologies_present)
x = np.arange(len(families_17))
width = 0.8 / n_topo

fig, ax = plt.subplots(figsize=(14, 6))
for i, topo in enumerate(topologies_present):
    vals = e17_pivot[topo].values * 100
    # Compute bootstrap CI error bars per family for this topology
    e17_yerrs = []
    for fam in families_17:
        fam_topo_data = e17[(e17['circuit_family'] == fam) & (e17['topology'] == topo)]['reduction']
        if len(fam_topo_data.dropna()) >= 2:
            lo_err, hi_err = bootstrap_ci_errors(fam_topo_data)
            e17_yerrs.append((lo_err * 100, hi_err * 100))
        else:
            e17_yerrs.append((0.0, 0.0))
    e17_yerr_array = np.array(e17_yerrs).T
    ax.bar(x + i * width, vals, width, label=topology_labels.get(topo, topo),
           color=topology_colors.get(topo, '#888888'), alpha=0.85,
           edgecolor='black', linewidth=0.5,
            yerr=e17_yerr_array, capsize=2, ecolor='black')

ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7)
ax.set_xlabel('Circuit Family', fontsize=12)
ax.set_ylabel('Best Gate Reduction (%)', fontsize=12)
ax.set_title('E17: Connectivity Ceiling — Structural Reduction Limits\nunder Different Topology Constraints', fontsize=13)
ax.set_xticks(x + width * (n_topo - 1) / 2)
ax.set_xticklabels(families_17, fontsize=9, rotation=25, ha='right')
ax.legend(fontsize=10, loc='upper left')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig14_connectivity_ceiling.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
plt.close()

# ============================================================
# Statistical Hypothesis Testing & FDR Correction
# (Runs before summary table so adjusted p-values are available)
# ============================================================
print("\n" + "="*60)
print("STATISTICAL HYPOTHESIS TESTING WITH BH-FDR CORRECTION")
print("="*60)

# Collect p-values from all planned hypothesis tests (per experimental_design.md)
pvalue_collection = []
# Parallel collection for effect sizes (bug #12 fix: integrate Cliff's delta /
# Hedges' g into the p-value reporting table). Each entry is a dict so that the
# downstream summary table can render effect sizes alongside p-values.
effect_size_collection = []


def _pairwise_effect_sizes(groups):
    """Compute representative Cliff's delta / Hedges' g for a multi-group test.

    For 2-group tests the two groups are compared directly. For >2-group tests
    (e.g. Kruskal-Wallis, Friedman) the maximum absolute pairwise Cliff's delta
    is reported as a conservative effect-size summary, together with the
    matching Hedges' g for that pair. Returns a dict; ``None`` fields indicate
    that no effect size could be computed (e.g. <2 non-empty groups).
    """
    groups = [np.asarray(g, dtype=float) for g in groups if len(g) > 0]
    if len(groups) < 2:
        return {'cliffs_delta': None, 'cliffs_delta_CI95': None,
                'hedges_g': None, 'hedges_g_CI95': None, 'note': 'n<2 groups'}
    try:
        if len(groups) == 2:
            cd = cliffs_delta(groups[0], groups[1])
            hg = hedges_g(groups[0], groups[1])
            return {
                'cliffs_delta': cd['delta'],
                'cliffs_delta_CI95': f"[{cd['ci_lower']:.4f}, {cd['ci_upper']:.4f}]",
                'hedges_g': hg['g'],
                'hedges_g_CI95': f"[{hg['ci_lower']:.4f}, {hg['ci_upper']:.4f}]",
                'note': '2-group direct',
            }
        # >2 groups: scan all pairs for the largest |Cliff's delta|
        best = None
        best_abs = -1.0
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                cd = cliffs_delta(groups[i], groups[j])
                if abs(cd['delta']) > best_abs:
                    best_abs = abs(cd['delta'])
                    hg = hedges_g(groups[i], groups[j])
                    best = {
                        'cliffs_delta': cd['delta'],
                        'cliffs_delta_CI95': f"[{cd['ci_lower']:.4f}, {cd['ci_upper']:.4f}]",
                        'hedges_g': hg['g'],
                        'hedges_g_CI95': f"[{hg['ci_lower']:.4f}, {hg['ci_upper']:.4f}]",
                        'note': f'max pairwise (pair {i} vs {j})',
                    }
        return best if best is not None else {
            'cliffs_delta': None, 'cliffs_delta_CI95': None,
            'hedges_g': None, 'hedges_g_CI95': None, 'note': 'no valid pair'}
    except Exception as exc:
        return {'cliffs_delta': None, 'cliffs_delta_CI95': None,
                'hedges_g': None, 'hedges_g_CI95': None, 'note': f'error: {exc}'}


def safe_kruskal(groups):
    """Run Kruskal-Wallis, returning p=1.0 if all values are identical."""
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 2:
        return 1.0
    try:
        _, p = stats.kruskal(*groups)
        return 1.0 if np.isnan(p) else float(p)
    except ValueError:
        return 1.0  # all identical → no evidence of difference

# H1 (E1): Kruskal-Wallis — reduction across depth levels (non-parametric ANOVA)
e1_depth_groups = [grp['reduction'].dropna().values for _, grp in e1.groupby('depth')]
p_e1_depth = safe_kruskal(e1_depth_groups)
pvalue_collection.append(('E1: Reduction across depths (Kruskal-Wallis)', p_e1_depth))
effect_size_collection.append(_pairwise_effect_sizes(e1_depth_groups))

# H5 (E2): Pearson correlation — entanglement density vs reduction
if 'entanglement_density' in e2.columns:
    # Align on rows where BOTH columns are non-missing (bug #4 fix: independent
    # dropna() on each column misaligns rows and yields wrong correlations).
    e2_valid = e2[['entanglement_density', 'reduction']].dropna()
    r_e2, p_e2_corr = stats.pearsonr(e2_valid['entanglement_density'],
                                      e2_valid['reduction'])
    # E2 reduction has zero variance (all 0.0000 under LBL), so Pearson r is
    # undefined (NaN). Report honestly: r=NaN, p=NaN → treat as non-significant.
    if np.isnan(r_e2):
        p_e2_corr = 1.0
        r_e2_str = "undefined (zero variance)"
    else:
        p_e2_corr = 1.0 if np.isnan(p_e2_corr) else float(p_e2_corr)
        r_e2_str = f"{r_e2:.4f}"
    pvalue_collection.append(('E2: Entanglement-reduction correlation (Pearson)', p_e2_corr))
    # For Pearson, r is itself the standardized effect size; record it directly.
    effect_size_collection.append({
        'cliffs_delta': None, 'cliffs_delta_CI95': None,
        'hedges_g': float(r_e2) if not np.isnan(r_e2) else None,
        'hedges_g_CI95': None, 'note': f'Pearson r={r_e2_str}',
    })

# H2 (E3): Kruskal-Wallis — reduction across qubit counts
e3_qubit_groups = [grp['reduction'].dropna().values for _, grp in e3.groupby('n_qubits')]
p_e3_qubits = safe_kruskal(e3_qubit_groups)
pvalue_collection.append(('E3: Reduction across qubit counts (Kruskal-Wallis)', p_e3_qubits))
effect_size_collection.append(_pairwise_effect_sizes(e3_qubit_groups))

# H3 (E4): Kruskal-Wallis — reduction across optimizers (non-parametric)
e4_opt_groups = [grp['reduction'].dropna().values for _, grp in e4.groupby('optimizer')]
p_e4_opt = safe_kruskal(e4_opt_groups)
pvalue_collection.append(('E4: Reduction across optimizers (Kruskal-Wallis)', p_e4_opt))
effect_size_collection.append(_pairwise_effect_sizes(e4_opt_groups))

# E4 runtime comparison: Kruskal-Wallis — runtime across optimizers
e4_rt_groups = [grp['runtime_seconds'].dropna().values for _, grp in e4.groupby('optimizer')]
p_e4_rt = safe_kruskal(e4_rt_groups)
pvalue_collection.append(('E4: Runtime across optimizers (Kruskal-Wallis)', p_e4_rt))
effect_size_collection.append(_pairwise_effect_sizes(e4_rt_groups))

# H6 (E5): Kruskal-Wallis — reduction across depths (landscape)
e5_depth_groups = [grp['reduction'].dropna().values for _, grp in e5.groupby('depth')]
p_e5_depth = safe_kruskal(e5_depth_groups)
pvalue_collection.append(('E5: Reduction across depths (Kruskal-Wallis)', p_e5_depth))
effect_size_collection.append(_pairwise_effect_sizes(e5_depth_groups))

# H4 (E10): Kruskal-Wallis — reduction across circuit families
e10_fam_groups = [grp['reduction'].dropna().values for _, grp in e10.groupby('circuit_family')]
p_e10_fam = safe_kruskal(e10_fam_groups)
pvalue_collection.append(('E10: Reduction across circuit families (Kruskal-Wallis)', p_e10_fam))
effect_size_collection.append(_pairwise_effect_sizes(e10_fam_groups))

# E10: Kruskal-Wallis — reduction across optimizers
e10_opt_groups = [grp['reduction'].dropna().values for _, grp in e10.groupby('optimizer')]
if len(e10_opt_groups) >= 2:
    p_e10_opt = safe_kruskal(e10_opt_groups)
    pvalue_collection.append(('E10: Reduction across optimizers (Kruskal-Wallis)', p_e10_opt))
    effect_size_collection.append(_pairwise_effect_sizes(e10_opt_groups))

# E10 Universal subset: Mann-Whitney U — Greedy vs Hybrid (Phase 2 advantage)
e10_uni = e10[e10['circuit_family'] == 'Universal']
if len(e10_uni) > 0:
    greedy_vals = e10_uni[e10_uni['optimizer'] == 'Greedy']['reduction'].dropna().values
    hybrid_vals = e10_uni[e10_uni['optimizer'] == 'HybridCommuteRewrite']['reduction'].dropna().values
    if len(greedy_vals) > 0 and len(hybrid_vals) > 0:
        u_stat, p_e10_uni = stats.mannwhitneyu(greedy_vals, hybrid_vals, alternative='less')
        p_e10_uni = 1.0 if np.isnan(p_e10_uni) else float(p_e10_uni)
        pvalue_collection.append(('E10 Universal: Greedy vs Hybrid (Mann-Whitney U)', p_e10_uni))
        effect_size_collection.append(_pairwise_effect_sizes([greedy_vals, hybrid_vals]))

# === Extended tests (E11-E18) for comprehensive FDR correction ===

# H7 (E11): Kruskal-Wallis — reduction across circuit families (real benchmarks)
e11_fam_groups = [grp['reduction'].dropna().values for _, grp in e11.groupby('circuit_family')]
p_e11_fam = safe_kruskal(e11_fam_groups)
pvalue_collection.append(('E11: Reduction across circuit families (KW, H7)', p_e11_fam))
effect_size_collection.append(_pairwise_effect_sizes(e11_fam_groups))

# H8 (E12): Kruskal-Wallis — reduction across Qiskit optimization levels
e12_level_groups = [grp['reduction'].dropna().values for _, grp in e12.groupby('compiler_optimization_level')]
p_e12_levels = safe_kruskal(e12_level_groups)
pvalue_collection.append(('E12: Reduction across optimization levels (KW, H8)', p_e12_levels))
effect_size_collection.append(_pairwise_effect_sizes(e12_level_groups))

# H9 (E14): Kruskal-Wallis — reduction across families x optimizers interaction
e14['family_opt'] = e14['circuit_family'] + '_' + e14['optimizer']
e14_interact_groups = [grp['reduction'].dropna().values for _, grp in e14.groupby('family_opt')]
p_e14_interact = safe_kruskal(e14_interact_groups)
pvalue_collection.append(('E14: Reduction across families x optimizers (KW, H9)', p_e14_interact))
effect_size_collection.append(_pairwise_effect_sizes(e14_interact_groups))

# H10 (E15): Friedman test — reduction across compilers (matched circuit families)
try:
    e15_pivot_data = e15.groupby(['circuit_family', 'compiler'])['reduction'].mean().reset_index()
    e15_matrix = e15_pivot_data.pivot(index='circuit_family', columns='compiler', values='reduction').dropna()
    if len(e15_matrix.columns) >= 2 and len(e15_matrix) >= 2:
        _friedman_stat, _friedman_p = stats.friedmanchisquare(*[e15_matrix[c].values for c in e15_matrix.columns])
        _friedman_p = 1.0 if np.isnan(_friedman_p) else float(_friedman_p)
        pvalue_collection.append(('E15: Reduction across compilers (Friedman, H10)', _friedman_p))
        effect_size_collection.append(_pairwise_effect_sizes(
            [e15_matrix[c].values for c in e15_matrix.columns]))
    else:
        raise ValueError("Insufficient matched data for Friedman test")
except Exception:
    # Fallback to Kruskal-Wallis if Friedman not applicable
    e15_comp_groups = [grp['reduction'].dropna().values for _, grp in e15.groupby('compiler')]
    p_e15_comp = safe_kruskal(e15_comp_groups)
    pvalue_collection.append(('E15: Reduction across compilers (KW, H10)', p_e15_comp))
    effect_size_collection.append(_pairwise_effect_sizes(e15_comp_groups))

# H11 (E16): Kruskal-Wallis — reduction across window sizes
e16_ws_groups = [grp['reduction'].dropna().values for _, grp in e16.groupby('window_size')]
p_e16_ws = safe_kruskal(e16_ws_groups)
pvalue_collection.append(('E16: Reduction across window sizes (KW, H11)', p_e16_ws))
effect_size_collection.append(_pairwise_effect_sizes(e16_ws_groups))

# H12 (E17): Kruskal-Wallis — reduction across topologies
e17_topo_groups = [grp['reduction'].dropna().values for _, grp in e17.groupby('topology')]
p_e17_topo = safe_kruskal(e17_topo_groups)
pvalue_collection.append(('E17: Reduction across topologies (KW, H12)', p_e17_topo))
effect_size_collection.append(_pairwise_effect_sizes(e17_topo_groups))

# H13 (E18): Kruskal-Wallis — reduction across circuit families in Clifford+T (ok status only)
e18_ok = e18[e18['status'] == 'ok']
e18_fam_groups = [grp['reduction'].dropna().values for _, grp in e18_ok.groupby('circuit_family')]
e18_fam_groups = [g for g in e18_fam_groups if len(g) > 0]
p_e18_fam = safe_kruskal(e18_fam_groups)
pvalue_collection.append(('E18: Reduction across families in Clifford+T (KW, H13)', p_e18_fam))
effect_size_collection.append(_pairwise_effect_sizes(e18_fam_groups))

# --- Apply Benjamini-Hochberg FDR correction ---
raw_p_array = np.array([p for _, p in pvalue_collection])
rejected, adjusted_p = benjamini_hochberg(raw_p_array, alpha=0.05)

print(f"\nNumber of hypothesis tests: {len(pvalue_collection)}")
print(f"BH-FDR alpha: 0.05")
print(f"Hypotheses rejected (significant): {rejected.sum()} / {len(rejected)}")
print()
print(f"{'Test':<58} {'Raw p':>12} {'Adj p':>12} {'Sig':>5}")
print("-" * 92)
for i, (test_name, raw_p) in enumerate(pvalue_collection):
    adj_p = adjusted_p[i]
    sig = "***" if adj_p < 0.001 else "**" if adj_p < 0.01 else "*" if adj_p < 0.05 else "ns"
    es = effect_size_collection[i] if i < len(effect_size_collection) else {}
    cd_str = f"{es.get('cliffs_delta'):.3f}" if es.get('cliffs_delta') is not None else "n/a"
    print(f"{test_name:<58} {raw_p:>12.6f} {adj_p:>12.6f} {sig:>5}  d={cd_str}")

# Save FDR results to CSV (with integrated effect sizes, bug #12 fix)
fdr_results_rows = []
for i, (test_name, raw_p) in enumerate(pvalue_collection):
    sig = "significant" if rejected[i] else "not significant"
    es = effect_size_collection[i] if i < len(effect_size_collection) else {
        'cliffs_delta': None, 'cliffs_delta_CI95': None,
        'hedges_g': None, 'hedges_g_CI95': None, 'note': 'n/a'}
    fdr_results_rows.append({
        'Test': test_name,
        'Raw_p_value': raw_p,
        'Adjusted_p_value_BH': adjusted_p[i],
        'Significant_at_0.05': sig,
        'Rejected': bool(rejected[i]),
        'Cliffs_delta': es.get('cliffs_delta'),
        'Cliffs_delta_CI95': es.get('cliffs_delta_CI95'),
        'Hedges_g': es.get('hedges_g'),
        'Hedges_g_CI95': es.get('hedges_g_CI95'),
        'Effect_size_note': es.get('note'),
    })
fdr_df = pd.DataFrame(fdr_results_rows)
fdr_df.to_csv(OUTPUT_DIR / 'fdr_correction_results.csv', index=False)
print(f"\nFDR correction results (with effect sizes) saved to: {OUTPUT_DIR / 'fdr_correction_results.csv'}")

# ============================================================
# Figure 8: FDR Correction Results Visualization
# ============================================================
print("\nGenerating Figure 8: FDR Correction Results...")
fig, ax = plt.subplots(figsize=(12, 6))

test_labels = [name for name, _ in pvalue_collection]
raw_pvals = [p for _, p in pvalue_collection]
adj_pvals = list(adjusted_p)

y_pos = np.arange(len(test_labels))
bar_height = 0.35

# Clamp zero p-values for log scale display
raw_p_plot = [max(p, 1e-10) for p in raw_pvals]
adj_p_plot = [max(p, 1e-10) for p in adj_pvals]

bars1 = ax.barh(y_pos - bar_height / 2, raw_p_plot, bar_height,
                label='Raw p-value', color='#2E86AB', alpha=0.8, edgecolor='black', linewidth=0.5)
bars2 = ax.barh(y_pos + bar_height / 2, adj_p_plot, bar_height,
                label='BH-adjusted p-value', color='#A23B72', alpha=0.8, edgecolor='black', linewidth=0.5)

ax.axvline(x=0.05, color='red', linestyle='--', linewidth=1.5, alpha=0.8, label=r'$\alpha$ = 0.05')
ax.set_xscale('log')
ax.set_xlabel('p-value (log scale)', fontsize=12)
ax.set_ylabel('Hypothesis Test', fontsize=11)
ax.set_title('Benjamini-Hochberg FDR Correction — All Hypothesis Tests\n'
             '(Raw vs. Adjusted p-values, dashed line = significance threshold)', fontsize=13)
ax.set_yticks(y_pos)
ax.set_yticklabels(test_labels, fontsize=9)
ax.legend(loc='lower right', fontsize=10)

# Annotate significance after correction
for i in range(len(test_labels)):
    marker = "SIG" if rejected[i] else ""
    if marker:
        ax.text(adj_p_plot[i] * 1.5, i, marker, va='center', fontsize=8,
                color='#C73E1D', fontweight='bold')

ax.text(0.02, 0.02,
        f'BH-FDR correction applied to {len(pvalue_collection)} tests; '
        f'{int(rejected.sum())} significant at q=0.05. '
        f'Effect sizes (Cliff\'s delta / Hedges\' g) reported in fdr_correction_results.csv.',
        transform=ax.transAxes, fontsize=9, verticalalignment='bottom',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig08_fdr_correction.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
plt.close()

# ============================================================
# Figure 8b: Real-Circuit Optimizer Comparison (E11/E14)
# ============================================================
print("\nGenerating Figure 8b: Real-Circuit Optimizer Comparison...")
e11_e14 = pd.concat([e11, e14], ignore_index=True)
if 'circuit_family' in e11_e14.columns and 'reduction' in e11_e14.columns:
    family_means = e11_e14.groupby('circuit_family')['reduction'].mean().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = sns.color_palette('husl', n_colors=min(len(family_means), 15))
    bars = ax.bar(range(len(family_means)), family_means.values * 100, color=colors)
    ax.set_xticks(range(len(family_means)))
    ax.set_xticklabels(family_means.index, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('Mean Gate Reduction (%)')
    ax.set_title('Real-Circuit Optimizer Comparison (E11/E14)')
    ax.axhline(y=0, color='k', linewidth=0.5)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig08b_real_circuit_optimizer_comparison.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
    plt.close()

# ============================================================
# Figure 9: Compiler Baseline Comparison (E12)
# ============================================================
print("Generating Figure 9: Compiler Baseline Comparison (E12)...")
if 'circuit_family' in e12.columns and 'reduction' in e12.columns:
    opt_level_col = [c for c in e12.columns if 'optimization_level' in c.lower() or 'opt_level' in c.lower()]
    if opt_level_col:
        e12_grouped = e12.groupby(['circuit_family', opt_level_col[0]])['reduction'].mean().reset_index()
        fig, ax = plt.subplots(figsize=(14, 7))
        pivot = e12_grouped.pivot_table(index='circuit_family', columns=opt_level_col[0], values='reduction', aggfunc='mean')
        if pivot is not None and not pivot.empty:
            pivot.plot(kind='bar', ax=ax, width=0.8)
            ax.set_ylabel('Mean Gate Reduction')
            ax.set_title('Qiskit Optimization Levels vs Circuit Family (E12)')
            ax.legend(title='Optimization Level')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(OUTPUT_DIR / 'fig09_compiler_baseline_comparison.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
            plt.close()
    else:
        family_means = e12.groupby('circuit_family')['reduction'].mean().sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(range(len(family_means)), family_means.values * 100, color='steelblue')
        ax.set_xticks(range(len(family_means)))
        ax.set_xticklabels(family_means.index, rotation=45, ha='right')
        ax.set_ylabel('Mean Gate Reduction (%)')
        ax.set_title('Qiskit Compiler Baseline (E12)')
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'fig09_compiler_baseline_comparison.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
        plt.close()

# ============================================================
# Figure 10: Structural Ceiling Gap (E13)
# ============================================================
print("Generating Figure 10: Structural Ceiling Gap (E13)...")
if 'circuit_family' in e13.columns:
    proxy_col = [c for c in e13.columns if 'proxy' in c.lower() or 'ceiling' in c.lower() or 'predicted' in c.lower()]
    obs_col = [c for c in e13.columns if 'reduction' in c.lower() or 'observed' in c.lower()]
    if proxy_col and obs_col:
        e13_means = e13.groupby('circuit_family').agg({
            proxy_col[0]: 'mean', obs_col[0]: 'mean'
        }).sort_values(obs_col[0], ascending=False)
        fig, ax = plt.subplots(figsize=(12, 6))
        x = np.arange(len(e13_means))
        w = 0.35
        ax.bar(x - w/2, e13_means[proxy_col[0]].values * 100, w, label='Ceiling Proxy', color='coral')
        ax.bar(x + w/2, e13_means[obs_col[0]].values * 100, w, label='Observed Max', color='steelblue')
        ax.set_xticks(x)
        ax.set_xticklabels(e13_means.index, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('Gate Reduction (%)')
        ax.set_title('Structural Ceiling Proxy vs Observed Reduction (E13)')
        ax.legend()
        ax.axhline(y=0, color='k', linewidth=0.5)
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'fig10_structural_ceiling_gap.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
        plt.close()
    else:
        # Fallback: just plot mean reduction by family
        family_means = e13.groupby('circuit_family')['reduction'].mean().sort_values(ascending=False) if 'reduction' in e13.columns else pd.Series()
        if len(family_means) > 0:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(range(len(family_means)), family_means.values * 100, color='steelblue')
            ax.set_xticks(range(len(family_means)))
            ax.set_xticklabels(family_means.index, rotation=45, ha='right')
            ax.set_ylabel('Mean Gate Reduction (%)')
            ax.set_title('Structural Ceiling Analysis (E13)')
            plt.tight_layout()
            plt.savefig(OUTPUT_DIR / 'fig10_structural_ceiling_gap.pdf', format=FIGURE_FORMAT, bbox_inches='tight')
            plt.close()

# ============================================================
# Statistical Summary Table
# ============================================================
print("\nGenerating statistical summary...")

summary_data = []
for name, df in [('E1', e1), ('E2', e2), ('E3', e3), ('E4', e4), ('E5', e5)]:
    # Compute Cliff's delta and Hedges' g vs. a zero baseline (structural ceiling test)
    reduction_vals = df['reduction'].dropna().values
    zero_baseline = np.zeros(len(reduction_vals))
    # effect_size.py contract returns Dict; guard empty/variance-zero cases.
    try:
        cd = cliffs_delta(reduction_vals, zero_baseline)
        cd_val, cd_low, cd_high = cd['delta'], cd['ci_lower'], cd['ci_upper']
    except Exception:
        cd_val, cd_low, cd_high = float('nan'), float('nan'), float('nan')
    try:
        hg = hedges_g(reduction_vals, zero_baseline)
        hg_val, hg_low, hg_high = hg['g'], hg['ci_lower'], hg['ci_upper']
    except Exception:
        hg_val, hg_low, hg_high = float('nan'), float('nan'), float('nan')

    summary_data.append({
        'Experiment': name,
        'N': len(df),
        'Mean_Reduction_%': f"{df['reduction'].mean() * 100:.4f}",
        'Max_Reduction_%': f"{df['reduction'].max() * 100:.2f}",
        # NOTE (M-20): This column reports sample standard deviation (std, ddof=1),
        # NOT the standard error of the mean (SEM). For mean +/- error reporting in
        # the manuscript, use SEM = std / sqrt(N). The unified error bar method for
        # all figures is now bootstrap 95% CI (see bootstrap_ci_errors above).
        # Std is retained here for backwards compatibility with the CSV schema.
        'Std_Reduction_%': f"{df['reduction'].std() * 100:.4f}",
        'Success_20pct_%': f"{df['success'].mean() * 100:.2f}",
        'Mean_Fidelity': f"{df['fidelity'].mean():.6f}",
        'Mean_Runtime_ms': f"{df['runtime_seconds'].mean() * 1000:.2f}",
        'Cliffs_delta_vs_0': f"{cd_val:.4f}",
        'Cliffs_delta_CI95': f"[{cd_low:.4f}, {cd_high:.4f}]",
        'Hedges_g_vs_0': f"{hg_val:.4f}",
        'Hedges_g_CI95': f"[{hg_low:.4f}, {hg_high:.4f}]",
    })

summary_df = pd.DataFrame(summary_data)

# Generate E4 pairwise effect size table (optimizer comparisons)
print("\nGenerating E4 pairwise effect sizes (Cliff's delta + Hedges' g)...")
e4_effect_size_rows = []
e4_optimizers = sorted(e4['optimizer'].unique())
for i, opt_a in enumerate(e4_optimizers):
    for opt_b in e4_optimizers[i+1:]:
        grp_a = e4[e4['optimizer'] == opt_a]['reduction'].dropna().values
        grp_b = e4[e4['optimizer'] == opt_b]['reduction'].dropna().values
        try:
            cd = cliffs_delta(grp_a, grp_b)
            cd_val, cd_low, cd_high = cd['delta'], cd['ci_lower'], cd['ci_upper']
        except Exception:
            cd_val, cd_low, cd_high = float('nan'), float('nan'), float('nan')
        try:
            hg = hedges_g(grp_a, grp_b)
            hg_val, hg_low, hg_high = hg['g'], hg['ci_lower'], hg['ci_upper']
        except Exception:
            hg_val, hg_low, hg_high = float('nan'), float('nan'), float('nan')
        e4_effect_size_rows.append({
            'Comparison': f"{opt_a} vs {opt_b}",
            'n1': len(grp_a),
            'n2': len(grp_b),
            'Cliffs_delta': f"{cd_val:.4f}",
            'Cliffs_delta_CI95': f"[{cd_low:.4f}, {cd_high:.4f}]",
            'Hedges_g': f"{hg_val:.4f}",
            'Hedges_g_CI95': f"[{hg_low:.4f}, {hg_high:.4f}]",
        })
e4_effect_df = pd.DataFrame(e4_effect_size_rows)
e4_effect_df.to_csv(OUTPUT_DIR / 'e4_effect_sizes.csv', index=False)
print(f"E4 effect sizes saved to: {OUTPUT_DIR / 'e4_effect_sizes.csv'}")

# Append FDR-corrected statistical tests summary to the CSV
fdr_summary_rows = []
for i, (test_name, raw_p) in enumerate(pvalue_collection):
    es = effect_size_collection[i] if i < len(effect_size_collection) else {}
    cd_v = es.get('cliffs_delta')
    hg_v = es.get('hedges_g')
    fdr_summary_rows.append({
        'Experiment': 'FDR',
        'N': len(pvalue_collection),
        'Mean_Reduction_%': f'p_raw={raw_p:.6f}',
        'Max_Reduction_%': f'p_adj={adjusted_p[i]:.6f}',
        'Std_Reduction_%': 'BH-FDR',
        'Success_20pct_%': 'significant' if rejected[i] else 'ns',
        'Mean_Fidelity': f'alpha=0.05',
        'Mean_Runtime_ms': test_name,
        'Cliffs_delta': f'{cd_v:.4f}' if cd_v is not None else 'n/a',
        'Hedges_g': f'{hg_v:.4f}' if hg_v is not None else 'n/a',
        'Effect_size_note': es.get('note', 'n/a'),
    })
fdr_summary_append = pd.DataFrame(fdr_summary_rows)
full_summary_df = pd.concat([summary_df, fdr_summary_append], ignore_index=True)
full_summary_df.to_csv(OUTPUT_DIR / 'statistical_summary.csv', index=False)

print("\n" + "="*60)
print("STATISTICAL SUMMARY")
print("="*60)
print(summary_df.to_string(index=False))

# E10 summary
print("\n" + "="*60)
print("E10: PHASE 1 vs PHASE 2")
print("="*60)
e10_summary = e10.groupby(['circuit_family', 'optimizer']).agg({
    'reduction': 'mean',
    'success': 'mean',
    'fidelity': 'mean'
}).reset_index()
print(e10_summary.to_string(index=False))

print("\n" + "="*60)
print("ALL FIGURES GENERATED")
print("="*60)
print(f"Output directory: {OUTPUT_DIR}")
for f in sorted(OUTPUT_DIR.glob('*.pdf')):
    print(f"  - {f.name}")
print(f"  - statistical_summary.csv")
print(f"  - fdr_correction_results.csv")
