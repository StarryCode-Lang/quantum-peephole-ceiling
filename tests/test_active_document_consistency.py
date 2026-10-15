"""Regression checks for active evidence and release-facing documents."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_active_manuscript_uses_current_repository_and_sealed_panel_scope():
    manuscript = (PROJECT_ROOT / "docs" / "manuscript" / "manuscript.md").read_text(
        encoding="utf-8"
    )

    assert "https://github.com/StarryCode-Lang/quantum-peephole-ceiling" in manuscript
    assert "github.com/Q-research-team/q-research" not in manuscript
    assert "data/v11/e31_listing_phase2b/" in manuscript
    assert "sealed E31 formal factorial" in manuscript
    assert "smoke pilot remains historical support only" in manuscript


def test_experiment_guide_and_residual_register_expose_hash_bound_scope():
    guide = (PROJECT_ROOT / "experiments" / "EXPERIMENT_GUIDE.md").read_text(
        encoding="utf-8"
    )
    register = (
        PROJECT_ROOT
        / "docs"
        / "review"
        / "residual_issue_disposition_2026-08-07.md"
    ).read_text(encoding="utf-8")

    assert "Supporting Pilot: E31 Listing x Phase-2b" in guide
    assert "not silently added" in guide
    assert "hash-bound v11 evidence layers" in guide
    assert "P3 WCL x Phase-2b interaction" in register
    assert "full family x size/depth/seed factorial remains open" in register
