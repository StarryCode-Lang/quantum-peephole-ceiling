#!/usr/bin/env python3
"""
Regenerate ``analysis/figures/unified_summary.csv`` from on-disk data.

The previous unified_summary.csv was stale (review F4): it reported
E10=627 rows (actual 1905), E11=168 (actual 426), E12=224 (actual 568),
and was missing E14-E19 entirely.  This script scans the canonical data
directories, reads each experiment's declared canonical CSV, and emits
an accurate per-experiment summary keyed on real row counts.

Usage:
    python scripts/regenerate_unified_summary.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "data"
OUTPUT_PATH = PROJECT_ROOT / "analysis" / "figures" / "unified_summary.csv"

# Canonical mapping: experiment id -> directory containing its data.
# Each directory must have a metadata.json declaring canonical_data_file.
EXPERIMENT_DIRS = {
    "E1":  "v2_fixed/e01",
    "E2":  "v2_fixed/e02",
    "E3":  "v2_fixed/e03",
    "E4":  "v2_fixed/e04",
    "E5":  "v2_fixed/e05",
    "E10": "v5/e10",
    "E11": "v4/e11",
    "E12": "v4/e12",
    "E13": "v4/e13",
    "E14": "v5/e14",
    "E15": "v5/e15",
    "E16": "v5/e16",
    "E17": "v5/e17",
    "E18": "v5/e18",
    "E19": "v6/e19",
    "E21": "v6/e21",
}


def _resolve_canonical_csv(exp_dir: Path) -> Path | None:
    """Return the canonical CSV for an experiment directory."""
    meta_path = exp_dir / "metadata.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            canonical = meta.get("canonical_data_file")
            if canonical:
                candidate = exp_dir / canonical
                if candidate.exists():
                    return candidate
        except Exception:
            pass
    # Fall back to the most recently modified CSV.
    csvs = sorted(exp_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return csvs[0] if csvs else None


def _column_reduction(df: pd.DataFrame) -> pd.Series | None:
    """Locate the reduction column under any of its common aliases."""
    for name in ("reduction", "reduction_pct", "gate_reduction"):
        if name in df.columns:
            return df[name]
    return None


def _column_fidelity(df: pd.DataFrame) -> pd.Series | None:
    for name in ("fidelity",):
        if name in df.columns:
            return df[name]
    return None


def _column_runtime(df: pd.DataFrame) -> pd.Series | None:
    for name in ("runtime_seconds", "runtime_ms", "runtime"):
        if name in df.columns:
            return df[name]
    return None


def _column_optimizer(df: pd.DataFrame) -> pd.Series | None:
    for name in ("optimizer", "compiler_backend", "optimizer_version"):
        if name in df.columns:
            return df[name]
    return None


def _best_optimizer(df: pd.DataFrame, reduction: pd.Series) -> str:
    opt = _column_optimizer(df)
    if opt is None or reduction is None:
        return "N/A"
    try:
        means = reduction.groupby(opt).mean()
        if len(means) == 0 or means.max() == 0:
            return "N/A"
        return str(means.idxmax())
    except Exception:
        return "N/A"


def summarize_experiment(exp_id: str, csv_path: Path) -> dict | None:
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        print(f"  [WARN] {exp_id}: failed to read {csv_path.name}: {exc}", file=sys.stderr)
        return None

    reduction = _column_reduction(df)
    fidelity = _column_fidelity(df)
    runtime = _column_runtime(df)

    # Normalize runtime to milliseconds for comparability.
    runtime_ms = None
    if runtime is not None:
        runtime_ms = runtime.astype(float) * 1000.0
        if "runtime_ms" in (runtime.name or ""):
            runtime_ms = runtime.astype(float)

    n_qubits_range = "N/A"
    if "n_qubits" in df.columns:
        qs = pd.to_numeric(df["n_qubits"], errors="coerce").dropna()
        if len(qs):
            n_qubits_range = f"{int(qs.min())}-{int(qs.max())}"

    depth_range = "N/A"
    if "depth" in df.columns:
        ds = pd.to_numeric(df["depth"], errors="coerce").dropna()
        if len(ds):
            depth_range = f"{int(ds.min())}-{int(ds.max())}"

    mean_red = float(reduction.mean() * 100.0) if reduction is not None and len(reduction) else None
    std_red = float(reduction.std() * 100.0) if reduction is not None and len(reduction) > 1 else None
    mean_fid = float(fidelity.dropna().mean()) if fidelity is not None and fidelity.notna().any() else None
    mean_rt = float(runtime_ms.dropna().mean()) if runtime_ms is not None and runtime_ms.notna().any() else None
    best = _best_optimizer(df, reduction) if reduction is not None else "N/A"

    return {
        "experiment": exp_id,
        "n_records": int(len(df)),
        "n_qubits_range": n_qubits_range,
        "depth_range": depth_range,
        "mean_reduction_pct": round(mean_red, 4) if mean_red is not None else "N/A",
        "std_reduction_pct": round(std_red, 4) if std_red is not None else "N/A",
        "mean_fidelity": round(mean_fid, 6) if mean_fid is not None else "N/A",
        "mean_runtime_ms": round(mean_rt, 2) if mean_rt is not None else "N/A",
        "best_optimizer": best,
    }


def main() -> int:
    rows = []
    for exp_id, rel_dir in EXPERIMENT_DIRS.items():
        exp_dir = DATA_ROOT / rel_dir
        if not exp_dir.exists():
            print(f"  [SKIP] {exp_id}: directory {rel_dir} does not exist", file=sys.stderr)
            rows.append({"experiment": exp_id, "n_records": 0, "n_qubits_range": "N/A",
                         "depth_range": "N/A", "mean_reduction_pct": "N/A",
                         "std_reduction_pct": "N/A", "mean_fidelity": "N/A",
                         "mean_runtime_ms": "N/A", "best_optimizer": "N/A",
                         "status": "missing"})
            continue
        csv_path = _resolve_canonical_csv(exp_dir)
        if csv_path is None:
            print(f"  [SKIP] {exp_id}: no CSV data in {rel_dir}", file=sys.stderr)
            rows.append({"experiment": exp_id, "n_records": 0, "n_qubits_range": "N/A",
                         "depth_range": "N/A", "mean_reduction_pct": "N/A",
                         "std_reduction_pct": "N/A", "mean_fidelity": "N/A",
                         "mean_runtime_ms": "N/A", "best_optimizer": "N/A",
                         "status": "no_data"})
            continue
        summary = summarize_experiment(exp_id, csv_path)
        if summary is None:
            continue
        summary["status"] = "ok"
        rows.append(summary)
        print(f"  {exp_id}: {summary['n_records']} rows | {csv_path.parent.name}/{csv_path.name}")

    df = pd.DataFrame(rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    header = (
        "# n_records: per-experiment total rows, aggregated across all optimizers "
        "and parameter settings within that experiment. Not per-optimizer counts.\n"
        "# Regenerated by scripts/regenerate_unified_summary.py from on-disk canonical data.\n"
    )
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        fh.write(header)
        df.to_csv(fh, index=False)

    print(f"\nWrote {len(df)} experiment rows to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
