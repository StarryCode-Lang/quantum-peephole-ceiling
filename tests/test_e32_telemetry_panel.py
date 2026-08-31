from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.e32_telemetry_panel import build_summary, canonical_run_id
from experiments.e32_telemetry_worker import EventRecorder


def test_run_ids_are_stable_and_treatment_sensitive() -> None:
    one = canonical_run_id("a" * 64, "LBL", "COMMUTATION_ONLY", 16)
    assert one == canonical_run_id("a" * 64, "LBL", "COMMUTATION_ONLY", 16)
    assert one != canonical_run_id("a" * 64, "WCL", "COMMUTATION_ONLY", 16)


def test_event_recorder_rejects_nonmonotonic_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    values = iter([101, 100])
    monkeypatch.setattr("experiments.e32_telemetry_worker.time.perf_counter_ns", lambda: next(values))
    recorder = EventRecorder(0)
    recorder.add("first")
    with pytest.raises(RuntimeError, match="backwards"):
        recorder.add("second")


def test_summary_retains_failures_in_itt() -> None:
    common = {"listing_model": "LBL", "rule_set": "COMMUTATION_ONLY", "circuit_family": "A"}
    receipts = [
        {**common, "status": "success", "time_to_first_valid_seconds": 1.0, "time_to_best_seconds": 2.0},
        {**common, "status": "timeout", "time_to_first_valid_seconds": None, "time_to_best_seconds": None},
    ]
    summary = build_summary(receipts, "b" * 64)
    assert summary["itt_observed_n"] == 2
    assert summary["timing_available_n"] == 1
    assert summary["timing_unavailable_n"] == 1
    assert summary["treatment_summaries"][0]["failure_timeout_invalid_n"] == 1
