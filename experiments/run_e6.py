"""
E6: Qiskit Transpiler Baseline Comparison Experiment
=====================================================
Compares our Greedy optimizer against Qiskit's built-in transpiler
at optimization levels 0-3 to establish an industrial baseline.

This is a critical missing baseline identified in the postdoctoral audit.
Without this comparison, we cannot claim our greedy optimizer's performance
is meaningful relative to production-grade tools.

Author: Q-research Team
Date: May 2026
"""

import sys
import os
import time
import logging
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.circuits.generator_v2 import (
    CircuitConfig, CircuitFamily, 
    generate_circuit_batch, MetricsCalculator
)
from src.optimisation.optimizers_v2 import (
    OptimizerType, create_optimizer
)
from qiskit import transpile
from qiskit.quantum_info import Statevector, state_fidelity

# Configuration
N_QUBITS = 5
DEPTHS = [5, 10, 15, 20, 25, 30]
N_TRIALS_PER_DEPTH = 30
SEED_BASE = 42
OUTPUT_DIR = Path('data/raw')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def compute_fidelity(original_circuit, optimized_circuit):
    """Compute state fidelity between original and optimized circuits."""
    try:
        sv_orig = Statevector.from_instruction(original_circuit)
        sv_opt = Statevector.from_instruction(optimized_circuit)
        return float(state_fidelity(sv_orig, sv_opt))
    except Exception:
        return np.nan

def count_gates(circuit):
    """Count total gates in a circuit."""
    return sum(1 for _ in circuit)

def run_qiskit_transpile(circuit, opt_level):
    """Run Qiskit transpiler at specified optimization level (no backend)."""
    start = time.time()
    orig_gates = count_gates(circuit)
    try:
        optimized = transpile(circuit, optimization_level=opt_level,
                             seed_transpiler=42)
        runtime = time.time() - start
        opt_gates = count_gates(optimized)
        fidelity = compute_fidelity(circuit, optimized)
        reduction = (orig_gates - opt_gates) / max(orig_gates, 1)
        return {
            'optimizer': f'Qiskit_L{opt_level}',
            'gate_count_orig': orig_gates,
            'gate_count_opt': opt_gates,
            'reduction': reduction,
            'fidelity': fidelity,
            'runtime': runtime,
            'success': reduction >= 0.2 and (fidelity >= 0.99 if not np.isnan(fidelity) else False),
        }
    except Exception as e:
        runtime = time.time() - start
        return {
            'optimizer': f'Qiskit_L{opt_level}',
            'gate_count_orig': orig_gates,
            'gate_count_opt': orig_gates,
            'reduction': 0.0,
            'fidelity': np.nan,
            'runtime': runtime,
            'success': False,
            'error': str(e)[:200],
        }

def run_greedy_optimizer(circuit):
    """Run our Greedy optimizer."""
    start = time.time()
    orig_gates = count_gates(circuit)
    try:
        optimizer = create_optimizer(OptimizerType.GREEDY)
        result = optimizer.optimize(circuit)
        runtime = time.time() - start
        opt_gates = count_gates(result.optimized_circuit)
        fidelity = compute_fidelity(circuit, result.optimized_circuit)
        reduction = result.reduction
        return {
            'optimizer': 'Greedy_Ours',
            'gate_count_orig': orig_gates,
            'gate_count_opt': opt_gates,
            'reduction': reduction,
            'fidelity': fidelity,
            'runtime': runtime,
            'success': result.success,
        }
    except Exception as e:
        runtime = time.time() - start
        return {
            'optimizer': 'Greedy_Ours',
            'gate_count_orig': orig_gates,
            'gate_count_opt': orig_gates,
            'reduction': 0.0,
            'fidelity': np.nan,
            'runtime': runtime,
            'success': False,
            'error': str(e)[:200],
        }

def main():
    metrics_calculator = MetricsCalculator()
    results = []
    total = len(DEPTHS) * N_TRIALS_PER_DEPTH
    count = 0

    logger.info("Starting E6: Qiskit Transpiler Baseline Comparison")
    logger.info(f"  Qubits: {N_QUBITS}, Depths: {DEPTHS}, Trials/depth: {N_TRIALS_PER_DEPTH}")
    logger.info(f"  Total circuits: {total}, Total runs: {total * 5} (4 Qiskit levels + 1 Greedy)")

    for depth in DEPTHS:
        for trial in range(N_TRIALS_PER_DEPTH):
            seed = SEED_BASE + trial * 1000 + depth

            # Generate circuit
            config = CircuitConfig(
                n_qubits=N_QUBITS,
                depth=depth,
                family=CircuitFamily.UNIVERSAL,
                seed=seed,
                entanglement_density=0.3,
            )
            circuits = generate_circuit_batch(config, 1, metrics_calculator)
            circuit, metrics = circuits[0]

            # Qiskit levels 0-3
            for level in range(4):
                result = run_qiskit_transpile(circuit, level)
                result['depth'] = depth
                result['trial'] = trial
                result['seed'] = seed
                result['n_qubits'] = N_QUBITS
                result['entanglement_entropy'] = metrics.entanglement_entropy
                result['normalized_entropy'] = metrics.normalized_entropy
                results.append(result)

            # Our Greedy
            result = run_greedy_optimizer(circuit)
            result['depth'] = depth
            result['trial'] = trial
            result['seed'] = seed
            result['n_qubits'] = N_QUBITS
            result['entanglement_entropy'] = metrics.entanglement_entropy
            result['normalized_entropy'] = metrics.normalized_entropy
            results.append(result)

            count += 1
            if count % 10 == 0:
                logger.info(f"Progress: {count}/{total} ({100*count/total:.1f}%)")

    # Save results
    df = pd.DataFrame(results)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = OUTPUT_DIR / f'exp6_baseline_comparison_{timestamp}.csv'
    df.to_csv(csv_path, index=False)
    logger.info(f"Saved {len(df)} records to {csv_path}")

    # Print summary
    print("\n" + "="*80)
    print("E6 BASELINE COMPARISON SUMMARY")
    print("="*80)
    for opt in sorted(df['optimizer'].unique()):
        sub = df[df['optimizer'] == opt]
        print(f"\n{opt}:")
        print(f"  Mean reduction:  {sub['reduction'].mean():.4f}")
        print(f"  Success rate:    {sub['success'].mean():.4f}")
        print(f"  Mean fidelity:   {sub['fidelity'].dropna().mean():.6f}")
        print(f"  Mean runtime:    {sub['runtime'].mean():.4f} s")
    
    # Per-depth breakdown
    print("\n" + "-"*80)
    print("PER-DEPTH REDUCTION COMPARISON")
    print("-"*80)
    pivot = df.pivot_table(values='reduction', index='depth', columns='optimizer', aggfunc='mean')
    print(pivot.round(4).to_string())
    print("="*80)

if __name__ == '__main__':
    main()
