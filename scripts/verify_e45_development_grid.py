"""Independent structural verifier for the E45 development grid."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "v13" / "e45_development_grid"
CONFIG_COUNT = 18
ARMS = {
    "greedy", "wcl_greedy", "v12_cgl_greedy", "phase2b_greedy",
    "unguided_beam", "certificate_guided_escape",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    args = parser.parse_args()
    output = args.output_root.resolve()
    required = ["protocol.json", "normalization_manifest.csv", "grid_results.csv", "config_summaries.json", "selection.json", "receipt.json"]
    missing = [name for name in required if not (output / name).is_file()]
    if missing:
        print(json.dumps({"status": "FAIL", "reason": "missing:" + ",".join(missing)}))
        return 1
    protocol = json.loads((output / "protocol.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((output / "grid_results.csv").open(newline="", encoding="utf-8")))
    manifest = list(csv.DictReader((output / "normalization_manifest.csv").open(newline="", encoding="utf-8")))
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    reference_manifest_path = ROOT / "data" / "v13" / "e45_development_grid" / "normalization_manifest.csv"
    reference_manifest = []
    if reference_manifest_path.is_file():
        with reference_manifest_path.open(newline="", encoding="utf-8") as handle:
            reference_manifest = list(csv.DictReader(handle))
    source_scope_matches_v13 = bool(reference_manifest) and [
        row.get("source_sha256", "") for row in manifest
    ] == [row.get("source_sha256", "") for row in reference_manifest]
    expected = {"Nam-normalize-v1", "e44_core_v1"}
    checks = {
        "protocol_status": protocol.get("status") == "DEVELOPMENT_ONLY",
        "normalization_id": protocol.get("normalization", {}).get("id") == "Nam-normalize-v1",
        "configuration_count": len(protocol.get("configuration_grid", [])) == CONFIG_COUNT,
        "arm_set": set(protocol.get("arms", [])) == ARMS,
        "manifest_nonempty": bool(manifest),
        "rows_nonempty": bool(rows),
        "manifest_cardinality": len(manifest) == 128,
        "result_cardinality": len(rows) == 13_824,
        "source_scope_matches_v13": source_scope_matches_v13,
        "required_scopes": expected.issubset({protocol.get("normalization", {}).get("id"), protocol.get("rule_library", {}).get("rule_scope")}),
        "row_arm_set": {row.get("arm") for row in rows}.issubset(ARMS),
        "no_future_panel_marker": protocol.get("future_panel_access") == "E46_AND_LATER_NOT_READ",
        "receipt_cardinality": (
            receipt.get("source_count") == len(manifest)
            and receipt.get("normalized_count") == len(manifest)
            and receipt.get("result_rows") == len(rows)
            and receipt.get("configuration_count") == CONFIG_COUNT
            and receipt.get("arm_count") == len(ARMS)
        ),
        "receipt_hashes_match": all(receipt.get(key) == sha256(output / filename) for key, filename in (("protocol_sha256", "protocol.json"), ("normalization_manifest_sha256", "normalization_manifest.csv"), ("grid_results_sha256", "grid_results.csv"), ("config_summaries_sha256", "config_summaries.json"), ("selection_sha256", "selection.json"))),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, "checks": checks, "manifest_rows": len(manifest), "result_rows": len(rows)}, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
