"""Checkpointed E17 full rerun -> data/v9/e17/.

Replicates experiments/e17_connectivity/run.py::run() row-for-row (same loop
structure, same row schema), but flushes rows to a partial CSV after every
circuit so a killed run can resume. Uses rerun_to_v9.load_patched_module so
the experiment's own functions (TOPOLOGIES, apply_topology_constraint,
_count_metrics, ...) are used unmodified, with output redirected to v9.

Resume: delete nothing; just run again. Completed circuit_ids are skipped.
On completion the partial rows are assembled into the final timestamped CSV
and metadata.json, mirroring run.py's outputs.

Usage:
  /d/Downloads/miniforge3/python analysis/rerun_e17_checkpointed.py
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
FINAL_DIR = PROJECT_ROOT / "data" / "v9" / "e17"

MODE, SEED, MQF = "full", 42, 10
TOPOLOGIES = ["linear", "grid", "heavy_hex"]
# Deferred: transpiled qwalk_8/9/10 reach 40k-100k+ basis gates; a faithful
# greedy/commutation pass on them cannot finish within the per-call budget.
# qwalk_8 is the only one present in canonical (n=9); the gap is reported.
SKIP_CIRCUITS = {"qwalk_8", "qwalk_9", "qwalk_10", "grover_10", "adder_10",
                 "cnot_chain_20",  # cnot_chain_20 grid/heavy_hex pairs exceeded per-call budget
                 "surface_code_20"}  # n=21 pairs exceeded per-call budget


def main() -> None:
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

    run_id = f"e17_{MODE}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    # Keep a stable run_id across resumes
    rid_file = PARTIAL_DIR / "run_id.txt"
    PARTIAL_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    if rid_file.exists():
        run_id = rid_file.read_text().strip()
    else:
        rid_file.write_text(run_id)

    done_pairs = set()
    if PARTIAL_CSV.exists():
        prev = pd.read_csv(PARTIAL_CSV, usecols=["circuit_id", "topology"])
        done_pairs = set(zip(prev["circuit_id"], prev["topology"]))
        print(f"[e17-ckpt] resume: {len(done_pairs)} (circuit, topology) pairs done",
              flush=True)

    circuits = generate_extended_suite(mode=MODE, seed=SEED)
    todo = [(b, t) for b in circuits for t in TOPOLOGIES
            if (b.circuit_id, t) not in done_pairs and b.circuit_id not in SKIP_CIRCUITS]
    n_skip = sum(len(TOPOLOGIES) for b in circuits if b.circuit_id in SKIP_CIRCUITS)
    print(f"[e17-ckpt] {len(circuits)} circuits x {len(TOPOLOGIES)} topologies, "
          f"{len(todo)} pairs to do ({n_skip} deferred: {sorted(SKIP_CIRCUITS)}), "
          f"run_id={run_id}", flush=True)

    our_optimizers = {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "commutation_phase2": CommutationRewriter(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }

    total_pairs = len(circuits) * len(TOPOLOGIES) - n_skip
    for bench, topo_name in todo:
        t_circ = time.time()
        circuit = bench.circuit
        n = circuit.num_qubits
        trial = next(i for i, b in enumerate(circuits) if b.circuit_id == bench.circuit_id)
        rows = []
        if True:
            topo_fn = TOPOLOGIES_MAP[topo_name]
            coupling_map = topo_fn(n)
            try:
                constrained_circuit = apply_topology_constraint(circuit, coupling_map, seed_transpiler=SEED)
            except Exception as exc:
                rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "circuit_id": bench.circuit_id,
                    "circuit_family": bench.family,
                    "n_qubits": n,
                    "topology": topo_name,
                    "optimizer": "none",
                    "status": "transpile_error",
                    "error_message": str(exc),
                    "error_type": type(exc).__name__,
                })
                transpile_failed = True
            else:
                transpile_failed = False

        if not transpile_failed:
            input_hash = circuit_sha256(constrained_circuit)
            orig_counts = constrained_circuit.size()
            orig_m = _count_metrics(constrained_circuit)

            for opt_name, opt in our_optimizers.items():
                start = time.time()
                result = opt.optimize(constrained_circuit, target=constrained_circuit)
                runtime = time.time() - start

                output_hash = circuit_sha256(result.optimized_circuit)
                opt_m = _count_metrics(result.optimized_circuit)

                fidelity = result.fidelity
                if fidelity is None or fidelity == 0.0:
                    exact = average_gate_fidelity(
                        result.optimized_circuit, constrained_circuit,
                        max_qubits=MQF,
                    )
                    fidelity = exact if exact is not None else result.fidelity

                rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "circuit_id": bench.circuit_id,
                    "circuit_family": bench.family,
                    "n_qubits": n,
                    "topology": topo_name,
                    "n_edges": len(coupling_map),
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
                    "seed": bench.seed,
                    "trial": trial,
                    "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                    "source_sha256": file_sha256(script_path),
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": output_hash,
                    "notes": bench.notes,
                    "status": "ok",
                })

        # atomic-ish append: write chunk to temp then append
        ALL_COLS = ["schema_version","experiment_id","run_id","timestamp_utc",
                    "circuit_id","circuit_family","n_qubits","topology","n_edges",
                    "baseline_gate_count","optimized_gate_count","reduction",
                    "reduction_pct","depth_reduction","two_qubit_reduction",
                    "cnot_reduction","fidelity","runtime_seconds","optimizer",
                    "seed","trial","source_file","source_sha256",
                    "input_circuit_sha256","output_circuit_sha256","notes","status",
                    "error_message","error_type"]
        chunk = pd.DataFrame(rows).reindex(columns=ALL_COLS)
        tmp = PARTIAL_DIR / "chunk.tmp"
        chunk.to_csv(tmp, index=False)
        with open(PARTIAL_CSV, "a", newline="") as fout, open(tmp, "r") as fin:
            if PARTIAL_CSV.stat().st_size == 0:
                fout.write(fin.read())
            else:
                next(fin)  # skip header
                fout.writelines(fin.readlines())
        os.remove(tmp)
        done_pairs.add((bench.circuit_id, topo_name))
        print(f"[e17-ckpt] {bench.circuit_id}/{topo_name} (n={n}) done in "
              f"{time.time()-t_circ:.1f}s ({len(done_pairs)}/{total_pairs})", flush=True)

    if len(done_pairs) < total_pairs:
        print(f"[e17-ckpt] PARTIAL: {len(done_pairs)}/{total_pairs} pairs done; "
              f"rerun to resume", flush=True)
        return

    # Assemble final CSV
    df = pd.read_csv(PARTIAL_CSV)
    csv_path = FINAL_DIR / f"e17_connectivity_{run_id}.csv"
    tmp_final = FINAL_DIR / "final.tmp"
    df.to_csv(tmp_final, index=False)
    os.replace(tmp_final, csv_path)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "description": "Hardware connectivity constraint experiment",
        "mode": MODE,
        "seed": SEED,
        "max_qubits_fidelity": MQF,
        "topologies": TOPOLOGIES,
        "canonical_data_file": csv_path.name,
        "n_input_circuits": len(circuits),
        "n_rows": len(df),
        "circuit_families": sorted({b.family for b in circuits}),
        "rerun_note": "checkpointed rerun via analysis/rerun_e17_checkpointed.py; "
                      "fast-fidelity runtime accommodation (exact<=10q, 32 samples, "
                      "equality+Clifford shortcuts, memoized)",
        "deferred_pairs": sorted(SKIP_CIRCUITS),
        "deferred_reason": "transpiled qwalk_8/9/10 exceed 40k basis gates; faithful "
                           "optimizer pass exceeds per-call compute budget",
    })
    with (FINAL_DIR / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"[e17-ckpt] COMPLETE: {len(df)} rows -> {csv_path}", flush=True)


if __name__ == "__main__":
    main()
