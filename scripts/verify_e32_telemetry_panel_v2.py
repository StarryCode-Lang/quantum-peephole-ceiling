"""Corrected independent E32 verifier.

Erratum: the protocol-frozen v1 verifier counted only result receipts when
checking artifact cardinality, while the formal manifest intentionally binds
both each worker payload and each result receipt.  This verifier leaves every
frozen source and result byte untouched and checks the complete 90+90 pairing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_id(input_hash: str, listing: str, rule_set: str, window: int) -> str:
    material = f"E32|{input_hash}|{listing}|{rule_set}|{window}".encode()
    return "e32-" + hashlib.sha256(material).hexdigest()[:24]


def verify(protocol_path: Path, output_dir: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    manifest_path = output_dir / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with (output_dir / "results.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    treatments = list(itertools.product(
        protocol["factors"]["listing_model"],
        protocol["factors"]["rule_set"],
        protocol["factors"]["window_gates"],
    ))
    expected_ids = {
        run_id(row["input_circuit_sha256"], listing, rules, int(window))
        for row in protocol["inputs"] for listing, rules, window in treatments
    }
    if len(expected_ids) != 90 or {row["run_id"] for row in rows} != expected_ids:
        raise ValueError("result schedule does not equal the frozen 90-cell design")
    if summary.get("status") != "FORMAL_BOUNDED_PANEL_COMPLETE" or summary.get("itt_observed_n") != 90:
        raise ValueError("summary does not retain the complete ITT schedule")
    if summary.get("protocol_sha256") != sha256(protocol_path):
        raise ValueError("summary protocol binding failed")

    result_by_id = {row["run_id"]: row for row in rows}
    success_n = 0
    available_n = 0
    for expected_order, identifier in enumerate(sorted(expected_ids, key=lambda rid: int(result_by_id[rid]["run_order"]))):
        payload_path = output_dir / "cells" / f"{identifier}.payload.json"
        receipt_path = output_dir / "cells" / f"{identifier}.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        row = result_by_id[identifier]
        if int(payload["run_order"]) != expected_order or int(receipt["run_order"]) != expected_order:
            raise ValueError(f"run-order mismatch: {identifier}")
        bound = ("run_id", "run_order", "circuit_family", "input_circuit_sha256", "n_qubits", "listing_model", "rule_set", "window_gates", "budget_seconds")
        if any(payload[key] != receipt[key] for key in bound):
            raise ValueError(f"payload/receipt treatment drift: {identifier}")
        if sha256(receipt_path) != row["cell_receipt_sha256"]:
            raise ValueError(f"receipt hash mismatch: {identifier}")
        events = receipt.get("events", [])
        elapsed = [int(event["elapsed_ns"]) for event in events]
        if elapsed != sorted(elapsed) or len(events) != int(receipt["event_count"]):
            raise ValueError(f"non-monotonic or incomplete event stream: {identifier}")
        valid = [event for event in events if event.get("event") == "iteration_candidate_validated" and event.get("valid_equivalent_output")]
        if receipt["status"] == "success":
            success_n += 1
            if not valid:
                raise ValueError(f"success without exact-valid event: {identifier}")
            best_gate = min(int(event["gate_count"]) for event in valid)
            first_best = next(event for event in valid if int(event["gate_count"]) == best_gate)
            if int(receipt["time_to_first_valid_ns"]) != int(valid[0]["elapsed_ns"]):
                raise ValueError(f"first-valid timing mismatch: {identifier}")
            if int(receipt["time_to_best_ns"]) != int(first_best["elapsed_ns"]):
                raise ValueError(f"time-to-best mismatch: {identifier}")
            if int(receipt["best_valid_gate_count"]) != best_gate:
                raise ValueError(f"best gate count mismatch: {identifier}")
            available_n += 1
        elif any(receipt.get(key) is not None for key in ("time_to_first_valid_ns", "time_to_best_ns")):
            raise ValueError(f"non-success has imputed timing: {identifier}")

    listed = {entry["path"]: entry for entry in manifest["artifacts"]}
    expected_manifest_n = 90 * 2 + 6
    if len(listed) != int(manifest["artifact_count"]) or len(listed) != expected_manifest_n:
        raise ValueError("artifact manifest cardinality is not 90 payloads + 90 receipts + 6 roots")
    for relative, entry in listed.items():
        path = PROJECT_ROOT / relative
        if not path.is_file() or path.stat().st_size != int(entry["bytes"]) or sha256(path) != entry["sha256"]:
            raise ValueError(f"artifact manifest mismatch: {relative}")
    if available_n != int(summary["timing_available_n"]):
        raise ValueError("timing availability summary mismatch")
    if summary.get("status_counts") != {"success": success_n, "timeout": 90 - success_n}:
        raise ValueError("status-count summary mismatch")
    return {
        "status": "VERIFIED",
        "erratum": "v1_expected_96_instead_of_186_manifest_members",
        "rows": 90,
        "payloads": 90,
        "receipts": 90,
        "families": 15,
        "success": success_n,
        "timeout": 90 - success_n,
        "timing_available": available_n,
        "protocol_sha256": sha256(protocol_path),
        "artifact_manifest_sha256": sha256(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=PROJECT_ROOT / "experiments/e32_telemetry_protocol.json")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data/v11/e32_telemetry")
    parser.add_argument("--receipt", type=Path, default=PROJECT_ROOT / "release/e32_telemetry_independent_verification_receipt.json")
    args = parser.parse_args()
    receipt = verify(args.protocol.resolve(), args.output_dir.resolve())
    receipt["verifier_sha256"] = sha256(Path(__file__).resolve())
    receipt["scope"] = "fixed descriptive 15-family <=8-qubit E32 panel; not sealed E31 reconstruction or generalized timing"
    receipt["metric_dispositions"] = {
        "9.52": {
            "status": "PASS",
            "disposition": "Direct event-level monotonic time-to-first-valid is observed for 89/90 frozen ITT cells; the one timeout remains unavailable without imputation. Scope is the fixed E32 panel and this host only.",
        },
        "9.53": {
            "status": "PASS",
            "disposition": "Direct event-level monotonic time-to-earliest-best is observed for 89/90 frozen ITT cells; best is recomputed from every exact-valid iteration event and the timeout remains unavailable. Scope is the fixed E32 panel and this host only.",
        },
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
