# 2026-10-25 Engine Successor Fix — Pilot Re-Certification (REVIEW GRADE)

**Status: review-grade evidence, OUTSIDE the release hash chain.** Nothing in
`data/` (frozen), `docs/manuscript/`, or `release/` was modified by this
package. Frozen v14/v15 numbers remain the released record until a successor
panel is certified.

## Defect

`src/optimisation/certified_landscape.py::iter_legal_actions` overwrote the
per-rule action list on every matching listing location ("last location
wins"): for any Quartz rule whose source signature matched at >= 2 locations,
only the last location's actions were emitted; earlier locations were
silently dropped. The complete engine `legal_actions` was unaffected. All
frozen v14/v15 certificates produced by
`search_landscape_horizons_compact` / `search_escape_idastar` used the buggy
generator (both call `iter_legal_actions`); the audit verified live on a
synthetic 4-gate state (rule `quartz_v1:9_2`, scope `e44_core_v1`):
`legal_actions` 3 actions vs `iter_legal_actions` 2.

Fix (minimal diff): accumulate actions across **all** locations of a rule,
then apply the single final `sort_key` sort — the documented rule-by-rule,
sorted-within-rule order is preserved; `_check_deadline` stays per location.

## Contents

| File | What it is |
| --- | --- |
| `pilot_cells.jsonl` | Full screening evidence: all 78 panel cells with `baseline_cost <= 70`, frozen vs corrected metrics, wall times, states seen, replay statuses, per-cell verdicts. |
| `comparison.csv` | The 13-cell pilot set: 6 false H-local-optima + 5 wrong escape quantities + 2 agreeing controls, frozen vs corrected side by side. |
| `pilot_results.json` | Machine-readable contract: defect, fix, SHA-256-pinned inputs (rule library, frozen certificate files, classification CSV), engine source hashes, screening totals, full 128-cell re-run estimate. |
| `build_package.py` | Deterministic builder that regenerates `comparison.csv` + `pilot_results.json` from `pilot_cells.jsonl`. |
| `rerun_all_cells.py` | Full 128-cell driver: re-runs BOTH engines on every panel root with the fixed engine at the exact frozen v14 budgets/configs, hash-checked root states, incremental (crash-safe) JSONL output, resume-safe, per-cell engine-source hashes. |
| `run_with_stability.py` | Resilience wrapper: waits for the engine source to be hash-stable (3 min), prunes cells produced under other engine versions, gates on free RAM (>= 6 GB, needed by the largest 12k-gate cells at the frozen 30 s budget), resumes until 128 cells share one engine hash. |
| `full_cells.jsonl` | Per-cell evidence for all 128 cells (frozen vs corrected certificates, wall times, states seen, witness replays, producing engine-source hashes). |
| `full_cells_first_pass.jsonl` | Archived first pass (56 cells) from before the concurrent engine-edit disruption; superseded by `full_cells.jsonl`, retained for provenance. |
| `build_full_package.py` | Deterministic builder that regenerates `full_comparison.csv` + `full_results.json` + `determinism.json` + `receipt.json` from `full_cells.jsonl` + `determinism_cells.jsonl`; validates all 78 screened cells against the pilot. |
| `full_comparison.csv` | 128 rows: frozen verdict/best cost/escape depth vs corrected, changed flag, change_type, states seen, wall times. |
| `full_results.json` | Aggregates: change_type counts, corrected headline numbers, every changed best cost (old -> new), flagged cells, wall-time totals. |
| `determinism.json` | Re-run of a deterministic 10-cell subsample (5 changed + 5 agreeing); all byte-identical verdict/best_cost/escape_depth. |
| `determinism_cells.jsonl` | Second-run per-cell records backing `determinism.json`. |
| `receipt.json` | Package-wide SHA-256 receipt (pilot artifacts kept, full re-certification artifacts added) plus engine/input hashes. |

## Method

- Root states rebuilt via
  `experiments.e46_window_landscape.run.load_root_states` (hash-checked
  against the frozen compact certificates).
- Engines: the **fixed** `search_landscape_horizons_compact` (horizon 3,
  state budget 200,000, 30 s cell budget) and `search_escape_idastar`
  (30 s cell budget), scope `e44_core_v1`, rule library
  `data/v13/e43_quartz_rule_import/generation_a/rule_library.json`
  (sha256 `fe9876de0d9b75afc458bbdcf806bdc797da0369ac5cd595cb4bf7a0232f3295`)
  — identical to `data/v14/e45_full_development` and
  `data/v14/e45_idastar_escape`.
- Screening scope: every panel cell with `baseline_cost <= 70` (78 cells),
  matching the audit scope. Every non-empty corrected witness was replayed
  (`replay_actions`): all `REPLAY_PASS`, zero resource truncations.

## Result (matches the prior audit exactly)

- **6 false H-local-optima** — frozen `EXACT_H_LOCAL_OPTIMUM` best 10, true
  best 8, escape depth 3 (`e39:0ed63ca1…`, `e39:7130c27a…`, `e39:8a0f6aa4…`,
  `e39:a8db7c39…`, `e39:b81e1fce…`, `e39:d666adb1…`).
- **5 wrong escape quantities** — `e39:dce7762d…` best 21 -> 20;
  `e39:e00e580e…` best 52 -> 51; `e39:06114511…`, `e39:0ea94971…`,
  `e39:1af7528f…` escape depth 3 -> 2 (best cost unchanged).
- **67/78 cells agree** with frozen, including both controls
  (`e39:ec754f7e…` H-local control, `e39:2d71c39b…` escape control).

## Wall times and full re-run estimate

- 13-cell pilot set: ~7.5 s total (compact ~6.6 s + IDA* ~0.9 s); slowest
  cell 2.71 s (`e39:ec754f7e…` compact).
- 78-cell screen: compact 8.77 s + IDA* 1.58 s = **10.35 s** (frozen same
  cells: 4.56 s + 1.84 s; corrected/frozen ratio ~1.92 compact, ~0.86 IDA*).
- **Full 128-cell re-run estimate: ~18-22 min** (remaining 50 big cells are
  dominated by compact runs already pinned at the 30 s fail-closed budget —
  7 of 50 at the cap in frozen — which the corrected engine cannot exceed;
  small cells are milliseconds). Absolute worst case if *every* remaining
  compact and IDA* cell exhausts its 30 s budget: ~50 min.

## Engine identity (new provenance)

`src/provenance.py::engine_source_hashes` (new function;
`DEFAULT_SOURCE_FILES` deliberately unchanged) pins:

```
src/optimisation/certified_landscape.py  9119a470bd2fc2e4feb4d403e999133722d2424d09e75609895cc0ec41b93b93
src/optimisation/quartz_rule_import.py   bb51a4a891ff27cd55afab998674479668dba85ee24e312dcfa4d4bdc5ee7404
src/optimisation/rewrite_exposure.py     88a1b9a9e7893133f490d9d9ef218de613456f3e9d1f052792fd7c1a3a295d28
```

Any successor receipts should embed these hashes so a verifier can confirm
the engine that produced the data. `scripts/reproduce_all.py --verify` was
run before and after the fix: byte-identical output (modulo timestamps),
exit 0 both times.

## Regression protection

`tests/test_v13_certified_landscape.py` adds: (1) a regression test on the
multi-location `quartz_v1:9_2` state (fails on the buggy engine, passes on
the fixed one) and (2) a seeded 60-listing property test asserting
`iter_legal_actions` == `legal_actions` as multisets of sort keys.

## Full 128-cell re-certification (2026-10-25, review grade)

`rerun_all_cells.py` re-ran BOTH engines (`search_landscape_horizons_compact`
+ `search_escape_idastar`) on **all 128 fixed-panel roots** with the fixed
`iter_legal_actions`, the exact frozen v14 budgets/configs (compact
`h3_b64_s200k` = horizon 3 / beam 64 / state budget 200,000; IDA* horizon 3;
30 s fail-closed time budget per engine per cell; scope `e44_core_v1`), and
the same hash-checked root-state loader the pilot used. Frozen `data/` and
`release/` were not touched.

**Pilot validation:** all 78 screened cells reproduce `pilot_cells.jsonl`
corrected statuses / best costs / escape depths exactly (the builder aborts on
any mismatch).

### Result: change_type breakdown (all 128 cells)

| change_type | cells | meaning |
| --- | --- | --- |
| `AGREE` | 82 | corrected exact quantities identical to frozen stated ones (includes both pilot controls and all 32 E44 oracle cells) |
| `RESOURCE_BOUNDED_BOTH` | 34 | frozen and corrected compact both truncated at the frozen budgets; **all 34 corrected incumbents identical to frozen (0 improved, 0 regressed)** |
| `FALSE_OPTIMUM_NOW_ESCAPE` | 6 | frozen stated exact H-local optimum, corrected finds an exact escape: best cost 10 -> 8, escape depth 3 (same 6 cells as the pilot) |
| `ESCAPE_DEPTH_OVERSTATED` | 3 | frozen stated escape depth 3, corrected exact depth 2, best cost unchanged (same 3 cells as the pilot) |
| `ESCAPE_COST_STATED_WRONG` | 2 | frozen stated exact best cost 21 -> 20 and 52 -> 51 (same 2 cells as the pilot) |
| `FROZEN_EXACT_NOW_TRUNCATED` | 1 | **new beyond the pilot** — see below |

Every non-empty corrected witness replayed: 69/69 `REPLAY_PASS` on both
engines, 0 failures.

### Corrected headline vs frozen

- Frozen headline: **94 exact best-cost** values (64 enumerated H-local optima
  + 29 enumerated escapes + 1 derived), classification 65 H-local + 63 escape.
- Corrected at the frozen budgets: **93 exact best-cost** values
  (58 exact H-local optima + 35 exact escapes, all compact-COMPLETE) + 0
  derived; 35 compact cells resource-truncated (34 with a certified escape
  witness, 1 without); IDA* exact on 127/128 (58 H-local + 69 escapes),
  1 truncated.
- **8 of the frozen 94 exact best-cost values change**, total −14 gates:
  the 6 false optima (10 -> 8) and the 2 cost corrections (21 -> 20,
  52 -> 51). A **9th** cell of the 94 is no longer re-certifiable at the
  frozen budget (below). All other 85 stated exact values reproduce exactly.
- The 3 stated escape depths 3 -> 2 corrections also reproduce panel-wide
  (no additional depth changes anywhere on the 128).

### Flagged cell (behaved differently than frozen, not hidden)

`e39:b2f83603…` (QFT, 8 qubits, baseline 148) — the frozen classification's
single `COMPACT_COMPLETE_DERIVED` cell: frozen compact truncated (time), but
frozen IDA* COMPLETED and proved the exact H-local optimum by derivation.
With the fixed engine, **both corrected compact and corrected IDA* hit the
200,000-state budget** (corrected compact at 200,000 states in 22.7 s; the
frozen compact saw 53,885) — the corrected engine generates strictly more
successors per state, so the exhaustive no-escape proof no longer fits the
frozen state budget. The exact H-local claim is neither confirmed nor refuted
at the frozen budgets; it is resource-bounded. This is the only cell whose
stated exact quantity lost its re-certification, and the only deviation from
the pilot's picture found in the big cells. No cell regressed on any stated
exact quantity and no corrected incumbent is worse than frozen anywhere.

### Determinism

A 10-cell subsample (5 changed + 5 agreeing, chosen deterministically: sort
each group by `source_id`, take 5 evenly spaced picks) was re-run a second
time: **all 10 byte-identical** on verdict / best_cost / escape_depth
(`determinism.json`).

### Provenance note (concurrent engine editing during certification)

While this re-certification ran, a concurrent session continued editing
`src/optimisation/certified_landscape.py` (working-tree hashes observed:
`9119a470…` at pilot time -> `d806e56e…` -> `9efba38a…`; the `iter_legal_actions`
fix itself is identical in all of them, and the later edits add a certified
IDA* lower-bound refinement and scope filtering on top).  Handling:

- `rerun_all_cells.py` records the engine source hashes **per cell**;
  `build_full_package.py` aborts unless all 128 cells share one hash.
- `run_with_stability.py` waited for the engine hash to settle, pruned cells
  produced under earlier versions, and resumed until all 128 cells were
  produced by the single settled version `9efba38a…` (pinned above and in
  `receipt.json`).
- Certified quantities (statuses / best costs / escape depths) were identical
  across every post-fix engine version observed: a first full 128-cell pass
  (`full_cells_first_pass.jsonl`), an interrupted second pass (56 cells), and
  the final pinned pass — only wall times and timing-dependent truncation
  detail differ.
- Environment note: the largest 12k-gate cells at the frozen 30 s budget
  enumerate enough states (~20k x ~140 KB) to need ~3 GB peak RAM; with the
  machine shared by concurrent sessions the first attempt at cell
  `e39:37cdb70b…` failed with `MemoryError` and was retried successfully
  under the same frozen budgets once memory allowed.  The frozen
  time/state budgets were never altered.

### Wall times (measured, producing run)

- Full corrected run: **1238.8 s ≈ 20.6 min** total (compact 1206.4 s, 32
  cells at the 30 s cap; IDA* 32.4 s, 0 cells capped) vs frozen same-panel
  1084.8 s (compact 1058.8 s + IDA* 26.0 s) — within the pilot's 18-22 min
  estimate.
- Corrected compact truncated for 29 cells on `time_budget` and 6 on
  `state_budget` (frozen: 20 time, 15 state); the split is timing-dependent
  (the archived first pass measured 25/10) while all certified quantities are
  identical.

