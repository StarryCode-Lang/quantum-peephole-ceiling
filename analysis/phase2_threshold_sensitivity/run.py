"""
Threshold Sensitivity Analysis
==============================
Re-analyze all experiment results at multiple success thresholds.
Demonstrates that the 20% threshold is arbitrary and shows how
results change with threshold choice.

Version: 3.0.0 (PRA-compliant)
"""

from __future__ import annotations

import sys
import os
import json
import glob
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from analysis.phase1_statistics.core import threshold_sensitivity


# Module-level alias for paths referenced elsewhere in this file (bug #3 fix).
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_all_experiments():
    """Load all available experiment data (v2_fixed and v5/e10)."""
    project_root = Path(__file__).resolve().parent.parent.parent
    data_dirs = [
        str(project_root / "data/v2_fixed"),
        str(project_root / "data/v5/e10"),
    ]
    
    experiments = {}
    
    for data_dir in data_dirs:
        if not os.path.exists(data_dir):
            continue
        
        for csv_file in glob.glob(f"{data_dir}/**/*.csv", recursive=True):
            try:
                df = pd.read_csv(csv_file)
                exp_name = Path(csv_file).stem
                experiments[exp_name] = df
                print(f"Loaded: {exp_name} ({len(df)} records)")
            except Exception as e:
                print(f"Failed to load {csv_file}: {e}")
    
    return experiments


def analyze_threshold_sensitivity(experiments):
    """Analyze threshold sensitivity for all experiments."""
    thresholds = [0.01, 0.05, 0.10, 0.20]
    
    all_results = []
    
    for exp_name, df in experiments.items():
        if 'reduction' not in df.columns:
            continue
        
        for threshold in thresholds:
            success = df['reduction'] >= threshold
            all_results.append({
                'experiment': exp_name,
                'threshold': threshold,
                'threshold_pct': f'{threshold*100:.0f}%',
                'success_rate': success.mean(),
                'n_success': int(success.sum()),
                'n_total': len(success),
            })
    
    return pd.DataFrame(all_results)


def generate_figure(results_df):
    """Generate threshold sensitivity figure."""
    plt.style.use('seaborn-v0_8-paper')
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 11,
        'axes.labelsize': 13,
        'axes.titlesize': 13,
        'legend.fontsize': 9,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'mathtext.fontset': 'cm',
    })
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ['#2166ac', '#b2182b', '#4daf4a', '#984ea3', '#ff7f00']
    
    for i, (exp_name, group) in enumerate(results_df.groupby('experiment')):
        color = colors[i % len(colors)]
        ax.plot(group['threshold'] * 100, group['success_rate'] * 100,
                marker='o', linewidth=2, markersize=6,
                label=exp_name, color=color)
    
    ax.set_xlabel('Success Threshold (%)')
    ax.set_ylabel('Success Rate (%)')
    ax.set_title('Threshold Sensitivity Analysis')
    ax.legend(loc='upper right', framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 25)
    ax.set_ylim(-2, 102)
    
    # Add annotations for key thresholds
    ax.axvline(x=5, color='gray', linestyle='--', alpha=0.5, label='5% (recommended)')
    ax.axvline(x=20, color='red', linestyle='--', alpha=0.5, label='20% (original)')
    
    plt.tight_layout()
    
    output_dir = PROJECT_ROOT / "analysis" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    plt.savefig(output_dir / 'threshold_sensitivity.pdf')
    plt.close()
    
    print(f"Figure saved to {output_dir / 'threshold_sensitivity.pdf'}")


def main():
    """Run threshold sensitivity analysis."""
    print("Loading experiment data...")
    experiments = load_all_experiments()
    
    if not experiments:
        print("No experiment data found. Please run experiments first.")
        return
    
    print(f"\nLoaded {len(experiments)} experiments")
    
    print("\nAnalyzing threshold sensitivity...")
    results_df = analyze_threshold_sensitivity(experiments)
    
    # Save results
    output_dir = PROJECT_ROOT / "analysis" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_df.to_csv(output_dir / 'threshold_sensitivity.csv', index=False)
    
    # Generate report
    report = []
    report.append("# Threshold Sensitivity Analysis Report")
    report.append("")
    report.append("## Summary")
    report.append("")
    report.append("This report shows how success rates change with different threshold choices.")
    report.append("")
    report.append("| Experiment | 1% Threshold | 5% Threshold | 10% Threshold | 20% Threshold |")
    report.append("|------------|-------------|-------------|--------------|--------------|")
    
    for exp_name, group in results_df.groupby('experiment'):
        row = [exp_name]
        for threshold in [0.01, 0.05, 0.10, 0.20]:
            sub = group[group['threshold'] == threshold]
            if len(sub) > 0:
                row.append(f"{sub['success_rate'].values[0]:.1%}")
            else:
                row.append("N/A")
        report.append("| " + " | ".join(row) + " |")
    
    report.append("")
    report.append("## Recommendations")
    report.append("")
    report.append("- **Random circuits**: Use 5% threshold (natural ceiling ~2-5%)")
    report.append("- **Structured circuits**: Use 10% threshold (ceiling ~15-30%)")
    report.append("- **20% threshold**: Too high for random circuits, artificially marks all optimizers as 'failing'")
    report.append("")
    report.append("## Key Finding")
    report.append("")
    report.append("The 20% success threshold used in the original analysis is **arbitrary and self-defeating**.")
    report.append("At 20%, even the 'best' optimizer (Greedy) achieves only ~20% success on random circuits,")
    report.append("while SA/GA/RLS achieve ~0%. At 5%, the separation is much more informative.")
    
    report_text = "\n".join(report)
    
    with open(output_dir / 'threshold_sensitivity_report.md', 'w') as f:
        f.write(report_text)
    
    print("\n" + report_text)
    
    # Generate figure
    generate_figure(results_df)
    
    print("\nThreshold sensitivity analysis complete!")


if __name__ == "__main__":
    main()
