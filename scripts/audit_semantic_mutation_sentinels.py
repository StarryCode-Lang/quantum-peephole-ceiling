"""Check that semantic test oracles kill targeted rewrite mutants."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qiskit.quantum_info import Operator

from scripts.audit_equivalence_verifier_agreement import _random_unitary_circuit
from src.equivalence import certify_equivalence
DEFAULT_OUTPUT = ROOT / "release/semantic_mutation_sentinel_audit.json"
SEED = 20260824
THRESHOLD = 0.999999999


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_audit(*, cases: int = 20) -> dict[str, object]:
    rng = random.Random(SEED)
    records: list[dict[str, object]] = []
    controls: list[dict[str, object]] = []
    for case in range(cases):
        qubits = 2 + case % 3
        original = _random_unitary_circuit(rng, qubits)
        target = case % qubits
        mutants = {}

        deleted = original.copy()
        del deleted.data[0]
        mutants["delete_first_instruction"] = deleted

        inserted_x = original.copy()
        inserted_x.x(target)
        mutants["insert_x"] = inserted_x

        inserted_phase = original.copy()
        inserted_phase.rz(0.125, target)
        mutants["perturb_phase"] = inserted_phase

        inserted_cx = original.copy()
        inserted_cx.cx(0, 1)
        mutants["insert_cx"] = inserted_cx

        for mutation, candidate in mutants.items():
            certificate = certify_equivalence(
                candidate, original, threshold=THRESHOLD, max_exact_qubits=12
            )
            independent_equivalent = bool(Operator(candidate).equiv(Operator(original)))
            records.append({
                "case": case,
                "mutation": mutation,
                "certificate_accepted": certificate.accepted,
                "certificate_status": certificate.status.value,
                "independent_operator_equivalent": independent_equivalent,
                "killed": not certificate.accepted and not independent_equivalent,
            })

        equivalent = original.copy()
        equivalent.x(target)
        equivalent.x(target)
        certificate = certify_equivalence(
            equivalent, original, threshold=THRESHOLD, max_exact_qubits=12
        )
        controls.append({
            "case": case,
            "control": "insert_x_inverse_pair",
            "certificate_accepted": certificate.accepted,
            "independent_operator_equivalent": bool(
                Operator(equivalent).equiv(Operator(original))
            ),
        })
    killed = sum(bool(record["killed"]) for record in records)
    controls_passed = sum(
        bool(record["certificate_accepted"] and record["independent_operator_equivalent"])
        for record in controls
    )
    status = (
        "PASS_ALL_TARGETED_MUTANTS_KILLED"
        if killed == len(records) and controls_passed == len(controls)
        else "FAIL"
    )
    return {
        "status": status,
        "seed": SEED,
        "cases": cases,
        "mutants": len(records),
        "mutants_killed": killed,
        "equivalent_controls": len(controls),
        "equivalent_controls_passed": controls_passed,
        "mutation_operators": [
            "delete_first_instruction", "insert_x", "perturb_phase", "insert_cx",
        ],
        "records": records,
        "controls": controls,
        "source_sha256": {
            "src/equivalence.py": _sha(ROOT / "src/equivalence.py"),
            "scripts/audit_equivalence_verifier_agreement.py": _sha(
                ROOT / "scripts/audit_equivalence_verifier_agreement.py"
            ),
            "scripts/audit_semantic_mutation_sentinels.py": _sha(Path(__file__)),
        },
        "interpretation": (
            "This is targeted semantic mutation coverage for four destructive operator classes, "
            "not a whole-program mutation score."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cases", type=int, default=20)
    args = parser.parse_args()
    if args.cases < 1:
        raise ValueError("cases must be positive")
    audit = build_audit(cases=args.cases)
    if audit["status"] != "PASS_ALL_TARGETED_MUTANTS_KILLED":
        raise RuntimeError("semantic mutation sentinel audit failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({key: audit[key] for key in (
        "status", "mutants", "mutants_killed", "equivalent_controls_passed",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
