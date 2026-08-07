"""Paired descriptive analysis for the non-canonical E31 pilot.

The pilot crosses three valid listings with three optimizer phases on the same
source circuits. This module reports paired listing contrasts and phase
progression; it does not fit or test a confirmatory interaction model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_CSV = PROJECT_ROOT / "data" / "v11" / "e31_listing_phase2b" / "e31_listing_phase2b_pilot.csv"
DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_CSV.parent
LISTINGS = ("LBL", "WCL", "SHUFFLE")
PHASES = ("phase1", "phase2a", "phase2b")
CORE_COLUMNS = {"circuit_id", "circuit_family", "listing_model", "phase", "reduction"}
PAIR_KEY_COLUMNS = ["circuit_id", "circuit_family", "listing_model", "phase"]


def validate_pilot_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate the paired-pilot schema and return a defensive copy."""
    missing = CORE_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"missing E31 columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("E31 pilot must not be empty")
    if frame.duplicated(PAIR_KEY_COLUMNS).any():
        raise ValueError("E31 pilot contains duplicate circuit/listing/phase rows")
    if not set(frame["listing_model"]).issubset(LISTINGS):
        raise ValueError("E31 pilot contains an unknown listing model")
    if not set(frame["phase"]).issubset(PHASES):
        raise ValueError("E31 pilot contains an unknown phase")
    if not np.isfinite(frame["reduction"].to_numpy(dtype=float)).all():
        raise ValueError("E31 reductions must be finite")
    if "listing_fidelity" in frame:
        fidelity = frame["listing_fidelity"].to_numpy(dtype=float)
        if (fidelity < 1.0 - 1e-10).any():
            raise ValueError("E31 contains a listing with fidelity below tolerance")
    return frame.copy()


def _stats(values: pd.Series) -> dict[str, Any]:
    values = values.dropna().astype(float)
    if values.empty:
        raise ValueError("cannot summarize an empty contrast")
    return {
        "n_circuits": int(values.size),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "std": float(values.std(ddof=1)) if values.size > 1 else 0.0,
        "min": float(values.min()),
        "max": float(values.max()),
    }


def _wide_frame(frame: pd.DataFrame) -> pd.DataFrame:
    wide = frame.pivot(
        index=["circuit_id", "circuit_family", "listing_model"],
        columns="phase",
        values="reduction",
    ).reset_index()
    wide.columns.name = None
    missing = set(PHASES).difference(wide.columns)
    if missing:
        raise ValueError(f"E31 pilot is missing phase columns: {sorted(missing)}")
    return wide


def summarize_cells(frame: pd.DataFrame) -> pd.DataFrame:
    """Return one descriptive row for each listing x phase cell."""
    frame = validate_pilot_frame(frame)
    return (
        frame.groupby(["listing_model", "phase"], sort=True, as_index=False)
        .agg(
            n=("reduction", "size"),
            n_circuits=("circuit_id", "nunique"),
            mean=("reduction", "mean"),
            median=("reduction", "median"),
            std=("reduction", "std"),
            minimum=("reduction", "min"),
            maximum=("reduction", "max"),
        )
    )


def summarize_phase_deltas(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize paired Phase-2a/2b gains over Phase 1 by listing."""
    wide = _wide_frame(validate_pilot_frame(frame))
    rows: list[dict[str, Any]] = []
    for listing in LISTINGS:
        subset = wide[wide["listing_model"] == listing]
        for phase in ("phase2a", "phase2b"):
            values = subset[phase] - subset["phase1"]
            rows.append({
                "listing_model": listing,
                "contrast": f"{phase}_over_phase1",
                **_stats(values),
            })
    return pd.DataFrame(rows)


def compute_contrasts(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute paired listing deltas and listing x phase contrasts.

    ``phase*_vs_LBL`` is the same-circuit listing difference. The
    ``*_over_phase1`` rows subtract the LBL phase progression from the
    corresponding alternative listing progression, which is the descriptive
    difference-in-differences used for this pilot.
    """
    wide = _wide_frame(validate_pilot_frame(frame))
    baseline = wide[wide["listing_model"] == "LBL"].set_index("circuit_id")
    if baseline.empty:
        raise ValueError("E31 pilot requires LBL as the paired baseline")

    rows: list[dict[str, Any]] = []
    for listing in ("WCL", "SHUFFLE"):
        current = wide[wide["listing_model"] == listing].set_index("circuit_id")
        common = baseline.index.intersection(current.index)
        if len(common) == 0:
            raise ValueError(f"no paired circuits for listing {listing}")
        base = baseline.loc[common]
        alternative = current.loc[common]
        for phase in PHASES:
            values = alternative[phase] - base[phase]
            rows.append({
                "listing_model": listing,
                "contrast": f"{phase}_vs_LBL",
                **_stats(values),
            })
        for phase in ("phase2a", "phase2b"):
            values = (
                (alternative[phase] - alternative["phase1"])
                - (base[phase] - base["phase1"])
            )
            rows.append({
                "listing_model": listing,
                "contrast": f"{phase}_over_phase1",
                **_stats(values),
            })
    return pd.DataFrame(rows)


def analyze_pilot(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return all deterministic descriptive outputs for an E31 pilot frame."""
    frame = validate_pilot_frame(frame)
    return {
        "cell_summary": summarize_cells(frame),
        "phase_delta_summary": summarize_phase_deltas(frame),
        "contrasts": compute_contrasts(frame),
    }


def run(
    input_csv: Path | str = DEFAULT_INPUT_CSV,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Analyze an E31 pilot CSV and write non-canonical summaries."""
    input_csv = Path(input_csv)
    output_dir = Path(output_dir)
    if not input_csv.is_absolute():
        input_csv = PROJECT_ROOT / input_csv
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    frame = pd.read_csv(input_csv)
    outputs = analyze_pilot(frame)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs["cell_summary"].to_csv(output_dir / "e31_cell_summary.csv", index=False)
    outputs["phase_delta_summary"].to_csv(
        output_dir / "e31_phase_delta_summary.csv", index=False
    )
    outputs["contrasts"].to_csv(output_dir / "e31_contrasts.csv", index=False)
    summary = {
        "experiment_id": "E31-pilot",
        "status": "supporting_noncanonical_pilot",
        "input_csv": str(input_csv),
        "n_rows": int(len(frame)),
        "n_source_circuits": int(frame["circuit_id"].nunique()),
        "n_families": int(frame["circuit_family"].nunique()),
        "confirmatory_interaction_test": False,
        "interpretation": (
            "Descriptive paired contrasts only; smoke-scale pilot does not "
            "establish a listing x phase interaction."
        ),
        "cell_summary": json.loads(outputs["cell_summary"].to_json(orient="records")),
        "phase_delta_summary": json.loads(
            outputs["phase_delta_summary"].to_json(orient="records")
        ),
        "contrasts": json.loads(outputs["contrasts"].to_json(orient="records")),
    }
    (output_dir / "e31_analysis_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    summary = run(args.input_csv, args.output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
