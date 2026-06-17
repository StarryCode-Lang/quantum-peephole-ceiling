"""E15: Multi-compiler baseline comparison.

Compares our peephole optimizers against Qiskit transpiler (opt levels 0-3),
and optionally Cirq and t|ket> compilers, on the extended benchmark suite.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase2.commutation_rewriter import (  # noqa: E402
    CommutationRewriter,
    HybridCommuteRewrite,
)
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "2.0.0"
EXPERIMENT_ID = "E15"
VERSION = "5.0.0"


def _safe_ratio(o, p):
    """Safe ratio computation: 1 - p/o, or 0.0 if o==0."""
    return 1.0 - p / o if o > 0 else 0.0


# ---------------------------------------------------------------------------
# Compiler backends (graceful degradation when optional deps are missing)
# ---------------------------------------------------------------------------

def _qiskit_transpile(circuit, opt_level: int):
    """Run Qiskit transpiler at a given optimization level."""
    from qiskit import transpile
    start = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        optimized = transpile(circuit, optimization_level=opt_level, seed_transpiler=42)
    runtime = time.time() - start
    return optimized, runtime


def _cirq_optimize(circuit):
    """Convert to Cirq, apply built-in optimizers, convert back."""
    try:
        import cirq
        from qiskit import QuantumCircuit
    except ImportError:
        return None, 0.0, "cirq_not_installed"

    try:
        from qiskit.circuit import QuantumCircuit as QC
        # Qiskit -> OpenQASM2 -> Cirq
        from qiskit.qasm2 import dumps as qasm2_dumps
        qasm_str = qasm2_dumps(circuit)

        # Convert via Cirq's QASM parser
        from cirq.contrib.qasm_import import circuit_from_qasm
        cirq_circ = circuit_from_qasm(qasm_str)

        start = time.time()
        # Apply Cirq's built-in optimization passes
        from cirq.transformers import (
            drop_empty_moments,
            drop_negligible_operations,
            merge_single_qubit_gates_to_phased_x_and_z,
        )
        cirq_circ = drop_empty_moments(cirq_circ)
        cirq_circ = drop_negligible_operations(cirq_circ)
        cirq_circ = merge_single_qubit_gates_to_phased_x_and_z(cirq_circ)
        cirq_circ = drop_empty_moments(cirq_circ)
        runtime = time.time() - start

        # Convert back to Qiskit via QASM2
        from qiskit.qasm2 import loads as qasm2_loads
        qasm_out = cirq.qasm(cirq_circ)
        qc_back = qasm2_loads(qasm_out)
        return qc_back, runtime, "ok"
    except Exception as exc:
        return None, 0.0, str(exc)


def _tket_optimize(circuit):
    """Convert to t|ket>, apply optimization, convert back."""
    try:
        from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
        from pytket.passes import (
            FullPeepholeOptimise,
            SequencePass,
            DecomposeBoxes,
        )
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


def _count_metrics(circuit) -> Dict[str, float]:
    """Count depth, 2Q gates, CNOT for a circuit."""
    depth = int(circuit.depth() or 0)
    two_q = sum(1 for inst in circuit.data if inst.operation.num_qubits == 2)
    cnot = sum(1 for inst in circuit.data if inst.operation.name in ('cx', 'cnot'))
    return {"depth": depth, "two_q": two_q, "cnot": cnot}


# ---------------------------------------------------------------------------
# Main experiment runner
# ---------------------------------------------------------------------------

def run(mode: str, seed: int, max_qubits_fidelity: int,
        skip_cirq: bool = False, skip_tket: bool = False) -> pd.DataFrame:
    """Run E15 and return the result table."""
    run_id = f"e15_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v5" / "e15"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    circuits = generate_extended_suite(mode=mode, seed=seed)

    # Our optimizers
    our_optimizers = {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "commutation_phase2": CommutationRewriter(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }

    rows: List[dict] = []
    for trial, bench in enumerate(circuits):
        circuit = bench.circuit
        input_hash = circuit_sha256(circuit)
        counts = gate_counts(circuit)
        orig_m = _count_metrics(circuit)

        # --- Our optimizers ---
        for opt_name, opt in our_optimizers.items():
            start = time.time()
            result = opt.optimize(circuit, target=circuit)
            runtime = time.time() - start
            output_hash = circuit_sha256(result.optimized_circuit)
            opt_m = _count_metrics(result.optimized_circuit)
            fidelity = result.fidelity
            if fidelity is None or fidelity == 0.0:
                exact = average_gate_fidelity(
                    result.optimized_circuit, circuit,
                    max_qubits=max_qubits_fidelity,
                )
                fidelity = exact if exact is not None else result.fidelity

            rows.append({
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "circuit_id": bench.circuit_id,
                "circuit_family": bench.family,
                "n_qubits": circuit.num_qubits,
                "baseline_gate_count": result.original_size,
                "optimized_gate_count": result.optimized_size,
                "reduction": result.reduction,
                "reduction_pct": 100.0 * result.reduction,
                "depth_reduction": _safe_ratio(orig_m["depth"], opt_m["depth"]),
                "two_qubit_reduction": _safe_ratio(orig_m["two_q"], opt_m["two_q"]),
                "cnot_reduction": _safe_ratio(orig_m["cnot"], opt_m["cnot"]),
                "fidelity": fidelity,
                "runtime_seconds": runtime,
                "compiler": "custom",
                "compiler_backend": opt_name,
                "compiler_opt_level": "none",
                "compiler_status": "ok",
                "seed": bench.seed,
                "trial": trial,
                "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                "source_sha256": file_sha256(script_path),
                "input_circuit_sha256": input_hash,
                "output_circuit_sha256": output_hash,
                "notes": bench.notes,
            })

        # --- Qiskit transpiler (opt levels 0-3) ---
        for level in [0, 1, 2, 3]:
            opt_circ, runtime = _qiskit_transpile(circuit, level)
            opt_m = _count_metrics(opt_circ)
            output_hash = circuit_sha256(opt_circ)
            fidelity = average_gate_fidelity(opt_circ, circuit,
                                              max_qubits=max_qubits_fidelity)

            rows.append({
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "circuit_id": bench.circuit_id,
                "circuit_family": bench.family,
                "n_qubits": circuit.num_qubits,
                "baseline_gate_count": circuit.size(),
                "optimized_gate_count": opt_circ.size(),
                "reduction": 1.0 - opt_circ.size() / circuit.size() if circuit.size() > 0 else 0.0,
                "reduction_pct": 100.0 * (1.0 - opt_circ.size() / circuit.size()) if circuit.size() > 0 else 0.0,
                "depth_reduction": _safe_ratio(orig_m["depth"], opt_m["depth"]),
                "two_qubit_reduction": _safe_ratio(orig_m["two_q"], opt_m["two_q"]),
                "cnot_reduction": _safe_ratio(orig_m["cnot"], opt_m["cnot"]),
                "fidelity": fidelity,
                "runtime_seconds": runtime,
                "compiler": "qiskit",
                "compiler_backend": "transpiler",
                "compiler_opt_level": level,
                "compiler_status": "ok",
                "seed": bench.seed,
                "trial": trial,
                "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                "source_sha256": file_sha256(script_path),
                "input_circuit_sha256": input_hash,
                "output_circuit_sha256": output_hash,
                "notes": bench.notes,
            })

        # --- Cirq optimizer ---
        if not skip_cirq:
            opt_circ, runtime, status = _cirq_optimize(circuit)
            if opt_circ is not None:
                opt_m = _count_metrics(opt_circ)
                output_hash = circuit_sha256(opt_circ)
                fidelity = average_gate_fidelity(opt_circ, circuit,
                                                  max_qubits=max_qubits_fidelity)

                rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "circuit_id": bench.circuit_id,
                    "circuit_family": bench.family,
                    "n_qubits": circuit.num_qubits,
                    "baseline_gate_count": circuit.size(),
                    "optimized_gate_count": opt_circ.size(),
                    "reduction": 1.0 - opt_circ.size() / circuit.size() if circuit.size() > 0 else 0.0,
                    "reduction_pct": 100.0 * (1.0 - opt_circ.size() / circuit.size()) if circuit.size() > 0 else 0.0,
                    "depth_reduction": _safe_ratio(orig_m["depth"], opt_m["depth"]),
                    "two_qubit_reduction": _safe_ratio(orig_m["two_q"], opt_m["two_q"]),
                    "cnot_reduction": _safe_ratio(orig_m["cnot"], opt_m["cnot"]),
                    "fidelity": fidelity,
                    "runtime_seconds": runtime,
                    "compiler": "cirq",
                    "compiler_backend": "built_in_optimizers",
                    "compiler_opt_level": "default",
                    "compiler_status": status,
                    "seed": bench.seed,
                    "trial": trial,
                    "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                    "source_sha256": file_sha256(script_path),
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": output_hash,
                    "notes": bench.notes,
                })
            else:
                rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "circuit_id": bench.circuit_id,
                    "circuit_family": bench.family,
                    "n_qubits": circuit.num_qubits,
                    "baseline_gate_count": circuit.size(),
                    "optimized_gate_count": None,
                    "reduction": None,
                    "reduction_pct": None,
                    "depth_reduction": None,
                    "two_qubit_reduction": None,
                    "cnot_reduction": None,
                    "fidelity": None,
                    "runtime_seconds": 0.0,
                    "compiler": "cirq",
                    "compiler_backend": "built_in_optimizers",
                    "compiler_opt_level": "default",
                    "compiler_status": status,
                    "seed": bench.seed,
                    "trial": trial,
                    "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                    "source_sha256": file_sha256(script_path),
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": "none",
                    "notes": bench.notes,
                })

        # --- t|ket> optimizer ---
        if not skip_tket:
            opt_circ, runtime, status = _tket_optimize(circuit)
            if opt_circ is not None:
                opt_m = _count_metrics(opt_circ)
                output_hash = circuit_sha256(opt_circ)
                fidelity = average_gate_fidelity(opt_circ, circuit,
                                                  max_qubits=max_qubits_fidelity)

                rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "circuit_id": bench.circuit_id,
                    "circuit_family": bench.family,
                    "n_qubits": circuit.num_qubits,
                    "baseline_gate_count": circuit.size(),
                    "optimized_gate_count": opt_circ.size(),
                    "reduction": 1.0 - opt_circ.size() / circuit.size() if circuit.size() > 0 else 0.0,
                    "reduction_pct": 100.0 * (1.0 - opt_circ.size() / circuit.size()) if circuit.size() > 0 else 0.0,
                    "depth_reduction": _safe_ratio(orig_m["depth"], opt_m["depth"]),
                    "two_qubit_reduction": _safe_ratio(orig_m["two_q"], opt_m["two_q"]),
                    "cnot_reduction": _safe_ratio(orig_m["cnot"], opt_m["cnot"]),
                    "fidelity": fidelity,
                    "runtime_seconds": runtime,
                    "compiler": "tket",
                    "compiler_backend": "FullPeepholeOptimise",
                    "compiler_opt_level": "default",
                    "compiler_status": status,
                    "seed": bench.seed,
                    "trial": trial,
                    "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                    "source_sha256": file_sha256(script_path),
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": output_hash,
                    "notes": bench.notes,
                })
            else:
                rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "circuit_id": bench.circuit_id,
                    "circuit_family": bench.family,
                    "n_qubits": circuit.num_qubits,
                    "baseline_gate_count": circuit.size(),
                    "optimized_gate_count": None,
                    "reduction": None,
                    "reduction_pct": None,
                    "depth_reduction": None,
                    "two_qubit_reduction": None,
                    "cnot_reduction": None,
                    "fidelity": None,
                    "runtime_seconds": 0.0,
                    "compiler": "tket",
                    "compiler_backend": "FullPeepholeOptimise",
                    "compiler_opt_level": "default",
                    "compiler_status": status,
                    "seed": bench.seed,
                    "trial": trial,
                    "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                    "source_sha256": file_sha256(script_path),
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": "none",
                    "notes": bench.notes,
                })

    df = pd.DataFrame(rows)
    csv_path = output_dir / f"e15_multi_compiler_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata.update(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "description": "Multi-compiler baseline comparison (Qiskit, Cirq, t|ket>)",
            "mode": mode,
            "seed": seed,
            "max_qubits_fidelity": max_qubits_fidelity,
            "skip_cirq": skip_cirq,
            "skip_tket": skip_tket,
            "canonical_data_file": csv_path.name,
            "n_input_circuits": len(circuits),
            "n_rows": len(df),
            "compilers": ["custom", "qiskit"] + (["cirq"] if not skip_cirq else []) + (["tket"] if not skip_tket else []),
            "circuit_families": sorted({bench.family for bench in circuits}),
        }
    )
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"E15 complete: {len(df)} rows -> {csv_path}")
    summary = (
        df.dropna(subset=["reduction"])
        .groupby(["compiler", "compiler_backend"])
        .agg({"reduction": "mean", "depth_reduction": "mean", "cnot_reduction": "mean"})
    )
    print(summary.to_string())
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E15 multi-compiler baseline")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-qubits-fidelity", type=int, default=10)
    parser.add_argument("--skip-cirq", action="store_true", help="Skip Cirq backend")
    parser.add_argument("--skip-tket", action="store_true", help="Skip t|ket> backend")
    args = parser.parse_args()
    run(mode=args.mode, seed=args.seed, max_qubits_fidelity=args.max_qubits_fidelity,
        skip_cirq=args.skip_cirq, skip_tket=args.skip_tket)


if __name__ == "__main__":
    main()
