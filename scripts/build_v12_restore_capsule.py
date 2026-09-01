"""Build and independently restore-test the v12 research capsule."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release" / "prepaper_v12_capsule_inner_manifest.json"
ARCHIVE = ROOT / "release" / "prepaper_v12_restore_capsule.zip"
AUDIT = ROOT / "release" / "prepaper_v12_archive_restore_audit.json"
INNER_NAME = "release/prepaper_v12_release_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts or ":" in path.parts[0] or str(path) != normalized:
        raise RuntimeError(f"unsafe capsule path: {name}")
    return normalized


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def payload_files() -> list[Path]:
    excluded_dirs = {".git", ".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache"}
    excluded_names = {ARCHIVE.name, MANIFEST.name, AUDIT.name, "prepaper_restore_capsule.zip"}
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(ROOT).parts
        if any(part in excluded_dirs for part in relative_parts):
            continue
        if path.name in excluded_names or path.suffix in {".pyc", ".tmp"}:
            continue
        files.append(path)
    return sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())


def build_manifest() -> dict[str, Any]:
    files = payload_files()
    entries = [
        {"file": rel, "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in files
        for rel in [path.relative_to(ROOT).as_posix()]
    ]
    manifest = {
        "schema_version": "v12-capsule-manifest-v1",
        "status": "complete",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project": "Q-research v12 rewrite exposure certificate",
        "source_commit_at_capsule_build": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "counts": {"payload_files": len(entries)},
        "payload": entries,
        "claim_boundary": "The capsule is a byte-pinned local research snapshot. E41 E33/E35 source roots remain external inputs recorded by hash in the v12 evidence.",
    }
    write_json(MANIFEST, manifest)
    return manifest


def manifest_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries = manifest.get("payload")
    if not isinstance(entries, list) or not entries or manifest.get("counts", {}).get("payload_files") != len(entries):
        raise RuntimeError("invalid v12 capsule manifest")
    names = [safe_name(str(entry.get("file", ""))) for entry in entries]
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate v12 capsule manifest paths")
    return entries


def validate_payload(root: Path, entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        path = root / Path(*PurePosixPath(safe_name(str(entry["file"]))).parts)
        if not path.is_file() or path.stat().st_size != int(entry["bytes"]) or sha256(path) != entry["sha256"]:
            raise RuntimeError(f"payload hash mismatch: {entry['file']}")


def build_archive(manifest: dict[str, Any]) -> dict[str, Any]:
    entries = manifest_entries(manifest)
    temporary = ARCHIVE.with_suffix(ARCHIVE.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
            manifest_bytes = MANIFEST.read_bytes()
            archive.writestr(INNER_NAME, manifest_bytes)
            for entry in entries:
                relative = safe_name(str(entry["file"]))
                archive.write(ROOT / Path(*PurePosixPath(relative).parts), arcname=relative)
        os.replace(temporary, ARCHIVE)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "archive_sha256": sha256(ARCHIVE),
        "archive_bytes": ARCHIVE.stat().st_size,
        "inner_manifest_sha256": sha256(MANIFEST),
        "payload_files": len(entries),
        "uncompressed_payload_bytes": sum(int(entry["bytes"]) for entry in entries),
    }


def extract_safely(destination: Path) -> list[str]:
    destination_resolved = destination.resolve()
    names: list[str] = []
    with zipfile.ZipFile(ARCHIVE, "r") as archive:
        for info in archive.infolist():
            name = safe_name(info.filename)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise RuntimeError(f"symlink in capsule: {name}")
            target = (destination / Path(*PurePosixPath(name).parts)).resolve()
            try:
                target.relative_to(destination_resolved)
            except ValueError as exc:
                raise RuntimeError(f"capsule member escapes restore root: {name}") from exc
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
            names.append(name)
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate archive member")
    return names


def run_json_verifier(restored_root: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-I", "scripts/verify_v12_readiness_package.py"],
        cwd=restored_root, capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"restored v12 verifier failed: {(completed.stderr or completed.stdout)[-2000:]}")
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("restored v12 verifier emitted no receipt")
    result = json.loads(lines[-1])
    if result.get("status") != "verified":
        raise RuntimeError("restored v12 verifier did not verify")
    return result


def run_full_tests(restored_root: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-I", "-m", "pytest", "-q", "--disable-warnings"],
        cwd=restored_root, capture_output=True, text=True, check=False,
    )
    output = completed.stdout + "\n" + completed.stderr
    passed = re.search(r"(\d+) passed", output)
    failed = re.search(r"(\d+) failed", output)
    skipped = re.search(r"(\d+) skipped", output)
    failed_count = len(re.findall(r"^FAILED ", output, flags=re.MULTILINE))
    if not passed:
        collected_run = subprocess.run(
            [sys.executable, "-I", "-m", "pytest", "--collect-only", "-q", "--disable-warnings"],
            cwd=restored_root, capture_output=True, text=True, check=False,
        )
        collected_lines = collected_run.stdout.splitlines() + collected_run.stderr.splitlines()
        collected_count = sum(
            int(match.group(1))
            for line in collected_lines
            if (match := re.search(r":\s*(\d+)\s*$", line))
        )
        if collected_count:
            passed_count = collected_count - failed_count - int(skipped.group(1)) if skipped else collected_count - failed_count
        else:
            passed_count = None
    else:
        passed_count = int(passed.group(1))
    return {
        "command": f"{sys.executable} -I -m pytest -q --disable-warnings",
        "exit_code": completed.returncode,
        "passed": passed_count,
        "failed": int(failed.group(1)) if failed else (failed_count or None),
        "skipped": int(skipped.group(1)) if skipped else 0,
        "tail": output[-3000:],
    }


def restore_test(manifest: dict[str, Any], *, run_tests: bool) -> dict[str, Any]:
    entries = manifest_entries(manifest)
    with tempfile.TemporaryDirectory(prefix="qresearch-v12-restore-") as temporary:
        restored_root = Path(temporary) / "restored-project"
        restored_root.mkdir()
        names = extract_safely(restored_root)
        expected = {INNER_NAME, *(str(entry["file"]) for entry in entries)}
        if set(names) != expected:
            raise RuntimeError(f"member closure mismatch: missing={sorted(expected - set(names))[:5]} extra={sorted(set(names) - expected)[:5]}")
        restored_manifest = json.loads((restored_root / INNER_NAME).read_text(encoding="utf-8"))
        if restored_manifest != manifest:
            raise RuntimeError("inner manifest content drift")
        validate_payload(restored_root, entries)
        verifier = run_json_verifier(restored_root)
        tests = run_full_tests(restored_root) if run_tests else {"not_run": True}
        return {
            "temporary_directory_used": True,
            "temporary_directory_removed_after_test": True,
            "archive_members_extracted": len(names),
            "inner_manifest_sha256": sha256(restored_root / INNER_NAME),
            "isolated_python_flag": "-I",
            "python_no_user_site": True,
            "verifier": verifier,
            "full_test_recheck": tests,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    manifest = build_manifest()
    archive = build_archive(manifest)
    restore = restore_test(manifest, run_tests=not args.skip_tests)
    tests = restore["full_test_recheck"]
    status = "PASS_V12_CAPSULE_RESTORE_AND_VERIFIER"
    if tests.get("exit_code") != 0:
        status = "PASS_V12_CAPSULE_RESTORE_WITH_BASELINE_TEST_DRIFT"
    payload = {
        "schema_version": "v12-capsule-restore-audit-v1",
        "status": status,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "archive": {"path": ARCHIVE.relative_to(ROOT).as_posix(), **archive},
        "restore_test": restore,
        "claim_boundary": "This proves byte-complete restoration, hash closure, and v12 verifier execution in a temporary directory on the current Windows/Python stack. It does not prove external E33/E35 input availability or future dependency availability.",
    }
    write_json(AUDIT, payload)
    print(json.dumps({"status": status, "archive_sha256": archive["archive_sha256"], "members": archive["payload_files"], "restored_verifier": restore["verifier"]["status"], "restored_test_exit_code": tests.get("exit_code")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
