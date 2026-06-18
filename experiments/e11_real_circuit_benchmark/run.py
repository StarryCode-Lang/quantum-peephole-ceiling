"""E11: Real-circuit optimizer benchmark.

Runs project optimizers on non-random benchmark circuits (QFT, GHZ, CNOT-chain,
Bernstein-Vazirani, QAOA-like, VQE-like, and hardware-efficient ansatz circuits).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import (  # noqa: E402
    average_gate_fidelity,
    circuit_sha256,
    gate_counts,
    generate_real_circuit_suite,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase2.commutation_rewriter import CommutationRewriter, HybridCommuteRewrite  # noqa: E402
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "1.0.0"
EXPERIMENT_ID = "E11"
VERSION = "4.0.0"


def build_optimizers() -> Dict[str, object]:
    """Create optimizers used in the real-circuit benchmark."""
    return {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "commutation_phase2": CommutationRewriter(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }


def run(mode: str, seed: int, max_qubits_fidelity: int) -> pd.DataFrame:
    """Run E11 and return the result table."""
    run_id = f"e11_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v4" / "e11"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    circuits = generate_real_circuit_suite(mode=mode, seed=seed)
    optimizers = build_optimizers()

    rows: List[dict] = []
    for trial, bench in enumerate(circuits):
        circuit = bench.circuit
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
                    # Could not recompute exactly; result.fidelity may be a
                    # structural-similarity estimate from the optimizer's
                    # last-resort fallback (see base.py calculate_fidelity).
                    fidelity = result.fidelity
                    fidelity_method = "structural_estimate" if fidelity is not None else "unavailable"

            row = {
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "circuit_id": bench.circuit_id,
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
            }
            rows.append(row)

    df = pd.DataFrame(rows)
    csv_path = output_dir / f"e11_real_circuit_benchmark_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata.update(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "description": "Real-circuit optimizer benchmark",
            "mode": mode,
            "seed": seed,
            "max_qubits_fidelity": max_qubits_fidelity,
            "canonical_data_file": csv_path.name,
            "n_input_circuits": len(circuits),
            "n_rows": len(df),
            "optimizers": list(optimizers.keys()),
            "circuit_families": sorted({bench.family for bench in circuits}),
        }
    )
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"E11 complete: {len(df)} rows -> {csv_path}")
    print(df.groupby(["circuit_family", "optimizer"])["reduction"].mean().to_string())
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E11 real-circuit optimizer benchmark")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-qubits-fidelity", type=int, default=10)
    args = parser.parse_args()
    run(mode=args.mode, seed=args.seed, max_qubits_fidelity=args.max_qubits_fidelity)


if __name__ == "__main__":
    main()
