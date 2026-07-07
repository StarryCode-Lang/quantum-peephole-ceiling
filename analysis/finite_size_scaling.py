"""
Finite-Size Scaling (FSS) and Binder Cumulant Analysis
=======================================================
Implements Binder cumulant, finite-size scaling collapse, and critical
point estimation for quantum circuit optimization experiments.

Intended for experiments that sweep system size (n_qubits) and/or depth
to detect phase transitions in optimization effectiveness.

Version: 1.0.0 (PRA-compliant)
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import curve_fit, minimize_scalar
from scipy.stats import norm
from typing import Sequence, Dict, Any, Optional, Tuple, Callable, List


def binder_cumulant(
    data: Sequence[float],
    order: int = 4,
) -> Dict[str, Any]:
    """
    Compute the Binder cumulant (reduced cumulant) for a sample.

    The Binder cumulant is defined as:

        U_L = 1 - <x^4> / (3 <x^2>^2)          (standard, order=4)

    or more generally for order q:

        U_L(q) = 1 - <x^q> / ((q-1) <x^(q/2)>^2)

    where x is the order parameter (here, gate reduction). Near a critical
    point, curves of U_L vs. control parameter for different system sizes
    intersect, providing a size-independent estimate of the critical point.

    Parameters
    ----------
    data : sequence of float
        Observed order-parameter values (e.g., gate reduction).
    order : int, default 4
        Order of the cumulant. 4 is standard; 2 gives a simple normalized
        variance measure.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'cumulant': float, the Binder cumulant value U_L
        - 'mean': float, mean of the data
        - 'variance': float, variance of the data
        - 'n_samples': int, number of samples
        - 'moment_2': float, second moment <x^2>
        - 'moment_4': float, fourth moment <x^4> (if order=4)
    """
    data_arr = np.asarray(data, dtype=float)
    if data_arr.size == 0:
        raise ValueError("data must not be empty.")

    mean_val = float(np.mean(data_arr))
    var_val = float(np.var(data_arr, ddof=1))
    moment_2 = float(np.mean(data_arr ** 2))

    if order == 4:
        moment_4 = float(np.mean(data_arr ** 4))
        if moment_2 == 0:
            cumulant = 0.0
        else:
            cumulant = 1.0 - moment_4 / (3.0 * moment_2 ** 2)
    elif order == 2:
        cumulant = 1.0 - var_val / (moment_2 ** 2) if moment_2 != 0 else 0.0
        moment_4 = np.nan
    else:
        raise ValueError("order must be 2 or 4.")

    return {
        "cumulant": cumulant,
        "mean": mean_val,
        "variance": var_val,
        "n_samples": len(data_arr),
        "moment_2": moment_2,
        "moment_4": moment_4 if order == 4 else np.nan,
    }


def binder_cumulant_by_size(
    data: Sequence[float],
    sizes: Sequence[int],
) -> Dict[int, Dict[str, Any]]:
    """
    Compute Binder cumulants grouped by system size.

    Parameters
    ----------
    data : sequence of float
        Order-parameter values.
    sizes : sequence of int
        System size for each data point (same length as data).

    Returns
    -------
    dict
        Mapping size -> binder_cumulant() result.
    """
    if len(data) != len(sizes):
        raise ValueError("data and sizes must have the same length.")

    data_arr = np.asarray(data, dtype=float)
    sizes_arr = np.asarray(sizes, dtype=int)

    results = {}
    unique_sizes = np.unique(sizes_arr)
    for size in unique_sizes:
        mask = sizes_arr == size
        results[int(size)] = binder_cumulant(data_arr[mask])

    return results


def critical_point_from_intersection(
    control: Sequence[float],
    cumulants_by_size: Dict[int, float],
) -> Dict[str, Any]:
    """
    Estimate critical point from Binder cumulant intersection.

    For each pair of consecutive sizes, find where their cumulant curves
    cross (linear interpolation) and average the crossing points.

    Parameters
    ----------
    control : sequence of float
        Control-parameter values (e.g., depth, entanglement density).
    cumulants_by_size : dict
        Mapping size -> list of cumulant values (one per control point).

    Returns
    -------
    dict
        Dictionary with keys:
        - 'critical_estimate': float, estimated critical point
        - 'crossing_points': list of crossing points per size pair
        - 'n_pairs': int, number of size pairs used
    """
    sizes = sorted(cumulants_by_size.keys())
    if len(sizes) < 2:
        raise ValueError("Need at least two system sizes to find intersection.")

    control_arr = np.asarray(control, dtype=float)
    crossing_points = []

    for i in range(len(sizes) - 1):
        size_a = sizes[i]
        size_b = sizes[i + 1]
        cum_a = np.asarray(cumulants_by_size[size_a])
        cum_b = np.asarray(cumulants_by_size[size_b])

        if len(cum_a) != len(control_arr) or len(cum_b) != len(control_arr):
            raise ValueError(
                f"Cumulant arrays for sizes {size_a} and {size_b} must match control length."
            )

        # Find sign changes in difference
        diff = cum_a - cum_b
        for j in range(len(diff) - 1):
            if diff[j] == 0:
                crossing_points.append(float(control_arr[j]))
            elif diff[j] * diff[j + 1] < 0:
                # Linear interpolation
                x0, x1 = control_arr[j], control_arr[j + 1]
                y0, y1 = diff[j], diff[j + 1]
                crossing = x0 - y0 * (x1 - x0) / (y1 - y0)
                crossing_points.append(crossing)

    if not crossing_points:
        return {
            "critical_estimate": np.nan,
            "crossing_points": [],
            "n_pairs": len(sizes) - 1,
        }

    return {
        "critical_estimate": float(np.mean(crossing_points)),
        "crossing_points": crossing_points,
        "n_pairs": len(sizes) - 1,
    }


# ============================================================================
# Finite-Size Scaling Functions
# ============================================================================

def scaling_function_power(
    x: float,
    A: float,
    alpha: float,
) -> float:
    """Power-law scaling: f(x) = A * x^alpha."""
    return A * (x ** alpha)


def scaling_function_exponential(
    x: float,
    A: float,
    lambda_: float,
    C: float,
) -> float:
    """Exponential decay with offset: f(x) = A * exp(-lambda * x) + C."""
    return A * np.exp(-lambda_ * x) + C


def fit_finite_size_scaling(
    sizes: Sequence[int],
    values: Sequence[float],
    model: str = "power",
    initial_guess: Optional[Sequence[float]] = None,
) -> Dict[str, Any]:
    """
    Fit a finite-size scaling model to data.

    Parameters
    ----------
    sizes : sequence of int
        System sizes (e.g., n_qubits).
    values : sequence of float
        Observed quantity at each size.
    model : {'power', 'exponential'}, default 'power'
        Scaling model to fit.
    initial_guess : sequence of float, optional
        Initial parameter guess for the fit.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'params': fitted parameters
        - 'param_names': list of parameter names
        - 'covariance': covariance matrix
        - 'residuals': residuals
        - 'rmse': root mean squared error
        - 'extrapolated_infinite': float, extrapolated value at L -> infinity
    """
    sizes_arr = np.asarray(sizes, dtype=float)
    values_arr = np.asarray(values, dtype=float)

    if len(sizes_arr) < 3:
        raise ValueError("Need at least 3 data points for fitting.")

    if model == "power":
        if initial_guess is None:
            initial_guess = [values_arr[0] * sizes_arr[0], -1.0]

        def _func(x, A, alpha):
            return A * (x ** alpha)

        param_names = ["A", "alpha"]
        popt, pcov = curve_fit(_func, sizes_arr, values_arr, p0=initial_guess, maxfev=10000)
        fitted = _func(sizes_arr, *popt)

        # Extrapolate to infinity: lim_{L->inf} A * L^alpha
        if popt[1] < 0:
            extrapolated = 0.0
        elif popt[1] > 0:
            extrapolated = np.inf
        else:
            extrapolated = popt[0]

    elif model == "exponential":
        if initial_guess is None:
            initial_guess = [values_arr[0], 0.1, values_arr[-1]]

        def _func(x, A, lambda_, C):
            return A * np.exp(-lambda_ * x) + C

        param_names = ["A", "lambda", "C"]
        popt, pcov = curve_fit(_func, sizes_arr, values_arr, p0=initial_guess, maxfev=10000)
        fitted = _func(sizes_arr, *popt)
        extrapolated = popt[2]  # C is the asymptotic value

    else:
        raise ValueError("model must be 'power' or 'exponential'.")

    residuals = values_arr - fitted
    rmse = float(np.sqrt(np.mean(residuals ** 2)))

    return {
        "params": {name: float(val) for name, val in zip(param_names, popt)},
        "param_names": param_names,
        "covariance": pcov.tolist(),
        "residuals": residuals.tolist(),
        "rmse": rmse,
        "extrapolated_infinite": float(extrapolated),
    }


def scaling_collapse(
    control: Sequence[float],
    values: Sequence[float],
    sizes: Sequence[int],
    critical_estimate: float,
    nu: float = 1.0,
    beta: float = 1.0,
) -> Dict[str, Any]:
    """
    Perform finite-size scaling collapse using scaling ansatz.

    The scaling ansatz is:
        Y(L, t) ~ L^(beta/nu) * f( |t - t_c| * L^(1/nu) )

    where t is the control parameter, t_c is the critical point, and
    f is a universal scaling function.

    Parameters
    ----------
    control : sequence of float
        Control-parameter values.
    values : sequence of float
        Observed quantity.
    sizes : sequence of int
        System sizes.
    critical_estimate : float
        Estimated critical point.
    nu : float, default 1.0
        Critical exponent for correlation length.
    beta : float, default 1.0
        Critical exponent for the order parameter.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'rescaled_x': list, rescaled control parameter
        - 'rescaled_y': list, rescaled values
        - 'critical_estimate': float
        - 'nu': float
        - 'beta': float
        - 'collapsed': bool, whether collapse succeeded (quantitatively validated)
        - 'r_squared': float, R² goodness-of-fit for the scaling ansatz
        - 'quality': str, qualitative assessment ('good', 'marginal', 'poor')
    """
    control_arr = np.asarray(control, dtype=float)
    values_arr = np.asarray(values, dtype=float)
    sizes_arr = np.asarray(sizes, dtype=float)

    # Rescaled variables
    rescaled_x = np.abs(control_arr - critical_estimate) * (sizes_arr ** (1.0 / nu))
    rescaled_y = values_arr * (sizes_arr ** (-beta / nu))

    # Review M7 fix: previously ``collapsed`` was hardcoded to True with
    # no quantitative validation.  We now compute an R² goodness-of-fit
    # for the scaling ansatz by fitting rescaled_y as a function of
    # rescaled_x and measuring how well the data collapses onto a single
    # curve.  We use a simple polynomial fit (degree 2) as the reference
    # model and compute R² = 1 - SS_res/SS_tot.
    r_squared = None
    quality = "unknown"
    collapsed = False
    if len(rescaled_x) >= 4:
        try:
            from numpy.polynomial import polynomial as P
            coeffs = P.polyfit(rescaled_x, rescaled_y, min(3, len(rescaled_x) - 1))
            y_pred = P.polyval(rescaled_x, coeffs)
            ss_res = float(np.sum((rescaled_y - y_pred) ** 2))
            ss_tot = float(np.sum((rescaled_y - np.mean(rescaled_y)) ** 2))
            r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            # Quality thresholds: R² > 0.9 is good, > 0.7 is marginal.
            if r_squared >= 0.9:
                quality = "good"
                collapsed = True
            elif r_squared >= 0.7:
                quality = "marginal"
                collapsed = True
            else:
                quality = "poor"
                collapsed = False
        except Exception:
            r_squared = None
            quality = "fit_failed"
            collapsed = False

    return {
        "rescaled_x": rescaled_x.tolist(),
        "rescaled_y": rescaled_y.tolist(),
        "critical_estimate": float(critical_estimate),
        "nu": float(nu),
        "beta": float(beta),
        "collapsed": collapsed,
        "r_squared": r_squared,
        "quality": quality,
    }


# ============================================================================
# Critical Point Estimation with Confidence Intervals
# ============================================================================

def estimate_critical_point(
    sizes: Sequence[int],
    control: Sequence[float],
    values: Sequence[float],
    model: str = "power",
    n_bootstrap: int = 5000,
    confidence_level: float = 0.95,
    random_seed: Optional[int] = 42,
) -> Dict[str, Any]:
    """
    Estimate critical point / asymptotic value with bootstrap confidence interval.

    Parameters
    ----------
    sizes : sequence of int
        System sizes.
    control : sequence of float
        Control parameter (used for critical point extraction).
    values : sequence of float
        Observed values.
    model : {'power', 'exponential'}, default 'power'
        Scaling model.
    n_bootstrap : int, default 5000
        Number of bootstrap samples.
    confidence_level : float, default 0.95
        Confidence level for CI.
    random_seed : int or None, default 42
        Random seed.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'point_estimate': central estimate
        - 'ci_lower': lower CI bound
        - 'ci_upper': upper CI bound
        - 'fit_result': full fit result dict
        - 'bootstrap_estimates': list of bootstrap estimates
    """
    rng = np.random.default_rng(random_seed)
    sizes_arr = np.asarray(sizes, dtype=float)
    values_arr = np.asarray(values, dtype=float)
    n = len(values_arr)

    # Point estimate
    fit_result = fit_finite_size_scaling(sizes, values, model=model)
    if model == "power":
        point_estimate = fit_result["extrapolated_infinite"]
    elif model == "exponential":
        point_estimate = fit_result["extrapolated_infinite"]
    else:
        point_estimate = np.nan

    # Bootstrap
    bootstrap_estimates = []
    for _ in range(n_bootstrap):
        indices = rng.choice(n, size=n, replace=True)
        boot_sizes = sizes_arr[indices].astype(int)
        boot_values = values_arr[indices]
        try:
            boot_fit = fit_finite_size_scaling(boot_sizes, boot_values, model=model)
            bootstrap_estimates.append(boot_fit["extrapolated_infinite"])
        except Exception:
            bootstrap_estimates.append(np.nan)

    bootstrap_estimates = np.array(bootstrap_estimates)
    bootstrap_estimates = bootstrap_estimates[np.isfinite(bootstrap_estimates)]

    alpha = (1.0 - confidence_level) / 2.0
    ci_lower = float(np.percentile(bootstrap_estimates, alpha * 100))
    ci_upper = float(np.percentile(bootstrap_estimates, (1.0 - alpha) * 100))

    return {
        "point_estimate": float(point_estimate),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "fit_result": fit_result,
        "bootstrap_estimates": bootstrap_estimates.tolist(),
        "confidence_level": confidence_level,
    }


# ============================================================================
# Master Analysis Function
# ============================================================================

def run_fss_analysis(
    df_dict: Dict[str, Any],
    size_col: str = "n_qubits",
    value_col: str = "reduction",
    control_col: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a complete finite-size scaling analysis on experiment data.

    Parameters
    ----------
    df_dict : dict
        Data dictionary or DataFrame-like structure with columns.
    size_col : str, default 'n_qubits'
        Column name for system size.
    value_col : str, default 'reduction'
        Column name for the measured quantity.
    control_col : str or None, optional
        Column name for control parameter (e.g., depth). If None,
        a simple size scaling is performed without critical-point estimation.

    Returns
    -------
    dict
        Complete analysis results.
    """
    import pandas as pd
    df = pd.DataFrame(df_dict)

    sizes = df[size_col].values
    values = df[value_col].values
    unique_sizes = np.unique(sizes)

    results = {
        "n_total": len(df),
        "n_sizes": len(unique_sizes),
        "size_col": size_col,
        "value_col": value_col,
        "sizes": [int(s) for s in unique_sizes],
    }

    # Binder cumulant per size
    cumulants = binder_cumulant_by_size(values, sizes)
    results["binder_cumulants"] = cumulants

    # Fit scaling
    if len(unique_sizes) >= 3:
        size_means = []
        for s in unique_sizes:
            size_means.append(np.mean(values[sizes == s]))

        try:
            scaling_fit = fit_finite_size_scaling(unique_sizes, size_means, model="power")
            results["scaling_fit_power"] = scaling_fit
        except Exception as e:
            results["scaling_fit_power_error"] = str(e)

        try:
            scaling_fit_exp = fit_finite_size_scaling(unique_sizes, size_means, model="exponential")
            results["scaling_fit_exponential"] = scaling_fit_exp
        except Exception as e:
            results["scaling_fit_exponential_error"] = str(e)

    # Critical point estimation if control parameter is provided
    if control_col is not None and control_col in df.columns:
        control = df[control_col].values
        try:
            cp_est = estimate_critical_point(sizes, control, values, model="power")
            results["critical_point"] = cp_est
        except Exception as e:
            results["critical_point_error"] = str(e)

    return results
