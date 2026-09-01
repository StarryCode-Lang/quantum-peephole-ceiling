"""Generate the 592-item ledger from the item-specific evidence registry.

No section-level status map exists in this module. A PASS can only be emitted
when item-specific satisfaction evidence passes every registered hash,
selector, and predicate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "docs/review/metric_catalog_2026-08-11.md"
DEFAULT_REGISTRY = ROOT / "docs/review/metric_evidence_registry_2026-08-26.json"
DEFAULT_OUTPUT = ROOT / "docs/review/metric_audit_ledger_2026-08-24.csv"
DEFAULT_SUMMARY = ROOT / "docs/review/metric_audit_summary_2026-08-24.json"
DEFAULT_REPORT = ROOT / "docs/review/metric_audit_resolution_2026-08-24.md"
ALLOWED_STATUS = {"PASS", "PARTIAL", "FAIL", "EXTERNAL", "NA"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def _evaluate_catalog_selector(ref: dict[str, object], catalog_by_id: dict[str, dict[str, object]]) -> bool:
    selector = ref.get("selector")
    if not isinstance(selector, dict) or selector.get("type") != "catalog_metric_id":
        return False
    row = catalog_by_id.get(str(selector.get("metric_id")))
    return bool(row) and (
        int(selector.get("catalog_line", -1)) == int(row["catalog_line"])
        and selector.get("catalog_text_sha256") == text_sha256(str(row["catalog_text"]))
        and selector.get("target_sha256") == text_sha256(str(row["target"]))
    )


def _evaluate_ref(ref: dict[str, object], catalog_by_id: dict[str, dict[str, object]]) -> bool:
    path_value = ref.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        return False
    path = (ROOT / path_value).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        return False
    if not path.is_file() or path.is_dir() or ref.get("sha256") != sha256(path):
        return False
    predicate = ref.get("predicate")
    if predicate == "sha256_and_catalog_selector_match":
        return _evaluate_catalog_selector(ref, catalog_by_id)
    selector = ref.get("selector")
    if predicate == "sha256_and_json_pointer_equals" and isinstance(selector, dict):
        if selector.get("type") != "json_pointer_equals":
            return False
        value: object = json.loads(path.read_text(encoding="utf-8"))
        for token in str(selector.get("pointer", "")).strip("/").split("/"):
            if not token:
                continue
            if isinstance(value, dict) and token in value:
                value = value[token]
            else:
                return False
        return value == selector.get("expected")
    if predicate == "sha256_and_text_contains" and isinstance(selector, dict):
        if selector.get("type") != "text_contains":
            return False
        needle = selector.get("text")
        return isinstance(needle, str) and needle in path.read_text(encoding="utf-8")
    if predicate == "sha256_matches_and_required_json_fields_exist" and isinstance(selector, dict):
        if selector.get("type") != "json_fields":
            return False
        required = selector.get("required")
        value = json.loads(path.read_text(encoding="utf-8"))
        return (isinstance(required, list) and bool(required) and isinstance(value, dict)
                and all(isinstance(field, str) and field in value for field in required))
    if predicate == "sha256_matches_and_required_csv_columns_exist" and isinstance(selector, dict):
        if selector.get("type") != "csv_columns":
            return False
        required = selector.get("required")
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            columns = csv.DictReader(stream).fieldnames or []
        return (isinstance(required, list) and bool(required)
                and all(isinstance(field, str) and field in columns for field in required))
    if predicate == "sha256_matches_and_required_literal_terms_present" and isinstance(selector, dict):
        if selector.get("type") != "literal_terms":
            return False
        required = selector.get("required")
        text = path.read_text(encoding="utf-8")
        return (isinstance(required, list) and bool(required)
                and all(isinstance(term, str) and term in text for term in required))
    return False


def evaluate_metric(entry: dict[str, object], catalog_by_id: dict[str, dict[str, object]]) -> tuple[bool, str, list[bool]]:
    refs = entry.get("evidence_refs")
    predicate = entry.get("assessment_predicate")
    if not isinstance(refs, list) or not isinstance(predicate, dict):
        raise RuntimeError(f"invalid evidence contract: {entry.get('metric_id')}")
    if any(not isinstance(ref, dict) or ref.get("metric_id") != entry.get("metric_id")
           for ref in refs):
        raise RuntimeError(f"evidence reference is not metric-bound: {entry.get('metric_id')}")
    results = [_evaluate_ref(ref, catalog_by_id) for ref in refs if isinstance(ref, dict)]
    if len(results) != len(refs):
        raise RuntimeError(f"invalid evidence reference: {entry.get('metric_id')}")
    if predicate.get("type") != "all_satisfaction_evidence_matches":
        raise RuntimeError(f"unknown assessment predicate: {entry.get('metric_id')}")
    satisfaction = [result for ref, result in zip(refs, results)
                    if isinstance(ref, dict) and ref.get("role") == "satisfaction"]
    if any(ref.get("role") == "satisfaction"
           and ref.get("predicate") == "sha256_and_catalog_selector_match"
           for ref in refs if isinstance(ref, dict)):
        raise RuntimeError(f"criterion-source selector cannot satisfy metric: {entry.get('metric_id')}")
    minimum = predicate.get("minimum_satisfaction_refs")
    if not isinstance(minimum, int) or minimum < 1:
        raise RuntimeError(f"invalid satisfaction minimum: {entry.get('metric_id')}")
    criterion_met = len(satisfaction) >= minimum and all(results) and all(satisfaction)
    status = str(predicate.get("on_true") if criterion_met else predicate.get("on_false"))
    if status not in ALLOWED_STATUS or (criterion_met and status != "PASS"):
        raise RuntimeError(f"invalid computed status: {entry.get('metric_id')}")
    return criterion_met, status, results


def build_rows(catalog_path: Path, registry_path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    catalog_rows = parse_catalog(catalog_path)
    catalog_by_id = {str(row["metric_id"]): row for row in catalog_rows}
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema_version") != "metric-evidence-registry-v2":
        raise RuntimeError("unsupported metric evidence registry schema")
    if registry.get("catalog_sha256") != sha256(catalog_path):
        raise RuntimeError("registry catalog hash is stale")
    entries = registry.get("metrics")
    if not isinstance(entries, list) or len(entries) != 592:
        raise RuntimeError("registry is not a 592-item inventory")
    if len({entry.get("metric_id") for entry in entries if isinstance(entry, dict)}) != 592:
        raise RuntimeError("registry metric IDs are not unique")
    rows: list[dict[str, object]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("registry contains a non-object metric")
        metric_id = str(entry.get("metric_id"))
        catalog = catalog_by_id.get(metric_id)
        if catalog is None:
            raise RuntimeError(f"registry contains unknown metric: {metric_id}")
        for key in ("section", "item", "catalog_line", "catalog_text", "target"):
            if entry.get(key) != catalog.get(key):
                raise RuntimeError(f"registry catalog field drift: {metric_id}.{key}")
        if entry.get("catalog_text_sha256") != text_sha256(str(catalog["catalog_text"])):
            raise RuntimeError(f"registry text hash drift: {metric_id}")
        if entry.get("target_sha256") != text_sha256(str(catalog["target"])):
            raise RuntimeError(f"registry target hash drift: {metric_id}")
        criterion_met, status, ref_results = evaluate_metric(entry, catalog_by_id)
        if entry.get("criterion_met") is not criterion_met or entry.get("status") != status:
            raise RuntimeError(f"registry stores a stale assessment: {metric_id}")
        rows.append({
            "metric_id": metric_id, "section": entry["section"], "item": entry["item"],
            "metric": entry["catalog_text"], "metric_sha256": entry["catalog_text_sha256"],
            "target": entry["target"], "target_sha256": entry["target_sha256"],
            "criterion": entry["criterion"], "observed_value": entry["observed_value"],
            "criterion_met": criterion_met, "status": status, "scope": entry["scope"],
            "evidence_refs_json": json.dumps(entry["evidence_refs"], ensure_ascii=False, sort_keys=True),
            "evidence_predicates_met": all(ref_results),
            "assessment_predicate_json": json.dumps(entry["assessment_predicate"], sort_keys=True),
            "residual": entry["residual"], "assessed_utc": entry["assessed_utc"],
            "registry_sha256": sha256(registry_path),
            "legacy_status_2026_08_24": entry["legacy_status_2026_08_24"],
            "legacy_status_is_authoritative": False,
        })
    return rows, registry


def write_outputs(rows: list[dict[str, object]], registry: dict[str, object], *,
                  catalog_path: Path, registry_path: Path, output: Path,
                  summary_path: Path, report_path: Path) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts: dict[str, int] = {}
    for row in rows:
        counts[str(row["status"])] = counts.get(str(row["status"]), 0) + 1
    pass_count = counts.get("PASS", 0)
    report = "\n".join([
        "# Q-research 592-item metric evidence ledger v2", "",
        "Status: supersedes the legacy section-status/shared-evidence ledger.", "",
        f"- Registry: `{registry_path.relative_to(ROOT).as_posix()}`",
        f"- Registry SHA-256: `{sha256(registry_path)}`",
        f"- Catalog SHA-256: `{sha256(catalog_path)}`",
        f"- Item-specific PASS coverage: **{pass_count}/592**.",
        f"- Status counts: `{json.dumps(counts, sort_keys=True)}`.", "",
        "A row is PASS only when item-specific satisfaction evidence is a file, its current SHA-256 "
        "matches, its selector/predicate passes, and the registry assessment predicate is true. "
        "Directories and criterion-source references cannot satisfy a metric.", "",
        "The former CSV/summary contents are stale and superseded. Their section-level PASS values "
        "must not be cited as evidence of completion.", "",
    ])
    report_path.write_text(report, encoding="utf-8")
    summary = {
        "schema_version": "metric-audit-ledger-v2",
        "status": "SUPERSEDES_LEGACY_SHARED_EVIDENCE_LEDGER", "rows": 592,
        "catalog_sha256": sha256(catalog_path), "registry_sha256": sha256(registry_path),
        "ledger_sha256": sha256(output), "report_sha256": sha256(report_path),
        "status_counts": counts,
        "item_specific_pass_coverage": {"numerator": pass_count, "denominator": 592},
        "legacy_outputs_stale": True, "registry_created_utc": registry.get("created_utc"),
        "superseded_legacy_contract": registry.get("supersedes"),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    rows, registry = build_rows(args.catalog.resolve(), args.registry.resolve())
    summary = write_outputs(rows, registry, catalog_path=args.catalog.resolve(),
                            registry_path=args.registry.resolve(), output=args.output.resolve(),
                            summary_path=args.summary.resolve(), report_path=args.report.resolve())
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
