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
        optimizer = HybridPhase2aRewrite()
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



if __name__ == '__main__':
    unittest.main(verbosity=2)
