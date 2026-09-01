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

import argparse
import math
import sys
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
from src.circuits.real_benchmarks import average_gate_fidelity
from src.provenance import file_sha256


def run_e3(output_dir: Path | None = None, smoke: bool = False):
    """Run Experiment 3 with fixed Greedy optimizer."""
    
    n_qubits_list = [3] if smoke else list(range(3, 11))
    depths = [1, 5] if smoke else list(range(1, 31))
    n_trials = 2 if smoke else 50
    seed_base = 42
    entanglement_density = 0.3
    family = CircuitFamily.UNIVERSAL
    
    output_dir = (PROJECT_ROOT / "data/v10/prepaper/e03"
                  if output_dir is None else Path(output_dir).resolve())
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / "e03_checkpoint.csv"
    
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
        "mode": "smoke" if smoke else "full",
        "timestamp": datetime.now().isoformat(),
        "protocol_file": "experiments/prepaper_protocol.json",
        "protocol_sha256": file_sha256(PROJECT_ROOT / "experiments/prepaper_protocol.json"),
        "source_sha256": file_sha256(Path(__file__).resolve()),
        "output_dir": str(output_dir),
    }
    
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    total = len(n_qubits_list) * len(depths) * n_trials
    print(f"E3 Re-run: {len(n_qubits_list)} qubits × {len(depths)} depths × {n_trials} trials = {total} total")
    
    results = []
    if checkpoint_path.exists():
        results = pd.read_csv(checkpoint_path).to_dict(orient="records")
        print(f"Resuming E3 from {len(results)} checkpoint rows")
    completed = {
        (int(row["n_qubits"]), int(row["depth"]), int(row["trial"]), int(row["seed"]))
        for row in results
    }
    metrics_calculator = MetricsCalculator()
    optimizer = GreedyGateCancellation()
    
    with tqdm(total=total, desc="E3 v2") as pbar:
        for n_qubits in n_qubits_list:
            for depth in depths:
                for trial in range(n_trials):
                    row_key = (n_qubits, depth, trial, seed_base + trial)
                    if row_key in completed:
                        pbar.update(1)
                        continue
                    try:
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
                        exact_fidelity = average_gate_fidelity(
                            result.optimized_circuit, circuit, max_qubits=10
                        )
                        fidelity = float("nan") if exact_fidelity is None else exact_fidelity
                        valid = bool(
                            math.isfinite(fidelity)
                            and fidelity >= optimizer.fidelity_threshold
                        )
                        reduction = result.reduction
                        row = {
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
                        "reduction": reduction,
                        "fidelity": fidelity,
                        "fidelity_source": "exact" if math.isfinite(fidelity) else "unavailable",
                        "valid_equivalent_output": valid,
                        "success": bool(valid and reduction >= optimizer.success_reduction),
                        "analysis_reduction_itt": reduction if valid else 0.0,
                        "error": "",
                        "runtime_seconds": result.runtime_seconds,
                        "optimizer_version": "3.0.0",
                        }
                    except Exception as exc:
                        row = {
                            "experiment": 3, "n_qubits": n_qubits,
                            "depth": depth, "trial": trial,
                            "seed": seed_base + trial,
                            "gate_count": float("nan"),
                            "entanglement_entropy": float("nan"),
                            "normalized_entropy": float("nan"),
                            "original_size": float("nan"),
                            "optimized_size": float("nan"),
                            "reduction": float("nan"),
                            "fidelity": float("nan"),
                            "fidelity_source": "unavailable",
                            "valid_equivalent_output": False,
                            "success": False,
                            "analysis_reduction_itt": 0.0,
                            "error": f"{type(exc).__name__}: {exc}",
                            "runtime_seconds": float("nan"),
                            "optimizer_version": "3.0.0",
                        }
                    results.append(row)
                    completed.add(row_key)
                    if len(results) % 500 == 0:
                        pd.DataFrame(results).to_csv(checkpoint_path.with_suffix('.csv.tmp'), index=False)
                        checkpoint_path.with_suffix('.csv.tmp').replace(checkpoint_path)
                    
                    pbar.update(1)
    
    df = pd.DataFrame(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"e03_scaling_v2_{timestamp}.csv"
    df.to_csv(csv_path, index=False)
    if checkpoint_path.exists():
        checkpoint_path.unlink()
    
    print(f"\nE3 complete: {len(df)} records saved to {csv_path}")
    print(f"Mean reduction: {df['reduction'].mean():.4f}")
    print(f"Success rate (20% threshold): {df['success'].mean():.2%}")
    
    return df


def main():
    parser = argparse.ArgumentParser(description="Run E3 scaling confirmation")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--mode", choices=["smoke", "full"], default="full")
    args = parser.parse_args()
    run_e3(output_dir=args.output_dir, smoke=args.mode == "smoke")


if __name__ == "__main__":
    main()
