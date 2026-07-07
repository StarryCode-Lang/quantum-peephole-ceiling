"""E16: Phase 2 window-size scaling study.

Systematically evaluates how Phase 2 commutation-rewriting performance
varies with the search window size w in {2, 5, 10, 20, 50} across all
circuit families. Directly supports Conjecture 2 (context-dependent
super-constant improvement).

Review M5 caveat: the optimizer's objective function optimizes GATE COUNT
only.  The extended metrics (depth_reduction, two_qubit_reduction,
cnot_reduction) are reported for diagnostic purposes but are NON-TARGET
indicators — the optimizer does not directly optimize them.  A 0% depth
or CNOT reduction does NOT indicate optimizer failure; it simply means
the optimizer's gate-count objective did not incidentally reduce depth
or CNOT count.  Manuscripts must NOT claim depth/CNOT reduction as a
primary outcome of the optimizer.
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
EXPERIMENT_ID = "E16"
VERSION = "5.0.0"

WINDOW_SIZES = [2, 5, 10, 20, 50]


def run(mode: str, seed: int, max_qubits_fidelity: int,
        window_sizes: List[int] | None = None) -> pd.DataFrame:
    """Run E16 window-size scaling study."""
    if window_sizes is None:
        window_sizes = WINDOW_SIZES

    run_id = f"e16_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v5" / "e16"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    circuits = generate_extended_suite(mode=mode, seed=seed)

    rows: List[dict] = []
    for trial, bench in enumerate(circuits):
        circuit = bench.circuit
        input_hash = circuit_sha256(circuit)
        counts = gate_counts(circuit)

        for ws in window_sizes:
            # Phase-1-only baseline (independent of window size) to isolate
            # the marginal contribution of Phase-2 window scaling.
            for opt_cls, opt_label, opt_kwargs in [
                (GreedyGateCancellation, "phase1_only", {}),
                (CommutationRewriter, "commutation_phase2", {"window_size": ws}),
                (HybridCommuteRewrite, "hybrid_phase1_2", {"window_size": ws}),
            ]:
                optimizer = opt_cls(success_reduction=0.01, **opt_kwargs)
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

                ext = result.compute_extended_metrics(circuit)

                rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "circuit_id": bench.circuit_id,
                    "circuit_family": bench.family,
                    "circuit_type": bench.circuit_type,
                    "n_qubits": circuit.num_qubits,
                    "baseline_gate_count": result.original_size,
                    "optimized_gate_count": result.optimized_size,
                    "reduction": result.reduction,
                    "reduction_pct": 100.0 * result.reduction,
                    "depth_reduction": ext["depth_reduction"],
                    "two_qubit_reduction": ext["two_qubit_reduction"],
                    "cnot_reduction": ext["cnot_reduction"],
                    "window_size": ws,
                    "fidelity": fidelity,
                    "success": bool(result.success),
                    "iterations": result.iterations,
                    "runtime_seconds": runtime,
                    "optimizer": opt_label,
                    "seed": bench.seed,
                    "trial": trial,
                    "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                    "source_sha256": file_sha256(script_path),
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": output_hash,
                    "notes": bench.notes,
                })

    df = pd.DataFrame(rows)
    csv_path = output_dir / f"e16_window_scaling_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata.update(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "description": "Phase 2 window-size scaling study (includes Phase-1-only baseline)",
            "mode": mode,
            "seed": seed,
            "max_qubits_fidelity": max_qubits_fidelity,
            "window_sizes": window_sizes,
            "canonical_data_file": csv_path.name,
            "n_input_circuits": len(circuits),
            "n_rows": len(df),
            "circuit_families": sorted({bench.family for bench in circuits}),
            "m5_caveat": (
                "depth_reduction, two_qubit_reduction, and cnot_reduction are "
                "NON-TARGET diagnostic metrics (review M5). The optimizer "
                "optimizes GATE COUNT only. A 0% depth/CNOT reduction does "
                "NOT indicate optimizer failure."
            ),
        }
    )
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"E16 complete: {len(df)} rows -> {csv_path}")
    summary = (
        df.groupby(["optimizer", "window_size"])
        .agg({"reduction": "mean", "depth_reduction": "mean", "runtime_seconds": "mean"})
    )
    print(summary.to_string())

    # Review M5: runtime reminder that depth/CNOT metrics are NON-TARGET.
    if "depth_reduction" in df.columns or "cnot_reduction" in df.columns:
        import warnings
        warnings.warn(
            "E16 summary includes depth_reduction and cnot_reduction columns. "
            "These are NON-TARGET diagnostic metrics (review M5): the optimizer "
            "optimizes GATE COUNT only. A 0% depth or CNOT reduction does NOT "
            "indicate optimizer failure. Do not claim depth/CNOT reduction as "
            "a primary outcome in manuscripts.",
            UserWarning,
            stacklevel=2,
        )
        print(
            "\n[M5 caveat] depth_reduction and cnot_reduction are NON-TARGET "
            "diagnostic metrics. The optimizer optimizes gate count only.\n"
            "            A 0% depth/CNOT reduction does NOT indicate optimizer "
            "failure.\n"
        )
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E16 window-size scaling study")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-qubits-fidelity", type=int, default=10)
    parser.add_argument(
        "--window-sizes", type=int, nargs="+", default=None,
        help="Window sizes to evaluate (default: 2 5 10 20 50)",
    )
    args = parser.parse_args()
    run(mode=args.mode, seed=args.seed, max_qubits_fidelity=args.max_qubits_fidelity,
        window_sizes=args.window_sizes)


if __name__ == "__main__":
    main()
