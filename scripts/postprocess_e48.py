"""Post-process E48 outputs: merge the corrected pyzx channel and re-derive the
comparison against the project's frozen ``baseline_cost``.

Two corrections are applied here rather than by re-running the optimizers:

1. **pyzx phase convention.** ``pyzx`` stores phases in units of pi; the first
   pass emitted ``rz(phase)`` instead of ``rz(pi * phase)``, which produced
   non-equivalent outputs on 13 sources.  ``panel_rows_subset.csv`` is the
   corrected pyzx channel (0 equivalence failures).
2. **Comparison target.** The first pass compared each optimizer's cost with the
   *input* circuit, not with the project's frozen ``baseline_cost`` (the greedy
   fixed point).  The scientific question is whether an external optimizer beats
   the certified baseline, so ``delta_vs_baseline`` and ``beats_baseline`` are
   re-derived against ``baseline_cost``.

Reads and rewrites only files under
``docs/review/science_boost/2026-10-20_external_falsifier/``.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "review" / "science_boost" / "2026-10-20_external_falsifier"
PANEL = OUT / "panel_rows.csv"
SUBSETS = sorted(OUT.glob("panel_rows_subset*.csv"))
SUMMARY = OUT / "summary.json"


def main() -> int:
    panel = list(csv.DictReader(PANEL.open(encoding="utf-8", newline="")))
    subset: dict[tuple[str, str], dict[str, str]] = {}
    for path in SUBSETS:
        for row in csv.DictReader(path.open(encoding="utf-8", newline="")):
            subset[(row["source_id"], row["optimizer"])] = row
    print(f"merged {len(SUBSETS)} subset files: {[p.name for p in SUBSETS]}")
    fields = list(panel[0].keys())

    merged: list[dict[str, str]] = []
    for row in panel:
        key = (row["source_id"], row["optimizer"])
        if key in subset:
            row = {k: subset[key].get(k, "") for k in fields}
        baseline = int(row["baseline_cost"])
        if row["status"] == "OK" and row["cost_fair"]:
            cost = int(row["cost_fair"])
            row["delta_vs_baseline"] = str(baseline - cost)
            row["beats_baseline"] = str(cost < baseline)
        else:
            row["delta_vs_baseline"] = ""
            row["beats_baseline"] = ""
        merged.append(row)

    with PANEL.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in merged:
            writer.writerow(row)

    per_family: dict[str, dict[str, object]] = defaultdict(
        lambda: {"sources": set(), "beaten_rows": 0, "beaten_sources": set(), "max_gain": 0,
                 "errors": 0, "skipped": 0, "rows": 0}
    )
    for row in merged:
        fam = row["circuit_family"]
        slot = per_family[fam]
        slot["sources"].add(row["source_id"])  # type: ignore[union-attr]
        slot["rows"] += 1  # type: ignore[operator]
        if row["status"] == "SKIPPED_NON_CLIFFORD" or row["status"] == "SKIPPED_OVERSIZE":
            slot["skipped"] += 1  # type: ignore[operator]
            continue
        if row["status"] != "OK":
            slot["errors"] += 1  # type: ignore[operator]
            continue
        if row["beats_baseline"] == "True":
            slot["beaten_rows"] += 1  # type: ignore[operator]
            slot["beaten_sources"].add(row["source_id"])  # type: ignore[union-attr]
        slot["max_gain"] = max(slot["max_gain"], int(row["delta_vs_baseline"]))  # type: ignore[type-var,arg-type]

    by_family = {
        fam: {
            "sources": len(slot["sources"]),  # type: ignore[arg-type]
            "rows_beating_baseline": slot["beaten_rows"],
            "sources_beaten": len(slot["beaten_sources"]),  # type: ignore[arg-type]
            "largest_gain_over_baseline": slot["max_gain"],
            "errors": slot["errors"],
            "skipped": slot["skipped"],
        }
        for fam, slot in sorted(per_family.items())
    }

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    summary["part_b"]["by_family"] = by_family
    summary["part_b"]["ceiling_families"] = {
        k: v for k, v in by_family.items() if k in {"GHZ", "SurfaceCode", "QFT"}
    }
    summary["part_b"]["sources_beaten_by_any_tool"] = len(
        {row["source_id"] for row in merged if row["beats_baseline"] == "True"}
    )
    summary["part_b"]["equivalence_failures"] = sum(
        1 for row in merged if row["equivalent"] == "False"
    )
    summary["part_b"]["rows_beating_baseline"] = sum(
        1 for row in merged if row["beats_baseline"] == "True"
    )
    summary["corrections_applied"] = {
        "pyzx_phase_units": "phases multiplied by pi; pyzx channel re-run",
        "pytket_implicit_swaps": "tk_to_qiskit(..., replace_implicit_swaps=True)",
        "comparison_target": "delta and beats_baseline re-derived against frozen baseline_cost",
    }
    SUMMARY.write_text(json.dumps(summary, indent=1), encoding="utf-8")

    print(json.dumps(by_family, indent=1))
    print("sources beaten:", summary["part_b"]["sources_beaten_by_any_tool"],
          "/", summary["part_b"]["real_sources"])
    print("equivalence failures:", summary["part_b"]["equivalence_failures"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
