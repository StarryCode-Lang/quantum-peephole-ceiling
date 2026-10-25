"""Build the v16 release chain: the corrected-engine era's pinned artifacts.

The prepaper release manifest predates the v12+ package era by design (its
generator covers canonical CSV datasets through v10 only).  Each package era
since then is released through its readiness verdict in ``release/``; the
drift register defers the owner's re-pin choice to exactly this artifact.
This script writes ``release/v16_release_chain.json`` — the SHA-256-pinned
inventory of every corrected-engine (post successor-bug fix) artifact that
the v16 verdict depends on — plus per-entry provenance, and refuses to run
on a dirty worktree so the pinned git commit is meaningful.

Pinned:
- the four v16 data packages (every file, hashed individually),
- the v16 readiness verdict,
- the re-certification package receipt (engine source hashes),
- the producing engine source files,
- the E65 raised-contract campaign JSONL (in-flight companion).

Usage:
    python scripts/build_v16_release_chain.py            # requires clean tree
    python scripts/build_v16_release_chain.py --allow-dirty
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.provenance import engine_source_hashes  # noqa: E402

CHAIN = ROOT / "release" / "v16_release_chain.json"

PACKAGES = {
    "data/v16/e45_full_development": [
        "certificates.jsonl",
        "config_summaries.json",
        "grid_results.csv",
        "normalization_manifest.csv",
        "protocol.json",
        "receipt.json",
        "selection.json",
    ],
    "data/v16/e45_idastar_escape": [
        "certificates.jsonl",
        "config_summaries.json",
        "grid_results.csv",
        "normalization_manifest.csv",
        "protocol.json",
        "receipt.json",
        "selection.json",
    ],
    "data/v16/e46_window_landscape": [
        "escape_certificates.jsonl",
        "input_summaries.csv",
        "protocol.json",
        "receipt.json",
        "window_results.csv",
    ],
    "data/v16/e45_landscape_integration": [
        "classification_complete.csv",
        "derivations.jsonl",
        "protocol.json",
        "receipt.json",
    ],
}
SINGLE_FILES = [
    "release/v16_readiness_verdict.json",
    "docs/review/science_boost/2026-10-25_engine_successor_fix/receipt.json",
    "docs/review/science_boost/2026-10-25_bounded_exactification/cells.jsonl",
]
EXPERIMENT_ID = "V16_RELEASE_CHAIN_V1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> dict:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"], cwd=str(ROOT), capture_output=True, text=True, check=True
        ).stdout.strip()
    )
    return {"commit": commit, "dirty": dirty}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    git_state = git_head()
    if git_state["dirty"] and not args.allow_dirty:
        raise SystemExit("V16_CHAIN_DIRTY_TREE: commit (or pass --allow-dirty to pin a dirty HEAD)")

    entries: dict[str, dict] = {}
    missing = []
    for package, files in PACKAGES.items():
        for name in files:
            rel = f"{package}/{name}"
            path = ROOT / rel
            if not path.is_file():
                missing.append(rel)
                continue
            entries[rel] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    for rel in SINGLE_FILES:
        path = ROOT / rel
        if not path.is_file():
            missing.append(rel)
            continue
        entries[rel] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    if missing:
        raise SystemExit(f"V16_CHAIN_MISSING_FILES:{missing}")

    chain = {
        "experiment_id": EXPERIMENT_ID,
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "git": git_state,
        "engine_source_sha256": engine_source_hashes(ROOT),
        "packages": {pkg: sorted(files) for pkg, files in PACKAGES.items()},
        "entries": entries,
        "entry_count": len(entries),
        "policy": {
            "frozen_predecessors": "data/v14, data/v15, release/v14_readiness_verdict.json, release/v15_readiness_verdict.json remain untouched",
            "verifier": "python scripts/verify_v16_release_chain.py exits 0",
            "scope": "corrected-engine era artifacts only; the prepaper manifest (v10 era) is unchanged by design",
        },
    }
    CHAIN.write_text(json.dumps(chain, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "entries": len(entries), "git_commit": git_state["commit"][:12]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
