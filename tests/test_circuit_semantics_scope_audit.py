from analysis.circuit_semantics_scope_audit import build_audit


def test_circuit_semantics_scope_audit_is_explicit_and_fail_closed():
    audit = build_audit()

    assert audit["status"] == "PASS_EXPLICIT_FAIL_CLOSED_CIRCUIT_SEMANTICS_SCOPE"
    assert audit["policy"] == {
        "ancilla": "SUPPORTED_AS_DECLARED_QUBITS_WITHIN_FIXED_WIDTH_UNITARY_SCOPE",
        "barrier": "SUPPORTED_AS_A_SEMANTIC_NO_OP_WITHIN_UNITARY_SCOPE",
        "measurement": "REJECTED_FAIL_CLOSED_AS_NONUNITARY",
        "reset": "REJECTED_FAIL_CLOSED_AS_NONUNITARY",
        "classical_control": "REJECTED_FAIL_CLOSED",
        "dynamic_control_flow": "REJECTED_FAIL_CLOSED",
        "free_parameters": "REJECTED_FAIL_CLOSED_NO_SYMBOLIC_OR_FINITE_POINT_SUBSTITUTION",
        "large_nonclifford_sampling": "GLOBAL_COMPLEX_GAUSSIAN_NORMALIZATION_EQUIVALENT_TO_HAAR_WITH_FULL_SUPPORT_BUT_FINITE_PROBABILISTIC_COVERAGE",
    }
    assert audit["scenarios"]["declared_ancilla_nonstructural_identity"]["is_verified"]
    assert audit["scenarios"]["barrier_nonstructural_identity"]["is_verified"]
    for scenario in ("measurement", "reset", "classical_dynamic_if"):
        assert not audit["scenarios"][scenario]["accepted"]
    assert not audit["scenarios"]["free_parameter"]["accepted"]
    sampled = audit["scenarios"]["global_haar_sampled_identity"]
    assert sampled["method"] == "sampled_global_haar"
    assert sampled["samples"] == 256
