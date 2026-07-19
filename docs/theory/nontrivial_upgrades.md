# Non-Trivial Upgrade Analysis

**Version**: 1.0 (Draft)
**Date**: 2026-07-17
**Status**: Evaluation of which existing theorems can be elevated from "supporting observation" to "non-trivial technical contribution" through deepening or generalization.

---

## Grading Scale

| Grade | Meaning |
|-------|---------|
| ★★★ | Genuinely novel, publishable standalone result |
| ★★☆ | Significant improvement, strengthens paper substantially |
| ★☆☆ | Modest upgrade, worth including if low cost |
| ☆☆☆ | Current status is appropriate; upgrade not advisable |

---

## 1. Thm 1a/1b: Adjacent Inverse Pair Density / LBL Structural Emptiness

**Current status:** Elementary combinatorial calculation (Thm 1a) and trivial structural observation (Thm 1b). The framework document rates both as "supporting" — Thm 1a is a birthday-paradox-style bound, Thm 1b is a $n \ge 2 \Rightarrow \text{gap} \ge 2$ argument.

**Current contribution grade:** ☆☆☆ (supporting, not novel)

### Upgrade Path A: Generalize to non-adjacent (Phase-2) action space

**Idea.** Replace listing-adjacent pairs with commutation-adjacent pairs. Instead of counting $(g_i, g_{i+1})$ pairs, count $(g_i, g_k)$ pairs where all intermediate gates commute with both $g_i$ and $g_k$, and $g_k = g_i^{-1}$.

**Upgraded statement (Thm 1a$^+$).** For a random circuit $C(n,d,\rho)$, the expected Phase-2 action space size satisfies

$$
\mathbb{E}[|\mathcal{S}_{1+2}(C) \setminus \mathcal{S}_1(C)|] \le n(d-1) \cdot \frac{1}{(n-1)^2} \cdot O(1),
$$

which is $O(d/n)$ — vanishing as $n$ grows. This formalizes why Phase-2a advantage on random circuits is tiny (~3.26% empirical).

**Difficulty:** High. Requires analyzing commutation relations across non-adjacent gate pairs in a random circuit. The commutation graph is dense (many gates commute by disjoint qubits), so the non-adjacent inverse pair count could be much larger than the adjacent count. The bound would need to account for the fact that even though many pairs commute, most are not inverses.

**Expected grade if completed:** ★★☆ — would provide a theoretical foundation for why Phase-2a advantage is small on random circuits.

### Upgrade Path B: Generalize listing model analysis to arbitrary gate orderings

**Idea.** Thm 1b proves $\mathcal{S}_1(C)=\emptyset$ for LBL. More generally, characterize which gate orderings make $\mathcal{S}_1$ empty.

**Upgraded statement (Thm 1b$^+$).** For any circuit $C$, the Phase-1 action space $\mathcal{S}_1(C)$ is empty iff, for every qubit $q$, no two consecutive gates on $q$ in the circuit listing are mutual inverses. This reduces to: a circuit is Phase-1-irreducible iff its per-wire gate sequences contain no $g \cdot g^{-1}$ subsequence.

**Trivial reformulation.** This is just the definition restated. Not an upgrade.

### Upgrade Path C: WCL reduction high-probability concentration

**Idea.** Thm 5 gives a high-probability bound for LBL (trivially $\Pr[R_1 > 0] = 0$). Extend to WCL.

**Upgraded statement (Thm 1a$^+$ WCL).** Under WCL, with probability at least $1 - \delta$,

$$
R_1^{\text{WCL}}(C) \le 2p_{\text{cancel}} + \sqrt{\frac{2\ln(1/\delta)}{n(d-1)}} + O(1/(nd)).
$$

**Difficulty:** Low — follows immediately from McDiarmid (Thm 5 style) on the WCL representation.

**Expected grade if written up:** ★☆☆ — useful concentration bound, but methodologically straightforward.

### Verdict

| Path | Difficulty | Impact | Grade |
|------|-----------|--------|-------|
| A: Non-adjacent action space size | High | Moderate | ★★☆ |
| B: Arbitrary orderings | Trivial | Zero | ☆☆☆ |
| C: WCL concentration | Low | Low | ★☆☆ |

**Recommendation:** Pursue Path A if the Phase-2 action space analysis fills a clear gap in the manuscript (it explains why ~3% Phase-2a advantage on random circuits is the correct scale). Skip Path B (already definitional). Include Path C as a short note in the WCL discussion.

---

## 2. Thm 2c/2d: INSERTION Cascade Lemma

**Current status:** Bounded INSERTION cascade (Thm 2c: $R_{\text{removal}} \le 2k$) and INSERTION commutation cascade bound (Thm 2d: cannot exceed Phase-2 action space). These resolve a previously open gap in the INSERTION argument and are considered "resolved" in the framework.

**Current contribution grade:** ★★☆ (technically non-trivial, resolved a known gap)

### Upgrade Path A: Extend INSERTION + Phase-2 combination

**Idea.** Current Thm 2d says INSERTION within Phase 1 cannot exceed Phase-2 action space. What about INSERTION *within Phase 2* — i.e., commutation rewriting combined with deliberate identity insertion?

**Upgraded statement (Thm 2e).** For any Phase-2 optimizer (commutation + INSERTION), the INSERTION cascade cannot achieve net reduction beyond the Phase-2 action space augmented by template identities. Formally:

$$
R_{\text{Phase-2 + INSERTION}}(C) \le R_{\text{Phase-2b}}(C),
$$

where Phase-2b includes template matching.

**Proof idea (sketch).** INSERTION in Phase 2 is strictly weaker than template matching because:
1. INSERTION can only add identity pairs $(g, g^{-1})$, which are single-gate templates.
2. Template matching can apply any $k$-gate identity ($k \ge 2$), including the $H$-CNOT-$H$ identity (3 gates) that enables the BV reduction.
3. Therefore Phase-2a + INSERTION $\subseteq$ Phase-2b in terms of achievable reduction.

This is a useful structural result that clarifies the hierarchy: Phase-2a $\subset$ Phase-2a + INSERTION $\subset$ Phase-2b (strict inclusions if templates exist).

**Difficulty:** Medium. Requires showing that any INSERTION-facilitated reduction in Phase 2 can be simulated by a Phase-2b template. The key step is to show that an INSERTION creates an identity pair $(g, g^{-1})$, which is a template of size 2 — but the subsequent commutation that brings it into contact with other gates is already Phase-2a functionality.

**Expected grade if completed:** ★★☆ — clarifies the Phase-2a/2b hierarchy and justifies the current Thm 9 Phase-2b focus.

### Upgrade Path B: Reverse direction — Phase-2b reduction implies INSERTION cascade

**Idea.** Conversely, can any Phase-2b template be simulated by Phase-2a + INSERTION? If so, the hierarchy collapses.

**Conjecture (Thm 2f, negative).** There exist Phase-2b templates that cannot be simulated by Phase-2a + INSERTION. The $H$-CNOT-$H$ template is such an example.

**Evidence.** The $H$-CNOT-$H$ template changes the CNOT direction (control $\leftrightarrow$ target). No sequence of INSERTION ($g, g^{-1}$) and commutation (which preserves wire order up to commutation) can change the direction of a CNOT, because:
- INSERTION only adds identity pairs — it does not modify existing gates.
- Commutation only reorders gates — it does not change gate semantics.
- CNOT direction reversal requires replacing $\text{CNOT}(c,t)$ with $\text{CNOT}(t,c)$, which is a change of gate parameters, not a reordering or insertion.

Therefore $\text{Phase-2a + INSERTION} \subsetneq \text{Phase-2b}$ strictly.

**Difficulty:** Low-Medium. The argument is simple if we can formalize "commutation and insertion preserve CNOT direction" as an invariant.

**Expected grade if completed:** ★★☆ — establishes strict hierarchy, justifies Phase-2b as a separate optimization phase.

### Verdict

| Path | Difficulty | Impact | Grade |
|------|-----------|--------|-------|
| A: Phase-2 + INSERTION bound | Medium | Moderate | ★★☆ |
| B: Strict hierarchy (CNOT direction) | Medium | Moderate | ★★☆ |

**Recommendation:** Pursue both as a package — "On the Hierarchy of Phase-2 Optimization Techniques" — three-tier theorem:
- Phase-2a $\subset$ Phase-2a + INSERTION $\subset$ Phase-2b (strict)
- Proved via INSERTION-invariant (Thm 2c/2d), CNOT-direction invariant (Thm 2f), and BV template gap (Thm 9).

---

## 3. Thm 6: AG Canonical Form Clifford Ceiling

**Current status:** Proves $\mathcal{S}_1(C)=\emptyset$ for Clifford circuits in Aaronson-Gottesman canonical form. The proof relies specifically on the 11-stage decomposition ($H$-$C$-$H$-$C$-$H$-$S$-$C$-$S$-$H$-$C$-$H$) with disjoint-qubit stages.

**Current contribution grade:** ★★☆ (non-trivial but Clifford-only, and AG form is already minimal)

### Upgrade Path A: Generalize to arbitrary normal forms (universal gate sets)

**Idea.** The AG canonical form is Clifford-specific. Can we prove an analogous structural result for a normal form over a universal gate set? E.g., CNOT + $R_z$ + Hadamard, or the phase-polynomial normal form ($R_z$ rotations + CNOTs + $H$ boundary).

**Upgraded statement (Thm 6$^+$).** Let $\mathcal{G} = \{H, \text{CNOT}, R_z(\theta)\}$ (the standard universal gate set for compilation). Any circuit $C$ over $\mathcal{G}$ can be reduced to a normal form with $k \le 3$ "layers" of $H$ gates (one at each end and possibly in the middle), and within each $H$ layer, $H$ gates act on disjoint qubits. In this normal form, $\mathcal{S}_1(C) = \emptyset$.

**Difficulty:** Very high. The existence of a universal normal form with the required structural properties is a well-known open problem in quantum circuit synthesis. The closest known result is the $H$-$R_z$-$H$ decomposition (which is essentially the Euler angle decomposition for single qubits, extended to $n$ qubits via CNOT), but this does not give a canonical ordering with the same guarantees as AG.

**Expected grade if completed:** ★★★ — would be a major result in quantum circuit theory.

### Upgrade Path B: Clifford circuits NOT in canonical form

**Idea.** Thm 6 says AG-canonical Clifford circuits have $R_1=0$. What about *arbitrary* Clifford circuits (not in canonical form)? Can we bound $R_1$?

**Upgraded statement (Thm 6$^+$ B).** For any Clifford circuit $C$ on $n$ qubits, the Phase-1 reduction achievable by a single greedy pass is at most $O(n/|C|)$.

**Proof sketch.** Any Clifford circuit can be converted to AG canonical form in $O(n^3)$ time. The AG canonical form has no adjacent inverse pairs (Thm 6). The conversion process is a rewriting that eliminates redundant pairs. In the worst case, the original circuit may have up to $O(n)$ redundant pairs (e.g., a circuit that repeats each canonical stage $k$ times), which the AG conversion removes. After conversion, $R_1 = 0$. Therefore the original $R_1(C)$ is bounded by the number of AG-removable redundant pairs, which is $O(n)$ for any $n$-qubit Clifford circuit (since the AG form has $O(n)$ gates). Hence $R_1(C) \le O(n/|C|)$. $\square$

**Difficulty:** Low. This follows from the AG conversion algorithm and Thm 6.

**Expected grade if completed:** ★☆☆ — a modest bound that formalizes the intuition that Clifford circuits are "close to" their canonical form.

### Upgrade Path C: Non-Clifford+codes in canonical forms (e.g., CNOT$+T$)

**Idea.** Extend to CNOT$+T$ circuits, which have a canonical form via the phase-polynomial representation [Amy et al., 2013].

**Upgraded statement (Thm 6$^+$ C).** For any CNOT$+T$ circuit in the Amy-Maslov-Mosca normal form (Hadamard-free layers separated by Hadamard gates), $\mathcal{S}_1(C) = \emptyset$ for circuits with at most one $H$ layer.

**Difficulty:** Medium. The Amy-Maslov-Mosca normal form decomposes CNOT$+T$ circuits into $H$-free subcircuits connected by $H$ gates. Within each $H$-free subcircuit, all gates are CNOTs and $T$ gates. CNOTs may be adjacent on the same qubit pair (creating inverse pairs), but the normal form removes these redundancies. Showing that the normal form eliminates all adjacent inverse pairs requires a careful analysis of the rewriting system.

**Expected grade if completed:** ★★☆ — extends structural ceiling from Clifford to CNOT$+T$, a practically significant family.

### Verdict

| Path | Difficulty | Impact | Grade |
|------|-----------|--------|-------|
| A: Universal normal form | Very high | Major (★★★) | Unlikely feasible |
| B: Arbitrary Clifford bound | Low | Modest (★☆☆) | Worth including |
| C: CNOT$+T$ normal form | Medium | Significant (★★☆) | Most promising |

**Recommendation:** Pursue Path C (CNOT$+T$ extension) as primary. Path B as a short note. Path A is a research program, not a theorem upgrade.

---

## 4. Thm 7: Hardness Family Phase-2a Advantage (1/6 Bound)

**Current status:** Constructive existence proof of a circuit family with $\Omega(1)$ Phase-2a advantage ($R_{1+2a} \ge 1/6$). The construction is artificial (designed for the proof) and validated experimentally (E24: mean $0.7980 > 1/6$).

**Current contribution grade:** ★★☆ (proves C2 constructively, but artificial)

### Upgrade Path A: Tighten the bound from 1/6 to 2/5

**Idea.** The current construction achieves $2/5 = 0.4$ (as noted in the proof). The $1/6$ bound is conservative. Upgrade to the tight bound.

**Upgraded statement (Thm 7$^+$).** The explicit family $\{C_n\}$ satisfies $R_{1+2a}(C_n) \ge 2/5$ for all $n \ge 4$.

**Proof.** Already in the current proof (gate count analysis shows $2n/5n = 2/5$). The $1/6$ was a deliberately loose bound. $\square$

**Difficulty:** Trivial — already proven.

**Expected grade if completed:** The bound is already in the proof; just update the statement.

### Upgrade Path B: Make the construction natural (not artificial)

**Idea.** Modify the construction to correspond to a known quantum algorithm or circuit family, strengthening the parallel with Thm 9 (which is natural).

**Approach.** The current construction uses $S$-separated CNOT pairs. This structure is reminiscent of:
- **Quantum teleportation circuits**: teleportation uses CNOT + $H$ + measurement, similar to the CNOT-$S$-CNOT pattern.
- **Error correction parity-check circuits**: surface code syndrome extraction uses repeated CNOT patterns with $S$ gates for phase correction.
- **Phase estimation**: controlled-$U$ operations separated by $S$ or $T$ gates.

**Difficulty:** High. Making the construction natural while preserving the Phase-2a advantage requires finding a real algorithm whose circuit naturally includes $S$-commuting CNOT pairs. The $S$ gate is explicitly used for phase in quantum algorithms, so a connection to phase estimation or Shor's algorithm may be possible.

**Expected grade if completed:** ★★★ — would bridge the artificial/natural gap and provide a second natural family alongside BV.

### Upgrade Path C: Maximum achievable advantage

**Idea.** What is the maximum possible Phase-2a advantage for any circuit family? Can we find a family with $R_1=0$ and $R_{1+2a} \to 1$ (full reduction)?

**Construction.** Consider the circuit $C_n$ consisting of $n/2$ independent copies of the Thm 7 pattern. If the separators are chosen such that the commutation chain exposes all gate pairs, the reduction could approach $1 - O(1/n)$.

**Upper bound.** For any circuit with $R_1=0$, the Phase-2a advantage is at most $1 - \frac{\mathcal{C}(U)}{|C|}$ where $\mathcal{C}(U)$ is the circuit complexity of the unitary. This is bounded away from $1$ for non-identity unitaries.

**Difficulty:** Medium. The upper bound follows from Thm 8. The construction achieving near-full reduction is possible for identity-implementing circuits (like Thm 7's family).

**Expected grade if completed:** ★★☆ — provides a Phase-2a advantage range $[0, 1)$ and shows the construction can saturate it.

### Verdict

| Path | Difficulty | Impact | Grade |
|------|-----------|--------|-------|
| A: Tighten to 2/5 | Trivial | Minimal (★☆☆) | Just update the statement |
| B: Natural construction | High | Major (★★★) | High risk, high reward |
| C: Max advantage range | Medium | Significant (★★☆) | Worth exploring |

**Recommendation:** Update Thm 7's bound to the actual value 2/5 (Path A, trivial). Pursue Path C as a discussion point (what is the range of $\Gamma$?). Path B is an independent research direction.

---

## 5. Thm 5: High-Probability Bound (McDiarmid)

**Current status:** Standard application of McDiarmid's inequality to the adjacent inverse pair count. Provides a concentration bound but is methodologically routine.

**Current contribution grade:** ★☆☆ (standard technique, no novelty)

### Upgrade Path A: Multi-parameter concentration

**Idea.** McDiarmid bounds a single function $X = |\mathcal{A}_{\text{adj}}(C)|$. But the optimization process involves multiple correlated variables: $|\mathcal{S}_1(C)|$, $|\mathcal{S}_{1+2}(C)|$, $R_1(C)$, $\Gamma(C)$. A joint concentration bound would characterize the joint distribution.

**Difficulty:** Medium. Requires a multivariate extension of McDiarmid or a union bound over dependent events.

**Expected grade if completed:** ★★☆ — would strengthen the statistical guarantees.

### Upgrade Path B: PAC-Bayesian generalization bound

**Idea.** Instead of concentration of a single statistic, provide a Probably Approximately Correct (PAC) bound that generalizes from experimental observations to the circuit distribution. This would formalize the empirical findings as statistical learning guarantees.

**Difficulty:** High. Requires formulating the optimization outcome as a learning problem and applying VC-dimension or Rademacher complexity bounds to the circuit family.

**Expected grade if completed:** ★★★ — a novel connection between quantum circuit optimization and learning theory.

### Verdict

| Path | Difficulty | Impact | Grade |
|------|-----------|--------|-------|
| A: Multi-parameter concentration | Medium | Moderate (★★☆) | Natural extension |
| B: PAC-Bayesian bound | High | Major (★★★) | High novelty but difficult |

**Recommendation:** Thm 5 is fine as a supporting bound. Only pursue these upgrades if the paper needs a new theoretical angle.

---

## 6. Thm 8: Haar-Random Incompressibility

**Current status:** Proves that Haar-random circuits are essentially incompressible. The bound is standard (dimension-counting, Nielsen 2005) and explicitly does NOT apply to the experimental regime.

**Current contribution grade:** ★★☆ (standard but important contextual result)

### Upgrade Path A: Non-Haar random circuit ensembles

**Idea.** Replace the Haar-random assumption with a more practical ensemble: random circuits of depth $d$ with finite gate set. Show that these circuits are approximately Haar-random in the relevant complexity sense when $d$ exceeds the scrambling time.

**Difficulty:** Very high. The convergence of random circuits to Haar measure is an active area (Brandao-Harrow-Horodecki 2016). Making this rigorous for circuit complexity (not just approximate $t$-designs) requires new techniques.

**Expected grade if completed:** ★★★ — would directly connect Thm 8 to the experimental regime.

### Upgrade Path B: Average-case vs. worst-case separation

**Idea.** Formalize the separation: random circuits have $R_{\max} \to 0$ (Thm 8, average case) but there exist specific circuits with $R_{\max} = \Omega(1)$ (Thm 7/9, worst-case construction). This shows that the average- and worst-case behavior of CODP diverge exponentially.

**Upgraded statement (Thm 8$^+$).** Let $\mathcal{U}_{\text{Haar}}$ be the Haar measure on $U(2^n)$ and let $\mathcal{C}_n$ be the set of $n$-qubit circuits. Then:

$$
\Pr_{U \sim \mathcal{U}_{\text{Haar}}}[R_{\max}(C_U) > 0] \le \exp(-\Omega(4^n/n)),
$$

where $C_U$ is any circuit implementing $U$. Meanwhile, there exist infinite circuit families $\{C_n\}$ with $R_{\max}(C_n) = \Omega(1)$.

**Difficulty:** Low — combines Thm 8 (average) and Thm 7/9 (worst-case) with no new proof.

**Expected grade if completed:** ★☆☆ — immediate corollary of existing results.

### Verdict

| Path | Difficulty | Impact | Grade |
|------|-----------|--------|-------|
| A: Non-Haar ensembles | Very high | Major (★★★) | Separate research project |
| B: Avg/worst-case separation | Low | Minimal (★☆☆) | Worth a remark |

**Recommendation:** Keep Thm 8 as is. Add the average/worst-case separation as a remark (Path B). Do not attempt Path A within this project.

---

## 7. Thm 9: BV Oracle Phase-2b Bound

**Current status:** The strongest theoretical result — $\Omega(1)$ Phase-2b advantage for a natural circuit family. The bound $n/(4.5n+4) \to 1/4.5$ is conservative.

**Current contribution grade:** ★★★ (strongest result, natural family, non-trivial proof)

### Upgrade Path A: Tightening (see also Direction B in phase2_lower_bound_strengthening.md)

**Idea.** Reduce the overhead constant from 4.5 to 3 or lower via amortized pattern matching.

**Expected impact:** Improves limiting constant from $1/4.5 \approx 0.222$ to $1/3 \approx 0.333$. Worth while but does not change the $\Omega(1)$ classification.

### Upgrade Path B: Generalize to other oracle circuits (see Direction A)

**Idea.** Extend to Grover oracle, Simon's oracle, or general phase oracles.

**Difficulty:** Medium to high. Each oracle has a different structure and requires a custom template analysis.

### Upgrade Path C: Bridge to Phase-2a (see Direction C)

**Idea.** Show that the Phase-2b bound is actually achievable (or nearly achievable) by Phase-2a alone through a different commutation mechanism.

**Difficulty:** See Direction C analysis — likely impossible for the standard BV. A negative result (Phase-2a = 0) would elevate the Phase-2b result.

### Verdict

Thm 9 is already at ★★★. The upgrade paths are mainly about:
- **Tightening** (worth doing, improves the paper)
- **Generalizing to other oracles** (separate theorems, not upgrades to Thm 9)
- **Phase-2a bridge** (conceptual clarification, not a bound improvement)

---

## 8. Omitted but possible new theorem: Phase Transition in WCL/LBL Gap

**Current status:** Not a theorem. The WCL/LBL gap is observed empirically ($\sim 7.8\%$) and bounded in expectation (Thm D1 from the strengthening document).

**Proposed theorem (NEW: Thm 10).** For random circuits $C(n,d,\rho)$, the WCL/LBL gap $\Delta_{\text{WCL}}(n,d,\rho) = \mathbb{E}[R_1^{\text{WCL}} - R_1^{\text{LBL}}]$ satisfies:

1. **As $n \to \infty$ (fixed $d$, $\rho$):** $\Delta_{\text{WCL}} \to 0$ as $O(1/n)$.
2. **As $d \to \infty$ (fixed $n$, $\rho$):** $\Delta_{\text{WCL}} \to 2p_{\text{cancel}}$ from below as $O(1/d)$.
3. **As $\rho \to 0$:** $\Delta_{\text{WCL}} \to \frac{2(1-\rho)^2}{g_1^2}$.
4. **As $\rho \to 1$:** $\Delta_{\text{WCL}} \to \frac{2\rho^2}{g_2(n-1)}$.

**Contribution grade if written:** ★★☆ — characterizes the listing-model gap as a function of circuit parameters, providing a predictive theory for when listing model matters.

**Assessment.** This is a good candidate for a new theorem. It is:
- Proven via the expectation bound (Thm D1)
- Asymptotically tight (bounds match empirical 7.8% for E19 parameters)
- Practically relevant (guides compiler designers on when to care about listing model)

---

## 9. Omitted but possible new theorem: Phase-2a Advantage Is Not Universal

**Current status:** Empirical observation under C2. No formal theorem states that Phase-2a advantage is *not* universal.

**Proposed theorem (NEW: Thm 11).** There exist infinite circuit families $\{C_n\}$ such that:
1. $\mathcal{S}_1(C_n) = \emptyset$ (Phase-1 action space empty).
2. $\mathcal{S}_{1+2a}(C_n) = \emptyset$ (Phase-2a action space empty).
3. $U(C_n) \neq I$ (non-trivial unitary).

In words: there exist circuits that are irreducible by both Phase 1 and Phase-2a.

**Construction.** Take the Thm 7 circuit and replace each $S$ gate with $T$ or another non-commuting gate that breaks the commutation relation. For example, $T$ on the control qubit of CNOT: $[T \otimes I, \text{CNOT}] \neq 0$, so Phase-2a cannot commute past it.

Specifically, let $C_n'$ be the circuit:
- Layer 1: $\text{CNOT}(q_0, q_1), \text{CNOT}(q_2, q_3), \ldots$
- Layer 2: $H(q_0), \ldots, H(q_{n-1})$
- Layer 3: $\text{CNOT}(q_1, q_2), \text{CNOT}(q_3, q_4), \ldots$
- **Layer 3.5**: $T$ on each control qubit (instead of $S$)
- Layer 4: $\text{CNOT}(q_1, q_2), \ldots$
- Layer 5: $H(q_0), \ldots, H(q_{n-1})$
- Layer 6: $\text{CNOT}(q_0, q_1), \ldots$

Since $[T, \text{CNOT}] \neq 0$ (on the control), Phase-2a cannot commute the CNOT past the $T$. Both $\mathcal{S}_1$ and $\mathcal{S}_{1+2a}$ are empty. The unitary is non-trivial ($\neq I$) because the $T$-$T^\dagger$ pairs remain separated by non-commuting CNOTs.

**Contribution grade if written:** ★★☆ — provides the Phase-2a analogue of Thm 1(b) (which shows Phase-1 emptiness). Establishes that Phase-2a emptiness also occurs structurally, not just by accident.

---

## Summary: Upgrade Priority Matrix

| Theorem | Current Grade | Upgrade Path | Upgrade Grade | Effort | Priority |
|---------|--------------|-------------|---------------|--------|----------|
| Thm 1a | ☆☆☆ | A: Non-adjacent action space | ★★☆ | High | 3 |
| Thm 1b | ☆☆☆ | — | — | — | Skip |
| Thm 2c/2d | ★★☆ | A/B: Phase-2 hierarchy | ★★☆ | Medium | 2 |
| Thm 5 | ★☆☆ | A: Multi-parameter concentration | ★★☆ | Medium | 4 |
| Thm 6 | ★★☆ | C: CNOT$+T$ normal form | ★★☆ | Medium | 2 |
| Thm 7 | ★★☆ | A: Tighten to 2/5 | ★☆☆ | Trivial | 1 |
| Thm 8 | ★★☆ | B: Avg/worst separation | ☆☆☆ | Low | 5 |
| Thm 9 | ★★★ | A: Tighten constant | ★★★ | Medium | 1 |
| **NEW (Thm 10)** | — | WCL/LBL gap characterization | ★★☆ | Low | 1 |
| **NEW (Thm 11)** | — | Phase-2a non-universality | ★★☆ | Medium | 2 |

### Top recommended actions

1. **Immediate (low effort, high return):**
   - Thm 7: Update bound from $1/6$ to $2/5$ (already in the proof).
   - Thm 9: Tighten overhead constant from 4.5 to 3 (Direction B analysis).
   - **New Thm 10**: Write up WCL/LBL gap theorem (already implicitly proven by Thm D1).

2. **Medium effort (2-3 days):**
   - Thm 2c/2d: Extend to Phase-2 hierarchy (Phase-2a $\subset$ Phase-2a+INSERTION $\subset$ Phase-2b).
   - Thm 6: Extend to CNOT$+T$ normal form.
   - **New Thm 11**: Construct Phase-2a-irreducible family.

3. **Long-term (1+ weeks):**
   - Thm 1a upgrade Path A: Phase-2 action space size bound for random circuits.
   - Thm 5 Path A: Multi-parameter joint concentration.
   - Direction A/Thm A1 generalization: $S, X, R_z$ bracket families.

### Manuscript restructuring suggestion

If multiple upgrades are completed, the theorem numbering should be reorganized:

- **Primary contributions** (★★★ or can be elevated):
  - Thm 2: Phase-1 reduction ceiling (already core).
  - Thm 7$^+$: Tightened Phase-2a advantage ($2/5$).
  - Thm 9$^+$: Tightened Phase-2b BV bound ($\to 1/3$).
  - New Thm 10: WCL/LBL gap theorem.
  - New Thm 11: Phase-2a non-universality.

- **Supporting** (★★☆ or below):
  - Thm 1a: Adjacent pair density (supporting).
  - Thm 1b: LBL structural result (methodological).
  - Thm 5: High-probability bound (supporting).
  - Thm 6: Clifford ceiling (supporting).
  - Thm 8: Haar-random bound (contextual).
  - Thm 2c/2d: INSERTION lemmas (supporting).
  - Phase-2 hierarchy theorems (supporting).

This would give the manuscript approximately 6 primary theorems (up from 3-4) and 6-7 supporting results, significantly strengthening the theoretical contribution.
