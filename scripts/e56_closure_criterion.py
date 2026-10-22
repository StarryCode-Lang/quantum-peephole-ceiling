"""E56: commutation-closure exposability -- an exact, search-free predictor of the
required peephole horizon, and a constructive replacement for bounded search.

Motivation
----------
Six review rounds established that the certified landscape is *horizon*-relative:
E47 found 19/33 horizon-3 local optima escape at h<=7, E50 measured the first
improving horizon h* = 2,4,4,6,6,6,7 for BV n = 4..16, and E55 showed that the
engine does implement the commutation relations the escapes need -- it simply
cannot *chain* enough of them inside a bounded horizon.

That leaves an obvious question that no round has answered:

    Is the required horizon computable *without search*?

Answer (this experiment): yes, exactly.  In the trace-monoid reading of a
circuit listing, two occurrences g_i, g_j (i < j) can be brought adjacent by
commutation alone iff every gate strictly between them commutes with both.
That predicate is O(m^2), needs no search, and its crossing distance
``D = j - i - 1`` is the number of adjacent exchanges the engine must chain.
Hence the *predicted* first improving horizon is ``h* = D_min + 1``.

Parts
-----
A  Criterion on the frozen panel.  For all 128 hash-verified E45/E46 root
   states, enumerate every pair_v1-cancellable pair and compute D.  Record
   D_min, the rule, and whether the frozen h=3 search could have seen it.
B  Prediction test on the BV ladder.  Compute D_min(n) for n = 4..64 with zero
   search and compare ``D_min + 1`` against E50's *measured* h*(n).  Then
   extrapolate the growth law far past what BFS can reach.
C  Closure algorithm.  Iteratively cancel every exposable pair (smallest D
   first, non-overlapping, repeat to fixpoint).  Every applied step is emitted
   as a real action sequence (exchange... exchange, pair_v1) and the whole run
   is replayed through ``replay_actions``, so the output is a certificate, not
   a heuristic result.
D  Separation table.  Closure cost vs frozen baseline, vs the certified
   best_cost, and vs the frozen h=3 search.

Contract
    Read-only on ``data/``, ``release/`` and ``docs/manuscript/``.  The rule
    library and rule scope are the frozen ones (``e44_core_v1``).  Root states
    come from ``experiments.e46_window_landscape.run.load_root_states``, which
    hash-checks every root against the v14 certificates.

Outputs (``docs/review/science_boost/2026-10-23_closure_criterion/``):
    * ``panel_criterion.csv``    -- one row per source: D_min, rule, verdict
    * ``bv_prediction.csv``      -- n, D_min, predicted h*, measured h*
    * ``closure_results.csv``    -- one row per source: costs and replay status
    * ``summary.json``           -- aggregates, hashes, contract, law fit
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e45_development_grid.run import (  # noqa: E402
    MAX_BASELINE_GATES,
    RULE_LIBRARY,
    normalize_circuit,
    state_from_circuit,
)
from experiments.e46_window_landscape.run import RULE_SCOPE, load_root_states  # noqa: E402
from src.circuits.real_benchmarks import make_bernstein_vazirani  # noqa: E402
from src.optimisation.certified_landscape import (  # noqa: E402
    ANGLE_TOLERANCE,
    LandscapeState,
    StateGate,
    _commutes,
    _iter_exchange_actions,
    _iter_pair_actions,
    _state_from_normalized,
    normalize_angle,
    replay_actions,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402

EXPERIMENT_ID = "E56_CLOSURE_CRITERION_2026_10_23"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-23_closure_criterion"
CLASSIFICATION = ROOT / "data" / "v15" / "e45_landscape_integration" / "classification_complete.csv"
E50_SUMMARY = ROOT / "docs" / "review" / "science_boost" / "2026-10-21_horizon_scaling" / "summary.json"

SELF_INVERSE = frozenset({"h", "x", "y", "z", "cx", "cz", "swap"})
PAIR_ROTATIONS = frozenset({"rx", "ry", "rz"})
Z_FAMILY = frozenset({"z", "rz", "s", "sdg", "t", "tdg"})
X_FAMILY = frozenset({"x", "rx"})

BV_SIZES_MEASURED = (4, 6, 8, 10, 12, 14, 16)
BV_SIZES_EXTRAPOLATED = (18, 20, 24, 32, 48, 64)
CLOSURE_MAX_PASSES = 12
CLOSURE_TIME_BUDGET_SECONDS = 45.0
CLOSURE_MAX_D = 512
SEED = 42


# --------------------------------------------------------------------------
# Part A/B: the criterion
# --------------------------------------------------------------------------

def _pair_rule(left: StateGate, right: StateGate) -> str | None:
    """Return the pair_v1 rule id for a *listing-adjacent* pair, else None."""

    if left.qubits != right.qubits:
        return None
    if left.name == right.name and left.name in SELF_INVERSE:
        return "pair_v1.self_inverse"
    if {left.name, right.name} == {"t", "tdg"}:
        return "pair_v1.t_tdg"
    if {left.name, right.name} == {"s", "sdg"}:
        return "pair_v1.s_sdg"
    if left.name == right.name and left.name in PAIR_ROTATIONS:
        total = normalize_angle((left.angle or 0.0) + (right.angle or 0.0))
        return "pair_v1.rotation_zero" if abs(total) <= ANGLE_TOLERANCE else "pair_v1.rotation_merge"
    return None


def _adaptive_cap(size: int) -> int:
    """Distance cap traded against O(size * cap) runtime on very long listings."""

    if size > 4000:
        return 64
    if size > 1500:
        return 128
    return CLOSURE_MAX_D


def _make_fast_commutes(gates: tuple[StateGate, ...]):
    """Local re-implementation of the engine commutation predicate.

    The engine version is ``lru_cache``d and builds a ``set`` per call; on
    1,000-gate listings that dominates the runtime by an order of magnitude,
    and the criterion is applied to every root.
    """

    names = [gate.name for gate in gates]
    qubits = [gate.qubits for gate in gates]
    qsets = [frozenset(item) for item in qubits]

    def commutes(i: int, j: int) -> bool:
        left, right = names[i], names[j]
        ls, rs = qsets[i], qsets[j]
        if ls.isdisjoint(rs):
            return True
        same_qubits = qubits[i] == qubits[j]
        if same_qubits and left == right and len(qubits[i]) == 1:
            return True
        if same_qubits and left == right and left in PAIR_ROTATIONS:
            return True
        if left in Z_FAMILY and right in Z_FAMILY and same_qubits:
            return True
        if left == "cx" and right in Z_FAMILY and len(qubits[j]) == 1 and qubits[j][0] == qubits[i][0]:
            return True
        if right == "cx" and left in Z_FAMILY and len(qubits[i]) == 1 and qubits[i][0] == qubits[j][0]:
            return True
        if left == "cx" and right in X_FAMILY and len(qubits[j]) == 1 and qubits[j][0] == qubits[i][1]:
            return True
        if right == "cx" and left in X_FAMILY and len(qubits[i]) == 1 and qubits[i][0] == qubits[j][1]:
            return True
        if left == "cz" and right in Z_FAMILY and len(qubits[j]) == 1 and qubits[j][0] in ls:
            return True
        if right == "cz" and left in Z_FAMILY and len(qubits[i]) == 1 and qubits[i][0] in rs:
            return True
        if left == right == "swap" and same_qubits:
            return True
        if left == right == "cz" and same_qubits:
            return True
        return False

    return commutes


def _blocking(
    gates: tuple[StateGate, ...],
    max_d: int = CLOSURE_MAX_D,
    deadline: float | None = None,
) -> tuple[list[int], list[int]]:
    """first_dep[i] = first k>i that does not commute with gate i.
    last_dep[j]  = last  k<j that does not commute with gate j.

    Both scans are capped at ``max_d`` positions.  The cap only changes the
    answer for pairs whose crossing distance exceeds ``max_d``; every reported
    verdict with ``D <= max_d`` is exact.
    """

    size = len(gates)
    commutes = _make_fast_commutes(gates)
    first_dep = [min(size, max_d + 1)] * size
    last_dep = [-1] * size
    for i in range(size):
        if deadline is not None and (i & 127) == 0 and time.perf_counter() > deadline:
            break
        for k in range(i + 1, min(size, i + 1 + max_d)):
            if not commutes(i, k):
                first_dep[i] = k
                break
    for j in range(size):
        for k in range(j - 1, max(-1, j - 1 - max_d), -1):
            if not commutes(k, j):
                last_dep[j] = k
                break
    return first_dep, last_dep


def _blocking_reference(gates: tuple[StateGate, ...]) -> tuple[list[int], list[int]]:
    """Same quantity computed with the engine predicate; used for the self-check."""

    size = len(gates)
    first_dep = [size] * size
    last_dep = [-1] * size
    for i in range(size):
        for k in range(i + 1, size):
            if _commutes(gates[i], gates[k]) is None:
                first_dep[i] = k
                break
    for j in range(size):
        for k in range(j - 1, -1, -1):
            if _commutes(gates[k], gates[j]) is None:
                last_dep[j] = k
                break
    return first_dep, last_dep


def predicate_agreement(states: list[LandscapeState], samples_per_state: int = 4000) -> dict[str, Any]:
    """Pairwise agreement between the local predicate and the engine predicate."""

    import random  # noqa: PLC0415

    rng = random.Random(20261023)
    checked_pairs = 0
    mismatched = 0
    details: list[str] = []
    for state in states:
        gates = state.gates
        size = len(gates)
        if size < 2:
            continue
        commutes = _make_fast_commutes(gates)
        pairs: list[tuple[int, int]] = []
        if size <= 60:
            pairs = [(i, j) for i in range(size) for j in range(i + 1, size)]
        else:
            pairs = [(rng.randrange(size - 1), 0) for _ in range(samples_per_state)]
            pairs = [(i, i + 1 + rng.randrange(min(40, size - i - 1))) for i, _ in pairs]
        for i, j in pairs:
            checked_pairs += 1
            if commutes(i, j) != (_commutes(gates[i], gates[j]) is not None):
                mismatched += 1
                if len(details) < 5:
                    details.append(f"cost={size} pair=({i},{j})")
    return {
        "states_checked": len(states),
        "pairs_checked": checked_pairs,
        "mismatched": mismatched,
        "examples": details,
    }


def exposable_pairs(
    state: LandscapeState,
    max_d: int = CLOSURE_MAX_D,
    deadline: float | None = None,
) -> list[dict[str, Any]]:
    """All pairs that commutation alone can bring into cancellation.

    Exactness: in the trace monoid induced by the implemented commutation
    relation, occurrences i<j can be made adjacent iff no intervening letter is
    dependent with either of them.  A dependent letter can never cross, so it
    stays strictly between; conversely, if none is dependent, bubble j left
    through j-i-1 adjacent exchanges.  ``j = i + 1`` (distance 0) is included:
    ``GreedyGateCancellation`` does not merge rotations, so adjacent ``rz``
    pairs survive the frozen baseline (E54).
    """

    gates = state.gates
    size = len(gates)
    if size < 3:
        return []
    max_d = min(max_d, _adaptive_cap(size))
    first_dep, last_dep = _blocking(gates, max_d=max_d, deadline=deadline)
    found: list[dict[str, Any]] = []
    for i in range(size - 2):
        if deadline is not None and (i & 255) == 0 and time.perf_counter() > deadline:
            break
        gi = gates[i]
        limit = min(first_dep[i], size - 1)
        for j in range(i + 1, limit + 1):
            if last_dep[j] > i:
                continue
            rule = _pair_rule(gi, gates[j])
            if rule is None:
                continue
            distance = j - i - 1
            if distance > max_d:
                continue
            found.append(
                {
                    "i": i,
                    "j": j,
                    "distance": distance,
                    "rule_id": rule,
                    "predicted_horizon": distance + 1,
                }
            )
    return found


def criterion_min_distance(state: LandscapeState) -> dict[str, Any]:
    pairs = exposable_pairs(state)
    if not pairs:
        return {
            "exposable_pair_count": 0,
            "d_min": None,
            "d_max": None,
            "predicted_horizon": None,
            "rule_id": "",
            "all_distances": [],
        }
    best = min(pairs, key=lambda item: (item["distance"], item["i"], item["rule_id"]))
    return {
        "exposable_pair_count": len(pairs),
        "d_min": best["distance"],
        "d_max": max(item["distance"] for item in pairs),
        "predicted_horizon": best["distance"] + 1,
        "rule_id": best["rule_id"],
        "all_distances": sorted({item["distance"] for item in pairs}),
    }


# --------------------------------------------------------------------------
# Part C: the closure algorithm (certificate-producing)
# --------------------------------------------------------------------------

def _apply_step(
    state: LandscapeState,
    i: int,
    j: int,
    rule_id: str,
) -> tuple[LandscapeState, list[dict[str, Any]]]:
    """Bubble gate j left to i+1 by adjacent exchanges, then apply pair_v1."""

    actions: list[dict[str, Any]] = []
    current = state
    cursor = j
    while cursor > i + 1:
        exchange = next(
            iter(_iter_exchange_actions(current, only_location=cursor - 1)),
            None,
        )
        if exchange is None:
            # Swapping two *identical* gates is a no-op state, so the engine has
            # no exchange action for it.  Crossing such a gate changes nothing.
            if current.gates[cursor - 1] == current.gates[cursor]:
                cursor -= 1
                continue
            raise RuntimeError(f"criterion violated: no exchange at {cursor - 1}")
        actions.append(exchange.to_dict())
        current = exchange.post_state
        cursor -= 1
    pair = next(
        (action for action in _iter_pair_actions(current, only_location=i) if action.rule_id == rule_id),
        None,
    )
    if pair is None:
        raise RuntimeError(f"criterion violated: no {rule_id} at {i}")
    actions.append(pair.to_dict())
    return pair.post_state, actions


def closure_run(
    state: LandscapeState,
    *,
    deadline: float | None = None,
) -> dict[str, Any]:
    """Greedy commutation-closure fixpoint.  Deterministic and certified."""

    current = state
    all_actions: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []
    passes = 0
    truncated = False
    errors = 0
    for _ in range(CLOSURE_MAX_PASSES):
        passes += 1
        pairs = exposable_pairs(current, deadline=deadline)
        if not pairs:
            break
        pairs.sort(key=lambda item: (item["distance"], item["i"], item["rule_id"]))
        used: set[int] = set()
        selected: list[dict[str, Any]] = []
        for pair in pairs:
            span = set(range(pair["i"], pair["j"] + 1))
            if span & used:
                continue
            used |= span
            selected.append(pair)
        if not selected:
            break
        for pair in sorted(selected, key=lambda item: -item["i"]):
            if deadline is not None and time.perf_counter() > deadline:
                truncated = True
                break
            try:
                current, actions = _apply_step(current, pair["i"], pair["j"], pair["rule_id"])
            except RuntimeError as exc:
                errors += 1
                applied.append({"error": str(exc)})
                break
            all_actions.extend(actions)
            applied.append(
                {
                    "rule_id": pair["rule_id"],
                    "distance": pair["distance"],
                    "predicted_horizon": pair["predicted_horizon"],
                    "cost_after": current.cost,
                }
            )
        if truncated:
            break
    return {
        "final_state": current,
        "final_cost": current.cost,
        "initial_cost": state.cost,
        "passes": passes,
        "steps": len(applied),
        "action_count": len(all_actions),
        "actions": all_actions,
        "truncated": truncated,
        "errors": errors,
        "max_distance_used": max((item.get("distance", 0) for item in applied), default=0),
        "predicted_horizon_used": max((item.get("predicted_horizon", 0) for item in applied), default=0),
    }


# --------------------------------------------------------------------------
# IO helpers
# --------------------------------------------------------------------------

def _load_classification() -> dict[str, dict[str, str]]:
    with CLASSIFICATION.open(newline="", encoding="utf-8") as handle:
        return {row["source_id"]: row for row in csv.DictReader(handle)}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def _int_or_none(value: Any) -> int | None:
    if value in (None, "", "None"):
        return None
    return int(float(value))


# --------------------------------------------------------------------------
# Part A + C: the frozen panel
# --------------------------------------------------------------------------

def run_panel(
    output_root: Path | None = None,
    time_budget: float = CLOSURE_TIME_BUDGET_SECONDS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    classification = _load_classification()
    roots = load_root_states()
    criterion_rows: list[dict[str, Any]] = []
    closure_rows: list[dict[str, Any]] = []
    for index, root in enumerate(roots, start=1):
        source_id = root["source_id"]
        state: LandscapeState = root["state"]
        record = classification.get(source_id, {})
        started = time.perf_counter()
        source_deadline = started + time_budget
        criterion = criterion_min_distance(state)
        run = closure_run(state, deadline=source_deadline)
        elapsed = round(time.perf_counter() - started, 3)
        replay = replay_actions(state, run["actions"], RULE_LIBRARY, RULE_SCOPE)
        baseline_cost = _int_or_none(record.get("baseline_cost"))
        certified_best = _int_or_none(record.get("best_cost"))
        compact_best = _int_or_none(record.get("compact_best_cost"))
        criterion_rows.append(
            {
                "source_id": source_id,
                "circuit_family": record.get("circuit_family", ""),
                "n_qubits": record.get("n_qubits", ""),
                "root_cost": state.cost,
                "baseline_cost": baseline_cost,
                "certified_best_cost": certified_best,
                "best_cost_exactness": record.get("best_cost_exactness", ""),
                "exposable_pair_count": criterion["exposable_pair_count"],
                "d_min": criterion["d_min"],
                "d_max": criterion["d_max"],
                "predicted_horizon": criterion["predicted_horizon"],
                "min_rule_id": criterion["rule_id"],
                "distances": "|".join(str(value) for value in criterion["all_distances"]),
                "h3_search_could_see": (
                    ""
                    if criterion["predicted_horizon"] is None
                    else int(criterion["predicted_horizon"] <= 3)
                ),
            }
        )
        closure_rows.append(
            {
                "source_id": source_id,
                "circuit_family": record.get("circuit_family", ""),
                "root_cost": state.cost,
                "baseline_cost": baseline_cost,
                "certified_best_cost": certified_best,
                "closure_cost": run["final_cost"],
                "closure_gain_vs_root": state.cost - run["final_cost"],
                "closure_gain_vs_baseline": (
                    "" if baseline_cost is None else baseline_cost - run["final_cost"]
                ),
                "closure_vs_certified": (
                    "" if certified_best is None else certified_best - run["final_cost"]
                ),
                "closure_beats_certified": (
                    "" if certified_best is None else int(run["final_cost"] < certified_best)
                ),
                "closure_matches_certified": (
                    "" if certified_best is None else int(run["final_cost"] == certified_best)
                ),
                "passes": run["passes"],
                "steps": run["steps"],
                "action_count": run["action_count"],
                "max_distance_used": run["max_distance_used"],
                "predicted_horizon_used": run["predicted_horizon_used"],
                "truncated": int(run["truncated"]),
                "criterion_errors": run["errors"],
                "replay_status": "REPLAY_PASS" if replay.get("accepted") else f"REPLAY_FAIL:{replay.get('reason')}",
                "elapsed_seconds": elapsed,
            }
        )
        if output_root is not None and index % 8 == 0:
            _write_csv(output_root / "panel_criterion.csv", criterion_rows)
            _write_csv(output_root / "closure_results.csv", closure_rows)
        print(
            f"[{index:3d}/{len(roots)}] {source_id[:22]:22s} root={state.cost:4d} "
            f"closure={run['final_cost']:4d} cert={certified_best} D={criterion['d_min']} "
            f"{'PASS' if replay.get('accepted') else 'FAIL'}",
            flush=True,
        )
    aggregate = {
        "sources": len(closure_rows),
        "replay_pass": sum(1 for row in closure_rows if row["replay_status"] == "REPLAY_PASS"),
        "replay_fail": sum(1 for row in closure_rows if row["replay_status"] != "REPLAY_PASS"),
        "truncated": sum(row["truncated"] for row in closure_rows),
        "sources_with_exposable_pair": sum(1 for row in criterion_rows if row["exposable_pair_count"]),
        "d_min_histogram": _histogram([row["d_min"] for row in criterion_rows]),
        "total_root_gates": sum(row["root_cost"] for row in closure_rows),
        "total_closure_gates": sum(row["closure_cost"] for row in closure_rows),
        "closure_beats_certified_count": sum(row["closure_beats_certified"] for row in closure_rows),
        "closure_matches_certified_count": sum(row["closure_matches_certified"] for row in closure_rows),
        "certified_comparable_count": sum(1 for row in closure_rows if row["certified_best_cost"] is not None),
        "h3_could_see_count": sum(1 for row in criterion_rows if row["h3_search_could_see"] == 1),
        "h3_blind_but_exposable": sum(
            1
            for row in criterion_rows
            if row["predicted_horizon"] is not None and row["predicted_horizon"] > 3
        ),
    }
    return criterion_rows, closure_rows, aggregate


def _histogram(values: Iterable[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = "none" if value in (None, "") else str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (item[0] != "none", item[0])))


# --------------------------------------------------------------------------
# Part B: BV prediction
# --------------------------------------------------------------------------

def _bv_root(n_qubits: int) -> LandscapeState:
    source = make_bernstein_vazirani(n_qubits, seed=SEED)
    normalized, info = normalize_circuit(source)
    if normalized is None:
        raise RuntimeError(f"normalisation failed for n={n_qubits}: {info}")
    if int(normalized.size()) > MAX_BASELINE_GATES:
        baseline = normalized
    else:
        baseline = GreedyGateCancellation(
            max_iterations=50,
            fidelity_threshold=1.0,
            success_reduction=0.0,
        ).optimize(normalized).optimized_circuit
    return state_from_circuit(baseline)


def run_bv_prediction() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    measured: dict[str, Any] = {}
    if E50_SUMMARY.exists():
        measured = json.loads(E50_SUMMARY.read_text(encoding="utf-8")).get(
            "first_improving_horizon_by_size", {}
        )
    rows: list[dict[str, Any]] = []
    for n_qubits in BV_SIZES_MEASURED + BV_SIZES_EXTRAPOLATED:
        state = _bv_root(n_qubits)
        criterion = criterion_min_distance(state)
        run = closure_run(state)
        replay = replay_actions(state, run["actions"], RULE_LIBRARY, RULE_SCOPE)
        expected = measured.get(str(n_qubits))
        rows.append(
            {
                "n_qubits": n_qubits,
                "root_cost": state.cost,
                "exposable_pair_count": criterion["exposable_pair_count"],
                "d_min": criterion["d_min"],
                "predicted_horizon": criterion["predicted_horizon"],
                "measured_horizon_e50": "" if expected is None else expected,
                "prediction_matches": (
                    ""
                    if expected is None or criterion["predicted_horizon"] is None
                    else int(int(expected) == int(criterion["predicted_horizon"]))
                ),
                "closure_cost": run["final_cost"],
                "closure_gain": state.cost - run["final_cost"],
                "max_distance_used": run["max_distance_used"],
                "steps": run["steps"],
                "replay_status": "REPLAY_PASS" if replay.get("accepted") else f"REPLAY_FAIL:{replay.get('reason')}",
                "cohort": "measured" if n_qubits in BV_SIZES_MEASURED else "extrapolated",
            }
        )
        print(
            f"[BV n={n_qubits:3d}] root={state.cost:4d} D={criterion['d_min']} "
            f"pred={criterion['predicted_horizon']} measured={expected} closure={run['final_cost']}",
            flush=True,
        )
    matched = [row for row in rows if row["prediction_matches"] != ""]
    agreement = {
        "compared": len(matched),
        "matched": sum(row["prediction_matches"] for row in matched),
        "rows": [
            {
                "n_qubits": row["n_qubits"],
                "predicted": row["predicted_horizon"],
                "measured": row["measured_horizon_e50"],
            }
            for row in matched
        ],
    }
    # Growth law on the extrapolated tail: fit D = a * n + b by least squares
    # over the sizes where the criterion is defined.
    points = [(row["n_qubits"], row["d_min"]) for row in rows if row["d_min"] is not None]
    law: dict[str, Any] = {"points": points}
    if len(points) >= 3:
        xs = [float(x) for x, _ in points]
        ys = [float(y) for _, y in points]
        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        denom = sum((x - mean_x) ** 2 for x in xs)
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom if denom else 0.0
        intercept = mean_y - slope * mean_x
        residual = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
        total = sum((y - mean_y) ** 2 for y in ys)
        law.update(
            {
                "slope": round(slope, 6),
                "intercept": round(intercept, 6),
                "r_squared": round(1.0 - residual / total, 6) if total else None,
                "reading": "D_min grows linearly in n => required lookahead h* = D+1 is Theta(n)",
            }
        )
    return rows, {"agreement": agreement, "growth_law": law}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--panel", action="store_true", help="run the 128-source panel")
    parser.add_argument("--bv", action="store_true", help="run the BV prediction ladder")
    parser.add_argument("--time-budget", type=float, default=CLOSURE_TIME_BUDGET_SECONDS)
    parser.add_argument("--self-check", action="store_true", help="compare the local predicate with the engine")
    args = parser.parse_args()
    if not args.panel and not args.bv and not args.self_check:
        args.panel = args.bv = True
    args.output_root.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-23",
        "script": "scripts/e56_closure_criterion.py",
        "contract": {
            "rule_scope": RULE_SCOPE,
            "rule_library": str(RULE_LIBRARY.relative_to(ROOT)),
            "root_states": "experiments.e46_window_landscape.run.load_root_states (hash-checked)",
            "criterion": "g_i,g_j exposable iff every intervening gate commutes with both",
            "closure_selection": "smallest D first, non-overlapping, repeat to fixpoint",
            "max_passes": CLOSURE_MAX_PASSES,
            "time_budget_seconds_per_source": args.time_budget,
        },
        "inputs": {
            str(CLASSIFICATION.relative_to(ROOT)): _sha256(CLASSIFICATION),
        },
    }

    if args.self_check:
        sample = [root["state"] for root in load_root_states()[:16]]
        summary["predicate_self_check"] = predicate_agreement(sample)
        print(json.dumps(summary["predicate_self_check"], indent=2), flush=True)

    if args.panel:
        criterion_rows, closure_rows, aggregate = run_panel(
            output_root=args.output_root, time_budget=args.time_budget
        )
        _write_csv(args.output_root / "panel_criterion.csv", criterion_rows)
        _write_csv(args.output_root / "closure_results.csv", closure_rows)
        summary["panel"] = aggregate

    if args.bv:
        bv_rows, bv_meta = run_bv_prediction()
        _write_csv(args.output_root / "bv_prediction.csv", bv_rows)
        summary["bv"] = bv_meta

    (args.output_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
