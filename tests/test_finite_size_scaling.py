"""Scientific-contract tests for finite-size scaling helpers."""

import numpy as np
import pytest

from analysis.finite_size_scaling import (
    binder_cumulant,
    estimate_asymptotic_value,
    estimate_critical_point,
    scaling_collapse,
)


def test_zero_order_parameter_has_undefined_binder_cumulant():
    result = binder_cumulant([0.0, 0.0, 0.0, 0.0])
    assert np.isnan(result["cumulant"])
    assert not result["informative"]
    assert result["status"] == "undefined_zero_second_moment"


def test_nonstandard_second_order_formula_is_rejected():
    with pytest.raises(ValueError, match="fourth-order"):
        binder_cumulant([1.0, 2.0, 3.0], order=2)


def test_asymptotic_bootstrap_preserves_all_system_sizes():
    sizes = np.repeat([4, 6, 8, 10], 8)
    rng = np.random.default_rng(4)
    values = np.concatenate([
        0.2 + 0.8 * np.exp(-0.3 * size) + rng.normal(0, 0.002, 8)
        for size in [4, 6, 8, 10]
    ])
    result = estimate_asymptotic_value(
        sizes, values, model="exponential", n_bootstrap=100, random_seed=9
    )
    assert result["n_sizes"] == 4
    assert result["bootstrap_design"] == "resample_within_system_size"
    assert result["estimand"] == "infinite_size_asymptotic_value"


def test_critical_point_wrapper_discloses_true_estimand():
    sizes = np.repeat([3, 4, 5], 4)
    values = 1.0 / sizes
    control = np.tile(np.arange(4), 3)
    with pytest.deprecated_call():
        result = estimate_critical_point(
            sizes, control, values, n_bootstrap=20, random_seed=2
        )
    assert result["estimand"] == "asymptotic_value_not_critical_point"


def test_scaling_collapse_uses_leave_one_size_out_validation():
    sizes = np.repeat([4, 6, 8], 4)
    control = np.tile([0.1, 0.2, 0.3, 0.4], 3)
    values = 0.5 * np.abs(control - 0.25) * sizes
    result = scaling_collapse(control, values, sizes, 0.25, nu=1.0, beta=1.0)
    assert result["validation"] == "leave_one_size_out"
    assert result["r_squared"] is not None
