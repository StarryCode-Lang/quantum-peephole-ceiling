"""Regression tests for the large-circuit fidelity estimator."""

from qiskit import QuantumCircuit

from src.optimisation.base import BaseOptimizer, OptimizationResult


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
