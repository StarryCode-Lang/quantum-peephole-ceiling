#!/usr/bin/env python3
"""Generate the E31 formal release gate only from complete, hash-bound evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.e31_formal_orchestrator import validate_release_gate

GUOQ_ROOT = PROJECT_ROOT / "data/v10/prepaper/external_baselines/guoq/bqskit_pilot"
HELDOUT_ROOT = PROJECT_ROOT / "data/v10/prepaper/heldout_v2"
PROTOCOL = PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json"
DESIGN = PROJECT_ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv"
POWER = PROJECT_ROOT / "data/v11/e31_factorial_pareto/dual_estimand_power.json"
OUTPUT = PROJECT_ROOT / "data/v11/e31_factorial_pareto/formal_release_gate.json"
TOOLS = ("custom", "qiskit", "cirq", "tket")
EQUIVALENCE_SOURCE = PROJECT_ROOT / "src/equivalence.py"
FIDELITY_SOURCE = PROJECT_ROOT / "src/circuits/real_benchmarks.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"required evidence is absent: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"required evidence is absent: {path}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_guoq(root: Path) -> dict[str, str]:
    result = root / "guoq_bqskit_pilot.csv"
    metadata_path = root / "metadata.json"
    audit_path = root / "metric_revalidation.json"
    preregistration_path = root / "preregistration.json"
    dependency_path = root / "preflight/dependency_lock.json"
    local_preflight_path = root / "preflight/preflight.json"
    preflight_path = root.parent / "preflight/preflight.json"
    official_path = root.parent / "preflight/official_artifact_record.json"
    paths = (result, metadata_path, audit_path, preregistration_path, dependency_path,
             local_preflight_path, preflight_path, official_path)
    metadata, audit = read_json(metadata_path), read_json(audit_path)
    preregistration = read_json(preregistration_path)
    local_preflight = read_json(local_preflight_path)
    official_preflight = read_json(preflight_path)
    dependency_lock = read_json(dependency_path)
    rows = read_csv(result)
    if metadata.get("status") != "complete" or metadata.get("n_rows") != 3:
        raise ValueError("GUOQ pilot metadata is not complete with three preregistered rows")
    if len(rows) != 3 or len({row.get("circuit_id") for row in rows}) != 3:
        raise ValueError("GUOQ pilot does not contain three distinct smoke inputs")
    expected_ids = preregistration.get("circuit_ids_in_order")
    if expected_ids != [row.get("circuit_id") for row in rows]:
        raise ValueError("GUOQ pilot rows do not match the preregistered input order")
    if not all(row.get("exact_equivalent", "").lower() == "true" and
               row.get("valid_equivalent_output", "").lower() == "true" for row in rows):
        raise ValueError("GUOQ pilot contains a non-equivalent or invalid incumbent")
    if metadata.get("result_sha256") != sha256(result):
        raise ValueError("GUOQ metadata result hash mismatch")
    if audit.get("status") != "pass" or audit.get("revalidated_result_sha256") != sha256(result):
        raise ValueError("GUOQ metric revalidation is absent or hash-mismatched")
    if len(audit.get("rows", [])) != 3 or not all(row.get("exact_equivalent") is True
                                                  for row in audit["rows"]):
        raise ValueError("GUOQ metric revalidation does not cover three equivalent rows")
    audit_by_id = {row.get("circuit_id"): row for row in audit["rows"]}
    for row in rows:
        audited = audit_by_id.get(row.get("circuit_id"), {})
        if (audited.get("output_qasm_sha256") != row.get("output_qasm_sha256") or
                audited.get("source_common_qasm_sha256") != row.get("source_common_qasm_sha256")):
            raise ValueError("GUOQ metric audit rows are not bound to the pilot QASM hashes")
        output_qasm = PROJECT_ROOT / str(row.get("output_qasm_path", ""))
        if not output_qasm.is_file() or sha256(output_qasm) != row.get("output_qasm_sha256"):
            raise ValueError("GUOQ output QASM is absent or hash-mismatched")
        paths += (output_qasm,)
    if local_preflight.get("decision") != "GO" or local_preflight.get("blockers") != []:
        raise ValueError("GUOQ BQSKit preflight is not GO without blockers")
    if official_preflight.get("rewrite_only_smoke", {}).get("decision") != "GO":
        raise ValueError("GUOQ official-artifact rewrite smoke is not GO")
    if not dependency_lock.get("packages") and not dependency_lock.get("wheelhouse"):
        raise ValueError("GUOQ dependency lock is empty")
    if any(path.name.endswith("_checkpoint.csv") for path in root.rglob("*.csv")):
        raise ValueError("GUOQ pilot contains an unfinished checkpoint")
    return {path.relative_to(PROJECT_ROOT).as_posix(): sha256(path) for path in paths}


def _only_final(root: Path, tool: str) -> Path:
    candidates = [path for path in (root / "results/raw").glob(f"{tool}_default_*.csv")
                  if not path.name.endswith("_checkpoint.csv")]
    if len(candidates) != 1:
        raise ValueError(f"heldout-v2 {tool} must have exactly one final CSV; found {len(candidates)}")
    return candidates[0]


def validate_heldout(root: Path) -> dict[str, str]:
    active_checkpoints = [path for path in root.rglob("*_checkpoint.csv")
                          if "preflight_invalid" not in path.parts]
    if active_checkpoints:
        raise ValueError(f"heldout-v2 contains unfinished checkpoints: {active_checkpoints}")
    manifest = root / "inputs/benchmark_manifest.csv"
    seal_path = root / "sealed_predictions/SEALED.json"
    predictions = root / "sealed_predictions/heldout_v2_predictions.csv"
    start_path = root / "execution/START_GATE.json"
    metrics_path = root / "analysis/combined_heldout_metrics.json"
    contract_path = root / "analysis/execution_contract_audit.json"
    seal, start, metrics = read_json(seal_path), read_json(start_path), read_json(metrics_path)
    contract = read_json(contract_path)
    manifest_hash = sha256(manifest)
    manifest_rows = read_csv(manifest)
    key_fields = ("circuit_id", "trial", "seed", "input_circuit_sha256")
    manifest_keys = {tuple(row.get(field) for field in key_fields) for row in manifest_rows}
    if len(manifest_rows) != 192 or len(manifest_keys) != 192:
        raise ValueError("heldout-v2 manifest does not contain 192 unique execution keys")
    if seal.get("status") != "SEALED_BEFORE_HELDOUT_V2_OPTIMIZATION" or seal.get("n_rows") != 192:
        raise ValueError("heldout-v2 seal is not a complete pre-optimization 192-row seal")
    if seal.get("manifest_sha256") != manifest_hash or seal.get("predictions_sha256") != sha256(predictions):
        raise ValueError("heldout-v2 sealed artifact hash mismatch")
    if start.get("status") != "VERIFIED_BEFORE_FIRST_HELDOUT_V2_OPTIMIZER":
        raise ValueError("heldout-v2 start gate is not verified")
    if start.get("seal_sha256") != sha256(seal_path) or start.get("manifest_rows") != 192:
        raise ValueError("heldout-v2 start gate is not bound to the sealed packet")
    diagnostics_path = root / "analysis/heldout_v2_tool_diagnostics.csv"
    diagnostic_rows = read_csv(diagnostics_path)
    diagnostic_hashes = {row.get("tool"): row.get("result_sha256") for row in diagnostic_rows}
    if len(diagnostic_rows) != 4 or set(diagnostic_hashes) != set(TOOLS):
        raise ValueError("heldout-v2 tool diagnostics do not cover exactly four tools")
    if contract.get("status") != "PASS_ALL_FRESH_EXECUTION_CONTRACT_GATES":
        raise ValueError("heldout-v2 execution contract audit is not PASS")
    contract_sources = contract.get("source_hashes", {})
    expected_contract_sources = {
        "benchmark_runner_source_sha256": PROJECT_ROOT / "experiments/sota_benchmark.py",
        "equivalence_contract_source_sha256": EQUIVALENCE_SOURCE,
        "exact_fidelity_source_sha256": FIDELITY_SOURCE,
        "execution_protocol_sha256": PROJECT_ROOT / "experiments/heldout_v2_execution_protocol.json",
        "executor_source_sha256": PROJECT_ROOT / "experiments/heldout_v2_execute.py",
    }
    if any(contract_sources.get(field) != sha256(path)
           for field, path in expected_contract_sources.items()):
        raise ValueError("heldout-v2 execution contract source hashes have drifted")
    evidence = [manifest, seal_path, predictions, start_path, metrics_path, contract_path]
    for tool in TOOLS:
        result = _only_final(root, tool)
        metadata_path = root / f"results/metadata/{tool}_default_metadata.json"
        metadata, rows = read_json(metadata_path), read_csv(result)
        if metadata.get("canonical_data_file") != result.name or metadata.get("n_rows") != 192:
            raise ValueError(f"heldout-v2 {tool} metadata does not bind the complete final CSV")
        if metadata.get("benchmark_manifest_sha256") != manifest_hash or len(rows) != 192:
            raise ValueError(f"heldout-v2 {tool} row count or manifest hash mismatch")
        if metadata.get("n_ok") != 192 or metadata.get("n_valid_equivalent_outputs") != 192:
            raise ValueError(f"heldout-v2 {tool} metadata completion/equivalence counts are not 192")
        if any(row.get("compiler_status") != "ok" or
               row.get("valid_equivalent_output", "").lower() != "true" or
               row.get("equivalence_status") != "pass" for row in rows):
            raise ValueError(f"heldout-v2 {tool} contains a non-exact-valid row")
        for source_name, recorded_sha in metadata.get("source_hashes", {}).items():
            source_path = PROJECT_ROOT / source_name
            if not source_path.is_file() or sha256(source_path) != recorded_sha:
                raise ValueError(f"heldout-v2 {tool} source provenance drift: {source_name}")
        if {row.get("run_id") for row in rows} != {str(metadata.get("run_id"))}:
            raise ValueError(f"heldout-v2 {tool} CSV run_id does not match metadata")
        row_keys = {tuple(row.get(field) for field in key_fields) for row in rows}
        if row_keys != manifest_keys:
            raise ValueError(f"heldout-v2 {tool} execution keys differ from the sealed manifest")
        if diagnostic_hashes.get(tool) != sha256(result):
            raise ValueError(f"heldout-v2 {tool} analysis is not bound to the final CSV hash")
        contract_tool = contract.get("tool_gates", {}).get(tool, {})
        if (contract_tool.get("result_sha256") != sha256(result) or
                contract_tool.get("metadata_sha256") != sha256(metadata_path) or
                contract_tool.get("rows") != 192 or
                contract_tool.get("exact_equivalence_pass") != 192 or
                contract_tool.get("valid_equivalent_outputs") != 192):
            raise ValueError(f"heldout-v2 {tool} execution contract is incomplete or hash-mismatched")
        verifier = metadata.get("equivalence_verifier", {})
        provenance = metadata.get("fresh_run_provenance", {})
        equivalence_sha = sha256(EQUIVALENCE_SOURCE)
        fidelity_sha = sha256(FIDELITY_SOURCE)
        if metadata.get("source_hashes", {}).get("src/equivalence.py") != equivalence_sha:
            raise ValueError(f"heldout-v2 {tool} was not run with the current equivalence verifier")
        if metadata.get("source_hashes", {}).get("src/circuits/real_benchmarks.py") != fidelity_sha:
            raise ValueError(f"heldout-v2 {tool} was not run with the current fidelity implementation")
        if (verifier.get("source_sha256") != equivalence_sha or
                verifier.get("exact_fidelity_source_sha256") != fidelity_sha or
                verifier.get("layout_aware_qiskit_final_layout") is not True or
                "src/circuits/real_benchmarks.py::average_gate_fidelity" not in
                str(verifier.get("call_chain", ""))):
            raise ValueError(f"heldout-v2 {tool} lacks layout-aware verifier provenance")
        if provenance.get("reason") != "layout_aware_equivalence_rerun":
            raise ValueError(f"heldout-v2 {tool} lacks fresh layout-fix rerun provenance")
        if len({row.get("input_circuit_sha256") for row in rows}) != 192:
            raise ValueError(f"heldout-v2 {tool} is not unique by input circuit hash")
        if {row.get("benchmark_manifest_sha256") for row in rows} != {manifest_hash}:
            raise ValueError(f"heldout-v2 {tool} rows are not bound to the manifest")
        evidence.extend((result, metadata_path))
    analysis_hashes = {
        "merged_v2_sha256": root / "analysis/heldout_v2_predictions_outcomes.csv",
        "combined_data_sha256": root / "analysis/heldout_v1_v2_unique_inputs.csv",
        "bootstrap_sha256": root / "analysis/combined_mcc_nested_bootstrap_10000.csv",
        "family_diagnostics_sha256": root / "analysis/combined_generator_diagnostics.csv",
        "tool_diagnostics_sha256": root / "analysis/heldout_v2_tool_diagnostics.csv",
    }
    if metrics.get("seal_hashes_verified") is not True or metrics.get("v2_unique_inputs") != 192:
        raise ValueError("heldout-v2 analysis does not certify the sealed 192 unique inputs")
    if metrics.get("bootstrap_replicates") != 10000 or metrics.get("outer_clusters") != 16:
        raise ValueError("heldout-v2 analysis does not use the frozen clustered bootstrap design")
    if (contract.get("manifest_sha256") != manifest_hash or
            contract.get("start_gate_sha256") != sha256(start_path) or
            metrics.get("execution_contract_audit_sha256") != sha256(contract_path)):
        raise ValueError("heldout-v2 execution contract is not bound to manifest/start gate/analysis")
    for field, path in analysis_hashes.items():
        if metrics.get(field) != sha256(path):
            raise ValueError(f"heldout-v2 analysis hash mismatch: {field}")
        evidence.append(path)
    return {path.relative_to(root.parent).as_posix(): sha256(path) for path in evidence}


def build_gate(guoq_root: Path = GUOQ_ROOT, heldout_root: Path = HELDOUT_ROOT,
               protocol: Path = PROTOCOL, design: Path = DESIGN, power: Path = POWER) -> dict:
    hashes = {
        "protocol_sha256": sha256(protocol),
        "design_manifest_sha256": sha256(design),
        "power_sha256": sha256(power),
    }
    return {
        "schema_version": "1.0.0",
        "status": "COMPLETE",
        "guoq_status": "COMPLETE",
        "heldout_status": "COMPLETE",
        **hashes,
        "guoq_evidence_sha256": validate_guoq(guoq_root),
        "heldout_evidence_sha256": validate_heldout(heldout_root),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


def write_gate(payload: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        validate_release_gate(temporary, {key: payload[key] for key in
                              ("protocol_sha256", "design_manifest_sha256", "power_sha256")})
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def generate_gate(output: Path, **paths: Path) -> dict:
    """Fail closed: an invalid current evidence state cannot leave a formal gate."""
    try:
        payload = build_gate(**paths)
        write_gate(payload, output)
        return payload
    except Exception:
        output.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    generate_gate(args.output.resolve())
    print(f"Formal E31 release gate: {args.output.resolve()}")


if __name__ == "__main__":
    main()
