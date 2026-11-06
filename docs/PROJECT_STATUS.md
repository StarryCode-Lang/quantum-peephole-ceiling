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

## Round-21 addendum (2026-10-31)

Added by the science-boost review round of 2026-10-31. No earlier row is
rewritten; `data/`, `release/`, and `docs/manuscript/` are untouched.

| Area | Round-20 statement | Round-21 measured value | Disposition |
|---|---|---|---|
| 2-qubit Clifford diameter | `D = 7` on the fragment `W2` | `W2` has **order 1,152**, an index-10 subgroup; the panel basis `{h,x,rz,cx}` generates all **11,520** and has `D = 9` | Round-20 number **withdrawn as an undercount**; `PD-1` supersedes it |
| Library length budget | "3 levels below the 2-qubit threshold" | threshold **10** vs budget **5** = **5 levels** | Corrected; `LF-1` makes the resulting price strictly positive at `m = 10` |
| Gate-set dependence | not stated | `D` is a function of the (group, generator set) pair: adding `s` grows the group 10x and moves `D` 7 -> 9; removing the reverse CX moves `D` 9 -> 11 | New concept, `PD-2`; the frozen panel uses both CX directions (18,234 / 6,348) |
| Completeness ladder | "bounded, so the main-journal route is closed" | bounded at fixed `n`, `Omega(n^2/log n)` in `n`; `L_min(3) = 7 > 5` | Main-journal gate **conditionally reopened**; the condition is upgrading `Omega` to `Theta` |
| External gates | `external_cold_start` / `real_qpu` / `release_authority` OPEN | unchanged | Still OPEN; the local substitute is now two independent implementations agreeing bit-exactly on 7 fragments |

The operational consequence: the completeness threshold is **not** a property of
the rule library. It is a property of the (library, native gate set, qubit
count) triple, and on the last axis it is unbounded.

## Round-22 addendum (2026-11-02)

Added by the science-boost review round of 2026-11-02. No earlier row is
rewritten; `data/`, `release/`, and `docs/manuscript/` are untouched.

| Area | Round-21 statement | Round-22 measured value | Disposition |
|---|---|---|---|
| Completeness-price denominator | 4.63% (L=4) / 2.06% (m=6) / 0.46% (m=7) on "the 2-qubit Clifford fragment" | those numbers are **bit-exactly reproducible but belong to a 1,152-element subgroup**; on the panel group (11,520) the L=4 price is **6.40%** and the shipped-library price is **56.07%** (subgroup: 42.37%) | Denominator corrected; E87 Part A reproduces E78 exactly, which is the proof that the numbers were right and the scope label was wrong |
| Shipped-library coverage | "length-2 rules already saturate their class, so the ladder starts at length 3" | true on the subgroup (`base == complete_L2`), **false on the panel group** (56.07 > 47.72): 8.35pp of the price is missing length-2 coverage | Reading withdrawn for the panel; marginal value of completing each length class is 8.35 / 27.44 / 13.88 / 6.40 pp (L=2/3/4/5) against 36 / 78 / 365 / 983 rules in the library |
| Length axis at the production budget | "price at `m = 10` is strictly positive" (`LF-1`, no number) | `P_len(5,5) = 0.00%`, `P_len(6,5) = 4.03%`; the length floor is measurable one instance-length past the budget | New measured point; `PR-1` registered as an accounting identity with two provable ends, **not** a theorem |
| 3-qubit diameter | "not claimed; `|C_3| = 92,897,280` uncomputed" | `D_3 in [11, 12]`: certified lower bound 11 with an exactly pinned witness, sampled ceiling 12; ball growth 1/22/274/2,565/19,680/127,925/711,213 | Computed; `D_1 = 4`, `D_2 = 9`, `D_3 in [11,12]` is too short a sequence to discriminate `Theta(n^2/log n)` from linear, so it does **not** support `LF-C1` |
| Gate-set dependence | `PD-2`: `D` depends on the (group, generator) pair | `PD-3`: adding a redundant generator can leave both the group order and `D` unchanged while **moving the distance distribution** (2q + `sdg`: `D` 9 -> 9, but d=5 layer 2,465 -> 2,926 and d=8 layer 706 -> 328); 1q + `sdg`: `D` 4 -> 3 | Thresholds are generator-set robust; **prices are not**. Every price must be reported with its generator set |
| Main-journal gate | "conditionally reopened; condition is upgrading `Omega` to `Theta`" | `2607.22248` states the maximum CNOT-complexity is **known** to be `Theta(n^2/log n)`; `1305.0810` (2013) already applied optimal <=4-input Clifford circuits as a **peephole** optimiser (~50% reduction) | Gate **closed** on prior art, not on missing evidence. PRX Quantum is the ceiling for the price law; Quantum for the certificate methodology |
| `real_qpu` gate | `OPEN` | argued to be **out of scope**: every claim is a gate-count claim, gate count is not monotone in fidelity at this scale, and the only thing a QPU run could check (equivalence) is already externally verified by QCEC on 128/128 sources | Reclassification recommended to the owner; `release/` untouched, so the verdict JSON still says `OPEN` |

The operational consequence: the completeness threshold is a property of the
(library, generator set, instance length) triple, and the **price** additionally
depends on the distance distribution, which redundant generators can move
without moving the threshold. Reporting a price without its generator set is
now a defect, not a shorthand.

## Round-23 addendum (2026-11-04)

Added by the science-boost review round of 2026-11-04. No earlier row is
rewritten; `data/`, `release/`, and `docs/manuscript/` are untouched.

| Area | Round-22 statement | Round-23 measured value | Disposition |
|---|---|---|---|
| Escape mechanism | The lead narrative was the two-regime price law | E90: of 20,002 `EXACT_ESCAPE` windows, **19,303 (96.5%) have a reducing action at the root** (content-first) and **699 (3.5%) have none** (reorder-first). The 19,303 all sit on the RAW stratum; the 1,228 greedy-fixed-point windows have **zero**. The two "axes" are therefore a partition that coincides with the two strata | Narrative re-centred on the partition; the price law becomes one section |
| Rule utilisation | "The library budget is 5, the threshold is 10" | The declared scope `e44_core_v1` has maximal source length **4** (12 / 32 / 105 / 0 rules at lengths 2 / 3 / 4 / 5); 37 of 149 rules ever fire and **2** fire as reducing; every reducing action on the panel is source length 2 | New defect **D10** (scope label, not a number error); both readings support "the budget is far below the threshold" but must be quoted separately |
| Locally irreducible class | `LF-1` was an existence theorem with one hand-built witness | E91 counts it exactly: **20,568 of 10^10** words at `(m=10, L=9)` are locally rigid on the panel group (2.057e-6); `rho(m,5)` peaks at m=7 (6.03%) and then decays geometrically with lambda ~ 0.58 | `LF-1` quantified; rigidity is a small-`m` phenomenon, so it is **not** the mechanism behind the rising price |
| `rho` vs price | Implicitly `rho >= price` | E87's pooled price at `(m=6, L=5)` is 4.03% while the pooled `rho` is **4.83%**; the ordering fails because E75's search contract admits `cost_delta = 0` actions | Third reporting rule: every price must carry its **cost-delta profile** |
| Cross-experiment alignment | Recommended in round 22 | E91 reproduces E87's two fragment denominators (80,986 / 988,046) from the geodesic-count sequence alone, bit-exactly | First implementation of the convention |
| Fragment bench instances | "240 instances, aggregate reorder share 0.710" (round 16) | E93: the 240 rows are **170 distinct circuits**; `trotter_zz` and `arithmetic_phase` do not consume their seed, so 80 rows are 10 circuits replicated 8x. Pooled share is **0.880** | Defect **D11**; family-level conclusions stand, the aggregate is corrected, the bench is not regenerated (its manifest pins the hashes) |

The operational consequence: an escape is either content-first or reorder-first,
and the two classes are not distributed evenly across the panel — they are
separated by the root stratum. Any future escape statistic must say which class
it counts, or it is averaging two different mechanisms.

## Round-24 addendum (2026-11-06)

Added by the science-boost review round of 2026-11-06. No earlier row is
rewritten; `data/`, `release/`, and `docs/manuscript/` are untouched.

| Area | Round-23 statement | Round-24 measured value | Disposition |
|---|---|---|---|
| Two-axis escape partition | window-level only: 19,303 / 699 coinciding with the root strata (E90) | **source-level: 49 / 69 content-first vs 20 / 69 reorder-first, coinciding exactly with the strata** (all 49 RAW escapes content-first, all 20 greedy-fixed-point escapes reorder-first); E52's 63 shared sources agree with zero disagreements; 19/19 self-checks (E95) | Round-23 30-day item 1 **closed**; `AX-1` is now measured at both window and source level |
| Rigidity decay constant | λ ≈ 0.58 from 7 points (m = 8..14), L = 5 only | **λ stable per window length**, far inside the registered ±0.02 criterion: panel_2q λ(2..5) = 0.900 / 0.789 / 0.689 / 0.582, panel_1q λ(2,3) = 0.750 / 0.476; curves extended to m = 20; λ(L) decreases ≈ 0.106 per level (empirical, not a theorem) (E94) | Round-23 30-day item 4 **closed** |
| Cold start | protocol exists; "local Docker available" assumed | **Docker is absent on this box** (premise corrected); a zero-third-party-dependency CPython 3.12 interpreter audits both release chains **PASS** (37/37 MATCH + prepaper chain exit 0 with 20 registered dispositions) | Round-23 30-day item 7 **closed locally**; true third-party cold start still needs a second machine (owner) |
| Reproducibility tooling | `--audit-frozen` documented as the byte-level check | the flag alone **silently did nothing** (printed help, exit 0) — `args.audit_frozen` was missing from the no-flags guard; found by the cold start attempt and fixed the same day, verified with a full `--audit-frozen --verify` run | Fixed 2026-11-06; a silent-failure mode of the M1–M9 family; no published number was ever produced through the broken path |
| Reference hub | `unified_references.md` v2.2 (2026-08-24) | v2.3: **additive section Q** ([95]–[108], the certified-era must-cite set of rounds 10–23, 1 of 16 key IDs was previously present); drift registered as **entry 20** | Audit: 20 KNOWN_DRIFT_ACCEPTED / 35,022 MATCH / ok |
| Scoop status | E92 (2026-11-04): 2608.27592 nearest competitor | E96 (2026-11-06): arXiv newest-25 sweep + 7-ID coverage check — **no scoop**; only zero-coverage hit 2611.02345 (MBUndo) is none-of-four, optional cite; 2608.27592 full text read — demarcation holds (they select inside the plateau; no reachability criterion) | Verdict current as of 2026-11-06 |
| Fragment bench (D11) | 240 rows = 170 distinct circuits; aggregate 0.710 published, 0.880 after dedup reweighting | generators consume the seed (shuffled layer order / random carry length + window start); v2 bench = 240 rows / **230 distinct** (remainder is the n=4 structural cap); E70-v2 rerun: the four untouched families reproduce their shares **bit-exactly** (0.991 / 0.982 / 0.883 / 0.715 — harness validation), `trotter_zz` 0.000 → **0.118** (the old 0 was an artifact of identical layer orderings), pooled **0.736**, gap total 4,313 and absolute-optimum count 129 unchanged | Frozen 2026-10-25 bench untouched; quote 0.736 for the repaired bench, 0.880 only as the reweighting of the broken one |
| λ decay shape | λ ≈ 0.58 (L=5) from 7 points | λ per L, m→20: panel_2q λ(2..7) = 0.900 / 0.789 / 0.689 / 0.582 / 0.456 / 0.313 — per-L stability holds (≪ ±0.02) but the **linear reading is refuted** (per-level drop accelerates beyond L=5: −0.126, −0.143; convex decay) | Empirical shape: strictly decreasing, convex in L; not a linear law |
| Second panel | E90/E95 conclusions rested on one pipeline (96 sources) | E97 (2026-11-06): **30/30 MQT Bench circuits** (16 new algorithms) equivalence-certified and censused — min reducing source length **{2: 17}, 100% = 2**; 5 reducing-firing rules all length 2; all 8 greedy fixed points have zero reducing actions (stratification coincidence replicates); 23-circuit partition 14 content-first / 9 reorder-first; ghz5/ghz10 have **no action at all** (real-circuit `LF-1` instances); E71 gate counts reproduce field-exactly | Round-23 30-day item 3 closed; one honest difference (3 circuits whose closure-witness first step is a zero-cost exchange despite reducing actions at the root — witness-strategy dependence) establishes the reporting rule: a source's axis label must name its witness strategy |

The operational consequence: the two-axis partition no longer rests on window
slices alone — the source-level table (49/20) is the number to quote for "how
many certified escapes must begin with a cost-neutral action", and the λ table
is the number to quote for "how the locally irreducible class decays" (with the
convex-decay caveat). Both are review-grade (outside the hash chain) until the
release re-pin decision. The second-panel census (E97) replicates both headline
regularities outside the original pipeline. The reference hub now carries the
certified-era must-cite set as additive section Q ([95]–[111]; drift entry 20).
