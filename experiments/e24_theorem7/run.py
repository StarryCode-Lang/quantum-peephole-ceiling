"""
E24: Theorem-7 Hardness Family Instantiation
============================================
Empirically instantiate the artificial hardness family from Theorem 7 and
compare Phase-1, Phase-2a, and Phase-2b reductions.

Outputs:
    data/v7/e24/e24_theorem7_results.csv
    data/v7/e24/metadata.json
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

from src.circuits.hardness_families import make_theorem7_hardness_family
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase2 import Phase2aCommutationRewriter, Phase2bTemplateMatcher


def run_e24(n_min: int = 4, n_max: int = 12, step: int = 2, n_trials: int = 5):
    output_dir = PROJECT_ROOT / "data/v7/e24"
    output_dir.mkdir(parents=True, exist_ok=True)

    optimizers = {
        "phase1_greedy": GreedyGateCancellation(),
        "phase2a_commutation": Phase2aCommutationRewriter(max_iterations=500, window_size=30),
        "phase2b_template": Phase2bTemplateMatcher(max_iterations=100),
    }

    results = []
    sizes = list(range(n_min, n_max + 1, step))
    total = len(sizes) * n_trials * len(optimizers)

    with tqdm(total=total, desc="E24 Theorem 7") as pbar:
        for n_qubits in sizes:
            # Exact fidelity verification is feasible only for small qubit counts.
            use_target = n_qubits <= 8
            for trial in range(n_trials):
                qc = make_theorem7_hardness_family(n_qubits)
                for opt_name, optimizer in optimizers.items():
                    target = qc if use_target else None
                    result = optimizer.optimize(qc, target=target)
                    results.append({
                        "experiment": 24,
                        "n_qubits": n_qubits,
                        "trial": trial,
                        "optimizer": opt_name,
                        "original_size": result.original_size,
                        "optimized_size": result.optimized_size,
                        "reduction": result.reduction,
                        "fidelity": result.fidelity,
                        "iterations": result.iterations,
                        "runtime_seconds": result.runtime_seconds,
                    })
                    pbar.update(1)

    df = pd.DataFrame(results)
    csv_path = output_dir / "e24_theorem7_results.csv"
    df.to_csv(csv_path, index=False)

    summary = (
        df.groupby(["n_qubits", "optimizer"])
        .agg(mean_reduction=("reduction", "mean"), min_reduction=("reduction", "min"))
        .reset_index()
    )
    summary_path = output_dir / "e24_theorem7_summary.csv"
    summary.to_csv(summary_path, index=False)

    # Check theoretical lower bound: Gamma >= 1/6 for Phase-2a/2b.
    phase2 = df[df["optimizer"].isin(["phase2a_commutation", "phase2b_template"])]
    meets_bound = (phase2.groupby("n_qubits")["reduction"].min() >= 1.0 / 6.0 - 1e-9)

    metadata = {
        "experiment": "E24",
        "description": "Instantiation and validation of Theorem 7 hardness family.",
        "timestamp": datetime.now().isoformat(),
        "n_min": n_min,
        "n_max": n_max,
        "step": step,
        "n_trials": n_trials,
        "total_rows": len(df),
        "csv_path": str(csv_path.relative_to(PROJECT_ROOT)),
        "summary_path": str(summary_path.relative_to(PROJECT_ROOT)),
        "mean_phase2a_reduction": float(df[df["optimizer"] == "phase2a_commutation"]["reduction"].mean()),
        "mean_phase2b_reduction": float(df[df["optimizer"] == "phase2b_template"]["reduction"].mean()),
        "mean_phase1_reduction": float(df[df["optimizer"] == "phase1_greedy"]["reduction"].mean()),
        "all_sizes_meet_one_sixth_bound": bool(meets_bound.all()) if not meets_bound.empty else None,
    }

    meta_path = output_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("E24 complete")
    print(f"  Phase-1 mean reduction:   {metadata['mean_phase1_reduction']:.4f}")
    print(f"  Phase-2a mean reduction:  {metadata['mean_phase2a_reduction']:.4f}")
    print(f"  Phase-2b mean reduction:  {metadata['mean_phase2b_reduction']:.4f}")
    print(f"  CSV: {csv_path}")
    return df, metadata


if __name__ == "__main__":
    run_e24()
