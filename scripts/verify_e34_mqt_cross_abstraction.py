"""Independently verify the materialized E34 MQT four-level panel."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from qiskit import qasm2

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(protocol_path: Path, output_dir: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    manifest_path = output_dir / "artifact_manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = summary["rows"]
    if summary.get("status") != "FORMAL_BOUNDED_PANEL_COMPLETE" or summary.get("protocol_sha256") != sha256(protocol_path) or len(rows) != 12:
        raise ValueError("E34 panel incomplete or protocol-unbound")
    expected_levels = sorted(protocol["levels"])
    for case in protocol["sample"]:
        block = [row for row in rows if row["benchmark"] == case["benchmark"] and int(row["circuit_size"]) == int(case["circuit_size"])]
        if sorted(row["level"] for row in block) != expected_levels:
            raise ValueError("E34 same-case four-level block incomplete")
    coupling = {tuple(edge) for edge in summary["target_coupling_edges"]}
    native = set(summary["target_operation_names"])
    for row in rows:
        path = ROOT / row["qasm_path"]
        if sha256(path) != row["qasm_sha256"]:
            raise ValueError(f"E34 QASM hash mismatch: {path}")
        circuit = qasm2.load(path, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
        if circuit.num_qubits != int(row["n_qubits"]) or circuit.size() != int(row["gate_count"]) or int(circuit.depth() or 0) != int(row["depth"]):
            raise ValueError(f"E34 QASM metrics mismatch: {path}")
        if row["level"] in {"NATIVEGATES", "MAPPED"} and not (set(circuit.count_ops()) - {"barrier"}).issubset(native):
            raise ValueError(f"E34 native alphabet violation: {path}")
        if row["level"] == "MAPPED":
            for instruction in circuit.data:
                if len(instruction.qubits) == 2:
                    edge = tuple(circuit.find_bit(bit).index for bit in instruction.qubits)
                    if edge not in coupling and tuple(reversed(edge)) not in coupling:
                        raise ValueError(f"E34 mapped coupling violation: {path}")
    listed = {entry["path"]: entry for entry in manifest["artifacts"]}
    if len(listed) != int(manifest["artifact_count"]) or len(listed) != 16:
        raise ValueError("E34 artifact manifest cardinality mismatch")
    for relative, entry in listed.items():
        path = ROOT / relative
        if path.stat().st_size != int(entry["bytes"]) or sha256(path) != entry["sha256"]:
            raise ValueError(f"E34 artifact manifest mismatch: {relative}")
    return {"status": "VERIFIED", "same_case_blocks": 3, "levels_per_block": 4, "qasm_artifacts": 12, "protocol_sha256": sha256(protocol_path), "artifact_manifest_sha256": sha256(manifest_path), "metric_dispositions": summary["metric_dispositions"], "claim_boundary": summary["claim_boundary"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=ROOT / "experiments/e34_mqt_cross_abstraction_protocol.json"); parser.add_argument("--output-dir", type=Path, default=ROOT / "data/v11/e34_mqt_cross_abstraction")
    parser.add_argument("--receipt", type=Path, default=ROOT / "release/e34_mqt_cross_abstraction_independent_verification_receipt.json")
    args = parser.parse_args(); receipt = verify(args.protocol.resolve(), args.output_dir.resolve()); receipt["verifier_sha256"] = sha256(Path(__file__).resolve())
    args.receipt.parent.mkdir(parents=True, exist_ok=True); args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
