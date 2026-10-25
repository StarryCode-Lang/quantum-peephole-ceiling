# E64 — Escape-geometry atlas (2026-10-25)

**Authority**: review-grade evidence package, outside `release/release_manifest.json`.
**Contract**: frozen inputs only (`data/v15/e46_window_landscape`, `data/v15/e45_landscape_integration`,
`data/v14/e45_full_development`, `data/v14/e45_idastar_escape`, plus the E52 summary for the
family join); no search re-run; generator `scripts/e64_escape_geometry_atlas.py` is
byte-deterministic (fixed seed 20261025, no wall-clock timestamps).

## 1. Escape-rate atlas — one table, explicit denominators

All 76,236 window searches
(39,474 certified escapes) are reconciled in
`escape_rate_atlas.csv` (root_kind × width × horizon, pooled rows included); the named
slices quoted in the manuscript, the readiness verdict and the earlier audit are in
`escape_rate_slices.csv`.

| Slice | Escapes / windows | Rate | Status |
|---|---|---|---|
| Manuscript §6: greedy roots, w16, h3, depth ≥ 2 | 179/481 = 0.3721 | **0.372** | reproduced exactly |
| Verdict: all sources, w8 h2 | 9071/19363 = 0.4685 | 0.4685 | reproduced exactly |
| Verdict: all sources, w8 h3 | 9234/19363 = 0.4769 | 0.4769 | reproduced exactly |
| Verdict: all sources, w16 h2 | 10477/18755 = 0.5586 | 0.5586 | reproduced exactly |
| Verdict: all sources, w16 h3 | 10692/18755 = 0.5701 | 0.5701 | reproduced exactly |
| Audit anchor: GREEDY w8 (h pooled) | 237/1494 = 0.1586 | 0.159 | reproduced |
| Audit anchor: GREEDY w16 (h pooled) | 309/962 = 0.3212 | 0.321 | reproduced |
| Audit anchor: RAW w8 (h pooled) | 18068/37232 = 0.4853 | 0.485 | reproduced |
| Audit anchor: RAW w16 (h pooled) | 20860/36548 = 0.5708 | 0.571 | reproduced |
| GREEDY h2 (widths pooled) | 229/1228 = 0.1865 | 0.1865 | new |
| RAW h2 (widths pooled) | 19319/36890 = 0.5237 | 0.5237 | new |

Denominator structure: 78 greedy-root sources and
50 raw-root sources form the root universe, of which
44 and 50 carry at least one window;
34 further sources have greedy roots shorter than the 8-gate
minimum window and are absent from `window_results.csv` entirely (they appear only as
zero-window rows in `input_summaries.csv`).  Every rate above states its own n/N, so the
manuscript slice (greedy w16 h3 only) and the verdict slice (all sources per config) are no
longer confusable.

**Mismatch flag.** The same manuscript sentence that reports 179/481 also says "the 123
greedy fixed-point roots" and "the five raw-listing roots that exceed the baseline gate
budget".  The frozen data say **78** greedy-root
sources and **50** raw-root sources (root lengths
0–66 vs
82–12,422 gates), and
depth-one escapes occur on **49 of the 50** raw roots (38,606 depth-1
escapes vs 868 depth-≥2 escapes).  179/481 = 37.2% itself is exact;
the surrounding root counts are not consistent with the frozen panel and should be
corrected or re-derived before submission.

## 2. ">80 gates ⇒ depth-1 escapes": threshold or curve?

Root lengths in the panel are bimodal by construction: greedy roots run
0–66 gates, raw
roots 82–12,422 gates
(the raw kind is *defined* by exceeding the 80-gate budget).  Depth-1 window escapes occur on
49/50 raw roots (min length 82); the only
counterexample is
a QFT source at 148 gates with zero
window escapes of any depth.  No root between
67 and 81 gates
exists, so the data cannot resolve an onset inside that gap: the signal is **consistent with
a threshold law at the budget boundary but confounded with the root_kind definition**, and
it has one counterexample.  Per-source early/middle/late tercile rates of the listing are
0.3799 / 0.3571 / 0.3404 (w8 h2 mean across sources; w16 h2:
0.6162 / 0.5764 / 0.5339):
escape probability declines only mildly along the listing, i.e. the transition is in the
*root*, not in the window position.

## 3. Escape geometry

* Depth distribution: {"1": 38606, "2": 490, "3": 378} —
  depth-1 dominates with 97.8% of escapes.
* Depth ≥ 2 rows: 868 of 39,474, concentrated in
  IQP (448), QuantumWalk (182), UCCSD_inspired (87), Grover (86), RandomClifford (65).
* Depth split of the top families (d1/d2/d3): QuantumWalk
  7698/32/150,
  Grover 806/0/86,
  IQP 0/394/54,
  UCCSD_inspired 1908/0/87,
  RandomClifford 0/64/1.
  Deep escapes are a QuantumWalk/Grover/UCCSD phenomenon; IQP supplies breadth at depth 2.
* The 242 stored first-escape witnesses reduce via
  pair_v1 in 231 cases and via
  quartz_v1 in 11; the multi-step paths open with
  structural_exchange_v1 / quartz_v1 neutral moves and close with pair_v1 — the
  exchange-then-reduce mechanism the whole-listing greedy pass cannot see.
* Window gain distribution: {"1": 2423, "2": 14999, "3": 12080, "4": 4824, "5": 4946, "6": 202}
  (mode at gains 2–3; gains up to 6 exist).  Barrier height is 0 in
  99.83% of escapes.

## 4. Empirical branching-factor law

Mean states_seen per window search: w8 h2 = 16.3812, w8 h3 = 39.7148,
w16 h2 = 53.2114, w16 h3 = 220.6489; max 819
(VQE, w16 h3).
Fitting through the two horizons per width: states_seen ≈ c·b^h with effective growth factor
b ≈ 2.42 (w8) and b ≈ 4.15 (w16) — one extra horizon multiplies the mean search by
~2.4 on narrow windows and ~4.1 on wide ones, while doubling the width multiplies it by
~3.2 (h2) to ~5.6 (h3): width and horizon act at comparable multiplicative scale.  A joint
power law ln S = α + β·ln w + γ·h over all 76,236 searches gives β = 1.7256,
γ = 1.0282 (R² = 0.425187) — the modest R² reflects the wide per-source dispersion,
so the per-config means, not the global fit, are the usable calibration.

Implication for exactifying the bounded cells: per-level cost scales with the *root
branching* b (IDA* first-iteration states_seen − 1), and the tracker shows
26 of the 34 bounded cells have b ≤ 250 (cheap),
3 sit in the 250 < b ≤ 1000 band (HaarRandom nq=4 ×3 (b = 527–528)),
and the expensive tail is exactly the 5 QuantumWalk large-layout cells
(QuantumWalk nq=8 ×2 (7,514 gates, b = 1682–1682); QuantumWalk nq=9 ×3 (12,422 gates, b = 2677–2677)).

## 5. Window escape → whole-listing escape

| Scope | escape∩win | escape∩¬win | optimum∩win | optimum∩¬win | Fisher p |
|---|---|---|---|---|---|
| all 128 sources | 62 | 1 | 0 | 65 | 2.80e-36 |
| windowed 94 sources | 62 | 0 | 0 | 32 | 7.62e-26 |

Window-escape presence is a **near-perfect predictor** of the whole-listing verdict:
62/63 E45 escapes have a window escape and
0/65 optima have any.  On sources that actually
carry windows the separation is perfect (62 vs 0).  The single discordant escape is
e39:02163c542c157c61ed7195186ff2f5485f3042166bff997c922c173ac06103d0 (Oracle, nq=4), whose greedy root
collapsed below the 8-gate window minimum, so no window could fire.  Causality is one-way
compatible: a local window escape is *necessary* (given a nondegenerate listing) for a
whole-listing escape at the same rule scope and horizon budget.

## 6. The 34 bounded cells: distance to exact

`bounded_cell_exactification_tracker.csv` joins `classification_complete.csv`
(tier CLASSIFICATION_EXACT_EXTRAS_BOUNDED), the compact certificates (states explored
before budget, blocker: 19 time_budget /
15 state_budget) and the IDA* certificates
(root branching b = states_seen − 1; witness bound best_cost).

* Cost classes (cheap: root branching b <= 250; moderate: 250 < b <= 1000; expensive: b > 1000 (b = IDA* first-iteration states_seen - 1)):
  {"cheap": 26, "expensive": 5, "moderate": 3} over 34 cells.
* Statistically-isomorphic groups (≥ 2 bounded cells sharing family and qubit count):
  12 groups; 11 of them share byte-identical IDA* statistics,
  6 also share identical compact expansions,
  and the fully byte-identical set (IDA* *and* compact counters) is
  QAOA|nq4 (n=3, b=76).
  One IDA* proof rerun of a shared tree clears up to 4 cells at once.
* Cheapest cells: the state_budget groups with identical IDA* trees (smallest root
  branching first) — every bounded cell already carries a witness bound with gain ≥ 1
  (15 of the 34 cells gain ≥ 2), so a single bounded run each converts a
  witness-bounded extra into an enumerated exact value.
* Expensive tail: QuantumWalk nq=8 ×2 (7,514 gates, b = 1682–1682); QuantumWalk nq=9 ×3 (12,422 gates, b = 2677–2677).

## 7. Tier/family gains with cluster bootstrap

Resampling sources (n = 128, 10,000 resamples, seed 20261025),
the per-source gain distribution {"0": 65, "1": 22, "2": 25, "3": 6, "4": 1, "6": 9} has overall mean
1.156250 (95% CI 0.882812–1.460938).
`tier_family_gain_bootstrap.csv` carries all tier and family rows with their CIs.  The tier
split is not uniform by construction: bounded-tier cells (n = 34) carry small constant gains
still to be exactified while COMPACT_COMPLETE_ENUMERATED cells include the gain-6 sources,
so per-tier means differ structurally — the CIs quantify the source-level sampling noise
behind the manuscript's per-family claims.

## 8. Determinism and receipt

`receipt.json` pins every input and output by SHA-256, the script itself, the bootstrap
seed (20261025) and the interpreter version.  `generated_at` is the fixed package
instant 2026-10-25T00:00:00Z; re-running the script on the pinned inputs reproduces every file
byte-for-byte.
