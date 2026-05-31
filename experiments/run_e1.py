#!/usr/bin/env python3
"""Experiment 1: Phase Transition Detection"""
import sys
sys.path.insert(0, "D:/Desktop/Q-research")

from experiments.run_all_experiments_v3 import Experiment1, ExperimentConfig

config = ExperimentConfig()
exp = Experiment1(config)
print("=" * 60)
print("STARTING E1: Phase Transition Detection")
print("=" * 60)
try:
    df = exp.run()
    print(f"E1 COMPLETE: {len(df)} rows")
except Exception as e:
    print(f"E1 FAILED: {e}")
    import traceback
    traceback.print_exc()
