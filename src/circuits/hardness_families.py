"""
Hardness families for Phase-1/Phase-2 separation.

Implements the explicit circuit family from Theorem 7 that has R1 = 0 but
achieves Omega(1) reduction under Phase-2 commutation rewriting.
"""

from __future__ import annotations

from qiskit import QuantumCircuit


def make_theorem7_hardness_family(n_qubits: int) -> QuantumCircuit:
    """Construct the Theorem-7 artificial hardness family circuit.

    The circuit has the following layered structure (for even n):

        1. CNOT on even-indexed pairs: (0,1), (2,3), ...
        2. H on all qubits
        3. CNOT on odd-indexed pairs: (1,2), (3,4), ...
        4. S on each control qubit of Layer-3 CNOTs
        5. CNOT on the same odd-indexed pairs as Layer 3
        6. Sdg on each control qubit of Layer-3 CNOTs
        7. H on all qubits
        8. CNOT on the same even-indexed pairs as Layer 1

    The circuit implements the identity.  Phase 1 has no adjacent inverse pairs
    because the S/Sdg separators block direct CNOT-CNOT cancellation and the H
    layers are separated by non-commuting gates.  Phase 2 commutes S past CNOT
    controls, exposing the Layer-3/4 CNOT pairs and the S/Sdg pairs for
    cancellation.

    Args:
        n_qubits: Number of qubits.  Must be >= 4 and even.

    Returns:
        A QuantumCircuit representing the Theorem-7 family.
    """
    if n_qubits < 4:
        raise ValueError("Theorem-7 hardness family requires at least 4 qubits.")
    if n_qubits % 2 != 0:
        raise ValueError("Theorem-7 hardness family requires an even number of qubits.")

    qc = QuantumCircuit(n_qubits)

    # Layer 1: CNOT on even-indexed pairs.
    even_pairs = [(i, i + 1) for i in range(0, n_qubits, 2)]
    for c, t in even_pairs:
        qc.cx(c, t)

    # Layer 2: H on all qubits.
    for q in range(n_qubits):
        qc.h(q)

    # Layer 3: CNOT on odd-indexed pairs.
    odd_pairs = [(i, i + 1) for i in range(1, n_qubits - 1, 2)]
    for c, t in odd_pairs:
        qc.cx(c, t)

    # Layer 3.5: S on each control qubit of Layer 3.
    for c, _ in odd_pairs:
        qc.s(c)

    # Layer 4: repeat Layer 3 CNOTs.
    for c, t in odd_pairs:
        qc.cx(c, t)

    # Layer 4.5: Sdg on each control qubit of Layer 3.
    for c, _ in odd_pairs:
        qc.sdg(c)

    # Layer 5: H on all qubits.
    for q in range(n_qubits):
        qc.h(q)

    # Layer 6: repeat Layer 1 CNOTs.
    for c, t in even_pairs:
        qc.cx(c, t)

    return qc
