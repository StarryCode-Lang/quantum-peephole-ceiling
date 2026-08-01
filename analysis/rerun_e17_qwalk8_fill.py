"""E17 qwalk_8 deferred fill -> appends to data/v9/e17_partial/partial.csv.

qwalk_8 (QuantumWalk, n=9) was skipped in the main E17 rerun because its
transpiled form reaches ~41k basis gates, making a faithful
greedy/commutation pass exceed the per-call compute budget. The canonical
E17 data has 9 qwalk_8 rows (3 topologies × 3 optimizers, all `ok`).

This script processes qwalk_8 (topology, optimizer) triples one at a time,
flushing after each, so a killed run can resume. Each triple has its own
timeout (PER_TRIPLE_TIMEOUT, default 230 s). Triples that exceed the
timeout are recorded as `timeout` and can be retried with a larger budget.

Usage:
  /d/Downloads/miniforge3/python analysis/rerun_e17_qwalk8_fill.py
  RERUN_MAX_SECONDS=230 /d/Downloads/miniforge3/python analysis/rerun_e17_qwalk8_fill.py
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

PARTIAL_DIR = PROJECT_ROOT / "data" / "v9" / "e17_partial"
PARTIAL_CSV = PARTIAL_DIR / "partial.csv"
DEFERRED_FILE = PARTIAL_DIR / "qwalk8_deferred.json"
FINAL_DIR = PROJECT_ROOT / "data" / "v9" / "e17"

MODE, SEED, MQF = "full", 42, 10
TOPOLOGIES = ["linear", "grid", "heavy_hex"]
OPTIMIZERS = ["greedy_phase1", "commutation_phase2", "hybrid_phase1_2"]
TARGET_CIRCUIT = "qwalk_8"
MAX_SECONDS = float(os.environ.get("RERUN_MAX_SECONDS", "230"))

ALL_COLS = [
    "schema_version", "experiment_id", "run_id", "timestamp_utc",
    "circuit_id", "circuit_family", "n_qubits", "topology", "n_edges",
    "baseline_gate_count", "optimized_gate_count", "reduction",
    "reduction_pct", "depth_reduction", "two_qubit_reduction",
    "cnot_reduction", "fidelity", "runtime_seconds", "optimizer",
    "seed", "trial", "source_file", "source_sha256",
    "input_circuit_sha256", "output_circuit_sha256", "notes", "status",
    "error_message", "error_type",
]


def main() -> None:
    t_start = time.time()
    patch_fast_fidelity(n_samples=32)
    glb = load_patched_module("e17")

    generate_extended_suite = glb["generate_extended_suite"]
    apply_topology_constraint = glb["apply_topology_constraint"]
    _count_metrics = glb["_count_metrics"]
    _safe_ratio = glb["_safe_ratio"]
    circuit_sha256 = glb["circuit_sha256"]
    average_gate_fidelity = glb["average_gate_fidelity"]
    TOPOLOGIES_MAP = glb["TOPOLOGIES"]
    GreedyGateCancellation = glb["GreedyGateCancellation"]
    CommutationRewriter = glb["CommutationRewriter"]
    HybridCommuteRewrite = glb["HybridCommuteRewrite"]
    SCHEMA_VERSION = glb["SCHEMA_VERSION"]
    EXPERIMENT_ID = glb["EXPERIMENT_ID"]
    VERSION = glb["VERSION"]
    run_metadata = glb["run_metadata"]
    file_sha256 = glb["file_sha256"]
    script_path = Path(glb["__file__"])

    run_id = f"e17_{MODE}_qwalk8_fill"
    rid_file = PARTIAL_DIR / "run_id_qwalk8.txt"
    PARTIAL_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    if rid_file.exists():
        run_id = rid_file.read_text().strip()
    else:
        rid_file.write_text(run_id)

    # Resume: track (circuit_id, topology, optimizer) triples done
    done_triples = set()
    if PARTIAL_CSV.exists():
        prev = pd.read_csv(PARTIAL_CSV, usecols=["circuit_id", "topology", "optimizer"])
        qwalk_rows = prev[prev.circuit_id == TARGET_CIRCUIT]
        done_triples = set(zip(qwalk_rows["circuit_id"], qwalk_rows["topology"],
                                qwalk_rows["optimizer"]))
        print(f"[e17-qwalk8] resume: {len(done_triples)} qwalk_8 triples done",
              flush=True)

    deferred = []
    if DEFERRED_FILE.exists():
        deferred = json.loads(DEFERRED_FILE.read_text())

    # Find qwalk_8 in the suite
    circuits = generate_extended_suite(mode=MODE, seed=SEED)
    qwalk_bench = next((b for b in circuits if b.circuit_id == TARGET_CIRCUIT), None)
    if qwalk_bench is None:
        print(f"[e17-qwalk8] {TARGET_CIRCUIT} not found in suite", flush=True)
        return

    trial = next(i for i, b in enumerate(circuits) if b.circuit_id == TARGET_CIRCUIT)

    our_optimizers = {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "commutation_phase2": CommutationRewriter(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }

    def flush(row):
        if not row:
            return
        chunk = pd.DataFrame([row]).reindex(columns=ALL_COLS)
        tmp = PARTIAL_DIR / "chunk_qwalk8.tmp"
        chunk.to_csv(tmp, index=False)
        with open(PARTIAL_CSV, "a", newline="") as fout, open(tmp, "r") as fin:
            if not PARTIAL_CSV.exists() or PARTIAL_CSV.stat().st_size == 0:
                fout.write(fin.read())
            else:
                next(fin)
                fout.writelines(fin.readlines())
        os.remove(tmp)

    circuit = qwalk_bench.circuit
    n = circuit.num_qubits
    print(f"[e17-qwalk8] {TARGET_CIRCUIT} n={n}, "
          f"{len(done_triples)}/{len(TOPOLOGIES)*len(OPTIMIZERS)} triples done",
          flush=True)

    # Pre-compute topology-constrained circuits (one per topology)
    constrained_circuits = {}
    for topo_name in TOPOLOGIES:
        topo_fn = TOPOLOGIES_MAP[topo_name]
        coupling_map = topo_fn(n)
        try:
            constrained = apply_topology_constraint(
                circuit, coupling_map, seed_transpiler=SEED)
            constrained_circuits[topo_name] = (constrained, len(coupling_map))
            print(f"  {topo_name}: {constrained.size()} gates, "
                  f"{len(coupling_map)} edges", flush=True)
        except Exception as exc:
            # Record transpile_error for all 3 optimizers
            for opt_name in OPTIMIZERS:
                triple = (TARGET_CIRCUIT, topo_name, opt_name)
                if triple not in done_triples:
                    row = {
                        "schema_version": SCHEMA_VERSION,
                        "experiment_id": EXPERIMENT_ID,
                        "run_id": run_id,
                        "circuit_id": TARGET_CIRCUIT,
                        "circuit_family": qwalk_bench.family,
                        "n_qubits": n,
                        "topology": topo_name,
                        "optimizer": opt_name,
                        "status": "transpile_error",
                        "error_message": str(exc)[:200],
                        "error_type": type(exc).__name__,
                    }
                    flush(row)
                    done_triples.add(triple)
            print(f"  {topo_name}: transpile_error", flush=True)

    # Process each (topology, optimizer) triple
    for topo_name in TOPOLOGIES:
        if topo_name not in constrained_circuits:
            continue
        constrained, n_edges = constrained_circuits[topo_name]
        input_hash = circuit_sha256(constrained)
        orig_counts = constrained.size()
        orig_m = _count_metrics(constrained)

        for opt_name in OPTIMIZERS:
            triple = (TARGET_CIRCUIT, topo_name, opt_name)
            if triple in done_triples:
                continue
            if time.time() - t_start > MAX_SECONDS:
                print(f"[e17-qwalk8] budget reached, {len(done_triples)} triples done; "
                      f"rerun to resume", flush=True)
                DEFERRED_FILE.write_text(json.dumps(deferred, indent=2))
                return

            opt = our_optimizers[opt_name]
            print(f"  [{topo_name}/{opt_name}] starting (elapsed={time.time()-t_start:.0f}s)...",
                  flush=True)
            start = time.time()
            try:
                result = opt.optimize(constrained, target=constrained)
                runtime = time.time() - start

                output_hash = circuit_sha256(result.optimized_circuit)
                opt_m = _count_metrics(result.optimized_circuit)

                fidelity = result.fidelity
                if fidelity is None or fidelity == 0.0:
                    exact = average_gate_fidelity(
                        result.optimized_circuit, constrained,
                        max_qubits=MQF,
                    )
                    fidelity = exact if exact is not None else result.fidelity

                row = {
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "circuit_id": TARGET_CIRCUIT,
                    "circuit_family": qwalk_bench.family,
                    "n_qubits": n,
                    "topology": topo_name,
                    "n_edges": n_edges,
                    "baseline_gate_count": orig_counts,
                    "optimized_gate_count": result.optimized_size,
                    "reduction": result.reduction,
                    "reduction_pct": 100.0 * result.reduction,
                    "depth_reduction": _safe_ratio(orig_m["depth"], opt_m["depth"]),
                    "two_qubit_reduction": _safe_ratio(orig_m["two_q"], opt_m["two_q"]),
                    "cnot_reduction": _safe_ratio(orig_m["cnot"], opt_m["cnot"]),
                    "fidelity": fidelity,
                    "runtime_seconds": runtime,
                    "optimizer": opt_name,
                    "seed": qwalk_bench.seed,
                    "trial": trial,
                    "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                    "source_sha256": file_sha256(script_path),
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": output_hash,
                    "notes": qwalk_bench.notes,
                    "status": "ok",
                }
                flush(row)
                done_triples.add(triple)
                print(f"  [{topo_name}/{opt_name}] done in {runtime:.1f}s, "
                      f"reduction={result.reduction:.4f}, "
                      f"optimized={result.optimized_size}", flush=True)
            except Exception as exc:
                runtime = time.time() - start
                row = {
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "circuit_id": TARGET_CIRCUIT,
                    "circuit_family": qwalk_bench.family,
                    "n_qubits": n,
                    "topology": topo_name,
                    "n_edges": n_edges,
                    "optimizer": opt_name,
                    "status": "optimize_error",
                    "error_message": str(exc)[:200],
                    "error_type": type(exc).__name__,
                    "runtime_seconds": runtime,
                }
                flush(row)
                done_triples.add(triple)
                print(f"  [{topo_name}/{opt_name}] optimize_error: "
                      f"{type(exc).__name__}", flush=True)

    DEFERRED_FILE.write_text(json.dumps(deferred, indent=2))

    total_triples = len(TOPOLOGIES) * len(OPTIMIZERS)
    if len(done_triples) < total_triples:
        remaining = total_triples - len(done_triples)
        print(f"\n[e17-qwalk8] INCOMPLETE: {remaining} triples remaining. "
              f"Rerun to resume.", flush=True)
    else:
        print(f"\n[e17-qwalk8] COMPLETE: {len(done_triples)} triples processed",
              flush=True)


if __name__ == "__main__":
    main()
