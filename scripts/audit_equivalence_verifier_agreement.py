"""Build a deterministic verifier-versus-verifier disagreement audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import Operator

from src.equivalence import certify_equivalence
DEFAULT_OUTPUT = ROOT / "release/equivalence_verifier_agreement_audit.json"
SEED = 20260824
THRESHOLD = 0.999999999


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _random_unitary_circuit(rng: random.Random, qubits: int) -> QuantumCircuit:
    circuit = QuantumCircuit(qubits)
    for _ in range(rng.randint(6, 24)):
        gate = rng.choice(("h", "x", "z", "s", "t", "rx", "rz", "cx", "cz"))
        first = rng.randrange(qubits)
        if gate in {"cx", "cz"} and qubits > 1:
            second = rng.randrange(qubits - 1)
            if second >= first:
                second += 1
            getattr(circuit, gate)(first, second)
        elif gate in {"rx", "rz"}:
            getattr(circuit, gate)(rng.choice((-0.75, -0.25, 0.25, 0.75)), first)
        elif gate not in {"cx", "cz"}:
            getattr(circuit, gate)(first)
    return circuit


def _manual_gate_matrix(name: str, params: tuple[float, ...]) -> np.ndarray:
    """Return a gate matrix without using Qiskit's simulation primitives."""
    if name == "id":
        return np.eye(2, dtype=complex)
    if name == "h":
        return np.array(((1, 1), (1, -1)), dtype=complex) / math.sqrt(2)
    if name == "x":
        return np.array(((0, 1), (1, 0)), dtype=complex)
    if name == "y":
        return np.array(((0, -1j), (1j, 0)), dtype=complex)
    if name == "z":
        return np.diag((1, -1)).astype(complex)
    if name in {"s", "sdg", "t", "tdg"}:
        phase = {"s": math.pi / 2, "sdg": -math.pi / 2,
                 "t": math.pi / 4, "tdg": -math.pi / 4}[name]
        return np.diag((1, np.exp(1j * phase))).astype(complex)
    if name in {"rx", "ry", "rz", "p"}:
        theta = float(params[0])
        if name == "rx":
            return np.array(((math.cos(theta / 2), -1j * math.sin(theta / 2)),
                             (-1j * math.sin(theta / 2), math.cos(theta / 2))), dtype=complex)
        if name == "ry":
            return np.array(((math.cos(theta / 2), -math.sin(theta / 2)),
                             (math.sin(theta / 2), math.cos(theta / 2))), dtype=complex)
        if name == "rz":
            return np.diag((np.exp(-0.5j * theta), np.exp(0.5j * theta))).astype(complex)
        return np.diag((1, np.exp(1j * theta))).astype(complex)
    if name in {"sx", "sxdg"}:
        sign = 1 if name == "sx" else -1
        return 0.5 * np.array(((1 + 1j * sign, 1 - 1j * sign),
                              (1 - 1j * sign, 1 + 1j * sign)), dtype=complex)
    if name == "u":
        theta, phi, lam = (float(value) for value in params)
        return np.array(
            ((math.cos(theta / 2), -np.exp(1j * lam) * math.sin(theta / 2)),
             (np.exp(1j * phi) * math.sin(theta / 2),
              np.exp(1j * (phi + lam)) * math.cos(theta / 2))),
            dtype=complex,
        )
    raise ValueError(f"unsupported gate in independent semantic kernel: {name}")


def _manual_unitary(circuit: QuantumCircuit) -> np.ndarray:
    """Construct a little-endian unitary using only explicit NumPy algebra."""
    qubits = circuit.num_qubits
    dimension = 1 << qubits
    unitary = np.eye(dimension, dtype=complex)
    for instruction in circuit.data:
        operation = instruction.operation
        name = operation.name
        targets = tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits)
        if name == "barrier":
            continue
        if name in {"cx", "cz"}:
            if len(targets) != 2:
                raise ValueError(f"{name} requires two qubits")
            control, target = targets
            full = np.zeros((dimension, dimension), dtype=complex)
            for basis in range(dimension):
                mapped = basis
                phase = 1.0
                if name == "cx" and ((basis >> control) & 1):
                    mapped ^= 1 << target
                elif name == "cz" and ((basis >> control) & 1) and ((basis >> target) & 1):
                    phase = -1.0
                full[mapped, basis] = phase
        else:
            if len(targets) != 1:
                raise ValueError(f"unsupported arity for {name}: {len(targets)}")
            gate = _manual_gate_matrix(name, tuple(float(value) for value in operation.params))
            factors = [gate if qubit == targets[0] else np.eye(2, dtype=complex)
                       for qubit in reversed(range(qubits))]
            full = factors[0]
            for factor in factors[1:]:
                full = np.kron(full, factor)
        unitary = full @ unitary
    return np.exp(1j * float(circuit.global_phase)) * unitary


def _independent_average_gate_fidelity(left: QuantumCircuit, right: QuantumCircuit) -> float:
    left_matrix = _manual_unitary(left)
    right_matrix = _manual_unitary(right)
    dimension = left_matrix.shape[0]
    overlap = abs(np.trace(left_matrix.conj().T @ right_matrix))
    return float((overlap * overlap + dimension) / (dimension * (dimension + 1)))


def build_audit(*, cases: int = 100) -> dict[str, object]:
    rng = random.Random(SEED)
    records: list[dict[str, object]] = []
    for case in range(cases):
        qubits = 1 + case % 4
        original = _random_unitary_circuit(rng, qubits)
        expected_equivalent = case % 2 == 0
        candidate = original.copy()
        if expected_equivalent:
            target = case % qubits
            candidate.x(target)
            candidate.x(target)
        else:
            candidate.x(case % qubits)
        certificate = certify_equivalence(
            candidate, original, threshold=THRESHOLD, max_exact_qubits=12
        )
        operator_equivalent = bool(Operator(candidate).equiv(Operator(original)))
        independent_fidelity = _independent_average_gate_fidelity(candidate, original)
        independent_accept = independent_fidelity >= THRESHOLD
        agreement = (
            certificate.accepted == operator_equivalent == independent_accept
            and operator_equivalent == expected_equivalent
        )
        records.append({
            "case": case,
            "qubits": qubits,
            "expected_equivalent": expected_equivalent,
            "certificate_method": certificate.method.value,
            "certificate_status": certificate.status.value,
            "certificate_accepted": certificate.accepted,
            "operator_equivalent": operator_equivalent,
            "independent_average_gate_fidelity": independent_fidelity,
            "independent_threshold_accept": independent_accept,
            "agreement": agreement,
        })

    theta = Parameter("theta")
    parameterized = QuantumCircuit(1)
    parameterized.rx(theta, 0)
    measured = QuantumCircuit(1, 1)
    measured.measure(0, 0)
    scope_records = []
    for name, circuit in (("free_parameter", parameterized), ("measurement", measured)):
        certificate = certify_equivalence(circuit, circuit, threshold=THRESHOLD)
        scope_records.append({
            "case": name,
            "certificate_status": certificate.status.value,
            "certificate_method": certificate.method.value,
            "certificate_accepted": certificate.accepted,
            "independent_matrix_comparison": "NOT_APPLICABLE_OUTSIDE_BOUND_UNITARY_SCOPE",
            "reason": certificate.evidence.get("reason"),
        })
    disagreements = [record["case"] for record in records if not record["agreement"]]
    scope_failures = [
        record["case"] for record in scope_records
        if record["certificate_status"] != "unavailable" or record["certificate_accepted"]
    ]
    challenge_specs = []
    identity = QuantumCircuit(1)
    global_phase = QuantumCircuit(1)
    global_phase.global_phase = np.pi / 7
    challenge_specs.append(("global_phase", global_phase, identity, True))
    rewritten_z = QuantumCircuit(1)
    rewritten_z.h(0)
    rewritten_z.x(0)
    rewritten_z.h(0)
    direct_z = QuantumCircuit(1)
    direct_z.z(0)
    challenge_specs.append(("known_equivalent_rewrite", rewritten_z, direct_z, True))
    for label, target_fidelity, expected in (
        ("threshold_above", THRESHOLD + 5e-10, True),
        ("threshold_below", THRESHOLD - 5e-10, False),
    ):
        angle = 2 * math.acos(math.sqrt((3 * target_fidelity - 1) / 2))
        rotated = QuantumCircuit(1)
        rotated.rz(angle, 0)
        challenge_specs.append((label, rotated, identity, expected))
    challenge_records = []
    for label, candidate, original, expected in challenge_specs:
        certificate = certify_equivalence(
            candidate, original, threshold=THRESHOLD, max_exact_qubits=12
        )
        operator_equivalent = bool(Operator(candidate).equiv(Operator(original)))
        independent_fidelity = _independent_average_gate_fidelity(candidate, original)
        threshold_accept = independent_fidelity >= THRESHOLD
        challenge_records.append({
            "case": label,
            "expected_threshold_accept": expected,
            "certificate_accepted": certificate.accepted,
            "operator_equivalent": operator_equivalent,
            "matrix_trace_average_gate_fidelity": independent_fidelity,
            "matrix_trace_threshold_accept": threshold_accept,
            "agreement": (
                certificate.accepted == threshold_accept == expected
                and (operator_equivalent if not label.startswith("threshold_") else True)
            ),
        })
    challenge_failures = [
        record["case"] for record in challenge_records if not record["agreement"]
    ]
    return {
        "status": (
            "PASS_ZERO_DISAGREEMENTS"
            if not disagreements and not scope_failures and not challenge_failures else "FAIL"
        ),
        "seed": SEED,
        "threshold": THRESHOLD,
        "unitary_cases": cases,
        "disagreement_count": len(disagreements),
        "disagreement_cases": disagreements,
        "scope_failure_cases": scope_failures,
        "scope_records": scope_records,
        "challenge_failure_cases": challenge_failures,
        "challenge_records": challenge_records,
        "records": records,
        "methods": [
            "project fail-closed equivalence certificate",
            "qiskit.quantum_info.Operator.equiv",
            "independent explicit NumPy gate matrices and matrix-trace fidelity",
        ],
        "metric_dispositions": {
            "7.15": (
                "PASS: an explicit NumPy semantic kernel independently reconstructs the "
                "bounded unitary cases without Qiskit Operator or Statevector simulation"
            ),
        },
        "source_sha256": {
            "src/equivalence.py": _sha(ROOT / "src/equivalence.py"),
            "scripts/audit_equivalence_verifier_agreement.py": _sha(Path(__file__)),
        },
        "interpretation": (
            "Agreement is established across the project certificate, Qiskit Operator.equiv, and "
            "a bounded independent NumPy gate-matrix implementation, including global-phase, "
            "known-rewrite, and threshold challenges. Independence is semantic-kernel independence, "
            "not an external organization or independently authored replication."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cases", type=int, default=100)
    args = parser.parse_args()
    if args.cases < 1:
        raise ValueError("cases must be positive")
    audit = build_audit(cases=args.cases)
    if audit["status"] != "PASS_ZERO_DISAGREEMENTS":
        raise RuntimeError("equivalence verifiers disagree or a scope guard failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({key: audit[key] for key in (
        "status", "unitary_cases", "disagreement_count", "scope_failure_cases",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
