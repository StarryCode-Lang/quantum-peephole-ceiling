#!/usr/bin/env python
"""
WCL Full 15-Family Validation Experiment
========================================

Review gap (MEDIUM -> FATAL if WCL changes ceiling on structured families):
  E19 (WCL validation) is limited to random Universal circuits only.  If WCL
  changes the Phase-1 ceiling on structured families, the LBL-based trichotomy
  may be partially a listing artifact.

This script closes that gap by running the WCL vs LBL comparison across ALL
15 circuit families at canonical sizes, with multiple trials per family for
statistical power.

For each circuit:
  - LBL mode: GreedyGateCancellation(wire_traversal=False)  -> Phase-1 on
    the as-listed (layer-by-layer) circuit.
  - WCL mode: GreedyGateCancellation(wire_traversal=True)   -> Phase-1 after
    WireTraversalPreprocessor reorders gates into wire-consecutive listing.

Output: data/v6/e27_wcl_full_family/

Usage:
  python experiments/wcl_full_family.py --mode full
  python experiments/wcl_full_family.py --mode smoke
  python experiments/wcl_full_family.py --help
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

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
from src.provenance import file_sha256, run_metadata

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EXPERIMENT_ID = "E27_wcl_full_family"
VERSION = "1.1.0"
SCHEMA_VERSION = "1.1.0"

SIZES_FULL = [4, 6, 8]
SIZES_SMOKE = [4, 6]

N_TRIALS_RANDOM_FULL = 10
N_TRIALS_RANDOM_SMOKE = 3

N_TRIALS_ALGO_FULL = 10
N_TRIALS_ALGO_SMOKE = 3


# ---------------------------------------------------------------------------
# Circuit family registry (all 15 families)
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

# Families where multi-trial variation matters (stochastic generation)
RANDOM_FAMILIES = {"Universal", "RandomClifford", "Structured"}
# Families with seed-dependent parameters (variational ansatze)
SEED_DEPENDENT_FAMILIES = {
    "BV", "QAOA", "VQE", "HardwareEfficient", "SurfaceCode",
    "UCCSD_inspired", "Grover", "Adder", "QuantumWalk", "IQP",
}


def _generate_circuit(family_name: str, n: int, seed: int,
                      metrics_calc: MetricsCalculator):
    """Generate a single circuit for the given family at size n."""
    info = FAMILY_REGISTRY[family_name]
    gen = info["generator"]

    if gen == "random_universal":
        config = CircuitConfig(
            n_qubits=n, depth=max(20, 2 * n),
            family=CircuitFamily.UNIVERSAL,
            seed=seed, entanglement_density=0.3,
        )
        circuits = generate_circuit_batch(config, 1, metrics_calc)
        circuit, metrics = circuits[0]
        return circuit, metrics

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
        circuit, metrics = circuits[0]
        return circuit, metrics

    if gen == "bv_oracle":
        rng = np.random.RandomState(seed)
        secret = int(rng.randint(0, 1 << n))
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

    raise ValueError(f"Unknown generator for family {family_name}: {gen}")


# ---------------------------------------------------------------------------
# Main experiment runner
# ---------------------------------------------------------------------------

def run(mode: str = "full", families: list[str] | None = None,
        output_dir: Path | None = None) -> pd.DataFrame:
    """Run the WCL vs LBL comparison across all 15 families."""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "experiments" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Capture provenance
    meta = run_metadata(PROJECT_ROOT, Path(__file__), VERSION,
                        f"{EXPERIMENT_ID}_{mode}")
    script_hash = file_sha256(Path(__file__))

    is_smoke = mode == "smoke"
    sizes = SIZES_SMOKE if is_smoke else SIZES_FULL
    n_trials_random = N_TRIALS_RANDOM_SMOKE if is_smoke else N_TRIALS_RANDOM_FULL
    n_trials_algo = N_TRIALS_ALGO_SMOKE if is_smoke else N_TRIALS_ALGO_FULL

    if families is None:
        families = list(FAMILY_REGISTRY.keys())

    # Two listing models
    optimizers = {
        "LBL": GreedyGateCancellation(
            success_reduction=0.01, wire_traversal=False),
        "WCL": GreedyGateCancellation(
            success_reduction=0.01, wire_traversal=True),
    }

    metrics_calc = MetricsCalculator()
    wcl_preprocessor = WireTraversalPreprocessor()
    results = []

    # Count total rows
    total_rows = 0
    for fam in families:
        n_trials = n_trials_random if fam in RANDOM_FAMILIES else n_trials_algo
        total_rows += len(sizes) * n_trials * 2  # 2 listing models

    run_id = f"e27_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    print(f"E27 WCL Full Family: {mode} mode")
    print(f"  Families: {len(families)}")
    print(f"  Total rows (planned): {total_rows}")
    print(f"  Output: {output_dir}")

    with tqdm(total=total_rows, desc="E27 WCL") as pbar:
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
                        pbar.update(2)
                        continue

                    original_size = circuit.size()
                    if original_size == 0:
                        pbar.update(2)
                        continue

                    # Also compute WCL-preprocessed circuit size
                    # (for structural analysis)
                    wcl_circuit = wcl_preprocessor.preprocess(circuit)
                    wcl_listing_changed = (
                        [circuit.find_bit(q).index for inst in circuit.data
                         for q in inst.qubits] !=
                        [wcl_circuit.find_bit(q).index for inst in wcl_circuit.data
                         for q in inst.qubits]
                    )

                    for listing_model, opt in optimizers.items():
                        t0 = time.time()
                        result = opt.optimize(circuit, target=circuit)
                        runtime = time.time() - t0

                        results.append({
                            "schema_version": SCHEMA_VERSION,
                            "experiment_id": EXPERIMENT_ID,
                            "run_id": run_id,
                            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "mode": mode,
                            "circuit_family": fam,
                            "n_qubits": circuit.num_qubits,
                            "param_n": n,
                            "depth": circuit.depth(),
                            "gate_count": metrics.gate_count,
                            "entanglement_entropy": getattr(
                                metrics, "entanglement_entropy", None),
                            "trial": trial,
                            "seed": seed,
                            "optimizer": "greedy_gate_cancellation",
                            "listing_model": listing_model,
                            "wire_traversal": listing_model == "WCL",
                            "original_size": original_size,
                            "optimized_size": result.optimized_size,
                            "reduction": result.reduction,
                            "fidelity": result.fidelity,
                            "success": bool(result.success),
                            "runtime_seconds": runtime,
                            "wcl_listing_reordered": wcl_listing_changed,
                            "file_sha256": script_hash,
                            "git_commit": meta.get("git_commit", ""),
                        })
                        pbar.update(1)

    df = pd.DataFrame(results)

    # Save CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"wcl_full_family_{mode}_{timestamp}.csv"
    df.to_csv(csv_path, index=False)

    # Save metadata
    metadata = {
        "experiment_id": EXPERIMENT_ID,
        "version": VERSION,
        "mode": mode,
        "run_id": run_id,
        "description": (
            "WCL vs LBL across all 15 families. Closes gap: E19 was "
            "random Universal only."
        ),
        "listing_models": ["LBL", "WCL"],
        "families_run": families,
        "n_families": len(families),
        "sizes": sizes,
        "n_trials_random": n_trials_random,
        "n_trials_algo": n_trials_algo,
        "total_rows": len(df),
        "canonical_data_file": csv_path.name,
        "script_sha256": script_hash,
        "provenance": meta,
        "review_gap_closed": (
            "MEDIUM->FATAL: WCL validation limited to random Universal. "
            "If WCL changes ceiling on structured families, trichotomy "
            "may be listing artifact. This experiment tests all 15 families."
        ),
        "timestamp": datetime.now().isoformat(),
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nE27 complete: {len(df)} rows -> {csv_path}")

    from scipy import stats as sp_stats

    # Print summary
    print("\n=== Per-family mean reduction by listing model ===")
    for fam in families:
        sub = df[df["circuit_family"] == fam]
        if sub.empty:
            continue
        lbl = sub[sub["listing_model"] == "LBL"]
        wcl = sub[sub["listing_model"] == "WCL"]
        lbl_mean = lbl["reduction"].mean() if len(lbl) else 0.0
        wcl_mean = wcl["reduction"].mean() if len(wcl) else 0.0
        gap = wcl_mean - lbl_mean
        changed = sub["wcl_listing_reordered"].any()
        # Wilcoxon signed-rank: WCL > LBL?
        lbl_vals = lbl["reduction"].values
        wcl_vals = wcl["reduction"].values
        min_len = min(len(lbl_vals), len(wcl_vals))
        if min_len >= 5 and np.any(wcl_vals[:min_len] - lbl_vals[:min_len] != 0):
            w_stat, p_val = sp_stats.wilcoxon(wcl_vals[:min_len], lbl_vals[:min_len],
                                              alternative="greater")
            sig = "***" if p_val < 0.001 else ("**" if p_val < 0.01 else ("*" if p_val < 0.05 else ""))
            print(f"  [{fam}] LBL={lbl_mean:.6f} WCL={wcl_mean:.6f} "
                  f"gap={gap:+.6f} W={w_stat:.0f} p={p_val:.4e} {sig}"
                  f" reordered={'Y' if changed else 'N'} (n={min_len})")
        else:
            print(f"  [{fam}] LBL={lbl_mean:.6f} WCL={wcl_mean:.6f} "
                  f"gap={gap:+.6f} reordered={'Y' if changed else 'N'} "
                  f"(n={len(sub)//2})")

    # Key finding
    print("\n=== Key Result ===")
    families_with_gap = []
    for fam in families:
        sub = df[df["circuit_family"] == fam]
        if sub.empty:
            continue
        lbl = sub[sub["listing_model"] == "LBL"]["reduction"].mean()
        wcl = sub[sub["listing_model"] == "WCL"]["reduction"].mean()
        if wcl - lbl > 0.001:
            families_with_gap.append((fam, wcl - lbl))
    if families_with_gap:
        print(f"  {len(families_with_gap)} families show WCL > LBL gap:")
        for fam, gap in families_with_gap:
            print(f"    {fam}: gap = {gap:.6f}")
    else:
        print("  No family shows significant WCL > LBL gap.")

    return df


def main():
    parser = argparse.ArgumentParser(
        description="E27: WCL Full 15-Family Validation "
                    "(closes gap: WCL was random Universal only)")
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
