"""
E10 Expanded: Phase 1 vs Phase 2 with expanded Oracle/BV sample.
================================================================
Adds >=64 Oracle (Bernstein-Vazirani) instances per optimizer condition
to the original E10 experiment, addressing PHASE-7 Track A3 (P0).

Output: data/v5/e10/
"""

from __future__ import annotations

import sys
import json
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from qiskit import QuantumCircuit

from src.circuits.generator_v2 import (
    CircuitConfig, CircuitFamily, StructureType,
    generate_circuit_batch, MetricsCalculator
)
from src.circuits.real_benchmarks import make_bernstein_vazirani
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase2.commutation_rewriter import CommutationRewriter, HybridCommuteRewrite


def run_e10_expanded():
    """Run E10 with expanded Oracle/BV sample (>=64 instances per optimizer)."""

    output_dir = PROJECT_ROOT / "data/v5/e10"
    output_dir.mkdir(parents=True, exist_ok=True)

    optimizers = {
        "greedy_phase1": GreedyGateCancellation(),
        "commutation_phase2": CommutationRewriter(),
        "hybrid_phase1_2": HybridCommuteRewrite(),
    }

    results = []
    metrics_calculator = MetricsCalculator()

    # ---------------------------------------------------------------
    # Part 1: Random circuits (same as original E10)
    # ---------------------------------------------------------------
    print("E10-Expanded Part 1: Random circuits")
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

    # ---------------------------------------------------------------
    # Part 2: Structured circuits (same as original E10)
    # ---------------------------------------------------------------
    print("E10-Expanded Part 2: Structured circuits")
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

    # ---------------------------------------------------------------
    # Part 3: Real circuits (QFT, GHZ, CNOT chain -- original)
    # ---------------------------------------------------------------
    print("E10-Expanded Part 3: Real circuits (QFT/GHZ/CNOT)")
    real_circuits = []
    for n in [3, 4, 5]:
        qc = QuantumCircuit(n)
        for i in range(n):
            qc.h(i)
            for j in range(i + 1, n):
                qc.cp(np.pi / 2**(j - i), j, i)
        real_circuits.append(("QFT", n, qc))

    for n in [3, 4, 5]:
        qc = QuantumCircuit(n)
        qc.h(0)
        for i in range(n - 1):
            qc.cx(i, i + 1)
        real_circuits.append(("GHZ", n, qc))

    for n in [3, 4, 5]:
        qc = QuantumCircuit(n)
        for i in range(n - 1):
            qc.cx(i, i + 1)
            qc.cx(i, i + 1)
        real_circuits.append(("CNOT_chain", n, qc))

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

    # ---------------------------------------------------------------
    # Part 4: EXPANDED Oracle/BV sample (>=64 instances per optimizer)
    # This is the key addition for PHASE-7 A3 (P0).
    # We vary n_qubits (3-10) and seeds to get >=64 unique BV circuits.
    # ---------------------------------------------------------------
    print("E10-Expanded Part 4: Expanded Oracle/BV sample (>=64 instances)")
    bv_instances = []
    # 8 qubit-sizes x 8 seeds = 64 unique BV circuits
    for n in range(3, 11):       # n_qubits = 3..10
        for s in range(8):       # 8 different seeds per size
            seed_val = 1000 + n * 100 + s
            qc = make_bernstein_vazirani(n, seed=seed_val)
            bv_instances.append((f"BV_n{n}_s{seed_val}", n, seed_val, qc))

    print(f"  Generated {len(bv_instances)} unique BV/Oracle instances")

    total_bv = len(bv_instances) * len(optimizers)
    with tqdm(total=total_bv, desc="E10 Oracle/BV expanded") as pbar:
        for instance_id, n, seed_val, circuit in bv_instances:
            metrics = metrics_calculator.calculate(circuit)
            for opt_name, optimizer in optimizers.items():
                result = optimizer.optimize(circuit, target=circuit)
                results.append({
                    "experiment": 10,
                    "part": "oracle_bv_expanded",
                    "circuit_family": "Oracle",
                    "circuit_type": "bernstein_vazirani",
                    "instance_id": instance_id,
                    "n_qubits": n,
                    "depth": circuit.depth(),
                    "trial": seed_val,
                    "seed": seed_val,
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

    # ---------------------------------------------------------------
    # Save results
    # ---------------------------------------------------------------
    df = pd.DataFrame(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"e10_expanded_phase1_vs_phase2_{timestamp}.csv"
    df.to_csv(csv_path, index=False)

    # Metadata
    metadata = {
        "experiment_id": "E10-expanded",
        "description": "Phase 1 vs Phase 2 with expanded Oracle/BV sample (PHASE-7 A3)",
        "optimizers": list(optimizers.keys()),
        "circuit_families": [
            "Universal (random)", "Structured (brickwork)",
            "Real (QFT/GHZ/CNOT)", "Oracle/BV expanded (>=64 instances)"
        ],
        "n_trials_random": 100,
        "n_trials_structured": 100,
        "n_real_circuits": len(real_circuits),
        "n_bv_instances": len(bv_instances),
        "bv_instances_per_optimizer": len(bv_instances),
        "timestamp": datetime.now().isoformat(),
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nE10-Expanded complete: {len(df)} records -> {csv_path}")

    # Summary
    for part in ["random", "structured", "real", "oracle_bv_expanded"]:
        sub = df[df["part"] == part]
        if len(sub) == 0:
            continue
        print(f"\n{part.upper()}:")
        for opt_name in optimizers.keys():
            opt_sub = sub[sub["optimizer"] == opt_name]
            print(f"  {opt_name}: n={len(opt_sub)}, mean reduction={opt_sub['reduction'].mean():.4f}, "
                  f"fidelity={opt_sub['fidelity'].mean():.6f}")

    # Verify Oracle/BV condition has >=64 rows per optimizer
    bv_df = df[df["part"] == "oracle_bv_expanded"]
    for opt_name in optimizers.keys():
        n_rows = len(bv_df[bv_df["optimizer"] == opt_name])
        status = "PASS" if n_rows >= 64 else "FAIL"
        print(f"  [{status}] Oracle/BV instances for {opt_name}: {n_rows} (target >= 64)")

    return df


if __name__ == "__main__":
    run_e10_expanded()
