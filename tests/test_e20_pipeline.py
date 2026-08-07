"""Regression tests for the E20 multi-compiler pipeline."""

from experiments.e20_multi_compiler_full.run import (
    QASM2_SX_DEFS,
    _inject_qasm2_sx_definitions,
)


def test_cirq_qasm_sx_definitions_are_injected_once():
    qasm = (
        'OPENQASM 2.0;\n'
        'include "qelib1.inc";\n'
        'qreg q[1];\n'
        'sx q[0];\n'
    )

    fixed = _inject_qasm2_sx_definitions(qasm)

    assert fixed.count("gate sx ") == 1
    assert fixed.count("gate sxdg ") == 1
    assert QASM2_SX_DEFS in fixed


def test_cirq_qasm_without_sx_is_unchanged():
    qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\nh q[0];\n'

    assert _inject_qasm2_sx_definitions(qasm) == qasm


def test_e20_run_accepts_an_explicit_output_directory():
    import inspect

    from experiments.e20_multi_compiler_full import run as e20_run

    signature = inspect.signature(e20_run.run)
    assert "output_dir" in signature.parameters
    assert signature.parameters["output_dir"].default is None
