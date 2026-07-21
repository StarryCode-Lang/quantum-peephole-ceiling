"""
E23: Empirical Validation of Theorem 6
======================================
Aaronson-Gottesman canonical form Clifford circuits have empty Phase-1
action space, so Greedy Phase-1 reduction should be exactly 0.

Outputs:
    data/v7/e23/e23_ag_canonical_results.csv
    data/v7/e23/metadata.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.ag_canonical import generate_ag_canonical_circuit
from src.optimisation.phase1.greedy import GreedyGateCancellation


# ---------------------------------------------------------------------------
# Canonical-output overwrite guard (wave-4)
# ---------------------------------------------------------------------------
# E23 writes its canonical CSV to a fixed path. To avoid silently clobbering
# a published dataset with different content, the freshly computed results
# are checked against the existing file BEFORE any write:
#   - file absent                     -> write normally;
#   - deterministic content identical -> silent pass (file left untouched);
#   - deterministic content differs   -> warn loudly and exit(1) without
#                                        writing anything.
# "Deterministic content" excludes runtime_seconds (wall-clock timing,
# legitimately different between identical reruns) and rounds float columns
# to 12 decimals (a CSV float round-trip drifts the last bit). The SHA-256
# digests below are computed over this canonical serialization, so a mismatch
# means the scientific results themselves changed.

_NON_DETERMINISTIC_COLS = ("runtime_seconds",)
_FLOAT_ROUND_DECIMALS = 12


def _canonical_result_sha(df: pd.DataFrame) -> str:
    """SHA-256 over the deterministic part of an E23 results frame."""
    det = df.drop(columns=[c for c in _NON_DETERMINISTIC_COLS if c in df.columns]).copy()
    for col in det.select_dtypes(include="floating").columns:
        det[col] = det[col].round(_FLOAT_ROUND_DECIMALS)
    return hashlib.sha256(det.to_csv(index=False).encode("utf-8")).hexdigest()


def _guard_canonical_csv(df: pd.DataFrame, csv_path: Path) -> bool:
    """Check freshly computed results against the existing canonical CSV.

    Returns True when the file exists and its deterministic content matches
    (caller must skip the write); False when the file does not exist yet
    (caller must write). Exits with an error, writing nothing, when the file
    exists but the deterministic content differs.
    """
    if not csv_path.exists():
        return False

    existing = pd.read_csv(csv_path)
    new_sha = _canonical_result_sha(df)
    old_sha = _canonical_result_sha(existing)
    if old_sha == new_sha:
        return True  # identical deterministic content -> silent pass

    print("=" * 64, file=sys.stderr)
    print("ERROR: E23 canonical CSV overwrite guard triggered.", file=sys.stderr)
    print(f"  File:     {csv_path}", file=sys.stderr)
    print(f"  Existing  deterministic SHA-256: {old_sha}", file=sys.stderr)
    print(f"  Recomputed deterministic SHA-256: {new_sha}", file=sys.stderr)
    # Best-effort diagnostics: first differing deterministic column.
    det_new = df.drop(columns=[c for c in _NON_DETERMINISTIC_COLS if c in df.columns])
    det_old = existing.drop(columns=[c for c in _NON_DETERMINISTIC_COLS if c in existing.columns])
    if det_old.shape == det_new.shape and list(det_old.columns) == list(det_new.columns):
        for col in det_new.columns:
            if not det_old[col].equals(det_new[col]):
                n_diff = int((det_old[col] != det_new[col]).sum())
                print(f"  First differing column: {col!r} ({n_diff} rows differ)", file=sys.stderr)
                break
    else:
        print(f"  Shape/columns differ: existing {det_old.shape} vs new {det_new.shape}",
              file=sys.stderr)
    print("  The existing canonical CSV was NOT modified. Investigate the", file=sys.stderr)
    print("  discrepancy (code/data change?) and, if the new results are", file=sys.stderr)
    print("  intended, back up and remove the old file before rerunning.", file=sys.stderr)
    print("=" * 64, file=sys.stderr)
    sys.exit(1)


def run_e23(n_min: int = 3, n_max: int = 10, n_circuits_per_n: int = 20, seed_base: int = 2026):
    output_dir = PROJECT_ROOT / "data/v7/e23"
    output_dir.mkdir(parents=True, exist_ok=True)

    optimizer = GreedyGateCancellation()
    results = []

    total = (n_max - n_min + 1) * n_circuits_per_n
    with tqdm(total=total, desc="E23 AG canonical") as pbar:
        for n_qubits in range(n_min, n_max + 1):
            for trial in range(n_circuits_per_n):
                seed = seed_base + n_qubits * 1000 + trial
                qc = generate_ag_canonical_circuit(n_qubits, seed=seed)
                result = optimizer.optimize(qc, target=qc)

                results.append({
                    "experiment": 23,
                    "n_qubits": n_qubits,
                    "trial": trial,
                    "seed": seed,
                    "original_size": result.original_size,
                    "optimized_size": result.optimized_size,
                    "reduction": result.reduction,
                    "fidelity": result.fidelity,
                    "iterations": result.iterations,
                    "runtime_seconds": result.runtime_seconds,
                })
                pbar.update(1)

    df = pd.DataFrame(results)
    csv_path = output_dir / "e23_ag_canonical_results.csv"
    # Overwrite guard (wave-4): write only when the file is absent; silently
    # pass when the deterministic content is identical; exit(1) on mismatch.
    if not _guard_canonical_csv(df, csv_path):
        df.to_csv(csv_path, index=False)

    # Matching rate: reduction should be 0 up to numerical precision.
    matches = np.isclose(df["reduction"], 0.0, atol=1e-12)
    matching_rate = matches.mean()

    metadata = {
        "experiment": "E23",
        "description": "Empirical validation of Theorem 6: AG canonical form Clifford circuits have R1=0.",
        "timestamp": datetime.now().isoformat(),
        "n_min": n_min,
        "n_max": n_max,
        "n_circuits_per_n": n_circuits_per_n,
        "total_circuits": len(df),
        "matching_rate": float(matching_rate),
        "mean_reduction": float(df["reduction"].mean()),
        "max_reduction": float(df["reduction"].max()),
        "csv_path": str(csv_path.relative_to(PROJECT_ROOT)),
    }

    meta_path = output_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"E23 complete: {len(df)} circuits, matching rate = {matching_rate:.4f}")
    print(f"CSV: {csv_path}")
    print(f"Metadata: {meta_path}")
    return df, metadata


if __name__ == "__main__":
    run_e23()
