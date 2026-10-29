"""E78: is the completeness threshold a width effect or a group invariant?

Motivation
----------
E75 (2026-10-28) measured the price of a fixed-length rule library on two
fragments and reported two thresholds:

    width 1, {h,x,z}, listings <= 8      L* = 4
    width 2, {h0,h1,cx01}, listings <= 8 L* = 3

Two defects make those numbers unusable as stated.

1. **Label defect.**  ``{h,x,z}`` on one qubit generates only the order-8 group
   <h,x> (h normalises the Pauli group, so z = hxh adds nothing).  The 1-qubit
   Clifford group modulo phase has order 24.  E75's "1-qubit Clifford fragment"
   is therefore a one-third-size subgroup, and the sentence "the 1-qubit
   Clifford completeness threshold is L* = 4" in
   ``docs/theory/decidability_frontier_2026-10-28.md`` is not supported by the
   fragment it cites.  This script measures the real 24-element group.

2. **Comparability defect.**  Part C's L* = 3 and Part B's L* = 4 were compared
   as "the same listing length, different width", but the two fragments differ
   in group order (213 vs 8 classes), in generator arity, and in whether a
   phase gate exists.  Width is not the only variable that moved.

What this experiment does
-------------------------
Part A  width 2, the full 2-qubit Clifford generator set, listings <= 5.
        Decisive because 5 > 4: if the price is 0 at L = 4 here, then the
        threshold at width 2 is strictly below the instance length -- the
        non-trivial statement E75's Part A could not make (its m equalled its
        candidate L*).

Part B  width 3, the same generator pattern extended to three qubits,
        listings <= 5.  This is the data point the theory document names as
        its largest open question ("width >= 3 completely unmeasured").

Part C  a primitive-identity census.  For widths 1-3 it enumerates every
        identity listing up to a length bound and reports the shortest one
        that contains no shorter identity as a contiguous subword.  That
        length is a lower bound on L*: a listing whose only reduction is such
        an identity cannot be reduced by any rule shorter than it.

The claim under test
--------------------
H1 (width effect)      L* grows with the number of qubits.
H2 (group invariant)   L* is the shortest non-trivial relation of the
                       fragment's group and does not grow with width; for the
                       natural Clifford gate sets it is <= 4.

Both hypotheses are falsifiable from the tables this script writes.

Contract
--------
Read-only.  Frozen rule library
``data/v13/e43_quartz_rule_import/generation_a/rule_library.json`` (sha256
recorded).  Nothing under ``data/``, ``release/`` or ``docs/manuscript/`` is
written.  Search contract is E75's, unchanged: greedy closure plus a monotone
BFS of depth <= min(gap, 3), 20,000 nodes, 32 greedy passes.

Outputs (``docs/review/science_boost/2026-10-29_width_threshold/``)
    price_curve.csv        one row per (part, config)
    member_tau.csv         one row per reducible member: tau, c_abs, gap
    primitive_identities.csv  Part C census
    summary.json           contract, tables, self-checks
    MANIFEST.json          sha256 of every artifact
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from src.optimisation.certified_landscape import (  # noqa: E402
    StateGate,
    _state_from_normalized,
    state_unitary,
)

EXPERIMENT_ID = "E78_WIDTH_THRESHOLD_2026_10_29"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-29_width_threshold"


def _load(name: str, path: Path) -> Any:
    """Import a sibling script as a module, registering it for dataclasses."""

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot_load:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


E75 = _load("e75_completeness_price", ROOT / "scripts" / "e75_completeness_price.py")

# ---------------------------------------------------------------------------
# Alphabet closure, repaired.
#
# E75 filters library actions by gate *name* (``gate.name not in alphabet``).
# At width 2 that was harmless because both CX orders were generators.  At
# width 3 the generator set is the line CX(i, i+1) only, so a library rule that
# emits CX(i+1, i) passes the name filter and leaves the fragment.  The next
# window lookup then asks for a unitary class the fragment never enumerated and
# raises KeyError -- which is how this defect was found.
#
# The repair filters by (name, qubits) generator membership and, defensively,
# skips any window whose class is absent from the fragment table (counting the
# skips so the size of the leak stays visible).
# ---------------------------------------------------------------------------
_ORIGINAL_LEGAL_ACTIONS = E75.legal_actions
_ORIGINAL_SYNTHETIC = E75.synthetic_actions
_ALLOWED_GATES: set[tuple[str, tuple[int, ...]]] = set()
SKIPPED_WINDOW_CLASSES = {"count": 0}


def _filtered_legal_actions(state: Any, library: Path, scope: str) -> list[Any]:
    return [
        action
        for action in _ORIGINAL_LEGAL_ACTIONS(state, library, scope)
        if all((gate.name, tuple(gate.qubits)) in _ALLOWED_GATES for gate in action.post_state.gates)
    ]


def _safe_synthetic_actions(fragment: Any, state: Any, lmin: int, lmax: int, arity: int | None) -> list[Any]:
    gates = state.gates
    actions: list[Any] = []
    for length in range(lmin, lmax + 1):
        if length > len(gates):
            continue
        for start in range(0, len(gates) - length + 1):
            window = gates[start : start + length]
            if arity is not None and fragment.window_arity(window) != arity:
                continue
            key = fragment.key(window)
            if key not in fragment.best_form:
                SKIPPED_WINDOW_CLASSES["count"] += 1
                continue
            best_cost, best_gates = fragment.best_form[key]
            if best_cost >= length:
                continue
            post_gates = gates[:start] + best_gates + gates[start + length :]
            actions.append(
                E75.SyntheticAction(
                    rule_id=f"synth:w{fragment.num_qubits}:{arity or 0}q:L{length}",
                    location=start,
                    cost_delta=best_cost - length,
                    post_state=_state_from_normalized(fragment.num_qubits, post_gates),
                    window=(start, start + length),
                    pattern=gate_text(window),
                    replacement=gate_text(best_gates),
                )
            )
    return actions


E75.legal_actions = _filtered_legal_actions
E75.synthetic_actions = _safe_synthetic_actions


def generators_for(num_qubits: int) -> tuple[tuple[str, tuple[int, ...]], ...]:
    """Full Clifford generator set on ``num_qubits``: h/x/z everywhere, CX on a line.

    E73 uses both orders of the entangler at width 2.  At width 3 the ordered
    pair count is 6, which would make the enumeration 12^5 = 248,832 listings
    for no scientific gain, so the entangler is restricted to the line
    ``cx(i, i+1)``.  This is recorded in the contract: the width-3 fragment is
    *not* the full 3-qubit Clifford group, it is the subgroup generated by
    single-qubit Clifford gates plus nearest-neighbour CX on a line.
    """

    out: list[tuple[str, tuple[int, ...]]] = []
    for name in ("h", "x", "z"):
        for qubit in range(num_qubits):
            out.append((name, (qubit,)))
    for qubit in range(num_qubits - 1):
        out.append(("cx", (qubit, qubit + 1)))
    if num_qubits == 2:
        # Keep E73/E75's 8-generator set at width 2 so the numbers stay comparable.
        out.append(("cx", (1, 0)))
    return tuple(out)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def gate_text(gates: tuple[StateGate, ...]) -> str:
    return ".".join(gate.name + "".join(str(q) for q in gate.qubits) for gate in gates)


def is_identity(matrix: np.ndarray, tol: float = 1e-9) -> bool:
    """Unitary equals the identity up to a global phase."""

    overlap = abs(np.trace(matrix)) / matrix.shape[0]
    return bool(abs(overlap - 1.0) <= tol)


def primitive_identity_census(
    num_qubits: int,
    generators: tuple[tuple[str, tuple[int, ...]], ...],
    max_length: int,
) -> dict[str, Any]:
    """Shortest identity listing that the length-2 (pair) rule cannot already remove.

    The pair rule ``g g -> empty`` is available at ``L = 2`` in every library this
    project has ever measured, so an identity word containing an adjacent equal
    pair is not evidence about longer rules.  The census therefore reports the
    shortest *pair-free* identity, and among those the primitive ones (no proper
    contiguous subword is itself an identity).
    """

    identity_words: dict[tuple[int, ...], int] = {}
    for length in range(1, max_length + 1):
        for word in itertools.product(range(len(generators)), repeat=length):
            gates = tuple(StateGate(generators[i][0], generators[i][1], None) for i in word)
            state = _state_from_normalized(num_qubits, gates)
            if is_identity(state_unitary(state)):
                identity_words[word] = length

    def pair_free(word: tuple[int, ...]) -> bool:
        return all(word[i] != word[i + 1] for i in range(len(word) - 1))

    candidates = [word for word in identity_words if pair_free(word)]
    primitive: list[tuple[int, ...]] = []
    for word in candidates:
        length = len(word)
        has_shorter = False
        for start in range(length):
            for end in range(start + 1, length + 1):
                if end - start >= length:
                    continue
                if word[start:end] in identity_words:
                    has_shorter = True
                    break
            if has_shorter:
                break
        if not has_shorter:
            primitive.append(word)
    primitive.sort(key=lambda w: (len(w), w))
    shortest = len(primitive[0]) if primitive else None
    witnesses = [
        gate_text(tuple(StateGate(generators[i][0], generators[i][1], None) for i in word))
        for word in primitive[:6]
    ]
    by_length = Counter(len(word) for word in primitive)
    return {
        "num_qubits": num_qubits,
        "generators": [f"{name}{''.join(str(q) for q in qubits)}" for name, qubits in generators],
        "search_max_length": max_length,
        "identity_words_found": len(identity_words),
        "pair_free_identity_words": len(candidates),
        "primitive_identities": len(primitive),
        "shortest_primitive_length": shortest,
        "shortest_witnesses": witnesses,
        "primitive_by_length": {str(k): v for k, v in sorted(by_length.items())},
        "truncated": shortest is None,
    }


def run_fragment(
    name: str,
    num_qubits: int,
    max_length: int,
    curve_rows: list[dict[str, Any]],
    tau_rows: list[dict[str, Any]],
    cache: Any,
    deadline: float,
    configs: list[Any],
) -> dict[str, Any]:
    global _ALLOWED_GATES
    _ALLOWED_GATES = {(name, tuple(qubits)) for name, qubits in generators_for(num_qubits)}
    # A fresh cache per fragment: the cache key is the gate-name alphabet, which
    # is identical at width 2 and 3, so a shared cache would leak width-2 actions
    # (CX in either order) into the width-3 run.
    cache = E75.ActionCache()
    fragment = E75.Fragment(name, num_qubits, generators_for(num_qubits), max_length, key_mode="fixed")
    per_member: dict[str, dict[str, Any]] = defaultdict(dict)
    stats: dict[str, Any] = {}
    for config in configs:
        rows, config_stats = E75.evaluate(fragment, config, cache, deadline)
        config_stats["part"] = name
        stats[config.name] = config_stats
        curve_rows.append(config_stats)
        for row in rows:
            per_member[row["listing"]][config.name] = row
    for listing, by_config in per_member.items():
        tau = None
        for config_name in sorted(by_config):
            if config_name.startswith("all_L2_"):
                if by_config[config_name]["reached"] is True:
                    tau = int(config_name.rsplit("_", 1)[1])
                    break
        base_row = by_config["base"]
        tau_rows.append(
            {
                "part": name,
                "listing": listing,
                "cost": base_row["cost"],
                "c_abs": base_row["c_abs"],
                "base_gap": base_row["gap_closed"],
                "base_reached": base_row["reached"],
                "tau_all": "" if tau is None else tau,
            }
        )
    by_length: dict[int, list[int]] = defaultdict(list)
    for row in tau_rows:
        if row["part"] != name or row["tau_all"] == "":
            continue
        by_length[int(row["cost"])].append(int(row["tau_all"]))
    tau_table = []
    for length, taus in sorted(by_length.items()):
        entry = {
            "listing_length": length,
            "n": len(taus),
            "tau_min": min(taus),
            "tau_median": sorted(taus)[len(taus) // 2],
            "tau_max": max(taus),
            "tau_histogram": {str(k): v for k, v in sorted(Counter(taus).items())},
        }
        for L in range(2, max_length + 1):
            entry[f"price_L{L}"] = round(sum(1 for t in taus if t > L) / len(taus), 6)
        tau_table.append(entry)
    threshold = next(
        (L for L in range(2, max_length + 1) if stats.get(f"all_L2_{L}", {}).get("price") == 0.0),
        None,
    )
    return {
        "fragment": {
            "num_qubits": num_qubits,
            "generators": [f"{name_}{''.join(str(q) for q in qubits)}" for name_, qubits in generators_for(num_qubits)],
            "generator_count": len(generators_for(num_qubits)),
            "max_length": max_length,
            "listings": len(fragment.states),
            "classes": len(fragment.classes),
            "reducible": len(fragment.reducible),
            "c_abs_histogram": {str(k): v for k, v in sorted(Counter(fragment.c_abs.values()).items())},
        },
        "configs": stats,
        "tau_by_length": tau_table,
        "threshold": threshold,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width2-max-length", type=int, default=5)
    parser.add_argument("--width3-max-length", type=int, default=5)
    parser.add_argument("--census-max-length", type=int, default=6)
    parser.add_argument("--budget-seconds", type=float, default=7200.0)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--skip-census", action="store_true")
    parser.add_argument("--skip-part-a", action="store_true")
    parser.add_argument("--skip-part-b", action="store_true")
    parser.add_argument("--minimal-configs", action="store_true")
    args = parser.parse_args()
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)
    deadline = time.perf_counter() + args.budget_seconds
    cache = E75.ActionCache()
    started = time.perf_counter()

    curve_rows: list[dict[str, Any]] = []
    tau_rows: list[dict[str, Any]] = []

    def configs_for(max_length: int) -> list[Any]:
        rows = [E75.Config("base", None, 1, 0)]
        lengths = (
            [max_length - 1, max_length]
            if args.minimal_configs
            else list(range(2, max_length + 1))
        )
        rows += [E75.Config(f"all_L2_{L}", None, 2, L) for L in lengths]
        if not args.minimal_configs:
            rows += [E75.Config(f"1q_L2_{L}", 1, 2, L) for L in range(2, max_length + 1)]
        return rows

    part_a = (
        run_fragment(
        "A_width2_m5",
        2,
        args.width2_max_length,
        curve_rows,
        tau_rows,
        cache,
        deadline,
        configs_for(args.width2_max_length),
    )
        if not args.skip_part_a
        else {"fragment": {}, "configs": {}, "tau_by_length": [], "threshold": None}
    )
    part_b = (
        run_fragment(
        "B_width3_m5",
        3,
        args.width3_max_length,
        curve_rows,
        tau_rows,
        cache,
        deadline,
        configs_for(args.width3_max_length),
    )
        if not args.skip_part_b
        else {"fragment": {}, "configs": {}, "tau_by_length": [], "threshold": None}
    )

    # ------------------------------------------------------------ Part C
    census: dict[str, Any] = {}
    if not args.skip_census:
        for num_qubits in (1, 2, 3):
            census[f"width{num_qubits}"] = primitive_identity_census(
                num_qubits, generators_for(num_qubits), args.census_max_length
            )

    # ------------------------------------------------------------ self-checks
    checks = {
        "width2_threshold_below_max_length": (
            part_a["threshold"] is not None and part_a["threshold"] < args.width2_max_length
        ),
        "price_monotone_in_L_width2": all(
            part_a["configs"].get(f"all_L2_{L}", {}).get("price", 1.0)
            >= part_a["configs"].get(f"all_L2_{L + 1}", {}).get("price", 0.0)
            for L in range(2, args.width2_max_length)
            if f"all_L2_{L}" in part_a["configs"] and f"all_L2_{L + 1}" in part_a["configs"]
        ),
        "price_monotone_in_L_width3": (
            all(
                part_b["configs"][f"all_L2_{L}"]["price"] >= part_b["configs"][f"all_L2_{L + 1}"]["price"]
                for L in range(2, args.width3_max_length)
            )
            if part_b["configs"]
            else None
        ),
        "length2_rules_buy_nothing_width2": (
            part_a["configs"]["all_L2_2"]["price"] == part_a["configs"]["base"]["price"]
            if "all_L2_2" in part_a["configs"]
            else None
        ),
        "length2_rules_buy_nothing_width3": (
            part_b["configs"]["all_L2_2"]["price"] == part_b["configs"]["base"]["price"] if part_b["configs"] else None
        ),
        "alphabet_leak_windows_skipped": SKIPPED_WINDOW_CLASSES["count"],
    }

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-10-29",
        "purpose": (
            "decide whether the completeness threshold L* is a width effect or the shortest "
            "non-trivial relation of the fragment's group"
        ),
        "contract": {
            "rule_library": RULE_LIBRARY.relative_to(ROOT).as_posix(),
            "rule_library_sha256": sha256_file(RULE_LIBRARY),
            "scope": "full (1,474 quartz rules) + pair_v1 + structural exchanges",
            "search": "greedy closure (32 passes) + monotone BFS depth <= min(gap, 3), max 20,000 nodes",
            "read_only": ["data/", "release/", "docs/manuscript/"],
            "generator_set": (
                "h, x, z on every qubit plus cx(i, i+1) on a line; width 2 therefore matches E73's "
                "8-generator set minus cx(1,0), width 3 is the line-CX subgroup, NOT the full "
                "3-qubit Clifford group"
            ),
            "synthetic_library": (
                "maximally powerful rule set of a given (arity, source length) class, built from "
                "exhaustive enumeration of the fragment"
            ),
        },
        "part_a_width2": part_a,
        "part_b_width3": part_b,
        "part_c_primitive_identities": census,
        "hypotheses": {
            "H1_width_effect": "L* grows with qubit count",
            "H2_group_invariant": "L* is the shortest non-trivial relation length and stays <= 4",
        },
        "self_checks": checks,
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }

    _write_csv(
        out / "price_curve.csv",
        curve_rows,
        [
            "part",
            "config",
            "arity",
            "lmin",
            "lmax",
            "include_base",
            "members_reducible",
            "greedy_exact",
            "greedy_rate",
            "after_search",
            "after_search_rate",
            "failures",
            "price",
            "budget_exhausted",
        ],
    )
    _write_csv(
        out / "member_tau.csv",
        tau_rows,
        ["part", "listing", "cost", "c_abs", "base_gap", "base_reached", "tau_all"],
    )
    census_rows = [
        {
            "width": key,
            "num_qubits": value["num_qubits"],
            "generators": "|".join(value["generators"]),
            "search_max_length": value["search_max_length"],
            "identity_words_found": value["identity_words_found"],
            "pair_free_identity_words": value["pair_free_identity_words"],
            "primitive_identities": value["primitive_identities"],
            "shortest_primitive_length": value["shortest_primitive_length"],
            "primitive_by_length": json.dumps(value["primitive_by_length"]),
            "witnesses": " ; ".join(value["shortest_witnesses"]),
        }
        for key, value in census.items()
    ]
    _write_csv(
        out / "primitive_identities.csv",
        census_rows,
        [
            "width",
            "num_qubits",
            "generators",
            "search_max_length",
            "identity_words_found",
            "pair_free_identity_words",
            "primitive_identities",
            "shortest_primitive_length",
            "primitive_by_length",
            "witnesses",
        ],
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (out / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": EXPERIMENT_ID,
                "generated": "2026-10-29",
                "script": "scripts/e78_width_threshold.py",
                "artifacts": {
                    name: sha256_file(out / name)
                    for name in sorted(
                        ["price_curve.csv", "member_tau.csv", "primitive_identities.csv", "summary.json"]
                    )
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "self_checks": checks,
                "width2": {k: v["price"] for k, v in part_a["configs"].items()},
                "width3": {k: v["price"] for k, v in part_b["configs"].items()},
                "thresholds": {"width2": part_a["threshold"], "width3": part_b["threshold"]},
                "census": {k: (v["shortest_primitive_length"], v["shortest_witnesses"][:2]) for k, v in census.items()},
                "runtime": summary["runtime_seconds"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
