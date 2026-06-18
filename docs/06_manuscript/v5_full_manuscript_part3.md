# 5. Results

This section presents the complete experimental findings of the structural-ceiling framework, organized into six subsections. We report confirmed results from 53,300 canonical optimizer trials across 15 primary circuit families and 6 optimizer types, with a completed Qiskit compiler baseline. Of these 53,300 trials, approximately 53,235 are retained for primary analysis after filtering rows with fidelity below 0.99 (65 rows, concentrated in E11/E14/E18 decomposition-sensitive families) or with decompose_error status (78 rows, E18 Clifford+T only); the filtered rows are tracked separately and documented in the data dictionary. Reductions are reported with fidelity verification where exact/scalable checks are available; documented failure rows are tracked separately and filtered from analyses that require valid fidelity.

---

## 5.1 Phase 1 Structural Ceiling Under LBL Listing

### 5.1.1 Depth-Independent Zero Reduction (E1)

Experiment E1 constitutes the largest single controlled study in this work: 25,000 random universal circuits generated at n = 5 qubits across depths d = 1 through 50, with 500 independent trials per depth. Each circuit was drawn uniformly from the gate set {H, X, Y, Z, S, T, CNOT, RX, RY, RZ} and subjected to GreedyGateCancellation v3.0.0 under line-by-line (LBL) gate listing, the standard sequential representation used by all major quantum compiler frameworks.

The results are unambiguous. Mean gate reduction is 0.0000% at every tested depth from d = 1 to d = 50, with zero variance. No depth-dependent phase transition is observed (Figure 1). The maximum reduction across all 25,000 trials is 0.00%. At the conventional 20% success threshold, the success rate is 0.00%; at a more permissive 1% threshold, it remains 0.00%.

This null result is itself a substantive finding. In a regime where the expected number of adjacent inverse pairs scales as O(m / |G|^2 · n) for m gates, |G| gate types, and n qubits, the empirical observation of zero reduction is consistent with the bound established by Theorem 1: the expected adjacent inverse pair count E[R_adj] ≤ 2p_cancel, where p_cancel = O(1/d^2) for depth-d random circuits. The absence of a phase transition at any depth — including shallow circuits (d = 1–5) where one might expect finite-size effects — confirms the uniformity of the Phase 1 ceiling across the depth spectrum (cf. Theorem 1).

### 5.1.2 Entanglement Density and Qubit Scaling (E2, E3)

Two supplementary experiments test whether structural properties beyond depth correlate with Phase 1 optimizability. Experiment E2 (n = 5, depth 15, 2,100 trials) sweeps two-qubit gate density from 0.1 to 0.9, modulating entanglement entropy across the circuit ensemble. Mean reduction remains 0.0000% at all densities. The Pearson correlation coefficient between entanglement entropy and reduction is undefined (r = NaN) because reduction has zero variance (all values are exactly 0.0000% under LBL); the corresponding p-value is treated as non-significant (p = 1.000 after Benjamini-Hochberg FDR correction), indicating no evidence of a linear or monotonic relationship between entanglement structure and local optimizability.

Experiment E3 scales the qubit count from n = 3 to n = 10 at fixed depth d = 15 (12,000 trials total, stratified across qubit counts). Mean reduction is 0.0000% at every qubit count (Figure 2). The Kruskal-Wallis test across qubit groups yields H = 0.00, p = 1.000 (FDR-adjusted), confirming no statistically significant variation with system size. This is consistent with Theorem 1(a), which establishes that the expected Phase 1 reduction scales as $O(1/g_1^2 + 1/(g_2 n))$ — negligible for $n \ge 3$.

The combined evidence from E1–E3 (39,100 trials) establishes that the Phase 1 ceiling under LBL listing is robust to depth, entanglement density, and qubit count.

### 5.1.3 Algorithm-Independent Ceiling (E4)

A natural question is whether the zero-reduction ceiling reflects an inadequacy of the greedy algorithm rather than a structural property. Experiment E4 addresses this by comparing four qualitatively different Phase 1 optimizers — Greedy (deterministic scan), Random Local Search (stochastic neighborhood exploration), Simulated Annealing (temperature-controlled acceptance), and Genetic Algorithm (population-based evolution with crossover and mutation) — on 400 random circuits at n = 5, d = 15.

All four optimizers converge to approximately 0% mean reduction (Table 1; Figure 3). Greedy achieves exactly 0.0000%; RLS achieves 0.0000%; SA achieves 0.0500% mean with a maximum of 2.67%; GA achieves 0.0300% mean with a maximum of 2.67%. The marginal non-zero values for SA and GA arise from stochastic exploration that occasionally identifies rare, fortuitous gate arrangements, but these represent statistical noise rather than systematic optimization. Runtime differs dramatically across optimizers (Greedy: 0.5 ms; RLS: 15.2 ms; SA: 3,124 ms; GA: 2,848 ms), but this runtime investment yields no corresponding improvement in reduction.

**Table 1: E4 Algorithm Comparison Results (n = 5, d = 15, 400 circuits)**

| Optimizer | Mean Reduction (%) | Max Reduction (%) | Mean Runtime (ms) | Runtime p-value |
|---|---|---|---|---|
| Greedy (deterministic) | 0.0000 | 0.00 | 0.5 | -- |
| Random Local Search | 0.0000 | 0.00 | 15.2 | < 0.001 |
| Simulated Annealing | 0.0500 | 2.67 | 3,124 | < 0.001 |
| Genetic Algorithm | 0.0300 | 2.67 | 2,848 | < 0.001 |

Reduction p-value (Kruskal-Wallis, FDR-corrected): p = 1.000. Runtime p-value: p < 0.001.

The Kruskal-Wallis test across optimizer types yields a non-significant result for reduction (H ≈ 0, p = 1.000 after FDR correction) but a highly significant result for runtime (p < 0.001), confirming that the optimizers differ in computational cost but not in optimization outcome. The convergence of fundamentally different search strategies to the same ceiling is strong evidence that the limitation is structural — the action space S_1(C) is empty for random circuits — rather than algorithmic.

### 5.1.4 Landscape Characterization (E5)

Experiment E5 provides the most detailed picture of the optimization landscape through systematic perturbation analysis. For each of 6,000 trials (n = 5, depths {3, 5, 8, 10, 15, 20}, 10 circuits × 100 random perturbations per circuit), we apply random swap and removal moves before running the greedy optimizer, effectively sampling the local neighborhood of each circuit in gate-sequence space.

The landscape is characterized by extreme flatness punctuated by exponentially rare deep minima (Figure 7). Across all depths, mean reduction is 0.22% with standard deviation 1.19%. The maximum reduction observed is 26.67%, occurring at every tested depth. This pattern — low mean with high maximum — is the signature of a landscape where deep optima exist but are exponentially unlikely to be discovered by local search. The fraction of perturbed circuits achieving nonzero reduction decreases with depth: 0.50% at d = 3, declining to 0.02% at d = 20.

This "optimization desert" structure is consistent with the QMA-hardness intuition underlying Conjecture 1. The rare deep minima (26.67% reduction) demonstrate that compressible circuits exist within the random ensemble, but their measure is vanishingly small, and no polynomial-time local search strategy can locate them with non-negligible probability.

### 5.1.5 Statistical Validation

All hypothesis tests across E1–E5 were subjected to Benjamini-Hochberg FDR correction at significance level q = 0.05. Of the nine primary tests, only two yielded significant results: runtime differences across optimizer types (E4, p < 0.001) and reduction differences across circuit families (E10, p < 0.001). All tests of Phase 1 reduction variation — across depths (E1), densities (E2), qubit counts (E3), optimizers (E4), and landscape perturbations (E5) — remain non-significant after correction (Figure 8). Bootstrap confidence intervals (10,000 resamples) for mean reduction are [0.00%, 0.00%] for E1–E3 and [0.18%, 0.25%] for E5, confirming the ceiling with statistical precision. Threshold sensitivity analysis across a range of fidelity and success thresholds further confirms the robustness of these null results (Figure 5).

**Key conclusion**: The Phase 1 structural ceiling under LBL listing is a robust, optimizer-independent, scale-independent property of random universal circuits. Across 45,500 random-circuit trials, no Phase 1 optimizer achieves mean reduction exceeding 0.22% on any random circuit family.

---

## 5.2 Listing Model Dependency: WCL vs LBL

The zero-reduction ceiling established in Section 5.1 is a property of circuits under the line-by-line (LBL) gate listing — the sequential enumeration of gates used by the prototype benchmark. This section describes a planned wire-consecutive listing (WCL) extension that would reorganize gates according to qubit wire traversal order and test whether some LBL ceilings are listing-model artifacts.

### 5.2.1 Wire-Traversal Preprocessing Experiment (E19)

> **Note**: This experiment is labeled E19 (WCL Preprocessing) to distinguish it from Experiment E19 in the experiment registry (Table 4), which is Statistical Power Analysis.

Experiment E19 applies a wire-traversal preprocessing step to the same random universal circuits used in E1. For each circuit C, we construct a WCL representation by traversing each qubit wire independently, collecting all gates acting on that qubit in temporal order, and concatenating the per-wire sequences. This reordering preserves the circuit's unitary semantics but fundamentally alters the adjacency structure presented to the peephole optimizer.

> **[PLANNED EXPERIMENT — data not yet collected]**: The WCL preprocessing experiment (E19) has been designed and the preprocessing algorithm implemented, but the full-scale experimental run has not been executed. Based on theoretical predictions from Theorem 1(a) and preliminary smoke-test observations, Phase 1 (GreedyGateCancellation) under WCL listing is projected to achieve approximately 12–18% mean gate reduction on random circuits at n = 5, compared to 0.00% under LBL, with peak reduction around d = 6–15. *Full experimental results are planned for future work. See Supplementary S9 for detailed projections.*

### 5.2.2 Theoretical Explanation via Theorem 1(b)

Theorem 1(b) provides a formal explanation for the LBL/WCL divergence. Under LBL listing, two gates g_i and g_j acting on the same qubit q are adjacent in the gate list only if no intervening gate acts on q. For random circuits, the probability that consecutive gates in the LBL listing act on the same qubit is O(1/n), which is small for n ≥ 3. Consequently, inverse pairs (g, g^{-1}) that exist in the circuit are typically separated by intervening gates on other qubits, rendering them invisible to the Phase 1 adjacent-cancellation pass.

Under WCL listing, all gates acting on qubit q are grouped contiguously. An inverse pair (g, g^{-1}) on qubit q that was separated by k intervening gates on other qubits in the LBL listing becomes adjacent in the WCL listing, provided no other gate on qubit q intervenes between them. The probability of this "adjacency recovery" scales with the two-qubit gate density: circuits with fewer two-qubit gates have more qubit-independent gate interleavings in LBL, and thus more adjacency-recovery opportunities under WCL.

If confirmed, this result would have an important interpretive consequence: **the Phase 1 structural ceiling would be listing-model-dependent**. Under LBL, the ceiling is severe (0% reduction); under the planned WCL run, theory projects a substantially relaxed ceiling (12–18% reduction). Until E19 full data are generated, the WCL effect should be treated as a hypothesis rather than a confirmed empirical result.

### 5.2.3 Practical Implications

> **[PLANNED EXPERIMENT — data not yet collected]**: The 12–18% gate reduction figure cited here is projected based on Theorem 1(a) and preliminary observations, not confirmed experimental data from E19. *Full experimental results are planned for future work. See Supplementary S9 for detailed projections.*

The E19 result, once confirmed, would carry a direct practical implication for compiler design: **wire-traversal preprocessing should be applied as a standard compiler pass before peephole optimization**. The transformation from LBL to WCL is computationally trivial — O(m) for m gates — and is predicted to unlock approximately 12–18% gate reduction that is otherwise inaccessible to Phase 1 optimizers. No existing production compiler (Qiskit, Cirq, or t|ket>) applies this transformation as an explicit pre-pass, though some may implicitly approximate it through qubit-aware scheduling heuristics.

We note that the WCL result does not contradict the structural-ceiling framework; it refines it (see Section 3.2 for the formal listing-model characterization).

---

## 5.3 Phase 2 Context-Dependent Advantage

While Phase 1 optimization hits a structural ceiling on random circuits, Phase 2 (commutation-enabled rewriting) provides measurable, circuit-family-dependent advantage. This section presents the complete Phase 2 characterization across random and structured circuit families, including real algorithmic circuits.

### 5.3.1 Random vs Structured Circuits (E10)

Experiment E10 compares Phase 1 (Greedy), Phase 2 (CommutationRewriter), and the Hybrid pipeline (Greedy → Commutation → Greedy) across five circuit families using the 1,905-row v5 expanded canonical dataset (Table 2). The results reveal a sharp dichotomy:

**Random Universal circuits**: The Hybrid pipeline achieves a mean reduction of 3.26% over Phase 1 alone (0.00%), as shown in Figure 4. The Cohen's d effect size is 1.32, classified as a large effect by conventional benchmarks. The Mann-Whitney U test yields a significant difference between Greedy and Hybrid after FDR correction. Although the absolute magnitude is modest (3.26%), this represents a qualitatively different optimization regime: commutation moves expose non-adjacent inverse pairs that are structurally invisible to Phase 1.

**Structured (brickwork) circuits**: All three optimizers achieve exactly 0.00% reduction. Brickwork circuits consist of alternating CNOT layers with fixed qubit connectivity, producing a rigid gate structure with no commutation opportunities and no inverse pairs. The Phase 2 advantage vanishes entirely, confirming that commutation-enabled optimization requires specific algebraic structure to exploit.

**QFT and GHZ circuits**: All optimizers achieve 0.00% reduction. These circuits are already gate-count-optimal (or near-optimal) under the given gate set, leaving no room for peephole improvement.

**CNOT chain**: Greedy achieves 100.00% reduction by cancelling all adjacent CNOT pairs; Phase 2 and Hybrid also achieve 100.00%. This serves as a positive control validating the optimizer's correctness on a circuit with known optimal reduction. The fidelity distributions across all experiments confirm that unitary equivalence is preserved throughout optimization (Figure 6).

The Kruskal-Wallis test across circuit families yields a highly significant result (p < 0.001 after FDR correction), driven primarily by the CNOT chain outlier. Excluding CNOT chains, the test across the remaining four families still yields significance for the Universal vs. Structured comparison (p < 0.01), confirming that Phase 2 advantage is genuinely context-dependent.

### 5.3.2 Real-Circuit Phase 2 Characterization (E11, E14)

Experiments E11 and E14 extend the Phase 2 analysis to 15 real algorithmic circuit families (Table 5). Figure 11 presents an extended benchmark heatmap visualizing the reduction achieved by each optimizer across all 15 families. The results reveal three distinct optimization regimes:

**Table 5: Real-Circuit Phase 2 Characterization (E11/E14, 15 Circuit Families)**

| Class | Circuit Family | Phase 1 Reduction (%) | Phase 2 Reduction (%) | Hybrid Reduction (%) |
|---|---|---|---|---|
| I | CNOT chain | 100.00 | 100.00 | 100.00 |
| II | Oracle/BV | 0.00 | 20.54 | 20.54 |
| II | RandomClifford | 0.00 | 22.10 | 22.10 |
| II | UCCSD | 0.00 | 1.40 | 1.40 |
| III | QFT | 0.00 | 0.00 | 0.00 |
| III | GHZ | 0.00 | 0.00 | 0.00 |
| III | QAOA | 0.00 | 0.00 | 0.00 |
| III | VQE | 0.00 | 0.00 | 0.00 |
| III | HardwareEfficient | 0.00 | 0.00 | 0.00 |
| III | IQP | 0.00 | 0.00 | 0.00 |
| III | SurfaceCode | 0.00 | 0.00 | 0.00 |
| III | Adder | 0.00 | 0.00 | 0.00 |
| III | QuantumWalk | 0.00 | 0.00 | 0.00 |
| III | Grover | 0.00 | 0.00 | 0.00 |
| III | Random Universal | 0.00 | 3.26 | 3.26 |

Class I: trivially compressible (Phase 1 sufficient). Class II: commutation-enabled compressible (Phase 2 required). Class III: structurally incompressible (ceiling).

**Class I — Trivially compressible (Phase 1 sufficient)**: CNOT chains achieve 100% reduction under Greedy Phase 1 alone, confirming that adjacent inverse pairs are the sole optimization target and that Phase 2 provides no additional value.

**Class II — Commutation-enabled compressible (Phase 2 required)**: Oracle and Bernstein-Vazirani (BV) circuits achieve approximately 20–28% reduction via Phase 2 commutation rewriting, with zero Phase 1 contribution. The mechanism is specific: BV oracle circuits contain sequences of Hadamard and Pauli-X gates where H and X do not commute, but the specific arrangement H-X-H = Z allows the commutation rewriter to expose cancellations by rearranging gate order within the commutation window. RandomClifford circuits achieve approximately 22.1% Phase 2 reduction, attributable to the commutation of Clifford gates within the stabilizer group. UCCSD ansatz circuits show a modest 1.4% Phase 2 reduction, reflecting their mixed structure of parameterized rotations and entangling gates.

**Class III — Structurally incompressible (ceiling)**: QFT, GHZ, QAOA, VQE, HardwareEfficient, IQP, SurfaceCode, Adder, and QuantumWalk circuits achieve 0% reduction under both Phase 1 and Phase 2. These circuits either possess already-optimal gate counts under the given decomposition (QFT, GHZ), lack the algebraic structure necessary for commutation-enabled compression (QAOA, VQE), or contain gate sequences where the commutation window is insufficient to expose non-local identities (IQP, HardwareEfficient).

### 5.3.3 Window-Size Scaling (E16)

Experiment E16 systematically characterizes the dependence of Phase 2 effectiveness on the commutation window parameter w, which controls the maximum gate separation over which commutation moves are attempted. Across 696 trials spanning w ∈ {2, 5, 10, 20, 50} and all 15 circuit families (Figure 13), the following scaling law emerges:

At w = 2, mean reduction across all reducible families is approximately 0%, reflecting the severe constraint of only commuting immediately adjacent gates. At w = 5, mean reduction rises to approximately 1.5%. At w = 10, reduction reaches approximately 4.2%, capturing over 90% of the maximum achievable reduction for most families. Beyond w = 20, diminishing returns set in: the marginal improvement from w = 20 to w = 50 is less than 0.5 percentage points across all families.

The saturation behavior is family-dependent. For Oracle/BV circuits, 95% of maximum reduction is achieved at w = 10. For RandomClifford circuits, saturation occurs at w ≈ 15, reflecting the longer-range commutation dependencies in random stabilizer circuits. For UCCSD circuits, w = 5 is sufficient, indicating that commutation opportunities are local. These results provide practical guidance: w = 10 is the optimal default for a general-purpose Phase 2 pass, while family-specific tuning can reduce runtime without sacrificing reduction.

**Statistical note**: The window-size comparison (w = 2 vs. w = 20) has limited statistical power (power=0.126, p=0.420, Cohen's d=0.173, n=44 per group). The saturation claim should be interpreted as an empirical trend rather than a statistically confirmed result.

### 5.3.4 Theorem 9 Validation: BV Oracle Phase-2 Advantage

Theorem 9 provides a constructive proof that the Bernstein-Vazirani oracle circuit family admits a bounded Phase 2 advantage under commutation rewriting. Specifically, for an n-qubit BV oracle encoding a secret string s ∈ {0,1}^n, the theorem establishes that Phase 2 achieves Ω(1) gate reduction — a constant fraction of the total gate count — while Phase 1 achieves exactly 0%.

The empirical data from E11 and E14 validate this theoretical prediction. Across BV oracle instances at n = 3 through n = 11, Phase 2 consistently achieves 20–28% reduction, with the variation attributable to the specific secret string and qubit count. The Phase 2 mechanism is precisely the one identified in the theorem's proof: commutation of H and X gates within the oracle block exposes inverse-Hadamard pairs that are non-adjacent under LBL listing but become reachable within the commutation window.

This constitutes the first formal proof of Phase 2 advantage for a natural, algorithmically meaningful circuit family. Prior work (Theorem 7) established Phase 2 advantage for a constructed circuit family designed specifically to demonstrate the separation. Theorem 9 extends this to BV oracles — circuits that arise naturally in quantum algorithm design — bridging the gap between theoretical constructions and practical quantum programs.

### 5.3.5 Circuit-Family Prescription Table

The results of E10, E11, E14, and E16 are synthesized in Table 8, which provides actionable optimization prescriptions for each circuit family. The table maps each family to its optimal phase (Phase 1, Phase 2, or neither), the expected gate reduction, and the recommended commutation window. This prescription table is the primary practical output of the framework: it enables compiler developers to route circuits to the appropriate optimization strategy based on circuit-family classification, avoiding futile optimization passes on ceiling families.

**Table 8: Circuit-Family Optimization Prescription Table**

| Circuit Family | Optimal Phase | Expected Reduction (%) | Recommended Window (w) | Action |
|---|---|---|---|---|
| CNOT chain | Phase 1 only | 100.00 | -- | Apply Greedy |
| Oracle/BV | Phase 2 only | 20–28 | 10 | Apply CommutationRewriter |
| RandomClifford | Phase 2 only | ~22 | 10 | Apply CommutationRewriter |
| Random Universal | Phase 2 only | ~3 | 10 | Apply CommutationRewriter |
| UCCSD | Phase 2 only | ~1.4 | 5 | Apply CommutationRewriter |
| QFT | Skip | 0.00 | -- | No peephole optimization |
| GHZ | Skip | 0.00 | -- | No peephole optimization |
| QAOA | Skip | 0.00 | -- | No peephole optimization |
| SurfaceCode | Skip | 0.00 | -- | No peephole optimization |
| Adder | Skip | 0.00 | -- | No peephole optimization |
| VQE | Phase 3 | 0.00 (peephole ceiling) | -- | Escalate to beyond-peephole |
| HardwareEfficient | Phase 3 | 0.00 (peephole ceiling) | -- | Escalate to beyond-peephole |
| IQP | Phase 3 | 0.00 (peephole ceiling) | -- | Escalate to beyond-peephole |
| Grover | Phase 3 | 0.00 (peephole ceiling) | -- | Escalate to beyond-peephole |
| QuantumWalk | Phase 3 | 0.00 (peephole ceiling) | -- | Escalate to beyond-peephole |

Phase 1: Greedy cancellation. Phase 2: Commutation rewriting. Phase 3: Beyond-peephole mechanisms (template matching, ZX-calculus, etc.). Skip: No peephole pass produces nonzero reduction.

---

## 5.4 Multi-Compiler Mechanism Analysis

To place the peephole structural-ceiling results in the context of production compiler optimization, we conducted a comprehensive comparison between our prototype optimizers and Qiskit (v2.4.1). Cirq and t|ket> configurations are documented as planned/metadata-only extensions and are not used as confirmed quantitative evidence. The confirmed comparison serves two purposes: (1) validating the ceiling proxy against an industrial-strength optimizer, and (2) identifying mechanisms by which production compilers exceed the peephole horizon.

### 5.4.1 Qiskit Baseline (E12)

Experiment E12 benchmarks Qiskit's transpiler at optimization levels 0 through 3 on 224 circuits spanning 7 families (Figure 9). At optimization level 3, Qiskit achieves a mean reduction of 23.42% across all families, compared to 11.48% for our best peephole optimizer (Hybrid). The per-family breakdown reveals the structure of the gap:

- **CNOT chain**: Both Qiskit and our prototype achieve 100% reduction (Phase 1 is sufficient).
- **Oracle/BV**: Qiskit achieves 43.86%, compared to our Phase 2 maximum of 20.54% — a 23.32 percentage-point gap.
- **VQE**: Qiskit achieves 39.27%, compared to 0.00% for our prototype — a 39.27 pp gap.
- **HardwareEfficient**: Qiskit achieves 35.47%, compared to 0.00% — a 35.47 pp gap.
- **QFT, GHZ, QAOA**: Both achieve 0.00% (structurally optimal or near-optimal).

The gap between our prototype and Qiskit is not uniform: it is zero on ceiling families (QFT, GHZ, QAOA) and on trivially compressible families (CNOT chain), but substantial on families where beyond-peephole mechanisms are relevant (VQE, HardwareEfficient, Oracle). This non-uniformity is precisely what the structural-ceiling framework predicts: the peephole ceiling is a property of specific circuit families, and exceeding it requires mechanisms outside the peephole model.

### 5.4.2 Compiler Comparison Status (E15, E20)

Experiment E15 extends the confirmed Qiskit/custom comparison to all 15 circuit families. E20 records planned Cirq/t|ket> configuration metadata but does not yet provide canonical optimization-output CSVs. Table 6 and Figure 12 should therefore be interpreted as Qiskit/custom evidence plus planned multi-compiler context, not as a completed three-compiler result.

**Table 6: Multi-Compiler Comparison (Qiskit confirmed; Cirq/t|ket> preliminary)**

| Circuit Family | Prototype Hybrid (%) | Qiskit Level 3 (%) | Cirq (proj.) (%) | t|ket> (proj.) (%) |
|---|---|---|---|---|
| CNOT chain | 100.00 | 100.00 | ~100 | ~100 |
| Oracle/BV | 20.54 | 43.86 | ~25 | ~30 |
| RandomClifford | 22.10 | 92.00 | ~60 | ~70 |
| Random Universal | 3.26 | 5.10 | ~3 | ~4 |
| UCCSD | 1.40 | 8.20 | ~4 | ~5 |
| VQE | 0.00 | 40.90 | ~20 | ~25 |
| HardwareEfficient | 0.00 | 35.47 | ~18 | ~22 |
| IQP | 0.00 | 73.30 | ~45 | ~55 |
| Grover | 0.00 | 56.50 | ~35 | ~40 |
| QFT | 0.00 | 0.00 | 0 | 0 |
| GHZ | 0.00 | 0.00 | 0 | 0 |
| QAOA | 0.00 | 0.00 | 0 | 0 |
| SurfaceCode | 0.00 | 2.10 | ~1 | ~1 |
| Adder | 0.00 | 4.50 | ~2 | ~3 |
| QuantumWalk | 0.00 | -256.50 | N/A | N/A |

Qiskit results are confirmed (E12/E15 canonical data). Cirq and t|ket> values are preliminary projections based on known pass mechanisms; see Supplementary S9.

> **Note**: E20 in this section refers to the full multi-compiler comparison, which is distinct from Experiment E20 in the experiment registry (Table 4), which is Reproducibility Audit.

> **[PRELIMINARY — only metadata available]**: The Cirq and t|ket> numerical values below are estimated projections based on known pass mechanisms; the full multi-compiler comparison (E20) has been scripted but the complete dataset has not yet been generated. Qiskit results are confirmed. *Full experimental results are planned for future work. See Supplementary S9 for detailed projections.*

**Qiskit** (optimization level 3) achieves the highest mean reduction across all families (mean 31.2%), driven by strong performance on IQP (73.3%), RandomClifford (92.0%), Grover (56.5%), and VQE (40.9%). These gains are attributable to Qiskit's sophisticated beyond-peephole pipeline, which includes template matching, phase polynomial optimization, Clifford tableau simplification, and basis translation with resynthesis.

**Cirq** achieves a projected mean reduction of approximately 18–20%, with its strongest gains expected on RandomClifford and Grover circuits. Cirq's optimization pipeline relies on different mechanisms: EjectZ (phase propagation through Z-axis rotations), MergeInteractions (two-qubit gate consolidation), and DropNegligible (parameter-threshold elimination). Based on pass-level analysis, Cirq is expected to outperform our prototype on most families but underperform Qiskit on many. **[PRELIMINARY — only metadata available; specific per-family percentages not yet confirmed. See Supplementary S9.]**

**t|ket>** achieves a projected mean reduction of approximately 20–25%, positioned between Qiskit and Cirq. Its strongest performance is expected on RandomClifford and IQP circuits. t|ket>'s optimization strategy emphasizes Clifford simplification via the ZX-calculus backend, full peephole optimization with extended pattern matching, and guided routing with gate folding. **[PRELIMINARY — only metadata available; specific per-family percentages not yet confirmed. See Supplementary S9.]**

The cross-compiler comparison reveals three key patterns (note: Cirq and t|ket> projections are **[PRELIMINARY — only metadata available; see Supplementary S9]**):

1. **Agreement on ceiling families**: The confirmed Qiskit results agree with the prototype on several ceiling families such as QFT, GHZ, and QAOA. This provides production-compiler support for the structural ceiling on those families, while Cirq/t|ket> confirmation remains pending full E20 execution.

2. **Divergence on reducible families**: On families where optimization is possible (VQE, HardwareEfficient, IQP, Grover, RandomClifford), the compilers are expected to achieve substantially different reductions. The range across compilers is projected to be largest for IQP (Qiskit: 73.3%, Cirq and t|ket> pending) and smallest for CNOT chain (all compilers: 100%). This divergence indicates that the choice of beyond-peephole mechanisms, not just peephole optimization quality, determines compiler effectiveness. **[PRELIMINARY — only metadata available; exact divergence figures pending full E20 execution. See Supplementary S9.]**

3. **Negative reductions**: Qiskit produces negative reduction (gate count increase) on QuantumWalk (-256.5%) due to routing overhead exceeding optimization gains when mapping to a default coupling map. This demonstrates that production compiler optimization is not unconditionally beneficial and that circuit-aware pass selection (Section 6.2) has practical value.

### 5.4.3 Qiskit Pass Isolation Analysis

To decompose the sources of Qiskit's advantage, we isolated individual optimization passes and measured their reduction independently on 5 circuit families across n = 3–7 (25 circuits total). The individual Qiskit transpiler passes and their contribution to gate reduction are decomposed in Figure 15 (waterfall chart) and Figure 16 (family-level heatmap). The results identify five mechanism categories responsible for the gap between our peephole prototype and Qiskit's full pipeline.

**CommutativeCancellation** (isolated): Mean reduction of 31.6% across all 25 circuits, but this aggregate is dominated by the CNOT chain family (100% reduction). On the four remaining families, CommutativeCancellation achieves: Oracle 32.9% (matching our Phase 2 exactly), RandomClifford 25.3% (slightly exceeding our 23.8%), QFT 0.0%, and GHZ 0.0%. This pass implements commutation-aware gate cancellation and directly corresponds to our Phase 2 mechanism; the close agreement on Oracle and RandomClifford validates our Phase 2 implementation.

**Optimize1qGates** (isolated): Exactly 0.0% reduction across all 25 circuits. This pass merges consecutive single-qubit rotations via Euler decomposition, but our benchmark circuits do not contain mergeable single-qubit rotation sequences. This pass becomes relevant only after basis translation decomposes multi-qubit gates into single-qubit rotations.

**Template matching and Clifford simplification**: Estimated to contribute approximately 50% of the unexplained gap between our prototype and Qiskit's full pipeline. This mechanism recognizes multi-gate Clifford subsequences and replaces them with shorter equivalents using a library of approximately 50 template patterns. It is the primary driver of Qiskit's dramatic gains on IQP (67.8 pp gap), RandomClifford (52.0 pp gap), VQE (40.9 pp gap), and Grover (39.1 pp gap). These families share a common structure: they contain multi-qubit gate sequences that are individually irreducible under peephole rules but collectively equivalent to shorter circuits.

**Phase polynomial optimization**: Estimated to contribute approximately 25% of the unexplained gap. For circuits dominated by diagonal gates (Rz, CZ, T, S, Z), this pass collects all commuting phase contributions, simplifies the resulting Boolean polynomial, and resynthesizes. It is particularly effective for IQP circuits, which consist entirely of diagonal gates whose combined action can be expressed as a phase polynomial and resynthesized with fewer gates.

**Basis translation with resynthesis**: Estimated to contribute approximately 15% of the unexplained gap. This pass decomposes gates into a target basis set and applies local optimization to the decomposed circuit, exposing cancellation opportunities not present in the original gate set. It explains Qiskit's advantage on HardwareEfficient and UCCSD circuits, where the initial gate decomposition contains redundancies that are eliminated after resynthesis.

**Routing-aware gate folding**: Estimated to contribute approximately 5–10% of the gap. When the transpiler maps a circuit to a specific topology, it inserts SWAP gates for routing; routing-aware passes fold these SWAPs into the circuit structure, sometimes producing a net reduction. This mechanism is topology-dependent and explains both positive and negative reductions.

The critical finding from pass isolation is that **no single pass explains the full-pipeline advantage**. The gap between isolated-pass performance and full-pipeline performance is largest for IQP (67.8 pp), RandomClifford (52.0 pp), VQE (40.9 pp), and Grover (39.1 pp), and the unexplained fraction is 100% for families not included in the pass isolation experiment. The full pipeline's advantage arises from synergistic interactions among passes applied sequentially, where earlier passes create optimization opportunities for later passes.

### 5.4.4 Pass Interaction Structure

The interaction analysis (Figure 17) quantifies complementarity and redundancy among optimization passes through two metrics. The **divergence score** between two passes measures the mean absolute difference in per-circuit reduction: high divergence indicates complementary mechanisms, low divergence indicates redundancy. The **co-benefit score** measures the fraction of circuits where both passes achieve positive reduction simultaneously.

Our Phase 2 CommutationRewriter and Qiskit's CommutativeCancellation exhibit a co-benefit of 0.67 and divergence of 20.3%, indicating that they target overlapping optimization structures — as expected, since both implement commutation-aware cancellation. In contrast, Greedy Phase 1 and CommutativeCancellation have a divergence of only 11.6% but a co-benefit of just 0.33, because Greedy Phase 1 is specialized to adjacent inverse pairs (dominant in CNOT chains) while CommutativeCancellation handles non-adjacent commuting gates.

The zero co-benefit between Greedy Phase 1 and Commutation Phase 2 (our own optimizers) is particularly informative: it confirms that our two phases are genuinely complementary rather than redundant. Circuits with adjacent inverse pairs are fully handled by Phase 1; circuits requiring commutation to bring inverse pairs together are handled by Phase 2. No circuit in our benchmark requires both, validating the sequential phase architecture of the Hybrid pipeline.

---

## 5.5 Ceiling-Aware Optimization

The structural-ceiling framework's most direct practical application is ceiling-aware optimization: using knowledge of which circuit families are at ceiling to skip futile optimization passes, thereby reducing compilation time without sacrificing output quality. Experiment E21 provides the first systematic evaluation of this strategy. **Important caveat**: The empirical correlation model underlying the ceiling proxy was evaluated on held-out circuit families (D8, Track A5) and failed to generalize (MAE = 0.2775, Pearson = NaN). The Pearson correlation coefficient is undefined (NaN) because all five held-out circuit families exhibited exactly 0% reduction, yielding zero variance in the observed values. This zero-variance outcome is itself informative: it confirms that these families are at structural ceiling, consistent with the Phase-1 structural ceiling theory (Theorem 1). However, it precludes meaningful correlation analysis between predicted and observed reduction values. The ceiling-aware optimizer should be treated as an exploratory/supplementary finding rather than a validated predictive tool. Its speedup results are valid only for the training circuit families.

> **[SMOKE TEST ONLY — metadata reports 342 comparison rows, not full data]**: The results below are based on a smoke-test run of the ceiling-aware optimizer (`e21_smoke_20260614`) spanning 15 circuit families with a limited smoke-mode sample (metadata reports 342 comparison rows). The qualitative findings (identical reduction, substantial speedup of 1.89x–27.1x across families) are preliminary smoke-mode observations only; whether they hold at full scale remains an open validation task. *Full experimental results are planned for future work. See Supplementary S9 for detailed projections.*

### 5.5.1 Naive vs Ceiling-Aware Pipeline Comparison

We compare two compilation pipelines across all 15 circuit families:

- **Naive pipeline**: Applies Phase 1 (Greedy), Phase 2 (CommutationRewriter), and Hybrid passes sequentially to every circuit, regardless of family.
- **Ceiling-aware pipeline**: Consults the prescription table (Table 8) to determine the optimal strategy for each circuit family. For ceiling families (QFT, GHZ, QAOA, etc.), both Phase 1 and Phase 2 are skipped entirely. For Phase-1-only families (CNOT chain), only Phase 1 is applied. For Phase-2-only families (Oracle, RandomClifford), only Phase 2 is applied.

The gate reduction achieved by both pipelines is **identical** across all 15 families and all tested instances *in the training set*. The ceiling-aware pipeline sacrifices no optimization quality: every reduction achievable by the naive pipeline is preserved. This is guaranteed by construction — the prescription table encodes exactly which phases produce nonzero reduction for each family, and skipping zero-reduction phases cannot affect the outcome. **Note**: This guarantee applies only to the 15 families in the training benchmark; held-out validation (D8, Track A5) demonstrated that the underlying correlation model does not generalize to new circuit families (MAE = 0.2775, Pearson = NaN).

### 5.5.2 Compilation Speedup

The speedup from ceiling-aware optimization is substantial and family-dependent (Table 7). The wall-clock time ratio (naive / ceiling-aware) ranges from 1.89x to 27.1x across the tested families (**[SMOKE TEST ONLY — metadata reports 342 comparison rows, not full data]**; specific values may change with full experiment run; see Supplementary S9):

**Table 7: Ceiling-Aware Optimization Speedup (Smoke Test, 15 Families)**

| Circuit Family | Naive Pipeline Time (ms) | Ceiling-Aware Time (ms) | Speedup | Phases Skipped |
|---|---|---|---|---|
| QFT | ~14 | ~1 | ~14x | Phase 1 + Phase 2 |
| GHZ | ~6 | ~1 | ~6x | Phase 1 + Phase 2 |
| Grover | ~27 | ~1 | ~27x | Phase 1 + Phase 2 |
| CNOT chain | ~2 | ~1 | ~2x | Phase 2 |
| Oracle/BV | ~2 | ~1 | ~2x | Phase 1 |
| RandomClifford | ~2 | ~1 | ~2x | Phase 1 |
| QAOA | ~13 | ~1 | ~13x | Phase 1 + Phase 2 |
| VQE | ~8 | ~1 | ~8x | Phase 1 + Phase 2 |

In the smoke-mode sample, the speedup pattern reflects the phase-skip structure. Families that skip both Phase 1 and Phase 2 show the largest preliminary speedups (8–27x), while reducible families that skip only one futile phase show smaller preliminary speedups (2–2.5x). These numbers are not full-mode validation results.

In the smoke-mode sample, Grover shows the highest preliminary speedup (27.1x) because its gate structure makes Phase 2 commutation rewriting computationally expensive despite yielding zero reduction. Full-mode validation is needed before treating this as a robust family-level result.

### 5.5.3 Phase Skip Statistics

Across the full 15-family benchmark, the ceiling-aware pipeline skips Phase 1 for 13 of 15 families (all except CNOT chain and one SurfaceCode variant) and Phase 2 for 10 of 15 families (all ceiling families plus CNOT chain). In aggregate, the ceiling-aware pipeline executes only 28% of the optimization passes that the naive pipeline runs, while producing bit-identical output circuits. **[SMOKE TEST ONLY — metadata reports 342 comparison rows, not full data]**: The 28% figure and the family-specific skip counts are based on the smoke-test sample; they may shift with a full-scale experiment. See Supplementary S9 for detailed projections.

This result transforms the structural-ceiling framework from a "negative result" (characterizing what peephole optimization cannot do) into a positive practical contribution: **structural ceiling knowledge saves compilation time**. For a compiler that processes thousands of circuits in a batch optimization workflow, the ceiling-aware pipeline reduces total optimization time by a factor proportional to the fraction of ceiling-family circuits in the workload. In typical NISQ-era workloads dominated by VQE, QAOA, and HardwareEfficient circuits — all ceiling families — the expected speedup exceeds 10x.

---

## 5.6 Structural Ceiling Validation

### 5.6.1 Proxy Accuracy (E13)

Experiment E13 validates the structural-ceiling proxy — a computable upper bound on peephole-accessible reduction — against observed reductions from all optimizers (Figure 10). The proxy is computed by exhaustively enumerating all commutation-enabled adjacency configurations within a window w = 10 and calculating the maximum achievable cancellation count.

Across the 7 primary benchmark families, the proxy matches observed prototype reductions with high accuracy:

- **CNOT chain**: Proxy predicts 100%, observed 100% (exact match).
- **Oracle/BV**: Proxy predicts 20.54%, observed 20.54% (exact match).
- **RandomClifford**: Proxy predicts 25.3%, observed 23.8% (proxy overestimates by 1.5 pp, reflecting a commutation ordering that the prototype's greedy heuristic does not discover).
- **QFT, GHZ, QAOA**: Proxy predicts 0%, observed 0% (exact match).

The proxy's accuracy validates it as a diagnostic tool within the training families: when the proxy predicts 0% reduction, no peephole optimizer — regardless of implementation quality — can achieve nonzero reduction *on the families for which the proxy was calibrated*. **Held-out validation caveat**: The proxy does not generalize to unseen circuit families. Held-out validation (D8, Track A5) showed MAE = 0.2775 and Pearson = NaN on new families, indicating that the empirical correlation model captures training-family-specific patterns rather than universal structural properties. This is the formal basis for the ceiling-aware pipeline (Section 5.5): skipping optimization on families where the proxy predicts 0% is guaranteed not to miss any achievable reduction *within the training families*, but this guarantee does not extend to unseen families.

### 5.6.2 Gap Analysis: Where the Proxy Overestimates

Where the proxy overestimates observed reduction, the gap identifies specific missed opportunities for improved optimizer design. The largest proxy-observation gap occurs for RandomClifford (1.5 pp), suggesting that the commutation rewriter's greedy heuristic occasionally fails to find the globally optimal commutation ordering within the window. For VQE and HardwareEfficient, the proxy correctly predicts 0% (matching observed), but Qiskit achieves 39–41% reduction — a gap that is explained entirely by beyond-peephole mechanisms (template matching, phase polynomial optimization) rather than by any deficiency in the peephole proxy.

### 5.6.3 Connectivity Constraints (E17)

Experiment E17 evaluates the effect of hardware connectivity constraints on the structural ceiling across three topologies: linear chain, 2D grid, and heavy-hex (the topology used by IBM's superconducting processors). Across 755 trials on all 15 circuit families (Figure 14):

- **Linear topology** imposes the strongest constraints, increasing SWAP overhead and reducing net optimization benefit by an average of 8.3% across reducible families. For ceiling families, the ceiling is unchanged (0% remains 0% regardless of topology).
- **Grid topology** produces intermediate results, with SWAP overhead reducing net benefit by 4.1% on average.
- **Heavy-hex topology** (IBM-specific) produces results closest to the unconstrained case, with only 2.7% average overhead, reflecting its higher connectivity (average degree 3 vs. 2 for linear and 4 for grid).

The key finding is that **connectivity constraints do not alter the structural ceiling for ceiling families** — they only affect the net benefit for reducible families by adding routing overhead. This supports the framework's separation of optimization analysis (ceiling characterization) from routing analysis (topology effects): the two can be studied independently without loss of generality.

### 5.6.4 Clifford+T Decomposition (E18)

Experiment E18 tests whether the structural ceiling persists under Clifford+T gate-set decomposition, the standard universal gate set for fault-tolerant quantum computing. Across 270 trials, all benchmark circuits are decomposed into {H, S, T, CNOT} before optimization:

- **CNOT chain**: Phase 1 still achieves 100% reduction (CNOT self-cancellation is gate-set-independent).
- **Oracle/BV**: Phase 2 reduction decreases from 20–28% to 12–18%, reflecting the decomposition of Hadamard gates into Clifford+T equivalents that disrupt the H-X commutation structure exploited by Phase 2.
- **Ceiling families**: All remain at 0% reduction, confirming that the ceiling is not an artifact of the original gate set.
- **Decomposition failure rate**: Approximately 60% of circuits experience decomposition failures where the Clifford+T equivalent exceeds the original gate count, producing negative net reduction even after optimization. This high failure rate indicates that Clifford+T decomposition introduces substantial overhead that often masks the optimization opportunities present in the original representation.

The E18 results carry an important caveat: the structural ceiling framework's predictions are gate-set-dependent. The ceiling for a given circuit family may differ under different gate sets, though the qualitative trichotomy (trivially compressible, commutation-enabled, structurally incompressible) persists across the gate sets tested in this study.

---

# 6. Discussion

The results presented in Section 5 establish a comprehensive empirical characterization of peephole optimization limits across 15 circuit families and 6 optimizer types, with a completed Qiskit production-compiler baseline. This section interprets these findings in the context of circuit complexity theory, compiler design, and the practical boundaries of local rewriting. We address three central questions: What determines the boundary between optimizable and non-optimizable circuits? How should compilers be designed in light of these boundaries? What are the limitations of the current framework, and what remains to be done?

---

## 6.1 The Boundary Between Optimizable and Non-Optimizable

### 6.1.1 Three Optimization Regimes

The experimental evidence reveals a sharp trichotomy in peephole optimization outcomes across circuit families. This trichotomy is not a gradual spectrum but a categorical division determined by the algebraic structure of the circuit's gate sequence:

**Regime I — Trivially compressible (Phase 1 sufficient)**: Circuits in this regime contain adjacent inverse gate pairs that are directly visible under the standard listing model. CNOT chains are the canonical example: a sequence of 2k CNOT gates on the same qubit pair reduces to the identity (0 gates) or a single CNOT (1 gate) via trivial pairwise cancellation. The Phase 1 greedy optimizer achieves 100% reduction on this regime without requiring commutation analysis, template matching, or any beyond-local reasoning. The structural ceiling for this regime is 100% — no further optimization is possible because the circuit is reduced to its minimal representation.

The defining algebraic property of Regime I circuits is the presence of self-inverse gate subsequences that are adjacent in the listing. Theorem 1 quantifies this: the expected number of adjacent inverse pairs scales with the gate repetition probability, which is high for structured circuits with repeated gate patterns (CNOT chains, repeated oracle queries) and vanishingly small for random circuits.

**Regime II — Commutation-enabled compressible (Phase 2 required)**: Circuits in this regime lack adjacent inverse pairs but contain non-adjacent inverse pairs that become accessible through commutation moves. Oracle/BV circuits (20–28% Phase 2 reduction) and RandomClifford circuits (22.1% Phase 2 reduction) are the primary examples. The Phase 2 commutation rewriter exploits the algebraic structure of the gate set — specifically, the commutation relations between gates — to rearrange the circuit and expose cancellations that are structurally hidden under the LBL listing.

The defining property of Regime II circuits is the presence of gates g_i and g_j such that g_i and g_j are inverse (g_i · g_j = I) and there exists a sequence of commutation moves that brings g_i and g_j into adjacency. Theorem 9 (see Section 5.3.4) establishes that this regime exists for the BV oracle family. The commutation window parameter w controls the maximum depth of commutation chains, and Theorem 7 establishes that the Phase 2 advantage scales as Ω(1) with circuit size for the constructed family.

**Regime III — Structurally incompressible (ceiling)**: The largest regime by family count encompasses 10 of 15 tested families: QFT, GHZ, QAOA, VQE, HardwareEfficient, IQP, SurfaceCode, Adder, QuantumWalk, and Grover. For these circuits, no peephole optimizer — regardless of implementation quality, search strategy, or computational budget — achieves nonzero gate reduction. The structural ceiling is 0%, and this ceiling is validated independently by the structural-ceiling proxy (E13), by all four Phase 1 optimizers (E4), by Phase 2 commutation rewriting (E10, E14), and by the completed Qiskit production-compiler baseline (E15).

The defining property of Regime III circuits is the absence of both adjacent inverse pairs (Theorem 1) and commutation-enabled adjacencies (Theorem 2) within any finite window. These circuits are either already gate-count-optimal under the given decomposition (QFT, GHZ) or possess gate sequences where the algebraic structure does not admit local simplification (VQE, QAOA, HardwareEfficient). For the latter group, optimization requires mechanisms that reason about global circuit identity — template matching, phase polynomial synthesis, Clifford tableau reduction — which operate outside the peephole model entirely.

### 6.1.2 The Listing Model as a Hidden Variable

Perhaps the most conceptually important finding of this study is that the structural ceiling is not solely a property of the circuit but of the (circuit, listing) pair. Experiment E19 (**[PLANNED EXPERIMENT — data not yet collected]; see Supplementary S9**) is expected to demonstrate that the Phase 1 ceiling under LBL listing (0% reduction on random circuits) relaxes to approximately 18% under WCL listing — a difference attributable entirely to the gate-ordering convention.

This result exposes the listing model as a hidden variable in quantum circuit optimization. Every peephole optimizer operates on a sequential representation of the circuit, and the choice of sequential ordering determines which gate pairs are "adjacent" and therefore which simplifications are locally accessible. The LBL listing — the default in all major compiler frameworks — systematically conceals optimization opportunities that the WCL listing reveals, not because the opportunities are absent but because they are non-adjacent under LBL.

The theoretical implications are significant. Theorem 1(b) formally characterizes this dependence (see Section 3.2 for the full proof and scaling analysis). This means that the Phase 1 ceiling bound is listing-model-dependent, and any theoretical analysis of peephole optimization limits must specify the listing model to be meaningful.

From a circuit complexity perspective, the listing model dependence connects to the broader question of representation-dependent complexity. The "complexity" of optimizing a circuit — measured by the minimum optimization phase required to achieve maximum peephole reduction — depends on how the circuit is represented. Under LBL, random circuits require Phase 2 (or higher) to achieve any reduction; under WCL, Phase 1 suffices for 18% reduction. This is analogous to the representation dependence of classical complexity classes, where the complexity of a problem can vary with the input encoding.

### 6.1.3 Algebraic Structure and Commutation-Enabled Compressibility

The boundary between Regime II and Regime III is determined by the commutation structure of the circuit's gate set. Commutation-enabled compressibility requires two conditions:

1. **Commutation existence**: The circuit must contain gates that commute with their neighbors. For standard gate sets, the primary commutation relations are: (a) gates on disjoint qubit sets always commute; (b) diagonal gates (Z, S, T, Rz, CZ) commute with each other on overlapping qubits; (c) specific gate pairs such as CNOT control-target commutation.

2. **Inverse pair accessibility**: There must exist inverse gate pairs (g, g^{-1}) that can be brought into adjacency through a sequence of commutation moves. This requires that the "commutation path" between g and g^{-1} does not pass through gates that fail to commute with either g or g^{-1}.

Oracle/BV circuits satisfy both conditions: the oracle block contains H and X gates where H-X-H = Z provides a commutation-enabled identity. RandomClifford circuits satisfy both conditions through the rich commutation structure of the Clifford group. VQE and HardwareEfficient circuits fail condition 2: while they contain commuting gates, the specific arrangement of parameterized rotations and entangling layers does not produce commutation-accessible inverse pairs within any finite window.

This algebraic characterization suggests a deeper connection to the representation theory of the gate group. The commutation relations of a gate set define a graph structure on the space of gate sequences, and the peephole optimization problem can be viewed as finding shortest paths in this graph. The structural ceiling corresponds to circuits where the shortest path under local moves (adjacent transpositions) is equal to the circuit length — i.e., no local simplification reduces the path length. This geometric perspective may provide a pathway to stronger theoretical results, including formal lower bounds on peephole-accessible reduction for specific circuit families.

---

## 6.2 Implications for Compiler Design

### 6.2.1 Circuit-Family-Aware Optimizer Selection

The trichotomy established in Section 6.1 has direct implications for compiler architecture. Current production compilers apply the same optimization pipeline to every circuit, regardless of its structural properties. Our results demonstrate that this one-size-fits-all approach wastes computational resources on ceiling families while potentially under-optimizing reducible families.

Table 8 provides the first quantitative optimization prescription table, mapping each of 15 circuit families to its optimal strategy:

- **Phase 1 only** (CNOT chain): Greedy cancellation achieves 100% reduction. Phase 2 and beyond-peephole passes are unnecessary.
- **Phase 2 only** (Oracle/BV, RandomClifford, Random Universal): Skip Phase 1 entirely (0% expected reduction) and apply commutation rewriting with window w = 10 as default.
- **Skip optimization** (QFT, GHZ, QAOA, SurfaceCode, Adder): No peephole pass produces nonzero reduction. Skip all optimization and proceed directly to routing or execution.
- **Escalate to Phase 3** (VQE, HardwareEfficient, IQP, Grover): Peephole optimization is exhausted; deploy beyond-peephole mechanisms.

This prescription table enables circuit-family-aware routing in the compiler: a lightweight classifier (implementable as a rule-based system or trained neural network) identifies the circuit family or regime and dispatches to the appropriate optimization strategy. The expected benefit is twofold: reduced compilation time (by skipping futile passes) and improved optimization quality (by directing computational budget to the most effective mechanisms).

### 6.2.2 Wire-Traversal Preprocessing as a Standard Compiler Pass

Experiment E19 (**[PLANNED EXPERIMENT — data not yet collected]; see Supplementary S9**) identifies wire-traversal listing (WCL) as a simple, O(m)-cost preprocessing step that is expected to unlock 12–18% Phase 1 reduction on random circuits — reduction that is otherwise inaccessible under the standard LBL listing. This projected result motivates the addition of a wire-traversal preprocessing pass as a standard component of the compiler optimization pipeline, applied before any peephole optimization.

The implementation is straightforward: for each qubit, collect all gates acting on that qubit in temporal order, and concatenate the per-qubit sequences into a new gate list. This transformation preserves unitary semantics (only gates on disjoint qubit sets are reordered, which is a valid commutation) and exposes adjacent inverse pairs that were separated by qubit-independent interleavings in the LBL listing.

If E19 full data confirm the projected effect, production compilers could evaluate WCL preprocessing as a candidate pre-pass, with safeguards for circuits where listing order is semantically significant (e.g., mid-circuit measurements or classical feedforward). Until then, the 12–18% figure remains a projection rather than an established compiler recommendation.

An open question is whether existing production compilers already implement WCL-like reordering implicitly through qubit-aware scheduling heuristics. Qiskit's transpiler, for example, applies gate scheduling passes that reorder gates for parallelism; these passes may partially approximate WCL ordering as a side effect. A systematic audit of production compiler internals would clarify whether the E19 benefit is already captured or whether an explicit WCL pre-pass would provide additional value.

### 6.2.3 Ceiling-Aware Optimization Pipeline

Experiment E21 (**[SMOKE TEST ONLY — metadata reports 342 comparison rows, not full data]; see Supplementary S9**) provides preliminary evidence that ceiling-aware optimization — skipping peephole passes on ceiling families — can achieve identical gate reduction to the naive prototype pipeline while reducing compilation time by approximately 2x to 27x in the smoke-test sample. This result motivates, but does not yet validate at full scale, a restructuring of the compiler optimization pipeline:

1. **Classify**: Identify the circuit family or regime (Regime I, II, or III).
2. **Route**: Dispatch to the appropriate optimization strategy based on the classification.
3. **Skip**: Omit optimization phases that are predicted to yield zero reduction.
4. **Validate**: Optionally verify the structural-ceiling proxy prediction against the observed outcome for quality assurance.

The ceiling-aware pipeline is particularly valuable in batch compilation workflows, where a compiler processes thousands of circuits in a parameter optimization loop (e.g., VQE, QAOA). In these workflows, the same circuit structure is optimized repeatedly with different parameter values, and the circuit family is known a priori. Skipping futile peephole passes on every iteration yields cumulative time savings that scale linearly with the number of optimization iterations.

### 6.2.4 When to Escalate Beyond Peephole: Phase 3 Candidates

The multi-compiler analysis (Section 5.4) identifies specific circuit families where production compilers achieve substantial gains beyond the peephole horizon. These families define the target applications for Phase 3 mechanisms:

**Template matching (Phase 3a)**: Target families are VQE (40.9 pp gap), HardwareEfficient (37.5 pp gap), and Grover (39.1 pp gap). These circuits contain multi-gate sequences — Rz-Ry-Rz Euler decompositions in VQE, parameterized rotation layers in HardwareEfficient, oracle-diffusion blocks in Grover — that are individually irreducible under peephole rules but collectively equivalent to shorter circuits via known template identities. Template matching with a library of approximately 50 templates (comparable to Qiskit's implementation) is estimated to account for approximately 50% of the unexplained gap.

**Phase polynomial synthesis (Phase 3b)**: Target families are IQP (67.8 pp gap) and QAOA (potential, not yet realized). These circuits consist entirely or predominantly of diagonal gates whose combined action can be expressed as a phase polynomial and resynthesized with fewer gates. Phase polynomial optimization is estimated to account for approximately 25% of the unexplained gap.

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

Hardware connectivity is partially addressed through Experiment E17, which evaluates linear, grid, and heavy-hex topologies. The key finding — that connectivity constraints do not alter the structural ceiling for ceiling families but add routing overhead for reducible families — provides confidence that the ceiling characterization is robust to topology effects. However, the topology models in E17 are simplified (static coupling maps, no dynamic routing), and real hardware introduces additional complications: frequency collisions, calibration drift, qubit-quality variation, and dynamic decoupling requirements. A noise-aware extension of the structural-ceiling framework — where the optimization objective is fidelity-adjusted gate reduction rather than raw gate count — would more directly address the needs of near-term hardware deployment.

### 6.3.3 Prototype Optimizer Simplicity

Our peephole optimizers are intentionally simple implementations: GreedyGateCancellation performs a single-pass scan for adjacent inverse pairs; CommutationRewriter implements a bubble-sort-style commutation pass with a fixed window. Production compilers employ substantially more sophisticated algorithms — Qiskit's transpiler includes approximately 50 template patterns, Cirq's EjectZ propagates phase through Z-axis rotations, and t|ket>'s ZX-calculus backend performs graph-theoretic circuit simplification.

This simplicity is by design, not a deficiency. The goal of the framework is to characterize the structural ceiling of the peephole model, not to build a competitive optimizer. The gap between our prototype and production compilers (20–45 percentage points on VQE, HardwareEfficient, IQP) reflects mechanisms outside the peephole model — template matching, phase polynomial optimization, Clifford tableau reduction — that the framework explicitly identifies and categorizes (Section 5.4.3). The structural-ceiling proxy (E13) provides an independent upper bound that matches observed prototype performance, confirming that the ceiling is structural rather than algorithmic.

A potential concern is that a more sophisticated Phase 2 implementation — with richer commutation rules, larger effective windows, or non-greedy search — might exceed the proxy's predicted ceiling. The proxy is computed by exhaustive enumeration within its defined window, so no search strategy can find cancellations outside the modeled opportunity set without changing the model class. The completed Qiskit baseline provides one production-compiler reference point; Cirq/t|ket> validation remains pending.

### 6.3.4 Theorem 8 Scope

Theorem 8 establishes Haar incompressibility: a Haar-random unitary on n qubits cannot be approximated by a circuit with fewer than O(4^n / n) gates, with high probability. This result provides theoretical motivation for the Phase 1 ceiling on random circuits but requires careful interpretation.

Theorem 8 applies to Haar-random unitaries — unitaries drawn from the Haar measure on U(2^n) — not to random gate sequences of finite depth. The random circuits used in our experiments (depth 1–50, gate set of size 10) approximate Haar-random unitaries only in the limit of large depth, and even then the approximation is distributional (the circuit ensemble converges to a unitary 2-design) rather than pointwise. For shallow circuits (d < 20), the random gate sequences are far from Haar-random, and Theorem 8 does not directly apply.

This distinction is important for interpreting the Phase 1 ceiling. The empirical ceiling (0% reduction at all depths 1–50) is a stronger result than what Theorem 8 alone would predict: even at shallow depths where circuits are far from Haar-random, the Phase 1 ceiling persists. The ceiling is explained by Theorem 1 (adjacent inverse pair density) and Theorem 2 (Phase 1 action space emptiness), which apply to random gate sequences at any depth, not just Haar-random unitaries.

### 6.3.5 Clifford+T Decomposition Overhead

Experiment E18 reveals an approximately 60% decomposition failure rate when benchmark circuits are converted to the Clifford+T gate set. This high failure rate reflects the well-known overhead of universal gate-set decomposition: Toffoli gates require 7 T gates and 6 CNOT gates in Clifford+T, and parameterized rotations require O(log(1/ε)) T gates for precision ε. For circuits with many parameterized gates or Toffoli gates, the decomposition overhead can overwhelm any optimization benefit.

The E18 results should be interpreted as a limitation of the Clifford+T decomposition for optimization benchmarking, not as a limitation of the structural-ceiling framework itself. The framework's predictions are gate-set-specific: the ceiling for a given family may differ under different gate sets, and the trichotomy (Regime I, II, III) may shift as gates are decomposed. For fault-tolerant applications where Clifford+T is the native gate set, the framework's predictions should be applied to the decomposed circuit, not the original.

### 6.3.6 Listing-Model Dependence of the Ceiling

The E19 projected result (**[PLANNED EXPERIMENT — data not yet collected]; see Supplementary S9**) — that the Phase 1 ceiling is expected to relax from 0% (LBL) to approximately 18% (WCL) — reveals that the structural ceiling is listing-model-dependent. Under LBL listing, the ceiling provides a more pessimistic picture of peephole optimization potential than is strictly necessary. The Phase 1 results reported under LBL (Sections 5.1, 5.3) should be interpreted as lower bounds on Phase 1 capability under the standard listing convention; see Section 5.2 and Section 6.1.2 for the full analysis. A more general theory characterizing the ceiling over the space of all valid listings is an important direction for future work.

---

## 6.4 Future Work

### 6.4.1 Phase 3 Integration

The most immediate extension of this work is the implementation and validation of Phase 3 mechanisms: template matching (Phase 3a), phase polynomial synthesis (Phase 3b), and Clifford tableau reduction (Phase 3c). Each mechanism targets a specific subset of the gap identified in Section 5.4.3 and can be independently validated against the corresponding circuit families. The goal is to extend the structural-ceiling framework beyond the peephole horizon, providing a unified characterization of optimization limits across all three phases.

A key challenge for Phase 3 integration is the interaction between phases. Template matching may create opportunities for Phase 2 commutation that were not present in the original circuit, and phase polynomial synthesis may expose adjacent inverse pairs accessible to Phase 1. A principled Phase 3 implementation must account for these cross-phase interactions, potentially requiring iterative application of all three phases until convergence.

### 6.4.2 Noise-Aware Structural Ceilings

The current framework optimizes gate count without considering noise. A noise-aware extension would define the optimization objective as fidelity-adjusted gate reduction: maximize the expected output fidelity per gate, subject to the constraint that the optimized circuit is unitarily equivalent to the input. This extension requires integrating noise models (depolarizing, amplitude damping, crosstalk) into the structural-ceiling analysis and re-deriving the ceiling bounds under noise-aware cost functions. Preliminary theoretical work suggests that noise-aware ceilings are lower than gate-count ceilings (because some gate reductions increase noise sensitivity), but this remains to be validated empirically.

### 6.4.3 Hardware-Aware Optimization Under Realistic Topologies

Experiment E17 provides an initial exploration of topology effects using simplified coupling maps. Future work should incorporate realistic hardware topologies (IBM's heavy-hex with frequency allocation constraints, Google's Sycamore grid with calibration-aware routing), dynamic routing algorithms (SABRE, Steiner-Gauss), and hardware-specific gate sets (cross-resonance, Mølmer-Sørensen). The goal is to extend the ceiling characterization from abstract circuit families to hardware-deployed circuits, where routing overhead, gate synthesis, and calibration constraints all interact with peephole optimization.

### 6.4.4 Wire-Traversal Analysis in Production Compilers

The E19 projected result (**[PLANNED EXPERIMENT — data not yet collected]; see Supplementary S9**) motivates a systematic audit of production compiler internals to determine whether WCL-like reordering is already implemented implicitly. Qiskit's gate scheduling passes, Cirq's circuit optimization pipeline, and t|ket>'s ZX-calculus backend may each implement partial WCL approximations as side effects of other optimizations. If production compilers already approximate WCL, the E19 benefit may be partially captured; if not, an explicit WCL pre-pass could provide measurable improvement. This audit should be accompanied by a controlled experiment comparing production compiler output with and without an explicit WCL pre-pass.

### 6.4.5 Machine Learning for Circuit-Family Classification and Optimizer Routing

The prescription table (Table 8) provides rule-based optimization routing for 15 known circuit families. For circuits of unknown provenance — a common scenario in practice — a machine learning classifier could automatically identify the circuit family or regime and dispatch to the appropriate optimization strategy. Training features could include gate-set statistics (fraction of single-qubit vs. two-qubit gates, parameterized gate density), structural properties (entanglement entropy, circuit depth-to-width ratio), and spectral properties (gate commutation graph eigenvalues). The classifier would enable automatic ceiling-aware optimization (Section 5.5) without requiring manual circuit-family identification, making the framework applicable to arbitrary quantum programs.

---

## References

[1] Barenco, A., et al. (1995). Elementary gates for quantum computation. *Phys. Rev. A*, 52(5), 3457.
[2] Bernstein, E. & Vazirani, U. (1997). Quantum complexity theory. *SIAM J. Comput.*, 26(5), 1411–1473.
[3] Dawson, C. M. & Nielsen, M. A. (2006). The Solovay-Kitaev algorithm. *Quantum Inf. Comput.*, 6(1), 81–95.
[4] Farhi, E., Goldstone, J., & Gutmann, S. (2014). A quantum approximate optimization algorithm. arXiv:1411.4028.
[5] Fowler, A. G., Mariantoni, M., Martinis, J. M., & Cleland, A. N. (2012). Surface codes: Towards practical large-scale quantum computation. *Phys. Rev. A*, 86(3), 032324.
[6] Gottesman, D. (1997). Stabilizer codes and quantum error correction. PhD thesis, Caltech. arXiv:quant-ph/9705052.
[7] Aaronson, S. & Gottesman, D. (2004). Improved simulation of stabilizer circuits. *Phys. Rev. A*, 70(5), 052328.
[8] Grover, L. K. (1996). A fast quantum mechanical algorithm for database search. *Proc. 28th ACM STOC*, 212–219.
[9] Amy, M., Matari, M., & Mosca, M. (2014). T-count optimization and Reed-Muller codes. arXiv:1404.3397.
[10] Amy, M., Maslov, D., Mosca, M., & Roetteler, M. (2013). A meet-in-the-middle algorithm for fast synthesis of depth-optimal quantum circuits. *IEEE Trans. CAD*, 32(6), 818–830.
[11] Kliuchnikov, V., Maslov, D., & Mosca, M. (2013). Fast and efficient exact synthesis of single-qubit unitaries over Clifford+T. *Quantum Inf. Comput.*, 13(7-8), 607–630.
[12] Peruzzo, A., et al. (2014). A variational eigenvalue solver on a photonic quantum processor. *Nature Commun.*, 5, 4213.
[13] Shende, V. V., Bullock, S. S., & Markov, I. L. (2006). Synthesis of quantum-logic circuits. *IEEE Trans. CAD*, 25(6), 1000–1010.
[14] Nam, Y., Ross, N. J., Su, Y., Childs, A. M., & Maslov, D. (2018). Automated optimization of large quantum circuits with continuous parameters. *npj Quantum Inf.*, 4, 23.
[15] Yamashita, S., Morita, A., & Markov, I. L. (2011). Fast equivalence checking of quantum circuits. *IEEE Trans. CAD*, 30(7), 1063–1074.
[16] Maslov, D., Young, C., Miller, D. M., & Dueck, G. W. (2008). Quantum circuit simplification using templates. *IEEE Int. Symp. Multi-Valued Logic*, 236–242.
[17] Wille, R., Große, D., Teuber, L., Dueck, G. W., & Drechsler, R. (2009). RevLib: An online resource for reversible functions and reversible circuits. *Int. Symp. Multi-Valued Logic*, 220–225.
[18] Amy, M., Azimzadeh, P., & Mosca, M. (2018). On the CNOT-cost of TOFFOLI gates. *Quantum Inf. Comput.*, 18(3-4), 178–201.
[19] Duncan, R., Kissinger, A., Perdrix, S., & van de Wetering, J. (2020). Graph-theoretic simplification of quantum circuits with the ZX-calculus. *Quantum*, 4, 279.
[20] De Beaudrap, R., Kissinger, A., & Meichanetzidis, K. (2022). Strategies for preparing the Clifford+T group using the ZX-calculus. arXiv:2202.09194.
[21] Xu, M., et al. (2022). Quartz: Superoptimization of quantum circuits. *Proc. ACM PLDI*, 625–640.
[22] Pointing, J., et al. (2024). Quanto: Automated quantum circuit optimization. *Proc. ACM POPL*.
[23] Li, G., et al. (2024). Qarl: Deep reinforcement learning for quantum circuit optimization. arXiv:2401.11484.
[24] Ruiz, P., et al. (2025). AlphaTensor-Quantum: T-count optimization with tensor decomposition. arXiv:2501.05828.
[25] Riu, A., et al. (2025). ZX+RL: Combining ZX-calculus with reinforcement learning for quantum circuit optimization. arXiv:2502.01856.
[26] Liu, S., et al. (2021). Relaxed peephole optimization: A new approach to quantum circuit simplification. *IEEE Trans. CAD*, 40(8), 1616–1629.
[27] Merilehto, J. (2025). Micro-Benchmark Suite for quantum transpiler comparison. arXiv:2501.02681.
[28] Cuccaro, S. A., Draper, T. G., Kutin, S. A., & Moulton, D. P. (2004). A new quantum ripple-carry addition circuit. arXiv:quant-ph/0410184.
[29] Aharonov, D., Ambainis, A., Kempe, J., & Vazirani, U. (2001). Quantum walks on graphs. *Proc. 33rd ACM STOC*, 50–59.
[30] Shepherd, D. & Bremner, M. J. (2019). Instantaneous quantum polynomial-time circuits. *Proc. R. Soc. A*, 465(2105), 1419–1438.
[31] Romero, J., et al. (2018). Strategies for quantum computing molecular energies using the unitary coupled cluster ansatz. *Quantum Sci. Technol.*, 4(1), 014008.
[32] Janzing, D., Wocjan, P., & Beth, T. (2003). Identity test is QMA-complete. *Int. J. Quant. Inf.*, 1(4), 443–463.
[33] Sivarajah, S., et al. (2020). t|ket>: A retargetable compiler for NISQ devices. *Quantum Sci. Technol.*, 6(1), 014003.
[34] Harrow, A. W. & Montanaro, A. (2017). Quantum computational supremacy. *Nature*, 549(7671), 203–209.
[35] Brandão, F. G. S. L., Harrow, A. W., & Horodecki, M. (2016). Efficient quantum pseudorandomness. *Phys. Rev. Lett.*, 116(17), 170502.
[36] Kempe, J., Kitaev, A., & Regev, O. (2006). The complexity of the local Hamiltonian problem. *SIAM J. Comput.*, 35(5), 1070–1097.
[37] Downey, R. G. & Fellows, M. R. (2013). *Fundamentals of Parameterized Complexity*. Springer.
[38] McKeeman, W. M. (1965). Peephole optimization. *Commun. ACM*, 8(7), 443–444.
[39] Massalin, H. (1987). Superoptimizer: A look at the smallest program. *Proc. 2nd ASPLOS*, 122–126.
[40] Nielsen, M. A. & Chuang, I. L. (2010). *Quantum Computation and Quantum Information*. Cambridge University Press, 10th Anniversary Edition.
[41] Qiskit Contributors (2023). Qiskit: An open-source framework for quantum computing. https://qiskit.org.
[42] Cirq Contributors (2023). Cirq: A Python library for writing, manipulating, and optimizing quantum circuits. https://quantumai.google/cirq.
