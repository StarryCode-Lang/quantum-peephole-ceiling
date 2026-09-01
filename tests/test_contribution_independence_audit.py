from analysis.contribution_independence_audit import build


def test_contribution_gate_is_source_bound_and_scope_limited(tmp_path):
    audit = build(tmp_path / "audit.json")
    assert audit["status"] == "PASS_STANDALONE_EMPIRICAL_CONTRIBUTION_GATE"
    assert all(audit["criteria"].values())
    assert audit["observed_scope"]["formal_factorial_rows"] == 28152
    assert audit["observed_scope"]["heldout_outer_generator_families"] == 16
    assert audit["observed_scope"]["formal_external_methods"] == ["quartz", "quasar"]
    assert audit["metric_dispositions"]["3.27"].startswith("PASS:")
    assert "does not establish priority" in audit["claim_boundary"]
