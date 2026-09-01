from analysis.e31_specification_influence_audit import derive


def test_e31_specification_and_family_influence_audit(tmp_path):
    audit = derive(tmp_path)

    assert audit["status"] == "PASS_E31_SPECIFICATION_CURVE_AND_FAMILY_INFLUENCE_COMPLETE"
    assert audit["specification_count"] == 32
    assert audit["family_influence"]["leave_one_family_out_checks"] == 15
    assert (tmp_path / "specification_curve.csv").is_file()
    assert (tmp_path / "leave_one_family_out.csv").is_file()
    assert (tmp_path / "specification_curve.png").is_file()
