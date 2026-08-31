"""Regression tests for the pre-paper readiness verdict."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERDICT_PATH = ROOT / "release/prepaper_readiness_verdict.json"


def _verdict() -> dict:
    return json.loads(VERDICT_PATH.read_text(encoding="utf-8"))


def test_verdict_counts_sum_to_592():
    verdict = _verdict()
    counts = verdict["status_counts"]
    assert sum(counts.values()) == 592
    assert set(counts) == {"PASS", "PARTIAL", "FAIL", "NA", "EXTERNAL"}


def test_verdict_is_ready_with_boundaries():
    verdict = _verdict()
    assert verdict["verdict"] == "READY_FOR_PAPER_WRITING_WITH_BOUNDARIES"
    assert verdict["gates"]["engineering_verification"]["state"] == "COMPLETE"
    assert verdict["gates"]["scientific_evidence_scope"]["state"] == "BOUNDED"
    assert verdict["gates"]["external_real_hardware_gates"]["state"] == "OPEN"
    assert verdict["gates"]["release_authority_gates"]["state"] == "OPEN"
    assert all(verdict["readiness_conditions"].values())


def test_verdict_is_bound_to_current_zero_failure_pytest_receipt():
    verdict = _verdict()
    suite = ET.parse(ROOT / "release/pytest_junit.xml").getroot().find("testsuite")
    assert suite is not None
    receipt = verdict["verification_inputs"]["pytest"]
    assert receipt["tests"] == int(suite.attrib["tests"])
    assert receipt["tests"] >= 552
    assert receipt["failures"] == int(suite.attrib["failures"]) == 0
    assert receipt["errors"] == int(suite.attrib["errors"]) == 0
    assert receipt["skipped"] == int(suite.attrib["skipped"]) == 0


def test_verdict_requires_fixed_core_claims_and_complete_blocker_coverage():
    verdict = _verdict()
    assert len(verdict["required_core_claim_pass_ids"]) == 25
    blockers = verdict["verification_inputs"]["external_blockers"]
    counts = verdict["status_counts"]
    assert blockers["rows"] == counts["FAIL"] + counts["EXTERNAL"] == 40


def test_verdict_retains_all_non_pass_items():
    verdict = _verdict()
    remaining = verdict["remaining_non_pass"]
    assert remaining["FAIL"], "FAIL items must be honestly retained"
    assert remaining["EXTERNAL"], "EXTERNAL items must be honestly retained"
    assert remaining["PARTIAL_count"] > 0
    assert remaining["NA_count"] > 0


def test_live_repository_has_no_github_actions_workflows():
    workflow_root = ROOT / ".github/workflows"
    live_workflows = [] if not workflow_root.exists() else [
        path for path in workflow_root.rglob("*") if path.is_file()
    ]
    assert live_workflows == []
    generator = (ROOT / "scripts/generate_prepaper_release_manifest.py").read_text(
        encoding="utf-8"
    )
    assert '".github/workflows/tests.yml"' not in generator
