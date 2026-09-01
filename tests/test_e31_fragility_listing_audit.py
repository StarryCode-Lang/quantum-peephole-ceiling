"""Tests for the sealed E31 listing-extreme and fragility audit."""

from analysis.e31_fragility_listing_audit import build_audit


def test_fragility_listing_audit_is_complete_and_bounded(tmp_path):
    audit = build_audit(tmp_path)
    assert audit["status"] == "PASS_BOUNDED_E31_FRAGILITY_AND_LISTING_AUDIT"
    assert audit["listing_extremes"]["cells"] == 9384
    assert audit["listing_extremes"]["families"] == 15
    assert audit["single_input_influence"]["inputs"] == 391
    assert audit["single_input_influence"]["conclusions"] == 5
    assert audit["single_input_influence"]["sign_flip_count"] == 0
    assert audit["equal_budget_sensitivity"]["budgets_seconds"] == [1, 10, 30, 120]
    assert audit["equal_budget_sensitivity"]["sign_reversal_count"] == 0
    assert audit["timeout_deletion_sensitivity"]["timeout_rows"] == 7838
    assert audit["timeout_deletion_sensitivity"]["any_sign_flip"] is False
    assert audit["metric_dispositions"]["17.07"].startswith("PARTIAL:")
