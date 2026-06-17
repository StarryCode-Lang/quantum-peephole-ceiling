"""E13: Structural ceiling/action-space analysis for real benchmark circuits."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.structural_ceiling import analyze_structural_ceiling  # noqa: E402
from src.circuits.real_benchmarks import circuit_sha256, gate_counts, generate_real_circuit_suite  # noqa: E402
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase2.commutation_rewriter import HybridCommuteRewrite  # noqa: E402
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "1.0.0"
EXPERIMENT_ID = "E13"
VERSION = "4.0.0"


def run(mode: str, seed: int, window: int) -> pd.DataFrame:
    """Run structural ceiling analysis."""
    run_id = f"e13_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v4" / "e13"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    circuits = generate_real_circuit_suite(mode=mode, seed=seed)
    greedy = GreedyGateCancellation(success_reduction=0.01)
    hybrid = HybridCommuteRewrite(success_reduction=0.01)

    rows: List[dict] = []
    for trial, bench in enumerate(circuits):
        circuit = bench.circuit
        counts = gate_counts(circuit)
        ceiling = analyze_structural_ceiling(circuit, window=window)
        greedy_result = greedy.optimize(circuit, target=circuit)
        hybrid_result = hybrid.optimize(circuit, target=circuit)
        observed_best_gate_count = min(greedy_result.optimized_size, hybrid_result.optimized_size)
        observed_best_reduction = max(greedy_result.reduction, hybrid_result.reduction)
        best_optimizer = "hybrid_phase1_2" if hybrid_result.reduction >= greedy_result.reduction else "greedy_phase1"
        ceiling_gap = ceiling.structural_upper_bound_reduction - observed_best_reduction

        rows.append(
            {
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
                "commuting_block_count": ceiling.commuting_block_count,
                "mean_block_size": ceiling.mean_block_size,
                "max_block_size": ceiling.max_block_size,
                "cancellable_pair_count": ceiling.adjacent_cancellable_pairs,
                "mergeable_rotation_count": ceiling.mergeable_rotation_pairs,
                "adjacent_commuting_pairs": ceiling.adjacent_commuting_pairs,
                "commutation_enabled_inverse_pairs": ceiling.commutation_enabled_inverse_pairs,
                "structural_lower_bound": counts["gate_count_total"] - ceiling.theoretical_removed_gates_upper,
                "structural_upper_bound_reduction": ceiling.structural_upper_bound_reduction,
                "observed_best_gate_count": observed_best_gate_count,
                "observed_best_reduction": observed_best_reduction,
                "ceiling_gap": ceiling_gap,
                "ceiling_gap_pct": 100.0 * ceiling_gap,
                "best_optimizer": best_optimizer,
                "best_compiler": "not_evaluated_in_e13",
                "analysis_method": f"local_commutation_window_{window}",
                "analysis_version": VERSION,
                "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                "source_sha256": file_sha256(script_path),
                "input_circuit_sha256": circuit_sha256(circuit),
                "env_id": run_id,
                "notes": ceiling.notes,
                "seed": bench.seed,
                "trial": trial,
            }
        )

    df = pd.DataFrame(rows)
    csv_path = output_dir / f"e13_structural_ceiling_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata.update(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "description": "Structural ceiling/action-space analysis",
            "mode": mode,
            "seed": seed,
            "window": window,
            "canonical_data_file": csv_path.name,
            "n_input_circuits": len(circuits),
            "n_rows": len(df),
            "analysis_method": f"local_commutation_window_{window}",
        }
    )
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"E13 complete: {len(df)} rows -> {csv_path}")
    print(df.groupby("circuit_family")[["structural_upper_bound_reduction", "observed_best_reduction"]].mean().to_string())
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E13 structural ceiling analysis")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--window", type=int, default=10)
    args = parser.parse_args()
    run(mode=args.mode, seed=args.seed, window=args.window)


if __name__ == "__main__":
    main()
