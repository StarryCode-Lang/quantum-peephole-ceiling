"""Replay and semantically verify the E47 horizon-ladder escapes.

For every source that the ladder found strictly cheaper than its root, re-run
the first improving horizon, replay the stored escape witness step by step, and
check two independent things:

1. the replayed endpoint costs strictly less than the root (the escape is real);
2. the replayed endpoint is unitarily equivalent to the root up to global phase
   (the escape is not a semantic accident of the rule library).

The second check uses the project's dense-unitary contract, so it is exact only
for the sizes in this panel (n <= 9).  Outputs stay under
``docs/review/science_boost/2026-10-19_horizon4_probe/``.
"""

from __future__ import annotations

import argparse
import csv
import json
import multiprocessing
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e45_development_grid.run import RULE_LIBRARY  # noqa: E402
from experiments.e46_window_landscape.run import (  # noqa: E402
    RULE_SCOPE,
    load_root_states,
)
from src.optimisation.certified_landscape import (  # noqa: E402
    iter_legal_actions,
    replay_actions,
    search_landscape_horizons_compact,
    semantically_equivalent,
)

OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-19_horizon4_probe"
LADDER_SUMMARY = OUTPUT_ROOT / "ladder_summary.json"
STATE_BUDGET = 200_000
TIME_BUDGET_SECONDS = 20.0
WORKERS = 8


def _verify_one(job: dict[str, Any]) -> dict[str, Any]:
    horizon = int(job["first_improving_horizon"])
    initial = job["state"]
    certificates = search_landscape_horizons_compact(
        initial,
        RULE_LIBRARY,
        [horizon],
        state_budget=STATE_BUDGET,
        rule_scope=RULE_SCOPE,
        time_budget_seconds=TIME_BUDGET_SECONDS,
    )
    certificate = certificates[str(horizon)]
    actions = certificate.get("witnesses", {}).get("escape", [])
    row = {
        "source_id": job["source_id"],
        "circuit_family": job["circuit_family"],
        "circuit_id": job["circuit_id"],
        "n_qubits": job["n_qubits"],
        "baseline_cost": job["baseline_cost"],
        "horizon": horizon,
        "status": certificate.get("status"),
        "escape_depth": certificate.get("escape_depth"),
        "best_cost_at_horizon": certificate.get("best_cost"),
        "witness_steps": len(actions),
        "replay_status": "NO_WITNESS",
        "replay_endpoint_cost": None,
        "semantic_check": "NOT_RUN",
        "verdict": "UNVERIFIED",
    }
    if not actions:
        return row
    try:
        replay = replay_actions(initial, actions, RULE_LIBRARY, RULE_SCOPE)
    except Exception as exc:  # noqa: BLE001 - recorded, never raised
        row["replay_status"] = f"REPLAY_ERROR:{type(exc).__name__}"
        return row
    if not replay.get("accepted"):
        row["replay_status"] = f"REPLAY_REJECTED:{replay.get('reason')}"
        row["verdict"] = "REPLAY_FAILURE"
        return row
    row["replay_status"] = "REPLAY_PASS"

    # Independent global check: walk the witness again through the public action
    # generator to recover the endpoint state, then compare unitaries exactly.
    current = initial.normalized()
    walked = 0
    for record in actions:
        match = None
        for action in iter_legal_actions(current, RULE_LIBRARY, RULE_SCOPE):
            if (
                action.rule_id == record["rule_id"]
                and action.location == int(record["location"])
                and action.post_state_sha256 == record["post_state_sha256"]
            ):
                match = action
                break
        if match is None:
            row["semantic_check"] = "ENDPOINT_WALK_FAILED"
            row["verdict"] = "UNVERIFIED"
            return row
        current = match.post_state
        walked += 1
    row["replay_endpoint_cost"] = current.cost
    equivalent = bool(semantically_equivalent(initial, current))
    row["semantic_check"] = "UNITARY_EQUIVALENT" if equivalent else "UNITARY_MISMATCH"
    if equivalent and current.cost < initial.cost:
        row["verdict"] = "CERTIFIED_ESCAPE"
    elif equivalent:
        row["verdict"] = "NO_IMPROVEMENT"
    else:
        row["verdict"] = "SEMANTIC_FAILURE"
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    output_root = args.output_root.resolve()

    ladder = json.loads(LADDER_SUMMARY.read_text(encoding="utf-8"))
    roots = {row["source_id"]: row for row in load_root_states()}
    jobs = [
        {
            "source_id": item["source_id"],
            "circuit_family": item["circuit_family"],
            "circuit_id": item["circuit_id"],
            "n_qubits": roots[item["source_id"]]["n_qubits"],
            "baseline_cost": item["baseline_cost"],
            "first_improving_horizon": item["first_improving_horizon"],
            "state": roots[item["source_id"]]["state"],
        }
        for item in ladder["improving"]
    ]
    with multiprocessing.Pool(processes=min(WORKERS, len(jobs))) as pool:
        rows = pool.map(_verify_one, jobs, chunksize=1)
    rows.sort(key=lambda row: (row["circuit_family"], row["baseline_cost"], row["source_id"]))

    path = output_root / "escape_verification.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    verdicts: dict[str, int] = {}
    for row in rows:
        verdicts[row["verdict"]] = verdicts.get(row["verdict"], 0) + 1
    summary = {
        "verified_sources": len(rows),
        "verdicts": verdicts,
        "horizons_used": sorted({row["horizon"] for row in rows}),
        "state_budget": STATE_BUDGET,
        "time_budget_seconds": TIME_BUDGET_SECONDS,
        "rule_scope": RULE_SCOPE,
        "semantic_contract": "dense unitary, global-phase quotient, n<=9 exact",
    }
    (output_root / "escape_verification_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
