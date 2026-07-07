"""
E3 Re-run: Scaling Analysis (Fixed Greedy v3.0.0)
==================================================
Re-run Experiment 3 with the fixed Greedy optimizer.

Parameters (same as original):
- n_qubits = 3-10
- depth = 1-30
- n_trials = 50 (same as original)
- family = UNIVERSAL
- seed = 42
- entanglement_density = 0.3

Output: data/v5/e03/
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


def run_e3():
    """Run Experiment 3 with fixed Greedy optimizer."""
    
    n_qubits_list = list(range(3, 11))
    depths = list(range(1, 31))
    n_trials = 50
    seed_base = 42
    entanglement_density = 0.3
    family = CircuitFamily.UNIVERSAL
    
    output_dir = PROJECT_ROOT / "data/v5/e03"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    metadata = {
        "experiment_id": "E3",
        "description": "Scaling analysis with fixed Greedy v3.0.0",
        "n_qubits": n_qubits_list,
        "depths": depths,
        "n_trials": n_trials,
        "seed_base": seed_base,
        "entanglement_density": entanglement_density,
        "family": family.name,
        "optimizer": "GreedyGateCancellation v3.0.0",
        "timestamp": datetime.now().isoformat(),
    }
    
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    total = len(n_qubits_list) * len(depths) * n_trials
    print(f"E3 Re-run: {len(n_qubits_list)} qubits × {len(depths)} depths × {n_trials} trials = {total} total")
    
    results = []
    metrics_calculator = MetricsCalculator()
    optimizer = GreedyGateCancellation()
    
    with tqdm(total=total, desc="E3 v2") as pbar:
        for n_qubits in n_qubits_list:
            for depth in depths:
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
                    
                    result = optimizer.optimize(circuit, target=circuit)
                    
                    results.append({
                        "experiment": 3,
                        "n_qubits": n_qubits,
                        "depth": depth,
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
    csv_path = output_dir / f"e03_scaling_v2_{timestamp}.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"\nE3 complete: {len(df)} records saved to {csv_path}")
    print(f"Mean reduction: {df['reduction'].mean():.4f}")
    print(f"Success rate (20% threshold): {df['success'].mean():.2%}")
    
    return df


if __name__ == "__main__":
    run_e3()
