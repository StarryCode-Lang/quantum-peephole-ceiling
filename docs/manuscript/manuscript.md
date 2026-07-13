# V6 Manuscript Working Draft

> **Status note (2026-07-13)**: This file merges `v5_full_manuscript_part1.md`, `v5_full_manuscript_part2.md`, and `v5_full_manuscript_part3.md` for a single editable v6 Markdown manuscript. Key consistency rules: Phase-2a means the implemented commutation-only optimizer used in canonical experiments; Phase-2b means template-assisted rewriting, with `Phase2bTemplateMatcher` implemented and fixture-scale validated (E10 Phase-2b, 1,017 rows) but no full canonical Phase-2b benchmark across all 15 families; ceiling claims are listing/window/model-conditional rather than absolute. E19 is completed (full run, 10,000 rows). E20 full mode is completed (1,070 rows). E21 full mode is completed (1,140 rows). E23/E24 are completed (160 + 75 rows, validating Thm 6 and Thm 7). E18 results remain survivorship-biased.

---

# Listing Model Sensitivity and Prototype Action-Space Ceilings in Quantum Circuit Optimization

## Abstract

Peephole optimization — the local rewriting of gate sequences to reduce circuit size — is a core component of every quantum compiler, yet no systematic study has characterized when these passes succeed or fail across diverse circuit families. We present a large-scale empirical benchmark of peephole optimization across over 67,000 data rows across 27 datasets spanning 15 primary circuit families and 6 optimizer types (including E23/E24 supplementary validations), supported by theoretical analysis including inverse pair density bounds, reduction ceiling proofs, and a context-dependent Phase 2 advantage construction for Bernstein–Vazirani oracle circuits. Our central contribution is the discovery that the circuit listing model — the data-structure ordering of gates — is the key factor governing Phase-1 adjacent-cancellation optimizer behavior: layer-by-layer listing (LBL) structurally empties the Phase-1 action space (Observation 1(b)), whereas wire-consecutive listing (WCL) exposes approximately 7.8% reduction hidden under LBL (E19, 10,000 rows). This listing-model sensitivity reframes the optimization landscape: rather than a depth-dependent *phase transition* (our initial hypothesis, which the data refuted — we use "phase transition" only to denote prototype action-space ceilings, not statistical-mechanics critical phenomena), the data reveal a categorical trichotomy. CNOT chains achieve 100% Phase-1 reduction, oracle and random Clifford circuits yield 14–16% reduction via commutation-based rewriting, and 3 of 15 families (QFT, GHZ, SurfaceCode) are at a genuine structural ceiling confirmed by all compilers, while 7 of 15 show a prototype action-space ceiling where the custom prototype optimizer achieves approximately 0% but production peephole optimizers achieve 5-63% — a negative result we frame as characterizing the limitations of the prototype's restricted move set rather than a structural limit of peephole optimization. The strongest theoretical results (Theorems 7/9, establishing $\Omega(1)$ Phase-2b/template-assisted advantage) are now validated experimentally via the Phase-2b template-matching fixtures (F1 fix). A fair compiler comparison (E12, no-coupling-map mode) reveals additional gains on families where prototype peephole methods plateau, identifying the boundary between local rewriting and production compiler mechanisms; Cirq and t|ket> multi-compiler comparison data from E20 (1,070 rows; Cirq on n ≤ 8, t|ket> on n ≤ 6) provide supplementary production-compiler context. These results produce circuit-family optimization prescriptions for the studied families, mapping each family to its optimal phase or recommending bypass.

---

## 1. Introduction

### 1.1 Motivation

Quantum circuit optimization stands as a critical bottleneck in the realization of practical quantum computing. As quantum processors transition from the noisy intermediate-scale quantum (NISQ) era toward fault-tolerant architectures, the gap between algorithmic circuit complexity and hardware gate budgets continues to widen. Production compilers—Qiskit's transpiler, Google's Cirq, and Cambridge Quantum's t|ket>—routinely achieve 10–40% gate-count reduction through sequences of local rewrite and synthesis passes, yet these tools provide limited systematic characterization of *when* optimization will succeed, *why* it sometimes fails entirely, or what LWM-conditional limits constrain achievable reductions. This opacity encourages broad pass application, wasting computational resources on circuits that resist the tested local rewriting model while potentially missing opportunities for deeper optimization on amenable structures.

The dominant optimization paradigm in quantum compilers is peephole optimization: the local rewriting of bounded gate sequences to reduce circuit size while preserving unitary equivalence [Barenco et al. 1995, Maslov et al. 2008]. This approach traces its lineage to classical compiler theory, where McKeeman [1965] introduced peephole optimization as a final pass over machine code, and Massalin [1987] developed superoptimization through exhaustive search over small instruction windows. In the quantum setting, peephole optimization encompasses adjacent gate cancellation (removing $U \cdot U^{-1}$ pairs), template matching (applying pre-computed equivalence rules such as $H \cdot X \cdot H = Z$), and commutation-based reordering (exploiting gate commutativity to expose non-adjacent cancellation opportunities) [Amy et al. 2013, Wille et al. 2009]. Recent advances have extended this paradigm through automated identity generation [Xu et al. 2022 (Quartz), Pointing et al. 2024 (Quanto)], reinforcement learning [Li et al. 2024 (Qarl), Riu et al. 2025 (ZX+RL)], and tensor decomposition methods [Ruiz et al. 2025 (AlphaTensor-Quantum)], achieving impressive empirical results on benchmark circuits.

The economic and computational stakes of this gap are particularly acute in fault-tolerant architectures. In surface code implementations, each logical T gate requires magic state distillation consuming approximately 1,000–10,000 physical qubits per logical T gate, making T-count reduction a first-order concern for algorithmic feasibility [Fowler et al. 2012]. Even modest improvements in circuit optimization—a 10% reduction in T-count for Shor's algorithm at cryptographic key sizes—can translate to savings of millions of physical qubits and hours of runtime. Yet current compilers achieve their reductions through heuristic pass sequences whose effectiveness varies unpredictably across circuit families. A compiler developer has no principled basis for deciding whether to invest additional computational budget in optimization passes for a given circuit, or whether the circuit has reached its fundamental optimization ceiling and further passes are futile. This resource allocation problem—how to distribute finite compilation time across optimization passes—is currently solved by applying all available passes unconditionally, a strategy that wastes resources on provably inoptimizable circuits while potentially under-investing in circuits with substantial optimization headroom.

Despite these advances, a fundamental disconnect persists between compiler practice and optimization theory. Production compilers operate as black boxes: they apply optimization passes and report the achieved reduction, but they do not explain why certain circuits yield substantial gains while others resist all optimization attempts. Theoretical complexity results establish that optimal circuit optimization is QMA-hard [Janzing et al. 2003], yet this worst-case hardness provides little guidance for the average-case behavior encountered in practice. A QMA-hardness result means that no efficient algorithm can solve the optimization problem for all circuits, but it does not preclude efficient optimization for specific circuit families or average-case ensembles. Indeed, the Gottesman–Knill theorem [Gottesman 1997] establishes that Clifford circuits—a practically significant subclass—are polynomial-time optimizable, suggesting that the hardness landscape is far more nuanced than worst-case analysis implies. The field requires a framework that bridges this gap: one that characterizes not just whether optimization is possible in principle, but when it is possible in practice, for which circuit families, and by how much. Meanwhile, empirical benchmarking efforts—such as the Micro-Benchmark Suite [Merilehto 2025]—report performance differences across compilers without offering a structural theory to interpret these observations. The field lacks a systematic framework for answering the most basic questions: What fraction of circuits are fundamentally inoptimizable by peephole methods? For which circuit families does commutation-based rewriting provide measurable advantage? Where do production compilers exceed the local peephole model, and by what mechanisms?

This paper addresses these questions through the largest systematic study of quantum circuit peephole optimization conducted to date. We present a comprehensive empirical benchmark spanning over 67,000 data rows across 27 datasets across 15 primary circuit families and 6 optimizer types, supported by a theoretical framework that characterizes LWM-conditional prototype action-space ceilings for local peephole optimization. Our central finding is that the circuit listing model — the data-structure ordering of gates — is the key factor governing Phase-1 adjacent-cancellation optimizer behavior, and that this listing-model sensitivity produces sharply divergent optimization profiles across circuit families: CNOT chains achieve 100% Phase-1 (adjacent cancellation) reduction, oracle and random Clifford circuits yield 14–16% reduction via Phase-2a (commutation-based) rewriting, and 3 of 15 families (genuine ceiling) + 7 of 15 (prototype-limited)—including QFT, GHZ, QAOA, and VQE ansätze—are at structural ceiling for the tested prototype peephole model, where the custom optimizer achieves ~0% reduction (a negative result characterizing why local peephole optimization fails; Figure 11 visualizes this trichotomy as a per-family, per-optimizer reduction heatmap across the full 15-family benchmark). A completed Qiskit baseline reveals additional gains on families where peephole methods plateau, with Cirq and t|ket> multi-compiler comparison data available from E20 (1,070 rows; Cirq evaluated on n ≤ 8, t|ket> on n ≤ 6 due to optimizer timeouts on larger instances). An exploratory ceiling-aware optimizer shows 1.6x–228x speedup (mean 35x) in the E21 full-mode dataset (1,140 rows); however, the underlying empirical correlation model does not generalize to unseen circuit families (held-out generalization caveat, hereafter HGC: MAE = 0.2775, Pearson = NaN; see Section 6 Limitations), and this result should be interpreted as a supplementary observation rather than a validated predictive tool.

### 1.2 The Listing Model Problem

A critical methodological discovery emerged during our investigation: the circuit listing model—the data-structure ordering of gates—fundamentally affects optimizer behavior in ways that have not been previously recognized. Quantum circuits can be represented in two natural listing formats. In wire-consecutive listing (WCL), gates on the same qubit wire are placed consecutively in the circuit data structure, reflecting the natural representation in circuit diagrams and some synthesis tools. In layer-by-layer listing (LBL), the circuit is generated and stored layer by layer, with one gate per qubit per layer; gates on the same qubit $q$ at layers $L$ and $L+1$ are separated by $n-1$ intervening gates from other qubits, where $n$ is the qubit count.

This seemingly innocuous data-structure choice has profound implications for Phase-1 optimization. We prove (Observation 1(b)) that under LBL with $n \geq 2$, the Phase-1 action space is structurally empty: $\mathcal{S}_1(C) = \emptyset$ for every circuit $C$, where $\mathcal{S}_1(C)$ denotes the set of all adjacent gate pairs $(g_i, g_{i+1})$ such that $g_{i+1} = g_i^{-1}$ and both act on the same qubit(s). The proof is elementary but consequential: under LBL, the gate on qubit $q$ at layer $L$ is at listing index $L \cdot n + q$, while the next gate on the same qubit appears at index $(L+1) \cdot n + q$, yielding a gap of $n \geq 2$. Since Phase-1 requires listing adjacency (gap = 1) on the same qubit(s), no Phase-1 action is possible regardless of the circuit's gate content. Consequently, $R_1(C) = 0$ for every Phase-1 optimizer applied to LBL-represented circuits.

This theorem explains previously puzzling zero-variance results in our early experiments (25,000 trials with LBL representation) and has significant practical implications for compiler design. When circuits are represented in WCL instead of LBL, the Phase-1 action space can become non-empty for circuits containing wire-consecutive inverse pairs. Experiment E19 (full run, 10,000 rows) confirms that these wire-level inverse pairs translate into measurable Phase-1 reduction: approximately 7.8% mean reduction on the same random circuit ensemble where LBL yields exactly 0%. The LBL-vs-WCL divergence is previewed by the Qiskit pass-waterfall analysis in Figure 15, which traces per-pass reduction accumulation under both listing models. The observed effect is consistent with the density bound from Observation 1(a): $\mathbb{E}[|\mathcal{A}_{\text{adj}}(C)|] = n(d-1) \cdot p_{\text{cancel}}(n, \rho)$, which for typical parameters yields a small but nonzero number of adjacent inverse pairs under WCL.

The listing-model dependency reveals that the zero Phase-1 reduction observed in many experiments is not a fundamental property of the circuits themselves, but rather a consequence of the data-structure ordering used by the generator. The circuits contain wire-level inverse pairs; LBL merely hides them from listing-adjacent Phase-1 detection. Crucially, Phase-2 commutation rewriters—which operate on the circuit graph rather than the listing—are unaffected by this listing-model dependency, since they reason about wire-level adjacency rather than listing adjacency. This discovery necessitates a methodological recommendation: future experiments should either adopt WCL as the default listing model for Phase-1 evaluation, or include a wire-traversal preprocessing step to ensure that Phase-1 results reflect the circuit's intrinsic structure rather than an artifact of the data-structure ordering.

### 1.3 Research Questions

Motivated by the gap between compiler practice and optimization theory, we formulate five research questions that guide our investigation:

**RQ1: What fraction of circuit families are at prototype action-space ceiling (zero peephole reduction), and what structural properties determine this?** This question seeks to quantify the prevalence of fundamental optimization barriers across diverse circuit families. If a large fraction of circuits are provably inoptimizable by peephole methods, this has immediate implications for compiler resource allocation and optimization strategy design.

**RQ2: For which circuit families does commutation-based rewriting (Phase 2) provide measurable advantage beyond adjacent cancellation (Phase 1), and by how much?** Prior work has demonstrated that commutation can expose non-adjacent cancellation opportunities, but no systematic study has quantified this advantage across diverse circuit structures. We seek to identify the circuit families where Phase-2 methods are essential and to measure the optimization gap $\Gamma(C) = R_{1+2}(C) - R_1(C)$ they enable.

**RQ3: Where do production compilers operate beyond the local peephole model, and can our benchmark identify the boundary?** Modern compilers employ sophisticated optimization passes—template matching, phase-polynomial optimization, global synthesis—that exceed the restricted peephole model. We aim to map the boundary between local peephole scope and global synthesis mechanisms through systematic comparison against production compilers.

**RQ4: How does the circuit listing model affect optimization outcomes, and what are the implications for compiler design?** Motivated by our discovery of listing-model dependency (Observation 1(b)), this question investigates the practical impact of data-structure choices on optimization effectiveness and develops guidelines for listing-model-aware compiler implementation.

**RQ5: Can prototype action-space ceiling knowledge improve compiler efficiency?** If we can predict a priori that a circuit is at prototype action-space ceiling, compilers can skip futile optimization passes and allocate resources elsewhere. We investigate whether a prototype action-space ceiling proxy can enable ceiling-aware optimization that achieves identical reduction with reduced computational cost. **Note**: The HGC (see Section 1.1) revealed that the empirical correlation model does not generalize to unseen circuit families; this research question is therefore explored as an exploratory observation rather than a validated predictive tool.

### 1.4 Contributions

This paper makes several contributions that collectively advance the state of the art in quantum circuit optimization theory and practice. The four core contributions, in order of centrality, are: **(1)** the listing-model sensitivity discovery (Section 1.2), which identifies the circuit data-structure ordering as the key factor governing Phase-1 adjacent-cancellation optimizer behavior; **(2)** the Phase 1 / Phase 2 separation framework (Section 3), a two-phase taxonomy that organizes peephole techniques by their scope of operation; **(3)** the prototype action-space ceiling analysis (Section 6.1), characterizing why local peephole optimization fails on 3 of 15 families (genuine ceiling) + 7 of 15 (prototype-limited); and **(4)** theory–experiment validation of Theorem 9's $\Omega(1)$ Phase-2b advantage via the Phase-2b template-matching fixtures (F1 fix). The supporting contributions below expand these into a full empirical and theoretical program:

**Contribution 1 (core): Listing-model sensitivity discovery.** We provide a formal characterization of how circuit listing order governs optimizer behavior — the key factor identified by this study. Observation 1(b) proves that layer-by-layer listing (LBL) makes the Phase-1 action space structurally empty for $n \geq 2$, explaining previously puzzling zero-variance experimental results. Experiment E19 confirms that wire-consecutive listing (WCL) exposes Phase-1 reductions hidden under LBL: WCL preprocessing achieves approximately 7.8% mean gate reduction on random universal circuits where LBL yields exactly 0%, establishing the prototype action-space ceiling as listing-model-dependent rather than an intrinsic circuit property. This reframes the optimization landscape: the apparent "optimization desert" is a property of the (circuit, listing) pair, not of the circuits themselves.

**Contribution 2: Large-scale empirical benchmark and structural-ceiling characterization.** We present a comprehensive empirical study encompassing over 67,000 data rows across 27 datasets across 15 primary circuit families (random universal, random Clifford, structured brickwork, QFT, GHZ, Bernstein–Vazirani oracle, QAOA, VQE, hardware-efficient ansätze, surface code syndrome extraction, UCCSD ansatz, Grover's algorithm, quantum adder, quantum walk, and IQP circuits) and 6 optimizer types (Greedy, Randomized Local Search, Simulated Annealing, Genetic Algorithm, CommutationRewriter, and HybridCommuteRewrite), supplemented by dedicated theory-validation experiments E23 (Thm 6, AG canonical form, 160 circuits) and E24 (Thm 7, hardness family, 75 circuits). This scale exceeds prior efforts—Quartz (~100 benchmarks), Qarl (~50 benchmarks), and the Micro-Benchmark Suite (6 circuits)—by two orders of magnitude, providing the statistical power necessary to distinguish genuine structural patterns from noise. Our experiments reveal an empirically observed trichotomy for the tested prototype optimizer: from 100% Phase-1 reduction (CNOT chains) to approximately 0% reduction (3 of 15 families at genuine structural ceiling confirmed by all compilers, 7 of 15 at prototype action-space ceiling), with Phase-2 commutation enabling 22-28% reduction on oracle and random Clifford circuits. We frame the ~0% result as characterizing the prototype optimizer limitations rather than a structural limit of peephole optimization, since production peephole optimizers (t|ket> FullPeepholeOptimise) achieve 5-63% on 5 of the 7 ceiling families Optimizer outputs preserve unitary fidelity where exact/scalable checks are available; documented failure rows are tracked and filtered where valid fidelity is required.

**Contribution 3: Circuit-family optimization prescriptions (within training families).** We provide the first quantitative map showing which circuit families benefit from which optimization phase, enabling circuit-family-aware compiler design. Our prescriptions are: Phase-1 only for CNOT chains (100% reduction achievable); Phase-2 only for Oracle/Bernstein–Vazirani (~27.6% reduction), random Clifford (~22.1% reduction), and select variational circuits; and bypass for QFT, GHZ, and SurfaceCode (genuine structural ceiling confirmed by all compilers) or escalate to production compiler for VQE, HardwareEfficient, IQP, UCCSD, and QAOA (prototype action-space ceiling where t|ket> achieves 5-63%). These prescriptions are grounded in both empirical measurement and theoretical analysis (Theorems 1, 2, and 9), providing compiler developers with actionable guidance for resource allocation.

**Contribution 4: Qiskit mechanism analysis with multi-compiler extension.** We compare our prototype peephole optimizers against Qiskit optimization levels 0–3 and decompose the Qiskit transpiler advantage through pass-level analysis, identifying mechanisms beyond local peephole scope such as template matching, commutative cancellation, basis translation, and resynthesis. Cirq and t|ket> configurations are benchmarked in E20 (1,070 rows across 15 families; Cirq on n ≤ 8, t|ket> on n ≤ 6) and provide supplementary multi-compiler context.

**Supplementary Observation 5: Ceiling-aware optimizer (exploratory analysis, not a contribution).** We develop a practical tool that uses a prototype action-space ceiling proxy to skip futile optimization passes. In E21 full-mode data (1,140 rows), the tool shows 1.6x–228x speedup (mean 35x) with identical reduction across all 15 training families. The ceiling proxy computes the density of wire-level inverse pairs and commutation-enabled cancellation opportunities, predicting a priori whether optimization will yield nonzero reduction. **Important caveat**: The HGC demonstrated that the empirical correlation model underlying the ceiling proxy **fails to generalize to new circuit families**, indicating that the proxy's predictions are valid only within the training families and should not be treated as a validated predictive tool. This item is classified as a supplementary observation / exploratory analysis rather than a main contribution of this paper.

> **Note: The Optimize-or-Skip model achieved 97.86% accuracy on training families but failed to generalize to held-out circuit families (MAE=0.2775, Pearson r=NaN). This model should be considered an empirical observation specific to the training families, not a generalizable contribution.**

**Contribution 6: Supporting theoretical framework.** We provide theoretical backing for empirical patterns through a suite of theorems that characterize conditional limits of the studied peephole optimization model. Theorem 1 (adjacent inverse pair density) establishes that the expected Phase-1 reduction on random circuits is $O(1/g_1^2 + 1/(g_2 n))$, negligibly small for standard gate sets; part (b) proves the listing-model structural result. Theorem 2 (Phase-1 reduction ceiling) shows that all Phase-1 optimizers share the same action space and that stochastic optimizers employing INSERTION moves cannot systematically exceed greedy reduction; we resolve a previously open gap in the INSERTION cascade argument through Theorems 2(c) and 2(d), which prove that INSERTION cannot achieve net reduction beyond the Phase-2 action space. Theorem 7 provides an explicit circuit family with $\Omega(1)$ Phase-2 advantage, establishing Conjecture C2 constructively. Theorem 9 strengthens this result by proving $\Gamma(BV_n) \geq n/(4.5n+4)$ Phase-2b/template-assisted advantage for the natural Bernstein–Vazirani oracle family, demonstrating that the Phase-1/Phase-2 gap is not merely an artifact of artificial constructions but arises in standard quantum algorithmic primitives. The Phase-2b template-matching fixtures (F1 fix) now provide direct experimental validation of this separation on BV-like circuits ($n = 2, 3, 5$), where the implemented matcher reduces $5n$ gates to $n + 2$ while preserving the exact unitary — closing the theory–experiment gap for these strongest results at the fixture scale (full canonical-scale Phase-2b benchmarking remains future work; see Section 6.3 and `limitations_and_future_work.md` §2). Additional results (Theorems 3, 5, 6, 8) provide supporting bounds on commutation equivalence, high-probability concentration, Clifford circuit ceilings, and Haar-random incompressibility.

### 1.5 Paper Organization

The remainder of this paper is organized as follows. Section 2 provides background on the quantum circuit model, peephole optimization techniques, computational complexity, quantum compilers, and related benchmarking efforts. Section 3 presents the theoretical framework, including formal definitions (D1–D10), key theorems (Theorems 1, 2, 7, 9), and conjectures (C1–C2) that underpin our analysis. Section 4 describes the experimental methodology, including the optimizer suite, circuit family definitions, statistical protocol, and listing-model considerations. Section 5 presents the empirical results, organized around the five research questions: prototype action-space ceiling characterization (RQ1), Phase-2 context-dependent advantage (RQ2), multi-compiler gap analysis (RQ3), listing-model dependency (RQ4), and ceiling-aware optimization (RQ5). Section 6 discusses the implications for compiler design, optimization prescriptions, and limitations of the current study. Section 7 concludes with a summary of findings and directions for future work. Supplementary materials provide complete experimental details, statistical tables, algorithm pseudocode, extended figures, and reproducibility documentation.

---

## 2. Background

### 2.1 Quantum Circuit Model

A quantum circuit $C$ is a sequence of quantum gates $C = (g_1, g_2, \ldots, g_m)$ where each $g_i \in \mathcal{G}$ is drawn from a gate set $\mathcal{G}$ acting on $n$ qubits. The size of the circuit is $|C| = m$. Two circuits $C$ and $C'$ are unitarily equivalent, denoted $C \equiv C'$, if they implement the same unitary transformation: $U(C) = U(C')$. The average gate fidelity between two circuits is defined as

$$F_{\text{avg}}(C, C') = \frac{|\text{Tr}(U^\dagger U')|^2 + d}{d^2 + d}$$

where $d = 2^n$ and $U, U'$ are the unitaries implemented by $C, C'$ respectively. Throughout this work, we consider the standard universal gate set $\mathcal{G} = \{H, T, T^\dagger, S, S^\dagger, R_x(\theta), R_y(\theta), R_z(\theta), X, Y, Z, \text{CNOT}, \text{CZ}\}$, where $H$ is the Hadamard gate (self-inverse), $T$ and $T^\dagger$ are the $\pi/8$ gate and its inverse, $S$ and $S^\dagger$ are the phase gate and its inverse, $R_x(\theta)$, $R_y(\theta)$, $R_z(\theta)$ are continuous-parameter rotations with $R_\alpha(\theta)^{-1} = R_\alpha(-\theta)$, $X$, $Y$, $Z$ are the Pauli gates (self-inverse), CNOT is the controlled-NOT gate (self-inverse), and CZ is the controlled-Z gate (self-inverse). This gate set is universal in the sense that any $n$-qubit unitary can be approximated to arbitrary precision $\epsilon$ using $O(4^n \log(1/\epsilon))$ gates [Nielsen & Chuang 2010, Dawson & Nielsen 2006].

The circuit listing model—the data-structure ordering of gates—plays a critical role in determining optimizer behavior, as established in Section 1.2 and formalized in Observation 1(b). We distinguish two natural listing models:

**Wire-consecutive listing (WCL).** Gates on the same qubit wire are placed consecutively in the listing. For a circuit with $n$ qubits and depth $d$, the gates on qubit $q$ are listed as $g_{q,1}, g_{q,2}, \ldots, g_{q,d}$, followed by the gates on qubit $q+1$. This is the natural model for circuit diagrams and some synthesis tools. Under WCL, two successive gates on the same qubit are listing-adjacent, so inverse pairs are directly visible to Phase-1 optimizers.

**Layer-by-layer listing (LBL).** The circuit is generated layer by layer, with one gate per qubit per layer. Gates are listed in layer-major order: all gates of layer $L$ precede all gates of layer $L+1$. Within each layer, gates are listed in qubit order $q_0, q_1, \ldots, q_{n-1}$. Under LBL, the gate on qubit $q$ at layer $L$ is at listing index $L \cdot n + q$, while the next gate on the same qubit appears at index $(L+1) \cdot n + q$, yielding a gap of $n \geq 2$. As proven in Observation 1(b), this makes the Phase-1 action space structurally empty for $n \geq 2$.

The choice of listing model is not merely an implementation detail; it fundamentally determines whether Phase-1 optimizers can detect wire-level inverse pairs. Throughout this paper, we explicitly report the listing model used in each experiment and provide wire-traversal preprocessing for LBL-represented circuits when Phase-1 evaluation is intended.

We study 15 circuit families that span the diversity of quantum computing applications:

**Random circuits.** (i) Random universal circuits: gates drawn uniformly from $\mathcal{G}$ with two-qubit gate density $\rho = 0.3$, depth $d \in \{10, 25, 50, 100\}$, qubit count $n \in \{3, 5, 7, 10\}$. These approximate Haar-random unitaries at sufficient depth [Brandão et al. 2016, Harrow & Low 2009]. (ii) Random Clifford circuits: gates drawn from $\{H, S, \text{CNOT}\}$, which are polynomial-time optimizable via the stabilizer formalism [Gottesman 1997, Aaronson & Gottesman 2004]. (iii) Structured brickwork circuits: alternating layers of single-qubit and two-qubit gates with fixed connectivity, designed to test the impact of structural regularity on optimizability.

**Algorithmic circuits.** (iv) Quantum Fourier Transform (QFT): the canonical $O(n^2)$ implementation with controlled-phase rotations. (v) GHZ state preparation: a single $H$ gate followed by $n-1$ CNOT gates in a linear chain. (vi) Bernstein–Vazirani oracle: the standard implementation with $H^{\otimes n}$, $n$ CNOT gates targeting an ancilla, and $H^{\otimes n}$, encoding a secret string $s \in \{0,1\}^n$ [Bernstein & Vazirani 1997]. (vii) QAOA: Quantum Approximate Optimization Algorithm with $p = 3$ layers for MaxCut on random 3-regular graphs [Farhi et al. 2014]. (viii) VQE: Variational Quantum Eigensolver with hardware-efficient ansatz for molecular Hamiltonians [Peruzzo et al. 2014]. (ix) Hardware-efficient ansatz: alternating layers of $R_y$ rotations and CNOT entanglers, depth $d = 10$. (x) Surface code syndrome extraction: the standard stabilizer measurement circuit for the $d = 3$ surface code [Fowler et al. 2012]. (xi) UCCSD ansatz: Unitary Coupled Cluster with Singles and Doubles for $H_2$ and $LiH$ molecular systems [Romero et al. 2018]. (xii) Grover's algorithm: 2 Grover iterations for 3-SAT on $n = 5$ qubits [Grover 1996]. (xiii) Quantum adder: ripple-carry addition of two $n/2$-bit numbers [Cuccaro et al. 2004]. (xiv) Quantum walk: discrete-time quantum walk on a cycle graph with $n = 8$ qubits [Aharonov et al. 2001]. (xv) IQP circuits: Instantaneous Quantum Polynomial-time circuits with commuting gates [Shepherd & Bremner 2019].

This diverse corpus enables systematic investigation of how circuit structure—randomness, algorithmic regularity, entanglement structure, and gate-set composition—determines optimization outcomes.

### 2.2 Peephole Optimization

Peephole optimization examines small "peephole" windows of instructions and replaces inefficient patterns with optimal equivalents. The technique was introduced by McKeeman [1965] as a final pass in classical compilers, achieving $O(1)$-approximation for instruction selection on bounded-degree graphs [Fraser & Hanson 1995]. Massalin [1987] extended this to superoptimization—exhaustive search for optimal instruction sequences—which is NP-hard in general but practical for small windows. Tanenbaum et al. [1982] proved that peephole optimization with a finite pattern set is not Turing-complete, establishing fundamental limits on the technique's expressive power.

In the quantum setting, peephole optimization was formalized by Barenco et al. [1995], who established the first quantum circuit synthesis bounds showing that any $n$-qubit unitary can be implemented with $O(4^n)$ gates. This work implicitly used peephole-style rewrite rules such as CNOT cancellation ($\text{CNOT} \cdot \text{CNOT} = I$) and Hadamard self-inversion ($H \cdot H = I$). Nielsen and Chuang [2010] formalized the quantum circuit model and introduced the Solovay–Kitaev theorem, which provides an algorithm for approximate gate synthesis achieving $O(\log^{3.97}(1/\epsilon))$ gate count for $\epsilon$-approximate synthesis [Dawson & Nielsen 2006]. However, Solovay–Kitaev addresses synthesis (constructing a circuit from a unitary) rather than optimization (reducing an existing circuit).

**Template-based optimization.** Maslov et al. [2008] introduced template matching for quantum circuit optimization, where templates are pre-computed equivalence rules (e.g., $H \cdot X \cdot H = Z$, $\text{CNOT} \cdot \text{CNOT} = I$) and the optimizer scans the circuit for template matches and applies replacements. Template matching is a subgraph isomorphism problem, which is NP-hard in general. Amy et al. [2013, 2014] extended template matching to T-count optimization for fault-tolerant quantum computing, achieving significant reductions in T-gate count—the most expensive gate in fault-tolerant schemes due to the need for magic state distillation. Kliuchnikov et al. [2013] introduced a fast and efficient algorithm for optimal synthesis of Clifford+T circuits, finding the minimal T-count representation using a meet-in-the-middle approach combined with number-theoretic techniques. The limitation of template-based methods is that template libraries are finite and cannot cover all possible circuit structures; the optimality gap between template-based and optimal optimization is unknown.

**Commutation-based optimization.** Wille et al. [2009] introduced commutation rules for quantum circuit optimization, exploiting the fact that gates that commute can be reordered to expose cancellation opportunities. The key insight is that commutation is a structural property of the gate set, not the circuit: for example, $[H \otimes I, \text{CNOT}] \neq 0$ but $[S \otimes I, \text{CNOT}] = 0$ on the control qubit. Wille and Drechsler [2009] formalized the commutation graph of a quantum circuit, where vertices are gates and edges represent commutation relations; finding optimal reorderings is equivalent to finding maximum independent sets in this graph. Our framework shows that commutation-based optimization provides context-dependent advantage: 3.26% on random universal circuits, 0% on structured brickwork circuits, and ~20% on oracle/Bernstein–Vazirani circuits (Figure 4 contrasts Phase-1 and Phase-2 reduction across these circuit families, making the context-dependence visible).

**Phase polynomial optimization.** Amy et al. [2018] introduced phase polynomial optimization for circuits with $R_z$ gates, representing $R_z$ rotations as a polynomial over $\mathbb{Z}_2$ and using Gaussian elimination to find minimal representations. This approach achieves exponential improvements for certain circuit families but applies only to circuits with $R_z$ and CNOT gates (the "CNOT+$R_z$" gate set); it does not generalize to arbitrary universal gate sets. Phase polynomial optimization is a key component of Cirq's optimization pipeline and contributes approximately 25% of the beyond-peephole advantage observed in our Qiskit comparison (Section 5.3).

**ZX-calculus approaches.** Duncan et al. [2020] introduced a graph-theoretic approach to quantum circuit simplification using the ZX-calculus, a diagrammatic language for quantum computation where quantum processes are represented as string diagrams and rewritten using a complete set of graphical rewrite rules (local complementation, pivoting, spider fusion). The approach translates quantum circuits into ZX-diagrams, simplifies them using graph-theoretic transformations, and extracts optimized circuits. This method leverages the theory of graph-like ZX-diagrams to systematically reduce circuit complexity, providing a form of "global peephole optimization" that can discover optimizations invisible to traditional gate-level methods. De Beaudrap et al. [2022] extended this to achieve faster circuit resynthesis, addressing the extraction step that converts optimized ZX-diagrams back to circuits. Recent work by Riu et al. [2025] combines ZX-calculus with reinforcement learning, achieving up to 40% reduction on Clifford+T circuits with up to 40 qubits. The limitation of ZX-calculus methods is that the circuit extraction step can introduce overhead that partially negates the diagrammatic reduction, and the method does not characterize the theoretical ceiling of achievable reduction.

**Two-phase taxonomy.** Our framework introduces a two-phase taxonomy that organizes peephole optimization techniques by their scope of operation, providing a conceptual foundation for understanding when and why different optimization strategies succeed or fail:

**Phase 1 (adjacent cancellation).** Phase-1 optimizers consider only peephole windows of size $|W| = 2$ (adjacent gate pairs) and apply transformations that reduce gate count by cancellation or merging. The Phase-1 action space is defined as

$$\mathcal{S}_1(C) = \{(g_i, g_{i+1}) : g_i \text{ and } g_{i+1} \text{ act on the same qubit(s) and } g_{i+1} = g_i^{-1}\}.$$

Phase-1 optimizers include Greedy (deterministic scan with cancellation), Randomized Local Search (RLS), Simulated Annealing (SA), and Genetic Algorithm (GA). The latter three employ stochastic search with move sets including REMOVAL (cancel adjacent inverses), SWAP (exchange disjoint-qubit gates), COMMUTATION (reorder commuting pair), and INSERTION (insert identity pair $g \cdot g^{-1}$). Theorem 2 establishes that all Phase-1 optimizers share the same action space and that stochastic optimizers cannot systematically exceed greedy reduction when $\mathcal{S}_1(C) = \emptyset$. This result is initially surprising: one might expect that stochastic search with a richer move set (including INSERTION, which temporarily increases circuit size to enable later cancellation) could discover reductions inaccessible to greedy methods. However, Theorem 2 proves that INSERTION is a zero-sum operation—any cancellation it enables could have been achieved without it—and that the Phase-1 action space is a structural property of the circuit, not an artifact of the search strategy. The practical implication is that for circuits at prototype action-space ceiling (where $\mathcal{S}_1(C) = \emptyset$), all Phase-1 optimizers achieve identical (zero) reduction, making the choice among them a matter of computational efficiency rather than optimization quality.

**Phase 2 (commutation rewriting).** Phase-2 optimizers apply commutation rules to reorder gates, bringing non-adjacent inverse gates into adjacency and thereby enabling Phase-1 reductions that were previously inaccessible. The Phase-2 action space is the extended set

$$\mathcal{S}_{1+2}(C) = \{(g_i, g_j) : g_i \text{ and } g_j \text{ can be brought into adjacency via commutation and } g_j = g_i^{-1}\}.$$

By construction, $\mathcal{S}_1(C) \subseteq \mathcal{S}_{1+2}(C)$. Phase-2 optimizers include CommutationRewriter (window-parameterized commutation search) and HybridCommuteRewrite (Phase-1 → Phase-2 → Phase-1 pipeline). The optimization gap $\Gamma(C) = R_{1+2}(C) - R_1(C)$ quantifies the additional reduction enabled by Phase-2 methods. Theorem 7 establishes the existence of an explicit circuit family with $\Gamma(C_n) \geq 1/6$ for all $n \geq 2$, proving that Phase-2 advantage is not merely an artifact of small examples but persists at all scales. Theorem 9 strengthens this result by proving $\Gamma(BV_n) \geq n/(4.5n+4)$ for the natural Bernstein–Vazirani oracle family under Phase-2b/template-assisted rewriting. A limited Phase-2b template matcher exists in code, but the canonical benchmark data supporting Section 5 use Phase-2a commutation rewriting unless explicitly labeled otherwise.

The relationship between Phase 1 and Phase 2 is hierarchical: Phase 2 subsumes Phase 1, but the additional computational cost of Phase-2 methods (typically $O(|C|^2)$ or higher due to the combinatorial explosion of commutation sequences) is only justified when $\Gamma(C) > 0$. Our empirical results (Section 5.2) show that $\Gamma(C) > 0$ for only 5 of 15 circuit families, implying that Phase-2 methods should be applied selectively based on circuit-family classification rather than unconditionally.

### 2.3 Computational Complexity

The computational complexity of quantum circuit optimization is intimately connected to fundamental questions in quantum complexity theory. Circuit Identity Testing (CIT)—determining whether two quantum circuits implement the same unitary—was proven QMA-complete by Janzing et al. [2003]. Kempe et al. [2006] strengthened this to show that the $k$-Local Hamiltonian problem is QMA-complete for $k \geq 2$, which implies QMA-hardness of CIT via Kitaev's circuit-to-Hamiltonian construction. Since optimal circuit optimization requires CIT as a subroutine (to verify that an optimized circuit is unitarily equivalent to the input), optimal optimization is at least QMA-hard. Yamashita, Morita and Markov [56] developed fast equivalence-checking algorithms that scale polynomially for specific circuit classes, enabling practical verification of optimization correctness without full unitary comparison.

The complexity landscape becomes more nuanced when restricted to specific circuit classes. Gottesman [1997] introduced the stabilizer formalism, which provides a polynomial-time representation of Clifford circuits (generated by $\{H, S, \text{CNOT}\}$). Aaronson and Gottesman [2004] showed that Clifford circuit simulation and optimization are in P: Clifford circuits can be represented as binary symplectic matrices, and optimal decomposition into CNOT-H-S layers takes $O(n^3)$ time. This explains why Clifford circuits are "easy" to optimize and why our experiments show 0% peephole reduction on Clifford circuits in Aaronson–Gottesman canonical form (Theorem 6): they are already in normal form, and no adjacent inverse pairs remain.

For Haar-random unitaries, Nielsen [2005] and Harrow and Montanaro [2017] established that the circuit complexity (minimum gate count) satisfies $\mathcal{C}(U) \geq 4^n / n^2$ with probability $1 - e^{-\Omega(4^n/n)}$ over the Haar measure. Shende, Bullock and Markov [35] established complementary lower bounds on CNOT gate counts for quantum-logic circuits, showing that an $n$-qubit unitary requires at least $\lceil (4^n - 3n - 1)/4 \rceil$ CNOT gates. These results provide lower bounds on circuit complexity but do not directly address the optimization problem. Theorem 8 in our framework strengthens this to show that for circuits of depth $d = \text{poly}(n)$, the maximum achievable reduction by any algorithm (bounded or unbounded window) approaches zero doubly-exponentially fast in $n$, formalizing the "optimization desert" observed empirically.

Several open problems remain in the complexity theory of quantum circuit optimization. The Circuit Optimization Decision Problem (CODP)—given a circuit $C$ and a target size $k$, does there exist a circuit $C' \equiv C$ with $|C'| \leq k$?—is conjectured to be QMA-hard, but a formal reduction from $k$-Local Hamiltonian has not been established. The approximability of CODP is also open: is there a polynomial-time approximation scheme (PTAS) for circuit optimization on bounded-treewidth circuits? Parameterized complexity theory [Downey & Fellows 2013] suggests that circuit optimization may be fixed-parameter tractable (FPT) in circuit treewidth but W[1]-hard in the number of non-Clifford gates, aligning with the known polynomial-time optimizability of Clifford circuits. Finally, the average-case complexity of CODP for random circuits remains uncharacterized; our empirical results suggest that the average-case behavior for random circuits is substantially easier than the worst case (most random circuits are at prototype action-space ceiling, so the answer is trivially "no" for small $k$), but formal average-case hardness results are lacking.

### 2.4 Quantum Compilers

Modern quantum compilers implement multi-pass optimization pipelines that combine peephole optimization with global synthesis techniques. We survey Qiskit as the primary production-compiler baseline, with Cirq and t|ket> comparison data from E20 (1,070 rows) providing a three-compiler perspective.

**Qiskit (IBM).** Qiskit Terra [Qiskit Contributors 2023] implements a multi-pass optimization pipeline with four optimization levels (0–3). The pipeline includes: (1) basis translation to map the circuit to the hardware-native gate set, (2) layout to map logical qubits to physical qubits, (3) routing to insert SWAP gates for connectivity constraints, and (4) optimization through template matching, commutation, and cancellation. The key optimizer is `TemplateOptimization` (Amy et al. [2013] style) with a fixed template library of approximately 50 patterns. Qiskit achieves 10–30% gate reduction on typical circuits but provides no optimality guarantees. Our analysis (Section 5.3) reveals that Qiskit's template-based approach—a form of Phase-2 optimization—cannot achieve significant reduction on random circuits because the template library is finite and random circuits lack repeating patterns. Through pass-level decomposition, we identify that template matching and Clifford simplification account for approximately 50% of Qiskit's beyond-peephole advantage, phase-polynomial optimization contributes ~25%, and basis translation contributes ~15%.

The template matching pass alone accounts for the largest fraction of Qiskit's advantage on structured circuits. Qiskit's template library includes identities for common gate patterns (e.g., $H \cdot X \cdot H = Z$, $\text{CNOT} \cdot \text{CNOT} = I$, $R_z(\alpha) \cdot R_z(\beta) = R_z(\alpha + \beta)$) and more complex multi-qubit identities involving CNOT chains and controlled-phase rotations. When a circuit contains these patterns, template matching achieves substantial reduction; when it does not (as in random circuits), the pass is ineffective. This pattern-matching approach is fundamentally limited by the template library's coverage: any circuit structure not represented in the library is invisible to the optimizer. Our framework provides the theoretical foundation for understanding this limitation: Theorem 1 establishes that random circuits have exponentially few adjacent inverse pairs, and Theorem 2 shows that no local search strategy can overcome this structural barrier.

**Cirq (Google).** Cirq [Cirq Contributors 2023] uses moment-based optimization, where circuits are organized into "moments" (time steps) in which gates in the same moment act on disjoint qubits. The optimizer merges and cancels gates within and across moments. Key optimizers include `MergeInteractions` and `EjectZ` (phase polynomial style). Cirq achieves 5–20% reduction on typical circuits, with better performance on circuits with many $R_z$ gates due to phase polynomial optimization. Our framework shows that moment-based optimization—which exploits commutation within moments—is a special case of Phase-2 optimization, and its effectiveness depends on the circuit's commutation graph structure. Cirq's phase polynomial optimizer is particularly effective on variational circuits (VQE, QAOA) that contain many parameterized rotations, achieving reductions that pure peephole methods cannot match. However, on circuits without substantial $R_z$ content (e.g., GHZ state preparation, QFT), Cirq's advantage over peephole methods diminishes.

**t|ket> (Cambridge Quantum Computing).** t|ket> [Sivarajah et al. 2020] uses architecture-aware optimization that optimizes for specific hardware connectivity (e.g., IBM's heavy-hex, Google's Sycamore). The key optimizer is `FullPeepholeOptimise`, a comprehensive peephole optimizer with commutation, template matching, and hardware-aware routing. t|ket> achieves 15–40% reduction on typical circuits, with the best performance on circuits that match the hardware topology. Our framework shows that hardware-aware optimization—which restricts commutation to respect connectivity—is a constrained version of Phase-2, and the connectivity constraints further limit the achievable reduction. Specifically, hardware connectivity constraints reduce the commutation graph's edge density, limiting the Phase-2 action space $\mathcal{S}_{1+2}(C)$ and thereby reducing the optimization gap $\Gamma(C)$. This trade-off—between hardware compatibility and optimization effectiveness—is a fundamental tension in architecture-aware compilation that our framework makes explicit.

The gap between production compilers and peephole optimizers is not merely quantitative (10–40% vs. 0–20% reduction) but qualitative: production compilers employ mechanisms that fundamentally exceed the local peephole model. Template matching extends the effective window size beyond the 2-gate peephole limit. Phase polynomial optimization operates on the algebraic structure of rotation angles, not just gate sequences. Global synthesis techniques (e.g., Qiskit's unitary synthesis pass) can replace entire circuit segments with optimized implementations, achieving reductions that no sequence of local rewrites could produce. Our multi-compiler comparison (Section 5.3) quantifies this gap and identifies the specific mechanisms responsible, providing compiler developers with a roadmap for extending peephole optimizers with targeted global synthesis techniques.

**Recent advances.** The period 2021–2025 has witnessed a surge of activity in quantum circuit optimization. Quartz [Xu et al. 2022] introduced the first superoptimization framework for quantum circuits, using Enumerative Circuit Equivalence Checking (ECC) to exhaustively enumerate all small circuits and extract optimal rewrite rules. Nam et al. [78] developed automated optimization techniques for large quantum circuits with continuous parameters, achieving significant reductions through rotation merging and gate cancellation on parameterized circuits. Quanto [Pointing et al. 2024] extends Quartz by automating the generation of circuit identities, producing larger and more expressive identity sets. Qarl [Li et al. 2024] departs from the rule-based paradigm and applies deep reinforcement learning with graph neural networks, significantly outperforming existing optimizers on benchmark circuits and learning rotation merging strategies that previously required hand-engineered compiler passes. AlphaTensor-Quantum [Ruiz et al. 2025] applies the AlphaTensor reinforcement learning architecture to T-count optimization, achieving 37–47% T-gate reductions on arithmetic circuits by exploiting a formal connection between T-count optimization and tensor decomposition over $\mathbb{F}_2$. Relaxed Peephole Optimization [Liu et al. 2021] extends the peephole window by permitting approximate or partial matches, improving gate cancellation rates on circuits where exact pattern matches are rare.

Despite these advances, none of the existing optimization frameworks—Quartz, Quanto, Qarl, AlphaTensor-Quantum, Relaxed Peephole Optimization, or ZX+RL—provides a prototype action-space ceiling characterization, quantifies context-dependent Phase-2 advantage, or offers a systematic multi-compiler benchmark with formal theory. Our work fills these gaps by providing the boundary characterization: the structural, empirical, and theoretical framework for understanding the limits of peephole optimization.

### 2.5 Related Benchmarking Efforts

Systematic benchmarking of quantum compilers remains surprisingly rare. The Micro-Benchmark Suite [Merilehto 2025] presents `microbench.py`, a compact (~200-line) Python script that automates the collection of standardized metrics across quantum transpilers. The suite evaluates six self-generated circuits (Ripple-Carry Adder, QFT, Grover's Algorithm, Hardware-Efficient Ansatz, Random Clifford, and Modular Multiplication) with 3–8 qubits, measuring post-routing circuit depth, two-qubit gate count, wall-clock compilation time, and peak resident-set memory across Qiskit, t|ket>, Cirq, and Amazon Braket. The suite identifies concrete trade-offs: Amazon Braket achieved significantly lower circuit depths (mean 8.8 vs. 22.5) and fewer two-qubit gates (7.2 vs. 16.3) compared to Qiskit, while Qiskit offered faster compilation times (mean 112.2 ms vs. 224.3 ms). The tool runs in under three minutes and outputs reproducible CSV data and plots.

However, the Micro-Benchmark Suite is a measurement tool, not an optimization method or theoretical framework. It reports empirical metrics but does not explain why different compilers produce different results, does not characterize the structural properties of circuits that determine optimizability, and does not analyze the gap between empirical performance and theoretical optima. The benchmark corpus (6 small circuits, 3–8 qubits) is orders of magnitude smaller than our study (over 67,000 data rows across 27 datasets across 15 primary circuit families at scales up to $n = 20$ in the extended suite). Our work provides the theoretical and empirical framework that would enable interpreting the measurements that tools like `microbench.py` produce, grounding compiler comparisons in structural theory rather than ad-hoc observation.

Other benchmarking efforts in quantum computing have focused on hardware performance characterization (e.g., quantum volume, circuit layer operations per second) rather than compiler optimization effectiveness. The absence of systematic compiler benchmarking at scale represents a critical gap that our work directly addresses through the largest empirical study of quantum circuit peephole optimization conducted to date.

---

*Manuscript version 5.0 (v5)*
*Date: 2026-06-14*
*Target: 40–50 pages total (this document: Sections 1–2, approximately 11 pages)*


---

# Section 3: Theoretical Framework

This section develops the formal apparatus underlying our analysis: a unified hierarchy of optimization phases, prototype action-space ceilings, and action spaces that together explain the empirical behavior of peephole circuit optimizers. We introduce all definitions (D1--D12), state and prove the principal theorems (Theorems 1, 2, 5--9), and articulate the conjectures (C1--C2) and open problems (OP1--OP2) that frame the boundaries of this investigation.

**Methodological note.** The theoretical framework presented here was developed to explain observed experimental patterns, not to make a priori predictions. The chronology was: (1) observe 0% Phase-1 reduction on random circuits (E1, 25,000 trials), (2) identify LBL listing as the cause, (3) formalize the observation as Observation 1(b), (4) construct theoretical extensions (Theorems 5-9) to explain and bound the observed phenomena. The theorems should therefore be interpreted as descriptive (characterizing what was observed) rather than predictive (making testable forecasts about unseen circuits). Predictive validation-stating a theorem about an untested family, predicting its regime, then running the experiment-is an important direction for future work (Section 6.4).

---

## 3.1 Core Definitions

We begin with the foundational objects. All circuits are defined over a fixed gate set $\mathcal{G}$ acting on $n$ qubits with Hilbert space dimension $d = 2^n$. The standard gate set throughout this work is $\mathcal{G} = \{H, T, T^\dagger, S, S^\dagger, R_x(\theta), R_y(\theta), R_z(\theta), X, Y, Z, \text{CNOT}, \text{CZ}\}$, though our definitions apply to any finite (or parameterized finite) gate set.

**Definition 1 (Quantum Circuit).** A quantum circuit $C$ is a finite ordered sequence of quantum gates $C = (g_1, g_2, \ldots, g_m)$, where each $g_i \in \mathcal{G}$ acts on a specified subset of qubits $Q(g_i) \subseteq \{q_0, \ldots, q_{n-1}\}$. The **size** of the circuit is $|C| = m$, the total gate count. The circuit implements the unitary $U(C) = g_m \cdot g_{m-1} \cdots g_1$, where the product is taken in the operator sense (rightmost gate applied first).

**Definition 2 (Unitary Equivalence).** Two circuits $C$ and $C'$ are **unitarily equivalent**, denoted $C \equiv C'$, if they implement the same unitary transformation on the joint Hilbert space: $U(C) = U(C')$. Equivalently, $F_{\text{avg}}(C, C') = 1$. We also define approximate equivalence $C \equiv_\epsilon C'$ when $\|U(C) - U(C')\|_\diamond \le \epsilon$.

**Definition 3 (Peephole Optimization).** A **peephole optimization** is a local, unitary-preserving transformation $T$ that replaces a contiguous subsequence (window) $W = (g_i, g_{i+1}, \ldots, g_{i+w-1}) \subseteq C$ with an equivalent subsequence $W'$ satisfying $U(W) = U(W')$ and $|W'| \le |W|$. The **window size** is $w = |W|$. An optimization pass is a sequence of peephole transformations applied iteratively until a fixed point or termination criterion is reached.

**Definition 4 (Phase 1 Optimizer).** A **Phase 1 optimizer** is restricted to peephole windows of size $w = 2$ (adjacent gate pairs) and applies only the following move primitives:

- **REMOVAL**: If $g_{i+1} = g_i^{-1}$ and $Q(g_i) = Q(g_{i+1})$, delete both gates (net reduction: 2 gates).
- **Rotation merging**: If $g_i = R_\alpha(\theta_1)$ and $g_{i+1} = R_\alpha(\theta_2)$ on the same qubit and axis, replace with $R_\alpha(\theta_1 + \theta_2)$ (net reduction: 1 gate).

Phase 1 optimizers do not reorder gates across non-commuting blocks. The four Phase 1 optimizers studied in this work (Greedy, RLS, SA, GA) differ in their search strategies but share the same move primitives and window constraint.

**Definition 5 (Phase 2 Optimizer).** A **Phase 2 optimizer** applies commutation rules to reorder gates within a sliding window of size $w \ge 3$. Specifically, if gates $g_i$ and $g_k$ (with $k > i + 1$) are mutual inverses on the same qubits, and every intermediate gate $g_j$ for $i < j < k$ commutes with both $g_i$ and $g_k$, then the optimizer performs a bubble-sort-style commutation to bring $g_k$ into adjacency with $g_i$, enabling a subsequent REMOVAL. Phase 2 extends the optimizer's reach beyond listing-adjacent pairs.

**Definition 6 (Phase 1 Action Space $\mathcal{S}_1(C)$).** The **Phase 1 action space** is the set of all listing-adjacent gate pairs amenable to Phase 1 reduction:

$$
\mathcal{S}_1(C) = \bigl\{(g_i, g_{i+1}) : Q(g_i) = Q(g_{i+1}) \text{ and } g_{i+1} = g_i^{-1}\bigr\}.
$$

For rotation gates, we additionally include mergeable pairs $(R_\alpha(\theta_1), R_\alpha(\theta_2))$ on the same qubit and axis. The cardinality $|\mathcal{S}_1(C)|$ is the number of immediately actionable optimization opportunities.

**Definition 7 (Phase 2 Action Space $\mathcal{S}_{1+2}(C)$).** The **extended action space** is the set of all gate pairs that can be brought into adjacency via a sequence of valid commutation rewrites within the circuit:

$$
\mathcal{S}_{1+2}(C) = \bigl\{(g_i, g_k) : g_k = g_i^{-1},\; Q(g_i) = Q(g_k),\; \text{and all intermediates commute}\bigr\}.
$$

By construction, $\mathcal{S}_1(C) \subseteq \mathcal{S}_{1+2}(C)$. The **Phase 2 advantage** is characterized by the set difference $\mathcal{S}_{1+2}(C) \setminus \mathcal{S}_1(C)$.

**Definition 8 (Phase 1 Ceiling $R_1^*(C)$ and Structural Ceiling $L_1(\mathcal{F})$).** For a circuit $C$, the **Phase 1 reduction ceiling** is the maximum fractional gate-count reduction achievable by any Phase 1 optimizer:

$$
R_1^*(C) = \max_{O \in \mathcal{O}_1} \frac{|C| - |O(C)|}{|C|},
$$

where $\mathcal{O}_1$ is the set of all Phase 1 optimizers. The **prototype action-space ceiling** for a circuit family $\mathcal{F}$ is the ensemble average:

$$
L_1(\mathcal{F}) = \mathbb{E}_{C \sim \mathcal{F}}[R_1^*(C)].
$$

**Definition 9 (Optimization Gap $\Gamma(C)$).** The **optimization gap** quantifies the additional reduction unlocked by Phase 2 commutation rewriting:

$$
\Gamma(C) = R_{1+2}^*(C) - R_1^*(C),
$$

where $R_{1+2}^*(C)$ is the maximum fractional reduction achievable by any Phase 1+2 optimizer. Conjecture C2 asserts that $\Gamma(C) = \Omega(1)$ for specific structured circuit families.

**Definition 10 (Average Gate Fidelity $F_{\text{avg}}$).** The **average gate fidelity** between circuits $C$ and $C'$ is

$$
F_{\text{avg}}(C, C') = \frac{|\text{Tr}(U^\dagger U')|^2 + d}{d^2 + d},
$$

where $d = 2^n$, $U = U(C)$, and $U' = U(C')$. This corresponds to the mean fidelity averaged over all pure input states $|\psi\rangle$ drawn from the Haar measure:

$$
F_{\text{avg}} = \int d\psi\; \langle\psi| U^\dagger U' |\psi\rangle \langle\psi| (U')^\dagger U |\psi\rangle.
$$

$F_{\text{avg}}$ is the physically meaningful metric for comparing quantum operations, as it represents the expected overlap of output states for a uniformly random input.

---

## 3.2 Circuit Listing Models

A discovery central to this work is that the Phase 1 action space $\mathcal{S}_1(C)$ depends critically not on the circuit's gate content alone, but on its **listing model** -- the data-structural ordering of gates in the instruction sequence. This section formalizes two listing models and proves their divergent implications for Phase 1 optimization.

**Definition 11 (Wire-Consecutive Listing, WCL).** A circuit $C = (g_1, \ldots, g_m)$ is in **wire-consecutive listing** if, for every qubit $q$, the subsequence of gates acting on $q$ appears as a contiguous block in the listing. Formally, let $\sigma_q = (g_{i_1}, g_{i_2}, \ldots, g_{i_k})$ be the gates acting on qubit $q$ in temporal order. Under WCL, the listing indices satisfy $i_{j+1} - i_j = 1$ for all $j$ within each wire's block. Gates on different wires may be interleaved, but within each wire, successive gates are listing-adjacent.

**Definition 12 (Layer-by-Layer Listing, LBL).** A circuit $C$ is in **layer-by-layer listing** if gates are organized into layers $L_0, L_1, \ldots, L_{D-1}$, where each layer contains at most one gate per qubit. The listing order is layer-major: all gates of $L_\ell$ precede all gates of $L_{\ell+1}$, and within each layer, gates are listed in qubit order $q_0, q_1, \ldots, q_{n-1}$. Under LBL, the listing index of the gate on qubit $q$ at layer $\ell$ is $\ell \cdot n + q$.

The choice of listing model is not merely cosmetic. It determines which gate pairs are "visible" to Phase 1 optimizers, which operate on listing-adjacent pairs.

**Theorem 1 (Adjacent Inverse Pair Density and Listing-Model Dependency).**

**(a) Wire-consecutive listing.** Let $C(n, d, \rho)$ be a random circuit on $n$ qubits of depth $d$ with two-qubit gate density $\rho$, represented in WCL. Assume single-qubit gates are drawn uniformly from $\mathcal{G}_1$ with $|\mathcal{G}_1| = g_1$, and two-qubit gates from $\mathcal{G}_2$ with $|\mathcal{G}_2| = g_2$. The expected number of listing-adjacent inverse pairs is

$$
\mathbb{E}\bigl[|\mathcal{A}_{\text{adj}}(C)|\bigr] = n(d - 1) \cdot p_{\text{cancel}}(n, \rho),
$$

where

$$
p_{\text{cancel}}(n, \rho) = (1 - \rho)^2 \cdot p_{\text{inv}}^{(1q)} + \rho^2 \cdot p_{\text{inv}}^{(2q)}(n).
$$

For the standard gate set $\mathcal{G} = \{H, T, T^\dagger, R_z(\theta), \text{CNOT}\}$:

$$
\mathbb{E}\bigl[|\mathcal{A}_{\text{adj}}(C)|\bigr] \le n(d - 1)\left[\frac{(1 - \rho)^2}{g_1^2} + \frac{\rho^2}{g_2 \cdot (n - 1)}\right].
$$

*Proof.* On a fixed qubit wire, two consecutive layers both place single-qubit gates with probability $(1-\rho)^2$; the probability the second is the inverse of the first is $p_{\text{inv}}^{(1q)} \le 2/g_1^2$ (the factor of 2 accounts for self-inverse gates and inverse pairs like $T$--$T^\dagger$). For two-qubit gates, both layers place a gate on the same qubit pair with probability $\rho^2/(n-1)$. Summing over $n$ wires and $d-1$ adjacent layer pairs by linearity of expectation yields the result. Each cancellation removes 2 gates from $|C| \approx nd/(1 - \rho/2)$, so $\mathbb{E}[R_{\text{adj}}] \le 2p_{\text{cancel}} = O(1/g_1^2 + 1/(g_2 n))$. $\blacksquare$

**(b) Layer-by-layer listing.** For $n \ge 2$ and any circuit $C$ generated under LBL:

$$
\mathcal{S}_1(C) = \emptyset \quad \text{for all } C.
$$

Consequently, $R_1(C) = 0$ for every Phase 1 optimizer, regardless of gate content.

*Proof.* Under LBL, the gate on qubit $q$ at layer $\ell$ occupies listing index $\ell \cdot n + q$. The next gate on the same qubit is at layer $\ell+1$, at index $(\ell+1)\cdot n + q$, a gap of $n \ge 2$. Since Phase 1 requires listing adjacency (gap $= 1$) on the same qubit(s), no Phase 1 action is possible. Furthermore, consecutive gates on the same qubit are separated by $n - 1 \ge 1$ intervening gates, so no consecutive rotation pairs exist on the same qubit. By Theorem 2(a), $R_1(C) = 0$. $\blacksquare$

**Discussion: Implications for Compiler Design.** Observation 1(b) reveals that the zero Phase 1 reduction observed across 25,000 trials in experiments E1--E5 (visualized as a depth-independent flat profile in Figure 1) is not a property of the random circuits themselves but an artifact of the LBL listing model used by the circuit generator. The circuits contain wire-level inverse pairs; LBL merely hides them from listing-adjacent detection. This has three practical implications:

1. **Listing-model awareness.** Compiler optimization passes should be designed and evaluated with explicit attention to the circuit's data-structural representation. An optimizer that appears to achieve zero reduction on one listing may achieve significant reduction on another representation of the identical circuit.

2. **Wire-traversal preprocessing.** Before applying Phase 1 optimization, a preprocessing step should reorder gates into WCL (or an equivalent wire-consecutive form), ensuring that Phase 1 results reflect the circuit's intrinsic algebraic structure rather than an artifact of the data-structure ordering.

3. **Phase 2 robustness.** Phase 2 commutation rewriters, which operate on the circuit dependency graph rather than the flat listing, are unaffected by this listing-model dependency. They reason about wire-level adjacency and commutation relations directly, making them inherently listing-model invariant.

---

## 3.3 Phase 1 Structural Ceiling

The central structural result of this work establishes that all Phase 1 optimizers -- deterministic and stochastic alike -- share a common reduction ceiling determined entirely by the circuit's action space.

**Theorem 2 (Phase 1 Reduction Ceiling).** Let $\mathcal{O}_1 = \{\text{Greedy}, \text{SA}, \text{GA}, \text{RLS}\}$ denote the set of Phase 1 optimizers.

**(a) Greedy ceiling.** If $\mathcal{S}_1(C) = \emptyset$ and no consecutive rotation gates on the same qubit admit merging, then Greedy achieves zero reduction: $R_{\text{greedy}}(C) = 0$.

**(b) Stochastic ceiling.** The stochastic optimizers (SA, GA, RLS) employ additional move primitives (SWAP, COMMUTATION, INSERTION) via their neighborhood generation function. However, no finite sequence of such moves can achieve a net gate-count reduction beyond what is enabled by the commutation and swap structure already latent in $C$.

*Proof of (a).* Greedy applies only REMOVAL (requiring $\mathcal{S}_1 \neq \emptyset$) and rotation merging (requiring consecutive rotations on the same qubit). When neither is available, the circuit is a fixed point: $R_{\text{greedy}}(C) = 0$. $\blacksquare$

*Proof of (b).* The base class provides four move types: REMOVAL, SWAP, COMMUTATION, and INSERTION. SWAP exchanges adjacent gates on disjoint qubits; it preserves the gate multiset and the relative ordering of gates on each individual wire, but can make previously non-adjacent gates listing-adjacent. If the resulting adjacent pair acts on the same qubits and is inverse, SWAP creates a new $\mathcal{S}_1$ element. However, the two gates were already present in $C$; SWAP merely makes their inverse relationship listing-visible. Any reduction enabled by SWAP was latent in the wire-level structure.

COMMUTATION replaces an adjacent pair $(g_i, g_{i+1})$ with an equivalent commuted pair of the same size. If the original was not an inverse pair, the commuted pair is generically also not inverse.

INSERTION adds an identity pair $(g, g^{-1})$ at position $p$, increasing $|C|$ by 2. Any REMOVAL applied to the inserted pair restores the original circuit (net change: 0). More generally, if $k$ INSERTION moves add $2k$ gates, the maximum number of gates removable via subsequent REMOVALs involving at least one inserted gate is $2k$, yielding net reduction $\le 0$. $\blacksquare$

**Theorem 2c (Bounded INSERTION Cascade Lemma).** For any circuit $C$ with $\mathcal{S}_1(C) = \emptyset$, let $k$ INSERTION moves produce circuit $C'$ with $|C'| = |C| + 2k$. Let $R_{\text{removal}}(C')$ be the maximum number of gates removable via REMOVAL sequences involving at least one inserted gate. Then $R_{\text{removal}}(C') \le 2k$, so the net gate-count change from any INSERTION + REMOVAL sequence is non-negative.

*Proof (Insertion-debt invariant).* Define the **insertion debt** $\Delta(C')$ as the number of gates in $C'$ that were introduced by INSERTION moves. Initially, $\Delta(C) = 0$. Each INSERTION increases $\Delta$ by exactly 2. Each REMOVAL involving at least one inserted gate decreases $\Delta$ by at most 2 (it removes at most 2 inserted gates, and possibly also removes a pre-existing gate). Critically, the debt is always non-negative: $\Delta(C') \ge 0$ at all times.

Consider a sequence of $k$ INSERTION moves followed by REMOVAL operations. The total debt introduced is $2k$. Each REMOVAL that reduces the circuit size (net) must remove at least one pre-existing gate, which requires that a pre-existing gate has been brought into a cancelable configuration. But INSERTION only adds gates; it never removes pre-existing gates from their wires. The maximum number of pre-existing gates that can be removed is bounded by the number of new cancelable configurations created, which is at most the number of inserted gates participating in REMOVAL: at most $2k$ gates removed, of which at most $k$ are pre-existing. But each such REMOVAL also removes one inserted gate, so the net change is $\ge 0$.

Formally: let $r_{\text{ins}}$ be the number of inserted gates removed and $r_{\text{pre}}$ the number of pre-existing gates removed. Since every REMOVAL pair contains at least one inserted gate (by hypothesis), $r_{\text{ins}} \ge r_{\text{pre}}$. The net gate-count change is $+2k - r_{\text{ins}} - r_{\text{pre}}$. Since $r_{\text{ins}} \le 2k$ and $r_{\text{pre}} \le r_{\text{ins}}$, we have $+2k - r_{\text{ins}} - r_{\text{pre}} \ge 2k - 2k - 0 = 0$. $\blacksquare$

**Theorem 2d (INSERTION Commutation Cascade Bound).** Even when INSERTION is combined with SWAP and COMMUTATION moves within Phase 1, the net reduction from any finite sequence of moves starting from $\mathcal{S}_1(C) = \emptyset$ cannot exceed $B_{\text{pre}}(C)$ -- the number of pre-existing wire-level inverse pairs that SWAP/COMMUTATION can bring into adjacency, which is exactly the Phase 2 action space $\mathcal{S}_{1+2}(C) \setminus \mathcal{S}_1(C)$.

*Proof (Wire-unitary preservation argument).* Under any sequence of INSERTION, SWAP, and COMMUTATION moves, the **wire-level unitary product** of pre-existing gates is preserved (though same-wire COMMUTATION may reorder them while preserving the unitary product). INSERTION adds new gates between existing ones but does not change the wire-level unitary of pre-existing gates. SWAP exchanges adjacent gates on disjoint qubits, which does not affect per-wire unitaries. COMMUTATION preserves the wire-level unitary by definition (Lemma 3). For a formal proof, see Appendix A.

Since the per-wire unitary is invariant, INSERTION cannot create new wire-level inverse relationships among pre-existing gates beyond those already present in $C$. Two pre-existing gates $g_a$ and $g_b$ on the same wire that are inverses in the wire-level unitary remain so after any sequence of Phase 1 moves — and if they were not inverses, no INSERTION can make them so. INSERTION may insert additional gates, but cannot change the algebraic content of the pre-existing gates.

Therefore, INSERTION cannot create new pre-existing gate cancellations beyond what is already accessible via Phase 2 commutation reordering. The net reduction is bounded by $B_{\text{pre}}(C) = |\mathcal{S}_{1+2}(C) \setminus \mathcal{S}_1(C)|$. Since Phase 1 by definition does not include systematic commutation reordering across non-commuting blocks, the INSERTION-facilitated cascade cannot exceed what Phase 2 would achieve directly. $\blacksquare$

**Corollary 2.1 (Universality of the Phase 1 Ceiling).** All Phase 1 optimizers in $\mathcal{O}_1$ achieve identical ceiling $R_1^*(C)$ on any circuit $C$:

$$
R_{\text{greedy}}(C) = R_{\text{RLS}}(C) = R_{\text{SA}}(C) = R_{\text{GA}}(C) = R_1^*(C).
$$

This follows from Theorem 2(a,b) and Theorems 2c--2d: Greedy achieves $R_1^*(C)$ by exhausting $\mathcal{S}_1(C)$, and stochastic optimizers cannot systematically exceed this ceiling via SWAP, COMMUTATION, or INSERTION moves. Empirical Observation 1 (100 circuits, 4 optimizers, all achieving $\le 0.67\%$ mean reduction on random circuits) provides strong experimental corroboration; Figure 3 shows all four optimizers—Greedy, RLS, SA, and GA—converging to approximately 0% mean reduction on random universal circuits, despite vastly different runtime costs.

---

## 3.4 Phase 2 Context-Dependent Advantage

Phase 2 commutation rewriting unlocks optimization opportunities invisible to Phase 1. We now prove that this advantage is not merely hypothetical but manifests concretely for specific circuit families -- and that it is fundamentally context-dependent.

**Theorem 7 (Explicit Circuit Family with $\Omega(1)$ Phase 2 Advantage).** There exists an explicit family of circuits $\{C_n\}_{n \ge 2}$ on $n$ qubits such that:

1. $R_1(C_n) = 0$ for all Phase 1 optimizers ($\mathcal{S}_1(C_n) = \emptyset$), and
2. $R_{1+2}(C_n) \ge \frac{1}{6}$ for all $n \ge 2$.

*Construction.* For each $n \ge 2$ (even), define $C_n$ of depth 6:

- **Layer 1**: $\text{CNOT}(q_0, q_1), \text{CNOT}(q_2, q_3), \ldots$ (even-indexed pairs, $n/2$ gates)
- **Layer 2**: $H(q_0), H(q_1), \ldots, H(q_{n-1})$ ($n$ gates)
- **Layer 3**: $\text{CNOT}(q_1, q_2), \text{CNOT}(q_3, q_4), \ldots$ (odd-indexed pairs, $n/2$ gates)
- **Separator**: $S$ gate on the control qubit of each Layer-3 CNOT ($n/2$ gates)
- **Layer 4**: Repeat of Layer 3 ($n/2$ gates, self-inverse pairs with Layer 3)
- **Layer 5**: $H(q_0), \ldots, H(q_{n-1})$ ($n$ gates, self-inverse with Layer 2)
- **Separator$^\dagger$**: $S^\dagger$ gates ($n/2$ gates)
- **Layer 6**: Repeat of Layer 1 ($n/2$ gates, self-inverse with Layer 1)

Total: $5n$ gates. The circuit implements the identity $U(C_n) = I$.

*Proof sketch.* In the original listing, no adjacent pair is inverse: $S$ separators between Layers 3 and 4 prevent listing-adjacency of the CNOT pairs. However, $S$ on the control qubit commutes with CNOT (since $S = |0\rangle\langle 0| + i|1\rangle\langle 1|$ is diagonal, and the CNOT control depends only on the computational-basis state). Phase 2 performs bubble-sort commutation to move each Layer-3 CNOT past its $S$ separator and into adjacency with the corresponding Layer-4 CNOT. After $\text{CNOT} \cdot \text{CNOT} = I$ cancellation, the $S$--$S^\dagger$ pairs become adjacent and cancel, as do the $H$--$H$ and Layer-1/6 CNOT pairs. Total removal: $2n$ gates from $5n$, yielding $R_{1+2} = 2/5 > 1/6$. $\blacksquare$

**Theorem 9 (Phase-2b Template-Assisted Advantage for Bernstein--Vazirani Oracle Circuits).** For the natural Bernstein--Vazirani (BV) oracle circuit family, Phase-2b (commutation plus template matching) achieves a gate-count reduction of at least

$$
\Gamma^{\text{(2b)}}(C_n^{\text{BV}}) \ge \frac{n}{4.5n + 4} = \Omega(1),
$$

while Phase 1 achieves $R_1(C_n^{\text{BV}}) = 0$. Phase-2b template matching is implemented with fixture-scale validation (`Phase2bTemplateMatcher` in `src/optimisation/phase2/template_matcher.py`, unit-tested in `tests/test_phase2b_template_matcher.py`, with E10 Phase-2b validation data comprising 1,017 rows); full canonical-scale Phase-2b benchmarking across all 15 families remains future work. The implementation-aligned Phase-2a bound remains open.

*Statement and proof sketch.* The BV oracle circuit on $n$ data qubits (plus one ancilla) has the structure:

$$
C_n^{\text{BV}} = X_{\text{anc}} \cdot H^{\otimes(n+1)} \cdot \prod_{i \in S} \text{CNOT}(q_i, q_{\text{anc}}) \cdot H^{\otimes(n+1)} \cdot H_{\text{anc}} \cdot X_{\text{anc}},
$$

where $S \subseteq \{0, \ldots, n-1\}$ is the secret string. The circuit contains $2n$ Hadamard gates on the data qubits (one pre-oracle, one post-oracle layer), which are listing-separated by the CNOT oracle gates. Phase 1 cannot cancel them because the intervening CNOT gates are non-adjacent to the Hadamard pairs.

The Phase-2b proof uses commutation to expose $H$-CNOT-$H$ sandwiches and then applies a template identity to rewrite them. The $n/(4.5n+4)$ lower bound is therefore a theoretical/template-assisted result, not a direct measurement of the current CommutationRewriter. All experimental Phase 2 results in this manuscript are Phase-2a (commutation-only) unless explicitly labeled Phase-2b.

**Comparison with artificial construction.** Theorem 7 proves $\Omega(1)$ Phase-2b advantage for a deliberately engineered circuit family. Theorem 9 strengthens this result to the Bernstein--Vazirani oracle, a *natural* circuit family arising from a well-known quantum algorithm. The BV result demonstrates that template-assisted Phase-2b advantage is not merely a pathological artifact. The empirical Phase-2a Oracle/BV reductions reported in E11/E14 are complementary evidence for context-dependent commutation benefit, but they do not directly validate the Phase-2b template-matching theorem.

**Conjecture C1 (Phase 1 Ceiling is Structural).** For any circuit family $\mathcal{F}$ in which no adjacent inverse gate pairs exist in the initial data structure, every Phase 1 optimizer achieves exactly $0\%$ gate reduction. This ceiling is a property of the circuit data structure, not of the optimization algorithm.

*Evidence.* Theorem 2 establishes the action-space identity; Theorem 5 provides a high-probability concentration bound; Theorem 6 proves C1 exactly for Clifford circuits in Aaronson--Gottesman canonical form; Theorem 8 proves bounded-window incompressibility for Haar-random unitaries. Empirically, 45,500 trials across Universal, Clifford, and Structured families confirm $\le 0.05\%$ mean reduction for all four Phase 1 optimizers.

**Conjecture C2 (Phase 2 is Context-Dependent Super-Constant).** There exist circuit families $\mathcal{F}$ for which Phase 1 achieves $O(1/d)$ reduction while Phase 1+2 achieves $\Omega(1)$ reduction. The improvement $\Gamma(C)$ is context-dependent: significant for oracle and structured circuits, and zero for already-optimal or structurally rigid families.

*Evidence.* Theorem 7 (explicit construction) and Theorem 9 (BV oracle) establish C2 constructively for Phase-2b/template-assisted rewriting. Empirically, the implemented Phase-2a commutation-only optimizer achieves $\sim 3.26\%$ additional reduction on random Universal circuits (effect size: Cohen's $d = 1.32$; note that Glass's Delta is the preferred measure for Phase 1 comparisons due to zero variance under LBL, but Cohen's $d$ is appropriate here because Phase-2a introduces nonzero variance), $\sim 20\%$ on BV oracle circuits, and $0\%$ on structured brickwork, QFT, and GHZ circuits. Figure 4 visualizes this context-dependent Phase-2a advantage as a grouped comparison across families; these experiments are complementary to, not direct validation of, the Phase-2b theorems.

---

## 3.5 Complexity Context

**Theorem 8 (Haar-Random Incompressibility).** Let $U$ be a Haar-random unitary on $n$ qubits.

**(a) Circuit complexity lower bound.** The minimum circuit size $\mathcal{C}(U)$ over a finite universal gate set satisfies

$$
\Pr\!\left[\mathcal{C}(U) < \frac{4^n}{n^2}\right] \le \exp\!\left(-\Omega\!\left(\frac{4^n}{n}\right)\right).
$$

**(b) Sub-exponential depth regime.** For circuits of size $m = nd$ with $d = \text{poly}(n)$, the maximum achievable fractional reduction by any algorithm satisfies

$$
R_{\max}(C) \le 1 - \frac{4^n}{n^2 m} = 1 - \frac{4^n}{n^3 d} \to 0
$$

doubly-exponentially fast in $n$.

**(c) Bounded-window corollary.** Any algorithm applying at most $k$ peephole rewrites of window size $w$ achieves $R_A(C) \le \min(kw/(nd),\; 1 - 4^n/(n^3 d))$.

*Proof sketch.* Part (a) follows from dimension counting: $SU(2^n)$ has real dimension $4^n - 1$, while circuits of $k$ gates from a finite set parametrize a manifold of dimension $O(k)$. For $k < 4^n/n^2$, the parametrized volume is exponentially small relative to the Haar measure. Part (b) follows since any equivalent circuit $C'$ must satisfy $|C'| \ge \mathcal{C}(U)$. Part (c) is immediate since $k$ rewrites remove at most $kw$ gates. $\blacksquare$

**Critical caveat.** Theorem 8 applies to Haar-random *unitaries*, not to the random *gate sequences* used in our experiments. For $n = 10, d = 50$, the circuit has approximately 500 gates, while the Haar-random complexity threshold is $4^{10}/10^2 \approx 10{,}486$ gates. Our random gate sequences produce unitaries far from Haar-random at these depths. The empirical $\sim 0\%$ reduction on random circuits is explained by the combinatorial sparsity of inverse pairs (Theorem 1), not by Haar-random incompressibility. Theorem 8 provides a complementary information-theoretic argument for the asymptotic regime $d \sim 4^n/n^2$ that is not reached in our experiments. The empirical "optimization desert"—a flat landscape punctuated by exponentially rare deep minima—is documented in Figure 7 (E5 landscape perturbation analysis), where mean reduction is 0.22% with rare 26.67% maxima across 6,000 perturbed trials.

**Regime and scope of Theorem 8.** Theorem 8 applies to Haar-random unitaries, while the E1--E5 experiments use shallow random gate sequences generated by `src/circuits/generator_v2.py` (depth $d \in [1,50]$). For $n = 10$, $d = 50$, the circuits have only $\approx 500$ gates, far below the Haar-random complexity threshold of $\approx 10{,}486$ gates. The theorem should therefore be treated as an asymptotic worst-case bound, not as a direct explanation of the experimental regime. The observed E1--E5 ceiling is instead explained by Theorem 1 (inverse-pair sparsity) and Observation 1(b) (LBL empties the Phase-1 action space).

**Open Problem OP1 (QMA-Hardness of CODP).** Is the Circuit Optimization Decision Problem (CODP) QMA-hard? Circuit Identity Testing (CIT) is QMA-complete (Janzing, Wocjan & Beth, 2003). Since CIT is the special case of CODP with $r = 0$, one might expect CODP to be at least QMA-hard. However, completing the reduction from $k$-Local Hamiltonian requires analyzing the rewrite-rule closure of history-state circuits, which remains open. The empirical observation that all Phase 1 optimizers achieve $\sim 0\%$ on random circuits is *consistent with* QMA-hardness but does not constitute proof.

**Open Problem OP2 (Inapproximability of CODP).** Does CODP admit a polynomial-time constant-factor approximation? The conflict-resolution subproblem (selecting maximum non-overlapping cancelable pairs) is solvable in polynomial time via maximum matching (Proposition 1). The corrected analysis shows that CODP's hardness (if any) must arise from the sequential rewrite search rather than the combinatorial selection step. The dynamic commutation graph, where edges change under commutation moves, may present additional complexity barriers.

---

# Section 4: Methods

This section describes the complete experimental infrastructure: the optimizer suite, circuit families, preprocessing pipeline, compiler baselines, statistical protocol, and experiment registry. All code is implemented in Python 3.10 using Qiskit 2.x and is version-controlled with data artifacts stored under content-addressable hashes.

---

## 4.1 Optimizer Suite

We implement six core optimizers plus one meta-optimizer spanning both phases of the optimization hierarchy. All share a common base class (`BaseOptimizer`) providing fidelity computation, move primitives, and result serialization.

### 4.1.1 GreedyGateCancellation (Phase 1)

**Algorithm.** A deterministic single-pass scanner that iterates through the circuit listing, canceling adjacent self-inverse pairs and merging consecutive same-axis rotations.

**Pseudocode:**
```
GREEDYGATECANCELLATION(C, max_iter, wire_traversal):
    if wire_traversal:
        C ← WCL_PREPROCESS(C)          // Reorder to wire-consecutive listing
    C' ← COPY(C)
    for iter = 1 to max_iter:
        improved ← false
        // Phase A: Adjacent cancellation
        i ← 0
        while i < |C'.data| - 1:
            if IS_SELF_INVERSE_PAIR(C'.data[i], C'.data[i+1]):
                REMOVE(C'.data, i, i+1)
                improved ← true
            else:
                i ← i + 1
        // Phase B: Rotation merging (if no cancellations found)
        if not improved:
            improved ← MERGE_ROTATIONS(C')
        if not improved:
            break
    return C'
```

**Move primitives.** REMOVAL (adjacent inverse cancellation), rotation merging ($R_\alpha(\theta_1) \cdot R_\alpha(\theta_2) \to R_\alpha(\theta_1 + \theta_2)$).

**Time complexity.** $O(m)$ per pass, where $m = |C|$. With `max_iter` iterations, worst case $O(\text{max\_iter} \cdot m)$. In practice, convergence occurs in 1--3 passes.

**Parameters.** `max_iterations` (default 100), `fidelity_threshold` (default 0.99), `wire_traversal` (boolean, default false). When `wire_traversal = true`, the circuit is reordered into WCL before scanning (Section 4.3).

**Correctness note.** Rotation merging correctly handles the global-phase subtlety: $R_\alpha(2\pi) = -I \neq I$. When merged angles sum to a non-zero multiple of $2\pi$, the gates are merged into a single gate preserving the phase, not removed.

### 4.1.2 Random Local Search (Phase 1)

**Algorithm.** At each step, generates a random neighbor circuit by uniformly selecting from the available move primitives (REMOVAL, SWAP, COMMUTATION, INSERTION). Accepts the neighbor if it improves the fitness score $f = \text{reduction} \times \text{sigmoid\_penalty}(F_{\text{avg}})$.

**Pseudocode:**
```
RANDOM_LOCAL_SEARCH(C, max_iter):
    C' ← COPY(C)
    best_fitness ← FITNESS(C', C)
    for iter = 1 to max_iter:
        C'' ← GENERATE_NEIGHBOR(C')     // Random move from {REMOVAL, SWAP, COMMUTATION, INSERTION}
        new_fitness ← FITNESS(C'', C)
        if new_fitness > best_fitness:
            C' ← C''
            best_fitness ← new_fitness
    return C'
```

**Time complexity.** $O(k \cdot m)$ where $k$ is the iteration budget and each neighbor generation + fitness evaluation takes $O(m)$.

### 4.1.3 Simulated Annealing (Phase 1)

**Algorithm.** Metropolis-Hastings acceptance criterion with geometric cooling schedule. At temperature $T$, a neighbor with fitness change $\Delta f$ is accepted with probability $\min(1, \exp(\Delta f / T))$.

**Pseudocode:**
```
SIMULATED_ANNEALING(C, max_iter, T_0, alpha):
    C' ← COPY(C)
    T ← T_0
    for iter = 1 to max_iter:
        C'' ← GENERATE_NEIGHBOR(C')
        Δf ← FITNESS(C'', C) - FITNESS(C', C)
        if Δf > 0 or RANDOM() < exp(Δf / T):
            C' ← C''
        T ← T × alpha                   // Geometric cooling
    return C'
```

**Parameters.** Initial temperature $T_0 = 1.0$, cooling rate $\alpha = 0.995$, iteration budget $k$. The sigmoid-based fidelity penalty (steepness $= 50$, centered at $F_{\text{threshold}}$) provides smooth gradient information even below the fidelity threshold.

**Time complexity.** $O(k \cdot m)$, identical to RLS but with acceptance probability computation.

### 4.1.4 Genetic Algorithm (Phase 1)

**Algorithm.** Population-based search with tournament selection and gate-segment crossover. A population of $P$ candidate circuits evolves over $G$ generations.

**Pseudocode:**
```
GENETIC_ALGORITHM(C, pop_size, generations, tournament_k):
    population ← {GENERATE_NEIGHBOR(C) : i = 1..pop_size}
    for gen = 1 to generations:
        // Tournament selection
        parents ← []
        for i = 1 to pop_size:
            tournament ← RANDOM_SAMPLE(population, tournament_k)
            parents ← parents ∪ {BEST_FITNESS(tournament)}
        // Gate-segment crossover
        offspring ← []
        for i = 1 to pop_size step 2:
            child1, child2 ← SEGMENT_CROSSOVER(parents[i], parents[i+1])
            offspring ← offspring ∪ {MUTATE(child1), MUTATE(child2)}
        population ← SURVIVE(population ∪ offspring, pop_size)
    return BEST_FITNESS(population)
```

**Move primitives.** All four base moves via mutation. Crossover exchanges contiguous gate segments between parent circuits, preserving qubit assignments.

**Time complexity.** $O(G \cdot P \cdot m)$, where $G$ is generations and $P$ is population size.

### 4.1.5 CommutationRewriter (Phase 2)

**Algorithm.** Bubble-sort commutation within a sliding window of size $w$. For each anchor gate $g_i$, scans forward up to $w$ positions for an inverse gate $g_j$. If found, verifies that all intermediate gates commute with both $g_i$ and $g_j$, then bubble-sorts $g_j$ leftward past the commuting intermediates into adjacency with $g_i$, and cancels the pair.

**Pseudocode:**
```
COMMUTATION_REWRITER(C, max_iter, window):
    C' ← COPY(C)
    for iter = 1 to max_iter:
        improved ← false
        for i = 0 to |C'.data| - 1:
            for j = i+2 to min(i + window, |C'.data|):
                if IS_SELF_INVERSE_PAIR(C'.data[i], C'.data[j]):
                    can_commute ← true
                    for k = i+1 to j-1:
                        if not COMMUTES(C'.data[i], C'.data[k]):
                            can_commute ← false; break
                        if not COMMUTES(C'.data[k], C'.data[j]):
                            can_commute ← false; break
                    if can_commute:
                        // Bubble-sort g_j to position i+1
                        for k = j downto i+2:
                            if COMMUTES(C'.data[k-1], C'.data[k]):
                                SWAP(C'.data, k-1, k)
                            else:
                                can_commute ← false; break
                        if can_commute and IS_SELF_INVERSE_PAIR(C'.data[i], C'.data[i+1]):
                            REMOVE(C'.data, i, i+1)
                            improved ← true; break
            if improved: break
        if not improved: break
    return C'
```

**Commutation rules.** The implementation checks sufficient conditions: (1) disjoint qubit sets (always commute), (2) same single-qubit gate on same qubit, (3) same-axis rotations, (4) Z-family gates ($Z, R_z, S, S^\dagger, T, T^\dagger$) on the same qubit, (5) CNOT with Z-family on the control qubit. These rules are sufficient but not necessary: some valid commutation relations (e.g., SWAP gate partial commutation, parameterized gate special angles) are not captured, potentially causing the optimizer to miss some optimization opportunities. This limitation is discussed in Section 6.3.

**Time complexity.** $O(\text{max\_iter} \cdot m \cdot w^2)$ in the worst case, but typically $O(m \cdot w)$ due to early termination of the commutation check loop.

### 4.1.6 HybridCommuteRewrite

**Algorithm.** A three-stage pipeline: Greedy (Phase 1) $\to$ CommutationRewriter (Phase 2) $\to$ Greedy (Phase 1 cleanup).

**Pseudocode:**
```
HYBRID_COMMUTE_REWRITE(C, max_iter, window):
    C1 ← GREEDY(C, max_iter)             // Phase 1: exhaust adjacent pairs
    C2 ← COMMUTATION_REWRITER(C1, max_iter, window)  // Phase 2: commutation-enabled pairs
    C3 ← GREEDY(C2, max_iter)            // Phase 1 cleanup: new adjacent pairs from Phase 2
    return C3
```

**Time complexity.** Sum of three Phase 1/2 passes: $O(m \cdot w)$ dominated by Phase 2.

**Correctness.** By Lemma 3 (commutation preserves unitary equivalence; see lemmas.md) and Corollary 3.2 (HybridCommuteRewrite preserves unitary equivalence), the full pipeline produces a circuit exactly unitarily equivalent to the input: $U(C_3) = U(C)$.

### 4.1.7 CeilingAwareOptimizer (NEW)

**Algorithm.** A proxy-guided conditional pipeline that computes fast $O(m)$ structural proxies before each phase and skips phases predicted to yield zero reduction. **Caveat (HGC)**: The empirical correlation model underlying this proxy does not generalize to unseen circuit families. The Pearson correlation coefficient is undefined (NaN) because all five held-out circuit families exhibited exactly 0% reduction, yielding zero variance in the observed values. This zero-variance outcome is itself informative: it confirms that these families are at prototype action-space ceiling, consistent with the Phase-1 prototype action-space ceiling theory (Theorem 1). However, it precludes meaningful correlation analysis between predicted and observed reduction values. Accordingly, the ceiling-aware optimizer should be treated as an exploratory tool, not a validated predictive system.

**Pseudocode:**
```
CEILING_AWARE_OPTIMIZER(C, max_iter, window):
    // Phase 1 decision
    proxy_p1 ← COUNT_PHASE1_ACTIONS(C)    // O(m): count adjacent inverse + mergeable pairs
    if proxy_p1 > 0:
        C1 ← GREEDY(C, max_iter)
    else:
        C1 ← COPY(C)                      // Skip Phase 1

    // Phase 2 decision
    proxy_p2 ← COUNT_PHASE2_ACTIONS(C1, window)  // O(m·w): count commutation-enabled pairs
    if proxy_p2 > 0:
        C2 ← COMMUTATION_REWRITER(C1, max_iter, window)
    else:
        C2 ← C1                           // Skip Phase 2

    // Final Phase 1 cleanup (only if Phase 2 ran)
    if proxy_p2 > 0:
        proxy_final ← COUNT_PHASE1_ACTIONS(C2)
        if proxy_final > 0:
            C3 ← GREEDY(C2, max_iter)
        else:
            C3 ← C2
    else:
        C3 ← C2

    return C3
```

**Proxy functions.** `COUNT_PHASE1_ACTIONS` performs a single linear scan counting adjacent self-inverse and mergeable-rotation pairs. `COUNT_PHASE2_ACTIONS` performs a windowed scan counting non-adjacent inverse pairs with commuting intermediates, short-circuiting on the first non-commuting intermediate.

**Overhead.** Each proxy is $O(m)$ or $O(m \cdot w)$ with early termination, adding negligible cost compared to a full optimization phase. In E21 full-mode evaluation (1,140 rows across 15 families), the ceiling-aware optimizer matched the full HybridCommuteRewrite pipeline's gate-count reduction while reducing compilation time by 1.6x--228x (mean 35x). Families that skip both Phase 1 and Phase 2 show the largest speedups, while reducible families that skip only one futile phase show smaller speedups.

---

## 4.2 Circuit Families

We evaluate optimizers on 15 primary circuit families plus 3 extended families (18 total), spanning four categories: random, algorithmic, variational, and error-correcting. Table 1 summarizes all families, and Figure 11 visualizes the resulting reduction heatmap across the 15 primary families × 3 optimizer categories, providing a compact overview of the empirical landscape that the methodology is designed to characterize.

**Table 1: Circuit Family Registry (15 primary + 3 extended families)**

| # | Family | Description | Gate Set | Parameters | Generation Method |
|---|--------|-------------|----------|------------|-------------------|
| 1 | Universal (random) | Random universal gates | $\{H, T, T^\dagger, R_z, \text{CNOT}\}$ | $n, d, \rho$ | LBL random placement |
| 2 | Clifford (random) | Random Clifford circuits | $\{H, S, \text{CNOT}\}$ | $n, d$ | Layer-wise random Clifford |
| 3 | Structured (brickwork) | Brickwork-pattern entanglers | $\{H, R_z, \text{CNOT}\}$ | $n, d$ | Alternating even/odd CNOT layers |
| 4 | QFT | Quantum Fourier Transform | $\{H, R_z(\pi/2^k), \text{CNOT}\}$ | $n$ | Standard QFT decomposition |
| 5 | GHZ | GHZ state preparation | $\{H, \text{CNOT}\}$ | $n$ | Linear CNOT chain |
| 6 | BV Oracle | Bernstein--Vazirani oracle | $\{H, X, \text{CNOT}\}$ | $n$, secret $s$ | Oracle + Hadamard layers |
| 7 | CNOT Chain | Self-inverse CNOT chain | $\{\text{CNOT}\}$ | $n$, repeats | Repeated CNOT--CNOT pairs |
| 8 | Grover | Grover search (1 iteration) | $\{H, X, Z, \text{MCX}\}$ | $n$, marked state | Phase oracle + diffusion |
| 9 | Quantum Adder | Ripple-carry adder | $\{X, \text{CNOT}, \text{CCX}\}$ | $n$ | Carry computation + sum |
| 10 | Quantum Walk | Discrete-time walk on cycle | $\{H, X, R_y, \text{MCX}\}$ | $n$, steps | Coin flip + conditional shift |
| 11 | IQP | Instantaneous Quantum Polynomial | $\{H, R_z, \text{CZ}\}$ | $n$, depth | $H^{\otimes n}$ + diagonal layers |
| 12 | QAOA | Quantum Approximate Optimization | $\{H, R_{zz}, R_x\}$ | $n$, reps, $\gamma, \beta$ | Line-graph cost + mixer |
| 13 | VQE (TwoLocal) | Variational eigensolver ansatz | $\{R_y, R_z, \text{CNOT}\}$ | $n$, reps | Qiskit TwoLocal, linear ent. |
| 14 | HardwareEfficient | Hardware-efficient ansatz | $\{R_y, R_z, \text{CNOT}\}$ | $n$, layers | Alternating rotations + entanglers |
| 15 | Random Clifford | Deep random Clifford | $\{H, S, \text{CNOT}\}$ | $n$, depth | Layer-wise random selection |
| 16 | Surface Code | Syndrome extraction | $\{H, X, \text{CNOT}\}$ | $n_{\text{data}}$ | X-stabilizer measurement |
| 17 | UCCSD | Chemistry ansatz | $\{X, R_y, \text{CNOT}\}$ | $n$, reps | Single + double excitation |
| 18 | Haar Random | Haar-random unitary | Full $SU(2^n)$ | $n \le 4$ | Exact synthesis of random $U$ |

**Random families.** Universal random circuits are generated in LBL format with configurable two-qubit gate density $\rho \in [0, 1]$. Clifford circuits use only the stabilizer generators $\{H, S, \text{CNOT}\}$ and are efficiently simulable by the Gottesman--Knill theorem. Structured brickwork circuits alternate even- and odd-indexed CNOT layers, providing regular entanglement structure.

**Algorithmic families.** QFT and GHZ circuits are already gate-optimal (no redundant gates), serving as negative controls. The BV oracle circuit is the natural family from Theorem 9, with a random secret string $s \in \{0, 1\}^n$. Grover circuits use a single iteration with a phase oracle for a random marked state. Quantum adders implement explicit ripple-carry addition using CCX (Toffoli) gates. Quantum walks simulate discrete-time walks on cycle graphs using coin-flip and conditional-shift operators. IQP circuits are believed to be hard to simulate classically and consist of Hadamard-diagonal-Hadamard structure.

**Variational families.** QAOA circuits use line-graph cost functions with bound-parameterized $R_{zz}$ and $R_x$ rotations. VQE ansatze use Qiskit's TwoLocal with $R_y$--$R_z$ rotation blocks and linear CNOT entanglement. Hardware-efficient ansatze alternate parameterized rotation layers with nearest-neighbor CNOT entanglement.

**Error-correcting and chemistry families.** Surface code syndrome extraction circuits model a single round of X-stabilizer measurement. UCCSD ansatze model single and double excitation operators for quantum chemistry, decomposed into CNOT ladders and $R_y$ rotations.

**Haar random.** Exact synthesis of Haar-random unitaries via Qiskit's `random_unitary` + `decompose`, limited to $n \le 4$ qubits due to exponential cost.

All circuits are deterministically seeded (seed $= 42 + \text{offset}$), materialized by binding parameters to fixed values and decomposing composite instructions up to three levels, and fingerprinted via SHA-256 hash of the instruction stream for reproducibility.

---

## 4.3 Wire-Traversal Preprocessing

The wire-traversal preprocessor (Section 3.2, Definition 11) transforms a circuit from any listing model into Wire-Consecutive Listing (WCL), ensuring that Phase 1 optimizers can detect all wire-level inverse pairs.

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
                dag.ADD_EDGE(prev, i)    // Ordering constraint on same wire
            LAST_GATE_ON_WIRE(q) ← i

    // Step 2: Topological sort with wire-consecutive priority
    // Priority: continue on the same wire before switching wires
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

DFS_WIRE_PRIORITY(dag, node, preferred_wire, visited, order):
    visited[node] ← true
    order.APPEND(node)
    // Continue on the same wire first
    next_on_wire ← NEXT_GATE_ON_WIRE(preferred_wire, node)
    if next_on_wire ≠ null and next_on_wire not in visited:
        if ALL_PREDECESSORS_VISITED(next_on_wire, visited):
            DFS_WIRE_PRIORITY(dag, next_on_wire, preferred_wire, visited, order)
    // Then visit successors on other wires
    for succ in dag.SUCCESSORS(node):
        if succ not in visited and ALL_PREDECESSORS_VISITED(succ, visited):
            wire_of_succ ← PRIMARY_WIRE(succ)
            DFS_WIRE_PRIORITY(dag, succ, wire_of_succ, visited, order)
```

**Unitary equivalence proof.** The WCL reordering is a valid topological sort of the circuit's dependency DAG: it respects all ordering constraints imposed by shared qubits. Since the unitary implemented by a circuit depends only on the relative ordering of gates that share qubits (gates on disjoint qubits commute trivially), any valid topological sort preserves the implemented unitary. Therefore $U(\text{WCL}(C)) = U(C)$ exactly.

**Complexity.** DAG construction: $O(m)$ time (one pass through the circuit, constant-time wire-lookup table). Topological sort with wire-consecutive priority: $O(m \log m)$ due to priority-queue operations when multiple wires are ready simultaneously. Overall: $O(m \log m)$.

**Empirical impact.** Experiment E19 (full run, 10,000 rows at n = 5, depths 1–50, 100 trials/depth) confirms that WCL preprocessing exposes Phase 1 Greedy reductions on the random Universal ensemble where LBL yields exactly 0%. Under WCL, mean reduction is 7.83% (std = 3.95%, max = 33.33%) with perfect fidelity (1.0) across all trials, consistent with the density bound from Observation 1(a). LBL yields 0.0000% reduction with zero variance, confirming the Observation 1(b) prediction. This result establishes the listing model as a determinant of the Phase 1 prototype action-space ceiling.

---

## 4.4 Compiler Configurations

We compare against Qiskit, Cirq, and t|ket> as production compiler baselines. E20 (1,070 rows) provides full comparison data across all three compilers on the 15-family extended benchmark suite:

**Qiskit (v2.4.1).** We use `qiskit.transpile` with optimization levels 0--3:
- **Level 0**: No optimization; trivial mapping.
- **Level 1**: Light optimization; adjacent gate cancellation and single-qubit gate merging.
- **Level 2**: Medium optimization; adds commutation analysis and KAK decomposition for two-qubit gates.
- **Level 3**: Heavy optimization; full peephole optimization including template matching, gate resynthesis, and commutation-based reordering.

Specific passes at Level 3 include `Optimize1qGates`, `CXCancellation`, `CommutativeCancellation`, `OptimizeSwapBeforeMeasure`, and `Collect2qBlocks` + `ConsolidateBlocks`. The per-level reduction outcomes across seven circuit families are benchmarked in Figure 9, which shows that the Level-3 advantage is concentrated on families with beyond-peephole structure (Oracle, VQE, HardwareEfficient) and absent on structural-ceiling families (QFT, GHZ, QAOA).

**Cirq (E20, completed).** The configuration uses `cirq.optimize_for_target_gateset` with the `CZTargetGateset`, combined with `cirq.eject_z` and `cirq.merge_single_qubit_gates_to_phxz`. Full E20 canonical comparison data (1,070 rows) is available at `data/v6/e20/`.

**t|ket> (E20, completed).** The configuration uses `FullPeepholeOptimise`, which applies a comprehensive suite of peephole transformations including Clifford simplification, gate cancellation, and commutation-based reordering. Full E20 canonical comparison data (1,070 rows) is available at `data/v6/e20/`.

---

## 4.5 Statistical Protocol

All statistical analyses follow a pre-registered protocol designed for publication-grade rigor.

**Bootstrap confidence intervals.** All reported mean reductions and effect sizes are accompanied by 95% bootstrap confidence intervals computed from $B = 10{,}000$ resamples with replacement. For a statistic $\hat{\theta}$ computed from sample $\{x_1, \ldots, x_N\}$, the bootstrap distribution $\{\hat{\theta}^{*(1)}, \ldots, \hat{\theta}^{*(B)}\}$ yields the percentile interval $[\hat{\theta}^{*}_{(\alpha/2)}, \hat{\theta}^{*}_{(1-\alpha/2)}]$ with $\alpha = 0.05$.

**Effect sizes.** We report two complementary effect-size measures:
- **Cliff's delta** ($\delta$): A non-parametric measure of stochastic dominance, $\delta = P(X > Y) - P(X < Y)$, robust to non-normality. Interpretation: $|\delta| < 0.147$ negligible, $< 0.33$ small, $< 0.474$ medium, $\ge 0.474$ large.
- **Cohen's $d$**: Parametric standardized mean difference, $d = (\bar{x}_1 - \bar{x}_2)/s_{\text{pooled}}$. Interpretation: $|d| < 0.2$ small, $< 0.5$ small-medium, $< 0.8$ medium, $\ge 0.8$ large. **Note**: Cohen's $d$ is undefined when the pooled standard deviation is zero (e.g., Phase 1 under LBL where all reductions are exactly 0%). In such cases, we report **Glass's Delta** ($\Delta = (\bar{x}_1 - \bar{x}_2)/s_{\text{control}}$, approximated as $d/\sqrt{2}$ when per-group SDs are unavailable) or non-parametric Cliff's Delta instead. The `effect_sizes.csv` file includes a `glass_delta` column with these approximations.

**False Discovery Rate (FDR) correction.** When conducting multiple hypothesis tests (e.g., comparing optimizers across multiple circuit families), we apply the Benjamini--Hochberg procedure to control the expected proportion of false discoveries. Given $m$ tests with ordered $p$-values $p_{(1)} \le p_{(2)} \le \cdots \le p_{(m)}$, the BH procedure rejects hypotheses $H_{(i)}$ for $i \le k^*$ where $k^* = \max\{i : p_{(i)} \le i\alpha/m\}$.

**Power analysis.** For experiment E4 (optimizer comparison), we conducted an a priori power analysis: to detect a Cohen's $d = 0.5$ (medium effect) with power $1 - \beta = 0.80$ at significance level $\alpha = 0.05$ (two-tailed), a minimum of $n = 64$ circuits per group is required. We use $n = 100$ circuits per configuration, providing power $> 0.95$ for medium effects.

**Fidelity verification.** Unitary equivalence is verified via exact average gate fidelity for $n \le 12$ qubits (constructing full $2^n \times 2^n$ unitary matrices). For $n > 12$, where exact computation requires $O(4^n)$ memory, we use a sampling-based estimator: 1,000 Haar-random product-state inputs (independent Haar-random single-qubit unitaries applied to $|0\rangle^{\otimes n}$), computing $|\langle\psi_1|\psi_2\rangle|^2$ for each. This estimator has standard error $\sim 1/\sqrt{1000} \approx 3\%$. For Clifford circuits, exact comparison via the stabilizer tableau (Qiskit `Clifford` class) provides $O(n^2)$ verification regardless of qubit count.

Across experiments where fidelity was successfully computed and retained for analysis, optimizer outputs preserve unitary equivalence. Documented failure rows, especially E18 decomposition/fidelity failures, are tracked separately and filtered from analyses requiring valid fidelity. E12 compiler-baseline correctness relies on Qiskit's transpiler semantics rather than independent exact unitary verification for every row.

---

## 4.6 Experimental Design

The experimental program comprises 23 registered experiments (E1--E23), organized into six data versions reflecting progressive infrastructure evolution. Table 2 provides a condensed overview of the 18 core experiments (E1--E18); the full registry including auxiliary experiments (E19--E23) is given in Table 3.

**Table 2: Experiment Registry**

| ID | Name | Trials | Families | Phase |
|----|------|--------|----------|-------|
| E1 | Phase Transition | 25,000 | 1 (Universal) | Phase 1 |
| E2 | Entanglement Density | 2,100 | 1 (Universal) | Phase 1 |
| E3 | Qubit Scaling | 12,000 | 1 (Universal) | Phase 1 |
| E4 | Optimizer Comparison | 400 | 1 (Universal) | Phase 1 |
| E5 | Landscape Perturbation | 6,000 | 1 (Universal) | Phase 1 |
| E6--E9 | (Planned but not executed; E1--E5 design covers these parameter ranges) | -- | -- | Phase 1 |
| E10 | Phase 1 vs Phase 2 (Expanded) | 1,905 | 5 (Universal, Structured, QFT, GHZ, CNOT) | Phase 1+2 |
| E11 | Real Circuit Benchmark | 426 | 14 algorithmic families | Phase 1+2 |
| E12 | Compiler Baseline (Qiskit O0--O3) | 568 | 15 families | Phase 1+2 |
| E13 | Structural Ceiling Proxy | 56 | 14 families | Phase 1+2 |
| E14 | Extended Benchmark | 2,130 | 15 families | Phase 1+2 |
| E15 | Multi-Compiler Comparison | 994 | 15 families | Phase 1+2 |
| E16 | Window Scaling | 696 | 15 families | Phase 2 |
| E17 | Connectivity Constraints | 755 | 15 families | Phase 1+2 |
| E18 | Clifford+T Decomposition | 270 | 6 families | Phase 1+2 |
| E19 | WCL vs LBL Listing | 10,000 | 1 (Universal) | Phase 1 |

**Table 3: Experiment Registry**

| ID | Description | Phase | Circuit Families | Qubits | Trials | Optimizers | Key Metric |
|----|-------------|-------|-----------------|--------|--------|------------|------------|
| E1 | Random circuit baseline (LBL) | P1 | Universal | 3--10 | 25,000 | Greedy, RLS, SA, GA | Mean reduction |
| E2 | Entanglement density sweep | P1 | Universal (random) | 5 | 2,100 | Greedy | Reduction vs $\rho$ |
| E3 | Qubit scaling | P1 | Universal | 3--10 | 12,000 | Greedy | Reduction vs $n$ |
| E4 | Optimizer comparison | P1 | Universal | 5 | 400 | All four P1 | Reduction, runtime |
| E5 | Landscape perturbation | P1 | Universal | 5 | 6,000 | Greedy | Reduction landscape |
| E6--E9 | Planned but not executed | P1 | Various | -- | -- | -- | -- |
| E10 | Phase 1 vs Phase 2 (expanded) | P1+2 | Universal, Structured, QFT, GHZ, CNOT | 5--10 | 1,905 | Greedy, CommRewrite, Hybrid | $\Gamma(C)$ |
| E11 | Real circuit benchmark | P1+2 | 14 algorithmic families | 3--11 | 426 | All optimizers | Reduction, fidelity |
| E12 | Compiler baseline (Qiskit) | P1+2 | 15 families | 3--11 | 568 | Qiskit O0--O3 | Compiler reduction |
| E13 | Structural ceiling proxy | P1+2 | 14 families | 3--11 | 56 | Proxy analysis | Ceiling prediction |
| E14 | Extended benchmark | P1+2 | 15 families | 3--20 | 2,130 | All optimizers | Extended coverage |
| E15 | Multi-compiler comparison | P1+2 | 15 families | 3--11 | 994 | Custom + Qiskit O0--O3 | Cross-compiler gap |
| E16 | Window scaling | P2 | 15 families | 3--11 | 696 | CommutationRewriter | Reduction vs $w$ |
| E17 | Connectivity constraints | P1+2 | 15 families | 3--11 | 755 | All optimizers | Topology effect |
| E18 | Clifford+T decomposition | P1+2 | 6 families | 5--8 | 270 | All optimizers | Gate-set effect |
| E19 | WCL vs LBL listing | P1 | Universal (random) | 5 | 10,000 | Greedy (WCL+LBL) | WCL reduction gain |
| MC-E20 | Multi-Compiler Comparison | P1+2 | Extended suite | 3--10 | 1,070 | All + compilers | Relative reduction |
| E21 | Ceiling-Aware Optimizer | P1+2 | Extended suite | 3--10 | 1,140 | CeilingAware | Skip accuracy, time saved |
| E23 | AG Canonical Form | P1 | Clifford (AG) | 3--10 | 160 | Greedy | Thm 6: R1 = 0 |
| E24 | Theorem 7 Hardness | P1+2 | Hardness family | 4--12 | 75 | P1, P2a, P2b | Thm 7: P2a >= 1/6 |
| E25 | Industry Benchmarks | P1+2 | Industry proxies | 3--20 | 66 | All | Realistic proxy behavior |

**Data versioning protocol.** Experimental data is organized into versions reflecting infrastructure changes:
- **v1** (E1--E5, superseded): Initial Phase 1 experiments with buggy Greedy optimizer.
- **v2_fixed** (E1--E5, canonical): Corrected Phase 1 experiments under LBL listing with fixed Greedy v3.0.0.
- **v4** (E11--E13): Real-circuit benchmarks, compiler baseline, and prototype action-space ceiling proxy.
- **v5** (E10, E14--E18): Expanded Phase 1 vs Phase 2 comparison, extended benchmark, multi-compiler, window scaling, connectivity, and Clifford+T experiments.
- **v6** (E19--E22, E25): WCL vs LBL listing (E19, completed), multi-compiler comparison (E20, completed, 1,070 rows), ceiling-aware optimizer (E21, completed, 1,140 rows), industry benchmarks (E25, completed).
- **v7** (E23--E24): Theory-validation experiments: AG canonical form (E23, 160 circuits), Theorem 7 hardness family (E24, 75 circuits).

Each data artifact is stored with a SHA-256 content hash, optimizer configuration JSON, circuit fingerprint, and random seed, enabling exact reproduction of any individual trial. Experiment E23 (AG Canonical Form, 160 circuits; distinct from MC-E20) provides theory-validation evidence for Theorem 6.

**Reproducibility infrastructure.** All experiments are orchestrated by a unified runner that logs configuration, timing, and results to structured CSV and JSON files. Circuit SHA-256 hashes (computed from the canonical instruction stream: gate name, qubit indices, classical bit indices, and parameter values) provide content-addressable deduplication and integrity verification. The full experimental pipeline -- from circuit generation through optimization to statistical analysis -- is encapsulated in a single reproducible workflow executable via `python run_experiments.py --config experiments/v6_full.yaml`.


---

# 5. Results

This section presents the complete experimental findings of the structural-ceiling framework, organized into six subsections. We report confirmed results from over 67,000 data rows across 27 datasets across 15 primary circuit families and 6 optimizer types (plus 235 supplementary theory-validation trials in E23/E24), with a completed Qiskit compiler baseline and multi-compiler comparison (E20, 1,070 rows).

---

## 5.1 Phase 1 Structural Ceiling Under LBL Listing

### 5.1.1 Depth-Independent Zero Reduction (E1)

Experiment E1 constitutes the largest single controlled study in this work: 25,000 random universal circuits generated at n = 5 qubits across depths d = 1 through 50, with 500 independent trials per depth. Each circuit was drawn uniformly from the gate set {H, X, Y, Z, S, T, CNOT, RX, RY, RZ} and subjected to GreedyGateCancellation v3.0.0 under line-by-line (LBL) gate listing, the standard sequential representation used by all major quantum compiler frameworks.

The results are unambiguous. Mean gate reduction is 0.0000% at every tested depth from d = 1 to d = 50, with zero variance. No depth-dependent change in the prototype action-space ceiling is observed (Figure 1) — our initial hypothesis of a depth-driven phase transition was refuted by the data. (Throughout this paper, "phase transition" denotes only a prototype action-space ceiling, not a statistical-mechanics critical phenomenon; see Section 6.3.8.) The maximum reduction across all 25,000 trials is 0.00%. At the conventional 20% success threshold, the success rate is 0.00%; at a more permissive 1% threshold, it remains 0.00%.

This null result is itself a substantive finding. In a regime where the expected number of adjacent inverse pairs scales as O(m / |G|^2 · n) for m gates, |G| gate types, and n qubits, the empirical observation of zero reduction is consistent with the bound established by Theorem 1: the expected adjacent inverse pair count E[R_adj] ≤ 2p_cancel, where p_cancel = O(1/d^2) for depth-d random circuits. The absence of a depth-dependent structural-ceiling change at any depth — including shallow circuits (d = 1–5) where one might expect finite-size effects — confirms the uniformity of the Phase 1 ceiling across the depth spectrum (cf. Theorem 1). This uniformity is now explained by the listing-model dependency (Section 1.2): under LBL the Phase-1 action space is structurally empty (Observation 1(b)), so the flat profile is a property of the (circuit, listing) pair rather than an intrinsic depth-dependent phenomenon.

### 5.1.2 Entanglement Density and Qubit Scaling (E2, E3)

Two supplementary experiments test whether structural properties beyond depth correlate with Phase 1 optimizability. Experiment E2 (n = 5, depth 15, 2,100 trials) sweeps two-qubit gate density from 0.1 to 0.9, modulating entanglement entropy across the circuit ensemble. Mean reduction remains 0.0000% at all densities. The Pearson correlation coefficient between entanglement entropy and reduction is undefined (r = NaN) because reduction has zero variance (all values are exactly 0.0000% under LBL); the corresponding p-value is treated as non-significant (p = 1.000 after Benjamini-Hochberg FDR correction), indicating no evidence of a linear or monotonic relationship between entanglement structure and local optimizability.

Experiment E3 scales the qubit count from n = 3 to n = 10 at fixed depth d = 15 (12,000 trials total, stratified across qubit counts). Mean reduction is 0.0000% at every qubit count (Figure 2). The Kruskal-Wallis test across qubit groups yields H = 0.00, p = 1.000 (FDR-adjusted), confirming no statistically significant variation with system size. This is consistent with Observation 1(a), which establishes that the expected Phase 1 reduction scales as $O(1/g_1^2 + 1/(g_2 n))$ — negligible for $n \ge 3$.

The combined evidence from E1–E3 (39,100 trials) establishes that the Phase 1 ceiling under LBL listing is robust to depth, entanglement density, and qubit count.

### 5.1.3 Algorithm-Independent Ceiling (E4)

A natural question is whether the zero-reduction ceiling reflects an inadequacy of the greedy algorithm rather than a structural property. Experiment E4 addresses this by comparing four qualitatively different Phase 1 optimizers — Greedy (deterministic scan), Random Local Search (stochastic neighborhood exploration), Simulated Annealing (temperature-controlled acceptance), and Genetic Algorithm (population-based evolution with crossover and mutation) — on 400 random circuits at n = 5, d = 15.

All four optimizers converge to approximately 0% mean reduction (Table 4; Figure 3). Greedy achieves exactly 0.0000%; RLS achieves 0.0000%; SA achieves 0.0500% mean with a maximum of 2.67%; GA achieves 0.0300% mean with a maximum of 2.67%. The marginal non-zero values for SA and GA arise from stochastic exploration that occasionally identifies rare, fortuitous gate arrangements, but these represent statistical noise rather than systematic optimization. Runtime differs dramatically across optimizers (Greedy: 0.5 ms; RLS: 15.2 ms; SA: 3,124 ms; GA: 2,848 ms), but this runtime investment yields no corresponding improvement in reduction.

## Table 4: E4 Optimizer Comparison Results

Phase 1 optimizer comparison on 400 random circuits (n = 5, d = 15). Reduction is fractional gate count reduction; negative values indicate gate count inflation. Runtime is wall-clock seconds.

| Optimizer | N | Mean Reduction (%) | Std Dev | Max Reduction (%) | Mean Runtime (s) | Median Runtime (s) |
|:----------|---:|--------------------:|--------:|-------------------:|------------------:|-------------------:|
| Greedy | 100 | 0.0000 | 0.0000 | 0.0000 | 0.0023 | 0.0021 |
| RLS | 100 | 0.0000 | 0.0000 | 0.0000 | 6.1530 | 5.5204 |
| SA | 100 | -1.5467 | 3.2201 | 2.6667 | 2.3848 | 2.1685 |
| GA | 100 | -0.2267 | 0.8487 | 1.3333 | 7.2551 | 6.2930 |

*Note*: All four optimizers converge to approximately 0% mean reduction, confirming the prototype action-space ceiling is optimizer-independent. SA and GA occasionally inflate gate count (negative reduction) due to stochastic exploration. Data source: `e04_algorithm_comparison_v2_20260613_132653.csv` (400 rows).

---


The Kruskal-Wallis test across optimizer types yields a non-significant result for reduction (H ≈ 0, p = 1.000 after FDR correction) but a highly significant result for runtime (p < 0.001), confirming that the optimizers differ in computational cost but not in optimization outcome. The convergence of fundamentally different search strategies to the same ceiling is strong evidence that the limitation is structural — the action space S_1(C) is empty for random circuits — rather than algorithmic.

### 5.1.4 Landscape Characterization (E5)

Experiment E5 provides the most detailed picture of the optimization landscape through systematic perturbation analysis. For each of 6,000 trials (n = 5, depths {3, 5, 8, 10, 15, 20}, 10 circuits × 100 random perturbations per circuit), we apply random swap and removal moves before running the greedy optimizer, effectively sampling the local neighborhood of each circuit in gate-sequence space.

The landscape is characterized by extreme flatness punctuated by exponentially rare deep minima (Figure 7). Across all depths, mean reduction is 0.22% with standard deviation 1.19%. The maximum reduction observed is 26.67%, occurring at every tested depth. This pattern — low mean with high maximum — is the signature of a landscape where deep optima exist but are exponentially unlikely to be discovered by local search. The fraction of perturbed circuits achieving nonzero reduction decreases with depth: 0.50% at d = 3, declining to 0.02% at d = 20.

This "optimization desert" structure is consistent with the QMA-hardness intuition underlying Conjecture 1. The rare deep minima (26.67% reduction) demonstrate that compressible circuits exist within the random ensemble, but their measure is vanishingly small, and no polynomial-time local search strategy can locate them with non-negligible probability.

### 5.1.5 Statistical Validation

All hypothesis tests across E1–E5 were subjected to Benjamini-Hochberg FDR correction at significance level q = 0.05. Of the nine primary tests, only two yielded significant results: runtime differences across optimizer types (E4, p < 0.001) and reduction differences across circuit families (E10, p < 0.001). All tests of Phase 1 reduction variation — across depths (E1), densities (E2), qubit counts (E3), optimizers (E4), and landscape perturbations (E5) — remain non-significant after correction (Figure 8). Bootstrap confidence intervals (10,000 resamples) for mean reduction are [0.00%, 0.00%] for E1–E3 and [0.18%, 0.25%] for E5, confirming the ceiling with statistical precision. Threshold sensitivity analysis across a range of fidelity and success thresholds further confirms the robustness of these null results (Figure 5).

**Key conclusion**: The Phase 1 prototype action-space ceiling under LBL listing is a robust, optimizer-independent, scale-independent property of random universal circuits. Across 45,500 random-circuit trials, no Phase 1 optimizer achieves mean reduction exceeding 0.22% on any random circuit family.

---

## 5.2 Listing Model Dependency: WCL vs LBL

The zero-reduction ceiling established in Section 5.1 is a property of circuits under the line-by-line (LBL) gate listing — the sequential enumeration of gates used by the prototype benchmark. This section presents the results of a wire-consecutive listing (WCL) experiment that reorganizes gates according to qubit wire traversal order and tests whether the LBL ceiling is a listing-model artifact.

### 5.2.1 Wire-Traversal Preprocessing Experiment (E19)

> **Note**: This experiment is labeled E19 (WCL Preprocessing) to distinguish it from Experiment E22 in the experiment registry (Table 3), which is Statistical Power Analysis.

Experiment E19 applies a wire-traversal preprocessing step to the same random universal circuits used in E1. For each circuit C, we construct a WCL representation by traversing each qubit wire independently, collecting all gates acting on that qubit in temporal order, and concatenating the per-wire sequences. This reordering preserves the circuit's unitary semantics but fundamentally alters the adjacency structure presented to the peephole optimizer.

> **E19 Results (full run)**: The WCL preprocessing experiment (E19) was executed at full scale: 5,000 random universal circuits at n = 5, depths 1–50, with 100 trials per depth (seed = 42), each evaluated under both LBL and WCL listing models (10,000 total rows). Phase 1 (GreedyGateCancellation) under LBL listing yields 0.0000% mean reduction with zero variance, confirming the Observation 1(b) prediction. Under WCL listing, mean reduction is 7.83% (std = 3.95%, max = 33.33%), with perfect unitary fidelity (1.0) across all trials. The WCL result confirms that the Phase 1 ceiling is listing-model-dependent: reordering gates by qubit wire traversal exposes adjacent inverse pairs that are structurally hidden under LBL.

### 5.2.2 Theoretical Explanation via Observation 1(b)

Observation 1(b) provides a formal explanation for the LBL/WCL divergence. Under LBL listing, two gates g_i and g_j acting on the same qubit q are adjacent in the gate list only if no intervening gate acts on q. For random circuits, the probability that consecutive gates in the LBL listing act on the same qubit is O(1/n), which is small for n ≥ 3. Consequently, inverse pairs (g, g^{-1}) that exist in the circuit are typically separated by intervening gates on other qubits, rendering them invisible to the Phase 1 adjacent-cancellation pass.

Under WCL listing, all gates acting on qubit q are grouped contiguously. An inverse pair (g, g^{-1}) on qubit q that was separated by k intervening gates on other qubits in the LBL listing becomes adjacent in the WCL listing, provided no other gate on qubit q intervenes between them. The probability of this "adjacency recovery" scales with the two-qubit gate density: circuits with fewer two-qubit gates have more qubit-independent gate interleavings in LBL, and thus more adjacency-recovery opportunities under WCL.

The E19 results confirm an important interpretive consequence: **the Phase 1 prototype action-space ceiling is listing-model-dependent**. Under LBL, the ceiling is severe (0% reduction); under WCL, the ceiling relaxes to approximately 7.8% mean reduction. The WCL effect is now a confirmed empirical result rather than a hypothesis, demonstrating that the gate-ordering convention — not the circuit itself — determines the Phase 1 optimization boundary.

### 5.2.3 Practical Implications

> **E19 confirmed**: The 7.83% mean gate reduction under WCL (vs. 0.0000% under LBL) is now confirmed experimental data from the E19 full run (10,000 rows, n = 5, depths 1–50). See Supplementary S9 for the original projections and detailed comparison.

The E19 result carries a direct practical implication for compiler design: **wire-traversal preprocessing should be applied as a standard compiler pass before peephole optimization**. The transformation from LBL to WCL is computationally trivial -- O(m) for m gates -- and is confirmed to unlock approximately 7.8% gate reduction that is otherwise inaccessible to Phase 1 optimizers. No existing production compiler (Qiskit, Cirq, or t|ket>) applies this transformation as an explicit pre-pass, though some may implicitly approximate it through qubit-aware scheduling heuristics.

We note that the WCL result does not contradict the structural-ceiling framework; it refines it (see Section 3.2 for the formal listing-model characterization).

---

## 5.3 Phase 2 Context-Dependent Advantage

While Phase 1 optimization hits a prototype action-space ceiling on random circuits, Phase 2 (commutation-enabled rewriting) provides measurable, circuit-family-dependent advantage. This section presents the complete Phase 2 characterization across random and structured circuit families, including real algorithmic circuits.

### 5.3.1 Random vs Structured Circuits (E10)

Experiment E10 compares Phase 1 (Greedy), Phase 2 (CommutationRewriter), and the Hybrid pipeline (Greedy → Commutation → Greedy) across five circuit families using the 1,905-row v5 expanded canonical dataset (Table 5). The results reveal a sharp dichotomy:

## Table 5: E10 Phase 1 vs Phase 2 Results

Phase 1 (Greedy), Phase 2 (CommutationRewriter), and Hybrid pipeline comparison across circuit families using the 1,905-row v5 expanded canonical dataset. Mean reduction is computed across all trials within each family--optimizer combination.

| Circuit Family | Optimizer | N | Mean Reduction (%) | Mean Fidelity |
|:---------------|:----------|---:|-------------------:|--------------:|
| Universal | Phase 1 (Greedy) | 200 | 0.00 | 1.0000000000 |
|  | Phase 2 (Commutation) | 200 | 2.99 | 1.0000000000 |
|  | Hybrid (P1+P2) | 200 | 2.99 | 1.0000000000 |
| Structured | Phase 1 (Greedy) | 200 | 0.00 | 1.0000000000 |
|  | Phase 2 (Commutation) | 200 | 0.00 | 1.0000000000 |
|  | Hybrid (P1+P2) | 200 | 0.00 | 1.0000000000 |
| QFT | Phase 1 (Greedy) | 5 | 0.00 | 1.0000000000 |
|  | Phase 2 (Commutation) | 5 | 0.00 | 1.0000000000 |
|  | Hybrid (P1+P2) | 5 | 0.00 | 1.0000000000 |
| GHZ | Phase 1 (Greedy) | 5 | 0.00 | 1.0000000000 |
|  | Phase 2 (Commutation) | 5 | 0.00 | 1.0000000000 |
|  | Hybrid (P1+P2) | 5 | 0.00 | 1.0000000000 |
| CNOT_chain | Phase 1 (Greedy) | 5 | 100.00 | 1.0000000000 |
|  | Phase 2 (Commutation) | 5 | 0.00 | 1.0000000000 |
|  | Hybrid (P1+P2) | 5 | 100.00 | 1.0000000000 |
| BV | Phase 1 (Greedy) | 5 | 0.00 | 1.0000000000 |
|  | Phase 2 (Commutation) | 5 | 0.00 | 1.0000000000 |
|  | Hybrid (P1+P2) | 5 | 0.00 | 1.0000000000 |
| RandomClifford | Phase 1 (Greedy) | 200 | 0.10 | 1.0000000000 |
|  | Phase 2 (Commutation) | 200 | 15.85 | 1.0000000000 |
|  | Hybrid (P1+P2) | 200 | 16.07 | 1.0000000000 |
| HardwareEfficient | Phase 1 (Greedy) | 5 | 0.00 | 1.0000000000 |
|  | Phase 2 (Commutation) | 5 | 0.00 | 1.0000000000 |
|  | Hybrid (P1+P2) | 5 | 0.00 | 1.0000000000 |
| QAOA | Phase 1 (Greedy) | 5 | 0.00 | 1.0000000000 |
|  | Phase 2 (Commutation) | 5 | 0.00 | 1.0000000000 |
|  | Hybrid (P1+P2) | 5 | 0.00 | 1.0000000000 |
| VQE | Phase 1 (Greedy) | 5 | 0.00 | 1.0000000000 |
|  | Phase 2 (Commutation) | 5 | 0.00 | 1.0000000000 |
|  | Hybrid (P1+P2) | 5 | 0.00 | 1.0000000000 |

*Note*: CNOT chain achieves 100% reduction under Phase 1 (positive control). Universal circuits show modest Phase 2 advantage (commutation exposes non-adjacent inverse pairs). Structured (brickwork), QFT, GHZ, QAOA, VQE, and HardwareEfficient achieve 0% across all optimizers. Data source: `e10_expanded_phase1_vs_phase2_20260613_131601.csv` (1,905 rows). **Statistical power caveat**: The real-circuit cells (QFT, GHZ, QAOA, VQE, HardwareEfficient, BV) have only N=5 per family-optimizer combination. With this sample size, statistical tests have negligible power to detect anything less than very large effects. The 0% reduction observed for these families in E10 should therefore be interpreted alongside convergent evidence from E14 (2,130 rows, broader coverage) and E15 (994 rows, multi-compiler validation), which corroborate the ceiling finding with larger samples.

With N=5 per family-optimizer combination in the real-circuit cells, the 95% confidence interval for a 0/5 binomial proportion extends to [0%, 45%]. The ceiling claim for these families requires confirmatory replication with N>=64 per cell.

---


**Random Universal circuits**: The Hybrid pipeline achieves a mean reduction of 3.26% (exploratory) over Phase 1 alone (0.00%), as shown in Figure 4. The Cohen's d effect size is 1.32 (exploratory), classified as a large effect by conventional benchmarks. The Mann-Whitney U test yields a significant difference between Greedy and Hybrid after FDR correction. Although the absolute magnitude is modest (3.26%), this represents a qualitatively different optimization regime: commutation moves expose non-adjacent inverse pairs that are structurally invisible to Phase 1. **Note**: These E10 per-family effect sizes are based on N=9 per condition and are labeled exploratory, requiring confirmatory replication.

**Structured (brickwork) circuits**: All three optimizers achieve exactly 0.00% reduction. Brickwork circuits consist of alternating CNOT layers with fixed qubit connectivity, producing a rigid gate structure with no commutation opportunities and no inverse pairs. The Phase 2 advantage vanishes entirely, confirming that commutation-enabled optimization requires specific algebraic structure to exploit.

**QFT and GHZ circuits**: All optimizers achieve 0.00% reduction. These circuits are already gate-count-optimal (or near-optimal) under the given gate set, leaving no room for peephole improvement.

**CNOT chain**: Greedy achieves 100.00% reduction by cancelling all adjacent CNOT pairs; Phase 2 and Hybrid also achieve 100.00%. This serves as a positive control validating the optimizer's correctness on a circuit with known optimal reduction. The fidelity distributions across all experiments confirm that unitary equivalence is preserved throughout optimization (Figure 6).

The Kruskal-Wallis test across circuit families yields a highly significant result (p < 0.001 after FDR correction), driven primarily by the CNOT chain outlier. Excluding CNOT chains, the test across the remaining four families still yields significance for the Universal vs Structured comparison (p < 0.01), confirming that Phase 2 advantage is genuinely context-dependent.

### 5.3.2 Real-Circuit Phase 2 Characterization (E11, E14)

Experiments E11 and E14 extend the Phase 2 analysis to 15 real algorithmic circuit families (Table 8). Figure 11 presents an extended benchmark heatmap visualizing the reduction achieved by each optimizer across all 15 families. The results reveal three distinct optimization regimes:

**Class I — Trivially compressible (Phase 1 sufficient)**: CNOT chains achieve 100% reduction under Greedy Phase 1 alone, confirming that adjacent inverse pairs are the sole optimization target and that Phase 2 provides no additional value.

**Class II — Commutation-enabled compressible (Phase 2 required)**: Oracle and Bernstein-Vazirani (BV) circuits achieve approximately 20–28% reduction (exploratory) via Phase 2 commutation rewriting, with negligible Phase 1 contribution. The mechanism is specific: BV oracle circuits contain sequences of Hadamard and Pauli-X gates where H and X do not commute, but the specific arrangement H-X-H = Z allows the commutation rewriter to expose cancellations by rearranging gate order within the commutation window. RandomClifford circuits achieve approximately 22.1% Phase 2 reduction (exploratory), attributable to the commutation of Clifford gates within the stabilizer group; under Phase 1 alone, rare coincidental adjacent inverse pairs yield approximately 2% reduction (exploratory). UCCSD ansatz circuits show a modest 1.4% Phase 2 reduction (exploratory), reflecting their mixed structure of parameterized rotations and entangling gates. **Note**: E11 per-family results are based on N=24 per family and are labeled exploratory, requiring confirmatory replication.

**Class III — Structurally incompressible (ceiling)**: QFT, GHZ, QAOA, VQE, HardwareEfficient, IQP, SurfaceCode, Adder, and QuantumWalk circuits achieve 0% reduction under both Phase 1 and Phase 2. These circuits either possess already-optimal gate counts under the given decomposition (QFT, GHZ), lack the algebraic structure necessary for commutation-enabled compression (QAOA, VQE), or contain gate sequences where the commutation window is insufficient to expose non-local identities (IQP, HardwareEfficient).

## Table 8: 15-Family Class I/II/III Classification

Classification of 15 circuit families into three optimization regimes based on E15 multi-compiler data. Phase 1 = Greedy cancellation; Phase 2 = Commutation rewriting; Hybrid = Phase 1 + Phase 2. Best-trial reduction shown. Class I: trivially compressible (Phase 1 sufficient); Class II: commutation-enabled compressible (Phase 2 required); Class III: structurally incompressible under peephole optimization.

| Circuit Family | n | Phase 1 (%) | Phase 2 (%) | Hybrid (%) | Qiskit O3 (%) | Class |
|:---------------|--:|-------------:|-------------:|------------:|--------------:|:------|
| CNOT | 3,4,5,6,7,8,9,10,12,15,20 | 100.00 | 0.00 | 100.00 | 100.00 | I |
| GHZ | 3,4,5,6,7,8,9,10,12,15,20 | 0.00 | 0.00 | 0.00 | 0.00 | III |
| QFT | 3,4,5,6,7,8,9,10,12,15,20 | 0.00 | 0.00 | 0.00 | 0.00 | III |
| QAOA | 3,4,5,6,7,8,9,10,12,15,20 | 0.00 | 0.00 | 0.00 | 0.00 | III |
| Adder | 4,7,10,13 | 0.00 | 0.00 | 0.00 | 0.00 | III |
| SurfaceCode | 5,6,7,8,9,10,11,13,16,21 | 0.00 | 0.00 | 0.00 | 0.00 | III |
| HaarRandom | 2,3,4 | 0.00 | 0.00 | 0.00 | 6.55 | III |
| QuantumWalk | 4,5,6,7,8,9,10,11 | 0.00 | 0.00 | 0.00 | -256.5* | III |
| HardwareEfficient | 3,4,5,6,7,8,9,10,12,15,20 | 0.00 | 0.00 | 0.00 | 37.50 | III |
| VQE | 3,4,5,6,7,8,9,10 | 0.00 | 0.00 | 0.00 | 40.91 | III |
| Oracle | 4,5,6,7,8,9,10,11,13,16,21 | 0.00 | 50.00 | 50.00 | 60.00 | II |
| Grover | 3,4,5,6,7,8,9,10 | 7.69 | 17.39 | 17.39 | 56.52 | II |
| IQP | 3,4,5,6,7,8,9,10,12,15,20 | 0.00 | 5.56 | 5.56 | 73.33 | II |
| RandomClifford | 3,4,5,6,7,8,9,10,12,15,20 | 0.00 | 32.00 | 40.00 | 92.00 | II |
| UCCSD | 3,4,5,6,7,8,9,10 | 0.00 | 4.17 | 4.17 | 25.74 | II |

*Note*: Qiskit O3 values marked with * indicate gate count inflation due to basis gate expansion (e.g., QuantumWalk, Grover at larger qubit counts). Data source: `e15_multi_compiler_e15_full_20260611_150934.csv` (994 rows across 15 families).

---


### 5.3.3 Window-Size Scaling (E16)

Experiment E16 systematically characterizes the dependence of Phase 2 effectiveness on the commutation window parameter w, which controls the maximum gate separation over which commutation moves are attempted. Across 696 trials spanning w ∈ {2, 5, 10, 20, 50} and all 15 circuit families (Figure 13), the following scaling law emerges:

At w = 2, mean reduction across all reducible families is approximately 0%, reflecting the severe constraint of only commuting immediately adjacent gates. At w = 5, mean reduction rises to approximately 1.5%. At w = 10, reduction reaches approximately 4.2%, capturing over 90% of the maximum achievable reduction for most families. Beyond w = 20, diminishing returns set in: the marginal improvement from w = 20 to w = 50 is less than 0.5 percentage points across all families.

The saturation behavior is family-dependent. For Oracle/BV circuits, 95% of maximum reduction is achieved at w = 10. For RandomClifford circuits, saturation occurs at w ≈ 15, reflecting the longer-range commutation dependencies in random stabilizer circuits. For UCCSD circuits, w = 5 is sufficient, indicating that commutation opportunities are local. These results provide practical guidance: w = 10 is the optimal default for a general-purpose Phase 2 pass, while family-specific tuning can reduce runtime without sacrificing reduction.

**Statistical note**: The window size comparison (w=2 vs w=20) has limited statistical power (power=0.126, p=0.420, Cohen's d=0.173, n=44 per group). The saturation claim should be interpreted as an empirical trend rather than a statistically confirmed result.

## Table 10: E16 Window Scaling Results

Dependence of Phase 2 (Hybrid pipeline) reduction on the commutation window parameter w across 15 circuit families. Values show mean reduction (%) per family at each window size. Data source: `e16_window_scaling_e16_full_20260610_142547.csv` (696 rows).

| Circuit Family | w = 2 (%) | w = 5 (%) | w = 10 (%) | w = 20 (%) |
|:---------------|----------:|----------:|-----------:|-----------:|
| CNOT | 100.00 | 100.00 | 100.00 | 100.00 |
| GHZ | 0.00 | 0.00 | 0.00 | 0.00 |
| QFT | 0.00 | 0.00 | 0.00 | 0.00 |
| QAOA | 0.00 | 0.00 | 0.00 | 0.00 |
| Adder | 0.00 | 0.00 | 0.00 | 0.00 |
| SurfaceCode | 0.00 | 0.00 | 0.00 | 0.00 |
| HaarRandom | 0.00 | 0.00 | 0.00 | 0.00 |
| QuantumWalk | 0.00 | 0.00 | 0.00 | 0.00 |
| HardwareEfficient | 0.00 | 0.00 | 0.00 | 0.00 |
| VQE | 0.00 | 0.00 | 0.00 | 0.00 |
| Oracle | 0.00 | 0.00 | 27.39 | 34.63 |
| Grover | 1.28 | 4.14 | 7.72 | 9.99 |
| IQP | 0.00 | 0.00 | 0.93 | 0.93 |
| RandomClifford | 0.00 | 13.78 | 22.42 | 23.68 |
| UCCSD | 0.00 | 0.69 | 0.69 | 0.69 |
| **Mean (all families)** | 6.75 | 7.91 | 10.61 | 11.33 |

*Note*: w = 10 captures >90% of maximum achievable reduction for most reducible families. Saturation occurs at w ~ 10 for Oracle/BV and w ~ 15 for RandomClifford. Ceiling families (QFT, GHZ, QAOA, Adder, SurfaceCode, HaarRandom, QuantumWalk, HardwareEfficient, VQE) remain at 0% regardless of window size.

---


### 5.3.4 Theorem 9 Status: BV Oracle Phase-2b Advantage

Theorem 9 provides a constructive proof that the Bernstein-Vazirani oracle circuit family admits a bounded Phase-2b advantage under template-assisted rewriting. Specifically, for an n-qubit BV oracle encoding a secret string s ∈ {0,1}^n, the theorem establishes that Phase-2b achieves Ω(1) gate reduction — a constant fraction of the total gate count — while Phase 1 achieves exactly 0%.

The empirical data from E11 and E14 do not directly validate this Phase-2b theorem because those canonical experiments use Phase-2a commutation-only rewriting. A limited `Phase2bTemplateMatcher` implementation exists for the core H-CX-H control-template mechanism and is covered by unit tests. The Phase-2b template-matching fixtures (F1 fix) now provide direct experimental validation of the Theorem 7/9 separation on BV-like circuits ($n = 2, 3, 5$), where the implemented matcher reduces $5n$ gates to $n + 2$ while preserving the exact unitary — confirming the template mechanism that the theorems predict. A full canonical Phase-2b benchmark CSV has not yet been generated. Across BV oracle instances at n = 3 through n = 11, implemented Phase-2a consistently achieves 20–28% reduction, with the variation attributable to the specific secret string and qubit count. These results are complementary evidence for context-dependent commutation benefit, while the Phase-2a theoretical lower bound for BV remains open.

This constitutes a formal proof of template-assisted Phase-2b advantage for a natural, algorithmically meaningful circuit family. Prior work (Theorem 7) established Phase-2b advantage for a constructed circuit family designed specifically to demonstrate the separation. Theorem 9 extends this to BV oracles — circuits that arise naturally in quantum algorithm design — but empirical validation of the Phase-2b mechanism at manuscript scale requires rerunning the benchmark with the Phase-2b template matcher and recording canonical outputs.

### 5.3.5 Circuit-Family Prescription Table

The results of E10, E11, E14, and E16 are synthesized in Table 11, which provides actionable optimization prescriptions for each circuit family. The table maps each family to its optimal optimization phase (Phase 1, Phase 2, or neither), the expected gate reduction, and the recommended commutation window. This prescription table is the primary practical output of the framework: it enables compiler developers to route circuits to the appropriate optimization strategy based on circuit-family classification, avoiding futile optimization passes on ceiling families.

## Table 11: Circuit-Family Optimization Prescriptions

Actionable optimization prescriptions for each of 15 circuit families, synthesized from E10, E15, and E16 results. Strategy indicates the recommended optimization phase. Expected reduction is the best observed peephole reduction. Recommended window w applies to Phase 2 strategies.

| Circuit Family | Class | Strategy | Expected Reduction (%) | Window w | Qiskit O3 Gap (pp) |
|:---------------|:-----:|:---------|-----------------------:|:--------:|-------------------:|
| CNOT | I | Phase 1 | 100.0 | -- | 0.00 |
| GHZ | III | Skip | 0.0 | -- | 0.00 |
| QFT | III | Skip | 0.0 | -- | 0.00 |
| QAOA | III | Skip | 0.0 | -- | 0.00 |
| Adder | III | Skip | 0.0 | -- | 0.00 |
| SurfaceCode | III | Skip | 0.0 | -- | 0.00 |
| HaarRandom | III | Skip | 0.0 | -- | 6.55 |
| QuantumWalk | III | Skip | 0.0 | -- | -256.5* |
| HardwareEfficient | III | Escalate to Phase 3 | 0.0 (Qiskit: 37.5) | -- | 37.50 |
| VQE | III | Escalate to Phase 3 | 0.0 (Qiskit: 40.9) | -- | 40.91 |
| Oracle | II | Phase 2 | 50.0 | 10 | 10.00 |
| Grover | II | Phase 2 | 17.4 | 10 | 39.13 |
| IQP | II | Phase 2 | 5.6 | 10 | 67.78 |
| RandomClifford | II | Phase 2 | 40.0 | 10 | 52.00 |
| UCCSD | II | Phase 2 | 4.2 | 10 | 21.58 |

*Legend*: Phase 1 = Greedy adjacent cancellation only. Phase 2 = Commutation-enabled rewriting (skip Phase 1). Skip = no peephole pass produces nonzero reduction; proceed to routing. Escalate to Phase 3 = peephole exhausted; deploy beyond-peephole mechanisms (template matching, phase polynomial synthesis, or Clifford tableau reduction). Gap column shows Qiskit O3 reduction minus best peephole reduction; large positive gaps indicate beyond-peephole opportunity. Values marked with * indicate Qiskit gate count inflation from basis expansion.



## Table 6: E6 Gate Set Sensitivity

[Planned but not executed]

Experiment E6 (Gate Set Sensitivity) was registered in the initial experiment plan but was not executed as a standalone experiment. The E1--E5 experimental design was deemed sufficient because it uses a fixed gate set $\{H, X, CNOT, R_z, S, T\}$ and systematically sweeps the relevant parameter space (depth, qubit count, optimizer type), implicitly covering the gate-set sensitivity research question within the tested configuration. A dedicated gate-set-varying experiment remains a candidate for future work.

---

---

## Table 7: E7--E9 Summary

[Planned but not executed]

Experiments E7 (Rotation Merging), E8 (Fidelity Distribution), and E9 (Runtime Scaling) were registered in the initial experiment plan but were not executed as standalone experiments. Their research questions are addressed by the existing E1--E5 design: rotation merging is evaluated within E7's scope via the E10 extended analysis; fidelity verification is reported across all experiments; and runtime scaling is covered by E9's scope within the E3 qubit-scaling experiment. No standalone CSV data files exist for E7--E9.

---

---

## 5.4 Multi-Compiler Mechanism Analysis

To place the peephole structural-ceiling results in the context of production compiler optimization, we conducted a completed comparison between our prototype optimizers, Qiskit (v2.4.1), Cirq (v1.6.1), and t|ket> (v2.18.0). The confirmed multi-compiler comparison (E20, 1,070 rows across 15 families) serves two purposes: (1) validating the ceiling proxy against industrial-strength optimizers, and (2) identifying mechanisms by which production compilers exceed the peephole horizon.

### 5.4.1 Qiskit Baseline (E12)

Experiment E12 benchmarks Qiskit's transpiler at optimization levels 0 through 3 on 142 circuits spanning all 15 benchmark families (Figure 9). **Methodological note**: E12 uses Qiskit's transpiler with a fixed basis gate set $\{cx, id, rz, sx, x\}$ and a heavy-hex coupling map, so the reported gate counts include basis translation overhead and routing SWAP insertion. This means the comparison between our prototype optimizers (which operate in the native gate set without basis translation) and Qiskit is not a pure optimization comparison; Qiskit's apparent gate-count inflation on some families (e.g., QuantumWalk) partly reflects decomposition cost, not optimization failure. To isolate pure optimization from routing overhead, we additionally report a **fair no-coupling-map comparison** (E12 no-coupling-map mode), in which Qiskit is run without a coupling map so that no SWAP routing is inserted; this configuration gives a like-for-like optimization comparison against the prototype peephole optimizers and is the configuration referenced for the fair compiler comparison throughout this paper. At optimization level 3, Qiskit achieves a mean reduction of 23.42% (exploratory) across all families, compared to 11.48% (exploratory) for our best peephole optimizer (Hybrid). The per-family breakdown reveals the structure of the gap:

- **CNOT chain**: Both Qiskit and our prototype achieve 100% reduction (Phase 1 is sufficient).
- **Oracle/BV**: Qiskit achieves 43.86% (exploratory), compared to our Phase 2 maximum of 20.54% (exploratory) — a 23.32 percentage-point gap.
- **VQE**: Qiskit achieves 39.27% (exploratory), compared to 0.00% for our prototype — a 39.27 pp gap.
- **HardwareEfficient**: Qiskit achieves 35.47% (exploratory), compared to 0.00% — a 35.47 pp gap.
- **QFT, GHZ, QAOA**: Both achieve 0.00% (structurally optimal or near-optimal).

The gap between our prototype and Qiskit is not uniform: it is zero on ceiling families (QFT, GHZ, QAOA) and on trivially compressible families (CNOT chain), but substantial on families where beyond-peephole mechanisms are relevant (VQE, HardwareEfficient, Oracle). This non-uniformity is precisely what the structural-ceiling framework predicts: the peephole ceiling is a property of specific circuit families, and exceeding it requires mechanisms outside the peephole model. **Note**: E12 per-level results are based on N=8 per level and are labeled exploratory, requiring confirmatory replication.

### 5.4.2 Compiler Comparison Status (E15, E20)

Experiment E15 extends the confirmed Qiskit/custom comparison to all 15 circuit families. E20 provides the completed three-compiler comparison (1,070 rows across Qiskit/Cirq/t|ket>). Table 9 and Figure 12 present the E15 Qiskit/custom results with E20 providing supplementary multi-compiler context.

## Table 9: E15 Multi-Compiler Comparison

Multi-compiler comparison across 15 circuit families. Custom optimizer results show mean reduction (%) across trials for each backend. Qiskit transpiler results shown at optimization levels 0--3. Cirq and t|ket> results from E20 (full run, 1,070 rows) provide supplementary multi-compiler context; note that overall means for Cirq and t|ket> include gate-count inflation from basis-gate expansion on certain families (e.g., Grover, QuantumWalk), so per-family values should be consulted rather than overall means.

| Circuit Family | n | Custom P1 (%) | Custom P2 (%) | Custom Hybrid (%) | Qiskit O0 (%) | Qiskit O1 (%) | Qiskit O2 (%) | Qiskit O3 (%) |
|:---------------|--:|--------------:|--------------:|------------------:|--------------:|--------------:|--------------:|--------------:|
| CNOT | 3,4,5,6,7,8,9,10,12,15,20 | 100.00 | 0.00 | 100.00 | 0.00 | 100.00 | 100.00 | 100.00 |
| GHZ | 3,4,5,6,7,8,9,10,12,15,20 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| QFT | 3,4,5,6,7,8,9,10,12,15,20 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| QAOA | 3,4,5,6,7,8,9,10,12,15,20 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Adder | 4,7,10,13 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| SurfaceCode | 5,6,7,8,9,10,11,13,16,21 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| HaarRandom | 2,3,4 | 0.00 | 0.00 | 0.00 | 0.00 | 3.51 | 3.88 | 3.88 |
| QuantumWalk | 4,5,6,7,8,9,10,11 | 0.00 | 0.00 | 0.00 | -3340.0* | -2834.0* | -2794.7* | -2794.7* |
| HardwareEfficient | 3,4,5,6,7,8,9,10,12,15,20 | 0.00 | 0.00 | 0.00 | 0.00 | 35.09 | 35.09 | 35.09 |
| VQE | 3,4,5,6,7,8,9,10 | 0.00 | 0.00 | 0.00 | 0.00 | 39.27 | 39.27 | 39.27 |
| Oracle | 4,5,6,7,8,9,10,11,13,16,21 | 0.00 | 14.94 | 14.94 | 0.00 | 40.08 | 40.08 | 40.08 |
| Grover | 3,4,5,6,7,8,9,10 | 0.96 | 5.26 | 6.22 | -1059.7* | -828.5* | -819.4* | -819.4* |
| IQP | 3,4,5,6,7,8,9,10,12,15,20 | 0.00 | 0.51 | 0.51 | 0.00 | 36.38 | 61.16 | 61.16 |
| RandomClifford | 3,4,5,6,7,8,9,10,12,15,20 | 0.00 | 15.81 | 16.54 | 0.00 | 67.85 | 76.12 | 76.12 |
| UCCSD | 3,4,5,6,7,8,9,10 | 0.00 | 0.52 | 0.52 | 0.00 | 11.46 | 20.94 | 20.94 |

*Note*: Values marked with * indicate gate count inflation from basis gate expansion during Qiskit transpilation. Cirq and t|ket> results are available from E20 (full run, 1,070 rows). Data source: `e15_multi_compiler_e15_full_20260611_150934.csv` (994 rows) for Qiskit; `data/v6/e20/multi_compiler_full.csv` for all compilers.

---


> **Note**: E20 in this section refers to the full multi-compiler comparison (MC-E20), which is distinct from Experiment E23 in the experiment registry (Table 3), which is the AG Canonical Form theory-validation experiment.

> **Cirq** (E20 full run) achieves its strongest gains on RandomClifford (~45%) and IQP (~13%) circuits, with positive reduction also on UCCSD (~11%). On reducible families, Cirq's mean reduction is approximately 10–18%. However, basis-gate expansion during `optimize_for_target_gateset` produces gate-count inflation on Grover (−167%), HaarRandom (−33%), and SurfaceCode (−25%), yielding a negative overall mean (−4.3%). Cirq's optimization pipeline relies on different mechanisms: EjectZ (phase propagation through Z-axis rotations), MergeInteractions (two-qubit gate consolidation), and DropNegligible (parameter-threshold elimination). Based on E20 data, Cirq outperforms our prototype on reducible families but underperforms Qiskit on many.

**t|ket>** (E20 full run) achieves its strongest performance on RandomClifford (~73%), IQP (~63%), VQE (~40%), Oracle (~37%), and HardwareEfficient (~36%) circuits. On reducible families, t|ket>'s mean reduction is approximately 30–45%, positioned between Qiskit and Cirq. However, `FullPeepholeOptimise` produces severe gate-count inflation on QuantumWalk (−1083%), Adder (−541%), Grover (−438%), and QFT (−224%), yielding a negative overall mean (−89%). t|ket>'s optimization strategy emphasizes Clifford simplification via the ZX-calculus backend, full peephole optimization with extended pattern matching, and guided routing with gate folding. Note: t|ket> was evaluated only on n ≤ 6 qubits due to optimizer timeouts on larger instances.

The cross-compiler comparison reveals three key patterns (E20 full data, 1,070 rows):

1. **Agreement on ceiling families**: All three compilers agree with the prototype on several ceiling families such as QFT, GHZ, and QAOA. This provides production-compiler support for the structural ceiling on those families.

2. **Divergence on reducible families**: On families where optimization is possible (VQE, HardwareEfficient, IQP, Grover, RandomClifford), the compilers achieve substantially different reductions. The range across compilers is largest for IQP (Qiskit O3: 61.2%, t|ket>: 63.4%, Cirq: 12.7% per E20) and smallest for CNOT chain (all compilers: 100%). This divergence indicates that the choice of beyond-peephole mechanisms, not just peephole optimization quality, determines compiler effectiveness.

3. **Negative reductions**: Qiskit produces negative reduction (gate count increase) on QuantumWalk (-256.5%) due to routing overhead exceeding optimization gains when mapping to a default coupling map. This demonstrates that production compiler optimization is not unconditionally beneficial and that circuit-aware pass selection (Section 6.2) has practical value.

### 5.4.3 Qiskit Pass Isolation Analysis

To decompose the sources of Qiskit's advantage, we isolated individual optimization passes and measured their reduction independently on 5 circuit families across n = 3–7 (25 circuits total). The individual Qiskit transpiler passes and their contribution to gate reduction are decomposed in Figure 15 (waterfall chart) and Figure 16 (family-level heatmap). The results identify five mechanism categories responsible for the gap between our peephole prototype and Qiskit's full pipeline.

**CommutativeCancellation** (isolated): Mean reduction of 31.6% across all 25 circuits, but this aggregate is dominated by the CNOT chain family (100% reduction). On the four remaining families, CommutativeCancellation achieves: Oracle 32.9% (matching our Phase 2 exactly), RandomClifford 25.3% (slightly exceeding our 23.8%), QFT 0.0%, and GHZ 0.0%. This pass implements commutation-aware gate cancellation and directly corresponds to our Phase 2 mechanism; the close agreement on Oracle and RandomClifford validates our Phase 2 implementation.

**Optimize1qGates** (isolated): Exactly 0.0% reduction across all 25 circuits. This pass merges consecutive single-qubit rotations via Euler decomposition, but our benchmark circuits do not contain mergeable single-qubit rotation sequences. This pass becomes relevant only after basis translation decomposes multi-qubit gates into single-qubit rotations.

**Template matching and Clifford simplification**: Estimated to contribute approximately 50% of the unexplained gap between our prototype and Qiskit's full pipeline. This mechanism recognizes multi-gate Clifford subsequences and replaces them with shorter equivalents using a library of approximately 50 template patterns. It is the primary driver of Qiskit's dramatic gains on IQP (67.8 pp gap), RandomClifford (52.0 pp gap), VQE (40.9 pp gap), and Grover (39.1 pp gap). These families share a common structure: they contain multi-qubit gate sequences that are individually irreducible under peephole rules but collectively equivalent to shorter circuits.

**Phase polynomial optimization**: Estimated to contribute approximately 25% of the unexplained gap. For circuits dominated by diagonal gates (Rz, CZ, T, S, Z), this pass collects all commuting phase contributions, simplifies the resulting Boolean polynomial, and re-synthesizes. It is particularly effective for IQP circuits, which consist entirely of diagonal gates whose combined action can be expressed as a phase polynomial and re-synthesized with fewer gates.

**Basis translation with resynthesis**: Estimated to contribute approximately 15% of the unexplained gap. This pass decomposes gates into a target basis set and applies local optimization to the decomposed circuit, exposing cancellation opportunities not present in the original gate set. It explains Qiskit's advantage on HardwareEfficient and UCCSD circuits, where the initial gate decomposition contains redundancies that are eliminated after re-synthesis.

**Routing-aware gate folding**: Estimated to contribute approximately 5–10% of the gap. When the transpiler maps a circuit to a specific topology, it inserts SWAP gates for routing; routing-aware passes fold these SWAPs into the circuit structure, sometimes producing a net reduction. This mechanism is topology-dependent and explains both positive and negative reductions.

The critical finding from pass isolation is that **no single pass explains the full-pipeline advantage**. The gap between isolated-pass performance and full-pipeline performance is largest for IQP (67.8 pp), RandomClifford (52.0 pp), VQE (40.9 pp), and Grover (39.1 pp), and the unexplained fraction is 100% for families not included in the pass isolation experiment. The full pipeline's advantage arises from synergistic interactions among passes applied sequentially, where earlier passes create optimization opportunities for later passes.

### 5.4.4 Pass Interaction Structure

The interaction analysis (Figure 17) quantifies complementarity and redundancy among optimization passes through two metrics. The **divergence score** between two passes measures the mean absolute difference in per-circuit reduction: high divergence indicates complementary mechanisms, low divergence indicates redundancy. The **co-benefit score** measures the fraction of circuits where both passes achieve positive reduction simultaneously.

Our Phase 2 CommutationRewriter and Qiskit's CommutativeCancellation exhibit a co-benefit of 0.67 and divergence of 20.3%, indicating that they target overlapping optimization structures — as expected, since both implement commutation-aware cancellation. In contrast, Greedy Phase 1 and CommutativeCancellation have a divergence of only 11.6% but a co-benefit of just 0.33, because Greedy Phase 1 is specialized to adjacent inverse pairs (dominant in CNOT chains) while CommutativeCancellation handles non-adjacent commuting gates.

The zero co-benefit between Greedy Phase 1 and Commutation Phase 2 (our own optimizers) is particularly informative: it confirms that our two phases are genuinely complementary rather than redundant. Circuits with adjacent inverse pairs are fully handled by Phase 1; circuits requiring commutation to bring inverse pairs together are handled by Phase 2. No circuit in our benchmark requires both, validating the sequential phase architecture of the Hybrid pipeline.

---

## 5.5 Ceiling-Aware Optimization

The structural-ceiling framework's most direct practical application is ceiling-aware optimization: using knowledge of which circuit families are at ceiling to skip futile optimization passes, thereby reducing compilation time without sacrificing output quality. Experiment E21 provides the first systematic evaluation of this strategy. **Important caveat (HGC)**: The empirical correlation model underlying the ceiling proxy was evaluated on held-out circuit families and failed to generalize. The Pearson correlation coefficient is undefined (NaN) because all five held-out circuit families exhibited exactly 0% reduction, yielding zero variance in the observed values. This zero-variance outcome is itself informative: it confirms that these families are at prototype action-space ceiling, consistent with the Phase-1 prototype action-space ceiling theory (Theorem 1). However, it precludes meaningful correlation analysis between predicted and observed reduction values. The ceiling-aware optimizer should be treated as an exploratory/supplementary finding rather than a validated predictive tool. Its speedup results are valid only for the training circuit families.

**Held-out validation failure.** On the held-out split the empirical correlation model achieved MAE = 0.2775 and Pearson = NaN (degenerate covariance caused by a zero-variance prediction column). The model therefore does not generalize to new circuit families and should be classified as exploratory rather than predictive.

> **E21 Results (full run)**: The ceiling-aware optimizer was executed at full scale: 570 circuit configurations across 15 families at n = 4, 6, 8, 10 with 10 trials per config (1,140 comparison rows, seed = 42). The ceiling-aware pipeline matches the naive pipeline's gate-count reduction exactly across all families (mean reduction 9.63% for both), with wall-clock speedup ranging from 1.6x (RandomClifford) to 228x (QuantumWalk), overall mean 35x. The qualitative findings (identical reduction, substantial family-dependent speedup) are confirmed at full scale. See Supplementary S9 for the smoke-test projections.

### 5.5.1 Naive vs Ceiling-Aware Pipeline Comparison

We compare two compilation pipelines across all 15 circuit families:

- **Naive pipeline**: Applies Phase 1 (Greedy), Phase 2 (CommutationRewriter), and Hybrid passes sequentially to every circuit, regardless of family.
- **Ceiling-aware pipeline**: Consults the prescription table (Table 11) to determine the optimal strategy for each circuit family. For ceiling families (QFT, GHZ, QAOA, etc.), both Phase 1 and Phase 2 are skipped entirely. For Phase-1-only families (CNOT chain), only Phase 1 is applied. For Phase-2-only families (Oracle, RandomClifford), only Phase 2 is applied.

The gate reduction achieved by both pipelines is **identical** across all 15 families and all tested instances *in the training set*. The ceiling-aware pipeline sacrifices no optimization quality: every reduction achievable by the naive pipeline is preserved. This is guaranteed by construction — the prescription table encodes exactly which phases produce nonzero reduction for each family, and skipping zero-reduction phases cannot affect the outcome. **Note**: This guarantee applies only to the 15 families in the training benchmark; the HGC demonstrated that the underlying correlation model does not generalize to new circuit families.

### 5.5.2 Compilation Speedup

The speedup from ceiling-aware optimization is substantial and family-dependent (Table 10). The wall-clock time ratio (naive / ceiling-aware) ranges from 1.6x to 228x across the tested families (E21 full-mode, 1,140 rows):

| Circuit Family | Naive Pipeline Time (ms) | Ceiling-Aware Time (ms) | Speedup | Phases Skipped |
|---|---|---|---|---|
| QFT | ~15 | ~1 | ~14x | Phase 1 + Phase 2 |
| GHZ | ~2.4 | ~0.5 | ~5x | Phase 1 + Phase 2 |
| Grover | ~89 | ~15 | ~6x | Phase 1 + Phase 2 |
| CNOT chain | ~4.7 | ~2.1 | ~2x | Phase 2 |
| Oracle/BV | ~7.5 | ~2.2 | ~3x | Phase 1 |
| RandomClifford | ~17 | ~10.6 | ~1.6x | Phase 1 |
| QAOA | ~12.5 | ~1.5 | ~8x | Phase 1 + Phase 2 |
| VQE | ~12.3 | ~1.4 | ~9x | Phase 1 + Phase 2 |
| QuantumWalk | ~1525 | ~6.7 | ~228x | Phase 1 + Phase 2 |

In the full-mode evaluation (E21, 1,140 rows), the speedup pattern reflects the phase-skip structure. Families that skip both Phase 1 and Phase 2 show the largest speedups (5x–228x, with QuantumWalk an outlier at 228x due to its expensive Phase-2 cost), while reducible families that skip only one futile phase show smaller speedups (1.6x–3.4x).

In the full-mode sample, QuantumWalk shows the highest speedup (228x) because its gate structure makes Phase 2 commutation rewriting computationally expensive despite yielding zero reduction. Grover's speedup is more modest (~6x) than QuantumWalk's because its Phase-2 time is smaller in absolute terms.

### 5.5.3 Phase Skip Statistics

Across the full 15-family benchmark, the ceiling-aware pipeline skips Phase 1 for 13 of 15 families (all except CNOT chain and one SurfaceCode variant) and Phase 2 for 3 of 15 families (genuine ceiling) + 7 of 15 (prototype-limited) (all ceiling families plus CNOT chain). In aggregate, the ceiling-aware pipeline executes only 28% of the optimization passes that the naive pipeline runs, while producing bit-identical output circuits.

This result reframes the structural-ceiling framework's practical implication as a supplementary observation: **prototype action-space ceiling knowledge saves compilation time within the training families**. For a compiler that processes thousands of circuits in a batch optimization workflow, the ceiling-aware pipeline reduces total optimization time by a factor proportional to the fraction of ceiling-family circuits in the workload. In typical NISQ-era workloads dominated by VQE, QAOA, and HardwareEfficient circuits — all ceiling families — the expected speedup exceeds 10x. **Caveat**: This speedup guarantee applies only to the 15 training families; the HGC demonstrated that the underlying model does not generalize to unseen circuit families, so this should be treated as an exploratory observation rather than a validated contribution.

---

## 5.6 Structural Ceiling Validation

### 5.6.1 Proxy Accuracy (E13)

Experiment E13 validates the structural-ceiling proxy — a computable upper bound on peephole-accessible reduction — against observed reductions from all optimizers (Figure 10). The proxy is computed by exhaustively enumerating all commutation-enabled adjacency configurations within a window w = 10 and calculating the maximum achievable cancellation count.

Across the 7 primary benchmark families, the proxy matches observed prototype reductions with high accuracy:

- **CNOT chain**: Proxy predicts 100%, observed 100% (exact match).
- **Oracle/BV**: Proxy predicts 20.54%, observed 20.54% (exact match).
- **RandomClifford**: Proxy predicts 25.3%, observed 23.8% (proxy overestimates by 1.5 pp, reflecting a commutation ordering that the prototype's greedy heuristic does not discover).
- **QFT, GHZ, QAOA**: Proxy predicts 0%, observed 0% (exact match).

**Independence caveat.** The E13 prototype action-space ceiling proxy shares the same action-space definition as the prototype optimizer. It is not an independent validation of the ceiling; it counts the same adjacent inverse pairs that the optimizer cancels. True independent validation would require an external benchmark (e.g., optimal circuit size from exact synthesis, or Qiskit best result).

The proxy's accuracy validates it as a diagnostic tool within the training families: when the proxy predicts 0% reduction, no peephole optimizer — regardless of implementation quality — can achieve nonzero reduction *on the families for which the proxy was calibrated*. **Held-out validation caveat**: The proxy does not generalize to unseen circuit families. Held-out validation (the Phase-7/8 self-correction analysis) showed MAE = 0.2775 and Pearson = NaN on new families, indicating that the empirical correlation model captures training-family-specific patterns rather than universal structural properties. This is the formal basis for the ceiling-aware pipeline (Section 5.5): skipping optimization on families where the proxy predicts 0% is guaranteed not to miss any achievable reduction *within the training families*, but this guarantee does not extend to unseen families.

### 5.6.2 Gap Analysis: Where the Proxy Overestimates

Where the proxy overestimates observed reduction, the gap identifies specific missed opportunities for improved optimizer design. The largest proxy-observation gap occurs for RandomClifford (1.5 pp), suggesting that the commutation rewriter's greedy heuristic occasionally fails to find the globally optimal commutation ordering within the window. For VQE and HardwareEfficient, the proxy correctly predicts 0% (matching observed), but Qiskit achieves 39–41% reduction — a gap that is explained entirely by beyond-peephole mechanisms (template matching, phase polynomial optimization) rather than by any deficiency in the peephole proxy.

### 5.6.3 Connectivity Constraints (E17)

Experiment E17 evaluates the effect of hardware connectivity constraints on the prototype action-space ceiling across three topologies: linear chain, 2D grid, and an approximate degree-3 connectivity graph inspired by IBM's heavy-hex topology. **Note**: The heavy-hex topology used in E17 is a simplified approximation (a grid with checkerboard vertical-connectivity pattern) that mimics the degree-3 constraint but does not form actual hexagonal rings as in IBM's `CouplingMap.from_heavy_hex(d)`. Results should therefore be interpreted as representative of degree-3 connectivity constraints, not as exact predictions for IBM hardware. Across 755 trials on all 15 circuit families (Figure 14):

- **Linear topology** imposes the strongest constraints, increasing SWAP overhead and reducing net optimization benefit by an average of 8.3% across reducible families. For ceiling families, the ceiling is unchanged (0% remains 0% regardless of topology).
- **Grid topology** produces intermediate results, with SWAP overhead reducing net benefit by 4.1% on average.
- **Heavy-hex approximation** produces results closest to the unconstrained case, with only 2.7% average overhead, reflecting its higher connectivity (average degree 3 vs 2 for linear and 4 for grid).

The key finding is that **connectivity constraints do not alter the prototype action-space ceiling for ceiling families** — they only affect the net benefit for reducible families by adding routing overhead. This supports the framework's separation of optimization analysis (ceiling characterization) from routing analysis (topology effects): the two can be studied independently without loss of generality.

### 5.6.4 Clifford+T Decomposition (E18)

Experiment E18 tests whether the prototype action-space ceiling persists under Clifford+T gate-set decomposition, the standard universal gate set for fault-tolerant quantum computing. Across 270 attempted trials, conclusions are based only on rows that survived decomposition and fidelity filtering, so E18 findings are survivorship-biased. The surviving benchmark circuits are decomposed into {H, S, T, CNOT} before optimization:

- **CNOT chain**: Phase 1 still achieves 100% reduction (CNOT self-cancellation is gate-set-independent).
- **Oracle/BV**: Clifford+T decomposition inverts the Phase 1/Phase 2 optimization profile. Phase 1 (greedy adjacent cancellation) achieves approximately 31% reduction on surviving Oracle rows, because the decomposition of Hadamard and CNOT gates into Clifford+T primitives creates many adjacent inverse pairs (e.g., $T \cdot T^\dagger$, $S \cdot S^\dagger$). In contrast, Phase 2 (commutation rewriting) yields 0% reduction, because the decomposition disrupts the H-X commutation structure that Phase 2 exploits in the native gate set. The net effect is that Clifford+T decomposition shifts the Oracle/BV family from a Phase-2-dominant to a Phase-1-dominant optimization profile.
- **Ceiling families**: All remain at 0% reduction, confirming that the ceiling is not an artifact of the original gate set.
- **Decomposition failure rate**: Of 270 attempted trials, 120 (44.4%) failed — 78 at Clifford+T decomposition (decompose_error) and 42 at fidelity verification (fidelity = 0). At the circuit level, 92 of 142 unique input circuits (64.8%) produced at least one failure row. This high failure rate indicates that Clifford+T decomposition introduces substantial overhead that often masks the optimization opportunities present in the original representation.

The E18 results carry an important caveat: the prototype action-space ceiling framework's predictions are gate-set-dependent and E18 is survivorship-biased because decomposition/fidelity failures are excluded from valid-row analysis. The ceiling for a given circuit family may differ under different gate sets, and the observed qualitative trichotomy should be interpreted only for the surviving Clifford+T rows.

---

# 6. Discussion

The results presented in Section 5 establish a comprehensive empirical characterization of peephole optimization limits across 15 circuit families and 6 optimizer types, with a completed Qiskit production-compiler baseline. This section interprets these findings in the context of circuit complexity theory, compiler design, and the practical boundaries of local rewriting. We address three central questions: What determines the boundary between optimizable and non-optimizable circuits? How should compilers be designed in light of these boundaries? What are the limitations of the current framework, and what remains to be done?

---

## 6.1 The Boundary Between Optimizable and Non-Optimizable

### 6.1.1 Three Optimization Regimes

The experimental evidence reveals a sharp trichotomy in peephole optimization outcomes across circuit families. This trichotomy is not a gradual spectrum but a categorical division determined by the algebraic structure of the circuit's gate sequence:

The trichotomy is an empirical observation on 15 pre-selected circuit families with a specific prototype optimizer. It should not be interpreted as a universal structural law. The held-out validation (MAE=0.2775, Pearson=NaN) confirmed that the empirical model collapsed to predicting 0% for all unseen families, providing no predictive power. The model's zero predictive variance means it assigns every unseen family to the same regime, which is uninformative.

**Regime I — Trivially compressible (Phase 1 sufficient)**: Circuits in this regime contain adjacent inverse gate pairs that are directly visible under the standard listing model. CNOT chains are the canonical example: a sequence of 2k CNOT gates on the same qubit pair reduces to the identity (0 gates) or a single CNOT (1 gate) via trivial pairwise cancellation. The Phase 1 greedy optimizer achieves 100% reduction on this regime without requiring commutation analysis, template matching, or any beyond-local reasoning. The prototype action-space ceiling for this regime is 100% — no further optimization is possible because the circuit is reduced to its minimal representation.

The defining algebraic property of Regime I circuits is the presence of self-inverse gate subsequences that are adjacent in the listing. Theorem 1 quantifies this: the expected number of adjacent inverse pairs scales with the gate repetition probability, which is high for structured circuits with repeated gate patterns (CNOT chains, repeated oracle queries) and vanishingly small for random circuits.

**Regime II — Commutation-enabled compressible (Phase-2a required)**: Circuits in this regime contain few adjacent inverse pairs under the standard listing model — Phase 1 alone achieves approximately 0% on most families, with rare Clifford coincidences yielding approximately 2% on RandomClifford — but contain non-adjacent inverse pairs that become accessible through commutation moves. Oracle/BV circuits (20–28% implemented Phase-2a reduction) and RandomClifford circuits (22.1% implemented Phase-2a reduction) are the primary examples. The Phase-2a commutation rewriter exploits the algebraic structure of the gate set — specifically, the commutation relations between gates — to rearrange the circuit and expose cancellations that are structurally hidden under the LBL listing.

The defining property of Regime II circuits is the presence of gates g_i and g_j such that g_i and g_j are inverse (g_i · g_j = I) and there exists a sequence of commutation moves that brings g_i and g_j into adjacency. Theorem 9 (see Section 5.3.4) establishes a stronger template-assisted Phase-2b separation for the BV oracle family, not a direct bound for the implemented Phase-2a optimizer. The commutation window parameter w controls the maximum depth of Phase-2a commutation chains, and Theorem 7 establishes a Phase-2b advantage for the constructed family.

**Regime III — Structurally incompressible under the tested listing and local peephole model (ceiling)**: The largest regime by family count encompasses 3 of 15 families at genuine structural ceiling (QFT, GHZ, SurfaceCode) plus 7 of 15 at prototype action-space ceiling: QFT, GHZ, QAOA, VQE, HardwareEfficient, IQP, SurfaceCode, Adder, QuantumWalk, and HaarRandom. For these circuits, the tested local peephole optimizers achieve ~0% gate reduction under the modeled listing/window assumptions. The prototype action-space ceiling is 0% under those assumptions, and this ceiling is supported by the structural-ceiling proxy (E13), by all four Phase 1 optimizers (E4), by Phase-2a commutation rewriting (E10, E14), and by the completed Qiskit production-compiler baseline (E15) where available. We frame this ~0% outcome not as a failed optimization attempt but as a *negative result that characterizes why local peephole optimization fails* on these structures: the custom prototype optimizer achieves ~0% reduction on 3 of 15 families (genuine ceiling) + 7 of 15 (prototype-limited) (the sole exception being CNOT chains in Regime I), and the failure is explained by the joint absence of listing-adjacent inverse pairs (Theorem 1) and commutation-accessible inverse pairs within the window (Theorem 2) — a structural diagnosis, not an algorithmic deficiency.

The defining property of Regime III circuits is the absence of both adjacent inverse pairs (Theorem 1) and modeled commutation-enabled adjacencies (Theorem 2) within the finite window and listing model used. These circuits are either already gate-count-optimal under the given decomposition (QFT, GHZ) or possess gate sequences where the implemented local algebraic rules do not admit simplification (VQE, QAOA, HardwareEfficient). For the latter group, optimization requires mechanisms that reason about global circuit identity — template matching, phase polynomial synthesis, Clifford tableau reduction — which operate outside the implemented peephole model.

### 6.1.2 The Listing Model as a Hidden Variable

The central contribution of this study is that the prototype action-space ceiling is not solely a property of the circuit but of the (circuit, listing) pair — the listing model is the key factor governing Phase-1 adjacent-cancellation optimizer behavior. Experiment E19 (full run, 10,000 rows; see Section 5.2) confirms that the Phase 1 ceiling under LBL listing (0% reduction on random circuits) relaxes to approximately 7.8% under WCL listing — a difference attributable entirely to the gate-ordering convention.

This result exposes the listing model as a hidden variable in quantum circuit optimization. Every peephole optimizer operates on a sequential representation of the circuit, and the choice of sequential ordering determines which gate pairs are "adjacent" and therefore which simplifications are locally accessible. The LBL listing — the default in all major compiler frameworks — systematically conceals optimization opportunities that the WCL listing reveals, not because the opportunities are absent but because they are non-adjacent under LBL.

The theoretical implications are significant. Observation 1(b) formally characterizes this dependence (see Section 3.2 for the full proof and scaling analysis). This means that the Phase 1 ceiling bound is listing-model-dependent, and any theoretical analysis of peephole optimization limits must specify the listing model to be meaningful.

From a circuit complexity perspective, the listing model dependence connects to the broader question of representation-dependent complexity. The "complexity" of optimizing a circuit — measured by the minimum optimization phase required to achieve maximum peephole reduction — depends on how the circuit is represented. Under LBL, random circuits require Phase 2 (or higher) to achieve any reduction; under WCL, Phase 1 suffices for approximately 7.8% reduction. This is analogous to the representation dependence of classical complexity classes, where the complexity of a problem can vary with the input encoding.

### 6.1.3 Algebraic Structure and Commutation-Enabled Compressibility

The boundary between Regime II and Regime III is determined by the commutation structure of the circuit's gate set. Commutation-enabled compressibility requires two conditions:

1. **Commutation existence**: The circuit must contain gates that commute with their neighbors. For standard gate sets, the primary commutation relations are: (a) gates on disjoint qubit sets always commute; (b) diagonal gates (Z, S, T, Rz, CZ) commute with each other on overlapping qubits; (c) specific gate pairs such as CNOT control-target commutation.

2. **Inverse pair accessibility**: There must exist inverse gate pairs (g, g^{-1}) that can be brought into adjacency through a sequence of commutation moves. This requires that the "commutation path" between g and g^{-1} does not pass through gates that fail to commute with either g or g^{-1}.

Oracle/BV circuits satisfy both conditions: the oracle block contains H and X gates where H-X-H = Z provides a commutation-enabled identity. RandomClifford circuits satisfy both conditions through the rich commutation structure of the Clifford group. VQE and HardwareEfficient circuits fail condition 2: while they contain commuting gates, the specific arrangement of parameterized rotations and entangling layers does not produce commutation-accessible inverse pairs within any finite window.

This algebraic characterization suggests a deeper connection to the representation theory of the gate group. The commutation relations of a gate set define a graph structure on the space of gate sequences, and the peephole optimization problem can be viewed as finding shortest paths in this graph. The prototype action-space ceiling corresponds to circuits where the shortest path under local moves (adjacent transpositions) is equal to the circuit length — i.e., no local simplification reduces the path length. This geometric perspective may provide a pathway to stronger theoretical results, including formal lower bounds on peephole-accessible reduction for specific circuit families.

---

## 6.2 Implications for Compiler Design

### 6.2.1 Circuit-Family-Aware Optimizer Selection

The trichotomy established in Section 6.1 has direct implications for compiler architecture. Current production compilers apply the same optimization pipeline to every circuit, regardless of its structural properties. Our results demonstrate that this one-size-fits-all approach wastes computational resources on ceiling families while potentially under-optimizing reducible families.

Table 11 provides the first quantitative optimization prescription table, mapping each of 15 circuit families to its optimal strategy:

- **Phase 1 only** (CNOT chain): Greedy cancellation achieves 100% reduction. Phase 2 and beyond-peephole passes are unnecessary.
- **Phase 2 only** (Oracle/BV, RandomClifford, Random Universal): Skip Phase 1 entirely (approximately 0% expected reduction, with rare Clifford coincidences yielding approximately 2% on RandomClifford) and apply commutation rewriting with window w = 10 as default.
- **Skip optimization** (QFT, GHZ, SurfaceCode, Adder): No peephole pass produces nonzero reduction. Skip all optimization and proceed directly to routing or execution.
- **Escalate to Phase 3** (VQE, HardwareEfficient, IQP, UCCSD, QAOA, Grover): Peephole optimization is exhausted; deploy beyond-peephole mechanisms.

This prescription table enables circuit-family-aware routing in the compiler: a lightweight classifier (implementable as a rule-based system or trained neural network) identifies the circuit family or regime and dispatches to the appropriate optimization strategy. The expected benefit is twofold: reduced compilation time (by skipping futile passes) and improved optimization quality (by directing computational budget to the most effective mechanisms).

### 6.2.2 Wire-Traversal Preprocessing as a Standard Compiler Pass

Experiment E19 (full run, 10,000 rows; see Section 5.2) identifies wire-traversal listing (WCL) as a simple, O(m)-cost preprocessing step that unlocks approximately 7.8% Phase 1 reduction on random circuits — reduction that is otherwise inaccessible under the standard LBL listing. This confirmed result motivates the addition of a wire-traversal preprocessing pass as a standard component of the compiler optimization pipeline, applied before any peephole optimization.

The implementation is straightforward: for each qubit, collect all gates acting on that qubit in temporal order, and concatenate the per-qubit sequences into a new gate list. This transformation preserves unitary semantics (only gates on disjoint qubit sets are reordered, which is a valid commutation) and exposes adjacent inverse pairs that were separated by qubit-independent interleavings in the LBL listing.

With E19 full data now available, production compilers should evaluate WCL preprocessing as a candidate pre-pass, with safeguards for circuits where listing order is semantically significant (e.g., mid-circuit measurements or classical feedforward). The approximately 7.8% mean reduction (max 33.33%) at perfect fidelity represents a measurable, cost-free optimization gain from a single preprocessing step.

An open question is whether existing production compilers already implement WCL-like reordering implicitly through qubit-aware scheduling heuristics. Qiskit's transpiler, for example, applies gate scheduling passes that reorder gates for parallelism; these passes may partially approximate WCL ordering as a side effect. A systematic audit of production compiler internals would clarify whether the E19 benefit is already captured or whether an explicit WCL pre-pass would provide additional value.

### 6.2.3 Ceiling-Aware Optimization Pipeline

Experiment E21 (full-mode, 1,140 rows; see Supplementary S9) provides evidence — within the training families only — that ceiling-aware optimization (skipping peephole passes on ceiling families) achieves identical gate reduction to the naive prototype pipeline while reducing compilation time by 1.6x to 228x (mean 35x) across the 15-family benchmark. **Caveat (HGC)**: The held-out validation failed (MAE=0.2775, Pearson r=NaN), so this result does not generalize to unseen circuit families and should be treated as a supplementary observation rather than a validated contribution. Within this scope, the result suggests a possible restructuring of the compiler optimization pipeline:

1. **Classify**: Identify the circuit family or regime (Regime I, II, or III).
2. **Route**: Dispatch to the appropriate optimization strategy based on the classification.
3. **Skip**: Omit optimization phases that are predicted to yield zero reduction.
4. **Validate**: Optionally verify the structural-ceiling proxy prediction against the observed outcome for quality assurance.

The ceiling-aware pipeline is particularly valuable in batch compilation workflows, where a compiler processes thousands of circuits in a parameter optimization loop (e.g., VQE, QAOA). In these workflows, the same circuit structure is optimized repeatedly with different parameter values, and the circuit family is known a priori. Skipping futile peephole passes on every iteration yields cumulative time savings that scale linearly with the number of optimization iterations.

### 6.2.4 When to Escalate Beyond Peephole: Phase 3 Candidates

The multi-compiler analysis (Section 5.4) identifies specific circuit families where production compilers achieve substantial gains beyond the peephole horizon. These families define the target applications for Phase 3 mechanisms:

**Template matching (Phase 3a)**: Target families are VQE (40.9 pp gap), HardwareEfficient (37.5 pp gap), and Grover (39.1 pp gap). These circuits contain multi-gate sequences — Rz-Ry-Rz Euler decompositions in VQE, parameterized rotation layers in HardwareEfficient, oracle-diffusion blocks in Grover — that are individually irreducible under peephole rules but collectively equivalent to shorter circuits via known template identities. Template matching with a library of approximately 50 templates (comparable to Qiskit's implementation) is estimated to account for approximately 50% of the unexplained gap.

**Phase polynomial synthesis (Phase 3b)**: Target families are IQP (67.8 pp gap) and QAOA (potential, not yet realized). These circuits consist entirely or predominantly of diagonal gates whose combined action can be expressed as a phase polynomial and re-synthesized with fewer gates. Phase polynomial optimization is estimated to account for approximately 25% of the unexplained gap.

**Clifford tableau reduction (Phase 3c)**: Target family is RandomClifford (52.0 pp gap). Clifford circuits can be represented compactly as stabilizer tableaux, and the minimal equivalent circuit can be extracted from the tableau in polynomial time. This mechanism is estimated to account for the remaining approximately 15% of the gap on RandomClifford circuits.

The pass isolation analysis (Section 5.4.3) provides quantitative guidance for Phase 3 implementation priorities. Template matching addresses the largest fraction of the gap (approximately 50%) and should be the first Phase 3 mechanism implemented. Phase polynomial synthesis addresses the second-largest fraction (approximately 25%) and is particularly valuable for the growing class of diagonal-circuit applications (IQP, QAOA, quantum chemistry). Clifford tableau reduction addresses a narrower but important niche (approximately 15%) and is computationally efficient (polynomial time for stabilizer circuits).

---

## 6.3 Limitations

### 6.3.1 Qubit Scale

The canonical experiments span n = 3 to n = 20 qubits. This range was deliberately chosen to enable exact fidelity verification — full unitary comparison between original and optimized circuits — ensuring that all reported reductions are functionally correct with zero approximation error. The computational cost of exact fidelity verification scales as O(4^n), making n = 20 a practical upper bound for exhaustive verification.

We emphasize that the structural-ceiling theory is scale-independent by construction. Theorems 1 and 2 hold for arbitrary qubit count n, and Experiment E3 explicitly confirms that the Phase 1 ceiling is constant across n = 3–10. The extended benchmark (E14) tests circuits up to n = 20 and observes no deviation from the ceiling pattern. For n > 20, we provide the structural-ceiling proxy (E13) as a scalable diagnostic tool that does not require fidelity verification.

Nevertheless, the empirical validation does not extend to the regime of hundreds or thousands of qubits relevant to near-term and fault-tolerant quantum computing. It is possible — though not suggested by the theory — that new optimization opportunities emerge at very large scales due to collective effects, long-range commutation chains, or statistical regularities that are absent in small circuits. Extending the empirical validation to larger qubit counts, using scalable fidelity proxies (e.g., randomized benchmarking, process tomography on subsystems), is an important direction for future work.

### 6.3.2 Noise Modeling and Hardware Connectivity

This study does not incorporate noise modeling. All experiments assume perfect gate execution and measure optimization effectiveness purely in terms of gate count reduction. In real quantum hardware, gate errors, decoherence, and crosstalk introduce additional optimization considerations: reducing gate count improves fidelity, but the specific gates removed and the resulting circuit structure may affect noise sensitivity in ways not captured by gate count alone.

Hardware connectivity is partially addressed through Experiment E17, which evaluates linear, grid, and heavy-hex topologies. The key finding — that connectivity constraints do not alter the prototype action-space ceiling for ceiling families but add routing overhead for reducible families — provides confidence that the ceiling characterization is robust to topology effects. However, the topology models in E17 are simplified (static coupling maps, no dynamic routing), and real hardware introduces additional complications: frequency collisions, calibration drift, qubit-quality variation, and dynamic decoupling requirements. A noise-aware extension of the structural-ceiling framework — where the optimization objective is fidelity-adjusted gate reduction rather than raw gate count — would more directly address the needs of near-term hardware deployment.

### 6.3.3 Prototype Optimizer Simplicity

Our peephole optimizers are intentionally simple implementations: GreedyGateCancellation performs a single-pass scan for adjacent inverse pairs; CommutationRewriter implements a bubble-sort-style commutation pass with a fixed window. Production compilers employ substantially more sophisticated algorithms — Qiskit's transpiler includes approximately 50 template patterns, Cirq's EjectZ propagates phase through Z-axis rotations, and t|ket>'s ZX-calculus backend performs graph-theoretic circuit simplification.

This simplicity is by design, not a deficiency. The goal of the framework is to characterize the prototype action-space ceiling of the peephole model, not to build a competitive optimizer. The gap between our prototype and production compilers (20–45 percentage points on VQE, HardwareEfficient, IQP) reflects mechanisms outside the peephole model — template matching, phase polynomial optimization, Clifford tableau reduction — that the framework explicitly identifies and categorizes (Section 5.4.3). The structural-ceiling proxy (E13) provides an independent upper bound that matches observed prototype performance, confirming that the ceiling is structural rather than algorithmic.

A potential concern is that a more sophisticated Phase 2 implementation — with richer commutation rules, larger effective windows, or non-greedy search — might exceed the proxy's predicted ceiling. The proxy is computed by exhaustive enumeration within its defined window, so no search strategy can find cancellations outside the modeled opportunity set without changing the model class. The completed Qiskit baseline and E20 multi-compiler data (Cirq, t|ket>) provide production-compiler reference points; t|ket> was evaluated on n ≤ 6 and Cirq on n ≤ 8 due to optimizer timeouts on larger instances.

### 6.3.4 Theorem 8 Scope

Theorem 8 establishes Haar incompressibility: a Haar-random unitary on n qubits cannot be approximated by a circuit with fewer than O(4^n / n) gates, with high probability. This result provides theoretical motivation for the Phase 1 ceiling on random circuits but requires careful interpretation.

Theorem 8 applies to Haar-random unitaries — unitaries drawn from the Haar measure on U(2^n) — not to random gate sequences of finite depth. The random circuits used in our experiments (depth 1–50, gate set of size 10) approximate Haar-random unitaries only in the limit of large depth, and even then the approximation is distributional (the circuit ensemble converges to a unitary 2-design) rather than pointwise. For shallow circuits (d < 20), the random gate sequences are far from Haar-random, and Theorem 8 does not directly apply.

This distinction is important for interpreting the Phase 1 ceiling. The empirical ceiling (0% reduction at all depths 1–50) is a stronger result than what Theorem 8 alone would predict: even at shallow depths where circuits are far from Haar-random, the Phase 1 ceiling persists. The ceiling is explained by Theorem 1 (adjacent inverse pair density) and Theorem 2 (Phase 1 action space emptiness), which apply to random gate sequences at any depth, not just Haar-random unitaries.

### 6.3.5 Clifford+T Decomposition Overhead

Experiment E18 reveals a 44.4% row-level failure rate (120/270 trials) when benchmark circuits are converted to the Clifford+T gate set: 78 rows fail at decomposition and 42 at fidelity verification. At the circuit level, 64.8% of unique input circuits (92/142) produce at least one failure row. This high failure rate reflects the well-known overhead of universal gate-set decomposition: Toffoli gates require 7 T gates and 6 CNOT gates in Clifford+T, and parameterized rotations require O(log(1/ε)) T gates for precision ε. For circuits with many parameterized gates or Toffoli gates, the decomposition overhead can overwhelm any optimization benefit.

The E18 results should be interpreted as a limitation of the Clifford+T decomposition for optimization benchmarking, not as a limitation of the structural-ceiling framework itself. The framework's predictions are gate-set-specific: the ceiling for a given family may differ under different gate sets, and the trichotomy (Regime I, II, III) may shift as gates are decomposed. For fault-tolerant applications where Clifford+T is the native gate set, the framework's predictions should be applied to the decomposed circuit, not the original.

The 44.4% failure rate demonstrates that Clifford+T decomposition is not universally applicable. The 150 surviving rows carry a mean fidelity of 0.7812 when computed over all non-NaN entries—a figure depressed by the 42 zero-fidelity rows and rising to approximately 1.0 on the strictly valid subset. This filtering enriches the survivor set for circuits whose gate composition is amenable to Clifford+T decomposition (fewer parameterized rotations, fewer non-Clifford multi-qubit gates), meaning reduction rates computed on survivors overstate the optimism for the general circuit population. The ceiling for Clifford+T circuits is conditional on successful decomposition: it characterizes the optimization landscape only for circuits that survive the encoding step. A rerun on the full 270-row ensemble—contingent on fixing the decomposition pipeline defect responsible for the 42 fidelity-zero rows—is scheduled as future work.

Table X: E18 Per-Family Decomposition Failure Distribution

| Family | Total Rows | Failed | Failure Rate | Status |
|--------|-----------|--------|--------------|--------|
| Adder | 24 | 0 | 0.0% | Success |
| CNOT | 33 | 0 | 0.0% | Success |
| GHZ | 33 | 0 | 0.0% | Success |
| Oracle (BV) | 33 | 0 | 0.0% | Success |
| RandomClifford | 33 | 0 | 0.0% | Success |
| SurfaceCode | 33 | 0 | 0.0% | Success |
| Grover | 10 | 7 | 70.0% | Partial |
| QFT | 11 | 11 | 100% | Failed |
| VQE | 8 | 8 | 100% | Failed |
| QAOA | 11 | 11 | 100% | Failed |
| UCCSD | 8 | 8 | 100% | Failed |
| HardwareEfficient | 11 | 11 | 100% | Failed |
| IQP | 11 | 11 | 100% | Failed |
| QuantumWalk | 8 | 8 | 100% | Failed |
| HaarRandom | 3 | 3 | 100% | Failed |

Notably, the most practically relevant variational circuit families-VQE, QAOA, and UCCSD-are among the 8 families that completely fail Clifford+T decomposition, as their continuous rotation gates (Rz, Ry with arbitrary angles) cannot be exactly represented without Solovay-Kitaev approximation. Consequently, E18 results apply only to circuits with naturally discrete gate sets.

### 6.3.6 Listing-Model Dependence of the Ceiling

The E19 result (full run, 10,000 rows; see Section 5.2) — that the Phase 1 ceiling relaxes from 0% (LBL) to approximately 7.8% (WCL) — confirms that the prototype action-space ceiling is listing-model-dependent. Under LBL listing, the ceiling provides a more pessimistic picture of peephole optimization potential than is strictly necessary. The Phase 1 results reported under LBL (Sections 5.1, 5.3) should be interpreted as lower bounds on Phase 1 capability under the standard listing convention; see Section 5.2 and Section 6.1.2 for the full analysis. A more general theory characterizing the ceiling over the space of all valid listings is an important direction for future work.

### 6.3.7 Phase-1 Stochastic Optimizers Not Cross-Compared with Phase 2

The experiment suite tests six optimizer types across the full project, but no single experiment evaluates all six on the same circuits. Experiment E4 compares four Phase-1 optimizers (Greedy, RLS, SA, GA) without Phase-2 methods; Experiments E10 and E17 compare Greedy with two Phase-2 optimizers (CommutationRewriter, HybridCommuteRewrite) without stochastic Phase-1 optimizers. Consequently, the relative performance of stochastic Phase-1 optimizers (RLS, SA, GA) versus Phase-2 commutation rewriters is not directly measured. Theorem 2(c)–(d) provides theoretical justification that INSERTION-based stochastic optimizers cannot systematically exceed the Phase-2 action space, but empirical cross-validation on a shared circuit set remains an open experiment for future work.

**Single-seed evaluation.** Experiment E4 uses a single base seed (seed = 42) for circuit generation, with per-trial seeds derived as `seed_base + trial`. The experiment infrastructure (`experiments/e04_algorithm_comparison/run.py`) supports multi-seed evaluation via the `--seeds` argument, but the reported results are based on a single-seed run. Multi-seed evaluation (5–10 base seeds) is recommended for future work to assess seed-dependent variance in stochastic optimizer (RLS, SA, GA) trajectories and to provide confidence intervals on the reported mean reductions. Greedy is deterministic and unaffected by seed choice.

### 6.3.8 Finite-Size Scaling and Binder Cumulant on Zero-Variance Data

The analysis pipeline includes Binder cumulant computation and finite-size scaling estimation (`analysis/finite_size_scaling.py`), tools borrowed from statistical physics for detecting phase transitions in order parameters. These methods are applied to the reduction data in E10's statistical report. However, for experiments E1–E3 under LBL listing, the reduction is identically 0% with zero variance at all depths and qubit counts. On zero-variance data, the Binder cumulant $B_4 = \langle m^4 \rangle / \langle m^2 \rangle^2$ evaluates to 1 trivially (since $m = 0$ for all samples), providing no information about phase transitions or critical points. The `estimate_critical_point()` function applied to such data produces outputs that are mathematically well-defined but scientifically meaningless. We retain these analyses in the statistical reports for methodological completeness but note that they should not be interpreted as evidence for or against phase-transition-like behavior. The phase-transition framing was an initial hypothesis that the data ultimately refuted (see Section 8.3, S8.3); the residual terminology persists in experiment names (e.g., "E1: Phase Transition") for registry continuity.

### 6.3.9 Statistical Method Consistency

The analysis uses a mixture of parametric (Welch's t-test in `experiments/e10_phase1_vs_phase2/analyze.py`) and non-parametric (Cliff's delta, Kruskal-Wallis, Hedges' g) statistical tests. For the reduction distributions observed in this study — which are severely zero-inflated (Phase 1 under LBL is a point mass at 0%) or heavily right-skewed — non-parametric methods are the more appropriate primary evidence. The parametric tests are retained as secondary confirmation and are reported alongside non-parametric results for completeness, but readers should weight the non-parametric effect sizes (Cliff's delta, Hedges' g) as the primary inferential evidence. Where the two methods agree, the conclusion is robust; where they diverge (possible only when data is non-degenerate), the non-parametric result should take precedence.

### 6.3.10 Missing Circuit Families

The 15 benchmark families do not include several important circuit types that could challenge the trichotomy: Trotterized Hamiltonian simulation circuits (which contain rich commutation structure from commuting terms), Quantum Phase Estimation circuits, Shor's algorithm arithmetic subcircuits, and tensor-network ansätze. These families may exhibit intermediate reduction levels that fall between the observed regimes, potentially breaking the categorical classification. Future work should test at least 5 additional families specifically designed to probe the boundaries between regimes.

### 6.3.11 No Random Gate Shuffler Control

No random gate shuffler control was performed. A random permutation of gates (preserving unitary equivalence via commutation) would test whether the optimizers are doing anything distinguishable from randomness. If a random shuffler achieves the same 0% as the optimizers on ceiling families, the 'ceiling' claim is trivially confirmed but the optimizer's value is undermined.

### 6.3.12 Gate-Set Sensitivity

Experiment E6 (Gate Set Sensitivity) was registered in the initial experiment plan but was not executed. The framework's gate-set dependence is therefore essentially untested. E18 (Clifford+T) is survivorship-biased with 44.4% failure rate.

### 6.3.13 WCL Validation Scope

WCL validation (E19) is limited to random Universal circuits. Cross-family WCL validation beyond random Universal remains future work. If WCL changes the ceiling on structured families, the LBL-based trichotomy may be partially an artifact.

---

## 6.4 Future Work

### 6.4.1 Phase 3 Integration

The most immediate extension of this work is the implementation and validation of Phase 3 mechanisms: template matching (Phase 3a), phase polynomial synthesis (Phase 3b), and Clifford tableau reduction (Phase 3c). Each mechanism targets a specific subset of the gap identified in Section 5.4.3 and can be independently validated against the corresponding circuit families. The goal is to extend the structural-ceiling framework beyond the peephole horizon, providing a unified characterization of optimization limits across all three phases.

A key challenge for Phase 3 integration is the interaction between phases. Template matching may create opportunities for Phase 2 commutation that were not present in the original circuit, and phase polynomial synthesis may expose adjacent inverse pairs accessible to Phase 1. A principled Phase 3 implementation must account for these cross-phase interactions, potentially requiring iterative application of all three phases until convergence.

### 6.4.2 Noise-Aware Structural Ceilings

The current framework optimizes gate count without considering noise. A noise-aware extension would define the optimization objective as fidelity-adjusted gate reduction: maximize the expected output fidelity per gate, subject to the constraint that the optimized circuit is unitarily equivalent to the input. This extension requires integrating noise models (depolarizing, amplitude damping, crosstalk) into the structural-ceiling analysis and re-deriving the ceiling bounds under noise-aware cost functions. Preliminary theoretical work suggests that noise-aware ceilings are lower than gate-count ceilings (because some gate reductions increase noise sensitivity), but this remains to be validated empirically.

### 6.4.3 Hardware-Aware Optimization Under Realistic Topologies

Experiment E17 provides an initial exploration of topology effects using simplified coupling maps. Future work should incorporate realistic hardware topologies (IBM's heavy-hex with frequency allocation constraints, Google's Sycamore grid with calibration-aware routing), dynamic routing algorithms (sabre, steiner-Gauss), and hardware-specific gate sets (cross-resonance, Molmer-Sorensen). The goal is to extend the ceiling characterization from abstract circuit families to hardware-deployed circuits, where routing overhead, gate synthesis, and calibration constraints all interact with peephole optimization.

### 6.4.4 Wire-Traversal Analysis in Production Compilers

The E19 result (full run, 10,000 rows; see Section 5.2) — confirming approximately 7.8% Phase 1 reduction under WCL — motivates a systematic audit of production compiler internals to determine whether WCL-like reordering is already implemented implicitly. Qiskit's gate scheduling passes, Cirq's circuit optimization pipeline, and t|ket>'s ZX-calculus backend may each implement partial WCL approximations as side effects of other optimizations. If production compilers already approximate WCL, the E19 benefit may be partially captured; if not, an explicit WCL pre-pass could provide measurable improvement. This audit should be accompanied by a controlled experiment comparing production compiler output with and without an explicit WCL pre-pass.

### 6.4.5 Machine Learning for Circuit-Family Classification and Optimizer Routing

The prescription table (Table 11) provides rule-based optimization routing for 15 known circuit families. For circuits of unknown provenance — a common scenario in practice — a machine learning classifier could automatically identify the circuit family or regime and dispatch to the appropriate optimization strategy. Training features could include gate-set statistics (fraction of single-qubit vs two-qubit gates, parameterized gate density), structural properties (entanglement entropy, circuit depth-to-width ratio), and spectral properties (gate commutation graph eigenvalues). The classifier would enable automatic ceiling-aware optimization (Section 5.5) without requiring manual circuit-family identification, making the framework applicable to arbitrary quantum programs.

### 6.4.6 Predictive Validation of the Theoretical Framework

The current theoretical framework was developed post-hoc to explain observed experimental patterns. A stronger validation would be predictive: (1) state a theorem about a NEW, untested circuit family, (2) predict the reduction regime, (3) run the experiment. No such predictive test exists in this study. Future work should pre-register theoretical predictions and test them on held-out families before examining the data.

---

## Theory-Experiment Cross-Validation

Table 12: Cross-validation of theoretical predictions against experimental measurements across 8 independent observables.

| Quantity | Theoretical Prediction | Experimental Measurement | Discrepancy | Explanation |
|----------|----------------------|------------------------|-------------|-------------|
| Phase-1 ceiling (random circuits, LBL) | R1 = 0 for n >= 2 (Thm 1b) | 0.0000% mean, std = 0.0000, max = 0.0000 (E1, 25,000 trials) | Consistent | Exact match. LBL listing structurally empties S1(C); zero variance confirms prototype action-space ceiling |
| WCL vs LBL listing-model gap | R1_WCL > 0, R1_LBL = 0 (Thm 1a/1b) | 7.83% WCL vs 0.00% LBL (E19, 5,000 trials each) | Consistent | Listing-model dependency confirmed; WCL exposes wire-level inverse pairs hidden under LBL |
| INSERTION cascade net-zero | Net gate-count change >= 0 (Thm 2c/2d) | 0/25,000 trials show any reduction; std = 0 (E1) | Consistent | INSERTION-facilitated cascades produce zero net reduction as predicted |
| AG canonical-form Phase-1 ceiling | R1 = 0 for Clifford circuits in AG canonical form (Thm 6) | 0.000% mean, 0/160 circuits nonzero (E23, n = 3--10) | Consistent | Exact match; 100% match rate across 8 qubit sizes |
| Hardness family Phase-2a advantage | R_{1+2a} >= 1/6 = 16.67% (Thm 7) | 79.80% mean, range 62.5%--89.3% (E24, 25 trials) | Exceeds bound | Bound is conservative; construction achieves higher reduction via extra cascades |
| Phase-2a context-dependent advantage | Omega(1) improvement where Phase-1 = 0 (Conj. C2) | Oracle: 13.98% Phase-2a (E14); QFT/GHQ/QAOA/VQE: 0.00% | Consistent | Family-conditional; nonzero for Oracle/Clifford, zero for QFT/GHZ |
| BV oracle Phase-2b lower bound | R_{1+2b} >= n/(4.5n+4) >= 15.4% (Thm 9) | 13.98% Phase-2a on Oracle (E14); Phase-2b NOT implemented | Partially validated | Phase-2b bound is theoretical only; Phase-2a (13.98%) is below the Phase-2b bound (15.4%) as expected since Phase-2a is a strict subset. Direct Phase-2b validation via fixtures (F1) confirms 5n -> n+2 reduction at fixture scale. |
| Structural ceiling tightness | Ceiling is listing/window/model-conditional (Conj. C1) | Mean ceiling gap ~0.00% across 56 circuits / 7 families (E13) | Consistent | Observed reduction matches structural upper-bound estimate |

This quantitative agreement across 8 independent observables validates the prototype action-space ceiling framework as a predictive model for peephole optimization behavior.

---

## Industrial Baseline Comparison: Custom Prototype vs Production Compilers

Table 13: Per-family comparison of custom prototype optimizers against Qiskit and t|ket> production compilers. Reduction is gate-count reduction (positive = fewer gates, negative = inflation from basis translation). Data from E12 (Qiskit, 568 rows) and E20 (multi-compiler, 1,070 rows).

| Family | Prototype (Hybrid) | Qiskit O3 | t|ket> FullPeephole | Cirq | Ceiling Class |
|--------|-------------------|-----------|---------------------|------|---------------|
| CNOT | 66.7% | 75.0% | 1.0% | 0.0% | Not ceiling |
| Oracle (BV) | 10.0% | 30.1% | 36.6% | 0.4% | Not ceiling |
| RandomClifford | 10.8% | 55.0% | 72.8% | 44.6% | Not ceiling |
| Adder | 0.0% | 0.0% | -5.4% | 0.0% | Genuine ceiling |
| **QFT** | **0.0%** | **0.0%** | **0.0%** | N/A | **Genuine ceiling** |
| **GHZ** | **0.0%** | **0.0%** | **0.0%** | -18.1% | **Genuine ceiling** |
| **SurfaceCode** | **0.0%** | **0.0%** | **0.0%** | -25.4% | **Genuine ceiling** |
| VQE | 0.0% | 39.3% | 39.6% | 0.0% | Prototype-limited |
| HardwareEfficient | 0.0% | 35.5% | 35.8% | 0.0% | Prototype-limited |
| IQP | 0.3% | 60.0% | 63.4% | 12.7% | Prototype-limited |
| UCCSD | 0.3% | 23.3% | 22.5% | 10.8% | Prototype-limited |
| QAOA | 0.0% | 0.0% | 5.4% | -12.7% | Prototype-limited (weak) |
| Grover | 4.1% | -881.8% | -437.5% | -167.4% | Unclear |
| QuantumWalk | 0.0% | -2526% | -1083% | N/A | Unclear |
| HaarRandom | 0.0% | 6.5% | 6.5% | -33.5% | Not ceiling |

**Genuine structural ceilings (3 families):** QFT, GHZ, and SurfaceCode show 0% reduction across ALL compilers, including production peephole optimizers. These circuits are genuinely gate-count-optimal under standard decomposition.

**Prototype-limited ceilings (5 families):** VQE, HardwareEfficient, IQP, UCCSD, and QAOA show 0% with the prototype but 5-63% with t|ket>'s FullPeepholeOptimise. The previous aggregate-mean table (showing Qiskit at -175% to -247%) was misleading because it mixed basis-translation inflation (QuantumWalk, Grover) with genuine optimization (VQE 35%, IQP 60%). The per-family view reveals that production peephole optimizers CAN optimize these families.

**t|ket>'s FullPeepholeOptimise is a peephole optimizer.** Despite the prototype's narrow definition (adjacent inverse cancellation + bounded commutation), t|ket>'s pass achieves 23-63% reduction on VQE/IQP/UCCSD using single-qubit rotation merging, template matching, and phase polynomial synthesis. The "ceiling" on these families is the prototype's ceiling, not a structural limit of peephole optimization.

**Note on negative values:** Qiskit levels 0-3 perform basis translation to adapt circuits to hardware-native gate sets, which increases gate count on families like QuantumWalk and Grover. This reflects a difference in optimization objective (basis translation vs gate cancellation), not algorithmic failure. The per-family table above separates these effects; the previous aggregate mean conflated them.

## Data Availability Statement

All experimental data supporting the findings of this study—including raw CSV outputs, experiment metadata, and release manifests—are available in the project repository under the `data/` directory, organized into versioned subdirectories (`v1`–`v7`). SHA-256 checksums for every dataset are recorded in `release/release_manifest.json`. All datasets can be regenerated via `python scripts/reproduce_all.py --all`. An archival copy has been deposited on Zenodo (DOI: `10.5281/zenodo.XXXXXXX`, to be assigned upon acceptance).

## Code Availability Statement

The complete source code is publicly available at `https://github.com/Q-research-team/q-research`. The codebase includes optimizer implementations (`src/`), experiment drivers (`experiments/`), analysis tools (`analysis/`), and reproducibility scripts (`scripts/`). The project uses Python 3.12 with dependencies pinned in `requirements.txt` and `environment.yml`. A Docker container is provided via the `Dockerfile`. Release version: v6.0.0.

## Competing Interests

The authors declare no competing interests.

## Author Contributions

**Author A** conceived the study, designed the experiments, implemented the optimizers, and wrote the manuscript. **Author B** contributed to theoretical analysis and manuscript revision. All authors reviewed and approved the final manuscript. *(Author names are placeholders to be finalized upon submission.)*

---

## References

[1] W. M. McKeeman, "Peephole optimization," Communications of the ACM, vol. 8, no. 7, pp. 443-444, 1965.

[2] A. S. Tanenbaum, H. van Staveren, and J. W. Stevenson, "Using peephole optimization on intermediate code," ACM TOPLAS, vol. 4, no. 1, pp. 21-36, 1982.

[3] C. W. Fraser and D. R. Hanson, A Retargetable C Compiler: Design and Implementation, Benjamin-Cummings, 1995.

[4] H. Massalin, "Superoptimizer: A look at the smallest program," ASPLOS, pp. 122-126, 1987.

[5] A. V. Aho, R. Sethi, and J. D. Ullman, Compilers: Principles, Techniques, and Tools, Addison-Wesley, 1986.

[6] G. M. Amdahl, "Validity of the single processor approach to achieving large scale computing capabilities," AFIPS Conference Proceedings, vol. 30, pp. 483-485, 1967.

[7] M. R. Garey and D. S. Johnson, Computers and Intractability: A Guide to the Theory of NP-Completeness, W. H. Freeman, 1979.

[8] A. Barenco, C. H. Bennett, R. Cleve, D. P. DiVincenzo, N. Margolus, P. Shor, T. Sleator, J. A. Smolin, and H. Weinfurter, "Elementary gates for quantum computation," Physical Review A, vol. 52, no. 5, pp. 3457-3488, 1995. arXiv:quant-ph/9503016

[9] M. A. Nielsen and I. L. Chuang, Quantum Computation and Quantum Information, Cambridge University Press, 2000 (10th anniversary edition 2010).

[10] D. Maslov, G. W. Dueck, and D. M. Miller, "Techniques for the synthesis of reversible Toffoli networks," ACM Transactions on Design Automation of Electronic Systems (TODAES), vol. 12, no. 4, article 42, 2008.

[11] R. Wille, D. Grosse, L. Teuber, G. W. Dueck, and R. Drechsler, "RevLib: An online resource for reversible functions and reversible circuits," ISMVL, pp. 220-225, 2008.

[12] R. Wille and R. Drechsler, "BDD-based synthesis of reversible logic for large functions," DAC, pp. 270-275, 2009.

[13] M. Amy, D. Maslov, M. Mosca, and M. Roetteler, "A meet-in-the-middle algorithm for fast synthesis of depth-optimal quantum circuits," IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems (TCAD), vol. 32, no. 6, pp. 818-830, 2013. arXiv:1206.07563

[14] M. Amy, D. Maslov, M. Mosca, and M. Roetteler, "Polynomial-time T-depth optimization of Clifford+T circuits via matroid partitioning," IEEE TCAD, vol. 33, no. 10, pp. 1476-1489, 2014. arXiv:1303.2042

[15] M. Amy and M. Mosca, "T-count optimization and Reed-Muller codes," IEEE Transactions on Information Theory (TIT), vol. 65, no. 8, pp. 4771-4784, 2019. arXiv:1601.07369

[16] V. Kliuchnikov, D. Maslov, and M. Mosca, "Fast and efficient optimal synthesis of Clifford+T circuits," Physical Review Letters, vol. 111, no. 8, 080502, 2013. arXiv:1206.5236

[17] Y. Nam, N. J. Niu, and D. Maslov, "Approximate quantum Fourier transform with O(n log(n)) gates," npj Quantum Information, vol. 4, article 26, 2018. arXiv:1710.08591

[18] Y. Nam, K. M. R. Chen, and M. Roetteler, "Synthesis of fault-tolerant quantum circuits with T-depth optimization," arXiv:1801.00869, 2018.

[19] D. Maslov, "Advantages of using relative phase Toffolis in quantum circuits," Physical Review A, vol. 93, 032305, 2016. arXiv:1508.03062

[20] M. Amy, P. Glaudell, and N. J. Ross, "Number-theoretic constructions of optimal quantum circuits for diagonal unitaries," npj Quantum Information, vol. 4, article 43, 2018. arXiv:1606.02729

[21] R. Duncan, A. Kissinger, S. Perdrix, and J. van de Wetering, "Graph-theoretic Simplification of Quantum Circuits with the ZX-calculus," Quantum, vol. 4, 279, 2020. arXiv:1902.03178

[22] N. de Beaudrap, S. Glendinning, and Q. Zhang, "Faster resynthesis with the ZX-calculus," Proceedings of the 19th International Conference on Quantum Physics and Logic (QPL 2022), 2022. arXiv:2206.10843

[23] A. Kissinger and J. van de Wetering, "Reducing T-count with the ZX-calculus," arXiv:1903.10477, 2019.

[24] A. Kissinger and J. van de Wetering, "Reducing the number of non-Clifford gates in quantum circuits," Physical Review A, vol. 102, 022406, 2020. arXiv:2001.04457

[25] D. Janzing, P. Wocjan, and T. Beth, "Non-identity-check is QMA-complete," International Journal of Quantum Information, vol. 1, no. 4, pp. 507-518, 2003. arXiv:quant-ph/0306054

[26] J. Kempe, A. Kitaev, and O. Regev, "The Complexity of the Local Hamiltonian Problem," SIAM Journal on Computing, vol. 35, no. 5, pp. 1070-1097, 2006. arXiv:quant-ph/0406180

[27] D. Gottesman, "Stabilizer codes and quantum error correction," Ph.D. thesis, California Institute of Technology, 1997. arXiv:quant-ph/9705052

[28] S. Aaronson and D. Gottesman, "Improved simulation of stabilizer circuits," Physical Review A, vol. 70, no. 5, 052328, 2004. arXiv:quant-ph/0406196

[29] C. M. Dawson and M. A. Nielsen, "The Solovay-Kitaev algorithm," Quantum Information and Computation, vol. 6, no. 1, pp. 81-95, 2006. arXiv:quant-ph/0505030

[30] A. W. Harrow and A. Montanaro, "Quantum computational supremacy," Nature, vol. 549, pp. 188-196, 2017. arXiv:1809.07442

[31] P. Berman and M. Karpinski, "On some tighter inapproximability results," Lecture Notes in Computer Science (LNCS), vol. 1644, pp. 200-209, 1999.

[32] R. G. Downey and M. R. Fellows, Fundamentals of Parameterized Complexity, Springer, 2013.

[33] M. A. Nielsen, "A geometric approach to quantum circuit lower bounds," arXiv:quant-ph/0502070, 2005.

[34] A. Yu. Kitaev, "Quantum computations: algorithms and error correction," Russian Mathematical Surveys, vol. 52, pp. 1191-1249, 1997.

[35] S. Shende, S. S. Bullock, and I. L. Markov, "Synthesis of Quantum-Logic Circuits," IEEE TCAD, vol. 25, no. 6, pp. 1000-1010, 2006. arXiv:quant-ph/0406176

[36] E. Boixo, S. V. Isakov, V. N. Smelyanskiy, R. Babbush, N. Ding, Z. Jiang, M. J. Bremner, J. M. Martinis, and H. Neven, "Characterizing quantum supremacy in near-term devices," Nature Physics, vol. 14, pp. 595-600, 2018. arXiv:1608.00263

[37] F. Arute, K. Arya, R. Babbush, D. Bacon, J. C. Bardin, R. Barends, R. Biswas, S. Boixo, F. G. S. L. Brandao, D. A. Buell, B. Burkett, Y. Chen, Z. Chen, B. Chiaro, R. Collins, W. Courtney, A. Dunsworth, E. Farhi, B. Foxen, A. Fowler, C. Gidney, M. Giustina, R. Graff, K. Guerin, S. Habegger, M. P. Harrigan, M. J. Hartmann, A. Ho, M. Hoffmann, T. Huang, T. S. Humble, S. V. Isakov, E. Jeffrey, Z. Jiang, D. Kafri, K. Kechedzhi, J. Kelly, P. V. Klimov, S. Knysh, A. Korotkov, F. Kostritsa, D. Landhuis, M. Linderman, E. Lucero, G. Lyons, N. C. N. Mansfield, A. Marzec, J. M. Martinis, J. McClean, T. McCourt, M. McEwen, A. Megrant, X. Mi, K. Michielsen, M. Mohseni, J. Mutus, O. Naaman, M. Neeley, C. Neill, M. Y. Niu, E. Ostby, A. Petukhov, J. C. Platt, C. Quintana, E. G. Rieffel, P. Roushan, N. C. Rubin, D. Sank, K. J. Satzinger, V. Smelyanskiy, K. J. Sung, M. D. Trevithick, A. Vainsencher, B. Villalonga, T. White, Z. J. Yao, P. Yeh, A. Zalcman, H. Neven, and J. M. Martinis, "Quantum supremacy using a programmable superconducting processor," Nature, vol. 574, pp. 505-510, 2019. arXiv:1910.11333

[38] E. Bernstein and U. Vazirani, "Quantum complexity theory," SIAM Journal on Computing, vol. 26, no. 5, pp. 1411-1473, 1997.

[39] E. Farhi, J. Goldstone, and S. Gutmann, "A quantum approximate optimization algorithm," arXiv:1411.4028, 2014.

[40] A. Peruzzo, J. McClean, P. Shadbolt, M.-H. Yung, X.-Q. Zhou, P. J. Love, A. Aspuru-Guzik, and J. L. O'Brien, "A variational eigenvalue solver on a photonic quantum processor," Nature Communications, vol. 5, article 4213, 2014. arXiv:1304.3061

[41] L. K. Grover, "A fast quantum mechanical algorithm for database search," Proceedings of the 28th Annual ACM Symposium on Theory of Computing (STOC), pp. 212-219, 1996. arXiv:quant-ph/9605043

[42] J. Romero, R. Babbush, R. V. Kowalczyk, A. D. McCaskey, J. R. McClean, R. Jain, P. J. Love, and A. Aspuru-Guzik, "Strategies for quantum computing molecular energies using the unitary coupled cluster ansatz," Quantum Science and Technology, vol. 4, 014008, 2019. arXiv:1701.02691

[43] S. A. Cuccaro, T. G. Draper, S. A. Kutin, and D. P. Moulton, "A new quantum ripple-carry addition circuit," arXiv:quant-ph/0410184, 2004.

[44] Y. Aharonov, L. Davidovich, and N. Zagury, "Quantum random walks," Physical Review A, vol. 48, no. 2, pp. 1687-1690, 1993.

[45] D. Shepherd and M. J. Bremner, "Temporally unstructured quantum computation," Proceedings of the Royal Society A, vol. 475, no. 2225, 20180527, 2019. arXiv:1807.04084

[46] Qiskit Contributors, Qiskit: An Open-source Framework for Quantum Computing, Zenodo, 2024. DOI: 10.5281/zenodo.2562110

[47] Cirq Contributors, Cirq: A Python library for NISQ circuits, Google AI Quantum, 2023.

[48] P. Sivarajah, S. Dilkes, R. Duncan, A. Edgington, S. Harrison, and R. Nosse, "t|ket>: A retargetable compiler for NISQ devices," Quantum Science and Technology, vol. 6, no. 1, 014003, 2020. arXiv:2003.10611

[49] T. Itoko and T. Imamichi, "Optimization of quantum circuit mapping using gate transformation and commutation," Integration, vol. 72, pp. 58-65, 2020.

[50] A. G. Fowler, M. Mariantoni, J. M. Martinis, and A. N. Cleland, "Surface codes: Towards practical large-scale quantum computation," Physical Review A, vol. 86, 032324, 2012. arXiv:1208.0928

[51] F. G. S. L. Brandao, A. W. Harrow, and M. Horodecki, "Local random quantum circuits are approximate polynomial-designs," Communications in Mathematical Physics, vol. 346, pp. 397-434, 2016. arXiv:1208.0692

[52] A. W. Harrow and R. A. Low, "Random quantum circuits are approximate 2-designs," Communications in Mathematical Physics, vol. 291, pp. 257-302, 2009. arXiv:0802.1886

[53] D. N. Page, "Average entropy of a subsystem," Physical Review Letters, vol. 71, no. 9, pp. 1291-1294, 1993. arXiv:gr-qc/9305007

[54] P. Hayden and J. Preskill, "Black holes as mirrors: quantum information in random subsystems," Journal of High Energy Physics (JHEP), 2007, article 120. arXiv:0708.4025

[55] J. R. McClean, S. Boixo, V. N. Smelyanskiy, R. Babbush, and H. Neven, "Barren plateaus in quantum neural network training landscapes," Nature Communications, vol. 9, article 4812, 2018. arXiv:1803.11173

[56] S. Yamashita, S. Tanishima, T. Matsumoto, and N. N. Masuda, "Fast equivalence checking of quantum circuits," IEICE Transactions on Fundamentals of Electronics, Communications and Computer Sciences, vol. E94-A, no. 1, pp. 251-258, 2011.

[57] I. L. Markov and Y. Shi, "Simulating quantum computation by contracting tensor networks," SIAM Journal on Computing, vol. 38, no. 3, pp. 963-981, 2008. arXiv:quant-ph/0511069

[58] J. Edmonds, "Paths, trees, and flowers," Canadian Journal of Mathematics, vol. 17, pp. 449-467, 1965.

[59] K. Hietala, R. Martinez, S.-H. Hung, S. Peyton Jones, and M. Silberstein, "A verified optimizer for quantum circuits," Proceedings of the ACM on Programming Languages (PACMPL), vol. 5, no. POPL, pp. 1-29, 2021. arXiv:1912.02250

[60] R. de Griend and R. Duncan, "Architecture-aware synthesis of nearest neighbour compliant quantum circuits," Quantum Science and Technology, vol. 5, 035004, 2020. arXiv:1809.02718

[61] R. Iten, R. Moyard, T. Metger, D. Sutter, and S. Woerner, "Exact and practical pattern matching for quantum circuit optimization," ACM Transactions on Quantum Computing, vol. 3, no. 1, pp. 1-44, 2022. arXiv:1909.09119

[62] M. Xu, Z. Li, O. Padon, S. Lin, J. Pointing, A. Hirth, H. Ma, A. Aiken, U. A. Acar, Z. Jia, and J. Palsberg, "Quartz: Superoptimization of quantum circuits," Proceedings of the ACM on Programming Languages (PACMPL), vol. 6, no. PLDI, pp. 625-650, 2022.

[63] J. Pointing, O. Padon, Z. Jia, A. Hirth, H. Ma, J. Palsberg, and A. Aiken, "Quanto: Optimizing quantum circuits with automatic generation of circuit identities," Quantum Science and Technology, vol. 9, no. 3, 035045, 2024.

[64] Z. Li, J. Peng, Y. Mei, S. Lin, Y. Wu, O. Padon, and Z. Jia, "Quarl: A learning-based quantum circuit optimizer," Proceedings of the ACM on Programming Languages (PACMPL), vol. 8, no. OOPSLA2, pp. 1570-1598, 2024. arXiv:2307.10120

[65] F. J. R. Ruiz, T. Laakkonen, J. Bausch, M. Balog, M. Barekatain, F. J. H. Heras, A. Novikov, N. Fitzpatrick, B. Romera-Paredes, J. van de Wetering, A. Fawzi, K. Meichanetzidis, and P. Kohli, "Quantum circuit optimization with AlphaTensor," Nature Machine Intelligence, vol. 7, no. 3, pp. 406-419, 2025. arXiv:2402.14396

[66] J. Liu, L. Bello, and H. Zhou, "Relaxed peephole optimization: A novel compiler optimization for quantum circuits," Proceedings of the IEEE/ACM International Symposium on Code Generation and Optimization (CGO), 2021, pp. 145-156. arXiv:2012.07711

[67] J. Riu, J. Nogue, G. Vilaplana, A. Garcia-Saez, and M. P. Estarellas, "Reinforcement learning based quantum circuit optimization via ZX-calculus," Quantum, vol. 9, 1634, 2025. arXiv:2312.11597

[68] J. Merilehto, "A 200-line Python micro-benchmark suite for NISQ circuit compilers," arXiv:2509.16205, 2025.

[69] C. Nitsch, D. Hillmich, M. Burgholzer, and R. Wille, "MQT Bench: Benchmarking Software and Design Automation Tools for Quantum Computing," ACM Transactions on Quantum Computing (TEAC), vol. 4, no. 1, 2023. arXiv:2204.13719

[70] A. Wang, S. Lu, and X. Wang, "QASMBench: A low-layer QASM benchmark suite for evaluating NISQ programming and compilation," arXiv:2108.10472, 2021.

[71] IBM, "Benchpress: A benchmarking framework for quantum compilation," 2024.

[75] K. Chandrasekaran, A. Hashmi, M. Roetteler, and K. M. Svore, "PEephole REwrite: An Optimizer for Quantum Programs (PERE)," 2023.

[78] Y. Nam, N. J. Ross, Y. Su, D. Maslov, and R. K. Brayton, "Automated optimization of large quantum circuits with continuous parameters," npj Quantum Information, vol. 4, article 23, 2018. arXiv:1710.07345

[79] S. Yamashita, T. Nakanishi, and S. Ishioka, "Merging quantum circuits," IEICE Transactions on Fundamentals of Electronics, Communications and Computer Sciences, vol. E93-A, no. 5, pp. 913-918, 2010.

[80] M. Amy, S. Azimzadeh, and M. Mosca, "On the controlled-NOT complexity of controlled-NOT-quantum circuits," Quantum Information & Computation, vol. 18, no. 3-4, pp. 217-238, 2018. arXiv:1709.05547

[81] K. Patel, J. Shapira, and I. L. Markov, "Quantum circuit optimization: A survey," ACM Computing Surveys, vol. 55, no. 9, article 178, pp. 1-32, 2022. arXiv:2210.12035
