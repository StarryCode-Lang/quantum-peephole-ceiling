"""Fail-closed verifier for the v14 selected-configuration exact package."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.optimisation.certified_landscape import sha256_json  # noqa: E402


DEFAULT_OUTPUT = ROOT / "data" / "v14" / "e45_full_development"
SCREENING_MANIFEST = ROOT / "data" / "v14" / "e45_development_grid" / "normalization_manifest.csv"
EXPECTED_ARMS = {
    "greedy",
    "wcl_greedy",
    "v12_cgl_greedy",
    "phase2b_greedy",
    "unguided_beam",
    "certificate_guided_escape",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output_root.resolve()
    required = [
        output / "protocol.json",
        output / "normalization_manifest.csv",
        output / "grid_results.csv",
        output / "config_summaries.json",
        output / "certificates.jsonl",
        output / "selection.json",
        output / "receipt.json",
        SCREENING_MANIFEST,
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        print(json.dumps({"status": "FAIL", "missing": missing}, sort_keys=True))
        return 1

    protocol = read_json(output / "protocol.json")
    selection = read_json(output / "selection.json")
    screening_selection = read_json(ROOT / "data/v14/e45_development_grid/selection.json")
    receipt = read_json(output / "receipt.json")
    summaries = read_json(output / "config_summaries.json")
    with (output / "normalization_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    with SCREENING_MANIFEST.open(newline="", encoding="utf-8") as handle:
        screening_manifest = list(csv.DictReader(handle))
    with (output / "grid_results.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    # Certificates contain the complete finite-horizon state hash set and can
    # be tens of megabytes even for the bounded panel.  Stream the JSONL and
    # retain only the fields needed by the cross-artifact checks so validation
    # remains executable under the declared low-memory environment.
    certificate_metadata: dict[str, dict[str, Any]] = {}
    certificate_hashes_valid = True
    no_false_exact_status = True
    certificate_count = 0
    with (output / "certificates.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            certificate = item["certificate"]
            source_id = item.get("source_id")
            certificate_count += 1
            certificate_metadata[source_id] = {
                "status": certificate.get("status"),
                "best_cost": certificate.get("best_cost"),
                "resource_status": certificate.get("resource_status"),
                "exactness_status": certificate.get("exactness_status"),
            }
            no_false_exact_status = no_false_exact_status and not (
                certificate.get("resource_status") == "TRUNCATED"
                and certificate.get("status") in {"EXACT_H_LOCAL_OPTIMUM", "EXACT_ESCAPE"}
            )
            certificate_hashes_valid = certificate_hashes_valid and (
                certificate.get("certificate_sha256")
                == sha256_json({key: value for key, value in certificate.items() if key != "certificate_sha256"})
            )

    source_count = len(manifest)
    exact_rows = [row for row in rows if row.get("arm") == "certificate_guided_escape"]
    cert_by_source = certificate_metadata
    selected_config = selection.get("selected_config", {})
    screening_config = screening_selection.get("selected_config", {})
    selected_config_fields = ("config_id", "horizon", "beam_width", "state_budget", "barrier_cap")
    selected_config_shape = isinstance(selected_config, dict) and all(
        key in selected_config for key in selected_config_fields
    )
    screening_selection_matches = (
        selected_config_shape
        and (
            protocol.get("phase") == "smoke"
            or (
                isinstance(screening_config, dict)
                and all(selected_config.get(key) == screening_config.get(key) for key in selected_config_fields)
            )
        )
    )
    checks = {
        "protocol_status": protocol.get("status") == "DEVELOPMENT_ONLY",
        "phase_declared": protocol.get("phase") in {"full_development", "smoke"},
        "full_panel_cardinality": protocol.get("phase") == "smoke" or source_count == 128,
        "exact_method": protocol.get("search_method", {}).get("id") == "exact_compact_bfs_v2",
        "selected_config": screening_selection_matches,
        "arm_set": set(protocol.get("arms", [])) == EXPECTED_ARMS and {row.get("arm") for row in rows} == EXPECTED_ARMS,
        "source_scope_prefix": [row.get("source_sha256") for row in manifest] == [row.get("source_sha256") for row in screening_manifest[:source_count]],
        "screening_manifest_hash": protocol.get("source_contract", {}).get("screening_manifest_sha256") == sha256(SCREENING_MANIFEST),
        "selection_phase_matches_protocol": selection.get("phase") == protocol.get("phase"),
        "row_cardinality": len(rows) == source_count * len(EXPECTED_ARMS) and len(exact_rows) == source_count,
        "certificate_cardinality": certificate_count == source_count and set(cert_by_source) == {row.get("source_id") for row in manifest},
        "receipt_cardinality": receipt.get("source_count") == source_count and receipt.get("normalized_count") == source_count and receipt.get("result_rows") == len(rows) and receipt.get("configuration_count") == 1 and receipt.get("arm_count") == len(EXPECTED_ARMS),
        "summary_cardinality": len(summaries) == len(EXPECTED_ARMS) and all(row.get("row_count") == source_count for row in summaries),
        "no_unmarked_semantic_failure": all(row.get("semantic_status") not in {"SEMANTIC_FAILURE", "NOT_AVAILABLE"} for row in rows),
    }
    # Keep the exact certificate and result row joined by source and status.
    checks["exact_rows_join_certificates"] = all(
        row["source_id"] in cert_by_source
        and row["certificate_status"] == cert_by_source[row["source_id"]]["status"]
        and int(row["output_gate_count"]) == int(cert_by_source[row["source_id"]]["best_cost"])
        and (
            cert_by_source[row["source_id"]]["resource_status"] == "COMPLETE"
            or cert_by_source[row["source_id"]]["exactness_status"] == "INCOMPLETE"
        )
        for row in exact_rows
    )
    checks["no_false_exact_status"] = no_false_exact_status
    checks["certificate_hashes"] = certificate_hashes_valid
    checks["artifact_hashes"] = all(
        receipt.get(key) == sha256(output / filename)
        for key, filename in {
            "protocol_sha256": "protocol.json",
            "normalization_manifest_sha256": "normalization_manifest.csv",
            "grid_results_sha256": "grid_results.csv",
            "config_summaries_sha256": "config_summaries.json",
            "certificates_sha256": "certificates.jsonl",
            "selection_sha256": "selection.json",
        }.items()
    )
    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, "checks": checks, "source_count": source_count, "result_rows": len(rows)}, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
