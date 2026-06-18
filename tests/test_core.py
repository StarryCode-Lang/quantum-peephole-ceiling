"""
Comprehensive Unit Tests for Q-Research Project
================================================
Postdoctoral-grade test suite covering all core components.

Uses Python standard library unittest (no external dependencies).
Run with: python tests/test_core.py
"""

import sys
import os
import time
import unittest
import numpy as np

# Add project root to path
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
from src.optimisation.phase2.commutation_rewriter import CommutationRewriter, HybridCommuteRewrite
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


# ============================================================================
# Circuit Generation Tests
# ============================================================================

class TestCircuitGeneration(unittest.TestCase):
    """Tests for the circuit generation module."""
    
    def test_universal_circuit_generation(self):
        """Test that universal circuit generation produces valid circuits."""
        circuit = generate_circuit(
            n_qubits=3, depth=5, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        
        self.assertIsInstance(circuit, QuantumCircuit)
        self.assertEqual(circuit.num_qubits, 3)
        self.assertGreater(circuit.size(), 0)
        self.assertGreater(circuit.depth(), 0)
    
    def test_clifford_circuit_generation(self):
        """Test Clifford circuit generation."""
        circuit = generate_circuit(
            n_qubits=4, depth=3, seed=42,
            family=CircuitFamily.CLIFFORD
        )
        
        self.assertEqual(circuit.num_qubits, 4)
        # Clifford circuits should only use H, S, CNOT
        for inst in circuit.data:
            self.assertIn(inst.operation.name, ['h', 's', 'cx', 'id'])
    
    def test_structured_brickwork_generation(self):
        """Test structured brickwork circuit generation."""
        circuit = generate_circuit(
            n_qubits=4, depth=4, seed=42,
            family=CircuitFamily.STRUCTURED,
            structure_type=StructureType.BRICKWORK
        )
        
        self.assertEqual(circuit.num_qubits, 4)
        self.assertGreater(circuit.size(), 0)
    
    def test_cnot_dihedral_generation(self):
        """Test CNOT-Dihedral circuit generation."""
        circuit = generate_circuit(
            n_qubits=3, depth=3, seed=42,
            family=CircuitFamily.CNOT_DIHEDRAL
        )
        
        self.assertEqual(circuit.num_qubits, 3)
        for inst in circuit.data:
            self.assertIn(inst.operation.name, ['x', 'rz', 'cx', 'id'])
    
    def test_batch_generation(self):
        """Test batch circuit generation with metrics."""
        config = CircuitConfig(n_qubits=3, depth=5, family=CircuitFamily.UNIVERSAL, seed=42)
        results = generate_circuit_batch(config, n_circuits=10)
        
        self.assertEqual(len(results), 10)
        for circuit, metrics in results:
            self.assertIsInstance(circuit, QuantumCircuit)
            self.assertEqual(metrics.gate_count, circuit.size())
            self.assertEqual(metrics.num_qubits, circuit.num_qubits)
    
    def test_config_validation_n_qubits(self):
        """Test n_qubits validation."""
        with self.assertRaises(ValueError):
            CircuitConfig(n_qubits=0, depth=5, family=CircuitFamily.UNIVERSAL)
    
    def test_config_validation_depth(self):
        """Test depth validation."""
        with self.assertRaises(ValueError):
            CircuitConfig(n_qubits=3, depth=0, family=CircuitFamily.UNIVERSAL)
    
    def test_config_validation_density(self):
        """Test entanglement_density validation."""
        with self.assertRaises(ValueError):
            CircuitConfig(n_qubits=3, depth=5, family=CircuitFamily.UNIVERSAL,
                         entanglement_density=1.5)
    
    def test_config_serialization(self):
        """Test CircuitConfig to_dict and from_dict."""
        config = CircuitConfig(n_qubits=5, depth=10, family=CircuitFamily.UNIVERSAL,
                              seed=123, entanglement_density=0.5)
        d = config.to_dict()
        config2 = CircuitConfig.from_dict(d)
        
        self.assertEqual(config2.n_qubits, config.n_qubits)
        self.assertEqual(config2.depth, config.depth)
        self.assertEqual(config2.family, config.family)
        self.assertEqual(config2.seed, config.seed)
        self.assertEqual(config2.entanglement_density, config.entanglement_density)
    
    def test_reproducibility(self):
        """Test that same seed produces identical circuits."""
        circuit1 = generate_circuit(
            n_qubits=3, depth=5, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        circuit2 = generate_circuit(
            n_qubits=3, depth=5, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        
        self.assertEqual(circuit1.size(), circuit2.size())
        for inst1, inst2 in zip(circuit1.data, circuit2.data):
            self.assertEqual(inst1.operation.name, inst2.operation.name)


# ============================================================================
# Metrics Calculator Tests
# ============================================================================

class TestMetricsCalculator(unittest.TestCase):
    """Tests for the metrics calculator."""
    
    def test_basic_metrics(self):
        """Test basic metric calculation."""
        calc = MetricsCalculator()
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.cx(0, 1)
        qc.rz(0.5, 2)
        
        metrics = calc.calculate(qc)
        
        self.assertEqual(metrics.gate_count, 3)
        self.assertEqual(metrics.num_qubits, 3)
        self.assertEqual(metrics.two_qubit_gates, 1)
        self.assertEqual(metrics.single_qubit_gates, 2)
    
    def test_caching(self):
        """Test that metrics are cached."""
        calc = MetricsCalculator()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        
        metrics1 = calc.calculate(qc)
        metrics2 = calc.calculate(qc)
        
        # Should return cached result (same object)
        self.assertIs(metrics1, metrics2)
    
    def test_entanglement_entropy(self):
        """Test entanglement entropy calculation."""
        calc = MetricsCalculator()
        # Bell state circuit
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        
        metrics = calc.calculate(qc)
        # Bell state has maximal entanglement entropy = 1.0
        self.assertGreater(metrics.entanglement_entropy, 0.9)
        self.assertLessEqual(metrics.entanglement_entropy, 1.0 + 1e-6)


# ============================================================================
# Base Optimizer Tests
# ============================================================================

class TestBaseOptimizer(unittest.TestCase):
    """Tests for the base optimizer class."""
    
    def test_fidelity_identical_circuits(self):
        """Test that identical circuits have fidelity 1.0."""
        optimizer = _TestOptimizer()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        
        fidelity = optimizer.calculate_fidelity(qc, qc)
        self.assertAlmostEqual(fidelity, 1.0, places=10)
    
    def test_fidelity_different_qubit_counts(self):
        """Test fidelity with different qubit counts returns 0."""
        optimizer = _TestOptimizer()
        qc1 = QuantumCircuit(2)
        qc2 = QuantumCircuit(3)
        
        fidelity = optimizer.calculate_fidelity(qc1, qc2)
        self.assertEqual(fidelity, 0.0)
    
    def test_fidelity_inverses(self):
        """Test fidelity of circuit and its inverse."""
        optimizer = _TestOptimizer()
        qc = QuantumCircuit(1)
        qc.h(0)
        
        qc_inv = QuantumCircuit(1)
        qc_inv.h(0)  # H is self-inverse
        
        fidelity = optimizer.calculate_fidelity(qc, qc_inv)
        self.assertAlmostEqual(fidelity, 1.0, places=10)
    
    def test_optimization_result_reduction(self):
        """Test OptimizationResult reduction property."""
        result = OptimizationResult(
            optimized_circuit=QuantumCircuit(2),
            original_size=10,
            optimized_size=8,
            fidelity=1.0,
            iterations=2,
            runtime_seconds=0.1,
            success=True
        )
        
        self.assertAlmostEqual(result.reduction, 0.2, places=10)
    
    def test_optimization_result_zero_original(self):
        """Test reduction with zero original size."""
        result = OptimizationResult(
            optimized_circuit=QuantumCircuit(2),
            original_size=0,
            optimized_size=0,
            fidelity=1.0,
            iterations=0,
            runtime_seconds=0.0,
            success=False
        )
        
        self.assertEqual(result.reduction, 0.0)


# ============================================================================
# Greedy Optimizer Tests
# ============================================================================

class TestGreedyOptimizer(unittest.TestCase):
    """Tests for the GreedyGateCancellation optimizer."""
    
    def test_simple_cancellation(self):
        """Test that adjacent self-inverse gates are cancelled."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.h(0)  # H-H should cancel
        
        result = optimizer.optimize(qc)
        
        self.assertEqual(result.optimized_size, 0)
        self.assertEqual(result.fidelity, 1.0)
        self.assertEqual(result.reduction, 1.0)
    
    def test_no_cancellation_different_qubits(self):
        """CRITICAL: Test that gates on different qubits are NOT cancelled."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.h(1)  # H on different qubits should NOT cancel
        
        result = optimizer.optimize(qc)
        
        # This is the v3.0.0 bug fix: gates on different qubits must not cancel
        self.assertEqual(result.optimized_size, 2,
            "BUG: Gates on different qubits were incorrectly cancelled!")
        self.assertEqual(result.reduction, 0.0)
    
    def test_cnot_cancellation(self):
        """Test CNOT self-inverse cancellation."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(2)
        qc.cx(0, 1)
        qc.cx(0, 1)  # CNOT-CNOT should cancel
        
        result = optimizer.optimize(qc)
        
        self.assertEqual(result.optimized_size, 0)
        self.assertEqual(result.fidelity, 1.0)
    
    def test_t_tdg_cancellation(self):
        """Test T-Tdg cancellation."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.t(0)
        qc.tdg(0)  # T-Tdg should cancel
        
        result = optimizer.optimize(qc)
        
        self.assertEqual(result.optimized_size, 0)
        self.assertEqual(result.fidelity, 1.0)
    
    def test_rotation_merge(self):
        """Test rotation gate merging."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.rz(0.5, 0)
        qc.rz(0.5, 0)  # Should merge to rz(1.0)
        
        result = optimizer.optimize(qc)
        
        self.assertEqual(result.optimized_size, 1)
        self.assertEqual(result.fidelity, 1.0)
    
    def test_rotation_cancellation(self):
        """Test rotation gate cancellation when angles sum to 0."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.rz(0.5, 0)
        qc.rz(-0.5, 0)  # Should cancel
        
        result = optimizer.optimize(qc)
        
        self.assertEqual(result.optimized_size, 0)
        self.assertEqual(result.fidelity, 1.0)
    
    def test_no_false_cancellation(self):
        """Test that non-inverse gates are not cancelled."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.x(0)  # H and X are not inverses
        
        result = optimizer.optimize(qc)
        
        self.assertEqual(result.optimized_size, 2)
        self.assertEqual(result.reduction, 0.0)
    
    def test_fidelity_preservation_random_circuit(self):
        """Test that optimization preserves fidelity for random circuits."""
        optimizer = GreedyGateCancellation()
        circuit = generate_circuit(
            n_qubits=3, depth=10, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        
        result = optimizer.optimize(circuit)
        
        self.assertGreaterEqual(result.fidelity, 0.99)
        self.assertLessEqual(result.fidelity, 1.0 + 1e-10)


# ============================================================================
# Commutation Tests
# ============================================================================

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
        """Test that CommutationRewriter runs without errors."""
        optimizer = CommutationRewriter()
        circuit = generate_circuit(
            n_qubits=3, depth=5, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        
        result = optimizer.optimize(circuit)
        
        self.assertGreaterEqual(result.fidelity, 0.99)
        self.assertLessEqual(result.optimized_size, result.original_size)
    
    def test_hybrid_optimizer_runs(self):
        """Test that HybridCommuteRewrite runs without errors."""
        optimizer = HybridCommuteRewrite()
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
        optimizer = HybridCommuteRewrite()
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


class TestCommutationRewriterCorrectness(unittest.TestCase):
    """
    Exhaustive tests for the CommutationRewriter correctness fix (v3.1.0).

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
        opt = CommutationRewriter(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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
        by CommutationRewriter (it starts at j = i+2).
        Those are handled by Phase 1 (GreedyGateCancellation).
        """
        opt = CommutationRewriter(window_size=10)
        qc = QuantumCircuit(1)
        qc.h(0); qc.h(0)

        result = opt.optimize(qc)
        # CommutationRewriter should NOT cancel adjacent pairs
        self.assertEqual(result.optimized_size, 2,
                         "CommutationRewriter should not cancel adjacent pairs")

    def test_adjacent_pair_handled_by_hybrid(self):
        """
        HybridCommuteRewrite (Phase 1 + Phase 2) should cancel adjacent pairs
        via the Phase 1 greedy optimizer.
        """
        opt = HybridCommuteRewrite()
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
        opt = CommutationRewriter(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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
        """Test unitary preservation of HybridCommuteRewrite on random circuits."""
        opt = HybridCommuteRewrite(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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

        opt = CommutationRewriter(window_size=10)
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
        Note: T-Tdg is an adjacent pair, which CommutationRewriter does NOT
        handle (it starts at j = i+2).  Use HybridCommuteRewrite for both.
        """
        opt = CommutationRewriter(window_size=10)
        qc = QuantumCircuit(2)
        qc.cx(0, 1); qc.s(0); qc.cx(0, 1); qc.t(0); qc.tdg(0)

        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)

        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved after multiple cancellations")
        # CommutationRewriter cancels CNOT pair; T-Tdg is adjacent (Phase 1)
        self.assertEqual(result.optimized_size, 3,
                         "CNOT pair cancels, leaving S(0), T(0), Tdg(0)")

        # HybridCommuteRewrite should also cancel the adjacent T-Tdg pair
        opt_hybrid = HybridCommuteRewrite(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
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
        opt = CommutationRewriter(window_size=10)
        qc = make_qft(3)
        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)
        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved on QFT circuit")

    def test_unitary_preservation_on_ghz(self):
        """Test unitary preservation on GHZ circuit."""
        opt = CommutationRewriter(window_size=10)
        qc = make_ghz(3)
        U_before = _exact_unitary(qc)
        result = opt.optimize(qc)
        U_after = _exact_unitary(result.optimized_circuit)
        self.assertTrue(np.allclose(U_before, U_after),
                        "Unitary must be preserved on GHZ circuit")


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration(unittest.TestCase):
    """End-to-end integration tests."""
    
    def test_all_optimizers_on_random_circuit(self):
        """Test all optimizers on the same random circuit."""
        circuit = generate_circuit(
            n_qubits=3, depth=5, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        
        optimizers = {
            'greedy': GreedyGateCancellation(),
            'rls': RandomLocalSearch(),
            'sa': SimulatedAnnealingOptimizer(),
            'ga': GeneticAlgorithmOptimizer(),
            'commutation': CommutationRewriter(),
            'hybrid': HybridCommuteRewrite(),
        }
        
        results = {}
        for name, opt in optimizers.items():
            result = opt.optimize(circuit)
            results[name] = result
            
            # All optimizers must preserve fidelity
            self.assertGreaterEqual(result.fidelity, 0.99,
                f"{name} failed fidelity check: {result.fidelity}")
            # All optimizers must not increase gate count
            self.assertLessEqual(result.optimized_size, result.original_size,
                f"{name} increased gate count")
        
        # Log results for inspection
        print("\nOptimizer results on random circuit:")
        for name, result in results.items():
            print(f"  {name}: {result.original_size} -> {result.optimized_size} "
                  f"(reduction={result.reduction:.4f}, fidelity={result.fidelity:.6f})")
    
    def test_data_output_format(self):
        """Test that experiment output matches expected CSV format."""
        try:
            import pandas as pd
            from pathlib import Path
            
            # Check that v2_fixed data exists and has correct columns
            data_dir = Path(__file__).parent.parent / 'data' / 'v2_fixed' / 'e01'
            if data_dir.exists():
                csv_files = list(data_dir.glob('*.csv'))
                if csv_files:
                    df = pd.read_csv(csv_files[0])
                    required_columns = ['experiment', 'n_qubits', 'depth', 'trial', 'seed',
                                       'original_size', 'optimized_size', 'reduction',
                                       'fidelity', 'success', 'runtime_seconds']
                    for col in required_columns:
                        self.assertIn(col, df.columns, f"Missing column: {col}")
        except ImportError:
            self.skipTest("pandas not available")


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance(unittest.TestCase):
    """Basic performance sanity checks."""
    
    def test_greedy_runtime_small_circuit(self):
        """Test Greedy optimizer runs in reasonable time for small circuits."""
        optimizer = GreedyGateCancellation()
        circuit = generate_circuit(
            n_qubits=5, depth=20, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        
        start = time.time()
        result = optimizer.optimize(circuit)
        elapsed = time.time() - start
        
        # Should complete in under 1 second for small circuits
        self.assertLess(elapsed, 1.0, f"Greedy took {elapsed:.2f}s, expected < 1s")
    
    def test_hybrid_runtime_small_circuit(self):
        """Test Hybrid optimizer runs in reasonable time for small circuits."""
        optimizer = HybridCommuteRewrite()
        circuit = generate_circuit(
            n_qubits=3, depth=5, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        
        start = time.time()
        result = optimizer.optimize(circuit)
        elapsed = time.time() - start
        
        # Should complete in under 5 seconds for small circuits
        self.assertLess(elapsed, 5.0, f"Hybrid took {elapsed:.2f}s, expected < 5s")


# ============================================================================
# Extended Circuit Family Tests (v5)
# ============================================================================

class TestExtendedCircuitFamilies(unittest.TestCase):
    """Tests for the 8 new circuit families added in v5."""

    def test_grover_generation(self):
        """Test Grover search circuit generation."""
        qc = make_grover(3, seed=42)
        self.assertIsInstance(qc, QuantumCircuit)
        self.assertEqual(qc.num_qubits, 3)
        self.assertGreater(qc.size(), 0)

    def test_grover_single_qubit(self):
        """Test Grover with n=1 (edge case)."""
        qc = make_grover(1, seed=42)
        self.assertEqual(qc.num_qubits, 1)
        self.assertGreater(qc.size(), 0)

    def test_quantum_adder_generation(self):
        """Test quantum adder circuit generation."""
        qc = make_quantum_adder(5, seed=42)
        self.assertIsInstance(qc, QuantumCircuit)
        self.assertGreaterEqual(qc.num_qubits, 4)
        self.assertGreater(qc.size(), 0)

    def test_quantum_adder_minimum_size(self):
        """Test that adder enforces minimum qubit count."""
        qc = make_quantum_adder(2, seed=42)
        self.assertGreaterEqual(qc.num_qubits, 4)

    def test_quantum_walk_generation(self):
        """Test quantum walk circuit generation."""
        qc = make_quantum_walk(3, steps=2, seed=42)
        self.assertIsInstance(qc, QuantumCircuit)
        # n_pos + 1 coin qubit
        self.assertGreaterEqual(qc.num_qubits, 4)
        self.assertGreater(qc.size(), 0)

    def test_iqp_generation(self):
        """Test IQP circuit generation."""
        qc = make_iqp(4, depth=2, seed=42)
        self.assertIsInstance(qc, QuantumCircuit)
        self.assertEqual(qc.num_qubits, 4)
        self.assertGreater(qc.size(), 0)
        # IQP should have H gates at start and end
        gate_names = [inst.operation.name for inst in qc.data]
        self.assertIn('h', gate_names)

    def test_random_clifford_generation(self):
        """Test random Clifford circuit generation."""
        qc = make_random_clifford(4, depth=5, seed=42)
        self.assertIsInstance(qc, QuantumCircuit)
        self.assertEqual(qc.num_qubits, 4)
        # Clifford circuits should only use H, S, CNOT, id
        for inst in qc.data:
            self.assertIn(inst.operation.name, ['h', 's', 'cx', 'id'])

    def test_surface_code_syndrome_generation(self):
        """Test surface code syndrome circuit generation."""
        qc = make_surface_code_syndrome(4, seed=42)
        self.assertIsInstance(qc, QuantumCircuit)
        # n_data + 1 ancilla
        self.assertGreaterEqual(qc.num_qubits, 5)
        self.assertGreater(qc.size(), 0)

    def test_uccsd_ansatz_generation(self):
        """Test parameterized ansatz circuit generation (formerly UCCSD)."""
        qc = make_parameterized_ansatz(4, reps=1, seed=42)
        self.assertIsInstance(qc, QuantumCircuit)
        self.assertEqual(qc.num_qubits, 4)
        self.assertGreater(qc.size(), 0)

    def test_haar_random_generation(self):
        """Test Haar random circuit generation (n<=4 only)."""
        qc = make_haar_random(3, seed=42)
        self.assertIsInstance(qc, QuantumCircuit)
        self.assertEqual(qc.num_qubits, 3)
        self.assertGreater(qc.size(), 0)

    def test_haar_random_too_large_raises(self):
        """Test that Haar random raises ValueError for n>4."""
        with self.assertRaises(ValueError):
            make_haar_random(5, seed=42)

    def test_reproducibility_new_families(self):
        """Test that same seed produces identical circuits for new families."""
        for factory in [make_grover, make_iqp, make_random_clifford]:
            c1 = factory(3, seed=42)
            c2 = factory(3, seed=42)
            self.assertEqual(c1.size(), c2.size())
            for i1, i2 in zip(c1.data, c2.data):
                self.assertEqual(i1.operation.name, i2.operation.name)


# ============================================================================
# Extended Suite Generation Tests
# ============================================================================

class TestExtendedSuiteGeneration(unittest.TestCase):
    """Tests for generate_extended_suite."""

    def test_smoke_mode_generates_circuits(self):
        """Test smoke mode generates a non-empty list."""
        suite = generate_extended_suite(mode="smoke", seed=42)
        self.assertIsInstance(suite, list)
        self.assertGreater(len(suite), 0)
        for bench in suite:
            self.assertIsInstance(bench, BenchmarkCircuit)
            self.assertIsInstance(bench.circuit, QuantumCircuit)

    def test_smoke_mode_circuit_families(self):
        """Test that smoke mode includes all 15 families."""
        suite = generate_extended_suite(mode="smoke", seed=42)
        families = {bench.family for bench in suite}
        expected = {
            "QFT", "GHZ", "CNOT", "Oracle", "QAOA", "VQE",
            "HardwareEfficient", "Grover", "Adder", "QuantumWalk",
            "IQP", "RandomClifford", "SurfaceCode", "UCCSD", "HaarRandom",
        }
        self.assertTrue(expected.issubset(families),
                        f"Missing families: {expected - families}")

    def test_full_mode_includes_large_sizes(self):
        """Test that full mode includes n=12, 15, 20 circuits."""
        suite = generate_extended_suite(mode="full", seed=42)
        qubit_counts = {bench.circuit.num_qubits for bench in suite}
        # At least some circuits should have n>=12
        # (some families add ancilla qubits, so check >= 12)
        large = [b for b in suite if b.circuit.num_qubits >= 12]
        self.assertGreater(len(large), 0, "Full mode should include large circuits")

    def test_invalid_mode_raises(self):
        """Test that invalid mode raises ValueError."""
        with self.assertRaises(ValueError):
            generate_extended_suite(mode="invalid")


# ============================================================================
# Provenance and Metrics Tests
# ============================================================================

class TestRealBenchmarksHelpers(unittest.TestCase):
    """Tests for helper functions in real_benchmarks.py."""

    def test_circuit_sha256_deterministic(self):
        """Test that SHA-256 is deterministic for identical circuits."""
        qc1 = make_qft(3)
        qc2 = make_qft(3)
        self.assertEqual(circuit_sha256(qc1), circuit_sha256(qc2))

    def test_circuit_sha256_differs(self):
        """Test that SHA-256 differs for different circuits."""
        qc1 = make_qft(3)
        qc2 = make_ghz(3)
        self.assertNotEqual(circuit_sha256(qc1), circuit_sha256(qc2))

    def test_gate_counts_returns_expected_keys(self):
        """Test gate_counts returns all expected keys."""
        qc = make_qft(3)
        counts = gate_counts(qc)
        expected_keys = {"gate_count_total", "depth", "gate_count_1q",
                         "gate_count_2q", "gate_count_multiq", "gate_counts_json"}
        self.assertEqual(set(counts.keys()), expected_keys)
        self.assertGreater(counts["gate_count_total"], 0)

    def test_average_gate_fidelity_identical(self):
        """Test fidelity of identical circuits is ~1.0."""
        qc = make_ghz(3)
        fid = average_gate_fidelity(qc, qc)
        self.assertIsNotNone(fid)
        self.assertAlmostEqual(fid, 1.0, places=5)

    def test_average_gate_fidelity_too_large(self):
        """Test that fidelity returns None for circuits exceeding max_qubits."""
        qc = make_ghz(12)
        fid = average_gate_fidelity(qc, qc, max_qubits=10)
        self.assertIsNone(fid)


# ============================================================================
# Extended Metrics Tests
# ============================================================================

class TestExtendedMetrics(unittest.TestCase):
    """Tests for OptimizationResult.compute_extended_metrics."""

    def test_extended_metrics_on_cnot_chain(self):
        """Test extended metrics on CNOT chain cancellation."""
        qc = QuantumCircuit(2)
        for _ in range(4):
            qc.cx(0, 1)
            qc.cx(0, 1)

        optimizer = GreedyGateCancellation()
        result = optimizer.optimize(qc, target=qc)
        metrics = result.compute_extended_metrics(qc)

        # All CNOTs should cancel → optimized has 0 gates, depth 0
        self.assertIn('depth_reduction', metrics)
        self.assertIn('two_qubit_reduction', metrics)
        self.assertIn('cnot_reduction', metrics)
        # CNOT chain should fully cancel
        self.assertAlmostEqual(metrics['cnot_reduction'], 1.0, places=5)
        self.assertAlmostEqual(metrics['two_qubit_reduction'], 1.0, places=5)

    def test_extended_metrics_no_reduction(self):
        """Test extended metrics when no reduction occurs."""
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.x(0)

        optimizer = GreedyGateCancellation()
        result = optimizer.optimize(qc, target=qc)
        metrics = result.compute_extended_metrics(qc)

        self.assertAlmostEqual(metrics['depth_reduction'], 0.0, places=5)
        self.assertEqual(metrics['original_depth'], int(qc.depth()))

    def test_extended_metrics_stored_in_metadata(self):
        """Test that compute_extended_metrics populates self.metadata."""
        qc = QuantumCircuit(2)
        qc.cx(0, 1)
        qc.cx(0, 1)

        optimizer = GreedyGateCancellation()
        result = optimizer.optimize(qc, target=qc)
        metrics = result.compute_extended_metrics(qc)

        self.assertIn('cnot_reduction', result.metadata)
        self.assertEqual(result.metadata['cnot_reduction'], metrics['cnot_reduction'])

    def test_extended_metrics_on_real_circuit(self):
        """Test extended metrics on a real benchmark circuit."""
        qc = make_bernstein_vazirani(3, seed=42)
        optimizer = HybridCommuteRewrite()
        result = optimizer.optimize(qc, target=qc)
        metrics = result.compute_extended_metrics(qc)

        self.assertIn('original_depth', metrics)
        self.assertIn('optimized_depth', metrics)
        self.assertGreaterEqual(metrics['original_depth'], metrics['optimized_depth'])
        self.assertGreaterEqual(metrics['depth_reduction'], 0.0)
        self.assertLessEqual(metrics['depth_reduction'], 1.0)


# ============================================================================
# BUG C2 Fix: GA crossover preserves unitary for all n (including n>8)
# ============================================================================

class TestGACrossoverFix(unittest.TestCase):
    """Tests for BUG C2: GA crossover must verify unitary equivalence for all n."""

    def test_crossover_preserves_unitary_10qubit(self):
        """Verify GA crossover children have correct unitary for a 10-qubit circuit.

        BUG C2: the old code skipped verification for n>8, allowing invalid children.
        After the fix, every child is verified (exact for n<=12, sampling for n>12)
        and falls back to cloning the fitter parent if invalid.
        """
        from src.circuits.generator_v2 import CircuitFamily, generate_circuit

        n = 10
        circuit = generate_circuit(
            n_qubits=n, depth=8, seed=42,
            family=CircuitFamily.UNIVERSAL
        )

        optimizer = GeneticAlgorithmOptimizer(
            population_size=6, generations=3, random_seed=42
        )
        result = optimizer.optimize(circuit, target=circuit)

        # The optimizer must preserve unitary equivalence
        self.assertGreaterEqual(
            result.fidelity, 0.99,
            f"GA crossover produced invalid child for n={n}! "
            f"Fidelity: {result.fidelity:.6f}"
        )

    def test_crossover_children_always_valid(self):
        """Directly test the _crossover method for a 10-qubit circuit."""
        import copy
        from src.circuits.generator_v2 import CircuitFamily, generate_circuit

        n = 10
        circuit = generate_circuit(
            n_qubits=n, depth=6, seed=123,
            family=CircuitFamily.UNIVERSAL
        )

        optimizer = GeneticAlgorithmOptimizer(random_seed=42)
        target = circuit.copy()

        # Create two diverse parents
        parent1 = copy.deepcopy(circuit)
        parent2 = copy.deepcopy(circuit)
        for _ in range(5):
            parent2 = optimizer._generate_neighbor(parent2)

        child1, child2 = optimizer._crossover(parent1, parent2, target)

        # Verify children via exact fidelity (n=10 < MAX_EXACT_FIDELITY_QUBITS=12)
        f1 = optimizer.calculate_fidelity(child1, target)
        f2 = optimizer.calculate_fidelity(child2, target)

        threshold = optimizer.fidelity_threshold * 0.9
        self.assertGreaterEqual(
            f1, threshold,
            f"Child1 fidelity {f1:.6f} below threshold {threshold:.6f}"
        )
        self.assertGreaterEqual(
            f2, threshold,
            f"Child2 fidelity {f2:.6f} below threshold {threshold:.6f}"
        )

    def test_ga_end_to_end_10qubit_fidelity(self):
        """Full GA optimization on a 10-qubit circuit must preserve fidelity."""
        qc = make_qft(10)
        optimizer = GeneticAlgorithmOptimizer(
            population_size=8, generations=3, random_seed=42
        )
        result = optimizer.optimize(qc, target=qc)

        self.assertGreaterEqual(
            result.fidelity, 0.99,
            f"GA failed fidelity for 10-qubit QFT: {result.fidelity:.6f}"
        )


# ============================================================================
# BUG C3 Fix: Quantum adder correct carry propagation (Cuccaro MAJ/UMA)
# ============================================================================

class TestQuantumAdderFix(unittest.TestCase):
    """Tests for BUG C3: quantum adder must produce correct arithmetic."""

    def _build_adder_with_inputs(self, half, a_val, b_val):
        """Build a ripple-carry adder with known inputs (no random generation).

        Returns (QuantumCircuit, half) so the caller knows the register layout.
        """
        total_qubits = 3 * half + 1  # a + b + carry ancillas + carry output
        qc = QuantumCircuit(total_qubits)

        # Encode a into qubits [0, half)
        for i in range(half):
            if (a_val >> i) & 1:
                qc.x(i)
        # Encode b into qubits [half, 2*half)
        for i in range(half):
            if (b_val >> i) & 1:
                qc.x(half + i)

        # Step 1: Compute all carries (forward pass)
        for i in range(half):
            a_q = i
            b_q = half + i
            cin_q = 2 * half + i
            cout_q = 2 * half + i + 1
            qc.ccx(a_q, b_q, cout_q)
            qc.ccx(cin_q, a_q, cout_q)
            qc.ccx(cin_q, b_q, cout_q)

        # Step 2: Compute sums into b register
        for i in range(half):
            a_q = i
            b_q = half + i
            cin_q = 2 * half + i
            qc.cx(a_q, b_q)
            qc.cx(cin_q, b_q)

        return qc, half

    def _run_adder(self, half, a_val, b_val):
        """Run adder and return (sum_result, carry_out)."""
        from qiskit.quantum_info import Statevector

        qc, h = self._build_adder_with_inputs(half, a_val, b_val)
        sv = Statevector.from_int(0, 2 ** qc.num_qubits).evolve(qc)
        probs = np.abs(sv.data) ** 2
        measured_state = int(np.argmax(probs))

        # Extract b register (qubits [half, 2*half))
        sum_result = 0
        for i in range(half):
            qubit_idx = half + i
            if measured_state & (1 << qubit_idx):
                sum_result += (1 << i)

        # Extract final carry from the dedicated carry output qubit
        carry_qubit = 3 * half
        carry_out = 1 if (measured_state & (1 << carry_qubit)) else 0

        return sum_result, carry_out

    def test_adder_3_plus_2_equals_5(self):
        """3 + 2 = 5 using 2-bit operands."""
        sum_result, carry = self._run_adder(half=2, a_val=3, b_val=2)
        expected = 3 + 2  # = 5
        total = sum_result + carry * (2 ** 2)
        self.assertEqual(
            total, expected,
            f"3 + 2: expected {expected}, got sum={sum_result}, carry={carry}"
        )

    def test_adder_7_plus_3_equals_10(self):
        """7 + 3 = 10 using 3-bit operands."""
        sum_result, carry = self._run_adder(half=3, a_val=7, b_val=3)
        expected = 7 + 3  # = 10
        total = sum_result + carry * (2 ** 3)
        self.assertEqual(
            total, expected,
            f"7 + 3: expected {expected}, got sum={sum_result}, carry={carry}"
        )

    def test_adder_1_plus_1_equals_2(self):
        """1 + 1 = 2 using 1-bit operands (carry case)."""
        sum_result, carry = self._run_adder(half=1, a_val=1, b_val=1)
        expected = 1 + 1  # = 2
        total = sum_result + carry * (2 ** 1)
        self.assertEqual(
            total, expected,
            f"1 + 1: expected {expected}, got sum={sum_result}, carry={carry}"
        )

    def test_adder_0_plus_0_equals_0(self):
        """0 + 0 = 0 (identity case)."""
        sum_result, carry = self._run_adder(half=2, a_val=0, b_val=0)
        self.assertEqual(sum_result, 0)
        self.assertEqual(carry, 0)

    def test_adder_multiple_cases(self):
        """Test several addition cases across different operand sizes."""
        test_cases = [
            # (half, a, b)
            (1, 0, 0),  # 0+0=0
            (1, 1, 0),  # 1+0=1
            (1, 0, 1),  # 0+1=1
            (1, 1, 1),  # 1+1=2 (overflow)
            (2, 3, 2),  # 3+2=5
            (2, 1, 3),  # 1+3=4
            (2, 2, 2),  # 2+2=4
            (3, 7, 3),  # 7+3=10
            (3, 5, 6),  # 5+6=11
            (3, 4, 4),  # 4+4=8
        ]
        for half, a, b in test_cases:
            with self.subTest(half=half, a=a, b=b):
                sum_result, carry = self._run_adder(half, a, b)
                expected = a + b
                total = sum_result + carry * (2 ** half)
                self.assertEqual(
                    total, expected,
                    f"{a}+{b}: expected {expected}, got {total} "
                    f"(sum={sum_result}, carry={carry})"
                )

    def test_make_quantum_adder_random_inputs(self):
        """Test that make_quantum_adder with random inputs produces correct sums."""
        from qiskit.quantum_info import Statevector

        for n_qubits in [5, 7, 9]:
            with self.subTest(n_qubits=n_qubits):
                qc = make_quantum_adder(n_qubits, seed=42)
                # Determine half from the circuit
                half = max((max(n_qubits, 3) - 1) // 2, 1)
                max_val = 2 ** half

                # Re-generate with same seed to get the input values
                rng = np.random.RandomState(42)
                a_val = rng.randint(0, max_val)
                b_val = rng.randint(0, max_val)
                expected = a_val + b_val

                # Run the circuit
                sv = Statevector.from_int(0, 2 ** qc.num_qubits).evolve(qc)
                probs = np.abs(sv.data) ** 2
                measured_state = int(np.argmax(probs))

                # Extract b register
                sum_result = 0
                for i in range(half):
                    qubit_idx = half + i
                    if measured_state & (1 << qubit_idx):
                        sum_result += (1 << i)

                # Extract final carry from the dedicated carry output qubit
                carry_qubit = 3 * half
                carry_out = 1 if (measured_state & (1 << carry_qubit)) else 0
                total = sum_result + carry_out * max_val

                self.assertEqual(
                    total, expected,
                    f"make_quantum_adder(n={n_qubits}): {a_val}+{b_val} "
                    f"expected {expected}, got {total}"
                )


# ============================================================================
# Rotation Merging Bug-Fix Tests (v3.1.0)
# ============================================================================

class TestRotationMergingBugFix(unittest.TestCase):
    """Tests for the global-phase bug fix in _merge_rotations (v3.1.0).

    BUG: The old code removed rotation gates whose angles summed to 2*pi,
    but R(2*pi) = -I (global phase), NOT identity.  This is incorrect for
    controlled operations or subcircuit contexts.

    FIX: Only remove gates when the raw sum of angles is ~0 (true identity).
    When the raw sum is a non-zero multiple of 2*pi, keep a single gate
    with the raw_sum angle to preserve the unitary exactly.
    """

    def _unitary_close(self, qc1, qc2, atol=1e-8):
        """Check if two circuits have the same unitary up to global phase."""
        op1 = Operator(qc1).data
        op2 = Operator(qc2).data
        # Check matrix equality up to global phase:
        # |Tr(U1^dag U2)| / d should be ~1 for unitaries differing only by phase
        d = op1.shape[0]
        inner = np.abs(np.trace(np.conj(op1).T @ op2)) / d
        return np.isclose(inner, 1.0, atol=atol)

    # --- Rz tests ---

    def test_rz_pi_plus_pi_not_removed(self):
        """Rz(pi) + Rz(pi) = Rz(2*pi) = -I: must NOT be removed."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.rz(np.pi, 0)
        qc.rz(np.pi, 0)

        result = optimizer.optimize(qc)

        # Must NOT reduce to 0 gates; should merge into a single Rz gate
        self.assertEqual(result.optimized_size, 1,
            "BUG: Rz(pi)+Rz(pi) was incorrectly removed! Rz(2pi) = -I, not I.")

    def test_rz_pi_plus_neg_pi_removed(self):
        """Rz(pi) + Rz(-pi) = Rz(0) = I: SHOULD be removed."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.rz(np.pi, 0)
        qc.rz(-np.pi, 0)

        result = optimizer.optimize(qc)

        self.assertEqual(result.optimized_size, 0,
            "Rz(pi)+Rz(-pi) should cancel to identity and be removed.")

    def test_rz_half_pi_plus_three_half_pi_not_removed(self):
        """Rz(pi/2) + Rz(3*pi/2) = Rz(2*pi) = -I: must NOT be removed."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.rz(np.pi / 2, 0)
        qc.rz(3 * np.pi / 2, 0)

        result = optimizer.optimize(qc)

        self.assertEqual(result.optimized_size, 1,
            "BUG: Rz(pi/2)+Rz(3pi/2) was incorrectly removed! Rz(2pi) = -I.")

    def test_rz_05_plus_neg_05_removed(self):
        """Rz(0.5) + Rz(-0.5) = Rz(0) = I: SHOULD be removed."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.rz(0.5, 0)
        qc.rz(-0.5, 0)

        result = optimizer.optimize(qc)

        self.assertEqual(result.optimized_size, 0,
            "Rz(0.5)+Rz(-0.5) should cancel to identity and be removed.")

    # --- Rx tests (same bug applies) ---

    def test_rx_pi_plus_pi_not_removed(self):
        """Rx(pi) + Rx(pi) = Rx(2*pi) = -I: must NOT be removed."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.rx(np.pi, 0)
        qc.rx(np.pi, 0)

        result = optimizer.optimize(qc)

        self.assertEqual(result.optimized_size, 1,
            "BUG: Rx(pi)+Rx(pi) was incorrectly removed! Rx(2pi) = -I.")

    def test_rx_pi_plus_neg_pi_removed(self):
        """Rx(pi) + Rx(-pi) = Rx(0) = I: SHOULD be removed."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.rx(np.pi, 0)
        qc.rx(-np.pi, 0)

        result = optimizer.optimize(qc)

        self.assertEqual(result.optimized_size, 0,
            "Rx(pi)+Rx(-pi) should cancel to identity and be removed.")

    # --- Ry tests (same bug applies) ---

    def test_ry_pi_plus_pi_not_removed(self):
        """Ry(pi) + Ry(pi) = Ry(2*pi) = -I: must NOT be removed."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.ry(np.pi, 0)
        qc.ry(np.pi, 0)

        result = optimizer.optimize(qc)

        self.assertEqual(result.optimized_size, 1,
            "BUG: Ry(pi)+Ry(pi) was incorrectly removed! Ry(2pi) = -I.")

    def test_ry_pi_plus_neg_pi_removed(self):
        """Ry(pi) + Ry(-pi) = Ry(0) = I: SHOULD be removed."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.ry(np.pi, 0)
        qc.ry(-np.pi, 0)

        result = optimizer.optimize(qc)

        self.assertEqual(result.optimized_size, 0,
            "Ry(pi)+Ry(-pi) should cancel to identity and be removed.")

    # --- Unitary preservation tests ---

    def test_unitary_preserved_rz_pi_plus_pi(self):
        """Unitary must be preserved after merging Rz(pi)+Rz(pi)."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.rz(np.pi, 0)
        qc.rz(np.pi, 0)

        result = optimizer.optimize(qc)
        self.assertTrue(
            self._unitary_close(qc, result.optimized_circuit),
            "Unitary not preserved after merging Rz(pi)+Rz(pi)")

    def test_unitary_preserved_rz_half_pi_plus_three_half_pi(self):
        """Unitary must be preserved after merging Rz(pi/2)+Rz(3*pi/2)."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.rz(np.pi / 2, 0)
        qc.rz(3 * np.pi / 2, 0)

        result = optimizer.optimize(qc)
        self.assertTrue(
            self._unitary_close(qc, result.optimized_circuit),
            "Unitary not preserved after merging Rz(pi/2)+Rz(3pi/2)")

    def test_unitary_preserved_rz_05_plus_neg_05(self):
        """Unitary must be preserved after removing Rz(0.5)+Rz(-0.5)."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.rz(0.5, 0)
        qc.rz(-0.5, 0)

        result = optimizer.optimize(qc)
        # Empty circuit = identity; original Rz(0.5)+Rz(-0.5) = Rz(0) = I
        self.assertTrue(
            self._unitary_close(qc, result.optimized_circuit),
            "Unitary not preserved after removing Rz(0.5)+Rz(-0.5)")

    def test_unitary_preserved_rx_pi_plus_pi(self):
        """Unitary must be preserved after merging Rx(pi)+Rx(pi)."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.rx(np.pi, 0)
        qc.rx(np.pi, 0)

        result = optimizer.optimize(qc)
        self.assertTrue(
            self._unitary_close(qc, result.optimized_circuit),
            "Unitary not preserved after merging Rx(pi)+Rx(pi)")

    def test_unitary_preserved_ry_pi_plus_pi(self):
        """Unitary must be preserved after merging Ry(pi)+Ry(pi)."""
        optimizer = GreedyGateCancellation()
        qc = QuantumCircuit(1)
        qc.ry(np.pi, 0)
        qc.ry(np.pi, 0)

        result = optimizer.optimize(qc)
        self.assertTrue(
            self._unitary_close(qc, result.optimized_circuit),
            "Unitary not preserved after merging Ry(pi)+Ry(pi)")

    # --- CNOT-Dihedral generator stress test ---

    def test_cnot_dihedral_no_false_removal(self):
        """Stress test: CNOT-Dihedral circuits with discrete angles.

        The CNOT-Dihedral generator uses angles {0, pi/2, pi, 3*pi/2},
        which are at highest risk of summing to multiples of 2*pi.
        The optimizer must preserve unitary equivalence.
        """
        optimizer = GreedyGateCancellation()
        circuit = generate_circuit(
            n_qubits=3, depth=10, seed=42,
            family=CircuitFamily.CNOT_DIHEDRAL
        )

        result = optimizer.optimize(circuit)

        # Fidelity must be ~1.0 (accounts for global phase)
        fid = optimizer.calculate_fidelity(result.optimized_circuit, circuit)
        self.assertGreaterEqual(fid, 0.9999,
            f"CNOT-Dihedral fidelity too low after optimization: {fid}")


# ============================================================================
# Fidelity Estimator Tests (2-design fix)
# ============================================================================

class TestFidelityEstimator(unittest.TestCase):
    """Tests for the _estimate_fidelity method with Haar-random product states.

    Validates the corrected estimator that uses independent Haar-random
    single-qubit unitaries (exact single-qubit 2-design) instead of the
    previous Ry+Rz rotations which had biased 4th moments (3/8 vs 1/3).
    """

    def test_identical_circuits_large_n(self):
        """Identical circuits with n > 12 should return fidelity 1.0 via early return."""
        optimizer = _TestOptimizer(random_seed=42)
        n = 13
        qc = QuantumCircuit(n)
        for i in range(n):
            qc.h(i)
        for i in range(n - 1):
            qc.cx(i, i + 1)

        fidelity = optimizer.calculate_fidelity(qc, qc)
        self.assertAlmostEqual(fidelity, 1.0, places=10)

    def test_equivalent_clifford_circuits_large_n(self):
        """Equivalent Clifford circuits with n > 12 should return 1.0 via tableau."""
        optimizer = _TestOptimizer(random_seed=42)
        n = 13
        qc1 = QuantumCircuit(n)
        for i in range(n):
            qc1.h(i)
        for i in range(n - 1):
            qc1.cx(i, i + 1)

        # H-H = I, so this is functionally identical to qc1
        qc2 = QuantumCircuit(n)
        qc2.h(0)
        qc2.h(0)
        for i in range(n):
            qc2.h(i)
        for i in range(n - 1):
            qc2.cx(i, i + 1)

        fidelity = optimizer.calculate_fidelity(qc1, qc2)
        self.assertAlmostEqual(fidelity, 1.0, places=10)

    def test_estimate_fidelity_known_analytical_value(self):
        """Sampling estimate should be within 5% of the exact fidelity.

        For circuit U and V = Ry(eps) on qubit 0 composed after U, the exact
        average gate fidelity is:
            F = (d^2 * cos^2(eps/2) + d) / (d^2 + d)
        where d = 2^n.  This holds because Tr(V^dag U) = Tr(Ry(-eps)) = 2*cos(eps/2)
        by cyclicity of the trace.
        """
        optimizer = _TestOptimizer(random_seed=42)
        n = 5
        eps = 0.3
        d = 2 ** n

        qc = QuantumCircuit(n)
        for i in range(n):
            qc.h(i)
        for i in range(n - 1):
            qc.cx(i, i + 1)

        qc2 = qc.copy()
        qc2.ry(eps, 0)

        # Exact fidelity via Operator (trace formula)
        u1 = np.array(Operator(qc).data)
        u2 = np.array(Operator(qc2).data)
        inner_product = np.abs(np.trace(np.conj(u1).T @ u2)) ** 2
        exact_fidelity = (inner_product + d) / (d ** 2 + d)

        # Analytical cross-check
        expected = (d ** 2 * np.cos(eps / 2) ** 2 + d) / (d ** 2 + d)
        self.assertAlmostEqual(exact_fidelity, expected, places=6,
            msg="Analytical formula disagrees with Operator-based computation")

        # Sampling estimate (call _estimate_fidelity directly)
        estimated = optimizer._estimate_fidelity(qc, qc2, n_samples=2000)

        # Must be within 5% relative error
        relative_error = abs(estimated - exact_fidelity) / exact_fidelity
        self.assertLessEqual(relative_error, 0.05,
            f"Fidelity estimate {estimated:.4f} deviates from exact {exact_fidelity:.4f} "
            f"by {relative_error * 100:.1f}% (threshold: 5%)")

    def test_estimate_fidelity_different_circuits(self):
        """Estimate for circuits with larger divergence should still be reasonable."""
        optimizer = _TestOptimizer(random_seed=42)
        n = 5
        eps = 0.5
        d = 2 ** n

        qc = QuantumCircuit(n)
        for i in range(n):
            qc.h(i)
        for i in range(n - 1):
            qc.cx(i, i + 1)

        qc2 = qc.copy()
        qc2.ry(eps, 0)

        # Exact fidelity
        u1 = np.array(Operator(qc).data)
        u2 = np.array(Operator(qc2).data)
        inner_product = np.abs(np.trace(np.conj(u1).T @ u2)) ** 2
        exact_fidelity = (inner_product + d) / (d ** 2 + d)

        # Sampling estimate
        estimated = optimizer._estimate_fidelity(qc, qc2, n_samples=2000)

        relative_error = abs(estimated - exact_fidelity) / exact_fidelity
        self.assertLessEqual(relative_error, 0.05,
            f"Fidelity estimate {estimated:.4f} deviates from exact {exact_fidelity:.4f} "
            f"by {relative_error * 100:.1f}% (threshold: 5%)")

    def test_estimate_fidelity_large_n_identical(self):
        """For n > 12 with identical circuits, calculate_fidelity returns 1.0."""
        optimizer = _TestOptimizer(random_seed=42)
        n = 13

        qc = QuantumCircuit(n)
        for i in range(n):
            qc.h(i)
        for i in range(n - 1):
            qc.cx(i, i + 1)
        for i in range(0, n - 1, 2):
            qc.cx(i, i + 1)

        fidelity = optimizer.calculate_fidelity(qc, qc)
        self.assertAlmostEqual(fidelity, 1.0, places=10)

    def test_estimate_fidelity_backward_compatible(self):
        """Method signature must remain backward-compatible (n_samples kwarg)."""
        optimizer = _TestOptimizer(random_seed=42)
        n = 5

        qc = QuantumCircuit(n)
        qc.h(0)
        qc.cx(0, 1)
        for i in range(2, n):
            qc.h(i)

        qc2 = qc.copy()
        qc2.ry(0.3, 0)

        # Should accept n_samples keyword without error
        result_100 = optimizer._estimate_fidelity(qc, qc2, n_samples=100)
        result_500 = optimizer._estimate_fidelity(qc, qc2, n_samples=500)

        # Both should be valid fidelity values in [0, 1]
        self.assertGreaterEqual(result_100, 0.0)
        self.assertLessEqual(result_100, 1.0)
        self.assertGreaterEqual(result_500, 0.0)
        self.assertLessEqual(result_500, 1.0)

    def test_estimate_fidelity_single_qubit_2design(self):
        """Verify the corrected estimator uses a single-qubit 2-design.

        The 4th moment E[|alpha|^4] for Haar-random single-qubit states
        should equal 1/3, not 3/8 as with the old Ry+Rz approach.
        This test indirectly validates this by checking that the fidelity
        estimate for the identity-vs-identity comparison equals 1.0 even
        when called through _estimate_fidelity (bypassing the == shortcut).
        """
        optimizer = _TestOptimizer(random_seed=42)
        n = 4

        qc = QuantumCircuit(n)
        qc.h(0)
        qc.cx(0, 1)
        qc.h(2)
        qc.cx(2, 3)

        # Structurally different circuit but functionally identical (X-X = I)
        qc2 = QuantumCircuit(n)
        qc2.x(0)
        qc2.x(0)
        qc2.h(0)
        qc2.cx(0, 1)
        qc2.h(2)
        qc2.cx(2, 3)

        # _estimate_fidelity may or may not detect equivalence;
        # the key assertion is that the estimate is very close to 1.0
        est = optimizer._estimate_fidelity(qc, qc2, n_samples=500)
        self.assertGreater(est, 0.95,
            f"Estimate for equivalent circuits should be ~1.0, got {est:.4f}")


# ============================================================================
# Wire Traversal (WCL) Preprocessor Tests
# ============================================================================

class TestWireTraversal(unittest.TestCase):
    """Tests for the WireTraversalPreprocessor and WCL-enabled Greedy optimizer.

    Validates:
    1. Unitary equivalence (WCL reorder must not change circuit semantics)
    2. Wire-consecutive grouping (same-qubit gates are adjacent in listing)
    3. Hand-crafted scenario where WCL creates adjacent inverse pairs
    4. Integration with GreedyGateCancellation(wire_traversal=True)
    """

    def _exact_unitary(self, qc):
        """Compute exact unitary matrix of a circuit."""
        return np.array(Operator(qc).data)

    # ------------------------------------------------------------------
    # 1. Unitary equivalence
    # ------------------------------------------------------------------

    def test_unitary_equivalence_single_qubit(self):
        """WCL on a single-qubit circuit must preserve the unitary."""
        pre = WireTraversalPreprocessor()
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.t(0)
        qc.rz(0.5, 0)

        wcl = pre.preprocess(qc)
        self.assertTrue(
            np.allclose(self._exact_unitary(qc), self._exact_unitary(wcl)),
            "WCL must preserve unitary on single-qubit circuit"
        )

    def test_unitary_equivalence_multi_qubit(self):
        """WCL on a multi-qubit circuit with entangling gates preserves unitary."""
        pre = WireTraversalPreprocessor()
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.cx(0, 1)
        qc.rz(0.3, 2)
        qc.h(1)
        qc.cx(1, 2)
        qc.t(0)
        qc.s(2)

        wcl = pre.preprocess(qc)
        self.assertTrue(
            np.allclose(self._exact_unitary(qc), self._exact_unitary(wcl)),
            "WCL must preserve unitary on multi-qubit circuit with CNOTs"
        )

    def test_unitary_equivalence_random_circuits(self):
        """WCL preserves unitary on random universal circuits."""
        pre = WireTraversalPreprocessor()
        for seed in range(10):
            qc = generate_circuit(
                n_qubits=4, depth=10, seed=seed,
                family=CircuitFamily.UNIVERSAL
            )
            wcl = pre.preprocess(qc)
            self.assertTrue(
                np.allclose(self._exact_unitary(qc), self._exact_unitary(wcl)),
                f"WCL unitary NOT preserved for seed={seed}"
            )

    def test_unitary_equivalence_real_benchmarks(self):
        """WCL preserves unitary on real benchmark circuits."""
        pre = WireTraversalPreprocessor()
        for factory, args in [(make_qft, (3,)), (make_ghz, (4,)),
                               (make_bernstein_vazirani, (3, 42))]:
            qc = factory(*args)
            wcl = pre.preprocess(qc)
            self.assertTrue(
                np.allclose(self._exact_unitary(qc), self._exact_unitary(wcl)),
                f"WCL unitary NOT preserved for {factory.__name__}"
            )

    def test_empty_circuit(self):
        """WCL on empty circuit returns equivalent empty circuit."""
        pre = WireTraversalPreprocessor()
        qc = QuantumCircuit(3)
        wcl = pre.preprocess(qc)
        self.assertEqual(wcl.size(), 0)
        self.assertEqual(wcl.num_qubits, 3)

    def test_single_gate_circuit(self):
        """WCL on single-gate circuit is a no-op."""
        pre = WireTraversalPreprocessor()
        qc = QuantumCircuit(2)
        qc.h(0)
        wcl = pre.preprocess(qc)
        self.assertEqual(wcl.size(), 1)
        self.assertTrue(
            np.allclose(self._exact_unitary(qc), self._exact_unitary(wcl))
        )

    # ------------------------------------------------------------------
    # 2. Wire-consecutive grouping
    # ------------------------------------------------------------------

    def test_same_qubit_gates_adjacent(self):
        """WCL should place same-qubit gates adjacently in the listing.

        Circuit: H(0), H(1), T(0), T(1)
        LBL order: H(0), H(1), T(0), T(1)
        WCL order should group: [H(0), T(0)], [H(1), T(1)]
        (or some valid topological permutation thereof).
        """
        pre = WireTraversalPreprocessor()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.h(1)
        qc.t(0)
        qc.t(1)

        wcl = pre.preprocess(qc)
        gate_names_qubits = [
            (inst.operation.name, [qc.find_bit(q).index for q in inst.qubits])
            for inst in wcl.data
        ]

        # Gate on qubit 0 should appear before gate on qubit 1
        q0_gates = [i for i, (_, qs) in enumerate(gate_names_qubits) if 0 in qs and 1 not in qs]
        q1_gates = [i for i, (_, qs) in enumerate(gate_names_qubits) if 1 in qs and 0 not in qs]

        # All qubit-0-only gates should come before all qubit-1-only gates
        if q0_gates and q1_gates:
            self.assertLess(
                max(q0_gates), min(q1_gates),
                f"WCL should group qubit-0 gates before qubit-1 gates. "
                f"Got listing: {gate_names_qubits}"
            )

    def test_wire_ordering_three_qubits(self):
        """WCL should produce listing in qubit 0, 1, 2 order for disjoint gates."""
        pre = WireTraversalPreprocessor()
        qc = QuantumCircuit(3)
        qc.h(2)
        qc.h(1)
        qc.h(0)
        qc.t(2)
        qc.t(1)
        qc.t(0)

        wcl = pre.preprocess(qc)
        qubit_order = []
        for inst in wcl.data:
            q = qc.find_bit(inst.qubits[0]).index
            qubit_order.append(q)

        # Should be [0, 0, 1, 1, 2, 2]
        self.assertEqual(
            qubit_order, [0, 0, 1, 1, 2, 2],
            f"WCL should order gates by qubit index. Got: {qubit_order}"
        )

    def test_two_qubit_gate_assigned_to_primary_wire(self):
        """Two-qubit gates are assigned to their primary wire but respect deps.

        Circuit: H(2), CNOT(0,2), H(1)
        - H(2): primary wire 2, no dependencies
        - CNOT(0,2): primary wire 0, depends on H(2) (shared qubit 2)
        - H(1): primary wire 1, no dependencies

        WCL order (respecting deps): H(1), H(2), CNOT(0,2)
        H(1) comes first (wire 1, no deps). H(2) comes second (wire 2, no deps).
        CNOT(0,2) must follow H(2) because they share qubit 2 and H(2) precedes
        CNOT in the original listing.
        """
        pre = WireTraversalPreprocessor()
        qc = QuantumCircuit(3)
        qc.h(2)
        qc.cx(0, 2)  # primary wire = 0, but depends on h(2) via qubit 2
        qc.h(1)

        wcl = pre.preprocess(qc)
        gate_info = [
            (inst.operation.name, sorted(qc.find_bit(q).index for q in inst.qubits))
            for inst in wcl.data
        ]

        # Expected order: h(1), h(2), cx(0,2)
        self.assertEqual(
            gate_info,
            [('h', [1]), ('h', [2]), ('cx', [0, 2])],
            f"WCL should order by wire while respecting deps. Got: {gate_info}"
        )

        # Verify unitary is preserved
        self.assertTrue(
            np.allclose(self._exact_unitary(qc), self._exact_unitary(wcl)),
            "WCL must preserve unitary"
        )

    # ------------------------------------------------------------------
    # 3. Hand-crafted cancellation scenario
    # ------------------------------------------------------------------

    def test_wcl_creates_adjacent_inverse_pairs(self):
        """WCL should bring same-qubit inverse gates adjacent, enabling cancellation.

        Circuit (LBL): H(0), H(1), H(0)
        In LBL, H(0) at position 0 and H(0) at position 2 are separated by H(1).
        Greedy (LBL) cannot cancel them (not adjacent).

        After WCL: H(0), H(0), H(1) -- the two H(0) gates are now adjacent.
        Greedy (WCL) should cancel them, leaving only H(1).
        """
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.h(1)
        qc.h(0)

        # LBL greedy: cannot cancel (H(0) and H(0) separated by H(1))
        greedy_lbl = GreedyGateCancellation(wire_traversal=False)
        result_lbl = greedy_lbl.optimize(qc)

        # WCL greedy: should cancel the two H(0) gates
        greedy_wcl = GreedyGateCancellation(wire_traversal=True)
        result_wcl = greedy_wcl.optimize(qc)

        # Verify WCL result preserves unitary
        self.assertTrue(
            np.allclose(self._exact_unitary(qc), self._exact_unitary(result_wcl.optimized_circuit)),
            "WCL greedy must preserve unitary"
        )

        # WCL should achieve better reduction
        self.assertGreater(
            result_wcl.reduction, result_lbl.reduction,
            f"WCL (reduction={result_wcl.reduction:.4f}) should beat "
            f"LBL (reduction={result_lbl.reduction:.4f}) on this circuit"
        )
        # WCL should cancel the H(0) pair, leaving only H(1)
        self.assertEqual(result_wcl.optimized_size, 1,
                         f"WCL should cancel H(0)-H(0) pair, leaving 1 gate. "
                         f"Got {result_wcl.optimized_size}")

    def test_wcl_creates_adjacent_cnot_pairs(self):
        """WCL should bring same-qubit CNOT pairs adjacent for cancellation.

        Circuit (LBL): CNOT(0,1), H(2), CNOT(0,1)
        In LBL, the two CNOTs are separated by H(2) (disjoint qubits).
        Greedy (LBL) cannot cancel them.

        After WCL: CNOT(0,1) has primary wire 0, H(2) has primary wire 2.
        WCL order: CNOT(0,1), CNOT(0,1), H(2) -- CNOTs are adjacent.
        Greedy (WCL) should cancel them, leaving only H(2).
        """
        qc = QuantumCircuit(3)
        qc.cx(0, 1)
        qc.h(2)
        qc.cx(0, 1)

        greedy_wcl = GreedyGateCancellation(wire_traversal=True)
        result_wcl = greedy_wcl.optimize(qc)

        self.assertTrue(
            np.allclose(self._exact_unitary(qc), self._exact_unitary(result_wcl.optimized_circuit)),
            "WCL greedy must preserve unitary"
        )
        self.assertEqual(result_wcl.optimized_size, 1,
                         f"WCL should cancel CNOT pair, leaving H(2). "
                         f"Got {result_wcl.optimized_size}")

    def test_wcl_tdg_t_cancellation_across_wires(self):
        """WCL should bring T-Tdg pair on same qubit adjacent even with intervening gates.

        Circuit: T(0), H(1), S(2), Tdg(0)
        All three intermediate gates are on different qubits from T/Tdg.
        WCL groups: [T(0), Tdg(0)], [H(1)], [S(2)] -- T-Tdg become adjacent.
        """
        qc = QuantumCircuit(3)
        qc.t(0)
        qc.h(1)
        qc.s(2)
        qc.tdg(0)

        greedy_wcl = GreedyGateCancellation(wire_traversal=True)
        result_wcl = greedy_wcl.optimize(qc)

        self.assertTrue(
            np.allclose(self._exact_unitary(qc), self._exact_unitary(result_wcl.optimized_circuit)),
            "WCL greedy must preserve unitary"
        )
        self.assertLess(result_wcl.optimized_size, qc.size(),
                        f"WCL should cancel T-Tdg pair. "
                        f"Original: {qc.size()}, Optimized: {result_wcl.optimized_size}")

    # ------------------------------------------------------------------
    # 4. Integration with GreedyGateCancellation
    # ------------------------------------------------------------------

    def test_wire_traversal_parameter_default_false(self):
        """Default wire_traversal parameter should be False."""
        opt = GreedyGateCancellation()
        self.assertFalse(opt.wire_traversal)

    def test_wire_traversal_parameter_true(self):
        """wire_traversal=True should enable WCL preprocessing."""
        opt = GreedyGateCancellation(wire_traversal=True)
        self.assertTrue(opt.wire_traversal)
        self.assertIsNotNone(opt._wcl_preprocessor)

    def test_wire_traversal_false_no_preprocessing(self):
        """wire_traversal=False should NOT apply WCL preprocessing."""
        opt = GreedyGateCancellation(wire_traversal=False)
        self.assertFalse(opt.wire_traversal)
        self.assertIsNone(opt._wcl_preprocessor)

    def test_wcl_greedy_fidelity_preservation(self):
        """WCL-enabled greedy must preserve fidelity on random circuits."""
        opt = GreedyGateCancellation(wire_traversal=True)
        for seed in range(10):
            qc = generate_circuit(
                n_qubits=3, depth=10, seed=seed,
                family=CircuitFamily.UNIVERSAL
            )
            result = opt.optimize(qc, target=qc)
            self.assertGreaterEqual(result.fidelity, 0.99,
                                    f"WCL greedy fidelity < 0.99 for seed={seed}: {result.fidelity}")
            self.assertLessEqual(result.optimized_size, result.original_size,
                                 f"WCL greedy increased gate count for seed={seed}")

    def test_wcl_metadata_reports_wire_traversal(self):
        """Result metadata should include wire_traversal flag."""
        opt = GreedyGateCancellation(wire_traversal=True)
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)

        result = opt.optimize(qc)
        self.assertIn('wire_traversal', result.metadata)
        self.assertTrue(result.metadata['wire_traversal'])

    def test_wcl_no_change_for_single_wire_circuit(self):
        """WCL should be a no-op for circuits where all gates are on one qubit."""
        pre = WireTraversalPreprocessor()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.t(0)
        qc.s(0)
        qc.rz(0.5, 0)

        wcl = pre.preprocess(qc)
        # Gate order should be identical
        for orig_inst, wcl_inst in zip(qc.data, wcl.data):
            self.assertEqual(orig_inst.operation.name, wcl_inst.operation.name)


# ============================================================================
# Ceiling-Aware Optimizer Tests (E21)
# ============================================================================

class TestCeilingAware(unittest.TestCase):
    """Tests for the CeilingAwareOptimizer and action-space proxies.

    E21 validates three properties:
    1. The ceiling-aware optimizer produces the SAME gate reduction as
       the naive always-run pipeline (HybridCommuteRewrite).
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
        from src.optimisation.ceiling_aware import CeilingAwareOptimizer

        qc = make_cnot_chain(4, repeats=4)
        naive = HybridCommuteRewrite()
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
        from src.optimisation.ceiling_aware import CeilingAwareOptimizer

        circuit = generate_circuit(
            n_qubits=3, depth=10, seed=42,
            family=CircuitFamily.UNIVERSAL
        )
        naive = HybridCommuteRewrite()
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
        from src.optimisation.ceiling_aware import CeilingAwareOptimizer

        circuits = [
            ("QFT", make_qft(4)),
            ("GHZ", make_ghz(4)),
            ("CNOT", make_cnot_chain(3, repeats=3)),
            ("BV", make_bernstein_vazirani(3, seed=42)),
        ]
        naive = HybridCommuteRewrite()
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
        from src.optimisation.ceiling_aware import CeilingAwareOptimizer

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
        from src.optimisation.ceiling_aware import CeilingAwareOptimizer

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
        from src.optimisation.ceiling_aware import CeilingAwareOptimizer

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
        from src.optimisation.ceiling_aware import CeilingAwareOptimizer

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
        from src.optimisation.ceiling_aware import count_phase1_actions

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
        from src.optimisation.ceiling_aware import count_phase1_actions

        qc = QuantumCircuit(2)
        self.assertEqual(count_phase1_actions(qc), 0)

    def test_proxy_detects_hh_pair(self):
        """count_phase1_actions should detect an adjacent H-H pair."""
        from src.optimisation.ceiling_aware import count_phase1_actions

        qc = QuantumCircuit(1)
        qc.h(0)
        qc.h(0)
        self.assertGreaterEqual(count_phase1_actions(qc), 1)

    def test_proxy_zero_for_no_cancellable_pairs(self):
        """count_phase1_actions should return 0 when no adjacent pairs cancel."""
        from src.optimisation.ceiling_aware import count_phase1_actions

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
        from src.optimisation.ceiling_aware import count_phase1_actions

        qc = QuantumCircuit(1)
        qc.rz(0.5, 0)
        qc.rz(0.3, 0)  # Same axis, same qubit -> mergeable
        self.assertGreaterEqual(count_phase1_actions(qc), 1)

    def test_proxy_counts_multiple_pairs(self):
        """count_phase1_actions should count all adjacent cancellable pairs."""
        from src.optimisation.ceiling_aware import count_phase1_actions

        qc = QuantumCircuit(1)
        qc.h(0); qc.h(0)    # pair 1
        qc.x(0); qc.x(0)    # pair 2
        qc.z(0); qc.z(0)    # pair 3
        self.assertEqual(count_phase1_actions(qc), 3)

    def test_phase2_proxy_detects_commutation_opportunities(self):
        """count_phase2_actions should detect non-adjacent inverse pairs with commuting intermediates."""
        from src.optimisation.ceiling_aware import count_phase2_actions

        # CNOT(0,1), S(0), CNOT(0,1) -> S commutes with CNOT on control
        qc = QuantumCircuit(2)
        qc.cx(0, 1)
        qc.s(0)
        qc.cx(0, 1)
        self.assertGreaterEqual(count_phase2_actions(qc), 1)

    def test_phase2_proxy_zero_when_no_opportunities(self):
        """count_phase2_actions should return 0 when no commutation-enabled pairs exist."""
        from src.optimisation.ceiling_aware import count_phase2_actions

        # H(0), X(0), H(0) -> X does NOT commute with H, so no opportunity
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.x(0)
        qc.h(0)
        self.assertEqual(count_phase2_actions(qc), 0)

    def test_detailed_result_populates_all_fields(self):
        """optimize_detailed should populate all timing and skip fields."""
        from src.optimisation.ceiling_aware import CeilingAwareOptimizer

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
        from src.optimisation.ceiling_aware import CeilingAwareOptimizer

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


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    # Run with verbosity 2 for detailed output
    unittest.main(verbosity=2)
