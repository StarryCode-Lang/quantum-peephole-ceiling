"""Independently replay the frozen compiler-version panel artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit import qasm2
from qiskit.quantum_info import Operator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.compiler_version_panel_worker import (
    _canonical_gate_counts,
    _instruction_fingerprint,
)


DEFAULT_INPUT_DIR = ROOT / "data/v11/compiler_version_sensitivity"
DEFAULT_OUTPUT = DEFAULT_INPUT_DIR / "independent_verification.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(input_dir: Path = DEFAULT_INPUT_DIR, output: Path = DEFAULT_OUTPUT) -> dict:
    audit_path = input_dir / "compiler_version_sensitivity_audit.json"
    combined_path = input_dir / "all_version_results.csv"
    panel_path = input_dir / "frozen_panel.csv"
    comparison_path = input_dir / "per_tool_version_comparison.csv"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    combined = pd.read_csv(combined_path)
    panel = pd.read_csv(panel_path)

    if len(combined) != 105 or combined["environment_id"].nunique() != 7:
        raise RuntimeError("compiler-version combined table is not the 7x15 design")
    if len(panel) != 15 or panel["circuit_family"].nunique() != 15:
        raise RuntimeError("compiler-version panel is not one row per family")
    if audit["artifacts"]["all_version_results.csv"]["sha256"] != sha256(combined_path):
        raise RuntimeError("combined compiler-version table hash drift")
    if audit["artifacts"]["per_tool_version_comparison.csv"]["sha256"] != sha256(comparison_path):
        raise RuntimeError("compiler-version comparison table hash drift")
    if audit["panel"]["sha256"] != sha256(panel_path):
        raise RuntimeError("compiler-version panel hash drift")

    panel_lookup = panel.set_index(["circuit_family", "circuit_id"], verify_integrity=True)
    environment_records = {
        item["environment_id"]: item for item in audit["executed_environments"]
    }
    if set(environment_records) != set(combined["environment_id"]):
        raise RuntimeError("environment inventory differs from combined results")
    for environment_id, record in environment_records.items():
        run_dir = input_dir / "runs" / environment_id
        result_path = ROOT / record["result_path"]
        environment_path = run_dir / "environment.json"
        lock_path = run_dir / "resolved_requirements.txt"
        if (
            sha256(result_path) != record["result_sha256"]
            or sha256(environment_path) != record["environment_sha256"]
            or sha256(lock_path) != record["resolved_requirements_sha256"]
        ):
            raise RuntimeError(f"environment closure hash drift: {environment_id}")
        raw = pd.read_csv(result_path)
        expected = combined.loc[combined["environment_id"].eq(environment_id)].reset_index(drop=True)
        if not raw.reset_index(drop=True).equals(expected):
            raise RuntimeError(f"combined table differs from raw run: {environment_id}")
        metadata = json.loads(environment_path.read_text(encoding="utf-8"))
        if (
            metadata.get("environment_id") != environment_id
            or int(metadata.get("rows", -1)) != 15
            or metadata.get("results_sha256") != record["result_sha256"]
            or metadata.get("panel_sha256") != sha256(panel_path)
        ):
            raise RuntimeError(f"environment metadata mismatch: {environment_id}")

    minimum_overlap = 1.0
    verified_qasm_paths: set[str] = set()
    for row in combined.to_dict(orient="records"):
        key = (row["circuit_family"], row["circuit_id"])
        panel_row = panel_lookup.loc[key]
        input_path = ROOT / str(panel_row["qasm_path"])
        output_path = ROOT / str(row["optimized_qasm_path"])
        if sha256(input_path) != str(row["qasm_sha256"]):
            raise RuntimeError(f"input QASM hash drift: {key}")
        if sha256(output_path) != str(row["optimized_qasm_sha256"]):
            raise RuntimeError(f"optimized QASM hash drift: {row['optimized_qasm_path']}")
        if str(row["optimized_qasm_path"]) in verified_qasm_paths:
            raise RuntimeError("optimized QASM path is reused across panel cells")
        verified_qasm_paths.add(str(row["optimized_qasm_path"]))
        original = qasm2.loads(
            input_path.read_text(encoding="utf-8"),
            custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
        )
        optimized = qasm2.loads(
            output_path.read_text(encoding="utf-8"),
            custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
        )
        dimension = 2 ** original.num_qubits
        overlap = float(abs(
            np.trace(Operator(original).data.conj().T @ Operator(optimized).data)
        ) / dimension)
        minimum_overlap = min(minimum_overlap, overlap)
        if overlap < 1.0 - 1e-10:
            raise RuntimeError(f"semantic replay failed: {row['environment_id']}/{key}")
        if not np.isclose(overlap, float(row["unitary_trace_overlap"]), atol=1e-12, rtol=0):
            raise RuntimeError(f"recorded unitary overlap drift: {row['environment_id']}/{key}")
        if (
            int(row["output_gate_count"]) != optimized.size()
            or int(row["output_depth"]) != optimized.depth()
            or str(row["output_instruction_sha256"]) != _instruction_fingerprint(optimized)
            or json.loads(str(row["output_gate_counts_json"]))
            != _canonical_gate_counts(optimized)
        ):
            raise RuntimeError(f"optimized structure drift: {row['environment_id']}/{key}")

    payload = {
        "schema_version": "1.0.0",
        "status": "PASS_INDEPENDENT_COMPILER_VERSION_REPLAY",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "design_rows": int(len(combined)),
        "environments": int(combined["environment_id"].nunique()),
        "families": int(panel["circuit_family"].nunique()),
        "optimized_qasm_artifacts_verified": len(verified_qasm_paths),
        "semantic_unitaries_recomputed": int(len(combined)),
        "minimum_unitary_trace_overlap": minimum_overlap,
        "equivalence_threshold": 1.0 - 1e-10,
        "all_structure_fingerprints_recomputed": True,
        "source_bindings": {
            audit_path.relative_to(ROOT).as_posix(): sha256(audit_path),
            combined_path.relative_to(ROOT).as_posix(): sha256(combined_path),
            panel_path.relative_to(ROOT).as_posix(): sha256(panel_path),
            Path(__file__).resolve().relative_to(ROOT).as_posix(): sha256(Path(__file__)),
        },
        "claim_boundary": (
            "Independent replay is exhaustive over this 105-row, 15-family, "
            "4-5-qubit panel only; it is numerical full-unitary evidence and does "
            "not establish larger-width, unseen-family, cross-platform, or full-E31 robustness."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(verify(args.input_dir.resolve(), args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
