"""
Quantum Circuit Optimization Algorithms - Production Quality v2.2
================================================================
Implements multiple optimization algorithms with functional fidelity preservation,
comprehensive logging, and statistical tracking.

Defines 'optimization success' as:
  - Gate count reduction >= 20%
  - Fidelity >= 0.99 (unitary equivalence preservation)

Move set for stochastic optimizers:
  - REMOVAL: remove adjacent self-inverse gate pairs
  - SWAP: swap adjacent commuting gates
  - COMMUTATION: move a gate past its neighbor on disjoint qubits
  - INSERTION: insert an identity pair (e.g., H-H, X-X) to enable future cancellations

Author: Q-research Team
Version: 2.2.0
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction
from qiskit.quantum_info import Statevector, Operator
from typing import List, Tuple, Optional, Dict, Callable, Any
import copy
import time
import logging
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum, auto

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================

class OptimizerType(Enum):
    """Supported optimizer types."""
    GREEDY = auto()
    RANDOM_LOCAL_SEARCH = auto()
    SIMULATED_ANNEALING = auto()
    GENETIC_ALGORITHM = auto()


@dataclass
class OptimizationResult:
    """Result of an optimization run."""
    optimized_circuit: QuantumCircuit
    original_size: int
    optimized_size: int
    fidelity: float
    iterations: int
    runtime_seconds: float
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def reduction(self) -> float:
        """Gate count reduction ratio."""
        if self.original_size == 0:
            return 0.0
        return 1.0 - self.optimized_size / self.original_size
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'original_size': self.original_size,
            'optimized_size': self.optimized_size,
            'reduction': self.reduction,
            'fidelity': self.fidelity,
            'iterations': self.iterations,
            'runtime_seconds': self.runtime_seconds,
            'success': self.success,
            'metadata': self.metadata,
        }


# ============================================================================
# Move Types (for stochastic optimizers)
# ============================================================================

class MoveType(Enum):
    """Types of circuit transformation moves."""
    REMOVAL = "removal"           # Remove adjacent self-inverse pairs
    SWAP = "swap"                 # Swap adjacent commuting gates
    COMMUTATION = "commutation"   # Move gate past neighbor on disjoint qubits
    INSERTION = "insertion"       # Insert identity pair (e.g., H-H, X-X)


# Self-inverse gate names (gate^2 = I)
_SELF_INVERSE_GATES = frozenset({'h', 'x', 'y', 'z', 'cx', 'cz', 'swap'})

# Identity pairs that can be inserted (gate applied twice = identity)
_IDENTITY_PAIRS = ['h', 'x', 'y', 'z']


# ============================================================================
# Base Optimizer
# ============================================================================

class BaseOptimizer(ABC):
    """Abstract base class for all optimizers."""
    
    def __init__(self, fidelity_threshold: float = 0.99, success_reduction: float = 0.20):
        """
        Args:
            fidelity_threshold: Minimum fidelity to consider optimization valid
            success_reduction: Minimum gate reduction to consider optimization successful
        """
        self.fidelity_threshold = fidelity_threshold
        self.success_reduction = success_reduction
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def optimize(self, circuit: QuantumCircuit, target: Optional[QuantumCircuit] = None) -> OptimizationResult:
        """Optimize the given circuit."""
        pass
    
    def calculate_fidelity(self, circuit: QuantumCircuit, target: QuantumCircuit) -> float:
        """
        Calculate the average gate fidelity between two circuits.
        
        The average gate fidelity is defined as:
            F_avg = (|Tr(U1† U2)|² + d) / (d² + d)
        where d = 2^n is the Hilbert space dimension (n = number of qubits).
        
        NOTE: This is NOT the same as the normalized Hilbert-Schmidt inner product,
        F_HS = |Tr(U1† U2)|² / d², which overestimates the error by neglecting the
        identity-component contribution. The average gate fidelity F_avg corresponds
        to the average fidelity over all pure input states |ψ⟩:
            F_avg = ∫ dψ ⟨ψ|U1† U2|ψ⟩⟨ψ|U2† U1|ψ⟩
        where the integral is over the uniform (Haar) measure on the state space.
        This makes F_avg the physically meaningful metric for comparing quantum gates,
        as it represents the expected overlap of output states for a uniformly random
        input state.
        """
        try:
            if circuit.num_qubits != target.num_qubits:
                return 0.0
            
            n = circuit.num_qubits
            d = 2 ** n
            
            # Compute unitary matrices from circuits
            u1 = np.array(Operator(circuit).data)
            u2 = np.array(Operator(target).data)
            
            # Compute |Tr(U1† U2)|²
            inner_product = np.abs(np.trace(np.conj(u1).T @ u2)) ** 2
            
            # Average gate fidelity: (|Tr(U1† U2)|² + d) / (d² + d)
            # This equals the mean fidelity averaged over all pure input states.
            return float((inner_product + d) / (d ** 2 + d))
        except Exception as e:
            self.logger.warning(f"Failed to calculate fidelity: {e}")
            return 0.0
    
    def verify_functionality(self, circuit: QuantumCircuit, target: QuantumCircuit) -> bool:
        """Verify that the optimized circuit preserves functionality."""
        fidelity = self.calculate_fidelity(circuit, target)
        return fidelity >= self.fidelity_threshold
    
    def _is_success(self, reduction: float, fidelity: float) -> bool:
        """Determine if optimization was successful."""
        return reduction >= self.success_reduction and fidelity >= self.fidelity_threshold

    # ========================================================================
    # Shared Move Primitives (used by stochastic optimizers)
    # ========================================================================

    def _get_qubit_indices(self, circuit: QuantumCircuit, inst: CircuitInstruction) -> List[int]:
        """Get qubit indices for a circuit instruction."""
        try:
            return [circuit.find_bit(q).index for q in inst.qubits]
        except Exception:
            return []

    def _gates_on_disjoint_qubits(self, circuit: QuantumCircuit, 
                                   inst1: CircuitInstruction, 
                                   inst2: CircuitInstruction) -> bool:
        """Check if two instructions act on completely disjoint qubit sets."""
        qubits1 = set(self._get_qubit_indices(circuit, inst1))
        qubits2 = set(self._get_qubit_indices(circuit, inst2))
        if not qubits1 or not qubits2:
            return False
        return len(qubits1 & qubits2) == 0

    def _gates_commute(self, circuit: QuantumCircuit,
                       inst1: CircuitInstruction, 
                       inst2: CircuitInstruction) -> bool:
        """
        Check if two gate instructions commute.
        
        Sufficient conditions for commutation:
        1. Gates act on disjoint qubit sets
        2. Both are diagonal in the same basis (e.g., Rz gates)
        3. Both are the same single-qubit gate on the same qubit
        """
        # Disjoint qubits always commute
        if self._gates_on_disjoint_qubits(circuit, inst1, inst2):
            return True
        
        name1 = inst1.operation.name
        name2 = inst2.operation.name
        qubits1 = self._get_qubit_indices(circuit, inst1)
        qubits2 = self._get_qubit_indices(circuit, inst2)
        
        # Same single-qubit gate on same qubit commutes with itself
        if name1 == name2 and qubits1 == qubits2 and len(qubits1) == 1:
            return True
        
        # Rotation gates around the same axis commute
        if (name1 in ('rz', 'rx', 'ry') and name2 in ('rz', 'rx', 'ry') 
                and name1 == name2 and qubits1 == qubits2):
            return True
        
        # Z-rotations and Z gates commute with each other on same qubit
        z_family = {'z', 'rz', 's', 'sdg', 't', 'tdg'}
        if name1 in z_family and name2 in z_family and qubits1 == qubits2:
            return True
        
        return False

    def _is_self_inverse_pair(self, circuit: QuantumCircuit,
                               inst1: CircuitInstruction,
                               inst2: CircuitInstruction) -> bool:
        """Check if two adjacent instructions form a self-inverse pair (cancel each other)."""
        name1 = inst1.operation.name
        name2 = inst2.operation.name
        qubits1 = self._get_qubit_indices(circuit, inst1)
        qubits2 = self._get_qubit_indices(circuit, inst2)
        
        # Must act on the same qubits
        if qubits1 != qubits2:
            return False
        
        # Self-inverse gates: same gate cancels
        if name1 == name2 and name1 in _SELF_INVERSE_GATES:
            return True
        
        # T-Tdg pair
        if (name1 == 't' and name2 == 'tdg') or (name1 == 'tdg' and name2 == 't'):
            return True
        
        # S-Sdg pair
        if (name1 == 's' and name2 == 'sdg') or (name1 == 'sdg' and name2 == 's'):
            return True
        
        # Rotation gates with inverse angles
        if name1 == name2 and name1 in ('rx', 'ry', 'rz'):
            if len(inst1.operation.params) > 0 and len(inst2.operation.params) > 0:
                if abs(inst1.operation.params[0] + inst2.operation.params[0]) < 1e-10:
                    return True
        
        return False

    def _move_removal(self, circuit: QuantumCircuit) -> Optional[QuantumCircuit]:
        """
        REMOVAL move: Find and remove an adjacent self-inverse gate pair.
        Returns a new circuit with one pair removed, or None if no valid move exists.
        """
        if len(circuit.data) < 2:
            return None
        
        # Find all valid removal positions
        valid_positions = []
        for i in range(len(circuit.data) - 1):
            if self._is_self_inverse_pair(circuit, circuit.data[i], circuit.data[i + 1]):
                valid_positions.append(i)
        
        if not valid_positions:
            return None
        
        # Pick a random valid position
        idx = np.random.choice(valid_positions)
        neighbor = copy.deepcopy(circuit)
        neighbor.data.pop(idx)
        neighbor.data.pop(idx)
        return neighbor

    def _move_swap(self, circuit: QuantumCircuit) -> Optional[QuantumCircuit]:
        """
        SWAP move: Swap two adjacent commuting gates.
        Returns a new circuit with swapped gates, or None if no valid move exists.
        """
        if len(circuit.data) < 2:
            return None
        
        # Find all valid swap positions (adjacent gates that commute)
        valid_positions = []
        for i in range(len(circuit.data) - 1):
            if self._gates_commute(circuit, circuit.data[i], circuit.data[i + 1]):
                valid_positions.append(i)
        
        if not valid_positions:
            return None
        
        # Pick a random valid position
        idx = np.random.choice(valid_positions)
        neighbor = copy.deepcopy(circuit)
        neighbor.data[idx], neighbor.data[idx + 1] = neighbor.data[idx + 1], neighbor.data[idx]
        return neighbor

    def _move_commutation(self, circuit: QuantumCircuit) -> Optional[QuantumCircuit]:
        """
        COMMUTATION move: Move a gate past its neighbor when they act on disjoint qubits.
        This is a specialized swap that only applies to gates on completely disjoint qubit sets.
        Returns a new circuit or None if no valid move exists.
        """
        if len(circuit.data) < 2:
            return None
        
        # Find positions where gates act on disjoint qubits
        valid_positions = []
        for i in range(len(circuit.data) - 1):
            if self._gates_on_disjoint_qubits(circuit, circuit.data[i], circuit.data[i + 1]):
                valid_positions.append(i)
        
        if not valid_positions:
            return None
        
        # Pick a random valid position
        idx = np.random.choice(valid_positions)
        neighbor = copy.deepcopy(circuit)
        neighbor.data[idx], neighbor.data[idx + 1] = neighbor.data[idx + 1], neighbor.data[idx]
        return neighbor

    def _move_insertion(self, circuit: QuantumCircuit) -> Optional[QuantumCircuit]:
        """
        INSERTION move: Insert an identity pair (e.g., H-H, X-X) at a random position.
        This can enable future cancellations by bringing like gates adjacent.
        Returns a new circuit with an inserted pair.
        """
        if circuit.num_qubits == 0:
            return None
        
        neighbor = copy.deepcopy(circuit)
        
        # Pick a random gate type for the identity pair
        gate_name = np.random.choice(_IDENTITY_PAIRS)
        
        # Pick a random qubit
        qubit_idx = np.random.randint(0, neighbor.num_qubits)
        
        # Pick a random insertion position
        pos = np.random.randint(0, len(neighbor.data) + 1)
        
        # Build a small circuit with the identity pair and compose it
        insert_circ = QuantumCircuit(neighbor.num_qubits)
        if gate_name == 'h':
            insert_circ.h(qubit_idx)
            insert_circ.h(qubit_idx)
        elif gate_name == 'x':
            insert_circ.x(qubit_idx)
            insert_circ.x(qubit_idx)
        elif gate_name == 'y':
            insert_circ.y(qubit_idx)
            insert_circ.y(qubit_idx)
        elif gate_name == 'z':
            insert_circ.z(qubit_idx)
            insert_circ.z(qubit_idx)
        
        # Insert the two gates at the chosen position
        for j, inst in enumerate(insert_circ.data):
            neighbor.data.insert(pos + j, copy.deepcopy(inst))
        
        return neighbor

    def _generate_neighbor(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """
        Generate a neighbor circuit by applying a random valid move.
        
        Randomly selects from: REMOVAL, SWAP, COMMUTATION, INSERTION.
        Only applies moves that preserve unitary equivalence.
        Falls back to insertion if no other moves are valid.
        """
        # Define available moves with their methods
        moves = [
            (MoveType.REMOVAL, self._move_removal),
            (MoveType.SWAP, self._move_swap),
            (MoveType.COMMUTATION, self._move_commutation),
            (MoveType.INSERTION, self._move_insertion),
        ]
        
        # Shuffle to randomize priority
        np.random.shuffle(moves)
        
        # Try each move; use the first one that succeeds
        for move_type, move_fn in moves:
            result = move_fn(circuit)
            if result is not None:
                return result
        
        # Fallback: if nothing works, return a copy (no-op)
        return copy.deepcopy(circuit)

    def _fitness(self, circuit: QuantumCircuit, target: QuantumCircuit) -> float:
        """
        Calculate fitness with hard fidelity constraint.
        
        Returns 0.0 if fidelity < 0.99 (hard penalty).
        Otherwise: fidelity * 0.7 + reduction * 0.3
        """
        fidelity = self.calculate_fidelity(circuit, target)
        
        # Hard constraint: fidelity must be >= 0.99
        if fidelity < self.fidelity_threshold:
            return 0.0
        
        reduction = 1.0 - circuit.size() / target.size() if target.size() > 0 else 0.0
        return fidelity * 0.7 + reduction * 0.3


# ============================================================================
# Greedy Gate Cancellation
# ============================================================================

class GreedyGateCancellation(BaseOptimizer):
    """
    Greedy gate cancellation optimizer.
    
    Cancels adjacent inverse gates and applies commutation rules.
    Preserves functionality by construction.
    """
    
    def __init__(self, max_iterations: int = 100, fidelity_threshold: float = 0.99,
                 success_reduction: float = 0.20):
        super().__init__(fidelity_threshold, success_reduction)
        self.max_iterations = max_iterations
    
    def optimize(self, circuit: QuantumCircuit, target: Optional[QuantumCircuit] = None) -> OptimizationResult:
        """Optimize using greedy gate cancellation."""
        start_time = time.time()
        original = circuit
        optimized = copy.deepcopy(circuit)
        
        improvements = 0
        
        for iteration in range(self.max_iterations):
            improved = False
            
            # Phase 1: Cancel adjacent inverse gates
            i = 0
            while i < len(optimized.data) - 1:
                if self._are_inverse(optimized.data[i], optimized.data[i + 1]):
                    optimized.data.pop(i)
                    optimized.data.pop(i)
                    improved = True
                    improvements += 1
                else:
                    i += 1
            
            # Phase 2: Merge rotation gates
            if not improved:
                improved = self._merge_rotations(optimized)
            
            if not improved:
                break
        
        runtime = time.time() - start_time
        
        # Calculate fidelity
        fidelity = 1.0 if target is None else self.calculate_fidelity(optimized, target)
        reduction = 1.0 - optimized.size() / original.size() if original.size() > 0 else 0.0
        success = self._is_success(reduction, fidelity)
        
        return OptimizationResult(
            optimized_circuit=optimized,
            original_size=original.size(),
            optimized_size=optimized.size(),
            fidelity=fidelity,
            iterations=improvements,
            runtime_seconds=runtime,
            success=success,
            metadata={'algorithm': 'greedy', 'improvements': improvements}
        )
    
    def _are_inverse(self, inst1, inst2) -> bool:
        """Check if two instructions are inverses on the same qubit(s)."""
        try:
            gate1 = inst1.operation.name
            gate2 = inst2.operation.name
            
            # CRITICAL FIX: Verify both instructions act on the same qubit(s)
            qubits1 = tuple(sorted(q._index for q in inst1.qubits))
            qubits2 = tuple(sorted(q._index for q in inst2.qubits))
            if qubits1 != qubits2:
                return False
            
            # Self-inverse gates
            if gate1 == gate2 and gate1 in ('h', 'x', 'y', 'z', 'cx', 'cz', 'swap'):
                return True
            
            # T-Tdg pair
            if (gate1 == 't' and gate2 == 'tdg') or (gate1 == 'tdg' and gate2 == 't'):
                return True
            
            # S-Sdg pair
            if (gate1 == 's' and gate2 == 'sdg') or (gate1 == 'sdg' and gate2 == 's'):
                return True
            
            # Rx/Ry/Rz with angle 0
            if gate1 in ('rx', 'ry', 'rz') and gate2 in ('rx', 'ry', 'rz'):
                if len(inst1.operation.params) > 0 and len(inst2.operation.params) > 0:
                    if abs(inst1.operation.params[0] + inst2.operation.params[0]) < 1e-10:
                        return True
            
            return False
        except Exception:
            return False
    
    def _merge_rotations(self, circuit: QuantumCircuit) -> bool:
        """Merge consecutive rotation gates on the same qubit."""
        improved = False
        
        for i in range(len(circuit.data) - 1):
            try:
                gate1 = circuit.data[i].operation.name
                gate2 = circuit.data[i + 1].operation.name
                
                # Check if same qubit
                qubits1 = [q._index for q in circuit.data[i].qubits]
                qubits2 = [q._index for q in circuit.data[i + 1].qubits]
                
                if qubits1 == qubits2 and gate1 == gate2 and gate1 in ('rz', 'rx', 'ry'):
                    # Merge angles
                    angle1 = circuit.data[i].operation.params[0]
                    angle2 = circuit.data[i + 1].operation.params[0]
                    merged = (angle1 + angle2) % (2 * np.pi)
                    
                    if abs(merged) < 1e-10 or abs(merged - 2 * np.pi) < 1e-10:
                        circuit.data.pop(i)
                        circuit.data.pop(i)
                    else:
                        circuit.data[i].operation.params[0] = merged
                        circuit.data.pop(i + 1)
                    
                    improved = True
                    break
            except (IndexError, AttributeError):
                continue
        
        return improved


# ============================================================================
# Random Local Search
# ============================================================================

class RandomLocalSearch(BaseOptimizer):
    """
    Random Local Search optimizer.
    
    Explores the neighborhood of the current circuit by applying
    random modifications and accepting improvements.
    
    Uses the expanded move set: REMOVAL, SWAP, COMMUTATION, INSERTION.
    """
    
    def __init__(self, max_iterations: int = 100, neighborhood_size: int = 5,
                 fidelity_threshold: float = 0.99, success_reduction: float = 0.20):
        super().__init__(fidelity_threshold, success_reduction)
        self.max_iterations = max_iterations
        self.neighborhood_size = neighborhood_size
    
    def optimize(self, circuit: QuantumCircuit, target: Optional[QuantumCircuit] = None) -> OptimizationResult:
        """Optimize using random local search."""
        start_time = time.time()
        
        if target is None:
            target = circuit
        
        best = copy.deepcopy(circuit)
        best_fitness = self._fitness(best, target)
        
        fitness_history = [best_fitness]
        no_improvement = 0
        
        for iteration in range(self.max_iterations):
            neighbors = self._generate_neighbors(best)
            
            best_neighbor = None
            best_neighbor_fitness = -np.inf
            
            for neighbor in neighbors:
                fitness = self._fitness(neighbor, target)
                if fitness > best_neighbor_fitness:
                    best_neighbor_fitness = fitness
                    best_neighbor = neighbor
            
            if best_neighbor_fitness > best_fitness:
                best = best_neighbor
                best_fitness = best_neighbor_fitness
                no_improvement = 0
            else:
                no_improvement += 1
            
            fitness_history.append(best_fitness)
            
            # Early stopping
            if no_improvement >= 50:
                break
        
        runtime = time.time() - start_time
        fidelity = self.calculate_fidelity(best, target)
        reduction = 1.0 - best.size() / circuit.size() if circuit.size() > 0 else 0.0
        success = self._is_success(reduction, fidelity)
        
        return OptimizationResult(
            optimized_circuit=best,
            original_size=circuit.size(),
            optimized_size=best.size(),
            fidelity=fidelity,
            iterations=iteration + 1,
            runtime_seconds=runtime,
            success=success,
            metadata={'algorithm': 'rls', 'fitness_history': fitness_history}
        )
    
    def _generate_neighbors(self, circuit: QuantumCircuit) -> List[QuantumCircuit]:
        """
        Generate neighborhood of circuits using the expanded move set.
        
        Each neighbor is produced by applying one random valid move
        (REMOVAL, SWAP, COMMUTATION, or INSERTION) that preserves
        unitary equivalence.
        """
        neighbors = []
        for _ in range(self.neighborhood_size):
            neighbor = self._generate_neighbor(circuit)
            neighbors.append(neighbor)
        return neighbors


# ============================================================================
# Simulated Annealing
# ============================================================================

class SimulatedAnnealingOptimizer(BaseOptimizer):
    """
    Simulated Annealing optimizer.
    
    Uses temperature-based acceptance criterion to escape local minima.
    All moves preserve unitary equivalence via the expanded move set.
    """
    
    def __init__(self, max_iterations: int = 100, initial_temp: float = 1.0,
                 cooling_rate: float = 0.995, fidelity_threshold: float = 0.99,
                 success_reduction: float = 0.20):
        super().__init__(fidelity_threshold, success_reduction)
        self.max_iterations = max_iterations
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
    
    def optimize(self, circuit: QuantumCircuit, target: Optional[QuantumCircuit] = None) -> OptimizationResult:
        """Optimize using simulated annealing."""
        start_time = time.time()
        
        if target is None:
            target = circuit
        
        current = copy.deepcopy(circuit)
        current_fitness = self._fitness(current, target)
        
        best = copy.deepcopy(current)
        best_fitness = current_fitness
        
        temp = self.initial_temp
        min_temp = 1e-8  # Prevent division by zero
        
        for iteration in range(self.max_iterations):
            # Generate neighbor using expanded move set
            neighbor = self._generate_neighbor(current)
            neighbor_fitness = self._fitness(neighbor, target)
            
            # Acceptance criterion (Metropolis-Hastings)
            delta = neighbor_fitness - current_fitness
            if delta > 0:
                # Always accept improvements
                current = neighbor
                current_fitness = neighbor_fitness
            elif temp > min_temp:
                # Accept worse solutions with probability exp(delta / temp)
                acceptance_prob = np.exp(delta / temp)
                if np.random.random() < acceptance_prob:
                    current = neighbor
                    current_fitness = neighbor_fitness
            
            # Update best
            if current_fitness > best_fitness:
                best = copy.deepcopy(current)
                best_fitness = current_fitness
            
            # Cool down
            temp *= self.cooling_rate
            temp = max(temp, min_temp)
        
        runtime = time.time() - start_time
        fidelity = self.calculate_fidelity(best, target)
        reduction = 1.0 - best.size() / circuit.size() if circuit.size() > 0 else 0.0
        success = self._is_success(reduction, fidelity)
        
        return OptimizationResult(
            optimized_circuit=best,
            original_size=circuit.size(),
            optimized_size=best.size(),
            fidelity=fidelity,
            iterations=iteration + 1,
            runtime_seconds=runtime,
            success=success,
            metadata={'algorithm': 'sa', 'final_temp': temp}
        )


# ============================================================================
# Genetic Algorithm
# ============================================================================

class GeneticAlgorithmOptimizer(BaseOptimizer):
    """
    Genetic Algorithm optimizer.
    
    Uses evolutionary strategies: selection, crossover, mutation.
    All moves preserve unitary equivalence via the expanded move set.
    
    Crossover strategy: Uses the fitter parent as base and applies
    transformation patches derived from the other parent's gate operations.
    """
    
    def __init__(self, population_size: int = 10, generations: int = 10,
                 mutation_rate: float = 0.1, fidelity_threshold: float = 0.99,
                 success_reduction: float = 0.20):
        super().__init__(fidelity_threshold, success_reduction)
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
    
    def optimize(self, circuit: QuantumCircuit, target: Optional[QuantumCircuit] = None) -> OptimizationResult:
        """Optimize using genetic algorithm."""
        start_time = time.time()
        
        if target is None:
            target = circuit
        
        # Initialize population with random valid moves applied to the original
        population = [copy.deepcopy(circuit)]
        for _ in range(self.population_size - 1):
            individual = copy.deepcopy(circuit)
            # Apply 1-3 random moves to create diversity
            num_moves = np.random.randint(1, 4)
            for _ in range(num_moves):
                individual = self._generate_neighbor(individual)
            population.append(individual)
        
        best = copy.deepcopy(circuit)
        best_fitness = self._fitness(best, target)
        
        for generation in range(self.generations):
            # Evaluate fitness
            fitnesses = [self._fitness(ind, target) for ind in population]
            
            # Find best
            gen_best_idx = np.argmax(fitnesses)
            if fitnesses[gen_best_idx] > best_fitness:
                best = copy.deepcopy(population[gen_best_idx])
                best_fitness = fitnesses[gen_best_idx]
            
            # Selection (tournament)
            selected = self._tournament_select(population, fitnesses)
            
            # Crossover and mutation
            new_population = []
            for i in range(0, len(selected), 2):
                parent1 = selected[i]
                parent2 = selected[(i + 1) % len(selected)]
                
                child1, child2 = self._crossover(parent1, parent2, target)
                child1 = self._mutate(child1)
                child2 = self._mutate(child2)
                
                new_population.extend([child1, child2])
            
            population = new_population[:self.population_size]
        
        runtime = time.time() - start_time
        fidelity = self.calculate_fidelity(best, target)
        reduction = 1.0 - best.size() / circuit.size() if circuit.size() > 0 else 0.0
        success = self._is_success(reduction, fidelity)
        
        return OptimizationResult(
            optimized_circuit=best,
            original_size=circuit.size(),
            optimized_size=best.size(),
            fidelity=fidelity,
            iterations=self.generations,
            runtime_seconds=runtime,
            success=success,
            metadata={'algorithm': 'ga', 'population_size': self.population_size}
        )
    
    def _tournament_select(self, population: List[QuantumCircuit], fitnesses: List[float]) -> List[QuantumCircuit]:
        """Tournament selection."""
        selected = []
        for _ in range(len(population)):
            i, j = np.random.choice(len(population), 2, replace=False)
            selected.append(copy.deepcopy(population[i] if fitnesses[i] > fitnesses[j] else population[j]))
        return selected
    
    def _crossover(self, parent1: QuantumCircuit, parent2: QuantumCircuit,
                   target: QuantumCircuit) -> Tuple[QuantumCircuit, QuantumCircuit]:
        """
        Patch-based crossover that preserves unitary equivalence.
        
        Strategy:
        - Use the fitter parent as the base circuit
        - Extract 'gene patches' (successful local transformations) from the other parent
        - Apply patches from the weaker parent to the stronger parent's structure
        
        This avoids the broken half-concatenation that destroys unitary equivalence.
        """
        fitness1 = self._fitness(parent1, target)
        fitness2 = self._fitness(parent2, target)
        
        # Determine which parent is fitter
        if fitness1 >= fitness2:
            stronger, weaker = copy.deepcopy(parent1), copy.deepcopy(parent2)
        else:
            stronger, weaker = copy.deepcopy(parent2), copy.deepcopy(parent1)
        
        # Child 1: stronger parent with random moves applied (inspired by weaker parent's diversity)
        child1 = copy.deepcopy(stronger)
        # Apply 1-2 random valid moves as 'gene transfer'
        num_patches = np.random.randint(1, 3)
        for _ in range(num_patches):
            child1 = self._generate_neighbor(child1)
        
        # Child 2: weaker parent with random moves applied
        child2 = copy.deepcopy(weaker)
        num_patches = np.random.randint(1, 3)
        for _ in range(num_patches):
            child2 = self._generate_neighbor(child2)
        
        return child1, child2
    
    def _mutate(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """
        Mutate a circuit using the expanded move set.
        
        With probability mutation_rate, apply a random valid move
        that preserves unitary equivalence.
        """
        if np.random.random() < self.mutation_rate:
            circuit = self._generate_neighbor(circuit)
        return circuit


# ============================================================================
# Factory Function
# ============================================================================

def create_optimizer(optimizer_type: OptimizerType, **kwargs) -> BaseOptimizer:
    """Create an optimizer based on type."""
    optimizers = {
        OptimizerType.GREEDY: GreedyGateCancellation,
        OptimizerType.RANDOM_LOCAL_SEARCH: RandomLocalSearch,
        OptimizerType.SIMULATED_ANNEALING: SimulatedAnnealingOptimizer,
        OptimizerType.GENETIC_ALGORITHM: GeneticAlgorithmOptimizer,
    }
    
    if optimizer_type not in optimizers:
        raise ValueError(f"Unknown optimizer type: {optimizer_type}")
    
    return optimizers[optimizer_type](**kwargs)
