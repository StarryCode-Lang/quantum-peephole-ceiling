"""Run a deterministic generative property audit over composed rewrites."""

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

import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator

from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher
DEFAULT_OUTPUT = ROOT / "release/rewrite_property_sweep_audit.json"
SEED = 20260824
CONFIGURATIONS = tuple(
    (template_enabled, gather_window)
    for template_enabled in (False, True)
    for gather_window in (4, 16, 64)
)
BOUNDARY_ANGLES = (
    ("zero_below", -1e-12),
    ("zero_above", 1e-12),
    ("pi_below", np.pi - 1e-12),
    ("pi_above", np.pi + 1e-12),
    ("two_pi_below", 2 * np.pi - 1e-12),
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _random_circuit(rng: random.Random, case: int) -> QuantumCircuit:
    qubits = rng.randint(2, 4)
    circuit = QuantumCircuit(qubits)
    for _ in range(rng.randint(8, 28)):
        gate = rng.choice(("h", "x", "z", "s", "sdg", "t", "tdg", "rx", "rz", "cx", "cz"))
        target = rng.randrange(qubits)
        if gate in {"cx", "cz"}:
            other = rng.randrange(qubits - 1)
            if other >= target:
                other += 1
            getattr(circuit, gate)(target, other)
        elif gate in {"rx", "rz"}:
            getattr(circuit, gate)(rng.choice((
                -np.pi, -np.pi / 2, -1e-12, 1e-12, np.pi / 4, np.pi / 2,
                np.pi - 1e-12, np.pi + 1e-12, 2 * np.pi - 1e-12,
            )), target)
        else:
            getattr(circuit, gate)(target)
    control, target = 0, 1
    injection = case % 6
    if injection == 0:
        circuit.h(control)
        circuit.cx(control, target)
        circuit.h(control)
    elif injection == 1:
        circuit.cx(control, target)
        circuit.cx(control, target)
    elif injection == 2:
        circuit.s(target)
        circuit.s(target)
    elif injection == 3:
        circuit.rz(np.pi / 4, target)
        circuit.rz(-np.pi / 4, target)
    elif injection == 4:
        circuit.h(target)
        circuit.cz(control, target)
        circuit.h(target)
    else:
        circuit.t(target)
        circuit.tdg(target)
    boundary_label, boundary_angle = BOUNDARY_ANGLES[case % len(BOUNDARY_ANGLES)]
    circuit.rz(boundary_angle, target)
    circuit.metadata = {
        **(circuit.metadata or {}),
        "audit_boundary_angle_label": boundary_label,
    }
    return circuit


def build_audit(*, cases_per_configuration: int = 40) -> dict[str, object]:
    records: list[dict[str, object]] = []
    for template_enabled, gather_window in CONFIGURATIONS:
        rng = random.Random(SEED)
        for case in range(cases_per_configuration):
            original = _random_circuit(rng, case)
            input_qasm_sha256 = hashlib.sha256(
                qasm2.dumps(original).encode("utf-8")
            ).hexdigest()
            optimizer = Phase2bTemplateMatcher(
                max_iterations=100,
                gather_window=gather_window,
                template_enabled=template_enabled,
                collect_trace=True,
            )
            try:
                first = optimizer.optimize_full_pipeline(original, target=original)
                optimized = first.optimized_circuit
                trace_sizes = [
                    int(record["gate_count"]) for record in first.metadata["trace"]
                ]
                second = optimizer.optimize_full_pipeline(optimized, target=optimized)
                properties = {
                    "operator_equivalent": bool(Operator(optimized).equiv(Operator(original))),
                    "gate_count_nonincreasing": optimized.size() <= original.size(),
                    "certificate_accepted": bool(
                        first.equivalence_certificate
                        and first.equivalence_certificate.get("accepted") is True
                    ),
                    "trace_nonincreasing": all(
                        right <= left for left, right in zip(trace_sizes, trace_sizes[1:])
                    ),
                    "terminated_at_rewrite_counter_fixpoint": bool(
                        first.metadata["trace"]
                        and optimizer._no_progress(first.metadata["trace"][-1])
                    ),
                    "second_pass_operator_equivalent": bool(
                        Operator(second.optimized_circuit).equiv(Operator(optimized))
                    ),
                    "second_pass_size_stable": (
                        second.optimized_circuit.size() == optimized.size()
                    ),
                    "second_pass_syntax_stable": (
                        qasm2.dumps(second.optimized_circuit) == qasm2.dumps(optimized)
                    ),
                }
                error = None
            except Exception as exception:  # pragma: no cover - retained in audit artifact
                properties = {}
                error = f"{type(exception).__name__}: {exception}"
            records.append({
                "template_enabled": template_enabled,
                "gather_window": gather_window,
                "case": case,
                "input_qasm_sha256": input_qasm_sha256,
                "boundary_angle_label": original.metadata["audit_boundary_angle_label"],
                "properties": properties,
                "error": error,
                "passed": error is None and all(properties.values()),
            })
    failures = [
        {
            "template_enabled": record["template_enabled"],
            "gather_window": record["gather_window"],
            "case": record["case"],
            "error": record["error"],
            "failed_properties": [
                name for name, passed in record["properties"].items() if not passed
            ],
        }
        for record in records if not record["passed"]
    ]
    unique_inputs = {
        record["input_qasm_sha256"]: record["boundary_angle_label"] for record in records
    }
    boundary_coverage = {
        label: sum(value == label for value in unique_inputs.values())
        for label, _ in BOUNDARY_ANGLES
    }
    return {
        "status": "PASS_ALL_GENERATIVE_PROPERTIES" if not failures else "FAIL",
        "seed": SEED,
        "configurations": [
            {"template_enabled": enabled, "gather_window": window}
            for enabled, window in CONFIGURATIONS
        ],
        "cases_per_configuration": cases_per_configuration,
        "total_cases": len(records),
        "paired_configuration_cells": len(records),
        "unique_circuits": len(unique_inputs),
        "boundary_angle_unique_circuit_coverage": boundary_coverage,
        "failure_count": len(failures),
        "failures": failures,
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
            "scripts/audit_rewrite_properties.py": _sha(Path(__file__)),
        },
        "interpretation": (
            "The paired sweep covers 40 unique generated two-to-four-qubit bound-unitary circuits "
            "under six rule/window configurations, with forced zero/pi/two-pi boundary angles; it "
            "is not an exhaustive proof over all circuits."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cases-per-configuration", type=int, default=40)
    args = parser.parse_args()
    if args.cases_per_configuration < 1:
        raise ValueError("cases-per-configuration must be positive")
    audit = build_audit(cases_per_configuration=args.cases_per_configuration)
    if audit["status"] != "PASS_ALL_GENERATIVE_PROPERTIES":
        raise RuntimeError("rewrite property sweep detected a failure")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({key: audit[key] for key in (
        "status", "total_cases", "failure_count",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
