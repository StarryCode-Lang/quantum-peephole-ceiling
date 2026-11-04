"""E91: the rigidity floor, counted exactly instead of witnessed once.

Motivation
----------
`LF-1` (round 21) proves that a rewrite library of maximal source length ``L``
has *no legal action* on a listing whose every proper window is geodesic, and
that such a listing exists at ``m = D + 1`` (``D`` = the fragment's Cayley
diameter).  It is an existence statement with a hand-built witness.  Round 22's
action list asked for two things this script supplies:

1. turn the witness into a **number**: what fraction of length-``D+1`` listings
   admits no legal action at all under a length-``<= D`` library;
2. turn existence into a **density**: the same fraction as a function of
   ``(m, L)``, so the floor can be compared with the measured price curve.

Method
------
Everything is counting on the Cayley graph, so no search and no sampling is
involved.  Two exact dynamic programs:

``geodesic_counts``
    ``G[m]`` = number of words of length ``m`` whose product has Cayley
    distance exactly ``m`` (i.e. geodesic words).  DP over (element, length).

``valid_counts``
    ``V(m, L)`` = number of words of length ``m`` in which **every** contiguous
    window of length ``<= L`` is geodesic.  Those are exactly the listings on
    which a library of maximal source length ``L`` has no legal action: a rule
    of source length ``k <= L`` can only fire on a window of length ``k`` that
    is *not* geodesic.  DP state = the last ``L - 1`` generators, because a
    window of length ``k < L`` that is non-geodesic sits inside some length-``L``
    window, which is then non-geodesic too; checking all length-``L`` windows
    therefore implies the whole family.

    For ``m < L`` no length-``L`` window exists, and validity reduces to "the
    whole word is geodesic", so ``V(m, L) = G[m]`` there.

The quantity reported is

    rho(m, L) = (V(m, L) - G[m]) / (A**m - G[m])

the fraction of **reducible** listings of length ``m`` on which *no reducing rule
of source length <= L exists at all*.  Those listings are the "locally
irreducible" class: the library can only move them with cost-neutral rules, if
it has any.

``rho`` is **not** ordered against the measured completeness price.  E75's
search contract admits cost-neutral actions (``actions_for`` with
``strictly_reducing=False``), so a locally irreducible listing can still be
walked to its optimum; E87's measured price at ``(m=6, L=5)`` is 4.03% while
``rho(6, 5)`` is 5.26%, which is only possible for that reason.  ``rho`` is a
property of the ``(fragment, L)`` pair; the price is a property of the
``(fragment, library, search contract)`` triple.

``m = D + 1`` with ``L = D`` cannot use the generic DP (``A**(D-1)`` states), so
it is computed by the two-window identity

    LR_{D+1} = sum_{g, T} N(g, T) * #{s : d(U_s . T) = D}

where ``N(g, T)`` counts length-``D`` geodesic words whose first gate is ``g``
and whose *tail* product (gates 2..D) is ``T``.  Both windows of a length-``D+1``
word are then geodesic by construction.  The identity is cross-checked against
the generic DP on the 1-qubit fragment, where ``A**(D-1) = 4**3`` is enumerable.

Contract
--------
Read-only on frozen inputs.  Nothing under ``data/``, ``release/`` or
``docs/manuscript/`` is written.  The cost model *is* word length, so the Cayley
graph is exact; no unitary simulation is needed and no qiskit call is made.

Outputs (``docs/review/science_boost/2026-11-04_rigidity_floor/``)
    rigidity_floor.csv   one row per (fragment, L, m)
    summary.json         contract, results, self-checks, provenance
    MANIFEST.json        sha256 of every artifact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

e84 = importlib.import_module("e84_panel_gate_diameter")

OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-11-04_rigidity_floor"
EXPERIMENT_ID = "E91_RIGIDITY_FLOOR_2026_11_04"

PANEL_2Q = list(e84.PANEL_2Q)          # {h,x,z,s}^2 + both CX: order 11,520, D = 9
PANEL_1Q = list(e84.PANEL_1Q)          # {h,x,z,s}: order 24, D = 4

FRAGMENTS = [
    ("panel_1q", 1, PANEL_1Q, "the 1-qubit panel basis; D = 4, A = 4"),
    ("panel_2q", 2, PANEL_2Q, "the 2-qubit panel basis; D = 9, A = 10"),
]


class Group:
    """Index-addressed Cayley graph with precomputed left multiplication."""

    def __init__(self, n: int, names: Iterable[str]):
        self.n = n
        self.names = list(names)
        pairs = e84.generators_z4(n, self.names)
        if len(pairs) != len(self.names):
            raise RuntimeError("generator_construction_failed")
        dist_map, histogram = e84.build_group_z4(n, pairs)
        self.elements = list(dist_map)
        self.index = {element: i for i, element in enumerate(self.elements)}
        self.distance = [dist_map[element] for element in self.elements]
        self.histogram = histogram
        self.diameter = max(self.distance)
        self.alphabet = len(self.names)
        gen_elements = [dict(pairs)[name] for name in self.names]
        self.generator_index = [self.index[element] for element in gen_elements]
        # Convention (reversed product): for a word w_1..w_m, w_1 applied first,
        # P(w) = U_{w_1} . ... . U_{w_m} = U(w)^-1.  Cayley distance is invariant
        # under inversion, so every geodesic test below is exact, and appending a
        # gate to the *end* of a word is a right multiplication, which keeps the
        # state recursion one-sided.
        #   left[s][e]  = U_s . U_e
        #   right[s][e] = U_e . U_s
        self.left: list[list[int]] = []
        self.right: list[list[int]] = []
        for gen_element in gen_elements:
            self.left.append(
                [
                    self.index[e84.compose_z4(gen_element, element, n)]
                    for element in self.elements
                ]
            )
            self.right.append(
                [
                    self.index[e84.compose_z4(element, gen_element, n)]
                    for element in self.elements
                ]
            )
        self.identity = self.index[e84.compose_z4(pairs[0][1], pairs[0][1], n)]
        if self.identity != 0:
            # compose of a generator with its own inverse is the identity; the
            # index table is built from BFS order, so locate it explicitly.
            ident = (tuple(1 << i for i in range(2 * n)), tuple(0 for _ in range(2 * n)))
            self.identity = self.index[ident]


def geodesic_counts(group: Group, max_m: int) -> list[int]:
    """``G[m]`` = number of length-``m`` words whose product has distance ``m``."""

    counts = [1] + [0] * max_m
    frontier: dict[int, int] = {group.identity: 1}
    for m in range(1, max_m + 1):
        nxt: dict[int, int] = {}
        for element, count in frontier.items():
            for s in range(group.alphabet):
                child = group.right[s][element]
                if group.distance[child] == m:
                    nxt[child] = nxt.get(child, 0) + count
        counts[m] = sum(nxt.values())
        frontier = nxt
    return counts


def _state_products(group: Group, width: int) -> dict[tuple[int, ...], int]:
    """Product element of every generator tuple of the given width."""

    products: dict[tuple[int, ...], int] = {}

    def build(prefix: tuple[int, ...]) -> int:
        if prefix in products:
            return products[prefix]
        if not prefix:
            products[prefix] = group.identity
            return group.identity
        head, rest = prefix[0], prefix[1:]
        value = group.left[head][build(rest)]
        products[prefix] = value
        return value

    if width == 0:
        products[()] = group.identity
        return products
    stack: list[tuple[int, ...]] = [()]
    while stack:
        current = stack.pop()
        if len(current) == width:
            build(current)
            continue
        for s in range(group.alphabet):
            stack.append(current + (s,))
    return products


def valid_counts(group: Group, length_cap: int, max_m: int) -> list[int]:
    """``V(m, L)`` for fixed ``L`` = ``length_cap``, ``m`` up to ``max_m``.

    ``V(m, L)`` counts words of length ``m`` in which every window of length
    ``<= L`` is geodesic.  Returns a list indexed by ``m`` (entries below
    ``L - 1`` are filled with ``G[m]`` semantics by the caller).
    """

    out = [0] * (max_m + 1)
    width = length_cap - 1
    products = _state_products(group, width)
    states: dict[tuple[int, ...], int] = {}
    for state, element in products.items():
        if len(state) == width and group.distance[element] == width:
            states[state] = 1
    out[width] = len(states)
    for m in range(length_cap, max_m + 1):
        nxt: dict[tuple[int, ...], int] = {}
        for state, count in states.items():
            element = products[state]
            for s in range(group.alphabet):
                window = group.right[s][element]
                if group.distance[window] != length_cap:
                    continue
                tail = state[1:] + (s,)
                nxt[tail] = nxt.get(tail, 0) + count
        states = nxt
        out[m] = sum(states.values())
    return out


def locally_rigid_at_diameter(group: Group) -> dict[str, Any]:
    """``LR_{D+1}`` by the two-window identity (no ``A**(D-1)`` state space)."""

    target = group.diameter + 1
    tail_length = group.diameter - 1  # gates 2..D
    # N[g][T] = number of length-D geodesic words with first gate g and tail product T
    # (reversed-product convention: T = U_{w_2} . ... . U_{w_D})
    tables: list[dict[int, int]] = []
    for g in range(group.alphabet):
        frontier: dict[int, int] = {group.identity: 1}  # tail of the 1-gate word [g]
        for k in range(1, target - 1):  # extend to length D
            nxt: dict[int, int] = {}
            for tail, count in frontier.items():
                for s in range(group.alphabet):
                    new_tail = group.right[s][tail]
                    # full product of the word [g, ..., s] is (U_g . new_tail)
                    if group.distance[group.left[g][new_tail]] != k + 1:
                        continue
                    nxt[new_tail] = nxt.get(new_tail, 0) + count
            frontier = nxt
        tables.append(frontier)

    total = 0
    for g in range(group.alphabet):
        for tail, count in tables[g].items():
            # the second window is [w_2..w_D, s], whose product is tail . U_s
            extensions = sum(
                1
                for s in range(group.alphabet)
                if group.distance[group.right[s][tail]] == group.diameter
            )
            total += count * extensions
    return {
        "m": target,
        "L": group.diameter,
        "locally_rigid_words": total,
        "total_words": group.alphabet**target,
        "density": total / group.alphabet**target,
        "per_first_gate": {group.names[g]: sum(tables[g].values()) for g in range(group.alphabet)},
        "tail_length": tail_length,
    }


def brute_force_valid(group: Group, length_cap: int, m: int) -> int:
    """Independent enumeration of ``V(m, L)`` for tiny ``m`` (self-check only)."""

    total = 0
    alphabet = group.alphabet
    for code in range(alphabet**m):
        word = []
        rest = code
        for _ in range(m):
            word.append(rest % alphabet)
            rest //= alphabet
        word.reverse()
        ok = True
        for i in range(m):
            for j in range(i + 1, min(i + length_cap, m) + 1):
                element = group.identity
                for gate in word[i:j]:
                    element = group.left[gate][element]
                if group.distance[element] != j - i:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            total += 1
    return total


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-m", type=int, default=14)
    args = parser.parse_args()

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    details: dict[str, Any] = {}

    for name, n, generators, note in FRAGMENTS:
        group = Group(n, generators)
        print(f"[E91] {name}: order={len(group.elements)} D={group.diameter} A={group.alphabet}")
        max_m = min(args.max_m, group.diameter + 5)
        geodesic = geodesic_counts(group, max_m)
        per_fragment: dict[str, Any] = {
            "group_order": len(group.elements),
            "diameter": group.diameter,
            "alphabet": group.alphabet,
            "generators": generators,
            "histogram": group.histogram,
            "geodesic_counts": {m: geodesic[m] for m in range(max_m + 1)},
            "note": note,
        }
        for length_cap in range(2, group.diameter):
            valid = valid_counts(group, length_cap, max_m)
            for m in range(length_cap - 1, max_m + 1):
                if m < length_cap:
                    valid[m] = geodesic[m]
                reducible = group.alphabet**m - geodesic[m]
                no_action = valid[m] - geodesic[m]
                rows.append(
                    {
                        "fragment": name,
                        "L": length_cap,
                        "m": m,
                        "alphabet": group.alphabet,
                        "total_words": group.alphabet**m,
                        "geodesic_words": geodesic[m],
                        "valid_words": valid[m],
                        "reducible_words": reducible,
                        "locally_irreducible_words": no_action,
                        "rho": (no_action / reducible) if reducible else 0.0,
                    }
                )
            per_fragment[f"L{length_cap}"] = {
                str(m): valid[m] for m in range(length_cap - 1, max_m + 1)
            }
        details[name] = per_fragment

    # ---- m = D + 1 at L = D, the LF-1 extremal point -----------------------
    extremes: dict[str, Any] = {}
    for name, n, generators, _ in FRAGMENTS:
        group = Group(n, generators)
        extreme = locally_rigid_at_diameter(group)
        extremes[name] = extreme
        rows.append(
            {
                "fragment": name,
                "L": extreme["L"],
                "m": extreme["m"],
                "alphabet": group.alphabet,
                "total_words": extreme["total_words"],
                "geodesic_words": 0,
                "valid_words": extreme["locally_rigid_words"],
                "reducible_words": extreme["total_words"],
                "locally_irreducible_words": extreme["locally_rigid_words"],
                "rho": extreme["density"],
            }
        )
        print(
            f"[E91] {name} m=D+1={extreme['m']} L={extreme['L']}: "
            f"LR={extreme['locally_rigid_words']} rho={extreme['density']:.3e}"
        )

    # ---- self-checks -------------------------------------------------------
    checks: dict[str, Any] = {}
    g1 = Group(1, PANEL_1Q)
    g2 = Group(2, PANEL_2Q)
    checks["panel_2q_order_11520"] = len(g2.elements) == 11520
    checks["panel_2q_diameter_9"] = g2.diameter == 9
    checks["panel_1q_order_24"] = len(g1.elements) == 24
    checks["panel_1q_diameter_4"] = g1.diameter == 4

    # brute force agreement on small m (1q, L=2..3)
    g1_geodesic = geodesic_counts(g1, 5)
    checks["geodesic_counts_match_bruteforce_1q_m4"] = (
        g1_geodesic[4] == brute_force_valid(g1, 4, 4)
    )
    v1_3 = valid_counts(g1, 3, 5)
    checks["valid_counts_match_bruteforce_1q_L3_m5"] = v1_3[5] == brute_force_valid(g1, 3, 5)

    # two-window identity vs generic DP on the 1-qubit fragment (D = 4, L = 4)
    extreme_1q = extremes["panel_1q"]
    v1_4 = valid_counts(g1, 4, 5)
    checks["two_window_identity_matches_generic_dp_1q"] = v1_4[5] == extreme_1q["locally_rigid_words"]

    # exhaustive agreement on the panel alphabet, where sampling cannot hide a bug
    v2_4 = valid_counts(g2, 4, 5)
    checks["valid_counts_match_bruteforce_panel_L4_m5"] = v2_4[5] == brute_force_valid(g2, 4, 5)

    # T-9 consistency: at m = L the price is zero by construction
    zero_rows = [r for r in rows if r["m"] == r["L"]]
    checks["rho_zero_at_m_equals_L"] = all(r["locally_irreducible_words"] == 0 for r in zero_rows)

    # Cross-experiment alignment: E87's fragment denominators are exactly
    # sum_{k<=m} (A**k - G_k).  Reproducing them from the G sequence alone ties
    # this count to a published number rather than to another code path.
    e87_path = ROOT / "docs" / "review" / "science_boost" / "2026-11-02_panel_price_recheck" / "summary.json"
    if e87_path.exists():
        e87 = json.loads(e87_path.read_text(encoding="utf-8"))
        g6 = geodesic_counts(g2, 6)
        m5_reducible = sum(10**k - g6[k] for k in range(0, 6))
        m6_reducible = sum(10**k - g6[k] for k in range(0, 7))
        checks["e87_part_b_reducible_m5_reproduced"] = (
            m5_reducible == e87["part_b_panel"]["meta"]["reducible"]
        )
        checks["e87_part_d_reducible_m6_reproduced"] = (
            m6_reducible == e87["part_d_panel_m6"]["configs"]["all_L2_5"]["members_reducible"]
        )

    # E82's ``locally_rigid_census`` is NOT a valid cross-check here: it runs on
    # E82's sign-only tableau, whose metric E84 showed is wrong on any generator
    # set containing ``s`` (274/983 vs 272/967 at distances 4/5).  Round 20 used
    # it on the Y-free fragment W2, where it is exact; on the panel set it is not.
    # The brute-force checks above are the replacement.
    checks["e82_census_metric_note"] = "sign-only tableau; exact on W2, not on the panel set"

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "contract": {
            "frozen_inputs": "none (pure group computation on the declared generator sets)",
            "cost_model": "word length = Cayley distance; no unitary simulation",
            "writes": ["docs/review/science_boost/2026-11-04_rigidity_floor/"],
            "reads": [],
        },
        "definitions": {
            "G_m": "number of length-m words whose product has Cayley distance m",
            "V_m_L": "number of length-m words in which every window of length <= L is geodesic",
            "rho": "(V(m,L) - G_m) / (A**m - G_m), the locally irreducible fraction at (fragment, L, m)",
            "rho_vs_price": "not ordered: E75 admits cost-neutral actions, so rho may exceed the measured price",
        },
        "fragments": details,
        "extremal_m_D_plus_1": extremes,
        "self_checks": checks,
        "versions": {"python": sys.version.split()[0]},
    }

    with (OUTPUT_ROOT / "rigidity_floor.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (OUTPUT_ROOT / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "artifacts": {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in sorted(OUTPUT_ROOT.glob("*"))
            if path.is_file() and path.name != "MANIFEST.json"
        },
    }
    with (OUTPUT_ROOT / "MANIFEST.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)

    failed = [key for key, value in checks.items() if value is False]
    print(f"[E91] self-checks: {sum(1 for v in checks.values() if v is True)} true / {len(failed)} false")
    for row in rows:
        if row["fragment"] == "panel_2q" and row["L"] == 5:
            print(f"[E91] panel_2q L=5 m={row['m']}: rho={row['rho']:.6f}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
