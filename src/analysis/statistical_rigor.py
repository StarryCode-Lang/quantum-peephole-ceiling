"""
Statistical Rigor Module
========================
This module provides postdoctoral-level statistical functions for rigorous data analysis. 
It includes methods for multiple testing correction, model comparison, residual analysis, 
power analysis, and normality testing.

Mathematical Foundations & References:
--------------------------------------
1. Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: 
   a practical and powerful approach to multiple testing. Journal of the Royal 
   Statistical Society: Series B (Methodological), 57(1), 289-300.
2. Burnham, K. P., & Anderson, D. R. (2004). Multimodel inference: understanding 
   AIC and BIC in model selection. Sociological Methods & Research, 33(2), 261-304.
3. Shapiro, S. S., & Wilk, M. B. (1965). An analysis of variance test for normality 
   (complete samples). Biometrika, 52(3/4), 591-611.
4. Cohen, J. (1988). Statistical power analysis for the behavioral sciences (2nd ed.). 
   Lawrence Erlbaum Associates.
5. Breusch, T. S., & Pagan, A. R. (1979). A simple test for heteroscedasticity and 
   random coefficient variation. Econometrica, 47(5), 1287-1294.
"""

import numpy as np
import pandas as pd
import scipy.stats as stats
from typing import Tuple, Dict, Callable


# ==============================================================================
# 1. Multiple Testing Corrections
# ==============================================================================

def benjamini_hochberg(p_values: np.ndarray, alpha: float = 0.05) -> Tuple[np.ndarray, float]:
    """
    Benjamini-Hochberg FDR correction.
    
    Controls the False Discovery Rate (FDR) for multiple comparisons.
    Mathematical formula for adjusted p-value:
        p_adj(i) = min_{j >= i} { m * p_(j) / j }
    where p_(1) <= p_(2) <= ... <= p_(m) are the ordered p-values.
    
    Args:
        p_values (np.ndarray): Array of raw p-values.
        alpha (float): Significance level. Default is 0.05.
        
    Returns:
        Tuple[np.ndarray, float]: A tuple containing:
            - adjusted_p_values (np.ndarray): The FDR-adjusted p-values.
            - critical_threshold (float): The largest p-value threshold that is significant.
    """
    p_values = np.asarray(p_values)
    m = len(p_values)
    if m == 0:
        return np.array([]), 0.0
        
    sorted_indices = np.argsort(p_values)
    ranked_p_values = p_values[sorted_indices]
    
    # Calculate adjusted p-values
    adjusted_p = np.zeros(m)
    adjusted_p[-1] = ranked_p_values[-1]
    for i in range(m - 2, -1, -1):
        adjusted_p[i] = min(adjusted_p[i + 1], ranked_p_values[i] * m / (i + 1))
        
    adjusted_p = np.clip(adjusted_p, 0.0, 1.0)
    
    # Unsort to match original order
    unsorted_indices = np.argsort(sorted_indices)
    final_adjusted_p = adjusted_p[unsorted_indices]
    
    # Calculate critical threshold
    ranks = np.arange(1, m + 1)
    critical_values = ranks * alpha / m
    significant = ranked_p_values <= critical_values
    
    if np.any(significant):
        critical_threshold = critical_values[np.max(np.where(significant))]
    else:
        critical_threshold = 0.0
        
    return final_adjusted_p, float(critical_threshold)


def bonferroni_correction(p_values: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """
    Bonferroni correction for multiple comparisons.
    
    Adjusts p-values by multiplying by the number of tests to control the 
    Family-Wise Error Rate (FWER).
    Mathematical formula:
        p_adj = min(m * p, 1)
        
    Args:
        p_values (np.ndarray): Array of raw p-values.
        alpha (float): Significance level (documented for API consistency, 
                       though adjustment is independent of alpha). Default is 0.05.
        
    Returns:
        np.ndarray: Bonferroni-adjusted p-values.
    """
    p_values = np.asarray(p_values)
    return np.clip(p_values * len(p_values), 0.0, 1.0)


# ==============================================================================
# 2. Model Comparison (AIC/BIC)
# ==============================================================================

def compare_models(y_true: np.ndarray, models: Dict[str, Callable], 
                   params: Dict[str, np.ndarray]) -> pd.DataFrame:
    """
    Compare models using AIC, BIC, and adjusted R².
    
    Mathematical formulas:
        RSS = sum((y_true - y_pred)^2)
        AIC = n * ln(RSS/n) + 2k
        BIC = n * ln(RSS/n) + k * ln(n)
        R² = 1 - RSS / TSS
        Adjusted R² = 1 - (1 - R²) * (n - 1) / (n - k - 1)
        delta_AIC = AIC - min(AIC)
        AIC_weight = exp(-0.5 * delta_AIC) / sum(exp(-0.5 * delta_AIC))
        
    Args:
        y_true (np.ndarray): True observed values.
        models (Dict[str, Callable]): Dictionary mapping model names to callable functions.
                                      Each callable should take model parameters as arguments
                                      and return an array of predicted values.
        params (Dict[str, np.ndarray]): Dictionary mapping model names to their estimated 
                                        parameter arrays.
        
    Returns:
        pd.DataFrame: DataFrame with columns: model, AIC, BIC, delta_AIC, AIC_weight, adj_R2
    """
    y_true = np.asarray(y_true)
    n = len(y_true)
    ss_tot = np.sum((y_true - np.mean(y_true))**2)
    
    results = []
    for name, model_fn in models.items():
        p = np.asarray(params[name])
        k = len(p)
        
        # Evaluate model predictions
        y_pred = model_fn(*p)
        residuals = y_true - y_pred
        rss = np.sum(residuals**2)
        
        # Information Criteria
        aic = n * np.log(rss / n) + 2 * k
        bic = n * np.log(rss / n) + k * np.log(n)
        
        # Goodness of Fit
        r2 = 1 - (rss / ss_tot) if ss_tot > 0 else 0.0
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k - 1) if n > k + 1 else np.nan
        
        results.append({
            'model': name,
            'AIC': aic,
            'BIC': bic,
            'adj_R2': adj_r2
        })
        
    df = pd.DataFrame(results)
    df['delta_AIC'] = df['AIC'] - df['AIC'].min()
    
    # Akaike weights
    rel_lik = np.exp(-0.5 * df['delta_AIC'])
    df['AIC_weight'] = rel_lik / rel_lik.sum()
    
    return df[['model', 'AIC', 'BIC', 'delta_AIC', 'AIC_weight', 'adj_R2']]


def exponential_decay(d: np.ndarray, P0: float, d0: float) -> np.ndarray:
    """
    Exponential decay model.
    
    Mathematical formula:
        P(d) = P0 * exp(-d / d0)
        
    Args:
        d (np.ndarray): Independent variable (e.g., distance or time).
        P0 (float): Initial value at d=0.
        d0 (float): Decay constant (characteristic scale).
        
    Returns:
        np.ndarray: Predicted values.
    """
    d = np.asarray(d)
    return P0 * np.exp(-d / d0)


def sigmoid_decay(d: np.ndarray, dc: float, beta: float, P0: float) -> np.ndarray:
    """
    Sigmoidal decay model.
    
    Mathematical formula:
        S(d) = P0 / (1 + exp(beta * (d - dc)))
        
    Args:
        d (np.ndarray): Independent variable.
        dc (float): Critical value (inflection point).
        beta (float): Steepness of the curve.
        P0 (float): Maximum value (asymptote as d -> -inf).
        
    Returns:
        np.ndarray: Predicted values.
    """
    d = np.asarray(d)
    return P0 / (1.0 + np.exp(beta * (d - dc)))


def power_law(n: np.ndarray, a: float, b: float) -> np.ndarray:
    """
    Power law model.
    
    Mathematical formula:
        y = a * n^b
        
    Args:
        n (np.ndarray): Independent variable.
        a (float): Scaling coefficient.
        b (float): Exponent.
        
    Returns:
        np.ndarray: Predicted values.
    """
    n = np.asarray(n)
    return a * np.power(n, b)


# ==============================================================================
# 3. Residual Analysis
# ==============================================================================

def residual_analysis(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
    """
    Comprehensive residual analysis.
    
    Computes diagnostics to test assumptions of linear regression:
    - Normality of residuals (Shapiro-Wilk test)
    - Autocorrelation of residuals (Durbin-Watson statistic)
    - Homoscedasticity (Breusch-Pagan test against predicted values)
    
    Mathematical formulas:
        Durbin-Watson: DW = sum((e_t - e_{t-1})^2) / sum(e_t^2)
        Breusch-Pagan LM statistic: LM = n * R²_aux, 
        where R²_aux is from OLS regression of squared residuals (e²) on y_pred.
        
    Args:
        y_true (np.ndarray): True observed values.
        y_pred (np.ndarray): Model predicted values.
        
    Returns:
        Dict: Dictionary with keys:
            - 'residuals' (np.ndarray): The raw residuals.
            - 'shapiro_p' (float): P-value from Shapiro-Wilk test for normality.
            - 'durbin_watson' (float): Durbin-Watson statistic (close to 2 implies no autocorrelation).
            - 'breusch_pagan_p' (float): P-value from Breusch-Pagan test for homoscedasticity.
            - 'qq_data' (Tuple): Theoretical quantiles and ordered sample quantiles for QQ plot.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    residuals = y_true - y_pred
    
    # 1. Normality (Shapiro-Wilk)
    _, shapiro_p = stats.shapiro(residuals)
    
    # 2. Autocorrelation (Durbin-Watson)
    durbin_watson = np.sum(np.diff(residuals)**2) / np.sum(residuals**2)
    
    # 3. Homoscedasticity (Breusch-Pagan)
    e2 = residuals**2
    X = np.column_stack((np.ones_like(y_pred), y_pred))
    beta, _, _, _ = np.linalg.lstsq(X, e2, rcond=None)
    e2_pred = X @ beta
    ss_tot = np.sum((e2 - np.mean(e2))**2)
    ss_res = np.sum((e2 - e2_pred)**2)
    r2_aux = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    lm_stat = len(residuals) * r2_aux
    breusch_pagan_p = float(stats.chi2.sf(lm_stat, 1))
    
    # 4. QQ plot data
    qq_data = stats.probplot(residuals, dist="norm")
    
    return {
        'residuals': residuals,
        'shapiro_p': float(shapiro_p),
        'durbin_watson': float(durbin_watson),
        'breusch_pagan_p': breusch_pagan_p,
        'qq_data': (qq_data[0][0], qq_data[0][1])  # (theoretical quantiles, ordered values)
    }


# ==============================================================================
# 4. Power Analysis
# ==============================================================================

def power_analysis_sample_size(effect_size: float, alpha: float = 0.05, 
                                power: float = 0.80, test: str = 'ttest') -> int:
    """
    Calculate required sample size for given effect size and power.
    
    Uses the normal approximation for a two-sample independent t-test (Cohen's d).
    Mathematical formula:
        n = 2 * (Z_{1 - \alpha/2} + Z_{power})^2 / d^2
        
    Args:
        effect_size (float): Cohen's d effect size.
        alpha (float): Significance level. Default is 0.05.
        power (float): Desired statistical power. Default is 0.80.
        test (str): Type of statistical test. Currently supports 'ttest'.
        
    Returns:
        int: Required sample size per group.
    """
    if test != 'ttest':
        raise ValueError("Only 'ttest' is currently supported.")
        
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    
    n_per_group = 2 * ((z_alpha + z_power) / effect_size) ** 2
    return int(np.ceil(n_per_group))


def achieved_power(effect_size: float, n: int, alpha: float = 0.05) -> float:
    """
    Calculate achieved statistical power for given sample size.
    
    Uses the non-central t-distribution for an exact calculation in a two-sample t-test.
    Mathematical formula:
        Power = 1 - P(T' < t_{crit}) + P(T' < -t_{crit})
        where T' ~ non-central t-distribution with df = 2n - 2 
        and non-centrality parameter ncp = d * sqrt(n / 2).
        
    Args:
        effect_size (float): Cohen's d effect size.
        n (int): Sample size per group.
        alpha (float): Significance level. Default is 0.05.
        
    Returns:
        float: Achieved statistical power.
    """
    df = 2 * n - 2
    ncp = effect_size * np.sqrt(n / 2)
    t_crit = stats.t.ppf(1 - alpha / 2, df)
    
    # Calculate power using the cumulative distribution function of the non-central t-distribution
    power = 1 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp)
    return float(power)


# ==============================================================================
# 5. Normality Tests
# ==============================================================================

def normality_tests(data: np.ndarray) -> Dict:
    """
    Run Shapiro-Wilk, Anderson-Darling, and D'Agostino K² tests for normality.
    
    Args:
        data (np.ndarray): 1D array of sample data.
        
    Returns:
        Dict: Dictionary containing test names as keys, each mapping to a dictionary 
              with 'statistic' and 'p_value' (or 'critical_values' for Anderson-Darling).
    """
    data = np.asarray(data)
    
    # 1. Shapiro-Wilk Test
    sw_stat, sw_p = stats.shapiro(data)
    
    # 2. Anderson-Darling Test
    ad_result = stats.anderson(data, dist='norm')
    
    # 3. D'Agostino K² Test (Requires at least 20 samples)
    try:
        da_stat, da_p = stats.normaltest(data)
        dagostino_result = {'statistic': float(da_stat), 'p_value': float(da_p)}
    except ValueError:
        dagostino_result = {
            'statistic': np.nan, 
            'p_value': np.nan, 
            'error': 'Sample size too small (< 20) for D\'Agostino K² test'
        }
        
    return {
        'shapiro_wilk': {
            'statistic': float(sw_stat), 
            'p_value': float(sw_p)
        },
        'anderson_darling': {
            'statistic': float(ad_result.statistic), 
            'critical_values': ad_result.critical_values.tolist(),
            'significance_levels': ad_result.significance_level.tolist()
        },
        'dagostino_k2': dagostino_result
    }
