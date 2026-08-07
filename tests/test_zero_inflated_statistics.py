"""Tests for zero-inflated reduction summaries."""

import numpy as np
import pytest

from analysis.phase1_statistics.zero_inflated import (
    compare_zero_inflated,
    summarize_zero_inflated,
)


def test_summary_reports_zero_mass_and_conditional_nonzero_distribution():
    result = summarize_zero_inflated([0.0, 0.0, 0.2, 0.4, np.nan])

    assert result["n"] == 4
    assert result["zero_count"] == 2
    assert result["zero_rate"] == pytest.approx(0.5)
    assert result["nonzero_count"] == 2
    assert result["conditional_nonzero_mean"] == pytest.approx(0.3)
    assert result["conditional_nonzero_median"] == pytest.approx(0.3)


def test_comparison_separates_zero_rate_from_nonzero_effect():
    result = compare_zero_inflated([0.0, 0.4, 0.6], [0.0, 0.1, 0.2])

    assert result["zero_rate_difference"] == pytest.approx(0.0)
    assert result["conditional_nonzero_mean_difference"] == pytest.approx(0.35)
    assert result["conditional_nonzero_cliffs_delta"] == pytest.approx(1.0)


def test_summary_rejects_all_missing_values():
    with pytest.raises(ValueError, match="finite"):
        summarize_zero_inflated([np.nan, np.inf])
