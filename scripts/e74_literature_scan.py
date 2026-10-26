"""E74: 2026-10-27 literature and ecosystem scan (round 17).

Same dumb contract as E68: arXiv Atom API + GitHub REST, no LLM, no synthesis.
The query set is retargeted at round 17's findings -- rule-library completeness,
the order/content split, span-indexed reachability, and single-qubit merging.

Run from the repo root:
    python scripts/e74_literature_scan.py
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

import re  # noqa: E402
import time  # noqa: E402
import urllib.parse  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402

from e68_literature_scan import (  # noqa: E402
    _get,
    _github_token,
    repo_meta,
    repo_text_corpus,
)

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def arxiv_fielded(search_query: str, max_results: int = 40) -> list[dict[str, object]]:
    """arXiv API with an explicit fielded ``search_query``.

    ``e68`` wraps every query in ``all:``, which turns a phrase into an AND over
    tokens and drowns the relevant hits in date order.  Here the caller supplies
    the field operators (``abs:"..."``) directly.
    """

    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    root = ET.fromstring(_get(url))
    out: list[dict[str, object]] = []
    for entry in root.findall(f"{ATOM}entry"):
        aid = (entry.findtext(f"{ATOM}id") or "").rsplit("/", 1)[-1]
        published = entry.findtext(f"{ATOM}published") or ""
        primary = entry.find(f"{ARXIV_NS}primary_category")
        out.append(
            {
                "id": re.sub(r"v\d+$", "", aid),
                "title": " ".join((entry.findtext(f"{ATOM}title") or "").split()),
                "published": published[:10],
                "year": int(published[:4]) if published[:4].isdigit() else 0,
                "primary": primary.get("term") if primary is not None else "",
                "summary": " ".join((entry.findtext(f"{ATOM}summary") or "").split())[:900],
            }
        )
    return out

OUT = ROOT / "docs" / "review" / "science_boost" / "2026-10-27_literature_scan"
MIN_YEAR = 2023

QUERIES = [
    'abs:"peephole" AND abs:"quantum"',
    'abs:"completeness" AND abs:"rewrite" AND abs:"circuit"',
    'abs:"complete rule set" AND abs:"Clifford"',
    'abs:"superoptimization" AND abs:"quantum"',
    'abs:"quantum circuit" AND abs:"rewriting" AND abs:"termination"',
    'abs:"commutation" AND abs:"circuit optimization"',
    'abs:"e-graph" AND abs:"quantum"',
    'abs:"single-qubit" AND abs:"merging" AND abs:"circuit"',
    'abs:"circuit optimization" AND abs:"lower bound" AND abs:"gate count"',
    'abs:"transpiler" AND abs:"pass" AND abs:"ordering"',
    'abs:"quantum compiler" AND abs:"benchmark"',
    'abs:"equivalence checking" AND abs:"quantum circuit"',
    'abs:"ZX-calculus" AND abs:"optimization"',
    'abs:"phase polynomial" AND abs:"synthesis"',
    'abs:"circuit synthesis" AND abs:"NP-hard"',
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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    records: dict[str, dict[str, object]] = {}
    per_query: dict[str, int] = {}
    for index, query in enumerate(QUERIES, 1):
        try:
            hits = arxiv_fielded(query)
            time.sleep(3)
        except Exception as exc:  # noqa: BLE001
            print(f"[{index}/{len(QUERIES)}] FAIL {query} ({exc})", file=sys.stderr)
            per_query[query] = -1
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
    gaps.sort(key=lambda item: item["published"], reverse=True)

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
        json.dumps({"queries": per_query, "unique_records": len(records)}, indent=2), encoding="utf-8"
    )
    (OUT / "coverage_gaps.json").write_text(
        json.dumps({"uncovered": len(gaps), "records": len(records), "items": gaps}, indent=2), encoding="utf-8"
    )
    (OUT / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": "E74_LITERATURE_SCAN_2026_10_27",
                "started": started,
                "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "channels": {
                    "arxiv_atom_api": "OK",
                    "github_rest": "OK (authenticated)" if token else "OK (anonymous)",
                    "tavily": "UNAVAILABLE (no API key, package absent)",
                    "exa": "UNAVAILABLE (no MCP server configured)",
                    "multi-search-engine": "UNAVAILABLE (no search API key)",
                    "arxiv-reader": "UNAVAILABLE (no LLM key)",
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
    print(json.dumps({"unique_records": len(records), "uncovered": len(gaps)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
