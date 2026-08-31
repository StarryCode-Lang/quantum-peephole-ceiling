"""Execute the frozen external >10-qubit E33 robustness panel."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pyzx
from qiskit import qasm2, transpile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor
from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher

PROTOCOL = ROOT / "experiments/e33_real_scale_protocol.json"
OUTPUT = ROOT / "data/v11/e33_real_scale"
SOURCES = {
    "experiments/e33_real_scale_panel.py": Path(__file__).resolve(),
    "scripts/freeze_e33_real_scale_protocol.py": ROOT / "scripts/freeze_e33_real_scale_protocol.py",
    "scripts/verify_e33_real_scale_panel.py": ROOT / "scripts/verify_e33_real_scale_panel.py",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_id(input_hash: str, listing: str) -> str:
    return "e33-" + hashlib.sha256(f"E33|{input_hash}|{listing}".encode()).hexdigest()[:24]


def load_protocol(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    if protocol.get("design_status") != "FROZEN_BEFORE_EXECUTION":
        raise ValueError("E33 protocol is not frozen")
    if set(protocol.get("source_sha256", {})) != set(SOURCES):
        raise ValueError("E33 source closure mismatch")
    for relative, source in SOURCES.items():
        if sha256(source) != protocol["source_sha256"][relative]:
            raise ValueError(f"E33 source drift: {relative}")
    inputs = protocol.get("inputs", [])
    if len(inputs) != 11 or sorted({int(row["n_qubits"]) for row in inputs})[0] <= 10:
        raise ValueError("E33 requires 11 unique inputs, all beyond 10 qubits")
    schedule = []
    for source in inputs:
        path_value = (ROOT / source["qasm_path"]).resolve()
        if not path_value.is_relative_to(ROOT) or sha256(path_value) != source["qasm_file_sha256"]:
            raise ValueError(f"E33 input drift: {path_value}")
        for listing in protocol["factors"]["listing_model"]:
            schedule.append({
                **source,
                "listing_model": listing,
                "run_id": run_id(source["input_circuit_sha256"], listing),
                "run_order": len(schedule),
            })
    if len(schedule) != 22 or len({row["run_id"] for row in schedule}) != 22:
        raise ValueError("E33 schedule must have 22 unique paired cells")
    return protocol, schedule


def _proof(left_qasm: str, right_qasm: str, *, mutate: bool = False) -> bool | None:
    left = pyzx.Circuit.from_qasm(left_qasm)
    right = pyzx.Circuit.from_qasm(right_qasm)
    if mutate:
        right.add_gate("NOT", 0)
    decision = left.verify_equality(right, up_to_swaps=False, up_to_global_phase=True)
    return True if decision is True else None


def _worker(row: dict[str, Any], protocol: dict[str, Any], result_path: str) -> None:
    started = time.perf_counter()
    try:
        original = qasm2.load(ROOT / row["qasm_path"], custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
        listed = original.copy() if row["listing_model"] == "LBL" else WireTraversalPreprocessor().preprocess(original)
        engine = Phase2bTemplateMatcher(
            max_iterations=int(protocol["optimizer_contract"]["max_iterations"]),
            gather_window=int(protocol["optimizer_contract"]["gather_window"]),
            template_enabled=True,
            collect_trace=True,
        )
        optimized = listed.copy()
        total = engine._zero_counters()
        trace = []
        for iteration in range(engine.max_iterations):
            counts = engine._zero_counters()
            engine._gather_h_sandwiches(optimized, counts)
            engine._gather_commuting_pairs(optimized, counts)
            engine._apply_all_templates(optimized, counts)
            engine._cancel_inverse_pairs(optimized, counts)
            engine._merge_phase_gates(optimized, counts)
            engine._accumulate(total, counts)
            trace.append({"iteration": iteration, "gate_count": int(optimized.size()), **{key: int(value) for key, value in counts.items()}})
            if engine._no_progress(counts):
                break
        basis = list(protocol["verification_contract"]["symbolic_basis"])
        left = transpile(original, basis_gates=basis, optimization_level=0)
        right = transpile(optimized, basis_gates=basis, optimization_level=0)
        left_qasm, right_qasm = qasm2.dumps(left), qasm2.dumps(right)
        proved = _proof(left_qasm, right_qasm)
        mutant = _proof(left_qasm, right_qasm, mutate=True)
        result = {
            "status": "success" if proved is True else "inconclusive",
            "proof_decision": proved,
            "mutant_proof_decision": mutant,
            "wall_seconds": time.perf_counter() - started,
            "input_gate_count": int(original.size()),
            "listed_gate_count": int(listed.size()),
            "optimized_gate_count": int(optimized.size()),
            "reduction_pct_itt": 100.0 * (1.0 - optimized.size() / original.size()) if proved is True and original.size() else 0.0,
            "rewrite_counts": {key: int(value) for key, value in total.items()},
            "trace": trace,
            "original_basis_qasm": left_qasm,
            "optimized_basis_qasm": right_qasm,
            "pyzx_version": pyzx.__version__,
        }
    except BaseException as exc:
        result = {"status": "error", "error": f"{type(exc).__name__}: {exc}", "wall_seconds": time.perf_counter() - started}
    Path(result_path).write_text(json.dumps(result, sort_keys=True), encoding="utf-8")


def execute_cell(row: dict[str, Any], protocol: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    context = mp.get_context("spawn")
    worker_result_path = output_dir / "worker_results" / f"{row['run_id']}.json"
    worker_result_path.parent.mkdir(parents=True, exist_ok=True)
    process = context.Process(target=_worker, args=(row, protocol, str(worker_result_path)))
    process.start()
    timeout = float(protocol["resource_contract"]["cell_timeout_seconds"])
    process.join(timeout)
    if process.is_alive():
        process.terminate(); process.join(5)
        result: dict[str, Any] = {"status": "timeout", "wall_seconds": timeout}
    else:
        if worker_result_path.is_file():
            result = json.loads(worker_result_path.read_text(encoding="utf-8"))
            worker_result_path.unlink()
        else:
            result = {"status": "error", "error": f"worker exit {process.exitcode} without result"}
    original_qasm = result.pop("original_basis_qasm", None)
    optimized_qasm = result.pop("optimized_basis_qasm", None)
    if original_qasm is not None and optimized_qasm is not None:
        original_path = output_dir / "qasm" / f"{row['run_id']}.original.qasm"
        optimized_path = output_dir / "qasm" / f"{row['run_id']}.optimized.qasm"
        original_path.parent.mkdir(parents=True, exist_ok=True)
        original_path.write_text(original_qasm, encoding="utf-8", newline="\n")
        optimized_path.write_text(optimized_qasm, encoding="utf-8", newline="\n")
        result.update({
            "original_basis_qasm_path": str(original_path.relative_to(ROOT)).replace("\\", "/"),
            "original_basis_qasm_sha256": sha256(original_path),
            "optimized_basis_qasm_path": str(optimized_path.relative_to(ROOT)).replace("\\", "/"),
            "optimized_basis_qasm_sha256": sha256(optimized_path),
        })
    receipt = {"schema_version": "1.0.0", **row, **result}
    receipt_path = output_dir / "cells" / f"{row['run_id']}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--formal", action="store_true")
    args = parser.parse_args()
    protocol, schedule = load_protocol(args.protocol.resolve())
    if not args.formal:
        print(json.dumps({"status": "DRY_RUN_ONLY", "cells": len(schedule), "protocol_sha256": sha256(args.protocol)}, indent=2))
        return 0
    output_dir = args.output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    receipts = []
    for row in schedule:
        receipt = execute_cell(row, protocol, output_dir)
        receipts.append(receipt)
        print(f"[{len(receipts):02d}/{len(schedule)}] {row['run_id']} {receipt['status']}", flush=True)
    columns = ["run_id", "run_order", "benchmark_id", "benchmark_class", "n_qubits", "listing_model", "status", "proof_decision", "mutant_proof_decision", "input_gate_count", "optimized_gate_count", "reduction_pct_itt", "wall_seconds", "qasm_file_sha256"]
    with (output_dir / "results.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n"); writer.writeheader(); writer.writerows({key: row.get(key) for key in columns} for row in receipts)
    valid = [row for row in receipts if row["status"] == "success"]
    paired = []
    for source in protocol["inputs"]:
        pair = [row for row in receipts if row["input_circuit_sha256"] == source["input_circuit_sha256"]]
        by_listing = {row["listing_model"]: float(row.get("reduction_pct_itt", 0.0)) for row in pair}
        paired.append({"benchmark_id": source["benchmark_id"], "n_qubits": source["n_qubits"], "wcl_minus_lbl_reduction_pp_itt": by_listing.get("WCL", 0.0) - by_listing.get("LBL", 0.0)})
    summary = {
        "schema_version": "1.0.0", "status": "FORMAL_BOUNDED_PANEL_COMPLETE" if len(receipts) == 22 else "INCOMPLETE",
        "protocol_sha256": sha256(args.protocol.resolve()), "itt_scheduled_n": 22, "itt_observed_n": len(receipts),
        "status_counts": dict(sorted(Counter(row["status"] for row in receipts).items())),
        "proved_equal_n": len(valid), "mutants_proved_equal_n": sum(row.get("mutant_proof_decision") is True for row in receipts),
        "width_range": [min(row["n_qubits"] for row in receipts), max(row["n_qubits"] for row in receipts)],
        "paired_estimand": "finite-panel mean WCL-minus-LBL gate-reduction percentage points with nonvalid cells assigned zero under ITT",
        "paired_effect_mean_pp": sum(row["wcl_minus_lbl_reduction_pp_itt"] for row in paired) / len(paired),
        "paired_effects": paired,
        "claim_boundary": protocol["claim_boundary"],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    artifacts = [args.protocol.resolve(), Path(__file__).resolve(), output_dir / "results.csv", output_dir / "summary.json"] + sorted((output_dir / "cells").glob("*.json")) + sorted((output_dir / "qasm").glob("*.qasm"))
    manifest = {"schema_version": "1.0.0", "artifacts": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in artifacts]}
    manifest["artifact_count"] = len(manifest["artifacts"])
    (output_dir / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": summary["status"], "proved_equal": len(valid), "artifact_count": manifest["artifact_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
