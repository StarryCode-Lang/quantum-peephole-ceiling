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
            "IQP", "RandomClifford", "SurfaceCode", "UCCSD_inspired", "HaarRandom",
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
        optimizer = HybridPhase2aRewrite()
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



if __name__ == '__main__':
    unittest.main(verbosity=2)
