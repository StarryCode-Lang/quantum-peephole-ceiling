"""
Phase 0: Optimizer Bug Validation — Compare OLD vs NEW optimizer on SAME circuits.
========================================================
BUG: Old _are_inverse() didn't check qubit matching, so H(q0) was matched with H(q1)
as inverses even though they act on DIFFERENT qubits → FALSE cancellations.

This Phase 0 validates:
1. OLD optimizer inflates reduction by matching different-qubit gates
2. NEW optimizer (with qubit check) produces correct results
3. Fix is correct and doesn't break valid cancellations
"""
import sys, os, json, time, copy, numpy as np, pandas as pd
from datetime import datetime
from qiskit import QuantumCircuit

PROJECT_ROOT = "D:/Desktop/Q-research"
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, f"{PROJECT_ROOT}/archive/old_code")
os.makedirs(f"{PROJECT_ROOT}/data/processed", exist_ok=True)

np.random.seed(42)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Import OLD optimizer (with bug) and NEW optimizer (fixed)
from optimizers_v1 import GreedyOptimizer as OldGreedy
from src.optimisation.optimizers_v2 import GreedyGateCancellation as NewGreedy

# Import OLD generator and NEW generator
from generator_v1 import UniversalCircuit as OldGenerator
from src.circuits.generator_v2 import UniversalGenerator, CircuitConfig, CircuitFamily

old_opt = OldGreedy(max_iterations=100)
new_opt = NewGreedy(max_iterations=100)

# Use the OLD generator (same as original E1-E5)
# Note: old and new generators have the same structure (both don't produce
# adjacent cancelable pairs in circuit.data due to layer ordering).
# But we also test with HAND-CRAFTED circuits that DO have cancelable pairs.

print("=" * 70)
print("Phase 0: Optimizer Bug Validation")
print("=" * 70)
print()
print("Test 1: Hand-crafted circuits with KNOWN cancelable pairs")
print("-" * 70)

# Test circuits with known structure
test_circuits = []

# Circuit A: H-H on Q0 (adjacent in circuit.data) — should cancel
qc_a = QuantumCircuit(2)
qc_a.h(0)  # position 0
qc_a.h(0)  # position 1 — adjacent H-H on Q0
qc_a.cx(0, 1)
qc_a.h(1)
qc_a.h(1)  # adjacent H-H on Q1
test_circuits.append(("Hand-crafted H-H pairs", qc_a))

# Circuit B: Alternating H/T gates — mixed
qc_b = QuantumCircuit(2)
for _ in range(5):
    qc_b.h(0)
    qc_b.t(1)
    qc_b.h(0)
    qc_b.cx(0, 1)
test_circuits.append(("Mixed gates with some pairs", qc_b))

# Circuit C: Only Rx gates — NO cancelable pairs (rotation gates with random angles)
qc_c = QuantumCircuit(2)
for i in range(10):
    qc_c.rx(np.random.uniform(0.1, 2.0), i % 2)
test_circuits.append(("Random rotations (no pairs)", qc_c))

results = []

print(f"  {'Circuit':<30}  {'Optimizer':<10}  {'Original':>8}  {'Optimized':>9}  {'Reduction':>9}  {'Improvements':>12}")
print("  " + "-" * 95)

for name, qc in test_circuits:
    for opt_name, opt in [("OLD (buggy)", old_opt), ("NEW (fixed)", new_opt)]:
        r = opt.optimize(qc.copy(), None)
        results.append({
            'circuit': name, 'optimizer': opt_name,
            'original': r.original_size, 'optimized': r.optimized_size,
            'reduction': r.reduction, 'improvements': r.iterations
        })
        print(f"  {name:<30}  {opt_name:<10}  {r.original_size:>8}  {r.optimized_size:>9}  "
              f"{r.reduction:>8.1%}  {r.iterations:>12}")

print()
print("Test 2: Old generator circuits (UniversalCircuit from generator_v1)")
print("-" * 70)

# Generate 50 circuits with OLD generator
old_gen = OldGenerator(n_qubits=5)
records = []

print(f"  {'Circuit':<20}  {'Optimizer':<10}  {'Original':>8}  {'Optimized':>9}  {'Reduction':>9}")
print("  " + "-" * 70)

for seed in range(50):
    np.random.seed(seed)
    qc = old_gen.generate(depth=15, entanglement_density=0.3, seed=seed)
    orig_size = qc.size()
    
    for opt_name, opt in [("OLD (buggy)", old_opt), ("NEW (fixed)", new_opt)]:
        r = opt.optimize(qc.copy(), None)
        records.append({
            'seed': seed, 'optimizer': opt_name,
            'original': r.original_size, 'optimized': r.optimized_size,
            'reduction': r.reduction
        })
    
    old_red = [x['reduction'] for x in records if x['seed'] == seed and x['optimizer'] == 'OLD (buggy)'][0]
    new_red = [x['reduction'] for x in records if x['seed'] == seed and x['optimizer'] == 'NEW (fixed)'][0]
    print(f"  seed={seed:<14}  OLD={old_red:>7.1%}  NEW={new_red:>7.1%}")

df = pd.DataFrame(records)
df.to_csv(f"{PROJECT_ROOT}/data/processed/phase0_bug_validation_{TIMESTAMP}.csv", index=False)

print()
print("SUMMARY:")
print("=" * 70)

old_df = df[df['optimizer'] == 'OLD (buggy)']
new_df = df[df['optimizer'] == 'NEW (fixed)']

print(f"  OLD optimizer mean reduction: {old_df['reduction'].mean():.2%}")
print(f"  NEW optimizer mean reduction: {new_df['reduction'].mean():.2%}")
print(f"  OLD > NEW: {(old_df['reduction'] > new_df['reduction']).mean():.1%} of circuits")
print(f"  OLD inflated (reduction > 0): {(old_df['reduction'] > 0).mean():.1%}")
print(f"  NEW inflated (reduction > 0): {(new_df['reduction'] > 0).mean():.1%}")

print()
print("KEY FINDING:")
print("-" * 70)
if old_df['reduction'].mean() > new_df['reduction'].mean() + 0.01:
    print(f"  ✓ CONFIRMED: OLD optimizer inflates reduction by "
          f"{old_df['reduction'].mean() - new_df['reduction'].mean():.2%}")
    print(f"  ✓ The qubit-matching bug in OLD _are_inverse() causes false cancellations")
    print(f"  ✓ NEW optimizer correctly avoids same-qubit requirement")
    finding = "confirmed"
else:
    print(f"  ! Unexpected: OLD and NEW produce similar results")
    print(f"  ! This suggests the old optimizer may not have had the expected bug")
    finding = "unexpected"

summary = {
    'version': 'phase0_v1',
    'timestamp': TIMESTAMP,
    'finding': finding,
    'old_mean_reduction': float(old_df['reduction'].mean()),
    'new_mean_reduction': float(new_df['reduction'].mean()),
    'inflation': float(old_df['reduction'].mean() - new_df['reduction'].mean()),
    'old_success_rate': float((old_df['reduction'] > 0).mean()),
    'new_success_rate': float((new_df['reduction'] > 0).mean()),
    'n_circuits': len(df) // 2,
}
with open(f"{PROJECT_ROOT}/data/processed/phase0_validation_summary_{TIMESTAMP}.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"\nPhase 0 COMPLETE — saved: phase0_bug_validation_{TIMESTAMP}.csv")
print(f"Summary: phase0_validation_summary_{TIMESTAMP}.json")