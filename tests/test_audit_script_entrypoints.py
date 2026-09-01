"""Regression tests for directly executable release-audit entry points."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPTS = (
    "scripts/audit_equivalence_verifier_agreement.py",
    "scripts/audit_semantic_mutation_sentinels.py",
    "scripts/audit_rewrite_properties.py",
    "scripts/audit_rewrite_order_confluence.py",
)


@pytest.mark.parametrize("script", AUDIT_SCRIPTS)
def test_release_audit_script_supports_direct_help(script: str) -> None:
    completed = subprocess.run(
        [sys.executable, script, "--help"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert "usage:" in completed.stdout
