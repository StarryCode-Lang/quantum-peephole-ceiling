"""Core state-space search for the v13 certified rewrite landscape.

This module is intentionally independent of the v12 exposure solver.  It
operates on concrete, normalized gate listings and treats every transition as
a proof-carrying local replacement.  Exact mode is finite-horizon BFS with a
separate barrier-threshold enumeration; bounded mode never reports a local
optimum.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
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


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


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


@dataclass(frozen=True)
class LandscapeState:
    num_qubits: int
    gates: tuple[StateGate, ...]

    def normalized(self) -> "LandscapeState":
        return LandscapeState(
            self.num_qubits,
            tuple(
                StateGate(gate.name, tuple(gate.qubits), None if gate.angle is None else normalize_angle(gate.angle))
                for gate in self.gates
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"num_qubits": self.num_qubits, "gates": [gate.to_dict() for gate in self.gates]}

    @cached_property
    def key(self) -> str:
        return _canonical_bytes(self.normalized().to_dict()).decode()

    @cached_property
    def state_hash(self) -> str:
        return hashlib.sha256(self.key.encode()).hexdigest()

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


@lru_cache(maxsize=8)
def _quartz_index(path: Path, rule_scope: str = "full") -> dict[tuple[str, ...], tuple[dict[str, Any], ...]]:
    quartz, _ = _rule_library(path)
    if rule_scope == "e44_core_v1":
        quartz = [
            rule for rule in quartz
            if int(rule["source"]["num_qubits"]) <= 2
            and len(rule["source"]["operations"]) <= 4
            and len(rule["target"]["operations"]) <= 6
        ]
    elif rule_scope != "full":
        raise ValueError(f"unknown_rule_scope:{rule_scope}")
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


def _map_binding(mapping: Mapping[int, int], source_values: Mapping[str, float], target_values: Mapping[str, float]) -> str:
    return json.dumps(
        {
            "qubits": [[f"Q{key}", int(value)] for key, value in sorted(mapping.items())],
            "parameters": [[key, format(float(value), ".17g")] for key, value in sorted(target_values.items())],
            "source_parameters": [[key, format(float(value), ".17g")] for key, value in sorted(source_values.items())],
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _quartz_actions(
    state: LandscapeState,
    rules_by_first_name: Mapping[str, tuple[tuple[tuple[str, ...], tuple[dict[str, Any], ...]], ...]],
) -> list[LandscapeAction]:
    actions: list[LandscapeAction] = []
    for location in range(len(state.gates)):
        for source_names, rules in rules_by_first_name.get(state.gates[location].name, ()):
            if location + len(source_names) > len(state.gates):
                continue
            if tuple(gate.name for gate in state.gates[location:location + len(source_names)]) != source_names:
                continue
            for rule in rules:
                source = rule["source"]
                target = rule["target"]
                source_ops = source["operations"]
                if int(source["num_qubits"]) > state.num_qubits:
                    continue
                for actual_qubits in itertools.permutations(range(state.num_qubits), int(source["num_qubits"])):
                    mapping = dict(enumerate(actual_qubits))
                    source_values: dict[str, float] = {}
                    valid = True
                    for template_operation, actual_gate in zip(source_ops, state.gates[location:location + len(source_ops)]):
                        expected_qubits = tuple(mapping[int(q)] for q in template_operation["qubits"])
                        if actual_gate.qubits != expected_qubits:
                            valid = False
                            break
                        for parameter in template_operation.get("params", []):
                            if actual_gate.angle is None:
                                valid = False
                                break
                            value = normalize_angle(actual_gate.angle)
                            if parameter in source_values and not angles_equal(source_values[parameter], value):
                                valid = False
                                break
                            source_values[parameter] = value
                        if not valid:
                            break
                    if not valid:
                        continue
                    target_values = {
                        parameter: normalize_angle(sum(
                            int(coefficient) * source_values[label]
                            for label, coefficient in expression.items()
                        ))
                        for parameter, expression in rule.get("parameter_binding", {}).items()
                    }
                    replacement = []
                    for operation in target["operations"]:
                        params = operation.get("params", [])
                        replacement.append(
                            StateGate(
                                operation["name"],
                                tuple(mapping[int(q)] for q in operation["qubits"]),
                                None if not params else target_values[params[0]],
                            )
                        )
                    post = LandscapeState(
                        state.num_qubits,
                        state.gates[:location] + tuple(replacement) + state.gates[location + len(source_ops):],
                    ).normalized()
                    if post.state_hash == state.state_hash:
                        continue
                    binding = _map_binding(mapping, source_values, target_values)
                    actions.append(LandscapeAction(
                        rule_id=rule["rule_id"], family="quartz_v1", location=location,
                        binding=binding, pre_state_sha256=state.state_hash,
                        post_state_sha256=post.state_hash, local_proof_hash=rule["symbolic_proof_hash"],
                        post_state=post, cost_delta=post.cost - state.cost,
                    ))
    return actions


_SELF_INVERSE = frozenset({"h", "x", "y", "z", "cx", "cz", "swap"})
_Z_FAMILY = frozenset({"z", "rz", "s", "sdg", "t", "tdg"})
_X_FAMILY = frozenset({"x", "rx"})


def _pair_action(state: LandscapeState, location: int, rule_id: str, replacement: Iterable[StateGate], proof: str) -> LandscapeAction:
    post = LandscapeState(
        state.num_qubits,
        state.gates[:location] + tuple(replacement) + state.gates[location + 2:],
    ).normalized()
    return LandscapeAction(
        rule_id=rule_id, family="pair_v1", location=location, binding="{}",
        pre_state_sha256=state.state_hash, post_state_sha256=post.state_hash,
        local_proof_hash=proof, post_state=post, cost_delta=post.cost - state.cost,
    )


def _pair_actions(state: LandscapeState) -> list[LandscapeAction]:
    actions = []
    for location, (left, right) in enumerate(zip(state.gates, state.gates[1:])):
        if left.qubits == right.qubits and left.name == right.name and left.name in _SELF_INVERSE:
            actions.append(_pair_action(state, location, "pair_v1.self_inverse", (), "pair_v1.self_inverse"))
        elif left.qubits == right.qubits and {left.name, right.name} == {"t", "tdg"}:
            actions.append(_pair_action(state, location, "pair_v1.t_tdg", (), "pair_v1.t_tdg"))
        elif left.qubits == right.qubits and {left.name, right.name} == {"s", "sdg"}:
            actions.append(_pair_action(state, location, "pair_v1.s_sdg", (), "pair_v1.s_sdg"))
        elif left.qubits == right.qubits and left.name == right.name and left.name in {"rx", "ry", "rz"}:
            angle = normalize_angle((left.angle or 0.0) + (right.angle or 0.0))
            rule_id = "pair_v1.rotation_zero" if abs(angle) <= ANGLE_TOLERANCE else "pair_v1.rotation_merge"
            replacement = () if rule_id.endswith("zero") else (StateGate(left.name, left.qubits, angle),)
            actions.append(_pair_action(state, location, rule_id, replacement, rule_id))
    return actions


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
    actions = []
    proof_by_rule = {rule: rule for rule in (
        "exchange.disjoint", "exchange.same_single", "exchange.same_axis_rotation", "exchange.z_family",
        "exchange.cx_control_z", "exchange.cx_target_x", "exchange.cz_z", "exchange.same_swap", "exchange.same_cz"
    )}
    for location, (left, right) in enumerate(zip(state.gates, state.gates[1:])):
        classification = _commutes(left, right)
        if classification is None:
            continue
        rule_id, _ = classification
        post = LandscapeState(
            state.num_qubits,
            state.gates[:location] + (right, left) + state.gates[location + 2:],
        ).normalized()
        if post.state_hash == state.state_hash:
            continue
        actions.append(LandscapeAction(
            rule_id=rule_id, family="structural_exchange_v1", location=location,
            binding="{}", pre_state_sha256=state.state_hash,
            post_state_sha256=post.state_hash, local_proof_hash=proof_by_rule[rule_id],
            post_state=post, cost_delta=0,
        ))
    return actions


def legal_actions(
    state: LandscapeState,
    rule_library_path: Path,
    rule_scope: str = "full",
) -> list[LandscapeAction]:
    actions = _quartz_actions(state, _quartz_first_index(rule_library_path, rule_scope)) + _pair_actions(state) + _exchange_actions(state)
    dedup: dict[tuple[Any, ...], LandscapeAction] = {}
    for action in actions:
        dedup[action.sort_key] = action
    return sorted(dedup.values(), key=lambda action: action.sort_key)


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
            candidates = legal_actions(current, rule_library_path, rule_scope)
            match = next(
                (action for action in candidates if action.rule_id == record["rule_id"]
                 and action.location == int(record["location"])
                 and action.post_state_sha256 == record["post_state_sha256"]),
                None,
            )
            if match is None or not semantically_equivalent(current, match.post_state):
                return {"accepted": False, "reason": "action_or_semantic_mismatch", "steps": replayed}
            replayed.append(match.to_dict())
            current = match.post_state
        return {"accepted": True, "steps": replayed, "final_state_sha256": current.state_hash}
    except (KeyError, ValueError, IndexError, TypeError) as exc:
        return {"accepted": False, "reason": f"{type(exc).__name__}:{exc}", "steps": replayed}


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
    "legal_actions",
    "normalize_angle",
    "replay_actions",
    "search_landscape",
    "search_landscape_horizons",
    "semantically_equivalent",
    "sha256_json",
    "state_from_spec",
    "state_unitary",
]
