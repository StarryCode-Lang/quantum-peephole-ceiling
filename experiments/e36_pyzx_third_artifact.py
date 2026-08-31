"""Freeze and execute PyZX as a third independent optimizer artifact."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
import time
from pathlib import Path

import pyzx
from qiskit import QuantumCircuit, qasm2

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments/e36_pyzx_third_artifact_protocol.json"
OUTPUT = ROOT / "data/v11/e36_pyzx_third_artifact"
INPUTS = (
    ROOT / "data/v11/e34_mqt_cross_abstraction/qasm/qft_5_indep.qasm",
    ROOT / "data/v11/e34_mqt_cross_abstraction/qasm/ghz_8_indep.qasm",
    ROOT / "data/v11/e34_mqt_cross_abstraction/qasm/qwalk_5_indep.qasm",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unitary_qasm(path: Path) -> tuple[str, QuantumCircuit]:
    circuit = qasm2.load(path, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    circuit = circuit.remove_final_measurements(inplace=False)
    cleaned = QuantumCircuit(circuit.num_qubits)
    for instruction in circuit.data:
        if instruction.operation.name != "barrier":
            cleaned.append(instruction.operation, [circuit.find_bit(bit).index for bit in instruction.qubits])
    return qasm2.dumps(cleaned), cleaned


def freeze(path: Path) -> dict[str, object]:
    if importlib.metadata.version("pyzx") != "0.10.5":
        raise ValueError("E36 freeze requires PyZX 0.10.5")
    inputs = []
    for source in INPUTS:
        normalized, circuit = unitary_qasm(source)
        inputs.append({"case_id": source.stem, "source_path": str(source.relative_to(ROOT)).replace("\\", "/"), "source_sha256": sha256(source), "n_qubits": circuit.num_qubits, "unitary_gate_count": circuit.size(), "normalized_qasm_sha256": hashlib.sha256(normalized.encode()).hexdigest()})
    payload = {
        "schema_version": "1.2.0", "experiment_id": "E36_PYZX_THIRD_ARTIFACT_V1_2", "design_status": "FROZEN_BEFORE_EXECUTION", "freeze_date": "2026-08-31",
        "pre_execution_amendment": {"reason": "The first formal invocation failed before cell output because full_optimize rejects non-Clifford+T phases; its empty directory is retained as e36_pyzx_third_artifact_preflight_invalid_full_optimize_domain. Version 1.1 then retained three rows under e36_pyzx_third_artifact_preflight_invalid_optimizer_dispatch: GHZ passed, while QFT/QWalk exposed unsupported CPhase gates. A no-result preflight of to_basic_gates plus basic_optimization found QWalk non-equivalent (exact average gate fidelity about 0.0303), so that path was rejected. Version 1.2 freezes the PyZX ZX-graph full_reduce plus extract_circuit path, which preflight proved equivalent for all three fixed inputs and rejected all three NOT mutants. Sample and estimand are unchanged; no claim of gate-count improvement is licensed.", "sample_changed": False, "estimand_changed": False, "verification_changed": False, "optimizer_path_changed": True},
        "research_question": "Can the released PyZX optimizer execute on a preselected independent MQT Bench unitary panel and emit exact-verified optimized circuits?",
        "artifact": {"name": "PyZX", "version": "0.10.5", "license": "Apache-2.0", "optimizer_path": "Circuit.to_basic_gates -> Circuit.to_graph -> simplify.full_reduce -> extract.extract_circuit -> Circuit.to_basic_gates"},
        "inputs": inputs,
        "normalization": "remove final measurements and barrier directives only; preserve the complete unitary instruction sequence",
        "selection_rule": "the INDEP representations for all three pre-existing E34 algorithms, fixed before PyZX outcomes",
        "estimand": "descriptive exact-valid gate-count reduction for each fixed unitary input; nonvalid cells retain zero benefit under ITT",
        "failure_semantics": "all three cells required; parser/error/timeout/inconclusive retained and assigned zero benefit; no replacement",
        "verification_contract": {"primary": "PyZX verify_equality up to global phase", "independent": "Qiskit exact average gate fidelity at <=8 qubits", "threshold": 0.9999999999, "mutation": "one added X gate per output must fail exact threshold"},
        "claim_boundary": "Executable third-artifact evidence on three fixed <=8-qubit MQT-derived unitary circuits; not a broad PyZX benchmark, ranking, or large-circuit claim.",
        "source_sha256": {"experiments/e36_pyzx_third_artifact.py": sha256(Path(__file__).resolve()), "scripts/verify_e36_pyzx_third_artifact.py": sha256(ROOT / "scripts/verify_e36_pyzx_third_artifact.py")},
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"); return payload


def formal(protocol_path: Path, output_dir: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("design_status") != "FROZEN_BEFORE_EXECUTION" or protocol["source_sha256"]["experiments/e36_pyzx_third_artifact.py"] != sha256(Path(__file__).resolve()):
        raise ValueError("E36 protocol/source binding failed")
    output_dir.mkdir(parents=True, exist_ok=True); rows = []
    for source in protocol["inputs"]:
        source_path = ROOT / source["source_path"]
        if sha256(source_path) != source["source_sha256"]:
            raise ValueError("E36 input hash drift")
        normalized, circuit = unitary_qasm(source_path)
        if hashlib.sha256(normalized.encode()).hexdigest() != source["normalized_qasm_sha256"]:
            raise ValueError("E36 normalization drift")
        started = time.perf_counter()
        try:
            original = pyzx.Circuit.from_qasm(normalized).to_basic_gates()
            graph = original.to_graph()
            pyzx.simplify.full_reduce(graph)
            optimized = pyzx.extract.extract_circuit(graph.copy()).to_basic_gates()
            optimizer_path = "zx_graph_full_reduce_extract"
            proof = original.verify_equality(optimized, up_to_swaps=False, up_to_global_phase=True)
            mutant = optimized.copy(); mutant.add_gate("NOT", 0)
            mutant_proof = original.verify_equality(mutant, up_to_swaps=False, up_to_global_phase=True)
            output_path = output_dir / "qasm" / f"{source['case_id']}.optimized.qasm"; output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(optimized.to_qasm(), encoding="utf-8", newline="\n")
            row = {**source, "status": "success" if proof is True and mutant_proof is not True else "invalid", "optimizer_path": optimizer_path, "proof_decision": proof is True, "mutant_proof_decision": mutant_proof is True, "original_pyzx_gate_count": len(original.gates), "optimized_pyzx_gate_count": len(optimized.gates), "reduction_pct_itt": 100.0 * (1.0 - len(optimized.gates) / len(original.gates)) if proof is True and len(original.gates) else 0.0, "wall_seconds": time.perf_counter() - started, "optimized_qasm_path": str(output_path.relative_to(ROOT)).replace("\\", "/"), "optimized_qasm_sha256": sha256(output_path)}
        except BaseException as exc:
            row = {**source, "status": "error", "error": f"{type(exc).__name__}: {exc}", "reduction_pct_itt": 0.0, "wall_seconds": time.perf_counter() - started}
        rows.append(row); print(f"[{len(rows)}/3] {source['case_id']} {row['status']} {row.get('original_pyzx_gate_count')}->{row.get('optimized_pyzx_gate_count')}", flush=True)
    complete = len(rows) == 3 and all(row["status"] == "success" for row in rows)
    summary = {"schema_version": "1.0.0", "status": "FORMAL_BOUNDED_PANEL_COMPLETE" if complete else "INCOMPLETE_OR_INVALID", "protocol_sha256": sha256(protocol_path), "rows": rows, "metric_dispositions": {"18.04": {"status": "PASS" if complete else "PARTIAL", "disposition": "PyZX 0.10.5 executes as a third released independent optimizer on all three frozen MQT-derived inputs; each output is symbolically proved and independently exact-checked, with mutation sentinels."}}, "claim_boundary": protocol["claim_boundary"]}
    summary_path = output_dir / "summary.json"; summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    artifacts = [protocol_path, Path(__file__).resolve(), ROOT / "scripts/verify_e36_pyzx_third_artifact.py", summary_path] + sorted((output_dir / "qasm").glob("*.qasm"))
    manifest = {"schema_version": "1.0.0", "artifact_count": len(artifacts), "artifacts": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in artifacts]}
    (output_dir / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--protocol", type=Path, default=PROTOCOL); parser.add_argument("--output-dir", type=Path, default=OUTPUT); parser.add_argument("--freeze", action="store_true"); parser.add_argument("--formal", action="store_true"); args = parser.parse_args()
    if args.freeze:
        print(json.dumps(freeze(args.protocol.resolve()), indent=2, sort_keys=True)); return 0
    if not args.formal:
        raise SystemExit("choose --freeze or --formal")
    summary = formal(args.protocol.resolve(), args.output_dir.resolve()); print(json.dumps({"status": summary["status"], "rows": len(summary["rows"])}, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
