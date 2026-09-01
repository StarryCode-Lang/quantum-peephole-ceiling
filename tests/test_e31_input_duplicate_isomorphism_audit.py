from analysis.e31_input_duplicate_isomorphism_audit import build_audit


def test_e31_duplicate_and_qubit_relabel_audit_matches_frozen_design():
    audit = build_audit()

    assert audit["status"] == "PASS_NO_RESIDUAL_EXACT_OR_GLOBAL_QUBIT_RELABEL_DUPLICATES"
    assert audit["source_rows"] == 520
    assert audit["source_unique_logical_inputs"] == 391
    assert audit["source_repeated_rows_collapsed_before_e31"] == 129
    assert audit["e31_unique_input_hashes"] == 391
    assert audit["residual_exact_duplicate_inputs"] == 0
    assert audit["global_qubit_relabel_cluster_count"] == 0
