# Reproducibility

This repository supports lightweight verification, smoke reproduction, and full experiment reruns. Full reruns may take hours and are not required for routine engineering checks.

## Environment

Recommended Python: 3.12 (matching the data-generation environment recorded in `release/release_manifest.json`).

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
python -m pytest tests/test_core.py tests/test_statistical_analysis.py tests/test_commutation_bug_reproduction.py
python -m py_compile src/optimisation/base.py src/optimisation/phase2/commutation_rewriter.py scripts/characterize_fidelity_fallback.py
```

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

Full E1-E18 reruns are compute-sensitive. Record CPU, RAM, OS, Python version, Qiskit version, command lines, runtime, and any skipped optional compiler dependencies.

## Effect size reporting

Cliff's delta (non-parametric) and Hedges' g (bias-corrected Cohen's d) are computed for all pairwise optimizer comparisons using the canonical implementations in `analysis/phase1_statistics/effect_size.py`. Three scripts produce the effect-size outputs:

- `analysis/generate_figures.py` — integrates effect sizes into the FDR correction table (`analysis/figures/fdr_correction_results.csv`) and writes E4 pairwise comparisons to `analysis/figures/e4_effect_sizes.csv`. The `_pairwise_effect_sizes` helper computes Cliff's delta and Hedges' g independently (separate try/except blocks) so that a zero-variance failure in Hedges' g does not suppress the Cliff's delta result.
- `analysis/generate_effect_sizes.py` — standalone script that loads E1, E4, E10, E14, E19 and writes the machine-readable `analysis/figures/effect_sizes.csv` plus the formatted `analysis/figures/effect_sizes_summary.md`.
- `analysis/summarize_effect_sizes.py` — extracts the effect-size columns from `fdr_correction_results.csv` into `analysis/figures/effect_sizes_summary.csv`.

Coverage for the primary experiments: E4 (6 pairwise optimizer comparisons), E10 (Phase-1 vs Phase-2a), E11 (max pairwise across circuit families), E14 (16 per-family comparisons against the random baseline).

## Fidelity fallback characterization

The fallback characterization is not automatic. Run it manually when auditing fidelity estimates:

```bash
python scripts/characterize_fidelity_fallback.py
```

It writes `docs/verification/fidelity_fallback_characterization_<date>.md`.

## Numerical commutation fallback

`BaseOptimizer._gates_commute` remains rule-based by default. Numerical commutator checking is opt-in via `enable_numeric_commutation=True` or the per-call `use_numeric_fallback=True` parameter. It is bounded to gates whose combined support is at most two qubits and uses `numpy.allclose(..., atol=commutation_tolerance, rtol=0)`. The default tolerance is `DEFAULT_PRECISION` (`1e-10`).

## Lock files

No exact lock file is committed in this snapshot. See `requirements-lock-placeholder.txt` for generation instructions. Do not treat that placeholder as resolved dependency evidence.

## Current limitations

- Full experiment reruns are expensive and were not run as part of lightweight engineering verification.
- Optional compiler dependencies such as `pytket` may be platform-sensitive.
- Fidelity fallback characterization currently uses small synthetic circuits unless canonical outputs are added explicitly.
- Numerical commutation fallback can change optimization opportunities and should be reported separately from rule-based baseline results.
- Some planned experiments and multi-compiler comparisons are documented as deferred or metadata-only in project docs.
