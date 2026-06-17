"""E20: Full multi-compiler comparison (Qiskit, Cirq, t|ket>).

Extends E15 by running all three major quantum compilers on the same 15
circuit families with controlled qubit counts {4, 6, 8} and 10 random
trials per (family, qubit_count) combination.  This experiment addresses
the reviewer concern that E15 only reported Qiskit results.

Compilers:
  1. Qiskit  -- transpile with optimization_level=3
  2. Cirq    -- optimize_for_target_gateset(CZTargetGateset) + eject_z
                + merge_single_qubit_gates_to_phased_x_and_z
  3. t|ket>  -- FullPeepholeOptimise (via pytket-qiskit conversion)

Missing compilers are detected at startup; the experiment still runs with
whatever is available and records availability in metadata.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import (  # noqa: E402
    average_gate_fidelity,
    circuit_sha256,
    gate_counts,
    generate_extended_suite,
)
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "2.0.0"
EXPERIMENT_ID = "E20"
VERSION = "1.0.0"

# Target qubit counts for the controlled comparison
TARGET_QUBITS = {4, 6, 8}

# Number of independent random trials per (family, qubit_count) cell
DEFAULT_N_TRIALS = 10


def _safe_ratio(original: int, optimized: int) -> float:
    """Safe reduction ratio: 1 - optimized/original, or 0.0 if original==0."""
    return 1.0 - optimized / original if original > 0 else 0.0


# ---------------------------------------------------------------------------
# Compiler availability detection
# ---------------------------------------------------------------------------

def _check_compilers() -> Dict[str, bool]:
    """Return a dict mapping compiler name -> is_available."""
    availability: Dict[str, bool] = {}

    # Qiskit is always required (base dependency)
    try:
        import qiskit  # noqa: F401
        availability["qiskit"] = True
    except ImportError:
        availability["qiskit"] = False

    # Cirq
    try:
        import cirq  # noqa: F401
        availability["cirq"] = True
    except ImportError:
        availability["cirq"] = False

    # t|ket>
    try:
        from pytket.extensions.qiskit import qiskit_to_tk  # noqa: F401
        from pytket.passes import FullPeepholeOptimise  # noqa: F401
        availability["tket"] = True
    except ImportError:
        availability["tket"] = False

    return availability


# ---------------------------------------------------------------------------
# Compiler backends
# ---------------------------------------------------------------------------

def _qiskit_transpile(circuit, opt_level: int = 3):
    """Run Qiskit transpiler at optimization_level=3."""
    from qiskit import transpile
    start = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        optimized = transpile(circuit, optimization_level=opt_level, seed_transpiler=42)
    runtime = time.time() - start
    return optimized, runtime


def _cirq_optimize(circuit):
    """Convert Qiskit circuit to Cirq, apply enhanced optimization, convert back.

    Optimization pipeline:
      1. drop_empty_moments / drop_negligible_operations
      2. optimize_for_target_gateset(CZTargetGateset) -- re-synthesize 2Q gates
      3. eject_z -- propagate Z rotations through the circuit
      4. merge_single_qubit_gates_to_phased_x_and_z -- collapse 1Q chains
      5. drop_empty_moments (cleanup)
    """
    try:
        import cirq
        from cirq.contrib.qasm_import import circuit_from_qasm
        from qiskit.qasm2 import dumps as qasm2_dumps
        from qiskit.qasm2 import loads as qasm2_loads
    except ImportError:
        return None, 0.0, "cirq_not_installed"

    try:
        # Qiskit -> OpenQASM2 -> Cirq
        qasm_str = qasm2_dumps(circuit)
        cirq_circ = circuit_from_qasm(qasm_str)

        start = time.time()

        from cirq.transformers import (
            drop_empty_moments,
            drop_negligible_operations,
            eject_z,
            merge_single_qubit_gates_to_phased_x_and_z,
            optimize_for_target_gateset,
        )

        # Phase 1: cleanup
        cirq_circ = drop_empty_moments(cirq_circ)
        cirq_circ = drop_negligible_operations(cirq_circ)

        # Phase 2: re-synthesize two-qubit gates for CZ target
        try:
            cirq_circ = optimize_for_target_gateset(
                cirq_circ, target_gateset=cirq.CZTargetGateset()
            )
        except Exception:
            # Fallback: some circuits may not be compatible with CZTargetGateset
            pass

        # Phase 3: Z-ejection (push Z rotations toward output)
        cirq_circ = eject_z(cirq_circ)

        # Phase 4: merge single-qubit gate chains
        cirq_circ = merge_single_qubit_gates_to_phased_x_and_z(cirq_circ)

        # Phase 5: final cleanup
        cirq_circ = drop_empty_moments(cirq_circ)

        runtime = time.time() - start

        # Cirq -> OpenQASM2 -> Qiskit
        qasm_out = cirq.qasm(cirq_circ)
        qc_back = qasm2_loads(qasm_out)
        return qc_back, runtime, "ok"
    except Exception as exc:
        return None, 0.0, str(exc)


def _tket_optimize(circuit):
    """Convert Qiskit circuit to t|ket>, apply FullPeepholeOptimise, convert back."""
    try:
        from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
        from pytket.passes import DecomposeBoxes, FullPeepholeOptimise
    except ImportError:
        return None, 0.0, "tket_not_installed"

    try:
        tk_circ = qiskit_to_tk(circuit)
        start = time.time()
        DecomposeBoxes().apply(tk_circ)
        FullPeepholeOptimise().apply(tk_circ)
        runtime = time.time() - start
        qc_back = tk_to_qiskit(tk_circ)
        return qc_back, runtime, "ok"
    except Exception as exc:
        return None, 0.0, str(exc)


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------

def _count_metrics(circuit) -> Dict[str, int]:
    """Count depth, 2Q gates, and CNOT gates for a Qiskit circuit."""
    depth = int(circuit.depth() or 0)
    two_q = sum(1 for inst in circuit.data if inst.operation.num_qubits == 2)
    cnot = sum(1 for inst in circuit.data if inst.operation.name in ("cx", "cnot"))
    return {"depth": depth, "two_q": two_q, "cnot": cnot}


def _extract_n_param(circuit_id: str) -> int:
    """Extract the trailing integer parameter from a circuit_id like 'qft_4'."""
    match = re.search(r"_(\d+)$", circuit_id)
    if match:
        return int(match.group(1))
    return -1


# ---------------------------------------------------------------------------
# Suite generation with filtering
# ---------------------------------------------------------------------------

def _generate_filtered_suite(mode: str, seed: int) -> list:
    """Generate the extended suite and filter to TARGET_QUBITS sizes."""
    suite = generate_extended_suite(mode=mode, seed=seed)
    return [b for b in suite if _extract_n_param(b.circuit_id) in TARGET_QUBITS]


# ---------------------------------------------------------------------------
# Row builder (shared by all compiler backends)
# ---------------------------------------------------------------------------

def _build_row(
    *,
    schema_version: str,
    experiment_id: str,
    run_id: str,
    bench,
    n_qubits: int,
    original_size: int,
    optimized_size: int,
    orig_m: Dict[str, int],
    opt_m: Optional[Dict[str, int]],
    fidelity: Optional[float],
    runtime: float,
    compiler: str,
    compiler_backend: str,
    compiler_opt_level,
    compiler_status: str,
    trial: int,
    seed: int,
    script_path: Path,
    input_hash: str,
    output_hash: str,
) -> dict:
    """Build a single result row with consistent schema."""
    size = original_size
    reduction = (1.0 - optimized_size / size) if size > 0 and optimized_size is not None else None
    return {
        "schema_version": schema_version,
        "experiment_id": experiment_id,
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "circuit_id": bench.circuit_id,
        "circuit_family": bench.family,
        "n_qubits": n_qubits,
        "original_gate_count": original_size,
        "optimized_gate_count": optimized_size,
        "gate_reduction": reduction,
        "gate_reduction_pct": 100.0 * reduction if reduction is not None else None,
        "original_depth": orig_m["depth"],
        "optimized_depth": opt_m["depth"] if opt_m else None,
        "depth_reduction": _safe_ratio(orig_m["depth"], opt_m["depth"]) if opt_m else None,
        "original_2q_gates": orig_m["two_q"],
        "optimized_2q_gates": opt_m["two_q"] if opt_m else None,
        "two_qubit_reduction": _safe_ratio(orig_m["two_q"], opt_m["two_q"]) if opt_m else None,
        "original_cnot": orig_m["cnot"],
        "optimized_cnot": opt_m["cnot"] if opt_m else None,
        "cnot_reduction": _safe_ratio(orig_m["cnot"], opt_m["cnot"]) if opt_m else None,
        "fidelity": fidelity,
        "compilation_time_seconds": runtime,
        "compiler_name": compiler,
        "compiler_backend": compiler_backend,
        "optimization_level": compiler_opt_level,
        "compiler_status": compiler_status,
        "seed": seed,
        "trial": trial,
        "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
        "source_sha256": file_sha256(script_path),
        "input_circuit_sha256": input_hash,
        "output_circuit_sha256": output_hash,
        "notes": bench.notes,
    }


# ---------------------------------------------------------------------------
# Main experiment runner
# ---------------------------------------------------------------------------

def run(
    mode: str = "full",
    seed: int = 42,
    n_trials: int = DEFAULT_N_TRIALS,
    max_qubits_fidelity: int = 10,
    skip_cirq: bool = False,
    skip_tket: bool = False,
) -> pd.DataFrame:
    """Run E20 multi-compiler full comparison and return the result table."""
    run_id = f"e20_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v6" / "e20"
    output_dir.mkdir(parents=True, exist_ok=True)

    # -- Check compiler availability --
    compiler_avail = _check_compilers()
    if not compiler_avail["qiskit"]:
        print("ERROR: Qiskit is not installed. Cannot run experiment.")
        sys.exit(1)

    run_cirq = compiler_avail["cirq"] and not skip_cirq
    run_tket = compiler_avail["tket"] and not skip_tket

    if not compiler_avail["cirq"]:
        print("WARNING: cirq-core is not installed -- skipping Cirq backend.")
    elif skip_cirq:
        print("INFO: Cirq backend skipped via --skip-cirq flag.")

    if not compiler_avail["tket"]:
        print("WARNING: pytket / pytket-qiskit is not installed -- skipping t|ket> backend.")
    elif skip_tket:
        print("INFO: t|ket> backend skipped via --skip-tket flag.")

    print(f"Compilers active: qiskit"
          + (", cirq" if run_cirq else "")
          + (", tket" if run_tket else ""))

    # -- Collect all rows --
    rows: List[dict] = []
    total_circuits = 0

    for trial_idx in range(n_trials):
        trial_seed = seed + trial_idx
        suite = _generate_filtered_suite(mode=mode, seed=trial_seed)
        total_circuits += len(suite)

        for bench_idx, bench in enumerate(suite):
            circuit = bench.circuit
            n_qubits = circuit.num_qubits
            input_hash = circuit_sha256(circuit)
            orig_size = circuit.size()
            orig_m = _count_metrics(circuit)

            progress = (trial_idx * len(suite) + bench_idx + 1)
            total_work = n_trials * len(suite)
            print(
                f"  [{progress}/{total_work}] trial={trial_idx} "
                f"family={bench.family} circuit_id={bench.circuit_id} "
                f"n_qubits={n_qubits} gates={orig_size}",
                end="",
            )

            # ---- Qiskit (optimization_level=3) ----
            try:
                opt_circ, runtime = _qiskit_transpile(circuit, opt_level=3)
                opt_m = _count_metrics(opt_circ)
                output_hash = circuit_sha256(opt_circ)
                fidelity = average_gate_fidelity(
                    opt_circ, circuit, max_qubits=max_qubits_fidelity
                )
                rows.append(_build_row(
                    schema_version=SCHEMA_VERSION,
                    experiment_id=EXPERIMENT_ID,
                    run_id=run_id,
                    bench=bench,
                    n_qubits=n_qubits,
                    original_size=orig_size,
                    optimized_size=opt_circ.size(),
                    orig_m=orig_m,
                    opt_m=opt_m,
                    fidelity=fidelity,
                    runtime=runtime,
                    compiler="qiskit",
                    compiler_backend="transpiler",
                    compiler_opt_level=3,
                    compiler_status="ok",
                    trial=trial_idx,
                    seed=trial_seed,
                    script_path=script_path,
                    input_hash=input_hash,
                    output_hash=output_hash,
                ))
                print(" [qiskit:ok]", end="")
            except Exception as exc:
                print(f" [qiskit:FAIL]", end="")
                rows.append(_build_row(
                    schema_version=SCHEMA_VERSION,
                    experiment_id=EXPERIMENT_ID,
                    run_id=run_id,
                    bench=bench,
                    n_qubits=n_qubits,
                    original_size=orig_size,
                    optimized_size=None,
                    orig_m=orig_m,
                    opt_m=None,
                    fidelity=None,
                    runtime=0.0,
                    compiler="qiskit",
                    compiler_backend="transpiler",
                    compiler_opt_level=3,
                    compiler_status=f"error: {exc}",
                    trial=trial_idx,
                    seed=trial_seed,
                    script_path=script_path,
                    input_hash=input_hash,
                    output_hash="none",
                ))
                traceback.print_exc()

            # ---- Cirq ----
            if run_cirq:
                try:
                    opt_circ, runtime, status = _cirq_optimize(circuit)
                    if opt_circ is not None:
                        opt_m = _count_metrics(opt_circ)
                        output_hash = circuit_sha256(opt_circ)
                        fidelity = average_gate_fidelity(
                            opt_circ, circuit, max_qubits=max_qubits_fidelity
                        )
                        rows.append(_build_row(
                            schema_version=SCHEMA_VERSION,
                            experiment_id=EXPERIMENT_ID,
                            run_id=run_id,
                            bench=bench,
                            n_qubits=n_qubits,
                            original_size=orig_size,
                            optimized_size=opt_circ.size(),
                            orig_m=orig_m,
                            opt_m=opt_m,
                            fidelity=fidelity,
                            runtime=runtime,
                            compiler="cirq",
                            compiler_backend="optimize_for_target_gateset+eject_z+merge_1q",
                            compiler_opt_level="default",
                            compiler_status=status,
                            trial=trial_idx,
                            seed=trial_seed,
                            script_path=script_path,
                            input_hash=input_hash,
                            output_hash=output_hash,
                        ))
                        print(" [cirq:ok]", end="")
                    else:
                        rows.append(_build_row(
                            schema_version=SCHEMA_VERSION,
                            experiment_id=EXPERIMENT_ID,
                            run_id=run_id,
                            bench=bench,
                            n_qubits=n_qubits,
                            original_size=orig_size,
                            optimized_size=None,
                            orig_m=orig_m,
                            opt_m=None,
                            fidelity=None,
                            runtime=0.0,
                            compiler="cirq",
                            compiler_backend="optimize_for_target_gateset+eject_z+merge_1q",
                            compiler_opt_level="default",
                            compiler_status=status,
                            trial=trial_idx,
                            seed=trial_seed,
                            script_path=script_path,
                            input_hash=input_hash,
                            output_hash="none",
                        ))
                        print(f" [cirq:skip({status[:30]})]", end="")
                except Exception as exc:
                    print(f" [cirq:FAIL]", end="")
                    rows.append(_build_row(
                        schema_version=SCHEMA_VERSION,
                        experiment_id=EXPERIMENT_ID,
                        run_id=run_id,
                        bench=bench,
                        n_qubits=n_qubits,
                        original_size=orig_size,
                        optimized_size=None,
                        orig_m=orig_m,
                        opt_m=None,
                        fidelity=None,
                        runtime=0.0,
                        compiler="cirq",
                        compiler_backend="optimize_for_target_gateset+eject_z+merge_1q",
                        compiler_opt_level="default",
                        compiler_status=f"error: {exc}",
                        trial=trial_idx,
                        seed=trial_seed,
                        script_path=script_path,
                        input_hash=input_hash,
                        output_hash="none",
                    ))
                    traceback.print_exc()

            # ---- t|ket> ----
            if run_tket:
                try:
                    opt_circ, runtime, status = _tket_optimize(circuit)
                    if opt_circ is not None:
                        opt_m = _count_metrics(opt_circ)
                        output_hash = circuit_sha256(opt_circ)
                        fidelity = average_gate_fidelity(
                            opt_circ, circuit, max_qubits=max_qubits_fidelity
                        )
                        rows.append(_build_row(
                            schema_version=SCHEMA_VERSION,
                            experiment_id=EXPERIMENT_ID,
                            run_id=run_id,
                            bench=bench,
                            n_qubits=n_qubits,
                            original_size=orig_size,
                            optimized_size=opt_circ.size(),
                            orig_m=orig_m,
                            opt_m=opt_m,
                            fidelity=fidelity,
                            runtime=runtime,
                            compiler="tket",
                            compiler_backend="FullPeepholeOptimise",
                            compiler_opt_level="default",
                            compiler_status=status,
                            trial=trial_idx,
                            seed=trial_seed,
                            script_path=script_path,
                            input_hash=input_hash,
                            output_hash=output_hash,
                        ))
                        print(" [tket:ok]", end="")
                    else:
                        rows.append(_build_row(
                            schema_version=SCHEMA_VERSION,
                            experiment_id=EXPERIMENT_ID,
                            run_id=run_id,
                            bench=bench,
                            n_qubits=n_qubits,
                            original_size=orig_size,
                            optimized_size=None,
                            orig_m=orig_m,
                            opt_m=None,
                            fidelity=None,
                            runtime=0.0,
                            compiler="tket",
                            compiler_backend="FullPeepholeOptimise",
                            compiler_opt_level="default",
                            compiler_status=status,
                            trial=trial_idx,
                            seed=trial_seed,
                            script_path=script_path,
                            input_hash=input_hash,
                            output_hash="none",
                        ))
                        print(f" [tket:skip({status[:30]})]", end="")
                except Exception as exc:
                    print(f" [tket:FAIL]", end="")
                    rows.append(_build_row(
                        schema_version=SCHEMA_VERSION,
                        experiment_id=EXPERIMENT_ID,
                        run_id=run_id,
                        bench=bench,
                        n_qubits=n_qubits,
                        original_size=orig_size,
                        optimized_size=None,
                        orig_m=orig_m,
                        opt_m=None,
                        fidelity=None,
                        runtime=0.0,
                        compiler="tket",
                        compiler_backend="FullPeepholeOptimise",
                        compiler_opt_level="default",
                        compiler_status=f"error: {exc}",
                        trial=trial_idx,
                        seed=trial_seed,
                        script_path=script_path,
                        input_hash=input_hash,
                        output_hash="none",
                    ))
                    traceback.print_exc()

            print()  # newline after each circuit

    # -- Build DataFrame and save --
    df = pd.DataFrame(rows)
    csv_path = output_dir / "multi_compiler_full.csv"
    df.to_csv(csv_path, index=False)

    # -- Metadata --
    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    compilers_run = ["qiskit"]
    if run_cirq:
        compilers_run.append("cirq")
    if run_tket:
        compilers_run.append("tket")

    # Collect unique circuit families from the first trial's suite
    sample_suite = _generate_filtered_suite(mode=mode, seed=seed)
    circuit_families = sorted({b.family for b in sample_suite})

    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "description": (
            "Full multi-compiler comparison (Qiskit opt_level=3, "
            "Cirq optimize_for_target_gateset+eject_z+merge_1q, "
            "t|ket> FullPeepholeOptimise) across 15 circuit families"
        ),
        "mode": mode,
        "seed": seed,
        "n_trials": n_trials,
        "target_qubits": sorted(TARGET_QUBITS),
        "max_qubits_fidelity": max_qubits_fidelity,
        "compilers_available": {k: v for k, v in compiler_avail.items()},
        "compilers_run": compilers_run,
        "skip_cirq": skip_cirq,
        "skip_tket": skip_tket,
        "canonical_data_file": csv_path.name,
        "n_circuits_per_trial": len(sample_suite),
        "n_total_circuit_runs": total_circuits,
        "n_rows": len(df),
        "circuit_families": circuit_families,
    })
    metadata_path = output_dir / "metadata.json"
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    # -- Summary --
    print(f"\nE20 complete: {len(df)} rows -> {csv_path}")
    print(f"Metadata    -> {metadata_path}")
    print(f"Compilers   : {', '.join(compilers_run)}")
    print(f"Trials      : {n_trials}  |  Target qubits: {sorted(TARGET_QUBITS)}")
    print(f"Families    : {len(circuit_families)}  ({', '.join(circuit_families)})")

    if len(df) > 0:
        ok_df = df[df["compiler_status"] == "ok"].copy()
        if len(ok_df) > 0:
            summary = (
                ok_df
                .groupby(["compiler_name", "compiler_backend"])
                .agg({
                    "gate_reduction": "mean",
                    "depth_reduction": "mean",
                    "two_qubit_reduction": "mean",
                    "compilation_time_seconds": "mean",
                })
            )
            print("\n--- Per-compiler summary (successful runs) ---")
            print(summary.to_string())
        else:
            print("\nWARNING: No successful compiler runs to summarize.")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run E20 full multi-compiler comparison (Qiskit, Cirq, t|ket>)"
    )
    parser.add_argument(
        "--mode", choices=["smoke", "full"], default="full",
        help="'smoke' for quick validation, 'full' for publication results (default: full)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Base random seed")
    parser.add_argument(
        "--n-trials", type=int, default=DEFAULT_N_TRIALS,
        help=f"Number of random trials per (family, qubit_count) cell (default: {DEFAULT_N_TRIALS})"
    )
    parser.add_argument(
        "--max-qubits-fidelity", type=int, default=10,
        help="Max qubits for exact unitary fidelity computation"
    )
    parser.add_argument("--skip-cirq", action="store_true", help="Skip Cirq backend")
    parser.add_argument("--skip-tket", action="store_true", help="Skip t|ket> backend")
    args = parser.parse_args()

    run(
        mode=args.mode,
        seed=args.seed,
        n_trials=args.n_trials,
        max_qubits_fidelity=args.max_qubits_fidelity,
        skip_cirq=args.skip_cirq,
        skip_tket=args.skip_tket,
    )


if __name__ == "__main__":
    main()
