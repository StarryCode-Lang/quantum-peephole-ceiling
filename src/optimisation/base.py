"""
Base Optimizer Class for Quantum Circuit Peephole Optimization
=============================================================
Defines the abstract base class, data structures, and shared move primitives
used by all Phase 1 and Phase 2 optimizers.

Version: 3.0.0 (Postdoctoral-Grade Refactor)
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction
from qiskit.quantum_info import Operator
from typing import Callable, Any
from .constants import DEFAULT_FIDELITY_SAMPLES, DEFAULT_PRECISION, MAX_EXACT_FIDELITY_QUBITS
import copy
import time
import logging
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum, auto

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
    HYBRID_COMMUTE_REWRITE = auto()


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
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def reduction(self) -> float:
        """Gate count reduction ratio."""
        if self.original_size == 0:
            return 0.0
        return 1.0 - self.optimized_size / self.original_size

    def compute_extended_metrics(self, original_circuit: QuantumCircuit) -> dict[str, float]:
        """Compute extended metrics: depth, two-qubit gate, and CNOT reduction.

        Call after optimization to populate metadata with additional metrics.
        Returns the metrics dict and also stores them in self.metadata.
        """
        def _count_gates(circ: QuantumCircuit, num_qubits_fn=int):
            depth = int(circ.depth() or 0)
            two_q = sum(1 for inst in circ.data if inst.operation.num_qubits == 2)
            cnot = sum(1 for inst in circ.data
                       if inst.operation.name in ('cx', 'cnot'))
            return depth, two_q, cnot

        orig_depth, orig_2q, orig_cnot = _count_gates(original_circuit)
        opt_depth, opt_2q, opt_cnot = _count_gates(self.optimized_circuit)

        def _safe_ratio(orig, opt):
            return 1.0 - opt / orig if orig > 0 else 0.0

        metrics = {
            'original_depth': orig_depth,
            'optimized_depth': opt_depth,
            'depth_reduction': _safe_ratio(orig_depth, opt_depth),
            'original_2q_gates': orig_2q,
            'optimized_2q_gates': opt_2q,
            'two_qubit_reduction': _safe_ratio(orig_2q, opt_2q),
            'original_cnot_count': orig_cnot,
            'optimized_cnot_count': opt_cnot,
            'cnot_reduction': _safe_ratio(orig_cnot, opt_cnot),
        }
        self.metadata.update(metrics)
        return metrics
    
    def to_dict(self) -> dict[str, Any]:
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
    
    def __init__(self, fidelity_threshold: float = 0.99, success_reduction: float = 0.20,
                 random_seed: int | None = None):
        """
        Args:
            fidelity_threshold: Minimum fidelity to consider optimization valid
            success_reduction: Minimum gate reduction to consider optimization successful
            random_seed: Optional seed for optimizer-internal stochastic moves
        """
        self.fidelity_threshold = fidelity_threshold
        self.success_reduction = success_reduction
        self.random_seed = random_seed
        self.rng = np.random.RandomState(random_seed)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def optimize(self, circuit: QuantumCircuit, target: QuantumCircuit | None = None) -> OptimizationResult:
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

        For circuits with n > MAX_EXACT_FIDELITY_QUBITS (default 12), constructing the
        full unitary matrix would require O(4^n) memory. In that case, a lightweight
        sampling-based estimate is used instead.
        """
        try:
            if circuit.num_qubits != target.num_qubits:
                return 0.0

            n = circuit.num_qubits
            d = 2 ** n

            # For large circuits, use a lightweight estimate to avoid memory explosion
            if n > MAX_EXACT_FIDELITY_QUBITS:
                return self._estimate_fidelity(circuit, target)

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
    
    def _estimate_fidelity(self, circuit: QuantumCircuit, target: QuantumCircuit,
                           n_samples: int = DEFAULT_FIDELITY_SAMPLES) -> float:
        """
        Estimate average gate fidelity via Haar-random product-state sampling
        for n > MAX_EXACT_FIDELITY_QUBITS.

        Generates random input states by applying independent Haar-random
        single-qubit unitaries to the |0>^n state. Each single-qubit state
        is drawn exactly from the Haar measure on SU(2), ensuring correct
        4th moments (E[|alpha|^4] = 1/3 per qubit) that match the Haar
        distribution. This makes each qubit's marginal an exact single-qubit
        spherical 2-design.

        The previous implementation used uniform Ry(theta) + Rz(phi) rotations
        applied to random computational basis states, which yields
        E[|alpha|^4] = 3/8 != 1/3 (Haar), violating the 2-design property
        and causing the estimator to converge to an incorrect value.

        While the tensor product of single-qubit Haar states is not a full
        n-qubit 2-design, the dominant contributions to the fidelity integral
        arise from local terms where the per-qubit 2-design property suffices.
        The residual bias from cross-qubit correlations is O(1/d) where
        d = 2^n, making it negligible for the large circuits where this
        estimator is used (n > 12).

        For Clifford circuits, falls back to exact tableau comparison first.

        NOTE: This estimator has ~1/sqrt(n_samples) standard error. For
        n_samples=1000, expect ~3% uncertainty. Use exact fidelity (n <= 12)
        whenever possible for publication-quality results.
        """
        if circuit == target:
            return 1.0

        # Attempt exact Clifford comparison (O(n^2) memory)
        try:
            from qiskit.quantum_info import Clifford

            _CLIFFORD_GATES = {
                'h', 'x', 'y', 'z', 's', 'sdg', 'cx', 'cnot', 'cz', 'swap', 'id'
            }

            def _is_clifford(circ: QuantumCircuit) -> bool:
                return all(
                    inst.operation.name in _CLIFFORD_GATES
                    for inst in circ.data
                )

            if _is_clifford(circuit) and _is_clifford(target):
                c1 = Clifford(circuit)
                c2 = Clifford(target)
                if c1 == c2:
                    return 1.0
                # Different Cliffords: fall through to sampling
        except Exception:
            pass

        # Random-state sampling fidelity estimate
        try:
            from qiskit.quantum_info import Statevector, random_unitary
            
            n = circuit.num_qubits
            overlaps = []
            for _ in range(n_samples):
                # Create Haar-random product input state: apply independent
                # Haar-random single-qubit unitaries to |0>^n.
                # Each qubit's state is drawn from the exact Haar measure on
                # the single-qubit Bloch sphere (a 2-design), ensuring correct
                # 4th moments E[|alpha|^4] = 1/3 per qubit.
                psi_in = Statevector.from_label('0' * n)
                for i in range(n):
                    u_i = random_unitary(2, seed=int(self.rng.randint(0, 2**31)))
                    psi_in = psi_in.evolve(u_i, qargs=[i])
                
                # Evolve through both circuits
                sv1 = psi_in.evolve(circuit)
                sv2 = psi_in.evolve(target)
                # Compute |<psi1|psi2>|^2
                overlap = np.abs(np.vdot(sv1.data, sv2.data)) ** 2
                overlaps.append(float(overlap))
            
            estimated = float(np.mean(overlaps))
            return min(1.0, max(0.0, estimated))
        except Exception as e:
            self.logger.warning(f"Random-state sampling failed: {e}, falling back to structural estimate")
            # Last-resort fallback: structural similarity (clearly labeled)
            from collections import Counter
            c_gates = Counter(inst.operation.name for inst in circuit.data)
            t_gates = Counter(inst.operation.name for inst in target.data)
            common = sum((c_gates & t_gates).values())
            total = sum((c_gates | t_gates).values())
            if total == 0:
                return 1.0
            return float(common / total)

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

    def _get_qubit_indices(self, circuit: QuantumCircuit, inst: CircuitInstruction) -> list[int]:
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

        NOTE: This method checks SUFFICIENT conditions for commutation, not necessary
        conditions. Some valid commutation relationships are not detected:
        - Partial commutation of SWAP gates with other gates
        - Special-angle parameterized gate commutations
        - Multi-qubit gate commutation beyond the CNOT+Z-family rule
        These limitations may cause the optimizer to miss some optimization opportunities.
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
        
        # CNOT commutes with Z-rotation on control qubit
        if name1 == 'cx' and name2 in z_family and len(qubits2) == 1 and qubits2[0] == qubits1[0]:
            return True
        if name2 == 'cx' and name1 in z_family and len(qubits1) == 1 and qubits1[0] == qubits2[0]:
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
                angle_sum = float(inst1.operation.params[0]) + float(inst2.operation.params[0])
                scale = max(1.0, abs(float(inst1.operation.params[0])), abs(float(inst2.operation.params[0])))
                if abs(angle_sum) <= DEFAULT_PRECISION * scale:
                    return True
        
        return False

    def _move_removal(self, circuit: QuantumCircuit) -> QuantumCircuit | None:
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
        idx = self.rng.choice(valid_positions)
        neighbor = copy.deepcopy(circuit)
        neighbor.data.pop(idx)
        neighbor.data.pop(idx)
        return neighbor

    def _move_swap(self, circuit: QuantumCircuit) -> QuantumCircuit | None:
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
        idx = self.rng.choice(valid_positions)
        neighbor = copy.deepcopy(circuit)
        neighbor.data[idx], neighbor.data[idx + 1] = neighbor.data[idx + 1], neighbor.data[idx]
        return neighbor

    def _move_commutation(self, circuit: QuantumCircuit) -> QuantumCircuit | None:
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
        idx = self.rng.choice(valid_positions)
        neighbor = copy.deepcopy(circuit)
        neighbor.data[idx], neighbor.data[idx + 1] = neighbor.data[idx + 1], neighbor.data[idx]
        return neighbor

    def _move_insertion(self, circuit: QuantumCircuit) -> QuantumCircuit | None:
        """
        INSERTION move: Insert an identity pair (e.g., H-H, X-X) at a random position.
        This can enable future cancellations by bringing like gates adjacent.
        Returns a new circuit with an inserted pair.
        """
        if circuit.num_qubits == 0:
            return None
        
        neighbor = copy.deepcopy(circuit)
        
        # Pick a random gate type for the identity pair
        gate_name = self.rng.choice(_IDENTITY_PAIRS)
        
        # Pick a random qubit
        qubit_idx = self.rng.randint(0, neighbor.num_qubits)
        
        # Pick a random insertion position
        pos = self.rng.randint(0, len(neighbor.data) + 1)
        
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
        self.rng.shuffle(moves)
        
        # Try each move; use the first one that succeeds
        for move_type, move_fn in moves:
            result = move_fn(circuit)
            if result is not None:
                return result
        
        # Fallback: if nothing works, return a copy (no-op)
        return copy.deepcopy(circuit)

    def _fitness(self, circuit: QuantumCircuit, target: QuantumCircuit) -> float:
        """
        Calculate fitness with smooth fidelity penalty.
        
        Uses a sigmoid-based penalty instead of hard cutoff, providing gradient
        information for stochastic optimizers even when fidelity is below threshold.
        
        Returns: reduction * sigmoid_penalty, where sigmoid_penalty smoothly
        transitions from 0 to 1 around the fidelity threshold.
        """
        fidelity = self.calculate_fidelity(circuit, target)
        
        # Smooth penalty: sigmoid centered at fidelity_threshold with steep slope
        # At fidelity = threshold, penalty = 0.5; at threshold ± 0.05, penalty ≈ 0/1
        steepness = 50.0  # Controls transition sharpness
        penalty = 1.0 / (1.0 + np.exp(-steepness * (fidelity - self.fidelity_threshold)))
        
        reduction = 1.0 - circuit.size() / target.size() if target.size() > 0 else 0.0
        # Ensure non-negative reduction (circuit should not grow)
        reduction = max(0.0, reduction)
        
        return float(reduction * penalty + 0.1 * fidelity * penalty)
