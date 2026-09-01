"""Independently verify the v12 ledger, hash closure, and E38-E41 receipts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V12 = ROOT / "data" / "v12"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(reason: str) -> None:
    raise SystemExit(f"V12_VERIFY_FAIL:{reason}")


def run_verifier(script: str) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-I", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        fail(f"{script}:exit_{completed.returncode}:{(completed.stderr or completed.stdout)[-500:]}")
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        fail(f"{script}:no_receipt")
    try:
        result = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        fail(f"{script}:invalid_receipt:{exc}")
    if result.get("status") != "verified":
        fail(f"{script}:not_verified")
    return result


def main() -> int:
    ledger_path = V12 / "v12_requirement_to_evidence_ledger.json"
    verdict_path = ROOT / "release" / "prepaper_v12_readiness_verdict.json"
    sbom_path = V12 / "v12_sbom.json"
    environment_path = V12 / "v12_source_data_environment_manifest.json"
    for path in (ledger_path, verdict_path, sbom_path, environment_path):
        if not path.is_file():
            fail(f"missing_package_file:{path}")
    ledger = read_json(ledger_path)
    verdict = read_json(verdict_path)
    sbom = read_json(sbom_path)
    environment = read_json(environment_path)
    rows = ledger.get("rows")
    if not isinstance(rows, list) or len(rows) != 13:
        fail("ledger_row_count")
    if len({row.get("id") for row in rows}) != len(rows):
        fail("ledger_id_uniqueness")
    checked_evidence = 0
    for row in rows:
        if not row.get("status") or not row.get("requirement") or not row.get("boundary"):
            fail(f"ledger_required_fields:{row.get('id')}")
        for item in row.get("evidence", []):
            path = ROOT / item["file"]
            if not path.is_file() or sha256(path) != item.get("sha256") or path.stat().st_size != item.get("bytes"):
                fail(f"evidence_hash:{item.get('file')}")
            if not item.get("selector"):
                fail(f"evidence_selector:{item.get('file')}")
            checked_evidence += 1
    if verdict.get("verdict") != "NOT_READY_FOR_PAPER":
        fail("verdict_drift")
    if verdict.get("ledger", {}).get("sha256") != sha256(ledger_path):
        fail("verdict_ledger_hash")
    if verdict.get("sbom", {}).get("sha256") != sha256(sbom_path):
        fail("verdict_sbom_hash")
    if verdict.get("source_data_environment_manifest", {}).get("sha256") != sha256(environment_path):
        fail("verdict_environment_hash")
    if sbom.get("bomFormat") != "CycloneDX" or not sbom.get("components"):
        fail("sbom_contract")
    if environment.get("source_commit_at_manifest_build") in {None, ""}:
        fail("environment_source_commit")
    e40 = read_json(V12 / "e40_prospective_rewrite_exposure" / "primary_estimand.json")
    e41 = read_json(V12 / "e41_rewrite_exposure_scale" / "scalability_report.json")
    if e40.get("status") != "NOT_ESTIMABLE_EXTERNAL_BOUNDARY" or e40.get("opportunity_positive_family_count") != 0:
        fail("e40_estimand_boundary")
    if e41.get("unmarked_semantic_failure_count") != 0 or e41.get("resource_or_error_cells") != 4:
        fail("e41_scale_boundary")
    verifier_results = {
        "e38": run_verifier("scripts/verify_e38_rewrite_exposure.py"),
        "e39": run_verifier("scripts/verify_e39_development_grid.py"),
        "e40": run_verifier("scripts/verify_e40_prospective_rewrite_exposure.py"),
        "e41": run_verifier("scripts/verify_e41_rewrite_exposure_scale.py"),
    }
    result = {
        "status": "verified",
        "ledger_sha256": sha256(ledger_path),
        "evidence_entries_verified": checked_evidence,
        "verdict": verdict["verdict"],
        "verifier_results": verifier_results,
        "claim_boundary": verdict["claim_boundary"],
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
