"""Resilience wrapper for the 128-cell re-certification in a live-edit environment.

A concurrent session is editing ``src/optimisation/certified_landscape.py``
while this certification runs.  This wrapper:

1. waits until the engine source hash has been stable for 3 minutes,
2. prunes any cells in ``full_cells.jsonl`` that were produced under a
   different engine version than the current on-disk one,
3. resumes ``rerun_all_cells.py`` (crash- and MemoryError-safe),
4. repeats until 128 cells exist and every record carries the SAME engine hash.

Each retained cell's ``engine_source_sha256`` is checked again at build time.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parent
ROOT = PKG.parents[3]
OUT = PKG / "full_cells.jsonl"
ENGINE = ROOT / "src" / "optimisation" / "certified_landscape.py"
ENGINE_KEY = "src/optimisation/certified_landscape.py"
STABILITY_SECONDS = 180.0
MAX_ATTEMPTS = 60
MIN_AVAILABLE_GB = 3.2
RETRY_SLEEP_SECONDS = 30.0


def memory_ok() -> tuple[bool, float]:
    try:
        import psutil

        available_gb = psutil.virtual_memory().available / 1e9
        return available_gb >= MIN_AVAILABLE_GB, available_gb
    except ImportError:
        return True, -1.0


def engine_hash() -> str:
    return hashlib.sha256(ENGINE.read_bytes()).hexdigest()


def state() -> tuple[int, set[str]]:
    if not OUT.exists():
        return 0, set()
    hashes = set()
    count = 0
    for line in OUT.read_text(encoding="utf-8").splitlines():
        if line.strip():
            hashes.add(json.loads(line)["engine_source_sha256"][ENGINE_KEY])
            count += 1
    return count, hashes


def main() -> int:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        current = engine_hash()
        stable_since = time.time()
        while time.time() - stable_since < STABILITY_SECONDS:
            time.sleep(30)
            if engine_hash() != current:
                current = engine_hash()
                stable_since = time.time()
        ok, available_gb = memory_ok()
        if not ok:
            print(
                f"[attempt {attempt}] waiting: only {available_gb:.2f} GB available "
                f"(need {MIN_AVAILABLE_GB} GB for the largest cells); sleeping {RETRY_SLEEP_SECONDS:.0f}s",
                flush=True,
            )
            time.sleep(RETRY_SLEEP_SECONDS)
            continue
        print(
            f"[attempt {attempt}] engine stable at {current[:16]}, {available_gb:.1f} GB available, "
            f"pruning stale cells",
            flush=True,
        )
        if OUT.exists():
            lines = OUT.read_text(encoding="utf-8").splitlines()
            keep = [l for l in lines if l.strip() and json.loads(l)["engine_source_sha256"][ENGINE_KEY] == current]
            if len(keep) != len([l for l in lines if l.strip()]):
                OUT.write_text("".join(l + "\n" for l in keep), encoding="utf-8", newline="\n")
                print(f"[attempt {attempt}] pruned {len(lines) - len(keep)} cells from other engine versions", flush=True)
        started = time.time()
        code = subprocess.run([sys.executable, str(PKG / "rerun_all_cells.py")]).returncode
        count, hashes = state()
        print(
            f"[attempt {attempt}] rc={code} cells={count}/128 engine_versions={len(hashes)} "
            f"elapsed={time.time() - started:.0f}s",
            flush=True,
        )
        if code == 0 and count == 128 and len(hashes) == 1:
            print(f"COMPLETE under engine {hashes.pop()[:16]}", flush=True)
            return 0
        time.sleep(RETRY_SLEEP_SECONDS)
    print("GAVE UP after max attempts", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
