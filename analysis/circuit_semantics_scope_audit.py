"""Generate a machine-readable audit of the equivalence contract's circuit scope."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit import Parameter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.equivalence import EquivalenceStatus, certify_equivalence


DEFAULT_OUTPUT = ROOT / "release/circuit_semantics_scope_audit.json"


def _certificate(circuit: QuantumCircuit, target: QuantumCircuit) -> dict[str, object]:
    return certify_equivalence(circuit, target, threshold=1 - 1e-12).to_dict()


def build_audit() -> dict[str, object]:
    quantum = QuantumRegister(1, "q")
    ancilla = AncillaRegister(1, "anc")
    with_ancilla = QuantumCircuit(quantum, ancilla)
    with_ancilla.h(quantum[0])
    with_ancilla.h(quantum[0])
    ancilla_target = QuantumCircuit(quantum, ancilla)
    ancilla_certificate = _certificate(with_ancilla, ancilla_target)

    barrier_circuit = QuantumCircuit(1)
    barrier_circuit.h(0)
    barrier_circuit.barrier(0)
    barrier_circuit.h(0)
    barrier_certificate = _certificate(barrier_circuit, QuantumCircuit(1))

    measure = QuantumCircuit(1, 1)
    measure.measure(0, 0)
    measure_certificate = _certificate(measure, measure.copy())

    reset = QuantumCircuit(1)
    reset.reset(0)
    reset_certificate = _certificate(reset, reset.copy())

    quantum_dynamic = QuantumRegister(1, "q")
    classical_dynamic = ClassicalRegister(1, "c")
    dynamic = QuantumCircuit(quantum_dynamic, classical_dynamic)
    with dynamic.if_test((classical_dynamic[0], True)):
        dynamic.x(quantum_dynamic[0])
    dynamic_certificate = _certificate(dynamic, dynamic.copy())

    theta = Parameter("theta")
    parameterized = QuantumCircuit(1)
    parameterized.rx(theta, 0)
    parameterized_certificate = _certificate(parameterized, parameterized.copy())

    sampled = QuantumCircuit(2)
    sampled.rx(0.37, 0)
    sampled.rx(-0.37, 0)
    sampled_certificate = certify_equivalence(
        sampled,
        QuantumCircuit(2),
        threshold=1 - 1e-12,
        max_exact_qubits=1,
        n_samples=256,
        rng=np.random.RandomState(7013),
    ).to_dict()

    assert ancilla_certificate["status"] == EquivalenceStatus.VERIFIED_EQUIVALENT.value
    assert barrier_certificate["status"] == EquivalenceStatus.VERIFIED_EQUIVALENT.value
    assert measure_certificate["status"] == EquivalenceStatus.UNAVAILABLE.value
    assert "measure" in measure_certificate["evidence"]["blockers"]
    assert reset_certificate["status"] == EquivalenceStatus.UNAVAILABLE.value
    assert "reset" in reset_certificate["evidence"]["blockers"]
    assert dynamic_certificate["status"] == EquivalenceStatus.UNAVAILABLE.value
    assert "classical_bits" in dynamic_certificate["evidence"]["blockers"]
    assert "if_else" in dynamic_certificate["evidence"]["blockers"]
    assert parameterized_certificate["status"] == EquivalenceStatus.UNAVAILABLE.value
    assert parameterized_certificate["evidence"]["free_parameters"] == ["theta"]
    assert sampled_certificate["method"] == "sampled_global_haar"
    assert sampled_certificate["status"] == "estimated_equivalent"
    assert sampled_certificate["samples"] == 256

    return {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_EXPLICIT_FAIL_CLOSED_CIRCUIT_SEMANTICS_SCOPE",
        "contract": "fixed-width bound-parameter unitary circuits, up to global phase",
        "policy": {
            "ancilla": "SUPPORTED_AS_DECLARED_QUBITS_WITHIN_FIXED_WIDTH_UNITARY_SCOPE",
            "barrier": "SUPPORTED_AS_A_SEMANTIC_NO_OP_WITHIN_UNITARY_SCOPE",
            "measurement": "REJECTED_FAIL_CLOSED_AS_NONUNITARY",
            "reset": "REJECTED_FAIL_CLOSED_AS_NONUNITARY",
            "classical_control": "REJECTED_FAIL_CLOSED",
            "dynamic_control_flow": "REJECTED_FAIL_CLOSED",
            "free_parameters": "REJECTED_FAIL_CLOSED_NO_SYMBOLIC_OR_FINITE_POINT_SUBSTITUTION",
            "large_nonclifford_sampling": "GLOBAL_COMPLEX_GAUSSIAN_NORMALIZATION_EQUIVALENT_TO_HAAR_WITH_FULL_SUPPORT_BUT_FINITE_PROBABILISTIC_COVERAGE",
        },
        "scenarios": {
            "declared_ancilla_nonstructural_identity": ancilla_certificate,
            "barrier_nonstructural_identity": barrier_certificate,
            "measurement": measure_certificate,
            "reset": reset_certificate,
            "classical_dynamic_if": dynamic_certificate,
            "free_parameter": parameterized_certificate,
            "global_haar_sampled_identity": sampled_certificate,
        },
        "limitations": [
            "Ancilla support means declared extra qubits in a fixed-width unitary operator; it does not establish dynamic allocation or clean-ancilla recovery semantics.",
            "Measurement, reset, classical operands or conditions, and dynamic control flow are outside the verifier contract and return unavailable rather than an equivalence claim.",
            "Free parameters are neither symbolically verified nor checked at finitely selected parameter values; callers must bind them first.",
            "Normalized complex-Gaussian state draws implement global Haar sampling with full distributional support over pure Hilbert-space states, but any finite sample is probabilistic rather than exhaustive.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_audit()
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": output.relative_to(ROOT).as_posix(), "status": payload["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
