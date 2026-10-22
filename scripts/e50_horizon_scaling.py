"""E50: does the peephole escape depth grow with circuit size?

Motivation
----------
E47 (2026-10-19) showed that 19 of 33 real horizon-3 "local optima" admit a
strictly cheaper circuit at horizon 4..7, and that the six BV oracle escapes
all first appear at depth 4 with a 2-gate gain.  That is a fixed-horizon
statement on a fixed panel.  The question that decides whether the phenomenon
is a *law* or an artefact of one panel is whether the first improving horizon
grows with the circuit size on a controlled family.

This experiment builds Bernstein-Vazirani oracles ``bv_n`` for n = 4..14 with
the project's own generator, normalises them with the project's own normaliser,
reproduces the panel's baseline rule (greedy fixed point, or the raw normalised
circuit when it exceeds ``MAX_BASELINE_GATES``), and runs one exact
finite-horizon BFS per size out to horizon 6 under the frozen contract
(``e44_core_v1``, 200k states, 30 s).  For each size it records the smallest
horizon at which a strictly cheaper state is certified, and the best cost per
horizon.

A *growing* first-improving horizon is evidence for a size-dependent
reachability barrier; a *flat* one says the effect saturates and the claim must
stay finite-horizon.

Outputs (``docs/review/science_boost/2026-10-21_horizon_scaling/``):
  * ``bv_horizon_scaling.csv`` -- one row per (n, horizon)
  * ``summary.json``           -- first improving horizon per size + contracts

Read-only with respect to ``data/`` and ``release/``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e45_development_grid.run import (  # noqa: E402
    MAX_BASELINE_GATES,
    RULE_LIBRARY,
    normalize_circuit,
    state_from_circuit,
)
from experiments.e46_window_landscape.run import RULE_SCOPE  # noqa: E402
from src.circuits.real_benchmarks import make_bernstein_vazirani  # noqa: E402
from src.optimisation.certified_landscape import (  # noqa: E402
    replay_actions,
    search_landscape_horizons_compact,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402

EXPERIMENT_ID = "E50_BV_HORIZON_SCALING_2026_10_21"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-21_horizon_scaling"
SIZES = (4, 6, 8, 10, 12, 14, 16, 20)
HORIZONS = (1, 2, 3, 4, 5, 6, 7, 8)
STATE_BUDGET = 200_000
TIME_BUDGET_SECONDS = 30.0
SEED = 42


def run_one(n_qubits: int) -> dict[str, Any]:
    source = make_bernstein_vazirani(n_qubits, seed=SEED)
    normalized, info = normalize_circuit(source)
    if normalized is None:
        return {"n_qubits": n_qubits, "status": "NORMALIZATION_FAILED", "info": info}
    if int(normalized.size()) > MAX_BASELINE_GATES:
        baseline = normalized
        root_kind = "RAW_NORMALIZED_OVER_BASELINE_BUDGET"
    else:
        baseline = GreedyGateCancellation(
            max_iterations=50,
            fidelity_threshold=1.0,
            success_reduction=0.0,
        ).optimize(normalized).optimized_circuit
        root_kind = "GREEDY_FIXED_POINT"
    state = state_from_circuit(baseline)
    started = time.perf_counter()
    result = search_landscape_horizons_compact(
        state,
        RULE_LIBRARY,
        HORIZONS,
        state_budget=STATE_BUDGET,
        rule_scope=RULE_SCOPE,
        time_budget_seconds=TIME_BUDGET_SECONDS,
    )
    elapsed = round(time.perf_counter() - started, 3)
    rows = []
    first_improving = None
    witness_deltas: list[int] = []
    witness_rule_ids: list[str] = []
    replay_status = ""
    for horizon in HORIZONS:
        entry = result[str(horizon)]
        status = str(entry.get("status", ""))
        best_cost = entry.get("best_cost")
        rows.append(
            {
                "n_qubits": n_qubits,
                "horizon": horizon,
                "status": status,
                "best_cost": best_cost,
                "initial_cost": int(state.cost),
                "improved": bool(best_cost is not None and int(best_cost) < int(state.cost)),
                "resource_reason": str(entry.get("resource_reason", "") or ""),
                "elapsed_seconds": elapsed,
            }
        )
        if first_improving is None and best_cost is not None and int(best_cost) < int(state.cost):
            first_improving = horizon
            escape_witness = entry.get("witnesses", {}).get("escape", [])
            witness_deltas = [int(step.get("cost_delta", 0)) for step in escape_witness]
            witness_rule_ids = [str(step.get("rule_id", "")) for step in escape_witness]
            replay = replay_actions(state, escape_witness, RULE_LIBRARY, RULE_SCOPE)
            replay_status = (
                "REPLAY_PASS"
                if replay.get("accepted")
                and replay.get("final_state_sha256") == entry.get("best_state_sha256")
                else f"REPLAY_FAIL:{replay.get('reason', 'endpoint_mismatch')}"
            )
    return {
        "n_qubits": n_qubits,
        "status": "OK",
        "source_gate_count": int(source.size()),
        "normalized_gate_count": int(info["normalized_gate_count"]),
        "root_kind": root_kind,
        "initial_cost": int(state.cost),
        "first_improving_horizon": first_improving,
        "escape_witness_cost_deltas": witness_deltas,
        "escape_witness_rule_ids": witness_rule_ids,
        "escape_witness_replay": replay_status,
        "neutral_prefix_length": (
            next((index for index, delta in enumerate(witness_deltas) if delta != 0), None)
            if witness_deltas
            else None
        ),
        "best_cost_at_max_horizon": rows[-1]["best_cost"],
        "horizon_rows": rows,
        "elapsed_seconds": elapsed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="*", default=list(SIZES))
    args = parser.parse_args()

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    for n_qubits in args.sizes:
        print(f"[E50] n={n_qubits} ...", flush=True)
        record = run_one(n_qubits)
        results.append(record)
        if record["status"] == "OK":
            print(
                f"[E50] n={n_qubits} root={record['initial_cost']} "
                f"({record['root_kind']}) first_improving_h={record['first_improving_horizon']} "
                f"best_at_max_h={record['best_cost_at_max_horizon']} t={record['elapsed_seconds']}s",
                flush=True,
            )
        else:
            print(f"[E50] n={n_qubits} {record['status']}", flush=True)

    rows = [row for record in results if record["status"] == "OK" for row in record["horizon_rows"]]
    csv_path = OUTPUT_ROOT / "bv_horizon_scaling.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = __import__("csv").DictWriter(
                handle, fieldnames=list(rows[0].keys()), lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-21",
        "contract": {
            "rule_scope": RULE_SCOPE,
            "state_budget": STATE_BUDGET,
            "time_budget_seconds": TIME_BUDGET_SECONDS,
            "horizons": list(HORIZONS),
            "baseline_rule": (
                "greedy fixed point of the normalised circuit; raw normalised circuit when it "
                f"exceeds MAX_BASELINE_GATES={MAX_BASELINE_GATES}"
            ),
            "generator": f"src.circuits.real_benchmarks.make_bernstein_vazirani(seed={SEED})",
        },
        "sizes": results,
        "first_improving_horizon_by_size": {
            str(record["n_qubits"]): record.get("first_improving_horizon")
            for record in results
            if record["status"] == "OK"
        },
        "reading": (
            "A monotone increase of first_improving_horizon with n supports a size-dependent "
            "reachability barrier. A flat curve supports a bounded-horizon phenomenon. Either "
            "way the statement is about this generator, this normaliser and e44_core_v1."
        ),
        "script": "scripts/e50_horizon_scaling.py",
    }
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary["first_improving_horizon_by_size"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
