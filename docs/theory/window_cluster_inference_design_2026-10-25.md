# Design: source-clustered inference for the window-landscape panel (WL-4)

**Status**: design document, review grade (2026-10-25 execution round).
Registers the statistical contract that any window-level inferential claim
must satisfy before it enters the manuscript. Companion data: the frozen and
v16 E46 panels (`window_results.csv`, 76,236 rows, 128 sources × 4 configs).

## 1. The dependency problem

The 76,236 window searches are **not independent samples**: windows of one
source share the source's root listing, family, qubit count, and gate
density, and adjacent windows overlap by construction (stride 1 up to the
1,024-window cap). Treating rows as i.i.d. inflates the effective sample
size by roughly the within-source correlation factor and yields
anti-conservative p-values and intervals. The v15 verdict-era claim set
uses window-level counts (e.g. escape rates per config, the
window→whole-listing separation test) that must therefore be re-derived
under a design-based scheme.

## 2. Contract: cluster = source, config strata fixed

1. **Primary sampling units**: the 128 sources. All inferential statements
   (means, rates, differences, regression coefficients) are computed with
   the source as the cluster; window rows are repeated measures within a
   cluster.
2. **Estimator**: cluster-robust (design-based) estimates over the 128
   clusters, with per-cluster pre-aggregation: for each (source, config)
   compute the source-level escape rate $r_{s,c}$ (window count is the
   denominator within source), then estimate the panel quantity as the
   source-weighted mean $\hat\mu_c = \frac{1}{128}\sum_s r_{s,c}$ with the
   cluster variance
   $\widehat{\mathrm{Var}}(\hat\mu_c) = \frac{1}{128^2}\sum_s (r_{s,c} - \hat\mu_c)^2$.
   Finite-population correction is not applied (the panel is the population
   for descriptive claims; for superpopulation claims the uncorrected form
   is the conservative one).
3. **Comparisons between configs** (e.g. w8 vs w16 escape rates) use paired
   differences at the source level: $d_s = r_{s,c_1} - r_{s,c_2}$, the
   paired t / sign-test over 128 clusters — no window-level test is
   admissible.
4. **The window→whole-listing separation** (E64: 2×2 = [[62,1],[0,65]],
   Fisher p = 2.8e-36) is a *source-level* table already; its inference is
   valid as-is because the units are sources. This is recorded so the
   result is not re-litigated at the wrong level.
5. **Family-level claims**: families are post-hoc groupings of a
   convenience panel; any family contrast is reported descriptively with
   family as the cluster (15 clusters) and is labelled exploratory — no
   confirmatory family-level p-values.
6. **Multiplicity**: the pre-registered confirmatory set is fixed in
   advance — (i) per-config escape rate = 0 vs > 0, (ii) w8-h3 vs w16-h3
   paired difference, (iii) greedy vs raw root-kind difference. All other
   contrasts carry Holm correction across the exploratory family actually
   reported.
7. **Denominator reconciliation**: every headline percentage must name its
   denominator (window rows 76,236 vs h2-slice 229/1228-style slices vs
   source-level 128) — the E64 reconciliation table is the template; the
   v16 integration reproduces it under the same contract.

## 3. What changes for v16

The v16 E46 panel is the corrected-engine rerun of the same 128 sources
with identical window sampling (verified: 76,236 rows, 0 truncations), so
the contract applies unchanged; the v15/v16 delta (39,474 → 39,572 escape
rows) is itself a paired source-level comparison under item 3.

## 4. Implementation path

A single analysis script reads `window_results.csv` + `input_summaries.csv`,
emits the per-source aggregation table, the confirmatory results with exact
cluster variances, and the denominator reconciliation table. No new data
collection is needed; frozen and v16 panels are both sufficient.
**Executed 2026-10-26** as `scripts/e69_window_inference.py` (round 15),
which additionally quantifies the design effect (ICC 0.57–0.67, DEFF
134–153: the naive window-level interval is 17–18× too narrow) and surfaces
the D3 root-population confound (73,780/76,236 windows sit on unoptimized
raw roots; depth-1 escape mixing), both registered in
`docs/review/science_boost/2026-10-26_window_inference/`.

## 5. Non-goals

- No claim that 128 convenience sources are a random sample of any
  superpopulation — the design-based variance quantifies panel-internal
  uncertainty only.
- No window-level resampling (bootstrap over windows is invalid under
  within-source dependence; the cluster bootstrap over 128 sources, as
  used in E64 for the gain CI, remains the only admissible resampling).
