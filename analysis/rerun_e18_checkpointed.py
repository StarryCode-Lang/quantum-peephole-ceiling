"""Checkpointed E18 rerun -> data/v9/e18/.

Replicates experiments/e18_clifford_t/run.py::run(mode='full', seed=42,
max_qubits_fidelity=10) row-for-row, flushing rows after every circuit.

Guard rails (input drift from canonical: generator changed, decompose now
succeeds on families that previously threw BasisTranslator errors, producing
circuits up to 29,760 gates):
  - Skip decomposition if original circuit > 600 gates (canonical ok max = 152)
  - Defer if decomposed Clifford+T circuit > 2500 gates (canonical ok max = 152)
  - Time budget: 215s per call, rerun resumes

Usage:
  D:\\Downloads\\miniforge3\\python analysis/rerun_e18_checkpointed.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.rerun_to_v9 import load_patched_module, patch_fast_fidelity

PARTIAL_DIR = PROJECT_ROOT / "data" / "v9" / "e18_partial"
PARTIAL_CSV = PARTIAL_DIR / "partial.csv"
DEFERRED_FILE = PARTIAL_DIR / "deferred.json"
FINAL_DIR = PROJECT_ROOT / "data" / "v9" / "e18"

MODE, SEED, MQF = "full", 42, 10
MAX_SECONDS = float(os.environ.get("RERUN_MAX_SECONDS", "215"))
SKIP_ORIG_GT = 600      # skip decomposition if original > this many gates
DEFER_DECOMP_GT = 2500  # defer if decomposed > this many gates

ALL_COLS = [
    "schema_version", "experiment_id", "run_id", "timestamp_utc",
    "circuit_id", "circuit_family", "circuit_type", "n_qubits",
    "gate_set", "baseline_gate_count", "optimized_gate_count",
    "reduction", "reduction_pct", "depth_reduction",
    "two_qubit_reduction", "cnot_reduction", "t_count_reduction",
    "baseline_t_count", "optimized_t_count", "fidelity", "success",
    "runtime_seconds", "optimizer", "seed", "trial",
    "source_file", "source_sha256", "input_circuit_sha256",
    "output_circuit_sha256", "notes", "status", "error_message",
    "error_type",
]


def main() -> None:
    t_start = time.time()
    patch_fast_fidelity(n_samples=32)
    glb = load_patched_module("e18")

    generate_extended_suite = glb["generate_extended_suite"]
    average_gate_fidelity = glb["average_gate_fidelity"]
    circuit_sha256 = glb["circuit_sha256"]
    decompose_to_clifford_t = glb["decompose_to_clifford_t"]
    count_t_gates = glb["count_t_gates"]
    _count_metrics = glb["_count_metrics"]
    _safe_ratio = glb["_safe_ratio"]
    GreedyGateCancellation = glb["GreedyGateCancellation"]
    CommutationRewriter = glb["CommutationRewriter"]
    HybridCommuteRewrite = glb["HybridCommuteRewrite"]
    run_metadata = glb["run_metadata"]
    file_sha256 = glb["file_sha256"]
    SCHEMA_VERSION = glb["SCHEMA_VERSION"]
    EXPERIMENT_ID = glb["EXPERIMENT_ID"]
    VERSION = glb["VERSION"]
    script_path = Path(glb["__file__"])

    run_id = f"e18_{MODE}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    rid_file = PARTIAL_DIR / "run_id.txt"
    PARTIAL_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    if rid_file.exists():
        run_id = rid_file.read_text().strip()
    else:
        rid_file.write_text(run_id)

    done_circuits = set()
    if PARTIAL_CSV.exists():
        prev = pd.read_csv(PARTIAL_CSV, usecols=["circuit_id"])
        done_circuits = set(prev["circuit_id"].tolist())
        print(f"[e18-ckpt] resume: {len(done_circuits)} circuits done", flush=True)

    deferred = []
    if DEFERRED_FILE.exists():
        deferred = json.loads(DEFERRED_FILE.read_text())
        print(f"[e18-ckpt] {len(deferred)} deferred circuits", flush=True)

    circuits = generate_extended_suite(mode=MODE, seed=SEED)
    print(f"[e18-ckpt] {len(circuits)} circuits total, "
          f"{len(circuits) - len(done_circuits)} to do", flush=True)

    our_optimizers = {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "commutation_phase2": CommutationRewriter(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }

    def flush(rows):
        if not rows:
            return
        chunk = pd.DataFrame(rows).reindex(columns=ALL_COLS)
        tmp = PARTIAL_DIR / "chunk.tmp"
        chunk.to_csv(tmp, index=False)
        with open(PARTIAL_CSV, "a", newline="") as fout, open(tmp, "r") as fin:
            if not PARTIAL_CSV.exists() or PARTIAL_CSV.stat().st_size == 0:
                fout.write(fin.read())
            else:
                next(fin)
                fout.writelines(fin.readlines())
        os.remove(tmp)

    for trial, bench in enumerate(circuits):
        if bench.circuit_id in done_circuits:
            continue
        if time.time() - t_start > MAX_SECONDS:
            print(f"[e18-ckpt] budget reached, {len(done_circuits)} done; "
                  f"rerun to resume", flush=True)
            break

        circuit = bench.circuit
        orig_size = circuit.size()

        # Guard: skip if original circuit too large
        if orig_size > SKIP_ORIG_GT:
            reason = f"original too large ({orig_size} gates > {SKIP_ORIG_GT})"
            deferred.append({"circuit_id": bench.circuit_id, "reason": reason,
                             "orig_size": orig_size})
            print(f"  SKIP {bench.circuit_id}: {reason}", flush=True)
            done_circuits.add(bench.circuit_id)
            continue

        # Decompose to Clifford+T
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                from qiskit import transpile
                clifford_t_circuit = transpile(
                    circuit, basis_gates=['h', 's', 'sdg', 't', 'tdg', 'cx', 'x', 'y', 'z'],
                    optimization_level=0, seed_transpiler=42)
        except Exception as exc:
            # Record decompose_error (same as canonical)
            row = {
                "schema_version": SCHEMA_VERSION, "experiment_id": EXPERIMENT_ID,
                "run_id": run_id, "circuit_id": bench.circuit_id,
                "circuit_family": bench.family, "circuit_type": bench.circuit_type,
                "n_qubits": circuit.num_qubits, "gate_set": "clifford_t",
                "optimizer": "none", "status": "decompose_error",
                "error_message": str(exc)[:200], "error_type": type(exc).__name__,
                "trial": trial, "seed": bench.seed,
            }
            flush([row])
            done_circuits.add(bench.circuit_id)
            print(f"  {bench.circuit_id}: decompose_error ({type(exc).__name__})", flush=True)
            continue

        decomp_size = clifford_t_circuit.size()

        # Guard: defer if decomposed circuit too large
        if decomp_size > DEFER_DECOMP_GT:
            reason = f"decomposed too large ({decomp_size} gates > {DEFER_DECOMP_GT})"
            deferred.append({"circuit_id": bench.circuit_id, "reason": reason,
                             "decomp_size": decomp_size, "orig_size": orig_size})
            print(f"  DEFER {bench.circuit_id}: {reason}", flush=True)
            done_circuits.add(bench.circuit_id)
            continue

        input_hash = circuit_sha256(clifford_t_circuit)
        orig_counts = clifford_t_circuit.size()
        orig_m = _count_metrics(clifford_t_circuit)
        orig_t = count_t_gates(clifford_t_circuit)

        rows = []
        for opt_name, opt in our_optimizers.items():
            start = time.time()
            try:
                result = opt.optimize(clifford_t_circuit, target=clifford_t_circuit)
                runtime = time.time() - start

                output_hash = circuit_sha256(result.optimized_circuit)
                opt_m = _count_metrics(result.optimized_circuit)
                opt_t = count_t_gates(result.optimized_circuit)

                fidelity = result.fidelity
                if fidelity is None or fidelity == 0.0:
                    exact = average_gate_fidelity(
                        result.optimized_circuit, clifford_t_circuit, max_qubits=MQF)
                    fidelity = exact if exact is not None else result.fidelity

                row = {
                    "schema_version": SCHEMA_VERSION, "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "circuit_id": bench.circuit_id, "circuit_family": bench.family,
                    "circuit_type": bench.circuit_type, "n_qubits": circuit.num_qubits,
                    "gate_set": "clifford_t",
                    "baseline_gate_count": orig_counts,
                    "optimized_gate_count": result.optimized_size,
                    "reduction": result.reduction,
                    "reduction_pct": 100.0 * result.reduction,
                    "depth_reduction": _safe_ratio(orig_m["depth"], opt_m["depth"]),
                    "two_qubit_reduction": _safe_ratio(orig_m["two_q"], opt_m["two_q"]),
                    "cnot_reduction": _safe_ratio(orig_m["cnot"], opt_m["cnot"]),
                    "t_count_reduction": _safe_ratio(orig_m["t_count"], opt_m["t_count"]),
                    "baseline_t_count": orig_m["t_count"],
                    "optimized_t_count": opt_m["t_count"],
                    "fidelity": fidelity, "success": bool(result.success),
                    "runtime_seconds": runtime, "optimizer": opt_name,
                    "seed": bench.seed, "trial": trial,
                    "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                    "source_sha256": file_sha256(script_path),
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": output_hash,
                    "notes": bench.notes, "status": "ok",
                }
            except Exception as exc:
                row = {
                    "schema_version": SCHEMA_VERSION, "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id, "circuit_id": bench.circuit_id,
                    "circuit_family": bench.family, "circuit_type": bench.circuit_type,
                    "n_qubits": circuit.num_qubits, "gate_set": "clifford_t",
                    "optimizer": opt_name, "status": "optimize_error",
                    "error_message": str(exc)[:200], "error_type": type(exc).__name__,
                    "trial": trial, "seed": bench.seed,
                }
            rows.append(row)

        flush(rows)
        done_circuits.add(bench.circuit_id)
        el = time.time() - t_start
        print(f"  {bench.circuit_id}: {decomp_size} gates, 3 opts, "
              f"{el:.0f}s total", flush=True)

        # Save deferred list
        DEFERRED_FILE.write_text(json.dumps(deferred, indent=2))

    # Save deferred list
    DEFERRED_FILE.write_text(json.dumps(deferred, indent=2))

    # Check if complete
    remaining = len(circuits) - len(done_circuits)
    if remaining > 0:
        print(f"\n[e18-ckpt] INCOMPLETE: {remaining} circuits remaining. "
              f"Rerun to resume.", flush=True)
    else:
        print(f"\n[e18-ckpt] COMPLETE: {len(done_circuits)} circuits processed, "
              f"{len(deferred)} deferred", flush=True)
        # Finalize: merge partial into final CSV
        if PARTIAL_CSV.exists():
            df = pd.read_csv(PARTIAL_CSV)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_csv = FINAL_DIR / f"e18_clifford_t_{run_id}.csv"
            tmp = FINAL_DIR / (final_csv.name + ".tmp")
            df.to_csv(tmp, index=False)
            tmp.replace(final_csv)

            # Metadata
            meta = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
            meta.update({
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "description": "Clifford+T gate-set optimization experiment (rerun)",
                "mode": MODE, "seed": SEED, "max_qubits_fidelity": MQF,
                "gate_set": "clifford_t",
                "canonical_data_file": final_csv.name,
                "n_input_circuits": len(circuits),
                "n_rows": len(df),
                "deferred_circuits": len(deferred),
                "deferred_details": deferred,
            })
            mp = FINAL_DIR / "metadata.json"
            tmp3 = FINAL_DIR / "metadata.json.tmp"
            with open(tmp3, "w") as f:
                json.dump(meta, f, indent=2, sort_keys=True)
            tmp3.replace(mp)
            print(f"  Final: {len(df)} rows -> {final_csv}", flush=True)
            if "reduction" in df.columns:
                summary = df.dropna(subset=["reduction"]).groupby("optimizer").agg(
                    {"reduction": "mean", "depth_reduction": "mean",
                     "cnot_reduction": "mean", "t_count_reduction": "mean"})
                print(summary.to_string())


if __name__ == "__main__":
    main()
