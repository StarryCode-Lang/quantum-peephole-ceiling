"""
PHASE-7 A4: Qiskit Pass-Isolation Comparison.
================================================
Compares our Phase-1 (greedy) and Phase-2 (commutation) individually
against Qiskit's individual optimization passes:
  - CXCancellation
  - CommutativeCancellation
  - Optimize1qGates

This addresses the P1 issue of unfair compiler comparison by running
each compiler's passes in isolation (not the full pipeline).

Output: data/v5/qiskit_pass_isolation.csv
"""

from __future__ import annotations

import sys
import time
import warnings
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import PassManager

from src.circuits.real_benchmarks import (
    make_cnot_chain, make_qft, make_bernstein_vazirani,
    make_random_clifford, make_ghz,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase2.commutation_rewriter import CommutationRewriter


def _count_metrics(circuit):
    """Count gate count, depth, 2Q gates, CNOT for a circuit."""
    gate_count = int(circuit.size())
    depth = int(circuit.depth() or 0)
    two_q = sum(1 for inst in circuit.data if inst.operation.num_qubits == 2)
    cnot = sum(1 for inst in circuit.data if inst.operation.name in ('cx', 'cnot'))
    return gate_count, depth, two_q, cnot


def _safe_ratio(orig, opt):
    return 1.0 - opt / orig if orig > 0 else 0.0


def run_pass_isolation():
    """Run Qiskit pass-isolation comparison."""

    output_dir = PROJECT_ROOT / "data/v5"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate 5 circuit families with multiple sizes
    circuit_generators = {
        "CNOT_chain": lambda n: make_cnot_chain(n, repeats=4),
        "QFT": lambda n: make_qft(n),
        "Oracle": lambda n: make_bernstein_vazirani(n, seed=42 + n),
        "RandomClifford": lambda n: make_random_clifford(n, depth=10, seed=42 + n),
        "GHZ": lambda n: make_ghz(n),
    }

    sizes = [3, 4, 5, 6, 7]

    # Our optimizers (individual)
    our_phase1 = GreedyGateCancellation(success_reduction=0.01)
    our_phase2 = CommutationRewriter(success_reduction=0.01)

    rows = []

    for family_name, gen_fn in circuit_generators.items():
        for n in sizes:
            try:
                circuit = gen_fn(n)
            except Exception as e:
                print(f"  [SKIP] {family_name} n={n}: {e}")
                continue

            orig_size, orig_depth, orig_2q, orig_cnot = _count_metrics(circuit)

            # --- Our Phase-1 (greedy) alone ---
            t0 = time.time()
            r1 = our_phase1.optimize(circuit, target=circuit)
            t1 = time.time() - t0
            opt_size_p1, _, _, _ = _count_metrics(r1.optimized_circuit)

            rows.append({
                "circuit_family": family_name,
                "n_qubits": n,
                "original_gate_count": orig_size,
                "compiler": "custom",
                "pass_name": "greedy_phase1",
                "optimized_gate_count": opt_size_p1,
                "reduction": r1.reduction,
                "fidelity": r1.fidelity,
                "runtime_seconds": t1,
                "original_depth": orig_depth,
                "original_2q": orig_2q,
                "original_cnot": orig_cnot,
            })

            # --- Our Phase-2 (commutation) alone ---
            t0 = time.time()
            r2 = our_phase2.optimize(circuit, target=circuit)
            t1 = time.time() - t0
            opt_size_p2, _, _, _ = _count_metrics(r2.optimized_circuit)

            rows.append({
                "circuit_family": family_name,
                "n_qubits": n,
                "original_gate_count": orig_size,
                "compiler": "custom",
                "pass_name": "commutation_phase2",
                "optimized_gate_count": opt_size_p2,
                "reduction": r2.reduction,
                "fidelity": r2.fidelity,
                "runtime_seconds": t1,
                "original_depth": orig_depth,
                "original_2q": orig_2q,
                "original_cnot": orig_cnot,
            })

            # --- Qiskit pass: CXCancellation ---
            try:
                from qiskit.transpiler.passes import CXCancellation
                pm = PassManager([CXCancellation()])
                t0 = time.time()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    opt_cx = pm.run(circuit)
                t1 = time.time() - t0
                opt_size_cx, _, _, _ = _count_metrics(opt_cx)
                rows.append({
                    "circuit_family": family_name,
                    "n_qubits": n,
                    "original_gate_count": orig_size,
                    "compiler": "qiskit",
                    "pass_name": "CXCancellation",
                    "optimized_gate_count": opt_size_cx,
                    "reduction": _safe_ratio(orig_size, opt_size_cx),
                    "fidelity": None,
                    "runtime_seconds": t1,
                    "original_depth": orig_depth,
                    "original_2q": orig_2q,
                    "original_cnot": orig_cnot,
                })
            except Exception as e:
                print(f"  [WARN] CXCancellation failed for {family_name} n={n}: {e}")

            # --- Qiskit pass: CommutativeCancellation ---
            try:
                from qiskit.transpiler.passes import CommutativeCancellation
                pm = PassManager([CommutativeCancellation()])
                t0 = time.time()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    opt_cc = pm.run(circuit)
                t1 = time.time() - t0
                opt_size_cc, _, _, _ = _count_metrics(opt_cc)
                rows.append({
                    "circuit_family": family_name,
                    "n_qubits": n,
                    "original_gate_count": orig_size,
                    "compiler": "qiskit",
                    "pass_name": "CommutativeCancellation",
                    "optimized_gate_count": opt_size_cc,
                    "reduction": _safe_ratio(orig_size, opt_size_cc),
                    "fidelity": None,
                    "runtime_seconds": t1,
                    "original_depth": orig_depth,
                    "original_2q": orig_2q,
                    "original_cnot": orig_cnot,
                })
            except Exception as e:
                print(f"  [WARN] CommutativeCancellation failed for {family_name} n={n}: {e}")

            # --- Qiskit pass: Optimize1qGates ---
            try:
                from qiskit.transpiler.passes import Optimize1qGates
                pm = PassManager([Optimize1qGates()])
                t0 = time.time()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    opt_1q = pm.run(circuit)
                t1 = time.time() - t0
                opt_size_1q, _, _, _ = _count_metrics(opt_1q)
                rows.append({
                    "circuit_family": family_name,
                    "n_qubits": n,
                    "original_gate_count": orig_size,
                    "compiler": "qiskit",
                    "pass_name": "Optimize1qGates",
                    "optimized_gate_count": opt_size_1q,
                    "reduction": _safe_ratio(orig_size, opt_size_1q),
                    "fidelity": None,
                    "runtime_seconds": t1,
                    "original_depth": orig_depth,
                    "original_2q": orig_2q,
                    "original_cnot": orig_cnot,
                })
            except Exception as e:
                print(f"  [WARN] Optimize1qGates failed for {family_name} n={n}: {e}")

    df = pd.DataFrame(rows)
    csv_path = output_dir / "qiskit_pass_isolation.csv"
    df.to_csv(csv_path, index=False)

    print(f"\nPass-isolation complete: {len(df)} rows -> {csv_path}")

    # Summary
    print("\n=== Summary by pass (mean reduction) ===")
    summary = df.groupby(["compiler", "pass_name"]).agg(
        mean_reduction=("reduction", "mean"),
        n_circuits=("circuit_family", "count"),
    )
    print(summary.to_string())

    print("\n=== Summary by family ===")
    fam_summary = df.groupby(["circuit_family", "pass_name"]).agg(
        mean_reduction=("reduction", "mean"),
    )
    print(fam_summary.to_string())

    return df


if __name__ == "__main__":
    run_pass_isolation()
