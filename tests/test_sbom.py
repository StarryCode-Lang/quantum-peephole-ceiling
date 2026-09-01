import json

import pytest

from scripts.generate_prepaper_release_manifest import SOURCE_FILES
from scripts.verify_sbom import SBOM, verify_sbom


def test_checked_in_sbom_covers_direct_dependencies():
    result = verify_sbom()
    assert result["status"] == "verified"
    assert result["components"] >= result["direct_requirements_covered"]


def test_prepaper_release_pins_dependency_rebuild_inputs():
    expected = {"requirements.txt", "requirements-lock.txt", "pyproject.toml", "Dockerfile"}
    assert expected.issubset(set(SOURCE_FILES))


def test_sbom_verifier_rejects_volatile_metadata(tmp_path):
    payload = json.loads(SBOM.read_text(encoding="utf-8"))
    payload.setdefault("metadata", {})["timestamp"] = "2026-08-11T00:00:00Z"
    candidate = tmp_path / "volatile.cdx.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="not reproducible"):
        verify_sbom(candidate)


def test_sbom_verifier_rejects_missing_root_dependency_edges(tmp_path):
    payload = json.loads(SBOM.read_text(encoding="utf-8"))
    root_ref = payload["metadata"]["component"]["bom-ref"]
    for dependency in payload["dependencies"]:
        if dependency["ref"] == root_ref:
            dependency.pop("dependsOn", None)
    candidate = tmp_path / "disconnected.cdx.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="root dependency graph"):
        verify_sbom(candidate)
