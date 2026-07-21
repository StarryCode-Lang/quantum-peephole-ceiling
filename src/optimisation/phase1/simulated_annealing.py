"""
Simulated Annealing Optimizer - Phase 1
=======================================
Temperature-based stochastic optimizer with Metropolis-Hastings acceptance.

Version: 3.0.0
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from qiskit import QuantumCircuit
import copy
import time

from ..base import BaseOptimizer, OptimizationResult


class SimulatedAnnealingOptimizer(BaseOptimizer):
    """
    Simulated Annealing optimizer.

    Uses temperature-based acceptance criterion to escape local minima.
    All moves preserve unitary equivalence via the expanded move set.

    Complexity
    ----------
    Per iteration: one ``_generate_neighbor`` call O(m) plus one
    ``_fitness`` evaluation O(F + m), where m = gate count and F is the
    fidelity cost (for n <= 12 qubits, F = O(m * 4**n + 8**n); see the
    ``BaseOptimizer`` complexity model).  Temperature update and the
    Metropolis-Hastings acceptance test are O(1).

    Overall: O(I * (m + F)) time with I = ``max_iterations``
    (default 100), O(m) memory for circuit copies plus O(4**n) per exact
    fidelity call.  Runtime is dominated by exact fidelity evaluation:
    in E04 (n=5, m~75) SA averaged 2.38 s/trial versus 2.3 ms for the
    fidelity-free greedy scan (data/v2_fixed/e04, see
    docs/analysis/algorithmic_complexity.md).
    """
    
    def __init__(self, max_iterations: int = 100, initial_temp: float = 1.0,
                 cooling_rate: float = 0.995, fidelity_threshold: float = 0.99,
                 success_reduction: float = 0.20, random_seed: Optional[int] = None):
        super().__init__(fidelity_threshold, success_reduction, random_seed)
        self.max_iterations = max_iterations
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
    
    def optimize(self, circuit: QuantumCircuit, target: Optional[QuantumCircuit] = None) -> OptimizationResult:
        """Optimize using simulated annealing."""
        start_time = time.time()
        
        if target is None:
            target = circuit
        
        current = copy.deepcopy(circuit)
        current_fitness = self._fitness(current, target)
        
        best = copy.deepcopy(current)
        best_fitness = current_fitness
        
        temp = self.initial_temp
        min_temp = 1e-8  # Prevent division by zero
        iteration = -1
        
        for iteration in range(self.max_iterations):
            # Generate neighbor using expanded move set
            neighbor = self._generate_neighbor(current)
            neighbor_fitness = self._fitness(neighbor, target)
            
            # Acceptance criterion (Metropolis-Hastings)
            delta = neighbor_fitness - current_fitness
            if delta > 0:
                # Always accept improvements
                current = neighbor
                current_fitness = neighbor_fitness
            elif temp > min_temp:
                # Accept worse solutions with probability exp(delta / temp)
                acceptance_prob = np.exp(delta / temp)
                if self.rng.random_sample() < acceptance_prob:
                    current = neighbor
                    current_fitness = neighbor_fitness
            
            # Update best
            if current_fitness > best_fitness:
                best = copy.deepcopy(current)
                best_fitness = current_fitness
            
            # Cool down
            temp *= self.cooling_rate
            temp = max(temp, min_temp)
        
        runtime = time.time() - start_time
        fidelity = self.calculate_fidelity(best, target)
        reduction = 1.0 - best.size() / circuit.size() if circuit.size() > 0 else 0.0
        success = self._is_success(reduction, fidelity)
        
        return OptimizationResult(
            optimized_circuit=best,
            original_size=circuit.size(),
            optimized_size=best.size(),
            fidelity=fidelity,
            iterations=iteration + 1,
            runtime_seconds=runtime,
            success=success,
            metadata={'algorithm': 'sa', 'final_temp': temp}
        )
