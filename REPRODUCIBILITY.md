# Reproducibility

This repository supports lightweight verification, smoke reproduction, and full experiment reruns. Full reruns may take hours and are not required for routine engineering checks.

## Environment

Recommended Python: 3.10.

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
