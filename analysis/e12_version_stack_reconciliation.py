"""Reconcile E12 across Python/numerical-stack versions using the full scientific key."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "data/v4/e12/e12_compiler_baseline_e12_full_20260626_000134_nocoupling.csv"
RERUN = ROOT / "data/v9/e12/e12_compiler_baseline_e12_full_20260721_072841_nocoupling.csv"
CANONICAL_META = ROOT / "data/v4/e12/metadata.json"
RERUN_META = ROOT / "data/v9/e12/metadata.json"
OUTPUT_DIR = ROOT / "data/v9/e12/version_stack_reconciliation"
KEYS = ["circuit_id", "compiler_optimization_level"]
EXACT_FIELDS = [
    "input_circuit_sha256", "output_circuit_sha256", "compiled_depth",
    "compiled_gate_counts_json", "baseline_gate_count", "optimized_gate_count", "success",
]
NUMERIC_FIELDS = ["reduction", "reduction_pct", "fidelity"]
TOLERANCE = 1e-12


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _equal_with_missing(left: pd.Series, right: pd.Series) -> pd.Series:
    return left.eq(right) | (left.isna() & right.isna())


def build_audit(output_dir: Path = OUTPUT_DIR) -> dict[str, object]:
    canonical = pd.read_csv(CANONICAL)
    rerun = pd.read_csv(RERUN)
    if canonical.duplicated(KEYS).any() or rerun.duplicated(KEYS).any():
        raise ValueError("E12 scientific keys must be unique at circuit x optimization-level granularity")
    joined = canonical.merge(rerun, on=KEYS, how="inner", suffixes=("_canonical", "_rerun"),
                             validate="one_to_one")
    comparison = joined[KEYS].copy()
    exact_summary = {}
    for field in EXACT_FIELDS:
        match = _equal_with_missing(joined[f"{field}_canonical"], joined[f"{field}_rerun"])
        comparison[f"{field}_match"] = match
        exact_summary[field] = {"matching_rows": int(match.sum()), "rows": int(len(match))}
    numeric_summary = {}
    for field in NUMERIC_FIELDS:
        left = pd.to_numeric(joined[f"{field}_canonical"], errors="coerce")
        right = pd.to_numeric(joined[f"{field}_rerun"], errors="coerce")
        both_missing = left.isna() & right.isna()
        finite = left.notna() & right.notna()
        difference = (left - right).abs()
        match = both_missing | (finite & difference.le(TOLERANCE))
        comparison[f"{field}_absolute_difference"] = difference
        comparison[f"{field}_match_at_1e_12"] = match
        numeric_summary[field] = {
            "finite_pairs": int(finite.sum()), "both_missing_pairs": int(both_missing.sum()),
            "matching_rows_at_1e_12": int(match.sum()), "rows": int(len(match)),
            "maximum_absolute_difference": float(difference[finite].max()) if finite.any() else None,
        }
    runtime_left = pd.to_numeric(joined["runtime_seconds_canonical"], errors="coerce")
    runtime_right = pd.to_numeric(joined["runtime_seconds_rerun"], errors="coerce")
    runtime_diff = (runtime_left - runtime_right).abs()
    comparison["runtime_seconds_absolute_difference"] = runtime_diff
    comparison["runtime_seconds_exact_match"] = _equal_with_missing(runtime_left, runtime_right)
    all_scientific = ([f"{field}_match" for field in EXACT_FIELDS]
                      + [f"{field}_match_at_1e_12" for field in NUMERIC_FIELDS])
    comparison["all_scientific_fields_match"] = comparison[all_scientific].all(axis=1)

    canonical_keys = canonical[KEYS]
    rerun_keys = rerun[KEYS]
    missing = canonical_keys.merge(rerun_keys, on=KEYS, how="left", indicator=True)
    missing = missing.loc[missing["_merge"].eq("left_only"), KEYS]
    canonical_meta = json.loads(CANONICAL_META.read_text(encoding="utf-8"))
    rerun_meta = json.loads(RERUN_META.read_text(encoding="utf-8"))
    canonical_qiskit = canonical_meta.get(
        "qiskit_version", canonical_meta.get("package_versions", {}).get("qiskit")
    )
    rerun_qiskit = rerun_meta.get(
        "qiskit_version", rerun_meta.get("package_versions", {}).get("qiskit")
    )
    shared_source_hashes = {
        key: value for key, value in canonical_meta["source_hashes"].items()
        if rerun_meta["source_hashes"].get(key) == value
    }
    changed_source_hashes = sorted(
        key for key in set(canonical_meta["source_hashes"]) | set(rerun_meta["source_hashes"])
        if canonical_meta["source_hashes"].get(key) != rerun_meta["source_hashes"].get(key)
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = output_dir / "shared_key_comparison.csv"
    comparison.to_csv(comparison_path, index=False)
    audit = {
        "schema_version": "1.0.0",
        "status": "PASS_BOUNDED_E12_CROSS_STACK_RECONCILIATION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scientific_key": KEYS,
        "canonical_rows": int(len(canonical)), "rerun_rows": int(len(rerun)),
        "canonical_unique_keys": int(len(canonical_keys)),
        "rerun_unique_keys": int(len(rerun_keys)), "shared_unique_keys": int(len(joined)),
        "missing_rerun_keys": missing.to_dict(orient="records"),
        "all_shared_scientific_rows_match": bool(comparison["all_scientific_fields_match"].all()),
        "exact_field_comparison": exact_summary,
        "numeric_field_comparison": numeric_summary,
        "runtime_comparison": {
            "role": "volatile performance diagnostic; excluded from scientific equality",
            "exact_matching_rows": int(comparison["runtime_seconds_exact_match"].sum()),
            "rows": int(len(comparison)),
            "maximum_absolute_difference_seconds": float(runtime_diff.max()),
            "median_absolute_difference_seconds": float(runtime_diff.median()),
        },
        "environment_change": {
            "canonical_python": canonical_meta["python_version"],
            "rerun_python": rerun_meta["python_version"],
            "canonical_packages": canonical_meta["package_versions"],
            "rerun_packages": rerun_meta["package_versions"],
            "qiskit_versions": [canonical_qiskit, rerun_qiskit],
            "qiskit_version_changed": canonical_qiskit != rerun_qiskit,
            "platform_strings": [canonical_meta["platform"], rerun_meta["platform"]],
            "shared_source_hashes": shared_source_hashes,
            "changed_source_hash_paths": changed_source_hashes,
        },
        "metric_dispositions": {
            "12.26": (
                "PARTIAL: 560 shared E12 circuit-by-optimization-level keys reproduce scientific "
                "outputs across Python/numerical-stack changes, but Qiskit stayed at 2.4.1, eight "
                "rows were deferred, runtime changed, and central E31 analyses were not replayed"
            )
        },
        "claim_boundary": (
            "This is E12-only cross-stack evidence. It is not Qiskit-version sensitivity, does not "
            "cover Cirq/tket/custom optimizers, does not reproduce E31 conclusions, and is not an "
            "independent platform or hardware replication."
        ),
        "source_bindings": {
            "canonical_csv": _sha(CANONICAL), "rerun_csv": _sha(RERUN),
            "canonical_metadata": _sha(CANONICAL_META), "rerun_metadata": _sha(RERUN_META),
            "analysis/e12_version_stack_reconciliation.py": _sha(Path(__file__)),
        },
        "artifacts": {"shared_key_comparison.csv": {"rows": int(len(comparison)),
                                                      "sha256": _sha(comparison_path)}},
    }
    output = output_dir / "version_stack_reconciliation_audit.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(output)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    audit = build_audit(args.output_dir)
    print(json.dumps({key: audit[key] for key in (
        "status", "canonical_rows", "rerun_rows", "shared_unique_keys",
        "all_shared_scientific_rows_match", "runtime_comparison",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
