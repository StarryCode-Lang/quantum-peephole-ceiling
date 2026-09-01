"""Run bounded qubit-permutation metamorphic checks on equivalence decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.equivalence import certify_equivalence


DEFAULT_OUTPUT = ROOT / "release/qubit_permutation_metamorphic_audit.json"
SEED = 719031


def _permute(circuit: QuantumCircuit, permutation: list[int]) -> QuantumCircuit:
    output = QuantumCircuit(circuit.num_qubits)
    for instruction in circuit.data:
        qargs = [permutation[circuit.find_bit(qubit).index] for qubit in instruction.qubits]
        output.append(instruction.operation.copy(), qargs)
    return output


def _base_circuit(rng: np.random.RandomState, n_qubits: int, gates: int) -> QuantumCircuit:
    circuit = QuantumCircuit(n_qubits)
    for _ in range(gates):
        gate = int(rng.randint(0, 6))
        q0 = int(rng.randint(0, n_qubits))
        if gate == 0:
            circuit.h(q0)
        elif gate == 1:
            circuit.x(q0)
        elif gate == 2:
            circuit.rx(float(rng.uniform(-np.pi, np.pi)), q0)
        elif gate == 3:
            circuit.rz(float(rng.uniform(-np.pi, np.pi)), q0)
        else:
            q1 = int(rng.randint(0, n_qubits - 1))
            if q1 >= q0:
                q1 += 1
            (circuit.cx if gate == 4 else circuit.cz)(q0, q1)
    return circuit


def build_audit(cases: int = 40) -> dict[str, object]:
    rng = np.random.RandomState(SEED)
    records: list[dict[str, object]] = []
    for case in range(cases):
        n_qubits = 2 + case % 4
        original = _base_circuit(rng, n_qubits, 8 + case % 9)
        equivalent = original.copy()
        equivalent.x(0)
        equivalent.x(0)
        mutant = original.copy()
        mutant.x(0)
        permutation = list(map(int, rng.permutation(n_qubits)))
        if permutation == list(range(n_qubits)):
            permutation = permutation[1:] + permutation[:1]

        permuted_original = _permute(original, permutation)
        permuted_equivalent = _permute(equivalent, permutation)
        permuted_mutant = _permute(mutant, permutation)
        decisions = {
            "equivalent_original": certify_equivalence(original, equivalent, threshold=1 - 1e-10).accepted,
            "equivalent_permuted": certify_equivalence(
                permuted_original, permuted_equivalent, threshold=1 - 1e-10
            ).accepted,
            "mutant_original": certify_equivalence(original, mutant, threshold=1 - 1e-10).accepted,
            "mutant_permuted": certify_equivalence(
                permuted_original, permuted_mutant, threshold=1 - 1e-10
            ).accepted,
        }
        independent = {
            "equivalent_original": bool(Operator(original).equiv(Operator(equivalent))),
            "equivalent_permuted": bool(Operator(permuted_original).equiv(Operator(permuted_equivalent))),
            "mutant_original": bool(Operator(original).equiv(Operator(mutant))),
            "mutant_permuted": bool(Operator(permuted_original).equiv(Operator(permuted_mutant))),
        }
        passed = decisions == independent == {
            "equivalent_original": True,
            "equivalent_permuted": True,
            "mutant_original": False,
            "mutant_permuted": False,
        }
        records.append(
            {
                "case": case,
                "n_qubits": n_qubits,
                "permutation": permutation,
                "decisions": decisions,
                "operator_cross_check": independent,
                "passed": passed,
            }
        )

    failures = [record for record in records if not record["passed"]]
    if failures:
        raise RuntimeError(f"qubit-permutation metamorphic failures: {len(failures)}")
    source = ROOT / "src/equivalence.py"
    return {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_ALL_QUBIT_PERMUTATION_METAMORPHIC_CHECKS",
        "seed": SEED,
        "cases": cases,
        "equivalence_decisions_checked": cases * 4,
        "nonidentity_permutations_checked": cases,
        "failures": 0,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "records": records,
        "interpretation": (
            "Simultaneous global qubit relabeling preserved acceptance of identity rewrites and "
            "rejection of X-insertion mutants in every bounded seeded case."
        ),
        "limitation": (
            "The Operator cross-check shares Qiskit's circuit semantics and is not a second "
            "independent verifier implementation."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cases", type=int, default=40)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_audit(args.cases)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": output.relative_to(ROOT).as_posix(), "status": payload["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
