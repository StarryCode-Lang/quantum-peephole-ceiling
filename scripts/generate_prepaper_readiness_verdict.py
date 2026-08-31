"""Generate the final pre-paper readiness verdict from the current ledger.

This is a machine-checkable verdict, not paper prose.  It reports the final
592-item status counts, the evidence-chain anchors, and a go/no-go judgment
for entering paper writing, separated into engineering verification,
scientific-evidence scope, external/real-hardware gates, and release-authority
gates.  It changes no ledger status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    from scripts.verify_sbom import verify_sbom
except ModuleNotFoundError:  # Direct ``python scripts/...py`` execution.
    from verify_sbom import verify_sbom

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/review/metric_audit_ledger_2026-08-24.csv"
SUMMARY = ROOT / "docs/review/metric_audit_summary_2026-08-24.json"
REGISTRY = ROOT / "docs/review/metric_evidence_registry_2026-08-26.json"
BLOCKERS = ROOT / "release/prepaper_external_blockers.csv"
PYTEST_RECEIPT = ROOT / "release/pytest_junit.xml"
WORKSPACE_AUDIT = ROOT / "data/v10/prepaper/audit/workspace_coverage.json"
WORKSPACE_FILE_INVENTORY = (
    ROOT / "data/v10/prepaper/audit/workspace_file_inventory.csv"
)
WORKSPACE_DIRECTORY_INVENTORY = (
    ROOT / "data/v10/prepaper/audit/workspace_directory_inventory.csv"
)
ARCHIVE_AUDIT = ROOT / "release/prepaper_archive_restore_audit.json"
SBOM = ROOT / "release/sbom.cdx.json"
DEFAULT_OUTPUT = ROOT / "release/prepaper_readiness_verdict.json"
MINIMUM_PYTEST_TESTS = 552
REQUIRED_CORE_PASS_IDS = {
    "1.02", "1.09", "1.10", "1.12", "1.13", "1.14", "1.17",
    "2.01", "2.02", "2.03", "2.04", "2.05", "2.07", "2.08",
    "2.09", "2.10", "2.12", "2.13", "2.14", "2.16", "2.19",
    "2.21", "2.22", "2.24", "2.25",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pytest_receipt() -> dict:
    root = ET.parse(PYTEST_RECEIPT).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
    if not suites:
        raise RuntimeError("pytest JUnit receipt contains no test suite")
    values = {
        field: sum(int(suite.attrib.get(field, "0")) for suite in suites)
        for field in ("tests", "failures", "errors", "skipped")
    }
    if values["tests"] < MINIMUM_PYTEST_TESTS:
        raise RuntimeError(
            f"pytest receipt covers only {values['tests']} tests; "
            f"at least {MINIMUM_PYTEST_TESTS} are required"
        )
    if any(values[field] for field in ("failures", "errors", "skipped")):
        raise RuntimeError(f"pytest receipt is not zero-failure: {values}")
    values["sha256"] = sha256(PYTEST_RECEIPT)
    return values


def _workspace_receipt() -> dict:
    payload = json.loads(WORKSPACE_AUDIT.read_text(encoding="utf-8"))
    if payload.get("status") != "complete" or int(payload.get("files_byte_read", 0)) <= 0:
        raise RuntimeError("workspace coverage audit is not complete")
    expected = {
        "file_inventory_sha256": sha256(WORKSPACE_FILE_INVENTORY),
        "directory_inventory_sha256": sha256(WORKSPACE_DIRECTORY_INVENTORY),
    }
    for field, observed in expected.items():
        if payload.get(field) != observed:
            raise RuntimeError(f"workspace coverage receipt drift: {field}")
    return {
        "files_byte_read": int(payload["files_byte_read"]),
        "directories_enumerated": int(payload["directories_enumerated"]),
        "audit_sha256": sha256(WORKSPACE_AUDIT),
        **expected,
    }


def _archive_receipt() -> dict:
    payload = json.loads(ARCHIVE_AUDIT.read_text(encoding="utf-8"))
    restore = payload.get("restore_test", {})
    verifier = restore.get("verifier_receipt", {})
    if payload.get("status") != "PASS_LAYERED_ARCHIVE_RESTORE_TEST":
        raise RuntimeError("layered archive restore receipt is not PASS")
    if restore.get("verifier_exit_code") != 0 or verifier.get("status") != "verified":
        raise RuntimeError("restored isolated verifier did not pass")
    if verifier.get("metric_ledger_rows_verified") != 592:
        raise RuntimeError("restored verifier did not recheck all 592 metrics")
    return {
        "archive_members": int(payload["archive"]["archive_members"]),
        "archive_sha256": str(payload["archive"]["sha256"]),
        "receipt_sha256": sha256(ARCHIVE_AUDIT),
        "metric_ledger_rows_verified": 592,
    }


def _blocker_receipt(fail_ids: list[str], external_ids: list[str]) -> dict:
    blockers = pd.read_csv(BLOCKERS, keep_default_na=False, dtype=str)
    required_columns = {
        "metric_id", "status", "actor", "action", "required_input",
        "acceptance_evidence",
    }
    if not required_columns.issubset(blockers.columns):
        raise RuntimeError("external blocker table lacks required columns")
    if blockers[list(required_columns)].apply(lambda column: column.str.len().eq(0)).any().any():
        raise RuntimeError("external blocker table contains a blank required field")
    expected_ids = set(fail_ids) | set(external_ids)
    observed_ids = set(blockers["metric_id"])
    if len(blockers) != len(expected_ids) or observed_ids != expected_ids:
        raise RuntimeError("external blocker table does not exactly cover FAIL/EXTERNAL")
    expected_status = {
        **{metric_id: "FAIL" for metric_id in fail_ids},
        **{metric_id: "EXTERNAL" for metric_id in external_ids},
    }
    if any(expected_status[row.metric_id] != row.status for row in blockers.itertuples()):
        raise RuntimeError("external blocker status disagrees with the ledger")
    return {"rows": len(blockers), "sha256": sha256(BLOCKERS)}


def build(output: Path = DEFAULT_OUTPUT) -> dict:
    frame = pd.read_csv(LEDGER, keep_default_na=False, dtype=str)
    if len(frame) != 592 or frame["metric_id"].nunique() != 592:
        raise RuntimeError("ledger is not a unique 592-item inventory")
    counts = frame["status"].value_counts().to_dict()
    counts = {str(key): int(value) for key, value in counts.items()}
    for status in ("PASS", "PARTIAL", "FAIL", "NA", "EXTERNAL"):
        counts.setdefault(status, 0)
    if sum(counts.values()) != 592:
        raise RuntimeError("status counts do not sum to 592")

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    if summary.get("status_counts") != counts:
        raise RuntimeError("summary status counts drift from ledger")

    pass_ids = sorted(frame.loc[frame["status"] == "PASS", "metric_id"])
    fail_ids = sorted(frame.loc[frame["status"] == "FAIL", "metric_id"])
    external_ids = sorted(frame.loc[frame["status"] == "EXTERNAL", "metric_id"])

    missing_core = sorted(REQUIRED_CORE_PASS_IDS - set(pass_ids))
    if missing_core:
        raise RuntimeError(f"required core-claim metrics are not PASS: {missing_core}")
    pytest_receipt = _pytest_receipt()
    sbom_receipt = verify_sbom(SBOM)
    workspace_receipt = _workspace_receipt()
    archive_receipt = _archive_receipt()
    blocker_receipt = _blocker_receipt(fail_ids, external_ids)
    readiness_conditions = {
        "required_core_metrics_pass": not missing_core,
        "pytest_zero_failure": (
            pytest_receipt["failures"] == 0 and pytest_receipt["errors"] == 0
        ),
        "sbom_verified": sbom_receipt["status"] == "verified",
        "workspace_scan_complete": workspace_receipt["files_byte_read"] > 0,
        "layered_archive_restorable": archive_receipt["metric_ledger_rows_verified"] == 592,
        "all_fail_external_items_have_blockers": (
            blocker_receipt["rows"] == counts["FAIL"] + counts["EXTERNAL"]
        ),
    }
    ready = all(readiness_conditions.values())

    verdict = {
        "schema_version": "1.0.0",
        "status": "PRE_PAPER_READINESS_VERDICT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "ledger_sha256": sha256(LEDGER),
        "summary_sha256": sha256(SUMMARY),
        "registry_sha256": sha256(REGISTRY),
        "blockers_sha256": sha256(BLOCKERS),
        "status_counts": counts,
        "item_specific_pass_coverage": {
            "numerator": counts["PASS"], "denominator": 592,
        },
        "required_core_claim_pass_ids": sorted(REQUIRED_CORE_PASS_IDS),
        "readiness_conditions": readiness_conditions,
        "verification_inputs": {
            "pytest": pytest_receipt,
            "sbom": sbom_receipt,
            "workspace": workspace_receipt,
            "archive_restore": archive_receipt,
            "external_blockers": blocker_receipt,
        },
        "gates": {
            "engineering_verification": {
                "state": "COMPLETE",
                "evidence": [
                    f"full pytest {pytest_receipt['tests']} passed / 0 failed / 0 skipped",
                    f"CycloneDX SBOM verified ({sbom_receipt['components']} components)",
                    "workspace coverage scan: "
                    f"{workspace_receipt['files_byte_read']:,} files byte-read",
                    "layered archive restore test PASS "
                    f"({archive_receipt['archive_members']:,} members, isolated Python)",
                    f"all {blocker_receipt['rows']} FAIL/EXTERNAL metrics have explicit blockers",
                ],
            },
            "scientific_evidence_scope": {
                "state": "BOUNDED",
                "boundary": [
                    "fixed-panel conclusions are descriptive only",
                    "15-family results are supportive family-level inference only",
                    "unseen-family generalization remains BLOCKED",
                    "structural equivalence is not quantum semantic fidelity",
                    "over-budget verification fails closed",
                    "timeout/error/invalid remain in the ITT denominator",
                ],
            },
            "external_real_hardware_gates": {
                "state": "OPEN",
                "metric_ids": [mid for mid in fail_ids if mid.startswith("14.")]
                + ["13.15"],
                "required": "user-provided QPU account, budget, target device, authorization",
            },
            "release_authority_gates": {
                "state": "OPEN",
                "metric_ids": ["15.09", "15.10", "15.40"],
                "required": "user license decision, Zenodo publication authorization, release commit authorization",
            },
        },
        "remaining_non_pass": {
            "FAIL": fail_ids,
            "EXTERNAL": external_ids,
            "PARTIAL_count": counts["PARTIAL"],
            "NA_count": counts["NA"],
        },
        "verdict": "READY_FOR_PAPER_WRITING_WITH_BOUNDARIES" if ready else "NOT_READY",
        "verdict_rationale": (
            "All core-claim metrics carry item-specific, hash-pinned, machine-checkable "
            "satisfaction evidence and every key verifier passes; the release chain is "
            "independently restorable. Remaining FAIL/EXTERNAL items are genuine external, "
            "real-hardware, user-authorization, or new-frozen-protocol-experiment gaps and "
            "are honestly retained in release/prepaper_external_blockers.csv rather than "
            "fabricated to PASS. Paper writing may proceed on the bounded descriptive and "
            "supportive claims; it must not claim unseen-family universality, real-QPU "
            "results, or algorithm-independent ceilings."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    verdict = build(args.output.resolve())
    print(json.dumps({
        "status": verdict["status"],
        "status_counts": verdict["status_counts"],
        "verdict": verdict["verdict"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
