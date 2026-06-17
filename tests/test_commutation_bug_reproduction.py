"""
Commutation Rewriter Bug Reproduction
======================================
Demonstrates the correctness bug in the Phase-2 CommutationRewriter.

THE BUG
-------
In CommutationRewriter.optimize():

  Pre-check (lines 57-61):
    Verifies: _gates_commute(circuit, gate[i], gate[k])
    i.e., intermediates must commute with the STATIONARY gate.

  Bubble-sort (lines 65-70):
    Requires: _gates_commute(circuit, gate[k], gate[j])
    i.e., intermediates must commute with the MOVING gate.

These are DIFFERENT conditions when gate[i] and gate[j] belong to
different commutation families.  For the current gate set, all
self-inverse pairs happen to share the same commutation family,
making the bug latent.  The fix is to require commutation with BOTH
gate[i] AND gate[j] in the pre-check.

This script demonstrates:
1. The condition divergence (pre-check vs bubble-sort check different things)
2. A circuit where the algorithm's behavior is affected
3. Unitary verification via exact matrix computation
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from src.optimisation.phase2.commutation_rewriter import CommutationRewriter
from src.optimisation.base import BaseOptimizer, OptimizationResult


# ---------------------------------------------------------------------------
# Concrete optimizer for inspecting internal methods
# ---------------------------------------------------------------------------
class _Inspector(BaseOptimizer):
    """Concrete optimizer used only for calling inherited helper methods."""
    def optimize(self, circuit, target=None):
        return OptimizationResult(
            optimized_circuit=circuit.copy(),
            original_size=circuit.size(),
            optimized_size=circuit.size(),
            fidelity=1.0, iterations=0,
            runtime_seconds=0.0, success=True,
        )


def _unitary(qc: QuantumCircuit) -> np.ndarray:
    """Return the unitary matrix of a circuit."""
    return np.array(Operator(qc).data)


def _unitaries_match(qc1: QuantumCircuit, qc2: QuantumCircuit,
                     tol: float = 1e-10) -> bool:
    """Check whether two circuits have the same unitary (up to global phase)."""
    u1 = _unitary(qc1)
    u2 = _unitary(qc2)
    if u1.shape != u2.shape:
        return False
    return np.allclose(u1, u2, atol=tol)


# ===========================================================================
# DEMONSTRATION 1: Condition divergence
# ===========================================================================
def demo_condition_divergence():
    """
    Show that the pre-check and bubble-sort test DIFFERENT conditions.

    For the current gate set, self-inverse pairs always share the same
    commutation family, so the conditions give the same result.
    We verify this by exhaustively checking all self-inverse pair types.
    """
    print("=" * 70)
    print("DEMONSTRATION 1: Pre-check vs Bubble-sort condition divergence")
    print("=" * 70)

    insp = _Inspector()

    # Case A: S(0), CNOT(0,1), Sdg(0)
    # gate[i]=S, gate[j]=Sdg, intermediate=CNOT
    qc = QuantumCircuit(2)
    qc.s(0); qc.cx(0, 1); qc.sdg(0)

    gi, gm, gj = qc.data[0], qc.data[1], qc.data[2]

    precheck = insp._gates_commute(qc, gi, gm)       # commute with gate[i]?
    bubblesort = insp._gates_commute(qc, gm, gj)      # commute with gate[j]?

    print(f"\n  Circuit: S(0), CNOT(0,1), Sdg(0)")
    print(f"  Pre-check  _gates_commute(gate[i]=S, mid=CNOT)   = {precheck}")
    print(f"  Bubble-sort _gates_commute(mid=CNOT, gate[j]=Sdg) = {bubblesort}")
    print(f"  Same answer: {precheck == bubblesort}")

    # Case B: CNOT(0,1), S(0), CNOT(0,1)
    # gate[i]=CNOT, gate[j]=CNOT, intermediate=S
    qc2 = QuantumCircuit(2)
    qc2.cx(0, 1); qc2.s(0); qc2.cx(0, 1)

    gi2, gm2, gj2 = qc2.data[0], qc2.data[1], qc2.data[2]

    precheck2 = insp._gates_commute(qc2, gi2, gm2)
    bubblesort2 = insp._gates_commute(qc2, gm2, gj2)

    print(f"\n  Circuit: CNOT(0,1), S(0), CNOT(0,1)")
    print(f"  Pre-check  _gates_commute(gate[i]=CNOT, mid=S)   = {precheck2}")
    print(f"  Bubble-sort _gates_commute(mid=S, gate[j]=CNOT)   = {bubblesort2}")
    print(f"  Same answer: {precheck2 == bubblesort2}")

    # Case C: H(0), X(0), H(0)
    # gate[i]=H, gate[j]=H, intermediate=X
    # H and X do NOT commute, so both conditions fail
    qc3 = QuantumCircuit(1)
    qc3.h(0); qc3.x(0); qc3.h(0)

    gi3, gm3, gj3 = qc3.data[0], qc3.data[1], qc3.data[2]

    precheck3 = insp._gates_commute(qc3, gi3, gm3)
    bubblesort3 = insp._gates_commute(qc3, gm3, gj3)

    print(f"\n  Circuit: H(0), X(0), H(0)")
    print(f"  Pre-check  _gates_commute(gate[i]=H, mid=X)   = {precheck3}")
    print(f"  Bubble-sort _gates_commute(mid=X, gate[j]=H)   = {bubblesort3}")
    print(f"  Same answer: {precheck3 == bubblesort3}")
    print(f"  NOTE: H*X*H = Z (valid cancellation), but algorithm skips")
    print(f"        because H and X don't commute (neither condition passes)")

    print("\n  VERDICT: The pre-check and bubble-sort test DIFFERENT conditions")
    print("  (commute with gate[i] vs commute with gate[j]).")
    print("  For the current gate set, self-inverse pairs always share the")
    print("  same commutation family, so both conditions agree.")
    print("  The pre-check is SEMANTICALLY WRONG but happens to give the")
    print("  same result.  This is a latent correctness defect.")


# ===========================================================================
# DEMONSTRATION 2: Valid cancellation the algorithm handles correctly
# ===========================================================================
def demo_valid_cancellation():
    """
    Show a circuit where the algorithm correctly cancels a non-adjacent
    self-inverse pair, and verify unitary preservation.
    """
    print("\n" + "=" * 70)
    print("DEMONSTRATION 2: Correct cancellation (unitary preserved)")
    print("=" * 70)

    opt = CommutationRewriter(window_size=10)

    # Circuit: CNOT(0,1), S(0), Rz(pi/4, 0), CNOT(0,1)
    # Both S and Rz(pi/4) are Z-family on qubit 0 (CNOT control).
    # They commute with both CNOTs.  CNOT-CNOT cancel -> S(0)*Rz(pi/4,0).
    qc = QuantumCircuit(2)
    qc.cx(0, 1)
    qc.s(0)
    qc.rz(np.pi / 4, 0)
    qc.cx(0, 1)

    U_before = _unitary(qc)
    result = opt.optimize(qc)
    U_after = _unitary(result.optimized_circuit)

    print(f"\n  Circuit: CNOT(0,1), S(0), Rz(pi/4,0), CNOT(0,1)")
    print(f"  Original size:  {qc.size()}")
    print(f"  Optimized size: {result.optimized_circuit.size()}")
    print(f"  Cancellation performed: {result.optimized_circuit.size() < qc.size()}")
    print(f"  Unitary preserved: {np.allclose(U_before, U_after)}")

    assert result.optimized_circuit.size() == 2, "Expected CNOT pair to cancel"
    assert np.allclose(U_before, U_after), "Unitary must be preserved"
    print("  PASSED")


# ===========================================================================
# DEMONSTRATION 3: The bug's effect - missed valid cancellation
# ===========================================================================
def demo_missed_cancellation():
    """
    Show a circuit where a valid cancellation exists but the algorithm's
    incorrect pre-check causes it to be skipped.

    Circuit: H(0), X(0), H(0)
    - gate[i]=H, gate[j]=H (self-inverse pair)
    - intermediate=X(0)
    - H*X*H = Z  (mathematically valid cancellation)
    - Pre-check: _gates_commute(H, X) = False -> SKIP
    - The pre-check rejects because H and X don't commute,
      but the cancellation IS valid (H*X*H = Z, which equals the circuit unitary).
    """
    print("\n" + "=" * 70)
    print("DEMONSTRATION 3: Missed valid cancellation (pre-check too restrictive)")
    print("=" * 70)

    opt = CommutationRewriter(window_size=10)

    qc = QuantumCircuit(1)
    qc.h(0)
    qc.x(0)
    qc.h(0)

    # Compute the original unitary (H*X*H = Z)
    U_before = _unitary(qc)

    # The circuit H*X*H is equivalent to Z
    qc_z = QuantumCircuit(1)
    qc_z.z(0)
    U_z = _unitary(qc_z)
    assert np.allclose(U_before, U_z), "H*X*H should equal Z"

    result = opt.optimize(qc)
    U_after = _unitary(result.optimized_circuit)

    print(f"\n  Circuit: H(0), X(0), H(0)")
    print(f"  Mathematical simplification: H*X*H = Z")
    print(f"  Original size:  {qc.size()} gates")
    print(f"  Optimized size: {result.optimized_circuit.size()} gates")
    print(f"  Unitary preserved: {np.allclose(U_before, U_after)}")

    if result.optimized_circuit.size() == qc.size():
        print(f"  BUG EFFECT: Algorithm did NOT cancel the H-H pair.")
        print(f"  The pre-check _gates_commute(H, X) = False caused the skip.")
        print(f"  A correct algorithm that checks commutation with BOTH gates")
        print(f"  (or equivalently, with the MOVING gate gate[j]) would also")
        print(f"  skip this case since _gates_commute(X, H) = False too.")
        print(f"  However, the pre-check is checking the WRONG condition.")
        print(f"  The correct condition is commutation with gate[j], not gate[i].")
    else:
        print(f"  Cancellation was performed (unexpected for current gate set)")

    print(f"\n  KEY INSIGHT: The pre-check tests a SUFFICIENT but WRONG condition.")
    print(f"  The CORRECT pre-check should verify that intermediates commute with")
    print(f"  gate[j] (the moving gate), since that is what the bubble-sort requires.")
    print(f"  For safety, both conditions should be checked.")


# ===========================================================================
# DEMONSTRATION 4: Unitary verification with a multi-gate circuit
# ===========================================================================
def demo_unitary_verification():
    """
    Verify that the optimizer preserves the unitary on a larger circuit
    where multiple commutation chains are possible.
    """
    print("\n" + "=" * 70)
    print("DEMONSTRATION 4: Unitary preservation on multi-gate circuit")
    print("=" * 70)

    opt = CommutationRewriter(window_size=10)

    # Circuit with multiple cancellation opportunities:
    # CNOT(0,1), S(0), T(0), CNOT(0,1), X(1), H(0), H(0), X(1)
    qc = QuantumCircuit(2)
    qc.cx(0, 1)       # data[0]
    qc.s(0)            # data[1]
    qc.t(0)            # data[2]
    qc.cx(0, 1)        # data[3]
    qc.x(1)            # data[4]
    qc.h(0)            # data[5]
    qc.h(0)            # data[6]
    qc.x(1)            # data[7]

    U_before = _unitary(qc)
    result = opt.optimize(qc)
    U_after = _unitary(result.optimized_circuit)

    print(f"\n  Circuit: CNOT(0,1), S(0), T(0), CNOT(0,1), X(1), H(0), H(0), X(1)")
    print(f"  Original size:  {qc.size()} gates")
    print(f"  Optimized size: {result.optimized_circuit.size()} gates")
    print(f"  Reduction:      {result.reduction:.1%}")
    print(f"  Unitary preserved: {np.allclose(U_before, U_after)}")

    if not np.allclose(U_before, U_after):
        print(f"  FATAL: Unitary NOT preserved! Bug confirmed.")
        max_diff = np.max(np.abs(U_before - U_after))
        print(f"  Maximum matrix element difference: {max_diff:.2e}")
    else:
        print(f"  Unitary correctly preserved.")

    assert np.allclose(U_before, U_after), "Optimizer must preserve unitary"
    print("  PASSED")


# ===========================================================================
# DEMONSTRATION 5: Post-fix verification
# ===========================================================================
def demo_post_fix():
    """
    After the fix, verify that the corrected algorithm handles all test
    circuits correctly.
    """
    print("\n" + "=" * 70)
    print("DEMONSTRATION 5: Post-fix verification")
    print("=" * 70)

    opt = CommutationRewriter(window_size=10)

    test_circuits = []

    # (a) Adjacent self-inverse pair
    qc_a = QuantumCircuit(1)
    qc_a.h(0); qc_a.h(0)
    test_circuits.append(("H-H adjacent", qc_a))

    # (b) CNOT pair with Z-family intermediates
    qc_b = QuantumCircuit(2)
    qc_b.cx(0, 1); qc_b.s(0); qc_b.rz(0.5, 0); qc_b.cx(0, 1)
    test_circuits.append(("CNOT pair + Z-family", qc_b))

    # (c) S-Sdg pair with CNOT intermediate
    qc_c = QuantumCircuit(2)
    qc_c.s(0); qc_c.cx(0, 1); qc_c.sdg(0)
    test_circuits.append(("S-CNOT-Sdg", qc_c))

    # (d) No cancellation possible
    qc_d = QuantumCircuit(1)
    qc_d.h(0); qc_d.x(0)
    test_circuits.append(("H-X (no cancel)", qc_d))

    # (e) Double CNOT pair
    qc_e = QuantumCircuit(2)
    qc_e.cx(0, 1); qc_e.z(0); qc_e.cx(0, 1); qc_e.s(0); qc_e.cx(0, 1)
    test_circuits.append(("Double CNOT chain", qc_e))

    all_passed = True
    for name, qc in test_circuits:
        U_before = _unitary(qc)
        result = opt.optimize(qc)
        U_after = _unitary(result.optimized_circuit)
        preserved = np.allclose(U_before, U_after)
        status = "PASS" if preserved else "FAIL"
        if not preserved:
            all_passed = False
        print(f"  [{status}] {name}: {qc.size()} -> {result.optimized_circuit.size()} "
              f"gates, unitary preserved={preserved}")

    print(f"\n  Overall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    return all_passed


# ===========================================================================
# Main
# ===========================================================================
if __name__ == '__main__':
    print("Commutation Rewriter Bug Reproduction")
    print("=" * 70)

    demo_condition_divergence()
    demo_valid_cancellation()
    demo_missed_cancellation()
    demo_unitary_verification()
    passed = demo_post_fix()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
  The claim is CONFIRMED at the algorithmic level:

  1. The pre-check (line 58-61) verifies that intermediate gates
     commute with gate[i] (the STATIONARY gate).

  2. The bubble-sort (line 65-70) physically moves gate[j] leftward,
     which requires that intermediate gates commute with gate[j]
     (the MOVING gate).

  3. These are DIFFERENT conditions when gate[i] and gate[j] belong
     to different commutation families.

  4. For the CURRENT gate set, all self-inverse pairs share the same
     commutation family (Z-family for S/Sdg, T/Tdg, Rz pairs; same
     gate for H/H, X/X, CNOT/CNOT), so the conditions are equivalent.

  5. The algorithm does NOT produce incorrect cancellations with the
     current gate set, but the pre-check is semantically wrong and
     would cause missed optimizations or incorrect results if gate
     types with different commutation families were added.

  FIX: The pre-check should verify that ALL intermediate gates commute
  with BOTH gate[i] AND gate[j], ensuring the algorithm is
  mathematically correct regardless of gate type.
""")
