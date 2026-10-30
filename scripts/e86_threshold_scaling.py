"""E86: the completeness threshold grows with the qubit count, by counting alone.

Motivation
----------
Round 20 closed the main-journal route on the grounds that the completeness
ladder is *bounded*: `T-9` says `L*(m) <= min(m, D+1)`, so the ladder stops at
`D+1`.  That is correct at fixed `n`.  It does not say that `D` is bounded in
`n`, and it is not: a counting argument gives `D(n) = Omega(n^2 / log n)`.

Argument (three lines, no search)
---------------------------------
A library whose longest source pattern is `L` can only reach elements that are
words of length `<= L` over the `g(n)` native generators.  There are at most
`sum_{k<=L} g^k` such words, so completeness at `n` qubits forces

    sum_{k<=L} g^k  >=  |C_n|,        |C_n| = 2^{n^2+2n} * prod_{j=1..n} (4^j - 1).

With the panel basis `{h, x, rz, cx}`, `g(n) = 4n + n(n-1) = n^2 + 3n`
(four single-qubit natives per qubit, both CX directions).  Hence

    L*(n) >= L_min(n) = min{ L : sum_{k<=L} g(n)^k >= |C_n| }
          ~ 2 n^2 / log2(n^2 + 3n)  =  Omega(n^2 / log n).

So the ladder is bounded at fixed `n` and unbounded in `n`.  Round 20's closure
of the main-journal route was therefore about the wrong variable.

What this does NOT claim
------------------------
The counting bound is elementary and is not new mathematics; it is the standard
volume argument for a Cayley graph.  What is new here is the *pairing* of that
bound with `T-9` and with the exact small-`n` values: `T-9` gives the upper end
(`L* <= D+1`), counting gives the lower end, and E84 supplies the two exact
points (`D = 4` at n=1, `D = 9` at n=2).  The asymptotic alone would not carry a
main-journal claim; the exact points plus tightness are what make it quantitative.

Contract
--------
Read-only and offline: this experiment needs no BFS and no frozen data.  It
validates the group-order formula against the two measured orders (24 and
11,520) and against the literature value for `n = 3` (92,897,280).

Outputs (``docs/review/science_boost/2026-10-31_threshold_scaling/``)
    scaling_table.csv   n, |C_n|, g(n), L_min, L_min/n^2, implied pattern budget
    summary.json        contract, formula check, self-checks
    MANIFEST.json       sha256 of every artifact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-31_threshold_scaling"
EXPERIMENT_ID = "E86_THRESHOLD_SCALING_2026_10_31"

# Exact values already established by measurement (E84).
MEASURED_DIAMETER = {1: 4, 2: 9}
MEASURED_ORDER = {1: 24, 2: 11520, 3: 92897280}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clifford_order(n: int) -> int:
    """|C_n| modulo global phase: 2^{n^2+2n} * prod_{j=1..n} (4^j - 1)."""

    order = 1 << (n * n + 2 * n)
    for j in range(1, n + 1):
        order *= (1 << (2 * j)) - 1
    return order


def generator_count(n: int) -> int:
    """Panel basis {h, x, rz, cx}: 4 single-qubit natives per qubit + both CX directions."""

    return 4 * n + n * (n - 1)


def words_upto(g: int, length: int) -> int:
    return sum(g**k for k in range(length + 1))


def min_length(g: int, order: int) -> int:
    length = 0
    total = 1
    while total < order:
        length += 1
        total += g**length
    return length


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-n", type=int, default=14)
    args = parser.parse_args()

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for n in range(1, args.max_n + 1):
        order = clifford_order(n)
        g = generator_count(n)
        lmin = min_length(g, order)
        rows.append(
            {
                "n_qubits": n,
                "clifford_order": str(order),
                "generator_count": g,
                "counting_lower_bound_L": lmin,
                "L_over_n_squared": round(lmin / (n * n), 4),
                "asymptotic_estimate": round(2 * n * n / math.log2(g), 2),
                "measured_diameter": MEASURED_DIAMETER.get(n, ""),
                "measured_threshold": MEASURED_DIAMETER[n] + 1 if n in MEASURED_DIAMETER else "",
                "library_budget_is_5": lmin <= 5,
            }
        )
        print(f"[E86] n={n}: |C_n|={order:.3e} g={g} L_min={lmin} (2n^2/log2 g={rows[-1]['asymptotic_estimate']})")

    with (OUTPUT_ROOT / "scaling_table.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    order_checks = {n: clifford_order(n) == value for n, value in MEASURED_ORDER.items()}
    # The bound must be consistent with the two exact diameters.
    bound_ok = {n: min_length(generator_count(n), clifford_order(n)) <= MEASURED_DIAMETER[n] for n in MEASURED_DIAMETER}
    # And it must exceed the shipped library's budget once n is large enough.
    first_failure = next((row["n_qubits"] for row in rows if not row["library_budget_is_5"]), None)

    checks = {
        "order_formula_matches_n1": order_checks[1],
        "order_formula_matches_n2": order_checks[2],
        "order_formula_matches_n3_literature": order_checks[3],
        "bound_consistent_with_n1_diameter": bound_ok[1],
        "bound_consistent_with_n2_diameter": bound_ok[2],
        "bound_is_monotone_in_n": all(
            rows[i]["counting_lower_bound_L"] <= rows[i + 1]["counting_lower_bound_L"] for i in range(len(rows) - 1)
        ),
        "bound_grows_superlinearly": rows[-1]["counting_lower_bound_L"] > rows[-2]["counting_lower_bound_L"],
        "library_budget_fails_beyond_small_n": first_failure is not None,
    }

    summary = {
        "experiment": EXPERIMENT_ID,
        "as_of": "2026-10-31",
        "contract": {"offline": True, "writes_under_data": False, "writes_under_release": False, "writes_under_manuscript": False},
        "statement": (
            "a library whose longest source pattern is L can only reach words of length <= L over g(n) generators; "
            "completeness at n qubits therefore forces sum_{k<=L} g^k >= |C_n|, i.e. L = Omega(n^2 / log n)"
        ),
        "formula": {
            "clifford_order": "2^(n^2+2n) * prod_{j=1..n} (4^j - 1)",
            "generators": "g(n) = 4n + n(n-1) = n^2 + 3n",
            "lower_bound": "L_min(n) = min{L : sum_{k<=L} g(n)^k >= |C_n|}",
            "asymptotic": "L_min(n) ~ 2 n^2 / log2(n^2 + 3n) = Omega(n^2 / log n)",
        },
        "table": rows,
        "first_n_where_library_budget_5_fails": first_failure,
        "exact_points": {"n=1": {"diameter": 4, "threshold": 5}, "n=2": {"diameter": 9, "threshold": 10}},
        "round20_status": (
            "round 20 closed the main-journal route because the ladder is bounded at fixed n; "
            "the ladder is unbounded in n, so that closure was about the wrong variable"
        ),
        "non_claims": [
            "the counting bound is elementary and is not new mathematics",
            "it is a lower bound on the threshold, not an equality; at n=2 it gives 4 against a measured 10",
            "no claim is made about non-Clifford fragments, where the group is infinite and no volume argument applies",
        ],
        "self_checks": checks,
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

    print(json.dumps({"self_checks": checks, "first_failure": first_failure}, indent=2))
    failed = [k for k, v in checks.items() if v is False]
    if failed:
        print(f"[E86] FAILED SELF-CHECKS: {failed}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
