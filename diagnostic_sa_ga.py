#!/usr/bin/env python3
"""Diagnostic: Why do SA and GA show 0% success rate?"""
import sys
sys.path.insert(0, "D:/Desktop/Q-research")

import numpy as np
import copy
from qiskit import QuantumCircuit

from src.circuits.generator_v2 import CircuitConfig, CircuitFamily, MetricsCalculator
from src.optimisation.optimizers_v2 import (
    OptimizerType, create_optimizer, SimulatedAnnealingOptimizer, 
    GeneticAlgorithmOptimizer, GreedyGateCancellation,
    _SELF_INVERSE_GATES
)

np.random.seed(42)

# Generate the SAME circuit used in experiments
config = CircuitConfig(
    n_qubits=5,
    depth=15,
    family=CircuitFamily.UNIVERSAL,
    seed=42,  # First trial
    entanglement_density=0.3,
)

metrics_calc = MetricsCalculator()
circuits_data = __import__('src.circuits.generator_v2', fromlist=['generate_circuit_batch']).generate_circuit_batch(config, 1, metrics_calc)
circuit, metrics = circuits_data[0]

print("=" * 70)
print("DIAGNOSTIC: SA/GA 0% Success Rate Investigation")
print("=" * 70)
print(f"\nCircuit: {circuit.num_qubits} qubits, {circuit.size()} gates, depth={circuit.depth()}")
print(f"Gate count: {metrics.gate_count}")

# Count adjacent self-inverse pairs
print("\n" + "=" * 70)
print("1. ANALYZING ADJACENT GATE PAIRS IN ORIGINAL CIRCUIT")
print("=" * 70)

pair_stats = {}
self_inverse_count = 0
commuting_count = 0
disjoint_count = 0

# Create optimizer to use its methods
opt = create_optimizer(OptimizerType.SIMULATED_ANNEALING)

for i in range(len(circuit.data) - 1):
    inst1 = circuit.data[i]
    inst2 = circuit.data[i + 1]
    name1 = inst1.operation.name
    name2 = inst2.operation.name
    
    pair_key = (name1, name2)
    pair_stats[pair_key] = pair_stats.get(pair_key, 0) + 1
    
    is_si = opt._is_self_inverse_pair(circuit, inst1, inst2)
    is_commute = opt._gates_commute(circuit, inst1, inst2)
    is_disjoint = opt._gates_on_disjoint_qubits(circuit, inst1, inst2)
    
    if is_si:
        self_inverse_count += 1
        print(f"  SELF-INVERSE pair at [{i},{i+1}]: {name1}({opt._get_qubit_indices(circuit, inst1)}) - {name2}({opt._get_qubit_indices(circuit, inst2)})")
    if is_commute:
        commuting_count += 1
    if is_disjoint:
        disjoint_count += 1

print(f"\nTotal adjacent pairs: {len(circuit.data) - 1}")
print(f"Self-inverse pairs: {self_inverse_count}")
print(f"Commuting pairs: {commuting_count}")
print(f"Disjoint-qubit pairs: {disjoint_count}")

# Show most common pairs
print("\nMost common adjacent gate pairs:")
top_pairs = sorted(pair_stats.items(), key=lambda x: -x[1])[:15]
for (n1, n2), count in top_pairs:
    print(f"  {n1:8s} + {n2:8s}: {count} times")

# Now check greedy vs SA/GA methods for self-inverse detection
print("\n" + "=" * 70)
print("2. COMPARING GREEDY vs SA/GA SELF-INVERSE DETECTION")
print("=" * 70)

greedy = create_optimizer(OptimizerType.GREEDY)
greedy_pairs = 0
sa_pairs = 0
mismatch_pairs = []

for i in range(len(circuit.data) - 1):
    inst1 = circuit.data[i]
    inst2 = circuit.data[i + 1]
    
    g_result = greedy._are_inverse(inst1, inst2)
    sa_result = opt._is_self_inverse_pair(circuit, inst1, inst2)
    
    if g_result:
        greedy_pairs += 1
    if sa_result:
        sa_pairs += 1
    
    if g_result != sa_result:
        name1 = inst1.operation.name
        name2 = inst2.operation.name
        qubits1_g = tuple(sorted(q._index for q in inst1.qubits))
        qubits2_g = tuple(sorted(q._index for q in inst2.qubits))
        qubits1_sa = opt._get_qubit_indices(circuit, inst1)
        qubits2_sa = opt._get_qubit_indices(circuit, inst2)
        mismatch_pairs.append((i, name1, name2, qubits1_g, qubits2_g, qubits1_sa, qubits2_sa, g_result, sa_result))

print(f"Greedy detects {greedy_pairs} self-inverse pairs")
print(f"SA/GA detects {sa_pairs} self-inverse pairs")
if mismatch_pairs:
    print(f"\nMISMATCHES ({len(mismatch_pairs)}):")
    for idx, n1, n2, q1g, q2g, q1sa, q2sa, gr, sr in mismatch_pairs:
        print(f"  [{idx}] {n1}+{n2}: greedy={gr}, sa/ga={sr}")
        print(f"    greedy qubits: {q1g} vs {q2g}")
        print(f"    sa/ga qubits:  {q1sa} vs {q2sa}")

# Now check what _move_removal finds
print("\n" + "=" * 70)
print("3. TESTING MOVE VALIDITY")
print("=" * 70)

removal_result = opt._move_removal(circuit)
swap_result = opt._move_swap(circuit)
commutation_result = opt._move_commutation(circuit)
insertion_result = opt._move_insertion(circuit)

print(f"_move_removal:     {'SUCCESS' if removal_result else 'FAIL'} (size: {removal_result.size() if removal_result else 'N/A'})")
print(f"_move_swap:        {'SUCCESS' if swap_result else 'FAIL'} (size: {swap_result.size() if swap_result else 'N/A'})")
print(f"_move_commutation: {'SUCCESS' if commutation_result else 'FAIL'} (size: {commutation_result.size() if commutation_result else 'N/A'})")
print(f"_move_insertion:   {'SUCCESS' if insertion_result else 'FAIL'} (size: {insertion_result.size() if insertion_result else 'N/A'})")

# Test fitness values
print("\n" + "=" * 70)
print("4. FITNESS LANDSCAPE ANALYSIS")
print("=" * 70)

target = circuit
original_fitness = opt._fitness(circuit, target)
print(f"Original circuit fitness: {original_fitness:.6f}")

if removal_result:
    rem_fitness = opt._fitness(removal_result, target)
    print(f"After REMOVAL fitness:    {rem_fitness:.6f} (delta = {rem_fitness - original_fitness:+.6f})")

if swap_result:
    swap_fitness = opt._fitness(swap_result, target)
    print(f"After SWAP fitness:       {swap_fitness:.6f} (delta = {swap_fitness - original_fitness:+.6f})")

if insertion_result:
    ins_fitness = opt._fitness(insertion_result, target)
    print(f"After INSERTION fitness:  {ins_fitness:.6f} (delta = {ins_fitness - original_fitness:+.6f})")

# Now run full SA with detailed logging
print("\n" + "=" * 70)
print("5. SA DETAILED TRACE (first 50 iterations)")
print("=" * 70)

# Create a custom SA with verbose output
class VerboseSA(SimulatedAnnealingOptimizer):
    def optimize(self, circuit, target=None):
        if target is None:
            target = circuit
        
        current = copy.deepcopy(circuit)
        current_fitness = self._fitness(current, target)
        best = copy.deepcopy(current)
        best_fitness = current_fitness
        temp = self.initial_temp
        min_temp = 1e-8
        
        print(f"\nIter | Temp     | CurrFit  | BestFit  | NeighFit | Delta   | Accept | MoveType | Size")
        print("-" * 90)
        
        for iteration in range(self.max_iterations):
            neighbor = self._generate_neighbor(current)
            neighbor_fitness = self._fitness(neighbor, target)
            
            delta = neighbor_fitness - current_fitness
            
            # Determine what move was applied
            n_size = neighbor.size()
            c_size = current.size()
            if n_size < c_size:
                move_type = "REMOVAL"
            elif n_size > c_size:
                move_type = "INSERTION"
            else:
                move_type = "SWAP/COMM"
            
            accepted = False
            if delta > 0:
                current = neighbor
                current_fitness = neighbor_fitness
                accepted = True
            elif temp > min_temp:
                acceptance_prob = np.exp(delta / temp)
                if np.random.random() < acceptance_prob:
                    current = neighbor
                    current_fitness = neighbor_fitness
                    accepted = True
            
            if current_fitness > best_fitness:
                best = copy.deepcopy(current)
                best_fitness = current_fitness
            
            temp *= self.cooling_rate
            temp = max(temp, min_temp)
            
            if iteration < 50 or n_size != c_size:
                print(f"{iteration:4d} | {temp:8.5f} | {current_fitness:8.5f} | {best_fitness:8.5f} | {neighbor_fitness:8.5f} | {delta:+7.5f} | {'Y' if accepted else 'N':6s} | {move_type:8s} | {n_size}")
        
        fidelity = self.calculate_fidelity(best, target)
        reduction = 1.0 - best.size() / circuit.size() if circuit.size() > 0 else 0.0
        
        print(f"\nFINAL: best_size={best.size()}, original_size={circuit.size()}, reduction={reduction:.4f}, fidelity={fidelity:.10f}")
        return super().optimize(circuit, target)

# Run verbose SA
print("\n--- Running SA with verbose output ---")
verbose_sa = VerboseSA(max_iterations=100, initial_temp=1.0, cooling_rate=0.995)
np.random.seed(42)  # Reset seed for reproducibility
verbose_sa.optimize(circuit)

# Run full greedy
print("\n" + "=" * 70)
print("6. GREEDY OPTIMIZER TRACE")
print("=" * 70)

greedy = create_optimizer(OptimizerType.GREEDY)
greedy_result = greedy.optimize(circuit)
print(f"Greedy result: {greedy_result.original_size} -> {greedy_result.optimized_size}")
print(f"Reduction: {greedy_result.reduction:.4f}, Fidelity: {greedy_result.fidelity:.10f}")
print(f"Success: {greedy_result.success}")
print(f"Iterations (improvements): {greedy_result.metadata['improvements']}")

# Run SA with default params
print("\n" + "=" * 70)
print("7. SA DEFAULT PARAMS RUN")
print("=" * 70)

sa = create_optimizer(OptimizerType.SIMULATED_ANNEALING)
np.random.seed(42)
sa_result = sa.optimize(circuit)
print(f"SA result: {sa_result.original_size} -> {sa_result.optimized_size}")
print(f"Reduction: {sa_result.reduction:.4f}, Fidelity: {sa_result.fidelity:.10f}")
print(f"Success: {sa_result.success}")

# Run GA with default params
print("\n" + "=" * 70)
print("8. GA DEFAULT PARAMS RUN")
print("=" * 70)

ga = create_optimizer(OptimizerType.GENETIC_ALGORITHM)
np.random.seed(42)
ga_result = ga.optimize(circuit)
print(f"GA result: {ga_result.original_size} -> {ga_result.optimized_size}")
print(f"Reduction: {ga_result.reduction:.4f}, Fidelity: {ga_result.fidelity:.10f}")
print(f"Success: {ga_result.success}")

# Test with MUCH higher iterations
print("\n" + "=" * 70)
print("9. SA WITH 10000 ITERATIONS")
print("=" * 70)

sa_long = SimulatedAnnealingOptimizer(max_iterations=10000, initial_temp=1.0, cooling_rate=0.9999)
np.random.seed(42)
sa_long_result = sa_long.optimize(circuit)
print(f"SA(10000) result: {sa_long_result.original_size} -> {sa_long_result.optimized_size}")
print(f"Reduction: {sa_long_result.reduction:.4f}, Fidelity: {sa_long_result.fidelity:.10f}")
print(f"Success: {sa_long_result.success}")

# Test with very high iterations
print("\n" + "=" * 70)
print("10. SA WITH 100000 ITERATIONS")
print("=" * 70)

sa_very_long = SimulatedAnnealingOptimizer(max_iterations=100000, initial_temp=1.0, cooling_rate=0.99995)
np.random.seed(42)
sa_very_long_result = sa_very_long.optimize(circuit)
print(f"SA(100000) result: {sa_very_long_result.original_size} -> {sa_very_long_result.optimized_size}")
print(f"Reduction: {sa_very_long_result.reduction:.4f}, Fidelity: {sa_very_long_result.fidelity:.10f}")
print(f"Success: {sa_very_long_result.success}")

# Check _fitness hard constraint behavior
print("\n" + "=" * 70)
print("11. FITNESS FUNCTION HARD CONSTRAINT BEHAVIOR")
print("=" * 70)

# The _fitness returns 0.0 if fidelity < 0.99
# But all moves preserve unitary equivalence, so fidelity should be ~1.0
# However, _fitness uses target.size() not original_size
# Let's check what happens if target differs from the original circuit
print(f"Target size (original circuit): {target.size()}")
print(f"Original fitness: {opt._fitness(circuit, target):.6f}")
print(f"  fidelity component: 1.0 * 0.7 = 0.7")
print(f"  reduction component: 0.0 * 0.3 = 0.0")
print(f"  Total: 0.7")

# What if a circuit has size N-2?
test_smaller = copy.deepcopy(circuit)
test_smaller.data.pop(0)  # Remove one gate (will break fidelity)
fidelity_smaller = opt.calculate_fidelity(test_smaller, target)
print(f"\nAfter removing 1 gate (breaking unitary):")
print(f"  Fidelity: {fidelity_smaller:.10f}")
fitness_smaller = opt._fitness(test_smaller, target)
print(f"  Fitness: {fitness_smaller:.6f}")
print(f"  (Hard constraint: fitness=0.0 since fidelity < 0.99)")

# What about removing an H-H pair?
print("\n" + "=" * 70)
print("12. CHECKING GA POPULATION DIVERSITY")
print("=" * 70)

ga_opt = create_optimizer(OptimizerType.GENETIC_ALGORITHM)
np.random.seed(42)

# Check initial population fitnesses
target_ga = circuit
pop = [copy.deepcopy(circuit)]
for _ in range(9):
    individual = copy.deepcopy(circuit)
    num_moves = np.random.randint(1, 4)
    for _ in range(num_moves):
        individual = ga_opt._generate_neighbor(individual)
    pop.append(individual)

print("Initial GA population:")
for i, ind in enumerate(pop):
    f = ga_opt._fitness(ind, target_ga)
    fid = ga_opt.calculate_fidelity(ind, target_ga)
    print(f"  Individual {i}: size={ind.size()}, fidelity={fid:.10f}, fitness={f:.6f}")
