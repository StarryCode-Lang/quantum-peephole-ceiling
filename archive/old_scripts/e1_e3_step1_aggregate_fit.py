"""
Step 1: E1+E3 Data Aggregation & Sigmoid Fitting
- Load raw data
- Aggregate by depth (E1) and by (n_qubits, depth) (E3)
- Sigmoid fit: P_success(d) = A / (1 + exp(-(d - d_c) / w))
- Save intermediate results
"""
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import json
import os

os.chdir("D:/Desktop/Q-research")

# ─── Load data ───
print("Loading E1 data...")
e1 = pd.read_csv("data/raw/exp1_phase_transition_20260530_095003.csv")
print(f"E1: {len(e1)} rows, columns={list(e1.columns)}")
print(f"E1 sample:\n{e1.head(2)}")

print("Loading E3 data...")
e3 = pd.read_csv("data/raw/exp3_scaling_20260530_100830.csv")
print(f"E3: {len(e3)} rows, columns={list(e3.columns)}")
print(f"E3 sample:\n{e3.head(2)}")

# ─── E1: Aggregate by depth ───
print("\n=== E1 Aggregation ===")
e1_agg = e1.groupby('depth').agg(
    success_rate=('success', 'mean'),
    mean_reduction=('reduction', 'mean'),
    std_reduction=('reduction', 'std'),
    mean_fidelity=('fidelity', 'mean'),
    std_fidelity=('fidelity', 'std'),
    mean_entropy=('normalized_entropy', 'mean'),
    std_entropy=('normalized_entropy', 'std'),
    n_trials=('success', 'count'),
    n_success=('success', 'sum')
).reset_index()
print(e1_agg.head(10))
print(f"E1 aggregated: {len(e1_agg)} depth values, depth range [{e1_agg.depth.min()}, {e1_agg.depth.max()}]")

# ─── E3: Aggregate by (n_qubits, depth) ───
print("\n=== E3 Aggregation ===")
e3_agg = e3.groupby(['n_qubits', 'depth']).agg(
    success_rate=('success', 'mean'),
    mean_reduction=('reduction', 'mean'),
    std_reduction=('reduction', 'std'),
    mean_fidelity=('fidelity', 'mean'),
    std_fidelity=('fidelity', 'std'),
    mean_entropy=('normalized_entropy', 'mean'),
    std_entropy=('normalized_entropy', 'std'),
    n_trials=('success', 'count'),
    n_success=('success', 'sum')
).reset_index()
print(e3_agg.head(10))
print(f"E3 aggregated: {len(e3_agg)} (n,d) pairs")

# ─── Sigmoid fit function ───
def sigmoid(x, A, d_c, w):
    """P_success(d) = A / (1 + exp(-(d - d_c) / w))"""
    return A / (1.0 + np.exp(-(x - d_c) / w))

# ─── E1 Sigmoid fit ───
print("\n=== E1 Sigmoid Fit ===")
x_e1 = e1_agg['depth'].values
y_e1 = e1_agg['success_rate'].values

# Initial guesses
A_init = y_e1.max()
d_c_init = float(np.median(x_e1[y_e1 > 0.5 * y_e1.max()]))
w_init = 5.0

try:
    popt_e1, pcov_e1 = curve_fit(
        sigmoid, x_e1, y_e1,
        p0=[A_init, d_c_init, w_init],
        bounds=([0, 0, 0.1], [1, 100, 50]),
        maxfev=10000
    )
    A_e1, d_c_e1, w_e1 = popt_e1
    perr_e1 = np.sqrt(np.diag(pcov_e1))
    print(f"E1 sigmoid fit: A={A_e1:.4f}±{perr_e1[0]:.4f}, d_c={d_c_e1:.4f}±{perr_e1[1]:.4f}, w={w_e1:.4f}±{perr_e1[2]:.4f}")
    
    # R²
    y_pred_e1 = sigmoid(x_e1, *popt_e1)
    ss_res = np.sum((y_e1 - y_pred_e1)**2)
    ss_tot = np.sum((y_e1 - np.mean(y_e1))**2)
    r2_e1 = 1 - ss_res / ss_tot
    print(f"R² = {r2_e1:.4f}")
    
    e1_fit = {'A': A_e1, 'd_c': d_c_e1, 'w': w_e1, 
              'A_err': perr_e1[0], 'd_c_err': perr_e1[1], 'w_err': perr_e1[2],
              'r2': r2_e1}
except Exception as e:
    print(f"E1 sigmoid fit failed: {e}")
    e1_fit = None

# ─── E3 Sigmoid fit for each n_qubits ───
print("\n=== E3 Sigmoid Fits per n_qubits ===")
e3_fits = {}
for n in sorted(e3_agg['n_qubits'].unique()):
    sub = e3_agg[e3_agg['n_qubits'] == n]
    x = sub['depth'].values
    y = sub['success_rate'].values
    
    A_init = float(y.max())
    # Find d_c where success_rate crosses half-max
    half_max = 0.5 * y.max()
    d_c_init = float(np.median(x[y > half_max]))
    w_init = 3.0
    
    try:
        popt, pcov = curve_fit(
            sigmoid, x, y,
            p0=[A_init, d_c_init, w_init],
            bounds=([0, 0, 0.1], [1, 100, 50]),
            maxfev=10000
        )
        A, d_c, w = popt
        perr = np.sqrt(np.diag(pcov))
        
        y_pred = sigmoid(x, *popt)
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r2 = 1 - ss_res / ss_tot
        
        e3_fits[int(n)] = {'A': float(A), 'd_c': float(d_c), 'w': float(w),
                           'A_err': float(perr[0]), 'd_c_err': float(perr[1]), 'w_err': float(perr[2]),
                           'r2': float(r2)}
        print(f"  n={n}: A={A:.4f}±{perr[0]:.4f}, d_c={d_c:.2f}±{perr[1]:.2f}, w={w:.2f}±{perr[2]:.2f}, R²={r2:.4f}")
    except Exception as e:
        print(f"  n={n}: fit failed - {e}")

# ─── Save intermediate results ───
print("\nSaving intermediate results...")
e1_agg.to_csv("data/processed/e1_phase_transition_summary.csv", index=False)
e3_agg.to_csv("data/processed/e3_scaling_summary.csv", index=False)

results = {
    'e1_sigmoid_fit': e1_fit,
    'e3_sigmoid_fits': e3_fits,
    'e1_stats': {
        'total_trials': int(e1_agg['n_trials'].sum()),
        'depth_range': [int(e1_agg.depth.min()), int(e1_agg.depth.max())],
        'success_rate_range': [float(e1_agg.success_rate.min()), float(e1_agg.success_rate.max())],
        'mean_reduction': float(e1_agg.mean_reduction.mean()),
        'mean_fidelity': float(e1_agg.mean_fidelity.mean())
    },
    'e3_stats': {
        'total_trials': int(e3_agg['n_trials'].sum()),
        'n_qubits_range': [int(e3_agg.n_qubits.min()), int(e3_agg.n_qubits.max())],
        'depth_range': [int(e3_agg.depth.min()), int(e3_agg.depth.max())],
        'success_rate_range': [float(e3_agg.success_rate.min()), float(e3_agg.success_rate.max())],
        'mean_reduction': float(e3_agg.mean_reduction.mean()),
        'mean_fidelity': float(e3_agg.mean_fidelity.mean())
    }
}

with open("data/processed/e1_e3_step1_results.json", 'w') as f:
    json.dump(results, f, indent=2)

print("\n✅ Step 1 complete!")
print(f"  e1_phase_transition_summary.csv: {len(e1_agg)} rows")
print(f"  e3_scaling_summary.csv: {len(e3_agg)} rows")
print(f"  e1_e3_step1_results.json: saved")