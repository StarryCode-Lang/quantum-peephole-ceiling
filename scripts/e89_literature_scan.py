"""E89: round-22 literature and ecosystem scan.

Scope is narrower than E83/E85 and aimed at this round's two questions:

  1. Is the completeness *threshold* scaling already published?  Round 21's
     ``LF-C1`` derives ``L*(n) = Omega(n^2 / log n)`` by counting words.  The
     same counting is the classical CNOT-count lower bound, so the question is
     whether the bound, the *diameter* framing, or the peephole application is
     already in the literature.
  2. Is "optimal peephole optimization of Clifford circuits" prior art?  If a
     paper already reports provably optimal local replacement tables for
     Clifford circuits, then the project's template-library narrative needs a
     demarcation paragraph, not a new theorem.

Channels actually used: the arXiv Atom API with field-qualified queries
(``abs:"..." AND abs:"..."``; round 17 showed that a bare ``all:`` wrapper
degenerates into a bag-of-words AND) and the authenticated GitHub REST API.
Channels unavailable in this environment are recorded in the summary rather
than silently omitted -- no claim in the round's document depends on them.

Read-only.  Writes only into its own evidence package.

Outputs (``docs/review/science_boost/2026-11-02_literature_scan/``)
    arxiv_records.csv     one row per unique record
    arxiv_queries.json    the exact queries and their hit counts
    github_state.json     one row per repository
    coverage.json         which records are cited anywhere in the repo
    summary.json          contract, counts, unavailable channels
    MANIFEST.json         sha256 of every artifact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

EXPERIMENT_ID = "E89_LITERATURE_SCAN_2026_11_02"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-11-02_literature_scan"

QUERIES = [
    'abs:"Clifford" AND abs:"optimal synthesis"',
    'abs:"symplectic group" AND abs:"diameter"',
    'abs:"Clifford" AND abs:"gate count" AND abs:"asymptotic"',
    'abs:"peephole" AND abs:"quantum"',
    'abs:"circuit optimization" AND abs:"local" AND abs:"optimal"',
    'abs:"rewrite" AND abs:"complete" AND abs:"Clifford"',
    'abs:"CNOT" AND abs:"lower bound" AND abs:"linear reversible"',
    'abs:"Clifford" AND abs:"tableau" AND abs:"synthesis"',
    'abs:"quantum compiler" AND abs:"peephole"',
    'abs:"template" AND abs:"matching" AND abs:"quantum circuit"',
    'abs:"equality saturation" AND abs:"quantum"',
    'abs:"circuit" AND abs:"representation" AND abs:"optimization" AND abs:"quantum"',
    'abs:"gate set" AND abs:"Clifford" AND abs:"completeness"',
    'abs:"quantum" AND abs:"compilation" AND abs:"benchmark" AND abs:"optimal"',
    'abs:"stabilizer" AND abs:"circuit" AND abs:"optimization"',
    'abs:"quantum circuit" AND abs:"distance" AND abs:"rewrite"',
    'abs:"phase polynomial" AND abs:"Clifford"',
    'abs:"quantum" AND abs:"compiler" AND abs:"pass" AND abs:"ordering"',
]

REPOS = [
    "Qiskit/qiskit",
    "Quantinuum/tket",
    "quantum-compiler/quartz",
    "zxcalc/pyzx",
    "BQSKit/bqskit",
    "munich-quantum-toolkit/qcec",
    "qqq-wisc/tzap",
    "psg-mit/quanto",
    "CQCL/tket",
    "quartz-tools/quartz",
    "quantum-compiler/quanto",
]


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot_load:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


E85 = _load("e85_literature_scan", ROOT / "scripts" / "e85_literature_scan.py")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--max-results", type=int, default=40)
    args = parser.parse_args()
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    records: dict[str, dict[str, Any]] = {}
    query_log: list[dict[str, Any]] = []
    for query in QUERIES:
        try:
            hits = E85.arxiv(query, max_results=args.max_results)
        except Exception as exc:  # pragma: no cover - network
            query_log.append({"query": query, "hits": 0, "error": repr(exc)})
            print(f"  [arxiv] {query}: ERROR {exc!r}", flush=True)
            continue
        query_log.append({"query": query, "hits": len(hits)})
        for record in hits:
            records.setdefault(record["id"], record)
        print(f"  [arxiv] {query}: {len(hits)} hits, {len(records)} unique", flush=True)
        time.sleep(3)

    token = E85.github_token()
    github_rows: list[dict[str, Any]] = []
    for repo in REPOS:
        try:
            github_rows.append(E85.github(repo, token))
        except Exception as exc:  # pragma: no cover - network
            github_rows.append({"repo": repo, "error": repr(exc)})
        time.sleep(1)

    cited = E85.cited_ids()
    # Defect fixed this round: ``E85.cited_ids`` scans every ``.md/.csv/.json/.txt``
    # under ``docs/``, which includes the previous rounds' own ``arxiv_records.json``
    # dumps.  An id that only ever appeared in a scan dump therefore counted as
    # "cited in the repository" -- a false positive that inflates coverage and
    # hides real gaps.  The strict set drops the scan packages and the
    # machine-readable dumps, keeping prose, tables and the reference catalogue.
    strict: set[str] = set()
    for path in ROOT.glob("docs/**/*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".csv"}:
            continue
        if "science_boost" in path.parts:
            continue
        try:
            strict.update(E85.ID_PATTERN.findall(path.read_text(encoding="utf-8", errors="ignore")))
        except Exception:  # pragma: no cover
            continue
    for path in ROOT.glob("*.md"):
        strict.update(E85.ID_PATTERN.findall(path.read_text(encoding="utf-8", errors="ignore")))
    rows = sorted(records.values(), key=lambda r: r.get("published", ""), reverse=True)
    coverage = [
        {
            "id": row["id"],
            "published": row.get("published", ""),
            "title": row.get("title", ""),
            "cited_in_repo_loose": row["id"] in cited,
            "cited_in_repo_strict": row["id"] in strict,
        }
        for row in rows
    ]
    uncited = [row for row in coverage if not row["cited_in_repo_strict"]]
    recent = [row for row in coverage if row["published"] >= "2025-01-01"]
    recent_uncited = [row for row in uncited if row["published"] >= "2025-01-01"]

    with (out / "arxiv_records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["id", "published", "title", "authors", "primary_category"]
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in writer.fieldnames})
    (out / "arxiv_queries.json").write_text(json.dumps(query_log, indent=2) + "\n", encoding="utf-8")
    (out / "github_state.json").write_text(json.dumps(github_rows, indent=2) + "\n", encoding="utf-8")
    (out / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n", encoding="utf-8")

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-11-02",
        "purpose": (
            "check whether the completeness-threshold scaling and 'optimal peephole "
            "optimization of Clifford circuits' are already published"
        ),
        "contract": {
            "arxiv": "Atom API, field-qualified abs: queries, 3 s spacing",
            "github": "REST API, authenticated when a token is available",
            "coverage": "arXiv ids found anywhere under docs/ plus top-level markdown",
            "read_only": ["data/", "release/", "docs/manuscript/"],
        },
        "counts": {
            "queries": len(query_log),
            "records": len(coverage),
            "records_2025_or_later": len(recent),
            "records_cited_loose": len(cited & {row["id"] for row in coverage}),
            "records_cited_strict": len(strict & {row["id"] for row in coverage}),
            "records_uncited_strict": len(uncited),
            "records_2025_or_later_uncited_strict": len(recent_uncited),
        },
        "github": github_rows,
        "unavailable_channels": {
            "tavily": "no API key and package not installed",
            "exa": "no MCP server configured",
            "multi-search-engine": "no API key",
            "arxiv-reader": "no LLM key",
            "citation-manager": "no Crossref dependency",
        },
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (out / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": EXPERIMENT_ID,
                "generated": "2026-11-02",
                "script": "scripts/e89_literature_scan.py",
                "artifacts": {
                    name: sha256_file(out / name)
                    for name in (
                        "arxiv_records.csv",
                        "arxiv_queries.json",
                        "github_state.json",
                        "coverage.json",
                        "summary.json",
                    )
                    if (out / name).exists()
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
