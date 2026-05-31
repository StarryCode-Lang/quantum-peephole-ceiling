"""
Step 2b: Save E1+E3 analysis results (fix JSON serialization)
"""
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import linregress
import json
import os

os.chdir("D:/Desktop/Q-research")
np.random.seed(42)

# Custom JSON encoder for numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super().default(obj)

# ─── Load data ───
e1 = pd.read_csv("data/raw/exp1_phase_transition_20260530_095003.csv")
e3 = pd.read_csv("data/raw/exp3_scaling_20260530_100830.csv")
e1['success'] = e1['success'].astype(int)
e3['success'] = e3['success'].astype(int)

results = {}

# ════════════════════════════════════════════
# E1: Phase Transition Analysis
# ════════════════════════════════════════════

print("=== E1 Analysis ===")
e1_agg = e1.groupby('depth').agg(
    success_rate=('success', 'mean'),
    mean_reduction=('reduction', 'mean'),
    mean_entropy=('normalized_entropy', 'mean'),
    n_trials=('success', 'count')
).reset_index()

# Exponential decay: P(d) = P0 * exp(-d/d0) + P_bg
def exp_decay(x, P0, d0, P_bg):
    return P0 * np.exp(-x / d0) + P_bg

x_e1 = e1_agg['depth'].values
y_e1 = e1_agg['success_rate'].values

popt, pcov = curve_fit(exp_decay, x_e1, y_e1, p0=[0.30, 15, 0.05],
                       bounds=([0, 1, 0], [1, 100, 0.5]), maxfev=10000)
P0_e1, d0_e1, Pbg_e1 = popt
perr = np.sqrt(np.diag(pcov))
y_pred = exp_decay(x_e1, *popt)
r2_e1 = 1 - np.sum((y_e1 - y_pred)**2) / np.sum((y_e1 - np.mean(y_e1))**2)
print(f"  P(d) = {P0_e1:.4f}*exp(-d/{d0_e1:.2f}) + {Pbg_e1:.4f}, R²={r2_e1:.4f}")

results['e1_exp_decay'] = {
    'P0': float(P0_e1), 'd0': float(d0_e1), 'P_bg': float(Pbg_e1),
    'P0_err': float(perr[0]), 'd0_err': float(perr[1]), 'P_bg_err': float(perr[2]),
    'r2': float(r2_e1)
}

# Entropy threshold
entropy_thresholds = {'0.3': 9, '0.5': 11, '0.7': 15, '0.9': 24}
for thresh_str, d_cross in entropy_thresholds.items():
    sr = float(e1_agg[e1_agg['depth'] == d_cross]['success_rate'].values[0])
    entropy_thresholds[thresh_str] = {'depth': d_cross, 'success_rate': sr}
results['e1_entropy_thresholds'] = entropy_thresholds

# Entropy binned
e1['entropy_bin'] = pd.cut(e1['normalized_entropy'], bins=np.arange(0, 1.1, 0.1))
e1_entropy = e1.groupby('entropy_bin', observed=False).agg(
    success_rate=('success', 'mean'), mean_reduction=('reduction', 'mean'), n=('success', 'count')
).reset_index()
results['e1_entropy_binned'] = {
    'success_rates': [float(x) for x in e1_entropy['success_rate'].values],
    'mean_reductions': [float(x) for x in e1_entropy['mean_reduction'].values],
    'counts': [int(x) for x in e1_entropy['n'].values]
}

# ════════════════════════════════════════════
# E3: Scaling Analysis
# ════════════════════════════════════════════

print("\n=== E3 Analysis ===")
e3_n_agg = e3.groupby('n_qubits').agg(
    mean_reduction=('reduction', 'mean'), std_reduction=('reduction', 'std'),
    mean_success=('success', 'mean'), mean_entropy=('normalized_entropy', 'mean'),
    mean_fidelity=('fidelity', 'mean'), n_trials=('success', 'count')
).reset_index()

e3_nd_agg = e3.groupby(['n_qubits', 'depth']).agg(
    success_rate=('success', 'mean'), mean_reduction=('reduction', 'mean'),
    mean_entropy=('normalized_entropy', 'mean'), n_trials=('success', 'count')
).reset_index()

# Power law: reduction(n) = a * n^b + c
n_vals = e3_n_agg['n_qubits'].values
r_vals = e3_n_agg['mean_reduction'].values

def power_law(x, a, b, c):
    return a * x**b + c

popt_pl, pcov_pl = curve_fit(power_law, n_vals, r_vals, p0=[0.05, 0.5, 0.10],
                              bounds=([0, -2, 0], [0.5, 3, 0.5]), maxfev=10000)
a_pl, b_pl, c_pl = popt_pl
perr_pl = np.sqrt(np.diag(pcov_pl))
y_pred_pl = power_law(n_vals, *popt_pl)
r2_pl = 1 - np.sum((r_vals - y_pred_pl)**2) / np.sum((r_vals - np.mean(r_vals))**2)
print(f"  reduction(n) = {a_pl:.4f} * n^{b_pl:.4f} + {c_pl:.4f}, R²={r2_pl:.4f}")

results['e3_reduction_scaling'] = {
    'a': float(a_pl), 'b': float(b_pl), 'c': float(c_pl),
    'a_err': float(perr_pl[0]), 'b_err': float(perr_pl[1]), 'c_err': float(perr_pl[2]),
    'r2': float(r2_pl)
}

# Per-n exponential decay
e3_per_n_fits = {}
for n in sorted(e3_nd_agg['n_qubits'].unique()):
    sub = e3_nd_agg[e3_nd_agg['n_qubits'] == n]
    x = sub['depth'].values
    y = sub['success_rate'].values
    try:
        popt, pcov = curve_fit(exp_decay, x, y, p0=[y.max(), 5, 0.05],
                                bounds=([0, 1, 0], [1, 100, 0.5]), maxfev=10000)
        P0, d0, Pbg = popt
        perr = np.sqrt(np.diag(pcov))
        y_pred = exp_decay(x, *popt)
        r2 = float(1 - np.sum((y - y_pred)**2) / np.sum((y - np.mean(y))**2))
        e3_per_n_fits[int(n)] = {
            'P0': float(P0), 'd0': float(d0), 'P_bg': float(Pbg),
            'P0_err': float(perr[0]), 'd0_err': float(perr[1]), 'P_bg_err': float(perr[2]),
            'r2': r2
        }
    except Exception as e:
        print(f"  n={n}: fit failed - {e}")
results['e3_per_n_exp_decay'] = e3_per_n_fits

# FSS: d_c(n) scaling using decay constant d0
ns_all = np.array([k for k in e3_per_n_fits.keys()])
dcs_all = np.array([v['d0'] for v in e3_per_n_fits.values()])

# Exclude n=10 (anomalous - d0=40.54, very noisy)
valid_mask = ns_all != 10
ns_fit = ns_all[valid_mask]
dcs_fit = dcs_all[valid_mask]

log_n = np.log(ns_fit)
log_dc = np.log(dcs_fit)
slope, intercept, r_value, p_value, std_err = linregress(log_n, log_dc)
b_fss = slope
a_fss = np.exp(intercept)
r2_fss = r_value**2
print(f"  FSS: d_c(n) = {a_fss:.4f} * n^{b_fss:.4f}, R²={r2_fss:.4f}, p={p_value:.4f}")

results['e3_fss'] = {
    'a': float(a_fss), 'b': float(b_fss),
    'b_err': float(std_err),
    'r2': float(r2_fss), 'p_value': float(p_value),
    'n_values': [int(x) for x in ns_fit],
    'dc_values': [float(x) for x in dcs_fit],
    'excluded_n': [10],
    'method': 'decay_constant_log-log'
}

# ════════════════════════════════════════════
# Bootstrap CIs
# ════════════════════════════════════════════

print("\n=== Bootstrap (N=5000) ===")
N_boot = 5000

def bootstrap_mean(data, n_boot=5000):
    means = []
    for _ in range(n_boot):
        sample = np.random.choice(data, size=len(data), replace=True)
        means.append(float(np.mean(sample)))
    ci_low = float(np.percentile(means, 2.5))
    ci_high = float(np.percentile(means, 97.5))
    return float(np.mean(means)), ci_low, ci_high

# E1 bootstrap
e1_sr_mean, e1_sr_lo, e1_sr_hi = bootstrap_mean(e1['success'].values, N_boot)
e1_red_mean, e1_red_lo, e1_red_hi = bootstrap_mean(e1['reduction'].values, N_boot)
print(f"  E1: success={e1_sr_mean:.4f}[{e1_sr_lo:.4f},{e1_sr_hi:.4f}], reduction={e1_red_mean:.4f}[{e1_red_lo:.4f},{e1_red_hi:.4f}]")
results['e1_bootstrap'] = {
    'success_rate': {'mean': e1_sr_mean, 'ci_low': e1_sr_lo, 'ci_high': e1_sr_hi},
    'mean_reduction': {'mean': e1_red_mean, 'ci_low': e1_red_lo, 'ci_high': e1_red_hi}
}

# E3 per-n bootstrap
e3_bootstrap = {}
for n in sorted(e3['n_qubits'].unique()):
    sub = e3[e3['n_qubits'] == n]
    sr_m, sr_lo, sr_hi = bootstrap_mean(sub['success'].values, N_boot)
    red_m, red_lo, red_hi = bootstrap_mean(sub['reduction'].values, N_boot)
    e3_bootstrap[int(n)] = {
        'success_rate': {'mean': sr_m, 'ci_low': sr_lo, 'ci_high': sr_hi},
        'mean_reduction': {'mean': red_m, 'ci_low': red_lo, 'ci_high': red_hi}
    }
    print(f"  n={n}: success={sr_m:.4f}[{sr_lo:.4f},{sr_hi:.4f}], reduction={red_m:.4f}[{red_lo:.4f},{red_hi:.4f}]")
results['e3_bootstrap'] = e3_bootstrap

# ─── Save ───
print("\nSaving...")
with open("data/processed/e1_e3_analysis_results.json", 'w') as f:
    json.dump(results, f, indent=2, cls=NumpyEncoder)
e1_agg.to_csv("data/processed/e1_phase_transition_summary.csv", index=False)
e3_n_agg.to_csv("data/processed/e3_n_scaling_summary.csv", index=False)
e3_nd_agg.to_csv("data/processed/e3_nd_scaling_summary.csv", index=False)

print("✅ Step 2b complete - all results saved!")