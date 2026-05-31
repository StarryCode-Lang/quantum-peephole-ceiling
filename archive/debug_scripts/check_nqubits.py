import pandas as pd

# Check n_qubits values across all experiments
e5 = pd.read_csv('D:/Desktop/Q-research/data/raw/exp5_landscape_20260530_102615.csv')
e1 = pd.read_csv('D:/Desktop/Q-research/data/raw/exp1_phase_transition_20260530_095003.csv')
e2 = pd.read_csv('D:/Desktop/Q-research/data/raw/exp2_entanglement_density_20260530_112304.csv')
e3 = pd.read_csv('D:/Desktop/Q-research/data/raw/exp3_scaling_20260530_100830.csv')
e4 = pd.read_csv('D:/Desktop/Q-research/data/raw/exp4_algorithm_comparison_20260530_111458.csv')

print('E5 n_qubits:', sorted(e5['n_qubits'].unique()))
print('E5 depth:', sorted(e5['depth'].unique()))
print()
print('E1 n_qubits:', sorted(e1['n_qubits'].unique()))
print('E1 depth:', sorted(e1['depth'].unique()))
print()
print('E2 n_qubits:', sorted(e2['n_qubits'].unique()))
print('E2 depth:', sorted(e2['depth'].unique()))
print()
print('E3 n_qubits:', sorted(e3['n_qubits'].unique()))
print('E3 depth:', sorted(e3['depth'].unique()))
print()
print('E4 n_qubits:', sorted(e4['n_qubits'].unique()))
print('E4 depth:', sorted(e4['depth'].unique()))