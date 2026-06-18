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

## 7. E19 (WCL Full Validation) Has Not Been Run

The directory `data/v6/e19/` is created as a placeholder; no experiment has been executed. E19 is designed to validate Phase-1 and Phase-2 optimization under wire-consecutive listing (WCL) on the full 45,500-circuit ensemble, addressing three questions: (i) how the structural ceiling shifts under WCL vs. LBL across all 15 circuit families; (ii) whether WCL exposes new Phase-2 commutation opportunities invisible under LBL; and (iii) whether the ~18% LBL→WCL Phase-1 gap observed in the E1 smoke study generalizes beyond the single sampled family.

E19 is deferred for computational and scope reasons. Re-listing 45,500+ circuits under WCL and re-running all six optimizers is a full-experiment-scale effort. The placeholder directory `data/v6/e19/README.md` documents the planned protocol, the deferred status, and the dependency on `framework.md §"Listing Model Dependency"`, `lemmas.md` (Theorem 1(a) vs. 1(b)), and `listing_models_and_dag_compilers.md`.

The manuscript's claims about WCL are scoped accordingly: the ~18% figure is reported as a single-family smoke observation (E1), not as a cross-family result; the WCL-related theorems (Theorem 1(a), Theorem 9) are presented as existence/structural results, not as empirical generalizations. Running E19 is the single experiment most likely to upgrade a preliminary claim to a confirmed main result; it is the top priority in the Future Work schedule (Section 15.7).

## 8. E18 (Clifford+T) Survivorship Bias

Experiment E18 evaluates Clifford+T decomposition and optimization across 270 circuit rows. Of these, 120 rows fail: 78 with `decompose_error` (the Clifford+T decomposition routine cannot encode a parameterized gate within the precision budget) and 42 with `fidelity = 0` (the decomposition succeeds but the resulting circuit is not unitarily equivalent to the input, indicating a numerical or structural defect in the decomposition pipeline). The 150 surviving rows are the basis for all E18 statistics reported in the manuscript.

This filtering introduces survivorship bias. The surviving rows are not a random sample of the original 270: they are enriched for circuits whose gate composition is amenable to Clifford+T decomposition (fewer parameterized rotations, fewer non-Clifford multi-qubit gates). Reduction rates and ceiling classifications computed on the 150 survivors may overstate the optimism of the result for the general population.

All E18 conclusions in the manuscript are labeled "survivorship-biased" at first mention in every section that invokes them (Section 5.3, Section 5.4.3, Section 6.3.5). The bias direction is conservative for our central claims: the structural-ceiling framework predicts *less* reduction on the harder circuits that failed decomposition, so the survivor-filtered mean reduction is likely an *upper* bound on the population mean. The decomposition pipeline defect causing the 42 fidelity-zero rows is a software bug, not a theoretical limitation; it is tracked as a separate infrastructure item (see `CRITICAL_BUG_FIXES_LOG.md`) and its fix is a prerequisite for any rerun of E18. A rerun on the full 270-row ensemble is scheduled as future work (Section 15.13).

## 9. Multiple Experiments Are Under-Powered

Six experiments in the canonical ensemble have statistical power below the β ≥ 0.80 threshold conventionally required for confirmatory inference: E10, E11, E12, E13, E14, and E18. The under-powering arises from a combination of small effect sizes, high within-cell variance, and limited trial counts per cell (typically 10 trials). For these experiments the probability of a Type II error is non-negligible, and a non-rejection of the null hypothesis should not be read as positive evidence for the null.

These six experiments are labeled "exploratory" in the manuscript's claim-evidence map and in the relevant table captions. They are not used as confirmatory evidence for any main claim. Their role is to provide *consistent directional evidence* that aligns with the confirmatory results from the adequately-powered experiments (E1–E9, E15–E17); where an under-powered experiment is the sole support for a claim, the claim is downgraded to conjecture or removed.

Adequately-powered reruns require either larger trial counts (a 4× increase in trials would lift most cells to β ≥ 0.80 for the observed effect sizes) or variance-reduction techniques (common random numbers, antithetic variates, stratified sampling across circuit seeds). Both are straightforward engineering items; the blocking factor is compute budget. The rerun schedule is in Section 15.14.

## 10. `_gates_commute` Is a Conservative Lower Bound

The Phase-2a commutation check `_gates_commute()` in `src/optimisation/commutation.py` implements a *sufficient-condition* test for gate commutativity. The current rule set covers: Pauli-frame commutativity (single-qubit Pauli gates and Clifford generators on disjoint qubit supports), and an extended SWAP/CZ pair check added in v6. A gate pair that does not match any rule is treated as non-commuting, even if a full unitary commutator check would certify commutativity.

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

Experiment E4 compares three stochastic optimizers — simulated annealing (SA), randomized local search (RLS), and a genetic algorithm (GA) — on the Phase-2a commutation search problem. Each optimizer is run with a single fixed random seed: `seed=42` for SA, `seed=17` for RLS, `seed=2026` for GA. The optimizer ranking reported in Section 5.3.1 is therefore based on one realization of each optimizer's stochastic trajectory.

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

### 15.7 E19: WCL Full Validation (addresses §3, §7)

Run the E19 experiment as specified in `data/v6/e19/README.md`. Re-list all 45,500+ circuits under WCL, re-run all six optimizers, and measure: (i) the LBL→WCL Phase-1 gap across all 15 families; (ii) new Phase-2 commutation opportunities exposed by WCL; (iii) the consistency of the ~18% smoke observation. On success, upgrade the WCL claim from single-family smoke to cross-family confirmed.

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

Fix the decomposition pipeline defect causing the 42 fidelity-zero rows (tracked in `CRITICAL_BUG_FIXES_LOG.md`), rerun E18 on the full 270-row ensemble, and recompute all E18 statistics without the survivorship filter. On success, remove the "survivorship-biased" qualifier from all E18 conclusions.

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
*Cross-references: `v6_scope_limitations_risks.md` (D-delimitations); `v6_claim_evidence_map.md` (claim-evidence scope column); `data/v6/e19/README.md` (E19 plan); `data/v6/e20/metadata.json` (E20 plan); `src/optimisation/commutation.py` (`_gates_commute` implementation); `CRITICAL_BUG_FIXES_LOG.md` (E18 decomposition defect).*
