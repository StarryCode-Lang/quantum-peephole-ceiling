#!/usr/bin/env python3
"""Update release_manifest.json with v5 experiment dataset entries.

Scans data/v5/e14-e18 for the latest CSV files, computes SHA-256 hashes,
and appends dataset entries to release/release_manifest.json.
"""

import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = PROJECT_ROOT / "release" / "release_manifest.json"

EXPERIMENTS = {
    "E14": "data/v5/e14",
    "E15": "data/v5/e15",
    "E16": "data/v5/e16",
    "E17": "data/v5/e17",
    "E18": "data/v5/e18",
}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    with MANIFEST.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    existing_ids = {d["experiment_id"] for d in manifest["datasets"]}
    added = 0

    for exp_id, rel_dir in EXPERIMENTS.items():
        if exp_id in existing_ids:
            # Check if it's a smoke entry and we have a full one now
            for ds in manifest["datasets"]:
                if ds["experiment_id"] == exp_id and "_smoke_" in ds["file"]:
                    # Replace with full data if available
                    data_dir = PROJECT_ROOT / rel_dir
                    full_csvs = sorted(data_dir.glob(f"*full*.csv"))
                    if full_csvs:
                        csv_path = full_csvs[-1]
                        import pandas as pd
                        df = pd.read_csv(csv_path)
                        ds["file"] = csv_path.relative_to(PROJECT_ROOT).as_posix()
                        ds["rows"] = len(df)
                        ds["schema"] = "results_v2"
                        ds["sha256"] = file_sha256(csv_path)
                        print(f"  Updated {exp_id}: {csv_path.name} ({len(df)} rows)")
                        added += 1
            continue

        data_dir = PROJECT_ROOT / rel_dir
        if not data_dir.exists():
            print(f"  SKIP {exp_id}: directory not found")
            continue

        # Prefer full mode CSV, fall back to latest
        csvs = sorted(data_dir.glob("*full*.csv")) or sorted(data_dir.glob("*.csv"))
        if not csvs:
            print(f"  SKIP {exp_id}: no CSV files found")
            continue

        csv_path = csvs[-1]  # latest
        import pandas as pd
        df = pd.read_csv(csv_path)

        entry = {
            "experiment_id": exp_id,
            "file": csv_path.relative_to(PROJECT_ROOT).as_posix(),
            "rows": len(df),
            "schema": "results_v2",
            "sha256": file_sha256(csv_path),
        }
        manifest["datasets"].append(entry)
        print(f"  Added {exp_id}: {csv_path.name} ({len(df)} rows, sha256={entry['sha256'][:16]}...)")
        added += 1

    if added > 0:
        manifest["schema_version"] = "2.0.0"
        with MANIFEST.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
        print(f"\nManifest updated: {added} entries added/updated.")
    else:
        print("\nNo new entries to add.")


if __name__ == "__main__":
    main()
