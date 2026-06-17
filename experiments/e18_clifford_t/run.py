"""E18: Clifford+T gate-set experiment.

Evaluates optimizer performance on circuits decomposed into the
Clifford+T universal gate set {H, S, T, CNOT} (and their inverses).
This tests whether Phase 2 commutation rewriting is effective under
the fault-tolerant gate set commonly used in quantum error correction.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit, transpile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import (  # noqa: E402
    average_gate_fidelity,
    circuit_sha256,
    gate_counts,
    generate_extended_suite,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase2.commutation_rewriter import (  # noqa: E402
    CommutationRewriter,
    HybridCommuteRewrite,
)
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "2.0.0"
EXPERIMENT_ID = "E18"
VERSION = "5.0.0"


def _safe_ratio(o, p):
    """Safe ratio computation: 1 - p/o, or 0.0 if o==0."""
    return 1.0 - p / o if o > 0 else 0.0

# Clifford+T basis gates
CLIFFORD_T_BASIS = ['h', 's', 'sdg', 't', 'tdg', 'cx', 'x', 'y', 'z']
CLIFFORD_T_DECOMPOSED_BASIS = ['h', 's', 'sdg', 't', 'tdg', 'cx']


def decompose_to_clifford_t(circuit: QuantumCircuit) -> QuantumCircuit:
    """Decompose a circuit into the Clifford+T gate set.

    Uses Qiskit transpiler to map arbitrary gates to {H, S, T, CNOT, X, Y, Z}.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        transpiled = transpile(
            circuit,
            basis_gates=CLIFFORD_T_BASIS,
            optimization_level=0,  # no optimization, just decompose
            seed_transpiler=42,
        )
    return transpiled


def count_t_gates(circuit: QuantumCircuit) -> Dict[str, int]:
    """Count T/Tdg gate occurrences."""
    ops = circuit.count_ops()
    return {
        "t_count": ops.get("t", 0),
        "tdg_count": ops.get("tdg", 0),
        "total_t": ops.get("t", 0) + ops.get("tdg", 0),
        "s_count": ops.get("s", 0),
        "sdg_count": ops.get("sdg", 0),
        "h_count": ops.get("h", 0),
        "cx_count": ops.get("cx", 0),
    }


def _count_metrics(circuit) -> Dict[str, float]:
    depth = int(circuit.depth() or 0)
    two_q = sum(1 for inst in circuit.data if inst.operation.num_qubits == 2)
    cnot = sum(1 for inst in circuit.data if inst.operation.name in ('cx', 'cnot'))
    t_count = sum(1 for inst in circuit.data if inst.operation.name in ('t', 'tdg'))
    return {"depth": depth, "two_q": two_q, "cnot": cnot, "t_count": t_count}


def run(mode: str, seed: int, max_qubits_fidelity: int) -> pd.DataFrame:
    """Run E18 Clifford+T gate-set experiment."""
    run_id = f"e18_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v5" / "e18"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    circuits = generate_extended_suite(mode=mode, seed=seed)

    our_optimizers = {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "commutation_phase2": CommutationRewriter(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }

    rows: List[dict] = []
    for trial, bench in enumerate(circuits):
        circuit = bench.circuit

        # Decompose to Clifford+T
        try:
            clifford_t_circuit = decompose_to_clifford_t(circuit)
        except Exception as exc:
            rows.append({
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "run_id": run_id,
                "circuit_id": bench.circuit_id,
                "circuit_family": bench.family,
                "n_qubits": circuit.num_qubits,
                "optimizer": "none",
                "status": f"decompose_error: {exc}",
            })
            continue

        input_hash = circuit_sha256(clifford_t_circuit)
        orig_counts = clifford_t_circuit.size()
        orig_m = _count_metrics(clifford_t_circuit)
        orig_t = count_t_gates(clifford_t_circuit)

        for opt_name, opt in our_optimizers.items():
            start = time.time()
            result = opt.optimize(clifford_t_circuit, target=clifford_t_circuit)
            runtime = time.time() - start

            output_hash = circuit_sha256(result.optimized_circuit)
            opt_m = _count_metrics(result.optimized_circuit)
            opt_t = count_t_gates(result.optimized_circuit)

            fidelity = result.fidelity
            if fidelity is None or fidelity == 0.0:
                exact = average_gate_fidelity(
                    result.optimized_circuit, clifford_t_circuit,
                    max_qubits=max_qubits_fidelity,
                )
                fidelity = exact if exact is not None else result.fidelity

            rows.append({
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "circuit_id": bench.circuit_id,
                "circuit_family": bench.family,
                "circuit_type": bench.circuit_type,
                "n_qubits": circuit.num_qubits,
                "gate_set": "clifford_t",
                "baseline_gate_count": orig_counts,
                "optimized_gate_count": result.optimized_size,
                "reduction": result.reduction,
                "reduction_pct": 100.0 * result.reduction,
                "depth_reduction": _safe_ratio(orig_m["depth"], opt_m["depth"]),
                "two_qubit_reduction": _safe_ratio(orig_m["two_q"], opt_m["two_q"]),
                "cnot_reduction": _safe_ratio(orig_m["cnot"], opt_m["cnot"]),
                "t_count_reduction": _safe_ratio(orig_m["t_count"], opt_m["t_count"]),
                "baseline_t_count": orig_m["t_count"],
                "optimized_t_count": opt_m["t_count"],
                "fidelity": fidelity,
                "success": bool(result.success),
                "runtime_seconds": runtime,
                "optimizer": opt_name,
                "seed": bench.seed,
                "trial": trial,
                "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                "source_sha256": file_sha256(script_path),
                "input_circuit_sha256": input_hash,
                "output_circuit_sha256": output_hash,
                "notes": bench.notes,
                "status": "ok",
            })

    df = pd.DataFrame(rows)
    csv_path = output_dir / f"e18_clifford_t_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata.update(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "description": "Clifford+T gate-set optimization experiment",
            "mode": mode,
            "seed": seed,
            "max_qubits_fidelity": max_qubits_fidelity,
            "gate_set": "clifford_t",
            "basis_gates": CLIFFORD_T_BASIS,
            "canonical_data_file": csv_path.name,
            "n_input_circuits": len(circuits),
            "n_rows": len(df),
            "circuit_families": sorted({bench.family for bench in circuits}),
        }
    )
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"E18 complete: {len(df)} rows -> {csv_path}")
    if "reduction" in df.columns:
        summary = (
            df.dropna(subset=["reduction"])
            .groupby(["optimizer"])
            .agg({
                "reduction": "mean",
                "depth_reduction": "mean",
                "cnot_reduction": "mean",
                "t_count_reduction": "mean",
            })
        )
        print(summary.to_string())
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E18 Clifford+T gate-set experiment")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-qubits-fidelity", type=int, default=10)
    args = parser.parse_args()
    run(mode=args.mode, seed=args.seed, max_qubits_fidelity=args.max_qubits_fidelity)


if __name__ == "__main__":
    main()
