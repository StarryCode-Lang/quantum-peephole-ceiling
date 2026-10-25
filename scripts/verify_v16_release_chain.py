"""Fail-closed verifier for release/v16_release_chain.json.

Re-hashes every pinned entry, checks the engine source hashes and the git
commit recorded at build time, and exits non-zero on any mismatch.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.provenance import engine_source_hashes  # noqa: E402

CHAIN = ROOT / "release" / "v16_release_chain.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    chain = json.loads(CHAIN.read_text(encoding="utf-8"))
    failures = []
    for rel, pinned in chain["entries"].items():
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"missing:{rel}")
            continue
        if sha256(path) != pinned["sha256"]:
            failures.append(f"hash_drift:{rel}")
    if chain["engine_source_sha256"] != engine_source_hashes(ROOT):
        failures.append("engine_source_drift")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True, check=True
    ).stdout.strip()
    if chain["git"]["commit"] != commit:
        # HEAD may have moved forward since the chain was built; require the
        # pinned commit to be an ancestor of (or equal to) HEAD
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", chain["git"]["commit"], "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if ancestor.returncode != 0:
            failures.append(f"git_commit_not_ancestor:{chain['git']['commit'][:12]}")
    print(
        json.dumps(
            {
                "experiment_id": chain["experiment_id"],
                "entries": chain["entry_count"],
                "failures": failures,
                "status": "PASS" if not failures else "FAIL",
            },
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
