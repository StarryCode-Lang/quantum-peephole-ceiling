"""Effect size estimation for quantum circuit optimization experiments.

Provides Cliff's delta (robust, non-parametric) and Cohen's d (parametric)
with confidence intervals and magnitude interpretation suitable for
Quantum publication standards.
"""

from __future__ import annotations

import numpy as np
from typing import Sequence, Dict, Any, Tuple, Optional


def cliffs_delta(x: Sequence[float], y: Sequence[float]) -> Dict[str, Any]:
    """Calculate Cliff's delta with a normal-approximation confidence interval.

    Cliff's delta is a non-parametric effect size measure based on the
    probability that a randomly chosen observation from one group is larger
    than a randomly chosen observation from the other group, minus the
    reverse probability.

    Parameters
    ----------
    x, y : sequence of float
        Two samples to compare.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'delta': Cliff's delta (range [-1, 1])
        - 'ci_lower': 95% CI lower bound
        - 'ci_upper': 95% CI upper bound
        - 'magnitude': qualitative interpretation
        - 'n1', 'n2': sample sizes

    Raises
    ------
    ValueError
        If either sample is empty.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if x_arr.size == 0 or y_arr.size == 0:
        raise ValueError("Both samples must be non-empty.")

    n1, n2 = len(x_arr), len(y_arr)

    # Vectorised computation of dominance matrix
    # delta = (sum_{i,j} sign(x_i - y_j)) / (n1 * n2)
    # Using broadcasting for speed
    diff = x_arr[:, np.newaxis] - y_arr[np.newaxis, :]
    delta = np.mean(np.sign(diff))

    # Normal approximation variance (Cliff 1993, 1996)
    # Var(delta) = [Var_A + Var_B - Cov] / (n1 * n2)
    # where A_i = sum_j sign(x_i - y_j), B_j = sum_i sign(x_i - y_j)
    a = np.sum(np.sign(diff), axis=1)  # length n1
    b = np.sum(np.sign(diff), axis=0)  # length n2

    var_a = np.var(a, ddof=1) if n1 > 1 else 0.0
    var_b = np.var(b, ddof=1) if n2 > 1 else 0.0

    # Cliff's variance formula
    var_delta = (var_a / (n1 * n2**2)) + (var_b / (n1**2 * n2))
    se = np.sqrt(var_delta) if var_delta > 0 else 0.0

    z = 1.96  # 95% normal CI
    ci_lower = float(np.clip(delta - z * se, -1.0, 1.0))
    ci_upper = float(np.clip(delta + z * se, -1.0, 1.0))

    return {
        "delta": float(delta),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "magnitude": interpret_effect_size(float(delta), metric="cliffs_delta"),
        "n1": n1,
        "n2": n2,
        "se": float(se),
    }


def cohens_d(x: Sequence[float], y: Sequence[float]) -> Dict[str, Any]:
    """Calculate Cohen's d with a bias-corrected (Hedges' g) variant.

    Uses the pooled standard deviation with a small-sample correction factor.

    Parameters
    ----------
    x, y : sequence of float
        Two samples to compare.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'd': Cohen's d
        - 'g': Hedges' g (bias-corrected)
        - 'ci_lower': approximate 95% CI lower bound
        - 'ci_upper': approximate 95% CI upper bound
        - 'magnitude': qualitative interpretation
        - 'n1', 'n2': sample sizes
        - 'pooled_sd': pooled standard deviation

    Raises
    ------
    ValueError
        If either sample is empty or has zero variance.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if x_arr.size == 0 or y_arr.size == 0:
        raise ValueError("Both samples must be non-empty.")

    n1, n2 = len(x_arr), len(y_arr)
    m1, m2 = np.mean(x_arr), np.mean(y_arr)
    v1 = np.var(x_arr, ddof=1)
    v2 = np.var(y_arr, ddof=1)

    # Pooled SD
    pooled_sd = np.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    if pooled_sd == 0:
        raise ValueError("Pooled standard deviation is zero; cannot compute Cohen's d.")

    d = (m1 - m2) / pooled_sd

    # Hedges' g correction
    # J = 1 - 3 / (4 * (n1 + n2 - 2) - 1)
    df = n1 + n2 - 2
    j = 1.0 - 3.0 / (4.0 * df - 1.0) if df > 1 else 1.0
    g = d * j

    # Approximate CI using Satterthwaite-like SE
    se_d = np.sqrt(1.0 / n1 + 1.0 / n2 + d**2 / (2 * df))
    z = 1.96
    ci_lower = float(g - z * se_d)
    ci_upper = float(g + z * se_d)

    return {
        "d": float(d),
        "g": float(g),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "magnitude": interpret_effect_size(float(g), metric="cohens_d"),
        "n1": n1,
        "n2": n2,
        "pooled_sd": float(pooled_sd),
        "se": float(se_d),
    }


def glass_delta(
    x: Sequence[float],
    y: Sequence[float],
    control: str = "auto",
) -> Dict[str, Any]:
    """Calculate Glass's Delta (Glass, 1976) with explicit zero-variance handling.

    Glass's Delta standardises the mean difference by the standard deviation
    of a designated control group rather than the pooled SD:

        Delta = (mean(x) - mean(y)) / sd_control

    This is the effect-size measure required by the project statistical
    protocol (README item 2) for comparisons in which the pooled standard
    deviation is zero — the canonical case being Phase-1 reduction under
    LBL listing, where every observation is exactly 0.0 and Cohen's d is
    undefined.

    Parameters
    ----------
    x, y : sequence of float
        Two samples to compare. By convention ``x`` is the first (often
        treatment) group and ``y`` the second (often baseline/control).
    control : {'auto', 'x', 'y'}, default 'auto'
        Which group supplies the denominator SD.

        - ``'x'`` / ``'y'``: use that group's SD. If that group has zero
          variance, Glass's Delta is undefined (returns NaN with a note),
          because a zero-variance control cannot standardise anything.
        - ``'auto'``: prefer ``y`` (the conventional control/baseline
          position). If ``y`` has zero variance but ``x`` does not, fall
          back to ``x``'s SD (the only non-degenerate denominator
          available) and record the fallback in ``control_group``. This
          reproduces the values previously produced by the retired
          ``d / sqrt(2)`` approximation exactly for one-zero-variance,
          equal-n comparisons, while remaining a properly defined Glass's
          Delta when both groups have nonzero variance.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'delta': Glass's Delta (float; NaN when undefined)
        - 'ci_lower', 'ci_upper': approximate 95% CI (NaN when undefined)
        - 'control_group': which group's SD was used ('x', 'y', or None)
        - 'control_sd': the denominator SD (NaN when undefined)
        - 'magnitude': qualitative interpretation (Cohen 1988 thresholds),
          or 'undefined (zero variance)' when not computable
        - 'n1', 'n2': sample sizes
        - 'note': human-readable description of any fallback/undefined case

    Raises
    ------
    ValueError
        If either sample is empty, has fewer than 2 observations, or
        ``control`` is not one of 'auto'/'x'/'y'.

    Reference
    ---------
        Glass, G. V. (1976). Primary, secondary, and meta-analysis of
        research. Educational Researcher, 5(10), 3-8.
    """
    if control not in ("auto", "x", "y"):
        raise ValueError("control must be 'auto', 'x', or 'y'.")

    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if x_arr.size == 0 or y_arr.size == 0:
        raise ValueError("Both samples must be non-empty.")
    n1, n2 = len(x_arr), len(y_arr)
    if n1 < 2 or n2 < 2:
        raise ValueError("Both samples must have at least 2 observations.")

    m1, m2 = float(np.mean(x_arr)), float(np.mean(y_arr))
    sd_x = float(np.std(x_arr, ddof=1))
    sd_y = float(np.std(y_arr, ddof=1))

    # Resolve the control group.
    note = "control group: y (baseline convention)"
    if control == "x":
        control_group, control_sd = "x", sd_x
        note = "control group: x (explicit)"
    elif control == "y":
        control_group, control_sd = "y", sd_y
    else:  # auto
        if sd_y > 0:
            control_group, control_sd = "y", sd_y
        elif sd_x > 0:
            control_group, control_sd = "x", sd_x
            note = (
                "control group: x (fallback; y has zero variance, so the "
                "only non-degenerate denominator was used)"
            )
        else:
            control_group, control_sd = None, 0.0

    # Undefined cases: zero-variance denominator.
    if control_sd == 0.0:
        if sd_x == 0.0 and sd_y == 0.0:
            reason = "both groups have zero variance"
        else:
            reason = f"designated control group '{control_group}' has zero variance"
        return {
            "delta": float("nan"),
            "ci_lower": float("nan"),
            "ci_upper": float("nan"),
            "control_group": control_group,
            "control_sd": float("nan"),
            "magnitude": "undefined (zero variance)",
            "n1": n1,
            "n2": n2,
            "note": f"Glass's Delta undefined: {reason}.",
        }

    delta = (m1 - m2) / control_sd

    # Approximate SE for Glass's Delta (Hedges 1981, eq. for Glass's estimator):
    # Var(Delta) ~= (n1 + n2) / (n1 * n2) + Delta^2 / (2 * (n_c - 1))
    n_c = n2 if control_group == "y" else n1
    se = float(np.sqrt((n1 + n2) / (n1 * n2) + delta**2 / (2.0 * (n_c - 1))))
    z = 1.96
    ci_lower = float(delta - z * se)
    ci_upper = float(delta + z * se)

    return {
        "delta": float(delta),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "control_group": control_group,
        "control_sd": float(control_sd),
        "magnitude": interpret_effect_size(float(delta), metric="cohens_d"),
        "n1": n1,
        "n2": n2,
        "se": se,
        "note": note,
    }


def interpret_effect_size(delta: float, metric: str = "auto") -> str:
    """Interpret the magnitude of an effect size.

    Uses conventional thresholds for Cohen's d / Hedges' g and
    adapted thresholds for Cliff's delta (absolute value).

    Review M2 fix: previously this function used Cohen's d thresholds
    (0.2/0.5/0.8) for BOTH Cliff's delta and Cohen's d, causing
    inconsistencies with ``core.py`` which uses Cliff-specific
    thresholds (0.147/0.33/0.474).  The ``metric`` parameter now
    selects the correct threshold set:

    - ``metric="cliffs_delta"`` (or ``"delta"``): Cliff 1993 thresholds
      (0.147 / 0.33 / 0.474).
    - ``metric="cohens_d"`` (or ``"d"``, ``"g"``): Cohen 1988 thresholds
      (0.2 / 0.5 / 0.8).
    - ``metric="auto"`` (default): uses Cliff thresholds when
      ``abs(delta) <= 1.0`` (Cliff's delta range) and Cohen thresholds
      otherwise.  This is a heuristic; pass the metric explicitly when
      the type is known.

    Parameters
    ----------
    delta : float
        Effect size estimate (Cohen's d, Hedges' g, or Cliff's delta).
    metric : str
        Which threshold set to use (see above).

    Returns
    -------
    str
        One of: 'negligible', 'small', 'medium', 'large'.
    """
    abs_d = abs(delta)

    # Select threshold set based on metric.
    if metric in ("cliffs_delta", "delta"):
        # Cliff 1993 thresholds — designed for delta in [-1, 1].
        small, medium, large = 0.147, 0.33, 0.474
    elif metric in ("cohens_d", "d", "g"):
        # Cohen 1988 thresholds.
        small, medium, large = 0.2, 0.5, 0.8
    else:  # "auto"
        if abs_d <= 1.0:
            small, medium, large = 0.147, 0.33, 0.474
        else:
            small, medium, large = 0.2, 0.5, 0.8

    if abs_d < small:
        return "negligible"
    elif abs_d < medium:
        return "small"
    elif abs_d < large:
        return "medium"
    else:
        return "large"


def effect_size_table(comparisons: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a summary table of effect sizes for multiple comparisons.

    Parameters
    ----------
    comparisons : sequence of dict
        Each dict must contain:
        - 'name': str, comparison label
        - 'x': sequence of float, first sample
        - 'y': sequence of float, second sample
        - 'method': {'cliffs_delta', 'cohens_d'}, default 'cliffs_delta'

    Returns
    -------
    dict
        Dictionary with keys:
        - 'table': list of dict rows with effect size results
        - 'summary': dict with mean, median, min, max effect sizes

    Raises
    ------
    ValueError
        If comparisons is empty or contains invalid method.
    """
    if not comparisons:
        raise ValueError("comparisons must not be empty.")

    table = []
    deltas = []

    for comp in comparisons:
        name = comp.get("name", "")
        x = comp["x"]
        y = comp["y"]
        method = comp.get("method", "cliffs_delta")

        if method == "cliffs_delta":
            result = cliffs_delta(x, y)
            delta = result["delta"]
        elif method == "cohens_d":
            result = cohens_d(x, y)
            delta = result["g"]
        else:
            raise ValueError(f"Unknown method: {method}")

        row = {
            "comparison": name,
            "method": method,
            "effect_size": float(f"{delta:.3g}"),
            "ci_lower": float(f"{result['ci_lower']:.3g}"),
            "ci_upper": float(f"{result['ci_upper']:.3g}"),
            "magnitude": result["magnitude"],
            "n1": result["n1"],
            "n2": result["n2"],
        }
        table.append(row)
        deltas.append(delta)

    d_arr = np.array(deltas)
    summary = {
        "mean_effect_size": float(np.mean(d_arr)),
        "median_effect_size": float(np.median(d_arr)),
        "min_effect_size": float(np.min(d_arr)),
        "max_effect_size": float(np.max(d_arr)),
        "n_comparisons": len(d_arr),
        "n_negligible": int(np.sum(np.abs(d_arr) < 0.2)),
        "n_small": int(np.sum((np.abs(d_arr) >= 0.2) & (np.abs(d_arr) < 0.5))),
        "n_medium": int(np.sum((np.abs(d_arr) >= 0.5) & (np.abs(d_arr) < 0.8))),
        "n_large": int(np.sum(np.abs(d_arr) >= 0.8)),
    }

    return {"table": table, "summary": summary}


def hedges_g(x: Sequence[float], y: Sequence[float]) -> Dict[str, Any]:
    """Hedges' g effect size (bias-corrected Cohen's d).

    This is a convenience wrapper around :func:`cohens_d` — the Cohen's d
    function already applies the Hedges' g small-sample correction factor
    and returns the result as the ``'g'`` key.  This function exists so
    that callers importing ``hedges_g`` from ``effect_size`` (rather than
    from ``core``) get the same unified ``Dict[str, Any]`` contract.

    Parameters
    ----------
    x, y : sequence of float
        Two samples to compare.

    Returns
    -------
    dict
        Same as :func:`cohens_d` (keys include ``'d'``, ``'g'``,
        ``'ci_lower'``, ``'ci_upper'``, ``'magnitude'``, etc.).

    Raises
    ------
    ValueError
        If either sample is empty or has zero variance.
    """
    return cohens_d(x, y)
