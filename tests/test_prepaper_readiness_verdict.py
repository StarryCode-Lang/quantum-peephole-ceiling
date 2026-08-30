"""Regression tests for the pre-paper readiness verdict."""

import json
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


def test_verdict_retains_all_non_pass_items():
    verdict = _verdict()
    remaining = verdict["remaining_non_pass"]
    assert remaining["FAIL"], "FAIL items must be honestly retained"
    assert remaining["EXTERNAL"], "EXTERNAL items must be honestly retained"
    assert remaining["PARTIAL_count"] > 0
    assert remaining["NA_count"] > 0
