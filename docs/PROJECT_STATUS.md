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
| Window-local certified landscape | Did not exist | E46: 76,236 window searches over the fixed panel, 0 truncations, 39,474 certified window escapes, first-escape witnesses stored | **New v15 evidence layer** |
| Independent cold start | Protocol exists; full independent extraction was not completed | Sparse package verification is recorded; clean non-author execution remains pending | **External/open** |
| Real QPU validation | Protocol prepared without credentials or device run | No real-device result is claimed | **External/open** |
| Enumerated exact landscape quantities | Required all 128 selected cells to finish compact enumeration | Classification is complete; 34 long-listing escape cells keep witness-bounded best-cost and barrier values instead of enumerated ones | **Open (bounded form)** |

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
- detailed execution record: `docs/review/v14_execution_status_2026-09-07.md`

The repository remains `NOT_READY_FOR_PAPER` under the current v15 verdict.
That label does not negate the completed engineering gates listed above.
