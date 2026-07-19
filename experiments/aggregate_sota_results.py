"""Aggregate SOTA benchmark results and update comparison tables.

Reads raw CSVs from data/v6/sota_benchmark/raw/, computes per-family
mean reduction, and writes:
  1. aggregated/sota_comparison_aggregated.csv (updated)
  2. A markdown summary of key findings.
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "v6" / "sota_benchmark" / "raw"
AGG_DIR = PROJECT_ROOT / "data" / "v6" / "sota_benchmark" / "aggregated"
AGG_DIR.mkdir(parents=True, exist_ok=True)

# Latest raw files per tool (pick the largest = most complete)
TOOL_FILES = {
    "tket": "tket_default_20260718_173443.csv",
    "qiskit": "qiskit_default_20260718_181056.csv",
    "cirq": "cirq_default_20260718_181336.csv",
    "custom": "custom_default_20260717_052910.csv",
}


def load_tool(tool: str, fname: str) -> pd.DataFrame:
    path = RAW_DIR / fname
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["tool"] = tool
    # Normalize: gate_reduction_pct is the main metric; treat errors as NaN
    if "gate_reduction_pct" in df.columns:
        df["reduction"] = df["gate_reduction_pct"] / 100.0
    if "compiler_status" in df.columns:
        df.loc[df["compiler_status"] != "ok", "reduction"] = np.nan
    return df


def main() -> int:
    frames = []
    for tool, fname in TOOL_FILES.items():
        df = load_tool(tool, fname)
        if not df.empty:
            frames.append(df)
            print(f"  {tool}: {len(df)} rows")
    if not frames:
        print("ERROR: no data", file=sys.stderr)
        return 1
    all_df = pd.concat(frames, ignore_index=True)
    print(f"\nTotal: {len(all_df)} rows across {all_df['tool'].nunique()} tools")

    # Per (tool, family) mean reduction
    pivot = all_df.groupby(["tool", "circuit_family"])["reduction"].agg(
        ["mean", "median", "std", "count"]
    ).reset_index()
    pivot.columns = ["tool", "family", "mean_reduction", "median_reduction",
                     "std_reduction", "n_trials"]
    pivot["mean_pct"] = (pivot["mean_reduction"] * 100).round(2)
    pivot["median_pct"] = (pivot["median_reduction"] * 100).round(2)
    pivot = pivot.sort_values(["family", "tool"])
    out_csv = AGG_DIR / "sota_comparison_aggregated.csv"
    pivot.to_csv(out_csv, index=False)
    print(f"\nWrote: {out_csv}")

    # Pretty wide table: rows=family, cols=tool
    wide = pivot.pivot(index="family", columns="tool", values="mean_pct")
    wide = wide.reindex(columns=["custom", "qiskit", "cirq", "tket"])
    # Sort families by tket performance (best first)
    if "tket" in wide.columns:
        wide = wide.sort_values("tket", ascending=False)
    print("\n=== Mean reduction (%) by family x tool ===")
    print(wide.to_string())

    # Key findings
    print("\n=== Key findings ===")
    for tool in wide.columns:
        col = wide[tool].dropna()
        pos = (col > 0).sum()
        neg = (col < 0).sum()
        print(f"  {tool}: {pos} positive, {neg} negative (gate blowup), "
              f"range [{col.min():.1f}, {col.max():.1f}]")

    # Best tool per family
    print("\n=== Best tool per family ===")
    for fam in wide.index:
        row = wide.loc[fam].dropna()
        if len(row) == 0:
            continue
        best = row.idxmax()
        best_val = row.max()
        print(f"  {fam:20s}: {best} = {best_val:+.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
