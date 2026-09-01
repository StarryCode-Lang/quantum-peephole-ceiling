"""Tests preventing pseudo-replication in family-level validation."""

import pandas as pd

from experiments.predictive_advantage import (
    _aggregate_family_predictions,
    validate_predictions,
)


def _predictions():
    return pd.DataFrame([
        {"circuit_family": "A", "n_qubits": 3, "ceiling_class": "ceiling",
         "predicted_optimizable": False, "predicted_reduction_pct": 0.0},
        {"circuit_family": "A", "n_qubits": 5, "ceiling_class": "ceiling",
         "predicted_optimizable": False, "predicted_reduction_pct": 0.0},
        {"circuit_family": "B", "n_qubits": 3, "ceiling_class": "open",
         "predicted_optimizable": True, "predicted_reduction_pct": 10.0},
        {"circuit_family": "B", "n_qubits": 5, "ceiling_class": "open",
         "predicted_optimizable": True, "predicted_reduction_pct": 20.0},
    ])


def test_family_aggregation_reports_instance_count_and_agreement():
    result = _aggregate_family_predictions(_predictions())
    assert len(result) == 2
    assert result.set_index("circuit_family").loc["B", "predicted_reduction_pct"] == 15.0
    assert set(result["n_prediction_instances"]) == {2}
    assert set(result["prediction_agreement"]) == {1.0}


def test_validation_counts_families_not_size_rows(tmp_path):
    sota = pd.DataFrame([
        {"circuit_family": "A", "mean_gate_reduction": 0.0, "tool": "x"},
        {"circuit_family": "B", "mean_gate_reduction": 12.0, "tool": "y"},
    ])
    path = tmp_path / "sota.csv"
    sota.to_csv(path, index=False)

    results, summary = validate_predictions(_predictions(), str(path))

    assert len(results) == 2
    assert summary["n_families"] == 2
    assert summary["n_with_sota_data"] == 2
