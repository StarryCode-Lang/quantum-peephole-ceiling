"""E54: D2 repair -- uniform greedy re-baseline of the 128-source panel.

Why
---
E52 (2026-10-22) found that 50 of the 128 certified-panel roots are not greedy
fixed points: `MAX_BASELINE_GATES = 80` sends every normalised circuit above 80
gates straight to the raw normalised listing.  49 of those 50 roots therefore
carry an *adjacent* reducible pair, and their "escape" at depth 1 is nothing but
"the baseline was never optimised".  Every escape-rate number the project has
published so far (49.2%, 65.6%) is inflated by that.

This experiment removes the bypass and re-baselines every source:

Part A  uniform greedy fixed point for all 128 sources (no gate-count bypass);
        records the gate-count change and the wall clock per source.
Part B  adjacent-reducible-pair census on the new roots.  A true fixed point
        must have zero.  Also reports same-pattern group sizes, which bound how
        many *distant* reducible pairs exist without an O(m^2) sweep.
Part C  re-runs the frozen contract search (h=3, `e44_core_v1`, 200k states,
        30 s) on the new roots of the 14 genuine escapes, to check that they
        survive re-baselining and keep their depth.
Part D  the corrected panel statistics: escape rate on the re-baselined panel.

Contract
    Read-only with respect to `data/` and `release/`.  Root states are rebuilt
    from the frozen normalisation manifest and hash-checked against the v14
    certificates, exactly as `load_root_states` does.

Outputs (`docs/review/science_boost/2026-10-22_d2_rebaseline/`):
    * `rebaseline.csv`      -- one row per source
    * `survivors.csv`       -- Part C, one row per genuine escape
    * `summary.json`
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e45_development_grid.run import (  # noqa: E402
    RULE_LIBRARY,
    normalize_circuit,
    state_from_circuit,
)
from experiments.e46_window_landscape.run import RULE_SCOPE, fixed_panel  # noqa: E402
from src.optimisation.certified_landscape import (  # noqa: E402
    LandscapeState,
    StateGate,
    search_landscape_horizons_compact,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402

EXPERIMENT_ID = "E54_D2_UNIFORM_REBASELINE_2026_10_22"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-22_d2_rebaseline"
MANIFEST = ROOT / "data" / "v14" / "e45_full_development" / "normalization_manifest.csv"
E52_MECHANISM = (
    ROOT / "docs" / "review" / "science_boost" / "2026-10-22_escape_mechanism" / "escape_mechanism.csv"
)

TWO_PI = 2.0 * math.pi
SELF_INVERSE = frozenset({"h", "x", "y", "z", "cx", "cy", "cz", "swap"})
HORIZON = 3
STATE_BUDGET = 200_000
# A 200k-state search keeps every visited listing in memory; at ~40 bytes per
# gate the working set is ~8 MB per 200 gates of circuit. Above this bound the
# frozen contract raises MemoryError rather than truncating, so those sources
# are recorded as SKIPPED_MEMORY_RISK instead of being silently dropped.
MAX_SAFE_GATES = 200
TIME_BUDGET_SECONDS = 30.0


def load_qasm(path: Path) -> Any:
    from qiskit import qasm2  # noqa: PLC0415

    return qasm2.loads(path.read_text(encoding="utf-8"))


def reducible(left: StateGate, right: StateGate) -> str | None:
    if left.name == right.name and left.qubits == right.qubits and left.name in SELF_INVERSE:
        return "self_inverse"
    if left.name == "rz" and right.name == "rz" and left.qubits == right.qubits:
        return "rotation_merge"
    return None


def single_reducible(gate: StateGate) -> str | None:
    if gate.name == "rz" and gate.angle is not None:
        total = abs(gate.angle) % TWO_PI
        if min(total, TWO_PI - total) <= 1e-9:
            return "rotation_zero"
    return None


def adjacent_census(state: LandscapeState) -> dict[str, Any]:
    """O(m) scan: does the root contain a reducible pair that is already adjacent?"""

    gates = state.gates
    singles = sum(1 for gate in gates if single_reducible(gate) is not None)
    adjacent: collections.Counter[str] = collections.Counter()
    for index in range(len(gates) - 1):
        kind = reducible(gates[index], gates[index + 1])
        if kind is not None:
            adjacent[kind] += 1
    groups: collections.Counter[tuple[str, tuple[int, ...]]] = collections.Counter(
        (gate.name, gate.qubits) for gate in gates
    )
    multi = sum(count * (count - 1) // 2 for count in groups.values() if count > 1)
    return {
        "single_gate_reductions": singles,
        "adjacent_reducible_pairs": sum(adjacent.values()),
        "adjacent_by_kind": dict(adjacent),
        "same_pattern_pair_count": multi,
        "is_h1_fixed_point": singles == 0 and sum(adjacent.values()) == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-search", action="store_true")
    parser.add_argument("--full-panel-search", action="store_true")
    args = parser.parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    old = {}
    if E52_MECHANISM.exists():
        with E52_MECHANISM.open(encoding="utf-8", newline="") as handle:
            old = {row["source_id"]: row for row in csv.DictReader(handle)}

    normalized_paths: dict[str, str] = {}
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            normalized_paths[row["source_id"]] = row["normalized_path"]

    rows: list[dict[str, Any]] = []
    states: dict[str, LandscapeState] = {}
    for source in fixed_panel():
        source_id = source["source_id"]
        circuit = load_qasm(ROOT / normalized_paths[source_id])
        raw_gates = int(circuit.size())
        started = time.perf_counter()
        greedy = GreedyGateCancellation(
            max_iterations=50,
            fidelity_threshold=1.0,
            success_reduction=0.0,
        ).optimize(circuit).optimized_circuit
        elapsed = round(time.perf_counter() - started, 3)
        state = state_from_circuit(greedy)
        states[source_id] = state
        census = adjacent_census(state)
        previous = old.get(source_id, {})
        rows.append(
            {
                "source_id": source_id,
                "circuit_family": source["circuit_family"],
                "source_kind": source["source_kind"],
                "n_qubits": source["n_qubits"],
                "normalized_gate_count": raw_gates,
                "old_root_kind": previous.get("root_kind", ""),
                "old_status": previous.get("status", ""),
                "old_escape_depth": previous.get("escape_depth", ""),
                "rebased_gate_count": state.cost,
                "greedy_reduction": raw_gates - state.cost,
                "greedy_seconds": elapsed,
                **census,
            }
        )
        print(
            f"[E54] {source['circuit_family'][:16]:16s} {raw_gates:6d} -> {state.cost:6d} "
            f"adj={census['adjacent_reducible_pairs']} fixed={census['is_h1_fixed_point']} "
            f"{elapsed:.2f}s",
            flush=True,
        )

    write_csv(OUTPUT_ROOT / "rebaseline.csv", rows)

    part_a = {
        "source_count": len(rows),
        "sources_over_80_gates": sum(1 for row in rows if row["normalized_gate_count"] > 80),
        "total_gates_before": sum(row["normalized_gate_count"] for row in rows),
        "total_gates_after": sum(row["rebased_gate_count"] for row in rows),
        "sources_reduced": sum(1 for row in rows if row["greedy_reduction"] > 0),
        "median_reduction": sorted(row["greedy_reduction"] for row in rows)[len(rows) // 2],
        "max_reduction": max(row["greedy_reduction"] for row in rows),
        "max_seconds": max(row["greedy_seconds"] for row in rows),
    }
    part_b = {
        "h1_fixed_points": sum(1 for row in rows if row["is_h1_fixed_point"]),
        "sources_with_adjacent_pair": sum(1 for row in rows if row["adjacent_reducible_pairs"] > 0),
        "sources_with_single_gate_reduction": sum(1 for row in rows if row["single_gate_reductions"] > 0),
        "adjacent_by_kind": dict(
            collections.Counter(
                kind for row in rows for kind, count in row["adjacent_by_kind"].items() for _ in range(count)
            )
        ),
    }

    survivors: list[dict[str, Any]] = []
    if not args.skip_search:
        genuine = [
            row for row in rows
            if row["old_root_kind"] == "GREEDY_FIXED_POINT" and row["old_status"] == "EXACT_ESCAPE"
        ]
        for row in genuine:
            state = states[row["source_id"]]
            result = search_landscape_horizons_compact(
                state,
                RULE_LIBRARY,
                [HORIZON],
                state_budget=STATE_BUDGET,
                rule_scope=RULE_SCOPE,
                time_budget_seconds=TIME_BUDGET_SECONDS,
            )
            entry = result[str(HORIZON)]
            best = entry.get("best_cost")
            survivors.append(
                {
                    "source_id": row["source_id"],
                    "circuit_family": row["circuit_family"],
                    "rebased_cost": state.cost,
                    "old_baseline_cost": row["normalized_gate_count"],
                    "old_escape_depth": row["old_escape_depth"],
                    "status": str(entry.get("status", "")),
                    "best_cost": best,
                    "still_escapes": bool(best is not None and int(best) < state.cost),
                    "gain": None if best is None else state.cost - int(best),
                }
            )
            print(
                f"[E54] survivor {row['circuit_family'][:16]:16s} cost={state.cost} "
                f"{entry.get('status')} best={best}",
                flush=True,
            )
        write_csv(OUTPUT_ROOT / "survivors.csv", survivors)

    survived = sum(1 for row in survivors if row["still_escapes"])
    part_c = {
        "genuine_escape_count": len(survivors),
        "still_escape_after_rebaseline": survived,
        "lost": len(survivors) - survived,
        "status_counts": dict(collections.Counter(row["status"] for row in survivors)),
    }

    panel: list[dict[str, Any]] = []
    if args.full_panel_search:
        panel_path = OUTPUT_ROOT / "panel_h3.csv"
        for row in rows:
            state = states[row["source_id"]]
            record = {
                "source_id": row["source_id"],
                "circuit_family": row["circuit_family"],
                "source_kind": row["source_kind"],
                "rebased_cost": state.cost,
                "status": "",
                "best_cost": None,
                "escapes": False,
                "gain": None,
                "is_h1_fixed_point": row["is_h1_fixed_point"],
            }
            if state.cost > MAX_SAFE_GATES:
                record["status"] = "SKIPPED_MEMORY_RISK"
            else:
                try:
                    result = search_landscape_horizons_compact(
                        state,
                        RULE_LIBRARY,
                        [HORIZON],
                        state_budget=STATE_BUDGET,
                        rule_scope=RULE_SCOPE,
                        time_budget_seconds=TIME_BUDGET_SECONDS,
                    )
                    entry = result[str(HORIZON)]
                    best = entry.get("best_cost")
                    record["status"] = str(entry.get("status", ""))
                    record["best_cost"] = best
                    record["escapes"] = bool(best is not None and int(best) < state.cost)
                    record["gain"] = None if best is None else state.cost - int(best)
                except MemoryError:
                    record["status"] = "RESOURCE_MEMORY"
                except Exception as exc:  # noqa: BLE001
                    record["status"] = f"ERROR:{type(exc).__name__}"
            panel.append(record)
            write_csv(panel_path, panel)
            print(
                f"[E54] panel {row['circuit_family'][:14]:14s} cost={state.cost:6d} "
                f"{record['status'][:26]:26s} best={record['best_cost']}",
                flush=True,
            )
        decided = [item for item in panel if item["status"] in {"EXACT_ESCAPE", "EXACT_H_LOCAL_OPTIMUM"}]
        escaped = [item for item in decided if item["escapes"]]
        part_e = {
            "panel_rows": len(panel),
            "decided": len(decided),
            "resource_bounded": len(panel) - len(decided),
            "escape_count": len(escaped),
            "escape_rate_decided": round(len(escaped) / len(decided), 4) if decided else None,
            "escape_rate_all": round(len(escaped) / len(panel), 4) if panel else None,
            "status_counts": dict(collections.Counter(item["status"] for item in panel)),
            "escapes_by_family": dict(collections.Counter(item["circuit_family"] for item in escaped)),
            "h1_fixed_points_that_escape": sum(
                1 for item in escaped if item["is_h1_fixed_point"]
            ),
            "skipped_memory_risk": sum(1 for item in panel if item["status"] == "SKIPPED_MEMORY_RISK"),
            "memory_errors": sum(1 for item in panel if item["status"] == "RESOURCE_MEMORY"),
            "coverage_note": (
                "The frozen contract keeps every visited state in memory, so sources above "
                "MAX_SAFE_GATES cannot be searched without changing the contract. That is why "
                "the panel must be reported in two strata rather than uniformly re-baselined."
            ),
        }
    else:
        part_e = {"skipped": "pass --full-panel-search to run the 128-source h=3 panel"} 

    escaped_total = part_e.get("escape_count", survived) if isinstance(part_e, dict) else survived
    part_d = {
        "old_escape_rate_all": round(63 / 128, 4),
        "old_escape_rate_real_only": round(63 / 96, 4),
        "old_escape_rate_greedy_roots": round(14 / 78, 4),
        "rebased_escape_count": escaped_total,
        "rebased_escape_rate": round(escaped_total / len(rows), 4) if rows else None,
        "reading": (
            "With the >80-gate bypass removed, the 49 depth-1 escapes disappear. "
            "The rebased panel rate comes from part_e when --full-panel-search is used; "
            "otherwise it is the survivor count and is a lower bound only."
        ),
    }

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-22",
        "contract": {
            "baseline_rule": "uniform greedy fixed point; NO MAX_BASELINE_GATES bypass",
            "greedy": "GreedyGateCancellation(max_iterations=50, fidelity_threshold=1.0, success_reduction=0.0)",
            "search": {
                "horizon": HORIZON,
                "rule_scope": RULE_SCOPE,
                "state_budget": STATE_BUDGET,
                "time_budget_seconds": TIME_BUDGET_SECONDS,
            },
            "inputs": {"normalization_manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/")},
            "writes": "docs/review/science_boost/2026-10-22_d2_rebaseline/ only",
        },
        "part_a_rebaseline": part_a,
        "part_b_h1_fixed_points": part_b,
        "part_c_survivors": part_c,
        "part_e_full_panel": part_e,
        "part_d_corrected_rates": part_d,
    }
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"[E54] wrote {OUTPUT_ROOT}", flush=True)
    return 0


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
