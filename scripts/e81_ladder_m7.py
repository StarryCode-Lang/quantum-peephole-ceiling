"""E81: the m = 7 ladder point, computed without materialising the fragment.

Motivation
----------
E78 established ``L* = m`` at m = 5 and m = 6 on the width-2 Clifford fragment.
The natural next point, m = 7, is 8^7 = 2,097,152 listings; E75's ``Fragment``
keeps every state and every per-member row, and the direct run died with
``MemoryError`` inside ``evaluate`` after 14 minutes.

This script answers the same question in two streaming passes:

  pass 1  enumerate every listing, keep only ``c_abs[class]`` and a canonical
          best form per class (a few thousand entries), discard the states;
  pass 2  re-enumerate, and for every reducible listing run the frozen greedy
          closure under a length-<=L synthetic rule set, counting outcomes.

Nothing is retained per member, so peak memory is the class table plus one
state, not 2.4 M states.

Question answered
-----------------
Is ``price(L = m-1)`` still strictly positive at m = 7?  If yes, the ladder
continues and no fixed-length library is complete; if it is zero, the ladder
stops at 6 and completeness *is* purchasable at L = 6.

Contract
--------
Read-only.  Frozen rule library (sha256 recorded).  Same search contract as
E75/E78: greedy closure (32 passes) plus a monotone BFS of depth <= min(gap, 3).
Nothing under ``data/``, ``release/`` or ``docs/manuscript/`` is written.

Outputs (``docs/review/science_boost/2026-10-29_rule_length_demand/``)
    ladder_m7.csv    one row per (max_rule_length): counts and price
    ladder_m7.json   contract, counts, residue witnesses, hashes
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

from src.optimisation.certified_landscape import (  # noqa: E402
    StateGate,
    _state_from_normalized,
    state_unitary,
)

EXPERIMENT_ID = "E81_LADDER_M7_2026_10_29"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-29_rule_length_demand"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


E75 = _load("e75_completeness_price", ROOT / "scripts" / "e75_completeness_price.py")

GENERATORS: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("h", (0,)),
    ("h", (1,)),
    ("x", (0,)),
    ("x", (1,)),
    ("z", (0,)),
    ("z", (1,)),
    ("cx", (0, 1)),
    ("cx", (1, 0)),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def key_of(gates: tuple[StateGate, ...]) -> str:
    return E75.canonical_key_fixed(state_unitary(_state_from_normalized(2, gates)))


def words(max_length: int):
    for length in range(0, max_length + 1):
        for word in itertools.product(range(len(GENERATORS)), repeat=length):
            yield tuple(StateGate(GENERATORS[i][0], GENERATORS[i][1], None) for i in word)


def pass_one(max_length: int) -> tuple[dict[str, int], dict[str, tuple[StateGate, ...]], int]:
    """``c_abs`` and a canonical best form per unitary class; no states retained."""

    c_abs: dict[str, int] = {}
    best: dict[str, tuple[int, tuple[StateGate, ...]]] = {}
    total = 0
    for gates in words(max_length):
        total += 1
        k = key_of(gates)
        cost = len(gates)
        if k not in c_abs or cost < c_abs[k]:
            c_abs[k] = cost
            best[k] = (cost, gates)
        elif cost == c_abs[k] and E75.gate_tuple_text(gates) < E75.gate_tuple_text(best[k][1]):
            best[k] = (cost, gates)
    return c_abs, {k: v[1] for k, v in best.items()}, total


def pass_two(
    c_abs: dict[str, int],
    best: dict[str, tuple[StateGate, ...]],
    max_length: int,
    max_rule: int,
    deadline: float,
    witness_limit: int = 12,
) -> dict[str, Any]:
    """Evaluate the length-<=max_rule synthetic library on every reducible listing."""

    class StreamingFragment:
        num_qubits = 2
        alphabet = frozenset(name for name, _ in GENERATORS)
        allowed_gates = frozenset((name, tuple(q)) for name, q in GENERATORS)
        best_form = {k: (len(v), v) for k, v in best.items()}

        _cache: dict[tuple[tuple[str, tuple[int, ...]], ...], str] = {}

        @classmethod
        def key(cls, gates: tuple[StateGate, ...]) -> str:
            # Windows are short (<= max_rule) and drawn from 8 generators, so the
            # distinct-window set is bounded by 8**max_rule (32,768 at 5) and a
            # plain dict cache is both safe and decisive: without it every greedy
            # pass recomputes an 8x8 matrix product per window.
            cache_key = tuple((gate.name, tuple(gate.qubits)) for gate in gates)
            hit = cls._cache.get(cache_key)
            if hit is None:
                hit = key_of(gates)
                cls._cache[cache_key] = hit
            return hit

        @staticmethod
        def window_arity(gates: tuple[StateGate, ...]) -> int:
            return len({q for gate in gates for q in gate.qubits})

    fragment = StreamingFragment()
    config = E75.Config(f"all_L2_{max_rule}", None, 2, max_rule)
    cache = E75.ActionCache()
    _ = cache  # base library is not part of the question at this length

    reducible = 0
    greedy_exact = 0
    after_search = 0
    budget = 0
    gaps: Counter[int] = Counter()
    witnesses: list[str] = []
    for gates in words(max_length):
        cost = len(gates)
        k = fragment.key(gates)
        target = c_abs[k]
        if cost <= target:
            continue
        reducible += 1
        if time.perf_counter() > deadline:
            raise RuntimeError(f"deadline_after:{reducible}")
        state = _state_from_normalized(2, gates)
        closed, _path, timed_out = E75.greedy_closure(fragment, state, config, cache, deadline)
        if timed_out:
            raise RuntimeError("closure_deadline")
        if closed.cost == target:
            greedy_exact += 1
            after_search += 1
            continue
        gap = closed.cost - target
        gaps[gap] += 1
        reached, _nodes, _path = E75.bfs_reaches(
            fragment,
            state,
            target,
            max_depth=min(gap, 3),
            config=config,
            cache=cache,
            deadline=deadline,
        )
        if reached is True:
            after_search += 1
        elif reached is None:
            budget += 1
        elif len(witnesses) < witness_limit:
            witnesses.append(E75.gate_tuple_text(gates))
    return {
        "max_rule_length": max_rule,
        "members_reducible": reducible,
        "greedy_exact": greedy_exact,
        "after_search": after_search,
        "failures": reducible - after_search,
        "price": round(1 - after_search / reducible, 6) if reducible else None,
        "budget_exhausted": budget,
        "gap_histogram": {str(k): v for k, v in sorted(gaps.items())},
        "witnesses": witnesses,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-length", type=int, default=7)
    parser.add_argument("--max-rule", type=int, default=6)
    parser.add_argument("--budget-seconds", type=float, default=7200.0)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    deadline = started + args.budget_seconds

    c_abs, best, total = pass_one(args.max_length)
    pass_one_seconds = round(time.perf_counter() - started, 1)
    result = pass_two(c_abs, best, args.max_length, args.max_rule, deadline)
    result["pass_one_seconds"] = pass_one_seconds
    result["runtime_seconds"] = round(time.perf_counter() - started, 1)

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-10-29",
        "purpose": "the m=7 ladder point, computed with a two-pass streaming fragment",
        "contract": {
            "rule_library": RULE_LIBRARY.relative_to(ROOT).as_posix(),
            "rule_library_sha256": sha256_file(RULE_LIBRARY),
            "generators": [f"{name}{''.join(str(q) for q in qubits)}" for name, qubits in GENERATORS],
            "max_length": args.max_length,
            "listings": total,
            "classes": len(c_abs),
            "reducible": sum(1 for _ in ()) or None,
            "search": "greedy closure (32 passes) + monotone BFS depth <= min(gap, 3), 20,000 nodes",
            "note": "base library is excluded: the question is whether a length-<=max_rule synthetic rule set suffices",
            "read_only": ["data/", "release/", "docs/manuscript/"],
        },
        "result": result,
        "class_histogram": {str(k): v for k, v in sorted(Counter(c_abs.values()).items())},
    }
    with (out / "ladder_m7.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "max_rule_length",
                "members_reducible",
                "greedy_exact",
                "after_search",
                "failures",
                "price",
                "budget_exhausted",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerow(result)
    (out / "ladder_m7.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2)[:2500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
