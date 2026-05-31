"""
Generate fig1_phase_transition.png - Publication-quality
3-panel figure:
(a) Success rate vs depth with exponential decay fit
(b) Gate reduction vs depth  
(c) Normalized entropy vs depth with threshold annotations
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import json
import os

os.chdir("D:/Desktop/Q-research")

# ─── Style ───
plt.style.use('seaborn-v0_8-paper')
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.labelsize': 13,
    'axes.titlesize': 13,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'mathtext.fontset': 'cm',
})

# ─── Load data ───
e1 = pd.read_csv("data/raw/exp1_phase_transition_20260530_095003.csv")
e1['success'] = e1['success'].astype(int)
e1_agg = e1.groupby('depth').agg(
    success_rate=('success', 'mean'),
    mean_reduction=('reduction', 'mean'),
    std_reduction=('reduction', 'std'),
    mean_entropy=('normalized_entropy', 'mean'),
    std_entropy=('normalized_entropy', 'std'),
    n_trials=('success', 'count')
).reset_index()

# Load analysis results
with open("data/processed/e1_e3_analysis_results.json", 'r') as f:
    results = json.load(f)

# ─── Exponential decay function ───
def exp_decay(x, P0, d0, P_bg):
    return P0 * np.exp(-x / d0) + P_bg

e1_fit = results['e1_exp_decay']
x_fit = np.linspace(1, 50, 200)
y_fit = exp_decay(x_fit, e1_fit['P0'], e1_fit['d0'], e1_fit['P_bg'])

# ─── Create figure ───
fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))

# Panel (a): Success rate vs depth
ax = axes[0]
ax.scatter(e1_agg['depth'], e1_agg['success_rate'], s=20, c='#2166ac', alpha=0.7, 
           edgecolors='#2166ac', linewidths=0.5, zorder=3, label='Data (n=5)')
ax.plot(x_fit, y_fit, '-', c='#b2182b', linewidth=2, zorder=4,
        label='Fit: $P_0 e^{-d/d_0}$\n' + f'$P_0={e1_fit["P0"]:.3f}, d_0={e1_fit["d0"]:.1f}$')

# Bootstrap CI for overall success rate
bs = results['e1_bootstrap']['success_rate']
ax.axhline(y=bs['mean'], color='#4daf4a', linestyle='--', linewidth=1.2, alpha=0.6,
           label=f'Mean: {bs["mean"]:.3f}')
ax.axhspan(bs['ci_low'], bs['ci_high'], alpha=0.15, color='#4daf4a')

ax.set_xlabel('Circuit Depth $d$')
ax.set_ylabel('Success Rate $P_{\\mathrm{success}}$')
ax.set_title('(a) Phase Transition: Success Rate')
ax.legend(loc='upper right', framealpha=0.9)
ax.set_xlim(0, 51)
ax.set_ylim(-0.02, 0.40)
ax.grid(True, alpha=0.3)

# Add R² annotation
ax.text(0.05, 0.05, f'$R^2 = {e1_fit["r2"]:.3f}$', transform=ax.transAxes,
        fontsize=10, verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Panel (b): Gate reduction vs depth
ax = axes[1]
ax.scatter(e1_agg['depth'], e1_agg['mean_reduction'], s=20, c='#2166ac', alpha=0.7,
           edgecolors='#2166ac', linewidths=0.5, zorder=3)

# Error bars
ax.errorbar(e1_agg['depth'], e1_agg['mean_reduction'], yerr=e1_agg['std_reduction'],
            fmt='none', ecolor='#2166ac', elinewidth=0.8, capsize=2, alpha=0.5, zorder=2)

# Mean line with CI
bs_red = results['e1_bootstrap']['mean_reduction']
ax.axhline(y=bs_red['mean'], color='#4daf4a', linestyle='--', linewidth=1.2, alpha=0.6,
           label=f'Mean: {bs_red["mean"]:.4f}')
ax.axhspan(bs_red['ci_low'], bs_red['ci_high'], alpha=0.15, color='#4daf4a')

ax.set_xlabel('Circuit Depth $d$')
ax.set_ylabel('Gate Reduction $\\Delta_{\\mathrm{gate}}$')
ax.set_title('(b) Gate Reduction vs Depth')
ax.legend(loc='upper right', framealpha=0.9)
ax.set_xlim(0, 51)
ax.set_ylim(0.10, 0.18)
ax.grid(True, alpha=0.3)

# Panel (c): Normalized entropy vs depth
ax = axes[2]
ax.scatter(e1_agg['depth'], e1_agg['mean_entropy'], s=20, c='#2166ac', alpha=0.7,
           edgecolors='#2166ac', linewidths=0.5, zorder=3)
ax.errorbar(e1_agg['depth'], e1_agg['mean_entropy'], yerr=e1_agg['std_entropy'],
            fmt='none', ecolor='#2166ac', elinewidth=0.8, capsize=2, alpha=0.5, zorder=2)

# Entropy thresholds
thresh_info = results['e1_entropy_thresholds']
colors_thresh = ['#ff7f00', '#e41a1c', '#984ea3', '#377eb8']
for i, (thresh_val, info) in enumerate(thresh_info.items()):
    ax.axhline(y=float(thresh_val), color=colors_thresh[i], linestyle=':', linewidth=1.0, alpha=0.7)
    ax.annotate(f'$S/{format(float(thresh_val),".1f")}$', xy=(info['depth'], float(thresh_val)),
                fontsize=8, color=colors_thresh[i],
                xytext=(info['depth']+3, float(thresh_val)+0.03),
                arrowprops=dict(arrowstyle='->', color=colors_thresh[i], lw=0.8))

ax.set_xlabel('Circuit Depth $d$')
ax.set_ylabel('Normalized Entropy $S/S_{\\max}$')
ax.set_title('(c) Entanglement Entropy Growth')
ax.set_xlim(0, 51)
ax.set_ylim(-0.1, 1.1)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('figures/final/fig1_phase_transition.png')
print("✅ fig1_phase_transition.png saved!")

# Also save as PDF for publication
plt.savefig('figures/final/fig1_phase_transition.pdf')
print("✅ fig1_phase_transition.pdf saved!")
plt.close()