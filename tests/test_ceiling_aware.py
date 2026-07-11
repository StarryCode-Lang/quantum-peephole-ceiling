"""
Ceiling-Aware Optimizer Tests (E21)
====================================
Focused test module for the ceiling-aware optimizer and its action-space proxies.
"""

import os
import sys
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from src.circuits.generator_v2 import CircuitFamily, generate_circuit
from src.circuits.real_benchmarks import (
    make_bernstein_vazirani,
    make_cnot_chain,
    make_ghz,
    make_qft,
    make_random_clifford,
)
from src.optimisation.ceiling_aware import (
    CeilingAwareOptimizer,
    count_phase1_actions,
    count_phase2_actions,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase2.commutation_rewriter import HybridPhase2aRewrite


class TestCeilingAware(unittest.TestCase):
    """Tests for the CeilingAwareOptimizer and action-space proxies.

    E21 validates three properties:
    1. The ceiling-aware optimizer produces the SAME gate reduction as
       the naive always-run pipeline (HybridPhase2aRewrite).
    2. The ceiling-aware optimizer is FASTER on ceiling families
       (QFT, GHZ, etc.) where at least one phase has an empty action space.
    3. The action-space proxy (count_phase1_actions) correctly identifies
       empty action spaces (returns 0 when no adjacent cancellable pairs exist).
    """

    # ------------------------------------------------------------------
    # 1. Reduction parity: ceiling-aware == naive
    # ------------------------------------------------------------------

    def test_reduction_parity_on_cnot_chain(self):
        """Ceiling-aware and naive should produce identical reduction on CNOT chains."""
        qc = make_cnot_chain(4, repeats=4)
        naive = HybridPhase2aRewrite()
        aware = CeilingAwareOptimizer()

        naive_result = naive.optimize(qc, target=qc)
        aware_result = aware.optimize(qc, target=qc)

        self.assertEqual(
            naive_result.optimized_size, aware_result.optimized_size,
            f"CNOT chain: naive={naive_result.optimized_size}, "
            f"aware={aware_result.optimized_size}"
        )

    def test_reduction_parity_on_random_circuit(self):
        """Ceiling-aware should not produce worse reduction than naive on random circuits."""
        circuit = generate_circuit(
            n_qubits=3, depth=10, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        naive = HybridPhase2aRewrite()
        aware = CeilingAwareOptimizer()

        naive_result = naive.optimize(circuit, target=circuit)
        aware_result = aware.optimize(circuit, target=circuit)

        # Ceiling-aware should achieve at least as much reduction as naive
        # (they run the same phases, just conditionally)
        self.assertGreaterEqual(
            aware_result.reduction, naive_result.reduction - 1e-10,
            f"Ceiling-aware reduction ({aware_result.reduction:.4f}) "
            f"< naive reduction ({naive_result.reduction:.4f})"
        )

    def test_reduction_parity_across_benchmarks(self):
        """Ceiling-aware matches naive reduction on multiple benchmark families."""
        circuits = [
            ("QFT", make_qft(4)),
            ("GHZ", make_ghz(4)),
            ("CNOT", make_cnot_chain(3, repeats=3)),
            ("BV", make_bernstein_vazirani(3, seed=42)),
        ]
        naive = HybridPhase2aRewrite()
        aware = CeilingAwareOptimizer()

        for name, qc in circuits:
            with self.subTest(family=name):
                naive_r = naive.optimize(qc, target=qc)
                aware_r = aware.optimize(qc, target=qc)
                self.assertEqual(
                    naive_r.optimized_size, aware_r.optimized_size,
                    f"{name}: naive={naive_r.optimized_size}, "
                    f"aware={aware_r.optimized_size}"
                )

    def test_unitary_preserved_ceiling_aware(self):
        """Ceiling-aware optimizer must preserve the circuit unitary."""
        qc = generate_circuit(
            n_qubits=3, depth=8, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        aware = CeilingAwareOptimizer()
        U_before = np.array(Operator(qc).data)
        result = aware.optimize(qc, target=qc)
        U_after = np.array(Operator(result.optimized_circuit).data)

        self.assertTrue(
            np.allclose(U_before, U_after),
            "Ceiling-aware optimizer did not preserve unitary"
        )

    # ------------------------------------------------------------------
    # 2. Speed advantage on ceiling families
    # ------------------------------------------------------------------

    def test_faster_on_ghz(self):
        """Ceiling-aware should skip Phase 1 on GHZ (no adjacent inverse pairs)."""
        qc = make_ghz(6)
        aware = CeilingAwareOptimizer()
        detailed = aware.optimize_detailed(qc, target=qc)

        # GHZ = H(0) + CX chain -> no adjacent inverse pairs
        # Phase 1 should be skipped
        self.assertTrue(
            detailed.phase1_skipped,
            "Phase 1 should be skipped for GHZ circuit (no adjacent inverse pairs)"
        )

    def test_faster_on_qft(self):
        """Ceiling-aware should skip Phase 1 on QFT (no adjacent inverse pairs)."""
        qc = make_qft(5)
        aware = CeilingAwareOptimizer()
        detailed = aware.optimize_detailed(qc, target=qc)

        # QFT = H + controlled phase gates -> no adjacent inverse pairs
        self.assertTrue(
            detailed.phase1_skipped,
            "Phase 1 should be skipped for QFT circuit"
        )

    def test_phase1_not_skipped_on_cnot_chain(self):
        """Ceiling-aware should NOT skip Phase 1 on CNOT chains (many inverse pairs)."""
        qc = make_cnot_chain(4, repeats=3)
        aware = CeilingAwareOptimizer()
        detailed = aware.optimize_detailed(qc, target=qc)

        self.assertFalse(
            detailed.phase1_skipped,
            "Phase 1 should NOT be skipped for CNOT chain"
        )
        self.assertGreater(
            detailed.ceiling_proxy_phase1, 0,
            "Ceiling proxy should detect cancellable pairs in CNOT chain"
        )

    def test_timing_overhead_is_small(self):
        """The ceiling proxy computation should add negligible overhead."""
        qc = make_random_clifford(8, depth=20, seed=42)

        # Time the proxy computation
        t0 = time.perf_counter()
        for _ in range(100):
            count_phase1_actions(qc)
        proxy_time_ms = (time.perf_counter() - t0) * 1000.0 / 100.0

        # Time a single Phase 1 run
        greedy = GreedyGateCancellation()
        t0 = time.perf_counter()
        greedy.optimize(qc)
        phase1_time_ms = (time.perf_counter() - t0) * 1000.0

        # Proxy should be much faster than Phase 1
        self.assertLess(
            proxy_time_ms, phase1_time_ms,
            f"Proxy ({proxy_time_ms:.3f} ms) should be faster than "
            f"Phase 1 ({phase1_time_ms:.3f} ms)"
        )

    # ------------------------------------------------------------------
    # 3. Action-space proxy correctness
    # ------------------------------------------------------------------

    def test_proxy_empty_for_identity_circuit(self):
        """count_phase1_actions should return 0 for an empty circuit."""
        qc = QuantumCircuit(2)
        self.assertEqual(count_phase1_actions(qc), 0)

    def test_proxy_detects_hh_pair(self):
        """count_phase1_actions should detect an adjacent H-H pair."""
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.h(0)
        self.assertGreaterEqual(count_phase1_actions(qc), 1)

    def test_proxy_zero_for_no_cancellable_pairs(self):
        """count_phase1_actions should return 0 when no adjacent pairs cancel."""
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)  # H and CNOT on different qubits, not inverse
        qc.h(1)
        # H(0), CX(0,1), H(1) — no adjacent self-inverse pairs
        # H and CX don't form a self-inverse pair (different gate types)
        # CX and H(1) don't form a self-inverse pair (different qubits)
        self.assertEqual(count_phase1_actions(qc), 0)

    def test_proxy_detects_mergeable_rotations(self):
        """count_phase1_actions should detect mergeable adjacent rotations."""
        qc = QuantumCircuit(1)
        qc.rz(0.5, 0)
        qc.rz(0.3, 0)  # Same axis, same qubit -> mergeable
        self.assertGreaterEqual(count_phase1_actions(qc), 1)

    def test_proxy_counts_multiple_pairs(self):
        """count_phase1_actions should count all adjacent cancellable pairs."""
        qc = QuantumCircuit(1)
        qc.h(0); qc.h(0)    # pair 1
        qc.x(0); qc.x(0)    # pair 2
        qc.z(0); qc.z(0)    # pair 3
        self.assertEqual(count_phase1_actions(qc), 3)

    def test_phase2_proxy_detects_commutation_opportunities(self):
        """count_phase2_actions should detect non-adjacent inverse pairs with commuting intermediates."""
        # CNOT(0,1), S(0), CNOT(0,1) -> S commutes with CNOT on control
        qc = QuantumCircuit(2)
        qc.cx(0, 1)
        qc.s(0)
        qc.cx(0, 1)
        self.assertGreaterEqual(count_phase2_actions(qc), 1)

    def test_phase2_proxy_zero_when_no_opportunities(self):
        """count_phase2_actions should return 0 when no commutation-enabled pairs exist."""
        # H(0), X(0), H(0) -> X does NOT commute with H, so no opportunity
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.x(0)
        qc.h(0)
        self.assertEqual(count_phase2_actions(qc), 0)

    def test_detailed_result_populates_all_fields(self):
        """optimize_detailed should populate all timing and skip fields."""
        qc = make_cnot_chain(3, repeats=2)
        aware = CeilingAwareOptimizer()
        detailed = aware.optimize_detailed(qc, target=qc)

        self.assertIsNotNone(detailed.optimization_result)
        self.assertIsInstance(detailed.phase1_skipped, bool)
        self.assertIsInstance(detailed.phase2_skipped, bool)
        self.assertGreaterEqual(detailed.phase1_time_ms, 0.0)
        self.assertGreaterEqual(detailed.phase2_time_ms, 0.0)
        self.assertGreaterEqual(detailed.total_time_ms, 0.0)
        self.assertGreaterEqual(detailed.ceiling_proxy_phase1, 0)
        self.assertGreaterEqual(detailed.ceiling_proxy_phase2, 0)

    def test_to_dict_has_expected_keys(self):
        """CeilingAwareResult.to_dict() should contain all expected keys."""
        qc = make_ghz(4)
        aware = CeilingAwareOptimizer()
        detailed = aware.optimize_detailed(qc, target=qc)
        d = detailed.to_dict()

        expected_keys = {
            'phase1_skipped', 'phase2_skipped',
            'phase1_time_ms', 'phase2_time_ms',
            'final_phase1_time_ms', 'total_time_ms',
            'ceiling_proxy_phase1', 'ceiling_proxy_phase2',
            'ceiling_proxy_final',
            'gate_reduction', 'original_size', 'optimized_size', 'fidelity',
        }
        self.assertTrue(
            expected_keys.issubset(d.keys()),
            f"Missing keys: {expected_keys - set(d.keys())}"
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
