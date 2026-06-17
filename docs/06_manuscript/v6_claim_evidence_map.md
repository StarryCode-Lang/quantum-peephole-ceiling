# V6 Claim-Evidence Map

> **Version**: 6.0  
> **Date**: 2026-06-15  
> **Scope**: Updated for *Quantum* manuscript v5.0 — confirmed claims are limited to E1-E18 canonical optimizer data plus completed Qiskit baseline/pass-isolation. Listing-model dependency (C9) is planned/preliminary, ceiling-aware optimization (C10) is smoke-only, and Cirq/t|ket> multi-compiler analysis (C11) is metadata-only/planned.

---

## Claim-Evidence Table

| # | Claim | Evidence | Figure/Table | Support | Scope | Caveat |
|---|---|---|---|---|---|---|
| C1 | The Phase 1 ceiling is structural: every Phase-1 optimizer achieves ~0% gate reduction on circuits without adjacent inverse pairs. | E1–E5 (random), E14 (extended 15-family suite) | Fig.1 (composite: depth/density/qubit sweeps); Table 1 (family-wise summary) | Greedy Phase 1 = 0% on QFT, GHZ, BV, IQP, SurfaceCode, QAOA, HardwareEfficient, etc. | Project generators, n=3–20 (extended), depths 1–50 | Not a universal lower bound; specific to tested circuit families. Ceiling classification is listing-model-dependent (see C9). |
| C2 | Phase 2 provides context-dependent super-constant improvement on select circuit families. | E10, E14, E16 | Fig.4 (Phase 2 vs Phase 1 per family); Fig.13 (window scaling) | E14: Oracle/BV ~27.6%, RandomClifford ~22.1%, UCCSD ~1.4%; E16: improvement scales with window size | Local commutation rewriter, window w in {2,5,10,20,50} | Improvement is family-dependent; not universal across all circuit types. |
| C3 | Production compiler gap analysis reveals mechanisms beyond the prototype peephole model. | E12, E15, pass-isolation artifact | Fig.12 (Qiskit comparison); Fig.17 (Qiskit pass interaction); Table 8 (Qiskit/custom prescriptions) | Qiskit transpiler at opt levels 0–3 exceeds the prototype on selected families; Cirq and t\|ket> are planned/metadata-only and excluded from confirmed claims. | Qiskit 2.4.1; default no-backend transpilation | Hardware-specific effects not fully modeled. Cirq/t\|ket> require full CSV data before being used as evidence. |
| C4 | Phase 2 window size w controls the trade-off between optimization power and runtime. | E16 | Fig.13 (window size vs reduction, per family) | w=2: ~0%, w=5: ~1.5%, w=10: ~4.2% on full suite | Window sizes {2, 5, 10, 20, 50} | Diminishing returns beyond w=20 for most families. |
| C5 | Hardware topology constraints (linear, grid, heavy-hex) affect optimization opportunities differently. | E17 | Fig.14 (topology comparison) | Linear, grid, heavy-hex topologies on all 15 families | Simplified topology models | Real hardware has additional noise/error effects not modeled. |
| C6 | Clifford+T gate-set decomposition preserves Phase 2 optimization value. | E18 | Section 5.6.4 (Clifford+T decomposition analysis) | Decomposition to {H, S, T, CNOT}; T-count, CNOT reduction tracked | Clifford+T universal gate set | Decomposition overhead may mask original optimization opportunities. |
| C7 | Exact functionality is preserved in all canonical optimizer outputs where fidelity is computed. | E1–E21 | fidelity columns in all CSV files | Mean fidelity 1.000000 for verified datasets | Exact unitary comparison for n ≤ max_qubits_fidelity | Large circuits need sampled/process fidelity. |
| C8 | The Phase-1 reduction ceiling (Theorem 2) is formally established for bounded circuits, with the INSERTION cascade gap resolved under bounded depth and gate count. | Theory (Thm 2, Thm 2b); E1–E5 empirical validation | Open Problems section; Thm 2b proof | Thm 2b proves polynomial-time termination of INSERTION move sequences for circuits with bounded depth and gate count; empirical ceilings (E1–E5) confirm theoretical predictions | Bounded circuits: depth O(poly(n)), gate count O(poly(n)) | The unbounded INSERTION cascade remains an open problem for circuits with unbounded depth. Thm 2b resolves the practically relevant bounded case. QMA-hardness of CODP (OP1) remains a separate open theoretical motivation. |
| C9 | **NEW** Listing-model dependency: WCL-style preprocessing can expose Phase-1 opportunities hidden under LBL. | Planned WCL-E19; theoretical listing-model analysis | Table 2 (experiment registry); Section 5.2 (planned listing-model analysis) | Full WCL benchmarking is not yet collected; current quantitative WCL values are projections/smoke observations and should not be treated as confirmed results. | Planned n=3–20, 15+ circuit families | Do not use WCL as a main empirical result until full E19 CSV data exists. |
| C10 | **NEW** Ceiling-aware optimization: structural ceiling proxy can skip futile optimization passes in a smoke-mode evaluation. | E21 smoke dataset | Section 5.5 (ceiling-aware optimization); Table 7 (smoke speedup per family) | Smoke-mode E21 reports preliminary 1.9x–27x speedups with identical reduction on sampled training-family cases. | Smoke mode only (`n_rows=342` comparison rows); training families | Treat as exploratory/supplementary until full-mode E21 is collected; proxy failed held-out generalization. |
| C11 | **PLANNED** Multi-compiler mechanism analysis: Cirq and t\|ket> extensions are designed but not yet supported by canonical optimization-output CSVs. | E20 metadata only; E21 smoke unrelated to full multi-compiler comparison | S11.2 status note | Qiskit pass analysis is available; Cirq/t\|ket> values are planned projections/metadata only. | E20 metadata only | Do not claim no-single-compiler dominance or Cirq/t\|ket> percentages before full data generation. |

---

## Supporting Experiments (Legacy)

| experiment_id | description | data dir |
|---|---|---|
| E01 | Phase transition study | data/v2_fixed/e01/ |
| E02 | Entanglement density study | data/v2_fixed/e02/ |
| E03 | Scaling study | data/v2_fixed/e03/ |
| E04 | Algorithm comparison | data/v2_fixed/e04/ |
| E05 | Landscape study | data/v2_fixed/e05/ |
| E10 | Phase 1 vs Phase 2 | data/v3_extended/e10/ |
| E11 | Real-circuit benchmark (v4) | data/v4/e11/ |
| E12 | Compiler baseline (v4) | data/v4/e12/ |
| E13 | Structural ceiling proxy | data/v4/e13/ |

## v5 Experiments

| experiment_id | description | data dir | key claim |
|---|---|---|---|
| E14 | Extended benchmark suite (15 families, extended metrics) | data/v5/e14/ | C1, C2, C7 |
| E15 | Compiler comparison (custom peephole vs Qiskit) | data/v5/e15/ | C3, C7 |
| E16 | Phase 2 window-size scaling study | data/v5/e16/ | C2, C4 |
| E17 | Hardware connectivity constraints | data/v5/e17/ | C5 |
| E18 | Clifford+T gate-set experiment | data/v5/e18/ | C6, C7 |

## v5 New Experiments (Listing-Model, Ceiling-Aware, Multi-Compiler)

| experiment_id | description | data dir | key claim |
|---|---|---|---|
| WCL-E19 | Planned listing-model dependency test (WCL vs. LBL) | data/v6/e19/ | C9 planned |
| MC-E20 | Planned/metadata-only Cirq and t\|ket> extension | data/v6/e20/ | C11 planned |
| E21 | Ceiling-aware optimizer smoke study | data/v6/e21/ | C10 smoke-only |

---

## Claim Dependency Graph

```
C1 (Phase-1 ceiling) ──┬── C2 (Phase-2 advantage)
                        ├── C9 (Listing-model dependency)  ← modifies C1
                        └── C10 (Ceiling-aware optimizer)  ← builds on C1, C9

C3 (Multi-compiler gap) ── C11 (Pass-level decomposition) ← extends C3

C8 (Theorem 2 / INSERTION) ← C1 (empirical backing)
   └── Thm 2b (bounded cascade) resolves gap

C4 (Window scaling) ← C2
C5 (Topology) ← C1
C6 (Clifford+T) ← C2
C7 (Fidelity) ← all claims
```

---

## Changes from v5 to v6

| Claim | v5 Status | v6 Status | Change Description |
|-------|-----------|-----------|-------------------|
| C1 | Ceiling under LBL only | Ceiling under LBL; revised under WCL | Caveat added: ceiling classification is listing-model-dependent |
| C3 | Qiskit only | Qiskit only confirmed; Cirq/t\|ket> planned | E20 metadata-only; do not claim completed multi-compiler evidence |
| C8 | INSERTION cascade gap open (empirically validated, not formally proven) | Bounded INSERTION cascade resolved (Thm 2b) | Upgraded: formal proof for bounded circuits; unbounded case remains open |
| C9 | Not present | Listing-model dependency hypothesis (WCL vs. LBL) | Planned/preliminary extension; full E19 data pending |
| C10 | Not present | Ceiling-aware optimizer smoke study (1.9x–27x preliminary speedup) | Smoke-mode only; full E21 data pending |
| C11 | Not present | Qiskit mechanism analysis with planned Cirq/t\|ket> extension | Do not claim full multi-compiler pass decomposition |

---

*Document version: 6.0*  
*Last updated: 2026-06-15*  
*Author: Q-Research Manuscript Team*
