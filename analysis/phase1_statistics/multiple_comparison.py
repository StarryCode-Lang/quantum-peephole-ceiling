"""Multiple comparison correction for quantum circuit optimization experiments.

Implements Benjamini-Hochberg FDR control and Holm-Bonferroni family-wise
error rate correction for publication-level statistical reporting in
Quantum.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from typing import Sequence, Dict, List, Any, Optional


def benjamini_hochberg(p_values: Sequence[float], alpha: float = 0.05) -> Dict[str, Any]:
    """Apply Benjamini-Hochberg FDR correction.

    Parameters
    ----------
    p_values : sequence of float
        Raw p-values from multiple hypothesis tests.
    alpha : float, default 0.05
        Desired false discovery rate.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'p_values': original p-values (numpy array)
        - 'adjusted_p': BH-adjusted p-values
        - 'rejected': boolean array indicating rejected null hypotheses
        - 'alpha': FDR level used
        - 'n_tests': number of tests performed
        - 'method': 'Benjamini-Hochberg'

    Raises
    ------
    ValueError
        If any p-value is outside [0, 1] or alpha is invalid.
    """
    p_arr = np.asarray(p_values, dtype=float)
    if p_arr.size == 0:
        raise ValueError("p_values must not be empty.")
    if np.any((p_arr < 0) | (p_arr > 1)):
        raise ValueError("All p-values must lie in [0, 1].")
    if not (0 < alpha <= 1):
        raise ValueError("alpha must be in (0, 1].")

    n = len(p_arr)
    order = np.argsort(p_arr)
    sorted_p = p_arr[order]

    # BH procedure: find largest k such that p_(k) <= (k/m) * alpha
    thresholds = (np.arange(1, n + 1) / n) * alpha
    below = sorted_p <= thresholds
    k = np.max(np.where(below)[0]) + 1 if np.any(below) else 0

    rejected = np.zeros(n, dtype=bool)
    if k > 0:
        rejected[order[:k]] = True

    # Adjusted p-values: standard Benjamini-Hochberg (BH) step-up values.
    # NOTE (review Stage 5 / BH-Y labeling): the formula below is the
    # ORIGINAL BH (1995) adjustment p_(k)*m/k, which assumes independent
    # or positively dependent test statistics.  The previous comment
    # labelled this "Benjamini-Hochberg-Yekutieli style for general
    # dependence", which was misleading: the BY (2001) procedure would
    # additionally multiply by c(m) = sum_{i=1}^{m} 1/i.  If arbitrary
    # dependence must be controlled, call benjamini_yekutieli() instead.
    adjusted = np.zeros(n)
    adjusted[order] = np.minimum.accumulate(
        sorted_p[::-1] * n / np.arange(n, 0, -1)
    )[::-1]
    adjusted = np.minimum(adjusted, 1.0)

    return {
        "p_values": p_arr,
        "adjusted_p": adjusted,
        "rejected": rejected,
        "alpha": alpha,
        "n_tests": n,
        "method": "Benjamini-Hochberg",
        "method_note": (
            "Original BH (1995): assumes independent or positively "
            "dependent tests. For arbitrary dependence, use "
            "benjamini_yekutieli() which applies the c(m) correction."
        ),
        "n_rejected": int(np.sum(rejected)),
    }


def benjamini_yekutieli(p_values: Sequence[float], alpha: float = 0.05) -> Dict[str, Any]:
    """Apply Benjamini-Yekutieli FDR correction for arbitrary dependence.

    BY is more conservative than BH: it multiplies each adjusted p-value
    by c(m) = sum_{i=1}^{m} 1/i, controlling FDR under arbitrary
    dependence structures among the test statistics.

    Parameters
    ----------
    p_values : sequence of float
        Raw p-values from multiple hypothesis tests.
    alpha : float, default 0.05
        Desired false discovery rate.

    Returns
    -------
    dict
        Same structure as :func:`benjamini_hochberg`, with
        ``method='Benjamini-Yekutieli'``.
    """
    p_arr = np.asarray(p_values, dtype=float)
    if p_arr.size == 0:
        raise ValueError("p_values must not be empty.")
    if np.any((p_arr < 0) | (p_arr > 1)):
        raise ValueError("All p-values must lie in [0, 1].")
    if not (0 < alpha <= 1):
        raise ValueError("alpha must be in (0, 1].")

    n = len(p_arr)
    order = np.argsort(p_arr)
    sorted_p = p_arr[order]

    # BY correction factor c(m) = sum_{i=1}^{m} 1/i (harmonic number).
    c_m = float(np.sum(1.0 / np.arange(1, n + 1)))

    # BY thresholds: p_(k) <= (k / (m * c(m))) * alpha
    thresholds = (np.arange(1, n + 1) / (n * c_m)) * alpha
    below = sorted_p <= thresholds
    k = np.max(np.where(below)[0]) + 1 if np.any(below) else 0

    rejected = np.zeros(n, dtype=bool)
    if k > 0:
        rejected[order[:k]] = True

    # BY adjusted p-values: BH adjustment * c(m), clamped to 1.
    adjusted = np.zeros(n)
    adjusted[order] = np.minimum.accumulate(
        sorted_p[::-1] * n * c_m / np.arange(n, 0, -1)
    )[::-1]
    adjusted = np.minimum(adjusted, 1.0)

    return {
        "p_values": p_arr,
        "adjusted_p": adjusted,
        "rejected": rejected,
        "alpha": alpha,
        "n_tests": n,
        "method": "Benjamini-Yekutieli",
        "c_m": c_m,
        "n_rejected": int(np.sum(rejected)),
    }


def holm_bonferroni(p_values: Sequence[float], alpha: float = 0.05) -> Dict[str, Any]:
    """Apply Holm-Bonferroni step-down correction.

    Controls the family-wise error rate (FWER) more powerfully than
    Bonferroni's single-step procedure.

    Parameters
    ----------
    p_values : sequence of float
        Raw p-values from multiple hypothesis tests.
    alpha : float, default 0.05
        Significance level.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'p_values': original p-values
        - 'adjusted_p': Holm-adjusted p-values
        - 'rejected': boolean array indicating rejected null hypotheses
        - 'alpha': significance level used
        - 'n_tests': number of tests performed
        - 'method': 'Holm-Bonferroni'

    Raises
    ------
    ValueError
        If any p-value is outside [0, 1] or alpha is invalid.
    """
    p_arr = np.asarray(p_values, dtype=float)
    if p_arr.size == 0:
        raise ValueError("p_values must not be empty.")
    if np.any((p_arr < 0) | (p_arr > 1)):
        raise ValueError("All p-values must lie in [0, 1].")
    if not (0 < alpha <= 1):
        raise ValueError("alpha must be in (0, 1].")

    n = len(p_arr)
    order = np.argsort(p_arr)
    sorted_p = p_arr[order]

    # Holm step-down thresholds
    thresholds = alpha / np.arange(n, 0, -1)
    # Find first index where p > threshold
    violations = sorted_p > thresholds
    first_violation = np.argmax(violations) if np.any(violations) else n

    rejected = np.zeros(n, dtype=bool)
    if first_violation > 0:
        rejected[order[:first_violation]] = True

    # Adjusted p-values
    adjusted = np.zeros(n)
    adjusted[order] = np.maximum.accumulate(
        sorted_p * np.arange(n, 0, -1)
    )
    adjusted = np.minimum(adjusted, 1.0)

    return {
        "p_values": p_arr,
        "adjusted_p": adjusted,
        "rejected": rejected,
        "alpha": alpha,
        "n_tests": n,
        "method": "Holm-Bonferroni",
        "n_rejected": int(np.sum(rejected)),
    }


def fdr_control_table(
    experiment_results: List[Dict[str, Any]],
    alpha: float = 0.05,
    method: str = "bh",
) -> pd.DataFrame:
    """Generate an FDR-controlled summary table for multiple experiments.

    Parameters
    ----------
    experiment_results : list of dict
        Each dict must contain at least 'experiment' (str) and 'p_value' (float).
        Optional keys: 'comparison', 'effect_size', 'n1', 'n2'.
    alpha : float, default 0.05
        FDR or FWER level.
    method : {'bh', 'holm'}, default 'bh'
        Correction method: 'bh' for Benjamini-Hochberg, 'holm' for Holm-Bonferroni.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns:
        experiment, comparison, p_value, adjusted_p, rejected,
        effect_size, n1, n2, method.

    Raises
    ------
    ValueError
        If experiment_results is empty or method is invalid.
    """
    if not experiment_results:
        raise ValueError("experiment_results must not be empty.")
    if method not in ("bh", "holm"):
        raise ValueError("method must be 'bh' or 'holm'.")

    p_values = [r["p_value"] for r in experiment_results]

    if method == "bh":
        correction = benjamini_hochberg(p_values, alpha=alpha)
    else:
        correction = holm_bonferroni(p_values, alpha=alpha)

    rows = []
    for i, res in enumerate(experiment_results):
        rows.append(
            {
                "experiment": res.get("experiment", ""),
                "comparison": res.get("comparison", ""),
                "p_value": _fmt_p(res["p_value"]),
                "adjusted_p": _fmt_p(correction["adjusted_p"][i]),
                "rejected": bool(correction["rejected"][i]),
                "effect_size": res.get("effect_size", np.nan),
                "n1": res.get("n1", np.nan),
                "n2": res.get("n2", np.nan),
                "method": correction["method"],
            }
        )

    return pd.DataFrame(rows)


def _fmt_p(p: float) -> float:
    """Round p-value to 3 significant figures for PRA reporting."""
    if p == 0:
        return 0.0
    if not np.isfinite(p):
        return p
    # 3 significant figures
    return float(f"{p:.3g}")


def shapiro_wilk_normality_test(data, alpha: float = 0.05) -> Dict[str, Any]:
    """Shapiro-Wilk test for normality.

    Validates the non-normality assumption that motivates the use of
    non-parametric tests (Mann-Whitney U, Kruskal-Wallis) throughout
    this project (review Stage 5).

    The null hypothesis is that the data were drawn from a normal
    distribution. A small p-value (``p < alpha``) indicates sufficient
    evidence to reject normality, justifying the non-parametric testing
    strategy adopted in this project.

    Parameters
    ----------
    data : array-like
        Sample observations to test for normality.
    alpha : float, default 0.05
        Significance level for the normality decision.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'statistic': Shapiro-Wilk W statistic (float)
        - 'p_value': p-value of the test (float)
        - 'is_normal': bool, True if normality is not rejected (p >= alpha)
        - 'alpha': significance level used
        - 'method': 'Shapiro-Wilk'
        - 'n': number of finite observations tested

    Notes
    -----
    For samples larger than 5000 the Shapiro-Wilk test becomes
    unreliable; consider :func:`scipy.stats.kstest` or
    :func:`scipy.stats.normaltest` as alternatives.

    Raises
    ------
    ValueError
        If data has fewer than 3 observations or more than 5000, or if
        alpha is outside (0, 1].
    """
    if not (0 < alpha <= 1):
        raise ValueError("alpha must be in (0, 1].")

    arr = np.asarray(data, dtype=float).ravel()
    arr = arr[np.isfinite(arr)]
    n = len(arr)
    if n < 3:
        raise ValueError("Shapiro-Wilk requires at least 3 observations.")
    if n > 5000:
        raise ValueError(
            "Shapiro-Wilk is unreliable for n > 5000; use KS or "
            "normaltest instead."
        )

    statistic, p_value = stats.shapiro(arr)
    is_normal = bool(p_value >= alpha)

    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "is_normal": is_normal,
        "alpha": alpha,
        "method": "Shapiro-Wilk",
        "n": n,
    }


def levene_variance_test(groups, alpha: float = 0.05) -> Dict[str, Any]:
    """Levene's test for equality of variances (homoscedasticity).

    Tests the null hypothesis that all input groups have equal
    variances. This is a prerequisite for parametric ANOVA; when
    Levene's test rejects, the non-parametric Kruskal-Wallis test
    (used in this project) is preferred (review Stage 5).

    Parameters
    ----------
    groups : sequence of array-like
        List of sample arrays, one per group.
    alpha : float, default 0.05
        Significance level for the equal-variance decision.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'statistic': Levene's W statistic (float)
        - 'p_value': p-value of the test (float)
        - 'equal_variance': bool, True if equal variance is not rejected
        - 'alpha': significance level used
        - 'method': "Levene's test"
        - 'n_groups': number of groups
        - 'group_sizes': list of group sample sizes

    Raises
    ------
    ValueError
        If fewer than 2 groups, any group has fewer than 2 observations,
        or alpha is outside (0, 1].
    """
    if not (0 < alpha <= 1):
        raise ValueError("alpha must be in (0, 1].")
    if len(groups) < 2:
        raise ValueError("At least 2 groups are required.")

    arrs = [np.asarray(g, dtype=float).ravel() for g in groups]
    arrs = [a[np.isfinite(a)] for a in arrs]
    for i, a in enumerate(arrs):
        if len(a) < 2:
            raise ValueError(f"Group {i} has fewer than 2 observations.")

    statistic, p_value = stats.levene(*arrs)
    equal_variance = bool(p_value >= alpha)

    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "equal_variance": equal_variance,
        "alpha": alpha,
        "method": "Levene's test",
        "n_groups": len(arrs),
        "group_sizes": [len(a) for a in arrs],
    }


def dunn_posthoc_test(
    groups,
    group_names: Optional[Sequence[str]] = None,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Dunn's post-hoc test for pairwise comparisons after Kruskal-Wallis.

    Performs non-parametric pairwise multiple comparisons of group mean
    ranks following a significant Kruskal-Wallis result. P-values are
    adjusted with the Bonferroni correction to control the family-wise
    error rate (review Stage 5).

    scipy does not ship a Dunn's test implementation, so the step-down
    procedure is implemented here using the standard rank-based
    z-statistic with a tie correction.

    Parameters
    ----------
    groups : sequence of array-like
        List of sample arrays, one per group.
    group_names : sequence of str, optional
        Names for each group. If None, groups are labelled
        ``'Group 1'``, ``'Group 2'``, ...
    alpha : float, default 0.05
        Significance level used for the rejection decision after
        Bonferroni adjustment.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'method': "Dunn's test"
        - 'adjustment': 'Bonferroni'
        - 'alpha': significance level used
        - 'n_groups': number of groups
        - 'n_comparisons': number of pairwise comparisons
        - 'pairwise': dict keyed by ``'{a} vs {b}'`` whose values are
          dicts with 'z', 'p_value', 'adjusted_p', and 'rejected'
        - 'group_mean_ranks': dict mapping group name to mean rank

    Notes
    -----
    The test statistic for each pair (i, j) is::

        z = (R_i - R_j) / sqrt(sigma^2 * (1/n_i + 1/n_j))

    where ``R_i`` is the mean rank of group *i*, and the variance term
    ``sigma^2`` incorporates a tie correction::

        sigma^2 = N(N+1)/12 - sum(t^3 - t) / (12(N-1))

    with *N* the total sample size and *t* the size of each tie group.

    Raises
    ------
    ValueError
        If fewer than 2 groups, any group is empty, group_names length
        mismatches, or alpha is outside (0, 1].
    """
    if not (0 < alpha <= 1):
        raise ValueError("alpha must be in (0, 1].")
    if len(groups) < 2:
        raise ValueError("At least 2 groups are required.")

    arrs = [np.asarray(g, dtype=float).ravel() for g in groups]
    arrs = [a[np.isfinite(a)] for a in arrs]
    sizes = np.array([len(a) for a in arrs])
    if np.any(sizes == 0):
        raise ValueError("All groups must be non-empty.")

    k = len(arrs)
    if group_names is None:
        group_names = [f"Group {i + 1}" for i in range(k)]
    else:
        group_names = list(group_names)
        if len(group_names) != k:
            raise ValueError(
                "group_names length must match the number of groups."
            )

    all_data = np.concatenate(arrs)
    N = len(all_data)

    ranks = stats.rankdata(all_data)
    splits = np.cumsum(sizes)[:-1]
    group_ranks = np.split(ranks, splits)
    mean_ranks = np.array([np.mean(r) for r in group_ranks])

    _, counts = np.unique(all_data, return_counts=True)
    tie_term = (
        np.sum(counts ** 3 - counts) / (12.0 * (N - 1)) if N > 1 else 0.0
    )
    sigma_sq = N * (N + 1) / 12.0 - tie_term

    n_comparisons = k * (k - 1) // 2
    pairs: List[str] = []
    z_values: List[float] = []
    p_values: List[float] = []

    for i in range(k):
        for j in range(i + 1, k):
            se = np.sqrt(sigma_sq * (1.0 / sizes[i] + 1.0 / sizes[j]))
            z = (mean_ranks[i] - mean_ranks[j]) / se
            p = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
            pairs.append(f"{group_names[i]} vs {group_names[j]}")
            z_values.append(float(z))
            p_values.append(float(p))

    p_arr = np.array(p_values)
    adjusted = np.minimum(p_arr * n_comparisons, 1.0)
    rejected = adjusted < alpha

    pairwise: Dict[str, Any] = {}
    for idx, label in enumerate(pairs):
        pairwise[label] = {
            "z": z_values[idx],
            "p_value": p_values[idx],
            "adjusted_p": float(adjusted[idx]),
            "rejected": bool(rejected[idx]),
        }

    return {
        "method": "Dunn's test",
        "adjustment": "Bonferroni",
        "alpha": alpha,
        "n_groups": k,
        "n_comparisons": n_comparisons,
        "pairwise": pairwise,
        "group_mean_ranks": {
            group_names[i]: float(mean_ranks[i]) for i in range(k)
        },
    }
