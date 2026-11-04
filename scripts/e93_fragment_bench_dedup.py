"""E93: the fragment bench's 240 instances are 170 circuits (defect D11).

Motivation
----------
Round 16 (E70) built a "fragment-native benchmark" of 240 instances -- 6 families
x 5 sizes x 8 instances -- and reported an aggregate reorder share of
``g_reorder / g_total = 0.710``.  The generator draws a distinct seed per
instance, but two of the six generators never consume the RNG:

* ``gen_trotter_zz``      builds a fixed ladder, ``rng`` is created and unused;
* ``gen_arithmetic_phase`` is a deterministic carry-chain oracle, no RNG at all.

So 80 of the 240 rows are 10 distinct circuits replicated 8 times.  This matters
because one of the two affected families (``trotter_zz``) carries a reorder share
of exactly 0 and 952 of the 4,313 total gap units -- 22% of the pooled weight
with 8x the influence it should have.

What this script does
---------------------
1. Hashes every instance file and counts distinct circuits per (family, n).
2. Recomputes the pooled and per-family reorder share with and without the
   duplicate rows, from E70's own ``fragment_gap_rows.csv`` (no re-run).
3. Records the corrected number and the families it applies to.

It does **not** regenerate the bench: the E70 package's MANIFEST pins the file
hashes, and rewriting the inputs would invalidate a frozen evidence package.
The repair (seed-dependent structure for the two families) is specified in the
summary as a follow-up, to be run into a new dated directory.

Outputs (``docs/review/science_boost/2026-11-04_fragment_bench_dedup/``)
    family_weights.csv   per family: rows, distinct circuits, pooled share, gap weight
    summary.json         contract, corrected aggregate, self-checks
    MANIFEST.json        sha256 of every artifact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "docs" / "review" / "science_boost" / "2026-10-25_fragment_bench"
E70_ROWS = ROOT / "docs" / "review" / "science_boost" / "2026-10-26_fragment_rotation_gap" / "fragment_gap_rows.csv"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-11-04_fragment_bench_dedup"
EXPERIMENT_ID = "E93_FRAGMENT_BENCH_DEDUP_2026_11_04"
SEED_INDEPENDENT = ("trotter_zz", "arithmetic_phase")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _num(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)

    distinct: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    files_by_family: dict[str, int] = defaultdict(int)
    for path in sorted((BENCH / "instances").glob("*/*.qasm")):
        family = path.parent.name
        size = int(path.name.split("_n")[1].split("_")[0])
        distinct[family][size].add(sha256_file(path))
        files_by_family[family] += 1

    rows = list(csv.DictReader(E70_ROWS.open(encoding="utf-8", newline="")))
    by_family: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_family[row["family"]].append(row)

    def pooled(selection: list[dict[str, str]]) -> float | None:
        total = sum(_num(row["gap_total_root"]) for row in selection)
        reorder = sum(_num(row["gap_reorder"]) for row in selection)
        return (reorder / total) if total else None

    dedup_rows = [
        row
        for row in rows
        if row["family"] not in SEED_INDEPENDENT or row["instance"] == "0"
    ]

    table: list[dict[str, Any]] = []
    for family in sorted(by_family):
        subset = by_family[family]
        keep = [row for row in subset if row["family"] not in SEED_INDEPENDENT or row["instance"] == "0"]
        table.append(
            {
                "family": family,
                "rows": len(subset),
                "distinct_circuits": sum(len(v) for v in distinct[family].values()),
                "seed_independent": family in SEED_INDEPENDENT,
                "gap_total_all_rows": sum(_num(row["gap_total_root"]) for row in subset),
                "gap_total_dedup": sum(_num(row["gap_total_root"]) for row in keep),
                "share_all_rows": pooled(subset),
                "share_dedup": pooled(keep),
            }
        )

    total_all = sum(row["gap_total_all_rows"] for row in table)
    total_dedup = sum(row["gap_total_dedup"] for row in table)
    for row in table:
        row["weight_all_rows"] = row["gap_total_all_rows"] / total_all if total_all else None
        row["weight_dedup"] = row["gap_total_dedup"] / total_dedup if total_dedup else None

    checks = {
        "e70_row_count_240": len(rows) == 240,
        "bench_file_count_240": sum(files_by_family.values()) == 240,
        "dedup_row_count_170": len(dedup_rows) == 170,
        "seed_independent_families_have_5_distinct": all(
            sum(len(v) for v in distinct[family].values()) == 5 for family in SEED_INDEPENDENT
        ),
        "other_families_have_40_distinct": all(
            sum(len(v) for v in distinct[family].values()) == 40
            for family in distinct
            if family not in SEED_INDEPENDENT
        ),
        "pooled_share_rises_after_dedup": (pooled(dedup_rows) or 0) > (pooled(rows) or 1),
    }

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "defect": "D11",
        "contract": {
            "inputs": [
                str(E70_ROWS.relative_to(ROOT)),
                str((BENCH / "instances").relative_to(ROOT)) + "/*/*.qasm",
            ],
            "rerun": "none (arithmetic on the frozen E70 rows and file hashes)",
            "writes": ["docs/review/science_boost/2026-11-04_fragment_bench_dedup/"],
        },
        "result": {
            "rows": len(rows),
            "distinct_circuits": sum(len(v) for family in distinct.values() for v in family.values()),
            "pooled_share_all_rows": pooled(rows),
            "pooled_share_dedup": pooled(dedup_rows),
            "gap_total_all_rows": total_all,
            "gap_total_dedup": total_dedup,
        },
        "repair": (
            "gen_trotter_zz and gen_arithmetic_phase must consume the seed (random edge order / "
            "random carry length). Regenerate into a new dated bench directory and re-run E70 there; "
            "do not overwrite the pinned 2026-10-25 package."
        ),
        "self_checks": checks,
    }

    with (out / "family_weights.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    with (out / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "artifacts": {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in sorted(out.glob("*"))
            if path.is_file() and path.name != "MANIFEST.json"
        },
    }
    with (out / "MANIFEST.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)

    print(json.dumps(summary["result"], indent=1))
    for row in table:
        print(
            f"  {row['family']:24s} rows={row['rows']:3d} distinct={row['distinct_circuits']:3d} "
            f"share_all={row['share_all_rows']} share_dedup={row['share_dedup']} "
            f"weight_all={row['weight_all_rows']:.3f} weight_dedup={row['weight_dedup']:.3f}"
        )
    failed = [key for key, value in checks.items() if value is False]
    print(f"[E93] self-checks: {len(checks) - len(failed)}/{len(checks)} true")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
