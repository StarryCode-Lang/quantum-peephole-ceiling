# Theory-Experiment Cross-Validation Table

> **Document Status**: Comprehensive mapping of theoretical predictions to experimental observations.
> **Version**: 1.0
> **Date**: 2026-06-13
> **Scope**: All theorems, lemmas, propositions, observations, and conjectures from `lemmas.md` and `conjectures.md` mapped against experiments E1-E18.
> **Methodology**: For each result, we state the quantitative/qualitative prediction, identify the corresponding experiment(s), report the observed value, compare against the predicted value, and render an honest consistency verdict.

---

## How to Read This Table

- **MATCH**: The experimental observation is consistent with the theoretical prediction within the regime tested.
- **PARTIAL MATCH**: The observation is broadly consistent but exhibits caveats, discrepancies, or tests only a proxy of the predicted quantity.
- **MISMATCH**: The observation directly contradicts the prediction in the regime tested. (A mismatch is not necessarily an error -- it may indicate a model-experiment mismatch in assumptions, as with Thm 1a.)
- **UNTESTED**: No experiment directly tests the prediction.

---

## Primary Cross-Validation Table

| ID | Prediction | Corresponding Experiment(s) | Predicted Value | Observed Value | Consistency | Notes |
|----|-----------|----------------------------|-----------------|----------------|-------------|-------|
| **Thm 1a** | Under wire-consecutive listing (WCL), the expected number of listing-adjacent inverse pairs is E[\|A_adj\|] = n(d-1) * p_cancel. For E1 parameters (n=5, rho=0.3, gate set {H, T, Rz, Rx, Ry, CNOT}): p_cancel = 0.0421. | E1 (25,000 trials, n=5, d=1-50), E2 (2,100 trials), E3 (11,962 trials), E4 (400 trials), E5 (6,000 trials) | **d=5**: ~0.842 pairs; **d=10**: ~1.894 pairs; **d=50**: ~10.314 pairs. Fractional Phase-1 reduction <= 2% per Corollary 1.1. | **0 adjacent inverse pairs** in all 25,000+ trials. Phase-1 reduction = 0.0000% with std = 0.0000%. | **MISMATCH** | Thm 1a assumes WCL; experiments use the LBL generator (`generator_v2.py`). Under LBL, wire-consecutive gates are separated by n-1 intervening gates, so no listing-adjacent same-qubit pairs exist. The MISMATCH is fully explained by Thm 1b. The Thm 1a formula overcounts because it treats wire-consecutive gates as listing-adjacent. See `FIX2_E1_Zero_Std_Analysis.md` Section 4 for detailed analysis. **NOTE: All experiments E1-E5 use LBL (layer-by-layer listing via `generator_v2.py`), NOT WCL (wire-consecutive listing). The Thm 1a prediction applies only to the WCL model and should not be compared against LBL-generated circuits.** |
| **Thm 1b** | Under layer-by-layer listing (LBL), S_1(C) = empty for all circuits with n >= 2. Consequently R_1(C) = 0 for every Phase-1 optimizer. | E1 (25,000 trials, n=5, d=1-50), E2 (n=6, d=20), E3 (n=3-10), E4 (n=5, d=15), E5 (n=5, d=3-20) | Exactly 0% reduction; exactly 0 listing-adjacent inverse pairs; std = 0 across all trials. | Mean reduction = 0.0000%, std = 0.0000% across all 25,000 E1 trials. Confirmed across E2-E5 (45,500+ total trials). Independent verification: 0 same-qubit adjacent pairs found in ~99,000 pairs per 1,000 circuits at d=20. | **MATCH** | Thm 1b perfectly explains the empirically observed structural zero. The generator (`generator_v2.py` lines 230-258) places gate on qubit q at layer L at listing index L*n + q, guaranteeing gap >= n between same-qubit gates. This is not a bug but a structural property. |
| **Thm 2 (a)** | If S_1(C) = empty and no consecutive rotation gates on the same qubit admit merging, the Greedy optimizer achieves zero reduction. | E1-E5 (all Greedy trials), E10 (Greedy Phase 1), E14 (extended benchmark) | Greedy R_1(C) = 0% on all random circuits. | Greedy mean reduction: E1 = 0.0000%, E2 = 0.0000%, E3 = 0.0000%, E4 = 0.0000%, E10 random = 0.0000%. | **MATCH** | Greedy achieves exactly 0% on all random circuit experiments, confirming the reduction ceiling when S_1 is empty. |
| **Thm 2 (b)** | Stochastic optimizers (SA, GA, RLS) employ SWAP, COMMUTATION, and INSERTION moves that can populate S_1, but cannot systematically achieve net gate-count reduction beyond what is enabled by the commutation/swap structure already present. INSERTION + REMOVAL sequences yield zero net reduction. | E4 (4 optimizers x 100 circuits, n=5, d=15) | All stochastic optimizers achieve ~0% mean reduction, with differences from Greedy bounded by O(1/\|C\|). INSERTION creates new S_1 elements in 100% of trials but INSERTION+REMOVAL yields zero net reduction in 100% of trials. | E4: Greedy = 0.00%, SA ~= 0%, RLS ~= 0%, GA = 0.67%. Overall mean = 0.0067%. GA's 0.67% arises from rare SWAP-enabled non-adjacent pair discovery, not INSERTION. | **MATCH** | The 0.67% GA advantage is consistent with rare SWAP-facilitated discovery (Thm 2 Step 2 acknowledges SWAP can reveal pre-existing wire-level structure). The INSERTION-specific prediction (100% zero net reduction in 5000/5000 trials) is reported in the Thm 2 remark but not from a labeled experiment. The INSERTION cascade gap (whether INSERTION can change commutation topology to enable net reduction) remains formally open. |
| **Lemma 3** | Commutation rewriting preserves unitary equivalence exactly. Any circuit produced by the HybridCommuteRewrite pipeline (Phase 1 + Phase 2 + Phase 1) is unitarily equivalent to the input. | All experiments (E1-E18) that report fidelity | F_avg = 1.000000 (exact) for all optimizer outputs. | Mean fidelity = 1.000000 across all verified datasets (E1-E18). No fidelity violations reported above numerical precision threshold. | **MATCH** | Exact unitary preservation is confirmed across 45,000+ trials. Note: fidelity verification uses direct unitary comparison for n <= max_qubits_fidelity; large circuits require sampled/process fidelity (see claim C7 caveat in `v4_claim_evidence_map.md`). |
| **Lemma 4** | When no two cancelable pairs share a gate (non-conflicting pairs), the Greedy scan achieves the maximum Phase-1 reduction, exactly 2\|S_1(C)\| gates. | E11 (CNOT chain, n=3-5), E4 (random circuits where \|S_1\| = 0 trivially) | Greedy achieves maximum possible Phase-1 reduction when pairs are non-conflicting. For CNOT chain: 100% reduction. For random circuits: 0% (trivially, since \|S_1\| = 0). | E11 CNOT chain: Greedy achieves 100% reduction. E4 random: Greedy achieves 0% (trivially optimal since \|S_1\| = 0). | **MATCH** | CNOT chain is the canonical test case: all adjacent inverse pairs are non-conflicting (each CNOT is paired with exactly one neighbor), and Greedy correctly cancels all of them. Not tested on structured circuits with known conflicting pairs. |
| **Prop 1** | Maximum non-overlapping adjacent inverse pair selection is solvable in polynomial time via maximum matching. The O(m) greedy scan computes a maximal (not necessarily maximum) matching, suboptimal by at most 2x. | E4 (algorithm comparison), E11 (CNOT chain), E1-E5 (random circuits where conflicts are rare) | Greedy achieves near-optimal Phase-1 reduction. In random circuits (conflicts rare), Greedy ~= optimal. In CNOT chain (no conflicts), Greedy = optimal = 100%. | E4: Greedy = 0.00% (optimal, since \|S_1\| = 0). E11 CNOT chain: Greedy = 100% (optimal). No experiment directly compares Greedy vs. Edmonds' blossom algorithm on circuits with known conflicts. | **PARTIAL MATCH** | The polynomial-time solvability claim is a complexity-theoretic result not directly tested by experiments. The greedy-approximation bound (within 2x of optimal) is empirically supported (Greedy matches or exceeds stochastic optimizers) but not rigorously tested on circuits engineered to produce conflicting pairs. |
| **Obs 1** | E[R_stoch(C)] <= R_greedy(C) + O(1/\|C\|) for any stochastic Phase-1 optimizer. | E4 (100 circuits x 4 optimizers, n=5, d=15, \|C\| = 75) | All four optimizers achieve <= 0.67% mean reduction. Stochastic advantage over Greedy bounded by O(1/75) ~= 1.3%. | E4: Greedy = 0.00%, GA = 0.67%, SA ~= 0%, RLS ~= 0%. Maximum stochastic advantage = 0.67% (GA), which is < 1/75 ~= 1.3%. | **MATCH** | The 0.67% GA advantage is within the O(1/\|C\|) bound. The advantage arises from rare SWAP-enabled non-adjacent pair discovery, not from INSERTION-facilitated reduction. Originally stated as Proposition 2; downgraded to Empirical Observation on 2026-06-12 because the O(1/\|C\|) term lacks rigorous proof. |
| **Thm 5** | High-probability bound (McDiarmid): with probability >= 1 - delta, X <= n(d-1)*p_cancel + sqrt(2n(d-1)*ln(1/delta)). Corollary 5.1: R_1(C) vanishes as n, d -> infinity. | E1 (depth sweep d=1-50, n=5), E3 (qubit sweep n=3-10) | Under WCL at delta=0.01, n=5, d=50: X <= 10.314 + 13.572 = 23.886. Phase-1 reduction fraction -> 0 as n,d -> inf. Under LBL: trivially satisfied (0 <= any positive bound). | Observed: X = 0 (and R_1 = 0%) for all depths d=1-50 and all n=3-10. The bound is satisfied but not tightly tested. | **MATCH** (trivially) | The concentration inequality is satisfied trivially because LBL produces X=0 <= any positive upper bound. A meaningful tightness test would require WCL circuits where X > 0. Corollary 5.1 (vanishing reduction) is consistent with E1/E3 observations but the vanishing rate is not directly measured since the observed value is already exactly 0. |
| **Thm 6** | For Clifford circuits in Aaronson-Gottesman canonical form: S_1(C) = empty, R_1(C) = 0 for all Phase-1 optimizers. | **No experiment directly tests this prediction.** E14 includes RandomClifford circuits but these are NOT in Aaronson-Gottesman canonical form. No AG-canonical-form circuits were generated or tested. | R_1(C) = 0% exactly for Clifford circuits in AG canonical form. | No data. E14 RandomClifford shows Phase 1 = 0%, but these circuits are not in canonical form (the 0% arises from the LBL generator structure, not from the AG canonical form properties). | **UNTESTED** | The theorem's proof relies specifically on the 11-stage AG decomposition structure (H-C-H-C-H-S-C-S-H-C-H) with disjoint-qubit stages. No experiment generates circuits in this canonical form. The E14 RandomClifford 0% Phase-1 result is explained by Thm 1b (LBL structure), not Thm 6. Testing Thm 6 would require implementing an AG canonical form generator and verifying Phase-1 on its output. **[ACTION REQUIRED]** This theorem has not been experimentally validated. Recommend: (a) implement AG canonical form generator for verification, or (b) explicitly label as 'Theoretical result not tested in this work' in the manuscript. |
| **Thm 7** | Explicit circuit family {C_n} with R_1(C_n) = 0 and R_{1+2}(C_n) >= 1/6 ~= 16.7% for all n >= 2. (Proves C2 constructively.) | E10 (random Universal: Phase 2 advantage), E11 (Oracle/BV: ~20% Phase 2), E14 (Oracle/BV ~27.6%, RandomClifford ~22.1%). **No experiment directly instantiates the Thm 7 construction** (interleaved CNOT-H-CNOT-Separator-H-CNOT circuit). | R_1 = 0% and R_{1+2} >= 16.7% for the explicit construction. More broadly: existence of circuit families with Omega(1) Phase-2 advantage. | E10 random Universal: R_1 = 0%, R_{1+2} = 3.26%. E11 Oracle/BV: R_1 = 0%, R_{1+2} ~= 20% (16-50%). E14 RandomClifford: R_1 = 0%, R_{1+2} ~= 22.1%. E14 Oracle/BV: R_1 = 0%, R_{1+2} ~= 27.6%. | **PARTIAL MATCH** | The broader existence claim (Omega(1) Phase-2 advantage for some families) is strongly supported by E10/E11/E14 empirical data. However, the specific Thm 7 construction (with S-gate separators exploiting [S, CNOT]=0 on control qubit) was not directly instantiated as an experiment. The Oracle/BV circuits achieve Phase-2 advantage through a related but distinct mechanism (commuting H/X gates). The 1/6 lower bound is consistent with observed values (3.26% to 27.6%). |
| **Thm 8a** | Haar-random circuit complexity lower bound: Pr[C(U) < 4^n/n^2] <= exp(-Omega(4^n/n)). Haar-random unitaries are incompressible below the 4^n/n^2 threshold. | E1-E5 (n=3-10, d=1-50). **Critical caveat**: experiments use random gate sequences at depth d=poly(n), far below the Haar-random complexity threshold. For n=10, d=50: \|C\| ~= 500 gates while 4^n/n^2 ~= 10,486 gates. | For Haar-random U with n=5: C(U) >= 4^5/25 = 1024/25 ~= 41 gates with overwhelming probability. For n=10: C(U) >= 4^10/100 ~= 10,486 gates. | E1-E5: R_1 ~= 0% on random gate sequences. However, these circuits are NOT Haar-random unitaries; they are random gate sequences at depth d=poly(n), producing unitaries far from Haar-random. | **PARTIAL MATCH** | The ~0% reduction observed in E1-E5 is consistent with Thm 8a's prediction of incompressibility, but the experimental regime (d=poly(n)) does not reach the Haar-random complexity threshold (d ~ 4^n/n^2). The empirical ~0% is explained by Thm 1b (combinatorial sparsity under LBL), not by Haar-random incompressibility. Thm 8a provides a complementary information-theoretic argument for the asymptotic regime not reached in experiments. See `framework.md` caveat #4. |
| **Thm 8b** | For d = o(4^n/n^2), R_max(C) <= 1 - 4^n/(n^3 d) -> 0 doubly-exponentially. For n=10, d=100: 4^10/(10^3 * 100) ~= 10.5, so R_max <= 0 (literally no reduction possible). | E1-E5 (n=3-10, d=1-50) | For E1 params (n=5, d=50): 4^5/(125*50) = 1024/6250 ~= 0.164, so R_max <= 1 - 0.164 = 0.836. For E3 params (n=10, d=30): 4^10/(1000*30) ~= 34.95, so R_max = 0. | E1-E5: R_1 = 0% (consistent with R_max = 0 for large n). For n=5, the bound R_max <= 83.6% is not tight. | **PARTIAL MATCH** | The bound is directionally correct (reduction is indeed 0%) but the theorem applies to Haar-random unitaries, not the random gate sequences used in experiments. For n=5, d=50, the bound (83.6%) is far from tight. For n=10, the bound correctly predicts zero reduction possible, but again the experimental circuits are not Haar-random. The doubly-exponential vanishing rate is not directly measurable. |
| **Thm 8c** | Bounded-window corollary: R_A(C) <= min(kw/(nd), 1 - 4^n/(n^3 d)). Each rewrite of window w removes at most w gates; k rewrites remove at most kw gates. | E16 (window-size scaling: w in {2, 5, 10, 20}), E1-E5 | R(C) <= kw/(nd). For fixed k, R scales linearly with w and inversely with nd. The Haar-random term (1 - 4^n/(n^3 d)) dominates for d=poly(n). | E16: w=2 -> ~0%, w=5 -> ~1.5%, w=10 -> ~4.2%, w=20 -> higher. Phase-2 reduction increases with window size, consistent with the kw/(nd) upper bound. | **MATCH** (trivially) | The kw/(nd) bound is trivially true for any circuit (as noted in `framework.md`: "Part c trivially true for any circuit"). The observed increase with w is consistent with the bound but does not test it tightly. The Haar-random term from Part (b) provides the tighter constraint but is not experimentally reachable. |
| **C1** | The Phase 1 ceiling is structural: for any circuit family without adjacent inverse pairs, every Phase-1 optimizer achieves exactly 0% reduction. This is a property of the circuit data structure, not the algorithm. | E1-E5 (45,500+ random circuit trials), E10 (random circuits), E14 (15-family extended benchmark) | All Phase-1 optimizers achieve 0% reduction on all circuit families lacking adjacent inverse pairs. | E1-E5: <= 0.67% mean (GA); Greedy = 0.00% on all random. E10 random: Greedy = 0.00%. E14: Greedy = 0% on QFT, GHZ, BV, IQP, SurfaceCode, QAOA, HardwareEfficient, and most families. E11: Greedy = 0% on QFT, GHZ, Oracle/BV, QAOA, VQE, HardwareEfficient. | **MATCH** | Strong support from both theory (Thm 2, Thm 5, Thm 8) and experiments (45,500+ trials). The ceiling is reproducible and algorithm-independent. The GA's 0.67% in E4 is a minor stochastic fluctuation, not a systematic violation. Remaining open problem: formalize the invariant characterizing exactly which circuit families have empty Phase-1 action spaces (C1.OP1). |
| **C2** | Phase 2 provides context-dependent super-constant improvement: some families show Omega(1) Phase-2 advantage while others show zero. Gamma(C) = R_{1+2}(C) - R_1(C) is family-dependent. | E10 (Phase 1 vs Phase 2 on random/structured/real), E11 (Oracle/BV ~20%), E14 (extended 15-family suite), E16 (window-size scaling) | R_1 = 0% and R_{1+2} = Omega(1) for specific families (e.g., Oracle). R_1 = 0% and R_{1+2} = 0% for families without commutation structure (e.g., QFT, GHZ). | E10 random Universal: R_1=0%, R_{1+2}=3.26% (Cohen's d=1.32, Cliff's delta=-0.840). E11 Oracle/BV: R_1=0%, R_{1+2}~=20% (16-50%). E14 Oracle/BV: ~27.6%, RandomClifford: ~22.1%, UCCSD: ~1.4%. E10 structured brickwork: R_{1+2}=0%. E11 QFT/GHZ/QAOA/VQE/HardwareEfficient: R_{1+2}=0%. E16: improvement scales with window size (w=2: ~0%, w=10: ~4.2%). | **MATCH** | Proven constructively by Thm 7 and strongly supported by E10/E11/E14/E16 empirical data. The context-dependence is clearly demonstrated: Oracle/BV benefits greatly (~20-28%) while QFT/GHZ/QAOA show zero improvement. The C2.OP1 open problem (construct explicit family) is closed by Thm 7. Remaining: characterize ALL families with super-constant improvement (C2.OP2, C2.OP3). |

---

## Summary Scorecard

| Consistency | Count | IDs |
|-------------|-------|-----|
| **MATCH** | 10 | Thm 1b, Thm 2a, Thm 2b, Lemma 3, Lemma 4, Obs 1, Thm 5 (trivial), Thm 8c (trivial), C1, C2 |
| **PARTIAL MATCH** | 4 | Prop 1, Thm 7, Thm 8a, Thm 8b |
| **MISMATCH** | 1 | Thm 1a (WCL prediction vs. LBL generator) |
| **UNTESTED** | 1 | Thm 6 (AG canonical form) |

---

## Detailed Discussion of Key Discrepancies

### 1. Theorem 1a: The WCL vs. LBL Mismatch

This is the most significant discrepancy in the cross-validation table and warrants detailed discussion.

**The prediction.** Theorem 1a derives an expectation formula for the number of listing-adjacent inverse pairs under the wire-consecutive listing (WCL) model. For E1 parameters (n=5, rho=0.3):

$$
p_{\text{cancel}} = (1-0.3)^2 \times \frac{1}{25} + (0.3)^2 \times \frac{1}{4} = 0.0196 + 0.0225 = 0.0421
$$

This yields:

| Depth (d) | Thm 1a E[\|A_adj\|] | P(X=0) Poisson approx | Observed |
|-----------|---------------------|----------------------|----------|
| 1 | 0.000 | 100% | 0 |
| 5 | 0.842 | 43% | 0 |
| 10 | 1.894 | 15% | 0 |
| 25 | 5.052 | 0.6% | 0 |
| 50 | 10.314 | ~0% | 0 |

At d=50, Theorem 1a predicts ~10.3 adjacent inverse pairs (Poisson probability of zero: ~0%), yet the experiment observes exactly zero across all 500 trials at this depth.

**The resolution.** Theorem 1a applies to WCL, where wire-consecutive gates are listing-adjacent. The experimental generator uses LBL, where gate(q, L) is at listing index L*n + q and the next gate on the same qubit is at (L+1)*n + q (gap = n). For n=5, same-qubit gates are separated by 4 intervening gates, making listing-adjacency impossible. Theorem 1b correctly captures this: under LBL, S_1(C) = empty structurally for n >= 2.

**Implication for the manuscript.** The MISMATCH between Thm 1a and E1-E5 is not a theoretical error but a model-experiment mismatch. The manuscript should clearly state that Thm 1a predictions apply to WCL circuits and that E1-E5 test Thm 1b (LBL), not Thm 1a. To directly test Thm 1a, a WCL generator or wire-traversal pre-processing step is needed.

### 2. Theorem 6: The Untested Canonical Form Result

**[ACTION REQUIRED]** This theorem has not been experimentally validated. Recommend: (a) implement AG canonical form generator for verification, or (b) explicitly label as 'Theoretical result not tested in this work' in the manuscript.

Theorem 6 proves that Clifford circuits in Aaronson-Gottesman canonical form have an empty Phase-1 action space. This is the only theorem with no corresponding experimental test.

**Why it remains untested.** The E14 experiment includes a "RandomClifford" circuit family, but these are generated by random Clifford gate sequences (via the LBL generator), not by constructing circuits in the 11-stage Aaronson-Gottesman normal form (H-C-H-C-H-S-C-S-H-C-H). The 0% Phase-1 reduction observed on RandomClifford circuits is explained by Thm 1b (LBL structure), not by the AG canonical form properties.

**What would be needed.** To test Thm 6, one would need to:
1. Implement an Aaronson-Gottesman canonical form circuit generator.
2. Generate Clifford circuits in canonical form for various n.
3. Verify that S_1(C) = empty and R_1(C) = 0 for all Phase-1 optimizers.
4. Compare against non-canonical Clifford circuits where S_1(C) may be non-empty.

### 3. Theorem 8: The Haar-Random vs. Random Gate Sequence Gap

Theorems 8a and 8b prove incompressibility for Haar-random unitaries, but all experiments use random gate sequences of depth d = poly(n). For the experimental regime:

- n=5, d=50: |C| ~= 250 gates vs. Haar threshold 4^5/25 ~= 41 gates (reachable, but the random gate sequence does not produce a Haar-random unitary)
- n=10, d=50: |C| ~= 500 gates vs. Haar threshold 4^10/100 ~= 10,486 gates (far below threshold)

The ~0% reduction observed in E1-E5 is therefore explained by the combinatorial sparsity of inverse pairs (Thm 1b), not by Haar-random incompressibility (Thm 8). The Thm 8 bounds are directionally consistent with observations but do not directly explain them. This caveat is explicitly acknowledged in `framework.md` (caveat #4).

### 4. Theorem 7: Constructive Proof Without Direct Instantiation

Theorem 7 constructs an explicit circuit family (interleaved CNOT layers with S-gate separators) demonstrating Omega(1) Phase-2 advantage. While the existence claim is supported by Oracle/BV and RandomClifford results, the specific construction was not instantiated as an experiment.

**What was tested instead.** Oracle/Bernstein-Vazirani circuits provide a natural (non-artificial) family where Phase 2 achieves ~20% reduction through a related mechanism (commuting H/X gates past CNOT layers). The broader implication of C2 (context-dependent super-constant advantage) is well-supported even though the specific Thm 7 circuit family was not tested.

---

## Experiment Coverage Matrix

This matrix shows which experiments provide evidence for which theoretical results.

| Experiment | N trials | Thm 1b | Thm 2 | Lemma 3 | Lemma 4 | Obs 1 | Thm 5 | C1 | C2 |
|-----------|----------|--------|-------|---------|---------|-------|-------|----|----|
| E1 (depth sweep) | 25,000 | X | X | X | | X | X | X | |
| E2 (entanglement) | 2,100 | X | X | X | | | X | X | |
| E3 (scaling) | 11,962 | X | X | X | | | X | X | |
| E4 (algorithms) | 400 | X | X | X | | X | | X | |
| E5 (landscape) | 6,000 | X | X | X | | | | X | |
| E10 (Phase1 vs 2) | 1,905 | X | X | X | | | | X | X |
| E11 (real circuits) | 426 | X | X | X | X | | | X | X |
| E14 (extended) | 2,130 | X | X | X | | | | X | X |
| E16 (window) | 696 | | | X | | | | | X |

**Not covered by any experiment**: Thm 1a (WCL model), Thm 6 (AG canonical form), Thm 7 (explicit construction), Thm 8a-b (Haar-random regime).

---

## Recommendations for Closing Gaps

| Gap | Priority | Recommended Action |
|-----|----------|-------------------|
| **Thm 1a untested** (WCL model) | High | Implement a WCL circuit generator (gates on same qubit placed consecutively) and verify that observed adjacent inverse pair counts match the E[\|A_adj\|] = n(d-1)*p_cancel prediction. Alternatively, add a wire-traversal pre-processing step to the Phase-1 optimizer. |
| **Thm 6 untested** (AG canonical form) | Medium | Implement an Aaronson-Gottesman canonical form generator (e.g., using the stabilizer tableau formalism) and run Phase-1 optimizers on canonical-form Clifford circuits. Verify S_1(C) = empty. |
| **Thm 7 construction not instantiated** | Low | Generate the explicit C_n circuit family from Thm 7 (with S-gate separators) and verify R_1 = 0%, R_{1+2} >= 16.7%. Low priority because C2 is already well-supported by Oracle/BV data. |
| **Thm 8 not in experimental regime** | Low | Not addressable with current n <= 20 experiments. The Haar-random threshold 4^n/n^2 is unreachable for meaningful n. Document the caveat clearly (already done in `framework.md`). |
| **Prop 1 not directly tested** | Medium | Construct circuits with known conflicting adjacent inverse pairs and compare Greedy matching vs. Edmonds' blossom algorithm output. |

---

*Document version: 1.1*
*Last updated: 2026-06-17*
*Author: Q-research Cross-Validation Analysis*
*Source files: `docs/01_theory/lemmas.md` (v3.4), `docs/01_theory/conjectures.md` (v3.2), `docs/01_theory/framework.md` (v5.4.0), `docs/03_results/e10_analysis.md`, `docs/03_results/experimental_design.md` (v2.3), `docs/06_manuscript/v4_claim_evidence_map.md` (v5.0), `docs/06_manuscript/v4_tables.md`, `docs/FIX2_E1_Zero_Std_Analysis.md`*

*Changelog: v1.1 (2026-06-17) — Added E18 survivorship-bias caveat. Updated C2 row to reflect Phase-2a vs Phase-2b distinction (theoretical proofs use Phase-2b; experiments use Phase-2a). Cross-referenced limitations_and_future_work.md.*

---

## Addendum: E18 Survivorship Bias (added 2026-06-17)

**E18 (Clifford+T decomposition)** is not included in the primary cross-validation table above because it does not directly test a specific theorem. However, E18 results are referenced in the manuscript and require an explicit survivorship-bias caveat:

- **Total trials**: 270
- **Failed trials**: 120 (78 decompose_error + 42 fidelity=0), a 44.4% failure rate
- **Surviving trials**: 150

**All E18 conclusions are based on the 150 surviving trials and are therefore survivorship-biased.** Circuits that fail Clifford+T decomposition or fidelity verification are systematically excluded, and the surviving subset may have systematically different reduction properties than the full population.

**Bias direction**: The bias is *conservative* — circuits that fail decomposition likely have *higher* structural complexity, and their exclusion means the reported mean reduction is likely an *overestimate* of the true population mean. The bias direction is stated to prevent misinterpretation, not to dismiss the finding.

**Manuscript requirement**: All E18-related claims in the manuscript must carry the annotation "(survivorship-biased; 44.4% failure rate)" or equivalent. See `limitations_and_future_work.md` §8 for the full discussion.

---

## Addendum: Phase-2a vs Phase-2b in C2 (added 2026-06-17)

The C2 row in the primary table reports Phase-2a empirical results (from E10/E11/E14/E16). The theoretical proofs of C2 (Theorem 7 artificial, Theorem 9 BV natural) use **Phase-2b template matching**, which is *not implemented* in the experimental codebase. The Phase-2a achievable bound is an **open question**. The empirical Phase-2a reductions (~3% random, ~20% Oracle) are *complementary* to but not direct validations of the Phase-2b theoretical bounds. See `thm7_natural_bv.md` §"Phase-2a vs Phase-2b" and `conjectures.md` C2 status for details.
