"""Regressions for stochastic Phase-1 exploration versus returned incumbent."""

from qiskit import QuantumCircuit
import pytest

from src.optimisation.phase1.genetic_algorithm import GeneticAlgorithmOptimizer
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase1.random_local_search import RandomLocalSearch
from src.optimisation.phase1.simulated_annealing import SimulatedAnnealingOptimizer


def hidden_cancellation_circuit() -> QuantumCircuit:
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.x(1)
    circuit.h(0)
    return circuit


def test_swap_then_removal_refutes_general_empty_initial_action_ceiling():
    circuit = hidden_cancellation_circuit()
    greedy = GreedyGateCancellation().optimize(circuit)
    assert greedy.optimized_size == 3

    optimizer = SimulatedAnnealingOptimizer(random_seed=0)
    swapped = optimizer._move_swap(circuit)
    assert swapped is not None
    reduced = optimizer._move_removal(swapped)
    assert reduced is not None
    assert reduced.size() == 1
    assert optimizer.calculate_fidelity(reduced, circuit) >= 0.9999999999

    result = SimulatedAnnealingOptimizer(
        max_iterations=200, initial_temp=1.0, cooling_rate=0.99,
        random_seed=0,
    ).optimize(circuit)
    assert result.optimized_size == 1
    assert result.reduction == pytest.approx(2 / 3)
    assert result.fidelity >= 0.9999999999


def test_exploration_bonus_never_returns_a_larger_circuit():
    circuit = hidden_cancellation_circuit()
    optimizers = [
        SimulatedAnnealingOptimizer(max_iterations=200, random_seed=1),
        SimulatedAnnealingOptimizer(max_iterations=200, random_seed=3),
        RandomLocalSearch(max_iterations=60, neighborhood_size=5, random_seed=1),
        GeneticAlgorithmOptimizer(
            population_size=6, generations=4, mutation_rate=0.5, random_seed=1
        ),
    ]
    for optimizer in optimizers:
        result = optimizer.optimize(circuit)
        assert result.optimized_size <= circuit.size()
        assert result.reduction >= 0.0
        assert result.fidelity >= 0.9999999999
