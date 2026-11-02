"""E87: the completeness-price ladder was measured on a subgroup, not on the group.

Motivation
----------
Rounds 17-20 built a four-point price curve on 2-qubit Clifford fragments:

    E73  m = 4, {h,x,z} x 2 + cx01 + cx10   30.25% unreachable
    E78  m = 5, same generators              4.63%  at L = 4
    E81  m = 6, same generators              2.06%  at L = 5
    E81  m = 7, same generators              0.46%  at L = 6

and round 21's E84 then showed that ``{h,x,z}`` generates the order-8 group
``<h,x>`` on one qubit, because ``z = s^2`` cannot manufacture the missing
``s``.  On two qubits the same gap makes the fragment an **order-1,152 subgroup
of index 10**, while the 2-qubit Clifford group modulo phase has order 11,520.

Round 21 corrected the *diameter* (7 -> 9) but did not re-measure the *price*.
Every published price number is therefore a statement about a subgroup, not
about 2-qubit Clifford.  This experiment re-measures the curve on the panel's
own generator set -- ``{h,x,z,s}`` on each qubit plus both CX directions, ten
generators, the set E84 used -- and decomposes the price into its two axes.

What is measured
----------------
Part A  the E78 configuration reproduced bit-exactly (8 generators, m = 5).
        This is the control: it must return 0.423702 / 0.158621 / 0.046329 / 0.0.
Part B  the panel configuration (10 generators, m = 5), same five library
        configurations.
Part C  the decomposition.  Write the shipped library's price at budget
        ``L = 5`` as

            P_total = P_len + P_cov

        where ``P_len`` is what a *complete* length-<=5 library still costs
        (the length axis) and ``P_cov = P_total - P_len`` is what the shipped
        library costs on top of it (the coverage axis).  The same split is
        reported at ``L = 4`` so the split itself can be seen to move.
Part D  the same curve one listing length further out (m = 6) on the panel
        basis, synthetic configurations only.  The shipped library is omitted
        there for cost; the length axis is what m = 6 is for.

Contract
--------
Read-only.  Frozen rule library (sha256 recorded), E78's published summary for
the control.  Nothing under ``data/``, ``release/`` or ``docs/manuscript/`` is
written.  Search is E73/E75's contract verbatim: greedy closure plus a bounded
monotone BFS of depth <= min(gap, 3), 20,000 nodes.

The ``base`` configuration is filtered to the fragment's generator *instances*
(``(name, qubits)``), exactly as E75's ``ActionCache`` already does.  A rule
whose replacement emits a gate outside the fragment therefore contributes
nothing -- that is part of the coverage axis, and it is why the 1-qubit reading
in E80-A (82.87% price for the shipped library against 0.00% for a complete
one) is not a length statement.

Outputs (``docs/review/science_boost/2026-11-02_panel_price_recheck/``)
    price_curve.csv      one row per (part, config)
    decomposition.csv    P_total / P_len / P_cov at L = 4 and L = 5
    summary.json         contract, results, self-checks, provenance
    MANIFEST.json        sha256 of every artifact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPERIMENT_ID = "E87_PANEL_PRICE_RECHECK_2026_11_02"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
E78_SUMMARY = ROOT / "docs" / "review" / "science_boost" / "2026-10-29_width_threshold" / "summary.json"
E84_SUMMARY = ROOT / "docs" / "review" / "science_boost" / "2026-10-31_panel_diameter" / "summary.json"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-11-02_panel_price_recheck"

# E78's control values, read from the published summary at run time; the literals
# are only a fallback so the self-check still means something if the file moves.
E78_EXPECTED = {"base": 0.423702, "all_L2_3": 0.158621, "all_L2_4": 0.046329, "all_L2_5": 0.0}

SUBGROUP_GENERATORS: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("h", (0,)),
    ("h", (1,)),
    ("x", (0,)),
    ("x", (1,)),
    ("z", (0,)),
    ("z", (1,)),
    ("cx", (0, 1)),
    ("cx", (1, 0)),
)

# The panel's own basis.  ``rz(theta)`` is one native gate for every angle, so
# ``z = rz(pi)`` and ``s = rz(pi/2)`` both cost 1; ``cx`` in the basis
# translator means any control/target pair, so both directions are native
# (E84 counted 18,234 forward and 6,348 reversed CX in the frozen 128-source
# panel).  Ten generators, group order 11,520, Cayley diameter 9 (E84).
PANEL_GENERATORS: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("h", (0,)),
    ("h", (1,)),
    ("x", (0,)),
    ("x", (1,)),
    ("z", (0,)),
    ("z", (1,)),
    ("s", (0,)),
    ("s", (1,)),
    ("cx", (0, 1)),
    ("cx", (1, 0)),
)


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


def run_part(
    label: str,
    generators: tuple[tuple[str, tuple[int, ...]], ...],
    max_length: int,
    configs: list[Any],
    deadline: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    started = time.perf_counter()
    fragment = E75.Fragment(label, 2, generators, max_length, key_mode="fixed")
    cache = E75.ActionCache()
    stats: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    for config in configs:
        config_rows, config_stats = E75.evaluate(fragment, config, cache, deadline)
        config_stats["part"] = label
        stats[config.name] = config_stats
        rows.extend(config_rows)
        print(
            f"  [{label}] {config.name}: price={config_stats['price']} "
            f"reducible={config_stats['members_reducible']} "
            f"({time.perf_counter() - started:.1f}s)",
            flush=True,
        )
    meta = {
        "num_qubits": 2,
        "generators": [f"{name}{''.join(str(q) for q in qubits)}" for name, qubits in generators],
        "generator_count": len(generators),
        "max_length": max_length,
        "listings": len(fragment.states),
        "unitary_classes": len(fragment.classes),
        "reducible": len(fragment.reducible),
        "c_abs_histogram": {str(k): v for k, v in sorted(Counter(fragment.c_abs.values()).items())},
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }
    return {"meta": meta, "configs": stats}, rows


def configs_for(max_length: int, include_base: bool) -> list[Any]:
    out: list[Any] = []
    if include_base:
        out.append(E75.Config("base", None, 1, 0))
    out.extend(E75.Config(f"all_L2_{L}", None, 2, L) for L in range(2, max_length + 1))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-length", type=int, default=5)
    parser.add_argument("--panel-max-length", type=int, default=5)
    parser.add_argument("--budget-seconds", type=float, default=10800.0)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--skip-part-d", action="store_true")
    args = parser.parse_args()
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)
    deadline = time.perf_counter() + args.budget_seconds
    started = time.perf_counter()

    print("Part A: subgroup control (8 generators)", flush=True)
    part_a, rows_a = run_part(
        "A_subgroup_w2",
        SUBGROUP_GENERATORS,
        args.max_length,
        configs_for(args.max_length, include_base=True),
        deadline,
    )

    print("Part B: panel basis (10 generators)", flush=True)
    part_b, rows_b = run_part(
        "B_panel_w2",
        PANEL_GENERATORS,
        args.panel_max_length,
        configs_for(args.panel_max_length, include_base=True),
        deadline,
    )

    # ---- Part C: the two-axis decomposition -----------------------------------
    def price(part: dict[str, Any], name: str) -> float | None:
        return part["configs"].get(name, {}).get("price")

    decomposition: list[dict[str, Any]] = []
    for label, part in (("A_subgroup_w2", part_a), ("B_panel_w2", part_b)):
        for budget in (4, 5):
            total = price(part, "base")
            length = price(part, f"all_L2_{budget}")
            if total is None or length is None:
                continue
            decomposition.append(
                {
                    "part": label,
                    "budget_L": budget,
                    "unitary_classes": part["meta"]["unitary_classes"],
                    "listings": part["meta"]["listings"],
                    "p_total_base": round(total, 6),
                    "p_len_complete": round(length, 6),
                    "p_cov_shipped": round(total - length, 6),
                    "p_cov_share": round((total - length) / total, 6) if total else None,
                }
            )

    # ---- Part D: one listing length further out, panel basis ------------------
    part_d: dict[str, Any] = {}
    rows_d: list[dict[str, Any]] = []
    if not args.skip_part_d:
        print("Part D: panel basis at m = 6 (synthetic configs only)", flush=True)
        part_d, rows_d = run_part(
            "D_panel_w2_m6",
            PANEL_GENERATORS,
            args.panel_max_length + 1,
            configs_for(args.panel_max_length + 1, include_base=False),
            deadline,
        )

    # ---- self-checks ---------------------------------------------------------
    e78: dict[str, Any] = {}
    if E78_SUMMARY.exists():
        e78 = json.loads(E78_SUMMARY.read_text(encoding="utf-8")).get("part_a_width2", {}).get("configs", {})
    control = {name: (e78.get(name, {}).get("price") if e78 else E78_EXPECTED[name]) for name in E78_EXPECTED}

    # E84's Cayley BFS gives the exact size of the radius-5 ball in each group.
    # The fragment's unitary-class count must equal it: that is a cross-check
    # between two independent code paths (unitary canonicalisation of every
    # listing vs. tableau BFS over the group), and it also fixes the denominator
    # the price is measured on.
    e84_ball: dict[str, dict[int, int]] = {}
    if E84_SUMMARY.exists():
        frags = json.loads(E84_SUMMARY.read_text(encoding="utf-8")).get("fragments", {})
        for key in ("w2_round20", "panel_2q"):
            entry = frags.get(key, {})
            # E84 stores the histogram as a JSON string under "histogram"; accept
            # both shapes so a schema change upstream does not silently disable
            # the cross-check (a missing histogram makes every check below False).
            hist = entry.get("histogram") or entry.get("distance_histogram") or {}
            if isinstance(hist, str):
                hist = json.loads(hist)
            if hist:
                e84_ball[key] = {
                    r: sum(int(v) for d, v in hist.items() if int(d) <= r) for r in (5, 6)
                }

    checks = {
        "subgroup_reproduces_e78_base": price(part_a, "base") == control["base"],
        "subgroup_reproduces_e78_L3": price(part_a, "all_L2_3") == control["all_L2_3"],
        "subgroup_reproduces_e78_L4": price(part_a, "all_L2_4") == control["all_L2_4"],
        "subgroup_reproduces_e78_L5": price(part_a, "all_L2_5") == control["all_L2_5"],
        "subgroup_classes_match_e84_ball5": (
            part_a["meta"]["unitary_classes"] == e84_ball.get("w2_round20", {}).get(5)
        ),
        "panel_classes_match_e84_ball5": (
            part_b["meta"]["unitary_classes"] == e84_ball.get("panel_2q", {}).get(5)
        ),
        "panel_ball_is_larger_than_subgroup_ball": (
            part_b["meta"]["unitary_classes"] > part_a["meta"]["unitary_classes"]
        ),
        "panel_price_above_subgroup_at_L4": (price(part_b, "all_L2_4") or 0) > (price(part_a, "all_L2_4") or 1),
        # Phrased positively: the subgroup library IS length-2 complete, the panel one
        # is NOT. The second is the round's finding, so it must read as True.
        "subgroup_shipped_equals_complete_L2": price(part_a, "base") == price(part_a, "all_L2_2"),
        "panel_shipped_exceeds_complete_L2": (price(part_b, "base") or 0) > (price(part_b, "all_L2_2") or 0),
        "decomposition_is_additive": all(
            abs(row["p_len_complete"] + row["p_cov_shipped"] - row["p_total_base"]) < 1e-9 for row in decomposition
        ),
    }
    if part_d:
        checks["panel_classes_m6_match_e84_ball6"] = (
            part_d["meta"]["unitary_classes"] == e84_ball.get("panel_2q", {}).get(6)
        )
        checks["panel_length_floor_rises_with_m"] = (
            price(part_d, f"all_L2_{args.panel_max_length}") or 0
        ) > 0

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-11-02",
        "purpose": (
            "re-measure the completeness-price curve on the panel's own generator set, because "
            "every published price point used {h,x,z} per qubit, which generates an order-1,152 "
            "subgroup of the order-11,520 two-qubit Clifford group"
        ),
        "contract": {
            "rule_library": RULE_LIBRARY.relative_to(ROOT).as_posix(),
            "rule_library_sha256": sha256_file(RULE_LIBRARY),
            "control_source": E78_SUMMARY.relative_to(ROOT).as_posix() if E78_SUMMARY.exists() else None,
            "read_only": ["data/", "release/", "docs/manuscript/"],
            "search": "greedy closure (32 passes) + monotone BFS depth <= min(gap, 3), 20,000 nodes",
            "synthetic_library": "maximally powerful rule set of the given source-length class, built from the fragment's own truth table",
            "base_filter": "actions whose replacement emits a gate outside the fragment's (name, qubits) set are dropped",
            "price": "1 - (members reaching the fragment optimum) / (reducible members)",
        },
        "part_a_subgroup": part_a,
        "part_b_panel": part_b,
        "part_c_decomposition": decomposition,
        "part_d_panel_m6": part_d,
        "self_checks": checks,
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }

    all_rows = rows_a + rows_b + rows_d
    _write_csv(
        out / "price_curve.csv",
        all_rows,
        [
            "config",
            "listing",
            "cost",
            "c_abs",
            "c_closed",
            "gap_closed",
            "reached",
            "bfs_nodes",
            "bfs_path",
            "greedy_path",
        ],
    )
    _write_csv(
        out / "decomposition.csv",
        decomposition,
        [
            "part",
            "budget_L",
            "unitary_classes",
            "listings",
            "p_total_base",
            "p_len_complete",
            "p_cov_shipped",
            "p_cov_share",
        ],
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (out / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": EXPERIMENT_ID,
                "generated": "2026-11-02",
                "script": "scripts/e87_panel_price_recheck.py",
                "artifacts": {
                    name: sha256_file(out / name)
                    for name in ("price_curve.csv", "decomposition.csv", "summary.json")
                    if (out / name).exists()
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"self_checks": checks, "decomposition": decomposition}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
