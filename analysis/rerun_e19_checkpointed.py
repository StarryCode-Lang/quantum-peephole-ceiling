"""Checkpointed E19 full rerun -> data/v9/e19/.

Replicates experiments/e19_wcl_listing/run.py::run() row-for-row (same loop
structure, same row schema, same trial_seed schedule), but flushes rows to a
partial CSV after every depth so a killed run can resume. Uses
rerun_to_v9.load_patched_module so the experiment's own constants/functions
are used unmodified, with output redirected to v9 (RUN_PY entry injected
here, so the shared rerun_to_v9.py file is NOT modified).

Resume: delete nothing; just run again. Completed (depth, trial) pairs are
skipped. On completion the partial rows are assembled into the final
timestamped CSV and metadata.json, mirroring run.py's outputs.

Canonical parameters (data/v6/e19/metadata.json):
  seed=42, mode=full, n_qubits=5, depth 1..50, trials_per_depth=100,
  optimizer=both (LBL + WCL).

Usage:
  /d/Downloads/miniforge3/python analysis/rerun_e19_checkpointed.py
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

from analysis import rerun_to_v9  # noqa: E402

rerun_to_v9.RUN_PY["e19"] = (
    "experiments/e19_wcl_listing/run.py", "v6",
    {"seed": 42, "mode": "full"},
)
from analysis.rerun_to_v9 import load_patched_module  # noqa: E402

PARTIAL_DIR = PROJECT_ROOT / "data" / "v9" / "e19_partial"
PARTIAL_CSV = PARTIAL_DIR / "partial.csv"
FINAL_DIR = PROJECT_ROOT / "data" / "v9" / "e19"

SEED, MODE = 42, "full"
N_QUBITS, DEPTH_MIN, DEPTH_MAX, TRIALS_PER_DEPTH = 5, 1, 50, 100

ALL_COLS = ["schema_version", "experiment_id", "run_id", "timestamp_utc",
            "mode", "n_qubits", "depth", "trial", "seed", "optimizer",
            "listing_model", "wire_traversal", "original_size",
            "optimized_size", "reduction", "fidelity", "runtime_seconds",
            "success"]


def main() -> None:
    glb = load_patched_module("e19")
    generate_circuit = glb["generate_circuit"]
    CircuitFamily = glb["CircuitFamily"]
    GreedyGateCancellation = glb["GreedyGateCancellation"]
    SCHEMA_VERSION = glb["SCHEMA_VERSION"]
    EXPERIMENT_ID = glb["EXPERIMENT_ID"]
    VERSION = glb["VERSION"]
    run_metadata = glb["run_metadata"]
    script_path = Path(glb["__file__"])

    run_id = f"e19_{MODE}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    rid_file = PARTIAL_DIR / "run_id.txt"
    PARTIAL_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    if rid_file.exists():
        run_id = rid_file.read_text().strip()
    else:
        rid_file.write_text(run_id)

    done_pairs = set()
    if PARTIAL_CSV.exists():
        prev = pd.read_csv(PARTIAL_CSV, usecols=["depth", "trial"])
        done_pairs = set(zip(prev["depth"], prev["trial"]))
        print(f"[e19-ckpt] resume: {len(done_pairs)} (depth, trial) pairs done",
              flush=True)

    selected = [
        ("LBL", GreedyGateCancellation(success_reduction=0.01, wire_traversal=False), False),
        ("WCL", GreedyGateCancellation(success_reduction=0.01, wire_traversal=True), True),
    ]

    total_trials = (DEPTH_MAX - DEPTH_MIN + 1) * TRIALS_PER_DEPTH
    for depth in range(DEPTH_MIN, DEPTH_MAX + 1):
        todo_trials = [t for t in range(TRIALS_PER_DEPTH)
                       if (depth, t) not in done_pairs]
        if not todo_trials:
            continue
        t_depth = time.time()
        rows = []
        for trial in todo_trials:
            trial_seed = SEED * 1_000_000 + depth * 100 + trial
            circuit = generate_circuit(
                n_qubits=N_QUBITS,
                depth=depth,
                seed=trial_seed,
                family=CircuitFamily.UNIVERSAL,
            )
            original_size = circuit.size()
            if original_size == 0:
                done_pairs.add((depth, trial))
                continue
            for listing_model, opt, uses_wire_traversal in selected:
                t0 = time.time()
                result = opt.optimize(circuit, target=circuit)
                runtime = time.time() - t0
                rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "mode": MODE,
                    "n_qubits": N_QUBITS,
                    "depth": depth,
                    "trial": trial,
                    "seed": trial_seed,
                    "optimizer": "greedy_gate_cancellation",
                    "listing_model": listing_model,
                    "wire_traversal": uses_wire_traversal,
                    "original_size": original_size,
                    "optimized_size": result.optimized_size,
                    "reduction": result.reduction,
                    "fidelity": result.fidelity,
                    "runtime_seconds": runtime,
                    "success": bool(result.success),
                })
            done_pairs.add((depth, trial))

        # atomic-ish append: write chunk to temp then append
        if rows:
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
        print(f"[e19-ckpt] depth {depth} done in {time.time()-t_depth:.1f}s "
              f"({len(done_pairs)}/{total_trials} trials)", flush=True)

    if len(done_pairs) < total_trials:
        print(f"[e19-ckpt] PARTIAL: {len(done_pairs)}/{total_trials} trials done; "
              f"rerun to resume", flush=True)
        return

    # Assemble final CSV
    df = pd.read_csv(PARTIAL_CSV)
    csv_path = FINAL_DIR / f"e19_wcl_listing_{MODE}_{run_id}.csv"
    tmp_final = FINAL_DIR / "final.tmp"
    df.to_csv(tmp_final, index=False)
    os.replace(tmp_final, csv_path)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "description": "WCL vs LBL listing model comparison for Phase 1 ceiling",
        "mode": MODE,
        "seed": SEED,
        "n_qubits": N_QUBITS,
        "depth_range": [DEPTH_MIN, DEPTH_MAX],
        "trials_per_depth": TRIALS_PER_DEPTH,
        "optimizer_selection": "both",
        "optimizers_run": [item[0] for item in selected],
        "wire_traversal_by_listing_model": {item[0]: item[2] for item in selected},
        "total_circuits": total_trials,
        "canonical_data_file": csv_path.name,
        "n_rows": len(df),
        "rerun_note": "checkpointed rerun via analysis/rerun_e19_checkpointed.py; "
                      "no fidelity patch (n=5 exact path is cheap)",
    })
    with (FINAL_DIR / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"[e19-ckpt] COMPLETE: {len(df)} rows -> {csv_path}", flush=True)


if __name__ == "__main__":
    main()
