"""E14: Extended benchmark suite evaluation (v5).

Runs all optimizers on the extended 15-family benchmark suite with
parameterized window sizes and extended metrics (depth, 2Q-gate, CNOT reduction).
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
    generate_extended_suite,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase2.commutation_rewriter import (  # noqa: E402
    CommutationRewriter,
    HybridCommuteRewrite,
)
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "2.0.0"
EXPERIMENT_ID = "E14"
VERSION = "5.0.0"

WINDOW_SIZES = [2, 5, 10, 20, 50]


def build_optimizers(window_size: int = 10,
                     success_reduction: float = 0.01) -> Dict[str, object]:
    """Create optimizers with configurable window size and success threshold.

    Parameters
    ----------
    window_size : int
        Commutation analysis window size (Phase-2 optimizers).
    success_reduction : float
        Minimum fractional gate-count reduction for an optimization to
        be deemed "meaningful" by the optimizer's success criterion.
    """
    return {
        "greedy_phase1": GreedyGateCancellation(success_reduction=success_reduction),
        "commutation_phase2": CommutationRewriter(
            success_reduction=success_reduction, window_size=window_size,
        ),
        "hybrid_phase1_2": HybridCommuteRewrite(
            success_reduction=success_reduction, window_size=window_size,
        ),
    }


def run(mode: str, seed: int, max_qubits_fidelity: int,
        window_sizes: List[int] | None = None) -> pd.DataFrame:
    """Run E14 and return the result table."""
    if window_sizes is None:
        window_sizes = [10]  # default: only one window size for smoke

    run_id = f"e14_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v5" / "e14"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    circuits = generate_extended_suite(mode=mode, seed=seed)

    rows: List[dict] = []
    for trial, bench in enumerate(circuits):
        circuit = bench.circuit
        input_hash = circuit_sha256(circuit)
        counts = gate_counts(circuit)

        for ws in window_sizes:
            optimizers = build_optimizers(window_size=ws)
            for optimizer_name, optimizer in optimizers.items():
                start = time.time()
                result = optimizer.optimize(circuit, target=circuit)
                runtime = time.time() - start

                output_hash = circuit_sha256(result.optimized_circuit)
                fidelity = result.fidelity
                if fidelity is None or fidelity == 0.0:
                    exact = average_gate_fidelity(
                        result.optimized_circuit, circuit,
                        max_qubits=max_qubits_fidelity,
                    )
                    fidelity = exact if exact is not None else result.fidelity

                # Compute extended metrics
                ext = result.compute_extended_metrics(circuit)

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
                    "baseline_gate_count": result.original_size,
                    "optimized_gate_count": result.optimized_size,
                    "reduction": result.reduction,
                    "reduction_pct": 100.0 * result.reduction,
                    # Extended metrics (P9)
                    "depth_reduction": ext["depth_reduction"],
                    "two_qubit_reduction": ext["two_qubit_reduction"],
                    "cnot_reduction": ext["cnot_reduction"],
                    "original_depth": ext["original_depth"],
                    "optimized_depth": ext["optimized_depth"],
                    "original_2q_gates": ext["original_2q_gates"],
                    "optimized_2q_gates": ext["optimized_2q_gates"],
                    "original_cnot_count": ext["original_cnot_count"],
                    "optimized_cnot_count": ext["optimized_cnot_count"],
                    # Window size (P6)
                    "window_size": ws,
                    "fidelity": fidelity,
                    "success": bool(result.success),
                    "runtime_seconds": runtime,
                    "optimizer": optimizer_name,
                    "optimizer_version": VERSION,
                    "optimizer_config_json": json.dumps(
                        result.metadata, sort_keys=True, separators=(",", ":"),
                    ),
                    "seed": bench.seed,
                    "trial": trial,
                    "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                    "source_sha256": file_sha256(script_path),
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": output_hash,
                    "notes": bench.notes,
                }
                rows.append(row)

    df = pd.DataFrame(rows)
    csv_path = output_dir / f"e14_extended_benchmark_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata.update(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "description": "Extended benchmark suite (v5, 15 families)",
            "mode": mode,
            "seed": seed,
            "max_qubits_fidelity": max_qubits_fidelity,
            "window_sizes": window_sizes,
            "canonical_data_file": csv_path.name,
            "n_input_circuits": len(circuits),
            "n_rows": len(df),
            "optimizers": list(build_optimizers().keys()),
            "circuit_families": sorted({bench.family for bench in circuits}),
        }
    )
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"E14 complete: {len(df)} rows -> {csv_path}")
    summary = (
        df.groupby(["circuit_family", "optimizer"])
        .agg({"reduction": "mean", "depth_reduction": "mean", "cnot_reduction": "mean"})
    )
    print(summary.to_string())
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E14 extended benchmark suite")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-qubits-fidelity", type=int, default=10)
    parser.add_argument(
        "--window-sizes", type=int, nargs="+", default=None,
        help="Window sizes to evaluate (default: [10] for smoke, all for full)",
    )
    args = parser.parse_args()
    ws = args.window_sizes
    if ws is None and args.mode == "full":
        ws = WINDOW_SIZES
    run(mode=args.mode, seed=args.seed, max_qubits_fidelity=args.max_qubits_fidelity,
        window_sizes=ws)


if __name__ == "__main__":
    main()
