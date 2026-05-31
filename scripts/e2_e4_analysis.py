"""
Entanglement Density & Algorithm Comparison Analysis (E2+E4)
- Load E2 data, plot success_rate vs entanglement_density per optimizer
- Calculate correlation between density and optimization metrics
- Load E4 data, compare optimizers
- Paired Wilcoxon signed-rank tests
- Bootstrap CIs for all metrics
- Generate fig3_density_sweep.png, fig4_algorithm_comparison.png
"""

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import json
import os

# Use science style
try:
    plt.style.use('science')
except OSError:
    plt.style.use('seaborn-v0_8-paper')
plt.rcParams.update({
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'font.size': 10,
    'axes.labelsize': 11,
    'legend.fontsize': 9,
    'figure.figsize': (7, 5),
})

DATA_DIR = 'D:/Desktop/Q-research/data/raw'
FIG_DIR = 'D:/Desktop/Q-research/figures/final'
PROC_DIR = 'D:/Desktop/Q-research/data/processed'

os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(PROC_DIR, exist_ok=True)

# ============================================================
# 1. Load E2 data
# ============================================================
e2 = pd.read_csv(os.path.join(DATA_DIR, 'exp2_entanglement_density_20260530_112304.csv'))
print(f"E2 data: {e2.shape[0]} rows, {e2.shape[1]} columns")
print(f"Optimizers: {e2['optimizer'].unique()}")
print(f"Density range: {e2['entanglement_density'].min()} - {e2['entanglement_density'].max()}")

# ============================================================
# 2. Plot success_rate vs entanglement_density for each optimizer
# ============================================================
# Group by density and optimizer, compute mean success rate
e2_grouped = e2.groupby(['entanglement_density', 'optimizer']).agg(
    success_rate=('success', 'mean'),
    mean_reduction=('reduction', 'mean'),
    mean_fidelity=('fidelity', 'mean'),
    mean_runtime=('runtime', 'mean'),
    std_success=('success', 'std'),
    std_reduction=('reduction', 'std'),
    n_trials=('success', 'count')
).reset_index()

# Also compute per-density overall stats
e2_density_stats = e2.groupby('entanglement_density').agg(
    success_rate=('success', 'mean'),
    mean_reduction=('reduction', 'mean'),
    mean_fidelity=('fidelity', 'mean'),
    mean_entropy=('entanglement_entropy', 'mean'),
    n_trials=('success', 'count')
).reset_index()

# Figure 3: Density sweep
fig, axes = plt.subplots(2, 2, figsize=(10, 8))

# Panel (a): Success rate vs density
ax = axes[0, 0]
for opt in e2['optimizer'].unique():
    sub = e2_grouped[e2_grouped['optimizer'] == opt]
    ax.errorbar(sub['entanglement_density'], sub['success_rate'],
                yerr=sub['std_success']/np.sqrt(sub['n_trials']),
                marker='o', capsize=3, label=opt, linewidth=1.5)
ax.set_xlabel('Entanglement Density')
ax.set_ylabel('Success Rate')
ax.set_title('(a) Success Rate vs Density')
ax.legend()
ax.set_xlim(-0.05, 1.05)

# Panel (b): Mean reduction vs density
ax = axes[0, 1]
for opt in e2['optimizer'].unique():
    sub = e2_grouped[e2_grouped['optimizer'] == opt]
    ax.plot(sub['entanglement_density'], sub['mean_reduction'],
            marker='s', label=opt, linewidth=1.5)
ax.set_xlabel('Entanglement Density')
ax.set_ylabel('Mean Gate Reduction')
ax.set_title('(b) Reduction vs Density')
ax.legend()

# Panel (c): Mean fidelity vs density
ax = axes[1, 0]
for opt in e2['optimizer'].unique():
    sub = e2_grouped[e2_grouped['optimizer'] == opt]
    ax.plot(sub['entanglement_density'], sub['mean_fidelity'],
            marker='^', label=opt, linewidth=1.5)
ax.set_xlabel('Entanglement Density')
ax.set_ylabel('Mean Fidelity')
ax.set_title('(c) Fidelity vs Density')
ax.legend()
ax.set_ylim(0.995, 1.001)

# Panel (d): Runtime vs density
ax = axes[1, 1]
for opt in e2['optimizer'].unique():
    sub = e2_grouped[e2_grouped['optimizer'] == opt]
    ax.plot(sub['entanglement_density'], sub['mean_runtime'],
            marker='D', label=opt, linewidth=1.5)
ax.set_xlabel('Entanglement Density')
ax.set_ylabel('Mean Runtime (s)')
ax.set_title('(d) Runtime vs Density')
ax.legend()

fig.suptitle('Experiment 2: Entanglement Density Sweep (n=6, d=20)', fontsize=13, y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'fig3_density_sweep.png'), bbox_inches='tight')
print(f"Saved fig3_density_sweep.png")
plt.close(fig)

# ============================================================
# 3. Correlation between density and optimization metrics
# ============================================================
corr_results = {}
for opt in e2['optimizer'].unique():
    sub = e2[e2['optimizer'] == opt]
    for metric in ['reduction', 'fidelity', 'runtime', 'success']:
        r, p = stats.pearsonr(sub['entanglement_density'], sub[metric])
        rho, p_spearman = stats.spearmanr(sub['entanglement_density'], sub[metric])
        corr_results[f"{opt}_{metric}"] = {
            'pearson_r': r, 'pearson_p': p,
            'spearman_rho': rho, 'spearman_p': p_spearman
        }

print("\n=== Correlation Analysis (E2) ===")
for key, val in corr_results.items():
    print(f"  {key}: Pearson r={val['pearson_r']:.4f} (p={val['pearson_p']:.4e}), "
          f"Spearman rho={val['spearman_rho']:.4f} (p={val['spearman_p']:.4e})")

# ============================================================
# 4. Load E4 data
# ============================================================
e4 = pd.read_csv(os.path.join(DATA_DIR, 'exp4_algorithm_comparison_20260530_111458.csv'))
print(f"\nE4 data: {e4.shape[0]} rows, {e4.shape[1]} columns")
print(f"Optimizers: {e4['optimizer'].unique()}")

# ============================================================
# 5. Compare optimizers: mean reduction, mean fidelity, success rate, runtime
# ============================================================
optimizer_stats = e4.groupby('optimizer').agg(
    mean_reduction=('reduction', 'mean'),
    std_reduction=('reduction', 'std'),
    mean_fidelity=('fidelity', 'mean'),
    std_fidelity=('fidelity', 'std'),
    success_rate=('success', 'mean'),
    mean_runtime=('runtime', 'mean'),
    std_runtime=('runtime', 'std'),
    n_trials=('trial', 'count')
).reset_index()

print("\n=== Optimizer Comparison (E4) ===")
print(optimizer_stats.to_string(index=False))

# ============================================================
# 6. Paired Wilcoxon signed-rank tests between optimizers
# ============================================================
optimizers = sorted(e4['optimizer'].unique())
wilcoxon_results = {}

# For paired tests, we match on (n_qubits, depth, trial) - same problem instance
metrics_to_test = ['reduction', 'fidelity', 'runtime']

for i, opt1 in enumerate(optimizers):
    for j, opt2 in enumerate(optimizers):
        if i >= j:
            continue
        for metric in metrics_to_test:
            data1 = e4[e4['optimizer'] == opt1].sort_values(['n_qubits', 'depth', 'trial'])[metric].values
            data2 = e4[e4['optimizer'] == opt2].sort_values(['n_qubits', 'depth', 'trial'])[metric].values
            # Ensure same number of paired observations
            min_len = min(len(data1), len(data2))
            data1 = data1[:min_len]
            data2 = data2[:min_len]
            diff = data1 - data2
            # Skip if all diffs are zero (Wilcoxon can't handle that)
            if np.all(diff == 0):
                stat_val = 0
                p_val = 1.0
            else:
                try:
                    stat_val, p_val = stats.wilcoxon(data1, data2, alternative='two-sided')
                except ValueError:
                    stat_val, p_val = 0, 1.0
            key = f"{opt1}_vs_{opt2}_{metric}"
            wilcoxon_results[key] = {'statistic': stat_val, 'p_value': p_val}

print("\n=== Wilcoxon Signed-Rank Tests (E4) ===")
for key, val in wilcoxon_results.items():
    sig = "***" if val['p_value'] < 0.001 else "**" if val['p_value'] < 0.01 else "*" if val['p_value'] < 0.05 else ""
    print(f"  {key}: W={val['statistic']:.2f}, p={val['p_value']:.4e} {sig}")

# ============================================================
# 7. Bootstrap CIs for all metrics
# ============================================================
np.random.seed(42)
n_bootstrap = 10000
bootstrap_results = {}

for opt in optimizers:
    opt_data = e4[e4['optimizer'] == opt]
    for metric in metrics_to_test + ['success']:
        values = opt_data[metric].values
        boots = np.random.choice(values, size=(n_bootstrap, len(values)), replace=True)
        boot_means = boots.mean(axis=1)
        ci_low = np.percentile(boot_means, 2.5)
        ci_high = np.percentile(boot_means, 97.5)
        bootstrap_results[f"{opt}_{metric}"] = {
            'mean': float(np.mean(values)),
            'ci_low': float(ci_low),
            'ci_high': float(ci_high)
        }

print("\n=== Bootstrap 95% CIs (E4) ===")
for key, val in bootstrap_results.items():
    print(f"  {key}: mean={val['mean']:.4f}, 95% CI=[{val['ci_low']:.4f}, {val['ci_high']:.4f}]")

# Also bootstrap CIs for E2 per optimizer per density
e2_bootstrap_results = {}
for opt in e2['optimizer'].unique():
    opt_data = e2[e2['optimizer'] == opt]
    for metric in ['reduction', 'fidelity', 'success', 'runtime']:
        values = opt_data[metric].values
        boots = np.random.choice(values, size=(n_bootstrap, len(values)), replace=True)
        boot_means = boots.mean(axis=1)
        ci_low = np.percentile(boot_means, 2.5)
        ci_high = np.percentile(boot_means, 97.5)
        e2_bootstrap_results[f"{opt}_{metric}"] = {
            'mean': float(np.mean(values)),
            'ci_low': float(ci_low),
            'ci_high': float(ci_high)
        }

# ============================================================
# 8. Figure 4: Algorithm Comparison
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(10, 8))

colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

# Panel (a): Mean reduction comparison
ax = axes[0, 0]
x_pos = np.arange(len(optimizers))
means = [optimizer_stats[optimizer_stats['optimizer'] == opt]['mean_reduction'].values[0] for opt in optimizers]
stds = [optimizer_stats[optimizer_stats['optimizer'] == opt]['std_reduction'].values[0] for opt in optimizers]
# Use bootstrap CIs for error bars
ci_lows = [bootstrap_results[f"{opt}_reduction"]["ci_low"] for opt in optimizers]
ci_highs = [bootstrap_results[f"{opt}_reduction"]["ci_high"] for opt in optimizers]
ci_err = [[m - lo for m, lo in zip(means, ci_lows)], [hi - m for m, hi in zip(means, ci_highs)]]
bars = ax.bar(x_pos, means, color=colors, alpha=0.7, yerr=ci_err, capsize=5)
ax.set_xticks(x_pos)
ax.set_xticklabels([opt.replace('_', '\n') for opt in optimizers], fontsize=8)
ax.set_ylabel('Mean Gate Reduction')
ax.set_title('(a) Gate Reduction')
ax.set_ylim(0, max(means) * 1.4)

# Panel (b): Mean fidelity comparison
ax = axes[0, 1]
means_fid = [optimizer_stats[optimizer_stats['optimizer'] == opt]['mean_fidelity'].values[0] for opt in optimizers]
ci_lows_fid = [bootstrap_results[f"{opt}_fidelity"]["ci_low"] for opt in optimizers]
ci_highs_fid = [bootstrap_results[f"{opt}_fidelity"]["ci_high"] for opt in optimizers]
ci_err_fid = [[m - lo for m, lo in zip(means_fid, ci_lows_fid)], [hi - m for m, hi in zip(means_fid, ci_highs_fid)]]
ax.bar(x_pos, means_fid, color=colors, alpha=0.7, yerr=ci_err_fid, capsize=5)
ax.set_xticks(x_pos)
ax.set_xticklabels([opt.replace('_', '\n') for opt in optimizers], fontsize=8)
ax.set_ylabel('Mean Fidelity')
ax.set_title('(b) Fidelity')
# Set y-limits to show differences
fid_min = min(ci_lows_fid) - 0.002
fid_max = max(ci_highs_fid) + 0.002
ax.set_ylim(fid_min, fid_max)

# Panel (c): Success rate comparison
ax = axes[1, 0]
means_succ = [optimizer_stats[optimizer_stats['optimizer'] == opt]['success_rate'].values[0] for opt in optimizers]
ci_lows_succ = [bootstrap_results[f"{opt}_success"]["ci_low"] for opt in optimizers]
ci_highs_succ = [bootstrap_results[f"{opt}_success"]["ci_high"] for opt in optimizers]
ci_err_succ = [[m - lo for m, lo in zip(means_succ, ci_lows_succ)], [hi - m for m, hi in zip(means_succ, ci_highs_succ)]]
ax.bar(x_pos, means_succ, color=colors, alpha=0.7, yerr=ci_err_succ, capsize=5)
ax.set_xticks(x_pos)
ax.set_xticklabels([opt.replace('_', '\n') for opt in optimizers], fontsize=8)
ax.set_ylabel('Success Rate')
ax.set_title('(c) Success Rate')
ax.set_ylim(0, max(means_succ) * 1.4 if max(means_succ) > 0 else 0.5)

# Panel (d): Runtime comparison
ax = axes[1, 1]
means_rt = [optimizer_stats[optimizer_stats['optimizer'] == opt]['mean_runtime'].values[0] for opt in optimizers]
ci_lows_rt = [bootstrap_results[f"{opt}_runtime"]["ci_low"] for opt in optimizers]
ci_highs_rt = [bootstrap_results[f"{opt}_runtime"]["ci_high"] for opt in optimizers]
ci_err_rt = [[m - lo for m, lo in zip(means_rt, ci_lows_rt)], [hi - m for m, hi in zip(means_rt, ci_highs_rt)]]
ax.bar(x_pos, means_rt, color=colors, alpha=0.7, yerr=ci_err_rt, capsize=5)
ax.set_xticks(x_pos)
ax.set_xticklabels([opt.replace('_', '\n') for opt in optimizers], fontsize=8)
ax.set_ylabel('Mean Runtime (s)')
ax.set_title('(d) Runtime')
ax.set_ylim(0, max(means_rt) * 1.4)

fig.suptitle('Experiment 4: Algorithm Comparison (n=5, d=15)', fontsize=13, y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'fig4_algorithm_comparison.png'), bbox_inches='tight')
print(f"Saved fig4_algorithm_comparison.png")
plt.close(fig)

# ============================================================
# Save processed data
# ============================================================
# E2 processed data
e2_grouped.to_csv(os.path.join(PROC_DIR, 'e2_density_sweep_summary.csv'), index=False)
e2_density_stats.to_csv(os.path.join(PROC_DIR, 'e2_density_overall_stats.csv'), index=False)

# E4 processed data
optimizer_stats.to_csv(os.path.join(PROC_DIR, 'e4_optimizer_comparison_summary.csv'), index=False)

# Save all analysis results as JSON
analysis_results = {
    'e2_overall': {
        'success_rate': float(e2['success'].mean()),
        'mean_reduction': float(e2['reduction'].mean()),
        'mean_fidelity': float(e2['fidelity'].mean()),
    },
    'e4_overall': {
        'success_rate': float(e4['success'].mean()),
        'mean_reduction': float(e4['reduction'].mean()),
        'mean_fidelity': float(e4['fidelity'].mean()),
    },
    'correlations_e2': corr_results,
    'wilcoxon_tests_e4': wilcoxon_results,
    'bootstrap_cis_e4': bootstrap_results,
    'bootstrap_cis_e2': e2_bootstrap_results,
    'optimizer_stats_e4': optimizer_stats.to_dict(orient='records'),
}

with open(os.path.join(PROC_DIR, 'e2_e4_analysis_results.json'), 'w') as f:
    json.dump(analysis_results, f, indent=2, default=str)

print(f"\nSaved processed data to {PROC_DIR}")
print(f"  - e2_density_sweep_summary.csv")
print(f"  - e2_density_overall_stats.csv")
print(f"  - e4_optimizer_comparison_summary.csv")
print(f"  - e2_e4_analysis_results.json")

print("\n=== ANALYSIS COMPLETE ===")