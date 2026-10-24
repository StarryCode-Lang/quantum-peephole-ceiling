"""Round-12 literature sweep: arXiv phrase queries + GitHub ecosystem snapshot.

Writes a dated evidence package under
``docs/review/science_boost/2026-10-25_literature_scan/``:
  * ``arxiv_records.json``  -- deduplicated records, >= 2023
  * ``query_log.json``      -- every query, hit count, and failure mode
  * ``github_snapshot.json``-- repository releases / last push

Read-only.  Network failures are recorded, never papered over.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "review" / "science_boost" / "2026-10-25_literature_scan"
ATOM = "{http://www.w3.org/2005/Atom}"

QUERIES = [
    'all:"phase polynomial" AND cat:quant-ph',
    'all:"T-count" AND all:"lower bound"',
    'all:"commutation" AND all:"quantum circuit" AND all:"optimisation"',
    'all:"normal form" AND all:"quantum circuit"',
    'all:"token swapping"',
    'all:"peephole" AND all:"quantum"',
    'all:"equality saturation"',
    'all:"ZX-calculus" AND all:"completeness"',
    'all:"CNOT" AND all:"lower bound" AND all:"circuit"',
    'all:"linear reversible" AND all:"synthesis"',
    'all:"quantum compiler" AND all:"language model"',
    'all:"circuit optimisation" AND all:"benchmark"',
    'all:"Clifford+T" AND all:"optimisation"',
    'all:"phase polynomial" AND all:"synthesis"',
    'all:"rewrite system" AND all:"termination"',
    'all:"circuit compilation" AND all:"representation"',
    'all:"pass ordering" OR all:"pass sequence" AND all:"compiler"',
    'all:"equivalence checking" AND all:"quantum circuit"',
    'all:"quantum circuit" AND all:"optimisation" AND all:"landscape"',
    'all:"template matching" AND all:"quantum circuit"',
]

REPOS = [
    "Qiskit/qiskit",
    "CQCL/tket",
    "quantum-compiler/quartz",
    "quantum-compiler/quanto",
    "uwserial/VOQC",
    "zxcalc/pyzx",
    "BQSKit/bqskit",
    "qqq-wisc/tzap",
    "munich-quantum-toolkit/qcec",
    "tbcdebug/quartz",  # placeholder, will 404 harmlessly
]


def arxiv_query(term: str, max_results: int = 60) -> list[dict]:
    url = (
        "http://export.arxiv.org/api/query?"
        + urllib.parse.urlencode(
            {
                "search_query": term,
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
    )
    with urllib.request.urlopen(url, timeout=45) as response:
        payload = response.read()
    root = ET.fromstring(payload)
    records = []
    for entry in root.findall(f"{ATOM}entry"):
        published = (entry.findtext(f"{ATOM}published") or "")[:10]
        if published < "2023-01-01":
            continue
        identifier = (entry.findtext(f"{ATOM}id") or "").rsplit("/", 1)[-1]
        records.append(
            {
                "id": identifier,
                "published": published,
                "title": " ".join((entry.findtext(f"{ATOM}title") or "").split()),
                "abstract": " ".join((entry.findtext(f"{ATOM}summary") or "").split()),
                "query": term,
            }
        )
    return records


def github_token() -> str | None:
    try:
        out = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
    except Exception:
        return None
    match = re.search(r"^password=(.+)$", out, re.MULTILINE)
    return match.group(1).strip() if match else None


def github_get(url: str, token: str | None) -> dict:
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("User-Agent", "q-research-lit-scan")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    log: list[dict] = []
    records: dict[str, dict] = {}
    for term in QUERIES:
        try:
            hits = arxiv_query(term)
            log.append({"query": term, "hits": len(hits), "status": "ok"})
            for record in hits:
                if record["id"] not in records:
                    records[record["id"]] = record
        except Exception as exc:  # noqa: BLE001
            log.append({"query": term, "hits": 0, "status": f"error:{type(exc).__name__}"})
        time.sleep(3.2)

    token = github_token()
    repos: list[dict] = []
    for slug in REPOS:
        try:
            info = github_get(f"https://api.github.com/repos/{slug}", token)
            release = None
            try:
                release = github_get(f"https://api.github.com/repos/{slug}/releases/latest", token)
            except Exception:
                release = None
            repos.append(
                {
                    "repo": slug,
                    "stars": info.get("stargazers_count"),
                    "pushed_at": info.get("pushed_at"),
                    "open_issues": info.get("open_issues_count"),
                    "latest_release": (release or {}).get("tag_name"),
                    "latest_release_at": (release or {}).get("published_at"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            repos.append({"repo": slug, "error": f"{type(exc).__name__}"})
        time.sleep(0.4)

    (OUT / "arxiv_records.json").write_text(
        json.dumps(list(records.values()), indent=1), encoding="utf-8"
    )
    (OUT / "query_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    (OUT / "github_snapshot.json").write_text(json.dumps(repos, indent=1), encoding="utf-8")
    ok = sum(1 for item in log if item["status"] == "ok")
    print(f"queries ok {ok}/{len(QUERIES)}; unique records {len(records)}")
    for item in log:
        if item["status"] != "ok":
            print("FAILED", item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
