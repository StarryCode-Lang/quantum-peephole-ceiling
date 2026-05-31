"""
Core quantum circuit primitives - FIXED VERSION
===============================================
Fixes:
1. Random circuit: random pairing (not sequential) for CNOT gates
2. Page value: computed numerically via Haar-random states
3. Structural perturbations for landscape analysis
"""

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Statevector, partial_trace, entropy, random_statevector
from typing import List, Tuple, Optional, Dict
import warnings
warnings.filterwarnings('ignore')


# ============================================================
# Page value computation
# ============================================================

def compute_page_value(n_qubits: int, n_samples: int = 500, seed: int = 42) -> float:
    """
    Compute the Page value numerically by averaging over Haar-random states.
    
    The Page value is the expected entanglement entropy of a subsystem A
    (first floor(n/2) qubits) when the total state is Haar-random.
    
    This avoids formula approximation errors for small n.
    """
    rng = np.random.RandomState(seed)
    n_A = n_qubits // 2
    qubits_B = list(range(n_A, n_qubits))
    
    entropies = []
    for _ in range(n_samples):
        # Generate Haar-random state using Qiskit
        sv = random_statevector(2**n_qubits, seed=rng.randint(0, 2**31))
        rho_A = partial_trace(sv, qubits_B)
        S = float(entropy(rho_A, base=2))
        entropies.append(S)
    
    return float(np.mean(entropies))


# Pre-compute Page values for common system sizes
PAGE_VALUES = {}


def get_page_value(n_qubits: int) -> float:
    """Get Page value for given qubit count, computing if needed."""
    if n_qubits not in PAGE_VALUES:
        PAGE_VALUES[n_qubits] = compute_page_value(n_qubits)
    return PAGE_VALUES[n_qubits]


# ============================================================
# Random circuit generation - FIXED
# ============================================================

def generate_random_circuit(
    n_qubits: int,
    depth: int,
    two_qubit_ratio: float = 0.3,
    gate_set: str = 'ht_rz_cnot',
    topology: str = 'nearest_neighbor',
    seed: int = 0
) -> QuantumCircuit:
    """
    Generate a random quantum circuit with controlled parameters.
    
    FIXES:
    - All qubits can participate in CNOT gates (random pairing)
    - Multiple gate sets supported for ablation
    - Multiple topologies supported for ablation
    
    Args:
        n_qubits: Number of qubits
        depth: Circuit depth (number of layers)
        two_qubit_ratio: Fraction of operations that are two-qubit gates
        gate_set: 'ht_rz_cnot', 'clifford_cnot', 'h_cnot', 't_rz_cnot'
        topology: 'nearest_neighbor', 'random_pairing', 'all_to_all'
        seed: Random seed for reproducibility
    
    Returns:
        QuantumCircuit
    """
    rng = np.random.RandomState(seed)
    qr = QuantumRegister(n_qubits, 'q')
    qc = QuantumCircuit(qr)
    
    # Define gate sets
    single_gates = {
        'ht_rz_cnot': ['h', 't', 'rz'],
        'clifford_cnot': ['h', 's', 'x'],
        'h_cnot': ['h'],
        't_rz_cnot': ['t', 'rz'],
    }
    gates = single_gates.get(gate_set, single_gates['ht_rz_cnot'])
    
    for layer in range(depth):
        # Decide which qubits get two-qubit vs single-qubit gates
        # Use random pairing so ALL qubits can participate
        if n_qubits == 1:
            # Single qubit: only single-qubit gates
            gate = rng.choice(gates)
            _apply_single_gate(qc, 0, gate, rng)
            continue
        
        # Generate a random matching of qubits for this layer
        if topology == 'nearest_neighbor':
            pairs = _nearest_neighbor_pairs(n_qubits, rng)
        elif topology == 'random_pairing':
            pairs = _random_pairing(n_qubits, rng)
        elif topology == 'all_to_all':
            pairs = _random_pairing(n_qubits, rng)  # same as random for one layer
        else:
            pairs = _nearest_neighbor_pairs(n_qubits, rng)
        
        # For each pair, decide if it's a CNOT or two single-qubit gates
        used_qubits = set()
        for q1, q2 in pairs:
            if rng.random() < two_qubit_ratio:
                qc.cx(q1, q2)
                used_qubits.add(q1)
                used_qubits.add(q2)
        
        # Apply single-qubit gates to unused qubits
        for q in range(n_qubits):
            if q not in used_qubits:
                gate = rng.choice(gates)
                _apply_single_gate(qc, q, gate, rng)
    
    return qc


def _apply_single_gate(qc: QuantumCircuit, qubit: int, gate: str, rng):
    """Apply a single-qubit gate to the circuit."""
    if gate == 'h':
        qc.h(qubit)
    elif gate == 't':
        qc.t(qubit)
    elif gate == 's':
        qc.s(qubit)
    elif gate == 'x':
        qc.x(qubit)
    elif gate == 'rz':
        qc.rz(rng.uniform(0, 2 * np.pi), qubit)
    elif gate == 'rx':
        qc.rx(rng.uniform(0, 2 * np.pi), qubit)
    elif gate == 'ry':
        qc.ry(rng.uniform(0, 2 * np.pi), qubit)


def _nearest_neighbor_pairs(n_qubits: int, rng) -> List[Tuple[int, int]]:
    """
    Generate nearest-neighbor pairs with random offset.
    Returns a list of non-overlapping pairs.
    """
    offset = rng.randint(0, 2)  # 0 or 1
    pairs = []
    i = offset
    while i + 1 < n_qubits:
        pairs.append((i, i + 1))
        i += 2
    return pairs


def _random_pairing(n_qubits: int, rng) -> List[Tuple[int, int]]:
    """
    Generate a random perfect matching (or near-perfect) of qubits.
    All qubits are paired, guaranteeing everyone can participate.
    """
    qubits = list(range(n_qubits))
    rng.shuffle(qubits)
    pairs = []
    for i in range(0, len(qubits) - 1, 2):
        pairs.append((qubits[i], qubits[i + 1]))
    return pairs


# ============================================================
# Entanglement entropy computation
# ============================================================

def compute_entanglement_entropy(circuit: QuantumCircuit, n_qubits: int) -> float:
    """
    Compute exact von Neumann entropy of reduced state on first half.
    Returns entropy in bits (log base 2).
    """
    try:
        sv = Statevector.from_label('0' * n_qubits).evolve(circuit)
        n_A = n_qubits // 2
        rho_A = partial_trace(sv, list(range(n_A, n_qubits)))
        return float(entropy(rho_A, base=2))
    except Exception:
        return 0.0


def compute_entanglement_entropy_from_sv(sv: Statevector, n_qubits: int) -> float:
    """Compute entanglement entropy from a pre-computed statevector."""
    try:
        n_A = n_qubits // 2
        rho_A = partial_trace(sv, list(range(n_A, n_qubits)))
        return float(entropy(rho_A, base=2))
    except Exception:
        return 0.0


# ============================================================
# Structural perturbation for landscape analysis - NEW
# ============================================================

def perturb_circuit_structural(
    circuit: QuantumCircuit,
    n_qubits: int,
    n_swaps: int = 1,
    seed: int = 0
) -> QuantumCircuit:
    """
    Perturb a circuit by swapping gate positions (structural perturbation).
    
    This probes the entanglement landscape properly, because entanglement
    depends on gate ordering, not just gate angles.
    
    Types of perturbation:
    1. Swap two adjacent gate positions
    2. Replace a CNOT with a different qubit pair
    3. Replace a single-qubit gate with a different type
    """
    rng = np.random.RandomState(seed)
    perturbed = circuit.copy()
    data = list(perturbed.data)
    
    if len(data) < 2:
        return perturbed
    
    for _ in range(n_swaps):
        pert_type = rng.choice(['swap_positions', 'replace_single', 'change_cnot_target'])
        
        if pert_type == 'swap_positions' and len(data) >= 2:
            # Swap two random gate positions
            i, j = rng.choice(len(data), 2, replace=False)
            data[i], data[j] = data[j], data[i]
            
        elif pert_type == 'replace_single':
            # Find single-qubit gates and replace with a different type
            single_indices = [i for i, inst in enumerate(data) 
                           if inst.operation.num_qubits == 1]
            if single_indices:
                idx = rng.choice(single_indices)
                inst = data[idx]
                qubit = inst.qubits[0]
                current_name = inst.operation.name
                alternatives = [g for g in ['h', 't', 'rz'] if g != current_name]
                if alternatives:
                    new_gate = rng.choice(alternatives)
                    new_circ = QuantumCircuit(n_qubits)
                    if new_gate == 'h':
                        new_circ.h(qubit)
                    elif new_gate == 't':
                        new_circ.t(qubit)
                    elif new_gate == 'rz':
                        new_circ.rz(rng.uniform(0, 2*np.pi), qubit)
                    data[idx] = list(new_circ.data)[0]
                    
        elif pert_type == 'change_cnot_target':
            # Find CNOT gates and change target qubit
            cnot_indices = [i for i, inst in enumerate(data) 
                          if inst.operation.num_qubits == 2]
            if cnot_indices:
                idx = rng.choice(cnot_indices)
                inst = data[idx]
                control = inst.qubits[0]
                # Change target to a different qubit
                possible_targets = [q for q in range(n_qubits) if q != control]
                if possible_targets:
                    new_target = rng.choice(possible_targets)
                    new_circ = QuantumCircuit(n_qubits)
                    new_circ.cx(control, new_target)
                    data[idx] = list(new_circ.data)[0]
    
    # Rebuild circuit
    new_qc = QuantumCircuit(QuantumRegister(n_qubits, 'q'))
    for inst in data:
        new_qc.append(inst)
    return new_qc


def perturb_circuit_angle(
    circuit: QuantumCircuit,
    n_qubits: int,
    n_perturbations: int = 1,
    sigma: float = 0.3,
    seed: int = 0
) -> QuantumCircuit:
    """
    Perturb a circuit by changing gate angles (original method).
    NOTE: This does NOT probe entanglement landscape because
    entanglement is invariant to single-qubit rotations.
    Kept for comparison with structural perturbation.
    """
    rng = np.random.RandomState(seed)
    perturbed = circuit.copy()
    
    rot_names = {'rz', 'rx', 'ry'}
    rot_indices = [i for i, inst in enumerate(perturbed.data) 
                  if inst.operation.name in rot_names]
    
    for _ in range(n_perturbations):
        if rot_indices:
            idx = rng.choice(rot_indices)
            old_angle = perturbed.data[idx].operation.params[0]
            perturbed.data[idx].operation.params[0] = old_angle + rng.normal(0, sigma)
    
    return perturbed


# ============================================================
# Gate counting utilities
# ============================================================

def count_gates(circuit: QuantumCircuit) -> Dict[str, int]:
    """Count gates by type."""
    counts = {'single': 0, 'two_qubit': 0, 'total': 0}
    for inst in circuit.data:
        counts['total'] += 1
        if inst.operation.num_qubits == 1:
            counts['single'] += 1
        elif inst.operation.num_qubits == 2:
            counts['two_qubit'] += 1
    return counts


def gate_reduction(original: QuantumCircuit, optimized: QuantumCircuit) -> float:
    """Compute gate reduction ratio."""
    orig_size = original.size()
    opt_size = optimized.size()
    if orig_size == 0:
        return 0.0
    return 1.0 - opt_size / orig_size
