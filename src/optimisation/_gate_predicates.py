"""
Shared Gate Predicate Functions
================================
Stateless, O(1) predicate functions for quantum gate analysis.

These predicates are used by both ``BaseOptimizer`` (in ``base.py``) and
``CeilingAwareOptimizer`` (in ``ceiling_aware.py``) to avoid duplicating
the same gate-level structural checks in multiple locations.

All functions accept a ``QuantumCircuit`` and one or two
``CircuitInstruction`` objects and return a boolean.

NOTE: The commutation rules implemented here are SUFFICIENT but not NECESSARY.
Some valid commutation relations may be missing (e.g., SWAP gate partial commutation,
parameterized gate special angles). This may cause the optimizer to miss some
optimization opportunities. See manuscript Section 4.1.5 for theoretical discussion.

Complexity: every predicate is O(a) = O(1) per call -- a constant number of
``circuit.find_bit`` dict lookups plus set/list comparisons over at most
``a`` qubits, where a <= 2 is the max gate arity in the supported gate
sets.  No predicate allocates or simulates unitary matrices, which is why
the ceiling-aware proxies built on them are strict O(m) / O(m * w) scans.

Version: 1.0.0
"""

from __future__ import annotations

from qiskit import QuantumCircuit

from .base import _SELF_INVERSE_GATES
from .constants import DEFAULT_PRECISION


# ---------------------------------------------------------------------------
# Qubit-index helpers
# ---------------------------------------------------------------------------

def qubit_indices(circuit: QuantumCircuit, inst) -> list[int]:
    """Return the list of qubit indices an instruction acts on.

    Returns an empty list if the indices cannot be determined.
    """
    try:
        return [circuit.find_bit(q).index for q in inst.qubits]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Self-inverse / cancellation predicates
# ---------------------------------------------------------------------------

def is_self_inverse_pair(circuit: QuantumCircuit, inst1, inst2) -> bool:
    """Check if two instructions form a self-inverse (cancellable) pair.

    A pair is cancellable when:
    - Both instructions act on the same qubits, AND one of:
      (a) Both are the same self-inverse gate (H, X, Y, Z, CX, CZ, SWAP).
      (b) One is T and the other is Tdg (or vice versa).
      (c) One is S and the other is Sdg (or vice versa).
      (d) Both are same-axis rotation gates whose angles sum to ~0.

    This is the canonical predicate shared between ``BaseOptimizer``
    and the ceiling-aware action-space proxy.
    """
    q1 = qubit_indices(circuit, inst1)
    q2 = qubit_indices(circuit, inst2)
    if q1 != q2:
        return False

    n1 = inst1.operation.name
    n2 = inst2.operation.name

    # (a) Self-inverse gates: same gate cancels
    if n1 == n2 and n1 in _SELF_INVERSE_GATES:
        return True

    # (b) T-Tdg pair
    if (n1 == 't' and n2 == 'tdg') or (n1 == 'tdg' and n2 == 't'):
        return True

    # (c) S-Sdg pair
    if (n1 == 's' and n2 == 'sdg') or (n1 == 'sdg' and n2 == 's'):
        return True

    # (d) Rotation gates with inverse angles
    if n1 == n2 and n1 in ('rx', 'ry', 'rz'):
        p1 = inst1.operation.params
        p2 = inst2.operation.params
        if p1 and p2:
            try:
                angle_sum = float(p1[0]) + float(p2[0])
                # Scale tolerance by the larger angle magnitude to avoid
                # false negatives for large rotations (absolute tolerance
                # would under-count).
                scale = max(1.0, abs(float(p1[0])), abs(float(p2[0])))
                return abs(angle_sum) <= DEFAULT_PRECISION * scale
            except Exception:
                return False

    return False


# ---------------------------------------------------------------------------
# Mergeable-rotation predicate
# ---------------------------------------------------------------------------

def is_mergeable_rotation(circuit: QuantumCircuit, inst1, inst2) -> bool:
    """Check if two adjacent instructions are same-axis rotations on the same qubit.

    Two consecutive same-axis rotations (rx, ry, rz) on the same qubit(s)
    can be merged into a single rotation whose angle is the sum of the two.
    """
    q1 = qubit_indices(circuit, inst1)
    q2 = qubit_indices(circuit, inst2)
    if q1 != q2:
        return False
    n1 = inst1.operation.name
    n2 = inst2.operation.name
    return n1 == n2 and n1 in ('rx', 'ry', 'rz')


# ---------------------------------------------------------------------------
# Commutation predicate (sufficient-conditions only, no numeric fallback)
# ---------------------------------------------------------------------------

# Z-family gates: all mutually commute on the same qubit.
_Z_FAMILY = frozenset({'z', 'rz', 's', 'sdg', 't', 'tdg'})

# X-family gates: commute with CNOT on the target qubit (CNOT conjugates
# X -> X on target; RX is a linear combination of I and X, so also commutes).
_X_FAMILY = frozenset({'x', 'rx'})


def gates_commute(circuit: QuantumCircuit, inst1, inst2) -> bool:
    """Check if two gate instructions commute (sufficient conditions only).

    Conservative: returns True only for proven commuting cases; may return
    False for actually-commuting gate pairs that are not covered by the
    rule set below. This matches the deterministic rule-based behaviour
    used in the ceiling-aware proxy.

    Sufficient conditions checked:
    1. Gates act on disjoint qubit sets.
    2. Both are the same single-qubit gate on the same qubit.
    3. Both are same-axis rotation gates on the same qubit.
    4. Both are in the Z-family on the same qubit.
    5. CNOT commutes with Z-family rotations on its control qubit.
    6. CNOT commutes with X-family rotations on its target qubit.
    7. CZ commutes with Z-family rotations on either of its qubits.
    """
    q1_set = set(qubit_indices(circuit, inst1))
    q2_set = set(qubit_indices(circuit, inst2))

    # 1. Disjoint qubits always commute
    if q1_set and q2_set and len(q1_set & q2_set) == 0:
        return True

    n1 = inst1.operation.name
    n2 = inst2.operation.name
    q1 = qubit_indices(circuit, inst1)
    q2 = qubit_indices(circuit, inst2)

    # 2. Same single-qubit gate on same qubit
    if n1 == n2 and q1 == q2 and len(q1) == 1:
        return True

    # 3. Same-axis rotations commute
    if n1 == n2 and q1 == q2 and n1 in ('rz', 'rx', 'ry'):
        return True

    # 4. Z-family commutation
    if n1 in _Z_FAMILY and n2 in _Z_FAMILY and q1 == q2:
        return True

    # 5. CNOT commutes with Z-rotation on control qubit
    if n1 == 'cx' and n2 in _Z_FAMILY and len(q2) == 1 and q2[0] == q1[0]:
        return True
    if n2 == 'cx' and n1 in _Z_FAMILY and len(q1) == 1 and q1[0] == q2[0]:
        return True

    # 6. CNOT commutes with X-family rotations on target qubit
    #    (CNOT conjugates X -> X on target; RX = cos(a/2)I - i sin(a/2)X
    #    is a linear combination of I and X, so also commutes.)
    if n1 == 'cx' and n2 in _X_FAMILY and len(q2) == 1 and len(q1) == 2 and q2[0] == q1[1]:
        return True
    if n2 == 'cx' and n1 in _X_FAMILY and len(q1) == 1 and len(q2) == 2 and q1[0] == q2[1]:
        return True

    # 7. CZ commutes with Z-family rotations on either of its qubits
    #    (CZ is symmetric; both qubits behave as "controls".)
    if n1 == 'cz' and n2 in _Z_FAMILY and len(q2) == 1 and len(q1) == 2 and q2[0] in q1:
        return True
    if n2 == 'cz' and n1 in _Z_FAMILY and len(q1) == 1 and len(q2) == 2 and q1[0] in q2:
        return True

    # 8. Two SWAP gates on the same qubit pair commute (bug #11 sync with base.py)
    if n1 == 'swap' and n2 == 'swap' and len(q1) == 2 and len(q2) == 2:
        if set(q1) == set(q2):
            return True

    # 9. Two CZ gates on the same qubit pair commute (bug #11 sync with base.py)
    #    CZ is diagonal; diagonal operators always commute.
    if n1 == 'cz' and n2 == 'cz' and len(q1) == 2 and len(q2) == 2:
        if set(q1) == set(q2):
            return True

    return False
