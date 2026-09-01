import pytest
from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.exceptions import TranspilerError

from analysis.compiler_integration_audit import build
from src.integrations import QResearchOptimizationPass
from src.optimisation import GreedyGateCancellation
from src.optimisation.base import OptimizationResult


def test_qiskit_pass_manager_adapter_cancels_and_records_certificate():
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(0, 1)
    manager = PassManager([QResearchOptimizationPass(GreedyGateCancellation())])
    optimized = manager.run(circuit)
    assert optimized.size() == 0
    metadata = manager.property_set["qresearch_optimization"]
    assert metadata["certificate"]["accepted"] is True
    assert metadata["original_size"] == 4
    assert metadata["optimized_size"] == 0


class _LyingOptimizer(GreedyGateCancellation):
    def optimize(self, circuit, target=None):
        mutant = circuit.copy()
        mutant.x(0)
        return OptimizationResult(
            optimized_circuit=mutant,
            original_size=circuit.size(),
            optimized_size=mutant.size(),
            fidelity=1.0,
            iterations=1,
            runtime_seconds=0.0,
            success=True,
        )


def test_adapter_rejects_invalid_output_even_when_optimizer_claims_success():
    circuit = QuantumCircuit(1)
    with pytest.raises(TranspilerError, match="rejected"):
        PassManager([QResearchOptimizationPass(_LyingOptimizer())]).run(circuit)


def test_compiler_integration_audit_is_bounded(tmp_path):
    audit = build(tmp_path / "audit.json")
    assert audit["status"] == "PASS_QISKIT_PASSMANAGER_DIRECT_INTEGRATION"
    assert audit["sentinel"]["certificate_accepted"] is True
    assert audit["metric_dispositions"]["16.13"].startswith("PARTIAL:")
    assert "not a Cirq" in audit["claim_boundary"]

