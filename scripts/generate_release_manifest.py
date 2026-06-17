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

STANDALONE_IDS = {
    "new_families_heldout.csv": "HELDOU",
    "qiskit_pass_isolation.csv": "ISOLATION",
}


def dataset_entries(data_root: Path) -> List[Dict[str, object]]:
    """Collect canonical active CSV datasets under data/v2_fixed, data/v3_extended, data/v4, and data/v5."""
    entries: List[Dict[str, object]] = []
    for root_name in ["v2_fixed", "v3_extended", "v4", "v5"]:
        root = data_root / root_name
        if not root.exists():
            continue
        for exp_dir in sorted(path for path in root.glob("**") if path.is_dir()):
            if (root_name, exp_dir.name) in KNOWN_DUPLICATES:
                continue
            metadata_path = exp_dir / "metadata.json"
            if metadata_path.exists():
                try:
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                except Exception:
                    metadata = {}
                canonical = metadata.get("canonical_data_file")
                csv_paths = [exp_dir / canonical] if canonical else sorted(exp_dir.glob("*.csv"))
            else:
                csv_paths = sorted(exp_dir.glob("*.csv"))
            for csv_path in csv_paths:
                if not csv_path or not csv_path.exists():
                    continue
                try:
                    rows = int(len(pd.read_csv(csv_path)))
                except Exception:
                    rows = None
                exp_id = STANDALONE_IDS.get(csv_path.name, csv_path.parent.name.upper())
                entries.append(
                    {
                        "file": csv_path.relative_to(PROJECT_ROOT).as_posix(),
                        "sha256": file_sha256(csv_path),
                        "rows": rows,
                        "schema": (
                            "results_v2"
                            if root_name == "v5"
                            else "results_v1"
                            if root_name == "v4"
                            else "legacy_v2_v3"
                        ),
                        "experiment_id": exp_id,
                    }
                )
    return entries


def generate_manifest(release_id: str) -> Dict[str, object]:
    """Build release manifest data."""
    source_files = tuple(DEFAULT_SOURCE_FILES) + (
        "src/circuits/real_benchmarks.py",
        "analysis/structural_ceiling.py",
        "experiments/e11_real_circuit_benchmark/run.py",
        "experiments/e12_compiler_baseline/run.py",
        "experiments/e13_structural_ceiling/run.py",
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
                "conda run -n q-research python tests/test_core.py",
                "conda run -n q-research python scripts/reproduce_all.py --verify",
                "conda run -n q-research python experiments/e11_real_circuit_benchmark/run.py --mode smoke",
                "conda run -n q-research python experiments/e12_compiler_baseline/run.py --mode smoke",
                "conda run -n q-research python experiments/e13_structural_ceiling/run.py --mode smoke",
                "conda run -n q-research python scripts/generate_release_manifest.py",
            ],
            "full_experiment_entrypoints": [
                "conda run -n q-research python experiments/e11_real_circuit_benchmark/run.py --mode full",
                "conda run -n q-research python experiments/e12_compiler_baseline/run.py --mode full",
                "conda run -n q-research python experiments/e13_structural_ceiling/run.py --mode full",
                "conda run -n q-research python experiments/e14_extended_benchmark/run.py --mode full",
                "conda run -n q-research python experiments/e15_multi_compiler/run.py --mode full",
                "conda run -n q-research python experiments/e16_window_scaling/run.py --mode full",
                "conda run -n q-research python experiments/e17_connectivity/run.py --mode full",
                "conda run -n q-research python experiments/e18_clifford_t/run.py --mode full",
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


if __name__ == "__main__":
    main()
