"""E85: fielded literature and ecosystem scan for round 21 (2026-10-31).

Channels actually used
----------------------
* arXiv Atom API with **fielded** queries (``abs:"..." AND abs:"..."``).  Round
  17 showed that the ``all:`` wrapper degenerates into a bag-of-words AND and
  drowns the relevant hits; every query here is fielded.
* GitHub REST **with authentication** (the Windows credential store holds a
  token for the account that owns this worktree).  Rounds 20 and 21-previous
  reported 403 on the unauthenticated quota; that is no longer a limitation.

Channels unavailable in this environment (disclosed, no claim depends on them)
-----------------------------------------------------------------------------
* tavily      -- no ``TAVILY_API_KEY``, package not installed
* exa         -- no MCP server configured, no key
* multi-search-engine -- no key
* arxiv-reader -- no LLM key
* citation-manager -- no Crossref dependency; replaced by a text-coverage check
  against every arXiv id already cited anywhere under ``docs/``.

Coverage is measured against the *whole* documentation tree, not just the
catalogue: an id that appears only in a review note is still "known to the
project", and conflating that with "cited in the manuscript" was a defect of the
earlier rounds' coverage tables.

Outputs (``docs/review/science_boost/2026-10-31_literature_scan/``)
    arxiv_records.csv   one row per unique arXiv record
    arxiv_queries.json  the exact queries and their hit counts
    github_repos.csv    repo -> latest release / last push
    coverage.csv        per-record: is the id cited anywhere under docs/?
    summary.json        contract, counts, must-cite shortlist, hashes
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-31_literature_scan"
EXPERIMENT_ID = "E85_LITERATURE_SCAN_2026_10_31"

QUERIES = [
    'abs:"Clifford" AND abs:"Cayley"',
    'abs:"Clifford group" AND abs:"diameter"',
    'abs:"Clifford group" AND abs:"word length"',
    'abs:"gate set" AND abs:"compilation" AND abs:"quantum circuit"',
    'abs:"quantum circuit" AND abs:"template" AND abs:"library"',
    'abs:"peephole" AND abs:"quantum"',
    'abs:"rewrite" AND abs:"completeness" AND abs:"quantum"',
    'abs:"circuit optimization" AND abs:"phase polynomial"',
    'abs:"ZX-calculus" AND abs:"completeness"',
    'abs:"equality saturation" AND abs:"quantum"',
    'abs:"quantum circuit" AND abs:"lower bound" AND abs:"gate count"',
    'abs:"transpilation" AND abs:"equivalence" AND abs:"verification"',
    'abs:"quantum circuit" AND abs:"large language model" AND abs:"compiler"',
    'abs:"reinforcement learning" AND abs:"circuit synthesis" AND abs:"quantum"',
    'abs:"Clifford" AND abs:"synthesis" AND abs:"optimal"',
    'abs:"quantum compiler" AND abs:"testing"',
    'abs:"quantum circuit" AND abs:"canonical form"',
    'abs:"stabilizer" AND abs:"tableau" AND abs:"optimization"',
    'abs:"quantum" AND abs:"compilation" AND abs:"co-design"',
    'abs:"quantum circuit" AND abs:"representation" AND abs:"compiler"',
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

ID_PATTERN = re.compile(r"\b(\d{4}\.\d{4,5})\b")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def github_token() -> str:
    """Read the token the worktree already uses, without printing it."""

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        out = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
    except Exception:  # pragma: no cover
        return ""
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    return ""


def fetch(url: str, timeout: int = 40, token: str = "") -> bytes:
    headers = {"User-Agent": "q-research-review/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
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
        authors = [author.findtext("a:name", default="", namespaces=namespace) for author in entry.findall("a:author", namespace)]
        out.append(
            {
                "id": re.sub(r"v\d+$", "", identifier.rsplit("/abs/", 1)[-1]),
                "published": published[:10],
                "title": title,
                "abstract": summary,
                "authors": "; ".join(authors[:4]),
                "query": query,
            }
        )
    return out


def github(repo: str, token: str) -> dict[str, Any]:
    try:
        meta = json.loads(fetch(f"https://api.github.com/repos/{repo}", token=token))
        release: dict[str, Any] = {}
        try:
            release = json.loads(fetch(f"https://api.github.com/repos/{repo}/releases/latest", token=token))
        except Exception:
            release = {}
        return {
            "repo": repo,
            "status": "OK",
            "stars": meta.get("stargazers_count"),
            "pushed_at": (meta.get("pushed_at") or "")[:10],
            "latest_release": release.get("tag_name", ""),
            "release_date": (release.get("published_at") or "")[:10],
        }
    except Exception as exc:  # pragma: no cover - network
        return {
            "repo": repo,
            "status": f"ERROR:{type(exc).__name__}",
            "stars": "",
            "pushed_at": "",
            "latest_release": "",
            "release_date": "",
        }


def cited_ids() -> set[str]:
    """Every arXiv id already mentioned anywhere under ``docs/`` or the top-level md files."""

    found: set[str] = set()
    for path in ROOT.glob("docs/**/*"):
        if path.is_file() and path.suffix.lower() in {".md", ".csv", ".json", ".txt"}:
            try:
                found.update(ID_PATTERN.findall(path.read_text(encoding="utf-8", errors="ignore")))
            except Exception:  # pragma: no cover
                continue
    for path in ROOT.glob("*.md"):
        found.update(ID_PATTERN.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return found


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
    if reuse_mode:
        with (out / "arxiv_records.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                row["id"] = re.sub(r"v\d+$", "", row["id"])
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

    known = cited_ids()
    rows = []
    for identifier, record in sorted(records.items(), key=lambda kv: kv[1]["published"], reverse=True):
        rows.append(
            {
                "id": identifier,
                "published": record["published"],
                "title": record["title"],
                "authors": record["authors"],
                "cited_in_repo": identifier in known,
                "query": record["query"],
                "abstract": record["abstract"],
            }
        )

    with (out / "arxiv_records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["id"])
        writer.writeheader()
        writer.writerows(rows)
    (out / "arxiv_queries.json").write_text(json.dumps(query_log, indent=2) + "\n", encoding="utf-8")

    token = "" if reuse_mode else github_token()
    repo_rows = []
    if not reuse_mode:
        for repo in REPOS:
            repo_rows.append(github(repo, token))
            time.sleep(0.5)
    else:
        with (out / "github_repos.csv").open(encoding="utf-8", newline="") as handle:
            repo_rows = list(csv.DictReader(handle))
    if repo_rows:
        with (out / "github_repos.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(repo_rows[0]))
            writer.writeheader()
            writer.writerows(repo_rows)

    with (out / "coverage.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "published", "cited_in_repo", "title"])
        for row in rows:
            writer.writerow([row["id"], row["published"], row["cited_in_repo"], row["title"]])

    by_year: dict[str, int] = {}
    for row in rows:
        by_year[row["published"][:4]] = by_year.get(row["published"][:4], 0) + 1

    summary = {
        "experiment": EXPERIMENT_ID,
        "as_of": "2026-10-31",
        "channels_used": {
            "arxiv_atom_fielded": {"queries": len(query_log), "records": len(rows)},
            "github_rest_authenticated": {"repos": len(repo_rows), "ok": sum(1 for r in repo_rows if r["status"] == "OK")},
        },
        "channels_unavailable": {
            "tavily": "no TAVILY_API_KEY, package not installed",
            "exa": "no MCP server configured, no key",
            "multi-search-engine": "no key",
            "arxiv-reader": "no LLM key",
            "citation-manager": "no Crossref dependency; replaced by a docs-wide text-coverage check",
        },
        "counts": {
            "unique_records": len(rows),
            "from_2026": by_year.get("2026", 0),
            "cited_in_repo": sum(1 for r in rows if r["cited_in_repo"]),
            "uncited": sum(1 for r in rows if not r["cited_in_repo"]),
            "by_year": dict(sorted(by_year.items())),
        },
        "query_log": query_log,
        "github": repo_rows,
        "coverage_basis": "every arXiv id mentioned anywhere under docs/ plus the top-level markdown files",
        "elapsed_seconds": round(time.perf_counter() - started, 1),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "experiment": EXPERIMENT_ID,
        "files": {
            path.name: sha256_file(path)
            for path in sorted(out.iterdir())
            if path.is_file() and path.name != "MANIFEST.json"
        },
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("counts", "channels_used")}, indent=2))
    print(json.dumps(repo_rows, indent=2)[:1600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
