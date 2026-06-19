"""Structural ceiling analysis for peephole circuit optimization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction

from src.optimisation.base import BaseOptimizer, OptimizationResult


class _ActionSpaceAnalyzer(BaseOptimizer):
    """Concrete wrapper exposing BaseOptimizer action predicates."""

    def optimize(self, circuit: QuantumCircuit, target: QuantumCircuit | None = None) -> OptimizationResult:
        return OptimizationResult(circuit.copy(), circuit.size(), circuit.size(), 1.0, 0, 0.0, False)


def _instruction_qubits(circuit: QuantumCircuit, inst: CircuitInstruction) -> tuple[int, ...]:
    return tuple(circuit.find_bit(q).index for q in inst.qubits)


def _are_inverse(circuit: QuantumCircuit, inst1: CircuitInstruction, inst2: CircuitInstruction) -> bool:
    """Check inverse relation on identical qubits using project-compatible rules."""
    name1 = inst1.operation.name
    name2 = inst2.operation.name
    if _instruction_qubits(circuit, inst1) != _instruction_qubits(circuit, inst2):
        return False
    if name1 == name2 and name1 in {"h", "x", "y", "z", "cx", "cz", "swap"}:
        return True
    if {name1, name2} == {"t", "tdg"}:
        return True
    if {name1, name2} == {"s", "sdg"}:
        return True
    if name1 == name2 and name1 in {"rx", "ry", "rz"}:
        if inst1.operation.params and inst2.operation.params:
            try:
                return abs(float(inst1.operation.params[0]) + float(inst2.operation.params[0])) < 1e-10
            except Exception:
                return False
    return False


def _is_mergeable_rotation(circuit: QuantumCircuit, inst1: CircuitInstruction, inst2: CircuitInstruction) -> bool:
    """Check if two adjacent instructions are mergeable parameterized rotations.

    NOTE: This function only detects rx/ry/rz mergeable pairs (same-axis rotations
    whose angles can be added). For gate sets that do NOT include parameterized
    rotations (e.g., Clifford+T = {H, S, T, CNOT, CZ}), this function returns
    False for all pairs, so ``mergeable_rotation_count`` will be 0.

    This is BY DESIGN, not a bug:
    - Clifford+T circuits do not contain rx/ry/rz gates, so there are no
      parameterized rotations to merge.
    - H/S/T "merging" is a different operation (cancellation or phase accumulation),
      captured by ``adjacent_cancellable_pairs`` and ``adjacent_commuting_pairs``.

    If the circuit family uses parameterized rotations (e.g., Universal with
    {Rx, Ry, Rz, CNOT}), this function correctly counts same-axis adjacent
    rotation pairs. The 47,401-row observation of mergeable_rotation_count=0
    in E13 is because E13 uses Clifford+T circuits (gate set {cp, h, ...}),
    which contain no rx/ry/rz gates.

    See: limitations_and_future_work.md §10 (conservative bounds).
    """
    if _instruction_qubits(circuit, inst1) != _instruction_qubits(circuit, inst2):
        return False
    return inst1.operation.name == inst2.operation.name and inst1.operation.name in {"rx", "ry", "rz"}


@dataclass(frozen=True)
class StructuralCeiling:
    """Structural ceiling metrics for one circuit."""

    adjacent_cancellable_pairs: int
    mergeable_rotation_pairs: int
    adjacent_commuting_pairs: int
    commutation_enabled_inverse_pairs: int
    theoretical_removed_gates_upper: int
    structural_upper_bound_reduction: float
    commuting_block_count: int
    mean_block_size: float
    max_block_size: int
    notes: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "adjacent_cancellable_pairs": self.adjacent_cancellable_pairs,
            "mergeable_rotation_pairs": self.mergeable_rotation_pairs,
            "adjacent_commuting_pairs": self.adjacent_commuting_pairs,
            "commutation_enabled_inverse_pairs": self.commutation_enabled_inverse_pairs,
            "theoretical_removed_gates_upper": self.theoretical_removed_gates_upper,
            "structural_upper_bound_reduction": self.structural_upper_bound_reduction,
            "commuting_block_count": self.commuting_block_count,
            "mean_block_size": self.mean_block_size,
            "max_block_size": self.max_block_size,
            "notes": self.notes,
        }


def analyze_structural_ceiling(circuit: QuantumCircuit, window: int = 10) -> StructuralCeiling:
    """Estimate local structural ceilings for Phase-1 and commutation-enabled peephole moves.

    This is an interpretable upper-bound proxy, not a proof of global optimality.
    It counts directly adjacent cancellable pairs and near-neighbor inverse pairs
    that can be brought together if all intermediate gates commute with the left gate.
    """
    analyzer = _ActionSpaceAnalyzer()
    n_inst = len(circuit.data)
    adjacent_cancellable = 0
    mergeable_rotation = 0
    adjacent_commuting = 0

    block_sizes: List[int] = []
    current_block = 1 if n_inst else 0
    for i in range(n_inst - 1):
        inst1 = circuit.data[i]
        inst2 = circuit.data[i + 1]
        if analyzer._is_self_inverse_pair(circuit, inst1, inst2):
            adjacent_cancellable += 1
        if _is_mergeable_rotation(circuit, inst1, inst2):
            mergeable_rotation += 1
        if analyzer._gates_commute(circuit, inst1, inst2):
            adjacent_commuting += 1
            current_block += 1
        else:
            if current_block:
                block_sizes.append(current_block)
            current_block = 1
    if current_block:
        block_sizes.append(current_block)

    commutation_enabled = 0
    for i in range(n_inst):
        inst_i = circuit.data[i]
        upper = min(n_inst, i + window)
        for j in range(i + 2, upper):
            inst_j = circuit.data[j]
            if not _are_inverse(circuit, inst_i, inst_j):
                continue
            if all(analyzer._gates_commute(circuit, inst_i, circuit.data[k]) for k in range(i + 1, j)):
                commutation_enabled += 1

    theoretical_removed = 2 * (adjacent_cancellable + commutation_enabled) + mergeable_rotation
    total = max(1, circuit.size())
    upper_reduction = min(1.0, theoretical_removed / total)
    notes = "upper-bound proxy; overlapping opportunities may double-count"
    return StructuralCeiling(
        adjacent_cancellable_pairs=adjacent_cancellable,
        mergeable_rotation_pairs=mergeable_rotation,
        adjacent_commuting_pairs=adjacent_commuting,
        commutation_enabled_inverse_pairs=commutation_enabled,
        theoretical_removed_gates_upper=theoretical_removed,
        structural_upper_bound_reduction=upper_reduction,
        commuting_block_count=len(block_sizes),
        mean_block_size=float(np.mean(block_sizes)) if block_sizes else 0.0,
        max_block_size=int(max(block_sizes)) if block_sizes else 0,
        notes=notes,
    )


def structural_metrics_json(circuit: QuantumCircuit, window: int = 10) -> str:
    """Return structural ceiling metrics as stable JSON."""
    return json.dumps(analyze_structural_ceiling(circuit, window=window).to_dict(), sort_keys=True, separators=(",", ":"))
