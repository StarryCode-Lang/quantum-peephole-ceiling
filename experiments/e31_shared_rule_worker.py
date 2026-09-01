"""One cold-process worker for an E31 shared-rule-engine treatment cell."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from qiskit import qasm2, transpile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.e31_listing_phase2b_interaction import random_topological_listing
from src.circuits.real_benchmarks import average_gate_fidelity, circuit_sha256
from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor
from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher


def _listing(circuit, model: str, seed: int):
    if model == "LBL":
        return circuit.copy()
    if model == "WCL":
        return WireTraversalPreprocessor().preprocess(circuit)
    if model == "RANDOM_TOPOLOGICAL":
        return random_topological_listing(circuit, seed)
    raise ValueError(f"unknown listing model: {model}")


def execute(payload: dict) -> dict:
    """Execute one cell; template_enabled is the sole rule-set branch."""
    qasm_path = Path(payload["qasm_path"])
    if not qasm_path.is_absolute():
        qasm_path = PROJECT_ROOT / qasm_path
    original = qasm2.load(
        qasm_path,
        custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
    )
    listed = _listing(original, str(payload["listing_model"]), int(payload["listing_seed"]))
    template_enabled = str(payload["rule_set"]) == "COMMUTATION_PLUS_TEMPLATES"
    if str(payload["rule_set"]) not in {"COMMUTATION_ONLY", "COMMUTATION_PLUS_TEMPLATES"}:
        raise ValueError(f"unknown rule set: {payload['rule_set']}")
    engine = Phase2bTemplateMatcher(
        max_iterations=100,
        fidelity_threshold=float(payload["fidelity_threshold"]),
        success_reduction=0.0,
        gather_window=int(payload["window_gates"]),
        template_enabled=template_enabled,
        collect_trace=True,
    )
    optimized = engine.optimize_full_pipeline(listed, target=original)
    fidelity = average_gate_fidelity(
        optimized.optimized_circuit, original, max_qubits=original.num_qubits
    )
    basis = list(payload["common_basis"])
    normalized_input = transpile(listed, basis_gates=basis, optimization_level=0)
    normalized_output = transpile(
        optimized.optimized_circuit, basis_gates=basis, optimization_level=0
    )
    initial = normalized_input.size()
    reduction = 100.0 * (1.0 - normalized_output.size() / initial) if initial else 0.0
    valid = bool(fidelity >= float(payload["fidelity_threshold"]))
    return {
        "status": "success" if valid else "invalid",
        "valid_equivalent_output": valid,
        "exact_fidelity": float(fidelity),
        "output_circuit_sha256": circuit_sha256(optimized.optimized_circuit),
        "common_basis_gate_reduction_pct": float(reduction),
        "optimizer_runtime_seconds": float(optimized.runtime_seconds),
        "original_common_basis_gate_count": int(initial),
        "optimized_common_basis_gate_count": int(normalized_output.size()),
        "template_enabled": template_enabled,
        "trace": optimized.metadata.get("trace", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    result = execute(payload)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(args.result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
