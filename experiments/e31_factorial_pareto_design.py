"""Generate the pre-freeze E31 full-factorial and equal-budget run schedule.

This module schedules work only.  It never invokes an optimizer and therefore
cannot create scientific result rows.  Duplicate source rows with the same
input hash are collapsed before treatment expansion so that a seed which did
not change the circuit cannot become a false independent replicate.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = PROJECT_ROOT / "experiments" / "e31_factorial_pareto_protocol.json"
DEFAULT_INPUT = PROJECT_ROOT / "data" / "v10" / "prepaper" / "sota" / "inputs" / "benchmark_manifest.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "v11" / "e31_factorial_pareto"
INPUT_COLUMNS = {
    "circuit_id", "circuit_family", "n_qubits", "input_circuit_sha256", "qasm_path"
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_hash(*parts: object) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()


def load_unique_inputs(path: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    """Load one row per actual input circuit and audit collapsed repetitions."""
    frame = pd.read_csv(path.resolve())
    missing = INPUT_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"input manifest lacks columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("input manifest is empty")
    hashes = frame["input_circuit_sha256"].astype(str)
    if not hashes.str.fullmatch(r"[0-9a-f]{64}").all():
        raise ValueError("input manifest contains a malformed SHA-256")
    # A byte-identical input may be a technical repeat, but it must not have
    # contradictory family/size/QASM metadata.
    for digest, group in frame.groupby("input_circuit_sha256", sort=False):
        for column in ("circuit_family", "n_qubits"):
            if group[column].nunique(dropna=False) != 1:
                raise ValueError(f"input hash {digest} has conflicting {column}")
        if group["qasm_path"].nunique(dropna=False) != 1:
            # Multiple materialized files are acceptable only if their QASM
            # content hash proves equality; qasm_sha256 is required then.
            if "qasm_sha256" not in group or group["qasm_sha256"].nunique() != 1:
                raise ValueError(f"input hash {digest} has ambiguous QASM lineage")
    sort_columns = [name for name in ("circuit_family", "n_qubits", "circuit_id", "trial", "seed")
                    if name in frame]
    frame = frame.sort_values(sort_columns, kind="stable")
    counts = frame.groupby("input_circuit_sha256").size().rename("source_rows_collapsed")
    unique = frame.drop_duplicates("input_circuit_sha256", keep="first").copy()
    unique["source_rows_collapsed"] = unique["input_circuit_sha256"].map(counts).astype(int)
    audit = {
        "source_rows": int(len(frame)),
        "unique_input_hashes": int(len(unique)),
        "collapsed_repeated_rows": int(len(frame) - len(unique)),
    }
    return unique.reset_index(drop=True), audit


def treatment_cells(protocol: dict) -> list[dict[str, object]]:
    factors = protocol["factors"]
    names = ("listing_model", "rule_set", "window_gates", "budget_seconds")
    return [dict(zip(names, values)) for values in itertools.product(
        *(factors[name] for name in names)
    )]


def build_design(inputs: pd.DataFrame, protocol: dict, protocol_sha256: str) -> pd.DataFrame:
    """Return a complete repeated-measures factorial with seeded run order."""
    if inputs["input_circuit_sha256"].duplicated().any():
        raise ValueError("build_design requires one row per unique input hash")
    cells = treatment_cells(protocol)
    inputs = inputs.copy()
    # Freeze a family-stratified, near-balanced orientation for the paired
    # primary contrast. It is analysis metadata, not another replicate.
    orientations: dict[str, int] = {}
    for family, group in inputs.groupby("circuit_family", sort=True):
        ordered = sorted(
            group["input_circuit_sha256"].astype(str),
            key=lambda digest: _stable_hash(protocol["randomization_seed"], family, digest),
        )
        start = 1 if int(_stable_hash(protocol["randomization_seed"], family)[:2], 16) % 2 else -1
        orientations.update({digest: start * (1 if index % 2 == 0 else -1)
                             for index, digest in enumerate(ordered)})
    rows: list[dict[str, object]] = []
    for source in inputs.to_dict(orient="records"):
        digest = str(source["input_circuit_sha256"])
        for cell in cells:
            listing_seed = int(_stable_hash(
                protocol["randomization_seed"], digest, cell["listing_model"]
            )[:8], 16)
            run_id = _stable_hash(
                protocol_sha256, digest, cell["listing_model"], cell["rule_set"],
                cell["window_gates"], cell["budget_seconds"]
            )
            rows.append({
                "experiment_id": protocol["experiment_id"],
                "run_id": run_id,
                "protocol_sha256": protocol_sha256,
                "block_id": digest,
                "circuit_id": source["circuit_id"],
                "circuit_family": source["circuit_family"],
                "n_qubits": int(source["n_qubits"]),
                "input_circuit_sha256": digest,
                "qasm_path": source["qasm_path"],
                "source_rows_collapsed": int(source["source_rows_collapsed"]),
                "primary_pair_orientation": int(orientations[digest]),
                **cell,
                "listing_seed": listing_seed,
                "memory_budget_mb": int(protocol["resource_contract"]["memory_budget_mb_per_worker"]),
            })
    design = pd.DataFrame(rows)
    rng = np.random.default_rng(int(protocol["randomization_seed"]))
    permutation = rng.permutation(len(design))
    design = design.iloc[permutation].reset_index(drop=True)
    design.insert(2, "run_order", np.arange(len(design), dtype=int))
    validate_design(design, protocol)
    return design


def validate_design(design: pd.DataFrame, protocol: dict) -> None:
    """Reject duplicate, incomplete, or pseudoreplicated schedules."""
    cells = treatment_cells(protocol)
    expected_per_input = len(cells)
    if design.empty or design["run_id"].duplicated().any():
        raise ValueError("design has no rows or duplicate run_id values")
    if design["input_circuit_sha256"].nunique() * expected_per_input != len(design):
        raise ValueError("design row count is not inputs x full-factorial cells")
    factor_names = ["listing_model", "rule_set", "window_gates", "budget_seconds"]
    expected_cells = {tuple(cell[name] for name in factor_names) for cell in cells}
    for digest, group in design.groupby("input_circuit_sha256", sort=False):
        observed = set(map(tuple, group[factor_names].itertuples(index=False, name=None)))
        if observed != expected_cells or len(group) != expected_per_input:
            raise ValueError(f"input {digest} lacks a complete factorial")
        if group["circuit_family"].nunique() != 1:
            raise ValueError(f"input {digest} crosses family metadata")
        if group["primary_pair_orientation"].nunique() != 1:
            raise ValueError(f"input {digest} crosses primary-pair orientation")
    orientation = design[["input_circuit_sha256", "circuit_family",
                          "primary_pair_orientation"]].drop_duplicates()
    imbalance = orientation.groupby("circuit_family")["primary_pair_orientation"].sum().abs()
    if (imbalance > 1).any():
        raise ValueError("primary-pair orientation is not balanced within family")
    if sorted(design["run_order"].astype(int)) != list(range(len(design))):
        raise ValueError("run_order is not a permutation of the scheduled rows")


def generate(input_manifest: Path, protocol_path: Path, output_dir: Path) -> tuple[Path, Path]:
    protocol_path = protocol_path.resolve()
    input_manifest = input_manifest.resolve()
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    unique, input_audit = load_unique_inputs(input_manifest)
    protocol_sha = file_sha256(protocol_path)
    design = build_design(unique, protocol, protocol_sha)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "design_manifest.csv"
    metadata_path = output_dir / "design_metadata.json"
    design.to_csv(manifest_path, index=False)
    power_path = output_dir / "dual_estimand_power.json"
    power_bound = False
    if power_path.exists():
        power = json.loads(power_path.read_text(encoding="utf-8"))
        power_bound = (
            power.get("protocol_sha256") == protocol_sha
            and power.get("design_manifest_sha256") == file_sha256(manifest_path)
            and power.get("decision", {}).get("fixed_benchmark_A") == "PASS"
        )
    metadata = {
        "experiment_id": protocol["experiment_id"],
        "status": protocol["design_status"],
        "scientific_results_present": False,
        "formal_execution_authorized": (
            protocol["design_status"] == "FROZEN_BEFORE_EXECUTION" and power_bound
        ),
        "dual_estimand_power_bound": power_bound,
        "protocol_file": str(protocol_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "protocol_sha256": protocol_sha,
        "source_manifest": str(input_manifest.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "source_manifest_sha256": file_sha256(input_manifest),
        "design_manifest_sha256": file_sha256(manifest_path),
        "factorial_cells_per_input": len(treatment_cells(protocol)),
        "scheduled_rows": int(len(design)),
        "families": int(unique["circuit_family"].nunique()),
        **input_audit,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path, metadata_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    manifest, metadata = generate(args.input_manifest, args.protocol, args.output_dir)
    print(json.dumps({"design_manifest": str(manifest), "metadata": str(metadata)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
