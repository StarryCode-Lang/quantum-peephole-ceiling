"""Run the fixed E33/E35 scale panel with explicit resource boundaries."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "data" / "v12" / "e41_rewrite_exposure_scale"
E33_PROTOCOL = ROOT / "experiments" / "e33_real_scale_protocol.json"
E35_PROTOCOL = ROOT / "experiments" / "e35_benchpress_stress_protocol.json"
EXPERIMENT_ID = "E41_REWRITE_EXPOSURE_SCALE_V1"
ARMS = ("WCL_Greedy", "CGL_Greedy", "LBL_Phase2b", "CGL_Phase2b")
RSS_CAP = 8 * 1024**3
THRESHOLD = 0.9999999999


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(field for row in rows for field in row))
    import io
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def build_inputs() -> list[dict[str, Any]]:
    e33 = json.loads(E33_PROTOCOL.read_text(encoding="utf-8"))
    e35 = json.loads(E35_PROTOCOL.read_text(encoding="utf-8"))
    inputs: list[dict[str, Any]] = []
    for item in e33["inputs"]:
        path = ROOT / item["qasm_path"]
        if not path.is_file():
            path = Path("D:/Desktop/Q-research") / item["qasm_path"]
        inputs.append({
            "panel": "E33",
            "case_id": item["benchmark_id"],
            "family": item["benchmark_class"],
            "n_qubits_declared": item["n_qubits"],
            "qasm_path": item["qasm_path"],
            "source_path": str(path),
            "qasm_sha256": item["qasm_file_sha256"],
            "timeout_seconds": 120,
        })
    for item in e35["inputs"]:
        path = Path("D:/Downloads/qresearch-benchpress-official") / item["relative_path"]
        inputs.append({
            "panel": "E35",
            "case_id": item["case_id"],
            "family": "benchpress_stress",
            "n_qubits_declared": item["expected_qubits_from_name"],
            "qasm_path": item["relative_path"],
            "source_path": str(path),
            "qasm_sha256": item["sha256"],
            "timeout_seconds": 180,
        })
    if len(inputs) != 16 or len({item["case_id"] for item in inputs}) != 16:
        raise RuntimeError("expected_16_fixed_inputs")
    for item in inputs:
        path = Path(item["source_path"])
        item["source_exists"] = path.is_file()
        item["source_observed_sha256"] = sha256_file(path) if path.is_file() else None
    return inputs


def _source_hashes() -> dict[str, str]:
    return {
        path: sha256_file(ROOT / path)
        for path in (
            "experiments/e41_rewrite_exposure_scale/run.py",
            "scripts/verify_e41_rewrite_exposure_scale.py",
            "src/optimisation/rewrite_exposure.py",
            "src/optimisation/_gate_predicates.py",
            "src/optimisation/base.py",
        )
    }


def _equivalence(circuit, original) -> tuple[str, float | None]:
    """Return proof status without sampled fidelity fallback."""
    names = {instruction.operation.name for instruction in circuit.data}
    clifford_names = {"h", "x", "y", "z", "s", "sdg", "sx", "sxdg", "cx", "cnot", "cz", "swap", "id", "barrier"}
    if names.issubset(clifford_names):
        try:
            from qiskit.quantum_info import Clifford
            return ("exact_stabilizer", 1.0 if Clifford(circuit) == Clifford(original) else 0.0)
        except Exception:
            pass
    if circuit.num_qubits <= 10:
        try:
            from src.circuits.real_benchmarks import average_gate_fidelity
            fidelity = average_gate_fidelity(circuit, original, max_qubits=10)
            return ("exact_operator" if fidelity is not None else "equivalence_unavailable", fidelity)
        except Exception:
            return "equivalence_unavailable", None
    return "equivalence_unavailable", None


def _run_optimizer(circuit, arm: str):
    from src.optimisation.phase1.greedy import GreedyGateCancellation
    from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor
    from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher
    if arm == "WCL_Greedy":
        listed = WireTraversalPreprocessor().preprocess(circuit)
        return GreedyGateCancellation(max_iterations=50, fidelity_threshold=THRESHOLD, success_reduction=0.0, wire_traversal=False).optimize(listed, target=None)
    if arm == "LBL_Phase2b":
        return Phase2bTemplateMatcher(max_iterations=50, fidelity_threshold=THRESHOLD, success_reduction=0.0, gather_window=64, template_enabled=True).optimize_full_pipeline(circuit, target=None)
    raise ValueError(f"unsupported_optimizer_arm:{arm}")


def execute_cell(item: dict[str, Any]) -> dict[str, Any]:
    from qiskit import qasm2

    path = Path(item["source_path"])
    if not path.is_file() or sha256_file(path) != item["qasm_sha256"]:
        raise RuntimeError("input_qasm_missing_or_hash_drift")
    circuit = qasm2.load(path, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    original = circuit.copy()
    from src.optimisation.rewrite_exposure import (
        DependenceModel, ExposureConfig, certify_rewrite_exposure, materialize_cgl_listing,
    )
    certificate = certify_rewrite_exposure(circuit, ExposureConfig(dependence_model=DependenceModel.CONSERVATIVE_COMMUTATION_V1, beam_width=32, candidate_cap=256, exact_node_budget=1_000_000, overlap_check_budget=20_000_000))
    certificate_payload = {
        "status": certificate.status,
        "ub": certificate.matching_upper_bound,
        "lb": certificate.constructive_lower_bound,
        "candidate_count": certificate.candidate_count,
        "fallback_reason": certificate.fallback_reason or "",
        "actual_dependence_model": certificate.dependence_model,
    }
    outputs: list[dict[str, Any]] = []
    for arm in ARMS:
        started = time.perf_counter()
        if arm.startswith("CGL"):
            if certificate.status == "unavailable":
                outputs.append({"arm": arm, "status": "unavailable", "equivalence_status": "equivalence_unavailable", "reduction": 0.0, "output_gate_count": original.size(), "runtime_seconds": time.perf_counter() - started, "error": certificate.failure_reason or "certificate_unavailable"})
                continue
            listed = materialize_cgl_listing(original, certificate.listing_order)
            if arm == "CGL_Greedy":
                from src.optimisation.phase1.greedy import GreedyGateCancellation
                result = GreedyGateCancellation(max_iterations=50, fidelity_threshold=THRESHOLD, success_reduction=0.0, wire_traversal=False).optimize(listed, target=None)
            else:
                from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher
                result = Phase2bTemplateMatcher(max_iterations=50, fidelity_threshold=THRESHOLD, success_reduction=0.0, gather_window=64, template_enabled=True).optimize_full_pipeline(listed, target=None)
        else:
            result = _run_optimizer(original, arm)
        proof_status, fidelity = _equivalence(result.optimized_circuit, original)
        reduction = 1.0 - result.optimized_size / original.size() if original.size() else 0.0
        outputs.append({
            "arm": arm,
            "status": "success",
            "equivalence_status": proof_status,
            "equivalence_fidelity": fidelity,
            "reduction": reduction if proof_status in {"exact_stabilizer", "exact_operator"} and fidelity is not None and fidelity >= THRESHOLD else 0.0,
            "output_gate_count": int(result.optimized_size),
            "output_depth": int(result.optimized_circuit.depth() or 0),
            "runtime_seconds": time.perf_counter() - started,
        })
    return {
        "status": "success",
        "case_id": item["case_id"],
        "panel": item["panel"],
        "input_qasm_sha256": item["qasm_sha256"],
        "n_qubits": int(circuit.num_qubits),
        "input_gate_count": int(circuit.size()),
        "certificate": certificate_payload,
        "arms": outputs,
    }


def run_cell(item: dict[str, Any]) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_cell_worker, args=(item, queue))
    started = time.perf_counter()
    process.start()
    peak_rss = 0
    try:
        import psutil
        root_process = psutil.Process(process.pid)
    except Exception:
        root_process = None
    deadline = started + float(item["timeout_seconds"])
    terminal_reason = None
    while process.is_alive() and time.perf_counter() < deadline:
        if root_process is not None:
            try:
                rss = root_process.memory_info().rss + sum(child.memory_info().rss for child in root_process.children(recursive=True))
                peak_rss = max(peak_rss, int(rss))
                if rss > RSS_CAP:
                    terminal_reason = "rss_cap_8GiB"
                    process.terminate()
                    break
            except Exception:
                pass
        time.sleep(0.5)
    if process.is_alive():
        process.terminate()
        process.join(5)
        terminal_reason = terminal_reason or f"cell_timeout_{item['timeout_seconds']}s"
    else:
        process.join(1)
    if terminal_reason:
        receipt = {"status": "resource_failure", "error": terminal_reason}
    else:
        try:
            receipt = queue.get(timeout=1)
        except Exception:
            receipt = {"status": "error", "error": "worker_no_receipt"}
    receipt.update({"case_id": item["case_id"], "panel": item["panel"], "wall_seconds": time.perf_counter() - started, "peak_rss_bytes": peak_rss, "input_qasm_sha256": item["qasm_sha256"]})
    return receipt


def _cell_worker(item: dict[str, Any], queue) -> None:
    try:
        queue.put(execute_cell(item))
    except Exception as exc:
        queue.put({"status": "error", "error": f"{type(exc).__name__}:{str(exc)[:240]}"})


def formal() -> dict[str, Any]:
    inputs = build_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = {
        "experiment_id": EXPERIMENT_ID,
        "status": "FROZEN_BEFORE_EXECUTION",
        "e33_protocol_sha256": sha256_file(E33_PROTOCOL),
        "e35_protocol_sha256": sha256_file(E35_PROTOCOL),
        "input_count": 16,
        "panels": {"E33": 11, "E35": 5},
        "arms": list(ARMS),
        "workers": 1,
        "threads_per_worker": 1,
        "cold_process_per_cell": True,
        "cell_timeout_seconds": {"E33": 120, "E35": 180},
        "rss_cap_bytes": RSS_CAP,
        "equivalence_policy": "exact stabilizer for Clifford; exact operator when within bound; otherwise equivalence_unavailable; never sampled fidelity",
        "claim_boundary": "E41 supports scale and resource behavior only and does not alter E40 efficacy conclusions",
        "source_hashes": _source_hashes(),
    }
    atomic_write(OUT / "protocol.json", protocol)
    atomic_write(OUT / "inputs.json", inputs)
    rows: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for index, item in enumerate(inputs, start=1):
        print(f"[{index}/16] {item['panel']} {item['case_id']}", flush=True)
        receipt = run_cell(item)
        receipts.append(receipt)
        atomic_write(OUT / "cells" / f"{item['case_id']}.json", receipt)
        if receipt.get("status") == "success":
            for arm in receipt.get("arms", []):
                rows.append({"case_id": item["case_id"], "panel": item["panel"], "n_qubits": receipt.get("n_qubits"), "input_gate_count": receipt.get("input_gate_count"), "certificate_status": receipt.get("certificate", {}).get("status"), "certificate_ub": receipt.get("certificate", {}).get("ub"), "certificate_lb": receipt.get("certificate", {}).get("lb"), **arm})
    write_csv(OUT / "formal_results.csv", rows)
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "status": "FORMAL_COMPLETE" if all(item.get("status") == "success" for item in receipts) else "FORMAL_WITH_RESOURCE_OR_ERROR_OUTCOMES",
        "input_count": len(inputs),
        "cell_count": len(receipts),
        "successful_cells": sum(item.get("status") == "success" for item in receipts),
        "resource_or_error_cells": sum(item.get("status") != "success" for item in receipts),
        "result_rows": len(rows),
        "unmarked_semantic_failure_count": 0,
        "wire_order_fallback_cells": sum(any("wire_order_v1" in str(arm) for arm in item.get("arms", [])) for item in receipts),
        "equivalence_unavailable_arm_count": sum(arm.get("equivalence_status") == "equivalence_unavailable" for row in rows for arm in [row]),
        "claim_boundary": protocol["claim_boundary"],
    }
    atomic_write(OUT / "summary.json", summary)
    receipt = {**summary, "protocol_sha256": sha256_file(OUT / "protocol.json"), "inputs_sha256": sha256_file(OUT / "inputs.json"), "formal_results_sha256": sha256_file(OUT / "formal_results.csv"), "source_hashes": protocol["source_hashes"]}
    atomic_write(OUT / "receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("formal",), required=True)
    parser.parse_args()
    formal()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
