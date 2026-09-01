"""Tests for the corrected E12 cross-stack reconciliation."""

import pandas as pd

from analysis import rerun_reconciliation
from analysis.e12_version_stack_reconciliation import build_audit


def test_e12_reconciliation_uses_full_level_key_and_separates_runtime(tmp_path):
    audit = build_audit(tmp_path)
    assert audit["status"] == "PASS_BOUNDED_E12_CROSS_STACK_RECONCILIATION"
    assert audit["scientific_key"] == ["circuit_id", "compiler_optimization_level"]
    assert audit["canonical_unique_keys"] == 568
    assert audit["rerun_unique_keys"] == 560
    assert audit["shared_unique_keys"] == 560
    assert len(audit["missing_rerun_keys"]) == 8
    assert audit["all_shared_scientific_rows_match"] is True
    assert audit["runtime_comparison"]["exact_matching_rows"] == 0
    assert audit["environment_change"]["qiskit_version_changed"] is False
    assert audit["metric_dispositions"]["12.26"].startswith("PARTIAL:")


def test_generic_overlap_reconciliation_does_not_collapse_e12_levels():
    canonical = pd.read_csv(rerun_reconciliation.PROJECT_ROOT / rerun_reconciliation.CANONICAL_MAP["E12"])
    rerun = pd.read_csv(
        rerun_reconciliation.PROJECT_ROOT
        / "data/v9/e12/e12_compiler_baseline_e12_full_20260721_072841_nocoupling.csv"
    )
    result = rerun_reconciliation.reconcile_overlap(canonical.copy(), rerun.copy())
    assert "compiler_optimization_level" in result["keys"]
    assert result["canonical_key_rows"] == 568
    assert result["rerun_key_rows"] == 560
    assert result["common_key_rows"] == 560
