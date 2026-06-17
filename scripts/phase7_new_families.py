"""
PHASE-7 A5: 5 New Unseen Circuit Families (Held-Out Validation).
=================================================================
Generates 5 NEW circuit families NOT in the original 15:
  1. Shor (modular exponentiation)
  2. Ising (transverse field)
  3. QML (variational quantum classifier)
  4. QPE (quantum phase estimation)
  5. QAOA-mixer (modified QAOA with different mixer)

Runs our optimizer on each family and compares ACTUAL reduction to the
predicted reduction from the "Universal Law" (multilinear model):
    reduction = 1.102 * commutation_density + 1.332 * inverse_pair_density + 0.001

Output: data/v5/new_families_heldout.csv
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from qiskit import QuantumCircuit

from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase2.commutation_rewriter import HybridCommuteRewrite


# ============================================================================
# Circuit feature extraction
# ============================================================================

def compute_inverse_pair_density(circuit: QuantumCircuit) -> float:
    """Compute inverse_pair_density: fraction of adjacent gate pairs that are inverses."""
    SELF_INVERSE = {'h', 'x', 'y', 'z', 'cx', 'cz', 'swap'}
    data = circuit.data
    if len(data) < 2:
        return 0.0
    count = 0
    total = len(data) - 1
    for i in range(total):
        g1 = data[i].operation
        g2 = data[i + 1].operation
        n1, n2 = g1.name, g2.name
        q1 = [circuit.find_bit(q).index for q in data[i].qubits]
        q2 = [circuit.find_bit(q).index for q in data[i + 1].qubits]
        if q1 == q2 and n1 == n2 and n1 in SELF_INVERSE:
            count += 1
        elif q1 == q2 and ((n1 == 't' and n2 == 'tdg') or (n1 == 'tdg' and n2 == 't')):
            count += 1
        elif q1 == q2 and ((n1 == 's' and n2 == 'sdg') or (n1 == 'sdg' and n2 == 's')):
            count += 1
        elif q1 == q2 and n1 == n2 and n1 in ('rx', 'ry', 'rz'):
            try:
                a1 = g1.params[0]
                a2 = g2.params[0]
                if abs(a1 + a2) < 1e-10:
                    count += 1
            except (IndexError, AttributeError):
                pass
    return count / total if total > 0 else 0.0


def compute_commutation_density(circuit: QuantumCircuit) -> float:
    """Compute commutation_density: fraction of adjacent gate pairs on disjoint qubits."""
    data = circuit.data
    if len(data) < 2:
        return 0.0
    count = 0
    total = len(data) - 1
    for i in range(total):
        q1 = set(circuit.find_bit(q).index for q in data[i].qubits)
        q2 = set(circuit.find_bit(q).index for q in data[i + 1].qubits)
        if q1 and q2 and len(q1 & q2) == 0:
            count += 1
    return count / total if total > 0 else 0.0


def predict_reduction(ipd: float, cd: float) -> float:
    """Predict reduction using the multilinear 'Universal Law' model."""
    return 1.102231 * cd + 1.331912 * ipd + 0.001117


# ============================================================================
# 5 NEW circuit family generators
# ============================================================================

def make_shor_mod_exp(n_qubits: int, seed: int = 42) -> QuantumCircuit:
    """Simplified Shor's modular exponentiation circuit.

    Models the core of Shor's algorithm: controlled modular multiplication.
    Uses a simplified version with controlled-SWAP and controlled-addition.
    n_qubits is the size of the work register (total qubits = 2*n_qubits + 1 control).
    """
    rng = np.random.RandomState(seed)
    n_work = max(n_qubits, 3)
    n_total = 2 * n_work + 1  # work register + ancilla register + control
    qc = QuantumCircuit(n_total)
    ctrl = n_total - 1

    # Initialize control in superposition
    qc.h(ctrl)

    # Controlled modular multiplication (simplified)
    a = rng.randint(2, 2**n_work - 1)
    for i in range(n_work):
        if (a >> i) & 1:
            # Controlled-SWAP between work and ancilla qubits
            for j in range(min(n_work, 3)):
                qc.cswap(ctrl, j, n_work + j)

    # Controlled addition (simplified)
    for i in range(n_work - 1):
        qc.ccx(ctrl, i, i + 1)
    for i in range(n_work):
        qc.cx(ctrl, n_work + i)

    # Inverse QFT on work register (simplified)
    for i in range(n_work):
        qc.h(i)
        for j in range(i + 1, n_work):
            qc.cp(-np.pi / 2**(j - i), j, i)

    return qc


def make_ising_transverse(n_qubits: int, depth: int = 3, seed: int = 42) -> QuantumCircuit:
    """Transverse-field Ising model Trotterization.

    H = -J sum(Z_i Z_{i+1}) - h sum(X_i)
    Trotter step: exp(-i*dt*H) ~ prod exp(-i*dt*ZZ) * prod exp(-i*dt*X)
    """
    rng = np.random.RandomState(seed)
    n = max(n_qubits, 3)
    qc = QuantumCircuit(n)
    J = 1.0
    h_field = 0.5
    dt = float(rng.uniform(0.1, 0.5))

    for _ in range(depth):
        # ZZ interaction layer (Ising coupling)
        for i in range(n - 1):
            qc.cx(i, i + 1)
            qc.rz(2 * J * dt, i + 1)
            qc.cx(i, i + 1)

        # Transverse field layer (X rotation)
        for i in range(n):
            qc.rx(2 * h_field * dt, i)

    return qc


def make_qml_classifier(n_qubits: int, layers: int = 3, seed: int = 42) -> QuantumCircuit:
    """Variational quantum classifier (VQC) ansatz.

    Structure: state-prep (Ry rotations) -> variational layers (Ry-CX-Ry pattern).
    """
    rng = np.random.RandomState(seed)
    n = max(n_qubits, 3)
    qc = QuantumCircuit(n)

    # State preparation: encode input features as Ry rotations
    for q in range(n):
        qc.ry(float(rng.uniform(-np.pi, np.pi)), q)
        qc.rz(float(rng.uniform(-np.pi, np.pi)), q)

    # Variational layers
    for layer in range(layers):
        # Entangling layer
        for q in range(n - 1):
            qc.cx(q, q + 1)
        # Wrap-around entanglement for n >= 4
        if n >= 4:
            qc.cx(n - 1, 0)
        # Rotation layer
        for q in range(n):
            qc.ry(float(rng.uniform(-np.pi, np.pi)), q)
            qc.rz(float(rng.uniform(-np.pi, np.pi)), q)

    return qc


def make_qpe(n_qubits: int, seed: int = 42) -> QuantumCircuit:
    """Quantum Phase Estimation circuit.

    Estimates the phase of a controlled-U operation.
    n_qubits = counting register size.
    Target register = 1 qubit (eigenstate of U).
    """
    rng = np.random.RandomState(seed)
    n_count = max(n_qubits, 3)
    n_target = 1
    n_total = n_count + n_target
    qc = QuantumCircuit(n_total)

    target = n_total - 1

    # Prepare eigenstate on target qubit
    theta = float(rng.uniform(0.1, np.pi))
    qc.ry(theta, target)

    # Create superposition on counting register
    for q in range(n_count):
        qc.h(q)

    # Controlled-U^{2^k} operations
    for k in range(n_count):
        reps = 2 ** k
        for _ in range(reps):
            # Controlled phase rotation (simplified U)
            qc.cp(theta, k, target)

    # Inverse QFT on counting register
    for i in range(n_count):
        for j in range(i):
            qc.cp(-np.pi / 2**(i - j), j, i)
        qc.h(i)

    return qc


def make_qaoa_mixer(n_qubits: int, reps: int = 2, seed: int = 42) -> QuantumCircuit:
    """Modified QAOA with non-standard mixer (XY mixer instead of X mixer).

    Standard QAOA uses Rx mixer. This variant uses an XY mixer:
    H_mixer = sum(X_i X_{i+1} + Y_i Y_{i+1})
    This is relevant for constrained optimization problems.
    """
    rng = np.random.RandomState(seed)
    n = max(n_qubits, 3)
    qc = QuantumCircuit(n)

    # Initial state: alternating |01> pattern (Dicken state for constrained problems)
    for q in range(0, n, 2):
        qc.x(q)

    for rep in range(reps):
        gamma = float(rng.uniform(0.05, np.pi / 2))
        beta = float(rng.uniform(0.05, np.pi / 2))

        # Problem unitary: ZZ interactions (MaxCut-like)
        for i in range(n - 1):
            qc.cx(i, i + 1)
            qc.rz(2 * gamma, i + 1)
            qc.cx(i, i + 1)

        # XY mixer: XX + YY interactions
        for i in range(n - 1):
            # exp(-i * beta * (XX + YY)) decomposition
            qc.cx(i, i + 1)
            qc.cx(i + 1, i)
            qc.rx(2 * beta, i)
            qc.rx(2 * beta, i + 1)
            qc.cx(i + 1, i)
            qc.cx(i, i + 1)

    return qc


# ============================================================================
# Main experiment
# ============================================================================

def run_new_families():
    """Run optimizer on 5 new circuit families and validate Universal Law."""

    output_dir = PROJECT_ROOT / "data/v5"
    output_dir.mkdir(parents=True, exist_ok=True)

    families = {
        "Shor": make_shor_mod_exp,
        "Ising": make_ising_transverse,
        "QML": make_qml_classifier,
        "QPE": make_qpe,
        "QAOA_mixer": make_qaoa_mixer,
    }

    sizes = [3, 4, 5, 6, 7]
    seeds = [42, 142, 242, 342, 442]  # 5 seeds per size

    optimizer = HybridCommuteRewrite(success_reduction=0.01)

    rows = []

    for family_name, gen_fn in families.items():
        for n in sizes:
            for seed in seeds:
                try:
                    circuit = gen_fn(n, seed=seed)
                except Exception as e:
                    print(f"  [SKIP] {family_name} n={n} seed={seed}: {e}")
                    continue

                # Compute structural features
                ipd = compute_inverse_pair_density(circuit)
                cd = compute_commutation_density(circuit)

                # Predict reduction using Universal Law
                predicted = predict_reduction(ipd, cd)

                # Measure ACTUAL reduction
                t0 = time.time()
                result = optimizer.optimize(circuit, target=circuit)
                runtime = time.time() - t0

                actual = result.reduction
                prediction_error = actual - predicted

                rows.append({
                    "circuit_family": family_name,
                    "n_qubits": n,
                    "seed": seed,
                    "original_gate_count": result.original_size,
                    "optimized_gate_count": result.optimized_size,
                    "inverse_pair_density": ipd,
                    "commutation_density": cd,
                    "predicted_reduction": predicted,
                    "actual_reduction": actual,
                    "prediction_error": prediction_error,
                    "fidelity": result.fidelity,
                    "runtime_seconds": runtime,
                    "gate_count_total": result.original_size,
                })

    df = pd.DataFrame(rows)
    csv_path = output_dir / "new_families_heldout.csv"
    df.to_csv(csv_path, index=False)

    print(f"\nNew families held-out complete: {len(df)} rows -> {csv_path}")

    # Summary
    print("\n=== Held-out validation: Predicted vs Actual ===")
    for family_name in families.keys():
        sub = df[df["circuit_family"] == family_name]
        if len(sub) == 0:
            continue
        mean_pred = sub["predicted_reduction"].mean()
        mean_actual = sub["actual_reduction"].mean()
        mae = sub["prediction_error"].abs().mean()
        rmse = (sub["prediction_error"] ** 2).mean() ** 0.5
        print(f"  {family_name:15s}: n={len(sub):3d}, predicted={mean_pred:.4f}, "
              f"actual={mean_actual:.4f}, MAE={mae:.4f}, RMSE={rmse:.4f}")

    # Overall metrics
    mae_all = df["prediction_error"].abs().mean()
    rmse_all = (df["prediction_error"] ** 2).mean() ** 0.5
    corr = df[["predicted_reduction", "actual_reduction"]].corr().iloc[0, 1]
    print(f"\n  Overall: MAE={mae_all:.4f}, RMSE={rmse_all:.4f}, Pearson r={corr:.4f}")

    return df


if __name__ == "__main__":
    run_new_families()
