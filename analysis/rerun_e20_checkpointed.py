"""Checkpointed E20 rerun -> data/v9/e20/.

Replicates experiments/e20_multi_compiler_full/run.py::run(mode='full',
seed=42, max_qubits_fidelity=10, skip_custom=True,
per_circuit_timeout=60.0) row-for-row, flushing rows after every
(circuit, compiler) block so a killed run can resume.

The canonical E20 covers 43 circuits (filtered to n in {4,6,8}) x 10
trials x 3 compilers (qiskit, cirq, tket) = ~1290 expected rows
(canonical: 1070 with ~220 error/timeout rows). Generators are unchanged
since the canonical run, so rerun hashes should match exactly.

Budget: stops gracefully after RERUN_MAX_SECONDS (default 215); rerun
resumes by skipping done (circuit_id, trial, compiler) blocks.

Usage:
  /d/Downloads/miniforge3/python analysis/rerun_e20_checkpointed.py
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

PARTIAL_DIR = PROJECT_ROOT / "data" / "v9" / "e20_partial"
PARTIAL_CSV = PARTIAL_DIR / "partial.csv"
DEFERRED_FILE = PARTIAL_DIR / "deferred.json"
FINAL_DIR = PROJECT_ROOT / "data" / "v9" / "e20"

MODE, SEED, MQF = "full", 42, 10
SKIP_CUSTOM = True
PER_CIRCUIT_TIMEOUT = 60.0
N_TRIALS = 10
MAX_SECONDS = float(os.environ.get("RERUN_MAX_SECONDS", "215"))

# Schema columns from run.py _build_row
ALL_COLS = [
    "schema_version", "experiment_id", "run_id", "timestamp_utc",
    "circuit_id", "circuit_family", "n_qubits",
    "original_gate_count", "optimized_gate_count",
    "gate_reduction", "gate_reduction_pct",
    "original_depth", "optimized_depth", "depth_reduction",
    "original_2q_gates", "optimized_2q_gates", "two_qubit_reduction",
    "original_cnot", "optimized_cnot", "cnot_reduction",
    "original_t_count", "optimized_t_count", "t_count_reduction",
    "fidelity", "compilation_time_seconds",
    "compiler_name", "compiler_backend", "compiler_version",
    "optimization_level", "compiler_status",
    "seed", "trial", "source_file", "source_sha256",
    "input_circuit_sha256", "output_circuit_sha256", "notes",
]


def main() -> None:
    t_start = time.time()
    patch_fast_fidelity(n_samples=32)
    glb = load_patched_module("e20")

    # Load all E20 globals we need
    _generate_filtered_suite = glb["_generate_filtered_suite"]
    _check_compilers = glb["_check_compilers"]
    _count_metrics = glb["_count_metrics"]
    _safe_ratio = glb["_safe_ratio"]
    _qiskit_transpile = glb["_qiskit_transpile"]
    _cirq_optimize = glb["_cirq_optimize"]
    _tket_optimize = glb["_tket_optimize"]
    _safe_fidelity = glb["_safe_fidelity"]
    _run_with_timeout = glb["_run_with_timeout"]
    _build_row = glb["_build_row"]
    circuit_sha256 = glb["circuit_sha256"]
    run_metadata = glb["run_metadata"]
    file_sha256 = glb["file_sha256"]
    SCHEMA_VERSION = glb["SCHEMA_VERSION"]
    EXPERIMENT_ID = glb["EXPERIMENT_ID"]
    VERSION = glb["VERSION"]
    script_path = Path(glb["__file__"])

    run_id = f"e20_{MODE}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    rid_file = PARTIAL_DIR / "run_id.txt"
    PARTIAL_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    if rid_file.exists():
        run_id = rid_file.read_text().strip()
    else:
        rid_file.write_text(run_id)

    # Resume from partial CSV: track (circuit_id, trial, compiler_name) blocks done
    done_blocks = set()
    if PARTIAL_CSV.exists():
        prev = pd.read_csv(
            PARTIAL_CSV,
            usecols=["circuit_id", "trial", "compiler_name"],
        )
        done_blocks = set(zip(prev["circuit_id"], prev["trial"].astype(int),
                              prev["compiler_name"]))
        print(f"[e20-ckpt] resume: {len(done_blocks)} blocks done", flush=True)

    deferred = []
    if DEFERRED_FILE.exists():
        deferred = json.loads(DEFERRED_FILE.read_text())
        print(f"[e20-ckpt] {len(deferred)} deferred entries", flush=True)

    compiler_avail, compiler_versions = _check_compilers()
    run_cirq = compiler_avail["cirq"]
    run_tket = compiler_avail["tket"]

    print(f"[e20-ckpt] compilers active: qiskit"
          + (", cirq" if run_cirq else "")
          + (", tket" if run_tket else "")
          + f" (timeout={PER_CIRCUIT_TIMEOUT}s, trials={N_TRIALS})", flush=True)

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

    total_rows_written = 0
    total_circuits = 0

    for trial_idx in range(N_TRIALS):
        if time.time() - t_start > MAX_SECONDS:
            print(f"[e20-ckpt] budget reached after trial {trial_idx}; "
                  f"rerun to resume", flush=True)
            break

        trial_seed = SEED + trial_idx
        suite = _generate_filtered_suite(mode=MODE, seed=trial_seed)
        total_circuits += len(suite)
        print(f"[e20-ckpt] trial {trial_idx}/{N_TRIALS}: {len(suite)} circuits, "
              f"elapsed={time.time()-t_start:.0f}s", flush=True)

        for bench_idx, bench in enumerate(suite):
            if time.time() - t_start > MAX_SECONDS:
                print(f"[e20-ckpt] budget reached mid-trial {trial_idx}, "
                      f"circuit {bench_idx}/{len(suite)}; rerun to resume",
                      flush=True)
                break

            circuit = bench.circuit
            n_qubits = circuit.num_qubits
            input_hash = circuit_sha256(circuit)
            orig_size = circuit.size()
            orig_m = _count_metrics(circuit)

            rows = []
            # ---- Qiskit (optimization_level=3) ----
            qiskit_block = (bench.circuit_id, trial_idx, "qiskit")
            if qiskit_block not in done_blocks:
                try:
                    opt_circ, runtime, status = _run_with_timeout(
                        _qiskit_transpile, circuit,
                        opt_level=3, seed_transpiler=trial_seed,
                        timeout=PER_CIRCUIT_TIMEOUT,
                    )
                except Exception as exc:
                    opt_circ, runtime, status = None, 0.0, f"error: {exc}"

                if opt_circ is not None and status == "ok":
                    opt_m = _count_metrics(opt_circ)
                    output_hash = circuit_sha256(opt_circ)
                    fidelity = _safe_fidelity(opt_circ, circuit, MQF)
                    rows.append(_build_row(
                        schema_version=SCHEMA_VERSION,
                        experiment_id=EXPERIMENT_ID, run_id=run_id,
                        bench=bench, n_qubits=n_qubits,
                        original_size=orig_size,
                        optimized_size=opt_circ.size(),
                        orig_m=orig_m, opt_m=opt_m,
                        fidelity=fidelity, runtime=runtime,
                        compiler="qiskit", compiler_backend="transpiler",
                        compiler_version=compiler_versions.get("qiskit"),
                        compiler_opt_level=3, compiler_status="ok",
                        trial=trial_idx, seed=trial_seed,
                        script_path=script_path,
                        input_hash=input_hash, output_hash=output_hash,
                    ))
                else:
                    rows.append(_build_row(
                        schema_version=SCHEMA_VERSION,
                        experiment_id=EXPERIMENT_ID, run_id=run_id,
                        bench=bench, n_qubits=n_qubits,
                        original_size=orig_size, optimized_size=None,
                        orig_m=orig_m, opt_m=None,
                        fidelity=None, runtime=runtime,
                        compiler="qiskit", compiler_backend="transpiler",
                        compiler_version=compiler_versions.get("qiskit"),
                        compiler_opt_level=3, compiler_status=status or "FAIL",
                        trial=trial_idx, seed=trial_seed,
                        script_path=script_path,
                        input_hash=input_hash, output_hash="none",
                    ))
                done_blocks.add(qiskit_block)

            # ---- Cirq (only for n_qubits <= 8 per canonical) ----
            cirq_block = (bench.circuit_id, trial_idx, "cirq")
            if cirq_block not in done_blocks and run_cirq and n_qubits <= 8:
                try:
                    opt_circ, runtime, status = _run_with_timeout(
                        _cirq_optimize, circuit,
                        timeout=PER_CIRCUIT_TIMEOUT,
                    )
                except Exception as exc:
                    opt_circ, runtime, status = None, 0.0, f"error: {exc}"

                if opt_circ is not None and status == "ok":
                    opt_m = _count_metrics(opt_circ)
                    output_hash = circuit_sha256(opt_circ)
                    fidelity = _safe_fidelity(opt_circ, circuit, MQF)
                    rows.append(_build_row(
                        schema_version=SCHEMA_VERSION,
                        experiment_id=EXPERIMENT_ID, run_id=run_id,
                        bench=bench, n_qubits=n_qubits,
                        original_size=orig_size,
                        optimized_size=opt_circ.size(),
                        orig_m=orig_m, opt_m=opt_m,
                        fidelity=fidelity, runtime=runtime,
                        compiler="cirq",
                        compiler_backend="optimize_for_target_gateset+eject_z+merge_1q",
                        compiler_version=compiler_versions.get("cirq"),
                        compiler_opt_level="default", compiler_status="ok",
                        trial=trial_idx, seed=trial_seed,
                        script_path=script_path,
                        input_hash=input_hash, output_hash=output_hash,
                    ))
                else:
                    rows.append(_build_row(
                        schema_version=SCHEMA_VERSION,
                        experiment_id=EXPERIMENT_ID, run_id=run_id,
                        bench=bench, n_qubits=n_qubits,
                        original_size=orig_size, optimized_size=None,
                        orig_m=orig_m, opt_m=None,
                        fidelity=None, runtime=runtime,
                        compiler="cirq",
                        compiler_backend="optimize_for_target_gateset+eject_z+merge_1q",
                        compiler_version=compiler_versions.get("cirq"),
                        compiler_opt_level="default",
                        compiler_status=status or "FAIL",
                        trial=trial_idx, seed=trial_seed,
                        script_path=script_path,
                        input_hash=input_hash, output_hash="none",
                    ))
                done_blocks.add(cirq_block)
            elif (cirq_block not in done_blocks and not run_cirq
                  and n_qubits <= 8):
                # Cirq unavailable - record availability error
                rows.append(_build_row(
                    schema_version=SCHEMA_VERSION,
                    experiment_id=EXPERIMENT_ID, run_id=run_id,
                    bench=bench, n_qubits=n_qubits,
                    original_size=orig_size, optimized_size=None,
                    orig_m=orig_m, opt_m=None,
                    fidelity=None, runtime=0.0,
                    compiler="cirq",
                    compiler_backend="optimize_for_target_gateset+eject_z+merge_1q",
                    compiler_version=compiler_versions.get("cirq"),
                    compiler_opt_level="default",
                    compiler_status="error: cirq unavailable",
                    trial=trial_idx, seed=trial_seed,
                    script_path=script_path,
                    input_hash=input_hash, output_hash="none",
                ))
                done_blocks.add(cirq_block)

            # ---- t|ket> ----
            # FullPeepholeOptimise is run only on small instances (<=6 qubits),
            # matching canonical E20 behavior. On larger circuits it can become
            # non-interruptible and hang the run.
            tket_block = (bench.circuit_id, trial_idx, "tket")
            if tket_block not in done_blocks and run_tket and n_qubits <= 6:
                try:
                    opt_circ, runtime, status = _run_with_timeout(
                        _tket_optimize, circuit,
                        timeout=PER_CIRCUIT_TIMEOUT,
                    )
                except Exception as exc:
                    opt_circ, runtime, status = None, 0.0, f"error: {exc}"

                if opt_circ is not None and status == "ok":
                    opt_m = _count_metrics(opt_circ)
                    output_hash = circuit_sha256(opt_circ)
                    fidelity = _safe_fidelity(opt_circ, circuit, MQF)
                    rows.append(_build_row(
                        schema_version=SCHEMA_VERSION,
                        experiment_id=EXPERIMENT_ID, run_id=run_id,
                        bench=bench, n_qubits=n_qubits,
                        original_size=orig_size,
                        optimized_size=opt_circ.size(),
                        orig_m=orig_m, opt_m=opt_m,
                        fidelity=fidelity, runtime=runtime,
                        compiler="tket",
                        compiler_backend="FullPeepholeOptimise",
                        compiler_version=compiler_versions.get("tket"),
                        compiler_opt_level="default", compiler_status="ok",
                        trial=trial_idx, seed=trial_seed,
                        script_path=script_path,
                        input_hash=input_hash, output_hash=output_hash,
                    ))
                else:
                    rows.append(_build_row(
                        schema_version=SCHEMA_VERSION,
                        experiment_id=EXPERIMENT_ID, run_id=run_id,
                        bench=bench, n_qubits=n_qubits,
                        original_size=orig_size, optimized_size=None,
                        orig_m=orig_m, opt_m=None,
                        fidelity=None, runtime=runtime,
                        compiler="tket",
                        compiler_backend="FullPeepholeOptimise",
                        compiler_version=compiler_versions.get("tket"),
                        compiler_opt_level="default",
                        compiler_status=status or "FAIL",
                        trial=trial_idx, seed=trial_seed,
                        script_path=script_path,
                        input_hash=input_hash, output_hash="none",
                    ))
                done_blocks.add(tket_block)
            elif tket_block not in done_blocks and not run_tket:
                rows.append(_build_row(
                    schema_version=SCHEMA_VERSION,
                    experiment_id=EXPERIMENT_ID, run_id=run_id,
                    bench=bench, n_qubits=n_qubits,
                    original_size=orig_size, optimized_size=None,
                    orig_m=orig_m, opt_m=None,
                    fidelity=None, runtime=0.0,
                    compiler="tket",
                    compiler_backend="FullPeepholeOptimise",
                    compiler_version=compiler_versions.get("tket"),
                    compiler_opt_level="default",
                    compiler_status="error: tket unavailable",
                    trial=trial_idx, seed=trial_seed,
                    script_path=script_path,
                    input_hash=input_hash, output_hash="none",
                ))
                done_blocks.add(tket_block)

            flush(rows)
            total_rows_written += len(rows)
            if rows:
                summary = " ".join(
                    f"[{r['compiler_name']}:{r['compiler_status'][:6]}]"
                    for r in rows)
                print(f"  trial={trial_idx} id={bench.circuit_id} "
                      f"n={n_qubits} gates={orig_size} {summary} "
                      f"({len(done_blocks)} done, "
                      f"elapsed={time.time()-t_start:.0f}s)", flush=True)

        # Save deferred state after each trial
        DEFERRED_FILE.write_text(json.dumps(deferred, indent=2))

    # Save deferred state
    DEFERRED_FILE.write_text(json.dumps(deferred, indent=2))

    # Check if complete: all trials processed AND no budget-stop mid-trial
    all_trials_done = True
    blocks_expected = 0
    for trial_idx in range(N_TRIALS):
        trial_seed = SEED + trial_idx
        suite = _generate_filtered_suite(mode=MODE, seed=trial_seed)
        for bench in suite:
            n_qubits = bench.circuit.num_qubits
            blocks_expected += 1  # qiskit
            if n_qubits <= 8:
                blocks_expected += 1  # cirq
            blocks_expected += 1  # tket

    complete = len(done_blocks) >= blocks_expected
    if not complete:
        remaining = blocks_expected - len(done_blocks)
        print(f"\n[e20-ckpt] INCOMPLETE: {remaining} blocks remaining. "
              f"Rerun to resume.", flush=True)
        return

    print(f"\n[e20-ckpt] COMPLETE: {len(done_blocks)} blocks processed",
          flush=True)

    # Finalize: merge partial into final CSV
    if PARTIAL_CSV.exists():
        df = pd.read_csv(PARTIAL_CSV)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_csv = FINAL_DIR / "multi_compiler_full.csv"
        if final_csv.exists():
            final_csv.rename(FINAL_DIR / f"multi_compiler_full.csv.bak-{ts}")
        tmp = FINAL_DIR / "multi_compiler_full.csv.tmp"
        df.to_csv(tmp, index=False)
        tmp.rename(final_csv)

        # Metadata
        meta = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
        meta.update({
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "description": (
                "Full multi-compiler comparison (Qiskit opt_level=3, "
                "Cirq optimize_for_target_gateset+eject_z+merge_1q, "
                "t|ket> FullPeepholeOptimise) - rerun for reconciliation"),
            "mode": MODE, "seed": SEED, "n_trials": N_TRIALS,
            "max_qubits_fidelity": MQF,
            "per_circuit_timeout_seconds": PER_CIRCUIT_TIMEOUT,
            "compilers_available": {k: v for k, v in compiler_avail.items()},
            "compiler_versions": {k: v for k, v in compiler_versions.items()},
            "skip_custom": SKIP_CUSTOM,
            "canonical_data_file": final_csv.name,
            "n_circuits_per_trial": len(_generate_filtered_suite(mode=MODE, seed=SEED)),
            "n_total_circuit_runs": total_circuits,
            "n_rows": len(df),
            "rerun_notes": (
                "Reconciliation rerun. Generator code unchanged since canonical "
                "run; expected to match canonical input_circuit_sha256 on all rows."
            ),
        })
        mp = FINAL_DIR / "metadata.json"
        tmp3 = FINAL_DIR / "metadata.json.tmp"
        with open(tmp3, "w") as f:
            json.dump(meta, f, indent=2, sort_keys=True)
        tmp3.rename(mp)
        print(f"  Final: {len(df)} rows -> {final_csv}", flush=True)
        if "gate_reduction" in df.columns:
            ok_df = df[df["compiler_status"] == "ok"]
            if len(ok_df) > 0:
                summary = (
                    ok_df.groupby(["compiler_name", "compiler_backend"])
                    .agg({"gate_reduction": "mean",
                          "depth_reduction": "mean",
                          "two_qubit_reduction": "mean",
                          "compilation_time_seconds": "mean"})
                )
                print(summary.to_string())


if __name__ == "__main__":
    main()
