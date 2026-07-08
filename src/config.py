"""Central project paths and path helpers.

This module resolves the project root relative to this file's location,
so no absolute or hard-coded paths need to live in analysis scripts.
"""

from __future__ import annotations

import os
from pathlib import Path

# Project layout (relative to this file in <repo>/src)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_ROOT = PROJECT_ROOT / "data"
ANALYSIS_DIR = PROJECT_ROOT / "analysis"
FIGURES_DIR = ANALYSIS_DIR / "figures"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SRC_DIR = PROJECT_ROOT / "src"


def latest_csv(directory: Path | str, prefix: str) -> Path:
    """Return the most recent CSV in *directory* whose name starts with *prefix*.

    Prefers files containing ``_full_`` over ``_smoke_`` so fresh full runs are
    picked up automatically.  If no CSV is found, returns a non-existent path
    with the expected suffix so callers can emit a clean "not found" message.
    """
    dirp = Path(directory)
    candidates = sorted(dirp.glob(f"{prefix}*.csv"))
    if not candidates:
        return dirp / f"{prefix}_NOT_FOUND.csv"
    full_runs = [f for f in candidates if "_full_" in f.name]
    return (full_runs or candidates)[-1]
