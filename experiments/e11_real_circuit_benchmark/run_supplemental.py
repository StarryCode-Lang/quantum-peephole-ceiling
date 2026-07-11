"""E11 supplemental replica to increase statistical power.

Generates an independent replica of the randomized benchmark families
(QAOA, VQE, HardwareEfficient, Grover, Adder, QuantumWalk, IQP,
RandomClifford, SurfaceCode, UCCSD_inspired, Oracle/Bernstein-Vazirani,
HaarRandom) for sizes n<=10, using a different seed.  The resulting CSV
is intended to be merged with the existing full-mode E11 data.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import (
    average_gate_fidelity,
    circuit_sha256,
    gate_counts,
    generate_real_circuit_suite,
    BenchmarkCircuit,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase2.commutation_rewriter import CommutationRewriter, HybridCommuteRewrite
from src.provenance import file_sha256, run_metadata

SCHEMA_VERSION = "1.0.0"
EXPERIMENT_ID = "E11"
VERSION = "4.0.0"
# Families identified as underpowered in the original full-mode E11 data
# (power < 0.80 for greedy_phase1 vs hybrid_phase1_2 reduction difference).
TARGET_FAMILIES = {"Grover", "IQP", "Oracle", "UCCSD_inspired"}


def build_optimizers() -> Dict[str, object]:
    return {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "commutation_phase2": CommutationRewriter(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }


def run(seed: int = 1042, max_qubits_fidelity: int = 10) -> pd.DataFrame:
    run_id = f"e11_supplemental_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v4" / "e11"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    full_suite = generate_real_circuit_suite(mode="full", seed=seed)
    circuits: List[BenchmarkCircuit] = [
        bench for bench in full_suite
        if bench.family in TARGET_FAMILIES
        and bench.circuit.num_qubits <= 10
    ]
    optimizers = build_optimizers()

    rows: List[dict] = []
    for trial, bench in enumerate(circuits):
        circuit = bench.circuit
        circuit_id = f"{bench.circuit_id}_r1"
        input_hash = circuit_sha256(circuit)
        counts = gate_counts(circuit)
        for optimizer_name, optimizer in optimizers.items():
            start = time.time()
            result = optimizer.optimize(circuit, target=circuit)
            runtime = time.time() - start
            output_hash = circuit_sha256(result.optimized_circuit)
            fidelity = result.fidelity
            fidelity_method = "optimizer_reported"
            if fidelity is None or fidelity == 0.0:
                exact = average_gate_fidelity(result.optimized_circuit, circuit, max_qubits=max_qubits_fidelity)
                if exact is not None:
                    fidelity = exact
                    fidelity_method = "recomputed_exact"
                else:
                    fidelity = result.fidelity
                    fidelity_method = "structural_estimate" if fidelity is not None else "unavailable"

            rows.append({
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "circuit_id": circuit_id,
                "circuit_family": bench.family,
                "circuit_type": bench.circuit_type,
                "benchmark_suite": bench.suite,
                "n_qubits": circuit.num_qubits,
                "depth": counts["depth"],
                "gate_count_total": counts["gate_count_total"],
                "gate_count_1q": counts["gate_count_1q"],
                "gate_count_2q": counts["gate_count_2q"],
                "gate_count_multiq": counts["gate_count_multiq"],
                "gate_counts_json": counts["gate_counts_json"],
                "baseline_gate_count": result.original_size,
                "optimized_gate_count": result.optimized_size,
                "reduction": result.reduction,
                "reduction_pct": 100.0 * result.reduction,
                "fidelity": fidelity,
                "fidelity_method": fidelity_method,
                "success": bool(result.success),
                "runtime_seconds": runtime,
                "optimizer": optimizer_name,
                "optimizer_version": VERSION,
                "optimizer_config_json": json.dumps(result.metadata, sort_keys=True, separators=(",", ":")),
                "compiler": "none",
                "compiler_version": "none",
                "compiler_optimization_level": "none",
                "compiler_config_id": "none",
                "seed": bench.seed,
                "trial": trial,
                "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                "source_sha256": file_sha256(script_path),
                "input_circuit_sha256": input_hash,
                "output_circuit_sha256": output_hash,
                "env_id": run_id,
                "notes": bench.notes,
            })

    df = pd.DataFrame(rows)
    csv_path = output_dir / f"e11_real_circuit_benchmark_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "description": "Supplemental replica for E11 real-circuit benchmark",
        "seed": seed,
        "max_qubits_fidelity": max_qubits_fidelity,
        "canonical_data_file": csv_path.name,
        "n_input_circuits": len(circuits),
        "n_rows": len(df),
        "optimizers": list(optimizers.keys()),
        "circuit_families": sorted({bench.family for bench in circuits}),
    })
    with (output_dir / f"metadata_{run_id}.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"E11 supplemental complete: {len(df)} rows -> {csv_path}")
    print(df.groupby(["circuit_family", "optimizer"])["reduction"].mean().to_string())
    return df


if __name__ == "__main__":
    run()
