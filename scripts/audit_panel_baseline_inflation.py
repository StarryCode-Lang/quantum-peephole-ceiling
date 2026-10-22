"""Audit: is the v14/v15 certified-panel baseline comparable to the source circuit?

Motivation (2026-10-20 science_boost run)
----------------------------------------
The E45/E46/E47 panels are built on ``normalized`` circuits produced by
``experiments.e45_development_grid.run.normalize_circuit``, which translates
every source into ``NAM_BASIS = ["h", "x", "rz", "cx"]`` with
``optimization_level=0``.  That translation is *lossless but expansive*: a
native ``u3`` becomes several ``rz``/``h`` gates, ``rzz`` becomes ``cx``+
``rz``, ``cz`` becomes ``cx``+``h``.

The frozen ``baseline_cost`` of the certified landscape is the gate count of the
greedy fixed point *of the normalized circuit*.  If the normalization inflates a
family by several times, then every "gate reduction" number in the certified
layer is measured against a baseline that is larger than the circuit the author
wrote, and it cannot be compared with any compiler benchmark that measures
against the source.

This script quantifies that inflation per family.  It reads only frozen files.

Output: ``docs/review/science_boost/2026-10-20_external_falsifier/baseline_inflation.csv``
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "v14" / "e45_full_development" / "normalization_manifest.csv"
CLASSIFICATION = ROOT / "data" / "v15" / "e45_landscape_integration" / "classification_complete.csv"
OUT = ROOT / "docs" / "review" / "science_boost" / "2026-10-20_external_falsifier"


def main() -> int:
    classification = {
        row["source_id"]: row
        for row in csv.DictReader(CLASSIFICATION.open(encoding="utf-8", newline=""))
    }
    rows: list[dict[str, object]] = []
    for row in csv.DictReader(MANIFEST.open(encoding="utf-8", newline="")):
        cls = classification.get(row["source_id"])
        if cls is None:
            continue
        source_gates = int(row["source_gate_count"])
        normalized = int(row["normalized_gate_count"])
        baseline = int(cls["baseline_cost"])
        rows.append(
            {
                "source_id": row["source_id"],
                "source_kind": row["source_kind"],
                "circuit_id": row["circuit_id"],
                "circuit_family": row["circuit_family"],
                "n_qubits": int(row["n_qubits"]),
                "source_gate_count": source_gates,
                "normalized_gate_count": normalized,
                "baseline_cost": baseline,
                "normalization_factor": round(normalized / max(1, source_gates), 3),
                "baseline_over_source": round(baseline / max(1, source_gates), 3),
                "baseline_minus_source": baseline - source_gates,
                "classification_status": cls["classification_status"],
            }
        )

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "baseline_inflation.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    agg: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        fam = str(row["circuit_family"])
        a = agg[fam]
        a["sources"] += 1
        a["source_gates"] += int(row["source_gate_count"])
        a["normalized"] += int(row["normalized_gate_count"])
        a["baseline"] += int(row["baseline_cost"])
        a["max_baseline_over_source"] = max(
            a["max_baseline_over_source"], float(row["baseline_over_source"])
        )

    summary = {
        "date": "2026-10-20",
        "panel_sources": len(rows),
        "families": {
            fam: {
                "sources": int(a["sources"]),
                "mean_source_gates": round(a["source_gates"] / a["sources"], 1),
                "mean_normalized_gates": round(a["normalized"] / a["sources"], 1),
                "mean_baseline_cost": round(a["baseline"] / a["sources"], 1),
                "mean_baseline_over_source": round(a["baseline"] / max(1.0, a["source_gates"]), 3),
                "max_baseline_over_source": round(a["max_baseline_over_source"], 3),
            }
            for fam, a in sorted(
                agg.items(), key=lambda kv: -kv[1]["baseline"] / max(1.0, kv[1]["source_gates"])
            )
        },
    }
    (OUT / "baseline_inflation.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8"
    )
    print(json.dumps(summary["families"], indent=1))
    inflated = [f for f, v in summary["families"].items() if v["mean_baseline_over_source"] >= 2.0]
    print(f"families with mean baseline >= 2x source: {inflated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
