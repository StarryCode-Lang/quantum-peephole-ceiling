"""
Phase 0: Data Integrity Fix — Re-run E1-E5 with FIXED Greedy optimizer.
Uses FastRandomCircuitGenerator (from archive/old_code/fast_generator.py)
to match the generator used in original E1-E5 experiments.

BUG FIX: GreedyGateCancellation._are_inverse() now checks qubits match before
cancelling gates. This was the root cause of incorrect optimizer comparisons.

Original E1-E5 data had this bug. This script reproduces those experiments
with the fix applied so results are comparable.
"""
import sys, os, json, time, copy, numpy as np, pandas as pd
from datetime import datetime

sys.path.insert(0, "D:/Desktop/Q-research")
sys.path.insert(0, "D:/Desktop/Q-research/archive/old_code")

PROJECT_ROOT = "D:/Desktop/Q-research"
os.makedirs(f"{PROJECT_ROOT}/data/raw", exist_ok=True)
os.makedirs(f"{PROJECT_ROOT}/data/processed", exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Use old FastRandomCircuitGenerator (matches original E1-E5)
from fast_generator import FastRandomCircuitGenerator
from src.optimisation.optimizers_v2 import (
    GreedyGateCancellation, SimulatedAnnealingOptimizer,
    GeneticAlgorithmOptimizer, RandomLocalSearch
)

np.random.seed(42)

# Configure optimizers
greedy = GreedyGateCancellation(max_iterations=100)
sa = SimulatedAnnealingOptimizer(max_iterations=200, initial_temp=5.0, cooling_rate=0.999)
ga = GeneticAlgorithmOptimizer(population_size=15, generations=15, mutation_rate=0.2)
rls = RandomLocalSearch(max_iterations=100, neighborhood_size=10)
optimizers = [
    ("greedy", greedy),
    ("sa", sa),
    ("ga", ga),
    ("rls", rls),
]

def generate_circuit_old(n_qubits, depth, seed=None):
    """Use FastRandomCircuitGenerator to produce circuits with cancelable pairs."""
    gen = FastRandomCircuitGenerator(n_qubits, gate_set=['h', 'cx', 't', 'rz'])
    qc = gen.generate(depth=depth, two_qubit_ratio=0.3, seed=seed, angle_randomness=0.0)
    return qc

def run_experiment(name, n_qubits_list, depth_list, n_trials, label=""):
    """Run one experiment (E1-E5 equivalent)."""
    print(f"\n[{name}] {label}")
    records = []
    configs = [(n, d) for n in n_qubits_list for d in depth_list]
    total = len(configs) * n_trials * len(optimizers)
    done = 0
    
    for n_q in n_qubits_list:
        for depth in depth_list:
            for trial in range(n_trials):
                seed = n_q * 10000 + depth * 10 + trial
                np.random.seed(seed)
                
                qc = generate_circuit_old(n_q, depth, seed=seed)
                original_size = qc.size()
                target = qc.copy()
                
                for opt_name, opt in optimizers:
                    qc_copy = qc.copy()
                    start = time.time()
                    result = opt.optimize(qc_copy, target)
                    elapsed = time.time() - start
                    
                    records.append({
                        'experiment': name,
                        'version': 'phase0_fixed',
                        'timestamp': TIMESTAMP,
                        'n_qubits': n_q,
                        'depth': depth,
                        'trial': trial,
                        'seed': seed,
                        'optimizer': opt_name,
                        'original_gates': result.original_size,
                        'optimized_gates': result.optimized_size,
                        'reduction': result.reduction,
                        'fidelity': result.fidelity,
                        'success': result.success,
                        'runtime': elapsed,
                    })
                    done += 1
                    if done % 200 == 0:
                        print(f"  Progress: {done}/{total} ({100*done/total:.0f}%)")
    
    return pd.DataFrame(records)

# =========================================================================
# E1: Phase Transition (n=3,5,7 × d=5,10,15,20,25,30 × 50 trials)
# =========================================================================
print("=" * 70)
print("Phase 0: Data Integrity Fix — Re-running E1-E5 with FIXED Greedy")
print("Generator: FastRandomCircuitGenerator (matches original E1-E5)")
print("Optimizer fix: _are_inverse checks qubit matching")
print("=" * 70)

start_all = time.time()
records_all = []

# E1: Phase Transition
e1 = run_experiment(
    "e1_phase_transition",
    n_qubits_list=[3, 5, 7],
    depth_list=[5, 10, 15, 20, 25, 30],
    n_trials=50,
    label="Phase Transition (3 n × 6 d × 50 trials × 4 opts = 3600 records)"
)

# E2: Entanglement Density
e2 = run_experiment(
    "e2_entanglement_density",
    n_qubits_list=[5, 7],
    depth_list=[15],
    n_trials=50,
    label="Entanglement Density (2 n × 50 trials × 4 opts = 400 records)"
)

# E3: Scaling
e3 = run_experiment(
    "e3_scaling",
    n_qubits_list=[3, 4, 5, 6, 7, 8, 9],
    depth_list=[20],
    n_trials=50,
    label="Scaling (7 n × 50 trials × 4 opts = 1400 records)"
)

# E4: Algorithm Comparison
e4 = run_experiment(
    "e4_algorithm_comparison",
    n_qubits_list=[3, 5, 7],
    depth_list=[10, 20],
    n_trials=100,
    label="Algorithm Comparison (3 n × 2 d × 100 trials × 4 opts = 2400 records)"
)

# E5: Landscape
e5 = run_experiment(
    "e5_landscape",
    n_qubits_list=[5],
    depth_list=[15],
    n_trials=50,
    label="Landscape (1 n × 50 trials × 4 opts = 200 records)"
)

records_all = pd.concat([e1, e2, e3, e4, e5], ignore_index=True)
records_all.to_csv(f"{PROJECT_ROOT}/data/raw/phase0_e1_e5_fixed_{TIMESTAMP}.csv", index=False)

elapsed = time.time() - start_all
print(f"\nPhase 0 COMPLETE in {elapsed:.0f}s")
print(f"Saved {len(records_all)} total records")
print(f"File: phase0_e1_e5_fixed_{TIMESTAMP}.csv")

# Quick sanity check
print("\n" + "=" * 70)
print("Sanity Check (FIXED Greedy):")
print("=" * 70)
greedy_data = records_all[records_all['optimizer'] == 'greedy']
print(f"  Greedy mean reduction: {greedy_data['reduction'].mean():.2%}")
print(f"  Greedy success (any reduction): {(greedy_data['reduction'] > 0).mean():.1%}")
print(f"  Greedy success (>5%): {(greedy_data['reduction'] > 0.05).mean():.1%}")
print(f"  Greedy success (>10%): {(greedy_data['reduction'] > 0.10).mean():.1%}")

# By n_qubits
for n in sorted(records_all['n_qubits'].unique()):
    sub = greedy_data[greedy_data['n_qubits'] == n]
    print(f"  n={n}: mean={sub['reduction'].mean():.2%}, succ>0={(sub['reduction']>0).mean():.1%}, "
          f"succ>5%={(sub['reduction']>0.05).mean():.1%}")

# Compare old vs new (should be very similar since the optimizer fix is subtle)
print("\n--- OLD vs NEW Greedy (bug fix comparison) ---")
print("If old data used the buggy _are_inverse, new data with fix should be similar or slightly lower.")
print("The fix prevents false positive cancellations (different-qubit gates matched as inverse).")

# Save summary
summary = {
    'version': 'phase0_fixed',
    'timestamp': TIMESTAMP,
    'runtime_seconds': elapsed,
    'n_records': len(records_all),
    'greedy_stats': {
        'mean_reduction': float(greedy_data['reduction'].mean()),
        'std_reduction': float(greedy_data['reduction'].std()),
        'median_reduction': float(greedy_data['reduction'].median()),
        'success_rate_positive': float((greedy_data['reduction'] > 0).mean()),
        'success_rate_5pct': float((greedy_data['reduction'] > 0.05).mean()),
        'success_rate_10pct': float((greedy_data['reduction'] > 0.10).mean()),
    }
}
with open(f"{PROJECT_ROOT}/data/processed/phase0_summary_{TIMESTAMP}.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"\nPhase 0 COMPLETE — {len(records_all)} records, summary: phase0_summary_{TIMESTAMP}.json")