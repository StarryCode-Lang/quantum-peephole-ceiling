"""Bootstrap confidence intervals with convergence diagnostics.

Implements percentile bootstrap CIs, convergence checks via increasing
resample counts, and full bootstrap distribution extraction for
publication-quality statistical reporting.
"""

from __future__ import annotations

import numpy as np
from typing import Sequence, Callable, Dict, Any, Optional


def bootstrap_ci(
    data: Sequence[float],
    statistic: Callable[[np.ndarray], float] = np.mean,
    n_bootstrap: int = 10000,
    ci: float = 95,
    random_seed: Optional[int] = 42,
) -> Dict[str, Any]:
    """Compute a percentile bootstrap confidence interval.

    Parameters
    ----------
    data : sequence of float
        Observed sample.
    statistic : callable, default np.mean
        Scalar statistic function applied to resampled arrays.
    n_bootstrap : int, default 10000
        Number of bootstrap resamples.
    ci : float, default 95
        Confidence level in percent (e.g., 95 for 95% CI).
    random_seed : int or None, default 42
        Random seed for reproducibility.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'estimate': point estimate on original data
        - 'ci_lower': lower bound of CI
        - 'ci_upper': upper bound of CI
        - 'n_bootstrap': number of resamples
        - 'ci_level': confidence level
        - 'std_error': bootstrap standard error
        - 'converged': bool, whether CI width is stable (see bootstrap_convergence)

    Raises
    ------
    ValueError
        If data is empty, n_bootstrap < 100, or ci invalid.
    """
    data_arr = np.asarray(data, dtype=float)
    if data_arr.size == 0:
        raise ValueError("data must not be empty.")
    if n_bootstrap < 100:
        raise ValueError("n_bootstrap must be at least 100.")
    if not (0 < ci < 100):
        raise ValueError("ci must be in (0, 100).")

    rng = np.random.default_rng(random_seed)
    n = len(data_arr)
    point = float(statistic(data_arr))

    boot_stats = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        sample = rng.choice(data_arr, size=n, replace=True)
        boot_stats[i] = statistic(sample)

    alpha = (100 - ci) / 2.0
    ci_lower = float(np.percentile(boot_stats, alpha))
    ci_upper = float(np.percentile(boot_stats, 100 - alpha))

    # Convergence check at current n_bootstrap
    conv = bootstrap_convergence(data_arr, statistic, max_bootstrap=n_bootstrap, random_seed=random_seed)

    return {
        "estimate": point,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "n_bootstrap": n_bootstrap,
        "ci_level": ci,
        "std_error": float(np.std(boot_stats, ddof=1)),
        "converged": conv["converged"],
        "convergence_note": conv["note"],
    }


def bootstrap_convergence(
    data: Sequence[float],
    statistic: Callable[[np.ndarray], float] = np.mean,
    max_bootstrap: int = 50000,
    tolerance: float = 0.01,
    random_seed: Optional[int] = 42,
) -> Dict[str, Any]:
    """Check whether bootstrap CI has converged by comparing at multiple scales.

    The procedure computes CIs at geometrically spaced resample counts
    (e.g., 1000, 2500, 5000, 10000, 25000, 50000) and checks whether
    the CI width changes by less than ``tolerance`` relative to the
    width at the largest count.

    Parameters
    ----------
    data : sequence of float
        Observed sample.
    statistic : callable, default np.mean
        Scalar statistic function.
    max_bootstrap : int, default 50000
        Maximum number of resamples to evaluate.
    tolerance : float, default 0.01
        Relative tolerance for CI width stability (1% = 0.01).
    random_seed : int or None, default 42
        Random seed for reproducibility.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'converged': bool
        - 'widths': dict mapping n_bootstrap -> CI width
        - 'tolerance': relative tolerance used
        - 'note': human-readable description
    """
    data_arr = np.asarray(data, dtype=float)
    if data_arr.size == 0:
        raise ValueError("data must not be empty.")

    rng = np.random.default_rng(random_seed)
    n = len(data_arr)

    # Geometric progression of resample counts up to max_bootstrap
    counts = []
    c = 1000
    while c <= max_bootstrap:
        counts.append(c)
        c = int(c * 2.5) if c < 10000 else int(c * 2)
    if counts[-1] != max_bootstrap:
        counts.append(max_bootstrap)

    widths: Dict[int, float] = {}
    for count in counts:
        stats = np.empty(count)
        for i in range(count):
            sample = rng.choice(data_arr, size=n, replace=True)
            stats[i] = statistic(sample)
        widths[count] = float(np.percentile(stats, 97.5) - np.percentile(stats, 2.5))

    final_width = widths[max_bootstrap]
    if final_width == 0:
        converged = all(w == 0 for w in widths.values())
        note = "CI width is zero; convergence trivial." if converged else "CI width unstable (zero at max)."
        return {"converged": converged, "widths": widths, "tolerance": tolerance, "note": note}

    relative_changes = {
        c: abs(widths[c] - final_width) / final_width for c in counts[:-1]
    }
    converged = all(rel <= tolerance for rel in relative_changes.values())

    if converged:
        note = f"CI width stable within {tolerance*100:.1f}% across all tested resample counts."
    else:
        max_change = max(relative_changes.values())
        note = f"CI width changed by up to {max_change*100:.1f}% — may need more resamples."

    return {"converged": converged, "widths": widths, "tolerance": tolerance, "note": note}


def bootstrap_distribution(
    data: Sequence[float],
    statistic: Callable[[np.ndarray], float] = np.mean,
    n_bootstrap: int = 10000,
    random_seed: Optional[int] = 42,
) -> Dict[str, Any]:
    """Return the full bootstrap distribution of a statistic.

    Parameters
    ----------
    data : sequence of float
        Observed sample.
    statistic : callable, default np.mean
        Scalar statistic function.
    n_bootstrap : int, default 10000
        Number of bootstrap resamples.
    random_seed : int or None, default 42
        Random seed for reproducibility.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'distribution': numpy array of bootstrap statistics
        - 'estimate': point estimate on original data
        - 'n_bootstrap': number of resamples
        - 'percentiles': dict of common percentiles (1, 5, 10, 25, 50, 75, 90, 95, 99)

    Raises
    ------
    ValueError
        If data is empty or n_bootstrap < 100.
    """
    data_arr = np.asarray(data, dtype=float)
    if data_arr.size == 0:
        raise ValueError("data must not be empty.")
    if n_bootstrap < 100:
        raise ValueError("n_bootstrap must be at least 100.")

    rng = np.random.default_rng(random_seed)
    n = len(data_arr)
    point = float(statistic(data_arr))

    dist = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        sample = rng.choice(data_arr, size=n, replace=True)
        dist[i] = statistic(sample)

    percentiles = {int(p): float(np.percentile(dist, p)) for p in (1, 5, 10, 25, 50, 75, 90, 95, 99)}

    return {
        "distribution": dist,
        "estimate": point,
        "n_bootstrap": n_bootstrap,
        "percentiles": percentiles,
    }
