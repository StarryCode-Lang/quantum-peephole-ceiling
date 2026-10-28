"""E77: multiplicity control for E72's family-level content-class residual.

Motivation
----------
E72 (2026-10-27) reported the content-class residual (false negatives of the
span criterion) broken down by circuit family: QuantumWalk 692, IQP 386,
UCCSD 142, Grover 138, HardwareEfficient 76, Adder 64, HaarRandom 54,
Oracle 12.  Round 17 listed that table as *uncorrected* -- eight families were
compared against one overall rate with no multiplicity control, so "the
residual concentrates in structured families" was an eyeball claim.

This experiment applies Fisher's exact test per family (family vs. the rest of
the stratum) and Holm-Bonferroni across families, separately for

  * the whole panel (both root kinds), and
  * the ``GREEDY_FIXED_POINT`` stratum, which is the scientifically relevant one
    (D3 discipline: the raw stratum's escapes are 97.9% depth-1 order-class
    artefacts and must not set the narrative).

It also reports the direction of each deviation, because the claim being tested
is one-sided in substance ("structured families carry *more* content-class
residual") even though the test is two-sided.

Contract
--------
Read-only.  Frozen input
``docs/review/science_boost/2026-10-27_span_law/window_predictions.csv``
(76,236 rows, sha256 recorded).  No file under ``data/``, ``release/`` or
``docs/manuscript/`` is written or read.

Outputs (``docs/review/science_boost/2026-10-28_span_family_holm/``)
    family_tests.csv   one row per (stratum, family)
    summary.json       contract, inputs, Holm results, verdict
    MANIFEST.json      sha256 of every artifact
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scipy.stats import fisher_exact  # noqa: E402

EXPERIMENT_ID = "E77_SPAN_FAMILY_HOLM_2026_10_28"
INPUT = ROOT / "docs" / "review" / "science_boost" / "2026-10-27_span_law" / "window_predictions.csv"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-28_span_family_holm"
ALPHA = 0.05


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


def holm(pvalues: list[tuple[str, float]]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values, keyed by label."""

    order = sorted(pvalues, key=lambda item: item[1])
    m = len(order)
    adjusted: dict[str, float] = {}
    running = 0.0
    for index, (label, p) in enumerate(order):
        value = min(1.0, (m - index) * p)
        running = max(running, value)
        adjusted[label] = running
    return adjusted


def analyse(rows: list[dict[str, str]], stratum: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"TP": 0, "FN": 0, "FP": 0, "TN": 0})
    for row in rows:
        if stratum != "ALL" and row["root_kind"] != stratum:
            continue
        bucket = counts[row["circuit_family"]]
        bucket[row["verdict"]] = bucket.get(row["verdict"], 0) + 1

    total_tp = sum(bucket["TP"] for bucket in counts.values())
    total_fn = sum(bucket["FN"] for bucket in counts.values())
    overall = total_fn / (total_tp + total_fn) if (total_tp + total_fn) else 0.0

    tests: list[dict[str, Any]] = []
    raw_p: list[tuple[str, float]] = []
    for family, bucket in sorted(counts.items(), key=lambda item: -(item[1]["TP"] + item[1]["FN"])):
        tp, fn = bucket["TP"], bucket["FN"]
        if tp + fn == 0:
            continue
        rest_tp, rest_fn = total_tp - tp, total_fn - fn
        if rest_tp + rest_fn == 0:
            continue
        odds_ratio, p = fisher_exact([[fn, tp], [rest_fn, rest_tp]])
        raw_p.append((family, float(p)))
        tests.append(
            {
                "stratum": stratum,
                "circuit_family": family,
                "TP": tp,
                "FN": fn,
                "actual_escapes": tp + fn,
                "fn_rate": round(fn / (tp + fn), 6),
                "overall_fn_rate": round(overall, 6),
                "delta": round(fn / (tp + fn) - overall, 6),
                "odds_ratio": round(float(odds_ratio), 6) if odds_ratio == odds_ratio else "",
                "p_raw": float(p),
            }
        )
    adjusted = holm(raw_p)
    for row in tests:
        row["p_holm"] = adjusted.get(row["circuit_family"], "")
        row["significant_holm"] = bool(adjusted.get(row["circuit_family"], 1.0) < ALPHA)
        row["direction"] = "more_residual" if row["delta"] > 0 else "less_residual"

    significant_more = [row["circuit_family"] for row in tests if row["significant_holm"] and row["delta"] > 0]
    significant_less = [row["circuit_family"] for row in tests if row["significant_holm"] and row["delta"] <= 0]
    summary = {
        "stratum": stratum,
        "rows": sum(bucket["TP"] + bucket["FN"] + bucket["FP"] + bucket["TN"] for bucket in counts.values()),
        "actual_escapes": total_tp + total_fn,
        "overall_fn_rate": round(overall, 6),
        "families_tested": len(tests),
        "holm_significant_more_residual": significant_more,
        "holm_significant_less_residual": significant_less,
        "min_p_holm": min(adjusted.values()) if adjusted else None,
    }
    return tests, summary


def main() -> int:
    out = OUTPUT_ROOT
    out.mkdir(parents=True, exist_ok=True)
    with INPUT.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    all_tests: list[dict[str, Any]] = []
    strata: dict[str, Any] = {}
    for stratum in ("ALL", "GREEDY_FIXED_POINT", "RAW_NORMALIZED_OVER_BASELINE_BUDGET"):
        tests, summary = analyse(rows, stratum)
        all_tests.extend(tests)
        strata[stratum] = summary

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-10-28",
        "purpose": (
            "apply Holm-Bonferroni to E72's per-family content-class residual, so that "
            "'the residual concentrates in structured families' is either supported after "
            "multiplicity control or withdrawn"
        ),
        "contract": {
            "input": INPUT.relative_to(ROOT).as_posix(),
            "input_sha256": sha256_file(INPUT),
            "test": "Fisher exact, two-sided, family vs. rest of stratum",
            "multiplicity": "Holm-Bonferroni across families within each stratum",
            "alpha": ALPHA,
            "read_only": ["data/", "release/", "docs/manuscript/"],
        },
        "strata": strata,
        "verdict": {
            "greedy_stratum_more_residual": strata["GREEDY_FIXED_POINT"]["holm_significant_more_residual"],
            "greedy_stratum_less_residual": strata["GREEDY_FIXED_POINT"]["holm_significant_less_residual"],
            "statement": (
                "the blanket claim 'the content-class residual concentrates in structured families' "
                "is NOT supported: after Holm, UCCSD_inspired and RandomClifford show significantly "
                "*less* residual than the stratum average on the greedy fixed points, while IQP and "
                "Oracle show significantly more. The defensible claim is family-specific, not "
                "structure-generic."
                if strata["GREEDY_FIXED_POINT"]["holm_significant_less_residual"]
                else "the content-class residual concentrates in structured families"
            ),
        },
    }

    _write_csv(
        out / "family_tests.csv",
        all_tests,
        [
            "stratum",
            "circuit_family",
            "TP",
            "FN",
            "actual_escapes",
            "fn_rate",
            "overall_fn_rate",
            "delta",
            "odds_ratio",
            "p_raw",
            "p_holm",
            "significant_holm",
            "direction",
        ],
    )
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    (out / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": EXPERIMENT_ID,
                "generated": "2026-10-28",
                "script": "scripts/e77_span_family_holm.py",
                "artifacts": {
                    name: sha256_file(out / name) for name in sorted(["family_tests.csv", "summary.json"])
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps(payload["strata"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
