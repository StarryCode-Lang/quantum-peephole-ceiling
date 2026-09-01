"""Independent verifier for E41 scale/resource evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v12" / "e41_rewrite_exposure_scale"
EXPECTED_ID = "E41_REWRITE_EXPOSURE_SCALE_V1"
ARMS = {"WCL_Greedy", "CGL_Greedy", "LBL_Phase2b", "CGL_Phase2b"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fail(message: str) -> None:
    raise SystemExit(f"E41_VERIFY_FAIL:{message}")


def main() -> int:
    protocol = read_json(OUT / "protocol.json")
    inputs = read_json(OUT / "inputs.json")
    summary = read_json(OUT / "summary.json")
    receipt = read_json(OUT / "receipt.json")
    rows = read_csv(OUT / "formal_results.csv")
    cell_files = sorted((OUT / "cells").glob("*.json"))
    cells = [read_json(path) for path in cell_files]

    if protocol.get("experiment_id") != EXPECTED_ID or protocol.get("status") != "FROZEN_BEFORE_EXECUTION":
        fail("protocol_identity")
    if len(inputs) != 16 or len({item["case_id"] for item in inputs}) != 16:
        fail("fixed_input_count")
    if sum(item["panel"] == "E33" for item in inputs) != 11 or sum(item["panel"] == "E35" for item in inputs) != 5:
        fail("panel_counts")
    if len(cells) != 16 or {cell.get("case_id") for cell in cells} != {item["case_id"] for item in inputs}:
        fail("cell_coverage")
    if any(item.get("source_observed_sha256") != item.get("qasm_sha256") for item in inputs):
        fail("input_hash_binding")
    if protocol.get("arms") != sorted(ARMS) and set(protocol.get("arms", [])) != ARMS:
        fail("arm_contract")
    if protocol.get("rss_cap_bytes") != 8 * 1024**3 or protocol.get("workers") != 1 or protocol.get("cold_process_per_cell") is not True:
        fail("resource_contract")
    if "never sampled fidelity" not in protocol.get("equivalence_policy", "").lower():
        fail("sampled_equivalence_policy")
    if len(rows) != sum(4 for cell in cells if cell.get("status") == "success"):
        fail("result_row_accounting")
    for cell in cells:
        if cell.get("status") == "success":
            if {arm.get("arm") for arm in cell.get("arms", [])} != ARMS:
                fail(f"arm_coverage:{cell.get('case_id')}")
            if any(arm.get("status") == "success" and arm.get("equivalence_status") not in {"exact_stabilizer", "exact_operator", "equivalence_unavailable"} for arm in cell.get("arms", [])):
                fail(f"equivalence_status:{cell.get('case_id')}")
        elif cell.get("status") not in {"resource_failure", "error"}:
            fail(f"unmarked_cell_failure:{cell.get('case_id')}:{cell.get('status')}")
    if summary.get("experiment_id") != EXPECTED_ID or summary.get("input_count") != 16 or summary.get("cell_count") != 16:
        fail("summary_contract")
    if summary.get("unmarked_semantic_failure_count") != 0:
        fail("unmarked_semantic_failure")
    receipt_checks = {
        "protocol_sha256": sha256(OUT / "protocol.json"),
        "inputs_sha256": sha256(OUT / "inputs.json"),
        "formal_results_sha256": sha256(OUT / "formal_results.csv"),
    }
    if any(receipt.get(key) != value for key, value in receipt_checks.items()):
        fail("receipt_hashes")
    for relative_path, expected_hash in protocol.get("source_hashes", {}).items():
        if sha256(ROOT / relative_path) != expected_hash:
            fail(f"source_hash:{relative_path}")

    result = {
        "status": "verified",
        "experiment_id": EXPECTED_ID,
        "input_count": len(inputs),
        "cell_count": len(cells),
        "successful_cells": sum(cell.get("status") == "success" for cell in cells),
        "resource_or_error_cells": sum(cell.get("status") != "success" for cell in cells),
        "formal_result_rows": len(rows),
        "unmarked_semantic_failure_count": summary["unmarked_semantic_failure_count"],
        "protocol_sha256": receipt_checks["protocol_sha256"],
    }
    (OUT / "verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
