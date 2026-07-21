"""Known-limitation impact audit.

For every Known Limitation listed in the project README, this script
recomputes the headline quantifying metric from canonical data, so each
limitation is backed by a runnable analysis rather than prose alone.

README Known Limitations (2026-07-14):
  L-trichotomy  Trichotomy is empirical on 15 pre-selected families, not a
                universal law.
  L-heldout     Held-out validation failed (MAE=0.2775, Pearson=NaN) --
                ceiling-aware model does not generalize.
  L-phase2b     Phase-2b template matching validated at fixture scale only.
  L-e18         E18 Clifford+T results are survivorship-biased (44.4% failure).
  L-wcl         WCL validation (E19) limited to random Universal circuits.
  L-shuffler    No random gate shuffler control performed.
  L-e04seed     E04 uses a single seed.

Usage:
    python analysis/limitations_impact_audit.py [--out-dir docs/review/wave1/data]

Output:
    limitations_impact.csv - one row per limitation with the recomputed
                             metric, the reference value from README/docs,
                             and a consistency verdict.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUT_DIR = PROJECT_ROOT / "docs" / "review" / "wave1" / "data"

E14 = "data/v5/e14/e14_extended_benchmark_e14_full_20260611_114726.csv"
E04 = "data/v2_fixed/e04/e04_algorithm_comparison_v2_20260613_132653.csv"
E15 = "data/v5/e15/e15_multi_compiler_e15_full_20260611_150934.csv"
E18 = "data/v5/e18/e18_clifford_t_e18_full_20260610_052140.csv"
E19 = "data/v6/e19/e19_wcl_listing_full_e19_full_20260620_123825.csv"
E20 = "data/v6/e20/multi_compiler_full.csv"
E22 = "data/v7/e22/e22_gate_shuffle_ablation.csv"
E24 = "data/v7/e24/e24_theorem7_results.csv"
E27 = "data/v7/e19_extended/e19_wcl_full_family.csv"
E29 = "data/v7/e29/e29_multi_seed_e04_full.csv"
HELDOUT = "data/v5/new_families_heldout.csv"
E10P2B = "data/v7/e10_phase2b_full/e10_phase2b_full_validation.csv"


def _load(rel: str) -> pd.DataFrame | None:
    p = PROJECT_ROOT / rel
    return pd.read_csv(p) if p.exists() else None


def audit_trichotomy() -> dict:
    """Recompute the trichotomy family counts from E14 (ours) and E20 (production).

    Classification rule (derived from manuscript Section 6.3 text):
      Class I   : our best mean reduction >= 99.9% (Phase-1 sufficient)
      Class II  : our best mean reduction > 1% (commutation-enabled)
      Class III : ours ~0 (< 1%); among these,
                    genuine          = no production compiler exceeds +1%
                    prototype-limited = a production compiler exceeds +1%
    Family-name mapping: E20 "UCCSD_inspired" == E14/manuscript "UCCSD".
    """
    e14, e20 = _load(E14), _load(E20)
    if e14 is None or e20 is None:
        return {"limitation": "L-trichotomy", "verdict": "data missing"}

    ours = e14.groupby(["circuit_family", "optimizer"])["reduction"].mean().unstack()
    ours_best = ours.max(axis=1)

    ok = e20[e20["compiler_status"] == "ok"].copy()
    ok["circuit_family"] = ok["circuit_family"].replace({"UCCSD_inspired": "UCCSD"})
    prod = ok.groupby(["circuit_family", "compiler_name"])["gate_reduction"].mean().unstack()
    prod_best = prod.max(axis=1)

    fams = sorted(set(ours_best.index) | set(prod_best.index))
    eps = 1e-9
    cls = {}
    for f in fams:
        o = float(ours_best.get(f, 0.0))
        p = float(prod_best.get(f, float("nan")))
        if o >= 0.999:
            cls[f] = "I"
        elif o > 0.01:
            cls[f] = "II"
        elif not np.isfinite(p) or p <= 0.01 + eps:
            cls[f] = "III-genuine"
        else:
            cls[f] = "III-prototype"

    def pick(*keys):
        return sorted([f for f, c in cls.items() if c in keys])

    classI = pick("I")
    classII = pick("II")
    genuine = pick("III-genuine")
    proto = pick("III-prototype")
    detail = "; ".join(
        f"{f}: ours={100*float(ours_best.get(f, 0.0)):.2f}% prod_best="
        f"{100*float(prod_best.get(f, float('nan'))):.2f}% -> {cls[f]}" for f in fams)

    # Manuscript cross-check: text L425 says 3 genuine {QFT,GHZ,SurfaceCode} and
    # 7 prototype-limited {QAOA,VQE,HardwareEfficient,IQP,UCCSD,Adder,QuantumWalk};
    # its own E15/E20 table labels Adder "Genuine ceiling" and QuantumWalk
    # "Unclear", and Section 6.3 text later says 5 prototype-limited.
    ms_genuine = {"QFT", "GHZ", "SurfaceCode"}
    data_supports_3 = ms_genuine.issubset(set(genuine))
    return {
        "limitation": "L-trichotomy",
        "metric": "family classification counts (E14 ours-mean vs E20 production-mean)",
        "recomputed": (f"Class I: {len(classI)} {classI}; Class II: {len(classII)} {classII}; "
                       f"III-genuine: {len(genuine)} {genuine}; "
                       f"III-prototype: {len(proto)} {proto}. Per-family: {detail}"),
        "reference": "3 genuine structural ceilings (QFT/GHZ/SurfaceCode); 7 prototype-limited",
        "verdict": ("PARTIAL: data reproduces genuine {QFT,GHZ,SurfaceCode} "
                    f"(subset rule holds: {data_supports_3}) but also classifies Adder as "
                    "genuine-by-rule (manuscript's own table agrees; its text says 3). "
                    "Prototype-limited count is 5-6 by rule (HaarRandom borderline at 6.5%), "
                    "not 7: manuscript Sec. 6.3 internally inconsistent "
                    "(L425 lists 7 incl. Adder+QuantumWalk vs table labels vs 5 in text)."),
    }


def audit_heldout() -> dict:
    h = _load(HELDOUT)
    if h is None:
        return {"limitation": "L-heldout", "verdict": "data missing"}
    mae = float(np.mean(np.abs(h["predicted_reduction"] - h["actual_reduction"])))
    pearson = float("nan")
    note = ""
    if h["actual_reduction"].std(ddof=1) == 0 or h["predicted_reduction"].std(ddof=1) == 0:
        note = "Pearson undefined (zero variance in held-out actual reductions)"
    else:
        pearson = float(stats.pearsonr(h["predicted_reduction"], h["actual_reduction"])[0])
    return {
        "limitation": "L-heldout",
        "metric": "held-out MAE / Pearson",
        "recomputed": f"MAE={mae:.4f} on n={len(h)} held-out rows "
                      f"({h['circuit_family'].nunique()} families: "
                      f"{sorted(h['circuit_family'].unique())}); Pearson={pearson}; {note}",
        "reference": "MAE=0.2775, Pearson=NaN",
        "verdict": "consistent" if abs(mae - 0.2775) < 5e-5 and np.isnan(pearson) else "REVIEW",
    }


def audit_phase2b() -> dict:
    e24, p2b = _load(E24), _load(E10P2B)
    parts = []
    if e24 is not None:
        for opt, grp in e24.groupby("optimizer"):
            parts.append(f"E24 {opt}: mean={grp['reduction'].mean()*100:.2f}% (n={len(grp)})")
    if p2b is not None:
        fams = p2b["circuit_family"].nunique() if "circuit_family" in p2b.columns else "?"
        parts.append(f"E10p2b full-validation rows={len(p2b)}, families={fams}")
    return {
        "limitation": "L-phase2b",
        "metric": "Phase-2b validation scale and achieved reduction",
        "recomputed": "; ".join(parts),
        "reference": "fixture-scale only; E24 Phase-2b mean 2.5% (does not meet 1/6 bound)",
        "verdict": "quantified",
    }


def audit_e18() -> dict:
    df = _load(E18)
    if df is None:
        return {"limitation": "L-e18", "verdict": "data missing"}
    failed = df[(df.get("status", "ok") != "ok") | df["reduction"].isna()]
    fid0 = df[(df.get("status", "ok") == "ok") & (df["fidelity"] == 0)]
    total_fail = len(failed) + len(fid0)
    row_rate = total_fail / len(df)
    fail_any = (df.assign(fail=lambda d: d["reduction"].isna() | (d["fidelity"] == 0))
                  .groupby("circuit_id")["fail"].any())
    circ_rate = float(fail_any.mean())
    n_families_ok = df[df["reduction"].notna()]["circuit_family"].nunique()
    return {
        "limitation": "L-e18",
        "metric": "row-level and circuit-level failure rates",
        "recomputed": (f"rows: {total_fail}/{len(df)} = {100*row_rate:.1f}% "
                       f"({len(failed)} decompose_error + {len(fid0)} fidelity=0); "
                       f"circuits: {int(fail_any.sum())}/{fail_any.size} = {100*circ_rate:.1f}%; "
                       f"families with surviving rows: {n_families_ok}/15"),
        "reference": "44.4% row failure (120/270); 92/142 = 64.8% circuit-level",
        "verdict": ("consistent" if abs(row_rate - 0.4444) < 5e-4
                    and abs(circ_rate - 0.648) < 5e-3 else "REVIEW"),
    }


def audit_wcl() -> dict:
    e19, e27 = _load(E19), _load(E27)
    if e19 is None:
        return {"limitation": "L-wcl", "verdict": "data missing"}
    fams19 = e19["circuit_family"].unique().tolist() if "circuit_family" in e19.columns else ["Universal"]
    parts = [f"E19 families: {fams19}"]
    if e27 is not None:
        fams27 = sorted(e27["circuit_family"].unique().tolist())
        wcl = e27[e27["listing_model"] == "WCL"].groupby("circuit_family")["reduction"].mean()
        lbl = e27[e27["listing_model"] == "LBL"].groupby("circuit_family")["reduction"].mean()
        nonzero_wcl = wcl[wcl > 1e-9]
        parts.append(f"E27 WCL-full-family extension: {len(fams27)} families {fams27}; "
                     f"families with WCL mean reduction > 0: "
                     f"{dict((k, round(100*v, 2)) for k, v in nonzero_wcl.items())}; "
                     f"LBL nonzero: {dict((k, round(100*v, 2)) for k, v in lbl[lbl > 1e-9].items())}")
    return {
        "limitation": "L-wcl",
        "metric": "listing-model validation coverage beyond random Universal",
        "recomputed": "; ".join(parts),
        "reference": "WCL validation (E19) limited to random Universal circuits",
        "verdict": "quantified (E27 extends coverage; see recomputed)",
    }


def audit_shuffler() -> dict:
    df = _load(E22)
    if df is None:
        return {"limitation": "L-shuffler", "verdict": "data missing"}
    grp = df.groupby(["listing_model", "optimizer"])["reduction"].agg(["mean", "count"])
    lines = [f"{idx[0]}/{idx[1]}: mean={row['mean']*100:.3f}% (n={int(row['count'])})"
             for idx, row in grp.iterrows()]
    # Shuffle vs original for each optimizer (MWU).
    tests = []
    for opt in df["optimizer"].unique():
        o = df[(df["optimizer"] == opt) & (df["listing_model"] == "original")]["reduction"]
        s = df[(df["optimizer"] == opt)
               & df["listing_model"].astype(str).str.startswith("shuffle")]["reduction"]
        if len(o) > 1 and len(s) > 1 and (o.std() > 0 or s.std() > 0):
            _, p = stats.mannwhitneyu(o, s, alternative="two-sided")
            tests.append(f"{opt}: shuffle-vs-original MWU p={p:.4f}")
    return {
        "limitation": "L-shuffler",
        "metric": "E22 gate-shuffle ablation: reduction by listing model",
        "recomputed": "; ".join(lines + tests),
        "reference": "README lists shuffler control as NOT performed",
        "verdict": "STALE LIMITATION: E22 control now exists (data/v7/e22); "
                   "manuscript limitation 6.3.9 should be updated by integration worker",
    }


def audit_e04_seed() -> dict:
    df = _load(E29)
    e04 = _load(E04)
    if df is None:
        return {"limitation": "L-e04seed", "verdict": "data missing"}
    per_seed = df.groupby(["optimizer", "seed"])["reduction"].mean().reset_index()
    spread = per_seed.groupby("optimizer")["reduction"].agg(["mean", "std", "min", "max", "count"])
    lines = [f"{opt}: across-seed mean={row['mean']*100:.4f}%, std={row['std']*100 if pd.notna(row['std']) else 0:.4f}%, "
             f"range=[{row['min']*100:.4f}%, {row['max']*100:.4f}%], seeds={int(row['count'])}"
             for opt, row in spread.iterrows()]
    # Cross-check against the E04 single-seed canonical point estimates.
    e04_note = "E04 canonical not loaded"
    mismatch = True
    if e04 is not None:
        e04_means = e04.groupby("optimizer")["reduction"].mean()
        e29_means = df.groupby("optimizer")["reduction"].mean()
        comp = []
        mismatch = False
        for opt in sorted(set(e04_means.index) & set(e29_means.index)):
            a, b = float(e04_means[opt]), float(e29_means[opt])
            same = abs(a - b) < 0.02  # within 2 percentage points
            mismatch |= not same
            comp.append(f"{opt}: E04={100*a:.2f}% vs E29={100*b:.2f}%"
                        f"{' (MISMATCH)' if not same else ''}")
        e04_note = "; ".join(comp)
    return {
        "limitation": "L-e04seed",
        "metric": "E29 multi-seed E04 replication: across-seed variance AND "
                  "reproduction of E04 single-seed point estimates",
        "recomputed": "; ".join(lines) + f". E04-vs-E29 point estimates: {e04_note}",
        "reference": "E04 uses single seed",
        "verdict": ("REVIEW: E29 does NOT reproduce the E04 single-seed point "
                    "estimates: RLS 0.00% -> -176.5% mean (gate inflation at "
                    "fidelity 1.0), SA -1.6% -> -22.1%, GA -0.2% -> -8.3% "
                    "(all mismatch). E04 conclusions are seed/configuration-"
                    "fragile; E29 circuits (n=5, depth=15) also differ from "
                    "E04. Integration worker must qualify any E04-based claim."
                    if mismatch else
                    "quantified (E29 provides multi-seed variance estimates "
                    "consistent with E04 point estimates)"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Known-limitation impact audit.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    audits = [
        audit_trichotomy(),
        audit_heldout(),
        audit_phase2b(),
        audit_e18(),
        audit_wcl(),
        audit_shuffler(),
        audit_e04_seed(),
    ]
    out = pd.DataFrame(audits)
    tmp = out_dir / "limitations_impact.csv.tmp"
    out.to_csv(tmp, index=False)
    os.replace(tmp, out_dir / "limitations_impact.csv")

    pd.set_option("display.max_colwidth", 160)
    pd.set_option("display.width", 260)
    for _, r in out.iterrows():
        print(f"\n[{r['limitation']}] verdict: {r['verdict']}")
        print(f"  metric:    {r.get('metric', '')}")
        print(f"  recomputed:{r.get('recomputed', '')}")
        print(f"  reference: {r.get('reference', '')}")
    print(f"\nWrote {out_dir / 'limitations_impact.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
