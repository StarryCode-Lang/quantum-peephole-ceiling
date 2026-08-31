from pathlib import Path

from scripts.verify_e34_mqt_cross_abstraction import sha256


def test_sha256_is_content_sensitive(tmp_path: Path) -> None:
    path = tmp_path / "x"; path.write_bytes(b"a"); one = sha256(path)
    path.write_bytes(b"b")
    assert sha256(path) != one
