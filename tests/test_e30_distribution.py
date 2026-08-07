"""Tests for E30 count-distribution diagnostics."""

import numpy as np

from analysis.e30_distribution_validation import poisson_gof


def test_poisson_gof_returns_grouped_counts_and_valid_p_value():
    rng = np.random.RandomState(7)
    counts = rng.poisson(3.0, size=500)

    result = poisson_gof(counts, mean=3.0)

    assert result["n"] == 500
    assert result["observed_total"] == 500
    assert result["expected_total"] == 500
    assert result["n_bins"] >= 2
    assert 0.0 <= result["p_value"] <= 1.0


def test_poisson_gof_handles_a_degenerate_count_sample():
    result = poisson_gof(np.zeros(20, dtype=int), mean=0.0)

    assert result["p_value"] is None
    assert result["reason"] == "zero_theoretical_mean"
