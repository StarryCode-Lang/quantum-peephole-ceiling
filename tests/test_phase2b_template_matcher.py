import os
import sys
import unittest

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.optimisation.phase2 import Phase2bTemplateMatcher


class TestPhase2bTemplateMatcher(unittest.TestCase):
    def assert_unitary_equal(self, left, right, tol=1e-10):
        self.assertTrue(
            np.allclose(Operator(left).data, Operator(right).data, atol=tol),
            f"unitaries differ for {left.size()} -> {right.size()} gates",
        )

    def make_bv_like_template_pipeline(self, n):
        qc = QuantumCircuit(n + 1)
        anc = n
        for q in range(n):
            qc.h(q)
            qc.cx(q, anc)
            qc.h(q)
            qc.h(anc)
            qc.h(anc)
        return qc

    def test_basic_h_cx_h_control_template(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.h(0)

        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        optimized = result.optimized_circuit

        self.assertEqual([inst.operation.name for inst in optimized.data], ['h', 'cx', 'h'])
        self.assertEqual(
            [[optimized.find_bit(q).index for q in inst.qubits] for inst in optimized.data],
            [[1], [1, 0], [1]],
        )
        self.assert_unitary_equal(qc, optimized)
        self.assertAlmostEqual(result.fidelity, 1.0, places=10)

    def test_exposed_adjacent_h_pairs_cancel(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.h(0)
        qc.h(1)
        qc.h(1)

        result = Phase2bTemplateMatcher().optimize(qc, target=qc)

        self.assertEqual(result.optimized_size, 3)
        self.assertEqual([inst.operation.name for inst in result.optimized_circuit.data], ['h', 'cx', 'h'])
        self.assert_unitary_equal(qc, result.optimized_circuit)
        self.assertEqual(result.metadata['template_rewrites'], 1)
        self.assertEqual(result.metadata['hh_cancellations'], 1)

    def test_bv_like_unitary_and_fidelity_preserved_for_2_3_5(self):
        optimizer = Phase2bTemplateMatcher()
        for n in (2, 3, 5):
            with self.subTest(n=n):
                qc = self.make_bv_like_template_pipeline(n)
                result = optimizer.optimize(qc, target=qc)
                self.assert_unitary_equal(qc, result.optimized_circuit)
                self.assertAlmostEqual(result.fidelity, 1.0, places=10)
                self.assertLessEqual(result.optimized_size, result.original_size)

    def test_bv_like_measured_bound_for_2_3_5(self):
        optimizer = Phase2bTemplateMatcher()
        for n in (2, 3, 5):
            with self.subTest(n=n):
                qc = self.make_bv_like_template_pipeline(n)
                result = optimizer.optimize(qc, target=qc)
                self.assertEqual(result.original_size, 5 * n)
                self.assertEqual(result.optimized_size, n + 2)
                self.assertAlmostEqual(result.reduction, 1.0 - (n + 2) / (5 * n))
                self.assertEqual(result.metadata['template_rewrites'], n)
                self.assertEqual(result.metadata['hh_cancellations'], 2 * n - 1)


if __name__ == '__main__':
    unittest.main()
