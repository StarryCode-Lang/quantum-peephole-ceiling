# Phase 0 Baseline Verification Report

Date: 2026-06-17
Workspace: `D:\Desktop\Q-research`
Scope: Baseline verification only; no heavy full experiments; no commit.

## Summary

| Step | Command / Action | Outcome |
|---|---|---|
| Git status | `git status --short --untracked-files=all` | Working tree had many pre-existing modified/untracked files. Three anomalous zero-byte root files with private-use glyph names were found and removed as generated junk. |
| Pytest | `python -m pytest tests/` | Timed out after 120s, then again after 300s. Collection succeeded with 219 tests; failures were already visible in `tests/test_core.py` before timeout. |
| Unittest | `python -m unittest discover tests/` | Failed: 162 tests run in 264.757s, 14 errors. |
| Figures | `python analysis/generate_figures.py` | Completed successfully. Generated/updated figures and CSV summaries under `analysis/figures`. One `ConstantInputWarning` from Pearson correlation was emitted. |
| Release manifest | `python scripts/generate_release_manifest.py` | Completed successfully. Wrote `release/release_manifest.json`; reported 17 datasets. |

## Git Status Inspection

Initial status showed extensive modified and untracked files. Notable anomalous untracked root files:

- `\uf02a\uf02aDate\uf02a\uf02a\uf03a`
- `\uf02a\uf02aDocument`
- `\uf02a\uf02aVersion\uf02a\uf02a\uf03a`

Inspection showed all three were files, zero bytes, at repository root. They were deleted as clearly generated junk.

Final status no longer listed those glyph files. The repository still has many modified/untracked project files, including outputs touched by the requested generation scripts.

## Command Results

### 1. `python -m pytest tests/`

Outcome: Timeout.

- First run timed out after 120 seconds.
- Second run timed out after 300 seconds.
- Pytest environment:
  - Python 3.12.12
  - pytest 8.2.2
  - plugins: anyio 4.13.0, cov 5.0.0
- Collection succeeded: 219 tests.
- Progress before timeout included visible failures in `tests/test_core.py`:
  - `tests/test_commutation_bug_reproduction.py` completed with 9 passing tests.
  - `tests/test_core.py` showed multiple `F` markers before timeout.

Next action: rerun targeted failing tests with shorter scope, for example `python -m pytest tests/test_core.py -x -vv`, then address first failure before rerunning full suite.

### 2. `python -m unittest discover tests/`

Outcome: Failed.

- Ran 162 tests in 264.757 seconds.
- Result: `FAILED (errors=14)`.
- Repeated deprecation warnings from Qiskit `TwoLocal`, `NLocal`, and `BlueprintCircuit` were emitted from `src/circuits/real_benchmarks.py:159` and installed Qiskit internals.

Primary error pattern:

```text
TypeError: GreedyGateCancellation.__init__() got an unexpected keyword argument 'enable_numeric_commutation'
```

Affected tests included:

- `test_core.TestCeilingAware.test_reduction_parity_across_benchmarks` for families `QFT`, `GHZ`, `CNOT`, `BV`
- `test_core.TestCeilingAware.test_reduction_parity_on_cnot_chain`
- `test_core.TestCeilingAware.test_reduction_parity_on_random_circuit`
- `test_core.TestCommutationRewriterCorrectness.test_adjacent_pair_handled_by_hybrid`
- `test_core.TestCommutationRewriterCorrectness.test_multiple_cancellations_in_sequence`
- `test_core.TestCommutationRewriterCorrectness.test_unitary_preservation_hybrid_random`
- `test_core.TestExtendedMetrics.test_extended_metrics_on_real_circuit`
- `test_core.TestIntegration.test_all_optimizers_on_random_circuit`
- `test_core.TestPerformance.test_hybrid_runtime_small_circuit`
- `test_core.TestPhase2Optimizer.test_hybrid_on_cnot_chain`
- `test_core.TestPhase2Optimizer.test_hybrid_optimizer_runs`

Traceback source:

```text
src/optimisation/phase2/commutation_rewriter.py:158
self.phase1 = GreedyGateCancellation(max_iterations=self.max_iterations,
TypeError: GreedyGateCancellation.__init__() got an unexpected keyword argument 'enable_numeric_commutation'
```

Next action: reconcile `HybridCommuteRewrite` / `CommutationRewriter` constructor arguments with `GreedyGateCancellation.__init__`, either by adding supported parameter handling to `GreedyGateCancellation` or removing/renaming the unsupported argument at the callsite.

### 3. `python analysis/generate_figures.py`

Outcome: Passed.

Data loaded:

- E1: 25000 records
- E2: 2100 records
- E3: 12000 records; 38 dropped by fidelity filter, 11962 remaining
- E4: 400 records
- E5: 6000 records
- E10: 1905 records
- E11: 426 records; 3 dropped, 423 remaining
- E12: 568 records
- E14: 2130 records; 20 dropped, 2110 remaining
- E15: 994 records
- E16: 696 records
- E17: 755 records
- E18: 270 records; 42 dropped, 228 remaining

Warning:

```text
analysis/generate_figures.py:742: ConstantInputWarning: An input array is constant; the correlation coefficient is not defined.
```

Generated/updated outputs included:

- `analysis/figures/fig01_phase_transition.png`
- `analysis/figures/fig02_scaling.png`
- `analysis/figures/fig03_algorithm_comparison.png`
- `analysis/figures/fig04_phase1_vs_phase2.png`
- `analysis/figures/fig05_threshold_sensitivity.png`
- `analysis/figures/fig06_fidelity_distribution.png`
- `analysis/figures/fig07_landscape.png`
- `analysis/figures/fig08_fdr_correction.png`
- `analysis/figures/fig08b_real_circuit_optimizer_comparison.png`
- `analysis/figures/fig09_compiler_baseline_comparison.png`
- `analysis/figures/fig10_structural_ceiling_gap.png`
- `analysis/figures/fig11_extended_benchmark_heatmap.png`
- `analysis/figures/fig12_multi_compiler_comparison.png`
- `analysis/figures/fig13_window_scaling_curves.png`
- `analysis/figures/fig14_connectivity_ceiling.png`
- `analysis/figures/fig15_qiskit_pass_waterfall.png`
- `analysis/figures/fig16_qiskit_pass_family_heatmap.png`
- `analysis/figures/fig17_qiskit_pass_interaction.png`
- `analysis/figures/statistical_summary.csv`
- `analysis/figures/fdr_correction_results.csv`
- `analysis/figures/e4_effect_sizes.csv`

Statistical testing summary:

- Number of hypothesis tests: 15
- BH-FDR alpha: 0.05
- Significant after correction: 11 / 15

Next action: review whether generated figure/CSV diffs are expected before committing in a separate explicit commit step.

### 4. `python scripts/generate_release_manifest.py`

Outcome: Passed.

Output:

```text
Release manifest written to D:\Desktop\Q-research\release\release_manifest.json
Datasets: 17
```

Next action: inspect `release/release_manifest.json` diff for expected path/hash/count changes.

## Follow-up Fix and Rerun

After the initial failure report, the optimizer stack was corrected and rerun:

| Command | Outcome |
|---|---|
| `python -m pytest tests/test_commutation_bug_reproduction.py::TestNumericCommutationFallback tests/test_core.py::TestCommutation tests/test_phase2b_template_matcher.py -q` | Passed: 11 tests in 0.95s. |
| `python -m pytest tests/test_core.py::TestIntegration::test_all_optimizers_on_random_circuit tests/test_core.py::TestGACrossoverFix -q` | Passed: 4 tests in 272.31s. |
| `python -m pytest tests/ -q` | Passed: 219 tests, 42 warnings, in 383.14s. |
| `python -m unittest discover tests/` | Passed: 162 tests in 380.179s. |

The earlier `GreedyGateCancellation.__init__()` API mismatch is resolved. The Phase-2b template matcher conflict was rerun and passed. A GA fidelity regression exposed by pytest was also resolved before the full rerun.

## Failures and Risks

1. The baseline Python test suites are now green after the follow-up fixes.
2. Figure generation and release manifest generation modified tracked/generated files; these should be reviewed before any future commit.
3. Qiskit deprecation warnings indicate future compatibility risk for `TwoLocal` usage.
4. Full E19/E20/E21 production experiments and E18 rerun remain deferred; current evidence for those items must remain planned, metadata-only, smoke-only, or caveated as applicable.

## Recommended Next Actions

1. Review generated artifact diffs from `analysis/figures` and `release/release_manifest.json`.
2. Address or suppress known Qiskit deprecations in a separate maintenance change.
3. Run E19/E20/E21 and E18 production reruns only with explicit compute budget and time allocation.
