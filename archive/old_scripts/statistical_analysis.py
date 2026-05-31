"""
Statistical Analysis for Quantum Circuit Paper - v2
====================================================
Computes: bootstrap CI, effect sizes, correlation analysis,
threshold sensitivity, E4 conditional analysis.
"""

import os
import json
import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from datetime import datetime

DATA_DIR = 'D:/Desktop/Q-research/data/raw'
OUT_DIR = 'D:/Desktop/Q-research/data/analysis'
os.makedirs(OUT_DIR, exist_ok=True)


def bootstrap_ci(data, n_bootstrap=2000, ci=0.95, seed=42):
    """Bootstrap CI for the mean."""
    rng = np.random.RandomState(seed)
    means = [np.mean(rng.choice(data, size=len(data), replace=True)) for _ in range(n_bootstrap)]
    alpha = (1 - ci) / 2
    return float(np.percentile(means, 100 * alpha)), float(np.percentile(means, 100 * (1 - alpha)))


def bootstrap_corr(x, y, n_bootstrap=2000, seed=42):
    """Bootstrap CI for Pearson correlation."""
    rng = np.random.RandomState(seed)
    rs = []
    for _ in range(n_bootstrap):
        idx = rng.choice(len(x), size=len(x), replace=True)
        r, _ = sp_stats.pearsonr(x.iloc[idx], y.iloc[idx])
        rs.append(r)
    return float(np.percentile(rs, 2.5)), float(np.percentile(rs, 97.5))


def cohens_d(x, y):
    """Cohen's d effect size."""
    nx, ny = len(x), len(y)
    pooled_std = np.sqrt(((nx-1)*np.std(x, ddof=1)**2 + (ny-1)*np.std(y, ddof=1)**2) / (nx+ny-2))
    if pooled_std == 0:
        return 0.0
    return (np.mean(x) - np.mean(y)) / pooled_std


def load(name):
    files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith(name) and f.endswith('.csv')],
                   reverse=True)
    if files:
        return pd.read_csv(os.path.join(DATA_DIR, files[0]))
    return None


def analyze_e1():
    """E1: Entropy vs depth analysis."""
    print("\n=== E1: Entropy vs Depth ===")
    df = load('exp1_entropy_vs_depth')
    if df is None:
        return {}
    
    results = {}
    for n in sorted(df.n_qubits.unique()):
        sub = df[df.n_qubits == n]
        page = sub['page_value'].iloc[0]
        
        # Find depth where normalized entropy first exceeds 0.9
        for d in sorted(sub.depth.unique()):
            dsub = sub[sub.depth == d]
            mean_norm = dsub['normalized_entropy'].mean()
            if mean_norm >= 0.9:
                results[f'd_saturation_n{n}'] = d
                break
        
        # Maximum entropy achieved
        max_S = sub.groupby('depth')['entanglement_entropy'].mean().max()
        results[f'max_S_n{n}'] = float(max_S)
        results[f'page_n{n}'] = float(page)
        results[f'max_S_ratio_n{n}'] = float(max_S / page)
        
        print(f"  n={n}: page={page:.4f}, max_S={max_S:.4f}, ratio={max_S/page:.3f}")
    
    return results


def analyze_e2():
    """E2: Ratio sweep analysis."""
    print("\n=== E2: Ratio Sweep ===")
    df = load('exp2_ratio_sweep')
    if df is None:
        return {}
    
    results = {}
    for (n, d), grp in df.groupby(['n_qubits', 'depth']):
        means = grp.groupby('two_qubit_ratio')['entanglement_entropy'].mean()
        optimal_rho = means.idxmax()
        max_S = means.max()
        results[f'optimal_rho_n{n}_d{d}'] = float(optimal_rho)
        results[f'max_S_rho_n{n}_d{d}'] = float(max_S)
        print(f"  n={n}, d={d}: optimal_rho={optimal_rho:.2f}, max_S={max_S:.4f}")
    
    # Test non-monotonicity
    for (n, d), grp in df.groupby(['n_qubits', 'depth']):
        means = grp.groupby('two_qubit_ratio')['entanglement_entropy'].mean().sort_index()
        ratios = means.index.values
        values = means.values
        # Find if there's a peak (value higher than both neighbors)
        for i in range(1, len(values) - 1):
            if values[i] > values[i-1] and values[i] > values[i+1]:
                results[f'peak_detected_n{n}_d{d}'] = True
                break
    
    return results


def analyze_e3():
    """E3: Scaling analysis with multiple thresholds."""
    print("\n=== E3: Scaling Analysis ===")
    df = load('exp3_scaling')
    if df is None:
        return {}
    
    results = {}
    
    # Load Page values
    from core import get_page_value
    
    for thresh in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
        scaling = []
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
            
            if dcs and len(dcs) >= 5:
                ci_lo, ci_hi = bootstrap_ci(dcs)
                scaling.append({
                    'n': n, 'dc_mean': np.mean(dcs), 'dc_std': np.std(dcs),
                    'dc_ci_lo': ci_lo, 'dc_ci_hi': ci_hi,
                    'n_found': len(dcs), 'n_total': sub.trial.nunique()
                })
                print(f"  thresh={thresh}, n={n}: d_c={np.mean(dcs):.1f}±{np.std(dcs):.1f}, "
                      f"CI=[{ci_lo:.1f},{ci_hi:.1f}], found={len(dcs)}/{sub.trial.nunique()}")
        
        if len(scaling) >= 3:
            sdf = pd.DataFrame(scaling)
            valid = sdf[sdf.dc_mean > 0]
            log_n = np.log(valid.n.values.astype(float))
            log_dc = np.log(valid.dc_mean.values.astype(float))
            slope, intercept, r_value, p_value, std_err = sp_stats.linregress(log_n, log_dc)
            
            results[f'alpha_{thresh}'] = slope
            results[f'alpha_std_{thresh}'] = std_err
            results[f'r_squared_{thresh}'] = r_value**2
            results[f'p_value_{thresh}'] = p_value
            
            print(f"  => alpha={slope:.3f}±{std_err:.3f}, R²={r_value**2:.4f}, p={p_value:.2e}")
    
    return results


def analyze_e4():
    """E4: Optimization vs entanglement - CONDITIONAL analysis."""
    print("\n=== E4: Optimization vs Entanglement ===")
    df = load('exp4_optimization')
    if df is None:
        return {}
    
    results = {}
    
    # Overall correlation
    r, p = sp_stats.pearsonr(df.entanglement_entropy, df.gate_reduction_2)
    r_ci_lo, r_ci_hi = bootstrap_corr(df.entanglement_entropy, df.gate_reduction_2)
    results['overall_r'] = r
    results['overall_p'] = p
    results['overall_r_ci'] = [r_ci_lo, r_ci_hi]
    print(f"  Overall: r={r:.4f} [{r_ci_lo:.4f},{r_ci_hi:.4f}], p={p:.2e}")
    
    # Conditional on depth (partial correlation)
    for depth in sorted(df.depth.unique()):
        sub = df[df.depth == depth]
        if len(sub) >= 10:
            r_d, p_d = sp_stats.pearsonr(sub.entanglement_entropy, sub.gate_reduction_2)
            results[f'r_depth{depth}'] = r_d
            results[f'p_depth{depth}'] = p_d
            print(f"  depth={depth}: r={r_d:.4f}, p={p_d:.2e}")
    
    # Conditional on n
    for n in sorted(df.n_qubits.unique()):
        sub = df[df.n_qubits == n]
        if len(sub) >= 10:
            r_n, p_n = sp_stats.pearsonr(sub.entanglement_entropy, sub.gate_reduction_2)
            r_ci = bootstrap_corr(sub.entanglement_entropy, sub.gate_reduction_2)
            results[f'r_n{n}'] = r_n
            results[f'p_n{n}'] = p_n
            results[f'r_ci_n{n}'] = r_ci
            print(f"  n={n}: r={r_n:.4f} [{r_ci[0]:.4f},{r_ci[1]:.4f}], p={p_n:.2e}")
    
    # Multiple regression: gate_reduction ~ entropy + depth + n + gate_count
    from numpy.linalg import lstsq
    X = df[['entanglement_entropy', 'depth', 'n_qubits', 'gate_count']].values
    X = np.column_stack([np.ones(len(X)), X])
    y = df['gate_reduction_2'].values
    beta, residuals, rank, sv = lstsq(X, y, rcond=None)
    y_pred = X @ beta
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r_squared = 1 - ss_res / ss_tot
    results['multivariate_r_squared'] = r_squared
    results['multivariate_beta'] = beta.tolist()
    print(f"  Multivariate R²={r_squared:.4f}")
    print(f"  beta (entropy, depth, n, gate_count): {beta[1]:.4f}, {beta[2]:.4f}, {beta[3]:.4f}, {beta[4]:.6f}")
    
    # Level 3 comparison
    r3, p3 = sp_stats.pearsonr(df.entanglement_entropy, df.gate_reduction_3)
    results['overall_r_level3'] = r3
    results['overall_p_level3'] = p3
    print(f"  Level 3: r={r3:.4f}, p={p3:.2e}")
    
    return results


def analyze_e5():
    """E5: Landscape analysis."""
    print("\n=== E5: Landscape Analysis ===")
    df = load('exp5_landscape')
    if df is None:
        return {}
    
    results = {}
    
    # Compare structural vs angle ruggedness
    struct_rug = df['struct_std'].values
    angle_rug = df['angle_std'].values
    
    # Filter out zero entries for meaningful comparison
    struct_nonzero = struct_rug[struct_rug > 1e-10]
    angle_nonzero = angle_rug[angle_rug > 1e-10]
    
    results['struct_mean_rug'] = float(np.mean(struct_rug))
    results['angle_mean_rug'] = float(np.mean(angle_rug))
    results['struct_nonzero_frac'] = float(np.mean(struct_rug > 1e-10))
    results['angle_nonzero_frac'] = float(np.mean(angle_rug > 1e-10))
    
    if len(struct_nonzero) > 5 and len(angle_nonzero) > 5:
        t_stat, t_p = sp_stats.ttest_ind(struct_nonzero, angle_nonzero)
        d = cohens_d(struct_nonzero, angle_nonzero)
        results['ttest_stat'] = float(t_stat)
        results['ttest_p'] = float(t_p)
        results['cohens_d'] = float(d)
        print(f"  Structural vs Angle: t={t_stat:.3f}, p={t_p:.2e}, d={d:.3f}")
    
    # By depth
    for depth in sorted(df.depth.unique()):
        sub = df[df.depth == depth]
        s_mean = sub['struct_std'].mean()
        a_mean = sub['angle_std'].mean()
        results[f'struct_rug_d{depth}'] = float(s_mean)
        results[f'angle_rug_d{depth}'] = float(a_mean)
        print(f"  depth={depth}: struct={s_mean:.6f}, angle={a_mean:.6f}")
    
    return results


def analyze_e6_e7_e8():
    """Ablation studies analysis."""
    print("\n=== E6: Gate Set Ablation ===")
    df6 = load('exp6_gate_ablation')
    results = {}
    
    if df6 is not None:
        # ANOVA across gate sets for each (n, depth)
        for n in sorted(df6.n_qubits.unique()):
            for depth in [10, 20]:
                sub = df6[(df6.n_qubits == n) & (df6.depth == depth)]
                groups = [sub[sub.gate_set == gs]['entanglement_entropy'].values 
                         for gs in sorted(sub.gate_set.unique())]
                if all(len(g) >= 5 for g in groups):
                    f_stat, p_val = sp_stats.f_oneway(*groups)
                    results[f'anova_gate_n{n}_d{depth}'] = {'f': float(f_stat), 'p': float(p_val)}
                    print(f"  n={n}, d={depth}: ANOVA F={f_stat:.3f}, p={p_val:.2e}")
    
    print("\n=== E7: Topology Ablation ===")
    df7 = load('exp7_topology_ablation')
    
    if df7 is not None:
        for n in sorted(df7.n_qubits.unique()):
            for depth in [10, 20]:
                sub = df7[(df7.n_qubits == n) & (df7.depth == depth)]
                groups = [sub[sub.topology == t]['entanglement_entropy'].values 
                         for t in sorted(sub.topology.unique())]
                if all(len(g) >= 5 for g in groups):
                    f_stat, p_val = sp_stats.f_oneway(*groups)
                    results[f'anova_topo_n{n}_d{depth}'] = {'f': float(f_stat), 'p': float(p_val)}
                    print(f"  n={n}, d={depth}: ANOVA F={f_stat:.3f}, p={p_val:.2e}")
    
    print("\n=== E8: Initial State Ablation ===")
    df8 = load('exp8_initial_state_ablation')
    
    if df8 is not None:
        for n in sorted(df8.n_qubits.unique()):
            for depth in [10, 20]:
                sub = df8[(df8.n_qubits == n) & (df8.depth == depth)]
                groups = [sub[sub.initial_state == s]['entanglement_entropy'].values 
                         for s in sorted(sub.initial_state.unique())]
                if all(len(g) >= 5 for g in groups):
                    f_stat, p_val = sp_stats.f_oneway(*groups)
                    results[f'anova_state_n{n}_d{depth}'] = {'f': float(f_stat), 'p': float(p_val)}
                    print(f"  n={n}, d={depth}: ANOVA F={f_stat:.3f}, p={p_val:.2e}")
    
    return results


def main():
    print("=" * 60)
    print("STATISTICAL ANALYSIS")
    print("=" * 60)
    
    all_results = {}
    all_results['e1'] = analyze_e1()
    all_results['e2'] = analyze_e2()
    all_results['e3'] = analyze_e3()
    all_results['e4'] = analyze_e4()
    all_results['e5'] = analyze_e5()
    all_results['ablation'] = analyze_e6_e7_e8()
    all_results['timestamp'] = datetime.now().isoformat()
    
    # Save
    out_path = os.path.join(OUT_DIR, 'statistical_analysis.json')
    with open(out_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n\nAnalysis saved to {out_path}")
    return all_results


if __name__ == '__main__':
    main()
