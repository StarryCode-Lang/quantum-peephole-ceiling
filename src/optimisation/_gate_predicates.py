"""
Shared Gate Predicate Functions
================================
Stateless, O(1) predicate functions for quantum gate analysis.

These predicates are used by both ``BaseOptimizer`` (in ``base.py``) and
``CeilingAwareOptimizer`` (in ``ceiling_aware.py``) to avoid duplicating
the same gate-level structural checks in multiple locations.

All functions accept a ``QuantumCircuit`` and one or two
``CircuitInstruction`` objects and return a boolean.

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

    return False
