"""E3 Bootstrap CI for power law reduction(n) = a * n^b"""
import os
os.chdir("D:/Desktop/Q-research")
import sys
sys.path.insert(0, 'src')

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import json

# Load E3 data
e3 = pd.read_csv('data/raw/exp3_scaling_20260530_100830.csv')
print(f"E3 data: {len(e3)} rows")

# Aggregate by n_qubits
agg = e3.groupby('n_qubits')['reduction'].agg(['mean', 'count', 'std']).reset_index()
agg.columns = ['n_qubits', 'mean_reduction', 'n_trials', 'std_reduction']
print(agg)

n_vals = agg['n_qubits'].values.astype(float)
r_vals = agg['mean_reduction'].values.astype(float)
nt_vals = agg['n_trials'].values.astype(float)
std_vals = agg['std_reduction'].values.astype(float)

# Power law fit
def power_law(n, a, b):
    return a * n**b

popt, pcov = curve_fit(power_law, n_vals, r_vals, p0=[0.08, 0.3])
a_fit, b_fit = popt
perr = np.sqrt(np.diag(pcov))

r_pred = power_law(n_vals, a_fit, b_fit)
ss_res = np.sum((r_vals - r_pred)**2)
ss_tot = np.sum((r_vals - np.mean(r_vals))**2)
r2 = 1 - ss_res / ss_tot

print(f"\nPower law fit: reduction(n) = {a_fit:.4f} * n^{b_fit:.4f}")
print(f"  R² = {r2:.4f}")
print(f"  a_err = {perr[0]:.4f}, b_err = {perr[1]:.4f}")

# Bootstrap CI (resample per n_qubits group)
N_BOOTSTRAP = 5000
np.random.seed(42)

a_samples = []
b_samples = []

for _ in range(N_BOOTSTRAP):
    # Resample reduction values per n_qubits
    boot_means = []
    for n, nt, mean_r, std_r in zip(n_vals, nt_vals, r_vals, std_vals):
        # Resample from normal distribution around mean
        boot_mean = np.random.normal(mean_r, std_r / np.sqrt(nt))
        boot_means.append(boot_mean)
    boot_means = np.array(boot_means)
    
    try:
        popt_b, _ = curve_fit(power_law, n_vals, boot_means, p0=[a_fit, b_fit])
        a_samples.append(popt_b[0])
        b_samples.append(popt_b[1])
    except:
        pass

a_samples = np.array(a_samples)
b_samples = np.array(b_samples)

a_ci = np.percentile(a_samples, [2.5, 97.5])
b_ci = np.percentile(b_samples, [2.5, 97.5])

print(f"\nBootstrap CI ({len(a_samples)} successful fits):")
print(f"  a = {np.mean(a_samples):.4f} [{a_ci[0]:.4f}, {a_ci[1]:.4f}]")
print(f"  b = {np.mean(b_samples):.4f} [{b_ci[0]:.4f}, {b_ci[1]:.4f}]")

# Save results
results = {
    'power_law_fit': {
        'a': float(a_fit), 'b': float(b_fit),
        'a_err': float(perr[0]), 'b_err': float(perr[1]),
        'R2': float(r2),
        'bootstrap_CI': {
            'N_BOOTSTRAP': N_BOOTSTRAP,
            'n_successful': len(a_samples),
            'a_mean': float(np.mean(a_samples)),
            'a_ci_lower': float(a_ci[0]),
            'a_ci_upper': float(a_ci[1]),
            'b_mean': float(np.mean(b_samples)),
            'b_ci_lower': float(b_ci[0]),
            'b_ci_upper': float(b_ci[1]),
        }
    },
    'n_qubits_values': [int(x) for x in n_vals],
    'mean_reduction_values': [float(x) for x in r_vals],
}

# Update existing e1_e3_analysis_results.json
with open('data/processed/e1_e3_analysis_results.json', 'r') as f:
    existing = json.load(f)

# Add/update E3_bootstrap section
existing['E3_bootstrap_power_law'] = results

with open('data/processed/e1_e3_analysis_results.json', 'w') as f:
    json.dump(existing, f, indent=2, ensure_ascii=False)

print(f"\n✅ Updated e1_e3_analysis_results.json with E3 Bootstrap CI")