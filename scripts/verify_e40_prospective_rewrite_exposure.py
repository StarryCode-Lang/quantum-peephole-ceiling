"""Independent verifier for the E40 prospective MQT panel."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v12" / "e40_prospective_rewrite_exposure"
EXPERIMENT_ID = "E40_PROSPECTIVE_REWRITE_EXPOSURE_V1"
IDS = {
    "ae", "bmw_quark_cardinality", "bmw_quark_copula", "cdkm_ripple_carry_adder",
    "dj", "draper_qft_adder", "full_adder", "graphstate", "half_adder", "hhl",
    "hrs_cumulative_multiplier", "iqpe", "modular_adder", "multiplier",
    "qftentangled", "qnn", "qpeexact", "qpeinexact", "rg_qft_multiplier",
    "seven_qubit_steane_code", "shor", "shors_nine_qubit_code",
    "vbe_ripple_carry_adder", "wstate",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str) -> dict[str, Any]:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def load_csv(name: str) -> list[dict[str, str]]:
    with (OUT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fail(reason: str) -> None:
    raise SystemExit(f"E40_VERIFY_FAIL:{reason}")


def main() -> int:
    generation = load_json("generation_manifest.json")
    protocol = load_json("protocol.json")
    summary = load_json("summary.json")
    receipt = load_json("receipt.json")
    attempts = load_csv("generator_attempts.csv")
    inputs = load_csv("inputs.csv")
    classification = load_csv("classification.csv")
    formal = load_csv("formal_results.csv")
    checkpoint_path = OUT / "checkpoint.sqlite3"

    if generation.get("experiment_id") != EXPERIMENT_ID or generation.get("mqt_bench_version") != "2.2.3" or generation.get("qiskit_version") != "2.5.2":
        fail("generation_environment")
    if set(generation.get("generator_ids", [])) != IDS or generation.get("declared_sizes") != list(range(4, 11)):
        fail("fixed_generator_panel")
    if generation.get("attempt_count") != 168 or len(attempts) != 168:
        fail("attempt_count")
    if len(inputs) != 24 or {row.get("benchmark") for row in inputs} != IDS:
        fail("input_family_count")
    if len(classification) != 24 or {row.get("benchmark") for row in classification} != IDS:
        fail("classification_family_count")
    if any(row.get("panel_status") != "no_eligible_input" for row in inputs):
        fail("unexpected_eligible_input")
    if any(row.get("classification") != "unavailable" or row.get("opportunity_positive") != "0" or row.get("robust_zero_control") != "0" for row in classification):
        fail("unavailable_classification")
    if generation.get("eligible_family_count") != 0:
        fail("eligible_count_drift")
    if protocol.get("experiment_id") != EXPERIMENT_ID or protocol.get("status") != "FROZEN_BEFORE_FORMAL_EXECUTION":
        fail("protocol_identity")
    if protocol.get("generator_environment") != {"mqt.bench": "2.2.3", "qiskit_generation": "2.5.2", "qiskit_core": "2.4.1"}:
        fail("protocol_environment")
    if protocol.get("arms") != ["LBL_Greedy", "WCL_Greedy", "RandomTopological32_Greedy", "CGL_Greedy", "LBL_Phase2b", "CGL_Phase2b"]:
        fail("arm_grid")
    if protocol.get("random_topological_replicates") != 32 or protocol.get("cell_timeout_seconds") != 180:
        fail("formal_budget")
    if protocol.get("inputs_sha256") != sha256(OUT / "inputs.csv") or protocol.get("classification_sha256") != sha256(OUT / "classification.csv"):
        fail("protocol_input_hashes")
    if summary.get("status") != "FORMAL_COMPLETE" or summary.get("cell_count") != 0 or summary.get("result_rows") != 0:
        fail("formal_summary")
    if formal:
        fail("unexpected_formal_rows")
    if not checkpoint_path.is_file() or receipt.get("checkpoint_sqlite_sha256") != sha256(checkpoint_path):
        fail("checkpoint_sqlite")
    if receipt.get("formal_results_sha256") != sha256(OUT / "formal_results.csv") or receipt.get("classification_sha256") != sha256(OUT / "classification.csv"):
        fail("receipt_hashes")
    if receipt.get("equivalence_failure_count") != 0 or receipt.get("certificate_violation_count") != 0:
        fail("formal_zero_tolerance")
    for relative_path, expected_hash in protocol.get("source_hashes", {}).items():
        if sha256(ROOT / relative_path) != expected_hash:
            fail(f"source_hash:{relative_path}")

    result = {
        "status": "verified",
        "experiment_id": EXPERIMENT_ID,
        "generator_family_count": len(IDS),
        "attempt_count": len(attempts),
        "eligible_family_count": 0,
        "classification_rows": len(classification),
        "formal_cell_count": 0,
        "formal_result_rows": 0,
        "external_boundary": "no eligible pure-unitary classical-free MQT INDEP output under the frozen 24-ID x 4..10 panel; no substitution permitted",
        "protocol_sha256": sha256(OUT / "protocol.json"),
    }
    (OUT / "verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
