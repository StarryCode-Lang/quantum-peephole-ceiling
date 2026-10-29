"""E80: how long must a rule be?  Two measurements of rule-length demand.

Motivation
----------
Round 19's E78 showed that on enumerable Clifford fragments the completeness
threshold equals the *instance* length (``L* = m``), with a residue of 4,664
gap-1 listings at m = 6 that no length-<=5 rule set can touch.  Two questions
were left open and are answered here.

Part A -- the genuine one-qubit Clifford group (closes D5)
    E75's "one-qubit Clifford" fragment used generators ``{h,x,z}``, which
    generate only the order-8 group ``<h,x>`` (``h`` normalises the Pauli
    group, so ``z = hxh`` adds nothing).  The one-qubit Clifford group modulo
    phase has order 24 and needs a phase gate.  This part re-measures the
    threshold on ``{h,s,x,z}`` at listing length <= 8, so the number attached
    to "one-qubit Clifford" finally refers to that group.

Part B -- rule-length demand on the real panel (P0-2 from round 19)
    E72 found 1,564 window rows where the search-free span criterion is silent
    but a certified escape exists (the *content class*).  For every such
    window this part asks the concrete question the ladder is about: among the
    actions the frozen 1,474-rule library can actually take, what is the
    shortest source-pattern length that reduces the window?  If the answer is
    2-3 everywhere, the ladder is a synthetic-fragment phenomenon; if it has a
    tail at 4-6, the ladder is visible in real circuits.

Contract
--------
Read-only.  Frozen rule library
``data/v13/e43_quartz_rule_import/generation_a/rule_library.json`` (sha256
recorded); frozen E46 window results and the hash-checked root states from
``experiments.e46_window_landscape.run.load_root_states``; E72's predictions
CSV.  Nothing under ``data/``, ``release/`` or ``docs/manuscript/`` is written.
No search beyond depth 1 on the window root: the question is which rules the
library offers, not how deep a plan is needed.

Outputs (``docs/review/science_boost/2026-10-29_rule_length_demand/``)
    part_a_price_curve.csv   threshold curve for the 24-element group
    fn_span_census.csv       one row per content-class window: min rule length
    summary.json             contract, histograms, self-checks, hashes
    MANIFEST.json            sha256 of every artifact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from experiments.e46_window_landscape.run import load_root_states, window_state  # noqa: E402
from src.optimisation.certified_landscape import legal_actions  # noqa: E402

EXPERIMENT_ID = "E80_RULE_LENGTH_DEMAND_2026_10_29"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
WINDOW_PREDICTIONS = (
    ROOT / "docs" / "review" / "science_boost" / "2026-10-27_span_law" / "window_predictions.csv"
)
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-29_rule_length_demand"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot_load:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


E75 = _load("e75_completeness_price", ROOT / "scripts" / "e75_completeness_price.py")


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


def rule_source_lengths() -> dict[str, int]:
    """``rule_id -> source gate count`` for every rule the library ships."""

    payload = json.loads(RULE_LIBRARY.read_text(encoding="utf-8"))
    table: dict[str, int] = {}
    for rule in payload["rules"]:
        source = rule.get("source") or {}
        length = source.get("gate_count")
        if isinstance(length, int):
            table[rule["rule_id"]] = length
    return table


# --------------------------------------------------------------------- Part A
def part_a(max_length: int, deadline: float) -> dict[str, Any]:
    """The genuine one-qubit Clifford group: {h,s,x,z}, listings <= max_length."""

    generators = (("h", (0,)), ("s", (0,)), ("x", (0,)), ("z", (0,)))
    allowed = {(name, tuple(qubits)) for name, qubits in generators}
    fragment = E75.Fragment("width1_clifford24", 1, generators, max_length, key_mode="fixed")

    original_legal = E75.legal_actions

    def filtered(state: Any, library: Path, scope: str) -> list[Any]:
        return [
            action
            for action in original_legal(state, library, scope)
            if all((gate.name, tuple(gate.qubits)) in allowed for gate in action.post_state.gates)
        ]

    E75.legal_actions = filtered
    try:
        cache = E75.ActionCache()
        configs = [E75.Config("base", None, 1, 0)]
        configs += [E75.Config(f"all_L2_{L}", None, 2, L) for L in range(2, max_length + 1)]
        stats: dict[str, Any] = {}
        rows_all: list[dict[str, Any]] = []
        for config in configs:
            rows, config_stats = E75.evaluate(fragment, config, cache, deadline)
            config_stats["part"] = "A_width1_clifford24"
            stats[config.name] = config_stats
            rows_all.extend(rows)
    finally:
        E75.legal_actions = original_legal

    threshold = next(
        (L for L in range(2, max_length + 1) if stats[f"all_L2_{L}"]["price"] == 0.0), None
    )
    return {
        "fragment": {
            "num_qubits": 1,
            "generators": [f"{name}{''.join(str(q) for q in qubits)}" for name, qubits in generators],
            "max_length": max_length,
            "listings": len(fragment.states),
            "classes": len(fragment.classes),
            "reducible": len(fragment.reducible),
            "c_abs_histogram": {str(k): v for k, v in sorted(Counter(fragment.c_abs.values()).items())},
        },
        "configs": stats,
        "threshold": threshold,
        "rows": rows_all,
    }


# --------------------------------------------------------------------- Part B
def _action_kind(action: Any) -> str:
    """Classify a library action by mechanism, not by rule id prefix."""

    rule_id = action.rule_id
    if "rotation_merge" in rule_id:
        return "merge"
    if rule_id.startswith("pair_v1"):
        return "cancel"
    if rule_id.startswith("exchange"):
        return "exchange"
    return "rule"


def part_b(deadline: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Shortest library rule that reduces each content-class window."""

    lengths = rule_source_lengths()
    roots = {item["source_id"]: item["state"] for item in load_root_states()}
    with WINDOW_PREDICTIONS.open(encoding="utf-8", newline="") as handle:
        predictions = [row for row in csv.DictReader(handle) if row["verdict"] == "FN"]

    seen: dict[tuple[str, int, int], dict[str, Any]] = {}
    for row in predictions:
        key = (row["source_id"], int(row["window_width"]), int(row["window_start"]))
        if key not in seen:
            seen[key] = row

    rows: list[dict[str, Any]] = []
    truncated = 0
    for index, (key, row) in enumerate(sorted(seen.items())):
        if time.perf_counter() > deadline:
            truncated = len(seen) - index
            break
        source_id, width, start = key
        state = window_state(roots[source_id], start, width)
        actions = legal_actions(state, RULE_LIBRARY, "full")
        reducing = [action for action in actions if action.cost_delta < 0]
        # Action taxonomy.  ``pair_v1.rotation_merge`` merges two rotations on the
        # same wire (cost -1); it is *not* a cancellation pair, so the exposability
        # criterion of Theorem 1 does not model it at all.  Separating it from
        # ``pair_v1`` cancellation and from ``quartz_v1`` pattern rules is what
        # makes the content-class count interpretable.
        kinds = sorted({_action_kind(action) for action in reducing})
        spans = sorted(
            {
                lengths.get(action.rule_id, 2 if action.rule_id.startswith("pair_v1") else 0)
                for action in reducing
                if _action_kind(action) == "rule"
            }
            - {0}
        )
        rows.append(
            {
                "source_id": source_id,
                "circuit_family": row["circuit_family"],
                "root_kind": row["root_kind"],
                "window_width": width,
                "window_start": start,
                "window_cost": state.cost,
                "horizon": row["horizon"],
                "actual_depth": row["actual_depth"],
                "actual_best_cost": row["actual_best_cost"],
                "reducing_action_count": len(reducing),
                "action_kinds": "|".join(kinds),
                "min_rule_length": spans[0] if spans else "",
                "max_rule_length": spans[-1] if spans else "",
                "rule_lengths": "|".join(str(s) for s in spans),
                "families": "|".join(sorted({action.family for action in reducing})),
            }
        )
    kinds_hist: Counter[str] = Counter()
    for row in rows:
        kinds_hist[row["action_kinds"] or "none"] += 1
    stats = {
        "content_windows": len(seen),
        "action_kind_histogram": dict(sorted(kinds_hist.items())),
        "scanned": len(rows),
        "truncated": truncated,
        "min_length_histogram": {
            str(k): v for k, v in sorted(Counter(int(r["min_rule_length"]) for r in rows if r["min_rule_length"] != "").items())
        },
        "no_action": sum(1 for r in rows if r["min_rule_length"] == ""),
        "by_root_kind": {
            kind: {
                str(k): v
                for k, v in sorted(
                    Counter(int(r["min_rule_length"]) for r in rows if r["root_kind"] == kind and r["min_rule_length"] != "").items()
                )
            }
            for kind in sorted({r["root_kind"] for r in rows})
        },
        "by_family": {
            family: {
                str(k): v
                for k, v in sorted(
                    Counter(int(r["min_rule_length"]) for r in rows if r["circuit_family"] == family and r["min_rule_length"] != "").items()
                )
            }
            for family in sorted({r["circuit_family"] for r in rows})
        },
    }
    return rows, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width1-max-length", type=int, default=8)
    parser.add_argument("--budget-seconds", type=float, default=5400.0)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--skip-part-a", action="store_true")
    parser.add_argument("--skip-part-b", action="store_true")
    parser.add_argument("--merge", action="store_true")
    args = parser.parse_args()
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)
    deadline = time.perf_counter() + args.budget_seconds
    started = time.perf_counter()

    part_a_result: dict[str, Any] = {}
    if not args.skip_part_a:
        part_a_result = part_a(args.width1_max_length, deadline)

    part_b_rows: list[dict[str, Any]] = []
    part_b_stats: dict[str, Any] = {}
    if not args.skip_part_b:
        part_b_rows, part_b_stats = part_b(deadline)

    checks = {
        "part_a_is_the_24_element_group": part_a_result.get("fragment", {}).get("classes") == 24
        if part_a_result
        else None,
        "part_a_threshold_defined": part_a_result.get("threshold") is not None if part_a_result else None,
        "part_b_scanned_all_windows": part_b_stats.get("truncated") == 0 if part_b_stats else None,
        "part_b_has_actions_for_most": (
            part_b_stats["no_action"] < part_b_stats["scanned"] if part_b_stats else None
        ),
    }

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-10-29",
        "purpose": "measure rule-length demand: (A) the genuine 24-element one-qubit Clifford group, (B) the content-class windows of the real panel",
        "contract": {
            "rule_library": RULE_LIBRARY.relative_to(ROOT).as_posix(),
            "rule_library_sha256": sha256_file(RULE_LIBRARY),
            "window_predictions": WINDOW_PREDICTIONS.relative_to(ROOT).as_posix(),
            "window_predictions_sha256": sha256_file(WINDOW_PREDICTIONS),
            "scope": "full (1,474 safe rules) + pair_v1 + structural exchanges",
            "read_only": ["data/", "release/", "docs/manuscript/"],
            "part_a_search": "greedy closure + monotone BFS depth <= min(gap, 3), exactly E75",
            "part_b_search": "depth 1 on the window root only; the question is which rules exist, not how deep a plan is",
            "rule_length_definition": "source.gate_count of the matched rule; pair_v1 actions count as 2",
        },
        "part_a": {k: v for k, v in part_a_result.items() if k != "rows"},
        "part_b": part_b_stats,
        "self_checks": checks,
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }

    if part_a_result:
        _write_csv(
            out / "part_a_price_curve.csv",
            list(part_a_result["configs"].values()),
            [
                "part",
                "config",
                "arity",
                "lmin",
                "lmax",
                "include_base",
                "members_reducible",
                "greedy_exact",
                "greedy_rate",
                "after_search",
                "after_search_rate",
                "failures",
                "price",
                "budget_exhausted",
            ],
        )
    if part_b_rows:
        _write_csv(
            out / "fn_span_census.csv",
            part_b_rows,
            [
                "source_id",
                "circuit_family",
                "root_kind",
                "window_width",
                "window_start",
                "window_cost",
                "horizon",
                "actual_depth",
                "actual_best_cost",
                "reducing_action_count",
                "action_kinds",
                "min_rule_length",
                "max_rule_length",
                "rule_lengths",
                "families",
            ],
        )
    # Merge with a previous run of the other part, so the two halves can be
    # executed in separate processes (part A is minutes, part B is seconds).
    merged_path = out / "summary.json"
    if args.merge and merged_path.exists():
        previous = json.loads(merged_path.read_text(encoding="utf-8"))
        for key in ("part_a", "part_b", "self_checks"):
            if summary.get(key):
                previous[key] = summary[key]
        previous["runtime_seconds"] = round(
            float(previous.get("runtime_seconds", 0.0)) + summary["runtime_seconds"], 1
        )
        summary = previous
    merged_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (out / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": EXPERIMENT_ID,
                "generated": "2026-10-29",
                "script": "scripts/e80_rule_length_demand.py",
                "artifacts": {
                    name: sha256_file(out / name)
                    for name in sorted(
                        n
                        for n in ["part_a_price_curve.csv", "fn_span_census.csv", "summary.json"]
                        if (out / n).exists()
                    )
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"self_checks": checks, "part_a": summary["part_a"], "part_b": part_b_stats}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
