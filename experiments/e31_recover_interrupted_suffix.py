"""Audited recovery of an infrastructure-interrupted E31 checkpoint suffix.

This operator-only utility preserves a consistent SQLite snapshot and every
affected run directory before replacing the live checkpoint with a copy that
ends immediately before the explicitly identified interrupted suffix.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import psutil


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _refuse_active_formal_processes() -> None:
    own_pid = os.getpid()
    active = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        if process.info["pid"] == own_pid:
            continue
        command = " ".join(process.info.get("cmdline") or []).lower()
        name = str(process.info.get("name") or "").lower()
        if "python" in name and (
            "e31_formal_orchestrator.py" in command
            or "e31_shared_rule_worker.py" in command
        ):
            active.append((process.info["pid"], command[:240]))
    if active:
        raise RuntimeError(f"active E31 formal processes prevent recovery: {active}")


def _artifact_manifest(directory: Path) -> list[dict]:
    return [
        {
            "path": str(path.relative_to(directory)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    ]


def _export_rows(rows: list[dict], path: Path) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def recover_interrupted_suffix(
    checkpoint_path: Path,
    run_root: Path,
    archive_dir: Path,
    *,
    first_order: int,
    expected_live_rows: int,
    expected_suffix_rows: int,
) -> dict:
    checkpoint_path = checkpoint_path.resolve()
    run_root = run_root.resolve()
    archive_dir = archive_dir.resolve()
    if archive_dir.exists():
        raise FileExistsError(f"recovery archive already exists: {archive_dir}")
    if not checkpoint_path.is_file() or not run_root.is_dir():
        raise FileNotFoundError("checkpoint or run directory is absent")
    _refuse_active_formal_processes()

    archive_dir.mkdir(parents=True)
    archived_db = archive_dir / "checkpoint_before.sqlite3"
    source = sqlite3.connect(checkpoint_path, timeout=30)
    try:
        if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("live checkpoint failed SQLite integrity_check")
        source.execute("PRAGMA wal_checkpoint(FULL)")
        all_records = source.execute(
            "SELECT run_id, run_order, result_json, committed_utc "
            "FROM results ORDER BY run_order"
        ).fetchall()
        archive_connection = sqlite3.connect(archived_db)
        try:
            source.backup(archive_connection)
        finally:
            archive_connection.close()
    finally:
        source.close()

    if len(all_records) != expected_live_rows:
        raise ValueError(
            f"live row count {len(all_records)} differs from expected {expected_live_rows}"
        )
    observed_orders = [int(record[1]) for record in all_records]
    if observed_orders != list(range(expected_live_rows)):
        raise ValueError("checkpoint run_order is not a zero-based contiguous prefix")
    suffix = [record for record in all_records if int(record[1]) >= first_order]
    if len(suffix) != expected_suffix_rows:
        raise ValueError(
            f"suffix row count {len(suffix)} differs from expected {expected_suffix_rows}"
        )
    if [int(record[1]) for record in suffix] != list(range(first_order, expected_live_rows)):
        raise ValueError("identified rows are not the entire contiguous checkpoint suffix")
    parsed_suffix = [json.loads(record[2]) for record in suffix]
    if any(result.get("status") != "error" for result in parsed_suffix):
        raise ValueError("identified suffix includes a non-error result")
    if any(int(result.get("run_order", -1)) != int(record[1])
           or str(result.get("run_id")) != str(record[0])
           for result, record in zip(parsed_suffix, suffix)):
        raise ValueError("suffix result identity differs from checkpoint keys")

    archived_runs = archive_dir / "runs"
    archived_runs.mkdir()
    for run_id, _, _, _ in suffix:
        source_dir = run_root / str(run_id)
        if not source_dir.is_dir():
            raise FileNotFoundError(f"affected run directory is absent: {source_dir}")
        shutil.copytree(source_dir, archived_runs / str(run_id))

    repaired_temp = checkpoint_path.with_suffix(
        checkpoint_path.suffix + f".{os.getpid()}.repaired"
    )
    archived_connection = sqlite3.connect(archived_db)
    repaired = sqlite3.connect(repaired_temp)
    try:
        archived_connection.backup(repaired)
        repaired.execute("BEGIN IMMEDIATE")
        repaired.execute("DELETE FROM results WHERE run_order >= ?", (first_order,))
        repaired.commit()
        remaining = repaired.execute(
            "SELECT run_id, run_order, result_json FROM results ORDER BY run_order"
        ).fetchall()
        if len(remaining) != first_order:
            raise ValueError("repaired checkpoint does not end at the expected prefix")
        if repaired.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("repaired checkpoint failed SQLite integrity_check")
    finally:
        repaired.close()
        archived_connection.close()

    retained_results = [json.loads(record[2]) for record in remaining]
    csv_path = checkpoint_path.parent / "formal_results_checkpoint.csv"
    _export_rows(retained_results, csv_path)
    before_sha = sha256(archived_db)
    after_sha = sha256(repaired_temp)
    audit = {
        "action": "AUDITED_INFRASTRUCTURE_INTERRUPTION_SUFFIX_RECOVERY",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "reason": (
            "Host interruption produced a contiguous terminal error suffix; "
            "the affected cells are invalidated and must be rerun in frozen order."
        ),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_before_sha256": before_sha,
        "checkpoint_after_sha256": after_sha,
        "rows_before": expected_live_rows,
        "rows_after": first_order,
        "invalidated_first_run_order": first_order,
        "invalidated_rows": [
            {
                "run_id": str(record[0]),
                "run_order": int(record[1]),
                "committed_utc": str(record[3]),
                "recorded_result": result,
            }
            for record, result in zip(suffix, parsed_suffix)
        ],
        "archived_run_artifacts": _artifact_manifest(archived_runs),
        "recovery_invariant": (
            "All pre-suffix rows and committed timestamps are preserved byte-for-byte "
            "at the logical record level; only the explicit terminal suffix is removed."
        ),
    }
    _atomic_json(archive_dir / "recovery_audit.json", audit)

    for sidecar in (
        checkpoint_path.with_name(checkpoint_path.name + "-wal"),
        checkpoint_path.with_name(checkpoint_path.name + "-shm"),
    ):
        if sidecar.exists() and sidecar.stat().st_size:
            raise RuntimeError(f"non-empty SQLite sidecar appeared during recovery: {sidecar}")
        sidecar.unlink(missing_ok=True)
    os.replace(repaired_temp, checkpoint_path)
    if sha256(checkpoint_path) != after_sha:
        raise RuntimeError("live checkpoint hash differs after atomic replacement")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--first-order", type=int, required=True)
    parser.add_argument("--expected-live-rows", type=int, required=True)
    parser.add_argument("--expected-suffix-rows", type=int, required=True)
    args = parser.parse_args()
    audit = recover_interrupted_suffix(
        args.checkpoint,
        args.run_root,
        args.archive_dir,
        first_order=args.first_order,
        expected_live_rows=args.expected_live_rows,
        expected_suffix_rows=args.expected_suffix_rows,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
