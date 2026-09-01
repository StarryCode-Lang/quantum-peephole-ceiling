"""Resume and fault-safety tests for the E31 formal orchestrator."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path

import pandas as pd
import pytest

from experiments.e31_formal_orchestrator import (
    Checkpoint, resource_plan, run_schedule, validate_release_gate,
    verify_authorization, refuse_process_overlap, validate_qasm_inputs,
)

ROOT = Path(__file__).resolve().parents[1]


def _design(n: int = 4) -> pd.DataFrame:
    return pd.DataFrame({
        "run_id": [f"run-{index}" for index in range(n)],
        "run_order": list(range(n)),
        "budget_seconds": [1] * n,
    })


def _protocol() -> dict:
    return {"resource_contract": {"memory_budget_mb_per_worker": 64}}


def _executor(calls: list[str]):
    def execute(row: pd.Series) -> dict:
        calls.append(str(row.run_id))
        return {"run_id": str(row.run_id), "run_order": int(row.run_order), "status": "success"}
    return execute


def test_checkpoint_resume_skips_committed_ids_and_preserves_order(tmp_path: Path):
    design = _design()
    checkpoint = Checkpoint(tmp_path / "checkpoint.sqlite3")
    calls: list[str] = []
    assert run_schedule(
        design, _protocol(), "d" * 64, checkpoint, tmp_path / "runs",
        workers=1, max_runs=2, stop_event=threading.Event(), executor=_executor(calls),
    ) == 2
    assert calls == ["run-0", "run-1"]
    resumed_calls: list[str] = []
    assert run_schedule(
        design, _protocol(), "d" * 64, checkpoint, tmp_path / "runs",
        workers=1, max_runs=None, stop_event=threading.Event(), executor=_executor(resumed_calls),
    ) == 2
    assert resumed_calls == ["run-2", "run-3"]
    assert checkpoint.completed() == {f"run-{i}": i for i in range(4)}
    checkpoint.close()


def test_duplicate_run_id_is_rejected_atomically(tmp_path: Path):
    checkpoint = Checkpoint(tmp_path / "checkpoint.sqlite3")
    result = {"run_id": "run-0", "run_order": 0, "status": "success"}
    checkpoint.commit(result)
    with pytest.raises(sqlite3.IntegrityError):
        checkpoint.commit(result)
    assert checkpoint.completed() == {"run-0": 0}
    checkpoint.close()


def test_fault_after_commit_resumes_without_duplicate_or_skip(tmp_path: Path):
    design = _design(3)
    checkpoint = Checkpoint(tmp_path / "checkpoint.sqlite3")
    first_calls: list[str] = []
    stop = threading.Event()
    with pytest.raises(RuntimeError, match="injected crash"):
        run_schedule(
            design, _protocol(), "d" * 64, checkpoint, tmp_path / "runs",
            workers=1, max_runs=None, stop_event=stop, executor=_executor(first_calls),
            fault_after_commits=1,
        )
    assert checkpoint.completed() == {"run-0": 0}
    resume_calls: list[str] = []
    run_schedule(
        design, _protocol(), "d" * 64, checkpoint, tmp_path / "runs",
        workers=1, max_runs=None, stop_event=threading.Event(), executor=_executor(resume_calls),
    )
    assert resume_calls == ["run-1", "run-2"]
    assert checkpoint.completed() == {"run-0": 0, "run-1": 1, "run-2": 2}
    checkpoint.close()


def test_worker_identity_fault_is_not_checkpointed(tmp_path: Path):
    checkpoint = Checkpoint(tmp_path / "checkpoint.sqlite3")
    def wrong(row: pd.Series) -> dict:
        return {"run_id": "foreign", "run_order": int(row.run_order), "status": "success"}
    with pytest.raises(ValueError, match="identity"):
        run_schedule(
            _design(1), _protocol(), "d" * 64, checkpoint, tmp_path / "runs",
            workers=1, max_runs=None, stop_event=threading.Event(), executor=wrong,
        )
    assert checkpoint.completed() == {}
    checkpoint.close()


def test_real_frozen_hash_chain_authorizes_dry_preflight():
    protocol, design, hashes = verify_authorization(
        ROOT / "experiments/e31_factorial_pareto_protocol.json",
        ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv",
        ROOT / "data/v11/e31_factorial_pareto/design_metadata.json",
        ROOT / "data/v11/e31_factorial_pareto/dual_estimand_power.json",
    )
    assert len(design) == 28152
    assert protocol["design_status"] == "FROZEN_BEFORE_EXECUTION"
    assert len(hashes["power_sha256"]) == 64


def test_qasm_preflight_parses_legacy_u_and_verifies_frozen_hash():
    design = pd.read_csv(ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv")
    representative = design[design["circuit_id"].eq("qaoa_line_6")].head(1)
    assert len(representative) == 1
    assert validate_qasm_inputs(representative) == {"unique_qasm_inputs_parsed": 1}

    corrupted = representative.copy()
    corrupted.loc[:, "input_circuit_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="parsed-circuit hash mismatch"):
        validate_qasm_inputs(corrupted)


def test_release_gate_requires_both_external_tasks_and_hashes(tmp_path: Path):
    path = tmp_path / "gate.json"
    hashes = {"protocol_sha256": "a", "design_manifest_sha256": "b", "power_sha256": "c"}
    path.write_text(json.dumps({**hashes, "guoq_status": "COMPLETE", "heldout_status": "RUNNING"}))
    with pytest.raises(ValueError, match="both be COMPLETE"):
        validate_release_gate(path, hashes)


def test_worker_ram_aggregate_safety_rejects_absurd_parallelism():
    with pytest.raises(ValueError, match="safety cap"):
        resource_plan(_design(), _protocol(), workers=10**9)


def test_formal_mode_rejects_overlapping_pytest(monkeypatch):
    class FakeProcess:
        info = {"pid": os.getpid() + 1, "name": "python.exe",
                "cmdline": ["python", "-m", "pytest", "tests"]}
    monkeypatch.setattr("experiments.e31_formal_orchestrator.psutil.process_iter",
                        lambda attrs: [FakeProcess()])
    with pytest.raises(RuntimeError, match="overlaps"):
        refuse_process_overlap()
