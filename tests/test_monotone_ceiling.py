"""Tests for the mechanism-derived monotone ceiling analysis."""

import numpy as np

from analysis.monotone_ceiling_p7 import phase1_lower_bound


def test_phase1_lower_bound_is_clipped_and_monotone():
    result = phase1_lower_bound(np.array([0.0, 0.2, 0.6]))

    np.testing.assert_allclose(result, [0.0, 0.4, 1.0])
    assert np.all(np.diff(result) >= 0)


def test_phase1_lower_bound_rejects_negative_density():
    result = phase1_lower_bound(np.array([-0.2, 0.0, 0.5]))

    np.testing.assert_allclose(result, [0.0, 0.0, 1.0])
