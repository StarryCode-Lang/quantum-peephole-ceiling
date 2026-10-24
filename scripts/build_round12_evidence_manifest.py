"""Build self-describing SHA-256 manifests for the round-12 evidence packages.

These packages are review-grade and deliberately NOT added to
``release/release_manifest.json`` (that would create a new drift entry before
the release re-pin decision).  The local manifest makes each package
self-verifying without touching the frozen release chain.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import time

BASE = pathlib.Path("docs/review/science_boost")
PACKAGES = {
    "2026-10-25_rotation_gap": {
        "experiment_id": "E62_ROTATION_GAP_2026_10_25",
        "script": "scripts/e62_rotation_gap.py",
        "contract": {
            "rule_scope": "e44_core_v1",
            "fragment": "{x, rz, cx}",
            "metric": "rz gate count",
            "read_only": ["data/", "release/", "docs/manuscript/"],
        },
        "inputs": {
            "data/v15/e45_landscape_integration/classification_complete.csv":
                "786b8a0c4fbeb46f7813fcad5874c353402dbc565e8f07ee5d4229ade09826fc"
        },
    },
    "2026-10-25_qiskit_261": {
        "experiment_id": "E63_QISKIT_261_RECHECK_2026_10_25",
        "script": "scripts/e63_qiskit_261_recheck.py",
        "contract": {
            "basis": ["h", "x", "rz", "cx"],
            "levels": [2, 3],
            "seed_transpiler": 42,
            "size_cap": 300,
            "versions": ["qiskit 2.4.1 (repo env)", "qiskit 2.6.1 (isolated uv venv)"],
            "read_only": ["data/", "release/", "docs/manuscript/"],
        },
        "inputs": {},
    },
    "2026-10-25_literature_scan": {
        "experiment_id": "ROUND12_LITERATURE_2026_10_25",
        "script": "scripts/round12_literature_scan.py",
        "contract": {
            "channels_used": [
                "arXiv API (20 structured queries)",
                "GitHub REST (authenticated)",
                "WebSearch (2)",
            ],
            "channels_unavailable": [
                "tavily (no key)",
                "exa (no MCP server)",
                "multi-search-engine (no key)",
                "arxiv-reader (no LLM key)",
                "citation-manager (no Crossref dependency)",
                "github-trending (replaced by authenticated REST)",
            ],
            "read_only": ["data/", "release/", "docs/manuscript/"],
        },
        "inputs": {},
    },
}


def main() -> int:
    e61 = pathlib.Path(
        "docs/review/science_boost/2026-10-24_opt_level_monotonicity/level_sweep.csv"
    )
    if e61.exists():
        PACKAGES["2026-10-25_qiskit_261"]["inputs"][str(e61).replace("\\", "/")] = hashlib.sha256(
            e61.read_bytes()
        ).hexdigest()
    for name, meta in PACKAGES.items():
        directory = BASE / name
        files = {}
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.name != "MANIFEST.json":
                files[path.relative_to(directory).as_posix()] = {
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "bytes": path.stat().st_size,
                }
        payload = {
            "package": name,
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "produced_by": "round 12 science_boost scan (automation 408cca6d)",
            "authority": "review-grade; NOT part of release/release_manifest.json",
            "files": files,
            **meta,
        }
        (directory / "MANIFEST.json").write_text(
            json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8"
        )
        print(f"{name}: {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
