"""E92: fielded literature and ecosystem scan for the 2026-11-04 review round.

Reuses E85's fetch / token / citation-coverage helpers (one implementation, no
second copy of the arXiv client), and changes only the query set: this round's
questions are about the *content axis* of the rewrite problem (rule length,
library completeness, cost-neutral moves) rather than the reorder axis that
rounds 20-22 already covered.

Outputs (``docs/review/science_boost/2026-11-04_literature_scan/``)
    arxiv_records.csv   one row per unique record
    coverage.json       which ids the repository cites, strict and loose
    github_state.json   release state of the watched repositories
    summary.json        query log, counts, contract
    MANIFEST.json       sha256 of every artifact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

EXPERIMENT_ID = "E92_LITERATURE_SCAN_2026_11_04"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-11-04_literature_scan"

QUERIES = [
    'abs:"rewrite" AND abs:"quantum circuit" AND abs:"complete"',
    'abs:"peephole" AND abs:"quantum"',
    'abs:"template" AND abs:"quantum circuit" AND abs:"matching"',
    'abs:"equality saturation" AND abs:"quantum"',
    'abs:"e-graph" AND abs:"quantum"',
    'abs:"commutation" AND abs:"quantum circuit" AND abs:"optimization"',
    'abs:"Clifford" AND abs:"optimal" AND abs:"synthesis" AND abs:"gate count"',
    'abs:"CNOT" AND abs:"complexity" AND abs:"linear reversible"',
    'abs:"quantum compiler" AND abs:"pass" AND abs:"ordering"',
    'abs:"quantum" AND abs:"compilation" AND abs:"reinforcement learning"',
    'abs:"large language model" AND abs:"quantum circuit" AND abs:"compilation"',
    'abs:"benchmark" AND abs:"quantum compiler" AND abs:"reproducib"',
    'abs:"circuit optimization" AND abs:"local optimum" AND abs:"quantum"',
    'abs:"phase polynomial" AND abs:"optimization"',
    'abs:"ZX-calculus" AND abs:"optimization" AND abs:"completeness"',
    'abs:"quantum circuit" AND abs:"representation" AND abs:"equivalence"',
    'abs:"stabilizer" AND abs:"circuit" AND abs:"lower bound"',
    'abs:"transpilation" AND abs:"quantum" AND abs:"equivalence checking"',
    'abs:"quantum" AND abs:"circuit" AND abs:"depth" AND abs:"trade-off" AND abs:"gate count"',
    'abs:"resource estimation" AND abs:"fault-tolerant" AND abs:"circuit optimization"',
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
    "quantum-compiler/quanto",
    "openqasm/openqasm",
    "pnnl/qsearch",
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
    parser.add_argument("--skip-github", action="store_true")
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

    github_rows: list[dict[str, Any]] = []
    if not args.skip_github:
        token = E85.github_token()
        for repo in REPOS:
            try:
                github_rows.append(E85.github(repo, token))
            except Exception as exc:  # pragma: no cover - network
                github_rows.append({"repo": repo, "error": repr(exc)})
            time.sleep(1)

    cited_loose = E85.cited_ids()
    strict: set[str] = set()
    skip_dirs = {"science_boost", "literature_scan"}
    for path in sorted((ROOT / "docs").rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".csv", ".txt"}:
            continue
        if any(part in skip_dirs or part.startswith("20") and "_" in part for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in __import__("re").findall(r"\b(\d{4}\.\d{4,5})\b", text):
            strict.add(match)
    reference_text = (ROOT / "docs" / "references" / "unified_references.md").read_text(
        encoding="utf-8", errors="ignore"
    )
    for match in __import__("re").findall(r"\b(\d{4}\.\d{4,5})\b", reference_text):
        strict.add(match)

    rows = []
    for record in records.values():
        rows.append(
            {
                "id": record.get("id", ""),
                "published": record.get("published", ""),
                "title": record.get("title", "").replace("\n", " "),
                "primary_category": record.get("primary_category", ""),
                "cited_strict": record.get("id", "") in strict,
                "cited_loose": record.get("id", "") in cited_loose,
            }
        )
    rows.sort(key=lambda row: row["published"], reverse=True)

    recent = [row for row in rows if row["published"] >= "2026-01-01"]
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "contract": {
            "queries": len(QUERIES),
            "query_style": 'fielded abs:"..." AND abs:"..."',
            "writes": ["docs/review/science_boost/2026-11-04_literature_scan/"],
            "channels": {
                "arxiv_api": "used",
                "github_rest": "skipped" if args.skip_github else "used",
                "tavily": "unavailable (no key in this environment)",
                "exa": "unavailable (no MCP server configured)",
                "multi_search_engine": "unavailable (no package)",
            },
        },
        "totals": {
            "unique_records": len(rows),
            "records_2026_or_later": len(recent),
            "records_2025_or_later": sum(1 for row in rows if row["published"] >= "2025-01-01"),
            "cited_strict": sum(1 for row in rows if row["cited_strict"]),
            "cited_loose": sum(1 for row in rows if row["cited_loose"]),
        },
        "uncited_2026": [
            {"id": row["id"], "published": row["published"], "title": row["title"]}
            for row in recent
            if not row["cited_strict"]
        ],
        "query_log": query_log,
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }

    with (out / "arxiv_records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["id"])
        writer.writeheader()
        writer.writerows(rows)
    with (out / "coverage.json").open("w", encoding="utf-8") as handle:
        json.dump({"strict_count": len(strict), "loose_count": len(cited_loose)}, handle, indent=2)
    with (out / "github_state.json").open("w", encoding="utf-8") as handle:
        json.dump(github_rows, handle, indent=2)
    with (out / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "artifacts": {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in sorted(out.glob("*"))
            if path.is_file() and path.name != "MANIFEST.json"
        },
    }
    with (out / "MANIFEST.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)

    print(json.dumps(summary["totals"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
