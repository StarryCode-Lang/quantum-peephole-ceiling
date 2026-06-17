# v6 Data Directory

> **Status**: Experimental / In Progress  
> **Date**: 2026-06-14

This directory contains preliminary artifacts from experiments E19-E21, which are supplementary experiments developed during Phase 7-8 auditing. These are NOT part of the core manuscript dataset (v2-v5) and should not be treated as full-scale evidence until the corresponding full-mode runs are completed.

## Experiments

| Exp | Status | Data | Notes |
|-----|--------|------|-------|
| E19 | **NOT YET RUN** | No data | Planned experiment; directory created but not populated |
| E20 | **METADATA ONLY** | `metadata.json` only | Multi-compiler full comparison (Qiskit + Cirq + t|ket>); experiment defined but CSV not yet generated |
| E21 | **COMPLETE (smoke)** | 2 CSVs; metadata reports 342 comparison rows | Ceiling-aware optimizer comparison; smoke mode only, not full canonical evidence |

## Notes

- E19 and E20 are documented in the manuscript as "Future Work" items
- E21 provides smoke-mode preliminary evidence for the ceiling-aware optimization strategy; specific speedup values should not be treated as full-scale results
- Full-mode E20/E21 runs require a fully configured compiler environment; `requirements.txt` includes pip entries for Cirq/pytket, while conda users may need additional pip installation for pytket packages
