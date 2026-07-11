"""
Split test module from tests/test_core.py.
"""
import os
import sys
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from src.circuits.generator_v2 import (
    CircuitConfig, CircuitFamily, StructureType,
    generate_circuit, generate_circuit_batch,
    MetricsCalculator, create_generator
)
from src.optimisation.base import BaseOptimizer, OptimizationResult
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase1.random_local_search import RandomLocalSearch
from src.optimisation.phase1.simulated_annealing import SimulatedAnnealingOptimizer
from src.optimisation.phase1.genetic_algorithm import GeneticAlgorithmOptimizer
from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor
from src.optimisation.phase2.commutation_rewriter import Phase2aCommutationRewriter, HybridPhase2aRewrite
from src.circuits.real_benchmarks import (
    make_qft, make_ghz, make_cnot_chain, make_bernstein_vazirani,
    make_qaoa_line, make_vqe_twolocal, make_hardware_efficient,
    make_grover, make_quantum_adder, make_quantum_walk, make_iqp,
    make_random_clifford, make_surface_code_syndrome, make_parameterized_ansatz,
    make_haar_random, generate_extended_suite,
    circuit_sha256, gate_counts, average_gate_fidelity, BenchmarkCircuit,
)


# ============================================================================
# Helper: Concrete optimizer for testing BaseOptimizer methods
# ============================================================================

class _TestOptimizer(BaseOptimizer):
    """Concrete optimizer for testing abstract base class methods."""
    def optimize(self, circuit, target=None):
        return OptimizationResult(
            optimized_circuit=circuit.copy(),
            original_size=circuit.size(),
            optimized_size=circuit.size(),
            fidelity=1.0,
            iterations=0,
            runtime_seconds=0.0,
            success=True
        )


class TestCommutation(unittest.TestCase):
    """Tests for commutation rules."""
    
    def test_disjoint_qubits_commute(self):
        """Test that gates on disjoint qubits commute."""
        optimizer = _TestOptimizer()
        
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.h(1)
        
        self.assertTrue(optimizer._gates_commute(qc, qc.data[0], qc.data[1]))
    
    def test_same_single_qubit_gate_commutes(self):
        """Test that same single-qubit gate on same qubit commutes with itself."""
        optimizer = _TestOptimizer()
        
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.h(0)
        
        self.assertTrue(optimizer._gates_commute(qc, qc.data[0], qc.data[1]))
    
    def test_h_x_do_not_commute(self):
        """Test that H and X do not commute."""
        optimizer = _TestOptimizer()
        
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.x(0)
        
        self.assertFalse(optimizer._gates_commute(qc, qc.data[0], qc.data[1]))
    
    def test_cnot_commutes_with_z_on_control(self):
        """Test CNOT commutes with Z on control qubit."""
        optimizer = _TestOptimizer()
        
        qc = QuantumCircuit(2)
        qc.z(0)
        qc.cx(0, 1)
        
        self.assertTrue(optimizer._gates_commute(qc, qc.data[0], qc.data[1]))


# ============================================================================
# Phase 2 Optimizer Tests
# ============================================================================



class TestPhase2Optimizer(unittest.TestCase):
    """Tests for Phase 2 commutation-based optimizers."""
    
    def test_commutation_rewriter_runs(self):
        """Test that Phase2aCommutationRewriter runs without errors."""
        optimizer = Phase2aCommutationRewriter()
        circuit = generate_circuit(
            n_qubits=3, depth=5, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        
        result = optimizer.optimize(circuit)
        
        self.assertGreaterEqual(result.fidelity, 0.99)
        self.assertLessEqual(result.optimized_size, result.original_size)
    
    def test_hybrid_optimizer_runs(self):
        """Test that HybridPhase2aRewrite runs without errors."""
        optimizer = HybridPhase2aRewrite()
        circuit = generate_circuit(
            n_qubits=3, depth=5, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        
        result = optimizer.optimize(circuit)
        
        self.assertGreaterEqual(result.fidelity, 0.99)
        self.assertLessEqual(result.optimized_size, result.original_size)
        # Should have metadata about phase reductions
        self.assertIn('phase1_reduction', result.metadata)
        self.assertIn('phase2_reduction', result.metadata)
    
    def test_hybrid_on_cnot_chain(self):
        """Test hybrid optimizer on CNOT chain (should cancel all)."""
        optimizer = HybridPhase2aRewrite()
        qc = QuantumCircuit(2)
        for _ in range(6):
            qc.cx(0, 1)
        
        result = optimizer.optimize(qc)
        
        # All CNOTs should cancel (even number)
        self.assertEqual(result.optimized_size, 0)
        self.assertEqual(result.fidelity, 1.0)


# ============================================================================
# Commutation Rewriter Correctness Tests (v3.1.0 bug fix)
# ============================================================================

class _TestCommutationInspector(BaseOptimizer):
    """Concrete optimizer for inspecting _gates_commute and _is_self_inverse_pair."""
    def optimize(self, circuit, target=None):
        return OptimizationResult(
            optimized_circuit=circuit.copy(),
            original_size=circuit.size(),
            optimized_size=circuit.size(),
            fidelity=1.0, iterations=0,
            runtime_seconds=0.0, success=True,
        )


def _exact_unitary(qc):
    """Compute exact unitary matrix of a circuit."""
    return np.array(Operator(qc).data)


def _unitaries_equal(qc1, qc2, tol=1e-10):
    """Check if two circuits produce the same unitary."""
    u1 = _exact_unitary(qc1)
    u2 = _exact_unitary(qc2)
    if u1.shape != u2.shape:
        return False
    return np.allclose(u1, u2, atol=tol)




class TestPhase2aCommutationRewriterCorrectness(unittest.TestCase):
    """
    Exhaustive tests for the Phase2aCommutationRewriter correctness fix (v3.1.0).

    The v3.0.0 pre-check verified commutation with gate[i] only, but the
    bubble-sort moves gate[j] leftward, requiring commutation with gate[j].
    The fix checks commutation with BOTH gate[i] AND gate[j].

    These tests verify:
    1. Unitary preservation for all tested circuits
    2. Correct cancellation of valid non-adjacent pairs
    3. No false cancellations (unitary must not change)
    4. Edge cases: adjacent pairs, single intermediate, full window
    """

    # ------------------------------------------------------------------
    # 1. Counterexample circuit: pre-check divergence
    # ------------------------------------------------------------------
    def test_precheck_divergence_s_cnot_sdg(self):
        """
        Circuit: S(0), CNOT(0,1), Sdg(0)
        gate[i]=S, gate[j]=Sdg (self-inverse pair), intermediate=CNOT.
        Pre-check (old): commute(S, CNOT) = True
        Bubble-sort: commute(CNOT, Sdg) = True
        Both pass -> cancellation is valid.
        """
        insp = _TestCommutationInspector()
        qc = QuantumCircuit(2)
        qc.s(0); qc.cx(0, 1); qc.sdg(0)

        gi, gm, gj = qc.data[0], qc.data[1], qc.data[2]
        # Both conditions should agree for this gate set
        self.assertTrue(insp._gates_commute(qc, gi, gm))
        self.assertTrue(insp._gates_commute(qc, gm, gj))

        # Verify cancellation preserves unitary
        opt = Phase2aCommutationRewriter(window_size=10)
        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)
        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved after S-CNOT-Sdg cancellation")
        self.assertEqual(result.optimized_size, 1,
                         "S-Sdg pair should cancel, leaving only CNOT")

    def test_precheck_divergence_cnot_s_cnot(self):
        """
        Circuit: CNOT(0,1), S(0), CNOT(0,1)
        gate[i]=CNOT, gate[j]=CNOT (self-inverse pair), intermediate=S(0).
        S is in Z-family on control qubit -> commutes with CNOT.
        Both conditions pass -> valid cancellation.
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(2)
        qc.cx(0, 1); qc.s(0); qc.cx(0, 1)

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved")
        self.assertEqual(result.optimized_size, 1,
                         "CNOT pair should cancel, leaving S(0)")

    # ------------------------------------------------------------------
    # 2. Correct cancellation with multiple intermediates
    # ------------------------------------------------------------------
    def test_cnot_pair_with_z_family_intermediates(self):
        """
        Circuit: CNOT(0,1), S(0), Rz(pi/4, 0), CNOT(0,1)
        Both intermediates are Z-family on qubit 0 (CNOT control).
        They commute with both CNOTs.  CNOT-CNOT should cancel.
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(2)
        qc.cx(0, 1); qc.s(0); qc.rz(np.pi / 4, 0); qc.cx(0, 1)

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved")
        self.assertEqual(result.optimized_size, 2,
                         "CNOT pair should cancel, leaving S(0) and Rz(pi/4, 0)")

    def test_s_sdg_pair_with_multiple_intermediates(self):
        """
        Circuit: S(0), CNOT(0,1), Rz(0.3, 0), T(0), Sdg(0)
        gate[i]=S, gate[j]=Sdg, intermediates are all Z-family on control.
        All commute with S and Sdg.  S-Sdg should cancel.
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(2)
        qc.s(0); qc.cx(0, 1); qc.rz(0.3, 0); qc.t(0); qc.sdg(0)

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved after S-Sdg cancellation")
        self.assertLess(result.optimized_size, qc.size(),
                        "S-Sdg pair should have been cancelled")

    # ------------------------------------------------------------------
    # 3. No false cancellation when commutation fails
    # ------------------------------------------------------------------
    def test_no_cancel_when_intermediate_does_not_commute(self):
        """
        Circuit: H(0), X(0), H(0)
        gate[i]=H, gate[j]=H, intermediate=X.
        H and X do NOT commute (not in same family).
        The pre-check (both conditions) should FAIL.
        No cancellation should occur.
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(1)
        qc.h(0); qc.x(0); qc.h(0)

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved (no cancellation)")
        # H and X don't commute, so H-H should NOT be cancelled by commutation
        self.assertEqual(result.optimized_size, 3,
                         "H-X-H should not be cancelled (H and X don't commute)")

    def test_no_cancel_cnot_with_noncommuting_intermediate(self):
        """
        Circuit: CNOT(0,1), X(0), CNOT(0,1)
        X on control qubit does NOT commute with CNOT (not Z-family).
        No cancellation should occur.
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(2)
        qc.cx(0, 1); qc.x(0); qc.cx(0, 1)

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved")

    def test_no_cancel_mixed_commutation(self):
        """
        Circuit: CNOT(0,1), Z(0), H(0), CNOT(0,1)
        Z(0) commutes with CNOT (Z-family on control), but H(0) does NOT.
        Pre-check should fail at H(0). No cancellation.
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(2)
        qc.cx(0, 1); qc.z(0); qc.h(0); qc.cx(0, 1)

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved when pre-check correctly rejects")

    # ------------------------------------------------------------------
    # 4. Edge cases
    # ------------------------------------------------------------------
    def test_single_intermediate_gate(self):
        """
        Minimum non-adjacent case: exactly one gate between the pair.
        Circuit: S(0), Z(0), Sdg(0)
        Z commutes with S and Sdg (all Z-family). Valid cancellation.
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(1)
        qc.s(0); qc.z(0); qc.sdg(0)

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved with single intermediate")
        self.assertEqual(result.optimized_size, 1,
                         "S-Sdg should cancel, leaving Z(0)")

    def test_full_window_cancellation(self):
        """
        Test with a large window of commuting intermediates.
        Circuit: CNOT(0,1), S(0), T(0), Z(0), Rz(0.1, 0), Sdg(0), CNOT(0,1)
        All intermediates are Z-family on qubit 0 (CNOT control).
        Window size must be large enough to span i to j.
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(2)
        qc.cx(0, 1)    # data[0] = gate[i]
        qc.s(0)         # data[1]
        qc.t(0)         # data[2]
        qc.z(0)         # data[3]
        qc.rz(0.1, 0)   # data[4]
        qc.sdg(0)       # data[5]
        qc.cx(0, 1)     # data[6] = gate[j]

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved with full window")
        self.assertLess(result.optimized_size, qc.size(),
                        "At least one pair should cancel")

    def test_adjacent_pair_not_handled_by_phase2(self):
        """
        Adjacent self-inverse pairs (j = i+1) should NOT be handled
        by Phase2aCommutationRewriter (it starts at j = i+2).
        Those are handled by Phase 1 (GreedyGateCancellation).
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(1)
        qc.h(0); qc.h(0)

        result = opt.optimize(qc)
        # Phase2aCommutationRewriter should NOT cancel adjacent pairs
        self.assertEqual(result.optimized_size, 2,
                         "Phase2aCommutationRewriter should not cancel adjacent pairs")

    def test_adjacent_pair_handled_by_hybrid(self):
        """
        HybridPhase2aRewrite (Phase 1 + Phase 2) should cancel adjacent pairs
        via the Phase 1 greedy optimizer.
        """
        opt = HybridPhase2aRewrite()
        qc = QuantumCircuit(1)
        qc.h(0); qc.h(0)

        result = opt.optimize(qc)
        self.assertEqual(result.optimized_size, 0,
                         "Hybrid should cancel adjacent H-H pair via Phase 1")

    def test_disjoint_qubit_intermediate(self):
        """
        Circuit: CNOT(0,1), H(2), CNOT(0,1)
        H(2) is on a disjoint qubit from CNOT(0,1).
        Disjoint qubits always commute -> valid cancellation.
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(3)
        qc.cx(0, 1); qc.h(2); qc.cx(0, 1)

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved with disjoint intermediate")
        self.assertEqual(result.optimized_size, 1,
                         "CNOT pair should cancel, leaving H(2)")

    # ------------------------------------------------------------------
    # 5. Unitary preservation on random circuits
    # ------------------------------------------------------------------
    def test_unitary_preservation_random_small(self):
        """Test unitary preservation on random 2-qubit circuits."""
        opt = Phase2aCommutationRewriter(window_size=10)
        for seed in range(10):
            circuit = generate_circuit(
                n_qubits=2, depth=8, seed=seed,
                family=CircuitFamily.UNIVERSAL
            )
            U_before = _exact_unitary(circuit)
            result = opt.optimize(circuit)
            U_after = _exact_unitary(result.optimized_circuit)
            self.assertTrue(
                np.allclose(U_before, U_after),
                f"Unitary NOT preserved for seed={seed}, "
                f"size {circuit.size()} -> {result.optimized_size}"
            )

    def test_unitary_preservation_random_medium(self):
        """Test unitary preservation on random 3-qubit circuits."""
        opt = Phase2aCommutationRewriter(window_size=10)
        for seed in range(10):
            circuit = generate_circuit(
                n_qubits=3, depth=10, seed=seed,
                family=CircuitFamily.UNIVERSAL
            )
            U_before = _exact_unitary(circuit)
            result = opt.optimize(circuit)
            U_after = _exact_unitary(result.optimized_circuit)
            self.assertTrue(
                np.allclose(U_before, U_after),
                f"Unitary NOT preserved for seed={seed}, "
                f"size {circuit.size()} -> {result.optimized_size}"
            )

    def test_unitary_preservation_random_clifford(self):
        """Test unitary preservation on random Clifford circuits."""
        opt = Phase2aCommutationRewriter(window_size=10)
        for seed in range(10):
            circuit = generate_circuit(
                n_qubits=3, depth=8, seed=seed,
                family=CircuitFamily.CLIFFORD
            )
            U_before = _exact_unitary(circuit)
            result = opt.optimize(circuit)
            U_after = _exact_unitary(result.optimized_circuit)
            self.assertTrue(
                np.allclose(U_before, U_after),
                f"Unitary NOT preserved for Clifford seed={seed}, "
                f"size {circuit.size()} -> {result.optimized_size}"
            )

    def test_unitary_preservation_hybrid_random(self):
        """Test unitary preservation of HybridPhase2aRewrite on random circuits."""
        opt = HybridPhase2aRewrite(window_size=10)
        for seed in range(5):
            circuit = generate_circuit(
                n_qubits=3, depth=10, seed=seed,
                family=CircuitFamily.UNIVERSAL
            )
            U_before = _exact_unitary(circuit)
            result = opt.optimize(circuit)
            U_after = _exact_unitary(result.optimized_circuit)
            self.assertTrue(
                np.allclose(U_before, U_after),
                f"Hybrid unitary NOT preserved for seed={seed}, "
                f"size {circuit.size()} -> {result.optimized_size}"
            )

    # ------------------------------------------------------------------
    # 6. Pre-check correctness verification
    # ------------------------------------------------------------------
    def test_precheck_checks_both_conditions(self):
        """
        Verify that the fixed pre-check tests commutation with BOTH
        gate[i] and gate[j].  If either fails, no cancellation occurs.

        Circuit: T(0), S(0), CNOT(0,1), Tdg(0)
        gate[i]=T, gate[j]=Tdg (self-inverse pair).
        Intermediate S(0): commutes with T and Tdg (all Z-family).
        Intermediate CNOT(0,1): commutes with T and Tdg (Z-family on control).
        Both conditions pass -> cancellation should occur.
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(2)
        qc.t(0); qc.s(0); qc.cx(0, 1); qc.tdg(0)

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved")
        self.assertLess(result.optimized_size, qc.size(),
                        "T-Tdg should cancel when both conditions pass")

    def test_precheck_rejects_when_only_one_condition_passes(self):
        """
        Circuit: H(0), X(0), H(0)
        gate[i]=H, gate[j]=H. Intermediate=X(0).
        _gates_commute(H, X) = False (pre-check with gate[i] fails).
        _gates_commute(X, H) = False (pre-check with gate[j] fails).
        Both conditions fail -> no cancellation.

        This verifies the fix correctly rejects when NEITHER condition passes.
        """
        insp = _TestCommutationInspector()
        qc = QuantumCircuit(1)
        qc.h(0); qc.x(0); qc.h(0)

        gi, gm, gj = qc.data[0], qc.data[1], qc.data[2]
        self.assertFalse(insp._gates_commute(qc, gi, gm),
                         "H should not commute with X")
        self.assertFalse(insp._gates_commute(qc, gm, gj),
                         "X should not commute with H")

        opt = Phase2aCommutationRewriter(window_size=10)
        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "No cancellation should occur when commutation fails")
        self.assertEqual(result.optimized_size, 3)

    # ------------------------------------------------------------------
    # 7. Multi-cancellation chains
    # ------------------------------------------------------------------
    def test_multiple_cancellations_in_sequence(self):
        """
        Circuit with multiple non-adjacent pairs that can cancel:
        CNOT(0,1), S(0), CNOT(0,1), T(0), Tdg(0)
        First: CNOT pair cancels (S commutes with CNOT).
        Note: T-Tdg is an adjacent pair, which Phase2aCommutationRewriter does NOT
        handle (it starts at j = i+2).  Use HybridPhase2aRewrite for both.
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(2)
        qc.cx(0, 1); qc.s(0); qc.cx(0, 1); qc.t(0); qc.tdg(0)

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved after multiple cancellations")
        # Phase2aCommutationRewriter cancels CNOT pair; T-Tdg is adjacent (Phase 1)
        self.assertEqual(result.optimized_size, 3,
                         "CNOT pair cancels, leaving S(0), T(0), Tdg(0)")

        # HybridPhase2aRewrite should also cancel the adjacent T-Tdg pair
        opt_hybrid = HybridPhase2aRewrite(window_size=10)
        result_hybrid = opt_hybrid.optimize(qc)
        U_hybrid = _exact_unitary(result_hybrid.optimized_circuit)
        self.assertTrue(np.allclose(U_before, U_hybrid),
                        "Hybrid unitary must be preserved")
        self.assertEqual(result_hybrid.optimized_size, 1,
                         "Hybrid should cancel both CNOT pair and T-Tdg, leaving S(0)")

    def test_double_cnot_chain(self):
        """
        Circuit: CNOT(0,1), Z(0), CNOT(0,1), S(0), CNOT(0,1)
        Multiple CNOT cancellation opportunities with Z-family intermediates.
        """
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = QuantumCircuit(2)
        qc.cx(0, 1); qc.z(0); qc.cx(0, 1); qc.s(0); qc.cx(0, 1)

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved in double CNOT chain")
        self.assertLess(result.optimized_size, qc.size(),
                        "At least one CNOT pair should cancel")

    # ------------------------------------------------------------------
    # 8. Real benchmark circuits
    # ------------------------------------------------------------------
    def test_unitary_preservation_on_qft(self):
        """Test unitary preservation on QFT circuit."""
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = make_qft(3)
        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)
        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved on QFT circuit")

    def test_unitary_preservation_on_ghz(self):
        """Test unitary preservation on GHZ circuit."""
        opt = Phase2aCommutationRewriter(window_size=10)
        qc = make_ghz(3)
        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)
        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved on GHZ circuit")


# ============================================================================
# Integration Tests
# ============================================================================



if __name__ == '__main__':
    unittest.main(verbosity=2)
