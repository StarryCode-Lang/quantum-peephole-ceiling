"""Tests for class- and exact-gate-set-out diagnostic cross-fitting."""

from analysis.heldout_class_gateset_generalization_audit import build_audit


def test_all_rows_receive_class_and_gateset_crossfit_predictions(tmp_path):
    audit = build_audit(tmp_path)
    assert audit["status"] == "PASS_DIAGNOSTIC_CLASS_AND_GATESET_GENERALIZATION_AUDIT"
    assert audit["integrity"]["rows"] == 520
    assert audit["integrity"]["families"] == 15
    assert audit["leave_one_algorithm_class_out"]["folds"] == 4
    assert audit["leave_one_algorithm_class_out"]["pooled_cross_fitted_metrics"]["n"] == 520
    assert audit["leave_one_exact_gate_set_out"]["folds"] == 18
    assert audit["leave_one_exact_gate_set_out"]["pooled_cross_fitted_metrics"]["n"] == 520
    assert audit["metric_dispositions"]["13.10"].startswith("PASS:")
    assert audit["metric_dispositions"]["13.11"].startswith("PASS:")
