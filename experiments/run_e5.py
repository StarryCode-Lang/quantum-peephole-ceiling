#!/usr/bin/env python3
"""Experiment 5: Landscape Characterization"""
import sys
sys.path.insert(0, "D:/Desktop/Q-research")

from experiments.run_all_experiments_v3 import Experiment5, ExperimentConfig

config = ExperimentConfig()
exp = Experiment5(config)
print("=" * 60)
print("STARTING E5: Landscape Characterization")
print("=" * 60)
try:
    df = exp.run()
    print(f"E5 COMPLETE: {len(df)} rows")
except Exception as e:
    print(f"E5 FAILED: {e}")
    import traceback
    traceback.print_exc()
