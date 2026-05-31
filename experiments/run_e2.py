#!/usr/bin/env python3
"""Experiment 2: Entanglement Density Study"""
import sys
sys.path.insert(0, "D:/Desktop/Q-research")

from experiments.run_all_experiments_v3 import Experiment2, ExperimentConfig

config = ExperimentConfig()
exp = Experiment2(config)
print("=" * 60)
print("STARTING E2: Entanglement Density Study")
print("=" * 60)
try:
    df = exp.run()
    print(f"E2 COMPLETE: {len(df)} rows")
except Exception as e:
    print(f"E2 FAILED: {e}")
    import traceback
    traceback.print_exc()
