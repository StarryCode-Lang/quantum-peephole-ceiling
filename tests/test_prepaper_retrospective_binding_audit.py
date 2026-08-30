"""Regression tests for the retrospective evidence-binding audit."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "release/prepaper_retrospective_binding_audit.json"


def _audit() -> dict:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_retrospective_binding_status_and_metrics():
    audit = _audit()
    assert audit["status"] == "PASS_RETROSPECTIVE_EVIDENCE_BINDING"
    assert set(audit["metric_dispositions"]) == {
        "13.14", "16.23", "3.12", "16.16", "16.18", "13.13",
    }
    assert audit["metric_dispositions"]["3.12"].startswith("PASS:")
    assert audit["metric_dispositions"]["13.14"].startswith("PARTIAL:")
    assert audit["metric_dispositions"]["16.23"].startswith("PARTIAL:")
    assert audit["metric_dispositions"]["16.16"].startswith("PARTIAL:")
    assert audit["metric_dispositions"]["16.18"].startswith("PARTIAL:")
    assert audit["metric_dispositions"]["13.13"].startswith("PARTIAL:")


def test_retrospective_binding_hashes_match_workspace():
    import hashlib

    audit = _audit()
    for relative, record in audit["evidence_bindings"].items():
        path = ROOT / relative
        assert path.is_file(), f"bound evidence missing: {relative}"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == record["sha256"], f"bound evidence drifted: {relative}"
        assert record["metrics"], f"binding has no metrics: {relative}"


def test_retrospective_binding_claim_boundary_is_bounded():
    audit = _audit()
    boundary = audit["claim_boundary"]
    assert "does not extend any claim" in boundary
    assert "bounded PARTIAL" in boundary
