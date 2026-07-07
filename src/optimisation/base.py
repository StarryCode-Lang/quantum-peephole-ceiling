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
    
    def __init__(self, fidelity_threshold: float = 0.99, success_reduction: float = 0.05,
                 random_seed: int | None = None, enable_numeric_commutation: bool = False,
                 commutation_tolerance: float = DEFAULT_PRECISION):
        """
        Args:
            fidelity_threshold: Minimum fidelity to consider optimization valid
            success_reduction: Minimum gate reduction (fraction) for an optimization
                to be flagged as ``meaningful`` (see ``_is_meaningful``). This is
                retained for backward compatibility. The ``_is_success`` contract
                now treats *success* as fidelity compliance only; the higher bar of
                ``success_reduction`` is reported separately as ``meaningful``.
            random_seed: Optional seed for optimizer-internal stochastic moves
            enable_numeric_commutation: Enable exact 1-2 qubit matrix commutator
                fallback when rule-based checks do not prove commutation. Disabled
                by default to preserve deterministic v6 rule-based behavior.
            commutation_tolerance: Absolute tolerance for the numerical commutator
                fallback, applied with numpy.allclose(..., atol=tolerance, rtol=0).

        Note on threshold choice (bug #5 fix):
            The previous default of ``0.20`` (20%) caused artificially high failure
            rates in E10/E11 because many genuinely-optimized circuits that preserve
            fidelity achieve <20% reduction. The new default of ``0.05`` (5%) aligns
            with the recommendation in ``data/DATA_CANONICAL.md`` and separates
            *success* (fidelity compliance) from *meaningful reduction* (threshold
            crossing), avoiding conflation of the two concepts.
        """
        self.fidelity_threshold = fidelity_threshold
        self.success_reduction = success_reduction
        self.random_seed = random_seed
        self.enable_numeric_commutation = enable_numeric_commutation
        self.commutation_tolerance = commutation_tolerance
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
            #
            # WARNING: This fallback computes a Jaccard-style gate-type overlap
            # (Counter intersection / union of gate-type counts). It is a
            # STRUCTURAL HEURISTIC, not a quantum fidelity measure:
            #   - It ignores gate order, qubit assignment, and angles.
            #   - Its correlation with true average gate fidelity has NOT been
            #     characterized (no calibration study exists).
            #   - It may over-estimate fidelity for circuits with the same gate
            #     multiset but different topology.
            #
            # Experimental impact: this fallback is triggered for large circuits
            # (n > max_qubits_fidelity) where exact unitary comparison is
            # infeasible. If a significant fraction of experimental trials
            # fall through to this path, the reported fidelity values for those
            # trials are heuristic estimates, not verified fidelities.
            #
            # See: limitations_and_future_work.md §10 (conservative bounds /
            #      uncharacterized fallback precision).
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
        """Determine if optimization was successful (fidelity-compliant).

        As of bug #5 fix, ``success`` is defined by fidelity compliance only.
        This avoids penalizing circuits that legitimately preserve functionality
        but achieve a small reduction. Use :meth:`_is_meaningful` to additionally
        require the reduction to cross ``success_reduction``.
        """
        return fidelity >= self.fidelity_threshold

    def _is_meaningful(self, reduction: float, fidelity: float) -> bool:
        """Determine if the optimization achieved a *meaningful* reduction.

        A meaningful optimization both preserves functionality (fidelity
        compliance, as in :meth:`_is_success`) AND crosses the
        ``success_reduction`` threshold. Callers that previously relied on
        ``_is_success`` requiring both conditions should switch here to keep
        the old, stricter semantics.
        """
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
                       inst2: CircuitInstruction,
                       use_numeric_fallback: bool | None = None,
                       tolerance: float | None = None) -> bool:
        """
        Check if two gate instructions commute.

        Conservative by default: returns True only for proven commuting cases;
        may return False for actually-commuting gate pairs. This preserves the
        deterministic rule-based v6 behavior. Set ``use_numeric_fallback=True``
        (or ``BaseOptimizer(..., enable_numeric_commutation=True)``) to run a
        bounded numerical fallback for one- and two-qubit gates whose combined
        support has at most two qubits. The fallback compares UV and VU with
        ``numpy.allclose(..., atol=tolerance, rtol=0)``; the default tolerance is
        ``DEFAULT_PRECISION``.

        Sufficient conditions for commutation checked here:
        1. Gates act on disjoint qubit sets
        2. Both are diagonal in the same basis (e.g., Rz gates)
        3. Both are the same single-qubit gate on the same qubit
        4. CNOT commutes with Z-family rotations on its control qubit
        5. Two SWAP gates on the same qubit pair commute (bug #11 fix)
        6. Two CZ gates on the same qubit pair commute (bug #11 fix)

        NOTE: Unless numeric fallback is enabled, this method checks SUFFICIENT
        conditions for commutation, not necessary conditions. Some valid
        commutation relationships may be missed.
        """
        numeric_fallback = self.enable_numeric_commutation if use_numeric_fallback is None else use_numeric_fallback
        numeric_tolerance = self.commutation_tolerance if tolerance is None else tolerance

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

        # SWAP gates commute with each other when acting on the same qubit pair
        # (bug #11 fix). Two SWAPs on the same pair compose as SWAP*SWAP = I,
        # hence they certainly commute. Treat the pair as an unordered set so
        # that (q0,q1) and (q1,q0) refer to the same logical pair.
        if name1 == 'swap' and name2 == 'swap' and len(qubits1) == 2 and len(qubits2) == 2:
            if set(qubits1) == set(qubits2):
                return True

        # CZ gates commute with each other on the same qubit pair (bug #11 fix).
        # CZ is diagonal (it is a controlled-Z = diag(1,1,1,-1)), and diagonal
        # operators always commute; the same unordered-pair test handles
        # control/target symmetry.
        if name1 == 'cz' and name2 == 'cz' and len(qubits1) == 2 and len(qubits2) == 2:
            if set(qubits1) == set(qubits2):
                return True

        if numeric_fallback:
            return self._gates_commute_numerically(inst1, inst2, qubits1, qubits2, numeric_tolerance)

        return False

    def _gates_commute_numerically(self,
                                   inst1: CircuitInstruction,
                                   inst2: CircuitInstruction,
                                   qubits1: list[int],
                                   qubits2: list[int],
                                   tolerance: float) -> bool:
        """Numerically test commutation for gates on at most two combined qubits."""
        support = sorted(set(qubits1) | set(qubits2))
        if not support or len(support) > 2:
            return False
        if inst1.operation.num_qubits > 2 or inst2.operation.num_qubits > 2:
            return False

        try:
            local_circuit_12 = QuantumCircuit(len(support))
            local_circuit_21 = QuantumCircuit(len(support))
            index = {qubit: i for i, qubit in enumerate(support)}
            local_qubits1 = [index[qubit] for qubit in qubits1]
            local_qubits2 = [index[qubit] for qubit in qubits2]

            local_circuit_12.append(inst1.operation, local_qubits1)
            local_circuit_12.append(inst2.operation, local_qubits2)
            local_circuit_21.append(inst2.operation, local_qubits2)
            local_circuit_21.append(inst1.operation, local_qubits1)

            u12 = np.array(Operator(local_circuit_12).data)
            u21 = np.array(Operator(local_circuit_21).data)
            return bool(np.allclose(u12, u21, atol=tolerance, rtol=0.0))
        except Exception as e:
            self.logger.debug(f"Numerical commutation check failed: {e}")
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
        Calculate fitness with smooth fidelity penalty and cancellation potential.

        Uses a sigmoid-based penalty instead of hard cutoff, providing gradient
        information for stochastic optimizers even when fidelity is below threshold.

        Returns: reduction * sigmoid_penalty + cancellation_potential_bonus.

        Review Stage 6 / fitness insertion bias fix:
        Previously, INSERTION moves (which add 2 gates) always decreased
        fitness because they increased circuit.size(), making reduction
        negative (clamped to 0).  This meant stochastic optimizers
        effectively never used insertion, even though insertion can
        enable future cancellations.  We now add a small "potential"
        bonus proportional to the number of adjacent cancellable pairs
        in the circuit, giving insertion moves a gradient signal when
        they create cancellation opportunities.  The bonus coefficient
        (0.01) is small enough not to dominate the reduction objective.
        """
        fidelity = self.calculate_fidelity(circuit, target)

        # Smooth penalty: sigmoid centered at fidelity_threshold with steep slope
        # At fidelity = threshold, penalty = 0.5; at threshold ± 0.05, penalty ≈ 0/1
        steepness = 50.0  # Controls transition sharpness
        penalty = 1.0 / (1.0 + np.exp(-steepness * (fidelity - self.fidelity_threshold)))

        # Guard against division by zero when target is empty; use explicit
        # conditional rather than a fragile inline ternary for clarity.
        target_size = target.size()
        if target_size > 0:
            reduction = 1.0 - circuit.size() / target_size
        else:
            reduction = 0.0
        # Ensure non-negative reduction (circuit should not grow)
        reduction = max(0.0, reduction)

        # Reward term only applies when some reduction was actually achieved,
        # to avoid rewarding no-ops or circuits that grew while keeping fidelity.
        reward = 0.1 * fidelity * penalty if reduction > 0.0 else 0.0

        # Cancellation potential bonus (review Stage 6 fix).
        # Count adjacent self-inverse / mergeable pairs that could be
        # cancelled in the next move.  This gives INSERTION moves a
        # positive gradient when they bring inverse gates together.
        # The coefficient is deliberately small (0.01) so the bonus
        # never dominates the primary reduction objective.
        potential_bonus = 0.0
        if len(circuit.data) >= 2:
            cancellable = 0
            for i in range(len(circuit.data) - 1):
                if self._is_self_inverse_pair(circuit, circuit.data[i], circuit.data[i + 1]):
                    cancellable += 1
            potential_bonus = 0.01 * cancellable * penalty

        return float(reduction * penalty + reward + potential_bonus)
