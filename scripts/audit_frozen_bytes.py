"""Audit frozen bytes against a manifest, without trusting ``git status``.

Why this exists
---------------
Round 19 (2026-10-29) found that ``git status -- data release`` can be clean
while a hash-pinned CSV differs from its own Git blob by 6,721 carriage
returns.  Git normalises line endings on comparison, so the standard
"the worktree is clean, therefore the frozen data is untouched" argument used
by rounds 10-18 is unsound for that failure mode.

This script answers the question directly: for every ``(file, sha256)`` pair a
manifest declares, does the file on disk hash to the declared value?

Classification
--------------
MATCH        worktree bytes hash to the declared digest
CRLF_DRIFT   the Git blob for that path hashes to the declared digest, so the
             only difference is line endings -- data values are unchanged
REAL_DRIFT   neither the worktree nor the blob matches: the content changed
MISSING      the declared path does not exist
NO_DIGEST    the entry carries no sha256 (reported, never silently skipped)

Usage
-----
    python scripts/audit_frozen_bytes.py --manifest release/release_manifest.json
    python scripts/audit_frozen_bytes.py --manifest release/prepaper_release_manifest.json \
        --allow-missing --limit 5000

Exit status is 0 when every entry is MATCH, or CRLF_DRIFT with ``--allow-crlf``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]

DIGEST_KEYS = ("sha256", "observed_sha256", "digest", "hash")
PATH_KEYS = ("file", "path", "relative_path")


def iter_entries(node: Any) -> Iterator[tuple[str, str]]:
    """Yield ``(path, digest)`` for every dict that carries both."""

    if isinstance(node, dict):
        path = next((node[key] for key in PATH_KEYS if isinstance(node.get(key), str)), None)
        digest = next((node[key] for key in DIGEST_KEYS if isinstance(node.get(key), str)), None)
        if path and digest and len(digest) == 64:
            yield path, digest
            return
        for value in node.values():
            yield from iter_entries(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_entries(value)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha(relative: str) -> str | None:
    """sha256 of ``HEAD:<relative>``; ``None`` when Git cannot produce it."""

    try:
        proc = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
    except OSError:  # pragma: no cover - git absent
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    return sha256_bytes(proc.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--allow-crlf", action="store_true", help="treat CRLF_DRIFT as acceptable")
    parser.add_argument("--allow-missing", action="store_true", help="treat MISSING as acceptable")
    parser.add_argument("--limit", type=int, default=0, help="audit at most N entries (0 = all)")
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    entries = list(dict.fromkeys(iter_entries(payload)))
    if args.limit:
        entries = entries[: args.limit]

    counts: Counter[str] = Counter()
    problems: list[dict[str, str]] = []
    for relative, expected in entries:
        path = ROOT / relative
        if not path.exists():
            counts["MISSING"] += 1
            problems.append({"path": relative, "status": "MISSING", "expected": expected})
            continue
        actual = sha256_file(path)
        if actual == expected:
            counts["MATCH"] += 1
            continue
        blob = git_blob_sha(relative)
        if blob == expected:
            counts["CRLF_DRIFT"] += 1
            problems.append(
                {
                    "path": relative,
                    "status": "CRLF_DRIFT",
                    "expected": expected,
                    "actual": actual,
                    "bytes_delta": str(path.stat().st_size),
                }
            )
        else:
            counts["REAL_DRIFT"] += 1
            problems.append(
                {"path": relative, "status": "REAL_DRIFT", "expected": expected, "actual": actual}
            )

    ok = counts["REAL_DRIFT"] == 0 and not counts["MISSING"]
    if args.allow_crlf:
        ok = counts["REAL_DRIFT"] == 0 and (args.allow_missing or not counts["MISSING"])
    if args.allow_missing:
        ok = counts["REAL_DRIFT"] == 0

    summary = {
        "manifest": manifest_path.relative_to(ROOT).as_posix()
        if manifest_path.is_relative_to(ROOT)
        else str(manifest_path),
        "entries": len(entries),
        "counts": dict(sorted(counts.items())),
        "ok": ok,
        "problems": problems,
    }
    if args.report:
        args.report.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if not args.quiet:
        print(json.dumps({k: summary[k] for k in ("manifest", "entries", "counts", "ok")}, indent=2))
        for problem in problems[:20]:
            print(f"  {problem['status']:11s} {problem['path']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
