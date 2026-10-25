# The "certified" claims contract (WL-2 closure, 2026-10-25)

**Status**: governance/theory document, review grade. Registers the single
definition of "certified" that every manuscript use of the word must carry,
and the witness-availability contract behind it.

## 1. Definition (the one paragraph)

A quantity in this project is called **certified** when it is produced by the
declared engine under a declared contract and carries all four of the
following, with hashes pinned in a receipt:

1. **Scope**: the rule library (SHA-256-pinned, currently
   `data/v13/e43_quartz_rule_import/generation_a/rule_library.json`) restricted
   by a named scope (`e44_core_v1` = source ≤ 2 qubits, ≤ 4 source ops, ≤ 6
   target ops; `full` = all 1,474), through the single authority
   `filter_rule_scope`.
2. **Horizon**: the search horizon $h$ (currently $h = 3$ actions). All
   landscape costs are **horizon-relative** (`best_cost_at_h3`), never
   unconstrained optima and never gate-count-optimal claims.
3. **Resource contract**: the exact state/time budgets under which the search
   ran (frozen budgets: compact `h3_b64_s200k`, 30 s fail-closed per cell;
   window searches: 20k states / 10 s), with every truncation recorded
   fail-closed — a resource-truncated quantity is reported as bounded, never
   as exact.
4. **Equivalence contract**: every claimed improvement carries a witness that
   replays through `replay_actions` against the hash-checked root state
   (`REPLAY_PASS` or the claim aborts); cross-checks are layered — E44 oracle
   (in-engine), determinism subsamples (byte-level), and the third-party
   MQT QCEC decision-diagram verifier (E59: 128/128 closure outputs
   equivalent, 13/16 perturbation negatives; QCEC covers the closure output
   layer, not the interior search).

"Exact" is the stronger qualifier: a quantity is **exact** only when the
enumeration or proof completed inside the resource contract (compact
`COMPLETE`, IDA* completion, or a valid derivation from completed
certificates), and it remains horizon-relative and scope-relative.

## 2. Witness availability contract

- Stored: the first escape certificate per (source, width, horizon) for E46;
  full witness sets for the compact/IDA* panels (all replayed).
- Regeneration: every stored witness set is **deterministically regenerable**
  by the committed runners (`experiments/e46_window_landscape/run.py`,
  `experiments/e45_development_grid/*`) from pinned inputs; the runners are
  the archive. Any regeneration must reproduce byte-identical results or the
  discrepancy is a defect.
- Engine identity: since the 2026-10-25 successor-bug fix, receipts pin
  `engine_source_hashes()` per cell
  (`docs/review/science_boost/2026-10-25_engine_successor_fix/`), so a
  verifier can confirm which engine produced each number.

## 3. Version discipline

v14/v15 are the frozen released record, produced by the pre-fix engine. v16
(`data/v16/`, 2026-10-25) is the corrected-engine re-pin at identical
budgets. Any manuscript number must name its version and engine; the
version meanings are registered in `data/DATA_CANONICAL.md`.

## 4. Known limits of the word

- Window claims are **window-local** (actions consuming gates outside the
  slice are invisible to the window).
- Closure-optimality claims are **⊥-relative**
  (`docs/theory/perp_reliability_2026-10-25.md`): phase-adjusted exchanges
  outside the nine exchange rules are not covered.
- The bounded tier's `best_cost` values are upper bounds from certified
  witnesses, not enumerated optima; `e65` (running) upgrades them where the
  raised contract completes.
