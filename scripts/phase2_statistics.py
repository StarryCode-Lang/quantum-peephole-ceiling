"""Phase 2B: Statistical Re-analysis — phase transition, model comparison, power analysis."""
import sys, os, json, numpy as np, pandas as pd
from datetime import datetime
from scipy import stats as sp_stats, optimize

sys.path.insert(0, "D:/Desktop/Q-research")
os.makedirs("data/processed", exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# =========================================================================
# Load all available Phase 0 data (use most recent files)
# =========================================================================
import glob

def get_latest_csv(pattern):
    files = sorted(glob.glob(f"data/raw/{pattern}*.csv"))
    return files[-1] if files else None

print("Loading data files...")
e1_path = get_latest_csv("exp1_phase_transition")
e3_path = get_latest_csv("exp3_scaling")
e4_path = get_latest_csv("exp4_algorithm_comparison")
e2_path = get_latest_csv("exp2_entanglement_density")

all_found = all([e1_path, e3_path, e4_path, e2_path])
print(f"  E1: {e1_path}")
print(f"  E2: {e2_path}")
print(f"  E3: {e3_path}")
print(f"  E4: {e4_path}")

if not all_found:
    print("ERROR: Not all data files found. Run Phase 0 first.")
    sys.exit(1)

e1 = pd.read_csv(e1_path)
if 'optimizer' not in e1.columns:
    e1['optimizer'] = 'greedy'  # Old data only used one optimizer
e3 = pd.read_csv(e3_path)
if 'optimizer' not in e3.columns:
    e3['optimizer'] = 'greedy'
e4 = pd.read_csv(e4_path)
e4['optimizer'] = e4['optimizer'].str.lower()  # Normalize: GREEDY -> greedy
e2 = pd.read_csv(e2_path)
e2['optimizer'] = e2['optimizer'].str.lower()
print(f"Loaded: E1={len(e1)}, E2={len(e2)}, E3={len(e3)}, E4={len(e4)}")

# =========================================================================
# Analysis 1: Phase Transition Re-test
# =========================================================================
print("\n" + "=" * 70)
print("ANALYSIS 1: Phase Transition — Exponential vs Sigmoid Model")
print("=" * 70)

results_by_n = {}
for n_q in [3, 5, 7]:
    sub = e1[(e1['n_qubits'] == n_q) & (e1['optimizer'] == 'greedy')]
    depths = sorted(sub['depth'].unique())
    success_rates = [sub[sub['depth'] == d]['reduction'].apply(lambda r: float(r >= 0.05)).mean() for d in depths]
    
    # Fit exponential: P(d) = P0 * exp(-d/d0)
    def exp_model(d, P0, d0):
        return P0 * np.exp(-d / d0)
    
    try:
        popt_exp, pcov_exp = optimize.curve_fit(exp_model, depths, success_rates,
                                                  p0=[0.5, 10.0], maxfev=5000)
        residuals_exp = success_rates - exp_model(np.array(depths), *popt_exp)
        ss_res_exp = np.sum(residuals_exp**2)
        ss_tot = np.sum((success_rates - np.mean(success_rates))**2)
        r2_exp = 1 - ss_res_exp / ss_tot if ss_tot > 0 else 0
    except Exception as e:
        popt_exp = [np.nan, np.nan]
        ss_res_exp = np.nan
        ss_tot = np.nan
        r2_exp = np.nan
    
    # Fit sigmoid: P(d) = 1 / (1 + exp((d - dc) / w))
    def sigmoid_model(d, dc, w):
        return 1 / (1 + np.exp((d - dc) / w))
    
    try:
        popt_sig, pcov_sig = optimize.curve_fit(sigmoid_model, depths, success_rates,
                                                 p0=[15.0, 5.0], maxfev=5000,
                                                 bounds=([0, 0.1], [100, 50]))
        residuals_sig = success_rates - sigmoid_model(np.array(depths), *popt_sig)
        ss_res_sig = np.sum(residuals_sig**2)
        r2_sig = 1 - ss_res_sig / ss_tot if (ss_tot and ss_tot > 0) else 0
    except Exception as e:
        popt_sig = [np.nan, np.nan]
        ss_res_sig = np.nan
        r2_sig = np.nan
    
    # AIC/BIC comparison
    k_exp, k_sig = 2, 2
    n_pts = len(depths)
    if n_pts == 0 or not np.isfinite(ss_res_exp) or ss_res_exp == 0:
        log_lik_exp = -np.inf
    else:
        log_lik_exp = -n_pts/2 * np.log(ss_res_exp / n_pts + 1e-10)
    if n_pts == 0 or not np.isfinite(ss_res_sig) or ss_res_sig == 0:
        log_lik_sig = -np.inf
    else:
        log_lik_sig = -n_pts/2 * np.log(ss_res_sig / n_pts + 1e-10)
    aic_exp = 2*k_exp - 2*log_lik_exp
    aic_sig = 2*k_sig - 2*log_lik_sig
    bic_exp = k_exp * np.log(n_pts) - 2*log_lik_exp if n_pts > 0 else np.inf
    bic_sig = k_sig * np.log(n_pts) - 2*log_lik_sig if n_pts > 0 else np.inf
    
    results_by_n[n_q] = {
        'exponential': {'P0': float(popt_exp[0]), 'd0': float(popt_exp[1]), 'r2': float(r2_exp),
                        'aic': float(aic_exp), 'bic': float(bic_exp)},
        'sigmoid': {'dc': float(popt_sig[0]), 'w': float(popt_sig[1]), 'r2': float(r2_sig),
                    'aic': float(aic_sig), 'bic': float(bic_sig)},
        'delta_aic': float(aic_exp - aic_sig),
        'delta_bic': float(bic_exp - bic_sig),
        'favors_model': 'exponential' if aic_exp < aic_sig else 'sigmoid',
        'success_rates': {int(d): float(s) for d, s in zip(depths, success_rates)},
    }
    
    print(f"\n  n={n_q}:")
    print(f"    Exponential: P0={popt_exp[0]:.3f}, d0={popt_exp[1]:.1f}, R²={r2_exp:.3f}")
    print(f"    Sigmoid: dc={popt_sig[0]:.1f}, w={popt_sig[1]:.1f}, R²={r2_sig:.3f}")
    print(f"    ΔAIC = {aic_exp - aic_sig:+.1f} → favors {results_by_n[n_q]['favors_model']}")
    print(f"    ΔBIC = {bic_exp - bic_sig:+.1f}")

# =========================================================================
# Analysis 2: FSS — d0 does NOT scale with n
# =========================================================================
print("\n" + "=" * 70)
print("ANALYSIS 2: Finite-Size Scaling of d0")
print("=" * 70)

d0_values = {n: results_by_n[n]['exponential']['d0'] for n in [3, 5, 7]}
n_values = np.array(list(d0_values.keys()), dtype=float)
d0_arr = np.array(list(d0_values.values()), dtype=float)

slope, intercept, r_val, p_val, std_err = sp_stats.linregress(n_values, d0_arr)
print(f"  d0 vs n: slope={slope:.2f}, R²={r_val**2:.3f}, p={p_val:.3f}")
print(f"  Conclusion: d0 {'DOES' if slope > 0.1 else 'does NOT'} scale with n")

# =========================================================================
# Analysis 3: SA/GA vs Greedy — Wilcoxon + Effect Size
# =========================================================================
print("\n" + "=" * 70)
print("ANALYSIS 3: Algorithm Comparison (SA/GA vs Greedy)")
print("=" * 70)

greedy_red = e4[e4['optimizer'] == 'greedy']['reduction'].values
sa_red = e4[e4['optimizer'] == 'simulated_annealing']['reduction'].values
ga_red = e4[e4['optimizer'] == 'genetic_algorithm']['reduction'].values
rls_red = e4[e4['optimizer'] == 'random_local_search']['reduction'].values

print(f"\n  {'Optimizer':<10}  {'Mean':>8}  {'Median':>8}  {'Std':>7}  {'Succ 5%':>8}")
print("  " + "-" * 50)
for name, arr in [('Greedy', greedy_red), ('SA', sa_red), ('GA', ga_red), ('RLS', rls_red)]:
    print(f"  {name:<10}  {arr.mean():>7.2%}  {np.median(arr):>7.2%}  {arr.std():>6.2%}  {(arr>=0.05).mean():>7.1%}")

# Wilcoxon: Greedy vs SA
stat_sa, p_sa = sp_stats.mannwhitneyu(greedy_red, sa_red, alternative='greater')
stat_ga, p_ga = sp_stats.mannwhitneyu(greedy_red, ga_red, alternative='greater')
stat_rls, p_rls = sp_stats.mannwhitneyu(greedy_red, rls_red, alternative='greater')

# Cliff's delta effect size
def cliffs_delta(x, y):
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return 0.0
    sum_gt = sum(xi > yi for xi in x for yi in y)
    sum_lt = sum(xi < yi for xi in x for yi in y)
    return (sum_gt - sum_lt) / (n1 * n2)

cd_sa = cliffs_delta(greedy_red, sa_red)
cd_ga = cliffs_delta(greedy_red, ga_red)
cd_rls = cliffs_delta(greedy_red, rls_red)

print(f"\n  Mann-Whitney (Greedy vs SA): U={int(stat_sa)}, p={p_sa:.2e}")
print(f"  Mann-Whitney (Greedy vs GA): U={int(stat_ga)}, p={p_ga:.2e}")
print(f"  Mann-Whitney (Greedy vs RLS): U={int(stat_rls)}, p={p_rls:.2e}")
print(f"  Cliff's delta (Greedy vs SA): {cd_sa:+.3f} ({'negligible' if abs(cd_sa)<0.147 else 'small' if abs(cd_sa)<0.33 else 'medium' if abs(cd_sa)<0.474 else 'large'})")
print(f"  Cliff's delta (Greedy vs GA): {cd_ga:+.3f}")

# =========================================================================
# Analysis 4: Power-law for gate reduction scaling (E3)
# =========================================================================
print("\n" + "=" * 70)
print("ANALYSIS 4: Power-Law Scaling (E3)")
print("=" * 70)

mean_by_n = e3.groupby('n_qubits')['reduction'].agg(['mean', 'std', 'count']).reset_index()
log_n = np.log(mean_by_n['n_qubits'].values.astype(float))
log_red = np.log(mean_by_n['mean'].values.astype(float))
slope_pl, intercept_pl, r_val_pl, p_val_pl, std_err_pl = sp_stats.linregress(log_n, log_red)

print(f"  Power law: reduction ∝ n^{slope_pl:.3f}")
print(f"  95% CI: [{slope_pl - 1.96*std_err_pl:.3f}, {slope_pl + 1.96*std_err_pl:.3f}]")
print(f"  R²={r_val_pl**2:.3f}, p={p_val_pl:.4f}")
print(f"  Table: n={mean_by_n['n_qubits'].values}, reduction={mean_by_n['mean'].values}")

# =========================================================================
# Analysis 5: Entanglement sweet spot (E2)
# =========================================================================
print("\n" + "=" * 70)
print("ANALYSIS 5: Entanglement Density Sweet Spot (E2)")
print("=" * 70)

by_rho = e2.groupby('entanglement_density')['reduction'].agg(['mean', 'std', 'count']).reset_index()
best_rho = by_rho.loc[by_rho['mean'].idxmax(), 'entanglement_density']
second_best = by_rho.nlargest(2, 'mean').iloc[-1]['entanglement_density']
print(f"  Optimal ρ: {best_rho:.1f} (reduction={by_rho[by_rho['entanglement_density']==best_rho]['mean'].values[0]:.2%})")
print(f"  2nd best: ρ={second_best:.1f}")
print(f"  Reduction by ρ:")
for _, row in by_rho.iterrows():
    print(f"    ρ={row['entanglement_density']:.1f}: {row['mean']:.2%} ± {row['std']:.2%} (n={int(row['count'])})")

# Bootstrap CI for best rho
np.random.seed(42)
bootstrapped_best = []
for _ in range(1000):
    sample = e2.sample(n=len(e2), replace=True)
    boot_best = sample.groupby('entanglement_density')['reduction'].mean().idxmax()
    bootstrapped_best.append(boot_best)
ci_low = np.percentile(bootstrapped_best, 2.5)
ci_high = np.percentile(bootstrapped_best, 97.5)
print(f"  95% Bootstrap CI for optimal ρ: [{ci_low:.2f}, {ci_high:.2f}]")

# =========================================================================
# Save consolidated analysis
# =========================================================================
summary = {
    'version': 'phase0_v1', 'timestamp': TIMESTAMP,
    'fss': {'slope': float(slope), 'intercept': float(intercept),
            'r_squared': float(r_val**2), 'p_value': float(p_val)},
    'power_law': {'exponent': float(slope_pl), 'intercept': float(intercept_pl),
                  'r_squared': float(r_val_pl**2), 'p_value': float(p_val_pl)},
    'algorithm_comparison': {
        'greedy_mean': float(greedy_red.mean()), 'greedy_median': float(np.median(greedy_red)),
        'sa_mean': float(sa_red.mean()), 'ga_mean': float(ga_red.mean()),
        'rls_mean': float(rls_red.mean()),
        'p_greedy_vs_sa': float(p_sa) if np.isfinite(p_sa) else None,
        'p_greedy_vs_ga': float(p_ga) if np.isfinite(p_ga) else None,
        'p_greedy_vs_rls': float(p_rls) if np.isfinite(p_rls) else None,
        'cliffs_delta_sa': float(cd_sa), 'cliffs_delta_ga': float(cd_ga),
        'cliffs_delta_rls': float(cd_rls),
    },
    'entanglement_sweet_spot': {
        'optimal_rho': float(best_rho),
        'ci_low': float(ci_low) if np.isfinite(ci_low) else None,
        'ci_high': float(ci_high) if np.isfinite(ci_high) else None,
        'reduction_at_optimal': float(by_rho[by_rho['entanglement_density']==best_rho]['mean'].values[0])
                                 if best_rho in by_rho['entanglement_density'].values else None,
    },
}
with open(f"data/processed/phase2_statistics_{TIMESTAMP}.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"\nPhase 2B COMPLETE — stats: phase2_statistics_{TIMESTAMP}.json")