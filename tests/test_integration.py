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
            'commutation': Phase2aCommutationRewriter(),
            'hybrid': HybridPhase2aRewrite(),
        }
        
        results = {}
        for name, opt in optimizers.items():
            result = opt.optimize(circuit)
            results[name] = result
            
            # All optimizers must preserve fidelity
            self.assertGreaterEqual(result.fidelity, 0.99,
                f"{name} failed fidelity check: {result.fidelity}")
            # Deterministic peephole optimizers must not increase gate count.
            # Stochastic optimizers (RLS, SA, GA) may use INSERTION moves and
            # therefore can increase gate count during search; only fidelity is
            # required for them.
            if name in ('greedy', 'commutation', 'hybrid'):
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



if __name__ == '__main__':
    unittest.main(verbosity=2)
