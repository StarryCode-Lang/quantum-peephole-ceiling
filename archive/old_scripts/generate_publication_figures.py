"""
Publication-Quality Figure Generation - Fixed Version
Generates all figures for the research paper.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Set style for publication-quality figures
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")


class PublicationFigureGenerator:
    """Generate publication-quality figures."""
    
    def __init__(self, data_dir: str = 'data/raw', output_dir: str = 'figures'):
        self.data_dir = data_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Load all data
        self.data = self._load_all_data()
    
    def _load_all_data(self) -> Dict[str, pd.DataFrame]:
        """Load all experimental data."""
        data = {}
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.csv'):
                filepath = os.path.join(self.data_dir, filename)
                df = pd.read_csv(filepath)
                
                # Normalize column names
                df = self._normalize_columns(df)
                
                # Extract experiment name
                if 'basic' in filename:
                    data['basic'] = df
                elif 'entanglement' in filename:
                    data['entanglement'] = df
                elif 'randomness' in filename:
                    data['randomness'] = df
                elif 'scaling' in filename:
                    data['scaling'] = df
                elif 'algorithm' in filename:
                    data['algorithm'] = df
                elif 'landscape' in filename:
                    data['landscape'] = df
        
        return data
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names."""
        # Rename columns if needed
        column_mapping = {
            'n_qubits': 'num_qubits',
            'original_gate_count': 'gate_count',
            'optimized_gate_count': 'optimized_size'
        }
        
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns and new_name not in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        return df
    
    def generate_figure_1_phase_diagrams(self):
        """Figure 1: Phase diagrams showing success rate vs circuit parameters."""
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        # 1a: Success rate vs depth
        if 'basic' in self.data:
            df = self.data['basic']
            success_by_depth = df.groupby('depth')['success'].mean()
            
            axes[0].plot(success_by_depth.index, success_by_depth.values, 
                        'b-', linewidth=2, marker='o', markersize=4)
            axes[0].set_xlabel('Circuit Depth', fontsize=12)
            axes[0].set_ylabel('Success Rate', fontsize=12)
            axes[0].set_title('(a) Success Rate vs Depth', fontsize=12)
            axes[0].set_ylim(0, 1)
            axes[0].grid(True, alpha=0.3)
        
        # 1b: Success rate vs entanglement density
        if 'entanglement' in self.data:
            df = self.data['entanglement']
            success_by_density = df.groupby('entanglement_density')['success'].mean()
            
            axes[1].plot(success_by_density.index, success_by_density.values, 
                        'r-', linewidth=2, marker='s', markersize=4)
            axes[1].set_xlabel('Entanglement Density', fontsize=12)
            axes[1].set_ylabel('Success Rate', fontsize=12)
            axes[1].set_title('(b) Success Rate vs Entanglement Density', fontsize=12)
            axes[1].set_ylim(0, 1)
            axes[1].grid(True, alpha=0.3)
        
        # 1c: Success rate vs randomness
        if 'randomness' in self.data:
            df = self.data['randomness']
            success_by_randomness = df.groupby('randomness')['success'].mean()
            
            axes[2].plot(success_by_randomness.index, success_by_randomness.values, 
                        'g-', linewidth=2, marker='^', markersize=4)
            axes[2].set_xlabel('Randomness Parameter', fontsize=12)
            axes[2].set_ylabel('Success Rate', fontsize=12)
            axes[2].set_title('(c) Success Rate vs Randomness', fontsize=12)
            axes[2].set_ylim(0, 1)
            axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        save_path = os.path.join(self.output_dir, 'fig1_phase_diagrams.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Figure 1 saved to: {save_path}")
    
    def generate_figure_2_scaling_plots(self):
        """Figure 2: Scaling behavior analysis."""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        if 'scaling' in self.data:
            df = self.data['scaling']
            
            # 2a: Success rate vs depth for different qubit counts
            if 'num_qubits' in df.columns:
                for n_qubits in sorted(df['num_qubits'].unique()):
                    subset = df[df['num_qubits'] == n_qubits]
                    success_by_depth = subset.groupby('depth')['success'].mean()
                    
                    axes[0].plot(success_by_depth.index, success_by_depth.values, 
                               linewidth=2, label=f'n={n_qubits}')
                
                axes[0].set_xlabel('Circuit Depth', fontsize=12)
                axes[0].set_ylabel('Success Rate', fontsize=12)
                axes[0].set_title('(a) Scaling Behavior', fontsize=12)
                axes[0].legend()
                axes[0].grid(True, alpha=0.3)
            
            # 2b: Critical depth vs qubit count
            if 'num_qubits' in df.columns:
                critical_depths = []
                for n_qubits in sorted(df['num_qubits'].unique()):
                    subset = df[df['num_qubits'] == n_qubits]
                    success_by_depth = subset.groupby('depth')['success'].mean()
                    
                    # Find critical depth (where success = 0.5)
                    depths = success_by_depth.index.values
                    successes = success_by_depth.values
                    
                    if len(successes) > 1:
                        # Interpolate to find critical depth
                        from scipy.interpolate import interp1d
                        f = interp1d(successes, depths, bounds_error=False, fill_value='extrapolate')
                        critical_depth = f(0.5)
                        critical_depths.append((n_qubits, critical_depth))
                
                if critical_depths:
                    n_values, d_values = zip(*critical_depths)
                    
                    # Fit power law: d_c ~ n^alpha
                    log_n = np.log(n_values)
                    log_d = np.log(d_values)
                    slope, intercept, r_value, p_value, std_err = stats.linregress(log_n, log_d)
                    
                    axes[1].scatter(n_values, d_values, s=100, c='blue', zorder=5)
                    
                    # Plot fit
                    n_fit = np.linspace(min(n_values), max(n_values), 100)
                    d_fit = np.exp(intercept) * n_fit**slope
                    axes[1].plot(n_fit, d_fit, 'r--', linewidth=2, 
                               label=f'$d_c \\sim n^{{{slope:.2f}}}$, $R^2={r_value**2:.3f}$')
                    
                    axes[1].set_xlabel('Number of Qubits (n)', fontsize=12)
                    axes[1].set_ylabel('Critical Depth ($d_c$)', fontsize=12)
                    axes[1].set_title('(b) Critical Depth Scaling', fontsize=12)
                    axes[1].legend()
                    axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        save_path = os.path.join(self.output_dir, 'fig2_scaling_plots.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Figure 2 saved to: {save_path}")
    
    def generate_figure_3_landscape_visualizations(self):
        """Figure 3: Landscape analysis across phases."""
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        if 'landscape' in self.data:
            df = self.data['landscape']
            
            # 3a: Ruggedness by region
            if 'region' in df.columns:
                regions = df['region'].unique()
                ruggedness_by_region = df.groupby('region')['landscape_ruggedness'].mean()
                
                axes[0].bar(range(len(regions)), ruggedness_by_region.values)
                axes[0].set_xticks(range(len(regions)))
                axes[0].set_xticklabels(regions, rotation=45, ha='right')
                axes[0].set_ylabel('Ruggedness', fontsize=12)
                axes[0].set_title('(a) Landscape Ruggedness', fontsize=12)
            
            # 3b: Gradient norm by region
            if 'region' in df.columns:
                gradient_by_region = df.groupby('region')['landscape_gradient_norm'].mean()
                
                axes[1].bar(range(len(regions)), gradient_by_region.values, color='orange')
                axes[1].set_xticks(range(len(regions)))
                axes[1].set_xticklabels(regions, rotation=45, ha='right')
                axes[1].set_ylabel('Gradient Norm', fontsize=12)
                axes[1].set_title('(b) Gradient Norm', fontsize=12)
            
            # 3c: Local minima by region
            if 'region' in df.columns:
                minima_by_region = df.groupby('region')['landscape_local_minima'].mean()
                
                axes[2].bar(range(len(regions)), minima_by_region.values, color='green')
                axes[2].set_xticks(range(len(regions)))
                axes[2].set_xticklabels(regions, rotation=45, ha='right')
                axes[2].set_ylabel('Number of Local Minima', fontsize=12)
                axes[2].set_title('(c) Local Minima Count', fontsize=12)
        
        plt.tight_layout()
        save_path = os.path.join(self.output_dir, 'fig3_landscape_visualizations.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Figure 3 saved to: {save_path}")
    
    def generate_figure_4_statistical_plots(self):
        """Figure 4: Statistical analysis plots."""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        if 'algorithm' in self.data:
            df = self.data['algorithm']
            
            # 4a: Box plot of gate reduction by algorithm
            if 'algorithm' in df.columns and 'gate_reduction' in df.columns:
                algorithms = df['algorithm'].unique()
                data_by_algo = [df[df['algorithm'] == algo]['gate_reduction'].values 
                               for algo in algorithms]
                
                bp = axes[0].boxplot(data_by_algo, labels=algorithms, patch_artist=True)
                
                colors = plt.cm.Set3(np.linspace(0, 1, len(algorithms)))
                for patch, color in zip(bp['boxes'], colors):
                    patch.set_facecolor(color)
                
                axes[0].set_xlabel('Algorithm', fontsize=12)
                axes[0].set_ylabel('Gate Reduction', fontsize=12)
                axes[0].set_title('(a) Algorithm Comparison', fontsize=12)
                axes[0].tick_params(axis='x', rotation=45)
            
            # 4b: Violin plot of gate reduction by algorithm
            if 'algorithm' in df.columns and 'gate_reduction' in df.columns:
                sns.violinplot(data=df, x='algorithm', y='gate_reduction', ax=axes[1])
                axes[1].set_xlabel('Algorithm', fontsize=12)
                axes[1].set_ylabel('Gate Reduction', fontsize=12)
                axes[1].set_title('(b) Gate Reduction Distribution', fontsize=12)
                axes[1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        save_path = os.path.join(self.output_dir, 'fig4_statistical_plots.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Figure 4 saved to: {save_path}")
    
    def generate_figure_5_combined_phase_diagram(self):
        """Figure 5: Combined phase diagram."""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        if 'scaling' in self.data:
            df = self.data['scaling']
            
            if 'num_qubits' in df.columns:
                # Create 2D phase diagram: qubits vs depth
                pivot = df.pivot_table(
                    values='success', 
                    index='num_qubits', 
                    columns='depth', 
                    aggfunc='mean'
                )
                
                im = ax.imshow(pivot.values, aspect='auto', origin='lower', 
                              cmap='RdYlBu_r', extent=[pivot.columns[0], pivot.columns[-1],
                                                       pivot.index[0], pivot.index[-1]])
                
                # Add contour lines
                contour = ax.contour(pivot.columns, pivot.index, pivot.values, 
                                    levels=[0.3, 0.5, 0.7], colors='black', linewidths=2)
                ax.clabel(contour, inline=True, fontsize=10)
                
                plt.colorbar(im, ax=ax, label='Success Rate')
                ax.set_xlabel('Circuit Depth', fontsize=12)
                ax.set_ylabel('Number of Qubits', fontsize=12)
                ax.set_title('Phase Diagram: Success Rate', fontsize=14)
        
        plt.tight_layout()
        save_path = os.path.join(self.output_dir, 'fig5_combined_phase_diagram.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Figure 5 saved to: {save_path}")
    
    def generate_all_figures(self):
        """Generate all figures."""
        print("="*60)
        print("GENERATING PUBLICATION-QUALITY FIGURES")
        print("="*60)
        
        self.generate_figure_1_phase_diagrams()
        self.generate_figure_2_scaling_plots()
        self.generate_figure_3_landscape_visualizations()
        self.generate_figure_4_statistical_plots()
        self.generate_figure_5_combined_phase_diagram()
        
        print("\n" + "="*60)
        print("ALL FIGURES GENERATED")
        print("="*60)


if __name__ == '__main__':
    generator = PublicationFigureGenerator()
    generator.generate_all_figures()
