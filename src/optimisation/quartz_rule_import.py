"""Deterministic, read-only import of a pinned Quartz ECC set.

The v13 landscape method treats an ECC as a finite rule library.  This module
keeps the import deliberately independent from the historical Quartz build:
it reads only the pinned JSON artifact, chooses anchors by a documented total
ordering, derives parameter bindings, and proves every derived direction.

Quartz's JSON operation format is ``[name, [Q...], [Q..., P...]]``.  The
second list carries qubit operands and the final list carries the symbolic
parameter labels accepted by the operation.  The Nam set used here contains
only ``h``, ``x``, ``cx`` and ``rz``.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import sympy as sp


SUPPORTED_GATES = frozenset({"h", "x", "cx", "rz"})
QUARTZ_SOURCE_COMMIT = "c4abf876608b111b2900d59a3c4efd7982063c20"
NUMERIC_CHECK_COUNT = 32
NUMERIC_TOLERANCE = 1e-12
SYMBOLIC_TOLERANCE = 0


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_json(payload: Any) -> str:
    return sha256_bytes(_canonical_bytes(payload))


@dataclass(frozen=True)
class QuartzOperation:
    name: str
    qubits: tuple[int, ...]
    params: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "qubits": list(self.qubits),
            "params": list(self.params),
        }


@dataclass(frozen=True)
class QuartzTemplate:
    class_id: str
    num_qubits: int
    raw_cost: tuple[Any, ...]
    operations: tuple[QuartzOperation, ...]

    @property
    def gate_count(self) -> int:
        return len(self.operations)

    @property
    def cx_count(self) -> int:
        return sum(operation.name == "cx" for operation in self.operations)

    @property
    def depth(self) -> int:
        ending: dict[int, int] = defaultdict(int)
        for operation in self.operations:
            layer = max((ending[q] for q in operation.qubits), default=0) + 1
            for qubit in operation.qubits:
                ending[qubit] = layer
        return max(ending.values(), default=0)

    @property
    def parameter_labels(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                parameter
                for operation in self.operations
                for parameter in operation.params
            )
        )

    @property
    def serialized_ops(self) -> str:
        return json.dumps(
            [operation.to_dict() for operation in self.operations],
            sort_keys=True,
            separators=(",", ":"),
        )

    @property
    def anchor_key(self) -> tuple[Any, ...]:
        return (self.gate_count, self.cx_count, self.depth, self.serialized_ops)

    @property
    def content_hash(self) -> str:
        return sha256_json(
            {
                "num_qubits": self.num_qubits,
                "raw_cost": list(self.raw_cost),
                "operations": [operation.to_dict() for operation in self.operations],
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_id": self.class_id,
            "num_qubits": self.num_qubits,
            "raw_cost": list(self.raw_cost),
            "gate_count": self.gate_count,
            "cx_count": self.cx_count,
            "depth": self.depth,
            "parameter_rank": len(self.parameter_labels),
            "parameter_labels": list(self.parameter_labels),
            "serialized_ops": self.serialized_ops,
            "content_hash": self.content_hash,
            "operations": [operation.to_dict() for operation in self.operations],
        }


def _class_sort_key(class_id: str) -> tuple[int, int, str]:
    parts = class_id.split("_")
    try:
        return (int(parts[0]), int(parts[1]), class_id)
    except (IndexError, ValueError):
        return (math.inf, math.inf, class_id)


def _parse_operation(raw: Any) -> QuartzOperation:
    if not isinstance(raw, list) or len(raw) != 3:
        raise ValueError("quartz_operation_shape_invalid")
    name, raw_qubits, raw_outputs = raw
    if name not in SUPPORTED_GATES:
        raise ValueError(f"quartz_gate_unsupported:{name}")
    if not isinstance(raw_qubits, list) or not all(
        isinstance(token, str) and token.startswith("Q") for token in raw_qubits
    ):
        raise ValueError("quartz_qubit_operands_invalid")
    if not isinstance(raw_outputs, list):
        raise ValueError("quartz_output_operands_invalid")
    qubits = tuple(int(token[1:]) for token in raw_qubits)
    params = tuple(token for token in raw_outputs if isinstance(token, str) and token.startswith("P"))
    expected_arity = {"h": 1, "x": 1, "rz": 1, "cx": 2}[name]
    if len(qubits) != expected_arity:
        raise ValueError(f"quartz_arity_invalid:{name}")
    if name == "rz" and len(params) != 1:
        raise ValueError("quartz_rz_parameter_invalid")
    if name != "rz" and params:
        raise ValueError(f"quartz_unexpected_parameters:{name}")
    return QuartzOperation(name=name, qubits=qubits, params=params)


def load_quartz_ecc(path: Path) -> tuple[dict[str, Any], list[tuple[str, tuple[QuartzTemplate, ...]]]]:
    """Load and validate the pinned ECC without changing the source file."""

    source = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(source, list) or len(source) != 2 or not isinstance(source[1], dict):
        raise ValueError("quartz_ecc_root_shape_invalid")
    classes: list[tuple[str, tuple[QuartzTemplate, ...]]] = []
    for class_id in sorted(source[1], key=_class_sort_key):
        raw_members = source[1][class_id]
        if not isinstance(raw_members, list) or not raw_members:
            raise ValueError(f"quartz_class_empty:{class_id}")
        members: list[QuartzTemplate] = []
        for raw_member in raw_members:
            if not isinstance(raw_member, list) or len(raw_member) != 2:
                raise ValueError(f"quartz_member_shape_invalid:{class_id}")
            raw_cost, raw_operations = raw_member
            if not isinstance(raw_cost, list) or not isinstance(raw_operations, list):
                raise ValueError(f"quartz_member_payload_invalid:{class_id}")
            operations = tuple(_parse_operation(raw) for raw in raw_operations)
            if not raw_cost or int(raw_cost[0]) < 1:
                raise ValueError(f"quartz_num_qubits_invalid:{class_id}")
            members.append(
                QuartzTemplate(
                    class_id=class_id,
                    num_qubits=int(raw_cost[0]),
                    raw_cost=tuple(raw_cost),
                    operations=operations,
                )
            )
        classes.append((class_id, tuple(members)))
    return {"basis_record": source[0], "class_count": len(classes)}, classes


def _parameter_values(labels: Iterable[str], check: int) -> dict[str, float]:
    return {
        label: math.pi * (
            0.173 * math.sin((check + 1) * (index + 1) * 0.71)
            + 0.097 * math.cos((check + 3) * (index + 2) * 0.37)
        )
        for index, label in enumerate(labels)
    }


def _apply_numeric_operation(
    matrix: np.ndarray,
    operation: QuartzOperation,
    num_qubits: int,
    values: Mapping[str, float],
) -> np.ndarray:
    dimension = 2**num_qubits
    gate = np.zeros((dimension, dimension), dtype=np.complex128)
    if operation.name == "h":
        for basis in range(dimension):
            bit = (basis >> operation.qubits[0]) & 1
            for output_bit, coefficient in (
                (0, 1 / math.sqrt(2)),
                (1, (-1 if bit else 1) / math.sqrt(2)),
            ):
                output = (basis & ~(1 << operation.qubits[0])) | (output_bit << operation.qubits[0])
                gate[output, basis] = coefficient
    elif operation.name == "x":
        for basis in range(dimension):
            gate[basis ^ (1 << operation.qubits[0]), basis] = 1
    elif operation.name == "rz":
        angle = values[operation.params[0]]
        for basis in range(dimension):
            bit = (basis >> operation.qubits[0]) & 1
            gate[basis, basis] = np.exp((-1j * angle / 2) if bit == 0 else (1j * angle / 2))
    elif operation.name == "cx":
        control, target = operation.qubits
        for basis in range(dimension):
            output = basis ^ (1 << target) if ((basis >> control) & 1) else basis
            gate[output, basis] = 1
    else:  # pragma: no cover - parser rejects unknown gates
        raise ValueError(operation.name)
    return gate @ matrix


def _numeric_unitary(
    template: QuartzTemplate,
    values: Mapping[str, float],
) -> np.ndarray:
    matrix = np.eye(2**template.num_qubits, dtype=np.complex128)
    for operation in template.operations:
        matrix = _apply_numeric_operation(matrix, operation, template.num_qubits, values)
    return matrix


def _up_to_global_phase(left: np.ndarray, right: np.ndarray, tolerance: float = NUMERIC_TOLERANCE) -> bool:
    dimension = left.shape[0]
    overlap = abs(np.trace(left.conj().T @ right)) / dimension
    return bool(np.isclose(overlap, 1.0, atol=tolerance, rtol=0.0))


def _binding_values(binding: Mapping[str, Mapping[str, int]], values: Mapping[str, float]) -> dict[str, float]:
    return {
        target: sum(int(coefficient) * values[source] for source, coefficient in expression.items())
        for target, expression in binding.items()
    }


def _numeric_relation(
    source: QuartzTemplate,
    target: QuartzTemplate,
    binding: Mapping[str, Mapping[str, int]],
    checks: Iterable[int],
) -> bool:
    labels = source.parameter_labels
    return all(
        _up_to_global_phase(
            _numeric_unitary(source, values := _parameter_values(labels, check)),
            _numeric_unitary(target, _binding_values(binding, values)),
        )
        for check in checks
    )


def _candidate_bindings(source: QuartzTemplate, target: QuartzTemplate) -> Iterable[dict[str, dict[str, int]]]:
    source_labels = source.parameter_labels
    target_labels = target.parameter_labels
    if len(source_labels) == len(target_labels):
        for permutation in itertools.permutations(source_labels):
            yield {
                target_label: {source_label: 1}
                for target_label, source_label in zip(target_labels, permutation)
            }
    elif len(source_labels) == 2 and len(target_labels) == 1:
        # Quartz's Nam ECC uses the ``add`` parameter constructor in this
        # rank-changing class.  Keep the candidate set explicit and finite.
        for coefficients in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            yield {
                target_labels[0]: {
                    source_labels[0]: coefficients[0],
                    source_labels[1]: coefficients[1],
                }
            }


def find_parameter_binding(source: QuartzTemplate, target: QuartzTemplate) -> dict[str, dict[str, int]] | None:
    for binding in _candidate_bindings(source, target):
        if _numeric_relation(source, target, binding, (0, 7, 19)):
            return binding
    return None


def _symbolic_operation_matrix(
    operation: QuartzOperation,
    num_qubits: int,
    values: Mapping[str, sp.Expr],
) -> sp.Matrix:
    dimension = 2**num_qubits
    matrix = sp.zeros(dimension, dimension)
    if operation.name == "h":
        for basis in range(dimension):
            bit = (basis >> operation.qubits[0]) & 1
            for output_bit, coefficient in (
                (0, sp.sqrt(2) ** -1),
                (1, (-1 if bit else 1) * sp.sqrt(2) ** -1),
            ):
                output = (basis & ~(1 << operation.qubits[0])) | (output_bit << operation.qubits[0])
                matrix[output, basis] = coefficient
    elif operation.name == "x":
        for basis in range(dimension):
            matrix[basis ^ (1 << operation.qubits[0]), basis] = 1
    elif operation.name == "rz":
        angle = values[operation.params[0]]
        for basis in range(dimension):
            bit = (basis >> operation.qubits[0]) & 1
            matrix[basis, basis] = sp.exp((-sp.I * angle / 2) if bit == 0 else (sp.I * angle / 2))
    elif operation.name == "cx":
        control, target = operation.qubits
        for basis in range(dimension):
            output = basis ^ (1 << target) if ((basis >> control) & 1) else basis
            matrix[output, basis] = 1
    return matrix


def _symbolic_unitary(template: QuartzTemplate, values: Mapping[str, sp.Expr]) -> sp.Matrix:
    matrix = sp.eye(2**template.num_qubits)
    for operation in template.operations:
        matrix = _symbolic_operation_matrix(operation, template.num_qubits, values) * matrix
    return matrix


def _symbolic_simplify(value: sp.Expr) -> sp.Expr:
    return sp.simplify(sp.powsimp(value, force=True))


def symbolic_equivalence(
    source: QuartzTemplate,
    target: QuartzTemplate,
    binding: Mapping[str, Mapping[str, int]],
) -> tuple[bool, str]:
    symbols = {label: sp.Symbol(label) for label in source.parameter_labels}
    target_values = {
        target_label: sum(
            int(coefficient) * symbols[source_label]
            for source_label, coefficient in expression.items()
        )
        for target_label, expression in binding.items()
    }
    left = _symbolic_unitary(source, symbols)
    right = _symbolic_unitary(target, target_values)
    phase: sp.Expr | None = None
    for row in range(left.rows):
        for column in range(left.cols):
            if left[row, column] != 0:
                phase = _symbolic_simplify(right[row, column] / left[row, column])
                break
        if phase is not None:
            break
    if phase is None:
        equivalent = left == right
        return equivalent, sha256_json({"phase": "none", "equivalent": equivalent})
    residuals = []
    equivalent = True
    for row in range(left.rows):
        for column in range(left.cols):
            residual = _symbolic_simplify(right[row, column] - phase * left[row, column])
            residuals.append(str(residual))
            if residual != 0:
                equivalent = False
    proof_payload = {
        "phase": str(phase),
        "residual_sha256": sha256_bytes("\n".join(residuals).encode("utf-8")),
        "equivalent": equivalent,
    }
    return equivalent, sha256_json(proof_payload)


def _rule_id(class_id: str, source: QuartzTemplate, target: QuartzTemplate, direction: str) -> str:
    return f"quartz_v1:{class_id}:{source.content_hash[:12]}->{target.content_hash[:12]}:{direction}"


def _quartz_rule(
    source: QuartzTemplate,
    target: QuartzTemplate,
    direction: str,
    reversible: bool,
) -> dict[str, Any]:
    binding = find_parameter_binding(source, target)
    if binding is None:
        raise ValueError(f"parameter_binding_not_found:{source.class_id}:{direction}")
    equivalent, proof_hash = symbolic_equivalence(source, target, binding)
    if not equivalent:
        raise ValueError(f"symbolic_equivalence_failed:{source.class_id}:{direction}")
    rule = {
        "rule_id": _rule_id(source.class_id, source, target, direction),
        "rule_family": "quartz_v1",
        "class_id": source.class_id,
        "direction": direction,
        "reversible": reversible,
        "source_template_hash": source.content_hash,
        "target_template_hash": target.content_hash,
        "source": source.to_dict(),
        "target": target.to_dict(),
        "parameter_binding": binding,
        "source_parameter_rank": len(source.parameter_labels),
        "target_parameter_rank": len(target.parameter_labels),
        "parameter_rank": max(len(source.parameter_labels), len(target.parameter_labels)),
        "source_gate_count": source.gate_count,
        "target_gate_count": target.gate_count,
        "cost_delta": target.gate_count - source.gate_count,
        "symbolic_status": "PASS",
        "symbolic_proof_hash": proof_hash,
        "numeric_check_count": NUMERIC_CHECK_COUNT,
        "numeric_tolerance": NUMERIC_TOLERANCE,
    }
    rule["content_hash"] = sha256_json(
        {
            key: value
            for key, value in rule.items()
            if key not in {"rule_id", "content_hash", "symbolic_proof_hash"}
        }
    )
    return rule


def _pair_and_structural_rules() -> list[dict[str, Any]]:
    pair_rules = [
        ("pair_v1.self_inverse", "same gate and operands; self inverse"),
        ("pair_v1.t_tdg", "t and tdg inverse pair"),
        ("pair_v1.s_sdg", "s and sdg inverse pair"),
        ("pair_v1.rotation_zero", "same-axis rotations sum to zero modulo 2pi"),
        ("pair_v1.rotation_merge", "same-axis rotations merge by angle addition"),
    ]
    structural_rules = [
        ("exchange.disjoint", "disjoint supports commute"),
        ("exchange.same_single", "same single-qubit gate commutes with itself"),
        ("exchange.same_axis_rotation", "same-axis rotations commute"),
        ("exchange.z_family", "Z-family gates commute on one wire"),
        ("exchange.cx_control_z", "CX commutes with Z-family gate on control"),
        ("exchange.cx_target_x", "CX commutes with X-family gate on target"),
        ("exchange.cz_z", "CZ commutes with Z-family gate on either wire"),
        ("exchange.same_swap", "SWAP gates on the same pair commute"),
        ("exchange.same_cz", "CZ gates on the same pair commute"),
    ]
    result = []
    for family, entries in (("pair_v1", pair_rules), ("structural_exchange_v1", structural_rules)):
        for rule_id, semantics in entries:
            payload = {"rule_id": rule_id, "rule_family": family, "semantics": semantics}
            result.append({**payload, "content_hash": sha256_json(payload)})
    return result


def _mutant_audit(rules: list[dict[str, Any]]) -> dict[str, Any]:
    """Run five fail-closed mutation classes against the imported library."""

    quartz = [rule for rule in rules if rule["rule_family"] == "quartz_v1"]
    representative = quartz[0]
    mutant_results = []

    # 1. Change a gate name while retaining the proof and binding.
    gate_mutant = json.loads(json.dumps(representative))
    gate_mutant["source"]["operations"][0]["name"] = "x" if gate_mutant["source"]["operations"][0]["name"] != "x" else "h"
    mutant_results.append(("gate_name", not _verify_rule(gate_mutant)))

    # 2. Change an operand.  This catches control/target and wire identity.
    operand_mutant = json.loads(json.dumps(representative))
    operation = operand_mutant["source"]["operations"][0]
    if len(operation["qubits"]) == 2:
        operation["qubits"] = list(reversed(operation["qubits"]))
    else:
        operation["qubits"] = [operation["qubits"][0] + 1]
    mutant_results.append(("operand", not _verify_rule(operand_mutant)))

    # 3. Change a parameter binding coefficient where one exists.
    binding_mutant = json.loads(json.dumps(representative))
    if binding_mutant["parameter_binding"]:
        target_label = next(iter(binding_mutant["parameter_binding"]))
        source_label = next(iter(binding_mutant["parameter_binding"][target_label]))
        binding_mutant["parameter_binding"][target_label][source_label] *= -1
    else:
        binding_mutant["parameter_binding"] = {"P_mut": {"P_source": 1}}
    mutant_results.append(("parameter_binding", not _verify_rule(binding_mutant)))

    # 4. Replace the target with an unrelated valid template of the same arity.
    target_mutant = json.loads(json.dumps(representative))
    target_mutant["target"]["operations"] = [{"name": "h", "qubits": [0], "params": []}]
    target_mutant["target"]["gate_count"] = 1
    target_mutant["target"]["parameter_rank"] = 0
    target_mutant["target"]["parameter_labels"] = []
    target_mutant["parameter_binding"] = {}
    mutant_results.append(("target_template", not _verify_rule(target_mutant)))

    # 5. Claim the rank-increasing reverse of Quartz's only non-reversible
    # parameter split.  The verifier must reject it before semantic use.
    rank_mutant = next(
        (rule for rule in quartz if rule["source_parameter_rank"] == 2 and rule["target_parameter_rank"] == 1),
        representative,
    )
    reverse_mutant = json.loads(json.dumps(rank_mutant))
    reverse_mutant["source"], reverse_mutant["target"] = reverse_mutant["target"], reverse_mutant["source"]
    reverse_mutant["source_parameter_rank"], reverse_mutant["target_parameter_rank"] = 1, 2
    reverse_mutant["reversible"] = True
    mutant_results.append(("rank_increasing_reverse", not _verify_rule(reverse_mutant)))

    return {
        "classes": [name for name, _ in mutant_results],
        "checked": len(mutant_results),
        "non_equivalent_mutant_escapes": sum(not rejected for _, rejected in mutant_results),
        "rejected": {name: rejected for name, rejected in mutant_results},
    }


def _verify_rule(rule: Mapping[str, Any]) -> bool:
    if rule.get("rule_family") != "quartz_v1":
        return True
    if rule.get("reversible") and int(rule.get("source_parameter_rank", 0)) != int(rule.get("target_parameter_rank", 0)):
        return False
    source_data = rule.get("source", {})
    target_data = rule.get("target", {})
    try:
        source = QuartzTemplate(
            class_id=str(source_data["class_id"]),
            num_qubits=int(source_data["num_qubits"]),
            raw_cost=tuple(source_data["raw_cost"]),
            operations=tuple(
                QuartzOperation(
                    name=str(operation["name"]),
                    qubits=tuple(int(q) for q in operation["qubits"]),
                    params=tuple(str(p) for p in operation["params"]),
                )
                for operation in source_data["operations"]
            ),
        )
        target = QuartzTemplate(
            class_id=str(target_data["class_id"]),
            num_qubits=int(target_data["num_qubits"]),
            raw_cost=tuple(target_data["raw_cost"]),
            operations=tuple(
                QuartzOperation(
                    name=str(operation["name"]),
                    qubits=tuple(int(q) for q in operation["qubits"]),
                    params=tuple(str(p) for p in operation["params"]),
                )
                for operation in target_data["operations"]
            ),
        )
        binding = rule["parameter_binding"]
        if find_parameter_binding(source, target) != binding:
            return False
        equivalent, proof_hash = symbolic_equivalence(source, target, binding)
        return equivalent and proof_hash == rule.get("symbolic_proof_hash")
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def generate_rule_library(ecc_path: Path, source_metadata_path: Path) -> dict[str, Any]:
    metadata = json.loads(source_metadata_path.read_text(encoding="utf-8"))
    source_info, classes = load_quartz_ecc(ecc_path)
    quartz_rules: list[dict[str, Any]] = []
    rank_counts: Counter[str] = Counter()
    cost_delta_counts: Counter[str] = Counter()
    direction_counts: Counter[str] = Counter()
    for class_id, members in classes:
        anchor = min(members, key=lambda member: member.anchor_key)
        for member in members:
            if member.content_hash == anchor.content_hash:
                continue
            reversible = len(member.parameter_labels) == len(anchor.parameter_labels)
            quartz_rules.append(_quartz_rule(member, anchor, "to_anchor", reversible))
            direction_counts["bidirectional" if reversible else "one_way"] += 1
            if reversible:
                quartz_rules.append(_quartz_rule(anchor, member, "from_anchor", True))
                direction_counts["bidirectional" if reversible else "one_way"] += 1
            rank_counts[str(max(len(member.parameter_labels), len(anchor.parameter_labels)))] += 1
            cost_delta_counts[str(anchor.gate_count - member.gate_count)] += 1
    quartz_rules.sort(key=lambda rule: rule["rule_id"])
    auxiliary_rules = _pair_and_structural_rules()
    all_rules = quartz_rules + auxiliary_rules
    content_hashes = [rule["content_hash"] for rule in all_rules]
    duplicates = len(content_hashes) - len(set(content_hashes))
    mutants = _mutant_audit(all_rules)
    summary = {
        "raw_class_count": len(classes),
        "raw_member_count": sum(len(members) for _, members in classes),
        "anchor_count": len(classes),
        "nonanchor_count": sum(len(members) - 1 for _, members in classes),
        "quartz_v1_direction_count": len(quartz_rules),
        "quartz_v1_reversible_direction_count": sum(rule["reversible"] for rule in quartz_rules),
        "quartz_v1_one_way_direction_count": sum(not rule["reversible"] for rule in quartz_rules),
        "parameter_rank_distribution_nonanchor": dict(sorted(rank_counts.items(), key=lambda item: int(item[0]))),
        "cost_delta_distribution_nonanchor_to_anchor": dict(sorted(cost_delta_counts.items(), key=lambda item: int(item[0]))),
        "direction_counts": dict(direction_counts),
        "auxiliary_rule_count": len(auxiliary_rules),
        "combined_rule_count": len(all_rules),
        "content_hash_duplicate_count": duplicates,
        "symbolic_mismatch_count": sum(rule.get("symbolic_status") != "PASS" for rule in quartz_rules),
        "numeric_mismatch_count": sum(
            not _numeric_relation(
                _template_from_dict(rule["source"]),
                _template_from_dict(rule["target"]),
                rule["parameter_binding"],
                range(NUMERIC_CHECK_COUNT),
            )
            for rule in quartz_rules
        ),
        "mutant_audit": mutants,
    }
    if summary["quartz_v1_direction_count"] != 1474:
        raise ValueError(f"quartz_direction_count_unexpected:{summary['quartz_v1_direction_count']}")
    if summary["symbolic_mismatch_count"] != 0 or summary["numeric_mismatch_count"] != 0:
        raise ValueError("quartz_semantic_zero_tolerance_failed")
    if mutants["non_equivalent_mutant_escapes"] != 0:
        raise ValueError("quartz_mutant_zero_tolerance_failed")
    return {
        "schema_version": "1.0.0",
        "method": "v13_certified_rewrite_landscape",
        "source": {
            **metadata,
            "ecc_sha256": sha256_bytes(ecc_path.read_bytes()),
            "source_metadata_sha256": sha256_bytes(source_metadata_path.read_bytes()),
            "parsed_basis_record": source_info["basis_record"],
        },
        "summary": summary,
        "rules": all_rules,
        "rule_library_sha256": sha256_json(all_rules),
    }


def _template_from_dict(data: Mapping[str, Any]) -> QuartzTemplate:
    return QuartzTemplate(
        class_id=str(data["class_id"]),
        num_qubits=int(data["num_qubits"]),
        raw_cost=tuple(data["raw_cost"]),
        operations=tuple(
            QuartzOperation(
                name=str(operation["name"]),
                qubits=tuple(int(q) for q in operation["qubits"]),
                params=tuple(str(p) for p in operation["params"]),
            )
            for operation in data["operations"]
        ),
    )


def write_outputs(
    ecc_path: Path,
    source_metadata_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    library = generate_rule_library(ecc_path.resolve(), source_metadata_path.resolve())
    output_root.mkdir(parents=True, exist_ok=True)
    library_path = output_root / "rule_library.json"
    summary_path = output_root / "summary.json"
    receipt_path = output_root / "receipt.json"
    library_path.write_text(json.dumps(library, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(library["summary"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = {
        "status": "PASS_STAGE_S2_E43",
        "ecc_sha256": library["source"]["ecc_sha256"],
        "source_metadata_sha256": library["source"]["source_metadata_sha256"],
        "rule_library_sha256": sha256_bytes(library_path.read_bytes()),
        "summary_sha256": sha256_bytes(summary_path.read_bytes()),
        "summary": library["summary"],
        "independent_generation_required": True,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


__all__ = [
    "NUMERIC_CHECK_COUNT",
    "QuartzOperation",
    "QuartzTemplate",
    "generate_rule_library",
    "load_quartz_ecc",
    "sha256_bytes",
    "sha256_json",
    "symbolic_equivalence",
    "write_outputs",
]
