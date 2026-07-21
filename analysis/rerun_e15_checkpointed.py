"""Checkpointed E15 rerun -> data/v9/e15/.

Replicates experiments/e15_multi_compiler/run.py::run(mode='full', seed=42,
max_qubits_fidelity=10, skip_cirq=True, skip_tket=True) row-for-row, flushing
rows to a partial CSV after every circuit so a killed run can resume. Uses
rerun_to_v9.load_patched_module (experiment functions unmodified, output
redirected to v9) plus the batch-1 fast-fidelity runtime accommodation for the
custom-optimizer path only (the Qiskit rows use average_gate_fidelity exactly
as canonical did).

Budget: stops gracefully after RERUN_MAX_SECONDS (default 215); re-run resumes.

Usage:
  /d/Downloads/miniforge3/python analysis/rerun_e15_checkpointed.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.rerun_to_v9 import load_patched_module, patch_fast_fidelity  # noqa: E402

PARTIAL_DIR = PROJECT_ROOT / "data" / "v9" / "e15_partial"
PARTIAL_CSV = PARTIAL_DIR / "partial.csv"
FINAL_DIR = PROJECT_ROOT / "data" / "v9" / "e15"

MODE, SEED, MQF = "full", 42, 10
SKIP_CIRQ, SKIP_TKET = True, True  # canonical metadata values
MAX_SECONDS = float(os.environ.get("RERUN_MAX_SECONDS", "215"))

ALL_COLS = ["schema_version", "experiment_id", "run_id", "timestamp_utc",
            "circuit_id", "circuit_family", "n_qubits", "baseline_gate_count",
            "optimized_gate_count", "reduction", "reduction_pct",
            "depth_reduction", "two_qubit_reduction", "cnot_reduction",
            "fidelity", "runtime_seconds", "compiler", "compiler_backend",
            "compiler_opt_level", "compiler_status", "conversion_format",
            "conversion_caveat", "seed", "trial", "source_file",
            "source_sha256", "input_circuit_sha256", "output_circuit_sha256",
            "notes"]


def main() -> None:
    t_start = time.time()
    patch_fast_fidelity(n_samples=32)
    glb = load_patched_module("e15")
    generate_extended_suite = glb["generate_extended_suite"]
    average_gate_fidelity = glb["average_gate_fidelity"]
    circuit_sha256 = glb["circuit_sha256"]
    _count_metrics = glb["_count_metrics"]
    _safe_ratio = glb["_safe_ratio"]
    _qiskit_transpile = glb["_qiskit_transpile"]
    GreedyGateCancellation = glb["GreedyGateCancellation"]
    CommutationRewriter = glb["CommutationRewriter"]
    HybridCommuteRewrite = glb["HybridCommuteRewrite"]
    run_metadata = glb["run_metadata"]
    file_sha256 = glb["file_sha256"]
    SCHEMA_VERSION = glb["SCHEMA_VERSION"]
    EXPERIMENT_ID = glb["EXPERIMENT_ID"]
    VERSION = glb["VERSION"]
    script_path = Path(glb["__file__"])

    run_id = f"e15_{MODE}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    rid_file = PARTIAL_DIR / "run_id.txt"
    PARTIAL_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    if rid_file.exists():
        run_id = rid_file.read_text().strip()
    else:
        rid_file.write_text(run_id)

    done_blocks = set()
    if PARTIAL_CSV.exists():
        prev = pd.read_csv(
            PARTIAL_CSV,
            usecols=["circuit_id", "compiler", "compiler_opt_level"])
        done_blocks = set(zip(prev["circuit_id"], prev["compiler"],
                              prev["compiler_opt_level"].astype(str)))
        print(f"[e15-ckpt] resume: {len(done_blocks)} blocks done", flush=True)

    circuits = generate_extended_suite(mode=MODE, seed=SEED)
    n_todo = sum(
        (0 if (b.circuit_id, "custom", "none") in done_blocks else 1)
        + sum(0 if (b.circuit_id, "qiskit", str(lv)) in done_blocks else 1
              for lv in (0, 1, 2, 3))
        for b in circuits)
    print(f"[e15-ckpt] {len(circuits)} circuits, {n_todo} blocks to do, "
          f"run_id={run_id}", flush=True)

    our_optimizers = {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "commutation_phase2": CommutationRewriter(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }

    def flush(rows):
        chunk = pd.DataFrame(rows).reindex(columns=ALL_COLS)
        tmp = PARTIAL_DIR / "chunk.tmp"
        chunk.to_csv(tmp, index=False)
        with open(PARTIAL_CSV, "a", newline="") as fout, open(tmp, "r") as fin:
            if PARTIAL_CSV.stat().st_size == 0:
                fout.write(fin.read())
            else:
                next(fin)
                fout.writelines(fin.readlines())
        os.remove(tmp)

    def base_row(bench, circuit, trial):
        return {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "run_id": run_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "circuit_id": bench.circuit_id,
            "circuit_family": bench.family,
            "n_qubits": circuit.num_qubits,
            "seed": bench.seed,
            "trial": trial,
            "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
            "source_sha256": file_sha256(script_path),
            "notes": bench.notes,
        }

    for trial, bench in enumerate(circuits):
        need_custom = (bench.circuit_id, "custom", "none") not in done_blocks
        levels_todo = [lv for lv in (0, 1, 2, 3)
                       if (bench.circuit_id, "qiskit", str(lv)) not in done_blocks]
        if not need_custom and not levels_todo:
            continue
        if time.time() - t_start > MAX_SECONDS:
            print(f"[e15-ckpt] budget reached, {len(done_blocks)} blocks done; "
                  f"rerun to resume", flush=True)
            return
        t_circ = time.time()
        circuit = bench.circuit
        input_hash = circuit_sha256(circuit)
        orig_m = _count_metrics(circuit)

        # --- custom optimizers ---
        if need_custom:
            rows = []
            for opt_name, opt in our_optimizers.items():
                start = time.time()
                result = opt.optimize(circuit, target=circuit)
                runtime = time.time() - start
                output_hash = circuit_sha256(result.optimized_circuit)
                opt_m = _count_metrics(result.optimized_circuit)
                fidelity = result.fidelity
                if fidelity is None or fidelity == 0.0:
                    exact = average_gate_fidelity(
                        result.optimized_circuit, circuit, max_qubits=MQF)
                    fidelity = exact if exact is not None else result.fidelity
                row = base_row(bench, circuit, trial)
                row.update({
                    "baseline_gate_count": result.original_size,
                    "optimized_gate_count": result.optimized_size,
                    "reduction": result.reduction,
                    "reduction_pct": 100.0 * result.reduction,
                    "depth_reduction": _safe_ratio(orig_m["depth"], opt_m["depth"]),
                    "two_qubit_reduction": _safe_ratio(orig_m["two_q"], opt_m["two_q"]),
                    "cnot_reduction": _safe_ratio(orig_m["cnot"], opt_m["cnot"]),
                    "fidelity": fidelity,
                    "runtime_seconds": runtime,
                    "compiler": "custom",
                    "compiler_backend": opt_name,
                    "compiler_opt_level": "none",
                    "compiler_status": "ok",
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": output_hash,
                })
                rows.append(row)
            flush(rows)
            done_blocks.add((bench.circuit_id, "custom", "none"))
            print(f"[e15-ckpt] {bench.circuit_id}/custom done "
                  f"({len(done_blocks)} blocks)", flush=True)

        # --- Qiskit transpiler levels 0-3 ---
        # Cost guard (same rule as E12): exact average-gate fidelity composes
        # the transpiled circuit as a dense Operator; at n>=10 with >1500
        # transpiled gates (qwalk_9: ~6.9k) one level exceeds the per-call
        # budget. Defer only the qiskit rows; custom rows still run.
        qiskit_defer = False
        if levels_todo and MQF >= circuit.num_qubits >= 10:
            probe, _ = _qiskit_transpile(circuit, 0, seed_transpiler=SEED)
            if probe.size() > 1500:
                qiskit_defer = True
                dfile = PARTIAL_DIR / "deferred.json"
                deferred = json.loads(dfile.read_text()) if dfile.exists() else []
                deferred.append({
                    "circuit_id": bench.circuit_id,
                    "n_qubits": circuit.num_qubits,
                    "baseline_gate_count": int(circuit.size()),
                    "compiled_l0_gate_count": int(probe.size()),
                    "rows_deferred": "qiskit L0-L3",
                    "reason": "exact fidelity on n>=10 with >1500 transpiled "
                              "gates exceeds per-call compute budget",
                })
                dfile.write_text(json.dumps(deferred, indent=2))
                print(f"[e15-ckpt] {bench.circuit_id} qiskit rows DEFERRED "
                      f"(compiled L0={probe.size()} gates)", flush=True)
                for lv in levels_todo:
                    done_blocks.add((bench.circuit_id, "qiskit", str(lv)))
        for level in levels_todo:
            if qiskit_defer:
                break
            opt_circ, runtime = _qiskit_transpile(circuit, level, seed_transpiler=SEED)
            opt_m = _count_metrics(opt_circ)
            output_hash = circuit_sha256(opt_circ)
            fidelity = average_gate_fidelity(opt_circ, circuit, max_qubits=MQF)
            row = base_row(bench, circuit, trial)
            row.update({
                "baseline_gate_count": circuit.size(),
                "optimized_gate_count": opt_circ.size(),
                "reduction": 1.0 - opt_circ.size() / circuit.size() if circuit.size() > 0 else 0.0,
                "reduction_pct": 100.0 * (1.0 - opt_circ.size() / circuit.size()) if circuit.size() > 0 else 0.0,
                "depth_reduction": _safe_ratio(orig_m["depth"], opt_m["depth"]),
                "two_qubit_reduction": _safe_ratio(orig_m["two_q"], opt_m["two_q"]),
                "cnot_reduction": _safe_ratio(orig_m["cnot"], opt_m["cnot"]),
                "fidelity": fidelity,
                "runtime_seconds": runtime,
                "compiler": "qiskit",
                "compiler_backend": "transpiler",
                "compiler_opt_level": level,
                "compiler_status": "ok",
                "conversion_format": "native",
                "input_circuit_sha256": input_hash,
                "output_circuit_sha256": output_hash,
            })
            # flush per (circuit, level): an over-budget fidelity call
            # (e.g. qwalk_8) never loses completed levels
            flush([row])
            done_blocks.add((bench.circuit_id, "qiskit", str(level)))
            print(f"[e15-ckpt] {bench.circuit_id}/L{level} done "
                  f"({len(done_blocks)} blocks)", flush=True)

        print(f"[e15-ckpt] {bench.circuit_id} (n={circuit.num_qubits}) circuit done in "
              f"{time.time()-t_circ:.1f}s", flush=True)

    df = pd.read_csv(PARTIAL_CSV)
    csv_path = FINAL_DIR / f"e15_multi_compiler_{run_id}.csv"
    tmp_final = FINAL_DIR / "final.tmp"
    df.to_csv(tmp_final, index=False)
    os.replace(tmp_final, csv_path)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "description": "Multi-compiler baseline comparison (Qiskit, Cirq, t|ket>)",
        "mode": MODE,
        "seed": SEED,
        "qiskit_transpiler_seed": SEED,
        "max_qubits_fidelity": MQF,
        "skip_cirq": SKIP_CIRQ,
        "skip_tket": SKIP_TKET,
        "canonical_data_file": csv_path.name,
        "n_input_circuits": len(circuits),
        "n_rows": len(df),
        "compilers": ["custom", "qiskit"],
        "circuit_families": sorted({b.family for b in circuits}),
        "rerun_note": "checkpointed rerun via analysis/rerun_e15_checkpointed.py; "
                      "fast-fidelity runtime accommodation on the custom-optimizer "
                      "path only (exact<=10q, 32 samples, equality+Clifford "
                      "shortcuts, memoized); Qiskit rows computed exactly as canonical",
    })
    dfile = PARTIAL_DIR / "deferred.json"
    if dfile.exists():
        metadata["deferred_circuits"] = json.loads(dfile.read_text())
        metadata["deferred_reason"] = ("exact fidelity on n>=10 with >1500 "
                                       "transpiled gates exceeds per-call compute "
                                       "budget (qiskit rows only)")
    with (FINAL_DIR / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"[e15-ckpt] COMPLETE: {len(df)} rows -> {csv_path}", flush=True)


if __name__ == "__main__":
    main()
