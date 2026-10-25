"""Small executable contracts for the v13 landscape core."""

import json
import hashlib
import math
import random
import time
from pathlib import Path

from src.optimisation.certified_landscape import (
    STATUS_EXACT_LOCAL,
    STATUS_RESOURCE_NO_WITNESS,
    _canonical_bytes,
    _quartz_index,
    admissible_remaining_cost_lower_bound,
    filter_rule_scope,
    iter_legal_actions,
    legal_actions,
    replay_actions,
    search_escape_idastar,
    search_landscape,
    search_landscape_horizons,
    search_landscape_horizons_compact,
    semantically_equivalent,
    state_from_spec,
    state_wcl,
)
from src.provenance import DEFAULT_SOURCE_FILES, ENGINE_SOURCE_FILES, engine_source_hashes


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


def _multi_location_case():
    """Signature (cx, rz) matches at locations 0 and 2 for rule quartz_v1:9_2."""
    return state_from_spec({"num_qubits": 2, "operations": [
        {"name": "cx", "qubits": [0, 1]}, {"name": "rz", "qubits": [1], "params": [0.5]},
        {"name": "cx", "qubits": [0, 1]}, {"name": "rz", "qubits": [1], "params": [0.5]},
    ]})


def test_iter_legal_actions_accumulates_every_signature_location():
    """Regression: one Quartz rule matching at several locations must keep all matches.

    The audit defect overwrote ``local_actions`` per location inside
    ``iter_legal_actions``, so only the last location of a shared signature
    survived (legal_actions: 5, iter_legal_actions: 4 on this state).
    """
    state = _multi_location_case()
    expected = legal_actions(state, RULES, "e44_core_v1")
    actual = list(iter_legal_actions(state, RULES, "e44_core_v1"))
    assert sorted(actual, key=lambda action: action.sort_key) == sorted(expected, key=lambda action: action.sort_key)
    # The audited rule must appear at every matching location, not just the last.
    audited = [action.location for action in actual if action.rule_id.startswith("quartz_v1:9_2:")]
    assert audited == [0, 2]
    assert len(actual) == len(expected) == 5


_MOTIFS = (
    ({"name": "cx", "qubits": [0, 1]},),
    ({"name": "cx", "qubits": [0, 1]}, {"name": "rz", "qubits": [1]}),
    ({"name": "h", "qubits": [0]},),
    ({"name": "x", "qubits": [1]},),
    ({"name": "rz", "qubits": [0]},),
    ({"name": "h", "qubits": [0]}, {"name": "cx", "qubits": [1, 0]}),
    ({"name": "rz", "qubits": [1]}, {"name": "rz", "qubits": [1]}),
    ({"name": "cx", "qubits": [1, 0]}, {"name": "rz", "qubits": [0]}),
)
_MOTIF_ANGLES = (0.0, 0.5, -1.25, 2.0, 3.14159)


def _random_repeat_pattern_listing(rng: random.Random) -> dict:
    """Random listing built from a small motif pool so signatures repeat."""
    operations = []
    for _ in range(rng.randint(1, 10)):  # motif count keeps the listing within ~40 gates
        motif = rng.choice(_MOTIFS)
        angle = rng.choice(_MOTIF_ANGLES)
        for operation in motif:
            entry = {"name": operation["name"], "qubits": list(operation["qubits"])}
            if operation["name"] == "rz":
                entry["params"] = [angle]
            operations.append(entry)
    return {"num_qubits": 2, "operations": operations}


def test_iter_legal_actions_matches_legal_actions_on_repeat_pattern_listings():
    """Property: streamed actions equal contract actions as multisets of sort keys."""
    rng = random.Random(20261025)
    multi_location_trials = 0
    started = time.perf_counter()
    for _ in range(60):
        state = state_from_spec(_random_repeat_pattern_listing(rng))
        expected = legal_actions(state, RULES, "e44_core_v1")
        actual = list(iter_legal_actions(state, RULES, "e44_core_v1"))
        assert sorted(action.sort_key for action in actual) == sorted(action.sort_key for action in expected)
        by_rule_locations = {}
        for action in actual:
            if action.family == "quartz_v1":
                by_rule_locations.setdefault(action.rule_id, set()).add(action.location)
        if any(len(locations) > 1 for locations in by_rule_locations.values()):
            multi_location_trials += 1
    elapsed = time.perf_counter() - started
    assert multi_location_trials >= 1, "property sweep must exercise shared signatures"
    assert elapsed < 60.0


def test_engine_source_hashes_pins_certification_engine_without_legacy_gates():
    """New receipts can pin the engine identity; legacy DEFAULT_SOURCE_FILES stay untouched."""
    hashes = engine_source_hashes(ROOT)
    assert set(hashes) == set(ENGINE_SOURCE_FILES)
    for relative, digest in hashes.items():
        assert len(digest) == 64 and int(digest, 16) >= 0
        assert digest == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    # The legacy provenance list predates the v13 chain and must stay unchanged
    # so existing verify gates keep their exact green output.
    assert not (set(DEFAULT_SOURCE_FILES) & set(ENGINE_SOURCE_FILES))


_ORACLE_INPUTS = ROOT / "data" / "v13" / "e44_certified_landscape_oracle" / "inputs.jsonl"
_ORACLE_CERTIFICATES = ROOT / "data" / "v13" / "e44_certified_landscape_oracle" / "certificates.jsonl"


def test_admissible_bound_never_exceeds_the_e44_oracle_optimum():
    """Admissibility over the frozen oracle: bound <= true reachable optimum.

    For every oracle instance and every frozen horizon H, the certified bound
    with budget H from the root listing must not exceed the best cost the
    complete engine certified as reachable within H actions, and it must be
    non-increasing in the budget.
    """
    best = {}
    with _ORACLE_CERTIFICATES.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            best[(row["case_id"], int(row["horizon"]))] = row["formal_certificate"]["best_cost"]
    checked = 0
    with _ORACLE_INPUTS.open(encoding="utf-8") as handle:
        for line in handle:
            case = json.loads(line)
            state = state_from_spec(case)
            previous = None
            for horizon in range(5):
                bound = admissible_remaining_cost_lower_bound(
                    state, state.cost - 1, horizon,
                    rule_library_path=RULES, rule_scope="e44_core_v1",
                )
                assert bound <= best[(case["case_id"], horizon)]
                if previous is not None:
                    assert bound <= previous
                previous = bound
                checked += 1
    assert checked == 5120


def test_idastar_per_gate_bound_preserves_exact_bfs_verdicts():
    """The enhanced lower bound never changes a certified escape verdict."""
    rng = random.Random(20261025)
    cases = [_multi_location_case()]
    cases.extend(state_from_spec(_random_repeat_pattern_listing(rng)) for _ in range(4))
    for state in cases:
        bfs = search_landscape_horizons(state, RULES, (4,), rule_scope="e44_core_v1")["4"]
        ida = search_escape_idastar(state, RULES, 4, rule_scope="e44_core_v1")
        assert ida["status"] == bfs["status"]
        assert ida["escape_depth"] == bfs["escape_depth"]
        assert ida["exactness_status"] == "EXACT_FINITE_HORIZON"
        if ida["escape_depth"] is not None:
            assert replay_actions(state, ida["witnesses"]["escape"], RULES, "e44_core_v1")["accepted"]


def test_state_wcl_is_deterministic_cost_and_multiset_invariant():
    """WCL reordering is a pure, byte-stable, semantics-preserving permutation."""
    rng = random.Random(20261025)
    reordered_trials = 0
    for _ in range(24):
        spec = _random_repeat_pattern_listing(rng)
        state = state_from_spec(spec)
        result = state_wcl(state)
        assert result.num_qubits == state.num_qubits
        assert result.cost == state.cost
        assert sorted(gate._canonical_bytes for gate in result.gates) == sorted(
            gate._canonical_bytes for gate in state.gates
        )
        # Byte stability: an independent rebuild reorders to the same listing.
        again = state_wcl(state_from_spec(spec))
        assert again._canonical_state_bytes == result._canonical_state_bytes
        assert semantically_equivalent(result, state)
        if result.key != state.key:
            reordered_trials += 1
    assert reordered_trials >= 1, "property sweep must exercise actual reordering"


def test_state_wcl_matches_the_qiskit_wire_traversal_preprocessor():
    """The engine converter mirrors the reference preprocessor's exact order."""
    try:
        from qiskit import QuantumCircuit
        from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor
    except ImportError:
        return
    rng = random.Random(20261025)
    for _ in range(12):
        spec = _random_repeat_pattern_listing(rng)
        circuit = QuantumCircuit(spec["num_qubits"])
        for operation in spec["operations"]:
            if operation["name"] == "rz":
                circuit.rz(operation["params"][0], operation["qubits"][0])
            else:
                getattr(circuit, operation["name"])(*operation["qubits"])
        expected = WireTraversalPreprocessor().preprocess(circuit)
        expected_order = [
            (
                instance.operation.name,
                tuple(circuit.find_bit(qubit).index for qubit in instance.qubits),
                float(instance.operation.params[0]) if instance.operation.params else None,
            )
            for instance in expected.data
        ]
        actual = state_wcl(state_from_spec(spec))
        actual_order = [(gate.name, tuple(gate.qubits), gate.angle) for gate in actual.gates]
        assert len(expected_order) == len(actual_order)
        for (ename, equbits, eangle), (aname, aquibits, aangle) in zip(expected_order, actual_order):
            assert ename == aname and equbits == aquibits
            assert (eangle is None) == (aangle is None)
            if eangle is not None:
                assert math.isclose(eangle, aangle, abs_tol=1e-12)


def test_filter_rule_scope_reproduces_the_pinned_e44_core_predicate():
    """One scope authority: the helper must equal the historical inline filter.

    The predicate was triplicated across ``_quartz_index``,
    ``_maximum_single_step_reduction`` and
    ``scripts/derive_v15_certified_lower_bounds.py``; this test pins the
    extracted helper to the original e44_core_v1 membership and order on the
    frozen generation_a rule library.
    """
    library = json.loads(RULES.read_text(encoding="utf-8"))
    quartz = [rule for rule in library["rules"] if rule.get("rule_family") == "quartz_v1"]
    expected_ids = [
        rule["rule_id"] for rule in quartz
        if int(rule["source"]["num_qubits"]) <= 2
        and len(rule["source"]["operations"]) <= 4
        and len(rule["target"]["operations"]) <= 6
    ]
    filtered = filter_rule_scope(quartz, "e44_core_v1")
    assert [rule["rule_id"] for rule in filtered] == expected_ids
    assert len(expected_ids) == 149
    # ``full`` keeps every Quartz rule, unchanged and in input order.
    assert filter_rule_scope(quartz, "full") == quartz
    # The engine signature index built through the helper carries exactly the
    # same rule ids.
    index_ids = sorted(rule["rule_id"] for rules in _quartz_index(RULES, "e44_core_v1").values() for rule in rules)
    assert index_ids == sorted(expected_ids)
    try:
        filter_rule_scope(quartz, "unknown_scope")
    except ValueError as exc:
        assert "unknown_rule_scope:unknown_scope" in str(exc)
    else:
        raise AssertionError("unknown scope must be rejected")
