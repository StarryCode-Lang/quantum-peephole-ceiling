"""Fail-closed verifier for the v14 IDA* escape-depth package."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.optimisation.certified_landscape import sha256_json


DEFAULT_OUTPUT = ROOT / "data" / "v14" / "e45_idastar_escape"
SCREENING_MANIFEST = ROOT / "data" / "v14" / "e45_development_grid" / "normalization_manifest.csv"
SCREENING_SELECTION = ROOT / "data" / "v14" / "e45_development_grid" / "selection.json"
EXPECTED_STATUS = {"EXACT_ESCAPE", "EXACT_H_LOCAL_OPTIMUM", "WITNESS_CERTIFIED_SEARCH_INCOMPLETE", "RESOURCE_BOUNDED_NO_WITNESS"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output_root.resolve()
    required = [
        output / "protocol.json",
        output / "normalization_manifest.csv",
        output / "grid_results.csv",
        output / "config_summaries.json",
        output / "certificates.jsonl",
        output / "selection.json",
        output / "receipt.json",
        SCREENING_MANIFEST,
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        print(json.dumps({"status": "FAIL", "missing": missing}, sort_keys=True))
        return 1

    protocol = read_json(output / "protocol.json")
    selection = read_json(output / "selection.json")
    screening_selection = read_json(SCREENING_SELECTION)
    receipt = read_json(output / "receipt.json")
    summaries = read_json(output / "config_summaries.json")
    with (output / "normalization_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    with SCREENING_MANIFEST.open(newline="", encoding="utf-8") as handle:
        screening_manifest = list(csv.DictReader(handle))
    with (output / "grid_results.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    certificates = [
        json.loads(line)
        for line in (output / "certificates.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cert_by_source = {item.get("source_id"): item for item in certificates}
    row_by_source = {row.get("source_id"): row for row in rows}
    checks: dict[str, bool] = {
        "protocol_status": protocol.get("status") == "DEVELOPMENT_ONLY",
        "method": protocol.get("search_method", {}).get("id") == "idastar_escape_v1",
        "phase_declared": protocol.get("phase") in {"full_development", "smoke"},
        "selected_config": (
            protocol.get("phase") == "smoke"
            and all(
                key in selection.get("selected_config", {})
                for key in ("config_id", "horizon", "beam_width", "state_budget", "barrier_cap")
            )
        ) or (
            protocol.get("phase") != "smoke"
            and all(
                selection.get("selected_config", {}).get(key)
                == screening_selection.get("selected_config", {}).get(key)
                for key in ("config_id", "horizon", "beam_width", "state_budget", "barrier_cap")
            )
        ),
        "arm_set": protocol.get("arms") == ["idastar_escape"] and {row.get("arm") for row in rows} == {"idastar_escape"},
        "source_scope": [row.get("source_sha256") for row in manifest] == [row.get("source_sha256") for row in screening_manifest[: len(manifest)]],
        "cardinality": len(rows) == len(manifest) == len(certificates) and len(certificates) == receipt.get("source_count") == receipt.get("result_rows"),
        "certificate_join": set(cert_by_source) == set(row_by_source) == {row.get("source_id") for row in manifest},
        "status_set": all(row.get("status") in EXPECTED_STATUS for row in rows),
        "no_false_exact": all(
            item["certificate"].get("resource_status") != "TRUNCATED"
            or item["certificate"].get("status") not in {"EXACT_ESCAPE", "EXACT_H_LOCAL_OPTIMUM"}
            for item in certificates
        ),
        "replay_boundary": all(
            item.get("witness_replay_status") == ("REPLAY_PASS" if item["certificate"].get("witnesses", {}).get("escape") else "NO_WITNESS")
            for item in certificates
        ),
        "certificate_hashes": all(
            item["certificate"].get("certificate_sha256")
            == sha256_json({key: value for key, value in item["certificate"].items() if key != "certificate_sha256"})
            for item in certificates
        ),
        "artifact_hashes": all(
            receipt.get(key) == sha256(output / filename)
            for key, filename in {
                "protocol_sha256": "protocol.json",
                "normalization_manifest_sha256": "normalization_manifest.csv",
                "grid_results_sha256": "grid_results.csv",
                "config_summaries_sha256": "config_summaries.json",
                "certificates_sha256": "certificates.jsonl",
                "selection_sha256": "selection.json",
            }.items()
        ),
        "summary_join": len(summaries) == 1 and summaries[0].get("row_count") == len(rows),
    }
    checks["row_certificate_join"] = all(
        row["status"] == cert_by_source[row["source_id"]]["certificate"].get("status")
        and row["escape_depth"] in {"", str(cert_by_source[row["source_id"]]["certificate"].get("escape_depth"))}
        and row["resource_status"] == cert_by_source[row["source_id"]]["certificate"].get("resource_status")
        for row in rows
    )
    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, "checks": checks, "source_count": len(manifest), "result_rows": len(rows)}, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
