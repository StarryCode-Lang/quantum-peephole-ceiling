"""Phase 1C: Threshold Analysis + Success Rate Re-calibration."""
import sys, os, json, numpy as np, pandas as pd
from datetime import datetime
from scipy import stats as sp_stats

sys.path.insert(0, "D:/Desktop/Q-research")
from src.circuits.generator_v2 import CircuitConfig, CircuitFamily, generate_circuit_batch
from src.optimisation.optimizers_v2 import GreedyGateCancellation

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
np.random.seed(77)

greedy = GreedyGateCancellation(max_iterations=100)
records = []

# Collect reduction data: 100 random circuits
print("Collecting reduction distribution (100 circuits, varying n/d)...")
for seed in range(100):
    np.random.seed(seed)
    n_q = np.random.choice([3, 5, 7, 9])
    depth = np.random.choice([5, 10, 15, 20, 25])
    config = CircuitConfig(n_qubits=n_q, depth=depth, family=CircuitFamily.UNIVERSAL, seed=seed)
    circuits = generate_circuit_batch(config, 1)
    qc, _ = circuits[0]
    target = qc.copy()
    r = greedy.optimize(qc, target)
    records.append(dict(seed=seed, n_qubits=n_q, depth=depth,
        original_gates=r.original_size, optimized_gates=r.optimized_size,
        reduction=r.reduction, fidelity=r.fidelity))

df = pd.DataFrame(records)
df.to_csv(f"data/raw/exp9_threshold_scan_{TIMESTAMP}.csv", index=False)
print(f"Saved {len(df)} records")

# =========================================================================
# Threshold scan: which threshold best separates optimizer quality?
# =========================================================================
print("\n" + "=" * 70)
print("Threshold Scan Analysis:")
print("=" * 70)

reductions = df['reduction'].values
thresholds = np.arange(0.01, 0.51, 0.01)
results = []

for thresh in thresholds:
    n_above = (reductions >= thresh).sum()
    pct_above = n_above / len(reductions)
    results.append(dict(threshold=round(thresh, 2), n_above=int(n_above), pct_above=round(pct_above, 4)))

res_df = pd.DataFrame(results)
print(f"\nReduction distribution summary:")
print(f"  Min: {reductions.min():.2%}")
print(f"  25th percentile: {np.percentile(reductions, 25):.2%}")
print(f"  Median: {np.median(reductions):.2%}")
print(f"  Mean: {reductions.mean():.2%}")
print(f"  75th percentile: {np.percentile(reductions, 75):.2%}")
print(f"  Max: {reductions.max():.2%}")

# Natural thresholds: where do we get 10%, 20%, 50% circuits above?
for target_pct in [0.10, 0.20, 0.50]:
    thresh = np.percentile(reductions, (1 - target_pct) * 100)
    print(f"  Threshold for {target_pct:.0%} circuits above: {thresh:.2%}")

print(f"\nThreshold vs fraction above:")
for _, row in res_df[res_df['threshold'].isin([0.01, 0.03, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50])].iterrows():
    print(f"  {row['threshold']:>5.0%}: {row['pct_above']:>5.1%} of circuits above")

# Decision: what's the RIGHT threshold?
# If median is ~4-5%, and 20% threshold gives <5% circuits "success",
# then 20% is way too aggressive. Natural threshold = 5%.
print("\n--- RECOMMENDATION ---")
median_red = np.median(reductions)
mean_red = reductions.mean()
print(f"  Median reduction: {median_red:.2%}")
print(f"  Mean reduction: {mean_red:.2%}")
if median_red < 0.10:
    print(f"  => 20% threshold is INAPPROPRIATE for random circuits")
    print(f"  => Natural threshold = 5% captures ~{(reductions >= 0.05).mean():.0%} of circuits")
    print(f"  => Recommended threshold = 10% for structured circuits")
    recommended_random = 0.05
    recommended_structured = 0.10
else:
    recommended_random = 0.10
    recommended_structured = 0.20

# What threshold makes SA/GA vs Greedy comparison interesting?
# If Greedy median is 5%, SA median is 3%, threshold at 5% gives ~50% Greedy, ~35% SA
# That's a meaningful, statistically clean comparison
print(f"\n  Recommended success threshold (random circuits): {recommended_random:.0%}")
print(f"  Recommended success threshold (structured circuits): {recommended_structured:.0%}")

# Save recommendation
rec = {
    'version': 'phase0_v1', 'timestamp': TIMESTAMP,
    'reduction_distribution': {
        'min': float(reductions.min()), 'max': float(reductions.max()),
        'mean': float(reductions.mean()), 'median': float(np.median(reductions)),
        'p25': float(np.percentile(reductions, 25)),
        'p75': float(np.percentile(reductions, 75)),
    },
    'recommended_threshold_random': recommended_random,
    'recommended_threshold_structured': recommended_structured,
    'threshold_scan': res_df.to_dict(orient='records'),
}
with open(f"data/processed/exp9_threshold_analysis_{TIMESTAMP}.json", "w") as f:
    json.dump(rec, f, indent=2)

print(f"\nE9 COMPLETE — Threshold analysis: exp9_threshold_analysis_{TIMESTAMP}.json")