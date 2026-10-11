"""Regression tests for the v15 landscape-integration package."""

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data" / "v15" / "e45_landscape_integration"


def test_v15_integration_verifier_passes():
    completed = subprocess.run(
        [sys.executable, "scripts/verify_v15_landscape_integration.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    verdict = json.loads(completed.stdout.strip().splitlines()[-1])
    assert verdict["status"] == "PASS"
    assert verdict["source_count"] == 128
    assert verdict["regeneration_matches"] is True


def test_v15_integration_closes_the_v14_classification_gap():
    receipt = json.loads((PACKAGE / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "CLASSIFICATION_COMPLETE"
    assert receipt["source_count"] == 128
    assert receipt["classified_count"] == 128
    assert receipt["unclassified_count"] == 0
    assert receipt["escape_count"] == 63
    assert receipt["local_optimum_count"] == 65
    assert receipt["certificate_tiers"] == {
        "COMPACT_COMPLETE_ENUMERATED": 93,
        "COMPACT_COMPLETE_DERIVED": 1,
        "CLASSIFICATION_EXACT_EXTRAS_BOUNDED": 34,
    }
    assert receipt["exact_best_cost_count"] == 94
    assert receipt["bounded_best_cost_count"] == 34
    assert receipt["witness_replay_failure_count"] == 0


def test_v15_integration_inputs_are_hash_bound_to_frozen_v14_packages():
    import hashlib

    receipt = json.loads((PACKAGE / "receipt.json").read_text(encoding="utf-8"))
    inputs = receipt["inputs"]
    compact = ROOT / "data/v14/e45_full_development/certificates.jsonl"
    idastar = ROOT / "data/v14/e45_idastar_escape/certificates.jsonl"
    assert inputs["compact_certificates_sha256"] == hashlib.sha256(compact.read_bytes()).hexdigest()
    assert inputs["idastar_certificates_sha256"] == hashlib.sha256(idastar.read_bytes()).hexdigest()
