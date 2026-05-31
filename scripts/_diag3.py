import sys, copy, time
sys.path.insert(0, "D:/Desktop/Q-research")
import numpy as np
from qiskit import QuantumCircuit
from src.optimisation.optimizers_v2 import (
    SimulatedAnnealingOptimizer, GeneticAlgorithmOptimizer,
    GreedyGateCancellation
)

print("=" * 70)
print("ANALYSIS 1: Cancellable pairs & greedy ceiling by n/d")
print("=" * 70)

def count_cancellable_pairs(circuit):
    count = 0
    for i in range(len(circuit.data) - 1):
        i1, i2 = circuit.data[i], circuit.data[i+1]
        q1 = tuple(sorted(q._index for q in i1.qubits))
        q2 = tuple(sorted(q._index for q in i2.qubits))
        if q1 != q2:
            continue
        g1, g2 = i1.operation.name, i2.operation.name
        if g1 == g2 and g1 in ('h','x','y','z','cx','cz','swap'):
            count += 1
        elif (g1 == 't' and g2 == 'tdg') or (g1 == 'tdg' and g2 == 't'):
            count += 1
        elif (g1 == 's' and g2 == 'sdg') or (g1 == 'sdg' and g2 == 's'):
            count += 1
    return count

greedy = GreedyGateCancellation(max_iterations=100)
for n_q in [3, 5, 7]:
    for depth in [10, 20, 30]:
        tot_cancel = 0; tot_gates = 0; greedy_reds = []
        for seed in range(10):
            np.random.seed(seed)
            qc = QuantumCircuit(n_q)
            for d in range(depth):
                for q in range(n_q):
                    g = np.random.choice(['h','x','y','z','t','s'])
                    getattr(qc, g)(q)
                for _ in range(np.random.randint(1, n_q)):
                    q1, q2 = np.random.choice(n_q, 2, replace=False)
                    qc.cx(q1, q2)
            tot_cancel += count_cancellable_pairs(qc)
            tot_gates += qc.size()
            greedy_reds.append(greedy.optimize(qc).reduction)
        avg_g = tot_gates / 10
        avg_c = tot_cancel / 10
        avg_gr = np.mean(greedy_reds)
        print(f"  n={n_q}, d={depth}: avg_gates={avg_g:.0f}, adjacent_pairs={avg_c:.1f}, greedy_red={avg_gr:.2%}")

print("\n" + "=" * 70)
print("ANALYSIS 2: SA aggressive (1000 iters) vs Greedy")
print("=" * 70)

for seed in [42, 123, 456]:
    np.random.seed(seed)
    qc = QuantumCircuit(5)
    for d in range(20):
        for q in range(5):
            g = np.random.choice(['h','x','y','z','t','s'])
            getattr(qc, g)(q)
        for _ in range(np.random.randint(1, 5)):
            q1, q2 = np.random.choice(5, 2, replace=False)
            qc.cx(q1, q2)
    orig = qc.size()
    r_g = greedy.optimize(qc)
    r_sa = SimulatedAnnealingOptimizer(max_iterations=1000, initial_temp=10.0, cooling_rate=0.999).optimize(qc)
    r_ga = GeneticAlgorithmOptimizer(population_size=30, generations=30, mutation_rate=0.3).optimize(qc)
    print(f"  seed={seed} orig={orig}: Greedy {r_g.reduction:.2%}({r_g.optimized_size}g), "
          f"SA {r_sa.reduction:.2%}({r_sa.optimized_size}g {r_sa.runtime_seconds:.1f}s), "
          f"GA {r_ga.reduction:.2%}({r_ga.optimized_size}g {r_ga.runtime_seconds:.1f}s)")
