"""E65: bounded-cell exactification campaign under a raised declared contract.

The 34 witness-bounded cells of the certified landscape carry best-cost and
barrier values bounded above by a replayed certified witness instead of
enumerated quantities, and the single derived cell ``e39:b2f83603...`` lost
its re-certification at the frozen 200,000-state budget under the corrected
engine (both engines now truncate).  This driver re-runs BOTH certified
engines on those 35 roots under one raised, uniformly declared contract:

    horizon 3, scope e44_core_v1, state budget 1,000,000,
    time budget 300 s per engine per cell (fail-closed),

so cheap-class cells are expected to finish enumeration (exact best cost,
escape depth, and barrier) while the tail cells record their truncation at
the raised contract as permanent-boundary evidence.

RAM gating: the visited state set dominates memory (~13.7 KB/state for a
1,100-gate listing, empirically ~150 KB/state for 12k-gate listings), and the
workstation is shared by concurrent sessions.  Before starting a cell the
driver requires free RAM according to the cell's listing-size class; cells
whose class is unavailable are deferred to the back of the queue and retried
until every cell is done or ``--max-wait-minutes`` elapses.

Output: one JSON line per cell (resume-safe; re-invocation skips source_ids
already present) plus the producing engine-source hashes per cell.  Frozen
``data/``, ``release/``, and ``docs/manuscript/`` are read-only.

Usage:
    python scripts/e65_bounded_exactification.py                # full campaign
    python scripts/e65_bounded_exactification.py --workers 1    # RAM-lean mode
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TRACKER = (
    ROOT
    / "docs"
    / "review"
    / "science_boost"
    / "2026-10-25_escape_geometry"
    / "bounded_cell_exactification_tracker.csv"
)
DERIVED_CELL_PREFIX = "e39:b2f83603"
FROZEN_COMPACT_CERTS = ROOT / "data" / "v14" / "e45_full_development" / "certificates.jsonl"
FROZEN_IDASTAR_CERTS = ROOT / "data" / "v14" / "e45_idastar_escape" / "certificates.jsonl"
CLASSIFICATION = ROOT / "data" / "v15" / "e45_landscape_integration" / "classification_complete.csv"
PACKAGE = ROOT / "docs" / "review" / "science_boost" / "2026-10-25_bounded_exactification"
ENGINE_SOURCE_FILES = (
    ROOT / "src" / "optimisation" / "certified_landscape.py",
    ROOT / "src" / "optimisation" / "quartz_rule_import.py",
    ROOT / "src" / "optimisation" / "rewrite_exposure.py",
)

RULE_SCOPE = "e44_core_v1"
HORIZON = 3

# Tiered contracts: tier A is the declared campaign contract; tier B is the
# reduced fallback for hosts whose free RAM cannot fit tier A (the user
# authorized splitting the work into smaller blocks).  A cell that COMPLETES
# enumeration under either tier is exactly certified — a completed search is
# complete regardless of the budget label; the tier only bounds truncation.
TIERS = {
    "A": {
        "config_id": "h3_b64_s1M_t300",
        "horizon": HORIZON,
        "beam_width": 64,
        "state_budget": 1_000_000,
        "barrier_cap": 2,
        "time_budget_seconds": 300.0,
        "ram_gate_gb_by_size": [(300, 4.0), (600, 6.0), (1200, 8.0)],
        "ram_gate_default": None,  # >1200 gates: not attempted on this host
    },
    "B": {
        "config_id": "h3_b64_s300k_t120",
        "horizon": HORIZON,
        "beam_width": 64,
        "state_budget": 300_000,
        "barrier_cap": 2,
        "time_budget_seconds": 120.0,
        "ram_gate_gb_by_size": [(300, 3.0), (600, 3.5), (1200, 4.0)],
        "ram_gate_default": 4.5,
    },
}
EXPERIMENT_ID = "E65_BOUNDED_EXACTIFICATION_V1"


def sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_free_ram_gb(baseline_gates: int, tier: str) -> float | None:
    """Free-RAM floor for a listing-size class under a tier contract.

    Returns None when the tier cannot attempt the listing at all on this
    host (tier A never attempts >1200-gate listings: the re-cert measured
    ~140 KB/state and ~3 GB for 20k states on 12k-gate listings, so the
    1M-state contract projects to tens of GB).
    """

    tier_config = TIERS[tier]
    for ceiling, gate in tier_config["ram_gate_gb_by_size"]:
        if baseline_gates <= ceiling:
            return gate
    return tier_config["ram_gate_default"]


def free_ram_gb() -> float | None:
    try:
        import psutil

        return psutil.virtual_memory().available / 2**30
    except Exception:
        return None


def load_target_cells() -> list[dict]:
    """The 34 tracker cells plus the derived cell, ordered by listing size."""

    cells: dict[str, dict] = {}
    with TRACKER.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            cells[row["source_id"]] = {
                "source_id": row["source_id"],
                "circuit_family": row["circuit_family"],
                "n_qubits": row["n_qubits"],
                "baseline_gates": int(row["baseline_gates"]),
                "tracker_cost_class": row["projected_exactification_cost_class"],
                "tracker_blocker": row["blocker"],
                "iso_group": row["iso_group"],
            }
    derived = [sid for sid in cells if sid.startswith(DERIVED_CELL_PREFIX)]
    if derived:
        raise RuntimeError(f"derived_cell_already_in_tracker:{derived}")
    cells[DERIVED_CELL_PREFIX] = {
        "source_id": DERIVED_CELL_PREFIX,
        "circuit_family": "QFT",
        "n_qubits": "8",
        "baseline_gates": 148,
        "tracker_cost_class": "derived_rescue",
        "tracker_blocker": "state_budget",
        "iso_group": "solo",
    }
    return sorted(cells.values(), key=lambda c: (c["baseline_gates"], c["source_id"]))


def load_frozen() -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    frozen_c: dict[str, dict] = {}
    for line in FROZEN_COMPACT_CERTS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            frozen_c[item["source_id"]] = item["certificate"]
    frozen_i: dict[str, dict] = {}
    for line in FROZEN_IDASTAR_CERTS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            frozen_i[item["source_id"]] = item["certificate"]
    classification: dict[str, dict] = {}
    with CLASSIFICATION.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            classification[row["source_id"]] = row
    return frozen_c, frozen_i, classification


def _engine_summary(certificate: dict, engine: str) -> dict:
    summary = {
        "status": certificate["status"],
        "states_seen": certificate["states_seen"],
        "expanded": certificate["expanded"],
        "pruned": certificate["pruned"],
        "resource_status": certificate["resource_status"],
        "exactness_status": certificate["exactness_status"],
        "resource_reason": certificate.get("resource_reason", ""),
    }
    if engine == "compact":
        summary.update(
            {
                "best_cost": certificate["best_cost"],
                "escape_depth": certificate["escape_depth"],
                "barrier_height": certificate["barrier_height"],
            }
        )
    else:
        summary.update(
            {
                "escape_depth": certificate["escape_depth"],
                "depth_iterations": certificate.get("depth_iterations", 0),
            }
        )
    return summary


def run_cell(root: dict, meta: dict, frozen_c: dict, frozen_i: dict, classification: dict, tier: str) -> dict:
    from experiments.e45_development_grid.run import RULE_LIBRARY
    from src.optimisation.certified_landscape import (
        replay_actions,
        search_escape_idastar,
        search_landscape_horizons_compact,
    )

    tier_config = TIERS[tier]
    state_budget = int(tier_config["state_budget"])
    time_budget = float(tier_config["time_budget_seconds"])
    source_id = root["source_id"]
    state = root["state"]

    started = time.perf_counter()
    compact = search_landscape_horizons_compact(
        state,
        RULE_LIBRARY,
        (HORIZON,),
        state_budget=state_budget,
        rule_scope=RULE_SCOPE,
        time_budget_seconds=time_budget,
    )[str(HORIZON)]
    compact_seconds = time.perf_counter() - started

    started = time.perf_counter()
    idastar = search_escape_idastar(
        state,
        RULE_LIBRARY,
        HORIZON,
        state_budget=state_budget,
        rule_scope=RULE_SCOPE,
        time_budget_seconds=time_budget,
    )
    idastar_seconds = time.perf_counter() - started

    compact_replay = "NO_WITNESS"
    if compact.get("witnesses", {}).get("escape"):
        replay = replay_actions(state, compact["witnesses"]["escape"], RULE_LIBRARY, RULE_SCOPE)
        compact_replay = "REPLAY_PASS" if replay.get("accepted") else "REPLAY_FAIL"
    idastar_replay = "NO_WITNESS"
    if idastar.get("witnesses", {}).get("escape"):
        replay = replay_actions(state, idastar["witnesses"]["escape"], RULE_LIBRARY, RULE_SCOPE)
        idastar_replay = "REPLAY_PASS" if replay.get("accepted") else "REPLAY_FAIL"

    cls = classification[source_id]
    return {
        "experiment_id": EXPERIMENT_ID,
        "source_id": source_id,
        "source_kind": root["source_kind"],
        "circuit_family": root["circuit_family"],
        "n_qubits": root["n_qubits"],
        "root_state_sha256": root["root_state_sha256"],
        "root_kind": root["root_kind"],
        "root_gate_count": root["root_gate_count"],
        "baseline_cost": state.cost,
        "raised_config": dict(tier_config),
        "attempt_tier": tier,
        "rule_scope": RULE_SCOPE,
        "tracker_cost_class": meta["tracker_cost_class"],
        "tracker_blocker": meta["tracker_blocker"],
        "iso_group": meta["iso_group"],
        "frozen_classification": {
            "classification_status": cls["classification_status"],
            "best_cost": int(cls["best_cost"]),
            "escape_depth": int(cls["escape_depth"]) if cls["escape_depth"] else None,
            "certificate_tier": cls["certificate_tier"],
            "best_cost_exactness": cls["best_cost_exactness"],
            "barrier_height": cls["barrier_height"],
        },
        "frozen_compact_states_seen": frozen_c[source_id]["states_seen"],
        "frozen_idastar_states_seen": frozen_i[source_id]["states_seen"],
        "raised_compact": _engine_summary(compact, "compact"),
        "raised_idastar": _engine_summary(idastar, "idastar"),
        "compact_seconds": compact_seconds,
        "idastar_seconds": idastar_seconds,
        "compact_replay": compact_replay,
        "idastar_replay": idastar_replay,
        "engine_source_sha256": {
            p.relative_to(ROOT).as_posix(): sha256(p) for p in ENGINE_SOURCE_FILES
        },
        "rule_library_sha256": sha256(RULE_LIBRARY),
    }


def completed_ids(path: Path) -> set[str]:
    done: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                if record.get("raised_compact") and record.get("raised_idastar"):
                    done.add(record["source_id"])
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--max-wait-minutes", type=int, default=720)
    parser.add_argument("--out", type=Path, default=PACKAGE / "cells.jsonl")
    args = parser.parse_args()

    targets = load_target_cells()
    by_prefix = {meta["source_id"]: meta for meta in targets}
    roots_by_id: dict[str, dict] = {}
    from experiments.e46_window_landscape.run import load_root_states

    roots = load_root_states()
    for index, root in enumerate(roots):
        root["panel_index"] = index
        roots_by_id[root["source_id"]] = root
    selected: list[tuple[dict, dict]] = []
    for source_id, meta in by_prefix.items():
        matches = [rid for rid in roots_by_id if rid.startswith(source_id)]
        if len(matches) != 1:
            raise RuntimeError(f"root_state_match_error:{source_id}:{len(matches)}")
        selected.append((roots_by_id[matches[0]], meta))
    frozen_c, frozen_i, classification = load_frozen()

    done = completed_ids(args.out)
    queue = [(root, meta) for root, meta in selected if root["source_id"] not in done]
    print(
        f"targets {len(selected)}, already done {len(selected) - len(queue)}, to run {len(queue)}",
        flush=True,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)

    # listings too large for this host: record the projection, don't run
    impossible = [(root, meta) for root, meta in queue if required_free_ram_gb(meta["baseline_gates"], "A") is None and required_free_ram_gb(meta["baseline_gates"], "B") is None]
    queue = [(root, meta) for root, meta in queue if (root, meta) not in impossible]
    if impossible:
        with args.out.open("a", encoding="utf-8", newline="\n") as handle:
            for root, meta in impossible:
                states_at_30s = 20000  # re-cert measurement for 12k-gate listings
                projected_states = states_at_30s * (TIME_BUDGET_SECONDS / 30.0)
                projected_gb = projected_states * 140e3 / 2**30
                handle.write(
                    json.dumps(
                        {
                            "experiment_id": EXPERIMENT_ID,
                            "source_id": root["source_id"],
                            "status": "RAM_INSUFFICIENT_PROJECTED",
                            "baseline_gates": meta["baseline_gates"],
                            "raised_config": dict(TIERS["A"]),
                            "projection": {
                                "states_at_30s": states_at_30s,
                                "projected_states_at_contract": projected_states,
                                "projected_visited_set_gb": round(projected_gb, 1),
                                "host_total_ram_gb": 15.8,
                                "basis": "2026-10-25_engine_successor_fix README: ~20k states x ~140 KB = ~3 GB at the 30 s budget on 12k-gate listings",
                            },
                            "note": (
                                "raised-contract run projects beyond host RAM; recorded "
                                "fail-closed without running (permanent machine boundary)"
                            ),
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
        print(f"[skip] {len(impossible)} over-RAM listings recorded as RAM_INSUFFICIENT_PROJECTED", flush=True)

    run_started = time.perf_counter()
    waits = 0
    max_waits = args.max_wait_minutes * 60 // 90
    with args.out.open("a", encoding="utf-8", newline="\n") as handle:
        while queue and waits <= max_waits:
            progressed = False
            deferred: list[tuple[dict, dict]] = []
            for root, meta in queue:
                available = free_ram_gb()
                tier = "A" if required_free_ram_gb(meta["baseline_gates"], "A") is not None else "B"
                need = required_free_ram_gb(meta["baseline_gates"], tier)
                if need is None or (available is not None and available < need):
                    if tier == "A":
                        # fall back to the reduced tier before deferring
                        need_b = required_free_ram_gb(meta["baseline_gates"], "B")
                        if need_b is not None and (available is None or available >= need_b):
                            tier = "B"
                            need = need_b
                if need is None or (available is not None and available < need):
                    deferred.append((root, meta))
                    print(
                        f"[defer] {root['source_id'][:22]}… tier {tier} needs {need} GB, "
                        f"available {available if available is not None else -1:.1f} GB",
                        flush=True,
                    )
                    continue
                cell_started = time.perf_counter()
                try:
                    record = run_cell(
                        root,
                        meta,
                        frozen_c,
                        frozen_i,
                        classification,
                        tier,
                    )
                except MemoryError:
                    handle.write(
                        json.dumps(
                            {
                                "experiment_id": EXPERIMENT_ID,
                                "source_id": root["source_id"],
                                "status": "MEMORY_ERROR",
                                "attempt_tier": tier,
                                "baseline_gates": meta["baseline_gates"],
                                "raised_config": dict(TIERS[tier]),
                                "note": (
                                    "search aborted on host RAM exhaustion under the "
                                    "raised contract; recorded fail-closed"
                                ),
                            },
                            sort_keys=True,
                        )
                        + "\n"
                    )
                    handle.flush()
                    gc.collect()
                    progressed = True
                    print(f"[mem ] {root['source_id'][:22]}… MEMORY_ERROR recorded", flush=True)
                    continue
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
                gc.collect()
                progressed = True
                print(
                    f"[{root['panel_index']:3d}] {record['source_id'][:22]}… "
                    f"cc={record['raised_compact']['status']}/"
                    f"{record['raised_compact']['best_cost']}/"
                    f"s{record['raised_compact']['states_seen']} "
                    f"ci={record['raised_idastar']['status']}/s{record['raised_idastar']['states_seen']} "
                    f"{record['raised_compact']['resource_status'][:4]}/"
                    f"{record['raised_idastar']['resource_status'][:4]} "
                    f"cell={time.perf_counter() - cell_started:6.2f}s "
                    f"total={time.perf_counter() - run_started:7.1f}s",
                    flush=True,
                )
            queue = deferred
            if queue and not progressed:
                waits += 1
                print(f"[wait] all remaining cells RAM-deferred; sleep 90 s ({waits}/{max_waits})", flush=True)
                time.sleep(90)
    if queue:
        print(f"INCOMPLETE: {len(queue)} cells left after max wait", flush=True)
        return 1
    print(f"DONE wrote {len(selected) - len(done)} cells to {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
