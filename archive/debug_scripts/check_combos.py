import pandas as pd
e3 = pd.read_csv('D:/Desktop/Q-research/data/raw/exp3_scaling_20260530_100830.csv')
print('E3 unique (n, depth) combos:', len(e3.groupby(['n_qubits', 'depth'])))
e1 = pd.read_csv('D:/Desktop/Q-research/data/raw/exp1_phase_transition_20260530_095003.csv')
print('E1 unique (n, depth) combos:', len(e1.groupby(['n_qubits', 'depth'])))
print('E3 shape:', e3.shape)
print('E1 shape:', e1.shape)