"""Independent integrity tests for the registry-backed 592-item ledger."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.verify_metric_audit_ledger import (
    DEFAULT_ATTACHMENT,
    DEFAULT_CATALOG,
    DEFAULT_OUTPUT,
    DEFAULT_REGISTRY,
    DEFAULT_REPORT,
    DEFAULT_SUMMARY,
    verify,
)


def test_current_metric_ledger_is_independently_verified():
    report = verify()
    assert report["status"] == "VERIFIED_INDEPENDENT_REGISTRY_V2"
    assert report["rows"] == 592
    summary = json.loads(DEFAULT_SUMMARY.read_text(encoding="utf-8"))
    pass_ids = report["item_specific_pass_ids"]
    assert len(pass_ids) == summary["item_specific_pass_coverage"]["numerator"]
    assert len(pass_ids) == len(set(pass_ids))
    assert pass_ids
    assert report["legacy_outputs_stale"] is True


def test_verifier_rejects_manual_status_edit_even_if_summary_hash_is_updated(tmp_path: Path):
    frame = pd.read_csv(DEFAULT_OUTPUT, keep_default_na=False, dtype=str)
    # Use a bounded PARTIAL metric.  Event telemetry metrics 9.51/9.52 are now
    # legitimately PASS and no longer exercise a manual status escalation.
    frame.loc[frame["metric_id"].astype(str).eq("10.08"), "status"] = "PASS"
    ledger = tmp_path / "ledger.csv"
    frame.to_csv(ledger, index=False)
    summary = json.loads(DEFAULT_SUMMARY.read_text(encoding="utf-8"))
    summary["ledger_sha256"] = hashlib.sha256(ledger.read_bytes()).hexdigest()
    summary["status_counts"] = {
        str(key): int(value) for key, value in frame["status"].value_counts().items()
    }
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(RuntimeError, match="ledger field drift: 10.08.status"):
        verify(ledger, summary_path, DEFAULT_CATALOG, DEFAULT_REGISTRY,
               DEFAULT_ATTACHMENT, DEFAULT_REPORT)


def test_verifier_rejects_attachment_catalog_text_drift(tmp_path: Path):
    catalog = tmp_path / "catalog.md"
    catalog.write_text(DEFAULT_CATALOG.read_text(encoding="utf-8").replace(
        "核心主张证据覆盖率", "核心主张证据覆盖率已改", 1), encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not exactly match"):
        verify(DEFAULT_OUTPUT, DEFAULT_SUMMARY, catalog, DEFAULT_REGISTRY,
               DEFAULT_ATTACHMENT, DEFAULT_REPORT)


def test_verifier_rejects_registry_selector_drift(tmp_path: Path):
    registry = json.loads(DEFAULT_REGISTRY.read_text(encoding="utf-8"))
    registry["metrics"][0]["evidence_refs"][0]["selector"]["catalog_text_sha256"] = "0" * 64
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(RuntimeError, match="evidence selector/predicate drift"):
        verify(DEFAULT_OUTPUT, DEFAULT_SUMMARY, DEFAULT_CATALOG, registry_path,
               DEFAULT_ATTACHMENT, DEFAULT_REPORT)


def test_independent_verifier_does_not_import_generator_status_logic():
    source = Path(__file__).parents[1].joinpath(
        "scripts/verify_metric_audit_ledger.py"
    ).read_text(encoding="utf-8")
    assert "from scripts.generate_metric_audit_ledger" not in source
    assert "SPECS" not in source
    assert "_resolved_status" not in source
