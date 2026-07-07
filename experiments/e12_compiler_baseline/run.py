"""E12: Qiskit compiler baseline comparison.

Runs Qiskit transpiler optimization levels 0-3 on the same real-circuit suite used by E11.
v4.1.0 fix: Added coupling_map (heavy-hex d=3) and basis_gates to differentiate L1/L2/L3.
Without a backend/coupling_map, Qiskit skips layout and routing, making L1-L3 bit-identical.

v4.2.0 fix (review H1/F3): Added ``--no-coupling-map`` mode for a *fair* comparison.
The default coupling_map forces Qiskit to solve routing + optimization, while the
custom peephole optimizer only does optimization (no routing).  This makes Qiskit's
baseline artificially worse.  The ``--no-coupling-map`` mode runs Qiskit without a
coupling map so both optimizers solve only the optimization problem, enabling an
apples-to-apples comparison.  Run BOTH modes and report them separately.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd
import qiskit
from qiskit import transpile
from qiskit.transpiler import CouplingMap

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import (  # noqa: E402
    average_gate_fidelity,
    circuit_sha256,
    gate_counts,
    generate_real_circuit_suite,
)
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "1.0.0"
EXPERIMENT_ID = "E12"
VERSION = "4.2.1"

# Review L6 note: the ``fidelity`` column in E12 output is often NULL
# for large circuits (n > max_qubits_fidelity) because Qiskit's
# transpiled circuit uses a different basis gate set than the input,
# making exact unitary comparison infeasible.  The ``fidelity_source``
# column (added in v4.2.1) records WHY:
#   "exact"        — unitary comparison succeeded (n <= max_qubits_fidelity)
#   "unavailable"  — n > max_qubits_fidelity or qubit count mismatch
#   "error"        — compiler exception, fidelity not computed
# Consumers should filter on fidelity_source == "exact" for reliable
# fidelity values.

# Default heavy-hex distance and basis gates for fair compiler comparison.
# The coupling map is now selected dynamically based on circuit size
# (see _select_coupling_map) instead of a fixed 19-qubit map that
# over-constrains small circuits and cannot fit large ones.
DEFAULT_HEAVY_HEX_D = 3
BASIS_GATES = ["cx", "id", "rz", "sx", "x"]
COMPILER_CONFIG_ID = "qiskit_heavy_hex"


def _select_coupling_map(n_qubits: int, heavy_hex_d: int = DEFAULT_HEAVY_HEX_D) -> CouplingMap:
    """Select an appropriate coupling map for the given circuit size.

    Uses the requested heavy-hex distance if it provides enough qubits;
    otherwise scales up to the smallest distance that fits.  Falls back
    to a linear chain for very small circuits (n <= 2).
    """
    if n_qubits <= 2:
        return CouplingMap([[0, 1]])
    cmap = CouplingMap.from_heavy_hex(heavy_hex_d)
    if cmap.size() >= n_qubits:
        return cmap
    # Scale up: find smallest odd heavy-hex distance that fits n_qubits.
    # Qiskit requires d to be odd; start from next odd and step by 2.
    start_d = heavy_hex_d + 1 if heavy_hex_d % 2 == 0 else heavy_hex_d + 2
    for d in range(start_d, start_d + 10, 2):
        cmap = CouplingMap.from_heavy_hex(d)
        if cmap.size() >= n_qubits:
            return cmap
    # Last resort: return the largest we tried.
    return cmap


def run(mode: str, seed: int, max_qubits_fidelity: int,
        heavy_hex_d: int = DEFAULT_HEAVY_HEX_D,
        no_coupling_map: bool = False) -> pd.DataFrame:
    """Run Qiskit transpiler baselines and return results.

    When ``no_coupling_map=True`` (review H1/F3), Qiskit runs WITHOUT a coupling
    map so that it solves only the gate-optimization problem — matching the
    scope of the custom peephole optimizer (which does no routing).  This
    produces a fair comparison.  The default (``no_coupling_map=False``) keeps
    the routing-aware baseline for hardware-realism reporting.
    """
    run_id = f"e12_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    if no_coupling_map:
        run_id += "_nocoupling"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v4" / "e12"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    circuits = generate_real_circuit_suite(mode=mode, seed=seed)
    rows: List[dict] = []

    for trial, bench in enumerate(circuits):
        circuit = bench.circuit
        input_hash = circuit_sha256(circuit)
        counts = gate_counts(circuit)
        baseline_gate_count = int(circuit.size())
        # Only select a coupling map when not in no-coupling mode.
        coupling_map = None if no_coupling_map else _select_coupling_map(circuit.num_qubits, heavy_hex_d)
        for level in [0, 1, 2, 3]:
            start = time.time()
            error = ""
            compiled = None
            try:
                transpile_kwargs = dict(
                    optimization_level=level,
                    seed_transpiler=seed,
                )
                if coupling_map is not None:
                    transpile_kwargs["coupling_map"] = coupling_map
                    transpile_kwargs["basis_gates"] = BASIS_GATES
                compiled = transpile(circuit, **transpile_kwargs)
                runtime = time.time() - start
                optimized_gate_count = int(compiled.size())
                reduction = 1.0 - optimized_gate_count / baseline_gate_count if baseline_gate_count else 0.0
                fidelity = average_gate_fidelity(compiled, circuit, max_qubits=max_qubits_fidelity)
                fidelity_source = "exact" if fidelity is not None else "unavailable"
                success = bool(fidelity is not None and fidelity >= 0.999)
                output_hash = circuit_sha256(compiled)
                compiled_counts = gate_counts(compiled)
            except Exception as exc:  # record compiler failures as data, not crashes
                runtime = time.time() - start
                optimized_gate_count = -1
                reduction = 0.0
                fidelity = None
                fidelity_source = "error"
                success = False
                output_hash = ""
                compiled_counts = {
                    "gate_count_total": -1,
                    "depth": -1,
                    "gate_count_1q": -1,
                    "gate_count_2q": -1,
                    "gate_count_multiq": -1,
                    "gate_counts_json": "{}",
                }
                error = repr(exc)

            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "circuit_id": bench.circuit_id,
                    "circuit_family": bench.family,
                    "circuit_type": bench.circuit_type,
                    "benchmark_suite": bench.suite,
                    "n_qubits": circuit.num_qubits,
                    "depth": counts["depth"],
                    "gate_count_total": counts["gate_count_total"],
                    "gate_count_1q": counts["gate_count_1q"],
                    "gate_count_2q": counts["gate_count_2q"],
                    "gate_count_multiq": counts["gate_count_multiq"],
                    "gate_counts_json": counts["gate_counts_json"],
                    "compiled_depth": compiled_counts["depth"],
                    "compiled_gate_counts_json": compiled_counts["gate_counts_json"],
                    "baseline_gate_count": baseline_gate_count,
                    "optimized_gate_count": optimized_gate_count,
                    "reduction": reduction,
                    "reduction_pct": 100.0 * reduction,
                    "fidelity": fidelity,
                    "fidelity_source": fidelity_source,
                    "success": success,
                    "runtime_seconds": runtime,
                    "optimizer": "none",
                    "optimizer_version": "none",
                    "optimizer_config_json": "{}",
                    "compiler": "qiskit_transpile",
                    "compiler_version": qiskit.__version__,
                    "compiler_optimization_level": level,
                    "compiler_config_id": COMPILER_CONFIG_ID,
                    "seed": seed,
                    "trial": trial,
                    "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                    "source_sha256": file_sha256(script_path),
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": output_hash,
                    "env_id": run_id,
                    "notes": error,
                }
            )

    df = pd.DataFrame(rows)
    csv_path = output_dir / f"e12_compiler_baseline_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata.update(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "description": "Qiskit transpiler compiler baseline comparison",
            "mode": mode,
            "seed": seed,
            "max_qubits_fidelity": max_qubits_fidelity,
            "canonical_data_file": csv_path.name,
            "n_input_circuits": len(circuits),
            "n_rows": len(df),
            "compiler": "qiskit_transpile",
            "compiler_version": qiskit.__version__,
            "optimization_levels": [0, 1, 2, 3],
            "compiler_config_id": COMPILER_CONFIG_ID,
            "coupling_map": "none" if no_coupling_map else f"heavy_hex_d{heavy_hex_d}_dynamic",
            "coupling_map_base_d": heavy_hex_d,
            "coupling_map_selection": "none" if no_coupling_map else "dynamic_per_circuit",
            "no_coupling_map": no_coupling_map,
            "fairness_note": (
                "no_coupling_map=True: Qiskit solves optimization only (no routing), "
                "matching the scope of the custom peephole optimizer. This is the "
                "FAIR comparison mode (review H1/F3)."
            ) if no_coupling_map else (
                "no_coupling_map=False: Qiskit solves routing + optimization, which "
                "is harder than the custom optimizer's optimization-only scope. "
                "Use the no_coupling_map=True run for fair comparison."
            ),
            "basis_gates": BASIS_GATES if not no_coupling_map else "none (native gate set)",
        }
    )
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"E12 complete: {len(df)} rows -> {csv_path}")
    print(df.groupby(["circuit_family", "compiler_optimization_level"])["reduction"].mean().to_string())
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E12 Qiskit compiler baseline")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-qubits-fidelity", type=int, default=10)
    parser.add_argument("--heavy-hex-d", type=int, default=DEFAULT_HEAVY_HEX_D,
                        help="Base heavy-hex coupling map distance (default: 3)")
    parser.add_argument("--no-coupling-map", action="store_true",
                        help="Run Qiskit WITHOUT a coupling map (fair comparison mode, review H1/F3)")
    parser.add_argument("--both", action="store_true",
                        help="Run BOTH coupling-map and no-coupling-map modes and save separately")
    args = parser.parse_args()

    if args.both:
        # Run hardware-realistic (with coupling) first, then fair (without).
        run(mode=args.mode, seed=args.seed, max_qubits_fidelity=args.max_qubits_fidelity,
            heavy_hex_d=args.heavy_hex_d, no_coupling_map=False)
        run(mode=args.mode, seed=args.seed, max_qubits_fidelity=args.max_qubits_fidelity,
            heavy_hex_d=args.heavy_hex_d, no_coupling_map=True)
    else:
        run(mode=args.mode, seed=args.seed, max_qubits_fidelity=args.max_qubits_fidelity,
            heavy_hex_d=args.heavy_hex_d, no_coupling_map=args.no_coupling_map)


if __name__ == "__main__":
    main()
