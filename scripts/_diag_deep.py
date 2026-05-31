
import sys, copy, time
sys.path.insert(0, "D:/Desktop/Q-research")
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction
from src.optimisation.optimizers_v2 import (
    SimulatedAnnealingOptimizer, 
    GeneticAlgorithmOptimizer,
    GreedyGateCancellation,
    BaseOptimizer
)

# ===== ANALYSIS 1: How many cancellable pairs exist in typical random circuits? =====
print("=" * 70)
print("ANALYSIS 1: Counting cancellable pairs in random circuits")
print("=" * 70)

def count_cancellable_pairs(circuit):
    """Count adjacent inverse gate pairs (same qubit)"""
    count = 0
    for i in range(len(circuit.data) - 1):
        inst1, inst2 = circuit.data[i], circuit.data[i+1]
        q1 = tuple(sorted(q._index for q in inst1.qubits))
        q2 = tuple(sorted(q._index for q in inst2.qubits))
        if q1 != q2:
            continue
        g1, g2 = inst1.operation.name, inst2.operation.name
        if g1 == g2 and g1 in ('h','x','y','z','cx','cz','swap'):
            count += 1
        elif (g1 == 't' and g2 == 'tdg') or (g1 == 'tdg' and g2 == 't'):
            count += 1
        elif (g1 == 's' and g2 == 'sdg') or (g1 == 'sdg' and g2 == 's'):
            count += 1
    return count

def count_commuting_pairs(circuit):
    """Count adjacent commuting gate pairs (different qubits)"""
    count = 0
    for i in range(len(circuit.data) - 1):
        inst1, inst2 = circuit.data[i], circuit.data[i+1]
        q1 = set(q._index for q in inst1.qubits)
        q2 = set(q._index for q in inst2.qubits)
        if q1.isdisjoint(q2):
            count += 1
    return count

# Test across multiple qubit counts and depths
for n_q in [3, 5, 7]:
    for depth in [10, 20, 30]:
        totals_cancel = 0
        totals_commute = 0
        totals_gates = 0
        for seed in range(10):
            np.random.seed(seed)
            qc = QuantumCircuit(n_q)
            for d in range(depth):
                for q in range(n_q):
                    g = np.random.choice(['h','x','y','z','t','s','rx','ry','rz'])
                    if g in ('rx','ry','rz'):
                        getattr(qc, g)(q, np.random.uniform(0, 2*np.pi))
                    else:
                        getattr(qc, g)(q)
                for _ in range(np.random.randint(1, n_q)):
                    q1, q2 = np.random.choice(n_q, 2, replace=False)
                    qc.cx(q1, q2)
            totals_cancel += count_cancellable_pairs(qc)
            totals_commute += count_commuting_pairs(qc)
            totals_gates += qc.size()
        
        avg_gates = totals_gates / 10
        avg_cancel = totals_cancel / 10
        avg_commute = totals_commute / 10
        max_possible_reduction = (avg_cancel * 2) / avg_gates  # Each pair removes 2 gates
        print(f"  n={n_q}, d={depth}: avg_gates={avg_gates:.0f}, cancellable_pairs={avg_cancel:.1f}, "
              f"commuting_pairs={avg_commute:.1f}, max_adjacent_reduction={max_possible_reduction:.1%}")

# ===== ANALYSIS 2: The REAL question - can SWAP/COMMUTATION enable NEW cancellations? =====
print("\n" + "=" * 70)
print("ANALYSIS 2: Can commutation bring non-adjacent inverses together?")
print("=" * 70)

# Build a circuit where H(0) and H(0) are separated by a gate on q(1)
# If we can commute the q(1) gate past one H, we can cancel the Hs
qc = QuantumCircuit(2)
qc.h(0)
qc.z(1)  # Disjoint qubit - can commute past
qc.h(0)  # Same as first H(0) - should cancel after commutation

greedy = GreedyGateCancellation(max_iterations=100)
sa = SimulatedAnnealingOptimizer(max_iterations=500, initial_temp=5.0, cooling_rate=0.999)

r_greedy = greedy.optimize(qc)
r_sa = sa.optimize(qc)

print(f"  Circuit: H(0)-Z(1)-H(0) — 3 gates, can be reduced to Z(1) — 1 gate (66% reduction)")
print(f"  Greedy: reduction={r_greedy.reduction:.2%}, gates={r_greedy.optimized_size}")
print(f"  SA:     reduction={r_sa.reduction:.2%}, gates={r_sa.optimized_size}, iters={r_sa.iterations}")

# ===== ANALYSIS 3: SA with aggressive parameters =====
print("\n" + "=" * 70)
print("ANALYSIS 3: SA with aggressive parameters (1000 iterations)")
print("=" * 70)

np.random.seed(42)
qc_rand = QuantumCircuit(5)
for d in range(15):
    for q in range(5):
        g = np.random.choice(['h','x','y','z','t','s'])
        getattr(qc_rand, g)(q)
    for _ in range(np.random.randint(1, 5)):
        q1, q2 = np.random.choice(5, 2, replace=False)
        qc_rand.cx(q1, q2)

print(f"Original: {qc_rand.size()} gates")

# Very aggressive SA
sa_aggressive = SimulatedAnnealingOptimizer(
    max_iterations=1000, initial_temp=10.0, cooling_rate=0.999
)
r = sa_aggressive.optimize(qc_rand)
print(f"SA (1000 iters, T0=10, alpha=0.999): reduction={r.reduction:.2%}, fidelity={r.fidelity:.4f}, "
      f"success={r.success}, gates={r.optimized_size}, runtime={r.runtime_seconds:.1f}s")

# Greedy for comparison
r_g = greedy.optimize(qc_rand)
print(f"Greedy (100 iters): reduction={r_g.reduction:.2%}, fidelity={r_g.fidelity:.4f}, "
      f"success={r_g.success}, gates={r_g.optimized_size}, runtime={r_g.runtime_seconds:.1f}s")

# ===== ANALYSIS 4: The FUNDAMENTAL problem with SA move set =====
print("\n" + "=" * 70)
print("ANALYSIS 4: Move set bottleneck")
print("=" * 70)

# Count how often each move type actually fires
sa_diag = SimulatedAnnealingOptimizer(max_iterations=500, initial_temp=5.0, cooling_rate=0.999)
c = copy.deepcopy(qc_rand)

move_stats = {"REMOVAL": 0, "SWAP": 0, "COMMUTATION": 0, "INSERTION": 0, "FALLBACK": 0}
move_effects = {"REMOVAL": [], "SWAP": [], "COMMUTATION": [], "INSERTION": [], "FALLBACK": []}

for i in range(200):
    # Try each move type in sequence and record which one fires
    moves = [
        ("REMOVAL", sa_diag._move_removal),
        ("SWAP", sa_diag._move_swap),
        ("COMMUTATION", sa_diag._move_commutation),
        ("INSERTION", sa_diag._move_insertion),
    ]
    np.random.shuffle(moves)
    
    found = False
    for name, fn in moves:
        result = fn(c)
        if result is not None:
            move_stats[name] += 1
            move_effects[name].append(result.size() - c.size())
            c = result
            found = True
            break
    if not found:
        move_stats["FALLBACK"] += 1

print("Move type distribution (200 steps):")
for name, count in move_stats.items():
    if move_effects[name]:
        avg_effect = np.mean(move_effects[name])
        print(f"  {name}: {count} times ({count/200:.0%}), avg gate change: {avg_effect:+.1f}")
    else:
        print(f"  {name}: {count} times ({count/200:.0%})")

# ===== ANALYSIS 5: What % of random circuit gates are adjacent cancellable? =====
print("\n" + "=" * 70)
print("ANALYSIS 5: Theoretical maximum from adjacent-only cancellation")
print("=" * 70)
print("This tells us the ceiling of what ANY optimizer using only")
print("adjacent cancellation (without commutation rewriting) can achieve.")

for n_q in [3, 5, 7]:
    total_reduction = 0
    for seed in range(20):
        np.random.seed(seed)
        qc = QuantumCircuit(n_q)
        for d in range(20):
            for q in range(n_q):
                g = np.random.choice(['h','x','y','z','t','s'])
                getattr(qc, g)(q)
            for _ in range(np.random.randint(1, n_q)):
                q1, q2 = np.random.choice(n_q, 2, replace=False)
                qc.cx(q1, q2)
        
        r = greedy.optimize(qc)
        total_reduction += r.reduction
    
    avg_red = total_reduction / 20
    print(f"  n={n_q}: Greedy achieves avg {avg_red:.2%} gate reduction on random circuits")
    print(f"    → To reach 20%, need {0.20/avg_red:.0f}x more reduction (impossible with adjacent-only)")
