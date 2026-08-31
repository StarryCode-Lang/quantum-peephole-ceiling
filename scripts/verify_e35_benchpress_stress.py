"""Independently verify E35 schedule, external hashes, receipts, and manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(protocol_path: Path, output_dir: Path, benchpress_root: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8")); summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8")); manifest_path = output_dir / "artifact_manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if summary.get("status") != "FORMAL_STRESS_SCHEDULE_COMPLETE" or summary.get("itt_observed_n") != 5 or summary.get("protocol_sha256") != sha256(protocol_path):
        raise ValueError("E35 incomplete or protocol-unbound")
    ids = set()
    for source in protocol["inputs"]:
        path = benchpress_root / source["relative_path"]
        if path.stat().st_size != int(source["bytes"]) or sha256(path) != source["sha256"]:
            raise ValueError(f"E35 external input drift: {path}")
        cell_id = "e35-" + hashlib.sha256(f"{source['sha256']}|stress-v1".encode()).hexdigest()[:24]; ids.add(cell_id)
        receipt = json.loads((output_dir / "cells" / f"{cell_id}.json").read_text(encoding="utf-8"))
        if receipt["cell_id"] != cell_id or receipt["status"] not in {"success", "timeout", "memory_cap", "error"}:
            raise ValueError(f"E35 invalid terminal receipt: {cell_id}")
        if int(receipt["peak_process_tree_rss_bytes"]) > int(protocol["resource_contract"]["rss_cap_bytes"]) * 2:
            raise ValueError(f"E35 implausible uncapped RSS receipt: {cell_id}")
        if receipt["status"] == "success" and (int(receipt["parsed_qubits"]) != int(source["expected_qubits_from_name"]) or receipt["semantic_status"] != "UNAVAILABLE_LARGE_STRESS_ONLY"):
            raise ValueError(f"E35 successful receipt metrics/boundary invalid: {cell_id}")
    if len(ids) != 5:
        raise ValueError("E35 duplicate cell IDs")
    listed = {entry["path"]: entry for entry in manifest["artifacts"]}
    if len(listed) != int(manifest["artifact_count"]) or len(listed) != 14:
        raise ValueError("E35 manifest cardinality mismatch")
    for relative, entry in listed.items():
        path = ROOT / relative
        if path.stat().st_size != int(entry["bytes"]) or sha256(path) != entry["sha256"]:
            raise ValueError(f"E35 artifact mismatch: {relative}")
    return {"status": "VERIFIED", "itt_cells": 5, "status_counts": summary["status_counts"], "large_cells_observed": summary["large_cells_observed"], "large_cells_successful": summary["large_cells_successful"], "maximum_declared_qubits": summary["maximum_declared_qubits"], "protocol_sha256": sha256(protocol_path), "artifact_manifest_sha256": sha256(manifest_path), "metric_dispositions": summary["metric_dispositions"], "semantic_boundary": summary["semantic_boundary"], "claim_boundary": summary["claim_boundary"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--protocol", type=Path, default=ROOT / "experiments/e35_benchpress_stress_protocol.json"); parser.add_argument("--output-dir", type=Path, default=ROOT / "data/v11/e35_benchpress_stress"); parser.add_argument("--benchpress-root", type=Path, default=Path("D:/Downloads/qresearch-benchpress-official")); parser.add_argument("--receipt", type=Path, default=ROOT / "release/e35_benchpress_stress_independent_verification_receipt.json"); args = parser.parse_args()
    receipt = verify(args.protocol.resolve(), args.output_dir.resolve(), args.benchpress_root.resolve()); receipt["verifier_sha256"] = sha256(Path(__file__).resolve()); args.receipt.parent.mkdir(parents=True, exist_ok=True); args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"); print(json.dumps(receipt, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
