"""Independently verify E32 schedule, event receipts, summaries, and hashes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(protocol_path: Path, output_dir: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "artifact_manifest.json").read_text(encoding="utf-8"))
    with (output_dir / "results.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = 15 * 3 * 2
    if len(rows) != expected or len({row["run_id"] for row in rows}) != expected:
        raise ValueError("E32 result rows are incomplete or duplicated")
    if summary.get("status") != "FORMAL_BOUNDED_PANEL_COMPLETE" or summary.get("itt_observed_n") != expected:
        raise ValueError("E32 summary is not complete")
    if summary.get("protocol_sha256") != sha256(protocol_path):
        raise ValueError("E32 summary protocol binding failed")
    for row in rows:
        receipt_path = output_dir / "cells" / f"{row['run_id']}.json"
        if sha256(receipt_path) != row["cell_receipt_sha256"]:
            raise ValueError(f"receipt hash mismatch: {receipt_path}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        events = receipt.get("events", [])
        elapsed = [int(event["elapsed_ns"]) for event in events]
        if elapsed != sorted(elapsed) or len(events) != int(receipt["event_count"]):
            raise ValueError(f"non-monotonic or incomplete event stream: {receipt_path}")
        valid = [event for event in events if event.get("event") == "iteration_candidate_validated" and event.get("valid_equivalent_output")]
        if receipt["status"] == "success":
            if not valid:
                raise ValueError(f"success without exact-valid event: {receipt_path}")
            best_gate = min(int(event["gate_count"]) for event in valid)
            first_best = next(event for event in valid if int(event["gate_count"]) == best_gate)
            if int(receipt["time_to_first_valid_ns"]) != int(valid[0]["elapsed_ns"]):
                raise ValueError(f"first-valid timing mismatch: {receipt_path}")
            if int(receipt["time_to_best_ns"]) != int(first_best["elapsed_ns"]):
                raise ValueError(f"best timing mismatch: {receipt_path}")
            if int(receipt["best_valid_gate_count"]) != best_gate:
                raise ValueError(f"best gate count mismatch: {receipt_path}")
        elif any(receipt.get(key) is not None for key in ("time_to_first_valid_ns", "time_to_best_ns")):
            raise ValueError(f"non-success has imputed timing: {receipt_path}")
    listed = {entry["path"]: entry for entry in manifest["artifacts"]}
    if len(listed) != int(manifest["artifact_count"]) or len(listed) != expected + 6:
        raise ValueError("artifact manifest cardinality mismatch")
    for relative, entry in listed.items():
        path = PROJECT_ROOT / relative
        if not path.is_file() or path.stat().st_size != int(entry["bytes"]) or sha256(path) != entry["sha256"]:
            raise ValueError(f"artifact manifest mismatch: {relative}")
    first_available = sum(row["time_to_first_valid_seconds"] not in ("", None) for row in rows)
    best_available = sum(row["time_to_best_seconds"] not in ("", None) for row in rows)
    if first_available != int(summary["timing_available_n"]) or first_available != best_available:
        raise ValueError("summary timing counts disagree with result rows")
    return {"status": "VERIFIED", "rows": len(rows), "families": len({row["circuit_family"] for row in rows}), "timing_available": first_available, "protocol_sha256": sha256(protocol_path), "artifact_manifest_sha256": sha256(output_dir / "artifact_manifest.json")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=PROJECT_ROOT / "experiments/e32_telemetry_protocol.json")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data/v11/e32_telemetry")
    args = parser.parse_args()
    print(json.dumps(verify(args.protocol.resolve(), args.output_dir.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
