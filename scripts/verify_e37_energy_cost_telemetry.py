"""Independently verify E37 counter arithmetic, receipts, and cost scenarios."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e37_energy_cost_telemetry import cny_cost


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(protocol_path: Path, output_dir: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8")); summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8")); manifest_path = output_dir / "artifact_manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with (output_dir / "results.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if summary.get("status") != "FORMAL_PAIRED_ENERGY_PANEL_COMPLETE" or summary.get("protocol_sha256") != sha256(protocol_path) or len(rows) != 5:
        raise ValueError("E37 incomplete or protocol-unbound")
    gross = []; adjusted = []
    for row in rows:
        idle_delta = int(row["idle_raw_after"]) - int(row["idle_raw_before"]); work_delta = int(row["workload_raw_after"]) - int(row["workload_raw_before"])
        if idle_delta <= 0 or work_delta <= 0 or abs(float(row["idle_package_joules"]) - idle_delta / 1e9) > 1e-9 or abs(float(row["gross_package_joules"]) - work_delta / 1e9) > 1e-9:
            raise ValueError("E37 counter arithmetic mismatch")
        expected = max(0.0, work_delta / 1e9 - (idle_delta / 1e9 / float(row["idle_wall_seconds"])) * float(row["workload_wall_seconds"]))
        if abs(float(row["idle_adjusted_package_joules"]) - expected) > 1e-9:
            raise ValueError("E37 idle adjustment mismatch")
        receipt_path = ROOT / row["workload_receipt_path"]
        if sha256(receipt_path) != row["workload_receipt_sha256"] or json.loads(receipt_path.read_text(encoding="utf-8")).get("status") != "success":
            raise ValueError("E37 workload receipt mismatch")
        gross.append(float(row["gross_package_joules"])); adjusted.append(float(row["idle_adjusted_package_joules"]))
    for item in summary["cost_sensitivity_cny_per_run"]:
        rate = float(item["rate_cny_per_kwh"])
        import statistics
        if abs(float(item["gross_median_cny"]) - cny_cost(statistics.median(gross), rate)) > 1e-15 or abs(float(item["idle_adjusted_median_cny"]) - cny_cost(statistics.median(adjusted), rate)) > 1e-15:
            raise ValueError("E37 cost sensitivity arithmetic mismatch")
    listed = {entry["path"]: entry for entry in manifest["artifacts"]}
    if len(listed) != int(manifest["artifact_count"]) or len(listed) != 10:
        raise ValueError("E37 manifest cardinality mismatch")
    for relative, entry in listed.items():
        path = ROOT / relative
        if path.stat().st_size != int(entry["bytes"]) or sha256(path) != entry["sha256"]:
            raise ValueError(f"E37 artifact mismatch: {relative}")
    return {"status": "VERIFIED", "paired_blocks": 5, "protocol_sha256": sha256(protocol_path), "artifact_manifest_sha256": sha256(manifest_path), "metric_dispositions": summary["metric_dispositions"], "gross_package_joules_median": summary["gross_package_joules_median"], "idle_adjusted_package_joules_median": summary["idle_adjusted_package_joules_median"], "claim_boundary": summary["claim_boundary"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--protocol", type=Path, default=ROOT / "experiments/e37_energy_cost_telemetry_protocol.json"); parser.add_argument("--output-dir", type=Path, default=ROOT / "data/v11/e37_energy_cost_telemetry"); parser.add_argument("--receipt", type=Path, default=ROOT / "release/e37_energy_cost_independent_verification_receipt.json"); args = parser.parse_args()
    receipt = verify(args.protocol.resolve(), args.output_dir.resolve()); receipt["verifier_sha256"] = sha256(Path(__file__).resolve()); args.receipt.parent.mkdir(parents=True, exist_ok=True); args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"); print(json.dumps(receipt, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
