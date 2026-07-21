"""Outlier scan across canonical experiment datasets.

Screens the primary metric columns (reduction, fidelity, runtime) of every
canonical CSV for statistical outliers and physically impossible values, then
classifies each finding:

  explainable     - matches a documented, understood pattern:
                      * E18 fidelity == 0 rows (Clifford+T decompose failures,
                        docs/results/e18_survivor_bias.md)
                      * negative reduction in multi-compiler data (E15/E20),
                        i.e. gate-count inflation from basis-gate translation
                        (manuscript Sec. 6.3 footnote)
                      * negative reduction in E29 baseline algorithms
                        (RLS/SA/GA inflate gate count at fidelity 1.0; E29 is
                        the multi-seed robustness check for E04)
                      * fidelity == 0 rows whose success flag is False
                        (failed trials, e.g. E14 at n_qubits >= 10)
  benign          - not a validity issue:
                      * fidelity above 1.0 by <= 1e-9 (floating-point epsilon
                        from statevector overlaps; observed max 4.4e-15)
                      * in-range statistical tail values (heavy-tailed
                        runtime distributions; reduction/fidelity tails that
                        stay inside the physical range)
  needs-attention - hard range violations (fidelity outside [0,1] beyond
                    float epsilon, reduction > 1), undocumented negative
                    reductions, or column-integrity defects.

Detection rules (per experiment x metric):
  * hard range checks with 1e-9 float tolerance
  * Z-score: |z| > 4 within the experiment's metric distribution
  * IQR: outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR]
  * column integrity: status columns constant across the whole file

Usage:
    python analysis/outlier_scan.py [--out-dir docs/review/wave1/data]

Output:
    outlier_scan.csv - one row per (experiment, metric, rule) with counts,
                       classification, rationale and example rows.
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
    "E20": "data/v6/e20/multi_compiler_full.csv",
    "E22": "data/v7/e22/e22_gate_shuffle_ablation.csv",
    "E24": "data/v7/e24/e24_theorem7_results.csv",
    "E27": "data/v7/e19_extended/e19_wcl_full_family.csv",
    "E29": "data/v7/e29/e29_multi_seed_e04_full.csv",
}

METRIC_CANDIDATES = {
    "reduction": ["reduction", "gate_reduction"],
    "fidelity": ["fidelity"],
    "runtime_seconds": ["runtime_seconds", "compilation_time_seconds"],
}

# Experiments where negative reduction is a documented/expected inflation
# pattern, with the specific rationale.
NEG_RED_EXPLAINABLE = {
    "E4": ("baseline metaheuristic inflation (SA/GA can increase gate count; "
           "same mechanism quantified multi-seed in E29)"),
    "E12": ("documented Qiskit gate-count inflation from basis-gate "
            "translation at low optimization levels (manuscript Sec. 6.3 footnote)"),
    "E15": ("documented gate-count inflation from basis-gate translation "
            "(manuscript Sec. 6.3 footnote)"),
    "E20": ("documented gate-count inflation from basis-gate translation "
            "(manuscript Sec. 6.3 footnote)"),
    "E29": ("baseline metaheuristic inflation (RLS/SA/GA increase gate count "
            "at fidelity 1.0; E29 is the multi-seed robustness check for E04)"),
}
Z_THRESH = 4.0
IQR_K = 1.5
FP_TOL = 1e-9
MAX_ROWS_PER_CELL = 25  # cap reported example ids per (experiment, metric, rule)

_CLASS_RANK = {"benign": 0, "explainable": 1, "needs-attention": 2}


def _pick_col(df: pd.DataFrame, candidates) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _classify_row(exp: str, metric: str, rule: str, value: float,
                  success: object) -> tuple[str, str]:
    """Per-row classification; worst case across rows wins at aggregation."""
    if rule == "fidelity_out_of_range":
        return "needs-attention", "fidelity outside [0,1] beyond float epsilon"
    if rule == "fidelity_fp_epsilon":
        return "benign", "fidelity 1+eps (float rounding, |eps|<=1e-9)"
    if rule == "reduction_above_1":
        return "needs-attention", "reduction > 1 impossible (negative optimized size)"
    if metric == "fidelity" and value == 0.0:
        if exp == "E18":
            return "explainable", "E18 Clifford+T decompose failure (documented survivor bias)"
        if success is False:
            return "explainable", "failed trial (success=False)"
        if exp == "E3":
            return "explainable", ("E3 zero-fidelity rows have reduction=0; consistent with "
                                   "disclosed mean fidelity 0.9968 (= 1 - 38/12000); E3 success "
                                   "column is uniformly False (broken), see column-integrity finding")
        return "needs-attention", "zero fidelity without failure flag or documentation"
    if metric == "reduction" and value < 0:
        if exp in NEG_RED_EXPLAINABLE:
            return "explainable", NEG_RED_EXPLAINABLE[exp]
        return "needs-attention", "negative reduction outside documented-inflation experiments"
    if metric == "runtime_seconds":
        return "benign", "heavy-tailed runtime distribution (not a validity issue)"
    return "benign", "in-range statistical tail value (distributional, not a validity issue)"


def scan_experiment(exp: str, rel: str) -> list[dict]:
    path = PROJECT_ROOT / rel
    if not path.exists():
        return [{"experiment": exp, "metric": "", "rule": "missing_file",
                 "n_rows_flagged": 0, "pct_of_experiment": 0.0,
                 "classification": "needs-attention",
                 "rationale": f"canonical file not found: {rel}",
                 "example_values": "", "example_ids": ""}]
    df = pd.read_csv(path)
    findings: list[dict] = []
    id_col = "circuit_id" if "circuit_id" in df.columns else None

    # Column integrity: constant status columns.
    for status_col in ("success",):
        if status_col in df.columns and df[status_col].nunique(dropna=False) == 1:
            val = df[status_col].iloc[0]
            findings.append({
                "experiment": exp, "metric": status_col,
                "rule": "constant_status_column",
                "n_rows_flagged": len(df), "pct_of_experiment": 100.0,
                "classification": "needs-attention",
                "rationale": (f"'{status_col}' is uniformly {val!r} across all rows; "
                              "column carries no information and cannot corroborate "
                              "failure flags"),
                "example_values": repr(val), "example_ids": "",
            })

    success = df["success"] if "success" in df.columns else None

    for metric, candidates in METRIC_CANDIDATES.items():
        col = _pick_col(df, candidates)
        if col is None:
            continue
        x = pd.to_numeric(df[col], errors="coerce")
        valid = x.dropna()
        if valid.empty:
            continue

        rules: list[tuple[str, pd.Series]] = []
        if metric == "fidelity":
            rules.append(("fidelity_out_of_range", (x < -FP_TOL) | (x > 1 + FP_TOL)))
            rules.append(("fidelity_fp_epsilon", (x > 1) & (x <= 1 + FP_TOL)))
            rules.append(("fidelity_zero", x == 0))
        if metric == "reduction":
            rules.append(("reduction_above_1", x > 1))
            rules.append(("reduction_negative", x < 0))

        mu, sd = float(valid.mean()), float(valid.std(ddof=1))
        if sd > 0:
            z = (x - mu) / sd
            rules.append((f"zscore_abs_gt_{Z_THRESH:g}", z.abs() > Z_THRESH))
        q1, q3 = float(valid.quantile(0.25)), float(valid.quantile(0.75))
        iqr = q3 - q1
        if iqr > 0:
            lo, hi = q1 - IQR_K * iqr, q3 + IQR_K * iqr
            rules.append((f"iqr_{IQR_K:g}x", (x < lo) | (x > hi)))

        for rule, mask in rules:
            mask = mask.fillna(False)
            n = int(mask.sum())
            if n == 0:
                continue
            vals = x[mask]
            ids = df.loc[mask, id_col].astype(str) if id_col else pd.Series([], dtype=str)
            succ_vals = success[mask] if success is not None else pd.Series([None] * n)
            classes = [_classify_row(exp, metric, rule, float(v), s)
                       for v, s in zip(vals.head(1000), succ_vals.head(1000))]
            worst = max(classes, key=lambda c: _CLASS_RANK[c[0]])
            cls = worst[0]
            rationales = sorted({c[1] for c in classes if c[0] == cls})
            findings.append({
                "experiment": exp,
                "metric": metric,
                "rule": rule,
                "n_rows_flagged": n,
                "pct_of_experiment": round(100 * n / len(df), 3),
                "classification": cls,
                "rationale": "; ".join(rationales),
                "example_values": ", ".join(f"{v:.6g}" for v in vals.head(5)),
                "example_ids": ", ".join(ids.head(MAX_ROWS_PER_CELL)),
            })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Outlier scan over canonical datasets.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    findings: list[dict] = []
    for exp, rel in CANON.items():
        findings.extend(scan_experiment(exp, rel))

    out = pd.DataFrame(findings)
    tmp = out_dir / "outlier_scan.csv.tmp"
    out.to_csv(tmp, index=False)
    os.replace(tmp, out_dir / "outlier_scan.csv")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 70)
    cols = ["experiment", "metric", "rule", "n_rows_flagged",
            "pct_of_experiment", "classification"]
    print(out[cols].to_string(index=False))
    counts = out["classification"].value_counts().to_dict()
    print(f"\nWrote {out_dir / 'outlier_scan.csv'}")
    print(f"Finding rows: {len(out)}; "
          + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    att = out[out["classification"] == "needs-attention"]
    if len(att):
        print("\nNeeds-attention summary:")
        print(att[["experiment", "metric", "rule", "n_rows_flagged",
                   "rationale"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
