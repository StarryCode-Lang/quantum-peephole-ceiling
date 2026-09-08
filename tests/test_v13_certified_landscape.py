"""Small executable contracts for the v13 landscape core."""

import json
import hashlib
from pathlib import Path

from src.optimisation.certified_landscape import (
    STATUS_EXACT_LOCAL,
    STATUS_RESOURCE_NO_WITNESS,
    _canonical_bytes,
    iter_legal_actions,
    legal_actions,
    replay_actions,
    search_escape_idastar,
    search_landscape,
    search_landscape_horizons,
    search_landscape_horizons_compact,
    state_from_spec,
)


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"


def _neutral_case():
    return state_from_spec({"num_qubits": 2, "operations": [
        {"name": "h", "qubits": [0]}, {"name": "x", "qubits": [1]},
        {"name": "h", "qubits": [0]}, {"name": "x", "qubits": [1]},
    ]})


def test_listing_order_and_angle_are_state_key_material():
    state = _neutral_case()
    reversed_state = state_from_spec({"num_qubits": 2, "operations": list(reversed([
        {"name": "h", "qubits": [0]}, {"name": "x", "qubits": [1]},
        {"name": "h", "qubits": [0]}, {"name": "x", "qubits": [1]},
    ]))})
    assert state.state_hash != reversed_state.state_hash


def test_spliced_child_hash_matches_the_contract_bytes():
    state = _neutral_case()
    for action in legal_actions(state, RULES, "e44_core_v1"):
        expected = hashlib.sha256(_canonical_bytes(action.post_state.to_dict())).hexdigest()
        assert action.post_state_sha256 == expected
        assert action.post_state.state_hash == expected


def test_indexed_action_iterator_matches_contract_action_order():
    state = _neutral_case()
    expected = legal_actions(state, RULES, "e44_core_v1")
    actual = list(iter_legal_actions(state, RULES, "e44_core_v1"))
    assert [action.to_dict() for action in actual] == [action.to_dict() for action in expected]


def test_exact_horizons_are_monotone_and_witness_replays():
    certificates = search_landscape_horizons(state_from_spec({"num_qubits": 2, "operations": [
        {"name": "h", "qubits": [0]}, {"name": "x", "qubits": [1]},
        {"name": "h", "qubits": [0]}, {"name": "x", "qubits": [1]},
    ]}), RULES, range(5), rule_scope="e44_core_v1")
    costs = [certificates[str(horizon)]["best_cost"] for horizon in range(5)]
    assert costs == sorted(costs, reverse=True)
    final = certificates["4"]
    assert replay_actions(_neutral_case(), final["witnesses"]["escape"], RULES, "e44_core_v1")["accepted"]


def test_bounded_search_cannot_claim_exact_local_optimum():
    certificate = search_landscape(_neutral_case(), RULES, 4, state_budget=1, rule_scope="e44_core_v1")
    assert certificate["status"] == STATUS_RESOURCE_NO_WITNESS
    assert certificate["status"] != STATUS_EXACT_LOCAL


def test_compact_exact_search_matches_bfs_metrics_and_replays_witnesses():
    state = _neutral_case()
    reference = search_landscape_horizons(state, RULES, range(5), rule_scope="e44_core_v1")
    compact = search_landscape_horizons_compact(state, RULES, range(5), rule_scope="e44_core_v1")
    for horizon in range(5):
        expected = reference[str(horizon)]
        actual = compact[str(horizon)]
        assert {
            key: actual[key]
            for key in ("status", "best_cost", "escape_depth", "barrier_height", "states_seen", "state_set_sha256", "state_hashes")
        } == {
            key: expected[key]
            for key in ("status", "best_cost", "escape_depth", "barrier_height", "states_seen", "state_set_sha256", "state_hashes")
        }
        assert replay_actions(state, actual["witnesses"]["barrier"], RULES, "e44_core_v1")["accepted"]


def test_compact_certificate_serialization_is_byte_stable():
    state = _neutral_case()
    first = search_landscape_horizons_compact(state, RULES, (4,), rule_scope="e44_core_v1")["4"]
    second = search_landscape_horizons_compact(state, RULES, (4,), rule_scope="e44_core_v1")["4"]
    first_json = json.dumps(first, indent=2, sort_keys=True) + "\n"
    second_json = json.dumps(second, indent=2, sort_keys=True) + "\n"
    assert first_json == second_json


def test_compact_exact_search_time_budget_is_fail_closed():
    certificate = search_landscape_horizons_compact(
        _neutral_case(), RULES, (4,), rule_scope="e44_core_v1", time_budget_seconds=0.0
    )["4"]
    assert certificate["status"] == STATUS_RESOURCE_NO_WITNESS
    assert certificate["resource_status"] == "TRUNCATED"
    assert certificate["exactness_status"] == "INCOMPLETE"
    assert certificate["resource_reason"] == "time_budget"


def test_idastar_escape_depth_matches_exact_bfs_and_replays():
    state = _neutral_case()
    bfs = search_landscape_horizons(state, RULES, (4,), rule_scope="e44_core_v1")["4"]
    ida = search_escape_idastar(state, RULES, 4, rule_scope="e44_core_v1")
    assert ida["status"] == "EXACT_ESCAPE"
    assert ida["escape_depth"] == bfs["escape_depth"]
    assert ida["exactness_status"] == "EXACT_FINITE_HORIZON"
    assert ida["admissible_max_single_step_reduction"] >= 1
    assert replay_actions(state, ida["witnesses"]["escape"], RULES, "e44_core_v1")["accepted"]


def test_idastar_time_budget_is_fail_closed():
    certificate = search_escape_idastar(
        _neutral_case(), RULES, 4, rule_scope="e44_core_v1", time_budget_seconds=0.0
    )
    assert certificate["status"] == STATUS_RESOURCE_NO_WITNESS
    assert certificate["resource_status"] == "TRUNCATED"
    assert certificate["exactness_status"] == "INCOMPLETE"
    assert certificate["resource_reason"] == "time_budget"


def test_e44_receipt_is_zero_tolerance():
    receipt = json.loads((ROOT / "docs" / "review" / "v13_stage4_e44_receipt.json").read_text(encoding="utf-8"))
    assert receipt["zero_tolerance"] is True
    assert receipt["cells"] == 5120
    assert receipt["classification_mismatches"] == 0
