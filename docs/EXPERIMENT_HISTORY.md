# Experiment history

This is the compact history of the project's experimental evolution. It
replaces live-tree process diaries whose durable conclusions are already
captured by code, data, receipts, and Git history.

## E1-E9: the original hypothesis is refuted

The project began by testing for a phase transition in local quantum-circuit
optimization. Layer-by-layer listings repeatedly produced a flat or empty
Phase-1 action space. This refuted the original broad phase-transition story
and redirected the work toward representation-conditioned optimization.

## E10-E20: representation and compiler context

Phase-2 commutation, template matching, production compiler baselines, circuit
families, window size, connectivity, and alternate listings were added. E19
showed that wire-consecutive listing exposes reductions hidden under the
layer-by-layer representation. E20 and related compiler panels established that
prototype ceilings must not be presented as universal compiler ceilings.

## E21-E30: mechanisms, prediction, robustness

The project added a ceiling-aware routing prototype, shuffle controls,
theory-validation families, broader benchmarks, a full Phase-2b grid,
held-out family checks, multi-seed replication, and direct validation of the
corrected WCL density formula. Several early broad claims were narrowed:
stochastic optimizer results were seed- and fitness-sensitive, family-level
prediction remained underpowered, and E18 retained survivorship bias.

## E31-E37: sealed evidence and operational telemetry

E31 replaced a smoke pilot with a sealed 28,152-row factorial and independent
semantic replay. E32-E37 added timing telemetry, real-scale tests, MQT
cross-abstraction evidence, resource stress, a PyZX comparator, and energy/cost
telemetry. These packages are separately hash-bound and do not silently change
the historical canonical totals.

## v12 / E38-E41: rewrite exposure

The v12 extension introduced explicit rewrite-exposure certificates and a
certificate-guided lower-bound search. The E38 oracle passed its finite-panel
checks. E39 remained development-only. E40 found no eligible prospective input
under the frozen panel, and E41 recorded bounded scale/resource behavior.
Those availability and resource outcomes remain visible.

## v13 / E43-E45: certified rewrite landscapes

v13 froze and semantically verified a Quartz-derived rule library, implemented
the exact E44 oracle, and opened an E45 development grid. E45 stopped at its
predeclared resource gate: no configuration was eligible and the maximum
guided failure rate was 63.28125%. This is a resource-bound development result,
not evidence of zero scientific effect.

## v14: resource-safe search

v14 retained the v13 source panel and rule contract while improving lookup,
mapping, normalization, state hashing, candidate generation, beam retention,
deadline propagation, and exact escape search. The screening gate moved from
0/18 to 18/18 eligible configurations. The compact exact panel produced 93
exact certificates and 35 resource-truncated cells. The complementary IDA*
panel classified all 128 inputs with no resource or replay failures.

## v15: classification-complete integration and window-local profiles

v15 did not rerun any frozen search. The compact exact panel and the IDA*
panel were integrated into one classification-complete statement: all 128
fixed-panel sources are classified (63 exact escapes with exact minimum
escape depth, 65 exact local optima). Sixty-four compact-complete local
optima and 29 escapes keep enumerated certificates; one truncated local
optimum inherits a complete derived certificate from the IDA* proof; the 34
truncated escape cells keep exact escape depths with witness-bounded
best-cost and barrier values. Every derived claim is fail-closed: package
identity checks, root-state hash rebuilds, and witness replays all pass.

E46 added the first position-resolved certified landscape layer: for every
fixed-panel root listing, contiguous windows of 8 and 16 gates were searched
exactly at horizons 2 and 3 with the E45 engine and rule scope. The panel
ran 76,236 window searches with zero resource truncations and, after the
v16 engine repair and re-pin, 39,572 certified window escapes (39,474 in the
superseded v15 run). The panel has two strata and the escape rates are
reported per stratum: on the 23 greedy fixed-point roots that have 16-gate
windows, 191 of 481 windows (39.71 percent) hide a certified escape of depth
at least two, and depth-one escapes are exactly zero; on the 50 roots whose
normalised listing exceeds the baseline gate budget, 10,565 of 18,274
windows (57.81 percent) escape, but 10,339 of those are depth one. The
earlier "37.2 percent on 123 greedy roots" reading mixed one stratum's
denominator with the other stratum's qualifier and is withdrawn
(`docs/review/science_boost/2026-10-26_innovation_scan.md` §2.2).
Only the first escape certificate per (source, width, horizon) is stored; the
deterministic runner regenerates the complete witness set on demand.

## Round 18 (2026-10-28): completeness price curve and multiplicity control

Three review-grade panels were added; `data/`, `release/`, and
`docs/manuscript/` were not touched. E75 parameterises the rule library by
maximal source-pattern length on fragments where the absolute optimum is
enumerable, and turns E73's single 30.25% point into a curve: on the 2-qubit
Clifford fragment the gap is unchanged by adding every length-2 rule
(exactly 0.00 gain — the pair rule already saturates that class), falls to
9.12% with all length-3 patterns, and reaches exactly 0.00% with all
length-4 patterns; on the 1-qubit Clifford fragment the completeness
threshold is `L* = 4` against listing length `m = 8`, and below the
threshold there are two regimes with no middle — P(2) rises with instance
length while P(3) saturates and P(4) vanishes. E75 also found a
measurement defect in E73's unitary-class key: the legacy argmax-pivot key
splits tied-pivot Clifford unitaries across classes; the fixed
phase-invariant key merges 12 classes to 8 on the 1-qubit fragment, and the
E73 30.25% figure reproduces exactly under the legacy key, so the earlier
result stands (regression-gated in the E75 summary).

E77 applies Fisher exact tests per family and Holm-Bonferroni across
families to E72's per-family content-class residual. The blanket claim that
the residual concentrates in structured families is withdrawn: on the
greedy fixed-point stratum, IQP and Oracle carry significantly more residual
than the stratum average and RandomClifford and UCCSD significantly less —
the defensible claim is family-specific. E76 retargeted the fielded
literature and ecosystem scan at the price-of-completeness subject
(24 fielded arXiv queries, 246 unique records, 0 failed queries) and added
references [129]-[133] to the reference-additions register. The theory
consolidation — Theorem 5 (order/content decidability frontier) and
Theorem 6 (local-rigidity lower bound on the price) — is
`docs/theory/decidability_frontier_2026-10-28.md`; the mapping of nine
silent-failure mechanisms to fail-closed certificate fields is
`docs/review/certificate_failure_mode_map_2026-10-28.md`.

## Superseded interpretations

- The original phase-transition hypothesis is refuted by the data.
- A prototype action-space ceiling is not a universal optimizer ceiling.
- The early E31 smoke pilot is historical support; the sealed formal panel is
  the controlling E31 evidence.
- v13's resource failure remains the baseline; v14 does not rewrite it.
- v14's unclassified resource-truncated cells remain the enumerated-certificate
  boundary; v15 replaces the unclassified outcomes with derived and bounded
  evidence without rewriting the v14 receipts.
- Passing engineering verifiers does not establish paper readiness or external
  reproduction.

## Current source of truth

Use `docs/PROJECT_STATUS.md` for the current disposition,
`data/DATA_CANONICAL.md` for canonical-data policy, and machine-readable
receipts under `release/` and `data/v12`-`data/v15` for exact claims. Removed
process notes remain available in Git history; the pre-paper restore capsules
were retired on 2026-10-11 as unpinned, git-redundant bulk.
