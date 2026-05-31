"""
Quantum Circuit Phase Transition Experiments - COMPLETELY REDESIGNED
====================================================================

Research Question: Do random quantum circuits exhibit phase transitions in 
entanglement entropy as circuit depth increases?

Background:
- Random quantum circuits are known to generate entanglement as depth increases
- For shallow circuits, entanglement entropy grows linearly with depth
- At a critical depth, entanglement saturates at the Page value
- This transition has been studied theoretically (Harrow & Low 2009, 
  Nahum et al. 2017, Skinner et al. 2019) but systematic numerical 
  verification with scaling analysis is lacking

This experiment:
1. Measures exact von Neumann entropy S(d) for random circuits
2. Detects critical depth d_c where S saturates
3. Studies scaling of d_c with qubit count n
4. Analyzes the relationship between entanglement and circuit structure
5. Examines the connection to optimization landscape properties
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from datetime import datetime
from tqdm import tqdm
import time
import json

from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Statevector, partial_trace, entropy
from src.analysis.analysis_tools import PhaseTransitionDetector, CriticalExponentEstimator


def compute_entanglement_entropy(circuit: QuantumCircuit, n_qubits: int) -> float:
    """Compute exact von Neumann entropy of reduced state on first half."""
    try:
        sv = Statevector.from_label('0' * n_qubits).evolve(circuit)
        n_A = n_qubits // 2
        rho_A = partial_trace(sv, list(range(n_A, n_qubits)))
        return float(entropy(rho_A, base=2))
    except Exception as e:
        return 0.0


def compute_bipartite_mutual_info(circuit: QuantumCircuit, n_qubits: int) -> float:
    """Compute mutual information between two halves of the system."""
    try:
        sv = Statevector.from_label('0' * n_qubits).evolve(circuit)
        n_A = n_qubits // 2
        
        rho_A = partial_trace(sv, list(range(n_A, n_qubits)))
        rho_B = partial_trace(sv, list(range(n_A)))
        rho_AB = sv.to_operator()
        
        S_A = entropy(rho_A, base=2)
        S_B = entropy(rho_B, base=2)
        S_AB = entropy(rho_AB, base=2)
        
        return float(S_A + S_B - S_AB)
    except:
        return 0.0


def generate_random_circuit(n_qubits: int, depth: int, 
                           two_qubit_ratio: float = 0.3,
                           seed: int = 0) -> QuantumCircuit:
    """Generate a random quantum circuit with controlled parameters."""
    np.random.seed(seed)
    qr = QuantumRegister(n_qubits, 'q')
    qc = QuantumCircuit(qr)
    
    for layer in range(depth):
        for q in range(n_qubits):
            if np.random.random() < two_qubit_ratio and q < n_qubits - 1:
                qc.cx(q, q + 1)
            else:
                gate = np.random.choice(['h', 't', 'rz'])
                if gate == 'h':
                    qc.h(q)
                elif gate == 't':
                    qc.t(q)
                elif gate == 'rz':
                    qc.rz(np.random.uniform(0, 2 * np.pi), q)
    return qc


def run_experiment_1_entanglement_vs_depth():
    """
    Experiment 1: Entanglement entropy as a function of circuit depth.
    
    For each (n, depth), generate multiple random circuits and measure
    the exact von Neumann entropy of the reduced density matrix.
    
    Expected result: S(d) grows linearly then saturates at Page value ~ n/2 - 1.
    """
    print("=" * 60)
    print("EXPERIMENT 1: Entanglement Entropy vs Depth")
    print("=" * 60)
    
    results = []
    n_qubits_list = [3, 4, 5, 6, 7, 8]
    depths = list(range(1, 31)) + [40, 50]
    n_trials = 30  # More trials for better statistics
    
    total = len(n_qubits_list) * len(depths) * n_trials
    print(f"Total circuits: {total}")
    
    with tqdm(total=total, desc="Exp1") as pbar:
        for n in n_qubits_list:
            # Maximum possible entanglement entropy (Page value)
            max_entropy = (n // 2) - (1 / (2 ** (n - 1) * np.log(2)))  # Page formula
            
            for depth in depths:
                entropies = []
                for trial in range(n_trials):
                    seed = n * 100000 + depth * 1000 + trial
                    qc = generate_random_circuit(n, depth, two_qubit_ratio=0.3, seed=seed)
                    
                    S = compute_entanglement_entropy(qc, n)
                    entropies.append(S)
                    
                    results.append({
                        'experiment': 1,
                        'n_qubits': n,
                        'depth': depth,
                        'trial': trial,
                        'seed': seed,
                        'entanglement_entropy': S,
                        'max_entropy': max_entropy,
                        'normalized_entropy': S / max_entropy if max_entropy > 0 else 0,
                        'gate_count': qc.size(),
                        'two_qubit_gates': sum(1 for inst in qc.data if inst.operation.num_qubits == 2),
                    })
                    pbar.update(1)
                
                # Print summary for this (n, depth)
                mean_S = np.mean(entropies)
                std_S = np.std(entropies)
                if depth in [1, 5, 10, 20, 50] or depth == depths[-1]:
                    print(f"  n={n}, depth={depth:2d}: S={mean_S:.3f} ± {std_S:.3f} (max={max_entropy:.3f})")
    
    df = pd.DataFrame(results)
    return df


def run_experiment_2_two_qubit_ratio_sweep():
    """
    Experiment 2: Effect of two-qubit gate ratio on entanglement.
    
    Fix n and depth, vary the fraction of two-qubit gates.
    Expected: Higher two_qubit_ratio → faster entanglement generation.
    """
    print("\n" + "=" * 60)
    print("EXPERIMENT 2: Two-Qubit Ratio Sweep")
    print("=" * 60)
    
    results = []
    ratios = np.arange(0, 1.05, 0.05)
    n = 6
    depth = 15
    n_trials = 30
    
    for ratio in tqdm(ratios, desc="Exp2"):
        entropies = []
        for trial in range(n_trials):
            seed = int(ratio * 100000) + trial
            qc = generate_random_circuit(n, depth, two_qubit_ratio=ratio, seed=seed)
            
            S = compute_entanglement_entropy(qc, n)
            entropies.append(S)
            
            results.append({
                'experiment': 2,
                'n_qubits': n,
                'depth': depth,
                'two_qubit_ratio': round(ratio, 2),
                'trial': trial,
                'seed': seed,
                'entanglement_entropy': S,
                'gate_count': qc.size(),
            })
        
        print(f"  ratio={ratio:.2f}: S={np.mean(entropies):.3f} ± {np.std(entropies):.3f}")
    
    df = pd.DataFrame(results)
    return df


def run_experiment_3_scaling_behavior():
    """
    Experiment 3: Scaling of critical depth with qubit count.
    
    For each n, find the depth where entanglement entropy first reaches
    90% of its maximum (Page) value.
    
    Expected: d_c scales as a power law with n.
    """
    print("\n" + "=" * 60)
    print("EXPERIMENT 3: Scaling Behavior")
    print("=" * 60)
    
    results = []
    n_qubits_list = [3, 4, 5, 6, 7, 8, 9, 10]
    n_trials = 50  # More trials for scaling analysis
    
    for n in n_qubits_list:
        max_entropy = (n // 2) - (1 / (2 ** (n - 1) * np.log(2)))
        threshold = 0.9 * max_entropy
        
        # Adaptive depth search
        depths_to_test = list(range(1, min(5 * n, 51)))
        
        critical_depths = []
        
        for trial in range(n_trials):
            found_critical = False
            for depth in depths_to_test:
                seed = n * 100000 + depth * 1000 + trial
                qc = generate_random_circuit(n, depth, two_qubit_ratio=0.3, seed=seed)
                S = compute_entanglement_entropy(qc, n)
                
                results.append({
                    'experiment': 3,
                    'n_qubits': n,
                    'depth': depth,
                    'trial': trial,
                    'seed': seed,
                    'entanglement_entropy': S,
                    'max_entropy': max_entropy,
                    'threshold': threshold,
                    'exceeds_threshold': S >= threshold,
                })
                
                if S >= threshold and not found_critical:
                    critical_depths.append(depth)
                    found_critical = True
            
            if not found_critical:
                critical_depths.append(depths_to_test[-1])
        
        mean_dc = np.mean(critical_depths)
        std_dc = np.std(critical_depths)
        print(f"  n={n:2d}: d_c={mean_dc:.1f} ± {std_dc:.1f} (max_S={max_entropy:.3f}, threshold={threshold:.3f})")
    
    df = pd.DataFrame(results)
    return df


def run_experiment_4_optimization_vs_entanglement():
    """
    Experiment 4: Relationship between entanglement and optimizability.
    
    Measure both entanglement entropy and Qiskit optimization reduction
    for the same circuits.
    
    Expected: Higher entanglement → harder to optimize (correlation).
    """
    print("\n" + "=" * 60)
    print("EXPERIMENT 4: Optimization vs Entanglement")
    print("=" * 60)
    
    from qiskit import transpile
    
    results = []
    n = 5
    depths = [3, 5, 8, 10, 15, 20]
    n_trials = 30
    
    for depth in tqdm(depths, desc="Exp4"):
        for trial in range(n_trials):
            seed = n * 100000 + depth * 1000 + trial
            qc = generate_random_circuit(n, depth, two_qubit_ratio=0.3, seed=seed)
            
            # Compute entanglement
            S = compute_entanglement_entropy(qc, n)
            
            # Compute optimization reduction
            try:
                opt_qc = transpile(qc, optimization_level=2, seed_transpiler=42)
                reduction = 1 - opt_qc.size() / max(qc.size(), 1)
            except:
                reduction = 0.0
            
            results.append({
                'experiment': 4,
                'n_qubits': n,
                'depth': depth,
                'trial': trial,
                'seed': seed,
                'entanglement_entropy': S,
                'gate_count': qc.size(),
                'optimized_size': opt_qc.size() if 'opt_qc' in locals() else qc.size(),
                'gate_reduction': reduction,
            })
        
        mean_S = np.mean([r['entanglement_entropy'] for r in results if r['depth'] == depth])
        mean_red = np.mean([r['gate_reduction'] for r in results if r['depth'] == depth])
        print(f"  depth={depth:2d}: S={mean_S:.3f}, reduction={mean_red:.3f}")
    
    df = pd.DataFrame(results)
    return df


def run_experiment_5_landscape_analysis():
    """
    Experiment 5: Optimization landscape analysis near the entanglement transition.
    
    Sample the fitness landscape by perturbing circuits at different depths
    and measuring the change in entanglement entropy.
    """
    print("\n" + "=" * 60)
    print("EXPERIMENT 5: Landscape Analysis")
    print("=" * 60)
    
    results = []
    n = 5
    depths = [3, 5, 8, 10, 15, 20, 30]
    n_circuits = 10
    n_perturbations = 50
    
    for depth in tqdm(depths, desc="Exp5"):
        for circuit_id in range(n_circuits):
            seed = n * 100000 + depth * 1000 + circuit_id * 10
            qc = generate_random_circuit(n, depth, two_qubit_ratio=0.3, seed=seed)
            base_entropy = compute_entanglement_entropy(qc, n)
            
            perturbation_entropies = []
            for p in range(n_perturbations):
                # Perturb: change one random gate angle
                perturbed = qc.copy()
                rot_indices = [i for i, inst in enumerate(perturbed.data) 
                              if inst.operation.name in ['rz', 'rx', 'ry']]
                if rot_indices:
                    idx = rot_indices[np.random.randint(len(rot_indices))]
                    perturbed.data[idx].operation.params[0] += np.random.normal(0, 0.3)
                
                S_perturbed = compute_entanglement_entropy(perturbed, n)
                perturbation_entropies.append(S_perturbed)
            
            # Landscape metrics
            perturbation_array = np.array(perturbation_entropies)
            ruggedness = np.std(perturbation_array)
            mean_perturbation = np.mean(perturbation_array)
            autocorr = np.corrcoef(perturbation_array[:-1], perturbation_array[1:])[0, 1] if len(perturbation_array) > 1 else 0
            
            results.append({
                'experiment': 5,
                'n_qubits': n,
                'depth': depth,
                'circuit_id': circuit_id,
                'base_entropy': base_entropy,
                'mean_perturbation_entropy': mean_perturbation,
                'ruggedness': ruggedness,
                'autocorrelation': autocorr if not np.isnan(autocorr) else 0,
                'entropy_range': np.max(perturbation_array) - np.min(perturbation_array),
            })
        
        mean_rug = np.mean([r['ruggedness'] for r in results if r['depth'] == depth])
        print(f"  depth={depth:2d}: mean_base_S={base_entropy:.3f}, ruggedness={mean_rug:.4f}")
    
    df = pd.DataFrame(results)
    return df


def run_all_experiments():
    """Run all 5 experiments and save results."""
    
    output_dir = 'D:/Desktop/Q-research/data/raw'
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("QUANTUM CIRCUIT ENTANGLEMENT ENTROPY PHASE TRANSITIONS")
    print("=" * 60)
    print("Research Question: Do random quantum circuits exhibit phase transitions")
    print("in entanglement entropy as circuit depth increases?")
    print("=" * 60)
    
    start_time = time.time()
    
    # Run all experiments
    df1 = run_experiment_1_entanglement_vs_depth()
    df1.to_csv(f'{output_dir}/exp1_entropy_vs_depth_{timestamp}.csv', index=False)
    
    df2 = run_experiment_2_two_qubit_ratio_sweep()
    df2.to_csv(f'{output_dir}/exp2_ratio_sweep_{timestamp}.csv', index=False)
    
    df3 = run_experiment_3_scaling_behavior()
    df3.to_csv(f'{output_dir}/exp3_scaling_{timestamp}.csv', index=False)
    
    df4 = run_experiment_4_optimization_vs_entanglement()
    df4.to_csv(f'{output_dir}/exp4_optimization_{timestamp}.csv', index=False)
    
    df5 = run_experiment_5_landscape_analysis()
    df5.to_csv(f'{output_dir}/exp5_landscape_{timestamp}.csv', index=False)
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("ALL EXPERIMENTS COMPLETE")
    print("=" * 60)
    print(f"Total time: {total_time:.1f}s")
    print(f"Files saved to: {output_dir}")
    
    # Summary statistics
    print(f"\nSummary:")
    print(f"  Exp1 (Entropy vs Depth): {len(df1)} records")
    print(f"  Exp2 (Ratio Sweep): {len(df2)} records")
    print(f"  Exp3 (Scaling): {len(df3)} records")
    print(f"  Exp4 (Optimization): {len(df4)} records")
    print(f"  Exp5 (Landscape): {len(df5)} records")
    print(f"  Total: {len(df1)+len(df2)+len(df3)+len(df4)+len(df5)} records")
    
    return {
        'exp1': df1, 'exp2': df2, 'exp3': df3, 'exp4': df4, 'exp5': df5,
        'timestamp': timestamp
    }


if __name__ == '__main__':
    results = run_all_experiments()
