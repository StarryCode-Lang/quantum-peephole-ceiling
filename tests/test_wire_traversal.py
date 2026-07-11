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
# Main
# ============================================================================

if __name__ == '__main__':
    # Run with verbosity 2 for detailed output
    unittest.main(verbosity=2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
