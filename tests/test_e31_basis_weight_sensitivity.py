import json
from pathlib import Path

from qiskit import QuantumCircuit

from analysis.e31_basis_weight_sensitivity import ROOT, circuit_costs


def test_basis_and_weight_cost_profiles_are_explicit():
    circuit = QuantumCircuit(2)
    circuit.rz(0.3, 0)
    circuit.cx(0, 1)
    costs = circuit_costs(circuit)["basis_costs"]["ibm_rz_sx_x_cx"]

    assert costs["equal"] == 2.0
    assert costs["two_qubit_10"] == 11.0
    assert costs["virtual_rz_two_qubit_10"] == 10.0


def test_generated_full_e31_basis_sensitivity_is_complete():
    path = ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis/basis_weight_sensitivity.json"
    audit = json.loads(path.read_text(encoding="utf-8"))

    assert audit["status"] == "PASS_E31_COMMON_BASIS_AND_GATE_WEIGHT_SENSITIVITY_COMPLETE"
    assert audit["formal_rows"] == 28152
    assert audit["success_rows"] == 20314
    assert audit["unique_inputs"] == 391
    assert audit["unique_successful_output_qpy_hashes"] == 1802
    assert audit["recorded_current_basis_counts_reproduced"] is True
    assert len(audit["cost_configurations"]) == 5
