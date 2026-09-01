import json

from qiskit import QuantumCircuit

from analysis.cost_vector_scope_audit import (
    DEFAULT_OUTPUT_DIR,
    dependency_preserving_t_depth,
)


def test_dependency_preserving_t_depth_respects_causal_cliffords():
    parallel = QuantumCircuit(2)
    parallel.t(0)
    parallel.tdg(1)
    assert dependency_preserving_t_depth(parallel) == 1

    causal = QuantumCircuit(2)
    causal.t(0)
    causal.cx(0, 1)
    causal.t(1)
    assert dependency_preserving_t_depth(causal) == 2


def test_generated_cost_vector_scope_audit_is_complete():
    audit = json.loads(
        (DEFAULT_OUTPUT_DIR / "cost_vector_scope_audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert audit["status"] == "PASS_BOUNDED_COST_VECTOR_AND_SCOPE_AUDIT"
    assert audit["native_clifford_t"]["n_native_clifford_t_inputs"] == 360
    assert audit["native_clifford_t"]["n_reconstructed_rows"] == 1080
    assert audit["native_clifford_t"]["all_historical_output_hashes_reproduced"] is True
    assert audit["hardware_snapshot"]["run_rows"] == 288
    assert audit["hardware_snapshot"]["structural_design_cells"] == 48
    assert audit["fixed_unitary_scope"]["semantic_cells"] == 6858
    assert audit["fixed_unitary_scope"]["measurement_count_total"] == 0
    assert audit["fixed_unitary_scope"]["cells_with_idle_declared_wires"] == 965
