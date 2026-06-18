# v6 Data Directory

> **Status**: Experimental / In Progress  
> **Date**: 2026-06-14

This directory contains preliminary artifacts from experiments E19-E21, which are supplementary experiments developed during Phase 7-8 auditing. These are NOT part of the core manuscript dataset (v2-v5) and should not be treated as full-scale evidence until the corresponding full-mode runs are completed.

## Experiments

| Exp | Status | Data | Notes |
|-----|--------|------|-------|
| E19 | **SCRIPTED / NOT FULL RUN** | Generated only when run locally | Supports smoke/full modes, configurable qubits, depth range, trials, and LBL/WCL selection |
| E20 | **SCRIPTED / ENV-DEPENDENT** | Generated only when run locally | Multi-compiler comparison with Qiskit, optional Cirq/t|ket>, and custom optimizers; missing compilers are reported in metadata |
| E21 | **COMPLETE (smoke)** | 2 CSVs; metadata reports 342 comparison rows | Ceiling-aware optimizer comparison; smoke mode only, not full canonical evidence; rows include fidelity source |

## Notes

- E19 and E20 are documented in the manuscript as "Future Work" items
- E19 smoke runs can be used for script validation; WCL rows use `wire_traversal=True`, LBL rows use `wire_traversal=False`
- E20 smoke runs can validate compiler availability and custom optimizers without requiring every optional backend; missing compilers are recorded in metadata
- E21 provides smoke-mode preliminary evidence for the ceiling-aware optimization strategy; specific speedup values should not be treated as full-scale results
- Full-mode E20/E21 runs require a fully configured compiler environment; `requirements.txt` includes pip entries for Cirq/pytket, while conda users may need additional pip installation for pytket packages
