"""Artifact tests for the isolated compiler-version panel."""

import json

import pandas as pd

from analysis.compiler_version_sensitivity_audit import DEFAULT_OUTPUT_DIR, ENVIRONMENTS


def test_version_panel_covers_two_versions_of_three_compilers():
    audit = json.loads(
        (DEFAULT_OUTPUT_DIR / "compiler_version_sensitivity_audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert audit["status"] == "PASS_BOUNDED_COMPILER_VERSION_PANEL"
    assert audit["panel"]["rows"] == 15
    assert audit["panel"]["families"] == 15
    assert audit["all_tools_have_two_versions"] is True
    assert audit["all_runs_successful"] is True
    assert audit["all_outputs_exact_equivalent"] is True
    assert audit["all_version_pairs_structurally_identical"] is True
    assert audit["panel"]["qubit_range"] == [4, 5]
    comparisons = {row["tool"]: row for row in audit["tool_version_comparisons"]}
    assert set(comparisons) == {"qiskit", "cirq", "tket"}
    for row in comparisons.values():
        assert row["rows"] == 15
        assert row["structurally_identical_rows"] == 15
        assert row["all_rows_structurally_identical"] is True
        assert row["runtime_role"].startswith("descriptive only")


def test_version_panel_records_every_isolated_environment_and_bounded_claims():
    audit = json.loads(
        (DEFAULT_OUTPUT_DIR / "compiler_version_sensitivity_audit.json").read_text(
            encoding="utf-8"
        )
    )
    expected = {str(spec["id"]) for spec in ENVIRONMENTS}
    observed = {row["environment_id"] for row in audit["executed_environments"]}
    assert observed == expected
    combined = pd.read_csv(DEFAULT_OUTPUT_DIR / "all_version_results.csv")
    assert len(combined) == 15 * len(ENVIRONMENTS)
    assert combined["status"].eq("success").all()
    assert combined["exact_equivalent"].all()
    assert combined["numerically_unitary_equivalent"].all()
    assert combined["optimized_qasm_path"].notna().all()
    assert "not E31 replication" in audit["claim_boundary"]
    assert audit["metric_dispositions"]["8.28"].startswith("PARTIAL:")
    assert audit["metric_dispositions"]["18.10"].startswith("PARTIAL:")
