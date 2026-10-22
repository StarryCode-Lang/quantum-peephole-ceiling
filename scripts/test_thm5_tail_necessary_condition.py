"""Empirical admissibility test for the Candidate Theorem 5 tail bound.

Background
----------
``docs/theory/formal_results.md`` states, for X = |A_adj(C)| (the number of
listing-adjacent inverse gate pairs),

    P[X >= E[X] + t]  <=  exp(-t^2 / (2 N)),        N = n(d-1)

and records the proof as **incomplete** because the generator's per-layer
two-qubit matchings couple the endpoint choices, so the product-space
bounded-differences assumption does not hold.

What this script does
---------------------
A sub-Gaussian tail with variance proxy ``N`` forces ``Var(X) <= 2 N``
(integration by parts: E[(X-EX)^2] = 2 * integral t P[X >= EX + t] dt
<= 2 * integral t exp(-t^2/(2N)) dt = 2N).  This script therefore tests the
*necessary condition* ``Var(X) <= 2N`` directly on the frozen E30 ensemble
(13,500 trials, 27 cells), and additionally fits the implied exponent scale
``N_eff = t^2 / (2 ln(1/P_emp(t)))`` from the empirical upper tail.

Outcomes:
  * ``Var(X) <= 2N`` for every cell  -> the stated exponent is not excluded;
    Thm 5 remains open but admissible.
  * ``Var(X) >  2N`` for some cell   -> the stated bound is *false* for the
    E30 generator at that cell, independently of the missing proof.

Inputs are read-only.  Output goes to a dated directory outside data/.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E30 = ROOT / "data/v10/e30/e30_thm1a_wcl_results.csv"
DEFAULT_OUT = ROOT / "docs/review/science_boost/2026-10-17_thm5_tail_test"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out_root = args.output_root
    out_root.mkdir(parents=True, exist_ok=True)

    cells: dict[tuple[int, int, float], list[int]] = defaultdict(list)
    with E30.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (int(row["n_qubits"]), int(row["depth"]), float(row["rho"]))
            cells[key].append(int(row["a_adj_raw"]))

    rows: list[dict] = []
    for (n, depth, rho), values in sorted(cells.items()):
        trials = len(values)
        mean = statistics.fmean(values)
        var = statistics.variance(values) if trials > 1 else 0.0
        N = n * (depth - 1)
        # empirical upper tail, largest t with at least one exceedance
        ordered = sorted(values)
        tail: list[tuple[float, float]] = []
        for t in [x - mean for x in range(int(math.ceil(mean)), max(values) + 1)]:
            if t <= 0:
                continue
            exceed = sum(1 for v in values if v >= mean + t) / trials
            if exceed > 0:
                tail.append((t, exceed))
        n_eff = None
        if tail:
            t_max, p_max = tail[-1]
            n_eff = t_max ** 2 / (2 * math.log(1.0 / p_max)) if p_max < 1 else None
        rows.append({
            "n_qubits": n,
            "depth": depth,
            "rho": rho,
            "trials": trials,
            "mean_adj_raw": round(mean, 6),
            "variance_adj_raw": round(var, 6),
            "N_n_d_minus_1": N,
            "variance_over_N": round(var / N, 6) if N else "",
            "dispersion_index_variance_over_mean": round(var / mean, 6) if mean else "",
            "necessary_condition_2N_satisfied": bool(var <= 2 * N),
            "max_observed": max(values),
            "tail_points": len(tail),
            "N_eff_from_extreme_tail": None if n_eff is None else round(n_eff, 4),
            "N_eff_over_N": None if (n_eff is None or not N) else round(n_eff / N, 4),
        })

    csv_path = out_root / "thm5_tail_test.csv"
    with csv_path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    violations = [r for r in rows if not r["necessary_condition_2N_satisfied"]]
    ratios = [r["variance_over_N"] for r in rows]
    neff_ratios = [r["N_eff_over_N"] for r in rows if r["N_eff_over_N"] is not None]
    dispersion = [r["dispersion_index_variance_over_mean"] for r in rows]

    summary = {
        "as_of": datetime.now().astimezone().strftime("%Y-%m-%d"),
        "cell_count": len(rows),
        "total_trials": sum(r["trials"] for r in rows),
        "necessary_condition_violations": len(violations),
        "violating_cells": [
            {"n_qubits": r["n_qubits"], "depth": r["depth"], "rho": r["rho"],
             "variance_over_N": r["variance_over_N"]} for r in violations
        ],
        "variance_over_N_min": min(ratios),
        "variance_over_N_max": max(ratios),
        "variance_over_N_median": round(statistics.median(ratios), 6),
        "N_eff_over_N_min": min(neff_ratios) if neff_ratios else None,
        "N_eff_over_N_max": max(neff_ratios) if neff_ratios else None,
        "N_eff_over_N_median": round(statistics.median(neff_ratios), 4) if neff_ratios else None,
        "dispersion_index_min": min(dispersion),
        "dispersion_index_max": max(dispersion),
        "dispersion_index_median": round(statistics.median(dispersion), 6),
        "dispersion_index_interpretation": (
            "Variance/mean ratio of X per cell; a value near 1 is consistent with "
            "Poisson/Poisson-binomial counting behaviour, which would place the true "
            "concentration scale near E[X] rather than near N = n(d-1)."
        ),
        "verdict": (
            "THM5_EXPONENT_NOT_EXCLUDED" if not violations else "THM5_EXPONENT_FALSIFIED_ON_E30"
        ),
        "claim_boundary": (
            "This is a necessary-condition test of the stated exponent on one frozen ensemble. "
            "Satisfying it does not prove Thm 5; violating it would refute the stated bound for "
            "the E30 generator. Tail resolution is bounded by the 500 trials per cell."
        ),
        "input": {"path": E30.relative_to(ROOT).as_posix(), "sha256": sha256_file(E30)},
    }
    (out_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_root / "protocol.json").write_text(json.dumps({
        "protocol_id": "THM5_TAIL_NECESSARY_CONDITION_TEST_V1",
        "date": summary["as_of"],
        "statistic": "Var(X) <= 2N, N = n(d-1), X = a_adj_raw",
        "derivation": "E[(X-EX)^2] = 2*int t P[X>=EX+t] dt <= 2*int t exp(-t^2/(2N)) dt = 2N",
        "inputs_read_only": {"e30": summary["input"]},
        "frozen_paths_untouched": ["data/", "release/", "docs/manuscript/"],
        "output": {"csv": csv_path.relative_to(ROOT).as_posix()},
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
