"""
Phase 2b Optimizer: Template Matching
=====================================
Deterministic template rewrites for Clifford subcircuits.

The optimizer exposes two entry points:
  * ``optimize``                 — single template pass on the *as-listed* circuit.
  * ``optimize_full_pipeline``   — commutation reordering + template + HH cancel.

The single-pass ``optimize`` only fires on listing-adjacent H-CX-H patterns.
For circuits like the Bernstein–Vazirani oracle, where the H gates live in
separate layers from the CNOTs, the template cannot fire until a
commutation pre-pass brings the H gates next to their CNOTs.  The
``optimize_full_pipeline`` method performs that reordering and is the
correct entry point for validating Theorem 9 (review F1).
"""

from __future__ import annotations

import copy
import time

from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction
from qiskit.circuit.library import CXGate, HGate

from ..base import BaseOptimizer, OptimizationResult


class Phase2bTemplateMatcher(BaseOptimizer):
    """Apply local unitary-preserving Phase-2b templates."""

    def __init__(self, max_iterations: int = 100, fidelity_threshold: float = 0.99,
                 success_reduction: float = 0.20):
        super().__init__(fidelity_threshold, success_reduction)
        self.max_iterations = max_iterations

    def optimize(self, circuit: QuantumCircuit, target: QuantumCircuit | None = None) -> OptimizationResult:
        """Single template pass on the as-listed circuit (no reordering).

        This only fires on listing-adjacent H-CX-H patterns.  For circuits
        where H gates are in separate layers from CNOTs (e.g. BV oracle),
        use :meth:`optimize_full_pipeline` instead.
        """
        start_time = time.time()
        original = circuit
        optimized = copy.deepcopy(circuit)
        template_rewrites = 0
        hh_cancellations = 0

        template_rewrites = self._apply_h_cx_h_control_template(optimized)
        for _ in range(self.max_iterations):
            cancellations = self._cancel_adjacent_h_pairs(optimized)
            hh_cancellations += cancellations
            if cancellations == 0:
                break

        runtime = time.time() - start_time
        fidelity = 1.0 if target is None else self.calculate_fidelity(optimized, target)
        reduction = 1.0 - optimized.size() / original.size() if original.size() > 0 else 0.0

        return OptimizationResult(
            optimized_circuit=optimized,
            original_size=original.size(),
            optimized_size=optimized.size(),
            fidelity=fidelity,
            iterations=template_rewrites + hh_cancellations,
            runtime_seconds=runtime,
            success=self._is_success(reduction, fidelity),
            metadata={
                'algorithm': 'phase2b_template_matcher',
                'template_rewrites': template_rewrites,
                'hh_cancellations': hh_cancellations,
                'pipeline': 'single_pass',
                'version': '1.1.0',
            },
        )

    def optimize_full_pipeline(self, circuit: QuantumCircuit,
                                target: QuantumCircuit | None = None) -> OptimizationResult:
        """Full Phase-2b pipeline: reordering + template + HH cancellation.

        This is the correct entry point for validating Theorem 9 on BV
        oracle circuits (review F1).  The pipeline performs:

          1. **Commutation reordering** — bring each H gate next to the
             CNOT it sandwiches by bubbling it past gates on disjoint
             qubits.  This realizes Stage B-1 of the Thm 9 proof.
          2. **Template application** — rewrite each H-CX-H(control)
             pattern to H-CX-H with reversed CNOT direction (Stage B-2).
          3. **HH cancellation** — remove adjacent H-H pairs created by
             the template rewrites (Stage B-3).
          4. Repeat steps 1-3 until no further improvement.

        The reordering is a *sufficient* implementation of Stage B-1: it
        only moves H gates past gates on disjoint qubits, which is always
        a valid commutation.  It does not attempt the more aggressive
        CNOT-CNOT reordering of Lemma A1 (that is handled by the
        CommutationRewriter when run as part of a hybrid pipeline).
        """
        start_time = time.time()
        original = circuit
        optimized = copy.deepcopy(circuit)
        total_reorders = 0
        total_template_rewrites = 0
        total_hh_cancellations = 0

        for iteration in range(self.max_iterations):
            iter_reorders = self._reorder_h_next_to_cnots(optimized)
            iter_templates = self._apply_h_cx_h_control_template(optimized)
            iter_hh = 0
            for _ in range(self.max_iterations):
                c = self._cancel_adjacent_h_pairs(optimized)
                iter_hh += c
                if c == 0:
                    break
            total_reorders += iter_reorders
            total_template_rewrites += iter_templates
            total_hh_cancellations += iter_hh
            if iter_reorders == 0 and iter_templates == 0 and iter_hh == 0:
                break

        runtime = time.time() - start_time
        fidelity = 1.0 if target is None else self.calculate_fidelity(optimized, target)
        reduction = 1.0 - optimized.size() / original.size() if original.size() > 0 else 0.0

        return OptimizationResult(
            optimized_circuit=optimized,
            original_size=original.size(),
            optimized_size=optimized.size(),
            fidelity=fidelity,
            iterations=total_reorders + total_template_rewrites + total_hh_cancellations,
            runtime_seconds=runtime,
            success=self._is_success(reduction, fidelity),
            metadata={
                'algorithm': 'phase2b_template_matcher_full_pipeline',
                'template_rewrites': total_template_rewrites,
                'hh_cancellations': total_hh_cancellations,
                'h_reorders': total_reorders,
                'pipeline': 'full',
                'version': '1.1.0',
                'theorem_target': 'Thm 9 (BV oracle)',
            },
        )

    def _reorder_h_next_to_cnots(self, circuit: QuantumCircuit) -> int:
        """Bring H gates next to the CNOT they sandwich (Stage B-1 of Thm 9).

        For each H gate, look ahead within a window for the nearest CNOT
        that shares the H's qubit as its *control*.  Bubble the H gate
        rightward (or leftward) past any intermediate gates that act on
        disjoint qubits, which is always a valid commutation.  This
        realizes the disjoint-qubit commutation of Stage B-1.

        Returns the number of H-gate moves performed.
        """
        moves = 0
        window = 20  # search window for the matching CNOT
        i = 0
        while i < len(circuit.data):
            inst = circuit.data[i]
            if inst.operation.name != 'h':
                i += 1
                continue
            h_qubits = self._get_qubit_indices(circuit, inst)
            if len(h_qubits) != 1:
                i += 1
                continue
            h_q = h_qubits[0]

            # Search rightward for a CNOT whose control is h_q.
            target_j = -1
            for j in range(i + 1, min(i + window, len(circuit.data))):
                candidate = circuit.data[j]
                if candidate.operation.name in ('cx', 'cnot'):
                    cx_q, _ = self._cx_qubits(circuit, candidate)
                    if cx_q == h_q:
                        target_j = j
                        break
                # If we hit a gate that shares h_q and is NOT a commuting
                # gate, we cannot move past it — stop searching right.
                cand_qubits = set(self._get_qubit_indices(circuit, candidate))
                if h_q in cand_qubits and candidate.operation.name not in ('cx', 'cnot'):
                    # e.g. another H, or a rotation on h_q — these block
                    # rightward movement but the search for a CNOT can
                    # continue since the H might still reach a CNOT beyond.
                    pass

            if target_j > i + 1:
                # Bubble H rightward past disjoint-qubit intermediates.
                ok = True
                for k in range(i, target_j - 1):
                    left = circuit.data[k]
                    right = circuit.data[k + 1]
                    if self._gates_on_disjoint_qubits(circuit, left, right):
                        circuit.data[k], circuit.data[k + 1] = circuit.data[k + 1], circuit.data[k]
                        moves += 1
                    else:
                        ok = False
                        break
                if ok:
                    # H is now at target_j - 1, adjacent to the CNOT at target_j.
                    # Check if there is a matching H on the right of the CNOT
                    # to complete the sandwich — if so, leave it for the template.
                    pass

            # Also search leftward for a CNOT whose control is h_q
            # (the right H of a sandwich).  Only do this if we did not
            # already move rightward.
            if target_j <= i + 1:
                target_j_left = -1
                for j in range(i - 1, max(-1, i - window), -1):
                    candidate = circuit.data[j]
                    if candidate.operation.name in ('cx', 'cnot'):
                        cx_q, _ = self._cx_qubits(circuit, candidate)
                        if cx_q == h_q:
                            target_j_left = j
                            break
                if 0 <= target_j_left < i - 1:
                    ok = True
                    for k in range(i, target_j_left + 1, -1):
                        left = circuit.data[k - 1]
                        right = circuit.data[k]
                        if self._gates_on_disjoint_qubits(circuit, left, right):
                            circuit.data[k - 1], circuit.data[k] = circuit.data[k], circuit.data[k - 1]
                            moves += 1
                        else:
                            ok = False
                            break
            i += 1
        return moves

    def _apply_h_cx_h_control_template(self, circuit: QuantumCircuit) -> int:
        rewrites = 0
        i = 0
        while i <= len(circuit.data) - 3:
            first = circuit.data[i]
            middle = circuit.data[i + 1]
            last = circuit.data[i + 2]
            if self._is_h_cx_h_control(circuit, first, middle, last):
                control, target = self._cx_qubits(circuit, middle)
                self._replace_with_reversed_h_cx_h(circuit, i, control, target)
                rewrites += 1
                i += 3
            else:
                i += 1
        return rewrites

    def _cancel_adjacent_h_pairs(self, circuit: QuantumCircuit) -> int:
        cancellations = 0
        i = 0
        while i < len(circuit.data) - 1:
            if self._is_adjacent_h_pair(circuit, circuit.data[i], circuit.data[i + 1]):
                circuit.data.pop(i)
                circuit.data.pop(i)
                cancellations += 1
                if i > 0:
                    i -= 1
            else:
                i += 1
        return cancellations

    def _is_h_cx_h_control(self, circuit: QuantumCircuit, first, middle, last) -> bool:
        if first.operation.name != 'h' or middle.operation.name not in ('cx', 'cnot') or last.operation.name != 'h':
            return False
        first_qubits = self._get_qubit_indices(circuit, first)
        last_qubits = self._get_qubit_indices(circuit, last)
        cx_qubits = self._cx_qubits(circuit, middle)
        return len(first_qubits) == 1 and first_qubits == last_qubits and first_qubits[0] == cx_qubits[0]

    def _is_adjacent_h_pair(self, circuit: QuantumCircuit, first, second) -> bool:
        return (
            first.operation.name == 'h'
            and second.operation.name == 'h'
            and self._get_qubit_indices(circuit, first) == self._get_qubit_indices(circuit, second)
        )

    def _replace_with_reversed_h_cx_h(self, circuit: QuantumCircuit, index: int, control: int, target: int) -> None:
        for _ in range(3):
            circuit.data.pop(index)
        replacement = [
            CircuitInstruction(HGate(), (circuit.qubits[target],), ()),
            CircuitInstruction(CXGate(), (circuit.qubits[target], circuit.qubits[control]), ()),
            CircuitInstruction(HGate(), (circuit.qubits[target],), ()),
        ]
        for offset, instruction in enumerate(replacement):
            circuit.data.insert(index + offset, instruction)

    def _cx_qubits(self, circuit: QuantumCircuit, inst) -> tuple[int, int]:
        qubits = self._get_qubit_indices(circuit, inst)
        if len(qubits) != 2:
            return (-1, -1)
        return (qubits[0], qubits[1])
