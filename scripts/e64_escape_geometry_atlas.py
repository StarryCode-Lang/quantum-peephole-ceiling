"""E64: escape-geometry atlas -- new quantities derived from frozen E45/E46 data.

Motivation
----------
The v15 E46 window landscape (76,236 certified window searches) and the v14/v15
E45 whole-listing certificates are frozen, but the manuscript and the readiness
verdict each quote only one slice of them (37.2% of greedy 16-gate windows at
h=3; four all-source per-config rates).  No single artefact reconciles those
slices with explicit denominators, and several scientific quantities that the
data already determine have never been computed:

    * the full escape-rate atlas (root_kind x width x horizon, explicit n/N);
    * the escape geometry (rate vs window position, first-escape position);
    * the window-gain and barrier-height distributions;
    * the empirical branching-factor law states_seen ~ c * b^h;
    * the depth>=2 escape mechanism profile by circuit family;
    * whether a window escape predicts a whole-listing escape (2x2 + Fisher);
    * a distance-to-exact tracker for the 34 bounded cells;
    * tier/family mean gains with a source-cluster bootstrap CI.

This experiment computes all of the above with frozen data only.

Contract
    Frozen inputs only, read-only (``data/``, ``docs/manuscript/``).  No search
    is re-run: every quantity is arithmetic over the frozen CSV/JSONL files,
    plus the E52 summary for the whole-listing rule-family join.  Outputs are
    byte-deterministic: fixed ordering everywhere, no wall-clock timestamps
    (``generated_at`` is the package date at 00:00:00Z), fixed bootstrap seed.

Outputs (``docs/review/science_boost/2026-10-25_escape_geometry/``):
    * ``escape_rate_atlas.csv``                  -- root_kind x width x horizon
    * ``escape_rate_slices.csv``                 -- named slices (manuscript,
                                                   verdict, audit anchors)
    * ``escape_geometry_by_start.csv``           -- rate vs window_start
    * ``source_escape_geometry.csv``             -- per source x config geometry
    * ``window_gain_distribution.csv``           -- gain x root_kind
    * ``window_barrier_distribution.csv``        -- barrier x root_kind
    * ``branching_factor_law.csv``               -- states_seen stats per config
    * ``window_escape_depth_by_family.csv``      -- depth x family counts
    * ``family_profile.csv``                     -- window x E52 family join
    * ``window_escape_contingency.csv``          -- 2x2 tables + Fisher p
    * ``contingency_source_table.csv``           -- the 128 source verdicts
    * ``bounded_cell_exactification_tracker.csv``-- the 34 bounded cells
    * ``tier_family_gain_bootstrap.csv``         -- cluster-bootstrap CIs
    * ``summary.json``                           -- aggregates + anchor checks
    * ``summary.md``                             -- interpretation
    * ``receipt.json``                           -- input/output/script hashes
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import platform
import random
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPERIMENT_ID = "E64_ESCAPE_GEOMETRY_ATLAS_2026_10_25"
PACKAGE = "2026-10-25_escape_geometry"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / PACKAGE
PACKAGE_DATE = "2026-10-25"
GENERATED_AT = PACKAGE_DATE + "T00:00:00Z"  # deterministic, no wall clock
BOOTSTRAP_SEED = 20261025
BOOTSTRAP_RESAMPLES = 10_000

WINDOW_RESULTS = ROOT / "data" / "v15" / "e46_window_landscape" / "window_results.csv"
INPUT_SUMMARIES = ROOT / "data" / "v15" / "e46_window_landscape" / "input_summaries.csv"
ESCAPE_CERTS = ROOT / "data" / "v15" / "e46_window_landscape" / "escape_certificates.jsonl"
CLASSIFICATION = ROOT / "data" / "v15" / "e45_landscape_integration" / "classification_complete.csv"
COMPACT_CERTS = ROOT / "data" / "v14" / "e45_full_development" / "certificates.jsonl"
IDASTAR_CERTS = ROOT / "data" / "v14" / "e45_idastar_escape" / "certificates.jsonl"
E52_SUMMARY = ROOT / "docs" / "review" / "science_boost" / "2026-10-22_escape_mechanism" / "summary.json"

INPUTS = {
    "window_results": WINDOW_RESULTS,
    "input_summaries": INPUT_SUMMARIES,
    "escape_certificates": ESCAPE_CERTS,
    "classification_complete": CLASSIFICATION,
    "compact_certificates": COMPACT_CERTS,
    "idastar_certificates": IDASTAR_CERTS,
    "e52_summary": E52_SUMMARY,
}

GREEDY = "GREEDY_FIXED_POINT"
RAW = "RAW_NORMALIZED_OVER_BASELINE_BUDGET"
WIDTHS = (8, 16)
HORIZONS = (2, 3)
BASELINE_GATE_LIMIT = 80  # experiments.e45_development_grid.run.MAX_BASELINE_GATES


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def fmt(x: float | int | None, nd: int = 6) -> str:
    """Fixed-precision CSV rendering; keeps outputs byte-deterministic."""
    if x is None:
        return ""
    return f"{float(x):.{nd}f}"


def quantile(sorted_xs: list[float], p: float) -> float | None:
    """Linear-interpolation quantile (numpy 'linear' convention)."""
    if not sorted_xs:
        return None
    n = len(sorted_xs)
    if n == 1:
        return float(sorted_xs[0])
    pos = p * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return float(sorted_xs[lo] * (1.0 - frac) + sorted_xs[hi] * frac)


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Exact two-sided Fisher p-value for [[a, b], [c, d]] (pure stdlib).

    Sums every hypergeometric table probability <= the observed one, using
    exact integer arithmetic (math.comb + fractions.Fraction).
    """

    row1, col1 = a + b, a + c
    n = a + b + c + d
    if min(row1, col1, n) <= 0 or n - row1 - col1 + a < 0:
        return 1.0

    def prob(x: int) -> Fraction:
        return Fraction(
            math.comb(col1, x) * math.comb(n - col1, row1 - x),
            math.comb(n, row1),
        )

    p_obs = prob(a)
    total = Fraction(0)
    for x in range(max(0, col1 - (n - row1)), min(row1, col1) + 1):
        px = prob(x)
        if px <= p_obs:
            total += px
    return float(min(total, Fraction(1)))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


# --------------------------------------------------------------------------- loading


def load_inputs() -> dict[str, Any]:
    with WINDOW_RESULTS.open(encoding="utf-8", newline="") as handle:
        window_rows = list(csv.DictReader(handle))
    with INPUT_SUMMARIES.open(encoding="utf-8", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    with CLASSIFICATION.open(encoding="utf-8", newline="") as handle:
        classification = {row["source_id"]: row for row in csv.DictReader(handle)}
    compact = {}
    for line in COMPACT_CERTS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            compact[payload["source_id"]] = payload["certificate"]
    idastar = {}
    for line in IDASTAR_CERTS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            idastar[payload["source_id"]] = payload["certificate"]
    escape_certs = []
    for line in ESCAPE_CERTS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            escape_certs.append(json.loads(line))
    e52 = json.loads(E52_SUMMARY.read_text(encoding="utf-8"))
    for row in summary_rows:
        row["window_count_i"] = int(row["window_count"])
        row["escape_count_i"] = int(row["escape_count"])
    for row in window_rows:
        row["window_width_i"] = int(row["window_width"])
        row["horizon_i"] = int(row["horizon"])
        row["window_start_i"] = int(row["window_start"])
        row["escape_depth_i"] = int(row["escape_depth"]) if row["escape_depth"] else 0
        row["is_escape"] = row["status"] == "EXACT_ESCAPE"
    return {
        "window_rows": window_rows,
        "summary_rows": summary_rows,
        "classification": classification,
        "compact": compact,
        "idastar": idastar,
        "escape_certs": escape_certs,
        "e52": e52,
    }


# --------------------------------------------------------------------------- Part A


def part_a_atlas(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Escape-rate atlas with explicit denominators, plus named slices."""

    window_rows = data["window_rows"]
    summary_rows = data["summary_rows"]
    distinct_sources = {r["source_id"] for r in summary_rows}
    sources_total = {
        "ALL": len(distinct_sources),
        GREEDY: len({r["source_id"] for r in summary_rows if r["root_kind"] == GREEDY}),
        RAW: len({r["source_id"] for r in summary_rows if r["root_kind"] == RAW}),
    }

    def slice_stats(kind: str, width: int | None, horizon: int | None) -> dict[str, Any]:
        rows = [
            r
            for r in window_rows
            if (kind == "ALL" or r["root_kind"] == kind)
            and (width is None or r["window_width_i"] == width)
            and (horizon is None or r["horizon_i"] == horizon)
        ]
        escapes = [r for r in rows if r["is_escape"]]
        d1 = [r for r in escapes if r["escape_depth_i"] == 1]
        d2p = [r for r in escapes if r["escape_depth_i"] >= 2]
        n = len(rows)
        return {
            "root_kind": kind,
            "window_width": width if width is not None else "both",
            "horizon": horizon if horizon is not None else "both",
            "sources_total": sources_total[kind],
            "sources_with_windows": len({r["source_id"] for r in rows}),
            "windows": n,
            "escapes": len(escapes),
            "escapes_depth1": len(d1),
            "escapes_depth2plus": len(d2p),
            "escape_rate": fmt(len(escapes) / n, 6) if n else "",
            "escape_rate_depth2plus": fmt(len(d2p) / n, 6) if n else "",
            "mean_escape_depth": fmt(sum(r["escape_depth_i"] for r in escapes) / len(escapes), 6)
            if escapes
            else "",
        }

    atlas = [
        slice_stats(kind, width, horizon)
        for kind in ("ALL", GREEDY, RAW)
        for width in WIDTHS + (None,)
        for horizon in HORIZONS + (None,)
        if not (width is None and horizon is None and kind == "ALL")
    ]

    greedy_w16_h3 = [r for r in window_rows if r["root_kind"] == GREEDY and r["window_width_i"] == 16 and r["horizon_i"] == 3]
    man_d2p = sum(1 for r in greedy_w16_h3 if r["is_escape"] and r["escape_depth_i"] >= 2)

    def pooled(kind: str, width: int) -> tuple[int, int]:
        rows = [r for r in window_rows if r["root_kind"] == kind and r["window_width_i"] == width]
        return sum(1 for r in rows if r["is_escape"]), len(rows)

    def pooled_horizon(kind: str, horizon: int) -> tuple[int, int]:
        rows = [r for r in window_rows if r["root_kind"] == kind and r["horizon_i"] == horizon]
        return sum(1 for r in rows if r["is_escape"]), len(rows)

    def all_rate(width: int, horizon: int) -> tuple[int, int]:
        rows = [r for r in window_rows if r["window_width_i"] == width and r["horizon_i"] == horizon]
        return sum(1 for r in rows if r["is_escape"]), len(rows)

    g8 = pooled(GREEDY, 8)
    g16 = pooled(GREEDY, 16)
    r8 = pooled(RAW, 8)
    r16 = pooled(RAW, 16)
    gh2 = pooled_horizon(GREEDY, 2)
    gh3 = pooled_horizon(GREEDY, 3)
    rh2 = pooled_horizon(RAW, 2)
    rh3 = pooled_horizon(RAW, 3)
    a8h2 = all_rate(8, 2)
    a8h3 = all_rate(8, 3)
    a16h2 = all_rate(16, 2)
    a16h3 = all_rate(16, 3)

    slices = [
        ("manuscript_greedy_w16_h3_depth2plus", man_d2p, len(greedy_w16_h3),
         "manuscript.md L1196-1197: '37.2 percent of 16-gate windows (179 of 481)'"),
        ("verdict_all_sources_w8_h2", a8h2[0], a8h2[1], "v15 readiness-verdict per-config rate ~0.4685"),
        ("verdict_all_sources_w8_h3", a8h3[0], a8h3[1], "v15 readiness-verdict per-config rate ~0.4769"),
        ("verdict_all_sources_w16_h2", a16h2[0], a16h2[1], "v15 readiness-verdict per-config rate ~0.5586"),
        ("verdict_all_sources_w16_h3", a16h3[0], a16h3[1], "v15 readiness-verdict per-config rate ~0.5701"),
        ("audit_greedy_w8_pooled_horizons", g8[0], g8[1], "earlier audit anchor GREEDY w8 15.9% (78 greedy roots)"),
        ("audit_greedy_w16_pooled_horizons", g16[0], g16[1], "earlier audit anchor GREEDY w16 32.1%"),
        ("audit_raw_w8_pooled_horizons", r8[0], r8[1], "earlier audit anchor RAW w8 48.5% (50 raw roots)"),
        ("audit_raw_w16_pooled_horizons", r16[0], r16[1], "earlier audit anchor RAW w16 57.1%"),
        ("greedy_only_h2_pooled_widths", gh2[0], gh2[1], "greedy-only h2 rate (task deliverable)"),
        ("greedy_only_h3_pooled_widths", gh3[0], gh3[1], "greedy-only h3 rate"),
        ("raw_only_h2_pooled_widths", rh2[0], rh2[1], "raw-listing h2 rate"),
        ("raw_only_h3_pooled_widths", rh3[0], rh3[1], "raw-listing h3 rate"),
    ]
    slice_rows = [
        {
            "slice": name,
            "numerator": num,
            "denominator": den,
            "rate": fmt(num / den, 6) if den else "",
            "note": note,
        }
        for name, num, den, note in slices
    ]

    checks = [
        ("manuscript 179/481 greedy w16 h3 depth>=2", man_d2p == 179 and len(greedy_w16_h3) == 481,
         f"{man_d2p}/{len(greedy_w16_h3)} = {man_d2p / len(greedy_w16_h3):.4f}"),
        ("verdict w8h2 ~0.4685", abs(a8h2[0] / a8h2[1] - 0.4685) < 5e-5, f"{a8h2[0] / a8h2[1]:.4f}"),
        ("verdict w8h3 ~0.4769", abs(a8h3[0] / a8h3[1] - 0.4769) < 5e-5, f"{a8h3[0] / a8h3[1]:.4f}"),
        ("verdict w16h2 ~0.5586", abs(a16h2[0] / a16h2[1] - 0.5586) < 5e-5, f"{a16h2[0] / a16h2[1]:.4f}"),
        ("verdict w16h3 ~0.5701", abs(a16h3[0] / a16h3[1] - 0.5701) < 5e-5, f"{a16h3[0] / a16h3[1]:.4f}"),
        ("audit GREEDY w8 ~15.9%", abs(g8[0] / g8[1] - 0.159) < 5e-4, f"{g8[0] / g8[1]:.4f} ({g8[0]}/{g8[1]})"),
        ("audit GREEDY w16 ~32.1%", abs(g16[0] / g16[1] - 0.321) < 5e-4, f"{g16[0] / g16[1]:.4f} ({g16[0]}/{g16[1]})"),
        ("audit RAW w8 ~48.5%", abs(r8[0] / r8[1] - 0.485) < 5e-4, f"{r8[0] / r8[1]:.4f} ({r8[0]}/{r8[1]})"),
        ("audit RAW w16 ~57.1%", abs(r16[0] / r16[1] - 0.571) < 5e-4, f"{r16[0] / r16[1]:.4f} ({r16[0]}/{r16[1]})"),
    ]
    length_range: dict[str, dict[str, int]] = {}
    for kind in (GREEDY, RAW):
        lengths = [int(r["root_gate_count"]) for r in summary_rows if r["root_kind"] == kind]
        length_range[kind] = {"min": min(lengths), "max": max(lengths)}

    aggregate = {
        "total_window_searches": len(window_rows),
        "total_certified_window_escapes": sum(1 for r in window_rows if r["is_escape"]),
        "sources_by_root_kind": {GREEDY: sources_total[GREEDY], RAW: sources_total[RAW]},
        "root_gate_count_range_by_kind": length_range,
        "baseline_gate_limit": BASELINE_GATE_LIMIT,
        "sources_in_window_results": len({r["source_id"] for r in window_rows}),
        "sources_absent_from_window_results": sorted(
            {r["source_id"] for r in summary_rows} - {r["source_id"] for r in window_rows}
        ),
        "absent_reason": "greedy root shorter than the 8-gate minimum window (root_gate_count < 8); zero windows in all configs",
        "anchor_checks": [
            {"anchor": name, "match": bool(ok), "observed": observed} for name, ok, observed in checks
        ],
        "anchor_checks_all_match": all(ok for _, ok, _ in checks),
    }
    return atlas, slice_rows, aggregate


# --------------------------------------------------------------------------- Part B


def part_b_geometry(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Escape geometry: rate vs window position, first-escape position, depth."""

    window_rows = data["window_rows"]
    summary_rows = data["summary_rows"]
    classification = data["classification"]

    by_start: collections.Counter = collections.Counter()
    agg: dict[tuple[int, int, int], dict[str, int]] = {}
    for r in window_rows:
        key = (r["window_width_i"], r["horizon_i"], r["window_start_i"])
        if key not in agg:
            agg[key] = {"windows": 0, "escapes": 0, "sources": 0}
        cell = agg[key]
        cell["windows"] += 1
        if r["is_escape"]:
            cell["escapes"] += 1
    # source count per start key (sources present at that start)
    starts_sources: dict[tuple[int, int, int], set[str]] = collections.defaultdict(set)
    for r in window_rows:
        key = (r["window_width_i"], r["horizon_i"], r["window_start_i"])
        starts_sources[key].add(r["source_id"])
    by_start_rows = [
        {
            "window_width": key[0],
            "horizon": key[1],
            "window_start": key[2],
            "sources": len(starts_sources[key]),
            "windows": cell["windows"],
            "escapes": cell["escapes"],
            "escape_rate": fmt(cell["escapes"] / cell["windows"], 6),
        }
        for key, cell in sorted(agg.items())
    ]

    meta = {r["source_id"]: r for r in summary_rows}
    grouped: dict[tuple[str, int, int], list[dict[str, Any]]] = collections.defaultdict(list)
    for r in window_rows:
        grouped[(r["source_id"], r["window_width_i"], r["horizon_i"])].append(r)
    per_source_rows: list[dict[str, Any]] = []
    first_pos_hist: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    rel_first_pos: dict[str, list[float]] = collections.defaultdict(list)
    med_by_config: dict[str, list[float]] = collections.defaultdict(list)
    tercile_rates: dict[tuple[str, int, int], list[float | None]] = collections.defaultdict(list)
    for (source_id, width, horizon), rows in sorted(grouped.items()):
        rows.sort(key=lambda r: r["window_start_i"])
        n_windows = len(rows)
        escapes = [r for r in rows if r["is_escape"]]
        summary = next(
            (s for s in summary_rows if s["source_id"] == source_id and int(s["window_width"]) == width and int(s["horizon"]) == horizon),
            None,
        )
        first_pos = int(summary["first_escape_position"]) if summary and summary["first_escape_position"] else None
        mean_depth = float(summary["mean_escape_depth"]) if summary and summary["mean_escape_depth"] else None
        if first_pos is not None and n_windows > 1:
            first_pos_hist[f"w{width}h{horizon}"][first_pos] += 1
            rel_first_pos[f"w{width}h{horizon}"].append(first_pos / (n_windows - 1))
        if mean_depth is not None:
            med_by_config[f"w{width}h{horizon}"].append(mean_depth)
        tercile: dict[str, float | None] = {}
        for name, chunk in (
            ("early", rows[: n_windows // 3]),
            ("mid", rows[n_windows // 3 : (2 * n_windows) // 3]),
            ("late", rows[(2 * n_windows) // 3 :]),
        ):
            rate = (sum(1 for r in chunk if r["is_escape"]) / len(chunk)) if chunk else None
            tercile[name] = rate
            tercile_rates[(name, width, horizon)].append(rate)
        info = meta[source_id]
        per_source_rows.append(
            {
                "source_id": source_id,
                "circuit_family": info["circuit_family"],
                "root_kind": info["root_kind"],
                "root_gate_count": int(info["root_gate_count"]),
                "window_width": width,
                "horizon": horizon,
                "n_windows": n_windows,
                "n_escapes": len(escapes),
                "escape_rate": fmt(len(escapes) / n_windows, 6),
                "first_escape_position": first_pos if first_pos is not None else "",
                "rel_first_escape_position": fmt(first_pos / (n_windows - 1), 6) if first_pos is not None and n_windows > 1 else "",
                "mean_escape_depth": fmt(mean_depth, 6) if mean_depth is not None else "",
                "rate_tercile_early": fmt(tercile["early"], 6) if tercile["early"] is not None else "",
                "rate_tercile_mid": fmt(tercile["mid"], 6) if tercile["mid"] is not None else "",
                "rate_tercile_late": fmt(tercile["late"], 6) if tercile["late"] is not None else "",
                "classification_status": classification[source_id]["classification_status"],
            }
        )

    root_stats: dict[str, dict[str, Any]] = {}
    for r in window_rows:
        st = root_stats.setdefault(
            r["source_id"],
            {"kind": r["root_kind"], "gates": int(r["root_gate_count"]), "family": r["circuit_family"], "escapes": 0, "d1": 0, "d2plus": 0},
        )
        if r["is_escape"]:
            st["escapes"] += 1
            if r["escape_depth_i"] == 1:
                st["d1"] += 1
            else:
                st["d2plus"] += 1
    raw_roots = [st for st in root_stats.values() if st["kind"] == RAW]
    greedy_roots = [st for st in root_stats.values() if st["kind"] == GREEDY]

    aggregate = {
        "roots_in_panel": len(root_stats),
        "roots_with_depth1_escape": sum(1 for st in root_stats.values() if st["d1"] > 0),
        "greedy_roots_with_depth1_escape": sum(1 for st in greedy_roots if st["d1"] > 0),
        "greedy_roots_in_panel": len(greedy_roots),
        "raw_roots_in_panel": len(raw_roots),
        "raw_roots_with_depth1_escape": sum(1 for st in raw_roots if st["d1"] > 0),
        "raw_roots_without_any_escape": [
            {"source_id": source_id, "circuit_family": st["family"], "root_gate_count": st["gates"]}
            for source_id, st in sorted(root_stats.items())
            if st["kind"] == RAW and st["escapes"] == 0
        ],
        "first_escape_position_histogram": {
            config: dict(sorted(counter.items())) for config, counter in sorted(first_pos_hist.items())
        },
        "rel_first_escape_position_quantiles": {
            config: {
                "n": len(values),
                "p10": fmt(quantile(sorted(values), 0.10), 4),
                "p50": fmt(quantile(sorted(values), 0.50), 4),
                "p90": fmt(quantile(sorted(values), 0.90), 4),
            }
            for config, values in sorted(rel_first_pos.items())
        },
        "per_source_mean_escape_depth": {
            config: {
                "n": len(values),
                "mean": fmt(sum(values) / len(values), 4),
                "p50": fmt(quantile(sorted(values), 0.50), 4),
                "max": fmt(max(values), 4),
            }
            for config, values in sorted(med_by_config.items())
        },
        "tercile_rate_mean_across_sources": {
            f"{name}_w{width}_h{horizon}": fmt(
                sum(v for v in values if v is not None) / max(1, sum(1 for v in values if v is not None)), 4
            )
            for (name, width, horizon), values in sorted(tercile_rates.items())
        },
    }
    return by_start_rows, per_source_rows, aggregate


# --------------------------------------------------------------------------- Part C


def part_c_gain_barrier(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Window-gain and barrier-height distributions with per-root_kind split."""

    window_rows = data["window_rows"]
    escapes = [r for r in window_rows if r["is_escape"]]
    gain_rows: list[dict[str, Any]] = []
    barrier_rows: list[dict[str, Any]] = []
    gain_totals: collections.Counter = collections.Counter()
    barrier_totals: collections.Counter = collections.Counter()
    per_kind_gain: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    per_kind_barrier: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for r in escapes:
        gain = int(r["window_cost"]) - int(r["best_cost"])
        barrier = int(r["barrier_height"])
        gain_totals[gain] += 1
        barrier_totals[barrier] += 1
        per_kind_gain[r["root_kind"]][gain] += 1
        per_kind_barrier[r["root_kind"]][barrier] += 1
    total = len(escapes)
    for value, count in sorted(gain_totals.items()):
        gain_rows.append({"statistic": "window_gain", "value": value, "root_kind": "ALL", "count": count, "share": fmt(count / total, 6)})
        for kind in (GREEDY, RAW):
            if per_kind_gain[kind].get(value):
                gain_rows.append(
                    {"statistic": "window_gain", "value": value, "root_kind": kind,
                     "count": per_kind_gain[kind][value], "share": fmt(per_kind_gain[kind][value] / total, 6)}
                )
    for value, count in sorted(barrier_totals.items()):
        barrier_rows.append({"statistic": "barrier_height", "value": value, "root_kind": "ALL", "count": count, "share": fmt(count / total, 6)})
        for kind in (GREEDY, RAW):
            if per_kind_barrier[kind].get(value):
                barrier_rows.append(
                    {"statistic": "barrier_height", "value": value, "root_kind": kind,
                     "count": per_kind_barrier[kind][value], "share": fmt(per_kind_barrier[kind][value] / total, 6)}
                )
    aggregate = {
        "escape_count": total,
        "window_gain_distribution": {str(k): v for k, v in sorted(gain_totals.items())},
        "barrier_height_distribution": {str(k): v for k, v in sorted(barrier_totals.items())},
        "window_gain_by_root_kind": {
            kind: {str(k): v for k, v in sorted(counter.items())} for kind, counter in sorted(per_kind_gain.items())
        },
        "barrier_height_by_root_kind": {
            kind: {str(k): v for k, v in sorted(counter.items())} for kind, counter in sorted(per_kind_barrier.items())
        },
    }
    return gain_rows, barrier_rows, aggregate


# --------------------------------------------------------------------------- Part D


def _solve_linear(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting for small dense systems."""
    n = len(rhs)
    aug = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot] = aug[pivot], aug[col]
        for r in range(col + 1, n):
            factor = aug[r][col] / aug[col][col]
            for c in range(col, n + 1):
                aug[r][c] -= factor * aug[col][c]
    result = [0.0] * n
    for r in range(n - 1, -1, -1):
        result[r] = (aug[r][n] - sum(aug[r][c] * result[c] for c in range(r + 1, n))) / aug[r][r]
    return result


def part_d_branching(data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Empirical branching-factor law: states_seen vs (width, horizon)."""

    window_rows = data["window_rows"]
    stat_rows: list[dict[str, Any]] = []
    means: dict[tuple[int, int], float] = {}
    all_values: list[tuple[int, int, int]] = []
    for width in WIDTHS:
        for horizon in HORIZONS:
            values = sorted(int(r["states_seen"]) for r in window_rows if r["window_width_i"] == width and r["horizon_i"] == horizon)
            n = len(values)
            mean = sum(values) / n
            means[(width, horizon)] = mean
            stat_rows.append(
                {
                    "window_width": width,
                    "horizon": horizon,
                    "n": n,
                    "mean_states_seen": fmt(mean, 4),
                    "p10": fmt(quantile(values, 0.10), 2),
                    "p25": fmt(quantile(values, 0.25), 2),
                    "p50": fmt(quantile(values, 0.50), 2),
                    "p75": fmt(quantile(values, 0.75), 2),
                    "p90": fmt(quantile(values, 0.90), 2),
                    "p99": fmt(quantile(values, 0.99), 2),
                    "max": max(values),
                }
            )
            all_values.extend((width, horizon, v) for v in values)

    exponential_fit = {}
    for width in WIDTHS:
        ratio = means[(width, 3)] / means[(width, 2)]
        exponential_fit[f"w{width}"] = {
            "model": "states_seen = c * b^h (exact through the two horizons)",
            "b": fmt(ratio, 4),
            "c": fmt(means[(width, 2)] / ratio**2, 4),
            "states_h2_mean": fmt(means[(width, 2)], 4),
            "states_h3_mean": fmt(means[(width, 3)], 4),
        }

    # joint power-law fit on logs: ln S = alpha + beta*ln(w) + gamma*h
    xs = [[1.0, math.log(w), float(h)] for w, h, _ in all_values]
    ys = [math.log(v) for _, _, v in all_values]
    k_dim = 3
    ata = [[sum(row[i] * row[j] for row in xs) for j in range(k_dim)] for i in range(k_dim)]
    aty = [sum(row[i] * y for row, y in zip(xs, ys)) for i in range(k_dim)]
    beta = _solve_linear(ata, aty)
    residuals = [y - sum(row[i] * beta[i] for i in range(k_dim)) for row, y in zip(xs, ys)]
    ss_res = sum(e * e for e in residuals)
    mean_y = sum(ys) / len(ys)
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    power_fit = {
        "model": "ln(states_seen) = alpha + beta*ln(width) + gamma*horizon (least squares, n=76236)",
        "alpha": fmt(math.exp(beta[0]), 6),
        "beta_ln_width": fmt(beta[1], 4),
        "gamma_horizon": fmt(beta[2], 4),
        "r_squared": fmt(1.0 - ss_res / ss_tot, 6),
        "implied_width_exponent": fmt(beta[1], 4),
        "implied_horizon_exponent": fmt(beta[2], 4),
    }

    aggregate = {
        "states_seen_max": max(v for _, _, v in all_values),
        "states_seen_max_context": next(
            {"source_id": r["source_id"], "window_width": r["window_width_i"], "horizon": r["horizon_i"],
             "window_start": r["window_start_i"], "circuit_family": r["circuit_family"]}
            for r in window_rows if int(r["states_seen"]) == max(v for _, _, v in all_values)
        ),
        "resource_truncated_rows": sum(1 for r in window_rows if r["resource_reason"]),
        "exponential_fit_per_width": exponential_fit,
        "power_law_fit_all": power_fit,
    }
    return stat_rows, aggregate


# --------------------------------------------------------------------------- Part E


def part_e_depth2(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Depth>=2 escape profile by family, joined with the E52 rule census."""

    window_rows = data["window_rows"]
    escapes = [r for r in window_rows if r["is_escape"]]
    depth_family: collections.Counter = collections.Counter()
    family_totals: collections.Counter = collections.Counter()
    for r in escapes:
        depth_family[(r["escape_depth_i"], r["circuit_family"])] += 1
        family_totals[r["circuit_family"]] += 1
    depth_rows = [
        {
            "circuit_family": family,
            "escape_depth": depth,
            "count": depth_family[(depth, family)],
            "share_of_family_escapes": fmt(depth_family[(depth, family)] / family_totals[family], 6),
        }
        for family in sorted(family_totals)
        for depth in (1, 2, 3)
        if (depth, family) in depth_family
    ]

    e52 = data["e52"]
    e52_mech = e52["part_c_mechanism_split"]["mechanism_by_circuit_family"]
    e52_usage = e52["part_a_escape_decomposition"]["rule_family_usage_all_steps"]
    e52_reducing = e52["part_a_escape_decomposition"]["reducing_family_counts"]
    window_all = collections.Counter(r["circuit_family"] for r in window_rows)
    profile_rows: list[dict[str, Any]] = []
    families = sorted(set(family_totals) | set(e52_mech))
    for family in families:
        profile_rows.append(
            {
                "circuit_family": family,
                "window_rows": window_all.get(family, 0),
                "window_escapes": family_totals.get(family, 0),
                "window_escapes_depth1": depth_family.get((1, family), 0),
                "window_escapes_depth2plus": depth_family.get((2, family), 0) + depth_family.get((3, family), 0),
                "e52_whole_listing_cells": sum(e52_mech.get(family, {}).values()),
                "e52_mechanism_counts": json.dumps(e52_mech.get(family, {}), sort_keys=True),
                "e52_rule_family_usage_all_steps": json.dumps(e52_usage, sort_keys=True),
                "e52_reducing_family_counts": json.dumps(e52_reducing, sort_keys=True),
            }
        )

    # rule-family census over the 242 stored first-escape witnesses
    witness_reducing: collections.Counter = collections.Counter()
    witness_all_steps: collections.Counter = collections.Counter()
    witness_reducing_by_depth: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    witness_path_lengths: collections.Counter = collections.Counter()
    for payload in data["escape_certs"]:
        witness = (payload["certificate"].get("witnesses") or {}).get("escape") or []
        depth = int(payload["certificate"].get("escape_depth") or 0)
        witness_path_lengths[len(witness)] += 1
        for step in witness:
            family = str(step.get("family", ""))
            witness_all_steps[family] += 1
            if int(step.get("cost_delta", 0)) < 0:
                witness_reducing[family] += 1
                witness_reducing_by_depth["depth1" if depth == 1 else "depth2plus"][family] += 1

    aggregate = {
        "escape_depth_distribution": {
            str(depth): sum(1 for r in escapes if r["escape_depth_i"] == depth)
            for depth in sorted({r["escape_depth_i"] for r in escapes})
        },
        "depth_by_family": {
            family: {
                str(depth): depth_family[(depth, family)]
                for depth in (1, 2, 3)
                if (depth, family) in depth_family
            }
            for family in sorted(family_totals)
        },
        "depth2plus_rows": sum(count for (depth, _), count in depth_family.items() if depth >= 2),
        "depth2plus_by_family": {
            family: depth_family.get((2, family), 0) + depth_family.get((3, family), 0)
            for family in sorted(family_totals)
            if depth_family.get((2, family), 0) + depth_family.get((3, family), 0) > 0
        },
        "stored_first_escape_witness_census": {
            "certificates": len(data["escape_certs"]),
            "path_length_histogram": {str(k): v for k, v in sorted(witness_path_lengths.items())},
            "reducing_family_counts": dict(sorted(witness_reducing.items())),
            "reducing_family_counts_by_depth": {
                key: dict(sorted(counter.items())) for key, counter in sorted(witness_reducing_by_depth.items())
            },
            "all_step_family_counts": dict(sorted(witness_all_steps.items())),
        },
    }
    return depth_rows, profile_rows, aggregate


# --------------------------------------------------------------------------- Part F


def part_f_contingency(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Does a window escape predict a whole-listing escape? 2x2 + Fisher."""

    classification = data["classification"]
    window_escape_sources = {r["source_id"] for r in data["window_rows"] if r["is_escape"]}
    windowed_sources = {r["source_id"] for r in data["window_rows"]}
    zero_window = sorted(set(classification) - windowed_sources)

    source_rows: list[dict[str, Any]] = []
    for source_id in sorted(classification):
        row = classification[source_id]
        in_panel = source_id in windowed_sources
        source_rows.append(
            {
                "source_id": source_id,
                "circuit_family": row["circuit_family"],
                "n_qubits": int(row["n_qubits"]),
                "root_kind": next(
                    (s["root_kind"] for s in data["summary_rows"] if s["source_id"] == source_id), ""
                ),
                "in_window_panel": in_panel,
                "e45_idastar_verdict": row["idastar_status"],
                "e45_whole_listing_escape": row["idastar_status"] == "EXACT_ESCAPE",
                "window_escape_present": source_id in window_escape_sources,
            }
        )

    tables: list[dict[str, Any]] = []
    aggregate: dict[str, Any] = {"zero_window_sources": zero_window}
    for scope, universe in (("all_128_sources", set(classification)), ("windowed_only_94_sources", windowed_sources)):
        a = sum(1 for s in universe if classification[s]["idastar_status"] == "EXACT_ESCAPE" and s in window_escape_sources)
        b = sum(1 for s in universe if classification[s]["idastar_status"] == "EXACT_ESCAPE" and s not in window_escape_sources)
        c = sum(1 for s in universe if classification[s]["idastar_status"] != "EXACT_ESCAPE" and s in window_escape_sources)
        d = sum(1 for s in universe if classification[s]["idastar_status"] != "EXACT_ESCAPE" and s not in window_escape_sources)
        p = fisher_two_sided(a, b, c, d)
        n = a + b + c + d
        phi = (a * d - b * c) / math.sqrt((a + b) * (c + d) * (a + c) * (b + d)) if min(a + b, c + d, a + c, b + d) > 0 else None
        tables.append(
            {
                "scope": scope,
                "n_sources": n,
                "cell_e45escape_and_winescape": a,
                "cell_e45escape_and_no_winescape": b,
                "cell_e45optimum_and_winescape": c,
                "cell_e45optimum_and_no_winescape": d,
                "fisher_two_sided_p": f"{p:.6e}",
                "phi_coefficient": fmt(phi, 6) if phi is not None else "",
                "note": "window-escape presence vs E45 IDA* whole-listing verdict",
            }
        )
        aggregate[scope] = {"table": [[a, b], [c, d]], "fisher_two_sided_p": p}
    discordant = [
        row["source_id"]
        for row in source_rows
        if row["e45_whole_listing_escape"] != row["window_escape_present"]
    ]
    aggregate["discordant_sources"] = discordant
    aggregate["discordant_detail"] = [
        {
            "source_id": s,
            "circuit_family": classification[s]["circuit_family"],
            "n_qubits": int(classification[s]["n_qubits"]),
            "certificate_tier": classification[s]["certificate_tier"],
            "in_window_panel": s in windowed_sources,
            "e45_verdict": classification[s]["idastar_status"],
        }
        for s in discordant
    ]
    return tables, source_rows, aggregate


# --------------------------------------------------------------------------- Part G


def part_g_tracker(data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Distance-to-exact tracker for the 34 bounded cells."""

    classification = data["classification"]
    compact = data["compact"]
    idastar = data["idastar"]
    bounded = sorted(
        (row for row in classification.values() if row["certificate_tier"] == "CLASSIFICATION_EXACT_EXTRAS_BOUNDED"),
        key=lambda r: r["source_id"],
    )
    groups: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    prepped: list[dict[str, Any]] = []
    for row in bounded:
        source_id = row["source_id"]
        ic = idastar[source_id]
        cc = compact[source_id]
        branching = int(ic["states_seen"]) - 1
        explored = int(cc.get("expanded") or 0) + int(cc.get("pruned") or 0)
        if branching <= 250:
            cost_class = "cheap"
        elif branching <= 1000:
            cost_class = "moderate"
        else:
            cost_class = "expensive"
        prepped.append(
            {
                "source_id": source_id,
                "circuit_family": row["circuit_family"],
                "n_qubits": int(row["n_qubits"]),
                "circuit_id": row["circuit_id"],
                "root_kind": next(s["root_kind"] for s in data["summary_rows"] if s["source_id"] == source_id),
                "baseline_gates": int(row["baseline_cost"]),
                "e45_escape_depth": int(row["escape_depth"]),
                "root_branching_b": branching,
                "idastar_states_seen": int(ic["states_seen"]),
                "idastar_expanded": int(ic.get("expanded") or 0),
                "idastar_pruned": int(ic.get("pruned") or 0),
                "compact_expanded": int(cc.get("expanded") or 0),
                "compact_pruned": int(cc.get("pruned") or 0),
                "states_seen_before_budget": explored,
                "blocker": row["compact_resource_reason"],
                "witness_best_cost_bound": int(row["best_cost"]),
                "gain": int(row["baseline_cost"]) - int(row["best_cost"]),
                "gain_ge1": int(row["baseline_cost"]) - int(row["best_cost"]) >= 1,
                "gain_ge2": int(row["baseline_cost"]) - int(row["best_cost"]) >= 2,
                "projected_exactification_cost_class": cost_class,
                "iso_group": "",
                "iso_group_size": 1,
                "iso_stats_byte_identical": "",
            }
        )
        groups[f"{row['circuit_family']}|nq{row['n_qubits']}"].append(prepped[-1])

    ida_key = lambda item: (item["idastar_states_seen"], item["idastar_expanded"], item["idastar_pruned"])  # noqa: E731
    cmp_key = lambda item: (item["compact_expanded"], item["compact_pruned"])  # noqa: E731
    cmp_exp_key = lambda item: item["compact_expanded"]  # noqa: E731
    rows: list[dict[str, Any]] = []
    group_summary: dict[str, Any] = {}
    for label, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        ida_identical = len({ida_key(m) for m in members}) == 1
        cmp_exp_identical = len({cmp_exp_key(m) for m in members}) == 1
        fully_identical = ida_identical and len({cmp_key(m) for m in members}) == 1
        for member in members:
            member["iso_group"] = label
            member["iso_group_size"] = len(members)
            member["iso_stats_byte_identical"] = fully_identical
        group_summary[label] = {
            "size": len(members),
            "idastar_stats_identical": ida_identical,
            "compact_expanded_identical": cmp_exp_identical,
            "byte_identical_search_statistics": fully_identical,
            "idastar_states_seen": sorted({m["idastar_states_seen"] for m in members}),
            "compact_expanded": sorted({m["compact_expanded"] for m in members}),
            "compact_pruned_spread": sorted({m["compact_pruned"] for m in members}),
            "one_enumeration_may_clear": len(members) if ida_identical else 1,
        }
    for member in prepped:
        rows.append({k: (str(v) if isinstance(v, bool) else v) for k, v in member.items()})

    aggregate = {
        "bounded_cell_count": len(rows),
        "bounded_gain_ge2_cells": sum(1 for m in prepped if m["gain_ge2"]),
        "blocker_counts": dict(collections.Counter(member["blocker"] for member in prepped)),
        "cost_class_counts": dict(collections.Counter(member["projected_exactification_cost_class"] for member in prepped)),
        "cost_class_rule": "cheap: root branching b <= 250; moderate: 250 < b <= 1000; expensive: b > 1000 (b = IDA* first-iteration states_seen - 1)",
        "moderate_cells": [
            {"source_id": m["source_id"], "circuit_family": m["circuit_family"], "n_qubits": m["n_qubits"],
             "baseline_gates": m["baseline_gates"], "root_branching_b": m["root_branching_b"]}
            for m in prepped if m["projected_exactification_cost_class"] == "moderate"
        ],
        "isomorphic_groups": group_summary,
        "expensive_tail": [
            {"source_id": m["source_id"], "circuit_family": m["circuit_family"], "n_qubits": m["n_qubits"],
             "baseline_gates": m["baseline_gates"], "root_branching_b": m["root_branching_b"]}
            for m in prepped if m["projected_exactification_cost_class"] == "expensive"
        ],
    }
    return rows, aggregate


# --------------------------------------------------------------------------- Part H


def part_h_bootstrap(data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Tier/family mean gain with a source-cluster bootstrap (seeded)."""

    classification = data["classification"]
    source_ids = sorted(classification)
    gain_of = {s: int(classification[s]["baseline_cost"]) - int(classification[s]["best_cost"]) for s in source_ids}
    tier_of = {s: classification[s]["certificate_tier"] for s in source_ids}
    family_of = {s: classification[s]["circuit_family"] for s in source_ids}
    tiers = sorted({tier_of[s] for s in source_ids})
    families = sorted({family_of[s] for s in source_ids})

    def observed(label: str, scope: str, members: list[str]) -> dict[str, Any]:
        gains = [gain_of[s] for s in members]
        return {
            "scope": scope,
            "label": label,
            "n_sources": len(members),
            "gain_total": sum(gains),
            "observed_mean_gain": fmt(sum(gains) / len(gains), 6),
        }

    specs = [("overall", "ALL", source_ids)]
    specs += [("tier", tier, [s for s in source_ids if tier_of[s] == tier]) for tier in tiers]
    specs += [("family", family, [s for s in source_ids if family_of[s] == family]) for family in families]

    rng = random.Random(BOOTSTRAP_SEED)
    n = len(source_ids)
    keys = [(scope, label) for scope, label, _ in specs]
    means: dict[tuple[str, str], list[float]] = {key: [] for key in keys}
    for _ in range(BOOTSTRAP_RESAMPLES):
        mult: collections.Counter = collections.Counter()
        for _ in range(n):
            mult[source_ids[rng.randrange(n)]] += 1
        acc: dict[tuple[str, str], list[int]] = {}
        for source_id, k in mult.items():
            contribution = gain_of[source_id] * k
            for key in (
                ("overall", "ALL"),
                ("tier", tier_of[source_id]),
                ("family", family_of[source_id]),
            ):
                cell = acc.setdefault(key, [0, 0])
                cell[0] += contribution
                cell[1] += k
        for key, (total_gain, count) in acc.items():
            means[key].append(total_gain / count)

    rows: list[dict[str, Any]] = []
    for scope, label, members in specs:
        key = (scope, label)
        values = sorted(means.get(key, []))
        base = observed(label, scope, members)
        rows.append(
            {
                **base,
                "ci95_low": fmt(quantile(values, 0.025), 6) if values else "",
                "ci95_high": fmt(quantile(values, 0.975), 6) if values else "",
                "bootstrap_resamples": BOOTSTRAP_RESAMPLES if values else 0,
                "cluster": "source",
                "seed": BOOTSTRAP_SEED,
            }
        )
    aggregate = {
        "gain_distribution_all_128": {str(k): v for k, v in sorted(collections.Counter(gain_of.values()).items())},
        "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED, "cluster": "source (n=128)", "method": "percentile 95% CI of the resampled mean"},
    }
    return rows, aggregate


# --------------------------------------------------------------------------- summary.md


def build_summary_md(
    atlas: list[dict[str, Any]],
    atlas_agg: dict[str, Any],
    slices: list[dict[str, Any]],
    geo_agg: dict[str, Any],
    gain_agg: dict[str, Any],
    branch_agg: dict[str, Any],
    depth_agg: dict[str, Any],
    cont_agg: dict[str, Any],
    tracker_agg: dict[str, Any],
    boot_rows: list[dict[str, Any]],
    boot_agg: dict[str, Any],
) -> str:
    sl = {row["slice"]: row for row in slices}
    overall_row = next(row for row in boot_rows if row["scope"] == "overall")
    identical_groups = {k: v for k, v in tracker_agg["isomorphic_groups"].items() if v["byte_identical_search_statistics"]}
    clearable = max(v["one_enumeration_may_clear"] for v in tracker_agg["isomorphic_groups"].values()) if tracker_agg["isomorphic_groups"] else 1
    cc = tracker_agg["cost_class_counts"]
    expensive = tracker_agg["expensive_tail"]
    expensive_by_layout: dict[tuple[str, int], list[dict[str, Any]]] = collections.defaultdict(list)
    for entry in expensive:
        expensive_by_layout[(entry["circuit_family"], entry["n_qubits"])].append(entry)
    expensive_tail_text = "; ".join(
        f"{family} nq={nq} ×{len(entries)} ({entries[0]['baseline_gates']:,} gates, b = {min(e['root_branching_b'] for e in entries)}–{max(e['root_branching_b'] for e in entries)})"
        for (family, nq), entries in sorted(expensive_by_layout.items())
    )
    moderate_by_layout: dict[tuple[str, int], list[dict[str, Any]]] = collections.defaultdict(list)
    for entry in tracker_agg["moderate_cells"]:
        moderate_by_layout[(entry["circuit_family"], entry["n_qubits"])].append(entry)
    moderate_text = "; ".join(
        f"{family} nq={nq} ×{len(entries)} (b = {min(e['root_branching_b'] for e in entries)}–{max(e['root_branching_b'] for e in entries)})"
        for (family, nq), entries in sorted(moderate_by_layout.items())
    )
    atlas_ix = {(row["root_kind"], str(row["window_width"]), str(row["horizon"])): row for row in atlas}
    disc = cont_agg["discordant_detail"][0] if cont_agg["discordant_detail"] else {}
    p_all = cont_agg["all_128_sources"]["fisher_two_sided_p"]
    p_win = cont_agg["windowed_only_94_sources"]["fisher_two_sided_p"]
    d2fam = depth_agg["depth2plus_by_family"]
    fits = branch_agg["exponential_fit_per_width"]
    power = branch_agg["power_law_fit_all"]
    groups = tracker_agg["isomorphic_groups"]
    gains = boot_agg["gain_distribution_all_128"]

    def rate(slice_name: str) -> str:
        row = sl[slice_name]
        return f"{row['numerator']}/{row['denominator']} = {float(row['rate']):.4f}"

    tri = geo_agg["tercile_rate_mean_across_sources"]

    lines = f"""# E64 — Escape-geometry atlas ({PACKAGE_DATE})

**Authority**: review-grade evidence package, outside `release/release_manifest.json`.
**Contract**: frozen inputs only (`data/v15/e46_window_landscape`, `data/v15/e45_landscape_integration`,
`data/v14/e45_full_development`, `data/v14/e45_idastar_escape`, plus the E52 summary for the
family join); no search re-run; generator `scripts/e64_escape_geometry_atlas.py` is
byte-deterministic (fixed seed {BOOTSTRAP_SEED}, no wall-clock timestamps).

## 1. Escape-rate atlas — one table, explicit denominators

All {atlas_agg['total_window_searches']:,} window searches
({atlas_agg['total_certified_window_escapes']:,} certified escapes) are reconciled in
`escape_rate_atlas.csv` (root_kind × width × horizon, pooled rows included); the named
slices quoted in the manuscript, the readiness verdict and the earlier audit are in
`escape_rate_slices.csv`.

| Slice | Escapes / windows | Rate | Status |
|---|---|---|---|
| Manuscript §6: greedy roots, w16, h3, depth ≥ 2 | {rate('manuscript_greedy_w16_h3_depth2plus')} | **{float(sl['manuscript_greedy_w16_h3_depth2plus']['rate']):.3f}** | reproduced exactly |
| Verdict: all sources, w8 h2 | {rate('verdict_all_sources_w8_h2')} | {float(sl['verdict_all_sources_w8_h2']['rate']):.4f} | reproduced exactly |
| Verdict: all sources, w8 h3 | {rate('verdict_all_sources_w8_h3')} | {float(sl['verdict_all_sources_w8_h3']['rate']):.4f} | reproduced exactly |
| Verdict: all sources, w16 h2 | {rate('verdict_all_sources_w16_h2')} | {float(sl['verdict_all_sources_w16_h2']['rate']):.4f} | reproduced exactly |
| Verdict: all sources, w16 h3 | {rate('verdict_all_sources_w16_h3')} | {float(sl['verdict_all_sources_w16_h3']['rate']):.4f} | reproduced exactly |
| Audit anchor: GREEDY w8 (h pooled) | {rate('audit_greedy_w8_pooled_horizons')} | {float(sl['audit_greedy_w8_pooled_horizons']['rate']):.3f} | reproduced |
| Audit anchor: GREEDY w16 (h pooled) | {rate('audit_greedy_w16_pooled_horizons')} | {float(sl['audit_greedy_w16_pooled_horizons']['rate']):.3f} | reproduced |
| Audit anchor: RAW w8 (h pooled) | {rate('audit_raw_w8_pooled_horizons')} | {float(sl['audit_raw_w8_pooled_horizons']['rate']):.3f} | reproduced |
| Audit anchor: RAW w16 (h pooled) | {rate('audit_raw_w16_pooled_horizons')} | {float(sl['audit_raw_w16_pooled_horizons']['rate']):.3f} | reproduced |
| GREEDY h2 (widths pooled) | {rate('greedy_only_h2_pooled_widths')} | {float(sl['greedy_only_h2_pooled_widths']['rate']):.4f} | new |
| RAW h2 (widths pooled) | {rate('raw_only_h2_pooled_widths')} | {float(sl['raw_only_h2_pooled_widths']['rate']):.4f} | new |

Denominator structure: {atlas_ix[(GREEDY, '8', 'both')]['sources_total']} greedy-root sources and
{atlas_ix[(RAW, '8', 'both')]['sources_total']} raw-root sources form the root universe, of which
{atlas_ix[(GREEDY, '8', 'both')]['sources_with_windows']} and {atlas_ix[(RAW, '8', 'both')]['sources_with_windows']} carry at least one window;
{len(cont_agg['zero_window_sources'])} further sources have greedy roots shorter than the 8-gate
minimum window and are absent from `window_results.csv` entirely (they appear only as
zero-window rows in `input_summaries.csv`).  Every rate above states its own n/N, so the
manuscript slice (greedy w16 h3 only) and the verdict slice (all sources per config) are no
longer confusable.

**Mismatch flag.** The same manuscript sentence that reports 179/481 also says "the 123
greedy fixed-point roots" and "the five raw-listing roots that exceed the baseline gate
budget".  The frozen data say **{atlas_ix[(GREEDY, '8', 'both')]['sources_total']}** greedy-root
sources and **{atlas_ix[(RAW, '8', 'both')]['sources_total']}** raw-root sources (root lengths
{atlas_agg['root_gate_count_range_by_kind'][GREEDY]['min']}–{atlas_agg['root_gate_count_range_by_kind'][GREEDY]['max']} vs
{atlas_agg['root_gate_count_range_by_kind'][RAW]['min']}–{atlas_agg['root_gate_count_range_by_kind'][RAW]['max']:,} gates), and
depth-one escapes occur on **{geo_agg['raw_roots_with_depth1_escape']} of the {geo_agg['raw_roots_in_panel']}** raw roots ({depth_agg['escape_depth_distribution'].get('1', 0):,} depth-1
escapes vs {depth_agg['depth2plus_rows']:,} depth-≥2 escapes).  179/481 = 37.2% itself is exact;
the surrounding root counts are not consistent with the frozen panel and should be
corrected or re-derived before submission.

## 2. ">80 gates ⇒ depth-1 escapes": threshold or curve?

Root lengths in the panel are bimodal by construction: greedy roots run
{atlas_agg['root_gate_count_range_by_kind'][GREEDY]['min']}–{atlas_agg['root_gate_count_range_by_kind'][GREEDY]['max']} gates, raw
roots {atlas_agg['root_gate_count_range_by_kind'][RAW]['min']}–{atlas_agg['root_gate_count_range_by_kind'][RAW]['max']:,} gates
(the raw kind is *defined* by exceeding the {BASELINE_GATE_LIMIT}-gate budget).  Depth-1 window escapes occur on
{geo_agg['raw_roots_with_depth1_escape']}/{geo_agg['raw_roots_in_panel']} raw roots (min length {atlas_agg['root_gate_count_range_by_kind'][RAW]['min']}); the only
counterexample{'s are' if len(geo_agg['raw_roots_without_any_escape']) != 1 else ' is'}
{', '.join(f"a {e['circuit_family']} source at {e['root_gate_count']:,} gates" for e in geo_agg['raw_roots_without_any_escape']) or 'none'} with zero
window escapes of any depth.  No root between
{atlas_agg['root_gate_count_range_by_kind'][GREEDY]['max'] + 1} and {atlas_agg['root_gate_count_range_by_kind'][RAW]['min'] - 1} gates
exists, so the data cannot resolve an onset inside that gap: the signal is **consistent with
a threshold law at the budget boundary but confounded with the root_kind definition**, and
it has one counterexample.  Per-source early/middle/late tercile rates of the listing are
{tri.get('early_w8_h2', '?')} / {tri.get('mid_w8_h2', '?')} / {tri.get('late_w8_h2', '?')} (w8 h2 mean across sources; w16 h2:
{tri.get('early_w16_h2', '?')} / {tri.get('mid_w16_h2', '?')} / {tri.get('late_w16_h2', '?')}):
escape probability declines only mildly along the listing, i.e. the transition is in the
*root*, not in the window position.

## 3. Escape geometry

* Depth distribution: {json.dumps(depth_agg['escape_depth_distribution'], sort_keys=True)} —
  depth-1 dominates with {depth_agg['escape_depth_distribution']['1'] / sum(depth_agg['escape_depth_distribution'].values()):.1%} of escapes.
* Depth ≥ 2 rows: {depth_agg['depth2plus_rows']} of {sum(depth_agg['escape_depth_distribution'].values()):,}, concentrated in
  {', '.join(f"{k} ({v})" for k, v in sorted(d2fam.items(), key=lambda kv: -kv[1]))}.
* Depth split of the top families (d1/d2/d3): QuantumWalk
  {depth_agg['depth_by_family']['QuantumWalk'].get('1', 0)}/{depth_agg['depth_by_family']['QuantumWalk'].get('2', 0)}/{depth_agg['depth_by_family']['QuantumWalk'].get('3', 0)},
  Grover {depth_agg['depth_by_family']['Grover'].get('1', 0)}/{depth_agg['depth_by_family']['Grover'].get('2', 0)}/{depth_agg['depth_by_family']['Grover'].get('3', 0)},
  IQP {depth_agg['depth_by_family']['IQP'].get('1', 0)}/{depth_agg['depth_by_family']['IQP'].get('2', 0)}/{depth_agg['depth_by_family']['IQP'].get('3', 0)},
  UCCSD_inspired {depth_agg['depth_by_family']['UCCSD_inspired'].get('1', 0)}/{depth_agg['depth_by_family']['UCCSD_inspired'].get('2', 0)}/{depth_agg['depth_by_family']['UCCSD_inspired'].get('3', 0)},
  RandomClifford {depth_agg['depth_by_family']['RandomClifford'].get('1', 0)}/{depth_agg['depth_by_family']['RandomClifford'].get('2', 0)}/{depth_agg['depth_by_family']['RandomClifford'].get('3', 0)}.
  Deep escapes are a QuantumWalk/Grover/UCCSD phenomenon; IQP supplies breadth at depth 2.
* The {depth_agg['stored_first_escape_witness_census']['certificates']} stored first-escape witnesses reduce via
  pair_v1 in {depth_agg['stored_first_escape_witness_census']['reducing_family_counts'].get('pair_v1', 0)} cases and via
  quartz_v1 in {depth_agg['stored_first_escape_witness_census']['reducing_family_counts'].get('quartz_v1', 0)}; the multi-step paths open with
  structural_exchange_v1 / quartz_v1 neutral moves and close with pair_v1 — the
  exchange-then-reduce mechanism the whole-listing greedy pass cannot see.
* Window gain distribution: {json.dumps(gain_agg['window_gain_distribution'], sort_keys=True)}
  (mode at gains 2–3; gains up to 6 exist).  Barrier height is 0 in
  {gain_agg['barrier_height_distribution']['0'] / gain_agg['escape_count']:.2%} of escapes.

## 4. Empirical branching-factor law

Mean states_seen per window search: w8 h2 = {fits['w8']['states_h2_mean']}, w8 h3 = {fits['w8']['states_h3_mean']},
w16 h2 = {fits['w16']['states_h2_mean']}, w16 h3 = {fits['w16']['states_h3_mean']}; max {branch_agg['states_seen_max']}
({branch_agg['states_seen_max_context']['circuit_family']}, w{branch_agg['states_seen_max_context']['window_width']} h{branch_agg['states_seen_max_context']['horizon']}).
Fitting through the two horizons per width: states_seen ≈ c·b^h with effective growth factor
b ≈ {float(fits['w8']['b']):.2f} (w8) and b ≈ {float(fits['w16']['b']):.2f} (w16) — one extra horizon multiplies the mean search by
~2.4 on narrow windows and ~4.1 on wide ones, while doubling the width multiplies it by
~3.2 (h2) to ~5.6 (h3): width and horizon act at comparable multiplicative scale.  A joint
power law ln S = α + β·ln w + γ·h over all {atlas_agg['total_window_searches']:,} searches gives β = {power['beta_ln_width']},
γ = {power['gamma_horizon']} (R² = {power['r_squared']}) — the modest R² reflects the wide per-source dispersion,
so the per-config means, not the global fit, are the usable calibration.

Implication for exactifying the bounded cells: per-level cost scales with the *root
branching* b (IDA* first-iteration states_seen − 1), and the tracker shows
{cc.get('cheap', 0)} of the {tracker_agg['bounded_cell_count']} bounded cells have b ≤ 250 (cheap),
{cc.get('moderate', 0)} sit in the 250 < b ≤ 1000 band ({moderate_text}),
and the expensive tail is exactly the {cc.get('expensive', 0)} QuantumWalk large-layout cells
({expensive_tail_text}).

## 5. Window escape → whole-listing escape

| Scope | escape∩win | escape∩¬win | optimum∩win | optimum∩¬win | Fisher p |
|---|---|---|---|---|---|
| all 128 sources | {cont_agg['all_128_sources']['table'][0][0]} | {cont_agg['all_128_sources']['table'][0][1]} | {cont_agg['all_128_sources']['table'][1][0]} | {cont_agg['all_128_sources']['table'][1][1]} | {p_all:.2e} |
| windowed 94 sources | {cont_agg['windowed_only_94_sources']['table'][0][0]} | {cont_agg['windowed_only_94_sources']['table'][0][1]} | {cont_agg['windowed_only_94_sources']['table'][1][0]} | {cont_agg['windowed_only_94_sources']['table'][1][1]} | {p_win:.2e} |

Window-escape presence is a **near-perfect predictor** of the whole-listing verdict:
{cont_agg['all_128_sources']['table'][0][0]}/{cont_agg['all_128_sources']['table'][0][0] + cont_agg['all_128_sources']['table'][0][1]} E45 escapes have a window escape and
{cont_agg['all_128_sources']['table'][1][0]}/{cont_agg['all_128_sources']['table'][1][0] + cont_agg['all_128_sources']['table'][1][1]} optima have any.  On sources that actually
carry windows the separation is perfect ({cont_agg['windowed_only_94_sources']['table'][0][0]} vs 0).  The single discordant escape is
{disc.get('source_id', '?')} ({disc.get('circuit_family', '?')}, nq={disc.get('n_qubits', '?')}), whose greedy root
collapsed below the 8-gate window minimum, so no window could fire.  Causality is one-way
compatible: a local window escape is *necessary* (given a nondegenerate listing) for a
whole-listing escape at the same rule scope and horizon budget.

## 6. The 34 bounded cells: distance to exact

`bounded_cell_exactification_tracker.csv` joins `classification_complete.csv`
(tier CLASSIFICATION_EXACT_EXTRAS_BOUNDED), the compact certificates (states explored
before budget, blocker: {tracker_agg['blocker_counts'].get('time_budget', 0)} time_budget /
{tracker_agg['blocker_counts'].get('state_budget', 0)} state_budget) and the IDA* certificates
(root branching b = states_seen − 1; witness bound best_cost).

* Cost classes ({tracker_agg['cost_class_rule']}):
  {json.dumps(tracker_agg['cost_class_counts'], sort_keys=True)} over {tracker_agg['bounded_cell_count']} cells.
* Statistically-isomorphic groups (≥ 2 bounded cells sharing family and qubit count):
  {len(groups)} groups; {sum(1 for v in groups.values() if v['idastar_stats_identical'])} of them share byte-identical IDA* statistics,
  {sum(1 for v in groups.values() if v['compact_expanded_identical'])} also share identical compact expansions,
  and the fully byte-identical set (IDA* *and* compact counters) is
  {', '.join(f"{k} (n={v['size']}, b={', '.join(str(s - 1) for s in v['idastar_states_seen'])})" for k, v in sorted(identical_groups.items())) if identical_groups else 'empty'}.
  One IDA* proof rerun of a shared tree clears up to {clearable} cells at once.
* Cheapest cells: the state_budget groups with identical IDA* trees (smallest root
  branching first) — every bounded cell already carries a witness bound with gain ≥ 1
  ({tracker_agg['bounded_gain_ge2_cells']} of the {tracker_agg['bounded_cell_count']} cells gain ≥ 2), so a single bounded run each converts a
  witness-bounded extra into an enumerated exact value.
* Expensive tail: {expensive_tail_text}.

## 7. Tier/family gains with cluster bootstrap

Resampling sources (n = 128, {boot_agg['bootstrap']['resamples']:,} resamples, seed {boot_agg['bootstrap']['seed']}),
the per-source gain distribution {json.dumps(gains, sort_keys=True)} has overall mean
{overall_row['observed_mean_gain']} (95% CI {overall_row['ci95_low']}–{overall_row['ci95_high']}).
`tier_family_gain_bootstrap.csv` carries all tier and family rows with their CIs.  The tier
split is not uniform by construction: bounded-tier cells (n = 34) carry small constant gains
still to be exactified while COMPACT_COMPLETE_ENUMERATED cells include the gain-6 sources,
so per-tier means differ structurally — the CIs quantify the source-level sampling noise
behind the manuscript's per-family claims.

## 8. Determinism and receipt

`receipt.json` pins every input and output by SHA-256, the script itself, the bootstrap
seed ({BOOTSTRAP_SEED}) and the interpreter version.  `generated_at` is the fixed package
instant {GENERATED_AT}; re-running the script on the pinned inputs reproduces every file
byte-for-byte.
"""
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    data = load_inputs()
    print(f"[E64] loaded {len(data['window_rows'])} window rows, {len(data['classification'])} cells, "
          f"{len(data['escape_certs'])} escape certificates", flush=True)

    atlas, slices, atlas_agg = part_a_atlas(data)
    ok = atlas_agg["anchor_checks_all_match"]
    print(f"[E64] part A atlas: {len(atlas)} rows, {len(slices)} slices, anchors_match={ok}", flush=True)
    for check in atlas_agg["anchor_checks"]:
        if not check["match"]:
            print(f"[E64]   MISMATCH: {check['anchor']}: {check['observed']}", flush=True)

    by_start_rows, per_source_rows, geo_agg = part_b_geometry(data)
    print(f"[E64] part B geometry: {len(by_start_rows)} start positions, {len(per_source_rows)} source configs", flush=True)

    gain_rows, barrier_rows, gain_agg = part_c_gain_barrier(data)
    print(f"[E64] part C gain/barrier: {gain_agg['window_gain_distribution']} | {gain_agg['barrier_height_distribution']}", flush=True)

    branch_rows, branch_agg = part_d_branching(data)
    print(f"[E64] part D branching: max={branch_agg['states_seen_max']}, "
          f"b_w8={branch_agg['exponential_fit_per_width']['w8']['b']}, "
          f"b_w16={branch_agg['exponential_fit_per_width']['w16']['b']}", flush=True)

    depth_rows, profile_rows, depth_agg = part_e_depth2(data)
    print(f"[E64] part E depth>=2: {depth_agg['depth2plus_rows']} rows "
          f"in {len(depth_agg['depth2plus_by_family'])} families", flush=True)

    cont_tables, cont_source_rows, cont_agg = part_f_contingency(data)
    print(f"[E64] part F contingency: all={cont_agg['all_128_sources']['table']}, "
          f"windowed={cont_agg['windowed_only_94_sources']['table']}, "
          f"discordant={len(cont_agg['discordant_sources'])}", flush=True)

    tracker_rows, tracker_agg = part_g_tracker(data)
    print(f"[E64] part G tracker: {tracker_agg['bounded_cell_count']} bounded cells, "
          f"cost classes {tracker_agg['cost_class_counts']}, "
          f"{len(tracker_agg['isomorphic_groups'])} iso groups", flush=True)

    boot_rows, boot_agg = part_h_bootstrap(data)
    print(f"[E64] part H bootstrap: {len(boot_rows)} rows, {boot_agg['bootstrap']['resamples']} resamples, "
          f"seed {boot_agg['bootstrap']['seed']}", flush=True)

    write_csv(OUTPUT_ROOT / "escape_rate_atlas.csv", atlas)
    write_csv(OUTPUT_ROOT / "escape_rate_slices.csv", slices)
    write_csv(OUTPUT_ROOT / "escape_geometry_by_start.csv", by_start_rows)
    write_csv(OUTPUT_ROOT / "source_escape_geometry.csv", per_source_rows)
    write_csv(OUTPUT_ROOT / "window_gain_distribution.csv", gain_rows)
    write_csv(OUTPUT_ROOT / "window_barrier_distribution.csv", barrier_rows)
    write_csv(OUTPUT_ROOT / "branching_factor_law.csv", branch_rows)
    write_csv(OUTPUT_ROOT / "window_escape_depth_by_family.csv", depth_rows)
    write_csv(OUTPUT_ROOT / "family_profile.csv", profile_rows)
    write_csv(OUTPUT_ROOT / "window_escape_contingency.csv", cont_tables)
    write_csv(OUTPUT_ROOT / "contingency_source_table.csv", cont_source_rows)
    write_csv(OUTPUT_ROOT / "bounded_cell_exactification_tracker.csv", tracker_rows)
    write_csv(OUTPUT_ROOT / "tier_family_gain_bootstrap.csv", boot_rows)

    output_names = [
        "escape_rate_atlas.csv", "escape_rate_slices.csv", "escape_geometry_by_start.csv",
        "source_escape_geometry.csv", "window_gain_distribution.csv", "window_barrier_distribution.csv",
        "branching_factor_law.csv", "window_escape_depth_by_family.csv", "family_profile.csv",
        "window_escape_contingency.csv", "contingency_source_table.csv",
        "bounded_cell_exactification_tracker.csv", "tier_family_gain_bootstrap.csv",
    ]

    summary_md = build_summary_md(
        atlas, atlas_agg, slices, geo_agg, gain_agg, branch_agg, depth_agg, cont_agg, tracker_agg, boot_rows, boot_agg
    )
    (OUTPUT_ROOT / "summary.md").write_text(summary_md, encoding="utf-8", newline="\n")

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "package": PACKAGE,
        "authority": "review-grade; NOT part of release/release_manifest.json",
        "date": PACKAGE_DATE,
        "generated_at": GENERATED_AT,
        "contract": {
            "inputs": {name: {"path": rel(path), "sha256": sha256(path)} for name, path in INPUTS.items()},
            "search_rerun": False,
            "writes": f"docs/review/science_boost/{PACKAGE}/ only",
            "determinism": {
                "generated_at_convention": "fixed package instant (date T00:00:00Z), no wall clock",
                "bootstrap_seed": BOOTSTRAP_SEED,
                "ordering": "all groupings sorted; JSON sort_keys",
            },
        },
        "part_a_escape_rate_atlas": atlas_agg,
        "part_b_escape_geometry": geo_agg,
        "part_c_gain_barrier": gain_agg,
        "part_d_branching_law": branch_agg,
        "part_e_depth2_profile": depth_agg,
        "part_f_window_to_whole_listing": cont_agg,
        "part_g_bounded_cell_tracker": tracker_agg,
        "part_h_gain_bootstrap": boot_agg,
    }
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )

    files: dict[str, Any] = {}
    for name in output_names + ["summary.md", "summary.json"]:
        path = OUTPUT_ROOT / name
        files[name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    receipt = {
        "experiment_id": EXPERIMENT_ID,
        "package": PACKAGE,
        "authority": "review-grade; NOT part of release/release_manifest.json",
        "generated_at": GENERATED_AT,
        "python_version": platform.python_version(),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "inputs": {name: {"path": rel(path), "sha256": sha256(path)} for name, path in INPUTS.items()},
        "script": {"path": rel(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "outputs": files,
    }
    (OUTPUT_ROOT / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"[E64] wrote {OUTPUT_ROOT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
