"""Phase 0: Data Integrity Fix — Re-run E1-E5 with fixed Greedy optimizer."""
import sys, os, json, time, copy, numpy as np, pandas as pd
from datetime import datetime
from qiskit import QuantumCircuit
from scipy import stats as sp_stats

sys.path.insert(0, "D:/Desktop/Q-research")

from src.circuits.generator_v2 import (
    CircuitConfig, CircuitFamily, StructureType,
    generate_circuit_batch, MetricsCalculator
)
from src.optimisation.optimizers_v2 import (
    GreedyGateCancellation, SimulatedAnnealingOptimizer,
    GeneticAlgorithmOptimizer, RandomLocalSearch
)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)
np.random.seed(42)

greedy = GreedyGateCancellation(max_iterations=100)
sa = SimulatedAnnealingOptimizer(max_iterations=300, initial_temp=5.0, cooling_rate=0.999)
ga = GeneticAlgorithmOptimizer(population_size=15, generations=15, mutation_rate=0.2)
rls = RandomLocalSearch(max_iterations=100, neighborhood_size=10)
optimizers = [("greedy", greedy), ("sa", sa), ("ga", ga), ("rls", rls)]

def run_opt(opt, qc, target):
    return opt.optimize(qc, target)

# =========================================================================
# E1: Phase Transition Re-test (50 trials per config to save time)
# =========================================================================
print(f"\n[E1] Phase Transition (50 trials x 3 n x 6 d x 4 opts = 3600 records)")
e1_records = []
for n_q in [3, 5, 7]:
    for depth in [5, 10, 15, 20, 25, 30]:
        for trial in range(50):
            seed = n_q * 10000 + depth * 100 + trial
            np.random.seed(seed)
            config = CircuitConfig(n_qubits=n_q, depth=depth, family=CircuitFamily.UNIVERSAL, seed=seed)
            circuits = generate_circuit_batch(config, 1)
            qc, metrics = circuits[0]
            orig = qc.size()
            target = qc.copy()
            for opt_name, opt in optimizers:
                r = run_opt(opt, qc.copy(), target)
                e1_records.append(dict(experiment="e1_phase_transition", version="phase0_v1", timestamp=TIMESTAMP,
                    n_qubits=n_q, depth=depth, trial=trial, seed=seed, optimizer=opt_name,
                    original_gates=orig, optimized_gates=r.optimized_size,
                    reduction=r.reduction, fidelity=r.fidelity,
                    success=r.success, runtime=r.runtime_seconds))

e1_df = pd.DataFrame(e1_records)
e1_df.to_csv(f"data/raw/exp1_phase_transition_{TIMESTAMP}.csv", index=False)
print(f"  Saved {len(e1_df)} records")

# =========================================================================
# E4: Algorithm Comparison (100 trials, n=5, d=20)
# =========================================================================
print(f"\n[E4] Algorithm Comparison (100 trials x 4 opts = 400 records)")
e4_records = []
for trial in range(100):
    seed = 5000 + trial
    np.random.seed(seed)
    config = CircuitConfig(n_qubits=5, depth=20, family=CircuitFamily.UNIVERSAL, seed=seed)
    circuits = generate_circuit_batch(config, 1)
    qc, _ = circuits[0]
    orig = qc.size()
    target = qc.copy()
    for opt_name, opt in optimizers:
        r = run_opt(opt, qc.copy(), target)
        e4_records.append(dict(experiment="e4_algorithm_comparison", version="phase0_v1", timestamp=TIMESTAMP,
            trial=trial, seed=seed, optimizer=opt_name,
            original_gates=orig, optimized_gates=r.optimized_size,
            reduction=r.reduction, fidelity=r.fidelity,
            success=r.success, runtime=r.runtime_seconds))

e4_df = pd.DataFrame(e4_records)
e4_df.to_csv(f"data/raw/exp4_algorithm_comparison_{TIMESTAMP}.csv", index=False)
print(f"  Saved {len(e4_records)} records")

# =========================================================================
# E3: Scaling (n=3..15, 30 trials each) - power law analysis
# =========================================================================
print(f"\n[E3] Gate Reduction Scaling (30 trials x 7 n = 210 records)")
e3_records = []
for n_q in [3, 5, 7, 9, 11, 13, 15]:
    for trial in range(30):
        seed = 30000 + n_q * 100 + trial
        np.random.seed(seed)
        config = CircuitConfig(n_qubits=n_q, depth=20, family=CircuitFamily.UNIVERSAL, seed=seed)
        circuits = generate_circuit_batch(config, 1)
        qc, _ = circuits[0]
        orig = qc.size()
        target = qc.copy()
        r = greedy.optimize(qc, target)
        e3_records.append(dict(experiment="e3_scaling", version="phase0_v1", timestamp=TIMESTAMP,
            n_qubits=n_q, trial=trial, seed=seed,
            original_gates=orig, optimized_gates=r.optimized_size,
            reduction=r.reduction, fidelity=r.fidelity))

e3_df = pd.DataFrame(e3_records)
e3_df.to_csv(f"data/raw/exp3_scaling_{TIMESTAMP}.csv", index=False)
print(f"  Saved {len(e3_records)} records")

# Power law fit on E3
mean_by_n = e3_df.groupby('n_qubits')['reduction'].mean()
log_n = np.log(mean_by_n.index.values.astype(float))
log_red = np.log(mean_by_n.values.astype(float))
slope, intercept, r_val, p_val, std_err = sp_stats.linregress(log_n, log_red)
print(f"  Power law: reduction ∝ n^{slope:.3f} (R²={r_val**2:.3f}, p={p_val:.4f})")

# =========================================================================
# E2: Entanglement Density Sweep (50 trials x 9 rho values)
# =========================================================================
print(f"\n[E2] Entanglement Density Sweep (50 trials x 9 rho = 450 records)")
e2_records = []
for rho in [round(r, 1) for r in np.arange(0.1, 1.0, 0.1)]:
    for trial in range(50):
        seed = 20000 + int(rho * 100) * 10 + trial
        np.random.seed(seed)
        config = CircuitConfig(n_qubits=5, depth=15, family=CircuitFamily.UNIVERSAL,
                               seed=seed, entanglement_density=rho)
        circuits = generate_circuit_batch(config, 1)
        qc, _ = circuits[0]
        orig = qc.size()
        target = qc.copy()
        r = greedy.optimize(qc, target)
        e2_records.append(dict(experiment="e2_entanglement_density", version="phase0_v1", timestamp=TIMESTAMP,
            rho=rho, trial=trial, seed=seed,
            original_gates=orig, optimized_gates=r.optimized_size,
            reduction=r.reduction, fidelity=r.fidelity))

e2_df = pd.DataFrame(e2_records)
e2_df.to_csv(f"data/raw/exp2_entanglement_density_{TIMESTAMP}.csv", index=False)
best_rho = e2_df.groupby('rho')['reduction'].mean().idxmax()
print(f"  Saved {len(e2_records)} records, optimal ρ={best_rho:.1f}")

# =========================================================================
# E5: Optimization Landscape (quick, 30 trials x 5 depths)
# =========================================================================
print(f"\n[E5] Optimization Landscape (30 trials x 5 depths = 150 records)")
e5_records = []
for depth in [5, 10, 15, 20, 25]:
    for trial in range(30):
        seed = 50000 + depth * 10 + trial
        np.random.seed(seed)
        config = CircuitConfig(n_qubits=5, depth=depth, family=CircuitFamily.UNIVERSAL, seed=seed)
        circuits = generate_circuit_batch(config, 1)
        qc, _ = circuits[0]
        orig = qc.size()
        target = qc.copy()
        for opt_name, opt in optimizers:
            r = run_opt(opt, qc.copy(), target)
            e5_records.append(dict(experiment="e5_landscape", version="phase0_v1", timestamp=TIMESTAMP,
                depth=depth, trial=trial, seed=seed, optimizer=opt_name,
                original_gates=orig, optimized_gates=r.optimized_size,
                reduction=r.reduction, fidelity=r.fidelity, runtime=r.runtime_seconds))

e5_df = pd.DataFrame(e5_records)
e5_df.to_csv(f"data/raw/exp5_landscape_{TIMESTAMP}.csv", index=False)
print(f"  Saved {len(e5_records)} records")

# =========================================================================
# Summary Statistics
# =========================================================================
def opt_summary(df, opt_name):
    sub = df[df['optimizer'] == opt_name]
    return dict(
        optimizer=opt_name,
        n=len(sub),
        mean_reduction=float(sub['reduction'].mean()),
        std_reduction=float(sub['reduction'].std()),
        median_reduction=float(sub['reduction'].median()),
        success_5pct=float((sub['reduction'] >= 0.05).mean()),
        success_10pct=float((sub['reduction'] >= 0.10).mean()),
        success_20pct=float((sub['reduction'] >= 0.20).mean()),
        mean_fidelity=float(sub['fidelity'].mean()),
        mean_runtime=float(sub['runtime'].mean()),
    )

print("\n" + "=" * 70)
print("E4 Optimizer Summary (n=5, d=20, 100 trials):")
print(f"  {'Optimizer':<10}  {'Mean Red':>9}  {'Med Red':>8}  {'Succ 5%':>8}  {'Succ 20%':>8}  {'Fidelity':>9}  {'Runtime(s)':>10}")
print("  " + "-" * 70)
e4_stats = [opt_summary(e4_df, n) for n, _ in optimizers]
for s in e4_stats:
    print(f"  {s['optimizer']:<10}  {s['mean_reduction']:>8.2%}  {s['median_reduction']:>7.2%}  "
          f"{s['success_5pct']:>7.1%}  {s['success_20pct']:>7.1%}  "
          f"{s['mean_fidelity']:>8.4f}  {s['mean_runtime']:>9.4f}")

summary = {
    'version': 'phase0_v1', 'timestamp': TIMESTAMP,
    'greedy_bug_fixed': True,
    'greedy_qubit_check': True,
    'e3_power_law': {'exponent': round(slope, 4), 'r_squared': round(r_val**2, 4), 'p_value': round(p_val, 6)},
    'e2_optimal_rho': best_rho,
    'e4_stats': e4_stats,
}
with open(f"data/processed/phase0_summary_{TIMESTAMP}.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"\nPhase 0 COMPLETE — timestamp: {TIMESTAMP}")
print(f"Files: data/raw/exp{{1,2,3,4,5}}_phase_transition_..._{TIMESTAMP}.csv")
print(f"Summary: data/processed/phase0_summary_{TIMESTAMP}.json")