"""Checkpointed E12 (no-coupling-map mode) rerun -> data/v9/e12/.

Replicates experiments/e12_compiler_baseline/run.py::run(mode='full', seed=42,
max_qubits_fidelity=10, no_coupling_map=True) row-for-row, flushing rows to a
partial CSV after every circuit so a killed run can resume. Uses
rerun_to_v9.load_patched_module so the experiment's own functions are used
unmodified, with output redirected to v9.

Budget: stops gracefully after MAX_SECONDS (default 215) and can be re-run to
resume. Canonical run was env python 3.10 / numpy 2.2.6; rerun uses the repo
python 3.12 / numpy 1.26.4 (qiskit identical 2.4.1).

Usage:
  /d/Downloads/miniforge3/python analysis/rerun_e12_checkpointed.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import qiskit
from qiskit import transpile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.rerun_to_v9 import load_patched_module  # noqa: E402

PARTIAL_DIR = PROJECT_ROOT / "data" / "v9" / "e12_partial"
PARTIAL_CSV = PARTIAL_DIR / "partial.csv"
FINAL_DIR = PROJECT_ROOT / "data" / "v9" / "e12"

MODE, SEED, MQF = "full", 42, 10
MAX_SECONDS = float(os.environ.get("RERUN_MAX_SECONDS", "215"))

ALL_COLS = ["schema_version", "experiment_id", "run_id", "timestamp_utc",
            "circuit_id", "circuit_family", "circuit_type", "benchmark_suite",
            "n_qubits", "depth", "gate_count_total", "gate_count_1q",
            "gate_count_2q", "gate_count_multiq", "gate_counts_json",
            "compiled_depth", "compiled_gate_counts_json",
            "baseline_gate_count", "optimized_gate_count", "reduction",
            "reduction_pct", "fidelity", "fidelity_source", "success",
            "runtime_seconds", "optimizer", "optimizer_version",
            "optimizer_config_json", "compiler", "compiler_version",
            "compiler_optimization_level", "compiler_config_id", "seed",
            "trial", "source_file", "source_sha256",
            "input_circuit_sha256", "output_circuit_sha256", "env_id", "notes"]


def main() -> None:
    t_start = time.time()
    glb = load_patched_module("e12")
    generate_real_circuit_suite = glb["generate_real_circuit_suite"]
    average_gate_fidelity = glb["average_gate_fidelity"]
    circuit_sha256 = glb["circuit_sha256"]
    gate_counts = glb["gate_counts"]
    run_metadata = glb["run_metadata"]
    file_sha256 = glb["file_sha256"]
    SCHEMA_VERSION = glb["SCHEMA_VERSION"]
    EXPERIMENT_ID = glb["EXPERIMENT_ID"]
    VERSION = glb["VERSION"]
    COMPILER_CONFIG_ID = glb["COMPILER_CONFIG_ID"]
    BASIS_GATES = glb["BASIS_GATES"]
    DEFAULT_HEAVY_HEX_D = glb["DEFAULT_HEAVY_HEX_D"]
    script_path = Path(glb["__file__"])

    run_id = f"e12_{MODE}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_nocoupling"
    rid_file = PARTIAL_DIR / "run_id.txt"
    PARTIAL_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    if rid_file.exists():
        run_id = rid_file.read_text().strip()
    else:
        rid_file.write_text(run_id)

    done_pairs = set()
    if PARTIAL_CSV.exists():
        prev = pd.read_csv(PARTIAL_CSV,
                           usecols=["circuit_id", "compiler_optimization_level"])
        done_pairs = set(zip(prev["circuit_id"], prev["compiler_optimization_level"]))
        print(f"[e12-ckpt] resume: {len(done_pairs)} (circuit, level) pairs done",
              flush=True)

    circuits = generate_real_circuit_suite(mode=MODE, seed=SEED)
    todo = [(b, lv) for b in circuits for lv in (0, 1, 2, 3)
            if (b.circuit_id, lv) not in done_pairs]
    print(f"[e12-ckpt] {len(circuits)} circuits, {len(todo)} pairs to do, "
          f"run_id={run_id}", flush=True)

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

    for trial, bench in enumerate(circuits):
        levels_todo = [lv for lv in (0, 1, 2, 3)
                       if (bench.circuit_id, lv) not in done_pairs]
        if not levels_todo:
            continue
        if time.time() - t_start > MAX_SECONDS:
            print(f"[e12-ckpt] budget reached, "
                  f"{len(done_pairs)}/{len(circuits)*4} pairs done; "
                  f"rerun to resume", flush=True)
            return
        t_circ = time.time()
        circuit = bench.circuit
        # Cost guard: exact average-gate fidelity composes the *compiled*
        # circuit as a dense Operator. At n=10 (1024-dim) a transpiled circuit
        # with >1500 basis gates (qwalk_9: ~6.9k) costs >250 s per level,
        # exceeding the per-call compute budget. Defer the whole circuit and
        # record it as a documented gap (same root cause as batch-1 E17
        # qwalk_8 deferral).
        if circuit.num_qubits >= 10 and circuit.num_qubits <= MQF:
            probe = transpile(circuit, optimization_level=0, seed_transpiler=SEED)
            if probe.size() > 1500:
                dfile = PARTIAL_DIR / "deferred.json"
                deferred = json.loads(dfile.read_text()) if dfile.exists() else []
                deferred.append({
                    "circuit_id": bench.circuit_id,
                    "n_qubits": circuit.num_qubits,
                    "baseline_gate_count": int(circuit.size()),
                    "compiled_l0_gate_count": int(probe.size()),
                    "reason": "exact fidelity on n>=10 with >1500 compiled gates "
                              "exceeds per-call compute budget (>250 s/level)",
                })
                dfile.write_text(json.dumps(deferred, indent=2))
                for lv in levels_todo:
                    done_pairs.add((bench.circuit_id, lv))
                print(f"[e12-ckpt] {bench.circuit_id} DEFERRED "
                      f"(n={circuit.num_qubits}, compiled L0={probe.size()} gates)",
                      flush=True)
                continue
        input_hash = circuit_sha256(circuit)
        counts = gate_counts(circuit)
        baseline_gate_count = int(circuit.size())
        rows = []
        for level in levels_todo:
            start = time.time()
            error = ""
            try:
                compiled = transpile(circuit, optimization_level=level,
                                     seed_transpiler=SEED)
                runtime = time.time() - start
                optimized_gate_count = int(compiled.size())
                reduction = 1.0 - optimized_gate_count / baseline_gate_count if baseline_gate_count else 0.0
                fidelity = average_gate_fidelity(compiled, circuit, max_qubits=MQF)
                fidelity_source = "exact" if fidelity is not None else "unavailable"
                success = bool(fidelity is not None and fidelity >= 0.999)
                output_hash = circuit_sha256(compiled)
                compiled_counts = gate_counts(compiled)
            except Exception as exc:
                runtime = time.time() - start
                optimized_gate_count = -1
                reduction = 0.0
                fidelity = None
                fidelity_source = "error"
                success = False
                output_hash = ""
                compiled_counts = {"gate_count_total": -1, "depth": -1,
                                   "gate_count_1q": -1, "gate_count_2q": -1,
                                   "gate_count_multiq": -1, "gate_counts_json": "{}"}
                error = repr(exc)
            rows.append({
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "circuit_id": bench.circuit_id,
                "circuit_family": bench.family,
                "circuit_type": bench.circuit_type,
                "benchmark_suite": bench.suite,
                "n_qubits": circuit.num_qubits,
                "depth": counts["depth"],
                "gate_count_total": counts["gate_count_total"],
                "gate_count_1q": counts["gate_count_1q"],
                "gate_count_2q": counts["gate_count_2q"],
                "gate_count_multiq": counts["gate_count_multiq"],
                "gate_counts_json": counts["gate_counts_json"],
                "compiled_depth": compiled_counts["depth"],
                "compiled_gate_counts_json": compiled_counts["gate_counts_json"],
                "baseline_gate_count": baseline_gate_count,
                "optimized_gate_count": optimized_gate_count,
                "reduction": reduction,
                "reduction_pct": 100.0 * reduction,
                "fidelity": fidelity,
                "fidelity_source": fidelity_source,
                "success": success,
                "runtime_seconds": runtime,
                "optimizer": "none",
                "optimizer_version": "none",
                "optimizer_config_json": "{}",
                "compiler": "qiskit_transpile",
                "compiler_version": qiskit.__version__,
                "compiler_optimization_level": level,
                "compiler_config_id": COMPILER_CONFIG_ID,
                "seed": SEED,
                "trial": trial,
                "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                "source_sha256": file_sha256(script_path),
                "input_circuit_sha256": input_hash,
                "output_circuit_sha256": output_hash,
                "env_id": run_id,
                "notes": error,
            })
            # flush per (circuit, level) so an over-budget single level
            # (e.g. qwalk_9 exact fidelity on n=10) never loses completed work
            flush(rows)
            done_pairs.add((bench.circuit_id, level))
            rows = []
            print(f"[e12-ckpt] {bench.circuit_id}/L{level} (n={circuit.num_qubits}) "
                  f"done in {time.time()-start:.1f}s "
                  f"({len(done_pairs)}/{len(circuits)*4})", flush=True)

    # Assemble final CSV + metadata
    df = pd.read_csv(PARTIAL_CSV)
    csv_path = FINAL_DIR / f"e12_compiler_baseline_{run_id}.csv"
    tmp_final = FINAL_DIR / "final.tmp"
    df.to_csv(tmp_final, index=False)
    os.replace(tmp_final, csv_path)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "description": "Qiskit transpiler compiler baseline comparison",
        "mode": MODE,
        "seed": SEED,
        "max_qubits_fidelity": MQF,
        "canonical_data_file": csv_path.name,
        "n_input_circuits": len(circuits),
        "n_rows": len(df),
        "compiler": "qiskit_transpile",
        "compiler_version": qiskit.__version__,
        "optimization_levels": [0, 1, 2, 3],
        "compiler_config_id": COMPILER_CONFIG_ID,
        "coupling_map": "none",
        "coupling_map_base_d": DEFAULT_HEAVY_HEX_D,
        "coupling_map_selection": "none",
        "no_coupling_map": True,
        "fairness_note": ("no_coupling_map=True: Qiskit solves optimization only "
                          "(no routing), matching the scope of the custom peephole "
                          "optimizer. This is the FAIR comparison mode (review H1/F3)."),
        "basis_gates": "none (native gate set)",
        "rerun_note": "checkpointed rerun via analysis/rerun_e12_checkpointed.py; "
                      "no runtime accommodations (transpile + exact fidelity n<=10)",
    })
    dfile = PARTIAL_DIR / "deferred.json"
    if dfile.exists():
        metadata["deferred_circuits"] = json.loads(dfile.read_text())
        metadata["deferred_reason"] = ("exact fidelity on n>=10 with >1500 compiled "
                                       "gates exceeds per-call compute budget")
    with (FINAL_DIR / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"[e12-ckpt] COMPLETE: {len(df)} rows -> {csv_path}", flush=True)


if __name__ == "__main__":
    main()
