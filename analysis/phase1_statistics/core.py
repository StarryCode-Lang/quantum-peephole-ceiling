"""
Statistical Analysis Toolkit - Postdoctoral Grade
===================================================
Implements multiple comparison correction, effect size reporting,
power analysis, bootstrap convergence diagnostics, and fidelity distribution analysis.

Version: 3.0.0 (PRA-compliant)

DEPRECATED (bug #8 fix): This module contains duplicated implementations.
Prefer the dedicated modules (effect_size.py, multiple_comparison.py,
power_analysis.py, bootstrap.py). This module is retained only for backward
compatibility with generate_figures.py and phase2_threshold_sensitivity/run.py.

As of this fix, ``cliffs_delta`` and ``hedges_g`` defined here are thin
re-exports of ``effect_size.py`` and share its ``Dict[str, Any]`` return
contract (keys: 'delta'/'g', 'ci_lower', 'ci_upper', 'magnitude', 'n1',
'n2', ...). The previous tuple ``(value, ci_low, ci_high)`` contract is no
longer returned; callers have been updated accordingly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from typing import List, Tuple, Dict, Callable, Optional, Any
import json
from dataclasses import dataclass

# Re-export the canonical effect-size implementations so that callers importing
# from core.py receive the unified Dict[str, Any] contract (bug #8 fix).
from .effect_size import cliffs_delta as _cliffs_delta_es, cohens_d as _cohens_d_es


# ============================================================================
# Multiple Comparison Correction
# ============================================================================

def benjamini_hochberg(p_values: np.ndarray, alpha: float = 0.05) -> Tuple[np.ndarray, np.ndarray]:
    """
    Benjamini-Hochberg False Discovery Rate (FDR) control.
    
    Args:
        p_values: Array of p-values
        alpha: Desired FDR level (default 0.05)
    
    Returns:
        (rejected, adjusted_p): Boolean array of rejected hypotheses,
                                Array of adjusted p-values
    
    Reference:
        Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery
        rate: a practical and powerful approach to multiple testing.
        Journal of the Royal Statistical Society: Series B, 57(1), 289-300.
    """
    p_values = np.asarray(p_values)
    n = len(p_values)
    
    # Sort p-values
    sorted_indices = np.argsort(p_values)
    sorted_p = p_values[sorted_indices]
    
    # Find largest k such that p_k <= (k/m) * alpha
    thresholds = np.arange(1, n + 1) / n * alpha
    
    # Find rejection threshold
    rejected_sorted = sorted_p <= thresholds
    
    # Adjusted p-values (Benjamini-Hochberg-Yekutieli)
    adjusted_p = np.minimum.accumulate(sorted_p[::-1] * n / np.arange(n, 0, -1))[::-1]
    adjusted_p = np.minimum(adjusted_p, 1.0)
    
    # Unsort
    adjusted_p_unsorted = np.empty_like(adjusted_p)
    adjusted_p_unsorted[sorted_indices] = adjusted_p
    
    rejected_unsorted = np.empty_like(rejected_sorted)
    rejected_unsorted[sorted_indices] = rejected_sorted
    
    return rejected_unsorted, adjusted_p_unsorted


def holm_bonferroni(p_values: np.ndarray, alpha: float = 0.05) -> Tuple[np.ndarray, np.ndarray]:
    """
    Holm-Bonferroni step-down procedure for family-wise error rate control.
    
    More conservative than BH-FDR but controls FWER strongly.
    """
    p_values = np.asarray(p_values)
    n = len(p_values)
    
    sorted_indices = np.argsort(p_values)
    sorted_p = p_values[sorted_indices]
    
    # Holm procedure
    thresholds = alpha / np.arange(n, 0, -1)
    rejected_sorted = sorted_p <= thresholds
    
    # Adjusted p-values
    adjusted_p = np.minimum.accumulate(sorted_p * np.arange(n, 0, -1))[::-1]
    adjusted_p = np.minimum(adjusted_p, 1.0)
    
    # Unsort
    adjusted_p_unsorted = np.empty_like(adjusted_p)
    adjusted_p_unsorted[sorted_indices] = adjusted_p
    
    rejected_unsorted = np.empty_like(rejected_sorted)
    rejected_unsorted[sorted_indices] = rejected_sorted
    
    return rejected_unsorted, adjusted_p_unsorted


@dataclass
class FDRControlResult:
    """Result of FDR control analysis."""
    experiment_name: str
    n_hypotheses: int
    n_rejected_bh: int
    n_rejected_holm: int
    alpha: float
    p_values: np.ndarray
    adjusted_p_bh: np.ndarray
    adjusted_p_holm: np.ndarray
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_name": self.experiment_name,
            "n_hypotheses": self.n_hypotheses,
            "n_rejected_bh": self.n_rejected_bh,
            "n_rejected_holm": self.n_rejected_holm,
            "alpha": self.alpha,
            "p_values": self.p_values.tolist(),
            "adjusted_p_bh": self.adjusted_p_bh.tolist(),
            "adjusted_p_holm": self.adjusted_p_holm.tolist(),
        }


def fdr_control_table(experiment_results: List[Tuple[str, np.ndarray]], alpha: float = 0.05) -> pd.DataFrame:
    """
    Generate FDR-controlled summary table for multiple experiments.
    
    Args:
        experiment_results: List of (experiment_name, p_values_array) tuples
        alpha: FDR level
    
    Returns:
        DataFrame with columns: experiment, n_hypotheses, n_rejected_bh, n_rejected_holm
    """
    rows = []
    for name, p_values in experiment_results:
        rejected_bh, _ = benjamini_hochberg(p_values, alpha)
        rejected_holm, _ = holm_bonferroni(p_values, alpha)
        
        rows.append({
            "experiment": name,
            "n_hypotheses": len(p_values),
            "n_rejected_bh": int(rejected_bh.sum()),
            "n_rejected_holm": int(rejected_holm.sum()),
            "alpha": alpha,
        })
    
    return pd.DataFrame(rows)


# ============================================================================
# Effect Size Analysis
# ============================================================================

def cliffs_delta(x, y):
    """Cliff's delta effect size (re-exported from effect_size.py, bug #8 fix).

    This function now delegates to :func:`effect_size.cliffs_delta` and returns
    the unified ``Dict[str, Any]`` contract (keys: ``'delta'``, ``'ci_lower'``,
    ``'ci_upper'``, ``'magnitude'``, ``'n1'``, ``'n2'``, ``'se'``). The legacy
    tuple ``(delta, ci_low, ci_high)`` return is no longer produced; callers
    must read dict keys instead.

    Unlike the previous core implementation, empty samples now raise
    ``ValueError`` (matching ``effect_size.py``) instead of returning zeros.

    Reference:
        Cliff, N. (1993). Dominance statistics: Ordinal analyses to answer
        ordinal questions. Psychological Bulletin, 114(3), 494-509.
    """
    return _cliffs_delta_es(x, y)


def cohens_d(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
    """
    Calculate Cohen's d effect size with confidence interval.
    
    Uses pooled standard deviation (for independent samples).
    """
    x = np.asarray(x)
    y = np.asarray(y)
    
    nx, ny = len(x), len(y)
    
    if nx < 2 or ny < 2:
        return 0.0, 0.0, 0.0
    
    mx, my = np.mean(x), np.mean(y)
    sx, sy = np.std(x, ddof=1), np.std(y, ddof=1)
    
    # Pooled standard deviation
    pooled_std = np.sqrt(((nx - 1) * sx**2 + (ny - 1) * sy**2) / (nx + ny - 2))
    
    if pooled_std == 0:
        return 0.0, 0.0, 0.0
    
    d = (mx - my) / pooled_std
    
    # Standard error (approximate)
    se = np.sqrt(1/nx + 1/ny)
    ci_low = d - 1.96 * se
    ci_high = d + 1.96 * se
    
    return d, ci_low, ci_high


def hedges_g(x, y):
    """Hedges' g effect size (re-exported from effect_size.py, bug #8 fix).

    This function now delegates to :func:`effect_size.cohens_d` (which returns
    Hedges' g as the ``'g'`` key) and returns the unified ``Dict[str, Any]``
    contract (keys: ``'d'``, ``'g'``, ``'ci_lower'``, ``'ci_upper'``,
    ``'magnitude'``, ``'n1'``, ``'n2'``, ``'pooled_sd'``, ``'se'``). The legacy
    tuple ``(g, ci_low, ci_high)`` return is no longer produced; callers must
    read dict keys instead.

    Unlike the previous core implementation, empty samples or zero pooled
    variance now raise ``ValueError`` (matching ``effect_size.py``) instead of
    returning zeros.

    Reference:
        Hedges, L. V. (1981). Distribution theory for Glass's estimator of
        effect size and related estimators. Journal of Educational Statistics,
        6(2), 107-128.
    """
    return _cohens_d_es(x, y)


def interpret_effect_size(delta: float) -> str:
    """Interpret Cliff's delta magnitude."""
    abs_delta = abs(delta)
    if abs_delta < 0.147:
        return "negligible"
    elif abs_delta < 0.33:
        return "small"
    elif abs_delta < 0.474:
        return "medium"
    else:
        return "large"


@dataclass
class EffectSizeResult:
    """Result of effect size analysis."""
    comparison: str
    group1: str
    group2: str
    n1: int
    n2: int
    cliffs_delta: float
    cliffs_ci_low: float
    cliffs_ci_high: float
    cohens_d: float
    cohens_ci_low: float
    cohens_ci_high: float
    hedges_g: float
    hedges_ci_low: float
    hedges_ci_high: float
    interpretation: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparison": self.comparison,
            "group1": self.group1,
            "group2": self.group2,
            "n1": self.n1,
            "n2": self.n2,
            "cliffs_delta": self.cliffs_delta,
            "cliffs_ci_low": self.cliffs_ci_low,
            "cliffs_ci_high": self.cliffs_ci_high,
            "cohens_d": self.cohens_d,
            "cohens_ci_low": self.cohens_ci_low,
            "cohens_ci_high": self.cohens_ci_high,
            "hedges_g": self.hedges_g,
            "hedges_ci_low": self.hedges_ci_low,
            "hedges_ci_high": self.hedges_ci_high,
            "interpretation": self.interpretation,
        }


def effect_size_table(comparisons: List[Tuple[str, str, np.ndarray, np.ndarray]]) -> pd.DataFrame:
    """
    Generate effect size summary table.
    
    Args:
        comparisons: List of (name, group1_name, group1_data, group2_data) tuples
    
    Returns:
        DataFrame with effect size results including Cliff's delta, Cohen's d, and Hedges' g
    """
    rows = []
    for name, g1_name, g1_data, g2_name, g2_data in comparisons:
        # cliffs_delta / hedges_g now return Dict (bug #8 fix); cohens_d here
        # still returns a tuple (core implementation unchanged).
        cd_res = cliffs_delta(g1_data, g2_data)
        d, d_low, d_high = cohens_d(g1_data, g2_data)
        g_res = hedges_g(g1_data, g2_data)
        cd = cd_res["delta"]
        cd_low = cd_res["ci_lower"]
        cd_high = cd_res["ci_upper"]
        g = g_res["g"]
        g_low = g_res["ci_lower"]
        g_high = g_res["ci_upper"]
        
        rows.append({
            "comparison": name,
            "group1": g1_name,
            "group2": g2_name,
            "n1": len(g1_data),
            "n2": len(g2_data),
            "cliffs_delta": cd,
            "cliffs_ci_low": cd_low,
            "cliffs_ci_high": cd_high,
            "cohens_d": d,
            "cohens_ci_low": d_low,
            "cohens_ci_high": d_high,
            "hedges_g": g,
            "hedges_ci_low": g_low,
            "hedges_ci_high": g_high,
            "interpretation": interpret_effect_size(cd),
        })
    
    return pd.DataFrame(rows)


# ============================================================================
# Power Analysis
# ============================================================================

def calculate_power(effect_size: float, n: int, alpha: float = 0.05, test_type: str = "two_sample") -> float:
    """
    Post-hoc power analysis for two-sample t-test.
    
    Args:
        effect_size: Cohen's d effect size
        n: Sample size per group
        alpha: Significance level
        test_type: "two_sample" or "one_sample"
    
    Returns:
        Statistical power (1 - beta)
    """
    from scipy.stats import norm
    
    if test_type == "two_sample":
        se = np.sqrt(2 / n)
    else:
        se = np.sqrt(1 / n)
    
    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = effect_size / se - z_alpha
    
    power = norm.cdf(z_beta)
    return float(power)


def required_sample_size(effect_size: float, power: float = 0.80, alpha: float = 0.05, test_type: str = "two_sample") -> int:
    """
    Calculate required sample size for desired power.
    
    Args:
        effect_size: Expected Cohen's d effect size
        power: Desired statistical power
        alpha: Significance level
        test_type: "two_sample" or "one_sample"
    
    Returns:
        Required sample size per group
    """
    from scipy.stats import norm
    
    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)
    
    if test_type == "two_sample":
        n = 2 * ((z_alpha + z_beta) / effect_size) ** 2
    else:
        n = ((z_alpha + z_beta) / effect_size) ** 2
    
    return int(np.ceil(n))


def power_curve(effect_sizes: np.ndarray, n_range: np.ndarray, alpha: float = 0.05) -> pd.DataFrame:
    """
    Generate power curves for different effect sizes and sample sizes.
    
    Returns:
        DataFrame with columns: effect_size, n, power
    """
    rows = []
    for es in effect_sizes:
        for n in n_range:
            power = calculate_power(es, n, alpha)
            rows.append({
                "effect_size": es,
                "n": n,
                "power": power,
            })
    
    return pd.DataFrame(rows)


# ============================================================================
# Bootstrap Analysis
# ============================================================================

def bootstrap_ci(data: np.ndarray, statistic: Callable = np.mean, n_bootstrap: int = 10000,
                 ci: float = 95, random_state: Optional[int] = None) -> Tuple[float, float, float]:
    """
    Calculate bootstrap confidence interval with convergence check.
    
    Args:
        data: Sample data
        statistic: Function to compute statistic (default: np.mean)
        n_bootstrap: Number of bootstrap resamples
        ci: Confidence level (default: 95)
        random_state: Random seed for reproducibility
    
    Returns:
        (point_estimate, ci_low, ci_high)
    """
    data = np.asarray(data)
    n = len(data)
    
    if n == 0:
        return 0.0, 0.0, 0.0
    
    rng = np.random.RandomState(random_state)
    
    # Point estimate
    point_estimate = statistic(data)
    
    # Bootstrap resamples
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        resample = rng.choice(data, size=n, replace=True)
        bootstrap_stats.append(statistic(resample))
    
    bootstrap_stats = np.array(bootstrap_stats)
    
    # Percentile CI
    alpha = (100 - ci) / 2
    ci_low = np.percentile(bootstrap_stats, alpha)
    ci_high = np.percentile(bootstrap_stats, 100 - alpha)
    
    return point_estimate, ci_low, ci_high


def bootstrap_convergence(data: np.ndarray, statistic: Callable = np.mean,
                          max_bootstrap: int = 50000, tolerance: float = 0.01,
                          random_state: Optional[int] = None) -> Dict[str, Any]:
    """
    Check if bootstrap CI has converged by increasing resamples.
    
    Args:
        data: Sample data
        statistic: Function to compute statistic
        max_bootstrap: Maximum number of resamples to test
        tolerance: Relative tolerance for convergence
        random_state: Random seed
    
    Returns:
        Dictionary with convergence results
    """
    data = np.asarray(data)
    n = len(data)
    
    if n == 0:
        return {"converged": False, "message": "Empty data"}
    
    rng = np.random.RandomState(random_state)
    
    # Test different bootstrap sizes
    test_sizes = [1000, 2000, 5000, 10000, 20000, 50000]
    test_sizes = [s for s in test_sizes if s <= max_bootstrap]
    
    cis = []
    for size in test_sizes:
        _, low, high = bootstrap_ci(data, statistic, n_bootstrap=size, random_state=random_state)
        cis.append((low, high))
    
    # Check convergence
    converged = True
    for i in range(1, len(cis)):
        prev_width = cis[i-1][1] - cis[i-1][0]
        curr_width = cis[i][1] - cis[i][0]
        if prev_width > 0:
            rel_change = abs(curr_width - prev_width) / prev_width
            if rel_change > tolerance:
                converged = False
                break
    
    return {
        "converged": converged,
        "test_sizes": test_sizes,
        "ci_widths": [high - low for low, high in cis],
        "recommended_n": test_sizes[-1] if converged else max_bootstrap,
    }


# ============================================================================
# Fidelity Distribution Analysis
# ============================================================================

def fidelity_summary(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate full fidelity distribution summary.
    
    Reports: min, 25%, median, 75%, max, mean, std, n_outliers
    
    Args:
        results_df: DataFrame with 'fidelity' column
    
    Returns:
        DataFrame with fidelity distribution statistics
    """
    if "fidelity" not in results_df.columns:
        raise ValueError("DataFrame must have 'fidelity' column")
    
    fidelity = results_df["fidelity"].dropna()
    
    summary = {
        "n": len(fidelity),
        "min": fidelity.min(),
        "q25": fidelity.quantile(0.25),
        "median": fidelity.median(),
        "q75": fidelity.quantile(0.75),
        "max": fidelity.max(),
        "mean": fidelity.mean(),
        "std": fidelity.std(),
        "n_below_0_99": (fidelity < 0.99).sum(),
        "n_below_0_95": (fidelity < 0.95).sum(),
        "n_below_0_90": (fidelity < 0.90).sum(),
    }
    
    return pd.DataFrame([summary])


def fidelity_by_circuit_family(results_df: pd.DataFrame, family_col: str = "circuit_family") -> pd.DataFrame:
    """
    Fidelity breakdown by circuit family.
    
    Args:
        results_df: DataFrame with 'fidelity' and family columns
        family_col: Column name for circuit family
    
    Returns:
        DataFrame with fidelity stats per family
    """
    if family_col not in results_df.columns:
        raise ValueError(f"DataFrame must have '{family_col}' column")
    
    rows = []
    for family, group in results_df.groupby(family_col):
        fidelity = group["fidelity"].dropna()
        rows.append({
            "circuit_family": family,
            "n": len(fidelity),
            "min": fidelity.min(),
            "q25": fidelity.quantile(0.25),
            "median": fidelity.median(),
            "q75": fidelity.quantile(0.75),
            "max": fidelity.max(),
            "mean": fidelity.mean(),
            "std": fidelity.std(),
            "n_below_0_99": (fidelity < 0.99).sum(),
        })
    
    return pd.DataFrame(rows)


def fidelity_outliers(results_df: pd.DataFrame, threshold: float = 0.99) -> pd.DataFrame:
    """
    Identify fidelity outliers below threshold.
    
    Args:
        results_df: DataFrame with experiment results
        threshold: Fidelity threshold (default 0.99)
    
    Returns:
        DataFrame with outlier records
    """
    outliers = results_df[results_df["fidelity"] < threshold].copy()
    return outliers


# ============================================================================
# Threshold Sensitivity Analysis
# ============================================================================

def threshold_sensitivity(results_df: pd.DataFrame, thresholds: List[float] = None) -> pd.DataFrame:
    """
    Re-compute success rates at multiple thresholds.
    
    Args:
        results_df: DataFrame with 'reduction' column
        thresholds: List of success thresholds to test (default: [0.01, 0.05, 0.10, 0.20])
    
    Returns:
        DataFrame with columns: threshold, success_rate, n_success, n_total
    """
    if thresholds is None:
        thresholds = [0.01, 0.05, 0.10, 0.20]
    
    if "reduction" not in results_df.columns:
        raise ValueError("DataFrame must have 'reduction' column")
    
    rows = []
    for threshold in thresholds:
        success = results_df["reduction"] >= threshold
        rows.append({
            "threshold": threshold,
            "threshold_pct": f"{threshold*100:.0f}%",
            "success_rate": success.mean(),
            "n_success": success.sum(),
            "n_total": len(success),
        })
    
    return pd.DataFrame(rows)


# ============================================================================
# Master Analysis Function
# ============================================================================

def run_full_statistical_analysis(results_df: pd.DataFrame, experiment_name: str = "experiment") -> Dict[str, Any]:
    """
    Run complete statistical analysis on experiment results.
    
    Returns dictionary with all statistical results including effect sizes
    (Cliff's delta and Hedges' g) when comparison groups are available.
    """
    analysis = {
        "experiment_name": experiment_name,
        "n_records": len(results_df),
    }
    
    # Fidelity distribution
    if "fidelity" in results_df.columns:
        analysis["fidelity_summary"] = fidelity_summary(results_df).to_dict(orient="records")[0]
    
    # Threshold sensitivity
    if "reduction" in results_df.columns:
        analysis["threshold_sensitivity"] = threshold_sensitivity(results_df).to_dict(orient="records")
    
    # Bootstrap CI for mean reduction
    if "reduction" in results_df.columns:
        reduction = results_df["reduction"].dropna().values
        point, ci_low, ci_high = bootstrap_ci(reduction, n_bootstrap=10000, random_state=42)
        analysis["reduction_bootstrap_ci"] = {
            "point_estimate": point,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "n": len(reduction),
        }
    
    # Effect sizes (Cliff's delta and Hedges' g) when group labels available
    if "optimizer" in results_df.columns and "reduction" in results_df.columns:
        optimizer_groups = results_df.groupby("optimizer")["reduction"].apply(lambda x: x.dropna().values)
        if len(optimizer_groups) >= 2:
            effect_sizes = []
            names = list(optimizer_groups.index)
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    g1, g2 = optimizer_groups[names[i]], optimizer_groups[names[j]]
                    cd_res = cliffs_delta(g1, g2)
                    g_res = hedges_g(g1, g2)
                    cd = cd_res["delta"]
                    g_val = g_res["g"]
                    effect_sizes.append({
                        "comparison": f"{names[i]} vs {names[j]}",
                        "cliffs_delta": cd,
                        "cliffs_ci_low": cd_res["ci_lower"],
                        "cliffs_ci_high": cd_res["ci_upper"],
                        "hedges_g": g_val,
                        "hedges_ci_low": g_res["ci_lower"],
                        "hedges_ci_high": g_res["ci_upper"],
                        "interpretation": interpret_effect_size(cd),
                    })
            analysis["effect_sizes"] = effect_sizes
    
    return analysis
