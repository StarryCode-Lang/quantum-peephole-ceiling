"""Generate a machine-readable release manifest for active experiment outputs."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.provenance import DEFAULT_SOURCE_FILES, file_sha256, git_commit, package_versions, source_hashes  # noqa: E402


def git_dirty(project_root: Path) -> bool | None:
    """Return whether the git worktree has uncommitted changes."""
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return bool(completed.stdout.strip())


KNOWN_DUPLICATES = {
    ("v5", "e03"),
}

# Legacy datasets superseded by a newer version in a later data directory.
# These are still listed in the manifest for provenance but marked as superseded.
# Maps (root_name, dir_name) -> superseded_by label.
SUPERSEDED_DIRS = {
    # v6 e29 smoke (80 rows, 2 seeds) → superseded by v7 e29 full (800 rows, 10 seeds)
    ("v6", "e29_multi_seed_e04"): "v7/e29 (800 rows)",
}

STANDALONE_IDS = {
    "new_families_heldout.csv": "HELDOU",
    "qiskit_pass_isolation.csv": "ISOLATION",
}

# Directory names that never hold canonical datasets:
#   derived/  - analysis artifacts regenerated from the canonical CSV
#   metadata/ - per-run metadata sidecars (sota_benchmark)
#   raw/      - primary per-tool run CSVs (sota_benchmark); inputs, not the
#               canonical analysis dataset (aggregated/ is canonical there)
#   logs/     - run logs
#   scholar/  - reference-verification artifacts (owned by the references
#               workstream); not experiment datasets
NON_CANONICAL_DIR_NAMES = {"derived", "metadata", "raw", "logs", "scholar"}

SCHEMA_BY_ROOT = {
    "v2_fixed": "legacy_v2_v3",
    "v4": "results_v1",
    "v5": "results_v2",
    "v6": "results_v6",
    "v7": "results_v7",
    "v8": "results_v8",
}

# Canonical-file override for directories that have no metadata.json (their
# contents are owned by another workstream and must not be modified). The
# override applies only while metadata.json is absent; a metadata.json with
# canonical_data_file always takes precedence.
CANONICAL_FILE_OVERRIDES = {
    # data/v8/hardware_validation: ehw_runs_*.csv is the primary per-run
    # dataset; ehw_summary_*.csv is a derived aggregate of it.
    # Wave-3 decision (final_verification): the 288-row FULL run is canonical
    # (the wave-1 hardware worker designated it canonical in
    # docs/review/wave1/hardware_validation.md). The two smoke runs
    # (48 and 96 rows) are earlier partial runs kept for provenance only;
    # ehw_summary_*.csv files are derived aggregates of their sibling runs.
    ("v8", "hardware_validation"): "ehw_runs_full_20260720_150931.csv",
}


def dataset_entries(data_root: Path) -> List[Dict[str, object]]:
    """Collect canonical CSV datasets under data/v2_fixed .. data/v8.

    Only the file declared by each directory's ``canonical_data_file`` (or, for
    directories without metadata, the single top-level CSV) is emitted. Files
    under derived/, metadata/, raw/ and logs/ subdirectories are excluded.
    """
    entries: List[Dict[str, object]] = []
    claimed: set[str] = set()
    for root_name in ["v2_fixed", "v4", "v5", "v6", "v7", "v8"]:
        root = data_root / root_name
        if not root.exists():
            continue
        for exp_dir in sorted(path for path in root.glob("**") if path.is_dir()):
            rel_parts = exp_dir.relative_to(root).parts
            if any(part in NON_CANONICAL_DIR_NAMES for part in rel_parts):
                continue
            if (root_name, exp_dir.name) in KNOWN_DUPLICATES:
                continue
            metadata_path = exp_dir / "metadata.json"
            metadata = {}
            if metadata_path.exists():
                try:
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                except Exception:
                    metadata = {}
            canonical = metadata.get("canonical_data_file")
            if not canonical:
                canonical = CANONICAL_FILE_OVERRIDES.get((root_name, exp_dir.name))
            if canonical:
                csv_paths = [exp_dir / canonical]
            else:
                # No metadata: only treat direct children CSVs as canonical
                # candidates (subdirectory files belong to raw/derived roles).
                csv_paths = sorted(exp_dir.glob("*.csv"))
            for csv_path in csv_paths:
                if not csv_path or not csv_path.exists():
                    continue
                rel_file = csv_path.relative_to(PROJECT_ROOT).as_posix()
                if rel_file in claimed:
                    continue
                claimed.add(rel_file)
                try:
                    rows = int(len(pd.read_csv(csv_path)))
                except Exception:
                    rows = None
                exp_id = metadata.get("experiment_id") or STANDALONE_IDS.get(
                    csv_path.name, exp_dir.name.upper()
                )
                superseded_by = SUPERSEDED_DIRS.get((root_name, exp_dir.name))
                entry = {
                    "file": rel_file,
                    "sha256": file_sha256(csv_path),
                    "rows": rows,
                    "schema": SCHEMA_BY_ROOT.get(root_name, "legacy_v2_v3"),
                    "experiment_id": exp_id,
                }
                if superseded_by:
                    entry["superseded"] = True
                    entry["superseded_by"] = superseded_by
                entries.append(entry)
    return entries


def generate_manifest(release_id: str) -> Dict[str, object]:
    """Build release manifest data."""
    source_files = tuple(DEFAULT_SOURCE_FILES) + (
        "src/circuits/real_benchmarks.py",
        "src/optimisation/_gate_predicates.py",
        "src/optimisation/ceiling_aware.py",
        "analysis/structural_ceiling.py",
        "experiments/e11_real_circuit_benchmark/run.py",
        "experiments/e12_compiler_baseline/run.py",
        "experiments/e13_structural_ceiling/run.py",
        "experiments/e19_wcl_listing/run.py",
        "scripts/generate_release_manifest.py",
    )
    return {
        "schema_version": "1.0.0",
        "release_id": release_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git": {
            "branch": subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip(),
            "commit": git_commit(PROJECT_ROOT),
            "dirty": git_dirty(PROJECT_ROOT),
        },
        "datasets": dataset_entries(PROJECT_ROOT / "data"),
        "source_hashes": source_hashes(PROJECT_ROOT, source_files),
        "environment": {
            "env_id": release_id,
            "python": sys.version,
            "platform": platform.platform(),
            "packages": package_versions(("qiskit", "numpy", "scipy", "pandas", "matplotlib", "tqdm")),
        },
        "reproduction": {
            "conda_env": "q-research",
            "entrypoints": [
                "conda run -n q-research python -m pytest tests/ -q",
                "conda run -n q-research python scripts/reproduce_all.py --verify",
                "conda run -n q-research python experiments/e11_real_circuit_benchmark/run.py --mode smoke",
                "conda run -n q-research python experiments/e12_compiler_baseline/run.py --mode smoke",
                "conda run -n q-research python experiments/e13_structural_ceiling/run.py --mode smoke",
                "conda run -n q-research python scripts/generate_release_manifest.py",
            ],
            "full_experiment_entrypoints": [
                "conda run -n q-research python experiments/e11_real_circuit_benchmark/run.py --mode full",
                "conda run -n q-research python experiments/e12_compiler_baseline/run.py --mode full --both",
                "conda run -n q-research python experiments/e13_structural_ceiling/run.py --mode full",
                "conda run -n q-research python experiments/e14_extended_benchmark/run.py --mode full",
                "conda run -n q-research python experiments/e15_multi_compiler/run.py --mode full",
                "conda run -n q-research python experiments/e16_window_scaling/run.py --mode full",
                "conda run -n q-research python experiments/e17_connectivity/run.py --mode full",
                "conda run -n q-research python experiments/e18_clifford_t/run.py --mode full",
                "conda run -n q-research python experiments/e19_wcl_listing/run.py --mode full",
                "conda run -n q-research python experiments/e10_phase1_vs_phase2/run_phase2b.py",
                "conda run -n q-research python experiments/e21_ceiling_aware/run.py --mode full",
            ],
            "random_seed_policy": "recorded_per_row",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate release manifest")
    parser.add_argument("--release-id", default=f"q-research-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--output", default="release/release_manifest.json")
    args = parser.parse_args()

    manifest = generate_manifest(args.release_id)
    output = PROJECT_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
    print(f"Release manifest written to {output}")
    print(f"Datasets: {len(manifest['datasets'])}")

    # Review H8: warn loudly when the worktree is dirty so the release
    # manager knows to commit before publishing.  A dirty release means
    # the source_hashes cannot be recovered from git alone, breaking
    # third-party reproducibility.
    if manifest["git"].get("dirty"):
        print(
            "\n⚠️  WARNING (review H8): git worktree is DIRTY. "
            "The release manifest's source_hashes may not be recoverable "
            "from git. To produce a clean release:\n"
            "  1. Commit all changes:  git add -A && git commit -m 'release'\n"
            "  2. Re-run:  python scripts/generate_release_manifest.py\n"
            "  3. Verify manifest['git']['dirty'] == false"
        )


if __name__ == "__main__":
    main()
