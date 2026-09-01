# Theoretical Framework: Structural Ceilings and Context-Dependent Optimization in Quantum Circuit Peephole Rewriting

**Version**: 5.4.2 (Metric-audit correction)
**Date**: 2026-08-11
**Status**: Conceptual framework only. Claim admissibility is controlled by
`prepaper_theory_gate_2026-08-10.md`; detailed proof status is controlled by
`formal_results.md`. Conflicts must be resolved in favour of the theory gate.

---

## Purpose

This document is the **central hub** of the theoretical framework for the QIP manuscript. It contains:

- All **formal definitions** (D1–D10)
- The **unified conceptual architecture** (Phase 1 / Phase 2, ceilings, action spaces)
- The **complexity classification** (known results, conjectured results, open problems)
- **Cross-references** to theorems, propositions, conjectures, and appendices

For detailed formal results, see the companion document `formal_results.md` which contains all theorems, lemmas, propositions, conjectures, and proof appendices.

> **Notation**: Phase-2a refers to commutation-based rewriting (implemented in `commutation_rewriter.py`). Phase-2b refers to template-assisted rewriting (implemented in `template_matcher.py` and evaluated at full scale in the v2 validation dataset). When we write "Phase-2" without a suffix, we refer to Phase-2a; Phase-2b results are always labeled explicitly.

> **Audit correction (2026-08-09).** The earlier contribution count was overstated:
> - **Thm 2(a)** proves only the Greedy no-action predicate.  The general stochastic ceiling is open; former Thm 2d uses an invalid per-wire factorization for multi-qubit gates.
> - **Thm 5** has an incomplete concentration proof, the former general **Thm 6** has a concrete generator counterexample, and **Thm 8** is withdrawn because its premises are incompatible.
> - **Thm 7** (Explicit Phase-2a advantage): Constructive but uses an artificial circuit family.
> - **Thm 9** (Phase-2b advantage for BV oracle circuits): Proves $\Omega(1)$ Phase-2b advantage for the natural Bernstein--Vazirani oracle family, strengthening Thm 7 from artificial to natural circuits.
>
> At present, the defensible theory consists of elementary/restricted structural results plus the explicit Thm 7/9 constructions.  Empirical regularities must not be promoted to universal algorithm-independent laws.

---

## Notation

Throughout this document and its companions, we use the following standard notation:

- $n$: number of qubits
- $d$: circuit depth
- $\mathcal{G}$: gate set
- $C(n,d,\rho)$: random circuit on $n$ qubits, depth $d$, two-qubit gate density $\rho$
- $|C|$: circuit size (number of gates)
- $F_{\text{avg}}$: average gate fidelity
- $L(C)$: line graph of circuit $C$ (vertices = gates, edges = adjacency in the circuit list)
- $\mathcal{A}_{\text{adj}}(C)$: the set of adjacent inverse gate pairs in $C$
- $\mathcal{A}_{\text{comm}}(C)$: the set of gate pairs that can be brought into adjacency via commutation rewriting
- $R_1(C)$: reduction fraction achieved by Phase-1-only optimization
- $R_{1+2}(C)$: reduction fraction achieved by Phase-1+2 optimization
- $\mathbb{E}_{C \sim \mathcal{E}}[\cdot]$: expectation over circuit ensemble $\mathcal{E}$

---

## Definitions

### D1–D4: Circuit and Optimization Basics

**Definition 1 (Project circuit scope).** A circuit $C$ is a finite sequence of
unitary gates $C=(g_1,\ldots,g_m)$ from a stated gate set $\mathcal G$ acting on
a fixed register of $n$ qubits. The size is $|C|=m$. Unless a result explicitly
says otherwise, this framework excludes measurement, reset, classical control,
dynamic branches, changing ancilla allocation, and unbound symbolic parameters.
Claims about those models require a separate semantic and cost contract.

**Definition 2 (Project unitary equivalence).** Two in-scope circuits are
equivalent, denoted $C\equiv C'$, when their unitaries agree up to a global
phase. Operationally, the frozen numerical contract uses average gate fidelity
and declares exact equivalence only when its stated tolerance is met. Sampled
checks are probabilistic evidence, not symbolic parameterized equivalence.

**Definition 3 (Peephole Optimization).** A **peephole optimization** is a local transformation $T$ that replaces a contiguous subsequence (window) $W \subseteq C$ with $W'$ such that $W \equiv W'$ and $|W'| \le |W|$.

**Definition 4 (Adjacent Greedy subsystem).** The implemented adjacent Greedy
subsystem considers size-two listing-adjacent pairs and applies its stated
cancellation/merge predicates. Its initial action set is Definition 6. SA, RLS,
and GA additionally traverse neutral or expanding moves and therefore do not
share this action space; the former algorithm-independence statement is refuted.

### D5–D7: Phase 2 and Action Spaces

**Definition 5 (Phase 2 Optimizer).** A **Phase 2 optimizer** applies commutation rules to reorder gates, bringing non-adjacent inverse gates into adjacency, thereby enabling Phase 1 reductions that were previously inaccessible. We distinguish two sub-phases:

- **Phase-2a (Commutation Rewriting)**: Uses only disjoint-qubit commutation and known algebraic commutation rules (e.g., Z-family commutation with CNOT) to reorder gates. This is the mechanism implemented in `commutation_rewriter.py`.

- **Phase-2b (Template Matching)**: Uses pre-computed circuit identity templates (e.g., H-CNOT-H $\to$ CNOT_reversed) to apply multi-gate rewrite rules. The current implementation is `template_matcher.py`; its full-scale v2 validation is recorded in `data/v8/phase2b_full/`.

Unless otherwise specified, "Phase 2" in the experimental results refers to Phase-2a (commutation rewriting only).

**Definition 6 (Phase 1 Action Space $\mathcal{S}_1(C)$).** The set of all adjacent gate pairs $(g_i, g_{i+1})$ in $C$ such that $g_{i+1} = g_i^{-1}$ and both act on the same qubit(s).

**Definition 7 (Phase 2 Action Space $\mathcal{S}_{1+2}(C)$).** The extended action space including pairs exposed by commutation rewrites and patterns transformed by the implemented template library. By construction, $\mathcal{S}_1(C) \subseteq \mathcal{S}_{1+2}(C)$. Phase-2a and Phase-2b are distinct evidence layers; the v8 full-scale dataset evaluates the implemented Phase-2b pipeline, not an unrestricted template universe.

### D8–D10: Ceilings, Gaps, and Fidelity

**Definition 8 (Phase 1 Ceiling $R_1^*(C)$ and Structural Ceiling $L_1(\mathcal{F})$).**
$$R_1^*(C) = \max_{O \in \mathcal{O}_1} \frac{|C| - |O(C)|}{|C|}, \qquad L_1(\mathcal{F}) = \mathbb{E}_{C \sim \mathcal{F}}[R_1^*(C)]$$

**Definition 9 (Optimization Gap $\Gamma(C)$).** The additional reduction enabled by Phase-2 (a+b):
$$\Gamma(C) = R_{1+2}^*(C) - R_1^*(C)$$
Conjecture C2 states that $\Gamma(C) = \Omega(1)$ for specific circuit families.

**Definition 10 (Average Gate Fidelity $F_{\text{avg}}$).** The fidelity between two circuits averaged over the Haar measure:
$$F_{\text{avg}}(C, C') = \frac{|\text{Tr}(U^\dagger U')|^2 + d}{d^2 + d}$$
where $d = 2^n$ and $U, U'$ are the unitaries implemented by $C, C'$.

### D11: Executable Equivalence-Certificate Contract

**Definition 11 (Equivalence certificate).** An executable equivalence check
returns `(method, status, scope, threshold, fidelity, uncertainty, evidence)`,
implemented by `src/equivalence.py`. Its current scope is fixed-width, fully
bound, unitary circuits compared up to global phase. Evidence classes are kept
distinct:

1. `exact_structural`: identical supported Qiskit circuit syntax;
2. `exact_clifford`: tableau equality beyond the dense-unitary budget;
3. `numerical_unitary`: dense-operator average gate fidelity within that budget;
4. `sampled_global_haar`: a Monte Carlo estimate with sample count and standard
   error, labelled `estimated_*`, never symbolic or exact;
5. `heuristic`: structural similarity only, never accepted as semantic evidence;
6. `unavailable`: no supported certificate, which fails closed.

Free parameters require a symbolic proof system or a predeclared,
probability-qualified parameter-domain protocol. Finite bindings are instances,
not a proof of parameterized equivalence. Measurement, reset, initialization,
classical bits/conditions, and dynamic control flow require observational or
channel semantics that are not implemented here; they return `unavailable`
even for identical program text. The contract therefore makes no claim of
symbolic completeness, partial-initialization equivalence, or support for
ancilla allocation/discard.

### D12: Representation-conditioned rewrite exposure

The v12 extension makes the representation dependence of local rewrite
opportunities explicit. For a fixed listed circuit and declared dependence
model, the rewrite-exposure certificate records the current exposed weight, a
constructive lower bound, a matching upper bound, and the exact optimum when
the bounded solver is complete. The certificate is about the finite action
space exposed by that representation; it is not a fidelity certificate and it
does not imply an unrestricted optimizer bound.

The current implementation is limited to the `pair_v1` rule library and the
`wire_order_v1` / `conservative_commutation_v1` dependence models. Unsupported
gate semantics, dynamic control, non-unitary operations, unbound parameters, or
budget exhaustion are represented fail-closed. E38 validates the contract on
its finite exhaustive panel; E39 is development-only; E40 has no eligible
efficacy population; and E41 reports scale/resource behavior only. Formal
definitions and falsifiers are maintained in `v12_rewrite_exposure_theory.md`.

### Additional Definitions: Formal Decision Problems

**Definition A1 (Circuit Optimization Decision Problem, CODP).**
> **Input**: A quantum circuit $C$, a target reduction ratio $r \in (0, 1]$, and a tolerance $\epsilon > 0$.
> **Question**: Does there exist a circuit $C'$ such that $C \equiv_\epsilon C'$ and $|C'| \le (1 - r) |C|$?

**Definition A2 (Circuit Identity Testing, CIT).**
> **Input**: Two quantum circuits $C$ and $C'$, and a tolerance $\epsilon > 0$.
> **Question**: Does $C \equiv_\epsilon C'$ hold?

Channel equivalence up to tolerance $\epsilon$: $C \equiv_\epsilon C'$ if
$\|\mathcal{U}-\mathcal{U}'\|_\diamond \le \epsilon$, where
$\mathcal{U}(\rho)=U\rho U^\dagger$. The diamond norm applies to channels,
not directly to the matrix difference $U-U'$, and therefore ignores global
phase. A complexity classification additionally requires an explicit
inverse-polynomial YES/NO promise gap; Definitions A1--A2 alone are problem
schemas, not complete promise-problem specifications.

---

## Scope and Nature of the Framework

> **Honest framing note (added 2026-06-11).** This note is included to preemptively address reviewer concerns about the nature and scope of the theoretical framework.

**The structural ceiling framework is primarily a combinatorial and algebraic analysis of gate sequences, not a discovery about quantum physics.** The central objects of study -- adjacent inverse pairs, conflict graphs, commutation relations, action spaces -- are properties of the *circuit data structure* (a sequence of instructions), not of the underlying quantum dynamics. Specifically:

1. **Combinatorial core.** The Phase-1 ceiling arises because adjacent inverse pairs are rare in random sequences of gates drawn from a finite alphabet. This is a property shared with any random sequence over a finite set with an involution (inverse operation) -- it has nothing specifically to do with quantum mechanics. Theorem 1 is, at its heart, a birthday-paradox-style calculation on sequences.

2. **Algebraic structure.** Phase-2a optimization exploits commutation relations between gates, which *are* properties of the operator algebra (e.g., $[H \otimes I, \text{CNOT}] \neq 0$ but $[S \otimes I, \text{CNOT}] = 0$ on the control qubit). This algebraic content is the genuinely quantum-computational aspect of the framework, but it is limited to cataloging which gates commute -- a well-known and finite set of relations for any given gate set.

3. **What the framework does NOT claim.** The framework does not discover new quantum phenomena, prove lower bounds on quantum circuit complexity, or establish connections to quantum gravity, holography, or other areas of fundamental physics. The "structural ceiling" is a limit on a specific class of *classical algorithms* (peephole rewriters) applied to a specific *data structure* (gate sequences). It should not be confused with circuit complexity lower bounds (which concern the minimum number of gates needed to represent a unitary, regardless of algorithm).

4. **Haar argument withdrawn.** Former Theorem 8 assumed both an exact polynomial-size implementation and, with high probability, complexity larger than that implementation. Its premises are incompatible, so it supplies no incompressibility result. The E1--E5 behavior is instead a generator- and Greedy-predicate observation about sparse listing-adjacent inverse pairs.

5. **Appropriate interpretation.** The framework's value lies in its systematic empirical methodology (96,205 active-canonical rows across 35 datasets; two additional manifest entries are superseded provenance) and its unification of several known observations into a representation-conditioned software model. Row count is not a unique-benchmark count or a priority proof.

This framing is not a limitation but a clarification: the framework occupies a well-defined niche at the intersection of quantum software engineering and combinatorial optimization, and its claims should be evaluated accordingly.

---

## Unified Conceptual Architecture

### The Two-Phase Optimization Hierarchy

```
                              ┌───────────────────────────────────────────────┐
                              │               CIRCUIT C (|C| gates)           │
                              └───────────────────────────────────────────────┘
                                                    │
                                    ┌───────────────┴───────────────┐
                                    ▼                               ▼
                          ┌─────────────────┐           ┌──────────────────────────┐
                          │   PHASE 1 ONLY   │           │   PHASE 1 + PHASE 2      │
                          │  (Adjacent pairs)│           │  (+ Commutation)          │
                          └─────────────────┘           └──────────────────────────┘
                                    │                               │
                                    ▼                               ▼
                          ┌─────────────────┐           ┌──────────────────────────┐
                          │  Action Space    │           │  Extended Action          │
                          │  S₁(C)           │           │  Space S₁₊₂(C)          │
                          │                  │           │                           │
                          │  • Adjacent      │           │  • Adjacent inverses      │
                          │    inverses only │           │  • Non-adjacent            │
                          │                  │           │    inverses brought        │
                          │  Ceiling: R₁*(C) │           │    together by             │
                          │                  │           │    commutation             │
                          │  Thm 2: if S₁=∅  │           │                           │
                          │  then R₁*=0      │           │  Ceiling: R₁₊₂*(C)        │
                          └─────────────────┘           │  ≥ R₁*(C) + Γ(C)          │
                                                        └──────────────────────────┘
```

### Key Empirical Findings

| Finding | Value | Source |
|---------|-------|--------|
| Phase 1 reduction on random circuits | $\approx$ 0% (all n, d) | E1--E5 |
| Phase-2a additional reduction (random Universal) | $\approx$ 3.26% | E10 |
| Phase-2a additional reduction (structured brickwork) | 0% | E10 |
| Phase-2a reduction on Oracle (BV) circuits | ~20% | E11 |
| Phase 1 reduction on CNOT chain | 100% | E11 |
| Qiskit O3 mean reduction (real circuits) | 23.42% | E12 |
| Our best optimizer mean (real circuits) | 11.48% | E11 |
| Fidelity preservation | 1.000000 (all trials) | All experiments |
| WCL listing enables Phase-1 reduction | 7.8% (vs 0% LBL) | E1 under WCL vs LBL; E19; Thm 1(b) |

### The Structural Ceiling Explained

The **structural ceiling** (Conjecture C1) is the fundamental limit on Phase 1 optimization imposed by the circuit's data structure:

1. **Random circuits** have $\mathcal{S}_1(C) \approx \emptyset$ because adjacent gates are drawn independently and the probability of an inverse pair is $\approx 1/(n \cdot |\mathcal{G}|)$ (Theorem 1).

2. **All Phase 1 optimizers** share the same action space $\mathcal{S}_1(C)$ (Theorem 2).

3. **Therefore**, when $\mathcal{S}_1(C) = \emptyset$, all Phase 1 optimizers achieve exactly 0% reduction. This is a **structural property**, not an algorithmic failure.

### The Phase-2 (a+b) Advantage is Context-Dependent

Phase-2a (commutation rewriting) provides additional reduction only when:
- The circuit contains **commuting gate blocks** that can be reordered
- **Non-adjacent inverse gates** exist that can be brought together
- The circuit has **structural regularity** (repeating patterns)

| Circuit Family | Phase 1 | Phase-2a Additional | Reason |
|---------------|---------|-------------------|--------|
| Random Universal | 0% | ~3% | Rare commutation opportunities |
| Structured brickwork | 0% | 0% | No commuting blocks to exploit |
| QFT / GHZ (already optimal) | 0% | 0% | No redundant gates |
| Oracle (Bernstein--Vazirani) | 0% | ~20% | Commutation exposes redundant H/X gates |
| CNOT chain | 100% | 0% | All cancellations are adjacent |

### Listing Model Dependency

> **Key insight (added 2026-06-13).** The Phase-1 action space $\mathcal{S}_1(C)$ depends critically on the **circuit listing model** -- the data-structure ordering of gates. This discovery, formalized in Theorem 1(b), has important implications for both the experimental methodology and the interpretation of results.

**Two listing models.** We distinguish:

1. **Wire-consecutive listing (WCL):** Gates on the same qubit wire are placed consecutively in the listing. This is the natural model for circuit diagrams and some synthesis tools. Under WCL, two successive gates on the same qubit are listing-adjacent, so inverse pairs are directly visible to Phase-1 optimizers.

2. **Layer-by-layer listing (LBL):** The circuit is generated layer by layer, with one gate per qubit per layer. Gates on the same qubit $q$ at layers $L$ and $L+1$ are separated by $n-1$ intervening gates from other qubits. This is the model used by our `UniversalGenerator` (`src/circuits/generator_v2.py`).

**Observation 1(b) (formal statement).** Under the stated LBL generator with
$n\ge2$, the implemented adjacent Greedy action set is empty. Consequently
Greedy returns zero reduction. This does not imply zero reduction for an
optimizer whose move closure includes SWAP, COMMUTATION, or INSERTION; the
three-gate counterexample in `tests/test_stochastic_incumbent.py` refutes that
generalization.

**Proof sketch.** Under LBL, the gate on qubit $q$ at layer $L$ is at listing index $L \cdot n + q$. The next gate on the same qubit is at index $(L+1) \cdot n + q$, a gap of $n \ge 2$. Since Phase-1 requires listing adjacency (gap = 1) on the same qubit(s), no Phase-1 action is possible.

**WCL discovery and empirical implications.** When circuits are represented in WCL instead of LBL, the Phase-1 action space becomes non-empty for circuits that contain wire-consecutive inverse pairs. Empirically, WCL listing enables approximately 7.8% Phase-1 reduction (E19, 10,000 rows: mean 7.83%, std 3.95%) on the same random circuit ensemble where LBL yields exactly 0%. This figure is consistent with the density bound from Theorem 1(a): $\mathbb{E}[|\mathcal{A}_{\text{adj}}(C)|] = n(d-1) \cdot p_{\text{cancel}}(n, \rho)$, which for typical parameters yields a small but non-zero number of adjacent inverse pairs.

**Interpretation.** The zero Phase-1 reduction observed in experiments E1--E5 is **not** a fundamental property of the random circuits themselves, but a consequence of the LBL listing model used by the generator. The circuits contain wire-level inverse pairs; LBL merely hides them from listing-adjacent Phase-1 detection. Phase-2a commutation rewriters (which operate on the circuit graph rather than the listing) are unaffected by this listing-model dependency, since they reason about wire-level adjacency rather than listing adjacency.

**Recommendation.** Future experiments should either (a) adopt WCL as the default listing model for Phase-1 evaluation, or (b) include a wire-traversal pre-processing step that identifies wire-consecutive (not listing-adjacent) inverse pairs before Phase-1 optimization. This ensures that Phase-1 results reflect the circuit's intrinsic structure rather than an artifact of the data-structure ordering.

---

## Complexity Classification

### Preliminaries

We assume familiarity with standard complexity classes:

- **P**: decision problems solvable in deterministic polynomial time.
- **NP**: decision problems with polynomial-time verifiable witnesses.
- **APX**: problems approximable within a constant factor in polynomial time.
- **PTAS**: polynomial-time approximation schemes (approximable within $(1 - \varepsilon)$ for any fixed $\varepsilon > 0$).
- **QMA**: Quantum Merlin-Arthur, the quantum analogue of NP; problems with efficiently verifiable quantum witnesses.
- **BQP**: Bounded-error Quantum Polynomial time; problems solvable efficiently on a quantum computer.

We study the following problems (see Definitions A1--A2 above for formal definitions):

| Problem | Abbreviation | Input | Question |
|---------|-------------|-------|----------|
| Circuit Identity Testing | CIT | $C, C', \epsilon$ | Is $C \equiv_\epsilon C'$? |
| Circuit Optimization Decision | CODP | $C, r, \epsilon$ | Does $\exists C'$ with $C \equiv_\epsilon C'$ and $|C'| \le (1-r)|C|$? |
| Phase-1 Optimization | P1OPT | $C$ | Find maximal non-overlapping $\mathcal{S}_1(C)$ subset. |
| Phase-1+2 Optimization | P12OPT | $C, \mathcal{G}$ | Find minimal $C'$ via adjacent + commutation moves. |
| Success Probability Estimation | SPE | $C(n,d,\rho), \delta$ | Compute $P_{\text{success}}(d)$. |

### Section 1: Known Results

#### 1.1 Standard Non-Identity/Non-Equivalence Check versus this document's CIT schema

**External result** [Janzing, Wocjan & Beth, 2003/2005]. The standard promise
problem **Non-Identity Check** (YES when a circuit is far from every
global-phase identity, NO when it is close) is QMA-complete; the work also
treats a promise version of non-equivalence checking. Its norm, phase quotient,
thresholds, and YES/NO orientation are part of the theorem.

**Scope correction.** Definition A2 asks a bare "are these channels close?"
question and does not state the complementary promise case or gap. It is not
therefore licensed to inherit the QMA-complete label merely by being named
"CIT". The earlier history-state paragraph was not a reduction and is
withdrawn.

**Status**: [STANDARD EXTERNAL RESULT, BUT NOT YET A CLASSIFICATION OF A2].

**No current implication for CODP.** CODP restricts $r\in(0,1]$; even if one
allowed $r=0$, the input circuit itself would be a trivial witness. Thus CIT is
not the $r=0$ special case of CODP and no QMA-hardness reduction follows. CODP
hardness remains open pending an explicit promise-preserving size-gap
reduction.

#### 1.2 Phase-1 Conflict Resolution is Polynomial-Time Solvable

**Result** (Proposition 1). The problem of selecting a maximum set of non-overlapping adjacent inverse pairs in a circuit is solvable in polynomial time.

**Proof idea.** The cancelable-pair conflict graph $G_{\text{cancel}}$ is the line graph of the subgraph of the circuit's path graph induced by cancelable edges. This restricts $G_{\text{cancel}}$ to a disjoint union of paths, on which maximum independent set (equivalently, maximum matching on the underlying edges) is solvable in $O(m)$ time by greedy or dynamic programming. More generally, even for formulations where the conflict graph has arbitrary structure, the problem reduces to maximum matching, solvable in $O(|E|\sqrt{|V|})$ time [Edmonds, 1965; Micali & Vazirani, 1980].

**Status**: [CORRECTED] -- Previous versions incorrectly claimed this problem was NP-complete via a flawed reduction from MIS on degree-3 graphs. The error was assuming the conflict graph could encode arbitrary degree-3 graphs; in fact, it is restricted to a line graph of a subgraph of a path.

**Implication.** Phase-1 adjacent-pair selection is computationally tractable. The greedy scan computes a maximal (not necessarily maximum) matching, achieving at least a 1/2-approximation in the worst case and the exact optimum when conflicts are absent (Lemma 4). For circuits where optimal conflict resolution is needed, an exact polynomial-time maximum matching algorithm can be substituted.

#### 1.3 Clifford Equivalence Is Efficient; Optimal Synthesis Is Separate

**Result** [Gottesman, 1997; Aaronson & Gottesman, 2004]. For Clifford circuits
(generated by $\{H,S,\mathrm{CNOT}\}$), exact equivalence up to global phase is
decidable in polynomial time using a stabilizer/tableau representation.

**Status**: [PROVEN FOR EQUIVALENCE/SIMULATION]. Gottesman--Knill does not by
itself prove that minimum-gate or minimum-depth Clifford synthesis is
polynomial-time.

**Implication.** Efficient semantic equivalence verification can make a
proposed Clifford optimization easy to *check*, but it does not make the search
for a globally minimum circuit easy. The complexity of CODP under a precise
Clifford gate basis, cost metric, ancilla policy, connectivity, and promise gap
must be proved separately; the earlier claim "Clifford CODP is in P" is
withdrawn.

#### 1.4 Solovay-Kitaev Provides Approximate Synthesis

**Result** [Kitaev, 1997; Dawson & Nielsen, 2006]. For any universal gate set $\mathcal{G}$ and any target unitary $U \in SU(2^n)$, there exists an $\epsilon$-approximate circuit $C$ with

$$
|C| = O\bigl(\log^{3.97}(1/\epsilon)\bigr).
$$

The Solovay-Kitaev algorithm constructs such a circuit in classical polynomial time (in $1/\epsilon$).

**Status**: [PROVEN].

**Implication.** Solovay-Kitaev provides an *upper bound* on circuit complexity for arbitrary unitaries, but it does not solve CODP: it synthesizes a circuit from a unitary, rather than reducing an existing circuit. The algorithm is not a peephole optimizer; it discards the original circuit structure entirely.

### Section 2: Conjectured Results

#### 2.1 Is CODP QMA-hard?

**Open question** (OP1). Is CODP QMA-hard under a fully specified promise and
cost model?

**Evidence status.** Non-Identity Check is QMA-hard, but no valid reduction to CODP is established here. The zero-size target reverses the usual identity/non-identity promise orientation, while $r=0$ is trivial under the present size convention. A reduction from $k$-Local Hamiltonian would need to prove that the history-state construction has a shorter equivalent exactly in the intended promise case and preserve both the channel-distance and circuit-size gaps; no such proof is currently available.

**Obstruction.** The history-state circuit has a very specific structure (Feynman-Kitaev clock, controlled operations). It is not known whether peephole rewrite rules can exploit this structure to find spurious reductions on NO instances. A full proof must rule out "false positives" from bounded-window rewrites.

#### 2.2 No Polynomial-Time Constant-Factor Approximation

**Withdrawn conjectural formulation** (OP2). The earlier multiplicative
approximation claim was not supported by a reduction and is ill-defined when
the optimum cost or achievable reduction is zero. The admissible question is:
under a fixed gate set, metric, ancilla/connectivity policy, and additive or
gap approximation objective, what approximation guarantees or hardness bounds
hold for sequential circuit rewriting?

**Evidence.** The Phase-1 subproblem (adjacent pair selection) is polynomial-time solvable via maximum matching (Proposition 1, corrected). However, the full CODP includes commutation rewriting, which dynamically changes the conflict graph. Whether the dynamic optimization problem is APX-hard is unknown. For the static Phase-1 problem on bounded-degree conflict graphs, greedy matching achieves a constant-factor approximation.

**Open direction.** The quantum case may be harder because commutation moves dynamically change the conflict graph. Whether this dynamic graph admits a PTAS or is APX-hard is unknown.

#### 2.3 Parameterized Complexity

**Conjecture.** CODP is fixed-parameter tractable (FPT) in the circuit treewidth $t$ but W[1]-hard in the number of non-Clifford gates $t_{\text{non-Clifford}}$.

**Evidence.**
- **Treewidth**: Circuits of treewidth $t$ can be optimized via dynamic programming on the tree decomposition in time $O(f(t) \cdot \text{poly}(|C|))$. For $t = O(\log n)$, this is quasi-polynomial. For $t = O(1)$, it is polynomial.
- **Non-Clifford gates**: Each $T$ gate or continuous rotation leaves the pure
  stabilizer formalism. The number of non-Clifford gates is a natural
  parameter, but this observation alone proves no CODP hardness result.

**Status**: [CONJECTURE] -- no FPT algorithm has been published for circuit optimization parameterized by treewidth, though the general approach is standard.

### Section 3: Open Problems

#### 3.1 Approximation Algorithms

**Open Problem 3.1.1.** What is the best approximation ratio achievable for CODP in polynomial time?

- Lower bound: $\Omega(1/n)$ (any algorithm can cancel at least one pair if one exists, giving $1/|C| = \Omega(1/(nd))$).
- Upper bound: $O(1)$ (greedy achieves a constant fraction of the maximum independent set in the conflict graph for bounded-degree graphs).
- Gap: Is there a polynomial-time $O(\log n)$-approximation? $O(\sqrt{n})$?

**Open Problem 3.1.2.** Does there exist a polynomial-time approximation scheme (PTAS) for CODP restricted to circuits of bounded treewidth?

#### 3.2 Quantum vs. Classical Complexity

**Open Problem 3.2.1.** Is CODP in QMA? That is, given a circuit $C$ and a claimed reduction $C'$, can a quantum verifier efficiently check that $C \equiv_\epsilon C'$ and $|C'| \le (1-r)|C|$?

- Checking $|C'| \le (1-r)|C|$ is trivial.
- A state on which two circuits differ witnesses **non-equivalence**, not the universal closeness condition $C \equiv_\epsilon C'$. The quantifier direction therefore does not give the claimed QMA verifier for equivalence.
- A polynomial classical description of $C'$ can witness the size bound, but this alone does not efficiently certify worst-case channel-distance closeness. Membership of CODP in QMA is open in this project.

**Open Problem 3.2.2.** Does a quantum computer provide any advantage for circuit optimization? That is, is there a BQP algorithm for CODP that outperforms the best classical algorithm?

- If CODP is QMA-hard, then BQP advantage is unlikely unless BQP = QMA.
- However, *approximate* optimization (e.g., quantum annealing on the conflict graph) may offer speedups for specific instances.

#### 3.3 Average-Case Complexity

**Open Problem 3.3.1.** What is the average-case complexity of CODP for random circuits $C(n, d, \rho)$?

- Empirically, greedy achieves $O(1/d)$ reduction on random circuits (Theorem 1).
- Is this optimal on average? That is, does the optimal reduction $\mathbb{E}[R_{\text{opt}}]$ also scale as $O(1/d)$?
- If so, greedy is an average-case constant-factor approximation, even though it may be worst-case suboptimal.

**Open Problem 3.3.2.** Is there a phase transition in the *average-case* hardness of CODP as a function of $(n, d, \rho)$?

- For small $d$, circuits are product-state-like and may admit efficient optimization.
- For large $d$, circuits approximate Haar-random unitaries and optimization is hard.
- Is there a sharp boundary, or a smooth crossover?

### Section 4: Complexity Classification Table

| Problem | Restriction | Complexity | Status | Reference |
|---------|------------|------------|--------|-----------|
| Non-Identity / Non-Equivalence Check | Standard general-circuit promise formulation | QMA-complete | [EXTERNAL RESULT; precise norm/gap/orientation required] | Janzing et al., 2003/2005 |
| A2 CIT schema | General circuits | Unclassified as written | [PROMISE GAP/ORIENTATION MISSING] | This audit |
| Exact equivalence | Clifford circuits | P | [PROVEN] | Stabilizer/tableau formalism |
| CIT | Stabilizer states | P | [PROVEN] | Aaronson & Gottesman, 2004 |
| CODP | General circuits | Open | [NO VALID CIT REDUCTION] | OP1 |
| CODP | Clifford circuits | Open under general optimal-cost formulations | [EQUIVALENCE IN P DOES NOT IMPLY OPTIMIZATION IN P] | Scope correction |
| CODP | Bounded treewidth | FPT? | [CONJECTURE] | Open |
| P1OPT (conflict resolution) | General circuits | P (maximum matching) | [CORRECTED] | Proposition 1 |
| P1OPT (greedy scan) | General circuits | P | [PROVEN] | $O(|C|)$ scan |
| P12OPT | General circuits | QMA-hard? | [CONJECTURE] | OP1 + OP2 |
| P12OPT | Clifford circuits | Unclassified for global optimum | [RESTRICTED REWRITES/SYNTHESIS HEURISTICS DO NOT PROVE P] | Scope correction |
| Approx-CODP | General circuits | APX-hard? | [CONJECTURE] | OP2 |
| Approx-CODP | Bounded degree | $O(1)$-approx | [PROVEN] | Greedy matching |
| SPE | General circuits | #P-hard? | [CONJECTURE] | Counting solutions |

### Section 5: Relationship to Existing Literature

#### 5.1 Quantum Circuit Optimization in Compilers

Production compilers (Qiskit, Cirq, t|ket>) implement both Phase 1 and Phase-2 (a+b). The complexity results here explain why:

- **Phase 1** (adjacent cancellation) is fast ($O(|C|)$) and the conflict resolution subproblem is polynomial-time solvable via maximum matching (Proposition 1, corrected). The greedy scan provides a practical $O(|C|)$ approximation.
- **Phase-2a** (commutation-based rewriting) is slower (the general problem is believed to be hard, see Conjecture OP1) but necessary to exceed the Phase-1 ceiling.
- **Template matching** (e.g., Qiskit's `TemplateOptimization`) is a form of Phase-2b with a fixed pattern library; its complexity is governed by subgraph isomorphism on the circuit graph, which is NP-hard.

#### 5.2 Barren Plateaus and Circuit Complexity

The phenomenon of *barren plateaus* in variational quantum algorithms [McClean et al., 2018] is related to the **optimization desert** observed in our experiments. Both arise from concentration of measure in high-dimensional Hilbert spaces:

- **Barren plateaus**: gradients of variational cost functions concentrate exponentially around zero.
- **Optimization deserts**: the probability of finding a useful local modification concentrates exponentially around zero.

We classify this as a **heuristic analogy** [HEURISTIC] rather than a proven equivalence, because the discrete optimization landscape lacks the smooth structure required for Levy's lemma.

#### 5.3 Circuit Complexity Theory

The *quantum circuit complexity* of a unitary $U$, denoted $\mathcal{C}(U)$, is the minimum number of gates from $\mathcal{G}$ needed to synthesize $U$. Key results:

- **Haar-random unitaries** have complexity $\mathcal{C}(U) \ge \Omega(4^n / n)$ with high probability [Nielsen, 2005; Harrow & Montanaro, 2017].
- **Random circuits of depth $d$** have complexity $\le nd$ by construction.
- For $d \ll 4^n / n$, random circuits are *far* from Haar-random in complexity, leaving room for optimization.
- Approximate design or distributional convergence does not imply that a
  particular sampled circuit is minimum-size, nor that a shorter equivalent
  circuit is impossible.

The former Haar-complexity explanation is withdrawn. The observed decay is an
empirical property of the sampled generator/listing/rule/budget contract; it
cannot be promoted to a circuit-complexity lower bound without a compatible
distributional theorem and a valid quantifier/size argument.

---

## Cross-Reference Map

### Conjectures (detailed in `formal_results.md`)

| ID | Statement | Evidence | Section |
|----|-----------|----------|---------|
| OP1 | CODP is QMA-hard (motivating open problem) | Weak -- reduction sketch | formal_results.md Conjectures |
| OP2 | No PTAS for CODP (motivating open problem) | Weak -- MIS gap issues | formal_results.md Conjectures |
| **C1** | **All Phase-1 optimizers share a structural ceiling** | **REFUTED -- three-gate SWAP+REMOVAL counterexample** | formal_results.md Former Conjectures |
| **C2** | **Some families have context-dependent $\Omega(1)$ Phase-2 advantage** | **EXISTENCE PROVED -- Thm 7 and Thm 9; classification open** | formal_results.md Former Conjectures |

### Theorems and Propositions (detailed in `formal_results.md`)

| ID | Statement | Status | Section |
|----|-----------|--------|---------|
| Thm 1(a) | Adjacent inverse pair density bound under WCL (expectation) | [PROVEN -- elementary] | formal_results.md Theorems |
| Thm 1(b) | LBL listing model yields $\mathcal{S}_1(C) = \emptyset$ for $n \ge 2$ | [PROVEN -- structural] | formal_results.md Theorems |
| Thm 2 | Greedy predicate ceiling; proposed stochastic ceiling | **[PART (a) PROVEN; GENERAL PART (b) REFUTED]** | formal_results.md Theorems |
| Thm 2c | Bounded INSERTION cascade lemma ($R_{\text{removal}} \le 2k$) | [PROVEN -- insertion-debt invariant] | formal_results.md Appendix A |
| Thm 2d | INSERTION commutation cascade bound | **[WITHDRAWN -- invalid multi-qubit per-wire factorization]** | formal_results.md Appendix A |
| Lemma 3 | Commutation preserves equivalence | [PROVEN -- 1-line, supporting lemma] | formal_results.md Lemmas |
| Lemma 4 | Greedy optimality for non-conflicting pairs | [PROVEN -- narrow scope, supporting lemma] | formal_results.md Lemmas |
| Thm 5 | High-probability bound on inverse pairs (McDiarmid) | **[PROOF INCOMPLETE -- dependent random matching]** | formal_results.md Theorems |
| Prop 6 | Greedy ceiling for corrected restricted AG generator | **[RESTRICTED; former general claim refuted by n=2, seed=35]** | formal_results.md Theorems |
| Thm 7 | Explicit circuit family with $\Omega(1)$ Phase-2a advantage | [PROVEN -- artificial] | formal_results.md Theorems |
| Thm 8 | Haar-random incompressibility + bounded-window limit | **[WITHDRAWN -- incompatible premises]** | formal_results.md Theorems |
| Thm 9 | Full-pipeline Phase-2b construction achieves $2n/(3n+2)$ for the stated all-ones BV circuit | [PROVEN achieved reduction; no global optimality; pure Phase-2a bound open] | formal_results.md Appendix B |
| Prop 1 | Conflict resolution is polynomial-time (maximum matching) | [CORRECTED] | formal_results.md Propositions |
| Obs 1 | Greedy matches stochastic optimizers | **[WITHDRAWN GENERALIZATION; COUNTEREXAMPLE + HISTORICAL INCUMBENT BUG]** | formal_results.md Empirical Observations |

### Complexity Results (see Complexity Classification above)

| Problem | Restriction | Complexity | Status |
|---------|------------|------------|--------|
| Non-Identity / Non-Equivalence Check | Standard promise formulation | QMA-complete | [EXTERNAL RESULT; not automatically A2] |
| Exact equivalence | Clifford circuits | P | [PROVEN] |
| CODP | General circuits | Open | [NO VALID HARDNESS REDUCTION -- OP1] |
| P1OPT (conflict resolution) | General circuits | P (maximum matching) | [Prop 1, corrected] |
| P1OPT (greedy scan) | General circuits | P | [PROVEN] |

---

## References

1. Janzing, D., Wocjan, P., & Beth, T. (2003). "Non-identity-check is QMA-complete." *Int. J. Quantum Information*, 1(4), 507-518.
2. Kempe, J., Kitaev, A., & Regev, O. (2006). "The Complexity of the Local Hamiltonian Problem." *SIAM J. Computing*, 35(5), 1070-1097.
3. Gottesman, D. (1997). "Stabilizer codes and quantum error correction." *Ph.D. thesis, Caltech*.
4. Aaronson, S., & Gottesman, D. (2004). "Improved simulation of stabilizer circuits." *Physical Review A*, 70(5), 052328.
5. Dawson, C. M. & Nielsen, M. A. (2006). "The Solovay-Kitaev algorithm." *Quantum Info. Comput.* 6, 81-95.
6. Harrow, A. W. & Montanaro, A. (2017). "Quantum computational supremacy." *Nature* 549, 188-196.
7. McClean, J. R. et al. (2018). "Barren plateaus in quantum neural network training landscapes." *Nat. Commun.* 9, 4812.
8. Garey, M. R. & Johnson, D. S. (1979). *Computers and Intractability*. W. H. Freeman.
9. Berman, P. & Karpinski, M. (1999). "On some tighter inapproximability results." *LNCS* 1644, 200-209.
10. Downey, R. G. & Fellows, M. R. (2013). *Fundamentals of Parameterized Complexity*. Springer.
11. Edmonds, J. (1965). "Paths, trees, and flowers." *Canad. J. Math.* 17, 449-467.
12. Micali, S. & Vazirani, V. V. (1980). "An $O(\sqrt{|V|} \cdot |E|)$ algorithm for finding maximum matching in general graphs." *Proc. 21st IEEE FOCS*, 17-27.
13. Kitaev, A. Yu. (1997). "Quantum computations: algorithms and error correction." *Russ. Math. Surv.* 52, 1191-1249.
14. McDiarmid, C. (1989). "On the method of bounded differences." *Surveys in Combinatorics*, London Mathematical Society Lecture Note Series 141, 148-188.
15. Nielsen, M. A. (2005). "A geometric approach to quantum circuit lower bounds." *arXiv:quant-ph/0502070*.

---

**Document version**: 5.4.0 (Consolidated)  
**Last updated**: 2026-06-13  
**Author**: Q-research Theoretical Framework Team  
**Companion document**: `formal_results.md` (all theorems, lemmas, propositions, conjectures, scope analysis, and proof appendices)
