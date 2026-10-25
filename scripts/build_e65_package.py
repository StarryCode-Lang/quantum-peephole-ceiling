"""Build the E65 bounded-exactification package summary from cells.jsonl.

Reads the resume-safe per-cell JSONL written by
``scripts/e65_bounded_exactification.py`` and emits, into the same package
directory:

- ``exactification_summary.csv`` — one row per cell: tracker class, raised
  compact/IDA* statuses, exactness verdict;
- ``summary.json`` — the headline counts: how many of the 34 witness-bounded
  cells became exact under the raised contract (s1M/t300), how many remain
  bounded, the derived-cell rescue verdict, and the RAM-insufficient records;
- ``receipt.json`` — SHA-256 of every input/output, producing engine hashes.

Usage:
    python scripts/build_e65_package.py [--cells <cells.jsonl>]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs" / "review" / "science_boost" / "2026-10-25_bounded_exactification"
EXPERIMENT_ID = "E65_BOUNDED_EXACTIFICATION_V1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=Path, default=PACKAGE / "cells.jsonl")
    args = parser.parse_args()
    records = [json.loads(l) for l in args.cells.read_text(encoding="utf-8").splitlines() if l.strip()]

    ran = [r for r in records if "raised_compact" in r]
    skipped = [r for r in records if r.get("status") == "RAM_INSUFFICIENT_PROJECTED"]
    mem_errors = [r for r in records if r.get("status") == "MEMORY_ERROR"]

    exactified = []
    still_bounded = []
    for r in ran:
        compact = r["raised_compact"]
        idastar = r["raised_idastar"]
        compact_exact = compact["status"] in ("EXACT_H_LOCAL_OPTIMUM", "EXACT_ESCAPE")
        ida_exact = idastar["status"] in ("EXACT_H_LOCAL_OPTIMUM", "EXACT_ESCAPE")
        if compact_exact or ida_exact:
            exactified.append(r)
        else:
            still_bounded.append(r)

    derived_rescue = [r for r in ran if r["source_id"].startswith("e39:b2f83603")]
    rescue = None
    if derived_rescue:
        r = derived_rescue[0]
        rescue = {
            "source_id": r["source_id"],
            "raised_compact_status": r["raised_compact"]["status"],
            "raised_compact_states_seen": r["raised_compact"]["states_seen"],
            "raised_idastar_status": r["raised_idastar"]["status"],
            "rescued": r["raised_idastar"]["status"] == "EXACT_H_LOCAL_OPTIMUM",
        }

    replay_failures = sum(
        1 for r in ran if r.get("compact_replay") == "REPLAY_FAIL" or r.get("idastar_replay") == "REPLAY_FAIL"
    )
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "raised_contract": "horizon 3, scope e44_core_v1, state budget 1,000,000, time budget 300 s per engine per cell (fail-closed)",
        "tracker_cells": 34,
        "derived_cell": "e39:b2f83603...",
        "ran_count": len(ran),
        "exactified_count": len(exactified),
        "still_bounded_count": len(still_bounded),
        "ram_insufficient_projected_count": len(skipped),
        "memory_error_count": len(mem_errors),
        "witness_replay_failure_count": replay_failures,
        "exactified_source_ids": sorted(r["source_id"] for r in exactified),
        "still_bounded_source_ids": sorted(r["source_id"] for r in still_bounded),
        "derived_cell_rescue": rescue,
        "headline": (
            "Exact best-cost certificates under the raised contract: "
            f"{len(exactified)} of the 34 witness-bounded cells plus "
            f"{'the' if rescue and rescue['rescued'] else 'NO'} derived-cell rescue "
            "(the frozen-budget v16 headline stays 93; this package records the "
            "raised-contract upgrades separately, never over v16)."
        ),
    }

    csv_path = PACKAGE / "exactification_summary.csv"
    csv_rows = []
    for r in records:
        row = {"source_id": r["source_id"], "family": r.get("circuit_family", ""),
               "baseline_cost": r.get("baseline_cost", ""),
               "tracker_class": r.get("tracker_cost_class", "")}
        if "raised_compact" in r:
            row.update({
                "raised_compact_status": r["raised_compact"]["status"],
                "raised_compact_states_seen": r["raised_compact"]["states_seen"],
                "raised_idastar_status": r["raised_idastar"]["status"],
                "raised_idastar_states_seen": r["raised_idastar"]["states_seen"],
                "compact_replay": r.get("compact_replay", ""),
                "idastar_replay": r.get("idastar_replay", ""),
                "exactified": (r["raised_compact"]["status"] in ("EXACT_H_LOCAL_OPTIMUM", "EXACT_ESCAPE")
                               or r["raised_idastar"]["status"] in ("EXACT_H_LOCAL_OPTIMUM", "EXACT_ESCAPE")),
            })
        else:
            row["status"] = r.get("status", "")
            row["note"] = r.get("note", "")
        csv_rows.append(row)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(csv_rows)

    receipt = {
        "experiment_id": EXPERIMENT_ID,
        "built_utc": summary["built_utc"],
        "cells_jsonl_sha256": sha256(args.cells),
        "exactification_summary_sha256": sha256(csv_path),
        "producing_engine_source_sha256": (
            ran[0]["engine_source_sha256"] if ran else {}
        ),
    }
    (PACKAGE / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    (PACKAGE / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({k: summary[k] for k in (
        "ran_count", "exactified_count", "still_bounded_count",
        "ram_insufficient_projected_count", "derived_cell_rescue",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
