"""Rerun reconciliation: compare rerun experiment outputs with canonical data.

Classifies each experiment as:
  IDENTICAL  - deterministic reproduction, all fields match
  EQUIVALENT - statistical consistency, minor rounding/timestamp differences
  DIVERGED   - substantive differences requiring attribution

Usage:
  python analysis/rerun_reconciliation.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_MAP = {
    "E12": "data/v4/e12/e12_compiler_baseline_e12_full_20260626_000134_nocoupling.csv",
    "E13": "data/v4/e13/e13_structural_ceiling_e13_full_20260609_043322.csv",
    "E14": "data/v5/e14/e14_extended_benchmark_e14_full_20260611_114726.csv",
    "E15": "data/v5/e15/e15_multi_compiler_e15_full_20260611_150934.csv",
    "E16": "data/v5/e16/e16_window_scaling_e16_full_20260610_142547.csv",
    "E17": "data/v5/e17/e17_connectivity_e17_full_20260610_150935.csv",
    "E18": "data/v5/e18/e18_clifford_t_e18_full_20260610_052140.csv",
    "E19": "data/v6/e19/e19_wcl_listing_full_e19_full_20260620_123825.csv",
    "E20": "data/v6/e20/multi_compiler_full.csv",
    "E21": "data/v6/e21/ceiling_aware_comparison.csv",
    "E25": "data/v6/e25/e25_industry_benchmarks_e25_industry_proxies_20260711_042550.csv",
}

RERUN_DIR = PROJECT_ROOT / "data" / "v9"

NUMERIC_COLS = ["reduction", "fidelity", "runtime_seconds", "original_size", "optimized_size"]
# runtime_seconds is inherently non-deterministic; exclude from IDENTICAL check
DETERMINISTIC_COLS = ["reduction", "fidelity", "original_size", "optimized_size"]
SORT_KEYS = ["circuit_family", "circuit_id", "n_qubits", "optimizer"]


def find_rerun(exp_id: str) -> Path | None:
    d = RERUN_DIR / exp_id.lower()
    if not d.exists():
        d2 = RERUN_DIR / exp_id
        if not d2.exists():
            return None
        d = d2
    csvs = sorted(d.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return csvs[0] if csvs else None


OVERLAP_KEYS = ["circuit_id", "optimizer", "window_size", "topology"]
# Extra scientific columns worth comparing when present (E13 schema etc.)
EXTRA_NUMERIC_COLS = [
    "gate_count_total", "baseline_gate_count", "optimized_gate_count",
    "depth", "original_depth", "optimized_depth",
    "structural_upper_bound_reduction", "observed_best_reduction",
    "observed_best_gate_count", "ceiling_gap",
    "depth_reduction", "two_qubit_reduction", "cnot_reduction",
    "structural_lower_bound", "cancellable_pair_count",
    "mergeable_rotation_count", "adjacent_commuting_pairs",
    "commutation_enabled_inverse_pairs", "commuting_block_count",
]


def reconcile_overlap(canon: pd.DataFrame, rerun: pd.DataFrame) -> dict:
    """Compare canonical vs rerun on their shared key rows.

    Used when row counts diverge (e.g. the circuit generator gained families
    since the canonical run). Answers two questions:
      1. Are same-named circuits bit-identical (input_circuit_sha256)?
      2. Do the scientific values on shared keys still agree?
    """
    keys = [c for c in OVERLAP_KEYS if c in canon.columns and c in rerun.columns]
    if "circuit_id" not in keys:
        return {"status": "OVERLAP_NOT_COMPARABLE", "reason": "no circuit_id key"}

    # Only compare rows with status ok (E17 emits transpile_error rows)
    for df in (canon, rerun):
        if "status" in df.columns:
            df.drop(df.index[df["status"] != "ok"], inplace=True)

    canon = canon.drop_duplicates(subset=keys).set_index(keys)
    rerun = rerun.drop_duplicates(subset=keys).set_index(keys)
    common = canon.index.intersection(rerun.index)
    out = {
        "keys": keys,
        "canonical_key_rows": len(canon),
        "rerun_key_rows": len(rerun),
        "common_key_rows": len(common),
    }
    if len(common) == 0:
        out["status"] = "OVERLAP_EMPTY"
        return out

    c = canon.loc[common]
    r = rerun.loc[common]

    if "input_circuit_sha256" in c.columns and "input_circuit_sha256" in r.columns:
        same_input = (c["input_circuit_sha256"].values == r["input_circuit_sha256"].values)
        out["input_circuit_identical"] = int(same_input.sum())
        out["input_circuit_changed"] = int((~same_input).sum())
    if "output_circuit_sha256" in c.columns and "output_circuit_sha256" in r.columns:
        same_output = (c["output_circuit_sha256"].values == r["output_circuit_sha256"].values)
        out["output_circuit_identical"] = int(same_output.sum())
        out["output_circuit_changed"] = int((~same_output).sum())

    num_cols = [col for col in NUMERIC_COLS + EXTRA_NUMERIC_COLS
                if col in c.columns and col in r.columns]
    diffs = {}
    worst = 0.0
    for col in num_cols:
        cv = pd.to_numeric(c[col], errors="coerce").values
        rv = pd.to_numeric(r[col], errors="coerce").values
        both = ~(np.isnan(cv) | np.isnan(rv))
        if both.sum() == 0:
            continue
        d = np.abs(cv[both] - rv[both])
        max_d = float(d.max()) if len(d) else 0.0
        n_match = int((d < 1e-9).sum())
        diffs[col] = {"max_diff": max_d, "n_match": n_match, "n_total": int(both.sum())}
        if col != "runtime_seconds":
            worst = max(worst, max_d)
    out["numeric_comparison"] = diffs
    out["worst_nonruntime_diff"] = worst

    if worst < 1e-9:
        out["status"] = "OVERLAP_IDENTICAL"
    elif worst < 1e-6:
        out["status"] = "OVERLAP_EQUIVALENT"
    else:
        out["status"] = "OVERLAP_DIVERGED"
    return out


def reconcile(exp_id: str) -> dict:
    canon_path = PROJECT_ROOT / CANONICAL_MAP.get(exp_id, "")
    if not canon_path.exists():
        return {"experiment_id": exp_id, "status": "CANONICAL_NOT_FOUND",
                "canonical_file": str(canon_path)}

    rerun_path = find_rerun(exp_id)
    if rerun_path is None:
        return {"experiment_id": exp_id, "status": "NOT_RERUN",
                "canonical_file": str(canon_path.relative_to(PROJECT_ROOT)),
                "note": "Rerun not completed within compute budget"}

    canon = pd.read_csv(canon_path)
    rerun = pd.read_csv(rerun_path)

    result = {
        "experiment_id": exp_id,
        "canonical_file": str(canon_path.relative_to(PROJECT_ROOT)),
        "rerun_file": str(rerun_path.relative_to(PROJECT_ROOT)),
        "canonical_rows": len(canon),
        "rerun_rows": len(rerun),
        "same_columns": set(canon.columns) == set(rerun.columns),
    }

    if len(canon) != len(rerun):
        result["status"] = "DIVERGED"
        result["reason"] = f"Row count mismatch: {len(canon)} vs {len(rerun)}"
        result["overlap"] = reconcile_overlap(canon, rerun)
        return result

    common_sort = [c for c in SORT_KEYS if c in canon.columns and c in rerun.columns]
    if common_sort:
        canon = canon.sort_values(common_sort).reset_index(drop=True)
        rerun = rerun.sort_values(common_sort).reset_index(drop=True)

    diffs = {}
    all_identical = True
    only_runtime_differs = True
    for col in NUMERIC_COLS:
        if col in canon.columns and col in rerun.columns:
            c = canon[col].values
            r = rerun[col].values
            if len(c) == len(r):
                diff = np.abs(c - r)
                max_d = float(diff.max()) if len(diff) else 0.0
                n_match = int((diff < 1e-9).sum())
                diffs[col] = {"max_diff": max_d, "n_match": n_match, "n_total": len(diff)}
                if col in DETERMINISTIC_COLS and n_match < len(diff):
                    all_identical = False
                    only_runtime_differs = False

    result["numeric_comparison"] = diffs

    if all_identical:
        # All deterministic columns match; check if only runtime differs
        rt = diffs.get("runtime_seconds", {})
        if rt and rt.get("n_match", 0) < rt.get("n_total", 0):
            result["status"] = "EQUIVALENT"
            result["reason"] = f"All scientific columns identical; only runtime_seconds differs (max={rt['max_diff']:.4f}s)"
        else:
            result["status"] = "IDENTICAL"
    else:
        max_det = max(d.get("max_diff", 0) for col, d in diffs.items() if col in DETERMINISTIC_COLS)
        if max_det < 1e-6:
            result["status"] = "EQUIVALENT"
            result["reason"] = f"Minor numerical differences (max={max_det:.2e}), likely rounding"
        else:
            result["status"] = "DIVERGED"
            result["reason"] = f"Substantive differences in deterministic columns (max={max_det:.6f})"

    return result


def main():
    results = []
    for exp_id in sorted(CANONICAL_MAP.keys()):
        r = reconcile(exp_id)
        results.append(r)
        status = r.get("status", "UNKNOWN")
        print(f"  {exp_id}: {status}", end="")
        if status == "IDENTICAL":
            print(f" ({r['canonical_rows']} rows, all match)")
        elif status == "EQUIVALENT":
            print(f" ({r.get('reason', '')})")
        elif status == "DIVERGED":
            print(f" ({r.get('reason', '')})")
        elif status == "NOT_RERUN":
            print(f" - {r.get('note', '')}")
        else:
            print()

    out = RERUN_DIR / "reconciliation_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults -> {out}")


if __name__ == "__main__":
    main()
