"""
E10 Expanded: Phase 1 vs Phase 2 Optimization Comparison (v2)
==============================================================
Expanded from 627 rows to ~2400+ rows with:
- 200 random Universal circuits (was 100)
- 200 structured Brickwork circuits (was 100)
- 200 random Clifford circuits (NEW)
- Real circuits: QFT, GHZ, CNOT_chain, BV, QAOA, VQE, HardwareEfficient (was QFT/GHZ/CNOT only)
- Multiple instances per real family via parameterized sizes

Optimizers:
1. Greedy (Phase 1 only)
2. CommutationRewriter (Phase 2 only)
3. HybridCommuteRewrite (Phase 1 + Phase 2)

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

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from qiskit import QuantumCircuit

from src.circuits.generator_v2 import (
    CircuitConfig, CircuitFamily, StructureType,
    generate_circuit_batch, MetricsCalculator
)
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase2.commutation_rewriter import CommutationRewriter, HybridCommuteRewrite


def make_qft(n: int) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    for i in range(n):
        qc.h(i)
        for j in range(i + 1, n):
            qc.cp(np.pi / 2**(j - i), j, i)
    return qc


def make_ghz(n: int) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    return qc


def make_cnot_chain(n: int) -> QuantumCircuit:
    """CNOT chain with self-inverse pairs (100% Phase-1 reducible)."""
    qc = QuantumCircuit(n)
    for i in range(n - 1):
        qc.cx(i, i + 1)
        qc.cx(i, i + 1)
    return qc


def make_bernstein_vazirani(n: int, secret: int = None) -> QuantumCircuit:
    """Bernstein-Vazirani oracle circuit.

    Uses n+1 qubits: n input qubits + 1 ancilla (the standard BV
    construction).  The returned circuit's ``num_qubits`` is n+1.
    """
    if secret is None:
        secret = (1 << n) - 1  # all-ones secret
    qc = QuantumCircuit(n + 1)  # n input + 1 ancilla
    # Prepare ancilla in |->
    qc.x(n)
    qc.h(n)
    # Apply Hadamard to input qubits
    for i in range(n):
        qc.h(i)
    # Oracle: CNOT from input qubit i to ancilla if secret bit i is 1
    for i in range(n):
        if (secret >> i) & 1:
            qc.cx(i, n)
    # Apply Hadamard to input qubits
    for i in range(n):
        qc.h(i)
    return qc


def make_qaoa(n: int, depth: int = 2) -> QuantumCircuit:
    """Simplified fixed-angle QAOA for MaxCut on a line graph.

    NOTE: This is a *fixed-angle* benchmark, not a parameterized QAOA
    ansatz.  The angles gamma and beta are hardcoded (not free
    parameters) so the circuit is a concrete unitary suitable for
    gate-cancellation benchmarking.  For a parameterized QAOA study,
    use ``make_qaoa_line`` from ``real_benchmarks.py`` instead.
    """
    qc = QuantumCircuit(n)
    # Initial superposition
    for i in range(n):
        qc.h(i)
    # p layers of cost + mixer
    for p in range(depth):
        gamma = 0.5 + 0.1 * p
        beta = 0.3 + 0.1 * p
        # Cost: ZZ interactions on line graph edges
        for i in range(n - 1):
            qc.cx(i, i + 1)
            qc.rz(2 * gamma, i + 1)
            qc.cx(i, i + 1)
        # Mixer: X rotations
        for i in range(n):
            qc.rx(2 * beta, i)
    return qc


def make_vqe_twolocal(n: int, depth: int = 2) -> QuantumCircuit:
    """VQE TwoLocal ansatz with fixed (non-parameterized) angles.

    NOTE: This is a *fixed-angle* benchmark.  The rotation angles are
    hardcoded constants rather than free ``Parameter`` objects, so the
    circuit is a concrete unitary.  For a parameterized VQE study, use
    ``make_vqe_twolocal`` from ``real_benchmarks.py`` instead.
    """
    qc = QuantumCircuit(n)
    for layer in range(depth):
        # Rotation layer
        for i in range(n):
            qc.ry(0.5 * (layer + 1) + 0.1 * i, i)
            qc.rz(0.3 * (layer + 1) + 0.2 * i, i)
        # Entanglement layer
        for i in range(n - 1):
            qc.cx(i, i + 1)
    # Final rotation layer
    for i in range(n):
        qc.ry(0.7 + 0.1 * i, i)
        qc.rz(0.4 + 0.2 * i, i)
    return qc


def make_hardware_efficient(n: int, depth: int = 3) -> QuantumCircuit:
    """Hardware-efficient ansatz."""
    qc = QuantumCircuit(n)
    for layer in range(depth):
        for i in range(n):
            qc.rz(0.3 * layer + 0.1 * i, i)
            qc.sx(i)
            qc.rz(0.5 * layer + 0.2 * i, i)
        for i in range(0, n - 1, 2):
            qc.cx(i, i + 1)
        for i in range(1, n - 1, 2):
            qc.cx(i, i + 1)
    return qc


REAL_CIRCUIT_GENERATORS = {
    "QFT": [make_qft],
    "GHZ": [make_ghz],
    "CNOT_chain": [make_cnot_chain],
    "BV": [make_bernstein_vazirani],
    "QAOA": [make_qaoa],
    "VQE": [make_vqe_twolocal],
    "HardwareEfficient": [make_hardware_efficient],
}

# Parameterized sizes for each family
SIZES = [3, 4, 5, 6, 7]


def generate_all_real_circuits():
    """Generate parameterized real circuits across families and sizes."""
    circuits = []
    for family_name, generators in REAL_CIRCUIT_GENERATORS.items():
        for gen_fn in generators:
            for n in SIZES:
                try:
                    qc = gen_fn(n)
                    circuits.append((family_name, n, qc))
                except Exception as e:
                    print(f"  Warning: {family_name}(n={n}) failed: {e}")
    return circuits


def run_e10_expanded():
    """Run expanded E10."""

    output_dir = PROJECT_ROOT / "data/v5/e10"
    output_dir.mkdir(parents=True, exist_ok=True)

    optimizers = {
        "greedy_phase1": GreedyGateCancellation(),
        "commutation_phase2": CommutationRewriter(),
        "hybrid_phase1_2": HybridCommuteRewrite(),
    }

    results = []
    metrics_calculator = MetricsCalculator()

    # ---- Part 1: Random Universal circuits (200 trials) ----
    print("E10 Part 1: Random Universal circuits (200 trials)")
    n_qubits = 5
    depth = 20
    n_trials_random = 200
    seed_base = 42

    total = n_trials_random * len(optimizers)
    with tqdm(total=total, desc="E10 Random") as pbar:
        for trial in range(n_trials_random):
            config = CircuitConfig(
                n_qubits=n_qubits, depth=depth,
                family=CircuitFamily.UNIVERSAL,
                seed=seed_base + trial,
                entanglement_density=0.3,
            )
            circuits = generate_circuit_batch(config, 1, metrics_calculator)
            circuit, metrics = circuits[0]

            for opt_name, optimizer in optimizers.items():
                result = optimizer.optimize(circuit, target=circuit)
                results.append({
                    "experiment": 10, "part": "random",
                    "circuit_family": "Universal", "circuit_type": "random",
                    "n_qubits": n_qubits, "depth": depth,
                    "trial": trial, "seed": seed_base + trial,
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

    # ---- Part 2: Structured Brickwork circuits (200 trials) ----
    print("E10 Part 2: Structured Brickwork circuits (200 trials)")
    n_trials_structured = 200
    seed_base_struct = 142

    total = n_trials_structured * len(optimizers)
    with tqdm(total=total, desc="E10 Structured") as pbar:
        for trial in range(n_trials_structured):
            config = CircuitConfig(
                n_qubits=n_qubits, depth=depth,
                family=CircuitFamily.STRUCTURED,
                seed=seed_base_struct + trial,
                entanglement_density=0.3,
                structure_type=StructureType.BRICKWORK,
            )
            circuits = generate_circuit_batch(config, 1, metrics_calculator)
            circuit, metrics = circuits[0]

            for opt_name, optimizer in optimizers.items():
                result = optimizer.optimize(circuit, target=circuit)
                results.append({
                    "experiment": 10, "part": "structured",
                    "circuit_family": "Structured", "circuit_type": "brickwork",
                    "n_qubits": n_qubits, "depth": depth,
                    "trial": trial, "seed": seed_base_struct + trial,
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

    # ---- Part 3: Random Clifford circuits (200 trials, NEW) ----
    print("E10 Part 3: Random Clifford circuits (200 trials, NEW)")
    n_trials_clifford = 200
    seed_base_cliff = 5000

    total = n_trials_clifford * len(optimizers)
    with tqdm(total=total, desc="E10 Clifford") as pbar:
        for trial in range(n_trials_clifford):
            config = CircuitConfig(
                n_qubits=n_qubits, depth=depth,
                family=CircuitFamily.CLIFFORD,
                seed=seed_base_cliff + trial,
                entanglement_density=0.3,
            )
            circuits = generate_circuit_batch(config, 1, metrics_calculator)
            circuit, metrics = circuits[0]

            for opt_name, optimizer in optimizers.items():
                result = optimizer.optimize(circuit, target=circuit)
                results.append({
                    "experiment": 10, "part": "random_clifford",
                    "circuit_family": "RandomClifford", "circuit_type": "random_clifford",
                    "n_qubits": n_qubits, "depth": depth,
                    "trial": trial, "seed": seed_base_cliff + trial,
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

    # ---- Part 4: Real algorithm circuits (expanded, 7 families x 5 sizes) ----
    print("E10 Part 4: Real algorithm circuits (7 families x 5 sizes)")
    real_circuits = generate_all_real_circuits()

    total = len(real_circuits) * len(optimizers)
    with tqdm(total=total, desc="E10 Real") as pbar:
        for circuit_name, n, circuit in real_circuits:
            metrics = metrics_calculator.calculate(circuit)

            for opt_name, optimizer in optimizers.items():
                result = optimizer.optimize(circuit, target=circuit)
                results.append({
                    "experiment": 10, "part": "real",
                    "circuit_family": circuit_name, "circuit_type": circuit_name,
                    "n_qubits": circuit.num_qubits, "depth": circuit.depth(),
                    "param_n": n,
                    "trial": 0, "seed": 0,
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
    csv_path = output_dir / f"e10_expanded_phase1_vs_phase2_{timestamp}.csv"
    df.to_csv(csv_path, index=False)

    # Metadata
    metadata = {
        "experiment_id": "E10",
        "version": "2.0.0_expanded",
        "description": "Expanded Phase 1 vs Phase 2 comparison with adequate sample sizes",
        "optimizers": list(optimizers.keys()),
        "circuit_families": [
            "Universal (random, 200 trials)",
            "Structured/Brickwork (200 trials)",
            "RandomClifford (200 trials, NEW)",
            "Real: QFT/GHZ/CNOT_chain/BV/QAOA/VQE/HardwareEfficient (5 sizes each)",
        ],
        "n_trials_random": n_trials_random,
        "n_trials_structured": n_trials_structured,
        "n_trials_clifford": n_trials_clifford,
        "n_real_circuits": len(real_circuits),
        "total_rows": len(df),
        "timestamp": datetime.now().isoformat(),
        "fix_note": "Expanded from N=9/condition to N>=100/condition for statistical power",
    }

    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nE10 Expanded complete: {len(df)} records saved to {csv_path}")

    # Summary
    for part in ["random", "structured", "random_clifford", "real"]:
        print(f"\n{part.upper()}:")
        sub = df[df["part"] == part]
        if part == "real":
            for fam in sub["circuit_family"].unique():
                fam_sub = sub[sub["circuit_family"] == fam]
                print(f"  [{fam}]")
                for opt_name in optimizers.keys():
                    opt_sub = fam_sub[fam_sub["optimizer"] == opt_name]
                    print(f"    {opt_name}: mean_red={opt_sub['reduction'].mean():.4f}, "
                          f"mean_fid={opt_sub['fidelity'].mean():.6f}, n={len(opt_sub)}")
        else:
            for opt_name in optimizers.keys():
                opt_sub = sub[sub["optimizer"] == opt_name]
                print(f"  {opt_name}: mean_red={opt_sub['reduction'].mean():.4f}, "
                      f"mean_fid={opt_sub['fidelity'].mean():.6f}, n={len(opt_sub)}")

    return df


if __name__ == "__main__":
    run_e10_expanded()
