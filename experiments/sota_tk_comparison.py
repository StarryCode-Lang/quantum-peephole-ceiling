"""SOTA t|ket> comparison script: FullPeepholeOptimise on the 15-family benchmark.

This script extends the E20 multi-compiler comparison with a dedicated t|ket>
benchmark using both default and tuned configurations.  It produces a CSV with
the unified metric schema defined in SOTA_BENCHMARK_PROTOCOL.md.

Usage:
    python experiments/sota_tk_comparison.py --mode full
    python experiments/sota_tk_comparison.py --mode smoke --n-trials 1
    python experiments/sota_tk_comparison.py --mode full --config tuned

Output:
    data/v6/sota_benchmark/raw/tket_{config}_{run_id}.csv
    data/v6/sota_benchmark/metadata/tket_{config}_metadata.json
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import (  # noqa: E402
    average_gate_fidelity,
    circuit_sha256,
    gate_counts,
    generate_extended_suite,
)
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "1.0.0"
EXPERIMENT_ID = "SOTA-TKET"
VERSION = "1.0.0"
DEFAULT_TIMEOUT_S = 60.0


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def _count_metrics(circuit) -> Dict[str, int]:
    """Count T, S, CNOT, 2Q, depth, total gates for a Qiskit circuit."""
    t_like = {"t", "tdg"}
    s_like = {"s", "sdg"}
    return {
        "t_count": sum(1 for inst in circuit.data if inst.operation.name in t_like),
        "s_count": sum(1 for inst in circuit.data if inst.operation.name in s_like),
        "cnot_count": sum(1 for inst in circuit.data if inst.operation.name in ("cx", "cnot")),
        "two_q_count": sum(1 for inst in circuit.data if inst.operation.num_qubits == 2),
        "depth": int(circuit.depth() or 0),
        "gate_count": int(circuit.size()),
    }


def _reduction_pct(original: int, optimized: int) -> float:
    """Safe percentage reduction."""
    if original is None or original <= 0 or optimized is None or optimized < 0:
        return 0.0
    return round(100.0 * (1.0 - optimized / original), 4)


# ---------------------------------------------------------------------------
# t|ket> optimization backends
# ---------------------------------------------------------------------------

def _tket_default(circuit):
    """t|ket> FullPeepholeOptimise with default parameters."""
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
    from pytket.passes import DecomposeBoxes, FullPeepholeOptimise

    tk_circ = qiskit_to_tk(circuit)
    DecomposeBoxes().apply(tk_circ)
    FullPeepholeOptimise().apply(tk_circ)
    return tk_to_qiskit(tk_circ)


def _tket_tuned(circuit):
    """t|ket> tuned: FullPeepholeOptimise + PeepholeOptimise (second pass) +
    contextual simplification."""
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
    from pytket.passes import (
        DecomposeBoxes,
        FullPeepholeOptimise,
        PeepholeOptimise,
        ContextualSimplification,
    )

    tk_circ = qiskit_to_tk(circuit)
    DecomposeBoxes().apply(tk_circ)
    FullPeepholeOptimise().apply(tk_circ)
    # Second pass: catch opportunities revealed by first pass
    PeepholeOptimise().apply(tk_circ)
    # Contextual simplification (removes redundant operations based on
    # known qubit states at circuit boundaries)
    try:
        ContextualSimplification(allow_alpha_state=True).apply(tk_circ)
    except Exception:
        # Some circuits may not support alpha-state simplification
        pass
    return tk_to_qiskit(tk_circ)


# ---------------------------------------------------------------------------
# Timeout wrapper
# ---------------------------------------------------------------------------

def _run_with_timeout(fn, *args, timeout: float = DEFAULT_TIMEOUT_S, **kwargs):
    """Run fn in a background thread with timeout."""
    result_container = [None]
    exception_container = [None]

    def _target():
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
# Main benchmark loop
# ---------------------------------------------------------------------------

def run(mode: str = "full", n_trials: int = 10, config: str = "default",
        seed: int = 42, timeout_s: float = DEFAULT_TIMEOUT_S) -> pd.DataFrame:
    """Run t|ket> FullPeepholeOptimise on the 15-family benchmark.

    Parameters
    ----------
    mode : "smoke" or "full"
    n_trials : number of random trials per (family, n_qubits) cell
    config : "default" or "tuned"
    seed : base random seed
    timeout_s : per-circuit timeout in seconds
    """
    run_id = f"tket_{config}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v6" / "sota_benchmark" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    meta_dir = PROJECT_ROOT / "data" / "v6" / "sota_benchmark" / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)

    # Detect pytket version
    try:
        import pytket
        tket_version = pytket.__version__
    except ImportError:
        tket_version = "not-installed"

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "tool": "tket",
        "tool_config": config,
        "tool_version": tket_version,
        "mode": mode,
        "n_trials": n_trials,
        "seed": seed,
        "timeout_s": timeout_s,
    })

    # Select optimization backend
    opt_fn = _tket_default if config == "default" else _tket_tuned

    # Generate circuits
    # For multiple trials, vary the seed offset
    all_rows: List[dict] = []
    for trial in range(n_trials):
        trial_seed = seed + trial * 1000
        circuits = generate_extended_suite(mode=mode, seed=trial_seed)
        for bench in circuits:
            circuit = bench.circuit
            input_hash = circuit_sha256(circuit)
            orig_metrics = _count_metrics(circuit)
            orig_counts = gate_counts(circuit)

            # Run t|ket> with timeout
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                opt_circ, runtime, status = _run_with_timeout(
                    opt_fn, circuit, timeout=timeout_s
                )

            if status == "ok" and opt_circ is not None:
                opt_metrics = _count_metrics(opt_circ)
                output_hash = circuit_sha256(opt_circ)
                fidelity = average_gate_fidelity(opt_circ, circuit, max_qubits=8)
                fidelity_source = "exact" if fidelity is not None else "unavailable"
            else:
                opt_metrics = {k: -1 for k in ["t_count", "s_count", "cnot_count",
                                                "two_q_count", "depth", "gate_count"]}
                output_hash = ""
                fidelity = None
                fidelity_source = "error" if "error" in status else "timeout"

            row = {
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "run_id": run_id,
                "tool": "tket",
                "tool_config": config,
                "tool_version": tket_version,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "circuit_family": bench.family,
                "circuit_id": bench.circuit_id,
                "circuit_type": bench.circuit_type,
                "n_qubits": circuit.num_qubits,
                "trial": trial,
                "seed": trial_seed,
                # Baseline metrics
                "t_count": orig_metrics["t_count"],
                "s_count": orig_metrics["s_count"],
                "cnot_count": orig_metrics["cnot_count"],
                "two_q_count": orig_metrics["two_q_count"],
                "depth": orig_metrics["depth"],
                "gate_count": orig_metrics["gate_count"],
                "baseline_gate_count": int(circuit.size()),
                # Optimized metrics
                "optimized_t_count": opt_metrics["t_count"],
                "optimized_s_count": opt_metrics["s_count"],
                "optimized_cnot_count": opt_metrics["cnot_count"],
                "optimized_two_q_count": opt_metrics["two_q_count"],
                "optimized_depth": opt_metrics["depth"],
                "optimized_gate_count": opt_metrics["gate_count"],
                # Reductions
                "gate_reduction_pct": _reduction_pct(orig_metrics["gate_count"], opt_metrics["gate_count"]),
                "t_count_reduction_pct": _reduction_pct(orig_metrics["t_count"], opt_metrics["t_count"]),
                "cnot_reduction_pct": _reduction_pct(orig_metrics["cnot_count"], opt_metrics["cnot_count"]),
                "depth_reduction_pct": _reduction_pct(orig_metrics["depth"], opt_metrics["depth"]),
                # Fidelity and status
                "fidelity": fidelity,
                "fidelity_source": fidelity_source,
                "runtime_seconds": round(runtime, 6),
                "compiler_status": status,
                # Provenance
                "input_circuit_sha256": input_hash,
                "output_circuit_sha256": output_hash,
                "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                "source_sha256": file_sha256(script_path),
            }
            all_rows.append(row)

    df = pd.DataFrame(all_rows)
    csv_path = output_dir / f"{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata["canonical_data_file"] = csv_path.name
    metadata["n_rows"] = len(df)
    metadata["n_circuits"] = df.groupby(["circuit_family", "n_qubits"]).ngroups
    metadata["n_timeouts"] = int((df["compiler_status"] == "timeout").sum())
    metadata["n_errors"] = int(df["compiler_status"].str.contains("error").sum())
    metadata["n_ok"] = int((df["compiler_status"] == "ok").sum())

    with (meta_dir / f"tket_{config}_metadata.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, sort_keys=True)

    print(f"SOTA-TKET complete: {len(df)} rows -> {csv_path}")
    print(f"  OK: {metadata['n_ok']}, Timeouts: {metadata['n_timeouts']}, "
          f"Errors: {metadata['n_errors']}")
    if metadata["n_ok"] > 0:
        ok_df = df[df["compiler_status"] == "ok"]
        summary = ok_df.groupby("circuit_family")["gate_reduction_pct"].agg(["mean", "median"])
        print("\nGate reduction (%) by family:")
        print(summary.to_string())
    return df


def main():
    parser = argparse.ArgumentParser(
        description="SOTA t|ket> FullPeepholeOptimise comparison"
    )
    parser.add_argument("--mode", choices=["smoke", "full"], default="full")
    parser.add_argument("--n-trials", type=int, default=10)
    parser.add_argument("--config", choices=["default", "tuned", "both"], default="default")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    args = parser.parse_args()

    if args.config == "both":
        run(mode=args.mode, n_trials=args.n_trials, config="default",
            seed=args.seed, timeout_s=args.timeout)
        run(mode=args.mode, n_trials=args.n_trials, config="tuned",
            seed=args.seed, timeout_s=args.timeout)
    else:
        run(mode=args.mode, n_trials=args.n_trials, config=args.config,
            seed=args.seed, timeout_s=args.timeout)


if __name__ == "__main__":
    main()
