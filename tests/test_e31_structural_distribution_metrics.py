"""Tests for post-seal E31 structural and distributional metrics."""

from __future__ import annotations

import pandas as pd
import pytest
from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister

from analysis.e31_structural_distribution_metrics import (
    circuit_structural_metrics,
    distributional_metrics,
)
from scripts.verify_e31_structural_distribution_metrics import _independent_metrics


def test_structural_metrics_are_exact_for_logical_qpy_representation():
    qubits = QuantumRegister(3, "q")
    ancilla = AncillaRegister(1, "a")
    classical = ClassicalRegister(1, "c")
    circuit = QuantumCircuit(qubits, ancilla, classical)
    circuit.h(qubits[0])
    circuit.cx(qubits[0], qubits[1])
    circuit.swap(qubits[1], qubits[2])
    circuit.ccx(qubits[0], qubits[1], ancilla[0])
    circuit.t(qubits[2])
    circuit.measure(qubits[2], classical[0])
    circuit.reset(ancilla[0])

    metrics = circuit_structural_metrics(circuit)
    assert metrics["declared_qubits"] == 4
    assert metrics["ancilla_qubits"] == 1
    assert metrics["active_qubits_static"] == 4
    assert metrics["multi_qubit_gate_count"] == 3
    assert metrics["two_qubit_gate_count"] == 2
    assert metrics["two_qubit_depth"] == 2
    assert metrics["measurement_count"] == metrics["reset_count"] == 1
    assert metrics["swap_count"] == metrics["toffoli_ccz_count"] == 1
    assert metrics["logical_t_tdg_count"] == metrics["logical_t_tdg_layer_depth"] == 1
    assert metrics["interaction_graph_pair_edges"] == 4
    assert metrics["interaction_graph_density"] == pytest.approx(4 / 6)
    assert metrics["contains_non_clifford_t_operations"] is True
    independently_recomputed = _independent_metrics(circuit)
    assert independently_recomputed == metrics


def test_distributional_metrics_fail_closed_and_include_zero_success_inputs():
    results = pd.DataFrame({
        "run_id": ["r1", "r2", "r3", "r4"],
        "input_circuit_sha256": ["a", "a", "b", "b"],
        "status": ["success", "success", "timeout", "error"],
        "common_basis_gate_reduction_pct": [-5.0, 10.0, None, None],
        "output_circuit_sha256": ["x", "y", None, None],
    })
    design = pd.DataFrame({
        "input_circuit_sha256": ["a", "b"],
        "circuit_id": ["A", "B"],
        "circuit_family": ["F1", "F2"],
    })
    summary, diversity = distributional_metrics(results, design)
    assert summary["successful_regression_count"] == 1
    assert summary["successful_regression_probability"] == pytest.approx(0.5)
    assert summary["successful_expansion_probability_by_threshold"][
        "increase_ge_5pct"
    ] == pytest.approx(0.5)
    assert summary["itt_zero_for_non_success_reduction_quantiles_pp"]["q50"] == 0.0
    no_success = diversity.loc[diversity["input_circuit_sha256"].eq("b")].iloc[0]
    assert no_success["successful_rows"] == 0
    assert no_success["unique_output_circuits"] == 0
