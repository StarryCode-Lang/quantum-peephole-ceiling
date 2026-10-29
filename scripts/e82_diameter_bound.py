"""E82: the completeness threshold is bounded by the Cayley diameter.

Motivation
----------
E78/E81 measured a "length ladder": on the 2-qubit Clifford fragment the
completeness threshold equals the *instance* length (``L* = m`` at m = 5, 6, 7),
with a positive residue at every measured point.  Round 19 read that as an
unbounded ladder and promoted it to the main-journal route.

This experiment tests that reading with a different algorithm -- an exact
Cayley distance oracle over the fragment's group -- and finds the opposite:

    L*(m) <= min(m, D + 1),   D = Cayley diameter of the fragment,

so the ladder cannot ascend past ``D + 1``.  Every E78/E81 measurement sits in
the *trivial* regime ``m <= D + 1``, where the bound is not binding.

Why the bound holds (three lines, no search)
--------------------------------------------
Let ``w`` be a word of length ``m`` with ``d(w) < m`` and let ``i`` be the
smallest index with ``d(w[1..i]) < i``.  Then ``w[1..i-1]`` is geodesic, so
``i - 1 = d(w[1..i-1]) <= D``, i.e. ``i <= D + 1``.  The prefix ``w[1..i]`` is
non-geodesic, so replacing it by a geodesic word of the same element strictly
lowers the cost.  Iterating terminates at a word all of whose prefixes are
geodesic, i.e. at cost ``d(element) = c_abs``.  Only windows of length
``<= D + 1`` are ever used.

Corollary: the completeness price ``P(L, m)`` is exactly 0 for every ``L >= D+1``
and every ``m``.  The price is a fragment invariant (its diameter), not a
property of how the library was designed.

Contract
--------
Read-only.  Frozen inputs: E78/E81/E80 summaries (validation only) and the
frozen rule library (hashed for provenance).  Nothing under ``data/``,
``release/`` or ``docs/manuscript/`` is written.  No simulation is needed for
the census: the fragment's cost *is* word length, so the Cayley graph is the
complete cost model.  A qiskit Clifford BFS is run as an independent
cross-check of the distance distribution, and two explicit witnesses are
checked by unitary equality.

Outputs (``docs/review/science_boost/2026-10-30_diameter_bound/``)
    distance_histogram.csv   exact distance distribution, both fragments
    ladder_census.csv        one row per m: locally-rigid words, residues, price
    witnesses.json           explicit T-7 counterexamples and their certificates
    summary.json             contract, theorem, validation, self-checks
    MANIFEST.json            sha256 of every artifact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-30_diameter_bound"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
E78_SUMMARY = ROOT / "docs" / "review" / "science_boost" / "2026-10-29_width_threshold" / "summary.json"
E81_SUMMARY = ROOT / "docs" / "review" / "science_boost" / "2026-10-29_rule_length_demand" / "ladder_m7.json"
E80_SUMMARY = ROOT / "docs" / "review" / "science_boost" / "2026-10-29_rule_length_demand" / "summary.json"

EXPERIMENT_ID = "E82_DIAMETER_BOUND_2026_10_30"
NAMES_W2 = ["h0", "x0", "z0", "h1", "x1", "z1", "cx01", "cx10"]
NAMES_Q1 = ["h0", "s0", "x0", "z0"]


# --------------------------------------------------------------------- algebra
# A Clifford tableau mod global phase: ``A`` is a tuple of 2n row masks over
# 2n columns (row i = image of Pauli generator i, ordered X_0..X_{n-1}, Z_0..
# Z_{n-1}), ``s`` is a 2n-bit sign mask.  The canonical operator of a row is
# ``prod_j X_j^a Z_j^b`` with all X factors before all Z factors, which makes
# (A, s) a complete invariant: for n = 2 there are exactly 11520 of them.


def _identity(n: int) -> tuple[tuple[int, ...], int]:
    return (tuple(1 << i for i in range(2 * n)), 0)


def compose_fast(left, right, n: int):
    """Tableau of ``left`` applied *after* ``right`` (``W = left . right``).

    The image of ``P_i`` under ``W`` is the product, over ``j`` in the support of
    ``A_left[i]``, of the signed canonical strings ``(-1)^{s_right_j} C(A_right_j)``.
    Multiplying canonical strings obeys
    ``(X^x Z^z)(X^x' Z^z') = (-1)^{z.x'} X^{x+x'} Z^{z+z'}``, so the running
    product must carry that cocycle term.  Dropping it (the naive
    ``A_left . s_right`` formula) still generates the right *set* but the wrong
    Cayley metric -- it produced 283/394/55 instead of 291/418/23 at distances
    4/5/7.  Caught by the qiskit cross-check below.
    """

    la, ls = left
    ra, rs = right
    low = (1 << n) - 1
    rows = []
    signs = 0
    for i in range(2 * n):
        xacc = 0
        zacc = 0
        sign = (ls >> i) & 1
        row = la[i]
        for j in range(2 * n):
            if (row >> j) & 1:
                sign ^= (rs >> j) & 1
                xj = ra[j] & low
                zj = (ra[j] >> n) & low
                sign ^= bin(zacc & xj).count("1") & 1
                xacc ^= xj
                zacc ^= zj
        rows.append(xacc | (zacc << n))
        signs |= sign << i
    return (tuple(rows), signs)


def generators(n: int, names: Iterable[str]) -> list[tuple[str, tuple[tuple[int, ...], int]]]:
    """Tableaus for the named generators on ``n`` qubits."""

    table: dict[str, tuple[tuple[int, ...], int]] = {}
    for q in range(n):
        x, z = q, n + q
        rows = [1 << i for i in range(2 * n)]
        rows[x], rows[z] = 1 << z, 1 << x
        table[f"h{q}"] = (tuple(rows), 0)
        rows = [1 << i for i in range(2 * n)]
        rows[x] = (1 << x) | (1 << z)  # X -> Y (projective XZ)
        table[f"s{q}"] = (tuple(rows), 0)
        table[f"x{q}"] = (tuple(1 << i for i in range(2 * n)), 1 << z)
        table[f"z{q}"] = (tuple(1 << i for i in range(2 * n)), 1 << x)
    for c in range(n):
        for t in range(n):
            if c == t:
                continue
            rows = [1 << i for i in range(2 * n)]
            rows[c] = (1 << c) | (1 << t)  # X_c -> X_c X_t
            rows[n + t] = (1 << (n + c)) | (1 << (n + t))  # Z_t -> Z_c Z_t
            table[f"cx{c}{t}"] = (tuple(rows), 0)
    return [(name, table[name]) for name in names]


def build_group(n: int, gens) -> tuple[dict[Any, int], dict[int, int]]:
    """BFS over the generated subgroup; returns (element -> distance, histogram)."""

    ident = _identity(n)
    dist = {ident: 0}
    frontier = [ident]
    depth = 0
    histogram: Counter[int] = Counter({0: 1})
    while frontier:
        depth += 1
        nxt = []
        for element in frontier:
            for _, gen in gens:
                child = compose_fast(gen, element, n)
                if child not in dist:
                    dist[child] = depth
                    nxt.append(child)
        if nxt:
            histogram[depth] = len(nxt)
        frontier = nxt
    return dist, dict(sorted(histogram.items()))


def word_element(word, gmap, n: int):
    element = _identity(n)
    for name in word:
        element = compose_fast(gmap[name], element, n)
    return element


def qiskit_histogram(names: list[str], n: int) -> dict[int, int] | None:
    """Independent BFS over qiskit ``Clifford`` objects (different code path)."""

    try:
        from qiskit import QuantumCircuit
        from qiskit.quantum_info import Clifford
    except Exception:  # pragma: no cover - qiskit optional
        return None

    def circuit(word: Iterable[str]) -> QuantumCircuit:
        qc = QuantumCircuit(n)
        for name in word:
            if name.startswith("cx"):
                qc.cx(int(name[2]), int(name[3]))
            elif name[0] == "h":
                qc.h(int(name[1]))
            elif name[0] == "s":
                qc.s(int(name[1]))
            elif name[0] == "x":
                qc.x(int(name[1]))
            elif name[0] == "z":
                qc.z(int(name[1]))
        return qc

    def key(clifford) -> tuple:
        array = clifford.tableau
        return tuple(
            (tuple(int(v) for v in array[i][:-1]), int(array[i][-1])) for i in range(array.shape[0])
        )

    start = Clifford(QuantumCircuit(n))
    gens = [Clifford(circuit([name])) for name in names]
    dist = {key(start): 0}
    frontier = [(key(start), start)]
    depth = 0
    histogram: Counter[int] = Counter({0: 1})
    while frontier:
        depth += 1
        nxt = []
        for _, clifford in frontier:
            for gen in gens:
                child = clifford.compose(gen)
                child_key = key(child)
                if child_key not in dist:
                    dist[child_key] = depth
                    nxt.append((child_key, child))
        if nxt:
            histogram[depth] = len(nxt)
        frontier = nxt
    return dict(sorted(histogram.items()))


# ------------------------------------------------------------------ census
def locally_rigid_census(dist, gmap, n: int, max_m: int, cap: int = 400_000):
    """Count, per length ``m``, the words whose *proper* windows are all geodesic.

    ``F_m`` = words of length ``m`` all of whose windows (the whole word
    included) are geodesic.  ``LR_m`` (locally rigid) = words of length ``m``
    all of whose *proper* windows are geodesic; those are exactly the words on
    which a rule set of maximal source length ``m-1`` has no legal action at
    all, so ``c_{m-1}(w) = cost(w)`` for them.
    """

    names = list(gmap)
    f_sets: dict[int, list[tuple[str, ...]]] = {0: [()]}
    rows: list[dict[str, Any]] = []
    truncated = False
    for m in range(1, max_m + 1):
        lr_count = 0
        lr_gap = 0
        lr_gap1 = 0
        examples: list[dict[str, Any]] = []
        f_m: list[tuple[str, ...]] = []
        for prefix in f_sets[m - 1]:
            # suffix elements of the prefix: suf[i] = element(prefix[i:])
            # suffix[i] = matrix of prefix[i:]; the leftmost gate of a suffix is
            # applied *first*, so it sits at the right end of the product.
            suffix: list[Any] = [None] * (m - 1)
            element = _identity(n)
            for i in range(m - 2, -1, -1):
                element = compose_fast(element, gmap[prefix[i]], n)
                suffix[i] = element
            for name in names:
                gen = gmap[name]
                ok = True
                for i in range(1, m):
                    window = compose_fast(gen, suffix[i], n) if i < m - 1 else gen
                    if dist.get(window, 1 << 30) != m - i:
                        ok = False
                        break
                if not ok:
                    continue
                full = compose_fast(gen, suffix[0], n) if m > 1 else gen
                distance = dist.get(full, 1 << 30)
                lr_count += 1
                if distance < m:
                    lr_gap += 1
                    if distance == m - 1:
                        lr_gap1 += 1
                    if len(examples) < 3:
                        examples.append({"word": list(prefix) + [name], "distance": distance})
                else:
                    if len(f_m) < cap:
                        f_m.append(prefix + (name,))
                    else:
                        truncated = True
        f_sets[m] = f_m
        rows.append(
            {
                "m": m,
                "total_words": len(names) ** m,
                "geodesic_words_all_windows": len(f_m),
                "locally_rigid_words": lr_count,
                "locally_rigid_with_gap": lr_gap,
                "locally_rigid_gap1": lr_gap1,
                "residue_examples": examples,
            }
        )
    return rows, truncated


def _lr_words(dist, gmap, n: int, target_m: int) -> list[tuple[str, ...]]:
    """All words of length ``target_m`` whose proper windows are geodesic."""

    names = list(gmap)
    f_sets: dict[int, list[tuple[str, ...]]] = {0: [()]}
    for m in range(1, target_m + 1):
        collected: list[tuple[str, ...]] = []
        f_m: list[tuple[str, ...]] = []
        for prefix in f_sets[m - 1]:
            # suffix[i] = matrix of prefix[i:]; the leftmost gate of a suffix is
            # applied *first*, so it sits at the right end of the product.
            suffix: list[Any] = [None] * (m - 1)
            element = _identity(n)
            for i in range(m - 2, -1, -1):
                element = compose_fast(element, gmap[prefix[i]], n)
                suffix[i] = element
            for name in names:
                gen = gmap[name]
                ok = True
                for i in range(1, m):
                    window = compose_fast(gen, suffix[i], n) if i < m - 1 else gen
                    if dist.get(window, 1 << 30) != m - i:
                        ok = False
                        break
                if not ok:
                    continue
                full = compose_fast(gen, suffix[0], n) if m > 1 else gen
                if m == target_m:
                    collected.append(prefix + (name,))
                if dist.get(full, 1 << 30) == m:
                    f_m.append(prefix + (name,))
        f_sets[m] = f_m
    return collected


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def shortest_word(target, gmap, dist, n: int) -> list[str] | None:
    """One geodesic word for ``target`` by greedy descent (prepending letters)."""

    names = list(gmap)
    word: list[str] = []
    element = target
    guard = 0
    while dist[element] > 0 and guard < 64:
        guard += 1
        want = dist[element] - 1
        for name in names:
            # element = gen . rest  =>  rest = gen^{-1} . element
            candidate = compose_fast(_inverse(gmap[name], n), element, n)
            if candidate in dist and dist[candidate] == want:
                word.append(name)
                element = candidate
                break
        else:  # pragma: no cover - BFS guarantees a descent exists
            return None
    word.reverse()
    return word


def _inverse(tableau, n: int):
    """Inverse of a projective Clifford (order <= 12 in these fragments)."""

    ident = _identity(n)
    if tableau == ident:
        return ident
    power = tableau
    for _ in range(24):
        if power == ident:
            break
        power = compose_fast(tableau, power, n)
    # ``power`` is now the identity; the previous one is the inverse.
    element = ident
    for _ in range(24):
        candidate = compose_fast(tableau, element, n)
        if candidate == ident:
            return element
        element = candidate
    return element  # pragma: no cover


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-m", type=int, default=9)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    gens_w2 = generators(2, NAMES_W2)
    gmap_w2 = dict(gens_w2)
    dist_w2, hist_w2 = build_group(2, gens_w2)
    diameter_w2 = max(dist_w2.values())

    gens_q1 = generators(1, NAMES_Q1)
    gmap_q1 = dict(gens_q1)
    dist_q1, hist_q1 = build_group(1, gens_q1)
    diameter_q1 = max(dist_q1.values())

    e81 = json.loads(E81_SUMMARY.read_text(encoding="utf-8"))
    e78 = json.loads(E78_SUMMARY.read_text(encoding="utf-8"))
    e80 = json.loads(E80_SUMMARY.read_text(encoding="utf-8"))

    cumulative: dict[int, int] = {}
    running = 0
    for d in sorted(hist_w2):
        running += hist_w2[d]
        cumulative[d] = running

    qiskit_w2 = qiskit_histogram(NAMES_W2, 2)
    qiskit_q1 = qiskit_histogram(NAMES_Q1, 1)

    validation = {
        "w2_group_order_1152": len(dist_w2) == 1152,
        "w2_classes_at_m5_match_e78": cumulative.get(5) == e78["part_a_width2"]["fragment"]["classes"],
        "w2_classes_at_m6_match_e78": cumulative.get(6) == 1129,
        "w2_classes_at_m7_match_e81": cumulative.get(7) == e81["contract"]["classes"],
        "w2_histogram_matches_e81_bit_exact": {str(k): v for k, v in hist_w2.items()}
        == {str(k): v for k, v in e81["class_histogram"].items()},
        "w2_histogram_matches_qiskit_bit_exact": qiskit_w2 is not None and hist_w2 == qiskit_w2,
        "q1_group_order_24": len(dist_q1) == 24,
        "q1_classes_match_e80": len(dist_q1) == e80["part_a"]["fragment"]["classes"],
        "q1_histogram_matches_qiskit_bit_exact": qiskit_q1 is not None and hist_q1 == qiskit_q1,
    }

    rows, truncated = locally_rigid_census(dist_w2, gmap_w2, 2, args.max_m)
    alphabet = len(NAMES_W2)
    for row in rows:
        row["price_of_length_m_minus_1_library"] = round(
            row["locally_rigid_with_gap"] / (alphabet**row["m"]), 8
        )
        row["l_star_upper_bound"] = min(row["m"], diameter_w2 + 1)
        row["in_trivial_regime"] = row["m"] <= diameter_w2 + 1
    rows_q1, _ = locally_rigid_census(dist_q1, gmap_q1, 1, min(args.max_m, 8))

    # explicit witnesses + independent unitary check
    witnesses: list[dict[str, Any]] = []
    for row in rows:
        for example in row["residue_examples"][:2]:
            witnesses.append({"fragment": "W2", "m": row["m"], **example})
    for row in rows_q1:
        for example in row["residue_examples"][:2]:
            witnesses.append({"fragment": "Q1", "m": row["m"], **example})

    unitary_checks: list[dict[str, Any]] = []
    try:
        from qiskit import QuantumCircuit
        from qiskit.quantum_info import Operator

        def circuit_of(word: Iterable[str], n: int) -> QuantumCircuit:
            qc = QuantumCircuit(n)
            for name in word:
                if name.startswith("cx"):
                    qc.cx(int(name[2]), int(name[3]))
                elif name[0] == "h":
                    qc.h(int(name[1]))
                elif name[0] == "s":
                    qc.s(int(name[1]))
                elif name[0] == "x":
                    qc.x(int(name[1]))
                elif name[0] == "z":
                    qc.z(int(name[1]))
            return qc

        for item in witnesses[:6]:
            n = 2 if item["fragment"] == "W2" else 1
            gmap = gmap_w2 if n == 2 else gmap_q1
            dist = dist_w2 if n == 2 else dist_q1
            target = word_element(item["word"], gmap, n)
            representative = shortest_word(target, gmap, dist, n)
            if representative is None:
                unitary_checks.append({"word": item["word"], "status": "NO_REPRESENTATIVE"})
                continue
            left = Operator(circuit_of(item["word"], n)).data
            right = Operator(circuit_of(representative, n)).data
            overlap = abs((left.conj().T @ right).trace()) / left.shape[0]
            unitary_checks.append(
                {
                    "fragment": item["fragment"],
                    "word": item["word"],
                    "word_length": len(item["word"]),
                    "distance": dist[target],
                    "representative": representative,
                    "overlap": float(round(float(abs(overlap)), 9)),
                    "equivalent": bool(abs(abs(overlap) - 1.0) < 1e-9),
                }
            )
    except Exception as exc:  # pragma: no cover - qiskit optional
        unitary_checks.append({"status": f"SKIPPED:{type(exc).__name__}:{exc}"})

    library_census: dict[str, Any] = {}
    if RULE_LIBRARY.exists():
        payload = json.loads(RULE_LIBRARY.read_text(encoding="utf-8"))
        lengths: Counter[int] = Counter()
        for rule in payload["rules"]:
            source = rule.get("source") or {}
            value = source.get("gate_count")
            if isinstance(value, int):
                lengths[value] += 1
        library_census = {
            "rules": len(payload["rules"]),
            "source_length_histogram": {str(k): v for k, v in sorted(lengths.items())},
            "max_source_length": max(lengths) if lengths else None,
            "rules_with_length_at_least_4": sum(v for k, v in lengths.items() if k >= 4),
            "rules_with_length_at_least_8": sum(v for k, v in lengths.items() if k >= 8),
        }

    def residue_at(m: int) -> int | None:
        return next((row["locally_rigid_with_gap"] for row in rows if row["m"] == m), None)

    # ---- subset cross-check against E78's dumped m=6 residue list
    subset_check: dict[str, Any] = {}
    residue_csv = E78_SUMMARY.parent / "width2_m6_residue.csv"
    if residue_csv.exists():
        with residue_csv.open(encoding="utf-8", newline="") as handle:
            frozen = {row["listing"] for row in csv.DictReader(handle) if row["cost"] == "6"}
        mine = {
            ".".join(example["word"])
            for row in rows
            if row["m"] == 6
            for example in row["residue_examples"]
        }
        # examples are capped at 3 per row, so recompute the full set for m = 6
        full_m6 = _lr_words(dist_w2, gmap_w2, 2, 6)
        mine_full = {".".join(word) for word in full_m6 if dist_w2[word_element(word, gmap_w2, 2)] < 6}
        subset_check = {
            "e78_m6_residue_rows": len(frozen),
            "our_m6_stuck_words": len(mine_full),
            "all_ours_are_in_e78_residue": mine_full <= frozen,
            "missing_examples": sorted(mine_full - frozen)[:5],
            "capped_examples_all_in_residue": mine <= frozen,
        }

    checks = {
        **validation,
        "diameter_w2_is_7": diameter_w2 == 7,
        "diameter_q1_is_4": diameter_q1 == 4,
        "ladder_truncates_above_d_plus_1": all(
            row["locally_rigid_words"] == 0 for row in rows if row["m"] > diameter_w2 + 1
        ),
        "q1_bound_is_attained": e80["part_a"]["threshold"] == diameter_q1 + 1,
        "gap1_at_m6_is_4664": next(
            (row["locally_rigid_gap1"] for row in rows if row["m"] == 6), None
        )
        == 4664,
        "gap1_at_m7_is_7056": next(
            (row["locally_rigid_gap1"] for row in rows if row["m"] == 7), None
        )
        == 7056,
        "stuck_at_m8_positive": next(
            (row["locally_rigid_gap1"] for row in rows if row["m"] == 8), 0
        )
        > 0,
        "stuck_at_m9_zero": next(
            (row["locally_rigid_gap1"] for row in rows if row["m"] == 9), None
        )
        == 0,
        "unitary_checks_pass": (
            all(item.get("equivalent") is True for item in unitary_checks) if unitary_checks else None
        ),
        "census_not_truncated": not truncated,
    }

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-10-30",
        "purpose": "test whether the completeness-threshold ladder is unbounded (T-7) or capped by the fragment's Cayley diameter",
        "contract": {
            "fragments": {
                "W2": {"qubits": 2, "generators": NAMES_W2, "matches": "E78 part_a_width2 / E81 m=7"},
                "Q1": {"qubits": 1, "generators": NAMES_Q1, "matches": "E80 part_a (24-element Clifford)"},
            },
            "cost_model": "fragment gate count == Cayley word length; the group is the complete cost model",
            "read_only": ["data/", "release/", "docs/manuscript/"],
            "rule_library": RULE_LIBRARY.relative_to(ROOT).as_posix(),
            "rule_library_sha256": sha256_file(RULE_LIBRARY) if RULE_LIBRARY.exists() else None,
            "algorithm": "exact BFS on the projective Clifford tableau (A, s); independent of E78/E81's word enumeration, cross-checked against qiskit Clifford",
        },
        "theorem": {
            "id": "T-9",
            "statement": "For a fragment with Cayley diameter D, the length-L completeness threshold satisfies L*(m) <= min(m, D+1) for every m; hence P(L, m) = 0 for every L >= D+1 and every m.",
            "proof": "Let i be the smallest index with d(w[1..i]) < i. Then w[1..i-1] is geodesic so i-1 <= D, i.e. i <= D+1; replacing that prefix by a geodesic word strictly lowers cost. Iterate until every prefix is geodesic.",
            "consequence": "T-7 (unbounded ladder) is false for m >= D+2; every E78/E81 measurement lies in the trivial regime m <= D+1.",
        },
        "fragments": {
            "W2": {
                "group_order": len(dist_w2),
                "diameter": diameter_w2,
                "distance_histogram": {str(k): v for k, v in hist_w2.items()},
                "qiskit_histogram": {str(k): v for k, v in (qiskit_w2 or {}).items()},
                "cumulative_classes": {str(k): v for k, v in cumulative.items()},
                "l_star_bound": diameter_w2 + 1,
            },
            "Q1": {
                "group_order": len(dist_q1),
                "diameter": diameter_q1,
                "distance_histogram": {str(k): v for k, v in hist_q1.items()},
                "qiskit_histogram": {str(k): v for k, v in (qiskit_q1 or {}).items()},
                "l_star_bound": diameter_q1 + 1,
            },
        },
        "ladder": rows,
        "ladder_q1": rows_q1,
        "library_census": library_census,
        "witnesses": witnesses,
        "subset_check": subset_check,
        "unitary_checks": unitary_checks,
        "self_checks": checks,
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }

    with (out / "distance_histogram.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["fragment", "distance", "elements", "cumulative", "qiskit_elements"])
        run = 0
        for d in sorted(hist_w2):
            run += hist_w2[d]
            writer.writerow(["W2", d, hist_w2[d], run, (qiskit_w2 or {}).get(d, "")])
        run = 0
        for d in sorted(hist_q1):
            run += hist_q1[d]
            writer.writerow(["Q1", d, hist_q1[d], run, (qiskit_q1 or {}).get(d, "")])

    with (out / "ladder_census.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "m",
            "total_words",
            "geodesic_words_all_windows",
            "locally_rigid_words",
            "locally_rigid_with_gap",
            "locally_rigid_gap1",
            "price_of_length_m_minus_1_library",
            "l_star_upper_bound",
            "in_trivial_regime",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})

    (out / "witnesses.json").write_text(
        json.dumps({"witnesses": witnesses, "unitary_checks": unitary_checks}, indent=2),
        encoding="utf-8",
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (out / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": EXPERIMENT_ID,
                "generated": "2026-10-30",
                "script": "scripts/e82_diameter_bound.py",
                "artifacts": {
                    name: sha256_file(out / name)
                    for name in sorted(
                        n
                        for n in [
                            "distance_histogram.csv",
                            "ladder_census.csv",
                            "witnesses.json",
                            "summary.json",
                        ]
                        if (out / n).exists()
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
                "W2": summary["fragments"]["W2"]["distance_histogram"],
                "Q1": summary["fragments"]["Q1"]["distance_histogram"],
                "ladder": [
                    {k: row[k] for k in ("m", "locally_rigid_words", "locally_rigid_with_gap", "price_of_length_m_minus_1_library")}
                    for row in rows
                ],
                "runtime": summary["runtime_seconds"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
