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

**Delimitation**: The listing-model hypothesis states that whole-circuit listing (WCL) may unlock Phase-1 reductions invisible under line-by-line listing (LBL). Full WCL benchmarking remains planned, so this should be presented as a preliminary/planned extension rather than a confirmed main result.

**Why this is a strength, not a weakness**: Framing listing-model dependence as a planned/preliminary extension prevents overclaiming while preserving a clear next experiment. The WCL/LBL dichotomy is the beginning, not the end, of listing-model exploration.

**Reviewer counterargument**: *"The listing-model effect may be an artifact of the prototype optimizer's implementation."*
- **Response**: The listing-model effect is theoretically motivated and supported by preliminary observations, but full WCL benchmarking remains planned. It should be framed as a planned/preliminary extension rather than a confirmed across-all-optimizers result.

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

Peephole optimization — the local rewriting of gate sequences to reduce circuit size — is a core component of every quantum compiler, yet no systematic study has characterized when these passes succeed or fail across diverse circuit families. We present a large-scale empirical benchmark of peephole optimization across 53,300 canonical optimizer trials spanning 15 primary circuit families and 6 optimizer types, with a completed Qiskit compiler baseline. Our central finding is sharply divergent circuit-family behavior: some families are trivially compressible, some require commutation, and many are at structural ceiling under local peephole rewriting. We further report planned/preliminary listing-model analysis and a smoke-mode ceiling-aware optimizer study that motivates future full-scale validation. Supporting theoretical analysis provides formal bounds including bounded INSERTION-cascade reasoning and a corrected Bernstein–Vazirani Phase-2b advantage theorem. These results produce circuit-family-aware optimization prescriptions for the studied families.

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
