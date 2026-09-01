"""Inventory and optionally live-check external links in project Markdown.

Definite HTTP 404/410 responses fail in ``--strict`` mode.  Authentication,
rate limiting, robots policies, and transient network failures remain explicit
``unverified`` states rather than being mislabeled as working or broken.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
TRAILING = ".,;:!?`"


def markdown_files() -> list[Path]:
    files = list((PROJECT_ROOT / "docs").rglob("*.md"))
    files.extend(path for path in [PROJECT_ROOT / "README.md"] if path.is_file())
    return sorted(files)


def extract_links(paths: list[Path]) -> dict[str, list[dict]]:
    inventory: dict[str, list[dict]] = {}
    for path in paths:
        try:
            relative = path.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            relative = path.as_posix()
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for match in URL_RE.finditer(line):
                url = match.group(0).rstrip(TRAILING)
                inventory.setdefault(url, []).append({
                    "path": relative,
                    "line": line_number,
                })
    return inventory


def check_url(url: str, timeout: float) -> dict:
    if "{" in url or "}" in url or "..." in url or url.endswith("="):
        return {"status": "template_not_checked"}
    headers = {"User-Agent": "Q-research-link-audit/1.0"}
    attempts = [("HEAD", headers), ("GET", {**headers, "Range": "bytes=0-0"})]
    last_error = None
    for method, request_headers in attempts:
        request = urllib.request.Request(url, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                code = int(response.status)
                return {
                    "status": "reachable" if code < 400 else "unverified_http",
                    "http_status": code,
                    "final_url": response.geturl(),
                    "method": method,
                }
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code in {404, 410}:
                return {
                    "status": "broken",
                    "http_status": int(error.code),
                    "final_url": error.geturl(),
                    "method": method,
                }
            if method == "GET":
                return {
                    "status": "unverified_http",
                    "http_status": int(error.code),
                    "final_url": error.geturl(),
                    "method": method,
                }
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
            if method == "GET":
                return {
                    "status": "unverified_network",
                    "error": f"{type(error).__name__}: {error}",
                    "method": method,
                }
    return {
        "status": "unverified_network",
        "error": f"{type(last_error).__name__}: {last_error}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "release" / "external_link_audit.json",
    )
    args = parser.parse_args()

    files = markdown_files()
    inventory = extract_links(files)
    checks: dict[str, dict] = {}
    if args.live:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(check_url, url, args.timeout): url for url in inventory
            }
            for future in concurrent.futures.as_completed(futures):
                checks[futures[future]] = future.result()

    records = []
    for url in sorted(inventory):
        records.append({
            "url": url,
            "occurrences": inventory[url],
            "check": checks.get(url, {"status": "not_checked"}),
        })
    counts: dict[str, int] = {}
    for record in records:
        status = record["check"]["status"]
        counts[status] = counts.get(status, 0) + 1
    payload = {
        "schema_version": "1.0.0",
        "status": (
            "PASS_NO_DEFINITE_BROKEN_LINKS_WITH_UNVERIFIED"
            if not counts.get("broken", 0) else "FAIL_DEFINITE_BROKEN_LINKS"
        ),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "README.md and docs/**/*.md",
        "markdown_files": len(files),
        "unique_urls": len(records),
        "url_occurrences": sum(len(value) for value in inventory.values()),
        "live_check_requested": args.live,
        "status_counts": counts,
        "metric_dispositions": {
            "15.42": (
                f"PARTIAL: live audit found {counts.get('broken', 0)} definite broken links "
                f"among {len(records)} unique URLs, but "
                f"{counts.get('unverified_http', 0) + counts.get('unverified_network', 0)} "
                "URLs remain unverified and future link rot cannot be excluded"
            )
        },
        "claim_boundary": (
            "This is a point-in-time live reachability audit. HTTP 403, authentication, robots, "
            "and network failures remain unverified; template URLs are not dereferenced; absence "
            "of a current 404/410 does not guarantee future persistence."
        ),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "records": records,
    }
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)
    print(json.dumps({
        "output": str(args.output),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "unique_urls": len(records),
        "status_counts": counts,
    }, sort_keys=True))
    if args.strict and counts.get("broken", 0):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
