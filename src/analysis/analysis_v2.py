"""
Statistical Analysis - Production Quality v2.1
==============================================
Comprehensive statistical analysis with proper hypothesis testing,
effect sizes, confidence intervals, and finite-size scaling.

Author: Q-research Team
Version: 2.1.0
"""

from __future__ import annotations

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Callable, Union
import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from scipy.optimize import curve_fit, minimize
from scipy.ndimage import uniform_filter1d

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

class AnalysisConfig:
    """Configuration for statistical analysis."""
    
    def __init__(self, data_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path('D:/Desktop/Q-research/data/raw')
        self.output_dir = output_dir or Path('D:/Desktop/Q-research/data/processed')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.alpha = 0.05  # Significance level
        self.ci = 0.95  # Confidence interval
        self.n_bootstrap = 10000  # Bootstrap samples (increased for publication)


# ============================================================================
# Bootstrap Utilities
# ============================================================================

def bootstrap_ci(data: np.ndarray, 
                 statistic: Callable = np.mean,
                 n_bootstrap: int = 10000,
                 ci: float = 0.95,
                 seed: int = 42) -> Tuple[float, float, float]:
    """
    Calculate bootstrap confidence interval.
    
    Returns:
        Tuple of (point_estimate, ci_lower, ci_upper)
    """
    rng = np.random.RandomState(seed)
    point = statistic(data)
    
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        sample = rng.choice(data, size=len(data), replace=True)
        bootstrap_stats.append(statistic(sample))
    
    alpha = (1 - ci) / 2
    ci_lower = np.percentile(bootstrap_stats, 100 * alpha)
    ci_upper = np.percentile(bootstrap_stats, 100 * (1 - alpha))
    
    return point, ci_lower, ci_upper


def bootstrap_corr(x: np.ndarray, y: np.ndarray,
                   n_bootstrap: int = 10000,
                   seed: int = 42) -> Tuple[float, float, float]:
    """
    Calculate bootstrap confidence interval for Pearson correlation.
    
    Returns:
        Tuple of (correlation, ci_lower, ci_upper)
    """
    rng = np.random.RandomState(seed)
    r, _ = sp_stats.pearsonr(x, y)
    
    bootstrap_rs = []
    for _ in range(n_bootstrap):
        idx = rng.choice(len(x), size=len(x), replace=True)
        try:
            r_boot, _ = sp_stats.pearsonr(x[idx], y[idx])
            bootstrap_rs.append(r_boot)
        except Exception:
            continue
    
    if len(bootstrap_rs) < 100:
        return r, r, r
    
    ci_lower = np.percentile(bootstrap_rs, 2.5)
    ci_upper = np.percentile(bootstrap_rs, 97.5)
    
    return r, ci_lower, ci_upper


# ============================================================================
# Effect Sizes
# ============================================================================

def cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """
    Calculate Cohen's d effect size.
    
    Returns:
        Effect size (small: 0.2, medium: 0.5, large: 0.8)
    """
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    
    if pooled_std == 0:
        return 0.0
    
    return (np.mean(group1) - np.mean(group2)) / pooled_std


def cliffs_delta(group1: np.ndarray, group2: np.ndarray) -> float:
    """
    Calculate Cliff's delta (non-parametric effect size).
    
    Returns:
        Effect size (small: 0.147, medium: 0.33, large: 0.474)
    """
    n1, n2 = len(group1), len(group2)
    
    # Count pairs
    greater = 0
    less = 0
    
    for x in group1:
        for y in group2:
            if x > y:
                greater += 1
            elif x < y:
                less += 1
    
    return (greater - less) / (n1 * n2)


# ============================================================================
# Phase Transition Detection
# ============================================================================

class PhaseTransitionDetector:
    """Detect phase transitions in experimental data."""
    
    @staticmethod
    def sigmoid_fit(depths: np.ndarray, success_rates: np.ndarray) -> Dict[str, Any]:
        """
        Fit success rate to sigmoid function.
        
        Model: S(d) = 1 / (1 + exp(-beta * (d - dc)))
        
        Returns:
            Dictionary with 'dc', 'beta', 'r_squared', and bootstrap CIs
        """
        def sigmoid(d, dc, beta):
            return 1.0 / (1.0 + np.exp(-beta * (d - dc)))
        
        # Initial guess
        dc_guess = depths[len(depths) // 2]
        beta_guess = 1.0
        
        try:
            popt, pcov = curve_fit(sigmoid, depths, success_rates, 
                                   p0=[dc_guess, beta_guess],
                                   bounds=([0, 0], [np.inf, np.inf]))
            
            dc, beta = popt
            dc_err, beta_err = np.sqrt(np.diag(pcov))
            
            # Calculate R^2
            predicted = sigmoid(depths, dc, beta)
            ss_res = np.sum((success_rates - predicted) ** 2)
            ss_tot = np.sum((success_rates - np.mean(success_rates)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
            
            return {
                'dc': dc,
                'dc_err': dc_err,
                'beta': beta,
                'beta_err': beta_err,
                'r_squared': r_squared,
                'is_sigmoid': r_squared > 0.8,  # Threshold for sigmoid-like behavior
            }
        except Exception as e:
            logger.warning(f"Sigmoid fit failed: {e}")
            return {'dc': np.nan, 'dc_err': np.nan, 'beta': np.nan, 
                    'beta_err': np.nan, 'r_squared': 0.0, 'is_sigmoid': False}
    
    @staticmethod
    def pelt(data: np.ndarray, penalty: float = 1.0) -> List[int]:
        """
        Pruned Exact Linear Time (PELT) algorithm for change point detection.
        
        Returns:
            List of change point indices
        """
        n = len(data)
        if n < 2:
            return []
        
        def cost(start: int, end: int) -> float:
            segment = data[start:end]
            if len(segment) == 0:
                return 0.0
            return np.sum((segment - np.mean(segment))**2)
        
        # Dynamic programming
        F = np.zeros(n + 1)
        cp = [[] for _ in range(n + 1)]
        
        for t in range(1, n + 1):
            min_cost = float('inf')
            best_s = 0
            
            for s in range(t):
                c = F[s] + cost(s, t) + penalty
                if c < min_cost:
                    min_cost = c
                    best_s = s
            
            F[t] = min_cost
            cp[t] = cp[best_s] + [best_s] if best_s > 0 else []
        
        return cp[n]
    
    @staticmethod
    def maximum_gradient(data: np.ndarray, parameter_values: np.ndarray) -> float:
        """
        Find point of maximum gradient.
        
        Returns:
            Parameter value at maximum gradient
        """
        gradient = np.gradient(data)
        return parameter_values[np.argmax(np.abs(gradient))]


# ============================================================================
# Finite-Size Scaling
# ============================================================================

class FiniteSizeScaling:
    """Finite-size scaling analysis for phase transitions."""
    
    @staticmethod
    def fss_collapse(n_values: np.ndarray, d_values: np.ndarray, 
                     success_rates: np.ndarray,
                     dc_guess: float, nu_guess: float, beta_guess: float) -> Dict[str, Any]:
        """
        Perform finite-size scaling collapse.
        
        Model: S(n, d) = f((d - dc) * n^(1/nu))
        where f is a universal scaling function.
        
        Args:
            n_values: Array of system sizes
            d_values: Array of depths (same length as n_values)
            success_rates: Array of success rates
            dc_guess: Initial guess for critical depth
            nu_guess: Initial guess for correlation length exponent
            beta_guess: Initial guess for order parameter exponent
        
        Returns:
            Dictionary with fitted parameters and quality metrics
        """
        def scaling_function(x, a, b, c):
            """Universal scaling function (sigmoid-like)."""
            return a / (1 + np.exp(-b * (x - c)))
        
        def residuals(params):
            dc, nu_inv, beta = params
            x = (d_values - dc) * (n_values ** nu_inv)
            # Fit scaling function
            try:
                popt, _ = curve_fit(scaling_function, x, success_rates, 
                                   p0=[1, 1, 0], maxfev=5000)
                predicted = scaling_function(x, *popt)
                return np.sum((success_rates - predicted) ** 2)
            except:
                return 1e10
        
        # Optimize
        result = minimize(residuals, [dc_guess, 1.0/nu_guess, beta_guess],
                         method='Nelder-Mead')
        
        if result.success:
            dc, nu_inv, beta = result.x
            nu = 1.0 / nu_inv if nu_inv != 0 else np.inf
            
            # Calculate collapse quality (R^2)
            x = (d_values - dc) * (n_values ** nu_inv)
            try:
                popt, _ = curve_fit(scaling_function, x, success_rates, p0=[1, 1, 0])
                predicted = scaling_function(x, *popt)
                ss_res = np.sum((success_rates - predicted) ** 2)
                ss_tot = np.sum((success_rates - np.mean(success_rates)) ** 2)
                r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
            except:
                r_squared = 0.0
            
            return {
                'dc': dc,
                'nu': nu,
                'beta': beta,
                'r_squared': r_squared,
                'converged': True,
            }
        else:
            return {
                'dc': np.nan, 'nu': np.nan, 'beta': np.nan,
                'r_squared': 0.0, 'converged': False,
            }
    
    @staticmethod
    def binder_cumulant(data: np.ndarray) -> float:
        """
        Calculate Binder cumulant for detecting phase transitions.
        
        U = 1 - <m^4> / (3<m^2>^2)
        
        For a proper order parameter, U -> 2/3 in ordered phase and U -> 0 in disordered phase.
        Crossing of U_L for different L indicates critical point.
        """
        if len(data) == 0:
            return 0.0
        
        m2 = np.mean(data ** 2)
        m4 = np.mean(data ** 4)
        
        if m2 == 0:
            return 0.0
        
        return 1.0 - m4 / (3.0 * m2 ** 2)


# ============================================================================
# Critical Exponent Estimation
# ============================================================================

class CriticalExponentEstimator:
    """Estimate critical exponents from experimental data."""
    
    @staticmethod
    def power_law_fit(x: np.ndarray, y: np.ndarray, x_c: float) -> Tuple[float, float, float, float]:
        """
        Fit data to power law: y = A * |x - x_c|^beta.
        
        Returns:
            Tuple of (A, beta, R_squared, std_error)
        """
        mask = np.abs(x - x_c) > 0.01
        x_fit = x[mask]
        y_fit = y[mask]
        
        if len(x_fit) < 3:
            return 0.0, 0.0, 0.0, 0.0
        
        log_x = np.log(np.abs(x_fit - x_c) + 1e-10)
        log_y = np.log(np.abs(y_fit) + 1e-10)
        
        slope, intercept, r_value, p_value, std_err = sp_stats.linregress(log_x, log_y)
        
        return np.exp(intercept), slope, r_value**2, std_err
    
    @staticmethod
    def log_log_regression(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float, float]:
        """
        Perform log-log regression.
        
        Returns:
            Tuple of (slope, intercept, R_squared, std_error)
        """
        log_x = np.log(np.abs(x) + 1e-10)
        log_y = np.log(np.abs(y) + 1e-10)
        
        slope, intercept, r_value, p_value, std_err = sp_stats.linregress(log_x, log_y)
        
        return slope, intercept, r_value**2, std_err


# ============================================================================
# Landscape Analysis
# ============================================================================

class LandscapeAnalyzer:
    """Analyze optimization landscape properties."""
    
    @staticmethod
    def ruggedness(fitness_values: np.ndarray) -> float:
        """
        Calculate landscape ruggedness.
        
        Returns:
            Ruggedness measure (higher = more rugged)
        """
        if len(fitness_values) < 2:
            return 0.0
        
        # Normalized autocorrelation at lag 1
        if np.std(fitness_values) == 0:
            return 0.0
        
        autocorr = np.corrcoef(fitness_values[:-1], fitness_values[1:])[0, 1]
        return 1.0 - autocorr if not np.isnan(autocorr) else 0.0
    
    @staticmethod
    def correlation_length(fitness_values: np.ndarray) -> float:
        """
        Estimate correlation length of fitness landscape.
        """
        if len(fitness_values) < 2:
            return 0.0
        
        # Find lag where autocorrelation drops below 1/e
        for lag in range(1, len(fitness_values) // 2):
            if np.std(fitness_values[:-lag]) == 0 or np.std(fitness_values[lag:]) == 0:
                continue
            autocorr = np.corrcoef(fitness_values[:-lag], fitness_values[lag:])[0, 1]
            if autocorr < np.exp(-1):
                return float(lag)
        
        return float(len(fitness_values) // 2)


# ============================================================================
# Main Analysis Pipeline
# ============================================================================

class AnalysisPipeline:
    """Main pipeline for analyzing experimental data."""
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        self.config = config or AnalysisConfig()
        self.detector = PhaseTransitionDetector()
        self.fss = FiniteSizeScaling()
        self.exponent_estimator = CriticalExponentEstimator()
    
    def analyze_phase_transition(self, df: pd.DataFrame, 
                                 n_qubits: int) -> Dict[str, Any]:
        """
        Analyze phase transition for a given system size.
        
        Args:
            df: DataFrame with columns 'depth', 'success'
            n_qubits: Number of qubits
        
        Returns:
            Dictionary with analysis results
        """
        # Aggregate by depth
        grouped = df.groupby('depth')['success'].agg(['mean', 'std', 'count'])
        depths = grouped.index.values
        success_rates = grouped['mean'].values
        
        # Sigmoid fit
        sigmoid_result = self.detector.sigmoid_fit(depths, success_rates)
        
        # Bootstrap CI for critical depth
        if not np.isnan(sigmoid_result['dc']):
            dc_samples = []
            rng = np.random.RandomState(42)
            for _ in range(self.config.n_bootstrap):
                # Resample data
                boot_df = df.sample(frac=1, replace=True, random_state=rng)
                boot_grouped = boot_df.groupby('depth')['success'].mean()
                boot_depths = boot_grouped.index.values
                boot_success = boot_grouped.values
                
                boot_result = self.detector.sigmoid_fit(boot_depths, boot_success)
                if not np.isnan(boot_result['dc']):
                    dc_samples.append(boot_result['dc'])
            
            if len(dc_samples) > 100:
                sigmoid_result['dc_ci_lower'] = np.percentile(dc_samples, 2.5)
                sigmoid_result['dc_ci_upper'] = np.percentile(dc_samples, 97.5)
            else:
                sigmoid_result['dc_ci_lower'] = np.nan
                sigmoid_result['dc_ci_upper'] = np.nan
        
        return {
            'n_qubits': n_qubits,
            'depths': depths.tolist(),
            'success_rates': success_rates.tolist(),
            'sigmoid_fit': sigmoid_result,
        }
    
    def analyze_scaling(self, results_by_n: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze scaling of critical depth with system size.
        
        Args:
            results_by_n: Dictionary mapping n_qubits -> phase transition results
        
        Returns:
            Dictionary with scaling analysis
        """
        n_values = []
        dc_values = []
        dc_errors = []
        
        for n, result in results_by_n.items():
            dc = result['sigmoid_fit'].get('dc', np.nan)
            if not np.isnan(dc):
                n_values.append(n)
                dc_values.append(dc)
                dc_errors.append(result['sigmoid_fit'].get('dc_err', 0.1))
        
        n_values = np.array(n_values)
        dc_values = np.array(dc_values)
        dc_errors = np.array(dc_errors)
        
        if len(n_values) < 3:
            return {'alpha': np.nan, 'alpha_err': np.nan, 'r_squared': 0.0}
        
        # Log-log regression
        log_n = np.log(n_values)
        log_dc = np.log(dc_values)
        
        slope, intercept, r_value, p_value, std_err = sp_stats.linregress(log_n, log_dc)
        
        return {
            'alpha': slope,
            'alpha_err': std_err,
            'r_squared': r_value**2,
            'p_value': p_value,
            'dc_values': dc_values.tolist(),
            'n_values': n_values.tolist(),
        }
    
    def analyze_entanglement_correlation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze correlation between entanglement and success rate.
        
        Args:
            df: DataFrame with columns 'entanglement_entropy', 'success'
        
        Returns:
            Dictionary with correlation analysis
        """
        entropy = df['entanglement_entropy'].values
        success = df['success'].values
        
        # Pearson correlation
        r, p = sp_stats.pearsonr(entropy, success)
        
        # Bootstrap CI for correlation
        r_boot = []
        rng = np.random.RandomState(42)
        for _ in range(self.config.n_bootstrap):
            idx = rng.choice(len(entropy), size=len(entropy), replace=True)
            try:
                r_b, _ = sp_stats.pearsonr(entropy[idx], success[idx])
                r_boot.append(r_b)
            except:
                continue
        
        if len(r_boot) > 100:
            r_ci_lower = np.percentile(r_boot, 2.5)
            r_ci_upper = np.percentile(r_boot, 97.5)
        else:
            r_ci_lower = r_ci_upper = r
        
        return {
            'pearson_r': r,
            'p_value': p,
            'r_ci_lower': r_ci_lower,
            'r_ci_upper': r_ci_upper,
        }
    
    def generate_report(self, results: Dict[str, Any], output_path: Optional[Path] = None) -> str:
        """Generate a formatted analysis report."""
        report = []
        report.append("=" * 70)
        report.append("STATISTICAL ANALYSIS REPORT")
        report.append("=" * 70)
        report.append("")
        
        # Phase transition results
        if 'phase_transitions' in results:
            report.append("PHASE TRANSITION ANALYSIS")
            report.append("-" * 70)
            for n, pt in results['phase_transitions'].items():
                report.append(f"n = {n}:")
                sigmoid = pt.get('sigmoid_fit', {})
                report.append(f"  Critical depth: {sigmoid.get('dc', 'N/A'):.2f} "
                             f"± {sigmoid.get('dc_err', 'N/A'):.2f}")
                report.append(f"  Sharpness (beta): {sigmoid.get('beta', 'N/A'):.3f}")
                report.append(f"  R²: {sigmoid.get('r_squared', 'N/A'):.3f}")
                report.append(f"  Sigmoid-like: {sigmoid.get('is_sigmoid', False)}")
                report.append("")
        
        # Scaling results
        if 'scaling' in results:
            report.append("SCALING ANALYSIS")
            report.append("-" * 70)
            scaling = results['scaling']
            report.append(f"Critical exponent alpha: {scaling.get('alpha', 'N/A'):.3f} "
                         f"± {scaling.get('alpha_err', 'N/A'):.3f}")
            report.append(f"R²: {scaling.get('r_squared', 'N/A'):.3f}")
            report.append("")
        
        # Entanglement correlation
        if 'entanglement' in results:
            report.append("ENTANGLEMENT CORRELATION")
            report.append("-" * 70)
            ent = results['entanglement']
            report.append(f"Pearson r: {ent.get('pearson_r', 'N/A'):.3f}")
            report.append(f"p-value: {ent.get('p_value', 'N/A'):.3e}")
            report.append("")
        
        report.append("=" * 70)
        
        report_text = "\n".join(report)
        
        if output_path:
            output_path.write_text(report_text)
        
        return report_text
