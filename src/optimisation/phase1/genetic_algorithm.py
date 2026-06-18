"""
Genetic Algorithm Optimizer - Phase 1
=====================================
Evolutionary optimizer with tournament selection and patch-based crossover.

Version: 3.0.0
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from typing import Optional, List, Tuple
import copy
import time

from ..base import BaseOptimizer, OptimizationResult


class GeneticAlgorithmOptimizer(BaseOptimizer):
    """
    Genetic Algorithm optimizer.
    
    Uses evolutionary strategies: selection, crossover, mutation.
    All moves preserve unitary equivalence via the expanded move set.
    
    Crossover strategy: Uses the fitter parent as base and applies
    transformation patches derived from the other parent's gate operations.
    """
    
    def __init__(self, population_size: int = 10, generations: int = 10,
                 mutation_rate: float = 0.1, fidelity_threshold: float = 0.99,
                 success_reduction: float = 0.20, random_seed: Optional[int] = None):
        super().__init__(fidelity_threshold, success_reduction, random_seed)
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
    
    def optimize(self, circuit: QuantumCircuit, target: Optional[QuantumCircuit] = None) -> OptimizationResult:
        """Optimize using genetic algorithm."""
        start_time = time.time()
        
        if target is None:
            target = circuit
        
        # Initialize population with random valid moves applied to the original
        population = [copy.deepcopy(circuit)]
        for _ in range(self.population_size - 1):
            individual = copy.deepcopy(circuit)
            # Apply 1-3 random moves to create diversity
            num_moves = self.rng.randint(1, 4)
            for _ in range(num_moves):
                individual = self._generate_neighbor(individual)
            population.append(individual)
        
        best = copy.deepcopy(circuit)
        best_fitness = self._fitness(best, target)
        
        for generation in range(self.generations):
            # Evaluate fitness
            fitnesses = [self._fitness(ind, target) for ind in population]
            
            # Find best
            gen_best_idx = np.argmax(fitnesses)
            if fitnesses[gen_best_idx] > best_fitness:
                best = copy.deepcopy(population[gen_best_idx])
                best_fitness = fitnesses[gen_best_idx]
            
            # Selection (tournament)
            selected = self._tournament_select(population, fitnesses)
            
            # Crossover and mutation
            new_population = []
            for i in range(0, len(selected), 2):
                parent1 = selected[i]
                parent2 = selected[(i + 1) % len(selected)]
                
                child1, child2 = self._crossover(parent1, parent2, target)
                child1 = self._mutate(child1)
                child2 = self._mutate(child2)
                
                new_population.extend([child1, child2])
            
            population = new_population[:self.population_size]
        
        runtime = time.time() - start_time
        fidelity = self.calculate_fidelity(best, target)
        reduction = 1.0 - best.size() / circuit.size() if circuit.size() > 0 else 0.0
        success = self._is_success(reduction, fidelity)
        
        return OptimizationResult(
            optimized_circuit=best,
            original_size=circuit.size(),
            optimized_size=best.size(),
            fidelity=fidelity,
            iterations=self.generations,
            runtime_seconds=runtime,
            success=success,
            metadata={'algorithm': 'ga', 'population_size': self.population_size}
        )
    
    def _tournament_select(self, population: List[QuantumCircuit], fitnesses: List[float]) -> List[QuantumCircuit]:
        """Tournament selection."""
        if len(population) <= 1:
            return [copy.deepcopy(population[0])] if population else []
        selected = []
        for _ in range(len(population)):
            i, j = self.rng.choice(len(population), 2, replace=False)
            selected.append(copy.deepcopy(population[i] if fitnesses[i] > fitnesses[j] else population[j]))
        return selected
    
    def _crossover(self, parent1: QuantumCircuit, parent2: QuantumCircuit,
                   target: QuantumCircuit) -> Tuple[QuantumCircuit, QuantumCircuit]:
        """
        Gate-segment crossover that preserves unitary equivalence.
        
        Strategy:
        - Identify 'safe' cut points where both parents have gates on disjoint qubits
        - Exchange middle segments between parents at safe cut points
        - Verify unitary equivalence; if violated, fall back to parent copies
        
        This is a genuine recombination operator that combines structural
        features from both parents.
        """
        fitness1 = self._fitness(parent1, target)
        fitness2 = self._fitness(parent2, target)
        
        n1 = len(parent1.data)
        n2 = len(parent2.data)
        
        # Need at least 2 gates in each parent for meaningful crossover
        if n1 < 2 or n2 < 2:
            return copy.deepcopy(parent1), copy.deepcopy(parent2)
        
        # Find safe cut points in parent1: positions where consecutive gates
        # act on disjoint qubits (so swapping a segment won't break qubit coherence)
        def _find_safe_cuts(parent: QuantumCircuit) -> list:
            cuts = []
            for i in range(1, len(parent.data)):
                q1 = set(self._get_qubit_indices(parent, parent.data[i-1]))
                q2 = set(self._get_qubit_indices(parent, parent.data[i]))
                if len(q1 & q2) == 0:
                    cuts.append(i)
            return cuts
        
        safe_cuts_1 = _find_safe_cuts(parent1)
        safe_cuts_2 = _find_safe_cuts(parent2)
        
        # If we can find compatible cut points, perform segment exchange
        if safe_cuts_1 and safe_cuts_2:
            cut1 = self.rng.choice(safe_cuts_1)
            cut2 = self.rng.choice(safe_cuts_2)
            
            # Child 1: parent1[:cut1] + parent2[cut2:] (if qubit counts match)
            child1 = QuantumCircuit(parent1.num_qubits)
            child1.data = copy.deepcopy(parent1.data[:cut1]) + copy.deepcopy(parent2.data[cut2:])
            
            # Child 2: parent2[:cut2] + parent1[cut1:]
            child2 = QuantumCircuit(parent2.num_qubits)
            child2.data = copy.deepcopy(parent2.data[:cut2]) + copy.deepcopy(parent1.data[cut1:])
            
            # Always verify unitary equivalence.
            # For small circuits (n <= MAX_EXACT_FIDELITY_QUBITS), calculate_fidelity
            # uses exact Operator comparison.  For larger circuits it automatically
            # falls back to sampling-based fidelity estimation.
            try:
                f1 = self.calculate_fidelity(child1, target)
                if f1 < self.fidelity_threshold:
                    child1 = copy.deepcopy(parent1 if fitness1 >= fitness2 else parent2)
            except Exception:
                child1 = copy.deepcopy(parent1 if fitness1 >= fitness2 else parent2)
            
            try:
                f2 = self.calculate_fidelity(child2, target)
                if f2 < self.fidelity_threshold:
                    child2 = copy.deepcopy(parent2 if fitness2 >= fitness1 else parent1)
            except Exception:
                child2 = copy.deepcopy(parent2 if fitness2 >= fitness1 else parent1)
            
            return child1, child2
        
        # Fallback: no safe cut points found, return mutated copies of stronger parent
        stronger = copy.deepcopy(parent1 if fitness1 >= fitness2 else parent2)
        child1 = self._generate_neighbor(stronger)
        child2 = self._generate_neighbor(copy.deepcopy(stronger))
        return child1, child2
    
    def _mutate(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """
        Mutate a circuit using the expanded move set.
        
        With probability mutation_rate, apply a random valid move
        that preserves unitary equivalence.
        """
        if self.rng.random_sample() < self.mutation_rate:
            circuit = self._generate_neighbor(circuit)
        return circuit
