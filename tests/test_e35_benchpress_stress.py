from pathlib import Path

from experiments.e35_benchpress_stress import sha256


def test_sha256_stream_is_content_sensitive(tmp_path: Path) -> None:
    path = tmp_path / "input.qasm"; path.write_bytes(b"a"); before = sha256(path); path.write_bytes(b"b"); assert sha256(path) != before
