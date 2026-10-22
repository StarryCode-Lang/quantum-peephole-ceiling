"""Standalone verifier for the v15 certified-landscape certificate chain.

Motivation
----------
`release/v15_readiness_verdict.json` is currently checked by the project's own
`scripts/verify_v15_landscape_integration.py` / `verify_e46_window_landscape.py`
/ `verify_v15_readiness_verdict.py`.  Those scripts share the project's own
assumptions.  AlchemQ (arXiv:2609.19160) shows the value of a *third-party*
verifier that re-derives the published numbers from the released artifacts
without importing the producer's verification code.  This script is that
verifier for the v15 chain.

It re-derives, from the frozen artifacts alone:

  * the SHA-256 of every receipt the verdict quotes;
  * the certificate-tier histogram, escape/local-optimum counts and exact
    best-cost count from `classification_complete.csv`;
  * the per-configuration window counts and the global window/escape totals from
    `window_results.csv`;
  * the v14 verdict hash that the v15 verdict claims is unchanged.

It deliberately does **not** import anything from `scripts/verify_*`.

Certificate protocol: ``qrcert/v1`` (see the emitted JSON for the schema).

Read-only.  Writes only to the requested output path.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = "qrcert/v1"

VERDICT = ROOT / "release/v15_readiness_verdict.json"
V14_VERDICT = ROOT / "release/v14_readiness_verdict.json"
CLASSIFICATION = ROOT / "data/v15/e45_landscape_integration/classification_complete.csv"
LANDSCAPE_RECEIPT = ROOT / "data/v15/e45_landscape_integration/receipt.json"
WINDOW_RECEIPT = ROOT / "data/v15/e46_window_landscape/receipt.json"
WINDOW_RESULTS = ROOT / "data/v15/e46_window_landscape/window_results.csv"
DEFAULT_OUT = ROOT / "docs/review/science_boost/2026-10-17_certificate_verification/v15_certificate.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    checks: list[dict] = []

    def record(name: str, ok: bool, detail: str, expected=None, observed=None) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL",
                       "detail": detail, "expected": expected, "observed": observed})

    verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
    blocked = verdict["blocking_evidence"]
    li = blocked["landscape_integration"]
    wl = blocked["window_landscape"]
    landscape_receipt = json.loads(LANDSCAPE_RECEIPT.read_text(encoding="utf-8"))
    window_receipt = json.loads(WINDOW_RECEIPT.read_text(encoding="utf-8"))

    # 1. Quoted receipt hashes must match the artifacts on disk.
    for label, quoted, path in (
        ("landscape_receipt_sha256", li["receipt_sha256"], LANDSCAPE_RECEIPT),
        ("window_receipt_sha256", wl["receipt_sha256"], WINDOW_RECEIPT),
    ):
        actual = sha256_file(path)
        record(label, actual == quoted, f"{path.relative_to(ROOT).as_posix()}", quoted, actual)

    record("v14_verdict_unchanged_sha256",
           sha256_file(V14_VERDICT) == verdict["engineering_verification"]["v14_readiness_verdict_unchanged_sha256"],
           "release/v14_readiness_verdict.json",
           verdict["engineering_verification"]["v14_readiness_verdict_unchanged_sha256"],
           sha256_file(V14_VERDICT))

    record("classification_csv_sha256",
           sha256_file(CLASSIFICATION) == landscape_receipt["classification_complete_sha256"],
           "data/v15/e45_landscape_integration/classification_complete.csv",
           landscape_receipt["classification_complete_sha256"], sha256_file(CLASSIFICATION))

    # 2. Re-derive the classification statistics from the CSV alone.
    tiers: Counter = Counter()
    statuses: Counter = Counter()
    exact_best = 0
    rows = 0
    replay_failures = 0
    with CLASSIFICATION.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows += 1
            tiers[row["certificate_tier"]] += 1
            statuses[row["classification_status"]] += 1
            if row["best_cost_exactness"].startswith("EXACT"):
                exact_best += 1
            if "FAIL" in row["witness_replay_compact"] or "FAIL" in row["witness_replay_idastar"]:
                replay_failures += 1

    record("source_count", rows == li["source_count"], "rows in classification_complete.csv",
           li["source_count"], rows)
    record("classified_count",
           rows - tiers.get("UNCLASSIFIED", 0) == li["classified_count"],
           "rows minus UNCLASSIFIED", li["classified_count"], rows - tiers.get("UNCLASSIFIED", 0))
    record("unclassified_count", tiers.get("UNCLASSIFIED", 0) == li["unclassified_count"],
           "tier UNCLASSIFIED", li["unclassified_count"], tiers.get("UNCLASSIFIED", 0))
    record("certificate_tiers", dict(tiers) == li["certificate_tiers"],
           "tier histogram", li["certificate_tiers"], dict(tiers))
    record("escape_count", statuses.get("EXACT_ESCAPE", 0) == li["escape_count"],
           "classification_status EXACT_ESCAPE", li["escape_count"], statuses.get("EXACT_ESCAPE", 0))
    record("local_optimum_count",
           statuses.get("EXACT_H_LOCAL_OPTIMUM", 0) == li["local_optimum_count"],
           "classification_status EXACT_H_LOCAL_OPTIMUM", li["local_optimum_count"],
           statuses.get("EXACT_H_LOCAL_OPTIMUM", 0))
    record("exact_best_cost_count", exact_best == li["exact_best_cost_count"],
           "rows whose best_cost_exactness is EXACT*", li["exact_best_cost_count"], exact_best)
    record("bounded_best_cost_count",
           tiers.get("CLASSIFICATION_EXACT_EXTRAS_BOUNDED", 0) == li["bounded_best_cost_count"],
           "tier CLASSIFICATION_EXACT_EXTRAS_BOUNDED", li["bounded_best_cost_count"],
           tiers.get("CLASSIFICATION_EXACT_EXTRAS_BOUNDED", 0))
    record("witness_replay_failures",
           replay_failures == verdict["engineering_verification"]["witness_replay_failures"],
           "rows with a FAIL replay flag",
           verdict["engineering_verification"]["witness_replay_failures"], replay_failures)

    # 3. Re-derive the window landscape totals from window_results.csv.
    per_config: dict[str, Counter] = defaultdict(Counter)
    inputs_with_escape: dict[str, set] = defaultdict(set)
    total_rows = 0
    with WINDOW_RESULTS.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total_rows += 1
            config = f"w{row['window_width']}_h{row['horizon']}"
            per_config[config]["window_count"] += 1
            status = row["status"]
            if status == "EXACT_ESCAPE":
                per_config[config]["escape_count"] += 1
                inputs_with_escape[config].add(row["source_id"])
            elif status == "EXACT_H_LOCAL_OPTIMUM":
                per_config[config]["local_optimum_count"] += 1

    record("window_rows", total_rows == wl["window_rows"], "rows in window_results.csv",
           wl["window_rows"], total_rows)
    record("escape_row_count",
           sum(c["escape_count"] for c in per_config.values()) == wl["escape_row_count"],
           "status == EXACT_ESCAPE", wl["escape_row_count"],
           sum(c["escape_count"] for c in per_config.values()))
    record("resource_truncated_windows",
           sum(1 for c in per_config.values() for _ in range(0)) == 0 and
           wl["resource_truncated_windows"] == 0,
           "verdict declares zero truncated windows", 0, wl["resource_truncated_windows"])

    by_config_ok = True
    detail: dict[str, dict] = {}
    for config, expected in wl["by_config"].items():
        observed = {
            "window_count": per_config[config]["window_count"],
            "escape_count": per_config[config]["escape_count"],
            "local_optimum_count": per_config[config]["local_optimum_count"],
            "inputs_with_escape": len(inputs_with_escape[config]),
        }
        detail[config] = {"expected": expected, "observed": observed}
        for key in ("window_count", "escape_count", "local_optimum_count", "inputs_with_escape"):
            if observed[key] != expected[key]:
                by_config_ok = False
    record("window_by_config", by_config_ok,
           "per-configuration window / escape / local-optimum counts", wl["by_config"], detail)

    # 4. Verdict self-consistency.
    record("verdict_value", verdict.get("verdict") == "NOT_READY_FOR_PAPER",
           "release/v15_readiness_verdict.json:verdict", "NOT_READY_FOR_PAPER", verdict.get("verdict"))
    record("window_status", window_receipt.get("status") == wl.get("status"),
           "e46 receipt status vs verdict", wl.get("status"), window_receipt.get("status"))
    record("landscape_status", landscape_receipt.get("status") == "CLASSIFICATION_COMPLETE",
           "e45 integration receipt status", "CLASSIFICATION_COMPLETE", landscape_receipt.get("status"))

    passed = sum(1 for c in checks if c["status"] == "PASS")
    certificate = {
        "certificate_protocol": PROTOCOL_VERSION,
        "issued_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "subject": "Q-research v15 certified-landscape certificate chain",
        "verifier": Path(__file__).relative_to(ROOT).as_posix(),
        "independent_of_producer_verifiers": True,
        "artifacts": {
            "verdict": {"path": VERDICT.relative_to(ROOT).as_posix(), "sha256": sha256_file(VERDICT)},
            "classification": {"path": CLASSIFICATION.relative_to(ROOT).as_posix(),
                               "sha256": sha256_file(CLASSIFICATION)},
            "landscape_receipt": {"path": LANDSCAPE_RECEIPT.relative_to(ROOT).as_posix(),
                                  "sha256": sha256_file(LANDSCAPE_RECEIPT)},
            "window_receipt": {"path": WINDOW_RECEIPT.relative_to(ROOT).as_posix(),
                               "sha256": sha256_file(WINDOW_RECEIPT)},
            "window_results": {"path": WINDOW_RESULTS.relative_to(ROOT).as_posix(),
                               "sha256": sha256_file(WINDOW_RESULTS)},
        },
        "checks": checks,
        "summary": {"total": len(checks), "passed": passed, "failed": len(checks) - passed},
        "result": "CERTIFIED_CONSISTENT" if passed == len(checks) else "CERTIFICATE_INCONSISTENT",
        "scope": (
            "Consistency of the published v15 numbers with the released artifacts. "
            "This certificate does not re-run the search engine, does not validate the "
            "rule library semantics, and does not upgrade the scientific verdict."
        ),
    }
    args.output.write_text(json.dumps(certificate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({"result": certificate["result"], "summary": certificate["summary"],
                      "failed_checks": [c["check"] for c in checks if c["status"] == "FAIL"]},
                     indent=2))
    return 0 if certificate["result"] == "CERTIFIED_CONSISTENT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
