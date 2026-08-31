from experiments.e36_pyzx_third_artifact import INPUTS, unitary_qasm


def test_normalization_removes_measurements_and_barriers() -> None:
    _, circuit = unitary_qasm(INPUTS[0])
    assert circuit.num_clbits == 0
    assert all(instruction.operation.name != "barrier" for instruction in circuit.data)
