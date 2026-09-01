"""Tests for the Qiskit-numerics-independent E31 semantic verifier."""

import numpy as np
import pytest
from qiskit import QuantumCircuit

from analysis.e31_native_semantic_verifier import (
    NativeSemanticFailure,
    compare_pair,
    probe_states,
    simulate,
)


def _all_basis(n: int) -> np.ndarray:
    return np.eye(1 << n, dtype=np.complex128)


def test_native_kernel_accepts_global_phase_and_composite_identities():
    original = QuantumCircuit(3)
    original.h(0)
    original.cp(0.37, 0, 2)
    original.crz(-0.21, 1, 2)
    original.ccx(0, 1, 2)
    optimized = original.copy()
    optimized.global_phase = 0.731
    result = compare_pair(original, optimized, _all_basis(3), 1e-12)
    assert result["maximum_phase_aligned_state_residual"] < 1e-12


def test_native_kernel_kills_semantic_mutant_and_fails_closed():
    identity = QuantumCircuit(1)
    mutant = QuantumCircuit(1)
    mutant.x(0)
    with pytest.raises(NativeSemanticFailure, match="residual"):
        compare_pair(identity, mutant, _all_basis(1), 1e-12)

    unsupported = QuantumCircuit(1, 1)
    unsupported.measure(0, 0)
    with pytest.raises(NativeSemanticFailure, match="unsupported operation"):
        simulate(unsupported, _all_basis(1))


def test_native_kernel_respects_qiskit_little_endian_control_target_order():
    cx = QuantumCircuit(2)
    cx.cx(0, 1)
    evolved = simulate(cx, _all_basis(2))
    # q0 is the least-significant bit: |01> maps to |11>, while |10> is fixed.
    assert np.argmax(np.abs(evolved[:, 1])) == 3
    assert np.argmax(np.abs(evolved[:, 2])) == 2

    ccx = QuantumCircuit(3)
    ccx.ccx(0, 1, 2)
    evolved = simulate(ccx, _all_basis(3))
    assert np.argmax(np.abs(evolved[:, 3])) == 7
    assert np.argmax(np.abs(evolved[:, 7])) == 3


def test_large_probe_set_is_deterministic_normalized_and_anchored():
    first, mode = probe_states(7, "a" * 64, exact_max_qubits=6, samples=8)
    second, _ = probe_states(7, "a" * 64, exact_max_qubits=6, samples=8)
    assert mode == "two_basis_anchors_plus_normalized_complex_gaussian"
    assert np.array_equal(first, second)
    assert first.shape == (128, 10)
    assert np.allclose(np.linalg.norm(first, axis=0), 1.0)
    assert first[0, 0] == 1 and first[-1, 1] == 1
