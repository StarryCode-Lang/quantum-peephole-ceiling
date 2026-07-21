"""Checkpointed E21 full rerun -> data/v9/e21/.

Replicates experiments/e21_ceiling_aware/run.py::run() row-for-row (same
family/size/trial loop, same trial_rng consumption order, same 26-column row
schema), but flushes rows to a partial CSV after every (family, n_qubits)
config so a killed run can resume. Uses rerun_to_v9.load_patched_module so
the experiment's own functions (FAMILIES, run_naive_pipeline,
fidelity_source, ...) are used unmodified, with output redirected to v9
(RUN_PY entry injected here; the shared rerun_to_v9.py is NOT modified).

Canonical parameters (data/v6/e21/metadata.json + wave-4 caveats):
  mode=full (n_trials=10), seed=42, window=10,
  max_exact_fidelity_qubits=6 (effective threshold of the canonical run,
  NOT the metadata-recorded module constant 12).

No fidelity patch: canonical semantics pass target=None for n>6 (optimizer
placeholder fidelity) and exact AGF only for n<=6 (<=64-dim, cheap).

Resume: delete nothing; just run again. Completed (family, n_qubits) configs
are skipped. On completion the partial rows are assembled into
ceiling_aware_comparison.csv + ceiling_aware_summary.csv + metadata.json
under data/v9/e21/, mirroring run.py's outputs.

Usage:
  /d/Downloads/miniforge3/python analysis/rerun_e21_checkpointed.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analysis import rerun_to_v9  # noqa: E402

rerun_to_v9.RUN_PY["e21"] = (
    "experiments/e21_ceiling_aware/run.py", "v6",
    {"mode": "full", "seed": 42, "window": 10, "max_exact_fidelity_qubits": 6},
)
from analysis.rerun_to_v9 import load_patched_module  # noqa: E402

PARTIAL_DIR = PROJECT_ROOT / "data" / "v9" / "e21_partial"
PARTIAL_CSV = PARTIAL_DIR / "partial.csv"
FINAL_DIR = PROJECT_ROOT / "data" / "v9" / "e21"

MODE, SEED, WINDOW, MAX_EXACT = "full", 42, 10, 6
N_TRIALS = 10  # mode="full" per canonical metadata

ALL_COLS = ["schema_version", "experiment_id", "run_id", "mode", "family",
            "n_qubits", "trial_seed", "trial_idx", "original_size",
            "original_depth", "original_cnot", "ceiling_proxy_value",
            "input_circuit_sha256", "strategy_name", "gate_reduction",
            "depth_reduction", "cnot_reduction", "fidelity",
            "fidelity_source", "optimized_size", "phase1_time_ms",
            "phase2_time_ms", "final_phase1_time_ms", "total_time_ms",
            "phase1_skipped", "phase2_skipped"]


def main() -> None:
    glb = load_patched_module("e21")
    FAMILIES = glb["FAMILIES"]
    QUBIT_SIZES = glb["QUBIT_SIZES"]
    HAAR_MAX_QUBITS = glb["HAAR_MAX_QUBITS"]
    run_naive_pipeline = glb["run_naive_pipeline"]
    fidelity_source = glb["fidelity_source"]
    generate_circuit_for_experiment = glb["generate_circuit_for_experiment"]
    CeilingAwareOptimizer = glb["CeilingAwareOptimizer"]
    circuit_sha256 = glb["circuit_sha256"]
    SCHEMA_VERSION = glb["SCHEMA_VERSION"]
    EXPERIMENT_ID = glb["EXPERIMENT_ID"]
    VERSION = glb["VERSION"]
    run_metadata = glb["run_metadata"]
    script_path = Path(glb["__file__"])

    run_id = f"e21_{MODE}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    rid_file = PARTIAL_DIR / "run_id.txt"
    PARTIAL_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    if rid_file.exists():
        run_id = rid_file.read_text().strip()
    else:
        rid_file.write_text(run_id)

    done_configs = set()
    if PARTIAL_CSV.exists():
        prev = pd.read_csv(PARTIAL_CSV, usecols=["family", "n_qubits"])
        done_configs = set(zip(prev["family"], prev["n_qubits"]))
        print(f"[e21-ckpt] resume: {len(done_configs)} configs done", flush=True)

    ceiling_opt = CeilingAwareOptimizer(max_iterations=100, window_size=WINDOW)
    trial_rng = np.random.RandomState(SEED)

    # Total configs mirrors run.py accounting (HaarRandom n>4 skipped upfront)
    skipped = 0
    processed = 0
    total_configs = len(FAMILIES) * len(QUBIT_SIZES) * N_TRIALS

    for family_name, factory, kwargs_builder in FAMILIES:
        for n_qubits in QUBIT_SIZES:
            if family_name == "HaarRandom" and n_qubits > HAAR_MAX_QUBITS:
                skipped += N_TRIALS
                continue

            # Consume trial seeds in the SAME order as run.py even for
            # configs already done (rng must stay in sync).
            trial_seeds = [int(trial_rng.randint(0, 2**31 - 1))
                           for _ in range(N_TRIALS)]

            if (family_name, n_qubits) in done_configs:
                processed += N_TRIALS
                continue

            t_conf = time.time()
            rows = []
            for trial_idx in range(N_TRIALS):
                trial_seed = trial_seeds[trial_idx]
                try:
                    circuit = generate_circuit_for_experiment(
                        family_name, factory, kwargs_builder,
                        n_qubits, trial_seed,
                    )
                except Exception as exc:
                    print(f"  SKIP {family_name} n={n_qubits} trial={trial_idx}: {exc}",
                          flush=True)
                    continue
                if circuit.size() == 0:
                    continue

                fidelity_target = circuit if n_qubits <= MAX_EXACT else None

                # -- Strategy 1: naive pipeline
                naive = run_naive_pipeline(circuit, window_size=WINDOW,
                                           target=fidelity_target)

                # -- Strategy 2: ceiling-aware pipeline
                detailed = ceiling_opt.optimize_detailed(circuit, target=fidelity_target)
                ca = detailed.to_dict()
                ca_opt = detailed.optimization_result

                def _count_ext(c):
                    d = int(c.depth() or 0)
                    cnot = sum(1 for inst in c.data
                               if inst.operation.name in ('cx', 'cnot'))
                    return d, cnot

                orig_d, orig_cnot = _count_ext(circuit)
                opt_d, opt_cnot = _count_ext(ca_opt.optimized_circuit)
                depth_red_ca = 1.0 - opt_d / orig_d if orig_d > 0 else 0.0
                cnot_red_ca = 1.0 - opt_cnot / orig_cnot if orig_cnot > 0 else 0.0

                base_record = {
                    'schema_version': SCHEMA_VERSION,
                    'experiment_id': EXPERIMENT_ID,
                    'run_id': run_id,
                    'mode': MODE,
                    'family': family_name,
                    'n_qubits': n_qubits,
                    'trial_seed': trial_seed,
                    'trial_idx': trial_idx,
                    'original_size': circuit.size(),
                    'original_depth': orig_d,
                    'original_cnot': orig_cnot,
                    'ceiling_proxy_value': detailed.ceiling_proxy_phase1,
                    'input_circuit_sha256': circuit_sha256(circuit),
                }

                naive_fidelity = naive['fidelity']
                ca_fidelity = ca['fidelity']

                rows.append({
                    **base_record,
                    'strategy_name': 'naive',
                    'gate_reduction': naive['gate_reduction'],
                    'depth_reduction': naive['depth_reduction'],
                    'cnot_reduction': naive['cnot_reduction'],
                    'fidelity': naive_fidelity,
                    'fidelity_source': fidelity_source(n_qubits, naive_fidelity, MAX_EXACT),
                    'optimized_size': naive['optimized_size'],
                    'phase1_time_ms': naive['phase1_time_ms'],
                    'phase2_time_ms': naive['phase2_time_ms'],
                    'final_phase1_time_ms': naive['final_phase1_time_ms'],
                    'total_time_ms': naive['total_time_ms'],
                    'phase1_skipped': False,
                    'phase2_skipped': False,
                })
                rows.append({
                    **base_record,
                    'strategy_name': 'ceiling_aware',
                    'gate_reduction': ca['gate_reduction'],
                    'depth_reduction': depth_red_ca,
                    'cnot_reduction': cnot_red_ca,
                    'fidelity': ca_fidelity,
                    'fidelity_source': fidelity_source(n_qubits, ca_fidelity, MAX_EXACT),
                    'optimized_size': ca['optimized_size'],
                    'phase1_time_ms': ca['phase1_time_ms'],
                    'phase2_time_ms': ca['phase2_time_ms'],
                    'final_phase1_time_ms': ca['final_phase1_time_ms'],
                    'total_time_ms': ca['total_time_ms'],
                    'phase1_skipped': ca['phase1_skipped'],
                    'phase2_skipped': ca['phase2_skipped'],
                })

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
            done_configs.add((family_name, n_qubits))
            processed += N_TRIALS
            print(f"[e21-ckpt] {family_name} n={n_qubits} done in "
                  f"{time.time()-t_conf:.1f}s ({len(done_configs)} configs, "
                  f"{len(rows)} rows)", flush=True)

    expected_configs = len(FAMILIES) * len(QUBIT_SIZES) - 3  # HaarRandom n>4 x3
    if len(done_configs) < expected_configs:
        print(f"[e21-ckpt] PARTIAL: {len(done_configs)}/{expected_configs} configs; "
              f"rerun to resume", flush=True)
        return

    # -- Assemble final outputs (mirror run.py) ----------------------------
    df = pd.read_csv(PARTIAL_CSV)

    summary_rows = []
    if not df.empty:
        for (fam, strat), group in df.groupby(['family', 'strategy_name']):
            summary_rows.append({
                'family': fam,
                'strategy_name': strat,
                'n_instances': len(group),
                'mean_gate_reduction': group['gate_reduction'].mean(),
                'std_gate_reduction': group['gate_reduction'].std(),
                'mean_depth_reduction': group['depth_reduction'].mean(),
                'std_depth_reduction': group['depth_reduction'].std(),
                'mean_cnot_reduction': group['cnot_reduction'].mean(),
                'mean_total_time_ms': group['total_time_ms'].mean(),
                'std_total_time_ms': group['total_time_ms'].std(),
                'median_total_time_ms': group['total_time_ms'].median(),
                'mean_phase1_time_ms': group['phase1_time_ms'].mean(),
                'mean_phase2_time_ms': group['phase2_time_ms'].mean(),
                'pct_phase1_skipped': group['phase1_skipped'].mean() * 100,
                'pct_phase2_skipped': group['phase2_skipped'].mean() * 100,
                'mean_ceiling_proxy': group['ceiling_proxy_value'].mean(),
                'mean_original_size': group['original_size'].mean(),
                'mean_optimized_size': group['optimized_size'].mean(),
            })
    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        pivot = summary_df.pivot_table(index='family', columns='strategy_name',
                                       values='mean_total_time_ms')
        if 'naive' in pivot.columns and 'ceiling_aware' in pivot.columns:
            pivot['speedup'] = pivot['naive'] / pivot['ceiling_aware'].replace(0, np.nan)
            summary_df = summary_df.merge(pivot[['speedup']].reset_index(),
                                          on='family', how='left')
        else:
            summary_df['speedup'] = np.nan

    csv_path = FINAL_DIR / "ceiling_aware_comparison.csv"
    tmp_final = FINAL_DIR / "final.tmp"
    df.to_csv(tmp_final, index=False)
    os.replace(tmp_final, csv_path)
    summary_path = FINAL_DIR / "ceiling_aware_summary.csv"
    tmp_sum = FINAL_DIR / "summary.tmp"
    summary_df.to_csv(tmp_sum, index=False)
    os.replace(tmp_sum, summary_path)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "description": ("Ceiling-aware optimizer vs naive pipeline comparison. "
                        "Demonstrates that structural ceiling knowledge saves "
                        "compilation time without losing gate-count reduction."),
        "mode": MODE,
        "seed": SEED,
        "window": WINDOW,
        "n_trials_per_config": N_TRIALS,
        "qubit_sizes": QUBIT_SIZES,
        "n_families": len(FAMILIES),
        "n_rows": len(df),
        "n_skipped": skipped,
        "n_processed": processed,
        "fidelity_field": "fidelity",
        "fidelity_sources": sorted(df['fidelity_source'].dropna().unique().tolist()) if not df.empty else [],
        "max_exact_fidelity_qubits": MAX_EXACT,
        "comparison_file": csv_path.name,
        "summary_file": summary_path.name,
        "canonical_data_file": csv_path.name,
        "rerun_note": "checkpointed rerun via analysis/rerun_e21_checkpointed.py; "
                      "no fidelity patch (canonical semantics: target=None for n>6, "
                      "exact AGF for n<=6)",
    })
    with (FINAL_DIR / "metadata.json").open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2, sort_keys=True)

    print(f"[e21-ckpt] COMPLETE: {len(df)} rows -> {csv_path}", flush=True)


if __name__ == "__main__":
    main()
