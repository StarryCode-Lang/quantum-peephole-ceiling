# Manuscript Working Draft

> **Status note (2026-07-21, v8)**: This v8 draft integrates the wave-1 review outcomes into the v7 restructure. Changes relative to v7: (i) structured abstract; (ii) new §1.4 with falsifiable hypotheses H1–H5 and pre-registered decision rules; (iii) the trichotomy taxonomy is now stated identically in the abstract, §6.3, §7.1 and the E15/E20 tables (3 genuine + 5 prototype-limited + 2 practical-ceiling + 1 borderline); (iv) full-scale Phase-2b v2 results (E25, `data/v8/phase2b_full/`, 729 rows at integration; 735 after the wave-4 QuantumWalk n=8 fill) integrated as §6.4, replacing the fixture-scale caveat; (v) §6.6 rewritten around the repaired ceiling-aware model (mechanism features, LOFO); (vi) SOTA tables S1–S5 with the corrected Cirq pipeline numbers integrated as §6.5; (vii) full 17-row theory–experiment cross-validation scorecard in §6.7; (viii) E18 ITT analysis in §6.8; (ix) E22 shuffler control and E29 multi-seed rerun integrated; (x) 18 figure references wired to `analysis/figures/*.pdf`; all body tables numbered; (xi) statistical claims re-verified against the canonical FDR table; (xii) reference list repaired (two fabricated entries removed/replaced, four bibliographic corrections, three additions) and renumbered contiguously. The v7 draft is preserved as `manuscript.md.bak-20260721-003505`. Realized length: ~1,085 lines with 18 figure references and 22 numbered tables integrated. **Wave-3 revision (2026-07-21):** documentation-consistency sweep — (xiii) E22 registry family count corrected to 16; (xiv) §6.4 Wilcoxon p-values recomputed from raw per-instance pairs; (xv) §7.2 E22 statistics aligned with §6.2; (xvi) power-analysis disclosure added to §5.2 and per-cell design parameters to §6.1; (xvii) new evidence paragraphs: E29 per-seed sign consistency (§6.1.1), E19-extended cross-family WCL validation (§6.2), E14 per-family corroboration (§6.3), per-size BV bound table (Table 11b, §6.4), E24 Theorem-7 validation detail (§4.2), Cirq pipeline-correction provenance (§6.5), EHW protocol detail (§7.4); (xviii) cross-references to Appendices D, E, and F wired from the body text. **Wave-4 revision (2026-07-21):** (xix) §6.6 adopts the mechanism-gate + random-forest hybrid ceiling model (LOFO MAE 0.0172 [0.0129, 0.0218], pooled $r = 0.977$ [0.963, 0.987], $\rho = 0.853$, $R^2 = 0.954$; held-out CNOT fold MAE 0.745 $\to$ 0.000), with the post-hoc-selection caveat retained; (xx) the flagship listing-model claim is scoped to listing-based peephole optimizers after the production-compiler audit (DAG/moment IRs are listing-invariant by representation); (xxi) the Phase-2b grid now covers QuantumWalk $n = 8$ (E25: 735 rows; corpus total 82,721) and pooled Phase-2b bootstrap CIs are restated from the refreshed grid; (xxii) fig04 regenerated after an optimizer-label fix and now matches its caption. **Wave-5/6 revision (2026-07-21):** (xxiii) E25 Phase-2b grid closed to the full factorial — 2,427 rows, depth families 56/56 $(n, \mathrm{depth})$ combinations, zero fidelity failures (§6.4, Tables 4 and 10, abstract and limitations updated); (xxiv) corpus totals updated to 36 canonical datasets / 82,721 rows; (xxv) §6.6 adds the 20-family LOFO robustness note (pooled MAE 0.0188, $r = 0.967$; family-mean $r = 0.780$ pure-RF / 0.887 gated) and §7.5 records the RepetitionCode fold failure (MAE 0.303, $r = -0.826$); (xxvi) wave-6 rerun reconciliation (E12–E17, E19, E21) integrated as §7.5 item 20 — canonical retained for all eight rerun experiments, with a unified IQP sensitivity statement; (xxvii) production-compiler relisting coverage completed to 15/15 families (6,652 rows; 0/126 sensitive combinations), §7.6 item 5 updated.

---

# Columnar Representation Example Sensitivity and Search Space Stratification in Quantum Circuit Optimization

> **Author information**: Author names are placeholders and will be filled in prior to submission.

## Abstract

**Background.** The reachable action space of a local optimizer is a property of the (object, representation) pair, not of the object alone. Peephole optimization — local rewriting of bounded gate sequences — is a core pass in every quantum compiler, yet no systematic study has characterized when these passes succeed, why they fail, or how the circuit's data-structural representation constrains them.

**Methods.** We benchmark 6 optimizer types across 15 circuit families (82,721 rows, 36 canonical datasets, experiments E1–E29), prove listing-model ceiling theorems, and validate theory against experiment including production compilers (Qiskit 2.4.1, Cirq 1.6.1, t|ket> 2.18.0) under a fair no-coupling-map protocol.

**Results.** We identify *columnar representation example sensitivity*: under layer-by-layer listing (LBL), the Phase-1 action space is provably empty for $n \geq 2$ (Theorem 1(b)) — exactly **0.0000%** gate reduction across **25,000** random circuits (E1); under wire-consecutive listing (WCL), the same circuits yield **7.83%** mean reduction (E19, 10,000 rows, fidelity = 1.0). Across 15 families a categorical trichotomy emerges: 100% reduction (CNOT chains), commutation/template-enabled reduction (oracle/Clifford circuits), and ~0% on the remainder — 3 families at genuine structural ceiling (QFT, GHZ, SurfaceCode; no tested compiler reduces them), 5 at prototype action-space ceiling where t|ket> achieves 6–64%, 2 at practical ceiling where every tested production compiler also fails (Adder, QuantumWalk), and 1 borderline (HaarRandom, ≤ 6.5 pp production gains). The lead result is that the prototype ceiling itself is not structural: the full-scale Phase-2b pipeline (inverse-cancellation closure plus conjugation templates) reaches the **provable $k+2$ gate optimum on every Bernstein–Vazirani instance** ($n = 3$–$10$, 80/80, mean reduction 69.2%, worst case 54.5%, exceeding the rigorous Theorem 9 bound by 3.1–4.2×), and achieves 92.0% on IQP, 51.6% on RandomClifford, and 40.2% on Structured brickwork — families that sat at or near 0% under Phase-1/Phase-2a. A ceiling-aware pipeline skips futile passes with bit-identical output (1.6×–228× speedup on training families); its hybrid predictive model — a mechanism-derived saturation gate over a random-forest regressor — generalizes strongly under leave-one-family-out validation (MAE 0.0172 vs 0.0963 predict-0 baseline; pooled $r = 0.977$) while family-mean prediction remains unreliable for unseen high-compression mechanisms — reported with its post-hoc-selection caveat and remaining limitations (§6.6).

**Conclusions.** Peephole optimization behavior is representation-dependent: the "optimization desert" is a property of the (circuit, listing) pair, not the circuits; and several presumed structural ceilings are properties of the move/template library, not the circuit family. Wire-traversal preprocessing, family-aware pass routing, and template-library completion are concrete, implementable compiler-design consequences.

**Keywords**: quantum circuit optimization; peephole optimization; quantum compilers; circuit representation; template matching; commutation rewriting; structural ceiling; Bernstein–Vazirani.

---

## 1. Introduction

### 1.1 Motivation

Peephole optimization — the local rewriting of bounded gate sequences to reduce circuit size — is a core component of every quantum compiler [Barenco et al. 1995, Maslov et al. 2008]. This approach traces its lineage to classical compiler theory, where McKeeman [1965] introduced peephole optimization as a final pass over machine code, and Massalin [1987] developed superoptimization through exhaustive search over small instruction windows. In the quantum setting, peephole optimization encompasses adjacent gate cancellation (removing $U \cdot U^{-1}$ pairs), template matching (applying pre-computed equivalence rules such as $H \cdot X \cdot H = Z$), and commutation-based reordering (exploiting gate commutativity to expose non-adjacent cancellation opportunities) [Amy et al. 2013, Nam et al. 2018].

Production compilers (Qiskit, Cirq, t|ket>) routinely achieve 10–40% gate-count reduction through sequences of local rewrite and synthesis passes, yet no systematic study has characterized *when* these passes succeed, *why* they sometimes fail entirely, or what representation-conditional limits constrain achievable reductions. This opacity encourages broad pass application, wasting computational resources on circuits that resist the tested local rewriting model while potentially missing opportunities for deeper optimization on amenable structures.

The economic stakes are acute in fault-tolerant architectures, where each logical T gate requires magic state distillation consuming approximately 1,000–10,000 physical qubits [Fowler et al. 2012]. A 10% reduction in T-count for Shor's algorithm at cryptographic key sizes can translate to savings of millions of physical qubits and hours of runtime. Yet current compilers achieve their reductions through heuristic pass sequences whose effectiveness varies unpredictably across circuit families. A compiler developer has no principled basis for deciding whether to invest additional computational budget in optimization passes for a given circuit, or whether the circuit has reached its fundamental optimization ceiling and further passes are futile. This resource allocation problem — how to distribute finite compilation time across optimization passes — is currently solved by applying all available passes unconditionally, a strategy that wastes resources on provably inoptimizable circuits while potentially under-investing in circuits with substantial optimization headroom.

Despite advances in automated identity generation [Xu et al. 2022 (Quartz), Pointing et al. 2024 (Quanto)], reinforcement learning [Li et al. 2024 (Quarl), Riu et al. 2025 (ZX+RL)], and tensor decomposition [Ruiz et al. 2025 (AlphaTensor-Quantum)], a fundamental disconnect persists between compiler practice and optimization theory. Production compilers operate as black boxes: they apply optimization passes and report the achieved reduction, but they do not explain why certain circuits yield substantial gains while others resist all optimization attempts. Theoretical complexity results establish that optimal circuit optimization is QMA-hard [Janzing et al. 2003], yet this worst-case hardness provides little guidance for the average-case behavior encountered in practice. The Gottesman–Knill theorem [Gottesman 1997] establishes that Clifford circuits are polynomial-time optimizable, suggesting that the hardness landscape is far more nuanced than worst-case analysis implies.

The field lacks a systematic framework for answering the most basic questions: What fraction of circuits are fundamentally inoptimizable by peephole methods? For which circuit families does commutation-based rewriting provide measurable advantage? How does the circuit representation — the data-structure ordering of gates — affect optimization outcomes?

### 1.2 The Discovery: Columnar Representation Example Sensitivity

A critical methodological discovery emerged during our investigation: the circuit listing model — the data-structure ordering of gates — fundamentally affects optimizer behavior in ways that have not been previously recognized. We call this phenomenon **columnar representation example sensitivity**: the observation that the same quantum circuit, when represented with different gate orderings in the instruction sequence, produces dramatically different optimization outcomes under peephole methods.

Quantum circuits can be represented in two natural listing formats. In **wire-consecutive listing (WCL)**, gates on the same qubit wire are placed consecutively in the circuit data structure, reflecting the natural representation in circuit diagrams and some synthesis tools. In **layer-by-layer listing (LBL)**, the circuit is generated and stored layer by layer, with one gate per qubit per layer; gates on the same qubit $q$ at layers $L$ and $L+1$ are separated by $n-1$ intervening gates from other qubits, where $n$ is the qubit count.

This seemingly innocuous data-structure choice has profound implications. We prove (Theorem 1(b)) that under LBL with $n \geq 2$, the Phase-1 action space is structurally empty: $\mathcal{S}_1(C) = \emptyset$ for every circuit $C$, where $\mathcal{S}_1(C)$ denotes the set of all adjacent gate pairs $(g_i, g_{i+1})$ such that $g_{i+1} = g_i^{-1}$ and both act on the same qubit(s). The proof is elementary but consequential: under LBL, the gate on qubit $q$ at layer $L$ is at listing index $L \cdot n + q$, while the next gate on the same qubit appears at index $(L+1) \cdot n + q$, yielding a gap of $n \geq 2$. Since Phase-1 requires listing adjacency (gap $= 1$) on the same qubit(s), no Phase-1 action is possible regardless of the circuit's gate content. Consequently, $R_1(C) = 0$ for every Phase-1 optimizer applied to LBL-represented circuits.

This theorem explains previously puzzling zero-variance results in our early experiments (25,000 trials with LBL representation) and has significant practical implications. When circuits are represented in WCL instead of LBL, the Phase-1 action space can become non-empty for circuits containing wire-consecutive inverse pairs. Experiment E19 (10,000 rows) confirms that WCL preprocessing achieves approximately **7.83%** mean reduction on random universal circuits where LBL yields exactly **0.0000%**.

This discovery reframes the optimization landscape: the apparent "optimization desert" — zero reduction across 25,000 trials — is a property of the (circuit, listing) pair, not of the circuits themselves. The circuits contain wire-level inverse pairs; LBL merely hides them from listing-adjacent Phase-1 detection. Crucially, Phase-2 commutation rewriters — which operate on the circuit graph rather than the listing — are unaffected by this representation dependency, since they reason about wire-level adjacency rather than listing adjacency. This discovery necessitates a methodological recommendation: future experiments should either adopt WCL as the default listing model for Phase-1 evaluation, or include a wire-traversal preprocessing step to ensure that Phase-1 results reflect the circuit's intrinsic structure rather than an artifact of the data-structure ordering. One scope qualification applies throughout: the listing-model claims in this paper characterize *listing-based* peephole optimizers. Production compilers that represent circuits as DAGs or moment sequences (Qiskit, Cirq, t|ket>) define their peephole windows per wire or per connected component, so they are insensitive to the flat listing — their intermediate representation already occupies the WCL-equivalent action space by construction (`docs/analysis/compiler_listing_audit.md`; §7.2).

### 1.3 Research Questions

We formulate three research questions:

**RQ1: How does the circuit listing model affect peephole optimization outcomes, and what are the implications for compiler design?** This question investigates the practical impact of data-structure choices on optimization effectiveness and develops guidelines for representation-aware compiler implementation. It is motivated by our discovery of columnar representation example sensitivity (Theorem 1(b)).

**RQ2: What is the structure of the peephole optimization search space across diverse circuit families?** We seek to quantify the prevalence of optimization barriers and identify the structural properties that determine which circuits are optimizable by which peephole techniques. This question subsumes the former "phase transition" hypothesis — our initial conjecture of a depth-driven critical phenomenon, which the data refuted; we now use "search space stratification" to denote the observed categorical division into optimization regimes.

**RQ3: Where do production compilers operate beyond the local peephole model, and can ceiling knowledge improve compiler efficiency?** We aim to map the boundary between local peephole scope and global synthesis mechanisms, and to investigate whether representation sensitivity and stratification knowledge can enable ceiling-aware optimization that skips futile passes.

### 1.4 Hypotheses and Decision Rules

The research questions are converted into five falsifiable hypotheses with pre-registered decision rules. Each hypothesis maps to already-executed experiments; no new data collection was required for this reanalysis. Each Results subsection cross-references the hypotheses it tests.

**Table 1. Falsifiable hypotheses and decision rules.**

| ID | Hypothesis | Decision rule (rejection criterion) | Primary evidence | Verdict |
|----|-----------|-------------------------------------|------------------|---------|
| H1 | Under LBL, Phase-1 reduction is exactly 0 for every family with $n \geq 2$ | Rejected if any LBL trial yields reduction $> 0$ | E1–E5, E14 (0 nonzero outcomes in 45,500+ trials) | Supported |
| H2 | WCL preprocessing yields strictly positive mean Phase-1 reduction on random Universal circuits | Rejected if the WCL mean is $\leq 0$ or its 95% CI includes 0 | E19 (7.83% $\pm$ 3.95%, fidelity = 1.0) | Supported |
| H3 | Phase-2 commutation advantage $\Gamma(C) > 0$ iff the family contains commutation-accessible inverse pairs | Rejected if a family with no commutation path shows $\Gamma > 0$ | E10/E14/E16 (Oracle/Clifford $> 0$; QFT/GHZ/Structured $= 0$ under Phase-2a) | Supported |
| H4 | The stratification is categorical, not gradual: inter-family reduction levels cluster at $\{100\%,\ 14\text{–}28\%,\ \sim 0\%\}$ | Rejected if $\geq 3$ families show intermediate levels (e.g., 40–80%) | E14/E15 (supported under Phase-1/2a); E25 Phase-2b v2 moves IQP (92.0%) and Structured (40.2%) into the intermediate band | Supported with Phase-2b qualification (§6.4) |
| H5 | Ceiling-aware skipping is output-neutral | Rejected if any skipped-run output differs in gate count from the naive pipeline | E21 (1,140 rows; 570/570 paired trials bit-identical) | Supported |

H1–H3 and H5 survive every test we could construct against them; H4 survives under the Phase-1/Phase-2a model and is refined — not refuted — by the Phase-2b v2 results of §6.4, which show that part of the "~0%" band was an artifact of template-library coverage rather than of circuit structure.

### 1.5 Contributions

This paper makes three contributions, in order of centrality.

**Contribution 1 (core): Columnar representation example sensitivity — formalization and empirical validation.**

- **What**: A formal characterization of how circuit listing order governs optimizer behavior. Theorem 1(b) proves that LBL makes the Phase-1 action space structurally empty for $n \geq 2$, explaining previously puzzling zero-variance experimental results. Theorem 1(a) establishes the density bound for WCL: $\mathbb{E}[|\mathcal{A}_{\text{adj}}(C)|] \leq n(d-1)[(1-\rho)^2/g_1^2 + \rho^2/(g_2(n-1))]$.
- **Why**: This identifies the data-structure ordering — not the optimization algorithm — as the key factor determining Phase-1 outcomes. The representation, not the circuit content alone, governs whether peephole optimization can detect cancellation opportunities. Across 45,500 trials and four algorithmically distinct optimizers, the ceiling under a fixed listing is identical — representation choice dominates algorithm choice, overturning the conventional wisdom that peephole outcomes are primarily a question of optimizer design.
- **Evidence**: E19 (10,000 rows) confirms that WCL achieves 7.83% mean reduction (std = 3.95%, max = 33.33%, fidelity = 1.0) on the same random ensemble where LBL yields exactly 0.0000%. E1 (25,000 trials) establishes the LBL ceiling with zero variance. E23 (160 circuits, $n = 3$–$10$) validates Theorem 6: Clifford circuits in Aaronson–Gottesman canonical form achieve 0.000% across all 160 instances. E22 (2,240 rows) adds the random gate-shuffle control: shuffling the listing does not reproduce the WCL benefit in a representation-neutral way — it *increases* mean reduction from 6.30% (original listing) to 10.34% (Mann–Whitney $p = 6.8\times10^{-15}$), while WCL reaches 12.20%, confirming that the effect tracks listing structure, not listing disruption.

**Contribution 2 (supporting): Search space stratification across 15 circuit families — and its partial refutation by full-scale Phase-2b.**

- **What**: A large-scale empirical benchmark revealing a categorical trichotomy: 100% Phase-1 reduction (CNOT chains), commutation-enabled Phase-2 reduction (oracle/Clifford circuits), and ~0% on 11 of 15 families — of which 3 (QFT, GHZ, SurfaceCode) are genuine structural ceilings (no tested compiler reduces them), 5 are prototype-limited (VQE, HardwareEfficient, IQP, UCCSD, QAOA; t|ket> achieves 6–64%), 2 are practical ceilings where every tested production compiler also fails (Adder, QuantumWalk), and 1 is borderline (HaarRandom, production gains ≤ 6.5 pp).
- **Why**: Provides the first systematic characterization of when peephole optimization succeeds and fails across diverse circuit families, with circuit-family optimization prescriptions for compiler design. The stratification is not a gradual spectrum but a categorical division determined by algebraic structure — and the Phase-2b v2 experiment (E25) shows that the boundary of the "incompressible" class is itself move-set-dependent: IQP moves from 0.5% (Phase-2a) to 92.0% (Phase-2b v2), Structured from 0.0% to 40.2%, and the BV oracle family to its provable $k+2$ optimum (69.2% mean over secrets), the single most citable result of this study.
- **Evidence**: 82,721 rows across 36 canonical datasets spanning 15 circuit families and 6 optimizer types (E1–E29), supplemented by E23/E24 theory-validation experiments (235 trials), E20/SOTA multi-compiler comparison (Qiskit/Cirq/t|ket>, 10 trials per cell, fair no-coupling-map mode), and E25 Phase-2b full-scale validation (2,427 rows, fidelity $\geq 1 - 2\times10^{-13}$ on every row). The scale exceeds prior efforts — Quartz (~100 benchmarks), Quarl (~50 benchmarks), Micro-Benchmark Suite (6 circuits) — by two orders of magnitude.

**Contribution 3 (application, with acknowledged limitations): Ceiling-aware optimizer.**

- **What**: A proxy-guided pipeline that uses representation and stratification knowledge to skip futile optimization passes, achieving 1.6×–228× speedup (aggregate 34.97× as $\sum t_{\text{naive}}/\sum t_{\text{ca}}$; unweighted family-mean 22.64×) on E21 (1,140 rows) while producing bit-identical output circuits.
- **Why**: If ceiling knowledge is available for a circuit family, compilation time can be reduced without sacrificing output quality — valuable for batch compilation workflows.
- **Evidence**: E21 full-mode evaluation confirms identical gate-count reduction across all 15 training families with substantial family-dependent speedup. **Critical limitations**: the E21 timing protocol is asymmetric (naive timings include per-phase exact-fidelity calls that the ceiling-aware timing excludes); under symmetric accounting the family speedups are 0.97×–11.48× (aggregate 2.20×) with output still bit-identical. A mechanism-informed predictive model repaired after an initial held-out failure achieves strong per-circuit generalization under leave-one-family-out validation (MAE 0.0172 vs 0.0963 predict-0 baseline; pooled $r = 0.977$) as a hybrid of a mechanism-derived saturation gate and a random-forest regressor — a post-hoc revision validated on a single dataset; family-mean prediction improves at $n = 20$ folds ($r = 0.780$ pure-RF, 0.887 gated) but remains unreliable for unseen high-compression mechanisms — all reported in full in §6.6.

### 1.6 Paper Organization

Section 2 provides background on the quantum circuit model, listing models, peephole optimization, and quantum compilers. Section 3 presents the core contribution: columnar representation example sensitivity, including formal definitions (Theorem 1), the E19 flagship experiment, and practical implications. Section 4 develops the theoretical framework: Phase-1/2 taxonomy, reduction ceiling theorems, and context-dependent advantage constructions. Section 5 describes experimental methods. Section 6 presents empirical results organized around the three research questions. Section 7 discusses implications, limitations, and future work. Section 8 concludes.

---

## 2. Background and Notation

### 2.1 Quantum Circuit Model

A quantum circuit $C = (g_1, g_2, \ldots, g_m)$ is a finite ordered sequence of gates from a gate set $\mathcal{G}$ acting on $n$ qubits with $|C| = m$. Two circuits are unitarily equivalent ($C \equiv C'$) if $U(C) = U(C')$. The average gate fidelity is $F_{\text{avg}}(C, C') = (|\text{Tr}(U^\dagger U')|^2 + d)/(d^2 + d)$ where $d = 2^n$. We use the standard universal gate set $\mathcal{G} = \{H, T, T^\dagger, S, S^\dagger, R_x(\theta), R_y(\theta), R_z(\theta), X, Y, Z, \text{CNOT}, \text{CZ}\}$, where $H$ is the Hadamard gate (self-inverse), $T$ and $T^\dagger$ are the $\pi/8$ gate and its inverse, $S$ and $S^\dagger$ are the phase gate and its inverse, $R_\alpha(\theta)^{-1} = R_\alpha(-\theta)$, and CNOT/CZ are self-inverse. This gate set is universal: any $n$-qubit unitary can be approximated to arbitrary precision $\epsilon$ using $O(4^n \log(1/\epsilon))$ gates [Nielsen & Chuang 2010, Dawson & Nielsen 2006].

### 2.2 Listing Models

The listing model — the data-structure ordering of gates — plays a critical role in determining optimizer behavior, as established in Section 1.2 and formalized in Section 3. The choice of listing model is not merely an implementation detail; it fundamentally determines whether Phase-1 optimizers can detect wire-level inverse pairs. Throughout this paper, we explicitly report the listing model used in each experiment and provide wire-traversal preprocessing for LBL-represented circuits when Phase-1 evaluation is intended.

**Wire-consecutive listing (WCL).** Gates on the same qubit wire appear as a contiguous block. Under WCL, two successive gates on the same qubit are listing-adjacent, so inverse pairs are directly visible to Phase-1 optimizers.

**Layer-by-layer listing (LBL).** Gates are organized into layers with at most one gate per qubit per layer, listed in layer-major order. Under LBL, the gate on qubit $q$ at layer $\ell$ is at index $\ell \cdot n + q$, and the next gate on the same qubit is at index $(\ell+1) \cdot n + q$, yielding a gap of $n \geq 2$. As proven in Theorem 1(b), this makes the Phase-1 action space structurally empty.

### 2.3 Peephole Optimization

Peephole optimization examines small "peephole" windows of instructions and replaces inefficient patterns with optimal equivalents. The technique was introduced by McKeeman [1965] as a final pass in classical compilers. Massalin [1987] extended this to superoptimization — exhaustive search for optimal instruction sequences — which is NP-hard in general but practical for small windows. Tanenbaum et al. [1982] proved that peephole optimization with a finite pattern set is not Turing-complete, establishing fundamental limits on the technique's expressive power.

In the quantum setting, peephole optimization was formalized by Barenco et al. [1995], who established the first quantum circuit synthesis bounds. Several paradigms have emerged:

**Template-based optimization** [Maslov et al. 2008, Amy et al. 2013]: Pre-computed equivalence rules (e.g., $H \cdot X \cdot H = Z$, $\text{CNOT} \cdot \text{CNOT} = I$) are scanned for and applied. Template matching is a subgraph isomorphism problem (NP-hard in general), and template libraries are finite, limiting coverage. Iten et al. [2022] give exact and practical pattern-matching algorithms; VOQC [Hietala et al. 2021] formalizes and verifies a peephole-class optimizer in Coq; equality saturation [Yang et al. 2026] replaces ordered rewriting with e-graph exploration over circuit identities; SSR [Huang et al. 2025] combines commutation-aware rearrangement with SAT-solver rewrites of CNOT subcircuits.

**Commutation-based optimization** [Nam et al. 2018, Iten et al. 2022]: Gates that commute can be reordered to expose cancellation opportunities. The commutation graph of a circuit has gates as vertices and commutation relations as edges; finding optimal reorderings is equivalent to finding maximum independent sets.

**Phase polynomial optimization** [Amy and Mosca 2019]: For circuits with $R_z$ gates, rotations are represented as a polynomial over $\mathbb{Z}_2$ and simplified via Gaussian elimination. This achieves exponential improvements for certain families but applies only to CNOT+$R_z$ circuits.

**ZX-calculus approaches** [Duncan et al. 2020, de Beaudrap et al. 2022, Riu et al. 2025]: Circuits are translated into ZX-diagrams, simplified using graph-theoretic transformations, and extracted as optimized circuits; the extraction step itself can be #P-hard in the worst case [de Beaudrap et al. 2022]. Recent work combines ZX with reinforcement learning, achieving up to 40% reduction on Clifford+T circuits with up to 40 qubits.

Our framework introduces a two-phase taxonomy: **Phase 1** (adjacent cancellation, window size $w = 2$) and **Phase 2** (commutation rewriting, $w \geq 3$; Phase-2b adds template matching on commutation-exposed patterns). The Phase-1 action space is $\mathcal{S}_1(C) = \{(g_i, g_{i+1}) : Q(g_i) = Q(g_{i+1}), g_{i+1} = g_i^{-1}\}$; the extended Phase-2 action space is $\mathcal{S}_{1+2}(C) = \{(g_i, g_k) : g_k = g_i^{-1}, \text{all intermediates commute}\}$, with $\mathcal{S}_1(C) \subseteq \mathcal{S}_{1+2}(C)$. The optimization gap $\Gamma(C) = R_{1+2}^*(C) - R_1^*(C)$ quantifies Phase-2 advantage. The relationship is hierarchical: Phase 2 subsumes Phase 1, but the additional computational cost ($O(|C|^2)$ or higher) is only justified when $\Gamma(C) > 0$.

### 2.4 Computational Complexity

Circuit Identity Testing (CIT) — determining whether two quantum circuits implement the same unitary — was proven QMA-complete by Janzing et al. [2003]. Since optimal circuit optimization requires CIT as a subroutine, optimal optimization is at least QMA-hard. However, the complexity landscape becomes more nuanced when restricted to specific circuit classes. Gottesman [1997] introduced the stabilizer formalism, providing a polynomial-time representation of Clifford circuits. Aaronson and Gottesman [2004] showed that Clifford circuit simulation and optimization are in P. For Haar-random unitaries, Nielsen [2005] and Harrow and Montanaro [2017] established that the circuit complexity satisfies $\mathcal{C}(U) \geq 4^n/n^2$ with high probability over the Haar measure. These results provide lower bounds on circuit complexity but do not directly address the optimization problem for specific circuit families.

### 2.5 Quantum Compilers

Modern quantum compilers implement multi-pass optimization pipelines. **Qiskit** (IBM) [Qiskit 2024] implements a four-level pipeline (0–3) including basis translation, layout, routing, and optimization via template matching (~50 patterns), commutation, and cancellation. **Cirq** (Google) [Cirq 2023] uses moment-based optimization with `MergeInteractions` and `EjectZ` (phase polynomial style), achieving 5–20% reduction. **t|ket>** (Cambridge Quantum) [Sivarajah et al. 2020] uses `FullPeepholeOptimise` with Clifford simplification, gate cancellation, and commutation-based reordering, achieving 15–40% reduction.

The gap between production compilers and peephole optimizers is not merely quantitative (10–40% vs. 0–20% reduction) but qualitative: production compilers employ mechanisms that fundamentally exceed the local peephole model, including template matching beyond the 2-gate window, phase polynomial optimization on algebraic structure, and global synthesis replacing entire circuit segments.

### 2.6 Circuit Families

We study 15 primary circuit families spanning random, algorithmic, variational, and error-correcting circuits. The roster below is the benchmark suite used uniformly by the 15-family experiments (E12–E22, E25) and is identical to the roster classified in §6.3:

**Table 2. The 15 benchmark circuit families.**

| # | Family | Gate Set | Category |
|---|--------|----------|----------|
| 1 | HaarRandom (universal random) | $\{H, T, T^\dagger, R_z, \text{CNOT}\}$ | Random |
| 2 | RandomClifford | $\{H, S, \text{CNOT}\}$ | Random |
| 3 | QFT | $\{H, R_z(\pi/2^k), \text{CNOT}\}$ | Algorithmic |
| 4 | GHZ | $\{H, \text{CNOT}\}$ | Algorithmic |
| 5 | Oracle (BV) | $\{H, X, \text{CNOT}\}$ | Algorithmic |
| 6 | CNOT Chain | $\{\text{CNOT}\}$ | Algorithmic |
| 7 | Grover | $\{H, X, Z, \text{MCX}\}$ | Algorithmic |
| 8 | Quantum Adder | $\{X, \text{CNOT}, \text{CCX}\}$ | Algorithmic |
| 9 | Quantum Walk | $\{H, X, R_y, \text{MCX}\}$ | Algorithmic |
| 10 | IQP | $\{H, R_z, \text{CZ}\}$ | Algorithmic |
| 11 | QAOA | $\{H, R_{zz}, R_x\}$ | Variational |
| 12 | VQE (TwoLocal) | $\{R_y, R_z, \text{CNOT}\}$ | Variational |
| 13 | HardwareEfficient | $\{R_y, R_z, \text{CNOT}\}$ | Variational |
| 14 | UCCSD (inspired) | $\{R_x, R_y, \text{CNOT}\}$ | Variational |
| 15 | Surface Code | $\{H, X, \text{CNOT}\}$ | Error-correcting |

Two naming notes keep the roster consistent across experiments. (i) The synthetic *Universal random* ensemble of the early listing experiments (E1–E5, E10, E19) is the same generator family reported as **HaarRandom** in the 15-family benchmark suite; the Phase-2b v2 experiment (E25) reports it under the name *Universal*. (ii) The *Structured* brickwork family appears in the random-ensemble experiments (E10) and in E25 (40.2% under Phase-2b v2), but is not part of the 15-family benchmark suite, which instead covers the variational UCCSD family; E25 therefore covers 16 families (the 15 of Table 2 with Universal and Structured explicit, minus HaarRandom).

**Random families.** Universal/HaarRandom circuits are generated in LBL format with configurable two-qubit gate density $\rho \in [0, 1]$. RandomClifford circuits use only stabilizer generators $\{H, S, \text{CNOT}\}$ and are efficiently simulable by the Gottesman–Knill theorem. Structured brickwork circuits alternate even- and odd-indexed CNOT layers.

**Algorithmic families.** QFT and GHZ circuits are already gate-optimal as generated (no redundant gates), serving as negative controls. The Oracle/BV circuit is the natural family from Theorem 9, with a random secret string $s \in \{0, 1\}^n$. Grover circuits use a single iteration with a phase oracle. Quantum adders implement ripple-carry addition using Toffoli gates. Quantum walks use coined walks with multi-controlled increment operators. IQP circuits consist of Hadamard-diagonal-Hadamard structure.

**Variational families.** QAOA circuits use line-graph cost functions with $R_{zz}$ and $R_x$ rotations. VQE ansätze use Qiskit's TwoLocal with $R_y$–$R_z$ rotation blocks and linear CNOT entanglement. Hardware-efficient ansätze alternate parameterized rotation layers with nearest-neighbor CNOT entanglement. UCCSD-inspired circuits use single- and double-excitation-style parameterized blocks.

All circuits are deterministically seeded (seed $= 42 + \text{offset}$), materialized by binding parameters to fixed values and decomposing composite instructions up to three levels, and fingerprinted via SHA-256 hash of the instruction stream for reproducibility.

### 2.7 Related Benchmarking Efforts

The Micro-Benchmark Suite [Merilehto 2025] evaluates six self-generated circuits (3–8 qubits) across Qiskit, t|ket>, Cirq, and Amazon Braket, measuring post-routing depth and gate counts. However, it is a measurement tool, not a theoretical framework: it reports empirical metrics without explaining *why* different compilers produce different results or characterizing structural properties that determine optimizability. Its corpus (6 circuits) is orders of magnitude smaller than our study (82,721 rows across 36 canonical datasets, 15 families). Other benchmarking efforts — MQT Bench [Quetschlich et al. 2023] and QASMBench [Li et al. 2022] — focus on circuit diversity rather than optimization-theoretic analysis. On the optimizer side, VOQC [Hietala et al. 2021] proves peephole rewrites correct in a proof assistant, Quartz/Quanto automate identity discovery, and equality saturation [Yang et al. 2026] and SSR [Huang et al. 2025] are the closest recent peephole-class systems; Table 12 (§6.5) places our prototype against production compilers on identical circuits. Despite these advances, none of the existing optimization frameworks — Quartz, Quanto, Quarl, AlphaTensor-Quantum, Relaxed Peephole Optimization, VOQC, equality saturation, SSR, or ZX+RL — provides a prototype action-space ceiling characterization, quantifies context-dependent Phase-2 advantage, or offers a systematic multi-compiler benchmark with formal theory. Our work fills these gaps.

---

## 3. Columnar Representation Example Sensitivity

This section presents the core contribution of this work: the formalization and empirical validation of columnar representation example sensitivity — the discovery that the circuit listing model is the key factor governing Phase-1 peephole optimizer behavior.

### 3.1 Formal Definitions

**Definition 11 (Wire-Consecutive Listing, WCL).** A circuit $C = (g_1, \ldots, g_m)$ is in wire-consecutive listing if, for every qubit $q$, the subsequence of gates acting on $q$ appears as a contiguous block in the listing. Formally, let $\sigma_q = (g_{i_1}, g_{i_2}, \ldots, g_{i_k})$ be the gates acting on qubit $q$ in temporal order. Under WCL, the listing indices satisfy $i_{j+1} - i_j = 1$ for all $j$ within each wire's block. Gates on different wires may be interleaved, but within each wire, successive gates are listing-adjacent.

**Definition 12 (Layer-by-Layer Listing, LBL).** A circuit $C$ is in layer-by-layer listing if gates are organized into layers $L_0, L_1, \ldots, L_{D-1}$, where each layer contains at most one gate per qubit. The listing order is layer-major: all gates of $L_\ell$ precede all gates of $L_{\ell+1}$, and within each layer, gates are listed in qubit order $q_0, q_1, \ldots, q_{n-1}$. Under LBL, the listing index of the gate on qubit $q$ at layer $\ell$ is $\ell \cdot n + q$.

The choice of listing model determines which gate pairs are "visible" to Phase-1 optimizers, which operate on listing-adjacent pairs.

### 3.2 The Core Theorem: Listing-Model Dependency

**Theorem 1 (Adjacent Inverse Pair Density and Listing-Model Dependency).**

**(a) Wire-consecutive listing.** Let $C(n, d, \rho)$ be a random circuit on $n$ qubits of depth $d$ with two-qubit gate density $\rho$, represented in WCL. Assume single-qubit gates drawn uniformly from $\mathcal{G}_1$ with $|\mathcal{G}_1| = g_1$, and two-qubit gates from $\mathcal{G}_2$ with $|\mathcal{G}_2| = g_2$. The expected number of listing-adjacent inverse pairs is:

$$\mathbb{E}[|\mathcal{A}_{\text{adj}}(C)|] = n(d-1) \cdot p_{\text{cancel}}(n, \rho),$$

where $p_{\text{cancel}}(n, \rho) = (1-\rho)^2 \cdot p_{\text{inv}}^{(1q)} + \rho^2 \cdot p_{\text{inv}}^{(2q)}(n)$. For the standard gate set:

$$\mathbb{E}[|\mathcal{A}_{\text{adj}}(C)|] \leq n(d-1)\left[\frac{(1-\rho)^2}{g_1^2} + \frac{\rho^2}{g_2(n-1)}\right].$$

*Proof.* On a fixed qubit wire, two consecutive layers both place single-qubit gates with probability $(1-\rho)^2$; the probability the second is the inverse of the first is $p_{\text{inv}}^{(1q)} \leq 2/g_1^2$ (the factor of 2 accounts for self-inverse gates and inverse pairs like $T$–$T^\dagger$). For two-qubit gates, both layers place a gate on the same qubit pair with probability $\rho^2/(n-1)$. Summing over $n$ wires and $d-1$ adjacent layer pairs by linearity of expectation yields the result. Each cancellation removes 2 gates from $|C| \approx nd/(1-\rho/2)$, so $\mathbb{E}[R_{\text{adj}}] \leq 2p_{\text{cancel}} = O(1/g_1^2 + 1/(g_2 n))$. $\blacksquare$

**(b) Layer-by-layer listing.** For $n \geq 2$ and any circuit $C$ generated under LBL:

$$\mathcal{S}_1(C) = \emptyset \quad \text{for all } C.$$

Consequently, $R_1(C) = 0$ for every Phase-1 optimizer, regardless of gate content.

*Proof.* Under LBL, the gate on qubit $q$ at layer $\ell$ occupies listing index $\ell \cdot n + q$. The next gate on the same qubit is at layer $\ell+1$, at index $(\ell+1)\cdot n + q$, a gap of $n \geq 2$. Since Phase-1 requires listing adjacency (gap $= 1$) on the same qubit(s), no Phase-1 action is possible. Furthermore, consecutive gates on the same qubit are separated by $n - 1 \geq 1$ intervening gates, so no consecutive rotation pairs exist on the same qubit. By Theorem 2(a), $R_1(C) = 0$. $\blacksquare$

**Discussion.** Theorem 1(b) reveals that the zero Phase-1 reduction observed across 25,000 trials in experiments E1–E5 is not a property of the random circuits themselves but an artifact of the LBL listing model used by the circuit generator. The circuits contain wire-level inverse pairs; LBL merely hides them from listing-adjacent detection. This has three practical implications:

1. **Listing-model awareness.** Compiler optimization passes should be designed and evaluated with explicit attention to the circuit's data-structural representation. An optimizer that appears to achieve zero reduction on one listing may achieve significant reduction on another representation of the identical circuit.

2. **Wire-traversal preprocessing.** Before applying Phase-1 optimization, a preprocessing step should reorder gates into WCL (or an equivalent wire-consecutive form), ensuring that Phase-1 results reflect the circuit's intrinsic algebraic structure rather than an artifact of the data-structure ordering.

3. **Phase-2 robustness.** Phase-2 commutation rewriters, which operate on the circuit dependency graph rather than the flat listing, are unaffected by this listing-model dependency. They reason about wire-level adjacency and commutation relations directly, making them inherently listing-model invariant.

### 3.3 Wire-Traversal Preprocessing Algorithm

The wire-traversal preprocessor transforms a circuit from any listing model into WCL, ensuring that Phase-1 optimizers can detect all wire-level inverse pairs.

**Algorithm:**
```
WCL_PREPROCESS(C):
    // Step 1: Build dependency DAG
    dag ← new DAG()
    for i = 0 to |C.data| - 1:
        dag.ADD_NODE(i)
        for each qubit q in Q(C.data[i]):
            prev ← LAST_GATE_ON_WIRE(q)
            if prev ≠ null:
                dag.ADD_EDGE(prev, i)
            LAST_GATE_ON_WIRE(q) ← i

    // Step 2: Topological sort with wire-consecutive priority
    order ← []
    visited ← {}
    for each qubit q:
        first ← FIRST_GATE_ON_WIRE(q)
        if first not in visited:
            DFS_WIRE_PRIORITY(dag, first, q, visited, order)

    // Step 3: Reorder circuit listing
    C' ← QuantumCircuit(C.num_qubits)
    for idx in order:
        C'.data.APPEND(C.data[idx])
    return C'
```

**Unitary equivalence.** The WCL reordering is a valid topological sort of the circuit's dependency DAG: it respects all ordering constraints imposed by shared qubits. Since the unitary depends only on the relative ordering of gates that share qubits (gates on disjoint qubits commute trivially), any valid topological sort preserves the implemented unitary: $U(\text{WCL}(C)) = U(C)$ exactly.

**Complexity.** DAG construction: $O(m)$. Topological sort with wire-consecutive priority: $O(m \log m)$ due to priority-queue operations. Overall: $O(m \log m)$.

### 3.4 Flagship Experiment: E19 — WCL vs LBL

Experiment E19 is the cleanest demonstration of columnar representation example sensitivity. It applies a wire-traversal preprocessing step to the same random universal circuits used in E1, converting from LBL to WCL while preserving unitary equivalence.

**Setup.** 5,000 random universal circuits at $n = 5$ qubits, depths $d = 1$–$50$, with 100 trials per depth (seed $= 42$), each evaluated under both LBL and WCL listing models (10,000 total rows). Gates drawn uniformly from $\{H, X, Y, Z, S, T, \text{CNOT}, R_x, R_y, R_z\}$ with two-qubit gate density $\rho = 0.3$.

**Table 3. E19 results: LBL vs WCL (10,000 rows).**

| Listing Model | Mean Reduction (%) | Std Dev | Max Reduction (%) | Mean Fidelity |
|:---|---:|---:|---:|---:|
| LBL | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| WCL | 7.83 | 3.95 | 33.33 | 1.0000 |

Under LBL, Phase-1 (GreedyGateCancellation) yields 0.0000% mean reduction with zero variance, confirming the Theorem 1(b) prediction. Under WCL, mean reduction is 7.83% (std = 3.95%, max = 33.33%) with perfect unitary fidelity (1.0) across all 5,000 trials. The WCL result confirms that the Phase-1 ceiling is listing-model-dependent: reordering gates by qubit wire traversal exposes adjacent inverse pairs that are structurally hidden under LBL. The benefit is broad-based rather than outlier-driven: 92.7% of the 5,000 WCL trials achieve strictly positive reduction (quartiles 5.71% / 7.92% / 10.00%; range 0.00–33.33%).

The observed effect is consistent with the density bound from Theorem 1(a): $\mathbb{E}[|\mathcal{A}_{\text{adj}}(C)|] = n(d-1) \cdot p_{\text{cancel}}(n, \rho)$, which for typical parameters yields a small but nonzero number of adjacent inverse pairs under WCL. The E22 shuffler control (§6.2) separates the effect of listing *structure* from listing *disruption*.

### 3.5 Practical Implications

The E19 result carries a direct practical implication: **wire-traversal preprocessing should be evaluated as a standard compiler pass before peephole optimization**. The transformation from LBL to WCL is computationally trivial ($O(m \log m)$) and is confirmed to unlock approximately 7.8% gate reduction that is otherwise inaccessible to Phase-1 optimizers. No production compiler (Qiskit, Cirq, or t|ket>) applies this transformation as an explicit pre-pass — and a source-level audit with a controlled relisting experiment (`docs/analysis/compiler_listing_audit.md`) explains why: their DAG/moment intermediate representations define peephole windows per wire or per connected component, so they already occupy the WCL-equivalent action space representationally and are empirically invariant to flat-list relisting. WCL preprocessing is therefore a candidate pre-pass for *listing-based* peephole optimizers, not an additive win for DAG-based production pipelines.

The WCL result does not contradict the structural-ceiling framework; it refines it. The Phase-1 prototype action-space ceiling is listing-model-dependent: under LBL, the ceiling is severe (0% reduction); under WCL, the ceiling relaxes to approximately 7.8% mean reduction. A more general theory characterizing the ceiling over the space of all valid listings is an important direction for future work.

---

## 4. Theoretical Framework

This section develops the formal apparatus underlying our analysis. All theorems are stated with proof sketches; full proofs appear in `docs/theory/formal_results.md` and the supplementary materials.

**Methodological note.** The theoretical framework was developed to explain observed experimental patterns, not to make a priori predictions. The chronology was: (1) observe 0% Phase-1 reduction on random circuits (E1, 25,000 trials), (2) identify LBL listing as the cause, (3) formalize as Theorem 1(b), (4) construct theoretical extensions (Theorems 2, 7, 9) to explain and bound the observed phenomena. The theorems should be interpreted as descriptive rather than predictive. Predictive validation — stating a theorem about an untested family, predicting its regime, then running the experiment — is an important direction for future work. The hypotheses of §1.4 are, correspondingly, post-registered against already-executed experiments rather than pre-registered before data collection.

### 4.1 Phase-1 Reduction Ceiling

**Theorem 2 (Phase-1 Reduction Ceiling).** Let $\mathcal{O}_1 = \{\text{Greedy}, \text{SA}, \text{GA}, \text{RLS}\}$.

**(a) Greedy ceiling.** If $\mathcal{S}_1(C) = \emptyset$ and no consecutive rotation gates on the same qubit admit merging, then $R_{\text{greedy}}(C) = 0$.

**(b) Stochastic ceiling.** The stochastic optimizers (SA, GA, RLS) employ additional move primitives (SWAP, COMMUTATION, INSERTION). No finite sequence of such moves can achieve a net gate-count reduction beyond what is enabled by the commutation and swap structure already latent in $C$.

*Proof sketch.* SWAP exchanges adjacent gates on disjoint qubits; it preserves the gate multiset and the relative ordering of gates on each individual wire, but can make previously non-adjacent gates listing-adjacent. If the resulting adjacent pair acts on the same qubits and is inverse, SWAP creates a new $\mathcal{S}_1$ element. However, any reduction enabled by SWAP was latent in the wire-level structure. COMMUTATION replaces an adjacent pair with an equivalent commuted pair of the same size; if the original was not an inverse pair, the commuted pair is generically also not inverse. INSERTION adds an identity pair $(g, g^{-1})$, increasing $|C|$ by 2; Theorem 2(c) proves the insertion-debt invariant. $\blacksquare$

**Theorem 2(c) (Bounded INSERTION Cascade Lemma).** For any circuit $C$ with $\mathcal{S}_1(C) = \emptyset$, let $k$ INSERTION moves produce circuit $C'$ with $|C'| = |C| + 2k$. Let $R_{\text{removal}}(C')$ be the maximum number of gates removable via REMOVAL sequences involving at least one inserted gate. Then $R_{\text{removal}}(C') \leq 2k$, so the net gate-count change from any INSERTION + REMOVAL sequence is non-negative.

*Proof (Insertion-debt invariant).* Define the insertion debt $\Delta(C')$ as the number of gates introduced by INSERTION moves. Initially $\Delta(C) = 0$; each INSERTION increases $\Delta$ by 2. Each REMOVAL involving at least one inserted gate decreases $\Delta$ by at most 2. The debt is always non-negative. Let $r_{\text{ins}}$ be inserted gates removed and $r_{\text{pre}}$ pre-existing gates removed. Since every REMOVAL pair contains at least one inserted gate, $r_{\text{ins}} \geq r_{\text{pre}}$. Net change: $+2k - r_{\text{ins}} - r_{\text{pre}} \geq 2k - 2k - 0 = 0$. $\blacksquare$

**Theorem 2(d) (INSERTION Commutation Cascade Bound).** Even when INSERTION is combined with SWAP and COMMUTATION, the net reduction from any finite sequence starting from $\mathcal{S}_1(C) = \emptyset$ cannot exceed $B_{\text{pre}}(C)$ — the number of pre-existing wire-level inverse pairs that SWAP/COMMUTATION can bring into adjacency, which is exactly the Phase-2 action space $\mathcal{S}_{1+2}(C) \setminus \mathcal{S}_1(C)$.

*Proof (Wire-unitary preservation).* Under any sequence of INSERTION, SWAP, and COMMUTATION moves, the wire-level unitary product of pre-existing gates is preserved. INSERTION adds new gates but does not change the wire-level unitary of pre-existing gates. SWAP exchanges gates on disjoint qubits, not affecting per-wire unitaries. COMMUTATION preserves the wire-level unitary by definition. Since the per-wire unitary is invariant, INSERTION cannot create new wire-level inverse relationships among pre-existing gates. The net reduction is bounded by $B_{\text{pre}}(C) = |\mathcal{S}_{1+2}(C) \setminus \mathcal{S}_1(C)|$. $\blacksquare$

**Corollary 2.1 (Universality of the Phase-1 Ceiling).** All Phase-1 optimizers achieve identical ceiling: $R_{\text{greedy}}(C) = R_{\text{RLS}}(C) = R_{\text{SA}}(C) = R_{\text{GA}}(C) = R_1^*(C)$. Empirically, 45,500 trials across Universal, Clifford, and Structured families confirm $\leq 0.05\%$ mean reduction for all four optimizers (see §6.1.1 for the E29 qualification of this statement for stochastic optimizers under non-default fitness settings).

### 4.2 Phase-2 Context-Dependent Advantage

**Lemma 3 (Commutation Preserves Unitary Equivalence).** If circuit $C'$ is obtained from $C$ by exchanging two adjacent gates $g_i, g_{i+1}$ with $[g_i, g_{i+1}] = 0$, then $U(C') = U(C)$ exactly. Consequently, any pipeline composed of commutation rewrites and inverse-pair cancellations produces a circuit exactly unitarily equivalent to the input.

**Theorem 6 (Aaronson–Gottesman Canonical-Form Ceiling).** Let $C$ be an $n$-qubit Clifford circuit expressed in Aaronson–Gottesman canonical form (the 11-stage $H$-$C$-$H$-$C$-$H$-$S$-$C$-$S$-$H$-$C$-$H$ decomposition [Aaronson & Gottesman 2004]). Then $\mathcal{S}_1(C) = \emptyset$ and $R_1(C) = 0$ for every Phase-1 optimizer. *Validation:* experiment E23 (160 circuits, $n = 3$–$10$, 20 circuits per $n$) confirms 0.000% reduction and a 100% canonical-form match rate on every instance (§6.7).

**Theorem 7 (Explicit Circuit Family with $\Omega(1)$ Phase-2 Advantage).** There exists an explicit family $\{C_n\}_{n \geq 2}$ on $n$ qubits such that $R_1(C_n) = 0$ for all Phase-1 optimizers and $R_{1+2}(C_n) \geq 1/6$ for all $n \geq 2$.

*Construction.* For each even $n \geq 2$, define $C_n$ of depth 6:
- Layer 1: $\text{CNOT}(q_0, q_1), \text{CNOT}(q_2, q_3), \ldots$ (even-indexed pairs, $n/2$ gates)
- Layer 2: $H(q_0), H(q_1), \ldots, H(q_{n-1})$ ($n$ gates)
- Layer 3: $\text{CNOT}(q_1, q_2), \text{CNOT}(q_3, q_4), \ldots$ (odd-indexed pairs, $n/2$ gates)
- Separator: $S$ gate on the control qubit of each Layer-3 CNOT ($n/2$ gates)
- Layer 4: Repeat of Layer 3 ($n/2$ gates, self-inverse pairs with Layer 3)
- Layer 5: $H(q_0), \ldots, H(q_{n-1})$ ($n$ gates, self-inverse with Layer 2)
- Separator$^\dagger$: $S^\dagger$ gates ($n/2$ gates)
- Layer 6: Repeat of Layer 1 ($n/2$ gates, self-inverse with Layer 1)

Total: $5n$ gates. The circuit implements the identity $U(C_n) = I$.

*Proof sketch.* In the original listing, no adjacent pair is inverse: $S$ separators between Layers 3 and 4 prevent listing-adjacency. However, $S$ on the control qubit commutes with CNOT (since $S$ is diagonal). Phase-2 performs bubble-sort commutation to move each Layer-3 CNOT past its $S$ separator into adjacency with the corresponding Layer-4 CNOT. After $\text{CNOT} \cdot \text{CNOT} = I$ cancellation, the $S$–$S^\dagger$ pairs become adjacent and cancel, as do the $H$–$H$ and Layer-1/6 CNOT pairs. Total removal: $2n$ gates from $5n$, yielding $R_{1+2} = 2/5 > 1/6$. $\blacksquare$

**Theorem 9 (Phase-2b Template-Assisted Advantage for BV Oracle Circuits).** For the natural Bernstein–Vazirani (BV) oracle circuit family, Phase-2b (commutation plus template matching) achieves:

$$\Gamma^{(2b)}(C_n^{\text{BV}}) \geq \frac{n}{4.5n + 4} = \Omega(1),$$

while Phase-1 achieves $R_1(C_n^{\text{BV}}) = 0$.

*Proof sketch.* The BV oracle on $n$ data qubits (plus one ancilla) has structure $X_{\text{anc}} \cdot H^{\otimes(n+1)} \cdot \prod_{i \in S} \text{CNOT}(q_i, q_{\text{anc}}) \cdot H^{\otimes(n+1)} \cdot H_{\text{anc}} \cdot X_{\text{anc}}$, where $S \subseteq \{0, \ldots, n-1\}$ is the secret string. The circuit contains $2n$ Hadamard gates on data qubits separated by CNOT oracle gates. Phase-1 cannot cancel them because the intervening CNOT gates are non-adjacent. Phase-2b uses commutation to expose $H$-CNOT-$H$ sandwiches and applies a template identity to rewrite them. The $n/(4.5n+4)$ lower bound is a theoretical/template-assisted result. $\blacksquare$

**Full-scale validation (2026-07-21 update).** Theorem 9 is no longer fixture-scale. The Phase-2b v2 pipeline (`Phase2bTemplateMatcher` v2.0.0: inverse-cancellation closure over self-inverse/named/parametric gate pairs, phase-polynomial merging, and the standard $\leq$3-qubit Clifford conjugation template set; not an exhaustive enumeration of the 11,520-element 2-qubit Clifford group) reaches the exact $k+2$ gate optimum on all 80 BV instances ($n = 3$–$10$, 10 secrets per size, original size $2n + k$ where $k$ is the secret Hamming weight), exceeding the rigorous bound by 3.1–4.2× per instance with fidelity $\geq 1 - 2\times10^{-13}$ everywhere (E25, §6.4). Relative to Theorem 7's *engineered* family (E24: Phase-2a mean 79.80%, range 62.5–89.3%), the BV result achieves the same magnitude on a *natural* algorithm family — the strongest empirical support for Conjecture C2.

**Comparison.** Theorem 7 proves $\Omega(1)$ Phase-2b advantage for a deliberately engineered circuit family. Theorem 9 strengthens this to the Bernstein–Vazirani oracle — a *natural* circuit family arising from a well-known quantum algorithm — demonstrating that template-assisted Phase-2b advantage is not merely a pathological artifact.

**Empirical validation of Theorem 7 (E24, 75 rows).** Experiment E24 instantiates the engineered family at $n \in \{4, 6, 8, 10, 12\}$ × 5 trials × 3 optimizers (`data/v7/e24/`). Phase-1 reduction is 0.0000% on every row, confirming the $R_1 = 0$ clause empirically; Phase-2a commutation achieves mean reduction 79.80% (95% CI [62.5, 89.3]), far above the proven $1/6 \approx 16.7\%$ lower bound — the construction's self-inverse layer pairs are even more commutation-accessible than the proof requires. Fidelity is exactly 1.0 on all 75 rows. Notably, Phase-2b v1 template matching achieves only 2.5% [0, 12.5] on the same instances: the engineered family's $S$–separator structure defeats the inverse-closure-plus-conjugation template library even though commutation exposes it fully. The Phase-2a/2b gap is therefore family-dependent — closed on the natural families of Table 10, open on this engineered family — motivating phase-gadget and richer template mechanisms as future work (§7.6).

**E24 per-size results (75 rows; within each size the 5 trials are identical, so min = max).**

| $n$ | Phase-1 (%) | Phase-2a (%) | Phase-2b v1 (%) |
|---:|---:|---:|---:|
| 4 | 0.00 | 62.50 | 12.50 |
| 6 | 0.00 | 76.92 | 0.00 |
| 8 | 0.00 | 83.33 | 0.00 |
| 10 | 0.00 | 86.96 | 0.00 |
| 12 | 0.00 | 89.29 | 0.00 |

The Phase-2a advantage grows monotonically with $n$ as the fixed separator overhead amortizes, while Phase-2b v1's only nonzero cell is $n = 4$ — the smallest instance, where a generic template happens to match.

**Conjecture C2 (Phase-2 is Context-Dependent Super-Constant).** There exist circuit families where Phase-1 achieves $O(1/d)$ reduction while Phase-1+2 achieves $\Omega(1)$. The improvement $\Gamma(C)$ is context-dependent: significant for oracle and structured circuits, zero for already-optimal or structurally rigid families.

*Evidence.* Theorem 7 (explicit construction) and Theorem 9 (BV oracle) establish C2 constructively. Empirically, Phase-2a achieves ~3.26% on random Universal (Cohen's $d = 1.32$), ~20% on BV oracle, and 0% on structured brickwork, QFT, and GHZ; Phase-2b v2 raises these to 14.1% (Universal), 69.2% (BV), and 40.2% (Structured) at full scale (§6.4).

### 4.3 Complexity Context

**Theorem 8 (Haar-Random Incompressibility).** (a) $\Pr[\mathcal{C}(U) < 4^n/n^2] \leq \exp(-\Omega(4^n/n))$ over the Haar measure. (b) For circuits of size $m = nd$ with $d = \text{poly}(n)$, $R_{\max}(C) \leq 1 - 4^n/(n^3 d) \to 0$ doubly-exponentially fast. (c) Any algorithm applying at most $k$ peephole rewrites of window size $w$ achieves $R_A(C) \leq \min(kw/(nd), 1 - 4^n/(n^3 d))$.

**Critical caveat.** Theorem 8 applies to Haar-random *unitaries*, not to the random *gate sequences* used in our experiments. For $n = 10$, $d = 50$, circuits have ~500 gates, far below the Haar-random threshold of ~10,486 gates. The empirical ~0% reduction is explained by Theorem 1 (inverse-pair sparsity) and Theorem 1(b) (LBL empties the action space), not by Haar-random incompressibility. Theorem 8 provides a complementary information-theoretic argument for the asymptotic regime $d \sim 4^n/n^2$ that is not reached in our experiments.

**Conjecture C1 (Phase-1 Ceiling is Structural).** For any circuit family where no adjacent inverse gate pairs exist in the initial data structure, every Phase-1 optimizer achieves exactly 0% gate reduction. *Evidence:* Theorem 2 (action-space identity), Theorem 6 (Clifford circuits in AG canonical form), E23 (160 circuits, 100% match rate), Theorem 8 (bounded-window incompressibility for Haar-random unitaries).

**Open Problem OP1 (QMA-Hardness of CODP).** Is the Circuit Optimization Decision Problem QMA-hard? CIT is QMA-complete [Janzing et al. 2003], but completing the reduction from $k$-Local Hamiltonian requires analyzing the rewrite-rule closure of history-state circuits, which remains open.

---

## 5. Methods

### 5.1 Optimizer Suite

We implement six core optimizers plus one meta-optimizer spanning both phases. All share a common base class (`BaseOptimizer`) providing fidelity computation, move primitives, and result serialization.

**GreedyGateCancellation (Phase-1).** Deterministic single-pass scanner that iterates through the circuit listing, canceling adjacent self-inverse pairs and merging consecutive same-axis rotations. Move primitives: REMOVAL (adjacent inverse cancellation), rotation merging ($R_\alpha(\theta_1) \cdot R_\alpha(\theta_2) \to R_\alpha(\theta_1 + \theta_2)$). Time complexity: $O(m)$ per pass, convergence in 1–3 passes. Parameters: `max_iterations` (default 100), `fidelity_threshold` (default 0.99), `wire_traversal` (boolean, default false). When `wire_traversal = true`, the circuit is reordered into WCL before scanning.

**Random Local Search, Simulated Annealing, Genetic Algorithm (Phase-1).** Three stochastic optimizers with move sets including REMOVAL, SWAP (exchange disjoint-qubit gates), COMMUTATION (reorder commuting pair), and INSERTION (insert identity pair $g \cdot g^{-1}$). RLS accepts improving moves; SA uses Metropolis-Hastings acceptance with geometric cooling ($T_0 = 1.0$, $\alpha = 0.995$); GA uses tournament selection and gate-segment crossover with population $P$ over $G$ generations.

**CommutationRewriter (Phase-2).** Bubble-sort commutation within a sliding window of size $w$. For each anchor gate $g_i$, scans forward up to $w$ positions for an inverse gate $g_j$. If found, verifies that all intermediate gates commute with both $g_i$ and $g_j$, then bubble-sorts $g_j$ leftward into adjacency with $g_i$ and cancels. Commutation rules check: (1) disjoint qubit sets, (2) same single-qubit gate, (3) same-axis rotations, (4) Z-family gates on the same qubit, (5) CNOT with Z-family on the control qubit. These rules are sufficient but not necessary; the `_gates_commute` predicate is conservative and may reject legal commutations (§7.5). Time complexity: $O(\text{max\_iter} \cdot m \cdot w^2)$ worst case, typically $O(m \cdot w)$.

**HybridCommuteRewrite.** Three-stage pipeline: Greedy (Phase-1) → CommutationRewriter (Phase-2) → Greedy (Phase-1 cleanup). By Lemma 3 (commutation preserves unitary equivalence), the full pipeline produces a circuit exactly unitarily equivalent to the input.

**Phase2bTemplateMatcher (v2.0.0, Phase-2b).** Template-assisted optimizer combining inverse-cancellation closure over self-inverse, named-inverse, and parametric gate pairs; phase-polynomial merging; and the standard $\leq$3-qubit Clifford conjugation template set. The template library is the inverse-closure-plus-conjugation set, *not* an exhaustive enumeration of the 11,520-element two-qubit Clifford group. Used in E25 (§6.4).

**CeilingAwareOptimizer.** Proxy-guided conditional pipeline that computes fast $O(m)$ structural proxies before each phase and skips phases predicted to yield zero reduction. `COUNT_PHASE1_ACTIONS` performs a single linear scan counting adjacent self-inverse and mergeable-rotation pairs. `COUNT_PHASE2_ACTIONS` performs a windowed scan counting non-adjacent inverse pairs with commuting intermediates. **Caveat (HGC)**: the original heuristic correlation model did not generalize to unseen circuit families; the repaired mechanism-informed model is quantified honestly in §6.6.

### 5.2 Statistical Protocol

All mean reductions and effect sizes are accompanied by 95% bootstrap confidence intervals ($B = 10{,}000$ resamples with replacement). We report complementary effect-size measures — Cliff's delta ($\delta$, non-parametric, robust to non-normality), Hedges' $g$ (small-sample-corrected Cohen's $d$), and Glass's Delta (baseline-group SD denominator, used when the pooled SD is zero) — implemented in `analysis/phase1_statistics/effect_size.py` and emitted by `analysis/generate_effect_sizes.py`; Cliff's $\delta$ is the primary metric for near-zero-variance comparisons where parametric effect sizes are undefined or unstable.^1 Multiple hypothesis tests use Benjamini–Hochberg FDR correction at $\alpha = 0.05$ over the full family of tests (`analysis/figures/fdr_correction_results.csv`). Power analysis: to detect Cohen's $d = 0.5$ with power $1 - \beta = 0.80$ at $\alpha = 0.05$, a minimum of $n = 64$ circuits per group is required; we use $n = 100$ per configuration.

^1 *Glass's Delta caveat.* When the control/baseline-group variance is zero or near zero, Glass's Delta is unstable by construction: in the E14 per-family comparisons, a strict baseline-SD denominator inflates Random vs IQP to $\Delta = 6.52$ and Random vs UCCSD to $6.44$ (wave-1 audit artifact, `docs/review/wave1/data/effect_sizes.csv`), while the production implementation (`effect_size.glass_delta`, `control = 'auto'`) falls back to the group-1 SD when the baseline variance is exactly zero, yielding $0.578$ and $0.536$ on the same rows (`analysis/figures/effect_sizes.csv`) — an order-of-magnitude swing driven purely by the denominator choice, with Cohen's $d$ at $0.82$ / $0.76$ for reference. This is inherent to Glass's Delta, not evidence of a larger effect; on all such rows Cliff's $\delta$ is the authoritative effect size.

**Power disclosure** (full accounting in `docs/results/experimental_design.md` §12.8). Experiments separate into two adequacy classes:

| Class | Experiments | Achieved power ($d = 0.5$) | Interpretation |
|:---|:---|:---:|:---|
| Adequate | E1–E5, E15–E17 | 0.940 to $>$0.999 | null results are *reliable absences of effect* |
| Underpowered (exploratory) | E10 per-family ($\sim$9/cell) 0.170; E11 0.396; E12 0.154; E13 (56 records total); E14 cell-level ($\sim$17/cell) 0.293; E18 0.679 | below the 0.80 target | cell-level non-significant results are uninformative; significant cells risk winner's-curse inflation |

The underpowered cells involve structured real-circuit families, where the number of distinct instances per condition is inherently limited; the pooled FDR-corrected omnibus tests remain well-powered in all cases, so the main cross-family findings are unaffected.

Two further protocol choices follow `docs/results/experimental_design.md` §8. Confidence intervals use the *percentile* bootstrap rather than BCa: the BCa jackknife acceleration estimate is unstable for the degenerate, near-constant reduction distributions typical under LBL (a point mass at 0%), and at $N \geq 100$ per condition the percentile/BCa difference is negligible. Effect sizes are interpreted against pre-registered thresholds — Cohen's $d$: $<0.2$ negligible, $0.2$–$0.5$ small, $0.5$–$0.8$ medium, $\geq 0.8$ large; Cliff's $\delta$: $<0.147$ negligible, $0.147$–$0.33$ small, $0.33$–$0.474$ medium, $\geq 0.474$ large — with Hedges' $g$ reported for small per-cell samples.

Fidelity verification: exact average gate fidelity for $n \leq 12$ (full $2^n \times 2^n$ unitary matrices, $O(4^n)$); sampling-based estimator (1,000 Haar-random product states, SE ~3%) for $n > 12$; exact stabilizer tableau comparison for Clifford circuits ($O(n^2)$). Across experiments where fidelity was successfully computed, optimizer outputs preserve unitary equivalence. Documented failure rows (especially E18 decomposition/fidelity failures) are tracked and filtered from analyses requiring valid fidelity; E18 additionally reports an intention-to-treat analysis over all attempted circuits (§6.8). A known labeling issue in E21 — rows computed with the fallback estimator (`target = None`) are tagged `exact_average_gate_fidelity` — is disclosed in §7.5.

### 5.3 Compiler Configurations

**Qiskit (v2.4.1).** `qiskit.transpile` with optimization levels 0–3. Level 0: no optimization. Level 1: light optimization (adjacent cancellation, single-qubit merging). Level 2: medium (commutation analysis, KAK decomposition). Level 3: heavy (template matching, gate resynthesis, commutation-based reordering). We additionally report a **fair no-coupling-map comparison** (no SWAP routing) for like-for-like optimization comparison. Following reviewer-driven re-testing, Qiskit levels L0–L2 were re-measured under the corrected configuration: L2 is bitwise identical to L3 in fair mode (100% of circuits), while L0 still performs MCX decomposition only (S2, §6.5).

**Cirq (v1.6.1).** `optimize_for_target_gateset` with `CZTargetGateset`, `eject_z`, and `merge_single_qubit_gates_to_phxz`. Evaluated on $n \leq 8$. The E20 configuration was found to mis-configure the target gateset; all Cirq numbers reported here use the corrected configuration (S1, §6.5), which changes several sign patterns relative to earlier drafts.

**t|ket> (v2.18.0).** `FullPeepholeOptimise` with Clifford simplification, gate cancellation, and commutation-based reordering. Evaluated on $n \leq 6$ due to optimizer timeouts on larger instances. On RandomClifford circuits, 14/30 tket outputs fail fidelity verification ($F \approx 0.27$–$0.33$); those rows are excluded from reduction means and flagged (S1 footnote, §6.5; §7.5).

### 5.4 Experiment Registry

The experimental program comprises the registered experiments E1–E25 (36 canonical datasets, 82,721 result rows) plus five SOTA comparison suites (S1–S5) and a hardware-validation extension (EHW). Key experiments:

**Table 4. Experiment registry (selected experiments).**

| ID | Name | Trials | Families | Phase |
|----|------|--------|----------|-------|
| E1 | Search Space Stratification | 25,000 | 1 (Universal) | P1 |
| E2 | Entanglement Density | 2,100 | 1 (Universal) | P1 |
| E3 | Qubit Scaling | 12,000 | 1 (Universal) | P1 |
| E4 | Optimizer Comparison | 400 | 1 (Universal) | P1 |
| E5 | Landscape Perturbation | 6,000 | 1 (Universal) | P1 |
| E10 | Phase 1 vs Phase 2 | 1,905 | 5 | P1+2 |
| E12 | Compiler Baseline (Qiskit) | 568 | 15 | P1+2 |
| E14 | Extended Benchmark | 2,130 | 15 | P1+2 |
| E15 | Multi-Compiler Comparison | 994 | 15 | P1+2 |
| E16 | Window Scaling ($w \in \{2,5,10,20\}$) | 696 | 15 | P2 |
| E17 | Connectivity Constraints | 755 | 15 | P1+2 |
| E18 | Clifford+T Decomposition | 270 | 6 | P1+2 |
| E19 | WCL vs LBL Listing | 10,000 | 1 (Universal) | P1 |
| E20 | Multi-Compiler (Qiskit/Cirq/t\|ket>) | 1,070 | 15 | P1+2 |
| E21 | Ceiling-Aware Optimizer | 1,140 | 15 | P1+2 |
| E22 | Listing-Order Robustness (shuffle) | 2,240 | 16 | P1+2 |
| E23 | AG Canonical Form | 160 | 1 (Clifford) | P1 |
| E24 | Theorem 7 Hardness | 75 | 1 | P1+2 |
| E25 | Phase-2b Full-Scale Validation | 2,427 | 16 | P2b |
| E29 | Multi-Seed Optimizer Stability | 800 | 1 (Universal) | P1 |
| EHW | Hardware Validation (noise-model) | 288 | 3 circuits | P1+2 |

Data versioning: v1 (E1–E5, superseded), v2_fixed (E1–E5, canonical), v4 (E11–E13), v5 (E10, E14–E18), v6 (E19–E21, SOTA suites S1–S5), v7 (E22–E24, E29), v8 (E25 Phase-2b v2 — closed to the full-factorial depth grid at 2,427 rows in wave 6 — EHW hardware validation, and the wave-5/6 listing-sensitivity dataset at 6,652 rows). Each artifact is stored with SHA-256 content hash, optimizer configuration JSON, circuit fingerprint, and random seed. All experiments are orchestrated by a unified runner with structured CSV/JSON output. Full pipeline: `python run_experiments.py --config experiments/v6_full.yaml`.

---

## 6. Results

### 6.1 Phase-1 Ceiling Under LBL Listing (E1–E5, RQ2)

**E1 (25,000 trials, $n = 5$, depths 1–50).** Mean gate reduction is 0.0000% at every tested depth, with zero variance. Maximum reduction across all 25,000 trials is 0.00%. At the conventional 20% success threshold, the success rate is 0.00%; at a more permissive 1% threshold, it remains 0.00%. This null result is explained by Theorem 1(b): under LBL, $\mathcal{S}_1(C) = \emptyset$ for all $C$ when $n \geq 2$. The absence of a depth-dependent ceiling change at any depth — including shallow circuits ($d = 1$–$5$) where one might expect finite-size effects — confirms the uniformity of the Phase-1 ceiling across the depth spectrum.

**Figure 1.** Phase-1 gate reduction as a function of circuit depth (E1, 25,000 trials). Mean reduction is identically 0.0000% at every depth $d = 1$–$50$, with zero variance — the hypothesized depth-driven phase transition is absent. *(`analysis/figures/fig01_phase_transition.pdf`)*

**E2 (2,100 trials, $n = 5$, density sweep).** Mean reduction remains 0.0000% at all two-qubit gate densities $\rho \in [0.1, 0.9]$. Pearson correlation between entanglement entropy and reduction is undefined ($r = \text{NaN}$, zero variance); $p = 1.000$ after FDR correction.

**E3 (12,000 trials, $n = 3$–$10$).** Mean reduction is 0.0000% at every qubit count. Kruskal–Wallis: $H = 0.00$, adjusted $p = 1.000$ (FDR), confirming no variation with system size. Consistent with Theorem 1(a), which establishes that expected Phase-1 reduction scales as $O(1/g_1^2 + 1/(g_2 n))$ — negligible for $n \geq 3$.

**Figure 2.** Qubit-count scaling of Phase-1 reduction (E3, 12,000 trials, $n = 3$–$10$). The ceiling is flat at 0.0000% across the entire size range; no finite-size deviation is detectable. *(`analysis/figures/fig02_scaling.pdf`)*

**E4 (400 trials, 4 optimizers, $n = 5$, $d = 15$).** All four Phase-1 optimizers converge to approximately 0% mean reduction:

**Table 5. E4 optimizer comparison (400 trials, $n = 5$, $d = 15$).**

| Optimizer | N | Mean Reduction (%) | Std Dev | Max (%) | Mean Runtime (s) |
|:----------|---:|---:|---:|---:|---:|
| Greedy | 100 | 0.0000 | 0.0000 | 0.0000 | 0.0023 |
| RLS | 100 | 0.0000 | 0.0000 | 0.0000 | 6.1530 |
| SA | 100 | −1.5467 | 3.2201 | 2.6667 | 2.3848 |
| GA | 100 | −0.2267 | 0.8487 | 1.3333 | 7.2551 |

The Kruskal–Wallis test on reduction is significant after FDR correction (raw $p = 6.1\times10^{-12}$, adjusted $p = 1.2\times10^{-11}$) — but the significance is driven by SA/GA *gate-count inflation* (negative means), not by any optimizer beating the ceiling: no optimizer achieves a positive mean reduction. Runtime differences are likewise highly significant ($p < 0.001$). The convergence of fundamentally different search strategies to the same zero-or-negative ceiling is strong evidence that the limitation is structural, not algorithmic — consistent with Theorem 2 and Corollary 2.1. A multi-seed follow-up (E29, §6.1.1) confirms that the stochastic-optimizer inflation is seed-robust while E4's exact single-seed values are not.

**Figure 3.** Per-optimizer reduction distributions (E4). Greedy and RLS sit at exactly 0%; SA and GA show symmetric spread around small negative means (inflation), with rare positive outliers. *(`analysis/figures/fig03_algorithm_comparison.pdf`)*

**E5 (6,000 trials, landscape perturbation, $n = 5$).** Mean reduction 0.22% (std 1.19%), maximum 26.67%; the depth-dependence of nonzero outcomes is significant after FDR correction (adjusted $p = 1.1\times10^{-10}$). The "optimization desert" structure — low mean with high maximum — is the signature of a landscape where deep optima exist but are exponentially unlikely to be discovered by local search. The fraction of perturbed circuits achieving nonzero reduction decreases with depth: 0.50% at $d = 3$, declining to 0.02% at $d = 20$.

**Figure 4.** Threshold sensitivity analysis (E1–E5). Success rate as a function of the reduction threshold: at any positive threshold the Phase-1 success rate under LBL is indistinguishable from zero. *(`analysis/figures/fig05_threshold_sensitivity.pdf`)*

**Figure 5.** Optimization landscape visualization (E5). Rare nonzero-reduction pockets are isolated in a flat zero desert; the density of discoverable pockets collapses with depth. *(`analysis/figures/fig07_landscape.pdf`)*

**Figure 6.** Fidelity distribution across verified optimizer outputs (protocol of §5.2). All successfully verified rows concentrate at $F_{\text{avg}} = 1.0$ within numerical precision; documented failure rows (E18) are tracked and filtered. *(`analysis/figures/fig06_fidelity_distribution.pdf`)*

**Key conclusion:** Across 45,500 random-circuit trials, no Phase-1 optimizer achieves mean reduction exceeding 0.22% under LBL listing. This ceiling is listing-model-dependent (Section 3), not an intrinsic property of the circuits. Hypothesis tests of Phase-1 reduction *level* across depths (E1), densities (E2), and qubit counts (E3) remain non-significant after FDR correction (adjusted $p = 1.0$); the significant tests (E4: adjusted $p = 1.2\times10^{-11}$; E5: adjusted $p = 1.1\times10^{-10}$) reflect stochastic-optimizer inflation and rare perturbation pockets respectively — both consistent with, and reinforcing, the structural-ceiling interpretation.

Per-cell design parameters (full protocol in `docs/results/experimental_design.md`): E1 uses 500 trials per depth (50 depths), E2 233 per density level (9 levels), E3 1,500 per qubit count (8 counts), E4 100 per optimizer, and E5 1,000 per depth — every cell exceeding the $n = 100$ adequacy threshold of §5.2, which is what licenses reading the E1–E3 nulls as reliable absences of effect rather than sensitivity failures.

**Figure 7.** Benjamini–Hochberg FDR correction across the full family of hypothesis tests. Raw versus adjusted $p$-values for every registered test; E1–E3 remain at adjusted $p = 1.0$ while E4, E5, and E16 survive correction. *(`analysis/figures/fig08_fdr_correction.pdf`)*

#### 6.1.1 Multi-Seed Stability of the Optimizer Comparison (E29)

E4 relies on a single base seed. E29 (800 rows = 4 optimizers × 10 seeds × 20 trials, Universal random circuits) replicates the comparison across seeds. Pooled mean reductions: Hybrid +4.69% [4.23, 5.16], RLS −176.53%, SA −22.15%, GA −8.31%. Two conclusions follow. First, E4's exact numeric values are single-seed indicative only — the stochastic optimizers' inflation is far larger in the multi-seed pool than E4's single seed suggested. Second, the qualitative ordering is seed-robust: no stochastic Phase-1 optimizer achieves a positive mean reduction, and the small positive Hybrid mean derives from Phase-2 commutation moves, consistent with the Phase-1 ceiling.

Per-seed sign consistency rules out a pooling artifact: the Hybrid mean is positive in all 10 of 10 base seeds (range +4.00% to +5.87%), while RLS, SA, and GA are negative in every seed (RLS −173.7% to −181.3%; SA −19.5% to −26.1%; GA −6.8% to −9.1%). The stochastic-optimizer inflation is therefore a seed-robust property of the (optimizer, listing) pair rather than an accident of any single seed (full per-seed table in Appendix F).

**Table 5b. E29 per-seed mean reduction (%) by optimizer (20 trials per seed; Universal circuits, $n = 5$, $d = 15$).**

| Base seed | Hybrid | RLS | SA | GA |
|---:|---:|---:|---:|---:|
| 42 | +5.07 | −177.47 | −21.47 | −6.80 |
| 142 | +5.07 | −177.20 | −19.47 | −8.13 |
| 242 | +4.80 | −174.67 | −24.27 | −8.80 |
| 342 | +4.40 | −181.33 | −22.67 | −9.07 |
| 442 | +4.67 | −174.67 | −22.53 | −8.67 |
| 542 | +4.00 | −178.27 | −19.60 | −8.93 |
| 642 | +4.40 | −178.00 | −22.13 | −8.00 |
| 742 | +4.13 | −175.07 | −26.13 | −9.07 |
| 842 | +4.53 | −174.93 | −19.87 | −8.53 |
| 942 | +5.87 | −173.73 | −23.33 | −7.13 |

### 6.2 Columnar Representation Sensitivity: WCL vs LBL (E19, RQ1)

See Section 3.4 for the full E19 flagship experiment. The key result: WCL achieves 7.83% mean reduction (std = 3.95%, max = 33.33%, fidelity = 1.0) versus 0.0000% under LBL, across 10,000 rows. This confirms that the Phase-1 ceiling is representation-dependent: the data-structure ordering, not the circuit content alone, determines whether peephole optimization can detect cancellation opportunities.

**Robustness to listing perturbation (E22).** E22 (2,240 rows, 16 families) stress-tests the listing sensitivity with a random-shuffle control. For the greedy optimizer under LBL, a random listing shuffle *increases* mean reduction from 6.30% to 10.34% (five shuffle seeds pooled; Mann–Whitney $p = 6.8\times10^{-15}$) and WCL reaches 12.20% ($p = 1.1\times10^{-12}$ versus original) — shuffling destroys the adversarial regularity of the canonical listings and accidentally creates adjacency. For the commutation Phase-2 optimizer, original versus shuffled listings are statistically indistinguishable (3.87% vs 2.70%, $p = 0.462$): Phase-2's windowed search is listing-robust. The listing model therefore acts as a hidden variable for Phase-1 (§7.2) but not for Phase-2.

**Table 4b. E22 listing ablation (mean reduction %, 160 rows per cell).**

| Optimizer | Original | Shuffle (5 seeds) | WCL | $p$ (orig vs shuffle) | $p$ (orig vs WCL) |
|:---|---:|---:|---:|---:|---:|
| Greedy Phase-1 (LBL) | 6.30 | 10.34 | 12.20 | $6.8\times10^{-15}$ | $1.1\times10^{-12}$ |
| Commutation Phase-2a | 3.87 | 2.70 | 1.00 | 0.462 | 0.057 |

**Table 4c. E22 per-family greedy Phase-1 reduction (%, original / 5-seed shuffle mean / WCL).** The eight families with all-zero rows (Adder, GHZ, HardwareEfficient, QAOA, QFT, QuantumWalk, SurfaceCode, VQE) are summarized in the final row.

| Family | Original | Shuffle (mean of 5 seeds) | WCL |
|:---|---:|---:|---:|
| CNOT chain | 100.00 | 95.00 | 100.00 |
| BV (Oracle) | 0.00 | 21.26 | 33.49 |
| RandomClifford | 0.22 | 17.89 | 20.46 |
| Structured | 0.00 | 8.84 | 11.76 |
| UCCSD-inspired | 0.00 | 8.11 | 10.63 |
| IQP | 0.00 | 7.30 | 9.12 |
| Universal | 0.00 | 5.30 | 6.83 |
| Grover | 0.56 | 1.69 | 2.97 |
| 8 all-zero families | 0.00 | 0.00 | 0.00 |

The per-family breakdown sharpens the headline result in two ways. First, the shuffle benefit is family-structured, not uniform: it concentrates in exactly the families with latent non-adjacent cancellation structure, and WCL exceeds the shuffle mean on every one of them — structure-aware ordering beats random reordering. Second, the CNOT chain moves in the opposite direction (100.00% → 95.00%): shuffling partially *destroys* the perfect adjacency that makes CNOT chains trivially compressible — the mirror image of the BV effect, and direct evidence that the canonical listings are adversarially regular in opposite directions for the two extreme classes.

**Cross-family WCL validation (E19-extended, 960 rows, 16 families).** The E19 flagship experiment covers random Universal circuits only; E19-extended (`data/v7/e19_extended/`, 30 trials per listing per family) repeats the WCL-versus-LBL comparison across all 16 families. Seven families show a positive WCL $-$ LBL advantage:

| Family | LBL (%) | WCL (%) | Advantage (pp) |
|:---|---:|---:|---:|
| BV (Oracle) | 0.00 | 30.79 | +30.8 |
| RandomClifford | 0.19 | 22.51 | +22.3 |
| Structured | 0.00 | 12.88 | +12.9 |
| UCCSD-inspired | 0.13 | 10.87 | +10.7 |
| IQP | 0.00 | 7.22 | +7.2 |
| Universal | 0.00 | 6.76 | +6.8 |
| Grover | 0.19 | 3.88 | +3.7 |

The remaining nine families (Adder, CNOT chain, GHZ, HardwareEfficient, QAOA, QFT, QuantumWalk, SurfaceCode, VQE) show no WCL benefit — the CNOT chain is saturated at 100% under both listings, and the other eight expose no cancellation structure under either listing — while WCL fidelity is numerically 1.0 on every row (minimum $1 - 1.1\times10^{-12}$). The listing effect is therefore not specific to random circuits: it generalizes to exactly the families with non-adjacent cancellation structure (the commutation- and template-accessible classes) and vanishes where no such structure exists. Two controls remain open (§7.5, item 2): WCL shuffle ablation and WCL $\times$ Phase-2b interaction. Full per-family data in Appendix F.

### 6.3 Search Space Stratification: The Trichotomy (E10, E14, E15, RQ2)

Experiments E10 (1,905 rows, 5 families) and E14 (2,130 rows, 15 families) extend the analysis to real algorithmic circuit families. The results reveal a categorical trichotomy, which we refine into five empirically distinct classes (unified with §6.5 and §7.1; 1 + 3 + 3 + 5 + 1 + 2 = 15 families):

**Class I — Trivially compressible (Phase-1 sufficient), 1 family.** CNOT chains achieve 100% reduction under Greedy Phase-1 alone; Phase-2 provides no additional value.

**Class II — Commutation-enabled compressible (Phase-2 required), 3 families.** Oracle/BV, RandomClifford, and Grover contain non-adjacent inverse pairs accessible through commutation moves (Table 6). IQP is annotated separately: at Phase-2a it sits at the prototype ceiling, but Phase-2b v2 reaches 92.0% (§6.4), moving it toward Class II at the template level.

**Class IIIa — Genuine structural ceiling, 3 families.** QFT, GHZ, and SurfaceCode show 0% reduction for the prototype *and* for Qiskit L3; Cirq and t|ket> either match 0% or inflate gate count (Cirq's +8.4% on SurfaceCode is the sole exception, footnoted in Table 12). No tested compiler achieves a reduction.

**Class IIIb — Prototype action-space ceiling, 5 families + 1 borderline.** VQE, HardwareEfficient, IQP, UCCSD, and QAOA show 0% with the prototype but 6.3–64.4% with t|ket>'s FullPeepholeOptimise — the ceiling is an artifact of the prototype's limited move set, not a structural limit of peephole optimization. HaarRandom is borderline (≤6.5 pp for any production compiler).

**Class IIIc — Practical ceiling, 2 families.** Adder and QuantumWalk show 0% for the prototype *and* gate-count inflation under all tested production compilers (Table 12): the ceiling is practical, shared by the entire tested compiler ecosystem, though we cannot exclude that a specialized arithmetic-circuit or walk-specific pass could break it.

**Table 6. E10 Phase-1 vs Phase-2 results (1,905 rows, selected families).**

| Family | P1 Greedy (%) | P2 Commutation (%) | Hybrid (%) | Mean Fidelity |
|:---|---:|---:|---:|---:|
| Universal | 0.00 | 2.99 | 2.99 | 1.0000 |
| Structured | 0.00 | 0.00 | 0.00 | 1.0000 |
| QFT | 0.00 | 0.00 | 0.00 | 1.0000 |
| GHZ | 0.00 | 0.00 | 0.00 | 1.0000 |
| CNOT chain | 100.00 | 0.00 | 100.00 | 1.0000 |
| RandomClifford | 0.10 | 15.85 | 16.07 | 1.0000 |

*Statistical power caveat:* real-circuit cells (QFT, GHZ) have $N = 5$ per family–optimizer combination. Ceiling claims rely on convergent evidence from E14 (2,130 rows) and E15 (994 rows).

**Figure 8.** Phase-1 versus Phase-2 reduction across the E10 families. Phase-2 dominates wherever reduction exists (except CNOT chains); Phase-1 contributes materially only on CNOT chains (≤ 0.1% mean elsewhere). *(`analysis/figures/fig04_phase1_vs_phase2.pdf`)*

**Table 7. 15-family classification (E15, 994 rows).** *Qiskit O3 column from the E15 dataset (`e15_multi_compiler_e15_full_20260611_150934.csv`); superseded multi-compiler numbers appear in Table 12. Negative values indicate gate-count inflation from basis-gate expansion.*

| Family | P1 (%) | P2 (%) | Hybrid (%) | Qiskit O3 (E15) (%) | Class |
|:---------------|---:|---:|---:|---:|:------|
| CNOT | 100.00 | 0.00 | 100.00 | 100.00 | I |
| Oracle | 0.00 | 14.94 | 14.94 | 40.08 | II |
| RandomClifford | 0.00 | 15.81 | 16.54 | 76.12 | II |
| Grover | 0.96 | 5.26 | 6.22 | −819.4* | II |
| IQP | 0.00 | 0.51 | 0.51 | 61.16 | IIIb (P2b v2: §6.4) |
| UCCSD | 0.00 | 0.52 | 0.52 | 20.94 | IIIb |
| QFT | 0.00 | 0.00 | 0.00 | 0.00 | IIIa |
| GHZ | 0.00 | 0.00 | 0.00 | 0.00 | IIIa |
| SurfaceCode | 0.00 | 0.00 | 0.00 | 0.00 | IIIa |
| QAOA | 0.00 | 0.00 | 0.00 | 0.00 | IIIb |
| VQE | 0.00 | 0.00 | 0.00 | 39.27 | IIIb |
| HardwareEfficient | 0.00 | 0.00 | 0.00 | 35.09 | IIIb |
| Adder | 0.00 | 0.00 | 0.00 | 0.00 | IIIc |
| QuantumWalk | 0.00 | 0.00 | 0.00 | −2794.7* | IIIc |
| HaarRandom | 0.00 | 0.00 | 0.00 | 3.88 | IIIb (borderline) |

**Figure 9.** Optimizer comparison on real circuit families (E15). Prototype Phase-1, Phase-2, and Hybrid reductions per family, with the Qiskit O3 reference. *(`analysis/figures/fig08b_real_circuit_optimizer_comparison.pdf`)*

**Figure 10.** Extended-benchmark heatmap (E14, 2,130 rows): reduction by family × optimizer. The block structure of the trichotomy is visible as three distinct bands. *(`analysis/figures/fig11_extended_benchmark_heatmap.pdf`)*

**Per-family corroboration (E14).** The independent E14 dataset (2,130 rows, 3 prototype optimizers) reproduces the trichotomy structure family by family: commutation Phase-2a mean reductions of 13.98% (Oracle), 13.04% (RandomClifford), 4.35% (Grover), 0.42% (UCCSD), and 0.30% (IQP); greedy Phase-1 reaches 100% on CNOT chains and is 0.00% on all other families except Grover (0.96%); every remaining family sits at exactly 0% for all three prototype optimizers. The class boundaries therefore replicate across two independently generated benchmark suites (E10/E15 and E14), subject to the E14 cell-level power caveat of §5.2; the pooled omnibus tests remain well-powered.

**IQP sensitivity note (wave-6 rerun reconciliation).** Four independent rerun reconciliations (E14, E15, E16, and E21; §7.5, item 20) consistently show that the strengthened commutation predicate of the current codebase finds additional cancellable inverse pairs in the all-diagonal IQP family. IQP commutation/hybrid reductions quoted from the canonical E14/E15/E16 datasets in this section (0.30–0.51%) are therefore systematically conservative relative to current code — an optimizer-capability enhancement (review FATAL-1 repair direction), not a data error. Canonical values are retained by adoption decision.

**Window-size scaling (E16, 696 rows, $w \in \{2, 5, 10, 20\}$).** Phase-2 effectiveness depends on the commutation window $w$:

**Table 8. E16 window scaling (hybrid Phase-1+2 reduction, %).**

| Family | $w = 2$ | $w = 5$ | $w = 10$ | $w = 20$ |
|:---|---:|---:|---:|---:|
| Oracle | 0.00 | 0.00 | 27.39 | 34.63 |
| RandomClifford | 0.00 | 13.78 | 22.42 | 23.68 |
| Grover | 1.28 | 4.14 | 7.72 | 9.99 |
| **Mean (all families)** | 6.75 | 7.91 | 10.61 | 11.33 |

The window effect is significant across the four tested windows (Kruskal–Wallis, FDR-adjusted $p = 1.7\times10^{-7}$). At the family-mean level, $w = 10$ captures 93.6% of the $w = 20$ value; saturation is an empirical trend — a paired Wilcoxon on family means between $w = 10$ and $w = 20$ gives $p = 0.0544$, i.e. marginal. Oracle/BV saturates at $w \approx 10$, RandomClifford continues to $w \approx 20$. (An earlier draft's "$p = 0.420$, $d = 0.173$" statistic could not be reproduced from canonical data and has been replaced by the two tests above.)

**Figure 11.** Window-scaling curves (E16) for the reducible families: reduction versus commutation window $w \in \{2, 5, 10, 20\}$, with family-level saturation knees. *(`analysis/figures/fig13_window_scaling_curves.pdf`)*

**Table 9. Circuit-family optimization prescriptions (synthesized from E10, E15, E16, and S1).**

| Family | Class | Strategy | Expected Reduction (%) | Window $w$ | Best Compiler Gap (pp) |
|:---|:---:|:---|---:|:---:|:---:|
| CNOT | I | Phase 1 | 100.0 | — | 0.0 |
| Oracle | II | Phase 2 | 14.9–41.8 | 10 | +26.9 (Qiskit L3) |
| RandomClifford | II | Phase 2 | 16.5–72.5 | 10–20 | +56.0 (Qiskit L3) |
| Grover | II | Phase 2 | 6.2 | 20 | compilers inflate |
| QFT | IIIa | Skip | 0.0 | — | 0.0 |
| GHZ | IIIa | Skip | 0.0 | — | 0.0 |
| SurfaceCode | IIIa | Skip | 0.0 | — | 0.0 |
| VQE | IIIb | Escalate | 0.0 (t\|ket>: 42.2) | — | +42.2 |
| HardwareEfficient | IIIb | Escalate | 0.0 (t\|ket>: 36.5) | — | +36.5 |
| IQP | IIIb | Escalate / P2b | 0.5 (t\|ket>: 64.4; P2b v2: 92.0) | 10 | +63.9 |
| UCCSD | IIIb | Escalate | 0.5 (Qiskit L3: 23.3) | — | +22.8 |
| QAOA | IIIb | Escalate | 0.0 (t\|ket>: 6.3) | — | +6.3 |
| Adder | IIIc | Skip (all fail) | 0.0 | — | compilers inflate |
| QuantumWalk | IIIc | Skip (all fail) | 0.0 | — | compilers inflate |
| HaarRandom | IIIb | Marginal | 0.0 (Qiskit L3: 6.5) | — | +6.5 |

*Legend:* Phase 1 = Greedy only. Phase 2 = Commutation rewriting. Skip = no peephole pass produces nonzero reduction. Escalate = deploy beyond-peephole mechanisms (template matching, phase-polynomial synthesis, Clifford tableau reduction). Gap = best production-compiler reduction minus prototype Hybrid reduction (Table 12).

### 6.4 Phase-2b Full-Scale Validation (E25, RQ2)

E25 (2,427 rows, `data/v8/phase2b_full/`) evaluates the Phase-2b template matcher (v2.0.0, §5.1) at full scale across 16 families. The design is now a **full factorial** over the depth-structured families — Universal, RandomClifford, Structured, and IQP at $n = 3$–$10$ × depth $\{20, 25, \ldots, 50\}$ × 3 seeds, all 56/56 $(n, \mathrm{depth})$ combinations (closed in wave 6 with 720 additional rows; the wave-4/5 stratified precursor covered only $n \in \{3, 5, 8\}$ × depth $\{20, 35, 50\}$) — plus BV at all $n = 3$–$10$ × 10 secrets. Family means moved by less than 0.8 percentage points between the stratified and full-factorial grids, confirming that the earlier stratified means were unbiased estimates of the full-factorial values (`docs/review/wave6/phase2b_crossfill.md`). Fidelity is verified per row by exact Operator equality for $n \leq 9$ (2,103 rows), exact Clifford-tableau equality for all-Clifford rows at $n = 10$ (123 rows), and Haar product-state sampling otherwise (`fidelity_method = sampled200`, 201 rows) — the sampled rows include the six QuantumWalk $n = 8$ rows, where exact Operator fidelity on the 9-qubit, 36-MCX walk circuit (~133 s/row) exceeds the compute envelope, and resolve via an exact structural-equality fast path wherever the optimizer leaves the circuit unchanged, so the reported fidelity of 1.0 is exact on those rows; zero of 2,427 rows fall below $1 - 10^{-9}$. The template library is the inverse-closure-plus-conjugation set described in §5.1, not an exhaustive 11,520-element Clifford enumeration.

**Table 10. Phase-2b v2 family results (E25; mean reduction %).**

| Family | Phase-1 (%) | Phase-2a (%) | Phase-2b (%) | Notes |
|:---|---:|---:|---:|:---|
| BV (Oracle) | 0.0 | 14.5 | **69.2** (min 54.5) | exact $k{+}2$ optimum on all 80 instances |
| IQP | 0.1 | 9.4 | **92.0** (min 84.4) | prototype ceiling broken |
| RandomClifford | 0.4 | 22.4 | **51.6** | |
| Structured | 0.0 | 0.0 | **40.2** | Phase-2a ceiling broken |
| Universal (HaarRandom) | 0.0 | 4.2 | 14.1 | |
| Grover | 0.0 | 4.2 | 16.1 | |
| UCCSD-inspired | 0.0 | 1.4 | 8.0 | |
| CNOT chain | 100.0 | 0.0 | 100.0 | Class I confirmed |
| Adder, GHZ, QFT, QAOA, VQE, HWE, SurfaceCode, QWalk | 0.0 | 0.0 | 0.0 | ceilings hold |

Pooled across families (bootstrap, $B = 10{,}000$): Phase-1 0.5% [0.1, 1.0], Phase-2a 9.0% [8.2, 9.7], Phase-2b 48.5% [46.5, 50.5]. The Phase-2b > Phase-1 improvement is significant by paired Wilcoxon in every reducible family: BV $p = 3.8\times10^{-15}$ ($n = 80$ pairs); Structured, IQP, RandomClifford, and Universal each at $p \approx 2.7\times10^{-51}$ (one-sided, $n = 168$ pairs — the $2^{-168}$ saturation value, all paired differences positive); Grover $p = 0.016$; UCCSD-inspired $p = 0.033$.

Depth trend (Phase-2b reduction grows with circuit depth): IQP 0.872 → 0.950, RandomClifford 0.482 → 0.533, Structured 0.396 → 0.406 (normalized reduction at $d = 20$ → $d = 50$, full-factorial grid). Deeper circuits present more template-matchable structure; the template advantage is super-constant in depth, supporting Conjecture C2 at the template level.

**Table 11. BV instances versus the Theorem 9 bound (E25, 80 instances, $n = 3$–$10$, 10 secrets per size).**

| Quantity | Value |
|:---|:---|
| Original size | $2n + k$ gates ($k$ = secret Hamming weight) |
| Achieved size | exactly $k + 2$ gates (all 80/80 instances) |
| Theorem 9 lower-bound reduction | $\geq n/(4.5n + 4)$ |
| Per-instance excess over bound | 3.1–4.2× |
| Fidelity | $\geq 1 - 2\times10^{-13}$ (all instances) |

The BV result upgrades Theorem 9 from a fixture-scale observation to a full-scale empirical optimum: Phase-2b reaches the *exact* $k + 2$ gate-count optimum — not merely the rigorous lower bound — on every instance, on a natural algorithm family. Combined with Table 10, this is the strongest empirical support for Conjecture C2 and directly overturns the prototype-level classification of IQP (IIIb) and Structured: at the template level both are compressible. The Class IIIa families (QFT, GHZ, SurfaceCode) and the Class IIIc families (Adder, QuantumWalk) remain at 0% even under Phase-2b, deepening the evidence that their ceilings are structural or ecosystem-wide rather than prototype-specific.

**Table 11b. BV reduction by size versus the Theorem 9 bound (E25; 10 secrets per size).**

| $n$ | Mean reduction (%) | Min reduction (%) | Thm 9 bound (%) | Bound met (worst instance) |
|---:|---:|---:|---:|:---:|
| 3 | 59.2 | 54.5 | 17.1 | yes |
| 4 | 61.2 | 57.1 | 18.2 | yes |
| 5 | 69.5 | 58.8 | 18.9 | yes |
| 6 | 71.6 | 60.0 | 19.4 | yes |
| 7 | 70.7 | 60.9 | 19.7 | yes |
| 8 | 72.7 | 61.5 | 20.0 | yes |
| 9 | 74.6 | 62.1 | 20.2 | yes |
| 10 | 74.4 | 62.5 | 20.4 | yes |

The bound is satisfied with a wide margin at every size — including the worst instance — and the achieved reduction grows with $n$ while the rigorous bound is nearly flat, so the empirical excess is super-constant in practice. Per-instance aggregates: `data/v8/phase2b_full/bv_theory_v8.csv`; full Phase-2b v2 methodology and per-family detail in Appendix D.

### 6.5 Multi-Compiler Benchmark and Mechanism Analysis (E12, E20, S1–S5, RQ3)

The multi-compiler comparison serves two purposes: validating the ceiling against industrial-strength optimizers and identifying the mechanisms by which production compilers exceed the peephole horizon. All numbers below come from the canonical SOTA benchmark (`data/v6/sota_benchmark/`; Qiskit 2.4.1, Cirq 1.6.1, pytket 2.18.0; 10 trials per (family, $n$) cell; fair mode: no coupling map, optimization only) with the prototype column from E15. The corrected Cirq configuration (§5.3) supersedes earlier-draft Cirq numbers, including those in the previous version of this section.

**Cirq pipeline corrections (provenance).** Two latent bugs in the SOTA harness were found and fixed on 2026-07-20 (`docs/results/sota_compiler_benchmark.md` §3; full detail in Appendix E). First, the `CZTargetGateset` step of `optimize_for_target_gateset` never executed: the keyword was renamed (`target_gateset=` to `gateset=`) in Cirq 1.6.1, the resulting `TypeError` was swallowed by a bare `except`, and the step was silently skipped — the corrected, protocol-conformant pipeline changes Cirq's numbers substantially (CNOT 0.0 → 100.0%, RandomClifford 47.4 → 63.1%, QuantumWalk −382.6 → −4547.4%) because the CZ-target rewriting now actually runs. Second, Cirq's QASM export emits `sx`/`sxdg` gates that Qiskit's builtin qelib1 set does not define, so 100 rows (Grover/QFT/QuantumWalk) failed the QASM round-trip re-import; injecting the standard qelib1 definitions repaired the round-trip. All Cirq numbers in this section and in Tables 12–16 use the corrected pipeline.

**Table 12 (S1). Mean gate-count reduction (%) by family and tool.**

| Family | Prototype (P1+P2) | Qiskit L3 | Cirq (fixed) | t\|ket> FPO |
|--------|:-----------------:|:---------:|:------------:|:-----------:|
| QFT | **+0.0** | +0.0 | −258.0 | −206.7 |
| GHZ | **+0.0** | +0.0 | −181.9 | +0.0 |
| SurfaceCode | +0.0 | +0.0 | **+8.4** | +0.0 |
| CNOT chain | +66.7 | **+100.0** | +100.0 | +100.0 |
| Oracle (BV) | +23.1 | **+41.8** | +33.5 | +39.2 |
| RandomClifford | +12.3 | **+72.5** | +63.1 | +71.6 |
| Grover | **+4.3** | −500.5 | −956.6 | −157.8 |
| Adder | **+0.0** | +0.0 | −1217.3 | −505.9 |
| QuantumWalk | **+0.0** | −1904.7 | −4547.4 | −1261.9 |
| IQP | +0.0 | +62.8 | +36.7 | **+64.4** |
| QAOA | +0.0 | +0.0 | −31.5 | **+6.3** |
| VQE | +0.0 | +39.3 | −1.2 | **+42.2** |
| HardwareEfficient | +0.0 | +35.5 | −16.9 | **+36.5** |
| UCCSD | +0.0 | **+23.3** | −12.3 | +14.5 |
| HaarRandom | +0.0 | **+6.5** | −4.1 | +5.8 |

*Correctness caveat (t|ket> RandomClifford):* 14 of 30 t|ket> RandomClifford trials fail exact-fidelity verification ($F_{\text{avg}} \approx 0.27$–$0.33$); the nominal +71.6% on those rows corresponds to a *different* unitary. On fidelity-passing rows the mean is +73.5% ($n = 16$). All other t|ket> families pass at $F = 1.0$. The Cirq +8.4% on SurfaceCode is the single exception to an otherwise unanimous Class IIIa ceiling.

**Key findings:**

1. **Genuine structural ceilings (Class IIIa, 3 families).** QFT, GHZ, and SurfaceCode: no tested compiler achieves any reduction (Cirq/t|ket> either match 0% or inflate by 181–258%; the sole exception is Cirq's +8.4% on SurfaceCode). We deliberately avoid the phrase "gate-count-optimal": the claim is empirical — unanimity across the tested compiler ecosystem — not a proof of optimality.

2. **Prototype-limited ceilings (Class IIIb, 5 families).** VQE, HardwareEfficient, IQP, UCCSD, and QAOA show 0% with the prototype but 6.3–64.4% with t|ket>'s FullPeepholeOptimise. The ceiling is an artifact of the prototype's limited move set (adjacent inverse cancellation + bounded commutation), not a structural limit of peephole optimization.

3. **Practical ceilings (Class IIIc, 2 families).** Adder and QuantumWalk show 0% for the prototype and gate-count inflation under *all* tested production compilers (Table 12, Table 16) — an ecosystem-wide practical ceiling.

4. **t|ket>'s FullPeepholeOptimise is a peephole optimizer.** Despite the prototype's narrow definition, t|ket>'s pass achieves 6.3–64.4% on the Class IIIb families using single-qubit rotation merging, template matching, and phase-polynomial synthesis — all standard peephole techniques. The difference is engineering sophistication, not algorithmic paradigm.

5. **Grover is a Class II family that production compilers actively damage.** The prototype reaches +4.3% (commutation-accessible structure), but Qiskit, Cirq, and t|ket> *inflate* Grover by 157.8–956.6% (Table 12): their mandatory multi-controlled-gate decomposition runs before any cancellation pass and creates far more gates than the peephole stage can remove. Grover thus illustrates that compiler "optimization level" is not monotone in gate count for MCX-heavy circuits — the same mechanism behind the Class IIIc blowups (Table 16), in milder form.

**Pass isolation (`data/v5/qiskit_pass_isolation.csv`, 5 families, $n = 3$–$7$).** Running Qiskit 2.4.1 passes individually against the prototype's phases localizes the mechanism gap: a single isolated CommutativeCancellation pass reproduces the prototype's entire reduction on CNOT chains (100.0%) and Oracle (32.9%), and nearly all of it on RandomClifford (25.3% versus the prototype's 23.8%), while Optimize1qGates contributes exactly 0% on this suite's gate set. The prototype's Phase-1+2 pipeline is therefore, mechanism-for-mechanism, a local peephole optimizer — the 20–45 pp full-pipeline gap on reducible families comes from beyond-peephole synergy across the pass sequence, not from any single missing pass. QuantumWalk anchors the negative case (−256.5% at $n = 4$; Table 16). Full pass-level detail in Appendix E.

**Figure 12.** Compiler baseline comparison (S1): reduction by family for prototype, Qiskit L3, Cirq, and t|ket>. The trichotomy band structure is invariant across tools; only the Class IIIb band moves. *(`analysis/figures/fig09_compiler_baseline_comparison.pdf`)*

**Table 13 (S2). Qiskit optimization-level progression (fair mode, mean reduction %).**

| Family | L0 | L1 | L2 | L3 |
|--------|:---:|:---:|:---:|:---:|
| QFT | +0.0 | +0.0 | +0.0 | +0.0 |
| GHZ | +0.0 | +0.0 | +0.0 | +0.0 |
| SurfaceCode | +0.0 | +0.0 | +0.0 | +0.0 |
| CNOT chain | +0.0 | +100.0 | +100.0 | +100.0 |
| Oracle (BV) | +0.0 | +41.8 | +41.8 | +41.8 |
| RandomClifford | +0.0 | +61.6 | +72.5 | +72.5 |
| Grover | −675.7 | −506.2 | −500.5 | −500.5 |
| Adder | +0.0 | +0.0 | +0.0 | +0.0 |
| QuantumWalk | −2287.0 | −1937.1 | −1904.7 | −1904.7 |
| IQP | +0.0 | +29.8 | +62.8 | +62.8 |
| QAOA | +0.0 | +0.0 | +0.0 | +0.0 |
| VQE | +0.0 | +39.3 | +39.3 | +39.3 |
| HardwareEfficient | +0.0 | +35.5 | +35.5 | +35.5 |
| UCCSD | +0.0 | +11.0 | +23.3 | +23.3 |
| HaarRandom | +0.0 | +5.5 | +6.5 | +6.5 |

In fair mode, Qiskit 2.4.1 L2 and L3 are empirically identical on all 15 families (100% bitwise-consistent outputs); L1 differs on IQP, RandomClifford, and UCCSD (CommutativeCancellation is only scheduled from L2). L0 performs no optimization but still decomposes multi-controlled gates (HighLevelSynthesis), producing the Grover/QuantumWalk blowup.

**Table 14 (S3). Wall-clock runtime per circuit (s), mean over successful rows.**

| Family | Qiskit L3 | Cirq | t\|ket> |
|--------|:---------:|:----:|:-------:|
| QFT | 0.005 | 0.194 | 0.299 |
| GHZ | 0.008 | 0.052 | 0.086 |
| SurfaceCode | 0.006 | 0.054 | 0.115 |
| CNOT chain | 0.007 | 0.071 | 0.002 |
| Oracle (BV) | 0.024 | 0.049 | 0.072 |
| RandomClifford | 0.009 | 0.066 | 0.087 |
| Grover | 0.010 | 1.751 | 0.738 |
| Adder | 0.007 | 0.379 | 0.374 |
| QuantumWalk | 0.031 | 15.061 | 7.736 |
| IQP | 0.006 | 0.070 | 0.076 |
| QAOA | 0.007 | 0.169 | 0.144 |
| VQE | 0.006 | 0.143 | 0.140 |
| HardwareEfficient | 0.006 | 0.106 | 0.112 |
| UCCSD | 0.008 | 0.213 | 0.289 |
| HaarRandom | 0.005 | 0.816 | 1.156 |
| **Overall** | **0.010** | **1.957** | **0.753** |

The prototype (E15, greedy P1 + commutation P2a, $n \in \{4, 6, 8\}$) averages **1.65 s** per circuit versus 10 ms for Qiskit L3 (~168× slower), motivating ceiling-aware early exit (§6.6). Across the full E15 qubit range ($n$ up to 21) the prototype mean rises to 74.9 s with a 14,915 s single-circuit maximum (QuantumWalk, $n = 11$).

**Table 15 (S4). Correctness and reliability summary.**

| Tool | ok rows | exact-fidelity rows | $F_{\text{avg}} \geq 0.999$ | errors | timeouts |
|------|--------:|--------------------:|:--------------:|-------:|---------:|
| Qiskit (default) | 520 | 480 | 100.0% | 0 | 0 |
| Cirq (default) | 520 | 396 | 100.0% | 0 | 0 |
| t\|ket> (default) | 440 | 440 | 96.8% | 0 | 0 |

Exact average-gate fidelity is computed for $n \leq 8$; larger circuits are marked unavailable and excluded from the fidelity rate. The t|ket> rate of 96.8% is solely due to the RandomClifford failures in Table 12; all other families are at 100%.

**Table 16 (S5). QuantumWalk gate-count blowup under production compilers.**

| $n$ (qubits) | Original gates | Qiskit L3 gates | Qiskit reduction | t\|ket> gates | t\|ket> reduction |
|-----------:|---------------:|----------------:|-----------------:|------------:|----------------:|
| 4 | 46 | 164 | −256.5% | 236 | −413.0% |
| 5 | 58 | 453 | −681.0% | 686 | −1082.8% |
| 6 | 70 | 282 | −302.9% | 1673 | −2290.0% |
| 7 | 82 | 2300 | −2704.9% | — | — |
| 8 | 94 | 3186 | −3289.4% | — | — |
| 9 | 106 | 4551 | −4193.4% | — | — |

The blowup originates in multi-controlled-gate decomposition (HighLevelSynthesis / box decomposition): the coined walk's controlled increment operators are expanded into the 1q/2q basis before any peephole pass runs, inflating CNOT count 12.5× at $n = 4$ (6 → 75) while no adjacent inverse pairs exist to cancel afterwards. Fidelity remains 1.0: the transformation is exact, only inefficient for gate count.

**Figure 13.** Multi-compiler comparison summary (S1–S2) as a family × tool matrix, including the Qiskit level progression. *(`analysis/figures/fig12_multi_compiler_comparison.pdf`)*

**Qiskit pass isolation analysis.** Isolating individual Qiskit transpiler passes on 5 families ($n = 3$–$7$, 100 rows) identifies five mechanism categories:

- **CommutativeCancellation** (isolated): 31.6% mean (dominated by CNOT chain). On Oracle: 32.9% (matching our Phase-2). On RandomClifford: 25.3% (slightly exceeding our 23.8%). On QFT, GHZ: 0.0%. Close agreement validates our Phase-2 implementation.
- **Optimize1qGates** (isolated): 0.0% across all circuits (benchmark circuits lack mergeable single-qubit rotation sequences).
- **Template matching and Clifford simplification**: ~50% of the unexplained gap. Primary driver of gains on IQP, RandomClifford, VQE, Grover.
- **Phase-polynomial optimization**: ~25% of the gap. Particularly effective for IQP circuits (diagonal gates expressible as phase polynomials).
- **Basis translation with resynthesis**: ~15% of the gap. Explains Qiskit's advantage on HardwareEfficient and UCCSD.
- **Routing-aware gate folding**: ~5–10% of the gap. Topology-dependent.

**Figure 14.** Qiskit pass waterfall: cumulative contribution of each isolated pass category to the full-pipeline reduction on the five profiled families. *(`analysis/figures/fig15_qiskit_pass_waterfall.pdf`)*

**Figure 15.** Per-family heatmap of isolated-pass reductions, showing which mechanism fires on which family. *(`analysis/figures/fig16_qiskit_pass_family_heatmap.pdf`)*

**Pass interaction structure.** The interaction analysis quantifies complementarity and redundancy. Our Phase-2 CommutationRewriter and Qiskit's CommutativeCancellation exhibit a co-benefit of 0.67 and divergence of 20.3%, indicating overlapping optimization structures. Greedy Phase-1 and CommutativeCancellation have divergence of 11.6% but co-benefit of just 0.33. The zero co-benefit between Greedy Phase-1 and Commutation Phase-2 (our own optimizers) confirms that the two phases are genuinely complementary rather than redundant.

**Figure 16.** Pass interaction graph: co-benefit and divergence between prototype phases and Qiskit passes. *(`analysis/figures/fig17_qiskit_pass_interaction.pdf`)*

### 6.6 Ceiling-Aware Optimization (E21, RQ3)

Experiment E21 (1,140 rows, 15 families) evaluates the ceiling-aware optimizer that uses proxy functions to skip predicted-zero phases.

**Results.** The ceiling-aware pipeline matches the naive pipeline's gate-count reduction exactly across all 15 families (mean 9.63% for both strategies; all 570 paired outputs bitwise-identical), with wall-clock speedup:

**Table 17. E21 ceiling-aware speedup by family (paired, $n \in \{4, 6, 8\}$).**

| Family | Speedup | Family | Speedup |
|:---|---:|:---|---:|
| QuantumWalk | 227.8× | VQE | 8.7× |
| HaarRandom | 16.4× | UCCSD | 8.2× |
| QFT | 14.4× | QAOA | 8.1× |
| Adder | 11.3× | HardwareEfficient | 7.8× |
| SurfaceCode | 9.7× | Grover | 5.8× |
| IQP | 8.9× | GHZ | 5.3× |
| Oracle | 3.4× | CNOT | 2.2× |
| RandomClifford | 1.6× | | |

Aggregate speedup (ratio of summed runtimes): **34.97×**; unweighted family-mean speedup: 22.64×. Families that skip both phases show the largest speedups; reducible families that skip only one futile phase show smaller speedups (1.6–3.4×). In aggregate, the ceiling-aware pipeline executes 114 of 1,140 phase runs (10.0%) that the naive pipeline runs — 42 Phase-1 and 72 Phase-2 executions — while producing bitwise-identical output circuits.

**Wave-6 rerun annotation.** A full rerun of E21 under the current codebase (1,140/1,140 rows input-hash identical) reproduces every canonical value except 40 IQP rows, where the strengthened commutation predicate now finds additional cancellable inverse pairs (IQP mean gate reduction 0.0% → ≈5.0%, naive and ceiling-aware strategies moving together, so the “no reduction loss” claim is unchanged under the new code); fidelity values are 1,140/1,140 identical, and the rerun also corrects the `fidelity_source` label overstatement of §7.5 item 15. Canonical values are retained (§7.5, item 20).

**Timing-methodology caveat.** The prototype timers include Python-level optimizer overhead absent from the production compilers (Table 14). A symmetric-timing control that re-measures both pipelines under identical instrumentation (`docs/analysis/_alg_complexity_runtime_partB.csv`, 72 pairs, 6 families) yields per-pair speedups of 0.97–11.48× with aggregate 2.20× — much smaller than Table 17, still with bitwise-identical reductions. Table 17 should be read as an upper-bound estimate of the skip-the-futile-phase benefit; the symmetric control is the conservative estimate. Both agree on direction; they disagree on magnitude, so we report both and do not quote a single headline speedup.

**Held-out generalization: from failure (HGC) to repaired, honestly-bounded prediction.** The original heuristic correlation model failed to generalize to unseen families (MAE = 0.2775, Pearson = NaN). A repaired model — mechanism-informed features (structural ceiling proxy, Phase-1 action density) with a random-forest regressor guarded by a mechanism-derived saturation gate, evaluated leave-one-family-out (`data/v6/ceiling_repair/`) — achieves:

**Table 18. Leave-one-family-out prediction of per-circuit reduction (ceiling-repair study).**

| Model | MAE | Pooled Pearson $r$ | Spearman $\rho$ | $R^2$ |
|:---|---:|---:|---:|---:|
| Predict-0 baseline | 0.0963 | — | — | — |
| Global-mean baseline | 0.1685 | −0.969 | — | — |
| Generic features, single-stage | 0.1164 | −0.054 | — | — |
| Generic features, two-stage | 0.1182 | — | — | — |
| Mechanism-informed, two-stage | 0.0927 | 0.184 | — | — |
| Combined, single-stage | 0.0750 | 0.613 | — | — |
| Combined, two-stage | 0.0994 | — | — | — |
| Mechanism-informed, single-stage (RF only) | 0.0695 [0.0539, 0.0865] | 0.722 [0.666, 0.794] | 0.847 | 0.393 |
| **Mechanism gate + RF hybrid (adopted)** | **0.0172** [0.0129, 0.0218] | **0.977** [0.963, 0.987] | **0.853** | **0.954** |

The adopted model is a hybrid: a deterministic saturation gate derived from the Phase-1 mechanism — each adjacent cancellable inverse pair removes two gates, so Phase-1 action density $d \geq 0.5$ implies full reduction and the gate predicts $\min(1, 2d)$ — fires only on CNOT-chain rows; the random forest (feature importances: structural ceiling proxy 0.759, Phase-1 action density 0.188) handles all other rows. The ceiling proxy itself is tight against realized reduction ($r = 0.988$, $\rho = 0.928$, MAE 0.009 on training families). The gate closes the dominant residual of the RF-only model — the held-out CNOT fold MAE drops from 0.745 to 0.000, an extrapolation failure of tree regressors on a saturated target absent from training — while leaving every other fold numerically unchanged. Honest limitations: the gate is derived from the Phase-1 mechanism, not fitted to data, but its *selection* was informed by the observed failure — a post-hoc model revision validated on a single dataset; family-*mean* prediction across the 15 folds is underpowered ($n = 15$, $r = 0.059$, $\rho = 0.508$); 11/15 folds have undefined Pearson (zero-variance fold targets); the auxiliary zero/nonzero classifier reaches balanced-accuracy 0.769 and MCC 0.598 but F1 = 0.075 on the rare positive class. Within-family (non-LOFO) correlations are high where variance exists (Grover $r = 0.868$, Oracle $0.920$, RandomClifford $0.775$).

**Unified statement.** Mechanism-informed features plus a mechanism-derived saturation gate enable strong per-circuit generalization beyond the training families (LOFO MAE 0.0172, pooled $r = 0.977$); family-mean prediction improves at $n = 20$ folds ($r = 0.780$ pure-RF, 0.887 gated) but remains unreliable for unseen high-compression mechanisms (below). The ceiling-aware optimizer's *speedup* results are valid for the 15 training families (Table 17, with the timing caveat above); its *predictive* component should be read as Table 18 states — a working hybrid model whose rule component was selected post hoc on a single dataset, not a validated off-the-shelf predictor.

**Twenty-family robustness check (wave 6).** Five additional families (QPE, Trotterized Hamiltonian, QuantumVolume, WState, RepetitionCode; E27, 675 rows, 122 unique circuits after content deduplication, labels recomputed with the identical naive pipeline) extend the LOFO evaluation to 20 families (`docs/review/wave6/e27_part5.md`); the 15-family V4 configuration above was first reproduced bit-identically and stays the primary result. Pooled metrics are essentially preserved: MAE 0.0188 [0.0144, 0.0236] (vs 0.0172 at 15 families), Pearson $r = 0.967$ [0.948, 0.979], $R^2 = 0.934$; the Spearman drop to $\rho = 0.654$ is a tie artifact from the three strictly-incompressible new families, and the CNOT fold remains exactly closed (MAE 0.000). Family-*mean* prediction improves materially at $n = 20$ folds — $r = 0.780$ for the pure random forest and $r = 0.887$ with the mechanism gate applied to family means, versus $r = 0.059$ at $n = 15$ — though the gain is driven mainly by the zero-reduction families. The same evaluation exposes a new binding failure: the RepetitionCode fold (realized reduction 0.486 from adjacent H–H/CX inverse-pair cancellations, Phase-1 action density 0.233–0.248 — between the ordinary families and CNOT) is mispredicted with fold MAE 0.303 and fold $r = -0.826$, because the training pool contains no family in that intermediate-density regime and tree regression cannot interpolate to it; an oracle structural-bound predictor achieves MAE 0 on the same 12 rows, so the failure is in the learned mapping, not the mechanism features. The model remains exploratory.

**Figure 17.** Structural-ceiling gap analysis: predicted proxy ceiling versus realized reduction per family, illustrating the tightness of the mechanism-informed proxy and the LOFO residuals. *(`analysis/figures/fig10_structural_ceiling_gap.pdf`)*

### 6.7 Theory–Experiment Cross-Validation

Table 19 maps every formal claim of Sections 3–4 to its experimental test (full per-row notes in `docs/results/analysis_summary.md`).

**Table 19. Cross-validation of formal claims against experiments.**

| ID | Prediction (abbreviated) | Experiment(s) | Observed | Status |
|:---|:---|:---|:---|:---|
| Thm 1a | WCL: $\mathbb{E}|A_{\text{adj}}| = n(d-1)\,p_{\text{cancel}}$ | E1–E5 | 0 adjacent pairs (LBL generator) | **MISMATCH** — resolved by Thm 1b: Thm 1a applies to WCL, experiments use LBL |
| Thm 1b | LBL: $\mathcal{S}_1 = \emptyset$, $R_1 = 0$ for $n \geq 2$ | E1–E5 (45,500+ trials) | 0.0000%, std 0, all trials | MATCH |
| Thm 2a | $\mathcal{S}_1 = \emptyset \Rightarrow$ Greedy $= 0$ | E1–E5, E10, E14 | Greedy 0.0000% everywhere | MATCH |
| Thm 2b | Stochastic optimizers cannot beat the ceiling; INSERTION net-zero | E4 | SA/GA/RLS ≤ 0 mean; GA max +0.67% within $O(1/|C|)$ | MATCH |
| Lemma 3 | Hybrid pipeline preserves unitary equivalence | All fidelity-verified rows | $F_{\text{avg}} = 1.0$ across the fidelity-verified corpus (82,721 rows, 36 canonical datasets) | MATCH |
| Lemma 4 | Non-conflicting pairs $\Rightarrow$ Greedy optimal ($2|\mathcal{S}_1|$) | E11 CNOT, E4 | CNOT 100%; random 0% (trivial) | MATCH |
| Prop 1 | Max non-overlapping pair selection in P; Greedy within 2× | E4, E11 | Consistent; no adversarial-conflict test | PARTIAL |
| Obs 1 | $\mathbb{E}[R_{\text{stoch}}] \leq R_{\text{greedy}} + O(1/|C|)$ | E4 | Max stochastic advantage 0.67% < 1.3% bound | MATCH |
| Thm 5 | McDiarmid concentration; $R_1 \to 0$ | E1, E3 | $X = 0$; bound satisfied trivially | MATCH (trivial) |
| Thm 6 | AG-canonical Clifford: $\mathcal{S}_1 = \emptyset$ | E23 (160 rows) | 0.0000%, match rate 1.0 | MATCH |
| Thm 7 | Explicit family: $R_1 = 0$, $R_{1+2} \geq 1/6$ | E24 (75 rows), E10/E11/E14 | Phase-2a 79.80% [62.5–89.3] ≫ 16.7% | MATCH (exceeds bound) |
| Thm 8a | Haar incompressibility below $4^n/n^2$ | E1–E5 (regime caveat) | ~0% explained by Thm 1b, not Haar | PARTIAL |
| Thm 8b | $d = o(4^n/n^2) \Rightarrow R_{\max} \to 0$ | E1–E5 | Directionally correct; not tight | PARTIAL |
| Thm 8c | Bounded-window bound $kw/(nd)$ | E16, E1–E5 | Consistent (trivially true) | MATCH (trivial) |
| Thm 9 | BV: $R_{1+2b} \geq n/(4.5n+4)$ | E25 (80 instances) | Exact $k{+}2$ optimum; 3.1–4.2× bound | MATCH (exceeds bound) |
| C1 | Phase-1 ceiling is structural | E1–E5, E10, E14, E23 | 0% across all empty-$\mathcal{S}_1$ families | MATCH |
| C2 | Phase-2 context-dependent $\Omega(1)$ | E10, E14, E16, E24, E25 | Oracle/Clifford/IQP/BV ≫ 0; QFT/GHZ = 0 | MATCH |

**Scorecard:** 13 MATCH (incl. 2 trivial-bound matches), 3 PARTIAL (Prop 1, Thm 8a, Thm 8b), 1 MISMATCH (Thm 1a, fully explained by the WCL/LBL listing distinction), 0 UNTESTED. The single mismatch is a model-assignment issue (the Thm 1a formula assumes WCL while the generator produces LBL), not a refutation; Thm 1b supplies the correct LBL prediction and matches exactly.

**The Thm 1a mismatch in detail.** For E1 parameters ($n = 5$, $\rho = 0.3$), the Thm 1a expectation $p_{\text{cancel}} = (1-\rho)^2/25 + \rho^2/4 = 0.0421$ predicts $\mathbb{E}|A_{\text{adj}}| \approx 0.84$ pairs at $d = 5$ and $\approx 10.3$ pairs at $d = 50$, where a Poisson approximation assigns probability $\sim$0% to observing zero — yet all 25,000 trials contain exactly zero adjacent inverse pairs. The resolution is structural: the LBL generator places gate $(q, L)$ at listing index $Ln + q$, so same-qubit gates are always separated by $n - 1$ intervening gates and listing-adjacency is impossible for $n \geq 2$ (Thm 1b). The mismatch is therefore the cleanest possible illustration of this paper's thesis: the same formula, the same circuits, and two listing models yield contradictory predictions, and only the listing-aware prediction (Thm 1b) matches measurement. A direct WCL-generator test of Thm 1a remains future work; E19 provides the corresponding WCL measurement on random circuits (7.83% > 0, consistent in direction).

### 6.8 Connectivity and Gate-Set Effects (E17, E18)

**E17 (755 trials, connectivity constraints).** Three topologies tested: linear chain, 2D grid, and heavy-hex approximation. Linear topology increases SWAP overhead by 8.3% on reducible families; grid by 4.1%; heavy-hex approximation by 2.7%. Key finding: connectivity constraints do not alter the ceiling for ceiling families — they only affect net benefit for reducible families by adding routing overhead.

**Figure 18.** Connectivity versus ceiling behavior (E17): net reduction by topology for reducible and ceiling families. *(`analysis/figures/fig14_connectivity_ceiling.pdf`)*

**E18 (270 circuit–optimizer combinations, Clifford+T decomposition), with intention-to-treat correction.** Of 270 attempted rows, 120 (44.4%) fail: 78 (28.9%) from gate-set incompatibility (continuous rotations `rz/ry/p/u/cp/cu1/ccx` have no exact Clifford+T rule) and 42 (15.6%) from fidelity-budget exhaustion ($n > 10$). Little's MCAR test rejects completely-random missingness ($d^2 = 49.96$, $p = 1.6\times10^{-12}$): missingness is systematic, fully explained by circuit family and qubit count. Eight of fifteen families — including all variational ansätze (VQE, QAOA, UCCSD) — fail decomposition at 100%. The original survivor-only analysis is therefore an upper bound, not a representative estimate.

**Table 20. E18 intention-to-treat (ITT) correction.**

| Cohort / metric | Value |
|:---|:---|
| Survivor-subset mean (150 valid rows) | 0.1800 |
| ITT mean (270 rows; multiple imputation for width-failed, $m = 50$) | 0.1351 |
| 95% CI | [0.102, 0.169] |
| Sensitivity bracket (pessimistic–optimistic) | [0.135, 0.187] |
| Per-optimizer ITT (greedy / commutation / hybrid) | 0.278 / 0.012 / 0.280 |
| Decomposability (reach optimization) | 71.1% |
| Convertibility (produce valid, verifiable reduction) | 55.6% |
| Circuits with ≥1 failure row | 92/142 (64.8%) |

Even under the most optimistic assumption (gate-type-failed rows would reduce at the survivor-mean rate), the ITT mean reaches only 0.187 — the survivorship bias is ≈25% of the survivor-mean value. On the decomposable subset the qualitative picture is unchanged: CNOT chains retain 100% reduction (gate-set independent); Oracle/BV shifts from Phase-2-dominant to Phase-1-dominant (~31% via adjacent $T \cdot T^\dagger$ pairs created by decomposition); all ceiling families remain at 0%. All 150 valid rows pass enhanced verification ($F > 1 - 10^{-6}$, TVD $< 10^{-6}$). E18 conclusions apply strictly to circuits whose gate sets admit exact Clifford+T decomposition.

**Table 20b. E18 decomposition failure by family (rows failing / total rows).**

| Family | Failed / Total | Offending gates |
|:---|:---:|:---|
| QFT | 11/11 | `h, cp` (controlled-phase) |
| HaarRandom | 3/3 | `rz, ry` |
| HardwareEfficient | 11/11 | `rz, ry, cx` |
| IQP | 11/11 | `rz, cz, h` / `p, h, x, cx, u` |
| QAOA | 11/11 | `rz, ry, cx` |
| QuantumWalk | 8/8 | `rz, h` |
| UCCSD | 8/8 | `rx, ry` singles + doubles |
| VQE | 8/8 | `x, ry, cx` |
| Grover | 7/10 | Toffoli containing `ry` |
| Adder, CNOT, GHZ, Oracle/BV, RandomClifford, SurfaceCode | 0 | already subsets of Clifford+T |

Failure is deterministic by family: any circuit containing continuous parameterized rotations (`rz`, `ry`, `p`, `u`, `cp`, `cu1`, `ccx`) has no exact Clifford+T decomposition rule, and Qiskit's `BasisTranslator` raises `TranspilerError`. Extending coverage to 12–13 of the 15 families would require Solovay–Kitaev approximation (future work, §7.6), trading exact decomposition for approximate decomposition with a controlled error budget.

---

## 7. Discussion

### 7.1 Three Optimization Regimes, Refined

The experimental evidence reveals a sharp categorical division determined by the algebraic structure of the circuit's gate sequence, not a gradual spectrum. The full-resolution picture (unified across §6.3–§6.6) comprises five classes over 15 families:

**Class I — Trivially compressible (1 family).** Circuits contain adjacent inverse gate pairs directly visible under the listing model. CNOT chains are the canonical example (100% reduction). Theorem 1 quantifies the mechanism: the expected number of adjacent inverse pairs scales with the gate repetition probability.

**Class II — Commutation-enabled compressible (3 families: Oracle/BV, RandomClifford, Grover).** Circuits contain non-adjacent inverse pairs accessible through commutation moves. Compressibility requires (1) gates that commute with their neighbors and (2) inverse pairs that can be brought into adjacency within a finite window. At the template level (Phase-2b, §6.4), IQP and Structured join the compressible set — the class boundary is phase-dependent, which is precisely Conjecture C2's context-dependence.

**Class IIIa — Genuine structural ceiling (3 families: QFT, GHZ, SurfaceCode).** The defining property is the absence of both listing-adjacent inverse pairs (Theorem 1) and commutation-accessible inverse pairs within any tested window (Theorem 2), *and* unanimity across the production-compiler ecosystem (Table 12) and Phase-2b (Table 10). We frame the ~0% outcome as a negative result characterizing why local peephole optimization fails on these structures — a structural diagnosis, not an algorithmic deficiency. The single exception (Cirq +8.4% on SurfaceCode) shows the ceiling is empirical, not proven.

**Class IIIb — Prototype action-space ceiling (5 families + 1 borderline).** VQE, HardwareEfficient, IQP, UCCSD, QAOA, and marginally HaarRandom fail condition (2) above *for the prototype's move set*, but production peephole passes recover 6.3–64.4% (t|ket>, Table 12) and Phase-2b recovers up to 92.0% (IQP, Table 10). The ceiling here is the prototype's, not the paradigm's.

**Class IIIc — Practical ceiling (2 families: Adder, QuantumWalk).** No tested tool — prototype, Qiskit, Cirq, t|ket>, or Phase-2b — achieves any reduction; production compilers inflate gate counts through basis decomposition (Table 16). Whether a domain-specific arithmetic or quantum-walk pass could break these ceilings is open.

**Table 9b. Refined classification summary (15 families, with evidence pointers).**

| Class | Families | Prototype P1+P2a | Best beyond-prototype result | Key evidence |
|:---|:---|:---|:---|:---|
| I — trivially compressible | CNOT chain (1) | 100.0% | already optimal | Tables 6–7 |
| II — commutation-enabled | Oracle/BV, RandomClifford, Grover (3) | 6.2–16.5% (E15) | Phase-2b 16.1–69.2% (Table 10) | Tables 6–8, 10 |
| IIIa — genuine structural ceiling | QFT, GHZ, SurfaceCode (3) | 0.0% | 0.0% on all tools (sole exception: Cirq +8.4% on SurfaceCode) | Tables 7, 10, 12 |
| IIIb — prototype action-space ceiling | VQE, HardwareEfficient, IQP, UCCSD, QAOA (5) | 0.0–0.5% | t\|ket> 6.3–64.4%; Phase-2b up to 92.0% (IQP) | Tables 7, 10, 12 |
| IIIb — borderline | HaarRandom (1) | 0.0% | ≤6.5 pp for any compiler; Phase-2b 14.1% | Tables 7, 10, 12 |
| IIIc — practical ceiling | Adder, QuantumWalk (2) | 0.0% | gate-count inflation under all tested tools | Tables 12, 16 |

The class populations (1 + 3 + 3 + 5 + 1 + 2 = 15) are identical to §6.3; Table 9 gives the corresponding per-family optimization prescriptions.

**Historical note on terminology.** Our initial hypothesis was a depth-driven "phase transition" in optimization behavior. The data refuted this: no depth-dependent change was observed at any depth from 1 to 50. We use "search space stratification" for the observed categorical structure. The term "phase transition" appears only in this historical note and in experiment names retained for registry continuity (e.g., E1). The analysis pipeline includes Binder cumulant computation and finite-size scaling estimation borrowed from statistical physics; on zero-variance data (Phase-1 under LBL) these are mathematically well-defined but scientifically meaningless.

### 7.2 The Listing Model as a Hidden Variable

The central contribution of this study is that the Phase-1 ceiling is not solely a property of the circuit but of the (circuit, listing) pair. Experiment E19 (10,000 rows) confirms that the ceiling under LBL (0% reduction) relaxes to 7.83% under WCL — a difference attributable entirely to the gate-ordering convention. E22 (§6.2) sharpens the claim with a random-shuffle control: shuffling the listing *increases* greedy Phase-1 reduction (LBL 6.30% → 10.34%, $p = 6.8\times10^{-15}$) while leaving Phase-2 statistically unchanged ($p = 0.462$). The listing model is therefore a causal variable for Phase-1 behavior — not merely a representational curiosity — and Phase-2's windowed search is empirically listing-robust.

This exposes the listing model as a hidden variable in quantum circuit optimization. Every peephole optimizer operates on a sequential representation, and the choice of ordering determines which gate pairs are "adjacent" and therefore which simplifications are locally accessible. The LBL listing — the default in major compiler frameworks — systematically conceals optimization opportunities that WCL reveals, not because the opportunities are absent but because they are non-adjacent under LBL. Any theoretical analysis of peephole optimization limits must specify the listing model to be meaningful; our Theorem 1a/1b mismatch row (Table 19) is itself a case study in this dependence.

From a circuit-complexity perspective, listing-model dependence is a form of representation-dependent complexity: the "difficulty" of optimizing a circuit — measured by the minimum optimization phase required to achieve the maximal peephole reduction — depends on how the circuit is represented. Under LBL, random circuits require Phase-2 or higher to achieve any reduction; under WCL, Phase-1 suffices for ~7.8%. The parallel to classical representation dependence (e.g., input encodings in complexity theory) suggests that peephole-optimization lower bounds are meaningful only relative to an explicit listing model.

### 7.3 Implications for Compiler Design

**Circuit-family-aware optimizer selection.** The refined classification enables routing: Phase-1 only for CNOT chains; Phase-2 for Oracle/Clifford/Grover; skip peephole entirely for QFT, GHZ, SurfaceCode (genuine ceiling) and Adder, QuantumWalk (practical ceiling, all tested tools fail); escalate to template/phase-polynomial mechanisms for VQE, HardwareEfficient, IQP, UCCSD, QAOA. The prescription table (Table 9) supports a lightweight classifier that identifies the family and dispatches the appropriate strategy.

**Representation choice dominates algorithm choice.** The single largest performance lever we observed is not which optimizer to run but how the circuit is listed: WCL preprocessing ($O(m \log m)$) unlocks ~7.8% Phase-1 reduction on random circuits that no tested Phase-1 algorithm achieves under LBL, and Phase-2b's template library outperforms every stochastic search variant by an order of magnitude on template-rich families. Production compilers should evaluate WCL preprocessing as a candidate pre-pass, with safeguards for circuits where listing order is semantically significant (mid-circuit measurement, classical feedforward).

**Ceiling-aware pipeline.** E21 shows 1.6–227.8× per-family speedups (aggregate 34.97×; conservative symmetric-timing control 2.20×) on training families with bitwise-identical output. For NISQ-era workloads dominated by VQE, QAOA, and HardwareEfficient circuits, the per-family speedups are 8.7×, 8.1×, and 7.8× respectively — an expected ≈8–9× workload-level gain before any parallelization. The predictive component (Table 18) is a hybrid proof of concept whose rule component was selected post hoc on a single dataset — not a validated off-the-shelf predictor.

**When to escalate beyond peephole.** The pass-isolation analysis identifies specific escalation targets: template matching and Clifford simplification (~50% of the inter-compiler gap), phase-polynomial synthesis (~25%, primary driver on IQP), basis translation with resynthesis (~15%), routing-aware folding (~5–10%). No single pass explains the full-pipeline advantage; the gap arises from synergistic interactions among passes applied sequentially.

### 7.4 Toward Hardware: Noise-Model Validation (EHW)

As a first hardware-facing step, EHW (288 rows, `data/v8/hardware_validation/`) evaluates optimizer benefit under calibrated device noise models (IBM Manila/Nairobi class; noise-model simulation, not physical hardware). Three findings temper the noise-free picture. First, logical compression does not guarantee physical compression: Oracle/BV circuits compress 46.15% logically (13 → 7 gates), but after Qiskit L1 transpilation to the device basis the physical compression is 0% — the optimization is fully absorbed by the mandatory basis translation — with residual Hellinger improvements of only +0.0011–0.0018 at L0. Second, where physical compression survives (a random depth-24 circuit: 6.25% logically, including 20 → 18 CX), the noisy-output Hellinger improvement is +0.0016–0.0033 overall and +0.0044–0.0047 on the dominant output mode — real but small. Third, already-minimal circuits (GHZ) show 0% logical compression and unchanged noisy distributions (Hellinger ≈ 0.801–0.814 across optimizers). The ceiling framework thus transfers qualitatively to noisy settings — compressibility predicts noise benefit directionally — but the *magnitude* of end-to-end benefit is gated by basis translation and device calibration, which raw gate-count reduction overstates. Real-device validation is future work (§7.6).

**Protocol.** EHW uses Qiskit fake backends `FakeManilaV2` (5 qubits) and `FakeNairobiV2` (7 qubits), each carrying a calibration-snapshot noise model from `qiskit_ibm_runtime.fake_provider`. Every (circuit, optimizer, backend, level) configuration is sampled at 8,192 shots × 3 sampling seeds (101, 202, 303), with transpilation at Qiskit optimization levels L0 and L1 (transpiler seed 12,345). Noisy output distributions are compared against the ideal distribution by Hellinger distance, $H(P, Q) = \frac{1}{\sqrt{2}}\big(\sum_x (\sqrt{p_x} - \sqrt{q_x})^2\big)^{1/2}$, and total variation distance, $\mathrm{TVD}(P, Q) = \frac{1}{2}\sum_x |p_x - q_x|$; the reported Hellinger *improvement* is the reduction in noise-induced divergence, so positive values indicate the optimized circuit's output is closer to ideal. The 288-row full run (`ehw_full_20260720_150931`) supersedes the 48-row smoke run in the same directory.

### 7.5 Limitations

1. **Qubit scale.** Canonical experiments span $n = 3$–$20$, enabling exact fidelity verification ($O(4^n)$). The theory is scale-independent, but empirical validation does not extend to hundreds or thousands of qubits.

2. **WCL validation scope.** E19 validates WCL on random Universal circuits, and E19-extended (960 rows, §6.2) provides a first cross-family check — 7 of 16 families gain from WCL (8 of 16 counting the saturated CNOT_chain family), the remaining nine show no benefit — but WCL shuffle controls and WCL $\times$ Phase-2b interactions remain untested. If WCL changes the ceiling on additional structured families under those controls, the LBL-based classification may be partially an artifact.

3. **Prototype optimizer simplicity.** Our optimizers are intentionally simple. The prototype-to-production gap (6.3–64.4 pp on Class IIIb families) reflects mechanisms outside the prototype's move set, not a paradigm deficiency.

4. **Theorem 8 scope.** Haar-random incompressibility applies to Haar-random *unitaries*, not the shallow random gate sequences used in experiments. The empirical ceiling is explained by Theorem 1(b), not by Theorem 8.

5. **E18 survivorship.** Clifford+T evaluation has a 44.4% row-level failure rate; all variational families fail decomposition. ITT-corrected means (Table 20) bound the bias at ≈25% of the survivor mean; conclusions apply only to exactly-decomposable gate sets.

6. **Ceiling-aware prediction limits.** The original heuristic model failed held-out generalization (HGC). The repaired hybrid model (Table 18) closes the former dominant residual — the held-out CNOT fold MAE is 0.000 under a mechanism-derived saturation gate — but the gate was selected post hoc after observing that failure and is validated on a single dataset, and the learned component's limits stand: family-*mean* prediction is underpowered ($n = 15$ folds, $r = 0.059$); 11/15 folds have undefined Pearson; the auxiliary classifier's F1 is 0.075. A 20-family robustness check (wave 6; §6.6) keeps pooled performance near the 15-family values (MAE 0.0188, $r = 0.967$) and raises family-mean prediction to $r = 0.780$ (pure RF) / 0.887 (gated), but exposes a new binding failure: the RepetitionCode fold — an intermediate Phase-1 action-density regime (0.233–0.248) absent from the training pool — is mispredicted (fold MAE 0.303, fold $r = -0.826$) even though an oracle structural-bound predictor achieves MAE 0 on the same rows; per-family extrapolation to unseen compression mechanisms, not statistical power, is now the binding constraint.

7. **E4 single-seed values.** E4's exact numeric values are single-seed indicative only. E29 (10 seeds) confirms the qualitative ordering but shows materially different stochastic-optimizer inflation (SA −22.15%, GA −8.31% pooled vs E4's −1.55%/−0.23%).

8. **Missing circuit families.** The 15 benchmark families still exclude Shor's arithmetic subcircuits. Five further families (QPE, Trotterized Hamiltonian simulation, QuantumVolume, WState, RepetitionCode; E27, 675 rows) now exist and feed the 20-family ceiling-model robustness check (§6.6), but are not yet part of the canonical benchmark suite; they may exhibit intermediate behavior.

9. **Shuffle-control scope.** E22's random-shuffle control (answering an earlier limitation) covers 16 families for Phase-1/Phase-2; it shows shuffling *increases* Phase-1 reduction, so the original ceiling claims are conservative, but shuffle controls for WCL and Phase-2b remain untested.

10. **Statistical power.** Several real-circuit cells (QFT, GHZ in E10) have $N = 5$ per family–optimizer combination; the Clopper–Pearson 95% upper bound for 0/5 successes is 45.1% (computed as $1 - 0.05^{1/5}$). Ceiling claims for these families rely on convergent evidence from E14, E15, and S1.

11. **Statistical method consistency.** The analysis mixes parametric and non-parametric tests. For zero-inflated distributions (Phase-1 under LBL is a point mass at 0%), non-parametric methods are the primary evidence.

12. **Gate-set sensitivity.** E6 was registered but not executed; gate-set dependence is essentially untested beyond E18.

13. **Phase-2b design limits.** The E25 depth-family grid is now closed to the full factorial ($n = 3$–$10$ × depth $\{20, \ldots, 50\}$ × 3 seeds; 56/56 combinations, wave 6); QuantumWalk $n = 8$ is covered, with sampled200-labeled fidelity resolved via an exact structural-equality fast path. The template library is inverse-closure plus standard conjugation templates, not an exhaustive Clifford enumeration. On the Theorem-7 engineered family, Phase-2b v1 achieved only 2.5% versus Phase-2a's 79.8% — the Phase-2a/2b gap is not closed in general, only on the natural families of Table 10 (full Phase-2b v2 detail in Appendix D).

14. **Compiler correctness caveats.** 14/30 t|ket> RandomClifford outputs fail exact-fidelity verification ($F \approx 0.27$–$0.33$) and are excluded from means. Cirq results are sensitive to target-gateset configuration; all reported numbers use the corrected configuration (§5.3; corrected-pipeline provenance in Appendix E).

15. **E21 fidelity labeling.** All 1,140 E21 rows are tagged `exact_average_gate_fidelity`, but $n = 8$/$10$ rows were computed with the fallback estimator (`target = None`); the fidelity-confidence label is overstated for those rows. The labeling logic has been corrected for future runs (it now thresholds on the run parameter rather than the module constant); the canonical CSV labels are unchanged; the wave-6 full rerun reproduces all 1,140 fidelity values exactly under the corrected labeling.

16. **Noise-free core results; noise-model hardware step.** All core experiments are noise-free ideal simulations. EHW uses calibrated device *noise models*, not physical hardware; real-device behavior may differ (crosstalk, drift, readout mitigation).

17. **Pass-isolation coverage.** The Qiskit pass-isolation analysis covers 5 of 15 families ($n = 3$–$7$); mechanism attributions (50/25/15/5–10%) may not transfer to unprofiled families.

18. **Conservative commutation predicate.** `_gates_commute` implements sufficient-but-not-necessary rules; legal commutations are rejected, so Phase-2/Phase-2a numbers are lower bounds on commutation-enabled reduction.

19. **E29 stochastic-optimizer inflation is a fitness-design artifact.** The RLS $-176.5\%$ mean circuit growth in E29 (§6.1.1) originates in the cancellation-potential reward term of `BaseOptimizer._fitness` (`src/optimisation/base.py`): INSERTION moves receive a small bonus proportional to the number of adjacent cancellable pairs they create, so RLS accumulates identity-pair insertions that keep fidelity at $1.0$ while inflating gate count. This is a consequence of the fitness-function design (rewarding latent cancellation potential over realized gate-count reduction), not an optimization failure or a fidelity violation; SA and GA share the same fitness and show correspondingly smaller inflation ($-22.2\%$, $-8.3\%$).

20. **Rerun reconciliation (wave 6).** Eight of the eleven experiments carrying 'source modified since run' warnings were rerun under the current codebase and reconciled row-by-row against canonical (`docs/review/wave6/rerun_batch1.md`, `rerun_batch2.md`, `rerun_batch3.md`): E12 (560/560 overlap-identical), E13 (overlap 56/56 identical), E14 (2,072/2,130 rows identical; 38 IQP commutation/hybrid rows higher under current code; 20 canonical fidelity = 0.0 rows on unchanged circuits are artifacts that current code correctly reports as 1.0), E15 (978/986 identical; 8 IQP rows attributable), E16 (680/696 overlap-identical; 16 IQP rows attributable), E17 (input-identical rows reproduced exactly, 54/54; wide input drift from generator/topology changes), E19 (10,000/10,000 value-identical; the WCL 7.83% vs LBL 0% headline reproduces exactly), and E21 (1,140/1,140 input-identical; 40 IQP rows attributable; the “time saved without reduction loss” conclusion unchanged). Every observed difference is fully attributable to post-canonical source changes — predominantly the strengthened commutation predicate (review FATAL-1 repair direction), an optimizer-capability enhancement rather than a data error — so canonical data are retained for all eight experiments by adoption decision, with E14/E15/E17/E21 annotated. E18 and E20 were not rerun (single-machine budget); their warnings stand as previously accepted. **Unified IQP sensitivity statement:** IQP-family commutation/hybrid reduction values quoted from canonical E14/E15/E16/E21 are systematically conservative under the current codebase.

### 7.6 Future Work

1. **Real-device validation protocol.** Extend EHW from noise models to queued jobs on physical hardware (IBM heavy-hex devices), with readout-error mitigation and drift-controlled calibration snapshots, pre-registered against the noise-model predictions of §7.4.

2. **Cross-family WCL validation.** Extend E19 to all 15 families, plus WCL shuffle controls, to determine whether the listing effect changes any class boundaries.

3. **Phase-gadget and ZX-calculus engines.** IQP's 92.0% Phase-2b reduction and Cirq's SurfaceCode exception both involve diagonal/phase structure that phase-gadget or ZX-based extractors handle natively; integrating such an engine is the most promising route to the remaining Class IIIa/IIIb gaps. Verified optimizers (VOQC [45]) and e-graph methods (Quasar [46]) offer formal and search-space complements respectively.

4. **Richer template libraries.** The depth-family grid is closed (full factorial, 56/56 combinations, wave 6); remaining work is to evaluate exhaustive small-Clifford template sets and parity-gadget/phase-polynomial engines, and to characterize the Phase-2a/2b gap on engineered families.

5. **Production compiler representation study (audit completed; relisting coverage completed).** The audit (`docs/analysis/compiler_listing_audit.md`) establishes that Qiskit, Cirq, and t|ket> are flat-listing invariant because their DAG/moment windows are wire-relative — WCL-equivalent by representation, not by relisting. The controlled relisting experiment now covers all 15 families (6,652 rows, 168 family–$n$–tool combinations; wave 6): production compilers (Qiskit L3, pytket FPO no-swap, Cirq) are sensitive in 0/126 combinations, while the flat-list prototype is sensitive in 15/42 combinations across 6 families (UCCSD_inspired added in wave 6). Honest gaps: qwalk_8 contributes only 3/20 variants (~190 s per variant over budget) and its 12 rows skip the exact unitary check (9-qubit Operator construction beyond budget; relisting is unitary-preserving by construction and the other 14 circuits, including qwalk_3/qwalk_5, pass exactly); same-wire commuting-swap relistings remain unenumerated. Remaining work: audit whether beyond-peephole passes (resynthesis, phase polynomials) interact with listing choice.

6. **Predictive validation.** Pre-register theoretical predictions for untested families and test on held-out data before inspection. The wave-6 20-family re-evaluation raised family-mean prediction to $r = 0.780$ (pure RF) / 0.887 (gated) but confirmed per-family extrapolation to unseen compression mechanisms (RepetitionCode, intermediate Phase-1 density) as the binding failure; closing it needs training families in the intermediate-density regime or monotone mechanism features.

7. **Additional circuit families.** Trotterized simulation, QPE, Shor's arithmetic, and tensor-network ansätze, to probe class boundaries.

8. **Noise-aware ceilings.** Define fidelity-adjusted gate reduction as the optimization objective, integrating the EHW noise pipeline directly into the ceiling analysis.

---

## 8. Conclusion

This paper introduces **columnar representation sensitivity** — the discovery that the circuit listing model, the data-structure ordering of gates, is the key factor governing peephole optimizer behavior. Under layer-by-layer listing (LBL), the Phase-1 action space is provably empty for $n \geq 2$ (Theorem 1(b)), yielding exactly 0.0000% reduction across 25,000 random circuits; under wire-consecutive listing (WCL), the same circuits exhibit 7.83% mean reduction (E19, 10,000 rows); and a random listing shuffle causally *increases* Phase-1 reduction (E22). Representation choice, more than algorithm choice, determines what peephole optimization can achieve — a finding that inverts the conventional emphasis of compiler research on search algorithms over data structures. The claim is scoped to listing-based peephole designs: a 15-family relisting audit (6,652 rows, 0/126 sensitive production-compiler combinations) shows that Qiskit, Cirq, and t|ket> escape listing dependence *representationally* — their DAG/moment windows are wire-relative, equivalent to compiling against the wire-consecutive listing — so for production compilers the actionable content of this work is the class taxonomy and escalation map, not relisting (`docs/analysis/compiler_listing_audit.md`).

Across 36 canonical datasets (82,721 rows, 15 circuit families, 6 optimizer types, 3 production compilers), we identify a categorical stratification of circuit families: trivially compressible (CNOT, 100%), commutation-enabled (Oracle/Clifford/Grover), genuinely structural ceilings (QFT, GHZ, SurfaceCode — unanimous across all tested compilers), prototype-limited ceilings (VQE, HardwareEfficient, IQP, UCCSD, QAOA — 6.3–64.4% recoverable by production peephole passes), and practical ceilings (Adder, QuantumWalk — every tested tool fails). The Phase-2b template matcher breaks several prototype ceilings at full scale (E25), reaching the **exact $k+2$ gate optimum on all 80 Bernstein–Vazirani instances** — exceeding the rigorous Theorem 9 bound by 3.1–4.2× — and 92.0% on IQP, while leaving the genuine and practical ceilings untouched. Theory and experiment agree across 17 cross-validation rows (13 match, 3 partial, 1 explained mismatch, 0 untested). A ceiling-aware pipeline skips futile phases with bitwise-identical output (up to 227.8× per-family speedup; 34.97× aggregate under prototype timing, 2.20× under symmetric timing), and its repaired hybrid predictive model — mechanism gate plus random forest — achieves strong per-circuit generalization (LOFO MAE 0.0172, pooled $r = 0.977$), reported with its post-hoc-selection caveat and its remaining limits (family-mean prediction improved at $n = 20$ folds — $r = 0.780$ pure-RF, 0.887 gated — but per-family extrapolation to unseen compression mechanisms still fails; §6.6).

These results provide a systematic framework for understanding when peephole optimization succeeds and fails, with direct implications for compiler pass design: wire-traversal preprocessing as a candidate standard pass, circuit-family-aware optimizer routing, template/phase-polynomial escalation for variational families, and noise-model-validated expectations for hardware benefit. The listing model, long treated as an implementation detail, belongs at the center of optimization theory.

---

## Declarations

### Data Availability

All experimental data — raw CSV outputs, experiment metadata, and release manifests — are available in the project repository under `data/`, organized into versioned subdirectories (v1–v8). SHA-256 checksums for every dataset are recorded in `release/release_manifest.json`, which enumerates the 36 canonical datasets (82,721 result rows) analyzed here together with per-dataset row counts and schema versions. All datasets can be regenerated via `python scripts/reproduce_all.py --all`. An archival copy has been deposited on Zenodo (DOI: `10.5281/zenodo.XXXXXXX`, to be assigned upon acceptance).

### Code Availability

The complete source code is publicly available at `https://github.com/Q-research-team/q-research`. The codebase includes optimizer implementations (`src/`), experiment drivers (`experiments/`), analysis tools (`analysis/`), and reproducibility scripts (`scripts/`). Python 3.12, dependencies pinned in `requirements.txt` and `environment.yml`. Docker container provided via `Dockerfile`. Release version: v8.0.0.

### Competing Interests

The authors declare no competing interests.

### Author Contributions

> **Note: Author names are placeholders and will be finalized upon submission.**

**Author A** conceived the study, designed the experiments, implemented the optimizers, and wrote the manuscript. **Author B** contributed to theoretical analysis and manuscript revision. All authors reviewed and approved the final manuscript.

### Acknowledgments

> **Placeholder: Acknowledgments will be added prior to submission, including funding sources, computational resources, and colleague contributions.**

---

## References

[1] W. M. McKeeman, "Peephole optimization," Communications of the ACM, vol. 8, no. 7, pp. 443–444, 1965.

[2] A. S. Tanenbaum, H. van Staveren, and J. W. Stevenson, "Using peephole optimization on intermediate code," ACM Transactions on Programming Languages and Systems, vol. 4, no. 1, pp. 21–36, 1982.

[3] H. Massalin, "Superoptimizer: A look at the smallest program," Proc. ASPLOS, pp. 122–126, 1987.

[4] A. Barenco et al., "Elementary gates for quantum computation," Physical Review A, vol. 52, no. 5, pp. 3457–3488, 1995. arXiv:quant-ph/9503016

[5] M. A. Nielsen and I. L. Chuang, Quantum Computation and Quantum Information, Cambridge University Press, 2010.

[6] D. Maslov, G. W. Dueck, and D. M. Miller, "Techniques for the synthesis of reversible Toffoli networks," ACM Transactions on Design Automation of Electronic Systems, vol. 12, no. 4, art. 42, 2008.

[7] M. Amy, D. Maslov, M. Mosca, and M. Roetteler, "A meet-in-the-middle algorithm for fast synthesis of depth-optimal quantum circuits," IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems, vol. 32, no. 6, pp. 818–830, 2013. arXiv:1206.07563

[8] V. Kliuchnikov, D. Maslov, and M. Mosca, "Asymptotically optimal approximation of single qubit unitaries by Clifford and T circuits using a constant number of ancillary qubits," Physical Review Letters, vol. 110, no. 19, 190502, 2013. arXiv:1212.0822

[9] M. Amy and M. Mosca, "Polynomial-time T-depth optimization of Clifford+T circuits via matroid partitioning," IEEE Transactions on Information Theory, vol. 65, no. 10, pp. 6271–6283, 2019. arXiv:1606.02729

[10] R. Duncan, A. Kissinger, S. Perdrix, and J. van de Wetering, "Graph-theoretic simplification of quantum circuits with the ZX-calculus," Quantum, vol. 4, 279, 2020. arXiv:1902.03178

[11] N. de Beaudrap, A. Kissinger, and J. van de Wetering, "Circuit extraction for ZX-diagrams can be #P-hard," Proc. ICALP, 2022. arXiv:2202.09194

[12] D. Janzing, P. Wocjan, and T. Beth, "Non-identity-check is QMA-complete," International Journal of Quantum Information, vol. 1, no. 4, pp. 507–518, 2003. arXiv:quant-ph/0306054

[13] D. Gottesman, "Stabilizer codes and quantum error correction," Ph.D. thesis, California Institute of Technology, 1997. arXiv:quant-ph/9705052

[14] S. Aaronson and D. Gottesman, "Improved simulation of stabilizer circuits," Physical Review A, vol. 70, no. 5, 052328, 2004. arXiv:quant-ph/0406196

[15] C. M. Dawson and M. A. Nielsen, "The Solovay-Kitaev algorithm," Quantum Information and Computation, vol. 6, no. 1, pp. 81–95, 2006. arXiv:quant-ph/0505030

[16] A. W. Harrow and A. Montanaro, "Quantum computational supremacy," Nature, vol. 549, pp. 188–196, 2017. arXiv:1809.07442

[17] R. G. Downey and M. R. Fellows, Fundamentals of Parameterized Complexity, Springer, 2013.

[18] M. A. Nielsen, "A geometric approach to quantum circuit lower bounds," arXiv:quant-ph/0502070, 2005.

[19] S. Shende, S. S. Bullock, and I. L. Markov, "Synthesis of quantum-logic circuits," IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems, vol. 25, no. 6, pp. 1000–1010, 2006. arXiv:quant-ph/0406176

[20] E. Bernstein and U. Vazirani, "Quantum complexity theory," SIAM Journal on Computing, vol. 26, no. 5, pp. 1411–1473, 1997.

[21] E. Farhi, J. Goldstone, and S. Gutmann, "A quantum approximate optimization algorithm," arXiv:1411.4028, 2014.

[22] A. Peruzzo et al., "A variational eigenvalue solver on a photonic quantum processor," Nature Communications, vol. 5, art. 4213, 2014. arXiv:1304.3061

[23] L. K. Grover, "A fast quantum mechanical algorithm for database search," Proc. STOC, pp. 212–219, 1996. arXiv:quant-ph/9605043

[24] J. Romero et al., "Strategies for quantum computing molecular energies using the unitary coupled cluster ansatz," Quantum Science and Technology, vol. 4, 014008, 2019. arXiv:1701.02691

[25] S. A. Cuccaro, T. G. Draper, S. A. Kutin, and D. P. Moulton, "A new quantum ripple-carry addition circuit," arXiv:quant-ph/0410184, 2004.

[26] D. Shepherd and M. J. Bremner, "Temporally unstructured quantum computation," Proceedings of the Royal Society A, vol. 475, no. 2225, 20180527, 2019. arXiv:1807.04084

[27] Qiskit Contributors, Qiskit: An Open-source Framework for Quantum Computing, Zenodo, 2024. DOI: 10.5281/zenodo.2562110

[28] Cirq Contributors, Cirq: A Python library for NISQ circuits, Google Quantum AI, 2023.

[29] P. Sivarajah et al., "t|ket>: A retargetable compiler for NISQ devices," Quantum Science and Technology, vol. 6, no. 1, 014003, 2020. arXiv:2003.10611

[30] A. G. Fowler, M. Mariantoni, J. M. Martinis, and A. N. Cleland, "Surface codes: Towards practical large-scale quantum computation," Physical Review A, vol. 86, 032324, 2012. arXiv:1208.0928

[31] F. G. S. L. Brandao, A. W. Harrow, and M. Horodecki, "Local random quantum circuits are approximate polynomial-designs," Communications in Mathematical Physics, vol. 346, pp. 397–434, 2016. arXiv:1208.0692

[32] S. Yamashita et al., "Fast equivalence checking of quantum circuits," IEICE Transactions on Fundamentals, vol. E94-A, no. 1, pp. 251–258, 2011.

[33] R. Iten et al., "Exact and practical pattern matching for quantum circuit optimization," ACM Transactions on Quantum Computing, vol. 3, no. 1, pp. 1–44, 2022. arXiv:1909.09119

[34] M. Xu et al., "Quartz: Superoptimization of quantum circuits," Proceedings of the ACM on Programming Languages, vol. 6, no. PLDI, pp. 625–650, 2022.

[35] J. Pointing et al., "Quanto: Optimizing quantum circuits with automatic generation of circuit identities," Quantum Science and Technology, vol. 9, no. 3, 035045, 2024.

[36] Z. Li et al., "Quarl: A learning-based quantum circuit optimizer," Proceedings of the ACM on Programming Languages, vol. 8, no. OOPSLA2, pp. 1570–1598, 2024. arXiv:2307.10120

[37] F. J. R. Ruiz et al., "Quantum circuit optimization with AlphaTensor," Nature Machine Intelligence, vol. 7, no. 3, pp. 406–419, 2025. arXiv:2402.14396

[38] J. Liu, L. Bello, and H. Zhou, "Relaxed peephole optimization," Proc. IEEE/ACM CGO, pp. 145–156, 2021. arXiv:2012.07711

[39] J. Riu et al., "Reinforcement learning based quantum circuit optimization via ZX-calculus," Quantum, vol. 9, 1758, 2025. arXiv:2312.11597

[40] J. Merilehto, "A 200-line Python micro-benchmark suite for NISQ circuit compilers," arXiv:2509.16205, 2025.

[41] N. Quetschlich, L. Burgholzer, and R. Wille, "MQT Bench: Benchmarking software and design automation tools for quantum computing," Quantum Science and Technology, vol. 8, no. 3, 035027, 2023. arXiv:2204.13719

[42] A. Li, S. Stein, S. Krishnamoorthy, and J. Ang, "QASMBench: A low-level QASM benchmark suite for NISQ evaluation and simulation," ACM Transactions on Quantum Computing, vol. 4, no. 1, pp. 1–26, 2022. arXiv:2005.13018

[43] Y. Nam et al., "Automated optimization of large quantum circuits with continuous parameters," npj Quantum Information, vol. 4, art. 23, 2018. arXiv:1710.07345

[44] S. Bravyi, R. Shaydulin, S. Hu, and D. Maslov, "Clifford circuit optimization with templates and symbolic Pauli gates," Quantum, vol. 5, art. 580, 2021. arXiv:2105.02291

[45] K. Hietala, R. Rand, S.-H. Hung, X. Wu, and M. Hicks, "A verified optimizer for quantum circuits," Proceedings of the ACM on Programming Languages, vol. 5, no. POPL, pp. 1–29, 2021. arXiv:1912.02250

[46] G. Yang, P. Raun, R. Tao, and R. Gu, "Equality saturation for quantum circuit optimization," Proceedings of the ACM on Programming Languages, vol. 10, no. PLDI, 2026. DOI: 10.1145/3808254

[47] Y. Huang et al., "SSR: A swapping-sweeping-and-rewriting optimizer for quantum circuit transformation," arXiv:2503.03227, 2025.
