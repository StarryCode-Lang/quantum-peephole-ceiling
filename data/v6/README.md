# v6 Data Directory

> **Status**: Updated  
> **Date**: 2026-06-20

This directory contains artifacts from experiments E19-E21, which are supplementary experiments developed during Phase 7-8 auditing. E19 has been completed as a full canonical run; E20 and E21 remain preliminary/smoke-only.

## Experiments

| Exp | Status | Data | Notes |
|-----|--------|------|-------|
| E19 | **COMPLETE (full)** | `e19_wcl_listing_full_e19_full_20260620_123825.csv` (10,000 rows) | Full canonical WCL vs LBL comparison; WCL mean reduction 7.83% vs LBL 0.0000%; confirms listing-model dependency (Theorem 1a) |
| E20 | **SCRIPTED / ENV-DEPENDENT** | Metadata only | Multi-compiler comparison with Qiskit, optional Cirq/t\|ket>; missing compilers are reported in metadata |
| E21 | **COMPLETE (smoke)** | 2 CSVs; metadata reports 342 comparison rows | Ceiling-aware optimizer comparison; smoke mode only, not full canonical evidence |

## Notes

- E19 is now a confirmed canonical result: 5,000 random universal circuits (n=5, depths 1-50, 100 trials/depth) evaluated under both LBL and WCL listing models (10,000 total rows)
- E20 smoke runs can validate compiler availability and custom optimizers without requiring every optional backend; missing compilers are recorded in metadata
- E21 provides smoke-mode preliminary evidence for the ceiling-aware optimization strategy; specific speedup values should not be treated as full-scale results
- Full-mode E20/E21 runs require a fully configured compiler environment; `requirements.txt` includes pip entries for Cirq/pytket, while conda users may need additional pip installation for pytket packages
