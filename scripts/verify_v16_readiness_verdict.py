"""Fail-closed verifier for the derived v16 readiness verdict."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERDICT = ROOT / "release" / "v16_readiness_verdict.json"
V14_VERDICT = ROOT / "release" / "v14_readiness_verdict.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    checks: dict[str, object] = {}
    status = "PASS"
    try:
        verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
        if verdict["verdict"] != "NOT_READY_FOR_PAPER":
            raise RuntimeError("verdict_upgraded_without_gate")
        if verdict["engineering_verification"]["v14_readiness_verdict_unchanged_sha256"] != sha256(V14_VERDICT):
            raise RuntimeError("v14_verdict_hash_drift")

        integration = verdict["blocking_evidence"]["landscape_integration"]
        receipt = json.loads(
            (ROOT / "data/v16/e45_landscape_integration/receipt.json").read_text(encoding="utf-8")
        )
        if integration["receipt_sha256"] != sha256(ROOT / "data/v16/e45_landscape_integration/receipt.json"):
            raise RuntimeError("integration_receipt_hash_drift")
        if receipt["classified_count"] != 127 or receipt["unclassified_count"] != 1:
            raise RuntimeError("classification_not_complete_with_boundary")
        if receipt["certificate_tiers"] != {
            "COMPACT_COMPLETE_ENUMERATED": 93,
            "COMPACT_COMPLETE_DERIVED": 0,
            "CLASSIFICATION_EXACT_EXTRAS_BOUNDED": 34,
            "CLASSIFICATION_RESOURCE_BOUNDED": 1,
        }:
            raise RuntimeError("tier_partition_drift")
        if receipt["witness_replay_failure_count"] != 0:
            raise RuntimeError("witness_replay_failure")

        window = verdict["blocking_evidence"]["window_landscape"]
        if window.get("status") not in {"PENDING", "PANEL_COMPLETE", "PANEL_COMPLETE_WITH_RESOURCE_BOUNDARY"}:
            raise RuntimeError("window_status_invalid")
        if window.get("status") != "PENDING":
            window_receipt = json.loads(
                (ROOT / "data/v16/e46_window_landscape/receipt.json").read_text(encoding="utf-8")
            )
            if window["receipt_sha256"] != sha256(ROOT / "data/v16/e46_window_landscape/receipt.json"):
                raise RuntimeError("window_receipt_hash_drift")
            if window_receipt["source_count"] != 128:
                raise RuntimeError("window_panel_scope")
        checks["gates"] = verdict["scientific_gates"]
    except (RuntimeError, KeyError, json.JSONDecodeError) as exc:
        status = "FAIL"
        checks["failure_reason"] = str(exc)

    print(json.dumps({"status": status, **checks}, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
