"""Descriptive inference for zero-inflated reduction outcomes.

Point-mass-at-zero outcomes make ordinary variance-based summaries and Pearson
correlations uninformative. These helpers keep structural zeros explicit and
describe the nonzero component separately; they do not fit a generative
zero-inflated model or impute structural zeros.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from .effect_size import cliffs_delta


def _finite_values(values: Sequence[float]) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        raise ValueError("values must contain at least one finite observation")
    return finite


def summarize_zero_inflated(
    values: Sequence[float], *, zero_tolerance: float = 0.0
) -> dict[str, Any]:
    """Return zero mass and conditional nonzero summaries.

    ``zero_rate`` describes the observed point mass at zero. Conditional
    summaries are computed only on finite observations whose absolute value is
    greater than ``zero_tolerance``.
    """
    if zero_tolerance < 0:
        raise ValueError("zero_tolerance must be non-negative")

    finite = _finite_values(values)
    zero_mask = np.abs(finite) <= zero_tolerance
    nonzero = finite[~zero_mask]
    result: dict[str, Any] = {
        "n": int(finite.size),
        "zero_count": int(zero_mask.sum()),
        "zero_rate": float(zero_mask.mean()),
        "nonzero_count": int(nonzero.size),
        "conditional_nonzero_mean": float(np.mean(nonzero)) if nonzero.size else None,
        "conditional_nonzero_median": float(np.median(nonzero)) if nonzero.size else None,
        "conditional_nonzero_std": (
            float(np.std(nonzero, ddof=1)) if nonzero.size >= 2 else None
        ),
    }
    return result


def compare_zero_inflated(
    x: Sequence[float],
    y: Sequence[float],
    *,
    zero_tolerance: float = 0.0,
) -> dict[str, Any]:
    """Compare zero mass and conditional nonzero effects for two samples."""
    x_summary = summarize_zero_inflated(x, zero_tolerance=zero_tolerance)
    y_summary = summarize_zero_inflated(y, zero_tolerance=zero_tolerance)

    x_values = _finite_values(x)
    y_values = _finite_values(y)
    x_nonzero = x_values[np.abs(x_values) > zero_tolerance]
    y_nonzero = y_values[np.abs(y_values) > zero_tolerance]

    conditional_delta = None
    if x_nonzero.size and y_nonzero.size:
        conditional_delta = cliffs_delta(x_nonzero, y_nonzero)["delta"]

    x_mean = x_summary["conditional_nonzero_mean"]
    y_mean = y_summary["conditional_nonzero_mean"]
    return {
        "x": x_summary,
        "y": y_summary,
        "zero_rate_difference": x_summary["zero_rate"] - y_summary["zero_rate"],
        "conditional_nonzero_mean_difference": (
            x_mean - y_mean if x_mean is not None and y_mean is not None else None
        ),
        "conditional_nonzero_cliffs_delta": conditional_delta,
    }
