"""Tests for the targeted semantic mutation-sentinel audit."""

from scripts.audit_semantic_mutation_sentinels import build_audit


def test_targeted_semantic_mutants_are_killed_and_equivalent_controls_survive():
    audit = build_audit(cases=4)
    assert audit["status"] == "PASS_ALL_TARGETED_MUTANTS_KILLED"
    assert audit["mutants"] == audit["mutants_killed"] == 16
    assert audit["equivalent_controls"] == audit["equivalent_controls_passed"] == 4

