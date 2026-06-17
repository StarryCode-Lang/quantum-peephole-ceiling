"""
E4 Re-run: Algorithm Comparison (Fixed Optimizers v3.0.0)
==========================================================
Re-run Experiment 4 with fixed optimizers.
For v2 re-run, we focus on Greedy (which had the bug) and keep SA/GA/RLS from v1.

Parameters (same as original):
- n_qubits = 5
- depth = 15
- n_trials = 100 (reduced from original)
- family = UNIVERSAL
- seed = 42
- entanglement_density = 0.3

Output: data/v2_fixed/e04/
"""

from __future__ import annotations

import sys
import os
import json
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.generator_v2 import (
    CircuitConfig, CircuitFamily,
    generate_circuit_batch, MetricsCalculator
)
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase1.random_local_search import RandomLocalSearch
from src.optimisation.phase1.simulated_annealing import SimulatedAnnealingOptimizer
from src.optimisation.phase1.genetic_algorithm import GeneticAlgorithmOptimizer


def run_e4():
    """Run Experiment 4 with fixed optimizers."""
    
    n_qubits = 5
    depth = 15
    n_trials = 100
    seed_base = 42
    entanglement_density = 0.3
    family = CircuitFamily.UNIVERSAL
    
    output_dir = PROJECT_ROOT / "data/v2_fixed/e04"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    optimizers = {
        "greedy": GreedyGateCancellation(),
        # NOTE: Each randomized optimizer (SA, GA, RLS) uses a single fixed seed.
        # This is a known limitation: single-seed evaluation does not capture
        # seed-dependent variance in stochastic optimizers. Multi-seed evaluation
        # (5-10 seeds per optimizer) is recommended for future work to assess
        # the robustness of the algorithm comparison to initialization effects.
        "rls": RandomLocalSearch(random_seed=seed_base + 10_000),
        "sa": SimulatedAnnealingOptimizer(random_seed=seed_base + 20_000),
        "ga": GeneticAlgorithmOptimizer(random_seed=seed_base + 30_000),
    }
    
    metadata = {
        "experiment_id": "E4",
        "description": "Algorithm comparison with fixed optimizers v3.0.0",
        "n_qubits": n_qubits,
        "depth": depth,
        "n_trials": n_trials,
        "seed_base": seed_base,
        "entanglement_density": entanglement_density,
        "family": family.name,
        "optimizers": list(optimizers.keys()),
        "timestamp": datetime.now().isoformat(),
    }
    
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    total = n_trials * len(optimizers)
    print(f"E4 Re-run: {n_trials} trials × {len(optimizers)} optimizers = {total} total")
    
    results = []
    metrics_calculator = MetricsCalculator()
    
    with tqdm(total=total, desc="E4 v2") as pbar:
        for trial in range(n_trials):
            config = CircuitConfig(
                n_qubits=n_qubits,
                depth=depth,
                family=family,
                seed=seed_base + trial,
                entanglement_density=entanglement_density,
            )
            
            circuits = generate_circuit_batch(config, 1, metrics_calculator)
            circuit, metrics = circuits[0]
            
            for opt_name, optimizer in optimizers.items():
                result = optimizer.optimize(circuit, target=circuit)
                
                results.append({
                    "experiment": 4,
                    "n_qubits": n_qubits,
                    "depth": depth,
                    "trial": trial,
                    "seed": seed_base + trial,
                    "optimizer": opt_name,
                    "gate_count": metrics.gate_count,
                    "entanglement_entropy": metrics.entanglement_entropy,
                    "normalized_entropy": metrics.normalized_entropy,
                    "original_size": result.original_size,
                    "optimized_size": result.optimized_size,
                    "reduction": result.reduction,
                    "fidelity": result.fidelity,
                    "success": result.success,
                    "runtime_seconds": result.runtime_seconds,
                    "optimizer_version": "3.0.0",
                })
                
                pbar.update(1)
    
    df = pd.DataFrame(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"e04_algorithm_comparison_v2_{timestamp}.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"\nE4 complete: {len(df)} records saved to {csv_path}")
    for opt_name in optimizers.keys():
        sub = df[df["optimizer"] == opt_name]
        print(f"  {opt_name}: mean reduction={sub['reduction'].mean():.4f}, success={sub['success'].mean():.2%}")
    
    return df


if __name__ == "__main__":
    run_e4()
