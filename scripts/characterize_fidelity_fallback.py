#!/usr/bin/env python3
"""
Characterize exact-vs-fallback fidelity behavior on lightweight circuits.

This script is not part of the automatic reproduction pipeline. Invoke it
manually when auditing the sampling fallback used for circuits above
MAX_EXACT_FIDELITY_QUBITS.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.optimisation.base import BaseOptimizer, OptimizationResult
from src.optimisation.constants import DEFAULT_FIDELITY_SAMPLES, MAX_EXACT_FIDELITY_QUBITS


class _Inspector(BaseOptimizer):
    def optimize(self, circuit, target=None):
        return OptimizationResult(circuit.copy(), circuit.size(), circuit.size(), 1.0, 0, 0.0, True)


def _build_cases() -> list[tuple[str, QuantumCircuit, QuantumCircuit]]:
    cases = []

    same = QuantumCircuit(2)
    same.h(0)
    same.cx(0, 1)
    cases.append(("identical_bell", same, same.copy()))

    phase_a = QuantumCircuit(2)
    phase_a.h(0)
    phase_a.cx(0, 1)
    phase_b = phase_a.copy()
    phase_b.rz(0.05, 0)
    cases.append(("small_phase_error", phase_a, phase_b))

    inverse_pair = QuantumCircuit(1)
    inverse_pair.h(0)
    inverse_pair.h(0)
    identity = QuantumCircuit(1)
    cases.append(("identity_vs_hh", identity, inverse_pair))

    entangled_a = QuantumCircuit(3)
    entangled_a.h(0)
    entangled_a.cx(0, 1)
    entangled_a.cx(1, 2)
    entangled_b = entangled_a.copy()
    entangled_b.x(2)
    cases.append(("bit_flip_error", entangled_a, entangled_b))

    return cases


def characterize(samples: int, output: Path | None = None) -> Path:
    inspector = _Inspector(random_seed=1234)
    rows = []

    for name, circuit, target in _build_cases():
        exact = inspector.calculate_fidelity(circuit, target)
        estimate = inspector._estimate_fidelity(circuit, target, n_samples=samples)
        rows.append((name, circuit.num_qubits, circuit.size(), exact, estimate, abs(exact - estimate)))

    output_dir = PROJECT_ROOT / "docs" / "verification"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output or output_dir / f"fidelity_fallback_characterization_{date.today().isoformat()}.md"

    lines = [
        "# Fidelity fallback characterization",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Samples per fallback estimate: {samples}",
        f"Exact fidelity threshold: n <= {MAX_EXACT_FIDELITY_QUBITS} qubits",
        "",
        "This lightweight audit compares exact average gate fidelity with the sampling fallback on small synthetic circuits where exact fidelity is available. It is a characterization report, not a replacement for full-scale experiment reruns.",
        "",
        "| Case | Qubits | Gates | Exact fidelity | Fallback estimate | Absolute error |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, qubits, gates, exact, estimate, error in rows:
        lines.append(f"| {name} | {qubits} | {gates} | {exact:.12f} | {estimate:.12f} | {error:.12f} |")

    lines.extend([
        "",
        "## Interpretation limits",
        "",
        "- The fallback estimator is stochastic but seeded here for reproducibility.",
        "- These synthetic cases are intentionally small and fast; they do not characterize all large-circuit behavior.",
        "- Full publication-grade validation should increase sample counts and include canonical experiment outputs when available.",
    ])

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Characterize fidelity fallback behavior on lightweight circuits.")
    parser.add_argument("--samples", type=int, default=DEFAULT_FIDELITY_SAMPLES)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    path = characterize(samples=args.samples, output=args.output)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
