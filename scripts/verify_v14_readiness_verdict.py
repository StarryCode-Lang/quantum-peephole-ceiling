"""Fail-closed verifier for the derived v14 screening readiness verdict."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V14 = ROOT / "data" / "v14" / "e45_development_grid"
FULL = ROOT / "data" / "v14" / "e45_full_development"
VERDICT = ROOT / "release" / "v14_readiness_verdict.json"
V13_MANIFEST = ROOT / "data" / "v13" / "e45_development_grid" / "normalization_manifest.csv"
V13_VERDICT = ROOT / "release" / "v13_readiness_verdict.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_e45_verifier() -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_e45_development_grid.py"), "--output-root", str(V14)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return {"status": "FAIL", "reason": (completed.stderr or completed.stdout)[-500:]}
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    try:
        return json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError):
        return {"status": "FAIL", "reason": "invalid_e45_verifier_receipt"}


def run_exact_verifier() -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_e45_exact_development.py"), "--output-root", str(FULL)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return {"status": "FAIL", "reason": (completed.stderr or completed.stdout)[-500:]}
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    try:
        return json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError):
        return {"status": "FAIL", "reason": "invalid_exact_verifier_receipt"}


def main() -> int:
    required = [
        VERDICT,
        V13_VERDICT,
        V13_MANIFEST,
        V14 / "protocol.json",
        V14 / "normalization_manifest.csv",
        V14 / "grid_results.csv",
        V14 / "config_summaries.json",
        V14 / "selection.json",
        V14 / "receipt.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        print(json.dumps({"status": "FAIL", "missing": missing}, sort_keys=True))
        return 1

    verdict = read_json(VERDICT)
    receipt = read_json(V14 / "receipt.json")
    selection = read_json(V14 / "selection.json")
    summaries = read_json(V14 / "config_summaries.json")
    with (V14 / "normalization_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    with V13_MANIFEST.open(newline="", encoding="utf-8") as handle:
        v13_manifest = list(csv.DictReader(handle))
    with (V14 / "grid_results.csv").open(newline="", encoding="utf-8") as handle:
        results = list(csv.DictReader(handle))

    checks: dict[str, bool] = {
        "required_files": not missing,
        "schema_and_verdict": verdict.get("schema_version") == "v14-readiness-verdict-v1" and verdict.get("verdict") == "NOT_READY_FOR_PAPER",
        "receipt_status": receipt.get("status") == "SCREENING_COMPLETE_SELECTION_PENDING_FULL_DEVELOPMENT",
        "experiment_id": receipt.get("experiment_id") == "E45_CERTIFIED_ESCAPE_DEVELOPMENT_V14",
        "panel_cardinality": len(manifest) == 128 and len(results) == 13_824 and receipt.get("source_count") == 128 and receipt.get("result_rows") == 13_824,
        "source_scope_matches_v13": [row.get("source_sha256") for row in manifest] == [row.get("source_sha256") for row in v13_manifest],
        "configuration_and_arm_cardinality": receipt.get("configuration_count") == 18 and receipt.get("arm_count") == 6 and len([row for row in summaries if row.get("arm") == "certificate_guided_escape"]) == 18,
        "guided_resource_gate": all(float(row.get("resource_or_error_rate", "1")) <= 0.05 and int(row.get("semantic_failure_count", "1")) == 0 for row in summaries if row.get("arm") == "certificate_guided_escape"),
        "guided_arm_has_no_exact_claim": not any(row.get("arm") == "certificate_guided_escape" and row.get("status", "").startswith("EXACT") for row in results),
        "selection_boundary": selection.get("eligible_config_count") == 18 and selection.get("selection_is_frozen_for_e48") is False and selection.get("status") == "SCREENING_COMPLETE_SELECTION_PENDING_FULL_DEVELOPMENT",
        "e45_verifier": run_e45_verifier().get("status") == "PASS",
        "full_development_verifier": run_exact_verifier().get("status") == "PASS",
        "full_development_boundary": verdict.get("scientific_gates", {}).get("S5_E45_full_development") == "COMPLETE_WITH_RESOURCE_BOUNDARY" and verdict.get("blocking_evidence", {}).get("full_development", {}).get("resource_bounded_rows") == 35 and verdict.get("blocking_evidence", {}).get("full_development", {}).get("exact_finite_horizon_certificates") == 93,
        "v13_verdict_unchanged": verdict.get("engineering_verification", {}).get("v13_readiness_verdict_unchanged_sha256") == sha256(V13_VERDICT),
    }
    artifact_paths = {
        "protocol": "protocol.json",
        "normalization_manifest": "normalization_manifest.csv",
        "grid_results": "grid_results.csv",
        "config_summaries": "config_summaries.json",
        "selection": "selection.json",
    }
    checks["receipt_artifact_hashes"] = all(
        receipt.get(f"{key}_sha256") == sha256(V14 / filename)
        for key, filename in artifact_paths.items()
    )
    full_evidence = verdict.get("blocking_evidence", {}).get("full_development", {})
    full_artifacts = full_evidence.get("artifacts", {})
    checks["full_development_evidence"] = (
        full_evidence.get("receipt_sha256") == sha256(FULL / "receipt.json")
        and len(full_artifacts) == 6
        and all(
            item.get("path")
            and item.get("sha256") == sha256(ROOT / item["path"])
            and item.get("selector") == f"$.{key}_sha256"
            for key, item in full_artifacts.items()
        )
    )
    recorded = verdict.get("derivation", {}).get("evidence", [])
    checks["evidence_contract"] = (
        verdict.get("derivation", {}).get("metric_id") == "E45.v14.S5.screening_resource_gate"
        and len(recorded) == 5
        and all(item.get("path") and item.get("sha256") and item.get("selector") and item.get("predicate") for item in recorded)
        and all(sha256(ROOT / item["path"]) == item["sha256"] for item in recorded)
    )
    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, "checks": checks}, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
