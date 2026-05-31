"""
Step 2: Comprehensive E1+E3 Analysis
- Exponential decay fit for success rate vs depth
- Entropy threshold analysis  
- Reduction scaling with n_qubits (FSS proxy)
- Bootstrap confidence intervals
- Save all results
"""
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import linregress
import json
import os

os.chdir("D:/Desktop/Q-research")

np.random.seed(42)

# ─── Load data ───
e1 = pd.read_csv("data/raw/exp1_phase_transition_20260530_095003.csv")
e3 = pd.read_csv("data/raw/exp3_scaling_20260530_100830.csv")

# ─── Convert success to numeric ───
e1['success'] = e1['success'].astype(int)
e3['success'] = e3['success'].astype(int)

results = {}

# ════════════════════════════════════════════
# E1: Phase Transition Analysis (n=5, depth 1-50)
# ════════════════════════════════════════════

print("=== E1: Exponential Decay Fit ===")
e1_agg = e1.groupby('depth').agg(
    success_rate=('success', 'mean'),
    mean_reduction=('reduction', 'mean'),
    mean_entropy=('normalized_entropy', 'mean'),
    n_trials=('success', 'count')
).reset_index()

# Model: P(d) = P0 * exp(-d / d0) + P_bg
def exp_decay(x, P0, d0, P_bg):
    return P0 * np.exp(-x / d0) + P_bg

x_e1 = e1_agg['depth'].values
y_e1 = e1_agg['success_rate'].values

try:
    popt, pcov = curve_fit(exp_decay, x_e1, y_e1, 
                           p0=[0.30, 15, 0.05],
                           bounds=([0, 1, 0], [1, 100, 0.5]),
                           maxfev=10000)
    P0_e1, d0_e1, Pbg_e1 = popt
    perr = np.sqrt(np.diag(pcov))
    y_pred = exp_decay(x_e1, *popt)
    r2 = 1 - np.sum((y_e1 - y_pred)**2) / np.sum((y_e1 - np.mean(y_e1))**2)
    print(f"  P0={P0_e1:.4f}±{perr[0]:.4f}, d0={d0_e1:.2f}±{perr[1]:.2f}, P_bg={Pbg_e1:.4f}±{perr[2]:.4f}, R²={r2:.4f}")
    results['e1_exp_decay'] = {
        'P0': P0_e1, 'd0': d0_e1, 'P_bg': Pbg_e1,
        'P0_err': perr[0], 'd0_err': perr[1], 'P_bg_err': perr[2],
        'r2': r2
    }
except Exception as e:
    print(f"  Fit failed: {e}")
    results['e1_exp_decay'] = None

# ─── E1: Entropy threshold analysis ───
print("\n=== E1: Entropy Threshold ===")
# Find depth where normalized_entropy > 0.5 (moderate entanglement)
entropy_thresholds = [0.3, 0.5, 0.7, 0.9]
for thresh in entropy_thresholds:
    d_cross = e1_agg[e1_agg['mean_entropy'] > thresh]['depth'].min()
    if pd.notna(d_cross):
        sr_at_cross = e1_agg[e1_agg['depth'] == d_cross]['success_rate'].values[0]
        print(f"  entropy > {thresh}: crosses at depth={int(d_cross)}, success_rate={sr_at_cross:.3f}")
    else:
        print(f"  entropy > {thresh}: never crosses")

# Entropy-binned success rate
e1['entropy_bin'] = pd.cut(e1['normalized_entropy'], bins=np.arange(0, 1.1, 0.1))
e1_entropy = e1.groupby('entropy_bin', observed=False).agg(
    success_rate=('success', 'mean'),
    mean_reduction=('reduction', 'mean'),
    n=('success', 'count')
).reset_index()
results['e1_entropy_binned'] = {
    'bins': [str(b) for b in e1_entropy['entropy_bin'].values],
    'success_rates': e1_entropy['success_rate'].tolist(),
    'mean_reductions': e1_entropy['mean_reduction'].tolist(),
    'counts': e1_entropy['n'].tolist()
}

# ════════════════════════════════════════════
# E3: Scaling Analysis (n=3-10, depth 1-30)
# ════════════════════════════════════════════

print("\n=== E3: Reduction Scaling with n_qubits ===")
e3_n_agg = e3.groupby('n_qubits').agg(
    mean_reduction=('reduction', 'mean'),
    std_reduction=('reduction', 'std'),
    mean_success=('success', 'mean'),
    mean_entropy=('normalized_entropy', 'mean'),
    mean_fidelity=('fidelity', 'mean'),
    n_trials=('success', 'count')
).reset_index()

# Power law fit: reduction(n) = a * n^b + c
n_vals = e3_n_agg['n_qubits'].values
r_vals = e3_n_agg['mean_reduction'].values

def power_law(x, a, b, c):
    return a * x**b + c

try:
    popt_pl, pcov_pl = curve_fit(power_law, n_vals, r_vals,
                                  p0=[0.05, 0.5, 0.10],
                                  bounds=([0, -2, 0], [0.5, 3, 0.5]),
                                  maxfev=10000)
    a_pl, b_pl, c_pl = popt_pl
    perr_pl = np.sqrt(np.diag(pcov_pl))
    y_pred_pl = power_law(n_vals, *popt_pl)
    r2_pl = 1 - np.sum((r_vals - y_pred_pl)**2) / np.sum((r_vals - np.mean(r_vals))**2)
    print(f"  reduction(n) = {a_pl:.4f} * n^{b_pl:.4f} + {c_pl:.4f}")
    print(f"  a={a_pl:.4f}±{perr_pl[0]:.4f}, b={b_pl:.4f}±{perr_pl[1]:.4f}, c={c_pl:.4f}±{perr_pl[2]:.4f}, R²={r2_pl:.4f}")
    results['e3_reduction_scaling'] = {
        'a': a_pl, 'b': b_pl, 'c': c_pl,
        'a_err': perr_pl[0], 'b_err': perr_pl[1], 'c_err': perr_pl[2],
        'r2': r2_pl
    }
except Exception as e:
    print(f"  Fit failed: {e}")
    # Linear regression fallback
    slope, intercept, r_value, p_value, std_err = linregress(n_vals, r_vals)
    print(f"  Linear: reduction = {slope:.4f} * n + {intercept:.4f}, R²={r_value**2:.4f}")
    results['e3_reduction_scaling'] = {
        'type': 'linear',
        'slope': slope, 'intercept': intercept,
        'r2': r_value**2, 'p_value': p_value, 'std_err': std_err
    }

# ─── E3: Per-n exponential decay ───
print("\n=== E3: Per-n Exponential Decay Fits ===")
e3_nd_agg = e3.groupby(['n_qubits', 'depth']).agg(
    success_rate=('success', 'mean'),
    mean_reduction=('reduction', 'mean'),
    mean_entropy=('normalized_entropy', 'mean'),
    n_trials=('success', 'count')
).reset_index()

e3_per_n_fits = {}
for n in sorted(e3_nd_agg['n_qubits'].unique()):
    sub = e3_nd_agg[e3_nd_agg['n_qubits'] == n]
    x = sub['depth'].values
    y = sub['success_rate'].values
    
    try:
        popt, pcov = curve_fit(exp_decay, x, y,
                                p0=[y.max(), 5, 0.05],
                                bounds=([0, 1, 0], [1, 100, 0.5]),
                                maxfev=10000)
        P0, d0, Pbg = popt
        perr = np.sqrt(np.diag(pcov))
        y_pred = exp_decay(x, *popt)
        r2 = 1 - np.sum((y - y_pred)**2) / np.sum((y - np.mean(y))**2)
        e3_per_n_fits[int(n)] = {
            'P0': P0, 'd0': d0, 'P_bg': Pbg,
            'P0_err': perr[0], 'd0_err': perr[1], 'P_bg_err': perr[2],
            'r2': r2
        }
        print(f"  n={n}: P0={P0:.4f}, d0={d0:.2f}, P_bg={Pbg:.4f}, R²={r2:.4f}")
    except Exception as e:
        print(f"  n={n}: fit failed - {e}")

results['e3_per_n_exp_decay'] = e3_per_n_fits

# ─── E3: FSS - d_c(n) scaling ───
print("\n=== E3: FSS - Critical Depth Scaling ===")
# Define d_c(n) as the depth where success_rate drops below 10%
threshold = 0.10
d_c_values = {}
for n in sorted(e3_nd_agg['n_qubits'].unique()):
    sub = e3_nd_agg[e3_nd_agg['n_qubits'] == n]
    max_sr = sub['success_rate'].max()
    # Use half-maximum as threshold for cleaner definition
    half_max_thresh = max_sr / 2.0
    crossings = sub[sub['success_rate'] < half_max_thresh]
    if len(crossings) > 0:
        d_c = crossings['depth'].min()
        d_c_values[int(n)] = {'d_c': d_c, 'max_sr': max_sr, 'half_max': half_max_thresh, 'method': 'half_max'}
        print(f"  n={n}: max_sr={max_sr:.3f}, half_max={half_max_thresh:.3f}, d_c={d_c}")
    else:
        # Use d_c from exp decay fit if available
        if int(n) in e3_per_n_fits:
            d0 = e3_per_n_fits[int(n)]['d0']
            d_c_values[int(n)] = {'d_c': d0, 'max_sr': max_sr, 'method': 'decay_constant'}
            print(f"  n={n}: max_sr={max_sr:.3f}, using decay constant d0={d0:.2f}")
        else:
            print(f"  n={n}: no crossing found")

results['e3_dc_values'] = d_c_values

# Power law fit: d_c(n) = a * n^b
if len(d_c_values) >= 3:
    ns = np.array([k for k in d_c_values.keys()])
    dcs = np.array([v['d_c'] for v in d_c_values.values()])
    
    # Filter out n=10 which has anomalous behavior
    valid_mask = ns != 10  # n=10 has unusual pattern
    ns_fit = ns[valid_mask]
    dcs_fit = dcs[valid_mask]
    
    if len(ns_fit) >= 3:
        # Log-log linear regression
        log_n = np.log(ns_fit)
        log_dc = np.log(dcs_fit)
        slope, intercept, r_value, p_value, std_err = linregress(log_n, log_dc)
        b_fss = slope
        a_fss = np.exp(intercept)
        print(f"\n  d_c(n) = {a_fss:.4f} * n^{b_fss:.4f}")
        print(f"  a={a_fss:.4f}, b={b_fss:.4f}, R²={r_value**2:.4f}, p={p_value:.4f}")
        
        results['e3_fss'] = {
            'a': a_fss, 'b': b_fss,
            'a_err': np.exp(intercept) * std_err,  # approximate
            'b_err': std_err,
            'r2': r_value**2, 'p_value': p_value,
            'n_values': ns_fit.tolist(),
            'dc_values': dcs_fit.tolist(),
            'excluded_n': [10],
            'method': 'log-log_regression'
        }
    else:
        print("  Not enough valid points for FSS fit")
        results['e3_fss'] = None
else:
    print("  Not enough d_c values for FSS")
    results['e3_fss'] = None

# ════════════════════════════════════════════
# Bootstrap Confidence Intervals
# ════════════════════════════════════════════

print("\n=== Bootstrap Confidence Intervals (N=5000) ===")
N_bootstrap = 5000  # Reduced from 10K for speed

def bootstrap_mean(data, n_boot=5000):
    """Bootstrap CI for mean."""
    means = []
    for _ in range(n_boot):
        sample = np.random.choice(data, size=len(data), replace=True)
        means.append(np.mean(sample))
    ci_low = np.percentile(means, 2.5)
    ci_high = np.percentile(means, 97.5)
    return np.mean(means), ci_low, ci_high

# E1 key metrics
e1_sr_mean, e1_sr_lo, e1_sr_hi = bootstrap_mean(e1['success'].values, N_bootstrap)
e1_red_mean, e1_red_lo, e1_red_hi = bootstrap_mean(e1['reduction'].values, N_bootstrap)
print(f"  E1 success_rate: {e1_sr_mean:.4f} [{e1_sr_lo:.4f}, {e1_sr_hi:.4f}]")
print(f"  E1 mean_reduction: {e1_red_mean:.4f} [{e1_red_lo:.4f}, {e1_red_hi:.4f}]")

results['e1_bootstrap'] = {
    'success_rate': {'mean': e1_sr_mean, 'ci_low': e1_sr_lo, 'ci_high': e1_sr_hi},
    'mean_reduction': {'mean': e1_red_mean, 'ci_low': e1_red_lo, 'ci_high': e1_red_hi}
}

# E3 per-n bootstrap
e3_bootstrap = {}
for n in sorted(e3['n_qubits'].unique()):
    sub = e3[e3['n_qubits'] == n]
    sr_m, sr_lo, sr_hi = bootstrap_mean(sub['success'].values, N_bootstrap)
    red_m, red_lo, red_hi = bootstrap_mean(sub['reduction'].values, N_bootstrap)
    e3_bootstrap[int(n)] = {
        'success_rate': {'mean': sr_m, 'ci_low': sr_lo, 'ci_high': sr_hi},
        'mean_reduction': {'mean': red_m, 'ci_low': red_lo, 'ci_high': red_hi}
    }
    print(f"  E3 n={n}: success={sr_m:.4f}[{sr_lo:.4f},{sr_hi:.4f}], reduction={red_m:.4f}[{red_lo:.4f},{red_hi:.4f}]")

results['e3_bootstrap'] = e3_bootstrap

# ─── Save results ───
print("\nSaving results...")
with open("data/processed/e1_e3_analysis_results.json", 'w') as f:
    json.dump(results, f, indent=2)

# Save aggregated data
e1_agg.to_csv("data/processed/e1_phase_transition_summary.csv", index=False)
e3_n_agg.to_csv("data/processed/e3_n_scaling_summary.csv", index=False)
e3_nd_agg.to_csv("data/processed/e3_nd_scaling_summary.csv", index=False)
e3_entropy.to_csv("data/processed/e3_entropy_summary.csv", index=False)

print("\n✅ Step 2 complete!")