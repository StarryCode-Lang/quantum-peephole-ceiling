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


_MWU_PITMAN_ARE = 0.955


def nonparametric_power_analysis(
    effect_size: float,
    n1: int,
    n2: int,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Estimate statistical power for the Mann-Whitney U test (review L9).

    The Mann-Whitney U test is the non-parametric test actually used in
    this project. Because no closed-form exact power formula exists for
    it, power is approximated via the asymptotic relative efficiency
    (ARE) approach: the parametric (two-sample t-test) power is
    computed first and then scaled by the Pitman ARE of the
    Mann-Whitney U test relative to the t-test under normality (0.955)::

        nonparametric_power ~= parametric_power * 0.955

    Parameters
    ----------
    effect_size : float
        Standardised effect size (Cohen's d / Hedges' g).
    n1 : int
        Sample size of group 1.
    n2 : int
        Sample size of group 2.
    alpha : float, default 0.05
        Significance level (two-sided test).

    Returns
    -------
    dict
        Dictionary with keys:
        - 'power': estimated Mann-Whitney U power (1 - beta)
        - 'parametric_power': two-sample t-test power at the same inputs
        - 'nonparametric_power': same as 'power'
        - 'are': the Pitman ARE factor used (0.955)
        - 'effect_size': input effect size
        - 'n1', 'n2': input sample sizes
        - 'alpha': significance level
        - 'method': 'Mann-Whitney U (ARE approximation)'
        - 'approximation_note': description of the approximation

    Notes
    -----
    This is an approximation. The Pitman ARE of 0.955 holds under
    normality, where it gives the *relative efficiency* in the limit as
    the effect size approaches zero. The resulting estimate should be
    treated as a **lower bound on power for non-normal distributions**:
    the Mann-Whitney U test can be substantially more powerful than the
    t-test when the data are heavy-tailed or skewed, so the true power
    may exceed this estimate. For heavy-tailed distributions the ARE
    can exceed 1.0 (i.e. the Mann-Whitney U test is more efficient than
    the t-test), which this conservative approximation does not capture.

    For a more precise estimate, consider Monte-Carlo simulation of the
    Mann-Whitney U test under the target distribution.

    Raises
    ------
    ValueError
        If n1 or n2 <= 1, effect_size < 0, or alpha is outside (0, 1).
    """
    if n1 <= 1 or n2 <= 1:
        raise ValueError("Both sample sizes must be > 1.")
    if effect_size < 0:
        raise ValueError("effect_size must be non-negative.")
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1).")

    ncp = effect_size / np.sqrt(1.0 / n1 + 1.0 / n2)
    df = n1 + n2 - 2
    crit = stats.t.ppf(1 - alpha / 2, df)
    parametric_power = 1.0 - stats.nct.cdf(crit, df, ncp) + stats.nct.cdf(
        -crit, df, ncp
    )
    parametric_power = float(np.clip(parametric_power, 0.0, 1.0))

    nonparametric_power = float(
        np.clip(parametric_power * _MWU_PITMAN_ARE, 0.0, 1.0)
    )

    return {
        "power": nonparametric_power,
        "parametric_power": parametric_power,
        "nonparametric_power": nonparametric_power,
        "are": _MWU_PITMAN_ARE,
        "effect_size": effect_size,
        "n1": n1,
        "n2": n2,
        "alpha": alpha,
        "method": "Mann-Whitney U (ARE approximation)",
        "approximation_note": (
            "Power approximated as parametric (t-test) power * Pitman "
            "ARE (0.955). This is a lower bound on power for non-normal "
            "distributions; the Mann-Whitney U test can be more "
            "powerful than the t-test under heavy-tailed or skewed data."
        ),
    }


_POWER_THRESHOLD = 0.80


def report_power_for_experiment(
    experiment_id: str,
    n: int,
    effect_size: float,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Report power for a key experiment (review H6).

    Returns both the parametric (two-sample t-test) and the
    non-parametric (Mann-Whitney U) power estimates for an experiment,
    and explicitly flags underpowered experiments (power < 0.80).

    Parameters
    ----------
    experiment_id : str
        Identifier for the experiment being reported.
    n : int
        Sample size per group (assumes balanced design).
    effect_size : float
        Standardised effect size (Cohen's d / Hedges' g).
    alpha : float, default 0.05
        Significance level.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'experiment_id': input identifier
        - 'n': sample size per group
        - 'effect_size': input effect size
        - 'alpha': significance level
        - 'parametric_power_ttest': two-sample t-test power
        - 'nonparametric_power_mwu': Mann-Whitney U power estimate
        - 'power_threshold': the underpowering threshold (0.80)
        - 'underpowered': bool, True if either power estimate < 0.80
        - 'status': 'adequate' or 'underpowered'
        - 'recommended_min_n': minimum n per group for the
          non-parametric test to reach 0.80 power (or None if already
          adequate or unattainable)

    Notes
    -----
    The Mann-Whitney U power uses the ARE approximation from
    :func:`nonparametric_power_analysis`. See that function's docstring
    for the limitations of this estimate.

    Raises
    ------
    ValueError
        If n <= 1, effect_size <= 0, or alpha is outside (0, 1).
    """
    if n <= 1:
        raise ValueError("Sample size n must be > 1.")
    if effect_size <= 0:
        raise ValueError("effect_size must be positive.")
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1).")

    param = calculate_power(effect_size, n, alpha=alpha, test_type="two-sided")
    nonparam = nonparametric_power_analysis(effect_size, n, n, alpha=alpha)

    param_power = param["power"]
    nonparam_power = nonparam["power"]
    underpowered = bool(
        param_power < _POWER_THRESHOLD or nonparam_power < _POWER_THRESHOLD
    )

    recommended_min_n: Optional[int]
    if nonparam_power >= _POWER_THRESHOLD:
        recommended_min_n = None
    else:
        lo = max(n, 2)
        hi = max(n * 2, 100)
        found = None
        for _ in range(20):
            p_hi = nonparametric_power_analysis(
                effect_size, hi, hi, alpha=alpha
            )["power"]
            if np.isfinite(p_hi) and p_hi >= _POWER_THRESHOLD:
                break
            if hi >= 50000:
                break
            hi *= 2
        while lo <= hi and hi <= 50000:
            mid = (lo + hi) // 2
            p_mid = nonparametric_power_analysis(
                effect_size, mid, mid, alpha=alpha
            )["power"]
            if np.isfinite(p_mid) and p_mid >= _POWER_THRESHOLD:
                found = mid
                hi = mid - 1
            else:
                lo = mid + 1
        recommended_min_n = found

    return {
        "experiment_id": experiment_id,
        "n": n,
        "effect_size": effect_size,
        "alpha": alpha,
        "parametric_power_ttest": param_power,
        "nonparametric_power_mwu": nonparam_power,
        "power_threshold": _POWER_THRESHOLD,
        "underpowered": underpowered,
        "status": "underpowered" if underpowered else "adequate",
        "recommended_min_n": recommended_min_n,
    }
