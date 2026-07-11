"""
E10: Phase 1 vs Phase 2 Optimization Comparison
================================================
Quantify the decisive value of Phase 2 (commutation-based) optimization
beyond the Phase 1 (adjacent-search) ceiling.

This is the project's strongest scientific contribution.

Circuit families:
- Random (Universal, n=5, d=20, 100 trials)
- Structured (Brickwork, n=5, d=20, 100 trials)
- Real (QFT, GHZ, CNOT chain, 10 each)

Optimizers:
1. Greedy (Phase 1 only)
2. CommutationRewriter (Phase 2 only)
3. HybridCommuteRewrite (Phase 1 + Phase 2)

NOTE: This original E10 experiment is superseded by the expanded run in
data/v5/e10/ (1905 canonical rows). Kept for reproducibility of the
original 627-row dataset.
Output: data/v5/e10_original/
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

from qiskit import QuantumCircuit

from src.circuits.generator_v2 import (
    CircuitConfig, CircuitFamily, StructureType,
    generate_circuit_batch, MetricsCalculator
)
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase2.commutation_rewriter import CommutationRewriter, HybridCommuteRewrite


def generate_real_circuits():
    """Generate real quantum algorithm circuits for benchmarking."""
    circuits = []
    
    # QFT (n=4)
    for n in [3, 4, 5]:
        qc = QuantumCircuit(n)
        for i in range(n):
            qc.h(i)
            for j in range(i + 1, n):
                qc.cp(np.pi / 2**(j - i), j, i)
        circuits.append(("QFT", n, qc))
    
    # GHZ (n=5)
    for n in [3, 4, 5]:
        qc = QuantumCircuit(n)
        qc.h(0)
        for i in range(n - 1):
            qc.cx(i, i + 1)
        circuits.append(("GHZ", n, qc))
    
    # CNOT chain (n=5)
    for n in [3, 4, 5]:
        qc = QuantumCircuit(n)
        for i in range(n - 1):
            qc.cx(i, i + 1)
            qc.cx(i, i + 1)  # Self-inverse pair
        circuits.append(("CNOT_chain", n, qc))
    
    return circuits


def run_e10():
    """Run E10: Phase 1 vs Phase 2 comparison."""
    
    output_dir = PROJECT_ROOT / "data/v5/e10_original"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    optimizers = {
        "greedy_phase1": GreedyGateCancellation(),
        "commutation_phase2": CommutationRewriter(),
        "hybrid_phase1_2": HybridCommuteRewrite(),
    }
    
    results = []
    metrics_calculator = MetricsCalculator()
    
    # Part 1: Random circuits
    print("E10 Part 1: Random circuits")
    n_qubits = 5
    depth = 20
    n_trials = 100
    seed_base = 42
    family = CircuitFamily.UNIVERSAL
    
    total_random = n_trials * len(optimizers)
    with tqdm(total=total_random, desc="E10 Random") as pbar:
        for trial in range(n_trials):
            config = CircuitConfig(
                n_qubits=n_qubits,
                depth=depth,
                family=family,
                seed=seed_base + trial,
                entanglement_density=0.3,
            )
            
            circuits = generate_circuit_batch(config, 1, metrics_calculator)
            circuit, metrics = circuits[0]
            
            for opt_name, optimizer in optimizers.items():
                result = optimizer.optimize(circuit, target=circuit)
                
                results.append({
                    "experiment": 10,
                    "part": "random",
                    "circuit_family": "Universal",
                    "circuit_type": "random",
                    "n_qubits": n_qubits,
                    "depth": depth,
                    "trial": trial,
                    "seed": seed_base + trial,
                    "optimizer": opt_name,
                    "gate_count": metrics.gate_count,
                    "original_size": result.original_size,
                    "optimized_size": result.optimized_size,
                    "reduction": result.reduction,
                    "fidelity": result.fidelity,
                    "success": result.success,
                    "runtime_seconds": result.runtime_seconds,
                })
                
                pbar.update(1)
    
    # Part 2: Structured circuits
    print("E10 Part 2: Structured circuits")
    n_qubits = 5
    depth = 20
    n_trials = 100
    seed_base = 142
    structure = StructureType.BRICKWORK
    
    total_structured = n_trials * len(optimizers)
    with tqdm(total=total_structured, desc="E10 Structured") as pbar:
        for trial in range(n_trials):
            config = CircuitConfig(
                n_qubits=n_qubits,
                depth=depth,
                family=CircuitFamily.STRUCTURED,
                seed=seed_base + trial,
                entanglement_density=0.3,
                structure_type=structure,
            )
            
            circuits = generate_circuit_batch(config, 1, metrics_calculator)
            circuit, metrics = circuits[0]
            
            for opt_name, optimizer in optimizers.items():
                result = optimizer.optimize(circuit, target=circuit)
                
                results.append({
                    "experiment": 10,
                    "part": "structured",
                    "circuit_family": "Structured",
                    "circuit_type": "brickwork",
                    "n_qubits": n_qubits,
                    "depth": depth,
                    "trial": trial,
                    "seed": seed_base + trial,
                    "optimizer": opt_name,
                    "gate_count": metrics.gate_count,
                    "original_size": result.original_size,
                    "optimized_size": result.optimized_size,
                    "reduction": result.reduction,
                    "fidelity": result.fidelity,
                    "success": result.success,
                    "runtime_seconds": result.runtime_seconds,
                })
                
                pbar.update(1)
    
    # Part 3: Real circuits
    print("E10 Part 3: Real circuits")
    real_circuits = generate_real_circuits()
    
    total_real = len(real_circuits) * len(optimizers)
    with tqdm(total=total_real, desc="E10 Real") as pbar:
        for circuit_name, n, circuit in real_circuits:
            metrics = metrics_calculator.calculate(circuit)
            
            for opt_name, optimizer in optimizers.items():
                result = optimizer.optimize(circuit, target=circuit)
                
                results.append({
                    "experiment": 10,
                    "part": "real",
                    "circuit_family": circuit_name,
                    "circuit_type": circuit_name,
                    "n_qubits": n,
                    "depth": circuit.depth(),
                    "trial": 0,
                    "seed": 0,
                    "optimizer": opt_name,
                    "gate_count": metrics.gate_count,
                    "original_size": result.original_size,
                    "optimized_size": result.optimized_size,
                    "reduction": result.reduction,
                    "fidelity": result.fidelity,
                    "success": result.success,
                    "runtime_seconds": result.runtime_seconds,
                })
                
                pbar.update(1)
    
    # Save results
    df = pd.DataFrame(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"e10_phase1_vs_phase2_{timestamp}.csv"
    df.to_csv(csv_path, index=False)
    
    # Metadata
    metadata = {
        "experiment_id": "E10",
        "description": "Phase 1 vs Phase 2 optimization comparison",
        "optimizers": list(optimizers.keys()),
        "circuit_families": ["Universal (random)", "Structured (brickwork)", "Real (QFT/GHZ/CNOT)"],
        "n_trials_random": n_trials,
        "n_trials_structured": n_trials,
        "n_real_circuits": len(real_circuits),
        "timestamp": datetime.now().isoformat(),
    }
    
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nE10 complete: {len(df)} records saved to {csv_path}")
    
    # Summary
    for part in ["random", "structured", "real"]:
        print(f"\n{part.upper()}:")
        sub = df[df["part"] == part]
        for opt_name in optimizers.keys():
            opt_sub = sub[sub["optimizer"] == opt_name]
            print(f"  {opt_name}: mean reduction={opt_sub['reduction'].mean():.4f}, fidelity={opt_sub['fidelity'].mean():.6f}")
    
    return df


if __name__ == "__main__":
    run_e10()
