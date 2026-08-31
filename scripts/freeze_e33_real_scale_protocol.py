"""Freeze the E33 external >10-qubit panel before execution."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from qiskit import qasm2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.circuits.real_benchmarks import circuit_sha256

BASE = ROOT / "data/v10/prepaper/external_baselines/quasar/quasar-artifact/benchmarks/circuits"
OUTPUT = ROOT / "experiments/e33_real_scale_protocol.json"
SELECTED = (
    ("mod_red_21.qasm", "modular_arithmetic"),
    ("gf2^4_mult.qasm", "finite_field_arithmetic"),
    ("qaoa_n14_p4.qasm", "qaoa"),
    ("csla_mux_3.qasm", "adder_mux"),
    ("qft_16.qasm", "qft"),
    ("barenco_tof_10.qasm", "reversible_toffoli"),
    ("qaoa_n20_p4.qasm", "qaoa"),
    ("gf2^7_mult.qasm", "finite_field_arithmetic"),
    ("adder_8.qasm", "adder"),
    ("csum_mux_9.qasm", "adder_mux"),
    ("qcla_adder_10.qasm", "adder"),
)
SOURCES = (
    "experiments/e33_real_scale_panel.py",
    "scripts/freeze_e33_real_scale_protocol.py",
    "scripts/verify_e33_real_scale_panel.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    inputs = []
    for name, benchmark_class in SELECTED:
        path = BASE / name
        circuit = qasm2.load(path, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
        if not 11 <= circuit.num_qubits <= 36:
            raise ValueError(f"width outside preregistered E33 scope: {name}")
        inputs.append({
            "benchmark_id": path.stem,
            "benchmark_class": benchmark_class,
            "n_qubits": int(circuit.num_qubits),
            "input_gate_count": int(circuit.size()),
            "qasm_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "qasm_file_sha256": sha256(path),
            "input_circuit_sha256": circuit_sha256(circuit),
        })
    payload = {
        "schema_version": "1.2.0", "experiment_id": "E33_REAL_SCALE_EXTERNAL_V1_2", "design_status": "FROZEN_BEFORE_EXECUTION", "freeze_date": "2026-08-31",
        "pre_execution_amendment": {"reason": "The first formal invocation produced ten error-only receipts because the mutation sentinel used an invalid PyZX string gate key. The run was interrupted and preserved under data/v11/e33_real_scale_preflight_invalid_keyerror_x. A subsequent no-result unit preflight established that PyZX 0.10.5 requires the key NOT rather than X or x. No valid scientific cell or aggregate result was emitted; the sentinel key changed to NOT and all source hashes were re-frozen before restart.", "scientific_question_changed": False, "sample_changed": False, "estimand_changed": False, "failure_semantics_changed": False, "invalid_receipts_retained": 10},
        "research_question": "Does the fixed WCL listing retain proof-valid optimization behavior relative to LBL on a preselected external 11-36-qubit application-oriented benchmark panel?",
        "source_record": {"doi": "10.5281/zenodo.19571754", "version": "v3", "archive_md5": "ff3a49973c97316bca0fb2d347ea5478", "local_archive_sha256": sha256(ROOT / "data/v10/prepaper/external_baselines/quasar/quasar-artifact.tar.gz"), "license_metadata": "not displayed in the retrieved Zenodo record; use is limited to the already archived research evidence"},
        "selection_rule": "eleven named circuits fixed before outcomes to span widths 11-36 and arithmetic, QAOA, QFT, and reversible classes; no result-dependent replacement",
        "inputs": inputs,
        "factors": {"listing_model": ["LBL", "WCL"]},
        "optimizer_contract": {"rule_set": "COMMUTATION_PLUS_TEMPLATES", "gather_window": 64, "max_iterations": 50},
        "resource_contract": {"cell_timeout_seconds": 120.0, "cold_process_per_cell": True, "threads_per_worker": 1},
        "verification_contract": {"method": "PyZX Circuit.verify_equality full_reduce identity attempt", "symbolic_basis": ["h", "rz", "cx"], "decision_true": "proved equal", "decision_nontrue": "inconclusive", "one_x_mutant_per_cell": True},
        "estimand": "finite-panel mean WCL-minus-LBL proof-valid total-gate reduction percentage points; timeout/error/inconclusive assigned zero under ITT",
        "failure_semantics": "all 22 cells retained; missing cell fatal; proof nontrue is inconclusive not inequivalent; non-success benefit zero",
        "claim_boundary": "Direct fixed-panel evidence beyond the prior 4-10-qubit validation range and without project-generated benchmarks. The panel is external and application-oriented, not field-collected production workload evidence; it cannot establish unseen-family, all-width, real-QPU, or optimizer-independent generalization.",
        "source_sha256": {relative: sha256(ROOT / relative) for relative in SOURCES},
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(OUTPUT), "inputs": len(inputs), "widths": [min(row["n_qubits"] for row in inputs), max(row["n_qubits"] for row in inputs)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
