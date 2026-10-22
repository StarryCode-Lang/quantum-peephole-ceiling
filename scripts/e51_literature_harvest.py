"""E51: arXiv frontier harvest for the 2026-10-21 innovation scan.

Runs phrase-quoted arXiv API queries over the six frontier themes the scan must
cover, de-duplicates by arXiv id, keeps records published in 2023 or later, and
reports which harvested ids have **zero** textual coverage anywhere in the
repository (``docs/**/*.md`` and ``docs/references/unified_references.md``).

No API key is required.  Outputs go to
``docs/review/science_boost/2026-10-21_literature_scan/``.

Read-only with respect to ``data/`` and ``release/``.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-21_literature_scan"  # overridable via --output-dir
API = "https://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom"}

QUERIES: list[tuple[str, str]] = [
    ("peephole", 'all:"peephole" AND all:"quantum circuit"'),
    ("equality_saturation", 'all:"equality saturation" AND all:"quantum"'),
    ("egraph", 'all:"e-graph" AND all:"quantum circuit"'),
    ("zx_calculus", 'all:"ZX-calculus" AND all:"optimization"'),
    ("template_matching", 'all:"template matching" AND all:"quantum circuit"'),
    ("rl_compilation", 'all:"reinforcement learning" AND all:"quantum circuit compilation"'),
    ("llm_compilation", 'all:"large language model" AND all:"quantum circuit"'),
    ("landscape", 'all:"local optimum" AND all:"quantum circuit"'),
    ("cnot_lower_bound", 'all:"CNOT" AND all:"lower bound" AND all:"Clifford"'),
    ("tcount_lower_bound", 'all:"T-count" AND all:"lower bound"'),
    ("phase_polynomial", 'all:"phase polynomial" AND all:"optimization"'),
    ("exact_synthesis", 'all:"exact synthesis" AND all:"quantum circuit"'),
    ("hardware_co_design", 'all:"quantum compiler" AND all:"hardware" AND all:"co-design"'),
    ("commutation", 'all:"commutation" AND all:"quantum circuit" AND all:"optimization"'),
    ("cx_direction", 'all:"CX" AND all:"direction" AND all:"circuit" AND all:"synthesis"'),
    ("normal_form", 'all:"normal form" AND all:"quantum circuit"'),
    ("windowed_local", 'all:"local" AND all:"rewriting" AND all:"quantum"'),
    ("representation", 'all:"circuit representation" AND all:"compiler"'),
    ("pass_order", 'all:"pass order" AND all:"quantum"'),
    ("average_case", 'all:"average-case" AND all:"quantum circuit"'),
    ("certificate", 'all:"certificate" AND all:"quantum circuit optimization"'),
    ("benchmark", 'all:"benchmark" AND all:"quantum circuit optimization" AND all:"reproducib"'),
    ("trace_monoid", 'all:"trace monoid" AND all:"quantum"'),
    ("commutation_closure", 'all:"commutation" AND all:"closure" AND all:"circuit"'),
    ("peephole_lookahead", 'all:"peephole" AND all:"lookahead"'),
    ("rewrite_saturation", 'all:"rewriting" AND all:"saturation" AND all:"quantum"'),
    ("gate_count_bound", 'all:"gate count" AND all:"lower bound" AND all:"circuit"'),
    ("token_swapping", 'all:"token swapping"'),
]

ID_PATTERN = re.compile(r"\b(\d{4}\.\d{4,5})\b")


def fetch(query: str, max_results: int = 100) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    request = urllib.request.Request(
        f"{API}?{params}", headers={"User-Agent": "q-research-innovation-scan/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    root = ET.fromstring(payload)
    records = []
    for entry in root.findall("atom:entry", NS):
        raw_id = entry.findtext("atom:id", default="", namespaces=NS)
        published = entry.findtext("atom:published", default="", namespaces=NS)[:10]
        records.append(
            {
                "id": raw_id.rsplit("/", 1)[-1],
                "published": published,
                "title": " ".join(entry.findtext("atom:title", default="", namespaces=NS).split()),
                "abstract": " ".join(
                    entry.findtext("atom:summary", default="", namespaces=NS).split()
                ),
                "authors": [
                    author.findtext("atom:name", default="", namespaces=NS)
                    for author in entry.findall("atom:author", NS)
                ][:6],
            }
        )
    return records


def repository_text() -> str:
    chunks = []
    for path in sorted((ROOT / "docs").rglob("*.md")):
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(chunks)


def main() -> int:
    global OUTPUT_ROOT
    if "--output-dir" in sys.argv:
        OUTPUT_ROOT = Path(sys.argv[sys.argv.index("--output-dir") + 1])
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    harvest: dict[str, dict[str, Any]] = {}
    query_log = []
    for label, query in QUERIES:
        try:
            records = fetch(query)
        except Exception as exc:  # network failures are recorded, not hidden
            query_log.append({"label": label, "query": query, "status": f"ERROR:{exc}"})
            print(f"[E51] {label}: ERROR {exc}", flush=True)
            time.sleep(3)
            continue
        kept = [record for record in records if record["published"] >= "2023-01-01"]
        query_log.append(
            {"label": label, "query": query, "status": "OK", "fetched": len(records), "kept": len(kept)}
        )
        for record in kept:
            harvest.setdefault(record["id"], record)
        print(f"[E51] {label}: {len(records)} fetched, {len(kept)} kept", flush=True)
        time.sleep(3)

    corpus = repository_text()
    for record in harvest.values():
        bare = record["id"].split("v")[0]
        record["covered_in_repo"] = bare in corpus

    ordered = sorted(harvest.values(), key=lambda item: item["published"], reverse=True)
    (OUTPUT_ROOT / "arxiv_records.json").write_text(
        json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    uncovered = [record for record in ordered if not record["covered_in_repo"]]
    (OUTPUT_ROOT / "uncovered_ids.json").write_text(
        json.dumps(uncovered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUTPUT_ROOT / "query_log.json").write_text(
        json.dumps(
            {
                "queries": query_log,
                "unique_records": len(ordered),
                "uncovered": len(uncovered),
                "earliest": min((record["published"] for record in ordered), default=""),
                "latest": max((record["published"] for record in ordered), default=""),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "unique_records": len(ordered),
                "uncovered": len(uncovered),
                "latest": max((record["published"] for record in ordered), default=""),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
