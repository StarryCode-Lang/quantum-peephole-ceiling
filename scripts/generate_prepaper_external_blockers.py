"""Generate the pre-paper external-blocker table from the current ledger.

Every non-PASS metric that cannot be closed by the local agent is recorded
with an explicit actor, action, required input, and acceptance evidence.
This is a deliverable, not a status upgrade: nothing here changes the ledger.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/review/metric_audit_ledger_2026-08-24.csv"
DEFAULT_OUTPUT = ROOT / "release/prepaper_external_blockers.csv"

# actor / action / required_input / acceptance_evidence, keyed by metric_id.
BLOCKERS = {
    # --- Real QPU / external hardware platform (user must provide access) ---
    "13.15": ("user/QPU provider", "run the frozen cross-platform panel on >=2 real QPU backends", "QPU accounts, budget, target devices, authorization", "per-device ITT results + semantic verification + hardware run logs"),
    "14.06": ("user/QPU provider", "record calibration time on a real QPU", "QPU access + timing telemetry", "timestamped calibration records"),
    "14.10": ("user/QPU provider", "report idle time on a real QPU", "QPU access + timing telemetry", "idle-time measurements per circuit"),
    "14.11": ("user/QPU provider", "run crosstalk-sensitive concurrency experiment", "QPU with concurrent execution + crosstalk data", "concurrency vs crosstalk measurements"),
    "14.16": ("user/QPU provider", "execute the frozen panel on at least one real QPU", "QPU account, budget, device, authorization", "real-hardware execution records + results"),
    "14.17": ("user/QPU provider", "repeat the hardware experiment on multiple dates", "QPU access across >=2 dates", "dated run records + drift analysis"),
    "14.18": ("user/QPU provider", "randomize execution order to resist drift", "QPU access + randomized schedule", "randomized-order run log + drift-bound analysis"),
    "14.20": ("user/QPU provider", "set shots by a precision target", "QPU access + precision spec", "shots-vs-precision justification + records"),
    "14.27": ("user/QPU provider", "test depth-shorter-but-crosstalk-stronger tradeoff", "QPU with crosstalk characterization", "depth vs crosstalk measurements"),
    "14.28": ("user/QPU provider", "report queue time vs pure execution time", "QPU access + queue telemetry", "queue/execution time split per job"),
    "14.29": ("user/QPU provider", "report end-to-end time-to-solution", "QPU access + end-to-end timing", "end-to-end wall-time records"),
    "14.33": ("user/QPU provider", "run pulse-aware compilation comparison", "QPU pulse access + pulse compiler", "pulse-aware vs gate-level results"),
    # --- External actors / independent humans ---
    "1.19": ("independent reproducer (non-developer)", "cold-start reproduction on a clean machine", "clean machine + the layered archive", "full reproduction log from empty env to key tables/receipts"),
    "3.30": ("anonymous peer reviewer", "perform a novelty red-team search", "frozen search protocol", "dated search queries, databases, and novelty judgment"),
    "13.16": ("independent research group", "provide independent cross-group data", "external group + their dataset", "independent dataset + provenance + results"),
    "15.28": ("independent verifier (clean machine)", "verify the release on a clean machine", "clean machine + archive", "clean-machine verification receipt"),
    "15.29": ("non-author verifier", "verify the release as a non-author", "non-author + archive", "non-author verification receipt"),
    "16.19": ("real user / external research group", "state a real need for the tool", "external user/group", "documented external requirement"),
    "16.20": ("external party", "provide reuse evidence", "external reuser", "documented external reuse"),
    "17.19": ("independent researcher", "attack the theorem", "independent researcher + theorem statement", "recorded attack attempts and outcome"),
    "17.21": ("external tool author", "check the run configuration", "tool author + version/commit/CLI/budget/input hashes", "author confirmation or objection, archived"),
    # --- User decision / release authority ---
    "15.09": ("user (rights holder)", "choose a compatible data license", "user legal/licensing decision", "license file + decision record"),
    "15.10": ("user (account holder)", "publish DOI/Zenodo archive", "user Zenodo account + publication authorization", "DOI + Zenodo deposit record"),
    "15.40": ("user (release authority)", "authorize a release commit and candidate SHA", "user commit authorization + candidate SHA", "release rebuilt from the fixed commit"),
    # --- EXTERNAL (pre-submission / external) ---
    "1.20": ("independent reviewer (pre-submission)", "novelty red-team per frozen search protocol", "frozen search protocol + independent reviewer", "dated search record and novelty judgment"),
    "8.35": ("external method authors", "verify the exact run configuration", "version/commit/CLI/budget/input hashes sent to authors", "author confirmation or objection, archived"),
    "18.09": ("independent reproducer (non-author, new machine)", "cold-start reproduction from the layered archive", "layered archive + clean machine", "full log from empty env to key tables/verification receipts"),
    "18.12": ("local agent (pre-submission only)", "refresh the latest literature", "frozen search date/databases/queries/inclusion-exclusion", "last-6-12-month results record"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    import pandas as pd

    frame = pd.read_csv(args.ledger, keep_default_na=False, dtype=str)
    non_pass = frame[frame["status"].isin({"FAIL", "EXTERNAL", "PARTIAL"})]
    rows = []
    unbound = []
    for record in non_pass.to_dict(orient="records"):
        metric_id = record["metric_id"]
        if metric_id in BLOCKERS:
            actor, action, required_input, acceptance = BLOCKERS[metric_id]
            rows.append({
                "metric_id": metric_id,
                "status": record["status"],
                "metric": record["metric"],
                "actor": actor,
                "action": action,
                "required_input": required_input,
                "acceptance_evidence": acceptance,
            })
        elif record["status"] in {"FAIL", "EXTERNAL"}:
            unbound.append(metric_id)

    if unbound:
        raise RuntimeError(f"FAIL/EXTERNAL metrics lack a blocker entry: {unbound}")

    rows.sort(key=lambda row: (row["status"], row["metric_id"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "metric_id", "status", "metric", "actor", "action",
            "required_input", "acceptance_evidence",
        ])
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "status": "PASS_EXTERNAL_BLOCKER_TABLE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "fail_rows": sum(1 for row in rows if row["status"] == "FAIL"),
        "external_rows": sum(1 for row in rows if row["status"] == "EXTERNAL"),
        "partial_rows": sum(1 for row in rows if row["status"] == "PARTIAL"),
        "note": (
            "PARTIAL rows are listed only when they carry an explicit external or "
            "user-authorization blocker; locally closable PARTIAL residuals stay in "
            "the ledger residual field. This table changes no ledger status."
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
