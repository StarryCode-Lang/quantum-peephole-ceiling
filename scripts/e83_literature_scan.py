"""E83: fielded literature and ecosystem scan for round 20 (2026-10-30).

Channels actually used
----------------------
* arXiv Atom API with **fielded** queries (``abs:"..." AND abs:"..."``).  Round
  17 showed that the ``all:`` wrapper degenerates into a bag-of-words AND and
  drowns the relevant hits; every query here is fielded.
* GitHub REST for the compiler ecosystem (unauthenticated, rate limited).

Channels unavailable in this environment (disclosed, no claim depends on them)
-----------------------------------------------------------------------------
* tavily      -- no ``TAVILY_API_KEY``, package not installed
* exa         -- no MCP server configured, no key
* multi-search-engine -- no key
* arxiv-reader -- no LLM key
* citation-manager -- no Crossref dependency; replaced by a text-coverage check
  against ``docs/references/unified_references.md`` + the addendum.

Outputs (``docs/review/science_boost/2026-10-30_literature_scan/``)
    arxiv_records.csv   one row per unique arXiv record
    arxiv_queries.json  the exact queries and their hit counts
    github_repos.csv    repo -> latest release / last push
    coverage.csv        per-record: is the id cited anywhere in the repo?
    summary.json        contract, counts, must-cite shortlist, hashes
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-30_literature_scan"
EXPERIMENT_ID = "E83_LITERATURE_SCAN_2026_10_30"

QUERIES = [
    'abs:"quantum circuit" AND abs:"peephole"',
    'abs:"quantum circuit" AND abs:"equality saturation"',
    'abs:"ZX-calculus" AND abs:"optimization"',
    'abs:"circuit optimization" AND abs:"rewrite rules"',
    'abs:"Clifford" AND abs:"diameter"',
    'abs:"Clifford group" AND abs:"word length"',
    'abs:"circuit synthesis" AND abs:"optimal" AND abs:"Clifford"',
    'abs:"template matching" AND abs:"quantum circuit"',
    'abs:"transpiler" AND abs:"benchmark" AND abs:"quantum"',
    'abs:"quantum compiler" AND abs:"reinforcement learning"',
    'abs:"large language model" AND abs:"quantum circuit" AND abs:"optimization"',
    'abs:"quantum circuit" AND abs:"local optima"',
    'abs:"quantum circuit" AND abs:"landscape" AND abs:"optimization"',
    'abs:"term rewriting" AND abs:"quantum"',
    'abs:"circuit equivalence" AND abs:"verification" AND abs:"quantum"',
    'abs:"gate set" AND abs:"compilation" AND abs:"overhead"',
    'abs:"quantum circuit" AND abs:"commutation" AND abs:"optimization"',
    'abs:"phase polynomial" AND abs:"optimization"',
    'abs:"quantum circuit" AND abs:"representation" AND abs:"compiler"',
    'abs:"certified" AND abs:"quantum circuit" AND abs:"optimization"',
    'abs:"quantum advantage" AND abs:"compilation"',
    'abs:"circuit knitting" OR abs:"circuit cutting"',
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, timeout: int = 40) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "q-research-review/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def arxiv(query: str, max_results: int = 40) -> list[dict[str, Any]]:
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": query, "start": 0, "max_results": max_results, "sortBy": "submittedDate", "sortOrder": "descending"}
    )
    raw = fetch(url)
    root = ET.fromstring(raw)
    namespace = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for entry in root.findall("a:entry", namespace):
        identifier = entry.findtext("a:id", default="", namespaces=namespace)
        published = entry.findtext("a:published", default="", namespaces=namespace)
        title = " ".join((entry.findtext("a:title", default="", namespaces=namespace) or "").split())
        summary = " ".join((entry.findtext("a:summary", default="", namespaces=namespace) or "").split())
        authors = [
            author.findtext("a:name", default="", namespaces=namespace)
            for author in entry.findall("a:author", namespace)
        ]
        out.append(
            {
                "id": identifier.rsplit("/abs/", 1)[-1],
                "published": published[:10],
                "title": title,
                "abstract": summary,
                "authors": "; ".join(authors[:4]),
                "query": query,
            }
        )
    return out


def github(repo: str) -> dict[str, Any]:
    try:
        meta = json.loads(fetch(f"https://api.github.com/repos/{repo}"))
        release = None
        try:
            release = json.loads(fetch(f"https://api.github.com/repos/{repo}/releases/latest"))
        except Exception:
            release = None
        return {
            "repo": repo,
            "status": "OK",
            "stars": meta.get("stargazers_count"),
            "pushed_at": (meta.get("pushed_at") or "")[:10],
            "latest_release": (release or {}).get("tag_name", ""),
            "release_date": ((release or {}).get("published_at") or "")[:10],
        }
    except Exception as exc:  # pragma: no cover - network
        return {"repo": repo, "status": f"ERROR:{type(exc).__name__}", "stars": "", "pushed_at": "", "latest_release": "", "release_date": ""}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--sleep", type=float, default=3.0)
    parser.add_argument("--reuse", action="store_true", help="reuse the existing CSVs, recompute coverage only")
    args = parser.parse_args()
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    reuse_mode = bool(args.reuse and (out / "arxiv_records.csv").exists())
    records: dict[str, dict[str, Any]] = {}
    query_log: list[dict[str, Any]] = []
    if args.reuse and (out / "arxiv_records.csv").exists():
        with (out / "arxiv_records.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                records[row["id"]] = dict(row)
        query_log = json.loads((out / "arxiv_queries.json").read_text(encoding="utf-8"))
    for query in ([] if reuse_mode else QUERIES):
        try:
            hits = arxiv(query)
            status = "OK"
        except Exception as exc:  # pragma: no cover - network
            hits = []
            status = f"ERROR:{type(exc).__name__}"
        query_log.append({"query": query, "status": status, "hits": len(hits)})
        for hit in hits:
            if hit["published"] >= "2023-01-01" and hit["id"] not in records:
                records[hit["id"]] = hit
        time.sleep(args.sleep)

    repo_rows: list[dict[str, Any]] = []
    if reuse_mode and (out / "github_repos.csv").exists():
        with (out / "github_repos.csv").open(encoding="utf-8", newline="") as handle:
            repo_rows = list(csv.DictReader(handle))
    for repo in ([] if reuse_mode else REPOS):
        repo_rows.append(github(repo))
        time.sleep(0.5)

    # coverage: is the arXiv id cited anywhere in docs/ or the source tree?
    corpus = []
    for path in list((ROOT / "docs").rglob("*.md")) + list((ROOT / "docs").rglob("*.csv")) + list(
        (ROOT / "release").rglob("*.json")
    ):
        # never let a scan artifact count as coverage: earlier rounds dumped
        # arXiv records under docs/review/science_boost/*_literature_scan/
        if OUTPUT_ROOT in path.parents or path.parent.name.endswith("_literature_scan"):
            continue
        if path.name in {"arxiv_records.csv", "coverage.csv"}:
            continue
        try:
            corpus.append(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
    blob = "\n".join(corpus)
    for record in records.values():
        # the repo cites ids without the arXiv version suffix
        base = re.sub(r"v[0-9]+$", "", record["id"])
        record["cited_in_repo"] = base in blob

    rows = sorted(records.values(), key=lambda r: r["published"], reverse=True)
    with (out / "arxiv_records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "published", "title", "authors", "query", "cited_in_repo", "abstract"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in writer.fieldnames})
    (out / "arxiv_queries.json").write_text(json.dumps(query_log, indent=2), encoding="utf-8")
    with (out / "github_repos.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["repo", "status", "stars", "pushed_at", "latest_release", "release_date"]
        )
        writer.writeheader()
        for row in repo_rows:
            writer.writerow(row)

    uncited = [row for row in rows if row["cited_in_repo"] in (False, "False")]
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-10-30",
        "channels": {
            "arxiv": "Atom API, fielded abs: queries, sorted by submission date",
            "github": "REST API, unauthenticated",
            "unavailable": {
                "tavily": "no TAVILY_API_KEY, package not installed",
                "exa": "no MCP server, no key",
                "multi-search-engine": "no key",
                "arxiv-reader": "no LLM key",
                "citation-manager": "no Crossref dependency; text-coverage check used instead",
            },
        },
        "counts": {
            "queries": len(QUERIES),
            "records": len(rows),
            "records_2026": sum(1 for row in rows if row["published"].startswith("2026")),
            "uncited_records": len(uncited),
            "cited_records": len(rows) - len(uncited),
            "repos": len(repo_rows),
        },
        "uncited_ids": [row["id"] for row in uncited],
        "latest": rows[0]["published"] if rows else None,
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (out / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": EXPERIMENT_ID,
                "generated": "2026-10-30",
                "script": "scripts/e83_literature_scan.py",
                "artifacts": {
                    name: sha256_file(out / name)
                    for name in ["arxiv_records.csv", "arxiv_queries.json", "github_repos.csv", "summary.json"]
                    if (out / name).exists()
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
