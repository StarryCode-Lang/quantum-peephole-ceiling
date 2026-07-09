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


if __name__ == '__main__':
    unittest.main()
