"""Freeze and run paired Windows RAPL CPU-package energy telemetry."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments/e37_energy_cost_telemetry_protocol.json"
OUTPUT = ROOT / "data/v11/e37_energy_cost_telemetry"
E32_PAYLOAD = ROOT / "data/v11/e32_telemetry/cells/e32-f67a12cec7bbe23193cf0f0d.payload.json"
E32_WORKER = ROOT / "experiments/e32_telemetry_worker.py"
COUNTER = r"\Energy Meter(RAPL_Package0_PKG)\Energy"
ORDER = ("idle_then_workload", "workload_then_idle", "idle_then_workload", "workload_then_idle", "idle_then_workload")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cny_cost(energy_joules: float, rate_cny_per_kwh: float) -> float:
    return energy_joules / 3_600_000.0 * rate_cny_per_kwh


def read_energy_raw() -> int:
    command = f"(Get-Counter '{COUNTER}').CounterSamples[0].RawValue"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], capture_output=True, text=True, check=True)
    return int(result.stdout.strip())


def freeze(path: Path) -> dict[str, object]:
    before = read_energy_raw(); time.sleep(0.25); after = read_energy_raw()
    if after <= before:
        raise ValueError("Windows Energy Meter is absent or non-monotonic")
    payload = {
        "schema_version": "1.0.0", "experiment_id": "E37_WINDOWS_RAPL_ENERGY_V1", "design_status": "FROZEN_BEFORE_EXECUTION", "freeze_date": "2026-08-31",
        "research_question": "What gross CPU-package energy and idle-adjusted CPU-package energy are observed for one fixed exact-verified optimizer workload on this host?",
        "meter": {"provider": "Windows Energy Meter / Intel RAPL", "counter": COUNTER, "raw_unit": "nanojoule", "primary_domain": "RAPL_Package0_PKG", "unit_evidence": "Windows EMI absolute energy is converted to nanojoules by Chromium EnergyMetricsProviderWin", "counter_preflight_delta_positive": True},
        "workload": {"worker": str(E32_WORKER.relative_to(ROOT)).replace("\\", "/"), "worker_sha256": sha256(E32_WORKER), "payload": str(E32_PAYLOAD.relative_to(ROOT)).replace("\\", "/"), "payload_sha256": sha256(E32_PAYLOAD), "expected_status": "success", "description": "frozen E32 Grover-8 LBL COMMUTATION_PLUS_TEMPLATES exact-verified cell"},
        "design": {"paired_blocks": 5, "order": list(ORDER), "idle_seconds": 6.0, "cold_process_each_workload": True, "single_worker": True},
        "estimands": {"gross_package_joules": "RAPL package counter delta during the cold workload process", "idle_package_watts": "RAPL package counter delta divided by measured idle wall time", "idle_adjusted_package_joules": "gross workload joules minus paired idle watts times workload wall time, floored at zero"},
        "cost_sensitivity_rates_cny_per_kwh": [0.5, 0.6, 1.0],
        "failure_semantics": "all five paired blocks retained; non-monotonic counter, workload error, missing receipt, or meter error makes the formal panel incomplete; no imputation",
        "claim_boundary": "Direct system-wide CPU-package RAPL evidence on this host, not process-exclusive energy, DRAM/display/storage/whole-wall energy, carbon emissions, cloud billing, or cross-machine generalization. Cost values are tariff scenarios, not an actual bill.",
        "source_sha256": {"experiments/e37_energy_cost_telemetry.py": sha256(Path(__file__).resolve()), "scripts/verify_e37_energy_cost_telemetry.py": sha256(ROOT / "scripts/verify_e37_energy_cost_telemetry.py")},
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"); return payload


def phase_idle(seconds: float) -> dict[str, object]:
    before = read_energy_raw(); started = time.perf_counter(); time.sleep(seconds); wall = time.perf_counter() - started; after = read_energy_raw()
    return {"raw_before": before, "raw_after": after, "wall_seconds": wall, "energy_joules": (after - before) / 1e9}


def phase_workload(block: int, output_dir: Path) -> dict[str, object]:
    result_path = output_dir / "workload_receipts" / f"block_{block:02d}.json"; result_path.parent.mkdir(parents=True, exist_ok=True)
    before = read_energy_raw(); started = time.perf_counter()
    completed = subprocess.run([sys.executable, str(E32_WORKER), "--payload", str(E32_PAYLOAD), "--result", str(result_path)], cwd=ROOT, capture_output=True, text=True, timeout=120, check=False)
    wall = time.perf_counter() - started; after = read_energy_raw()
    receipt = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
    status = "success" if completed.returncode == 0 and receipt.get("status") == "success" else "error"
    return {"status": status, "returncode": completed.returncode, "raw_before": before, "raw_after": after, "wall_seconds": wall, "energy_joules": (after - before) / 1e9, "receipt_path": str(result_path.relative_to(ROOT)).replace("\\", "/"), "receipt_sha256": sha256(result_path) if result_path.is_file() else None, "stderr_tail": completed.stderr[-2000:]}


def formal(protocol_path: Path, output_dir: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("design_status") != "FROZEN_BEFORE_EXECUTION" or protocol["source_sha256"]["experiments/e37_energy_cost_telemetry.py"] != sha256(Path(__file__).resolve()) or protocol["workload"]["payload_sha256"] != sha256(E32_PAYLOAD):
        raise ValueError("E37 protocol/source/workload binding failed")
    output_dir.mkdir(parents=True, exist_ok=True); rows = []
    for block, order in enumerate(protocol["design"]["order"]):
        if order == "idle_then_workload":
            idle = phase_idle(float(protocol["design"]["idle_seconds"])); workload = phase_workload(block, output_dir)
        else:
            workload = phase_workload(block, output_dir); idle = phase_idle(float(protocol["design"]["idle_seconds"]))
        if idle["energy_joules"] <= 0 or workload["energy_joules"] <= 0 or workload["status"] != "success":
            raise RuntimeError(f"E37 block {block} failed closed")
        idle_watts = float(idle["energy_joules"]) / float(idle["wall_seconds"]); adjusted = max(0.0, float(workload["energy_joules"]) - idle_watts * float(workload["wall_seconds"]))
        row = {"block": block, "order": order, "idle_raw_before": idle["raw_before"], "idle_raw_after": idle["raw_after"], "idle_wall_seconds": idle["wall_seconds"], "idle_package_joules": idle["energy_joules"], "idle_package_watts": idle_watts, "workload_raw_before": workload["raw_before"], "workload_raw_after": workload["raw_after"], "workload_wall_seconds": workload["wall_seconds"], "gross_package_joules": workload["energy_joules"], "idle_adjusted_package_joules": adjusted, "workload_receipt_path": workload["receipt_path"], "workload_receipt_sha256": workload["receipt_sha256"]}
        rows.append(row); print(f"[{len(rows)}/5] gross={row['gross_package_joules']:.3f}J adjusted={adjusted:.3f}J", flush=True)
    fields = list(rows[0]); results_path = output_dir / "results.csv"
    with results_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    rates = protocol["cost_sensitivity_rates_cny_per_kwh"]; gross = [row["gross_package_joules"] for row in rows]; adjusted = [row["idle_adjusted_package_joules"] for row in rows]
    summary = {"schema_version": "1.0.0", "status": "FORMAL_PAIRED_ENERGY_PANEL_COMPLETE", "protocol_sha256": sha256(protocol_path), "paired_blocks": 5, "gross_package_joules_median": float(np.median(gross)), "gross_package_joules_range": [min(gross), max(gross)], "idle_adjusted_package_joules_median": float(np.median(adjusted)), "idle_adjusted_package_joules_range": [min(adjusted), max(adjusted)], "cost_sensitivity_cny_per_run": [{"rate_cny_per_kwh": rate, "gross_median_cny": cny_cost(float(np.median(gross)), rate), "idle_adjusted_median_cny": cny_cost(float(np.median(adjusted)), rate)} for rate in rates], "metric_dispositions": {"10.07": {"status": "PASS", "disposition": "Five paired blocks directly measure monotonic Windows RAPL CPU-package energy for the fixed optimizer workload, with gross and paired idle-adjusted joules; scope excludes whole-system and process-exclusive energy."}, "10.08": {"status": "PARTIAL", "disposition": "Measured package joules are converted across three declared CNY/kWh sensitivity rates, but no actual tariff/bill, hardware amortization, cloud fee, or whole-system energy is available."}}, "claim_boundary": protocol["claim_boundary"], "environment": {"python": sys.version, "executable": str(Path(sys.executable).resolve()), "platform": platform.platform()}}
    summary_path = output_dir / "summary.json"; summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    artifacts = [protocol_path, Path(__file__).resolve(), ROOT / "scripts/verify_e37_energy_cost_telemetry.py", results_path, summary_path] + sorted((output_dir / "workload_receipts").glob("*.json"))
    manifest = {"schema_version": "1.0.0", "artifact_count": len(artifacts), "artifacts": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in artifacts]}; (output_dir / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"); return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--protocol", type=Path, default=PROTOCOL); parser.add_argument("--output-dir", type=Path, default=OUTPUT); parser.add_argument("--freeze", action="store_true"); parser.add_argument("--formal", action="store_true"); args = parser.parse_args()
    if args.freeze:
        print(json.dumps(freeze(args.protocol.resolve()), indent=2, sort_keys=True)); return 0
    if not args.formal:
        raise SystemExit("choose --freeze or --formal")
    summary = formal(args.protocol.resolve(), args.output_dir.resolve()); print(json.dumps({"status": summary["status"], "gross_median_j": summary["gross_package_joules_median"], "adjusted_median_j": summary["idle_adjusted_package_joules_median"]}, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
