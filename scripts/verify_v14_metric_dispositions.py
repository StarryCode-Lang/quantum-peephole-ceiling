"""Independently verify v14 evidence mappings before the 592-item ledger merge."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "release" / "v14_metric_dispositions.json"
ALLOWED_STATUS = {"PASS", "PARTIAL", "FAIL", "EXTERNAL", "NA"}


EXPECTED_STATUSES = {
    "1.18": "PARTIAL", "14.16": "EXTERNAL", "15.08": "PASS", "15.09": "EXTERNAL",
    "15.10": "EXTERNAL", "15.20": "PASS", "15.21": "PARTIAL", "15.22": "PARTIAL",
    "15.23": "PARTIAL", "15.24": "PARTIAL", "15.25": "PARTIAL", "15.26": "PARTIAL",
    "15.27": "PARTIAL", "15.28": "EXTERNAL", "15.29": "EXTERNAL", "15.30": "PARTIAL",
    "15.31": "NA", "15.32": "NA", "15.33": "PASS", "15.34": "PASS", "15.35": "PARTIAL",
    "15.36": "PARTIAL", "15.37": "PASS", "15.38": "PASS", "15.39": "PASS", "15.40": "EXTERNAL",
    "15.43": "PASS", "18.09": "EXTERNAL",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_pointer(value: object, pointer: str) -> object:
    current = value
    for raw_token in pointer.lstrip("/").split("/"):
        if not raw_token:
            continue
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        else:
            raise RuntimeError(f"missing JSON pointer: {pointer}")
    return current


def evaluate_evidence(record: dict[str, Any]) -> None:
    relative = record.get("path")
    if not isinstance(relative, str) or not relative:
        raise RuntimeError("evidence path is missing")
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError(f"evidence path escapes repository: {relative}") from exc
    if not path.is_file() or sha256(path) != record.get("sha256"):
        raise RuntimeError(f"evidence hash mismatch: {relative}")
    predicate = record.get("predicate")
    selector = record.get("selector")
    if not isinstance(selector, dict):
        raise RuntimeError(f"evidence selector is missing: {relative}")
    if predicate == "sha256_and_text_contains":
        if selector.get("type") != "text_contains" or selector.get("text") not in path.read_text(encoding="utf-8"):
            raise RuntimeError(f"text selector failed: {relative}")
        return
    if predicate == "sha256_matches_and_required_json_fields_exist":
        if selector.get("type") != "json_fields":
            raise RuntimeError(f"JSON field selector type failed: {relative}")
        value = json.loads(path.read_text(encoding="utf-8"))
        required = selector.get("required")
        if not isinstance(value, dict) or not isinstance(required, list) or not all(field in value for field in required):
            raise RuntimeError(f"JSON field selector failed: {relative}")
        return
    if predicate == "sha256_and_json_pointer_equals":
        if selector.get("type") != "json_pointer_equals":
            raise RuntimeError(f"JSON pointer selector type failed: {relative}")
        value = json_pointer(json.loads(path.read_text(encoding="utf-8")), str(selector.get("pointer", "")))
        if value != selector.get("expected"):
            raise RuntimeError(f"JSON pointer selector failed: {relative}")
        return
    raise RuntimeError(f"unsupported evidence predicate: {predicate}")


def run_json_command(arguments: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, *arguments], cwd=ROOT, capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"verification command failed: {' '.join(arguments)}")
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"verification command produced no receipt: {' '.join(arguments)}")
    result = json.loads(lines[-1])
    if result.get("status") != "PASS":
        raise RuntimeError(f"verification command did not pass: {' '.join(arguments)}")
    return result


def verify_e45_csvs() -> dict[str, object]:
    checks = {
        "screening": (ROOT / "data/v14/e45_development_grid/grid_results.csv", 13_824),
        "full": (ROOT / "data/v14/e45_full_development/grid_results.csv", 768),
    }
    result: dict[str, object] = {}
    for name, (path, expected_rows) in checks.items():
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != expected_rows or not rows:
            raise RuntimeError(f"unexpected CSV row count: {path}")
        for row in rows:
            for key, value in row.items():
                normalized = str(value).strip().lower()
                if normalized in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
                    raise RuntimeError(f"non-finite CSV value: {path}:{key}")
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(numeric):
                    raise RuntimeError(f"non-finite CSV value: {path}:{key}")
        result[name] = {"rows": len(rows), "columns": len(rows[0])}
    return result


def main() -> int:
    payload = json.loads(PACKAGE.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "v14-metric-dispositions-v1" or payload.get("status") != "VERIFIED_ITEM_SPECIFIC_BOUNDARIES":
        raise RuntimeError("unsupported v14 metric disposition package")
    dispositions = payload.get("metric_dispositions")
    metric_evidence = payload.get("metric_evidence")
    evidence = payload.get("evidence")
    if not isinstance(dispositions, dict) or set(dispositions) != set(EXPECTED_STATUSES):
        raise RuntimeError("metric disposition inventory mismatch")
    if not isinstance(metric_evidence, dict) or set(metric_evidence) != set(EXPECTED_STATUSES):
        raise RuntimeError("metric evidence inventory mismatch")
    if not isinstance(evidence, dict) or not evidence:
        raise RuntimeError("evidence inventory missing")

    for metric_id, expected_status in EXPECTED_STATUSES.items():
        disposition = dispositions[metric_id]
        if not isinstance(disposition, dict) or disposition.get("status") != expected_status or not disposition.get("disposition"):
            raise RuntimeError(f"disposition mismatch: {metric_id}")
        refs = metric_evidence[metric_id]
        if not isinstance(refs, list) or not refs:
            raise RuntimeError(f"metric evidence missing: {metric_id}")
        for evidence_id in refs:
            if evidence_id not in evidence:
                raise RuntimeError(f"unknown evidence id {evidence_id}: {metric_id}")

    for record in evidence.values():
        if not isinstance(record, dict):
            raise RuntimeError("non-object evidence record")
        evaluate_evidence(record)

    verdict = json.loads((ROOT / "release/v14_readiness_verdict.json").read_text(encoding="utf-8"))
    full_receipt = json.loads((ROOT / "data/v14/e45_full_development/receipt.json").read_text(encoding="utf-8"))
    hardware = json.loads((ROOT / "experiments/hardware_validation/real_qpu_protocol.json").read_text(encoding="utf-8"))
    zenodo = json.loads((ROOT / "release/zenodo_deposit_metadata.json").read_text(encoding="utf-8"))
    release_manifest = json.loads((ROOT / "release/release_manifest.json").read_text(encoding="utf-8"))
    checks: dict[str, object] = {
        "evidence_hashes_and_selectors": True,
        "v14_verdict_boundary": verdict.get("verdict") == "NOT_READY_FOR_PAPER" and verdict.get("scientific_gates", {}).get("S5_E45_full_development") == "COMPLETE_WITH_RESOURCE_BOUNDARY",
        "v14_full_counts": full_receipt.get("source_count") == 128 and full_receipt.get("result_rows") == 768 and full_receipt.get("status") == "DEVELOPMENT_COMPLETE_WITH_RESOURCE_BOUNDARY",
        "hardware_is_pending": hardware.get("authorization", {}).get("execution_status") == "NOT_EXECUTED" and hardware.get("status") == "FROZEN_PROTOCOL_PENDING_USER_AUTHORIZATION",
        "zenodo_is_pending": zenodo.get("release_boundary", {}).get("upload_performed") is False and zenodo.get("release_boundary", {}).get("doi") == "NOT_ASSIGNED",
        "release_manifest_shape": all(key in release_manifest for key in ("schema_version", "datasets", "environment", "git", "reproduction")),
    }
    checks["e45_verifier"] = run_json_command(["scripts/verify_e45_development_grid.py", "--output-root", "data/v14/e45_development_grid"]).get("status") == "PASS"
    checks["e45_exact_verifier"] = run_json_command(["scripts/verify_e45_exact_development.py", "--output-root", "data/v14/e45_full_development"]).get("status") == "PASS"
    checks["csv_shape_and_finite_values"] = verify_e45_csvs()
    if not all(value is True or isinstance(value, dict) for value in checks.values()):
        raise RuntimeError(f"v14 metric disposition checks failed: {checks}")
    print(json.dumps({"status": "PASS", "metrics": len(EXPECTED_STATUSES), "checks": checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
