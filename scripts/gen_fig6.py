"""
Generate fig6_baseline_comparison.png - Publication-quality
3-panel figure for E6: Qiskit Transpiler Baseline Comparison

Panels:
(a) Gate reduction vs depth for Qiskit L0-L3 vs Greedy (line chart)
(b) Success rate vs depth
(c) Fidelity comparison (box plot or bar chart)

Author: Q-research Team
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import os
import glob
from scipy import stats

os.chdir("D:/Desktop/Q-research")

# ─── Style ───
plt.style.use('seaborn-v0_8-paper')
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Computer Modern Roman', 'Times New Roman', 'DejaVu Serif'],
    'font.size': 9,
    'axes.labelsize': 10,
    'axes.titlesize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'figure.titlesize': 11,
    'lines.linewidth': 1.5,
    'lines.markersize': 5,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.top': True,
    'ytick.right': True,
    'axes.spines.top': True,
    'axes.spines.right': True,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
    'mathtext.fontset': 'cm',
})

# Colorblind-safe palette (Wong 2011)
COLORS = {
    'Qiskit_L0': '#0072B2',   # blue
    'Qiskit_L1': '#56B4E9',   # sky blue
    'Qiskit_L2': '#009E73',   # green
    'Qiskit_L3': '#E69F00',   # orange
    'Greedy_Ours': '#D55E00', # red
}
MARKERS = {
    'Qiskit_L0': 'o',
    'Qiskit_L1': 's',
    'Qiskit_L2': '^',
    'Qiskit_L3': 'D',
    'Greedy_Ours': 'X',
}
LABELS = {
    'Qiskit_L0': 'Qiskit L0 (no opt)',
    'Qiskit_L1': 'Qiskit L1 (light)',
    'Qiskit_L2': 'Qiskit L2 (medium)',
    'Qiskit_L3': 'Qiskit L3 (heavy)',
    'Greedy_Ours': 'Greedy (ours)',
}

# ─── Load data ───
csv_files = glob.glob("data/raw/exp6_baseline_comparison_*.csv")
csv_path = sorted(csv_files)[-1]  # most recent
df = pd.read_csv(csv_path)
df['success'] = df['success'].astype(int)

# ─── Per-depth aggregation ───
optimizers = ['Qiskit_L0', 'Qiskit_L1', 'Qiskit_L2', 'Qiskit_L3', 'Greedy_Ours']
depths = sorted(df['depth'].unique())

# ─── Create figure ───
fig, axes = plt.subplots(1, 3, figsize=(14, 4.0))

# ── Panel (a): Gate reduction vs depth ──
ax = axes[0]
for opt in optimizers:
    sub = df[df['optimizer'] == opt]
    agg = sub.groupby('depth')['reduction'].agg(['mean', 'std', 'count']).reset_index()
    ci = 1.96 * agg['std'] / np.sqrt(agg['count'])
    ax.plot(agg['depth'], agg['mean'], color=COLORS[opt], marker=MARKERS[opt],
            linewidth=1.5, markersize=5, label=LABELS[opt], zorder=3)
    ax.fill_between(agg['depth'], agg['mean'] - ci, agg['mean'] + ci,
                    color=COLORS[opt], alpha=0.1, zorder=2)

ax.set_xlabel('Circuit Depth $d$')
ax.set_ylabel('Gate Reduction $\\Delta_{\\mathrm{gate}}$')
ax.set_title('(a) Gate Count Reduction')
ax.legend(loc='lower right', framealpha=0.9, fontsize=7.5)
ax.set_xlim(min(depths) - 1, max(depths) + 1)
ax.set_ylim(-0.05, 0.65)
ax.grid(True, alpha=0.3)

# ── Panel (b): Success rate vs depth ──
ax = axes[1]
for opt in optimizers:
    sub = df[df['optimizer'] == opt]
    agg = sub.groupby('depth')['success'].agg(['mean', 'count']).reset_index()
    # Wilson score CI for proportions
    ci_low, ci_high = [], []
    for _, row in agg.iterrows():
        p = row['mean']
        n = int(row['count'])
        z = 1.96
        denom = 1 + z**2 / n
        center = (p + z**2 / (2*n)) / denom
        margin = z * np.sqrt((p*(1-p) + z**2/(4*n)) / n) / denom
        ci_low.append(center - margin)
        ci_high.append(center + margin)

    ax.plot(agg['depth'], agg['mean'], color=COLORS[opt], marker=MARKERS[opt],
            linewidth=1.5, markersize=5, label=LABELS[opt], zorder=3)
    ax.fill_between(agg['depth'], ci_low, ci_high,
                    color=COLORS[opt], alpha=0.1, zorder=2)

ax.set_xlabel('Circuit Depth $d$')
ax.set_ylabel('Success Rate $P_{\\mathrm{success}}$')
ax.set_title('(b) Optimization Success Rate')
ax.legend(loc='lower right', framealpha=0.9, fontsize=7.5)
ax.set_xlim(min(depths) - 1, max(depths) + 1)
ax.set_ylim(-0.05, 1.05)
ax.grid(True, alpha=0.3)

# ── Panel (c): Mean fidelity with error bars ──
ax = axes[2]
x_positions = np.arange(len(depths))
width = 0.13
n_opts = len(optimizers)

for i, opt in enumerate(optimizers):
    sub = df[df['optimizer'] == opt]
    agg = sub.groupby('depth')['fidelity'].agg(['mean', 'std', 'count']).reset_index()
    ci = 1.96 * agg['std'] / np.sqrt(agg['count'])
    x = x_positions + (i - n_opts/2 + 0.5) * width
    ax.bar(x, agg['mean'], width=width, color=COLORS[opt], edgecolor='black',
           linewidth=0.5, alpha=0.85, label=LABELS[opt], zorder=3)
    ax.errorbar(x, agg['mean'], yerr=ci, fmt='none', ecolor='black',
                elinewidth=0.6, capsize=2, alpha=0.7, zorder=4)

ax.set_xticks(x_positions)
ax.set_xticklabels([str(d) for d in depths])
ax.set_xlabel('Circuit Depth $d$')
ax.set_ylabel('Mean Fidelity $\\bar{F}$')
ax.set_title('(c) Average Gate Fidelity')
ax.legend(loc='lower right', framealpha=0.9, fontsize=7.5)
ax.set_ylim(-0.05, 1.10)
ax.grid(True, alpha=0.3, axis='y')

plt.suptitle('E6: Qiskit Transpiler Baseline Comparison', fontsize=12, fontweight='bold', y=1.02)
plt.tight_layout()

# Save
os.makedirs('figures/final', exist_ok=True)
plt.savefig('figures/final/fig6_baseline_comparison.png', dpi=300, bbox_inches='tight', pad_inches=0.05)
print("✅ fig6_baseline_comparison.png saved!")

plt.savefig('figures/final/fig6_baseline_comparison.pdf', bbox_inches='tight', pad_inches=0.05)
print("✅ fig6_baseline_comparison.pdf saved!")

plt.close()

# ─── Print summary stats ───
print("\n" + "="*80)
print("E6 FIGURE DATA SUMMARY")
print("="*80)
for opt in optimizers:
    sub = df[df['optimizer'] == opt]
    print(f"\n{LABELS[opt]}:")
    print(f"  Mean reduction:  {sub['reduction'].mean():.4f} ± {sub['reduction'].std():.4f}")
    print(f"  Success rate:    {sub['success'].mean():.4f}")
    print(f"  Mean fidelity:   {sub['fidelity'].mean():.6f} ± {sub['fidelity'].std():.6f}")
    print(f"  Mean runtime:    {sub['runtime'].mean():.4f} s")
