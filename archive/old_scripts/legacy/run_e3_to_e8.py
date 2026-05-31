"""Run E3-E8 experiments sequentially"""
import sys, os, gc, numpy as np, pandas as pd, time, json
from datetime import datetime
from scipy import stats as sp_stats
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with open("D:/Desktop/Q-research/data/raw/page_values.json") as f:
    _cached_pages = {int(k): v for k, v in json.load(f).items()}
def get_page_value(n): return _cached_pages[n]
from core import (generate_random_circuit, compute_entanglement_entropy,
                  perturb_circuit_structural, perturb_circuit_angle,
                  count_gates, gate_reduction)
from qiskit import transpile

OUTPUT_DIR = 'D:/Desktop/Q-research/data/raw'
os.makedirs(OUTPUT_DIR, exist_ok=True)
start_total = time.time()


# === E3: Scaling ===
print('\n=== E3: Scaling ===')
results = []
n_qubits_list = [3, 4, 5, 6, 7, 8, 9, 10]
n_trials = 30
rho = 0.3
depth_limits = {3: 15, 4: 25, 5: 35, 6: 45, 7: 55, 8: 60, 9: 70, 10: 70}

start = time.time()
for n in n_qubits_list:
    page_val = get_page_value(n)
    max_depth = depth_limits[n]
    depths = list(range(1, min(max_depth + 1, 41))) + [d for d in [50, 60, 70] if d <= max_depth]
    depths = sorted(set(depths))
    for depth in depths:
        for trial in range(n_trials):
            seed = n * 100000 + depth * 1000 + trial
            qc = generate_random_circuit(n, depth, two_qubit_ratio=rho, seed=seed)
            S = compute_entanglement_entropy(qc, n)
            results.append({
                'experiment': 3, 'n_qubits': n, 'depth': depth, 'trial': trial,
                'seed': seed, 'entanglement_entropy': S, 'page_value': page_val,
                'normalized_entropy': S / page_val if page_val > 0 else 0,
            })
    max_S = max(r['entanglement_entropy'] for r in results if r['n_qubits'] == n)
    print(f'  n={n}: max_S={max_S:.4f}, page={page_val:.4f}, ratio={max_S/page_val:.3f} ({time.time()-start:.0f}s)')
    sys.stdout.flush()

df3 = pd.DataFrame(results)
df3.to_csv(f'{OUTPUT_DIR}/exp3_scaling.csv', index=False)
print(f'E3: {len(df3)} records in {time.time()-start:.0f}s')
del results; gc.collect()

# === E4: Optimization ===
print('\n=== E4: Optimization ===')
results = []
n_qubits_list = [3, 4, 5, 6, 7, 8]
depths = [3, 5, 8, 10, 15, 20]
n_trials = 30
start = time.time()
for n in n_qubits_list:
    page_val = get_page_value(n)
    for depth in depths:
        for trial in range(n_trials):
            seed = n * 100000 + depth * 1000 + trial
            qc = generate_random_circuit(n, depth, two_qubit_ratio=rho, seed=seed)
            S = compute_entanglement_entropy(qc, n)
            gates = count_gates(qc)
            try:
                opt2 = transpile(qc, optimization_level=2, seed_transpiler=42)
                r2 = gate_reduction(qc, opt2)
                os2 = opt2.size()
            except:
                r2, os2 = 0.0, qc.size()
            try:
                opt3 = transpile(qc, optimization_level=3, seed_transpiler=42)
                r3 = gate_reduction(qc, opt3)
                os3 = opt3.size()
            except:
                r3, os3 = 0.0, qc.size()
            results.append({
                'experiment': 4, 'n_qubits': n, 'depth': depth, 'trial': trial,
                'seed': seed, 'entanglement_entropy': S, 'page_value': page_val,
                'normalized_entropy': S / page_val if page_val > 0 else 0,
                'gate_count': gates['total'], 'two_qubit_gates': gates['two_qubit'],
                'optimized_size_2': os2, 'gate_reduction_2': r2,
                'optimized_size_3': os3, 'gate_reduction_3': r3,
            })
    print(f'  n={n} done ({time.time()-start:.0f}s)')
    sys.stdout.flush()

df4 = pd.DataFrame(results)
df4.to_csv(f'{OUTPUT_DIR}/exp4_optimization.csv', index=False)
print(f'E4: {len(df4)} records in {time.time()-start:.0f}s')
del results; gc.collect()

# === E5: Landscape ===
print('\n=== E5: Landscape ===')
results = []
n = 5
depths = [3, 5, 8, 10, 15, 20, 30]
n_circuits = 10
n_perturbations = 30
start = time.time()
for depth in depths:
    page_val = get_page_value(n)
    for circuit_id in range(n_circuits):
        seed = n * 100000 + depth * 1000 + circuit_id * 10
        qc = generate_random_circuit(n, depth, two_qubit_ratio=rho, seed=seed)
        base_entropy = compute_entanglement_entropy(qc, n)
        
        struct_entropies = []
        angle_entropies = []
        for p in range(n_perturbations):
            p_seed = seed * 1000 + p
            ps = perturb_circuit_structural(qc, n, n_swaps=1, seed=p_seed)
            struct_entropies.append(compute_entanglement_entropy(ps, n))
            pa = perturb_circuit_angle(qc, n, n_perturbations=1, sigma=0.3, seed=p_seed)
            angle_entropies.append(compute_entanglement_entropy(pa, n))
        
        sa, aa = np.array(struct_entropies), np.array(angle_entropies)
        def safe_autocorr(x):
            if len(x) > 1 and np.std(x) > 1e-15:
                return float(np.corrcoef(x[:-1], x[1:])[0, 1])
            return 0.0
        
        results.append({
            'experiment': 5, 'n_qubits': n, 'depth': depth, 'circuit_id': circuit_id,
            'base_entropy': base_entropy,
            'struct_mean': float(np.mean(sa)), 'struct_std': float(np.std(sa)),
            'struct_range': float(np.max(sa) - np.min(sa)),
            'struct_autocorr': safe_autocorr(sa),
            'angle_mean': float(np.mean(aa)), 'angle_std': float(np.std(aa)),
            'angle_range': float(np.max(aa) - np.min(aa)),
            'angle_autocorr': safe_autocorr(aa),
        })
    print(f'  depth={depth} done ({time.time()-start:.0f}s)')
    sys.stdout.flush()

df5 = pd.DataFrame(results)
df5.to_csv(f'{OUTPUT_DIR}/exp5_landscape.csv', index=False)
print(f'E5: {len(df5)} records in {time.time()-start:.0f}s')
del results; gc.collect()

# === E6: Gate Ablation ===
print('\n=== E6: Gate Ablation ===')
results = []
gate_sets = ['ht_rz_cnot', 'clifford_cnot', 'h_cnot', 't_rz_cnot']
n_qubits_list = [4, 6, 8]
depths = [5, 10, 15, 20, 30]
n_trials = 30
start = time.time()
for gate_set in gate_sets:
    for n in n_qubits_list:
        page_val = get_page_value(n)
        for depth in depths:
            for trial in range(n_trials):
                seed = hash(f"{gate_set}_{n}_{depth}_{trial}") % (2**31)
                qc = generate_random_circuit(n, depth, two_qubit_ratio=rho, gate_set=gate_set, seed=seed)
                S = compute_entanglement_entropy(qc, n)
                gates = count_gates(qc)
                results.append({
                    'experiment': 6, 'gate_set': gate_set, 'n_qubits': n, 'depth': depth,
                    'trial': trial, 'entanglement_entropy': S,
                    'normalized_entropy': S / page_val if page_val > 0 else 0,
                    'gate_count': gates['total'], 'two_qubit_gates': gates['two_qubit'],
                })
    print(f'  {gate_set} done ({time.time()-start:.0f}s)')
    sys.stdout.flush()

df6 = pd.DataFrame(results)
df6.to_csv(f'{OUTPUT_DIR}/exp6_gate_ablation.csv', index=False)
print(f'E6: {len(df6)} records')
del results; gc.collect()

# === E7: Topology Ablation ===
print('\n=== E7: Topology Ablation ===')
results = []
topologies = ['nearest_neighbor', 'random_pairing', 'all_to_all']
n_trials = 30
start = time.time()
for topo in topologies:
    for n in n_qubits_list:
        page_val = get_page_value(n)
        for depth in depths:
            for trial in range(n_trials):
                seed = hash(f"{topo}_{n}_{depth}_{trial}") % (2**31)
                qc = generate_random_circuit(n, depth, two_qubit_ratio=rho, topology=topo, seed=seed)
                S = compute_entanglement_entropy(qc, n)
                gates = count_gates(qc)
                results.append({
                    'experiment': 7, 'topology': topo, 'n_qubits': n, 'depth': depth,
                    'trial': trial, 'entanglement_entropy': S,
                    'normalized_entropy': S / page_val if page_val > 0 else 0,
                    'gate_count': gates['total'], 'two_qubit_gates': gates['two_qubit'],
                })
    print(f'  {topo} done ({time.time()-start:.0f}s)')
    sys.stdout.flush()

df7 = pd.DataFrame(results)
df7.to_csv(f'{OUTPUT_DIR}/exp7_topology_ablation.csv', index=False)
print(f'E7: {len(df7)} records')
del results; gc.collect()

# === E8: Initial State Ablation ===
print('\n=== E8: Initial State Ablation ===')
from qiskit.quantum_info import Statevector, partial_trace, entropy as qiskit_entropy, random_statevector
results = []
state_types = ['zero', 'plus', 'random']
n_trials = 30
start = time.time()
for state_type in state_types:
    for n in n_qubits_list:
        page_val = get_page_value(n)
        for depth in depths:
            for trial in range(n_trials):
                seed = hash(f"{state_type}_{n}_{depth}_{trial}") % (2**31)
                qc = generate_random_circuit(n, depth, two_qubit_ratio=rho, seed=seed)
                try:
                    if state_type == 'zero':
                        sv = Statevector.from_label('0' * n)
                    elif state_type == 'plus':
                        from qiskit import QuantumCircuit
                        prep = QuantumCircuit(n)
                        for q in range(n):
                            prep.h(q)
                        sv = Statevector.from_label('0' * n).evolve(prep)
                    else:
                        sv = random_statevector(2**n, seed=seed)
                    final_sv = sv.evolve(qc)
                    n_A = n // 2
                    rho_A = partial_trace(final_sv, list(range(n_A, n)))
                    S = float(qiskit_entropy(rho_A, base=2))
                except:
                    S = 0.0
                results.append({
                    'experiment': 8, 'initial_state': state_type, 'n_qubits': n,
                    'depth': depth, 'trial': trial, 'entanglement_entropy': S,
                    'normalized_entropy': S / page_val if page_val > 0 else 0,
                })
    print(f'  {state_type} done ({time.time()-start:.0f}s)')
    sys.stdout.flush()

df8 = pd.DataFrame(results)
df8.to_csv(f'{OUTPUT_DIR}/exp8_initial_state_ablation.csv', index=False)
print(f'E8: {len(df8)} records')
del results; gc.collect()

# === Threshold Sensitivity ===
print('\n=== Threshold Sensitivity ===')
all_thresh = []
for thresh in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
    scaling = []
    for n in sorted(df3.n_qubits.unique()):
        sub = df3[df3.n_qubits == n]
        page_val = get_page_value(n)
        threshold = thresh * page_val
        dcs = []
        for t in sub.trial.unique():
            td = sub[sub.trial == t].sort_values('depth')
            exc = td[td.entanglement_entropy >= threshold]
            if len(exc) > 0:
                dcs.append(int(exc.iloc[0]['depth']))
        if dcs and len(dcs) >= 5:
            scaling.append({'n': n, 'dc_mean': np.mean(dcs), 'dc_std': np.std(dcs),
                           'n_found': len(dcs), 'n_total': sub.trial.nunique()})
    if len(scaling) >= 3:
        sdf = pd.DataFrame(scaling)
        valid = sdf[sdf.dc_mean > 0]
        log_n = np.log(valid.n.values.astype(float))
        log_dc = np.log(valid.dc_mean.values.astype(float))
        slope, intercept, r_value, p_value, std_err = sp_stats.linregress(log_n, log_dc)
        all_thresh.append({
            'threshold_frac': thresh, 'alpha': slope, 'alpha_std': std_err,
            'r_squared': r_value**2, 'p_value': p_value, 'n_points': len(valid),
        })
        print(f'  thresh={thresh}: alpha={slope:.3f}±{std_err:.3f}, R²={r_value**2:.4f}')

df_thresh = pd.DataFrame(all_thresh)
df_thresh.to_csv(f'{OUTPUT_DIR}/threshold_sensitivity.csv', index=False)

# Save summary
total_time = time.time() - start_total
summary = {
    'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
    'total_time_seconds': round(total_time, 1),
    'page_values': {str(n): round(get_page_value(n), 6) for n in range(3, 11)},
    'records': {
        'exp3': len(df3), 'exp4': len(df4), 'exp5': len(df5),
        'exp6': len(df6), 'exp7': len(df7), 'exp8': len(df8),
        'threshold_sensitivity': len(df_thresh),
    }
}
with open(f'{OUTPUT_DIR}/summary_v2.json', 'w') as f:
    json.dump(summary, f, indent=2)

print(f'\n=== ALL E3-E8 COMPLETE ===')
print(f'Total time: {total_time:.0f}s ({total_time/60:.1f}min)')
