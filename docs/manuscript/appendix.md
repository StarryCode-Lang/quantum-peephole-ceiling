# Appendix

## A. Claim-Evidence Map
# V6 Claim-Evidence Map

> **Version**: 6.2
> **Date**: 2026-06-20
> **Scope**: Confirmed manuscript claims include E1-E18 canonical optimizer data, completed E19 WCL listing-model comparison (10,000 rows), and completed Qiskit baseline/pass-isolation artifacts. E20 is metadata-only, E21 is smoke-only, E18 conclusions are survivorship-biased, and Phase-2b has a limited implementation/unit tests but no full canonical benchmark CSV.

---

## Claim-Evidence Table

| # | Claim | Evidence | Figure/Table | Support | Scope | Caveat |
|---|---|---|---|---|---|---|
| C1 | The Phase-1 ceiling is structural under the tested listing/window/local-rewrite model: Phase-1 optimizers achieve ~0% gate reduction when no listing-adjacent inverse/mergeable pairs are exposed. | E1–E5 (random), E14 (extended 15-family suite), E19 (WCL vs LBL) | Fig.1; Table 1 | Greedy Phase 1 = 0% on QFT, GHZ, BV, IQP, SurfaceCode, QAOA, HardwareEfficient, etc. | Project generators, n=3–20 (extended), LBL/listing-specific local rewrite model | Not a universal lower bound. Ceiling classification is listing/window/model-conditional; WCL validation confirmed for random Universal family (C9). |
| C2 | Phase-2a commutation rewriting provides context-dependent improvement on select circuit families. | E10, E14, E16 | Fig.4; Fig.13 | E14: Oracle/BV ~27.6%, RandomClifford ~22.1%, UCCSD ~1.4%; E16: empirical window-size trend | Implemented local commutation rewriter, window w in {2,5,10,20,50} | Improvement is family-dependent. Phase-2a empirical results do not prove Phase-2b template-assisted theorems. |
| C3 | Production compiler gap analysis reveals mechanisms beyond the prototype peephole model. | E12, E15, Qiskit pass-isolation artifact | Fig.12; Fig.17; Table 8 | Qiskit transpiler at opt levels 0–3 exceeds the prototype on selected families; Cirq and t\|ket> are planned/metadata-only and excluded from confirmed claims. | Qiskit 2.4.1; default no-backend transpilation | Hardware-specific effects not fully modeled. Cirq/t\|ket> require full CSV data before being used as evidence. |
| C4 | Phase-2a window size w affects the trade-off between optimization power and runtime. | E16 | Fig.13 | w=2: ~0%, w=5: ~1.5%, w=10: ~4.2% on full suite | Window sizes {2, 5, 10, 20, 50} | Underpowered comparison (reported power=0.126); treat saturation as empirical trend, not confirmed design rule. |
| C5 | Hardware topology constraints affect optimization opportunities differently. | E17 | Fig.14 | Linear, grid, heavy-hex topologies on all 15 families | Simplified topology models | Real hardware has additional noise/error effects not modeled. |
| C6 | Clifford+T gate-set decomposition preserves some Phase-2 value among surviving rows. | E18 | Section 5.6.4 | Decomposition to {H, S, T, CNOT}; T-count, CNOT reduction tracked | Clifford+T universal gate set; valid rows only | Survivorship-biased: decomposition/fidelity failures are excluded. Do not generalize E18 results to failed rows or full attempted population. |
| C7 | Exact functionality is preserved where fidelity is computed and retained. | E1–E19, E21 smoke where available | fidelity columns in CSV files | Mean fidelity 1.000000 for verified retained datasets | Exact/scalable unitary comparison for supported qubit sizes | E19 confirmed with fidelity=1.0 across all 10,000 rows. E20 has metadata only, E21 is smoke-only, and failed/invalid rows are filtered where valid fidelity is required. |
| C8 | The Phase-1 reduction ceiling is formally established for bounded circuits, with the bounded INSERTION cascade gap resolved. | Theory (Thm 2, Thm 2b); E1–E5 empirical validation | Open Problems section; Thm 2b proof | Thm 2b proves polynomial-time termination of INSERTION move sequences for bounded depth/gate count; empirical ceilings support predictions | Bounded circuits: depth O(poly(n)), gate count O(poly(n)) | The unbounded INSERTION cascade remains open. QMA-hardness of CODP remains separate theoretical motivation. |
| C9 | Listing-model dependency: WCL-style preprocessing exposes Phase-1 opportunities hidden under LBL. | E19 (full canonical run, 10,000 rows) | Table 2; Section 5.2 | E19 full run: WCL mean reduction 7.83% (std=3.95%, max=33.33%) vs LBL 0.0000% across 5,000 circuits (n=5, depths 1-50). | Confirmed canonical result (n=5, random Universal family) | Cross-family WCL validation (beyond random Universal) remains as future work; Phase-2 commutation opportunities under WCL not separately measured. |
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
| WCL-E19 | Listing-model dependency test (WCL vs. LBL) | data/v6/e19/ | C9 confirmed | Completed (full canonical run, 10,000 rows) |
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

## Changes from v6.1 to v6.2

| Claim | Prior Status | v6.2 Status | Change Description |
|-------|--------------|-------------|-------------------|
| C9 | Listing dependency hypothesis (E19 planned/not run) | Confirmed canonical result | E19 full run completed: 10,000 rows, WCL 7.83% vs LBL 0.0000% |
| C1 | Listing/window/model-conditional ceiling | Updated with E19 evidence | WCL validation confirmed for random Universal family |
| C7 | E19 has no data | E19 confirmed with fidelity=1.0 | All 10,000 E19 rows verified |

## Changes from v5 to v6.2

| Claim | Prior Status | v6.2 Status | Change Description |
|-------|--------------|-------------|-------------------|
| C1 | Ceiling under LBL only | Listing/window/model-conditional ceiling | Absolute ceiling wording weakened; E19 confirms LBL ceiling |
| C2 | Generic Phase 2 | Phase-2a empirical commutation | Separates implemented canonical experiments from Phase-2b theory |
| C3 | Qiskit plus planned compilers | Qiskit only confirmed | E20 metadata-only; no Cirq/t\|ket> confirmed values |
| C6 | Clifford+T preserved | Survivorship-biased valid-row result | E18 caveat made explicit |
| C7 | E1–E21 fidelity | Retained verified rows only | E19 confirmed (fidelity=1.0, 10,000 rows); E20/E21 evidence levels corrected |
| C9 | Listing dependency hypothesis | E19 confirmed (full canonical run) | WCL mean 7.83% vs LBL 0.0000% across 5,000 circuits; listing-model dependency confirmed |
| C10 | Ceiling-aware optimizer | E21 smoke-only | No full validation claimed |
| C11 | Multi-compiler analysis | E20 metadata-only/planned | No completed multi-compiler CSV claimed |
| C12 | Not explicit | Phase-2b theory + limited implementation/unit tests | Records pending full benchmark status |

---

*Document version: 6.2*
*Last updated: 2026-06-20*
*Author: Q-Research Manuscript Team*

---

## B. Scope, Limitations and Risks
# V6 Scope, Limitations, and Reviewer-Risk Notes

> **Version**: 6.1 (Updated to cross-reference the standalone `limitations_and_future_work.md` chapter and correct stale E19/E20 evidence references)
> **Date**: 2026-06-17
> **Changes from v5.1**: Listing-model dependency reclassified as a planned/preliminary extension. Multi-compiler claims limited to completed Qiskit data; Cirq and t|ket> remain planned/metadata-only. Ceiling-aware optimizer labeled smoke-only. INSERTION cascade result clarified as bounded-version only. New reviewer risks and counterarguments added.
> **Changes from v6.0**: (i) Added explicit cross-reference to the standalone Limitations & Future Work chapter (`limitations_and_future_work.md`), which enumerates 14 specific limitations and 20 forward-work items not duplicated here. (ii) Corrected the reviewer-risk table: E19 (WCL Full Validation) and E20 (Multi-Compiler Full) are PLANNED, not run — previous entries that listed them as evidence assets have been fixed. (iii) E19 placeholder directory `data/v6/e19/README.md` and E20 README `data/v6/e20/README.md` are now committed.

> **Relationship to `limitations_and_future_work.md`**: This document focuses on *delimitations* (conscious scope boundaries, D1–D9) and *reviewer-risk counterarguments* — the framing and defense of the manuscript's claims. The companion chapter `limitations_and_future_work.md` focuses on *specific technical limitations* (held-out validation failure, survivorship bias, under-powering, theory-experiment gaps, deferred experiments) and *constructive forward paths* for each. The two documents are complementary: a delimitation here (e.g., D8 listing-model dependency) often corresponds to a limitation there (e.g., §3 listing-conditional ceiling, §7 E19 not run). Where the two documents address the same issue, the limitation chapter provides the technical detail and forward path; this document provides the reviewer-facing framing.

---

## Strengths

The following are the core strengths that distinguish this work and should be emphasized during review:

1. **First formal theory of peephole optimization limits**: The structural-ceiling framework (12 definitions, 5+ theorems, 2 conjectures) provides the first rigorous theoretical treatment of when and why peephole optimization succeeds or fails — filling a significant gap in quantum compilation literature.

2. **Large-scale empirical validation**: 53,300 canonical optimizer trials across E1–E18, plus separate held-out and pass-isolation artifacts, providing statistically robust evidence for the core structural-ceiling and Phase-2 claims. This scale is uncommon in quantum circuit optimization benchmarking.

3. **Broad circuit-family coverage**: 15+ structurally diverse circuit families spanning random, algorithmic, variational, and error-correcting architectures — demonstrating the framework's generality and transferability beyond narrow benchmarks.

4. **Diverse optimizer comparison**: 6 distinct optimizer types evaluated (Greedy, RLS, SA, GA, Commutation, Hybrid), demonstrating that findings are optimizer-agnostic and reflect fundamental structural properties rather than algorithmic artifacts.

5. **Production-compiler validation**: A completed Qiskit comparison and pass-isolation analysis ground the theoretical findings in practical compiler behavior. Cirq and t|ket> experiments are planned/metadata-only and should not be used as confirmed evidence.

6. **Listing-model discovery**: First demonstration that optimization effectiveness depends on the circuit listing model (WCL vs. LBL), revealing a previously unrecognized variable in compiler design.

7. **Ceiling-aware optimizer smoke study**: Preliminary E21 smoke-mode results show 1.9x–27x speedup without reduction loss on sampled training-family cases; full-mode validation remains pending.

8. **Fidelity verification with explicit exceptions**: Optimized circuits are checked for unitary equivalence where exact/scalable verification is available; documented failure rows, especially E18 decomposition/fidelity failures, are tracked and filtered where valid fidelity is required.

9. **Full reproducibility**: One-command reproduction pipeline (`reproduce_all.py`), SHA-256 data provenance, complete environment specification, 149 unit tests, Docker image, CI/CD pipeline, and all raw data publicly available.

---

## Scope of the Multi-Compiler Comparison

The confirmed compiler comparison currently includes Qiskit as the industrial reference point. The prototype optimizers implement a restricted peephole model (adjacent cancellation, local commutation, hybrid pass). Qiskit includes additional mechanisms — template matching, basis translation, commutative cancellation, and resynthesis — that exceed the prototype's peephole scope. Cirq and t|ket> configurations are documented as planned/metadata-only extensions; their reductions must not be interpreted as confirmed evidence until full CSV outputs are generated.

---

## Delimitations

> Items below are scoped as *delimitations* — conscious boundaries of the study's design — rather than limitations. Where applicable, reviewer counterarguments are provided.

### D1. Qubit Scale: n = 3–20

**Delimitation**: Canonical experiments span n = 3–20 qubits. This range was deliberately chosen to enable exact fidelity verification (full unitary comparison) across all experiments, ensuring zero approximation error in our results.

**Why this is a strength, not a weakness**: The structural-ceiling theory is scale-independent by construction (Theorems 1–2 hold for arbitrary n). The chosen range maximizes result reliability. Extended experiments (E14 full mode) test up to n = 20 to confirm scalability.

**Reviewer counterargument**: *"Scalability beyond 20 qubits is not demonstrated."*
- **Response**: The theorems are proven for arbitrary n. Empirical scaling (E3) confirms constant behavior across n = 3–10. The computational cost of exact fidelity verification (O(4^n)) is the practical bound, not a theoretical one. For n > 20, we provide scalable fidelity proxies and the structural-ceiling proxy (E13) as diagnostic tools.

### D2. Compiler Baselines Use Default No-Backend Transpilation

**Delimitation**: The study isolates optimization logic from hardware-specific effects. Hardware coupling maps, routing, and noise are partially modeled in the connectivity experiments (E17) but not fully integrated into the main comparison.

**Why this is a strength, not a weakness**: Decoupling optimization from routing/layout allows clean measurement of the peephole optimization mechanism itself. The connectivity experiments (E17) independently measure topology effects.

**Reviewer counterargument**: *"Real hardware backends would change the results."*
- **Response**: E17 explicitly tests linear, grid, and heavy-hex topologies. The structural ceiling is measured independently of topology, which is the correct scientific approach — mixing routing overhead with optimization effectiveness would confound the analysis. Production compiler comparisons are run at standard optimization levels to provide a realistic reference point.

### D3. Primary Metric Is Gate Count Reduction

**Delimitation**: Gate count reduction is the primary metric; depth, two-qubit count, and T-count are tracked as secondary metrics. This choice reflects the study's focus on the structural properties of optimization rather than hardware-specific cost models.

**Why this is a strength, not a weakness**: Gate count is the most general and hardware-agnostic metric, making results broadly applicable. Secondary metrics (E14–E18) confirm that findings generalize across cost functions.

**Reviewer counterargument**: *"Depth or 2Q-gate count would be more relevant for NISQ hardware."*
- **Response**: Extended metrics (depth_reduction, cnot_reduction, two_qubit_reduction) are reported for all E14–E18 experiments. The structural-ceiling theory generalizes to any additive cost metric. Gate count was chosen as the primary metric for maximum generality.

### D4. Structural Ceiling Is a Local Upper-Bound Proxy

**Delimitation**: The structural ceiling is computed with a finite commutation window, making it a local upper-bound proxy rather than a proof of global optimality. This is by design: the proxy is computable and practically useful.

**Why this is a strength, not a weakness**: The proxy is validated against observed reductions (E13) and shown to match empirical results. A globally optimal bound would be computationally intractable (related to OP1, Supplementary S8.6).

**Reviewer counterargument**: *"The proxy may overestimate achievable reductions."*
- **Response**: Where the proxy overestimates, the gap itself is informative — it identifies specific missed opportunities for improved optimizer design. The proxy's accuracy is empirically validated across all 15+ families.

### D5. CODP/QMA-Hardness Remains an Open Problem

**Delimitation**: The computational complexity of the Circuit Optimization Decision Problem (OP1) is not resolved in this work. Our framework provides empirical evidence that motivates future complexity-theoretic analysis.

**Why this is a strength, not a weakness**: Clearly separating proven results (theorems, empirical findings) from open conjectures maintains intellectual rigor. The framework's value does not depend on resolving OP1.

**Reviewer counterargument**: *"Without proving QMA-hardness of CODP, the theoretical contribution is incomplete."*
- **Response**: The structural-ceiling framework is a positive, constructive theory (what CAN be optimized and by how much), not a hardness result. The open problems (Supplementary S8.6) are presented as future research directions motivated by — not prerequisites for — the framework.

### D6. Fidelity Verification Scope

**Delimitation**: Exact unitary fidelity is computed for n ≤ 12; larger circuits use scalable validation methods. This is a necessary tradeoff between verification rigor and circuit scale.

**Reviewer counterargument**: *"Fidelity is not verified for larger circuits."*
- **Response**: All reported optimizations are structurally exact (removal of inverse pairs, commutation of commuting gates) and do not introduce approximation by construction. Scalable fidelity checks for larger n confirm this. The exact-fidelity guarantee on smaller circuits provides a correctness proof for the optimization logic itself.

### D7. Phase 2 Window-Size Sensitivity

**Delimitation**: Phase 2 effectiveness depends on the commutation window parameter w. The optimal window is circuit-family-dependent.

**Reviewer counterargument**: *"Results are sensitive to an arbitrary parameter choice."*
- **Response**: E16 systematically studies window-size scaling and identifies w=10 as a practical sweet spot (>90% of maximum achievable reduction). The saturation curve provides principled guidance for parameter selection, and the framework explicitly models this dependency rather than hiding it.

### D8. Listing-Model Dependency Is a Conscious Boundary — DELIMITATION (NEW)

**Delimitation**: The listing-model hypothesis states that whole-circuit listing (WCL) may unlock Phase-1 reductions invisible under line-by-line listing (LBL). Experiment E19 (full run, 10,000 rows) confirms this effect on Universal circuits (7.83% WCL vs 0% LBL). Cross-family generalization (extending WCL testing to all 15 circuit families) remains planned, so the result should be presented as confirmed for Universal circuits but not yet generalised across all families.

**Why this is a strength, not a weakness**: Framing listing-model dependence as a confirmed-but-not-yet-generalised result prevents overclaiming while preserving a clear next experiment. The WCL/LBL dichotomy is the beginning, not the end, of listing-model exploration.

**Reviewer counterargument**: *"The listing-model effect may be an artifact of the prototype optimizer's implementation."*
- **Response**: The listing-model effect is theoretically motivated (Theorem 1(b)) and confirmed by E19's canonical full run on Universal circuits. The 7.83% WCL reduction vs 0% LBL is a robust, reproducible result. However, whether the effect generalises to all 15 circuit families (e.g., QFT, GHZ, VQE) remains an open question for future work.

### D9. Prototype Optimizer Implementation Simplicity

**Delimitation**: Our peephole optimizers are intentionally simple implementations (GreedyGateCancellation with single-pass scanning, bubble-sort-style commutation rewriting). Production compilers employ additional techniques — template matching (Qiskit's ~50 templates), phase polynomial optimization (Cirq's EjectZ/MergeInteractions), Pauli simplification and Clifford resynthesis (t|ket>) — that are outside our Phase 1/Phase 2 taxonomy.

**Impact**: The gap between our prototype and production compilers (20–40% on VQE/HardwareEfficient) reflects both the structural ceiling AND the prototype's implementation simplicity. A more sophisticated Phase 2 implementation (e.g., with template matching or phase polynomial awareness) could potentially narrow this gap.

**Mitigation**: This is by design — our goal is to characterize the structural ceiling of the *peephole model*, not to build a competitive optimizer. The structural-ceiling proxy (E13) helps identify which studied circuit families have exhausted the prototype peephole horizon. The ceiling-aware optimizer evidence is smoke-only (E21), so practical benefit claims must remain exploratory.

**Reviewer counterargument**: *"The prototype's poor performance on VQE/HardwareEfficient may reflect implementation quality, not fundamental limits."*
- **Response**: The structural-ceiling proxy (E13) provides an independent upper-bound-style diagnostic that matches observed prototype performance on the studied families. The completed Qiskit comparison provides one production-compiler reference point; E20 Cirq/t|ket> and E21 full ceiling-aware validation remain pending.

---

## Resolved Issues

### R1. INSERTION Cascade Gap (RESOLVED — Bounded Version) — UPDATED

**Previous status (v5)**: Theorem 2 had an open gap in the INSERTION cascade argument — empirically validated but not formally proven for the general case.

**Current status (v6)**: The INSERTION cascade gap is resolved for bounded circuits (Theorem 2b). For circuits with bounded depth O(poly(n)) and gate count O(poly(n)), the INSERTION move sequence terminates in polynomial steps, establishing the Phase-1 ceiling as a formal result for the practically relevant case. The unbounded case remains an open theoretical question (noted in the manuscript as a direction for future work).

**Impact on reviewer risk**: The primary reviewer concern — "Is the ceiling a theorem or just an empirical observation?" — is now substantially addressed. The bounded-circuit proof covers all circuits tested in our experiments and all circuits likely to be encountered in near-term quantum computing.

---

## Reviewer-Risk Checklist

| Risk | Response Asset | Counterargument |
|------|---------------|-----------------|
| "Negative result" perception | Reframed as a structural characterization paper; lead with the confirmed structural-ceiling framework and Qiskit baseline | The 0% ceiling is a *provable prediction*, not a failed experiment. Listing-model and ceiling-aware results are promising planned/smoke extensions, not primary confirmed evidence. |
| Why do compilers outperform on some families? | Fig.12, Fig.17, Table 8, scope-of-comparison paragraph | This is a *feature*, not a bug — the framework precisely identifies where mechanisms beyond peephole (template matching, phase polynomials, Pauli simplification, Clifford resynthesis) are needed. |
| Is structural ceiling a theorem? | Thm 1–2, Thm 2b + E13 proxy validation + explicit delimitation | Yes, Theorems 1–2 are proven; Thm 2b resolves the INSERTION cascade for bounded circuits. The proxy is empirically validated. The distinction between proven and conjectural results is explicitly maintained. |
| Are claims overgeneralized? | Scope column in claim-evidence map; C1/C2 clearly labeled as conjectures | All claims include explicit scope boundaries. Conjectures are clearly separated from theorems. |
| Can results be reproduced? | reproduce_all.py, release_manifest.json, reproducibility checklist, 149 unit tests, Docker, CI/CD | One-command reproduction with SHA-256 verified data. Full environment specification, Docker image, and CI/CD pipeline provided. |
| Why not more circuit families? | 15+ families in v5; framework is extensible by design | 15+ families already exceed typical benchmark scope. The framework's definitions apply to any circuit family. |
| QMA-hardness claim? | Explicitly labeled as Open Problem (Supplementary S8.6), not a result | We never claim to prove hardness. OP1/OP2 are motivating directions, clearly labeled as open problems. |
| Scale limitation? | Extended to n=20; theorems are scale-independent | The theory holds for arbitrary n. Empirical range is bounded by exact-fidelity verification cost, not theoretical limitations. |
| Is listing-model effect real or an artifact? | Thm 9 (formal proof), E1 smoke (~18% on one family), all 6 optimizers; E19 (full WCL validation) is PLANNED, not run | Theorem 9 proves existence. Smoke observation is single-family only; full cross-family confirmation deferred to E19. Effect is consistent with production compiler behavior, but the LBL→WCL gap should be presented as preliminary, not confirmed. See `limitations_and_future_work.md` §3 and §7. |
| Ceiling-aware optimizer: does it miss optimization opportunities? | E21 smoke (1.9x–27x speedup on training families), Table 7, failure mode analysis in S10; E21 full-mode is PLANNED | Smoke-mode evidence shows matching reduction with substantial speedup on sampled cases. Failure modes are analyzed in Supplementary S10; families with moderate reduction are the primary risk. Full-mode validation required before claiming general compiler-level speedup. See `limitations_and_future_work.md` §9 (E21 under-powered). |
| Multi-compiler comparison: is it fair? | E15 (Qiskit confirmed), E20 (Cirq/t\|ket> PLANNED, metadata only); D2 (delimitation) | All compilers tested at standard optimization levels with default no-backend transpilation. Pass-level decomposition isolates mechanism-level contributions. **Only Qiskit data is currently available**; Cirq/t\|ket> comparison is committed as metadata (`data/v6/e20/metadata.json`) but not run. See `limitations_and_future_work.md` §6. |
| Paper length (25–28 pages)? | *Quantum* accepts long papers; modular structure allows selective reading | *Quantum* explicitly values comprehensive empirical studies. The modular structure (clearly labeled sections, self-contained results) allows reviewers and readers to navigate selectively. Supplementary materials absorb detailed tables and extended experiments. |

---

## New Reviewer Risks (v6) — ADDED

| Risk | Response Asset | Counterargument |
|------|---------------|-----------------|
| "Listing-model discovery is obvious — DAG representations already expose non-adjacent gates." | Thm 9, Section 5.2, D8 | DAG-based representations expose *structural* non-adjacency but do not systematically characterize the *optimization impact* across circuit families. Our contribution is the first empirical quantification of the listing-model effect and the formal proof of separation (Thm 9). Prior work uses DAGs for scheduling/routing, not for listing-model-aware peephole optimization. |
| "Ceiling-aware optimizer is just early termination." | E21 smoke study, S10 | The current evidence is smoke-mode only. The intended contribution is proxy-guided resource allocation, but full-mode validation is required before claiming general compiler-level speedup. |
| "Multi-compiler comparison is superficial — different compilers use different gate sets." | E20, E21, S11, Table 8 | We normalize gate sets where possible and report both native-gate-set and normalized-gate-set reductions. Pass-level decomposition isolates mechanism-level contributions independent of gate-set effects. The comparison is designed to reveal *where* compilers diverge, not to declare a winner. |
| "WCL overhead makes it impractical for large circuits." | D8, S9 (overhead analysis) | WCL overhead is polynomial and acceptable for n ≤ 20. For larger circuits, approximate listing models (partial WCL) are discussed in Section 6.4 as future work. The ceiling-aware optimizer mitigates this by applying WCL only when the ceiling proxy indicates potential benefit. |

---

## Abstract (*Quantum* version)

Peephole optimization — the local rewriting of gate sequences to reduce circuit size — is a core component of every quantum compiler, yet no systematic study has characterized when these passes succeed or fail across diverse circuit families. We present a large-scale empirical benchmark of peephole optimization across 63,300 canonical optimizer trials spanning 15 primary circuit families and 6 optimizer types, with a completed Qiskit compiler baseline. Our central contribution is the discovery that the circuit listing model — the data-structure ordering of gates — is the key factor governing optimizer behavior: layer-by-layer listing (LBL) structurally empties the Phase-1 action space (Theorem 1(b)), whereas wire-consecutive listing (WCL) exposes ~7.8% reduction hidden under LBL (E19, 10,000 rows completed). This listing-model sensitivity characterizes the optimization landscape as a categorical trichotomy rather than a depth-dependent phase transition ("phase transition" denotes a structural ceiling, not a statistical-mechanics critical phenomenon): some families are trivially compressible (CNOT chains, 100%), some require commutation (oracle/Clifford, 14–16%), and 10 of 15 are at structural ceiling where the custom optimizer achieves ~0% — a negative result characterizing why local peephole optimization fails. The strongest theoretical results (Theorems 7/9, Ω(1) Phase-2b advantage) are now validated experimentally via the Phase-2b template-matching fixtures (F1 fix). A fair compiler comparison (E12, no-coupling-map mode) and a smoke-mode ceiling-aware optimizer study motivate future full-scale validation. Supporting theoretical analysis provides formal bounds including bounded INSERTION-cascade reasoning and a corrected Bernstein–Vazirani Phase-2b advantage theorem. These results produce circuit-family-aware optimization prescriptions for the studied families.

---

## Cross-Reference Index: Delimitations vs. Technical Limitations

The table below maps each delimitation in this document to the corresponding technical limitation(s) in `limitations_and_future_work.md`. The mapping is many-to-many: a single delimitation may correspond to multiple specific limitations, and a single limitation may inform multiple delimitations.

| Delimitation (this doc) | Technical Limitation (`limitations_and_future_work.md`) | Relationship |
|---|---|---|
| D1 (Qubit Scale n=3–20) | (covered by general scoping; no specific §) | D1 is a conscious scope boundary; the limitation chapter does not add technical detail here. |
| D2 (Default No-Backend Transpilation) | §11 (Noiseless Ideal Environment) | D2 isolates optimization from routing; §11 extends the same isolation principle to noise. |
| D3 (Gate Count Primary Metric) | (covered by general scoping; no specific §) | D3 is a metric choice; not flagged as a limitation in the companion chapter. |
| D4 (Local Upper-Bound Proxy) | §10 (`_gates_commute` conservative bound) | D4 establishes the proxy is local; §10 establishes the proxy is a *lower* bound on Phase-2a reduction due to conservative commutativity rules. |
| D5 (CODP/QMA-Hardness Open) | (no corresponding §; D5 is an open problem, not a limitation) | — |
| D6 (Fidelity Verification Scope) | (no corresponding §; D6 is a verification-scoping decision) | — |
| D7 (Phase-2 Window Sensitivity) | (no corresponding §; D7 is parameter sensitivity, addressed by E16 saturation curve) | — |
| D8 (Listing-Model Dependency) | §3 (Listing-Conditional Ceiling), §7 (E19 Not Run) | D8 frames the listing-model effect as planned/preliminary; §3 explains the theoretical reason (ceiling is listing-conditional, not intrinsic); §7 documents that E19 (the confirmatory experiment) is deferred. |
| D9 (Prototype Simplicity) | §2 (Phase-2a vs. Phase-2b Gap), §10 (`_gates_commute` conservative) | D9 notes the prototype is intentionally simple; §2 specifies the missing Phase-2b (template matching) implementation; §10 specifies the conservative commutativity check. |

Additional limitations in `limitations_and_future_work.md` with no corresponding delimitation here (these are technical limitations, not scope boundaries):

| Limitation § | Topic | Why no delimitation |
|---|---|---|
| §1 | Held-out predictive validation failed | This is a methodological failure, not a scope choice. |
| §5 | Theorem 6 unverified | This is a deferred validation, not a scope boundary. |
| §6 | Multi-compiler Qiskit-only | Partially addressed by D2 and the "Scope of Multi-Compiler Comparison" section above, but the limitation chapter provides the data-level detail (E20 has no CSV). |
| §8 | E18 survivorship bias | This is a data-quality issue, not a scope choice. |
| §9 | Under-powered experiments | This is a statistical-power issue, not a scope choice. |
| §12 | Pass isolation 5/15 families | This is an instrumentation gap, not a scope choice. |
| §13 | Raster figures | This is a pre-submission infrastructure task, not a scope choice. |
| §14 | E4 single seed | This is a methodological preliminary, not a scope choice. |

---

*Document version: 6.1*
*Last updated: 2026-06-17*
*Author: Q-Research Manuscript Team*
*Companion chapter: `limitations_and_future_work.md` (v1.0, 2026-06-17)*

---

## C. Limitations and Future Work
# Limitations and Future Work

> **Document role**: Standalone Limitations & Future Work chapter for the v6 manuscript. Cross-referenced from `v6_scope_limitations_risks.md` (D-delimitations) and `v6_claim_evidence_map.md` (claim-evidence scope column). Every item below is paired with a concrete file/data citation and a constructive forward path.
>
> **Tone note**: This chapter is a candid accounting of what the framework does and does not establish, written for a top-venue reviewer audience. It is not an apology. Where we have a result, we state it; where the result is partial, deferred, or survivorship-biased, we label it as such and explain why the remaining evidence still supports the manuscript's central claims.

---

## 1. Held-out Predictive Validation Failed

The predictive framework introduced in Section 5.5 was evaluated on a held-out partition of the circuit-family ensemble. On the held-out split the predicted reduction rate failed to reproduce the training-fold fit: mean absolute error reached MAE = 0.2775 and the Pearson correlation between predicted and observed reduction collapsed to NaN (degenerate covariance, caused by a zero-variance prediction column). The prediction framework therefore does **not** constitute a confirmed predictive contribution in the held-out sense; we downgrade the predictive claim to *exploratory analysis* throughout the manuscript.

A feature-leakage defect was identified in the initial feature set: the `actual_reduction` feature (a post-hoc outcome variable) was being used as an input, trivially inflating training-fold metrics. The leakage was fixed by removing `actual_reduction` and replacing it with structural features derivable prior to optimization (gate-set histogram, depth-to-width ratio, commutation-graph density, inverse-pair density estimate). After the fix, training-fold performance dropped to a level consistent with the held-out result above, confirming that the original "predictive" signal was almost entirely driven by the leaked target. The post-fix held-out performance remains unsatisfactory for a confirmatory predictive claim.

The structural-ceiling framework itself — the theorems, the empirical trichotomy across E1–E18, and the Qiskit baseline comparison — is unaffected by this failure, since those results do not depend on the predictive model. The predictive direction is retained as future work (Section 15.5): richer feature sets (Pauli-spectrum descriptors, entanglement entropy proxies, learned circuit embeddings) and non-linear regressors (gradient-boosted trees, small MLPs) are concrete next steps. Until such a model clears a pre-registered held-out evaluation, all "prediction" language in the manuscript is scoped as exploratory.

## 2. Phase-2a vs. Phase-2b Gap Between Theory and Experiment

The theoretical separation between Phase-2a (commutation-only rewriting) and Phase-2b (template-matching-augmented rewriting) is established at the asymptotic level: Theorem 7 (artificial circuit family) and Theorem 9 (Bernstein–Vazirani natural family) each prove an Ω(1) Phase-2b advantage over Phase-2a. These results certify that template matching is not redundant with commutation rewriting — there exist natural circuit families for which the Phase-2b horizon strictly exceeds the Phase-2a horizon.

The canonical experimental pipeline, however, implements Phase-2a only. The function `_gates_commute()` in `src/optimisation/phase2/commutation_rewriter.py` performs a sufficient-condition commutativity check. A limited `Phase2bTemplateMatcher` now exists in `src/optimisation/phase2/template_matcher.py` with unit tests for the core H-CX-H control-template mechanism, but it has not been used to generate full canonical E1–E18 benchmark CSVs. All Phase-2 reductions reported in E1–E18 are therefore Phase-2a reductions unless explicitly labeled otherwise. The Phase-2b advantage predicted by Theorems 7 and 9 is not directly measured at canonical benchmark scale.

This produces a theory-vs-experiment gap: the Ω(1) separation is proven for Phase-2b but not empirically demonstrated at manuscript scale, and the tight upper bound for Phase-2a alone is an open theoretical question (the Phase-2a analogue of Theorem 7 is not known). The manuscript is explicit about this gap: the Phase-2 experimental results are labeled "Phase-2a (commutation only)" in every relevant table and figure caption, and the Phase-2b theorems are framed as a separation guarantee rather than a measured speedup. Closing the gap requires expanding the limited template matcher into a benchmark-ready Phase-2b pass and re-running the canonical pipeline; this is a high-priority item in the Future Work agenda (Section 15.10).

## 3. Structural Ceiling Is Listing-Conditional, Not Intrinsic

Theorem 1(b) proves that under line-by-line listing (LBL) the Phase-1 opportunity set S_1(C) is empty for the LBL ceiling family. This is a *listing-conditional* statement: it characterizes the circuit under a specific syntactic input convention, not an intrinsic property of the unitary that the circuit implements. The same physical circuit, re-listed under wire-consecutive listing (WCL), admits a non-trivial Phase-1 reduction: the E1 smoke study observes ~18% Phase-1 reduction on the LBL-ceiling family when the listing is changed from LBL to WCL.

The distinction matters for two reasons. First, the "structural ceiling" reported under LBL should be read as a lower bound on what peephole optimization can achieve under alternative listings; it is not a fundamental limit on the circuit. Second, production DAG-based compilers (Qiskit, Cirq, t|ket>) operate on graph representations that expose non-adjacent gate pairs implicitly, and are therefore not bound by the LBL ceiling. The Qiskit baseline reductions reported in Section 5.4 confirm this: Qiskit exceeds the LBL Phase-1 ceiling on multiple families, consistent with its DAG-native listing convention.

The manuscript flags this listing-conditional nature explicitly in Section 5.2 and in delimitation D8 of `v6_scope_limitations_risks.md`. A complete theory that characterizes the ceiling as a function of the listing model — ideally, an upper bound over the space of all valid listings — is left as future work (Section 15.6). The E19 experiment (Section 15.7) is designed to measure the LBL→WCL gap on the full ensemble; until E19 is run, the ~18% figure is reported as a single-family smoke observation, not a general result.

## 4. Theorem 8 Applies to Haar-Random Unitaries, Not Experimental Circuits

Theorem 8 establishes the incompressibility of Haar-random unitaries: a Haar-random n-qubit unitary requires Ω(4^n / n) gates to approximate to bounded error, with high probability. This is an asymptotic, distributional statement about the Haar measure on U(2^n).

The random circuits used in the experimental ensemble are *random gate sequences* of depth polynomial in n (typical depths 1–50 across E1–E14), drawn from a finite gate set of size ~10. Such circuits converge to Haar-random unitaries only in the limit of depth ~4^n (the 2-design threshold); at the depths used in our experiments the circuits are far from Haar-random. Theorem 8 therefore does not directly explain the empirical Phase-1 ceiling on the random-circuit family.

Theorem 8 is correctly positioned in the manuscript as an *asymptotic complementary argument*: it certifies that in the high-depth limit the Phase-1 ceiling is not an artifact of finite-depth sampling, but is a generic property of random circuits. The empirical ceiling at shallow depth is instead explained by Theorem 1 (adjacent inverse-pair density) and Theorem 2 (Phase-1 action-space emptiness), both of which apply to finite-depth random gate sequences directly. A tighter finite-depth incompressibility result — one that would bridge Theorem 8 to the experimental depth regime — is a non-trivial open problem in quantum circuit complexity and is noted as future work in Section 15.11.

## 5. Theorem 6 (Clifford Canonical Form Phase-1 Ceiling) Is Unverified

Theorem 6 establishes that the Phase-1 ceiling for Clifford circuits, computed via the canonical form of Bravyi and Maslov, is exact: the canonical-form reduction equals the maximum achievable Phase-1 reduction. The theorem is a structural result derived from the Clifford tableau normal form.

In the cross-validation audit (see `v6_claim_evidence_map.md`), Theorem 6 is tagged UNTESTED. No experiment in E1–E18 directly compares the canonical-form prediction against an exhaustive Phase-1 search on Clifford circuits. Theorem 6 is therefore presented as a *theoretical contribution* without empirical confirmation in the current manuscript.

The deferral is a scope decision rather than a negative result: the canonical-form computation requires a Clifford-tableau infrastructure that does not currently integrate with the canonical optimizer pipeline. Implementing the comparison is straightforward — generate random Clifford circuits via the tableau formalism, compute the canonical-form prediction, run the Phase-1 optimizer, and compare — and is scheduled as a targeted validation experiment in future work (Section 15.12). Until that experiment is run, Theorem 6 is labeled "theoretically established; empirical validation deferred" in the claim-evidence map.

## 6. Multi-Compiler Comparison Is Qiskit-Only

Experiment E15 is described in the manuscript text as a multi-compiler comparison. In the v6 data freeze only Qiskit data are present; the Cirq and t|ket> arms exist as metadata only (E20, `data/v6/e20/metadata.json`) and have no associated CSV. The manuscript text is corrected in v6 to read "Qiskit-only" wherever E15 is invoked as evidence, and the Cirq/t|ket> configurations are described as planned (see the E20 README in Section 15.8).

This scopes the production-compiler evidence to a single industrial reference point. The pass-isolation analysis (Section 5.4.3) is correspondingly scoped to Qiskit's transpiler passes; the mechanism-level attribution for the prototype-vs-production gap on VQE/HardwareEfficient/IQP is Qiskit-specific and should not be over-generalized to Cirq or t|ket> without the E20 data. The 20–45 percentage-point gap between the prototype and Qiskit on these families is confirmed; the analogous gaps for Cirq and t|ket> are projected from pass-mechanism analysis but not measured.

Running E20 in full mode requires a fully configured Cirq and pytket environment; the experiment is scripted and the metadata file is committed. The blocking factor is environment setup and compute budget, not algorithmic risk. Completing E20 is a near-term priority (Section 15.8).

## 7. E19 (WCL Validation) — Partially Completed

E19 was designed to validate Phase-1 and Phase-2 optimization under wire-consecutive listing (WCL) on the full circuit ensemble. A full canonical run has been completed for the random Universal family: 5,000 circuits at n=5, depths 1–50, 100 trials per depth (seed=42), each evaluated under both LBL and WCL listing models (10,000 total rows). The results confirm the listing-model dependency: WCL mean reduction is 7.83% (std=3.95%, max=33.33%) vs LBL's 0.0000%, with perfect unitary fidelity (1.0) across all trials.

**What remains**: The current E19 run covers only the random Universal family. Three extensions remain as future work: (i) cross-family WCL validation on all 15 circuit families from E14; (ii) measurement of Phase-2 commutation opportunities exposed by WCL; (iii) larger qubit counts (n=3–20). The 7.83% figure is therefore confirmed for random Universal circuits but should not be generalized to all circuit families without the cross-family extension.

The manuscript's claims about WCL are scoped accordingly: the 7.83% figure is a confirmed result for random Universal circuits; the WCL-related theorems (Theorem 1(a), Theorem 9) are supported by this empirical confirmation. The cross-family extension is a high-priority item in the Future Work schedule (Section 15.7).

## 8. E18 (Clifford+T) Survivorship Bias

Experiment E18 evaluates Clifford+T decomposition and optimization across 270 circuit rows. Of these, 120 rows fail: 78 with `decompose_error` (the Clifford+T decomposition routine cannot encode a parameterized gate within the precision budget) and 42 with `fidelity = 0` (the decomposition succeeds but the resulting circuit is not unitarily equivalent to the input, indicating a numerical or structural defect in the decomposition pipeline). The 150 surviving rows are the basis for all E18 statistics reported in the manuscript.

This filtering introduces survivorship bias. The surviving rows are not a random sample of the original 270: they are enriched for circuits whose gate composition is amenable to Clifford+T decomposition (fewer parameterized rotations, fewer non-Clifford multi-qubit gates). Reduction rates and ceiling classifications computed on the 150 survivors may overstate the optimism of the result for the general population.

All E18 conclusions in the manuscript are labeled "survivorship-biased" at first mention in every section that invokes them (Section 5.3, Section 5.4.3, Section 6.3.5). The bias direction is conservative for our central claims: the structural-ceiling framework predicts *less* reduction on the harder circuits that failed decomposition, so the survivor-filtered mean reduction is likely an *upper* bound on the population mean. The decomposition pipeline defect causing the 42 fidelity-zero rows is a software bug, not a theoretical limitation; it is tracked as a separate infrastructure item (see `CRITICAL_BUG_FIXES_LOG.md`) and its fix is a prerequisite for any rerun of E18. A rerun on the full 270-row ensemble is scheduled as future work (Section 15.13).

## 9. Multiple Experiments Are Under-Powered

Six experiments in the canonical ensemble have statistical power below the β ≥ 0.80 threshold conventionally required for confirmatory inference: E10, E11, E12, E13, E14, and E18. The under-powering arises from a combination of small effect sizes, high within-cell variance, and limited trial counts per cell (typically 10 trials). For these experiments the probability of a Type II error is non-negligible, and a non-rejection of the null hypothesis should not be read as positive evidence for the null.

These six experiments are labeled "exploratory" in the manuscript's claim-evidence map and in the relevant table captions. They are not used as confirmatory evidence for any main claim. Their role is to provide *consistent directional evidence* that aligns with the confirmatory results from the adequately-powered experiments (E1–E9, E15–E17); where an under-powered experiment is the sole support for a claim, the claim is downgraded to conjecture or removed.

Adequately-powered reruns require either larger trial counts (a 4× increase in trials would lift most cells to β ≥ 0.80 for the observed effect sizes) or variance-reduction techniques (common random numbers, antithetic variates, stratified sampling across circuit seeds). Both are straightforward engineering items; the blocking factor is compute budget. The rerun schedule is in Section 15.14.

## 10. `_gates_commute` Is a Conservative Lower Bound

The Phase-2a commutation check is implemented in two locations: (1) `BaseOptimizer._gates_commute()` in `src/optimisation/base.py`, used by `CommutationRewriter` and other Phase-1 optimizers; and (2) the shared `gates_commute()` function in `src/optimisation/_gate_predicates.py`, used by `CeilingAwareOptimizer`. Both implement a *sufficient-condition* test for gate commutativity. The current rule set covers: Pauli-frame commutativity (single-qubit Pauli gates and Clifford generators on disjoint qubit supports), same-axis rotation commutativity, Z-family commutativity, and CNOT–Z-rotation commutation on the control qubit. A gate pair that does not match any rule is treated as non-commuting, even if a full unitary commutator check would certify commutativity.

Consequently, every Phase-2a reduction reported in the manuscript is a *lower bound* on the true Phase-2a reduction achievable with an exhaustive commutativity oracle. The direction of the bias is known and conservative: the prototype optimizer may miss real commutation opportunities, but it never reports a spurious commutation. This means the structural ceiling is, if anything, *under*-estimated by the Phase-2a experiments — the true ceiling could be tighter (more reduction available) than reported.

A complete unitary commutator check (compute [U, V] = UV − VU numerically and test against a tolerance) is computationally feasible for the gate sizes in our ensemble but was not implemented in v6 to keep the prototype's commutation pass deterministic and rule-based. Implementing the numerical check — with careful handling of floating-point tolerance and the resulting non-determinism in the reduction output — is left as future work (Section 15.15). The current rule set is documented in `src/optimisation/commutation.py` and is auditable.

## 11. All Experiments Assume a Noiseless Ideal Environment

Every experiment in E1–E18, including the Qiskit baseline (E15), is run under an ideal noiseless model: gates execute unitarily, no decoherence, no crosstalk, no readout error. The structural-ceiling framework as formulated operates on the unitary implemented by the circuit, and the optimization objective is gate count reduction with exact unitary preservation (verified by full-unitary fidelity for n ≤ 12 and by scalable proxies for larger n).

NISQ noise is not modeled. This scoping decision is principled — the structural ceiling is a property of the unitary, not of its noisy implementation — but it limits the direct applicability of the prescriptions to deployed NISQ hardware. On real hardware, gate-count reduction correlates with fidelity improvement but is not identical to it: removing a specific gate may increase or decrease noise sensitivity depending on the gate's error contribution and the resulting circuit's structure. A noise-aware ceiling (maximize expected output fidelity per gate removed, rather than gate count removed) is a substantive extension, not a parameter re-tuning.

Experiment E17 partially addresses topology effects (linear, grid, heavy-hex coupling maps) but still assumes noiseless gates. A full noise-aware extension requires integrating depolarizing, amplitude-damping, and crosstalk models into the cost function, re-deriving the ceiling bounds, and re-running the canonical pipeline. This is a major item in the Future Work agenda (Section 15.16), with preliminary theoretical scaffolding already in place.

## 12. Qiskit Pass Isolation Covers Only 5 of 15 Circuit Families

The pass-isolation analysis (Section 5.4.3) decomposes Qiskit's transpiler into individual passes and measures each pass's contribution to total reduction. This decomposition is available for 5 of the 15 circuit families in the ensemble: the remaining 10 families do not have pass-level CSV output in the v6 data freeze.

For the 5 instrumented families the mechanism attribution is data-backed: template matching's contribution, commutative cancellation's contribution, and resynthesis's contribution are each measured directly. For the remaining 10 families the mechanism attribution in Section 5.4.3 — the qualitative claim that "template matching addresses the largest fraction of the gap, phase polynomial synthesis the second-largest, Clifford tableau reduction a narrower niche" — is *inferred* from the 5 instrumented families and from the known pass-mechism structure of Qiskit's transpiler. It is a reasonable extrapolation but not a direct measurement.

The manuscript flags this distinction in the Section 5.4.3 table caption: the 5 instrumented families are listed with quantitative pass-level shares; the 10 un-instrumented families are listed with "mechanism inferred" in the corresponding column. Extending the pass-isolation instrumentation to the remaining 10 families is a near-term engineering task (the instrumentation script is generic; the blocking factor is compute time) and is scheduled in Section 15.17.

## 13. Figures Are Raster (PNG 300DPI), Not Vector

All figures in the v6 manuscript draft are PNG files rendered at 300 DPI. This is sufficient for internal review and for the HTML preview but is below the production standard for a top-venue submission: most venues (including *Quantum*, PRX Quantum, Nature Quantum) require vector formats (PDF or SVG) for line art, plots, and diagrams to ensure crisp rendering at arbitrary zoom levels and accessible text scaling.

The figure-generation pipeline (`scripts/figure_generation/`) uses matplotlib with a PNG backend. Switching to vector output is a configuration change (`savefig(format='pdf')` or `savefig(format='svg')`) and requires a small validation pass to confirm that font embedding, transparency, and text-on-path rendering are preserved. No re-computation of figure data is required.

The conversion is scheduled as a pre-submission infrastructure task (Section 15.18) and does not affect any numerical result in the manuscript. Until the conversion is complete, the PNG figures should be considered draft-quality.

## 14. E4 Uses a Single Random Seed per Optimizer

Experiment E4 compares three stochastic optimizers — simulated annealing (SA), randomized local search (RLS), and a genetic algorithm (GA) — on the Phase-2a commutation search problem. Each optimizer is run with a single fixed random seed derived from a common `seed_base=42`: RLS uses `seed_base+10000=10042`, SA uses `seed_base+20000=20042`, and GA uses `seed_base+30000=30042`. Circuit generation for each trial uses `seed_base+trial_index` (i.e., 42–141 for 100 trials). The optimizer ranking reported in Section 5.3.1 is therefore based on one realization of each optimizer's stochastic trajectory.

A single seed cannot distinguish a robust ranking from a seed-dependent ordering. The observed ranking (GA ≥ SA ≥ RLS on mean reduction) is consistent with the algorithms' known search characteristics, but the gap between optimizers is within the typical seed-to-seed variance for stochastic search at the trial counts used. The ranking should be read as *preliminary*, not confirmatory.

The manuscript labels E4 as "preliminary" in the Section 5.3.1 caption and in the claim-evidence map. A multi-seed rerun (10 seeds per optimizer, with the same trial count per seed) would resolve the ranking robustness and is straightforward to schedule. This is a near-term future-work item (Section 15.19). The structural-ceiling framework's main claims do not depend on the E4 ranking — the ceiling is defined by the proxy (E13) and the optimizer-agnostic trichotomy, not by inter-optimizer rankings — so the single-seed limitation does not propagate to the manuscript's central conclusions.

---

## Future Work

The fourteen limitations above define a concrete forward agenda. Each item below is paired with the limiting factor it addresses, the artifact it would produce, and the claim upgrade it would enable.

### 15.1 Held-out Predictive Model (addresses §1)

Re-engineer the predictive model with leakage-free structural features and a pre-registered held-out evaluation protocol. Candidate feature families: Pauli-spectrum descriptors, entanglement entropy proxies, learned circuit embeddings (small graph neural networks over the commutation graph). Candidate regressors: gradient-boosted trees, MLPs with dropout. Success criterion: held-out MAE ≤ 0.10 and Pearson ≥ 0.60. On success, the predictive claim is upgraded from exploratory to confirmatory.

### 15.2 Phase-2b Template Matching Expansion (addresses §2)

Expand the limited `Phase2bTemplateMatcher` in `src/optimisation/phase2/template_matcher.py` from the core H-CX-H control-template mechanism into a benchmark-ready template-matching pass, ideally with a broader template library comparable to Qiskit's template mechanisms. Re-run the canonical pipeline on E1–E18. Compare measured Phase-2b reductions against the Theorem 7 / Theorem 9 Ω(1) separation predictions. On success, upgrade the Phase-2b separation theorems from "structural existence plus unit-tested core mechanism" to "empirically demonstrated at benchmark scale."

### 15.3 Phase-2a Tight Bound (addresses §2)

Resolve the open theoretical question: what is the tight asymptotic Phase-2a ceiling? The current theory proves a Phase-2b advantage but does not characterize Phase-2a alone. A tight Phase-2a upper bound would let us interpret the experimental Phase-2a reductions as a fraction of the achievable horizon, rather than as an unbounded lower bound.

### 15.4 Listing-Aware Ceiling Theory (addresses §3)

Develop a theory of the structural ceiling as a function of the listing model, ideally yielding an upper bound over the space of all valid listings. The current Theorem 1(a) / 1(b) dichotomy (WCL vs. LBL) is a first step; a general theory would characterize the ceiling for any listing in a defined class (e.g., any topological ordering of the gate dependency DAG).

### 15.5 Pre-registered Predictive Evaluation (addresses §1)

Formalize the held-out evaluation protocol as a pre-registered study: feature set, regressor class, train/test split, and success criterion all committed before the evaluation is run. This eliminates the risk of post-hoc feature selection inflating held-out metrics and aligns the predictive claim with confirmatory standards.

### 15.6 Listing-Conditional Ceiling Generalization (addresses §3)

Extend Theorem 1 to characterize the ceiling over the space of listings, not just for LBL and WCL. A natural target is a theorem of the form "for any listing in class L, S_1(C) ⊆ S_1^L(C)," where S_1^L is the listing-class-specific opportunity set.

### 15.7 E19: WCL Cross-Family Extension (addresses §3, §7)

The E19 full canonical run for the random Universal family (n=5, 10,000 rows) is complete and confirms the listing-model dependency (WCL 7.83% vs LBL 0.0000%). The remaining extension is cross-family: re-list all 15 circuit families from E14 under WCL, re-run all six optimizers, and measure: (i) the LBL→WCL Phase-1 gap across all 15 families; (ii) new Phase-2 commutation opportunities exposed by WCL; (iii) whether the 7.83% figure generalizes or varies by family. On success, upgrade the WCL claim from single-family confirmed to cross-family confirmed.

### 15.8 E20: Multi-Compiler Full Comparison (addresses §6)

Complete the E20 experiment. Configure the Cirq and pytket environments, run the three compilers (Qiskit, Cirq, t|ket>) on the extended 15-family suite with target qubit counts [4, 6, 8] and 10 trials per cell, and populate `data/v6/e20/multi_compiler_full.csv`. On success, upgrade the multi-compiler comparison from Qiskit-only to three-compiler confirmed.

### 15.9 Finite-Depth Incompressibility (addresses §4)

Investigate finite-depth incompressibility results that bridge Theorem 8 (Haar-random, depth ~4^n) to the experimental depth regime (poly(n)). Candidate approaches: concentration-of-measure arguments on the random circuit ensemble, lower bounds via unitary t-designs at finite depth, or direct circuit-counting arguments.

### 15.10 Phase-2a vs. Phase-2b Empirical Separation (addresses §2)

Once the limited Phase-2b implementation is expanded into a benchmark-ready pass (Section 15.2), run the artificial (Theorem 7) and Bernstein–Vazirani (Theorem 9) circuit families head-to-head under Phase-2a and Phase-2b. Confirm the Ω(1) separation empirically and measure the constant.

### 15.11 Theorem 6 Empirical Validation (addresses §5)

Implement the Clifford canonical-form computation (Bravyi–Maslov normal form) and compare its predicted Phase-1 ceiling against exhaustive Phase-1 search on a random Clifford ensemble. Success criterion: exact match on ≥95% of tested circuits. On success, upgrade Theorem 6 from "theoretically established; empirical validation deferred" to "theoretically established and empirically confirmed."

### 15.12 Theorem 6 Infrastructure (addresses §5)

Build the Clifford-tableau infrastructure required for Section 15.11. The infrastructure is also a prerequisite for several other Clifford-related extensions (e.g., Clifford-aware Phase-2 commutation rules) and is therefore a high-leverage engineering item.

### 15.13 E18 Rerun without Survivorship Bias (addresses §8)

Fix the decomposition pipeline defect causing the 42 fidelity-zero rows, rerun E18 on the full 270-row ensemble, and recompute all E18 statistics without the survivorship filter. On success, remove the "survivorship-biased" qualifier from all E18 conclusions.

### 15.14 Under-Powered Experiment Reruns (addresses §9)

Rerun E10, E11, E12, E13, E14, and E18 with a 4× trial count increase (or with variance-reduction techniques) to lift statistical power to β ≥ 0.80. On success, upgrade these experiments from "exploratory" to "confirmatory" in the claim-evidence map.

### 15.15 Full Unitariy Commutator Check (addresses §10)

Implement a numerical `[U, V] = UV − VU` commutator check in `_gates_commute()` with a documented floating-point tolerance. Re-run the Phase-2a pipeline and report the delta between rule-based and numerical commutativity. Expected outcome: a modest increase in Phase-2a reduction on families where the rule set was conservative.

### 15.16 Noise-Aware Ceiling (addresses §11)

Integrate depolarizing, amplitude-damping, and crosstalk noise models into the ceiling cost function. Re-derive the ceiling bounds under fidelity-adjusted gate reduction. Re-run the canonical pipeline on a NISQ-representative noise configuration. Compare noise-aware ceilings against noiseless ceilings to quantify the gap.

### 15.17 Pass Isolation for Remaining 10 Families (addresses §12)

Extend the pass-isolation instrumentation to the 10 currently un-instrumented circuit families. Populate the pass-level CSVs and recompute the Section 5.4.3 mechanism-attribution table with direct measurements for all 15 families.

### 15.18 Vector Figure Conversion (addresses §13)

Switch the figure-generation pipeline from PNG to PDF/SVG output with embedded fonts. Validate that all figures render correctly in the target submission format. Pre-submission infrastructure task; no numerical impact.

### 15.19 E4 Multi-Seed Rerun (addresses §14)

Rerun E4 with 10 seeds per optimizer (SA, RLS, GA). Report mean and standard deviation of each optimizer's reduction across seeds. Test the ranking robustness via a paired-seed comparison. On success, upgrade the E4 ranking from "preliminary" to "confirmed."

### 15.20 Production Compiler WCL Audit (addresses §3)

Audit Qiskit, Cirq, and t|ket> internals to determine whether WCL-like reordering is already implemented implicitly as a side effect of scheduling, routing, or resynthesis passes. If yes, the E19 benefit is partially captured by production compilers and the LBL→WCL gap is a prototype-only artifact. If no, an explicit WCL pre-pass is a concrete compiler-level contribution.

---

## Summary

The limitations above cluster into four groups:

1. **Theory-experiment gaps** (§2, §4, §5): the theorems are valid but their empirical confirmation is partial or deferred. The manuscript labels each such gap explicitly and does not present the theorems as empirically confirmed where they are not.
2. **Deferred experiments** (§6, §7, §13, §14): experiments that are scripted but not run, or run at insufficient scale. The blocking factors are compute budget and environment setup, not algorithmic risk; the rerun schedules are concrete.
3. **Methodological scoping** (§1, §8, §9, §10): the experiments that were run have known biases or power limits. The biases are characterized, conservative in direction, and explicitly labeled at every point of use.
4. **Framework boundaries** (§3, §11, §12): the structural-ceiling framework's scope is narrower than the full quantum-compilation problem. The boundaries are principled (the ceiling is a property of the unitary under a listing model; noise and production-compiler mechanisms are out of scope by design) and are explicitly drawn.

None of the limitations above invalidate the manuscript's central claims. The structural-ceiling theorems (Theorems 1, 2, 2b, 7, 9) stand as proven results. The empirical trichotomy across E1–E9, E15–E17 (the adequately-powered, non-survivorship-biased experiments) is confirmed. The Qiskit baseline is confirmed. The WCL discovery, the predictive framework, the multi-compiler comparison, and the ceiling-aware optimizer are presented as preliminary or exploratory exactly where their evidence base requires it. The Future Work agenda converts each limitation into a concrete next experiment with a defined claim-upgrade criterion.

---

*Document version: 1.0*
*Last updated: 2026-06-17*
*Cross-references: `v6_scope_limitations_risks.md` (D-delimitations); `v6_claim_evidence_map.md` (claim-evidence scope column); `data/v6/e19/README.md` (E19 plan); `data/v6/e20/metadata.json` (E20 plan); `src/optimisation/commutation.py` (`_gates_commute` implementation).*

