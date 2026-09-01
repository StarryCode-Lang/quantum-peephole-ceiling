"""Independently verify the registry-backed 592-item research metric ledger.

This module intentionally imports no status map or assessment function from the
generator. It reparses both the frozen attachment and repository catalog, then
re-evaluates every evidence hash, selector, predicate, and ledger row.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATTACHMENT = Path(
    r"C:\Users\Administrator\.codex\attachments\719075d6-c952-41f9-8af7-35da63a72e52\pasted-text-1.txt"
)
DEFAULT_CATALOG = ROOT / "docs/review/metric_catalog_2026-08-11.md"
DEFAULT_REGISTRY = ROOT / "docs/review/metric_evidence_registry_2026-08-26.json"
DEFAULT_OUTPUT = ROOT / "docs/review/metric_audit_ledger_2026-08-24.csv"
DEFAULT_SUMMARY = ROOT / "docs/review/metric_audit_summary_2026-08-24.json"
DEFAULT_REPORT = ROOT / "docs/review/metric_audit_resolution_2026-08-24.md"
ALLOWED_STATUS = {"PASS", "PARTIAL", "FAIL", "EXTERNAL", "NA"}
REQUIRED_COLUMNS = {
    "metric_id", "section", "item", "metric", "metric_sha256", "target",
    "target_sha256", "criterion", "observed_value", "criterion_met", "status",
    "scope", "evidence_refs_json", "evidence_predicates_met",
    "assessment_predicate_json", "residual", "assessed_utc", "registry_sha256",
    "legacy_status_2026_08_24", "legacy_status_is_authoritative",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_catalog_independently(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    section = 0
    dashboard_item = 0
    numerals = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
                "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八"]
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        heading = re.fullmatch(r"#\s+([一二三四五六七八九十]+)、(.+)", line)
        if heading:
            if heading.group(1) not in numerals:
                raise RuntimeError("unknown catalog section numeral")
            section = numerals.index(heading.group(1)) + 1
            continue
        if section == 1 and line.startswith("|") and "---" not in line and "指标" not in line:
            cells = [value.strip() for value in line.strip("|").split("|")]
            if len(cells) >= 2 and cells[0]:
                dashboard_item += 1
                rows.append({"metric_id": f"1.{dashboard_item:02d}", "section": 1,
                             "item": dashboard_item, "catalog_text": cells[0],
                             "target": cells[1], "catalog_line": line_number})
            continue
        match = re.fullmatch(r"(\d+)\.\s+(.+)", line)
        if section and match:
            item = int(match.group(1))
            rows.append({"metric_id": f"{section}.{item:02d}", "section": section,
                         "item": item, "catalog_text": match.group(2),
                         "target": "top-tier audit question", "catalog_line": line_number})
    if len(rows) != 592 or len({str(row["metric_id"]) for row in rows}) != 592:
        raise RuntimeError("catalog is not a unique 592-item inventory")
    return rows


def _bool(value: object, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise RuntimeError(f"non-boolean {field}")


def _reference_matches(ref: dict[str, object], catalog: dict[str, dict[str, object]]) -> bool:
    relative = ref.get("path")
    if not isinstance(relative, str) or not relative:
        return False
    evidence = (ROOT / relative).resolve()
    try:
        evidence.relative_to(ROOT.resolve())
    except ValueError:
        return False
    if not evidence.is_file() or evidence.is_dir() or sha256(evidence) != ref.get("sha256"):
        return False
    selector = ref.get("selector")
    predicate = ref.get("predicate")
    if not isinstance(selector, dict):
        return False
    if predicate == "sha256_and_catalog_selector_match":
        if selector.get("type") != "catalog_metric_id":
            return False
        source = catalog.get(str(selector.get("metric_id")))
        return bool(source) and (
            int(selector.get("catalog_line", -1)) == int(source["catalog_line"])
            and selector.get("catalog_text_sha256") == text_sha256(str(source["catalog_text"]))
            and selector.get("target_sha256") == text_sha256(str(source["target"]))
        )
    if predicate == "sha256_and_json_pointer_equals":
        if selector.get("type") != "json_pointer_equals":
            return False
        value: object = json.loads(evidence.read_text(encoding="utf-8"))
        for part in str(selector.get("pointer", "")).strip("/").split("/"):
            if not part:
                continue
            if not isinstance(value, dict) or part not in value:
                return False
            value = value[part]
        return value == selector.get("expected")
    if predicate == "sha256_and_text_contains":
        return selector.get("type") == "text_contains" and isinstance(selector.get("text"), str) \
            and str(selector["text"]) in evidence.read_text(encoding="utf-8")
    if predicate == "sha256_matches_and_required_json_fields_exist":
        if selector.get("type") != "json_fields":
            return False
        required = selector.get("required")
        value = json.loads(evidence.read_text(encoding="utf-8"))
        return (isinstance(required, list) and bool(required) and isinstance(value, dict)
                and all(isinstance(field, str) and field in value for field in required))
    if predicate == "sha256_matches_and_required_csv_columns_exist":
        if selector.get("type") != "csv_columns":
            return False
        required = selector.get("required")
        with evidence.open("r", encoding="utf-8-sig", newline="") as stream:
            columns = csv.DictReader(stream).fieldnames or []
        return (isinstance(required, list) and bool(required)
                and all(isinstance(field, str) and field in columns for field in required))
    if predicate == "sha256_matches_and_required_literal_terms_present":
        if selector.get("type") != "literal_terms":
            return False
        required = selector.get("required")
        text = evidence.read_text(encoding="utf-8")
        return (isinstance(required, list) and bool(required)
                and all(isinstance(term, str) and term in text for term in required))
    return False


def _computed_assessment(entry: dict[str, object], catalog: dict[str, dict[str, object]]) -> tuple[bool, str, list[bool]]:
    refs = entry.get("evidence_refs")
    predicate = entry.get("assessment_predicate")
    if not isinstance(refs, list) or not refs or not isinstance(predicate, dict):
        raise RuntimeError(f"invalid registry evidence contract: {entry.get('metric_id')}")
    if predicate.get("type") != "all_satisfaction_evidence_matches":
        raise RuntimeError(f"unknown assessment predicate: {entry.get('metric_id')}")
    results = []
    satisfaction = []
    for ref in refs:
        if not isinstance(ref, dict):
            raise RuntimeError(f"non-object evidence ref: {entry.get('metric_id')}")
        if ref.get("metric_id") != entry.get("metric_id"):
            raise RuntimeError(f"evidence reference is not metric-bound: {entry.get('metric_id')}")
        result = _reference_matches(ref, catalog)
        results.append(result)
        if ref.get("role") == "satisfaction":
            if ref.get("predicate") == "sha256_and_catalog_selector_match":
                raise RuntimeError(
                    f"criterion-source selector cannot satisfy metric: {entry.get('metric_id')}"
                )
            satisfaction.append(result)
    minimum = predicate.get("minimum_satisfaction_refs")
    if not isinstance(minimum, int) or minimum < 1:
        raise RuntimeError(f"invalid satisfaction minimum: {entry.get('metric_id')}")
    criterion_met = len(satisfaction) >= minimum and all(results) and all(satisfaction)
    status = str(predicate.get("on_true") if criterion_met else predicate.get("on_false"))
    if status not in ALLOWED_STATUS or (criterion_met and status != "PASS"):
        raise RuntimeError(f"invalid computed status: {entry.get('metric_id')}")
    if status == "PASS" and any(not (ROOT / str(ref.get("path"))).is_file() for ref in refs):
        raise RuntimeError(f"PASS cites a directory or missing file: {entry.get('metric_id')}")
    return criterion_met, status, results


def verify(ledger_path: Path = DEFAULT_OUTPUT, summary_path: Path = DEFAULT_SUMMARY,
           catalog_path: Path = DEFAULT_CATALOG, registry_path: Path = DEFAULT_REGISTRY,
           attachment_path: Path = DEFAULT_ATTACHMENT, report_path: Path = DEFAULT_REPORT) -> dict[str, object]:
    for path in (ledger_path, summary_path, catalog_path, registry_path, attachment_path, report_path):
        if not path.is_file():
            raise RuntimeError(f"required audit artifact is missing: {path}")
    if sha256(catalog_path) != sha256(attachment_path):
        raise RuntimeError("repository catalog does not exactly match the referenced attachment")
    catalog_rows = parse_catalog_independently(catalog_path)
    attachment_rows = parse_catalog_independently(attachment_path)
    if catalog_rows != attachment_rows:
        raise RuntimeError("attachment/catalog 592-item text or target drift")
    catalog = {str(row["metric_id"]): row for row in catalog_rows}
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema_version") != "metric-evidence-registry-v2":
        raise RuntimeError("unsupported registry schema")
    if registry.get("catalog_sha256") != sha256(catalog_path) \
            or registry.get("source_attachment_sha256") != sha256(attachment_path):
        raise RuntimeError("registry source hash drift")
    entries = registry.get("metrics")
    if not isinstance(entries, list) or len(entries) != 592 \
            or len({entry.get("metric_id") for entry in entries if isinstance(entry, dict)}) != 592:
        raise RuntimeError("registry is not a unique 592-item inventory")
    frame = pd.read_csv(ledger_path, keep_default_na=False, dtype=str)
    if len(frame) != 592 or frame["metric_id"].nunique() != 592:
        raise RuntimeError("ledger is not a unique 592-item inventory")
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise RuntimeError(f"ledger lacks columns: {sorted(missing)}")
    if frame[list(REQUIRED_COLUMNS)].apply(lambda c: c.str.len().eq(0)).any().any():
        raise RuntimeError("ledger contains a blank required field")
    ledger = {str(row.metric_id): row for row in frame.itertuples(index=False)}
    registry_digest = sha256(registry_path)
    pass_ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("registry contains a non-object metric")
        metric_id = str(entry.get("metric_id"))
        source = catalog.get(metric_id)
        row = ledger.get(metric_id)
        if source is None or row is None:
            raise RuntimeError(f"metric inventory drift: {metric_id}")
        expected_fields = {
            "section": str(source["section"]), "item": str(source["item"]),
            "metric": str(source["catalog_text"]),
            "metric_sha256": text_sha256(str(source["catalog_text"])),
            "target": str(source["target"]), "target_sha256": text_sha256(str(source["target"])),
        }
        entry_field = {
            "metric": "catalog_text", "metric_sha256": "catalog_text_sha256",
            "target": "target", "target_sha256": "target_sha256",
            "section": "section", "item": "item",
        }
        for field, expected in expected_fields.items():
            if str(getattr(row, field)) != expected or str(entry.get(entry_field[field])) != expected:
                raise RuntimeError(f"catalog text/target/hash drift: {metric_id}.{field}")
        if int(entry.get("catalog_line", -1)) != int(source["catalog_line"]):
            raise RuntimeError(f"catalog selector line drift: {metric_id}")
        criterion_met, status, ref_results = _computed_assessment(entry, catalog)
        if not all(ref_results):
            raise RuntimeError(f"registry evidence selector/predicate drift: {metric_id}")
        if entry.get("criterion_met") is not criterion_met or entry.get("status") != status:
            raise RuntimeError(f"registry stores stale criterion/status: {metric_id}")
        comparisons = {
            "criterion": entry.get("criterion"), "observed_value": entry.get("observed_value"),
            "criterion_met": str(criterion_met), "status": status, "scope": entry.get("scope"),
            "evidence_refs_json": json.dumps(entry.get("evidence_refs"), ensure_ascii=False, sort_keys=True),
            "evidence_predicates_met": str(all(ref_results)),
            "assessment_predicate_json": json.dumps(entry.get("assessment_predicate"), sort_keys=True),
            "residual": entry.get("residual"), "assessed_utc": entry.get("assessed_utc"),
            "registry_sha256": registry_digest,
            "legacy_status_2026_08_24": entry.get("legacy_status_2026_08_24"),
            "legacy_status_is_authoritative": "False",
        }
        for field, expected in comparisons.items():
            observed = str(getattr(row, field))
            if field in {"criterion_met", "evidence_predicates_met", "legacy_status_is_authoritative"}:
                if _bool(observed, field=field) is not _bool(expected, field=field):
                    raise RuntimeError(f"ledger field drift: {metric_id}.{field}")
            elif observed != str(expected):
                raise RuntimeError(f"ledger field drift: {metric_id}.{field}")
        if status == "PASS":
            pass_ids.append(metric_id)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    counts = {str(key): int(value) for key, value in frame["status"].value_counts().items()}
    expected_summary = {
        "schema_version": "metric-audit-ledger-v2",
        "status": "SUPERSEDES_LEGACY_SHARED_EVIDENCE_LEDGER",
        "rows": 592, "catalog_sha256": sha256(catalog_path),
        "registry_sha256": registry_digest, "ledger_sha256": sha256(ledger_path),
        "report_sha256": sha256(report_path), "status_counts": counts,
        "item_specific_pass_coverage": {"numerator": len(pass_ids), "denominator": 592},
        "legacy_outputs_stale": True,
        "superseded_legacy_contract": registry.get("supersedes"),
    }
    for field, expected in expected_summary.items():
        if summary.get(field) != expected:
            raise RuntimeError(f"summary drift: {field}")
    return {"status": "VERIFIED_INDEPENDENT_REGISTRY_V2", "rows": 592,
            "status_counts": counts, "item_specific_pass_ids": pass_ids,
            "catalog_sha256": sha256(catalog_path), "registry_sha256": registry_digest,
            "ledger_sha256": sha256(ledger_path), "legacy_outputs_stale": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--attachment", type=Path, default=DEFAULT_ATTACHMENT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    print(json.dumps(verify(args.ledger, args.summary, args.catalog, args.registry,
                            args.attachment, args.report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
