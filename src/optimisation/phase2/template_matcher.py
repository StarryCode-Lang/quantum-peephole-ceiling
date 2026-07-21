"""
Phase 2b Optimizer: Template Matching
=====================================
Deterministic template rewrites for Clifford subcircuits.

Version 2.0.0 (E26/v8 full-scale release)
-----------------------------------------
The optimizer exposes two entry points:

  * ``optimize``                 — template + cancellation passes on the
                                   *as-listed* circuit (no reordering).
  * ``optimize_full_pipeline``   — bounded commutation gathering + templates +
                                   cancellations + phase-polynomial merging,
                                   iterated to a fixpoint.

Template library (all identities numerically verified against
``qiskit.quantum_info.Operator`` in ``tests/test_phase2b_template_matcher.py``):

  Conjugation templates (Clifford, <=3 qubits)
    * H-CX-H on control (c < t)  -> H-CX-H with reversed CNOT (3 -> 3,
      enables subsequent HH cancellation; the canonical-ordering guard
      ``control < target`` makes oscillation impossible because the reversed
      CNOT has control > target and can never re-fire the same template)
    * H-CX-H on target           -> CZ                     (3 -> 1)
    * H-CZ-H (either qubit)      -> CX                     (3 -> 1)
    * H-CCX-H on target          -> CCZ                    (3 -> 1)
    * H-MCX-H on target          -> MCZ                    (3 -> 1)
    * H-CCZ-H (any qubit)        -> CCX with swapped roles (3 -> 1)

  Inverse-cancellation closure (exact unitary inverses)
    * self-inverse gates on identical qubits: H, X, Y, Z, CX, CY, CH, CZ,
      SWAP, CCX, CSWAP, MCX (CZ/SWAP/CSWAP/CCZ matched as unordered sets)
    * inverse pairs: S<->Sdg, T<->Tdg, SX<->SXdg
    * parametric inverse pairs: Rx/Ry/Rz/P/U1 with theta1 + theta2 = 0

  Phase-polynomial merging (diagonal 1-qubit gates, computational basis)
    * adjacent {Z, S, Sdg, T, Tdg, P(theta), U1(theta)} on one qubit are
      merged by angle addition mod 2*pi and re-emitted canonically
      (0 -> removed, pi -> Z, pi/2 -> S, 3pi/2 -> Sdg, pi/4 -> T,
      7pi/4 -> Tdg, otherwise P(theta))
    * adjacent same-axis rotations Rx/Ry/Rz(theta1)+Rx/Ry/Rz(theta2) are
      merged; a zero total angle removes the pair
    * P-type and Rz-type gates are *not* cross-merged (they differ by a
      global phase); this keeps every rewrite exact under ``Operator``
      equality, not just up to phase.

  Commutation gathering (full pipeline only)
    * H gates are bubbled next to a partner controlled gate across gates on
      disjoint qubits (always a valid commutation), exposing H-CX-H / H-CZ-H
      sandwiches (Stage B-1 of the Theorem 9 proof).
    * inverse / mergeable pairs (CX, CZ, CCX, diagonal 1-qubit gates, ...)
      are gathered across intermediate gates that provably commute with the
      moving gate.  The local commutation predicate extends the conservative
      rule-based :meth:`BaseOptimizer._gates_commute` with the fact that any
      two gates diagonal in the computational basis mutually commute
      (Z-family rotations, CZ, CCZ).  This realizes a restricted
      phase-polynomial optimization over singleton Z-rotations and CZ/CCZ
      gadgets; full parity-gadget phase-polynomial optimization
      (Amy--Mosca style) is out of scope and documented as a limitation.

Termination: every pass either strictly reduces the gate count or performs a
guard-protected reversal that can fire at most once per CNOT, so the outer
loop terminates; ``max_iterations`` is a backstop only.
"""

from __future__ import annotations

import copy
import time

import numpy as np

from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction
from qiskit.circuit.library import CXGate, HGate, CZGate, CCXGate, ZGate

from ..base import BaseOptimizer, OptimizationResult
from ..constants import DEFAULT_PRECISION


# Gates that are their own inverse (U^2 = I).  Matched by name + qubits.
_SELF_INVERSE_GATES = frozenset({
    'h', 'x', 'y', 'z', 'cx', 'cy', 'ch', 'cz', 'swap', 'ccx', 'cswap', 'mcx',
})

# Gates symmetric under qubit exchange: matched as unordered qubit sets.
_SYMMETRIC_GATES = frozenset({'cz', 'swap', 'cswap', 'ccz'})

# Named inverse pairs (either order).
_INVERSE_NAME_PAIRS = frozenset({
    frozenset({'s', 'sdg'}),
    frozenset({'t', 'tdg'}),
    frozenset({'sx', 'sxdg'}),
})

# Parametric gates that cancel with a negated angle on the same qubit.
_PARAMETRIC_INVERSE_GATES = frozenset({'rx', 'ry', 'rz', 'p', 'u1'})

# Diagonal 1-qubit "P-type" gates: U = diag(1, exp(i*theta)).  Merged by
# angle addition.  (Rz differs from these by a global phase and is merged
# only with itself; see module docstring.)
_P_TYPE_ANGLES = {
    'z': np.pi,
    's': np.pi / 2,
    'sdg': -np.pi / 2,
    't': np.pi / 4,
    'tdg': -np.pi / 4,
}
_P_TYPE_PARAM_GATES = frozenset({'p', 'u1'})
_ROTATION_GATES = frozenset({'rx', 'ry', 'rz'})

# Gates diagonal in the computational basis: any two mutually commute.
# Used by the gathering pass (phase-polynomial exposure).
_DIAGONAL_GATE_NAMES = frozenset({
    'z', 's', 'sdg', 't', 'tdg', 'rz', 'p', 'u1', 'cz', 'ccz',
})

# Controlled-X gates that support the H-sandwich -> controlled-Z template.
_CONTROLLED_X_GATES = frozenset({'cx', 'ccx', 'mcx'})
# Controlled-Z gates that support the H-sandwich -> controlled-X template.
_CONTROLLED_Z_GATES = frozenset({'cz', 'ccz'})

_TWO_PI = 2.0 * np.pi


class Phase2bTemplateMatcher(BaseOptimizer):
    """Apply local unitary-preserving Phase-2b templates.

    Parameters
    ----------
    max_iterations : int
        Backstop bound on outer fixpoint iterations (termination is
        guaranteed structurally well before this bound; see module docs).
    fidelity_threshold, success_reduction : float
        Forwarded to :class:`BaseOptimizer`.
    gather_window : int
        Look-ahead window (in listing positions) used by the commutation
        gathering pass of :meth:`optimize_full_pipeline`.  Must exceed the
        largest H-CX-H separation intended to be exposed (for the BV oracle
        family at n data qubits the separation is <= 2n + k + 4, so the
        default of 64 covers n <= 30).
    """

    VERSION = '2.0.0'

    def __init__(self, max_iterations: int = 100, fidelity_threshold: float = 0.99,
                 success_reduction: float = 0.20, gather_window: int = 64):
        super().__init__(fidelity_threshold, success_reduction)
        self.max_iterations = max_iterations
        self.gather_window = gather_window

    # --------------------------------------------------------------------
    # Public entry points
    # --------------------------------------------------------------------

    def optimize(self, circuit: QuantumCircuit, target: QuantumCircuit | None = None) -> OptimizationResult:
        """Template + cancellation passes on the as-listed circuit.

        No commutation reordering is performed: patterns fire only where the
        listing already presents them adjacently.  For circuits where the
        relevant gates live in separate layers (e.g. the BV oracle), use
        :meth:`optimize_full_pipeline` instead.
        """
        start_time = time.time()
        original = circuit
        optimized = copy.deepcopy(circuit)
        counters = self._zero_counters()

        for _ in range(self.max_iterations):
            iter_counts = self._zero_counters()
            self._apply_all_templates(optimized, iter_counts)
            self._cancel_inverse_pairs(optimized, iter_counts)
            self._merge_phase_gates(optimized, iter_counts)
            self._accumulate(counters, iter_counts)
            if self._no_progress(iter_counts):
                break

        runtime = time.time() - start_time
        fidelity = 1.0 if target is None else self.calculate_fidelity(optimized, target)
        reduction = 1.0 - optimized.size() / original.size() if original.size() > 0 else 0.0

        metadata = self._metadata_from_counters(
            counters, algorithm='phase2b_template_matcher', pipeline='single_pass')
        return OptimizationResult(
            optimized_circuit=optimized,
            original_size=original.size(),
            optimized_size=optimized.size(),
            fidelity=fidelity,
            iterations=self._total_actions(counters),
            runtime_seconds=runtime,
            success=self._is_success(reduction, fidelity),
            metadata=metadata,
        )

    def optimize_full_pipeline(self, circuit: QuantumCircuit,
                                target: QuantumCircuit | None = None) -> OptimizationResult:
        """Full Phase-2b pipeline: gathering + templates + cancellations.

        Per outer iteration:

          1. **Commutation gathering** — bubble H gates next to a partner
             controlled gate across disjoint-qubit intermediates (Stage B-1
             of the Thm 9 proof), and gather inverse/mergeable pairs across
             provably commuting intermediates.
          2. **Template application** — fire every adjacent conjugation
             template (Stage B-2).
          3. **Inverse cancellation + phase merging** — remove adjacent
             inverse pairs and merge adjacent diagonal gates (Stage B-3).
          4. Repeat until an iteration performs no rewrite and no
             gate-count reduction.
        """
        start_time = time.time()
        original = circuit
        optimized = copy.deepcopy(circuit)
        counters = self._zero_counters()

        for _ in range(self.max_iterations):
            iter_counts = self._zero_counters()
            self._gather_h_sandwiches(optimized, iter_counts)
            self._gather_commuting_pairs(optimized, iter_counts)
            self._apply_all_templates(optimized, iter_counts)
            self._cancel_inverse_pairs(optimized, iter_counts)
            self._merge_phase_gates(optimized, iter_counts)
            self._accumulate(counters, iter_counts)
            # Gathering alone is not progress: it only reorders.  Continue
            # only if a rewrite or a reduction happened this iteration.
            if self._no_progress(iter_counts):
                break

        runtime = time.time() - start_time
        fidelity = 1.0 if target is None else self.calculate_fidelity(optimized, target)
        reduction = 1.0 - optimized.size() / original.size() if original.size() > 0 else 0.0

        metadata = self._metadata_from_counters(
            counters, algorithm='phase2b_template_matcher_full_pipeline', pipeline='full')
        metadata['theorem_target'] = 'Thm 9 (BV oracle)'
        return OptimizationResult(
            optimized_circuit=optimized,
            original_size=original.size(),
            optimized_size=optimized.size(),
            fidelity=fidelity,
            iterations=self._total_actions(counters),
            runtime_seconds=runtime,
            success=self._is_success(reduction, fidelity),
            metadata=metadata,
        )

    # --------------------------------------------------------------------
    # Counters / metadata helpers
    # --------------------------------------------------------------------

    @staticmethod
    def _zero_counters() -> dict[str, int]:
        return {
            'template_rewrites': 0,   # H-CX-H control reversals (3 -> 3)
            'cz_conversions': 0,      # H-CX-H -> CZ and H-CZ-H -> CX (3 -> 1)
            'mcz_conversions': 0,     # H-CCX/MCX-H -> CCZ/MCZ, H-CCZ-H -> CCX
            'hh_cancellations': 0,
            'local_cancellations': 0,  # all non-HH inverse cancellations
            'phase_merges': 0,
            'h_reorders': 0,          # H bubbles performed by gathering
            'pair_gathers': 0,        # non-H pairs gathered across commutations
        }

    @staticmethod
    def _accumulate(total: dict[str, int], delta: dict[str, int]) -> None:
        for key in total:
            total[key] += delta[key]

    @staticmethod
    def _no_progress(counts: dict[str, int]) -> bool:
        return (counts['template_rewrites'] == 0
                and counts['cz_conversions'] == 0
                and counts['mcz_conversions'] == 0
                and counts['hh_cancellations'] == 0
                and counts['local_cancellations'] == 0
                and counts['phase_merges'] == 0)

    @staticmethod
    def _total_actions(counts: dict[str, int]) -> int:
        return sum(counts.values())

    def _metadata_from_counters(self, counts: dict[str, int], algorithm: str,
                                pipeline: str) -> dict:
        return {
            'algorithm': algorithm,
            'template_rewrites': counts['template_rewrites'],
            'cz_conversions': counts['cz_conversions'],
            'mcz_conversions': counts['mcz_conversions'],
            'hh_cancellations': counts['hh_cancellations'],
            'local_cancellations': counts['local_cancellations'],
            'phase_merges': counts['phase_merges'],
            'h_reorders': counts['h_reorders'],
            'pair_gathers': counts['pair_gathers'],
            'pipeline': pipeline,
            'version': self.VERSION,
            'template_library': {
                'conjugation_templates': 6,
                'self_inverse_gates': sorted(_SELF_INVERSE_GATES),
                'inverse_pairs': sorted([sorted(p) for p in _INVERSE_NAME_PAIRS]),
                'parametric_inverse_gates': sorted(_PARAMETRIC_INVERSE_GATES),
                'phase_merge_gates': sorted(list(_P_TYPE_ANGLES)) + sorted(_P_TYPE_PARAM_GATES),
                'rotation_merge_gates': sorted(_ROTATION_GATES),
            },
        }

    # --------------------------------------------------------------------
    # Template application
    # --------------------------------------------------------------------

    def _apply_all_templates(self, circuit: QuantumCircuit, counts: dict[str, int]) -> None:
        """Scan left-to-right and fire every adjacent conjugation template.

        After a successful rewrite the scan backs up two positions so that
        patterns spanning the rewritten site are reconsidered.  Termination
        is guaranteed: 3->1 rewrites strictly shrink the circuit, and the
        3->3 CNOT reversal is guard-protected (it fires only when
        control < target; the reversed CNOT has control > target and can
        never re-fire within or across scans).
        """
        i = 0
        while i <= len(circuit.data) - 3:
            first, middle, last = circuit.data[i], circuit.data[i + 1], circuit.data[i + 2]
            fired = False

            if first.operation.name == 'h' and last.operation.name == 'h':
                first_q = self._get_qubit_indices(circuit, first)
                last_q = self._get_qubit_indices(circuit, last)
                if len(first_q) == 1 and first_q == last_q:
                    fired = self._try_h_sandwich(circuit, i, middle, first_q[0], counts)

            if fired:
                i = max(0, i - 2)
            else:
                i += 1

    def _try_h_sandwich(self, circuit: QuantumCircuit, index: int, middle,
                        h_qubit: int, counts: dict[str, int]) -> bool:
        """Try to fire an H-sandwich template at ``index``.

        ``middle`` is a controlled gate; ``h_qubit`` carries the flanking H
        gates at ``index`` and ``index + 2``.  Returns True if a rewrite
        fired.
        """
        name = middle.operation.name
        mid_q = self._get_qubit_indices(circuit, middle)

        if name in _CONTROLLED_X_GATES and len(mid_q) >= 2:
            controls, target = mid_q[:-1], mid_q[-1]
            if h_qubit == target:
                # H-CX-H on target -> controlled-Z (3 -> 1).
                self._replace_hxh_with_controlled_z(circuit, index, controls, target)
                key = 'cz_conversions' if name == 'cx' else 'mcz_conversions'
                counts[key] += 1
                return True
            if h_qubit in controls and name == 'cx' and mid_q[0] < mid_q[1]:
                # H-CX-H on control with control < target -> reversed CNOT
                # (3 -> 3; canonical guard prevents oscillation).
                control, tgt = mid_q[0], mid_q[1]
                self._replace_with_reversed_h_cx_h(circuit, index, control, tgt)
                counts['template_rewrites'] += 1
                return True
            return False

        if name in _CONTROLLED_Z_GATES and len(mid_q) >= 2 and h_qubit in mid_q:
            # H-CZ-H (or H-CCZ-H) on any one qubit -> controlled-X with that
            # qubit as target and the remaining qubits as controls (3 -> 1).
            target = h_qubit
            controls = [q for q in mid_q if q != h_qubit]
            self._replace_hzh_with_controlled_x(circuit, index, controls, target)
            key = 'cz_conversions' if name == 'cz' else 'mcz_conversions'
            counts[key] += 1
            return True

        return False

    # --------------------------------------------------------------------
    # Inverse-pair cancellation
    # --------------------------------------------------------------------

    def _cancel_inverse_pairs(self, circuit: QuantumCircuit, counts: dict[str, int]) -> None:
        """Remove every adjacent inverse pair (generalized closure)."""
        i = 0
        while i < len(circuit.data) - 1:
            category = self._inverse_pair_category(circuit, circuit.data[i], circuit.data[i + 1])
            if category is not None:
                circuit.data.pop(i)
                circuit.data.pop(i)
                if category == 'hh':
                    counts['hh_cancellations'] += 1
                else:
                    counts['local_cancellations'] += 1
                if i > 0:
                    i -= 1
            else:
                i += 1

    def _inverse_pair_category(self, circuit: QuantumCircuit, first, second) -> str | None:
        """Classify an adjacent pair as cancellable; None if not."""
        name1, name2 = first.operation.name, second.operation.name
        qubits1 = self._get_qubit_indices(circuit, first)
        qubits2 = self._get_qubit_indices(circuit, second)
        if not qubits1 or not qubits2:
            return None

        # Self-inverse gates on identical qubits (unordered for symmetric gates).
        if name1 == name2 and name1 in _SELF_INVERSE_GATES:
            if name1 in _SYMMETRIC_GATES:
                if set(qubits1) == set(qubits2) and len(qubits1) == len(qubits2):
                    return 'hh' if name1 == 'h' else 'self_inverse'
            elif qubits1 == qubits2 and self._params_equal(first, second):
                return 'hh' if name1 == 'h' else 'self_inverse'

        # Named inverse pairs (S/Sdg, T/Tdg, SX/SXdg) on identical qubits.
        if frozenset({name1, name2}) in _INVERSE_NAME_PAIRS and qubits1 == qubits2:
            return 'inverse_pair'

        # Parametric inverse pairs: theta1 + theta2 = 0 on identical qubits.
        if name1 == name2 and name1 in _PARAMETRIC_INVERSE_GATES and qubits1 == qubits2:
            angles = self._numeric_params(first, second)
            if angles is not None and abs(angles[0] + angles[1]) <= DEFAULT_PRECISION:
                return 'rotation_inverse'

        return None

    # --------------------------------------------------------------------
    # Phase-polynomial merging
    # --------------------------------------------------------------------

    def _merge_phase_gates(self, circuit: QuantumCircuit, counts: dict[str, int]) -> None:
        """Merge adjacent diagonal / same-axis-rotation gates on one qubit."""
        i = 0
        while i < len(circuit.data) - 1:
            first, second = circuit.data[i], circuit.data[i + 1]
            merged_angle = self._mergeable_angle(circuit, first, second)
            if merged_angle is None:
                i += 1
                continue
            counts['phase_merges'] += 1
            circuit.data.pop(i)
            circuit.data.pop(i)
            self._emit_phase_gate(circuit, i, merged_angle, first, second)
            if i > 0:
                i -= 1

    def _mergeable_angle(self, circuit: QuantumCircuit, first, second) -> float | None:
        """Return the merged angle for an adjacent mergeable pair, else None.

        Two merge families are supported (never mixed, to keep rewrites
        exact up to the *same* matrix, not just up to global phase):

          * P-type: {Z, S, Sdg, T, Tdg, P, U1} — angle sum mod 2*pi.
          * Rz/Rx/Ry same-name rotations — angle sum (not reduced mod 2*pi
            here; the emitter canonicalizes).
        """
        name1, name2 = first.operation.name, second.operation.name
        qubits1 = self._get_qubit_indices(circuit, first)
        qubits2 = self._get_qubit_indices(circuit, second)
        if len(qubits1) != 1 or qubits1 != qubits2:
            return None

        def p_angle(inst) -> float | None:
            name = inst.operation.name
            if name in _P_TYPE_ANGLES:
                return float(_P_TYPE_ANGLES[name])
            if name in _P_TYPE_PARAM_GATES:
                params = inst.operation.params
                if len(params) == 1 and isinstance(params[0], (int, float, np.floating)):
                    return float(params[0])
            return None

        a1, a2 = p_angle(first), p_angle(second)
        if a1 is not None and a2 is not None:
            return (a1 + a2) % _TWO_PI

        if name1 == name2 and name1 in _ROTATION_GATES:
            angles = self._numeric_params(first, second)
            if angles is not None:
                return angles[0] + angles[1]

        return None

    def _emit_phase_gate(self, circuit: QuantumCircuit, index: int, angle: float,
                         first, second) -> None:
        """Emit the canonical gate for a merged angle (or nothing for 0)."""
        name1 = first.operation.name
        # Rz-family merge: re-emit as Rz (mod 2*pi, drop if ~0).
        if name1 in _ROTATION_GATES:
            theta = angle % _TWO_PI
            if theta > np.pi:
                theta -= _TWO_PI
            if abs(theta) > DEFAULT_PRECISION:
                qubit = self._get_qubit_indices(circuit, first)[0]
                new = QuantumCircuit(1)
                getattr(new, name1)(theta, 0)
                circuit.data.insert(index, CircuitInstruction(
                    new.data[0].operation, (circuit.qubits[qubit],), ()))
            return

        # P-type merge: canonical named gate when possible, else P(theta).
        theta = angle % _TWO_PI
        named = {
            np.pi: 'z',
            np.pi / 2: 's',
            3 * np.pi / 2: 'sdg',
            np.pi / 4: 't',
            7 * np.pi / 4: 'tdg',
        }
        if theta <= DEFAULT_PRECISION or abs(theta - _TWO_PI) <= DEFAULT_PRECISION:
            return  # identity: emit nothing
        qubit = self._get_qubit_indices(circuit, first)[0]
        for ref, gate_name in named.items():
            if abs(theta - ref) <= 1e-9:
                new = QuantumCircuit(1)
                getattr(new, gate_name)(0)
                circuit.data.insert(index, CircuitInstruction(
                    new.data[0].operation, (circuit.qubits[qubit],), ()))
                return
        new = QuantumCircuit(1)
        new.p(theta, 0)
        circuit.data.insert(index, CircuitInstruction(
            new.data[0].operation, (circuit.qubits[qubit],), ()))

    # --------------------------------------------------------------------
    # Commutation gathering (full pipeline only)
    # --------------------------------------------------------------------

    def _gather_h_sandwiches(self, circuit: QuantumCircuit, counts: dict[str, int]) -> None:
        """Bubble H gates next to a partner controlled gate.

        For every controlled gate (CX/CCX/MCX/CZ/CCZ) at position j, try the
        candidate sandwich qubits in priority order — for a controlled-X
        gate the *target* first (its sandwich rewrites 3 -> 1 into a
        controlled-Z) and the *control* second (its sandwich rewrites 3 -> 3
        into the reversed CNOT, enabling later HH cancellations); for a
        symmetric controlled-Z gate both qubits are equivalent.  Gathering
        for a gate stops as soon as one candidate sandwich is complete,
        because the two flanking slots can hold H gates on only one qubit.
        """
        window = self.gather_window
        j = 0
        while j < len(circuit.data):
            inst = circuit.data[j]
            name = inst.operation.name
            if name not in _CONTROLLED_X_GATES and name not in _CONTROLLED_Z_GATES:
                j += 1
                continue
            mid_q = self._get_qubit_indices(circuit, inst)
            if len(mid_q) < 2:
                j += 1
                continue
            # Controlled-X: target (last qubit) has priority over control.
            # Controlled-Z: symmetric; either qubit works.
            candidates = [mid_q[-1], mid_q[0]]
            for q in candidates:
                if self._h_sandwich_complete(circuit, j, q):
                    break  # one completed sandwich per gate is enough
                # Left partner.
                if not self._h_adjacent(circuit, j - 1, q):
                    i = self._find_gatherable_h(circuit, j, q, direction=-1, window=window)
                    if i is not None:
                        # Bubbling the H right to j-1 shifts only the crossed
                        # intermediates; the controlled gate stays at j.
                        counts['h_reorders'] += self._bubble_gate(circuit, i, j - 1)
                # Right partner.
                if not self._h_adjacent(circuit, j + 1, q):
                    k = self._find_gatherable_h(circuit, j, q, direction=+1, window=window)
                    if k is not None:
                        counts['h_reorders'] += self._bubble_gate(circuit, k, j + 1)
                if self._h_sandwich_complete(circuit, j, q):
                    break
            j += 1

    def _h_adjacent(self, circuit: QuantumCircuit, idx: int, q: int) -> bool:
        """Check whether position idx holds an H gate on qubit q."""
        if idx < 0 or idx >= len(circuit.data):
            return False
        inst = circuit.data[idx]
        return inst.operation.name == 'h' and self._get_qubit_indices(circuit, inst) == [q]

    def _h_sandwich_complete(self, circuit: QuantumCircuit, j: int, q: int) -> bool:
        """Check whether gate j is flanked by H gates on qubit q."""
        return (self._h_adjacent(circuit, j - 1, q)
                and self._h_adjacent(circuit, j + 1, q))

    def _find_gatherable_h(self, circuit: QuantumCircuit, j: int, q: int,
                           direction: int, window: int) -> int | None:
        """Find the nearest H on qubit q that can bubble to gate j."""
        if direction < 0:
            # Indices j-1 down to max(0, j-window).  The range stop must be
            # one below the lowest intended index and must never be < -1,
            # otherwise index -1 would wrap around to the last gate.
            rng = range(j - 1, max(-1, j - window - 1), -1)
        else:
            rng = range(j + 1, min(len(circuit.data), j + 1 + window))
        for idx in rng:
            inst = circuit.data[idx]
            qubits = set(self._get_qubit_indices(circuit, inst))
            if inst.operation.name == 'h' and qubits == {q}:
                return idx
            if q in qubits:
                return None  # blocked by a non-H gate on q before any H
        return None

    def _bubble_gate(self, circuit: QuantumCircuit, src: int, dst: int) -> int:
        """Bubble the gate at ``src`` to position ``dst`` across disjoint gates.

        Every swap requires the two swapped gates to act on disjoint qubit
        sets (a provably valid commutation).  Returns the number of swaps
        performed (0 if immediately blocked); a partial bubble is possible
        when an intermediate non-disjoint gate is hit en route.
        """
        # Defensive guard: negative indices would wrap around the listing
        # and silently perform non-adjacent (invalid) swaps.
        if not (0 <= src < len(circuit.data)) or not (0 <= dst < len(circuit.data)):
            return 0
        if src == dst:
            return 0
        step = 1 if dst > src else -1
        moves = 0
        pos = src
        while pos != dst:
            nxt = pos + step
            left, right = (circuit.data[pos], circuit.data[nxt]) if step > 0 \
                else (circuit.data[nxt], circuit.data[pos])
            if not self._gates_on_disjoint_qubits(circuit, left, right):
                break
            circuit.data[pos], circuit.data[nxt] = circuit.data[nxt], circuit.data[pos]
            pos = nxt
            moves += 1
        return moves

    def _gather_commuting_pairs(self, circuit: QuantumCircuit, counts: dict[str, int]) -> None:
        """Gather inverse/mergeable pairs across commuting intermediates.

        For each gate g at i that participates in some cancellation or merge
        rule, search right within ``gather_window`` for a partner; if every
        intermediate gate commutes with the partner (rule-based predicate
        extended with mutual diagonality), bubble the partner left to i+1.
        The subsequent cancellation/merge passes then fire.
        """
        window = self.gather_window
        i = 0
        while i < len(circuit.data) - 1:
            inst = circuit.data[i]
            if not self._is_gatherable_seed(inst):
                i += 1
                continue
            partner = self._find_commuting_partner(circuit, i, window)
            if partner is not None:
                moved = self._bubble_commuting_gate(circuit, partner, i + 1)
                counts['pair_gathers'] += moved
            i += 1

    @staticmethod
    def _is_gatherable_seed(inst) -> bool:
        name = inst.operation.name
        return (name in _SELF_INVERSE_GATES
                or name in _DIAGONAL_GATE_NAMES
                or name in _ROTATION_GATES
                or any(name in pair for pair in _INVERSE_NAME_PAIRS))

    def _find_commuting_partner(self, circuit: QuantumCircuit, i: int,
                                window: int) -> int | None:
        """Find a cancellable/mergeable partner for gate i within window."""
        seed = circuit.data[i]
        limit = min(len(circuit.data), i + 1 + window)
        for j in range(i + 1, limit):
            candidate = circuit.data[j]
            if self._is_partner(circuit, seed, candidate):
                # Verify every intermediate commutes with the candidate.
                if all(self._commutes_for_gather(circuit, circuit.data[k], candidate)
                       for k in range(i + 1, j)):
                    return j
                return None  # nearest partner blocked; do not skip past it
            # A gate on overlapping qubits that does not commute with the
            # seed's potential partner blocks the search conservatively only
            # when it also overlaps the seed qubits.
        return None

    def _is_partner(self, circuit: QuantumCircuit, first, second) -> bool:
        """Check whether two gates cancel or merge (not necessarily adjacent)."""
        if self._inverse_pair_category(circuit, first, second) is not None:
            return True
        return self._mergeable_angle(circuit, first, second) is not None

    def _bubble_commuting_gate(self, circuit: QuantumCircuit, src: int, dst: int) -> int:
        """Bubble gate at ``src`` leftward to ``dst`` across commuting gates."""
        moves = 0
        pos = src
        while pos > dst:
            if not self._commutes_for_gather(circuit, circuit.data[pos - 1], circuit.data[pos]):
                break
            circuit.data[pos - 1], circuit.data[pos] = circuit.data[pos], circuit.data[pos - 1]
            pos -= 1
            moves += 1
        return moves

    def _commutes_for_gather(self, circuit: QuantumCircuit, inst1, inst2) -> bool:
        """Commutation predicate for gathering.

        Extends the conservative rule-based
        :meth:`BaseOptimizer._gates_commute` with mutual diagonality: any two
        gates diagonal in the computational basis commute, regardless of
        qubit overlap (Z-family rotations, P/U1, CZ, CCZ).
        """
        if self._gates_commute(circuit, inst1, inst2):
            return True
        if (inst1.operation.name in _DIAGONAL_GATE_NAMES
                and inst2.operation.name in _DIAGONAL_GATE_NAMES):
            return True
        return False

    # --------------------------------------------------------------------
    # Replacement primitives
    # --------------------------------------------------------------------

    def _replace_with_reversed_h_cx_h(self, circuit: QuantumCircuit, index: int,
                                      control: int, target: int) -> None:
        """H-CX(control,target)-H -> H-CX(target,control)-H (CNOT reversal)."""
        for _ in range(3):
            circuit.data.pop(index)
        replacement = [
            CircuitInstruction(HGate(), (circuit.qubits[target],), ()),
            CircuitInstruction(CXGate(), (circuit.qubits[target], circuit.qubits[control]), ()),
            CircuitInstruction(HGate(), (circuit.qubits[target],), ()),
        ]
        for offset, instruction in enumerate(replacement):
            circuit.data.insert(index + offset, instruction)

    def _replace_hxh_with_controlled_z(self, circuit: QuantumCircuit, index: int,
                                       controls: list[int], target: int) -> None:
        """H_t CX/MCX(controls -> t) H_t -> controlled-Z (3 -> 1)."""
        for _ in range(3):
            circuit.data.pop(index)
        n_controls = len(controls)
        if n_controls == 1:
            gate = CZGate()
        else:
            gate = ZGate().control(n_controls)
        qubits = tuple(circuit.qubits[q] for q in (*controls, target))
        circuit.data.insert(index, CircuitInstruction(gate, qubits, ()))

    def _replace_hzh_with_controlled_x(self, circuit: QuantumCircuit, index: int,
                                       controls: list[int], target: int) -> None:
        """H_t CZ/CCZ(... t) H_t -> controlled-X (3 -> 1)."""
        for _ in range(3):
            circuit.data.pop(index)
        n_controls = len(controls)
        if n_controls == 1:
            gate = CXGate()
        else:
            gate = CCXGate() if n_controls == 2 else CXGate().control(n_controls)
        qubits = tuple(circuit.qubits[q] for q in (*controls, target))
        circuit.data.insert(index, CircuitInstruction(gate, qubits, ()))

    # --------------------------------------------------------------------
    # Small parameter helpers
    # --------------------------------------------------------------------

    @staticmethod
    def _params_equal(first, second) -> bool:
        p1, p2 = first.operation.params, second.operation.params
        if len(p1) != len(p2):
            return False
        for a, b in zip(p1, p2):
            if isinstance(a, (int, float, np.floating)) and isinstance(b, (int, float, np.floating)):
                if abs(float(a) - float(b)) > DEFAULT_PRECISION:
                    return False
            elif a != b:
                return False
        return True

    @staticmethod
    def _numeric_params(first, second) -> tuple[float, float] | None:
        p1, p2 = first.operation.params, second.operation.params
        if len(p1) != 1 or len(p2) != 1:
            return None
        a, b = p1[0], p2[0]
        if not isinstance(a, (int, float, np.floating)) or not isinstance(b, (int, float, np.floating)):
            return None
        return float(a), float(b)

    def _cx_qubits(self, circuit: QuantumCircuit, inst) -> tuple[int, int]:
        """Extract (control, target) qubit indices from a CX instruction."""
        qubits = self._get_qubit_indices(circuit, inst)
        if len(qubits) != 2:
            return (-1, -1)
        return (qubits[0], qubits[1])
