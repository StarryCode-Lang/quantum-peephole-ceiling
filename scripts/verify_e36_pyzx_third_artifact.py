"""Independently exact-verify the frozen E36 PyZX optimizer outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from qiskit import qasm2
from qiskit.quantum_info import Operator, average_gate_fidelity

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e36_pyzx_third_artifact import unitary_qasm


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fidelity(left, right) -> float:
    return float(average_gate_fidelity(Operator(left), Operator(right)))


def verify(protocol_path: Path, output_dir: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8")); summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8")); manifest_path = output_dir / "artifact_manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if summary.get("status") != "FORMAL_BOUNDED_PANEL_COMPLETE" or summary.get("protocol_sha256") != sha256(protocol_path) or len(summary.get("rows", [])) != 3:
        raise ValueError("E36 incomplete or protocol-unbound")
    fidelities = []; mutant_fidelities = []
    for row in summary["rows"]:
        source_qasm, original = unitary_qasm(ROOT / row["source_path"])
        output_path = ROOT / row["optimized_qasm_path"]
        if sha256(output_path) != row["optimized_qasm_sha256"]:
            raise ValueError("E36 optimized QASM hash mismatch")
        optimized = qasm2.load(output_path, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
        value = fidelity(original, optimized); fidelities.append(value)
        mutant = optimized.copy(); mutant.x(0); mutant_value = fidelity(original, mutant); mutant_fidelities.append(mutant_value)
        if value < float(protocol["verification_contract"]["threshold"]) or mutant_value >= float(protocol["verification_contract"]["threshold"]):
            raise ValueError(f"E36 exact fidelity or mutant sentinel failed: {row['case_id']}")
    listed = {entry["path"]: entry for entry in manifest["artifacts"]}
    if len(listed) != int(manifest["artifact_count"]) or len(listed) != 7:
        raise ValueError("E36 manifest cardinality mismatch")
    for relative, entry in listed.items():
        path = ROOT / relative
        if path.stat().st_size != int(entry["bytes"]) or sha256(path) != entry["sha256"]:
            raise ValueError(f"E36 artifact mismatch: {relative}")
    return {"status": "VERIFIED", "rows": 3, "minimum_exact_average_gate_fidelity": min(fidelities), "maximum_x_mutant_average_gate_fidelity": max(mutant_fidelities), "protocol_sha256": sha256(protocol_path), "artifact_manifest_sha256": sha256(manifest_path), "metric_dispositions": summary["metric_dispositions"], "claim_boundary": summary["claim_boundary"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--protocol", type=Path, default=ROOT / "experiments/e36_pyzx_third_artifact_protocol.json"); parser.add_argument("--output-dir", type=Path, default=ROOT / "data/v11/e36_pyzx_third_artifact"); parser.add_argument("--receipt", type=Path, default=ROOT / "release/e36_pyzx_third_artifact_independent_verification_receipt.json"); args = parser.parse_args()
    receipt = verify(args.protocol.resolve(), args.output_dir.resolve()); receipt["verifier_sha256"] = sha256(Path(__file__).resolve()); args.receipt.parent.mkdir(parents=True, exist_ok=True); args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"); print(json.dumps(receipt, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
