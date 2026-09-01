"""Regression tests for the source-import/direct-requirement closure."""

from pathlib import Path

import pytest

from scripts.audit_direct_dependencies import DEFAULT_REQUIREMENTS, audit


def test_release_critical_imports_have_direct_requirements():
    report = audit()
    assert report["status"] == "VERIFIED"
    for name in ("PIL", "psutil", "qiskit_aer", "qiskit_ibm_runtime", "statsmodels"):
        assert report["third_party_imports"][name]["declared"] is True


def test_audit_rejects_a_removed_direct_requirement(tmp_path: Path):
    lines = DEFAULT_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    path = tmp_path / "requirements.txt"
    path.write_text(
        "\n".join(line for line in lines if not line.lower().startswith("psutil==")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="psutil->psutil"):
        audit(path)
