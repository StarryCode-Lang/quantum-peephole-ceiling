"""Build and independently restore-test a layered pre-paper release capsule.

The inner ZIP contains one immutable pre-paper manifest and every file pinned
by that manifest.  The outer audit receipt is intentionally *not* stored in
the ZIP: it pins the finished archive hash and thereby avoids an impossible
self-hash cycle.  A later/current release manifest may pin both the archive and
the outer receipt without changing the already tested inner snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "release/prepaper_capsule_inner_manifest.json"
DEFAULT_ARCHIVE = ROOT / "release/prepaper_restore_capsule.zip"
DEFAULT_AUDIT = ROOT / "release/prepaper_archive_restore_audit.json"
INNER_MANIFEST = "release/prepaper_release_manifest.json"
VERIFIER = "scripts/verify_prepaper_release_manifest.py"


class ArchiveRestoreFailure(RuntimeError):
    """The capsule is malformed, unsafe, incomplete, or fails verification."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_entries(manifest: dict) -> list[dict]:
    entries = (
        list(manifest.get("evidence", []))
        + list(manifest.get("project_evidence", []))
        + list(manifest.get("source_files", []))
    )
    paths = [str(entry.get("file", "")) for entry in entries]
    if not entries or len(paths) != len(set(paths)) or any(not path for path in paths):
        raise ArchiveRestoreFailure("inner manifest has missing or duplicate payload paths")
    expected = manifest.get("counts", {})
    for field, section in (
        ("evidence_files", "evidence"),
        ("project_evidence_files", "project_evidence"),
        ("source_files", "source_files"),
    ):
        if int(expected.get(field, -1)) != len(manifest.get(section, [])):
            raise ArchiveRestoreFailure(f"inner manifest count mismatch: {field}")
    return entries


def _safe_member_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ".." in path.parts
        or ":" in path.parts[0]
        or str(path) != normalized
    ):
        raise ArchiveRestoreFailure(f"unsafe archive member path: {name!r}")
    return normalized


def _validate_source_entry(root: Path, entry: dict) -> Path:
    relative = _safe_member_name(str(entry["file"]))
    path = root / Path(*PurePosixPath(relative).parts)
    if not path.is_file():
        raise ArchiveRestoreFailure(f"missing manifest payload: {relative}")
    if path.stat().st_size != int(entry.get("bytes", -1)):
        raise ArchiveRestoreFailure(f"payload byte count drift: {relative}")
    if sha256(path) != str(entry.get("sha256", "")):
        raise ArchiveRestoreFailure(f"payload hash drift: {relative}")
    return path


def build_capsule(root: Path, manifest_path: Path, archive_path: Path) -> dict:
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if manifest.get("status") != "complete":
        raise ArchiveRestoreFailure("inner pre-paper manifest is not complete")
    entries = _manifest_entries(manifest)
    payloads = [(str(entry["file"]), _validate_source_entry(root, entry)) for entry in entries]
    names = [INNER_MANIFEST] + [name for name, _ in payloads]
    if len(names) != len(set(names)):
        raise ArchiveRestoreFailure("inner manifest path collides with a payload path")

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive_path.with_suffix(archive_path.suffix + ".tmp")
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6,
            allowZip64=True,
        ) as archive:
            archive.writestr(INNER_MANIFEST, manifest_bytes)
            for relative, source in payloads:
                archive.write(source, arcname=_safe_member_name(relative))
        os.replace(temporary, archive_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "payload_entries": len(entries),
        "archive_members": len(names),
        "uncompressed_payload_bytes": sum(int(entry["bytes"]) for entry in entries),
        "inner_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }


def _extract_safely(archive_path: Path, destination: Path) -> list[str]:
    destination_resolved = destination.resolve()
    names: list[str] = []
    with zipfile.ZipFile(archive_path, "r") as archive:
        for info in archive.infolist():
            name = _safe_member_name(info.filename)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ArchiveRestoreFailure(f"symbolic link is forbidden in capsule: {name}")
            target = (destination / Path(*PurePosixPath(name).parts)).resolve()
            try:
                target.relative_to(destination_resolved)
            except ValueError as exc:
                raise ArchiveRestoreFailure(f"archive member escapes restore root: {name}") from exc
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
            names.append(name)
    if len(names) != len(set(names)):
        raise ArchiveRestoreFailure("capsule contains duplicate member names")
    return names


def restore_and_verify(
    archive_path: Path,
    *,
    python_executable: Path = Path(sys.executable),
    verifier_relative: str = VERIFIER,
) -> dict:
    with tempfile.TemporaryDirectory(prefix="qresearch-restore-") as temporary:
        restored_root = Path(temporary) / "restored-project"
        restored_root.mkdir()
        members = _extract_safely(archive_path, restored_root)
        manifest_path = restored_root / INNER_MANIFEST
        if not manifest_path.is_file():
            raise ArchiveRestoreFailure("capsule lacks its inner pre-paper manifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = _manifest_entries(manifest)
        expected_members = {INNER_MANIFEST, *(str(entry["file"]) for entry in entries)}
        if set(members) != expected_members:
            missing = sorted(expected_members - set(members))
            extra = sorted(set(members) - expected_members)
            raise ArchiveRestoreFailure(
                f"capsule member closure mismatch; missing={missing[:5]} extra={extra[:5]}"
            )
        for entry in entries:
            _validate_source_entry(restored_root, entry)

        verifier = restored_root / verifier_relative
        if not verifier.is_file():
            raise ArchiveRestoreFailure(f"restored verifier is missing: {verifier_relative}")
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment["PYTHONNOUSERSITE"] = "1"
        command = [
            str(python_executable), "-I", str(verifier),
            "--manifest", str(manifest_path),
        ]
        completed = subprocess.run(
            command,
            cwd=restored_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout)[-4000:]
            raise ArchiveRestoreFailure(
                f"restored release verifier failed with {completed.returncode}: {tail}"
            )
        output_lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if not output_lines:
            raise ArchiveRestoreFailure("restored release verifier emitted no receipt")
        try:
            verifier_receipt = json.loads(output_lines[-1])
        except json.JSONDecodeError as exc:
            raise ArchiveRestoreFailure("restored verifier did not end with JSON") from exc
        if verifier_receipt.get("status") != "verified":
            raise ArchiveRestoreFailure("restored release verifier did not report verified")
        return {
            "temporary_directory_used": True,
            "temporary_directory_removed_after_test": True,
            "archive_members_extracted": len(members),
            "inner_manifest_sha256": sha256(manifest_path),
            "isolated_python_flag": "-I",
            "python_no_user_site": True,
            "pythonpath_removed": True,
            "verifier_relative_path": verifier_relative,
            "verifier_exit_code": completed.returncode,
            "verifier_receipt": verifier_receipt,
        }


def run_audit(
    *,
    root: Path = ROOT,
    manifest_path: Path = DEFAULT_MANIFEST,
    archive_path: Path = DEFAULT_ARCHIVE,
    audit_path: Path = DEFAULT_AUDIT,
    python_executable: Path = Path(sys.executable),
) -> dict:
    build = build_capsule(root, manifest_path, archive_path)
    restore = restore_and_verify(archive_path, python_executable=python_executable)
    payload = {
        "schema_version": "1.0.0",
        "status": "PASS_LAYERED_ARCHIVE_RESTORE_TEST",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "layering_contract": {
            "inner_layer": (
                "immutable ZIP containing the pre-registration pre-paper manifest "
                "and its complete pinned file closure"
            ),
            "outer_layer": (
                "this audit receipt, stored outside the ZIP, pins the completed "
                "archive and inner manifest hashes"
            ),
            "self_reference_avoided": True,
            "registry_epoch_note": (
                "the archived metric registry is the internally consistent snapshot "
                "immediately before metric 15.41 registers this outer receipt"
            ),
        },
        "archive": {
            "path": archive_path.relative_to(root).as_posix(),
            "sha256": sha256(archive_path),
            "bytes": archive_path.stat().st_size,
            **build,
        },
        "restore_test": restore,
        "metric_dispositions": {
            "15.41": (
                "PASS: a layered release capsule was unpacked into a temporary directory, "
                "its inner manifest and complete hash closure were validated, and the "
                "restored release verifier passed under isolated Python mode"
            )
        },
        "claim_boundary": (
            "This proves byte-complete restoration and executable verification of one "
            "frozen local release capsule on the current Windows/Python dependency stack. "
            "It does not prove off-site durability, media longevity, disaster recovery on "
            "another operating system, or future dependency availability."
        ),
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    args = parser.parse_args()
    payload = run_audit(
        manifest_path=args.manifest.resolve(), archive_path=args.archive.resolve(),
        audit_path=args.audit.resolve(), python_executable=args.python.resolve(),
    )
    print(json.dumps({
        "status": payload["status"],
        "archive_sha256": payload["archive"]["sha256"],
        "members": payload["archive"]["archive_members"],
        "restored_files_verified": payload["restore_test"]["verifier_receipt"]["files"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
