"""Repair the pre-paper capsule inner manifest closure, fail-closed.

The archived metric registry is re-verified inside the restored capsule, so
every file referenced by any registry evidence selector must be pinned by the
inner manifest.  This script:

1. re-hashes every existing manifest entry against the workspace (fail-closed);
2. derives the complete set of registry-referenced evidence paths;
3. appends full entries (bytes/sha256, plus rows/columns for CSV files) for
   any referenced file that is not yet pinned;
4. updates the section counts and rewrites the manifest atomically.

It never removes entries, never alters existing entries, and never lowers a
check: a missing file, hash drift, or duplicate path raises and aborts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "release/prepaper_capsule_inner_manifest.json"
DEFAULT_REGISTRY = ROOT / "docs/review/metric_evidence_registry_2026-08-26.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(path: Path) -> dict[str, object]:
    relative = path.relative_to(ROOT).as_posix()
    entry: dict[str, object] = {
        "file": relative, "bytes": path.stat().st_size, "sha256": sha256(path),
    }
    if path.suffix.lower() == ".csv":
        import pandas as pd

        frame = pd.read_csv(path)
        entry.update({"rows": len(frame), "columns": list(frame.columns)})
    elif path.suffix.lower() == ".json":
        json.loads(path.read_text(encoding="utf-8"))
    return entry


def repair(manifest_path: Path = DEFAULT_MANIFEST,
           registry_path: Path = DEFAULT_REGISTRY) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise RuntimeError("inner manifest is not complete")
    sections = ("evidence", "project_evidence", "source_files")
    pinned: dict[str, dict] = {}
    for section in sections:
        for entry in manifest.get(section, []):
            relative = str(entry.get("file", ""))
            if not relative or relative in pinned:
                raise RuntimeError(f"inner manifest path missing/duplicate: {relative!r}")
            pinned[relative] = entry

    # Fail-closed: every existing entry must still match the workspace bytes.
    for relative, entry in pinned.items():
        path = ROOT / Path(*relative.split("/"))
        if not path.is_file():
            raise RuntimeError(f"pinned payload no longer exists: {relative}")
        if path.stat().st_size != int(entry.get("bytes", -1)):
            raise RuntimeError(f"pinned payload byte drift: {relative}")
        if sha256(path) != str(entry.get("sha256", "")):
            raise RuntimeError(f"pinned payload hash drift: {relative}")

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    referenced: set[str] = set()
    for metric in registry.get("metrics", []):
        for ref in metric.get("evidence_refs", []):
            path = ref.get("path")
            if isinstance(path, str) and path:
                referenced.add(path)
    if not referenced:
        raise RuntimeError("registry exposes no evidence references")

    missing = sorted(referenced - set(pinned))
    added: list[str] = []
    for relative in missing:
        path = ROOT / Path(*relative.split("/"))
        if not path.is_file():
            raise RuntimeError(f"registry-referenced evidence is missing: {relative}")
        expected = next(
            (
                str(ref.get("sha256", ""))
                for metric in registry.get("metrics", [])
                for ref in metric.get("evidence_refs", [])
                if ref.get("path") == relative
            ),
            "",
        )
        entry = _entry(path)
        if expected and entry["sha256"] != expected:
            raise RuntimeError(f"registry-referenced evidence hash drift: {relative}")
        # Registry evidence is project-level supporting material; classify it
        # with the other project evidence to keep the evidence section limited
        # to the canonical data/v10/prepaper tree.
        manifest["project_evidence"].append(entry)
        pinned[relative] = entry
        added.append(relative)

    manifest["project_evidence"].sort(key=lambda entry: str(entry["file"]))
    manifest["counts"] = {
        "evidence_files": len(manifest["evidence"]),
        "project_evidence_files": len(manifest["project_evidence"]),
        "source_files": len(manifest["source_files"]),
    }
    manifest["closure_repair"] = {
        "repaired_utc": datetime.now(timezone.utc).isoformat(),
        "rule": (
            "every registry evidence_refs path must be pinned by the inner "
            "manifest so the restored verifier can re-evaluate all selectors"
        ),
        "added_files": added,
        "existing_entries_unchanged": True,
        "all_existing_hashes_reverified": True,
    }

    paths = [str(entry["file"]) for section in sections for entry in manifest[section]]
    if len(paths) != len(set(paths)):
        raise RuntimeError("repaired manifest contains duplicate paths")

    temporary = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    os.replace(temporary, manifest_path)
    return {
        "status": "PASS_CAPSULE_CLOSURE_REPAIR",
        "added_files": added,
        "counts": manifest["counts"],
        "manifest_sha256": sha256(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    print(json.dumps(repair(args.manifest.resolve(), args.registry.resolve()),
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
