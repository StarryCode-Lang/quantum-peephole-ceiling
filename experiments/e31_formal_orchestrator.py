#!/usr/bin/env python3
"""Checkpointed E31 formal runner. Dry-run is the safe default.

No optimizer is started without --formal and a completed external release gate.
The SQLite checkpoint is the authoritative append-only result ledger.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.metadata
import json
import os
import platform
import signal
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd
import psutil
from qiskit import qasm2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.e31_factorial_pareto_design import validate_design
from experiments.e31_resource_smoke import run_cell
from src.circuits.real_benchmarks import circuit_sha256

DEFAULT_PROTOCOL = PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json"
DEFAULT_DESIGN = PROJECT_ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv"
DEFAULT_METADATA = PROJECT_ROOT / "data/v11/e31_factorial_pareto/design_metadata.json"
DEFAULT_POWER = PROJECT_ROOT / "data/v11/e31_factorial_pareto/dual_estimand_power.json"
DEFAULT_RELEASE_GATE = PROJECT_ROOT / "data/v11/e31_factorial_pareto/formal_release_gate.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/v11/e31_factorial_pareto/formal_run"
WORKER = PROJECT_ROOT / "experiments/e31_shared_rule_worker.py"
SOURCE_FILES = [
    WORKER,
    PROJECT_ROOT / "experiments/e31_resource_smoke.py",
    PROJECT_ROOT / "experiments/e31_listing_phase2b_interaction.py",
    PROJECT_ROOT / "src/circuits/real_benchmarks.py",
    PROJECT_ROOT / "src/optimisation/phase1/wire_traversal.py",
    PROJECT_ROOT / "src/optimisation/phase2/template_matcher.py",
    Path(__file__).resolve(),
]
THREAD_ENV = {
    "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1", "RAYON_NUM_THREADS": "1",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def verify_authorization(protocol_path: Path, design_path: Path,
                         metadata_path: Path, power_path: Path) -> tuple[dict, pd.DataFrame, dict]:
    protocol_path, design_path = protocol_path.resolve(), design_path.resolve()
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.resolve().read_text(encoding="utf-8"))
    power = json.loads(power_path.resolve().read_text(encoding="utf-8"))
    protocol_sha, design_sha = sha256(protocol_path), sha256(design_path)
    if protocol["design_status"] != "FROZEN_BEFORE_EXECUTION":
        raise ValueError("protocol is not frozen before execution")
    if not metadata.get("formal_execution_authorized") or not metadata.get("dual_estimand_power_bound"):
        raise ValueError("design metadata does not authorize formal execution")
    checks = {
        "metadata protocol": metadata.get("protocol_sha256") == protocol_sha,
        "metadata design": metadata.get("design_manifest_sha256") == design_sha,
        "power protocol": power.get("protocol_sha256") == protocol_sha,
        "power design": power.get("design_manifest_sha256") == design_sha,
        "fixed power": power.get("decision", {}).get("fixed_benchmark_A") == "PASS",
        "formal power": power.get("decision", {}).get("formal_28152_execution") == "PASS",
    }
    failed = [name for name, valid in checks.items() if not valid]
    if failed:
        raise ValueError(f"authorization hash/decision failure: {failed}")
    design = pd.read_csv(design_path)
    validate_design(design, protocol)
    if not design["protocol_sha256"].astype(str).eq(protocol_sha).all():
        raise ValueError("design rows are not bound to the frozen protocol")
    if len(design) != int(metadata["scheduled_rows"]):
        raise ValueError("metadata schedule count differs from design")
    if design["run_id"].duplicated().any() or design["run_order"].duplicated().any():
        raise ValueError("design has duplicate run_id or run_order")
    if not design.sort_values("run_order")["run_order"].tolist() == list(range(len(design))):
        raise ValueError("design run_order is not the frozen contiguous permutation")
    return protocol, design.sort_values("run_order", kind="stable").reset_index(drop=True), {
        "protocol_sha256": protocol_sha, "design_manifest_sha256": design_sha,
        "power_sha256": sha256(power_path.resolve()),
    }


def validate_release_gate(path: Path, hashes: dict[str, str]) -> dict:
    if not path.exists():
        raise ValueError("formal release gate is absent; GUOQ/heldout completion is required")
    gate = json.loads(path.read_text(encoding="utf-8"))
    if gate.get("guoq_status") != "COMPLETE" or gate.get("heldout_status") != "COMPLETE":
        raise ValueError("GUOQ and heldout tasks must both be COMPLETE")
    for field in ("protocol_sha256", "design_manifest_sha256", "power_sha256"):
        if gate.get(field) != hashes[field]:
            raise ValueError(f"release gate {field} mismatch")
    return gate


def validate_qasm_inputs(design: pd.DataFrame) -> dict[str, int]:
    """Parse and hash every unique frozen input before creating formal output."""
    unique = design[["qasm_path", "input_circuit_sha256"]].drop_duplicates()
    for row in unique.itertuples(index=False):
        path = (PROJECT_ROOT / str(row.qasm_path)).resolve()
        if not path.is_relative_to(PROJECT_ROOT) or not path.is_file():
            raise ValueError(f"E31 QASM path is absent or outside the project: {path}")
        circuit = qasm2.load(
            path,
            custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
        )
        observed = circuit_sha256(circuit)
        if observed != str(row.input_circuit_sha256):
            raise ValueError(f"E31 parsed-circuit hash mismatch: {path}")
    return {"unique_qasm_inputs_parsed": int(len(unique))}


def resource_plan(design: pd.DataFrame, protocol: dict, workers: int,
                  completed_ids: set[str] | None = None) -> dict:
    if workers < 1:
        raise ValueError("workers must be at least one")
    per_worker_mb = int(protocol["resource_contract"]["memory_budget_mb_per_worker"])
    vm = psutil.virtual_memory()
    requested = workers * per_worker_mb * 1024 * 1024
    safe_physical = int(vm.total * 0.75)
    safe_available = int(vm.available * 0.80)
    if requested > min(safe_physical, safe_available):
        raise ValueError(
            f"workers request {requested / 2**30:.2f} GiB, exceeding physical/available safety cap"
        )
    completed_ids = completed_ids or set()
    pending = design[~design["run_id"].astype(str).isin(completed_ids)]
    budget_seconds = int(pending["budget_seconds"].sum())
    return {
        "total_rows": int(len(design)), "completed_rows": int(len(completed_ids)),
        "pending_rows": int(len(pending)), "workers": workers,
        "per_worker_memory_cap_mb": per_worker_mb,
        "aggregate_memory_cap_mb": workers * per_worker_mb,
        "physical_ram_mb": int(vm.total / 2**20), "available_ram_mb": int(vm.available / 2**20),
        "pending_budget_worker_seconds": budget_seconds,
        "pending_budget_worker_hours": budget_seconds / 3600.0,
        "idealized_budget_wall_hours": budget_seconds / workers / 3600.0,
    }


class Checkpoint:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path, timeout=30, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS results ("
            "run_id TEXT PRIMARY KEY, run_order INTEGER UNIQUE NOT NULL, "
            "result_json TEXT NOT NULL, committed_utc TEXT NOT NULL)"
        )
        self.connection.commit()
        self.lock = threading.Lock()

    def completed(self) -> dict[str, int]:
        return {str(run_id): int(order) for run_id, order in
                self.connection.execute("SELECT run_id, run_order FROM results")}

    def validate_against(self, design: pd.DataFrame) -> None:
        expected = design.set_index("run_id")["run_order"].astype(int).to_dict()
        for run_id, order in self.completed().items():
            if run_id not in expected or expected[run_id] != order:
                raise ValueError("checkpoint contains a foreign or run_order-drifted result")

    def commit(self, result: dict) -> None:
        run_id, run_order = str(result["run_id"]), int(result["run_order"])
        with self.lock:
            try:
                self.connection.execute("BEGIN IMMEDIATE")
                self.connection.execute(
                    "INSERT INTO results VALUES (?, ?, ?, ?)",
                    (run_id, run_order, json.dumps(result, sort_keys=True),
                     datetime.now(timezone.utc).isoformat()),
                )
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise

    def export_csv(self, path: Path) -> None:
        rows = [json.loads(item[0]) for item in self.connection.execute(
            "SELECT result_json FROM results ORDER BY run_order")]
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
        pd.DataFrame(rows).to_csv(temporary, index=False)
        os.replace(temporary, path)

    def close(self) -> None:
        self.connection.close()


def environment_record(hashes: dict[str, str], plan: dict, release_gate: dict) -> dict:
    packages = {}
    for name in ("qiskit", "numpy", "pandas", "scipy", "psutil"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(), **hashes,
        "source_sha256": {str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): sha256(path)
                          for path in SOURCE_FILES},
        "python_executable": str(Path(sys.executable).resolve()),
        "python_executable_sha256": sha256(Path(sys.executable).resolve()),
        "python_version": sys.version, "platform": platform.platform(),
        "processor": platform.processor(), "logical_cpu_count": psutil.cpu_count(),
        "physical_cpu_count": psutil.cpu_count(logical=False),
        "physical_ram_bytes": psutil.virtual_memory().total,
        "thread_limits": THREAD_ENV, "cold_process_per_cell": True,
        "packages": packages, "resource_plan_at_start": plan,
        "release_gate": release_gate,
    }


def verify_or_write_environment(path: Path, record: dict) -> None:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        immutable = ("protocol_sha256", "design_manifest_sha256", "power_sha256",
                     "source_sha256", "python_executable_sha256", "thread_limits")
        drift = [field for field in immutable if existing.get(field) != record.get(field)]
        if drift:
            raise ValueError(f"resume environment/source drift: {drift}")
        return
    atomic_json(path, record)


def refuse_process_overlap() -> None:
    own_pid = os.getpid()
    forbidden = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        if process.info["pid"] == own_pid:
            continue
        command = " ".join(process.info.get("cmdline") or []).lower()
        name = str(process.info.get("name") or "").lower()
        is_python_or_pytest = "python" in name or "pytest" in name
        if is_python_or_pytest and (
            "pytest" in command or "e31_formal_orchestrator.py" in command
            or "e31_shared_rule_worker.py" in command
        ):
            forbidden.append((process.info["pid"], command[:240]))
    if forbidden:
        raise RuntimeError(f"formal execution overlaps an active test/formal worker: {forbidden}")


def acquire_lock(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)


def run_schedule(
    design: pd.DataFrame, protocol: dict, design_sha: str, checkpoint: Checkpoint,
    run_dir: Path, *, workers: int, max_runs: int | None,
    stop_event: threading.Event, executor: Callable | None = None,
    fault_after_commits: int | None = None,
) -> int:
    checkpoint.validate_against(design)
    completed = checkpoint.completed()
    pending = design[~design["run_id"].astype(str).isin(completed)].sort_values("run_order")
    if max_runs is not None:
        pending = pending.head(max_runs)
    rows = [row for _, row in pending.iterrows()]
    execute = executor or (lambda row: run_cell(row, protocol, design_sha, run_dir, stop_event))
    committed = 0
    cursor = 0
    futures: dict[concurrent.futures.Future, pd.Series] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        while (cursor < len(rows) or futures) and not stop_event.is_set():
            while cursor < len(rows) and len(futures) < workers and not stop_event.is_set():
                # Submission is strictly the frozen randomized run_order.
                row = rows[cursor]
                futures[pool.submit(execute, row)] = row
                cursor += 1
            if not futures:
                break
            done, _ = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for future in done:
                row = futures.pop(future)
                try:
                    result = future.result()
                except InterruptedError:
                    if stop_event.is_set():
                        continue
                    raise
                if (str(result.get("run_id")) != str(row.run_id)
                        or int(result.get("run_order", -1)) != int(row.run_order)):
                    raise ValueError("worker result identity differs from dispatched frozen row")
                checkpoint.commit(result)
                committed += 1
                if fault_after_commits is not None and committed >= fault_after_commits:
                    stop_event.set()
                    raise RuntimeError("injected crash after atomic commit")
    return committed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--power", type=Path, default=DEFAULT_POWER)
    parser.add_argument("--release-gate", type=Path, default=DEFAULT_RELEASE_GATE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--max-runs", type=int)
    parser.add_argument("--formal", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.formal and args.dry_run:
        raise SystemExit("choose either --formal or --dry-run")
    if not args.formal:
        args.dry_run = True
    protocol, design, hashes = verify_authorization(
        args.protocol, args.design, args.metadata, args.power
    )
    if args.max_runs is not None and args.max_runs < 0:
        raise SystemExit("--max-runs must be non-negative")
    plan = resource_plan(design, protocol, args.workers)
    if args.dry_run:
        print(json.dumps({"mode": "DRY_RUN_NO_CELLS_EXECUTED", "hashes": hashes,
                          "resource_plan": plan}, indent=2, sort_keys=True))
        return 0

    release_gate = validate_release_gate(args.release_gate.resolve(), hashes)
    qasm_gate = validate_qasm_inputs(design)
    refuse_process_overlap()
    output = args.output_dir.resolve()
    lock_path = output / "formal.lock"
    lock_fd = acquire_lock(lock_path)
    checkpoint = None
    stop_event = threading.Event()
    previous_handlers = {}
    try:
        for name in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[name] = signal.getsignal(name)
            signal.signal(name, lambda *_: stop_event.set())
        checkpoint = Checkpoint(output / "checkpoint.sqlite3")
        checkpoint.validate_against(design)
        plan = resource_plan(design, protocol, args.workers, set(checkpoint.completed()))
        verify_or_write_environment(
            output / "environment.json",
            {**environment_record(hashes, plan, release_gate), "qasm_preflight": qasm_gate},
        )
        committed = run_schedule(
            design, protocol, hashes["design_manifest_sha256"], checkpoint,
            output / "runs", workers=args.workers, max_runs=args.max_runs,
            stop_event=stop_event,
        )
        checkpoint.export_csv(output / "formal_results_checkpoint.csv")
        print(json.dumps({"newly_committed": committed,
                          "total_committed": len(checkpoint.completed()),
                          "stopped": stop_event.is_set()}, indent=2))
        return 130 if stop_event.is_set() else 0
    finally:
        if checkpoint is not None:
            checkpoint.export_csv(output / "formal_results_checkpoint.csv")
            checkpoint.close()
        for name, handler in previous_handlers.items():
            signal.signal(name, handler)
        os.close(lock_fd)
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
