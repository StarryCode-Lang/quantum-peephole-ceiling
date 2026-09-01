"""
Random Local Search Optimizer - Phase 1
=======================================
Stochastic local search with expanded move set.

Version: 3.0.0
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from typing import Optional, List
import copy
import time

from ..base import BaseOptimizer, OptimizationResult


class RandomLocalSearch(BaseOptimizer):
    """
    Random Local Search optimizer.

    Explores the neighborhood of the current circuit by applying
    random modifications and accepting improvements.

    Uses the expanded move set: REMOVAL, SWAP, COMMUTATION, INSERTION.

    Complexity
    ----------
    Per iteration: N = ``neighborhood_size`` (default 5) neighbors, each
    O(m) to generate (``_generate_neighbor``) and O(F + m) to score
    (``_fitness``), where m = gate count and F is the fidelity cost
    (for n <= 12 qubits, F = O(m * 4**n + 8**n); see the
    ``BaseOptimizer`` complexity model).  One iteration costs
    O(N * (m + F)).

    Overall: O(I * N * (m + F)) time with I = ``max_iterations``
    (default 100; early stopping after 50 non-improving iterations),
    O(N * m) memory for the neighbor batch plus O(4**n) per exact
    fidelity call.  Fidelity dominates: in E04 (n=5, m~75) RLS averaged
    6.15 s/trial (data/v2_fixed/e04;
    docs/analysis/algorithmic_complexity.md).
    """
    
    def __init__(self, max_iterations: int = 100, neighborhood_size: int = 5,
                 fidelity_threshold: float = 0.99, success_reduction: float = 0.05,
                 random_seed: Optional[int] = None):
        # success_reduction aligned with BaseOptimizer bug #5 fix (2026-08-06);
        # canonical v2_fixed..v8 runs used the legacy 0.20 default.
        super().__init__(fidelity_threshold, success_reduction, random_seed)
        self.max_iterations = max_iterations
        self.neighborhood_size = neighborhood_size
    
    def optimize(self, circuit: QuantumCircuit, target: Optional[QuantumCircuit] = None) -> OptimizationResult:
        """Optimize using random local search."""
        start_time = time.time()
        
        if target is None:
            target = circuit
        
        # ``current`` is the exploratory Markov state; ``incumbent`` is the
        # smallest fidelity-valid circuit seen.  Keeping them separate is
        # essential because the cancellation-potential bonus may deliberately
        # favor a temporarily larger circuit during exploration.
        current = copy.deepcopy(circuit)
        current_fitness = self._fitness(current, target)
        incumbent = copy.deepcopy(circuit)
        
        fitness_history = [current_fitness]
        no_improvement = 0
        iteration = 0
        
        for iteration in range(self.max_iterations):
            neighbors = self._generate_neighbors(current)
            
            best_neighbor = None
            best_neighbor_fitness = -np.inf
            
            for neighbor in neighbors:
                fitness = self._fitness(neighbor, target)
                if fitness > best_neighbor_fitness:
                    best_neighbor_fitness = fitness
                    best_neighbor = neighbor
            
            if best_neighbor_fitness > current_fitness:
                current = best_neighbor
                current_fitness = best_neighbor_fitness
                no_improvement = 0
            else:
                no_improvement += 1

            if current.size() < incumbent.size():
                candidate_fidelity = self.calculate_fidelity(current, target)
                if candidate_fidelity >= self.fidelity_threshold:
                    incumbent = copy.deepcopy(current)
            
            fitness_history.append(current_fitness)
            
            # Early stopping
            if no_improvement >= 50:
                break
        
        runtime = time.time() - start_time
        fidelity, equivalence_certificate = self.result_equivalence(incumbent, target)
        reduction = 1.0 - incumbent.size() / circuit.size() if circuit.size() > 0 else 0.0
        success = self._is_success(reduction, fidelity)
        
        return OptimizationResult(
            optimized_circuit=incumbent,
            original_size=circuit.size(),
            optimized_size=incumbent.size(),
            fidelity=fidelity,
            iterations=min(iteration + 1, self.max_iterations) if self.max_iterations > 0 else 0,
            runtime_seconds=runtime,
            success=success,
            equivalence_certificate=equivalence_certificate,
            metadata={'algorithm': 'rls', 'fitness_history': fitness_history}
        )
    
    def _generate_neighbors(self, circuit: QuantumCircuit) -> List[QuantumCircuit]:
        """
        Generate neighborhood of circuits using the expanded move set.
        
        Each neighbor is produced by applying one random valid move
        (REMOVAL, SWAP, COMMUTATION, or INSERTION) that preserves
        unitary equivalence.
        """
        neighbors = []
        for _ in range(self.neighborhood_size):
            neighbor = self._generate_neighbor(circuit)
            neighbors.append(neighbor)
        return neighbors
