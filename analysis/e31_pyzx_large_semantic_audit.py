"""Run bounded ZX-calculus equality checks on the largest sealed E31 circuits."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import queue
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyzx
from qiskit import qasm2, qpy, transpile

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv"
CELLS = ROOT / "data/v11/e31_factorial_pareto/formal_run/semantic_replay/cells"
OUTPUT_DIR = ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis/pyzx_large_semantic"
BASIS = ["h", "rz", "cx"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _proof_worker(original_qasm: str, optimized_qasm: str, mutate: bool,
                  output: mp.Queue) -> None:
    try:
        original = pyzx.Circuit.from_qasm(original_qasm)
        optimized = pyzx.Circuit.from_qasm(optimized_qasm)
        if mutate:
            optimized.add_gate("X", 0)
        started = time.perf_counter()
        decision = original.verify_equality(
            optimized, up_to_swaps=False, up_to_global_phase=True
        )
        output.put({
            "decision": True if decision is True else None,
            "wall_seconds": time.perf_counter() - started,
            "original_pyzx_gates": len(original.gates),
            "optimized_pyzx_gates": len(optimized.gates),
            "original_graph_vertices": original.to_graph().num_vertices(),
            "optimized_graph_vertices": optimized.to_graph().num_vertices(),
        })
    except BaseException as exc:  # child boundary: serialize any parser/prover failure
        output.put({"error": f"{type(exc).__name__}: {exc}"})


def _bounded_proof(original_qasm: str, optimized_qasm: str, *, mutate: bool,
                   timeout_seconds: float) -> dict[str, object]:
    context = mp.get_context("spawn")
    output = context.Queue()
    process = context.Process(
        target=_proof_worker, args=(original_qasm, optimized_qasm, mutate, output)
    )
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate(); process.join(5)
        return {"status": "TIMEOUT", "decision": None,
                "timeout_seconds": float(timeout_seconds)}
    try:
        result = output.get_nowait()
    except queue.Empty:
        return {"status": "ERROR", "decision": None,
                "error": f"worker exited {process.exitcode} without a result"}
    if "error" in result:
        return {"status": "ERROR", "decision": None, **result}
    return {"status": "PROVED_EQUAL" if result["decision"] is True else "INCONCLUSIVE",
            **result}


def _load_candidates(min_qubits: int) -> list[dict[str, object]]:
    design = pd.read_csv(DESIGN)
    inputs = design.loc[design["n_qubits"].ge(min_qubits), [
        "input_circuit_sha256", "circuit_family", "circuit_id", "n_qubits", "qasm_path"
    ]].drop_duplicates("input_circuit_sha256")
    by_hash = {str(row.input_circuit_sha256): row for row in inputs.itertuples(index=False)}
    candidates = []
    for path in sorted(CELLS.glob("*.json")):
        cell = json.loads(path.read_text(encoding="utf-8"))
        input_hash = str(cell["input_circuit_sha256"])
        if input_hash not in by_hash:
            continue
        candidates.append({"cell": cell, "cell_path": path, "input": by_hash[input_hash]})
    selected = {}
    for candidate in candidates:
        input_hash = str(candidate["cell"]["input_circuit_sha256"])
        rank = (int(candidate["cell"]["recorded_optimized_common_basis_gate_count"]),
                str(candidate["cell"]["semantic_cell_id"]))
        if input_hash not in selected or rank < selected[input_hash][0]:
            selected[input_hash] = (rank, candidate)
    return [item[1] for _, item in sorted(selected.items())]


def build_audit(output_dir: Path = OUTPUT_DIR, *, min_qubits: int = 9,
                timeout_seconds: float = 60.0) -> dict[str, object]:
    candidates = _load_candidates(min_qubits)
    if not candidates:
        raise ValueError("no large successful E31 semantic cells selected")
    records = []
    family_mutant_done: set[str] = set()
    for candidate in candidates:
        cell, row = candidate["cell"], candidate["input"]
        original = qasm2.load(
            ROOT / str(row.qasm_path), custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS
        )
        with (ROOT / str(cell["qpy_path"])).open("rb") as stream:
            optimized_list = qpy.load(stream)
        if len(optimized_list) != 1:
            raise ValueError("semantic replay QPY must contain exactly one circuit")
        optimized = optimized_list[0]
        original_basis = transpile(original, basis_gates=BASIS, optimization_level=0)
        optimized_basis = transpile(optimized, basis_gates=BASIS, optimization_level=0)
        original_qasm, optimized_qasm = qasm2.dumps(original_basis), qasm2.dumps(optimized_basis)
        proof = _bounded_proof(original_qasm, optimized_qasm, mutate=False,
                               timeout_seconds=timeout_seconds)
        family = str(row.circuit_family)
        mutant = None
        if family not in family_mutant_done:
            mutant = _bounded_proof(original_qasm, optimized_qasm, mutate=True,
                                    timeout_seconds=timeout_seconds)
            family_mutant_done.add(family)
        records.append({
            "circuit_family": family, "circuit_id": str(row.circuit_id),
            "input_circuit_sha256": str(row.input_circuit_sha256),
            "semantic_cell_id": str(cell["semantic_cell_id"]),
            "n_qubits": int(row.n_qubits),
            "original_h_rz_cx_gates": int(original_basis.size()),
            "optimized_h_rz_cx_gates": int(optimized_basis.size()),
            "recorded_common_basis_reduction_pct": float(
                cell["recorded_common_basis_gate_reduction_pct"]
            ),
            "proof_status": proof["status"], "proof_decision": proof.get("decision"),
            "proof_wall_seconds": proof.get("wall_seconds"),
            "original_graph_vertices": proof.get("original_graph_vertices"),
            "optimized_graph_vertices": proof.get("optimized_graph_vertices"),
            "mutant_status": None if mutant is None else mutant["status"],
            "mutant_decision": None if mutant is None else mutant.get("decision"),
        })
    frame = pd.DataFrame(records)
    design = pd.read_csv(DESIGN)
    eligible = design.loc[design["n_qubits"].ge(min_qubits), [
        "input_circuit_sha256", "circuit_family"
    ]].drop_duplicates("input_circuit_sha256")
    selected_hashes = set(frame["input_circuit_sha256"])
    omitted = eligible.loc[~eligible["input_circuit_sha256"].isin(selected_hashes)]
    proved = int(frame["proof_status"].eq("PROVED_EQUAL").sum())
    mutants = frame["mutant_status"].notna()
    mutants_rejected = int((mutants & frame["mutant_decision"].isna()).sum())
    complete = proved == len(frame) and mutants_rejected == int(mutants.sum())
    output_dir.mkdir(parents=True, exist_ok=True)
    cells_path = output_dir / "pyzx_large_semantic_cells.csv"
    frame.to_csv(cells_path, index=False)
    audit = {
        "schema_version": "1.0.0",
        "status": "PASS_ALL_SELECTED_LARGE_E31_CELLS_ZX_REDUCED_TO_IDENTITY" if complete
                  else "PARTIAL_ZX_PROOFS_INCLUDE_INCONCLUSIVE_OR_TIMEOUT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "selection": "one minimum-emitted-gate successful semantic cell per unique E31 input with n_qubits >= threshold",
            "min_qubits": int(min_qubits), "cells": int(len(frame)),
            "eligible_design_inputs": int(len(eligible)),
            "inputs_without_successful_semantic_cell": int(len(omitted)),
            "families_without_successful_semantic_cell": sorted(
                omitted["circuit_family"].unique()
            ),
            "families": sorted(frame["circuit_family"].unique()),
            "width_counts": {str(k): int(v) for k, v in frame["n_qubits"].value_counts().sort_index().items()},
            "translated_gate_count_range": [int(frame["original_h_rz_cx_gates"].min()),
                                            int(frame["original_h_rz_cx_gates"].max())],
            "per_case_timeout_seconds": float(timeout_seconds),
        },
        "method": {
            "library": "PyZX", "version": pyzx.__version__,
            "common_symbolic_basis": BASIS,
            "decision": "Circuit.verify_equality(up_to_global_phase=True)",
            "interpretation": (
                "True means the composed ZX diagram was reduced to identity by full_reduce; "
                "a non-True result is INCONCLUSIVE and is never classified as inequivalent."
            ),
        },
        "results": {
            "proved_equal": proved, "inconclusive_or_timeout": int(len(frame) - proved),
            "one_x_mutants": int(mutants.sum()), "mutants_not_proved_equal": mutants_rejected,
            "maximum_proof_wall_seconds": float(frame["proof_wall_seconds"].max()),
        },
        "metric_dispositions": {
            "7.25": (
                f"PASS: PyZX full-reduce proves equality for all {len(frame)} selected sealed "
                f"E31 cells at widths {int(frame['n_qubits'].min())}-{int(frame['n_qubits'].max())}, "
                "while one X-mutant per family is not proved equal"
                if complete else
                f"PARTIAL: PyZX proves {proved}/{len(frame)} selected large E31 cells; remaining "
                "cases are inconclusive/timeouts rather than semantic failures"
            )
        },
        "claim_boundary": (
            "This is a bounded ZX-calculus panel at the largest E31 widths, not all 6,858 cells. "
            "Selection requires a successful sealed semantic cell; the omitted large-width inputs "
            "are reported explicitly rather than treated as verified. "
            "Successful identity reduction is symbolic evidence; PyZX incompleteness means failure "
            "to reduce would be inconclusive. Qiskit is used only to parse QASM/QPY and translate "
            "both sides identically to h/rz/cx before PyZX parsing."
        ),
        "source_bindings": {
            "design_manifest.csv": _sha(DESIGN),
            "analysis/e31_pyzx_large_semantic_audit.py": _sha(Path(__file__)),
        },
        "artifacts": {"pyzx_large_semantic_cells.csv": {
            "rows": int(len(frame)), "sha256": _sha(cells_path)
        }},
    }
    output = output_dir / "pyzx_large_semantic_audit.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(output)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--min-qubits", type=int, default=9)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    args = parser.parse_args()
    audit = build_audit(args.output_dir, min_qubits=args.min_qubits,
                        timeout_seconds=args.timeout_seconds)
    print(json.dumps({"status": audit["status"], "scope": audit["scope"],
                      "results": audit["results"],
                      "metric_disposition": audit["metric_dispositions"]["7.25"]},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
