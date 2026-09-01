"""Run the E38 exhaustive topological-listing oracle.

The oracle is intentionally independent of the production solver for the
critical checks: it builds a dense reference dependency graph, enumerates all
topological orders, and scans adjacent gate pairs directly.  The formal panel
is small enough that every order is enumerable (at most 8!).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.optimisation._gate_predicates import gates_commute
from src.optimisation.rewrite_exposure import (
    CertificateStatus,
    DependenceModel,
    ExposureConfig,
    _candidate_pairs,
    _dependency_edges,
    _pairwise_exposable,
    _transitive_closure,
    certify_rewrite_exposure,
    materialize_cgl_listing,
)


PROTOCOL_ID = "E38_REWRITE_EXPOSURE_ORACLE_V1"
SEED = 20260901
FORMAL_CASES_PER_STRATUM = 128
PREFLIGHT_CASES_PER_STRATUM = 8
GATE_ALPHABET = (
    "h", "x", "z", "s", "sdg", "t", "tdg", "rx", "ry", "rz", "cx", "cz"
)
ROTATION_ANGLES = (-math.pi, -math.pi / 2, math.pi / 2, math.pi)
STRATA = ("random", "implanted", "blocked", "multi_pair")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_json(payload: Any) -> str:
    return _sha256_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _random_operation(rng: random.Random, qubits: int) -> dict[str, Any]:
    name = rng.choice(GATE_ALPHABET)
    if name in {"cx", "cz"}:
        left = rng.randrange(qubits)
        right = rng.randrange(qubits - 1)
        if right >= left:
            right += 1
        return {"name": name, "qubits": [left, right], "params": []}
    target = rng.randrange(qubits)
    params = [rng.choice(ROTATION_ANGLES)] if name in {"rx", "ry", "rz"} else []
    return {"name": name, "qubits": [target], "params": params}


def _pattern_operation(name: str, qubits: Iterable[int], params: Iterable[float] = ()) -> dict[str, Any]:
    return {"name": name, "qubits": list(qubits), "params": list(params)}


def _make_case(rng: random.Random, stratum: str, ordinal: int) -> dict[str, Any]:
    qubit_count = rng.randint(2, 5)
    gate_count = rng.randint(4, 8)
    operations: list[dict[str, Any]] = []

    if stratum == "implanted":
        target = rng.randrange(qubit_count)
        operations.extend([
            _pattern_operation("h", [target]),
            _pattern_operation("h", [target]),
        ])
    elif stratum == "blocked":
        target = rng.randrange(qubit_count)
        operations.extend([
            _pattern_operation("h", [target]),
            _pattern_operation("x", [target]),
            _pattern_operation("h", [target]),
        ])
    elif stratum == "multi_pair":
        left = rng.randrange(qubit_count)
        right = (left + 1) % qubit_count
        operations.extend([
            _pattern_operation("h", [left]),
            _pattern_operation("h", [right]),
            _pattern_operation("h", [left]),
            _pattern_operation("h", [right]),
        ])

    while len(operations) < gate_count:
        operations.append(_random_operation(rng, qubit_count))

    return {
        "case_id": f"{stratum}_{ordinal:03d}",
        "stratum": stratum,
        "num_qubits": qubit_count,
        "operations": operations[:gate_count],
    }


def generate_panel(cases_per_stratum: int, seed: int = SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    cases = []
    for stratum in STRATA:
        for ordinal in range(cases_per_stratum):
            cases.append(_make_case(rng, stratum, ordinal))
    return cases


def circuit_from_spec(spec: dict[str, Any]) -> QuantumCircuit:
    circuit = QuantumCircuit(spec["num_qubits"])
    for operation in spec["operations"]:
        name = operation["name"]
        qubits = operation["qubits"]
        params = operation.get("params", [])
        if name == "h":
            circuit.h(qubits[0])
        elif name == "x":
            circuit.x(qubits[0])
        elif name == "z":
            circuit.z(qubits[0])
        elif name == "s":
            circuit.s(qubits[0])
        elif name == "sdg":
            circuit.sdg(qubits[0])
        elif name == "t":
            circuit.t(qubits[0])
        elif name == "tdg":
            circuit.tdg(qubits[0])
        elif name == "rx":
            circuit.rx(params[0], qubits[0])
        elif name == "ry":
            circuit.ry(params[0], qubits[0])
        elif name == "rz":
            circuit.rz(params[0], qubits[0])
        elif name == "cx":
            circuit.cx(qubits[0], qubits[1])
        elif name == "cz":
            circuit.cz(qubits[0], qubits[1])
        else:  # pragma: no cover - the protocol generator controls the alphabet
            raise ValueError(f"unsupported_protocol_gate:{name}")
    return circuit


def _support(circuit: QuantumCircuit, index: int) -> tuple[int, ...]:
    return tuple(circuit.find_bit(qubit).index for qubit in circuit.data[index].qubits)


def reference_edges(circuit: QuantumCircuit, model: DependenceModel) -> list[set[int]]:
    """Independent dense reference DAG for the formal oracle."""
    count = len(circuit.data)
    edges = [set() for _ in range(count)]
    for left in range(count):
        left_instruction = circuit.data[left]
        left_support = set(_support(circuit, left))
        for right in range(left + 1, count):
            right_instruction = circuit.data[right]
            right_support = set(_support(circuit, right))
            if left_support.isdisjoint(right_support):
                continue
            if model == DependenceModel.WIRE_ORDER_V1 or not gates_commute(
                circuit, left_instruction, right_instruction
            ):
                edges[left].add(right)
    return edges


def topological_orders(edges: list[set[int]]) -> Iterable[tuple[int, ...]]:
    count = len(edges)
    predecessors = [0] * count
    for left, successors in enumerate(edges):
        for right in successors:
            predecessors[right] |= 1 << left

    def visit(remaining: int, order: tuple[int, ...]):
        if remaining == 0:
            yield order
            return
        available = [
            index
            for index in range(count)
            if remaining & (1 << index)
            and not (predecessors[index] & remaining)
        ]
        for index in available:
            yield from visit(remaining ^ (1 << index), order + (index,))

    yield from visit((1 << count) - 1, tuple())


_SELF_INVERSE = {"h", "x", "z", "cx", "cz"}


def _normalized_angle(value: float) -> float:
    return (value + math.pi) % (2 * math.pi) - math.pi


def oracle_pair_rule(circuit: QuantumCircuit, left: int, right: int) -> tuple[str, int] | None:
    first = circuit.data[left]
    second = circuit.data[right]
    if _support(circuit, left) != _support(circuit, right):
        return None
    first_name = first.operation.name
    second_name = second.operation.name
    if first_name == second_name and first_name in _SELF_INVERSE:
        return "self_inverse", 2
    if {first_name, second_name} == {"t", "tdg"}:
        return "t_tdg", 2
    if {first_name, second_name} == {"s", "sdg"}:
        return "s_sdg", 2
    if first_name == second_name and first_name in {"rx", "ry", "rz"}:
        summed = float(first.operation.params[0]) + float(second.operation.params[0])
        if abs(_normalized_angle(summed)) <= 1e-10:
            return "rotation_zero", 2
        return "rotation_merge", 1
    return None


def oracle_candidates(circuit: QuantumCircuit) -> list[tuple[int, int, tuple[str, int]]]:
    result = []
    for left in range(len(circuit.data)):
        for right in range(left + 1, len(circuit.data)):
            rule = oracle_pair_rule(circuit, left, right)
            if rule is not None:
                result.append((left, right, rule))
    return result


def oracle_optimum(circuit: QuantumCircuit, edges: list[set[int]]) -> dict[str, Any]:
    candidates = oracle_candidates(circuit)
    candidate_keys = {(left, right) for left, right, _ in candidates}
    pairwise_seen: set[tuple[int, int]] = set()
    best_weight = 0
    best_order: tuple[int, ...] = tuple(range(len(circuit.data)))
    order_count = 0
    for order in topological_orders(edges):
        order_count += 1
        for left, right in zip(order, order[1:]):
            key = (min(left, right), max(left, right))
            if oracle_pair_rule(circuit, key[0], key[1]) is not None:
                pairwise_seen.add(key)
        weight = _actual_weight(circuit, order)
        if weight > best_weight or (weight == best_weight and order < best_order):
            best_weight = weight
            best_order = order
    return {
        "maximum_weight": best_weight,
        "maximum_order": list(best_order),
        "topological_order_count": order_count,
        "pairwise_exposable": {
            f"{left}:{right}": (left, right) in pairwise_seen
            for left, right in sorted(candidate_keys)
        },
    }


def _actual_weight(circuit: QuantumCircuit, order: Iterable[int]) -> int:
    order = list(order)
    best_without_previous = 0
    best_through_previous = 0
    for left, right in zip(order, order[1:]):
        rule = oracle_pair_rule(circuit, min(left, right), max(left, right))
        edge_weight = rule[1] if rule is not None else 0
        best_without_previous, best_through_previous = (
            best_through_previous,
            max(best_through_previous, best_without_previous + edge_weight),
        )
    return best_through_previous


def _is_topological(order: list[int], edges: list[set[int]]) -> bool:
    position = {node: index for index, node in enumerate(order)}
    return sorted(order) == list(range(len(edges))) and all(
        position[left] < position[right]
        for left, successors in enumerate(edges)
        for right in successors
    )


def _production_pairwise(circuit: QuantumCircuit, model: DependenceModel) -> dict[str, bool]:
    edges, _, fallback, _ = _dependency_edges(circuit, model, 20_000_000)
    assert fallback is None
    descendants, ancestors = _transitive_closure(edges)
    return {
        f"{candidate.left_index}:{candidate.right_index}": _pairwise_exposable(
            candidate, descendants, ancestors
        )
        for candidate in _candidate_pairs(circuit, 1e-10)
    }


def _equivalent_up_to_global_phase(left: QuantumCircuit, right: QuantumCircuit) -> bool:
    left_data = np.asarray(Operator(left).data)
    right_data = np.asarray(Operator(right).data)
    dimension = left_data.shape[0]
    overlap = abs(np.trace(np.conj(left_data).T @ right_data)) / dimension
    return bool(np.isclose(overlap, 1.0, atol=1e-8))


def _verify_certificate(
    circuit: QuantumCircuit,
    certificate: dict[str, Any],
    edges: list[set[int]],
) -> bool:
    order = list(certificate["listing_order"])
    if not _is_topological(order, edges):
        return False
    actual = _actual_weight(circuit, order)
    if actual < int(certificate["constructive_lower_bound"]):
        return False
    if int(certificate["constructive_lower_bound"]) > int(certificate["matching_upper_bound"]):
        return False
    if certificate["status"] == CertificateStatus.EXACT.value:
        if certificate["discarded_candidate_count"] != 0:
            return False
        if certificate["constructive_lower_bound"] != certificate["matching_upper_bound"]:
            return False
    return True


def evaluate_case(spec: dict[str, Any], model: DependenceModel) -> dict[str, Any]:
    circuit = circuit_from_spec(spec)
    edges = reference_edges(circuit, model)
    oracle = oracle_optimum(circuit, edges)
    certificate = certify_rewrite_exposure(
        circuit,
        ExposureConfig(dependence_model=model, candidate_cap=256, beam_width=8),
    )
    production_pairwise = _production_pairwise(circuit, model)
    pairwise_mismatch = sum(
        production_pairwise.get(key) != expected
        for key, expected in oracle["pairwise_exposable"].items()
    )
    cgl = materialize_cgl_listing(circuit, certificate.listing_order)
    cgl_weight = _actual_weight(circuit, certificate.listing_order)
    cgl_equivalence_failure = not _equivalent_up_to_global_phase(circuit, cgl)
    dependency_invalid = not _is_topological(certificate.listing_order, edges)
    mutant = certificate.to_dict()
    if certificate.constructive_lower_bound == 0:
        mutant["constructive_lower_bound"] = 1
    else:
        mutant["matching_upper_bound"] = certificate.constructive_lower_bound - 1
    certificate_contract_failure = int(
        not _verify_certificate(circuit, certificate.to_dict(), edges)
    )
    mutant_rejected = not _verify_certificate(circuit, mutant, edges)
    exact_solver_mismatch = int(
        certificate.exact_optimum is not None
        and certificate.exact_optimum != oracle["maximum_weight"]
    )
    return {
        "case_id": spec["case_id"],
        "stratum": spec["stratum"],
        "num_qubits": spec["num_qubits"],
        "gate_count": len(spec["operations"]),
        "model": model.value,
        "input_sha256": certificate.input_sha256,
        "oracle_maximum_weight": oracle["maximum_weight"],
        "oracle_topological_order_count": oracle["topological_order_count"],
        "production_candidate_count": certificate.candidate_count,
        "theorem_mismatch": pairwise_mismatch,
        "lb_gt_oracle": int(certificate.constructive_lower_bound > oracle["maximum_weight"]),
        "ub_lt_oracle": int(certificate.matching_upper_bound < oracle["maximum_weight"]),
        "exact_solver_mismatch": exact_solver_mismatch,
        "cgl_lb": certificate.constructive_lower_bound,
        "cgl_actual_weight": cgl_weight,
        "cgl_lb_shortfall": int(cgl_weight < certificate.constructive_lower_bound),
        "dependency_invalid": int(dependency_invalid),
        "equivalence_failure": int(cgl_equivalence_failure),
        "mutant_not_rejected": int(not mutant_rejected),
        "certificate_contract_failure": certificate_contract_failure,
        "status": certificate.status,
        "certificate": certificate.to_dict(),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _protocol_payload(cases_per_stratum: int, seed: int) -> dict[str, Any]:
    return {
        "protocol_id": PROTOCOL_ID,
        "seed": seed,
        "cases_per_stratum": cases_per_stratum,
        "strata": list(STRATA),
        "num_cases": cases_per_stratum * len(STRATA),
        "qubits": [2, 3, 4, 5],
        "gate_count": [4, 5, 6, 7, 8],
        "gate_alphabet": list(GATE_ALPHABET),
        "rotation_angles": ["-pi", "-pi/2", "pi/2", "pi"],
        "dependence_models": [model.value for model in DependenceModel],
        "topological_order_limit": 40320,
        "candidate_cap": 256,
        "beam_width": 8,
        "rule_library": "pair_v1",
        "tolerance": 1e-10,
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    integer_fields = (
        "theorem_mismatch", "lb_gt_oracle", "ub_lt_oracle", "exact_solver_mismatch",
        "cgl_lb_shortfall", "dependency_invalid", "equivalence_failure",
        "certificate_contract_failure", "mutant_not_rejected",
    )
    summary = {field: sum(int(row[field]) for row in rows) for field in integer_fields}
    summary["rows"] = len(rows)
    summary["case_count"] = len({row["case_id"] for row in rows})
    summary["model_counts"] = dict(Counter(row["model"] for row in rows))
    summary["status_counts"] = dict(Counter(row["status"] for row in rows))
    summary["max_topological_orders"] = max(
        (row["oracle_topological_order_count"] for row in rows), default=0
    )
    return summary


def run(mode: str, output_root: Path, seed: int = SEED) -> dict[str, Any]:
    if mode not in {"preflight", "formal"}:
        raise ValueError("mode_must_be_preflight_or_formal")
    cases_per_stratum = (
        PREFLIGHT_CASES_PER_STRATUM if mode == "preflight" else FORMAL_CASES_PER_STRATUM
    )
    protocol = _protocol_payload(cases_per_stratum, seed)
    if mode == "formal":
        preflight_receipt = (
            REPO_ROOT / "data" / "v12" / "e38_rewrite_exposure_oracle_preflight" / "receipt.json"
        )
        protocol["preflight_receipt_sha256"] = _sha256_bytes(preflight_receipt.read_bytes())
    cases = generate_panel(cases_per_stratum, seed)
    _write_json(output_root / "protocol.json", protocol)
    _write_jsonl(output_root / "inputs.jsonl", cases)
    protocol_sha256 = _sha256_json(protocol)
    input_sha256 = _sha256_bytes(
        (output_root / "inputs.jsonl").read_bytes()
    )
    rows = []
    for index, spec in enumerate(cases, start=1):
        for model in DependenceModel:
            rows.append(evaluate_case(spec, model))
        if index % 16 == 0:
            print(f"evaluated {index}/{len(cases)} cases", flush=True)
    summary = _summarize(rows)
    receipt = {
        "protocol_id": PROTOCOL_ID,
        "mode": mode,
        "protocol_sha256": protocol_sha256,
        "inputs_sha256": input_sha256,
        "summary": summary,
        "zero_tolerance": all(
            summary[field] == 0
            for field in (
                "theorem_mismatch", "lb_gt_oracle", "ub_lt_oracle", "exact_solver_mismatch",
                "cgl_lb_shortfall", "dependency_invalid", "equivalence_failure",
                "certificate_contract_failure", "mutant_not_rejected",
            )
        ),
    }
    _write_jsonl(output_root / "rows.jsonl", rows)
    _write_json(output_root / "summary.json", summary)
    _write_json(output_root / "receipt.json", receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "formal"), required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
    )
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    if args.mode == "formal":
        preflight = REPO_ROOT / "data" / "v12" / "e38_rewrite_exposure_oracle_preflight" / "receipt.json"
        if not preflight.is_file():
            raise SystemExit("formal_run_requires_preflight_receipt")
        payload = json.loads(preflight.read_text(encoding="utf-8"))
        if not payload.get("zero_tolerance"):
            raise SystemExit("formal_run_blocked_by_preflight")
    output_root = args.output_root or (
        REPO_ROOT / "data" / "v12" /
        ("e38_rewrite_exposure_oracle_preflight" if args.mode == "preflight" else "e38_rewrite_exposure_oracle")
    )
    receipt = run(args.mode, output_root, args.seed)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["zero_tolerance"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
