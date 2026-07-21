# Canonical Data Files

> **Version**: 2.2.0  
> **Date**: 2026-07-21  
> **Purpose**: Define, for every experiment, the single **canonical** CSV used
> for analysis and manuscript figures, the layout of derived artifacts, and the
> data-version policy. Aligned with `release/release_manifest.json` (36 canonical
> datasets, 82,721 rows as of 2026-07-21).

## Roles

- **Canonical** — the authoritative dataset for an experiment; the only file
  listed in `release/release_manifest.json` for that experiment. Declared in the
  experiment directory's `metadata.json` via `canonical_data_file`.
- **Derived** — analysis artifacts regenerated from the canonical CSV (bias
  corrections, aggregates, paired statistics, imputation draws). Stored in a
  `derived/` subdirectory of the experiment directory; **not** listed in the
  release manifest. Regenerate from canonical if stale; never edit by hand.
- **Raw inputs** — primary per-tool run files that feed a canonical aggregate
  (currently only `data/v6/sota_benchmark/raw/`). Kept for provenance; not
  canonical themselves.
- **Smoke** — quick validation runs; never used as manuscript evidence. A smoke
  dataset is marked `superseded` in the manifest once a full run exists
  (e.g. v6 E29 smoke → v7 E29 full).
- **Legacy** — earlier versions kept for provenance only (see *Legacy Data*).

## Metadata minimal schema

Every experiment directory's `metadata.json` carries at least:

`experiment_id`, `description`, `timestamp`, `n_rows`, `seed`,
`python_version`, `qiskit_version`, `git_commit`, `canonical_data_file`

Fields that were not recorded at generation time were backfilled during the
2026-07-20 data-integrity wave; each backfill is documented in the file's
`notes` list (source of the value or an explicit "not recorded" statement).
`n_rows` always reflects the actual canonical CSV row count.

## Canonical Files

| Exp | Canonical File | Rows | Schema | Notes |
|-----|----------------|------|--------|-------|
| E1 | `v2_fixed/e01/e01_phase_transition_v2_20260613_132653.csv` | 25,000 | legacy_v2_v3 | Deterministic; all copies identical |
| E2 | `v2_fixed/e02/e02_entanglement_density_v2_20260613_130455.csv` | 2,100 | legacy_v2_v3 | Deterministic |
| E3 | `v2_fixed/e03/e03_scaling_v2_20260611_224540.csv` | 12,000 | legacy_v2_v3 | v5/e03 is a duplicate (fidelity rounding only) |
| E4 | `v2_fixed/e04/e04_algorithm_comparison_v2_20260613_132653.csv` | 400 | legacy_v2_v3 | Single seed; multi-seed extension is E29 |
| E5 | `v2_fixed/e05/e05_landscape_v2_20260613_130355.csv` | 6,000 | legacy_v2_v3 | Deterministic |
| E10 | `v5/e10/e10_expanded_phase1_vs_phase2_20260613_131601.csv` | 1,905 | results_v2 | Expanded version; the 819-row intermediate run is superseded |
| E11 | `v4/e11/e11_merged_powered.csv` | 519 | results_v1 | Merge of full run + supplemental replica (replica kept in `derived/`) |
| E12 | `v4/e12/e12_compiler_baseline_e12_full_20260626_000134_nocoupling.csv` | 568 | results_v1 | Fair comparison mode (no coupling map) |
| E13 | `v4/e13/e13_structural_ceiling_e13_full_20260609_043322.csv` | 56 | results_v1 | Only full run |
| E14 | `v5/e14/e14_extended_benchmark_e14_full_20260611_114726.csv` | 2,130 | results_v2 | 15 families, extended metrics |
| E15 | `v5/e15/e15_multi_compiler_e15_full_20260611_150934.csv` | 994 | results_v2 | **Qiskit only** (no Cirq/t\|ket>) |
| E16 | `v5/e16/e16_window_scaling_e16_full_20260610_142547.csv` | 696 | results_v2 | Only full run |
| E17 | `v5/e17/e17_connectivity_e17_full_20260610_150935.csv` | 755 | results_v2 | Only full run |
| E18 | `v5/e18/e18_clifford_t_e18_full_20260610_052140.csv` | 270 | results_v2 | Survivorship-biased: 120/270 = 44.4% failure; bias artifacts in `derived/` |
| E19 | `v6/e19/e19_wcl_listing_full_e19_full_20260620_123825.csv` | 10,000 | results_v6 | WCL 7.83% vs LBL 0% on random Universal circuits |
| E20 | `v6/e20/multi_compiler_full.csv` | 1,070 | results_v6 | Qiskit/Cirq/t\|ket> on 15 families |
| E21 | `v6/e21/ceiling_aware_comparison.csv` | 1,140 | results_v6 | Primary per-trial data; summary + paired stats in `derived/` |
| E23 | `v7/e23/e23_ag_canonical_results.csv` | 160 | results_v7 | Thm 6: Phase-1 = 0% on AG-canonical Clifford |
| E24 | `v7/e24/e24_theorem7_results.csv` | 75 | results_v7 | Thm 7 hardness family; per-size summary in `derived/` |
| E25 | `v6/e25/e25_industry_benchmarks_e25_industry_proxies_20260711_042550.csv` | 66 | results_v6 | Qiskit-based industry proxy circuits |
| E26 | `v7/e26/e26_bv_theory_results.csv` | 4 | results_v7 | Thm 9 BV-oracle bounds, n = 3..7 |
| E29 | `v7/e29/e29_multi_seed_e04_full.csv` | 800 | results_v7 | 10-seed E04 extension; per-optimizer statistics in `derived/` |
| E10p2b | `v6/e10_phase2b/e10_phase2b_validation_20260622_115818.csv` | 1,017 | results_v6 | Phase-2b validation on the E10 suite; companion theory CSV in same dir |
| E10var | `v6/e10_real_variance/e10_real_variance_20260623_012636.csv` | 700 | results_v6 | 5-seed real-family variance; summary CSV in same dir |
| E10p2b-full | `v7/e10_phase2b_full/e10_phase2b_full_validation.csv` | 624 | results_v7 | Phase-2b on all 15 families at canonical sizes |
| E19-ext | `v7/e19_extended/e19_wcl_full_family.csv` | 960 | results_v7 | WCL vs LBL across all 15 families |
| E22 | `v7/e22/e22_gate_shuffle_ablation.csv` | 2,240 | results_v7 | Shuffle ablation: ORIGINAL vs SHUFFLED vs WCL |
| E29-smoke | `v6/e29_multi_seed_e04/e29_multi_seed_smoke_20260717_121732.csv` | 80 | results_v6 | **Superseded by v7/e29** (800 rows, 10 seeds) |
| SOTA | `v6/sota_benchmark/aggregated/sota_comparison_aggregated.csv` | 105 | results_v6 | Canonical aggregate (7 tool configs × 15 families: Qiskit default/L0/L1/L2, Cirq fixed, t\|ket>, custom); per-tool runs in `raw/`, predictive-advantage analysis in `derived/` |
| CeilingRepair | `v6/ceiling_repair/lofo_cv_results.csv` | 20 | results_v6 | LOFO CV of the repaired ceiling model (analysis artifact) |
| Heldout | `v5/new_families_heldout.csv` | 125 | results_v2 | Phase 7 held-out validation |
| Isolation | `v5/qiskit_pass_isolation.csv` | 100 | results_v2 | Phase 7 Qiskit pass isolation |
| EHW | `v8/hardware_validation/ehw_runs_full_20260720_150931.csv` | 288 | results_v8 | Hardware-validation full run (FakeManilaV2/FakeNairobiV2 noise-model simulation, **not** real hardware); supersedes the 48-row smoke; summary CSV in same dir is derived |
| E10p2b-v2 | `v8/phase2b_full/phase2b_full_validation_v8.csv` | 2,427 | results_v8 | Phase-2b v2 full-scale validation (wave-6 full-factorial grid: depth families n=3..10 x depth={20..50 step 5}, 56/56 combos; 0 fidelity failures); BV reaches exact k+2 optimum on all 80 instances; analysis CSVs in same dir |
| E_listing_sensitivity_v8 | `v8/listing_sensitivity/listing_sensitivity_v8.csv` | 6,652 | results_v8 | Listing-sensitivity check (wave-6 full coverage): 15/15 families x 20-50 relisting variants; production compilers 0/126 sensitive, prototype 15/42 (6 sensitive families); qwalk_8 partial (3/20 variants; its 12 rows skip the exact unitary check) |
| E27_new_families | `v8/e27_new_families/e27_new_families_v8.csv` | 675 | results_v8 | 5 new circuit families (QPE, TrotterHamiltonian, QuantumVolume, WState, RepetitionCode) for family-mean statistical power; wave-6 PART-5 LOFO evaluation in `v6/ceiling_repair/part5_*` (docs/review/wave6/e27_part5.md) |

**Totals**: 36 canonical datasets, 82,721 rows (2026-07-21).

## derived/ directories

| Directory | Contents | Generator |
|-----------|----------|-----------|
| `v4/e11/derived/` | Supplemental replica CSV + its run metadata (merged into canonical) | `experiments/e11_real_circuit_benchmark/run_supplemental.py` |
| `v5/e18/derived/` | `e18_corrected.csv`, `e18_fidelity_verified.csv`, `e18_imputation_draws.csv`, `e18_itt_report.csv`, `e18_survivor_bias_report.csv`, `e18_fidelity_summary.json`, `e18_littles_mcar.json`, `e18_bias_report.txt` | `experiments/e18_fidelity_verification.py`, `experiments/e18_bias_correction.py`, `scripts/e18_survivor_bias_report.py` |
| `v6/e21/derived/` | `ceiling_aware_summary.csv`, `e21_paired_statistics.csv` | `experiments/e21_ceiling_aware/run.py`, `analyze.py` |
| `v6/sota_benchmark/derived/` | `predictive_advantage_predictions.csv`, `predictive_advantage_results.csv`, `predictive_advantage_summary.json` | `experiments/predictive_advantage.py` |
| `v7/e24/derived/` | `e24_theorem7_summary.csv` | `experiments/e24_theorem7/run.py` |
| `v7/e29/derived/` | `e29_multi_seed_statistics.csv` | `experiments/multi_seed_e04.py` |

Note: the generator scripts write derived files next to the canonical CSV when
re-run; the checked-in copies live under `derived/`. Content is identical as of
2026-07-20; regenerate and re-archive if the canonical file changes.

## Data version policy

A new `data/vN/` directory is created — never an in-place overwrite of an
existing canonical file — when **any** of the following holds:

1. **New evidence layer**: a new experiment or benchmark that did not exist
   before (e.g. v6: review-driven supplementary experiments E19–E21, E25, SOTA).
2. **Schema change**: the row schema changes incompatibly (column renames,
   new mandatory provenance fields).
3. **Full-mode supersession**: a full-mode run replaces an earlier smoke or
   reduced run of the *same* experiment (e.g. v7 E29 full supersedes v6 E29
   smoke). The older dataset stays on disk and is marked `superseded` in the
   release manifest.

Version meanings:

- **v2_fixed** — E1–E5 re-runs with the fixed Greedy v3.0.0 (supersedes buggy v1).
- **v4** — real-circuit era: E11–E13.
- **v5** — extended suites: E10 (expanded), E14–E18, held-out + pass-isolation.
- **v6** — review-driven supplementary experiments and analysis artifacts:
  E19–E21, E25, E10 phase-2b / real-variance, E29 smoke, SOTA benchmark,
  ceiling-model repair.
- **v7** — theory-validation and full-mode re-runs: E10p2b-full, E19-extended,
  E22–E24, E26, E29 full.
- **v8** — hardware validation (Phase-2b on backends) and full-scale Phase-2b
  v2 validation. Created for the first backend-based dataset (noise-model
  simulation on fake backends; 48-row smoke superseded by the 288-row full
  run). Real hardware (IBM Quantum) runs also belong here. Never reuse v8 for
  simulator re-runs of existing simulator experiments.

## Known Issues

1. **v5/e03 is a duplicate of v2_fixed/e03** — differs only in fidelity float
   rounding and runtime. Canonical is `v2_fixed/e03`.
2. **E1 has multiple CSV copies** — deterministic with fixed seed; copies differ
   only in fidelity precision.
3. **E18 survivorship bias** — 78 decompose_error rows + 42 fidelity=0 rows
   (120/270 = 44.4% failure). The canonical CSV retains all rows; bias-corrected
   analyses (ITT, multiple imputation, survivor-bias report) are in
   `v5/e18/derived/`. The human-readable audit is
   `v5/e18/derived/e18_bias_report.txt`: Little's MCAR rejected
   (p = 1.57e-12, missingness is MAR explained by family + width); pooled
   survivor mean 0.1800 is an **upper bound**; ITT-MI estimate 0.1351
   [0.102, 0.169]; sensitivity bracket width 0.0520. Manuscript claims must use
   the ITT-MI + bracket, not the survivor subset.
4. **E15 smoke/full data from 20260610 have negative reductions** — legitimate
   (Qiskit gate inflation on some circuits), not errors.
5. **v6 E29 smoke is superseded** by v7 E29 full (manifest marks it).
6. **v8 EHW is noise-model simulation**, not real hardware
   (`credential_audit.route = 3b_noise_model_simulation_NOT_real_hardware`);
   the canonical file is the 288-row full run (the 48-row smoke is superseded).
7. **`success` column is (near-)constant in every dataset that carries it** —
   verified 2026-07-21 by full-column scan: in the v2_fixed canonical CSVs
   (E1–E5) the column is `False` on essentially every row (E1–E4 are 100%
   `False`; E5 has exactly 1 `True` row in 6,000), while in all ten v6/v7/v8
   canonical CSVs that carry the column (E19, E25, E29 smoke + full, E10p2b,
   E10var, E10p2b-full, E19-ext, E22, E10p2b-v2) it is `True` on every row.
   The column therefore carries no cross-row information and must not be used
   as an analysis variable; it is retained for schema continuity across data
   versions. (Datasets whose schema has no `success` column — e.g. E20, E21,
   E23, E24, E26, SOTA, CeilingRepair, EHW — are unaffected.)
8. **Wave-6 rerun reconciliation (E12–E17, E19, E21)** — 8 experiments rerun
   under current code and reconciled row-by-row; canonical retained for all
   (owner decision), E14/E15/E17/E21 annotated. Unified IQP sensitivity:
   IQP-family commutation/hybrid reductions in canonical E14/E15/E16/E21 are
   systematically lower than current-code values (strengthened commutation
   predicate, review FATAL-1 repair direction — optimizer-capability
   enhancement, not a data error). E14 canonical also carries 20 fidelity = 0.0
   artifact rows on unchanged circuits (current code correctly reports 1.0).
   E18/E20 not rerun (single-machine budget); their 'source modified since run'
   warnings stand as accepted. Details: `docs/review/wave6/rerun_batch1.md`,
   `rerun_batch2.md`, `rerun_batch3.md`; rerun outputs live in `data/v9/`
   (non-canonical).

## Optimizer Naming Convention Map

The Greedy optimizer is referred to by different names across experiments due to schema evolution. This table maps all known aliases:

| Canonical Name | E1--E5 Column/Value | E4 | E10--E18 | E19 | Notes |
|:---------------|:--------------------|:---|:---------|:----|:------|
| Greedy | `optimizer_version` = `3.0.0` | `greedy` | `greedy_phase1` | `greedy_gate_cancellation` | Same algorithm (GreedyGateCancellation v3.0.0) |
| RLS | -- | `rls` | -- | -- | E4 only |
| SA | -- | `sa` | -- | -- | E4 only |
| GA | -- | `ga` | -- | -- | E4 only |
| CommutationRewriter | -- | -- | `commutation_phase2` | -- | E10/E11/E14/E16/E17/E18 |
| HybridCommuteRewrite | -- | -- | `hybrid_phase1_2` | -- | E10/E11/E14/E16/E17/E18 |
| Qiskit (baseline) | -- | -- | `none` | -- | E12/E17/E18 |

## Legacy Data (v1 - Buggy Greedy)

E1-E5 were originally run with a buggy Greedy optimizer (v1.x) where `_are_inverse()` 
did not check qubit matching. This was fixed in Greedy v3.0.0. All v1 data has been 
superseded by `data/v2_fixed/`. The original v1 data files are not included in the 
canonical release but may be available in the git history.

**Bug impact**: The buggy optimizer could incorrectly identify gate pairs on different 
qubits as inverse, leading to invalid circuit modifications. All v2_fixed data uses 
the corrected optimizer.
