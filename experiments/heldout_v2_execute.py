"""Fail-closed, sequential execution of the sealed heldout-v2 packet."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.heldout_v2_seal import verify_seal
from experiments.sota_benchmark import COMMON_BASIS, file_sha256, run_tool

ROOT = PROJECT_ROOT / "data" / "v10" / "prepaper" / "heldout_v2"
MANIFEST = ROOT / "inputs" / "benchmark_manifest.csv"
RESULTS = ROOT / "results"
SEAL_PATH = ROOT / "sealed_predictions" / "SEALED.json"
PROTOCOL_PATH = PROJECT_ROOT / "experiments" / "heldout_v2_execution_protocol.json"
START_GATE_PATH = ROOT / "execution" / "START_GATE.json"

SEALED_PATHS = {
    "manifest_sha256": MANIFEST,
    "features_sha256": ROOT / "inputs" / "preoptimization_features.csv",
    "predictions_sha256": ROOT / "sealed_predictions" / "heldout_v2_predictions.csv",
    "model_sha256": ROOT / "sealed_predictions" / "model.json",
    "protocol_sha256": PROJECT_ROOT / "experiments" / "heldout_v2_protocol.json",
    "generator_overlap_audit_sha256": ROOT / "sealed_predictions" / "generator_overlap_audit.json",
    "source_sha256": PROJECT_ROOT / "experiments" / "heldout_v2_seal.py",
    "training_manifest_sha256": PROJECT_ROOT / "data" / "v10" / "prepaper" / "sota" / "inputs" / "benchmark_manifest.csv",
    "v1_heldout_manifest_sha256": PROJECT_ROOT / "data" / "v10" / "prepaper" / "heldout" / "inputs" / "benchmark_manifest.csv",
}


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _verify_immutable_packet() -> tuple[dict, dict]:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    if seal.get("status") != "SEALED_BEFORE_HELDOUT_V2_OPTIMIZATION":
        raise RuntimeError("heldout-v2 seal status is invalid")
    if seal.get("optimizer_outcomes_present_at_seal") is not False:
        raise RuntimeError("seal does not mechanically attest results-at-seal=false")
    mismatches = {
        field: {"sealed": seal.get(field), "actual": file_sha256(path)}
        for field, path in SEALED_PATHS.items()
        if seal.get(field) != file_sha256(path)
    }
    if mismatches:
        raise RuntimeError(f"sealed hash mismatch: {mismatches}")

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    manifest = pd.read_csv(MANIFEST)
    expected = int(protocol["expected_rows_per_tool"])
    required_unique = int(protocol["required_unique_input_hashes"])
    if len(manifest) != expected:
        raise RuntimeError(f"manifest rows changed: {len(manifest)} != {expected}")
    if manifest["input_circuit_sha256"].nunique() != required_unique:
        raise RuntimeError("manifest input hashes are not globally unique")
    if protocol["common_basis"] != COMMON_BASIS:
        raise RuntimeError("execution protocol common basis differs from runner")
    if float(protocol["timeout_seconds_per_input"]) != 120.0:
        raise RuntimeError("execution timeout is not the frozen 120 seconds")
    return seal, protocol


def verify_or_create_start_gate() -> dict:
    seal, protocol = _verify_immutable_packet()
    source_hashes = {
        "execution_protocol_sha256": file_sha256(PROTOCOL_PATH),
        "executor_source_sha256": file_sha256(Path(__file__).resolve()),
        "benchmark_runner_source_sha256": file_sha256(PROJECT_ROOT / "experiments" / "sota_benchmark.py"),
        "exact_fidelity_source_sha256": file_sha256(PROJECT_ROOT / "src" / "circuits" / "real_benchmarks.py"),
        "equivalence_contract_source_sha256": file_sha256(PROJECT_ROOT / "src" / "equivalence.py"),
    }
    if START_GATE_PATH.exists():
        gate = json.loads(START_GATE_PATH.read_text(encoding="utf-8"))
        expected = {
            **source_hashes,
            "seal_sha256": file_sha256(SEAL_PATH),
            "results_directory_existed_before_first_optimizer": False,
        }
        mismatches = {key: (gate.get(key), value) for key, value in expected.items()
                      if gate.get(key) != value}
        if mismatches:
            raise RuntimeError(f"execution start-gate mismatch: {mismatches}")
        return gate

    # This strict verifier additionally refuses an existing results directory.
    strict = verify_seal(ROOT)
    if RESULTS.exists():
        raise RuntimeError("results existed before first optimizer launch")
    gate = {
        "status": "VERIFIED_BEFORE_FIRST_HELDOUT_V2_OPTIMIZER",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "seal_status": seal["status"],
        "seal_sha256": file_sha256(SEAL_PATH),
        "seal_verifier_status": strict["status"],
        "optimizer_outcomes_present_at_seal": False,
        "results_directory_existed_before_first_optimizer": False,
        "manifest_rows": int(protocol["expected_rows_per_tool"]),
        "unique_input_hashes": int(protocol["required_unique_input_hashes"]),
        "tool_order": protocol["tool_order"],
        **source_hashes,
        "sealed_artifact_hashes": {field: seal[field] for field in SEALED_PATHS},
    }
    _atomic_json(START_GATE_PATH, gate)
    return gate


def _augment_formal_metadata(tool: str) -> None:
    """Bind the fresh layout-aware rerun to both equivalence source layers."""
    metadata_path = RESULTS / "metadata" / f"{tool}_default_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    equivalence_sha = file_sha256(PROJECT_ROOT / "src" / "equivalence.py")
    exact_sha = file_sha256(PROJECT_ROOT / "src" / "circuits" / "real_benchmarks.py")
    metadata["equivalence_verifier"] = {
        "layout_aware_qiskit_final_layout": True,
        "source_sha256": equivalence_sha,
        "exact_fidelity_source_sha256": exact_sha,
        "call_chain": (
            "experiments/sota_benchmark.py::run_tool -> "
            "src/circuits/real_benchmarks.py::average_gate_fidelity -> "
            "qiskit.quantum_info.Operator.from_circuit; "
            "src/equivalence.py defines the project certificate contract"
        ),
    }
    metadata["fresh_run_provenance"] = {"reason": "layout_aware_equivalence_rerun"}
    metadata["source_hashes"] = {
        **metadata.get("source_hashes", {}),
        "src/equivalence.py": equivalence_sha,
        "src/circuits/real_benchmarks.py": exact_sha,
    }
    _atomic_json(metadata_path, metadata)


def execute(stop_after_tool: str | None = None) -> None:
    _, protocol = _verify_immutable_packet()
    gate = verify_or_create_start_gate()
    print(json.dumps({"start_gate": gate["status"], "tool_order": protocol["tool_order"]}, sort_keys=True))

    # Avoid hidden native-library concurrency while the isolated optimizer worker
    # is active. The benchmark runner itself starts exactly one persistent child.
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"

    for tool in protocol["tool_order"]:
        _verify_immutable_packet()
        frame = run_tool(
            tool,
            config=protocol["tool_config"],
            mode="full",
            timeout_s=float(protocol["timeout_seconds_per_input"]),
            manifest_path=MANIFEST,
            output_root=RESULTS,
            expected_manifest_rows=int(protocol["expected_rows_per_tool"]),
        )
        if len(frame) != int(protocol["expected_rows_per_tool"]):
            raise RuntimeError(f"{tool} did not produce the required row count")
        if frame["input_circuit_sha256"].nunique() != int(protocol["required_unique_input_hashes"]):
            raise RuntimeError(f"{tool} did not cover every unique sealed input")
        if set(frame["fidelity_source"].astype(str)) - {"exact", "unavailable"}:
            raise RuntimeError(f"{tool} emitted a non-confirmatory fidelity source")
        if set(frame["common_basis"].astype(str)) != {",".join(protocol["common_basis"])}:
            raise RuntimeError(f"{tool} common-basis contract mismatch")
        _augment_formal_metadata(tool)
        if stop_after_tool == tool:
            break


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--stop-after-tool", choices=["custom", "qiskit", "cirq", "tket"])
    args = parser.parse_args()
    gate = verify_or_create_start_gate()
    if args.verify_only:
        print(json.dumps(gate, indent=2, sort_keys=True))
        return
    execute(args.stop_after_tool)


if __name__ == "__main__":
    main()
