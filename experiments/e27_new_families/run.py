#!/usr/bin/env python
"""E27: New circuit families for family-mean statistical power improvement.

Generates 5 new structurally distinguishable families, runs them through
Phase-1 greedy, Phase-2a commutation, Phase-2b template pipelines.

New families:
  1. QPE - Quantum Phase Estimation (controlled-U + inverse QFT)
  2. TrotterHamiltonian - product of Pauli rotations
  3. QuantumVolume - random SU(4) blocks on random pairs
  4. WState - distributed entanglement (vs GHZ)
  5. RepetitionCode - 1D QEC encoding + syndrome extraction
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT
from qiskit.quantum_info import random_unitary, Operator

from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase2.commutation_rewriter import CommutationRewriter
from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher

EXPERIMENT_ID = "E27_new_families"
VERSION = "1.0.0"
DATA_DIR = PROJECT_ROOT / "data" / "v8" / "e27_new_families"

SIZES = [3, 4, 5, 6, 8]
DEPTHS = [10, 20, 30]
SEEDS = [1, 2, 3]
SMOKE_SIZES = [3, 5]
SMOKE_DEPTHS = [10]
SMOKE_SEEDS = [1]


def make_qpe(n, seed=42):
    rng = np.random.RandomState(seed)
    if n < 2: n = 2
    counting = n - 1
    qc = QuantumCircuit(n, name=f"QPE_{n}")
    qc.x(counting)
    for i in range(counting):
        qc.h(i)
    for k in range(counting):
        angle = rng.uniform(0, 2 * np.pi)
        for _ in range(2 ** k):
            qc.crz(angle, k, counting)
    qft_inv = QFT(counting).inverse()
    qc.compose(qft_inv, qubits=list(range(counting)), inplace=True)
    return qc


def make_trotter_hamiltonian(n, depth=10, seed=42):
    rng = np.random.RandomState(seed)
    qc = QuantumCircuit(n, name=f"TrotterHam_{n}_d{depth}")
    paulis = ["X", "Y", "Z"]
    for _ in range(depth):
        for q in range(n):
            p = rng.choice(paulis)
            angle = rng.uniform(0, 2 * np.pi)
            if p == "X": qc.rx(angle, q)
            elif p == "Y": qc.ry(angle, q)
            else: qc.rz(angle, q)
        for _ in range(n // 2):
            q1, q2 = rng.choice(n, size=2, replace=False)
            angle = rng.uniform(0, 2 * np.pi)
            qc.cx(q1, q2)
            qc.rz(angle, q2)
            qc.cx(q1, q2)
    return qc


def make_quantum_volume(n, depth=10, seed=42):
    rng = np.random.RandomState(seed)
    qc = QuantumCircuit(n, name=f"QV_{n}_d{depth}")
    layers = max(1, depth // max(n, 1))
    for _ in range(layers):
        order = list(range(n))
        rng.shuffle(order)
        pairs = [(order[i], order[i + 1]) for i in range(0, n - 1, 2)]
        for q1, q2 in pairs:
            su4 = random_unitary(4, seed=rng.randint(0, 2**31))
            qc.unitary(su4, [q1, q2], label=f"SU4")
    return qc


def make_w_state(n, seed=42):
    qc = QuantumCircuit(n, name=f"WState_{n}")
    qc.x(0)
    for i in range(n - 1):
        theta = 2 * np.arccos(np.sqrt(1.0 / (n - i)))
        qc.ry(-theta, i)
        qc.cz(i, i + 1)
        qc.ry(theta, i)
        qc.cx(i, i + 1)
    return qc


def make_repetition_code(n, depth=3, seed=42):
    if n < 4: n = 4
    n_data = n - 2
    n_anc = 2
    qc = QuantumCircuit(n, name=f"RepCode_{n}")
    qc.x(0)
    for i in range(1, n_data):
        qc.cx(0, i)
    for _ in range(depth):
        for a in range(n_anc):
            if a < n_data:
                qc.cx(a, n_data + a)
            if (a + 1) % n_data < n_data:
                qc.cx((a + 1) % n_data, n_data + a)
        for a in range(n_anc):
            qc.h(n_data + a)
            qc.h(n_data + a)
    return qc


FAMILY_GENERATORS = {
    "QPE": lambda n, d, s: make_qpe(n, seed=s),
    "TrotterHamiltonian": lambda n, d, s: make_trotter_hamiltonian(n, depth=d, seed=s),
    "QuantumVolume": lambda n, d, s: make_quantum_volume(n, depth=d, seed=s),
    "WState": lambda n, d, s: make_w_state(n, seed=s),
    "RepetitionCode": lambda n, d, s: make_repetition_code(n, depth=d, seed=s),
}


def _fidelity(optimizer, optimized, original):
    n = original.num_qubits
    if n <= 9:
        return optimizer.calculate_fidelity(optimized, original), "exact"
    try:
        u_o = Operator(optimized).data
        u_r = Operator(original).data
        d = 2 ** n
        tr = abs(np.trace(u_o.conj().T @ u_r)) / d
        return float(tr), "exact_large"
    except Exception:
        return optimizer._estimate_fidelity(optimized, original, n_samples=200), "sampled200"


def run(smoke=False, output_dir=None):
    sizes = SMOKE_SIZES if smoke else SIZES
    depths = SMOKE_DEPTHS if smoke else DEPTHS
    seeds = SMOKE_SEEDS if smoke else SEEDS
    out_dir = output_dir or DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    optimizers = {
        "greedy_phase1": (GreedyGateCancellation(), False),
        "commutation_phase2a": (CommutationRewriter(), False),
        "template_phase2b": (Phase2bTemplateMatcher(), True),
    }

    rows = []
    t_start = time.time()
    run_id = f"e27_{'smoke' if smoke else 'full'}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    for fam_name, gen in sorted(FAMILY_GENERATORS.items()):
        for n in sizes:
            for d in depths:
                for si, seed in enumerate(seeds):
                    try:
                        circuit = gen(n, d, seed)
                    except Exception as exc:
                        print(f"  SKIP {fam_name}(n={n},d={d},s={seed}): {exc}", flush=True)
                        continue
                    for opt_name, (optimizer, use_full) in optimizers.items():
                        try:
                            if use_full:
                                result = optimizer.optimize_full_pipeline(circuit, target=None)
                            else:
                                result = optimizer.optimize(circuit, target=None)
                            fid, fid_method = _fidelity(optimizer, result.optimized_circuit, circuit)
                            meta = result.metadata or {}
                            rows.append({
                                "experiment": EXPERIMENT_ID,
                                "run_id": run_id,
                                "optimizer": opt_name,
                                "circuit_family": fam_name,
                                "n_qubits": circuit.num_qubits,
                                "param_n": n,
                                "depth": d,
                                "original_size": result.original_size,
                                "optimized_size": result.optimized_size,
                                "reduction": result.reduction,
                                "fidelity": fid,
                                "fidelity_method": fid_method,
                                "success": bool(fid >= 0.99),
                                "runtime_seconds": result.runtime_seconds,
                                "seed": seed,
                                "trial": si,
                            })
                        except Exception as exc:
                            print(f"  ERROR {fam_name}(n={n},d={d},s={seed}) {opt_name}: {exc}", flush=True)
                    if len(rows) % 30 == 0 and rows:
                        pd.DataFrame(rows).to_csv(out_dir / "e27_partial.csv", index=False)
                        print(f"  ... {len(rows)} rows ({time.time()-t_start:.0f}s)", flush=True)

    df = pd.DataFrame(rows)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"e27_new_families_{ts}.csv"
    tmp = out_dir / (csv_path.name + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(csv_path)

    canonical = out_dir / "e27_new_families_v8.csv"
    if canonical.exists():
        canonical.replace(out_dir / f"e27_new_families_v8.csv.bak-{ts}")
    df.to_csv(canonical, index=False)

    import qiskit
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
    except Exception:
        git_commit = "unknown"
    metadata = {
        "experiment_id": EXPERIMENT_ID,
        "version": VERSION,
        "description": "5 new circuit families for family-mean statistical power. QPE, TrotterHamiltonian, QuantumVolume, WState, RepetitionCode.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_rows": int(len(df)),
        "mode": "smoke" if smoke else "full",
        "families": sorted(df.circuit_family.unique().tolist()) if len(df) else [],
        "sizes": sizes, "depths": depths, "seeds": seeds,
        "python_version": platform.python_version(),
        "qiskit_version": qiskit.__version__,
        "git_commit": git_commit,
        "canonical_data_file": canonical.name,
        "chunk_file": csv_path.name,
        "fidelity_methods": df.groupby("fidelity_method").size().to_dict() if len(df) else {},
    }
    mp = out_dir / "metadata.json"
    if mp.exists():
        mp.replace(out_dir / f"metadata.json.bak-{ts}")
    tmp3 = out_dir / "metadata.json.tmp"
    with open(tmp3, "w") as f:
        json.dump(metadata, f, indent=2)
    tmp3.replace(mp)

    print(f"\n=== E27 complete: {len(df)} rows -> {canonical}")
    print(f"    Fidelity failures: {len(df[df.fidelity < 0.99]) if len(df) else 0}")
    print(f"    Time: {time.time()-t_start:.0f}s")
    return canonical


def main():
    parser = argparse.ArgumentParser(description=f"{EXPERIMENT_ID} v{VERSION}")
    parser.add_argument("--mode", choices=["smoke", "full"], default="full")
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()
    out = Path(args.output_dir) if args.output_dir else None
    run(smoke=(args.mode == "smoke"), output_dir=out)


if __name__ == "__main__":
    main()
