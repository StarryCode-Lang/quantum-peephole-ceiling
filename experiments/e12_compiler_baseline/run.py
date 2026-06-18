"""E12: Qiskit compiler baseline comparison.

Runs Qiskit transpiler optimization levels 0-3 on the same real-circuit suite used by E11.
v4.1.0 fix: Added coupling_map (heavy-hex d=3) and basis_gates to differentiate L1/L2/L3.
Without a backend/coupling_map, Qiskit skips layout and routing, making L1-L3 bit-identical.
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
VERSION = "4.1.0"

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
    # Scale up: find smallest heavy-hex distance that fits n_qubits.
    for d in range(heavy_hex_d + 1, heavy_hex_d + 6):
        cmap = CouplingMap.from_heavy_hex(d)
        if cmap.size() >= n_qubits:
            return cmap
    # Last resort: return the largest we tried.
    return cmap


def run(mode: str, seed: int, max_qubits_fidelity: int,
        heavy_hex_d: int = DEFAULT_HEAVY_HEX_D) -> pd.DataFrame:
    """Run Qiskit transpiler baselines and return results."""
    run_id = f"e12_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
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
        # Dynamically select coupling map sized to this circuit.
        coupling_map = _select_coupling_map(circuit.num_qubits, heavy_hex_d)
        for level in [0, 1, 2, 3]:
            start = time.time()
            error = ""
            compiled = None
            try:
                compiled = transpile(
                    circuit,
                    coupling_map=coupling_map,
                    basis_gates=BASIS_GATES,
                    optimization_level=level,
                    seed_transpiler=seed,
                )
                runtime = time.time() - start
                optimized_gate_count = int(compiled.size())
                reduction = 1.0 - optimized_gate_count / baseline_gate_count if baseline_gate_count else 0.0
                fidelity = average_gate_fidelity(compiled, circuit, max_qubits=max_qubits_fidelity)
                success = bool(fidelity is not None and fidelity >= 0.999)
                output_hash = circuit_sha256(compiled)
                compiled_counts = gate_counts(compiled)
            except Exception as exc:  # record compiler failures as data, not crashes
                runtime = time.time() - start
                optimized_gate_count = -1
                reduction = 0.0
                fidelity = None
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
            "coupling_map": f"heavy_hex_d{heavy_hex_d}_dynamic",
            "coupling_map_base_d": heavy_hex_d,
            "coupling_map_selection": "dynamic_per_circuit",
            "basis_gates": BASIS_GATES,
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
    args = parser.parse_args()
    run(mode=args.mode, seed=args.seed, max_qubits_fidelity=args.max_qubits_fidelity,
        heavy_hex_d=args.heavy_hex_d)


if __name__ == "__main__":
    main()
