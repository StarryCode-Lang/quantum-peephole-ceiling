# E18 — Clifford+T Decomposition Experiment

> **Survivorship-biased dataset.** 44.4% trial failure rate (120/270). All
> conclusions based on the 150 surviving trials. See `e18_survivor_bias_report.csv`
> and the caveat at the end of this README.

## Canonical vs derived files

| File | Role | Rows |
|------|------|------|
| `e18_clifford_t_e18_full_20260610_052140.csv` | **CANONICAL** — original experiment output | 270 |
| `e18_corrected.csv` | Survivor-bias-corrected (decompose/fidelity failures excluded) | 270 |
| `e18_fidelity_verified.csv` | Fidelity-validated subset only | 270 |
| `e18_imputation_draws.csv` | Multiple imputation draws for missing reductions | 2100 |
| `e18_itt_report.csv` | Intention-to-treat analysis summary | 4 |
| `e18_littles_mcar.json` | Little's MCAR test result | — |
| `e18_survivor_bias_report.csv` | Bias summary by optimizer/cohort | 8 |
| `e18_fidelity_summary.json` | Fidelity distribution summary | — |

The canonical file is the source of truth. All other files are derived from it
by `experiments/e18_bias_correction.py`, `experiments/e18_fidelity_verification.py`,
and `scripts/e18_survivor_bias_report.py`. Regenerate from canonical if any
derived file is stale.

## Columns (canonical CSV, 31 columns)

`schema_version`, `experiment_id`, `run_id`, `circuit_id`, `circuit_family`,
`n_qubits`, `depth`, `gate_set`, `basis_gates`, `optimizer`, `original_size`,
`optimized_size`, `reduction`, `fidelity`, `success`, `runtime_seconds`,
`seed`, `decompose_error`, `fidelity_check`, `algorithm`, `timestamp_utc`,
... (see CSV header for full list)

## Survivorship bias caveat

- **Total trials**: 270
- **Failed trials**: 120 (78 `decompose_error` + 42 `fidelity=0`) — **44.4% failure rate**
- **Surviving trials**: 150

All quantitative claims in the manuscript that draw on E18 must carry the
annotation "(survivorship-biased; 44.4% failure rate)" or equivalent.

**Bias direction**: conservative. Circuits that fail Clifford+T decomposition
likely have *higher* structural complexity; their exclusion means the reported
mean reduction is likely an *overestimate* of the true population mean. The
bias direction is stated to prevent misinterpretation, not to dismiss the finding.

The ITT (intention-to-treat) analysis in `e18_itt_report.csv` treats failed
trials as zero reduction and provides a lower-bound estimate. The imputation
draws in `e18_imputation_draws.csv` (2100 rows = 270 trials × ~8 draws) provide
a multiple-imputation estimate under a missing-at-random assumption tested by
Little's MCAR (`e18_littles_mcar.json`).

## Generation

```bash
python experiments/e18_clifford_t/run.py --mode full
python experiments/e18_fidelity_verification.py
python experiments/e18_bias_correction.py
python scripts/e18_survivor_bias_report.py
```

Seed: 42 (project default). Python 3.12.12, Qiskit 2.4.1.
