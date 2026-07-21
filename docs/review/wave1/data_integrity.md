# Wave-1 Data Integrity & Schema — Completion Report

> Worker: 数据管家_Data (Data Integrity & Schema)
> Date: 2026-07-20
> Scope: `data/**`, `release/release_manifest.json`, `scripts/generate_release_manifest.py`,
> `data/DATA_CANONICAL.md`, `docs/data_dictionary.md`, `README.md` (dataset counts only)

## Verification (final)

```bash
/d/Downloads/miniforge3/python scripts/generate_release_manifest.py
#   -> Release manifest written to release/release_manifest.json ; Datasets: 33
/d/Downloads/miniforge3/python scripts/reproduce_all.py --verify
#   -> All 33 manifest dataset checksums verified
#   -> All per-experiment structural checks passed
#   -> All data integrity checks passed (manifest + structural) ; PASS: verify
```

Pre-existing warnings only (out of scope): several v5/v6 metadata `source_hashes`
are stale because optimizer source files changed after the runs (E21, E25, etc.)
— informational, unchanged by this wave. `git.dirty = true` in the manifest is
expected while the multi-worker wave is in flight (review H8 warning).

## 1. Metadata minimal-schema unification

All 31 experiment directories under `data/` now have a `metadata.json`
satisfying the minimal schema: `experiment_id`, `description`, `timestamp`,
`n_rows`, `seed`, `python_version`, `qiskit_version`, `git_commit`,
`canonical_data_file`.

- Backfills are **additive**; every backfilled/corrected field is recorded in
  the file's `notes` list with its source and the normalization timestamp.
- `n_rows` was recomputed from the canonical CSV on disk for every experiment
  (authoritative); several directories only had `total_rows` before.
- `timestamp` recovered from `run_id` where it was null (E20, E21).
- `git_commit` backfilled only where independently verifiable: v7/e29 from the
  run's own provenance sidecar (`8f41dbc...`, archived at
  `_agent_work/orphan_outputs/metadata.json`). All other unknown commits left
  `null` with an explicit note — no fabrication.
- Key normalization: v7/e23, v7/e24 legacy `experiment` key renamed to
  `experiment_id`; legacy `csv_path` superseded by `canonical_data_file`.
- Created `metadata.json` where missing: `data/v6/ceiling_repair/`,
  `data/v6/sota_benchmark/` (top-level).
- Normalizer script (one-off, deterministic, re-runnable):
  `_agent_work/data_integrity/normalize_metadata.py`.
- Pre-overwrite backups of every touched metadata.json:
  `_agent_work/data_integrity/metadata_backups/**` (`metadata.json.bak-<ts>`).

## 2. Multi-CSV experiments: canonical identification + derived/

| Experiment | Canonical (kept in place) | Moved to `derived/` |
|---|---|---|
| v4/e11 (2 CSV) | `e11_merged_powered.csv` (519) | supplemental replica CSV + its run metadata |
| v5/e18 (8 CSV + 2 JSON + 1 TXT) | `e18_clifford_t_e18_full_20260610_052140.csv` (270) | `e18_corrected.csv`, `e18_fidelity_verified.csv`, `e18_imputation_draws.csv`, `e18_itt_report.csv`, `e18_survivor_bias_report.csv`, `e18_fidelity_summary.json`, `e18_littles_mcar.json`, `e18_bias_report.txt` |
| v6/e21 (3 CSV) | `ceiling_aware_comparison.csv` (1,140) | `ceiling_aware_summary.csv`, `e21_paired_statistics.csv` |
| v6/sota_benchmark (11 CSV + 1 JSON) | `aggregated/sota_comparison_aggregated.csv` (60) | `predictive_advantage_predictions.csv`, `predictive_advantage_results.csv`, `predictive_advantage_summary.json`; `raw/` (per-tool primary runs) and `metadata/` (per-run sidecars) stay as documented non-canonical inputs |
| v7/e24 (2 CSV) | `e24_theorem7_results.csv` (75) | `e24_theorem7_summary.csv` |
| v7/e29 (2 CSV) | `e29_multi_seed_e04_full.csv` (800) | `e29_multi_seed_statistics.csv` |

Reference safety check: no analysis/test code reads any moved file by path (the
e18/e21/sota scripts only *write* derived files). `docs/manuscript/appendix.md`,
`docs/manuscript/sections/e18_revised.md`, `docs/results/e18_survivor_bias.md`,
`docs/supplementary/supplementary_materials.md`,
`docs/analysis/e18_failure_analysis.md` mention some derived file names in prose
without directory prefixes — content-wise still correct; integration worker may
optionally update path references.

New READMEs documenting canonical/derived relationships: `data/v4/e11/README.md`,
`data/v6/e21/README.md`, `data/v6/sota_benchmark/README.md`,
`data/v7/e24/README.md`, `data/v7/e29/README.md`; `data/v5/e18/README.md`
rewritten (see §5).

## 3. Release manifest regeneration

`scripts/generate_release_manifest.py` updated:

- Covers `data/v2_fixed` … `data/v8` (v8 included; hardware worker's
  `data/v8/hardware_validation/` left untouched).
- Emits **canonical CSVs only**: skips `derived/`, `metadata/`, `raw/`, `logs/`,
  and `scholar/` subdirectories (the last holds the references workstream's
  ref-verification CSVs under `v6/ceiling_repair/scholar/` — not experiment
  datasets).
- `CANONICAL_FILE_OVERRIDES` for metadata-less dirs owned by other workstreams
  (v8/hardware_validation → `ehw_runs_smoke_20260720_150244.csv`; the
  `ehw_summary_*` CSV is a derived aggregate).
- Schema labels fixed: v7 entries now `results_v7` (were mislabeled
  `legacy_v2_v3`); added `results_v8`.
- `experiment_id` taken from metadata (e.g. `WCL-E19`, `MC-E20`,
  `SOTA_BENCHMARK`) instead of upper-cased dir names; dedup guard against
  double-counting files reachable from multiple directories.
- `SUPERSEDED_DIRS` now a map; v6 E29 smoke (80 rows) marked
  `superseded_by: v7/e29 (800 rows)`.

Result: **33 canonical datasets, 72,682 rows** (was: 44 entries including raw
and derived files, with mislabeled schemas). Old manifest backed up at
`release/release_manifest.json.bak-20260720-230228`.

`README.md` counts updated in the two allowed places: "over 72,000 data rows
across 33 canonical datasets" (was 67,000 / 27).

## 4. `data/DATA_CANONICAL.md` rewritten (v2.0.0)

- Accurate canonical table for all 33 datasets incl. v6/e21, v7/e23, v7/e24,
  v7/e26, v7/e29, SOTA, ceiling-repair, v8/EHW (previous version stopped at
  E19 and contained stale E11/E12 file names).
- New sections: role definitions (canonical/derived/raw/smoke/legacy), metadata
  minimal schema, `derived/` directory inventory with generators, **data
  version policy** (§6 below), updated Known Issues (E18 numbers, E29
  supersession, v8 noise-model caveat).
- Backup: `data/DATA_CANONICAL.md.bak-20260720-230847`.
- `docs/data_dictionary.md` lightly aligned (schema-family table now covers
  results_v6/v7/v8 accurately; data-version list extended; version bumped to
  2.1.0).

## 5. E18 audit

`data/v5/e18/README.md` rewritten: derived-file table now points at `derived/`;
added a dedicated section recording **`e18_bias_report.txt` content and
whereabouts** — now at `data/v5/e18/derived/e18_bias_report.txt` (generated by
`experiments/e18_bias_correction.py`). Key contents captured in the README and
DATA_CANONICAL Known Issues: Little's MCAR rejected (p = 1.570e-12; MAR
explained by family + width); 120/270 = 44.4% failures (78 decompose + 42
fidelity-zero, both systematic); pooled survivor mean 0.1800 is an upper bound;
ITT-MI estimate 0.1351 [0.102, 0.169]; sensitivity bracket width 0.0520.
Backup: `data/v5/e18/README.md.bak-20260720-230946`.

## 6. Data version policy (now in DATA_CANONICAL.md)

Create a new `data/vN/` — never overwrite a canonical file in place — when any
of: (1) new evidence layer (new experiment/benchmark); (2) incompatible schema
change; (3) full-mode supersession of an earlier smoke/reduced run of the same
experiment (old dataset kept, marked `superseded` in the manifest).

- v2_fixed: E1–E5 bug-fixed re-runs. v4: real-circuit era (E11–E13).
- v5: extended suites (E10 expanded, E14–E18, heldout/isolation).
- v6: review-driven supplements (E19–E21, E25, E10p2b/variance, E29 smoke,
  SOTA, ceiling repair).
- v7: theory validation + full-mode re-runs (E10p2b-full, E19-ext, E22–E24,
  E26, E29 full).
- v8: hardware validation only (backend-based; smoke = noise-model simulation
  on fake backends; real IBM Quantum runs land here too). Never reuse v8 for
  simulator re-runs of simulator experiments.

## 7. Orphan outputs: `experiments/outputs/` → `_agent_work/orphan_outputs/`

All 33 files moved (nothing deleted); the directory itself removed. Per-file
rationale:

| File | Reason for archival |
|---|---|
| `phase2b_full_validation_full_20260718_211931.csv`, `..._221328.csv` | Un-curated run outputs; canonical copy curated at `data/v7/e10_phase2b_full/e10_phase2b_full_validation.csv` |
| `phase2b_full_validation_smoke_20260717_132402.csv` | Smoke run; never manuscript evidence |
| `wcl_full_family_full_20260718_212135.csv`, `..._212845.csv` | Canonical copy curated at `data/v7/e19_extended/e19_wcl_full_family.csv` |
| `wcl_full_family_smoke_20260717_132403.csv`, `..._132457.csv` | Smoke runs |
| `gate_shuffle_ablation_full_20260718_203735.csv`, `..._204023.csv` | Canonical copy curated at `data/v7/e22/e22_gate_shuffle_ablation.csv` |
| `gate_shuffle_ablation_smoke_20260717_132402.csv`, `..._132457.csv` | Smoke runs |
| `multi_seed_e04_full_20260719_005736.csv`, `..._010407.csv` | Canonical copy curated at `data/v7/e29/e29_multi_seed_e04_full.csv` |
| `multi_seed_e04_smoke_20260717_132436.csv` | Smoke run |
| `e29_statistics_full_20260719_005736.csv`, `..._010407.csv`, `e29_statistics_smoke_20260717_132436.csv` | Derived statistics; canonical statistics curated at `data/v7/e29/derived/e29_multi_seed_statistics.csv` |
| `e26_bv_theory_20260717_132402.csv`, `..._211931.csv`, `..._221328.csv` | Canonical copy curated at `data/v7/e26/e26_bv_theory_results.csv` |
| `ceiling_model_results.csv`, `ceiling_model_predictions.csv` | Analysis byproducts of `experiments/ceiling_model_repair.py`; curated LOFO CV artifacts live at `data/v6/ceiling_repair/` |
| `comprehensive_analysis_report.txt` | One-off analysis report (`experiments/comprehensive_analysis.py`); not a dataset |
| `e18_itt_analysis.csv` | Superseded by curated E18 ITT artifacts at `data/v5/e18/derived/e18_itt_report.csv` |
| `metadata.json` | Run metadata for the E29 full run (outputs-dir era); archived for provenance (used to backfill v7/e29 `git_commit`) |
| `logs/{phase2b,seed,shuffle,wcl}{,.err}.log` | Run logs of the 2026-07-18/19 batch; provenance only |

v7 metadata `source_file` fields that pointed into `experiments/outputs/` were
annotated with `archived_source_file` + a note (canonical CSVs already lived in
`data/v7/`).

## Changed files (this worker)

- `data/DATA_CANONICAL.md` (rewrite; .bak kept)
- `data/v4/e11/{metadata.json,README.md}`, `data/v4/e11/derived/` (2 files moved)
- `data/v5/e18/{metadata.json,README.md}`, `data/v5/e18/derived/` (8 files moved)
- `data/v6/ceiling_repair/metadata.json` (new), `data/v6/e21/{metadata.json,README.md}`,
  `data/v6/e21/derived/` (2 moved), `data/v6/sota_benchmark/{metadata.json,README.md}`,
  `data/v6/sota_benchmark/derived/` (3 moved)
- `data/v7/e24/{metadata.json,README.md}`, `data/v7/e24/derived/` (1 moved),
  `data/v7/e29/{metadata.json,README.md}`, `data/v7/e29/derived/` (1 moved)
- `data/**/metadata.json` — 31 files normalized (backups in `_agent_work/data_integrity/metadata_backups/`)
- `scripts/generate_release_manifest.py`
- `release/release_manifest.json` (regenerated; .bak kept)
- `docs/data_dictionary.md` (schema families + version list alignment)
- `README.md` (two dataset-count sentences only)
- `_agent_work/orphan_outputs/` (33 archived files), `_agent_work/data_integrity/` (normalizer + backups)

Untouched as instructed: `docs/manuscript/manuscript.md`, `data/v8/**` contents.

## Remaining gaps

1. `docs/supplementary/supplementary_materials.md` (not my file) lists manifest
   entries for E21 summary/paired-statistics CSVs and old SHA-pinned tables that
   are now stale after the derived/ moves and manifest regeneration — needs the
   docs/supplementary worker to refresh from the new manifest.
2. Stale `source_hashes` in older metadata (E21, E25, etc.) — pre-existing,
   reflects genuine post-run source edits; left as-is with verify warnings.
3. v8/hardware_validation smoke is noise-model simulation, not real hardware;
   canonical designation (`ehw_runs_*`) is codified via generator override
   because the directory must not be modified — if the hardware worker later
   adds its own `metadata.json` with `canonical_data_file`, that takes
   precedence automatically.
4. `data/v6/ceiling_repair/scholar/` (references workstream) appeared mid-wave;
   excluded from the manifest as non-experiment data. If the references worker
   intends those CSVs as release data, they should declare a canonical file in
   a metadata.json there.
5. Derived-file generators (e18/e21/sota scripts) still write next to canonical
   when re-run; checked-in copies live under `derived/`. Not changed (scripts
   owned by other workstreams); documented in DATA_CANONICAL.md.
