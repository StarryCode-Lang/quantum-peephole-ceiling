"""
Phase 2 Optimizers: Commutation-Based Optimization
==================================================
Implements commutation rewriting and hybrid optimizers that enable
non-local gate cancellations beyond the Phase 1 adjacent-search ceiling.

Version: 3.1.0 (Fixed commutation pre-check correctness bug)
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction
from typing import Optional, List, Tuple, Dict, Any
import copy
import time

from ..base import BaseOptimizer, OptimizationResult


class CommutationRewriter(BaseOptimizer):
    """
    Commutation-based circuit rewriter.
    
    Applies commutation rules to bring non-adjacent inverse gates together,
    enabling cancellations that Phase 1 optimizers cannot find.
    
    Key insight: If gates A and B commute, and B and C commute, then
    A...B...C can be reordered to A...C...B, potentially bringing
    A and C (which may be inverses) adjacent.
    """
    
    def __init__(self, max_iterations: int = 100, fidelity_threshold: float = 0.99,
                 success_reduction: float = 0.20, window_size: int = 10):
        super().__init__(fidelity_threshold, success_reduction)
        self.max_iterations = max_iterations
        self.window_size = window_size
    
    def optimize(self, circuit: QuantumCircuit, target: Optional[QuantumCircuit] = None) -> OptimizationResult:
        """Optimize using commutation rewriting."""
        start_time = time.time()
        original = circuit
        optimized = copy.deepcopy(circuit)
        
        improvements = 0
        
        for iteration in range(self.max_iterations):
            improved = False
            
            # Try to find commutation chains that enable cancellation
            for i in range(len(optimized.data)):
                for j in range(i + 2, min(i + self.window_size, len(optimized.data))):
                    # Check if gates at i and j are inverses
                    if self._is_self_inverse_pair(optimized, optimized.data[i], optimized.data[j]):
                        # Check if all gates between i and j commute with
                        # BOTH gate[i] (stationary) AND gate[j] (moving).
                        #
                        # The bubble-sort below moves gate[j] leftward past
                        # each intermediate, which requires commutation with
                        # gate[j].  For mathematical correctness independent
                        # of gate type, we verify commutation with both
                        # endpoints.  The pre-check with gate[i] alone is
                        # neither necessary nor sufficient when gate[i] and
                        # gate[j] belong to different commutation families.
                        can_commute = True
                        for k in range(i + 1, j):
                            if not self._gates_commute(optimized, optimized.data[i], optimized.data[k]):
                                can_commute = False
                                break
                            if not self._gates_commute(optimized, optimized.data[k], optimized.data[j]):
                                can_commute = False
                                break
                        
                        if can_commute:
                            # Move gate at j to position i+1 by swapping with commuting gates
                            for k in range(j, i + 1, -1):
                                if self._gates_commute(optimized, optimized.data[k - 1], optimized.data[k]):
                                    optimized.data[k - 1], optimized.data[k] = optimized.data[k], optimized.data[k - 1]
                                else:
                                    can_commute = False
                                    break
                            
                            if can_commute:
                                # Now gates at i and i+1 should be inverses
                                if self._is_self_inverse_pair(optimized, optimized.data[i], optimized.data[i + 1]):
                                    # Safety check: ensure list is long enough
                                    if i + 1 < len(optimized.data):
                                        optimized.data.pop(i)
                                        optimized.data.pop(i)
                                        improved = True
                                        improvements += 1
                                        break
                
                if improved:
                    break
            
            if not improved:
                break
        
        runtime = time.time() - start_time
        
        # Calculate fidelity
        fidelity = 1.0 if target is None else self.calculate_fidelity(optimized, target)
        reduction = 1.0 - optimized.size() / original.size() if original.size() > 0 else 0.0
        success = self._is_success(reduction, fidelity)
        
        return OptimizationResult(
            optimized_circuit=optimized,
            original_size=original.size(),
            optimized_size=optimized.size(),
            fidelity=fidelity,
            iterations=improvements,
            runtime_seconds=runtime,
            success=success,
            metadata={'algorithm': 'commutation_rewriter', 'improvements': improvements, 'window_size': self.window_size}
        )


class HybridCommuteRewrite(BaseOptimizer):
    """
    Hybrid optimizer: Phase 1 (Greedy) + Phase 2 (Commutation Rewriting).
    
    First applies greedy adjacent cancellation, then uses commutation
    rewriting to find non-local optimization opportunities.
    
    This demonstrates the decisive value of Phase 2 beyond the Phase 1 ceiling.
    """
    
    def __init__(self, max_iterations: int = 100, fidelity_threshold: float = 0.99,
                 success_reduction: float = 0.20, window_size: int = 10):
        super().__init__(fidelity_threshold, success_reduction)
        self.max_iterations = max_iterations
        self.window_size = window_size
        self.phase1 = None  # Will be initialized in optimize
        self.phase2 = CommutationRewriter(max_iterations=max_iterations,
                                          fidelity_threshold=fidelity_threshold,
                                          success_reduction=success_reduction,
                                          window_size=window_size)
    
    def optimize(self, circuit: QuantumCircuit, target: Optional[QuantumCircuit] = None) -> OptimizationResult:
        """Optimize using hybrid Phase 1 + Phase 2 approach."""
        start_time = time.time()
        original = circuit
        
        # Phase 1: Greedy adjacent cancellation
        from ..phase1.greedy import GreedyGateCancellation
        self.phase1 = GreedyGateCancellation(max_iterations=self.max_iterations,
                                             fidelity_threshold=self.fidelity_threshold,
                                             success_reduction=self.success_reduction)
        
        result1 = self.phase1.optimize(circuit, target)
        intermediate = result1.optimized_circuit
        
        # Phase 2: Commutation rewriting
        result2 = self.phase2.optimize(intermediate, target)
        optimized = result2.optimized_circuit
        
        # Phase 1 again: Clean up any new adjacent pairs created by Phase 2
        result3 = self.phase1.optimize(optimized, target)
        optimized = result3.optimized_circuit
        
        runtime = time.time() - start_time
        
        # Calculate fidelity
        fidelity = 1.0 if target is None else self.calculate_fidelity(optimized, target)
        reduction = 1.0 - optimized.size() / original.size() if original.size() > 0 else 0.0
        success = self._is_success(reduction, fidelity)
        
        total_improvements = (result1.metadata.get('improvements', 0) + 
                              result2.metadata.get('improvements', 0) +
                              result3.metadata.get('improvements', 0))
        
        return OptimizationResult(
            optimized_circuit=optimized,
            original_size=original.size(),
            optimized_size=optimized.size(),
            fidelity=fidelity,
            iterations=total_improvements,
            runtime_seconds=runtime,
            success=success,
            metadata={
                'algorithm': 'hybrid_commute_rewrite',
                'phase1_reduction': result1.reduction,
                'phase2_reduction': result2.reduction,
                'phase3_reduction': result3.reduction,
                'total_reduction': reduction,
                'improvements': total_improvements,
                'window_size': self.window_size,
            }
        )
