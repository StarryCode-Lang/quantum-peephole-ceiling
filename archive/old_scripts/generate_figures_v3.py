"""
Publication-quality figures for quantum circuit entanglement paper - v2
======================================================================
Generates 10 figures from the experimental data.
"""

import gc
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.size'] = 11
matplotlib.rcParams['mathtext.fontset'] = 'cm'
import matplotlib.pyplot as plt
from scipy import stats as sp_stats

DATA_DIR = 'D:/Desktop/Q-research/data/raw'
OUT_DIR = 'D:/Desktop/Q-research/figures/final'
os.makedirs(OUT_DIR, exist_ok=True)

COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b',
          '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']


def load(name):
    """Load the most recent CSV matching the name pattern."""
    files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith(name) and f.endswith('.csv')],
                   reverse=True)
    if files:
        return pd.read_csv(os.path.join(DATA_DIR, files[0]))
    return None


def bootstrap_ci(data, n_bootstrap=1000, ci=0.95, seed=42):
    """Bootstrap CI for the mean."""
    rng = np.random.RandomState(seed)
    means = [np.mean(rng.choice(data, size=len(data), replace=True)) for _ in range(n_bootstrap)]
    alpha = (1 - ci) / 2
    return np.percentile(means, 100 * alpha), np.percentile(means, 100 * (1 - alpha))


# ============================================================
# Figure 1: Entropy vs Depth
# ============================================================

def fig1():
    """Entropy vs depth with proper Page values."""
    df = load('exp1_entropy_vs_depth')
    if df is None:
        print("  fig1: NO DATA"); return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    
    for i, n in enumerate(sorted(df.n_qubits.unique())):
        sub = df[df.n_qubits == n]
        grp = sub.groupby('depth')['entanglement_entropy']
        m, s = grp.mean(), grp.std()
        page = sub['page_value'].iloc[0]
        
        ax1.fill_between(m.index, m - s, m + s, alpha=0.12, color=COLORS[i])
        ax1.plot(m.index, m.values, 'o-', ms=3, label=f'$n={n}$', color=COLORS[i], lw=1.5)
        ax1.axhline(page, color=COLORS[i], ls=':', alpha=0.3, lw=0.8)
    
    ax1.set_xlabel('Circuit Depth $d$', fontsize=12)
    ax1.set_ylabel('Entanglement Entropy $S$ (bits)', fontsize=12)
    ax1.legend(fontsize=9, ncol=2)
    ax1.grid(True, alpha=0.3)
    ax1.set_title('(a) Entanglement Entropy vs Depth', fontsize=12)
    
    # Normalized
    for i, n in enumerate(sorted(df.n_qubits.unique())):
        sub = df[df.n_qubits == n]
        page = sub['page_value'].iloc[0]
        grp = sub.groupby('depth')['entanglement_entropy']
        m, s = grp.mean() / page, grp.std() / page
        ax2.fill_between(m.index, m - s, m + s, alpha=0.12, color=COLORS[i])
        ax2.plot(m.index, m.values, 'o-', ms=3, label=f'$n={n}$', color=COLORS[i], lw=1.5)
    
    ax2.axhline(0.9, color='red', ls='--', alpha=0.5, lw=1, label='90% threshold')
    ax2.set_xlabel('Circuit Depth $d$', fontsize=12)
    ax2.set_ylabel('Normalized Entropy $S/S_{\\mathrm{Page}}$', fontsize=12)
    ax2.legend(fontsize=9, ncol=2)
    ax2.grid(True, alpha=0.3)
    ax2.set_title('(b) Normalized Entropy', fontsize=12)
    ax2.set_ylim(0, 1.15)
    
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig1_entropy_vs_depth.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig1 done")


# ============================================================
# Figure 2: Ratio Sweep (multi-config)
# ============================================================

def fig2():
    """Two-qubit ratio sweep for multiple (n, depth) configurations."""
    df = load('exp2_ratio_sweep')
    if df is None:
        print("  fig2: NO DATA"); return
    
    configs = sorted(df.groupby(['n_qubits', 'depth']).size().index.tolist())
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    for i, (n, d) in enumerate(configs):
        sub = df[(df.n_qubits == n) & (df.depth == d)]
        grp = sub.groupby('two_qubit_ratio')['entanglement_entropy']
        m, s = grp.mean(), grp.std()
        page = sub['page_value'].iloc[0] if 'page_value' in sub.columns else 1
        
        ax.fill_between(m.index, m - s, m + s, alpha=0.12, color=COLORS[i])
        ax.plot(m.index, m.values, 's-', ms=4, label=f'$n={n}, d={d}$', 
                color=COLORS[i], lw=1.8)
    
    ax.set_xlabel('Two-Qubit Gate Fraction $\\rho$', fontsize=12)
    ax.set_ylabel('Entanglement Entropy $S$ (bits)', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_title('Entanglement vs Two-Qubit Gate Fraction', fontsize=12)
    
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig2_ratio_sweep.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig2 done")


# ============================================================
# Figure 3: Scaling with bootstrap CI
# ============================================================

def fig3():
    """Critical depth scaling with bootstrap CI and power law fit."""
    df = load('exp3_scaling')
    if df is None:
        print("  fig3: NO DATA"); return
    
    # Compute critical depths per threshold
    from core import get_page_value
    
    scaling_data = []
    for thresh in [0.85, 0.90, 0.95]:
        for n in sorted(df.n_qubits.unique()):
            sub = df[df.n_qubits == n]
            page_val = get_page_value(n)
            threshold = thresh * page_val
            dcs = []
            for t in sub.trial.unique():
                td = sub[sub.trial == t].sort_values('depth')
                exc = td[td.entanglement_entropy >= threshold]
                if len(exc) > 0:
                    dcs.append(int(exc.iloc[0]['depth']))
            if dcs:
                ci_lo, ci_hi = bootstrap_ci(dcs)
                scaling_data.append({
                    'n_qubits': n, 'threshold': thresh,
                    'dc_mean': np.mean(dcs), 'dc_std': np.std(dcs),
                    'dc_ci_lo': ci_lo, 'dc_ci_hi': ci_hi,
                    'n_found': len(dcs), 'n_total': sub.trial.nunique()
                })
    
    sdf = pd.DataFrame(scaling_data)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    
    # Panel (a): d_c vs n for different thresholds
    for i, thresh in enumerate([0.85, 0.90, 0.95]):
        sub = sdf[sdf.threshold == thresh]
        ax1.errorbar(sub.n_qubits, sub.dc_mean, 
                    yerr=[sub.dc_mean - sub.dc_ci_lo, sub.dc_ci_hi - sub.dc_mean],
                    fmt='o-', ms=7, capsize=4, color=COLORS[i], lw=1.5,
                    label=f'threshold = {thresh:.0%}')
    
    ax1.set_xlabel('Number of Qubits $n$', fontsize=12)
    ax1.set_ylabel('Critical Depth $d_c$', fontsize=12)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_title('(a) Critical Depth vs System Size', fontsize=12)
    
    # Panel (b): log-log fit with CI
    sub90 = sdf[sdf.threshold == 0.90]
    valid = sub90[sub90.dc_mean > 0]
    
    if len(valid) >= 3:
        log_n = np.log(valid.n_qubits.values.astype(float))
        log_dc = np.log(valid.dc_mean.values.astype(float))
        slope, intercept, r_value, p_value, std_err = sp_stats.linregress(log_n, log_dc)
        
        ax2.errorbar(valid.n_qubits, valid.dc_mean,
                    yerr=[valid.dc_mean - valid.dc_ci_lo, valid.dc_ci_hi - valid.dc_mean],
                    fmt='o', ms=8, capsize=5, color='darkred', lw=2, label='Data')
        
        nf = np.linspace(valid.n_qubits.min() - 0.5, valid.n_qubits.max() + 0.5, 100)
        ax2.plot(nf, np.exp(intercept) * nf**slope, '--', color='gray', alpha=0.7, lw=2,
                label=f'$d_c \\propto n^{{{slope:.2f} \\pm {std_err:.2f}}}$\n'
                      f'$R^2 = {r_value**2:.4f}$')
        
        ax2.set_xlabel('Number of Qubits $n$', fontsize=12)
        ax2.set_ylabel('Critical Depth $d_c$', fontsize=12)
        ax2.set_xscale('log')
        ax2.set_yscale('log')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3, which='both')
        ax2.set_title('(b) Log-Log Scaling Fit', fontsize=12)
    
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig3_scaling.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    del df, sdf; gc.collect()
    print("  fig3 done")


# ============================================================
# Figure 4: Optimization vs Entanglement (FIXED)
# ============================================================

def fig4():
    """Entanglement vs optimization with proper statistics."""
    df = load('exp4_optimization')
    if df is None:
        print("  fig4: NO DATA"); return
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    
    # Panel (a): Scatter for each n (level 2)
    ax = axes[0]
    for i, n in enumerate(sorted(df.n_qubits.unique())):
        sub = df[df.n_qubits == n]
        r, p = sp_stats.pearsonr(sub.entanglement_entropy, sub.gate_reduction_2)
        ax.scatter(sub.entanglement_entropy, sub.gate_reduction_2,
                  alpha=0.4, s=20, color=COLORS[i], label=f'$n={n}$ (r={r:.3f})')
    
    ax.set_xlabel('Entanglement Entropy (bits)', fontsize=11)
    ax.set_ylabel('Gate Reduction (level 2)', fontsize=11)
    ax.legend(fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_title('(a) By Qubit Count', fontsize=11)
    
    # Panel (b): Scatter colored by depth (level 2)
    ax = axes[1]
    sc = ax.scatter(df.entanglement_entropy, df.gate_reduction_2,
                   c=df.depth, cmap='viridis', s=25, edgecolors='k', lw=0.3, alpha=0.6)
    plt.colorbar(sc, ax=ax, label='Depth')
    
    # Overall correlation with bootstrap CI
    r, p = sp_stats.pearsonr(df.entanglement_entropy, df.gate_reduction_2)
    # Bootstrap CI for r
    rng = np.random.RandomState(42)
    boot_rs = []
    for _ in range(1000):
        idx = rng.choice(len(df), size=len(df), replace=True)
        boot_r, _ = sp_stats.pearsonr(df.entanglement_entropy.iloc[idx], 
                                       df.gate_reduction_2.iloc[idx])
        boot_rs.append(boot_r)
    r_ci_lo, r_ci_hi = np.percentile(boot_rs, [2.5, 97.5])
    
    ax.text(0.05, 0.95, f'$r = {r:.3f}$ [{r_ci_lo:.3f}, {r_ci_hi:.3f}]\n$p = {p:.1e}$',
           transform=ax.transAxes, va='top', fontsize=10,
           bbox=dict(boxstyle='round', fc='wheat', alpha=0.5))
    ax.set_xlabel('Entanglement Entropy (bits)', fontsize=11)
    ax.set_ylabel('Gate Reduction (level 2)', fontsize=11)
    ax.set_title('(b) Overall Correlation', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # Panel (c): Both vs depth for each n
    ax = axes[2]
    for i, n in enumerate(sorted(df.n_qubits.unique())):
        sub = df[df.n_qubits == n].groupby('depth').agg({
            'entanglement_entropy': 'mean',
            'gate_reduction_2': 'mean'
        })
        ax.plot(sub.index, sub.entanglement_entropy, 'o-', color=COLORS[i], 
               ms=4, lw=1.5, label=f'$n={n}$ entropy')
    ax.set_xlabel('Depth', fontsize=11)
    ax.set_ylabel('Mean Entanglement Entropy (bits)', fontsize=11)
    ax.legend(fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_title('(c) Entropy vs Depth by $n$', fontsize=11)
    
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig4_optimization.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig4 done")


# ============================================================
# Figure 5: Phase Diagram Heatmap
# ============================================================

def fig5():
    """Phase diagram heatmap."""
    df = load('exp1_entropy_vs_depth')
    if df is None:
        print("  fig5: NO DATA"); return
    
    # Normalize by Page value
    df['norm_entropy'] = df['entanglement_entropy'] / df['page_value']
    
    depths = sorted(d for d in df.depth.unique() if d <= 50)
    pivot = df[df.depth.isin(depths)].pivot_table(
        values='norm_entropy', index='n_qubits', columns='depth', aggfunc='mean')
    
    fig, ax = plt.subplots(figsize=(12, 4.5))
    im = ax.imshow(pivot.values, aspect='auto', cmap='YlOrRd', origin='lower',
                   interpolation='nearest', vmin=0, vmax=1)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xticks(range(0, len(pivot.columns), 2))
    ax.set_xticklabels(pivot.columns[::2])
    ax.set_xlabel('Circuit Depth', fontsize=12)
    ax.set_ylabel('Number of Qubits', fontsize=12)
    ax.set_title('Entanglement Entropy Phase Diagram ($S/S_{\\mathrm{Page}}$)', fontsize=12)
    cbar = plt.colorbar(im, ax=ax, label='$S/S_{\\mathrm{Page}}$')
    
    # Mark the critical depth line
    from core import get_page_value
    for i, n in enumerate(sorted(pivot.index)):
        sub = df[df.n_qubits == n]
        page = get_page_value(n)
        threshold = 0.9 * page
        dcs = []
        for t in sub.trial.unique():
            td = sub[sub.trial == t].sort_values('depth')
            exc = td[td.entanglement_entropy >= threshold]
            if len(exc) > 0:
                dcs.append(int(exc.iloc[0]['depth']))
        if dcs:
            dc = np.mean(dcs)
            dc_idx = list(pivot.columns).index(int(dc)) if int(dc) in pivot.columns else None
            if dc_idx is not None:
                ax.plot(dc_idx, i, 'k*', ms=12, zorder=5)
    
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig5_phase_diagram.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig5 done")


# ============================================================
# Figure 6: Landscape Comparison (Structural vs Angle)
# ============================================================

def fig6():
    """Landscape analysis: structural vs angle perturbations."""
    df = load('exp5_landscape')
    if df is None:
        print("  fig6: NO DATA"); return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    
    depths = sorted(df.depth.unique())
    
    # Panel (a): Ruggedness comparison
    struct_rug = [df[df.depth == d]['struct_std'].values for d in depths]
    angle_rug = [df[df.depth == d]['angle_std'].values for d in depths]
    
    x = np.arange(len(depths))
    w = 0.35
    ax1.boxplot(struct_rug, positions=x - w/2, widths=w, patch_artist=True,
               boxprops=dict(facecolor='steelblue', alpha=0.6), label='Structural')
    ax1.boxplot(angle_rug, positions=x + w/2, widths=w, patch_artist=True,
               boxprops=dict(facecolor='darkred', alpha=0.6), label='Angle')
    ax1.set_xticks(x)
    ax1.set_xticklabels(depths)
    ax1.set_xlabel('Circuit Depth', fontsize=12)
    ax1.set_ylabel('Perturbation Std (Ruggedness)', fontsize=12)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_title('(a) Landscape Ruggedness', fontsize=12)
    
    # Panel (b): Entropy range comparison
    struct_range = [df[df.depth == d]['struct_range'].values for d in depths]
    angle_range = [df[df.depth == d]['angle_range'].values for d in depths]
    
    ax2.boxplot(struct_range, positions=x - w/2, widths=w, patch_artist=True,
               boxprops=dict(facecolor='steelblue', alpha=0.6), label='Structural')
    ax2.boxplot(angle_range, positions=x + w/2, widths=w, patch_artist=True,
               boxprops=dict(facecolor='darkred', alpha=0.6), label='Angle')
    ax2.set_xticks(x)
    ax2.set_xticklabels(depths)
    ax2.set_xlabel('Circuit Depth', fontsize=12)
    ax2.set_ylabel('Entropy Range (bits)', fontsize=12)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_title('(b) Entropy Range', fontsize=12)
    
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig6_landscape.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig6 done")


# ============================================================
# Figure 7: Gate Set Ablation
# ============================================================

def fig7():
    """Gate set ablation."""
    df = load('exp6_gate_ablation')
    if df is None:
        print("  fig7: NO DATA"); return
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    
    gate_sets = sorted(df.gate_set.unique())
    depths = sorted(df.depth.unique())
    
    for ax_i, n in enumerate(sorted(df.n_qubits.unique())):
        ax = axes[ax_i]
        for i, gs in enumerate(gate_sets):
            sub = df[(df.gate_set == gs) & (df.n_qubits == n)]
            grp = sub.groupby('depth')['entanglement_entropy']
            m, s = grp.mean(), grp.std()
            ax.fill_between(m.index, m - s, m + s, alpha=0.1, color=COLORS[i])
            ax.plot(m.index, m.values, 'o-', ms=4, label=gs, color=COLORS[i], lw=1.5)
        
        ax.set_xlabel('Depth', fontsize=11)
        ax.set_ylabel('Entropy (bits)', fontsize=11)
        ax.set_title(f'$n = {n}$', fontsize=12)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    fig.suptitle('Gate Set Ablation: Entanglement vs Depth', fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig7_gate_ablation.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig7 done")


# ============================================================
# Figure 8: Topology Ablation
# ============================================================

def fig8():
    """Topology ablation."""
    df = load('exp7_topology_ablation')
    if df is None:
        print("  fig8: NO DATA"); return
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    
    topos = sorted(df.topology.unique())
    
    for ax_i, n in enumerate(sorted(df.n_qubits.unique())):
        ax = axes[ax_i]
        for i, topo in enumerate(topos):
            sub = df[(df.topology == topo) & (df.n_qubits == n)]
            grp = sub.groupby('depth')['entanglement_entropy']
            m, s = grp.mean(), grp.std()
            ax.fill_between(m.index, m - s, m + s, alpha=0.1, color=COLORS[i])
            ax.plot(m.index, m.values, 'o-', ms=4, label=topo.replace('_', ' '), 
                   color=COLORS[i], lw=1.5)
        
        ax.set_xlabel('Depth', fontsize=11)
        ax.set_ylabel('Entropy (bits)', fontsize=11)
        ax.set_title(f'$n = {n}$', fontsize=12)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    fig.suptitle('Topology Ablation: Entanglement vs Depth', fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig8_topology_ablation.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig8 done")


# ============================================================
# Figure 9: Initial State Ablation
# ============================================================

def fig9():
    """Initial state ablation."""
    df = load('exp8_initial_state_ablation')
    if df is None:
        print("  fig9: NO DATA"); return
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    
    states = sorted(df.initial_state.unique())
    
    for ax_i, n in enumerate(sorted(df.n_qubits.unique())):
        ax = axes[ax_i]
        for i, st in enumerate(states):
            sub = df[(df.initial_state == st) & (df.n_qubits == n)]
            grp = sub.groupby('depth')['entanglement_entropy']
            m, s = grp.mean(), grp.std()
            ax.fill_between(m.index, m - s, m + s, alpha=0.1, color=COLORS[i])
            ax.plot(m.index, m.values, 'o-', ms=4, label=st, color=COLORS[i], lw=1.5)
        
        ax.set_xlabel('Depth', fontsize=11)
        ax.set_ylabel('Entropy (bits)', fontsize=11)
        ax.set_title(f'$n = {n}$', fontsize=12)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
    
    fig.suptitle('Initial State Ablation: Entanglement vs Depth', fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig9_initial_state_ablation.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig9 done")


# ============================================================
# Figure 10: Threshold Sensitivity
# ============================================================

def fig10():
    """Threshold sensitivity analysis."""
    df = load('threshold_sensitivity')
    if df is None:
        print("  fig10: NO DATA"); return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    
    # Panel (a): alpha vs threshold
    ax1.errorbar(df.threshold_frac, df.alpha, yerr=df.alpha_std,
                fmt='o-', ms=7, capsize=5, color='darkred', lw=2)
    ax1.axhspan(df.alpha.mean() - df.alpha.std(), df.alpha.mean() + df.alpha.std(),
               alpha=0.1, color='gray', label=f'Mean ± Std')
    ax1.set_xlabel('Threshold Fraction', fontsize=12)
    ax1.set_ylabel('Scaling Exponent $\\alpha$', fontsize=12)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_title('(a) Scaling Exponent vs Threshold', fontsize=12)
    
    # Panel (b): R² vs threshold
    ax2.plot(df.threshold_frac, df.r_squared, 's-', ms=7, color='steelblue', lw=2)
    ax2.set_xlabel('Threshold Fraction', fontsize=12)
    ax2.set_ylabel('$R^2$ of Power Law Fit', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.set_title('(b) Fit Quality vs Threshold', fontsize=12)
    
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig10_threshold_sensitivity.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig10 done")


# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    print("Generating publication figures...")
    for fn in [fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig9, fig10]:
        try:
            fn()
        except Exception as e:
            print(f"  ERROR in {fn.__name__}: {e}")
        gc.collect()
    print(f"\nAll figures saved to {OUT_DIR}")
