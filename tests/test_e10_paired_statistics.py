"""Regression tests for E10's paired experimental design."""

import numpy as np
import pandas as pd
import pytest

from experiments.e10_phase1_vs_phase2.analyze import (
    _paired_reductions,
    _run_pairwise_analysis,
)


def _synthetic_e10() -> pd.DataFrame:
    rows = []
    for trial, (greedy, hybrid) in enumerate([(0.0, 0.1), (0.2, 0.4), (0.1, 0.1)]):
        for optimizer, reduction in (
            ("greedy_phase1", greedy),
            ("hybrid_phase1_2", hybrid),
        ):
            rows.append({
                "part": "random",
                "circuit_family": "Universal",
                "circuit_type": "random",
                "n_qubits": 5,
                "depth": 20,
                "trial": trial,
                "seed": 42 + trial,
                "optimizer": optimizer,
                "reduction": reduction,
            })
    return pd.DataFrame(rows)


def test_pairing_is_key_based_not_row_order_based():
    df = _synthetic_e10().sample(frac=1.0, random_state=9)
    greedy, hybrid, keys = _paired_reductions(df, "greedy_phase1", "hybrid_phase1_2")

    assert "trial" in keys and "seed" in keys
    assert np.allclose(greedy, [0.0, 0.2, 0.1])
    assert np.allclose(hybrid, [0.1, 0.4, 0.1])


def test_pairwise_report_declares_paired_design_and_effects():
    result = _run_pairwise_analysis(
        _synthetic_e10(), "greedy_phase1", "hybrid_phase1_2"
    )

    assert result["design"] == "paired"
    assert result["n_pairs"] == 3
    assert result["primary_test"].startswith("Wilcoxon")
    assert result["mean_paired_difference"] == pytest.approx(-0.1)
    assert result["matched_rank_biserial"] == pytest.approx(-1.0)


def test_duplicate_circuit_optimizer_result_is_rejected():
    df = _synthetic_e10()
    duplicated = pd.concat([df, df.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate optimizer result"):
        _paired_reductions(duplicated, "greedy_phase1", "hybrid_phase1_2")
