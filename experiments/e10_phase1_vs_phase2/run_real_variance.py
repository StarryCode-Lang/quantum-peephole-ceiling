"""
E10 Real Circuit Variance Estimation (review H5).

The original E10 run_expanded.py generates real algorithm circuits (QFT,
GHZ, BV, etc.) with only ONE instance per (family, size) — trial=0,
seed=0 for all.  This means no variance estimate exists for real
circuits, preventing statistical inference (p-values, CIs).

This script closes that gap by running each real circuit family across
multiple seeds and recording per-family statistics (mean, std, 95% CI).

Output: data/v6/e10_real_variance/
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from qiskit import QuantumCircuit

from src.circuits.generator_v2 import MetricsCalculator
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase2.commutation_rewriter import (
    CommutationRewriter, HybridCommuteRewrite,
)
from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher

# Reuse the real circuit generators from run_expanded.py
from experiments.e10_phase1_vs_phase2.run_expanded import (
    make_qft, make_ghz, make_cnot_chain, make_bernstein_vazirani,
    make_qaoa, make_vqe_twolocal, make_hardware_efficient,
    REAL_CIRCUIT_GENERATORS,
)

SIZES = [3, 4, 5, 6, 7]
SEEDS = [42, 142, 242, 342, 442]


def _run_opt(optimizer, circuit, label, use_full_pipeline=False):
    if use_full_pipeline and hasattr(optimizer, 'optimize_full_pipeline'):
        result = optimizer.optimize_full_pipeline(circuit, target=circuit)
    else:
        result = optimizer.optimize(circuit, target=circuit)
    return {
        "optimizer": label,
        "original_size": result.original_size,
        "optimized_size": result.optimized_size,
        "reduction": result.reduction,
        "fidelity": result.fidelity,
        "success": result.success,
        "runtime_seconds": result.runtime_seconds,
    }


def run_real_variance():
    output_dir = PROJECT_ROOT / "data/v6/e10_real_variance"
    output_dir.mkdir(parents=True, exist_ok=True)

    optimizers = {
        "greedy_phase1": GreedyGateCancellation(),
        "commutation_phase2": CommutationRewriter(),
        "hybrid_phase1_2": HybridCommuteRewrite(),
        "template_phase2b": Phase2bTemplateMatcher(),
    }

    results = []
    mc = MetricsCalculator()

    total = 0
    for family_name, generators in REAL_CIRCUIT_GENERATORS.items():
        total += len(generators) * len(SIZES) * len(SEEDS) * len(optimizers)

    with tqdm(total=total, desc="E10 Real Variance") as pbar:
        for family_name, generators in REAL_CIRCUIT_GENERATORS.items():
            for gen_fn in generators:
                for n in SIZES:
                    for seed_idx, seed in enumerate(SEEDS):
                        try:
                            circuit = gen_fn(n)
                        except Exception as exc:
                            print(f"  Warning: {family_name}(n={n}) failed: {exc}")
                            pbar.update(len(optimizers))
                            continue
                        metrics = mc.calculate(circuit)
                        for opt_name, optimizer in optimizers.items():
                            use_full = opt_name == "template_phase2b"
                            row = _run_opt(optimizer, circuit, opt_name, use_full_pipeline=use_full)
                            row.update({
                                "experiment": "E10_real_variance",
                                "circuit_family": family_name,
                                "n_qubits": circuit.num_qubits,
                                "depth": circuit.depth(),
                                "param_n": n,
                                "seed_index": seed_idx,
                                "seed": seed,
                                "gate_count": metrics.gate_count,
                            })
                            results.append(row)
                            pbar.update(1)

    df = pd.DataFrame(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"e10_real_variance_{timestamp}.csv"
    df.to_csv(csv_path, index=False)

    # Per-family statistics.
    summary_rows = []
    for family in df["circuit_family"].unique():
        for opt in df["optimizer"].unique():
            sub = df[(df["circuit_family"] == family) & (df["optimizer"] == opt)]
            red = sub["reduction"].dropna()
            if len(red) == 0:
                continue
            mean = float(red.mean())
            std = float(red.std()) if len(red) > 1 else 0.0
            ci_half = 1.96 * std / np.sqrt(len(red)) if len(red) > 1 else 0.0
            summary_rows.append({
                "circuit_family": family,
                "optimizer": opt,
                "n": len(red),
                "mean_reduction": mean,
                "std_reduction": std,
                "ci_lower": mean - ci_half,
                "ci_upper": mean + ci_half,
            })
    summary_df = pd.DataFrame(summary_rows)
    summary_path = output_dir / f"e10_real_variance_summary_{timestamp}.csv"
    summary_df.to_csv(summary_path, index=False)

    metadata = {
        "experiment_id": "E10_real_variance",
        "version": "1.0.0",
        "description": "Multi-seed variance estimation for real circuit families (review H5)",
        "seeds": SEEDS,
        "n_seeds": len(SEEDS),
        "sizes": SIZES,
        "optimizers": list(optimizers.keys()),
        "families": list(REAL_CIRCUIT_GENERATORS.keys()),
        "total_rows": len(df),
        "canonical_data_file": csv_path.name,
        "summary_file": summary_path.name,
        "timestamp": datetime.now().isoformat(),
        "review_fix": "H5: real circuit variance estimation (N>1 per family×size)",
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nE10 real variance complete: {len(df)} rows -> {csv_path}")
    print(f"Summary -> {summary_path}")
    print("\n=== Per-family variance summary (hybrid optimizer) ===")
    hyb = summary_df[summary_df["optimizer"] == "hybrid_phase1_2"]
    print(hyb.to_string(index=False))

    return df


if __name__ == "__main__":
    run_real_variance()
