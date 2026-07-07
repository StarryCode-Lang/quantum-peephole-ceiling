"""
Ceiling-Aware Optimizer
=======================
A compiler pass that uses the structural ceiling proxy to skip
futile optimization phases, reducing compilation time without
sacrificing gate-count reduction.

The key insight: by computing the Phase-1 and Phase-2 action-space
sizes BEFORE running each optimizer phase (O(m) where m = gate count),
we can skip phases that would yield zero reduction, saving compilation
time.  This transforms a structural-ceiling *analysis* into a
structural-ceiling *decision rule* embedded in the compiler itself.

Pipeline:
    1. Compute Phase-1 action space |S1(C)|.
    2. If |S1(C)| > 0: run Phase 1 (Greedy).  Else: skip.
    3. Compute Phase-2 action space |S2(C')| on the intermediate circuit.
    4. If |S2(C')| > 0: run Phase 2 (CommutationRewriter).  Else: skip.
    5. If Phase 2 was run, do a final Phase-1 cleanup pass.

Version: 1.0.0
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import Any

from qiskit import QuantumCircuit

from .base import BaseOptimizer, OptimizationResult, _SELF_INVERSE_GATES
from .constants import DEFAULT_PRECISION
from . import _gate_predicates as _gp


# ---------------------------------------------------------------------------
# Fast action-space proxies (O(m) each)
# ---------------------------------------------------------------------------


def count_phase1_actions(circuit: QuantumCircuit) -> int:
    """Count adjacent self-inverse and mergeable-rotation pairs.

    This is the Phase-1 action-space size |S1(C)|: the number of
    adjacent gate pairs that GreedyGateCancellation could act on.

    Complexity: O(m) where m = len(circuit.data).

    Returns:
        Number of actionable adjacent pairs (>= 0).
    """
    n = len(circuit.data)
    if n < 2:
        return 0

    count = 0
    for i in range(n - 1):
        inst_a = circuit.data[i]
        inst_b = circuit.data[i + 1]
        if _gp.is_self_inverse_pair(circuit, inst_a, inst_b):
            count += 1
        elif _gp.is_mergeable_rotation(circuit, inst_a, inst_b):
            count += 1
    return count


def count_phase2_actions(circuit: QuantumCircuit, window: int = 10) -> int:
    """Count commutation-enabled inverse pairs within a sliding window.

    This is the Phase-2 action-space size |S2(C)|: the number of
    non-adjacent inverse pairs that CommutationRewriter could bring
    together by commuting intermediate gates.

    To keep this fast we restrict to pairs at distance 2..window and
    use a short-circuit scan that aborts the inner loop as soon as a
    non-commuting intermediate is found.

    Complexity: O(m * window) in the worst case, but typically O(m)
    because the inner loop short-circuits on the first non-commuting
    intermediate.  With window=10, this is effectively O(m).

    Returns:
        Number of actionable non-adjacent inverse pairs (>= 0).
    """
    n = len(circuit.data)
    if n < 3:
        return 0

    count = 0
    for i in range(n):
        upper = min(n, i + window)
        for j in range(i + 2, upper):
            if not _gp.is_self_inverse_pair(circuit, circuit.data[i], circuit.data[j]):
                continue
            # Check if all intermediates commute with BOTH endpoints
            can_commute = True
            for k in range(i + 1, j):
                if not _gp.gates_commute(circuit, circuit.data[i], circuit.data[k]):
                    can_commute = False
                    break
                if not _gp.gates_commute(circuit, circuit.data[k], circuit.data[j]):
                    can_commute = False
                    break
            if can_commute:
                count += 1
                break  # count at most one opportunity per anchor i
    return count


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class CeilingAwareResult:
    """Detailed result from the ceiling-aware optimizer, including
    per-phase timing and skip decisions.
    """
    optimization_result: OptimizationResult
    phase1_skipped: bool = False
    phase2_skipped: bool = False
    phase1_time_ms: float = 0.0
    phase2_time_ms: float = 0.0
    final_phase1_time_ms: float = 0.0
    total_time_ms: float = 0.0
    ceiling_proxy_phase1: int = 0
    ceiling_proxy_phase2: int = 0
    ceiling_proxy_final: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Flatten to a dict suitable for CSV output."""
        d = {
            'phase1_skipped': self.phase1_skipped,
            'phase2_skipped': self.phase2_skipped,
            'phase1_time_ms': self.phase1_time_ms,
            'phase2_time_ms': self.phase2_time_ms,
            'final_phase1_time_ms': self.final_phase1_time_ms,
            'total_time_ms': self.total_time_ms,
            'ceiling_proxy_phase1': self.ceiling_proxy_phase1,
            'ceiling_proxy_phase2': self.ceiling_proxy_phase2,
            'ceiling_proxy_final': self.ceiling_proxy_final,
            'gate_reduction': self.optimization_result.reduction,
            'original_size': self.optimization_result.original_size,
            'optimized_size': self.optimization_result.optimized_size,
            'fidelity': self.optimization_result.fidelity,
        }
        # Include extended metrics if available
        meta = self.optimization_result.metadata
        if 'depth_reduction' in meta:
            d['depth_reduction'] = meta['depth_reduction']
        if 'cnot_reduction' in meta:
            d['cnot_reduction'] = meta['cnot_reduction']
        return d


# ---------------------------------------------------------------------------
# Ceiling-Aware Optimizer
# ---------------------------------------------------------------------------


class CeilingAwareOptimizer(BaseOptimizer):
    """Ceiling-aware compilation pipeline that skips futile phases.

    Before each optimization phase, a fast O(m) structural proxy
    estimates the action-space size.  If the proxy is zero (no
    actionable gate pairs), the phase is skipped entirely, saving
    compilation time without losing any gate-count reduction.

    Pipeline:
        1. Compute |S1(C)| — Phase-1 action-space proxy.
        2. If |S1(C)| > 0 → run Phase 1 (GreedyGateCancellation).
           Else → skip Phase 1.
        3. Compute |S2(C')| — Phase-2 action-space proxy on the
           intermediate circuit.
        4. If |S2(C')| > 0 → run Phase 2 (CommutationRewriter).
           Else → skip Phase 2.
        5. If Phase 2 was run → final Phase 1 cleanup pass.

    The ceiling proxy adds O(m) overhead per check, which is
    negligible compared to the cost of a full optimization phase.
    """

    def __init__(self, max_iterations: int = 100,
                 fidelity_threshold: float = 0.99,
                 success_reduction: float = 0.20,
                 window_size: int = 10):
        super().__init__(fidelity_threshold, success_reduction)
        self.max_iterations = max_iterations
        self.window_size = window_size

    def optimize(self, circuit: QuantumCircuit,
                 target: QuantumCircuit | None = None) -> OptimizationResult:
        """Run the ceiling-aware pipeline and return an OptimizationResult.

        The result's ``metadata`` dict is populated with phase-skip
        decisions and per-phase timing for downstream analysis.
        """
        detailed = self.optimize_detailed(circuit, target)
        return detailed.optimization_result

    def optimize_detailed(self, circuit: QuantumCircuit,
                          target: QuantumCircuit | None = None) -> CeilingAwareResult:
        """Run the ceiling-aware pipeline and return a detailed CeilingAwareResult.

        Use this method when you need per-phase timing and skip
        information (e.g., for experiment E21).
        """
        from .phase1.greedy import GreedyGateCancellation
        from .phase2.commutation_rewriter import CommutationRewriter

        t_start = time.perf_counter()
        original = circuit

        phase1 = GreedyGateCancellation(
            max_iterations=self.max_iterations,
            fidelity_threshold=self.fidelity_threshold,
            success_reduction=self.success_reduction,
        )
        phase2 = CommutationRewriter(
            max_iterations=self.max_iterations,
            fidelity_threshold=self.fidelity_threshold,
            success_reduction=self.success_reduction,
            window_size=self.window_size,
        )

        # -- Phase 1 ---------------------------------------------------------
        proxy_p1 = count_phase1_actions(circuit)
        phase1_skipped = (proxy_p1 == 0)
        phase1_time_ms = 0.0

        if not phase1_skipped:
            t0 = time.perf_counter()
            result1 = phase1.optimize(circuit, target)
            phase1_time_ms = (time.perf_counter() - t0) * 1000.0
            intermediate = result1.optimized_circuit
        else:
            intermediate = copy.deepcopy(circuit)

        # -- Phase 2 ---------------------------------------------------------
        proxy_p2 = count_phase2_actions(intermediate, window=self.window_size)
        phase2_skipped = (proxy_p2 == 0)
        phase2_time_ms = 0.0

        if not phase2_skipped:
            t0 = time.perf_counter()
            result2 = phase2.optimize(intermediate, target)
            phase2_time_ms = (time.perf_counter() - t0) * 1000.0
            after_phase2 = result2.optimized_circuit
        else:
            after_phase2 = intermediate

        # -- Final Phase 1 (cleanup) ----------------------------------------
        final_phase1_time_ms = 0.0
        proxy_final = 0
        if not phase2_skipped:
            proxy_final = count_phase1_actions(after_phase2)
            if proxy_final > 0:
                t0 = time.perf_counter()
                result3 = phase1.optimize(after_phase2, target)
                final_phase1_time_ms = (time.perf_counter() - t0) * 1000.0
                optimized = result3.optimized_circuit
            else:
                optimized = after_phase2
        else:
            optimized = after_phase2

        total_time_ms = (time.perf_counter() - t_start) * 1000.0

        # -- Fidelity & reduction -------------------------------------------
        fidelity = 1.0 if target is None else self.calculate_fidelity(optimized, target)
        reduction = 1.0 - optimized.size() / original.size() if original.size() > 0 else 0.0
        success = self._is_success(reduction, fidelity)

        opt_result = OptimizationResult(
            optimized_circuit=optimized,
            original_size=original.size(),
            optimized_size=optimized.size(),
            fidelity=fidelity,
            iterations=0,
            runtime_seconds=total_time_ms / 1000.0,
            success=success,
            metadata={
                'algorithm': 'ceiling_aware',
                'phase1_skipped': phase1_skipped,
                'phase2_skipped': phase2_skipped,
                'phase1_time_ms': phase1_time_ms,
                'phase2_time_ms': phase2_time_ms,
                'final_phase1_time_ms': final_phase1_time_ms,
                'total_time_ms': total_time_ms,
                'ceiling_proxy_phase1': proxy_p1,
                'ceiling_proxy_phase2': proxy_p2,
                'ceiling_proxy_final': proxy_final,
            }
        )

        return CeilingAwareResult(
            optimization_result=opt_result,
            phase1_skipped=phase1_skipped,
            phase2_skipped=phase2_skipped,
            phase1_time_ms=phase1_time_ms,
            phase2_time_ms=phase2_time_ms,
            final_phase1_time_ms=final_phase1_time_ms,
            total_time_ms=total_time_ms,
            ceiling_proxy_phase1=proxy_p1,
            ceiling_proxy_phase2=proxy_p2,
            ceiling_proxy_final=proxy_final,
        )
