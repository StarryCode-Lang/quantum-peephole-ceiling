"""Verify the frozen E38 exhaustive oracle artifact without rerunning it."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


PROTOCOL_ID = "E38_REWRITE_EXPOSURE_ORACLE_V1"
MODELS = {"wire_order_v1", "conservative_commutation_v1"}
STRATA = {"random", "implanted", "blocked", "multi_pair"}
ALPHABET = {"h", "x", "z", "s", "sdg", "t", "tdg", "rx", "ry", "rz", "cx", "cz"}
ROTATION_ANGLES = {-math.pi, -math.pi / 2, math.pi / 2, math.pi}
ZERO_TOLERANCE_FIELDS = (
    "theorem_mismatch", "lb_gt_oracle", "ub_lt_oracle", "exact_solver_mismatch",
    "cgl_lb_shortfall", "dependency_invalid", "equivalence_failure",
    "certificate_contract_failure", "mutant_not_rejected",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid_jsonl:{path}:{line_number}:{exc}") from exc
    return rows


def verify_inputs(protocol: dict[str, Any], inputs: list[dict[str, Any]]) -> None:
    if protocol["protocol_id"] != PROTOCOL_ID:
        raise ValueError("protocol_id_mismatch")
    if protocol["num_cases"] != 512 or protocol["cases_per_stratum"] != 128:
        raise ValueError("formal_case_panel_mismatch")
    if len(inputs) != 512 or len({row["case_id"] for row in inputs}) != 512:
        raise ValueError("input_count_or_identity_mismatch")
    strata = Counter(row["stratum"] for row in inputs)
    if set(strata) != STRATA or any(value != 128 for value in strata.values()):
        raise ValueError("stratum_balance_mismatch")
    for row in inputs:
        if row["num_qubits"] not in {2, 3, 4, 5}:
            raise ValueError(f"qubit_range_mismatch:{row['case_id']}")
        if len(row["operations"]) not in {4, 5, 6, 7, 8}:
            raise ValueError(f"gate_count_range_mismatch:{row['case_id']}")
        for operation in row["operations"]:
            if operation["name"] not in ALPHABET:
                raise ValueError(f"gate_alphabet_mismatch:{row['case_id']}")
            if any(q < 0 or q >= row["num_qubits"] for q in operation["qubits"]):
                raise ValueError(f"qubit_operand_mismatch:{row['case_id']}")
            if operation["name"] in {"cx", "cz"}:
                if len(operation["qubits"]) != 2 or operation["qubits"][0] == operation["qubits"][1]:
                    raise ValueError(f"two_qubit_operand_mismatch:{row['case_id']}")
            elif len(operation["qubits"]) != 1:
                raise ValueError(f"single_qubit_operand_mismatch:{row['case_id']}")
            if operation["name"] in {"rx", "ry", "rz"}:
                if len(operation["params"]) != 1 or not any(
                    math.isclose(operation["params"][0], angle, abs_tol=1e-15)
                    for angle in ROTATION_ANGLES
                ):
                    raise ValueError(f"rotation_angle_mismatch:{row['case_id']}")
            elif operation["params"]:
                raise ValueError(f"unexpected_gate_params:{row['case_id']}")


def verify_rows(rows: list[dict[str, Any]], inputs: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) != 1024:
        raise ValueError("row_count_mismatch")
    input_ids = {row["case_id"] for row in inputs}
    seen = {(row["case_id"], row["model"]) for row in rows}
    if seen != {(case_id, model) for case_id in input_ids for model in MODELS}:
        raise ValueError("case_model_grid_mismatch")
    for row in rows:
        if row["oracle_topological_order_count"] > 40320:
            raise ValueError(f"topological_order_limit_exceeded:{row['case_id']}")
        if row["input_sha256"] != row["certificate"]["input_sha256"]:
            raise ValueError(f"certificate_input_hash_mismatch:{row['case_id']}")
        cert = row["certificate"]
        if cert["constructive_lower_bound"] > cert["matching_upper_bound"]:
            raise ValueError(f"certificate_bounds_inverted:{row['case_id']}")
        if cert["status"] == "exact" and (
            cert["discarded_candidate_count"] != 0
            or cert["constructive_lower_bound"] != cert["matching_upper_bound"]
        ):
            raise ValueError(f"invalid_exact_certificate:{row['case_id']}")
        if cert["status"] == "exact_zero" and cert["matching_upper_bound"] != 0:
            raise ValueError(f"invalid_exact_zero_certificate:{row['case_id']}")
    summary = {
        field: sum(int(row[field]) for row in rows)
        for field in ZERO_TOLERANCE_FIELDS
    }
    summary["rows"] = len(rows)
    summary["case_count"] = len(input_ids)
    summary["models"] = sorted(MODELS)
    return summary


def verify(root: Path) -> dict[str, Any]:
    protocol_path = root / "protocol.json"
    inputs_path = root / "inputs.jsonl"
    rows_path = root / "rows.jsonl"
    receipt_path = root / "receipt.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    inputs = load_jsonl(inputs_path)
    rows = load_jsonl(rows_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    verify_inputs(protocol, inputs)
    summary = verify_rows(rows, inputs)
    if receipt["mode"] != "formal" or receipt["protocol_id"] != PROTOCOL_ID:
        raise ValueError("receipt_identity_mismatch")
    if receipt["protocol_sha256"] != sha256_bytes(
        json.dumps(protocol, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ):
        raise ValueError("protocol_hash_mismatch")
    if receipt["inputs_sha256"] != sha256_bytes(inputs_path.read_bytes()):
        raise ValueError("inputs_hash_mismatch")
    if not receipt.get("zero_tolerance"):
        raise ValueError("receipt_not_zero_tolerance")
    if any(summary[field] != 0 for field in ZERO_TOLERANCE_FIELDS):
        raise ValueError("zero_tolerance_metric_nonzero")
    source_hashes = {
        json.dumps(row["certificate"]["source_hashes"], sort_keys=True)
        for row in rows
    }
    if len(source_hashes) != 1:
        raise ValueError("source_hash_drift_within_e38")
    module_path = root.parents[2] / "src" / "optimisation" / "rewrite_exposure.py"
    source_payload = json.loads(next(iter(source_hashes)))
    if source_payload.get("rewrite_exposure.py") != sha256_bytes(module_path.read_bytes()):
        raise ValueError("current_source_hash_does_not_match_certificate")
    result = {
        "status": "verified",
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": receipt["protocol_sha256"],
        "inputs_sha256": receipt["inputs_sha256"],
        "rows_sha256": sha256_bytes(rows_path.read_bytes()),
        "summary": summary,
        "source_hashes": json.loads(next(iter(source_hashes))),
    }
    (root / "verification.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("data/v12/e38_rewrite_exposure_oracle"),
    )
    args = parser.parse_args()
    result = verify(args.root.resolve())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
