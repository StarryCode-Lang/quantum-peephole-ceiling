"""E72: the span law -- the certified window landscape is *predicted*, not searched.

Motivation
----------
Round 15 (2026-10-26) proposed that the object indexed by every landscape result is
the *exposure span* D, not the horizon h, and left one deliverable open:

    "P0-1: draw escape_rate vs D on the 128 sources and show D explains escape
     better than h does."

A correlation would be weak evidence.  The exposability criterion (Theorem 1,
2026-10-23) makes a much sharper prediction available:

    a window's first improving move exists at horizon h  <=>  D_min + 1 <= h,

where D_min is the minimum crossing distance over all ``pair_v1``-cancellable
pairs *inside the window*.  That is a deterministic, per-window statement
computed in O(m*w) with zero search.  If it holds, the frozen E46 landscape is
not merely *correlated* with span: it is *decided* by it, and every miss is
attributable to a named cause.

Contract
--------
Read-only.  Inputs are the frozen ``data/v16/e46_window_landscape/window_results.csv``
(76,236 rows) and the hash-checked root states from
``experiments.e46_window_landscape.run.load_root_states``.  Nothing is rerun,
nothing under ``data/``/``release/``/``docs/manuscript/`` is written.

Outputs (``docs/review/science_boost/2026-10-27_span_law/``)
    window_predictions.csv  one row per frozen window row + prediction + verdict
    span_law.csv            observed vs predicted escape rate by (width, horizon, D_min)
    strata.csv              the same split by root_kind (D3 discipline)
    summary.json            confusion matrix, exact-depth agreement, law table, hashes
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from experiments.e46_window_landscape.run import (  # noqa: E402
    load_root_states,
    window_state,
)
from e56_closure_criterion import exposable_pairs  # noqa: E402

EXPERIMENT_ID = "E72_SPAN_LAW_2026_10_27"
WINDOW_RESULTS = ROOT / "data" / "v16" / "e46_window_landscape" / "window_results.csv"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-27_span_law"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- roots
    roots = {item["source_id"]: item for item in load_root_states()}
    state_by_source = {sid: item["state"] for sid, item in roots.items()}
    root_hash = {sid: item["state"].state_hash for sid, item in roots.items()}

    # ------------------------------------------------------- frozen windows
    with WINDOW_RESULTS.open(encoding="utf-8", newline="") as handle:
        frozen = list(csv.DictReader(handle))
    if not frozen:
        raise RuntimeError("window_results_empty")

    # Hash contract: the CSV pins the root state of every source.  A mismatch
    # would mean the window slice is not the slice the frozen search saw.
    hash_mismatch = sorted(
        {
            row["source_id"]
            for row in frozen
            if root_hash.get(row["source_id"]) != row["root_state_sha256"]
        }
    )

    # ------------------------------------------------ criterion per window
    # D_min depends only on (source, width, start); the horizon only decides
    # whether D_min + 1 fits in the action budget.
    cache: dict[tuple[str, int, int], dict[str, Any]] = {}
    for row in frozen:
        key = (row["source_id"], int(row["window_width"]), int(row["window_start"]))
        if key in cache:
            continue
        state = state_by_source[key[0]]
        window = window_state(state, key[2], key[1])
        pairs = exposable_pairs(window)
        if pairs:
            best = min(pairs, key=lambda item: (item["distance"], item["i"], item["rule_id"]))
            cache[key] = {
                "d_min": best["distance"],
                "d_max": max(item["distance"] for item in pairs),
                "pair_count": len(pairs),
                "rule_id": best["rule_id"],
                "window_cost_recomputed": window.cost,
            }
        else:
            cache[key] = {
                "d_min": None,
                "d_max": None,
                "pair_count": 0,
                "rule_id": "",
                "window_cost_recomputed": window.cost,
            }

    rows: list[dict[str, Any]] = []
    for row in frozen:
        sid = row["source_id"]
        width = int(row["window_width"])
        start = int(row["window_start"])
        horizon = int(row["horizon"])
        info = cache[(sid, width, start)]
        d_min = info["d_min"]
        predicted_depth = None if d_min is None else d_min + 1
        predicted_escape = predicted_depth is not None and predicted_depth <= horizon
        actual_escape = row["status"] == "EXACT_ESCAPE"
        actual_depth = int(row["escape_depth"]) if row["escape_depth"] else None
        if predicted_escape and actual_escape:
            verdict = "TP"
        elif predicted_escape and not actual_escape:
            verdict = "FP"
        elif actual_escape and not predicted_escape:
            verdict = "FN"
        else:
            verdict = "TN"
        rows.append(
            {
                "experiment_id": EXPERIMENT_ID,
                "source_id": sid,
                "circuit_family": row["circuit_family"],
                "root_kind": row["root_kind"],
                "window_width": width,
                "window_start": start,
                "window_cost": int(row["window_cost"]),
                "window_cost_recomputed": info["window_cost_recomputed"],
                "horizon": horizon,
                "d_min": "" if d_min is None else d_min,
                "d_max": "" if info["d_max"] is None else info["d_max"],
                "exposable_pair_count": info["pair_count"],
                "criterion_rule": info["rule_id"],
                "predicted_depth": "" if predicted_depth is None else predicted_depth,
                "predicted_escape": predicted_escape,
                "actual_status": row["status"],
                "actual_depth": "" if actual_depth is None else actual_depth,
                "actual_best_cost": row["best_cost"],
                "verdict": verdict,
                "depth_exact": (
                    "" if (predicted_depth is None or actual_depth is None) else predicted_depth == actual_depth
                ),
            }
        )

    cost_mismatch = sum(
        1 for row in rows if row["window_cost"] != row["window_cost_recomputed"]
    )

    # ------------------------------------------------------------ confusion
    def confusion(subset: list[dict[str, Any]]) -> dict[str, Any]:
        counts = Counter(item["verdict"] for item in subset)
        tp, fp, fn, tn = (counts.get(k, 0) for k in ("TP", "FP", "FN", "TN"))
        total = tp + fp + fn + tn
        return {
            "rows": total,
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "TN": tn,
            "precision": round(tp / (tp + fp), 6) if tp + fp else None,
            "recall": round(tp / (tp + fn), 6) if tp + fn else None,
            "accuracy": round((tp + tn) / total, 6) if total else None,
            "predicted_escapes": tp + fp,
            "actual_escapes": tp + fn,
        }

    def depth_agreement(subset: list[dict[str, Any]]) -> dict[str, Any]:
        both = [item for item in subset if item["verdict"] == "TP"]
        exact = sum(1 for item in both if item["depth_exact"] is True)
        return {
            "tp_rows": len(both),
            "depth_exact": exact,
            "rate": round(exact / len(both), 6) if both else None,
        }

    # ---------------------------------------------------------- law tables
    def law_table(subset: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[tuple[int, int, Any], list[dict[str, Any]]] = defaultdict(list)
        for item in subset:
            grouped[(item["window_width"], item["horizon"], item["d_min"])].append(item)
        table = []
        for (width, horizon, d_min), bucket in sorted(
            grouped.items(), key=lambda kv: (kv[0][0], kv[0][1], -1 if kv[0][2] == "" else kv[0][2])
        ):
            observed = sum(1 for item in bucket if item["actual_status"] == "EXACT_ESCAPE")
            table.append(
                {
                    "window_width": width,
                    "horizon": horizon,
                    "d_min": d_min,
                    "windows": len(bucket),
                    "observed_escapes": observed,
                    "observed_rate": round(observed / len(bucket), 6),
                    "criterion_says_visible": (
                        "" if d_min == "" else int(int(d_min) + 1 <= horizon)
                    ),
                }
            )
        return table

    def config_table(subset: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        for item in subset:
            grouped[(item["window_width"], item["horizon"])].append(item)
        table = []
        for (width, horizon), bucket in sorted(grouped.items()):
            observed = sum(1 for item in bucket if item["actual_status"] == "EXACT_ESCAPE")
            predicted = sum(1 for item in bucket if item["predicted_escape"])
            table.append(
                {
                    "window_width": width,
                    "horizon": horizon,
                    "windows": len(bucket),
                    "observed_escapes": observed,
                    "observed_rate": round(observed / len(bucket), 6),
                    "predicted_escapes": predicted,
                    "predicted_rate": round(predicted / len(bucket), 6),
                    "abs_rate_error": round(abs(observed - predicted) / len(bucket), 6),
                }
            )
        return table

    strata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in rows:
        strata[item["root_kind"]].append(item)

    family_fn: Counter[str] = Counter()
    family_tp: Counter[str] = Counter()
    for item in rows:
        if item["verdict"] == "FN":
            family_fn[item["circuit_family"]] += 1
        elif item["verdict"] == "TP":
            family_tp[item["circuit_family"]] += 1

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-10-27",
        "inputs": {
            "window_results": {
                "path": WINDOW_RESULTS.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(WINDOW_RESULTS),
                "rows": len(frozen),
            },
            "root_state_hash_mismatch_sources": hash_mismatch,
            "window_cost_recomputation_mismatch_rows": cost_mismatch,
        },
        "overall": confusion(rows),
        "depth_agreement": depth_agreement(rows),
        "by_root_kind": {kind: confusion(bucket) for kind, bucket in sorted(strata.items())},
        "depth_agreement_by_root_kind": {
            kind: depth_agreement(bucket) for kind, bucket in sorted(strata.items())
        },
        "config_law": config_table(rows),
        "config_law_greedy_only": config_table(
            [item for item in rows if item["root_kind"] == "GREEDY_FIXED_POINT"]
        ),
        "residual_fn_by_family": dict(family_fn.most_common()),
        "tp_by_family": dict(family_tp.most_common()),
        "contract": {
            "rule_scope": "e44_core_v1 (frozen); pair_v1 predicates only in the criterion",
            "search": "none -- criterion is O(m*w) per window",
            "read_only": ["data/", "release/", "docs/manuscript/"],
            "source": "frozen data/v16/e46_window_landscape/window_results.csv",
        },
    }

    _write_csv(
        out / "window_predictions.csv",
        rows,
        [
            "experiment_id",
            "source_id",
            "circuit_family",
            "root_kind",
            "window_width",
            "window_start",
            "window_cost",
            "window_cost_recomputed",
            "horizon",
            "d_min",
            "d_max",
            "exposable_pair_count",
            "criterion_rule",
            "predicted_depth",
            "predicted_escape",
            "actual_status",
            "actual_depth",
            "actual_best_cost",
            "verdict",
            "depth_exact",
        ],
    )
    _write_csv(
        out / "span_law.csv",
        law_table(rows),
        ["window_width", "horizon", "d_min", "windows", "observed_escapes", "observed_rate", "criterion_says_visible"],
    )
    _write_csv(
        out / "span_law_greedy_only.csv",
        law_table([item for item in rows if item["root_kind"] == "GREEDY_FIXED_POINT"]),
        ["window_width", "horizon", "d_min", "windows", "observed_escapes", "observed_rate", "criterion_says_visible"],
    )
    _write_csv(
        out / "strata.csv",
        [
            {
                "root_kind": kind,
                **confusion(bucket),
                **{f"depth_{k}": v for k, v in depth_agreement(bucket).items()},
            }
            for kind, bucket in sorted(strata.items())
        ],
        [
            "root_kind",
            "rows",
            "TP",
            "FP",
            "FN",
            "TN",
            "precision",
            "recall",
            "accuracy",
            "predicted_escapes",
            "actual_escapes",
            "depth_tp_rows",
            "depth_depth_exact",
            "depth_rate",
        ],
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (out / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": EXPERIMENT_ID,
                "generated": "2026-10-27",
                "script": "scripts/e72_span_law.py",
                "artifacts": {
                    name: sha256_file(out / name)
                    for name in sorted(
                        ["window_predictions.csv", "span_law.csv", "span_law_greedy_only.csv", "strata.csv", "summary.json"]
                    )
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(json.dumps({"overall": summary["overall"], "by_root_kind": summary["by_root_kind"],
                      "depth_agreement": summary["depth_agreement"],
                      "config_law": summary["config_law"],
                      "cost_mismatch": cost_mismatch, "hash_mismatch": hash_mismatch[:3]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
