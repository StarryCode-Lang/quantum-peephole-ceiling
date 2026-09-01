from analysis.e31_runtime_outcome_audit import build_audit


def test_e31_budget_exhausted_valid_rate_is_explicit():
    audit = build_audit()

    assert audit["status"] == "PASS_E31_BUDGET_EXHAUSTED_VALID_RATE_MEASURED"
    assert audit["status_counts"] == {"success": 20314, "timeout": 7838}
    assert audit["budget_exhausted_with_valid_retained_output"] == 0
    assert audit["budget_exhausted_but_valid_rate"] == 0.0
