"""Tests for Theorem-7 hardness family construction."""

import os
import sys
import unittest

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.circuits.hardness_families import make_theorem7_hardness_family
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase2 import Phase2aCommutationRewriter


class TestTheorem7HardnessFamily(unittest.TestCase):
    def test_circuit_implements_identity(self):
        for n in (4, 6, 8):
            with self.subTest(n=n):
                qc = make_theorem7_hardness_family(n)
                u = Operator(qc).data
                dim = 2 ** n
                self.assertTrue(np.allclose(u, np.eye(dim)))

    def test_phase1_no_reduction(self):
        opt = GreedyGateCancellation()
        for n in (4, 6, 8):
            with self.subTest(n=n):
                qc = make_theorem7_hardness_family(n)
                result = opt.optimize(qc, target=qc)
                self.assertAlmostEqual(result.reduction, 0.0, places=10)

    def test_phase2a_achieves_omega_one(self):
        opt = Phase2aCommutationRewriter(max_iterations=500, window_size=30)
        for n in (4, 6, 8, 10):
            with self.subTest(n=n):
                qc = make_theorem7_hardness_family(n)
                result = opt.optimize(qc, target=None)
                self.assertGreaterEqual(result.reduction, 1.0 / 6.0 - 1e-9)

    def test_invalid_n_raises(self):
        with self.assertRaises(ValueError):
            make_theorem7_hardness_family(3)
        with self.assertRaises(ValueError):
            make_theorem7_hardness_family(5)


if __name__ == '__main__':
    unittest.main()
