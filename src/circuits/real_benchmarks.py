"""Real-circuit benchmark suite for publication-grade optimizer evaluation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import TwoLocal
from qiskit.quantum_info import Operator


@dataclass(frozen=True)
class BenchmarkCircuit:
    """A named benchmark circuit and its provenance metadata."""

    circuit_id: str
    family: str
    circuit_type: str
    suite: str
    circuit: QuantumCircuit
    seed: Optional[int] = None
    notes: str = ""


def circuit_sha256(circuit: QuantumCircuit) -> str:
    """Return a stable SHA-256 hash of a circuit instruction stream."""
    instructions = []
    for inst in circuit.data:
        qubits = tuple(circuit.find_bit(q).index for q in inst.qubits)
        clbits = tuple(circuit.find_bit(c).index for c in inst.clbits)
        params = tuple(
            float(p) if isinstance(p, (int, float, np.floating)) else str(p)
            for p in inst.operation.params
        )
        instructions.append((inst.operation.name, qubits, clbits, params))
    payload = {
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "instructions": instructions,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def gate_counts(circuit: QuantumCircuit) -> Dict[str, int]:
    """Return gate-count summary for a circuit."""
    counts = {str(k): int(v) for k, v in circuit.count_ops().items()}
    one_q = sum(1 for inst in circuit.data if inst.operation.num_qubits == 1)
    two_q = sum(1 for inst in circuit.data if inst.operation.num_qubits == 2)
    multi_q = sum(1 for inst in circuit.data if inst.operation.num_qubits > 2)
    return {
        "gate_count_total": int(circuit.size()),
        "depth": int(circuit.depth() or 0),
        "gate_count_1q": int(one_q),
        "gate_count_2q": int(two_q),
        "gate_count_multiq": int(multi_q),
        "gate_counts_json": json.dumps(counts, sort_keys=True, separators=(",", ":")),
    }


def average_gate_fidelity(circuit: QuantumCircuit, target: QuantumCircuit, max_qubits: int = 10) -> Optional[float]:
    """Calculate average gate fidelity, or None if exact unitary comparison is too expensive."""
    if circuit.num_qubits != target.num_qubits or circuit.num_qubits > max_qubits:
        return None
    try:
        dim = 2 ** circuit.num_qubits
        u1 = np.asarray(Operator(circuit).data)
        u2 = np.asarray(Operator(target).data)
        inner = np.abs(np.trace(np.conj(u1).T @ u2)) ** 2
        return float((inner + dim) / (dim**2 + dim))
    except Exception:
        return None


def materialize_circuit(circuit: QuantumCircuit, parameter_seed: int = 42) -> QuantumCircuit:
    """Bind parameters deterministically and decompose composite instructions."""
    out = circuit
    if out.parameters:
        rng = np.random.RandomState(parameter_seed)
        values = {param: float(rng.uniform(-np.pi, np.pi)) for param in sorted(out.parameters, key=str)}
        out = out.assign_parameters(values)
    for _ in range(3):
        if all(inst.operation.definition is None for inst in out.data):
            break
        out = out.decompose()
    return out


def make_qft(n_qubits: int) -> QuantumCircuit:
    """Construct a transparent QFT circuit without final swaps."""
    qc = QuantumCircuit(n_qubits)
    for target in range(n_qubits):
        qc.h(target)
        for control in range(target + 1, n_qubits):
            qc.cp(np.pi / (2 ** (control - target)), control, target)
    return qc


def make_ghz(n_qubits: int) -> QuantumCircuit:
    """Construct a GHZ-state preparation circuit."""
    qc = QuantumCircuit(n_qubits)
    qc.h(0)
    for i in range(n_qubits - 1):
        qc.cx(i, i + 1)
    return qc


def make_cnot_chain(n_qubits: int, repeats: int = 4) -> QuantumCircuit:
    """Construct a positive-control CNOT chain with adjacent cancellable pairs."""
    qc = QuantumCircuit(n_qubits)
    for _ in range(repeats):
        for i in range(n_qubits - 1):
            qc.cx(i, i + 1)
            qc.cx(i, i + 1)
    return qc


def make_bernstein_vazirani(n_qubits: int, seed: int = 42) -> QuantumCircuit:
    """Construct a unitary Bernstein-Vazirani oracle-style circuit without measurement."""
    rng = np.random.RandomState(seed)
    qc = QuantumCircuit(n_qubits + 1)
    anc = n_qubits
    qc.x(anc)
    qc.h(anc)
    for i in range(n_qubits):
        qc.h(i)
    secret = rng.randint(0, 2, size=n_qubits)
    for i, bit in enumerate(secret):
        if bit:
            qc.cx(i, anc)
    for i in range(n_qubits):
        qc.h(i)
    qc.h(anc)
    qc.x(anc)
    return qc


def make_qaoa_line(n_qubits: int, reps: int = 1, seed: int = 42) -> QuantumCircuit:
    """Construct a line-graph QAOA-like ansatz with bound numeric angles."""
    rng = np.random.RandomState(seed)
    qc = QuantumCircuit(n_qubits)
    for q in range(n_qubits):
        qc.h(q)
    for _ in range(reps):
        gamma = float(rng.uniform(0.05, np.pi / 2))
        beta = float(rng.uniform(0.05, np.pi / 2))
        for i in range(n_qubits - 1):
            qc.rzz(2 * gamma, i, i + 1)
        for q in range(n_qubits):
            qc.rx(2 * beta, q)
    return materialize_circuit(qc, seed)


def make_vqe_twolocal(n_qubits: int, reps: int = 1, seed: int = 42) -> QuantumCircuit:
    """Construct a bound TwoLocal VQE-style ansatz."""
    ansatz = TwoLocal(
        n_qubits,
        rotation_blocks=["ry", "rz"],
        entanglement_blocks="cx",
        entanglement="linear",
        reps=reps,
        flatten=True,
    )
    return materialize_circuit(ansatz, seed)


def make_hardware_efficient(n_qubits: int, layers: int = 2, seed: int = 42) -> QuantumCircuit:
    """Construct a hardware-efficient ansatz with alternating rotations and entanglers."""
    rng = np.random.RandomState(seed)
    qc = QuantumCircuit(n_qubits)
    for _ in range(layers):
        for q in range(n_qubits):
            qc.ry(float(rng.uniform(-np.pi, np.pi)), q)
            qc.rz(float(rng.uniform(-np.pi, np.pi)), q)
        for start in (0, 1):
            for q in range(start, n_qubits - 1, 2):
                qc.cx(q, q + 1)
    return qc


# ---------------------------------------------------------------------------
# Extended circuit families (v5: added for QIP manuscript)
# ---------------------------------------------------------------------------


def make_grover(n_qubits: int, seed: int = 42) -> QuantumCircuit:
    """Construct a Grover search circuit for a random marked state.

    Uses a single Grover iteration with a phase oracle for one marked state.
    n_qubits is the number of search qubits (no ancilla).
    """
    rng = np.random.RandomState(seed)
    marked = rng.randint(0, 2 ** n_qubits)
    qc = QuantumCircuit(n_qubits)
    # Initialization: uniform superposition
    for q in range(n_qubits):
        qc.h(q)
    # Single Grover iteration
    # Oracle: flip sign of marked state
    marked_bits = format(marked, f"0{n_qubits}b")
    for i, bit in enumerate(marked_bits):
        if bit == "0":
            qc.x(i)
    if n_qubits >= 2:
        qc.h(n_qubits - 1)
        qc.mcx(list(range(n_qubits - 1)), n_qubits - 1)
        qc.h(n_qubits - 1)
    else:
        qc.z(0)
    for i, bit in enumerate(marked_bits):
        if bit == "0":
            qc.x(i)
    # Diffusion operator
    for q in range(n_qubits):
        qc.h(q)
        qc.x(q)
    if n_qubits >= 2:
        qc.h(n_qubits - 1)
        qc.mcx(list(range(n_qubits - 1)), n_qubits - 1)
        qc.h(n_qubits - 1)
    else:
        qc.z(0)
    for q in range(n_qubits):
        qc.x(q)
        qc.h(q)
    return qc


def make_quantum_adder(n_qubits: int, seed: int = 42) -> QuantumCircuit:
    """Construct a quantum ripple-carry adder for two n_qubit//2-bit numbers.

    Implements an explicit ripple-carry adder.  Carries are computed first
    (using only the original, unmodified input bits), then the sum is written
    into register b via CX gates.  This ordering guarantees correct carry
    propagation regardless of operand size.

    Qubit layout (total = 3*half + 1):
      [0, half)          -- register a  (input, preserved throughout)
      [half, 2*half)     -- register b  (input, overwritten with sum bits)
      [2*half, 3*half)   -- carry ancillas (one per bit position)
      3*half             -- carry output qubit (holds final carry)

    n_qubits is the total number of qubits (must be >= 3).
    half = (n_qubits - 1) // 2  bits per operand.
    """
    n = max(n_qubits, 3)
    half = max((n - 1) // 2, 1)  # bits per operand (>= 1)
    total_qubits = 3 * half + 1  # a + b + carry ancillas + carry output
    qc = QuantumCircuit(total_qubits)
    rng = np.random.RandomState(seed)
    a_val = rng.randint(0, 2 ** half)
    b_val = rng.randint(0, 2 ** half)

    # Encode input a into qubits [0, half)
    for i in range(half):
        if (a_val >> i) & 1:
            qc.x(i)
    # Encode input b into qubits [half, 2*half)
    for i in range(half):
        if (b_val >> i) & 1:
            qc.x(half + i)

    # Carry ancillas: carry[i] = 2*half + i, for i in [0, half)
    # All start as |0>.  carry[0] = carry_in = 0 (half-adder).
    # Carry output: qubit 3*half, starts as |0>.

    # --- Step 1: Compute all carries (forward pass) ---
    # carry[i+1] = (a[i] AND b[i]) OR (carry[i] AND (a[i] XOR b[i]))
    # Decomposed into: CCX(a[i], b[i], carry[i+1]) then CCX(carry[i], a[i] XOR b[i], carry[i+1])
    # The second CCX uses a[i] and b[i] as controls; their XOR is computed
    # implicitly because (a AND NOT-b) OR (NOT-a AND b) covers the XOR case.
    # We use the identity: CCX(c, a, t) . CCX(c, b, t) = carry for (a,b,c).
    for i in range(half):
        a_q = i
        b_q = half + i
        cin_q = 2 * half + i       # carry[i]
        cout_q = 2 * half + i + 1  # carry[i+1]
        # First term: a[i] AND b[i] -> carry[i+1]
        qc.ccx(a_q, b_q, cout_q)
        # Second term: carry[i] AND (a[i] XOR b[i]) -> carry[i+1]
        # Uses the fact that CCX(c,a,t) followed by CCX(c,b,t) toggles t
        # exactly when c=1 and exactly one of a,b is 1 (i.e., a XOR b = 1).
        qc.ccx(cin_q, a_q, cout_q)
        qc.ccx(cin_q, b_q, cout_q)

    # --- Step 2: Compute sums into b register ---
    # sum[i] = a[i] XOR b[i] XOR carry[i]
    for i in range(half):
        a_q = i
        b_q = half + i
        cin_q = 2 * half + i
        qc.cx(a_q, b_q)
        qc.cx(cin_q, b_q)

    return qc


def make_quantum_walk(n_qubits: int, steps: int = 3, seed: int = 42) -> QuantumCircuit:
    """Construct a discrete-time quantum walk on a cycle graph of 2^n_pos nodes.

    Uses a coin qubit plus n_pos position qubits (n_pos = max(n_qubits, 3)).
    The walk alternates Hadamard coin flips with conditional shifts
    (increment on coin=|0⟩, decrement on coin=|1⟩).
    
    Shift operations use a proper conditional incrementer/decrementer:
    - Increment: flip bit k iff all lower bits 0..k-1 are |1⟩ (carry propagation)
    - Decrement: flip bit k iff all lower bits 0..k-1 are |0⟩ (borrow propagation)
    """
    n_pos = max(n_qubits, 3)
    n_total = n_pos + 1  # +1 coin qubit
    qc = QuantumCircuit(n_total)
    coin = n_pos
    rng = np.random.RandomState(seed)
    # Initialize position to |0...0>
    # Apply random initial coin state
    theta = float(rng.uniform(0, np.pi))
    qc.ry(theta, coin)
    for _ in range(steps):
        # Coin flip
        qc.h(coin)
        # Conditional shift right (increment) controlled on coin=|0>
        qc.x(coin)  # flip coin so |0> -> |1> for controlled operations
        _controlled_increment(qc, coin, list(range(n_pos)))
        qc.x(coin)  # restore coin
        # Conditional shift left (decrement) controlled on coin=|1>
        _controlled_decrement(qc, coin, list(range(n_pos)))
    return qc


def _controlled_increment(qc: QuantumCircuit, ctrl: int, register: list):
    """Conditionally increment a binary register controlled on ctrl qubit.
    
    Flips bit k iff ctrl=|1> AND all lower bits 0..k-1 are |1> (carry propagation).
    Processes from MSB to LSB using multi-controlled X gates so that each bit
    is flipped based on the *original* (unmodified) values of all lower bits.
    """
    n = len(register)
    if n == 0:
        return
    if n == 1:
        qc.cx(ctrl, register[0])
        return
    if n == 2:
        qc.ccx(ctrl, register[0], register[1])
        qc.cx(ctrl, register[0])
        return
    # For n >= 3: flip each bit from MSB to LSB using MCX.
    # Bit k flips iff ctrl AND register[0] AND ... AND register[k-1] are all |1>.
    # Processing MSB-first ensures lower bits are still in their original state
    # when they serve as controls for higher-bit flips.
    for k in range(n - 1, 0, -1):
        controls = [ctrl] + register[:k]
        qc.mcx(controls, register[k])
    # Flip bit 0 controlled on ctrl only
    qc.cx(ctrl, register[0])


def _controlled_decrement(qc: QuantumCircuit, ctrl: int, register: list):
    """Conditionally decrement a binary register controlled on ctrl qubit.
    
    Flips bit k iff ctrl=|1⟩ AND all lower bits 0..k-1 are |0⟩.
    Uses X gates to convert to increment-like logic.
    """
    n = len(register)
    if n == 0:
        return
    # Decrement = X on all bits, then increment, then X on all bits
    # But controlled: only when ctrl=|1⟩
    # Simpler approach: flip all register bits, increment, flip back
    for q in register:
        qc.x(q)
    _controlled_increment(qc, ctrl, register)
    for q in register:
        qc.x(q)


def make_iqp(n_qubits: int, depth: int = 3, seed: int = 42) -> QuantumCircuit:
    """Construct an IQP (Instantaneous Quantum Polynomial) circuit.

    Structure: H^{⊗n} → diagonal unitary layers → H^{⊗n}.
    Diagonal layers consist of Z-rotations and CZ gates.
    IQP circuits are believed to be hard to simulate classically.
    """
    rng = np.random.RandomState(seed)
    qc = QuantumCircuit(n_qubits)
    # Initial Hadamard layer
    for q in range(n_qubits):
        qc.h(q)
    # Diagonal unitary layers
    for _ in range(depth):
        # Single-qubit Z-rotations
        for q in range(n_qubits):
            angle = float(rng.choice([0, np.pi / 4, np.pi / 2, np.pi]))
            if abs(angle) > 1e-10:
                qc.rz(angle, q)
        # Random CZ gates on nearest neighbors
        for q in range(n_qubits - 1):
            if rng.random() < 0.5:
                qc.cz(q, q + 1)
    # Final Hadamard layer
    for q in range(n_qubits):
        qc.h(q)
    return qc


def make_random_clifford(n_qubits: int, depth: int = 10, seed: int = 42) -> QuantumCircuit:
    """Construct a random Clifford circuit.

    Uses gates from {H, S, CNOT} — the Clifford group generators.
    Clifford circuits are efficiently simulable (Gottesman-Knill theorem).
    """
    rng = np.random.RandomState(seed)
    qc = QuantumCircuit(n_qubits)
    for _ in range(depth):
        for q in range(n_qubits):
            gate_choice = rng.choice(["h", "s", "id"])
            if gate_choice == "h":
                qc.h(q)
            elif gate_choice == "s":
                qc.s(q)
        # Random CNOT between nearest neighbors
        if rng.random() < 0.5 and n_qubits >= 2:
            ctrl = rng.randint(0, n_qubits - 1)
            qc.cx(ctrl, ctrl + 1)
    return qc


def make_surface_code_syndrome(n_qubits: int, seed: int = 42) -> QuantumCircuit:
    """Construct a simplified surface-code syndrome extraction circuit.

    Models a single round of X-stabilizer measurement on a surface code patch.
    n_qubits represents data qubits; one ancilla is added for syndrome extraction.
    """
    n_data = max(n_qubits, 4)
    qc = QuantumCircuit(n_data + 1)
    ancilla = n_data
    rng = np.random.RandomState(seed)
    # Random data-qubit initialization (some X errors)
    for q in range(n_data):
        if rng.random() < 0.2:
            qc.x(q)
    # Syndrome extraction: CNOT from each data qubit to ancilla
    qc.h(ancilla)
    for q in range(n_data):
        qc.cx(q, ancilla)
    qc.h(ancilla)
    return qc


def make_parameterized_ansatz(n_qubits: int, reps: int = 1, seed: int = 42) -> QuantumCircuit:
    """Construct a parameterized chemistry-inspired ansatz circuit.

    NOTE: This is *not* a true UCCSD ansatz. A genuine UCCSD would use
    fermionic excitation operators (implemented via Jordan-Wigner or
    Bravyi-Kitaev mappings) with SWAP networks and exact Trotterized
    exponentials. This function instead builds a simplified Ry-CNOT
    ladder structure that is loosely inspired by the *shape* of UCCSD
    (single + double excitation patterns) but does not preserve the
    fermionic structure or the unitary coupled-cluster amplitude
    parametrization. It is retained as a parameterized-ansatz
    benchmark, not as a chemically accurate UCCSD.

    Models single and double excitation-like patterns decomposed into
    CNOT ladders and Ry rotations.
    """
    rng = np.random.RandomState(seed)
    qc = QuantumCircuit(n_qubits)
    # Hartree-Fock reference state: fill first half of orbitals
    n_occ = n_qubits // 2
    for q in range(n_occ):
        qc.x(q)
    for _ in range(reps):
        # Single excitations: occ -> virt
        for i in range(n_occ):
            for a in range(n_occ, n_qubits):
                theta = float(rng.uniform(-0.5, 0.5))
                if abs(theta) > 0.01:
                    # Simplified single excitation: Ry-CNOT-Ry pattern
                    qc.ry(theta, a)
                    qc.cx(i, a)
                    qc.ry(-theta, a)
        # Double excitations: pair of occ -> pair of virt
        if n_qubits >= 4:
            for i in range(min(n_occ, 2)):
                j = (i + 1) % n_occ
                for a in range(n_occ, min(n_qubits, n_occ + 2)):
                    b = a + 1 if a + 1 < n_qubits else a
                    if a != b:
                        theta = float(rng.uniform(-0.3, 0.3))
                        if abs(theta) > 0.01:
                            # Simplified double excitation ladder
                            qc.cx(i, a)
                            qc.cx(j, b)
                            qc.ry(theta, a)
                            qc.cx(a, b)
                            qc.ry(-theta, a)
                            qc.cx(i, a)
                            qc.cx(j, b)
    return qc


def make_haar_random(n_qubits: int, seed: int = 42) -> QuantumCircuit:
    """Construct a Haar-random unitary circuit via exact synthesis.

    Only feasible for n_qubits <= 4 due to exponential cost.
    Uses Qiskit's random unitary generation and decomposition.
    """
    from qiskit.quantum_info import random_unitary
    if n_qubits > 4:
        raise ValueError(f"Haar random only feasible for n<=4, got n={n_qubits}")
    rng = np.random.RandomState(seed)
    u = random_unitary(2 ** n_qubits, seed=int(rng.randint(0, 2**31)))
    qc = QuantumCircuit(n_qubits)
    qc.unitary(u, list(range(n_qubits)), label="haar_random")
    return qc.decompose()


def generate_extended_suite(mode: str = "smoke", seed: int = 42) -> List[BenchmarkCircuit]:
    """Generate the extended benchmark suite (v5) with 15 circuit families.

    In 'full' mode, scalable families are also generated at n=12, 15, 20
    to support the qubit-scaling analysis (P4).
    """
    if mode not in {"smoke", "full"}:
        raise ValueError("mode must be 'smoke' or 'full'")
    sizes = [3, 4, 5] if mode == "smoke" else [3, 4, 5, 6, 7, 8, 9, 10]
    # Large-scale sizes for scalability analysis (P4)
    large_sizes = [] if mode == "smoke" else [12, 15, 20]
    circuits: List[BenchmarkCircuit] = []
    suite = f"extended_v5_{mode}"

    for n in sizes:
        # Original families
        circuits.extend([
            BenchmarkCircuit(f"qft_{n}", "QFT", "qft", suite, make_qft(n), seed),
            BenchmarkCircuit(f"ghz_{n}", "GHZ", "ghz", suite, make_ghz(n), seed),
            BenchmarkCircuit(f"cnot_chain_{n}", "CNOT", "cnot_chain", suite, make_cnot_chain(n), seed),
            BenchmarkCircuit(f"bv_{n}", "Oracle", "bernstein_vazirani", suite, make_bernstein_vazirani(n, seed + n), seed + n),
            BenchmarkCircuit(f"qaoa_line_{n}", "QAOA", "qaoa_line", suite, make_qaoa_line(n, reps=1 if mode == "smoke" else 2, seed=seed + 100 + n), seed + 100 + n),
            BenchmarkCircuit(f"vqe_twolocal_{n}", "VQE", "two_local", suite, make_vqe_twolocal(n, reps=1 if mode == "smoke" else 2, seed=seed + 200 + n), seed + 200 + n),
            BenchmarkCircuit(f"hardware_eff_{n}", "HardwareEfficient", "hardware_efficient", suite, make_hardware_efficient(n, layers=1 if mode == "smoke" else 2, seed=seed + 300 + n), seed + 300 + n),
        ])

        # New families (v5)
        circuits.extend([
            BenchmarkCircuit(f"grover_{n}", "Grover", "grover", suite, make_grover(n, seed=seed + 400 + n), seed + 400 + n, notes="Single Grover iteration, random marked state"),
            BenchmarkCircuit(f"adder_{n}", "Adder", "quantum_adder", suite, make_quantum_adder(n, seed=seed + 500 + n), seed + 500 + n, notes="Ripple-carry adder, random inputs"),
            BenchmarkCircuit(f"qwalk_{n}", "QuantumWalk", "quantum_walk", suite, make_quantum_walk(n, steps=3, seed=seed + 600 + n), seed + 600 + n, notes="DTQW on cycle, 3 steps"),
            BenchmarkCircuit(f"iqp_{n}", "IQP", "iqp", suite, make_iqp(n, depth=3, seed=seed + 700 + n), seed + 700 + n, notes="IQP circuit, 3 diagonal layers"),
            BenchmarkCircuit(f"clifford_{n}", "RandomClifford", "random_clifford", suite, make_random_clifford(n, depth=10, seed=seed + 800 + n), seed + 800 + n, notes="Random Clifford, depth=10"),
            BenchmarkCircuit(f"surface_code_{n}", "SurfaceCode", "surface_code", suite, make_surface_code_syndrome(n, seed=seed + 900 + n), seed + 900 + n, notes="X-stabilizer syndrome extraction"),
            BenchmarkCircuit(f"uccsd_{n}", "UCCSD", "uccsd_ansatz", suite, make_parameterized_ansatz(n, reps=1, seed=seed + 1000 + n), seed + 1000 + n, notes="Parameterized ansatz (not true UCCSD; see make_parameterized_ansatz docstring)"),
        ])

    # Large-scale instances for scalable families (P4: n=12, 15, 20)
    for n in large_sizes:
        reps = 2 if mode == "full" else 1
        circuits.extend([
            BenchmarkCircuit(f"qft_{n}", "QFT", "qft", suite, make_qft(n), seed, notes=f"Large-scale n={n}"),
            BenchmarkCircuit(f"ghz_{n}", "GHZ", "ghz", suite, make_ghz(n), seed, notes=f"Large-scale n={n}"),
            BenchmarkCircuit(f"cnot_chain_{n}", "CNOT", "cnot_chain", suite, make_cnot_chain(n), seed, notes=f"Large-scale n={n}"),
            BenchmarkCircuit(f"bv_{n}", "Oracle", "bernstein_vazirani", suite, make_bernstein_vazirani(n, seed + n), seed + n, notes=f"Large-scale n={n}"),
            BenchmarkCircuit(f"qaoa_line_{n}", "QAOA", "qaoa_line", suite, make_qaoa_line(n, reps=reps, seed=seed + 100 + n), seed + 100 + n, notes=f"Large-scale n={n}"),
            BenchmarkCircuit(f"hardware_eff_{n}", "HardwareEfficient", "hardware_efficient", suite, make_hardware_efficient(n, layers=2, seed=seed + 300 + n), seed + 300 + n, notes=f"Large-scale n={n}"),
            BenchmarkCircuit(f"iqp_{n}", "IQP", "iqp", suite, make_iqp(n, depth=3, seed=seed + 700 + n), seed + 700 + n, notes=f"Large-scale n={n}"),
            BenchmarkCircuit(f"clifford_{n}", "RandomClifford", "random_clifford", suite, make_random_clifford(n, depth=10, seed=seed + 800 + n), seed + 800 + n, notes=f"Large-scale n={n}"),
            BenchmarkCircuit(f"surface_code_{n}", "SurfaceCode", "surface_code", suite, make_surface_code_syndrome(n, seed=seed + 900 + n), seed + 900 + n, notes=f"Large-scale n={n}"),
        ])

    # Haar random only for small sizes (exponential cost)
    haar_sizes = [3, 4] if mode == "smoke" else [2, 3, 4]
    for n in haar_sizes:
        circuits.append(
            BenchmarkCircuit(f"haar_{n}", "HaarRandom", "haar_random", suite, make_haar_random(n, seed=seed + 1100 + n), seed + 1100 + n, notes="Haar-random unitary, exact synthesis")
        )

    return circuits


def generate_real_circuit_suite(mode: str = "smoke", seed: int = 42) -> List[BenchmarkCircuit]:
    """Generate benchmark circuits — delegates to generate_extended_suite for v5."""
    return generate_extended_suite(mode=mode, seed=seed)
