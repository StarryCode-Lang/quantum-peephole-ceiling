"""Tests for the layered archive restore mechanism."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import pytest

from scripts.archive_restore_audit import (
    ArchiveRestoreFailure,
    build_capsule,
    restore_and_verify,
)
from scripts.generate_prepaper_release_manifest import _assert_global_unique_sections


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tiny_release(root: Path) -> tuple[Path, Path]:
    (root / "release").mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)
    payload = root / "payload.txt"
    payload.write_text("restorable\n", encoding="utf-8")
    verifier = root / "scripts/tiny_verifier.py"
    verifier.write_text(
        "import argparse, hashlib, json, pathlib, sys\n"
        "p=argparse.ArgumentParser(); p.add_argument('--manifest'); a=p.parse_args()\n"
        "assert sys.flags.isolated == 1\n"
        "m=json.loads(pathlib.Path(a.manifest).read_text())\n"
        "root=pathlib.Path(a.manifest).parents[1]\n"
        "e=m['evidence'][0]; q=root/e['file']\n"
        "assert hashlib.sha256(q.read_bytes()).hexdigest() == e['sha256']\n"
        "print(json.dumps({'status':'verified','files':2}))\n",
        encoding="utf-8",
    )
    entries = [
        {"file": "payload.txt", "bytes": payload.stat().st_size, "sha256": _hash(payload)},
        {
            "file": "scripts/tiny_verifier.py",
            "bytes": verifier.stat().st_size,
            "sha256": _hash(verifier),
        },
    ]
    manifest = {
        "status": "complete",
        "evidence": entries[:1],
        "project_evidence": [],
        "source_files": entries[1:],
        "counts": {"evidence_files": 1, "project_evidence_files": 0, "source_files": 1},
    }
    manifest_path = root / "release/prepaper_release_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, root / "capsule.zip"


def test_capsule_restores_in_temporary_directory_and_isolated_python(tmp_path: Path):
    manifest, archive = _tiny_release(tmp_path)
    build = build_capsule(tmp_path, manifest, archive)
    result = restore_and_verify(
        archive, python_executable=Path(sys.executable),
        verifier_relative="scripts/tiny_verifier.py",
    )
    assert build["archive_members"] == 3
    assert result["archive_members_extracted"] == 3
    assert result["isolated_python_flag"] == "-I"
    assert result["verifier_exit_code"] == 0
    assert result["verifier_receipt"]["status"] == "verified"


def test_restore_rejects_path_traversal_member(tmp_path: Path):
    archive = tmp_path / "malicious.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../escape.txt", "bad")
    with pytest.raises(ArchiveRestoreFailure, match="unsafe archive member"):
        restore_and_verify(archive, python_executable=Path(sys.executable))


def test_release_manifest_sections_must_be_globally_unique():
    _assert_global_unique_sections(
        [{"file": "a.json"}], [{"file": "b.csv"}], [{"file": "c.py"}],
    )
    with pytest.raises(RuntimeError, match="globally unique"):
        _assert_global_unique_sections(
            [{"file": "same.json"}], [{"file": "same.json"}], [],
        )
