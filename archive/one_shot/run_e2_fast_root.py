import sys
sys.path.insert(0, 'D:/Desktop/Q-research')

from experiments.run_all_experiments_v3 import Experiment2, ExperimentConfig

# Reduce density steps and trials for reasonable runtime
# while maintaining statistical validity (n=30 per config)
config = ExperimentConfig()
config.entanglement_densities = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]  # 11 points
config.n_trials = 30

exp = Experiment2(config)
print("E2 START: 11 densities x 30 trials x 2 optimizers = 660 circuits")
df = exp.run()
print(f"E2 DONE: {len(df)} rows")
