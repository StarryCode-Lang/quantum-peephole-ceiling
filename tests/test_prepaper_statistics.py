"""Regression tests for confirmatory pre-paper statistical estimands."""

import numpy as np
import pandas as pd

from analysis.prepaper_rq3_tool_comparison import _cluster_permutation


def test_cluster_sign_permutation_is_exact_for_small_cluster_counts():
    frame = pd.DataFrame({
        "circuit_family": ["large", "large", "large", "small_a", "small_b"],
        "difference": [10.0, 10.0, 10.0, -4.0, -4.0],
    })
    replicates = 257
    seed = 9182
    cluster_sums = frame.groupby("circuit_family").difference.sum().to_numpy(float)
    observed = abs(cluster_sums.sum() / len(frame))
    masks = np.arange(1 << len(cluster_sums), dtype=np.uint32)[:, None]
    bits = (masks >> np.arange(len(cluster_sums), dtype=np.uint32)) & 1
    signs = bits.astype(float) * 2.0 - 1.0
    null = np.abs(np.sum(signs * cluster_sums, axis=1) / len(frame))
    expected = float(np.mean(null >= observed - 1e-15))

    assert _cluster_permutation(frame, replicates, seed) == expected
