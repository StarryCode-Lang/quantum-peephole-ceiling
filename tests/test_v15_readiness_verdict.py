"""Regression tests for the receipt-bound v15 readiness verdict."""

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v15_verdict_is_fail_closed_and_verifier_passes():
    completed = subprocess.run(
        [sys.executable, "scripts/verify_v15_readiness_verdict.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    receipt = json.loads(completed.stdout.strip().splitlines()[-1])
    assert receipt["status"] == "PASS"


def test_v15_verdict_keeps_v14_verdict_hash_bound_and_classification_complete():
    verdict = json.loads(
        (ROOT / "release/v15_readiness_verdict.json").read_text(encoding="utf-8")
    )
    assert verdict["verdict"] == "NOT_READY_FOR_PAPER"
    assert verdict["scientific_gates"]["S6_E45_classification"] == "COMPLETE_128_OF_128"
    assert verdict["scientific_gates"]["S6_landscape_quantities"] == (
        "EXACT_FOR_94_OF_128_WITNESS_BOUNDED_FOR_34"
    )
    landscape = verdict["blocking_evidence"]["landscape_integration"]
    assert landscape["escape_count"] == 63
    assert landscape["local_optimum_count"] == 65
    assert landscape["certificate_tiers"]["CLASSIFICATION_EXACT_EXTRAS_BOUNDED"] == 34
    assert verdict["blocking_evidence"]["window_landscape"]["status"] in {
        "PENDING",
        "PANEL_COMPLETE",
        "PANEL_COMPLETE_WITH_RESOURCE_BOUNDARY",
    }
