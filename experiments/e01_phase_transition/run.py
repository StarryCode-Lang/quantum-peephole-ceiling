"""
E1 Re-run: Phase Transition Detection (Fixed Greedy v3.0.0)
=============================================================
Re-run Experiment 1 with the fixed Greedy optimizer.
Original E1 used buggy Greedy v1.x where _are_inverse() did not check qubit matching.

Parameters (same as original):
- n_qubits = 5
- depth = 1-50
- n_trials = 500 (reduced from 5000 for time efficiency, documented)
- family = UNIVERSAL
- seed = 42
- entanglement_density = 0.3

Output: data/v2_fixed/e01/
"""

from __future__ import annotations

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.generator_v2 import (
    CircuitConfig, CircuitFamily, StructureType,
    generate_circuit_batch, MetricsCalculator
)
from src.optimisation.phase1.greedy import GreedyGateCancellation


def run_e1():
    """Run Experiment 1 with fixed Greedy optimizer."""
    
    # Configuration
    n_qubits = 5
    depths = list(range(1, 51))
    n_trials = 500  # Reduced from 5000 for time efficiency
    seed_base = 42
    entanglement_density = 0.3
    family = CircuitFamily.UNIVERSAL
    
    # Output directory
    output_dir = PROJECT_ROOT / "data/v2_fixed/e01"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Metadata
    metadata = {
        "experiment_id": "E1",
        "description": "Phase transition detection with fixed Greedy v3.0.0",
        "original_trials": 5000,
        "actual_trials": n_trials,
        "reduction_reason": "Time efficiency for v2 re-run; same parameter ranges",
        "n_qubits": n_qubits,
        "depths": depths,
        "seed_base": seed_base,
        "entanglement_density": entanglement_density,
        "family": family.name,
        "optimizer": "GreedyGateCancellation v3.0.0",
        "optimizer_fix": "_are_inverse() now checks qubit matching",
        "timestamp": datetime.now().isoformat(),
    }
    
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"E1 Re-run: {len(depths)} depths × {n_trials} trials = {len(depths) * n_trials} total")
    
    # Run experiment
    results = []
    metrics_calculator = MetricsCalculator()
    optimizer = GreedyGateCancellation()
    
    total = len(depths) * n_trials
    with tqdm(total=total, desc="E1 v2") as pbar:
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
                    "experiment": 1,
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
    
    # Save results
    df = pd.DataFrame(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"e01_phase_transition_v2_{timestamp}.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"\nE1 complete: {len(df)} records saved to {csv_path}")
    print(f"Mean reduction: {df['reduction'].mean():.4f}")
    print(f"Mean fidelity: {df['fidelity'].mean():.6f}")
    print(f"Success rate (20% threshold): {df['success'].mean():.2%}")
    
    return df


if __name__ == "__main__":
    run_e1()
