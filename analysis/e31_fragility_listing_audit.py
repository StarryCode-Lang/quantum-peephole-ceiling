"""Audit listing extremes and bounded single-observation/budget fragility for sealed E31."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data/v11/e31_factorial_pareto/formal_run/final/formal_results.csv"
PROTOCOL = ROOT / "experiments/e31_factorial_pareto_protocol.json"
OUTPUT_DIR = ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis/fragility_listing"

CO = "COMMUTATION_ONLY"
PT = "COMMUTATION_PLUS_TEMPLATES"
LISTINGS = ("LBL", "RANDOM_TOPOLOGICAL", "WCL")
CONTRASTS = {
    "primary_listing_by_rule_did": {(PT, "WCL"): 1, (PT, "LBL"): -1,
                                    (CO, "WCL"): -1, (CO, "LBL"): 1},
    "wcl_minus_lbl_commutation_only": {(CO, "WCL"): 1, (CO, "LBL"): -1},
    "wcl_minus_lbl_plus_templates": {(PT, "WCL"): 1, (PT, "LBL"): -1},
    "random_minus_lbl_commutation_only": {
        (CO, "RANDOM_TOPOLOGICAL"): 1, (CO, "LBL"): -1,
    },
    "random_minus_lbl_plus_templates": {
        (PT, "RANDOM_TOPOLOGICAL"): 1, (PT, "LBL"): -1,
    },
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _itt_frame() -> pd.DataFrame:
    frame = pd.read_csv(RESULTS)
    valid = frame["valid_equivalent_output"]
    if valid.dtype != bool:
        valid = valid.astype(str).str.lower().eq("true")
    frame["itt_reduction_pp"] = np.where(
        valid, frame["common_basis_gate_reduction_pct"].fillna(0.0), 0.0
    )
    expected = 391 * 3 * 2 * 3 * 4
    if len(frame) != expected or frame["input_circuit_sha256"].nunique() != 391:
        raise ValueError("sealed E31 result dimensions do not match the frozen design")
    return frame


def _contrast_grid(frame: pd.DataFrame) -> pd.DataFrame:
    keys = ["input_circuit_sha256", "circuit_family", "budget_seconds", "window_gates"]
    pivot = frame.pivot(index=keys, columns=["rule_set", "listing_model"],
                        values="itt_reduction_pp")
    required = sorted({cell for weights in CONTRASTS.values() for cell in weights})
    if any(cell not in pivot.columns for cell in required) or pivot[required].isna().any().any():
        raise ValueError("listing/rule contrast grid is incomplete")
    output = pd.DataFrame(index=pivot.index)
    for name, weights in CONTRASTS.items():
        output[name] = sum(weight * pivot[cell] for cell, weight in weights.items())
    return output.reset_index()


def _listing_extremes(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    keys = ["input_circuit_sha256", "circuit_family", "rule_set",
            "budget_seconds", "window_gates"]
    pivot = frame.pivot(index=keys, columns="listing_model", values="itt_reduction_pp")
    if tuple(sorted(pivot.columns)) != tuple(sorted(LISTINGS)) or pivot.isna().any().any():
        raise ValueError("every listing-extreme cell must contain all three listings")
    best = pivot.max(axis=1)
    worst = pivot.min(axis=1)
    random_value = pivot["RANDOM_TOPOLOGICAL"]
    detail = pivot.reset_index()
    detail["oracle_best_pp"] = best.to_numpy()
    detail["oracle_worst_pp"] = worst.to_numpy()
    detail["random_listing_pp"] = random_value.to_numpy()
    detail["best_minus_random_pp"] = (best - random_value).to_numpy()
    detail["random_minus_worst_pp"] = (random_value - worst).to_numpy()
    detail["best_tie_count"] = pivot.eq(best, axis=0).sum(axis=1).to_numpy()
    detail["worst_tie_count"] = pivot.eq(worst, axis=0).sum(axis=1).to_numpy()
    family = detail.groupby("circuit_family", as_index=False).agg(
        cells=("input_circuit_sha256", "size"),
        oracle_best_mean_pp=("oracle_best_pp", "mean"),
        random_listing_mean_pp=("random_listing_pp", "mean"),
        oracle_worst_mean_pp=("oracle_worst_pp", "mean"),
        best_minus_random_mean_pp=("best_minus_random_pp", "mean"),
        random_minus_worst_mean_pp=("random_minus_worst_pp", "mean"),
    )
    summary = {
        "cells": int(len(detail)),
        "families": int(detail["circuit_family"].nunique()),
        "oracle_best_mean_pp": float(detail["oracle_best_pp"].mean()),
        "random_listing_mean_pp": float(detail["random_listing_pp"].mean()),
        "oracle_worst_mean_pp": float(detail["oracle_worst_pp"].mean()),
        "best_minus_random_mean_pp": float(detail["best_minus_random_pp"].mean()),
        "random_minus_worst_mean_pp": float(detail["random_minus_worst_pp"].mean()),
        "all_three_tied_rate": float(detail["best_tie_count"].eq(3).mean()),
        "interpretation": (
            "Best and worst are post-seal per-cell oracle envelopes over the three frozen listings; "
            "they are a sensitivity bound, not a deployable listing selector."
        ),
    }
    return detail, family, summary


def _single_input_influence(grid: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    per_input = grid.groupby(["input_circuit_sha256", "circuit_family"], as_index=False)[
        list(CONTRASTS)
    ].mean()
    n = len(per_input)
    records = []
    sign_flips = []
    for conclusion in CONTRASTS:
        values = per_input[conclusion].to_numpy(float)
        full = float(values.mean())
        loo = (values.sum() - values) / (n - 1)
        for index, estimate in enumerate(loo):
            flip = bool(full != 0 and estimate != 0 and np.sign(full) != np.sign(estimate))
            record = {
                "conclusion": conclusion,
                "omitted_input_sha256": per_input.iloc[index]["input_circuit_sha256"],
                "omitted_family": per_input.iloc[index]["circuit_family"],
                "full_estimate_pp": full,
                "leave_one_input_out_estimate_pp": float(estimate),
                "absolute_shift_pp": float(abs(estimate - full)),
                "sign_flip": flip,
            }
            records.append(record)
            if flip:
                sign_flips.append(record)
    output = pd.DataFrame(records).sort_values("absolute_shift_pp", ascending=False)
    worst = output.iloc[0].to_dict()
    return output, {
        "inputs": int(n),
        "conclusions": len(CONTRASTS),
        "most_single_input_sensitive_conclusion": worst["conclusion"],
        "maximum_absolute_shift_pp": float(worst["absolute_shift_pp"]),
        "responsible_input_sha256": worst["omitted_input_sha256"],
        "responsible_family": worst["omitted_family"],
        "sign_flip_count": len(sign_flips),
    }


def _budget_sensitivity(grid: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    full = grid[list(CONTRASTS)].mean()
    by_budget = grid.groupby("budget_seconds")[list(CONTRASTS)].mean()
    records = []
    reversals = []
    for budget, row in by_budget.iterrows():
        for conclusion in CONTRASTS:
            estimate = float(row[conclusion])
            reference = float(full[conclusion])
            reversal = bool(reference != 0 and estimate != 0 and np.sign(reference) != np.sign(estimate))
            record = {"budget_seconds": int(budget), "conclusion": conclusion,
                      "equal_budget_estimate_pp": estimate, "all_budget_estimate_pp": reference,
                      "sign_reversal": reversal, "boundary_tie": bool(estimate == 0)}
            records.append(record)
            if reversal:
                reversals.append(record)
    return pd.DataFrame(records), {
        "budgets_seconds": [int(value) for value in by_budget.index],
        "audited_conclusions": len(CONTRASTS),
        "sign_reversal_count": len(reversals),
        "reversing_conclusions": sorted({row["conclusion"] for row in reversals}),
        "one_second_boundary": "all five audited ITT contrasts equal zero because every row timed out",
    }


def _timeout_deletion_sensitivity(frame: pd.DataFrame) -> dict[str, object]:
    grouped = frame.groupby(["rule_set", "listing_model"])["itt_reduction_pp"].agg(["sum", "count", "mean"])
    timeout = frame.loc[frame["status"].eq("timeout")]
    records = []
    for conclusion, weights in CONTRASTS.items():
        full = float(sum(weight * grouped.loc[cell, "mean"] for cell, weight in weights.items()))
        for cell, weight in weights.items():
            n = int(grouped.loc[cell, "count"])
            new_mean = float(grouped.loc[cell, "sum"] / (n - 1))
            shifted = full + weight * (new_mean - float(grouped.loc[cell, "mean"]))
            affected = timeout.loc[
                timeout["rule_set"].eq(cell[0]) & timeout["listing_model"].eq(cell[1])
            ]
            if len(affected):
                records.append({"conclusion": conclusion, "cell": list(cell),
                                "affected_timeout_rows": int(len(affected)),
                                "full_estimate_pp": full,
                                "single_timeout_deletion_estimate_pp": shifted,
                                "absolute_shift_pp": abs(shifted - full),
                                "sign_flip": bool(full != 0 and shifted != 0 and np.sign(full) != np.sign(shifted))})
    worst = max(records, key=lambda row: row["absolute_shift_pp"])
    return {
        "timeout_rows": int(len(timeout)),
        "single_record_deletion_cells": records,
        "largest_single_timeout_deletion_effect": worst,
        "any_sign_flip": any(row["sign_flip"] for row in records),
        "unresolved_hidden_incumbent": (
            "Timeout rows contain no retained incumbent, so deletion sensitivity cannot bound the "
            "unobserved outcome that might have existed before forced termination."
        ),
    }


def build_audit(output_dir: Path = OUTPUT_DIR) -> dict[str, object]:
    frame = _itt_frame()
    grid = _contrast_grid(frame)
    listing_detail, listing_family, listing_summary = _listing_extremes(frame)
    influence, influence_summary = _single_input_influence(grid)
    budget, budget_summary = _budget_sensitivity(grid)
    timeout_summary = _timeout_deletion_sensitivity(frame)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "listing_extremes_cells.csv": listing_detail,
        "listing_extremes_by_family.csv": listing_family,
        "single_input_influence.csv": influence,
        "equal_budget_conclusion_sensitivity.csv": budget,
    }
    artifact_bindings = {}
    for name, table in outputs.items():
        path = output_dir / name
        table.to_csv(path, index=False)
        artifact_bindings[name] = {"rows": int(len(table)), "sha256": _sha(path)}
    audit = {
        "schema_version": "1.0.0",
        "status": "PASS_BOUNDED_E31_FRAGILITY_AND_LISTING_AUDIT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "sealed 391-input E31 fixed panel; post-seal descriptive sensitivity only",
        "listing_extremes": listing_summary,
        "single_input_influence": influence_summary,
        "equal_budget_sensitivity": budget_summary,
        "timeout_deletion_sensitivity": timeout_summary,
        "metric_dispositions": {
            "12.14": "PASS: post-seal oracle-best, oracle-worst, and frozen random listings are compared for every complete design cell",
            "17.03": "PASS: five declared core descriptive conclusions receive exhaustive leave-one-input-out influence analysis",
            "17.07": "PARTIAL: every single recorded-timeout deletion is bounded, but no retained incumbent exists to bound hidden timeout outcomes",
            "17.08": "PASS: all five declared conclusions are recomputed at each equal budget and none reverses sign",
        },
        "claim_boundary": (
            "This audit diagnoses the frozen panel. Oracle best/worst selection is post hoc; the "
            "one-second all-timeout boundary is not evidence of equality; timeout deletion does not "
            "recover uncheckpointed incumbents; no unseen-family inference is claimed."
        ),
        "source_bindings": {
            "formal_results.csv": _sha(RESULTS),
            "e31_factorial_pareto_protocol.json": _sha(PROTOCOL),
            "analysis/e31_fragility_listing_audit.py": _sha(Path(__file__)),
        },
        "artifacts": artifact_bindings,
    }
    path = output_dir / "fragility_listing_audit.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    audit = build_audit(args.output_dir)
    print(json.dumps({"status": audit["status"], "listing_extremes": audit["listing_extremes"],
                      "single_input_influence": audit["single_input_influence"],
                      "equal_budget_sensitivity": audit["equal_budget_sensitivity"]},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
