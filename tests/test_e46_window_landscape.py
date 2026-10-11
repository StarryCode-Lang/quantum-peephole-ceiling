"""Executable contracts for the E46 window-local certified landscape."""

import json
import subprocess
import sys
from pathlib import Path

from src.optimisation.certified_landscape import (
    LandscapeState,
    StateGate,
    search_landscape_horizons_compact,
)

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"


def _listing_with_crossing_pair():
    """A listing with two x gates on qubit 0 separated by an s gate on qubit 1.

    The two x gates are not adjacent, so no reducing action applies directly;
    one structural exchange makes them adjacent and the pair cancels.
    """

    operations = [
        {"name": "x", "qubits": [0]},
        {"name": "s", "qubits": [1]},
        {"name": "x", "qubits": [0]},
    ]
    return LandscapeState(
        2,
        tuple(
            StateGate(
                operation["name"],
                tuple(operation["qubits"]),
                None,
            )
            for operation in operations
        ),
    ).normalized()


def test_window_slice_preserves_listing_semantics():
    from experiments.e46_window_landscape.run import window_state, window_starts

    state = _listing_with_crossing_pair()
    assert window_starts(len(state.gates), 2) == [0, 1]
    assert window_starts(1, 2) == []
    window = window_state(state, 0, 2)
    assert len(window.gates) == 2
    assert window.gates == state.gates[0:2]


def test_window_search_finds_hidden_exchange_escape():
    from experiments.e46_window_landscape.run import window_state

    state = _listing_with_crossing_pair()
    window = window_state(state, 0, 3)
    certificate = search_landscape_horizons_compact(
        window,
        RULES,
        (3,),
        state_budget=20_000,
        rule_scope="e44_core_v1",
        time_budget_seconds=10.0,
    )["3"]
    assert certificate["status"] == "EXACT_ESCAPE"
    assert certificate["escape_depth"] == 2
    witness = certificate["witnesses"]["escape"]
    from src.optimisation.certified_landscape import replay_actions

    assert replay_actions(window, witness, RULES, "e44_core_v1")["accepted"]


def test_e46_package_receipt_is_consistent():
    package = ROOT / "data" / "v15" / "e46_window_landscape" / "receipt.json"
    if not package.exists():
        import pytest

        pytest.skip("E46 full panel not yet generated")
    receipt = json.loads(package.read_text(encoding="utf-8"))
    assert receipt["status"] in {"PANEL_COMPLETE", "PANEL_COMPLETE_WITH_RESOURCE_BOUNDARY"}
    assert receipt["source_count"] == 128
    for aggregate in receipt["by_config"].values():
        assert (
            aggregate["escape_count"] + aggregate["local_optimum_count"]
            <= aggregate["window_count"]
        )


def test_e46_verifier_passes():
    if not (ROOT / "data" / "v15" / "e46_window_landscape" / "receipt.json").exists():
        import pytest

        pytest.skip("E46 full panel not yet generated")
    completed = subprocess.run(
        [sys.executable, "scripts/verify_e46_window_landscape.py", "--skip-search"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    verdict = json.loads(completed.stdout.strip().splitlines()[-1])
    assert verdict["status"] == "PASS"
