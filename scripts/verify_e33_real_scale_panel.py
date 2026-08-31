"""Independently replay E33 hashes and symbolic equality decisions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import pyzx

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_id(input_hash: str, listing: str) -> str:
    return "e33-" + hashlib.sha256(f"E33|{input_hash}|{listing}".encode()).hexdigest()[:24]


def verify(protocol_path: Path, output_dir: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    manifest_path = output_dir / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with (output_dir / "results.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {run_id(source["input_circuit_sha256"], listing) for source in protocol["inputs"] for listing in protocol["factors"]["listing_model"]}
    if len(rows) != 22 or {row["run_id"] for row in rows} != expected:
        raise ValueError("E33 result schedule mismatch")
    if summary.get("protocol_sha256") != sha256(protocol_path) or summary.get("itt_observed_n") != 22:
        raise ValueError("E33 summary/protocol binding mismatch")
    replay_proved = 0; mutants_rejected = 0
    for row in rows:
        receipt = json.loads((output_dir / "cells" / f"{row['run_id']}.json").read_text(encoding="utf-8"))
        if receipt["status"] != "success":
            continue
        left_path = ROOT / receipt["original_basis_qasm_path"]
        right_path = ROOT / receipt["optimized_basis_qasm_path"]
        if sha256(left_path) != receipt["original_basis_qasm_sha256"] or sha256(right_path) != receipt["optimized_basis_qasm_sha256"]:
            raise ValueError(f"E33 QASM hash mismatch: {row['run_id']}")
        left = pyzx.Circuit.from_qasm(left_path.read_text(encoding="utf-8"))
        right = pyzx.Circuit.from_qasm(right_path.read_text(encoding="utf-8"))
        decision = left.verify_equality(right, up_to_swaps=False, up_to_global_phase=True)
        if decision is not True:
            raise ValueError(f"E33 independent proof not reproduced: {row['run_id']}")
        replay_proved += 1
        right.add_gate("NOT", 0)
        if left.verify_equality(right, up_to_swaps=False, up_to_global_phase=True) is not True:
            mutants_rejected += 1
    listed = {entry["path"]: entry for entry in manifest["artifacts"]}
    if len(listed) != int(manifest["artifact_count"]):
        raise ValueError("E33 manifest cardinality mismatch")
    for relative, entry in listed.items():
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size != int(entry["bytes"]) or sha256(path) != entry["sha256"]:
            raise ValueError(f"E33 artifact mismatch: {relative}")
    if replay_proved != int(summary["proved_equal_n"]) or mutants_rejected != replay_proved:
        raise ValueError("E33 proof or mutation counts mismatch")
    return {
        "status": "VERIFIED", "rows": 22, "proved_equal": replay_proved, "mutants_rejected": mutants_rejected,
        "protocol_sha256": sha256(protocol_path), "artifact_manifest_sha256": sha256(manifest_path),
        "metric_dispositions": {
            "13.12": {"status": "PARTIAL", "disposition": "Direct proof-audited fixed-panel evidence at 11-36 qubits, beyond the prior 4-10 range; no unseen-family or all-width extrapolation."},
            "13.17": {"status": "PARTIAL", "disposition": "External application-oriented benchmark circuits are executed, but they are not field-collected production workloads."},
            "17.29": {"status": "PASS", "disposition": "The complete E33 panel uses only checksum-pinned circuits from the independent Quasar Zenodo artifact and no project-generated benchmark."},
            "17.30": {"status": "PARTIAL", "disposition": "The panel is entirely external benchmark circuits, but external benchmark is not synonymous with real production circuit."},
        },
        "claim_boundary": protocol["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=ROOT / "experiments/e33_real_scale_protocol.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/v11/e33_real_scale")
    parser.add_argument("--receipt", type=Path, default=ROOT / "release/e33_real_scale_independent_verification_receipt.json")
    args = parser.parse_args()
    receipt = verify(args.protocol.resolve(), args.output_dir.resolve())
    receipt["verifier_sha256"] = sha256(Path(__file__).resolve())
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
