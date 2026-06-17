"""
E21: Ceiling-Aware Optimizer vs. Naive Pipeline
================================================
Demonstrates the *positive contribution* of knowing the structural
ceiling: by computing a fast O(m) action-space proxy before each
optimization phase, the ceiling-aware compiler skips phases that
would yield zero reduction, saving compilation time without losing
any gate-count reduction.

Strategies compared:
    1. **naive**         — Always run Phase 1 -> Phase 2 -> Phase 1
                          (HybridCommuteRewrite, instrumented).
    2. **ceiling_aware** — Compute ceiling proxy, conditionally skip
                          phases, same reduction but less time.

Output:
    data/v6/e21/ceiling_aware_comparison.csv   (per-trial rows)
    data/v6/e21/ceiling_aware_summary.csv      (aggregate per family)
    data/v6/e21/metadata.json

Version: 1.0.0
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from qiskit import QuantumCircuit  # noqa: E402

from src.circuits.real_benchmarks import (  # noqa: E402
    make_qft, make_ghz, make_cnot_chain, make_bernstein_vazirani,
    make_qaoa_line, make_vqe_twolocal, make_hardware_efficient,
    make_grover, make_quantum_adder, make_quantum_walk, make_iqp,
    make_random_clifford, make_surface_code_syndrome, make_uccsd_ansatz,
    make_haar_random, circuit_sha256,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase2.commutation_rewriter import (  # noqa: E402
    CommutationRewriter, HybridCommuteRewrite,
)
from src.optimisation.ceiling_aware import (  # noqa: E402
    CeilingAwareOptimizer, count_phase1_actions,
)
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "1.0.0"
EXPERIMENT_ID = "E21"
VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Circuit family registry
# ---------------------------------------------------------------------------

# Each entry: (family_name, factory_function, kwargs_builder(n, seed))
# kwargs_builder returns a dict of kwargs to pass to the factory.
# The factory always receives (n_qubits, ...) — we wrap as needed.

FAMILIES: List[Tuple[str, Callable, Callable]] = [
    ("QFT",
     make_qft,
     lambda n, s: {}),
    ("GHZ",
     make_ghz,
     lambda n, s: {}),
    ("CNOT",
     make_cnot_chain,
     lambda n, s: {}),
    ("Oracle",
     make_bernstein_vazirani,
     lambda n, s: {"seed": s}),
    ("QAOA",
     make_qaoa_line,
     lambda n, s: {"reps": 1, "seed": s}),
    ("VQE",
     make_vqe_twolocal,
     lambda n, s: {"reps": 1, "seed": s}),
    ("HardwareEfficient",
     make_hardware_efficient,
     lambda n, s: {"layers": 2, "seed": s}),
    ("Grover",
     make_grover,
     lambda n, s: {"seed": s}),
    ("Adder",
     make_quantum_adder,
     lambda n, s: {"seed": s}),
    ("QuantumWalk",
     make_quantum_walk,
     lambda n, s: {"steps": 3, "seed": s}),
    ("IQP",
     make_iqp,
     lambda n, s: {"depth": 3, "seed": s}),
    ("RandomClifford",
     make_random_clifford,
     lambda n, s: {"depth": 10, "seed": s}),
    ("SurfaceCode",
     make_surface_code_syndrome,
     lambda n, s: {"seed": s}),
    ("UCCSD",
     make_uccsd_ansatz,
     lambda n, s: {"reps": 1, "seed": s}),
    ("HaarRandom",
     make_haar_random,
     lambda n, s: {"seed": s}),
]

# Sizes to test — HaarRandom is restricted to n <= 4
QUBIT_SIZES = [4, 6, 8, 10]
HAAR_MAX_QUBITS = 4

# Number of independent trials per (family, n_qubits)
N_TRIALS = 10


# ---------------------------------------------------------------------------
# Instrumented naive pipeline (Phase 1 -> Phase 2 -> Phase 1)
# ---------------------------------------------------------------------------


def run_naive_pipeline(circuit: QuantumCircuit,
                       max_iterations: int = 100,
                       window_size: int = 10,
                       ) -> Dict:
    """Run the naive always-on pipeline with per-phase timing.

    Equivalent to HybridCommuteRewrite but with instrumented timers
    for each phase so we can fairly compare compilation cost.

    Returns a dict with keys:
        optimized_circuit, gate_reduction, original_size, optimized_size,
        phase1_time_ms, phase2_time_ms, final_phase1_time_ms, total_time_ms,
        phase1_skipped, phase2_skipped, fidelity, depth_reduction, cnot_reduction
    """
    t_start = time.perf_counter()

    phase1 = GreedyGateCancellation(max_iterations=max_iterations)
    phase2 = CommutationRewriter(max_iterations=max_iterations,
                                 window_size=window_size)

    # Phase 1
    t0 = time.perf_counter()
    r1 = phase1.optimize(circuit, target=circuit)
    phase1_time_ms = (time.perf_counter() - t0) * 1000.0
    intermediate = r1.optimized_circuit

    # Phase 2
    t0 = time.perf_counter()
    r2 = phase2.optimize(intermediate, target=circuit)
    phase2_time_ms = (time.perf_counter() - t0) * 1000.0
    after_phase2 = r2.optimized_circuit

    # Final Phase 1 cleanup
    t0 = time.perf_counter()
    r3 = phase1.optimize(after_phase2, target=circuit)
    final_phase1_time_ms = (time.perf_counter() - t0) * 1000.0
    optimized = r3.optimized_circuit

    total_time_ms = (time.perf_counter() - t_start) * 1000.0

    original_size = circuit.size()
    optimized_size = optimized.size()
    gate_reduction = 1.0 - optimized_size / original_size if original_size > 0 else 0.0

    # Extended metrics
    def _count(c):
        d = int(c.depth() or 0)
        cnot = sum(1 for inst in c.data if inst.operation.name in ('cx', 'cnot'))
        return d, cnot

    orig_depth, orig_cnot = _count(circuit)
    opt_depth, opt_cnot = _count(optimized)
    depth_red = 1.0 - opt_depth / orig_depth if orig_depth > 0 else 0.0
    cnot_red = 1.0 - opt_cnot / orig_cnot if orig_cnot > 0 else 0.0

    return {
        'optimized_circuit': optimized,
        'gate_reduction': gate_reduction,
        'original_size': original_size,
        'optimized_size': optimized_size,
        'phase1_time_ms': phase1_time_ms,
        'phase2_time_ms': phase2_time_ms,
        'final_phase1_time_ms': final_phase1_time_ms,
        'total_time_ms': total_time_ms,
        'phase1_skipped': False,
        'phase2_skipped': False,
        'fidelity': 1.0,  # by construction (same pipeline as Hybrid)
        'depth_reduction': depth_red,
        'cnot_reduction': cnot_red,
    }


# ---------------------------------------------------------------------------
# Circuit generation helper
# ---------------------------------------------------------------------------


def generate_circuit_for_experiment(family_name: str, factory: Callable,
                                     kwargs_builder: Callable,
                                     n_qubits: int, trial_seed: int) -> QuantumCircuit:
    """Generate a circuit for the given family and size, with deterministic seed."""
    kwargs = kwargs_builder(n_qubits, trial_seed)
    return factory(n_qubits, **kwargs)


# ---------------------------------------------------------------------------
# Main experiment loop
# ---------------------------------------------------------------------------


def run(mode: str = "smoke", seed: int = 42, window: int = 10) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Run the E21 ceiling-aware comparison experiment.

    Args:
        mode: 'smoke' uses fewer trials (3) for quick validation;
              'full' uses N_TRIALS (10) for publication results.
        seed: Base random seed for reproducibility.
        window: Commutation window size for Phase 2.

    Returns:
        (comparison_df, summary_df) tuple.
    """
    n_trials = 3 if mode == "smoke" else N_TRIALS
    run_id = f"e21_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v6" / "e21"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)

    ceiling_opt = CeilingAwareOptimizer(
        max_iterations=100,
        window_size=window,
    )

    rows: List[Dict] = []
    trial_rng = np.random.RandomState(seed)

    total_configs = len(FAMILIES) * len(QUBIT_SIZES) * n_trials
    # HaarRandom at n>4 will be skipped
    print(f"E21: {len(FAMILIES)} families x {len(QUBIT_SIZES)} sizes x {n_trials} trials")
    print(f"     (HaarRandom skipped for n > {HAAR_MAX_QUBITS})")

    processed = 0
    skipped = 0

    for family_name, factory, kwargs_builder in FAMILIES:
        for n_qubits in QUBIT_SIZES:
            # Skip HaarRandom for large n
            if family_name == "HaarRandom" and n_qubits > HAAR_MAX_QUBITS:
                skipped += n_trials
                continue

            for trial_idx in range(n_trials):
                trial_seed = int(trial_rng.randint(0, 2**31 - 1))

                try:
                    circuit = generate_circuit_for_experiment(
                        family_name, factory, kwargs_builder,
                        n_qubits, trial_seed,
                    )
                except Exception as exc:
                    print(f"  SKIP {family_name} n={n_qubits} trial={trial_idx}: {exc}")
                    skipped += 1
                    continue

                if circuit.size() == 0:
                    skipped += 1
                    continue

                # -- Strategy 1: Naive pipeline ----------------------------
                naive = run_naive_pipeline(circuit, window_size=window)

                # -- Strategy 2: Ceiling-aware pipeline --------------------
                detailed = ceiling_opt.optimize_detailed(circuit, target=circuit)
                ca = detailed.to_dict()
                ca_opt = detailed.optimization_result

                # Compute extended metrics for ceiling-aware
                def _count_ext(c):
                    d = int(c.depth() or 0)
                    cnot = sum(1 for inst in c.data
                               if inst.operation.name in ('cx', 'cnot'))
                    return d, cnot

                orig_d, orig_cnot = _count_ext(circuit)
                opt_d, opt_cnot = _count_ext(ca_opt.optimized_circuit)
                depth_red_ca = 1.0 - opt_d / orig_d if orig_d > 0 else 0.0
                cnot_red_ca = 1.0 - opt_cnot / orig_cnot if orig_cnot > 0 else 0.0

                base_record = {
                    'schema_version': SCHEMA_VERSION,
                    'experiment_id': EXPERIMENT_ID,
                    'run_id': run_id,
                    'family': family_name,
                    'n_qubits': n_qubits,
                    'trial_seed': trial_seed,
                    'trial_idx': trial_idx,
                    'original_size': circuit.size(),
                    'original_depth': orig_d,
                    'original_cnot': orig_cnot,
                    'ceiling_proxy_value': detailed.ceiling_proxy_phase1,
                    'input_circuit_sha256': circuit_sha256(circuit),
                }

                # Naive row
                naive_row = {
                    **base_record,
                    'strategy_name': 'naive',
                    'gate_reduction': naive['gate_reduction'],
                    'depth_reduction': naive['depth_reduction'],
                    'cnot_reduction': naive['cnot_reduction'],
                    'optimized_size': naive['optimized_size'],
                    'phase1_time_ms': naive['phase1_time_ms'],
                    'phase2_time_ms': naive['phase2_time_ms'],
                    'final_phase1_time_ms': naive['final_phase1_time_ms'],
                    'total_time_ms': naive['total_time_ms'],
                    'phase1_skipped': False,
                    'phase2_skipped': False,
                }

                # Ceiling-aware row
                ca_row = {
                    **base_record,
                    'strategy_name': 'ceiling_aware',
                    'gate_reduction': ca['gate_reduction'],
                    'depth_reduction': depth_red_ca,
                    'cnot_reduction': cnot_red_ca,
                    'optimized_size': ca['optimized_size'],
                    'phase1_time_ms': ca['phase1_time_ms'],
                    'phase2_time_ms': ca['phase2_time_ms'],
                    'final_phase1_time_ms': ca['final_phase1_time_ms'],
                    'total_time_ms': ca['total_time_ms'],
                    'phase1_skipped': ca['phase1_skipped'],
                    'phase2_skipped': ca['phase2_skipped'],
                }

                rows.append(naive_row)
                rows.append(ca_row)

                processed += 1
                if processed % 50 == 0:
                    print(f"  [{processed}/{total_configs - skipped}] "
                          f"{family_name} n={n_qubits} trial={trial_idx}")

    # -- Build DataFrames --------------------------------------------------
    df = pd.DataFrame(rows)

    # -- Aggregate summary -------------------------------------------------
    summary_rows: List[Dict] = []
    if not df.empty:
        grouped = df.groupby(['family', 'strategy_name'])
        for (fam, strat), group in grouped:
            n = len(group)
            summary_rows.append({
                'family': fam,
                'strategy_name': strat,
                'n_instances': n,
                'mean_gate_reduction': group['gate_reduction'].mean(),
                'std_gate_reduction': group['gate_reduction'].std(),
                'mean_depth_reduction': group['depth_reduction'].mean(),
                'std_depth_reduction': group['depth_reduction'].std(),
                'mean_cnot_reduction': group['cnot_reduction'].mean(),
                'mean_total_time_ms': group['total_time_ms'].mean(),
                'std_total_time_ms': group['total_time_ms'].std(),
                'median_total_time_ms': group['total_time_ms'].median(),
                'mean_phase1_time_ms': group['phase1_time_ms'].mean(),
                'mean_phase2_time_ms': group['phase2_time_ms'].mean(),
                'pct_phase1_skipped': group['phase1_skipped'].mean() * 100,
                'pct_phase2_skipped': group['phase2_skipped'].mean() * 100,
                'mean_ceiling_proxy': group['ceiling_proxy_value'].mean(),
                'mean_original_size': group['original_size'].mean(),
                'mean_optimized_size': group['optimized_size'].mean(),
            })

    summary_df = pd.DataFrame(summary_rows)

    # -- Compute speedup column -------------------------------------------
    if not summary_df.empty:
        pivot = summary_df.pivot_table(
            index='family',
            columns='strategy_name',
            values='mean_total_time_ms',
        )
        if 'naive' in pivot.columns and 'ceiling_aware' in pivot.columns:
            pivot['speedup'] = pivot['naive'] / pivot['ceiling_aware'].replace(0, np.nan)
            summary_df = summary_df.merge(
                pivot[['speedup']].reset_index(),
                on='family', how='left',
            )
        else:
            summary_df['speedup'] = np.nan

    # -- Save outputs ------------------------------------------------------
    csv_path = output_dir / "ceiling_aware_comparison.csv"
    df.to_csv(csv_path, index=False)

    summary_path = output_dir / "ceiling_aware_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    # Metadata
    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "description": (
            "Ceiling-aware optimizer vs naive pipeline comparison. "
            "Demonstrates that structural ceiling knowledge saves "
            "compilation time without losing gate-count reduction."
        ),
        "mode": mode,
        "seed": seed,
        "window": window,
        "n_trials_per_config": n_trials,
        "qubit_sizes": QUBIT_SIZES,
        "n_families": len(FAMILIES),
        "n_rows": len(df),
        "n_skipped": skipped,
        "n_processed": processed,
        "comparison_file": csv_path.name,
        "summary_file": summary_path.name,
    })
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2, sort_keys=True)

    # -- Print summary -----------------------------------------------------
    print(f"\nE21 complete: {len(df)} rows -> {csv_path}")
    print(f"  Summary: {len(summary_df)} rows -> {summary_path}")
    print(f"  Skipped: {skipped} configs (HaarRandom n>4 or errors)")

    if not summary_df.empty:
        print("\n-- Per-family speedup (naive / ceiling_aware) --")
        for fam in summary_df['family'].unique():
            fam_data = summary_df[summary_df['family'] == fam]
            naive_t = fam_data[fam_data['strategy_name'] == 'naive']['mean_total_time_ms'].values
            ca_t = fam_data[fam_data['strategy_name'] == 'ceiling_aware']['mean_total_time_ms'].values
            naive_r = fam_data[fam_data['strategy_name'] == 'naive']['mean_gate_reduction'].values
            ca_r = fam_data[fam_data['strategy_name'] == 'ceiling_aware']['mean_gate_reduction'].values
            if len(naive_t) > 0 and len(ca_t) > 0 and ca_t[0] > 0:
                speedup = naive_t[0] / ca_t[0]
                print(f"  {fam:20s}  "
                      f"speedup={speedup:.2f}x  "
                      f"naive_red={naive_r[0]:.4f}  "
                      f"ca_red={ca_r[0]:.4f}")

    return df, summary_df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run E21 ceiling-aware optimizer comparison"
    )
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke",
                        help="smoke = 3 trials (quick); full = 10 trials (publication)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Base random seed for reproducibility")
    parser.add_argument("--window", type=int, default=10,
                        help="Commutation window size for Phase 2")
    args = parser.parse_args()
    run(mode=args.mode, seed=args.seed, window=args.window)


if __name__ == "__main__":
    main()
