"""E67: full-rule-scope pilot panel (P3, round-13 audit).

First run of the certified compact engine with ``rule_scope="full"``
(all 1,474 library rules) on the 32 E44 fixture cells (panel indices 96..127,
the last block of the frozen screening order), at the exact frozen budgets
(horizon 3, beam 64, 200k states, 30 s fail-closed).  The admissible
per-gate lower-bound pruning earns its keep in this scope: round-13 §2.2
measured little headroom in ``e44_core_v1`` and projected the real payoff
here.  The pilot answers, before any full-panel commitment: (i) wall-time
per cell, (ii) how many fixture cells remain exact, (iii) whether the
full scope changes any certified quantity vs the core scope.

Output: resume-safe JSONL + receipt in a dated review-grade package.
Frozen data/ and release/ are read-only.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PACKAGE = ROOT / "docs" / "review" / "science_boost" / "2026-10-25_full_scope_pilot"
ENGINE_SOURCE_FILES = (
    ROOT / "src" / "optimisation" / "certified_landscape.py",
    ROOT / "src" / "optimisation" / "quartz_rule_import.py",
    ROOT / "src" / "optimisation" / "rewrite_exposure.py",
)
RULE_SCOPE = "full"
HORIZON = 3
STATE_BUDGET = 200_000
TIME_BUDGET_SECONDS = 30.0
CONFIG = {
    "config_id": "h3_b64_s200k_full_scope",
    "horizon": HORIZON,
    "beam_width": 64,
    "state_budget": STATE_BUDGET,
    "barrier_cap": 2,
    "time_budget_seconds": TIME_BUDGET_SECONDS,
    "rule_scope": RULE_SCOPE,
}
EXPERIMENT_ID = "E67_FULL_SCOPE_PILOT_V1"
PILOT_START = 96
PILOT_END = 128


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def completed_ids(path: Path) -> set[str]:
    done: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                if record.get("full_compact"):
                    done.add(record["source_id"])
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=PACKAGE / "pilot_cells.jsonl")
    parser.add_argument("--start", type=int, default=PILOT_START)
    parser.add_argument("--end", type=int, default=PILOT_END)
    args = parser.parse_args()

    from experiments.e45_development_grid.run import RULE_LIBRARY
    from experiments.e46_window_landscape.run import load_root_states
    from src.optimisation.certified_landscape import (
        replay_actions,
        search_landscape_horizons_compact,
    )

    roots = load_root_states()
    if len(roots) != 128:
        raise RuntimeError(f"panel_size_mismatch:{len(roots)}")
    panel_slice = roots[args.start : args.end]
    done = completed_ids(args.out)
    pending = [r for r in panel_slice if r["source_id"] not in done]
    print(f"pilot cells {len(panel_slice)}, done {len(panel_slice) - len(pending)}, to run {len(pending)}", flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    with args.out.open("a", encoding="utf-8", newline="\n") as handle:
        for root in pending:
            state = root["state"]
            cell_started = time.perf_counter()
            certificate = search_landscape_horizons_compact(
                state,
                RULE_LIBRARY,
                (HORIZON,),
                state_budget=STATE_BUDGET,
                rule_scope=RULE_SCOPE,
                time_budget_seconds=TIME_BUDGET_SECONDS,
            )[str(HORIZON)]
            wall = time.perf_counter() - cell_started
            replay = "NO_WITNESS"
            if certificate.get("witnesses", {}).get("escape"):
                outcome = replay_actions(state, certificate["witnesses"]["escape"], RULE_LIBRARY, RULE_SCOPE)
                replay = "REPLAY_PASS" if outcome.get("accepted") else "REPLAY_FAIL"
                if replay == "REPLAY_FAIL":
                    raise RuntimeError(f"witness_replay_failed:{root['source_id']}")
            record = {
                "experiment_id": EXPERIMENT_ID,
                "panel_index": roots.index(root),
                "source_id": root["source_id"],
                "circuit_family": root["circuit_family"],
                "n_qubits": root["n_qubits"],
                "root_state_sha256": root["root_state_sha256"],
                "baseline_cost": state.cost,
                "raised_config": dict(CONFIG),
                "full_compact": {
                    "status": certificate["status"],
                    "best_cost": certificate["best_cost"],
                    "escape_depth": certificate["escape_depth"],
                    "barrier_height": certificate["barrier_height"],
                    "states_seen": certificate["states_seen"],
                    "expanded": certificate["expanded"],
                    "pruned": certificate["pruned"],
                    "resource_status": certificate["resource_status"],
                    "exactness_status": certificate["exactness_status"],
                    "resource_reason": certificate.get("resource_reason", ""),
                },
                "wall_seconds": wall,
                "witness_replay": replay,
                "engine_source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in ENGINE_SOURCE_FILES},
                "rule_library_sha256": sha256(RULE_LIBRARY),
            }
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            gc.collect()
            print(
                f"[{record['panel_index']:3d}] {root['source_id'][:22]}… "
                f"{certificate['status']}/b{certificate['best_cost']} "
                f"s{certificate['states_seen']} wall={wall:6.2f}s "
                f"total={time.perf_counter() - started:7.1f}s",
                flush=True,
            )
    print(f"DONE pilot", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
