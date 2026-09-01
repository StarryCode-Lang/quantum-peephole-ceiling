import json

from analysis.compiler_version_sensitivity_verifier import DEFAULT_OUTPUT


def test_independent_version_panel_receipt_replays_every_artifact():
    receipt = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS_INDEPENDENT_COMPILER_VERSION_REPLAY"
    assert receipt["design_rows"] == 105
    assert receipt["environments"] == 7
    assert receipt["families"] == 15
    assert receipt["optimized_qasm_artifacts_verified"] == 105
    assert receipt["semantic_unitaries_recomputed"] == 105
    assert receipt["minimum_unitary_trace_overlap"] >= receipt["equivalence_threshold"]
    assert receipt["all_structure_fingerprints_recomputed"] is True
