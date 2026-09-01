from analysis.e03_scaling_model_audit import build_audit


def test_e03_scaling_audit_has_models_cis_and_heldout_size():
    audit = build_audit(bootstrap_replicates=40)

    assert audit["status"] == "PASS_BOUNDED_SCALING_MODEL_CI_AND_EXTRAPOLATION_AUDIT"
    assert audit["rows"] == 12000
    assert audit["n_qubit_levels"] == list(range(3, 11))
    assert set(audit["models"]) == {
        "quadratic_polynomial",
        "exponential",
        "piecewise_linear_hinge",
    }
    for model in audit["models"].values():
        assert model["bootstrap_coefficient_ci95"]
        assert len(model["fitted_mean_runtime_ci95_by_n_qubits"]) == 8
    for result in audit["out_of_range_extrapolation"].values():
        assert result["trained_sizes"] == list(range(3, 10))
        assert result["held_out_size"] == 10
        assert result["bootstrap_mean_prediction_ci95"]
