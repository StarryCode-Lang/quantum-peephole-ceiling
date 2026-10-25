"""Re-run BOTH certified engines on ALL 128 fixed-panel roots with the fixed engine.

Full 128-cell successor re-certification driver.  Uses the exact frozen v14
budgets and configs (compact ``h3_b64_s200k`` = horizon 3, beam 64, state
budget 200,000; IDA* horizon 3; 30 s fail-closed time budget per cell per
engine; scope ``e44_core_v1``) and the same hash-checked root-state loader the
pilot used (``experiments.e46_window_landscape.run.load_root_states``).

Writes one JSON line per cell to the output file (default ``full_cells.jsonl``)
immediately after the cell finishes, so partial progress survives an
interrupted run; a re-invocation skips source_ids already present.  Frozen
``data/`` and ``release/`` are read-only; the only writes land in this package
directory.

Usage:
    python rerun_all_cells.py                        # all 128 cells (resume-safe)
    python rerun_all_cells.py --start 0 --end 40     # panel-order slice
    python rerun_all_cells.py --only <id1>,<id2> --out determinism_cells.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parents[4]
PKG = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e45_development_grid.run import RULE_LIBRARY  # noqa: E402
from experiments.e46_window_landscape.run import load_root_states  # noqa: E402
from src.optimisation.certified_landscape import (  # noqa: E402
    replay_actions,
    search_escape_idastar,
    search_landscape_horizons_compact,
)

FROZEN_COMPACT_CERTS = ROOT / "data" / "v14" / "e45_full_development" / "certificates.jsonl"
FROZEN_IDASTAR_CERTS = ROOT / "data" / "v14" / "e45_idastar_escape" / "certificates.jsonl"
CLASSIFICATION = ROOT / "data" / "v15" / "e45_landscape_integration" / "classification_complete.csv"
ENGINE_SOURCE_FILES = (
    ROOT / "src" / "optimisation" / "certified_landscape.py",
    ROOT / "src" / "optimisation" / "quartz_rule_import.py",
    ROOT / "src" / "optimisation" / "rewrite_exposure.py",
)
RULE_SCOPE = "e44_core_v1"
CONFIG = {
    "config_id": "h3_b64_s200k",
    "horizon": 3,
    "beam_width": 64,
    "state_budget": 200000,
    "barrier_cap": 2,
}
STATE_BUDGET = int(CONFIG["state_budget"])
HORIZON = int(CONFIG["horizon"])
TIME_BUDGET_SECONDS = 30.0
DEFAULT_OUT = PKG / "full_cells.jsonl"


def sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frozen() -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    """Frozen compact certificates, frozen IDA* certificates, classification rows."""

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
    if len(frozen_c) != 128 or len(frozen_i) != 128 or len(classification) != 128:
        raise RuntimeError(
            f"frozen_input_count_mismatch:{len(frozen_c)}:{len(frozen_i)}:{len(classification)}"
        )
    return frozen_c, frozen_i, classification


def _compact_summary(certificate: dict) -> dict:
    return {
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
    }


def _idastar_summary(certificate: dict) -> dict:
    return {
        "status": certificate["status"],
        "escape_depth": certificate["escape_depth"],
        "states_seen": certificate["states_seen"],
        "expanded": certificate["expanded"],
        "pruned": certificate["pruned"],
        "depth_iterations": certificate.get("depth_iterations", 0),
        "resource_status": certificate["resource_status"],
        "exactness_status": certificate["exactness_status"],
        "resource_reason": certificate.get("resource_reason", ""),
    }


def run_cell(root: dict, frozen_c: dict, frozen_i: dict, classification: dict) -> dict:
    """Run the fixed compact + IDA* engines on one root with the frozen budgets."""

    source_id = root["source_id"]
    state = root["state"]

    started = time.perf_counter()
    compact = search_landscape_horizons_compact(
        state,
        RULE_LIBRARY,
        (HORIZON,),
        state_budget=STATE_BUDGET,
        rule_scope=RULE_SCOPE,
        time_budget_seconds=TIME_BUDGET_SECONDS,
    )[str(HORIZON)]
    compact_seconds = time.perf_counter() - started

    started = time.perf_counter()
    idastar = search_escape_idastar(
        state,
        RULE_LIBRARY,
        HORIZON,
        state_budget=STATE_BUDGET,
        rule_scope=RULE_SCOPE,
        time_budget_seconds=TIME_BUDGET_SECONDS,
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
        "panel_index": root["panel_index"],
        "source_id": source_id,
        "source_kind": root["source_kind"],
        "circuit_family": root["circuit_family"],
        "n_qubits": root["n_qubits"],
        "root_state_sha256": root["root_state_sha256"],
        "root_kind": root["root_kind"],
        "root_gate_count": root["root_gate_count"],
        "baseline_cost": state.cost,
        "config": dict(CONFIG),
        "cell_time_budget_seconds": TIME_BUDGET_SECONDS,
        "rule_scope": RULE_SCOPE,
        "frozen_classification": {
            "classification_status": cls["classification_status"],
            "best_cost": int(cls["best_cost"]),
            "escape_depth": int(cls["escape_depth"]) if cls["escape_depth"] else None,
            "certificate_tier": cls["certificate_tier"],
            "best_cost_exactness": cls["best_cost_exactness"],
            "barrier_height": cls["barrier_height"],
        },
        "frozen_compact": {
            "status": frozen_c["status"],
            "best_cost": frozen_c["best_cost"],
            "escape_depth": frozen_c["escape_depth"],
            "barrier_height": frozen_c["barrier_height"],
            "states_seen": frozen_c["states_seen"],
            "expanded": frozen_c["expanded"],
            "pruned": frozen_c["pruned"],
            "resource_status": frozen_c["resource_status"],
            "exactness_status": frozen_c["exactness_status"],
            "resource_reason": frozen_c.get("resource_reason", ""),
        },
        "frozen_idastar": {
            "status": frozen_i["status"],
            "escape_depth": frozen_i["escape_depth"],
            "states_seen": frozen_i["states_seen"],
            "expanded": frozen_i["expanded"],
            "pruned": frozen_i["pruned"],
            "depth_iterations": frozen_i.get("depth_iterations", 0),
            "resource_status": frozen_i["resource_status"],
            "exactness_status": frozen_i["exactness_status"],
        },
        "corrected_compact": _compact_summary(compact),
        "corrected_idastar": _idastar_summary(idastar),
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
                if record.get("corrected_compact") and record.get("corrected_idastar"):
                    done.add(record["source_id"])
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--start", type=int, default=0, help="panel-order start index (inclusive)")
    parser.add_argument("--end", type=int, default=None, help="panel-order end index (exclusive)")
    parser.add_argument("--only", type=str, default="", help="comma-separated source_ids (prefix match ok)")
    parser.add_argument("--fresh", action="store_true", help="ignore existing output when resuming")
    args = parser.parse_args()

    roots = load_root_states()
    if len(roots) != 128:
        raise RuntimeError(f"panel_size_mismatch:{len(roots)}")
    for index, root in enumerate(roots):
        root["panel_index"] = index
    frozen_c, frozen_i, classification = load_frozen()

    roots = roots[args.start : args.end]
    if args.only:
        prefixes = tuple(p for p in (s.strip() for s in args.only.split(",")) if p)
        roots = [root for root in roots if root["source_id"].startswith(prefixes)]
        if not roots:
            raise RuntimeError("no_cells_match_only_filter")

    done = set() if args.fresh else completed_ids(args.out)
    pending = [root for root in roots if root["source_id"] not in done]
    print(
        f"cells selected {len(roots)}, already done {len(roots) - len(pending)}, to run {len(pending)}",
        flush=True,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    run_started = time.perf_counter()
    import gc

    with args.out.open("a", encoding="utf-8", newline="\n") as handle:
        for number, root in enumerate(pending, start=1):
            cell_started = time.perf_counter()
            record = run_cell(root, frozen_c[root["source_id"]], frozen_i[root["source_id"]], classification)
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            gc.collect()
            elapsed = time.perf_counter() - run_started
            print(
                f"[{root['panel_index']:3d}] {record['source_id'][:22]}… "
                f"cc={record['corrected_compact']['status']}/{record['corrected_compact']['best_cost']}"
                f"/d{record['corrected_compact']['escape_depth']} "
                f"ci={record['corrected_idastar']['status']}/d{record['corrected_idastar']['escape_depth']} "
                f"{record['corrected_compact']['resource_status'][:4]}/"
                f"{record['corrected_idastar']['resource_status'][:4]} "
                f"cell={time.perf_counter() - cell_started:6.2f}s total={elapsed:7.1f}s",
                flush=True,
            )
    print(f"DONE wrote {len(pending)} cells to {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
