#!/usr/bin/env python3
"""Experiment 2 Fast: Entanglement Density Study (30 trials instead of 100)"""
import sys
sys.path.insert(0, "D:/Desktop/Q-research")

from experiments.run_all_experiments_v3 import Experiment2, ExperimentConfig

config = ExperimentConfig()
config.n_trials = 30  # Reduced from 100 for speed
exp = Experiment2(config)
print("=" * 60)
print("STARTING E2 FAST: Entanglement Density (30 trials)")
print(f"Total iterations: 21 densities × 30 trials = 630")
print("=" * 60)
try:
    df = exp.run()
    print(f"E2 COMPLETE: {len(df)} rows")
except Exception as e:
    print(f"E2 FAILED: {e}")
    import traceback
    traceback.print_exc()
