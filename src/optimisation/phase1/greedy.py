"""
Greedy Gate Cancellation Optimizer - Phase 1
============================================
Deterministic adjacent-search optimizer with rotation merging.

Version: 3.2.0 (Added WCL preprocessing via wire_traversal parameter)
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from ..constants import DEFAULT_PRECISION
import copy
import time

from ..base import BaseOptimizer, OptimizationResult
from .wire_traversal import WireTraversalPreprocessor


class GreedyGateCancellation(BaseOptimizer):
    """
    Greedy gate cancellation optimizer.
    
    Cancels adjacent inverse gates and applies commutation rules.
    Preserves functionality by construction.
    
    CRITICAL FIX (v3.0.0): _are_inverse() now correctly checks qubit matching
    before declaring two gates as inverses. Previous versions (v1.x) had a bug
    where gates on different qubits could be incorrectly cancelled.
    
    WCL Preprocessing (v3.2.0): When ``wire_traversal=True``, gates are
    reordered into Wire-Consecutive Listing before the greedy scan.  This
    expands the Phase 1 action space by making same-qubit gates adjacent
    in the listing, potentially exposing cancellations that LBL listing
    hides (Theorem 1(b)).

    Complexity
    ----------
    Let m = gate count, c = cancellations performed in one pass.

    * Per step: the cancellation scan is one pass over the O(m) adjacent
      pairs with O(1) predicate checks (see ``BaseOptimizer`` complexity
      model); each cancellation is two ``list.pop(i)`` operations at
      O(m) each, so one pass costs O(m + c * m) = O((c + 1) * m).
      The rotation-merge scan is O(m) comparisons; each merge is O(m)
      (two pops), and it is retried until no further merge exists.
    * Overall: each improving pass removes >= 1 gate, so there are at
      most m passes; measured convergence is 1-3 passes on the benchmark
      families (manuscript Section 5.1).  Worst case O(m^2) per pass
      when c = Theta(m), O(m^3) pathological overall; typical case O(m)
      with a small constant (measured log-log slope ~1.0 vs m; see
      docs/analysis/algorithmic_complexity.md Part A2).
    * With ``wire_traversal=True``: plus O(m log m) WCL preprocessing
      (see ``WireTraversalPreprocessor``).
    * Plus one final ``calculate_fidelity`` call when a target is given:
      O(m * 4**n + 8**n) for n <= 12 (see ``BaseOptimizer``).
    """
    
    def __init__(self, max_iterations: int = 100, fidelity_threshold: float = 0.99,
                 success_reduction: float = 0.20, wire_traversal: bool = False,
                 enable_numeric_commutation: bool = False,
                 commutation_tolerance: float = DEFAULT_PRECISION):
        super().__init__(fidelity_threshold, success_reduction,
                         enable_numeric_commutation=enable_numeric_commutation,
                         commutation_tolerance=commutation_tolerance)
        self.max_iterations = max_iterations
        self.wire_traversal = wire_traversal
        self._wcl_preprocessor = WireTraversalPreprocessor() if wire_traversal else None
    
    def optimize(self, circuit: QuantumCircuit, target: QuantumCircuit | None = None) -> OptimizationResult:
        """Optimize using greedy gate cancellation.

        When ``self.wire_traversal`` is True, the circuit is first reordered
        into Wire-Consecutive Listing (WCL) before the greedy scan.  WCL
        preserves unitary equivalence but makes same-qubit gates adjacent,
        expanding the set of adjacent pairs the greedy scanner can inspect.
        """
        start_time = time.time()
        original = circuit

        # Apply WCL preprocessing if requested
        if self._wcl_preprocessor is not None:
            optimized = self._wcl_preprocessor.preprocess(circuit)
        else:
            optimized = copy.deepcopy(circuit)
        
        improvements = 0
        
        for iteration in range(self.max_iterations):
            improved = False
            
            # Phase 1: Cancel adjacent inverse gates
            i = 0
            while i < len(optimized.data) - 1:
                if self._is_self_inverse_pair(optimized, optimized.data[i], optimized.data[i + 1]):
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
            metadata={'algorithm': 'greedy', 'improvements': improvements,
                      'version': '3.2.0', 'wire_traversal': self.wire_traversal}
        )
    
    def _merge_rotations(self, circuit: QuantumCircuit) -> bool:
        """Merge consecutive rotation gates on the same qubit.

        Combines R(a1) followed by R(a2) on the same qubit into R(a1 + a2).
        The merged angle is reduced to the canonical [-pi, pi) range.

        CRITICAL (v3.1.0): R(2*pi) = -I (global phase), NOT identity.
        Therefore, gates whose angles sum to a non-zero multiple of 2*pi
        must NOT be removed -- they contribute a global phase of -1.
        Only when the reduced angle is ~0 (i.e., the raw sum is ~0, meaning
        R(0) = I) are both gates safely removed.

        Applies to all rotation gate types: Rx, Ry, Rz.

        NOTE (Qiskit 2.x): circuit.data[i].operation returns a fresh object
        on each access, so direct mutation of operation.params[0] is silently
        lost.  We use CircuitInstruction.replace() to atomically swap in a
        new gate with the merged angle.
        """
        # Gate class lookup for creating merged rotation gates.
        from qiskit.circuit.library import RZGate, RXGate, RYGate
        _ROTATION_GATE_CLASS = {'rz': RZGate, 'rx': RXGate, 'ry': RYGate}

        improved = False
        
        for i in range(len(circuit.data) - 1):
            try:
                gate1 = circuit.data[i].operation.name
                gate2 = circuit.data[i + 1].operation.name
                
                # Check if same qubit
                qubits1 = [circuit.find_bit(q).index for q in circuit.data[i].qubits]
                qubits2 = [circuit.find_bit(q).index for q in circuit.data[i + 1].qubits]
                
                if qubits1 == qubits2 and gate1 == gate2 and gate1 in ('rz', 'rx', 'ry'):
                    # Merge angles
                    angle1 = circuit.data[i].operation.params[0]
                    angle2 = circuit.data[i + 1].operation.params[0]
                    raw_sum = angle1 + angle2
                    
                    # Reduce to canonical [-pi, pi) range.
                    # This correctly maps multiples of 2*pi to 0:
                    #   raw_sum = 2*pi  ->  reduced = 0  (R(2pi) = -I, NOT removable)
                    #   raw_sum = 0     ->  reduced = 0  (R(0) = I, removable)
                    #   raw_sum = pi    ->  reduced = -pi (boundary, see NOTE below)
                    #
                    # NOTE (boundary behavior at raw_sum = -pi):
                    #   When raw_sum = -pi: (-pi + pi) % (2*pi) - pi = 0 - pi = -pi.
                    #   When raw_sum = +pi: (+pi + pi) % (2*pi) - pi = 0 - pi = -pi.
                    #   Both -pi and +pi map to the canonical value -pi, which is
                    #   mathematically correct since R(-pi) = R(+pi) (global phase).
                    #   The boundary is consistent: the canonical interval is [-pi, pi),
                    #   and -pi is the representative for the angle +/- pi.
                    reduced = ((raw_sum + np.pi) % (2 * np.pi)) - np.pi
                    
                    # Guard: ensure boundary consistency for the exact -pi case.
                    # np.fmod and % may produce -0.0 in some edge cases; normalize to +0.0.
                    if reduced == 0.0:
                        reduced = 0.0  # Canonical positive zero
                    # Note: Python's % operator ensures reduced is always in [-pi, pi).
                    # Edge case: raw_sum = -pi -> (-pi + pi) % (2*pi) - pi = -pi (correct).
                    
                    gate_cls = _ROTATION_GATE_CLASS[gate1]

                    if abs(reduced) < DEFAULT_PRECISION:
                        # Reduced angle is near zero.  Two sub-cases:
                        #
                        # 1) raw_sum ~ 0:  R(0) = I  (true identity).
                        #    Both gates are safely removed.
                        #
                        # 2) raw_sum ~ 2k*pi (k != 0):  R(2k*pi) = (-I)^k.
                        #    This is a global phase, NOT identity.
                        #    Must NOT remove -- keep a single gate with the
                        #    raw_sum angle to preserve the unitary exactly.
                        if abs(raw_sum) < DEFAULT_PRECISION:
                            # True identity: R(0) = I.  Remove both gates.
                            circuit.data.pop(i)
                            circuit.data.pop(i)
                        else:
                            # raw_sum is a non-zero multiple of 2*pi.
                            # Keep as a single gate with raw_sum angle to
                            # preserve the unitary (e.g., Rz(2pi) = -I).
                            new_gate = gate_cls(raw_sum)
                            circuit.data[i] = circuit.data[i].replace(operation=new_gate)
                            circuit.data.pop(i + 1)
                    else:
                        # Non-trivial merged angle: replace two gates with one.
                        # Use the reduced (canonical [-pi, pi)) representation.
                        new_gate = gate_cls(reduced)
                        circuit.data[i] = circuit.data[i].replace(operation=new_gate)
                        circuit.data.pop(i + 1)
                    
                    improved = True
                    break
            except (IndexError, AttributeError):
                continue
        
        return improved
