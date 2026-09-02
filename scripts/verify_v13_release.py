"""Fail-closed structural verifier for the stopped v13 release capsule."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    state_path = ROOT / "docs/review/v13_execution_state.json"
    verdict_path = ROOT / "release/v13_readiness_verdict.json"
    ledger_path = ROOT / "docs/review/v13_requirement_evidence_ledger.csv"
    e43_path = ROOT / "docs/review/v13_stage2_quartz_import_receipt.json"
    e44_path = ROOT / "data/v13/e44_certified_landscape_oracle/receipt.json"
    e45_path = ROOT / "docs/review/v13_stage5_e45_receipt.json"
    required = [state_path, verdict_path, ledger_path, e43_path, e44_path, e45_path]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    checks: dict[str, bool] = {"required_files": not missing}
    if missing:
        print(json.dumps({"status": "FAIL", "missing": missing}, sort_keys=True))
        return 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    e43 = json.loads(e43_path.read_text(encoding="utf-8"))
    e44 = json.loads(e44_path.read_text(encoding="utf-8"))
    e45 = json.loads(e45_path.read_text(encoding="utf-8"))
    ledger = list(csv.DictReader(ledger_path.open(newline="", encoding="utf-8")))
    checks.update({
        "state_stopped_at_s5": state.get("status") == "STAGE_S5_BLOCKED_RESOURCE_GATE",
        "verdict_not_ready": verdict.get("verdict") == "NOT_READY_FOR_PAPER",
        "e43_zero_tolerance": e43.get("status") == "PASS_STAGE_S2_E43" and e43.get("semantic_audit", {}).get("symbolic_mismatch_count") == 0 and e43.get("semantic_audit", {}).get("numeric_mismatch_count") == 0 and e43.get("semantic_audit", {}).get("non_equivalent_mutant_escapes") == 0,
        "e44_zero_tolerance": e44.get("status") == "PASS_STAGE_S4_E44" and e44.get("zero_tolerance") is True and e44.get("summary", {}).get("mismatch_count") == 0 and e44.get("summary", {}).get("replay_failures") == 0 and e44.get("summary", {}).get("determinism_failures") == 0,
        "e45_block_recorded": e45.get("status") == "BLOCKED_S5_RESOURCE_GATE" and e45.get("resource_gate", {}).get("certificate_guided_escape_eligible_configurations", 0) == 0,
        "future_panels_closed": e45.get("zero_tolerance_checks", {}).get("future_panel_access") is False and state.get("stage_5", {}).get("future_panels_opened") is False,
        "ledger_complete": len(ledger) == 11 and {row["status"] for row in ledger} >= {"PASS", "BLOCKED_RESOURCE_GATE", "NOT_OPENED"},
        "claim_boundary_present": bool(verdict.get("claim_boundary")),
    })
    # Ensure the stopped result is backed by the canonical E45 artifact hashes.
    checks["e45_artifact_hashes_match"] = all(
        sha256(ROOT / path) == digest
        for path, digest in (
            ("data/v13/e45_development_grid/protocol.json", e45["artifacts"]["protocol"]["sha256"]),
            ("data/v13/e45_development_grid/normalization_manifest.csv", e45["artifacts"]["normalization_manifest"]["sha256"]),
            ("data/v13/e45_development_grid/grid_results.csv", e45["artifacts"]["grid_results"]["sha256"]),
            ("data/v13/e45_development_grid/config_summaries.json", e45["artifacts"]["config_summaries"]["sha256"]),
            ("data/v13/e45_development_grid/selection.json", e45["artifacts"]["selection"]["sha256"]),
        )
    )
    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, "checks": checks, "ledger_rows": len(ledger)}, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
