"""
Comprehensive Unit Tests for Statistical Analysis Functions
============================================================
Tests for:
  - Benjamini-Hochberg FDR  (analysis.phase1_statistics.multiple_comparison)
  - Bootstrap CI            (analysis.phase1_statistics.bootstrap)
  - Effect sizes            (analysis.phase1_statistics.effect_size)
  - Core statistics         (analysis.phase1_statistics.core)

Self-contained and runnable with:  python tests/test_statistical_analysis.py
No pytest dependency -- uses plain assert + print pass/fail.
"""

import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Make project root importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Imports from the standalone submodules
from analysis.phase1_statistics.multiple_comparison import (
    benjamini_hochberg as bh_fdr,
)
from analysis.phase1_statistics.bootstrap import (
    bootstrap_ci as boot_ci_mod,
    bootstrap_convergence as boot_conv_mod,
)
from analysis.phase1_statistics.effect_size import (
    cliffs_delta as cliffs_delta_mod,
    cohens_d as cohens_d_mod,
    interpret_effect_size as interpret_mod,
)

# Imports from the legacy core module (different signatures / return types)
from analysis.phase1_statistics.core import (
    cliffs_delta as cliffs_delta_core,
    cohens_d as cohens_d_core,
    fidelity_summary,
    threshold_sensitivity,
)
from analysis.phase1_statistics.core import (
    calculate_power as calculate_power_core,
)

# Imports from the standalone power_analysis module
from analysis.phase1_statistics.power_analysis import (
    calculate_power as calc_power_mod,
)


# ===================================================================
# Test runner
# ===================================================================

_results: list = []


def _run(test_fn):
    """Execute *test_fn* and record PASS / FAIL."""
    name = test_fn.__name__
    try:
        test_fn()
        _results.append((name, True, ""))
        print(f"  [PASS] {name}")
    except Exception as exc:
        tb = traceback.format_exc()
        _results.append((name, False, str(exc)))
        print(f"  [FAIL] {name}: {exc}")
        # Print the full traceback indented for easier debugging
        for line in tb.splitlines():
            print(f"         {line}")


def _report():
    """Print a summary table and exit with appropriate code."""
    n_pass = sum(1 for _, ok, _ in _results if ok)
    n_fail = sum(1 for _, ok, _ in _results if not ok)
    total = n_pass + n_fail

    print()
    print("=" * 60)
    print(f"  Results: {n_pass}/{total} passed, {n_fail} failed")
    print("=" * 60)

    if n_fail:
        print("\nFailed tests:")
        for name, ok, msg in _results:
            if not ok:
                print(f"  - {name}: {msg}")
        sys.exit(1)
    else:
        print("\nAll tests passed.")
        sys.exit(0)


# ===================================================================
# 1. Benjamini-Hochberg FDR  (multiple_comparison.py)
# ===================================================================

def test_bh_known_rejections():
    """With five known p-values, only the smallest should be rejected at alpha=0.05."""
    p_vals = [0.01, 0.03, 0.10, 0.50, 0.90]
    result = bh_fdr(p_vals, alpha=0.05)

    assert result["n_tests"] == 5, f"Expected n_tests=5, got {result['n_tests']}"
    assert result["alpha"] == 0.05, f"Expected alpha=0.05, got {result['alpha']}"
    assert result["method"] == "Benjamini-Hochberg"

    rejected = result["rejected"]
    assert rejected[0], "p=0.01 should be rejected"
    assert not rejected[2], "p=0.10 should not be rejected"
    assert not rejected[3], "p=0.50 should not be rejected"
    assert not rejected[4], "p=0.90 should not be rejected"


def test_bh_rejection_count_consistent():
    """n_rejected field must agree with sum of rejected boolean array."""
    p_vals = [0.001, 0.01, 0.02, 0.04, 0.10, 0.50]
    result = bh_fdr(p_vals, alpha=0.05)
    assert result["n_rejected"] == int(np.sum(result["rejected"]))


def test_bh_all_significant():
    """When all p-values are very small, all should be rejected."""
    p_vals = [0.001, 0.005, 0.01]
    result = bh_fdr(p_vals, alpha=0.05)
    assert np.all(result["rejected"]), (
        f"Expected all rejected, got {result['rejected']}"
    )


def test_bh_none_significant():
    """When all p-values are large, none should be rejected."""
    p_vals = [0.50, 0.80, 0.90]
    result = bh_fdr(p_vals, alpha=0.05)
    assert not np.any(result["rejected"]), (
        f"Expected none rejected, got {result['rejected']}"
    )


def test_bh_single_pvalue_significant():
    """Single small p-value should be rejected."""
    result = bh_fdr([0.01], alpha=0.05)
    assert result["rejected"][0], "Single p=0.01 should be rejected"
    assert result["n_tests"] == 1


def test_bh_single_pvalue_not_significant():
    """Single large p-value should not be rejected."""
    result = bh_fdr([0.50], alpha=0.05)
    assert not result["rejected"][0], "Single p=0.50 should not be rejected"


def test_bh_adjusted_p_monotone():
    """Adjusted p-values must be monotone non-decreasing w.r.t. raw p-value rank."""
    p_vals = [0.001, 0.01, 0.03, 0.10, 0.50]
    result = bh_fdr(p_vals)
    adj = result["adjusted_p"]

    # p_vals are already sorted ascending, so adjusted_p must be non-decreasing
    for i in range(len(adj) - 1):
        assert adj[i] <= adj[i + 1] + 1e-12, (
            f"Adjusted p not monotone at index {i}: "
            f"adj[{i}]={adj[i]:.6f} > adj[{i+1}]={adj[i+1]:.6f}"
        )


def test_bh_adjusted_p_bounded_by_one():
    """No adjusted p-value may exceed 1.0."""
    p_vals = [0.10, 0.50, 0.80, 0.95, 1.0]
    result = bh_fdr(p_vals)
    assert np.all(result["adjusted_p"] <= 1.0 + 1e-12), (
        f"Some adjusted p-values exceed 1.0: {result['adjusted_p']}"
    )


def test_bh_adjusted_geq_raw():
    """Adjusted p-values should be >= the corresponding raw p-values."""
    p_vals = [0.01, 0.03, 0.10, 0.50]
    result = bh_fdr(p_vals)
    for raw, adj in zip(p_vals, result["adjusted_p"]):
        assert adj >= raw - 1e-12, (
            f"Adjusted p ({adj:.6f}) < raw p ({raw})"
        )


def test_bh_empty_raises_valueerror():
    """Empty p-values sequence must raise ValueError."""
    try:
        bh_fdr([], alpha=0.05)
        assert False, "Should have raised ValueError for empty p-values"
    except ValueError:
        pass


def test_bh_invalid_pvalue_raises():
    """p-values outside [0, 1] must raise ValueError."""
    for bad in [[-0.1], [1.5], [0.5, -0.01]]:
        try:
            bh_fdr(bad)
            assert False, f"Should have raised ValueError for p_values={bad}"
        except ValueError:
            pass


def test_bh_invalid_alpha_raises():
    """alpha outside (0, 1] must raise ValueError."""
    for bad_alpha in [0.0, -0.1, 1.5]:
        try:
            bh_fdr([0.05], alpha=bad_alpha)
            assert False, f"Should have raised ValueError for alpha={bad_alpha}"
        except ValueError:
            pass


# ===================================================================
# 2. Bootstrap CI  (bootstrap.py)
# ===================================================================

def test_bootstrap_normal_contains_mean():
    """95% CI from normal data should contain the sample mean."""
    rng = np.random.default_rng(123)
    data = rng.normal(loc=10.0, scale=2.0, size=200)
    result = boot_ci_mod(data, n_bootstrap=5000, random_seed=42)

    assert result["ci_lower"] <= result["estimate"] <= result["ci_upper"], (
        f"CI [{result['ci_lower']:.4f}, {result['ci_upper']:.4f}] "
        f"does not contain estimate {result['estimate']:.4f}"
    )


def test_bootstrap_normal_ci_brackets_mean():
    """For normal data centred at mu, CI should bracket mu."""
    rng = np.random.default_rng(999)
    mu = 5.0
    data = rng.normal(loc=mu, scale=1.0, size=500)
    result = boot_ci_mod(data, n_bootstrap=5000, random_seed=42)
    assert result["ci_lower"] < mu < result["ci_upper"], (
        f"CI [{result['ci_lower']:.4f}, {result['ci_upper']:.4f}] "
        f"does not bracket true mean {mu}"
    )


def test_bootstrap_constant_data_zero_width():
    """Constant data should yield a zero-width CI."""
    data = np.full(100, 7.0)
    # n_bootstrap must be >= 1000 because bootstrap_ci internally calls
    # bootstrap_convergence whose geometric series starts at 1000.
    result = boot_ci_mod(data, n_bootstrap=1000, random_seed=42)

    assert result["estimate"] == 7.0, (
        f"Estimate should be 7.0, got {result['estimate']}"
    )
    width = result["ci_upper"] - result["ci_lower"]
    assert abs(width) < 1e-10, (
        f"CI width should be zero for constant data, got {width}"
    )
    assert result["std_error"] < 1e-10, (
        f"Std error should be ~0 for constant data, got {result['std_error']}"
    )


def test_bootstrap_reproducibility():
    """Identical seeds must produce identical results."""
    data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    r1 = boot_ci_mod(data, n_bootstrap=1000, random_seed=42)
    r2 = boot_ci_mod(data, n_bootstrap=1000, random_seed=42)

    assert r1["estimate"] == r2["estimate"], "Estimates differ"
    assert r1["ci_lower"] == r2["ci_lower"], (
        f"ci_lower differs: {r1['ci_lower']} vs {r2['ci_lower']}"
    )
    assert r1["ci_upper"] == r2["ci_upper"], (
        f"ci_upper differs: {r1['ci_upper']} vs {r2['ci_upper']}"
    )
    assert r1["std_error"] == r2["std_error"], "Std errors differ"


def test_bootstrap_different_seeds_differ():
    """Different seeds should generally produce slightly different CIs."""
    data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    r1 = boot_ci_mod(data, n_bootstrap=1000, random_seed=42)
    r2 = boot_ci_mod(data, n_bootstrap=1000, random_seed=99)

    # Estimates are the same (point estimate on original data), but CIs differ
    assert r1["estimate"] == r2["estimate"]
    # At least one of ci_lower or ci_upper should differ
    ci_differs = (
        abs(r1["ci_lower"] - r2["ci_lower"]) > 1e-12
        or abs(r1["ci_upper"] - r2["ci_upper"]) > 1e-12
    )
    assert ci_differs, "CIs should differ for different seeds"


def test_bootstrap_empty_raises_valueerror():
    """Empty data must raise ValueError."""
    try:
        boot_ci_mod([], n_bootstrap=1000, random_seed=42)
        assert False, "Should have raised ValueError for empty data"
    except ValueError:
        pass


def test_bootstrap_n_bootstrap_too_small_raises():
    """n_bootstrap < 100 must raise ValueError."""
    try:
        boot_ci_mod([1.0, 2.0, 3.0], n_bootstrap=50, random_seed=42)
        assert False, "Should have raised ValueError for n_bootstrap=50"
    except ValueError:
        pass


def test_bootstrap_invalid_ci_raises():
    """ci outside (0, 100) must raise ValueError."""
    data = [1.0, 2.0, 3.0]
    for bad_ci in [0, 100, -5, 110]:
        try:
            boot_ci_mod(data, ci=bad_ci, n_bootstrap=200, random_seed=42)
            assert False, f"Should have raised ValueError for ci={bad_ci}"
        except ValueError:
            pass


def test_bootstrap_convergence_check():
    """Convergence check should return a well-formed result dict."""
    rng = np.random.default_rng(77)
    data = rng.normal(loc=5.0, scale=1.0, size=100)
    conv = boot_conv_mod(data, max_bootstrap=2000, random_seed=42)

    assert "converged" in conv, "Missing 'converged' key"
    assert "widths" in conv, "Missing 'widths' key"
    assert "tolerance" in conv, "Missing 'tolerance' key"
    assert "note" in conv, "Missing 'note' key"
    assert isinstance(conv["converged"], bool)
    assert isinstance(conv["widths"], dict)
    assert len(conv["widths"]) > 0, "Widths dict should be non-empty"
    assert conv["tolerance"] == 0.01  # default


def test_bootstrap_convergence_constant_data():
    """Constant data should converge trivially (zero width everywhere)."""
    data = np.full(50, 3.0)
    conv = boot_conv_mod(data, max_bootstrap=1000, random_seed=42)
    assert conv["converged"], (
        f"Constant data should converge trivially. Note: {conv['note']}"
    )
    for n_boot, width in conv["widths"].items():
        assert abs(width) < 1e-10, (
            f"Width at n_bootstrap={n_boot} should be ~0, got {width}"
        )


def test_bootstrap_ci_level_stored():
    """The requested CI level should appear in the result."""
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    result = boot_ci_mod(data, ci=90, n_bootstrap=1000, random_seed=42)
    assert result["ci_level"] == 90


# ===================================================================
# 3. Effect sizes  (effect_size.py)
# ===================================================================

def test_cliffs_delta_identical_distributions():
    """Identical samples should yield delta near 0."""
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = cliffs_delta_mod(x, y)

    assert abs(result["delta"]) < 1e-10, (
        f"Cliff's delta should be ~0 for identical samples, got {result['delta']}"
    )
    assert result["magnitude"] == "negligible"
    assert result["n1"] == 5
    assert result["n2"] == 5


def test_cliffs_delta_clearly_different():
    """Non-overlapping samples should yield |delta| = 1."""
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
    result = cliffs_delta_mod(x, y)

    # Every x_i < every y_j => sign(x_i - y_j) = -1 for all pairs
    assert abs(result["delta"] - (-1.0)) < 1e-10, (
        f"Expected delta=-1.0 for completely dominated x, got {result['delta']}"
    )
    assert result["magnitude"] == "large"


def test_cliffs_delta_reversed():
    """Swapping x and y should negate the delta."""
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([5.0, 6.0, 7.0])
    r_xy = cliffs_delta_mod(x, y)
    r_yx = cliffs_delta_mod(y, x)

    assert abs(r_xy["delta"] + r_yx["delta"]) < 1e-10, (
        f"delta(x,y)={r_xy['delta']} should be -delta(y,x)={-r_yx['delta']}"
    )


def test_cliffs_delta_ci_bounds_valid():
    """CI bounds should be within [-1, 1] and properly ordered."""
    x = np.array([1.0, 3.0, 5.0, 7.0, 9.0])
    y = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
    result = cliffs_delta_mod(x, y)

    assert -1.0 <= result["ci_lower"] <= 1.0
    assert -1.0 <= result["ci_upper"] <= 1.0
    assert result["ci_lower"] <= result["ci_upper"]


def test_cohens_d_known_values():
    """Verify Cohen's d with manually computed values."""
    x = np.array([10.0, 12.0, 14.0, 16.0, 18.0])
    y = np.array([5.0, 7.0, 9.0, 11.0, 13.0])
    result = cohens_d_mod(x, y)

    # mean_x=14, mean_y=9, diff=5
    # var_x = var_y = 10 (ddof=1)
    # pooled_var = ((4*10)+(4*10))/(5+5-2) = 80/8 = 10
    # pooled_sd = sqrt(10) ~ 3.1623
    # d = 5 / sqrt(10) ~ 1.5811
    expected_d = 5.0 / np.sqrt(10.0)
    assert abs(result["d"] - expected_d) < 0.01, (
        f"Expected Cohen's d ~ {expected_d:.4f}, got {result['d']:.4f}"
    )
    assert result["magnitude"] == "large"
    assert result["n1"] == 5
    assert result["n2"] == 5
    assert abs(result["pooled_sd"] - np.sqrt(10.0)) < 0.01


def test_cohens_d_zero_effect():
    """Identical means should yield d=0."""
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = cohens_d_mod(x, y)
    assert abs(result["d"]) < 1e-10, f"Expected d=0, got {result['d']}"


def test_cohens_d_ci_brackets_estimate():
    """CI should bracket Hedges' g."""
    x = np.array([10.0, 12.0, 14.0, 16.0, 18.0])
    y = np.array([5.0, 7.0, 9.0, 11.0, 13.0])
    result = cohens_d_mod(x, y)
    assert result["ci_lower"] < result["g"] < result["ci_upper"], (
        f"CI [{result['ci_lower']:.4f}, {result['ci_upper']:.4f}] "
        f"does not bracket g={result['g']:.4f}"
    )


def test_hedges_g_correction_factor():
    """Hedges' g should be slightly smaller in magnitude than Cohen's d."""
    x = np.array([10.0, 12.0, 14.0, 16.0, 18.0])
    y = np.array([5.0, 7.0, 9.0, 11.0, 13.0])
    result = cohens_d_mod(x, y)

    d = result["d"]
    g = result["g"]

    # J = 1 - 3/(4*df - 1), df = n1+n2-2 = 8
    # J = 1 - 3/31 ~ 0.9032
    df = 5 + 5 - 2
    expected_j = 1.0 - 3.0 / (4.0 * df - 1.0)
    expected_g = d * expected_j

    assert abs(g - expected_g) < 1e-10, (
        f"Expected g={expected_g:.6f}, got {g:.6f}"
    )
    assert abs(g) < abs(d), "Hedges' g should be smaller than Cohen's d"


def test_hedges_g_larger_samples():
    """With larger samples, J approaches 1 so g approaches d."""
    rng = np.random.default_rng(55)
    x = rng.normal(10, 2, size=200)
    y = rng.normal(8, 2, size=200)
    result = cohens_d_mod(x, y)

    # With n1=n2=200, df=398, J ~ 1 - 3/1591 ~ 0.9981
    # g and d should be very close
    ratio = abs(result["g"] / result["d"]) if result["d"] != 0 else 1.0
    assert 0.99 < ratio < 1.01, (
        f"g/d ratio={ratio:.6f} should be close to 1 for large samples"
    )


def test_effect_size_magnitude_thresholds():
    """Verify interpretation thresholds match conventional cut-offs."""
    assert interpret_mod(0.0) == "negligible"
    assert interpret_mod(0.1) == "negligible"
    assert interpret_mod(0.19) == "negligible"

    assert interpret_mod(0.2) == "small"
    assert interpret_mod(0.35) == "small"
    assert interpret_mod(0.49) == "small"

    assert interpret_mod(0.5) == "medium"
    assert interpret_mod(0.65) == "medium"
    assert interpret_mod(0.79) == "medium"

    assert interpret_mod(0.8) == "large"
    assert interpret_mod(1.0) == "large"
    assert interpret_mod(2.0) == "large"

    # Negative values should use absolute magnitude
    assert interpret_mod(-0.1) == "negligible"
    assert interpret_mod(-0.3) == "small"
    assert interpret_mod(-0.6) == "medium"
    assert interpret_mod(-1.0) == "large"


def test_effect_size_empty_x_raises():
    """Empty x must raise ValueError."""
    try:
        cliffs_delta_mod([], [1.0, 2.0])
        assert False, "Should have raised ValueError for empty x"
    except ValueError:
        pass


def test_effect_size_empty_y_raises():
    """Empty y must raise ValueError."""
    try:
        cliffs_delta_mod([1.0, 2.0], [])
        assert False, "Should have raised ValueError for empty y"
    except ValueError:
        pass


def test_cohens_d_empty_raises():
    """Empty samples must raise ValueError for Cohen's d."""
    try:
        cohens_d_mod([], [1.0, 2.0])
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_cohens_d_zero_variance_raises():
    """Zero pooled variance must raise ValueError."""
    try:
        cohens_d_mod([5.0, 5.0, 5.0], [5.0, 5.0, 5.0])
        assert False, "Should have raised ValueError for zero variance"
    except ValueError:
        pass


# ===================================================================
# 4. Core statistics  (core.py)
# ===================================================================

def test_core_cliffs_delta_basic():
    """core.cliffs_delta returns (delta, ci_low, ci_high) tuple."""
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
    result = cliffs_delta_core(x, y)

    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 3, f"Expected 3 elements, got {len(result)}"

    delta, ci_low, ci_high = result
    assert delta < 0, f"Expected negative delta (x < y), got {delta}"
    assert abs(delta - (-1.0)) < 1e-10, f"Expected delta=-1.0, got {delta}"
    assert ci_low <= delta <= ci_high or ci_low <= ci_high, (
        "CI bounds should be ordered"
    )


def test_core_cliffs_delta_identical():
    """core.cliffs_delta with identical data should give delta=0."""
    x = np.array([3.0, 3.0, 3.0, 3.0])
    y = np.array([3.0, 3.0, 3.0, 3.0])
    delta, _, _ = cliffs_delta_core(x, y)
    assert abs(delta) < 1e-10, f"Expected delta~0, got {delta}"


def test_core_cohens_d_basic():
    """core.cohens_d returns (d, ci_low, ci_high) tuple."""
    x = np.array([10.0, 12.0, 14.0, 16.0, 18.0])
    y = np.array([5.0, 7.0, 9.0, 11.0, 13.0])
    result = cohens_d_core(x, y)

    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 3

    d, ci_low, ci_high = result
    expected_d = 5.0 / np.sqrt(10.0)
    assert abs(d - expected_d) < 0.01, (
        f"Expected d~{expected_d:.4f}, got {d:.4f}"
    )
    assert ci_low < d < ci_high, (
        f"CI [{ci_low:.4f}, {ci_high:.4f}] should bracket d={d:.4f}"
    )


def test_core_cohens_d_zero_variance():
    """core.cohens_d returns (0, 0, 0) when pooled SD is zero."""
    x = np.array([5.0, 5.0, 5.0])
    y = np.array([5.0, 5.0, 5.0])
    d, ci_low, ci_high = cohens_d_core(x, y)
    assert d == 0.0 and ci_low == 0.0 and ci_high == 0.0


def test_fidelity_summary_basic():
    """fidelity_summary should compute correct distribution statistics."""
    df = pd.DataFrame({"fidelity": [0.95, 0.97, 0.99, 0.98, 0.96, 1.0, 0.94]})
    result = fidelity_summary(df)

    assert isinstance(result, pd.DataFrame)
    row = result.iloc[0]
    assert row["n"] == 7, f"Expected n=7, got {row['n']}"
    assert abs(row["mean"] - np.mean([0.95, 0.97, 0.99, 0.98, 0.96, 1.0, 0.94])) < 1e-10
    assert abs(row["min"] - 0.94) < 1e-10
    assert abs(row["max"] - 1.0) < 1e-10
    assert row["n_below_0_99"] == 5, (
        f"Expected 5 values below 0.99, got {row['n_below_0_99']}"
    )
    assert row["n_below_0_95"] == 1, (
        f"Expected 1 value below 0.95, got {row['n_below_0_95']}"
    )


def test_fidelity_summary_missing_column_raises():
    """Missing 'fidelity' column must raise ValueError."""
    df = pd.DataFrame({"value": [0.95, 0.97]})
    try:
        fidelity_summary(df)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_fidelity_summary_quantiles():
    """fidelity_summary should report correct quartiles."""
    vals = np.linspace(0.90, 1.0, 11)  # 0.90, 0.91, ..., 1.00
    df = pd.DataFrame({"fidelity": vals})
    result = fidelity_summary(df)
    row = result.iloc[0]

    assert abs(row["q25"] - np.quantile(vals, 0.25)) < 1e-10
    assert abs(row["median"] - np.median(vals)) < 1e-10
    assert abs(row["q75"] - np.quantile(vals, 0.75)) < 1e-10


def test_threshold_sensitivity_basic():
    """threshold_sensitivity should compute correct success rates."""
    df = pd.DataFrame({"reduction": [0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]})
    result = threshold_sensitivity(df, thresholds=[0.05, 0.10, 0.20])

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3, f"Expected 3 rows, got {len(result)}"

    row_05 = result[result["threshold"] == 0.05].iloc[0]
    # Values >= 0.05: 0.05, 0.10, 0.15, 0.20, 0.25, 0.30 => 6 of 7
    expected_rate = 6.0 / 7.0
    assert abs(row_05["success_rate"] - expected_rate) < 1e-10, (
        f"Expected success_rate={expected_rate:.4f}, got {row_05['success_rate']:.4f}"
    )
    assert row_05["n_success"] == 6
    assert row_05["n_total"] == 7


def test_threshold_sensitivity_default_thresholds():
    """Default thresholds should be [0.01, 0.05, 0.10, 0.20]."""
    df = pd.DataFrame({"reduction": [0.02, 0.05, 0.10, 0.15, 0.20]})
    result = threshold_sensitivity(df)
    assert len(result) == 4
    assert list(result["threshold"]) == [0.01, 0.05, 0.10, 0.20]


def test_threshold_sensitivity_missing_column_raises():
    """Missing 'reduction' column must raise ValueError."""
    df = pd.DataFrame({"value": [0.1, 0.2]})
    try:
        threshold_sensitivity(df)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_threshold_sensitivity_all_pass():
    """All values above threshold should give success_rate=1."""
    df = pd.DataFrame({"reduction": [0.50, 0.60, 0.70]})
    result = threshold_sensitivity(df, thresholds=[0.10])
    assert result.iloc[0]["success_rate"] == 1.0


def test_threshold_sensitivity_none_pass():
    """No values above threshold should give success_rate=0."""
    df = pd.DataFrame({"reduction": [0.001, 0.002, 0.003]})
    result = threshold_sensitivity(df, thresholds=[0.10])
    assert result.iloc[0]["success_rate"] == 0.0


def test_power_calculation_large_effect():
    """Large effect size with moderate n should give high power.

    Manually verified:
      d=1.5, n=20, alpha=0.05 (two-sample)
      se = sqrt(2/20) = sqrt(0.1) ~ 0.3162
      z_alpha = norm.ppf(0.975) ~ 1.96
      z_beta = 1.5/0.3162 - 1.96 ~ 2.778
      power = norm.cdf(2.778) ~ 0.9973
    """
    power = calculate_power_core(1.5, 20, alpha=0.05)
    assert 0.99 < power <= 1.0, (
        f"Expected power > 0.99 for d=1.5, n=20, got {power:.4f}"
    )


def test_power_calculation_tiny_effect():
    """Very small effect with small n should give near-zero power."""
    power = calculate_power_core(0.01, 5, alpha=0.05)
    assert power < 0.10, (
        f"Expected very low power for d=0.01, n=5, got {power:.4f}"
    )


def test_power_calculation_medium_effect():
    """Medium effect with moderate n -- power should be in a plausible range.

    d=0.5, n=64 (two-sample):
      se = sqrt(2/64) = 0.1768
      z_beta = 0.5/0.1768 - 1.96 ~ 0.864
      power ~ norm.cdf(0.864) ~ 0.806
    """
    power = calculate_power_core(0.5, 64, alpha=0.05)
    assert 0.50 < power < 0.98, (
        f"Expected power roughly 0.5-0.98 for d=0.5, n=64, got {power:.4f}"
    )


def test_power_calculation_monotone_in_n():
    """Power should increase with sample size."""
    d = 0.5
    powers = [calculate_power_core(d, n) for n in [10, 20, 50, 100, 200]]
    for i in range(len(powers) - 1):
        assert powers[i] <= powers[i + 1] + 1e-10, (
            f"Power not monotone: power(n={[10,20,50,100,200][i]})={powers[i]:.4f} "
            f"> power(n={[10,20,50,100,200][i+1]})={powers[i+1]:.4f}"
        )


def test_power_calculation_monotone_in_d():
    """Power should increase with effect size."""
    n = 30
    powers = [calculate_power_core(d, n) for d in [0.1, 0.3, 0.5, 0.8, 1.2]]
    for i in range(len(powers) - 1):
        assert powers[i] <= powers[i + 1] + 1e-10, (
            f"Power not monotone in d"
        )


# ===================================================================
# 5. Additional cross-module checks
# ===================================================================

def test_power_module_calculate_power():
    """The standalone power_analysis module should return a dict."""
    result = calc_power_mod(effect_size=0.8, n=50, alpha=0.05)
    assert isinstance(result, dict)
    assert "power" in result
    assert "beta" in result
    assert 0.0 <= result["power"] <= 1.0
    assert abs(result["power"] + result["beta"] - 1.0) < 1e-10


def test_power_module_invalid_n_raises():
    """n <= 1 should raise ValueError."""
    try:
        calc_power_mod(effect_size=0.5, n=1)
        assert False, "Should have raised ValueError for n=1"
    except ValueError:
        pass


def test_core_bh_returns_tuple():
    """core.benjamini_hochberg should return (rejected, adjusted_p) tuple."""
    from analysis.phase1_statistics.core import benjamini_hochberg as bh_core
    p = np.array([0.01, 0.04, 0.10, 0.50])
    result = bh_core(p, alpha=0.05)
    assert isinstance(result, tuple)
    assert len(result) == 2
    rejected, adjusted = result
    assert rejected.dtype == bool
    assert len(rejected) == len(p)
    assert len(adjusted) == len(p)


# ===================================================================
# Main entry point
# ===================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  Statistical Analysis Unit Tests")
    print("=" * 60)
    print()

    # ---- 1. Benjamini-Hochberg FDR ----
    print("--- Benjamini-Hochberg FDR (multiple_comparison) ---")
    _run(test_bh_known_rejections)
    _run(test_bh_rejection_count_consistent)
    _run(test_bh_all_significant)
    _run(test_bh_none_significant)
    _run(test_bh_single_pvalue_significant)
    _run(test_bh_single_pvalue_not_significant)
    _run(test_bh_adjusted_p_monotone)
    _run(test_bh_adjusted_p_bounded_by_one)
    _run(test_bh_adjusted_geq_raw)
    _run(test_bh_empty_raises_valueerror)
    _run(test_bh_invalid_pvalue_raises)
    _run(test_bh_invalid_alpha_raises)
    print()

    # ---- 2. Bootstrap CI ----
    print("--- Bootstrap CI (bootstrap) ---")
    _run(test_bootstrap_normal_contains_mean)
    _run(test_bootstrap_normal_ci_brackets_mean)
    _run(test_bootstrap_constant_data_zero_width)
    _run(test_bootstrap_reproducibility)
    _run(test_bootstrap_different_seeds_differ)
    _run(test_bootstrap_empty_raises_valueerror)
    _run(test_bootstrap_n_bootstrap_too_small_raises)
    _run(test_bootstrap_invalid_ci_raises)
    _run(test_bootstrap_convergence_check)
    _run(test_bootstrap_convergence_constant_data)
    _run(test_bootstrap_ci_level_stored)
    print()

    # ---- 3. Effect sizes ----
    print("--- Effect sizes (effect_size) ---")
    _run(test_cliffs_delta_identical_distributions)
    _run(test_cliffs_delta_clearly_different)
    _run(test_cliffs_delta_reversed)
    _run(test_cliffs_delta_ci_bounds_valid)
    _run(test_cohens_d_known_values)
    _run(test_cohens_d_zero_effect)
    _run(test_cohens_d_ci_brackets_estimate)
    _run(test_hedges_g_correction_factor)
    _run(test_hedges_g_larger_samples)
    _run(test_effect_size_magnitude_thresholds)
    _run(test_effect_size_empty_x_raises)
    _run(test_effect_size_empty_y_raises)
    _run(test_cohens_d_empty_raises)
    _run(test_cohens_d_zero_variance_raises)
    print()

    # ---- 4. Core statistics ----
    print("--- Core statistics (core) ---")
    _run(test_core_cliffs_delta_basic)
    _run(test_core_cliffs_delta_identical)
    _run(test_core_cohens_d_basic)
    _run(test_core_cohens_d_zero_variance)
    _run(test_fidelity_summary_basic)
    _run(test_fidelity_summary_missing_column_raises)
    _run(test_fidelity_summary_quantiles)
    _run(test_threshold_sensitivity_basic)
    _run(test_threshold_sensitivity_default_thresholds)
    _run(test_threshold_sensitivity_missing_column_raises)
    _run(test_threshold_sensitivity_all_pass)
    _run(test_threshold_sensitivity_none_pass)
    _run(test_power_calculation_large_effect)
    _run(test_power_calculation_tiny_effect)
    _run(test_power_calculation_medium_effect)
    _run(test_power_calculation_monotone_in_n)
    _run(test_power_calculation_monotone_in_d)
    print()

    # ---- 5. Cross-module checks ----
    print("--- Cross-module checks ---")
    _run(test_power_module_calculate_power)
    _run(test_power_module_invalid_n_raises)
    _run(test_core_bh_returns_tuple)
    print()

    _report()
