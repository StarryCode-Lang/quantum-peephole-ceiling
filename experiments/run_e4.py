#!/usr/bin/env python3
"""Experiment 4: Algorithm Comparison"""
import sys
sys.path.insert(0, "D:/Desktop/Q-research")

from experiments.run_all_experiments_v3 import Experiment4, ExperimentConfig

config = ExperimentConfig()
exp = Experiment4(config)
print("=" * 60)
print("STARTING E4: Algorithm Comparison")
print("=" * 60)
try:
    df = exp.run()
    print(f"E4 COMPLETE: {len(df)} rows")
except Exception as e:
    print(f"E4 FAILED: {e}")
    import traceback
    traceback.print_exc()
