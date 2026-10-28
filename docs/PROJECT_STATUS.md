# Project status and optimization audit

**Snapshot:** 2026-10-11

**Scope:** implementation, evidence, repository quality, and public showcase.

**Excluded by project decision:** paper writing and GitHub Actions.

This page compares the active repository with the accumulated optimization
plans and evidence records. A row is closed when its declared verifier and
scope pass. A large improvement does not erase the earlier receipt; the old
result remains the baseline that makes the improvement measurable.

## Optimization status

| Area | Earlier state | Current evidence | Disposition |
|---|---|---|---|
| Frozen rewrite library | External Quartz rules needed provenance and semantic validation | 1,474 safe directed rules are source-pinned and independently checked; two underdetermined reverse directions remain excluded | **Closed for the declared rule library** |
| E44 exact oracle | Exact finite-panel quantities required executable proof obligations | 512 cases / 1,024 model rows pass theorem, solver, bound, replay, and determinism checks | **Closed for the E44 oracle panel** |
| E45 screening resource gate | v13: 0/18 eligible; maximum guided failure rate 63.28125% | v14: 18/18 eligible; selected rate 3.90625%; 13,824 rows and zero semantic failures | **Large improvement; optimization item closed** |
| Selected finite-horizon search | No complete selected-configuration exact panel | 93/128 exact certificates and 35/128 explicit resource truncations | **Improved, still incomplete** |
| Escape-depth classification | Compact search retained a resource boundary | IDA*: 63 exact escapes + 65 exact H-local optima; 0 resource bounds and 0 replay failures | **Closed for the declared 128-input panel** |
| Determinism and failure handling | High-branching enumeration could overrun late checks | Stable action ordering, byte-stable certificates, deadline propagation, and fail-closed statuses are regression tested | **Closed** |
| Historical E1-E37 evidence | Multiple audit waves and receipts | Canonical and sealed packages remain hash-bound; the 592-metric ledger keeps PASS/PARTIAL/FAIL/EXTERNAL/NA separate | **Preserved; no rerun justified by v14** |
| E45 classification bookkeeping | v14 left 35/128 compact cells truncated with no derived claims | v15 integration: 128/128 classified; 63 exact escapes with exact minimum depth; 65 exact local optima; 94 exact best costs; 34 witness-bounded extras; 0 replay failures | **Closed for classification (v15)** |
| Window-local certified landscape | Did not exist | E46: 76,236 window searches over the fixed panel, 0 truncations, 39,474 certified window escapes (v15 run), first-escape witnesses stored | **New v15 evidence layer; superseded by v16** |
| Repository footprint | Restore capsules 173 MB, vendored tool checkout 365 MB, cache and garbage objects | Capsules retired (unpinned, git-redundant), checkout removed, caches purged; all pinned evidence untouched | **Closed (v15 cleanup; see `docs/review/v15_cleanup_2026-10-11.md`)** |
| Independent cold start | Protocol exists; full independent extraction was not completed | Sparse package verification is recorded; clean non-author execution remains pending | **External/open** |
| Real QPU validation | Protocol prepared without credentials or device run | No real-device result is claimed | **External/open** |
| Enumerated exact landscape quantities | Required all 128 selected cells to finish compact enumeration | Classification is complete; 34 long-listing escape cells keep witness-bounded `best_cost_at_h3` and barrier values instead of enumerated ones | **Open (bounded form)** |

All landscape costs in this page are **horizon-relative**: `best_cost_at_h3` means the
exact best cost reachable within `h = 3` actions under rule scope `e44_core_v1`. It is
not an unconstrained optimum, and it is not a claim of gate-count optimality. A
search-free commutation closure beats it on 60/128 sources; 98.2% of that gain is
single-qubit gate merging (2026-10-24 scan, §2.1).

## What no longer needs another optimization pass

The v14 screening bottleneck, full-panel escape-depth classification,
certificate determinism, local witness replay, and deadline propagation all
meet their declared engineering gates. Reopening them without a new hypothesis
or a failing regression would add run history without adding evidence.

Historical E1-E37 results also do not need routine reruns. They are preserved as
frozen evidence and should be revisited only when a new scientific question
requires a versioned extension.

## Remaining work

The v15 integration closed the classification gap: no fixed-panel source is
unclassified. The remaining scientific gap is narrower than in v14: 34
long-listing escape cells carry witness-bounded best-cost and barrier values
rather than enumerated ones. Closing that gap requires a new resource or
algorithmic plan and a new versioned evidence package; the v14 results must
remain frozen. Open extensions that would change the science rather than the
search budget include full-rule-scope (1,474-rule) panels and wire-consecutive
window profiles. Independent cold-start reproduction and real-QPU execution
require external resources or authorization. These are kept separate from
local engineering readiness.

## Evidence pointers

- v13 baseline: `docs/review/v13_stage5_e45_receipt.json`
- v14 screening: `data/v14/e45_development_grid/receipt.json`
- v14 exact development: `data/v14/e45_full_development/receipt.json`
- v14 IDA*: `data/v14/e45_idastar_escape/receipt.json`
- v14 verdict: `release/v14_readiness_verdict.json`
- v15 landscape integration: `data/v15/e45_landscape_integration/receipt.json`
- v15 E46 window landscape: `data/v15/e46_window_landscape/receipt.json`
- v15 verdict: `release/v15_readiness_verdict.json`
- v15 cleanup record: `docs/review/v15_cleanup_2026-10-11.md`
- detailed execution record: `docs/review/v14_execution_status_2026-09-07.md`

The repository remains `NOT_READY_FOR_PAPER` under the current v16 verdict
(`release/v16_readiness_verdict.json`, as_of 2026-10-25). That label does not
negate the completed engineering gates listed above.

## v16 addendum (2026-10-25 → 2026-10-27)

Added by the science-boost review round of 2026-10-27. This section does not
rewrite any earlier row; it records what changed after the engine
successor-generation repair and the v16 re-pin.

| Area | v15 statement | v16 measured value | Disposition |
|---|---|---|---|
| Landscape quantities | 94 exact; 34 witness-bounded | **93 exact; 34 witness-bounded; 1 resource-bounded** | Re-pinned; v15 numbers remain the historical baseline |
| E45 classification | 63 escapes / 65 local optima | **69 escapes / 58 local optima**, 127 classified + 1 resource tier | Re-pinned |
| E46 window panel | 39,474 escapes | **39,572 escapes**, 0 truncations | Re-pinned |
| Window escape rates | "37.2% of 16-gate windows on 123 greedy roots" | **two strata**: 39.71% (191/481 windows, 23 greedy roots, depth-one escapes 0) vs 57.81% (10,565/18,274 windows, 50 raw over-budget roots, 97.9% depth-one) | **Earlier single-rate statement withdrawn**; rates must be reported per stratum |
| Span criterion | — | E72: a search-free O(m·w) criterion predicts all 76,236 window outcomes with **0 false positives** and an exact first-escape depth on **38,006/38,008** rows | New evidence layer, `docs/review/science_boost/2026-10-27_span_law/` |
| Content class | — | E72 recall is 97.0% on raw roots but **32.8% on greedy fixed points**: 398/592 escapes are rule-library content, not commutation | New open problem G4 |
| Rule-library completeness | — | E73: of 1,474 Quartz rules only **14 are single-qubit**, and no single-qubit source pattern has length 3; on the 2-qubit Clifford fragment **30.25% of reducible listings cannot reach the absolute optimum** | New measured caveat on every "certified optimum" claim |

The operational consequence: `best_cost_at_h3` is horizon-relative *and*
library-relative, and the library-relative gap now has a number (30.25% at
2 qubits, 4 gates) rather than a caveat. Full review:
`docs/review/science_boost/2026-10-27_innovation_scan.md`.

## Round-18 addendum (2026-10-28)

Added by the science-boost review round of 2026-10-28. No earlier row is
rewritten; `data/`, `release/`, and `docs/manuscript/` are untouched.

| Area | Round-17 statement | Round-18 measured value | Disposition |
|---|---|---|---|
| Content-class residual | E72: recall splits by stratum (97.0% raw / 32.8% greedy); residual read as a rule-library content class | E77 (Fisher exact per family + Holm-Bonferroni): the blanket "residual concentrates in structured families" claim is **not supported** — on greedy fixed points IQP and Oracle carry significantly *more* residual than the stratum average, RandomClifford and UCCSD significantly *less* | Claim narrowed to family-specific; `docs/review/science_boost/2026-10-28_span_family_holm/` |
| Completeness price | E73: single point, 30.25% at 2 qubits / 4 gates | E75 curve on enumerable fragments: the price is **thresholded, not diffuse** — every length-2 rule buys exactly 0.00 (pair rule already saturates that class); +all length-3 → 9.12%; +all length-4 → 0.00% (2-qubit fragment). 1-qubit Clifford: `L* = 4 ≪ m = 8`, with two regimes and no middle (P(2) rises with instance length, P(3) saturates, P(4) = 0) | New measured caveat in threshold form; `docs/review/science_boost/2026-10-28_completeness_price/` |
| Theory consolidation | Theorems 1/4 scattered across two theory documents | Theorem 5 (order/content decidability frontier) and Theorem 6 (local-rigidity lower bound on the price) stated and proved in one place, with their E72/E75 empirical support and explicit non-claims | `docs/theory/decidability_frontier_2026-10-28.md` |
| Certificate semantics | Per-action witness + replay + engine hash chain justified internally | Nine silent-failure mechanisms (M1-M9) each pinned to a fail-closed certificate field, with the experiment that actually caught each one (three of them were this project's own defects) | `docs/review/certificate_failure_mode_map_2026-10-28.md` |
| Measurement integrity | — | E75 found and fixed a **unitary-class key defect**: the legacy argmax pivot key splits tied-pivot Clifford unitaries across classes (1-qubit: 12 classes → 8; measured price 60.21% → 59.25%); E73's 30.25% reproduces exactly under the legacy key | Regression-gated: `legacy_key_reproduces_30_25pct: PASS` in the E75 summary |
