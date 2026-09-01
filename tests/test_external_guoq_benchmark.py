from pathlib import Path

from experiments.external_guoq_benchmark import (
    JAR_MD5,
    JAR_SHA256,
    _hash,
    _java_major,
)


def test_hashes_are_algorithm_specific(tmp_path: Path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"guoq")
    assert len(_hash(artifact)) == len(JAR_SHA256) == 64
    assert len(_hash(artifact, "md5")) == len(JAR_MD5) == 32


def test_missing_java_is_classified_without_exception(tmp_path: Path):
    major, detail = _java_major(tmp_path / "missing-java")
    assert major is None
    assert "FileNotFoundError" in detail
