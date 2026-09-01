"""Create the conservative, item-specific evidence registry for the 592 metrics.

This is a one-time migration helper.  The runtime ledger generator does not use
the legacy section maps below; it consumes the materialized per-metric registry.
Legacy PASS rows are deliberately migrated to PARTIAL until an item-specific
satisfaction predicate and file evidence are registered.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "docs/review/metric_catalog_2026-08-11.md"
DEFAULT_REGISTRY = ROOT / "docs/review/metric_evidence_registry_2026-08-26.json"


LEGACY_SPECS: dict[int, dict[str, str]] = {
    1: {"PASS": "1-8,10-12,16", "PARTIAL": "9,13-15,17,18", "FAIL": "19", "EXTERNAL": "20"},
    2: {"PASS": "1-5,7,10,13,15,19,21-25", "PARTIAL": "6,8,9,11,12,14,16-18,20"},
    3: {"PASS": "1-10,23-25,28", "PARTIAL": "11,14-17,20,22,26,29", "FAIL": "13,18,19,21,27,30", "EXTERNAL": "12"},
    4: {"PASS": "2,5-7,9-13,21-23,26", "PARTIAL": "1,3,8,14,15,17-19,25,27-29", "FAIL": "4,16,20,30", "NA": "24"},
    5: {"PASS": "2,3,6,8-10,13-15,18-22,24,25,27,33,34", "PARTIAL": "1,4,5,7,12,16,17,23,30,32,35", "FAIL": "11,26,28,29,31"},
    6: {"PASS": "2,3,6-8,14,15,17,19,26,32,35", "PARTIAL": "1,4,5,9-13,16,18,21,23,25,27-31,33,34", "FAIL": "20,22,24"},
    7: {"PASS": "1,2,7,10,12,13,17,18,20,21,23,24,26", "PARTIAL": "8,9,11,14-16,19,27-29", "FAIL": "6,22,25,30", "NA": "3-5"},
    8: {"PASS": "2-5,7,8,10,11,13,14,17,18,27,30-33", "PARTIAL": "1,6,9,12,16,19-24,26,29,34", "FAIL": "28", "NA": "15,25", "EXTERNAL": "35"},
    9: {"PASS": "1,3,6,9,21,37-39", "PARTIAL": "2,5,12,36,40,41,43,54", "FAIL": "4,7,8,10,11,13-20,22,23,42,44,45,49-53,55", "NA": "24-35,46-48"},
    10: {"PASS": "1,12,15,17,19,30,35", "PARTIAL": "16,18,21-23,25,29", "FAIL": "2,3,5-11,13,14,20,24,26-28,31-34", "NA": "4"},
    11: {"PASS": "1-7,9,11-13,15,17-26,31,34-36,38,39,43,46,49,50", "PARTIAL": "8,10,14,16,27,28,30,37,41,44,45,47", "FAIL": "29,32,33,40,42,48"},
    12: {"PASS": "1,3,5,7,8,12,13,16-18,20,31,33,34", "PARTIAL": "2,4,6,9,11,15,19,21,27,28,32", "FAIL": "10,14,22-26,29,30", "NA": "35"},
    13: {"PASS": "1,2,6,8,18", "PARTIAL": "4,21", "FAIL": "3,5,7,9-17,19,20,22-25"},
    14: {"PASS": "1,2,4,7,14,19,22,30,31,35", "PARTIAL": "5,15,21,25,26", "FAIL": "3,6,8-13,16-18,20,27-29,32,33", "NA": "23,24,34"},
    15: {"PASS": "3-5,8,12,14-20,23,24,30-35,37-39,43", "PARTIAL": "1,2,7,11,13,21,22,25-27,36,44,45", "FAIL": "6,9,10,28,29,40-42"},
    16: {"PASS": "3,5-7,10,24,25,28,29", "PARTIAL": "1,2,4,8,9,11,12,14,21,22,26,27,30", "FAIL": "13,15-20,23"},
    17: {"PASS": "1,2,9,11-14,16,18,23,25-28", "PARTIAL": "4-6,10,15,17,20,22,24", "FAIL": "3,7,8,19,21,29,30"},
    18: {"PARTIAL": "1,2,5,8,11", "FAIL": "3,4,6,7,10", "EXTERNAL": "9,12"},
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def numbers(spec: str) -> set[int]:
    values: set[int] = set()
    for token in filter(None, (part.strip() for part in spec.split(","))):
        if "-" in token:
            start, end = map(int, token.split("-", 1))
            values.update(range(start, end + 1))
        else:
            values.add(int(token))
    return values


def legacy_status(section: int, item: int) -> str:
    for status, spec in LEGACY_SPECS[section].items():
        if item in numbers(spec):
            return status
    raise RuntimeError(f"legacy inventory did not map {section}.{item:02d}")


def parse_catalog(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    section = 0
    dashboard_item = 0
    numerals = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
                "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八"]
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        heading = re.match(r"^#\s+([一二三四五六七八九十]+)、(.+)$", line)
        if heading:
            section = numerals.index(heading.group(1)) + 1
            continue
        if section == 1 and line.startswith("|") and "---" not in line and "指标" not in line:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 2 and cells[0]:
                dashboard_item += 1
                rows.append({"metric_id": f"1.{dashboard_item:02d}", "section": 1,
                             "item": dashboard_item, "catalog_text": cells[0],
                             "target": cells[1], "catalog_line": line_number})
            continue
        match = re.match(r"^(\d+)\.\s+(.+)$", line)
        if section and match:
            item = int(match.group(1))
            rows.append({"metric_id": f"{section}.{item:02d}", "section": section,
                         "item": item, "catalog_text": match.group(2),
                         "target": "top-tier audit question", "catalog_line": line_number})
    if len(rows) != 592 or len({row["metric_id"] for row in rows}) != 592:
        raise RuntimeError("catalog is not the expected unique 592-item inventory")
    return rows


def build_registry(catalog: Path, assessed_utc: str) -> dict[str, object]:
    catalog_sha = sha256_bytes(catalog.read_bytes())
    metrics = []
    for source in parse_catalog(catalog):
        old = legacy_status(int(source["section"]), int(source["item"]))
        unmet = "PARTIAL" if old in {"PASS", "PARTIAL"} else old
        text = str(source["catalog_text"])
        target = str(source["target"])
        metrics.append({
            **source,
            "catalog_text_sha256": sha256_bytes(text.encode("utf-8")),
            "target_sha256": sha256_bytes(target.encode("utf-8")),
            "criterion": target if int(source["section"]) == 1 else (
                "Provide a direct, item-specific answer to this audit question, supported by "
                "file-hashed evidence and a reproducible selector/predicate."
            ),
            "observed_value": "NO_ITEM_SPECIFIC_SATISFACTION_EVIDENCE_REGISTERED",
            "criterion_met": False,
            "status": unmet,
            "scope": "This catalog metric only; no neighboring metric or section-level evidence is inherited.",
            "evidence_refs": [{
                "role": "criterion_source",
                "metric_id": source["metric_id"],
                "path": "docs/review/metric_catalog_2026-08-11.md",
                "sha256": catalog_sha,
                "selector": {
                    "type": "catalog_metric_id",
                    "metric_id": source["metric_id"],
                    "catalog_line": source["catalog_line"],
                    "catalog_text_sha256": sha256_bytes(text.encode("utf-8")),
                    "target_sha256": sha256_bytes(target.encode("utf-8")),
                },
                "predicate": "sha256_and_catalog_selector_match",
            }],
            "assessment_predicate": {
                "type": "all_satisfaction_evidence_matches",
                "minimum_satisfaction_refs": 1,
                "on_true": "PASS",
                "on_false": unmet,
            },
            "residual": (
                "Register at least one item-specific satisfaction evidence file with its SHA-256, "
                "a machine-checkable selector, and a predicate that directly answers this metric."
            ),
            "assessed_utc": assessed_utc,
            "legacy_status_2026_08_24": old,
            "legacy_status_is_authoritative": False,
        })
    return {
        "schema_version": "metric-evidence-registry-v2",
        "catalog_path": "docs/review/metric_catalog_2026-08-11.md",
        "catalog_sha256": catalog_sha,
        "source_attachment_sha256": catalog_sha,
        "created_utc": assessed_utc,
        "migration_policy": "legacy PASS is PARTIAL until item-specific satisfaction evidence passes",
        "supersedes": {
            "status": "STALE_SUPERSEDED",
            "contract": "legacy section-status/shared-evidence assignment",
            "artifact_paths": [
                "docs/review/metric_audit_ledger_2026-08-24.csv",
                "docs/review/metric_audit_summary_2026-08-24.json",
                "docs/review/metric_audit_resolution_2026-08-24.md",
            ],
        },
        "metrics": metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--assessed-utc", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    payload = build_registry(args.catalog.resolve(), args.assessed_utc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(payload["metrics"]), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
