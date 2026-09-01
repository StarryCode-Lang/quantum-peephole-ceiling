"""Tests for the bounded equivalence decision-path agreement audit."""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from scripts.audit_equivalence_verifier_agreement import _manual_unitary, build_audit


def test_equivalence_verifiers_agree_and_unsupported_semantics_fail_closed():
    audit = build_audit(cases=16)
    assert audit["status"] == "PASS_ZERO_DISAGREEMENTS"
    assert audit["disagreement_count"] == 0
    assert audit["scope_failure_cases"] == []
    assert audit["challenge_failure_cases"] == []
    assert {record["case"] for record in audit["challenge_records"]} == {
        "global_phase", "known_equivalent_rewrite", "threshold_above", "threshold_below",
    }
    assert all(
        record["certificate_status"] == "unavailable"
        and record["certificate_accepted"] is False
        for record in audit["scope_records"]
    )
    assert audit["metric_dispositions"]["7.15"].startswith("PASS:")


def test_manual_semantic_kernel_matches_qiskit_only_as_an_external_oracle():
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.rx(0.37, 1)
    circuit.sx(2)
    circuit.cx(0, 2)
    circuit.cz(2, 1)
    circuit.rz(-0.41, 0)
    circuit.global_phase = 0.23
    assert np.allclose(_manual_unitary(circuit), Operator(circuit).data, atol=1e-12)
