#!/usr/bin/env python3
"""Experiment 3: Scaling Behavior"""
import sys
sys.path.insert(0, "D:/Desktop/Q-research")

from experiments.run_all_experiments_v3 import Experiment3, ExperimentConfig

config = ExperimentConfig()
exp = Experiment3(config)
print("=" * 60)
print("STARTING E3: Scaling Behavior")
print("=" * 60)
try:
    df = exp.run()
    print(f"E3 COMPLETE: {len(df)} rows")
except Exception as e:
    print(f"E3 FAILED: {e}")
    import traceback
    traceback.print_exc()
