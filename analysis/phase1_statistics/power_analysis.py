"""Statistical power analysis for quantum circuit optimization experiments.

Provides post-hoc power calculations, sample-size planning, and power curve
generation for publication-quality reporting in Quantum.
"""

from __future__ import annotations

import numpy as np
from scipy import stats
from typing import Sequence, Dict, Any, List, Optional, Tuple


def calculate_power(
    effect_size: float,
    n: int,
    alpha: float = 0.05,
    test_type: str = "two-sided",
) -> Dict[str, Any]:
    """Post-hoc statistical power for a two-sample t-test.

    Uses the non-central t-distribution approximation.

    Parameters
    ----------
    effect_size : float
        Standardised effect size (Cohen's d or Hedges' g).
    n : int
        Sample size per group (assumes equal group sizes).
    alpha : float, default 0.05
        Significance level.
    test_type : {'two-sided', 'one-sided'}, default 'two-sided'
        Directionality of the test.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'power': statistical power (1 - beta)
        - 'beta': Type II error rate
        - 'effect_size': input effect size
        - 'n': sample size per group
        - 'alpha': significance level
        - 'test_type': test directionality

    Raises
    ------
    ValueError
        If n <= 1, alpha invalid, or test_type unknown.
    """
    if n <= 1:
        raise ValueError("Sample size n must be > 1.")
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1).")
    if test_type not in ("two-sided", "one-sided"):
        raise ValueError("test_type must be 'two-sided' or 'one-sided'.")

    # Non-centrality parameter
    ncp = effect_size * np.sqrt(n / 2.0)

    df = 2 * n - 2
    if test_type == "two-sided":
        crit = stats.t.ppf(1 - alpha / 2, df)
        power = 1 - stats.nct.cdf(crit, df, ncp) + stats.nct.cdf(-crit, df, ncp)
    else:
        crit = stats.t.ppf(1 - alpha, df)
        power = 1 - stats.nct.cdf(crit, df, ncp)

    power = float(np.clip(power, 0.0, 1.0))

    return {
        "power": power,
        "beta": 1.0 - power,
        "effect_size": effect_size,
        "n": n,
        "alpha": alpha,
        "test_type": test_type,
    }


def required_sample_size(
    effect_size: float,
    power: float = 0.80,
    alpha: float = 0.05,
    test_type: str = "two-sided",
    max_n: int = 10000,
) -> Dict[str, Any]:
    """Plan required sample size per group for a two-sample t-test.

    Parameters
    ----------
    effect_size : float
        Anticipated standardised effect size.
    power : float, default 0.80
        Desired statistical power.
    alpha : float, default 0.05
        Significance level.
    test_type : {'two-sided', 'one-sided'}, default 'two-sided'
        Directionality of the test.
    max_n : int, default 10000
        Upper bound for search.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'n': required sample size per group
        - 'power': achieved power at that n
        - 'effect_size': anticipated effect size
        - 'alpha': significance level

    Raises
    ------
    ValueError
        If effect_size <= 0, power or alpha invalid, or max_n too small.
    """
    if effect_size <= 0:
        raise ValueError("effect_size must be positive.")
    if not (0 < power < 1):
        raise ValueError("power must be in (0, 1).")
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1).")
    if test_type not in ("two-sided", "one-sided"):
        raise ValueError("test_type must be 'two-sided' or 'one-sided'.")

    # Binary search for minimum n
    lo, hi = 2, max_n
    best_n = max_n
    best_power = 0.0

    while lo <= hi:
        mid = (lo + hi) // 2
        pwr = calculate_power(effect_size, mid, alpha, test_type)["power"]
        if pwr >= power:
            best_n = mid
            best_power = pwr
            hi = mid - 1
        else:
            lo = mid + 1

    return {
        "n": best_n,
        "power": best_power,
        "effect_size": effect_size,
        "alpha": alpha,
        "test_type": test_type,
    }


def power_curve(
    effect_sizes: Sequence[float],
    n_range: Sequence[int],
    alpha: float = 0.05,
    test_type: str = "two-sided",
) -> Dict[str, Any]:
    """Generate a power curve matrix for multiple effect sizes and sample sizes.

    Parameters
    ----------
    effect_sizes : sequence of float
        Effect sizes to evaluate.
    n_range : sequence of int
        Sample sizes (per group) to evaluate.
    alpha : float, default 0.05
        Significance level.
    test_type : {'two-sided', 'one-sided'}, default 'two-sided'
        Directionality of the test.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'effect_sizes': list of effect sizes
        - 'n_range': list of sample sizes
        - 'power_matrix': 2-D list [i_effect_size][j_n]
        - 'alpha': significance level
        - 'test_type': test directionality
    """
    if not effect_sizes or not n_range:
        raise ValueError("effect_sizes and n_range must be non-empty.")

    matrix = []
    for es in effect_sizes:
        row = []
        for n in n_range:
            pwr = calculate_power(es, n, alpha, test_type)["power"]
            row.append(pwr)
        matrix.append(row)

    return {
        "effect_sizes": list(effect_sizes),
        "n_range": list(n_range),
        "power_matrix": matrix,
        "alpha": alpha,
        "test_type": test_type,
    }
