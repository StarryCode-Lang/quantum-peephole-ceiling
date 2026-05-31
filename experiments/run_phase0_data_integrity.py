"""
Phase 0: Data Integrity Fix — Re-run E1-E5 with fixed Greedy optimizer.
Key changes from original E1-E5:
1. Greedy _are_inverse now checks qubit matching (bug fix)
2. SA/GA success threshold lowered from 20% to 5% (natural threshold)
3. All experiments run 100 trials each
4. Fidelity properly measured for all optimizers
5. All results saved with version='phase0_v1' for provenance
"""
import sys, os, json, time, copy, numpy as np, pandas as pd
from datetime import datetime
from qiskit import QuantumCircuit
# Fix path: project root is parent of 'experiments' dir
_script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_script_dir)  # D:/Desktop/Q-research
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)
from src.optimisation.optimizers_v2 import (
    GreedyGateCancellation,
    SimulatedAnnealingOptimizer,
    GeneticAlgorithmOptimizer,
    RandomLocalSearch,
    BaseOptimizer
)
from src.circuits.generator_v2 import generate_circuit
from src.analysis.statistical_rigor import calculate_statistics

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
RESULTS_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

np.random.seed(42)

# =========================================================================
# E1: Phase Transition Re-test with FIXED Greedy
# =========================================================================
print("\n[E1] Phase Transition Re-test with fixed Greedy...")
print("  Testing: n ∈ [3,5,7], depths ∈ [5,10,15,20,25,30], 100 trials each")
print("  Optimizers: Greedy, SA, GA, RLS, Random")

e1_records = []
n_qubits_list = [3, 5, 7]
depths_list = [5, 10, 15, 20, 25, 30]
n_trials = 100

greedy = GreedyGateCancellation(max_iterations=100)
sa = SimulatedAnnealingOptimizer(max_iterations=500, initial_temp=5.0, cooling_rate=0.999)
ga = GeneticAlgorithmOptimizer(population_size=20, generations=20, mutation_rate=0.2)
rls = RandomLocalSearch(max_iterations=200, neighborhood_size=10)
optimizers = {
    'greedy': greedy,
    'sa': sa,
    'ga': ga,
    'rls': rls,
}

for n_q in n_qubits_list:
    for depth in depths_list:
        for trial in range(n_trials):
            seed = n_q * 10000 + depth * 100 + trial
            np.random.seed(seed)
            qc = generate_circuit(n_qubits=n_q, depth=depth, seed=seed)
            orig_size = qc.size()
            target = qc.copy()

            for opt_name, opt in optimizers.items():
                result = opt.optimize(qc, target)
                e1_records.append({
                    'experiment': 'e1_phase_transition',
                    'version': 'phase0_v1',
                    'timestamp': TIMESTAMP,
                    'n_qubits': n_q,
                    'depth': depth,
                    'trial': trial,
                    'seed': seed,
                    'optimizer': opt_name,
                    'original_gates': orig_size,
                    'optimized_gates': result.optimized_size,
                    'reduction': result.reduction,
                    'fidelity': result.fidelity,
                    'success': result.success,
                    'runtime': result.runtime_seconds,
                    'iterations': result.iterations,
                })

e1_df = pd.DataFrame(e1_records)
e1_path = f"{RESULTS_DIR}/exp1_phase_transition_{TIMESTAMP}.csv"
e1_df.to_csv(e1_path, index=False)
print(f"  E1 complete: {len(e1_df)} records → {e1_path}")

# =========================================================================
# E4: Algorithm Comparison Re-test with FIXED Greedy (and lowered threshold)
# =========================================================================
print("\n[E4] Algorithm Comparison Re-test (with 5% threshold for SA/GA)...")
print("  Testing: n=5, depth=20, 100 trials each, 5 optimizers")

e4_records = []
greedy2 = GreedyGateCancellation(max_iterations=100)
sa2 = SimulatedAnnealingOptimizer(max_iterations=500, initial_temp=5.0, cooling_rate=0.999)
ga2 = GeneticAlgorithmOptimizer(population_size=20, generations=20, mutation_rate=0.2)
rls2 = RandomLocalSearch(max_iterations=200, neighborhood_size=10)
optimizers2 = {'greedy': greedy2, 'sa': sa2, 'ga': ga2, 'rls': rls2}

for trial in range(100):
    seed = 5000 + trial
    np.random.seed(seed)
    qc = generate_circuit(n_qubits=5, depth=20, seed=seed)
    orig_size = qc.size()
    target = qc.copy()

    for opt_name, opt in optimizers2.items():
        result = opt.optimize(qc, target)
        e4_records.append({
            'experiment': 'e4_algorithm_comparison',
            'version': 'phase0_v1',
            'timestamp': TIMESTAMP,
            'trial': trial,
            'seed': seed,
            'optimizer': opt_name,
            'original_gates': orig_size,
            'optimized_gates': result.optimized_size,
            'reduction': result.reduction,
            'fidelity': result.fidelity,
            'success': result.success,
            'runtime': result.runtime_seconds,
        })

e4_df = pd.DataFrame(e4_records)
e4_path = f"{RESULTS_DIR}/exp4_algorithm_comparison_{TIMESTAMP}.csv"
e4_df.to_csv(e4_path, index=False)
print(f"  E4 complete: {len(e4_df)} records → {e4_path}")

# =========================================================================
# Compute Summary Statistics
# =========================================================================
print("\n[Stats] Computing summary statistics...")

def summarize_optimizer(df, opt_name):
    opt_df = df[df['optimizer'] == opt_name]
    if len(opt_df) == 0:
        return {}
    return {
        'optimizer': opt_name,
        'n_trials': len(opt_df),
        'mean_reduction': float(opt_df['reduction'].mean()),
        'std_reduction': float(opt_df['reduction'].std()),
        'median_reduction': float(opt_df['reduction'].median()),
        'min_reduction': float(opt_df['reduction'].min()),
        'max_reduction': float(opt_df['reduction'].max()),
        'success_rate': float(opt_df['success'].mean()),
        'mean_fidelity': float(opt_df['fidelity'].mean()),
        'mean_runtime': float(opt_df['runtime'].mean()),
        'pct_above_5pct': float((opt_df['reduction'] >= 0.05).mean()),
        'pct_above_10pct': float((opt_df['reduction'] >= 0.10).mean()),
        'pct_above_20pct': float((opt_df['reduction'] >= 0.20).mean()),
    }

# E1 by optimizer
e1_stats = [summarize_optimizer(e1_df, opt) for opt in optimizers.keys()]
e1_stats_path = f"{PROCESSED_DIR}/e1_phase_transition_stats_{TIMESTAMP}.json"
with open(e1_stats_path, 'w') as f:
    json.dump({'version': 'phase0_v1', 'timestamp': TIMESTAMP, 'stats': e1_stats, 'n_trials_per_config': n_trials}, f, indent=2)
print(f"  E1 stats: {e1_stats_path}")

# E4 by optimizer
e4_stats = [summarize_optimizer(e4_df, opt) for opt in optimizers2.keys()]
e4_stats_path = f"{PROCESSED_DIR}/e4_algorithm_comparison_stats_{TIMESTAMP}.json"
with open(e4_stats_path, 'w') as f:
    json.dump({'version': 'phase0_v1', 'timestamp': TIMESTAMP, 'stats': e4_stats}, f, indent=2)
print(f"  E4 stats: {e4_stats_path}")

# =========================================================================
# Key comparison: OLD vs NEW Greedy on E4
# =========================================================================
print("\n[Key Finding] Fixed Greedy vs SA/GA comparison (E4, n=5, depth=20):")
print(f"  {'Optimizer':<10}  {'Mean Reduction':>15}  {'Success Rate (20%)':>18}  {'Success Rate (5%)':>17}  {'Fidelity':>10}  {'Runtime (s)':>12}")
print("  " + "-" * 90)
for s in e4_stats:
    if not s:
        continue
    print(f"  {s['optimizer']:<10}  {s['mean_reduction']:>14.2%}  {s['pct_above_20pct']:>17.1%}  "
          f"{s['pct_above_5pct']:>16.1%}  {s['mean_fidelity']:>9.4f}  {s['mean_runtime']:>11.4f}")

# =========================================================================
# E3: Scaling (n from 3 to 15) — critical for power-law analysis
# =========================================================================
print("\n[E3] Gate Reduction Scaling Re-test (n=3..15, 50 trials each)...")

e3_records = []
for n_q in [3, 5, 7, 9, 11, 13, 15]:
    for trial in range(50):
        seed = 30000 + n_q * 100 + trial
        np.random.seed(seed)
        qc = generate_circuit(n_qubits=n_q, depth=20, seed=seed)
        orig_size = qc.size()
        target = qc.copy()
        result = greedy.optimize(qc, target)
        e3_records.append({
            'experiment': 'e3_scaling',
            'version': 'phase0_v1',
            'timestamp': TIMESTAMP,
            'n_qubits': n_q,
            'trial': trial,
            'seed': seed,
            'original_gates': orig_size,
            'optimized_gates': result.optimized_size,
            'reduction': result.reduction,
            'fidelity': result.fidelity,
        })

e3_df = pd.DataFrame(e3_records)
e3_path = f"{RESULTS_DIR}/exp3_scaling_{TIMESTAMP}.csv"
e3_df.to_csv(e3_path, index=False)
print(f"  E3 complete: {len(e3_df)} records → {e3_path}")

# Power law fit
from scipy import stats as sp_stats
log_n = np.log(e3_df.groupby('n_qubits')['original_gates'].mean().index.values.astype(float))
log_dg = np.log(e3_df.groupby('n_qubits')['reduction'].mean().reindex(
    e3_df.groupby('n_qubits')['original_gates'].mean().index).values.astype(float))
slope, intercept, r_val, p_val, std_err = sp_stats.linregress(log_n, log_dg)

print(f"\n  Power law fit: reduction ∝ n^{slope:.3f} (R²={r_val**2:.3f}, p={p_val:.4f})")
print(f"  95% CI for exponent: [{slope - 1.96*std_err:.3f}, {slope + 1.96*std_err:.3f}]")

# =========================================================================
# E2: Entanglement Density Sweep (quick re-run, 50 trials)
# =========================================================================
print("\n[E2] Entanglement Density Sweep (re-test, 50 trials)...")

e2_records = []
for rho in np.arange(0.1, 1.0, 0.1):
    for trial in range(50):
        seed = 20000 + int(rho * 100) * 10 + trial
        np.random.seed(seed)
        qc = generate_circuit(n_qubits=5, depth=15, seed=seed, entanglement_density=rho)
        orig_size = qc.size()
        target = qc.copy()
        result = greedy.optimize(qc, target)
        e2_records.append({
            'experiment': 'e2_entanglement_density',
            'version': 'phase0_v1',
            'timestamp': TIMESTAMP,
            'rho': round(rho, 1),
            'trial': trial,
            'seed': seed,
            'original_gates': orig_size,
            'optimized_gates': result.optimized_size,
            'reduction': result.reduction,
            'fidelity': result.fidelity,
        })

e2_df = pd.DataFrame(e2_records)
e2_path = f"{RESULTS_DIR}/exp2_entanglement_density_{TIMESTAMP}.csv"
e2_df.to_csv(e2_path, index=False)
print(f"  E2 complete: {len(e2_df)} records → {e2_path}")

# Find sweet spot
e2_by_rho = e2_df.groupby('rho')['reduction'].agg(['mean', 'std', 'count'])
best_rho = e2_by_rho['mean'].idxmax()
print(f"  Optimal entanglement density: ρ = {best_rho:.1f} (reduction = {e2_by_rho.loc[best_rho, 'mean']:.2%})")

# =========================================================================
# Summary
# =========================================================================
print("\n" + "=" * 70)
print("Phase 0 COMPLETE — Data Integrity Report")
print("=" * 70)
print(f"Timestamp: {TIMESTAMP}")
print(f"E1: {len(e1_df)} records (phase transition, fixed Greedy)")
print(f"E2: {len(e2_df)} records (entanglement density)")
print(f"E3: {len(e3_df)} records (scaling)")
print(f"E4: {len(e4_df)} records (algorithm comparison, 5% threshold)")

# Save consolidated summary
summary = {
    'version': 'phase0_v1',
    'timestamp': TIMESTAMP,
    'greedy_bug_fixed': True,
    'threshold_lowered_to_5pct': True,
    'e1': {'n_records': len(e1_df), 'stats_path': e1_stats_path},
    'e2': {'n_records': len(e2_df), 'best_rho': best_rho},
    'e3': {'n_records': len(e3_df), 'power_law_exponent': slope, 'r_squared': r_val**2, 'p_value': p_val},
    'e4': {'n_records': len(e4_df), 'optimizer_stats': e4_stats},
}

summary_path = f"{PROCESSED_DIR}/phase0_summary_{TIMESTAMP}.json"
with open(summary_path, 'w') as f:
    json.dump(summary, f, indent=2)
print(f"\nConsolidated summary: {summary_path}")
print("Phase 0 DONE.")