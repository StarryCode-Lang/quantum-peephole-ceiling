# Wave-6 Rerun Reconciliation — Consolidated Disposition

> **Date**: 2026-08-06 (consolidates batch reports 1–4, 2026-07-21)
> **Status**: FINAL — owner decision recorded for every rerun experiment
> **Scope**: All eleven experiments that carried 'source modified since run'
> warnings at the 2026-08-01 release freeze.

## Decision summary

Canonical data are **retained for all eleven experiments**. Every observed
canonical-vs-rerun difference is attributable to post-canonical source
changes — predominantly the strengthened commutation predicate (review
FATAL-1 repair direction) and the improved Qiskit BasisTranslator coverage —
i.e. optimizer-capability enhancements, not data errors. Rerun outputs live
in `data/v9/` (non-canonical; never cited as manuscript evidence).

| Exp | Canonical rows | Rerun rows | Machine status (v9 JSON) | Attribution (batch reports) | Disposition |
|-----|---:|---:|---|---|---|
| E12 | 568 | 560 | DIVERGED / OVERLAP_IDENTICAL | 8-row coverage delta; all 140 overlap rows value-identical | canonical retained |
| E13 | 56 | 142 | DIVERGED / OVERLAP_IDENTICAL | rerun is a superset (more families); overlap identical | canonical retained |
| E14 | 2,130 | 2,130 | DIVERGED | 38 IQP commutation/hybrid rows higher under current code; 20 canonical fidelity=0.0 artifacts now 1.0 | canonical retained + annotated |
| E15 | 994 | 986 | DIVERGED / OVERLAP_IDENTICAL | 8 IQP rows attributable to commutation strengthening | canonical retained + annotated |
| E16 | 696 | 2,130 | DIVERGED / OVERLAP_DIVERGED | rerun superset; 16 IQP rows attributable | canonical retained + annotated |
| E17 | 755 | 1,189 | DIVERGED / OVERLAP_DIVERGED | input drift from generator/topology changes; 54/54 input-identical rows reproduce exactly | canonical retained + annotated |
| E18 | 270 | 231 | DIVERGED / OVERLAP_DIVERGED | generator drift: BasisTranslator now decomposes formerly-erroring families (39 extra ok rows in rerun); 172/192 shared reductions agree | canonical retained; rerun metadata adopted |
| E19 | 10,000 | 10,000 | EQUIVALENT | value-identical (runtime only) — WCL 7.83% vs LBL 0% headline reproduces exactly | canonical confirmed |
| E20 | 1,070 | 1,070 | IDENTICAL | bit-for-bit identical incl. SHA-256 | canonical confirmed |
| E21 | 1,140 | 1,140 | DIVERGED | 40 IQP rows attributable; "time saved without reduction loss" conclusion unchanged | canonical retained + annotated |
| E25 | 66 | 66 | EQUIVALENT | value-identical (runtime only) | canonical confirmed |

## Unified IQP sensitivity statement

IQP-family commutation/hybrid reduction values quoted from canonical
E14/E15/E16/E21 are **systematically conservative** under the current
codebase (the strengthened commutation predicate finds additional legal
rewrites). Any future re-analysis using current code will report equal or
higher IQP reductions; the canonical values therefore bound the claims
from below.

## Corrected record for E18/E20

Earlier documentation (DATA_CANONICAL Known Issue 8 pre-2026-08-06 and
manuscript §7.5 item 20) stated that E18/E20 were not rerun due to
single-machine budget. That was superseded by batch 4
(`rerun_batch4.md`, completed 2026-07-21): both experiments were rerun;
E20 is bit-for-bit identical, E18 diverged with full attribution as above.

## Sources

- `docs/review/wave6/rerun_batch1.md` (E12, E13, E19)
- `docs/review/wave6/rerun_batch2.md` (E14, E15, E21)
- `docs/review/wave6/rerun_batch3.md` (E16, E17)
- `docs/review/wave6/rerun_batch4.md` (E18, E20)
- `data/v9/reconciliation_results.json` (machine-readable statuses)
