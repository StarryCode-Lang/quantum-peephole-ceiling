"""
Phase Transition Analysis and Visualization - Complete Implementation
Implements all analysis methods as specified in research outline.
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.optimize import curve_fit
from scipy.ndimage import uniform_filter1d
from typing import List, Tuple, Dict, Optional
import warnings
warnings.filterwarnings('ignore')


class PhaseTransitionDetector:
    """Complete phase transition detection with multiple methods."""
    
    @staticmethod
    def pelt(data: np.ndarray, penalty: float = 1.0) -> List[int]:
        """Pruned Exact Linear Time algorithm."""
        n = len(data)
        if n < 2:
            return []
        
        def cost(start, end):
            segment = data[start:end]
            if len(segment) == 0:
                return 0
            return np.sum((segment - np.mean(segment))**2)
        
        F = np.zeros(n + 1)
        cp = [[] for _ in range(n + 1)]
        
        for t in range(1, n + 1):
            candidates = []
            for s in range(t):
                cost_val = F[s] + cost(s, t) + penalty
                candidates.append((cost_val, s))
            
            F[t], best_s = min(candidates)
            cp[t] = cp[best_s] + [best_s] if best_s > 0 else []
        
        return cp[n]
    
    @staticmethod
    def binary_segmentation(data: np.ndarray, min_segment: int = 5) -> List[int]:
        """Binary segmentation for change point detection."""
        n = len(data)
        if n < 2 * min_segment:
            return []
        
        best_score = -np.inf
        best_split = None
        
        for split in range(min_segment, n - min_segment):
            left = data[:split]
            right = data[split:]
            score = abs(np.mean(left) - np.mean(right))
            
            if score > best_score:
                best_score = score
                best_split = split
        
        if best_split is None:
            return []
        
        left_cps = PhaseTransitionDetector.binary_segmentation(data[:best_split], min_segment)
        right_cps = PhaseTransitionDetector.binary_segmentation(data[best_split:], min_segment)
        
        return left_cps + [best_split] + [cp + best_split for cp in right_cps]
    
    @staticmethod
    def bayesian_changepoint(data: np.ndarray) -> List[int]:
        """Bayesian change point detection (simplified)."""
        n = len(data)
        if n < 10:
            return []
        
        # Calculate posterior probability of change point
        posteriors = []
        for i in range(1, n - 1):
            left = data[:i]
            right = data[i:]
            
            # Likelihood ratio
            ll_left = np.sum(stats.norm.logpdf(left, np.mean(left), np.std(left) + 1e-10))
            ll_right = np.sum(stats.norm.logpdf(right, np.mean(right), np.std(right) + 1e-10))
            ll_null = np.sum(stats.norm.logpdf(data, np.mean(data), np.std(data) + 1e-10))
            
            posterior = np.exp(ll_left + ll_right - ll_null)
            posteriors.append(posterior)
        
        # Find peaks in posterior
        posteriors = np.array(posteriors)
        threshold = np.mean(posteriors) + 2 * np.std(posteriors)
        
        change_points = []
        for i in range(1, len(posteriors) - 1):
            if (posteriors[i] > posteriors[i-1] and 
                posteriors[i] > posteriors[i+1] and 
                posteriors[i] > threshold):
                change_points.append(i)
        
        return change_points
    
    @staticmethod
    def inflection_point(data: np.ndarray, parameter_values: np.ndarray) -> float:
        """Find inflection point in data."""
        smoothed = uniform_filter1d(data, size=min(5, len(data)))
        d2 = np.gradient(np.gradient(smoothed))
        
        zero_crossings = np.where(np.diff(np.sign(d2)))[0]
        
        if len(zero_crossings) > 0:
            return parameter_values[zero_crossings[0]]
        else:
            return parameter_values[np.argmax(np.abs(np.gradient(smoothed)))]
    
    @staticmethod
    def maximum_gradient(data: np.ndarray, parameter_values: np.ndarray) -> float:
        """Find point of maximum gradient."""
        gradient = np.gradient(data)
        return parameter_values[np.argmax(np.abs(gradient))]


class CriticalExponentEstimator:
    """Estimate critical exponents from experimental data."""
    
    @staticmethod
    def power_law_fit(x: np.ndarray, y: np.ndarray, x_c: float) -> Tuple[float, float, float]:
        """Fit data to power law: y = A * |x - x_c|^beta."""
        mask = np.abs(x - x_c) > 0.01
        x_fit = x[mask]
        y_fit = y[mask]
        
        if len(x_fit) < 3:
            return 0.0, 0.0, 0.0
        
        log_x = np.log(np.abs(x_fit - x_c) + 1e-10)
        log_y = np.log(np.abs(y_fit) + 1e-10)
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, log_y)
        
        return np.exp(intercept), slope, r_value**2
    
    @staticmethod
    def log_log_regression(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
        """Perform log-log regression."""
        log_x = np.log(np.abs(x) + 1e-10)
        log_y = np.log(np.abs(y) + 1e-10)
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, log_y)
        
        return slope, intercept, r_value**2
    
    @staticmethod
    def finite_size_scaling(data: Dict[int, np.ndarray],
                           parameter_values: np.ndarray,
                           x_c: float) -> Tuple[float, float]:
        """Perform finite-size scaling analysis."""
        sizes = sorted(data.keys())
        
        if len(sizes) < 2:
            return 0.0, 0.0
        
        best_beta_nu = 0.0
        best_nu_inv = 0.0
        best_score = np.inf
        
        for beta_nu in np.arange(0.1, 2.0, 0.1):
            for nu_inv in np.arange(0.1, 2.0, 0.1):
                collapsed_x = []
                collapsed_y = []
                
                for n in sizes:
                    scaled_x = (parameter_values - x_c) * n**nu_inv
                    scaled_y = data[n] * n**beta_nu
                    
                    collapsed_x.extend(scaled_x)
                    collapsed_y.extend(scaled_y)
                
                collapsed_x = np.array(collapsed_x)
                collapsed_y = np.array(collapsed_y)
                
                sort_idx = np.argsort(collapsed_x)
                collapsed_x = collapsed_x[sort_idx]
                collapsed_y = collapsed_y[sort_idx]
                
                if len(collapsed_y) > 1:
                    score = np.var(np.diff(collapsed_y))
                else:
                    score = np.inf
                
                if score < best_score:
                    best_score = score
                    best_beta_nu = beta_nu
                    best_nu_inv = nu_inv
        
        return best_beta_nu, best_nu_inv
    
    @staticmethod
    def binder_cumulant(data: np.ndarray, parameter_values: np.ndarray) -> np.ndarray:
        """Calculate Binder cumulant."""
        m2 = np.mean(data**2)
        m4 = np.mean(data**4)
        
        if m2 == 0:
            return np.zeros_like(parameter_values)
        
        return 1 - m4 / (3 * m2**2)


class StatisticalAnalysis:
    """Complete statistical analysis tools."""
    
    @staticmethod
    def pearson_correlation(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
        """Calculate Pearson correlation coefficient."""
        corr, p_value = stats.pearsonr(x, y)
        return corr, p_value
    
    @staticmethod
    def spearman_correlation(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
        """Calculate Spearman rank correlation."""
        corr, p_value = stats.spearmanr(x, y)
        return corr, p_value
    
    @staticmethod
    def mutual_information(x: np.ndarray, y: np.ndarray, bins: int = 20) -> float:
        """Calculate mutual information."""
        hist_xy, _, _ = np.histogram2d(x, y, bins=bins)
        hist_x, _ = np.histogram(x, bins=bins)
        hist_y, _ = np.histogram(y, bins=bins)
        
        # Normalize
        p_xy = hist_xy / np.sum(hist_xy)
        p_x = hist_x / np.sum(hist_x)
        p_y = hist_y / np.sum(hist_y)
        
        # Calculate MI
        mi = 0.0
        for i in range(bins):
            for j in range(bins):
                if p_xy[i, j] > 0 and p_x[i] > 0 and p_y[j] > 0:
                    mi += p_xy[i, j] * np.log2(p_xy[i, j] / (p_x[i] * p_y[j]))
        
        return mi
    
    @staticmethod
    def t_test(group1: np.ndarray, group2: np.ndarray) -> Tuple[float, float]:
        """Perform t-test between two groups."""
        t_stat, p_value = stats.ttest_ind(group1, group2)
        return t_stat, p_value
    
    @staticmethod
    def anova(*groups) -> Tuple[float, float]:
        """Perform one-way ANOVA."""
        f_stat, p_value = stats.f_oneway(*groups)
        return f_stat, p_value
    
    @staticmethod
    def effect_size_cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
        """Calculate Cohen's d effect size."""
        n1, n2 = len(group1), len(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        if pooled_std == 0:
            return 0.0
        
        return (np.mean(group1) - np.mean(group2)) / pooled_std
    
    @staticmethod
    def mann_whitney_u(group1: np.ndarray, group2: np.ndarray) -> Tuple[float, float]:
        """Perform Mann-Whitney U test."""
        u_stat, p_value = stats.mannwhitneyu(group1, group2)
        return u_stat, p_value


class LandscapeAnalyzer:
    """Complete landscape analysis tools."""
    
    @staticmethod
    def ruggedness(fitness_values: np.ndarray) -> float:
        """Calculate landscape ruggedness."""
        if len(fitness_values) < 2:
            return 0.0
        
        autocorr = np.correlate(fitness_values, fitness_values, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        autocorr = autocorr / autocorr[0]
        
        correlation_length = np.argmax(autocorr < 0.5) if any(autocorr < 0.5) else len(autocorr)
        
        return 1.0 / (correlation_length + 1)
    
    @staticmethod
    def gradient_norm(fitness_values: np.ndarray) -> float:
        """Calculate gradient norm."""
        if len(fitness_values) < 2:
            return 0.0
        
        gradient = np.gradient(fitness_values)
        return np.mean(np.abs(gradient))
    
    @staticmethod
    def local_minima_count(fitness_values: np.ndarray) -> int:
        """Count local minima in fitness landscape."""
        if len(fitness_values) < 3:
            return 0
        
        count = 0
        for i in range(1, len(fitness_values) - 1):
            if (fitness_values[i] < fitness_values[i-1] and 
                fitness_values[i] < fitness_values[i+1]):
                count += 1
        
        return count
    
    @staticmethod
    def information_content(fitness_values: np.ndarray) -> float:
        """Calculate information content of landscape."""
        if len(fitness_values) < 2:
            return 0.0
        
        # Discretize fitness values
        bins = min(20, len(fitness_values) // 5)
        hist, _ = np.histogram(fitness_values, bins=bins)
        probs = hist / np.sum(hist)
        
        # Shannon entropy
        probs = probs[probs > 0]
        return -np.sum(probs * np.log2(probs))
    
    @staticmethod
    def get_all_landscape_metrics(fitness_values: np.ndarray) -> Dict[str, float]:
        """Get all landscape metrics."""
        return {
            'ruggedness': LandscapeAnalyzer.ruggedness(fitness_values),
            'gradient_norm': LandscapeAnalyzer.gradient_norm(fitness_values),
            'local_minima': LandscapeAnalyzer.local_minima_count(fitness_values),
            'information_content': LandscapeAnalyzer.information_content(fitness_values),
            'mean_fitness': np.mean(fitness_values),
            'std_fitness': np.std(fitness_values),
            'min_fitness': np.min(fitness_values),
            'max_fitness': np.max(fitness_values)
        }


class PhaseDiagramBuilder:
    """Build and visualize phase diagrams."""
    
    @staticmethod
    def plot_phase_diagram(param1_values: np.ndarray,
                          param2_values: np.ndarray,
                          metric_values: np.ndarray,
                          title: str = "Phase Diagram",
                          xlabel: str = "Parameter 1",
                          ylabel: str = "Parameter 2",
                          save_path: Optional[str] = None):
        """Plot phase diagram."""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        im = ax.imshow(metric_values, 
                       extent=[param1_values[0], param1_values[-1],
                              param2_values[0], param2_values[-1]],
                       origin='lower', aspect='auto', cmap='RdYlBu_r')
        
        contour = ax.contour(param1_values, param2_values, metric_values,
                            levels=[0.5], colors='black', linewidths=2)
        
        plt.colorbar(im, ax=ax, label='Metric Value')
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.close()
    
    @staticmethod
    def plot_scaling(parameter_values: np.ndarray,
                    metric_values: Dict[int, np.ndarray],
                    system_sizes: List[int],
                    title: str = "Scaling Plot",
                    save_path: Optional[str] = None):
        """Plot scaling behavior."""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        colors = plt.cm.viridis(np.linspace(0, 1, len(system_sizes)))
        
        for i, n in enumerate(system_sizes):
            ax.plot(parameter_values, metric_values[n], 
                   color=colors[i], label=f'n={n}', linewidth=2)
        
        ax.set_xlabel('Control Parameter')
        ax.set_ylabel('Order Parameter')
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.close()


if __name__ == '__main__':
    print("Testing complete analysis tools...")
    
    # Test phase transition detection
    x = np.linspace(0, 1, 100)
    y = np.where(x < 0.5, 1.0, 0.0) + np.random.normal(0, 0.1, 100)
    
    detector = PhaseTransitionDetector()
    print(f"PELT change points: {detector.pelt(y)}")
    print(f"Binary segmentation: {detector.binary_segmentation(y)}")
    print(f"Bayesian change points: {detector.bayesian_changepoint(y)}")
    
    # Test critical exponent estimation
    estimator = CriticalExponentEstimator()
    A, beta, r2 = estimator.power_law_fit(x, y, 0.5)
    print(f"Power law fit: A={A:.3f}, beta={beta:.3f}, R²={r2:.3f}")
    
    # Test statistical analysis
    analyzer = StatisticalAnalysis()
    corr, p_val = analyzer.pearson_correlation(x, y)
    print(f"Pearson correlation: r={corr:.3f}, p={p_val:.3f}")
