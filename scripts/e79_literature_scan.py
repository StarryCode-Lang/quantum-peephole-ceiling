"""E79: 2026-10-29 literature and ecosystem scan (round 19).

Same contract as E68/E74/E76: arXiv Atom API with field-qualified queries plus
GitHub REST, no LLM, no synthesis.  The query set is retargeted at round 19's
subject -- whether the completeness threshold of a fixed-length rewrite library
is a *width* effect or the shortest non-trivial relation (the "girth") of the
fragment's group, and what the field already knows about that quantity.

Run from the repo root:
    python scripts/e79_literature_scan.py
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from e68_literature_scan import _github_token, repo_meta, repo_text_corpus  # noqa: E402
from e74_literature_scan import arxiv_fielded  # noqa: E402

OUT = ROOT / "docs" / "review" / "science_boost" / "2026-10-29_literature_scan"
MIN_YEAR = 2023

QUERIES = [
    # round-19 subject: shortest relations / girth / word problem in Clifford groups
    'abs:"Clifford group" AND abs:"shortest" AND abs:"word"',
    'abs:"girth" AND abs:"Cayley graph" AND abs:"generators"',
    'abs:"word problem" AND abs:"Clifford"',
    'abs:"Clifford" AND abs:"presentation" AND abs:"relation"',
    'abs:"normal form" AND abs:"Clifford" AND abs:"circuit"',
    # rewrite-library completeness and its limits
    'abs:"rewrite" AND abs:"complete" AND abs:"quantum circuit"',
    'abs:"template" AND abs:"matching" AND abs:"quantum circuit" AND abs:"optimal"',
    'abs:"equality saturation" AND abs:"quantum"',
    'abs:"peephole" AND abs:"quantum"',
    'abs:"circuit optimization" AND abs:"lower bound" AND abs:"gate count"',
    # landscape / average case / hardness
    'abs:"local optimum" AND abs:"circuit" AND abs:"synthesis"',
    'abs:"barrier" AND abs:"optimization landscape" AND abs:"circuit"',
    'abs:"hardness" AND abs:"Clifford" AND abs:"synthesis"',
    # LLM / RL / agentic compilers (standing competitive track)
    'abs:"large language model" AND abs:"quantum circuit" AND abs:"compiler"',
    'abs:"reinforcement learning" AND abs:"quantum circuit" AND abs:"optimization"',
    'abs:"agent" AND abs:"compiler" AND abs:"verif"',
    # hardware co-design and representation
    'abs:"representation" AND abs:"transpiler" AND abs:"quantum"',
    'abs:"gate set" AND abs:"dependent" AND abs:"complexity" AND abs:"quantum"',
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
    "CQCL/tket",
    "quartz-tools/quartz",
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    token = _github_token()
    records: dict[str, dict[str, object]] = {}
    query_log: list[dict[str, object]] = []
    for query in QUERIES:
        try:
            hits = arxiv_fielded(query, max_results=40)
        except Exception as exc:  # noqa: BLE001
            query_log.append({"query": query, "status": f"ERROR:{type(exc).__name__}", "hits": 0})
            continue
        kept = 0
        for hit in hits:
            published = str(hit.get("published", ""))
            if published[:4].isdigit() and int(published[:4]) < MIN_YEAR:
                continue
            records.setdefault(str(hit["id"]), hit)
            kept += 1
        query_log.append({"query": query, "status": "OK", "hits": kept})
        time.sleep(3.0)

    repos: list[dict[str, object]] = []
    for name in REPOS:
        meta = repo_meta(name, token)
        meta["requested"] = name
        repos.append(meta)
        time.sleep(0.5)

    corpus = repo_text_corpus()
    for record in records.values():
        record["in_repo_corpus"] = str(record["id"]) in corpus

    rows = sorted(records.values(), key=lambda r: str(r.get("published", "")), reverse=True)
    with (OUT / "arxiv_records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "published", "title", "primary_category", "in_repo_corpus", "summary"],
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    with (OUT / "github_repos.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["requested", "name", "status", "stars", "pushed_at", "latest_release", "release_date", "url"],
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in repos:
            writer.writerow(row)
    (OUT / "arxiv_queries.json").write_text(json.dumps(query_log, indent=2), encoding="utf-8")

    uncovered = [row["id"] for row in rows if not row["in_repo_corpus"]]
    summary = {
        "as_of": "2026-10-29",
        "channels": {
            "arxiv_atom_api": "OK",
            "github_rest": "OK" if any(r.get("status") == "OK" for r in repos) else "DEGRADED",
            "tavily": "UNAVAILABLE (no TAVILY_API_KEY, package not installed)",
            "exa": "UNAVAILABLE (no MCP server, no EXA_API_KEY)",
            "multi_search_engine": "UNAVAILABLE (no key)",
            "arxiv_reader": "UNAVAILABLE (no LLM key)",
            "citation_manager": "SUBSTITUTED by in-repo text-coverage check",
        },
        "queries": len(QUERIES),
        "records": len(rows),
        "records_2026": sum(1 for row in rows if str(row.get("published", "")).startswith("2026")),
        "uncovered_ids": uncovered,
        "uncovered_count": len(uncovered),
        "repos": {row.get("requested"): row.get("status") for row in repos},
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
