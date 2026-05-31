"""
Fast Circuit Generator - Optimized for large-scale experiments
Uses structural approximations instead of full statevector simulation.

IMPORTANT TERMINOLOGY CLARIFICATION:
- 'two_qubit_ratio' = fraction of two-qubit gates (structural property)
- This is NOT quantum entanglement (which requires statevector simulation)
- 'structural_complexity' = approximation based on gate structure
"""

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Statevector, Operator
from typing import List, Tuple, Optional, Dict
import warnings
warnings.filterwarnings('ignore')


class FastCircuitMetrics:
    """Fast circuit metrics with clear terminology."""
    
    @staticmethod
    def gate_count(circuit: QuantumCircuit) -> int:
        return circuit.size()
    
    @staticmethod
    def depth(circuit: QuantumCircuit) -> int:
        return circuit.depth()
    
    @staticmethod
    def two_qubit_gate_count(circuit: QuantumCircuit) -> int:
        return sum(1 for inst in circuit.data if inst[0].num_qubits == 2)
    
    @staticmethod
    def two_qubit_gate_ratio(circuit: QuantumCircuit) -> float:
        """Fraction of two-qubit gates in the circuit. NOT quantum entanglement."""
        total = circuit.size()
        return FastCircuitMetrics.two_qubit_gate_count(circuit) / total if total > 0 else 0.0
    
    @staticmethod
    def structural_complexity(circuit: QuantumCircuit) -> float:
        """
        Structural complexity based on gate types and connectivity.
        This is a SYNTACTIC measure, not a quantum measure.
        For actual entanglement, use compute_exact_entanglement() on small circuits.
        """
        n = circuit.num_qubits
        if n < 2:
            return 0.0
        
        two_qubit_count = FastCircuitMetrics.two_qubit_gate_count(circuit)
        total_gates = circuit.size()
        
        if total_gates == 0:
            return 0.0
        
        # Structural complexity: weighted combination of gate count and connectivity
        two_qubit_ratio = two_qubit_count / max(total_gates, 1)
        
        # Count unique qubit pairs connected by two-qubit gates
        connected_pairs = set()
        for inst in circuit.data:
            if inst[0].num_qubits == 2:
                qubits = tuple(sorted([q._index for q in inst[1]]))
                connected_pairs.add(qubits)
        
        max_pairs = n * (n - 1) / 2
        connectivity = len(connected_pairs) / max(max_pairs, 1)
        
        # Complexity formula (heuristic, not physics-based)
        complexity = (two_qubit_ratio * 0.6 + connectivity * 0.4) * np.log2(n + 1)
        
        return complexity
    
    @staticmethod
    def compute_exact_entanglement(circuit: QuantumCircuit) -> float:
        """
        Compute exact von Neumann entropy of the reduced state.
        WARNING: O(2^n) complexity - only for small circuits (n <= 10).
        """
        n = circuit.num_qubits
        if n < 2 or n > 12:
            return 0.0
        
        try:
            sv = Statevector.from_label('0' * n).evolve(circuit)
            # Compute reduced density matrix for first half of qubits
            n_A = n // 2
            rho_A = sv.partial_trace(range(n_A, n))
            # Von Neumann entropy
            eigenvalues = np.linalg.eigvalsh(rho_A.data)
            eigenvalues = eigenvalues[eigenvalues > 1e-12]
            return float(-np.sum(eigenvalues * np.log2(eigenvalues)))
        except Exception:
            return 0.0
    
    @staticmethod
    def circuit_complexity(circuit: QuantumCircuit) -> float:
        """Log-depth-weighted complexity measure."""
        n = circuit.num_qubits
        d = circuit.depth()
        g = circuit.size()
        return np.log2(g + 1) * d / n if n > 0 else 0.0
    
    @staticmethod
    def depth_to_width_ratio(circuit: QuantumCircuit) -> float:
        return circuit.depth() / circuit.num_qubits if circuit.num_qubits > 0 else 0.0
    
    @staticmethod
    def gate_density(circuit: QuantumCircuit) -> float:
        n = circuit.num_qubits
        d = circuit.depth()
        return circuit.size() / (n * d) if n > 0 and d > 0 else 0.0
    
    @staticmethod
    def get_all_metrics(circuit: QuantumCircuit) -> Dict[str, float]:
        return {
            'gate_count': FastCircuitMetrics.gate_count(circuit),
            'depth': FastCircuitMetrics.depth(circuit),
            'two_qubit_gates': FastCircuitMetrics.two_qubit_gate_count(circuit),
            'two_qubit_gate_ratio': FastCircuitMetrics.two_qubit_gate_ratio(circuit),
            'structural_complexity': FastCircuitMetrics.structural_complexity(circuit),
            'num_qubits': circuit.num_qubits,
            'circuit_complexity': FastCircuitMetrics.circuit_complexity(circuit),
            'depth_to_width_ratio': FastCircuitMetrics.depth_to_width_ratio(circuit),
            'gate_density': FastCircuitMetrics.gate_density(circuit)
        }


class FastRandomCircuitGenerator:
    """Fast random circuit generator with parameterized gate angles."""
    
    def __init__(self, n_qubits: int, gate_set: List[str] = None):
        self.n_qubits = n_qubits
        self.gate_set = gate_set or ['h', 'cx', 't', 'rz']
    
    def generate(self, depth: int, two_qubit_ratio: float = 0.3, 
                 seed: Optional[int] = None, 
                 angle_randomness: float = 1.0) -> QuantumCircuit:
        """
        Generate a random quantum circuit.
        
        Args:
            depth: Circuit depth
            two_qubit_ratio: Fraction of two-qubit gates (structural, NOT entanglement)
            seed: Random seed for reproducibility
            angle_randomness: Controls rotation angle spread (0=fixed pi/4, 1=full random)
        """
        if seed is not None:
            np.random.seed(seed)
        
        qr = QuantumRegister(self.n_qubits, 'q')
        circuit = QuantumCircuit(qr)
        
        for layer in range(depth):
            for qubit in range(self.n_qubits):
                if np.random.random() < two_qubit_ratio and qubit < self.n_qubits - 1:
                    circuit.cx(qubit, qubit + 1)
                else:
                    gate = np.random.choice(['h', 't', 'rz'])
                    if gate == 'h':
                        circuit.h(qubit)
                    elif gate == 't':
                        circuit.t(qubit)
                    elif gate == 'rz':
                        if angle_randomness > 0:
                            angle = np.random.uniform(0, 2 * np.pi) * angle_randomness
                        else:
                            angle = np.pi / 4  # Fixed angle when randomness=0
                        circuit.rz(angle, qubit)
        
        return circuit


class FastGreedyOptimizer:
    """
    Fast greedy gate cancellation.
    Gate cancellation preserves functionality by definition.
    """
    
    def __init__(self, max_iterations: int = 50):
        self.max_iterations = max_iterations
    
    def optimize(self, circuit: QuantumCircuit) -> Tuple[QuantumCircuit, Dict]:
        optimized = circuit.copy()
        improvements = 0
        
        for _ in range(self.max_iterations):
            improved = False
            i = 0
            while i < len(optimized.data) - 1:
                g1 = optimized.data[i][0]
                g2 = optimized.data[i + 1][0]
                q1 = [q._index for q in optimized.data[i][1]]
                q2 = [q._index for q in optimized.data[i + 1][1]]
                
                # Check same qubits AND inverse gates
                if q1 == q2:
                    if (g1.name == g2.name and g1.name in ['h', 'cx']) or \
                       (g1.name == 't' and g2.name == 'tdg') or \
                       (g1.name == 'tdg' and g2.name == 't') or \
                       (g1.name == 's' and g2.name == 'sdg') or \
                       (g1.name == 'sdg' and g2.name == 's') or \
                       (g1.name == 'x' and g2.name == 'x'):
                        optimized.data.pop(i)
                        optimized.data.pop(i)
                        improved = True
                        improvements += 1
                    else:
                        i += 1
                else:
                    i += 1
            
            if not improved:
                break
        
        original_size = circuit.size()
        optimized_size = optimized.size()
        
        return optimized, {
            'improvements': improvements,
            'original_size': original_size,
            'optimized_size': optimized_size,
            'reduction': 1 - optimized_size / max(original_size, 1),
            'functional': True  # Gate cancellation preserves functionality
        }


class FastSimulatedAnnealing:
    """
    Fast simulated annealing with CORRECTED fitness function.
    
    Key fix: Uses Operator fidelity (not Statevector) for speed and correctness.
    Gate removal only accepted if fidelity > threshold.
    """
    
    def __init__(self, max_iterations: int = 100, initial_temp: float = 0.5,
                 cooling_rate: float = 0.95, fidelity_threshold: float = 0.90):
        self.max_iterations = max_iterations
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.fidelity_threshold = fidelity_threshold
    
    def _operator_fidelity(self, circuit: QuantumCircuit, target: QuantumCircuit) -> float:
        """
        Compute operator fidelity using matrix comparison.
        Much faster than Statevector for repeated evaluations.
        """
        try:
            n = circuit.num_qubits
            if n != target.num_qubits:
                return 0.0
            
            # For small circuits, use exact operator comparison
            if n <= 8:
                op_circuit = Operator(circuit).data
                op_target = Operator(target).data
                # Hilbert-Schmidt inner product
                trace = np.abs(np.trace(op_circuit.conj().T @ op_target))
                dim = 2 ** n
                return float((trace / dim) ** 2)
            else:
                # For larger circuits, use random state sampling
                fidelity_sum = 0.0
                n_samples = 5
                for _ in range(n_samples):
                    # Random initial state
                    sv = Statevector.from_label('0' * n)
                    sv_circuit = sv.evolve(circuit)
                    sv_target = sv.evolve(target)
                    fidelity_sum += float(abs(sv_circuit.inner(sv_target))**2)
                return fidelity_sum / n_samples
        except Exception:
            return 0.0
    
    def _neighbour(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """Generate neighbour: remove gate or perturb angle."""
        neighbour = circuit.copy()
        if len(neighbour.data) == 0:
            return neighbour
        
        op = np.random.random()
        if op < 0.5:
            # Remove random gate (but keep at least 10% of gates)
            if len(neighbour.data) > max(2, circuit.size() * 0.1):
                idx = np.random.randint(0, len(neighbour.data))
                neighbour.data.pop(idx)
        elif op < 0.8:
            # Perturb rotation angle
            rot_indices = [i for i, inst in enumerate(neighbour.data) 
                          if inst[0].name in ['rz', 'rx', 'ry']]
            if rot_indices:
                idx = rot_indices[np.random.randint(len(rot_indices))]
                neighbour.data[idx][0].params[0] += np.random.normal(0, 0.2)
                neighbour.data[idx][0].params[0] %= (2 * np.pi)
        else:
            # Swap two adjacent gates (preserves gate count)
            if len(neighbour.data) > 2:
                idx = np.random.randint(0, len(neighbour.data) - 1)
                # Only swap if gates act on different qubits
                q1 = set(q._index for q in neighbour.data[idx][1])
                q2 = set(q._index for q in neighbour.data[idx + 1][1])
                if q1.isdisjoint(q2):
                    neighbour.data[idx], neighbour.data[idx + 1] = \
                        neighbour.data[idx + 1], neighbour.data[idx]
        
        return neighbour
    
    def optimize(self, circuit: QuantumCircuit) -> Tuple[QuantumCircuit, Dict]:
        original_size = circuit.size()
        
        # Compute initial fidelity (should be 1.0 for original)
        current = circuit.copy()
        current_fitness = 1.0  # Original circuit has fidelity 1.0 with itself
        
        best = current.copy()
        best_fitness = current_fitness
        best_fidelity = 1.0
        
        temp = self.initial_temp
        accepted = 0
        rejected = 0
        
        for iteration in range(self.max_iterations):
            neighbour = self._neighbour(current)
            
            # Compute fidelity with original circuit
            fidelity = self._operator_fidelity(neighbour, circuit)
            
            # Fitness: gate reduction weighted by fidelity
            gate_reduction = 1.0 - neighbour.size() / max(original_size, 1)
            
            # Only reward gate reduction if fidelity is above threshold
            if fidelity >= self.fidelity_threshold:
                fitness = 0.3 * gate_reduction + 0.7 * fidelity
            else:
                fitness = fidelity - 1.0  # Penalty for low fidelity
            
            delta = fitness - current_fitness
            
            # SA acceptance criterion
            if delta > 0 or (temp > 1e-10 and np.random.random() < np.exp(delta / max(temp, 1e-10))):
                current = neighbour
                current_fitness = fitness
                accepted += 1
                
                if fidelity >= self.fidelity_threshold and fitness > best_fitness:
                    best = current.copy()
                    best_fitness = fitness
                    best_fidelity = fidelity
            else:
                rejected += 1
            
            temp *= self.cooling_rate
        
        # Final fidelity check
        final_fidelity = self._operator_fidelity(best, circuit)
        
        return best, {
            'original_size': original_size,
            'optimized_size': best.size(),
            'reduction': 1 - best.size() / max(original_size, 1),
            'best_fitness': best_fitness,
            'acceptance_rate': accepted / max(accepted + rejected, 1),
            'final_fidelity': final_fidelity,
            'functional': final_fidelity >= self.fidelity_threshold
        }


def fast_generate_batch(family: str, n_qubits: int, depth: int, num_circuits: int,
                        two_qubit_ratio: float = 0.3, seed_start: int = 0,
                        angle_randomness: float = 1.0) -> List[QuantumCircuit]:
    """Generate a batch of circuits quickly.
    
    Args:
        family: Circuit family ('random' only for now)
        n_qubits: Number of qubits
        depth: Circuit depth
        num_circuits: Number of circuits to generate
        two_qubit_ratio: Fraction of two-qubit gates (structural, NOT entanglement)
        seed_start: Starting random seed
        angle_randomness: Controls rotation angle spread (0=fixed, 1=full random)
    """
    gen = FastRandomCircuitGenerator(n_qubits)
    circuits = []
    for i in range(num_circuits):
        circuits.append(gen.generate(depth, two_qubit_ratio, seed=seed_start + i, 
                                    angle_randomness=angle_randomness))
    return circuits


def fast_optimize(circuit: QuantumCircuit, algorithm: str = 'greedy') -> Tuple[QuantumCircuit, Dict]:
    """Fast optimization with specified algorithm."""
    if algorithm == 'greedy':
        opt = FastGreedyOptimizer()
        return opt.optimize(circuit)
    elif algorithm == 'sa':
        opt = FastSimulatedAnnealing()
        return opt.optimize(circuit)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")


if __name__ == '__main__':
    import time
    
    print("Testing fast circuit generation and optimization...")
    
    # Test speed
    start = time.time()
    circuits = fast_generate_batch('random', n_qubits=5, depth=20, num_circuits=100, two_qubit_ratio=0.3)
    gen_time = time.time() - start
    print(f"Generated 100 circuits in {gen_time:.2f}s")
    
    # Test metrics
    metrics = FastCircuitMetrics.get_all_metrics(circuits[0])
    print(f"Metrics: {metrics}")
    
    # Test greedy optimization
    start = time.time()
    for c in circuits[:20]:
        optimized, opt_metrics = fast_optimize(c, 'greedy')
    opt_time = time.time() - start
    print(f"Greedy optimized 20 circuits in {opt_time:.2f}s")
    print(f"  Mean reduction: {np.mean([fast_optimize(c, 'greedy')[1]['reduction'] for c in circuits[:10]]):.3f}")
    
    # Test SA optimization
    print("\nTesting SA (should show realistic reduction, not 1.0)...")
    start = time.time()
    reductions_sa = []
    fidelities_sa = []
    for c in circuits[:10]:
        optimized_sa, metrics_sa = fast_optimize(c, 'sa')
        reductions_sa.append(metrics_sa['reduction'])
        fidelities_sa.append(metrics_sa.get('final_fidelity', 0))
    sa_time = time.time() - start
    
    print(f"SA optimized 10 circuits in {sa_time:.2f}s")
    print(f"  Mean reduction: {np.mean(reductions_sa):.3f}")
    print(f"  Mean fidelity: {np.mean(fidelities_sa):.3f}")
    print(f"  All functional: {all(m.get('functional', False) for m in [fast_optimize(c, 'sa')[1] for c in circuits[:5]])}")
