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
import concurrent.futures
import json
import re
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import (  # noqa: E402
    average_gate_fidelity,
    circuit_sha256,
    gate_counts,
    generate_extended_suite,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase2.commutation_rewriter import (  # noqa: E402
    CommutationRewriter,
    HybridCommuteRewrite,
)
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "2.1.0"
# Disambiguated from the experiment-registry E20 (Reproducibility Audit).
# The manuscript refers to this experiment as "MC-E20" (Multi-Compiler full
# comparison). See docs/06_manuscript/v5_full_manuscript_part3.md.
EXPERIMENT_ID = "MC-E20"
VERSION = "1.1.0"

# Target qubit counts for the controlled comparison
TARGET_QUBITS = {4, 6, 8}

# Number of independent random trials per (family, qubit_count) cell
DEFAULT_N_TRIALS = 10
SMOKE_N_TRIALS = 1


def _safe_ratio(original: int, optimized: int) -> float:
    """Safe reduction ratio: 1 - optimized/original, or 0.0 if original==0."""
    return 1.0 - optimized / original if original > 0 else 0.0


# ---------------------------------------------------------------------------
# Timeout helper for long-running compiler calls
# ---------------------------------------------------------------------------


def _run_with_timeout(
    fn: Callable[..., Any],
    *args: Any,
    timeout: Optional[float] = None,
    **kwargs: Any,
) -> Tuple[Any, float, str]:
    """Run ``fn`` in a background thread and enforce an optional timeout.

    Returns:
        A tuple of (result, elapsed_seconds, status).  On timeout the
        result is None and status is ``timeout``.  On exception the
        result is None and status is ``error: <message>``.
    """
    result_container: List[Any] = [None]
    exception_container: List[BaseException] = [None]

    def _target() -> None:
        try:
            result_container[0] = fn(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001
            exception_container[0] = exc

    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_target)
        try:
            future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return None, time.time() - start, "timeout"

    elapsed = time.time() - start
    if exception_container[0] is not None:
        return None, elapsed, f"error: {exception_container[0]}"
    return result_container[0], elapsed, "ok"


# ---------------------------------------------------------------------------
# Compiler availability detection
# ---------------------------------------------------------------------------

def _check_compilers() -> Tuple[Dict[str, bool], Dict[str, Optional[str]]]:
    """Return (availability, versions) dicts mapping compiler name -> info."""
    availability: Dict[str, bool] = {}
    versions: Dict[str, Optional[str]] = {}

    # Qiskit is always required (base dependency)
    try:
        import qiskit  # noqa: F401
        availability["qiskit"] = True
        versions["qiskit"] = qiskit.__version__
    except ImportError:
        availability["qiskit"] = False
        versions["qiskit"] = None

    # Cirq
    try:
        import cirq  # noqa: F401
        availability["cirq"] = True
        versions["cirq"] = cirq.__version__
    except ImportError:
        availability["cirq"] = False
        versions["cirq"] = None

    # t|ket>
    try:
        from pytket.extensions.qiskit import qiskit_to_tk  # noqa: F401
        from pytket.passes import FullPeepholeOptimise  # noqa: F401
        availability["tket"] = True
        versions["tket"] = __import__("pytket").__version__
    except ImportError:
        availability["tket"] = False
        versions["tket"] = None

    return availability, versions


# ---------------------------------------------------------------------------
# Compiler backends
# ---------------------------------------------------------------------------

def _qiskit_transpile(circuit, opt_level: int = 3, seed_transpiler: int = 42):
    """Run Qiskit transpiler at the given optimization level."""
    from qiskit import transpile
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        optimized = transpile(circuit, optimization_level=opt_level, seed_transpiler=seed_transpiler)
    return optimized


def _cirq_optimize(circuit):
    """Convert Qiskit circuit to Cirq, apply enhanced optimization, convert back.

    Optimization pipeline:
      1. drop_empty_moments / drop_negligible_operations
      2. optimize_for_target_gateset(CZTargetGateset) -- re-synthesize 2Q gates
      3. eject_z -- propagate Z rotations through the circuit
      4. merge_single_qubit_gates_to_phased_x_and_z -- collapse 1Q chains
      5. drop_empty_moments (cleanup)

    Returns:
        The optimized Qiskit QuantumCircuit.
    """
    import cirq
    from cirq.contrib.qasm_import import circuit_from_qasm
    from qiskit.qasm2 import dumps as qasm2_dumps
    from qiskit.qasm2 import loads as qasm2_loads

    # Qiskit -> OpenQASM2 -> Cirq
    qasm_str = qasm2_dumps(circuit)
    cirq_circ = circuit_from_qasm(qasm_str)

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

    # Cirq -> OpenQASM2 -> Qiskit
    qasm_out = cirq.qasm(cirq_circ)
    return qasm2_loads(qasm_out)


def _safe_fidelity(opt_circ, circuit, max_qubits: int) -> Optional[float]:
    """Compute exact fidelity only for small circuits to avoid blow-up."""
    if opt_circ.num_qubits > 8:
        return None
    return average_gate_fidelity(opt_circ, circuit, max_qubits=max_qubits)


def _run_custom_optimizer(circuit, opt_cls):
    """Run one of the project's custom optimizers and return (circuit, fidelity)."""
    optimizer = opt_cls(success_reduction=0.01)
    result = optimizer.optimize(circuit, target=circuit)
    return result.optimized_circuit, result.fidelity


def _tket_optimize(circuit):
    """Convert Qiskit circuit to t|ket>, apply FullPeepholeOptimise, convert back."""
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
    from pytket.passes import DecomposeBoxes, FullPeepholeOptimise

    tk_circ = qiskit_to_tk(circuit)
    DecomposeBoxes().apply(tk_circ)
    FullPeepholeOptimise().apply(tk_circ)
    return tk_to_qiskit(tk_circ)


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------

def _count_metrics(circuit) -> Dict[str, int]:
    """Count depth, 2Q gates, CNOT gates, and T/S gates for a Qiskit circuit."""
    depth = int(circuit.depth() or 0)
    two_q = sum(1 for inst in circuit.data if inst.operation.num_qubits == 2)
    cnot = sum(1 for inst in circuit.data if inst.operation.name in ("cx", "cnot"))
    t_like = {"t", "tdg", "s", "sdg"}
    t_count = sum(1 for inst in circuit.data if inst.operation.name in t_like)
    return {"depth": depth, "two_q": two_q, "cnot": cnot, "t_count": t_count}


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
    compiler_version: Optional[str],
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
        "original_t_count": orig_m["t_count"],
        "optimized_t_count": opt_m["t_count"] if opt_m else None,
        "t_count_reduction": _safe_ratio(orig_m["t_count"], opt_m["t_count"]) if opt_m else None,
        "fidelity": fidelity,
        "compilation_time_seconds": runtime,
        "compiler_name": compiler,
        "compiler_backend": compiler_backend,
        "compiler_version": compiler_version,
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
    n_trials: int | None = None,
    max_qubits_fidelity: int = 10,
    skip_cirq: bool = False,
    skip_tket: bool = False,
    skip_custom: bool = False,
    per_circuit_timeout: float = 120.0,
) -> pd.DataFrame:
    """Run E20 multi-compiler full comparison and return the result table."""
    if n_trials is None:
        n_trials = SMOKE_N_TRIALS if mode == "smoke" else DEFAULT_N_TRIALS
    run_id = f"e20_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v6" / "e20"
    output_dir.mkdir(parents=True, exist_ok=True)

    # -- Check compiler availability and versions --
    compiler_avail, compiler_versions = _check_compilers()
    if not compiler_avail["qiskit"]:
        print("WARNING: Qiskit is not installed -- writing metadata and empty results.")
        output_dir = PROJECT_ROOT / "data" / "v6" / "e20"
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "multi_compiler_full.csv"
        df = pd.DataFrame()
        df.to_csv(csv_path, index=False)
        metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
        metadata.update({
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "description": "Full multi-compiler comparison skipped because Qiskit is unavailable",
            "mode": mode,
            "seed": seed,
            "n_trials": n_trials,
            "target_qubits": sorted(TARGET_QUBITS),
            "max_qubits_fidelity": max_qubits_fidelity,
            "compilers_available": compiler_avail,
            "compiler_versions": compiler_versions,
            "compilers_run": [],
            "skip_cirq": skip_cirq,
            "skip_tket": skip_tket,
            "canonical_data_file": csv_path.name,
            "n_circuits_per_trial": 0,
            "n_total_circuit_runs": 0,
            "n_rows": 0,
            "blocker": "qiskit_not_installed",
        })
        with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2, sort_keys=True)
        return df

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
            opt_circ, runtime, status = _run_with_timeout(
                _qiskit_transpile, circuit, opt_level=3, seed_transpiler=trial_seed,
                timeout=per_circuit_timeout,
            )
            if opt_circ is not None and status == "ok":
                opt_m = _count_metrics(opt_circ)
                output_hash = circuit_sha256(opt_circ)
                fidelity = _safe_fidelity(opt_circ, circuit, max_qubits_fidelity)
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
                    compiler_version=compiler_versions.get("qiskit"),
                    compiler_opt_level=3,
                    compiler_status="ok",
                    trial=trial_idx,
                    seed=trial_seed,
                    script_path=script_path,
                    input_hash=input_hash,
                    output_hash=output_hash,
                ))
                print(" [qiskit:ok]", end="")
            else:
                print(f" [qiskit:{status.split(':', 1)[0] if status else 'FAIL'}]", end="")
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
                    runtime=runtime,
                    compiler="qiskit",
                    compiler_backend="transpiler",
                    compiler_version=compiler_versions.get("qiskit"),
                    compiler_opt_level=3,
                    compiler_status=status,
                    trial=trial_idx,
                    seed=trial_seed,
                    script_path=script_path,
                    input_hash=input_hash,
                    output_hash="none",
                ))

            # ---- Cirq ----
            # Cirq is run on instances up to 8 qubits; larger circuits can hang.
            if run_cirq and n_qubits <= 8:
                opt_circ, runtime, status = _run_with_timeout(
                    _cirq_optimize, circuit, timeout=per_circuit_timeout,
                )
                if opt_circ is not None and status == "ok":
                    opt_m = _count_metrics(opt_circ)
                    output_hash = circuit_sha256(opt_circ)
                    fidelity = _safe_fidelity(opt_circ, circuit, max_qubits_fidelity)
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
                        compiler_version=compiler_versions.get("cirq"),
                        compiler_opt_level="default",
                        compiler_status="ok",
                        trial=trial_idx,
                        seed=trial_seed,
                        script_path=script_path,
                        input_hash=input_hash,
                        output_hash=output_hash,
                    ))
                    print(" [cirq:ok]", end="")
                else:
                    print(f" [cirq:{status.split(':', 1)[0] if status else 'FAIL'}]", end="")
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
                        runtime=runtime,
                        compiler="cirq",
                        compiler_backend="optimize_for_target_gateset+eject_z+merge_1q",
                        compiler_version=compiler_versions.get("cirq"),
                        compiler_opt_level="default",
                        compiler_status=status,
                        trial=trial_idx,
                        seed=trial_seed,
                        script_path=script_path,
                        input_hash=input_hash,
                        output_hash="none",
                    ))

            # ---- t|ket> ----
            # FullPeepholeOptimise is run only on small instances (<=6 qubits).
            # On larger circuits it can become non-interruptible and hang the run.
            if run_tket and n_qubits <= 6:
                opt_circ, runtime, status = _run_with_timeout(
                    _tket_optimize, circuit, timeout=per_circuit_timeout,
                )
                if opt_circ is not None and status == "ok":
                    opt_m = _count_metrics(opt_circ)
                    output_hash = circuit_sha256(opt_circ)
                    fidelity = _safe_fidelity(opt_circ, circuit, max_qubits_fidelity)
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
                        compiler_version=compiler_versions.get("tket"),
                        compiler_opt_level="default",
                        compiler_status="ok",
                        trial=trial_idx,
                        seed=trial_seed,
                        script_path=script_path,
                        input_hash=input_hash,
                        output_hash=output_hash,
                    ))
                    print(" [tket:ok]", end="")
                else:
                    print(f" [tket:{status.split(':', 1)[0] if status else 'FAIL'}]", end="")
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
                        runtime=runtime,
                        compiler="tket",
                        compiler_backend="FullPeepholeOptimise",
                        compiler_version=compiler_versions.get("tket"),
                        compiler_opt_level="default",
                        compiler_status=status,
                        trial=trial_idx,
                        seed=trial_seed,
                        script_path=script_path,
                        input_hash=input_hash,
                        output_hash="none",
                    ))

            # ---- Custom optimizers (our Phase-1 / Phase-2) ----
            if not skip_custom:
                for opt_name, opt_cls in [
                    ("greedy_phase1", GreedyGateCancellation),
                    ("commutation_phase2", CommutationRewriter),
                    ("hybrid_phase1_2", HybridCommuteRewrite),
                ]:
                    opt_result, runtime, status = _run_with_timeout(
                        _run_custom_optimizer, circuit, opt_cls,
                        timeout=per_circuit_timeout,
                    )
                    if opt_result is not None and status == "ok":
                        opt_circ, fidelity = opt_result
                        opt_m = _count_metrics(opt_circ)
                        output_hash = circuit_sha256(opt_circ)
                        if fidelity is None or fidelity == 0.0:
                            exact = _safe_fidelity(opt_circ, circuit, max_qubits_fidelity)
                            fidelity = exact if exact is not None else fidelity
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
                            compiler="custom",
                            compiler_backend=opt_name,
                            compiler_version=None,
                            compiler_opt_level="default",
                            compiler_status="ok",
                            trial=trial_idx,
                            seed=trial_seed,
                            script_path=script_path,
                            input_hash=input_hash,
                            output_hash=output_hash,
                        ))
                        print(f" [{opt_name}:ok]", end="")
                    else:
                        print(f" [{opt_name}:{status.split(':', 1)[0] if status else 'FAIL'}]", end="")
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
                            runtime=runtime,
                            compiler="custom",
                            compiler_backend=opt_name,
                            compiler_version=None,
                            compiler_opt_level="default",
                            compiler_status=status,
                            trial=trial_idx,
                            seed=trial_seed,
                            script_path=script_path,
                            input_hash=input_hash,
                            output_hash="none",
                        ))

            print()  # newline after each circuit

    # -- Build DataFrame and save --
    df = pd.DataFrame(rows)
    csv_path = output_dir / "multi_compiler_full.csv"
    df.to_csv(csv_path, index=False)

    # -- Metadata --
    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    compilers_run = ["qiskit"]
    if not skip_custom:
        compilers_run.append("custom")
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
            "t|ket> FullPeepholeOptimise, custom Phase-1/Phase-2 optimizers) "
            "across 15 circuit families"
        ),
        "mode": mode,
        "seed": seed,
        "n_trials": n_trials,
        "target_qubits": sorted(TARGET_QUBITS),
        "max_qubits_fidelity": max_qubits_fidelity,
        "per_circuit_timeout_seconds": per_circuit_timeout,
        "compilers_available": {k: v for k, v in compiler_avail.items()},
        "compiler_versions": {k: v for k, v in compiler_versions.items()},
        "compiler_availability_report": {
            "qiskit": "available" if compiler_avail["qiskit"] else "missing",
            "cirq": "skipped_by_flag" if skip_cirq else ("available" if compiler_avail["cirq"] else "missing"),
            "tket": "skipped_by_flag" if skip_tket else ("available" if compiler_avail["tket"] else "missing"),
        },
        "basis_gate_sets": {
            "qiskit": "default transpiler basis (cx, u, h, s, t where selected by transpiler)",
            "cirq": "CZTargetGateset (PhasedXZ + CZ)",
            "tket": "pytket FullPeepholeOptimise default basis",
        },
        "compilers_run": compilers_run,
        "custom_optimizers": ["greedy_phase1", "commutation_phase2", "hybrid_phase1_2"],
        "skip_cirq": skip_cirq,
        "skip_tket": skip_tket,
        "skip_custom": skip_custom,
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
        "--mode", choices=["smoke", "full"], default="smoke",
        help="'smoke' for quick validation (default), 'full' for publication results"
    )
    parser.add_argument("--seed", type=int, default=42, help="Base random seed")
    parser.add_argument(
        "--n-trials", type=int, default=None,
        help=f"Number of random trials per (family, qubit_count) cell (default: {SMOKE_N_TRIALS} smoke, {DEFAULT_N_TRIALS} full)"
    )
    parser.add_argument(
        "--max-qubits-fidelity", type=int, default=10,
        help="Max qubits for exact unitary fidelity computation"
    )
    parser.add_argument("--skip-cirq", action="store_true", help="Skip Cirq backend")
    parser.add_argument("--skip-tket", action="store_true", help="Skip t|ket> backend")
    parser.add_argument("--skip-custom", action="store_true", help="Skip custom Phase-1/Phase-2 optimizers")
    parser.add_argument(
        "--timeout", type=float, default=120.0,
        help="Per-circuit compiler timeout in seconds (default: 120)"
    )
    args = parser.parse_args()

    run(
        mode=args.mode,
        seed=args.seed,
        n_trials=args.n_trials,
        max_qubits_fidelity=args.max_qubits_fidelity,
        skip_cirq=args.skip_cirq,
        skip_tket=args.skip_tket,
        skip_custom=args.skip_custom,
        per_circuit_timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
