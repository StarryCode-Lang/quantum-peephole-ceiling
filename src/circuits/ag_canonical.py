"""
Aaronson-Gottesman canonical form circuit generator.

The Aaronson-Gottesman normal form decomposes any n-qubit Clifford circuit
into at most 11 stages:

    H -- C -- H -- C -- H -- S -- C -- S -- H -- C -- H

where H = layer of Hadamard gates, C = layer of CNOT gates, S = layer of
phase gates.  Within each stage, gates act on disjoint qubits.

Reference:
    S. Aaronson and D. Gottesman, "Improved Simulation of Stabilizer Circuits",
    Phys. Rev. A 70, 052328 (2004).
"""

from __future__ import annotations

import random
from typing import Optional

from qiskit import QuantumCircuit


def _random_pairing(n_qubits: int, seed: Optional[int] = None) -> list[tuple[int, int]]:
    """Return a random matching of qubits into disjoint pairs (or one singleton)."""
    rng = random.Random(seed)
    qubits = list(range(n_qubits))
    rng.shuffle(qubits)
    pairs = []
    while len(qubits) >= 2:
        a = qubits.pop()
        b = qubits.pop()
        pairs.append((a, b))
    return pairs


def generate_ag_canonical_circuit(
    n_qubits: int,
    seed: Optional[int] = None,
    apply_h: bool = True,
    apply_s: bool = True,
) -> QuantumCircuit:
    """Generate a random Clifford circuit in Aaronson-Gottesman canonical form.

    Args:
        n_qubits: Number of qubits (must be >= 2).
        seed: Random seed for reproducibility.
        apply_h: If False, omit all H layers (for testing sub-components).
        apply_s: If False, omit all S layers.

    Returns:
        A QuantumCircuit in AG canonical form.
    """
    if n_qubits < 2:
        raise ValueError("AG canonical form requires at least 2 qubits.")

    rng = random.Random(seed)
    qc = QuantumCircuit(n_qubits)

    # 11 stages: H C H C H S C S H C H
    stages = ["H", "C", "H", "C", "H", "S", "C", "S", "H", "C", "H"]
    for stage_idx, stage in enumerate(stages):
        stage_seed = seed + stage_idx * 10007 if seed is not None else None
        if stage == "H":
            if not apply_h:
                continue
            # Each H layer applies H to a random subset of qubits, disjoint by
            # definition (single-qubit gates).
            for q in range(n_qubits):
                if rng.random() < 0.5:
                    qc.h(q)
        elif stage == "S":
            if not apply_s:
                continue
            # Each S layer applies S or Sdg to a random subset of qubits.
            for q in range(n_qubits):
                if rng.random() < 0.3:
                    qc.s(q)
                elif rng.random() < 0.3:
                    qc.sdg(q)
        elif stage == "C":
            # CNOT layer: disjoint pairs.
            pairs = _random_pairing(n_qubits, stage_seed)
            for control, target in pairs:
                # Random direction for variety.
                if rng.random() < 0.5:
                    qc.cx(control, target)
                else:
                    qc.cx(target, control)
    return qc


def generate_ag_canonical_batch(
    n_qubits: int,
    n_circuits: int,
    base_seed: int = 42,
    **kwargs,
) -> list[QuantumCircuit]:
    """Generate a batch of AG canonical form circuits."""
    return [
        generate_ag_canonical_circuit(n_qubits, seed=base_seed + i, **kwargs)
        for i in range(n_circuits)
    ]
