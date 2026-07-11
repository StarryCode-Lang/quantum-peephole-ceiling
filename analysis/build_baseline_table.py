import pandas as pd

# E12: Qiskit L0-L3 (no-coupling = fair comparison mode)
e12 = pd.read_csv(r'D:\Desktop\Q-research\data\v4\e12\e12_compiler_baseline_e12_full_20260626_000134_nocoupling.csv')

# E15: custom optimizers
e15 = pd.read_csv(r'D:\Desktop\Q-research\data\v5\e15\e15_multi_compiler_e15_full_20260611_150934.csv')
e15_custom = e15[e15['compiler'] == 'custom'].copy()

print('=== E15 custom backends ===')
for bk in e15_custom['compiler_backend'].unique():
    sub = e15_custom[e15_custom['compiler_backend'] == bk]
    fid = sub['fidelity'].dropna()
    print(f'  {bk}: n={len(sub)}, mean_red={sub["reduction_pct"].mean():.2f}%, '
          f'mean_fid={fid.mean():.6f} (n_fid={len(fid)}), '
          f'mean_rt={sub["runtime_seconds"].mean():.4f}s')

print()
print('=== E12 Qiskit levels ===')
for lvl in sorted(e12['compiler_optimization_level'].unique()):
    sub = e12[e12['compiler_optimization_level'] == lvl]
    fid = sub['fidelity'].dropna()
    print(f'  L{lvl}: n={len(sub)}, mean_red={sub["reduction_pct"].mean():.2f}%, '
          f'mean_fid={fid.mean():.6f} (n_fid={len(fid)}), '
          f'mean_rt={sub["runtime_seconds"].mean():.4f}s')

print()
print('=== E15 qiskit (cross-check) ===')
e15_q = e15[e15['compiler'] == 'qiskit']
for lvl in sorted(e15_q['compiler_opt_level'].unique()):
    sub = e15_q[e15_q['compiler_opt_level'] == lvl]
    print(f'  L{lvl}: n={len(sub)}, mean_red={sub["reduction_pct"].mean():.2f}%, '
          f'mean_rt={sub["runtime_seconds"].mean():.4f}s')

# Build rows
rows = []

backend_map = {
    'greedy_phase1': ('Greedy (ours)', 'Phase-1 peephole'),
    'commutation_phase2': ('CommutationRewriter (ours)', 'Phase-2 commutation'),
    'hybrid_phase1_2': ('HybridCommuteRewrite (ours)', 'Phase-1+2 hybrid'),
}

for bk, (name, typ) in backend_map.items():
    sub = e15_custom[e15_custom['compiler_backend'] == bk]
    fid = sub['fidelity'].dropna()
    fid_str = f'{fid.mean():.3f}' if len(fid) > 0 else 'N/A'
    rows.append({
        'name': name, 'type': typ,
        'red': sub['reduction_pct'].mean(),
        'fid': fid_str,
        'rt': sub['runtime_seconds'].mean(),
        'n': len(sub),
    })

qiskit_types = {
    0: 'Basis translation',
    1: 'Light peephole',
    2: 'Noise-aware',
    3: 'Heavy optimization',
}

for lvl in [0, 1, 2, 3]:
    sub = e12[e12['compiler_optimization_level'] == lvl]
    fid = sub['fidelity'].dropna()
    fid_str = f'{fid.mean():.3f}' if len(fid) > 0 else 'N/A'
    rows.append({
        'name': f'Qiskit L{lvl}',
        'type': qiskit_types[lvl],
        'red': sub['reduction_pct'].mean(),
        'fid': fid_str,
        'rt': sub['runtime_seconds'].mean(),
        'n': len(sub),
    })

print()
print('=== TABLE ROWS ===')
for r in rows:
    print(f"| {r['name']} | {r['type']} | {r['red']:.1f} | {r['fid']} | {r['rt']:.2f} | {r['n']} |")
