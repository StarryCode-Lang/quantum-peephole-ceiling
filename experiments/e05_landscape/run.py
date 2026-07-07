"""
E5 Re-run: Landscape Characterization (Fixed Greedy v3.0.0)
=============================================================
Re-run Experiment 5 with the fixed Greedy optimizer.

Parameters (same as original):
- n_qubits = 5
- depths = [3, 5, 8, 10, 15, 20]
- n_circuits = 10
- n_samples = 100
- family = UNIVERSAL
- seed = 42
- entanglement_density = 0.3

Output: data/v2_fixed/e05/
"""

from __future__ import annotations

import sys
import os
import json
import copy
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


def run_e5():
    """Run Experiment 5 with fixed Greedy optimizer."""
    
    n_qubits = 5
    depths = [3, 5, 8, 10, 15, 20]
    n_circuits = 10
    n_samples = 100
    seed_base = 42
    entanglement_density = 0.3
    family = CircuitFamily.UNIVERSAL
    
    output_dir = PROJECT_ROOT / "data/v2_fixed/e05"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    metadata = {
        "experiment_id": "E5",
        "description": "Landscape characterization with fixed Greedy v3.0.0",
        "n_qubits": n_qubits,
        "depths": depths,
        "n_circuits": n_circuits,
        "n_samples": n_samples,
        "seed_base": seed_base,
        "entanglement_density": entanglement_density,
        "family": family.name,
        "optimizer": "GreedyGateCancellation v3.0.0",
        "timestamp": datetime.now().isoformat(),
    }
    
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    total = len(depths) * n_circuits * n_samples
    print(f"E5 Re-run: {len(depths)} depths × {n_circuits} circuits × {n_samples} samples = {total} total")
    
    results = []
    metrics_calculator = MetricsCalculator()
    optimizer = GreedyGateCancellation()
    
    with tqdm(total=total, desc="E5 v2") as pbar:
        for depth in depths:
            for circuit_id in range(n_circuits):
                config = CircuitConfig(
                    n_qubits=n_qubits,
                    depth=depth,
                    family=family,
                    seed=seed_base + circuit_id,
                    entanglement_density=entanglement_density,
                )
                
                circuits = generate_circuit_batch(config, 1, metrics_calculator)
                base_circuit, base_metrics = circuits[0]
                
                for sample in range(n_samples):
                    perturbed = _perturb_circuit(base_circuit, n_qubits, sample)
                    perturbed_metrics = metrics_calculator.calculate(perturbed)
                    
                    result = optimizer.optimize(perturbed, target=perturbed)
                    
                    results.append({
                        "experiment": 5,
                        "n_qubits": n_qubits,
                        "depth": depth,
                        "circuit_id": circuit_id,
                        "sample": sample,
                        "base_entropy": base_metrics.entanglement_entropy,
                        "perturbed_entropy": perturbed_metrics.entanglement_entropy,
                        "entropy_diff": abs(base_metrics.entanglement_entropy - perturbed_metrics.entanglement_entropy),
                        "base_gates": base_metrics.gate_count,
                        "perturbed_gates": perturbed_metrics.gate_count,
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
    csv_path = output_dir / f"e05_landscape_v2_{timestamp}.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"\nE5 complete: {len(df)} records saved to {csv_path}")
    
    return df


def _perturb_circuit(circuit, n_qubits, seed):
    """Create a perturbed version of the circuit.

    Review M3 fix: previously this function could *remove* a gate (the
    ``else`` branch popped a gate), which changed the circuit's size and
    thus the denominator of the reduction metric.  Different perturbation
    levels then had different denominators, making the reduction values
    incomparable.  We now only *swap* two gates (preserving size) or, if
    a removal is desired for a specific analysis, the caller must record
    the original size separately and use a fixed-denominator reduction.
    The removal branch is removed entirely so all perturbed circuits
    have the same gate count as the base circuit.
    """
    rng = np.random.RandomState(seed)
    perturbed = copy.deepcopy(circuit)

    if len(perturbed.data) > 1:
        # Only swap two gates — this preserves the circuit size so the
        # reduction denominator is constant across perturbation levels.
        i, j = rng.choice(len(perturbed.data), 2, replace=False)
        perturbed.data[i], perturbed.data[j] = perturbed.data[j], perturbed.data[i]

    return perturbed


if __name__ == "__main__":
    run_e5()
