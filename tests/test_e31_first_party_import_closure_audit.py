"""Regression tests for the independently reconstructed E31 import closure."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.audit_e31_first_party_import_closure as audit


def test_current_e31_import_closure_is_exactly_frozen_plus_disclosed():
    payload = audit.build_audit()
    assert payload["status"] == "PASS_EXACT_STATIC_FIRST_PARTY_IMPORT_CLOSURE_RECONSTRUCTED"
    assert payload["resolved_source_count"] == 23
    assert payload["direct_prerun_frozen_count"] == 7
    assert payload["posthoc_disclosed_count"] == 16
    assert payload["complete_cryptographic_prerun_source_closure"] is False
    assert payload["dynamic_imports_not_proven"] is True


def test_recorded_import_closure_audit_fails_closed_on_inventory_drift(
    tmp_path: Path,
):
    payload = audit.build_audit()
    payload["resolved_sources"].pop("src/optimisation/base.py")
    path = tmp_path / "audit.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="absent, stale, or inconsistent"):
        audit.verify_audit(path)
