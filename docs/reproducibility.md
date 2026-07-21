# Reproducibility

This repository supports lightweight verification, smoke reproduction, and full experiment reruns. Full reruns may take hours and are not required for routine engineering checks.

## Environment

Recommended Python: 3.12 (data was generated on Python 3.12.12; see `release/release_manifest.json`).

Conda setup:

```bash
conda env create -f environment.yml
conda activate q-research
```

Pip setup:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Lightweight checks

```bash
python -m pytest tests/ -q
python -m py_compile src/optimisation/base.py src/optimisation/phase2/commutation_rewriter.py scripts/reproduce_all.py
```

Data integrity verification (the same command CI runs in the `verify-data-integrity` job):

```bash
python scripts/reproduce_all.py --verify
```

`--verify` checks every canonical CSV listed in `release/release_manifest.json` for existence, SHA-256 checksum, and exact row count, then runs per-experiment structural checks (metadata presence, required CSV columns, and source-hash drift warnings). Any missing file, checksum mismatch, or row-count mismatch fails the command with a non-zero exit code.

## Smoke reproduction

Use the project reproduction entry point for selected experiments or smoke defaults:

```bash
python scripts/reproduce_all.py --tests
python scripts/reproduce_all.py --experiments E10 E11 E12
```

Individual experiment scripts under `experiments/` may expose their own smoke/full flags. Check each script before running full-scale jobs.

## Full reproduction

A full rerun should use a clean environment, fixed package versions, and explicit hardware/runtime notes:

```bash
python scripts/reproduce_all.py --tests --figures --verify
```

Full E1-E29 reruns are compute-sensitive. `python scripts/reproduce_all.py --all` runs the test suite, every registered experiment in pinned `--mode smoke`, figure generation, and data verification; it is a fast end-to-end check, not a full-data regeneration. For full-scale reruns, invoke the individual experiment scripts directly with `--mode full` (see the `full_experiment_entrypoints` list in `release/release_manifest.json`). Record CPU, RAM, OS, Python version, Qiskit version, command lines, runtime, and any skipped optional compiler dependencies.

## Effect size reporting

Cliff's delta (non-parametric) and Hedges' g (bias-corrected Cohen's d) are computed for all pairwise optimizer comparisons using the canonical implementations in `analysis/phase1_statistics/effect_size.py`. Three scripts produce the effect-size outputs:

- `analysis/generate_figures.py` — integrates effect sizes into the FDR correction table (`analysis/figures/fdr_correction_results.csv`) and writes E4 pairwise comparisons to `analysis/figures/e4_effect_sizes.csv`. The `_pairwise_effect_sizes` helper computes Cliff's delta and Hedges' g independently (separate try/except blocks) so that a zero-variance failure in Hedges' g does not suppress the Cliff's delta result.
- `analysis/generate_effect_sizes.py` — standalone script that loads E1, E4, E10, E14, E19 and writes the machine-readable `analysis/figures/effect_sizes.csv` plus the formatted `analysis/figures/effect_sizes_summary.md`.
- `analysis/summarize_effect_sizes.py` — extracts the effect-size columns from `fdr_correction_results.csv` into `analysis/figures/effect_sizes_summary.csv`.

Coverage for the primary experiments: E4 (6 pairwise optimizer comparisons), E10 (Phase-1 vs Phase-2a), E11 (max pairwise across circuit families), E14 (16 per-family comparisons against the random baseline).

## Fidelity fallback characterization

Fidelity is estimated by random-state overlap sampling where feasible. When that path fails — for example for circuits larger than `max_qubits_fidelity`, where exact comparison is infeasible — `BaseOptimizer` falls back to a clearly labeled Jaccard-style structural heuristic in `src/optimisation/base.py`. The code comments there state explicitly that this heuristic ignores gate order, qubit assignment, and angles, and that its correlation with true average gate fidelity has not been characterized. A standalone characterization script (`scripts/characterize_fidelity_fallback.py`, writing reports to `docs/verification/`) is planned but is **not shipped in this release**; treat fallback-path fidelity values as heuristic estimates, not verified fidelities.

## Numerical commutation fallback

`BaseOptimizer._gates_commute` remains rule-based by default. Numerical commutator checking is opt-in via `enable_numeric_commutation=True` or the per-call `use_numeric_fallback=True` parameter. It is bounded to gates whose combined support is at most two qubits and uses `numpy.allclose(..., atol=commutation_tolerance, rtol=0)`. The default tolerance is `DEFAULT_PRECISION` (`1e-10`).

## Lock files

This repository ships three dependency specification files:

- `requirements-lock.txt` — the canonical dependency lock, generated by `pip-compile --generate-hashes` on Python 3.12. It pins every transitive dependency with cryptographic hashes and is the authoritative source for reproducible installs.
- `requirements.txt` — the pinned top-level specification. Every package is pinned with `==` to the exact version resolved in `requirements-lock.txt`.
- `environment.yml` — the conda mirror of `requirements.txt`, targeting Python 3.12 with the same pinned versions.

For maximal reproducibility, install directly from the lock file:

```bash
python -m pip install -r requirements-lock.txt
```

After changing `requirements.txt`, regenerate the lock with `pip-tools` on Python 3.12 (this is exactly how the shipped lock was produced):

```bash
python -m piptools compile --generate-hashes --output-file=requirements-lock.txt requirements.txt
```

## Current limitations

- Full experiment reruns are expensive and were not run as part of lightweight engineering verification.
- Optional compiler dependencies such as `pytket` may be platform-sensitive.
- The standalone fidelity-fallback characterization script is not yet shipped; fallback-path fidelities are heuristic estimates (see above).
- Numerical commutation fallback can change optimization opportunities and should be reported separately from rule-based baseline results.
- Some planned experiments and multi-compiler comparisons are documented as deferred or metadata-only in project docs.
- `scripts/reproduce_all.py --verify` reports "source file(s) modified since data generation" warnings for 11 experiments (E12–E21 and E25; 10–11 source files each, all under `src/optimisation/`). These stem from legitimate improvements to optimizer/analysis code made after the canonical data was generated, not from data tampering. They have been evaluated and are accepted as-is: the canonical datasets are anchored by the numbers quoted in the manuscript and are intentionally not rerun, so the warnings remain visible in verification output by design.

## Figure regeneration

All 17 manuscript figure PDFs (plus the companion summary CSVs) regenerate from a single entry point:

```bash
# Git Bash, from the repo root
/d/Downloads/miniforge3/python analysis/generate_figures.py
```

- Runtime: ~51 s on the reference machine (Windows, Python 3.12). Exit code 0 and the final log section `ALL FIGURES GENERATED` listing `fig01` ... `fig17` indicate success.
- **Do not use the bare `python` on PATH** — that is a different runtime without the project dependencies (qiskit etc.). The project interpreter is `/d/Downloads/miniforge3/python`.
- All outputs land in `analysis/figures/` (resolved via `src/config.py`: `PROJECT_ROOT/analysis/figures`; no absolute paths are hard-coded).

### Figure PDFs (17)

| # | File | Experiment / data | Content |
|---|------|-------------------|---------|
| 1 | `fig01_phase_transition.pdf` | E1 (`data/v2_fixed/e01`) | Mean gate reduction vs circuit depth, bootstrap 95% CI band |
| 2 | `fig02_scaling.pdf` | E3 (`data/v2_fixed/e03`) | Reduction and success rate vs qubit count (2 panels) |
| 3 | `fig03_algorithm_comparison.pdf` | E4 (`data/v2_fixed/e04`) | Optimizer comparison: reduction + runtime (2 panels) |
| 4 | `fig04_phase1_vs_phase2.pdf` | E10 (`data/v5/e10`) | Phase-1 vs Phase-2 grouped bars per family |
| 5 | `fig05_threshold_sensitivity.pdf` | E1/E2/E3/E5 | Success rate vs threshold, log-log |
| 6 | `fig06_fidelity_distribution.pdf` | E1/E2/E3/E5 | Fidelity histograms (2x2 panels) |
| 7 | `fig07_landscape.pdf` | E5 (`data/v2_fixed/e05`) | Perturbation landscape: scatter + boxplot (2 panels) |
| 8 | `fig08_fdr_correction.pdf` | all (p-value collection) | Raw vs BH-adjusted p-values, log scale |
| 8b | `fig08b_real_circuit_optimizer_comparison.pdf` | E11 + E14 | Per-family mean reduction, sorted bars |
| 9 | `fig09_compiler_baseline_comparison.pdf` | E12 (`data/v4/e12`, no-coupling-map) | Qiskit opt levels 0-3 x 15 families; extreme negative bars clipped + annotated |
| 10 | `fig10_structural_ceiling_gap.pdf` | E13 (`data/v4/e13`) | Structural upper bound (proxy) vs observed best reduction |
| 11 | `fig11_extended_benchmark_heatmap.pdf` | E14 (`data/v5/e14`) | 15 families x 3 optimizers heatmap, cividis |
| 12 | `fig12_multi_compiler_comparison.pdf` | E15 (`data/v5/e15`) | Best reduction per family: custom vs Qiskit vs Cirq vs tket |
| 13 | `fig13_window_scaling_curves.pdf` | E16 (`data/v5/e16`) | Window-size saturation curves, color x marker encoding |
| 14 | `fig14_connectivity_ceiling.pdf` | E17 (`data/v5/e17`) | Best reduction per family under linear / grid / heavy-hex |
| 15 | `fig15_qiskit_pass_waterfall.pdf` | `data/v5/qiskit_pass_isolation.csv` + E15 | Per-pass effectiveness per family; full-pipeline reference line |
| 16 | `fig16_qiskit_pass_family_heatmap.pdf` | pass isolation CSV | Pass x family mean-reduction heatmap, cividis |
| 17 | `fig17_qiskit_pass_interaction.pdf` | pass isolation CSV | Pass divergence + co-benefit matrices, cividis / viridis |

### Companion CSVs

| File | Producer |
|------|----------|
| `statistical_summary.csv` | `generate_figures.py` (E1-E5 summary + FDR appendix) |
| `fdr_correction_results.csv` | `generate_figures.py` (BH-FDR with effect sizes) |
| `e4_effect_sizes.csv` | `generate_figures.py` (E4 pairwise Cliff's delta / Hedges' g) |
| `qiskit_pass_analysis_summary.csv` | `generate_figures.py` via the shared helper `qiskit_pass_analysis.save_summary_csv` |

Other CSVs in `analysis/figures/` (`effect_sizes*.csv`, `optimizer_vs_compiler.csv`, `unified_summary.csv`) are produced by `analysis/generate_effect_sizes.py`, `analysis/summarize_effect_sizes.py`, and `analysis/build_baseline_table.py` respectively, not by the figure script.

### Input data dependencies

Resolution rule: for each prefix the latest `_full_` CSV in the directory is used (see `load_latest_csv`). The currently selected files match `data/DATA_CANONICAL.md`:

| Data | Canonical file |
|------|----------------|
| E1-E5 | `data/v2_fixed/e0{1..5}/e0{1..5}_*_full_*.csv` |
| E11 | `data/v4/e11/e11_*_full_*.csv` |
| E12 | `data/v4/e12/e12_compiler_baseline_e12_full_20260626_000134_nocoupling.csv` (fair no-coupling-map mode) |
| E13 | `data/v4/e13/e13_structural_ceiling_e13_full_20260609_043322.csv` |
| E10, E14-E18 | `data/v5/e{10,14,...,18}/e*_*_full_*.csv` |
| Pass isolation | `data/v5/qiskit_pass_isolation.csv` (100 rows, 5 families, 4 passes) |

A fidelity quality filter (`fidelity >= 0.99`) is applied to every loaded experiment before plotting; dropped-row counts are printed to the log.

### Code dependencies

- `src/config.py` — path resolution (`PROJECT_ROOT`, `DATA_ROOT`, `FIGURES_DIR`).
- `analysis/phase1_statistics/` — `multiple_comparison.benjamini_hochberg`, `effect_size.cliffs_delta` / `hedges_g`.
- `analysis/qiskit_pass_analysis.py` — Figures 15-17 reuse its data helpers so both scripts compute identical matrices. The plotting code for Figures 15-17 lives in `generate_figures.py` (canonical figure source); the older plotting functions in `qiskit_pass_analysis.py` still work but use the pre-wave-1 style (SEM error bars in fig15).
- Python packages: numpy, pandas, scipy, matplotlib, seaborn (pinned versions per project environment).

### Figure style conventions (enforced since 2026-07-20)

1. **Error bars**: bootstrap 95% CI of the mean, B = 10,000 resamples, `seed = 42`, matching the manuscript protocol (`bootstrap_ci_errors()`, a vectorized percentile bootstrap statistically equivalent to `phase1_statistics.bootstrap.bootstrap_ci`).
2. **Palette**: Okabe-Ito colorblind-safe palette (Wong, *Nature Methods* 2011), exposed as `CB` / `C_PRIMARY` ... `C_ACCENT` / `CB4` in the script.
3. **Colormaps**: perceptually uniform, colorblind-safe only — `cividis` (fig11, fig16, fig17-left), `viridis` (fig17-right). `RdYlGn`, `husl`, `tab20` are banned; fig13 uses 8 colors x 2 markers redundant encoding.
4. **Math**: axis labels and annotations support LaTeX-style math via mathtext (`mathtext.fontset = dejavusans`).
5. **Typography / embedding**: unified `rcParams` (axes label 11 pt, tick 9 pt, legend 9 pt), and `pdf.fonttype = 42` (TrueType embedding; journals reject Type-3 fonts).
6. **Figure-specific honest-data conventions**: fig09 clips/hatches/annotates QuantumWalk/Grover bars reaching -5,761% (basis-translation overhead); fig10 uses explicit columns `structural_upper_bound_reduction` (proxy) and `observed_best_reduction` (observed).

### Figure verification checklist

1. Run the command above; expect exit 0 and 17 PDFs in the final log block.
2. Confirm timestamps: all `fig*.pdf` share the run time.
3. Spot-render any PDF, e.g. with PyMuPDF (`d[0].get_pixmap(dpi=110)`).
4. Expected log notes: `ConstantInputWarning` for E2 is intentional (zero-variance reduction under LBL; handled honestly, p treated as 1.0).

Overwrites are atomic in practice (the script writes each PDF in one `savefig` call). The pre-regeneration backup `analysis/figures/_bak-20260720/` was removed in the 2026-07-21 cleanup; previous figure versions remain recoverable from git history.
