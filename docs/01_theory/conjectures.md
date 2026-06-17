# Conjectures and Open Problems

> **Document Status**: Living document — formal conjectures and open problems for the QIP manuscript.  
> **Version**: 3.1  
> **Date**: 2026-06-11  
> **Scope**: Two formal conjectures (C1–C2) with strong empirical support, and two motivating open problems (OP1–OP2) from complexity theory.  
> **Changes from v3.0**: Corrected OP2 to align with Proposition 1 correction (maximum matching, not MIS). Updated C1 remaining gap to reference Theorem 2 v3.3 resolution. Removed stale C2 remaining gap that contradicts Theorem 7.  
> **Dependencies**: Base definitions (D1–D10) in `framework.md`.

---

## Preliminaries

For base notation ($n$, $d$, $\mathcal{G}$, $C(n,d,\rho)$, $|C|$, $F_{\text{avg}}$, etc.) and all formal definitions D1–D10 (quantum circuit, unitary equivalence, peephole optimization, Phase 1/2, ceilings, action spaces), see **`framework.md`**.

This document defines two formal decision problems:

**Definition A1 (Circuit Optimization Decision Problem, CODP).**  
> **Input**: A quantum circuit $C$, a target reduction ratio $r \in (0, 1]$, and a tolerance $\epsilon > 0$.  
> **Question**: Does there exist a circuit $C'$ such that $C \equiv_\epsilon C'$ and $|C'| \le (1 - r) |C|$?

**Definition A2 (Circuit Identity Testing, CIT).**  
> **Input**: Two quantum circuits $C$ and $C'$, and a tolerance $\epsilon > 0$.  
> **Question**: Does $C \equiv_\epsilon C'$ hold?

Unitary equivalence up to tolerance $\epsilon$: $C \equiv_\epsilon C'$ if $\| U - U' \|_\diamond \le \epsilon$, where $\| \cdot \|_\diamond$ is the diamond norm.

---

## Motivating Open Problems

These open problems motivate the study but are not claimed as results of this paper. They are included to contextualize the empirical findings within the broader complexity-theoretic landscape.

### OP1: Is Peephole Optimization QMA-hard?

**Question.** Is the Circuit Optimization Decision Problem (CODP) QMA-hard?

**Motivation.** Circuit Identity Testing (CIT) is QMA-complete [Janzing, Wocjan & Beth, 2003]. Since CIT is the special case of CODP with $r = 0$, one might expect CODP to be at least QMA-hard. However, the standard path — Kitaev's circuit-to-Hamiltonian construction [Kitaev, 1997] — yields a specific circuit family (history-state circuits), and showing that bounded-window peephole rewrites can distinguish YES from NO instances requires analyzing the rewrite-rule closure of these circuits, which is open.

**Current status.** The empirical observation that all Phase-1 optimizers achieve ~0% reduction on random circuits is *consistent with* QMA-hardness but does not constitute proof. A zero-mean reduction could also arise from a flat but classically tractable landscape.

**Sub-problems:**
- OP1.1: Complete the reduction from $k$-Local Hamiltonian to CODP with explicit circuit construction and gap preservation.
- OP1.2: Determine whether CODP remains hard when restricted to Clifford circuits (CIT is in P for Clifford circuits via Gottesman-Knill, so hardness likely fails here).
- OP1.3: Determine the parameterized complexity: is CODP hard for circuits of treewidth $t = O(\log n)$?

### OP2: Inapproximability of CODP

**Question.** Does CODP admit a polynomial-time constant-factor approximation?

**Motivation.** The conflict-resolution subproblem (selecting maximum non-overlapping cancelable pairs) was previously thought to reduce to Maximum Independent Set on the line graph of the circuit [Garey & Johnson, 1979]. However, as corrected in Proposition 1 (lemmas.md, 2026-06-11), the correct graph-theoretic formulation is **maximum matching** on the conflict graph (which is a line graph of a subgraph of a path), solvable in polynomial time via Edmonds' blossom algorithm [Edmonds, 1965]. This correction weakens the inapproximability motivation: since the base problem is in P, the hardness of CODP must arise from other sources (e.g., the search over rewrite sequences, not the conflict resolution itself). Circuit line graphs have bounded clique size (maximum fan-in = 2), and the polynomial-time solvability of the conflict-resolution subproblem suggests that CODP's hardness (if any) lies in the *sequential* nature of rewrites rather than the *combinatorial* selection step.

**Sub-problems:**
- OP2.1: Since the conflict-resolution subproblem is in P (Proposition 1, corrected), identify the true source of CODP hardness — is it the sequential rewrite search, the fidelity constraint, or the window-boundedness?
- OP2.2: Determine whether the dynamic commutation graph (where edges change under commutation moves) admits a PTAS for the *sequential* optimization problem.

---

## Formal Conjectures

These are the paper's central formal claims, supported by strong empirical evidence and partial theoretical arguments.

### Conjecture 1: The Phase 1 Ceiling is Structural

**Statement.** For any circuit family $\mathcal{F}$ in which no adjacent inverse gate pairs exist in the initial data structure, *every* Phase-1-only optimizer (greedy, simulated annealing, genetic algorithm, random local search) achieves exactly $0\%$ gate reduction. This ceiling is a property of the circuit data structure, not of the optimization algorithm.

**Status**: [CONJECTURE → PARTIALLY PROVEN] — the statement follows from Theorem 2 (action-space identity) for deterministic optimizers; the conjecture concerns the universality claim for stochastic optimizers. Theorem 5 strengthens the empirical bound to a high-probability guarantee. Theorem 6 proves the conjecture exactly for Clifford circuits in canonical form. Theorem 8 proves the bounded-window reduction limit for Haar-random circuits.

**Evidence:**

1. **Action-space identity** (Theorem 2 in `lemmas.md`). All Phase-1 optimizers operate on the same action space $\mathcal{S}_1(C)$. If $\mathcal{S}_1(C) = \emptyset$, no Phase-1 move reduces gate count. Note: Theorem 2 has a known gap in the INSERTION cascade argument (see `lemmas.md` Remark).

2. **Empirical validation** (E1–E5, 45,500 trials). Across Universal, Clifford, and Structured circuit families, all four Phase-1 optimizers achieved $\le 0.05\%$ mean reduction. The ceiling is reproducible and algorithm-independent. Note: Empirical Observation 1 (formerly Prop 2) formalizes this as $\mathbb{E}[R_{\text{stoch}}(C)] \le R_{\text{greedy}}(C) + O(1/|C|)$.

3. **Theoretical argument.** A Phase-1 optimizer can cancel adjacent inverses (REMOVAL), swap disjoint-qubit gates (SWAP), or commute gates (COMMUTATION). SWAP and COMMUTATION preserve gate count. Without commutation-based reordering across non-commuting blocks, the set of cancelable pairs is invariant under Phase-1 moves.

**Remaining gap.** The formal invariant argument must show that SWAP and COMMUTATION moves within Phase-1 scope cannot *create* new adjacent inverse pairs. Theorem 2 (v3.3, renamed "Phase-1 Reduction Ceiling") addresses this: it proves that SWAP can create listing-adjacent pairs but only reveals pre-existing wire-level structure (no net reduction), and INSERTION creates new S₁ elements but cannot achieve net reduction (insertion adds 2 gates, cancellation removes 2 gates). The remaining open question is whether this invariant extends to Phase-1 scope when commutation is restricted (no reordering across non-commuting blocks) — which is precisely why Phase 2 exists.

**Open problems:**
- C1.OP1: Formalize the invariant characterizing exactly which circuit families have empty Phase-1 action spaces.
- C1.OP2: Quantify $\Pr[\mathcal{S}_1(C) \neq \emptyset]$ as a function of $(n, d, \mathcal{G})$ for random circuit ensembles.

### Conjecture 2: Phase 2 Provides Context-Dependent Super-Constant Improvement

**Statement.** There exist circuit families $\mathcal{F}$ and gate sets $\mathcal{G}$ for which Phase-1 optimization achieves $O(1/d)$ reduction (or $0\%$), while Phase-1+2 optimization achieves $\Omega(1)$ reduction. The improvement $\Gamma(C) = R_{1+2}(C) - R_1(C)$ is context-dependent: it is significant for some families (e.g., oracle circuits) and zero for others (e.g., structured brickwork, QFT, GHZ).

**Status**: [CONJECTURE → PROVEN FOR EXPLICIT CONSTRUCTION] — Theorem 7 constructs an explicit circuit family demonstrating $\Omega(1)$ Phase-2 advantage, establishing Conjecture C2 constructively. The broader question of characterizing *all* families with super-constant improvement remains open (see C2.OP1–OP3).

**Evidence:**

1. **Random Universal circuits (E10).** Phase 1 achieves $\approx 0\%$; Phase 1+2 achieves $\approx 3.26\%$ additional reduction (Cohen's $d = 1.32$, large effect).

2. **Oracle / Bernstein–Vazirani circuits (E11).** Phase 1 achieves $0\%$; Phase 1+2 achieves $\sim 20\%$ reduction via commutation of redundant H/X gates. The Phase 2 advantage is directly attributable to the algebraic structure of the oracle.

3. **CNOT-chain validation circuits (E11).** Phase 1 alone achieves $100\%$ reduction, confirming that the Phase 2 advantage is circuit-family dependent rather than universal.

4. **Mechanism.** Phase 2 exploits commutation relations $[U, V] = 0$ to reorder gates, bringing non-adjacent inverses into adjacency. For circuits with repeating structural patterns, commutation can slide gates across $O(d)$ positions, creating cancellations invisible to Phase 1.

**Remaining gap.** Theorem 7 (lemmas.md) constructs an explicit circuit family demonstrating $\Omega(1)$ Phase-2 advantage, partially closing this gap. The remaining open question is characterizing *all* circuit families with super-constant Phase-2 improvement: specifically, what algebraic or structural properties of a circuit family $\mathcal{F}$ determine whether $\Gamma(C)$ is $O(1/d)$ or $\Omega(1)$?

**Open problems:**
- C2.OP1: Construct an explicit circuit family with proven super-constant Phase-2 improvement.
- C2.OP2: Determine $\max_C \Gamma(C) / R_1(C)$ as a function of $(n, d, \mathcal{G})$.
- C2.OP3: Characterize the gate-set conditions under which Phase 2 is necessary.

---

## Summary Table

| ID | Type | Statement | Evidence | Key Open Problem |
|----|------|-----------|----------|-----------------|
| OP1 | Open Problem | CODP is QMA-hard | Weak — reduction sketch incomplete | Complete the Kitaev reduction |
| OP2 | Open Problem | No PTAS for CODP | Updated — conflict resolution is in P (Prop 1); hardness source unclear | Identify true hardness source |
| **C1** | **Conjecture** | **Phase 1 ceiling is structural** | **Strong — Thm 2 + Thm 5 + Thm 6 (Clifford) + Thm 8 (Haar) + 45,500 trials** | **Formalize invariant for general circuit families** |
| **C2** | **Conjecture** | **Phase 2 is context-dependent super-constant** | **Proven — Thm 7 (explicit construction) + E10/E11 empirical** | **Characterize all families with super-constant $\Gamma$** |

---

## References

1. Kempe, J., Kitaev, A. \& Regev, O. (2006). The Complexity of the Local Hamiltonian Problem. *SIAM J. Comput.* **35**, 1070–1097.
2. Janzing, D., Wocjan, P. \& Beth, T. (2003). Non-identity-check is QMA-complete. *Int. J. Quantum Inform.* **1**, 507–518.
3. Kitaev, A. Yu. (1997). Quantum computations: algorithms and error correction. *Russ. Math. Surv.* **52**, 1191–1249.
4. Garey, M. R. \& Johnson, D. S. (1979). *Computers and Intractability*. W. H. Freeman.
5. Berman, P. \& Karpinski, M. (1999). On some tighter inapproximability results. *LNCS* **1644**, 200–209.

---

*Document version: 3.1*  
*Last updated: 2026-06-11*  
*Author: Q-research Theoretical Framework Team*
