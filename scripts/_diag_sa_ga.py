
import sys, json, copy, time
sys.path.insert(0, "D:/Desktop/Q-research")

import numpy as np
from qiskit import QuantumCircuit
from src.optimisation.optimizers_v2 import (
    SimulatedAnnealingOptimizer, 
    GeneticAlgorithmOptimizer,
    GreedyGateCancellation,
    BaseOptimizer,
    MoveType
)

results = {}

# ===== TEST 1: Simple circuit with obvious cancellations =====
qc_simple = QuantumCircuit(3)
qc_simple.h(0); qc_simple.h(0)
qc_simple.cx(0,1); qc_simple.cx(0,1)
qc_simple.x(1); qc_simple.x(1)
qc_simple.t(2); qc_simple.tdg(2)

print("=== Simple Circuit ===")
print(f"Original: {qc_simple.size()} gates")

for name, opt_cls, kwargs in [
    ("Greedy", GreedyGateCancellation, {"max_iterations": 100}),
    ("SA", SimulatedAnnealingOptimizer, {"max_iterations": 100, "initial_temp": 1.0, "cooling_rate": 0.99}),
    ("GA", GeneticAlgorithmOptimizer, {"population_size": 10, "generations": 10, "mutation_rate": 0.2}),
]:
    opt = opt_cls(**kwargs)
    r = opt.optimize(qc_simple)
    print(f"  {name}: reduction={r.reduction:.2%}, fidelity={r.fidelity:.4f}, success={r.success}, runtime={r.runtime_seconds:.4f}s")

# ===== TEST 2: Random circuit =====
np.random.seed(42)
n_qubits, depth = 5, 15
qc_rand = QuantumCircuit(n_qubits)
for d in range(depth):
    for q in range(n_qubits):
        g = np.random.choice(['h','x','y','z','t','s'])
        getattr(qc_rand, g)(q)
    for _ in range(np.random.randint(1, n_qubits)):
        q1, q2 = np.random.choice(n_qubits, 2, replace=False)
        qc_rand.cx(q1, q2)

print(f"\n=== Random Circuit ===")
print(f"Original: {qc_rand.size()} gates, {n_qubits} qubits")

for name, opt_cls, kwargs in [
    ("Greedy", GreedyGateCancellation, {"max_iterations": 100}),
    ("SA", SimulatedAnnealingOptimizer, {"max_iterations": 200, "initial_temp": 2.0, "cooling_rate": 0.995}),
    ("GA", GeneticAlgorithmOptimizer, {"population_size": 20, "generations": 20, "mutation_rate": 0.3}),
]:
    opt = opt_cls(**kwargs)
    r = opt.optimize(qc_rand)
    print(f"  {name}: reduction={r.reduction:.2%}, fidelity={r.fidelity:.4f}, success={r.success}, gates={r.optimized_size}/{r.original_size}, runtime={r.runtime_seconds:.4f}s")

# ===== DIAGNOSTIC: Trace SA internal state =====
print("\n=== SA Deep Trace (random circuit) ===")
sa = SimulatedAnnealingOptimizer(max_iterations=200, initial_temp=2.0, cooling_rate=0.995)
target = qc_rand
current = copy.deepcopy(qc_rand)

# Check initial fitness
init_fidelity = sa.calculate_fidelity(current, target)
init_reduction = 1.0 - current.size() / target.size()
init_fitness = sa._fitness(current, target)
print(f"Initial: size={current.size()}, fidelity={init_fidelity:.4f}, fitness={init_fitness:.4f}")

# Check how many valid moves exist
move_counts = {}
for move_type, move_fn in [
    ("REMOVAL", sa._move_removal),
    ("SWAP", sa._move_swap),
    ("COMMUTATION", sa._move_commutation),
    ("INSERTION", sa._move_insertion),
]:
    result = move_fn(current)
    move_counts[move_type] = "available" if result is not None else "none"
print(f"Available moves: {move_counts}")

# Run 30 iterations with tracing
temp = 2.0
improvements = 0
no_change = 0
insert_only = 0

for i in range(30):
    neighbor = sa._generate_neighbor(current)
    n_fitness = sa._fitness(neighbor, target)
    c_fitness = sa._fitness(current, target)
    delta = n_fitness - c_fitness
    
    accepted = False
    if delta > 0:
        current = neighbor
        c_fitness = n_fitness
        improvements += 1
        accepted = True
    elif temp > 1e-8:
        prob = np.exp(delta / temp)
        if np.random.random() < prob:
            current = neighbor
            c_fitness = n_fitness
            accepted = True
        else:
            no_change += 1
    else:
        no_change += 1
    
    n_size = neighbor.size()
    c_size = current.size()
    if i < 10 or accepted:
        print(f"  Iter {i}: size={c_size}, fitness={c_fitness:.4f}, delta={delta:+.4f}, temp={temp:.4f}, accepted={accepted}")
    
    temp *= 0.995

print(f"\nAfter 30 iters: improvements={improvements}, no_change={no_change}")
print(f"Current size: {current.size()}, Original: {qc_rand.size()}")

# ===== KEY DIAGNOSTIC: Check if INSERTION inflates gate count =====
print("\n=== Move Type Analysis ===")
c = copy.deepcopy(qc_rand)
sizes = [c.size()]
for i in range(20):
    new_c = sa._generate_neighbor(c)
    sizes.append(new_c.size())
    if new_c.size() < c.size():
        action = f"SHRANK by {c.size() - new_c.size()}"
    elif new_c.size() > c.size():
        action = f"GREW by {new_c.size() - c.size()} (INSERTION?)"
    else:
        action = "SAME SIZE (SWAP/COMMUTATION)"
    c = new_c
    if i < 10:
        print(f"  Move {i}: size {sizes[-2]}->{sizes[-1]}: {action}")

print(f"\nSize trajectory: {sizes[:15]}...")

# ===== DIAGNOSTIC: What does success_reduction=0.20 mean? =====
print("\n=== Success Threshold Analysis ===")
for opt_name, opt_cls, kwargs in [
    ("Greedy", GreedyGateCancellation, {"max_iterations": 100}),
    ("SA", SimulatedAnnealingOptimizer, {"max_iterations": 200, "initial_temp": 2.0, "cooling_rate": 0.995}),
    ("GA", GeneticAlgorithmOptimizer, {"population_size": 20, "generations": 20}),
]:
    opt = opt_cls(**kwargs)
    r = opt.optimize(qc_rand)
    print(f"  {opt_name}: reduction={r.reduction:.4f}, needed>={opt.success_reduction:.4f}, gap={opt.success_reduction - r.reduction:.4f}")
    print(f"    fidelity={r.fidelity:.4f}, needed>={opt.fidelity_threshold:.4f}")

# ===== CRITICAL: Test with LOWER success threshold =====
print("\n=== Lowering Success Threshold to 5% ===")
for opt_name, opt_cls, kwargs in [
    ("SA-5%", SimulatedAnnealingOptimizer, {"max_iterations": 200, "initial_temp": 2.0, "cooling_rate": 0.995, "success_reduction": 0.05}),
    ("GA-5%", GeneticAlgorithmOptimizer, {"population_size": 20, "generations": 20, "success_reduction": 0.05}),
]:
    opt = opt_cls(**kwargs)
    r = opt.optimize(qc_rand)
    print(f"  {opt_name}: reduction={r.reduction:.2%}, fidelity={r.fidelity:.4f}, success={r.success}")
