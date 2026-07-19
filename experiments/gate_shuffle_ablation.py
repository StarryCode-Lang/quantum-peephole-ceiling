#!/usr/bin/env python
"""
Gate-Order Shuffle Ablation Experiment
=======================================

Review gap (MEDIUM -> FATAL if random shuffle matches structured optimization):
  The manuscript admits (Section 6.3.11): "No random gate shuffler control was
  performed. A random permutation of gates (preserving unitary equivalence via
  commutation) would test whether the optimizers are doing anything
  distinguishable from randomness."

This script closes that gap by running a controlled ablation:
  For each circuit C, we compare:
    1. ORIGINAL listing  -- the circuit as generated (natural structure)
    2. SHUFFLED listing   -- a random commutation-preserving permutation of
       the gate order (unitarily equivalent but listing-scrambled)
    3. WCL listing        -- Wire-Consecutive Listing (structured reorder)

  Under all three listing models, we run:
    - Phase-1 (GreedyGateCancellation, wire_traversal=False)
    - Phase-2a (CommutationRewriter)

  The key hypothesis:
    H0 (null): The listing-model sensitivity is an artifact of random gate
    placement, not circuit structure. Under a random shuffle, optimizers
    achieve the same reduction as under the original listing.
    H1 (alt):  The listing-model sensitivity is structural. The original listing
    produces measurably different reduction than a random shuffle, and WCL
    produces measurably different reduction than a random shuffle.

  If H0 holds (shuffle reduction == original reduction), the "listing model
  matters" claim is weakened. If H1 holds (shuffle reduction != original),
  the claim is strengthened: the structure of the listing, not mere gate
  order, determines optimizer behavior.

Output: data/v6/e28_gate_shuffle_ablation/

Usage:
  python experiments/gate_shuffle_ablation.py --mode full
  python experiments/gate_shuffle_ablation.py --mode smoke
  python experiments/gate_shuffle_ablation.py --help
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from qiskit import QuantumCircuit

from src.circuits.generator_v2 import (
    CircuitConfig, CircuitFamily, StructureType,
    generate_circuit_batch, MetricsCalculator,
)
from src.circuits.real_benchmarks import (
    make_qft, make_ghz, make_cnot_chain,
    make_bernstein_vazirani, make_qaoa_line, make_vqe_twolocal,
    make_hardware_efficient, make_surface_code_syndrome,
    make_parameterized_ansatz, make_grover, make_quantum_adder,
    make_quantum_walk, make_iqp, make_random_clifford,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor
from src.optimisation.phase2.commutation_rewriter import CommutationRewriter
from src.optimisation.base import BaseOptimizer, OptimizationResult
from src.provenance import file_sha256, run_metadata

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EXPERIMENT_ID = "E28_gate_shuffle_ablation"
VERSION = "1.1.0"

SIZES_FULL = [6]
SIZES_SMOKE = [6]

N_TRIALS_RANDOM_FULL = 10
N_TRIALS_RANDOM_SMOKE = 3

N_TRIALS_ALGO_FULL = 10
N_TRIALS_ALGO_SMOKE = 3

N_SHUFFLES_FULL = 5
N_SHUFFLES_SMOKE = 2

# ---------------------------------------------------------------------------
# Commutation-preserving random shuffle
# ---------------------------------------------------------------------------

class GateShuffler(BaseOptimizer):
    """Randomly permute circuit gate order preserving unitary equivalence.

    Uses a dependency-DAG topological sort with random priorities.  Two gates
    that share a qubit are never reordered relative to each other (they are
    dependent).  Gates on disjoint qubits can be swapped freely (they commute).
    The result is a random linear extension of the partial order defined by
    qubit-sharing dependencies, which is always unitarily equivalent to the
    original circuit.

    Multiple shuffles with different seeds produce different random linear
    extensions, allowing us to sample the distribution of optimizer outcomes
    over listing-equivalent circuits.
    """

    def __init__(self, random_seed: int = 42):
        super().__init__(random_seed=random_seed)

    def optimize(self, circuit: QuantumCircuit,
                 target: QuantumCircuit | None = None) -> OptimizationResult:
        """Return a randomly shuffled (but unitarily equivalent) circuit."""
        n_gates = len(circuit.data)
        start = time.time()

        if n_gates <= 1:
            return OptimizationResult(
                optimized_circuit=circuit.copy(),
                original_size=circuit.size(),
                optimized_size=circuit.size(),
                fidelity=1.0, iterations=0,
                runtime_seconds=time.time() - start,
                success=True, metadata={"algorithm": "gate_shuffler"}
            )

        # Build dependency DAG: edges between consecutive gates on same qubit
        qubit_to_gates: dict[int, list[int]] = {}
        for idx, inst in enumerate(circuit.data):
            for q in self._get_qubit_indices(circuit, inst):
                qubit_to_gates.setdefault(q, []).append(idx)

        in_degree = [0] * n_gates
        adj: dict[int, list[int]] = {}
        edges = set()
        for _q, gates_on_q in qubit_to_gates.items():
            for k in range(len(gates_on_q) - 1):
                i, j = gates_on_q[k], gates_on_q[k + 1]
                if (i, j) not in edges:
                    edges.add((i, j))
                    adj.setdefault(i, []).append(j)
                    in_degree[j] += 1

        # Random-priority topological sort (Kahn's algorithm with random heap)
        import heapq
        heap = []
        available = [i for i in range(n_gates) if in_degree[i] == 0]
        # Use random priorities
        priorities = self.rng.permutation(n_gates)
        for i in available:
            heapq.heappush(heap, (priorities[i], i))

        order: list[int] = []
        while heap:
            _, idx = heapq.heappop(heap)
            order.append(idx)
            for j in adj.get(idx, []):
                in_degree[j] -= 1
                if in_degree[j] == 0:
                    heapq.heappush(heap, (priorities[j], j))

        # Safety: if cycle (shouldn't happen), fall back to original
        if len(order) != n_gates:
            order = list(range(n_gates))

        result_circuit = circuit.copy()
        result_circuit.data = [circuit.data[i] for i in order]

        return OptimizationResult(
            optimized_circuit=result_circuit,
            original_size=circuit.size(),
            optimized_size=result_circuit.size(),
            fidelity=1.0,  # unitarily equivalent by construction
            iterations=0,
            runtime_seconds=time.time() - start,
            success=True,
            metadata={"algorithm": "gate_shuffler", "n_gates": n_gates},
        )


# ---------------------------------------------------------------------------
# Circuit family registry
# ---------------------------------------------------------------------------

FAMILY_REGISTRY: dict[str, dict] = {
    "Universal": {"generator": "random_universal"},
    "RandomClifford": {"generator": "random_clifford"},
    "Structured": {"generator": "structured_brickwork"},
    "QFT": {"generator": make_qft},
    "GHZ": {"generator": make_ghz},
    "CNOT_chain": {"generator": make_cnot_chain},
    "BV": {"generator": "bv_oracle"},
    "QAOA": {"generator": make_qaoa_line},
    "VQE": {"generator": make_vqe_twolocal},
    "HardwareEfficient": {"generator": make_hardware_efficient},
    "SurfaceCode": {"generator": make_surface_code_syndrome},
    "UCCSD_inspired": {"generator": make_parameterized_ansatz},
    "Grover": {"generator": make_grover},
    "Adder": {"generator": make_quantum_adder},
    "QuantumWalk": {"generator": make_quantum_walk},
    "IQP": {"generator": make_iqp},
}

RANDOM_FAMILIES = {"Universal", "RandomClifford", "Structured"}


def _generate_circuit(family_name: str, n: int, seed: int,
                      metrics_calc: MetricsCalculator):
    """Generate a single circuit for the given family."""
    info = FAMILY_REGISTRY[family_name]
    gen = info["generator"]

    if gen == "random_universal":
        config = CircuitConfig(
            n_qubits=n, depth=max(20, 2 * n),
            family=CircuitFamily.UNIVERSAL,
            seed=seed, entanglement_density=0.3,
        )
        circuits = generate_circuit_batch(config, 1, metrics_calc)
        return circuits[0]  # (circuit, metrics) tuple

    if gen == "random_clifford":
        circuit = make_random_clifford(n, depth=max(20, 2 * n), seed=seed)
        metrics = metrics_calc.calculate(circuit)
        return circuit, metrics

    if gen == "structured_brickwork":
        config = CircuitConfig(
            n_qubits=n, depth=max(20, 2 * n),
            family=CircuitFamily.STRUCTURED,
            seed=seed, entanglement_density=0.3,
            structure_type=StructureType.BRICKWORK,
        )
        circuits = generate_circuit_batch(config, 1, metrics_calc)
        return circuits[0]  # (circuit, metrics) tuple

    if gen == "bv_oracle":
        circuit = make_bernstein_vazirani(n, seed=seed)
        metrics = metrics_calc.calculate(circuit)
        return circuit, metrics

    if callable(gen):
        try:
            circuit = gen(n, seed=seed)
        except TypeError:
            circuit = gen(n)
        metrics = metrics_calc.calculate(circuit)
        return circuit, metrics

    raise ValueError(f"Unknown generator: {gen}")


# ---------------------------------------------------------------------------
# Main experiment runner
# ---------------------------------------------------------------------------

def run(mode: str = "full", families: list[str] | None = None,
        output_dir: Path | None = None) -> pd.DataFrame:
    """Run the gate-shuffle ablation across all 15 families."""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "experiments" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    meta = run_metadata(PROJECT_ROOT, Path(__file__), VERSION,
                        f"{EXPERIMENT_ID}_{mode}")
    script_hash = file_sha256(Path(__file__))

    is_smoke = mode == "smoke"
    sizes = SIZES_SMOKE if is_smoke else SIZES_FULL
    n_trials_random = N_TRIALS_RANDOM_SMOKE if is_smoke else N_TRIALS_RANDOM_FULL
    n_trials_algo = N_TRIALS_ALGO_SMOKE if is_smoke else N_TRIALS_ALGO_FULL
    n_shuffles = N_SHUFFLES_SMOKE if is_smoke else N_SHUFFLES_FULL

    if families is None:
        families = list(FAMILY_REGISTRY.keys())

    # Listing models: original, shuffled (x N_SHUFFLES), WCL
    # Optimizers: greedy_phase1, commutation_phase2a
    greedy_lbl = GreedyGateCancellation(
        success_reduction=0.01, wire_traversal=False)
    greedy_wcl = GreedyGateCancellation(
        success_reduction=0.01, wire_traversal=True)
    commutation = CommutationRewriter()

    wcl_preprocessor = WireTraversalPreprocessor()
    metrics_calc = MetricsCalculator()
    results = []

    # 3 listing conditions: original, WCL, shuffled (x n_shuffles)
    # 2 optimizers per listing condition: greedy, commutation
    # Total per circuit = (2 + n_shuffles) * 2
    listing_conditions = 2 + n_shuffles  # original + wcl + shuffles
    optimizers_per_circuit = 2
    total_per_circuit = listing_conditions * optimizers_per_circuit

    # Count total rows
    total_rows = 0
    for fam in families:
        n_trials = n_trials_random if fam in RANDOM_FAMILIES else n_trials_algo
        total_rows += len(sizes) * n_trials * total_per_circuit

    run_id = f"e28_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    print(f"E28 Gate-Order Shuffle Ablation: {mode} mode")
    print(f"  Families: {len(families)}")
    print(f"  Shuffles per circuit: {n_shuffles}")
    print(f"  Total rows (planned): {total_rows}")
    print(f"  Output: {output_dir}")

    with tqdm(total=total_rows, desc="E28 Shuffle") as pbar:
        for fam in families:
            n_trials = (n_trials_random if fam in RANDOM_FAMILIES
                        else n_trials_algo)

            for trial in range(n_trials):
                for n in sizes:
                    seed = 42 + trial * 1000 + n
                    try:
                        circuit, metrics = _generate_circuit(
                            fam, n, seed, metrics_calc)
                    except Exception as exc:
                        print(f"  Warning: {fam}(n={n}, trial={trial}) "
                              f"failed: {exc}")
                        pbar.update(total_per_circuit)
                        continue

                    original_size = circuit.size()
                    if original_size == 0:
                        pbar.update(total_per_circuit)
                        continue

                    # Prepare listing variants
                    wcl_circuit = wcl_preprocessor.preprocess(circuit)

                    # Generate shuffled variants
                    shuffled_circuits = []
                    for sh_idx in range(n_shuffles):
                        shuffler = GateShuffler(random_seed=seed * 100 + sh_idx)
                        sh_result = shuffler.optimize(circuit)
                        shuffled_circuits.append(sh_result.optimized_circuit)

                    # Run optimizers on each listing variant
                    listing_variants = [
                        ("original", circuit),
                        ("wcl", wcl_circuit),
                    ]
                    for sh_idx, sc in enumerate(shuffled_circuits):
                        listing_variants.append((f"shuffle_{sh_idx}", sc))

                    for listing_label, variant_circuit in listing_variants:
                        # Greedy Phase-1 (LBL, no wire traversal)
                        # -- tests the raw listing effect
                        t0 = time.time()
                        r1 = greedy_lbl.optimize(variant_circuit, target=circuit)
                        rt1 = time.time() - t0
                        results.append({
                            "experiment_id": EXPERIMENT_ID,
                            "run_id": run_id,
                            "mode": mode,
                            "circuit_family": fam,
                            "n_qubits": circuit.num_qubits,
                            "param_n": n,
                            "trial": trial,
                            "seed": seed,
                            "listing_model": listing_label,
                            "optimizer": "greedy_phase1_lbl",
                            "original_size": original_size,
                            "variant_size": variant_circuit.size(),
                            "optimized_size": r1.optimized_size,
                            "reduction": r1.reduction,
                            "fidelity": r1.fidelity,
                            "success": bool(r1.success),
                            "runtime_seconds": rt1,
                            "file_sha256": script_hash,
                            "git_commit": meta.get("git_commit", ""),
                        })
                        pbar.update(1)

                        # Commutation Phase-2a
                        t0 = time.time()
                        r2 = commutation.optimize(variant_circuit, target=circuit)
                        rt2 = time.time() - t0
                        results.append({
                            "experiment_id": EXPERIMENT_ID,
                            "run_id": run_id,
                            "mode": mode,
                            "circuit_family": fam,
                            "n_qubits": circuit.num_qubits,
                            "param_n": n,
                            "trial": trial,
                            "seed": seed,
                            "listing_model": listing_label,
                            "optimizer": "commutation_phase2a",
                            "original_size": original_size,
                            "variant_size": variant_circuit.size(),
                            "optimized_size": r2.optimized_size,
                            "reduction": r2.reduction,
                            "fidelity": r2.fidelity,
                            "success": bool(r2.success),
                            "runtime_seconds": rt2,
                            "file_sha256": script_hash,
                            "git_commit": meta.get("git_commit", ""),
                        })
                        pbar.update(1)

    df = pd.DataFrame(results)

    # Save CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"gate_shuffle_ablation_{mode}_{timestamp}.csv"
    df.to_csv(csv_path, index=False)

    # Save metadata
    metadata = {
        "experiment_id": EXPERIMENT_ID,
        "version": VERSION,
        "mode": mode,
        "run_id": run_id,
        "description": (
            "Gate-order shuffle ablation: tests whether listing-model "
            "sensitivity is structural or a random-order artifact."
        ),
        "listing_models": ["original", "wcl"] + [
            f"shuffle_{i}" for i in range(n_shuffles)],
        "optimizers": ["greedy_phase1_lbl", "commutation_phase2a"],
        "families_run": families,
        "n_families": len(families),
        "sizes": sizes,
        "n_shuffles_per_circuit": n_shuffles,
        "n_trials_random": n_trials_random,
        "n_trials_algo": n_trials_algo,
        "total_rows": len(df),
        "canonical_data_file": csv_path.name,
        "script_sha256": script_hash,
        "provenance": meta,
        "review_gap_closed": (
            "MEDIUM->FATAL: Manuscript admits no random gate shuffler "
            "control (Section 6.3.11). This ablation tests whether the "
            "listing-model sensitivity is distinguishable from randomness."
        ),
        "hypotheses": {
            "H0": "Listing-model sensitivity is a random-order artifact. "
                  "Shuffle reduction == original reduction.",
            "H1": "Listing-model sensitivity is structural. Original != "
                  "shuffle, and WCL != shuffle.",
        },
        "timestamp": datetime.now().isoformat(),
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nE28 complete: {len(df)} rows -> {csv_path}")

    from scipy import stats as sp_stats

    # Print summary
    print("\n=== Per-family mean reduction by listing model ===")
    for fam in families:
        sub = df[df["circuit_family"] == fam]
        if sub.empty:
            continue
        for opt in ["greedy_phase1_lbl", "commutation_phase2a"]:
            s = sub[sub["optimizer"] == opt]
            orig = s[s["listing_model"] == "original"]["reduction"]
            shuffles = s[s["listing_model"].str.startswith("shuffle_")]["reduction"]
            wcl = s[s["listing_model"] == "wcl"]["reduction"]
            orig_m = orig.mean() if len(orig) else 0.0
            shuf_m = shuffles.mean() if len(shuffles) else 0.0
            wcl_m = wcl.mean() if len(wcl) else 0.0
            print(f"  [{fam}] {opt}: orig={orig_m:.6f} "
                  f"shuf={shuf_m:.6f} wcl={wcl_m:.6f}")

    # Key ablation result: Wilcoxon for original vs shuffle (paired)
    print("\n=== Ablation Key Result (Wilcoxon signed-rank) ===")
    for opt in ["greedy_phase1_lbl", "commutation_phase2a"]:
        s = df[df["optimizer"] == opt]
        orig = s[s["listing_model"] == "original"]["reduction"].values
        shuf = s[s["listing_model"].str.startswith("shuffle_")]["reduction"].values
        wcl = s[s["listing_model"] == "wcl"]["reduction"].values
        if len(orig) >= 5 and len(shuf) >= 5:
            min_len = min(len(orig), len(shuf))
            diff = orig[:min_len] - shuf[:min_len]
            if np.any(diff != 0):
                w_stat, p_val = sp_stats.wilcoxon(orig[:min_len], shuf[:min_len], alternative="two-sided")
            else:
                w_stat, p_val = 0.0, 1.0
            cohens_d = ((orig.mean() - shuf.mean()) /
                        np.sqrt((orig.var() + shuf.var()) / 2))
            print(f"  {opt}: orig={orig.mean():.6f} vs shuf={shuf.mean():.6f} "
                  f"W={w_stat:.0f} p={p_val:.4e} d={cohens_d:.3f}")
        if len(orig) >= 5 and len(wcl) >= 5:
            min_len = min(len(orig), len(wcl))
            diff = orig[:min_len] - wcl[:min_len]
            if np.any(diff != 0):
                w_stat, p_val = sp_stats.wilcoxon(orig[:min_len], wcl[:min_len], alternative="two-sided")
            else:
                w_stat, p_val = 0.0, 1.0
            print(f"  {opt}: orig={orig.mean():.6f} vs wcl={wcl.mean():.6f} "
                  f"W={w_stat:.0f} p={p_val:.4e}")

    return df


def main():
    parser = argparse.ArgumentParser(
        description="E28: Gate-Order Shuffle Ablation "
                    "(closes gap: no random shuffler control, Sec 6.3.11)")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke",
                        help="Smoke (quick check) or full experiment")
    parser.add_argument("--families", type=str, default=None,
                        help="Comma-separated family names (default: all 15)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Override output directory")
    args = parser.parse_args()

    fams = None
    if args.families:
        fams = [f.strip() for f in args.families.split(",")]
        for f in fams:
            if f not in FAMILY_REGISTRY:
                print(f"Error: unknown family '{f}'. "
                      f"Available: {list(FAMILY_REGISTRY.keys())}")
                sys.exit(1)

    out_dir = Path(args.output_dir) if args.output_dir else None
    run(mode=args.mode, families=fams, output_dir=out_dir)


if __name__ == "__main__":
    main()
