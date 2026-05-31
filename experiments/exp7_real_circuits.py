"""Phase 1A: Real Quantum Algorithm Circuits — benchmark all 5 optimizers.
Non-parameterized circuits only (no VQE ansatz — those have unbound symbolic params).
Uses generator_v1 for Clifford circuits which produce adjacent cancelable pairs.
"""
import sys, os, json, time, numpy as np, pandas as pd
from datetime import datetime
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT

sys.path.insert(0, "D:/Desktop/Q-research")
from src.optimisation.optimizers_v2 import (
    GreedyGateCancellation, SimulatedAnnealingOptimizer,
    GeneticAlgorithmOptimizer, RandomLocalSearch
)
from archive.old_code.generator_v1 import UniversalCircuit, CliffordCircuit

PROJECT_ROOT = "D:/Desktop/Q-research"
os.makedirs(f"{PROJECT_ROOT}/data/raw", exist_ok=True)
os.makedirs(f"{PROJECT_ROOT}/data/processed", exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
np.random.seed(42)

optimizers = [
    ("greedy", GreedyGateCancellation(max_iterations=100)),
    ("sa",     SimulatedAnnealingOptimizer(max_iterations=150, initial_temp=5.0, cooling_rate=0.995)),
    ("ga",     GeneticAlgorithmOptimizer(population_size=10, generations=10, mutation_rate=0.2)),
    ("rls",    RandomLocalSearch(max_iterations=80, neighborhood_size=8)),
]

records = []

def get_real_circuits():
    """Generate non-parameterized real quantum algorithm circuits."""
    circuits = []
    
    # QFT circuits (5 sizes)
    for n in [3, 4, 5, 6, 7]:
        try:
            qc = QFT(n).decompose().decompose()
            circuits.append((f'QFT_n{n}', qc))
        except:
            pass

    # GHZ / Bell states (7 sizes) — highly entangled, known structure
    for n in [3, 4, 5, 6, 7, 8, 10]:
        qc = QuantumCircuit(n)
        qc.h(0)
        for i in range(n-1):
            qc.cx(i, i+1)
        circuits.append((f'GHZ_n{n}', qc))

    # GHZ with H layers (more 2-qubit gate density)
    for n in [4, 5, 6, 7, 8]:
        qc = QuantumCircuit(n)
        qc.h(0)
        for i in range(n-1):
            qc.cx(i, i+1)
        for i in range(n):
            qc.h(i)
        circuits.append((f'GHZ_H_n{n}', qc))

    # Linear entanglement with CNOT chains
    for n in [4, 5, 6, 7, 8]:
        qc = QuantumCircuit(n)
        for layer in range(5):
            for i in range(n-1):
                qc.cx(i, i+1)
            for i in range(n):
                qc.h(i)
        circuits.append((f'CNOT_chain_n{n}', qc))

    # Clifford circuits via generator_v1 (these have cancelable pairs)
    for seed in range(20):
        np.random.seed(seed + 1000)
        qc = CliffordCircuit(n_qubits=5).generate(depth=15, seed=seed + 1000)
        circuits.append((f'Clifford_s{seed}', qc))
    
    for seed in range(10):
        np.random.seed(seed + 2000)
        qc = CliffordCircuit(n_qubits=6).generate(depth=12, seed=seed + 2000)
        circuits.append((f'Clifford_n6_s{seed}', qc))

    # Universal circuits via generator_v1 (some structure)
    for seed in range(10):
        np.random.seed(seed + 3000)
        qc = UniversalCircuit(n_qubits=5).generate(depth=15, entanglement_density=0.5, seed=seed + 3000)
        circuits.append((f'Universal_s{seed}', qc))

    return circuits

print("Generating non-parameterized real circuits...")
circuit_list = get_real_circuits()
print(f"Generated {len(circuit_list)} circuits:")
print(f"  - QFT circuits")
print(f"  - GHZ / GHZ+H circuits")  
print(f"  - CNOT chain circuits")
print(f"  - Clifford circuits (generator_v1, 30 total)")
print(f"  - Universal circuits (generator_v1, 10 total)")

print(f"\nRunning {len(circuit_list)} circuits × {len(optimizers)} optimizers")

for idx, (name, qc) in enumerate(circuit_list):
    orig_size = qc.size()
    if orig_size < 2:
        continue

    target = qc.copy()

    for opt_name, opt in optimizers:
        skip_keys = {'logger', 'rng'}
        safe_dict = {k: v for k, v in opt.__dict__.items() if k not in skip_keys}
        opt_copy = type(opt)(**safe_dict)
        start = time.time()
        try:
            r = opt_copy.optimize(qc.copy(), target)
            elapsed = time.time() - start
            records.append({
                'experiment': 'e7_real_circuits',
                'version': 'phase1a_v2',
                'timestamp': TIMESTAMP,
                'circuit_name': name,
                'n_qubits': qc.num_qubits,
                'original_gates': r.original_size,
                'optimized_gates': r.optimized_size,
                'reduction': r.reduction,
                'fidelity': r.fidelity,
                'success': r.success,
                'optimizer': opt_name,
                'runtime': elapsed,
            })
        except Exception as e:
            records.append({
                'experiment': 'e7_real_circuits',
                'version': 'phase1a_v2',
                'timestamp': TIMESTAMP,
                'circuit_name': name,
                'n_qubits': qc.num_qubits,
                'original_gates': orig_size,
                'optimized_gates': orig_size,
                'reduction': 0.0,
                'fidelity': 0.0,
                'success': False,
                'optimizer': opt_name,
                'runtime': time.time() - start,
            })

    if (idx + 1) % 10 == 0:
        print(f"  Progress: {idx+1}/{len(circuit_list)} circuits done")

df = pd.DataFrame(records)
df.to_csv(f"{PROJECT_ROOT}/data/raw/exp7_real_circuits_{TIMESTAMP}.csv", index=False)

print("\n" + "=" * 70)
print("REAL CIRCUIT RESULTS:")
print("=" * 70)

print(f"\n{'Optimizer':<10}  {'Mean Red':>9}  {'Succ >0%':>8}  {'Succ >5%':>8}  {'Succ >10%':>9}  {'Max Red':>8}")
print("  " + "-" * 60)
for opt_name, grp in df.groupby('optimizer'):
    print(f"  {opt_name:<10}  {grp['reduction'].mean():>8.1%}  "
          f"{(grp['reduction']>0).mean():>7.1%}  "
          f"{(grp['reduction']>0.05).mean():>7.1%}  "
          f"{(grp['reduction']>0.10).mean():>8.1%}  "
          f"{grp['reduction'].max():>7.1%}")

print(f"\nTop circuits (Greedy, top 10):")
greedy_df = df[df['optimizer']=='greedy'].sort_values('reduction', ascending=False)
for _, row in greedy_df.head(10).iterrows():
    print(f"  {row['circuit_name']:<25} n={row['n_qubits']:>2}: red={row['reduction']:>6.1%}")

# Circuit type analysis
print(f"\nBy circuit type:")
clifford_df = df[df['circuit_name'].str.startswith('Clifford')]
universal_df = df[df['circuit_name'].str.startswith('Universal')]
ghz_df = df[df['circuit_name'].str.startswith('GHZ')]
qft_df = df[df['circuit_name'].str.startswith('QFT')]
cnot_df = df[df['circuit_name'].str.startswith('CNOT')]

for label, sub in [('Clifford', clifford_df), ('Universal', universal_df),
                    ('GHZ', ghz_df), ('QFT', qft_df), ('CNOT', cnot_df)]:
    if len(sub) > 0:
        print(f"  {label:<10}: n={len(sub):>3} records, greedy mean={sub[sub['optimizer']=='greedy']['reduction'].mean():>6.1%}")

print("\n--- KEY INSIGHT ---")
greedy_mean = df[df['optimizer']=='greedy']['reduction'].mean()
sa_mean = df[df['optimizer']=='sa']['reduction'].mean()
ga_mean = df[df['optimizer']=='ga']['reduction'].mean()
rls_mean = df[df['optimizer']=='rls']['reduction'].mean()
print(f"  Real circuits (non-parameterized):")
print(f"  Greedy: {greedy_mean:.1%}, SA: {sa_mean:.1%}, GA: {ga_mean:.1%}, RLS: {rls_mean:.1%}")
print(f"  → Clifford circuits from generator_v1 have cancelable pairs")
print(f"  → generator_v2 UniversalGenerator produces 0% on same optimizer")

analysis = {
    'version': 'phase1a_v2', 'timestamp': TIMESTAMP,
    'n_circuits': len(circuit_list),
    'n_records': len(df),
    'optimizer_summary': df.groupby('optimizer')['reduction'].agg(['mean','std','max']).to_dict(),
    'top_circuits': greedy_df[['circuit_name','n_qubits','reduction']].head(15).to_dict(orient='records'),
}
with open(f"{PROJECT_ROOT}/data/processed/exp7_analysis_{TIMESTAMP}.json", "w") as f:
    json.dump(analysis, f, indent=2)

print(f"\nE7 COMPLETE — {len(df)} records → exp7_real_circuits_{TIMESTAMP}.csv")