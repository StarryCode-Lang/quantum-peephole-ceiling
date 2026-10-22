"""E51b: open-source ecosystem probe for the 2026-10-21 innovation scan.

Queries the public GitHub REST API for the compilers the project benchmarks or
could benchmark (latest release + activity), plus a search for recently created
quantum-compiler repositories.  Unauthenticated; rate limit is 60 requests/hour,
so the request count is deliberately small.

Output: ``docs/review/science_boost/2026-10-21_literature_scan/github_ecosystem.json``
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "review" / "science_boost" / "2026-10-21_literature_scan" / "github_ecosystem.json"

REPOS = [
    "Qiskit/qiskit",
    "Quantinuum/tket",
    "CQCL/pytket",
    "zxcalc/pyzx",
    "BQSKit/bqskit",
    "quantum-compiler/quartz",
    "qqq-wisc/tzap",
    "mqt/qcec",
    "Qiskit/qiskit-addon-sqd",
    "unitaryfund/mitiq",
]


def api(path: str) -> dict:
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "q-research-scan/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for repo in REPOS:
        record: dict = {"repo": repo}
        try:
            info = api(f"/repos/{repo}")
            record.update(
                {
                    "status": "OK",
                    "pushed_at": info.get("pushed_at"),
                    "stars": info.get("stargazers_count"),
                    "archived": info.get("archived"),
                    "default_branch": info.get("default_branch"),
                }
            )
            try:
                release = api(f"/repos/{repo}/releases/latest")
                record["latest_release"] = release.get("tag_name")
                record["latest_release_at"] = release.get("published_at")
            except Exception as exc:
                record["latest_release"] = f"NONE:{type(exc).__name__}"
        except Exception as exc:
            record["status"] = f"ERROR:{type(exc).__name__}"
        rows.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
        time.sleep(1)

    search = {}
    try:
        payload = api(
            "/search/repositories?q=quantum+compiler+in:name,description&sort=updated&order=desc&per_page=15"
        )
        search["recent_quantum_compiler_repos"] = [
            {
                "full_name": item["full_name"],
                "stars": item["stargazers_count"],
                "pushed_at": item["pushed_at"],
                "description": (item.get("description") or "")[:160],
            }
            for item in payload.get("items", [])
        ]
    except Exception as exc:
        search["error"] = f"{type(exc).__name__}:{exc}"

    OUTPUT.write_text(
        json.dumps({"date": "2026-10-21", "repos": rows, "search": search}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
