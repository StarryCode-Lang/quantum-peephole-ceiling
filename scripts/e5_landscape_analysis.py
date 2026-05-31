#!/usr/bin/env python3
"""
E5 Landscape Analysis — Comprehensive characterization of quantum circuit optimization landscape.
Generates: figures/final/fig5_landscape.png and data/processed/e5_landscape_analysis_results.json
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
import os
import json
import warnings
warnings.filterwarnings('ignore')

BASE = 'D:/Desktop/Q-research'
DATA = f'{BASE}/data/raw'
FIGS_FINAL = f'{BASE}/figures/final'
PROCESSED = f'{BASE}/data/processed'
os.makedirs(FIGS_FINAL, exist_ok=True)
os.makedirs(PROCESSED, exist_ok=True)

plt.style.use('seaborn-v0_8-paper')

N_BOOT = 2000
CI_LEVEL = 0.95

def bootstrap_ci(data_values, stat_func=np.mean, n_boot=N_BOOT, ci=CI_LEVEL):
    """Bootstrap CI for 1D data."""
    arr = np.asarray(data_values, dtype=float)
    n = len(arr)
    if n == 0:
        return np.nan, (np.nan, np.nan)
    idx = np.random.randint(0, n, size=(n_boot, n))
    boot_samples = arr[idx]
    if stat_func == np.mean:
        boot_stats = np.mean(boot_samples, axis=1)
    elif stat_func == np.std:
        boot_stats = np.std(boot_samples, axis=1)
    elif stat_func == np.median:
        boot_stats = np.median(boot_samples, axis=1)
    else:
        boot_stats = np.array([stat_func(s) for s in boot_samples])
    lower = np.percentile(boot_stats, (1 - ci) / 2 * 100)
    upper = np.percentile(boot_stats, (1 + ci) / 2 * 100)
    return stat_func(arr), (lower, upper)

def page_entropy(n_qubits):
    return n_qubits / 2 * np.log(2) - 0.5

# ============================================================
# 1. Load data
# ============================================================
print("Loading E5 data...")
e5 = pd.read_csv(f'{DATA}/exp5_landscape_20260530_102615.csv')
print(f"E5 shape: {e5.shape}")
print(f"Columns: {list(e5.columns)}")
depths = sorted(e5['depth'].unique())
print(f"Depths: {depths}")

# ============================================================
# 2. Landscape Roughness Analysis
# ============================================================
print("\n=== Landscape Roughness ===")
roughness_by_depth = e5.groupby('depth')['entropy_diff'].agg(['std', 'mean', 'median', 'count']).reset_index()
roughness_by_depth.columns = ['depth', 'std_entropy_diff', 'mean_entropy_diff', 'median_entropy_diff', 'count']
print(roughness_by_depth.to_string(index=False))

# Bootstrap CIs for roughness
roughness_ci_rows = []
for d in depths:
    sub = e5[e5['depth'] == d]['entropy_diff'].values
    mean_val, mean_ci = bootstrap_ci(sub, np.mean)
    std_val, std_ci = bootstrap_ci(sub, np.std)
    med_val, med_ci = bootstrap_ci(sub, np.median)
    roughness_ci_rows.append({
        'depth': d,
        'mean_entropy_diff': mean_val, 'mean_ci_low': mean_ci[0], 'mean_ci_high': mean_ci[1],
        'std_entropy_diff': std_val, 'std_ci_low': std_ci[0], 'std_ci_high': std_ci[1],
        'median_entropy_diff': med_val, 'median_ci_low': med_ci[0], 'median_ci_high': med_ci[1],
        'n': len(sub)
    })
roughness_ci_df = pd.DataFrame(roughness_ci_rows)

# ============================================================
# 3. Correlation Analysis (base_entropy vs entropy_diff)
# ============================================================
print("\n=== Correlation Analysis ===")
corr_val, corr_p = stats.pearsonr(e5['base_entropy'], e5['entropy_diff'])
spearman_r, spearman_p = stats.spearmanr(e5['base_entropy'], e5['entropy_diff'])
print(f"Overall Pearson r={corr_val:.6f}, p={corr_p:.6e}")
print(f"Overall Spearman r={spearman_r:.6f}, p={spearman_p:.6e}")

depth_corr_rows = []
for d in depths:
    sub = e5[e5['depth'] == d]
    r, p = stats.pearsonr(sub['base_entropy'], sub['entropy_diff'])
    sr, sp = stats.spearmanr(sub['base_entropy'], sub['entropy_diff'])
    depth_corr_rows.append({
        'depth': d, 'pearson_r': r, 'pearson_p': p,
        'spearman_r': sr, 'spearman_p': sp, 'n': len(sub)
    })
depth_corr_df = pd.DataFrame(depth_corr_rows)
print(depth_corr_df.to_string(index=False))

# ============================================================
# 4. Reduction Distribution by Depth
# ============================================================
print("\n=== Reduction (gate reduction) by Depth ===")
e5['gate_reduction'] = e5['base_gates'] - e5['perturbed_gates']
e5['reduction_pct'] = e5['gate_reduction'] / e5['base_gates'] * 100

reduction_by_depth = e5.groupby('depth').agg(
    mean_reduction=('gate_reduction', 'mean'),
    std_reduction=('gate_reduction', 'std'),
    mean_reduction_pct=('reduction_pct', 'mean'),
    std_reduction_pct=('reduction_pct', 'std'),
    count=('gate_reduction', 'count')
).reset_index()
print(reduction_by_depth.to_string(index=False))

# ============================================================
# 5. Landscape Structure — Multi-modality Analysis
# ============================================================
print("\n=== Landscape Structure: Multi-modality ===")
# Check for multiple peaks in entropy_diff distribution per depth
modality_results = []
for d in depths:
    sub = e5[e5['depth'] == d]['entropy_diff'].values
    # Use histogram-based peak detection
    hist, bin_edges = np.histogram(sub, bins=50)
    # Find peaks (local maxima)
    peaks = []
    for i in range(1, len(hist) - 1):
        if hist[i] > hist[i-1] and hist[i] > hist[i+1] and hist[i] > 5:
            peaks.append({
                'bin_center': (bin_edges[i] + bin_edges[i+1]) / 2,
                'count': hist[i]
            })
    modality_results.append({
        'depth': d,
        'n_peaks': len(peaks),
        'peak_positions': [p['bin_center'] for p in peaks],
        'peak_counts': [p['count'] for p in peaks],
        'is_multimodal': len(peaks) > 1
    })
    peak_strs = [f"{p['bin_center']:.4f}" for p in peaks]
    print(f"  depth={d}: {len(peaks)} peaks at {peak_strs}")

# ============================================================
# 6. Entropy vs Reduction Relationship
# ============================================================
print("\n=== Entropy vs Reduction ===")
ent_red_corr, ent_red_p = stats.pearsonr(e5['base_entropy'], e5['gate_reduction'])
print(f"Pearson r(base_entropy, gate_reduction) = {ent_red_corr:.6f}, p = {ent_red_p:.6e}")
ent_red_spearman, ent_red_sp = stats.spearmanr(e5['base_entropy'], e5['gate_reduction'])
print(f"Spearman r(base_entropy, gate_reduction) = {ent_red_spearman:.6f}, p = {ent_red_sp:.6e}")

# Also check normalized_entropy vs reduction (if available)
norm_red_corr = None
norm_red_p = None
if 'normalized_entropy' in e5.columns:
    norm_red_corr, norm_red_p = stats.pearsonr(e5['normalized_entropy'], e5['gate_reduction'])
    print(f"Pearson r(normalized_entropy, gate_reduction) = {norm_red_corr:.6f}, p = {norm_red_p:.6e}")

# ============================================================
# 7. Page Entropy Comparison
# ============================================================
print("\n=== Page Entropy Reference ===")
n5 = 5
n5_page = page_entropy(n5)
print(f"Page entropy for n={n5}: S_Page = {n5_page:.6f}")

e5_mean_base = e5.groupby('depth')['base_entropy'].agg(['mean', 'std']).reset_index()
e5_mean_base.columns = ['depth', 'mean_base_entropy', 'std_base_entropy']
e5_mean_base['page_entropy'] = n5_page
e5_mean_base['deviation'] = e5_mean_base['mean_base_entropy'] - n5_page
e5_mean_base['relative_deviation'] = e5_mean_base['deviation'] / n5_page
print(e5_mean_base.to_string(index=False))

# ============================================================
# 8. Generate Figure — fig5_landscape.png
# ============================================================
print("\nGenerating fig5_landscape.png...")

fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle('Experiment 5: Quantum Circuit Landscape Characterization', fontsize=14, fontweight='bold')

# Panel A: Landscape Roughness (std of entropy_diff) by Depth
ax = axes[0, 0]
bars = ax.bar(roughness_ci_df['depth'], roughness_ci_df['std_entropy_diff'],
              color='steelblue', edgecolor='navy', alpha=0.8, width=2.5)
# Add CI error bars
ax.errorbar(roughness_ci_df['depth'], roughness_ci_df['std_entropy_diff'],
            yerr=[roughness_ci_df['std_entropy_diff'] - roughness_ci_df['std_ci_low'],
                  roughness_ci_df['std_ci_high'] - roughness_ci_df['std_entropy_diff']],
            fmt='none', ecolor='darkred', capsize=4, linewidth=1.5)
ax.set_xlabel('Circuit Depth')
ax.set_ylabel('Roughness: std(ΔEntropy)')
ax.set_title('(a) Landscape Roughness by Depth')
ax.grid(True, alpha=0.3)

# Panel B: Mean Perturbation Impact by Depth
ax = axes[0, 1]
bars = ax.bar(roughness_ci_df['depth'], roughness_ci_df['mean_entropy_diff'],
              color='coral', edgecolor='darkred', alpha=0.8, width=2.5)
ax.errorbar(roughness_ci_df['depth'], roughness_ci_df['mean_entropy_diff'],
            yerr=[roughness_ci_df['mean_entropy_diff'] - roughness_ci_df['mean_ci_low'],
                  roughness_ci_df['mean_ci_high'] - roughness_ci_df['mean_entropy_diff']],
            fmt='none', ecolor='navy', capsize=4, linewidth=1.5)
ax.set_xlabel('Circuit Depth')
ax.set_ylabel('Mean ΔEntropy (Perturbation Impact)')
ax.set_title('(b) Mean Perturbation Impact')
ax.grid(True, alpha=0.3)

# Panel C: Gate Reduction Distribution by Depth (boxplot)
ax = axes[0, 2]
reduction_data_by_depth = [e5[e5['depth'] == d]['gate_reduction'].values for d in depths]
bp = ax.boxplot(reduction_data_by_depth, labels=depths, patch_artist=True,
                boxprops=dict(facecolor='lightgreen', alpha=0.7),
                medianprops=dict(color='darkgreen', linewidth=2))
ax.set_xlabel('Circuit Depth')
ax.set_ylabel('Gate Reduction (base - perturbed)')
ax.set_title('(c) Gate Reduction Distribution')
ax.grid(True, alpha=0.3)

# Panel D: Base Entropy vs Entropy Diff Scatter
ax = axes[1, 0]
idx_sample = np.random.choice(len(e5), min(2000, len(e5)), replace=False)
scatter_colors = e5['depth'].iloc[idx_sample].values
scatter = ax.scatter(e5['base_entropy'].iloc[idx_sample], e5['entropy_diff'].iloc[idx_sample],
                     alpha=0.3, s=10, c=scatter_colors, cmap='viridis', edgecolors='none')
ax.set_xlabel('Base Entropy')
ax.set_ylabel('ΔEntropy (Perturbation Impact)')
ax.set_title(f'(d) Base Entropy vs Perturbation Impact\nPearson r={corr_val:.4f}')
ax.grid(True, alpha=0.3)
cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Depth')

# Panel E: Correlation Strength by Depth
ax = axes[1, 1]
ax.plot(depth_corr_df['depth'], depth_corr_df['pearson_r'], 'o-', color='purple',
        linewidth=2, markersize=8, label='Pearson')
ax.plot(depth_corr_df['depth'], depth_corr_df['spearman_r'], 's--', color='teal',
        linewidth=2, markersize=8, label='Spearman')
ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
ax.set_xlabel('Circuit Depth')
ax.set_ylabel('Correlation Coefficient')
ax.set_title('(e) Correlation: Base Entropy vs ΔEntropy')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

# Panel F: Entropy vs Gate Reduction Scatter
ax = axes[1, 2]
ax.scatter(e5['base_entropy'].iloc[idx_sample], e5['gate_reduction'].iloc[idx_sample],
           alpha=0.3, s=10, c=scatter_colors, cmap='plasma', edgecolors='none')
ax.set_xlabel('Base Entropy')
ax.set_ylabel('Gate Reduction')
ax.set_title(f'(f) Entropy vs Gate Reduction\nPearson r={ent_red_corr:.4f}')
ax.grid(True, alpha=0.3)
cbar2 = plt.colorbar(scatter, ax=ax)
cbar2.set_label('Depth')

plt.tight_layout()
plt.savefig(f'{FIGS_FINAL}/fig5_landscape.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"Saved fig5_landscape.png to {FIGS_FINAL}")
plt.close()

# Also save to figures/ root for compatibility
import shutil
shutil.copy2(f'{FIGS_FINAL}/fig5_landscape.png', f'{BASE}/figures/fig5_landscape.png')
print(f"Copied to {BASE}/figures/fig5_landscape.png")

# ============================================================
# 9. Save E5 Analysis Results JSON
# ============================================================
print("\nSaving E5 analysis results JSON...")

results = {
    "experiment": "E5_landscape",
    "description": "Quantum circuit landscape characterization (n=5, depth=3-20)",
    "data_file": "data/raw/exp5_landscape_20260530_102615.csv",
    "n_rows": int(e5.shape[0]),
    "n_qubits": 5,
    "depths": depths,
    "trials_per_depth": 1000,
    "columns": list(e5.columns),

    "landscape_roughness": {
        "description": "Roughness measured as std(entropy_diff) per depth",
        "overall_correlation": {
            "pearson_r": float(corr_val),
            "pearson_p": float(corr_p),
            "spearman_r": float(spearman_r),
            "spearman_p": float(spearman_p)
        },
        "per_depth": roughness_ci_df.to_dict(orient='records')
    },

    "correlation_analysis": {
        "base_entropy_vs_entropy_diff": {
            "overall": {
                "pearson_r": float(corr_val),
                "pearson_p": float(corr_p),
                "spearman_r": float(spearman_r),
                "spearman_p": float(spearman_p)
            },
            "per_depth": depth_corr_df.to_dict(orient='records')
        },
        "base_entropy_vs_gate_reduction": {
            "pearson_r": float(ent_red_corr),
            "pearson_p": float(ent_red_p),
            "spearman_r": float(ent_red_spearman),
            "spearman_p": float(ent_red_sp)
        }
    },

    "reduction_distribution": reduction_by_depth.to_dict(orient='records'),

    "landscape_structure": {
        "description": "Multi-modality analysis via histogram peak detection",
        "per_depth": modality_results
    },

    "page_entropy_comparison": {
        "formula": "S_Page(n) = n/2 * ln(2) - 0.5",
        "n5_page_entropy": float(n5_page),
        "measured_vs_page": e5_mean_base.to_dict(orient='records')
    },

    "figure": "figures/final/fig5_landscape.png",
    "analysis_date": "2026-05-30"
}

json_path = f'{PROCESSED}/e5_landscape_analysis_results.json'
with open(json_path, 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"Saved e5_landscape_analysis_results.json to {json_path}")

# ============================================================
# 10. Summary
# ============================================================
print("\n=== E5 Analysis Summary ===")
print(f"Data: {e5.shape[0]} rows, depths={depths}, 1000 trials/depth")
print(f"Landscape roughness range: {roughness_ci_df['std_entropy_diff'].min():.6f} - {roughness_ci_df['std_entropy_diff'].max():.6f}")
print(f"Overall Pearson r(base_entropy, entropy_diff): {corr_val:.4f}")
print(f"Overall Pearson r(base_entropy, gate_reduction): {ent_red_corr:.4f}")
print(f"Page entropy n=5: {n5_page:.6f}")
multimodal_count = sum(1 for m in modality_results if m['is_multimodal'])
print(f"Multimodal depths: {multimodal_count}/{len(depths)}")
print(f"Figure saved: {FIGS_FINAL}/fig5_landscape.png")
print(f"Results saved: {json_path}")
print("\nDone!")