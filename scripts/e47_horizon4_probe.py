"""E47 probe: does the certified horizon-3 local-optimum classification survive h=4?

Motivation
----------
The v15 integration classifies 65 of the 128 fixed-panel sources as
``EXACT_H_LOCAL_OPTIMUM`` at horizon 3 with rule scope ``e44_core_v1``.  Horizon
3 is a *declared* bound, not a property of the circuit: a state can be an exact
h=3 local optimum and still admit a cost-reducing path of length 4.  The
library-wide maximum single-action reduction is 2 gates, so h=3 bounds the
reachable gain at 6 gates; h=4 bounds it at 8.

This probe re-searches every one of the 65 horizon-3 local optima at horizon 4
under the *same* resource contract as the frozen v14 panel
(``state_budget = 200000``, ``time_budget_seconds = 30``, scope
``e44_core_v1``) and records one of three outcomes per source:

* ``H4_CERTIFIED_LOCAL_OPTIMUM`` -- h=4 completed exactly with no escape;
* ``H4_ESCAPE_FOUND``            -- a cost-reducing path of length <= 4 exists;
* ``H4_RESOURCE_BOUNDED``        -- the budget was exhausted, no claim made.

Root states are rebuilt by ``experiments.e46_window_landscape.run.load_root_states``,
which hash-checks every root against the frozen v14 certificate, so this probe
adds evidence without touching any frozen package.

Read-only with respect to ``data/`` and ``release/``; all outputs are written
under ``docs/review/science_boost/2026-10-19_horizon4_probe/``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing
import sys
import time
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
    search_landscape_horizons_compact,
)

EXPERIMENT_ID = "E47_HORIZON4_PROBE_2026_10_19"
CLASSIFICATION = ROOT / "data" / "v15" / "e45_landscape_integration" / "classification_complete.csv"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-19_horizon4_probe"

STATE_BUDGET = 200_000
TIME_BUDGET_SECONDS = 30.0
PROBE_HORIZONS = (4,)
REFERENCE_HORIZON = 3
WORKERS = 8


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _probe_one(payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    result = search_landscape_horizons_compact(
        payload["state"],
        RULE_LIBRARY,
        PROBE_HORIZONS,
        state_budget=STATE_BUDGET,
        rule_scope=RULE_SCOPE,
        time_budget_seconds=TIME_BUDGET_SECONDS,
    )
    h4 = result[str(max(PROBE_HORIZONS))]
    status = str(h4.get("status", ""))
    if status == "EXACT_H_LOCAL_OPTIMUM":
        outcome = "H4_CERTIFIED_LOCAL_OPTIMUM"
    elif status == "EXACT_ESCAPE":
        outcome = "H4_ESCAPE_FOUND"
    else:
        outcome = "H4_RESOURCE_BOUNDED"
    return {
        "experiment_id": EXPERIMENT_ID,
        "source_id": payload["source_id"],
        "source_kind": payload["source_kind"],
        "circuit_family": payload["circuit_family"],
        "n_qubits": payload["n_qubits"],
        "baseline_cost": payload["baseline_cost"],
        "reference_horizon": REFERENCE_HORIZON,
        "reference_classification": payload["classification_status"],
        "probe_horizon": max(PROBE_HORIZONS),
        "probe_status": status,
        "probe_outcome": outcome,
        "probe_escape_depth": h4.get("escape_depth"),
        "probe_best_cost": h4.get("best_cost"),
        "probe_barrier_height": h4.get("barrier_height"),
        "probe_resource_reason": h4.get("resource_reason", ""),
        "probe_elapsed_seconds": round(time.perf_counter() - started, 3),
        "state_budget": STATE_BUDGET,
        "time_budget_seconds": TIME_BUDGET_SECONDS,
        "rule_scope": RULE_SCOPE,
        "root_state_sha256": payload["root_state_sha256"],
    }


def run(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    roots = {row["source_id"]: row for row in load_root_states()}
    with CLASSIFICATION.open(encoding="utf-8", newline="") as handle:
        panel = list(csv.DictReader(handle))

    local_optima = [
        row for row in panel if row["classification_status"] == "EXACT_H_LOCAL_OPTIMUM"
    ]
    jobs: list[dict[str, Any]] = []
    for row in local_optima:
        root = roots[row["source_id"]]
        jobs.append(
            {
                "source_id": row["source_id"],
                "source_kind": row["source_kind"],
                "circuit_family": row["circuit_family"],
                "n_qubits": int(row["n_qubits"]),
                "baseline_cost": int(row["baseline_cost"]),
                "classification_status": row["classification_status"],
                "root_state_sha256": row["input_circuit_sha256"],
                "state": root["state"],
            }
        )

    started = time.perf_counter()
    with multiprocessing.Pool(processes=min(WORKERS, len(jobs))) as pool:
        rows = pool.map(_probe_one, jobs, chunksize=1)
    elapsed = time.perf_counter() - started

    rows.sort(key=lambda row: (row["source_kind"], row["circuit_family"], row["source_id"]))
    csv_path = output_root / "horizon4_probe_rows.csv"
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    def count(predicate) -> int:
        return sum(1 for row in rows if predicate(row))

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-10-19",
        "probe": {
            "horizon": max(PROBE_HORIZONS),
            "reference_horizon": REFERENCE_HORIZON,
            "state_budget": STATE_BUDGET,
            "time_budget_seconds": TIME_BUDGET_SECONDS,
            "rule_scope": RULE_SCOPE,
            "rule_library": str(RULE_LIBRARY.relative_to(ROOT)),
            "rule_library_sha256": sha256(RULE_LIBRARY),
            "panel_source": str(CLASSIFICATION.relative_to(ROOT)),
            "panel_source_sha256": sha256(CLASSIFICATION),
            "probed_sources": len(rows),
            "wall_clock_seconds": round(elapsed, 3),
        },
        "outcome_counts": {
            "H4_CERTIFIED_LOCAL_OPTIMUM": count(lambda r: r["probe_outcome"] == "H4_CERTIFIED_LOCAL_OPTIMUM"),
            "H4_ESCAPE_FOUND": count(lambda r: r["probe_outcome"] == "H4_ESCAPE_FOUND"),
            "H4_RESOURCE_BOUNDED": count(lambda r: r["probe_outcome"] == "H4_RESOURCE_BOUNDED"),
        },
        "by_source_kind": {
            kind: {
                "probed": count(lambda r, k=kind: r["source_kind"] == k),
                "certified": count(lambda r, k=kind: r["source_kind"] == k and r["probe_outcome"] == "H4_CERTIFIED_LOCAL_OPTIMUM"),
                "escape": count(lambda r, k=kind: r["source_kind"] == k and r["probe_outcome"] == "H4_ESCAPE_FOUND"),
                "bounded": count(lambda r, k=kind: r["source_kind"] == k and r["probe_outcome"] == "H4_RESOURCE_BOUNDED"),
            }
            for kind in sorted({row["source_kind"] for row in rows})
        },
        "by_cost_band": {
            band: {
                "probed": count(lambda r, b=band: _band(r["baseline_cost"]) == b),
                "certified": count(lambda r, b=band: _band(r["baseline_cost"]) == b and r["probe_outcome"] == "H4_CERTIFIED_LOCAL_OPTIMUM"),
                "escape": count(lambda r, b=band: _band(r["baseline_cost"]) == b and r["probe_outcome"] == "H4_ESCAPE_FOUND"),
                "bounded": count(lambda r, b=band: _band(r["baseline_cost"]) == b and r["probe_outcome"] == "H4_RESOURCE_BOUNDED"),
            }
            for band in ("cost_le_2", "cost_3_to_9", "cost_ge_10")
        },
        "escape_sources": [
            {
                "source_id": row["source_id"],
                "circuit_family": row["circuit_family"],
                "baseline_cost": row["baseline_cost"],
                "escape_depth": row["probe_escape_depth"],
                "best_cost": row["probe_best_cost"],
            }
            for row in rows
            if row["probe_outcome"] == "H4_ESCAPE_FOUND"
        ],
        "bounded_sources": [
            {
                "source_id": row["source_id"],
                "circuit_family": row["circuit_family"],
                "baseline_cost": row["baseline_cost"],
                "resource_reason": row["probe_resource_reason"],
            }
            for row in rows
            if row["probe_outcome"] == "H4_RESOURCE_BOUNDED"
        ],
        "claim_boundary": (
            "Every row is a finite-horizon statement under the frozen rule scope and the "
            "declared state/time budget. H4_RESOURCE_BOUNDED is a resource boundary, not a "
            "negative result. No frozen v14/v15 package is read-modify-written."
        ),
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def _band(cost: int) -> str:
    if cost <= 2:
        return "cost_le_2"
    if cost < 10:
        return "cost_3_to_9"
    return "cost_ge_10"


LADDER_HORIZONS = (3, 4, 5, 6, 7, 8)
LADDER_STATE_BUDGET = 200_000
LADDER_TIME_BUDGET_SECONDS = 20.0


def _ladder_one(payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    result = search_landscape_horizons_compact(
        payload["state"],
        RULE_LIBRARY,
        LADDER_HORIZONS,
        state_budget=LADDER_STATE_BUDGET,
        rule_scope=RULE_SCOPE,
        time_budget_seconds=LADDER_TIME_BUDGET_SECONDS,
    )
    row: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "source_id": payload["source_id"],
        "circuit_family": payload["circuit_family"],
        "circuit_id": payload["circuit_id"],
        "n_qubits": payload["n_qubits"],
        "baseline_cost": payload["baseline_cost"],
        "reference_classification": payload["classification_status"],
        "ladder_state_budget": LADDER_STATE_BUDGET,
        "ladder_time_budget_seconds": LADDER_TIME_BUDGET_SECONDS,
        "ladder_elapsed_seconds": None,
    }
    for horizon in LADDER_HORIZONS:
        cell = result[str(horizon)]
        row[f"h{horizon}_status"] = cell.get("status", "")
        row[f"h{horizon}_best_cost"] = cell.get("best_cost")
        row[f"h{horizon}_escape_depth"] = cell.get("escape_depth")
        row[f"h{horizon}_resource_reason"] = cell.get("resource_reason", "")
    row["ladder_elapsed_seconds"] = round(time.perf_counter() - started, 3)
    return row


def run_ladder(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    roots = {row["source_id"]: row for row in load_root_states()}
    with CLASSIFICATION.open(encoding="utf-8", newline="") as handle:
        panel = list(csv.DictReader(handle))
    jobs = [
        {
            "source_id": row["source_id"],
            "circuit_family": row["circuit_family"],
            "circuit_id": row["circuit_id"],
            "n_qubits": int(row["n_qubits"]),
            "baseline_cost": int(row["baseline_cost"]),
            "classification_status": row["classification_status"],
            "state": roots[row["source_id"]]["state"],
        }
        for row in panel
        if row["classification_status"] == "EXACT_H_LOCAL_OPTIMUM" and row["source_kind"] == "e39"
    ]
    with multiprocessing.Pool(processes=min(WORKERS, len(jobs))) as pool:
        rows = pool.map(_ladder_one, jobs, chunksize=1)
    rows.sort(key=lambda row: (row["circuit_family"], row["baseline_cost"], row["source_id"]))
    path = output_root / "horizon_ladder_rows.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    def best(row: dict[str, Any]) -> int | None:
        values = [row.get(f"h{h}_best_cost") for h in LADDER_HORIZONS]
        values = [int(v) for v in values if v not in (None, "")]
        return min(values) if values else None

    improving = [
        {
            "source_id": row["source_id"],
            "circuit_family": row["circuit_family"],
            "circuit_id": row["circuit_id"],
            "baseline_cost": row["baseline_cost"],
            "h3_best_cost": row.get("h3_best_cost"),
            "ladder_best_cost": best(row),
            "first_improving_horizon": next(
                (
                    h
                    for h in LADDER_HORIZONS
                    if row.get(f"h{h}_best_cost") not in (None, "")
                    and int(row[f"h{h}_best_cost"]) < int(row["baseline_cost"])
                ),
                None,
            ),
        }
        for row in rows
        if best(row) is not None and int(best(row)) < int(row["baseline_cost"])
    ]
    summary = {
        "experiment_id": EXPERIMENT_ID + "_LADDER",
        "horizons": list(LADDER_HORIZONS),
        "state_budget": LADDER_STATE_BUDGET,
        "time_budget_seconds": LADDER_TIME_BUDGET_SECONDS,
        "sources": len(rows),
        "sources_with_lower_best_cost_than_root": len(improving),
        "improving": improving,
        "claim_boundary": (
            "Best cost is the minimum over the horizons that completed exactly; a "
            "resource-bounded cell contributes no value. This is not a global optimum."
        ),
    }
    (output_root / "ladder_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--ladder", action="store_true", help="run the horizon ladder instead of the h=4 probe")
    args = parser.parse_args()
    summary = run_ladder(args.output_root) if args.ladder else run(args.output_root)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
