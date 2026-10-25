"""E68: 2026-10-26 literature and ecosystem scan for the science-boost review.

Writes a review-grade evidence package (outside ``data/`` and ``release/``):

  docs/review/science_boost/2026-10-26_literature_scan/
    arxiv_records.csv     one row per unique arXiv record (>= 2023)
    arxiv_queries.json    the exact query strings and per-query hit counts
    github_repos.csv      repository metadata for the tracked ecosystem
    coverage_gaps.json    must-cite candidates with no textual coverage in-repo
    MANIFEST.json         sha256 of every produced file + provenance

The scan is deliberately dumb: arXiv Atom API + GitHub REST, no LLM, no
synthesis. Interpretation happens in the round report, not here.

Run from the repo root:
    python scripts/e68_literature_scan.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "review" / "science_boost" / "2026-10-26_literature_scan"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
MIN_YEAR = 2023

# Phrase-quoted queries: arXiv's `all:` field over-quotes, so each phrase is
# kept narrow enough to stay under ~50 hits.
QUERIES = [
    '"peephole optimization" quantum circuit',
    '"equality saturation" quantum',
    '"ZX-calculus" circuit optimization',
    '"phase polynomial" optimization CNOT',
    '"quantum circuit" "rewrite" confluence',
    '"circuit optimization" "representation" dependence',
    '"compiler pass" ordering quantum',
    '"quantum compiler" "reinforcement learning"',
    '"large language model" "quantum circuit" optimization',
    '"template matching" quantum circuit',
    '"CNOT" lower bound synthesis',
    '"T-count" lower bound',
    '"Clifford" synthesis complexity',
    '"quantum circuit" "local optimum" landscape',
    '"token swapping" routing quantum',
    '"quantum circuit" verification equivalence checking',
    '"quantum compiler" testing',
    '"circuit synthesis" "NP-hard"',
    '"quantum advantage" compilation overhead',
    '"hardware-efficient" ansatz transpilation',
    '"quantum circuit" "search space"',
    '"gate set" dependent complexity',
    '"quantum" "circuit rewriting" automation',
    '"benchmark" "quantum compiler" suite',
]

REPOS = [
    "Qiskit/qiskit",
    "Quantinuum/tket",
    "quantum-compiler/quartz",
    "zxcalc/pyzx",
    "BQSKit/bqskit",
    "munich-quantum-toolkit/qcec",
    "qqq-wisc/tzap",
    "CQCL/tket",
    "psg-mit/quanto",
    "inseok/VOQC",
]


def _get(url: str, headers: dict[str, str] | None = None, tries: int = 4) -> bytes:
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "q-research-scan"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code in (429, 503):
                time.sleep(3 * (attempt + 1))
                continue
            raise
        except Exception as exc:  # noqa: BLE001 - network flake, retry
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET failed after {tries} tries: {url} ({last})")


def arxiv_query(query: str, max_results: int = 60) -> list[dict[str, object]]:
    url = (
        "https://export.arxiv.org/api/query?"
        + urllib.parse.urlencode(
            {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
    )
    raw = _get(url)
    root = ET.fromstring(raw)
    out = []
    for entry in root.findall(f"{ATOM}entry"):
        aid = (entry.findtext(f"{ATOM}id") or "").rsplit("/", 1)[-1]
        published = entry.findtext(f"{ATOM}published") or ""
        out.append(
            {
                "id": re.sub(r"v\d+$", "", aid),
                "title": " ".join((entry.findtext(f"{ATOM}title") or "").split()),
                "published": published[:10],
                "year": int(published[:4]) if published[:4].isdigit() else 0,
                "primary": (entry.find(f"{ARXIV}primary_category").get("term")
                            if entry.find(f"{ARXIV}primary_category") is not None else ""),
                "summary": " ".join((entry.findtext(f"{ATOM}summary") or "").split())[:900],
            }
        )
    return out


def _github_token() -> str | None:
    """Reuse the stored git credential instead of asking for a new token."""
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:  # noqa: BLE001
        return None
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    return None


def repo_meta(name: str, token: str | None) -> dict[str, object]:
    headers = {"User-Agent": "q-research-scan", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        data = json.loads(_get(f"https://api.github.com/repos/{name}", headers=headers))
    except Exception as exc:  # noqa: BLE001
        return {"repo": name, "status": f"ERROR:{type(exc).__name__}", "pushed_at": "",
                "stars": "", "archived": "", "latest_release": "", "open_issues": ""}
    release = ""
    try:
        rel = json.loads(
            _get(f"https://api.github.com/repos/{name}/releases/latest", headers=headers)
        )
        release = f"{rel.get('tag_name','')} ({str(rel.get('published_at',''))[:10]})"
    except Exception:  # noqa: BLE001
        release = "none"
    return {
        "repo": data.get("full_name", name),
        "status": "OK",
        "pushed_at": str(data.get("pushed_at", ""))[:10],
        "stars": data.get("stargazers_count", ""),
        "archived": data.get("archived", ""),
        "latest_release": release,
        "open_issues": data.get("open_issues_count", ""),
    }


def repo_text_corpus() -> str:
    """All in-repo text we can cheaply search for citation coverage."""
    parts = []
    for path in sorted(ROOT.rglob("*.md")):
        if any(seg in path.parts for seg in ("__pycache__", ".git", "node_modules")):
            continue
        try:
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:  # noqa: BLE001
            continue
    return "\n".join(parts)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    records: dict[str, dict[str, object]] = {}
    per_query: dict[str, int] = {}
    for i, q in enumerate(QUERIES, 1):
        try:
            hits = arxiv_query(q)
        except Exception as exc:  # noqa: BLE001
            print(f"[{i}/{len(QUERIES)}] FAIL {q} ({exc})", file=sys.stderr)
            per_query[q] = -1
            continue
        kept = 0
        for rec in hits:
            if int(rec["year"]) < MIN_YEAR:
                continue
            kept += 1
            records.setdefault(str(rec["id"]), rec)
        per_query[q] = kept
        print(f"[{i}/{len(QUERIES)}] {kept:3d} kept  {q}")
        time.sleep(1.0)

    rows = sorted(records.values(), key=lambda r: (str(r["published"]), str(r["id"])), reverse=True)
    with (OUT / "arxiv_records.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["id", "published", "year", "primary", "title", "summary"])
        writer.writeheader()
        writer.writerows(rows)

    (OUT / "arxiv_queries.json").write_text(
        json.dumps({"queries": QUERIES, "per_query_kept": per_query,
                    "unique_records": len(rows), "min_year": MIN_YEAR,
                    "started_utc": started}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    token = _github_token()
    gh_rows = []
    for name in REPOS:
        meta = repo_meta(name, token)
        gh_rows.append(meta)
        print(f"[gh] {meta['repo']:32s} {meta['status']:12s} {meta['pushed_at']} {meta['latest_release']}")
        time.sleep(0.6)
    with (OUT / "github_repos.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["repo", "status", "pushed_at", "stars", "archived", "latest_release", "open_issues"]
        )
        writer.writeheader()
        writer.writerows(gh_rows)

    corpus = repo_text_corpus()
    gaps = [{"id": r["id"], "title": r["title"], "published": r["published"]}
            for r in rows if str(r["id"]) not in corpus]
    (OUT / "coverage_gaps.json").write_text(
        json.dumps({"definition": "arXiv id absent from every .md file in the repo",
                    "count": len(gaps), "records": gaps}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "experiment_id": "E68_LITERATURE_SCAN_2026_10_26",
        "scope": "review-grade package outside data/ and release/",
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "queries": len(QUERIES),
        "unique_records": len(rows),
        "coverage_gap_count": len(gaps),
        "files": {},
    }
    for name in ("arxiv_records.csv", "arxiv_queries.json", "github_repos.csv", "coverage_gaps.json"):
        blob = (OUT / name).read_bytes()
        manifest["files"][name] = hashlib.sha256(blob).hexdigest()
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"\nunique records: {len(rows)}   coverage gaps: {len(gaps)}   out: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
