"""Audit rewrite-order conflicts and bounded non-confluence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qiskit import qasm2
from qiskit.quantum_info import Operator

from scripts.audit_rewrite_properties import _random_circuit
from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher
DEFAULT_OUTPUT = ROOT / "release/rewrite_order_confluence_audit.json"
SEED = 20260824
PASS_ORDERS = {
    "frozen_default": (
        "gather_h", "gather_pairs", "templates", "cancel", "merge",
    ),
    "simplify_first": (
        "cancel", "merge", "gather_h", "gather_pairs", "templates",
    ),
    "templates_first": (
        "templates", "cancel", "merge", "gather_h", "gather_pairs",
    ),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_order(circuit, order: tuple[str, ...]):
    engine = Phase2bTemplateMatcher(
        max_iterations=100, gather_window=64, template_enabled=True,
    )
    optimized = copy.deepcopy(circuit)
    operations = {
        "gather_h": engine._gather_h_sandwiches,
        "gather_pairs": engine._gather_commuting_pairs,
        "templates": engine._apply_all_templates,
        "cancel": engine._cancel_inverse_pairs,
        "merge": engine._merge_phase_gates,
    }
    iterations = 0
    converged = False
    structural_cycle_detected = False
    seen = {qasm2.dumps(optimized)}
    for iteration in range(engine.max_iterations):
        before = qasm2.dumps(optimized)
        counters = engine._zero_counters()
        for name in order:
            operations[name](optimized, counters)
        iterations = iteration + 1
        after = qasm2.dumps(optimized)
        if after == before:
            converged = True
            break
        if after in seen:
            structural_cycle_detected = True
            break
        seen.add(after)
    return optimized, iterations, converged, structural_cycle_detected


def build_audit(*, cases: int = 60) -> dict[str, object]:
    rng = random.Random(SEED)
    records: list[dict[str, object]] = []
    semantic_failures: list[dict[str, object]] = []
    convergence_failures: list[dict[str, object]] = []
    for case in range(cases):
        original = _random_circuit(rng, case)
        outputs = {}
        for name, order in PASS_ORDERS.items():
            optimized, iterations, converged, structural_cycle = _run_order(original, order)
            equivalent = bool(Operator(optimized).equiv(Operator(original)))
            output_text = qasm2.dumps(optimized)
            outputs[name] = {
                "gate_count": optimized.size(),
                "iterations": iterations,
                "qasm_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
                "operator_equivalent": equivalent,
                "converged_at_structural_fixpoint": converged,
                "structural_cycle_detected": structural_cycle,
            }
            if not equivalent:
                semantic_failures.append({
                    "case": case,
                    "pass_order": name,
                })
            if not converged:
                convergence_failures.append({"case": case, "pass_order": name})
        distinct_syntax = len({record["qasm_sha256"] for record in outputs.values()})
        distinct_sizes = len({record["gate_count"] for record in outputs.values()})
        records.append({
            "case": case,
            "outputs": outputs,
            "distinct_syntax_outputs": distinct_syntax,
            "distinct_gate_counts": distinct_sizes,
            "gate_count_spread": (
                max(record["gate_count"] for record in outputs.values())
                - min(record["gate_count"] for record in outputs.values())
            ),
        })
    syntax_nonconfluent = sum(record["distinct_syntax_outputs"] > 1 for record in records)
    cost_nonconfluent = sum(record["distinct_gate_counts"] > 1 for record in records)
    structural_cycles = sum(
        bool(output["structural_cycle_detected"])
        for record in records for output in record["outputs"].values()
    )
    return {
        "status": (
            "PASS_AUDIT_COMPLETE"
            if not semantic_failures and not convergence_failures else "FAIL"
        ),
        "seed": SEED,
        "cases": cases,
        "pass_orders": {name: list(order) for name, order in PASS_ORDERS.items()},
        "semantic_failure_count": len(semantic_failures),
        "semantic_failures": semantic_failures,
        "convergence_failure_count": len(convergence_failures),
        "convergence_failures": convergence_failures,
        "structural_cycle_count": structural_cycles,
        "syntax_nonconfluent_cases": syntax_nonconfluent,
        "cost_nonconfluent_cases": cost_nonconfluent,
        "maximum_gate_count_spread": max(record["gate_count_spread"] for record in records),
        "records": records,
        "source_sha256": {
            "src/optimisation/phase2/template_matcher.py": _sha(
                ROOT / "src/optimisation/phase2/template_matcher.py"
            ),
            "src/optimisation/base.py": _sha(ROOT / "src/optimisation/base.py"),
            "src/optimisation/constants.py": _sha(
                ROOT / "src/optimisation/constants.py"
            ),
            "src/equivalence.py": _sha(ROOT / "src/equivalence.py"),
            "scripts/audit_rewrite_properties.py": _sha(
                ROOT / "scripts/audit_rewrite_properties.py"
            ),
            "scripts/audit_rewrite_order_confluence.py": _sha(Path(__file__)),
        },
        "interpretation": (
            "PASS means the bounded order-sensitivity audit completed without semantic drift; "
            "syntax or cost divergence is reported as non-confluence, not hidden as failure."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cases", type=int, default=60)
    args = parser.parse_args()
    if args.cases < 1:
        raise ValueError("cases must be positive")
    audit = build_audit(cases=args.cases)
    if audit["status"] != "PASS_AUDIT_COMPLETE":
        raise RuntimeError("rewrite-order audit found semantic drift")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({key: audit[key] for key in (
        "status", "cases", "semantic_failure_count", "syntax_nonconfluent_cases",
        "convergence_failure_count", "structural_cycle_count", "cost_nonconfluent_cases",
        "maximum_gate_count_spread",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
