#!/usr/bin/env python
"""Summarize existing ablation datasets for the algorithmic-complexity report.

Read-only analysis: loads canonical CSVs and prints summary tables used in
docs/analysis/algorithmic_complexity.md. No experiment re-runs.

Datasets:
  E04  data/v2_fixed/e04/e04_algorithm_comparison_v2_20260613_132653.csv
  E10  data/v5/e10/e10_expanded_phase1_vs_phase2_20260613_131601.csv
  E21  data/v6/e21/ceiling_aware_comparison.csv + ceiling_aware_summary.csv
  E22  data/v7/e22/e22_gate_shuffle_ablation.csv
  E29  data/v7/e29/e29_multi_seed_e04_full.csv + e29_multi_seed_statistics.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)


def e04():
    print("=" * 70)
    print("E04 algorithm comparison (canonical, 400 rows)")
    f = ROOT / "data/v2_fixed/e04/e04_algorithm_comparison_v2_20260613_132653.csv"
    df = pd.read_csv(f)
    g = df.groupby("optimizer").agg(
        n=("reduction", "size"),
        mean_reduction=("reduction", "mean"),
        std_reduction=("reduction", "std"),
        mean_fidelity=("fidelity", "mean"),
        success_rate=("success", "mean"),
        mean_runtime_s=("runtime_seconds", "mean"),
        mean_runtime_ms=("runtime_seconds", lambda s: s.mean() * 1000),
        mean_original_size=("original_size", "mean"),
        mean_optimized_size=("optimized_size", "mean"),
    )
    print(g.to_string(float_format=lambda x: f"{x:.4f}"))
    # paired deltas vs greedy
    pivot = df.pivot_table(index=["trial"], columns="optimizer", values="reduction")
    print("\nPaired mean delta vs greedy (same circuit per trial):")
    for col in pivot.columns:
        if col != "greedy":
            d = (pivot[col] - pivot["greedy"]).mean()
            print(f"  {col} - greedy: {d:+.4f}")


def e10():
    print("=" * 70)
    print("E10 phase1 vs phase2 vs hybrid (canonical expanded, 1905 rows)")
    f = ROOT / "data/v5/e10/e10_expanded_phase1_vs_phase2_20260613_131601.csv"
    df = pd.read_csv(f)
    print("parts:", df["part"].unique().tolist())
    print("optimizers:", df["optimizer"].unique().tolist())
    print("families:", df["circuit_family"].unique().tolist())
    g = df.groupby(["circuit_family", "optimizer"]).agg(
        n=("reduction", "size"),
        mean_reduction=("reduction", "mean"),
        std_reduction=("reduction", "std"),
        mean_fidelity=("fidelity", "mean"),
        success_rate=("success", "mean"),
    )
    print(g.to_string(float_format=lambda x: f"{x:.4f}"))
    # phase contribution: hybrid - phase1 alone per family
    piv = df.groupby(["circuit_family", "optimizer"])["reduction"].mean().unstack()
    print("\nMean reduction pivot (families x optimizer):")
    print(piv.to_string(float_format=lambda x: f"{x:.4f}"))
    if {"greedy_phase1", "hybrid_phase1_2"}.issubset(piv.columns):
        piv["phase2_gain"] = piv["hybrid_phase1_2"] - piv["greedy_phase1"]
        print("\nPhase-2 marginal gain (hybrid - greedy_phase1):")
        print(piv[["greedy_phase1", "commutation_phase2", "hybrid_phase1_2", "phase2_gain"]].to_string(
            float_format=lambda x: f"{x:.4f}"))


def e21():
    print("=" * 70)
    print("E21 ceiling-aware vs naive (full, 1140 rows) — speedup claim verification")
    f = ROOT / "data/v6/e21/ceiling_aware_comparison.csv"
    df = pd.read_csv(f)
    print("rows:", len(df), "strategies:", df["strategy_name"].unique().tolist())
    print("families:", sorted(df["family"].unique().tolist()))

    # Per-family mean times and speedups (recompute from raw rows)
    g = df.groupby(["family", "strategy_name"]).agg(
        n=("total_time_ms", "size"),
        mean_time_ms=("total_time_ms", "mean"),
        mean_gate_reduction=("gate_reduction", "mean"),
        std_gate_reduction=("gate_reduction", "std"),
        pct_p1_skipped=("phase1_skipped", "mean"),
        pct_p2_skipped=("phase2_skipped", "mean"),
        mean_size=("original_size", "mean"),
    ).reset_index()
    piv_t = g.pivot_table(index="family", columns="strategy_name", values="mean_time_ms")
    piv_r = g.pivot_table(index="family", columns="strategy_name", values="mean_gate_reduction")
    piv_t["speedup"] = piv_t["naive"] / piv_t["ceiling_aware"]
    piv_t["red_naive"] = piv_r["naive"]
    piv_t["red_ca"] = piv_r["ceiling_aware"]
    piv_t["red_match"] = np.isclose(piv_t["red_naive"], piv_t["red_ca"], atol=1e-9)
    print("\nPer-family (recomputed from raw rows):")
    print(piv_t.sort_values("speedup", ascending=False).to_string(
        float_format=lambda x: f"{x:.4f}"))
    sp = piv_t["speedup"]
    print(f"\nSpeedup min={sp.min():.2f}x  max={sp.max():.2f}x  mean={sp.mean():.2f}x  median={sp.median():.2f}x")
    print(f"Claim: 1.6x-228x, mean 35x")
    print(f"Reduction identical across strategies for all families: {bool(piv_t['red_match'].all())}")

    # Per-trial speedups (raw distribution)
    piv_trial = df.pivot_table(index=["family", "n_qubits", "trial_idx"],
                               columns="strategy_name", values="total_time_ms")
    piv_trial["speedup"] = piv_trial["naive"] / piv_trial["ceiling_aware"]
    print(f"\nPer-trial speedup: min={piv_trial['speedup'].min():.2f}x "
          f"max={piv_trial['speedup'].max():.2f}x mean={piv_trial['speedup'].mean():.2f}x")

    # Fraction of phases executed by ceiling-aware
    ca = df[df["strategy_name"] == "ceiling_aware"]
    phases_run = ((~ca["phase1_skipped"]).astype(int) + (~ca["phase2_skipped"]).astype(int)).mean()
    print(f"Mean phases executed per circuit (of 2 skippable): {phases_run:.3f} "
          f"-> executes {phases_run / 2:.1%} of phases")
    # Check summary CSV consistency (moved to derived/ by E21 owner worker)
    sf = ROOT / "data/v6/e21/derived/ceiling_aware_summary.csv"
    sdf = pd.read_csv(sf)
    piv_s = sdf.pivot_table(index="family", columns="strategy_name", values="mean_total_time_ms")
    piv_s["speedup"] = piv_s["naive"] / piv_s["ceiling_aware"]
    print(f"\nSummary CSV speedups: min={piv_s['speedup'].min():.2f}x max={piv_s['speedup'].max():.2f}x mean={piv_s['speedup'].mean():.2f}x")


def e22():
    print("=" * 70)
    print("E22 gate-order shuffle ablation (v7 canonical, 2240 rows)")
    f = ROOT / "data/v7/e22/e22_gate_shuffle_ablation.csv"
    df = pd.read_csv(f)
    print("families:", df["circuit_family"].unique().tolist())
    print("listing models:", df["listing_model"].unique().tolist())
    print("optimizers:", df["optimizer"].unique().tolist())
    g = df.groupby(["circuit_family", "listing_model", "optimizer"]).agg(
        n=("reduction", "size"),
        mean_reduction=("reduction", "mean"),
        std_reduction=("reduction", "std"),
        mean_fidelity=("fidelity", "mean"),
    )
    print(g.to_string(float_format=lambda x: f"{x:.4f}"))
    piv = df.groupby(["listing_model", "optimizer"])["reduction"].agg(["mean", "std", "size"])
    print("\nOverall by listing_model x optimizer:")
    print(piv.to_string(float_format=lambda x: f"{x:.4f}"))


def e29():
    print("=" * 70)
    print("E29 multi-seed E04 (v7 canonical, 800 rows)")
    f = ROOT / "data/v7/e29/e29_multi_seed_e04_full.csv"
    df = pd.read_csv(f)
    print("seeds:", sorted(df["seed_base"].unique().tolist()))
    g = df.groupby("optimizer").agg(
        n=("reduction", "size"),
        mean_reduction=("reduction", "mean"),
        std_reduction=("reduction", "std"),
        mean_fidelity=("fidelity", "mean"),
        success_rate=("success", "mean"),
    )
    print("\nAcross-seed aggregate:")
    print(g.to_string(float_format=lambda x: f"{x:.4f}"))
    # per-seed spread
    ps = df.groupby(["optimizer", "seed_base"])["reduction"].mean().unstack()
    print("\nPer-seed mean reduction:")
    print(ps.to_string(float_format=lambda x: f"{x:.4f}"))
    print("\nSeed-to-seed std of per-seed means:")
    print(ps.std(axis=1).to_string(float_format=lambda x: f"{x:.5f}"))
    sf = ROOT / "data/v7/e29/e29_multi_seed_statistics.csv"
    if sf.exists():
        sdf = pd.read_csv(sf)
        print("\nStatistics file columns:", sdf.columns.tolist())
        print(sdf.head(50).to_string(float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "e04"):
        e04()
    if which in ("all", "e10"):
        e10()
    if which in ("all", "e21"):
        e21()
    if which in ("all", "e22"):
        e22()
    if which in ("all", "e29"):
        e29()
