import pandas as pd

e5 = pd.read_csv('D:/Desktop/Q-research/data/raw/exp5_landscape_20260530_102615.csv')
print('E5 shape:', e5.shape)
print('E5 columns:', e5.columns.tolist())
print(e5.head(3))
print()
if 'n_qubits' in e5.columns:
    print('n_qubits values:', sorted(e5['n_qubits'].unique()))
if 'depth' in e5.columns:
    print('depth values:', sorted(e5['depth'].unique()))

# Check other experiment files
files = [
    'exp1_phase_transition_20260530_095003.csv',
    'exp2_entanglement_density_20260530_112304.csv',
    'exp3_scaling_20260530_100830.csv',
    'exp4_algorithm_comparison_20260530_111458.csv',
]
for f in files:
    path = f'D:/Desktop/Q-research/data/raw/{f}'
    try:
        df = pd.read_csv(path)
        print(f'\n{f}: shape={df.shape}, cols={df.columns.tolist()}')
        print(df.head(2))
    except Exception as e:
        print(f'{f}: ERROR {e}')