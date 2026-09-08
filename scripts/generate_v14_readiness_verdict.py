"""Derive the v14 readiness verdict from receipt-bound screening and development artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import argparse
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V14 = ROOT / "data" / "v14" / "e45_development_grid"
FULL = ROOT / "data" / "v14" / "e45_full_development"
V13 = ROOT / "data" / "v13" / "e45_development_grid"
V13_VERDICT = ROOT / "release" / "v13_readiness_verdict.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(reason: str) -> None:
    raise SystemExit(f"V14_VERDICT_DERIVATION_FAIL:{reason}")


def load_full_development() -> dict[str, Any]:
    required = {
        "protocol": FULL / "protocol.json",
        "normalization_manifest": FULL / "normalization_manifest.csv",
        "grid_results": FULL / "grid_results.csv",
        "config_summaries": FULL / "config_summaries.json",
        "certificates": FULL / "certificates.jsonl",
        "selection": FULL / "selection.json",
        "receipt": FULL / "receipt.json",
    }
    present = [path.is_file() for path in required.values()]
    if not any(present):
        return {"status": "PENDING"}
    if not all(present):
        fail("full_development_partial_package")

    protocol = read_json(required["protocol"])
    receipt = read_json(required["receipt"])
    selection = read_json(required["selection"])
    summaries = read_json(required["config_summaries"])
    with required["normalization_manifest"].open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    with required["grid_results"].open(newline="", encoding="utf-8") as handle:
        results = list(csv.DictReader(handle))
    certificate_count = 0
    truncated = 0
    exact = 0
    with required["certificates"].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            certificate = json.loads(line).get("certificate", {})
            certificate_count += 1
            truncated += certificate.get("resource_status") == "TRUNCATED"
            exact += certificate.get("exactness_status") == "EXACT_FINITE_HORIZON"
    if protocol.get("phase") != "full_development" or receipt.get("source_count") != 128:
        fail("full_development_scope")
    if receipt.get("result_rows") != 768 or len(manifest) != 128 or len(results) != 768 or certificate_count != 128:
        fail("full_development_cardinality")
    if selection.get("source_count") != 128 or selection.get("phase") != "full_development":
        fail("full_development_selection")
    for key, path in required.items():
        if key == "receipt":
            continue
        receipt_key = f"{key}_sha256"
        if receipt.get(receipt_key) != sha256(path):
            fail(f"full_development_hash:{key}")
    guided = next((row for row in summaries if row.get("arm") == "certificate_guided_escape"), None)
    if guided is None:
        fail("full_development_guided_summary")
    artifacts = {
        key: {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(path),
            "selector": f"$.{key}_sha256",
            "predicate": "verify_e45_exact_development.py --output-root data/v14/e45_full_development exits 0",
        }
        for key, path in required.items()
        if key != "receipt"
    }
    return {
        "status": receipt.get("status"),
        "phase": protocol.get("phase"),
        "source_count": receipt.get("source_count"),
        "result_rows": receipt.get("result_rows"),
        "selected_config": receipt.get("selected_config", {}).get("config_id"),
        "resource_bounded_rows": truncated,
        "exact_finite_horizon_certificates": exact,
        "semantic_failure_count": guided.get("semantic_failure_count"),
        "resource_or_error_rate": guided.get("resource_or_error_rate"),
        "receipt_sha256": sha256(required["receipt"]),
        "artifacts": artifacts,
    }


def main() -> int:
    receipt_path = V14 / "receipt.json"
    selection_path = V14 / "selection.json"
    summaries_path = V14 / "config_summaries.json"
    manifest_path = V14 / "normalization_manifest.csv"
    results_path = V14 / "grid_results.csv"
    required = (receipt_path, selection_path, summaries_path, manifest_path, results_path, V13 / "normalization_manifest.csv", V13_VERDICT)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        fail("missing:" + ",".join(missing))

    receipt = read_json(receipt_path)
    selection = read_json(selection_path)
    summaries = read_json(summaries_path)
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    with results_path.open(newline="", encoding="utf-8") as handle:
        results = list(csv.DictReader(handle))
    with (V13 / "normalization_manifest.csv").open(newline="", encoding="utf-8") as handle:
        v13_manifest = list(csv.DictReader(handle))

    guided = [row for row in summaries if row.get("arm") == "certificate_guided_escape"]
    if receipt.get("status") != "SCREENING_COMPLETE_SELECTION_PENDING_FULL_DEVELOPMENT":
        fail("receipt_status")
    if receipt.get("experiment_id") != "E45_CERTIFIED_ESCAPE_DEVELOPMENT_V14":
        fail("experiment_id")
    if len(manifest) != 128 or len(v13_manifest) != 128:
        fail("manifest_cardinality")
    if [row.get("source_sha256") for row in manifest] != [row.get("source_sha256") for row in v13_manifest]:
        fail("source_scope")
    if len(guided) != 18 or len(results) != 13_824:
        fail("panel_cardinality")
    if len({row.get("status") for row in results if row.get("arm") == "certificate_guided_escape"} & {"EXACT_ESCAPE", "EXACT_H_LOCAL_OPTIMUM"}):
        fail("exact_claim_in_beam_arm")
    if any(float(row.get("resource_or_error_rate", "1")) > 0.05 or int(row.get("semantic_failure_count", "1")) != 0 for row in guided):
        fail("resource_gate")

    selected = selection["selected_config"]
    full_development = load_full_development()
    receipt_artifacts = {
        "protocol": {"path": "data/v14/e45_development_grid/protocol.json", "sha256": receipt["protocol_sha256"], "selector": "$.protocol_sha256", "predicate": "verify_e45_development_grid.py --output-root data/v14/e45_development_grid exits 0"},
        "normalization_manifest": {"path": "data/v14/e45_development_grid/normalization_manifest.csv", "sha256": receipt["normalization_manifest_sha256"], "selector": "$.source_count and source_sha256 order", "predicate": "manifest has 128 rows and exact source_sha256 order of the sealed v13 panel"},
        "grid_results": {"path": "data/v14/e45_development_grid/grid_results.csv", "sha256": receipt["grid_results_sha256"], "selector": "$.result_rows", "predicate": "CSV has 13,824 rows and zero semantic failures in the guided arm"},
        "config_summaries": {"path": "data/v14/e45_development_grid/config_summaries.json", "sha256": receipt["config_summaries_sha256"], "selector": "$.selection.eligible_config_count", "predicate": "all 18 guided configurations have resource_or_error_rate <= 0.05"},
        "selection": {"path": "data/v14/e45_development_grid/selection.json", "sha256": receipt["selection_sha256"], "selector": "$.selected_config.config_id", "predicate": "selection status is screening-complete and selection_is_frozen_for_e48 is false"},
    }
    verdict = {
        "schema_version": "v14-readiness-verdict-v1",
        "verdict": "NOT_READY_FOR_PAPER",
        "project": "Q-research v14 certified landscape screening",
        "as_of": "2026-09-08",
        "derivation": {
            "script": "scripts/generate_v14_readiness_verdict.py",
            "metric_id": "E45.v14.S5.screening_resource_gate",
            "state_upgrade_predicate": "python scripts/verify_v14_readiness_verdict.py exits 0 and every guided configuration has resource_or_error_rate <= 0.05 with zero semantic failures",
            "evidence": list(receipt_artifacts.values()),
        },
        "engineering_verification": {
            "v14_e45_verifier": "PASS",
            "source_scope_matches_sealed_v13": True,
            "v13_readiness_verdict_unchanged_sha256": sha256(V13_VERDICT),
            "semantic_failures_in_guided_arm": 0,
        },
        "scientific_gates": {
            "S0_to_S4": "INHERITED_WITH_BOUNDARIES",
            "S5_E45_v14_screening": "PASS_RESOURCE_GATE_WITH_BOUNDARIES",
            "S5_E45_full_development": "COMPLETE_WITH_RESOURCE_BOUNDARY" if full_development["status"] != "PENDING" else "PENDING",
            "EXACT_CERTIFIED_LANDSCAPE": "NOT_ESTABLISHED",
            "C3_title_and_positioning": "USER_DECISION_PENDING",
            "external_cold_start": "OPEN",
            "real_qpu": "OPEN",
            "release_authority": "OPEN",
        },
        "blocking_evidence": {
            "receipt": receipt_artifacts,
            "source_count": receipt["source_count"],
            "configuration_count": receipt["configuration_count"],
            "arm_count": receipt["arm_count"],
            "result_rows": receipt["result_rows"],
            "guided_rows": len(guided) * 128,
            "guided_resource_bounded_rows": sum(int(row["resource_bounded_count"]) for row in guided),
            "guided_resource_or_error_rate_max": max(float(row["resource_or_error_rate"]) for row in guided),
            "required_max_rate": 0.05,
            "eligible_config_count": selection["eligible_config_count"],
            "selected_config": selected["config_id"],
            "selected_config_resource_or_error_rate": selected["resource_or_error_rate"],
            "selection_is_frozen_for_e48": selection["selection_is_frozen_for_e48"],
            "v13_readiness_verdict": "release/v13_readiness_verdict.json",
            "full_development": full_development,
        },
        "claim_boundary": (
            "The v14 result establishes a fixed 128-source screening resource gate and a full "
            f"selected-configuration development panel with {full_development['exact_finite_horizon_certificates']} "
            f"complete finite-horizon certificates and {full_development['resource_bounded_rows']} "
            "resource-truncated cells. It does not establish a complete exact landscape over all 128 sources, "
            "a confirmatory advantage, or a paper-ready landscape claim."
        ),
        "paper_status": (
            "Do not claim v14 certified-landscape completion or complete exact landscape quantities: "
            f"{full_development['resource_bounded_rows']} of {full_development['source_count']} selected-configuration "
            "development cells remain resource-truncated, and external cold-start, real-QPU, title, and release "
            "gates remain open."
        ),
    }
    rendered = json.dumps(verdict, indent=2, sort_keys=True) + "\n"
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
