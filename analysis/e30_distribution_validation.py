"""Distribution-level diagnostics for E30 Theorem 1(a) counts.

E30's primary release check compares cell means with the corrected expectation.
This module adds a discrete goodness-of-fit diagnostic for the aggregate
``a_adj_raw`` count. It does not test wire-level independence because E30 does
not retain per-wire pair indicators.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import chisquare, poisson

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = PROJECT_ROOT / "data" / "v10" / "e30" / "e30_thm1a_wcl_results.csv"
SUMMARY_CSV = PROJECT_ROOT / "data" / "v10" / "e30" / "derived" / "e30_thm1a_cell_summary.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "v10" / "e30" / "derived"


def poisson_gof(
    counts: np.ndarray | pd.Series,
    *,
    mean: float,
    min_expected: float = 5.0,
) -> dict[str, Any]:
    """Run a grouped Pearson chi-square diagnostic against Poisson(mean).

    Sparse upper-tail categories are merged with their lower neighbour until
    expected frequencies meet ``min_expected``. The theoretical mean is fixed,
    so this is a diagnostic goodness-of-fit p-value, not a fitted-model test.
    """
    values = np.asarray(counts, dtype=float)
    if values.size == 0:
        raise ValueError("counts must not be empty")
    if not np.all(np.isfinite(values)) or np.any(values < 0) or np.any(values % 1):
        raise ValueError("counts must be finite non-negative integers")
    if min_expected <= 0:
        raise ValueError("min_expected must be positive")

    values = values.astype(int)
    n = int(values.size)
    if mean <= 0:
        return {
            "n": n,
            "observed_total": n,
            "expected_total": n,
            "n_bins": 1,
            "p_value": None,
            "reason": "zero_theoretical_mean",
        }

    max_count = int(values.max())
    observed = np.bincount(values, minlength=max_count + 1).astype(float)
    support = np.arange(max_count + 1)
    expected = n * poisson.pmf(support, mean)
    observed = np.append(observed, 0.0)
    expected = np.append(expected, n * poisson.sf(max_count, mean))

    # Merge sparse bins while retaining a valid chi-square approximation.
    while len(expected) > 1 and np.any(expected < min_expected):
        idx = int(np.where(expected < min_expected)[0][-1])
        neighbour = idx + 1 if idx == 0 else idx - 1
        expected[neighbour] += expected[idx]
        observed[neighbour] += observed[idx]
        expected = np.delete(expected, idx)
        observed = np.delete(observed, idx)

    if len(expected) < 2:
        return {
            "n": n,
            "observed_total": n,
            "expected_total": n,
            "n_bins": int(len(expected)),
            "p_value": None,
            "reason": "insufficient_expected_bins",
        }

    expected *= observed.sum() / expected.sum()
    statistic, p_value = chisquare(observed, expected)
    return {
        "n": n,
        "observed_total": int(observed.sum()),
        "expected_total": int(round(expected.sum())),
        "n_bins": int(len(expected)),
        "chi2_statistic": float(statistic),
        "degrees_of_freedom": int(len(expected) - 1),
        "p_value": float(p_value),
        "reason": None,
    }


def benjamini_hochberg_adjust(p_values: pd.Series) -> pd.Series:
    """Adjust finite p-values with the BH step-up procedure."""
    values = p_values.to_numpy(dtype=float)
    valid = np.isfinite(values)
    adjusted = np.full(values.shape, np.nan, dtype=float)
    if not valid.any():
        return pd.Series(adjusted, index=p_values.index)
    raw = values[valid]
    order = np.argsort(raw)
    ranked = raw[order]
    m = len(ranked)
    corrected = np.minimum.accumulate((ranked * m / np.arange(1, m + 1))[::-1])[::-1]
    corrected = np.clip(corrected, 0.0, 1.0)
    restored = np.empty_like(corrected)
    restored[order] = corrected
    adjusted[valid] = restored
    return pd.Series(adjusted, index=p_values.index)


def validate_e30_distribution() -> pd.DataFrame:
    """Return one Poisson diagnostic row per E30 parameter cell."""
    raw = pd.read_csv(RAW_CSV)
    theory = pd.read_csv(SUMMARY_CSV)
    keys = ["n_qubits", "depth", "rho"]
    rows: list[dict[str, Any]] = []
    for key, group in raw.groupby(keys, sort=True):
        mask = np.ones(len(theory), dtype=bool)
        for name, value in zip(keys, key):
            mask &= np.isclose(theory[name].to_numpy(dtype=float), float(value))
        matched = theory.loc[mask]
        if len(matched) != 1:
            raise ValueError(f"expected one theory row for cell {key}, got {len(matched)}")
        result = poisson_gof(group["a_adj_raw"], mean=float(matched.iloc[0]["theory_a_adj"]))
        rows.append({**dict(zip(keys, key)), "theory_a_adj": float(matched.iloc[0]["theory_a_adj"]), **result})

    result = pd.DataFrame(rows)
    result["p_value_bh"] = benjamini_hochberg_adjust(result["p_value"])
    result["reject_bh_0_05"] = result["p_value_bh"].lt(0.05).fillna(False)
    return result


def main() -> int:
    result = validate_e30_distribution()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_DIR / "e30_distribution_validation.csv", index=False)
    summary = {
        "n_cells": int(len(result)),
        "n_testable": int(result["p_value"].notna().sum()),
        "n_rejected_bh_0_05": int(result["reject_bh_0_05"].sum()),
        "median_p_value": float(result["p_value"].median()),
        "wire_level_independence_tested": False,
        "wire_level_independence_note": "E30 stores aggregate pair counts only; per-wire indicators are not available.",
    }
    (OUTPUT_DIR / "e30_distribution_validation.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(result.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
