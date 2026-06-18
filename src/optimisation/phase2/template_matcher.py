"""
Phase 2b Optimizer: Template Matching
=====================================
Deterministic template rewrites for Clifford subcircuits.
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
                'version': '1.0.0',
            },
        )

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
