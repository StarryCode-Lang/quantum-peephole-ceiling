"""E76: 2026-10-28 literature and ecosystem scan (round 18).

Same dumb contract as E68/E74: arXiv Atom API + GitHub REST, no LLM, no
synthesis.  The query set is retargeted at round 18's subject -- the *price of
completeness*: how the coverage of a fixed-length rewrite library depends on the
source-pattern length, and whether that dependence is a threshold or a slope.

Run from the repo root:
    python scripts/e76_literature_scan.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from e68_literature_scan import _github_token, repo_meta, repo_text_corpus  # noqa: E402
from e74_literature_scan import arxiv_fielded  # noqa: E402

import time  # noqa: E402

OUT = ROOT / "docs" / "review" / "science_boost" / "2026-10-28_literature_scan"
MIN_YEAR = 2023

QUERIES = [
    # the round-18 subject: fixed-length libraries and their coverage
    'abs:"rule set" AND abs:"complete" AND abs:"circuit"',
    'abs:"rewrite system" AND abs:"completeness" AND abs:"quantum"',
    'abs:"Clifford" AND abs:"identity" AND abs:"shortest"',
    'abs:"word problem" AND abs:"Clifford"',
    'abs:"redundancy" AND abs:"removal" AND abs:"quantum circuit"',
    'abs:"peephole" AND abs:"rule"',
    'abs:"template matching" AND abs:"quantum circuit"',
    'abs:"reachability" AND abs:"circuit optimization"',
    'abs:"decidability" AND abs:"quantum"',
    # standing frontier
    'abs:"superoptimization" AND abs:"quantum"',
    'abs:"equality saturation" AND abs:"quantum"',
    'abs:"e-graph" AND abs:"quantum"',
    'abs:"ZX-calculus" AND abs:"optimization"',
    'abs:"phase polynomial" AND abs:"synthesis"',
    'abs:"circuit synthesis" AND abs:"NP-hard"',
    'abs:"lower bound" AND abs:"gate count" AND abs:"Clifford"',
    'abs:"quantum compiler" AND abs:"benchmark"',
    'abs:"transpiler" AND abs:"pass" AND abs:"ordering"',
    'abs:"equivalence checking" AND abs:"quantum circuit"',
    'abs:"large language model" AND abs:"quantum circuit"',
    'abs:"reinforcement learning" AND abs:"quantum compilation"',
    'abs:"token swapping" AND abs:"quantum"',
    'abs:"local optimum" AND abs:"quantum circuit"',
    'abs:"certificate" AND abs:"compiler" AND abs:"quantum"',
]

REPOS = [
    "Qiskit/qiskit",
    "Quantinuum/tket",
    "quantum-compiler/quartz",
    "zxcalc/pyzx",
    "BQSKit/bqskit",
    "munich-quantum-toolkit/qcec",
    "munich-quantum-toolkit/bench",
    "qqq-wisc/tzap",
    "psg-mit/quanto",
    "unitaryfund/mitiq",
]

# Must-cite candidates carried forward from earlier rounds, checked for repo coverage.
CARRIED = [
    "2609.40106",
    "2610.23832",
    "2610.21714",
    "2609.07776",
    "2609.36060",
    "2609.01762",
    "2608.13035",
    "2609.13839",
    "2608.08248",
    "2607.28598",
    "2607.20170",
    "2609.16208",
    "2510.20730",
    "2609.29406",
    "2608.22801",
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    records: dict[str, dict[str, object]] = {}
    per_query: dict[str, int] = {}
    failures = 0
    for index, query in enumerate(QUERIES, 1):
        try:
            hits = arxiv_fielded(query)
            time.sleep(3)
        except Exception as exc:  # noqa: BLE001
            print(f"[{index}/{len(QUERIES)}] FAIL {query} ({exc})", file=sys.stderr)
            per_query[query] = -1
            failures += 1
            continue
        kept = 0
        for record in hits:
            if int(record["year"]) < MIN_YEAR:
                continue
            kept += 1
            records.setdefault(str(record["id"]), record)
        per_query[query] = kept
        print(f"[{index}/{len(QUERIES)}] {kept:3d} kept  {query}")

    token = _github_token()
    repos = [repo_meta(name, token) for name in REPOS]
    for row in repos:
        print(f"  repo {row['repo']:<40} {row['status']:<12} {row['latest_release']}")

    corpus = repo_text_corpus().lower()
    gaps = []
    for aid, record in records.items():
        if aid.lower() in corpus:
            continue
        gaps.append(
            {
                "id": aid,
                "published": record["published"],
                "title": record["title"],
                "primary": record["primary"],
            }
        )
    gaps.sort(key=lambda item: str(item["published"]), reverse=True)

    carried = [
        {"id": aid, "covered": aid.lower() in corpus, "in_records": aid in records}
        for aid in CARRIED
    ]

    with (OUT / "arxiv_records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "published", "year", "primary", "title", "summary"])
        writer.writeheader()
        for record in sorted(records.values(), key=lambda item: str(item["published"]), reverse=True):
            writer.writerow(record)
    with (OUT / "github_repos.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["repo", "status", "pushed_at", "stars", "archived", "latest_release", "open_issues"],
        )
        writer.writeheader()
        for row in repos:
            writer.writerow(row)
    (OUT / "arxiv_queries.json").write_text(
        json.dumps({"queries": per_query, "unique_records": len(records), "failed_queries": failures}, indent=2),
        encoding="utf-8",
    )
    (OUT / "coverage_gaps.json").write_text(
        json.dumps(
            {
                "uncovered": len(gaps),
                "records": len(records),
                "items": gaps,
                "carried_must_cites": carried,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (OUT / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": "E76_LITERATURE_SCAN_2026_10_28",
                "started": started,
                "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "channels": {
                    "arxiv_atom_api": "OK" if failures == 0 else f"DEGRADED ({failures} failed queries)",
                    "github_rest": "OK (authenticated)" if token else "OK (anonymous)",
                    "tavily": "UNAVAILABLE (no API key, package absent)",
                    "exa": "UNAVAILABLE (no MCP server configured)",
                    "multi-search-engine": "UNAVAILABLE (no search API key)",
                    "arxiv-reader": "UNAVAILABLE (no LLM key)",
                    "citation-manager": "UNAVAILABLE (no Crossref dependency); replaced by text-coverage audit",
                },
                "min_year": MIN_YEAR,
                "queries": len(QUERIES),
                "unique_records": len(records),
                "repos": len(REPOS),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"unique_records": len(records), "uncovered": len(gaps), "failed_queries": failures}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
