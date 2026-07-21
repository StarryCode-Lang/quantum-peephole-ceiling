"""Aggregate SOTA benchmark results (compatibility wrapper).

Historically this script wrote its own 8-column summary schema to
``data/v6/sota_benchmark/aggregated/sota_comparison_aggregated.csv`` while
``experiments/sota_benchmark.py --aggregate`` wrote the protocol schema
(SOTA_BENCHMARK_PROTOCOL.md Sec. 6.2) to the same path.  To eliminate the
schema conflict, this script now delegates to
``experiments.sota_benchmark.aggregate_results()``, which:

  * selects the NEWEST raw CSV per (tool, config) — superseded smoke or
    partial runs never double-count trials;
  * aggregates per (tool, tool_config, circuit_family) with the full
    protocol schema including success/fidelity/runtime statistics;
  * writes atomically and keeps a timestamped backup of any previous file.

Usage:
    python experiments/aggregate_sota_results.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

from sota_benchmark import aggregate_results  # noqa: E402


def main() -> int:
    agg = aggregate_results()
    if agg.empty:
        print("ERROR: no data aggregated", file=sys.stderr)
        return 1

    # Console summary: mean reduction (%) by family x tool/config
    agg["tool_key"] = agg["tool"] + "/" + agg["tool_config"]
    wide = agg.pivot_table(index="circuit_family", columns="tool_key",
                           values="mean_gate_reduction")
    print("\n=== Mean gate reduction (%) by family x tool/config ===")
    print(wide.round(1).to_string())

    print("\n=== Per-tool/config summary ===")
    for key in wide.columns:
        col = wide[key].dropna()
        pos = int((col > 0).sum())
        neg = int((col < 0).sum())
        print(f"  {key:16s}: {pos} positive, {neg} negative (blowup), "
              f"range [{col.min():.1f}, {col.max():.1f}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
