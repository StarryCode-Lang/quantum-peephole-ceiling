"""Certified exposure of supported rewrite opportunities.

This module studies a deliberately narrower question than circuit
optimization: for a fixed unitary gate listing, which supported inverse or
mergeable pairs can be made adjacent by a legal topological reorder?  The
answer is represented as a certificate with a constructive lower bound and a
matching upper bound.  ``CertificateGuidedPreprocessor`` materializes the
selected pairs as a deterministic topological listing (CGL).

The implementation is fail-closed.  Measurements, resets, control flow,
delays, free parameters, classical operands, and malformed instructions are
not silently treated as unitary gates.  Unknown overlapping gates are retained
as dependency barriers in the conservative model; they are never assumed to
commute.

The theorem statements motivating this module are intentionally labelled as
draft/conjectural until E38 has compared the implementation with an exhaustive
small-instance oracle.
"""

from __future__ import annotations

import copy
import hashlib
import heapq
import itertools
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
from qiskit import QuantumCircuit

from ._gate_predicates import gates_commute


PAIR_RULE_LIBRARY = "pair_v1"
PAIR_TOLERANCE = 1e-10
DEFAULT_EXACT_CANDIDATE_LIMIT = 24
DEFAULT_EXACT_NODE_BUDGET = 1_000_000
DEFAULT_CANDIDATE_CAP = 256
DEFAULT_BEAM_WIDTH = 8
DEFAULT_OVERLAP_CHECK_BUDGET = 20_000_000


class DependenceModel(str, Enum):
    """Dependency contract used to define legal listing reorderings."""

    WIRE_ORDER_V1 = "wire_order_v1"
    CONSERVATIVE_COMMUTATION_V1 = "conservative_commutation_v1"


class CertificateStatus(str, Enum):
    """Fail-closed status of an exposure certificate."""

    EXACT_ZERO = "exact_zero"
    EXACT = "exact"
    BOUNDED = "bounded"
    TRUNCATED = "truncated"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ExposureConfig:
    """Deterministic solver and scope configuration."""

    dependence_model: DependenceModel | str = DependenceModel.WIRE_ORDER_V1
    rule_library: str = PAIR_RULE_LIBRARY
    candidate_cap: int = DEFAULT_CANDIDATE_CAP
    beam_width: int = DEFAULT_BEAM_WIDTH
    exact_node_budget: int = DEFAULT_EXACT_NODE_BUDGET
    overlap_check_budget: int = DEFAULT_OVERLAP_CHECK_BUDGET
    tolerance: float = PAIR_TOLERANCE

    def normalized(self) -> "ExposureConfig":
        model = DependenceModel(self.dependence_model)
        if self.rule_library != PAIR_RULE_LIBRARY:
            raise ValueError(f"unsupported_rule_library:{self.rule_library}")
        if self.candidate_cap < 1:
            raise ValueError("candidate_cap_must_be_positive")
        if self.beam_width < 1:
            raise ValueError("beam_width_must_be_positive")
        if self.exact_node_budget < 1:
            raise ValueError("exact_node_budget_must_be_positive")
        if self.overlap_check_budget < 1:
            raise ValueError("overlap_check_budget_must_be_positive")
        if not math.isfinite(float(self.tolerance)) or self.tolerance <= 0:
            raise ValueError("tolerance_must_be_positive_finite")
        return ExposureConfig(
            dependence_model=model,
            rule_library=self.rule_library,
            candidate_cap=int(self.candidate_cap),
            beam_width=int(self.beam_width),
            exact_node_budget=int(self.exact_node_budget),
            overlap_check_budget=int(self.overlap_check_budget),
            tolerance=float(self.tolerance),
        )


@dataclass(frozen=True)
class RewriteCandidate:
    """One supported endpoint pair in the original listing."""

    left_index: int
    right_index: int
    rule_id: str
    reduction_weight: int
    pairwise_exposable: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExposureCertificate:
    """Evidence returned by :func:`certify_rewrite_exposure`."""

    input_sha256: str
    dependence_model: str
    rule_library: str
    current_exposed_weight: int
    constructive_lower_bound: int
    matching_upper_bound: int
    exact_optimum: int | None
    status: str
    selected_pairs: list[dict[str, Any]]
    listing_order: list[int]
    candidate_count: int
    discarded_candidate_count: int
    search_nodes: int
    source_hashes: dict[str, str]
    failure_reason: str | None
    fallback_reason: str | None = None
    solver: str = ""
    listing_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


_SELF_INVERSE = frozenset({"h", "x", "y", "z", "cx", "cz", "swap"})
_DYNAMIC_OR_NONUNITARY = frozenset({
    "measure", "reset", "initialize", "delay", "if_else", "while_loop", "for_loop",
    "switch_case", "store", "load", "break_loop", "continue_loop",
})
_KNOWN_COMMUTATION_GATES = frozenset({
    "h", "x", "y", "z", "cx", "cz", "swap", "t", "tdg", "s", "sdg",
    "rx", "ry", "rz", "p", "u1",
})


def _qubit_indices(circuit: QuantumCircuit, instruction: Any) -> list[int]:
    try:
        return [circuit.find_bit(q).index for q in instruction.qubits]
    except Exception:
        return []


def _clbit_indices(circuit: QuantumCircuit, instruction: Any) -> list[int]:
    try:
        return [circuit.find_bit(c).index for c in instruction.clbits]
    except Exception:
        return []


def _canonical_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return {"array": [_canonical_value(v) for v in value.tolist()]}
    if isinstance(value, np.generic):
        return _canonical_value(value.item())
    if isinstance(value, complex):
        return {"complex": [repr(float(value.real)), repr(float(value.imag))]}
    if isinstance(value, (float, int, bool, str)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_canonical_value(v) for v in value]
    return repr(value)


def _canonical_parameter(parameter: Any) -> Any:
    free = getattr(parameter, "parameters", None)
    if free:
        return {"free_parameter": str(parameter)}
    try:
        return {"float": repr(float(parameter))}
    except (TypeError, ValueError):
        return _canonical_value(parameter)


def _input_payload(circuit: QuantumCircuit) -> dict[str, Any]:
    instructions = []
    for index, instruction in enumerate(circuit.data):
        operation = instruction.operation
        instructions.append({
            "index": index,
            "name": getattr(operation, "name", type(operation).__name__),
            "qubits": _qubit_indices(circuit, instruction),
            "clbits": _clbit_indices(circuit, instruction),
            "num_qubits": getattr(operation, "num_qubits", None),
            "num_clbits": getattr(operation, "num_clbits", None),
            "params": [
                _canonical_parameter(parameter)
                for parameter in getattr(operation, "params", [])
            ],
        })
    return {
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "global_phase": _canonical_parameter(circuit.global_phase),
        "instructions": instructions,
    }


def _input_sha256(circuit: QuantumCircuit) -> str:
    encoded = json.dumps(
        _input_payload(circuit),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _listing_sha256(listing_order: Iterable[int]) -> str:
    encoded = json.dumps(list(listing_order), separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _adjacent_matching_weight(
    circuit: QuantumCircuit,
    listing_order: Iterable[int],
    tolerance: float,
) -> int:
    """Maximum weight of endpoint-disjoint supported pairs in one listing."""
    order = list(listing_order)
    best_without_previous = 0
    best_through_previous = 0
    for position in range(1, len(order)):
        rule = _pair_rule(circuit, order[position - 1], order[position], tolerance)
        edge_weight = rule[1] if rule is not None else 0
        best_without_previous, best_through_previous = (
            best_through_previous,
            max(best_through_previous, best_without_previous + edge_weight),
        )
    return best_through_previous


def _source_hashes() -> dict[str, str]:
    result: dict[str, str] = {}
    module_path = Path(__file__).resolve()
    for path in (module_path, module_path.with_name("base.py"), module_path.with_name("_gate_predicates.py")):
        if path.is_file():
            result[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _scope_failure(circuit: Any) -> str | None:
    if not isinstance(circuit, QuantumCircuit):
        return "input_is_not_qiskit_quantum_circuit"
    if getattr(circuit, "parameters", None):
        return "free_parameters_are_out_of_scope"
    for index, instruction in enumerate(circuit.data):
        operation = instruction.operation
        name = getattr(operation, "name", "")
        if name == "barrier":
            continue
        if name in _DYNAMIC_OR_NONUNITARY:
            return f"unsupported_dynamic_or_nonunitary_instruction:{index}:{name}"
        if getattr(operation, "condition", None) is not None:
            return f"conditional_instruction_is_out_of_scope:{index}:{name}"
        if instruction.clbits or getattr(operation, "num_clbits", 0):
            return f"classical_operand_is_out_of_scope:{index}:{name}"
        if not instruction.qubits:
            return f"zero_support_instruction:{index}:{name}"
        if len(instruction.qubits) != getattr(operation, "num_qubits", len(instruction.qubits)):
            return f"malformed_qubit_arity:{index}:{name}"
    return None


def _angle_mod_two_pi(angle: float) -> float:
    return (float(angle) + math.pi) % (2.0 * math.pi) - math.pi


def _pair_rule(
    circuit: QuantumCircuit,
    left_index: int,
    right_index: int,
    tolerance: float,
) -> tuple[str, int] | None:
    left = circuit.data[left_index]
    right = circuit.data[right_index]
    left_name = left.operation.name
    right_name = right.operation.name
    if left_name == "barrier" or right_name == "barrier":
        return None
    # pair_v1 is operand-order sensitive.  In particular, reversed qargs are
    # not silently treated as the same rule.
    if _qubit_indices(circuit, left) != _qubit_indices(circuit, right):
        return None
    if left_name == right_name and left_name in _SELF_INVERSE:
        return "pair_v1.self_inverse", 2
    if {left_name, right_name} == {"t", "tdg"}:
        return "pair_v1.t_tdg", 2
    if {left_name, right_name} == {"s", "sdg"}:
        return "pair_v1.s_sdg", 2
    if left_name == right_name and left_name in {"rx", "ry", "rz"}:
        params_left = getattr(left.operation, "params", [])
        params_right = getattr(right.operation, "params", [])
        if not params_left or not params_right:
            return None
        try:
            angle_sum = float(params_left[0]) + float(params_right[0])
        except (TypeError, ValueError):
            return None
        if abs(_angle_mod_two_pi(angle_sum)) <= tolerance:
            return "pair_v1.rotation_zero", 2
        return "pair_v1.rotation_merge", 1
    return None


def _candidate_pairs(circuit: QuantumCircuit, tolerance: float) -> list[RewriteCandidate]:
    """Enumerate pair rules through operand/name buckets, not all gate pairs."""
    buckets: dict[tuple[str, tuple[int, ...]], list[int]] = defaultdict(list)
    for index, instruction in enumerate(circuit.data):
        name = instruction.operation.name
        if name == "barrier" or name not in _KNOWN_COMMUTATION_GATES:
            continue
        buckets[(name, tuple(_qubit_indices(circuit, instruction)))].append(index)

    pairs: set[tuple[int, int]] = set()
    for (name, qargs), indices in buckets.items():
        if name in _SELF_INVERSE or name in {"rx", "ry", "rz"}:
            pairs.update(itertools.combinations(indices, 2))
    for inverse_names in (("t", "tdg"), ("s", "sdg")):
        for qargs in sorted({q for n, q in buckets if n in inverse_names}):
            pairs.update(
                (left, right)
                for left in buckets.get((inverse_names[0], qargs), [])
                for right in buckets.get((inverse_names[1], qargs), [])
                if left != right
            )

    candidates: list[RewriteCandidate] = []
    for left_index, right_index in sorted((min(a, b), max(a, b)) for a, b in pairs):
        rule = _pair_rule(circuit, left_index, right_index, tolerance)
        if rule is not None:
            candidates.append(RewriteCandidate(
                left_index=left_index,
                right_index=right_index,
                rule_id=rule[0],
                reduction_weight=rule[1],
                pairwise_exposable=False,
            ))
    return candidates


def _add_edge(edges: list[set[int]], left: int, right: int) -> None:
    if left != right:
        edges[left].add(right)


def _wire_edges(circuit: QuantumCircuit) -> list[set[int]]:
    n = len(circuit.data)
    edges = [set() for _ in range(n)]
    last_on_wire: dict[int, int] = {}
    for index, instruction in enumerate(circuit.data):
        for qubit in _qubit_indices(circuit, instruction):
            previous = last_on_wire.get(qubit)
            if previous is not None:
                _add_edge(edges, previous, index)
            last_on_wire[qubit] = index
    _add_barrier_fences(circuit, edges)
    return edges


def _add_barrier_fences(circuit: QuantumCircuit, edges: list[set[int]]) -> None:
    barriers = [i for i, instruction in enumerate(circuit.data) if instruction.operation.name == "barrier"]
    for barrier in barriers:
        for before in range(barrier):
            _add_edge(edges, before, barrier)
        for after in range(barrier + 1, len(circuit.data)):
            _add_edge(edges, barrier, after)


def _known_commute(circuit: QuantumCircuit, left: Any, right: Any) -> bool:
    left_name = left.operation.name
    right_name = right.operation.name
    left_qubits = set(_qubit_indices(circuit, left))
    right_qubits = set(_qubit_indices(circuit, right))
    if left_qubits.isdisjoint(right_qubits):
        return True
    # Unknown overlapping operations are never assumed to commute.
    if left_name not in _KNOWN_COMMUTATION_GATES or right_name not in _KNOWN_COMMUTATION_GATES:
        return False
    try:
        return bool(gates_commute(circuit, left, right))
    except Exception:
        return False


def _dependency_edges(
    circuit: QuantumCircuit,
    requested_model: DependenceModel,
    overlap_check_budget: int,
) -> tuple[list[set[int]], DependenceModel, str | None, int]:
    if requested_model == DependenceModel.WIRE_ORDER_V1:
        return _wire_edges(circuit), requested_model, None, 0

    n = len(circuit.data)
    edges = [set() for _ in range(n)]
    overlap_checks = 0
    for right_index in range(n):
        right = circuit.data[right_index]
        right_support = set(_qubit_indices(circuit, right))
        for left_index in range(right_index):
            left = circuit.data[left_index]
            if left.operation.name == "barrier" or right.operation.name == "barrier":
                continue
            left_support = set(_qubit_indices(circuit, left))
            if left_support.isdisjoint(right_support):
                continue
            overlap_checks += 1
            if overlap_checks > overlap_check_budget:
                reason = (
                    "conservative_overlap_check_budget_exceeded:"
                    f"{overlap_check_budget}"
                )
                return _wire_edges(circuit), DependenceModel.WIRE_ORDER_V1, reason, overlap_checks
            if not _known_commute(circuit, left, right):
                _add_edge(edges, left_index, right_index)
    _add_barrier_fences(circuit, edges)
    return edges, requested_model, None, overlap_checks


def _all_pairs_reference_edges(
    circuit: QuantumCircuit,
    model: DependenceModel,
) -> list[set[int]]:
    """Build the dense all-pairs reference DAG used only by small oracles.

    The production path uses the linear wire scan or the budgeted overlap
    scan.  This intentionally simpler implementation is retained as an
    independent reference for E38; it has no overlap budget and is not used
    by the public certificate function.
    """
    n = len(circuit.data)
    edges = [set() for _ in range(n)]
    for left_index in range(n):
        left = circuit.data[left_index]
        left_support = set(_qubit_indices(circuit, left))
        for right_index in range(left_index + 1, n):
            right = circuit.data[right_index]
            if left.operation.name == "barrier" or right.operation.name == "barrier":
                continue
            right_support = set(_qubit_indices(circuit, right))
            if left_support.isdisjoint(right_support):
                continue
            if model == DependenceModel.WIRE_ORDER_V1 or not _known_commute(circuit, left, right):
                _add_edge(edges, left_index, right_index)
    _add_barrier_fences(circuit, edges)
    return edges


def _transitive_closure(edges: list[set[int]]) -> tuple[list[int], list[int]]:
    n = len(edges)
    descendants = [0] * n
    for left in range(n - 1, -1, -1):
        mask = 0
        for right in edges[left]:
            mask |= (1 << right) | descendants[right]
        descendants[left] = mask
    ancestors = [0] * n
    for left in range(n):
        for right in edges[left]:
            ancestors[right] |= (1 << left) | ancestors[left]
    return descendants, ancestors


def _pairwise_exposable(
    candidate: RewriteCandidate,
    descendants: list[int],
    ancestors: list[int],
) -> bool:
    left = candidate.left_index
    right = candidate.right_index
    if (descendants[left] >> right) & 1:
        between = descendants[left] & ancestors[right]
        return (between & ~(1 << left) & ~(1 << right)) == 0
    if (descendants[right] >> left) & 1:
        between = descendants[right] & ancestors[left]
        return (between & ~(1 << left) & ~(1 << right)) == 0
    return True


def _rank_candidates(candidates: list[RewriteCandidate]) -> list[RewriteCandidate]:
    endpoint_frequency = Counter(
        endpoint
        for candidate in candidates
        for endpoint in (candidate.left_index, candidate.right_index)
    )

    def key(candidate: RewriteCandidate) -> tuple[Any, ...]:
        conflicts = endpoint_frequency[candidate.left_index] + endpoint_frequency[candidate.right_index] - 2
        return (
            -candidate.reduction_weight,
            conflicts,
            candidate.right_index - candidate.left_index,
            candidate.left_index,
            candidate.right_index,
            candidate.rule_id,
        )

    return sorted(candidates, key=key)


def _quotient_is_acyclic(
    n: int,
    edges: list[set[int]],
    selected: list[RewriteCandidate],
) -> bool:
    # Use an explicit -1 sentinel.  Block ids are dense and must not be
    # confused with original instruction indices (a selected pair may have
    # block id 0 while instruction 0 is a singleton).
    block_of = [-1] * n
    block_members: list[list[int]] = []
    for candidate in sorted(selected, key=lambda item: (item.left_index, item.right_index, item.rule_id)):
        block = len(block_members)
        members = [candidate.left_index, candidate.right_index]
        block_members.append(sorted(members))
        for member in members:
            block_of[member] = block
    for node in range(n):
        if block_of[node] == -1:
            block_of[node] = len(block_members)
            block_members.append([node])

    quotient_edges = [set() for _ in block_members]
    indegree = [0] * len(block_members)
    for left, successors in enumerate(edges):
        for right in successors:
            left_block = block_of[left]
            right_block = block_of[right]
            if left_block == right_block:
                continue
            if right_block not in quotient_edges[left_block]:
                quotient_edges[left_block].add(right_block)
                indegree[right_block] += 1

    heap = []
    minima = [min(members) for members in block_members]
    for block, degree in enumerate(indegree):
        if degree == 0:
            heapq.heappush(heap, (minima[block], block))
    visited = 0
    while heap:
        _, block = heapq.heappop(heap)
        visited += 1
        for successor in quotient_edges[block]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(heap, (minima[successor], successor))
    return visited == len(block_members)


def _materialize_order(n: int, edges: list[set[int]], selected: list[RewriteCandidate]) -> list[int]:
    block_of = [-1] * n
    block_members: list[list[int]] = []
    for candidate in sorted(selected, key=lambda item: (item.left_index, item.right_index, item.rule_id)):
        block = len(block_members)
        members = [candidate.left_index, candidate.right_index]
        block_members.append(sorted(members))
        for member in members:
            block_of[member] = block
    for node in range(n):
        if block_of[node] == -1:
            block_of[node] = len(block_members)
            block_members.append([node])

    quotient_edges = [set() for _ in block_members]
    indegree = [0] * len(block_members)
    for left, successors in enumerate(edges):
        for right in successors:
            left_block = block_of[left]
            right_block = block_of[right]
            if left_block == right_block:
                continue
            if right_block not in quotient_edges[left_block]:
                quotient_edges[left_block].add(right_block)
                indegree[right_block] += 1

    minimum = [min(members) for members in block_members]
    heap = [(minimum[block], block) for block, degree in enumerate(indegree) if degree == 0]
    heapq.heapify(heap)
    order: list[int] = []
    while heap:
        _, block = heapq.heappop(heap)
        order.extend(block_members[block])
        for successor in sorted(quotient_edges[block]):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(heap, (minimum[successor], successor))
    if len(order) != n:
        raise ValueError("selected_pairs_do_not_form_acyclic_quotient")
    return order


def _selection_key(selection: list[RewriteCandidate]) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (item.left_index, item.right_index, item.rule_id)
        for item in sorted(selection, key=lambda x: (x.left_index, x.right_index, x.rule_id))
    )


def _matching_upper_bound_small(candidates: list[RewriteCandidate]) -> int:
    best = 0

    def visit(position: int, used: int, weight: int) -> None:
        nonlocal best
        if weight > best:
            best = weight
        if position >= len(candidates):
            return
        visit(position + 1, used, weight)
        candidate = candidates[position]
        bit_left = 1 << candidate.left_index
        bit_right = 1 << candidate.right_index
        if not (used & (bit_left | bit_right)):
            visit(position + 1, used | bit_left | bit_right, weight + candidate.reduction_weight)

    visit(0, 0, 0)
    return best


def _matching_upper_bound_milp(candidates: list[RewriteCandidate], n: int) -> tuple[int, str | None]:
    if not candidates:
        return 0, None
    try:
        from scipy.optimize import Bounds, LinearConstraint, milp
        from scipy.sparse import coo_matrix

        rows = []
        cols = []
        for column, candidate in enumerate(candidates):
            rows.extend((candidate.left_index, candidate.right_index))
            cols.extend((column, column))
        matrix = coo_matrix(
            (np.ones(len(rows)), (rows, cols)),
            shape=(n, len(candidates)),
        ).tocsr()
        result = milp(
            c=-np.asarray([item.reduction_weight for item in candidates], dtype=float),
            integrality=np.ones(len(candidates)),
            bounds=Bounds(0.0, 1.0),
            constraints=LinearConstraint(matrix, -np.inf, 1.0),
            options={"presolve": True},
        )
        if not result.success or result.fun is None:
            return sum(item.reduction_weight for item in candidates), "matching_milp_not_optimal"
        return int(round(-float(result.fun))), None
    except Exception as exc:  # pragma: no cover - dependency/runtime fallback
        return sum(item.reduction_weight for item in candidates), f"matching_milp_unavailable:{type(exc).__name__}"


def _exact_joint_selection(
    candidates: list[RewriteCandidate],
    n: int,
    edges: list[set[int]],
    node_budget: int,
) -> tuple[list[RewriteCandidate], int, bool]:
    best_selection: list[RewriteCandidate] = []
    best_weight = 0
    search_nodes = 0
    budget_exceeded = False
    suffix_weights = [0] * (len(candidates) + 1)
    for position in range(len(candidates) - 1, -1, -1):
        suffix_weights[position] = suffix_weights[position + 1] + candidates[position].reduction_weight

    def visit(position: int, used: int, selected: list[RewriteCandidate], weight: int) -> None:
        nonlocal best_selection, best_weight, search_nodes, budget_exceeded
        if budget_exceeded:
            return
        search_nodes += 1
        if search_nodes > node_budget:
            budget_exceeded = True
            return
        if weight + suffix_weights[position] < best_weight:
            return
        if weight > best_weight or (
            weight == best_weight and _selection_key(selected) < _selection_key(best_selection)
        ):
            best_weight = weight
            best_selection = list(selected)
        if position >= len(candidates):
            return
        candidate = candidates[position]
        visit(position + 1, used, selected, weight)
        endpoint_bits = (1 << candidate.left_index) | (1 << candidate.right_index)
        if used & endpoint_bits:
            return
        proposed = selected + [candidate]
        if _quotient_is_acyclic(n, edges, proposed):
            visit(position + 1, used | endpoint_bits, proposed, weight + candidate.reduction_weight)

    visit(0, 0, [], 0)
    return best_selection, search_nodes, budget_exceeded


def _beam_selection(
    candidates: list[RewriteCandidate],
    n: int,
    edges: list[set[int]],
    beam_width: int,
) -> tuple[list[RewriteCandidate], int]:
    states: list[tuple[int, tuple[int, ...], int]] = [(0, tuple(), 0)]
    for position, candidate in enumerate(candidates):
        expanded = list(states)
        for weight, chosen_positions, used in states:
            endpoint_bits = (1 << candidate.left_index) | (1 << candidate.right_index)
            if used & endpoint_bits:
                continue
            selected = [candidates[index] for index in chosen_positions] + [candidate]
            if _quotient_is_acyclic(n, edges, selected):
                expanded.append((
                    weight + candidate.reduction_weight,
                    chosen_positions + (position,),
                    used | endpoint_bits,
                ))
        expanded.sort(key=lambda state: (-state[0], tuple(_selection_key([candidates[i] for i in state[1]]))))
        dedup: dict[tuple[int, ...], tuple[int, tuple[int, ...], int]] = {}
        for state in expanded:
            dedup.setdefault(state[1], state)
        states = list(dedup.values())[:beam_width]
    best = max(
        states,
        key=lambda state: (state[0], tuple(-x for pair in _selection_key([candidates[i] for i in state[1]]) for x in (pair[0], pair[1]))),
    )
    return [candidates[index] for index in best[1]], len(states) * max(1, len(candidates))


def _coerce_config(config: ExposureConfig | Mapping[str, Any] | None) -> ExposureConfig:
    if config is None:
        return ExposureConfig().normalized()
    if isinstance(config, ExposureConfig):
        return config.normalized()
    if isinstance(config, Mapping):
        return ExposureConfig(**dict(config)).normalized()
    raise ValueError("config_must_be_exposure_config_or_mapping")


def _unavailable_certificate(
    circuit: Any,
    config: ExposureConfig | None,
    reason: str,
) -> ExposureCertificate:
    if isinstance(circuit, QuantumCircuit):
        input_hash = _input_sha256(circuit)
        order = list(range(len(circuit.data)))
        model = str(config.dependence_model.value if isinstance(config and config.dependence_model, DependenceModel) else getattr(config, "dependence_model", "unavailable"))
        rule_library = config.rule_library if config else PAIR_RULE_LIBRARY
    else:
        input_hash = hashlib.sha256(repr(circuit).encode()).hexdigest()
        order = []
        model = "unavailable"
        rule_library = PAIR_RULE_LIBRARY
    return ExposureCertificate(
        input_sha256=input_hash,
        dependence_model=model,
        rule_library=rule_library,
        current_exposed_weight=0,
        constructive_lower_bound=0,
        matching_upper_bound=0,
        exact_optimum=None,
        status=CertificateStatus.UNAVAILABLE.value,
        selected_pairs=[],
        listing_order=order,
        candidate_count=0,
        discarded_candidate_count=0,
        search_nodes=0,
        source_hashes=_source_hashes(),
        failure_reason=reason,
        solver="none",
        listing_sha256=_listing_sha256(order),
    )


def certify_rewrite_exposure(
    circuit: QuantumCircuit,
    config: ExposureConfig | Mapping[str, Any] | None = None,
) -> ExposureCertificate:
    """Certify supported pair exposure and return a deterministic result.

    ``matching_upper_bound`` is safe for the candidate graph.  It is not a
    claim about arbitrary templates, synthesis, or the global optimum of a
    circuit.  When candidate truncation or search-budget exhaustion occurs,
    the status is never upgraded to ``exact``.
    """
    try:
        normalized = _coerce_config(config)
    except Exception as exc:
        return _unavailable_certificate(circuit, None, f"invalid_config:{exc}")
    failure = _scope_failure(circuit)
    if failure is not None:
        return _unavailable_certificate(circuit, normalized, failure)

    input_hash = _input_sha256(circuit)
    n = len(circuit.data)
    candidates = _candidate_pairs(circuit, normalized.tolerance)
    edges, actual_model, fallback_reason, _overlap_checks = _dependency_edges(
        circuit,
        normalized.dependence_model,
        normalized.overlap_check_budget,
    )
    descendants, ancestors = _transitive_closure(edges)
    candidates = [
        RewriteCandidate(
            left_index=item.left_index,
            right_index=item.right_index,
            rule_id=item.rule_id,
            reduction_weight=item.reduction_weight,
            pairwise_exposable=_pairwise_exposable(item, descendants, ancestors),
        )
        for item in candidates
    ]
    pairwise_candidates = [item for item in candidates if item.pairwise_exposable]
    ranked = _rank_candidates(pairwise_candidates)
    discarded = max(0, len(ranked) - normalized.candidate_cap)
    retained = ranked[: normalized.candidate_cap]
    current_weight = _adjacent_matching_weight(
        circuit, range(n), normalized.tolerance
    )

    matching_milp_reason = None
    all_for_ub = retained
    if len(all_for_ub) <= DEFAULT_EXACT_CANDIDATE_LIMIT:
        retained_ub = _matching_upper_bound_small(all_for_ub)
        solver = "exact_branch_and_bound_plus_small_matching"
    else:
        retained_ub, matching_milp_reason = _matching_upper_bound_milp(all_for_ub, n)
        solver = "beam_plus_scipy_milp_matching"
    matching_ub = retained_ub + sum(item.reduction_weight for item in ranked[normalized.candidate_cap:])

    search_nodes = 0
    exact_optimum: int | None = None
    search_budget_exceeded = False
    if len(ranked) <= DEFAULT_EXACT_CANDIDATE_LIMIT and discarded == 0:
        selected, search_nodes, budget_exceeded = _exact_joint_selection(
            retained, n, edges, normalized.exact_node_budget
        )
        search_budget_exceeded = budget_exceeded
        exact_optimum = sum(item.reduction_weight for item in selected) if not budget_exceeded else None
        solver = "exact_branch_and_bound"
        if budget_exceeded:
            selected, search_nodes = _beam_selection(
                retained, n, edges, normalized.beam_width
            )
    else:
        selected, search_nodes = _beam_selection(retained, n, edges, normalized.beam_width)
        if len(ranked) <= DEFAULT_EXACT_CANDIDATE_LIMIT and discarded == 0:
            exact_optimum = None

    lower_bound = sum(item.reduction_weight for item in selected)
    listing = _materialize_order(n, edges, selected)
    if exact_optimum is not None and lower_bound != exact_optimum:
        raise AssertionError("exact_solver_listing_did_not_attain_exact_optimum")

    if matching_milp_reason and fallback_reason is None:
        fallback_reason = matching_milp_reason
    if discarded:
        status = CertificateStatus.TRUNCATED
    elif lower_bound == matching_ub and not search_budget_exceeded:
        status = CertificateStatus.EXACT_ZERO if lower_bound == 0 else CertificateStatus.EXACT
    elif exact_optimum is None:
        status = CertificateStatus.BOUNDED
    else:
        status = CertificateStatus.BOUNDED
    if not retained:
        status = CertificateStatus.EXACT_ZERO
        exact_optimum = 0

    return ExposureCertificate(
        input_sha256=input_hash,
        dependence_model=actual_model.value,
        rule_library=normalized.rule_library,
        current_exposed_weight=current_weight,
        constructive_lower_bound=lower_bound,
        matching_upper_bound=int(matching_ub),
        exact_optimum=exact_optimum,
        status=status.value,
        selected_pairs=[item.to_dict() for item in selected],
        listing_order=listing,
        candidate_count=len(candidates),
        discarded_candidate_count=discarded,
        search_nodes=search_nodes,
        source_hashes=_source_hashes(),
        failure_reason=None,
        fallback_reason=fallback_reason,
        solver=solver,
        listing_sha256=_listing_sha256(listing),
    )


def materialize_cgl_listing(circuit: QuantumCircuit, listing_order: Iterable[int]) -> QuantumCircuit:
    """Return a deep-copied circuit with the supplied instruction order."""
    order = list(listing_order)
    if sorted(order) != list(range(len(circuit.data))):
        raise ValueError("listing_order_must_be_a_permutation_of_instruction_indices")
    result = copy.deepcopy(circuit)
    instructions = list(result.data)
    # QuantumCircuitData accepts a replacement sequence, whereas slice
    # assignment expects raw ``(operation, qargs, cargs)`` triples.
    result.data = [instructions[index] for index in order]
    return result


class CertificateGuidedPreprocessor:
    """Explicit opt-in CGL preprocessor; existing optimizers are untouched."""

    def __init__(self, config: ExposureConfig | Mapping[str, Any] | None = None):
        self.config = _coerce_config(config)

    def preprocess(self, circuit: QuantumCircuit) -> tuple[QuantumCircuit, ExposureCertificate]:
        certificate = certify_rewrite_exposure(circuit, self.config)
        if certificate.status == CertificateStatus.UNAVAILABLE.value:
            return copy.deepcopy(circuit), certificate
        return materialize_cgl_listing(circuit, certificate.listing_order), certificate


__all__ = [
    "CertificateGuidedPreprocessor",
    "CertificateStatus",
    "DependenceModel",
    "ExposureCertificate",
    "ExposureConfig",
    "RewriteCandidate",
    "certify_rewrite_exposure",
    "materialize_cgl_listing",
]
