from analysis.e31_fidelity_threshold_sensitivity import build_audit


def test_frozen_e31_threshold_is_stable_and_stricter_grid_is_reported():
    audit = build_audit()

    assert audit["status"] == "PASS_E31_FIDELITY_THRESHOLD_SENSITIVITY_COMPLETE"
    assert audit["semantic_cells"] == 6858
    assert audit["formal_success_rows"] == 20314
    frozen = audit["threshold_grid"][audit["frozen_threshold"]]
    assert frozen["semantic_cells_accepted"] == 6858
    assert frozen["formal_success_rows_accepted"] == 20314
    assert "1.0" in audit["threshold_grid"]
