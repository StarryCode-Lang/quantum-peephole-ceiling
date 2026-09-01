"""Byte-read and inventory the full project tree for the final coverage claim."""

from __future__ import annotations

import argparse
import codecs
import csv
import hashlib
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "v10" / "prepaper" / "audit"
SELF_GENERATED_MANIFEST = PROJECT_ROOT / "release" / "prepaper_release_manifest.json"
SELF_GENERATED_FINALIZATION_FILES = {
    PROJECT_ROOT / "docs/review/metric_evidence_registry_2026-08-26.json",
    PROJECT_ROOT / "docs/review/metric_audit_ledger_2026-08-24.csv",
    PROJECT_ROOT / "docs/review/metric_audit_summary_2026-08-24.json",
    PROJECT_ROOT / "docs/review/metric_audit_resolution_2026-08-24.md",
}
REGENERABLE_CACHE_DIRECTORIES = {
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "__pycache__",
}
TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".jsonl", ".csv", ".toml", ".yaml",
    ".yml", ".ini", ".cfg", ".rst", ".tex", ".bib", ".qasm", ".sml",
    ".cmake", ".sh", ".ps1", ".bat", ".gitignore", ".gitattributes",
}


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="")
    temporary.replace(path)


def _inspect(path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    size = 0
    newlines = 0
    last = b""
    suffix = path.suffix.lower()
    text_candidate = suffix in TEXT_SUFFIXES or (not suffix and path.stat().st_size <= 1024 * 1024)
    decoder = codecs.getincrementaldecoder("utf-8")("strict") if text_candidate else None
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
            newlines += chunk.count(b"\n")
            last = chunk[-1:]
            if decoder is not None:
                try:
                    decoder.decode(chunk, final=False)
                except UnicodeDecodeError:
                    decoder = None
    utf8 = decoder is not None
    if decoder is not None:
        try:
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            utf8 = False
    return {
        "relative_path": path.relative_to(PROJECT_ROOT).as_posix(),
        "bytes": size, "sha256": digest.hexdigest(),
        "kind": "utf8_text" if utf8 else "binary_or_external_encoding",
        "lines": (newlines + (1 if size and last != b"\n" else 0)) if utf8 else "",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--workers", type=int,
        default=min(16, max(4, (os.cpu_count() or 4))),
        help="ordered parallel readers used for byte hashing",
    )
    args = parser.parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be positive")
    output = args.output_dir.resolve()
    files: list[Path] = []
    directory_rows: list[dict[str, object]] = []
    for current, directories, filenames in os.walk(PROJECT_ROOT):
        current_path = Path(current)
        relative = current_path.relative_to(PROJECT_ROOT)
        directories[:] = sorted(name for name in directories if not (
            (relative == Path(".") and name == ".git")
            or name in REGENERABLE_CACHE_DIRECTORIES
            or (current_path / name).resolve() == output
        ))
        filenames = sorted(
            name for name in filenames
            if (current_path / name).resolve() != SELF_GENERATED_MANIFEST.resolve()
            and (current_path / name).resolve() not in SELF_GENERATED_FINALIZATION_FILES
        )
        directory_rows.append({
            "relative_directory": "." if relative == Path(".") else relative.as_posix(),
            "direct_files": len(filenames), "direct_subdirectories": len(directories),
        })
        files.extend(current_path / name for name in filenames)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        records = list(executor.map(_inspect, files))
    output.mkdir(parents=True, exist_ok=True)
    file_csv = output / "workspace_file_inventory.csv"
    with file_csv.with_suffix(".csv.tmp").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]) if records else
                                ["relative_path", "bytes", "sha256", "kind", "lines"])
        writer.writeheader()
        writer.writerows(records)
    file_csv.with_suffix(".csv.tmp").replace(file_csv)
    directory_csv = output / "workspace_directory_inventory.csv"
    with directory_csv.with_suffix(".csv.tmp").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(directory_rows[0]))
        writer.writeheader()
        writer.writerows(directory_rows)
    directory_csv.with_suffix(".csv.tmp").replace(directory_csv)
    kinds = Counter(str(record["kind"]) for record in records)
    total_lines = sum(int(record["lines"]) for record in records if record["lines"] != "")
    summary = {
        "status": "complete", "created_utc": datetime.now(timezone.utc).isoformat(),
        "coverage_boundary": "all files and directories under project root at scan start",
        "excluded": [
            ".git internals",
            "regenerable caches: " + ", ".join(sorted(REGENERABLE_CACHE_DIRECTORIES)),
            output.relative_to(PROJECT_ROOT).as_posix()
            + " (self-generated audit outputs)",
            SELF_GENERATED_MANIFEST.relative_to(PROJECT_ROOT).as_posix()
            + " (self-generated release manifest)",
            "self-generated metric finalization files: " + ", ".join(sorted(
                path.relative_to(PROJECT_ROOT).as_posix()
                for path in SELF_GENERATED_FINALIZATION_FILES
            )),
        ],
        "files_byte_read": len(records), "directories_enumerated": len(directory_rows),
        "ordered_hash_workers": args.workers,
        "bytes_read": sum(int(record["bytes"]) for record in records),
        "utf8_text_files": kinds["utf8_text"],
        "binary_or_external_encoding_files": kinds["binary_or_external_encoding"],
        "utf8_lines_counted": total_lines,
        "file_inventory_sha256": hashlib.sha256(file_csv.read_bytes()).hexdigest(),
        "directory_inventory_sha256": hashlib.sha256(directory_csv.read_bytes()).hexdigest(),
    }
    _atomic_text(output / "workspace_coverage.json",
                 json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
