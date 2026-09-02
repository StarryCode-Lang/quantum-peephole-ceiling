"""Independent structural verifier for the E45 development grid."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
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
    required = ["protocol.json", "normalization_manifest.csv", "grid_results.csv", "config_summaries.json", "selection.json", "receipt.json"]
    missing = [name for name in required if not (OUTPUT / name).is_file()]
    if missing:
        print(json.dumps({"status": "FAIL", "reason": "missing:" + ",".join(missing)}))
        return 1
    protocol = json.loads((OUTPUT / "protocol.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((OUTPUT / "grid_results.csv").open(newline="", encoding="utf-8")))
    manifest = list(csv.DictReader((OUTPUT / "normalization_manifest.csv").open(newline="", encoding="utf-8")))
    expected = {"Nam-normalize-v1", "e44_core_v1"}
    checks = {
        "protocol_status": protocol.get("status") == "DEVELOPMENT_ONLY",
        "normalization_id": protocol.get("normalization", {}).get("id") == "Nam-normalize-v1",
        "configuration_count": len(protocol.get("configuration_grid", [])) == CONFIG_COUNT,
        "arm_set": set(protocol.get("arms", [])) == ARMS,
        "manifest_nonempty": bool(manifest),
        "rows_nonempty": bool(rows),
        "required_scopes": expected.issubset({protocol.get("normalization", {}).get("id"), protocol.get("rule_library", {}).get("rule_scope")}),
        "row_arm_set": {row.get("arm") for row in rows}.issubset(ARMS),
        "no_future_panel_marker": protocol.get("future_panel_access") == "E46_AND_LATER_NOT_READ",
        "receipt_hashes_match": all(json.loads((OUTPUT / "receipt.json").read_text(encoding="utf-8")).get(key) == sha256(OUTPUT / filename) for key, filename in (("protocol_sha256", "protocol.json"), ("normalization_manifest_sha256", "normalization_manifest.csv"), ("grid_results_sha256", "grid_results.csv"), ("config_summaries_sha256", "config_summaries.json"), ("selection_sha256", "selection.json"))),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, "checks": checks, "manifest_rows": len(manifest), "result_rows": len(rows)}, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
