"""Semantic and contract tests for the v12 rewrite-exposure certificate."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Gate, Parameter
from qiskit.quantum_info import Operator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.optimisation.rewrite_exposure import (
    CertificateGuidedPreprocessor,
    CertificateStatus,
    DependenceModel,
    ExposureConfig,
    RewriteCandidate,
    _all_pairs_reference_edges,
    _dependency_edges,
    _quotient_is_acyclic,
    _transitive_closure,
    certify_rewrite_exposure,
    materialize_cgl_listing,
)


def _up_to_global_phase(left, right, atol=1e-9):
    left_data = np.asarray(Operator(left).data)
    right_data = np.asarray(Operator(right).data)
    dimension = left_data.shape[0]
    overlap = abs(np.trace(np.conj(left_data).T @ right_data)) / dimension
    return np.isclose(overlap, 1.0, atol=atol)


def _h_pair_circuit():
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.h(1)
    circuit.h(0)
    circuit.h(1)
    return circuit


def test_adjacent_self_inverse_pair_is_exact_and_currently_exposed():
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.h(0)

    certificate = certify_rewrite_exposure(circuit)

    assert certificate.status == CertificateStatus.EXACT.value
    assert certificate.current_exposed_weight == 2
    assert certificate.constructive_lower_bound == 2
    assert certificate.matching_upper_bound == 2
    assert certificate.exact_optimum == 2
    assert certificate.selected_pairs[0]["rule_id"] == "pair_v1.self_inverse"


def test_cgl_exposes_two_disjoint_pairs_and_preserves_unitary():
    circuit = _h_pair_circuit()

    preprocessed, certificate = CertificateGuidedPreprocessor().preprocess(circuit)

    assert certificate.listing_order == [0, 2, 1, 3]
    assert certificate.constructive_lower_bound == 4
    assert certificate.current_exposed_weight == 0
    assert _up_to_global_phase(circuit, preprocessed)
    assert [item.operation.name for item in preprocessed.data] == ["h", "h", "h", "h"]


def test_pairwise_exposure_accepts_a_cover_but_rejects_open_interval():
    cover = QuantumCircuit(1)
    cover.h(0)
    cover.h(0)
    cover_certificate = certify_rewrite_exposure(cover)
    assert cover_certificate.candidate_count == 1
    assert cover_certificate.selected_pairs

    open_interval = QuantumCircuit(1)
    open_interval.h(0)
    open_interval.x(0)
    open_interval.h(0)
    open_certificate = certify_rewrite_exposure(open_interval)
    assert open_certificate.candidate_count == 1
    assert not open_certificate.selected_pairs
    assert open_certificate.status == CertificateStatus.EXACT_ZERO.value


def test_unknown_overlapping_operation_is_a_conservative_dependency_barrier():
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.append(Gate("mystery", 1, []), [0])
    circuit.h(0)

    certificate = certify_rewrite_exposure(
        circuit,
        ExposureConfig(dependence_model=DependenceModel.CONSERVATIVE_COMMUTATION_V1),
    )

    assert certificate.candidate_count == 1
    assert not certificate.selected_pairs
    assert certificate.constructive_lower_bound == 0
    assert certificate.fallback_reason is None


def test_conservative_model_allows_disjoint_reordering():
    certificate = certify_rewrite_exposure(
        _h_pair_circuit(),
        ExposureConfig(dependence_model=DependenceModel.CONSERVATIVE_COMMUTATION_V1),
    )

    assert certificate.dependence_model == DependenceModel.CONSERVATIVE_COMMUTATION_V1.value
    assert certificate.constructive_lower_bound == 4
    assert certificate.status == CertificateStatus.EXACT.value


def test_conservative_model_exposes_an_incomparable_overlapping_free_pair():
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.x(1)
    circuit.h(0)

    certificate = certify_rewrite_exposure(
        circuit,
        ExposureConfig(dependence_model=DependenceModel.CONSERVATIVE_COMMUTATION_V1),
    )

    assert certificate.candidate_count == 1
    assert certificate.constructive_lower_bound == 2
    assert certificate.selected_pairs[0]["pairwise_exposable"] is True


def test_dense_reference_dag_has_same_reachability_as_production_dag():
    circuit = _h_pair_circuit()
    for model in DependenceModel:
        production, _, _, _ = _dependency_edges(circuit, model, 100)
        reference = _all_pairs_reference_edges(circuit, model)
        production_desc, _ = _transitive_closure(production)
        reference_desc, _ = _transitive_closure(reference)
        assert production_desc == reference_desc


def test_barrier_is_a_fence_even_for_a_same_wire_pair():
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.barrier(0)
    circuit.h(0)

    certificate = certify_rewrite_exposure(circuit)

    assert certificate.candidate_count == 1
    assert not certificate.selected_pairs
    assert certificate.status == CertificateStatus.EXACT_ZERO.value


def test_operand_order_is_part_of_pair_identity():
    circuit = QuantumCircuit(2)
    circuit.cx(0, 1)
    circuit.cx(1, 0)

    certificate = certify_rewrite_exposure(circuit)

    assert certificate.candidate_count == 0
    assert certificate.constructive_lower_bound == 0


@pytest.mark.parametrize(
    ("builder", "expected_rule", "expected_weight"),
    [
        (lambda c: (c.t(0), c.tdg(0)), "pair_v1.t_tdg", 2),
        (lambda c: (c.s(0), c.sdg(0)), "pair_v1.s_sdg", 2),
        (lambda c: (c.rz(0.5, 0), c.rz(-0.5, 0)), "pair_v1.rotation_zero", 2),
        (lambda c: (c.rx(0.5, 0), c.rx(0.25, 0)), "pair_v1.rotation_merge", 1),
        (lambda c: (c.ry(np.pi, 0), c.ry(np.pi, 0)), "pair_v1.rotation_zero", 2),
    ],
)
def test_pair_rule_library_and_weights(builder, expected_rule, expected_weight):
    circuit = QuantumCircuit(1)
    builder(circuit)

    certificate = certify_rewrite_exposure(circuit)

    assert certificate.selected_pairs[0]["rule_id"] == expected_rule
    assert certificate.constructive_lower_bound == expected_weight


def test_current_exposure_counts_supported_adjacent_rules_only():
    circuit = QuantumCircuit(1)
    circuit.rz(0.2, 0)
    circuit.rz(0.1, 0)
    circuit.x(0)

    certificate = certify_rewrite_exposure(circuit)

    assert certificate.current_exposed_weight == 1
    assert certificate.selected_pairs[0]["rule_id"] == "pair_v1.rotation_merge"


def test_current_exposure_uses_endpoint_disjoint_matching_not_adjacent_edge_sum():
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.h(0)
    circuit.h(0)

    certificate = certify_rewrite_exposure(circuit)

    assert certificate.current_exposed_weight == 2


def test_matching_upper_bound_is_safe_and_exact_for_small_instance():
    circuit = _h_pair_circuit()
    certificate = certify_rewrite_exposure(circuit)

    assert certificate.constructive_lower_bound <= certificate.matching_upper_bound
    assert certificate.exact_optimum == certificate.constructive_lower_bound
    assert certificate.constructive_lower_bound == certificate.matching_upper_bound


def test_quotient_cycle_rejects_jointly_incompatible_individually_exposable_pairs():
    # 0 -> 2 and 1 -> 3 make pairs (0, 3) and (1, 2) individually
    # incomparable, but contracting both creates a two-block cycle.
    edges = [{2}, {3}, set(), set()]
    candidates = [
        RewriteCandidate(0, 3, "pair_v1.self_inverse", 2, True),
        RewriteCandidate(1, 2, "pair_v1.self_inverse", 2, True),
    ]

    assert not _quotient_is_acyclic(4, edges, candidates)
    assert _quotient_is_acyclic(4, edges, candidates[:1])


def test_candidate_cap_is_fail_closed_and_reports_discarded_weight_domain():
    circuit = QuantumCircuit(1)
    for _ in range(8):
        circuit.h(0)

    certificate = certify_rewrite_exposure(
        circuit,
        ExposureConfig(candidate_cap=2),
    )

    assert certificate.status == CertificateStatus.TRUNCATED.value
    assert certificate.candidate_count == 28
    assert certificate.discarded_candidate_count == 5
    assert certificate.constructive_lower_bound <= certificate.matching_upper_bound


def test_exact_node_budget_exhaustion_is_bounded_and_not_exact():
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.h(0)

    certificate = certify_rewrite_exposure(
        circuit,
        ExposureConfig(exact_node_budget=1),
    )

    assert certificate.status == CertificateStatus.BOUNDED.value
    assert certificate.exact_optimum is None
    assert certificate.constructive_lower_bound <= certificate.matching_upper_bound


def test_conservative_overlap_budget_falls_back_to_wire_model_with_reason():
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.x(0)
    circuit.h(0)

    certificate = certify_rewrite_exposure(
        circuit,
        ExposureConfig(
            dependence_model=DependenceModel.CONSERVATIVE_COMMUTATION_V1,
            overlap_check_budget=1,
        ),
    )

    assert certificate.dependence_model == DependenceModel.WIRE_ORDER_V1.value
    assert certificate.fallback_reason.startswith(
        "conservative_overlap_check_budget_predicted:1:"
    )


@pytest.mark.parametrize("operation", ["measure", "reset"])
def test_nonunitary_instructions_are_unavailable(operation):
    circuit = QuantumCircuit(1, 1)
    if operation == "measure":
        circuit.measure(0, 0)
    else:
        circuit.reset(0)

    certificate = certify_rewrite_exposure(circuit)

    assert certificate.status == CertificateStatus.UNAVAILABLE.value
    assert certificate.failure_reason is not None


def test_classical_operands_are_unavailable():
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)
    circuit.measure(0, 0)

    certificate = certify_rewrite_exposure(circuit)

    assert certificate.status == CertificateStatus.UNAVAILABLE.value
    assert "nonunitary" in certificate.failure_reason


def test_free_parameters_are_unavailable():
    circuit = QuantumCircuit(1)
    circuit.rz(Parameter("theta"), 0)

    certificate = certify_rewrite_exposure(circuit)

    assert certificate.status == CertificateStatus.UNAVAILABLE.value
    assert certificate.failure_reason == "free_parameters_are_out_of_scope"


def test_invalid_configuration_is_unavailable_not_silently_defaulted():
    circuit = QuantumCircuit(1)
    circuit.h(0)

    certificate = certify_rewrite_exposure(circuit, {"beam_width": 0})

    assert certificate.status == CertificateStatus.UNAVAILABLE.value
    assert certificate.failure_reason.startswith("invalid_config:")


def test_input_and_certificate_are_deterministic_and_input_is_unchanged():
    circuit = _h_pair_circuit()
    before = circuit.copy()
    first = certify_rewrite_exposure(circuit)
    second = certify_rewrite_exposure(circuit)

    assert first.to_dict() == second.to_dict()
    assert first.input_sha256 == second.input_sha256
    assert first.listing_sha256 == hashlib.sha256(
        json.dumps(first.listing_order, separators=(",", ":")).encode()
    ).hexdigest()
    assert circuit == before


def test_materialized_listing_requires_a_permutation():
    circuit = QuantumCircuit(1)
    circuit.h(0)

    with pytest.raises(ValueError, match="permutation"):
        materialize_cgl_listing(circuit, [0, 0])


def test_preprocessor_returns_copy_for_unavailable_circuit():
    circuit = QuantumCircuit(1)
    circuit.measure_all()

    output, certificate = CertificateGuidedPreprocessor().preprocess(circuit)

    assert certificate.status == CertificateStatus.UNAVAILABLE.value
    assert output is not circuit
    assert output == circuit


def test_certificate_json_contains_source_hashes_and_listing_hash():
    circuit = QuantumCircuit(1)
    circuit.h(0)
    circuit.h(0)

    certificate = certify_rewrite_exposure(circuit)
    payload = certificate.to_json()

    assert "rewrite_exposure.py" in payload
    assert "listing_sha256" in payload
    assert len(certificate.input_sha256) == 64


def test_empty_unitary_circuit_has_exact_zero_certificate():
    certificate = certify_rewrite_exposure(QuantumCircuit(2))

    assert certificate.status == CertificateStatus.EXACT_ZERO.value
    assert certificate.exact_optimum == 0
    assert certificate.listing_order == []


def test_non_circuit_input_is_unavailable():
    certificate = certify_rewrite_exposure("not a circuit")

    assert certificate.status == CertificateStatus.UNAVAILABLE.value
    assert certificate.failure_reason == "input_is_not_qiskit_quantum_circuit"
