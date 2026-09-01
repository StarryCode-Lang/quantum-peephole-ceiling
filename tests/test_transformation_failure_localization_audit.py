"""Tests for stage-addressable Phase-2b semantic failure localization."""

from analysis.transformation_failure_localization_audit import build_audit


def test_all_transformation_stage_sentinels_localize_the_first_failure():
    audit = build_audit()
    assert audit["status"] == "PASS_STAGE_ADDRESSABLE_FAILURE_LOCALIZATION_SENTINELS"
    assert audit["correct_stage_checks"] == 5
    assert audit["fault_sentinels_localized"] == 5
    assert all(record["action_counters"] for record in audit["records"])
    assert audit["metric_dispositions"]["7.22"].startswith("PARTIAL:")
