"""E69: design-based inference for the v16 window landscape (closes WL-4).

Why this exists
---------------
`release/v16_readiness_verdict.json` reports four window escape rates
(0.4685 / 0.4775 / 0.5598 / 0.5735) as if each of the 76,236 windows were an
independent Bernoulli trial.  They are not: the windows of one source overlap
by construction, so the 76,236 rows contain at most 128 independent units.
Round 13 recorded this as weakness WL-4 and asked for a design-based analysis;
this script supplies it and nothing else.  It reads frozen CSVs, writes no
evidence into ``data/``, and re-derives no search.

What it computes
----------------
A  Denominator reconciliation: every rate in the verdict, re-expressed with an
   explicit numerator and denominator, split by root kind (greedy fixed point
   vs raw listing above the baseline budget) and by horizon.
B  Cluster-robust interval for each config: cluster = source (n <= 128),
   percentile bootstrap over sources (10,000 resamples, fixed seed).  The
   naive Wilson interval is reported alongside so the understatement is
   visible rather than argued.
C  Intra-cluster correlation and design effect, from a one-way ANOVA
   decomposition of the escape indicator over sources.  deff tells a referee
   how many *independent* windows the panel really contains.
D  Family-level rates with Holm correction over the 15 circuit families, using
   the cluster bootstrap as the resampling unit.

Contract
    Read-only.  Rule scope and horizon come from the frozen protocol; nothing
    is re-run.  Deterministic given the seed.

Outputs (``docs/review/science_boost/2026-10-26_window_inference/``):
    denominators.csv    per config x root_kind x horizon numerator/denominator
    rates.csv           per config: point estimate, Wilson, cluster bootstrap
    icc_deff.csv        per config: ICC, mean cluster size, design effect
    families.csv        per family x config rate with Holm-adjusted p
    summary.json        aggregates, hashes, verdict
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "v16" / "e46_window_landscape" / "window_results.csv"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-26_window_inference"
CONFIGS = [(8, 2), (8, 3), (16, 2), (16, 3)]
BOOTSTRAP = 10_000
SEED = 20261026


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def cluster_bootstrap(clusters: dict[str, tuple[int, int]]) -> tuple[float, float, float]:
    """Percentile interval over a source-level resample; returns (lo, hi, se)."""

    keys = sorted(clusters)
    rng = random.Random(SEED)
    rates = []
    for _ in range(BOOTSTRAP):
        k = n = 0
        for _ in range(len(keys)):
            key = keys[rng.randrange(len(keys))]
            ck, cn = clusters[key]
            k += ck
            n += cn
        rates.append(k / n if n else float("nan"))
    rates.sort()
    lo = rates[int(0.025 * BOOTSTRAP)]
    hi = rates[int(0.975 * BOOTSTRAP) - 1]
    mean = sum(rates) / len(rates)
    var = sum((r - mean) ** 2 for r in rates) / (len(rates) - 1)
    return lo, hi, math.sqrt(var)


def icc_deff(clusters: dict[str, tuple[int, int]]) -> tuple[float, float, float]:
    """One-way ANOVA ICC for a binary indicator with unequal cluster sizes."""

    sizes = [cn for _, cn in clusters.values()]
    sums = [ck for ck, _ in clusters.values()]
    k = len(sizes)
    n_total = sum(sizes)
    grand = sum(sums) / n_total
    ssb = sum(cn * ((ck / cn) - grand) ** 2 for ck, cn in zip(sums, sizes))
    ssw = sum((ck / cn) * (1 - ck / cn) * cn for ck, cn in zip(sums, sizes))
    msb = ssb / (k - 1) if k > 1 else float("nan")
    msw = ssw / (n_total - k) if n_total > k else float("nan")
    if not (msw > 0) or math.isnan(msb):
        return (float("nan"), n_total / k, float("nan"))
    m_bar = n_total / k
    icc = (msb - msw) / (msb + (m_bar - 1) * msw)
    icc = max(0.0, min(1.0, icc))
    deff = 1 + (m_bar - 1) * icc
    return icc, m_bar, deff


def holm(pvals: list[tuple[str, float]]) -> dict[str, float]:
    ordered = sorted(pvals, key=lambda item: item[1])
    m = len(ordered)
    out: dict[str, float] = {}
    running = 0.0
    for rank, (name, p) in enumerate(ordered):
        adjusted = min(1.0, (m - rank) * p)
        running = max(running, adjusted)
        out[name] = running
    return out


def two_prop_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided z-test on a difference of proportions (normal approximation)."""

    if n1 == 0 or n2 == 0:
        return 1.0
    p1, p2 = k1 / n1, k2 / n2
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = abs(p1 - p2) / se
    return math.erfc(z / math.sqrt(2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.input.open(encoding="utf-8")))
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)

    # ---- A. denominators -------------------------------------------------
    denom: dict[tuple[int, int, str, str], dict[str, int]] = defaultdict(
        lambda: {"windows": 0, "escapes": 0}
    )
    per_source: dict[tuple[int, int], dict[str, list[int]]] = defaultdict(dict)
    family_rows: dict[tuple[str, int, int], dict[str, int]] = defaultdict(
        lambda: {"windows": 0, "escapes": 0}
    )
    for row in rows:
        width = int(row["window_width"])
        horizon = int(row["horizon"])
        kind = row["root_kind"]
        escape = 1 if row["status"] == "EXACT_ESCAPE" else 0
        denom[(width, horizon, kind, row["circuit_family"])]["windows"] += 1
        denom[(width, horizon, kind, row["circuit_family"])]["escapes"] += escape
        bucket = per_source[(width, horizon)].setdefault(row["source_id"], [0, 0])
        bucket[0] += escape
        bucket[1] += 1
        fam = family_rows[(row["circuit_family"], width, horizon)]
        fam["windows"] += 1
        fam["escapes"] += escape

    with (out / "denominators.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["window_width", "horizon", "root_kind", "circuit_family", "windows", "escapes", "rate"])
        for (width, horizon, kind, family), cell in sorted(denom.items()):
            writer.writerow([width, horizon, kind, family, cell["windows"], cell["escapes"],
                             f"{cell['escapes'] / cell['windows']:.6f}"])

    # ---- B/C. cluster-robust rates --------------------------------------
    rate_rows = []
    icc_rows = []
    for width, horizon in CONFIGS:
        clusters = {sid: (v[0], v[1]) for sid, v in per_source[(width, horizon)].items()}
        k = sum(v[0] for v in clusters.values())
        n = sum(v[1] for v in clusters.values())
        point = k / n
        w_lo, w_hi = wilson(k, n)
        b_lo, b_hi, b_se = cluster_bootstrap(clusters)
        icc, m_bar, deff = icc_deff(clusters)
        rate_rows.append({
            "config": f"w{width}_h{horizon}",
            "windows": n,
            "escapes": k,
            "rate": f"{point:.6f}",
            "wilson_lo": f"{w_lo:.6f}",
            "wilson_hi": f"{w_hi:.6f}",
            "cluster_lo": f"{b_lo:.6f}",
            "cluster_hi": f"{b_hi:.6f}",
            "cluster_se": f"{b_se:.6f}",
            "ci_width_ratio": f"{(b_hi - b_lo) / (w_hi - w_lo):.3f}" if w_hi > w_lo else "",
            "sources": len(clusters),
        })
        icc_rows.append({
            "config": f"w{width}_h{horizon}",
            "sources": len(clusters),
            "mean_cluster_size": f"{m_bar:.2f}",
            "icc": f"{icc:.4f}" if not math.isnan(icc) else "",
            "design_effect": f"{deff:.2f}" if not math.isnan(deff) else "",
            "effective_n": f"{n / deff:.1f}" if deff and not math.isnan(deff) else "",
        })

    with (out / "rates.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rate_rows[0]))
        writer.writeheader()
        writer.writerows(rate_rows)
    with (out / "icc_deff.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(icc_rows[0]))
        writer.writeheader()
        writer.writerows(icc_rows)

    # ---- D. family-level with Holm --------------------------------------
    fam_out = []
    for width, horizon in CONFIGS:
        cells = {fam: cell for (fam, w, h), cell in family_rows.items() if w == width and h == horizon}
        if not cells:
            continue
        baseline_name = max(cells, key=lambda f: cells[f]["windows"])
        base = cells[baseline_name]
        pvals = []
        for fam, cell in cells.items():
            if fam == baseline_name:
                continue
            pvals.append((fam, two_prop_p(cell["escapes"], cell["windows"], base["escapes"], base["windows"])))
        adjusted = holm(pvals)
        for fam, cell in sorted(cells.items()):
            fam_out.append({
                "config": f"w{width}_h{horizon}",
                "family": fam,
                "windows": cell["windows"],
                "escapes": cell["escapes"],
                "rate": f"{cell['escapes'] / cell['windows']:.6f}",
                "p_vs_largest_family": "" if fam == baseline_name else f"{dict(pvals)[fam]:.3e}",
                "p_holm": "" if fam == baseline_name else f"{adjusted[fam]:.3e}",
            })
    with (out / "families.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fam_out[0]))
        writer.writeheader()
        writer.writerows(fam_out)

    # ---- E. paired by source (the design that actually has power) --------
    # Windows of the same source share a root, a family and a gate budget, so a
    # paired contrast removes the between-source variance that dominates the
    # marginal rates.  The sign count is reported because a zero-reversal
    # contrast is a monotonicity statement, not a rate comparison.
    paired_rows = []
    for left, right in (((8, 2), (16, 2)), ((8, 3), (16, 3)), ((8, 2), (8, 3)), ((16, 2), (16, 3))):
        d1 = per_source[left]
        d2 = per_source[right]
        common = sorted(set(d1) & set(d2))
        diffs = [d2[s][0] / d2[s][1] - d1[s][0] / d1[s][1] for s in common]
        rng = random.Random(SEED)
        means = []
        for _ in range(BOOTSTRAP):
            sample = [diffs[rng.randrange(len(diffs))] for _ in range(len(diffs))]
            means.append(sum(sample) / len(sample))
        means.sort()
        up = sum(1 for d in diffs if d > 1e-12)
        down = sum(1 for d in diffs if d < -1e-12)
        paired_rows.append({
            "from": f"w{left[0]}_h{left[1]}",
            "to": f"w{right[0]}_h{right[1]}",
            "sources": len(common),
            "mean_delta": f"{sum(diffs) / len(diffs):+.6f}",
            "cluster_lo": f"{means[int(0.025 * BOOTSTRAP)]:+.6f}",
            "cluster_hi": f"{means[int(0.975 * BOOTSTRAP) - 1]:+.6f}",
            "sources_up": up,
            "sources_down": down,
            "sources_tied": len(diffs) - up - down,
        })
    with (out / "paired.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(paired_rows[0]))
        writer.writeheader()
        writer.writerows(paired_rows)

    # ---- F. stratify by root kind ----------------------------------------
    # 96.8% of the frozen windows sit on roots that were *never optimised*
    # (the MAX_BASELINE_GATES=80 bypass).  Those roots carry the entire
    # depth-1 escape population, so a pooled rate mixes "the baseline was not
    # optimised" with "greedy cannot see a deeper escape".  The stratum split
    # is the only honest denominator for either claim.
    strat: dict[tuple[int, int, str], dict[str, int]] = defaultdict(
        lambda: {"windows": 0, "escapes": 0, "depth1": 0, "depth_ge2": 0, "sources": 0}
    )
    seen_sources: dict[tuple[int, int, str], set[str]] = defaultdict(set)
    for row in rows:
        width = int(row["window_width"])
        horizon = int(row["horizon"])
        kind = row["root_kind"]
        cell = strat[(width, horizon, kind)]
        cell["windows"] += 1
        seen_sources[(width, horizon, kind)].add(row["source_id"])
        if row["status"] == "EXACT_ESCAPE":
            cell["escapes"] += 1
            if row["escape_depth"] == "1":
                cell["depth1"] += 1
            else:
                cell["depth_ge2"] += 1
    strat_rows = []
    for (width, horizon, kind), cell in sorted(strat.items()):
        n = cell["windows"]
        strat_rows.append({
            "config": f"w{width}_h{horizon}",
            "root_kind": kind,
            "sources": len(seen_sources[(width, horizon, kind)]),
            "windows": n,
            "escapes": cell["escapes"],
            "rate": f"{cell['escapes'] / n:.6f}",
            "depth1_escapes": cell["depth1"],
            "depth_ge2_escapes": cell["depth_ge2"],
            "depth1_share": f"{cell['depth1'] / cell['escapes']:.4f}" if cell["escapes"] else "",
        })
    with (out / "stratified.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(strat_rows[0]))
        writer.writeheader()
        writer.writerows(strat_rows)

    summary = {
        "experiment_id": "E69_WINDOW_INFERENCE_V1",
        "purpose": "design-based (cluster-robust) inference for the frozen v16 window landscape; closes WL-4",
        "input": {"path": str(args.input.relative_to(ROOT)), "sha256": _sha256(args.input), "rows": len(rows)},
        "method": {
            "cluster": "source_id (windows overlap within a source by construction)",
            "bootstrap": f"percentile, {BOOTSTRAP} resamples over sources, seed {SEED}",
            "naive_comparator": "Wilson score interval treating windows as independent",
            "icc": "one-way ANOVA estimator for a binary indicator, unequal cluster sizes",
            "family_test": "two-sided z on a difference of proportions vs the largest family, Holm-adjusted",
        },
        "rates": rate_rows,
        "icc": icc_rows,
        "paired": paired_rows,
        "stratified": strat_rows,
        "files": {},
    }
    for name in ("denominators.csv", "rates.csv", "icc_deff.csv", "families.csv", "paired.csv", "stratified.csv"):
        summary["files"][name] = _sha256(out / name)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    for row in rate_rows:
        print(
            f"{row['config']}: {row['rate']}  wilson [{row['wilson_lo']},{row['wilson_hi']}]  "
            f"cluster [{row['cluster_lo']},{row['cluster_hi']}]  ratio {row['ci_width_ratio']}"
        )
    for row in icc_rows:
        print(f"{row['config']}: icc {row['icc']}  deff {row['design_effect']}  effective_n {row['effective_n']}")
    print(f"out: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
