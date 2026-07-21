# Wave-4 Report: Phase-2b Grid Gap-Fill — QuantumWalk n=8

**Worker:** Phase2b补全_Grid
**Date:** 2026-07-21
**Scope (exclusive):** `experiments/phase2b_full_validation.py`,
`data/v8/phase2b_full/`, `docs/review/wave1/phase2b.md` (append-only),
`docs/review/wave4/phase2b_gridfill.md` (this file)

---

## 1. Task

Close the QuantumWalk n=8 gap in the Phase-2b v2 stratified grid (E26,
`data/v8/phase2b_full/`). The gap existed because the 9-qubit walk circuit
(36 MCX gates, up to 8 controls) made exact Operator-based fidelity exceed
the per-chunk compute envelope (~280 s / 3 rows estimate in the original
comment).

## 2. What was done

### 2.1 Timing probes (decision evidence)

Probed with `/d/Downloads/miniforge3/python` before choosing the fidelity
path:

| Probe | Result |
|---|---|
| Circuit generation, QuantumWalk n=8 | 9 qubits, 106 gates, depth 59; ops: 36 MCX, 54 X, 6 CCX, 6 CX, 3 H, 1 RY |
| `greedy_phase1` optimize + **exact** fidelity (1 row) | optimize 0.0 s; exact fidelity **133.3 s** |
| All 3 optimizers + `sampled200` fidelity (1 grid point) | all optimizers 0% reduction (106 -> 106); fidelity 1.0 via structural-equality fast path, ~0 s |

Exact fidelity at ~133 s/row x 6 rows (~13–15 min) plus the 300 s per-call
execution envelope of this runtime made the exact path infeasible here, so
the task-authorized `sampled200` fallback was used. Because all three
optimizers leave the MCX-heavy circuit structurally unchanged, the sampled
estimator resolves via its exact `circuit == target` fast path — the
reported fidelity of 1.0 is exact for these rows, and no row can false-pass.

### 2.2 Script changes (`experiments/phase2b_full_validation.py`)

- New chunk `qw8`: plans QuantumWalk n=8 x `ALGO_SEEDS` with the identical
  seed formula as the algo chunk (`BASE_SEED + seed*100 + n` -> seeds
  153/253, trials 0/1), forcing `fidelity_method=sampled200`.
- `_fidelity` / `_run_row` / `run_chunk`: threaded `force_method` override
  (default off; existing chunks unchanged).
- `merge_and_analyze`: coverage statement for
  `other_algorithmic_families` is now derived from the merged data (claims
  QuantumWalk n=8 coverage only when those rows are actually present, with
  the fidelity method read from the rows).
- All merged CSV outputs now written atomically (timestamped `.bak-*`
  backup + `.tmp` -> rename), matching the pre-existing metadata.json
  pattern and the wave-4 write-safety rules.
- Updated the stale comment at `size_override` (it claimed "up to
  7-controlled MCX, ~280 s / 3 rows"; the circuit in fact carries MCX up to
  8 controls and exact fidelity measured ~133 s/row).

### 2.3 Run + re-merge (2026-07-21)

- `python experiments/phase2b_full_validation.py --chunk qw8` -> 6 rows,
  `data/v8/phase2b_full/phase2b_v8_qw8_20260721_084322.csv`.
- `python experiments/phase2b_full_validation.py --merge-only` -> merged
  table **735 rows** (was 729); all summary artifacts regenerated.

## 3. Results (as measured, unvarnished)

**QuantumWalk n=8: 0.0% reduction for all three optimizers** (greedy
Phase-1, commutation Phase-2a, template Phase-2b full pipeline), both
seeds — identical to n={3,5}. Fidelity 1.0 on all 6 rows
(`fidelity_method=sampled200`, exact via structural-equality fast path).
This matches the pre-registered expectation of 0%: the MCX/X-gather
blocking is structural.

Merged-analysis deltas vs the pre-fill backups:

| File | Change |
|---|---|
| `core_question_v8.csv` | QuantumWalk `n_rows_phase2b` 4 -> 6; means 0.0/0.0/0.0; verdicts unchanged |
| `family_summary_v8.csv` | QuantumWalk per-optimizer counts 4 -> 6; means unchanged at 0.0 |
| `bootstrap_ci_v8.csv` | negligible: template_phase2b mean 0.4645 -> 0.4607, CI [0.4194, 0.5014] |
| `bv_theory_v8.csv` | unchanged; Thm-9 bound PASS at all n=3..10 |
| `metadata.json` | coverage now states QuantumWalk covered at n=[3,5,8] with sampled200 at n=8; `fidelity_methods` sampled200 6 -> 12 |

All 16 families now have full stratified-grid coverage.

## 4. Verification

- `pytest tests/ -q`: **298 passed, 0 failed** (281 s).
- Merge digest: BV vs Thm 9 PASS at every n; core-question verdicts
  unchanged.
- Timestamped backups preserved for all 6 overwritten artifacts
  (`*.bak-20260721-084339/084340`).
- Docs: addendum §10 appended to `docs/review/wave1/phase2b.md`
  (append-only; manuscript untouched).

## 5. Files changed

- `experiments/phase2b_full_validation.py` (edited; new sha256 applies)
- `data/v8/phase2b_full/phase2b_v8_qw8_20260721_084322.csv` (new, 6 rows)
- `data/v8/phase2b_full/phase2b_full_validation_v8.csv` (729 -> 735 rows)
- `data/v8/phase2b_full/{family_summary,core_question,bootstrap_ci,bv_theory}_v8.csv` (regenerated)
- `data/v8/phase2b_full/metadata.json` (coverage + fidelity-method counts)
- `data/v8/phase2b_full/*.bak-20260721-0843*` (6 timestamped backups — may be cleaned by the final wave)
- `docs/review/wave1/phase2b.md` (addendum §10 appended)

## 6. Outstanding issues / handoff notes

1. **Release manifest is now stale by design**: `release/release_manifest.json`
   pins the old sha256 + 729-row count for
   `data/v8/phase2b_full/phase2b_full_validation_v8.csv`, so
   `scripts/reproduce_all.py --verify` will flag that entry until the next
   wave regenerates the manifest (explicitly deferred per task brief).
2. **Fidelity method caveat for downstream prose**: the 6 QuantumWalk n=8
   rows carry `fidelity_method=sampled200`. The values are exact (circuits
   unchanged by all optimizers), but any manuscript/claim table that
   aggregates "exact-only" rows should be aware of the label. Manuscript
   edit deliberately not made here (out of scope; next wave owns it).
3. The pre-existing `scipy` Wilcoxon small-sample warning during merge is
   unchanged behavior, not a regression.
