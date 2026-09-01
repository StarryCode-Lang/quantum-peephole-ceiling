"""Audit E31 semantic acceptance under a declared fidelity-threshold grid."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/v11/e31_factorial_pareto/formal_run/semantic_replay/semantic_replay_manifest.json"
DEFAULT_OUTPUT = ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis/fidelity_threshold_sensitivity.json"
THRESHOLDS = (
    "0.99",
    "0.999",
    "0.9999",
    "0.999999",
    "0.9999999999",
    "0.99999999999",
    "0.999999999999",
    "0.9999999999999",
    "1.0",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_audit() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cells = manifest["semantic_cells"]
    results = {
        threshold: {"semantic_cells_accepted": 0, "formal_success_rows_accepted": 0}
        for threshold in THRESHOLDS
    }
    fidelities: list[Decimal] = []
    rows_total = 0

    for binding in cells:
        certificate_path = ROOT / binding["cell_certificate_path"]
        if _sha256(certificate_path) != binding["cell_certificate_sha256"]:
            raise RuntimeError(f"cell certificate hash mismatch: {certificate_path}")
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        if certificate["status"] != "PASS":
            raise RuntimeError(f"non-passing semantic cell: {certificate_path}")
        fidelity = Decimal(str(certificate["independent_trace_average_gate_fidelity"]))
        formal_rows = int(certificate["formal_success_rows_bound"])
        fidelities.append(fidelity)
        rows_total += formal_rows
        for threshold in THRESHOLDS:
            if fidelity >= Decimal(threshold):
                results[threshold]["semantic_cells_accepted"] += 1
                results[threshold]["formal_success_rows_accepted"] += formal_rows

    expected_cells = int(manifest["unique_semantic_cells_replayed"])
    expected_rows = int(manifest["success_rows_verified_and_bound"])
    if len(fidelities) != expected_cells or rows_total != expected_rows:
        raise RuntimeError("semantic-cell or formal-row binding count mismatch")

    for counts in results.values():
        counts["semantic_cell_acceptance_rate"] = counts["semantic_cells_accepted"] / expected_cells
        counts["formal_success_row_acceptance_rate"] = counts["formal_success_rows_accepted"] / expected_rows

    frozen_threshold = "0.9999999999"
    if results[frozen_threshold]["semantic_cells_accepted"] != expected_cells:
        raise RuntimeError("frozen E31 fidelity threshold no longer accepts every sealed semantic cell")

    return {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_E31_FIDELITY_THRESHOLD_SENSITIVITY_COMPLETE",
        "source_manifest": MANIFEST.relative_to(ROOT).as_posix(),
        "source_manifest_sha256": _sha256(MANIFEST),
        "frozen_threshold": frozen_threshold,
        "semantic_cells": expected_cells,
        "formal_success_rows": expected_rows,
        "minimum_recorded_independent_fidelity": float(min(fidelities)),
        "maximum_recorded_independent_fidelity": float(max(fidelities)),
        "threshold_grid": results,
        "interpretation": (
            "All sealed successful cells remain accepted from 0.99 through the frozen "
            "0.9999999999 threshold. Stricter near-one thresholds are reported as numerical "
            "sensitivity only and do not retroactively redefine the frozen protocol."
        ),
        "limitation": (
            "This varies the acceptance threshold over already sealed independent trace-fidelity "
            "certificates; it is not a new optimizer run or a hardware-noise fidelity study."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_audit()
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": output.relative_to(ROOT).as_posix(), "status": payload["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
