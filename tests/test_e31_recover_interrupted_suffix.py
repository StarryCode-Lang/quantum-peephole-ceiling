"""Tests for audited recovery of an interrupted E31 checkpoint suffix."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from experiments.e31_recover_interrupted_suffix import recover_interrupted_suffix, sha256


def _fixture(tmp_path: Path, statuses: list[str]) -> tuple[Path, Path]:
    checkpoint = tmp_path / "formal" / "checkpoint.sqlite3"
    checkpoint.parent.mkdir()
    connection = sqlite3.connect(checkpoint)
    connection.execute(
        "CREATE TABLE results (run_id TEXT PRIMARY KEY, run_order INTEGER UNIQUE NOT NULL, "
        "result_json TEXT NOT NULL, committed_utc TEXT NOT NULL)"
    )
    for order, status in enumerate(statuses):
        result = {"run_id": f"run-{order}", "run_order": order, "status": status}
        connection.execute(
            "INSERT INTO results VALUES (?, ?, ?, ?)",
            (result["run_id"], order, json.dumps(result), f"time-{order}"),
        )
        run_dir = checkpoint.parent / "runs" / result["run_id"]
        run_dir.mkdir(parents=True)
        (run_dir / "worker_result.json").write_text(json.dumps(result), encoding="utf-8")
    connection.commit()
    connection.close()
    return checkpoint, checkpoint.parent / "runs"


def test_recovery_archives_evidence_and_removes_only_error_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "experiments.e31_recover_interrupted_suffix._refuse_active_formal_processes",
        lambda: None,
    )
    checkpoint, runs = _fixture(tmp_path, ["success", "timeout", "error", "error"])
    archive = tmp_path / "archive"
    audit = recover_interrupted_suffix(
        checkpoint, runs, archive,
        first_order=2, expected_live_rows=4, expected_suffix_rows=2,
    )
    connection = sqlite3.connect(checkpoint)
    assert connection.execute("SELECT run_order FROM results ORDER BY run_order").fetchall() == [
        (0,), (1,)
    ]
    connection.close()
    archived = sqlite3.connect(archive / "checkpoint_before.sqlite3")
    assert archived.execute("SELECT COUNT(*) FROM results").fetchone()[0] == 4
    archived.close()
    assert [row["run_order"] for row in audit["invalidated_rows"]] == [2, 3]
    assert audit["checkpoint_before_sha256"] == sha256(archive / "checkpoint_before.sqlite3")
    assert audit["checkpoint_after_sha256"] == sha256(checkpoint)
    assert (archive / "runs" / "run-2" / "worker_result.json").is_file()
    assert (archive / "runs" / "run-3" / "worker_result.json").is_file()
    assert len((checkpoint.parent / "formal_results_checkpoint.csv").read_text().splitlines()) == 3


def test_recovery_refuses_suffix_containing_non_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "experiments.e31_recover_interrupted_suffix._refuse_active_formal_processes",
        lambda: None,
    )
    checkpoint, runs = _fixture(tmp_path, ["success", "error", "success"])
    with pytest.raises(ValueError, match="non-error"):
        recover_interrupted_suffix(
            checkpoint, runs, tmp_path / "archive",
            first_order=1, expected_live_rows=3, expected_suffix_rows=2,
        )
    connection = sqlite3.connect(checkpoint)
    assert connection.execute("SELECT COUNT(*) FROM results").fetchone()[0] == 3
    connection.close()
