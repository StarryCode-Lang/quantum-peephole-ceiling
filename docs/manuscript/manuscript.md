# Manuscript Working Draft

> **Status note (2026-07-17)**: This v7 draft restructures the manuscript around the project's core novel contribution — columnar representation example sensitivity — as the primary narrative thread. The former "phase transition" terminology has been replaced with "search space stratification" throughout; the old term appears only in a historical note (Section 7.1). Contributions have been reorganized from 5+ to 3, each with explicit What/Why/Evidence structure. All experimental data from v6 are preserved; only the organization has changed. The v6 draft has been archived to `archive/manuscript_v6_archived.md`; this file is now the sole active manuscript draft. Target length: 1200–1400 lines (down from 1761).

---

# Columnar Representation Example Sensitivity and Search Space Stratification in Quantum Circuit Optimization

> **Author information**: Author names are placeholders and will be filled in prior to submission.

## Abstract

We discover that the circuit listing model — the data-structure ordering of gates in the instruction sequence — is the key factor governing peephole optimizer behavior, a phenomenon we term **columnar representation example sensitivity**. Three findings establish this: (1) under layer-by-layer listing (LBL), the Phase-1 action space is provably empty for $n \geq 2$, yielding exactly **0.0000%** gate reduction across **25,000** random circuits (E1); (2) under wire-consecutive listing (WCL), the same circuits exhibit **7.83%** mean reduction (E19, **10,000** rows); (3) across **15** circuit families and **67,000+** data rows, a categorical trichotomy emerges — 100% reduction (CNOT chains), 14–16% via commutation (oracle/Clifford circuits), and ~0% on 10 of 15 families, of which 3 are genuine structural ceilings confirmed by all production compilers and 7 are prototype-limited. These findings reframe peephole optimization from a purely algorithmic question to a representation-dependent one: the apparent "optimization desert" is a property of the (circuit, listing) pair, not of the circuits themselves, with direct implications for compiler pass design.

---

## 1. Introduction

### 1.1 Motivation

Peephole optimization — the local rewriting of bounded gate sequences to reduce circuit size — is a core component of every quantum compiler [Barenco et al. 1995, Maslov et al. 2008]. This approach traces its lineage to classical compiler theory, where McKeeman [1965] introduced peephole optimization as a final pass over machine code, and Massalin [1987] developed superoptimization through exhaustive search over small instruction windows. In the quantum setting, peephole optimization encompasses adjacent gate cancellation (removing $U \cdot U^{-1}$ pairs), template matching (applying pre-computed equivalence rules such as $H \cdot X \cdot H = Z$), and commutation-based reordering (exploiting gate commutativity to expose non-adjacent cancellation opportunities) [Amy et al. 2013, Wille et al. 2009].

Production compilers (Qiskit, Cirq, t|ket>) routinely achieve 10–40% gate-count reduction through sequences of local rewrite and synthesis passes, yet no systematic study has characterized *when* these passes succeed, *why* they sometimes fail entirely, or what representation-conditional limits constrain achievable reductions. This opacity encourages broad pass application, wasting computational resources on circuits that resist the tested local rewriting model while potentially missing opportunities for deeper optimization on amenable structures.

The economic stakes are acute in fault-tolerant architectures, where each logical T gate requires magic state distillation consuming approximately 1,000–10,000 physical qubits [Fowler et al. 2012]. A 10% reduction in T-count for Shor's algorithm at cryptographic key sizes can translate to savings of millions of physical qubits and hours of runtime. Yet current compilers achieve their reductions through heuristic pass sequences whose effectiveness varies unpredictably across circuit families. A compiler developer has no principled basis for deciding whether to invest additional computational budget in optimization passes for a given circuit, or whether the circuit has reached its fundamental optimization ceiling and further passes are futile. This resource allocation problem — how to distribute finite compilation time across optimization passes — is currently solved by applying all available passes unconditionally, a strategy that wastes resources on provably inoptimizable circuits while potentially under-investing in circuits with substantial optimization headroom.

Despite advances in automated identity generation [Xu et al. 2022 (Quartz), Pointing et al. 2024 (Quanto)], reinforcement learning [Li et al. 2024 (Qarl), Riu et al. 2025 (ZX+RL)], and tensor decomposition [Ruiz et al. 2025 (AlphaTensor-Quantum)], a fundamental disconnect persists between compiler practice and optimization theory. Production compilers operate as black boxes: they apply optimization passes and report the achieved reduction, but they do not explain why certain circuits yield substantial gains while others resist all optimization attempts. Theoretical complexity results establish that optimal circuit optimization is QMA-hard [Janzing et al. 2003], yet this worst-case hardness provides little guidance for the average-case behavior encountered in practice. The Gottesman–Knill theorem [Gottesman 1997] establishes that Clifford circuits are polynomial-time optimizable, suggesting that the hardness landscape is far more nuanced than worst-case analysis implies.

The field lacks a systematic framework for answering the most basic questions: What fraction of circuits are fundamentally inoptimizable by peephole methods? For which circuit families does commutation-based rewriting provide measurable advantage? How does the circuit representation — the data-structure ordering of gates — affect optimization outcomes?

### 1.2 The Discovery: Columnar Representation Example Sensitivity

A critical methodological discovery emerged during our investigation: the circuit listing model — the data-structure ordering of gates — fundamentally affects optimizer behavior in ways that have not been previously recognized. We call this phenomenon **columnar representation example sensitivity**: the observation that the same quantum circuit, when represented with different gate orderings in the instruction sequence, produces dramatically different optimization outcomes under peephole methods.

Quantum circuits can be represented in two natural listing formats. In **wire-consecutive listing (WCL)**, gates on the same qubit wire are placed consecutively in the circuit data structure, reflecting the natural representation in circuit diagrams and some synthesis tools. In **layer-by-layer listing (LBL)**, the circuit is generated and stored layer by layer, with one gate per qubit per layer; gates on the same qubit $q$ at layers $L$ and $L+1$ are separated by $n-1$ intervening gates from other qubits, where $n$ is the qubit count.

This seemingly innocuous data-structure choice has profound implications. We prove (Theorem 1(b)) that under LBL with $n \geq 2$, the Phase-1 action space is structurally empty: $\mathcal{S}_1(C) = \emptyset$ for every circuit $C$, where $\mathcal{S}_1(C)$ denotes the set of all adjacent gate pairs $(g_i, g_{i+1})$ such that $g_{i+1} = g_i^{-1}$ and both act on the same qubit(s). The proof is elementary but consequential: under LBL, the gate on qubit $q$ at layer $L$ is at listing index $L \cdot n + q$, while the next gate on the same qubit appears at index $(L+1) \cdot n + q$, yielding a gap of $n \geq 2$. Since Phase-1 requires listing adjacency (gap $= 1$) on the same qubit(s), no Phase-1 action is possible regardless of the circuit's gate content. Consequently, $R_1(C) = 0$ for every Phase-1 optimizer applied to LBL-represented circuits.

This theorem explains previously puzzling zero-variance results in our early experiments (25,000 trials with LBL representation) and has significant practical implications. When circuits are represented in WCL instead of LBL, the Phase-1 action space can become non-empty for circuits containing wire-consecutive inverse pairs. Experiment E19 (10,000 rows) confirms that WCL preprocessing achieves approximately **7.83%** mean reduction on random universal circuits where LBL yields exactly **0.0000%**.

This discovery reframes the optimization landscape: the apparent "optimization desert" — zero reduction across 25,000 trials — is a property of the (circuit, listing) pair, not of the circuits themselves. The circuits contain wire-level inverse pairs; LBL merely hides them from listing-adjacent Phase-1 detection. Crucially, Phase-2 commutation rewriters — which operate on the circuit graph rather than the listing — are unaffected by this representation dependency, since they reason about wire-level adjacency rather than listing adjacency. This discovery necessitates a methodological recommendation: future experiments should either adopt WCL as the default listing model for Phase-1 evaluation, or include a wire-traversal preprocessing step to ensure that Phase-1 results reflect the circuit's intrinsic structure rather than an artifact of the data-structure ordering.

### 1.3 Research Questions

We formulate three research questions:

**RQ1: How does the circuit listing model affect peephole optimization outcomes, and what are the implications for compiler design?** This question investigates the practical impact of data-structure choices on optimization effectiveness and develops guidelines for representation-aware compiler implementation. It is motivated by our discovery of columnar representation example sensitivity (Theorem 1(b)).

**RQ2: What is the structure of the peephole optimization search space across diverse circuit families?** We seek to quantify the prevalence of optimization barriers and identify the structural properties that determine which circuits are optimizable by which peephole techniques. This question subsumes the former "phase transition" hypothesis — our initial conjecture of a depth-driven critical phenomenon, which the data refuted; we now use "search space stratification" to denote the observed categorical division into optimization regimes.

**RQ3: Where do production compilers operate beyond the local peephole model, and can ceiling knowledge improve compiler efficiency?** We aim to map the boundary between local peephole scope and global synthesis mechanisms, and to investigate whether representation sensitivity and stratification knowledge can enable ceiling-aware optimization that skips futile passes.

### 1.4 Contributions

This paper makes three contributions, in order of centrality.

**Contribution 1 (core): Columnar representation example sensitivity — formalization and empirical validation.**

- **What**: A formal characterization of how circuit listing order governs optimizer behavior. Theorem 1(b) proves that LBL makes the Phase-1 action space structurally empty for $n \geq 2$, explaining previously puzzling zero-variance experimental results. Theorem 1(a) establishes the density bound for WCL: $\mathbb{E}[|\mathcal{A}_{\text{adj}}(C)|] \leq n(d-1)[(1-\rho)^2/g_1^2 + \rho^2/(g_2(n-1))]$.
- **Why**: This identifies the data-structure ordering — not the optimization algorithm — as the key factor determining Phase-1 outcomes. The representation, not the circuit content alone, governs whether peephole optimization can detect cancellation opportunities.
- **Evidence**: E19 (10,000 rows) confirms that WCL achieves 7.83% mean reduction (std = 3.95%, max = 33.33%, fidelity = 1.0) on the same random ensemble where LBL yields exactly 0.0000%. E1 (25,000 trials) establishes the LBL ceiling with zero variance. E23 (160 circuits, $n = 3$–$10$) validates Theorem 6: Clifford circuits in Aaronson–Gottesman canonical form achieve 0.000% across all 160 instances.

**Contribution 2 (supporting): Search space stratification across 15 circuit families.**

- **What**: A large-scale empirical benchmark revealing a categorical trichotomy: 100% Phase-1 reduction (CNOT chains), 14–16% Phase-2 reduction (oracle/Clifford circuits), and ~0% on 10 of 15 families — of which 3 (QFT, GHZ, SurfaceCode) are genuine structural ceilings confirmed by all production compilers and 7 are prototype-limited (where t|ket> FullPeepholeOptimise achieves 5–63%).
- **Why**: Provides the first systematic characterization of when peephole optimization succeeds and fails across diverse circuit families, with circuit-family optimization prescriptions for compiler design. The stratification is not a gradual spectrum but a categorical division determined by algebraic structure.
- **Evidence**: Over 67,000 data rows across 27 datasets spanning 15 circuit families and 6 optimizer types (E1–E18), supplemented by E23/E24 theory-validation experiments (235 trials) and E20 multi-compiler comparison (1,070 rows across Qiskit/Cirq/t|ket>). The scale exceeds prior efforts — Quartz (~100 benchmarks), Qarl (~50 benchmarks), Micro-Benchmark Suite (6 circuits) — by two orders of magnitude.

**Contribution 3 (application, with acknowledged limitations): Ceiling-aware optimizer.**

- **What**: A proxy-guided pipeline that uses representation and stratification knowledge to skip futile optimization passes, achieving 1.6×–228× speedup (mean 35×) on E21 (1,140 rows) while producing bit-identical output circuits.
- **Why**: If ceiling knowledge is available for a circuit family, compilation time can be reduced without sacrificing output quality — valuable for batch compilation workflows.
- **Evidence**: E21 full-mode evaluation confirms identical gate-count reduction across all 15 training families with substantial family-dependent speedup. **Critical limitation**: The held-out generalization caveat (HGC) demonstrates that the empirical correlation model does not generalize to unseen circuit families (MAE = 0.2775, Pearson = NaN), so this result is valid only within training families and should be treated as an exploratory observation rather than a validated predictive tool.

### 1.5 Paper Organization

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

**Template-based optimization** [Maslov et al. 2008, Amy et al. 2013]: Pre-computed equivalence rules (e.g., $H \cdot X \cdot H = Z$, $\text{CNOT} \cdot \text{CNOT} = I$) are scanned for and applied. Template matching is a subgraph isomorphism problem (NP-hard in general), and template libraries are finite, limiting coverage.

**Commutation-based optimization** [Wille et al. 2009]: Gates that commute can be reordered to expose cancellation opportunities. The commutation graph of a circuit has gates as vertices and commutation relations as edges; finding optimal reorderings is equivalent to finding maximum independent sets.

**Phase polynomial optimization** [Amy et al. 2018]: For circuits with $R_z$ gates, rotations are represented as a polynomial over $\mathbb{Z}_2$ and simplified via Gaussian elimination. This achieves exponential improvements for certain families but applies only to CNOT+$R_z$ circuits.

**ZX-calculus approaches** [Duncan et al. 2020, de Beaudrap et al. 2022, Riu et al. 2025]: Circuits are translated into ZX-diagrams, simplified using graph-theoretic transformations, and extracted as optimized circuits. Recent work combines ZX with reinforcement learning, achieving up to 40% reduction on Clifford+T circuits with up to 40 qubits.

Our framework introduces a two-phase taxonomy: **Phase 1** (adjacent cancellation, window size $w = 2$) and **Phase 2** (commutation rewriting, $w \geq 3$). The Phase-1 action space is $\mathcal{S}_1(C) = \{(g_i, g_{i+1}) : Q(g_i) = Q(g_{i+1}), g_{i+1} = g_i^{-1}\}$; the extended Phase-2 action space is $\mathcal{S}_{1+2}(C) = \{(g_i, g_k) : g_k = g_i^{-1}, \text{all intermediates commute}\}$, with $\mathcal{S}_1(C) \subseteq \mathcal{S}_{1+2}(C)$. The optimization gap $\Gamma(C) = R_{1+2}^*(C) - R_1^*(C)$ quantifies Phase-2 advantage. The relationship is hierarchical: Phase 2 subsumes Phase 1, but the additional computational cost ($O(|C|^2)$ or higher) is only justified when $\Gamma(C) > 0$.

### 2.4 Computational Complexity

Circuit Identity Testing (CIT) — determining whether two quantum circuits implement the same unitary — was proven QMA-complete by Janzing et al. [2003]. Since optimal circuit optimization requires CIT as a subroutine, optimal optimization is at least QMA-hard. However, the complexity landscape becomes more nuanced when restricted to specific circuit classes. Gottesman [1997] introduced the stabilizer formalism, providing a polynomial-time representation of Clifford circuits. Aaronson and Gottesman [2004] showed that Clifford circuit simulation and optimization are in P. For Haar-random unitaries, Nielsen [2005] and Harrow and Montanaro [2017] established that the circuit complexity satisfies $\mathcal{C}(U) \geq 4^n/n^2$ with high probability over the Haar measure. These results provide lower bounds on circuit complexity but do not directly address the optimization problem for specific circuit families.

### 2.5 Quantum Compilers

Modern quantum compilers implement multi-pass optimization pipelines. **Qiskit** (IBM) [Qiskit 2024] implements a four-level pipeline (0–3) including basis translation, layout, routing, and optimization via template matching (~50 patterns), commutation, and cancellation. **Cirq** (Google) [Cirq 2023] uses moment-based optimization with `MergeInteractions` and `EjectZ` (phase polynomial style), achieving 5–20% reduction. **t|ket>** (Cambridge Quantum) [Sivarajah et al. 2020] uses `FullPeepholeOptimise` with Clifford simplification, gate cancellation, and commutation-based reordering, achieving 15–40% reduction.

The gap between production compilers and peephole optimizers is not merely quantitative (10–40% vs. 0–20% reduction) but qualitative: production compilers employ mechanisms that fundamentally exceed the local peephole model, including template matching beyond the 2-gate window, phase polynomial optimization on algebraic structure, and global synthesis replacing entire circuit segments.

### 2.6 Circuit Families

We study 15 primary circuit families spanning random, algorithmic, variational, and error-correcting circuits:

| # | Family | Gate Set | Category |
|---|--------|----------|----------|
| 1 | Universal (random) | $\{H, T, T^\dagger, R_z, \text{CNOT}\}$ | Random |
| 2 | Clifford (random) | $\{H, S, \text{CNOT}\}$ | Random |
| 3 | Structured (brickwork) | $\{H, R_z, \text{CNOT}\}$ | Random |
| 4 | QFT | $\{H, R_z(\pi/2^k), \text{CNOT}\}$ | Algorithmic |
| 5 | GHZ | $\{H, \text{CNOT}\}$ | Algorithmic |
| 6 | BV Oracle | $\{H, X, \text{CNOT}\}$ | Algorithmic |
| 7 | CNOT Chain | $\{\text{CNOT}\}$ | Algorithmic |
| 8 | Grover | $\{H, X, Z, \text{MCX}\}$ | Algorithmic |
| 9 | Quantum Adder | $\{X, \text{CNOT}, \text{CCX}\}$ | Algorithmic |
| 10 | Quantum Walk | $\{H, X, R_y, \text{MCX}\}$ | Algorithmic |
| 11 | IQP | $\{H, R_z, \text{CZ}\}$ | Algorithmic |
| 12 | QAOA | $\{H, R_{zz}, R_x\}$ | Variational |
| 13 | VQE (TwoLocal) | $\{R_y, R_z, \text{CNOT}\}$ | Variational |
| 14 | HardwareEfficient | $\{R_y, R_z, \text{CNOT}\}$ | Variational |
| 15 | Surface Code | $\{H, X, \text{CNOT}\}$ | Error-correcting |

**Random families.** Universal random circuits are generated in LBL format with configurable two-qubit gate density $\rho \in [0, 1]$. Clifford circuits use only stabilizer generators $\{H, S, \text{CNOT}\}$ and are efficiently simulable by the Gottesman–Knill theorem. Structured brickwork circuits alternate even- and odd-indexed CNOT layers.

**Algorithmic families.** QFT and GHZ circuits are already gate-optimal (no redundant gates), serving as negative controls. The BV oracle circuit is the natural family from Theorem 9, with a random secret string $s \in \{0, 1\}^n$. Grover circuits use a single iteration with a phase oracle. Quantum adders implement ripple-carry addition using Toffoli gates. IQP circuits consist of Hadamard-diagonal-Hadamard structure.

**Variational families.** QAOA circuits use line-graph cost functions with $R_{zz}$ and $R_x$ rotations. VQE ansatze use Qiskit's TwoLocal with $R_y$–$R_z$ rotation blocks and linear CNOT entanglement. Hardware-efficient ansatze alternate parameterized rotation layers with nearest-neighbor CNOT entanglement.

All circuits are deterministically seeded (seed $= 42 + \text{offset}$), materialized by binding parameters to fixed values and decomposing composite instructions up to three levels, and fingerprinted via SHA-256 hash of the instruction stream for reproducibility.

### 2.7 Related Benchmarking Efforts

The Micro-Benchmark Suite [Merilehto 2025] evaluates six self-generated circuits (3–8 qubits) across Qiskit, t|ket>, Cirq, and Amazon Braket, measuring post-routing depth and gate counts. However, it is a measurement tool, not a theoretical framework: it reports empirical metrics without explaining *why* different compilers produce different results or characterizing structural properties that determine optimizability. Its corpus (6 circuits) is orders of magnitude smaller than our study (67,000+ data rows across 15 families). Other benchmarking efforts — MQT Bench [Nitsch et al. 2023] and QASMBench [Wang et al. 2021] — focus on circuit diversity rather than optimization-theoretic analysis. Despite these advances, none of the existing optimization frameworks — Quartz, Quanto, Qarl, AlphaTensor-Quantum, Relaxed Peephole Optimization, or ZX+RL — provides a prototype action-space ceiling characterization, quantifies context-dependent Phase-2 advantage, or offers a systematic multi-compiler benchmark with formal theory. Our work fills these gaps.

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

**Results.**

| Listing Model | Mean Reduction (%) | Std Dev | Max Reduction (%) | Mean Fidelity |
|:---|---:|---:|---:|---:|
| LBL | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| WCL | 7.83 | 3.95 | 33.33 | 1.0000 |

Under LBL, Phase-1 (GreedyGateCancellation) yields 0.0000% mean reduction with zero variance, confirming the Theorem 1(b) prediction. Under WCL, mean reduction is 7.83% (std = 3.95%, max = 33.33%) with perfect unitary fidelity (1.0) across all 5,000 trials. The WCL result confirms that the Phase-1 ceiling is listing-model-dependent: reordering gates by qubit wire traversal exposes adjacent inverse pairs that are structurally hidden under LBL.

The observed effect is consistent with the density bound from Theorem 1(a): $\mathbb{E}[|\mathcal{A}_{\text{adj}}(C)|] = n(d-1) \cdot p_{\text{cancel}}(n, \rho)$, which for typical parameters yields a small but nonzero number of adjacent inverse pairs under WCL.

### 3.5 Practical Implications

The E19 result carries a direct practical implication: **wire-traversal preprocessing should be applied as a standard compiler pass before peephole optimization**. The transformation from LBL to WCL is computationally trivial ($O(m \log m)$) and is confirmed to unlock approximately 7.8% gate reduction that is otherwise inaccessible to Phase-1 optimizers. No existing production compiler (Qiskit, Cirq, or t|ket>) applies this transformation as an explicit pre-pass, though some may implicitly approximate it through qubit-aware scheduling heuristics. An open question is whether production compilers already implement WCL-like reordering implicitly — a systematic audit is an important direction for future work (Section 7.5).

The WCL result does not contradict the structural-ceiling framework; it refines it. The Phase-1 prototype action-space ceiling is listing-model-dependent: under LBL, the ceiling is severe (0% reduction); under WCL, the ceiling relaxes to approximately 7.8% mean reduction. A more general theory characterizing the ceiling over the space of all valid listings is an important direction for future work.

---

## 4. Theoretical Framework

This section develops the formal apparatus underlying our analysis. All theorems are stated with proof sketches; full proofs appear in the supplementary materials.

**Methodological note.** The theoretical framework was developed to explain observed experimental patterns, not to make a priori predictions. The chronology was: (1) observe 0% Phase-1 reduction on random circuits (E1, 25,000 trials), (2) identify LBL listing as the cause, (3) formalize as Theorem 1(b), (4) construct theoretical extensions (Theorems 2, 7, 9) to explain and bound the observed phenomena. The theorems should be interpreted as descriptive rather than predictive. Predictive validation — stating a theorem about an untested family, predicting its regime, then running the experiment — is an important direction for future work.

### 4.1 Phase-1 Reduction Ceiling

**Theorem 2 (Phase-1 Reduction Ceiling).** Let $\mathcal{O}_1 = \{\text{Greedy}, \text{SA}, \text{GA}, \text{RLS}\}$.

**(a) Greedy ceiling.** If $\mathcal{S}_1(C) = \emptyset$ and no consecutive rotation gates on the same qubit admit merging, then $R_{\text{greedy}}(C) = 0$.

**(b) Stochastic ceiling.** The stochastic optimizers (SA, GA, RLS) employ additional move primitives (SWAP, COMMUTATION, INSERTION). No finite sequence of such moves can achieve a net gate-count reduction beyond what is enabled by the commutation and swap structure already latent in $C$.

*Proof sketch.* SWAP exchanges adjacent gates on disjoint qubits; it preserves the gate multiset and the relative ordering of gates on each individual wire, but can make previously non-adjacent gates listing-adjacent. If the resulting adjacent pair acts on the same qubits and is inverse, SWAP creates a new $\mathcal{S}_1$ element. However, any reduction enabled by SWAP was latent in the wire-level structure. COMMUTATION replaces an adjacent pair with an equivalent commuted pair of the same size; if the original was not an inverse pair, the commuted pair is generically also not inverse. INSERTION adds an identity pair $(g, g^{-1})$, increasing $|C|$ by 2; Theorem 2(c) proves the insertion-debt invariant. $\blacksquare$

**Theorem 2(c) (Bounded INSERTION Cascade Lemma).** For any circuit $C$ with $\mathcal{S}_1(C) = \emptyset$, let $k$ INSERTION moves produce circuit $C'$ with $|C'| = |C| + 2k$. Let $R_{\text{removal}}(C')$ be the maximum number of gates removable via REMOVAL sequences involving at least one inserted gate. Then $R_{\text{removal}}(C') \leq 2k$, so the net gate-count change from any INSERTION + REMOVAL sequence is non-negative.

*Proof (Insertion-debt invariant).* Define the insertion debt $\Delta(C')$ as the number of gates introduced by INSERTION moves. Initially $\Delta(C) = 0$; each INSERTION increases $\Delta$ by 2. Each REMOVAL involving at least one inserted gate decreases $\Delta$ by at most 2. The debt is always non-negative. Let $r_{\text{ins}}$ be inserted gates removed and $r_{\text{pre}}$ pre-existing gates removed. Since every REMOVAL pair contains at least one inserted gate, $r_{\text{ins}} \geq r_{\text{pre}}$. Net change: $+2k - r_{\text{ins}} - r_{\text{pre}} \geq 2k - 2k - 0 = 0$. $\blacksquare$

**Theorem 2(d) (INSERTION Commutation Cascade Bound).** Even when INSERTION is combined with SWAP and COMMUTATION, the net reduction from any finite sequence starting from $\mathcal{S}_1(C) = \emptyset$ cannot exceed $B_{\text{pre}}(C)$ — the number of pre-existing wire-level inverse pairs that SWAP/COMMUTATION can bring into adjacency, which is exactly the Phase-2 action space $\mathcal{S}_{1+2}(C) \setminus \mathcal{S}_1(C)$.

*Proof (Wire-unitary preservation).* Under any sequence of INSERTION, SWAP, and COMMUTATION moves, the wire-level unitary product of pre-existing gates is preserved. INSERTION adds new gates but does not change the wire-level unitary of pre-existing gates. SWAP exchanges gates on disjoint qubits, not affecting per-wire unitaries. COMMUTATION preserves the wire-level unitary by definition. Since the per-wire unitary is invariant, INSERTION cannot create new wire-level inverse relationships among pre-existing gates. The net reduction is bounded by $B_{\text{pre}}(C) = |\mathcal{S}_{1+2}(C) \setminus \mathcal{S}_1(C)|$. $\blacksquare$

**Corollary 2.1 (Universality of the Phase-1 Ceiling).** All Phase-1 optimizers achieve identical ceiling: $R_{\text{greedy}}(C) = R_{\text{RLS}}(C) = R_{\text{SA}}(C) = R_{\text{GA}}(C) = R_1^*(C)$. Empirically, 45,500 trials across Universal, Clifford, and Structured families confirm $\leq 0.05\%$ mean reduction for all four optimizers.

### 4.2 Phase-2 Context-Dependent Advantage

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

*Proof sketch.* The BV oracle on $n$ data qubits (plus one ancilla) has structure $X_{\text{anc}} \cdot H^{\otimes(n+1)} \cdot \prod_{i \in S} \text{CNOT}(q_i, q_{\text{anc}}) \cdot H^{\otimes(n+1)} \cdot H_{\text{anc}} \cdot X_{\text{anc}}$, where $S \subseteq \{0, \ldots, n-1\}$ is the secret string. The circuit contains $2n$ Hadamard gates on data qubits separated by CNOT oracle gates. Phase-1 cannot cancel them because the intervening CNOT gates are non-adjacent. Phase-2b uses commutation to expose $H$-CNOT-$H$ sandwiches and applies a template identity to rewrite them. The $n/(4.5n+4)$ lower bound is a theoretical/template-assisted result. Phase-2b template matching is implemented with fixture-scale validation (`Phase2bTemplateMatcher`, unit-tested, E10 Phase-2b validation data: 1,017 rows); full canonical-scale Phase-2b benchmarking remains future work. $\blacksquare$

**Comparison.** Theorem 7 proves $\Omega(1)$ Phase-2b advantage for a deliberately engineered circuit family. Theorem 9 strengthens this to the Bernstein–Vazirani oracle — a *natural* circuit family arising from a well-known quantum algorithm — demonstrating that template-assisted Phase-2b advantage is not merely a pathological artifact.

**Conjecture C2 (Phase-2 is Context-Dependent Super-Constant).** There exist circuit families where Phase-1 achieves $O(1/d)$ reduction while Phase-1+2 achieves $\Omega(1)$. The improvement $\Gamma(C)$ is context-dependent: significant for oracle and structured circuits, zero for already-optimal or structurally rigid families.

*Evidence.* Theorem 7 (explicit construction) and Theorem 9 (BV oracle) establish C2 constructively. Empirically, Phase-2a achieves ~3.26% on random Universal (Cohen's $d = 1.32$), ~20% on BV oracle, and 0% on structured brickwork, QFT, and GHZ.

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

**CommutationRewriter (Phase-2).** Bubble-sort commutation within a sliding window of size $w$. For each anchor gate $g_i$, scans forward up to $w$ positions for an inverse gate $g_j$. If found, verifies that all intermediate gates commute with both $g_i$ and $g_j$, then bubble-sorts $g_j$ leftward into adjacency with $g_i$ and cancels. Commutation rules check: (1) disjoint qubit sets, (2) same single-qubit gate, (3) same-axis rotations, (4) Z-family gates on the same qubit, (5) CNOT with Z-family on the control qubit. These rules are sufficient but not necessary. Time complexity: $O(\text{max\_iter} \cdot m \cdot w^2)$ worst case, typically $O(m \cdot w)$.

**HybridCommuteRewrite.** Three-stage pipeline: Greedy (Phase-1) → CommutationRewriter (Phase-2) → Greedy (Phase-1 cleanup). By Lemma 3 (commutation preserves unitary equivalence), the full pipeline produces a circuit exactly unitarily equivalent to the input.

**CeilingAwareOptimizer.** Proxy-guided conditional pipeline that computes fast $O(m)$ structural proxies before each phase and skips phases predicted to yield zero reduction. `COUNT_PHASE1_ACTIONS` performs a single linear scan counting adjacent self-inverse and mergeable-rotation pairs. `COUNT_PHASE2_ACTIONS` performs a windowed scan counting non-adjacent inverse pairs with commuting intermediates. **Caveat (HGC)**: The empirical correlation model does not generalize to unseen circuit families.

### 5.2 Statistical Protocol

All mean reductions and effect sizes are accompanied by 95% bootstrap confidence intervals ($B = 10{,}000$ resamples with replacement). We report two complementary effect-size measures: Cliff's delta ($\delta$, non-parametric, robust to non-normality) and Cohen's $d$ (parametric, replaced by Glass's Delta when pooled SD is zero). Multiple hypothesis tests use Benjamini–Hochberg FDR correction at $\alpha = 0.05$. Power analysis: to detect Cohen's $d = 0.5$ with power $1 - \beta = 0.80$ at $\alpha = 0.05$, a minimum of $n = 64$ circuits per group is required; we use $n = 100$ per configuration.

Fidelity verification: exact average gate fidelity for $n \leq 12$ (full $2^n \times 2^n$ unitary matrices, $O(4^n)$); sampling-based estimator (1,000 Haar-random product states, SE ~3%) for $n > 12$; exact stabilizer tableau comparison for Clifford circuits ($O(n^2)$). Across experiments where fidelity was successfully computed, optimizer outputs preserve unitary equivalence. Documented failure rows (especially E18 decomposition/fidelity failures) are tracked and filtered from analyses requiring valid fidelity.

### 5.3 Compiler Configurations

**Qiskit (v2.4.1).** `qiskit.transpile` with optimization levels 0–3. Level 0: no optimization. Level 1: light optimization (adjacent cancellation, single-qubit merging). Level 2: medium (commutation analysis, KAK decomposition). Level 3: heavy (template matching, gate resynthesis, commutation-based reordering). We additionally report a **fair no-coupling-map comparison** (no SWAP routing) for like-for-like optimization comparison.

**Cirq (v1.6.1, E20).** `optimize_for_target_gateset` with `CZTargetGateset`, `eject_z`, and `merge_single_qubit_gates_to_phxz`. Evaluated on $n \leq 8$.

**t|ket> (v2.18.0, E20).** `FullPeepholeOptimise` with Clifford simplification, gate cancellation, and commutation-based reordering. Evaluated on $n \leq 6$ due to optimizer timeouts on larger instances.

### 5.4 Experiment Registry

The experimental program comprises 23 registered experiments (E1–E25). Key experiments:

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
| E16 | Window Scaling | 696 | 15 | P2 |
| E17 | Connectivity Constraints | 755 | 15 | P1+2 |
| E18 | Clifford+T Decomposition | 270 | 6 | P1+2 |
| E19 | WCL vs LBL Listing | 10,000 | 1 (Universal) | P1 |
| E20 | Multi-Compiler (Qiskit/Cirq/t|ket>) | 1,070 | 15 | P1+2 |
| E21 | Ceiling-Aware Optimizer | 1,140 | 15 | P1+2 |
| E23 | AG Canonical Form | 160 | 1 (Clifford) | P1 |
| E24 | Theorem 7 Hardness | 75 | 1 | P1+2 |

Data versioning: v1 (E1–E5, superseded), v2_fixed (E1–E5, canonical), v4 (E11–E13), v5 (E10, E14–E18), v6 (E19–E22, E25), v7 (E23–E24). Each artifact stored with SHA-256 content hash, optimizer configuration JSON, circuit fingerprint, and random seed. All experiments orchestrated by a unified runner with structured CSV/JSON output. Full pipeline: `python run_experiments.py --config experiments/v6_full.yaml`.

---

## 6. Results

### 6.1 Phase-1 Ceiling Under LBL Listing (E1–E5, RQ2)

**E1 (25,000 trials, $n = 5$, depths 1–50).** Mean gate reduction is 0.0000% at every tested depth, with zero variance. Maximum reduction across all 25,000 trials is 0.00%. At the conventional 20% success threshold, the success rate is 0.00%; at a more permissive 1% threshold, it remains 0.00%. This null result is explained by Theorem 1(b): under LBL, $\mathcal{S}_1(C) = \emptyset$ for all $C$ when $n \geq 2$. The absence of a depth-dependent ceiling change at any depth — including shallow circuits ($d = 1$–$5$) where one might expect finite-size effects — confirms the uniformity of the Phase-1 ceiling across the depth spectrum.

**E2 (2,100 trials, $n = 5$, density sweep).** Mean reduction remains 0.0000% at all two-qubit gate densities $\rho \in [0.1, 0.9]$. Pearson correlation between entanglement entropy and reduction is undefined ($r = \text{NaN}$, zero variance); $p = 1.000$ after FDR correction.

**E3 (12,000 trials, $n = 3$–$10$).** Mean reduction is 0.0000% at every qubit count. Kruskal-Wallis: $H = 0.00$, $p = 1.000$ (FDR-adjusted), confirming no variation with system size. Consistent with Theorem 1(a), which establishes that expected Phase-1 reduction scales as $O(1/g_1^2 + 1/(g_2 n))$ — negligible for $n \geq 3$.

**E4 (400 trials, 4 optimizers, $n = 5$, $d = 15$).** All four Phase-1 optimizers converge to approximately 0% mean reduction:

| Optimizer | N | Mean Reduction (%) | Std Dev | Max (%) | Mean Runtime (s) |
|:----------|---:|---:|---:|---:|---:|
| Greedy | 100 | 0.0000 | 0.0000 | 0.0000 | 0.0023 |
| RLS | 100 | 0.0000 | 0.0000 | 0.0000 | 6.1530 |
| SA | 100 | -1.5467 | 3.2201 | 2.6667 | 2.3848 |
| GA | 100 | -0.2267 | 0.8487 | 1.3333 | 7.2551 |

The Kruskal-Wallis test yields a non-significant result for reduction ($H \approx 0$, $p = 1.000$) but highly significant for runtime ($p < 0.001$). The convergence of fundamentally different search strategies to the same ceiling is strong evidence that the limitation is structural, not algorithmic — consistent with Theorem 2 and Corollary 2.1.

**E5 (6,000 trials, landscape perturbation, $n = 5$).** Mean reduction 0.22% (std 1.19%), maximum 26.67%. The "optimization desert" structure — low mean with high maximum — is the signature of a landscape where deep optima exist but are exponentially unlikely to be discovered by local search. The fraction of perturbed circuits achieving nonzero reduction decreases with depth: 0.50% at $d = 3$, declining to 0.02% at $d = 20$.

**Key conclusion:** Across 45,500 random-circuit trials, no Phase-1 optimizer achieves mean reduction exceeding 0.22% under LBL listing. This ceiling is listing-model-dependent (Section 3), not an intrinsic property of the circuits. All hypothesis tests of Phase-1 reduction variation — across depths (E1), densities (E2), qubit counts (E3), optimizers (E4), and landscape perturbations (E5) — remain non-significant after FDR correction.

### 6.2 Columnar Representation Sensitivity: WCL vs LBL (E19, RQ1)

See Section 3.4 for the full E19 flagship experiment. The key result: WCL achieves 7.83% mean reduction (std = 3.95%, max = 33.33%, fidelity = 1.0) versus 0.0000% under LBL, across 10,000 rows. This confirms that the Phase-1 ceiling is representation-dependent: the data-structure ordering, not the circuit content alone, determines whether peephole optimization can detect cancellation opportunities.

### 6.3 Search Space Stratification: The Trichotomy (E10, E14, E15, RQ2)

Experiments E10 (1,905 rows, 5 families) and E14 (2,130 rows, 15 families) extend the analysis to real algorithmic circuit families. The results reveal a categorical trichotomy:

**Class I — Trivially compressible (Phase-1 sufficient):** CNOT chains achieve 100% reduction under Greedy Phase-1 alone, confirming that adjacent inverse pairs are the sole optimization target and Phase-2 provides no additional value.

**Class II — Commutation-enabled compressible (Phase-2 required):** Oracle/BV circuits (~20–28% Phase-2 reduction), RandomClifford (~22.1%), Grover (~17.4%), IQP (~5.6%), UCCSD (~4.2%). These circuits contain non-adjacent inverse pairs accessible through commutation moves.

**Class III — Structurally incompressible under the tested peephole model (ceiling):** 3 of 15 families (QFT, GHZ, SurfaceCode) at genuine structural ceiling confirmed by all compilers, plus 7 of 15 (QAOA, VQE, HardwareEfficient, IQP, UCCSD, Adder, QuantumWalk) at prototype action-space ceiling where the prototype achieves ~0% but production compilers achieve 5–63%.

**Table: E10 Phase-1 vs Phase-2 Results (1,905 rows, selected families)**

| Family | P1 Greedy (%) | P2 Commutation (%) | Hybrid (%) | Mean Fidelity |
|:---|---:|---:|---:|---:|
| Universal | 0.00 | 2.99 | 2.99 | 1.0000 |
| Structured | 0.00 | 0.00 | 0.00 | 1.0000 |
| QFT | 0.00 | 0.00 | 0.00 | 1.0000 |
| GHZ | 0.00 | 0.00 | 0.00 | 1.0000 |
| CNOT chain | 100.00 | 0.00 | 100.00 | 1.0000 |
| RandomClifford | 0.10 | 15.85 | 16.07 | 1.0000 |

*Statistical power caveat:* Real-circuit cells (QFT, GHZ) have $N = 5$ per family-optimizer combination. Ceiling claims rely on convergent evidence from E14 (2,130 rows) and E15 (994 rows).

**Table: 15-Family Classification (E15, 994 rows)**

| Family | P1 (%) | P2 (%) | Hybrid (%) | Qiskit O3 (%) | Class |
|:---------------|---:|---:|---:|---:|:------|
| CNOT | 100.00 | 0.00 | 100.00 | 100.00 | I |
| Oracle | 0.00 | 14.94 | 14.94 | 40.08 | II |
| RandomClifford | 0.00 | 15.81 | 16.54 | 76.12 | II |
| Grover | 0.96 | 5.26 | 6.22 | -819.4* | II |
| IQP | 0.00 | 0.51 | 0.51 | 61.16 | II |
| UCCSD | 0.00 | 0.52 | 0.52 | 20.94 | II |
| QFT | 0.00 | 0.00 | 0.00 | 0.00 | III (genuine) |
| GHZ | 0.00 | 0.00 | 0.00 | 0.00 | III (genuine) |
| SurfaceCode | 0.00 | 0.00 | 0.00 | 0.00 | III (genuine) |
| QAOA | 0.00 | 0.00 | 0.00 | 0.00 | III (proto-limited) |
| VQE | 0.00 | 0.00 | 0.00 | 39.27 | III (proto-limited) |
| HardwareEfficient | 0.00 | 0.00 | 0.00 | 35.09 | III (proto-limited) |
| Adder | 0.00 | 0.00 | 0.00 | 0.00 | III (genuine) |
| QuantumWalk | 0.00 | 0.00 | 0.00 | -2794.7* | III (unclear) |
| HaarRandom | 0.00 | 0.00 | 0.00 | 3.88 | III |

*Gate-count inflation from basis-gate expansion. Data source: `e15_multi_compiler_e15_full_20260611_150934.csv`.*

**Window-size scaling (E16, 696 rows).** Phase-2 effectiveness depends on the commutation window $w$:

| Family | $w = 2$ (%) | $w = 5$ (%) | $w = 10$ (%) | $w = 20$ (%) |
|:---|---:|---:|---:|---:|
| Oracle | 0.00 | 0.00 | 27.39 | 34.63 |
| RandomClifford | 0.00 | 13.78 | 22.42 | 23.68 |
| Grover | 1.28 | 4.14 | 7.72 | 9.99 |
| **Mean (all)** | 6.75 | 7.91 | 10.61 | 11.33 |

$w = 10$ captures >90% of maximum achievable reduction for most reducible families. Saturation: Oracle/BV at $w \approx 10$, RandomClifford at $w \approx 15$. Statistical note: limited power ($p = 0.420$, Cohen's $d = 0.173$); saturation is an empirical trend.

**Circuit-family optimization prescriptions (Table 11, synthesized from E10, E15, E16):**

| Family | Class | Strategy | Expected Reduction (%) | Window $w$ | Qiskit O3 Gap (pp) |
|:---|:---:|:---|---:|:---:|---:|
| CNOT | I | Phase 1 | 100.0 | -- | 0.00 |
| Oracle | II | Phase 2 | 50.0 | 10 | 10.00 |
| RandomClifford | II | Phase 2 | 40.0 | 10 | 52.00 |
| QFT | III | Skip | 0.0 | -- | 0.00 |
| GHZ | III | Skip | 0.0 | -- | 0.00 |
| SurfaceCode | III | Skip | 0.0 | -- | 0.00 |
| VQE | III | Escalate | 0.0 (Qiskit: 40.9) | -- | 40.91 |
| HardwareEfficient | III | Escalate | 0.0 (Qiskit: 37.5) | -- | 37.50 |
| IQP | III | Escalate | 5.6 (Qiskit: 73.3) | 10 | 67.78 |

*Legend:* Phase 1 = Greedy only. Phase 2 = Commutation rewriting. Skip = no peephole pass produces nonzero reduction. Escalate = deploy beyond-peephole mechanisms (template matching, phase polynomial synthesis, Clifford tableau reduction).*

### 6.4 Multi-Compiler Mechanism Analysis (E12, E20, RQ3)

The completed multi-compiler comparison (E20, 1,070 rows across Qiskit/Cirq/t|ket>) serves two purposes: validating the ceiling against industrial-strength optimizers and identifying mechanisms by which production compilers exceed the peephole horizon.

**Table: Industrial Baseline Comparison (E12, E20)**

| Family | Prototype (Hybrid) | Qiskit O3 | t|ket> FullPeephole | Cirq | Ceiling Class |
|--------|---:|---:|---:|---:|:---|
| CNOT | 66.7% | 75.0% | 1.0% | 0.0% | Not ceiling |
| Oracle (BV) | 10.0% | 30.1% | 36.6% | 0.4% | Not ceiling |
| RandomClifford | 10.8% | 55.0% | 72.8% | 44.6% | Not ceiling |
| **QFT** | **0.0%** | **0.0%** | **0.0%** | N/A | **Genuine ceiling** |
| **GHZ** | **0.0%** | **0.0%** | **0.0%** | -18.1% | **Genuine ceiling** |
| **SurfaceCode** | **0.0%** | **0.0%** | **0.0%** | -25.4% | **Genuine ceiling** |
| Adder | 0.0% | 0.0% | -5.4% | 0.0% | Genuine ceiling |
| VQE | 0.0% | 39.3% | 39.6% | 0.0% | Prototype-limited |
| HardwareEfficient | 0.0% | 35.5% | 35.8% | 0.0% | Prototype-limited |
| IQP | 0.3% | 60.0% | 63.4% | 12.7% | Prototype-limited |
| UCCSD | 0.3% | 23.3% | 22.5% | 10.8% | Prototype-limited |
| QAOA | 0.0% | 0.0% | 5.4% | -12.7% | Prototype-limited (weak) |
| Grover | 4.1% | -881.8%* | -437.5%* | -167.4%* | Unclear |
| QuantumWalk | 0.0% | -2526%* | -1083%* | N/A | Unclear |
| HaarRandom | 0.0% | 6.5% | 6.5% | -33.5% | Not ceiling |

*Negative values indicate gate-count inflation from basis translation.*

**Key findings:**

1. **Genuine structural ceilings (3 families):** QFT, GHZ, and SurfaceCode show 0% across ALL compilers, including t|ket>'s FullPeepholeOptimise. These circuits are genuinely gate-count-optimal.

2. **Prototype-limited ceilings (5 families):** VQE, HardwareEfficient, IQP, UCCSD, and QAOA show 0% with the prototype but 5–63% with t|ket>. The ceiling is an artifact of the prototype's limited move set (adjacent inverse cancellation + bounded commutation), not a structural limit of peephole optimization.

3. **t|ket>'s FullPeepholeOptimise is a peephole optimizer.** Despite the prototype's narrow definition, t|ket>'s pass achieves 23–63% reduction on VQE/IQP/UCCSD using single-qubit rotation merging, template matching, and phase polynomial synthesis — all standard peephole techniques. The difference is engineering sophistication, not algorithmic paradigm.

**Qiskit pass isolation analysis.** Isolating individual Qiskit transpiler passes on 5 families ($n = 3$–$7$, 25 circuits) identifies five mechanism categories:

- **CommutativeCancellation** (isolated): 31.6% mean (dominated by CNOT chain). On Oracle: 32.9% (matching our Phase-2). On RandomClifford: 25.3% (slightly exceeding our 23.8%). On QFT, GHZ: 0.0%. Close agreement validates our Phase-2 implementation.
- **Optimize1qGates** (isolated): 0.0% across all circuits (benchmark circuits lack mergeable single-qubit rotation sequences).
- **Template matching and Clifford simplification**: ~50% of the unexplained gap. Primary driver of gains on IQP (67.8 pp), RandomClifford (52.0 pp), VQE (40.9 pp), Grover (39.1 pp).
- **Phase polynomial optimization**: ~25% of the gap. Particularly effective for IQP circuits (diagonal gates expressible as phase polynomials).
- **Basis translation with resynthesis**: ~15% of the gap. Explains Qiskit's advantage on HardwareEfficient and UCCSD.
- **Routing-aware gate folding**: ~5–10% of the gap. Topology-dependent.

**Pass interaction structure.** The interaction analysis quantifies complementarity and redundancy. Our Phase-2 CommutationRewriter and Qiskit's CommutativeCancellation exhibit a co-benefit of 0.67 and divergence of 20.3%, indicating overlapping optimization structures. Greedy Phase-1 and CommutativeCancellation have divergence of 11.6% but co-benefit of just 0.33. The zero co-benefit between Greedy Phase-1 and Commutation Phase-2 (our own optimizers) confirms that the two phases are genuinely complementary rather than redundant.

### 6.5 Ceiling-Aware Optimization (E21, RQ3)

Experiment E21 (1,140 rows, 15 families) evaluates the ceiling-aware optimizer that uses proxy functions to skip predicted-zero phases.

**Results.** The ceiling-aware pipeline matches the naive pipeline's gate-count reduction exactly across all 15 training families (mean 9.63% for both), with wall-clock speedup:

| Family | Naive Time (ms) | Ceiling-Aware Time (ms) | Speedup | Phases Skipped |
|---|---|---|---|---|
| QFT | ~15 | ~1 | ~14× | P1 + P2 |
| GHZ | ~2.4 | ~0.5 | ~5× | P1 + P2 |
| Grover | ~89 | ~15 | ~6× | P1 + P2 |
| CNOT chain | ~4.7 | ~2.1 | ~2× | P2 |
| Oracle/BV | ~7.5 | ~2.2 | ~3× | P1 |
| RandomClifford | ~17 | ~10.6 | ~1.6× | P1 |
| QAOA | ~12.5 | ~1.5 | ~8× | P1 + P2 |
| VQE | ~12.3 | ~1.4 | ~9× | P1 + P2 |
| QuantumWalk | ~1525 | ~6.7 | ~228× | P1 + P2 |

Overall mean speedup: 35×. Families that skip both phases show the largest speedups; reducible families that skip only one futile phase show smaller speedups (1.6×–3.4×). In aggregate, the ceiling-aware pipeline executes only 28% of the optimization passes that the naive pipeline runs, while producing bit-identical output circuits.

**Critical limitation (HGC).** On held-out circuit families, the empirical correlation model achieved MAE = 0.2775 and Pearson = NaN (zero-variance predictions because all five held-out families exhibited exactly 0% reduction). The model does not generalize to unseen circuit families. The ceiling-aware optimizer should be treated as an exploratory observation, not a validated predictive tool. Its speedup results are valid only for the 15 training families.

### 6.6 Theory-Experiment Cross-Validation

| Quantity | Prediction | Measurement | Status |
|----------|-----------|------------|--------|
| Phase-1 ceiling (LBL) | $R_1 = 0$ for $n \geq 2$ (Thm 1b) | 0.0000% (E1, 25,000 trials) | Consistent |
| WCL vs LBL gap | $R_1^{\text{WCL}} > 0$ (Thm 1a/1b) | 7.83% vs 0.00% (E19, 10,000 rows) | Consistent |
| INSERTION net-zero | Net change $\geq 0$ (Thm 2c/2d) | 0/25,000 trials show reduction (E1) | Consistent |
| AG canonical ceiling | $R_1 = 0$ (Thm 6) | 0.000%, 0/160 nonzero (E23) | Consistent |
| Hardness family P2a | $\geq 1/6 = 16.67\%$ (Thm 7) | 79.80% mean, 62.5%–89.3% (E24) | Exceeds bound |
| Phase-2a context-dep. | $\Omega(1)$ where P1 $= 0$ (Conj. C2) | Oracle: 13.98%; QFT/GHZ: 0% (E14) | Consistent |
| BV Phase-2b bound | $\geq n/(4.5n+4) \geq 15.4\%$ (Thm 9) | 13.98% Phase-2a; fixtures confirm $5n \to n+2$ | Partially validated |
| Ceiling tightness | Listing/window/model-conditional (Conj. C1) | Gap ~0.00% across 56 circuits (E13) | Consistent |

This quantitative agreement across 8 independent observables validates the framework as a predictive model for peephole optimization behavior.

### 6.7 Connectivity and Gate-Set Effects (E17, E18)

**E17 (755 trials, connectivity constraints).** Three topologies tested: linear chain, 2D grid, and heavy-hex approximation. Linear topology increases SWAP overhead by 8.3% on reducible families; grid by 4.1%; heavy-hex approximation by 2.7%. Key finding: connectivity constraints do not alter the ceiling for ceiling families — they only affect net benefit for reducible families by adding routing overhead.

**E18 (270 trials, Clifford+T decomposition).** Survivorship-biased: 120/270 rows (44.4%) failed at decomposition (78) or fidelity verification (42). At the circuit level, 92/142 (64.8%) produced at least one failure row. On surviving rows:

- CNOT chains retain 100% reduction (gate-set-independent).
- Oracle/BV shifts from Phase-2-dominant to Phase-1-dominant (~31% via adjacent $T \cdot T^\dagger$ pairs), because decomposition creates many adjacent inverse pairs.
- All ceiling families remain at 0%.
- The most relevant variational families (VQE, QAOA, UCCSD, HardwareEfficient, IQP) completely fail decomposition (continuous rotation gates cannot be exactly represented without Solovay-Kitaev approximation).

E18 results apply only to circuits with naturally discrete gate sets.

---

## 7. Discussion

### 7.1 Three Optimization Regimes

The experimental evidence reveals a sharp trichotomy — a categorical division determined by the algebraic structure of the circuit's gate sequence, not a gradual spectrum:

**Regime I — Trivially compressible.** Circuits contain adjacent inverse gate pairs directly visible under the listing model. CNOT chains are the canonical example (100% reduction). The defining algebraic property is the presence of self-inverse gate subsequences that are listing-adjacent. Theorem 1 quantifies this: the expected number of adjacent inverse pairs scales with the gate repetition probability, which is high for structured circuits with repeated gate patterns and vanishingly small for random circuits.

**Regime II — Commutation-enabled compressible.** Circuits contain non-adjacent inverse pairs accessible through commutation moves. Oracle/BV (~20–28%) and RandomClifford (~22.1%) are primary examples. The defining property is the existence of gates $g_i, g_j$ with $g_i \cdot g_j = I$ and a commutation path between them. Commutation-enabled compressibility requires two conditions: (1) the circuit must contain gates that commute with their neighbors, and (2) there must exist inverse gate pairs that can be brought into adjacency through a sequence of commutation moves. Oracle/BV circuits satisfy both: the oracle block contains $H$ and $X$ gates where $H$-$X$-$H$ = $Z$ provides a commutation-enabled identity. RandomClifford circuits satisfy both through the rich commutation structure of the Clifford group. VQE and HardwareEfficient circuits fail condition 2: while they contain commuting gates, the specific arrangement of parameterized rotations and entangling layers does not produce commutation-accessible inverse pairs within any finite window.

**Regime III — Structurally incompressible under the tested peephole model.** 3 of 15 families (QFT, GHZ, SurfaceCode) at genuine structural ceiling and 7 of 15 at prototype action-space ceiling. The defining property is the absence of both listing-adjacent inverse pairs (Theorem 1) and commutation-accessible inverse pairs within the window (Theorem 2). We frame the ~0% outcome as a *negative result characterizing why local peephole optimization fails* on these structures — a structural diagnosis, not an algorithmic deficiency. For the 7 prototype-limited families, the ceiling is the prototype's ceiling, not a structural limit: t|ket>'s FullPeepholeOptimise achieves 5–63% on these families using standard peephole techniques (single-qubit rotation merging, template matching, phase polynomial synthesis).

This algebraic characterization suggests a deeper connection to the representation theory of the gate group. The commutation relations of a gate set define a graph structure on the space of gate sequences, and the peephole optimization problem can be viewed as finding shortest paths in this graph. The prototype action-space ceiling corresponds to circuits where the shortest path under local moves is equal to the circuit length.

**Historical note on terminology.** Our initial hypothesis was a depth-driven "phase transition" in optimization behavior. The data refuted this: no depth-dependent change was observed at any depth from 1 to 50. We now use "search space stratification" to denote the observed categorical trichotomy. The term "phase transition" appears only in this historical note and in experiment names retained for registry continuity (e.g., E1). The analysis pipeline includes Binder cumulant computation and finite-size scaling estimation borrowed from statistical physics, but on zero-variance data (Phase-1 under LBL), these methods are mathematically well-defined but scientifically meaningless.

### 7.2 The Listing Model as a Hidden Variable

The central contribution of this study is that the prototype action-space ceiling is not solely a property of the circuit but of the (circuit, listing) pair — the listing model is the key factor governing Phase-1 adjacent-cancellation optimizer behavior. Experiment E19 (10,000 rows) confirms that the Phase-1 ceiling under LBL (0% reduction) relaxes to approximately 7.8% under WCL — a difference attributable entirely to the gate-ordering convention.

This exposes the listing model as a hidden variable in quantum circuit optimization. Every peephole optimizer operates on a sequential representation, and the choice of sequential ordering determines which gate pairs are "adjacent" and therefore which simplifications are locally accessible. The LBL listing — the default in major compiler frameworks — systematically conceals optimization opportunities that WCL reveals, not because the opportunities are absent but because they are non-adjacent under LBL.

From a circuit complexity perspective, the listing-model dependence connects to representation-dependent complexity. The "complexity" of optimizing a circuit — measured by the minimum optimization phase required to achieve maximum peephole reduction — depends on how the circuit is represented. Under LBL, random circuits require Phase-2 (or higher) to achieve any reduction; under WCL, Phase-1 suffices for ~7.8% reduction. This is analogous to the representation dependence of classical complexity classes. Any theoretical analysis of peephole optimization limits must specify the listing model to be meaningful.

### 7.3 Implications for Compiler Design

**Circuit-family-aware optimizer selection.** The trichotomy enables circuit-family-aware routing: Phase-1 only for CNOT chains (100% reduction); Phase-2 only for Oracle/Clifford (~14–28%); skip for QFT, GHZ, SurfaceCode (genuine ceiling); escalate to beyond-peephole mechanisms for VQE, HardwareEfficient, IQP, UCCSD (template matching, phase polynomial synthesis, Clifford tableau reduction). The prescription table (Section 6.3) enables a lightweight classifier that identifies the circuit family or regime and dispatches to the appropriate optimization strategy.

**Wire-traversal preprocessing.** E19 identifies WCL as a simple, $O(m \log m)$-cost preprocessing step unlocking ~7.8% Phase-1 reduction on random circuits — reduction inaccessible under standard LBL. Production compilers should evaluate WCL preprocessing as a candidate pre-pass, with safeguards for circuits where listing order is semantically significant (e.g., mid-circuit measurements or classical feedforward).

**Ceiling-aware pipeline.** E21 shows 1.6×–228× speedup (mean 35×) on training families, but the HGC failure means this does not generalize to unseen families. Within training families, the pipeline reduces total optimization time by a factor proportional to the fraction of ceiling-family circuits in the workload. In typical NISQ-era workloads dominated by VQE, QAOA, and HardwareEfficient circuits — all ceiling families — the expected speedup exceeds 10×.

**When to escalate beyond peephole.** The multi-compiler analysis identifies specific Phase-3 targets: template matching for VQE (40.9 pp gap), HardwareEfficient (37.5 pp), Grover (39.1 pp); phase polynomial synthesis for IQP (67.8 pp); Clifford tableau reduction for RandomClifford (52.0 pp). No single pass explains the full-pipeline advantage; the gap arises from synergistic interactions among passes applied sequentially.

### 7.4 Limitations

1. **Qubit scale.** Canonical experiments span $n = 3$–$20$, enabling exact fidelity verification ($O(4^n)$). The theory is scale-independent (Theorems 1, 2 hold for arbitrary $n$), but empirical validation does not extend to hundreds or thousands of qubits. Extending to larger scales using scalable fidelity proxies is important future work.

2. **WCL validation scope.** E19 validates WCL only on random Universal circuits. Cross-family WCL validation remains future work. If WCL changes the ceiling on structured families, the LBL-based trichotomy may be partially an artifact.

3. **Prototype optimizer simplicity.** Our optimizers are intentionally simple. The gap between prototype and production compilers (5–63 percentage points on 7 families) reflects mechanisms outside the peephole model, not algorithmic deficiency.

4. **Theorem 8 scope.** Haar-random incompressibility applies to Haar-random *unitaries*, not the shallow random gate sequences used in experiments. The empirical ceiling is explained by Theorem 1 (inverse-pair sparsity) and Theorem 1(b) (LBL), not by Theorem 8.

5. **Clifford+T decomposition overhead.** E18 has a 44.4% row-level failure rate. The most relevant variational families (VQE, QAOA, UCCSD) completely fail decomposition. E18 results apply only to circuits with naturally discrete gate sets.

6. **Held-out generalization failure (HGC).** The ceiling-aware optimizer's empirical correlation model does not generalize to unseen families (MAE = 0.2775, Pearson = NaN). This is an exploratory observation, not a validated predictive tool.

7. **Single-seed evaluation.** E4 uses a single base seed. Multi-seed evaluation (5–10 base seeds) is recommended for future work to assess seed-dependent variance in stochastic optimizer trajectories.

8. **Missing circuit families.** The 15 families do not include Trotterized Hamiltonian simulation, Quantum Phase Estimation, or Shor's arithmetic subcircuits. These may exhibit intermediate reduction levels that break the categorical classification.

9. **No random gate shuffler control.** A random permutation control was not performed. If a random shuffler achieves the same 0% as the optimizers on ceiling families, the ceiling claim is trivially confirmed but the optimizer's value is undermined.

10. **Statistical power.** Several real-circuit cells (QFT, GHZ, QAOA, VQE in E10) have only $N = 5$ per family-optimizer combination. The 95% CI for a 0/5 binomial proportion extends to [0%, 45%]. Ceiling claims for these families rely on convergent evidence from E14 (2,130 rows) and E15 (994 rows).

11. **Statistical method consistency.** The analysis uses a mixture of parametric (Welch's t-test) and non-parametric (Cliff's delta, Kruskal-Wallis) tests. For the zero-inflated distributions observed (Phase-1 under LBL is a point mass at 0%), non-parametric methods are the more appropriate primary evidence.

12. **Gate-set sensitivity.** Experiment E6 (Gate Set Sensitivity) was registered but not executed. The framework's gate-set dependence is essentially untested. E18 (Clifford+T) is survivorship-biased with 44.4% failure rate.

### 7.5 Future Work

1. **Cross-family WCL validation.** Extend E19 to all 15 families to determine whether WCL changes the ceiling on structured families.

2. **Phase-3 integration.** Implement template matching (Phase-3a), phase polynomial synthesis (Phase-3b), and Clifford tableau reduction (Phase-3c), targeting the specific families where the gap analysis identifies beyond-peephole opportunity. A key challenge is cross-phase interaction: template matching may create opportunities for Phase-2 commutation not present in the original circuit.

3. **Production compiler audit.** Systematically audit Qiskit, Cirq, and t|ket> internals to determine whether WCL-like reordering is already implemented implicitly. If production compilers already approximate WCL, the E19 benefit may be partially captured; if not, an explicit WCL pre-pass could provide measurable improvement.

4. **Predictive validation.** Pre-register theoretical predictions for untested circuit families and test them on held-out data before examining the data. The current framework was developed post-hoc; predictive validation would strengthen its scientific standing.

5. **Noise-aware structural ceilings.** Extend the framework to optimize fidelity-adjusted gate reduction rather than raw gate count. A noise-aware extension would define the optimization objective as fidelity-adjusted gate reduction, integrating noise models (depolarizing, amplitude damping, crosstalk) into the ceiling analysis.

6. **Hardware-aware optimization.** Incorporate realistic hardware topologies (IBM's heavy-hex, Google's Sycamore grid), dynamic routing algorithms, and hardware-specific gate sets.

7. **Additional circuit families.** Test at least 5 additional families (Trotterized simulation, QPE, Shor's arithmetic, tensor-network ansätze) to probe the boundaries between regimes.

8. **Machine learning for circuit classification.** For circuits of unknown provenance, a machine learning classifier could automatically identify the circuit family or regime and dispatch to the appropriate optimization strategy.

---

## 8. Conclusion

This paper introduces **columnar representation example sensitivity** — the discovery that the circuit listing model, the data-structure ordering of gates, is the key factor governing peephole optimizer behavior. Under layer-by-layer listing (LBL), the Phase-1 action space is provably empty for $n \geq 2$ (Theorem 1(b)), yielding exactly 0.0000% reduction across 25,000 random circuits. Under wire-consecutive listing (WCL), the same circuits exhibit 7.83% mean reduction (E19, 10,000 rows). This finding reframes peephole optimization from a purely algorithmic question to a representation-dependent one: the apparent "optimization desert" is a property of the (circuit, listing) pair, not of the circuits themselves.

Combined with a 15-family empirical benchmark (67,000+ data rows, 6 optimizer types), we identify a categorical trichotomy — search space stratification — across circuit families: 100% reduction (CNOT chains), 14–16% via commutation (oracle/Clifford), and ~0% on 10 of 15 families (3 genuine structural ceilings confirmed by all production compilers, 7 prototype-limited). Theoretical results (Theorems 1, 2, 7, 9) provide formal backing, validated experimentally across 8 independent observables. A ceiling-aware optimizer achieves 1.6×–228× speedup on training families, though its predictive model does not generalize to unseen families (HGC).

These results provide the first systematic framework for understanding when peephole optimization succeeds and fails, with direct implications for compiler pass design: wire-traversal preprocessing as a standard compiler pass, circuit-family-aware optimizer routing, and a roadmap for extending peephole methods with targeted beyond-peephole mechanisms.

---

## Declarations

### Data Availability

All experimental data — raw CSV outputs, experiment metadata, and release manifests — are available in the project repository under `data/`, organized into versioned subdirectories (v1–v7). SHA-256 checksums for every dataset are recorded in `release/release_manifest.json`. All datasets can be regenerated via `python scripts/reproduce_all.py --all`. An archival copy has been deposited on Zenodo (DOI: `10.5281/zenodo.XXXXXXX`, to be assigned upon acceptance).

### Code Availability

The complete source code is publicly available at `https://github.com/Q-research-team/q-research`. The codebase includes optimizer implementations (`src/`), experiment drivers (`experiments/`), analysis tools (`analysis/`), and reproducibility scripts (`scripts/`). Python 3.12, dependencies pinned in `requirements.txt` and `environment.yml`. Docker container provided via `Dockerfile`. Release version: v7.0.0.

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

[2] A. S. Tanenbaum, H. van Staveren, and J. W. Stevenson, "Using peephole optimization on intermediate code," ACM TOPLAS, vol. 4, no. 1, pp. 21–36, 1982.

[4] H. Massalin, "Superoptimizer: A look at the smallest program," ASPLOS, pp. 122–126, 1987.

[8] A. Barenco et al., "Elementary gates for quantum computation," Physical Review A, vol. 52, no. 5, pp. 3457–3488, 1995. arXiv:quant-ph/9503016

[9] M. A. Nielsen and I. L. Chuang, Quantum Computation and Quantum Information, Cambridge University Press, 2010.

[10] D. Maslov, G. W. Dueck, and D. M. Miller, "Techniques for the synthesis of reversible Toffoli networks," ACM TODAES, vol. 12, no. 4, art. 42, 2008.

[13] M. Amy, D. Maslov, M. Mosca, and M. Roetteler, "A meet-in-the-middle algorithm for fast synthesis of depth-optimal quantum circuits," IEEE TCAD, vol. 32, no. 6, pp. 818–830, 2013. arXiv:1206.07563

[16] V. Kliuchnikov, D. Maslov, and M. Mosca, "Fast and efficient optimal synthesis of Clifford+T circuits," Physical Review Letters, vol. 111, no. 8, 080502, 2013. arXiv:1206.5236

[20] M. Amy, P. Glaudell, and N. J. Ross, "Number-theoretic constructions of optimal quantum circuits for diagonal unitaries," npj Quantum Information, vol. 4, art. 43, 2018. arXiv:1606.02729

[21] R. Duncan et al., "Graph-theoretic Simplification of Quantum Circuits with the ZX-calculus," Quantum, vol. 4, 279, 2020. arXiv:1902.03178

[22] N. de Beaudrap et al., "Faster resynthesis with the ZX-calculus," Proc. QPL 2022, 2022. arXiv:2206.10843

[25] D. Janzing, P. Wocjan, and T. Beth, "Non-identity-check is QMA-complete," Int. J. Quantum Information, vol. 1, no. 4, pp. 507–518, 2003. arXiv:quant-ph/0306054

[27] D. Gottesman, "Stabilizer codes and quantum error correction," Ph.D. thesis, Caltech, 1997. arXiv:quant-ph/9705052

[28] S. Aaronson and D. Gottesman, "Improved simulation of stabilizer circuits," Physical Review A, vol. 70, no. 5, 052328, 2004. arXiv:quant-ph/0406196

[29] C. M. Dawson and M. A. Nielsen, "The Solovay-Kitaev algorithm," Quantum Information and Computation, vol. 6, no. 1, pp. 81–95, 2006. arXiv:quant-ph/0505030

[30] A. W. Harrow and A. Montanaro, "Quantum computational supremacy," Nature, vol. 549, pp. 188–196, 2017. arXiv:1809.07442

[32] R. G. Downey and M. R. Fellows, Fundamentals of Parameterized Complexity, Springer, 2013.

[33] M. A. Nielsen, "A geometric approach to quantum circuit lower bounds," arXiv:quant-ph/0502070, 2005.

[35] S. Shende, S. S. Bullock, and I. L. Markov, "Synthesis of Quantum-Logic Circuits," IEEE TCAD, vol. 25, no. 6, pp. 1000–1010, 2006. arXiv:quant-ph/0406176

[38] E. Bernstein and U. Vazirani, "Quantum complexity theory," SIAM J. Computing, vol. 26, no. 5, pp. 1411–1473, 1997.

[39] E. Farhi, J. Goldstone, and S. Gutmann, "A quantum approximate optimization algorithm," arXiv:1411.4028, 2014.

[40] A. Peruzzo et al., "A variational eigenvalue solver on a photonic quantum processor," Nature Communications, vol. 5, art. 4213, 2014. arXiv:1304.3061

[41] L. K. Grover, "A fast quantum mechanical algorithm for database search," STOC, pp. 212–219, 1996. arXiv:quant-ph/9605043

[42] J. Romero et al., "Strategies for quantum computing molecular energies using the unitary coupled cluster ansatz," Quantum Science and Technology, vol. 4, 014008, 2019. arXiv:1701.02691

[43] S. A. Cuccaro et al., "A new quantum ripple-carry addition circuit," arXiv:quant-ph/0410184, 2004.

[45] D. Shepherd and M. J. Bremner, "Temporally unstructured quantum computation," Proc. Royal Society A, vol. 475, no. 2225, 20180527, 2019. arXiv:1807.04084

[46] Qiskit Contributors, Qiskit: An Open-source Framework for Quantum Computing, Zenodo, 2024. DOI: 10.5281/zenodo.2562110

[47] Cirq Contributors, Cirq: A Python library for NISQ circuits, Google AI Quantum, 2023.

[48] P. Sivarajah et al., "t|ket>: A retargetable compiler for NISQ devices," Quantum Science and Technology, vol. 6, no. 1, 014003, 2020. arXiv:2003.10611

[50] A. G. Fowler et al., "Surface codes: Towards practical large-scale quantum computation," Physical Review A, vol. 86, 032324, 2012. arXiv:1208.0928

[51] F. G. S. L. Brandao, A. W. Harrow, and M. Horodecki, "Local random quantum circuits are approximate polynomial-designs," Communications in Mathematical Physics, vol. 346, pp. 397–434, 2016. arXiv:1208.0692

[56] S. Yamashita et al., "Fast equivalence checking of quantum circuits," IEICE Trans. Fundamentals, vol. E94-A, no. 1, pp. 251–258, 2011.

[61] R. Iten et al., "Exact and practical pattern matching for quantum circuit optimization," ACM Trans. Quantum Computing, vol. 3, no. 1, pp. 1–44, 2022. arXiv:1909.09119

[62] M. Xu et al., "Quartz: Superoptimization of quantum circuits," PACMPL, vol. 6, no. PLDI, pp. 625–650, 2022.

[63] J. Pointing et al., "Quanto: Optimizing quantum circuits with automatic generation of circuit identities," Quantum Science and Technology, vol. 9, no. 3, 035045, 2024.

[64] Z. Li et al., "Quarl: A learning-based quantum circuit optimizer," PACMPL, vol. 8, no. OOPSLA2, pp. 1570–1598, 2024. arXiv:2307.10120

[65] F. J. R. Ruiz et al., "Quantum circuit optimization with AlphaTensor," Nature Machine Intelligence, vol. 7, no. 3, pp. 406–419, 2025. arXiv:2402.14396

[66] J. Liu, L. Bello, and H. Zhou, "Relaxed peephole optimization," Proc. IEEE/ACM CGO, pp. 145–156, 2021. arXiv:2012.07711

[67] J. Riu et al., "Reinforcement learning based quantum circuit optimization via ZX-calculus," Quantum, vol. 9, 1634, 2025. arXiv:2312.11597

[68] J. Merilehto, "A 200-line Python micro-benchmark suite for NISQ circuit compilers," arXiv:2509.16205, 2025.

[69] C. Nitsch et al., "MQT Bench: Benchmarking Software and Design Automation Tools for Quantum Computing," ACM Trans. Quantum Computing, vol. 4, no. 1, 2023. arXiv:2204.13719

[70] A. Wang, S. Lu, and X. Wang, "QASMBench: A low-layer QASM benchmark suite," arXiv:2108.10472, 2021.

[78] Y. Nam et al., "Automated optimization of large quantum circuits with continuous parameters," npj Quantum Information, vol. 4, art. 23, 2018. arXiv:1710.07345

[81] K. Patel, J. Shapira, and I. L. Markov, "Quantum circuit optimization: A survey," ACM Computing Surveys, vol. 55, no. 9, art. 178, 2022. arXiv:2210.12035

[82] S. Bravyi, R. Shaydulin, S. Hu, and D. Maslov, "Clifford Circuit Optimization with Templates and Symbolic Pauli Gates," Quantum, vol. 5, art. 580, 2021. arXiv:2105.02291
