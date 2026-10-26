"""E73: rule-library completeness on a fragment where the absolute optimum is known.

Motivation
----------
E72 (2026-10-27) shows the certified landscape splits cleanly into

  * an **order class**, decided exactly and without search by the exposability
    criterion (0 false positives in 76,236 windows), and
  * a **content class**, which no commutation argument can reach and which
    accounts for 67.2% of the escapes on genuine greedy fixed points.

The content class is therefore a property of the *rule library*, not of the
listing.  Round 15 left the corresponding question open as P1-1:

    "Can 'optimal relative to the 1,488-rule library' be replaced by 'optimal
     relative to a complete rule set'?"

This experiment answers the smallest honest version of that question.  On the
2-qubit Clifford fragment -- where the absolute optimum of every unitary class
is computable by exhaustive enumeration -- it measures three costs for every
listing:

    c_abs    absolute minimum gate count in the fragment (ground truth)
    c_pair   cost after the project's own peephole closure (pair_v1 only)
    c_lib    cost after greedy closure over the *full* 1,488-rule library

The gap ``c_lib - c_abs`` is exactly the residual that P1-1 has to close: it is
nonzero only if the library is incomplete at this size.

Contract
--------
Read-only.  Frozen rule library ``data/v13/e43_quartz_rule_import/generation_a/rule_library.json``
(sha256 recorded), scope ``full``.  No file under ``data/``, ``release/`` or
``docs/manuscript/`` is written.

Outputs (``docs/review/science_boost/2026-10-27_library_completeness/``)
    classes.csv    one row per unitary class: c_abs, best achievable per engine
    members.csv    one row per listing: costs under each closure
    failures.csv   listings where a closure cannot reach c_abs, with witnesses
    summary.json   coverage, gap distribution, contract, hashes
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from src.optimisation.certified_landscape import (  # noqa: E402
    LandscapeState,
    StateGate,
    _state_from_normalized,
    legal_actions,
    state_unitary,
)

EXPERIMENT_ID = "E73_LIBRARY_COMPLETENESS_2026_10_27"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-27_library_completeness"

# Two-qubit Clifford generators, both qubit orders for the entangler.
GENERATORS: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("h", (0,)),
    ("h", (1,)),
    ("x", (0,)),
    ("x", (1,)),
    ("z", (0,)),
    ("z", (1,)),
    ("cx", (0, 1)),
    ("cx", (1, 0)),
)


ALPHABET = frozenset({"h", "x", "z", "cx"})


def in_alphabet(state: LandscapeState) -> bool:
    return all(gate.name in ALPHABET for gate in state.gates)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def canonical_unitary_key(state: LandscapeState, tolerance: int = 6) -> str:
    """Unitary up to global phase, rounded -- the identity of the class."""

    matrix = state_unitary(state)
    flat = matrix.reshape(-1)
    pivot = int(np.argmax(np.abs(flat)))
    if abs(flat[pivot]) < 1e-9:
        raise RuntimeError("degenerate_unitary")
    # Divide by the pivot *value* (not its phase) so that the pivot entry becomes
    # exactly +1 and the global phase is fixed consistently: U and -U map to the
    # same key, which is what "equal up to global phase" means.
    normalised = matrix / flat[pivot]
    real = np.round(normalised.real, tolerance) + 0.0
    imag = np.round(normalised.imag, tolerance) + 0.0
    return ";".join(f"{r:+.6f}{i:+.6f}" for r, i in zip(real.reshape(-1), imag.reshape(-1)))


def listing(state: LandscapeState) -> str:
    parts = []
    for gate in state.gates:
        if len(gate.qubits) == 1:
            parts.append(f"{gate.name}{gate.qubits[0]}")
        else:
            parts.append(f"{gate.name}{gate.qubits[0]}{gate.qubits[1]}")
    return ".".join(parts)


def enumerate_listings(max_length: int) -> list[LandscapeState]:
    states: list[LandscapeState] = [_state_from_normalized(2, ())]
    for length in range(1, max_length + 1):
        for word in itertools.product(range(len(GENERATORS)), repeat=length):
            gates = tuple(StateGate(GENERATORS[i][0], GENERATORS[i][1], None) for i in word)
            states.append(_state_from_normalized(2, gates))
    return states


def greedy_closure(
    state: LandscapeState, scope: str, deadline: float, restrict_alphabet: bool
) -> tuple[LandscapeState, list[str]]:
    """Repeatedly apply the largest cost reduction available; return fixpoint + path."""

    current = state
    path: list[str] = []
    for _ in range(24):
        if time.perf_counter() > deadline:
            path.append("DEADLINE")
            break
        best = None
        for action in legal_actions(current, RULE_LIBRARY, scope):
            if action.cost_delta >= 0:
                continue
            if restrict_alphabet and not in_alphabet(action.post_state):
                continue
            key = (action.post_state.cost, action.rule_id, action.location)
            if best is None or key < best[0]:
                best = (key, action)
        if best is None:
            break
        action = best[1]
        current = action.post_state
        path.append(f"{action.rule_id}@{action.location}({action.cost_delta})")
    return current, path


def bfs_reaches(
    state: LandscapeState,
    target_cost: int,
    max_depth: int,
    deadline: float,
    restrict_alphabet: bool = True,
    max_nodes: int = 20000,
) -> tuple[bool, int, str]:
    """Exhaustive search for any state of cost <= target within ``max_depth`` actions.

    Only cost-non-increasing actions are expanded (a detour that raises the cost
    cannot help reach a *lower* cost in fewer actions).  Returns
    (reached, nodes_expanded, first_rule_path).
    """

    frontier = [(state, ())]
    seen = {state.state_hash}
    nodes = 0
    for depth in range(max_depth):
        next_frontier = []
        for current, path in frontier:
            if time.perf_counter() > deadline or nodes > max_nodes:
                return False, nodes, "BUDGET"
            for action in legal_actions(current, RULE_LIBRARY, "full"):
                if action.cost_delta > 0:
                    continue
                if restrict_alphabet and not in_alphabet(action.post_state):
                    continue
                nodes += 1
                if action.post_state.cost <= target_cost:
                    return True, nodes, "|".join(path + (f"{action.rule_id}@{action.location}",))
                if action.post_state.state_hash in seen:
                    continue
                seen.add(action.post_state.state_hash)
                next_frontier.append((action.post_state, path + (f"{action.rule_id}@{action.location}",)))
        frontier = next_frontier
        if not frontier:
            break
    return False, nodes, ""


def library_structure() -> dict[str, Any]:
    """Coverage census of the frozen library, by source-pattern length and arity."""

    library = json.loads(RULE_LIBRARY.read_text(encoding="utf-8"))
    quartz = [rule for rule in library["rules"] if rule.get("rule_family") == "quartz_v1"]
    by_arity: dict[str, Counter[int]] = defaultdict(Counter)
    for rule in quartz:
        by_arity[str(rule["source"]["num_qubits"])][len(rule["source"]["operations"])] += 1
    return {
        "quartz_rules": len(quartz),
        "source_length_histogram": dict(sorted(Counter(len(r["source"]["operations"]) for r in quartz).items())),
        "source_length_by_arity": {arity: dict(sorted(counter.items())) for arity, counter in sorted(by_arity.items())},
        "one_qubit_rules": sum(counter_total for counter_total in by_arity["1"].values()),
        "gate_names_in_sources": sorted({op["name"] for r in quartz for op in r["source"]["operations"]}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-length", type=int, default=5)
    parser.add_argument("--budget-seconds", type=float, default=900.0)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)
    deadline = time.perf_counter() + args.budget_seconds

    states = enumerate_listings(args.max_length)
    classes: dict[str, list[tuple[int, LandscapeState]]] = defaultdict(list)
    for index, state in enumerate(states):
        if time.perf_counter() > deadline:
            raise RuntimeError("enumeration_deadline")
        classes[canonical_unitary_key(state)].append((len(state.gates), state))

    class_rows: list[dict[str, Any]] = []
    member_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for key, members in classes.items():
        c_abs = min(cost for cost, _ in members)
        for cost, state in members:
            if time.perf_counter() > deadline:
                raise RuntimeError("closure_deadline")
            frag_state, frag_path = greedy_closure(state, "full", deadline, restrict_alphabet=True)
            open_state, open_path = greedy_closure(state, "full", deadline, restrict_alphabet=False)
            gap = frag_state.cost - c_abs
            reached = None
            bfs_nodes = 0
            bfs_path = ""
            root_actions = None
            if gap > 0:
                reached, bfs_nodes, bfs_path = bfs_reaches(
                    state, c_abs, max_depth=min(gap, 3), deadline=deadline
                )
                root_actions = len(legal_actions(state, RULE_LIBRARY, "full"))
            member_rows.append(
                {
                    "experiment_id": EXPERIMENT_ID,
                    "class_key": key[:24],
                    "listing": listing(state),
                    "cost": cost,
                    "c_abs": c_abs,
                    "c_frag": frag_state.cost,
                    "c_open": open_state.cost,
                    "frag_gap": gap,
                    "open_gap": open_state.cost - c_abs,
                    "bfs_reaches": "" if reached is None else reached,
                    "bfs_nodes": bfs_nodes,
                    "root_legal_actions": "" if root_actions is None else root_actions,
                    "frag_path": "|".join(frag_path),
                    "open_path": "|".join(open_path),
                    "bfs_path": bfs_path,
                }
            )
            if gap > 0 and reached is not True:
                failures.append(
                    {
                        "experiment_id": EXPERIMENT_ID,
                        "class_key": key[:24],
                        "listing": listing(state),
                        "cost": cost,
                        "c_abs": c_abs,
                        "c_frag": frag_state.cost,
                        "frag_gap": gap,
                        "bfs_reaches": reached,
                        "bfs_nodes": bfs_nodes,
                        "frag_path": "|".join(frag_path),
                    }
                )
        window = member_rows[-len(members) :]
        class_rows.append(
            {
                "experiment_id": EXPERIMENT_ID,
                "class_key": key[:24],
                "class_size": len(members),
                "c_abs": c_abs,
                "max_cost_in_class": max(cost for cost, _ in members),
                "min_c_frag": min(row["c_frag"] for row in window),
                "min_c_open": min(row["c_open"] for row in window),
            }
        )

    total_members = len(member_rows)
    reducible = [row for row in member_rows if row["cost"] > row["c_abs"]]
    frag_exact = sum(1 for row in member_rows if row["frag_gap"] == 0)
    frag_reducible_exact = sum(1 for row in reducible if row["frag_gap"] == 0)
    greedy_failures = [row for row in reducible if row["frag_gap"] > 0]
    bfs_saved = sum(1 for row in greedy_failures if row["bfs_reaches"] is True)
    bfs_unknown = sum(1 for row in greedy_failures if row["bfs_reaches"] == "")
    depth_capped = sum(1 for row in greedy_failures if row["frag_gap"] > 3)
    open_below_abs = sum(1 for row in member_rows if row["open_gap"] < 0)

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-10-27",
        "fragment": {
            "num_qubits": 2,
            "generators": [f"{name}{''.join(str(q) for q in qubits)}" for name, qubits in GENERATORS],
            "alphabet": sorted(ALPHABET),
            "max_length": args.max_length,
            "listings": len(states),
        },
        "classes": {
            "count": len(classes),
            "size_histogram": dict(sorted(Counter(len(v) for v in classes.values()).items())),
            "c_abs_histogram": dict(sorted(Counter(row["c_abs"] for row in class_rows).items())),
        },
        "alphabet_restricted_closure": {
            "members": total_members,
            "reducible_members": len(reducible),
            "reaches_c_abs_all": frag_exact,
            "rate_all": round(frag_exact / total_members, 6),
            "reaches_c_abs_reducible": frag_reducible_exact,
            "rate_reducible": round(frag_reducible_exact / len(reducible), 6) if reducible else None,
            "greedy_failures": len(greedy_failures),
            "greedy_failures_rescued_by_bounded_search": bfs_saved,
            "greedy_failures_unresolved": len(greedy_failures) - bfs_saved - bfs_unknown,
            "greedy_failures_budget_exhausted": bfs_unknown,
            "greedy_failures_depth_capped_at_3": depth_capped,
            "greedy_failures_with_zero_legal_actions": sum(
                1 for row in greedy_failures if row["root_legal_actions"] == 0
            ),
            "rate_reducible_after_search": (
                round((frag_reducible_exact + bfs_saved) / len(reducible), 6) if reducible else None
            ),
        },
        "unrestricted_closure": {
            "members_below_fragment_optimum": open_below_abs,
            "note": (
                "open_gap < 0 means the library rewrote the circuit into a cheaper listing "
                "outside the {h,x,z,cx} alphabet; the fragment optimum is therefore not the "
                "absolute optimum over all gate sets, only the minimum inside the alphabet."
            ),
        },
        "frag_gap_histogram": {str(k): v for k, v in sorted(Counter(row["frag_gap"] for row in member_rows).items())},
        "open_gap_histogram": {str(k): v for k, v in sorted(Counter(row["open_gap"] for row in member_rows).items())},
        "library_structure": library_structure(),
        "failures": len(failures),
        "failure_examples": failures[:10],
        "contract": {
            "rule_library": RULE_LIBRARY.relative_to(ROOT).as_posix(),
            "rule_library_sha256": sha256_file(RULE_LIBRARY),
            "scope": "full (1,488 rules) + pair_v1 + structural exchanges",
            "read_only": ["data/", "release/", "docs/manuscript/"],
            "absolute_optimum": "min gate count over all enumerated listings of the same unitary",
        },
    }

    _write_csv(
        out / "members.csv",
        member_rows,
        [
            "experiment_id",
            "class_key",
            "listing",
            "cost",
            "c_abs",
            "c_frag",
            "c_open",
            "frag_gap",
            "open_gap",
            "bfs_reaches",
            "bfs_nodes",
            "root_legal_actions",
            "frag_path",
            "open_path",
            "bfs_path",
        ],
    )
    _write_csv(
        out / "classes.csv",
        class_rows,
        ["experiment_id", "class_key", "class_size", "c_abs", "max_cost_in_class", "min_c_frag", "min_c_open"],
    )
    _write_csv(
        out / "failures.csv",
        failures,
        ["experiment_id", "class_key", "listing", "cost", "c_abs", "c_frag", "frag_gap", "bfs_reaches", "bfs_nodes", "frag_path"],
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (out / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": EXPERIMENT_ID,
                "generated": "2026-10-27",
                "script": "scripts/e73_library_completeness.py",
                "artifacts": {
                    name: sha256_file(out / name)
                    for name in sorted(["members.csv", "classes.csv", "failures.csv", "summary.json"])
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "classes": summary["classes"],
                "alphabet_restricted_closure": summary["alphabet_restricted_closure"],
                "unrestricted_closure": summary["unrestricted_closure"],
                "frag_gap_histogram": summary["frag_gap_histogram"],
                "failures": summary["failures"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
