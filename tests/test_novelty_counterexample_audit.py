from analysis.novelty_counterexample_audit import build


def test_identical_counterexample_audit_is_bounded_not_absence_proof(tmp_path):
    audit = build(tmp_path / "audit.json")
    assert audit["status"] == "PARTIAL_TARGETED_NO_IDENTICAL_COUNTEREXAMPLE_FOUND"
    assert all(audit["checks"].values())
    assert audit["metric_dispositions"]["3.13"].startswith("PARTIAL:")
    assert "not proof that none exists" in audit["claim_boundary"]

