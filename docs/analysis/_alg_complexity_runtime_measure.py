#!/usr/bin/env python
"""Wall-clock measurements for the algorithmic-complexity report.

Measures (read-only, no experiment data is modified):
  A. Ceiling-aware proxy costs (count_phase1_actions / count_phase2_actions)
     and full CeilingAwareOptimizer pipeline time vs gate count m -> O(m) check.
  B. Live speedup re-verification: naive 3-phase pipeline vs ceiling-aware
     pipeline on a subset of E21 families (subset re-run; canonical numbers
     come from data/v6/e21/, this is a reproducibility spot check).
  C. Phase2bTemplateMatcher wall-clock scaling vs m (gates) and n (qubits)
     -> empirical check of the O(k * n * gates) cost model (k = #templates).

All timings use time.perf_counter with repeated median.  target=None is
passed to optimizers so no fidelity computation pollutes the timings
(consistent with E21's handling of large circuits).

Usage: python docs/analysis/_alg_complexity_runtime_measure.py [A|B|C|all]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from qiskit import QuantumCircuit  # noqa: E402

from src.circuits.generator_v2 import (  # noqa: E402
    CircuitConfig, CircuitFamily, generate_circuit_batch, MetricsCalculator,
)
from src.circuits.real_benchmarks import (  # noqa: E402
    make_qft, make_cnot_chain, make_bernstein_vazirani, make_vqe_twolocal,
    make_quantum_walk, make_random_clifford,
)
from src.optimisation.ceiling_aware import (  # noqa: E402
    CeilingAwareOptimizer, count_phase1_actions, count_phase2_actions,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase2.commutation_rewriter import (  # noqa: E402
    Phase2aCommutationRewriter,
)
from src.optimisation.phase2.template_matcher import (  # noqa: E402
    Phase2bTemplateMatcher,
)

OUT_DIR = ROOT / "docs" / "analysis"


def _median_time(fn, reps: int = 7) -> float:
    """Median wall-clock seconds over reps calls."""
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts))


def _loglog_slope(x: np.ndarray, y: np.ndarray) -> float:
    """Slope of log(y) ~ log(x); the empirical scaling exponent."""
    lx, ly = np.log(x), np.log(y)
    return float(np.polyfit(lx, ly, 1)[0])


# ---------------------------------------------------------------------------
# Part A: ceiling-aware O(m) scaling
# ---------------------------------------------------------------------------

def part_a() -> pd.DataFrame:
    print("=" * 72)
    print("Part A: ceiling-aware proxy + pipeline scaling vs gate count m")
    rows = []
    metrics = MetricsCalculator()

    # A1: proxies on UNIVERSAL random circuits (ceiling family: proxies return
    # small counts; scan cost dominates) -- n=5 fixed, depth sweep -> m sweep.
    print("\nA1: proxy cost vs m (UNIVERSAL random, n=5, depth sweep)")
    for depth in [10, 20, 40, 80, 160, 320]:
        cfg = CircuitConfig(n_qubits=5, depth=depth, family=CircuitFamily.UNIVERSAL,
                            seed=1234, entanglement_density=0.3)
        circuit, _ = generate_circuit_batch(cfg, 1, metrics)[0]
        m = circuit.size()
        t_p1 = _median_time(lambda: count_phase1_actions(circuit), reps=9)
        t_p2 = _median_time(lambda: count_phase2_actions(circuit, window=10), reps=9)
        ca = CeilingAwareOptimizer(max_iterations=100, window_size=10)
        t_full = _median_time(lambda: ca.optimize_detailed(circuit, target=None), reps=5)
        p1, p2 = count_phase1_actions(circuit), count_phase2_actions(circuit)
        rows.append(dict(part="A1_universal_proxy", n_qubits=5, m_gates=m,
                         proxy1=p1, proxy2=p2,
                         t_proxy1_ms=t_p1 * 1e3, t_proxy2_ms=t_p2 * 1e3,
                         t_pipeline_ms=t_full * 1e3))
        print(f"  m={m:5d}  proxy1={p1:3d} proxy2={p2:3d}  "
              f"t_p1={t_p1*1e3:7.3f}ms  t_p2={t_p2*1e3:7.3f}ms  t_pipe={t_full*1e3:8.3f}ms")

    df1 = pd.DataFrame(rows)
    s1 = _loglog_slope(df1["m_gates"].values, df1["t_proxy1_ms"].values)
    s2 = _loglog_slope(df1["m_gates"].values, df1["t_proxy2_ms"].values)
    s3 = _loglog_slope(df1["m_gates"].values, df1["t_pipeline_ms"].values)
    print(f"  log-log slopes: proxy1={s1:.2f}  proxy2={s2:.2f}  pipeline={s3:.2f}")

    # A2: full pipeline on a REDUCIBLE family (CNOT chain) where Phase-1 runs
    # -- worst case for the ceiling-aware pipeline.
    print("\nA2: pipeline on reducible CNOT chain (phases execute), repeats sweep")
    rows2 = []
    for repeats in [4, 8, 16, 32, 64, 128]:
        circuit = make_cnot_chain(6, repeats=repeats)
        m = circuit.size()
        ca = CeilingAwareOptimizer(max_iterations=100, window_size=10)
        t_full = _median_time(lambda: ca.optimize_detailed(circuit, target=None), reps=5)
        p1, p2 = count_phase1_actions(circuit), count_phase2_actions(circuit)
        rows2.append(dict(part="A2_cnot_chain_pipeline", n_qubits=6, m_gates=m,
                          proxy1=p1, proxy2=p2, t_pipeline_ms=t_full * 1e3))
        print(f"  m={m:5d}  proxy1={p1:3d} proxy2={p2:3d}  t_pipe={t_full*1e3:8.3f}ms")
    df2 = pd.DataFrame(rows2)
    s4 = _loglog_slope(df2["m_gates"].values, df2["t_pipeline_ms"].values)
    print(f"  log-log slope pipeline (reducible family): {s4:.2f}")

    df = pd.concat([df1, df2], ignore_index=True)
    df.attrs["slopes"] = dict(A1_proxy1=s1, A1_proxy2=s2, A1_pipeline=s3, A2_pipeline=s4)
    return df


# ---------------------------------------------------------------------------
# Part B: live speedup verification (subset re-run of E21 design)
# ---------------------------------------------------------------------------

def _run_naive_pipeline(circuit: QuantumCircuit, window_size: int = 10) -> dict:
    """Identical phase sequence to experiments/e21_ceiling_aware/run.py
    run_naive_pipeline (Phase1 -> Phase2a -> Phase1), instrumented."""
    t_start = time.perf_counter()
    phase1 = GreedyGateCancellation(max_iterations=100)
    phase2 = Phase2aCommutationRewriter(max_iterations=100, window_size=window_size)

    t0 = time.perf_counter()
    r1 = phase1.optimize(circuit, target=None)
    p1_ms = (time.perf_counter() - t0) * 1e3
    t0 = time.perf_counter()
    r2 = phase2.optimize(r1.optimized_circuit, target=None)
    p2_ms = (time.perf_counter() - t0) * 1e3
    t0 = time.perf_counter()
    r3 = phase1.optimize(r2.optimized_circuit, target=None)
    p3_ms = (time.perf_counter() - t0) * 1e3

    opt = r3.optimized_circuit
    orig_size = circuit.size()
    return dict(total_time_ms=(time.perf_counter() - t_start) * 1e3,
                phase1_time_ms=p1_ms, phase2_time_ms=p2_ms, final_phase1_time_ms=p3_ms,
                gate_reduction=1.0 - opt.size() / orig_size if orig_size else 0.0,
                optimized_size=opt.size(), original_size=orig_size)


def part_b() -> pd.DataFrame:
    print("=" * 72)
    print("Part B: live speedup re-verification (subset of E21 families)")
    families = [
        ("CNOT", lambda n, s: make_cnot_chain(n)),
        ("QuantumWalk", lambda n, s: make_quantum_walk(n, steps=3, seed=s)),
        ("VQE", lambda n, s: make_vqe_twolocal(n, reps=1, seed=s)),
        ("RandomClifford", lambda n, s: make_random_clifford(n, depth=10, seed=s)),
        ("QFT", lambda n, s: make_qft(n)),
        ("Oracle", lambda n, s: make_bernstein_vazirani(n, seed=s)),
    ]
    sizes = [4, 6, 8, 10]
    n_trials = 3
    rows = []
    ca_opt = CeilingAwareOptimizer(max_iterations=100, window_size=10)
    rng = np.random.RandomState(42)
    for fam, factory in families:
        for n in sizes:
            for t in range(n_trials):
                seed = int(rng.randint(0, 2**31 - 1))
                circuit = factory(n, seed)
                naive = _run_naive_pipeline(circuit)
                ca = ca_opt.optimize_detailed(circuit, target=None)
                ca_d = ca.to_dict()
                rows.append(dict(family=fam, n_qubits=n, trial=t,
                                 naive_ms=naive["total_time_ms"],
                                 ca_ms=ca_d["total_time_ms"],
                                 naive_red=naive["gate_reduction"],
                                 ca_red=ca_d["gate_reduction"],
                                 p1_skipped=ca_d["phase1_skipped"],
                                 p2_skipped=ca_d["phase2_skipped"],
                                 m_gates=naive["original_size"]))
                print(f"  {fam:15s} n={n:2d} t={t}  naive={naive['total_time_ms']:9.3f}ms  "
                      f"ca={ca_d['total_time_ms']:8.3f}ms  "
                      f"speedup={naive['total_time_ms']/max(ca_d['total_time_ms'],1e-9):8.2f}x  "
                      f"red_match={np.isclose(naive['gate_reduction'], ca_d['gate_reduction'])}")
    df = pd.DataFrame(rows)
    g = df.groupby("family").agg(naive_ms=("naive_ms", "mean"), ca_ms=("ca_ms", "mean"),
                                 naive_red=("naive_red", "mean"), ca_red=("ca_red", "mean"))
    g["speedup"] = g["naive_ms"] / g["ca_ms"]
    print("\nPer-family live speedups (mean of 12 trials each):")
    print(g.to_string(float_format=lambda x: f"{x:.4f}"))
    agg = df["naive_ms"].sum() / df["ca_ms"].sum()
    print(f"\nLive aggregate speedup (sum naive / sum ca): {agg:.2f}x")
    print(f"Live family-mean speedup: {g['speedup'].mean():.2f}x "
          f"(min {g['speedup'].min():.2f}x, max {g['speedup'].max():.2f}x)")
    print(f"Reduction match on all rows: {bool(np.isclose(df['naive_red'], df['ca_red']).all())}")
    return df


# ---------------------------------------------------------------------------
# Part C: template matcher wall clock
# ---------------------------------------------------------------------------

def part_c() -> pd.DataFrame:
    print("=" * 72)
    print("Part C: Phase2bTemplateMatcher wall-clock scaling")
    tm = Phase2bTemplateMatcher(max_iterations=100)
    rows = []

    # C1: m sweep at fixed n (RandomClifford depth sweep) -> time vs m
    print("\nC1: optimize() vs m (RandomClifford n=6, depth sweep)")
    for depth in [5, 10, 20, 40, 80, 160]:
        circuit = make_random_clifford(6, depth=depth, seed=99)
        m = circuit.size()
        t = _median_time(lambda: tm.optimize(circuit, target=None), reps=5)
        rows.append(dict(part="C1_m_sweep", n_qubits=6, m_gates=m, t_ms=t * 1e3))
        print(f"  m={m:5d}  t={t*1e3:9.3f}ms")

    # C2: n sweep with templates firing (BV oracle: H-CX-H sandwiches)
    print("\nC2: optimize() on BV oracle (templates fire), n sweep")
    for n in [4, 6, 8, 10, 12, 14, 16]:
        circuit = make_bernstein_vazirani(n, seed=7)
        m = circuit.size()
        t = _median_time(lambda: tm.optimize(circuit, target=None), reps=7)
        t_full = _median_time(lambda: tm.optimize_full_pipeline(circuit, target=None), reps=5)
        rows.append(dict(part="C2_bv_n_sweep", n_qubits=n, m_gates=m,
                         t_ms=t * 1e3, t_full_pipeline_ms=t_full * 1e3))
        print(f"  n={n:3d}  m={m:4d}  t={t*1e3:8.3f}ms  t_fullpipe={t_full*1e3:8.3f}ms")

    # C3: pure-scan worst case (CNOT chain: no templates fire, full scans)
    print("\nC3: optimize() on CNOT chain (no templates fire), repeats sweep")
    for repeats in [8, 16, 32, 64, 128, 256]:
        circuit = make_cnot_chain(6, repeats=repeats)
        m = circuit.size()
        t = _median_time(lambda: tm.optimize(circuit, target=None), reps=5)
        rows.append(dict(part="C3_cnot_m_sweep", n_qubits=6, m_gates=m, t_ms=t * 1e3))
        print(f"  m={m:5d}  t={t*1e3:9.3f}ms")

    df = pd.DataFrame(rows)
    for part, tcol in [("C1_m_sweep", "t_ms"), ("C3_cnot_m_sweep", "t_ms")]:
        sub = df[df.part == part]
        s = _loglog_slope(sub["m_gates"].values, sub[tcol].values)
        print(f"  {part}: log-log slope time vs m = {s:.2f}")
    sub = df[df.part == "C2_bv_n_sweep"]
    s_n = _loglog_slope(sub["n_qubits"].values, sub["t_ms"].values)
    s_m = _loglog_slope(sub["m_gates"].values, sub["t_ms"].values)
    s_full = _loglog_slope(sub["m_gates"].values, sub["t_full_pipeline_ms"].values)
    print(f"  C2_bv_n_sweep: slope vs n = {s_n:.2f}, vs m = {s_m:.2f}, full-pipe vs m = {s_full:.2f}")
    # O(k*n*m) model check: with k=5 fixed, predict t ∝ n*m
    sub_nm = sub["n_qubits"].values * sub["m_gates"].values
    s_nm = _loglog_slope(sub_nm, sub["t_ms"].values)
    print(f"  C2: slope vs n*m (k fixed) = {s_nm:.2f}")
    return df


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    outs = {}
    if which in ("all", "A"):
        outs["A"] = part_a()
    if which in ("all", "B"):
        outs["B"] = part_b()
    if which in ("all", "C"):
        outs["C"] = part_c()
    for k, df in outs.items():
        p = OUT_DIR / f"_alg_complexity_runtime_part{k}.csv"
        df.to_csv(p, index=False)
        print(f"saved {p}")
