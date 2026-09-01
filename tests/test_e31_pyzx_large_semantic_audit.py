"""Tests for the bounded largest-width E31 PyZX semantic audit."""

from analysis.e31_pyzx_large_semantic_audit import build_audit


def test_pyzx_proves_selected_large_cells_and_rejects_mutants(tmp_path):
    audit = build_audit(tmp_path, min_qubits=10, timeout_seconds=30.0)
    assert audit["status"] == "PASS_ALL_SELECTED_LARGE_E31_CELLS_ZX_REDUCED_TO_IDENTITY"
    assert audit["scope"]["cells"] == 9
    assert audit["scope"]["width_counts"] == {"10": 9}
    assert audit["results"]["proved_equal"] == 9
    assert audit["results"]["one_x_mutants"] == 1
    assert audit["results"]["mutants_not_proved_equal"] == 1
    assert audit["metric_dispositions"]["7.25"].startswith("PASS:")
