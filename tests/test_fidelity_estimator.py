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
