# Theoretical Framework: Structural Ceilings and Context-Dependent Optimization in Quantum Circuit Peephole Rewriting

**Version**: 5.4.0 (INSERTION cascade resolved; Thm 9 BV oracle added; Listing Model Dependency section added)  
**Date**: 2026-06-13  
**Status**: Central hub document. Definitions, theorems, and conjectures with cross-references.  
**Changes from v5.3.0**: Added Thm 2c/2d (INSERTION cascade resolved, bounded version). Added Thm 9 (Phase-2 advantage for BV oracle circuits). Added "Listing Model Dependency" section. Updated Key Empirical Findings table with WCL discovery. Updated honest assessment.

---

## Purpose

This file is the **central hub** of the theoretical framework for the QIP manuscript. It contains:
- All **formal definitions** (D1–D10)
- The **unified conceptual architecture** (Phase 1 / Phase 2, ceilings, action spaces)
- **Cross-references** to theorems, propositions, and conjectures

For detailed statements, see:
- `conjectures.md` — 2 formal conjectures (C1–C2) + 2 motivating open problems (OP1–OP2)
- `lemmas.md` — 3 primary theorems (Thm 1–2, Thm 8ab), 5 supporting results (Thm 3–7, Thm 8c), and 2 propositions (Prop 1–2)
- `thm2_insertion_proof.md` — Thm 2c/2d: INSERTION cascade closure (bounded version)
- `thm7_natural_bv.md` — Thm 9: Phase-2 advantage for Bernstein–Vazirani oracle circuits
- `complexity.md` — Complexity classification table

> **Honest assessment of theoretical contribution (updated 2026-06-13)**. Of the 11 labeled theorems, 3--4 serve as primary theoretical contributions, with the remaining results providing formal backing for the empirical patterns observed:
> - **Thm 2** (Phase-1 Reduction Ceiling): The core structural result. The INSERTION cascade gap is now **resolved** (bounded version) via Thm 2c/2d (`thm2_insertion_proof.md`), which prove that INSERTION cannot achieve net reduction beyond the Phase-2 action space.
> - **Thm 8 Parts a--b** (Haar-random incompressibility): Standard but non-trivial dimension-counting; however, it applies to Haar-random *unitaries*, not the random *gate sequences* used in experiments (see caveat below).
> - **Thm 7** (Explicit Phase-2 advantage): Constructive but uses an artificial circuit family.
> - **Thm 9** (Phase-2 advantage for BV oracle circuits): Proves $\Omega(1)$ Phase-2 advantage for the natural Bernstein--Vazirani oracle family, strengthening Thm 7 from artificial to natural circuits. See `thm7_natural_bv.md`.
>
> The remaining theorems are supporting: Thm 1(a) (birthday-paradox calculation), Thm 1(b) (listing-model structural result, important for methodology), Thm 2c/2d (INSERTION cascade closure), Thm 3 (1-line associativity), Thm 4 (trivially narrow special case), Thm 5 (standard McDiarmid application), Thm 6 (untested on actual circuits), Thm 8 Part c (trivially true for any circuit). They provide formal backing but are not themselves novel contributions.

---

## Notation and Definitions

### D1–D4: Circuit and Optimization Basics

**Definition 1 (Quantum Circuit).** A quantum circuit $C$ is a sequence of quantum gates $C = (g_1, g_2, \ldots, g_m)$ where each $g_i \in \mathcal{G}$ is drawn from a gate set $\mathcal{G}$ acting on $n$ qubits. The **size** of the circuit is $|C| = m$.

**Definition 2 (Unitary Equivalence).** Two circuits $C$ and $C'$ are **unitarily equivalent**, denoted $C \equiv C'$, if they implement the same unitary transformation: $U(C) = U(C')$.

**Definition 3 (Peephole Optimization).** A **peephole optimization** is a local transformation $T$ that replaces a contiguous subsequence (window) $W \subseteq C$ with $W'$ such that $W \equiv W'$ and $|W'| \le |W|$.

**Definition 4 (Phase 1 Optimizer).** A **Phase 1 optimizer** only considers peephole windows of size $|W| = 2$ (adjacent gate pairs) and applies transformations that reduce gate count by cancellation or merging. See Theorem 2 (`lemmas.md`) for the proof that all Phase-1 optimizers share the same action space.

### D5–D7: Phase 2 and Action Spaces

**Definition 5 (Phase 2 Optimizer).** A **Phase 2 optimizer** applies commutation rules to reorder gates, bringing non-adjacent inverse gates into adjacency, thereby enabling Phase 1 reductions that were previously inaccessible. We distinguish two sub-phases:

- **Phase-2a (Commutation Rewriting)**: Uses only disjoint-qubit commutation and known algebraic commutation rules (e.g., Z-family commutation with CNOT) to reorder gates. This is the mechanism implemented in `commutation_rewriter.py`.

- **Phase-2b (Template Matching)**: Uses pre-computed circuit identity templates (e.g., H·CNOT·H → CNOT_reversed) to apply multi-gate rewrite rules. This mechanism is NOT implemented in the current codebase but is referenced in Theorem 9.

Unless otherwise specified, "Phase 2" in the experimental results refers to Phase-2a (commutation rewriting only).

**Definition 6 (Phase 1 Action Space $\mathcal{S}_1(C)$).** The set of all adjacent gate pairs $(g_i, g_{i+1})$ in $C$ such that $g_{i+1} = g_i^{-1}$ and both act on the same qubit(s).

**Definition 7 (Phase 2 Action Space $\mathcal{S}_{1+2}(C)$).** The extended action space including all pairs that can be brought into adjacency via a sequence of commutation rewrites. By construction, $\mathcal{S}_1(C) \subseteq \mathcal{S}_{1+2}(C)$. In the current implementation, $\mathcal{S}_{1+2}(C)$ is computed using Phase-2a (commutation rewriting) only; Phase-2b (template matching) would extend this action space further but is not implemented.

### D8–D10: Ceilings, Gaps, and Fidelity

**Definition 8 (Phase 1 Ceiling $R_1^*(C)$ and Structural Ceiling $L_1(\mathcal{F})$).**
$$R_1^*(C) = \max_{O \in \mathcal{O}_1} \frac{|C| - |O(C)|}{|C|}, \qquad L_1(\mathcal{F}) = \mathbb{E}_{C \sim \mathcal{F}}[R_1^*(C)]$$

**Definition 9 (Optimization Gap $\Gamma(C)$).** The additional reduction enabled by Phase 2:
$$\Gamma(C) = R_{1+2}^*(C) - R_1^*(C)$$
Conjecture C2 (`conjectures.md`) states that $\Gamma(C) = \Omega(1)$ for specific circuit families.

**Definition 10 (Average Gate Fidelity $F_{\text{avg}}$).** The fidelity between two circuits averaged over the Haar measure:
$$F_{\text{avg}}(C, C') = \frac{|\text{Tr}(U^\dagger U')|^2 + d}{d^2 + d}$$
where $d = 2^n$ and $U, U'$ are the unitaries implemented by $C, C'$.

---

## Scope and Nature of the Framework

> **Honest framing note (added 2026-06-11).** This note is included to preemptively address reviewer concerns about the nature and scope of the theoretical framework.

**The structural ceiling framework is primarily a combinatorial and algebraic analysis of gate sequences, not a discovery about quantum physics.** The central objects of study — adjacent inverse pairs, conflict graphs, commutation relations, action spaces — are properties of the *circuit data structure* (a sequence of instructions), not of the underlying quantum dynamics. Specifically:

1. **Combinatorial core.** The Phase-1 ceiling arises because adjacent inverse pairs are rare in random sequences of gates drawn from a finite alphabet. This is a property shared with any random sequence over a finite set with an involution (inverse operation) — it has nothing specifically to do with quantum mechanics. Theorem 1 is, at its heart, a birthday-paradox-style calculation on sequences.

2. **Algebraic structure.** Phase-2 optimization exploits commutation relations between gates, which *are* properties of the operator algebra (e.g., $[H \otimes I, \text{CNOT}] \neq 0$ but $[S \otimes I, \text{CNOT}] = 0$ on the control qubit). This algebraic content is the genuinely quantum-computational aspect of the framework, but it is limited to cataloging which gates commute — a well-known and finite set of relations for any given gate set.

3. **What the framework does NOT claim.** The framework does not discover new quantum phenomena, prove lower bounds on quantum circuit complexity, or establish connections to quantum gravity, holography, or other areas of fundamental physics. The "structural ceiling" is a limit on a specific class of *classical algorithms* (peephole rewriters) applied to a specific *data structure* (gate sequences). It should not be confused with circuit complexity lower bounds (which concern the minimum number of gates needed to represent a unitary, regardless of algorithm).

4. **Critical caveat: Haar-random unitaries vs. random gate sequences.** Theorem 8 proves incompressibility for Haar-random *unitaries*, but all experiments use random *gate sequences* of depth d=poly(n). For n=10, d=50, the circuit has ~500 gates while the Haar-random complexity threshold is ~4^n/n^2 ≈ 10,486 gates. Random gate sequences at these depths produce unitaries far from Haar-random. Therefore, Thm 8's bounds do not directly explain the experimental results — the empirical ~0% reduction on random circuits is explained by the combinatorial sparsity of inverse pairs (Thm 1), not by Haar-random incompressibility. Thm 8 provides a *complementary* information-theoretic argument for the asymptotic regime that is not reached in our experiments. Note: The empirical optimization desert observed in E1-E5 is explained by Theorem 1 (combinatorial sparsity of inverse pairs), not by Theorem 8 (which applies to Haar-random unitaries, a regime not reached in our experiments). Corollary 8.1 provides a complementary information-theoretic perspective for the asymptotic regime.

4. **Appropriate interpretation.** The framework's value lies in its systematic empirical methodology (45,000+ controlled trials) and its unification of several known observations (adjacent cancellation limits, commutation-based advantage, compiler comparisons) into a coherent predictive model. The theorems provide rigorous support for empirical patterns, but the patterns themselves are about *software behavior* (compiler optimization passes), not *physics*.

This framing is not a limitation but a clarification: the framework occupies a well-defined niche at the intersection of quantum software engineering and combinatorial optimization, and its claims should be evaluated accordingly.

---

## Unified Conceptual Architecture

### The Two-Phase Optimization Hierarchy

```
┌───────────────────────────────────────────────────────────────┐
│                     CIRCUIT C (|C| gates)                      │
└───────────────────────────────────────────────────────────────┘
                             │
             ┌───────────────┴───────────────┐
             ▼                               ▼
   ┌─────────────────┐           ┌─────────────────────┐
   │   PHASE 1 ONLY   │           │   PHASE 1 + PHASE 2  │
   │  (Adjacent pairs)│           │  (+ Commutation)      │
   └─────────────────┘           └─────────────────────┘
             │                               │
             ▼                               ▼
   ┌─────────────────┐           ┌─────────────────────┐
   │  Action Space    │           │  Extended Action     │
   │  S₁(C)           │           │  Space S₁₊₂(C)     │
   │                  │           │                      │
   │  • Adjacent      │           │  • Adjacent inverses │
   │    inverses only │           │  • Non-adjacent      │
   │                  │           │    inverses brought  │
   │  Ceiling: R₁*(C) │           │    together by       │
   │                  │           │    commutation       │
   │  Thm 2: if S₁=∅  │           │                      │
   │  then R₁*=0      │           │  Ceiling: R₁₊₂*(C)   │
   └─────────────────┘           │  ≥ R₁*(C) + Γ(C)     │
                                 └─────────────────────┘
```

### Key Empirical Findings

| Finding | Value | Source |
|---------|-------|--------|
| Phase 1 reduction on random circuits | ≈ 0% (all n, d) | E1–E5 |
| Phase 2 additional reduction (random Universal) | ≈ 3.26% | E10 |
| Phase 2 additional reduction (structured brickwork) | 0% | E10 |
| Phase 2 reduction on Oracle (BV) circuits | ~20% | E11 |
| Phase 1 reduction on CNOT chain | 100% | E11 |
| Qiskit O3 mean reduction (real circuits) | 23.42% | E12 |
| Our best optimizer mean (real circuits) | 11.48% | E11 |
| Fidelity preservation | 1.000000 (all trials) | All experiments |
| WCL listing enables Phase-1 reduction | 18% (vs 0% LBL) | E1 under WCL vs LBL; Thm 1(b) |

### The Structural Ceiling Explained

The **structural ceiling** (Conjecture C1) is the fundamental limit on Phase 1 optimization imposed by the circuit's data structure:

1. **Random circuits** have $\mathcal{S}_1(C) \approx \emptyset$ because adjacent gates are drawn independently and the probability of an inverse pair is $\approx 1/(n \cdot |\mathcal{G}|)$ (Theorem 1).

2. **All Phase 1 optimizers** share the same action space $\mathcal{S}_1(C)$ (Theorem 2).

3. **Therefore**, when $\mathcal{S}_1(C) = \emptyset$, all Phase 1 optimizers achieve exactly 0% reduction. This is a **structural property**, not an algorithmic failure.

### The Phase 2 Advantage is Context-Dependent

Phase 2 (commutation rewriting) provides additional reduction only when:
- The circuit contains **commuting gate blocks** that can be reordered
- **Non-adjacent inverse gates** exist that can be brought together
- The circuit has **structural regularity** (repeating patterns)

| Circuit Family | Phase 1 | Phase 2 Additional | Reason |
|---------------|---------|-------------------|--------|
| Random Universal | 0% | ~3% | Rare commutation opportunities |
| Structured brickwork | 0% | 0% | No commuting blocks to exploit |
| QFT / GHZ (already optimal) | 0% | 0% | No redundant gates |
| Oracle (Bernstein–Vazirani) | 0% | ~20% | Commutation exposes redundant H/X gates |
| CNOT chain | 100% | 0% | All cancellations are adjacent |

### Listing Model Dependency

> **Key insight (added 2026-06-13).** The Phase-1 action space $\mathcal{S}_1(C)$ depends critically on the **circuit listing model** — the data-structure ordering of gates. This discovery, formalized in Theorem 1(b), has important implications for both the experimental methodology and the interpretation of results.

**Two listing models.** We distinguish:

1. **Wire-consecutive listing (WCL):** Gates on the same qubit wire are placed consecutively in the listing. This is the natural model for circuit diagrams and some synthesis tools. Under WCL, two successive gates on the same qubit are listing-adjacent, so inverse pairs are directly visible to Phase-1 optimizers.

2. **Layer-by-layer listing (LBL):** The circuit is generated layer by layer, with one gate per qubit per layer. Gates on the same qubit $q$ at layers $L$ and $L+1$ are separated by $n-1$ intervening gates from other qubits. This is the model used by our `UniversalGenerator` (`src/circuits/generator_v2.py`).

**Theorem 1(b) (formal statement).** Under LBL with $n \ge 2$, the Phase-1 action space is structurally empty: $\mathcal{S}_1(C) = \emptyset$ for every circuit $C$. Consequently, $R_1(C) = 0$ for every Phase-1 optimizer, regardless of the circuit's gate content.

**Proof sketch.** Under LBL, the gate on qubit $q$ at layer $L$ is at listing index $L \cdot n + q$. The next gate on the same qubit is at index $(L+1) \cdot n + q$, a gap of $n \ge 2$. Since Phase-1 requires listing adjacency (gap = 1) on the same qubit(s), no Phase-1 action is possible.

**WCL discovery and empirical implications.** When circuits are represented in WCL instead of LBL, the Phase-1 action space becomes non-empty for circuits that contain wire-consecutive inverse pairs. Empirically, WCL listing enables approximately 18% Phase-1 reduction on the same random circuit ensemble where LBL yields exactly 0%. This 18% figure is consistent with the density bound from Theorem 1(a): $\mathbb{E}[|\mathcal{A}_{\text{adj}}(C)|] = n(d-1) \cdot p_{\text{cancel}}(n, \rho)$, which for typical parameters yields a small but non-zero number of adjacent inverse pairs.

**Interpretation.** The zero Phase-1 reduction observed in experiments E1--E5 is **not** a fundamental property of the random circuits themselves, but a consequence of the LBL listing model used by the generator. The circuits contain wire-level inverse pairs; LBL merely hides them from listing-adjacent Phase-1 detection. Phase-2 commutation rewriters (which operate on the circuit graph rather than the listing) are unaffected by this listing-model dependency, since they reason about wire-level adjacency rather than listing adjacency.

**Recommendation.** Future experiments should either (a) adopt WCL as the default listing model for Phase-1 evaluation, or (b) include a wire-traversal pre-processing step that identifies wire-consecutive (not listing-adjacent) inverse pairs before Phase-1 optimization. This ensures that Phase-1 results reflect the circuit's intrinsic structure rather than an artifact of the data-structure ordering.

---

## Cross-Reference Map

### Conjectures (detailed in `conjectures.md`)

| ID | Statement | Evidence | File |
|----|-----------|----------|------|
| OP1 | CODP is QMA-hard (motivating open problem) | Weak — reduction sketch | `conjectures.md` §OP1 |
| OP2 | No PTAS for CODP (motivating open problem) | Weak — MIS gap issues | `conjectures.md` §OP2 |
| **C1** | **Phase 1 ceiling is structural** | **Strong — Thm 2 + empirical** | `conjectures.md` §C1 |
| **C2** | **Phase 2 is context-dependent super-constant** | **Strong — E10/E11** | `conjectures.md` §C2 |

### Theorems and Propositions (detailed in `lemmas.md`)

| ID | Statement | Status | File |
|----|-----------|--------|------|
| Thm 1(a) | Adjacent inverse pair density bound under WCL (expectation) | [PROVEN — elementary] | `lemmas.md` §Thm1 |
| Thm 1(b) | LBL listing model yields $\mathcal{S}_1(C) = \emptyset$ for $n \ge 2$ | [PROVEN — structural] | `lemmas.md` §Thm1 |
| Thm 2 | Phase-1 action-space identity / reduction ceiling | [PROVEN — INSERTION cascade resolved (bounded version)] | `lemmas.md` §Thm2 |
| Thm 2c | Bounded INSERTION cascade lemma ($R_{\text{removal}} \le 2k$) | [PROVEN — insertion-debt invariant] | `thm2_insertion_proof.md` |
| Thm 2d | INSERTION commutation cascade bound ($\le$ Phase-2 action space) | [PROVEN — wire-order invariant] | `thm2_insertion_proof.md` |
| Lemma 3 | Commutation preserves equivalence | [PROVEN — 1-line, supporting lemma] | `lemmas.md` §Lemma3 |
| Lemma 4 | Greedy optimality for non-conflicting pairs | [PROVEN — narrow scope, supporting lemma] | `lemmas.md` §Lemma4 |
| Thm 5 | High-probability bound on inverse pairs (McDiarmid) | [PROVEN — standard] | `lemmas.md` §Thm5 |
| Thm 6 | Phase-1 ceiling exact for Clifford in canonical form | [PROVEN — untested] | `lemmas.md` §Thm6 |
| Thm 7 | Explicit circuit family with $\Omega(1)$ Phase-2 advantage | [PROVEN — artificial] | `lemmas.md` §Thm7 |
| Thm 8 | Haar-random incompressibility + bounded-window limit | [PROVEN — Parts a-b substantive; Part c trivial] | `lemmas.md` §Thm8 |
| Thm 9 | Phase-2b/template-assisted advantage $\ge n/(4.5n+4)$ for BV oracle circuits | [PROVEN — natural circuit family; pure Phase-2a bound open] | `thm7_natural_bv.md` |
| Prop 1 | Conflict resolution is polynomial-time (maximum matching) | [CORRECTED] | `lemmas.md` §Prop1 |
| Obs 1 | Greedy matches stochastic optimizers | [EMPIRICAL] | `lemmas.md` §Obs1 |

### Complexity Results (detailed in `complexity.md`)

| Problem | Restriction | Complexity | Status |
|---------|------------|------------|--------|
| CIT | General circuits | QMA-complete | [PROVEN] |
| CIT | Clifford circuits | P | [PROVEN] |
| CODP | General circuits | QMA-hard? | [OPEN — OP1] |
| P1OPT (conflict resolution) | General circuits | P (maximum matching) | [Prop 1, corrected] |
| P1OPT (greedy scan) | General circuits | P | [PROVEN] |

---

## References

1. Janzing, D., Wocjan, P., & Beth, T. (2003). "Non-identity-check is QMA-complete." *Int. J. Quantum Information*, 1(4), 507-518.
2. Kempe, J., Kitaev, A., & Regev, O. (2006). "The Complexity of the Local Hamiltonian Problem." *SIAM J. Computing*, 35(5), 1070-1097.
3. Gottesman, D. (1997). "Stabilizer codes and quantum error correction." *Ph.D. thesis, Caltech*.
4. Aaronson, S., & Gottesman, D. (2004). "Improved simulation of stabilizer circuits." *Physical Review A*, 70(5), 052328.

---

**Document version**: 5.4.0  **Last updated**: 2026-06-13  
**Author**: Q-research Theoretical Framework Team  
**Companion documents**: `conjectures.md` (C1–C2, OP1–OP2), `lemmas.md` (Thm 1–9, Thm 2c/2d, Prop 1, Obs 1), `thm2_insertion_proof.md` (INSERTION cascade proofs), `thm7_natural_bv.md` (BV oracle Phase-2 proof), `complexity.md`
