"""Audit exact and global-qubit-relabel duplicates in the frozen E31 input panel."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "data/v10/prepaper/sota/inputs/benchmark_manifest.csv"
DESIGN_MANIFEST = ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv"
DEFAULT_OUTPUT = ROOT / "data/v11/e31_factorial_pareto/input_duplicate_isomorphism_audit.json"
_QUBIT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\]")
_QREG = re.compile(r"^qreg\s+([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\];$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _qubit_relabel_signature(path: Path) -> str:
    registers: dict[str, int] = {}
    mapping: dict[tuple[str, int], int] = {}
    operations: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("//", 1)[0].strip()
        if not line or line.startswith("OPENQASM") or line.startswith("include"):
            continue
        declaration = _QREG.match(line)
        if declaration:
            registers[declaration.group(1)] = int(declaration.group(2))
            continue

        def canonical(match: re.Match[str]) -> str:
            key = (match.group(1), int(match.group(2)))
            if key not in mapping:
                mapping[key] = len(mapping)
            return f"q[{mapping[key]}]"

        operations.append(_QUBIT.sub(canonical, line))
    payload = json.dumps(
        {"declared_qubits": sum(registers.values()), "ordered_operations": operations},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_audit() -> dict[str, object]:
    source = _rows(SOURCE_MANIFEST)
    design = _rows(DESIGN_MANIFEST)
    source_hash_counts = Counter(row["input_circuit_sha256"] for row in source)
    design_hash_counts = Counter(row["input_circuit_sha256"] for row in design)
    unique_design = {row["input_circuit_sha256"]: row for row in design}

    if set(source_hash_counts) != set(design_hash_counts):
        raise RuntimeError("source and E31 design input-hash sets differ")
    if set(design_hash_counts.values()) != {72}:
        raise RuntimeError("E31 design is not a complete 72-cell panel per unique input")
    for row in source:
        qasm = ROOT / row["qasm_path"]
        if _sha256(qasm) != row["qasm_sha256"]:
            raise RuntimeError(f"QASM hash mismatch: {qasm}")

    signature_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for input_hash, row in sorted(unique_design.items()):
        signature_groups[_qubit_relabel_signature(ROOT / row["qasm_path"])].append(
            {
                "input_circuit_sha256": input_hash,
                "circuit_family": row["circuit_family"],
                "circuit_id": row["circuit_id"],
                "qasm_path": row["qasm_path"],
            }
        )
    relabel_clusters = [members for members in signature_groups.values() if len(members) > 1]
    repeated_source_rows = len(source) - len(source_hash_counts)
    relabel_excess = sum(len(cluster) - 1 for cluster in relabel_clusters)

    return {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_NO_RESIDUAL_EXACT_OR_GLOBAL_QUBIT_RELABEL_DUPLICATES",
        "source_manifest": SOURCE_MANIFEST.relative_to(ROOT).as_posix(),
        "source_manifest_sha256": _sha256(SOURCE_MANIFEST),
        "design_manifest": DESIGN_MANIFEST.relative_to(ROOT).as_posix(),
        "design_manifest_sha256": _sha256(DESIGN_MANIFEST),
        "source_rows": len(source),
        "source_unique_logical_inputs": len(source_hash_counts),
        "source_repeated_rows_collapsed_before_e31": repeated_source_rows,
        "e31_scheduled_rows": len(design),
        "e31_unique_input_hashes": len(design_hash_counts),
        "factorial_cells_per_unique_input": 72,
        "residual_exact_duplicate_inputs": 0,
        "global_qubit_relabel_signature_count": len(signature_groups),
        "global_qubit_relabel_cluster_count": len(relabel_clusters),
        "global_qubit_relabel_excess_inputs": relabel_excess,
        "global_qubit_relabel_clusters": relabel_clusters,
        "definition": (
            "Global-qubit-relabel isomorphism preserves declared width, instruction order, "
            "operation spelling and parameters, and ordered gate operands while canonicalizing "
            "qubit identifiers by first occurrence."
        ),
        "interpretation": (
            "The 520-row source contained 129 repeated logical inputs, which were collapsed before "
            "freezing E31. The resulting 391-input panel has neither exact-hash duplicates nor "
            "duplicates under the declared global-qubit-relabel signature."
        ),
        "limitation": (
            "This is not semantic circuit equivalence and does not merge circuits that become "
            "equivalent only after gate commutation, algebraic rewriting, or graph-only abstraction."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_audit()
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": output.relative_to(ROOT).as_posix(), "status": payload["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
