"""Deterministic generative properties for composed Phase-2 rewrites."""

from scripts.audit_rewrite_properties import build_audit


def test_composed_rewrite_properties_across_seeded_random_circuits():
    audit = build_audit(cases_per_configuration=4)
    assert audit["status"] == "PASS_ALL_GENERATIVE_PROPERTIES"
    assert audit["total_cases"] == 24
    assert audit["paired_configuration_cells"] == 24
    assert audit["unique_circuits"] == 4
    assert len({record["input_qasm_sha256"] for record in audit["records"]}) == 4
    assert all(
        record["properties"]["second_pass_syntax_stable"]
        for record in audit["records"]
    )
    assert audit["failure_count"] == 0
