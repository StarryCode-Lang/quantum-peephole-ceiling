from analysis.e31_validity_runtime_frontier import derive


def test_e31_validity_runtime_frontier_and_auc(tmp_path):
    audit = derive(tmp_path, bootstrap_replicates=30)

    assert audit["status"] == "PASS_E31_VALIDITY_RUNTIME_FRONTIER_AND_BUDGET_AUC_COMPLETE"
    assert audit["formal_rows"] == 28152
    assert audit["budgets_seconds"] == [1, 10, 30, 120]
    assert 0.0 <= audit["log10_budget_normalized_auc"]["validity_rate"] <= 1.0
    assert audit["log10_budget_normalized_auc"]["itt_mean_reduction_pp"] >= 0.0
    assert (tmp_path / "frontier_by_budget.csv").is_file()
    assert (tmp_path / "validity_runtime_frontier.png").is_file()
    assert (tmp_path / "validity_runtime_frontier.pdf").is_file()
