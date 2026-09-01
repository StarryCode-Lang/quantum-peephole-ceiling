from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from scripts.audit_e31_temporal_gate_binding import build_audit


def test_temporal_binding_distinguishes_embedded_time_from_filesystem_mtime(tmp_path: Path):
    e31 = tmp_path / "data/v11/e31_factorial_pareto"
    checkpoint = e31 / "formal_run/checkpoint.sqlite3"
    checkpoint.parent.mkdir(parents=True)
    with sqlite3.connect(checkpoint) as connection:
        connection.execute(
            "CREATE TABLE results (run_order INTEGER, committed_utc TEXT, result_json TEXT)"
        )
        connection.executemany(
            "INSERT INTO results VALUES (?, ?, ?)",
            [
                (0, "2026-08-24T00:00:00+00:00", json.dumps({"status": "success"})),
                (1, "2026-08-24T00:00:01+00:00", json.dumps({"status": "timeout"})),
            ],
        )
    (e31 / "preanalysis_method_erratum_gate.json").write_text(json.dumps({
        "checkpoint_boundary": {
            "committed_rows": 1, "max_run_order": 0,
            "last_committed_utc": "2026-08-24T00:00:00+00:00",
        },
    }), encoding="utf-8")
    (e31 / "host_environment_limitation_gate.json").write_text(json.dumps({
        "created_utc": "2026-08-24T00:00:02+00:00",
        "checkpoint_boundary": {
            "rows": 2, "max_run_order": 1,
            "status_counts_only": {"success": 1, "timeout": 1},
        },
    }), encoding="utf-8")
    audit = build_audit(tmp_path)
    assert audit["overall_temporal_provenance_rating"] == "PARTIAL"
    assert audit["method_gate"]["created_utc_embedded_in_original_gate"] is False
    assert audit["host_gate"]["temporal_evidence"].startswith("PASS_")
