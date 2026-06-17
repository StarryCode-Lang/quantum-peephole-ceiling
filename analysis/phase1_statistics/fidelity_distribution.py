"""Fidelity distribution analysis for quantum circuit optimization experiments.

Provides full distributional summaries, outlier detection, and breakdowns
by circuit family for publication-quality reporting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Sequence


def fidelity_summary(results_df: pd.DataFrame, fidelity_col: str = "fidelity") -> Dict[str, Any]:
    """Generate a full fidelity distribution summary.

    Parameters
    ----------
    results_df : pandas.DataFrame
        DataFrame containing fidelity values.
    fidelity_col : str, default 'fidelity'
        Name of the column holding fidelity values.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'n': number of observations
        - 'min', 'q1', 'median', 'q3', 'max': five-number summary
        - 'mean', 'std': mean and standard deviation
        - 'iqr': inter-quartile range
        - 'skewness', 'kurtosis': moment-based shape statistics
        - 'missing': number of missing values

    Raises
    ------
    ValueError
        If fidelity_col is missing from the DataFrame.
    """
    if fidelity_col not in results_df.columns:
        raise ValueError(f"Column '{fidelity_col}' not found in DataFrame.")

    fid = results_df[fidelity_col].dropna().astype(float)
    n = len(fid)
    if n == 0:
        return {
            "n": 0,
            "min": np.nan,
            "q1": np.nan,
            "median": np.nan,
            "q3": np.nan,
            "max": np.nan,
            "mean": np.nan,
            "std": np.nan,
            "iqr": np.nan,
            "skewness": np.nan,
            "kurtosis": np.nan,
            "missing": int(results_df[fidelity_col].isna().sum()),
        }

    q1 = float(fid.quantile(0.25))
    q3 = float(fid.quantile(0.75))
    iqr = q3 - q1

    summary = {
        "n": n,
        "min": float(fid.min()),
        "q1": q1,
        "median": float(fid.median()),
        "q3": q3,
        "max": float(fid.max()),
        "mean": float(fid.mean()),
        "std": float(fid.std(ddof=1)),
        "iqr": iqr,
        "skewness": float(fid.skew()),
        "kurtosis": float(fid.kurtosis()),
        "missing": int(results_df[fidelity_col].isna().sum()),
    }

    return summary


def fidelity_outliers(
    results_df: pd.DataFrame,
    fidelity_col: str = "fidelity",
    threshold: float = 0.99,
    method: str = "iqr",
) -> Dict[str, Any]:
    """Identify fidelity outliers using IQR or absolute threshold methods.

    Parameters
    ----------
    results_df : pandas.DataFrame
        DataFrame containing fidelity values.
    fidelity_col : str, default 'fidelity'
        Name of the column holding fidelity values.
    threshold : float, default 0.99
        For ``method='absolute'``, values below this are flagged.
        For ``method='iqr'``, the IQR multiplier (default 1.5).
    method : {'iqr', 'absolute'}, default 'iqr'
        Outlier detection rule.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'n_outliers': number of outliers
        - 'outlier_fraction': fraction of outliers
        - 'outlier_indices': list of row indices (if available)
        - 'outlier_values': list of outlier fidelity values
        - 'threshold_description': human-readable threshold description
        - 'lower_bound', 'upper_bound': bounds used

    Raises
    ------
    ValueError
        If fidelity_col is missing or method is invalid.
    """
    if fidelity_col not in results_df.columns:
        raise ValueError(f"Column '{fidelity_col}' not found in DataFrame.")

    fid = results_df[fidelity_col].dropna().astype(float)
    n = len(fid)
    if n == 0:
        return {
            "n_outliers": 0,
            "outlier_fraction": 0.0,
            "outlier_indices": [],
            "outlier_values": [],
            "threshold_description": "No data",
            "lower_bound": np.nan,
            "upper_bound": np.nan,
        }

    if method == "iqr":
        q1 = float(fid.quantile(0.25))
        q3 = float(fid.quantile(0.75))
        iqr = q3 - q1
        multiplier = threshold if threshold > 0 else 1.5
        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr
        mask = (fid < lower) | (fid > upper)
        desc = f"IQR method (multiplier={multiplier:.2f})"
    elif method == "absolute":
        lower = -np.inf
        upper = threshold
        mask = fid < threshold
        desc = f"Absolute threshold (< {threshold})"
    else:
        raise ValueError("method must be 'iqr' or 'absolute'.")

    outlier_vals = fid[mask].tolist()
    outlier_idx = fid[mask].index.tolist()

    return {
        "n_outliers": int(mask.sum()),
        "outlier_fraction": float(mask.sum() / n),
        "outlier_indices": outlier_idx,
        "outlier_values": outlier_vals,
        "threshold_description": desc,
        "lower_bound": lower,
        "upper_bound": upper,
    }


def fidelity_by_circuit_family(
    results_df: pd.DataFrame,
    fidelity_col: str = "fidelity",
    family_col: Optional[str] = None,
) -> Dict[str, Any]:
    """Break down fidelity distribution by circuit family or experiment.

    Parameters
    ----------
    results_df : pandas.DataFrame
        DataFrame containing fidelity values.
    fidelity_col : str, default 'fidelity'
        Name of the column holding fidelity values.
    family_col : str or None, default None
        Column to group by. If None, attempts to infer from common
        column names: 'circuit_name', 'optimizer', 'experiment', 'n_qubits'.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'by_family': dict mapping family name -> fidelity_summary dict
        - 'family_col': column used for grouping
        - 'n_families': number of families
        - 'overall': fidelity_summary on the whole DataFrame

    Raises
    ------
    ValueError
        If no suitable family column can be found.
    """
    if fidelity_col not in results_df.columns:
        raise ValueError(f"Column '{fidelity_col}' not found in DataFrame.")

    if family_col is None:
        candidates = ["circuit_name", "optimizer", "experiment", "n_qubits", "depth"]
        for col in candidates:
            if col in results_df.columns:
                family_col = col
                break
        if family_col is None:
            raise ValueError(
                "No family column found. Please specify family_col explicitly."
            )

    if family_col not in results_df.columns:
        raise ValueError(f"Column '{family_col}' not found in DataFrame.")

    by_family = {}
    for name, group in results_df.groupby(family_col):
        by_family[str(name)] = fidelity_summary(group, fidelity_col)

    return {
        "by_family": by_family,
        "family_col": family_col,
        "n_families": len(by_family),
        "overall": fidelity_summary(results_df, fidelity_col),
    }
