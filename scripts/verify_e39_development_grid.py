"""Independent verifier for the E39 development configuration grid."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "data" / "v12" / "e39_development_grid"
EXPECTED_ID = "E39_DEVELOPMENT_GRID_V1"
EXPECTED_CONFIGS = {
    f"b{beam}_c{cap}": (beam, cap)
    for cap in (64, 256)
    for beam in (1, 8, 32)
}
EXPECTED_STATUSES = {"success"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fail(message: str) -> None:
    raise SystemExit(f"E39_VERIFY_FAIL:{message}")


def main() -> int:
    protocol = read_json(OUTPUT_ROOT / "protocol.json")
    receipt = read_json(OUTPUT_ROOT / "receipt.json")
    selection = read_json(OUTPUT_ROOT / "selection.json")
    frozen = read_json(OUTPUT_ROOT / "frozen_algorithm_config.json")
    inputs = read_csv(OUTPUT_ROOT / "inputs.csv")
    rows = read_csv(OUTPUT_ROOT / "grid_results.csv")
    loo = read_csv(OUTPUT_ROOT / "leave_one_family_out.csv")
    summaries = read_json(OUTPUT_ROOT / "config_summaries.json")

    if protocol.get("experiment_id") != EXPECTED_ID or protocol.get("status") != "DEVELOPMENT_ONLY":
        fail("protocol_identity")
    if receipt.get("status") != "verified_development_grid":
        fail("receipt_status")
    if len(inputs) != 391 or len({row["input_circuit_sha256"] for row in inputs}) != 391:
        fail("input_count_or_uniqueness")
    families = {row["circuit_family"] for row in inputs}
    if len(families) != 15:
        fail("family_count")
    input_ids = {row["input_circuit_sha256"] for row in inputs}
    if len(rows) != 2346:
        fail("result_row_count")
    actual_protocol_configs = {
        (item.get("config_id"), item.get("beam_width"), item.get("candidate_cap"))
        for item in protocol.get("configurations", [])
    }
    expected_protocol_configs = {
        (key, value[0], value[1]) for key, value in EXPECTED_CONFIGS.items()
    }
    if actual_protocol_configs != expected_protocol_configs:
        fail("protocol_configurations")

    pair_counts = Counter((row["input_circuit_sha256"], row["config_id"]) for row in rows)
    if set(pair_counts) != {(input_hash, config_id) for input_hash in input_ids for config_id in EXPECTED_CONFIGS}:
        fail("input_config_grid")
    if any(count != 1 for count in pair_counts.values()):
        fail("duplicate_input_config_cell")

    for row in rows:
        if row["status"] not in EXPECTED_STATUSES:
            fail(f"unresolved_cell:{row['input_circuit_sha256']}:{row['config_id']}:{row['status']}")
        if row["config_id"] not in EXPECTED_CONFIGS:
            fail("unknown_config")
        beam, cap = EXPECTED_CONFIGS[row["config_id"]]
        if int(row["beam_width"]) != beam or int(row["candidate_cap"]) != cap:
            fail("cell_config_parameters")
        if int(row["certificate_lb"]) > int(row["certificate_ub"]):
            fail("certificate_bound_order")
        expected_effect = 100.0 * (float(row["reduction"]) - float(row["wcl_reduction"]))
        if abs(float(row["effect_pp"]) - expected_effect) > 1e-9:
            fail("effect_recomputation")
        if int(row["opportunity_positive"]) != int(int(row["certificate_ub"]) > 0):
            fail("opportunity_flag")

    if len(loo) != 6 * len(families):
        fail("loo_row_count")
    if {row["left_out_family"] for row in loo} != families:
        fail("loo_family_coverage")
    if any(int(row["left_out_input_count"]) != 391 - sum(1 for item in inputs if item["circuit_family"] == row["left_out_family"]) for row in loo):
        fail("loo_input_count")
    if len(summaries) != 6 or {row["config_id"] for row in summaries} != set(EXPECTED_CONFIGS):
        fail("summary_grid")
    if any(int(row["input_count"]) != 391 or int(row["error_count"]) != 0 for row in summaries):
        fail("summary_completeness")

    selected = selection.get("selected_config", {})
    selected_id = selected.get("config_id")
    if not selection.get("selection_is_frozen_for_e40") or selection.get("no_e40_result_used") is not True:
        fail("selection_freeze_contract")
    if selected_id not in EXPECTED_CONFIGS or frozen.get("selected_config_id") != selected_id:
        fail("frozen_selection_identity")
    if frozen.get("status") != "FROZEN_FOR_E40" or frozen.get("no_e40_result_used") is not True:
        fail("frozen_config_contract")
    beam, cap = EXPECTED_CONFIGS[selected_id]
    if frozen.get("beam_width") != beam or frozen.get("candidate_cap") != cap:
        fail("frozen_config_parameters")
    source_path = REPO_ROOT / frozen["source_module"]
    if frozen.get("source_module_sha256") != sha256_file(source_path):
        fail("frozen_source_hash")

    checks = {
        "protocol_sha256": sha256_file(OUTPUT_ROOT / "protocol.json"),
        "inputs_sha256": sha256_file(OUTPUT_ROOT / "inputs.csv"),
        "grid_results_sha256": sha256_file(OUTPUT_ROOT / "grid_results.csv"),
        "leave_one_family_out_sha256": sha256_file(OUTPUT_ROOT / "leave_one_family_out.csv"),
        "frozen_algorithm_config_sha256": sha256_file(OUTPUT_ROOT / "frozen_algorithm_config.json"),
    }
    if any(receipt.get(key) != value for key, value in checks.items()):
        fail("receipt_hashes")
    if receipt.get("input_count") != 391 or receipt.get("family_count") != 15 or receipt.get("result_rows") != 2346:
        fail("receipt_counts")

    result = {
        "status": "verified",
        "experiment_id": EXPECTED_ID,
        "input_count": len(inputs),
        "family_count": len(families),
        "configuration_count": len(EXPECTED_CONFIGS),
        "result_rows": len(rows),
        "error_count": sum(row["status"] != "success" for row in rows),
        "selected_config_id": selected_id,
        "source_module_sha256": frozen["source_module_sha256"],
        "grid_results_sha256": checks["grid_results_sha256"],
    }
    (OUTPUT_ROOT / "verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
