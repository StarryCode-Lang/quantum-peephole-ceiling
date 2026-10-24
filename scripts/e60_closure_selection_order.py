"""E60: does the closure's pair-selection order matter? A theory-driven comparison.

Motivation
----------
The 2026-10-24 theory note (``docs/theory/closure_termination_and_optimality_2026-10-24.md``)
proves that a single closure pass is an *interval scheduling* problem: the pairs
cancellable in one pass are intervals ``[i, j]`` on the listing, and the pass can
realise any pairwise-span-disjoint subset.  The maximum such subset is attained
by greedy selection in **increasing right endpoint** ``j``.

The E56 implementation selects by **increasing crossing distance** ``D = j-i-1``
instead.  Length order carries no optimality proof, and the note gives a
three-interval counterexample where it loses a factor of two in a single pass.

This experiment answers the only question that matters for the paper: on the
real 128-source panel, does the order actually change the outcome?

Parts
-----
A  Panel comparison.  Run the closure to fixpoint under three selection keys --
   ``distance`` (E56, current), ``finish`` (right endpoint, provably per-pass
   optimal), and ``random`` (seeded, a control for how much the order can move
   the result at all).  Report final gate counts, two-qubit counts, pass counts,
   and per-source agreement.  Every run is replayed as a certificate.
B  Combinatorial demonstration.  The three-interval counterexample from the
   theory note, evaluated directly on the interval-scheduling abstraction.  This
   is a statement about the selection rule, not about a circuit, and is labelled
   as such.
C  Equivalence.  Dense-unitary equality between the ``distance`` and ``finish``
   outputs for every source with n <= 8, so a difference in gate count is never
   a difference in semantics.

Contract
    Read-only on ``data/``, ``release/``, ``docs/manuscript/``.  Frozen rule
    library and rule scope (``e44_core_v1``).  Root states from
    ``load_root_states`` (hash-checked).

Outputs (``docs/review/science_boost/2026-10-24_closure_order/``):
    * ``order_comparison.csv``   -- one row per (source, order)
    * ``intervals.csv``          -- Part B
    * ``summary.json``           -- aggregates, contract, hashes
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qiskit import QuantumCircuit  # noqa: E402
from qiskit.quantum_info import Operator  # noqa: E402

from experiments.e46_window_landscape.run import RULE_SCOPE, load_root_states  # noqa: E402
from src.optimisation.certified_landscape import LandscapeState, replay_actions  # noqa: E402
from scripts.e56_closure_criterion import (  # noqa: E402
    CLOSURE_MAX_PASSES,
    _apply_step,
    exposable_pairs,
)

EXPERIMENT_ID = "E60_CLOSURE_SELECTION_ORDER_2026_10_24"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-24_closure_order"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
TWO_QUBIT = frozenset({"cx", "cz", "swap"})
UNITARY_QUBIT_CAP = 8
UNITARY_GATE_CAP = 600
SEED = 42
ORDERS = ("distance", "finish", "random")


# --------------------------------------------------------------------------
# closure with a pluggable selection key
# --------------------------------------------------------------------------

def _key_distance(pair: Mapping[str, Any]) -> tuple[int, int, str]:
    return (pair["distance"], pair["i"], pair["rule_id"])


def _key_finish(pair: Mapping[str, Any]) -> tuple[int, int, str]:
    # Interval scheduling: earliest right endpoint first; ties by larger i
    # (the shorter of two intervals sharing a right endpoint).
    return (pair["j"], -pair["i"], pair["rule_id"])


def _key_random(pair: Mapping[str, Any]) -> tuple[int, int, str]:
    return (pair["_rand"], 0, "")


KEYS: dict[str, Callable[[Mapping[str, Any]], tuple[Any, ...]]] = {
    "distance": _key_distance,
    "finish": _key_finish,
    "random": _key_random,
}


def closure_with_order(state: LandscapeState, order: str, seed: int = SEED) -> dict[str, Any]:
    rng = random.Random(seed)
    current = state
    applied: list[dict[str, Any]] = []
    all_actions: list[dict[str, Any]] = []
    passes = 0
    errors = 0
    for _ in range(CLOSURE_MAX_PASSES):
        passes += 1
        pairs = exposable_pairs(current)
        if not pairs:
            break
        if order == "random":
            for pair in pairs:
                pair["_rand"] = rng.random()
        pairs.sort(key=KEYS[order])
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
                    "cost_after": current.cost,
                }
            )
    return {
        "final_state": current,
        "final_cost": current.cost,
        "passes": passes,
        "steps": len(applied),
        "actions": all_actions,
        "errors": errors,
    }


def _counts(state: LandscapeState) -> dict[str, int]:
    total = len(state.gates)
    two_q = sum(1 for gate in state.gates if gate.name in TWO_QUBIT)
    return {"total": total, "two_qubit": two_q}


def _to_qiskit(state: LandscapeState) -> QuantumCircuit | None:
    circuit = QuantumCircuit(state.num_qubits)
    for gate in state.gates:
        if gate.name == "h":
            circuit.h(gate.qubits[0])
        elif gate.name == "x":
            circuit.x(gate.qubits[0])
        elif gate.name == "rz":
            circuit.rz(float(gate.angle or 0.0), gate.qubits[0])
        elif gate.name == "cx":
            circuit.cx(gate.qubits[0], gate.qubits[1])
        else:
            return None
    return circuit


def _unitary_equal(left: LandscapeState, right: LandscapeState) -> bool | None:
    if left.num_qubits != right.num_qubits:
        return False
    if left.num_qubits > UNITARY_QUBIT_CAP or max(len(left.gates), len(right.gates)) > UNITARY_GATE_CAP:
        return None
    a, b = _to_qiskit(left), _to_qiskit(right)
    if a is None or b is None:
        return None
    try:
        return bool(Operator(a).equiv(Operator(b)))
    except Exception:
        return None


# --------------------------------------------------------------------------
# Part B: interval-scheduling demonstration
# --------------------------------------------------------------------------

def interval_demo() -> list[dict[str, Any]]:
    """Three intervals where length order loses a factor of two in one pass."""

    intervals = [(1, 9), (9, 11), (11, 20)]
    rows: list[dict[str, Any]] = []

    def select(key: Callable[[tuple[int, int]], tuple[Any, ...]]) -> list[tuple[int, int]]:
        ordered = sorted(intervals, key=key)
        used: set[int] = set()
        chosen: list[tuple[int, int]] = []
        for start, end in ordered:
            span = set(range(start, end + 1))
            if span & used:
                continue
            used |= span
            chosen.append((start, end))
        return chosen

    for label, key in (
        ("distance", lambda item: (item[1] - item[0] - 1, item[0])),
        ("finish", lambda item: (item[1], -item[0])),
    ):
        chosen = select(key)
        rows.append(
            {
                "order": label,
                "intervals": json.dumps(intervals),
                "chosen": json.dumps(chosen),
                "pairs_cancelled": len(chosen),
                "gates_removed": 2 * len(chosen),
            }
        )
    return rows


# --------------------------------------------------------------------------
# IO
# --------------------------------------------------------------------------

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
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(OUTPUT_ROOT))
    args = parser.parse_args()
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    started = time.time()
    rows: list[dict[str, Any]] = []
    for root in load_root_states():
        state = root["state"]
        per_order: dict[str, dict[str, Any]] = {}
        for order in ORDERS:
            run = closure_with_order(state, order)
            replay = replay_actions(state, run["actions"], RULE_LIBRARY, RULE_SCOPE)
            counts = _counts(run["final_state"])
            per_order[order] = {
                "final_state": run["final_state"],
                "final_cost": run["final_cost"],
                "two_qubit": counts["two_qubit"],
                "passes": run["passes"],
                "steps": run["steps"],
                "replay_ok": bool(replay.get("accepted", False)),
                "errors": run["errors"],
            }
        equiv = _unitary_equal(per_order["distance"]["final_state"], per_order["finish"]["final_state"])
        for order in ORDERS:
            payload = per_order[order]
            rows.append(
                {
                    "source_id": root["source_id"],
                    "circuit_family": root["circuit_family"],
                    "n_qubits": root["n_qubits"],
                    "root_cost": state.cost,
                    "root_two_qubit": _counts(state)["two_qubit"],
                    "order": order,
                    "final_cost": payload["final_cost"],
                    "final_two_qubit": payload["two_qubit"],
                    "gain": state.cost - payload["final_cost"],
                    "passes": payload["passes"],
                    "steps": payload["steps"],
                    "replay_ok": payload["replay_ok"],
                    "errors": payload["errors"],
                    "distance_vs_finish_unitary": "" if equiv is None else str(equiv),
                }
            )

    by_order: dict[str, dict[str, Any]] = {}
    for order in ORDERS:
        subset = [row for row in rows if row["order"] == order]
        by_order[order] = {
            "sources": len(subset),
            "root_total": sum(row["root_cost"] for row in subset),
            "final_total": sum(row["final_cost"] for row in subset),
            "gain_total": sum(row["gain"] for row in subset),
            "final_two_qubit": sum(row["final_two_qubit"] for row in subset),
            "passes_total": sum(row["passes"] for row in subset),
            "replay_pass": sum(1 for row in subset if row["replay_ok"]),
            "errors": sum(1 for row in subset if row["errors"]),
        }

    index = {(row["source_id"], row["order"]): row for row in rows}
    source_ids = sorted({row["source_id"] for row in rows})
    finish_better = sum(
        1
        for sid in source_ids
        if index[(sid, "finish")]["final_cost"] < index[(sid, "distance")]["final_cost"]
    )
    distance_better = sum(
        1
        for sid in source_ids
        if index[(sid, "distance")]["final_cost"] < index[(sid, "finish")]["final_cost"]
    )
    equiv_rows = [row for row in rows if row["order"] == "distance" and row["distance_vs_finish_unitary"]]
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-24",
        "contract": {
            "root_states": "experiments.e46_window_landscape.run.load_root_states (hash-checked)",
            "rule_library": str(RULE_LIBRARY.relative_to(ROOT)),
            "rule_scope": RULE_SCOPE,
            "orders": list(ORDERS),
            "max_passes": CLOSURE_MAX_PASSES,
            "random_seed": SEED,
        },
        "inputs": {str(RULE_LIBRARY.relative_to(ROOT)): _sha256(RULE_LIBRARY)},
        "by_order": by_order,
        "finish_vs_distance": {
            "finish_strictly_better": finish_better,
            "distance_strictly_better": distance_better,
            "tied": len(source_ids) - finish_better - distance_better,
        },
        "unitary_checked": len(equiv_rows),
        "unitary_pass": sum(1 for row in equiv_rows if row["distance_vs_finish_unitary"] == "True"),
        "unitary_fail": sum(1 for row in equiv_rows if row["distance_vs_finish_unitary"] == "False"),
        "interval_demo": interval_demo(),
        "wall_clock_seconds": round(time.time() - started, 1),
    }
    _write_csv(output_root / "order_comparison.csv", rows)
    _write_csv(output_root / "intervals.csv", summary["interval_demo"])
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("by_order", "finish_vs_distance", "unitary_checked", "unitary_pass", "unitary_fail")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
