"""Fail-closed verifier for the E46 window-landscape package.

The verifier checks the receipt hash chain, re-derives every aggregate from
the stored window rows, re-searches a deterministic subsample of windows with
the certified engine and compares the claims, and re-replays every stored
escape witness.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e46_window_landscape.run import (  # noqa: E402
    HORIZONS,
    RULE_SCOPE,
    WINDOW_STATE_BUDGET,
    WINDOW_WIDTHS,
    WINDOW_TIME_BUDGET_SECONDS,
    load_root_states,
    window_starts,
    window_state,
)
from src.optimisation.certified_landscape import (  # noqa: E402
    replay_actions,
    search_landscape_horizons_compact,
)

PACKAGE = ROOT / "data" / "v15" / "e46_window_landscape"
SUBSAMPLE_STARTS = {0, 1, 7, 31}
SUBSAMPLE_LIMIT = 12


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_cell(value: Any) -> str:
    """Match csv.DictWriter rendering of None and scalars."""

    return "" if value is None else str(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=PACKAGE)
    parser.add_argument("--skip-search", action="store_true", help="skip the window re-search subsample")
    args = parser.parse_args()
    package = args.output_root.resolve()

    checks: dict[str, Any] = {}
    status = "PASS"
    try:
        receipt = json.loads((package / "receipt.json").read_text(encoding="utf-8"))
        for name, field in (
            ("protocol.json", "protocol_sha256"),
            ("window_results.csv", "window_results_sha256"),
            ("input_summaries.csv", "input_summaries_sha256"),
            ("escape_certificates.jsonl", "escape_certificates_sha256"),
        ):
            if sha256(package / name) != receipt[field]:
                raise RuntimeError(f"receipt_hash_mismatch:{name}")
        checks["receipt_hashes"] = "PASS"

        with (package / "window_results.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != receipt["window_rows"]:
            raise RuntimeError("window_row_count_mismatch")
        for key, aggregate in receipt["by_config"].items():
            width = int(key.split("_")[0][1:])
            horizon = int(key.split("_h")[1])
            selected = [row for row in rows if int(row["window_width"]) == width and int(row["horizon"]) == horizon]
            escapes = [row for row in selected if row["status"] == "EXACT_ESCAPE"]
            if len(selected) != aggregate["window_count"] or len(escapes) != aggregate["escape_count"]:
                raise RuntimeError(f"aggregate_mismatch:{key}")
            if (
                len({row["source_id"] for row in escapes}) != aggregate["inputs_with_escape"]
                or sum(row["status"] == "EXACT_H_LOCAL_OPTIMUM" for row in selected) != aggregate["local_optimum_count"]
            ):
                raise RuntimeError(f"aggregate_detail_mismatch:{key}")
        checks["aggregates"] = "PASS"
        truncated = sum(
            row["status"] in {"WITNESS_CERTIFIED_SEARCH_INCOMPLETE", "RESOURCE_BOUNDED_NO_WITNESS"}
            for row in rows
        )
        if truncated != receipt["resource_truncated_windows"]:
            raise RuntimeError("truncation_count_mismatch")

        stored_escapes = [
            json.loads(line)
            for line in (package / "escape_certificates.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(stored_escapes) != receipt["escape_certificate_count"]:
            raise RuntimeError("escape_certificate_count_mismatch")
        escape_rows = sum(row["status"] == "EXACT_ESCAPE" for row in rows)
        if escape_rows != receipt["escape_row_count"]:
            raise RuntimeError("escape_row_count_mismatch")
        first_per_config = {
            (record["source_id"], int(record["window_width"]), int(record["horizon"]))
            for record in stored_escapes
        }
        if len(first_per_config) != len(stored_escapes):
            raise RuntimeError("witness_storage_contract_violated")
        checks["escape_witnesses_replayed"] = len(stored_escapes)
        root_by_id = {item["source_id"]: item for item in load_root_states()}
        for record in stored_escapes:
            item = root_by_id[record["source_id"]]
            window = window_state(item["state"], int(record["window_start"]), int(record["window_width"]))
            if window.state_hash != record["window_state_sha256"]:
                raise RuntimeError(f"window_hash_mismatch:{record['source_id']}")
            witness = record["certificate"]["witnesses"]["escape"]
            outcome = replay_actions(window, witness, ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json", RULE_SCOPE)
            if not outcome.get("accepted"):
                raise RuntimeError(f"witness_replay_failed:{record['source_id']}:{outcome.get('reason')}")

        if not args.skip_search:
            verified = 0
            for item in root_by_id.values():
                for width in WINDOW_WIDTHS:
                    starts = [start for start in window_starts(item["root_gate_count"], width) if start in SUBSAMPLE_STARTS][:SUBSAMPLE_LIMIT]
                    for start in starts:
                        window = window_state(item["state"], start, width)
                        for horizon in HORIZONS:
                            certificate = search_landscape_horizons_compact(
                                window,
                                ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json",
                                (horizon,),
                                state_budget=WINDOW_STATE_BUDGET,
                                rule_scope=RULE_SCOPE,
                                time_budget_seconds=WINDOW_TIME_BUDGET_SECONDS,
                            )[str(horizon)]
                            stored = next(
                                row
                                for row in rows
                                if row["source_id"] == item["source_id"]
                                and int(row["window_width"]) == width
                                and int(row["window_start"]) == start
                                and int(row["horizon"]) == horizon
                            )
                            if (
                                certificate["status"] != stored["status"]
                                or csv_cell(certificate["escape_depth"]) != stored["escape_depth"]
                                or csv_cell(certificate["best_cost"]) != stored["best_cost"]
                            ):
                                raise RuntimeError(
                                    f"window_search_mismatch:{item['source_id']}:{width}:{start}:{horizon}"
                                )
                            verified += 1
            checks["window_search_subsample"] = verified
    except RuntimeError as exc:
        status = "FAIL"
        checks["failure_reason"] = str(exc)

    print(json.dumps({"status": status, "package": package.relative_to(ROOT).as_posix(), **checks}, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
