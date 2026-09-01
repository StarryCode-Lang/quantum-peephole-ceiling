"""Revalidate external optimizer outputs with the frozen exact-fidelity rule.

Raw driver results remain immutable.  This script writes separate
``*_revalidated.csv`` files using the project's exact full-operator average
gate fidelity and the preregistered threshold 1 - 1e-10.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit import qasm2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import average_gate_fidelity
from src.provenance import file_sha256

KEY = ["circuit_id", "trial", "seed"]
THRESHOLD = 1.0 - 1e-10


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _load_qasm(path: Path):
    return qasm2.loads(
        path.read_text(encoding="utf-8"),
        custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
    )


def _revalidate(method: str, raw_path: Path, manifest_path: Path,
                output_path: Path) -> dict[str, object]:
    raw_path, manifest_path = raw_path.resolve(), manifest_path.resolve()
    frame = pd.read_csv(raw_path)
    manifest = pd.read_csv(manifest_path)
    if len(frame) != 520 or frame.duplicated(KEY).any():
        raise RuntimeError(f"{method}: raw result key integrity failure")
    if len(manifest) != 520 or manifest.duplicated(KEY).any():
        raise RuntimeError(f"{method}: manifest key integrity failure")
    source_column = "qasm_path" if method == "quasar" else "source_common_qasm_path"
    manifest_hash_column = "input_circuit_sha256"
    manifest_columns = KEY + [source_column, manifest_hash_column]
    manifest_subset = manifest[manifest_columns].rename(
        columns={manifest_hash_column: "revalidation_source_sha256"}
    )
    joined = frame.merge(
        manifest_subset, on=KEY, how="left", validate="one_to_one",
        suffixes=("", "_manifest"),
    )
    if joined[source_column].isna().any():
        raise RuntimeError(f"{method}: missing source path after manifest join")
    legacy = joined.exact_equivalent.astype(str).str.lower().eq("true")
    fidelities = np.full(len(joined), np.nan, dtype=float)
    cache: dict[tuple[str, str], float] = {}
    cache_hits = 0
    computed = 0
    for index, row in enumerate(joined.itertuples(index=False)):
        output_relative = str(row.output_qasm_path) if pd.notna(row.output_qasm_path) else ""
        if str(row.status) != "ok" or not output_relative:
            continue
        source_path = PROJECT_ROOT / str(getattr(row, source_column))
        output_file = PROJECT_ROOT / output_relative
        if not source_path.is_file() or not output_file.is_file():
            raise RuntimeError(f"{method}: missing source/output for {row.circuit_id}")
        output_hash = hashlib.sha256(output_file.read_bytes()).hexdigest()
        if output_hash != str(row.output_qasm_sha256):
            raise RuntimeError(f"{method}: output hash mismatch for {row.circuit_id}")
        key = (str(row.revalidation_source_sha256), output_hash)
        if key in cache:
            fidelity = cache[key]
            cache_hits += 1
        else:
            fidelity = average_gate_fidelity(
                _load_qasm(output_file), _load_qasm(source_path), max_qubits=10)
            if fidelity is None or not np.isfinite(fidelity):
                raise RuntimeError(f"{method}: exact fidelity unavailable for {row.circuit_id}")
            cache[key] = float(fidelity)
            computed += 1
        fidelities[index] = fidelity
    valid = np.isfinite(fidelities) & (fidelities >= THRESHOLD)
    joined["legacy_operator_equiv"] = legacy
    joined["exact_average_gate_fidelity"] = fidelities
    joined["fidelity_threshold"] = THRESHOLD
    joined["exact_equivalent"] = valid
    joined["valid_equivalent_output"] = valid
    joined["fidelity_source"] = np.where(np.isfinite(fidelities), "exact", "unavailable")
    if method == "quasar":
        joined["analysis_gate_reduction_pct_itt"] = np.where(
            valid, joined.gate_reduction_pct.astype(float), 0.0)
    else:
        for metric in ("gate", "two_qubit", "depth"):
            raw_column = f"analysis_common_{metric}_reduction_pct"
            itt_column = f"analysis_common_{metric}_reduction_pct_itt"
            joined[itt_column] = np.where(valid, joined[raw_column].astype(float), 0.0)
    drop = [name for name in joined.columns
            if name.endswith("_manifest") or name == "revalidation_source_sha256"]
    joined = joined.drop(columns=drop)
    _atomic_text(output_path, joined.to_csv(index=False))
    return {
        "method": method,
        "rows": len(joined),
        "raw_sha256": file_sha256(raw_path),
        "manifest_sha256": file_sha256(manifest_path),
        "revalidated_sha256": file_sha256(output_path),
        "legacy_valid_n": int(legacy.sum()),
        "revalidated_valid_n": int(valid.sum()),
        "threshold": THRESHOLD,
        "fidelity_formula": "(abs(Tr(U_dagger V))^2 + d) / (d^2 + d)",
        "exact_operator_pairs_computed": computed,
        "cache_hits": cache_hits,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quasar-raw", type=Path, required=True)
    parser.add_argument("--quasar-manifest", type=Path, required=True)
    parser.add_argument("--quartz-raw", type=Path, required=True)
    parser.add_argument("--quartz-manifest", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    records = [
        _revalidate(
            "quasar", args.quasar_raw, args.quasar_manifest,
            args.quasar_raw.with_name("quasar_shared_520_revalidated.csv"),
        ),
        _revalidate(
            "quartz", args.quartz_raw, args.quartz_manifest,
            args.quartz_raw.with_name("quartz_shared_520_revalidated.csv"),
        ),
    ]
    audit = {
        "status": "complete",
        "rule": "frozen exact full-operator average gate fidelity >= 1 - 1e-10",
        "raw_results_preserved": True,
        "records": records,
        "source_sha256": file_sha256(Path(__file__).resolve()),
    }
    _atomic_text(args.audit.resolve(), json.dumps(audit, indent=2, sort_keys=True))
    print(json.dumps(audit, sort_keys=True))


if __name__ == "__main__":
    main()
