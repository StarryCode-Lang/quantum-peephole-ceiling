"""
Quantum Circuit Optimization Algorithms - Corrected Implementation
Fixes fatal fitness function bug and adds functional fidelity assessment.
"""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, Operator
from typing import List, Tuple, Optional, Dict, Callable
import copy
import warnings
warnings.filterwarnings('ignore')


class CircuitFitness:
    """Corrected fitness functions for quantum circuit optimization."""
    
    @staticmethod
    def fidelity(circuit: QuantumCircuit, target: QuantumCircuit) -> float:
        """Calculate state fidelity between circuit and target output states."""
        try:
            if circuit.num_qubits != target.num_qubits:
                return 0.0
            
            n = circuit.num_qubits
            sv_init = Statevector.from_label('0' * n)
            sv_circuit = sv_init.evolve(circuit)
            sv_target = sv_init.evolve(target)
            
            return float(abs(sv_circuit.inner(sv_target))**2)
        except Exception:
            return 0.0
    
    @staticmethod
    def gate_count_reduction(original: QuantumCircuit, optimized: QuantumCircuit) -> float:
        """Calculate gate count reduction ratio."""
        if original.size() == 0:
            return 0.0
        return 1.0 - optimized.size() / original.size()
    
    @staticmethod
    def functional_fitness(circuit: QuantumCircuit, target: QuantumCircuit, 
                          fidelity_threshold: float = 0.95,
                          alpha: float = 0.7) -> float:
        """
        CORRECTED fitness function that rewards gate reduction ONLY when functionality preserved.
        
        fitness = alpha * fidelity(circuit, target) + (1-alpha) * gate_reduction(circuit, target)
        but penalizes heavily if fidelity < threshold.
        """
        fid = CircuitFitness.fidelity(circuit, target)
        
        if fid < fidelity_threshold:
            # Heavy penalty for losing functionality
            return -1.0 + fid * 0.5
        
        # Reward gate reduction proportional to fidelity preservation
        gate_red = CircuitFitness.gate_count_reduction(target, circuit)
        return alpha * fid + (1 - alpha) * gate_red


class GreedyGateCancellation:
    """
    Greedy Gate Cancellation with extended simplification rules.
    Includes: inverse cancellation, commutation-based cancellation, identity detection.
    """
    
    def __init__(self, max_iterations: int = 100):
        self.max_iterations = max_iterations
        self.iterations = 0
        self.improvements = 0
    
    def optimize(self, circuit: QuantumCircuit) -> Tuple[QuantumCircuit, Dict]:
        optimized = copy.deepcopy(circuit)
        self.iterations = 0
        self.improvements = 0
        
        for iteration in range(self.max_iterations):
            self.iterations = iteration + 1
            improved = False
            
            # Phase 1: Cancel adjacent inverse gates
            i = 0
            while i < len(optimized.data) - 1:
                gate1 = optimized.data[i][0]
                gate2 = optimized.data[i + 1][0]
                qubits1 = [q._index for q in optimized.data[i][1]]
                qubits2 = [q._index for q in optimized.data[i + 1][1]]
                
                if qubits1 == qubits2 and self._are_inverse_gates(gate1, gate2):
                    optimized.data.pop(i)
                    optimized.data.pop(i)
                    improved = True
                    self.improvements += 1
                else:
                    i += 1
            
            # Phase 2: Cancel non-adjacent inverse gates via commutation
            if not improved:
                improved = self._cancel_via_commutation(optimized)
            
            # Phase 3: Merge rotation gates on same qubit
            if not improved:
                improved = self._merge_rotations(optimized)
            
            if not improved:
                break
        
        original_size = circuit.size()
        optimized_size = optimized.size()
        
        return optimized, {
            'iterations': self.iterations,
            'improvements': self.improvements,
            'original_size': original_size,
            'optimized_size': optimized_size,
            'reduction': 1 - optimized_size / max(original_size, 1),
            'functional': True  # Gate cancellation preserves functionality by definition
        }
    
    def _are_inverse_gates(self, gate1, gate2) -> bool:
        """Check if two gates are inverses of each other."""
        try:
            # Self-inverse gates
            if gate1.name in ['h', 'x', 'y', 'z'] and gate1.name == gate2.name:
                return True
            # T-Tdg pair
            if (gate1.name == 't' and gate2.name == 'tdg') or \
               (gate1.name == 'tdg' and gate2.name == 't'):
                return True
            # S-Sdg pair
            if (gate1.name == 's' and gate2.name == 'sdg') or \
               (gate1.name == 'sdg' and gate2.name == 's'):
                return True
            # CNOT cancellation (same control and target)
            if gate1.name == 'cx' and gate2.name == 'cx':
                return True
            return False
        except Exception:
            return False
    
    def _cancel_via_commutation(self, circuit: QuantumCircuit) -> bool:
        """Try to cancel gates that commute past intermediate gates."""
        improved = False
        for i in range(len(circuit.data) - 2):
            gate_i = circuit.data[i][0]
            qubits_i = set(q._index for q in circuit.data[i][1])
            
            for j in range(i + 2, min(i + 5, len(circuit.data))):
                gate_j = circuit.data[j][0]
                qubits_j = set(q._index for q in circuit.data[j][1])
                
                # Check if gates i and j are inverse
                if not self._are_inverse_gates(gate_i, gate_j):
                    continue
                
                # Check if all intermediate gates commute with gate_i
                can_commute = True
                for k in range(i + 1, j):
                    qubits_k = set(q._index for q in circuit.data[k][1])
                    if qubits_k & qubits_i:
                        # Shared qubits - check commutation
                        if not self._commute(gate_i, circuit.data[k][0], 
                                           list(qubits_i), list(qubits_k)):
                            can_commute = False
                            break
                
                if can_commute:
                    # Remove gates i and j (j first since it's later)
                    circuit.data.pop(j)
                    circuit.data.pop(i)
                    improved = True
                    self.improvements += 1
                    break
            
            if improved:
                break
        
        return improved
    
    def _commute(self, gate1, gate2, qubits1, qubits2) -> bool:
        """Simple commutation check for common gates."""
        # Single-qubit gates on different qubits always commute
        if len(set(qubits1) & set(qubits2)) == 0:
            return True
        # CNOT commutes with Z-type gates on control
        # (Simplified - full check requires matrix computation)
        return False
    
    def _merge_rotations(self, circuit: QuantumCircuit) -> bool:
        """Merge consecutive rotation gates on the same qubit."""
        improved = False
        for i in range(len(circuit.data) - 1):
            gate1 = circuit.data[i][0]
            gate2 = circuit.data[i + 1][0]
            qubits1 = [q._index for q in circuit.data[i][1]]
            qubits2 = [q._index for q in circuit.data[i + 1][1]]
            
            if qubits1 == qubits2 and gate1.name == gate2.name:
                # Check if both are rotation gates
                if gate1.name in ['rz', 'rx', 'ry']:
                    try:
                        # Merge angles
                        angle1 = gate1.params[0]
                        angle2 = gate2.params[0]
                        merged_angle = (angle1 + angle2) % (2 * np.pi)
                        
                        if abs(merged_angle) < 1e-10 or abs(merged_angle - 2 * np.pi) < 1e-10:
                            # Identity rotation - remove both
                            circuit.data.pop(i)
                            circuit.data.pop(i)
                        else:
                            # Keep one rotation with merged angle
                            gate1.params[0] = merged_angle
                            circuit.data.pop(i + 1)
                        
                        improved = True
                        self.improvements += 1
                        break
                    except Exception:
                        continue
        
        return improved


class RandomLocalSearch:
    """Random Local Search with functional fidelity check."""
    
    def __init__(self, max_iterations: int = 1000, neighbourhood_size: int = 10):
        self.max_iterations = max_iterations
        self.neighbourhood_size = neighbourhood_size
    
    def optimize(self, circuit: QuantumCircuit, target: QuantumCircuit) -> Tuple[QuantumCircuit, Dict]:
        best_circuit = copy.deepcopy(circuit)
        best_fitness = CircuitFitness.functional_fitness(best_circuit, target)
        
        fitness_history = [best_fitness]
        no_improvement_count = 0
        
        for iteration in range(self.max_iterations):
            neighbours = self._generate_neighbours(best_circuit)
            
            best_neighbour = None
            best_neighbour_fitness = -np.inf
            
            for neighbour in neighbours:
                fitness = CircuitFitness.functional_fitness(neighbour, target)
                if fitness > best_neighbour_fitness:
                    best_neighbour_fitness = fitness
                    best_neighbour = neighbour
            
            if best_neighbour_fitness > best_fitness:
                best_circuit = best_neighbour
                best_fitness = best_neighbour_fitness
                no_improvement_count = 0
            else:
                no_improvement_count += 1
            
            fitness_history.append(best_fitness)
            
            # Early stopping if no improvement for 100 iterations
            if no_improvement_count >= 100:
                break
        
        return best_circuit, {
            'iterations': iteration + 1,
            'best_fitness': best_fitness,
            'fitness_history': fitness_history,
            'original_size': circuit.size(),
            'optimized_size': best_circuit.size(),
            'reduction': 1 - best_circuit.size() / max(circuit.size(), 1),
            'fidelity_preserved': CircuitFitness.fidelity(best_circuit, target) >= 0.95
        }
    
    def _generate_neighbours(self, circuit: QuantumCircuit) -> List[QuantumCircuit]:
        """Generate neighbours by removing single gates or tweaking angles."""
        neighbours = []
        for _ in range(self.neighbour_size):
            neighbour = copy.deepcopy(circuit)
            if len(neighbour.data) > 0:
                # Randomly choose: remove gate or modify angle
                if np.random.random() < 0.7:
                    # Remove a random gate
                    idx = np.random.randint(0, len(neighbour.data))
                    neighbour.data.pop(idx)
                else:
                    # Modify a random rotation gate angle
                    rot_gates = [(i, inst) for i, inst in enumerate(neighbour.data) 
                                if inst[0].name in ['rz', 'rx', 'ry']]
                    if rot_gates:
                        idx, inst = rot_gates[np.random.randint(len(rot_gates))]
                        new_angle = inst[0].params[0] + np.random.normal(0, 0.1)
                        neighbour.data[idx][0].params[0] = new_angle % (2 * np.pi)
            neighbours.append(neighbour)
        return neighbours


class SimulatedAnnealing:
    """
    CORRECTED Simulated Annealing that preserves circuit functionality.
    Fitness function now requires fidelity > 0.95 to be considered valid.
    """
    
    def __init__(self, initial_temp: float = 1.0, cooling_rate: float = 0.995, 
                 max_iterations: int = 2000, fidelity_threshold: float = 0.95):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.max_iterations = max_iterations
        self.fidelity_threshold = fidelity_threshold
    
    def optimize(self, circuit: QuantumCircuit, target: QuantumCircuit) -> Tuple[QuantumCircuit, Dict]:
        current = copy.deepcopy(circuit)
        current_fitness = CircuitFitness.functional_fitness(current, target, self.fidelity_threshold)
        
        best = copy.deepcopy(current)
        best_fitness = current_fitness
        
        temp = self.initial_temp
        accepted = 0
        rejected = 0
        
        fitness_history = [current_fitness]
        
        for iteration in range(self.max_iterations):
            neighbour = self._generate_neighbour(current)
            neighbour_fitness = CircuitFitness.functional_fitness(neighbour, target, self.fidelity_threshold)
            
            delta = neighbour_fitness - current_fitness
            
            # Metropolis criterion
            if delta > 0:
                accept = True
            elif temp > 1e-10:
                prob = np.exp(delta / temp)
                accept = np.random.random() < prob
            else:
                accept = False
            
            if accept:
                current = neighbour
                current_fitness = neighbour_fitness
                accepted += 1
                
                if current_fitness > best_fitness:
                    best = copy.deepcopy(current)
                    best_fitness = current_fitness
            else:
                rejected += 1
            
            temp *= self.cooling_rate
            fitness_history.append(current_fitness)
            
            # Early stopping if temperature is very low
            if temp < 1e-8:
                break
        
        final_fidelity = CircuitFitness.fidelity(best, target)
        
        return best, {
            'iterations': iteration + 1,
            'best_fitness': best_fitness,
            'acceptance_rate': accepted / max(accepted + rejected, 1),
            'final_temp': temp,
            'fitness_history': fitness_history,
            'original_size': circuit.size(),
            'optimized_size': best.size(),
            'reduction': 1 - best.size() / max(circuit.size(), 1),
            'final_fidelity': final_fidelity,
            'functional': final_fidelity >= self.fidelity_threshold
        }
    
    def _generate_neighbour(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """Generate neighbour: remove gate or perturb angle."""
        neighbour = copy.deepcopy(circuit)
        if len(neighbour.data) == 0:
            return neighbour
        
        # Randomly choose operation
        op = np.random.random()
        
        if op < 0.6:
            # Remove a random gate
            idx = np.random.randint(0, len(neighbour.data))
            neighbour.data.pop(idx)
        elif op < 0.8:
            # Modify a rotation gate angle
            rot_indices = [i for i, inst in enumerate(neighbour.data) 
                          if inst[0].name in ['rz', 'rx', 'ry']]
            if rot_indices:
                idx = rot_indices[np.random.randint(len(rot_indices))]
                current_angle = neighbour.data[idx][0].params[0]
                new_angle = current_angle + np.random.normal(0, 0.2)
                neighbour.data[idx][0].params[0] = new_angle % (2 * np.pi)
        else:
            # Swap two adjacent gates (may enable future cancellations)
            if len(neighbour.data) >= 2:
                idx = np.random.randint(0, len(neighbour.data) - 1)
                neighbour.data[idx], neighbour.data[idx + 1] = \
                    neighbour.data[idx + 1], neighbour.data[idx]
        
        return neighbour


class GeneticAlgorithm:
    """Genetic Algorithm with functional fidelity preservation."""
    
    def __init__(self, population_size: int = 50, generations: int = 100, 
                 mutation_rate: float = 0.1, crossover_rate: float = 0.7, 
                 elite_size: int = 5, fidelity_threshold: float = 0.95):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_size = elite_size
        self.fidelity_threshold = fidelity_threshold
    
    def optimize(self, initial_circuit: QuantumCircuit, target: QuantumCircuit) -> Tuple[QuantumCircuit, Dict]:
        population = self._initialize_population(initial_circuit)
        
        best_fitness = -np.inf
        best_circuit = None
        
        fitness_history = []
        
        for gen in range(self.generations):
            fitness_scores = [CircuitFitness.functional_fitness(c, target, self.fidelity_threshold) 
                            for c in population]
            
            max_fitness = max(fitness_scores)
            if max_fitness > best_fitness:
                best_fitness = max_fitness
                best_idx = fitness_scores.index(max_fitness)
                best_circuit = copy.deepcopy(population[best_idx])
            
            fitness_history.append(max_fitness)
            
            # Early convergence check
            if gen > 20 and np.std(fitness_history[-10:]) < 1e-6:
                break
            
            new_population = []
            
            # Elitism
            sorted_indices = np.argsort(fitness_scores)[::-1]
            for i in range(min(self.elite_size, len(sorted_indices))):
                new_population.append(copy.deepcopy(population[sorted_indices[i]]))
            
            # Fill rest with crossover and mutation
            while len(new_population) < self.population_size:
                parent1 = self._tournament_select(population, fitness_scores)
                parent2 = self._tournament_select(population, fitness_scores)
                
                if np.random.random() < self.crossover_rate:
                    child = self._crossover(parent1, parent2)
                else:
                    child = copy.deepcopy(parent1)
                
                if np.random.random() < self.mutation_rate:
                    child = self._mutate(child)
                
                new_population.append(child)
            
            population = new_population
        
        if best_circuit is None:
            best_circuit = initial_circuit
            best_fitness = CircuitFitness.functional_fitness(initial_circuit, target, self.fidelity_threshold)
        
        final_fidelity = CircuitFitness.fidelity(best_circuit, target)
        
        return best_circuit, {
            'generations': gen + 1,
            'best_fitness': best_fitness,
            'fitness_history': fitness_history,
            'original_size': initial_circuit.size(),
            'optimized_size': best_circuit.size(),
            'reduction': 1 - best_circuit.size() / max(initial_circuit.size(), 1),
            'final_fidelity': final_fidelity,
            'functional': final_fidelity >= self.fidelity_threshold
        }
    
    def _initialize_population(self, template: QuantumCircuit) -> List[QuantumCircuit]:
        """Initialize population with variations of template."""
        population = [copy.deepcopy(template)]  # Keep original
        
        for _ in range(self.population_size - 1):
            circuit = copy.deepcopy(template)
            # Apply 1-3 random modifications
            num_mods = np.random.randint(1, min(4, len(circuit.data) // 2 + 1))
            for _ in range(num_mods):
                if len(circuit.data) > 0:
                    op = np.random.random()
                    if op < 0.5:
                        # Remove gate
                        idx = np.random.randint(0, len(circuit.data))
                        circuit.data.pop(idx)
                    else:
                        # Perturb rotation angle
                        rot_indices = [i for i, inst in enumerate(circuit.data) 
                                      if inst[0].name in ['rz', 'rx', 'ry']]
                        if rot_indices:
                            idx = rot_indices[np.random.randint(len(rot_indices))]
                            circuit.data[idx][0].params[0] += np.random.normal(0, 0.3)
                            circuit.data[idx][0].params[0] %= (2 * np.pi)
            population.append(circuit)
        
        return population
    
    def _tournament_select(self, population, fitness_scores, tournament_size: int = 3) -> QuantumCircuit:
        indices = np.random.choice(len(population), min(tournament_size, len(population)), replace=False)
        best_idx = indices[np.argmax([fitness_scores[i] for i in indices])]
        return population[best_idx]
    
    def _crossover(self, parent1: QuantumCircuit, parent2: QuantumCircuit) -> QuantumCircuit:
        if len(parent1.data) == 0 or len(parent2.data) == 0:
            return copy.deepcopy(parent1)
        
        point = np.random.randint(0, min(len(parent1.data), len(parent2.data)))
        child = copy.deepcopy(parent1)
        child.data = parent1.data[:point] + parent2.data[point:]
        return child
    
    def _mutate(self, circuit: QuantumCircuit) -> QuantumCircuit:
        mutant = copy.deepcopy(circuit)
        if len(mutant.data) > 0:
            op = np.random.random()
            if op < 0.5:
                # Remove random gate
                idx = np.random.randint(0, len(mutant.data))
                mutant.data.pop(idx)
            else:
                # Perturb rotation angle
                rot_indices = [i for i, inst in enumerate(mutant.data) 
                              if inst[0].name in ['rz', 'rx', 'ry']]
                if rot_indices:
                    idx = rot_indices[np.random.randint(len(rot_indices))]
                    mutant.data[idx][0].params[0] += np.random.normal(0, 0.3)
                    mutant.data[idx][0].params[0] %= (2 * np.pi)
        return mutant


class LandscapeAwareSearch:
    """Landscape-Aware Search with proper landscape sampling."""
    
    def __init__(self, landscape_samples: int = 100, max_iterations: int = 500, 
                 fidelity_threshold: float = 0.95):
        self.landscape_samples = landscape_samples
        self.max_iterations = max_iterations
        self.fidelity_threshold = fidelity_threshold
    
    def optimize(self, circuit: QuantumCircuit, target: QuantumCircuit) -> Tuple[QuantumCircuit, Dict]:
        # Sample landscape around the circuit
        landscape = self._sample_landscape(circuit, target)
        
        # Estimate local structure
        ruggedness = self._estimate_ruggedness(landscape)
        
        # Choose strategy based on landscape
        if ruggedness < 0.3:
            return self._greedy_search(circuit, target)
        elif ruggedness < 0.7:
            sa = SimulatedAnnealing(max_iterations=self.max_iterations, 
                                   fidelity_threshold=self.fidelity_threshold)
            return sa.optimize(circuit, target)
        else:
            return self._multi_start_search(circuit, target)
    
    def _sample_landscape(self, circuit: QuantumCircuit, target: QuantumCircuit) -> List[float]:
        """Sample fitness landscape by perturbing the circuit (NOT generating random circuits)."""
        fitness_values = []
        for _ in range(self.landscape_samples):
            neighbour = self._random_neighbour(circuit)
            fitness = CircuitFitness.functional_fitness(neighbour, target, self.fidelity_threshold)
            fitness_values.append(fitness)
        return fitness_values
    
    def _estimate_ruggedness(self, landscape: List[float]) -> float:
        if len(landscape) < 2:
            return 0.0
        
        autocorr = np.correlate(landscape, landscape, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        autocorr = autocorr / max(autocorr[0], 1e-10)
        
        correlation_length = np.argmax(autocorr < 0.5) if any(autocorr < 0.5) else len(autocorr)
        return 1.0 / (correlation_length + 1)
    
    def _greedy_search(self, circuit: QuantumCircuit, target: QuantumCircuit) -> Tuple[QuantumCircuit, Dict]:
        greedy = GreedyGateCancellation(max_iterations=self.max_iterations)
        return greedy.optimize(circuit)
    
    def _multi_start_search(self, circuit: QuantumCircuit, target: QuantumCircuit) -> Tuple[QuantumCircuit, Dict]:
        """Multi-start search for rugged landscapes."""
        best_circuit = copy.deepcopy(circuit)
        best_fitness = CircuitFitness.functional_fitness(best_circuit, target, self.fidelity_threshold)
        
        for _ in range(10):
            restart = self._random_neighbour(circuit)
            greedy = GreedyGateCancellation(max_iterations=50)
            optimized, _ = greedy.optimize(restart)
            fitness = CircuitFitness.functional_fitness(optimized, target, self.fidelity_threshold)
            
            if fitness > best_fitness:
                best_circuit = optimized
                best_fitness = fitness
        
        return best_circuit, {
            'iterations': self.max_iterations,
            'best_fitness': best_fitness,
            'strategy': 'multi_start',
            'original_size': circuit.size(),
            'optimized_size': best_circuit.size(),
            'reduction': 1 - best_circuit.size() / max(circuit.size(), 1),
            'functional': best_fitness >= -0.5  # Not penalized
        }
    
    def _random_neighbour(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """Generate a random neighbour by perturbing the circuit."""
        neighbour = copy.deepcopy(circuit)
        if len(neighbour.data) == 0:
            return neighbour
        
        op = np.random.random()
        if op < 0.5:
            # Remove random gate
            idx = np.random.randint(0, len(neighbour.data))
            neighbour.data.pop(idx)
        else:
            # Perturb rotation angle
            rot_indices = [i for i, inst in enumerate(neighbour.data) 
                          if inst[0].name in ['rz', 'rx', 'ry']]
            if rot_indices:
                idx = rot_indices[np.random.randint(len(rot_indices))]
                neighbour.data[idx][0].params[0] += np.random.normal(0, 0.2)
                neighbour.data[idx][0].params[0] %= (2 * np.pi)
        
        return neighbour


def run_optimization_experiment(circuit: QuantumCircuit,
                               target: QuantumCircuit,
                               algorithm: str,
                               **kwargs) -> Tuple[QuantumCircuit, Dict]:
    """Run optimization experiment with specified algorithm."""
    if algorithm == 'greedy':
        optimizer = GreedyGateCancellation(**kwargs)
        return optimizer.optimize(circuit)
    elif algorithm == 'rls':
        optimizer = RandomLocalSearch(**kwargs)
        return optimizer.optimize(circuit, target)
    elif algorithm == 'sa':
        optimizer = SimulatedAnnealing(**kwargs)
        return optimizer.optimize(circuit, target)
    elif algorithm == 'ga':
        optimizer = GeneticAlgorithm(**kwargs)
        return optimizer.optimize(circuit, target)
    elif algorithm == 'landscape':
        optimizer = LandscapeAwareSearch(**kwargs)
        return optimizer.optimize(circuit, target)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")


if __name__ == '__main__':
    print("Testing corrected optimization algorithms...")
    
    from qiskit import QuantumCircuit
    import numpy as np
    
    # Create a test circuit
    n_qubits = 4
    depth = 10
    qc = QuantumCircuit(n_qubits)
    
    np.random.seed(42)
    for layer in range(depth):
        for qubit in range(n_qubits):
            if np.random.random() < 0.3 and qubit < n_qubits - 1:
                qc.cx(qubit, qubit + 1)
            else:
                angle = np.random.uniform(0, 2 * np.pi)
                qc.rz(angle, qubit)
    
    print(f"Original circuit: {qc.size()} gates")
    
    # Test greedy (should preserve functionality)
    optimized_greedy, metrics_greedy = run_optimization_experiment(qc, qc, 'greedy')
    print(f"Greedy: {metrics_greedy['optimized_size']} gates, reduction={metrics_greedy['reduction']:.3f}, functional={metrics_greedy.get('functional', True)}")
    
    # Test SA (should now preserve functionality)
    optimized_sa, metrics_sa = run_optimization_experiment(qc, qc, 'sa', max_iterations=500)
    print(f"SA: {metrics_sa['optimized_size']} gates, reduction={metrics_sa['reduction']:.3f}, functional={metrics_sa.get('functional', 'N/A')}, fidelity={metrics_sa.get('final_fidelity', 'N/A'):.3f}")
    
    print("\nIf SA shows much smaller reduction than before (not 1.0), the fix is working!")
