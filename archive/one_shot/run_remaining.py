import sys
sys.path.insert(0, 'D:/Desktop/Q-research')

from experiments.run_all_experiments_v3 import Experiment2, Experiment4, ExperimentConfig

config = ExperimentConfig()

print("="*60)
print("RUNNING E2: Entanglement Density Study")
print("="*60)
try:
    exp2 = Experiment2(config)
    df2 = exp2.run()
    print(f"E2 COMPLETE: {len(df2)} rows")
except Exception as e:
    print(f"E2 FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("RUNNING E4: Algorithm Comparison")
print("="*60)
try:
    exp4 = Experiment4(config)
    df4 = exp4.run()
    print(f"E4 COMPLETE: {len(df4)} rows")
except Exception as e:
    print(f"E4 FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("ALL REMAINING EXPERIMENTS COMPLETE")
print("="*60)
