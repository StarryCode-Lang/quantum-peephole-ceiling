"""Freeze and run a bounded Benchpress-derived large-circuit stress panel."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import psutil
from qiskit import qasm2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_BENCHPRESS = Path("D:/Downloads/qresearch-benchpress-official")
PROTOCOL = ROOT / "experiments/e35_benchpress_stress_protocol.json"
OUTPUT = ROOT / "data/v11/e35_benchpress_stress"
SELECTED = (
    ("benchpress/qasm/qasmbench-medium/factor247_n15/factor247_n15.qasm", "medium", 15),
    ("benchpress/qasm/qasmbench-large/vqe_uccsd_n28/vqe_uccsd_n28.qasm", "large", 28),
    ("benchpress/qasm/qasmbench-large/bwt_n37/bwt_n37_transpiled.qasm", "large", 37),
    ("benchpress/qasm/qasmbench-large/qft_n320/qft_n320.qasm", "large", 320),
    ("benchpress/qasm/qasmbench-large/multiplier_n400/multiplier_n400_transpiled.qasm", "large", 400),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def freeze(path: Path, benchpress_root: Path) -> dict[str, object]:
    commit = git_value(benchpress_root, "rev-parse", "HEAD")
    if commit != "b695f30e83a32bac05b9b4d8e98d37ba9aae5236" or git_value(benchpress_root, "status", "--short"):
        raise ValueError("Benchpress source is not the frozen clean commit")
    inputs = []
    for relative, tier, expected_qubits in SELECTED:
        source = benchpress_root / relative
        inputs.append({"case_id": source.stem, "relative_path": relative, "tier": tier, "expected_qubits_from_name": expected_qubits, "bytes": source.stat().st_size, "sha256": sha256(source)})
    payload = {
        "schema_version": "1.0.0", "experiment_id": "E35_BENCHPRESS_STRESS_V1", "design_status": "FROZEN_BEFORE_EXECUTION", "freeze_date": "2026-08-31",
        "research_question": "Can the project parser, WCL preprocessing, and one bounded Phase-2b rewrite iteration process a fixed multi-tier subset of official Benchpress QASM workloads under explicit time and memory failure semantics?",
        "source": {"repository": "https://github.com/Qiskit/benchpress", "commit": commit, "license": "Apache-2.0", "license_sha256": sha256(benchpress_root / "LICENSE.txt")},
        "selection_rule": "five named files fixed before execution: one medium and four large QASMBench workloads spanning filename-declared widths 15, 28, 37, 320, and 400; no outcome-dependent replacement",
        "inputs": inputs,
        "workload": ["SHA-256 stream", "QASM2 parse", "gate/depth characterization", "WCL preprocessing", "one Phase-2b commutation-plus-template iteration"],
        "resource_contract": {"cell_timeout_seconds": 180.0, "rss_cap_bytes": 8589934592, "workers": 1, "threads_per_worker": 1, "cold_process_per_cell": True},
        "estimand": "descriptive completion/status, peak process-tree RSS, elapsed time, parsed width/gates/depth, and one-iteration output size for each fixed stress cell",
        "failure_semantics": "all five cells remain in ITT; timeout, memory-cap termination, parser error, and rewrite error are terminal observed outcomes and are not replaced",
        "semantic_boundary": "The large stress tier tests software execution and resource behavior only. No large-width semantic-equivalence or optimization-effectiveness claim is made from cells lacking an independent proof.",
        "claim_boundary": "Bounded five-file Benchpress-derived stress panel on one 16-GB Windows host, not the complete >1000-test Benchpress campaign or its 96-GB recommended environment.",
        "source_sha256": {"experiments/e35_benchpress_stress.py": sha256(Path(__file__).resolve()), "scripts/verify_e35_benchpress_stress.py": sha256(ROOT / "scripts/verify_e35_benchpress_stress.py")},
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"); return payload


def worker(payload_path: Path, result_path: Path) -> int:
    payload = json.loads(payload_path.read_text(encoding="utf-8")); source = Path(payload["source_path"]); started = time.perf_counter()
    try:
        if sha256(source) != payload["sha256"]:
            raise ValueError("Benchpress input hash drift")
        circuit = qasm2.load(source, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
        parse_seconds = time.perf_counter() - started
        if int(circuit.num_qubits) != int(payload["expected_qubits_from_name"]):
            raise ValueError("parsed width differs from frozen filename-declared width")
        original_size = int(circuit.size()); original_depth = int(circuit.depth() or 0)
        from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor
        from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher
        listed = WireTraversalPreprocessor().preprocess(circuit)
        wcl_seconds = time.perf_counter() - started - parse_seconds
        engine = Phase2bTemplateMatcher(max_iterations=1, gather_window=64, template_enabled=True)
        optimized = listed.copy(); counts = engine._zero_counters()
        engine._gather_h_sandwiches(optimized, counts); engine._gather_commuting_pairs(optimized, counts); engine._apply_all_templates(optimized, counts); engine._cancel_inverse_pairs(optimized, counts); engine._merge_phase_gates(optimized, counts)
        result = {"status": "success", "parsed_qubits": int(circuit.num_qubits), "parsed_gate_count": original_size, "parsed_depth": original_depth, "gate_alphabet": sorted(circuit.count_ops()), "wcl_gate_count": int(listed.size()), "one_iteration_gate_count": int(optimized.size()), "rewrite_counts": {key: int(value) for key, value in counts.items()}, "parse_seconds": parse_seconds, "wcl_seconds": wcl_seconds, "worker_wall_seconds": time.perf_counter() - started, "semantic_status": "UNAVAILABLE_LARGE_STRESS_ONLY"}
    except BaseException as exc:
        result = {"status": "error", "error": f"{type(exc).__name__}: {exc}", "worker_wall_seconds": time.perf_counter() - started, "semantic_status": "UNAVAILABLE"}
    result_path.write_text(json.dumps(result, sort_keys=True), encoding="utf-8"); return 0


def _tree_rss(process: psutil.Process) -> int:
    total = 0
    try:
        items = [process, *process.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0
    for item in items:
        try:
            total += int(item.memory_info().rss)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total


def run_cell(source: dict[str, Any], protocol: dict[str, Any], benchpress_root: Path, output_dir: Path) -> dict[str, Any]:
    cell_id = "e35-" + hashlib.sha256(f"{source['sha256']}|stress-v1".encode()).hexdigest()[:24]
    payload = {**source, "cell_id": cell_id, "source_path": str((benchpress_root / source["relative_path"]).resolve())}
    payload_path = output_dir / "payloads" / f"{cell_id}.json"; result_path = output_dir / "worker_results" / f"{cell_id}.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True); result_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--payload", str(payload_path), "--result", str(result_path)]
    env = os.environ.copy(); env.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
    started = time.perf_counter(); child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True); process = psutil.Process(child.pid); peak = 0; terminal = None
    timeout = float(protocol["resource_contract"]["cell_timeout_seconds"]); cap = int(protocol["resource_contract"]["rss_cap_bytes"])
    while child.poll() is None:
        peak = max(peak, _tree_rss(process)); elapsed = time.perf_counter() - started
        if peak > cap:
            terminal = "memory_cap"; child.kill(); break
        if elapsed > timeout:
            terminal = "timeout"; child.kill(); break
        time.sleep(0.1)
    stdout, stderr = child.communicate(timeout=10); peak = max(peak, _tree_rss(process))
    if terminal is None and result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
    else:
        result = {"status": terminal or "error", "error": f"worker returncode={child.returncode}", "semantic_status": "UNAVAILABLE"}
    receipt = {"schema_version": "1.0.0", **source, "cell_id": cell_id, **result, "outer_wall_seconds": time.perf_counter() - started, "peak_process_tree_rss_bytes": peak, "stdout_tail": stdout[-2000:], "stderr_tail": stderr[-4000:]}
    receipt_path = output_dir / "cells" / f"{cell_id}.json"; receipt_path.parent.mkdir(parents=True, exist_ok=True); receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"); return receipt


def formal(protocol_path: Path, benchpress_root: Path, output_dir: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("design_status") != "FROZEN_BEFORE_EXECUTION" or protocol["source_sha256"]["experiments/e35_benchpress_stress.py"] != sha256(Path(__file__).resolve()):
        raise ValueError("E35 protocol/source binding failed")
    if git_value(benchpress_root, "rev-parse", "HEAD") != protocol["source"]["commit"] or git_value(benchpress_root, "status", "--short"):
        raise ValueError("E35 Benchpress checkout drift")
    output_dir.mkdir(parents=True, exist_ok=True); rows = []
    for source in protocol["inputs"]:
        receipt = run_cell(source, protocol, benchpress_root, output_dir); rows.append(receipt); print(f"[{len(rows)}/5] {source['case_id']} {receipt['status']} rss={receipt['peak_process_tree_rss_bytes']}", flush=True)
    status_counts = dict(sorted(Counter(row["status"] for row in rows).items())); observed_large = sum(int(row["expected_qubits_from_name"]) >= 28 for row in rows); successful_large = sum(int(row["expected_qubits_from_name"]) >= 28 and row["status"] == "success" for row in rows)
    summary = {"schema_version": "1.0.0", "status": "FORMAL_STRESS_SCHEDULE_COMPLETE" if len(rows) == 5 else "INCOMPLETE", "protocol_sha256": sha256(protocol_path), "itt_scheduled_n": 5, "itt_observed_n": len(rows), "status_counts": status_counts, "large_cells_observed": observed_large, "large_cells_successful": successful_large, "maximum_declared_qubits": max(int(row["expected_qubits_from_name"]) for row in rows), "maximum_peak_process_tree_rss_bytes": max(int(row["peak_process_tree_rss_bytes"]) for row in rows), "rows": rows, "metric_dispositions": {"5.29": {"status": "PARTIAL", "disposition": "A frozen five-file Benchpress-derived multi-tier stress schedule ran with cold-process timeout/memory/error retention; it is not the complete Benchpress campaign."}, "18.06": {"status": "PASS" if successful_large >= 1 and observed_large == 4 else "PARTIAL", "disposition": f"A direct large-circuit software tier covers declared widths 28, 37, 320, and 400 with all four terminal outcomes retained; {successful_large}/4 completed the full bounded parser/WCL/one-iteration workload. No large-width semantic-effect claim is made."}}, "semantic_boundary": protocol["semantic_boundary"], "claim_boundary": protocol["claim_boundary"], "environment": {"python": sys.version, "executable": str(Path(sys.executable).resolve()), "executable_sha256": sha256(Path(sys.executable).resolve()), "qiskit": importlib.metadata.version("qiskit"), "psutil": importlib.metadata.version("psutil"), "platform": platform.platform()}}
    summary_path = output_dir / "summary.json"; summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    artifacts = [protocol_path, Path(__file__).resolve(), ROOT / "scripts/verify_e35_benchpress_stress.py", summary_path] + sorted((output_dir / "cells").glob("*.json")) + sorted((output_dir / "payloads").glob("*.json"))
    manifest = {"schema_version": "1.0.0", "artifact_count": len(artifacts), "artifacts": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in artifacts]}; (output_dir / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"); return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--protocol", type=Path, default=PROTOCOL); parser.add_argument("--output-dir", type=Path, default=OUTPUT); parser.add_argument("--benchpress-root", type=Path, default=DEFAULT_BENCHPRESS); parser.add_argument("--freeze", action="store_true"); parser.add_argument("--formal", action="store_true"); parser.add_argument("--worker", action="store_true"); parser.add_argument("--payload", type=Path); parser.add_argument("--result", type=Path); args = parser.parse_args()
    if args.worker:
        return worker(args.payload.resolve(), args.result.resolve())
    if args.freeze:
        print(json.dumps(freeze(args.protocol.resolve(), args.benchpress_root.resolve()), indent=2, sort_keys=True)); return 0
    if not args.formal:
        raise SystemExit("choose --freeze or --formal")
    summary = formal(args.protocol.resolve(), args.benchpress_root.resolve(), args.output_dir.resolve()); print(json.dumps({"status": summary["status"], "status_counts": summary["status_counts"], "large_successful": summary["large_cells_successful"]}, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
