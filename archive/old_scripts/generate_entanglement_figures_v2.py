"""
Publication figures - Memory optimized version
"""
import gc
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.size'] = 11

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

DATA_DIR = 'D:/Desktop/Q-research/data/raw'
OUT_DIR = 'D:/Desktop/Q-research/figures/final'
os.makedirs(OUT_DIR, exist_ok=True)


def load(name_pattern):
    files = sorted([f for f in os.listdir(DATA_DIR) if name_pattern in f], reverse=True)
    if files:
        return pd.read_csv(os.path.join(DATA_DIR, files[0]))
    return None


def fig1():
    """Entropy vs depth."""
    df = load('exp1_entropy_vs_depth')
    if df is None: return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for i, n in enumerate(sorted(df.n_qubits.unique())):
        sub = df[df.n_qubits == n].groupby('depth')['entanglement_entropy']
        m, s = sub.mean(), sub.std()
        ax1.fill_between(m.index, m-s, m+s, alpha=0.15, color=colors[i%6])
        ax1.plot(m.index, m.values, 'o-', ms=3, label=f'n={n}', color=colors[i%6], lw=1.5)
    
    ax1.set_xlabel('Circuit Depth d')
    ax1.set_ylabel('Entanglement Entropy S (bits)')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_title('(a) Entanglement Entropy vs Depth')
    
    # Normalized
    for i, n in enumerate(sorted(df.n_qubits.unique())):
        sub = df[df.n_qubits == n]
        mx = sub['max_entropy'].iloc[0]
        grp = sub.groupby('depth')['entanglement_entropy']
        m, s = grp.mean()/mx, grp.std()/mx
        ax2.fill_between(m.index, m-s, m+s, alpha=0.15, color=colors[i%6])
        ax2.plot(m.index, m.values, 'o-', ms=3, label=f'n={n}', color=colors[i%6], lw=1.5)
    
    ax2.axhline(0.9, color='red', ls='--', alpha=0.5, label='90% threshold')
    ax2.set_xlabel('Circuit Depth d')
    ax2.set_ylabel('Normalized Entropy S/S_max')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_title('(b) Normalized Entropy')
    ax2.set_ylim(0, 1.15)
    
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig1_entropy_vs_depth.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig1 done")


def fig2():
    """Ratio sweep."""
    df = load('exp2_ratio_sweep')
    if df is None: return
    
    fig, ax = plt.subplots(figsize=(7, 4))
    grp = df.groupby('two_qubit_ratio')['entanglement_entropy']
    m, s = grp.mean(), grp.std()
    ax.fill_between(m.index, m-s, m+s, alpha=0.2, color='steelblue')
    ax.plot(m.index, m.values, 's-', ms=5, color='steelblue', lw=2)
    ax.set_xlabel('Two-Qubit Gate Ratio ρ')
    ax.set_ylabel('Entanglement Entropy S (bits)')
    ax.set_title('Entanglement vs Two-Qubit Gate Fraction (n=6, d=15)')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig2_ratio_sweep.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig2 done")


def fig3():
    """Scaling: d_c vs n."""
    df = load('exp3_scaling')
    if df is None: return
    
    scaling = []
    for n in sorted(df.n_qubits.unique()):
        sub = df[df.n_qubits == n]
        threshold = sub['threshold'].iloc[0]
        dcs = []
        for t in sub.trial.unique():
            td = sub[sub.trial == t]
            exc = td[td.exceeds_threshold]
            if len(exc) > 0:
                dcs.append(exc['depth'].min())
        if dcs:
            scaling.append({'n': n, 'dc': np.mean(dcs), 'dc_std': np.std(dcs)})
    
    sdf = pd.DataFrame(scaling)
    
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.errorbar(sdf.n, sdf.dc, yerr=sdf.dc_std, fmt='o-', ms=7, capsize=4,
                color='darkred', lw=2, ecolor='red')
    
    # Power law fit
    if len(sdf) > 2:
        from scipy.stats import linregress
        sl, ic, r, p, se = linregress(np.log(sdf.n), np.log(sdf.dc))
        nf = np.linspace(sdf.n.min(), sdf.n.max(), 50)
        ax.plot(nf, np.exp(ic)*nf**sl, '--', color='gray', alpha=0.7,
                label=f'$d_c \\propto n^{{{sl:.2f}}}$ ($R^2={r**2:.3f}$)')
    
    ax.set_xlabel('Number of Qubits n')
    ax.set_ylabel('Critical Depth $d_c$')
    ax.set_title('Scaling of Critical Depth with System Size')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig3_scaling.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    del df, sdf; gc.collect()
    print("  fig3 done")


def fig4():
    """Optimization vs entanglement."""
    df = load('exp4_optimization')
    if df is None: return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    
    sc = ax1.scatter(df.entanglement_entropy, df.gate_reduction, 
                     c=df.depth, cmap='viridis', s=40, edgecolors='k', lw=0.5, alpha=0.7)
    plt.colorbar(sc, ax=ax1, label='Depth')
    
    from scipy.stats import pearsonr
    r, p = pearsonr(df.entanglement_entropy, df.gate_reduction)
    ax1.text(0.05, 0.95, f'r = {r:.3f}\np = {p:.1e}', transform=ax1.transAxes,
             va='top', fontsize=10, bbox=dict(boxstyle='round', fc='wheat', alpha=0.5))
    ax1.set_xlabel('Entanglement Entropy (bits)')
    ax1.set_ylabel('Gate Reduction')
    ax1.set_title('(a) Entanglement vs Optimization')
    ax1.grid(True, alpha=0.3)
    
    dm = df.groupby('depth').agg({'entanglement_entropy': 'mean', 'gate_reduction': 'mean'})
    ax2b = ax2.twinx()
    l1 = ax2.plot(dm.index, dm.entanglement_entropy, 'o-', color='steelblue', lw=2, label='Entropy')
    l2 = ax2b.plot(dm.index, dm.gate_reduction, 's-', color='darkred', lw=2, label='Reduction')
    ax2.set_xlabel('Depth')
    ax2.set_ylabel('Entropy (bits)', color='steelblue')
    ax2b.set_ylabel('Gate Reduction', color='darkred')
    ax2.legend(l1+l2, [l.get_label() for l in l1+l2], fontsize=9)
    ax2.set_title('(b) Both vs Depth')
    ax2.grid(True, alpha=0.3)
    
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig4_optimization.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig4 done")


def fig5():
    """Phase diagram heatmap."""
    df = load('exp1_entropy_vs_depth')
    if df is None: return
    
    depths = sorted(d for d in df.depth.unique() if d <= 30)
    pivot = df[df.depth.isin(depths)].pivot_table(
        values='entanglement_entropy', index='n_qubits', columns='depth', aggfunc='mean')
    
    fig, ax = plt.subplots(figsize=(10, 4.5))
    im = ax.imshow(pivot.values, aspect='auto', cmap='YlOrRd', origin='lower', interpolation='nearest')
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xticks(range(0, len(pivot.columns), 2))
    ax.set_xticklabels(pivot.columns[::2])
    ax.set_xlabel('Circuit Depth')
    ax.set_ylabel('Number of Qubits')
    ax.set_title('Entanglement Entropy Phase Diagram')
    plt.colorbar(im, ax=ax, label='Entropy (bits)')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig5_phase_diagram.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    del df; gc.collect()
    print("  fig5 done")


if __name__ == '__main__':
    print("Generating figures...")
    fig1(); gc.collect()
    fig2(); gc.collect()
    fig3(); gc.collect()
    fig4(); gc.collect()
    fig5(); gc.collect()
    print(f"\nAll figures saved to {OUT_DIR}")
