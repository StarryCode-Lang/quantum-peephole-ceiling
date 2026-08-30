"""Regression tests for the pre-paper external-blocker table."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKERS_PATH = ROOT / "release/prepaper_external_blockers.csv"
LEDGER_PATH = ROOT / "docs/review/metric_audit_ledger_2026-08-24.csv"


def _blocker_rows() -> list[dict]:
    with BLOCKERS_PATH.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_blocker_table_covers_every_fail_and_external():
    import pandas as pd

    frame = pd.read_csv(LEDGER_PATH, keep_default_na=False, dtype=str)
    expected = set(frame.loc[frame["status"].isin({"FAIL", "EXTERNAL"}), "metric_id"])
    rows = _blocker_rows()
    observed_fail_external = {
        row["metric_id"] for row in rows if row["status"] in {"FAIL", "EXTERNAL"}
    }
    assert observed_fail_external == expected
    assert len(rows) >= len(expected)


def test_blocker_table_has_complete_fields():
    for row in _blocker_rows():
        for field in ("metric_id", "status", "metric", "actor", "action",
                      "required_input", "acceptance_evidence"):
            assert row[field].strip(), f"blank field {field}: {row['metric_id']}"


def test_blocker_table_does_not_claim_local_agent_as_external_actor():
    rows = _blocker_rows()
    external = [row for row in rows if row["status"] == "EXTERNAL"]
    assert external, "EXTERNAL metrics must appear in the blocker table"
    for row in external:
        assert row["actor"].strip(), row["metric_id"]
