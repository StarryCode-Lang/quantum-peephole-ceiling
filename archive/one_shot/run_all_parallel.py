#!/usr/bin/env python3
"""
Parallel Experiment Runner - Complete All Remaining Experiments
E1, E3 already done. Running E2, E4, E5 in parallel with multiprocessing.
"""
import sys
sys.path.insert(0, 'D:/Desktop/Q-research')

import multiprocessing as mp
import time
from pathlib import Path

from experiments.run_all_experiments_v3 import (
    ExperimentConfig, Experiment2, Experiment3, Experiment4, Experiment5
)

def run_experiment(name, exp_class, config):
    """Run a single experiment and return status."""
    start = time.time()
    print(f"[{name}] START at {time.strftime('%H:%M:%S')}")
    try:
        exp = exp_class(config)
        df = exp.run()
        elapsed = time.time() - start
        print(f"[{name}] DONE: {len(df)} rows in {elapsed:.1f}s")
        return name, "success", len(df), elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"[{name}] FAILED: {e} ({elapsed:.1f}s)")
        return name, "failed", str(e), elapsed

if __name__ == '__main__':
    config = ExperimentConfig()
    
    # E1 and E3 already completed
    experiments = [
        ("E2_entanglement", Experiment2),
        ("E4_algorithm", Experiment4),
        ("E5_landscape", Experiment5),
    ]
    
    print("="*60)
    print("PARALLEL EXPERIMENT RUNNER")
    print(f"CPUs: {mp.cpu_count()}")
    print(f"Running: E2, E4, E5 in parallel")
    print("="*60)
    
    start_all = time.time()
    
    # Use process pool - one experiment per process
    with mp.Pool(processes=min(3, mp.cpu_count())) as pool:
        results = pool.starmap(
            run_experiment,
            [(name, cls, config) for name, cls in experiments]
        )
    
    total = time.time() - start_all
    
    print("\n" + "="*60)
    print("ALL EXPERIMENTS COMPLETE")
    print("="*60)
    for name, status, data, elapsed in results:
        print(f"  {name}: {status} | {data} | {elapsed:.1f}s")
    print(f"\nTotal time: {total:.1f}s ({total/60:.1f} min)")
