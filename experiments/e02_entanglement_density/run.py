"""
E2 Re-run: Entanglement Density Sweep (Fixed Greedy v3.0.0)
============================================================
Re-run Experiment 2 with the fixed Greedy optimizer.

Parameters (same as original):
- n_qubits = 6
- depth = 20
- densities = 0.0 to 1.0 in steps of 0.05
- n_trials = 100 (reduced from 300 for time efficiency)
- family = UNIVERSAL
- seed = 42

Output: data/v2_fixed/e02/
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


def run_e2():
    """Run Experiment 2 with fixed Greedy optimizer."""
    
    n_qubits = 6
    depth = 20
    densities = np.arange(0, 1.05, 0.05)
    n_trials = 100
    seed_base = 42
    family = CircuitFamily.UNIVERSAL
    
    output_dir = PROJECT_ROOT / "data/v2_fixed/e02"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    metadata = {
        "experiment_id": "E2",
        "description": "Entanglement density sweep with fixed Greedy v3.0.0",
        "original_trials": 300,
        "actual_trials": n_trials,
        "n_qubits": n_qubits,
        "depth": depth,
        "densities": [float(d) for d in densities],
        "seed_base": seed_base,
        "family": family.name,
        "optimizer": "GreedyGateCancellation v3.0.0",
        "timestamp": datetime.now().isoformat(),
    }
    
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"E2 Re-run: {len(densities)} densities × {n_trials} trials = {len(densities) * n_trials} total")
    
    results = []
    metrics_calculator = MetricsCalculator()
    optimizer = GreedyGateCancellation()
    
    total = len(densities) * n_trials
    with tqdm(total=total, desc="E2 v2") as pbar:
        for density in densities:
            for trial in range(n_trials):
                config = CircuitConfig(
                    n_qubits=n_qubits,
                    depth=depth,
                    family=family,
                    seed=seed_base + trial,
                    entanglement_density=float(density),
                )
                
                circuits = generate_circuit_batch(config, 1, metrics_calculator)
                circuit, metrics = circuits[0]
                
                result = optimizer.optimize(circuit, target=circuit)
                
                results.append({
                    "experiment": 2,
                    "n_qubits": n_qubits,
                    "depth": depth,
                    "entanglement_density": float(density),
                    "trial": trial,
                    "seed": seed_base + trial,
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
    csv_path = output_dir / f"e02_entanglement_density_v2_{timestamp}.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"\nE2 complete: {len(df)} records saved to {csv_path}")
    print(f"Mean reduction: {df['reduction'].mean():.4f}")
    print(f"Success rate (20% threshold): {df['success'].mean():.2%}")
    
    return df


if __name__ == "__main__":
    run_e2()
