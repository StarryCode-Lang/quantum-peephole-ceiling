"""Fail-closed verifier for the v15 landscape-integration package.

The verifier independently re-derives the integration from the frozen v14
packages into a temporary directory, compares every artifact byte-for-byte
with the stored package, re-checks the receipt hash chain, and re-replays
every witness.  Any mismatch fails the verdict.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data" / "v15" / "e45_landscape_integration"
COMPACT_ROOT = ROOT / "data" / "v14" / "e45_full_development"
IDASTAR_ROOT = ROOT / "data" / "v14" / "e45_idastar_escape"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "receipt.json"
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=PACKAGE)
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()
    package = args.output_root.resolve()

    checks: dict[str, Any] = {}
    status = "PASS"
    try:
        receipt = json.loads((package / "receipt.json").read_text(encoding="utf-8"))
        for field in ("protocol_sha256", "classification_complete_sha256", "derivations_sha256"):
            name = field.removesuffix("_sha256") + ".json" if field.startswith("protocol") else field.removesuffix("_sha256") + (".csv" if "classification" in field else ".jsonl")
            if sha256(package / name) != receipt[field]:
                raise RuntimeError(f"receipt_hash_mismatch:{name}")

        stored = artifact_hashes(package)
        temporary = Path(tempfile.mkdtemp(prefix="v15_integration_verify_"))
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_v15_landscape_integration.py"),
                    "--output-root",
                    str(temporary),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"regeneration_failed:{(completed.stderr or completed.stdout)[-500:]}")
            regenerated = artifact_hashes(temporary)
            if set(stored) != set(regenerated):
                raise RuntimeError(
                    f"artifact_set_mismatch:stored_only={sorted(set(stored) - set(regenerated))[:3]}"
                )
            differing = sorted(name for name in stored if stored[name] != regenerated[name])
            if differing:
                raise RuntimeError(f"artifact_byte_mismatch:{differing[:3]}")
        finally:
            if not args.keep_temp:
                shutil.rmtree(temporary, ignore_errors=True)
        checks["regeneration_matches"] = True

        with (package / "classification_complete.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        tiers = {row["certificate_tier"] for row in rows}
        checks["source_count"] = len(rows)
        checks["certificate_tiers"] = sorted(tiers)
        if len(rows) != receipt["source_count"] or receipt["unclassified_count"] != 0:
            raise RuntimeError("receipt_row_count_mismatch")
        if receipt["witness_replay_failure_count"] != 0:
            raise RuntimeError("stored_receipt_records_replay_failure")
        compact_by_id = {
            json.loads(line)["source_id"]: json.loads(line)["certificate"]
            for line in (COMPACT_ROOT / "certificates.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        idastar_by_id = {
            json.loads(line)["source_id"]: json.loads(line)["certificate"]
            for line in (IDASTAR_ROOT / "certificates.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        for row in rows:
            compact_status = compact_by_id[row["source_id"]]["status"]
            idastar_status = idastar_by_id[row["source_id"]]["status"]
            if row["compact_status"] != compact_status or row["idastar_status"] != idastar_status:
                raise RuntimeError(f"status_transcription_mismatch:{row['source_id']}")
            if row["certificate_tier"] == "CLASSIFICATION_EXACT_EXTRAS_BOUNDED" and (
                int(row["witness_endpoint_cost"]) >= int(row["baseline_cost"])
            ):
                raise RuntimeError(f"bounded_witness_not_improving:{row['source_id']}")
        checks["row_level_status_agreement"] = True
    except RuntimeError as exc:
        status = "FAIL"
        checks["failure_reason"] = str(exc)

    print(json.dumps({"status": status, "package": package.relative_to(ROOT).as_posix(), **checks}, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
