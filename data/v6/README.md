# v6 Data Directory

> **Status**: Canonical v6 evidence directory
> **Date**: 2026-08-07

This directory contains canonical artifacts for E19-E21, E25, the SOTA
benchmark, and related derived analyses. Canonical status is governed by
`data/DATA_CANONICAL.md` and `release/release_manifest.json`.

## Experiments

| Exp | Status | Data | Notes |
|-----|--------|------|-------|
| E19 | **COMPLETE (canonical)** | `e19/e19_wcl_listing_full_e19_full_20260620_123825.csv` (10,000 rows) | WCL mean reduction 7.83% vs LBL 0.0000%; listing-model dependence for the recorded Universal family |
| E20 | **COMPLETE (canonical)** | `e20/multi_compiler_full.csv` (1,070 rows) | Qiskit/Cirq/t\|ket> comparison; frozen as-executed data retains documented Cirq QASM errors |
| E21 | **COMPLETE (canonical)** | `e21/ceiling_aware_comparison.csv` (1,140 rows) | Full-mode ceiling-aware comparison; predictive model remains exploratory after held-out failure |
| E25 | **COMPLETE (canonical)** | `e25/e25_industry_benchmarks_e25_industry_proxies_20260711_042550.csv` (66 rows) | Industry proxy circuits |
| SOTA | **COMPLETE (canonical aggregate)** | `sota_benchmark/aggregated/sota_comparison_aggregated.csv` (105 rows) | Multi-compiler aggregate; corrected Cirq pipeline |

## Notes

- E19 is a confirmed canonical result: 5,000 random Universal circuits (n=5,
  depths 1-50, 100 trials/depth) evaluated under both LBL and WCL listings.
- E20 canonical data remain as-executed evidence. Corrected reruns belong in
  non-canonical `data/v11/e20_corrected/` until an explicit release decision.
- E21 is full-mode canonical evidence for the recorded 15-family comparison;
  its repaired hybrid predictor remains exploratory and has a documented
  RepetitionCode generalization boundary.
- Full reruns require the optional compiler dependencies and the commands in
  `docs/reproducibility.md`.
