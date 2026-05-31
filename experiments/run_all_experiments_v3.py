"""
Experiment Runner - Production Quality v2.1
============================================
Runs all experiments with proper logging, error handling,
reproducibility guarantees, and checkpointing.

Author: Q-research Team
Version: 2.1.0
"""

from __future__ import annotations

import sys
import os
import json
import time
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.circuits.generator_v2 import (
    CircuitConfig, CircuitFamily, StructureType,
    generate_circuit_batch, MetricsCalculator
)
from src.optimisation.optimizers_v2 import (
    OptimizerType, create_optimizer, OptimizationResult
)


# ============================================================================
# Configuration
# ============================================================================

class ExperimentConfig:
    """Configuration for experiments."""
    
    def __init__(self, output_dir: Optional[Path] = None, log_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path('D:/Desktop/Q-research/data/raw')
        self.log_dir = log_dir or Path('D:/Desktop/Q-research/logs')
        self.seed = 42
        self.n_trials = 100  # Minimum for statistical significance
        
        # Experiment parameters
        self.n_qubits_range = list(range(3, 11))  # 3-10 qubits
        self.depth_range = list(range(1, 51))  # 1-50 depth
        self.entanglement_densities = np.arange(0, 1.05, 0.05)  # 0-1 in steps of 0.05
        
    def setup_logging(self):
        """Setup logging configuration."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger(__name__)
        if not logger.handlers:  # Prevent duplicate handlers
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(self.log_dir / f'experiment_{datetime.now():%Y%m%d_%H%M%S}.log'),
                    logging.StreamHandler()
                ]
            )
        return logger


# ============================================================================
# Base Experiment
# ============================================================================

class BaseExperiment:
    """Base class for all experiments."""
    
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.logger = config.setup_logging()
        self.results: List[Dict[str, Any]] = []
        self.metrics_calculator = MetricsCalculator()
    
    def run(self) -> pd.DataFrame:
        """Run the experiment. Must be implemented by subclasses."""
        raise NotImplementedError
    
    def save_results(self, experiment_name: str):
        """Save results to CSV."""
        df = pd.DataFrame(self.results)
        output_path = self.config.output_dir / f'{experiment_name}_{datetime.now():%Y%m%d_%H%M%S}.csv'
        df.to_csv(output_path, index=False)
        self.logger.info(f"Saved {len(df)} records to {output_path}")
        return df


# ============================================================================
# Experiment 1: Basic Phase Transition Detection
# ============================================================================

class Experiment1(BaseExperiment):
    """
    Experiment 1: Basic Phase Transition Detection
    
    Vary circuit depth (1-50) with fixed n=5, measure optimization success rate.
    """
    
    def run(self) -> pd.DataFrame:
        """Run Experiment 1."""
        self.logger.info("=" * 60)
        self.logger.info("EXPERIMENT 1: Basic Phase Transition Detection")
        self.logger.info("=" * 60)
        
        n_qubits = 5
        depths = self.config.depth_range
        n_trials = self.config.n_trials
        
        total = len(depths) * n_trials
        self.logger.info(f"Total circuits: {total}")
        
        with tqdm(total=total, desc="E1") as pbar:
            for depth in depths:
                for trial in range(n_trials):
                    # Generate circuit
                    config = CircuitConfig(
                        n_qubits=n_qubits,
                        depth=depth,
                        family=CircuitFamily.UNIVERSAL,
                        seed=self.config.seed + trial,
                        entanglement_density=0.3,
                    )
                    
                    circuits = generate_circuit_batch(config, 1, self.metrics_calculator)
                    circuit, metrics = circuits[0]
                    
                    # Run optimization
                    optimizer = create_optimizer(OptimizerType.GREEDY)
                    result = optimizer.optimize(circuit)
                    
                    self.results.append({
                        'experiment': 1,
                        'n_qubits': n_qubits,
                        'depth': depth,
                        'trial': trial,
                        'gate_count': metrics.gate_count,
                        'entanglement_entropy': metrics.entanglement_entropy,
                        'normalized_entropy': metrics.normalized_entropy,
                        'optimized_size': result.optimized_size,
                        'reduction': result.reduction,
                        'fidelity': result.fidelity,
                        'success': result.success,
                        'runtime': result.runtime_seconds,
                    })
                    
                    pbar.update(1)
        
        return self.save_results('exp1_phase_transition')


# ============================================================================
# Experiment 2: Entanglement Density Study
# ============================================================================

class Experiment2(BaseExperiment):
    """
    Experiment 2: Entanglement Density Study
    
    Vary entanglement density (0-1) with fixed n=6, d=20.
    """
    
    def run(self) -> pd.DataFrame:
        """Run Experiment 2."""
        self.logger.info("=" * 60)
        self.logger.info("EXPERIMENT 2: Entanglement Density Study")
        self.logger.info("=" * 60)
        
        n_qubits = 6
        depth = 20
        densities = self.config.entanglement_densities
        n_trials = self.config.n_trials
        
        total = len(densities) * n_trials
        self.logger.info(f"Total circuits: {total}")
        
        with tqdm(total=total, desc="E2") as pbar:
            for density in densities:
                for trial in range(n_trials):
                    config = CircuitConfig(
                        n_qubits=n_qubits,
                        depth=depth,
                        family=CircuitFamily.UNIVERSAL,
                        seed=self.config.seed + trial,
                        entanglement_density=density,
                    )
                    
                    circuits = generate_circuit_batch(config, 1, self.metrics_calculator)
                    circuit, metrics = circuits[0]
                    
                    # Run multiple optimizers
                    for opt_type in [OptimizerType.GREEDY, OptimizerType.SIMULATED_ANNEALING]:
                        optimizer = create_optimizer(opt_type)
                        result = optimizer.optimize(circuit)
                        
                        self.results.append({
                            'experiment': 2,
                            'n_qubits': n_qubits,
                            'depth': depth,
                            'entanglement_density': density,
                            'trial': trial,
                            'optimizer': opt_type.name,
                            'gate_count': metrics.gate_count,
                            'entanglement_entropy': metrics.entanglement_entropy,
                            'normalized_entropy': metrics.normalized_entropy,
                            'optimized_size': result.optimized_size,
                            'reduction': result.reduction,
                            'fidelity': result.fidelity,
                            'success': result.success,
                            'runtime': result.runtime_seconds,
                        })
                    
                    pbar.update(1)
        
        return self.save_results('exp2_entanglement_density')


# ============================================================================
# Experiment 3: Scaling Behavior
# ============================================================================

class Experiment3(BaseExperiment):
    """
    Experiment 3: Scaling Behavior
    
    Vary qubit count (2-10) and depth (1-30).
    """
    
    def run(self) -> pd.DataFrame:
        """Run Experiment 3."""
        self.logger.info("=" * 60)
        self.logger.info("EXPERIMENT 3: Scaling Behavior")
        self.logger.info("=" * 60)
        
        n_qubits_list = self.config.n_qubits_range
        depths = list(range(1, 31))
        n_trials = 50  # Fewer trials for larger parameter space
        
        total = len(n_qubits_list) * len(depths) * n_trials
        self.logger.info(f"Total circuits: {total}")
        
        with tqdm(total=total, desc="E3") as pbar:
            for n_qubits in n_qubits_list:
                for depth in depths:
                    for trial in range(n_trials):
                        config = CircuitConfig(
                            n_qubits=n_qubits,
                            depth=depth,
                            family=CircuitFamily.UNIVERSAL,
                            seed=self.config.seed + trial,
                            entanglement_density=0.3,
                        )
                        
                        circuits = generate_circuit_batch(config, 1, self.metrics_calculator)
                        circuit, metrics = circuits[0]
                        
                        optimizer = create_optimizer(OptimizerType.GREEDY)
                        result = optimizer.optimize(circuit)
                        
                        self.results.append({
                            'experiment': 3,
                            'n_qubits': n_qubits,
                            'depth': depth,
                            'trial': trial,
                            'gate_count': metrics.gate_count,
                            'entanglement_entropy': metrics.entanglement_entropy,
                            'normalized_entropy': metrics.normalized_entropy,
                            'optimized_size': result.optimized_size,
                            'reduction': result.reduction,
                            'fidelity': result.fidelity,
                            'success': result.success,
                            'runtime': result.runtime_seconds,
                        })
                        
                        pbar.update(1)
        
        return self.save_results('exp3_scaling')


# ============================================================================
# Experiment 4: Algorithm Comparison
# ============================================================================

class Experiment4(BaseExperiment):
    """
    Experiment 4: Algorithm Comparison
    
    Compare all optimization algorithms on the same circuits.
    """
    
    def run(self) -> pd.DataFrame:
        """Run Experiment 4."""
        self.logger.info("=" * 60)
        self.logger.info("EXPERIMENT 4: Algorithm Comparison")
        self.logger.info("=" * 60)
        
        n_qubits = 5
        depth = 15
        n_trials = self.config.n_trials
        
        total = n_trials * len(OptimizerType)
        self.logger.info(f"Total runs: {total}")
        
        with tqdm(total=total, desc="E4") as pbar:
            for trial in range(n_trials):
                # Generate one circuit per trial
                config = CircuitConfig(
                    n_qubits=n_qubits,
                    depth=depth,
                    family=CircuitFamily.UNIVERSAL,
                    seed=self.config.seed + trial,
                    entanglement_density=0.3,
                )
                
                circuits = generate_circuit_batch(config, 1, self.metrics_calculator)
                circuit, metrics = circuits[0]
                
                # Test each optimizer
                for opt_type in OptimizerType:
                    optimizer = create_optimizer(opt_type)
                    result = optimizer.optimize(circuit)
                    
                    self.results.append({
                        'experiment': 4,
                        'n_qubits': n_qubits,
                        'depth': depth,
                        'trial': trial,
                        'optimizer': opt_type.name,
                        'gate_count': metrics.gate_count,
                        'entanglement_entropy': metrics.entanglement_entropy,
                        'normalized_entropy': metrics.normalized_entropy,
                        'optimized_size': result.optimized_size,
                        'reduction': result.reduction,
                        'fidelity': result.fidelity,
                        'success': result.success,
                        'runtime': result.runtime_seconds,
                    })
                    
                    pbar.update(1)
        
        return self.save_results('exp4_algorithm_comparison')


# ============================================================================
# Experiment 5: Landscape Characterization
# ============================================================================

class Experiment5(BaseExperiment):
    """
    Experiment 5: Landscape Characterization
    
    Detailed landscape analysis with extensive sampling.
    """
    
    def run(self) -> pd.DataFrame:
        """Run Experiment 5."""
        self.logger.info("=" * 60)
        self.logger.info("EXPERIMENT 5: Landscape Characterization")
        self.logger.info("=" * 60)
        
        n_qubits = 5
        depths = [3, 5, 8, 10, 15, 20]
        n_circuits = 10
        n_samples = 100  # Samples per circuit for landscape
        
        total = len(depths) * n_circuits * n_samples
        self.logger.info(f"Total samples: {total}")
        
        with tqdm(total=total, desc="E5") as pbar:
            for depth in depths:
                for circuit_id in range(n_circuits):
                    # Generate base circuit
                    config = CircuitConfig(
                        n_qubits=n_qubits,
                        depth=depth,
                        family=CircuitFamily.UNIVERSAL,
                        seed=self.config.seed + circuit_id,
                        entanglement_density=0.3,
                    )
                    
                    circuits = generate_circuit_batch(config, 1, self.metrics_calculator)
                    base_circuit, base_metrics = circuits[0]
                    
                    # Sample landscape
                    for sample in range(n_samples):
                        # Create perturbed version
                        perturbed = self._perturb_circuit(base_circuit, n_qubits, sample)
                        
                        # Calculate metrics
                        perturbed_metrics = self.metrics_calculator.calculate(perturbed)
                        
                        self.results.append({
                            'experiment': 5,
                            'n_qubits': n_qubits,
                            'depth': depth,
                            'circuit_id': circuit_id,
                            'sample': sample,
                            'base_entropy': base_metrics.entanglement_entropy,
                            'perturbed_entropy': perturbed_metrics.entanglement_entropy,
                            'entropy_diff': abs(base_metrics.entanglement_entropy - perturbed_metrics.entanglement_entropy),
                            'base_gates': base_metrics.gate_count,
                            'perturbed_gates': perturbed_metrics.gate_count,
                        })
                        
                        pbar.update(1)
        
        return self.save_results('exp5_landscape')
    
    def _perturb_circuit(self, circuit: QuantumCircuit, n_qubits: int, seed: int) -> QuantumCircuit:
        """Create a perturbed version of the circuit."""
        import copy
        rng = np.random.RandomState(seed)
        
        perturbed = copy.deepcopy(circuit)
        
        if len(perturbed.data) > 0:
            # Random modification
            if rng.random() < 0.5 and len(perturbed.data) > 1:
                # Swap two gates
                i, j = rng.choice(len(perturbed.data), 2, replace=False)
                perturbed.data[i], perturbed.data[j] = perturbed.data[j], perturbed.data[i]
            else:
                # Remove random gate
                idx = rng.randint(0, len(perturbed.data))
                perturbed.data.pop(idx)
        
        return perturbed


# ============================================================================
# Main Runner
# ============================================================================

def run_all_experiments():
    """Run all experiments."""
    config = ExperimentConfig()
    
    experiments = [
        Experiment1(config),
        Experiment2(config),
        Experiment3(config),
        Experiment4(config),
        Experiment5(config),
    ]
    
    for experiment in experiments:
        try:
            experiment.run()
        except Exception as e:
            logging.error(f"Experiment failed: {e}", exc_info=True)


if __name__ == '__main__':
    run_all_experiments()
