"""Fail-closed Qiskit PassManager adapter for Q-research optimizers."""

from __future__ import annotations

from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.exceptions import TranspilerError

from src.equivalence import certify_equivalence
from src.optimisation.base import BaseOptimizer, OptimizationResult
from src.optimisation.constants import (
    DEFAULT_FIDELITY_SAMPLES,
    MAX_EXACT_FIDELITY_QUBITS,
)


class QResearchOptimizationPass(TransformationPass):
    """Run a ``BaseOptimizer`` as a Qiskit transformation pass.

    The adapter independently certifies the returned circuit against the DAG
    input and rejects unavailable or failed semantic evidence. It never trusts
    an optimizer's ``success`` flag as the sole integration boundary.
    """

    def __init__(
        self,
        optimizer: BaseOptimizer,
        *,
        fidelity_threshold: float = 0.9999999999,
        max_exact_qubits: int = MAX_EXACT_FIDELITY_QUBITS,
        n_samples: int = DEFAULT_FIDELITY_SAMPLES,
    ) -> None:
        super().__init__()
        if not isinstance(optimizer, BaseOptimizer):
            raise TypeError("optimizer must implement BaseOptimizer")
        self.optimizer = optimizer
        self.fidelity_threshold = float(fidelity_threshold)
        self.max_exact_qubits = int(max_exact_qubits)
        self.n_samples = int(n_samples)
        self.last_result: OptimizationResult | None = None
        self.last_certificate: dict[str, object] | None = None

    def run(self, dag):
        original = dag_to_circuit(dag)
        result = self.optimizer.optimize(original, target=original)
        optimized = result.optimized_circuit
        certificate = certify_equivalence(
            optimized,
            original,
            threshold=self.fidelity_threshold,
            max_exact_qubits=self.max_exact_qubits,
            n_samples=self.n_samples,
        )
        self.last_result = result
        self.last_certificate = certificate.to_dict()
        if not certificate.accepted:
            raise TranspilerError(
                "Q-research optimizer output rejected by the independent "
                f"integration certificate: {certificate.status}"
            )
        self.property_set["qresearch_optimization"] = {
            "optimizer": type(self.optimizer).__name__,
            "original_size": int(result.original_size),
            "optimized_size": int(result.optimized_size),
            "reduction": float(result.reduction),
            "certificate": self.last_certificate,
        }
        return circuit_to_dag(optimized)

