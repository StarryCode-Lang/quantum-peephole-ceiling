import json

from analysis.heldout_generalization_ood_audit import DEFAULT_OUTPUT_DIR


def test_generated_generalization_ood_audit_is_complete_and_bounded():
    audit = json.loads(
        (DEFAULT_OUTPUT_DIR / "generalization_ood_audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert audit["status"] == "PASS_POSTSEAL_GENERALIZATION_OOD_AUDIT"
    assert audit["integrity"]["training_rows"] == 520
    assert audit["integrity"]["training_families"] == 15
    assert audit["integrity"]["heldout_rows"] == 378
    assert audit["integrity"]["heldout_families"] == 16
    assert audit["integrity"]["family_overlap"] == []
    assert audit["integrity"]["input_hash_overlap"] == 0
    assert audit["integrity"]["sealed_probability_replay_max_abs_error"] < 1e-12
    assert audit["outer_interval"]["narrow_interval_criterion_met"] is False
    assert audit["shortcut_diagnostics"]["feature_ablation_specs"] == 15
    assert audit["shortcut_diagnostics"]["training_logo_folds"] == 15
    assert audit["qubit_extrapolation"]["out_of_range_test_present"] is False
    assert "synthetic" in audit["claim_boundary"]


def test_ood_threshold_uses_training_only_and_abstention_is_diagnostic():
    audit = json.loads(
        (DEFAULT_OUTPUT_DIR / "generalization_ood_audit.json").read_text(
            encoding="utf-8"
        )
    )
    selective = audit["selective_prediction"]
    assert selective["threshold_source"] == "training features only"
    assert selective["status"] == "POST_SEAL_DIAGNOSTIC_NOT_PRIMARY_CLASSIFIER_CHANGE"
    assert 0.0 <= selective["coverage"] <= 1.0
