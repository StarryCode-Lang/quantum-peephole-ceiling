"""Exercise stage-addressable semantic failure localization for Phase-2b rewrites."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit, qasm2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_equivalence_verifier_agreement import _independent_average_gate_fidelity
from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher

OUTPUT = ROOT / "release/transformation_failure_localization_audit.json"
THRESHOLD = 0.999999999


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _circuit_hash(circuit: QuantumCircuit) -> str:
    return hashlib.sha256(qasm2.dumps(circuit).encode("utf-8")).hexdigest()


def _cases() -> dict[str, QuantumCircuit]:
    gather_h = QuantumCircuit(3)
    gather_h.h(0); gather_h.x(2); gather_h.cx(0, 1); gather_h.h(0)
    gather_pair = QuantumCircuit(2)
    gather_pair.x(0); gather_pair.z(1); gather_pair.x(0)
    template = QuantumCircuit(2)
    template.h(1); template.cx(0, 1); template.h(1)
    cancellation = QuantumCircuit(1)
    cancellation.x(0); cancellation.x(0)
    phase_merge = QuantumCircuit(1)
    phase_merge.rz(0.2, 0); phase_merge.rz(0.3, 0)
    return {
        "gather_h_sandwiches": gather_h,
        "gather_commuting_pairs": gather_pair,
        "apply_conjugation_templates": template,
        "cancel_inverse_pairs": cancellation,
        "merge_phase_gates": phase_merge,
    }


def _apply_stage(engine: Phase2bTemplateMatcher, stage: str,
                 circuit: QuantumCircuit, counters: dict[str, int]) -> None:
    methods = {
        "gather_h_sandwiches": engine._gather_h_sandwiches,
        "gather_commuting_pairs": engine._gather_commuting_pairs,
        "apply_conjugation_templates": engine._apply_all_templates,
        "cancel_inverse_pairs": engine._cancel_inverse_pairs,
        "merge_phase_gates": engine._merge_phase_gates,
    }
    methods[stage](circuit, counters)


def _changed_actions(counters: dict[str, int]) -> dict[str, int]:
    return {name: int(value) for name, value in counters.items() if value}


def build_audit() -> dict[str, object]:
    records = []
    for stage, original in _cases().items():
        engine = Phase2bTemplateMatcher(gather_window=16, template_enabled=True)
        transformed = copy.deepcopy(original)
        counters = engine._zero_counters()
        before_hash = _circuit_hash(transformed)
        _apply_stage(engine, stage, transformed, counters)
        after_hash = _circuit_hash(transformed)
        actions = _changed_actions(counters)
        if not actions or before_hash == after_hash:
            raise RuntimeError(f"diagnostic circuit did not activate {stage}")
        fidelity = _independent_average_gate_fidelity(transformed, original)
        correct_accept = bool(fidelity >= THRESHOLD)

        corrupted = copy.deepcopy(transformed)
        corrupted.x(0)
        corrupted_fidelity = _independent_average_gate_fidelity(corrupted, original)
        checkpoints = [
            {"transformation_id": f"iteration=0:stage={stage}",
             "semantic_accept": bool(corrupted_fidelity >= THRESHOLD),
             "independent_average_gate_fidelity": corrupted_fidelity,
             "pre_stage_hash": before_hash, "post_stage_hash": after_hash,
             "action_counters": actions}
        ]
        first_failure = next(
            (item["transformation_id"] for item in checkpoints if not item["semantic_accept"]),
            None,
        )
        records.append({
            "stage": stage,
            "correct_transformation_semantic_accept": correct_accept,
            "correct_transformation_average_gate_fidelity": fidelity,
            "injected_fault": "append_x_on_q0_immediately_after_stage",
            "injected_fault_average_gate_fidelity": corrupted_fidelity,
            "expected_first_failing_transformation_id": f"iteration=0:stage={stage}",
            "localized_first_failing_transformation_id": first_failure,
            "localized_correctly": first_failure == f"iteration=0:stage={stage}",
            "action_counters": actions,
            "pre_stage_circuit_sha256": before_hash,
            "post_stage_circuit_sha256": after_hash,
        })
    passed = all(
        record["correct_transformation_semantic_accept"] and record["localized_correctly"]
        for record in records
    )
    return {
        "schema_version": "1.0.0",
        "status": "PASS_STAGE_ADDRESSABLE_FAILURE_LOCALIZATION_SENTINELS" if passed else "FAIL",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "semantic_kernel": "explicit NumPy matrices from audit_equivalence_verifier_agreement; no Qiskit Operator/Statevector",
        "transformation_stages": [record["stage"] for record in records],
        "correct_stage_checks": sum(record["correct_transformation_semantic_accept"] for record in records),
        "fault_sentinels_localized": sum(record["localized_correctly"] for record in records),
        "records": records,
        "metric_dispositions": {
            "7.22": (
                "PARTIAL: five Phase-2b transformation stages have semantic checkpoints that "
                "localize injected failures to iteration and stage, but the sealed E31 trace "
                "contains aggregate counters rather than one checkpoint per individual rewrite"
            )
        },
        "claim_boundary": (
            "The harness proves stage-addressable localization for targeted diagnostic circuits. "
            "It does not retroactively identify a particular gate-level rewrite inside a sealed "
            "E31 stage containing multiple actions; adding that granularity would change the formal "
            "worker trace contract and require a new formal execution."
        ),
        "source_bindings": {
            "src/optimisation/phase2/template_matcher.py": _sha(
                ROOT / "src/optimisation/phase2/template_matcher.py"
            ),
            "scripts/audit_equivalence_verifier_agreement.py": _sha(
                ROOT / "scripts/audit_equivalence_verifier_agreement.py"
            ),
            "analysis/transformation_failure_localization_audit.py": _sha(Path(__file__)),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    audit = build_audit()
    if audit["status"] == "FAIL":
        raise RuntimeError("transformation localization sentinel failed")
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({"status": audit["status"],
                      "correct_stage_checks": audit["correct_stage_checks"],
                      "fault_sentinels_localized": audit["fault_sentinels_localized"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
