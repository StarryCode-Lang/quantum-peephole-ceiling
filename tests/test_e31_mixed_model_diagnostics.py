"""Tests for the supportive E31 random-slope mixed-model diagnostics."""

import math

from analysis.e31_mixed_model_diagnostics import build_audit


def test_mixed_model_converges_but_reports_boundary_geometry(tmp_path):
    audit = build_audit(tmp_path)
    assert audit["convergence"]["converged"] is True
    assert audit["convergence"]["optimizer_warnflag"] == 0
    assert audit["model"]["observations"] == 1564
    assert audit["model"]["family_groups"] == 15
    assert math.isclose(
        audit["primary_interaction_reproduces_descriptive_pp"],
        -0.37976652169697117,
        abs_tol=1e-9,
    )
    assert audit["diagnostics"]["near_singular_random_effect_geometry"] is True
    assert audit["diagnostics"]["hessian_negative_definite"] is False
    assert audit["metric_dispositions"]["11.33"].startswith("PARTIAL:")
    assert audit["metric_dispositions"]["11.40"].startswith("PASS:")
