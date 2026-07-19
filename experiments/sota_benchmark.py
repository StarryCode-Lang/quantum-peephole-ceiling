"""Generic SOTA benchmark framework: unified comparison across all tools.

This script provides a unified interface for running multiple quantum circuit
optimizers on the same 15-family benchmark suite.  It supports t|ket>,
Qiskit, Cirq, VOQC (if available), and the custom prototype optimizers,
producing a single aggregated CSV with the unified metric schema defined in
SOTA_BENCHMARK_PROTOCOL.md.

Usage:
    # Run a single tool
    python experiments/sota_benchmark.py --tool tket --mode full
    python experiments/sota_benchmark.py --tool qiskit --mode full
    python experiments/sota_benchmark.py --tool cirq --mode full
    python experiments/sota_benchmark.py --tool custom --mode full
    python experiments/sota_benchmark.py --tool voqc --mode full

    # Run all available tools
    python experiments/sota_benchmark.py --all --mode full

    # Aggregate results from all runs
    python experiments/sota_benchmark.py --aggregate

Output:
    data/v6/sota_benchmark/raw/{tool}_{config}_{run_id}.csv
    data/v6/sota_benchmark/aggregated/sota_comparison_aggregated.csv
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
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import (  # noqa: E402
    average_gate_fidelity,
    circuit_sha256,
    generate_extended_suite,
)
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "1.0.0"
EXPERIMENT_ID = "SOTA-BENCH"
VERSION = "1.0.0"
DEFAULT_TIMEOUT_S = 120.0
DEFAULT_N_TRIALS = 10
TARGET_QUBITS = {4, 6, 8}

# Gate categories for unified metric extraction
T_GATES = {"t", "tdg"}
S_GATES = {"s", "sdg"}
CNOT_GATES = {"cx", "cnot"}


# ---------------------------------------------------------------------------
# Unified metric extraction
# ---------------------------------------------------------------------------

def count_metrics(circuit) -> Dict[str, int]:
    """Extract unified metrics from a Qiskit QuantumCircuit."""
    return {
        "t_count": sum(1 for inst in circuit.data if inst.operation.name in T_GATES),
        "s_count": sum(1 for inst in circuit.data if inst.operation.name in S_GATES),
        "cnot_count": sum(1 for inst in circuit.data if inst.operation.name in CNOT_GATES),
        "two_q_count": sum(1 for inst in circuit.data if inst.operation.num_qubits == 2),
        "depth": int(circuit.depth() or 0),
        "gate_count": int(circuit.size()),
    }


def reduction_pct(original: int, optimized: int) -> float:
    """Safe percentage reduction (positive = improvement)."""
    if original is None or original <= 0 or optimized is None or optimized < 0:
        return 0.0
    return round(100.0 * (1.0 - optimized / original), 4)


def cliffs_delta(a: List[float], b: List[float]) -> float:
    """Cliff's delta effect size (non-parametric)."""
    a, b = np.array(a), np.array(b)
    if len(a) == 0 or len(b) == 0:
        return 0.0
    count = 0
    for x in a:
        for y in b:
            if x > y:
                count += 1
            elif x < y:
                count -= 1
    return count / (len(a) * len(b))


# ---------------------------------------------------------------------------
# Timeout wrapper
# ---------------------------------------------------------------------------

def run_with_timeout(fn: Callable, *args, timeout: float = DEFAULT_TIMEOUT_S, **kwargs):
    """Run fn with a timeout. Returns (result, elapsed_s, status)."""
    result_container: List[Any] = [None]
    exception_container: List[BaseException] = [None]

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
# Tool backends
# ---------------------------------------------------------------------------

def tket_optimize(circuit, config: str = "default"):
    """t|ket> FullPeepholeOptimise."""
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
    from pytket.passes import DecomposeBoxes, FullPeepholeOptimise

    tk_circ = qiskit_to_tk(circuit)
    DecomposeBoxes().apply(tk_circ)
    FullPeepholeOptimise().apply(tk_circ)
    if config == "tuned":
        from pytket.passes import PeepholeOptimise
        PeepholeOptimise().apply(tk_circ)
    return tk_to_qiskit(tk_circ)


def qiskit_optimize(circuit, config: str = "default", seed: int = 42):
    """Qiskit transpile (fair mode: no coupling map)."""
    from qiskit import transpile
    level = 3 if config in ("default", "tuned") else 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return transpile(circuit, optimization_level=level, seed_transpiler=seed)


def cirq_optimize(circuit, config: str = "default"):
    """Cirq optimization pipeline."""
    import cirq
    from cirq.contrib.qasm_import import circuit_from_qasm
    from qiskit.qasm2 import dumps as qasm2_dumps, loads as qasm2_loads
    from cirq.transformers import (
        drop_empty_moments, drop_negligible_operations, eject_z,
        merge_single_qubit_gates_to_phased_x_and_z, optimize_for_target_gateset,
    )

    qasm_str = qasm2_dumps(circuit)
    cirq_circ = circuit_from_qasm(qasm_str)
    cirq_circ = drop_empty_moments(cirq_circ)
    cirq_circ = drop_negligible_operations(cirq_circ)
    try:
        cirq_circ = optimize_for_target_gateset(cirq_circ, target_gateset=cirq.CZTargetGateset())
    except Exception:
        pass
    cirq_circ = eject_z(cirq_circ)
    cirq_circ = merge_single_qubit_gates_to_phased_x_and_z(cirq_circ)
    cirq_circ = drop_empty_moments(cirq_circ)
    qasm_out = cirq.qasm(cirq_circ)
    return qasm2_loads(qasm_out)


def custom_optimize(circuit, config: str = "default"):
    """Custom prototype optimizer (Phase-1 Greedy + Phase-2a Hybrid)."""
    if config == "phase1":
        from src.optimisation.phase1.greedy import GreedyGateCancellation
        opt = GreedyGateCancellation(success_reduction=0.01)
    elif config in ("phase2", "hybrid"):
        from src.optimisation.phase2.commutation_rewriter import HybridCommuteRewrite
        opt = HybridCommuteRewrite(success_reduction=0.01)
    else:
        from src.optimisation.phase1.greedy import GreedyGateCancellation
        opt = GreedyGateCancellation(success_reduction=0.01)
    result = opt.optimize(circuit, target=circuit)
    return result.optimized_circuit


def voqc_optimize(circuit, config: str = "default"):
    """VOQC verified optimizer (if pyvoqc is available)."""
    from qiskit.qasm2 import dumps as qasm2_dumps, loads as qasm2_loads
    import pyvoqc

    qasm_str = qasm2_dumps(circuit)
    v = pyvoqc.VOQC()
    optimized_qasm = v.optimize(qasm_str)
    return qasm2_loads(optimized_qasm)


# Tool registry
TOOL_REGISTRY: Dict[str, Callable] = {
    "tket": tket_optimize,
    "qiskit": qiskit_optimize,
    "cirq": cirq_optimize,
    "custom": custom_optimize,
    "voqc": voqc_optimize,
}


def check_tool_available(tool: str) -> Tuple[bool, Optional[str]]:
    """Check if a tool is available in the current environment."""
    try:
        if tool == "tket":
            import pytket
            from pytket.extensions.qiskit import qiskit_to_tk
            from pytket.passes import FullPeepholeOptimise
            return True, pytket.__version__
        elif tool == "qiskit":
            import qiskit
            from qiskit import transpile
            return True, qiskit.__version__
        elif tool == "cirq":
            import cirq
            return True, cirq.__version__
        elif tool == "custom":
            from src.optimisation.phase1.greedy import GreedyGateCancellation
            return True, "prototype-v4"
        elif tool == "voqc":
            import pyvoqc
            return True, getattr(pyvoqc, "__version__", "unknown")
    except ImportError as e:
        return False, str(e)
    return False, "unknown tool"


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def build_row(
    *, tool: str, tool_config: str, tool_version: str, run_id: str,
    bench, trial: int, seed: int, orig_m: Dict[str, int],
    opt_circ, opt_m: Optional[Dict[str, int]], fidelity: Optional[float],
    runtime: float, status: str, script_path: Path,
) -> dict:
    """Build a single result row with the unified schema."""
    circuit = bench.circuit
    input_hash = circuit_sha256(circuit)
    output_hash = circuit_sha256(opt_circ) if opt_circ is not None else ""

    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "tool": tool,
        "tool_config": tool_config,
        "tool_version": tool_version,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "circuit_family": bench.family,
        "circuit_id": bench.circuit_id,
        "n_qubits": circuit.num_qubits,
        "trial": trial,
        "seed": seed,
        # Baseline metrics
        "t_count": orig_m["t_count"],
        "s_count": orig_m["s_count"],
        "cnot_count": orig_m["cnot_count"],
        "two_q_count": orig_m["two_q_count"],
        "depth": orig_m["depth"],
        "gate_count": orig_m["gate_count"],
        "baseline_gate_count": int(circuit.size()),
        # Optimized metrics
        "optimized_t_count": opt_m["t_count"] if opt_m else -1,
        "optimized_s_count": opt_m["s_count"] if opt_m else -1,
        "optimized_cnot_count": opt_m["cnot_count"] if opt_m else -1,
        "optimized_two_q_count": opt_m["two_q_count"] if opt_m else -1,
        "optimized_depth": opt_m["depth"] if opt_m else -1,
        "optimized_gate_count": opt_m["gate_count"] if opt_m else -1,
        # Reductions
        "gate_reduction_pct": reduction_pct(orig_m["gate_count"], opt_m["gate_count"]) if opt_m else 0.0,
        "t_count_reduction_pct": reduction_pct(orig_m["t_count"], opt_m["t_count"]) if opt_m else 0.0,
        "cnot_reduction_pct": reduction_pct(orig_m["cnot_count"], opt_m["cnot_count"]) if opt_m else 0.0,
        "depth_reduction_pct": reduction_pct(orig_m["depth"], opt_m["depth"]) if opt_m else 0.0,
        # Fidelity and status
        "fidelity": fidelity,
        "fidelity_source": "exact" if fidelity is not None else ("error" if "error" in status else "timeout"),
        "runtime_seconds": round(runtime, 6),
        "compiler_status": status,
        # Provenance
        "input_circuit_sha256": input_hash,
        "output_circuit_sha256": output_hash,
        "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
        "source_sha256": file_sha256(script_path),
    }


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------

def run_tool(
    tool: str, config: str = "default", mode: str = "full",
    n_trials: int = DEFAULT_N_TRIALS, seed: int = 42,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> pd.DataFrame:
    """Run a single tool on the 15-family benchmark."""
    available, version_or_err = check_tool_available(tool)
    if not available:
        print(f"Tool '{tool}' not available: {version_or_err}")
        return pd.DataFrame()

    run_id = f"{tool}_{config}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v6" / "sota_benchmark" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    meta_dir = PROJECT_ROOT / "data" / "v6" / "sota_benchmark" / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)

    opt_fn = TOOL_REGISTRY[tool]
    all_rows: List[dict] = []

    for trial in range(n_trials):
        trial_seed = seed + trial * 1000
        circuits = generate_extended_suite(mode=mode, seed=trial_seed)
        # Filter to target qubit sizes for controlled comparison
        circuits = [b for b in circuits if b.circuit.num_qubits in TARGET_QUBITS or
                     int(b.circuit_id.rsplit("_", 1)[-1]) in TARGET_QUBITS]

        for bench in circuits:
            circuit = bench.circuit
            orig_m = count_metrics(circuit)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if tool == "qiskit":
                    opt_circ, runtime, status = run_with_timeout(
                        opt_fn, circuit, config=config, seed=trial_seed, timeout=timeout_s
                    )
                else:
                    opt_circ, runtime, status = run_with_timeout(
                        opt_fn, circuit, config=config, timeout=timeout_s
                    )

            if status == "ok" and opt_circ is not None:
                opt_m = count_metrics(opt_circ)
                fidelity = average_gate_fidelity(opt_circ, circuit, max_qubits=8)
            else:
                opt_m = None
                fidelity = None

            row = build_row(
                tool=tool, tool_config=config, tool_version=version_or_err,
                run_id=run_id, bench=bench, trial=trial, seed=trial_seed,
                orig_m=orig_m, opt_circ=opt_circ, opt_m=opt_m,
                fidelity=fidelity, runtime=runtime, status=status,
                script_path=script_path,
            )
            all_rows.append(row)

    df = pd.DataFrame(all_rows)
    csv_path = output_dir / f"{run_id}.csv"
    df.to_csv(csv_path, index=False)

    # Metadata
    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "tool": tool,
        "tool_config": config,
        "tool_version": version_or_err,
        "mode": mode,
        "n_trials": n_trials,
        "seed": seed,
        "timeout_s": timeout_s,
        "canonical_data_file": csv_path.name,
        "n_rows": len(df),
        "n_ok": int((df["compiler_status"] == "ok").sum()),
        "n_timeouts": int((df["compiler_status"] == "timeout").sum()),
        "n_errors": int(df["compiler_status"].str.contains("error").sum()),
    })
    with (meta_dir / f"{tool}_{config}_metadata.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, sort_keys=True)

    print(f"SOTA-BENCH [{tool}/{config}] complete: {len(df)} rows -> {csv_path}")
    print(f"  OK: {metadata['n_ok']}, Timeouts: {metadata['n_timeouts']}, "
          f"Errors: {metadata['n_errors']}")
    return df


# ---------------------------------------------------------------------------
# Aggregation with statistics
# ---------------------------------------------------------------------------

def aggregate_results() -> pd.DataFrame:
    """Aggregate all raw CSV files and compute statistics."""
    raw_dir = PROJECT_ROOT / "data" / "v6" / "sota_benchmark" / "raw"
    agg_dir = PROJECT_ROOT / "data" / "v6" / "sota_benchmark" / "aggregated"
    agg_dir.mkdir(parents=True, exist_ok=True)

    if not raw_dir.exists():
        print("No raw data found. Run benchmarks first.")
        return pd.DataFrame()

    dfs = []
    for csv_file in raw_dir.glob("*.csv"):
        try:
            df = pd.read_csv(csv_file)
            dfs.append(df)
        except Exception as e:
            print(f"  Skipping {csv_file.name}: {e}")

    if not dfs:
        print("No valid CSV files found.")
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    # Only keep successful runs for aggregation
    ok = combined[combined["compiler_status"] == "ok"].copy()

    if ok.empty:
        print("No successful runs to aggregate.")
        return pd.DataFrame()

    # Per-family, per-tool aggregation
    agg_rows = []
    tools = ok["tool"].unique()
    families = ok["circuit_family"].unique()
    n_comparisons = len(families)
    holm_alpha = 0.05 / n_comparisons

    for tool in tools:
        tool_df = ok[ok["tool"] == tool]
        for family in families:
            fam_df = tool_df[tool_df["circuit_family"] == family]
            if fam_df.empty:
                continue
            # Get custom tool data for comparison (if custom exists)
            custom_df = ok[(ok["tool"] == "custom") & (ok["circuit_family"] == family)]
            tool_reductions = fam_df["gate_reduction_pct"].tolist()
            custom_reductions = custom_df["gate_reduction_pct"].tolist()

            # Statistical tests
            mw_p = None
            wilcox_p = None
            delta = None
            holm_sig = False

            if tool != "custom" and len(tool_reductions) >= 3 and len(custom_reductions) >= 3:
                try:
                    _, mw_p = stats.mannwhitneyu(tool_reductions, custom_reductions,
                                                 alternative="two-sided")
                except Exception:
                    mw_p = None
                try:
                    _, wilcox_p = stats.wilcoxon(tool_reductions, custom_reductions)
                except Exception:
                    wilcox_p = None
                delta = cliffs_delta(tool_reductions, custom_reductions)
                holm_sig = (mw_p is not None and mw_p < holm_alpha)

            agg_rows.append({
                "tool": tool,
                "circuit_family": family,
                "n_qubits_median": float(fam_df["n_qubits"].median()),
                "n_trials": len(fam_df),
                "mean_gate_reduction": round(float(fam_df["gate_reduction_pct"].mean()), 4),
                "median_gate_reduction": round(float(fam_df["gate_reduction_pct"].median()), 4),
                "iqr_gate_reduction": round(
                    float(fam_df["gate_reduction_pct"].quantile(0.75) -
                          fam_df["gate_reduction_pct"].quantile(0.25)), 4),
                "mean_t_count_reduction": round(float(fam_df["t_count_reduction_pct"].mean()), 4),
                "mean_cnot_reduction": round(float(fam_df["cnot_reduction_pct"].mean()), 4),
                "mean_depth_reduction": round(float(fam_df["depth_reduction_pct"].mean()), 4),
                "mean_runtime_seconds": round(float(fam_df["runtime_seconds"].mean()), 6),
                "fidelity_pass_rate": round(
                    float((fam_df["fidelity_source"] == "exact").mean()), 4),
                "mann_whitney_p_vs_custom": mw_p,
                "wilcoxon_p_vs_custom": wilcox_p,
                "cliffs_delta_vs_custom": round(delta, 4) if delta is not None else None,
                "holm_significant": holm_sig,
                "holm_alpha": holm_alpha,
            })

    agg_df = pd.DataFrame(agg_rows)
    agg_csv = agg_dir / "sota_comparison_aggregated.csv"
    agg_df.to_csv(agg_csv, index=False)
    print(f"Aggregated {len(agg_df)} rows -> {agg_csv}")
    return agg_df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SOTA benchmark: unified comparison across quantum circuit optimizers"
    )
    parser.add_argument("--tool", choices=list(TOOL_REGISTRY.keys()) + ["all"],
                        default="all")
    parser.add_argument("--config", default="default",
                        help="Tool configuration: default, tuned, phase1, phase2, hybrid")
    parser.add_argument("--mode", choices=["smoke", "full"], default="full")
    parser.add_argument("--n-trials", type=int, default=DEFAULT_N_TRIALS)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--aggregate", action="store_true",
                        help="Aggregate all raw CSVs and compute statistics")
    args = parser.parse_args()

    if args.aggregate:
        aggregate_results()
        return

    if args.tool == "all":
        for tool in TOOL_REGISTRY:
            available, _ = check_tool_available(tool)
            if available:
                run_tool(tool, config=args.config, mode=args.mode,
                         n_trials=args.n_trials, seed=args.seed,
                         timeout_s=args.timeout)
            else:
                print(f"Skipping {tool}: not available")
        # Auto-aggregate after all runs
        aggregate_results()
    else:
        run_tool(args.tool, config=args.config, mode=args.mode,
                 n_trials=args.n_trials, seed=args.seed,
                 timeout_s=args.timeout)


if __name__ == "__main__":
    main()
