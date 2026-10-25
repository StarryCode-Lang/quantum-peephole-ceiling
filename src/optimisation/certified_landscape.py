"""Core state-space search for the v13 certified rewrite landscape.

This module is intentionally independent of the v12 exposure solver.  It
operates on concrete, normalized gate listings and treats every transition as
a proof-carrying local replacement.  Exact mode is finite-horizon BFS with a
separate barrier traversal; an IDA* escape-depth engine is also provided for
the target predicate ``cost < initial_cost``.  Bounded mode never reports a
local optimum.
"""

from __future__ import annotations

import hashlib
import heapq
import itertools
import json
import math
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


TWO_PI = 2.0 * math.pi
ANGLE_TOLERANCE = 1e-10
SEMANTIC_TOLERANCE = 1e-10
STATUS_EXACT_ESCAPE = "EXACT_ESCAPE"
STATUS_EXACT_LOCAL = "EXACT_H_LOCAL_OPTIMUM"
STATUS_WITNESS_INCOMPLETE = "WITNESS_CERTIFIED_SEARCH_INCOMPLETE"
STATUS_RESOURCE_NO_WITNESS = "RESOURCE_BOUNDED_NO_WITNESS"
STATUS_UNSUPPORTED = "UNSUPPORTED_INPUT"
STATUS_INVALID_RULES = "INVALID_RULE_LIBRARY"
STATUS_SEMANTIC_FAILURE = "SEMANTIC_FAILURE"


class _SearchResourceLimit(RuntimeError):
    """Internal signal for a resource boundary observed during generation."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _check_deadline(deadline: float | None) -> None:
    if deadline is not None and time.perf_counter() >= deadline:
        raise _SearchResourceLimit("time_budget")


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


@lru_cache(maxsize=262144)
def _canonical_gate_bytes(name: str, qubits: tuple[int, ...], angle: float | None) -> bytes:
    payload: dict[str, Any] = {"name": name, "qubits": list(qubits)}
    if angle is not None:
        payload["angle"] = format(normalize_angle(angle), ".17g")
    return _canonical_bytes(payload)


@lru_cache(maxsize=262144)
def _intern_state_gate(name: str, qubits: tuple[int, ...], angle: float | None) -> "StateGate":
    """Reuse immutable gate values across the many local rewrite candidates."""

    return StateGate(name, qubits, angle)


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def normalize_angle(angle: float) -> float:
    value = (float(angle) + math.pi) % TWO_PI - math.pi
    if abs(value) <= ANGLE_TOLERANCE or abs(value + math.pi) <= ANGLE_TOLERANCE:
        return 0.0 if abs(value) <= ANGLE_TOLERANCE else -math.pi
    return float(value)


def angles_equal(left: float, right: float) -> bool:
    return abs(normalize_angle(left - right)) <= ANGLE_TOLERANCE


@dataclass(frozen=True)
class StateGate:
    name: str
    qubits: tuple[int, ...]
    angle: float | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": self.name, "qubits": list(self.qubits)}
        if self.angle is not None:
            payload["angle"] = format(normalize_angle(self.angle), ".17g")
        return payload

    @cached_property
    def _canonical_bytes(self) -> bytes:
        """Cache the canonical fragment used by every containing state."""

        return _canonical_gate_bytes(self.name, self.qubits, self.angle)


@dataclass(frozen=True)
class LandscapeState:
    num_qubits: int
    gates: tuple[StateGate, ...]

    def __post_init__(self) -> None:
        normalized_gates = tuple(
            StateGate(gate.name, tuple(gate.qubits), None if gate.angle is None else normalize_angle(gate.angle))
            for gate in self.gates
        )
        if normalized_gates != self.gates:
            object.__setattr__(self, "gates", normalized_gates)

    def normalized(self) -> "LandscapeState":
        return self

    def to_dict(self) -> dict[str, Any]:
        return {"num_qubits": self.num_qubits, "gates": [gate.to_dict() for gate in self.gates]}

    @cached_property
    def _canonical_state_bytes(self) -> bytes:
        # Keep the exact sort-keys/separators contract of _canonical_bytes,
        # while avoiding a temporary list/dict tree for every child state.
        gates = b",".join(gate._canonical_bytes for gate in self.gates)
        return b'{"gates":[' + gates + b'],"num_qubits":' + str(self.num_qubits).encode() + b"}"

    @cached_property
    def _canonical_gate_spans(self) -> tuple[tuple[int, int], ...]:
        """Return byte spans for each gate in ``_canonical_state_bytes``."""

        cursor = len(b'{"gates":[')
        spans: list[tuple[int, int]] = []
        for index, gate in enumerate(self.gates):
            start = cursor
            cursor += len(gate._canonical_bytes)
            spans.append((start, cursor))
            if index + 1 < len(self.gates):
                cursor += 1
        return tuple(spans)

    @cached_property
    def key(self) -> str:
        return self._canonical_state_bytes.decode()

    @cached_property
    def state_hash(self) -> str:
        return hashlib.sha256(self._canonical_state_bytes).hexdigest()

    @property
    def cost(self) -> int:
        return len(self.gates)

    @property
    def depth(self) -> int:
        ending: dict[int, int] = defaultdict(int)
        for gate in self.gates:
            layer = max((ending[q] for q in gate.qubits), default=0) + 1
            for qubit in gate.qubits:
                ending[qubit] = layer
        return max(ending.values(), default=0)


@dataclass(frozen=True)
class LandscapeAction:
    rule_id: str
    family: str
    location: int
    binding: str
    pre_state_sha256: str
    post_state_sha256: str
    local_proof_hash: str
    post_state: LandscapeState
    cost_delta: int

    @property
    def sort_key(self) -> tuple[Any, ...]:
        return (self.rule_id, self.location, self.binding, self.post_state_sha256)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "family": self.family,
            "location": self.location,
            "binding": json.loads(self.binding),
            "pre_state_sha256": self.pre_state_sha256,
            "post_state_sha256": self.post_state_sha256,
            "local_proof_hash": self.local_proof_hash,
            "cost_delta": self.cost_delta,
        }


def state_from_spec(spec: Mapping[str, Any]) -> LandscapeState:
    gates = []
    for operation in spec["operations"]:
        params = operation.get("params", [])
        gates.append(
            StateGate(
                str(operation["name"]),
                tuple(int(q) for q in operation["qubits"]),
                None if not params else float(params[0]),
            )
        )
    return LandscapeState(int(spec["num_qubits"]), tuple(gates)).normalized()


def _state_from_normalized(num_qubits: int, gates: Iterable[StateGate]) -> LandscapeState:
    """Build an immutable state when all gates are already normalized.

    Rewrite transitions only splice existing normalized gates and normalized
    rule targets.  Avoiding a second full-list normalization pass here keeps
    the public constructor strict while making candidate generation linear in
    the changed listing fragments.
    """

    state = object.__new__(LandscapeState)
    object.__setattr__(state, "num_qubits", int(num_qubits))
    object.__setattr__(state, "gates", tuple(gates))
    return state


def _state_from_splice(
    state: LandscapeState,
    location: int,
    consumed: int,
    replacement: Iterable[StateGate],
) -> LandscapeState:
    """Build a child state while reusing the parent's canonical byte layout."""

    replacement_tuple = tuple(replacement)
    gate_count = len(state.gates)
    if location < 0 or consumed < 1 or location + consumed > gate_count:
        raise ValueError("invalid_state_splice")
    post_gates = (
        state.gates[:location]
        + replacement_tuple
        + state.gates[location + consumed:]
    )
    spans = state._canonical_gate_spans
    first_start = spans[location][0]
    last_end = spans[location + consumed - 1][1]
    has_left = location > 0
    has_right = location + consumed < gate_count
    region_start = first_start - (1 if has_left else 0)
    region_end = last_end + (1 if has_right else 0)
    replacement_bytes = b",".join(gate._canonical_bytes for gate in replacement_tuple)
    if replacement_tuple:
        middle = (
            (b"," if has_left else b"")
            + replacement_bytes
            + (b"," if has_right else b"")
        )
    elif has_left and has_right:
        middle = b","
    else:
        middle = b""
    child = _state_from_normalized(state.num_qubits, post_gates)
    digest = hashlib.sha256(
        state._canonical_state_bytes[:region_start]
        + middle
        + state._canonical_state_bytes[region_end:]
    )
    # Keep the child byte representation lazy.  Duplicate candidates only
    # need this digest; an expanded child reconstructs its own bytes once.
    child.__dict__["state_hash"] = digest.hexdigest()
    return child


def _unitary_gate_matrix(state: LandscapeState, gate: StateGate) -> np.ndarray:
    dimension = 2**state.num_qubits
    result = np.zeros((dimension, dimension), dtype=np.complex128)
    if gate.name == "h":
        for basis in range(dimension):
            bit = (basis >> gate.qubits[0]) & 1
            for output_bit, coefficient in ((0, 1 / math.sqrt(2)), (1, (-1 if bit else 1) / math.sqrt(2))):
                output = (basis & ~(1 << gate.qubits[0])) | (output_bit << gate.qubits[0])
                result[output, basis] = coefficient
    elif gate.name in {"x", "y", "z", "s", "sdg", "t", "tdg", "rx", "ry", "rz"}:
        for basis in range(dimension):
            bit = (basis >> gate.qubits[0]) & 1
            if gate.name == "x":
                result[basis ^ (1 << gate.qubits[0]), basis] = 1
            elif gate.name == "y":
                result[basis ^ (1 << gate.qubits[0]), basis] = 1j if bit == 0 else -1j
            elif gate.name == "z":
                result[basis, basis] = 1 if bit == 0 else -1
            else:
                angle = {
                    "s": math.pi / 2,
                    "sdg": -math.pi / 2,
                    "t": math.pi / 4,
                    "tdg": -math.pi / 4,
                    "rx": gate.angle or 0.0,
                    "ry": gate.angle or 0.0,
                    "rz": gate.angle or 0.0,
                }[gate.name]
                if gate.name == "rz":
                    result[basis, basis] = np.exp((-1j * angle / 2) if bit == 0 else (1j * angle / 2))
                elif gate.name == "rx":
                    result[basis, basis] = math.cos(angle / 2)
                    result[basis ^ (1 << gate.qubits[0]), basis] = -1j * math.sin(angle / 2)
                elif gate.name == "ry":
                    result[basis, basis] = math.cos(angle / 2)
                    result[basis ^ (1 << gate.qubits[0]), basis] = (-1 if bit == 1 else 1) * math.sin(angle / 2)
                else:
                    result[basis, basis] = np.exp(1j * angle * (1 if bit else 0))
    elif gate.name == "cx":
        control, target = gate.qubits
        for basis in range(dimension):
            output = basis ^ (1 << target) if ((basis >> control) & 1) else basis
            result[output, basis] = 1
    elif gate.name == "cz":
        left, right = gate.qubits
        for basis in range(dimension):
            result[basis, basis] = -1 if ((basis >> left) & 1 and (basis >> right) & 1) else 1
    elif gate.name == "swap":
        left, right = gate.qubits
        for basis in range(dimension):
            left_bit, right_bit = (basis >> left) & 1, (basis >> right) & 1
            output = basis
            if left_bit != right_bit:
                output ^= (1 << left) | (1 << right)
            result[output, basis] = 1
    else:
        raise ValueError(f"unsupported_gate:{gate.name}")
    return result


def state_unitary(state: LandscapeState) -> np.ndarray:
    result = np.eye(2**state.num_qubits, dtype=np.complex128)
    for gate in state.gates:
        result = _unitary_gate_matrix(state, gate) @ result
    return result


def semantically_equivalent(left: LandscapeState, right: LandscapeState) -> bool:
    if left.num_qubits != right.num_qubits:
        return False
    left_matrix, right_matrix = state_unitary(left), state_unitary(right)
    dimension = left_matrix.shape[0]
    overlap = abs(np.trace(left_matrix.conj().T @ right_matrix)) / dimension
    return bool(np.isclose(overlap, 1.0, atol=SEMANTIC_TOLERANCE, rtol=0.0))


def state_wcl(state: LandscapeState) -> LandscapeState:
    """Reorder the listing into wire-consecutive listing (WCL) order.

    Mirrors ``WireTraversalPreprocessor.preprocess`` from
    ``src/optimisation/phase1/wire_traversal.py`` on ``LandscapeState`` gate
    tuples, with identical tie-breaking: each gate's primary wire is the
    lowest qubit index it acts on; a dependency DAG adds one deduplicated
    edge between every pair of consecutive gates on each qubit (preserving
    their listing order); and Kahn's algorithm with a min-heap keyed on
    ``(primary_wire, original_index)`` emits the deterministic WCL
    permutation.  Gates sharing a qubit keep their relative order by
    construction, and gates on disjoint qubits commute, so the result is
    unitarily equivalent to the input.

    The function is pure and returns a permutation of the same gate multiset
    (same ``StateGate`` objects, same angles), so the total cost is invariant
    and the output is byte-stable for a given input listing.

    Semantic gaps relative to the Qiskit preprocessor: register structure,
    global phase, classical bits, and non-unitary directives have no
    ``LandscapeState`` counterpart and are absent here; listings of at most
    one gate are returned unchanged, mirroring the preprocessor's
    ``n_gates <= 1`` early return; qubit indices are used as given (the
    Qiskit ``find_bit`` indirection has no analogue); and the cycle fallback
    of the preprocessor is kept for parity although the DAG is acyclic by
    construction (every per-qubit edge points from an earlier to a later
    listing index).
    """

    gate_count = len(state.gates)
    if gate_count <= 1:
        return state
    gate_qubits = [set(gate.qubits) for gate in state.gates]
    qubit_to_gates: dict[int, list[int]] = defaultdict(list)
    for index, qubits in enumerate(gate_qubits):
        for qubit in qubits:
            qubit_to_gates[qubit].append(index)
    edges: set[tuple[int, int]] = set()
    for gates_on_qubit in qubit_to_gates.values():
        for k in range(len(gates_on_qubit) - 1):
            edges.add((gates_on_qubit[k], gates_on_qubit[k + 1]))
    in_degree = [0] * gate_count
    adjacency: dict[int, list[int]] = defaultdict(list)
    for left, right in edges:
        adjacency[left].append(right)
        in_degree[right] += 1
    primary_wire = [min(qubits) for qubits in gate_qubits]
    heap: list[tuple[int, int]] = []
    for index in range(gate_count):
        if in_degree[index] == 0:
            heapq.heappush(heap, (primary_wire[index], index))
    order: list[int] = []
    while heap:
        _, index = heapq.heappop(heap)
        order.append(index)
        for successor in adjacency[index]:
            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                heapq.heappush(heap, (primary_wire[successor], successor))
    if len(order) != gate_count:
        # Unreachable for a valid listing (the DAG is acyclic by
        # construction); mirrors the preprocessor's fallback exactly.
        return state
    return _state_from_normalized(
        state.num_qubits, tuple(state.gates[index] for index in order)
    )


@lru_cache(maxsize=4)
def _rule_library(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    library = json.loads(path.read_text(encoding="utf-8"))
    rules = library.get("rules")
    if not isinstance(rules, list) or len(rules) != 1488:
        raise ValueError("rule_library_count_invalid")
    quartz = [rule for rule in rules if rule.get("rule_family") == "quartz_v1"]
    auxiliary = [rule for rule in rules if rule.get("rule_family") != "quartz_v1"]
    if len(quartz) != 1474 or len({rule.get("content_hash") for rule in rules}) != len(rules):
        raise ValueError("rule_library_quartz_or_hash_invalid")
    return quartz, auxiliary


def filter_rule_scope(
    rules: Iterable[Mapping[str, Any]],
    rule_scope: str = "full",
) -> list[dict[str, Any]]:
    """Restrict Quartz rules to the declared certification scope.

    ``full`` keeps every rule unchanged and in input order; ``e44_core_v1``
    keeps the pinned core subset (source on at most 2 qubits, at most 4 source
    operations, at most 6 target operations).  Any other scope name is
    rejected.  This is the single authority for scope membership; the engine
    indexes and the certified lower-bound derivation must agree on it.
    """

    if rule_scope == "full":
        return list(rules)
    if rule_scope == "e44_core_v1":
        return [
            rule for rule in rules
            if int(rule["source"]["num_qubits"]) <= 2
            and len(rule["source"]["operations"]) <= 4
            and len(rule["target"]["operations"]) <= 6
        ]
    raise ValueError(f"unknown_rule_scope:{rule_scope}")


@lru_cache(maxsize=8)
def _quartz_index(path: Path, rule_scope: str = "full") -> dict[tuple[str, ...], tuple[dict[str, Any], ...]]:
    quartz = filter_rule_scope(_rule_library(path)[0], rule_scope)
    index: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for rule in quartz:
        signature = tuple(operation["name"] for operation in rule["source"]["operations"])
        index[signature].append(rule)
    return {signature: tuple(rules) for signature, rules in index.items()}


@lru_cache(maxsize=8)
def _quartz_first_index(path: Path, rule_scope: str = "full") -> dict[str, tuple[tuple[tuple[str, ...], tuple[dict[str, Any], ...]], ...]]:
    """Index the immutable signature table by its first operation name.

    The public action order remains governed by ``sort_key``.  This index only
    removes the repeated scan over signatures that cannot match the gate at a
    given listing position.
    """
    grouped: dict[str, list[tuple[tuple[str, ...], tuple[dict[str, Any], ...]]]] = defaultdict(list)
    for signature, rules in _quartz_index(path, rule_scope).items():
        if signature:
            grouped[signature[0]].append((signature, rules))
    return {name: tuple(entries) for name, entries in grouped.items()}


@lru_cache(maxsize=8)
def _quartz_rule_by_id(
    path: Path, rule_scope: str = "full"
) -> dict[str, tuple[tuple[str, ...], dict[str, Any]]]:
    """Cache the rule-id lookup used by every exact-search state."""

    return {
        rule["rule_id"]: (signature, rule)
        for signature, signature_rules in _quartz_index(path, rule_scope).items()
        for rule in signature_rules
    }


@lru_cache(maxsize=8)
def _quartz_rule_ids(path: Path, rule_scope: str = "full") -> tuple[str, ...]:
    """Return the immutable deterministic Quartz rule order."""

    return tuple(sorted(_quartz_rule_by_id(path, rule_scope)))


@lru_cache(maxsize=262144)
def _binding_json(
    mapping_items: tuple[tuple[int, int], ...],
    source_items: tuple[tuple[str, float], ...],
    target_items: tuple[tuple[str, float], ...],
) -> str:
    return json.dumps(
        {
            "qubits": [[f"Q{key}", int(value)] for key, value in mapping_items],
            "parameters": [[key, format(float(value), ".17g")] for key, value in target_items],
            "source_parameters": [[key, format(float(value), ".17g")] for key, value in source_items],
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _map_binding(mapping: Mapping[int, int], source_values: Mapping[str, float], target_values: Mapping[str, float]) -> str:
    return _binding_json(
        tuple(sorted(mapping.items())),
        tuple(sorted(source_values.items())),
        tuple(sorted(target_values.items())),
    )


def _quartz_actions(
    state: LandscapeState,
    rules_by_signature: Mapping[tuple[str, ...], tuple[dict[str, Any], ...]],
) -> list[LandscapeAction]:
    return list(_iter_quartz_actions(state, rules_by_signature))


def _iter_quartz_actions(
    state: LandscapeState,
    rules_by_signature: Mapping[tuple[str, ...], tuple[dict[str, Any], ...]],
    *,
    only_rule_id: str | None = None,
    only_location: int | None = None,
) -> Iterable[LandscapeAction]:
    gate_names = tuple(gate.name for gate in state.gates)
    signature_lengths = tuple(sorted({len(signature) for signature in rules_by_signature}))
    locations = range(len(state.gates)) if only_location is None else (only_location,)
    for location in locations:
        for source_length in signature_lengths:
            if location + source_length > len(gate_names):
                continue
            source_names = gate_names[location:location + source_length]
            rules = rules_by_signature.get(source_names, ())
            for rule in rules:
                if only_rule_id is not None and rule["rule_id"] != only_rule_id:
                    continue
                yield from _iter_quartz_rule_actions(state, rule, location)


def _iter_quartz_rule_actions(
    state: LandscapeState,
    rule: Mapping[str, Any],
    location: int,
    deadline: float | None = None,
) -> Iterable[LandscapeAction]:
    """Yield matches for one indexed rule at one already matching location.

    The ordered operands in every matched source operation constrain the
    source-to-actual qubit map directly.  Enumerating permutations for qubits
    that have already appeared is equivalent but much more expensive on the
    long listings in E45; only source variables absent from the source
    operations remain genuinely unconstrained and retain the permutation
    enumeration required by the rule semantics.
    """

    source = rule["source"]
    target = rule["target"]
    source_ops = source["operations"]
    if int(source["num_qubits"]) > state.num_qubits:
        return
    source_qubits = int(source["num_qubits"])
    if location < 0 or location + len(source_ops) > len(state.gates) or not source_ops:
        return
    first_template = source_ops[0]
    first_actual = state.gates[location]
    if len(first_template["qubits"]) != len(first_actual.qubits):
        return
    if len(set(first_template["qubits"])) != len(first_template["qubits"]):
        return
    if len(set(first_actual.qubits)) != len(first_actual.qubits):
        return

    constrained: dict[int, int] = {}
    reverse_constrained: dict[int, int] = {}
    source_values: dict[str, float] = {}
    for template_operation, actual_gate in zip(
        source_ops, state.gates[location:location + len(source_ops)]
    ):
        _check_deadline(deadline)
        template_qubits = tuple(int(q) for q in template_operation["qubits"])
        if len(template_qubits) != len(actual_gate.qubits):
            return
        for template_qubit, actual_qubit in zip(template_qubits, actual_gate.qubits):
            previous_actual = constrained.get(template_qubit)
            if previous_actual is not None and previous_actual != actual_qubit:
                return
            previous_template = reverse_constrained.get(actual_qubit)
            if previous_template is not None and previous_template != template_qubit:
                return
            constrained[template_qubit] = actual_qubit
            reverse_constrained[actual_qubit] = template_qubit
        for parameter in template_operation.get("params", []):
            if actual_gate.angle is None:
                return
            value = normalize_angle(actual_gate.angle)
            if parameter in source_values and not angles_equal(source_values[parameter], value):
                return
            source_values[parameter] = value

    unmapped_template = [q for q in range(source_qubits) if q not in constrained]
    available_actual = [q for q in range(state.num_qubits) if q not in reverse_constrained]
    target_values = {
        parameter: normalize_angle(sum(
            int(coefficient) * source_values[label]
            for label, coefficient in expression.items()
        ))
        for parameter, expression in rule.get("parameter_binding", {}).items()
    }
    for remaining_actual in itertools.permutations(available_actual, len(unmapped_template)):
        _check_deadline(deadline)
        mapping = dict(constrained)
        mapping.update(zip(unmapped_template, remaining_actual))
        replacement = tuple(
            _intern_state_gate(
                operation["name"],
                tuple(mapping[int(q)] for q in operation["qubits"]),
                None if not operation.get("params") else target_values[operation["params"][0]],
            )
            for operation in target["operations"]
        )
        post = _state_from_splice(state, location, len(source_ops), replacement)
        if post.state_hash == state.state_hash:
            continue
        binding = _map_binding(mapping, source_values, target_values)
        yield LandscapeAction(
            rule_id=rule["rule_id"], family="quartz_v1", location=location,
            binding=binding, pre_state_sha256=state.state_hash,
            post_state_sha256=post.state_hash, local_proof_hash=rule["symbolic_proof_hash"],
            post_state=post, cost_delta=post.cost - state.cost,
        )


_SELF_INVERSE = frozenset({"h", "x", "y", "z", "cx", "cz", "swap"})
_ROTATION_FAMILY = frozenset({"rx", "ry", "rz"})
_Z_FAMILY = frozenset({"z", "rz", "s", "sdg", "t", "tdg"})
_X_FAMILY = frozenset({"x", "rx"})


def _pair_action(state: LandscapeState, location: int, rule_id: str, replacement: Iterable[StateGate], proof: str) -> LandscapeAction:
    post = _state_from_splice(state, location, 2, replacement)
    return LandscapeAction(
        rule_id=rule_id, family="pair_v1", location=location, binding="{}",
        pre_state_sha256=state.state_hash, post_state_sha256=post.state_hash,
        local_proof_hash=proof, post_state=post, cost_delta=post.cost - state.cost,
    )


def _iter_pair_candidates(
    state: LandscapeState,
) -> Iterable[tuple[int, str, tuple[StateGate, ...], str]]:
    for location, (left, right) in enumerate(zip(state.gates, state.gates[1:])):
        if left.qubits == right.qubits and left.name == right.name and left.name in _SELF_INVERSE:
            yield location, "pair_v1.self_inverse", (), "pair_v1.self_inverse"
        elif left.qubits == right.qubits and {left.name, right.name} == {"t", "tdg"}:
            yield location, "pair_v1.t_tdg", (), "pair_v1.t_tdg"
        elif left.qubits == right.qubits and {left.name, right.name} == {"s", "sdg"}:
            yield location, "pair_v1.s_sdg", (), "pair_v1.s_sdg"
        elif left.qubits == right.qubits and left.name == right.name and left.name in {"rx", "ry", "rz"}:
            angle = normalize_angle((left.angle or 0.0) + (right.angle or 0.0))
            rule_id = "pair_v1.rotation_zero" if abs(angle) <= ANGLE_TOLERANCE else "pair_v1.rotation_merge"
            replacement = () if rule_id.endswith("zero") else (_intern_state_gate(left.name, left.qubits, angle),)
            yield location, rule_id, replacement, rule_id


def _iter_pair_actions(
    state: LandscapeState,
    *,
    only_rule_id: str | None = None,
    only_location: int | None = None,
    deadline: float | None = None,
) -> Iterable[LandscapeAction]:
    for location, rule_id, replacement, proof in _iter_pair_candidates(state):
        _check_deadline(deadline)
        if only_location is not None and location != only_location:
            continue
        if only_rule_id is not None and rule_id != only_rule_id:
            continue
        yield _pair_action(state, location, rule_id, replacement, proof)


def _pair_actions(state: LandscapeState) -> list[LandscapeAction]:
    return list(_iter_pair_actions(state))


@lru_cache(maxsize=32768)
def _commutes(left: StateGate, right: StateGate) -> tuple[str, str] | None:
    left_set, right_set = set(left.qubits), set(right.qubits)
    if left_set.isdisjoint(right_set):
        return "exchange.disjoint", "disjoint"
    if left.name == right.name and left.qubits == right.qubits and len(left.qubits) == 1:
        return "exchange.same_single", "same_single"
    if left.name == right.name and left.qubits == right.qubits and left.name in {"rx", "ry", "rz"}:
        return "exchange.same_axis_rotation", "same_axis_rotation"
    if left.name in _Z_FAMILY and right.name in _Z_FAMILY and left.qubits == right.qubits:
        return "exchange.z_family", "z_family"
    if left.name == "cx" and right.name in _Z_FAMILY and len(right.qubits) == 1 and right.qubits[0] == left.qubits[0]:
        return "exchange.cx_control_z", "cx_control_z"
    if right.name == "cx" and left.name in _Z_FAMILY and len(left.qubits) == 1 and left.qubits[0] == right.qubits[0]:
        return "exchange.cx_control_z", "cx_control_z"
    if left.name == "cx" and right.name in _X_FAMILY and len(right.qubits) == 1 and right.qubits[0] == left.qubits[1]:
        return "exchange.cx_target_x", "cx_target_x"
    if right.name == "cx" and left.name in _X_FAMILY and len(left.qubits) == 1 and left.qubits[0] == right.qubits[1]:
        return "exchange.cx_target_x", "cx_target_x"
    if left.name == "cz" and right.name in _Z_FAMILY and len(right.qubits) == 1 and right.qubits[0] in left_set:
        return "exchange.cz_z", "cz_z"
    if right.name == "cz" and left.name in _Z_FAMILY and len(left.qubits) == 1 and left.qubits[0] in right_set:
        return "exchange.cz_z", "cz_z"
    if left.name == right.name == "swap" and left_set == right_set:
        return "exchange.same_swap", "same_swap"
    if left.name == right.name == "cz" and left_set == right_set:
        return "exchange.same_cz", "same_cz"
    return None


def _exchange_actions(state: LandscapeState) -> list[LandscapeAction]:
    return list(_iter_exchange_actions(state))


def _iter_exchange_actions(
    state: LandscapeState,
    *,
    only_rule_id: str | None = None,
    only_location: int | None = None,
    deadline: float | None = None,
) -> Iterable[LandscapeAction]:
    proof_by_rule = {rule: rule for rule in (
        "exchange.disjoint", "exchange.same_single", "exchange.same_axis_rotation", "exchange.z_family",
        "exchange.cx_control_z", "exchange.cx_target_x", "exchange.cz_z", "exchange.same_swap", "exchange.same_cz"
    )}
    for location, (left, right) in enumerate(zip(state.gates, state.gates[1:])):
        _check_deadline(deadline)
        if only_location is not None and location != only_location:
            continue
        classification = _commutes(left, right)
        if classification is None:
            continue
        rule_id, _ = classification
        if only_rule_id is not None and rule_id != only_rule_id:
            continue
        post = _state_from_splice(state, location, 2, (right, left))
        if post.state_hash == state.state_hash:
            continue
        yield LandscapeAction(
            rule_id=rule_id, family="structural_exchange_v1", location=location,
            binding="{}", pre_state_sha256=state.state_hash,
            post_state_sha256=post.state_hash, local_proof_hash=proof_by_rule[rule_id],
            post_state=post, cost_delta=0,
        )


def legal_actions(
    state: LandscapeState,
    rule_library_path: Path,
    rule_scope: str = "full",
) -> list[LandscapeAction]:
    actions = _quartz_actions(state, _quartz_index(rule_library_path, rule_scope)) + _pair_actions(state) + _exchange_actions(state)
    dedup: dict[tuple[Any, ...], LandscapeAction] = {}
    for action in actions:
        dedup[action.sort_key] = action
    return sorted(dedup.values(), key=lambda action: action.sort_key)


def iter_legal_actions(
    state: LandscapeState,
    rule_library_path: Path,
    rule_scope: str = "full",
    *,
    deadline: float | None = None,
) -> Iterable[LandscapeAction]:
    """Yield legal actions in the historical deterministic action order.

    Matching locations are indexed by the first operation name before rules
    are checked.  Actions are still emitted rule-by-rule and location-by-
    location, matching the public ``legal_actions`` sort key without scanning
    the complete listing once per rule.
    """

    rule_by_id = _quartz_rule_by_id(rule_library_path, rule_scope)
    rules_by_signature = _quartz_index(rule_library_path, rule_scope)
    gate_names = tuple(gate.name for gate in state.gates)
    locations_by_signature: dict[tuple[str, ...], list[int]] = defaultdict(list)
    signature_lengths = tuple(sorted({len(signature) for signature in rules_by_signature if signature}))
    for location in range(len(gate_names)):
        _check_deadline(deadline)
        for signature_length in signature_lengths:
            if location + signature_length > len(gate_names):
                continue
            signature = gate_names[location:location + signature_length]
            if signature in rules_by_signature:
                locations_by_signature[signature].append(location)
    _check_deadline(deadline)
    matched_quartz_rule_ids = {
        rule["rule_id"]
        for signature, locations in locations_by_signature.items()
        if locations
        for rule in rules_by_signature[signature]
    }
    auxiliary_rule_ids = (
        "exchange.cx_control_z",
        "exchange.cx_target_x",
        "exchange.disjoint",
        "exchange.same_cz",
        "exchange.same_single",
        "exchange.same_swap",
        "exchange.same_axis_rotation",
        "exchange.z_family",
        "exchange.cz_z",
        "pair_v1.rotation_merge",
        "pair_v1.rotation_zero",
        "pair_v1.s_sdg",
        "pair_v1.self_inverse",
        "pair_v1.t_tdg",
    )
    pair_by_rule: dict[str, list[LandscapeAction]] | None = None
    exchange_by_rule: dict[str, list[LandscapeAction]] | None = None
    for rule_id in sorted((*matched_quartz_rule_ids, *auxiliary_rule_ids)):
        _check_deadline(deadline)
        if rule_id in matched_quartz_rule_ids:
            signature, rule = rule_by_id[rule_id]
            local_actions: list[LandscapeAction] = []
            for location in locations_by_signature.get(signature, ()):
                _check_deadline(deadline)
                local_actions.extend(_iter_quartz_rule_actions(state, rule, location, deadline))
            if len(local_actions) > 1:
                local_actions.sort(key=lambda action: action.sort_key)
            yield from local_actions
        elif rule_id.startswith("pair_v1."):
            if pair_by_rule is None:
                pair_by_rule = defaultdict(list)
                for action in _iter_pair_actions(state, deadline=deadline):
                    pair_by_rule[action.rule_id].append(action)
            local_actions = pair_by_rule.get(rule_id, [])
            if len(local_actions) > 1:
                local_actions.sort(key=lambda action: action.sort_key)
            yield from local_actions
        else:
            if exchange_by_rule is None:
                exchange_by_rule = defaultdict(list)
                for action in _iter_exchange_actions(state, deadline=deadline):
                    exchange_by_rule[action.rule_id].append(action)
            local_actions = exchange_by_rule.get(rule_id, [])
            if len(local_actions) > 1:
                local_actions.sort(key=lambda action: action.sort_key)
            yield from local_actions


def _path_from_parent(
    state_hash: str,
    parents: Mapping[str, tuple[str, LandscapeAction]],
) -> list[LandscapeAction]:
    result = []
    current = state_hash
    while current in parents:
        previous, action = parents[current]
        result.append(action)
        current = previous
    return list(reversed(result))


def _path_peak(initial: LandscapeState, path: Iterable[LandscapeAction]) -> int:
    peak = initial.cost
    current = initial
    for action in path:
        peak = max(peak, action.post_state.cost)
        current = action.post_state
    return peak


def _threshold_escape(
    initial: LandscapeState,
    states: Mapping[str, LandscapeState],
    adjacency: Mapping[str, list[LandscapeAction]],
    horizon: int,
    threshold: int,
) -> tuple[str, list[LandscapeAction]] | None:
    queue = deque([(initial.state_hash, 0)])
    parents: dict[tuple[str, int], tuple[tuple[str, int], LandscapeAction]] = {}
    seen = {(initial.state_hash, 0)}
    while queue:
        current_hash, depth = queue.popleft()
        current = states[current_hash]
        if depth > 0 and current.cost < initial.cost:
            path = []
            key = (current_hash, depth)
            while key != (initial.state_hash, 0):
                previous, action = parents[key]
                path.append(action)
                key = previous
            return current_hash, list(reversed(path))
        if depth >= horizon:
            continue
        for action in adjacency.get(current_hash, []):
            if action.post_state.cost > initial.cost + threshold:
                continue
            child = (action.post_state_sha256, depth + 1)
            if child in seen:
                continue
            seen.add(child)
            parents[child] = ((current_hash, depth), action)
            queue.append(child)
    return None


def _greedy_trace(initial: LandscapeState, adjacency: Mapping[str, list[LandscapeAction]]) -> list[LandscapeAction]:
    current = initial
    trace: list[LandscapeAction] = []
    seen = {current.state_hash}
    while True:
        improving = [action for action in adjacency.get(current.state_hash, []) if action.post_state.cost < current.cost]
        if not improving:
            return trace
        action = min(improving, key=lambda candidate: (candidate.post_state.cost, candidate.post_state_sha256, candidate.sort_key))
        if action.post_state_sha256 in seen:
            return trace
        trace.append(action)
        seen.add(action.post_state_sha256)
        current = action.post_state


def search_landscape(
    initial: LandscapeState,
    rule_library_path: Path,
    horizon: int,
    state_budget: int | None = None,
    rule_scope: str = "full",
) -> dict[str, Any]:
    initial = initial.normalized()
    try:
        quartz, _ = _rule_library(rule_library_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"status": STATUS_INVALID_RULES, "failure_reason": f"{type(exc).__name__}:{exc}"}
    if initial.num_qubits < 1 or any(
        gate.name not in {"h", "x", "y", "z", "s", "sdg", "t", "tdg", "rx", "ry", "rz", "cx", "cz", "swap"}
        or any(q < 0 or q >= initial.num_qubits for q in gate.qubits)
        for gate in initial.gates
    ):
        return {"status": STATUS_UNSUPPORTED}
    states: dict[str, LandscapeState] = {initial.state_hash: initial}
    distances: dict[str, int] = {initial.state_hash: 0}
    parents: dict[str, tuple[str, LandscapeAction]] = {}
    adjacency: dict[str, list[LandscapeAction]] = {}
    queue = deque([initial.state_hash])
    expanded = 0
    pruned = 0
    resource_limited = False
    while queue:
        current_hash = queue.popleft()
        current = states[current_hash]
        depth = distances[current_hash]
        if depth >= horizon:
            continue
        if state_budget is not None and expanded >= state_budget:
            resource_limited = True
            pruned += len(queue) + 1
            break
        actions = legal_actions(current, rule_library_path, rule_scope)
        adjacency[current_hash] = actions
        expanded += 1
        for action in actions:
            child_hash = action.post_state_sha256
            if child_hash not in states:
                states[child_hash] = action.post_state
                distances[child_hash] = depth + 1
                parents[child_hash] = (current_hash, action)
                queue.append(child_hash)
            else:
                pruned += 1
    # Nodes at the horizon are not expanded, but their parent actions are
    # still present in the complete state set and witness paths.
    improving = [
        state for state in states.values()
        if distances[state.state_hash] > 0 and state.cost < initial.cost
    ]
    best = min(states.values(), key=lambda state: (state.cost, distances[state.state_hash], state.state_hash))
    escape_state = min(
        improving,
        key=lambda state: (distances[state.state_hash], _path_peak(initial, _path_from_parent(state.state_hash, parents)), state.state_hash),
        default=None,
    )
    escape_path = _path_from_parent(escape_state.state_hash, parents) if escape_state else []
    barrier_witness = None
    max_threshold = max((state.cost - initial.cost for state in states.values()), default=0)
    for threshold in range(max(0, max_threshold) + 1):
        barrier_witness = _threshold_escape(initial, states, adjacency, horizon, threshold)
        if barrier_witness is not None:
            break
    if barrier_witness is None:
        barrier_height: int | None = None
        barrier_path: list[LandscapeAction] = []
    else:
        _, barrier_path = barrier_witness
        barrier_height = max(0, _path_peak(initial, barrier_path) - initial.cost)
    greedy_path = _greedy_trace(initial, adjacency)
    if resource_limited:
        status = STATUS_WITNESS_INCOMPLETE if escape_state else STATUS_RESOURCE_NO_WITNESS
    else:
        status = STATUS_EXACT_ESCAPE if escape_state else STATUS_EXACT_LOCAL
    witnesses = {
        "escape": [action.to_dict() for action in escape_path],
        "barrier": [action.to_dict() for action in barrier_path],
        "greedy": [action.to_dict() for action in greedy_path],
    }
    certificate = {
        "status": status,
        "initial_state_sha256": initial.state_hash,
        "horizon": horizon,
        "state_budget": state_budget,
        "rule_scope": rule_scope,
        "baseline_cost": initial.cost,
        "best_cost": best.cost,
        "best_state_sha256": best.state_hash,
        "escape_depth": distances[escape_state.state_hash] if escape_state else None,
        "barrier_height": barrier_height,
        "states_seen": len(states),
        "expanded": expanded,
        "pruned": pruned,
        "state_set_sha256": hashlib.sha256("\n".join(sorted(states)).encode()).hexdigest(),
        "state_hashes": sorted(states),
        "witnesses": witnesses,
        "semantic_status": "NOT_REPLAYED",
        "resource_status": "TRUNCATED" if resource_limited else "COMPLETE",
        "exactness_status": "INCOMPLETE" if resource_limited else "EXACT_FINITE_HORIZON",
        "no_improvement_explanations": [] if escape_state else ["H_INSUFFICIENT" if horizon > 0 else "RULE_LIBRARY_GAP"],
    }
    certificate["certificate_sha256"] = sha256_json(certificate)
    return certificate


def search_landscape_horizons(
    initial: LandscapeState,
    rule_library_path: Path,
    horizons: Iterable[int],
    state_budget: int | None = None,
    rule_scope: str = "full",
) -> dict[str, dict[str, Any]]:
    """Run one exact BFS and emit deterministic certificates for many H values."""

    requested = tuple(sorted(set(int(horizon) for horizon in horizons)))
    if not requested or any(horizon < 0 for horizon in requested):
        raise ValueError("horizons_must_be_nonnegative_and_nonempty")
    initial = initial.normalized()
    try:
        _rule_library(rule_library_path)
        _quartz_index(rule_library_path, rule_scope)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {str(horizon): {"status": STATUS_INVALID_RULES, "failure_reason": f"{type(exc).__name__}:{exc}"} for horizon in requested}
    states: dict[str, LandscapeState] = {initial.state_hash: initial}
    distances: dict[str, int] = {initial.state_hash: 0}
    parents: dict[str, tuple[str, LandscapeAction]] = {}
    adjacency: dict[str, list[LandscapeAction]] = {}
    expanded_by_depth: Counter[int] = Counter()
    pruned_by_depth: Counter[int] = Counter()
    queue = deque([initial.state_hash])
    max_horizon = max(requested)
    resource_limited = False
    while queue:
        current_hash = queue.popleft()
        current = states[current_hash]
        depth = distances[current_hash]
        if depth >= max_horizon:
            continue
        if state_budget is not None and sum(expanded_by_depth.values()) >= state_budget:
            resource_limited = True
            pruned_by_depth[depth] += len(queue) + 1
            break
        actions = legal_actions(current, rule_library_path, rule_scope)
        adjacency[current_hash] = actions
        expanded_by_depth[depth] += 1
        for action in actions:
            child_hash = action.post_state_sha256
            if child_hash not in states:
                states[child_hash] = action.post_state
                distances[child_hash] = depth + 1
                parents[child_hash] = (current_hash, action)
                queue.append(child_hash)
            else:
                pruned_by_depth[depth] += 1
    certificates: dict[str, dict[str, Any]] = {}
    for horizon in requested:
        visible = {
            state_hash: state
            for state_hash, state in states.items()
            if distances[state_hash] <= horizon
        }
        improving = [
            state for state_hash, state in visible.items()
            if distances[state_hash] > 0 and state.cost < initial.cost
        ]
        best = min(visible.values(), key=lambda state: (state.cost, distances[state.state_hash], state.state_hash))
        escape_state = min(
            improving,
            key=lambda state: (distances[state.state_hash], _path_peak(initial, _path_from_parent(state.state_hash, parents)), state.state_hash),
            default=None,
        )
        escape_path = _path_from_parent(escape_state.state_hash, parents) if escape_state else []
        visible_adjacency = {
            state_hash: actions
            for state_hash, actions in adjacency.items()
            if distances[state_hash] < horizon
        }
        barrier_witness = None
        max_threshold = max((state.cost - initial.cost for state in visible.values()), default=0)
        for threshold in range(max(0, max_threshold) + 1):
            barrier_witness = _threshold_escape(initial, visible, visible_adjacency, horizon, threshold)
            if barrier_witness is not None:
                break
        if barrier_witness is None:
            barrier_height = None
            barrier_path: list[LandscapeAction] = []
        else:
            _, barrier_path = barrier_witness
            barrier_height = max(0, _path_peak(initial, barrier_path) - initial.cost)
        greedy_path = _greedy_trace(initial, visible_adjacency)
        reached_cutoff = resource_limited and sum(expanded_by_depth[d] for d in range(horizon)) >= (state_budget or 0)
        if reached_cutoff:
            status = STATUS_WITNESS_INCOMPLETE if escape_state else STATUS_RESOURCE_NO_WITNESS
        else:
            status = STATUS_EXACT_ESCAPE if escape_state else STATUS_EXACT_LOCAL
        certificate = {
            "status": status,
            "initial_state_sha256": initial.state_hash,
            "horizon": horizon,
            "state_budget": state_budget,
            "rule_scope": rule_scope,
            "baseline_cost": initial.cost,
            "best_cost": best.cost,
            "best_state_sha256": best.state_hash,
            "escape_depth": distances[escape_state.state_hash] if escape_state else None,
            "barrier_height": barrier_height,
            "states_seen": len(visible),
            "expanded": sum(expanded_by_depth[d] for d in range(horizon)),
            "pruned": sum(pruned_by_depth[d] for d in range(horizon)),
            "state_set_sha256": hashlib.sha256("\n".join(sorted(visible)).encode()).hexdigest(),
            "state_hashes": sorted(visible),
            "witnesses": {
                "escape": [action.to_dict() for action in escape_path],
                "barrier": [action.to_dict() for action in barrier_path],
                "greedy": [action.to_dict() for action in greedy_path],
            },
            "semantic_status": "NOT_REPLAYED",
            "resource_status": "TRUNCATED" if reached_cutoff else "COMPLETE",
            "exactness_status": "INCOMPLETE" if reached_cutoff else "EXACT_FINITE_HORIZON",
            "no_improvement_explanations": [] if escape_state else ["H_INSUFFICIENT" if horizon > 0 else "RULE_LIBRARY_GAP"],
        }
        certificate["certificate_sha256"] = sha256_json(certificate)
        certificates[str(horizon)] = certificate
    return certificates


def _threshold_escape_compact(
    initial: LandscapeState,
    states: Mapping[str, LandscapeState],
    horizon: int,
    threshold: int,
    rule_library_path: Path,
    rule_scope: str,
) -> tuple[str, list[LandscapeAction]] | None:
    """Enumerate one barrier threshold without retaining a global adjacency map.

    The original exact implementation keeps every action list alive until all
    certificates are assembled.  That is convenient for the oracle but makes
    the action objects dominate memory on long listings.  This variant
    regenerates actions for the compact threshold frontier and retains only
    its local parent table; the transition contract and action order are
    unchanged.
    """

    queue = deque([(initial.state_hash, 0)])
    parents: dict[tuple[str, int], tuple[tuple[str, int], LandscapeAction]] = {}
    seen = {(initial.state_hash, 0)}
    while queue:
        current_hash, depth = queue.popleft()
        current = states[current_hash]
        if depth > 0 and current.cost < initial.cost:
            path: list[LandscapeAction] = []
            key = (current_hash, depth)
            while key != (initial.state_hash, 0):
                previous, action = parents[key]
                path.append(action)
                key = previous
            return current_hash, list(reversed(path))
        if depth >= horizon:
            continue
        for action in legal_actions(current, rule_library_path, rule_scope):
            if action.post_state.cost > initial.cost + threshold:
                continue
            child = (action.post_state_sha256, depth + 1)
            if child in seen:
                continue
            seen.add(child)
            parents[child] = ((current_hash, depth), action)
            queue.append(child)
    return None


def _greedy_trace_compact(
    initial: LandscapeState,
    rule_library_path: Path,
    rule_scope: str,
    deadline: float | None = None,
) -> list[LandscapeAction]:
    """Build the deterministic pairwise greedy trace without cached adjacency."""

    current = initial
    trace: list[LandscapeAction] = []
    seen = {current.state_hash}
    while True:
        if deadline is not None and time.perf_counter() >= deadline:
            return trace
        improving = [
            action
            for action in iter_legal_actions(
                current, rule_library_path, rule_scope, deadline=deadline
            )
            if action.post_state.cost < current.cost
        ]
        if not improving:
            return trace
        action = min(
            improving,
            key=lambda candidate: (
                candidate.post_state.cost,
                candidate.post_state_sha256,
                candidate.sort_key,
            ),
        )
        if action.post_state_sha256 in seen:
            return trace
        trace.append(action)
        seen.add(action.post_state_sha256)
        current = action.post_state


def _minimax_barrier_compact(
    initial: LandscapeState,
    horizon: int,
    rule_library_path: Path,
    rule_scope: str,
    deadline: float | None = None,
) -> tuple[tuple[int, list[LandscapeAction]] | None, bool]:
    """Find the minimum peak-cost improving path in one layered traversal.

    A threshold sweep re-enumerates the same state frontier once per possible
    barrier value.  Here each ``(state, exact depth)`` keeps only its lowest
    reachable peak cost; a higher-peak path to the same key is dominated for
    every continuation.  Keeping exact depth preserves paths that use a
    harmless exchange or other zero-cost edge before an improvement.  An
    additional admissible per-gate reachability prune drops branches from
    which no improving cost is reachable within the remaining horizon; every
    state on any improving path survives it, so the certified minimum peak
    and its witness height are unchanged.
    """

    levels: list[dict[str, tuple[LandscapeState, int]]] = [{initial.state_hash: (initial, initial.cost)}]
    prior_min_peak: dict[str, int] = {initial.state_hash: initial.cost}
    parents: dict[tuple[int, str], tuple[tuple[int, str], LandscapeAction]] = {}
    insertion_order: dict[tuple[int, str], int] = {(0, initial.state_hash): 0}
    order = 1
    improving: tuple[int, int, int, str] | None = None
    improving_key: tuple[int, str] | None = None
    target_cost = initial.cost - 1
    reach_cache: dict[tuple[str, int], bool] = {}

    def _cannot_reach_target(state: LandscapeState, budget: int) -> bool:
        """Admissible test: no cost <= target_cost state within ``budget`` actions.

        Uses the per-gate certified bound, so a positive verdict proves that
        no improving path passes through ``state`` within the remaining
        horizon; such branches contribute no barrier witness and may be
        dropped without changing the certified minimum peak.
        """

        key = (state.state_hash, budget)
        verdict = reach_cache.get(key)
        if verdict is None:
            verdict = admissible_remaining_cost_lower_bound(
                state, target_cost, budget,
                rule_library_path=rule_library_path, rule_scope=rule_scope,
            ) > target_cost
            reach_cache[key] = verdict
        return verdict

    for depth in range(horizon):
        next_level: dict[str, tuple[LandscapeState, int]] = {}
        for current_hash, (current, current_peak) in levels[depth].items():
            # The peak cost cannot decrease along a path.  Once an improving
            # path has supplied an upper bound, a state already above that
            # bound cannot produce a better barrier certificate.  This is a
            # dominance prune in the barrier traversal only; the complete BFS
            # state set and its exactness contract remain unchanged.
            if improving is not None and current_peak > improving[0]:
                continue
            # Admissible reachability prune: a state from which no improving
            # cost is reachable within the remaining horizon cannot lie on
            # any improving path, so expanding it cannot change the certified
            # barrier.  Improving states always fail the cost guard below.
            if current.cost > target_cost and _cannot_reach_target(current, horizon - depth):
                continue
            try:
                actions = iter_legal_actions(
                    current, rule_library_path, rule_scope, deadline=deadline
                )
                for action in actions:
                    child_hash = action.post_state_sha256
                    # Prune a child whose current cost plus the admissible
                    # remaining reduction already excludes the improvement
                    # target within the child's remaining horizon.
                    if (
                        action.post_state.cost > target_cost
                        and _cannot_reach_target(action.post_state, horizon - depth - 1)
                    ):
                        continue
                    child_peak = max(current_peak, action.post_state.cost)
                    # A path to the same state from an earlier depth with an
                    # equal-or-lower peak dominates this path: every
                    # continuation from the later occurrence also fits the
                    # remaining horizon from the earlier occurrence.
                    if prior_min_peak.get(child_hash, math.inf) <= child_peak:
                        continue
                    prior_entry = next_level.get(child_hash)
                    if prior_entry is not None and child_peak >= prior_entry[1]:
                        continue
                    next_level[child_hash] = (action.post_state, child_peak)
                    key = (depth + 1, child_hash)
                    if key not in insertion_order:
                        insertion_order[key] = order
                        order += 1
                    parents[key] = ((depth, current_hash), action)
                    if action.post_state.cost < initial.cost and child_peak == initial.cost:
                        immediate_path: list[LandscapeAction] = []
                        winning_key = key
                        while winning_key[0] > 0:
                            parent_key, winning_action = parents[winning_key]
                            immediate_path.append(winning_action)
                            winning_key = parent_key
                        return (0, list(reversed(immediate_path))), False
                    candidate = (
                        child_peak,
                        depth + 1,
                        insertion_order[key],
                        child_hash,
                    )
                    if action.post_state.cost < initial.cost and (improving is None or candidate < improving):
                        improving = candidate
                        improving_key = key
            except _SearchResourceLimit:
                return None, True
        for state_hash, (_, peak) in next_level.items():
            prior_min_peak[state_hash] = min(prior_min_peak.get(state_hash, math.inf), peak)
        levels.append(next_level)
    if improving is None or improving_key is None:
        return None, False
    path: list[LandscapeAction] = []
    key = improving_key
    while key[0] > 0:
        key, action = parents[key]
        path.append(action)
    return (improving[0] - initial.cost, list(reversed(path))), False


@lru_cache(maxsize=8)
def _maximum_single_step_reduction(rule_library_path: Path, rule_scope: str) -> int:
    """Return a safe admissible bound for one action's gate-count decrease."""

    quartz, _ = _rule_library(rule_library_path)
    quartz = filter_rule_scope(quartz, rule_scope)
    reduction = max(
        [
            len(rule["source"]["operations"]) - len(rule["target"]["operations"])
            for rule in quartz
        ]
        + [2],  # pair cancellation is the largest auxiliary reduction
    )
    return max(0, int(reduction))


@lru_cache(maxsize=8)
def _per_gate_action_ceilings(rule_library_path: Path, rule_scope: str) -> dict[str, int]:
    """Largest per-action decrease of each gate-name count in the scope.

    Mirrors ``per_gate_action_ceiling`` in
    ``scripts/derive_v15_certified_lower_bounds.py``: Quartz rules contribute
    their source-versus-target per-name count differences and the auxiliary
    ``pair_v1`` families contribute their fixed cancellation ceilings
    (``exchange`` actions are count-neutral).  The returned mapping is shared
    between callers and must not be mutated.
    """

    quartz = filter_rule_scope(_rule_library(rule_library_path)[0], rule_scope)
    ceilings: dict[str, int] = {}
    for rule in quartz:
        source = Counter(operation["name"] for operation in rule["source"]["operations"])
        target = Counter(operation["name"] for operation in rule["target"]["operations"])
        for name in set(source) | set(target):
            drop = max(0, source.get(name, 0) - target.get(name, 0))
            if drop > ceilings.get(name, 0):
                ceilings[name] = drop
    for name in _SELF_INVERSE:
        ceilings[name] = max(ceilings.get(name, 0), 2)
    for left, right in (("t", "tdg"), ("s", "sdg")):
        ceilings[left] = max(ceilings.get(left, 0), 1)
        ceilings[right] = max(ceilings.get(right, 0), 1)
    for name in _ROTATION_FAMILY:
        ceilings[name] = max(ceilings.get(name, 0), 2)
    return ceilings


def admissible_remaining_cost_lower_bound(
    state: LandscapeState,
    target_cost: int,
    remaining_actions_budget: int,
    *,
    rule_library_path: Path,
    rule_scope: str = "full",
) -> int:
    """Certified lower bound on the cost still reachable within an action budget.

    Returns a lower bound on the minimum listing cost reachable from
    ``state`` by at most ``remaining_actions_budget`` further legal actions in
    the declared scope.  The derivation is the certified bounded-decrease
    argument of ``scripts/derive_v15_certified_lower_bounds.py``.  With
    ``r_g`` the largest per-action decrease of the count ``n_g`` of gates
    named ``g`` over all legal actions in the scope (see
    :func:`_per_gate_action_ceilings`) and ``D`` the largest per-action total
    gate-count decrease (see :func:`_maximum_single_step_reduction`), every
    action of every H-step trajectory satisfies
    ``n_g(s_{i+1}) >= n_g(s_i) - r_g`` and ``cost(s_{i+1}) >= cost(s_i) - D``,
    hence

        cost(s_H) >= max( sum_g max(0, n_g(s_0) - H * r_g),   -- per name
                          cost(s_0) - H * D ),                -- aggregate

    which is the value returned for ``H = remaining_actions_budget`` (the
    same maximum of the per-gate and aggregate bounds that the derivation
    script reports).  The bound never overestimates the true remaining
    reduction: it credits each action with at most the largest single-action
    drop any legal action in scope can realize (per gate name, and in
    total), and it never credits reductions of gate names absent from the
    listing, so it cannot exceed the true minimum reachable cost and pruning
    on it can never discard an optimal path.  Once the accumulated per-name
    sum exceeds ``target_cost`` the remaining name terms cannot lower it
    (each is nonnegative), so the partial sum is returned immediately;
    callers only compare the result against ``target_cost``, and the partial
    sum still under-approximates the true reachable minimum, so every prune
    decision stays exact.
    """

    budget = max(0, int(remaining_actions_budget))
    ceilings = _per_gate_action_ceilings(rule_library_path, rule_scope)
    aggregate = _maximum_single_step_reduction(rule_library_path, rule_scope)
    total = state.cost - budget * aggregate
    if total > target_cost:
        # The aggregate bound alone already excludes the target; skip the
        # per-name scan.  The returned value stays admissible because every
        # action decreases the total gate count by at most ``aggregate``.
        return total
    bound = 0
    for name, count in Counter(gate.name for gate in state.gates).items():
        term = count - budget * ceilings.get(name, 0)
        if term > 0:
            bound += term
            if bound > target_cost:
                break
    return max(bound, total, 0)


def search_escape_idastar(
    initial: LandscapeState,
    rule_library_path: Path,
    horizon: int,
    state_budget: int | None = None,
    rule_scope: str = "full",
    time_budget_seconds: float | None = None,
) -> dict[str, Any]:
    """Find the shortest improving path with exact, fail-closed IDA*.

    The goal is any state with fewer gates than ``initial``.  IDA* iterates a
    depth limit and prunes only when the admissible gate-count lower bound or
    an exact transposition entry proves that the goal cannot be reached at that
    limit.  Repeated transitions are allowed within the finite depth bound;
    a fully explored failure is memoized by ``(state_hash, remaining_depth)``.
    Because successors and the goal predicate depend only on that pair, this
    reuse is exact and a complete run proves the minimum escape depth within
    the declared finite horizon.

    This helper reports escape depth only.  ``search_landscape_horizons`` and
    ``search_landscape_horizons_compact`` remain the APIs for the complete
    state-set, best-cost, and barrier certificates.
    """

    if horizon < 0:
        raise ValueError("horizon_must_be_nonnegative")
    initial = initial.normalized()
    try:
        _rule_library(rule_library_path)
        _quartz_index(rule_library_path, rule_scope)
        maximum_reduction = _maximum_single_step_reduction(rule_library_path, rule_scope)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "status": STATUS_INVALID_RULES,
            "failure_reason": f"{type(exc).__name__}:{exc}",
        }
    if initial.num_qubits < 1 or any(
        gate.name not in {"h", "x", "y", "z", "s", "sdg", "t", "tdg", "rx", "ry", "rz", "cx", "cz", "swap"}
        or any(q < 0 or q >= initial.num_qubits for q in gate.qubits)
        for gate in initial.gates
    ):
        return {"status": STATUS_UNSUPPORTED}

    def lower_bound(state: LandscapeState, target_cost: int, remaining: int) -> int:
        if state.cost <= target_cost:
            return 0
        if maximum_reduction <= 0:
            return math.inf  # type: ignore[return-value]
        coarse = int(math.ceil((state.cost - target_cost) / maximum_reduction))
        budget = max(0, remaining)
        if coarse > budget:
            # The coarse bound alone proves the prune; the refinement cannot
            # strengthen a value that already exceeds the remaining budget.
            return coarse
        # Per-gate certified refinement: the smallest step count H within the
        # remaining budget whose admissible bound already reaches the target.
        # The bound is non-increasing in H, so the predicate is monotone and a
        # binary search is exact.  Probing at min(budget, coarse) settles the
        # common case where the coarse bound already dominates with one call.
        steps = bound_cache.get((state.state_hash, budget))
        if steps is None:
            probe = min(budget, coarse)
            if admissible_remaining_cost_lower_bound(
                state, target_cost, probe,
                rule_library_path=rule_library_path, rule_scope=rule_scope,
            ) <= target_cost:
                steps = probe
            else:
                steps = budget + 1
                low, high = coarse + 1, budget
                while low <= high:
                    middle = (low + high) // 2
                    if admissible_remaining_cost_lower_bound(
                        state, target_cost, middle,
                        rule_library_path=rule_library_path, rule_scope=rule_scope,
                    ) <= target_cost:
                        steps = middle
                        high = middle - 1
                    else:
                        low = middle + 1
            bound_cache[(state.state_hash, budget)] = steps
        return coarse if coarse >= steps else steps

    target_cost = initial.cost - 1
    deadline = (
        time.perf_counter() + float(time_budget_seconds)
        if time_budget_seconds is not None
        else None
    )
    expanded = 0
    pruned = 0
    depth_iterations = 0
    resource_reason = ""
    resource_limited = False
    path: list[LandscapeAction] = []
    seen_states = {initial.state_hash}
    failed_transpositions: set[tuple[str, int]] = set()
    bound_cache: dict[tuple[str, int], int] = {}

    if horizon == 0 or maximum_reduction <= 0:
        result = {
            "status": STATUS_EXACT_LOCAL,
            "initial_state_sha256": initial.state_hash,
            "horizon": horizon,
            "state_budget": state_budget,
            "rule_scope": rule_scope,
            "baseline_cost": initial.cost,
            "escape_depth": None,
            "states_seen": 1,
            "expanded": 0,
            "pruned": 0,
            "depth_iterations": 0,
            "admissible_max_single_step_reduction": maximum_reduction,
            "resource_status": "COMPLETE",
            "exactness_status": "EXACT_FINITE_HORIZON",
            "resource_reason": "",
            "witnesses": {"escape": []},
            "no_improvement_explanations": ["H_INSUFFICIENT" if horizon > 0 else "RULE_LIBRARY_GAP"],
        }
        result["certificate_sha256"] = sha256_json(result)
        return result

    def depth_first(current: LandscapeState, depth: int, limit: int) -> list[LandscapeAction] | None:
        nonlocal expanded, pruned, resource_limited, resource_reason
        if deadline is not None and time.perf_counter() >= deadline:
            resource_limited = True
            resource_reason = "time_budget"
            return None
        if current.cost < initial.cost:
            return list(path)
        remaining = limit - depth
        transposition_key = (current.state_hash, remaining)
        if transposition_key in failed_transpositions:
            pruned += 1
            return None
        lower = lower_bound(current, target_cost, limit - depth)
        if depth + lower > limit:
            pruned += 1
            return None
        if depth >= limit or depth >= horizon:
            return None
        if state_budget is not None and expanded >= state_budget:
            resource_limited = True
            resource_reason = "state_budget"
            return None
        expanded += 1
        try:
            actions = iter_legal_actions(
                current, rule_library_path, rule_scope, deadline=deadline
            )
            for action in actions:
                child_hash = action.post_state_sha256
                if state_budget is not None and child_hash not in seen_states and len(seen_states) >= state_budget:
                    resource_limited = True
                    resource_reason = "state_budget"
                    return None
                path.append(action)
                seen_states.add(child_hash)
                found = depth_first(action.post_state, depth + 1, limit)
                if found is not None:
                    return found
                path.pop()
                if resource_limited:
                    return None
        except _SearchResourceLimit as exc:
            resource_limited = True
            resource_reason = exc.reason
        if not resource_limited:
            failed_transpositions.add(transposition_key)
        return None

    initial_limit = max(1, lower_bound(initial, target_cost, horizon))
    escape_path: list[LandscapeAction] | None = None
    limit = initial_limit
    while limit <= horizon:
        if deadline is not None and time.perf_counter() >= deadline:
            resource_limited = True
            resource_reason = "time_budget"
            break
        depth_iterations += 1
        path.clear()
        escape_path = depth_first(initial, 0, limit)
        if escape_path is not None or resource_limited:
            break
        limit += 1

    if resource_limited:
        status = STATUS_WITNESS_INCOMPLETE if escape_path else STATUS_RESOURCE_NO_WITNESS
    else:
        status = STATUS_EXACT_ESCAPE if escape_path else STATUS_EXACT_LOCAL
    result = {
        "status": status,
        "initial_state_sha256": initial.state_hash,
        "horizon": horizon,
        "state_budget": state_budget,
        "rule_scope": rule_scope,
        "baseline_cost": initial.cost,
        "escape_depth": len(escape_path) if escape_path is not None else None,
        "states_seen": len(seen_states),
        "expanded": expanded,
        "pruned": pruned,
        "depth_iterations": depth_iterations,
        "admissible_max_single_step_reduction": maximum_reduction,
        "resource_status": "TRUNCATED" if resource_limited else "COMPLETE",
        "exactness_status": "INCOMPLETE" if resource_limited else "EXACT_FINITE_HORIZON",
        "resource_reason": resource_reason,
        "witnesses": {"escape": [action.to_dict() for action in (escape_path or [])]},
        "no_improvement_explanations": [] if escape_path else (
            ["RESOURCE_TRUNCATED"] if resource_limited else ["H_INSUFFICIENT"]
        ),
    }
    result["certificate_sha256"] = sha256_json(result)
    return result


def search_landscape_horizons_compact(
    initial: LandscapeState,
    rule_library_path: Path,
    horizons: Iterable[int],
    state_budget: int | None = None,
    rule_scope: str = "full",
    time_budget_seconds: float | None = None,
) -> dict[str, dict[str, Any]]:
    """Exact finite-horizon BFS with bounded adjacency memory.

    This function has the same exact state and witness semantics as
    :func:`search_landscape_horizons`.  It keeps the state table and one parent
    action per discovered state, while barrier and terminal-greedy traversals
    regenerate legal actions on demand.  A resource budget still produces an
    incomplete status and never an exact local-optimum claim.
    """

    requested = tuple(sorted(set(int(horizon) for horizon in horizons)))
    if not requested or any(horizon < 0 for horizon in requested):
        raise ValueError("horizons_must_be_nonnegative_and_nonempty")
    initial = initial.normalized()
    try:
        _rule_library(rule_library_path)
        _quartz_index(rule_library_path, rule_scope)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            str(horizon): {
                "status": STATUS_INVALID_RULES,
                "failure_reason": f"{type(exc).__name__}:{exc}",
            }
            for horizon in requested
        }

    states: dict[str, LandscapeState] = {initial.state_hash: initial}
    distances: dict[str, int] = {initial.state_hash: 0}
    parents: dict[str, tuple[str, LandscapeAction]] = {}
    expanded_by_depth: Counter[int] = Counter()
    pruned_by_depth: Counter[int] = Counter()
    queue = deque([initial.state_hash])
    max_horizon = max(requested)
    resource_limited = False
    deadline = (
        time.perf_counter() + float(time_budget_seconds)
        if time_budget_seconds is not None
        else None
    )
    resource_reason = ""
    while queue:
        current_hash = queue.popleft()
        current = states[current_hash]
        depth = distances[current_hash]
        if depth >= max_horizon:
            continue
        if state_budget is not None and sum(expanded_by_depth.values()) >= state_budget:
            resource_limited = True
            resource_reason = "state_budget"
            pruned_by_depth[depth] += len(queue) + 1
            break
        if deadline is not None and time.perf_counter() >= deadline:
            resource_limited = True
            resource_reason = "time_budget"
            pruned_by_depth[depth] += len(queue) + 1
            break
        expanded_by_depth[depth] += 1
        try:
            actions = iter_legal_actions(
                current, rule_library_path, rule_scope, deadline=deadline
            )
            for action in actions:
                child_hash = action.post_state_sha256
                if child_hash not in states:
                    if state_budget is not None and len(states) >= state_budget:
                        resource_limited = True
                        resource_reason = "state_budget"
                        pruned_by_depth[depth] += 1
                        break
                    states[child_hash] = action.post_state
                    distances[child_hash] = depth + 1
                    parents[child_hash] = (current_hash, action)
                    queue.append(child_hash)
                else:
                    pruned_by_depth[depth] += 1
        except _SearchResourceLimit as exc:
            resource_limited = True
            resource_reason = exc.reason
        if resource_limited:
            break

    certificates: dict[str, dict[str, Any]] = {}
    for horizon in requested:
        visible = {
            state_hash: state
            for state_hash, state in states.items()
            if distances[state_hash] <= horizon
        }
        improving = [
            state
            for state_hash, state in visible.items()
            if distances[state_hash] > 0 and state.cost < initial.cost
        ]
        best = min(
            visible.values(),
            key=lambda state: (state.cost, distances[state.state_hash], state.state_hash),
        )
        escape_state = min(
            improving,
            key=lambda state: (
                distances[state.state_hash],
                _path_peak(initial, _path_from_parent(state.state_hash, parents)),
                state.state_hash,
            ),
            default=None,
        )
        escape_path = _path_from_parent(escape_state.state_hash, parents) if escape_state else []
        reached_cutoff = resource_limited
        barrier_timed_out = False
        if reached_cutoff:
            minimax_barrier = None
        else:
            minimax_barrier, barrier_timed_out = _minimax_barrier_compact(
                initial,
                horizon,
                rule_library_path,
                rule_scope,
                deadline,
            )
            if barrier_timed_out:
                resource_limited = True
                resource_reason = "time_budget"
                reached_cutoff = True
        if minimax_barrier is None:
            barrier_height = None
            barrier_path: list[LandscapeAction] = []
        else:
            barrier_height, barrier_path = minimax_barrier
        if reached_cutoff:
            greedy_path = []
        else:
            try:
                greedy_path = _greedy_trace_compact(
                    initial, rule_library_path, rule_scope, deadline
                )
            except _SearchResourceLimit as exc:
                resource_limited = True
                resource_reason = exc.reason
                reached_cutoff = True
                greedy_path = []
        if reached_cutoff:
            status = STATUS_WITNESS_INCOMPLETE if escape_state else STATUS_RESOURCE_NO_WITNESS
        else:
            status = STATUS_EXACT_ESCAPE if escape_state else STATUS_EXACT_LOCAL
        certificate = {
            "status": status,
            "initial_state_sha256": initial.state_hash,
            "horizon": horizon,
            "state_budget": state_budget,
            "rule_scope": rule_scope,
            "baseline_cost": initial.cost,
            "best_cost": best.cost,
            "best_state_sha256": best.state_hash,
            "escape_depth": distances[escape_state.state_hash] if escape_state else None,
            "barrier_height": barrier_height,
            "states_seen": len(visible),
            "expanded": sum(expanded_by_depth[depth] for depth in range(horizon)),
            "pruned": sum(pruned_by_depth[depth] for depth in range(horizon)),
            "state_set_sha256": hashlib.sha256("\n".join(sorted(visible)).encode()).hexdigest(),
            "state_hashes": sorted(visible),
            "witnesses": {
                "escape": [action.to_dict() for action in escape_path],
                "barrier": [action.to_dict() for action in barrier_path],
                "greedy": [action.to_dict() for action in greedy_path],
            },
            "semantic_status": "NOT_REPLAYED",
            "resource_status": "TRUNCATED" if reached_cutoff else "COMPLETE",
            "resource_reason": resource_reason,
            "exactness_status": "INCOMPLETE" if reached_cutoff else "EXACT_FINITE_HORIZON",
            "no_improvement_explanations": [] if escape_state else (
                ["RESOURCE_TRUNCATED"] if reached_cutoff else [
                    "H_INSUFFICIENT" if horizon > 0 else "RULE_LIBRARY_GAP"
                ]
            ),
        }
        certificate["certificate_sha256"] = sha256_json(certificate)
        certificates[str(horizon)] = certificate
    return certificates


def replay_actions(
    initial: LandscapeState,
    actions: Iterable[Mapping[str, Any]],
    rule_library_path: Path,
    rule_scope: str = "full",
) -> dict[str, Any]:
    current = initial.normalized()
    replayed = []
    try:
        for record in actions:
            if record["pre_state_sha256"] != current.state_hash:
                return {"accepted": False, "reason": "pre_state_hash_mismatch", "steps": replayed}
            rule_id = str(record["rule_id"])
            location = int(record["location"])
            candidates: Iterable[LandscapeAction]
            quartz_rule = _quartz_rule_by_id(rule_library_path, rule_scope).get(rule_id)
            if quartz_rule is not None:
                signature, rule = quartz_rule
                gate_names = tuple(gate.name for gate in current.gates)
                if (
                    location < 0
                    or location + len(signature) > len(gate_names)
                    or gate_names[location:location + len(signature)] != signature
                ):
                    candidates = ()
                else:
                    candidates = sorted(
                        _iter_quartz_rule_actions(current, rule, location),
                        key=lambda action: action.sort_key,
                    )
            elif rule_id.startswith("pair_v1."):
                candidates = _iter_pair_actions(
                    current,
                    only_rule_id=rule_id,
                    only_location=location,
                )
            elif rule_id.startswith("exchange."):
                candidates = _iter_exchange_actions(
                    current,
                    only_rule_id=rule_id,
                    only_location=location,
                )
            else:
                candidates = ()
            match = next(
                (action for action in candidates if action.rule_id == rule_id
                 and action.post_state_sha256 == record["post_state_sha256"]),
                None,
            )
            if match is None or not _action_semantically_equivalent(current, match, rule_library_path, rule_scope):
                return {"accepted": False, "reason": "action_or_semantic_mismatch", "steps": replayed}
            replayed.append(match.to_dict())
            current = match.post_state
        return {"accepted": True, "steps": replayed, "final_state_sha256": current.state_hash}
    except (KeyError, ValueError, IndexError, TypeError) as exc:
        return {"accepted": False, "reason": f"{type(exc).__name__}:{exc}", "steps": replayed}


def _action_semantically_equivalent(
    state: LandscapeState,
    action: LandscapeAction,
    rule_library_path: Path,
    rule_scope: str,
) -> bool:
    """Check the rewritten window instead of reunitarizing the full listing."""

    if action.family == "quartz_v1":
        quartz_rule = _quartz_rule_by_id(rule_library_path, rule_scope).get(action.rule_id)
        if quartz_rule is None:
            return False
        consumed = len(quartz_rule[1]["source"]["operations"])
    elif action.family in {"pair_v1", "structural_exchange_v1"}:
        consumed = 2
    else:
        return False
    location = action.location
    if location < 0 or location + consumed > len(state.gates):
        return False
    target_count = len(action.post_state.gates) - (len(state.gates) - consumed)
    if target_count < 0 or location + target_count > len(action.post_state.gates):
        return False
    left_gates = state.gates[location:location + consumed]
    right_gates = action.post_state.gates[location:location + target_count]
    used_qubits = sorted({q for gate in (*left_gates, *right_gates) for q in gate.qubits})
    if not used_qubits:
        return True
    remap = {qubit: index for index, qubit in enumerate(used_qubits)}

    def local_state(gates: Iterable[StateGate]) -> LandscapeState:
        return LandscapeState(
            len(used_qubits),
            tuple(
                StateGate(gate.name, tuple(remap[q] for q in gate.qubits), gate.angle)
                for gate in gates
            ),
        )

    return semantically_equivalent(local_state(left_gates), local_state(right_gates))


__all__ = [
    "LandscapeAction",
    "LandscapeState",
    "StateGate",
    "STATUS_EXACT_ESCAPE",
    "STATUS_EXACT_LOCAL",
    "STATUS_INVALID_RULES",
    "STATUS_RESOURCE_NO_WITNESS",
    "STATUS_SEMANTIC_FAILURE",
    "STATUS_UNSUPPORTED",
    "STATUS_WITNESS_INCOMPLETE",
    "admissible_remaining_cost_lower_bound",
    "filter_rule_scope",
    "iter_legal_actions",
    "legal_actions",
    "normalize_angle",
    "replay_actions",
    "search_escape_idastar",
    "search_landscape",
    "search_landscape_horizons",
    "search_landscape_horizons_compact",
    "semantically_equivalent",
    "sha256_json",
    "state_from_spec",
    "state_unitary",
    "state_wcl",
]
