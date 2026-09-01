"""Fail-closed paired analysis for the pre-paper noise-aware validation.

Sampling seeds are repeated measurements.  The descriptive design cell is
``circuit × backend snapshot × transpile level × optimizer output``; neither
shots nor seeds are treated as independent circuits.  The experiment remains
a calibration-snapshot simulation and cannot support a real-QPU claim.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


PAIR_KEY = [
    "circuit_id",
    "backend_name",
    "transpile_optimization_level",
    "sampler",
    "seed_simulator",
]
CELL_KEY = [
    "circuit_id",
    "backend_name",
    "transpile_optimization_level",
    "version",
]


def paired_analysis(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    required = set(PAIR_KEY) | {
        "version",
        "output_sha256",
        "logical_reduction",
        "transpiled_2q_reduction",
        "hellinger_fidelity",
        "tvd",
        "transpiled_2q_depth",
        "scheduled_duration_seconds",
        "calibration_success_probability",
        "unitary_equivalence_method",
        "unitary_equivalence_status",
        "unitary_equivalence_is_verified",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"missing required hardware-validation columns: {missing}")

    originals = frame[frame["version"] == "original"]
    if originals.duplicated(PAIR_KEY).any():
        raise ValueError("original rows are not unique within the paired key")
    optimized = frame[frame["version"] != "original"].copy()
    reduced = optimized["logical_reduction"] > 0
    verified_values = optimized["unitary_equivalence_is_verified"]
    if verified_values.dtype == bool:
        verified = verified_values
    else:
        verified = verified_values.astype(str).str.lower().map({
            "true": True, "false": False
        })
        if verified.isna().any():
            raise ValueError("invalid unitary_equivalence_is_verified encoding")
    if (reduced & ~verified).any():
        raise ValueError("a logically reduced output lacks verified equivalence")
    reference = originals.set_index(PAIR_KEY)[[
        "hellinger_fidelity",
        "tvd",
        "transpiled_2q_depth",
        "scheduled_duration_seconds",
        "calibration_success_probability",
    ]]
    optimized = optimized.join(reference, on=PAIR_KEY, rsuffix="_original")
    if optimized["hellinger_fidelity_original"].isna().any():
        raise ValueError("at least one optimized row has no paired original")

    optimized["hellinger_gain"] = (
        optimized["hellinger_fidelity"]
        - optimized["hellinger_fidelity_original"]
    )
    optimized["tvd_improvement"] = optimized["tvd_original"] - optimized["tvd"]
    optimized["two_qubit_depth_reduction"] = np.where(
        optimized["transpiled_2q_depth_original"] > 0,
        1.0
        - optimized["transpiled_2q_depth"]
        / optimized["transpiled_2q_depth_original"],
        0.0,
    )
    optimized["duration_reduction"] = np.where(
        optimized["scheduled_duration_seconds_original"] > 0,
        1.0
        - optimized["scheduled_duration_seconds"]
        / optimized["scheduled_duration_seconds_original"],
        0.0,
    )
    optimized["calibration_success_gain"] = (
        optimized["calibration_success_probability"]
        - optimized["calibration_success_probability_original"]
    )

    noisy = optimized[optimized["sampler"] == "aer_noisy_fakebackend"].copy()
    cells = noisy.groupby(CELL_KEY, as_index=False).agg(
        circuit_family=("circuit_family", "first"),
        output_sha256=("output_sha256", "first"),
        n_seed_repeats=("seed_simulator", "nunique"),
        logical_reduction=("logical_reduction", "first"),
        transpiled_2q_reduction=("transpiled_2q_reduction", "first"),
        two_qubit_depth_reduction=("two_qubit_depth_reduction", "first"),
        duration_reduction=("duration_reduction", "first"),
        calibration_success_gain=("calibration_success_gain", "first"),
        hellinger_gain_mean=("hellinger_gain", "mean"),
        hellinger_gain_min=("hellinger_gain", "min"),
        hellinger_gain_max=("hellinger_gain", "max"),
        tvd_improvement_mean=("tvd_improvement", "mean"),
    )
    eligible = cells[cells["logical_reduction"] > 0].copy()
    summaries = []
    for version, group in eligible.groupby("version"):
        summaries.append({
            "version": version,
            "n_design_cells": int(len(group)),
            "n_distinct_circuits": int(group["circuit_id"].nunique()),
            "n_backend_snapshots": int(group["backend_name"].nunique()),
            "hellinger_gain_mean_across_cells": float(group["hellinger_gain_mean"].mean()),
            "hellinger_gain_worst_cell": float(group["hellinger_gain_mean"].min()),
            "cells_positive_hellinger_gain": int((group["hellinger_gain_mean"] > 0).sum()),
            "duration_reduction_mean_across_cells": float(group["duration_reduction"].mean()),
            "calibration_success_gain_mean_across_cells": float(
                group["calibration_success_gain"].mean()
            ),
        })

    duplicate_outputs = (
        eligible.groupby([
            "circuit_id", "backend_name", "transpile_optimization_level",
            "output_sha256",
        ])["version"].nunique()
    )
    report = {
        "status": "descriptive_calibration_snapshot_simulation",
        "experimental_unit": "distinct input circuit",
        "design_cell": "circuit x backend calibration snapshot x transpile level x optimizer output",
        "sampling_seed_role": "repeated measurement, not independent circuit",
        "n_input_circuits": int(frame["circuit_id"].nunique()),
        "n_backend_snapshots": int(frame["backend_name"].nunique()),
        "n_transpile_levels": int(frame["transpile_optimization_level"].nunique()),
        "n_run_rows": int(len(frame)),
        "n_eligible_design_cells": int(len(eligible)),
        "n_duplicate_output_groups_across_optimizer_labels": int(
            (duplicate_outputs > 1).sum()
        ),
        "optimizer_summaries": summaries,
        "claim_boundary": (
            "Supports paired noise-model evidence under two archived calibration "
            "snapshots only; it is not real-QPU, device-transfer, or broad-family evidence."
        ),
    }
    return cells, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    cells, report = paired_analysis(pd.read_csv(args.runs))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cells.to_csv(args.output_dir / "paired_noise_aware_cells.csv", index=False)
    with (args.output_dir / "hardware_validation_report.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
