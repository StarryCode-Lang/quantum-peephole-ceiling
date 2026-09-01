"""Registry-backed generation tests for the 592-item audit ledger."""

from __future__ import annotations

import json

import pytest

from scripts.generate_metric_audit_ledger import (
    DEFAULT_CATALOG,
    DEFAULT_REGISTRY,
    build_rows,
    evaluate_metric,
    parse_catalog,
)


def test_catalog_and_registry_are_unique_592_item_inventories():
    catalog = parse_catalog(DEFAULT_CATALOG)
    rows, registry = build_rows(DEFAULT_CATALOG, DEFAULT_REGISTRY)
    assert len(catalog) == len(rows) == len(registry["metrics"]) == 592
    assert len({row["metric_id"] for row in rows}) == 592


def test_passes_are_item_specific_and_nonpass_rows_fail_closed():
    rows, registry = build_rows(DEFAULT_CATALOG, DEFAULT_REGISTRY)
    passes = [row for row in rows if row["status"] == "PASS"]
    declared_passes = sum(
        entry["status"] == "PASS" for entry in registry["metrics"]
    )
    assert len(passes) == declared_passes
    assert passes
    assert all(row["criterion_met"] is (row["status"] == "PASS") for row in rows)
    assert all(row["legacy_status_is_authoritative"] is False for row in rows)
    pass_ids = {row["metric_id"] for row in passes}
    for entry in registry["metrics"]:
        if entry["metric_id"] in pass_ids:
            satisfaction = [
                ref for ref in entry["evidence_refs"] if ref["role"] == "satisfaction"
            ]
            assert satisfaction
            assert all(
                ref["path"] != "docs/review/metric_catalog_2026-08-11.md"
                for ref in satisfaction
            )
        assert all(
            ref["path"] != "docs/review/metric_evidence_registry_2026-08-26.json"
            for ref in entry["evidence_refs"]
        )


def test_every_registry_row_has_hashed_file_selector_and_predicate():
    registry = json.loads(DEFAULT_REGISTRY.read_text(encoding="utf-8"))
    for entry in registry["metrics"]:
        assert entry["criterion"]
        assert entry["observed_value"]
        assert entry["scope"]
        assert entry["residual"]
        assert entry["assessed_utc"]
        assert entry["evidence_refs"]
        for ref in entry["evidence_refs"]:
            assert len(ref["sha256"]) == 64
            assert ref["selector"]
            assert ref["predicate"]
            assert (DEFAULT_CATALOG.parents[2] / ref["path"]).is_file()


def test_catalog_reference_cannot_be_relabelled_as_satisfaction():
    registry = json.loads(DEFAULT_REGISTRY.read_text(encoding="utf-8"))
    entry = registry["metrics"][0]
    entry["evidence_refs"][0]["role"] = "satisfaction"
    catalog = {str(row["metric_id"]): row for row in parse_catalog(DEFAULT_CATALOG)}
    with pytest.raises(RuntimeError, match="criterion-source selector cannot satisfy"):
        evaluate_metric(entry, catalog)


def test_registry_catalog_hash_drift_is_rejected(tmp_path):
    registry = json.loads(DEFAULT_REGISTRY.read_text(encoding="utf-8"))
    registry["catalog_sha256"] = "0" * 64
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(RuntimeError, match="catalog hash is stale"):
        build_rows(DEFAULT_CATALOG, path)
