#!/usr/bin/env python3
"""Calibrate sampled fidelity fallback against exact average gate fidelity.

The calibration deliberately includes local and entangling mismatches.  A
product-state sampler can look accurate on some global circuit differences
while badly overestimating a local error; global Haar states are the required
Monte Carlo reference for average gate fidelity.

Usage:
    python scripts/characterize_fidelity_fallback.py
    python scripts/characterize_fidelity_fallback.py --n-values 3 5 8 --samples 1000
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from qiskit import QuantumCircuit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.optimisation.base import BaseOptimizer, OptimizationResult


class _CalibrationOptimizer(BaseOptimizer):
    """Concrete shell exposing shared fidelity methods for calibration."""

    def optimize(self, circuit: QuantumCircuit, target: QuantumCircuit | None = None) -> OptimizationResult:
        return OptimizationResult(
            optimized_circuit=circuit.copy(),
            original_size=circuit.size(),
            optimized_size=circuit.size(),
            fidelity=1.0,
            iterations=0,
            runtime_seconds=0.0,
            success=True,
        )


def make_case(n_qubits: int, case: str) -> tuple[QuantumCircuit, QuantumCircuit]:
    """Return a circuit/target pair with a known mismatch pattern."""
    circuit = QuantumCircuit(n_qubits)
    target = QuantumCircuit(n_qubits)
    if case == "local_x":
        circuit.x(0)
    elif case == "entangling_cx":
        circuit.cx(0, 1)
    else:
        raise ValueError(f"unknown case: {case}")
    return circuit, target


def run(n_values: list[int], samples: int, seed: int) -> list[dict[str, float | int | str]]:
    """Run exact-vs-sampled calibration rows."""
    rows: list[dict[str, float | int | str]] = []
    for n_qubits in n_values:
        for case in ("local_x", "entangling_cx"):
            circuit, target = make_case(n_qubits, case)
            optimizer = _CalibrationOptimizer(random_seed=seed + n_qubits)
            exact = optimizer.calculate_fidelity(circuit, target)
            estimate = optimizer._estimate_fidelity(circuit, target, n_samples=samples)
            rows.append({
                "n_qubits": n_qubits,
                "case": case,
                "samples": samples,
                "seed": seed + n_qubits,
                "exact_fidelity": exact,
                "estimated_fidelity": estimate,
                "absolute_error": abs(estimate - exact),
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-values", nargs="+", type=int, default=[3, 5, 8])
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/verification"))
    args = parser.parse_args()
    if args.samples < 1 or any(n < 1 for n in args.n_values):
        parser.error("n-values and samples must be positive")

    rows = run(args.n_values, args.samples, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "fidelity_fallback_calibration.csv"
    json_path = args.output_dir / "fidelity_fallback_calibration.json"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "method": "global_Haar_state_sampling",
        "n_values": args.n_values,
        "samples_per_row": args.samples,
        "seed": args.seed,
        "rows": rows,
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
