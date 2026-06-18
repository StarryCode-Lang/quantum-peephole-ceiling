# CRITICAL Bug Fixes Log

This log records every fix applied during the CRITICAL bug-fix pass on the
Q-research quantum circuit optimization project. Bugs are grouped A–K in the
order they were fixed. Line numbers refer to the file state **after** each fix
(where they shifted, the original bug-list line is noted in parentheses).

---

## Batch A — `experiments/e10_phase1_vs_phase2/analyze.py`

### Bug #1 — `or True` defeating the cumulant filter
- **File:** `experiments/e10_phase1_vs_phase2/analyze.py`
- **Location:** Binder cumulant dict comprehension (originally lines 301–304).
- **Change:** Removed `or True` from the comprehension condition so it reads
  `{k: v for k, v in c.items() if k != "cumulant"}`. The `or True` previously
  made the filter a no-op, leaking the raw `cumulant` key into the output.

### Bug #2 — Binder cumulant not grouped by `circuit_family`
- **File:** `experiments/e10_phase1_vs_phase2/analyze.py`
- **Location:** Binder cumulant block (originally lines 294–310).
- **Change:** Wrapped the computation in a `for family, sub in
  real_sub.groupby('circuit_family'):` loop, storing per-family results as
  `report["binder_cumulants"][family]` and
  `report["binder_cumulants_summary"][family]`. Added backward-compatible
  fallback to the original aggregate logic when `circuit_family` is absent.

---

## Batch B — `analysis/phase2_threshold_sensitivity/run.py`

### Bug #3 — `PROJECT_ROOT` undefined
- **File:** `analysis/phase2_threshold_sensitivity/run.py`
- **Location:** Module level (added near the top, after the
  `phase1_statistics.core` import); used at the figure-save and CSV-save
  call sites (originally lines 118 and 143).
- **Change:** Added module-level alias `PROJECT_ROOT =
  Path(__file__).resolve().parent.parent.parent` so the upper-case references
  resolve. The lower-case `project_root` inside `load_all_experiments` is
  unchanged.

---

## Batch C — `analysis/generate_figures.py`

### Bug #4 — Pearson correlation with misaligned `dropna()`
- **File:** `analysis/generate_figures.py`
- **Location:** E2 Pearson block (originally lines 666–668).
- **Change:** Replaced independent `e2['entanglement_density'].dropna()` /
  `e2['reduction'].dropna()` (which misalign rows) with a joint
  `e2_valid = e2[['entanglement_density', 'reduction']].dropna()` and
  correlation on the aligned columns. A full file scan confirmed this was the
  only pearsonr/spearmanr call with the broken pattern.

### Bug #12 — Effect sizes not integrated into p-value reporting
- **File:** `analysis/generate_figures.py`
- **Location:** Hypothesis-test section (originally lines 643–806) and FDR
  summary section (originally lines 854–994).
- **Change:** Added a parallel `effect_size_collection` and a
  `_pairwise_effect_sizes(groups)` helper built on
  `phase1_statistics.core.cliffs_delta` / `hedges_g`. After every hypothesis
  test (E1–E18) an effect-size entry is appended. The FDR results CSV
  (`fdr_correction_results.csv`), the printed table, the statistical summary
  CSV, and the Figure 8 annotation now include Cliff's delta / Hedges' g
  columns. Removed the stale "effect size not yet integrated" comments.

---

## Batch D — `src/optimisation/base.py`

### Bug #5 — `success_reduction` threshold too strict (20%)
- **File:** `src/optimisation/base.py`
- **Location:** `BaseOptimizer.__init__` (originally lines 129–138) and
  `_is_success` (originally lines 295–297).
- **Change:** Lowered the default `success_reduction` from `0.20` to `0.05`
  (aligning with `data/DATA_CANONICAL.md`). Redefined `_is_success` to check
  fidelity compliance only, and added a new `_is_meaningful(reduction,
  fidelity)` method that additionally requires crossing `success_reduction`.
  Added docstring explaining the threshold rationale and the
  success-vs-meaningful distinction. `success_reduction` parameter retained
  for backward compatibility.

### Bug #11 — `_gates_commute` only checks sufficient conditions
- **File:** `src/optimisation/base.py`
- **Location:** `_gates_commute` (originally lines 320–396).
- **Change:** Updated the docstring to explicitly mark the method as
  **Conservative** ("returns True only for proven commuting cases; may return
  False for actually-commuting gate pairs … Phase-2 reduction is a LOWER
  BOUND"). Added two new sufficient-condition checks: (a) two SWAP gates on
  the same qubit pair commute (unordered-set match), and (b) two CZ gates on
  the same qubit pair commute (CZ is diagonal). No numerical unitary
  commutator test is performed (left as future work).

---

## Batch E — `data/DATA_CANONICAL.md`

### Bug #6 — References to non-existent files
- **File:** `data/DATA_CANONICAL.md`
- **Location:** E01–E05 table rows (originally lines 17–21).
- **Change:** Updated file names to the actual on-disk names:
  - E1 → `e01_phase_transition_v2_20260613_132653.csv`
  - E2 → `e02_entanglement_density_v2_20260613_130455.csv`
  - E3 → unchanged (`e03_scaling_v2_20260611_224540.csv`)
  - E4 → `e04_algorithm_comparison_v2_20260613_132653.csv`
  - E5 → `e05_landscape_v2_20260613_130355.csv`

---

## Batch F — `release/release_manifest.json`

### Bug #7 — Duplicate E10 entry
- **File:** `release/release_manifest.json`
- **Location:** `datasets` array (legacy entry originally lines 40–45).
- **Change:** Deleted the legacy E10 entry (v3 `e10_phase1_vs_phase2_…627`
  rows, `legacy_v2_v3` schema). The canonical E10 entry (v5
  `e10_expanded_phase1_vs_phase2_…1905` rows, `results_v2` schema) is
  retained. Verified no other `experiment_id` is duplicated.

---

## Batch G — `analysis/phase1_statistics/core.py`

### Bug #8 — Duplicated effect-size implementations
- **File:** `analysis/phase1_statistics/core.py`
- **Location:** Module docstring, imports, `cliffs_delta` (originally lines
  154–200), `hedges_g` (originally lines 236–272), and internal callers in
  `effect_size_table` (originally lines 307–309) and the optimizer effect-size
  block (originally lines 672–673).
- **Change:** Added a DEPRECATED notice to the module docstring pointing to
  the dedicated modules. `cliffs_delta` now re-exports
  `effect_size.cliffs_delta` (Dict contract) and `hedges_g` delegates to
  `effect_size.cohens_d` returning its Dict (with the `g` key). Both return
  the unified `Dict[str, Any]` contract. Updated all internal tuple-unpacking
  callers in `core.py` to dict access. Updated
  `analysis/generate_figures.py` (`_pairwise_effect_sizes`, the summary loop,
  and the E4 pairwise loop) to dict access with try/except guards for the
  empty/zero-variance `ValueError` behavior of `effect_size.py`. Updated
  `tests/test_statistical_analysis.py` (`test_core_cliffs_delta_basic`,
  `test_core_cliffs_delta_identical`) to expect the Dict contract. `cohens_d`
  in `core.py` is intentionally left unchanged (still tuple-returning) as it
  was not in scope.
- **Callers verified:** `analysis/phase2_threshold_sensitivity/run.py` does
  not use these functions; `experiments/e10_phase1_vs_phase2/analyze.py`
  imports directly from `effect_size.py` (already Dict) and needed no change.

---

## Batch H — `scripts/phase7_statistical_remediation.py`

### Bug #9 — Observed (post-hoc) power fallacy
- **File:** `scripts/phase7_statistical_remediation.py`
- **Location:** `task_c4_power_analysis` (originally lines 560–835).
- **Change:** Removed all observed-power computation
  (`compute_power_one_sample`, `actual_power` fields, and verdict logic based
  on observed power). Replaced with: (1) **prior power** at three reference
  effect sizes (d = 0.2 / 0.5 / 0.8 for small / medium / large) evaluated at
  the actual sample size; (2) **95% CI width** of the observed mean
  reduction (t-based); (3) **required sample size** to reach power = 0.80 for
  each reference effect size. The `verdict` field is now derived from CI
  width and sample-size adequacy (whether n meets the requirement for a
  medium effect d=0.5 at 80% power), not from observed power. Added a
  docstring citing Hoenig & Heisey (2001). Observed Cohen's d is retained
  for descriptive reporting only.

### Bug #10 — Held-out feature leakage via `actual_reduction`
- **File:** `scripts/phase7_statistical_remediation.py`
- **Location:** `task_c6_held_out_validation` (originally lines 1007–1077).
- **Change:** Removed every use of `actual_reduction` as a prediction
  feature. Added `extract_structural_scalar(c)` (returns
  `predicted_gain`, the pre-optimization structural upper bound) and
  `extract_structural_vector(c)` (collects `predicted_gain`, `gate_count`,
  `n_qubits`, `depth`, `commuting_block_count`, `circuit_family` when
  present). The threshold rule is now learned and applied on structural
  scalars only. The output dict carries
  `"features": "structural-only (no target leakage) …"`, a
  `structural_feature_example`, and the interpretation string ends with
  "Features: structural-only (no target leakage)."

---

## Batch I — `experiments/e21_ceiling_aware/run.py`

### Bug #15 — Hardcoded `fidelity = 1.0`
- **File:** `experiments/e21_ceiling_aware/run.py`
- **Location:** `run_naive_pipeline` return dict (originally line 198) and
  the import block (lines 43–49).
- **Change:** Added `average_gate_fidelity` to the `real_benchmarks` import.
  Replaced `'fidelity': 1.0` with a computed value: prefer `r3.fidelity`
  (the final Phase-1 optimizer result); if missing/zero, fall back to
  `average_gate_fidelity(optimized, circuit, max_qubits=HAAR_MAX_QUBITS)`
  (mirroring `experiments/e18_clifford_t/run.py:144-148`). When exact AGF is
  infeasible for large circuits, records `NaN` rather than assuming 1.0.

---

## Batch J — `scripts/compute_new_summary.py`

### Bug #16 — Hardcoded `fidelity = 1.0` for E13
- **File:** `scripts/compute_new_summary.py`
- **Location:** E13 processing block (originally lines 137, 146, 161).
- **Change:** `df_e13["fidelity"]` is now set to `NaN` instead of `1.0`.
  Overall and per-family `mean_fidelity` use `pandas.Series.mean()` (which
  skips NaN). Added a `fidelity_note` field reporting
  `"n=X excluded due to missing fidelity"` for both the overall and each
  per-family summary. Added a comment explaining why 1.0 is not assumed.

---

## Batch K — `scripts/phase5_optimize_or_skip.py`

### Bug #17 — In-sample evaluation (train_df used for both train and eval)
- **File:** `scripts/phase5_optimize_or_skip.py`
- **Location:** Data-prep block (originally line 829) and the predictor
  train/evaluate blocks (originally lines 904–905 and the surrounding
  Rule/Threshold/Ensemble sections).
- **Change:** Added `train_test_split` to the sklearn imports. After
  constructing `train_df`, split into `train_split` / `test_split`
  (`test_size=0.3`, `random_state=42`, stratified on `worth_optimizing` when
  present). `MLPredictor.fit` and `OptimizeOrSkip.fit` (ensemble) now fit on
  `train_split`; `ThresholdPredictor.find_optimal_threshold` learns the
  threshold on `train_split`. All `evaluate_predictor` and
  `cost_benefit_analysis` calls for Rule / Threshold / ML / Ensemble now run
  on `test_split`. `ml_pred.get_cv_metrics` runs on `train_split`. Each
  predictor section prints
  `"Evaluation: held-out test set (n=<size>)"`. Non-evaluation uses of
  `train_df` (EDA summary, feature-column listing, per-circuit framework
  prediction dump, API demonstration) are intentionally left on `train_df`
  as they are out of scope for this bug.

---

## Summary

| Bug | File | Severity | Status |
|-----|------|----------|--------|
| #1  | `experiments/e10_phase1_vs_phase2/analyze.py` | CRITICAL | Fixed |
| #2  | `experiments/e10_phase1_vs_phase2/analyze.py` | CRITICAL | Fixed |
| #3  | `analysis/phase2_threshold_sensitivity/run.py` | CRITICAL | Fixed |
| #4  | `analysis/generate_figures.py` | CRITICAL | Fixed |
| #5  | `src/optimisation/base.py` | CRITICAL | Fixed |
| #6  | `data/DATA_CANONICAL.md` | CRITICAL | Fixed |
| #7  | `release/release_manifest.json` | CRITICAL | Fixed |
| #8  | `analysis/phase1_statistics/core.py` | CRITICAL | Fixed |
| #9  | `scripts/phase7_statistical_remediation.py` | CRITICAL | Fixed |
| #10 | `scripts/phase7_statistical_remediation.py` | CRITICAL | Fixed |
| #11 | `src/optimisation/base.py` | CRITICAL | Fixed |
| #12 | `analysis/generate_figures.py` | CRITICAL | Fixed |
| #15 | `experiments/e21_ceiling_aware/run.py` | CRITICAL | Fixed |
| #16 | `scripts/compute_new_summary.py` | CRITICAL | Fixed |
| #17 | `scripts/phase5_optimize_or_skip.py` | CRITICAL | Fixed |

No tests or experiments were run during this pass (code-only fixes, per
instructions). Downstream verification (running the experiment suites and
`test_statistical_analysis.py`) is recommended as the next step.
