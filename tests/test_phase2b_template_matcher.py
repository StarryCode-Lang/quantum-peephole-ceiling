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

    def test_h_cx_h_target_to_cz(self):
        """H on target of CX is equivalent to CZ: H_t CX(c,t) H_t = CZ(c,t)."""
        qc = QuantumCircuit(2)
        qc.h(1)
        qc.cx(0, 1)
        qc.h(1)

        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        optimized = result.optimized_circuit

        self.assertEqual(optimized.size(), 1)
        self.assertEqual(optimized.data[0].operation.name, 'cz')
        self.assert_unitary_equal(qc, optimized)

    def test_s_sdag_cancellation(self):
        qc = QuantumCircuit(1)
        qc.s(0)
        qc.sdg(0)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 0)
        self.assert_unitary_equal(qc, result.optimized_circuit)

    def test_cz_cz_cancellation(self):
        qc = QuantumCircuit(2)
        qc.cz(0, 1)
        qc.cz(1, 0)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 0)
        self.assert_unitary_equal(qc, result.optimized_circuit)

    def test_h_h_cancellation(self):
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.h(0)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 0)
        self.assert_unitary_equal(qc, result.optimized_circuit)


class TestPhase2bTemplateLibraryV2(unittest.TestCase):
    """Tests for the v2.0.0 extended template library (E26/v8)."""

    def assert_unitary_equal(self, left, right, tol=1e-10):
        self.assertTrue(
            np.allclose(Operator(left).data, Operator(right).data, atol=tol),
            f"unitaries differ for {left.size()} -> {right.size()} gates",
        )

    # ---- inverse-cancellation closure ------------------------------------

    def test_cx_cx_cancellation(self):
        qc = QuantumCircuit(2)
        qc.cx(0, 1)
        qc.cx(0, 1)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 0)
        self.assert_unitary_equal(qc, result.optimized_circuit)

    def test_ccx_ccx_cancellation(self):
        qc = QuantumCircuit(3)
        qc.ccx(0, 1, 2)
        qc.ccx(0, 1, 2)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 0)
        self.assert_unitary_equal(qc, result.optimized_circuit)

    def test_cswap_cswap_cancellation(self):
        qc = QuantumCircuit(3)
        qc.cswap(0, 1, 2)
        qc.cswap(0, 1, 2)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 0)
        self.assert_unitary_equal(qc, result.optimized_circuit)

    def test_t_tdg_cancellation(self):
        qc = QuantumCircuit(1)
        qc.t(0)
        qc.tdg(0)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 0)
        self.assert_unitary_equal(qc, result.optimized_circuit)

    def test_x_and_z_self_inverse(self):
        qc = QuantumCircuit(1)
        qc.x(0)
        qc.x(0)
        qc.z(0)
        qc.z(0)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 0)
        self.assert_unitary_equal(qc, result.optimized_circuit)

    # ---- phase-polynomial merging ----------------------------------------

    def test_phase_merge_ss_to_z(self):
        qc = QuantumCircuit(1)
        qc.s(0)
        qc.s(0)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 1)
        self.assertEqual(result.optimized_circuit.data[0].operation.name, 'z')
        self.assert_unitary_equal(qc, result.optimized_circuit)
        self.assertEqual(result.metadata['phase_merges'], 1)

    def test_phase_merge_tt_to_s(self):
        qc = QuantumCircuit(1)
        qc.t(0)
        qc.t(0)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 1)
        self.assertEqual(result.optimized_circuit.data[0].operation.name, 's')
        self.assert_unitary_equal(qc, result.optimized_circuit)

    def test_phase_merge_to_identity(self):
        qc2 = QuantumCircuit(1)
        qc2.s(0)
        qc2.sdg(0)  # inverse-pair cancellation path
        result = Phase2bTemplateMatcher().optimize(qc2, target=qc2)
        self.assertEqual(result.optimized_size, 0)
        self.assert_unitary_equal(qc2, result.optimized_circuit)

    def test_phase_merge_generic_angle_to_p(self):
        qc = QuantumCircuit(1)
        qc.t(0)
        qc.rz(0.3, 0)  # must NOT cross-merge (global phase differs)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 2)
        self.assert_unitary_equal(qc, result.optimized_circuit)

    def test_rotation_merge_rz(self):
        qc = QuantumCircuit(1)
        qc.rz(0.3, 0)
        qc.rz(0.4, 0)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 1)
        self.assertAlmostEqual(
            float(result.optimized_circuit.data[0].operation.params[0]), 0.7, places=12)
        self.assert_unitary_equal(qc, result.optimized_circuit)

    def test_rotation_inverse_cancellation(self):
        qc = QuantumCircuit(1)
        qc.ry(0.55, 0)
        qc.ry(-0.55, 0)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 0)
        self.assert_unitary_equal(qc, result.optimized_circuit)

    # ---- conjugation templates --------------------------------------------

    def test_h_cz_h_to_cx_on_qubit1(self):
        qc = QuantumCircuit(2)
        qc.h(1)
        qc.cz(0, 1)
        qc.h(1)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 1)
        inst = result.optimized_circuit.data[0]
        self.assertEqual(inst.operation.name, 'cx')
        self.assertEqual([result.optimized_circuit.find_bit(q).index for q in inst.qubits], [0, 1])
        self.assert_unitary_equal(qc, result.optimized_circuit)

    def test_h_cz_h_to_cx_on_qubit0(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cz(0, 1)
        qc.h(0)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 1)
        inst = result.optimized_circuit.data[0]
        self.assertEqual(inst.operation.name, 'cx')
        self.assertEqual([result.optimized_circuit.find_bit(q).index for q in inst.qubits], [1, 0])
        self.assert_unitary_equal(qc, result.optimized_circuit)

    def test_h_ccx_h_to_ccz(self):
        qc = QuantumCircuit(3)
        qc.h(2)
        qc.ccx(0, 1, 2)
        qc.h(2)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 1)
        self.assert_unitary_equal(qc, result.optimized_circuit)
        self.assertEqual(result.metadata['mcz_conversions'], 1)

    def test_h_mcx_h_to_mcz(self):
        qc = QuantumCircuit(4)
        qc.h(3)
        qc.mcx([0, 1, 2], 3)
        qc.h(3)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 1)
        self.assert_unitary_equal(qc, result.optimized_circuit)

    def test_reversal_guard_prevents_oscillation(self):
        """A reversed CNOT (control > target) must never re-reverse."""
        qc = QuantumCircuit(2)
        qc.h(1)
        qc.cx(1, 0)  # control > target: guard must block the reversal
        qc.h(1)
        result = Phase2bTemplateMatcher().optimize(qc, target=qc)
        self.assertEqual(result.optimized_size, 3)
        self.assertEqual(result.metadata['template_rewrites'], 0)
        self.assert_unitary_equal(qc, result.optimized_circuit)

    # ---- regression: negative-index wraparound (v2.0.0-rc1 bug) -----------

    def test_no_negative_index_wraparound(self):
        """H-gather left search hitting the circuit start must not wrap to -1.

        Regression test for the v2.0.0-rc1 bug where the left search range
        included index -1 (the *last* gate), letting an H from the circuit
        end "bubble" across position 0 and corrupt the unitary (Grover(5)
        fidelity dropped to 0.67).
        """
        # Left search for a sandwich H on qubit 2 finds no H before the
        # circuit start; the *last* gate is an H on qubit 2.  The rc1 range
        # bug wrapped to index -1 (this trailing H) and corrupted the
        # unitary; the fix must leave the circuit equivalent.
        qc = QuantumCircuit(3)
        qc.x(0)
        qc.cx(0, 1)
        qc.mcx([0, 1], 2)             # controlled gate scanned by the gather
        qc.x(1)
        qc.h(2)                       # trailing H on qubit 2 (was wrapped)
        result = Phase2bTemplateMatcher().optimize_full_pipeline(qc, target=qc)
        self.assert_unitary_equal(qc, result.optimized_circuit)
        self.assertAlmostEqual(result.fidelity, 1.0, places=10)

    def test_grover_fidelity_preserved(self):
        import sys as _sys
        import os as _os
        _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..'))
        from src.circuits.real_benchmarks import make_grover
        opt = Phase2bTemplateMatcher()
        for n, seed in ((3, 1), (4, 2), (5, 1)):
            with self.subTest(n=n, seed=seed):
                qc = make_grover(n, seed=seed)
                result = opt.optimize_full_pipeline(qc, target=qc)
                self.assertAlmostEqual(result.fidelity, 1.0, places=10)
                self.assertLessEqual(result.optimized_size, result.original_size)


class TestPhase2bFullPipelineBV(unittest.TestCase):
    """Full-pipeline validation of Theorem 9 on BV oracle circuits."""

    @staticmethod
    def make_bv(n, secret):
        qc = QuantumCircuit(n + 1)
        anc = n
        qc.x(anc)
        qc.h(anc)
        for i in range(n):
            qc.h(i)
        for i in range(n):
            if (secret >> i) & 1:
                qc.cx(i, anc)
        for i in range(n):
            qc.h(i)
        return qc

    def test_bv_reaches_k_plus_2_optimum(self):
        """The v2 pipeline reduces BV(n, secret) to exactly k+2 gates."""
        opt = Phase2bTemplateMatcher()
        for n in (2, 3, 4, 5):
            for trial in range(5):
                secret = (1 << n) - 1 if trial == 0 else int(
                    np.random.RandomState(1000 * trial + n).randint(1, 1 << n))
                k = bin(secret).count('1')
                qc = self.make_bv(n, secret)
                with self.subTest(n=n, secret=secret):
                    result = opt.optimize_full_pipeline(qc, target=qc)
                    self.assertEqual(result.optimized_size, k + 2)
                    self.assertAlmostEqual(result.fidelity, 1.0, places=10)

    def test_bv_exceeds_thm9_bound(self):
        """Mean Phase-2b reduction must meet/exceed n/(4.5n+4) for n=3..9."""
        opt = Phase2bTemplateMatcher()
        for n in (3, 5, 7, 9):
            reductions = []
            for trial in range(6):
                secret = (1 << n) - 1 if trial == 0 else int(
                    np.random.RandomState(42 + trial * 1000 + n).randint(1, 1 << n))
                qc = self.make_bv(n, secret)
                result = opt.optimize_full_pipeline(qc, target=None)
                reductions.append(result.reduction)
            bound = n / (4.5 * n + 4)
            with self.subTest(n=n):
                self.assertGreaterEqual(float(np.mean(reductions)), bound)
                # The v2 pipeline is far above the rigorous bound in practice.
                self.assertGreaterEqual(float(np.min(reductions)), 0.30)


if __name__ == '__main__':
    unittest.main()
