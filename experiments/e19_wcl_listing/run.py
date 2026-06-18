"""E19: Wire-Consecutive Listing (WCL) vs Layer-by-Layer (LBL) experiment."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.generator_v2 import CircuitFamily, generate_circuit  # noqa: E402
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.provenance import run_metadata  # noqa: E402

SCHEMA_VERSION = "1.1.0"
EXPERIMENT_ID = "WCL-E19"
VERSION = "5.1.0"

FULL_N_QUBITS = 5
FULL_DEPTH_MIN = 1
FULL_DEPTH_MAX = 50
FULL_TRIALS_PER_DEPTH = 100

SMOKE_N_QUBITS = 3
SMOKE_DEPTH_MIN = 1
SMOKE_DEPTH_MAX = 3
SMOKE_TRIALS_PER_DEPTH = 2

WCL_SIGNIFICANCE_MIN = 0.001
WCL_LBL_RATIO_THRESHOLD = 2.0


def _mode_defaults(mode: str) -> tuple[int, int, int, int]:
    if mode == "smoke":
        return SMOKE_N_QUBITS, SMOKE_DEPTH_MIN, SMOKE_DEPTH_MAX, SMOKE_TRIALS_PER_DEPTH
    return FULL_N_QUBITS, FULL_DEPTH_MIN, FULL_DEPTH_MAX, FULL_TRIALS_PER_DEPTH


def _selected_optimizers(selection: str) -> list[tuple[str, GreedyGateCancellation, bool]]:
    optimizers = {
        "lbl": ("LBL", GreedyGateCancellation(success_reduction=0.01, wire_traversal=False), False),
        "wcl": ("WCL", GreedyGateCancellation(success_reduction=0.01, wire_traversal=True), True),
    }
    if selection == "both":
        return [optimizers["lbl"], optimizers["wcl"]]
    return [optimizers[selection]]


def run(
    seed: int,
    mode: str = "full",
    n_qubits: int | None = None,
    depth_min: int | None = None,
    depth_max: int | None = None,
    trials_per_depth: int | None = None,
    optimizer: str = "both",
) -> pd.DataFrame:
    default_n, default_depth_min, default_depth_max, default_trials = _mode_defaults(mode)
    n_qubits = default_n if n_qubits is None else n_qubits
    depth_min = default_depth_min if depth_min is None else depth_min
    depth_max = default_depth_max if depth_max is None else depth_max
    trials_per_depth = default_trials if trials_per_depth is None else trials_per_depth
    if depth_min > depth_max:
        raise ValueError("depth_min must be <= depth_max")
    if n_qubits < 1 or trials_per_depth < 1:
        raise ValueError("n_qubits and trials_per_depth must be positive")

    run_id = f"e19_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v6" / "e19"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    selected = _selected_optimizers(optimizer)

    rows: List[dict] = []
    total_trials = (depth_max - depth_min + 1) * trials_per_depth
    completed = 0

    for depth in range(depth_min, depth_max + 1):
        for trial in range(trials_per_depth):
            trial_seed = seed * 1_000_000 + depth * 100 + trial
            circuit = generate_circuit(
                n_qubits=n_qubits,
                depth=depth,
                seed=trial_seed,
                family=CircuitFamily.UNIVERSAL,
            )
            original_size = circuit.size()
            if original_size == 0:
                completed += 1
                continue

            for listing_model, opt, uses_wire_traversal in selected:
                t0 = time.time()
                result = opt.optimize(circuit, target=circuit)
                runtime = time.time() - t0
                rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "mode": mode,
                    "n_qubits": n_qubits,
                    "depth": depth,
                    "trial": trial,
                    "seed": trial_seed,
                    "optimizer": "greedy_gate_cancellation",
                    "listing_model": listing_model,
                    "wire_traversal": uses_wire_traversal,
                    "original_size": original_size,
                    "optimized_size": result.optimized_size,
                    "reduction": result.reduction,
                    "fidelity": result.fidelity,
                    "runtime_seconds": runtime,
                    "success": bool(result.success),
                })

            completed += 1
            if completed % 500 == 0 or mode == "smoke":
                print(f"  Progress: {completed}/{total_trials} trials ({100 * completed / total_trials:.1f}%)")

    df = pd.DataFrame(rows)
    csv_path = output_dir / f"e19_wcl_listing_{mode}_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "description": "WCL vs LBL listing model comparison for Phase 1 ceiling",
        "mode": mode,
        "seed": seed,
        "n_qubits": n_qubits,
        "depth_range": [depth_min, depth_max],
        "trials_per_depth": trials_per_depth,
        "optimizer_selection": optimizer,
        "optimizers_run": [item[0] for item in selected],
        "wire_traversal_by_listing_model": {item[0]: item[2] for item in selected},
        "total_circuits": total_trials,
        "canonical_data_file": csv_path.name,
        "n_rows": len(df),
    })
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"\nE19 complete: {len(df)} rows -> {csv_path}")
    print("\n--- Summary by listing model ---")
    if not df.empty and "reduction" in df.columns:
        summary = df.groupby("listing_model").agg({
            "reduction": ["mean", "std", "min", "max"],
            "fidelity": "mean",
            "success": "mean",
            "runtime_seconds": "mean",
        })
        print(summary.to_string())

        if set(["LBL", "WCL"]).issubset(set(df["listing_model"])):
            print("\n--- Reduction by depth (first 10 and last 10) ---")
            depth_summary = df.groupby(["depth", "listing_model"])["reduction"].mean().unstack()
            depth_summary["wcl_minus_lbl"] = depth_summary["WCL"] - depth_summary["LBL"]
            print(depth_summary.head(10).to_string())
            print("...")
            print(depth_summary.tail(10).to_string())

            lbl_mean = df[df["listing_model"] == "LBL"]["reduction"].mean()
            wcl_mean = df[df["listing_model"] == "WCL"]["reduction"].mean()
            print("\n--- Key Result ---")
            print(f"LBL mean reduction: {lbl_mean:.6f}")
            print(f"WCL mean reduction: {wcl_mean:.6f}")
            if wcl_mean > WCL_SIGNIFICANCE_MIN and wcl_mean > lbl_mean * WCL_LBL_RATIO_THRESHOLD:
                print("CONCLUSION: WCL produces non-zero Phase 1 reduction. The structural ceiling is listing-dependent.")
            else:
                print("CONCLUSION: WCL does NOT significantly improve Phase 1 reduction. The structural ceiling appears to be real, not a listing artifact.")

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E19: WCL vs LBL listing model comparison")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke", help="Run a quick smoke check or the full experiment")
    parser.add_argument("--seed", type=int, default=42, help="Base random seed")
    parser.add_argument("--n-qubits", type=int, default=None, help="Override qubit count")
    parser.add_argument("--depth-min", type=int, default=None, help="Override minimum depth")
    parser.add_argument("--depth-max", type=int, default=None, help="Override maximum depth")
    parser.add_argument("--depth-range", nargs=2, type=int, metavar=("MIN", "MAX"), default=None, help="Override depth range")
    parser.add_argument("--trials", type=int, default=None, help="Override trials per depth")
    parser.add_argument("--optimizer", choices=["lbl", "wcl", "both"], default="both", help="Select LBL, WCL, or both")
    args = parser.parse_args()
    depth_min = args.depth_min
    depth_max = args.depth_max
    if args.depth_range is not None:
        depth_min, depth_max = args.depth_range
    run(
        seed=args.seed,
        mode=args.mode,
        n_qubits=args.n_qubits,
        depth_min=depth_min,
        depth_max=depth_max,
        trials_per_depth=args.trials,
        optimizer=args.optimizer,
    )


if __name__ == "__main__":
    main()
