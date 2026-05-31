#!/usr/bin/env python3
"""Compute no-optimization baselines from raw experimental data."""
import pandas as pd
import numpy as np
import json
from pathlib import Path

def compute_baseline_stats(data_dir: Path, output_dir: Path):
    """Compute baseline statistics for all experiments."""
    results = {}
    
    for csv_file in sorted(data_dir.glob('exp*.csv')):
        df = pd.read_csv(csv_file)
        exp_name = csv_file.stem
        
        baseline = {}
        
        # Original circuit statistics
        if 'original_size' in df.columns:
            baseline['original_gate_stats'] = {
                'mean': float(df['original_size'].mean()),
                'std': float(df['original_size'].std()),
                'median': float(df['original_size'].median()),
                'min': int(df['original_size'].min()),
                'max': int(df['original_size'].max()),
            }
        
        # Per-(n,d) statistics
        group_cols = [c for c in ['n_qubits', 'depth'] if c in df.columns]
        if group_cols and 'original_size' in df.columns:
            grouped = df.groupby(group_cols)['original_size'].agg(['mean', 'std', 'count'])
            baseline['per_config'] = grouped.reset_index().to_dict('records')
        
        # Null hypothesis: random gate removal
        # If we randomly remove k gates from a circuit of size N,
        # the probability of preserving functionality is approximately (1-k/N)^N for random circuits
        if 'original_size' in df.columns and 'optimized_size' in df.columns:
            df['gates_removed'] = df['original_size'] - df['optimized_size']
            baseline['random_removal_null'] = {
                'mean_removal': float(df['gates_removed'].mean()),
                'theoretical_random_success_rate': float(
                    np.mean((1 - df['gates_removed'] / df['original_size']) ** df['original_size'])
                ),
                'actual_success_rate': float(df['success'].mean()) if 'success' in df.columns else None,
            }
        
        # Effect size: how much better than random is the optimizer?
        if 'success' in df.columns:
            baseline['observed_success_rate'] = float(df['success'].mean())
            baseline['n_trials'] = len(df)
            # Wilson score interval for binomial proportion
            from scipy.stats import norm
            p = baseline['observed_success_rate']
            n = baseline['n_trials']
            z = norm.ppf(0.975)
            denom = 1 + z**2/n
            center = (p + z**2/(2*n)) / denom
            margin = z * np.sqrt((p*(1-p) + z**2/(4*n))/n) / denom
            baseline['success_rate_95ci'] = [float(max(0, center - margin)), float(min(1, center + margin))]
        
        results[exp_name] = baseline
    
    output_path = output_dir / 'baseline_statistics.json'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert numpy types for JSON serialization
    def convert(o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, np.ndarray): return o.tolist()
        if isinstance(o, float) and np.isnan(o): return None
        return o
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=convert)
    print(f"Baseline statistics saved to {output_path}")
    return results

if __name__ == '__main__':
    data_dir = Path('D:/Desktop/Q-research/data/raw')
    output_dir = Path('D:/Desktop/Q-research/data/processed')
    compute_baseline_stats(data_dir, output_dir)
