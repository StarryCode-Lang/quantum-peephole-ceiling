"""Tests for bounded rewrite-order conflict and non-confluence auditing."""

from scripts.audit_rewrite_order_confluence import build_audit


def test_rewrite_order_audit_completes_without_semantic_drift():
    audit = build_audit(cases=4)
    assert audit["status"] == "PASS_AUDIT_COMPLETE"
    assert audit["semantic_failure_count"] == 0
    assert audit["convergence_failure_count"] == 0
    assert audit["cases"] == 4
    assert all(
        output["converged_at_structural_fixpoint"]
        and not output["structural_cycle_detected"]
        for record in audit["records"]
        for output in record["outputs"].values()
    )
