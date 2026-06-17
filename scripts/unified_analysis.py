"""Unified cross-experiment analysis script.

Reads canonical datasets from E1-E5, E10, E11-E13 and produces:
1. unified_summary.csv — one row per experiment
2. optimizer_vs_compiler.csv — side-by-side comparison for shared circuit families
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def find_canonical_csv(data_dir: Path) -> Optional[Path]:
    """Locate canonical CSV via metadata.json or latest file."""
    meta = data_dir / "metadata.json"
    if meta.exists():
        try:
            metadata = json.loads(meta.read_text(encoding="utf-8"))
            canonical = metadata.get("canonical_data_file")
            if canonical:
                candidate = data_dir / canonical
                if candidate.exists():
                    return candidate
        except Exception:
            pass
    csvs = sorted(data_dir.glob("*.csv"))
    return csvs[-1] if csvs else None


def load_experiment(experiment_dir: Path) -> Optional[pd.DataFrame]:
    csv = find_canonical_csv(experiment_dir)
    if csv is None:
        return None
    return pd.read_csv(csv)


def summarize_experiment(exp_id: str, df: pd.DataFrame) -> Dict[str, object]:
    """Produce a single summary row for an experiment."""
    rows = len(df)
    n_qubits = df["n_qubits"].dropna()
    depth = df.get("depth", pd.Series(dtype=float)).dropna()
    reduction = df.get("reduction", pd.Series(dtype=float)).dropna()
    fidelity = df.get("fidelity", pd.Series(dtype=float)).dropna()
    runtime = df.get("runtime_seconds", pd.Series(dtype=float)).dropna()

    best_opt = "N/A"
    if "optimizer" in df.columns and not reduction.empty:
        grouped = df.groupby("optimizer")["reduction"].mean()
        if not grouped.empty:
            best_opt = grouped.idxmax()

    return {
        "experiment": exp_id,
        "n_records": rows,
        "n_qubits_range": f"{int(n_qubits.min())}-{int(n_qubits.max())}" if not n_qubits.empty else "N/A",
        "depth_range": f"{int(depth.min())}-{int(depth.max())}" if not depth.empty else "N/A",
        "mean_reduction_pct": f"{reduction.mean() * 100:.4f}" if not reduction.empty else "N/A",
        "std_reduction_pct": f"{reduction.std() * 100:.4f}" if not reduction.empty else "N/A",
        "mean_fidelity": f"{fidelity.mean():.6f}" if not fidelity.empty else "N/A",
        "mean_runtime_ms": f"{runtime.mean() * 1000:.2f}" if not runtime.empty else "N/A",
        "best_optimizer": best_opt,
    }


def build_unified_summary() -> pd.DataFrame:
    summaries: List[Dict[str, object]] = []
    experiments = {
        "E1": PROJECT_ROOT / "data/v2_fixed/e01",
        "E2": PROJECT_ROOT / "data/v2_fixed/e02",
        "E3": PROJECT_ROOT / "data/v2_fixed/e03",
        "E4": PROJECT_ROOT / "data/v2_fixed/e04",
        "E5": PROJECT_ROOT / "data/v2_fixed/e05",
        "E10": PROJECT_ROOT / "data/v3_extended/e10",
        "E11": PROJECT_ROOT / "data/v4/e11",
        "E12": PROJECT_ROOT / "data/v4/e12",
        "E13": PROJECT_ROOT / "data/v4/e13",
    }
    for exp_id, path in experiments.items():
        df = load_experiment(path)
        if df is not None:
            summaries.append(summarize_experiment(exp_id, df))
        else:
            summaries.append({"experiment": exp_id, "n_records": 0, "notes": "no data"})
    return pd.DataFrame(summaries)


def build_optimizer_vs_compiler() -> pd.DataFrame:
    e11_path = find_canonical_csv(PROJECT_ROOT / "data/v4/e11")
    e12_path = find_canonical_csv(PROJECT_ROOT / "data/v4/e12")
    e13_path = find_canonical_csv(PROJECT_ROOT / "data/v4/e13")

    if e11_path is None or e12_path is None:
        return pd.DataFrame()

    e11 = pd.read_csv(e11_path)
    e12 = pd.read_csv(e12_path)
    e13 = pd.read_csv(e13_path) if e13_path else pd.DataFrame()

    rows: List[Dict[str, object]] = []
    families = sorted(set(e11["circuit_family"].unique()) & set(e12["circuit_family"].unique()))

    for family in families:
        e11_sub = e11[e11["circuit_family"] == family]
        e12_sub = e12[e12["circuit_family"] == family]

        our_best = e11_sub.groupby("circuit_id")["reduction"].max().mean() * 100
        qiskit_best = e12_sub[e12_sub["compiler_optimization_level"] == 3].groupby("circuit_id")["reduction"].max().mean() * 100

        ceiling = None
        if not e13.empty and "circuit_family" in e13.columns:
            e13_sub = e13[e13["circuit_family"] == family]
            if not e13_sub.empty:
                ceiling = e13_sub["structural_upper_bound_reduction"].mean() * 100

        n_qubits = e11_sub["n_qubits"].iloc[0] if not e11_sub.empty else "N/A"

        rows.append(
            {
                "circuit_family": family,
                "n_qubits": n_qubits,
                "our_best_reduction_pct": f"{our_best:.2f}",
                "qiskit_o3_reduction_pct": f"{qiskit_best:.2f}",
                "structural_ceiling_pct": f"{ceiling:.2f}" if ceiling is not None else "N/A",
                "ceiling_gap_pct": f"{ceiling - max(our_best, qiskit_best):.2f}" if ceiling is not None else "N/A",
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    output_dir = PROJECT_ROOT / "analysis" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = build_unified_summary()
    summary_path = output_dir / "unified_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"Unified summary: {summary_path} ({len(summary)} experiments)")
    print(summary.to_string(index=False))

    comparison = build_optimizer_vs_compiler()
    if not comparison.empty:
        comp_path = output_dir / "optimizer_vs_compiler.csv"
        comparison.to_csv(comp_path, index=False)
        print(f"\nOptimizer vs Compiler: {comp_path}")
        print(comparison.to_string(index=False))
    else:
        print("\nNo shared circuit families between E11 and E12 for comparison.")


if __name__ == "__main__":
    main()
