"""Novel optimizer prototype + benchmark"""
import sys, copy, time, numpy as np
sys.path.insert(0, "D:/Desktop/Q-research")
from qiskit import QuantumCircuit
from src.optimisation.optimizers_v2 import (
    BaseOptimizer, OptimizationResult,
    SimulatedAnnealingOptimizer, GreedyGateCancellation
)

class HybridCommuteRewrite(BaseOptimizer):
    """
    Novel optimizer: Qubit-Aware Commutation-Rewriting + Hybrid Greedy-SA.
    
    KEY INSIGHT from diagnosis: Adjacent-only cancellation caps at ~4%.
    To exceed this, we need commutation rewriting that brings 
    non-adjacent inverses together through gate reordering.
    """
    def __init__(self, max_iterations=100, fidelity_threshold=0.99,
                 success_reduction=0.20, sa_prob=0.15):
        super().__init__(fidelity_threshold, success_reduction)
        self.max_iterations = max_iterations
        self.sa_prob = sa_prob

    def optimize(self, circuit, target=None):
        start = time.time()
        if target is None:
            target = circuit
        original_size = circuit.size()
        
        best = self._full_pass(copy.deepcopy(circuit), target)
        best_fitness = self._fitness(best, target)

        for it in range(self.max_iterations):
            if np.random.random() < self.sa_prob:
                current = self._sa_perturb(copy.deepcopy(best), target)
            else:
                current = copy.deepcopy(best)
            current = self._commute_rewrite(current, target)
            current = self._greedy_pass(current)
            
            fitness = self._fitness(current, target)
            if fitness > best_fitness:
                best = current
                best_fitness = fitness
        
        runtime = time.time() - start
        fidelity = self.calculate_fidelity(best, target)
        reduction = 1.0 - best.size() / original_size if original_size > 0 else 0.0
        success = self._is_success(reduction, fidelity)
        return OptimizationResult(
            optimized_circuit=best,
            original_size=original_size,
            optimized_size=best.size(),
            fidelity=fidelity,
            iterations=it + 1,
            runtime_seconds=runtime,
            success=success,
            metadata={'algorithm': 'hybrid_commute_rewrite'}
        )

    def _are_inverse(self, inst1, inst2):
        q1 = tuple(sorted(q._index for q in inst1.qubits))
        q2 = tuple(sorted(q._index for q in inst2.qubits))
        if q1 != q2:
            return False
        g1, g2 = inst1.operation.name, inst2.operation.name
        if g1 == g2 and g1 in ('h','x','y','z','cx','cz','swap'):
            return True
        if (g1=='t' and g2=='tdg') or (g1=='tdg' and g2=='t'):
            return True
        if (g1=='s' and g2=='sdg') or (g1=='sdg' and g2=='s'):
            return True
        return False

    def _greedy_pass(self, circuit):
        for _ in range(50):
            improved = False
            i = 0
            while i < len(circuit.data) - 1:
                if self._are_inverse(circuit.data[i], circuit.data[i+1]):
                    circuit.data.pop(i)
                    circuit.data.pop(i)
                    improved = True
                else:
                    i += 1
            if not improved:
                break
        return circuit

    def _commute_rewrite(self, circuit, target):
        """COMMUTATION REWRITING: actively reorder gates to bring non-adjacent inverses together."""
        changed = True
        pass_num = 0
        while changed and pass_num < 20:
            changed = False
            pass_num += 1
            i = 0
            while i < len(circuit.data) - 1:
                inst1, inst2 = circuit.data[i], circuit.data[i+1]
                q1 = set(q._index for q in inst1.qubits)
                q2 = set(q._index for q in inst2.qubits)
                if q1.isdisjoint(q2):
                    test = copy.deepcopy(circuit)
                    test.data[i], test.data[i+1] = test.data[i+1], test.data[i]
                    if self.calculate_fidelity(test, target) >= self.fidelity_threshold:
                        circuit = test
                        changed = True
                        if i > 0 and self._are_inverse(circuit.data[i-1], circuit.data[i]):
                            circuit.data.pop(i-1)
                            circuit.data.pop(i-1)
                            changed = True
                        break
                i += 1
        return circuit

    def _sa_perturb(self, circuit, target):
        gate = np.random.choice(['h','x','z'])
        q = np.random.randint(0, max(1, circuit.num_qubits))
        pos = np.random.randint(0, max(1, len(circuit.data)))
        insert_circ = QuantumCircuit(circuit.num_qubits)
        getattr(insert_circ, gate)(q)
        getattr(insert_circ, gate)(q)
        neighbor = copy.deepcopy(circuit)
        for j, inst in enumerate(insert_circ.data):
            neighbor.data.insert(pos + j, copy.deepcopy(inst))
        if self.calculate_fidelity(neighbor, target) >= self.fidelity_threshold:
            return neighbor
        return circuit

    def _full_pass(self, circuit, target):
        circuit = self._commute_rewrite(circuit, target)
        circuit = self._greedy_pass(circuit)
        return circuit


# ===== BENCHMARK =====
greedy = GreedyGateCancellation(max_iterations=100)
sa = SimulatedAnnealingOptimizer(max_iterations=500, initial_temp=5.0, cooling_rate=0.999)
hybrid = HybridCommuteRewrite(max_iterations=50, sa_prob=0.15)

results = []
for seed in [42, 123, 456, 789, 1010]:
    for n_q in [3, 5, 7]:
        np.random.seed(seed)
        qc = QuantumCircuit(n_q)
        for d in range(20):
            for q in range(n_q):
                g = np.random.choice(['h','x','y','z','t','s'])
                getattr(qc, g)(q)
            for _ in range(np.random.randint(1, n_q)):
                q1, q2 = np.random.choice(n_q, 2, replace=False)
                qc.cx(q1, q2)
        orig = qc.size()
        r_g = greedy.optimize(qc)
        r_sa = sa.optimize(qc)
        r_h = hybrid.optimize(qc)
        results.append({'seed': seed, 'n': n_q, 'orig': orig,
                        'greedy_red': r_g.reduction, 'greedy_gates': r_g.optimized_size,
                        'sa_red': r_sa.reduction, 'sa_gates': r_sa.optimized_size,
                        'hybrid_red': r_h.reduction, 'hybrid_gates': r_h.optimized_size,
                        'hybrid_time': r_h.runtime_seconds})

greedy_avg = np.mean([r['greedy_red'] for r in results])
sa_avg = np.mean([r['sa_red'] for r in results])
hybrid_avg = np.mean([r['hybrid_red'] for r in results])
hybrid_win = sum(1 for r in results if r['hybrid_red'] > r['greedy_red'])
hybrid_significant = sum(1 for r in results if r['hybrid_red'] - r['greedy_red'] > 0.01)

print("=" * 70)
print("NOVEL ALGORITHM RESULTS")
print("=" * 70)
print(f"\nAggregate across {len(results)} test cases:")
print(f"  Greedy:   avg = {greedy_avg:.2%}  (baseline)")
print(f"  SA:       avg = {sa_avg:.2%}  ({sa_avg/greedy_avg:.2f}x)")
print(f"  Hybrid:   avg = {hybrid_avg:.2%}  ({hybrid_avg/greedy_avg:.2f}x)")
print(f"  Hybrid beats Greedy: {hybrid_win}/{len(results)} cases")
print(f"  Hybrid > Greedy by >1%: {hybrid_significant}/{len(results)} cases")

print(f"\n  {'seed':>6}  {'n':>2}  {'orig':>5}  {'Greedy':>8}  {'SA':>8}  {'Hybrid':>8}  {'diff':>7}")
print("  " + "-" * 60)
for r in results:
    diff = r['hybrid_red'] - r['greedy_red']
    diff_str = f"+{diff:.2%}" if diff >= 0 else f"{diff:.2%}"
    win = "★" if diff > 0 else " "
    print(f"  {r['seed']:>6}  {r['n']:>2}  {r['orig']:>5}  "
          f"{r['greedy_red']:>6.2%}  {r['sa_red']:>6.2%}  "
          f"{r['hybrid_red']:>6.2%}  {diff_str} {win}")

diffs = [r['hybrid_red'] - r['greedy_red'] for r in results]
t = np.mean(diffs) / (np.std(diffs) / np.sqrt(len(diffs)))
print(f"\n  t-test (Hybrid vs Greedy): t={t:.2f}")
print(f"  Mean improvement: {np.mean(diffs):+.2%}, Max: {np.max(diffs):+.2%}")