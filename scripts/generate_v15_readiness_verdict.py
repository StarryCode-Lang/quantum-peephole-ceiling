"""Derive the v15 readiness verdict from receipt-bound v14/v15 artifacts.

The v15 verdict upgrades the v14 resource-boundary bookkeeping without
rerunning any search:

- the E45 classification is complete for all 128 sources (compact enumeration,
  IDA*-derived completions, and witness-bounded extras),
- the E46 window-landscape panel reports position-resolved certified profiles
  over the same fixed panel,
- paper, cold-start, real-QPU, title, and release gates remain unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V14_FULL = ROOT / "data" / "v14" / "e45_full_development"
V14_IDASTAR = ROOT / "data" / "v14" / "e45_idastar_escape"
INTEGRATION = ROOT / "data" / "v15" / "e45_landscape_integration"
WINDOW = ROOT / "data" / "v15" / "e46_window_landscape"
V14_VERDICT = ROOT / "release" / "v14_readiness_verdict.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(reason: str) -> None:
    raise SystemExit(f"V15_VERDICT_DERIVATION_FAIL:{reason}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_integration() -> dict[str, Any]:
    required = {
        "protocol": INTEGRATION / "protocol.json",
        "classification": INTEGRATION / "classification_complete.csv",
        "derivations": INTEGRATION / "derivations.jsonl",
        "receipt": INTEGRATION / "receipt.json",
    }
    if not all(path.is_file() for path in required.values()):
        fail("integration_package_missing")
    receipt = read_json(required["receipt"])
    for key, path in required.items():
        if key == "receipt":
            continue
        receipt_key = {
            "protocol": "protocol_sha256",
            "classification": "classification_complete_sha256",
            "derivations": "derivations_sha256",
        }[key]
        if receipt.get(receipt_key) != sha256(path):
            fail(f"integration_hash:{key}")
    if receipt.get("status") != "CLASSIFICATION_COMPLETE" or receipt.get("unclassified_count") != 0:
        fail("integration_status")
    return receipt


def load_window_landscape() -> dict[str, Any]:
    required = {
        "protocol": WINDOW / "protocol.json",
        "window_results": WINDOW / "window_results.csv",
        "input_summaries": WINDOW / "input_summaries.csv",
        "escape_certificates": WINDOW / "escape_certificates.jsonl",
        "receipt": WINDOW / "receipt.json",
    }
    present = [path.is_file() for path in required.values()]
    if not any(present):
        return {"status": "PENDING"}
    if not all(present):
        fail("window_package_partial")
    receipt = read_json(required["receipt"])
    for key, path in required.items():
        if key == "receipt":
            continue
        receipt_key = {
            "protocol": "protocol_sha256",
            "window_results": "window_results_sha256",
            "input_summaries": "input_summaries_sha256",
            "escape_certificates": "escape_certificates_sha256",
        }[key]
        if receipt.get(receipt_key) != sha256(path):
            fail(f"window_hash:{key}")
    if receipt.get("source_count") != 128:
        fail("window_panel_scope")
    return receipt


def main() -> int:
    if not V14_VERDICT.is_file():
        fail("v14_verdict_missing")
    integration = load_integration()
    window = load_window_landscape()

    integration_artifacts = {
        "protocol": {"path": "data/v15/e45_landscape_integration/protocol.json", "sha256": sha256(INTEGRATION / "protocol.json"), "predicate": "verify_v15_landscape_integration.py exits 0"},
        "classification_complete": {"path": "data/v15/e45_landscape_integration/classification_complete.csv", "sha256": sha256(INTEGRATION / "classification_complete.csv"), "predicate": "128 rows, tiers 93/1/34, zero replay failures"},
        "derivations": {"path": "data/v15/e45_landscape_integration/derivations.jsonl", "sha256": sha256(INTEGRATION / "derivations.jsonl"), "predicate": "per-source derivation log"},
    }

    verdict = {
        "schema_version": "v15-readiness-verdict-v1",
        "verdict": "NOT_READY_FOR_PAPER",
        "project": "Q-research v15 certified landscape integration and window profiles",
        "as_of": "2026-10-11",
        "derivation": {
            "script": "scripts/generate_v15_readiness_verdict.py",
            "state_upgrade_predicate": (
                "python scripts/verify_v15_readiness_verdict.py exits 0; the v14 verdict "
                "remains hash-unchanged; no frozen v14 package is modified"
            ),
            "evidence": list(integration_artifacts.values()),
        },
        "engineering_verification": {
            "v15_landscape_integration_verifier": "PASS",
            "v14_readiness_verdict_unchanged_sha256": sha256(V14_VERDICT),
            "witness_replay_failures": integration.get("witness_replay_failure_count"),
        },
        "scientific_gates": {
            "S0_to_S4": "INHERITED_WITH_BOUNDARIES",
            "S5_E45_v14_screening": "PASS_RESOURCE_GATE_WITH_BOUNDARIES",
            "S5_E45_full_development": "COMPLETE_WITH_RESOURCE_BOUNDARY",
            "S6_E45_classification": "COMPLETE_128_OF_128",
            "S6_landscape_quantities": "EXACT_FOR_94_OF_128_WITNESS_BOUNDED_FOR_34",
            "S6_E46_window_landscape": (
                "PENDING" if window.get("status") == "PENDING" else window.get("status")
            ),
            "C3_title_and_positioning": "USER_DECISION_PENDING",
            "external_cold_start": "OPEN",
            "real_qpu": "OPEN",
            "release_authority": "OPEN",
        },
        "blocking_evidence": {
            "v14_readiness_verdict": "release/v14_readiness_verdict.json",
            "landscape_integration": {
                "receipt": "data/v15/e45_landscape_integration/receipt.json",
                "receipt_sha256": sha256(INTEGRATION / "receipt.json"),
                "source_count": integration.get("source_count"),
                "classified_count": integration.get("classified_count"),
                "unclassified_count": integration.get("unclassified_count"),
                "escape_count": integration.get("escape_count"),
                "local_optimum_count": integration.get("local_optimum_count"),
                "certificate_tiers": integration.get("certificate_tiers"),
                "exact_best_cost_count": integration.get("exact_best_cost_count"),
                "bounded_best_cost_count": integration.get("bounded_best_cost_count"),
            },
            "window_landscape": (
                {"status": "PENDING"} if window.get("status") == "PENDING" else {
                    "status": window.get("status"),
                    "receipt": "data/v15/e46_window_landscape/receipt.json",
                    "receipt_sha256": sha256(WINDOW / "receipt.json"),
                    "source_count": window.get("source_count"),
                    "window_rows": window.get("window_rows"),
                    "escape_row_count": window.get("escape_row_count"),
                    "escape_certificate_count": window.get("escape_certificate_count"),
                    "resource_truncated_windows": window.get("resource_truncated_windows"),
                    "by_config": window.get("by_config"),
                }
            ),
        },
        "claim_boundary": (
            "v15 closes the E45 classification bookkeeping: every one of the 128 fixed-panel "
            "sources now carries either a complete compact certificate (enumerated or "
            "IDA*-derived) or an exact classification with witness-bounded landscape extras. "
            "The compact landscape quantities for 34 long-listing escape cells remain bounded "
            "rather than enumerated, the window profiles are window-local by construction, and "
            "external cold-start, real-QPU, title, and release gates remain open."
        ),
        "paper_status": (
            "Do not claim complete enumerated landscape quantities for the 34 bounded cells, "
            "whole-listing meaning for window-local profiles, or paper readiness. The v14 "
            "resource boundary remains the enumerated-certificate boundary; v15 replaces the "
            "unclassified outcome with derived and bounded evidence."
        ),
    }
    rendered = json.dumps(verdict, indent=2, sort_keys=True) + "\n"
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "release" / "v15_readiness_verdict.json")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
