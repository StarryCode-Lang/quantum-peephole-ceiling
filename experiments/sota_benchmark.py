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
import hashlib
import json
import multiprocessing as mp
import queue
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
    BenchmarkCircuit,
    average_gate_fidelity,
    circuit_sha256,
    generate_extended_suite,
)
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "1.1.0"
EXPERIMENT_ID = "SOTA-BENCH"
VERSION = "1.2.0"  # 2026-08-11: stage timing, CPU/RSS, and 2Q-depth instrumentation
DEFAULT_TIMEOUT_S = 120.0
DEFAULT_N_TRIALS = 10
TARGET_QUBITS = {4, 6, 8}
COMMON_BASIS = ["rz", "sx", "x", "cx"]
PREPAPER_ROOT = PROJECT_ROOT / "data" / "v10" / "prepaper" / "sota"

# Qiskit optimization_level per tool_config.  "default" is kept at level 3 for
# backward compatibility with the canonical 2026-07-18 runs.
QISKIT_LEVELS = {
    "level0": 0, "level1": 1, "level2": 2, "level3": 3,
    "default": 3, "tuned": 3,
}

# OpenQASM 2.0 gate definitions for sx/sxdg (identical to qiskit's qelib1.inc).
# qiskit.qasm2's builtin qelib1 gate set does NOT include sx/sxdg, so QASM text
# emitted by Cirq (which uses them) fails to re-import without explicit defs.
QASM2_SX_DEFS = (
    'gate sx a { sdg a; h a; sdg a; }\n'
    'gate sxdg a { s a; h a; s a; }\n'
)

# Gate categories for unified metric extraction
T_GATES = {"t", "tdg"}
S_GATES = {"s", "sdg"}
CNOT_GATES = {"cx", "cnot"}


# ---------------------------------------------------------------------------
# Unified metric extraction
# ---------------------------------------------------------------------------

def count_metrics(circuit) -> Dict[str, int]:
    """Extract unified metrics from a Qiskit QuantumCircuit."""
    two_q_depth = int(circuit.depth(
        filter_function=lambda inst: inst.operation.num_qubits == 2
    ) or 0)
    return {
        "t_count": sum(1 for inst in circuit.data if inst.operation.name in T_GATES),
        "s_count": sum(1 for inst in circuit.data if inst.operation.name in S_GATES),
        "cnot_count": sum(1 for inst in circuit.data if inst.operation.name in CNOT_GATES),
        "two_q_count": sum(1 for inst in circuit.data if inst.operation.num_qubits == 2),
        "two_q_depth": two_q_depth,
        "depth": int(circuit.depth() or 0),
        "gate_count": int(circuit.size()),
    }


def normalize_to_common_basis(circuit, seed: int):
    """Decompose without optimization to the preregistered comparison basis."""
    from qiskit import transpile

    return transpile(
        circuit,
        basis_gates=COMMON_BASIS,
        optimization_level=0,
        seed_transpiler=seed,
    )


def prepare_benchmark_manifest(
    *, mode: str = "full", n_trials: int = DEFAULT_N_TRIALS,
    seed: int = 42, target_qubits: Optional[set] = None,
    output_root: Path = PREPAPER_ROOT,
) -> Path:
    """Materialize the immutable shared inputs used by every optimizer.

    QASM is round-tripped before hashing so that the manifest identifies the
    exact circuit object later consumed by all backends, rather than an
    independently regenerated approximation of it.
    """
    from qiskit import qasm2

    target_qubits = TARGET_QUBITS if target_qubits is None else set(target_qubits)
    input_dir = output_root / "inputs"
    qasm_dir = input_dir / "qasm"
    qasm_dir.mkdir(parents=True, exist_ok=True)
    rows: List[dict] = []

    for trial in range(n_trials):
        trial_seed = seed + trial * 1000
        circuits = generate_extended_suite(mode=mode, seed=trial_seed)
        circuits = [
            b for b in circuits
            if b.circuit.num_qubits in target_qubits
            or int(b.circuit_id.rsplit("_", 1)[-1]) in target_qubits
        ]
        for index, bench in enumerate(circuits):
            qasm_text = qasm2.dumps(bench.circuit)
            consumed = qasm2.loads(
                qasm_text,
                custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
            )
            # qiskit_to_tk cannot consume generic multi-controlled operations
            # even when their OpenQASM definitions are present.  Recursively
            # inline every defined >3-qubit operation; one pass is insufficient
            # because decomposing ``mcx`` can expose ``mcphase`` or dynamically
            # named ``mcx_*`` instructions at the next level.
            for _ in range(12):
                names = {
                    inst.operation.name for inst in consumed.data
                    if inst.operation.num_qubits > 3
                    and inst.operation.definition is not None
                }
                if not names:
                    break
                consumed = consumed.decompose(gates_to_decompose=sorted(names))
            else:
                raise RuntimeError(
                    f"Portable input decomposition did not converge: {bench.circuit_id}"
                )
            qasm_text = qasm2.dumps(consumed)
            consumed = qasm2.loads(
                qasm_text,
                custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
            )
            consumed_hash = circuit_sha256(consumed)
            safe_id = "".join(c if c.isalnum() or c in "-_" else "-" for c in bench.circuit_id)
            filename = f"t{trial:02d}_{index:03d}_{safe_id}_{consumed_hash[:12]}.qasm"
            qasm_path = qasm_dir / filename
            _atomic_write_text(qasm_path, qasm_text)
            rows.append({
                "schema_version": "1.0.0",
                "trial": trial,
                "seed": trial_seed,
                "circuit_id": bench.circuit_id,
                "circuit_family": bench.family,
                "circuit_type": bench.circuit_type,
                "suite": bench.suite,
                "n_qubits": consumed.num_qubits,
                "source_circuit_sha256": circuit_sha256(bench.circuit),
                "input_circuit_sha256": consumed_hash,
                "qasm_sha256": file_sha256(qasm_path),
                "qasm_path": qasm_path.relative_to(PROJECT_ROOT).as_posix(),
                "notes": bench.notes,
            })

    manifest = pd.DataFrame(rows).sort_values(
        ["trial", "circuit_family", "circuit_id"], kind="stable"
    ).reset_index(drop=True)
    pair_cols = ["trial", "seed", "circuit_id", "input_circuit_sha256"]
    if manifest.duplicated(pair_cols).any():
        raise RuntimeError("Shared benchmark manifest contains duplicate pair keys")
    manifest_path = input_dir / "benchmark_manifest.csv"
    _atomic_write_text(manifest_path, manifest.to_csv(index=False))
    metadata = {
        "schema_version": "1.0.0",
        "mode": mode,
        "n_trials": n_trials,
        "base_seed": seed,
        "target_qubits": sorted(target_qubits),
        "n_rows": len(manifest),
        "manifest_sha256": file_sha256(manifest_path),
        "common_basis": COMMON_BASIS,
    }
    _atomic_write_text(
        input_dir / "benchmark_manifest_metadata.json",
        json.dumps(metadata, indent=2, sort_keys=True),
    )
    print(f"Shared benchmark manifest: {len(manifest)} rows -> {manifest_path}")
    return manifest_path


def load_benchmark_manifest(manifest_path: Path) -> Tuple[List[Tuple[BenchmarkCircuit, int, int, float]], str]:
    """Load and verify every materialized input before a tool is run."""
    from qiskit import qasm2

    manifest_path = manifest_path.resolve()
    manifest_sha = file_sha256(manifest_path)
    frame = pd.read_csv(manifest_path)
    loaded: List[Tuple[BenchmarkCircuit, int, int, float]] = []
    for row in frame.to_dict(orient="records"):
        parse_started = time.perf_counter()
        qasm_path = PROJECT_ROOT / str(row["qasm_path"])
        if file_sha256(qasm_path) != str(row["qasm_sha256"]):
            raise RuntimeError(f"QASM SHA mismatch: {qasm_path}")
        circuit = qasm2.loads(
            qasm_path.read_text(encoding="utf-8"),
            custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
        )
        if circuit_sha256(circuit) != str(row["input_circuit_sha256"]):
            raise RuntimeError(f"Circuit SHA mismatch after QASM load: {qasm_path}")
        parse_elapsed = time.perf_counter() - parse_started
        loaded.append((BenchmarkCircuit(
            circuit_id=str(row["circuit_id"]),
            family=str(row["circuit_family"]),
            # Confirmatory extension manifests identify a generator mechanism
            # rather than the older, looser ``circuit_type`` label.  This is
            # metadata only: QASM bytes and the reconstructed circuit hash are
            # still verified above before any optimizer worker is started.
            circuit_type=str(row.get("circuit_type", row.get("mechanism_id", "unspecified"))),
            suite=str(row["suite"]),
            circuit=circuit,
            seed=int(row["seed"]),
            notes="" if pd.isna(row.get("notes")) else str(row.get("notes", "")),
        ), int(row["trial"]), int(row["seed"]), parse_elapsed))
    return loaded, manifest_sha


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

def _atomic_write_text(path: Path, text: str) -> None:
    """Write text to path atomically (tmp file + os.replace)."""
    import os
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _backup_if_exists(path: Path) -> Optional[Path]:
    """If path exists, copy it to path.with_suffix(path.suffix + '.bak-<ts>')."""
    import shutil
    if not path.exists():
        return None
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    bak = path.with_name(path.name + f".bak-{ts}")
    shutil.copy2(path, bak)
    return bak


def _preload_backend(fn: Callable) -> None:
    """Import backend dependencies before per-instance timing starts."""
    name = fn.__name__
    if name == "tket_optimize":
        import pytket.extensions.qiskit  # noqa: F401
        import pytket.passes  # noqa: F401
    elif name == "qiskit_optimize":
        from qiskit import transpile  # noqa: F401
    elif name == "cirq_optimize":
        import cirq  # noqa: F401
        import cirq.contrib.qasm_import  # noqa: F401
    elif name == "custom_optimize":
        import src.optimisation.phase1.greedy  # noqa: F401
        import src.optimisation.phase2.commutation_rewriter  # noqa: F401


def _persistent_worker(task_queue, result_queue, fn: Callable) -> None:
    """Long-lived isolated optimizer worker with internal tool-only timing."""
    try:
        _preload_backend(fn)
    except BaseException as exc:  # noqa: BLE001
        result_queue.put((-1, "startup_error", f"{type(exc).__name__}: {exc}", 0.0, 0.0))
        return
    while True:
        item = task_queue.get()
        if item is None:
            return
        task_id, args, kwargs = item
        started = time.perf_counter()
        cpu_started = time.process_time()
        try:
            payload = fn(*args, **kwargs)
            elapsed = time.perf_counter() - started
            cpu_elapsed = time.process_time() - cpu_started
            result_queue.put((task_id, "ok", payload, elapsed, cpu_elapsed))
        except BaseException as exc:  # noqa: BLE001
            elapsed = time.perf_counter() - started
            cpu_elapsed = time.process_time() - cpu_started
            result_queue.put((task_id, "error", f"{type(exc).__name__}: {exc}", elapsed, cpu_elapsed))


class PersistentOptimizerWorker:
    """A reusable worker that is restarted only after a true timeout/crash."""

    def __init__(self, fn: Callable):
        self.fn = fn
        self.ctx = mp.get_context("spawn")
        self.task_queue = None
        self.result_queue = None
        self.process = None
        self.next_task_id = 0
        self._start()

    def _start(self) -> None:
        self.task_queue = self.ctx.Queue(maxsize=1)
        self.result_queue = self.ctx.Queue(maxsize=1)
        self.process = self.ctx.Process(
            target=_persistent_worker,
            args=(self.task_queue, self.result_queue, self.fn),
        )
        self.process.start()

    def _terminate(self) -> None:
        if self.process is not None and self.process.is_alive():
            self.process.terminate()
            self.process.join(5)
            if self.process.is_alive():
                self.process.kill()
                self.process.join()
        if self.task_queue is not None:
            self.task_queue.close()
        if self.result_queue is not None:
            self.result_queue.close()

    def run(self, *args, timeout: float = DEFAULT_TIMEOUT_S, **kwargs):
        wall_start = time.perf_counter()
        if self.process is None or not self.process.is_alive():
            self._terminate()
            self._start()
        task_id = self.next_task_id
        self.next_task_id += 1
        self.task_queue.put((task_id, args, kwargs))
        peak_rss_bytes = float("nan")
        try:
            import psutil
            monitored = psutil.Process(self.process.pid)
        except Exception:  # noqa: BLE001 - instrumentation is optional
            monitored = None
        deadline = wall_start + timeout
        while True:
            if monitored is not None:
                try:
                    processes = [monitored, *monitored.children(recursive=True)]
                    rss = float(sum(proc.memory_info().rss for proc in processes if proc.is_running()))
                    peak_rss_bytes = rss if not np.isfinite(peak_rss_bytes) else max(peak_rss_bytes, rss)
                except Exception:  # noqa: BLE001
                    monitored = None
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                self._terminate()
                self._start()
                return (None, float("nan"), time.perf_counter() - wall_start,
                        "timeout", float("nan"), peak_rss_bytes)
            try:
                returned_id, kind, payload, tool_elapsed, cpu_elapsed = self.result_queue.get(
                    timeout=min(0.05, remaining))
                break
            except queue.Empty:
                continue
        wall_elapsed = time.perf_counter() - wall_start
        if returned_id == -1 and kind == "startup_error":
            self._terminate()
            return None, float("nan"), wall_elapsed, f"error: worker {payload}", float("nan"), peak_rss_bytes
        if returned_id != task_id:
            self._terminate()
            self._start()
            return None, float("nan"), wall_elapsed, "error: worker task-id mismatch", float("nan"), peak_rss_bytes
        if kind == "error":
            return None, tool_elapsed, wall_elapsed, f"error: {payload}", cpu_elapsed, peak_rss_bytes
        return payload, tool_elapsed, wall_elapsed, "ok", cpu_elapsed, peak_rss_bytes

    def close(self) -> None:
        if self.process is not None and self.process.is_alive():
            try:
                self.task_queue.put(None, timeout=1)
                self.process.join(5)
            except Exception:  # noqa: BLE001
                pass
        self._terminate()


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
    # Preserve implicit output-wire permutations; dropping them can produce a
    # circuit with excellent gate counts but a different unitary.
    return tk_to_qiskit(tk_circ, replace_implicit_swaps=True)


def qiskit_optimize(circuit, config: str = "default", seed: int = 42):
    """Qiskit transpile (fair mode: no coupling map).

    config selects the optimization level explicitly:
    "level0".."level3", or "default"/"tuned" (both map to level 3).
    """
    from qiskit import transpile
    level = QISKIT_LEVELS.get(config, 3)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return transpile(circuit, optimization_level=level, seed_transpiler=seed)


def cirq_optimize(circuit, config: str = "default"):
    """Cirq optimization pipeline.

    Pipeline (SOTA_BENCHMARK_PROTOCOL.md Sec. 4.1):
    drop_empty_moments -> drop_negligible_operations ->
    optimize_for_target_gateset(CZTargetGateset) -> eject_z ->
    merge_single_qubit_gates_to_phased_x_and_z -> drop_empty_moments.

    Fixes (2026-07-20, v1.1.0):
      * cirq 1.6.1 renamed the keyword to ``gateset=``; the previous
        ``target_gateset=`` call raised TypeError and was silently swallowed,
        so the CZTargetGateset step never ran in the 2026-07-18 data.
      * Cirq's QASM export emits ``sx``/``sxdg`` gates, which qiskit.qasm2's
        builtin qelib1 set does not define; explicit gate definitions are
        injected after the include line (identical to qiskit's qelib1.inc).
    """
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
        cirq_circ = optimize_for_target_gateset(cirq_circ, gateset=cirq.CZTargetGateset())
    except Exception:
        pass
    cirq_circ = eject_z(cirq_circ)
    cirq_circ = merge_single_qubit_gates_to_phased_x_and_z(cirq_circ)
    cirq_circ = drop_empty_moments(cirq_circ)
    # Cirq circuits do not retain idle qubits.  Add identities before QASM
    # export so the original register size and LineQubit indices survive, then
    # remove those identities from the loaded Qiskit circuit below.
    # QASM importer names the declared register qubits ``q_0``, ``q_1``, ... .
    # Using LineQubit here creates a second, disjoint register on export and
    # silently doubles the circuit width.  Reuse the importer's NamedQubit
    # identity so only genuinely idle declared wires are restored.
    for index in range(circuit.num_qubits):
        cirq_circ.append(cirq.I(cirq.NamedQubit(f"q_{index}")))
    qasm_out = cirq.qasm(cirq_circ)
    # Inject sx/sxdg definitions right after the qelib1 include so that
    # qiskit.qasm2.loads can resolve them.
    if "sx" in qasm_out and "gate sx " not in qasm_out:
        marker = 'include "qelib1.inc";'
        if marker in qasm_out:
            qasm_out = qasm_out.replace(marker, marker + "\n" + QASM2_SX_DEFS, 1)
        else:
            qasm_out = qasm_out.replace(
                "OPENQASM 2.0;", "OPENQASM 2.0;\n" + QASM2_SX_DEFS, 1)
    restored = qasm2_loads(qasm_out)
    restored.data = [inst for inst in restored.data if inst.operation.name != "id"]
    return restored


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
    runtime: float, wall_runtime: float, status: str, script_path: Path,
    manifest_sha256: str = "", common_orig_m: Optional[Dict[str, int]] = None,
    common_opt_m: Optional[Dict[str, int]] = None,
    normalization_status: str = "not_run",
    parse_elapsed_seconds: float = float("nan"),
    input_normalization_elapsed_seconds: float = float("nan"),
    verification_elapsed_seconds: float = float("nan"),
    output_normalization_elapsed_seconds: float = float("nan"),
    optimizer_cpu_seconds: float = float("nan"),
    optimizer_peak_rss_bytes: float = float("nan"),
    pipeline_elapsed_seconds: float = float("nan"),
) -> dict:
    """Build a single result row with the unified schema."""
    circuit = bench.circuit
    input_hash = circuit_sha256(circuit)
    output_hash = circuit_sha256(opt_circ) if opt_circ is not None else ""

    equivalent = fidelity is not None and np.isfinite(fidelity) and fidelity >= 1.0 - 1e-10
    valid_output = status == "ok" and equivalent and opt_m is not None
    native_reduction = reduction_pct(orig_m["gate_count"], opt_m["gate_count"]) if opt_m else 0.0
    common_reduction = (
        reduction_pct(common_orig_m["gate_count"], common_opt_m["gate_count"])
        if common_orig_m and common_opt_m else 0.0
    )
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
        "benchmark_manifest_sha256": manifest_sha256,
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
        "gate_reduction_pct": native_reduction,
        "t_count_reduction_pct": reduction_pct(orig_m["t_count"], opt_m["t_count"]) if opt_m else 0.0,
        "cnot_reduction_pct": reduction_pct(orig_m["cnot_count"], opt_m["cnot_count"]) if opt_m else 0.0,
        "depth_reduction_pct": reduction_pct(orig_m["depth"], opt_m["depth"]) if opt_m else 0.0,
        # Fidelity and status
        "fidelity": fidelity,
        "fidelity_source": "exact" if fidelity is not None and np.isfinite(fidelity) else "unavailable",
        "equivalence_status": "pass" if equivalent else ("fail" if fidelity is not None and np.isfinite(fidelity) else "unavailable"),
        "valid_equivalent_output": bool(valid_output),
        "analysis_gate_reduction_pct_itt": native_reduction if valid_output else 0.0,
        "common_basis": ",".join(COMMON_BASIS),
        "common_baseline_gate_count": common_orig_m["gate_count"] if common_orig_m else -1,
        "common_optimized_gate_count": common_opt_m["gate_count"] if common_opt_m else -1,
        "common_baseline_two_q_count": common_orig_m["two_q_count"] if common_orig_m else -1,
        "common_optimized_two_q_count": common_opt_m["two_q_count"] if common_opt_m else -1,
        "common_baseline_two_q_depth": common_orig_m["two_q_depth"] if common_orig_m else -1,
        "common_optimized_two_q_depth": common_opt_m["two_q_depth"] if common_opt_m else -1,
        "common_baseline_depth": common_orig_m["depth"] if common_orig_m else -1,
        "common_optimized_depth": common_opt_m["depth"] if common_opt_m else -1,
        "common_gate_reduction_pct": common_reduction,
        "analysis_common_gate_reduction_pct_itt": common_reduction if valid_output else 0.0,
        "normalization_status": normalization_status,
        "runtime_seconds": round(runtime, 6),
        "optimizer_elapsed_seconds": round(runtime, 6),
        "end_to_end_elapsed_seconds": round(wall_runtime, 6),
        "parse_elapsed_seconds": parse_elapsed_seconds,
        "input_normalization_elapsed_seconds": input_normalization_elapsed_seconds,
        "verification_elapsed_seconds": verification_elapsed_seconds,
        "output_normalization_elapsed_seconds": output_normalization_elapsed_seconds,
        # Filled after the row has actually been converted to its one-row CSV
        # representation.  Historical rows and callers that skip instrumentation
        # retain NaN rather than a fabricated zero.
        "result_serialization_elapsed_seconds": float("nan"),
        "pipeline_elapsed_seconds": pipeline_elapsed_seconds,
        "optimizer_cpu_seconds": optimizer_cpu_seconds,
        "optimizer_peak_rss_bytes": optimizer_peak_rss_bytes,
        "optimizer_peak_rss_method": (
            "sampled_process_tree_50ms" if np.isfinite(optimizer_peak_rss_bytes)
            else "unavailable"
        ),
        "timing_semantics_version": "1.1.0",
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
    families: Optional[List[str]] = None,
    target_qubits: Optional[set] = None,
    manifest_path: Optional[Path] = None,
    output_root: Optional[Path] = None,
    expected_manifest_rows: Optional[int] = None,
) -> pd.DataFrame:
    """Run a single tool on the 15-family benchmark."""
    available, version_or_err = check_tool_available(tool)
    if not available:
        print(f"Tool '{tool}' not available: {version_or_err}")
        return pd.DataFrame()

    if target_qubits is None:
        target_qubits = TARGET_QUBITS
    run_id = f"{tool}_{config}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
    script_path = Path(__file__).resolve()
    if output_root is None:
        output_root = PROJECT_ROOT / "data" / "v6" / "sota_benchmark"
    output_dir = output_root / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    meta_dir = output_root / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)

    opt_fn = TOOL_REGISTRY[tool]
    all_rows: List[dict] = []
    checkpoint_scope = hashlib.sha256(json.dumps({
        "manifest": file_sha256(manifest_path) if manifest_path else None,
        "families": sorted(families) if families else None,
        "target_qubits": sorted(target_qubits),
        "mode": mode,
        "n_trials": n_trials,
        "seed": seed,
        "expected_manifest_rows": expected_manifest_rows,
    }, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    checkpoint_path = output_dir / f"{tool}_{config}_{checkpoint_scope}_checkpoint.csv"
    if checkpoint_path.exists():
        checkpoint = pd.read_csv(checkpoint_path)
        if manifest_path is None or set(checkpoint.get("benchmark_manifest_sha256", [])) == {file_sha256(manifest_path)}:
            all_rows = checkpoint.to_dict(orient="records")
            print(f"Resuming {tool}/{config} from {len(all_rows)} checkpoint rows")
        else:
            raise RuntimeError(f"Checkpoint manifest mismatch: {checkpoint_path}")

    manifest_sha = ""
    if manifest_path is not None:
        work_items, manifest_sha = load_benchmark_manifest(manifest_path)
        expected_rows = expected_manifest_rows
        if expected_rows is None and mode == "full" and n_trials == 10:
            expected_rows = 520
        if expected_rows is not None and len(work_items) != expected_rows:
            raise RuntimeError(
                f"Expected {expected_rows} shared inputs, found {len(work_items)}"
            )
    else:
        work_items = []
        for trial in range(n_trials):
            trial_seed = seed + trial * 1000
            circuits = generate_extended_suite(mode=mode, seed=trial_seed)
            circuits = [b for b in circuits if b.circuit.num_qubits in target_qubits or
                        int(b.circuit_id.rsplit("_", 1)[-1]) in target_qubits]
            work_items.extend((bench, trial, trial_seed, float("nan")) for bench in circuits)

    if families:
        fam_set = {f.lower() for f in families}
        work_items = [item for item in work_items if item[0].family.lower() in fam_set]

    completed_keys = {
        (str(row["input_circuit_sha256"]), str(row["circuit_id"]),
         int(row["trial"]), int(row["seed"]))
        for row in all_rows
    }
    worker = PersistentOptimizerWorker(opt_fn)
    try:
        for item_index, (bench, trial, trial_seed, parse_elapsed) in enumerate(work_items, start=1):
            pipeline_started = time.perf_counter()
            circuit = bench.circuit
            item_key = (circuit_sha256(circuit), bench.circuit_id, trial, trial_seed)
            if item_key in completed_keys:
                continue
            orig_m = count_metrics(circuit)
            input_normalization_started = time.perf_counter()
            try:
                common_orig = normalize_to_common_basis(circuit, trial_seed)
                common_orig_m = count_metrics(common_orig)
            except Exception as exc:  # noqa: BLE001
                common_orig_m = None
                input_normalization_error = str(exc)
            else:
                input_normalization_error = ""
            input_normalization_elapsed = time.perf_counter() - input_normalization_started

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if tool == "qiskit":
                    opt_circ, runtime, wall_runtime, status, cpu_seconds, peak_rss_bytes = worker.run(
                        circuit, config=config, seed=trial_seed, timeout=timeout_s
                    )
                else:
                    opt_circ, runtime, wall_runtime, status, cpu_seconds, peak_rss_bytes = worker.run(
                        circuit, config=config, timeout=timeout_s
                    )

            verification_elapsed = float("nan")
            output_normalization_elapsed = float("nan")
            if status == "ok" and opt_circ is not None:
                opt_m = count_metrics(opt_circ)
                verification_started = time.perf_counter()
                fidelity = average_gate_fidelity(opt_circ, circuit, max_qubits=10)
                verification_elapsed = time.perf_counter() - verification_started
                output_normalization_started = time.perf_counter()
                try:
                    common_opt = normalize_to_common_basis(opt_circ, trial_seed)
                    common_opt_m = count_metrics(common_opt)
                    normalization_status = "ok" if not input_normalization_error else f"input_error: {input_normalization_error}"
                except Exception as exc:  # noqa: BLE001
                    common_opt_m = None
                    normalization_status = f"output_error: {exc}"
                output_normalization_elapsed = time.perf_counter() - output_normalization_started
            else:
                opt_m = None
                fidelity = None
                common_opt_m = None
                normalization_status = "not_run"

            row = build_row(
                tool=tool, tool_config=config, tool_version=version_or_err,
                run_id=run_id, bench=bench, trial=trial, seed=trial_seed,
                orig_m=orig_m, opt_circ=opt_circ, opt_m=opt_m,
                fidelity=fidelity, runtime=runtime, wall_runtime=wall_runtime, status=status,
                script_path=script_path,
                manifest_sha256=manifest_sha,
                common_orig_m=common_orig_m,
                common_opt_m=common_opt_m,
                normalization_status=normalization_status,
                parse_elapsed_seconds=parse_elapsed,
                input_normalization_elapsed_seconds=input_normalization_elapsed,
                verification_elapsed_seconds=verification_elapsed,
                output_normalization_elapsed_seconds=output_normalization_elapsed,
                optimizer_cpu_seconds=cpu_seconds,
                optimizer_peak_rss_bytes=peak_rss_bytes,
            )
            serialization_started = time.perf_counter()
            pd.DataFrame([row]).to_csv(index=False)
            row["result_serialization_elapsed_seconds"] = time.perf_counter() - serialization_started
            row["pipeline_elapsed_seconds"] = time.perf_counter() - pipeline_started
            all_rows.append(row)
            completed_keys.add(item_key)
            if len(all_rows) % 10 == 0 or item_index == len(work_items):
                _atomic_write_text(checkpoint_path, pd.DataFrame(all_rows).to_csv(index=False))
                print(f"  checkpoint {tool}/{config}: {len(all_rows)}/{len(work_items)}", flush=True)
    finally:
        worker.close()

    df = pd.DataFrame(all_rows)
    csv_path = output_dir / f"{run_id}.csv"
    _atomic_write_text(csv_path, df.to_csv(index=False))
    if checkpoint_path.exists():
        checkpoint_path.unlink()

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
        "families": families,
        "target_qubits": sorted(target_qubits),
        "benchmark_manifest": str(manifest_path) if manifest_path else None,
        "benchmark_manifest_sha256": manifest_sha or None,
        "expected_manifest_rows": expected_manifest_rows,
        "common_basis": COMMON_BASIS,
        "resource_instrumentation": {
            "timing_semantics_version": "1.1.0",
            "optimizer_cpu": "time.process_time inside isolated worker",
            "optimizer_peak_rss": "worker process tree sampled every 50 ms via psutil",
            "historical_missing_policy": "unavailable; never zero-imputed",
        },
        "canonical_data_file": csv_path.name,
        "n_rows": len(df),
        "n_ok": int((df["compiler_status"] == "ok").sum()),
        "n_timeouts": int((df["compiler_status"] == "timeout").sum()),
        "n_errors": int(df["compiler_status"].str.contains("error").sum()),
        "n_valid_equivalent_outputs": int(df["valid_equivalent_output"].sum()),
    })
    _atomic_write_text(meta_dir / f"{tool}_{config}_metadata.json",
                       json.dumps(metadata, indent=2, sort_keys=True))

    print(f"SOTA-BENCH [{tool}/{config}] complete: {len(df)} rows -> {csv_path}")
    print(f"  OK: {metadata['n_ok']}, Timeouts: {metadata['n_timeouts']}, "
          f"Errors: {metadata['n_errors']}")
    return df


# ---------------------------------------------------------------------------
# Aggregation with statistics
# ---------------------------------------------------------------------------

def aggregate_results() -> pd.DataFrame:
    """Aggregate canonical raw CSV files and compute statistics.

    Canonical selection: raw filenames are ``{tool}_{config}_{run_id}.csv``
    where run_id is a UTC timestamp; only the NEWEST file per (tool, config)
    is used, so superseded smoke/partial runs never double-count trials.
    """
    raw_dir = PROJECT_ROOT / "data" / "v6" / "sota_benchmark" / "raw"
    agg_dir = PROJECT_ROOT / "data" / "v6" / "sota_benchmark" / "aggregated"
    agg_dir.mkdir(parents=True, exist_ok=True)

    if not raw_dir.exists():
        print("No raw data found. Run benchmarks first.")
        return pd.DataFrame()

    # Select newest file per (tool, config).  Filename layout:
    # {tool}_{config}_{YYYYMMDD}_{HHMMSS}.csv where config may itself
    # contain underscores (e.g. "level0"); tool never does.
    by_key: Dict[Tuple[str, str], Path] = {}
    for csv_file in raw_dir.glob("*.csv"):
        parts = csv_file.stem.split("_")
        if len(parts) < 4:
            continue
        key = (parts[0], "_".join(parts[1:-2]))
        if key not in by_key or csv_file.name > by_key[key].name:
            by_key[key] = csv_file

    dfs = []
    for key, csv_file in sorted(by_key.items()):
        try:
            df = pd.read_csv(csv_file)
            dfs.append(df)
            print(f"  canonical[{key[0]}/{key[1]}]: {csv_file.name} ({len(df)} rows)")
        except Exception as e:
            print(f"  Skipping {csv_file.name}: {e}")

    if not dfs:
        print("No valid CSV files found.")
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    combined["tool_key"] = combined["tool"] + "/" + combined["tool_config"].astype(str)
    # Success rate per cell over ALL rows (including errors/timeouts)
    cell_total = combined.groupby(["tool_key", "circuit_family"]).size().rename("cell_rows")
    cell_ok = (combined[combined["compiler_status"] == "ok"]
               .groupby(["tool_key", "circuit_family"]).size().rename("cell_ok_rows"))
    # Only keep successful runs for metric aggregation
    ok = combined[combined["compiler_status"] == "ok"].copy()

    if ok.empty:
        print("No successful runs to aggregate.")
        return pd.DataFrame()

    # Per-family, per-(tool, config) aggregation (tool_key inherited from combined)
    agg_rows = []
    tool_keys = sorted(ok["tool_key"].unique())
    families = ok["circuit_family"].unique()
    custom_ok = ok[ok["tool"] == "custom"]

    for tool_key in tool_keys:
        tool_df = ok[ok["tool_key"] == tool_key]
        tool_name = str(tool_df["tool"].iloc[0])
        tool_cfg = str(tool_df["tool_config"].iloc[0])
        for family in families:
            fam_df = tool_df[tool_df["circuit_family"] == family]
            if fam_df.empty:
                continue
            # Get custom tool data for comparison (if custom exists)
            custom_df = custom_ok[custom_ok["circuit_family"] == family]
            tool_reductions = fam_df["gate_reduction_pct"].tolist()
            custom_reductions = custom_df["gate_reduction_pct"].tolist()

            # Statistical tests
            mw_p = None
            wilcox_p = None
            delta = None
            matched_rbc = None
            n_pairs = 0
            holm_sig = False

            if tool_name != "custom":
                try:
                    pair_keys = [
                        "input_circuit_sha256", "circuit_id", "trial", "seed"
                    ]
                    paired = fam_df[pair_keys + ["gate_reduction_pct"]].merge(
                        custom_df[pair_keys + ["gate_reduction_pct"]],
                        on=pair_keys,
                        how="inner",
                        validate="one_to_one",
                        suffixes=("_tool", "_custom"),
                    )
                    n_pairs = len(paired)
                    paired_tool = paired["gate_reduction_pct_tool"].to_numpy(dtype=float)
                    paired_custom = paired["gate_reduction_pct_custom"].to_numpy(dtype=float)
                    differences = (
                        paired_tool - paired_custom
                    )
                    if n_pairs >= 3:
                        # Secondary unpaired statistic, restricted to the same
                        # matched circuit set so width/family coverage cannot
                        # confound the comparison.
                        _, mw_p = stats.mannwhitneyu(
                            paired_tool, paired_custom, alternative="two-sided"
                        )
                        delta = cliffs_delta(paired_tool, paired_custom)
                    if n_pairs >= 3 and np.any(differences != 0):
                        _, wilcox_p = stats.wilcoxon(differences)
                        nonzero = differences[differences != 0]
                        ranks = stats.rankdata(np.abs(nonzero), method="average")
                        matched_rbc = float(
                            (ranks[nonzero > 0].sum() - ranks[nonzero < 0].sum())
                            / ranks.sum()
                        )
                    elif n_pairs >= 3:
                        wilcox_p = 1.0
                        matched_rbc = 0.0
                except Exception:
                    wilcox_p = None

            # Fidelity pass rate among rows with exact unitary comparison only
            exact_rows = fam_df[fam_df["fidelity_source"] == "exact"]
            fid_pass = (float((exact_rows["fidelity"] >= 0.999).mean())
                        if len(exact_rows) else None)
            # True success rate over all rows (ok + error + timeout) in the cell
            tot = int(cell_total.get((tool_key, family), len(fam_df)))
            ok_n = int(cell_ok.get((tool_key, family), len(fam_df)))

            agg_rows.append({
                "tool": tool_name,
                "tool_config": tool_cfg,
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
                "median_runtime_seconds": round(float(fam_df["runtime_seconds"].median()), 6),
                "n_cell_rows": tot,
                "success_rate": round(ok_n / tot, 4) if tot else None,
                "fidelity_pass_rate": round(fid_pass, 4) if fid_pass is not None else None,
                "fidelity_exact_rate": round(
                    float((fam_df["fidelity_source"] == "exact").mean()), 4),
                "mann_whitney_p_vs_custom": mw_p,
                "wilcoxon_p_vs_custom": wilcox_p,
                "cliffs_delta_vs_custom": round(delta, 4) if delta is not None else None,
                "n_pairs_vs_custom": n_pairs,
                "matched_rank_biserial_vs_custom": (
                    round(matched_rbc, 4) if matched_rbc is not None else None
                ),
                "holm_significant": holm_sig,
                "holm_alpha": None,
                "holm_adjusted_p": None,
            })

    agg_df = pd.DataFrame(agg_rows)
    # Primary inference is paired Wilcoxon. Apply the actual Holm step-down
    # procedure across every available tool/config/family comparison.
    valid = agg_df["wilcoxon_p_vs_custom"].notna()
    if valid.any():
        indices = agg_df.index[valid].to_numpy()
        pvalues = agg_df.loc[indices, "wilcoxon_p_vs_custom"].to_numpy(dtype=float)
        order = np.argsort(pvalues)
        m = len(pvalues)
        sorted_p = pvalues[order]
        adjusted = np.maximum.accumulate(sorted_p * (m - np.arange(m)))
        adjusted = np.minimum(adjusted, 1.0)
        for rank, position in enumerate(order):
            row_index = indices[position]
            threshold = 0.05 / (m - rank)
            agg_df.at[row_index, "holm_alpha"] = threshold
            agg_df.at[row_index, "holm_adjusted_p"] = adjusted[rank]
            agg_df.at[row_index, "holm_significant"] = bool(adjusted[rank] < 0.05)
    agg_csv = agg_dir / "sota_comparison_aggregated.csv"
    bak = _backup_if_exists(agg_csv)
    if bak:
        print(f"  backup: {bak.name}")
    _atomic_write_text(agg_csv, agg_df.to_csv(index=False))
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
                        help="Aggregate canonical raw CSVs and compute statistics")
    parser.add_argument("--families", nargs="*", default=None,
                        help="Optional family filter, e.g. --families QFT QuantumWalk")
    parser.add_argument("--target-qubits", type=int, nargs="*", default=None,
                        help="Optional qubit-count filter, e.g. --target-qubits 3 4")
    parser.add_argument("--prepare-manifest", action="store_true",
                        help="Materialize and verify the immutable shared input set")
    parser.add_argument("--manifest", type=Path, default=None,
                        help="Shared benchmark manifest; required for confirmatory runs")
    parser.add_argument("--output-root", type=Path, default=None,
                        help="Versioned output root (confirmatory default: data/v10/prepaper/sota)")
    parser.add_argument("--expected-manifest-rows", type=int, default=None,
                        help="Required manifest cardinality (e.g. 240 for sealed held-out)")
    args = parser.parse_args()

    output_root = args.output_root.resolve() if args.output_root else None
    if args.prepare_manifest:
        prepare_benchmark_manifest(
            mode=args.mode, n_trials=args.n_trials, seed=args.seed,
            target_qubits=set(args.target_qubits) if args.target_qubits else None,
            output_root=output_root or PREPAPER_ROOT,
        )
        return

    if args.aggregate:
        aggregate_results()
        return

    tq = set(args.target_qubits) if args.target_qubits else None
    if args.tool == "all":
        for tool in TOOL_REGISTRY:
            available, _ = check_tool_available(tool)
            if available:
                run_tool(tool, config=args.config, mode=args.mode,
                         n_trials=args.n_trials, seed=args.seed,
                         timeout_s=args.timeout, families=args.families,
                         target_qubits=tq, manifest_path=args.manifest,
                         output_root=output_root,
                         expected_manifest_rows=args.expected_manifest_rows)
            else:
                print(f"Skipping {tool}: not available")
        # Auto-aggregate after all runs
        aggregate_results()
    else:
        run_tool(args.tool, config=args.config, mode=args.mode,
                 n_trials=args.n_trials, seed=args.seed,
                 timeout_s=args.timeout, families=args.families,
                 target_qubits=tq, manifest_path=args.manifest,
                 output_root=output_root,
                 expected_manifest_rows=args.expected_manifest_rows)


if __name__ == "__main__":
    main()
