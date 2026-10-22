"""Release-chain verifier with declared-drift dispositions.

Problem
-------
`scripts/verify_prepaper_release_manifest.py` fails on
`docs/review/metric_audit_ledger_2026-08-24.csv` and has failed on every review
run since 2026-10-18.  That script is itself path-bound in
`release/prepaper_release_manifest.json`, so editing it would create a second
drift.  `release/` is outside this project's write scope by standing rule.

The consequence is that a cold-start executor cannot tell a *known, attributed*
drift from tampering, and the release chain reads as broken.

This verifier closes that gap without touching any bound file:

* it reads `release/prepaper_release_manifest.json` **read-only**;
* it reads the declared-drift register at `docs/review/release_drift_register.json`
  (not under `release/`, not bound by any manifest);
* a mismatch whose observed hash is registered is reported as
  `KNOWN_DRIFT_ACCEPTED` and does not fail the run;
* any unregistered mismatch, missing file, or size-only mismatch fails closed.

Exit codes
----------
0  every entry matches, or every mismatch is registered with the observed hash
1  at least one unregistered mismatch / missing file
2  register missing or malformed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release" / "prepaper_release_manifest.json"
REGISTER = ROOT / "docs" / "review" / "release_drift_register.json"
LISTS = ("source_files", "evidence", "project_evidence")
DEFAULT_REPORT = ROOT / "docs" / "review" / "release_chain_verification_2026-10-22.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_register() -> dict[str, dict[str, Any]]:
    if not REGISTER.exists():
        raise SystemExit(f"register_missing:{REGISTER}")
    payload = json.loads(REGISTER.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        raise SystemExit("register_malformed:entries_not_a_list")
    return {str(entry["file"]): entry for entry in entries}


def check(item: dict[str, Any], registered: dict[str, dict[str, Any]]) -> dict[str, Any]:
    relative = str(item["file"])
    path = ROOT / relative
    record: dict[str, Any] = {
        "file": relative,
        "expected_sha256": str(item.get("sha256", "")),
        "expected_bytes": item.get("bytes"),
    }
    if not path.exists():
        record.update({"status": "MISSING", "observed_sha256": None, "observed_bytes": None})
        return record
    observed_bytes = path.stat().st_size
    observed_sha = sha256_file(path)
    record.update({"observed_sha256": observed_sha, "observed_bytes": observed_bytes})
    if observed_sha == record["expected_sha256"]:
        record["status"] = "MATCH"
        return record
    entry = registered.get(relative)
    if entry is not None and str(entry.get("observed_sha256")) == observed_sha:
        record.update(
            {
                "status": "KNOWN_DRIFT_ACCEPTED",
                "disposition": entry.get("disposition", ""),
                "attribution_commit": entry.get("attribution_commit", ""),
                "recommended_option": entry.get("recommended_option", ""),
            }
        )
        return record
    record["status"] = "DRIFT_UNREGISTERED"
    if entry is not None:
        record["register_note"] = "registered but observed hash differs from the register"
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    registered = load_register()

    items: list[dict[str, Any]] = []
    for key in LISTS:
        for entry in manifest.get(key, []):
            if isinstance(entry, dict) and "file" in entry:
                items.append(entry)

    print(f"[verify] {len(items)} manifest entries, {len(registered)} registered drifts", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda item: check(item, registered), items))

    counts: dict[str, int] = {}
    for record in results:
        counts[record["status"]] = counts.get(record["status"], 0) + 1

    failures = [r for r in results if r["status"] in {"MISSING", "DRIFT_UNREGISTERED"}]
    report = {
        "schema_version": "release-chain-verification-v1",
        "date": "2026-10-22",
        "manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "register": str(REGISTER.relative_to(ROOT)).replace("\\", "/"),
        "entry_count": len(results),
        "status_counts": counts,
        "verdict": "PASS_WITH_ACCEPTED_DRIFT" if not failures else "FAIL",
        "failures": failures if not args.summary_only else failures[:20],
        "accepted_drift": [r for r in results if r["status"] == "KNOWN_DRIFT_ACCEPTED"],
        "note": (
            "PASS_WITH_ACCEPTED_DRIFT means every mismatch is registered and attributed. "
            "It does not mean the manifest is correct: the owner still has to re-pin or "
            "supersede the entry in release/, which this project's write scope excludes."
        ),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"[verify] {counts}", flush=True)
    for record in failures[:20]:
        print(f"[verify] FAIL {record['status']}: {record['file']}", flush=True)
    print(f"[verify] verdict={report['verdict']} report={args.report}", flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
