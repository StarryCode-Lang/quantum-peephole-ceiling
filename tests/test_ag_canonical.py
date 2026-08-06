"""Tests for Aaronson-Gottesman canonical form circuit generator."""

import os
import sys
import unittest

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.circuits.ag_canonical import generate_ag_canonical_circuit, generate_ag_canonical_batch


class TestAGCanonical(unittest.TestCase):
    def test_generates_valid_circuit(self):
        qc = generate_ag_canonical_circuit(4, seed=42)
        self.assertIsInstance(qc, QuantumCircuit)
        self.assertEqual(qc.num_qubits, 4)
        self.assertGreater(qc.size(), 0)

    def test_reproducible(self):
        qc1 = generate_ag_canonical_circuit(5, seed=123)
        qc2 = generate_ag_canonical_circuit(5, seed=123)
        self.assertEqual(qc1.size(), qc2.size())
        self.assertEqual(
            [inst.operation.name for inst in qc1.data],
            [inst.operation.name for inst in qc2.data],
        )

    def test_batch(self):
        circuits = generate_ag_canonical_batch(4, 10, base_seed=42)
        self.assertEqual(len(circuits), 10)
        self.assertTrue(all(c.num_qubits == 4 for c in circuits))

    def test_stages_are_disjoint(self):
        qc = generate_ag_canonical_circuit(6, seed=42, apply_h=True, apply_s=False)
        # Within each CNOT layer, no two CNOTs should share a qubit.
        stage = []
        for inst in qc.data:
            name = inst.operation.name
            if name in ('cx', 'cnot'):
                stage.append(inst)
            elif stage:
                qubits = set()
                for s in stage:
                    for q in s.qubits:
                        idx = qc.find_bit(q).index
                        self.assertNotIn(idx, qubits)
                        qubits.add(idx)
                stage = []

    def test_s_sdg_sampling_is_symmetric(self):
        """Regression test for the S/Sdg sampling asymmetry bug.

        The AG form has two S stages with n independent draws each, and the
        documented design applies S with probability 0.3 and Sdg with
        probability 0.3.  The historical implementation used two sequential
        ``rng.random() < 0.3`` draws, which made P(Sdg) = 0.7*0.3 = 0.21.
        Over 300 circuits of n=4 (8 draws/circuit = 2400 draws) the expected
        counts are 720 each with binomial std ~22.4; the 5-sigma band below
        would reject the buggy 0.21 distribution (expected 504) decisively.
        """
        n_qubits, n_circuits = 4, 300
        draws_per_circuit = 2 * n_qubits  # two S stages
        total_draws = n_circuits * draws_per_circuit
        n_s = 0
        n_sdg = 0
        for i in range(n_circuits):
            qc = generate_ag_canonical_circuit(n_qubits, seed=10_000 + i)
            ops = qc.count_ops()
            n_s += ops.get('s', 0)
            n_sdg += ops.get('sdg', 0)

        expected = 0.3 * total_draws
        sigma = (total_draws * 0.3 * 0.7) ** 0.5
        self.assertGreater(n_s, expected - 5 * sigma)
        self.assertLess(n_s, expected + 5 * sigma)
        self.assertGreater(n_sdg, expected - 5 * sigma)
        self.assertLess(n_sdg, expected + 5 * sigma)
        # Symmetry between S and Sdg (difference std ~ sqrt(2)*sigma).
        self.assertLess(abs(n_s - n_sdg), 5 * (2 ** 0.5) * sigma)
        # The buggy distribution (P(Sdg)=0.21 -> ~504) must be excluded.
        self.assertGreater(n_sdg, 0.25 * total_draws)


if __name__ == '__main__':
    unittest.main()
