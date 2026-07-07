#!/usr/bin/env python3
"""
E18 Analysis: Survivor Bias and Failure Rate Reporting (review H7).

The E18 Clifford+T experiment has a non-trivial decompose-error rate
(circuits that cannot be translated to the Clifford+T basis).  Any
analysis that drops these rows and reports statistics on the surviving
subset suffers from **survivor bias**: the reported reductions only
apply to "easy-to-decompose" circuits.

This script:
  1. Reports the total, successful, and failed row counts.
  2. Reports the failure rate per circuit family and per optimizer.
  3. Emits a survivor-bias warning suitable for inclusion in the manuscript.
  4. Saves a summary CSV with both "full cohort" and "survivor subset"
     statistics so the manuscript can report both transparently.

Usage:
    python scripts/e18_survivor_bias_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "v5" / "e18"
OUTPUT_PATH = DATA_DIR / "e18_survivor_bias_report.csv"


def main() -> int:
    csv_files = sorted(DATA_DIR.glob("e18_clifford_t_*.csv"))
    if not csv_files:
        print("ERROR: no E18 CSV found", file=sys.stderr)
        return 1
    df = pd.read_csv(csv_files[-1])
    print(f"Loaded {len(df)} rows from {csv_files[-1].name}")

    # Identify failed rows: status != 'ok' or reduction is NaN.
    failed = df[(df.get("status", "ok") != "ok") | df["reduction"].isna()]
    ok = df.drop(failed.index)
    total = len(df)
    n_fail = len(failed)
    n_ok = len(ok)
    fail_rate = n_fail / total if total else 0.0

    print(f"\n=== E18 Failure Rate (review H7) ===")
    print(f"Total rows:        {total}")
    print(f"Successful (ok):   {n_ok} ({100*n_ok/total:.1f}%)")
    print(f"Failed (decompose_error): {n_fail} ({100*fail_rate:.1f}%)")

    # Per-family failure rate.
    print(f"\n=== Per-family failure rate ===")
    for fam, grp in df.groupby("circuit_family"):
        fr = grp["reduction"].isna().sum()
        print(f"  {fam}: {fr}/{len(grp)} failed ({100*fr/len(grp):.1f}%)")

    # Per-optimizer failure rate.
    print(f"\n=== Per-optimizer failure rate ===")
    for opt, grp in df.groupby("optimizer"):
        fr = grp["reduction"].isna().sum()
        print(f"  {opt}: {fr}/{len(grp)} failed ({100*fr/len(grp):.1f}%)")

    # Survivor bias summary.
    print(f"\n=== Survivor bias warning ===")
    print(
        "WARNING (review H7): The analysis subset of "
        f"{n_ok}/{total} rows ({100*n_ok/total:.1f}%) excludes circuits "
        "that failed Clifford+T decomposition.  Statistics computed on "
        "this subset suffer from SURVIVOR BIAS: the reported reductions "
        "apply only to 'easy-to-decompose' circuits and may not generalize "
        "to the full circuit population.  The manuscript MUST report the "
        f"complete failure rate ({100*fail_rate:.1f}%) and state that "
        "conclusions are conditional on successful decomposition."
    )

    # Save summary CSV.
    rows = []
    for opt in df["optimizer"].dropna().unique():
        for label, subset in [("full_cohort", df[df["optimizer"] == opt]),
                               ("survivor_subset", ok[ok["optimizer"] == opt])]:
            r = subset["reduction"].dropna()
            rows.append({
                "optimizer": opt,
                "cohort": label,
                "n_total": len(subset),
                "n_with_reduction": len(r),
                "n_failed": len(subset) - len(r),
                "failure_rate": (len(subset) - len(r)) / len(subset) if len(subset) else 0,
                "mean_reduction": float(r.mean()) if len(r) else None,
                "std_reduction": float(r.std()) if len(r) > 1 else None,
                "median_reduction": float(r.median()) if len(r) else None,
            })
    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSummary saved to {OUTPUT_PATH}")
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
