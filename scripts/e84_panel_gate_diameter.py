"""E84: the panel gate set's own Cayley diameter, and what round 20 actually measured.

Motivation
----------
Round 20 (`T-9`) proved `L*(m) <= min(m, D+1)` for a fragment of Cayley diameter
`D`, then measured `D = 7` on a fragment `W2` with generator set

    {h0, x0, z0, h1, x1, z1, cx01, cx10}

and compared that 7 with the shipped library's maximum rule source length (5),
concluding that "the production library is 3 levels short of the 2-qubit
Clifford threshold".

Two things are wrong with that comparison, and this experiment measures both.

1. **`W2` is not the 2-qubit Clifford group.**  The group it generates has order
   **1,152**, while the 2-qubit Clifford group modulo global phase has order
   **11,520**.  `{h, x, z}` generate the order-8 group `<h,x>` on one qubit
   (round 19, D5), and `z = s^2` cannot manufacture the missing `s`.  So `W2`
   is a subgroup of index 10 and its diameter is not the Clifford diameter.
   E82's qiskit cross-check passed because qiskit was handed the same eight
   generators -- it reproduced the *subgroup* bit-exactly, which is why the
   error survived.  Right group check, wrong group.

2. **The generator set must be the panel's, not a convenient one.**  The
   project's circuits live in the basis `{h, x, rz, cx}`.  `rz(theta)` is a
   single native gate for every angle, so `rz(pi) = -i Z` and
   `rz(pi/2) = e^{-i pi/4} S` are each reachable at cost **1**: the panel basis
   contains `s` for free.  `cx` in the basis translator means any
   control/target pair, so `cx10` is also cost 1.  Hence the panel generator
   set is `{h, x, z, s}` per qubit plus both CX directions, which generates the
   full 11,520 and has a *different* diameter.

Contract
--------
Read-only.  Frozen inputs: the rule library (hashed) and the E80/E82 summaries
(validation only).  Nothing under `data/`, `release/` or `docs/manuscript/` is
written.  The fragment's cost *is* word length, so the Cayley graph is the
complete cost model; no unitary simulation is needed.  qiskit's own Clifford
BFS is run as an independent cross-check of every reported diameter.

Outputs (``docs/review/science_boost/2026-10-31_panel_diameter/``)
    diameter_table.csv     one row per generator set: order, D, histogram, threshold
    element_distances.csv  distance of every 2-qubit Clifford element, panel set
    summary.json           contract, result, self-checks, provenance
    MANIFEST.json          sha256 of every artifact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
e82 = importlib.import_module("e82_diameter_bound")

OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-31_panel_diameter"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
E80_SUMMARY = ROOT / "docs" / "review" / "science_boost" / "2026-10-29_rule_length_demand" / "summary.json"
E82_SUMMARY = ROOT / "docs" / "review" / "science_boost" / "2026-10-30_diameter_bound" / "summary.json"

EXPERIMENT_ID = "E84_PANEL_GATE_DIAMETER_2026_10_31"

# Every listed gate is a *native* panel gate at cost 1.
#   rz is native and continuous  =>  z = rz(pi), s = rz(pi/2), sdg = rz(-pi/2)
#   cx is native for any control/target pair in the basis translator
PANEL_2Q = ["h0", "h1", "x0", "x1", "z0", "z1", "s0", "s1", "cx01", "cx10"]
PANEL_2Q_ONE_CX = ["h0", "h1", "x0", "x1", "z0", "z1", "s0", "s1", "cx01"]
PANEL_1Q = ["h0", "x0", "z0", "s0"]
W2_ROUND20 = ["h0", "x0", "z0", "h1", "x1", "z1", "cx01", "cx10"]
VARIANT_NO_S = ["h0", "h1", "x0", "x1", "z0", "z1", "cx01", "cx10"]
VARIANT_NO_S_ONE_CX = ["h0", "h1", "x0", "x1", "z0", "z1", "cx01"]
VARIANT_NO_X = ["h0", "h1", "z0", "z1", "s0", "s1", "cx01", "cx10"]

FRAGMENTS = [
    (
        "panel_2q",
        2,
        PANEL_2Q,
        "the project's basis {h,x,rz,cx}: rz makes z and s cost 1; cx native in both directions",
    ),
    ("panel_2q_one_cx", 2, PANEL_2Q_ONE_CX, "same, but the reverse CX costs 4 h + 1 cx (not a generator)"),
    ("panel_1q", 1, PANEL_1Q, "the 1-qubit panel basis {h,x,rz}: the 24-element Clifford group"),
    ("w2_round20", 2, W2_ROUND20, "round 20's W2: no s, both CX -- order 1152, an index-10 subgroup"),
    ("no_s_both_cx", 2, VARIANT_NO_S, "panel set minus the phase gate (isolates the s contribution)"),
    ("no_s_one_cx", 2, VARIANT_NO_S_ONE_CX, "round 20's generator set minus cx10"),
    ("no_x", 2, VARIANT_NO_X, "panel set minus x (x = h z h, so this should be a no-op up to 2 gates)"),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def qiskit_generator_check(names: Iterable[str], n: int) -> dict[str, Any] | None:
    """Bit-for-bit comparison of the hand-built tableaus with qiskit's.

    This is the guard that catches a wrong sign/phase convention *before* it
    becomes a wrong diameter: a wrong generator still generates the right group.
    """

    try:
        from qiskit import QuantumCircuit
        from qiskit.quantum_info import Clifford
    except Exception:  # pragma: no cover
        return None

    mismatches: list[str] = []
    for name in names:
        qc = QuantumCircuit(n)
        if name.startswith("cx"):
            qc.cx(int(name[2]), int(name[3]))
        else:
            gate = name.rstrip("0123456789")
            qubit = int(name[len(gate) :]) if name[len(gate) :] else 0
            getattr(qc, gate)(qubit)
        rows = Clifford(qc).tableau.tolist()
        expected_mask = [sum(int(row[j]) << j for j in range(2 * n)) for row in rows]
        expected_sign = sum(int(row[2 * n]) << i for i, row in enumerate(rows))
        actual = dict(generators_z4(n, [name]))[name]
        phases = list(actual[1])
        # qiskit's phase column is a +/- sign, so it is only comparable when every
        # image has an even Z4 phase; an odd phase is a Y-type image whose
        # representative qiskit normalises differently.  The masks must match always.
        comparable = all(phase % 2 == 0 for phase in phases)
        sign = sum((phase // 2) << i for i, phase in enumerate(phases))
        if list(actual[0]) != expected_mask or (comparable and sign != expected_sign):
            mismatches.append(name)
    return {"checked": list(names), "mismatches": mismatches, "ok": not mismatches}


def generators_z4(n: int, names: Iterable[str]) -> list[tuple[str, tuple[tuple[int, ...], tuple[int, ...]]]]:
    """Generators as (rows, Z4 phases) so that no ``i`` factor is ever dropped.

    E82's tableau keeps only a +/- sign per row, which is a complete invariant of
    a Clifford *up to global phase* only when every row's canonical string is
    free of ``Y``.  ``S`` is the first generator that is not: ``S X S^dagger = Y``
    and ``Y = i XZ``, so the image needs phase 1 (mod 4), not sign 0.  Dropping
    that ``i`` still generates the right group -- and gets the metric slightly
    wrong on a few dozen elements, which is exactly what the qiskit cross-check
    reported (274/983/... vs 272/967/...).  Tracking ``p in Z4`` per row and
    canonicalising ``p_0 = 0`` fixes it and reproduces qiskit exactly.
    """

    table: dict[str, tuple[tuple[int, ...], tuple[int, ...]]] = {}
    for q in range(n):
        x, z = q, n + q
        ident = tuple(1 << i for i in range(2 * n))
        zero = tuple(0 for _ in range(2 * n))
        rows = list(ident)
        rows[x], rows[z] = 1 << z, 1 << x
        table[f"h{q}"] = (tuple(rows), zero)
        rows = list(ident)
        rows[x] = (1 << x) | (1 << z)
        phases = list(zero)
        phases[x] = 1  # X -> Y = i XZ
        table[f"s{q}"] = (tuple(rows), tuple(phases))
        phases = list(zero)
        phases[x] = 3  # X -> -Y = -i XZ
        table[f"sdg{q}"] = (tuple(rows), tuple(phases))
        phases = list(zero)
        phases[z] = 2  # Z -> -Z
        table[f"x{q}"] = (ident, tuple(phases))
        phases = list(zero)
        phases[x] = 2  # X -> -X
        table[f"z{q}"] = (ident, tuple(phases))
    for c in range(n):
        for t in range(n):
            if c == t:
                continue
            rows = list(tuple(1 << i for i in range(2 * n)))
            rows[c] = (1 << c) | (1 << t)
            rows[n + t] = (1 << (n + c)) | (1 << (n + t))
            table[f"cx{c}{t}"] = (tuple(rows), tuple(0 for _ in range(2 * n)))
    return [(name, table[name]) for name in names]


def compose_z4(left, right, n: int):
    """Tableau of ``left`` applied *after* ``right``, with exact Z4 phases.

    ``(L . R)(P_i) = L(R(P_i))``, and ``R(P_i) = i^{rp_i} C(A_R[i])`` where
    ``C`` is the canonical "all X before all Z" string.  Applying ``L`` to each
    factor of ``C`` gives ``i^{rp_i} * prod_j i^{lp_j} C(A_L[j])``, with the
    ``(-1)^{z.x'}`` cocycle for the accumulated product.  Getting the two phase
    vectors the wrong way round still generates the right *group* but the wrong
    *metric* -- the same class of error as E82's dropped ``i``, and it shows up
    only as a handful of elements at each distance.
    """

    la, lp = left
    ra, rp = right
    low = (1 << n) - 1
    rows = []
    phases = []
    for i in range(2 * n):
        xacc = 0
        zacc = 0
        phase = rp[i]
        row = ra[i]
        for j in range(2 * n):
            if (row >> j) & 1:
                phase += lp[j]
                xj = la[j] & low
                zj = (la[j] >> n) & low
                phase += 2 * (bin(zacc & xj).count("1") & 1)
                xacc ^= xj
                zacc ^= zj
        rows.append(xacc | (zacc << n))
        phases.append(phase % 4)
    # No canonicalisation: a global phase on W cancels in W P W^dagger, so the
    # images -- and hence ``p`` -- are an exact invariant, not a class label.
    # Shifting ``p`` by a constant would change the element (that mistake gave a
    # 23,040-element "group" and a diameter of 6 on a 24-element group).
    return (tuple(rows), tuple(p % 4 for p in phases))


def build_group_z4(n: int, gens) -> tuple[dict[Any, int], dict[int, int]]:
    ident = (tuple(1 << i for i in range(2 * n)), tuple(0 for _ in range(2 * n)))
    dist = {ident: 0}
    frontier = [ident]
    depth = 0
    histogram: Counter[int] = Counter({0: 1})
    while frontier:
        depth += 1
        nxt = []
        for element in frontier:
            for _, gen in gens:
                child = compose_z4(gen, element, n)
                if child not in dist:
                    dist[child] = depth
                    nxt.append(child)
        if nxt:
            histogram[depth] = len(nxt)
        frontier = nxt
    return dist, dict(sorted(histogram.items()))


def panel_cx_directions() -> dict[str, Any]:
    """Count CX directions in the frozen 128-source panel (read-only).

    The generator set ``PANEL_2Q`` grants ``cx10`` at cost 1.  That is only
    legitimate if the panel's own circuits actually use both directions; this
    census is the evidence, and it is why the headline number is 9 and not 11.
    """

    files = sorted((ROOT / "data" / "v16" / "e45_full_development" / "qasm").glob("*.qasm"))
    pattern = re.compile(r"cx\s+q\[(\d+)\],\s*q\[(\d+)\]")
    forward = reversed_ = 0
    files_with_reverse = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [(int(m.group(1)), int(m.group(2))) for m in pattern.finditer(text)]
        local_reverse = sum(1 for c, t in hits if c > t)
        forward += sum(1 for c, t in hits if c < t)
        reversed_ += local_reverse
        files_with_reverse += 1 if local_reverse else 0
    return {
        "files": len(files),
        "cx_forward": forward,
        "cx_reversed": reversed_,
        "files_with_reversed_cx": files_with_reverse,
        "both_directions_present": forward > 0 and reversed_ > 0,
    }


def locally_rigid_witness(dist, gmap, n: int, length: int, attempts: int = 4000, seed: int = 20261031):
    """Randomised search for a word of ``length`` all of whose suffixes are geodesic.

    Such a word has every proper window geodesic, so no rule whose source pattern
    is shorter than ``length`` can fire anywhere in it and its library cost equals
    its length.  Its existence certifies ``LR_length > 0``, which is exactly the
    hypothesis of the length-floor lemma: a library whose maximum source length is
    below ``length`` has a *strictly positive* completeness price at ``m = length``.
    """

    rng = random.Random(seed)
    names = list(gmap)
    ident = (tuple(1 << i for i in range(2 * n)), tuple(0 for _ in range(2 * n)))
    for _ in range(attempts):
        word: list[str] = []
        suffixes: list[Any] = []  # suffixes[i] = element of word[i:]
        ok = True
        for _step in range(length):
            candidates = names[:]
            rng.shuffle(candidates)
            placed = False
            for name in candidates:
                gen = gmap[name]
                new_suffixes = [compose_z4(gen, element, n) for element in suffixes] + [gen]
                # only *proper* suffixes must be geodesic: at length D+1 the whole
                # word can never be geodesic (its distance is at most D), which is
                # precisely why LR_{D+1} > 0 is a statement about windows, not words.
                if all(
                    dist.get(element) == len(new_suffixes) - i
                    for i, element in enumerate(new_suffixes)
                    if i >= 1
                ):
                    word.append(name)
                    suffixes = new_suffixes
                    placed = True
                    break
            if not placed:
                ok = False
                break
        if ok and len(word) == length:
            element = ident
            for name in word:
                element = compose_z4(gmap[name], element, n)
            return {
                "word": word,
                "length": length,
                "distance_of_word": dist.get(element),
                "gap": length - dist.get(element, length),
                "proper_windows_all_geodesic": True,
                "found": True,
            }
    return {"word": [], "length": length, "found": False}


def rule_source_lengths() -> dict[str, int]:
    """Source pattern length of every rule in the frozen library."""

    payload = json.loads(RULE_LIBRARY.read_text(encoding="utf-8"))
    rules = payload["rules"] if isinstance(payload, dict) and "rules" in payload else payload
    lengths: dict[str, int] = {}
    for rule in rules:
        source = rule.get("source")
        rule_id = rule.get("rule_id") or rule.get("id") or ""
        if isinstance(source, dict):
            lengths[rule_id] = int(source.get("gate_count") or len(source.get("operations") or []))
        elif isinstance(source, list):
            lengths[rule_id] = len(source)
        else:
            lengths[rule_id] = 0
    return lengths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-qiskit", action="store_true")
    args = parser.parse_args()

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    table_rows: list[dict[str, Any]] = []
    details: dict[str, Any] = {}
    for name, n, gens, note in FRAGMENTS:
        pairs = generators_z4(n, gens)
        if len(pairs) != len(gens):
            raise SystemExit(f"generator construction failed for {name}")
        dist, histogram = build_group_z4(n, pairs)
        diameter = max(dist.values())
        table_rows.append(
            {
                "fragment": name,
                "n_qubits": n,
                "generator_count": len(gens),
                "generators": " ".join(gens),
                "group_order": len(dist),
                "diameter": diameter,
                "threshold_L_star_upper": diameter + 1,
                "histogram": json.dumps(histogram, sort_keys=True),
                "note": note,
            }
        )
        details[name] = {"distance": dist, "histogram": histogram, "diameter": diameter}
        print(f"[E84] {name}: order={len(dist)} D={diameter} L*<={diameter + 1} hist={histogram}")

    panel = details["panel_2q"]
    panel_dist = panel["distance"]
    panel_d = panel["diameter"]

    qiskit_checks: dict[str, Any] = {}
    gen_check = qiskit_generator_check(["h0", "x0", "z0", "s0", "sdg0", "cx01"], 2)
    print(f"[E84] generator tableau check: {gen_check}")
    if not args.skip_qiskit:
        for name, n, gens, _ in FRAGMENTS:
            hist = e82.qiskit_histogram(gens, n)
            qiskit_checks[name] = {
                "order": sum(hist.values()) if hist else None,
                "diameter": max(hist) if hist else None,
                "matches": hist == details[name]["histogram"] if hist else None,
            }
            print(f"[E84] qiskit {name}: {qiskit_checks[name]}")

    # Documented divergence: E82's sign-only engine on a generator set containing s.
    e82_divergence: dict[str, Any] = {}
    for name in ("panel_2q", "w2_round20", "panel_1q"):
        entry = next(f for f in FRAGMENTS if f[0] == name)
        _, hist_e82 = e82.build_group(entry[1], e82.generators(entry[1], entry[2]))
        e82_divergence[name] = {
            "matches_z4": hist_e82 == details[name]["histogram"],
            "e82_histogram": hist_e82,
        }
    print(f"[E84] E82 engine divergence: {json.dumps(e82_divergence, sort_keys=True)}")

    panel_cx = panel_cx_directions()
    print(f"[E84] panel CX directions: {panel_cx}")
    rigid = {}
    for name in ("panel_2q", "w2_round20"):
        entry = next(f for f in FRAGMENTS if f[0] == name)
        gmap = dict(generators_z4(entry[1], entry[2]))
        rigid[name] = locally_rigid_witness(details[name]["distance"], gmap, entry[1], details[name]["diameter"] + 1)
        print(f"[E84] locally rigid witness {name}: {rigid[name]}")

    lengths = rule_source_lengths()
    positive = [v for v in lengths.values() if v > 0]
    max_len = max(positive) if positive else 0
    length_hist = dict(sorted(Counter(positive).items()))

    round20_d = details["w2_round20"]["diameter"]
    e80 = json.loads(E80_SUMMARY.read_text(encoding="utf-8")) if E80_SUMMARY.exists() else {}
    e80_part_a = e80.get("part_a", {}) if isinstance(e80, dict) else {}
    e80_lstar = e80_part_a.get("threshold_L_star")
    q1_d = details["panel_1q"]["diameter"]

    checks = {
        "panel_2q_order_is_11520": len(panel_dist) == 11520,
        "panel_1q_order_is_24": len(details["panel_1q"]["distance"]) == 24,
        "w2_order_is_1152_not_11520": len(details["w2_round20"]["distance"]) == 1152,
        "w2_reproduces_round20_diameter_7": round20_d == 7,
        "w2_reproduces_round20_histogram": details["w2_round20"]["histogram"]
        == {0: 1, 1: 8, 2: 37, 3: 121, 4: 291, 5: 418, 6: 253, 7: 23},
        "q1_reproduces_round20_histogram": details["panel_1q"]["histogram"] == {0: 1, 1: 4, 2: 8, 3: 9, 4: 2},
        "q1_bound_attained_matches_e80": (e80_lstar is None) or (e80_lstar == q1_d + 1),
        "qiskit_matches_every_fragment": all(v.get("matches") for v in qiskit_checks.values()),
        "e82_engine_is_exact_without_s": e82_divergence["w2_round20"]["matches_z4"],
        "e82_engine_diverges_with_s": e82_divergence["panel_2q"]["matches_z4"] is False,
        "adding_s_grows_the_group_to_11520": len(details["no_s_both_cx"]["distance"]) == 1152
        and len(panel_dist) == 11520,
        "removing_x_costs_one_level": details["no_x"]["diameter"] == panel_d + 1,
        "generator_tableaus_match_qiskit": (gen_check or {}).get("ok"),
        "library_max_length_is_5": max_len == 5,
        "library_rule_total_is_1488": len(lengths) == 1488,
        "library_positive_length_rules_is_1462": len(positive) == 1462,
        "panel_uses_both_cx_directions": panel_cx["both_directions_present"],
        "panel_2q_has_locally_rigid_word_at_d_plus_1": rigid["panel_2q"]["found"],
        "w2_has_locally_rigid_word_at_d_plus_1": rigid["w2_round20"]["found"],
    }

    with (OUTPUT_ROOT / "element_distances.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["index", "distance", "tableau_rows", "z4_phases"])
        for index, (element, distance) in enumerate(sorted(panel_dist.items(), key=lambda kv: kv[1])):
            writer.writerow(
                [
                    index,
                    distance,
                    "|".join(str(row) for row in element[0]),
                    "|".join(str(phase) for phase in element[1]),
                ]
            )

    with (OUTPUT_ROOT / "diameter_table.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table_rows[0]))
        writer.writeheader()
        writer.writerows(table_rows)

    summary = {
        "experiment": EXPERIMENT_ID,
        "as_of": "2026-10-31",
        "contract": {
            "writes_under_data": False,
            "writes_under_release": False,
            "writes_under_manuscript": False,
            "cost_model": "word length over the fragment's native generators; the Cayley graph is exact",
            "no_simulation": "the fragment's cost is word length, so no unitary simulation is required",
        },
        "question": (
            "what is the Cayley diameter of the panel gate set, and is the shipped library's maximum "
            "source length (5) at or above its threshold D+1?"
        ),
        "answer": {
            "panel_2q_diameter": panel_d,
            "panel_2q_threshold_upper": panel_d + 1,
            "panel_2q_one_cx_diameter": details["panel_2q_one_cx"]["diameter"],
            "panel_1q_diameter": q1_d,
            "panel_1q_threshold_upper": q1_d + 1,
            "round20_w2_diameter": round20_d,
            "round20_w2_order": len(details["w2_round20"]["distance"]),
            "clifford_2q_order": 11520,
            "library_max_source_length": max_len,
            "library_length_histogram": length_hist,
            "gap_under_round20_comparison": max_len - (round20_d + 1),
            "gap_under_panel_comparison": max_len - (panel_d + 1),
            "verdict": "PANEL_BUDGET_SHORT_BY_%d" % ((panel_d + 1) - max_len)
            if max_len < panel_d + 1
            else "PANEL_BUDGET_SUFFICIENT",
            "round20_claim_status": "WITHDRAWN_AS_UNDERCOUNT_WRONG_GROUP",
            "one_qubit_reading": {
                "threshold": q1_d + 1,
                "library_budget": max_len,
                "budget_meets_threshold": max_len >= q1_d + 1,
                "e80_complete_library_price_at_threshold": (
                    e80_part_a.get("configs", {}).get(f"all_L2_{q1_d + 1}", {}).get("price")
                ),
                "e80_shipped_library_price": e80_part_a.get("configs", {}).get("base", {}).get("price"),
                "e80_threshold": e80_part_a.get("threshold"),
                "implication": "at L = D+1 a complete library has price 0, so a positive price at L = D+1 is coverage, not length",
            },
        },
        "attribution": {
            "s_effect_on_diameter": details["no_s_both_cx"]["diameter"] - panel_d,
            "s_effect_on_group_order": len(panel_dist) - len(details["no_s_both_cx"]["distance"]),
            "cx_direction_effect": details["panel_2q_one_cx"]["diameter"] - panel_d,
            "x_effect": details["no_x"]["diameter"] - panel_d,
        },
        "fragments": {row["fragment"]: {k: v for k, v in row.items() if k != "note"} for row in table_rows},
        "qiskit_cross_checks": qiskit_checks,
        "e80_part_a": e80_part_a,
        "self_checks": checks,
        "provenance": {
            "rule_library": {"path": str(RULE_LIBRARY.relative_to(ROOT)), "sha256": sha256_file(RULE_LIBRARY)},
            "e80_summary": {"path": str(E80_SUMMARY.relative_to(ROOT)), "sha256": sha256_file(E80_SUMMARY)}
            if E80_SUMMARY.exists()
            else None,
            "e82_summary": {"path": str(E82_SUMMARY.relative_to(ROOT)), "sha256": sha256_file(E82_SUMMARY)}
            if E82_SUMMARY.exists()
            else None,
        },
    }
    (OUTPUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "experiment": EXPERIMENT_ID,
        "files": {
            path.name: sha256_file(path)
            for path in sorted(OUTPUT_ROOT.iterdir())
            if path.is_file() and path.name != "MANIFEST.json"
        },
    }
    (OUTPUT_ROOT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {"answer": summary["answer"], "attribution": summary["attribution"], "self_checks": checks}, indent=2
        )
    )
    failed = [k for k, v in checks.items() if v is False]
    if failed:
        print(f"[E84] FAILED SELF-CHECKS: {failed}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
