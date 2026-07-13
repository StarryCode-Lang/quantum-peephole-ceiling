"""
Tests for shared gate predicate functions in _gate_predicates.py.

Covers: qubit_indices, is_self_inverse_pair, is_mergeable_rotation, gates_commute.
Tests all commutation rules including the synced SWAP-SWAP, CZ-CZ, CNOT+X-family,
and CZ+Z-family rules.
"""

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import HGate, XGate, YGate, ZGate, CXGate, CZGate, \
    SGate, SdgGate, TGate, TdgGate, RXGate, RYGate, RZGate, SwapGate

from src.optimisation._gate_predicates import (
    qubit_indices,
    is_self_inverse_pair,
    is_mergeable_rotation,
    gates_commute,
)


@pytest.fixture
def circuit_3q():
    return QuantumCircuit(3)


@pytest.fixture
def circuit_2q():
    return QuantumCircuit(2)


class TestQubitIndices:
    def test_single_qubit_gate(self, circuit_3q):
        circuit_3q.append(HGate(), [0])
        inst = circuit_3q.data[0]
        assert qubit_indices(circuit_3q, inst) == [0]

    def test_two_qubit_gate(self, circuit_3q):
        circuit_3q.append(CXGate(), [0, 1])
        inst = circuit_3q.data[0]
        assert qubit_indices(circuit_3q, inst) == [0, 1]

    def test_invalid_instruction(self, circuit_3q):
        class FakeInst:
            qubits = []
        assert qubit_indices(circuit_3q, FakeInst()) == []


class TestIsSelfInversePair:
    def test_h_h_cancels(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(HGate(), [0])
        c.append(HGate(), [0])
        assert is_self_inverse_pair(c, c.data[0], c.data[1]) is True

    def test_x_x_cancels(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(XGate(), [0])
        c.append(XGate(), [0])
        assert is_self_inverse_pair(c, c.data[0], c.data[1]) is True

    def test_cnot_cnot_cancels(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(CXGate(), [0, 1])
        c.append(CXGate(), [0, 1])
        assert is_self_inverse_pair(c, c.data[0], c.data[1]) is True

    def test_t_tdg_cancels(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(TGate(), [0])
        c.append(TdgGate(), [0])
        assert is_self_inverse_pair(c, c.data[0], c.data[1]) is True

    def test_s_sdg_cancels(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(SGate(), [0])
        c.append(SdgGate(), [0])
        assert is_self_inverse_pair(c, c.data[0], c.data[1]) is True

    def test_rz_inverse_angles(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(RZGate(0.5), [0])
        c.append(RZGate(-0.5), [0])
        assert is_self_inverse_pair(c, c.data[0], c.data[1]) is True

    def test_different_qubits_no_cancel(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(HGate(), [0])
        c.append(HGate(), [1])
        assert is_self_inverse_pair(c, c.data[0], c.data[1]) is False

    def test_non_inverse_pair(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(TGate(), [0])
        c.append(TGate(), [0])
        assert is_self_inverse_pair(c, c.data[0], c.data[1]) is False

    def test_swap_swap_cancels(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(SwapGate(), [0, 1])
        c.append(SwapGate(), [0, 1])
        assert is_self_inverse_pair(c, c.data[0], c.data[1]) is True


class TestIsMergeableRotation:
    def test_rz_rz_mergeable(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(RZGate(0.3), [0])
        c.append(RZGate(0.5), [0])
        assert is_mergeable_rotation(c, c.data[0], c.data[1]) is True

    def test_rx_rx_mergeable(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(RXGate(0.3), [0])
        c.append(RXGate(0.5), [0])
        assert is_mergeable_rotation(c, c.data[0], c.data[1]) is True

    def test_rz_rx_not_mergeable(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(RZGate(0.3), [0])
        c.append(RXGate(0.5), [0])
        assert is_mergeable_rotation(c, c.data[0], c.data[1]) is False

    def test_different_qubits_not_mergeable(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(RZGate(0.3), [0])
        c.append(RZGate(0.5), [1])
        assert is_mergeable_rotation(c, c.data[0], c.data[1]) is False


class TestGatesCommute:
    def test_disjoint_qubits_commute(self, circuit_3q):
        c = QuantumCircuit(3)
        c.append(HGate(), [0])
        c.append(XGate(), [1])
        assert gates_commute(c, c.data[0], c.data[1]) is True

    def test_same_gate_same_qubit_commutes(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(HGate(), [0])
        c.append(HGate(), [0])
        assert gates_commute(c, c.data[0], c.data[1]) is True

    def test_z_family_commute(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(ZGate(), [0])
        c.append(SGate(), [0])
        assert gates_commute(c, c.data[0], c.data[1]) is True

    def test_cnot_z_control_commute(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(CXGate(), [0, 1])
        c.append(ZGate(), [0])
        assert gates_commute(c, c.data[0], c.data[1]) is True

    def test_cnot_x_target_commute(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(CXGate(), [0, 1])
        c.append(XGate(), [1])
        assert gates_commute(c, c.data[0], c.data[1]) is True

    def test_cnot_rx_target_commute(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(CXGate(), [0, 1])
        c.append(RXGate(0.5), [1])
        assert gates_commute(c, c.data[0], c.data[1]) is True

    def test_cz_z_family_commute(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(CZGate(), [0, 1])
        c.append(ZGate(), [0])
        assert gates_commute(c, c.data[0], c.data[1]) is True

    def test_cz_z_family_other_qubit(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(CZGate(), [0, 1])
        c.append(TGate(), [1])
        assert gates_commute(c, c.data[0], c.data[1]) is True

    def test_swap_swap_same_pair_commute(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(SwapGate(), [0, 1])
        c.append(SwapGate(), [0, 1])
        assert gates_commute(c, c.data[0], c.data[1]) is True

    def test_cz_cz_same_pair_commute(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(CZGate(), [0, 1])
        c.append(CZGate(), [0, 1])
        assert gates_commute(c, c.data[0], c.data[1]) is True

    def test_non_commuting_h_cnot(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(HGate(), [0])
        c.append(CXGate(), [0, 1])
        assert gates_commute(c, c.data[0], c.data[1]) is False

    def test_non_commuting_x_z(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(XGate(), [0])
        c.append(ZGate(), [0])
        assert gates_commute(c, c.data[0], c.data[1]) is False

    def test_rz_rz_same_axis_commute(self, circuit_2q):
        c = QuantumCircuit(2)
        c.append(RZGate(0.3), [0])
        c.append(RZGate(0.5), [0])
        assert gates_commute(c, c.data[0], c.data[1]) is True
