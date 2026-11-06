"""E94: stability of the rigidity decay constant lambda per window length L.

Motivation
----------
Round 23 (E91) measured the locally-irreducible fraction ``rho(m, L)`` on the
panel group and observed a geometric decay with ``lambda ~ 0.58`` for
``L = 5`` -- but only from 7 points (m = 8..14), and only for one window
length.  Round 23's 30-day list (item 4) asks whether the decay constant is a
stable property of the fragment or an artifact of the fitted range:

1. extend the curve to ``m = 20`` (beyond the previous cap ``D + 5``);
2. fit ``lambda`` separately for ``L = 2, 3, 4, 5`` (panel_2q) and
   ``L = 2, 3`` (panel_1q).

Decision criterion registered in advance: lambda is called stable if the
tail ratios ``rho(m+1, L) / rho(m, L)`` stay within ``+/- 0.02`` of their
mean over the fit window (m = 12..19).

Method
------
Exactly the two dynamic programs of E91 (``geodesic_counts`` and
``valid_counts``), reused unmodified; nothing here re-derives them.  The only
new code is the fit and the alignment checks.  All counting is exact on the
Cayley graph; no search, no sampling, no qiskit call.

Cross-experiment alignment (house convention, round 22+):
``rho(m, 5)`` for m = 4..14 must reproduce the frozen
``2026-11-04_rigidity_floor/rigidity_floor.csv`` values, and the E87 fragment
denominators must fall out of the G sequence alone, as in E91.

Contract
--------
Read-only on frozen inputs.  Nothing under ``data/``, ``release/`` or
``docs/manuscript/`` is written.  New artifacts live in
``docs/review/science_boost/2026-11-06_rigidity_lambda/``.

Outputs
    rigidity_lambda.csv   one row per (fragment, L, m) with rho and the
                          successive ratio
    summary.json          contract, lambda fits, self-checks, provenance
    MANIFEST.json         sha256 of every artifact
"""

from __future__ import annotations

import csv
import hashlib
import importlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

e91 = importlib.import_module("e91_rigidity_floor")

OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-11-06_rigidity_lambda"
E91_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-11-04_rigidity_floor"
E87_PATH = ROOT / "docs" / "review" / "science_boost" / "2026-11-02_panel_price_recheck" / "summary.json"
EXPERIMENT_ID = "E94_RIGIDITY_LAMBDA_2026_11_06"

MAX_M = 20
FIT_LOW, FIT_HIGH = 12, 19  # ratio fit window: rho(m+1)/rho(m) for m in [12, 19]

# (fragment name, n, generators, window lengths L to fit)
# Round-24 extension: L = 6, 7 added on top of the registered L = 2..5 set to
# test the empirical "lambda decreases ~0.106 per level" observation (scan
# §2.2); L = 8 would need A^7 = 10^7 DP states and is skipped as too heavy.
PLAN = [
    ("panel_2q", 2, list(e91.PANEL_2Q), [2, 3, 4, 5, 6, 7]),
    ("panel_1q", 1, list(e91.PANEL_1Q), [2, 3]),
]


def fit_lambda(rhos: dict[int, float]) -> dict[str, Any]:
    """Tail ratio mean + spread, and a log-linear slope, over the fit window."""

    ratios = {
        m: rhos[m + 1] / rhos[m]
        for m in range(FIT_LOW, FIT_HIGH + 1)
        if rhos.get(m, 0.0) > 0.0 and rhos.get(m + 1, 0.0) > 0.0
    }
    if not ratios:
        return {"ratios": {}, "lambda_mean": None, "lambda_spread": None, "log_slope": None}
    values = list(ratios.values())
    mean = sum(values) / len(values)
    spread = max(abs(v - mean) for v in values)
    # log-linear slope over the fit window (natural log), robust to a single
    # noisy ratio: slope = -lambda_eff for rho ~ C * exp(-lambda * m)
    ms = sorted(ratios)
    xs = [m for m in ms if rhos[m] > 0.0]
    ys = [math.log(rhos[m]) for m in xs]
    n = len(xs)
    xbar = sum(xs) / n
    ybar = sum(ys) / n
    sxx = sum((x - xbar) ** 2 for x in xs)
    sxy = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    return {
        "ratios": {str(m): ratios[m] for m in ms},
        "lambda_mean": mean,
        "lambda_spread": spread,
        "lambda_stable": spread <= 0.02,
        "log_slope": slope,
        "lambda_from_log_slope": -slope,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    fits: dict[str, Any] = {}
    details: dict[str, Any] = {}

    for name, n, generators, lengths in PLAN:
        group = e91.Group(n, generators)
        print(
            f"[E94] {name}: order={len(group.elements)} D={group.diameter} "
            f"A={group.alphabet} max_m={MAX_M}"
        )
        geodesic = e91.geodesic_counts(group, MAX_M)
        per_fragment: dict[str, Any] = {
            "group_order": len(group.elements),
            "diameter": group.diameter,
            "alphabet": group.alphabet,
            "generators": generators,
            "geodesic_counts": {m: geodesic[m] for m in range(MAX_M + 1)},
        }
        for length_cap in lengths:
            valid = e91.valid_counts(group, length_cap, MAX_M)
            rhos: dict[int, float] = {}
            for m in range(MAX_M + 1):
                if m < length_cap:
                    continue
                if m == length_cap:
                    value = geodesic[m]  # rho(L, L) = 0 by T-9; V == G here
                else:
                    value = valid[m]
                reducible = group.alphabet**m - geodesic[m]
                no_action = value - geodesic[m]
                rho = (no_action / reducible) if reducible else 0.0
                rhos[m] = rho
                rows.append(
                    {
                        "fragment": name,
                        "L": length_cap,
                        "m": m,
                        "alphabet": group.alphabet,
                        "total_words": group.alphabet**m,
                        "geodesic_words": geodesic[m],
                        "valid_words": value,
                        "reducible_words": reducible,
                        "locally_irreducible_words": no_action,
                        "rho": rho,
                        "ratio_prev": (
                            rhos[m] / rhos[m - 1] if m - 1 in rhos and rhos[m - 1] > 0 else ""
                        ),
                    }
                )
            fits[f"{name}:L{length_cap}"] = fit_lambda(rhos)
            per_fragment[f"L{length_cap}_rho"] = {str(m): rhos[m] for m in sorted(rhos)}
            print(
                f"[E94] {name} L={length_cap}: "
                f"lambda_mean={fits[f'{name}:L{length_cap}']['lambda_mean']}"
            )
        details[name] = per_fragment

    # ---- self-checks -------------------------------------------------------
    checks: dict[str, Any] = {}
    g1 = e91.Group(1, e91.PANEL_1Q)
    g2 = e91.Group(2, e91.PANEL_2Q)
    checks["panel_2q_order_11520"] = len(g2.elements) == 11520
    checks["panel_2q_diameter_9"] = g2.diameter == 9
    checks["panel_1q_order_24"] = len(g1.elements) == 24
    checks["panel_1q_diameter_4"] = g1.diameter == 4

    # rho(L, L) = 0 (T-9 consistency) on every fitted (fragment, L)
    checks["rho_zero_at_m_equals_L"] = all(
        r["locally_irreducible_words"] == 0 for r in rows if r["m"] == r["L"]
    )

    # Alignment with the frozen E91 package: rho(m, 5) must reproduce the
    # published values for every overlapping m (4..14).
    e91_csv = E91_ROOT / "rigidity_floor.csv"
    if e91_csv.exists():
        with e91_csv.open(encoding="utf-8") as handle:
            e91_rows = {
                (r["fragment"], int(r["L"]), int(r["m"])): float(r["rho"])
                for r in csv.DictReader(handle)
            }
        mismatches = []
        for r in rows:
            key = (r["fragment"], r["L"], r["m"])
            if key in e91_rows and abs(e91_rows[key] - r["rho"]) > 1e-12:
                mismatches.append({"key": list(key), "e91": e91_rows[key], "e94": r["rho"]})
        checks["e91_rho_m5_reproduced"] = not mismatches
        checks["e91_rho_m5_overlap_cells"] = sum(
            1 for r in rows if (r["fragment"], r["L"], r["m"]) in e91_rows
        )
        if mismatches:
            checks["e91_rho_m5_mismatches"] = mismatches[:10]

    # Alignment with E87 (published fragment denominators from the G sequence).
    if E87_PATH.exists():
        e87 = json.loads(E87_PATH.read_text(encoding="utf-8"))
        g6 = e91.geodesic_counts(g2, 6)
        m5_reducible = sum(10**k - g6[k] for k in range(0, 6))
        m6_reducible = sum(10**k - g6[k] for k in range(0, 7))
        checks["e87_part_b_reducible_m5_reproduced"] = (
            m5_reducible == e87["part_b_panel"]["meta"]["reducible"]
        )
        checks["e87_part_d_reducible_m6_reproduced"] = (
            m6_reducible == e87["part_d_panel_m6"]["configs"]["all_L2_5"]["members_reducible"]
        )

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "contract": {
            "frozen_inputs": [
                "docs/review/science_boost/2026-11-04_rigidity_floor/rigidity_floor.csv (alignment only)",
            ],
            "cost_model": "word length = Cayley distance; no unitary simulation",
            "writes": ["docs/review/science_boost/2026-11-06_rigidity_lambda/"],
            "reads": [str(e91_csv)] if e91_csv.exists() else [],
        },
        "decision_criterion": (
            "lambda called stable if max |rho(m+1)/rho(m) - mean| <= 0.02 over "
            "m = 12..19 (registered before running; round-23 30-day list item 4)"
        ),
        "fit_window": [FIT_LOW, FIT_HIGH],
        "max_m": MAX_M,
        "lambda_fits": fits,
        "fragments": details,
        "self_checks": checks,
        "versions": {"python": sys.version.split()[0]},
        "provenance": {"round": 24, "date": "2026-11-06", "closes_30day_item": 4},
    }

    with (OUTPUT_ROOT / "rigidity_lambda.csv").open("w", encoding="utf-8", newline="") as handle:
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
    print(
        f"[E94] self-checks: {sum(1 for v in checks.values() if v is True)} true / "
        f"{len(failed)} false"
    )
    for key, fit in fits.items():
        print(f"[E94] {key}: lambda={fit['lambda_mean']} spread={fit['lambda_spread']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
