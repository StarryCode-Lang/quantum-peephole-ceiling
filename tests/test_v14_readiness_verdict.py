"""Regression tests for the receipt-bound v14 screening verdict."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v14_verdict_is_fail_closed_and_verifier_passes():
    completed = subprocess.run(
        [sys.executable, "scripts/verify_v14_readiness_verdict.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    receipt = json.loads(completed.stdout.strip().splitlines()[-1])
    assert receipt["status"] == "PASS"
    assert all(receipt["checks"].values())


def test_v14_verdict_keeps_v13_verdict_hash_bound():
    verdict = json.loads((ROOT / "release/v14_readiness_verdict.json").read_text(encoding="utf-8"))
    v13 = ROOT / "release/v13_readiness_verdict.json"
    assert verdict["verdict"] == "NOT_READY_FOR_PAPER"
    assert verdict["scientific_gates"]["S5_E45_v14_screening"] == "PASS_RESOURCE_GATE_WITH_BOUNDARIES"
    assert verdict["scientific_gates"]["S5_E45_full_development"] == "COMPLETE_WITH_RESOURCE_BOUNDARY"
    assert verdict["blocking_evidence"]["full_development"]["exact_finite_horizon_certificates"] == 93
    assert verdict["blocking_evidence"]["full_development"]["resource_bounded_rows"] == 35
    assert verdict["engineering_verification"]["v13_readiness_verdict_unchanged_sha256"] == hashlib.sha256(v13.read_bytes()).hexdigest()
