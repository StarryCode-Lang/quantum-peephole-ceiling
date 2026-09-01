"""Run a non-confirmatory 2-input x 4-cell E31 resource smoke packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import psutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_DESIGN = PROJECT_ROOT / "data" / "v11" / "e31_factorial_pareto" / "design_manifest.csv"
DEFAULT_PROTOCOL = PROJECT_ROOT / "experiments" / "e31_factorial_pareto_protocol.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "v11" / "e31_factorial_pareto" / "smoke_resource_2x4"
WORKER = PROJECT_ROOT / "experiments" / "e31_shared_rule_worker.py"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _kill_tree(pid: int) -> None:
    try:
        parent = psutil.Process(pid)
    except psutil.Error:
        return
    processes = parent.children(recursive=True) + [parent]
    for process in reversed(processes):
        try:
            process.terminate()
        except psutil.Error:
            pass
    _, alive = psutil.wait_procs(processes, timeout=1.0)
    for process in alive:
        try:
            process.kill()
        except psutil.Error:
            pass


def select_smoke_cells(design: pd.DataFrame) -> pd.DataFrame:
    """Choose two families and four cells exercising rules/listings/timeout."""
    units = (design.sort_values(["circuit_family", "n_qubits", "circuit_id"])
             .drop_duplicates("input_circuit_sha256"))
    chosen = units.drop_duplicates("circuit_family").head(2)[
        ["input_circuit_sha256"]
    ]
    if len(chosen) != 2:
        raise ValueError("resource smoke requires two unique families")
    cell_specs = {
        ("LBL", "COMMUTATION_ONLY", 4, 1),
        ("LBL", "COMMUTATION_PLUS_TEMPLATES", 4, 10),
        ("WCL", "COMMUTATION_ONLY", 4, 10),
        ("WCL", "COMMUTATION_PLUS_TEMPLATES", 4, 10),
    }
    subset = design[design["input_circuit_sha256"].isin(chosen.input_circuit_sha256)].copy()
    observed = list(zip(subset.listing_model, subset.rule_set,
                        subset.window_gates, subset.budget_seconds))
    subset = subset[[cell in cell_specs for cell in observed]].sort_values("run_order")
    if len(subset) != 8 or subset.input_circuit_sha256.nunique() != 2:
        raise ValueError("resource smoke selection is not 2 inputs x 4 cells")
    return subset.reset_index(drop=True)


def run_cell(row: pd.Series, protocol: dict, design_sha: str,
             work_dir: Path, stop_event=None) -> dict:
    run_dir = work_dir / str(row.run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        **row.to_dict(),
        "fidelity_threshold": protocol["semantic_contract"]["fidelity_threshold"],
        "common_basis": protocol["semantic_contract"]["common_basis"],
    }
    payload_path = run_dir / "payload.json"
    result_path = run_dir / "worker_result.json"
    result_path.unlink(missing_ok=True)
    payload_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    child_env = os.environ.copy()
    child_env.update({
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
        "RAYON_NUM_THREADS": "1",
    })
    start = time.perf_counter()
    process = subprocess.Popen(
        [sys.executable, str(WORKER), "--payload", str(payload_path), "--result", str(result_path)],
        cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        creationflags=creationflags, env=child_env,
    )
    peak_bytes = 0
    terminal_status: str | None = None
    interrupted = False
    budget = float(row.budget_seconds)
    memory_cap = float(row.memory_budget_mb) * 1024 * 1024
    while process.poll() is None:
        elapsed = time.perf_counter() - start
        if stop_event is not None and stop_event.is_set():
            interrupted = True
            _kill_tree(process.pid)
            break
        try:
            tree = [psutil.Process(process.pid)] + psutil.Process(process.pid).children(recursive=True)
            rss = sum(item.memory_info().rss for item in tree if item.is_running())
            peak_bytes = max(peak_bytes, rss)
        except psutil.Error:
            pass
        if peak_bytes > memory_cap:
            terminal_status = "oom"
            _kill_tree(process.pid)
            break
        if elapsed > budget:
            terminal_status = "timeout"
            _kill_tree(process.pid)
            break
        time.sleep(0.025)
    stdout, stderr = process.communicate(timeout=5)
    wall = time.perf_counter() - start
    if terminal_status is None and process.returncode == 0 and result_path.is_file():
        worker = json.loads(result_path.read_text(encoding="utf-8"))
    else:
        worker = {
            "status": terminal_status or "error",
            "valid_equivalent_output": False,
            "exact_fidelity": None,
            "output_circuit_sha256": "",
            "common_basis_gate_reduction_pct": 0.0,
            "trace": [],
        }
    (run_dir / "stdout.log").write_text(stdout, encoding="utf-8")
    (run_dir / "stderr.log").write_text(stderr, encoding="utf-8")
    if interrupted:
        raise InterruptedError("formal stop requested; current cell was not checkpointed")
    return {
        "run_id": row.run_id,
        "protocol_sha256": row.protocol_sha256,
        "design_manifest_sha256": design_sha,
        "input_circuit_sha256": row.input_circuit_sha256,
        "circuit_id": row.circuit_id,
        "circuit_family": row.circuit_family,
        "listing_model": row.listing_model,
        "rule_set": row.rule_set,
        "window_gates": int(row.window_gates),
        "budget_seconds": int(row.budget_seconds),
        "run_order": int(row.run_order),
        "primary_pair_orientation": int(row.primary_pair_orientation),
        **worker,
        "wall_seconds_end_to_end": float(wall),
        "peak_rss_mb": float(peak_bytes / (1024 * 1024)),
    }


def run(design_path: Path, protocol_path: Path, output_dir: Path) -> Path:
    design_path = design_path.resolve()
    protocol_path = protocol_path.resolve()
    design = pd.read_csv(design_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    selected = select_smoke_cells(design)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = pd.DataFrame([
        run_cell(row, protocol, _sha(design_path), output_dir / "runs")
        for _, row in selected.iterrows()
    ])
    result_path = output_dir / "smoke_results.csv"
    results.to_csv(result_path, index=False)
    from analysis.e31_factorial_pareto_analysis import validate_results
    validate_results(
        design, results, protocol, design_sha256=_sha(design_path),
        allow_incomplete_smoke=True,
    )
    metadata = {
        "experiment_id": protocol["experiment_id"],
        "status": "RESOURCE_SMOKE_NONCONFIRMATORY",
        "confirmatory": False,
        "formal_schedule_complete": False,
        "analysis_schema_gate_passed": True,
        "n_unique_inputs": int(results.input_circuit_sha256.nunique()),
        "n_cells_per_input": 4,
        "n_rows": len(results),
        "status_counts": results.status.value_counts().to_dict(),
        "protocol_sha256": _sha(protocol_path),
        "design_manifest_sha256": _sha(design_path),
        "result_sha256": _sha(result_path),
    }
    (output_dir / "smoke_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    return result_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(run(args.design, args.protocol, args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
