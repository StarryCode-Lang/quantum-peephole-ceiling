"""Fail-closed semantic equivalence certificates for quantum circuits.

The module deliberately implements a narrow contract: fixed-width, fully
bound, unitary Qiskit circuits, compared up to global phase.  Dynamic or
non-unitary programs and circuits with free parameters are reported as
unavailable rather than being coerced into an ``Operator`` or sampled at a
finite set of parameter values.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Clifford, Operator, Statevector


class EquivalenceMethod(str, Enum):
    """Evidence class used by an equivalence certificate."""

    EXACT_STRUCTURAL = "exact_structural"
    EXACT_CLIFFORD = "exact_clifford"
    NUMERICAL_UNITARY = "numerical_unitary"
    SAMPLED_GLOBAL_HAAR = "sampled_global_haar"
    HEURISTIC = "heuristic"
    UNAVAILABLE = "unavailable"


class EquivalenceStatus(str, Enum):
    """Conclusion strength, kept separate from a numeric fidelity value."""

    VERIFIED_EQUIVALENT = "verified_equivalent"
    VERIFIED_NOT_EQUIVALENT = "verified_not_equivalent"
    ESTIMATED_EQUIVALENT = "estimated_equivalent"
    ESTIMATED_NOT_EQUIVALENT = "estimated_not_equivalent"
    INCONCLUSIVE = "inconclusive"
    UNAVAILABLE = "unavailable"


UNITARY_SCOPE = "fixed-width bound-parameter unitary, up to global phase"


@dataclass(frozen=True)
class EquivalenceCertificate:
    """Machine-readable evidence for one circuit-equivalence decision."""

    method: EquivalenceMethod
    status: EquivalenceStatus
    scope: str
    threshold: float
    fidelity: float | None = None
    standard_error: float | None = None
    samples: int | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def passes_threshold(self) -> bool:
        """Whether available numeric evidence crosses the declared threshold."""
        return self.fidelity is not None and bool(self.fidelity >= self.threshold)

    @property
    def accepted(self) -> bool:
        """Whether this contract accepts functionality preservation.

        Sampled evidence is accepted only as an explicitly estimated result;
        callers needing proof-grade evidence should use ``is_verified``.
        Heuristic and unavailable certificates always fail closed.
        """
        return self.status in {
            EquivalenceStatus.VERIFIED_EQUIVALENT,
            EquivalenceStatus.ESTIMATED_EQUIVALENT,
        }

    @property
    def is_verified(self) -> bool:
        """True only for structural, Clifford, or bounded numerical evidence."""
        return self.status is EquivalenceStatus.VERIFIED_EQUIVALENT

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["method"] = self.method.value
        value["status"] = self.status.value
        value["passes_threshold"] = self.passes_threshold
        value["accepted"] = self.accepted
        value["is_verified"] = self.is_verified
        return value


_NON_UNITARY_NAMES = frozenset({
    "measure", "reset", "initialize", "if_else", "while_loop", "for_loop",
    "switch_case", "break_loop", "continue_loop", "store",
})
_CLIFFORD_GATES = frozenset({
    "h", "x", "y", "z", "s", "sdg", "cx", "cnot", "cz", "swap", "id",
})


def _unsupported_semantics(circuit: QuantumCircuit) -> list[str]:
    reasons: set[str] = set()
    if circuit.num_clbits:
        reasons.add("classical_bits")
    for instruction in circuit.data:
        operation = instruction.operation
        name = operation.name
        if name in _NON_UNITARY_NAMES:
            reasons.add(name)
        if instruction.clbits:
            reasons.add("classical_operands")
        if getattr(operation, "condition", None) is not None:
            reasons.add("classical_condition")
    return sorted(reasons)


def _unavailable(threshold: float, reason: str, **evidence: Any) -> EquivalenceCertificate:
    return EquivalenceCertificate(
        method=EquivalenceMethod.UNAVAILABLE,
        status=EquivalenceStatus.UNAVAILABLE,
        scope=UNITARY_SCOPE,
        threshold=threshold,
        evidence={"reason": reason, **evidence},
    )


def certify_equivalence(
    circuit: QuantumCircuit,
    target: QuantumCircuit,
    *,
    threshold: float = 0.99,
    max_exact_qubits: int = 12,
    n_samples: int = 1000,
    rng: np.random.RandomState | None = None,
) -> EquivalenceCertificate:
    """Return a fail-closed equivalence certificate.

    This is not a symbolic equivalence engine.  Free parameters, measurements,
    resets, initialization, classical control, and dynamic control flow return
    ``unavailable`` with an explicit blocker.  Global-Haar sampling is labelled
    estimated and includes its Monte Carlo standard error.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must lie in [0, 1]")
    if n_samples <= 0:
        raise ValueError("n_samples must be positive")

    if circuit.num_qubits != target.num_qubits:
        return EquivalenceCertificate(
            method=EquivalenceMethod.EXACT_STRUCTURAL,
            status=EquivalenceStatus.VERIFIED_NOT_EQUIVALENT,
            scope=UNITARY_SCOPE,
            threshold=threshold,
            fidelity=0.0,
            evidence={
                "reason": "qubit_width_mismatch",
                "circuit_qubits": circuit.num_qubits,
                "target_qubits": target.num_qubits,
            },
        )

    blockers = sorted(set(_unsupported_semantics(circuit) + _unsupported_semantics(target)))
    if blockers:
        return _unavailable(threshold, "unsupported_nonunitary_or_dynamic_semantics", blockers=blockers)

    free_parameters = sorted(str(parameter) for parameter in circuit.parameters | target.parameters)
    if free_parameters:
        return _unavailable(
            threshold,
            "free_parameters_require_symbolic_or_probability-qualified_contract",
            free_parameters=free_parameters,
        )

    if circuit == target:
        return EquivalenceCertificate(
            method=EquivalenceMethod.EXACT_STRUCTURAL,
            status=EquivalenceStatus.VERIFIED_EQUIVALENT,
            scope=UNITARY_SCOPE,
            threshold=threshold,
            fidelity=1.0,
            evidence={"reason": "identical_qiskit_circuit"},
        )

    n_qubits = circuit.num_qubits
    if n_qubits > max_exact_qubits:
        if all(inst.operation.name in _CLIFFORD_GATES for inst in circuit.data) and all(
            inst.operation.name in _CLIFFORD_GATES for inst in target.data
        ):
            try:
                equivalent = Clifford(circuit) == Clifford(target)
                return EquivalenceCertificate(
                    method=EquivalenceMethod.EXACT_CLIFFORD,
                    status=(EquivalenceStatus.VERIFIED_EQUIVALENT if equivalent
                            else EquivalenceStatus.VERIFIED_NOT_EQUIVALENT),
                    scope=UNITARY_SCOPE,
                    threshold=threshold,
                    fidelity=1.0 if equivalent else None,
                    evidence={"reason": "tableau_equality", "qubits": n_qubits},
                )
            except Exception as error:
                clifford_error = repr(error)
        else:
            clifford_error = "not_clifford_gate_set"
    else:
        clifford_error = "within_numerical_unitary_budget"

    if n_qubits <= max_exact_qubits:
        try:
            left = np.asarray(Operator(circuit).data)
            right = np.asarray(Operator(target).data)
            dimension = 2 ** n_qubits
            overlap = np.abs(np.vdot(left, right)) ** 2
            fidelity = float((overlap + dimension) / (dimension ** 2 + dimension))
            return EquivalenceCertificate(
                method=EquivalenceMethod.NUMERICAL_UNITARY,
                status=(EquivalenceStatus.VERIFIED_EQUIVALENT if fidelity >= threshold
                        else EquivalenceStatus.VERIFIED_NOT_EQUIVALENT),
                scope=UNITARY_SCOPE,
                threshold=threshold,
                fidelity=min(1.0, max(0.0, fidelity)),
                evidence={"qubits": n_qubits, "dimension": dimension},
            )
        except Exception as error:
            operator_error = repr(error)
    else:
        operator_error = "exact_unitary_budget_exceeded"

    try:
        generator = rng if rng is not None else np.random.RandomState(0)
        dimension = 2 ** n_qubits
        overlaps: list[float] = []
        for _ in range(n_samples):
            vector = generator.normal(size=dimension) + 1j * generator.normal(size=dimension)
            vector /= np.linalg.norm(vector)
            state = Statevector(vector)
            left_state = state.evolve(circuit)
            right_state = state.evolve(target)
            overlaps.append(float(np.abs(np.vdot(left_state.data, right_state.data)) ** 2))
        fidelity = float(np.mean(overlaps))
        standard_error = float(np.std(overlaps, ddof=1) / np.sqrt(n_samples)) if n_samples > 1 else None
        return EquivalenceCertificate(
            method=EquivalenceMethod.SAMPLED_GLOBAL_HAAR,
            status=(EquivalenceStatus.ESTIMATED_EQUIVALENT if fidelity >= threshold
                    else EquivalenceStatus.ESTIMATED_NOT_EQUIVALENT),
            scope=UNITARY_SCOPE,
            threshold=threshold,
            fidelity=min(1.0, max(0.0, fidelity)),
            standard_error=standard_error,
            samples=n_samples,
            evidence={
                "qubits": n_qubits,
                "operator_error": operator_error,
                "clifford_error": clifford_error,
            },
        )
    except Exception as error:
        return _unavailable(
            threshold,
            "all_supported_verifiers_failed",
            operator_error=operator_error,
            clifford_error=clifford_error,
            sampling_error=repr(error),
        )
