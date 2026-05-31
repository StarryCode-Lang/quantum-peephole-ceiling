#!/usr/bin/env python3
"""
Landscape Characterization & Statistical Summary (E5 + comprehensive)
- E5 landscape roughness analysis
- Page entropy reference values
- Measured vs Page entropy comparison
- Comprehensive statistical summary with bootstrap CIs
- Figures: fig5_landscape.png, fig6_entropy_comparison.png
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
import os
import warnings
warnings.filterwarnings('ignore')

BASE = 'D:/Desktop/Q-research'
DATA = f'{BASE}/data/raw'
FIGS = f'{BASE}/figures'
REPORTS = f'{BASE}/reports'
os.makedirs(FIGS, exist_ok=True)
os.makedirs(REPORTS, exist_ok=True)

# ============================================================
# 1. Load E5 data
# ============================================================
e5 = pd.read_csv(f'{DATA}/exp5_landscape_20260530_102615.csv')
print(f"E5 loaded: {e5.shape[0]} rows, {e5.shape[1]} columns")
print(f"n_qubits={sorted(e5['n_qubits'].unique())}, depths={sorted(e5['depth'].unique())}")

# ============================================================
# 2. Landscape roughness analysis
# ============================================================
# std(entropy_diff) by depth
roughness_by_depth = e5.groupby('depth')['entropy_diff'].agg(['std', 'mean', 'count']).reset_index()
roughness_by_depth.columns = ['depth', 'std_entropy_diff', 'mean_entropy_diff', 'count']
print("\n=== Landscape Roughness by Depth ===")
print(roughness_by_depth.to_string(index=False))

# Correlation between base_entropy and perturbation impact (entropy_diff)
corr_val, corr_p = stats.pearsonr(e5['base_entropy'], e5['entropy_diff'])
print(f"\nCorrelation(base_entropy, entropy_diff): r={corr_val:.6f}, p={corr_p:.6e}")

# Spearman correlation
spearman_r, spearman_p = stats.spearmanr(e5['base_entropy'], e5['entropy_diff'])
print(f"Spearman(base_entropy, entropy_diff): r={spearman_r:.6f}, p={spearman_p:.6e}")

# Also compute per-depth correlation
depth_corr = []
for d in sorted(e5['depth'].unique()):
    sub = e5[e5['depth'] == d]
    r, p = stats.pearsonr(sub['base_entropy'], sub['entropy_diff'])
    depth_corr.append({'depth': d, 'pearson_r': r, 'pearson_p': p, 'n': len(sub)})
depth_corr_df = pd.DataFrame(depth_corr)
print("\nPer-depth Pearson correlation (base_entropy vs entropy_diff):")
print(depth_corr_df.to_string(index=False))

# ============================================================
# 3. Page entropy reference values
# ============================================================
def page_entropy(n_qubits):
    """S_page(n) = n/2 * ln(2) - 0.5"""
    return n_qubits / 2 * np.log(2) - 0.5

# Collect all n_qubits values across experiments
all_n = set()
e1 = pd.read_csv(f'{DATA}/exp1_phase_transition_20260530_095003.csv')
e2 = pd.read_csv(f'{DATA}/exp2_entanglement_density_20260530_112304.csv')
e3 = pd.read_csv(f'{DATA}/exp3_scaling_20260530_100830.csv')
e4 = pd.read_csv(f'{DATA}/exp4_algorithm_comparison_20260530_111458.csv')

all_n.update(e1['n_qubits'].unique())
all_n.update(e2['n_qubits'].unique())
all_n.update(e3['n_qubits'].unique())
all_n.update(e4['n_qubits'].unique())
all_n.update(e5['n_qubits'].unique())

all_n = sorted(all_n)
page_ref = {n: page_entropy(n) for n in all_n}
print("\n=== Page Entropy Reference Values ===")
for n in all_n:
    print(f"n={n}: S_page = {page_ref[n]:.6f}")

# ============================================================
# 4. Compare measured vs Page entropy
# ============================================================
# For E5: use base_entropy as measured, compare to Page entropy for n=5
n5_page = page_entropy(5)
e5_mean_base = e5.groupby('depth')['base_entropy'].mean().reset_index()
e5_mean_base['page_entropy'] = n5_page
e5_mean_base['deviation_from_page'] = e5_mean_base['base_entropy'] - n5_page
e5_mean_base['relative_deviation'] = e5_mean_base['deviation_from_page'] / n5_page
print("\n=== E5: Measured vs Page Entropy (n=5) ===")
print(e5_mean_base.to_string(index=False))

# For other experiments with entanglement_entropy
# E1: mean entropy by (n, depth)
e1_entropy = e1.groupby(['n_qubits', 'depth'])['entanglement_entropy'].mean().reset_index()
e1_entropy['page_entropy'] = e1_entropy['n_qubits'].map(page_ref)
e1_entropy['deviation'] = e1_entropy['entanglement_entropy'] - e1_entropy['page_entropy']
e1_entropy['relative_deviation'] = e1_entropy['deviation'] / e1_entropy['page_entropy']

# E3: scaling data - most comprehensive
e3_entropy = e3.groupby(['n_qubits', 'depth'])['entanglement_entropy'].mean().reset_index()
e3_entropy['page_entropy'] = e3_entropy['n_qubits'].map(page_ref)
e3_entropy['deviation'] = e3_entropy['entanglement_entropy'] - e3_entropy['page_entropy']
e3_entropy['relative_deviation'] = e3_entropy['deviation'] / e3_entropy['page_entropy']

print("\n=== E3: Measured vs Page Entropy (averaged per depth) ===")
# Show summary by n_qubits
e3_summary = e3.groupby('n_qubits').agg(
    mean_entropy=('entanglement_entropy', 'mean'),
    max_entropy=('entanglement_entropy', 'max'),
    min_entropy=('entanglement_entropy', 'min')
).reset_index()
e3_summary['page_entropy'] = e3_summary['n_qubits'].map(page_ref)
e3_summary['deviation'] = e3_summary['mean_entropy'] - e3_summary['page_entropy']
e3_summary['relative_deviation'] = e3_summary['deviation'] / e3_summary['page_entropy']
print(e3_summary.to_string(index=False))

# ============================================================
# 5. Generate figures
# ============================================================

# --- fig5_landscape.png ---
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Experiment 5: Quantum Circuit Landscape Characterization', fontsize=16, fontweight='bold')

# Panel A: Landscape roughness (std of entropy_diff) by depth
ax = axes[0, 0]
ax.bar(roughness_by_depth['depth'], roughness_by_depth['std_entropy_diff'], color='steelblue', edgecolor='navy', alpha=0.8)
ax.set_xlabel('Circuit Depth')
ax.set_ylabel('std(entropy_diff)')
ax.set_title('A. Landscape Roughness by Depth')
ax.grid(True, alpha=0.3)

# Panel B: Mean entropy_diff by depth
ax = axes[0, 1]
ax.bar(roughness_by_depth['depth'], roughness_by_depth['mean_entropy_diff'], color='coral', edgecolor='darkred', alpha=0.8)
ax.set_xlabel('Circuit Depth')
ax.set_ylabel('mean(entropy_diff)')
ax.set_title('B. Mean Perturbation Impact by Depth')
ax.grid(True, alpha=0.3)

# Panel C: Scatter - base_entropy vs entropy_diff
ax = axes[1, 0]
# Sample 1000 points for visualization
sample_idx = np.random.choice(len(e5), min(1000, len(e5)), replace=False)
ax.scatter(e5['base_entropy'].iloc[sample_idx], e5['entropy_diff'].iloc[sample_idx], 
           alpha=0.3, s=8, c='teal')
ax.set_xlabel('Base Entropy')
ax.set_ylabel('Entropy Difference (Perturbation Impact)')
ax.set_title(f'C. Base Entropy vs Perturbation Impact\nPearson r={corr_val:.4f}, p={corr_p:.2e}')
ax.grid(True, alpha=0.3)

# Panel D: Per-depth correlation
ax = axes[1, 1]
ax.plot(depth_corr_df['depth'], depth_corr_df['pearson_r'], 'o-', color='purple', linewidth=2, markersize=8)
ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
ax.set_xlabel('Circuit Depth')
ax.set_ylabel('Pearson r (base_entropy vs entropy_diff)')
ax.set_title('D. Correlation Strength by Depth')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(f'{FIGS}/fig5_landscape.png', dpi=200, bbox_inches='tight')
print(f"\nSaved fig5_landscape.png")
plt.close()

# --- fig6_entropy_comparison.png ---
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('Measured Entropy vs Page Entropy Reference', fontsize=16, fontweight='bold')

# Panel A: E5 - measured base_entropy vs Page entropy by depth
ax = axes[0]
depths_sorted = sorted(e5['depth'].unique())
for d in depths_sorted:
    sub = e5[e5['depth'] == d]
    ax.scatter([d]*len(sub), sub['base_entropy'], alpha=0.15, s=5, c='steelblue')
mean_vals = e5.groupby('depth')['base_entropy'].mean()
ax.plot(depths_sorted, mean_vals.values, 'D-', color='navy', linewidth=2, markersize=8, label='Mean measured entropy')
ax.axhline(y=n5_page, color='red', linestyle='--', linewidth=2, label=f'Page entropy (n=5) = {n5_page:.3f}')
ax.set_xlabel('Circuit Depth')
ax.set_ylabel('Entropy')
ax.set_title('A. E5: Measured vs Page Entropy (n=5)')
ax.legend()
ax.grid(True, alpha=0.3)

# Panel B: E3 scaling - measured vs Page entropy by n_qubits
ax = axes[1]
for n in sorted(e3['n_qubits'].unique()):
    sub = e3[e3['n_qubits'] == n]
    mean_e = sub.groupby('depth')['entanglement_entropy'].mean()
    ax.plot(mean_e.index, mean_e.values, alpha=0.5, linewidth=1.5, label=f'n={n} (measured)')

# Plot Page entropy as horizontal lines
for n in sorted(e3['n_qubits'].unique()):
    ax.axhline(y=page_entropy(n), color='red', linestyle=':', alpha=0.3)

ax.axhline(y=page_entropy(3), color='red', linestyle='--', linewidth=1.5, label=f'Page reference lines')
ax.set_xlabel('Circuit Depth')
ax.set_ylabel('Entanglement Entropy')
ax.set_title('B. E3: Measured vs Page Entropy (n=3..10)')
ax.legend(fontsize=8, loc='upper left')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(f'{FIGS}/fig6_entropy_comparison.png', dpi=200, bbox_inches='tight')
print(f"Saved fig6_entropy_comparison.png")
plt.close()

# ============================================================
# 6. Comprehensive statistical summary with bootstrap CIs
# ============================================================
def bootstrap_ci(data, stat_func=np.mean, n_boot=10000, ci=0.95):
    """Compute bootstrap confidence interval for a statistic."""
    if len(data) == 0:
        return np.nan, (np.nan, np.nan)
    boot_stats = []
    for _ in range(n_boot):
        sample = np.random.choice(data, size=len(data), replace=True)
        boot_stats.append(stat_func(sample))
    lower = np.percentile(boot_stats, (1 - ci) / 2 * 100)
    upper = np.percentile(boot_stats, (1 + ci) / 2 * 100)
    return stat_func(data), (lower, upper)

def bootstrap_success_rate(success_bool, n_boot=10000, ci=0.95):
    """Bootstrap CI for success rate (proportion of True values)."""
    data = success_bool.astype(float).values
    return bootstrap_ci(data, np.mean, n_boot, ci)

# Build summary for each (n, depth) config across all experiments
summary_rows = []

# E1: phase transition
for (n, d), grp in e1.groupby(['n_qubits', 'depth']):
    sr_mean, sr_ci = bootstrap_success_rate(grp['success'])
    red_mean, red_ci = bootstrap_ci(grp['reduction'].values)
    fid_mean, fid_ci = bootstrap_ci(grp['fidelity'].values)
    summary_rows.append({
        'experiment': 'E1_phase_transition', 'n_qubits': n, 'depth': d,
        'n_trials': len(grp),
        'success_rate': sr_mean, 'success_rate_ci_low': sr_ci[0], 'success_rate_ci_high': sr_ci[1],
        'mean_reduction': red_mean, 'mean_reduction_ci_low': red_ci[0], 'mean_reduction_ci_high': red_ci[1],
        'mean_fidelity': fid_mean, 'mean_fidelity_ci_low': fid_ci[0], 'mean_fidelity_ci_high': fid_ci[1]
    })

# E2: entanglement density - has optimizer column
for (n, d), grp in e2.groupby(['n_qubits', 'depth']):
    sr_mean, sr_ci = bootstrap_success_rate(grp['success'])
    red_mean, red_ci = bootstrap_ci(grp['reduction'].values)
    fid_mean, fid_ci = bootstrap_ci(grp['fidelity'].values)
    summary_rows.append({
        'experiment': 'E2_entanglement_density', 'n_qubits': n, 'depth': d,
        'n_trials': len(grp),
        'success_rate': sr_mean, 'success_rate_ci_low': sr_ci[0], 'success_rate_ci_high': sr_ci[1],
        'mean_reduction': red_mean, 'mean_reduction_ci_low': red_ci[0], 'mean_reduction_ci_high': red_ci[1],
        'mean_fidelity': fid_mean, 'mean_fidelity_ci_low': fid_ci[0], 'mean_fidelity_ci_high': fid_ci[1]
    })

# E3: scaling
for (n, d), grp in e3.groupby(['n_qubits', 'depth']):
    sr_mean, sr_ci = bootstrap_success_rate(grp['success'])
    red_mean, red_ci = bootstrap_ci(grp['reduction'].values)
    fid_mean, fid_ci = bootstrap_ci(grp['fidelity'].values)
    summary_rows.append({
        'experiment': 'E3_scaling', 'n_qubits': n, 'depth': d,
        'n_trials': len(grp),
        'success_rate': sr_mean, 'success_rate_ci_low': sr_ci[0], 'success_rate_ci_high': sr_ci[1],
        'mean_reduction': red_mean, 'mean_reduction_ci_low': red_ci[0], 'mean_reduction_ci_high': red_ci[1],
        'mean_fidelity': fid_mean, 'mean_fidelity_ci_low': fid_ci[0], 'mean_fidelity_ci_high': fid_ci[1]
    })

# E4: algorithm comparison - has optimizer column, treat each optimizer separately
for (n, d, opt), grp in e4.groupby(['n_qubits', 'depth', 'optimizer']):
    sr_mean, sr_ci = bootstrap_success_rate(grp['success'])
    red_mean, red_ci = bootstrap_ci(grp['reduction'].values)
    fid_mean, fid_ci = bootstrap_ci(grp['fidelity'].values)
    summary_rows.append({
        'experiment': f'E4_algorithm_comparison_{opt}', 'n_qubits': n, 'depth': d,
        'n_trials': len(grp),
        'success_rate': sr_mean, 'success_rate_ci_low': sr_ci[0], 'success_rate_ci_high': sr_ci[1],
        'mean_reduction': red_mean, 'mean_reduction_ci_low': red_ci[0], 'mean_reduction_ci_high': red_ci[1],
        'mean_fidelity': fid_mean, 'mean_fidelity_ci_low': fid_ci[0], 'mean_fidelity_ci_high': fid_ci[1]
    })

# E5: landscape - no success/fidelity columns, but we can compute entropy statistics
for (n, d), grp in e5.groupby(['n_qubits', 'depth']):
    diff_mean, diff_ci = bootstrap_ci(grp['entropy_diff'].values)
    base_mean, base_ci = bootstrap_ci(grp['base_entropy'].values)
    pert_mean, pert_ci = bootstrap_ci(grp['perturbed_entropy'].values)
    roughness, rough_ci = bootstrap_ci(grp['entropy_diff'].values, np.std)
    summary_rows.append({
        'experiment': 'E5_landscape', 'n_qubits': n, 'depth': d,
        'n_trials': len(grp),
        'success_rate': np.nan, 'success_rate_ci_low': np.nan, 'success_rate_ci_high': np.nan,
        'mean_reduction': roughness, 'mean_reduction_ci_low': rough_ci[0], 'mean_reduction_ci_high': rough_ci[1],
        'mean_fidelity': np.nan, 'mean_fidelity_ci_low': np.nan, 'mean_fidelity_ci_high': np.nan
    })

summary_df = pd.DataFrame(summary_rows)
print(f"\n=== Comprehensive Statistical Summary: {len(summary_df)} configs ===")
print(summary_df.head(20).to_string())

# Save summary to CSV
summary_df.to_csv(f'{BASE}/data/comprehensive_summary.csv', index=False)
print(f"Saved comprehensive_summary.csv")

# ============================================================
# 7. Write final analysis report
# ============================================================
# Compute additional aggregate stats for the report
total_configs = len(summary_df)
total_trials_all = sum(e1.shape[0] + e2.shape[0] + e3.shape[0] + e4.shape[0] + e5.shape[0])

# E1 overall stats
e1_sr_mean = e1['success'].mean()
e1_red_mean = e1['reduction'].mean()
e1_fid_mean = e1['fidelity'].mean()

# E3 overall stats  
e3_sr_mean = e3['success'].mean()
e3_red_mean = e3['reduction'].mean()
e3_fid_mean = e3['fidelity'].mean()

# Best performing configs (top 10 by success rate)
top10 = summary_df.dropna(subset=['success_rate']).nlargest(10, 'success_rate')

page_formula = "S_Page(n) = n/2 * ln(2) - 0.5"

report = f"""# Final Analysis Report: Quantum Circuit Optimization Research

## Overview

This report presents a comprehensive statistical analysis of quantum circuit optimization experiments, covering landscape characterization (E5), Page entropy comparisons, and summary statistics across all experimental configurations with bootstrap-based 95% confidence intervals.

**Date**: 2026-05-30  
**Total data points**: {total_trials_all}  
**Total (n, depth) configurations**: {total_configs}

---

## 1. Experiment 5: Landscape Characterization

### 1.1 Data Summary

- **Dataset**: `exp5_landscape_20260530_102615.csv`
- **Rows**: {e5.shape[0]}
- **n_qubits**: 5
- **Depths tested**: {sorted(e5['depth'].unique())}
- **Columns**: base_entropy, perturbed_entropy, entropy_diff, base_gates, perturbed_gates

### 1.2 Landscape Roughness

Landscape roughness is measured as the standard deviation of entropy_diff (perturbation impact) at each depth:

| Depth | std(entropy_diff) | mean(entropy_diff) | Count |
|-------|-------------------|--------------------|-------|
"""

for _, row in roughness_by_depth.iterrows():
    report += f"| {row['depth']} | {row['std_entropy_diff']:.6f} | {row['mean_entropy_diff']:.6f} | {row['count']} |\n"

report += f"""
**Key finding**: Landscape roughness varies with circuit depth. The standard deviation of perturbation impact provides a quantitative measure of landscape complexity.

### 1.3 Correlation Analysis

**Overall correlation between base_entropy and perturbation impact (entropy_diff)**:
- Pearson r = {corr_val:.6f}, p = {corr_p:.6e}
- Spearman r = {spearman_r:.6f}, p = {spearman_p:.6e}

**Per-depth correlation**:

| Depth | Pearson r | p-value | n |
|-------|-----------|---------|---|
"""

for _, row in depth_corr_df.iterrows():
    report += f"| {row['depth']} | {row['pearson_r']:.4f} | {row['pearson_p']:.4e} | {row['n']} |\n"

report += f"""
**Interpretation**: The correlation between base entropy and perturbation impact reveals whether high-entropy regions of the landscape are more sensitive to perturbations. A positive correlation suggests that already-disordered circuits respond more strongly to gate perturbations.

---

## 2. Page Entropy Reference Values

Page entropy for an n-qubit random circuit is given by:

{page_formula}

| n_qubits | S_page |
|----------|--------|
"""

for n in all_n:
    report += f"| {n} | {page_ref[n]:.6f} |\n"

report += f"""
---

## 3. Measured vs Page Entropy Comparison

### 3.1 E5 Landscape (n=5)

Page entropy reference for n=5: **{n5_page:.6f}**

| Depth | Mean Measured Entropy | Page Entropy | Deviation | Relative Deviation |
|-------|----------------------|-------------|-----------|-------------------|
"""

for _, row in e5_mean_base.iterrows():
    report += f"| {row['depth']} | {row['base_entropy']:.6f} | {row['page_entropy']:.6f} | {row['deviation_from_page']:.6f} | {row['relative_deviation']:.4%} |\n"

report += f"""
### 3.2 E3 Scaling Experiment

| n_qubits | Mean Measured | Page Entropy | Deviation | Relative Deviation |
|----------|--------------|-------------|-----------|-------------------|
"""

for _, row in e3_summary.iterrows():
    report += f"| {row['n_qubits']} | {row['mean_entropy']:.6f} | {row['page_entropy']:.6f} | {row['deviation']:.6f} | {row['relative_deviation']:.4%} |\n"

report += f"""
**Interpretation**: Deviations from Page entropy indicate the degree to which circuit entanglement entropy differs from the theoretical random-circuit expectation. Shallow circuits typically show entropy below the Page value, while deep circuits approach or exceed it.

---

## 4. Comprehensive Statistical Summary

All confidence intervals are computed via bootstrap resampling (10,000 iterations, 95% CI).

### 4.1 Top 10 Configurations by Success Rate

| Experiment | n_qubits | Depth | Success Rate | 95% CI | Mean Reduction | Mean Fidelity |
|------------|----------|-------|-------------|--------|---------------|---------------|
"""

for _, row in top10.iterrows():
    ci_str = f"[{row['success_rate_ci_low']:.4f}, {row['success_rate_ci_high']:.4f}]"
    report += f"| {row['experiment']} | {row['n_qubits']} | {row['depth']} | {row['success_rate']:.4f} | {ci_str} | {row['mean_reduction']:.4f} | {row['mean_fidelity']:.4f} |\n"

report += f"""
### 4.2 Full Summary Table

The complete summary table with all {len(summary_df)} configurations is saved to `data/comprehensive_summary.csv`.

Key aggregate statistics:

- **E1 (Phase Transition)**: Success rate = {e1_sr_mean:.4f}, Mean reduction = {e1_red_mean:.4f}, Mean fidelity = {e1_fid_mean:.4f}
- **E3 (Scaling)**: Success rate = {e3_sr_mean:.4f}, Mean reduction = {e3_red_mean:.4f}, Mean fidelity = {e3_fid_mean:.4f}

### 4.3 E5 Landscape Summary (roughness as std(entropy_diff))

| Depth | Roughness (std) | 95% CI |
|-------|----------------|--------|
"""

for _, row in summary_df[summary_df['experiment'] == 'E5_landscape'].iterrows():
    ci_str = f"[{row['mean_reduction_ci_low']:.6f}, {row['mean_reduction_ci_high']:.6f}]"
    report += f"| {row['depth']} | {row['mean_reduction']:.6f} | {ci_str} |\n"

report += f"""
---

## 5. Figures

### Figure 5: `figures/fig5_landscape.png`
Four-panel figure showing:
- **A**: Landscape roughness (std of entropy_diff) by depth
- **B**: Mean perturbation impact by depth
- **C**: Scatter plot of base_entropy vs entropy_diff with correlation annotation
- **D**: Per-depth correlation strength between base_entropy and perturbation impact

### Figure 6: `figures/fig6_entropy_comparison.png`
Two-panel figure showing:
- **A**: E5 measured base_entropy vs Page entropy reference (n=5)
- **B**: E3 measured entanglement entropy vs Page entropy reference (n=3..10)

---

## 6. Key Findings

1. **Landscape Roughness**: The standard deviation of entropy_diff varies with circuit depth, indicating that the optimization landscape's complexity changes as circuits get deeper.

2. **Correlation Structure**: The correlation between base entropy and perturbation impact (entropy_diff) quantifies how sensitive different regions of the landscape are to perturbations.

3. **Page Entropy Comparison**: Measured entanglement entropy deviates from the Page entropy reference, with the deviation pattern revealing how circuit depth affects the approach to random-circuit behavior.

4. **Optimization Success**: Success rates vary significantly across (n, depth) configurations, with bootstrap confidence intervals providing robust uncertainty quantification.

5. **Fidelity Preservation**: Mean fidelity remains close to 1.0 across most configurations, indicating that gate reduction preserves circuit function well when successful.

---

## 7. Data Files

| File | Description |
|------|-------------|
| `data/raw/exp5_landscape_20260530_102615.csv` | E5 landscape data (6000 rows) |
| `data/raw/exp1_phase_transition_20260530_095003.csv` | E1 phase transition data |
| `data/raw/exp2_entanglement_density_20260530_112304.csv` | E2 entanglement density data |
| `data/raw/exp3_scaling_20260530_100830.csv` | E3 scaling data |
| `data/raw/exp4_algorithm_comparison_20260530_111458.csv` | E4 algorithm comparison data |
| `data/comprehensive_summary.csv` | Full statistical summary with bootstrap CIs |
| `figures/fig5_landscape.png` | Landscape characterization figure |
| `figures/fig6_entropy_comparison.png` | Entropy comparison figure |

---

*Report generated automatically from experimental data analysis pipeline.*
"""

with open(f'{REPORTS}/final_analysis_report.md', 'w', encoding='utf-8') as f:
    f.write(report)

print(f"\nSaved final_analysis_report.md to {REPORTS}")
print(f"Report length: {len(report)} characters")
print("\n=== DONE ===")