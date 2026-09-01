"""Summarize budget exhaustion and retained-valid-output outcomes in sealed E31."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/v11/e31_factorial_pareto/formal_run/final/formal_results.csv"
DEFAULT_OUTPUT = ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis/runtime_outcome_audit.json"


def build_audit() -> dict[str, object]:
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 28152:
        raise RuntimeError("unexpected E31 formal row count")
    status_counts = Counter(row["status"] for row in rows)
    timeout_rows = [row for row in rows if row["status"] == "timeout"]
    timeout_valid = [row for row in timeout_rows if row["valid_equivalent_output"].lower() == "true"]
    timeout_with_output = [row for row in timeout_rows if row["output_circuit_sha256"]]
    timeout_with_trace = [row for row in timeout_rows if row["trace"] not in {"", "[]"}]
    if status_counts != {"success": 20314, "timeout": 7838}:
        raise RuntimeError(f"unexpected E31 status counts: {status_counts}")
    return {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_E31_BUDGET_EXHAUSTED_VALID_RATE_MEASURED",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "formal_rows": len(rows),
        "status_counts": dict(status_counts),
        "budget_exhausted_rows": len(timeout_rows),
        "budget_exhausted_with_valid_retained_output": len(timeout_valid),
        "budget_exhausted_but_valid_rate": len(timeout_valid) / len(timeout_rows),
        "budget_exhausted_with_output_hash": len(timeout_with_output),
        "budget_exhausted_with_nonempty_trace": len(timeout_with_trace),
        "interpretation": (
            "The sealed schema records zero timeout rows with a retained valid output, output hash, "
            "or nonempty optimization trace; the observed budget-exhausted-but-valid rate is 0/7,838."
        ),
        "limitation": (
            "This zero is a retained-artifact outcome under forced process timeout. It does not prove "
            "that no valid incumbent existed transiently before termination; incumbent checkpointing "
            "was not instrumented for timed-out workers."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_audit()
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": output.relative_to(ROOT).as_posix(), "status": payload["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
