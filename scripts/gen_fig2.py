"""
Generate fig2_fss.png - Publication-quality
3-panel figure:
(a) Gate reduction vs n_qubits with power-law fit
(b) Per-n success rate curves vs depth
(c) Mean success rate vs n_qubits (bar chart with CI)
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
e3 = pd.read_csv("data/raw/exp3_scaling_20260530_100830.csv")
e3['success'] = e3['success'].astype(int)

e3_nd_agg = e3.groupby(['n_qubits', 'depth']).agg(
    success_rate=('success', 'mean'),
    mean_reduction=('reduction', 'mean'),
    mean_entropy=('normalized_entropy', 'mean'),
    n_trials=('success', 'count')
).reset_index()

e3_n_agg = e3.groupby('n_qubits').agg(
    mean_reduction=('reduction', 'mean'),
    std_reduction=('reduction', 'std'),
    mean_success=('success', 'mean'),
    mean_fidelity=('fidelity', 'mean'),
    n_trials=('success', 'count')
).reset_index()

with open("data/processed/e1_e3_analysis_results.json", 'r') as f:
    results = json.load(f)

# ─── Functions ───
def power_law(x, a, b, c):
    return a * x**b + c

def exp_decay(x, P0, d0, P_bg):
    return P0 * np.exp(-x / d0) + P_bg

# ─── Create figure ───
fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))

# Colors for different n
n_colors = {
    3: '#e41a1c', 4: '#377eb8', 5: '#4daf4a', 6: '#984ea3',
    7: '#ff7f00', 8: '#a65628', 9: '#f781bf', 10: '#999999'
}

# Panel (a): Reduction vs n_qubits with power-law fit
ax = axes[0]
n_vals = e3_n_agg['n_qubits'].values
r_vals = e3_n_agg['mean_reduction'].values

ax.errorbar(n_vals, r_vals, yerr=e3_n_agg['std_reduction'],
            fmt='o', color='#2166ac', markersize=6, capsize=3, linewidth=1.5,
            label='Data', zorder=3)

# Power law fit
scaling = results['e3_reduction_scaling']
n_fit = np.linspace(3, 10, 100)
y_fit = power_law(n_fit, scaling['a'], scaling['b'], scaling['c'])
ax.plot(n_fit, y_fit, '-', color='#b2182b', linewidth=2,
        label=f'$\\Delta = {scaling["a"]:.3f} \\, n^{{{scaling["b"]:.2f}}} + {scaling["c"]:.3f}$', zorder=4)

ax.set_xlabel('Number of Qubits $n$')
ax.set_ylabel('Mean Gate Reduction $\\Delta_{\\mathrm{gate}}$')
ax.set_title('(a) Reduction Scaling')
ax.legend(loc='lower right', framealpha=0.9)
ax.set_xlim(2.5, 10.5)
ax.grid(True, alpha=0.3)

# R² annotation
ax.text(0.05, 0.05, f'$R^2 = {scaling["r2"]:.3f}$', transform=ax.transAxes,
        fontsize=10, verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Panel (b): Per-n success rate curves vs depth
ax = axes[1]
for n in sorted(e3_nd_agg['n_qubits'].unique()):
    sub = e3_nd_agg[e3_nd_agg['n_qubits'] == n]
    color = n_colors.get(int(n), '#333333')
    ax.plot(sub['depth'], sub['success_rate'], '-', color=color, linewidth=1.5,
            alpha=0.8, label=f'$n={int(n)}$')
    
    # Overlay exponential fit
    if int(n) in results['e3_per_n_exp_decay']:
        fit = results['e3_per_n_exp_decay'][int(n)]
        x_fine = np.linspace(1, 30, 100)
        y_fine = exp_decay(x_fine, fit['P0'], fit['d0'], fit['P_bg'])
        ax.plot(x_fine, y_fine, '--', color=color, linewidth=0.8, alpha=0.4)

ax.set_xlabel('Circuit Depth $d$')
ax.set_ylabel('Success Rate $P_{\\mathrm{success}}$')
ax.set_title('(b) Success Rate vs Depth (per $n$)')
ax.legend(loc='upper right', framealpha=0.9, ncol=2)
ax.set_xlim(0, 31)
ax.set_ylim(-0.02, 0.65)
ax.grid(True, alpha=0.3)

# Panel (c): Mean success rate vs n_qubits (bar chart with Bootstrap CI)
ax = axes[2]
ns = sorted(e3['n_qubits'].unique())
bootstrap = results['e3_bootstrap']

bars_x = ns
bars_y = [bootstrap[str(int(n))]['success_rate']['mean'] for n in ns]
ci_low = [bootstrap[str(int(n))]['success_rate']['ci_low'] for n in ns]
ci_high = [bootstrap[str(int(n))]['success_rate']['ci_high'] for n in ns]
errors = [[y - lo for y, lo in zip(bars_y, ci_low)],
          [hi - y for y, hi in zip(bars_y, ci_high)]]

colors_bar = [n_colors.get(int(n), '#333333') for n in ns]
ax.bar(bars_x, bars_y, width=0.7, color=colors_bar, alpha=0.8, edgecolor='black', linewidth=0.5)
ax.errorbar(bars_x, bars_y, yerr=errors, fmt='none', ecolor='black', capsize=4, linewidth=1.2)

ax.set_xlabel('Number of Qubits $n$')
ax.set_ylabel('Mean Success Rate')
ax.set_title('(c) Bootstrap CI: Success Rate')
ax.set_xlim(2.5, 10.5)
ax.set_ylim(0, 0.25)
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('figures/final/fig2_fss.png')
print("✅ fig2_fss.png saved!")

plt.savefig('figures/final/fig2_fss.pdf')
print("✅ fig2_fss.pdf saved!")
plt.close()