"""Regression tests for the large-circuit fidelity estimator."""

import math

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit import qasm2

from src.equivalence import (
    EquivalenceCertificate,
    EquivalenceMethod,
    EquivalenceStatus,
    certify_equivalence,
)
from src.optimisation.base import BaseOptimizer, OptimizationResult
from src.optimisation.phase1.greedy import GreedyGateCancellation


class _FidelityTestOptimizer(BaseOptimizer):
    def optimize(self, circuit, target=None):
        return OptimizationResult(circuit.copy(), circuit.size(), circuit.size(), 1.0, 0, 0.0, True)


def test_global_sampling_does_not_treat_local_error_as_high_fidelity():
    """Global Haar sampling must converge near 1/(2**n + 1) for a local X error."""
    n_qubits = 5
    circuit = QuantumCircuit(n_qubits)
    circuit.x(0)
    target = QuantumCircuit(n_qubits)
    optimizer = _FidelityTestOptimizer(random_seed=123)

    exact = optimizer.calculate_fidelity(circuit, target)
    estimate = optimizer._estimate_fidelity(circuit, target, n_samples=1000)

    assert exact == 1 / (2**n_qubits + 1)
    assert estimate < 0.12


def test_identical_circuits_have_unit_fidelity():
    """Fidelity of a circuit against itself must be 1.0 up to float roundoff."""
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.t(2)
    optimizer = _FidelityTestOptimizer(random_seed=7)
    assert abs(optimizer.calculate_fidelity(circuit, circuit.copy()) - 1.0) < 1e-9


def test_known_analytic_fidelity_value():
    """Single X error on 2 qubits: F = d/(d^2 + d) = 0.2 exactly (d = 4)."""
    circuit = QuantumCircuit(2)
    circuit.x(0)
    target = QuantumCircuit(2)
    optimizer = _FidelityTestOptimizer(random_seed=7)
    exact = optimizer.calculate_fidelity(circuit, target)
    assert abs(exact - 0.2) < 1e-12


def test_fidelity_is_deterministic_across_calls():
    """Repeated exact evaluations must agree bit-for-bit."""
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 2)
    target = QuantumCircuit(3)
    target.h(1)
    optimizer = _FidelityTestOptimizer(random_seed=7)
    first = optimizer.calculate_fidelity(circuit, target)
    second = optimizer.calculate_fidelity(circuit, target)
    assert first == second


def test_sampling_estimator_tracks_exact_value():
    """The sampling estimator must stay within Monte-Carlo noise of the exact value."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    target = QuantumCircuit(2)
    optimizer = _FidelityTestOptimizer(random_seed=99)
    exact = optimizer.calculate_fidelity(circuit, target)
    estimate = optimizer._estimate_fidelity(circuit, target, n_samples=2000)
    assert abs(estimate - exact) < 0.08


def test_sampling_failure_is_unavailable_not_structural_similarity(monkeypatch):
    """An execution failure must fail closed instead of returning Jaccard."""
    from qiskit.quantum_info import Statevector
    import src.optimisation.base as base_module

    circuit = QuantumCircuit(2)
    circuit.x(0)
    target = QuantumCircuit(2)
    optimizer = _FidelityTestOptimizer(random_seed=5)

    def _raise(*args, **kwargs):
        raise RuntimeError("forced evolution failure")

    monkeypatch.setattr(Statevector, "evolve", _raise)
    monkeypatch.setattr(base_module, "Operator", _raise)
    estimate = optimizer._estimate_fidelity(circuit, target, n_samples=1)

    assert math.isnan(estimate)
    assert not optimizer.verify_functionality(circuit, target)


def test_exact_operator_failure_uses_sampled_estimator(monkeypatch):
    """A failed exact calculation is unavailable work, not physical F=0."""
    import src.equivalence as equivalence_module

    circuit = QuantumCircuit(2)
    circuit.h(0)
    target = QuantumCircuit(2)
    optimizer = _FidelityTestOptimizer(random_seed=5)

    def _raise(*args, **kwargs):
        raise MemoryError("forced exact-unitary failure")

    monkeypatch.setattr(equivalence_module, "Operator", _raise)
    certificate = optimizer.equivalence_certificate(circuit, target)

    assert certificate.method is EquivalenceMethod.SAMPLED_GLOBAL_HAAR
    assert certificate.status in {
        EquivalenceStatus.ESTIMATED_EQUIVALENT,
        EquivalenceStatus.ESTIMATED_NOT_EQUIVALENT,
    }
    assert certificate.standard_error is not None


def test_success_is_validity_and_meaningful_adds_reduction_threshold():
    optimizer = _FidelityTestOptimizer(
        fidelity_threshold=0.99,
        success_reduction=0.05,
    )

    assert optimizer._is_success(0.05, 0.99)
    assert optimizer._is_success(0.0, 1.0)
    assert not optimizer._is_success(0.10, 0.98)
    assert optimizer._is_meaningful(0.05, 0.99)
    assert not optimizer._is_meaningful(0.0, 1.0)


def test_rotation_inverse_predicate_respects_two_pi_periodicity():
    optimizer = _FidelityTestOptimizer()
    circuit = QuantumCircuit(1)
    circuit.rz(0.3, 0)
    circuit.rz(2 * math.pi - 0.3, 0)

    assert optimizer._is_self_inverse_pair(circuit, circuit.data[0], circuit.data[1])


def test_certificate_records_method_scope_threshold_and_evidence():
    circuit = QuantumCircuit(1)
    circuit.h(0)
    target = circuit.copy()

    certificate = certify_equivalence(circuit, target, threshold=1 - 1e-10)
    record = certificate.to_dict()

    assert record["method"] == "exact_structural"
    assert record["status"] == "verified_equivalent"
    assert record["scope"] == "fixed-width bound-parameter unitary, up to global phase"
    assert record["threshold"] == 1 - 1e-10
    assert record["evidence"]["reason"] == "identical_qiskit_circuit"
    assert record["accepted"] and record["is_verified"]


def test_free_parameter_is_unavailable_even_for_identical_syntax():
    theta = Parameter("theta")
    circuit = QuantumCircuit(1)
    circuit.rx(theta, 0)

    certificate = certify_equivalence(circuit, circuit.copy())

    assert certificate.method is EquivalenceMethod.UNAVAILABLE
    assert certificate.status is EquivalenceStatus.UNAVAILABLE
    assert certificate.evidence["reason"].startswith("free_parameters")
    assert certificate.evidence["free_parameters"] == ["theta"]
    assert not certificate.accepted


def test_bound_parameter_enters_numerical_unitary_contract():
    theta = Parameter("theta")
    parameterized = QuantumCircuit(1)
    parameterized.rx(theta, 0)
    bound = parameterized.assign_parameters({theta: 0.25})

    certificate = certify_equivalence(bound, bound.copy())

    assert certificate.method is EquivalenceMethod.EXACT_STRUCTURAL
    assert certificate.accepted


@pytest.mark.parametrize("instruction", ["measure", "reset"])
def test_nonunitary_operations_fail_closed(instruction):
    circuit = QuantumCircuit(1, 1)
    target = QuantumCircuit(1, 1)
    if instruction == "measure":
        circuit.measure(0, 0)
        target.measure(0, 0)
    else:
        circuit.reset(0)
        target.reset(0)

    certificate = certify_equivalence(circuit, target)

    assert certificate.method is EquivalenceMethod.UNAVAILABLE
    assert instruction in certificate.evidence["blockers"]
    assert not certificate.accepted


def test_classically_conditioned_or_dynamic_program_fails_closed():
    circuit = QuantumCircuit(1, 1)
    with circuit.if_test((circuit.clbits[0], True)):
        circuit.x(0)

    certificate = certify_equivalence(circuit, circuit.copy())

    assert certificate.status is EquivalenceStatus.UNAVAILABLE
    assert "classical_bits" in certificate.evidence["blockers"]
    assert "if_else" in certificate.evidence["blockers"]


def test_global_phase_is_accepted_by_numerical_unitary_contract():
    circuit = QuantumCircuit(1)
    circuit.x(0)
    target = circuit.copy()
    target.global_phase = math.pi / 3

    certificate = certify_equivalence(circuit, target, threshold=1 - 1e-12)

    assert certificate.method is EquivalenceMethod.NUMERICAL_UNITARY
    assert certificate.status is EquivalenceStatus.VERIFIED_EQUIVALENT
    assert certificate.fidelity == pytest.approx(1.0)


def test_minimal_identity_vs_x_counterexample_is_rejected():
    identity = QuantumCircuit(1)
    x_circuit = QuantumCircuit(1)
    x_circuit.x(0)

    certificate = certify_equivalence(identity, x_circuit, threshold=0.99)

    assert certificate.method is EquivalenceMethod.NUMERICAL_UNITARY
    assert certificate.status is EquivalenceStatus.VERIFIED_NOT_EQUIVALENT
    assert certificate.fidelity == pytest.approx(1 / 3)
    assert not certificate.accepted


def test_large_nonclifford_certificate_is_explicitly_sampled():
    circuit = QuantumCircuit(2)
    circuit.t(0)
    target = QuantumCircuit(2)

    certificate = certify_equivalence(
        circuit,
        target,
        max_exact_qubits=1,
        n_samples=64,
        rng=__import__("numpy").random.RandomState(123),
    )

    assert certificate.method is EquivalenceMethod.SAMPLED_GLOBAL_HAAR
    assert certificate.status is EquivalenceStatus.ESTIMATED_NOT_EQUIVALENT
    assert certificate.samples == 64
    assert certificate.standard_error is not None
    assert not certificate.is_verified


def test_qasm2_unitary_round_trip_preserves_semantics():
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.rz(0.25, 1)
    restored = qasm2.loads(qasm2.dumps(circuit))

    certificate = certify_equivalence(circuit, restored, threshold=1 - 1e-10)

    assert certificate.accepted
    assert certificate.is_verified


def test_qasm2_measurement_round_trip_remains_out_of_scope():
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)
    circuit.measure(0, 0)
    restored = qasm2.loads(qasm2.dumps(circuit))

    certificate = certify_equivalence(circuit, restored)

    assert certificate.status is EquivalenceStatus.UNAVAILABLE
    assert "measure" in certificate.evidence["blockers"]


def test_heuristic_certificate_can_never_be_accepted():
    certificate = EquivalenceCertificate(
        method=EquivalenceMethod.HEURISTIC,
        status=EquivalenceStatus.INCONCLUSIVE,
        scope="gate multiset only",
        threshold=0.99,
        fidelity=1.0,
        evidence={"reason": "test-only structural similarity"},
    )

    assert certificate.passes_threshold
    assert not certificate.accepted
    assert not certificate.is_verified


def test_optimization_result_preserves_non_lossy_equivalence_certificate():
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.h(0)

    result = GreedyGateCancellation().optimize(circuit, target=circuit)
    payload = result.to_dict()

    assert result.fidelity == pytest.approx(1.0)
    assert result.equivalence_certificate is not None
    assert result.equivalence_certificate["method"] == "numerical_unitary"
    assert result.equivalence_certificate["is_verified"] is True
    assert payload["equivalence_certificate"] == result.equivalence_certificate
