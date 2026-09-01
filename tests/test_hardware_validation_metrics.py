from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime.fake_provider import FakeManilaV2

from experiments.hardware_validation.run import circuit_structural_metrics


def test_hardware_metrics_use_target_snapshot_and_two_qubit_depth():
    backend = FakeManilaV2()
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    transpiled = transpile(
        circuit,
        backend=backend,
        initial_layout=[0, 1],
        routing_method="sabre",
        translation_method="translator",
        optimization_level=0,
        seed_transpiler=12345,
    )

    metrics = circuit_structural_metrics(transpiled, backend.target)

    assert metrics["two_qubit_gates"] >= 1
    assert metrics["two_qubit_depth"] >= 1
    assert metrics["scheduled_duration_seconds"] > 0
    assert 0 < metrics["calibration_success_probability"] <= 1


def test_logical_metrics_do_not_invent_backend_values():
    circuit = QuantumCircuit(2)
    circuit.cx(0, 1)

    metrics = circuit_structural_metrics(circuit)

    assert metrics["two_qubit_gates"] == 1
    assert metrics["two_qubit_depth"] == 1
    assert metrics["scheduled_duration_seconds"] is None
    assert metrics["calibration_success_probability"] is None
