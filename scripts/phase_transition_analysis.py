"""
Phase Transition Analysis (E1+E3) - Optimized version
"""

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Science-style matplotlib settings ──
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Computer Modern Roman', 'DejaVu Serif'],
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'legend.fontsize': 10,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.linewidth': 0.8,
    'grid.linewidth': 0.4,
    'lines.linewidth': 1.5,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'mathtext.fontset': 'cm',
})

# ── Paths ──
BASE = Path("D:/Desktop/Q-research")
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
FIGS = BASE / "figures" / "final"

PROC.mkdir(parents=True, exist_ok=True)
FIGS.mkdir(parents=True, exist_ok=True)

# ── Load data ──
e1 = pd.read_csv(RAW / "exp1_phase_transition_20260530_095003.csv")
e3 = pd.read_csv(RAW / "exp3_scaling_20260530_100830.csv")

print(f"E1: {len(e1)} rows, n_qubits={sorted(e1['n_qubits'].unique())}")
print(f"E3: {len(e3)} rows, n_qubits={sorted(e3['n_qubits'].unique())}")

# ── Aggregate ──
def aggregate(df):
    agg = df.groupby(['n_qubits', 'depth'])['success'].agg(['mean', 'count', 'std']).reset_index()
    agg.columns = ['n_qubits', 'depth', 'success_rate', 'n_trials', 'std_success']
    agg['se_success'] = agg['std_success'] / np.sqrt(agg['n_trials'])
    agg['se_success'] = agg['se_success'].fillna(0.05)
    agg.loc[agg['se_success'] == 0, 'se_success'] = 0.05
    return agg

e1_agg = aggregate(e1)
e3_agg = aggregate(e3)
combined_agg = pd.concat([e1_agg, e3_agg], ignore_index=True)
all_n_qubits = sorted(combined_agg['n_qubits'].unique())

print(f"\nCombined n_qubits: {all_n_qubits}")
for n in all_n_qubits:
    sub = combined_agg[combined_agg['n_qubits'] == n]
    print(f"  n={n}: depths {sub['depth'].min()}-{sub['depth'].max()}, {len(sub)} points")

# ── Sigmoid model ──
def sigmoid(d, dc, beta):
    return 1.0 / (1.0 + np.exp(-beta * (d - dc)))

# ── Fit sigmoid for each n_qubits ──
sigmoid_results = {}

for n in all_n_qubits:
    sub = combined_agg[combined_agg['n_qubits'] == n].sort_values('depth')
    d = sub['depth'].values.astype(float)
    p = sub['success_rate'].values.astype(float)
    nt = sub['n_trials'].values.astype(float)
    
    dc_guess = d[np.argmin(np.abs(p - 0.5))]
    beta_guess = 0.5
    
    try:
        popt, pcov = curve_fit(sigmoid, d, p, p0=[dc_guess, beta_guess],
                               bounds=([0, 0.01], [max(d)*2, 10]), maxfev=10000)
        dc_fit, beta_fit = popt
        perr = np.sqrt(np.diag(pcov))
        
        p_pred = sigmoid(d, dc_fit, beta_fit)
        ss_res = np.sum((p - p_pred)**2)
        ss_tot = np.sum((p - np.mean(p))**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        
        sigmoid_results[n] = {
            'dc': dc_fit, 'beta': beta_fit, 'r2': r2,
            'dc_se': perr[0], 'beta_se': perr[1],
            'depths': d, 'success_rates': p, 'n_trials': nt,
            'pred': p_pred, 'n_data_points': len(d),
        }
        print(f"  n={n}: dc={dc_fit:.3f}±{perr[0]:.3f}, beta={beta_fit:.4f}±{perr[1]:.4f}, R²={r2:.4f}")
    except Exception as e:
        print(f"  n={n}: FIT FAILED - {e}")
        sigmoid_results[n] = None

# ── Bootstrap (optimized - use numpy vectorized approach) ──
N_BOOTSTRAP = 10000
np.random.seed(42)  # reproducibility

print(f"\nRunning bootstrap ({N_BOOTSTRAP} resamples)...")

bootstrap_results = {}

for n in all_n_qubits:
    res = sigmoid_results[n]
    if res is None:
        bootstrap_results[n] = {'dc_mean': 0, 'dc_ci_lower': 0, 'dc_ci_upper': 0,
                                'beta_mean': 0, 'beta_ci_lower': 0, 'beta_ci_upper': 0,
                                'dc_std': 0, 'beta_std': 0, 'n_successful_fits': 0}
        continue
    
    d_vals = res['depths']
    p_vals = res['success_rates']
    nt_vals = res['n_trials']
    
    # Generate all bootstrap samples at once
    # For each depth, resample from binomial(n_trials, p)
    p_clipped = np.clip(p_vals, 1e-6, 1-1e-6)
    # Vectorized: generate N_BOOTSTRAP x len(d_vals) binomial samples
    boot_success = np.random.binomial(nt_vals.astype(int)[np.newaxis, :],
                                       p_clipped[np.newaxis, :],
                                       size=(N_BOOTSTRAP, len(d_vals)))
    boot_rates = boot_success / nt_vals[np.newaxis, :]
    
    dc_samples = []
    beta_samples = []
    
    # Fit each bootstrap sample
    dc_ref = res['dc']
    beta_ref = res['beta']
    
    for j in range(N_BOOTSTRAP):
        try:
            popt, _ = curve_fit(sigmoid, d_vals, boot_rates[j], 
                                p0=[dc_ref, beta_ref],
                                bounds=([0, 0.01], [max(d_vals)*2, 10]),
                                maxfev=3000)
            dc_samples.append(popt[0])
            beta_samples.append(popt[1])
        except:
            pass
    
    dc_samples = np.array(dc_samples)
    beta_samples = np.array(beta_samples)
    
    dc_ci = np.percentile(dc_samples, [2.5, 97.5])
    beta_ci = np.percentile(beta_samples, [2.5, 97.5])
    
    bootstrap_results[n] = {
        'dc_mean': np.mean(dc_samples), 'dc_ci_lower': dc_ci[0], 'dc_ci_upper': dc_ci[1],
        'beta_mean': np.mean(beta_samples), 'beta_ci_lower': beta_ci[0], 'beta_ci_upper': beta_ci[1],
        'dc_std': np.std(dc_samples), 'beta_std': np.std(beta_samples),
        'n_successful_fits': len(dc_samples),
    }
    
    print(f"  n={n}: dc={np.mean(dc_samples):.3f} [{dc_ci[0]:.3f}, {dc_ci[1]:.3f}], "
          f"beta={np.mean(beta_samples):.4f} [{beta_ci[0]:.4f}, {beta_ci[1]:.4f}] "
          f"(N={len(dc_samples)} successful)")

# ── Finite-size scaling ──
def power_law(n, a, b):
    return a * n**b

fss_data = [(n, sigmoid_results[n]['dc']) for n in all_n_qubits if sigmoid_results[n] is not None]
n_arr = np.array([x[0] for x in fss_data], dtype=float)
dc_arr = np.array([x[1] for x in fss_data], dtype=float)

print(f"\nFSS data: {len(fss_data)} points")
for n_val, dc_val in fss_data:
    print(f"  n={n_val}, dc={dc_val:.3f}")

fss_fit = None
if len(fss_data) >= 2:
    try:
        popt_fss, pcov_fss = curve_fit(power_law, n_arr, dc_arr, p0=[1.0, 1.0],
                                        bounds=([0.01, 0.01], [100, 10]), maxfev=10000)
        a_fss, b_fss = popt_fss
        perr_fss = np.sqrt(np.diag(pcov_fss))
        
        dc_pred_fss = power_law(n_arr, a_fss, b_fss)
        ss_res_fss = np.sum((dc_arr - dc_pred_fss)**2)
        ss_tot_fss = np.sum((dc_arr - np.mean(dc_arr))**2)
        r2_fss = 1 - ss_res_fss / ss_tot_fss if ss_tot_fss > 0 else 0.0
        
        print(f"\n  dc = {a_fss:.4f} * n^{b_fss:.4f}, R²={r2_fss:.4f}")
        
        # FSS bootstrap
        a_boot_samples = []
        b_boot_samples = []
        
        for _ in range(N_BOOTSTRAP):
            dc_boot = []
            n_boot = []
            for n_val in all_n_qubits:
                if n_val in bootstrap_results and sigmoid_results[n_val] is not None:
                    br = bootstrap_results[n_val]
                    dc_s = np.random.normal(br['dc_mean'], br['dc_std'])
                    dc_boot.append(dc_s)
                    n_boot.append(n_val)
            
            if len(dc_boot) >= 2:
                dc_b = np.array(dc_boot, dtype=float)
                n_b = np.array(n_boot, dtype=float)
                try:
                    popt_b, _ = curve_fit(power_law, n_b, dc_b, p0=[a_fss, b_fss],
                                         bounds=([0.01, 0.01], [100, 10]), maxfev=3000)
                    a_boot_samples.append(popt_b[0])
                    b_boot_samples.append(popt_b[1])
                except:
                    pass
        
        a_boot = np.array(a_boot_samples)
        b_boot = np.array(b_boot_samples)
        a_fss_ci = np.percentile(a_boot, [2.5, 97.5])
        b_fss_ci = np.percentile(b_boot, [2.5, 97.5])
        
        print(f"  FSS Bootstrap: a={np.mean(a_boot):.4f} [{a_fss_ci[0]:.4f}, {a_fss_ci[1]:.4f}], "
              f"b={np.mean(b_boot):.4f} [{b_fss_ci[0]:.4f}, {b_fss_ci[1]:.4f}]")
        
        fss_fit = {'a': a_fss, 'b': b_fss, 'r2': r2_fss,
                   'a_se': perr_fss[0], 'b_se': perr_fss[1],
                   'a_ci': a_fss_ci, 'b_ci': b_fss_ci,
                   'a_boot_mean': np.mean(a_boot), 'b_boot_mean': np.mean(b_boot)}
    except Exception as e:
        print(f"  FSS fit FAILED: {e}")

# ════════════════════════════════════════════════════════
# FIGURE 1: Phase Transition Sigmoid Fits
# ════════════════════════════════════════════════════════
ncols = min(4, len(all_n_qubits))
nrows = (len(all_n_qubits) + ncols - 1) // ncols

fig1, axes1 = plt.subplots(nrows, ncols, figsize=(4*ncols, 3.5*nrows))
if nrows == 1:
    axes1 = [axes1] if ncols == 1 else axes1
else:
    axes1 = axes1.flatten()

colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(all_n_qubits)))

for i, n in enumerate(all_n_qubits):
    ax = axes1[i] if len(all_n_qubits) > 1 else axes1[0]
    res = sigmoid_results[n]
    
    if res is None:
        ax.text(0.5, 0.5, f'n={n}\nFit Failed', transform=ax.transAxes, ha='center', va='center')
        ax.set_title(f'n = {n} qubits')
        continue
    
    d = res['depths']
    p = res['success_rates']
    
    ax.scatter(d, p, color=colors[i], s=20, zorder=3, alpha=0.8, label='Data')
    
    d_smooth = np.linspace(min(d), max(d), 200)
    p_smooth = sigmoid(d_smooth, res['dc'], res['beta'])
    ax.plot(d_smooth, p_smooth, color=colors[i], linewidth=2,
            label=f'Fit (R²={res["r2"]:.3f})')
    
    br = bootstrap_results[n]
    ax.axvline(res['dc'], color='red', linestyle='--', alpha=0.7, linewidth=1)
    ax.axvspan(br['dc_ci_lower'], br['dc_ci_upper'], alpha=0.15, color='red')
    
    ax.set_xlabel('Circuit Depth $d$')
    ax.set_ylabel('$P_{\\mathrm{success}}$')
    ax.set_title(f'$n = {n}$ qubits')
    ax.set_ylim(-0.05, 1.05)
    ax.annotate(f'$d_c = {res["dc"]:.1f}$\n$\\beta = {res["beta"]:.3f}$',
                xy=(0.02, 0.98), xycoords='axes fraction', fontsize=9, va='top', ha='left',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='wheat', alpha=0.5))

for j in range(len(all_n_qubits), len(axes1)):
    axes1[j].set_visible(False)

fig1.suptitle('Phase Transition: Sigmoid Fits for Each System Size', fontsize=14, y=1.02)
fig1.tight_layout()
fig1.savefig(FIGS / "fig1_phase_transition.png")
print(f"\nSaved fig1_phase_transition.png")

# ════════════════════════════════════════════════════════
# FIGURE 2: Finite-Size Scaling
# ════════════════════════════════════════════════════════
fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(12, 5))

if fss_fit is not None:
    a_fss = fss_fit['a']
    b_fss = fss_fit['b']
    r2_fss = fss_fit['r2']
    a_fss_ci = fss_fit['a_ci']
    b_fss_ci = fss_fit['b_ci']
    
    for i, n in enumerate(all_n_qubits):
        if sigmoid_results[n] is not None:
            br = bootstrap_results[n]
            err_lo = sigmoid_results[n]['dc'] - br['dc_ci_lower']
            err_hi = br['dc_ci_upper'] - sigmoid_results[n]['dc']
            ax2a.errorbar(n, sigmoid_results[n]['dc'], yerr=[[err_lo], [err_hi]],
                         fmt='o', color=colors[i], markersize=8, capsize=4, label=f'$n={n}$')
    
    n_smooth = np.linspace(min(n_arr)*0.8, max(n_arr)*1.2, 200)
    dc_smooth = power_law(n_smooth, a_fss, b_fss)
    ax2a.plot(n_smooth, dc_smooth, 'r-', linewidth=2,
             label=f'$d_c = {a_fss:.2f} \\cdot n^{{{b_fss:.2f}}}$ (R²={r2_fss:.3f})')
    
    ax2a.set_xlabel('Number of Qubits $n$')
    ax2a.set_ylabel('Critical Depth $d_c$')
    ax2a.set_title('Finite-Size Scaling: $d_c$ vs $n$')
    ax2a.legend(loc='upper left', fontsize=9)
    
    # Log-log
    ax2b.loglog(n_arr, dc_arr, 'ko', markersize=8, label='Data')
    n_smooth_log = np.logspace(np.log10(min(n_arr)*0.8), np.log10(max(n_arr)*1.2), 200)
    dc_smooth_log = power_law(n_smooth_log, a_fss, b_fss)
    ax2b.loglog(n_smooth_log, dc_smooth_log, 'r-', linewidth=2,
               label=f'$d_c = {a_fss:.2f} \\cdot n^{{{b_fss:.2f}}}$')
    
    dc_lower = power_law(n_smooth_log, a_fss_ci[0], b_fss_ci[0])
    dc_upper = power_law(n_smooth_log, a_fss_ci[1], b_fss_ci[1])
    ax2b.fill_between(n_smooth_log, dc_lower, dc_upper, alpha=0.2, color='red',
                     label='95% CI (bootstrap)')
    
    ax2b.set_xlabel('Number of Qubits $n$')
    ax2b.set_ylabel('Critical Depth $d_c$')
    ax2b.set_title('Log-Log: Finite-Size Scaling')
    ax2b.legend(loc='upper left', fontsize=9)
    
    ax2b.annotate(f'Scaling exponent $b = {b_fss:.3f}$\n95% CI: [{b_fss_ci[0]:.3f}, {b_fss_ci[1]:.3f}]',
                 xy=(0.02, 0.98), xycoords='axes fraction', fontsize=10, va='top', ha='left',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8))

fig2.suptitle('Finite-Size Scaling Analysis', fontsize=14, y=1.02)
fig2.tight_layout()
fig2.savefig(FIGS / "fig2_fss.png")
print(f"Saved fig2_fss.png")

# ════════════════════════════════════════════════════════
# Save results
# ════════════════════════════════════════════════════════
sig_df_data = []
for n in all_n_qubits:
    res = sigmoid_results[n]
    br = bootstrap_results[n]
    if res is not None:
        sig_df_data.append({
            'n_qubits': n, 'dc': res['dc'], 'dc_se': res['dc_se'],
            'beta': res['beta'], 'beta_se': res['beta_se'], 'r2': res['r2'],
            'n_data_points': res['n_data_points'],
            'dc_bootstrap_mean': br['dc_mean'], 'dc_ci_lower': br['dc_ci_lower'],
            'dc_ci_upper': br['dc_ci_upper'], 'dc_bootstrap_std': br['dc_std'],
            'beta_bootstrap_mean': br['beta_mean'], 'beta_ci_lower': br['beta_ci_lower'],
            'beta_ci_upper': br['beta_ci_upper'], 'beta_bootstrap_std': br['beta_std'],
            'n_bootstrap_successful': br['n_successful_fits'],
        })

sig_df = pd.DataFrame(sig_df_data)
sig_df.to_csv(PROC / "sigmoid_fit_results.csv", index=False)
print(f"\nSaved sigmoid_fit_results.csv")

if fss_fit is not None:
    fss_df = pd.DataFrame([{
        'a': fss_fit['a'], 'a_se': fss_fit['a_se'],
        'b': fss_fit['b'], 'b_se': fss_fit['b_se'],
        'r2': fss_fit['r2'],
        'a_ci_lower': fss_fit['a_ci'][0], 'a_ci_upper': fss_fit['a_ci'][1],
        'b_ci_lower': fss_fit['b_ci'][0], 'b_ci_upper': fss_fit['b_ci'][1],
        'a_bootstrap_mean': fss_fit['a_boot_mean'], 'b_bootstrap_mean': fss_fit['b_boot_mean'],
    }])
    fss_df.to_csv(PROC / "fss_results.csv", index=False)
    print(f"Saved fss_results.csv")

combined_agg.to_csv(PROC / "combined_aggregated_data.csv", index=False)
print(f"Saved combined_aggregated_data.csv")

# ── Summary ──
print("\n" + "="*60)
print("PHASE TRANSITION ANALYSIS SUMMARY")
print("="*60)
print(f"Data: E1 ({len(e1)} trials) + E3 ({len(e3)} trials)")
print(f"System sizes: {all_n_qubits}")
print(f"Bootstrap: {N_BOOTSTRAP} resamples")

print("\n--- Sigmoid Fit Results ---")
for n in all_n_qubits:
    res = sigmoid_results[n]
    br = bootstrap_results[n]
    if res:
        print(f"  n={n}: dc={res['dc']:.3f} [{br['dc_ci_lower']:.3f}, {br['dc_ci_upper']:.3f}], "
              f"beta={res['beta']:.4f} [{br['beta_ci_lower']:.4f}, {br['beta_ci_upper']:.4f}], "
              f"R²={res['r2']:.4f}")

if fss_fit:
    print("\n--- Finite-Size Scaling ---")
    print(f"  dc = {fss_fit['a']:.4f} * n^{fss_fit['b']:.4f}")
    print(f"  b = {fss_fit['b']:.4f} [{fss_fit['b_ci'][0]:.4f}, {fss_fit['b_ci'][1]:.4f}]")
    print(f"  R² = {fss_fit['r2']:.4f}")

print(f"\n--- Output Files ---")
for f in PROC.iterdir():
    print(f"  {f}")
for f in FIGS.iterdir():
    if f.suffix == '.png':
        print(f"  {f}")
print("="*60)