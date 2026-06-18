# V6 Claim-Evidence Map

> **Version**: 6.1
> **Date**: 2026-06-17
> **Scope**: Confirmed manuscript claims are limited to E1-E18 canonical optimizer data plus completed Qiskit baseline/pass-isolation artifacts. E19 is planned, E20 is metadata-only, E21 is smoke-only, E18 conclusions are survivorship-biased, and Phase-2b has a limited implementation/unit tests but no full canonical benchmark CSV.

---

## Claim-Evidence Table

| # | Claim | Evidence | Figure/Table | Support | Scope | Caveat |
|---|---|---|---|---|---|---|
| C1 | The Phase-1 ceiling is structural under the tested listing/window/local-rewrite model: Phase-1 optimizers achieve ~0% gate reduction when no listing-adjacent inverse/mergeable pairs are exposed. | E1–E5 (random), E14 (extended 15-family suite) | Fig.1; Table 1 | Greedy Phase 1 = 0% on QFT, GHZ, BV, IQP, SurfaceCode, QAOA, HardwareEfficient, etc. | Project generators, n=3–20 (extended), primarily LBL/listing-specific local rewrite model | Not a universal lower bound. Ceiling classification is listing/window/model-conditional; WCL full validation is planned (C9). |
| C2 | Phase-2a commutation rewriting provides context-dependent improvement on select circuit families. | E10, E14, E16 | Fig.4; Fig.13 | E14: Oracle/BV ~27.6%, RandomClifford ~22.1%, UCCSD ~1.4%; E16: empirical window-size trend | Implemented local commutation rewriter, window w in {2,5,10,20,50} | Improvement is family-dependent. Phase-2a empirical results do not prove Phase-2b template-assisted theorems. |
| C3 | Production compiler gap analysis reveals mechanisms beyond the prototype peephole model. | E12, E15, Qiskit pass-isolation artifact | Fig.12; Fig.17; Table 8 | Qiskit transpiler at opt levels 0–3 exceeds the prototype on selected families; Cirq and t\|ket> are planned/metadata-only and excluded from confirmed claims. | Qiskit 2.4.1; default no-backend transpilation | Hardware-specific effects not fully modeled. Cirq/t\|ket> require full CSV data before being used as evidence. |
| C4 | Phase-2a window size w affects the trade-off between optimization power and runtime. | E16 | Fig.13 | w=2: ~0%, w=5: ~1.5%, w=10: ~4.2% on full suite | Window sizes {2, 5, 10, 20, 50} | Underpowered comparison (reported power=0.126); treat saturation as empirical trend, not confirmed design rule. |
| C5 | Hardware topology constraints affect optimization opportunities differently. | E17 | Fig.14 | Linear, grid, heavy-hex topologies on all 15 families | Simplified topology models | Real hardware has additional noise/error effects not modeled. |
| C6 | Clifford+T gate-set decomposition preserves some Phase-2 value among surviving rows. | E18 | Section 5.6.4 | Decomposition to {H, S, T, CNOT}; T-count, CNOT reduction tracked | Clifford+T universal gate set; valid rows only | Survivorship-biased: decomposition/fidelity failures are excluded. Do not generalize E18 results to failed rows or full attempted population. |
| C7 | Exact functionality is preserved where fidelity is computed and retained. | E1–E18, E21 smoke where available | fidelity columns in CSV files | Mean fidelity 1.000000 for verified retained datasets | Exact/scalable unitary comparison for supported qubit sizes | Do not claim all E1–E21 outputs are verified: E19 has no data, E20 has metadata only, E21 is smoke-only, and failed/invalid rows are filtered where valid fidelity is required. |
| C8 | The Phase-1 reduction ceiling is formally established for bounded circuits, with the bounded INSERTION cascade gap resolved. | Theory (Thm 2, Thm 2b); E1–E5 empirical validation | Open Problems section; Thm 2b proof | Thm 2b proves polynomial-time termination of INSERTION move sequences for bounded depth/gate count; empirical ceilings support predictions | Bounded circuits: depth O(poly(n)), gate count O(poly(n)) | The unbounded INSERTION cascade remains open. QMA-hardness of CODP remains separate theoretical motivation. |
| C9 | Listing-model dependency: WCL-style preprocessing may expose Phase-1 opportunities hidden under LBL. | Planned WCL-E19; theoretical listing-model analysis | Table 2; Section 5.2 | Full WCL benchmarking is not collected. Any WCL numerical values are projections/smoke observations, not confirmed results. | Planned n=3–20, 15+ circuit families | E19 is planned/not run. Do not use WCL as a main empirical result until full E19 CSV data exists. |
| C10 | Ceiling-aware optimization can skip futile optimization passes in a smoke-mode evaluation. | E21 smoke dataset | Section 5.5; Table 7 | Smoke-mode E21 reports preliminary 1.9x–27x speedups with identical reduction on sampled training-family cases. | Smoke mode only (`n_rows=342` comparison rows); training families | Treat as exploratory/supplementary until full-mode E21 is collected; proxy failed held-out generalization. |
| C11 | Multi-compiler extension with Cirq and t\|ket> is planned but not supported by optimization-output CSVs. | E20 metadata only | S11.2 status note | Qiskit pass analysis is available; Cirq/t\|ket> values are planned projections/metadata only. | E20 metadata only | Do not claim no-single-compiler dominance or Cirq/t\|ket> percentages before full data generation. |
| C12 | Phase-2b template-assisted BV advantage is theoretically proved and partially implemented, but not full-benchmark validated. | Theory (Thm 7, Thm 9); `src/optimisation/phase2/template_matcher.py`; `tests/test_phase2b_template_matcher.py` | Section 5.3.4 | Limited matcher covers the H-CX-H control-template mechanism and unit tests verify BV-like examples. | Unit-tested implementation only; no canonical Phase-2b CSV | Do not conflate Phase-2b theorem/tests with E10/E11/E14/E16 Phase-2a canonical results. Full benchmark rerun is pending. |

---

## Supporting Experiments (Legacy)

| experiment_id | description | data dir |
|---|---|---|
| E01 | Phase transition study | data/v2_fixed/e01/ |
| E02 | Entanglement density study | data/v2_fixed/e02/ |
| E03 | Scaling study | data/v2_fixed/e03/ |
| E04 | Algorithm comparison | data/v2_fixed/e04/ |
| E05 | Landscape study | data/v2_fixed/e05/ |
| E10 | Phase 1 vs Phase 2a | data/v3_extended/e10/ and data/v5/e10/ |
| E11 | Real-circuit benchmark (v4) | data/v4/e11/ |
| E12 | Compiler baseline (v4) | data/v4/e12/ |
| E13 | Structural ceiling proxy | data/v4/e13/ |

## v5 Experiments

| experiment_id | description | data dir | key claim |
|---|---|---|---|
| E14 | Extended benchmark suite (15 families, extended metrics) | data/v5/e14/ | C1, C2, C7 |
| E15 | Compiler comparison (custom peephole vs Qiskit) | data/v5/e15/ | C3, C7 |
| E16 | Phase-2a window-size scaling study | data/v5/e16/ | C2, C4 |
| E17 | Hardware connectivity constraints | data/v5/e17/ | C5 |
| E18 | Clifford+T gate-set experiment | data/v5/e18/ | C6, C7; survivorship-biased |

## v6 Experiments and Preliminary Artifacts

| experiment_id | description | data dir | key claim | status |
|---|---|---|---|---|
| WCL-E19 | Listing-model dependency test (WCL vs. LBL) | data/v6/e19/ | C9 planned | Planned/not run |
| MC-E20 | Cirq and t\|ket> full multi-compiler extension | data/v6/e20/ | C11 planned | Metadata-only |
| E21 | Ceiling-aware optimizer evaluation | data/v6/e21/ | C10 smoke-only | Smoke-only |
| Phase-2b unit tests | Template-assisted matcher sanity tests | tests/test_phase2b_template_matcher.py | C12 | Unit-tested, no full canonical CSV |

---

## Claim Dependency Graph

```
C1 (Phase-1 listing/window/model-conditional ceiling)
 ├── C2 (Phase-2a commutation advantage)
 ├── C9 (Listing-model dependency; planned E19 modifies C1 scope)
 └── C10 (Ceiling-aware optimizer smoke study; depends on C1/C2 training-family prescriptions)

C3 (Qiskit confirmed compiler gap)
 └── C11 (Cirq/t|ket> metadata-only planned extension)

C8 (Theorem 2 / bounded INSERTION)
 └── C1 (empirical support)

C12 (Phase-2b template-assisted theorem/limited implementation)
 └── must not be conflated with C2 Phase-2a empirical results

C4 (Window scaling) ← C2
C5 (Topology) ← C1/C2
C6 (Clifford+T survivorship-biased) ← C2/C7
C7 (Fidelity for retained verified rows) ← retained verified datasets only
```

---

## Changes from v5 to v6.1

| Claim | Prior Status | v6.1 Status | Change Description |
|-------|--------------|-------------|-------------------|
| C1 | Ceiling under LBL only | Listing/window/model-conditional ceiling | Absolute ceiling wording weakened |
| C2 | Generic Phase 2 | Phase-2a empirical commutation | Separates implemented canonical experiments from Phase-2b theory |
| C3 | Qiskit plus planned compilers | Qiskit only confirmed | E20 metadata-only; no Cirq/t\|ket> confirmed values |
| C6 | Clifford+T preserved | Survivorship-biased valid-row result | E18 caveat made explicit |
| C7 | E1–E21 fidelity | Retained verified rows only | E19/E20/E21 evidence levels corrected |
| C9 | Listing dependency hypothesis | E19 planned/not run | No full WCL data claimed |
| C10 | Ceiling-aware optimizer | E21 smoke-only | No full validation claimed |
| C11 | Multi-compiler analysis | E20 metadata-only/planned | No completed multi-compiler CSV claimed |
| C12 | Not explicit | Phase-2b theory + limited implementation/unit tests | Records pending full benchmark status |

---

*Document version: 6.1*
*Last updated: 2026-06-17*
*Author: Q-Research Manuscript Team*
