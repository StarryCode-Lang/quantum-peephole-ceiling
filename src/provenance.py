"""Reusable provenance helpers for reproducible experiment outputs."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional


DEFAULT_SOURCE_FILES = (
    "src/circuits/generator_v2.py",
    "src/circuits/real_benchmarks.py",
    "src/optimisation/base.py",
    "src/optimisation/ceiling_aware.py",
    "src/optimisation/phase1/greedy.py",
    "src/optimisation/phase1/random_local_search.py",
    "src/optimisation/phase1/simulated_annealing.py",
    "src/optimisation/phase1/genetic_algorithm.py",
    "src/optimisation/phase1/wire_traversal.py",
    "src/optimisation/phase2/commutation_rewriter.py",
    "analysis/structural_ceiling.py",
)


def file_sha256(path: Path) -> str:
    """Return the SHA-256 hash for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)  # 64 KB chunks to reduce memory pressure
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(project_root: Path) -> Optional[str]:
    """Return the current git commit hash, if available."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None

    commit = completed.stdout.strip()
    return commit if completed.returncode == 0 and commit else None


def package_versions(packages: Iterable[str] = ("qiskit", "numpy", "scipy", "pandas")) -> Dict[str, str]:
    """Collect versions for important runtime packages."""
    versions: Dict[str, str] = {}
    for package in packages:
        try:
            module = __import__(package)
            versions[package] = str(getattr(module, "__version__", "unknown"))
        except ImportError:
            versions[package] = "not installed"
    return versions


def source_hashes(project_root: Path, files: Iterable[str] = DEFAULT_SOURCE_FILES) -> Dict[str, str]:
    """Hash source files that materially affect experiment outputs."""
    hashes: Dict[str, str] = {}
    for relative in files:
        path = project_root / relative
        if path.exists():
            hashes[relative] = file_sha256(path)
    return hashes


def optimizer_config(optimizer: Any) -> Dict[str, Any]:
    """Extract stable, serializable optimizer configuration."""
    fields = (
        "fidelity_threshold",
        "success_reduction",
        "max_iterations",
        "neighborhood_size",
        "initial_temp",
        "cooling_rate",
        "population_size",
        "generations",
        "mutation_rate",
    )
    config: Dict[str, Any] = {"class": optimizer.__class__.__name__}
    for field in fields:
        if hasattr(optimizer, field):
            value = getattr(optimizer, field)
            if isinstance(value, (str, int, float, bool)) or value is None:
                config[field] = value
    return config


def json_dumps_stable(value: Mapping[str, Any]) -> str:
    """Serialize metadata in a stable compact form for CSV columns."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def run_metadata(project_root: Path, script_path: Path, version: str, run_id: str,
                 source_files: Iterable[str] = DEFAULT_SOURCE_FILES) -> Dict[str, Any]:
    """Build run-level metadata shared by all records from an experiment."""
    script_relative = script_path.relative_to(project_root).as_posix()
    hashes = source_hashes(project_root, source_files)
    if script_path.exists():
        hashes[script_relative] = file_sha256(script_path)

    return {
        "version": version,
        "run_id": run_id,
        "git_commit": git_commit(project_root),
        "python_version": sys.version,
        "platform": platform.platform(),
        "package_versions": package_versions(),
        "source_hashes": hashes,
    }


def record_provenance_columns(metadata: Mapping[str, Any], optimizer: Any,
                              circuit_family: str,
                              fidelity_metric: str = "average_gate_fidelity") -> Dict[str, Any]:
    """Return flat columns suitable for appending to a raw result record."""
    opt_config = optimizer_config(optimizer)
    source = metadata.get("source_hashes", {})
    packages = metadata.get("package_versions", {})
    return {
        "run_id": metadata.get("run_id"),
        "git_commit": metadata.get("git_commit"),
        "python_version": metadata.get("python_version"),
        "platform": metadata.get("platform"),
        "package_versions_json": json_dumps_stable(packages),
        "source_hashes_json": json_dumps_stable(source),
        "optimizer_class": opt_config["class"],
        "optimizer_config_json": json_dumps_stable(opt_config),
        "success_threshold": opt_config.get("success_reduction"),
        "fidelity_threshold": opt_config.get("fidelity_threshold"),
        "fidelity_metric": fidelity_metric,
        "circuit_family": circuit_family,
    }
