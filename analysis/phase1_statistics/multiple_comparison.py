"""Multiple comparison correction for quantum circuit optimization experiments.

Implements Benjamini-Hochberg FDR control and Holm-Bonferroni family-wise
error rate correction for publication-level statistical reporting in
Quantum.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
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

    # Adjusted p-values (Benjamini-Hochberg-Yekutieli style for general dependence)
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
