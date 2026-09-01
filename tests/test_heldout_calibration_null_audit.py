from analysis.heldout_calibration_null_audit import derive


def test_heldout_calibration_baseline_and_label_permutation(tmp_path):
    audit = derive(tmp_path, permutations=100)

    assert audit["status"] == "PASS_HELDOUT_CALIBRATION_NULL_BASELINE_AND_LABEL_PERMUTATION_COMPLETE"
    assert audit["execution_rows"] == 240
    assert audit["unique_inputs"] == 186
    assert audit["families"] == 8
    assert audit["calibration"]["glm_converged"] is True
    assert audit["exact_family_block_label_permutation"]["exact_assignments"] == 56
    assert audit["exact_family_block_label_permutation"]["positive_families_per_assignment"] == 5
    assert (tmp_path / "calibration_bins.csv").is_file()
    assert (tmp_path / "exact_family_block_label_permutations.csv").is_file()
    assert (tmp_path / "reliability_diagram.png").is_file()
