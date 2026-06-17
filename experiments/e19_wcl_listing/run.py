"""E19: Wire-Consecutive Listing (WCL) vs Layer-by-Layer (LBL) experiment.

Theorem 1(b) proves that under LBL listing the Phase 1 action space S1(C)
is structurally empty for n>=2.  The near-zero Phase 1 reductions observed
in E1-E5 might therefore be a *listing artifact* rather than a true
structural ceiling.

This experiment tests whether reordering gates into Wire-Consecutive Listing
(WCL) before the greedy scan produces non-zero Phase 1 reduction.

Design
------
- n = 5 qubits (universal random circuits)
- depth = 1..50 (50 depths)
- 100 trials per depth  ->  5 000 circuits total
- Two listing models: LBL (original Greedy) and WCL (preprocessed Greedy)
- Records: depth, listing_model, reduction, fidelity, runtime

Key Question
------------
If WCL produces non-zero Phase 1 reduction, the structural ceiling is
listing-dependent.  If still ~0 %, the ceiling is real.

Version: 1.0.0
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.generator_v2 import (  # noqa: E402
    CircuitConfig,
    CircuitFamily,
    generate_circuit,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor  # noqa: E402
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "1.0.0"
EXPERIMENT_ID = "E19"
VERSION = "5.0.0"

# Fixed experiment parameters
N_QUBITS = 5
DEPTH_MIN = 1
DEPTH_MAX = 50
TRIALS_PER_DEPTH = 100


def run(seed: int) -> pd.DataFrame:
    """Run E19: WCL vs LBL listing experiment.

    Parameters
    ----------
    seed : int
        Base random seed.  Each trial uses ``seed * 1_000_000 + depth * 100 + trial``
        for full reproducibility.

    Returns
    -------
    pd.DataFrame
        One row per (depth, trial, listing_model) combination.
    """
    run_id = f"e19_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v6" / "e19"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)

    # Optimizers: LBL (default) and WCL (wire_traversal=True)
    greedy_lbl = GreedyGateCancellation(success_reduction=0.01, wire_traversal=False)
    greedy_wcl = GreedyGateCancellation(success_reduction=0.01, wire_traversal=True)

    # Also record WCL preprocessing alone (without greedy) to isolate listing effect
    wcl_preprocessor = WireTraversalPreprocessor()

    rows: List[dict] = []
    total_trials = (DEPTH_MAX - DEPTH_MIN + 1) * TRIALS_PER_DEPTH
    completed = 0

    for depth in range(DEPTH_MIN, DEPTH_MAX + 1):
        for trial in range(TRIALS_PER_DEPTH):
            trial_seed = seed * 1_000_000 + depth * 100 + trial

            # Generate random universal circuit
            circuit = generate_circuit(
                n_qubits=N_QUBITS, depth=depth, seed=trial_seed,
                family=CircuitFamily.UNIVERSAL,
            )
            original_size = circuit.size()

            if original_size == 0:
                completed += 1
                continue

            # ---- LBL: standard greedy (original listing) ----
            t0 = time.time()
            result_lbl = greedy_lbl.optimize(circuit, target=circuit)
            runtime_lbl = time.time() - t0

            rows.append({
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "n_qubits": N_QUBITS,
                "depth": depth,
                "trial": trial,
                "seed": trial_seed,
                "listing_model": "LBL",
                "original_size": original_size,
                "optimized_size": result_lbl.optimized_size,
                "reduction": result_lbl.reduction,
                "fidelity": result_lbl.fidelity,
                "runtime_seconds": runtime_lbl,
                "success": bool(result_lbl.success),
            })

            # ---- WCL: greedy with wire-traversal preprocessing ----
            t0 = time.time()
            result_wcl = greedy_wcl.optimize(circuit, target=circuit)
            runtime_wcl = time.time() - t0

            rows.append({
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "n_qubits": N_QUBITS,
                "depth": depth,
                "trial": trial,
                "seed": trial_seed,
                "listing_model": "WCL",
                "original_size": original_size,
                "optimized_size": result_wcl.optimized_size,
                "reduction": result_wcl.reduction,
                "fidelity": result_wcl.fidelity,
                "runtime_seconds": runtime_wcl,
                "success": bool(result_wcl.success),
            })

            completed += 1
            if completed % 500 == 0:
                print(f"  Progress: {completed}/{total_trials} trials "
                      f"({100 * completed / total_trials:.1f}%)")

    df = pd.DataFrame(rows)
    csv_path = output_dir / f"e19_wcl_listing_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    # Save metadata
    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "description": "WCL vs LBL listing model comparison for Phase 1 ceiling",
        "seed": seed,
        "n_qubits": N_QUBITS,
        "depth_range": [DEPTH_MIN, DEPTH_MAX],
        "trials_per_depth": TRIALS_PER_DEPTH,
        "total_circuits": (DEPTH_MAX - DEPTH_MIN + 1) * TRIALS_PER_DEPTH,
        "canonical_data_file": csv_path.name,
        "n_rows": len(df),
    })
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    # Print summary
    print(f"\nE19 complete: {len(df)} rows -> {csv_path}")
    print("\n--- Summary by listing model ---")
    if "reduction" in df.columns:
        summary = df.groupby("listing_model").agg({
            "reduction": ["mean", "std", "min", "max"],
            "fidelity": "mean",
            "success": "mean",
            "runtime_seconds": "mean",
        })
        print(summary.to_string())

    print("\n--- Reduction by depth (first 10 and last 10) ---")
    depth_summary = df.groupby(["depth", "listing_model"])["reduction"].mean().unstack()
    if "LBL" in depth_summary.columns and "WCL" in depth_summary.columns:
        depth_summary["wcl_minus_lbl"] = depth_summary["WCL"] - depth_summary["LBL"]
    print(depth_summary.head(10).to_string())
    print("...")
    print(depth_summary.tail(10).to_string())

    # Key conclusion
    lbl_mean = df[df["listing_model"] == "LBL"]["reduction"].mean()
    wcl_mean = df[df["listing_model"] == "WCL"]["reduction"].mean()
    print(f"\n--- Key Result ---")
    print(f"LBL mean reduction: {lbl_mean:.6f}")
    print(f"WCL mean reduction: {wcl_mean:.6f}")
    if wcl_mean > 0.001 and wcl_mean > lbl_mean * 2:
        print("CONCLUSION: WCL produces non-zero Phase 1 reduction. "
              "The structural ceiling is listing-dependent.")
    else:
        print("CONCLUSION: WCL does NOT significantly improve Phase 1 reduction. "
              "The structural ceiling appears to be real, not a listing artifact.")

    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run E19: WCL vs LBL listing model comparison"
    )
    parser.add_argument("--seed", type=int, default=42,
                        help="Base random seed (default: 42)")
    args = parser.parse_args()
    run(seed=args.seed)


if __name__ == "__main__":
    main()
