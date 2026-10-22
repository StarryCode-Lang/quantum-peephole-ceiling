"""E49: source-relative re-baselining of the certified 128-source panel.

Motivation
----------
E48 (2026-10-20) established that the v14/v15 certified panel evaluates every
source *after* lossless basis normalisation into ``{h,x,rz,cx}``, and that this
normalisation is expansive (Adder 9.4x, VQE 7.25x, QAOA 5.68x source gate
count).  ``baseline_cost`` is the greedy fixed point of the *normalised*
circuit, so every headline ratio in the panel -- escape rate, local-optimum
count, "0% ceiling" -- is measured against an inflated denominator.

This script performs the disposition that E48 recommended: it reports the same
frozen panel twice, once panel-relative (the frozen contract) and once
source-relative (what a user of the original circuit would experience).  No
search is rerun and no frozen file is modified; every input is a frozen CSV.

Outputs (``docs/review/science_boost/2026-10-21_source_relative/``):
  * ``source_relative.csv``  -- one row per source, both denominators
  * ``family_summary.csv``   -- per-family aggregates
  * ``summary.json``         -- panel-level aggregates and claim boundaries

Read-only with respect to ``data/`` and ``release/``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLASSIFICATION = ROOT / "data" / "v15" / "e45_landscape_integration" / "classification_complete.csv"
INFLATION = ROOT / "docs" / "review" / "science_boost" / "2026-10-20_external_falsifier" / "baseline_inflation.csv"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-21_source_relative"

EXPERIMENT_ID = "E49_SOURCE_RELATIVE_REBASELINE_2026_10_21"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def certified_best(row: dict[str, str]) -> tuple[int, str]:
    """Best cost the frozen panel actually certifies, with its exactness class."""

    if row["best_cost_exactness"].startswith("EXACT"):
        return int(row["best_cost"]), "exact"
    # Witness-bounded cells: the endpoint cost is a certified upper bound.
    return int(row["witness_endpoint_cost"]), "witness_bounded_upper"


def pct_reduction(numerator: int, denominator: int) -> float | None:
    """Percentage reduction; undefined (null) when the denominator is empty."""

    if denominator == 0:
        return None
    return round(100.0 * numerator / denominator, 6)


def median(values: list[float]) -> float | None:
    """Median over the defined entries only (empty denominators are dropped)."""

    clean = [value for value in values if value is not None]
    return round(statistics.median(clean), 6) if clean else None


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    inflation = {
        row["source_id"]: row
        for row in csv.DictReader(INFLATION.open(newline="", encoding="utf-8"))
    }
    classification = list(csv.DictReader(CLASSIFICATION.open(newline="", encoding="utf-8")))
    if len(classification) != 128:
        raise RuntimeError(f"classification_row_count:{len(classification)}")
    if len(inflation) != 128:
        raise RuntimeError(f"inflation_row_count:{len(inflation)}")

    rows: list[dict[str, Any]] = []
    for row in classification:
        source_id = row["source_id"]
        inf = inflation[source_id]
        source_gates = int(inf["source_gate_count"])
        normalized = int(inf["normalized_gate_count"])
        baseline = int(row["baseline_cost"])
        best, best_class = certified_best(row)
        rows.append(
            {
                "source_id": source_id,
                "source_kind": row["source_kind"],
                "circuit_id": row["circuit_id"],
                "circuit_family": row["circuit_family"],
                "n_qubits": int(row["n_qubits"]),
                "classification_status": row["classification_status"],
                "certificate_tier": row["certificate_tier"],
                "source_gate_count": source_gates,
                "normalized_gate_count": normalized,
                "normalization_factor": round(normalized / source_gates, 6) if source_gates else None,
                "baseline_cost": baseline,
                "certified_best_cost": best,
                "certified_best_class": best_class,
                # Frozen contract: reduction against the greedy fixed point of
                # the normalised circuit.  This is the panel's own denominator.
                "reduction_vs_baseline_pct": pct_reduction(baseline - best, baseline),
                # What the user of the source circuit sees: the certified output
                # against the circuit they handed in.
                "reduction_vs_source_pct": pct_reduction(source_gates - best, source_gates),
                # Representation tax: how much larger the evaluated circuit is
                # than the source it came from.
                "representation_tax": round(best / source_gates, 6) if source_gates else None,
                "output_larger_than_source": best > source_gates,
                "escape_depth": row["escape_depth"],
            }
        )

    rows.sort(key=lambda item: (item["circuit_family"], item["circuit_id"]))

    fieldnames = list(rows[0].keys())
    with (OUTPUT_ROOT / "source_relative.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    families = sorted({row["circuit_family"] for row in rows})
    family_rows: list[dict[str, Any]] = []
    for family in families:
        subset = [row for row in rows if row["circuit_family"] == family]
        family_rows.append(
            {
                "circuit_family": family,
                "sources": len(subset),
                "real_sources": sum(1 for row in subset if row["source_kind"] == "e39"),
                "median_normalization_factor": median([row["normalization_factor"] for row in subset if row["normalization_factor"] is not None]),
                "median_baseline_cost": median([row["baseline_cost"] for row in subset]),
                "median_certified_best": median([row["certified_best_cost"] for row in subset]),
                "median_reduction_vs_baseline_pct": median(
                    [row["reduction_vs_baseline_pct"] for row in subset]
                ),
                "median_reduction_vs_source_pct": median(
                    [row["reduction_vs_source_pct"] for row in subset]
                ),
                "median_representation_tax": median([row["representation_tax"] for row in subset if row["representation_tax"] is not None]),
                "sources_output_larger_than_source": sum(
                    1 for row in subset if row["output_larger_than_source"]
                ),
                "escapes": sum(1 for row in subset if row["classification_status"] == "EXACT_ESCAPE"),
                "local_optima": sum(
                    1 for row in subset if row["classification_status"] == "EXACT_H_LOCAL_OPTIMUM"
                ),
            }
        )
    family_rows.sort(key=lambda item: -item["median_normalization_factor"])

    with (OUTPUT_ROOT / "family_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(family_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(family_rows)

    real = [row for row in rows if row["source_kind"] == "e39"]
    fixtures = [row for row in rows if row["source_kind"] == "e44"]
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-21",
        "inputs": {
            "classification_complete.csv": sha256(CLASSIFICATION),
            "baseline_inflation.csv": sha256(INFLATION),
        },
        "panel": {
            "sources": len(rows),
            "real_sources": len(real),
            "oracle_fixtures": len(fixtures),
            "escapes": sum(1 for row in rows if row["classification_status"] == "EXACT_ESCAPE"),
            "local_optima": sum(
                1 for row in rows if row["classification_status"] == "EXACT_H_LOCAL_OPTIMUM"
            ),
        },
        "denominator_contrast": {
            "median_reduction_vs_baseline_pct_all": median(
                [row["reduction_vs_baseline_pct"] for row in rows if row["reduction_vs_baseline_pct"] is not None]
            ),
            "median_reduction_vs_source_pct_all": median(
                [row["reduction_vs_source_pct"] for row in rows if row["reduction_vs_source_pct"] is not None]
            ),
            "median_reduction_vs_baseline_pct_real": median(
                [row["reduction_vs_baseline_pct"] for row in real if row["reduction_vs_baseline_pct"] is not None]
            ),
            "median_reduction_vs_source_pct_real": median(
                [row["reduction_vs_source_pct"] for row in real if row["reduction_vs_source_pct"] is not None]
            ),
            "sources_output_larger_than_source_all": sum(
                1 for row in rows if row["output_larger_than_source"]
            ),
            "sources_output_larger_than_source_real": sum(
                1 for row in real if row["output_larger_than_source"]
            ),
            "median_normalization_factor_all": median(
                [row["normalization_factor"] for row in rows if row["normalization_factor"] is not None]
            ),
            "median_normalization_factor_real": median(
                [row["normalization_factor"] for row in real if row["normalization_factor"] is not None]
            ),
            "max_normalization_factor": max(row["normalization_factor"] for row in rows if row["normalization_factor"] is not None),
            "max_normalization_source": max(rows, key=lambda row: row["normalization_factor"] or 0)[
                "circuit_id"
            ],
        },
        "escape_reading": {
            "panel_relative_escape_rate_all": round(
                sum(1 for row in rows if row["classification_status"] == "EXACT_ESCAPE") / len(rows), 6
            ),
            "panel_relative_escape_rate_real": round(
                sum(1 for row in real if row["classification_status"] == "EXACT_ESCAPE") / len(real), 6
            ),
            "note": (
                "Escape is a within-listing statement: it compares the certified best cost with "
                "the greedy fixed point of the same normalised listing. It is unaffected by the "
                "denominator choice; only the *size* of the reported saving is."
            ),
        },
        "families": family_rows,
        "claim_boundary": (
            "Source-relative percentages compare a circuit in the {h,x,rz,cx} basis against the "
            "source circuit's own gate count in its native basis. The two counts are not in the "
            "same gate set, so the source-relative column is a compilation-level indicator, not a "
            "peephole-level one. It is reported because the panel's ratios have so far been quoted "
            "without it; neither column is a cross-gate-set optimality claim."
        ),
        "script": "scripts/e49_source_relative_rebaseline.py",
    }
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(json.dumps(summary["denominator_contrast"], indent=2))
    print(json.dumps(summary["escape_reading"], indent=2))
    for item in family_rows:
        print(
            f"{item['circuit_family']:<20} n={item['sources']:>2} "
            f"tax={item['median_normalization_factor']} "
            f"vs_base={item['median_reduction_vs_baseline_pct']}% "
            f"vs_src={item['median_reduction_vs_source_pct']}% "
            f"bigger={item['sources_output_larger_than_source']:>2}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
