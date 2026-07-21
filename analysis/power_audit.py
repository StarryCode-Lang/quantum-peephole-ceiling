"""Power audit: verify the README/experimental-design power disclosures against code.

Statistical protocol item 3 (README): "Power Analysis: Target beta > 0.80;
underpowered experiments labeled exploratory."

The per-experiment power figures disclosed in
``docs/results/experimental_design.md`` Section 12.8 were hand-written into
the document. This script regenerates them from the canonical datasets and
the canonical implementation in ``analysis/phase1_statistics/power_analysis.py``
so the disclosure table is reproducible end-to-end:

  1. For every experiment, measure the actual per-group sample size from the
     canonical CSV (smallest advertised grouping unit).
  2. Compute achieved power for the pre-registered target (two-sample
     comparison, Cohen's d = 0.5, alpha = 0.05, two-sided).
  3. Cross-check the doc-stated sample sizes and power figures against the
     same calculator (doc_reproduced_power column).
  4. Flag experiments below the beta > 0.80 target (status column).

Usage:
    python analysis/power_audit.py [--out-dir docs/review/wave1/data]

Output:
    power_audit.csv  - one row per (experiment, grouping unit)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.phase1_statistics.power_analysis import (
    calculate_power,
    nonparametric_power_analysis,
    required_sample_size,
)

DEFAULT_OUT_DIR = PROJECT_ROOT / "docs" / "review" / "wave1" / "data"

# Canonical datasets (data/DATA_CANONICAL.md).
CANON = {
    "E1": "data/v2_fixed/e01/e01_phase_transition_v2_20260613_132653.csv",
    "E2": "data/v2_fixed/e02/e02_entanglement_density_v2_20260613_130455.csv",
    "E3": "data/v2_fixed/e03/e03_scaling_v2_20260611_224540.csv",
    "E4": "data/v2_fixed/e04/e04_algorithm_comparison_v2_20260613_132653.csv",
    "E5": "data/v2_fixed/e05/e05_landscape_v2_20260613_130355.csv",
    "E10": "data/v5/e10/e10_expanded_phase1_vs_phase2_20260613_131601.csv",
    "E11": "data/v4/e11/e11_merged_powered.csv",
    "E12": "data/v4/e12/e12_compiler_baseline_e12_full_20260626_000134_nocoupling.csv",
    "E13": "data/v4/e13/e13_structural_ceiling_e13_full_20260609_043322.csv",
    "E14": "data/v5/e14/e14_extended_benchmark_e14_full_20260611_114726.csv",
    "E15": "data/v5/e15/e15_multi_compiler_e15_full_20260611_150934.csv",
    "E16": "data/v5/e16/e16_window_scaling_e16_full_20260610_142547.csv",
    "E17": "data/v5/e17/e17_connectivity_e17_full_20260610_150935.csv",
    "E18": "data/v5/e18/e18_clifford_t_e18_full_20260610_052140.csv",
    "E19": "data/v6/e19/e19_wcl_listing_full_e19_full_20260620_123825.csv",
}

# Doc-stated disclosures (experimental_design.md Section 12.8).
# (experiment, unit description, doc_n_per_group, doc_power_or_None)
DOC_CLAIMS = [
    ("E1", "per depth", 500, 0.999),
    ("E2", "per density level", 233, 0.9997),
    ("E3", "per qubit count", 1500, 0.999),
    ("E4", "per optimizer", 100, 0.940),
    ("E5", "per depth", 1000, 0.999),
    ("E10", "overall per cell", 42, 0.620),
    ("E10", "per family", 9, 0.170),
    ("E11", "per family", 24, 0.396),
    ("E12", "per optimization level", 8, 0.154),
    ("E14", "per family x optimizer cell", 17, 0.293),
    ("E15", "per compiler", 196, 0.999),
    ("E16", "per window size", 174, 0.996),
    ("E17", "per topology", 252, 0.999),
    ("E18", "per family", 48, 0.679),
]

TARGET_EFFECT = 0.5   # pre-registered medium effect (Cohen's d)
ALPHA = 0.05
POWER_TARGET = 0.80


def _min_group_n(df: pd.DataFrame, cols) -> int:
    """Smallest group size across the grouping columns."""
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return len(df)
    return int(df.groupby(cols).size().min())


def _median_group_n(df: pd.DataFrame, cols) -> float:
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return float(len(df))
    return float(df.groupby(cols).size().median())


def measure_actual_n(exp: str, df: pd.DataFrame) -> list:
    """Return list of (unit_description, min_n, median_n) measured from data."""
    rows = []
    if exp == "E1":
        rows.append(("per depth", _min_group_n(df, ["depth"]), _median_group_n(df, ["depth"])))
    elif exp == "E2":
        col = "entanglement_density" if "entanglement_density" in df.columns else "density"
        rows.append(("per density level", _min_group_n(df, [col]), _median_group_n(df, [col])))
    elif exp == "E3":
        rows.append(("per qubit count", _min_group_n(df, ["n_qubits"]), _median_group_n(df, ["n_qubits"])))
        rows.append(("per (qubit, depth) cell", _min_group_n(df, ["n_qubits", "depth"]),
                     _median_group_n(df, ["n_qubits", "depth"])))
    elif exp == "E4":
        rows.append(("per optimizer", _min_group_n(df, ["optimizer"]), _median_group_n(df, ["optimizer"])))
    elif exp == "E5":
        rows.append(("per depth", _min_group_n(df, ["depth"]), _median_group_n(df, ["depth"])))
    elif exp == "E10":
        rows.append(("overall per optimizer", _min_group_n(df, ["optimizer"]),
                     _median_group_n(df, ["optimizer"])))
        rows.append(("per family x optimizer cell",
                     _min_group_n(df, ["circuit_family", "optimizer"]),
                     _median_group_n(df, ["circuit_family", "optimizer"])))
    elif exp == "E11":
        group_cols = ["circuit_family", "optimizer"] if "optimizer" in df.columns else ["circuit_family"]
        rows.append(("per family cell", _min_group_n(df, group_cols), _median_group_n(df, group_cols)))
    elif exp == "E12":
        col = "compiler_optimization_level"
        rows.append(("per optimization level", _min_group_n(df, [col]), _median_group_n(df, [col])))
    elif exp == "E13":
        rows.append(("total records", len(df), float(len(df))))
    elif exp == "E14":
        rows.append(("per family x optimizer cell",
                     _min_group_n(df, ["circuit_family", "optimizer"]),
                     _median_group_n(df, ["circuit_family", "optimizer"])))
    elif exp == "E15":
        col = "compiler" if "compiler" in df.columns else "compiler_backend"
        rows.append(("per compiler", _min_group_n(df, [col]), _median_group_n(df, [col])))
    elif exp == "E16":
        rows.append(("per window size", _min_group_n(df, ["window_size"]),
                     _median_group_n(df, ["window_size"])))
    elif exp == "E17":
        rows.append(("per topology", _min_group_n(df, ["topology"]), _median_group_n(df, ["topology"])))
    elif exp == "E18":
        ok = df[(df.get("status", "ok") == "ok") & df["reduction"].notna()]
        rows.append(("per family (surviving rows)", _min_group_n(ok, ["circuit_family"]),
                     _median_group_n(ok, ["circuit_family"])))
    elif exp == "E19":
        rows.append(("per listing model", _min_group_n(df, ["listing_model"]),
                     _median_group_n(df, ["listing_model"])))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Power audit for protocol item 3.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Sanity anchor: the manuscript's "n = 64 per group" requirement.
    req = required_sample_size(TARGET_EFFECT, power=POWER_TARGET, alpha=ALPHA)
    print(f"[anchor] required n for d={TARGET_EFFECT}, power={POWER_TARGET}, "
          f"alpha={ALPHA}: n={req['n']} (achieved power {req['power']:.4f})")

    rows = []
    for exp, unit, doc_n, doc_power in DOC_CLAIMS:
        path = PROJECT_ROOT / CANON[exp]
        if not path.exists():
            rows.append({"experiment": exp, "unit": unit, "error": f"missing {CANON[exp]}"})
            continue
        df = pd.read_csv(path)
        measured = dict(((u, (mn, md)) for u, mn, md in measure_actual_n(exp, df)))
        # Pick the measured unit closest to the doc unit; fall back to first.
        match = None
        for u in measured:
            if u.split("(")[0].strip().lower()[:12] in unit.lower() or unit.lower()[:12] in u.lower():
                match = u
                break
        if match is None and measured:
            match = next(iter(measured))
        min_n, med_n = measured.get(match, (np.nan, np.nan))

        # Achieved power at measured n (parametric + MWU ARE approximation).
        if np.isfinite(min_n) and min_n > 1:
            pw = calculate_power(TARGET_EFFECT, int(min_n), alpha=ALPHA)
            pw_np = nonparametric_power_analysis(TARGET_EFFECT, int(min_n), int(min_n), alpha=ALPHA)
            achieved = pw["power"]
            achieved_np = pw_np["power"]
        else:
            achieved = np.nan
            achieved_np = np.nan

        # Reproduce the doc-stated power from the doc-stated n.
        doc_repro = calculate_power(TARGET_EFFECT, doc_n, alpha=ALPHA)["power"] if doc_n else np.nan

        status = "adequate" if (np.isfinite(achieved_np) and achieved_np >= POWER_TARGET) else "underpowered"
        rows.append({
            "experiment": exp,
            "unit": unit,
            "measured_unit": match,
            "doc_n": doc_n,
            "measured_min_n": min_n,
            "measured_median_n": med_n,
            "doc_power": doc_power,
            "doc_reproduced_power": round(doc_repro, 4) if np.isfinite(doc_repro) else np.nan,
            "achieved_power_parametric": round(achieved, 4) if np.isfinite(achieved) else np.nan,
            "achieved_power_mwu_are": round(achieved_np, 4) if np.isfinite(achieved_np) else np.nan,
            "power_target": POWER_TARGET,
            "status": status,
        })

    out = pd.DataFrame(rows)
    tmp = out_dir / "power_audit.csv.tmp"
    out.to_csv(tmp, index=False)
    os.replace(tmp, out_dir / "power_audit.csv")

    pd.set_option("display.width", 200)
    print(out.to_string(index=False))
    print(f"\nWrote {out_dir / 'power_audit.csv'}")
    n_under = int((out["status"] == "underpowered").sum())
    print(f"Underpowered rows: {n_under}/{len(out)} (target power >= {POWER_TARGET})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
