# Wave 3 — Final Verification Report (Release Manifest, `--verify`, pytest)

**Worker**: Final-verification engineer (wave 3, verification track)
**Date**: 2026-07-21 (timestamps below in local time)
**Scope owned**: `scripts/generate_release_manifest.py`, `release/release_manifest.json`,
`data/**/metadata.json` (manifest-required tweaks only), `_agent_work/` audit.
`docs/` was read-only for this worker (parallel documentation worker owns it).

---

## 1. Diagnosis of the failing `--verify`

Baseline run (`/d/Downloads/miniforge3/python scripts/reproduce_all.py --verify`,
output saved during the session) failed for exactly **one** hard error:

```
❌   SOTA_BENCHMARK | data/v6/sota_benchmark/aggregated/sota_comparison_aggregated.csv: SHA-256 mismatch
   Expected: 5c230d233c75821c9dd3f58e8267ba705b55e785ff2beb1c09c80cff4fc084d4
   Actual:   bfcaaa47588109fe4a07bd61a49d55df3d0dfe476dd40656d48c3cfa9345fe31
```

Root causes (all manifest staleness, no data corruption):

1. **SOTA aggregate regenerated in wave 1.** The compiler worker expanded
   `raw/` (canonical qiskit level0/1/2 runs + the fixed cirq run, see
   `docs/review/wave1/compiler_baseline.md` §"Created") and regenerated
   `aggregated/sota_comparison_aggregated.csv` from 60 → **105 rows**
   (protocol schema; three `.bak-20260720-*` copies of the 60-row file kept).
   The release manifest still pinned the old SHA/row count.
2. **`data/v8/` added after the manifest.** `phase2b_full/` (729-row canonical,
   declared in its `metadata.json`) and the 288-row EHW full run were absent
   from the manifest; `HARDWARE_VALIDATION` still pointed at the 48-row smoke
   file via `CANONICAL_FILE_OVERRIDES`.
3. **`data/v6/sota_benchmark/metadata.json` stale**: `n_rows: 60` (a wave-1
   backfill) no longer matched the regenerated aggregate.

The per-experiment structural checks already passed; the only failing gate was
the manifest checksum table. The ⚠️ "source file modified since run" notices
(E12/E13/E21/E25) are pre-existing provenance warnings (sources legitimately
improved after data generation) — warnings, not failures; left as-is.

## 2. Decisions (recorded per task instructions)

- **EHW canonical = 288-row full run.** No `metadata.json` exists in
  `data/v8/hardware_validation/` (only per-run `ehw_metadata_*.json` sidecars),
  so the decision was implemented via `CANONICAL_FILE_OVERRIDES` in
  `scripts/generate_release_manifest.py` — the mechanism built for exactly this
  case — switching the override from `ehw_runs_smoke_20260720_150244.csv` (48)
  to `ehw_runs_full_20260720_150931.csv` (288), with an explanatory comment.
  This matches the wave-1 hardware worker's designation
  (`docs/review/wave1/hardware_validation.md`: "FULL run, 288 rows (canonical)")
  and resolves the conflict flagged in wave-2
  (`docs/review/wave2/supporting_docs_integration.md`, decision D1).
  The two smoke runs (48/96 rows) stay on disk for provenance;
  `ehw_summary_*.csv` files remain derived aggregates (not collected).
- **phase2b_full 729 rows canonical.** Its `metadata.json` already declares
  `canonical_data_file: phase2b_full_validation_v8.csv`; the collector picks it
  up with no override. Summary/chunk CSVs in the same directory are correctly
  excluded (metadata-declared single canonical file).
- **sota `raw/` stays non-canonical input.** It remains in
  `NON_CANONICAL_DIR_NAMES`; `aggregated/sota_comparison_aggregated.csv` (now
  105 rows) is the single canonical dataset, exactly as documented in
  `data/v6/sota_benchmark/metadata.json` and its README. The manifest was
  regenerated to pin the current SHA/rows — **no validation rule was relaxed**;
  verify passes against the real on-disk checksums.
- **`data/v6/sota_benchmark/metadata.json` tweak (in scope)**: `n_rows`
  60 → 105 with an appended dated note explaining the wave-1 regeneration.
  Atomic write (`.tmp` → `os.replace`); timestamped backup kept.

## 3. Changes made

| File | Change | Backup |
|------|--------|--------|
| `scripts/generate_release_manifest.py` | `CANONICAL_FILE_OVERRIDES[("v8","hardware_validation")]` → full-run CSV; comment records the wave-3 decision | `scripts/generate_release_manifest.py.bak-20260721-011956` |
| `data/v6/sota_benchmark/metadata.json` | `n_rows` 60 → 105 + explanatory note (atomic) | `data/v6/sota_benchmark/metadata.json.bak-20260721-011956` |
| `release/release_manifest.json` | Regenerated (`--release-id q-research-8.0.0-wave3`), written to a temp file then `mv`ed into place (atomic) | `release/release_manifest.json.bak-20260721-011956` |

No other files written. No `git add/commit/push` performed (forbidden).

## 4. Verification results

### 4.1 `scripts/reproduce_all.py --verify` — PASS (genuine)

```
✅ All 34 manifest dataset checksums verified
✅ All per-experiment structural checks passed
✅ All data integrity checks passed (manifest + structural)
  ✅ PASS: verify
🎉 ALL TASKS PASSED — Reproduction successful!
```

Exit code 0; 34/34 datasets verified by SHA-256 + exact row count against the
on-disk CSVs. The previously failing SOTA entry now verifies
(`bfcaaa47…`, 105 rows).

### 4.2 Full pytest — 298 passed, 0 failed

`test_optimizers.py` was split into segments (per task note about its 5–8 min
runtime); everything else ran in one pass:

| Segment | Result | Runtime |
|---------|--------|---------|
| `pytest tests/ -q --timeout=600 --ignore=tests/test_optimizers.py` | 253 passed | 7.54 s |
| `test_optimizers.py -k "TestBaseOptimizer or TestGreedyOptimizer or TestPerformance"` | 15 passed | 0.71 s |
| `-k "TestGACrossoverFix or TestQuantumAdderFix"` | 9 passed | 271.17 s |
| `-k "TestRotationMergingBugFix"` | 14 passed | 0.67 s |
| `-k "TestFidelityEstimator"` | 7 passed | 7.53 s |
| **Total** | **298 passed, 0 failed** | — |

Only deprecation warnings (Qiskit 2.x); no failures, so no failure-logging or
fixes were needed.

### 4.3 Manifest final state

- **Datasets: 34** (was 33; +1 = `E26_phase2b_full_v8`; SOTA and EHW entries
  updated in place).
- **Total rows: 73,696** (was 72,682; Δ = +105−60 SOTA, +288−48 EHW, +729
  phase2b_full).
- New/updated entries:
  - `SOTA_BENCHMARK | data/v6/sota_benchmark/aggregated/sota_comparison_aggregated.csv | 105 rows | sha256 bfcaaa47588109fe…`
  - `HARDWARE_VALIDATION | data/v8/hardware_validation/ehw_runs_full_20260720_150931.csv | 288 rows | sha256 e6537e0ee9b59ca5…`
  - `E26_phase2b_full_v8 | data/v8/phase2b_full/phase2b_full_validation_v8.csv | 729 rows | sha256 81a0d1f44340e738…`
- Cross-check: the EHW-full SHA prefix `e6537e0e…` and phase2b-full prefix
  `81a0d1f4…` match the values independently recorded by the wave-2 docs worker
  in `docs/supplementary/supplementary_materials.md` S5.1. ✓
- `git.dirty = true` in the manifest (worktree has uncommitted wave 1–3
  changes; committing is outside this worker's permissions). The generator's
  review-H8 dirty-tree warning printed as designed.

## 5. `predictive_advantage_*.csv" disappearance — resolved (not lost)

The compiler worker reported `data/v6/sota_benchmark/predictive_advantage_*.csv`
missing. Investigation:

1. `_agent_work/orphan_outputs/` — contains earlier-session run outputs
   (e26/e29/gate-shuffle/phase2b/wcl/ceiling-model intermediates); **no**
   predictive-advantage files there, and none of its contents are canonical
   candidates (all superseded by the canonical CSVs already in the manifest).
2. Git history — `git ls-files` shows the three files were tracked at
   `data/v6/sota_benchmark/predictive_advantage_{predictions,results}.csv` and
   `predictive_advantage_summary.json` (top level, pre-reorganization).
   `git status` shows them as `D` (deleted) at the old paths with
   `data/v6/sota_benchmark/derived/` untracked.
3. Disk — the files now live at `data/v6/sota_benchmark/derived/…`; the first
   rows of `derived/predictive_advantage_results.csv` are byte-identical to
   `git show HEAD:data/v6/sota_benchmark/predictive_advantage_results.csv`.

**Conclusion**: the files were *relocated* into `derived/` during the wave-1
reorganization, not lost; content intact. This matches the layout documented in
`data/v6/sota_benchmark/metadata.json` notes and `DATA_CANONICAL.md`
("derived/ → experiments/predictive_advantage.py"). `derived/` is in
`NON_CANONICAL_DIR_NAMES`, so they are correctly excluded from the manifest as
derived artifacts. No restoration or manifest change needed.

## 6. `_agent_work/` audit

- `orphan_outputs/`: see §5 — historical intermediates only; no action.
- `data_integrity/`: `normalize_metadata.py` + `metadata_backups/` from the
  wave-1 metadata normalization; consistent with current `metadata.json` files.
- `past_sessions/`: archived session digests; informational only.

## 7. Leftover issues / handoff items

1. **README.md Experiment Registry stale (read-only for me — docs worker)**:
   EHW row still says 48 (manifest now 288); footer says "over 72,000 data rows
   across 33 canonical datasets" (now 73,696 / 34). Registry also omits
   SOTA_BENCHMARK, HELDOU, ISOLATION, CEILING_REPAIR, E10p2b-full etc. — it is a
   curated subset pointing to the manifest for exact counts, but the EHW row
   count and the totals line now contradict the manifest.
2. **`data/DATA_CANONICAL.md` stale (docs worker)**: still states "33 canonical
   datasets, 72,682 rows (2026-07-20)", SOTA 60 rows, EHW = smoke 48 rows, and
   has no `v8/phase2b_full` row; its header line references the 33-dataset
   manifest.
3. **`data/v6/sota_benchmark/README.md` stale (docs worker)**: header says
   "Canonical dataset … (60 rows)" and its raw/ table cites only the 20260718
   runs; the wave-1 canonical raw set is now level0/1/2 + fixed cirq with a
   105-row aggregate.
4. **Git worktree dirty**: the manifest's `source_hashes` are not recoverable
   from git alone until the wave 1–3 changes are committed (review-H8 warning).
   Committing is forbidden for workers; release owner should commit and, if a
   clean-tree manifest is required, re-run
   `python scripts/generate_release_manifest.py` + `--verify`.
5. **Pre-existing provenance warnings** in `--verify` (E12/E13/E21/E25: 10
   source files each modified since data generation): warnings only, verify
   still passes. If a future release requires zero warnings, those experiments
   must be re-run with the current sources (out of scope here).
