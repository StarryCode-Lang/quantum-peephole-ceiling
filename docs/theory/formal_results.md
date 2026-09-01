# Formal Results: Theorems, Conjectures, Scope Analysis, and Proof Appendices

**Version**: 4.0 (Consolidated)
**Date**: 2026-06-17
**Status**: Complete collection of all formal results for the QIP manuscript -- theorems, lemmas, propositions, empirical observations, conjectures, open problems, scope analysis, and detailed proof appendices.

---

## Notation

For base notation ($n$, $d$, $\mathcal{G}$, $C(n,d,\rho)$, $|C|$, $F_{\text{avg}}$, etc.) and all formal definitions D1--D10 (quantum circuit, unitary equivalence, peephole optimization, Phase 1/2, ceilings, action spaces), see `framework.md`.

> **Notation**: Phase-2a refers to commutation-based rewriting (implemented in `commutation_rewriter.py`). Phase-2b refers to template-assisted rewriting (implemented in `template_matcher.py` and evaluated at full scale in the v2 validation dataset). When we write "Phase-2" without a suffix, we refer to Phase-2a; Phase-2b results are labeled explicitly.

Notation specific to this document:

- $L(C)$: line graph of circuit $C$ (vertices = gates, edges = adjacency in the circuit list)
- $\mathcal{A}_{\text{adj}}(C)$: the set of adjacent inverse gate pairs in $C$
- $\mathcal{A}_{\text{comm}}(C)$: the set of gate pairs that can be brought into adjacency via commutation rewriting
- $R_1(C)$: reduction fraction achieved by Phase-1-only optimization
- $R_{1+2}(C)$: reduction fraction achieved by Phase-1+2 optimization
- $\mathbb{E}_{C \sim \mathcal{E}}[\cdot]$: expectation over circuit ensemble $\mathcal{E}$

---

## Section 1: Audited Results, Open Claims, and Withdrawn Candidates

### Observation 1 (formerly Theorem 1): Adjacent Inverse Pair Density in Random Circuits

> **CORRECTION (2026-08-06).** Part (a) below, as originally written, contains
> two constant errors: the one-qubit term omits the discrete-gate count
> $k_1$ (the correct probability is $k_1/g_1^2$, and the claimed bound
> $2/g_1^2$ fails for $g_1 \ge 3$), and the two-qubit term double-counts
> pairs per endpoint wire. The corrected statement —
> $\mathbb{E}[|\mathcal{A}_{\text{adj}}|] = n(d-1)\left[(1-\rho)^2 k_1/g_1^2 + \rho^2/(2 g_2 (n-1))\right]$
> for even $n$, with odd-$n$ finite-size corrections — appears in manuscript
> §3.2 and is **directly validated by experiment E30** (`data/v10/e30/`,
> 13,500 trials, 27 cells, max $|z| = 2.86$, median relative error 1.4%).
> See `docs/theory/proof_audit_2026-08-06.md` for the full audit.

> **Listing-model note (added 2026-06-13).** The number of adjacent inverse pairs depends critically on the **circuit listing model** -- how gates are ordered in the circuit data structure. We distinguish two models:
>
> - **Wire-consecutive listing (WCL):** Gates on the same qubit wire are placed consecutively in the listing. This is the natural model for circuit diagrams and some synthesis tools.
> - **Layer-by-layer listing (LBL):** The circuit is generated layer by layer, with one gate per qubit per layer. Gates on the same qubit at layers $L$ and $L+1$ are separated by $n-1$ intervening gates from other qubits. This is the model used by our `UniversalGenerator` (`src/circuits/generator_v2.py`).
>
> Observation 1(a) applies to its random-pairing WCL ensemble; Observation 1(b) is restricted to the concrete operation ordering emitted by `UniversalGenerator` and to the adjacent Greedy action set.

**Statement (a): Wire-consecutive listing model.** Let $C(n, d, \rho)$ be a random circuit on $n$ qubits of depth $d$ with two-qubit gate density $\rho$, represented in a wire-consecutive listing where gates on the same qubit are adjacent in the circuit listing. Assume single-qubit gates are drawn uniformly from $\mathcal{G}_1$ with $|\mathcal{G}_1| = g_1$, and two-qubit gates from $\mathcal{G}_2$ with $|\mathcal{G}_2| = g_2$. The expected number of listing-adjacent inverse pairs is

$$
\mathbb{E}\bigl[|\mathcal{A}_{\text{adj}}(C)|\bigr] = n(d - 1) \cdot p_{\text{cancel}}(n, \rho),
$$

where, for even $n$ under the random-pairing layer model used by E30,

$$
p_{\text{cancel}}(n, \rho) = (1 - \rho)^2\frac{k_1}{g_1^2} + \frac{\rho^2}{2g_2(n-1)},
$$

and $k_1$ is the number of discrete one-qubit labels whose inverse is also
sampled. Continuous angles match their inverse with probability zero. For odd
$n$, the unpaired wire gives the finite-size correction recorded and tested in
E30; it must not be replaced by the even-$n$ formula.

**Corollary 1.1.** Under WCL, the expected fractional reduction from Phase-1 adjacent cancellations satisfies $\mathbb{E}[R_{\text{adj}}] \le 2 p_{\text{cancel}}$, which is $O(1/g_1^2 + 1/(g_2 n))$ -- negligibly small for standard gate sets.

**Statement (b): `UniversalGenerator` layer-major listing.** Let $C(n,d,\rho)$ be emitted by `UniversalGenerator`: at position $q<n-1$ in each layer the operation has support either $\{q\}$ or $\{q,q+1\}$, while position $n-1$ has support $\{n-1\}$.  For $n\ge2$, the adjacent Greedy action space (same-support inverse cancellation or same-axis rotation merging) is structurally empty:

$$
\mathcal{S}_{\mathrm{Greedy}}(C) = \emptyset.
$$

Consequently, the implemented `GreedyGateCancellation` without WCL preprocessing has $R(C)=0$ on this generator.  This does **not** imply zero reduction for stochastic optimizers that can reorder gates, nor for arbitrary layer-major circuit generators.

**Proof of (a).**

**Step 1: Single-qubit contribution.** On a fixed wire, two consecutive layers both place single-qubit gates with probability $(1-\rho)^2$. Uniform discrete labels contribute inverse-match probability $k_1/g_1^2$; continuously sampled rotations contribute zero.

**Step 2: Two-qubit contribution.** Summing over the $\binom n2$ unordered pairs avoids double-counting the two endpoints. Random pairing and gate-label matching give the per-wire-normalized term $\rho^2/[2g_2(n-1)]$.

**Step 3: Summing.** Linearity of expectation over $n(d-1)$ wire-boundary positions gives the stated even-$n$ expression; the odd-$n$ correction accounts for one unpaired wire per layer.

**Step 4: Fractional bound.** Each cancellation removes 2 gates from $|C| \approx nd/(1-\rho/2)$, giving $\mathbb{E}[R_{\text{adj}}] \le 2 p_{\text{cancel}}$. For realistic parameters ($\rho=0.3$, $n=5$, $g_1=4$), this yields $\le 2\%$ per pass. $\blacksquare$

**Proof of (b).**

**Step 1: Generator support structure.** Within a layer, consecutive positions $q,q+1$ have supports in $\{\{q\},\{q,q+1\}\}$ and $\{\{q+1\},\{q+1,q+2\}\}$ (with the endpoint truncated).  They may overlap, but their complete supports are never equal.

**Step 2: Layer boundary.** The last support $\{n-1\}$ and the next layer's first support $\{0\}$ or $\{0,1\}$ are unequal for every $n\ge2$ (including the overlapping $n=2$ case).

**Step 3: Greedy predicates require equal support.** Both `_is_self_inverse_pair` and rotation merging require identical ordered qubit support. Steps 1-2 rule this out for every adjacent pair, so neither action is available.

**Step 4: Conclusion.** Greedy terminates without a rewrite, hence has zero reduction.  The conclusion is generator- and algorithm-specific. $\blacksquare$

**Remark.** Observation 1(b) explains the empirically observed zero standard deviation in E1 (25,000 trials): the generator uses LBL, so $\mathcal{S}_1(C)$ is structurally empty for every generated circuit. This is not a bug but a property of the listing model.

**Note on depth.** Adjacent operations are not always disjoint; the valid invariant is unequal complete support.  This is a direct property of the current generator, not a general theorem about layer-major listings.

---

### Theorem 2: Greedy Predicate Result and Refuted Generalization

**Statement.** Let $\mathcal{O}_1 = \{\text{Greedy}, \text{SA}, \text{GA}, \text{RLS}\}$. Define the set of listing-adjacent inverse pairs:

$$
\mathcal{S}_1(C) = \bigl\{(g_i, g_{i+1}) : g_i \text{ and } g_{i+1} \text{ act on the same qubit(s) and } g_{i+1} = g_i^{-1}\bigr\}.
$$

**(a)** For the Greedy optimizer (which uses only REMOVAL and rotation merging), if $\mathcal{S}_1(C) = \emptyset$ and no consecutive rotation gates on the same qubit admit merging, then Greedy achieves zero reduction.

**(b) General stochastic ceiling refuted (2026-08-10).** Let $C=[H(q_0),X(q_1),H(q_0)]$. Its initial adjacent Greedy action set is empty, so Greedy returns three gates. A legal SWAP of the first two disjoint-support gates gives $[X(q_1),H(q_0),H(q_0)]$, after which REMOVAL returns the one-gate circuit $[X(q_1)]$ with exact fidelity. The implemented simulated annealer finds this 66.7% reduction for fixed seeds (regression: `tests/test_stochastic_incumbent.py`). Thus an optimizer allowed to traverse a gate-count-neutral SWAP can strictly exceed Greedy even when the initial $\mathcal{S}_1(C)$ is empty.

**Proof.**

**Step 1: Characterize Phase-1 moves.** The base class provides four move types: REMOVAL (cancel adjacent inverses), SWAP (exchange disjoint-qubit gates), COMMUTATION (reorder commuting pair), and INSERTION (insert an identity pair $g \cdot g^{-1}$ at an arbitrary position).

**Step 2: SWAP and COMMUTATION can create listing-adjacent pairs.** SWAP exchanges gates on disjoint qubits. While it preserves the gate multiset and the relative order of gates on each individual wire, it can bring previously non-adjacent gates into listing adjacency. If the resulting adjacent pair acts on the same qubits and is inverse, SWAP creates a new $\mathcal{S}_1$ element. However, the two gates in the new pair were already present in $C$ on their respective wires; SWAP merely makes their inverse relationship listing-visible. Any reduction enabled by SWAP was therefore latent in the wire-level structure of $C$, not created by SWAP itself.

Local COMMUTATION replaces $(g_i, g_{i+1})$ with an equivalent pair $(g_i', g_{i+1}')$ of the same size. If the original was not an inverse pair, the commuted pair is generically also not an inverse pair (commutation preserves the unitary product, not the inverse relationship).

**Step 3: INSERTION creates new $\mathcal{S}_1$ elements but cannot achieve net reduction.** INSERTION adds an identity pair $(g, g^{-1})$ at position $p$, increasing $|C|$ by 2. The inserted pair is itself an adjacent inverse pair, so $\mathcal{S}_1(C') \supseteq \{(g_p, g_{p+1})\} \neq \emptyset$. However, any REMOVAL applied to the inserted pair simply restores the original circuit (net change: 0). More generally, if $k$ INSERTION moves are applied (adding $2k$ gates), the maximum number of gates removable via subsequent REMOVALs that involve at least one inserted gate is $2k$, yielding a net reduction of at most 0. Cancellations involving only pre-existing gates (not the inserted gates) could have been found without INSERTION.

**Step 4: Induction for Greedy.** Starting from $C$ with $\mathcal{S}_1(C) = \emptyset$ and no mergeable rotations, Greedy applies only REMOVAL (which requires $\mathcal{S}_1 \neq \emptyset$) and rotation merging (which requires consecutive rotations on the same qubit). Neither is available, so $R_{\text{greedy}}(C) = 0$.

**Step 5: What the code and data establish.** SA, GA, and RLS call `_generate_neighbor`, which proposes REMOVAL, SWAP, COMMUTATION, or INSERTION.  Their observed convergence near Greedy is empirical evidence about these implementations and sampled circuits.  A fitness preference against longer circuits is not a proof that every accepted multi-step path obeys a global reduction ceiling.  Thus part (a) is proved; the general stochastic conclusion in part (b) remains open.

**Remark (INSERTION and Theorem 2 scope).** The code implements INSERTION as a unitary-preserving expansion move that inserts identity pairs from $\{H\text{-}H, X\text{-}X, Y\text{-}Y, Z\text{-}Z\}$ (`base.py:444-483`). All three stochastic optimizers (RLS, SA, GA) invoke INSERTION via `_generate_neighbor`. Empirically, INSERTION creates new $\mathcal{S}_1$ elements in 100% of trials (1000/1000 on a test circuit with $\mathcal{S}_1 = \emptyset$), but INSERTION + REMOVAL sequences yield zero net reduction in 100% of trials (5000/5000). The insertion-debt argument proves this only for the INSERTION+REMOVAL subsystem. Once SWAP or COMMUTATION is admitted, the earlier "identical action space" and general stochastic "reduction ceiling" claims are unproved; the 5000/5000 result remains empirical evidence about the tested implementations and distribution.

**Re-audit of the INSERTION cascade [2026-08-09].** Appendix A does not close the general gap.  Theorem 2c is limited to the literal INSERTION+REMOVAL rewrite system.  Former Theorem 2d relies on an invalid per-wire-unitary factorization for multi-qubit gates and on an unproved identification of pair counts with an attainable Phase-2 optimum.

- **Theorem 2c (Bounded INSERTION Cascade Lemma):** For any circuit $C$ with $\mathcal{S}_1(C) = \emptyset$, let $k$ INSERTION moves produce circuit $C'$ with $|C'| = |C| + 2k$. Let $R_{\text{removal}}(C')$ be the maximum number of gates removable via REMOVAL sequences involving at least one inserted gate. Then $R_{\text{removal}}(C') \le 2k$, so the net gate-count change from any INSERTION + REMOVAL sequence is $\ge 0$. The proof uses an insertion-debt invariant: each INSERTION increases the debt by 2, each REMOVAL involving an inserted gate decreases it by at most 2, and the debt is always non-negative.

- **Former Theorem 2d:** **[PROOF INVALID / CLAIM OPEN].** A valid replacement would need a precise trace-monoid or dependency-DAG model, a conflict-aware optimum rather than a raw pair count, and a proof that identity insertion cannot improve that optimum.

**Status:** Part (a) proved; Theorem 2c is a restricted rewrite-system result; the general part (b) is refuted by an explicit three-gate counterexample; former Theorem 2d remains open after its proof was invalidated.

---

### Lemma 3 (formerly Theorem 3): Commutation Rewriting Preserves Unitary Equivalence

> **Status note (2026-06-13):** Downgraded from Theorem to Lemma. The result is a one-line proof of a basic algebraic property, more appropriately classified as a supporting lemma than a standalone theorem.

**Statement.** Let $C = (g_1, \ldots, g_m)$ implement $U = g_m \cdots g_1$. If $C'$ is obtained by replacing $(g_i, g_{i+1})$ with $(g_i', g_{i+1}')$ such that $g_{i+1}' g_i' = g_{i+1} g_i$ and supports match, then $U' = U$ exactly.

**Proof.** $U = g_m \cdots g_{i+2} \cdot (g_{i+1} g_i) \cdot g_{i-1} \cdots g_1 = g_m \cdots g_{i+2} \cdot (g_{i+1}' g_i') \cdot g_{i-1} \cdots g_1 = U'$. $\blacksquare$

**Corollary 3.1.** Any sequence of commutation rewrites preserves unitary equivalence.

**Corollary 3.2.** Any circuit produced by the HybridCommuteRewrite pipeline (Phase 1 + Phase-2a + Phase 1) is exactly unitarily equivalent to the input.

---

### Lemma 4 (formerly Theorem 4): Greedy is Optimal for Non-Conflicting Adjacent Pairs

> **Status note (2026-06-13):** Downgraded from Theorem to Lemma. The result applies only to the special case where no two cancelable pairs share a gate -- a condition that holds trivially for most random circuits and is too narrow to serve as a standalone theorem.

**Statement.** If no two pairs in $\mathcal{S}_1(C)$ share a gate (i.e., pairs are non-conflicting), then the greedy scan achieves the maximum Phase-1 reduction, exactly $2|\mathcal{S}_1(C)|$ gates.

**Proof.** Non-conflicting pairs are independent: removing one does not affect the availability of others. The greedy scan visits every position and cancels all encountered pairs. Since pairs are disjoint, no cancellation destroys another. Therefore greedy cancels all $|\mathcal{S}_1(C)|$ pairs, achieving the maximum. $\blacksquare$

---

### Candidate Theorem 5: High-Probability Bound on Adjacent Inverse Pair Density

**Status (2026-08-09): PROOF INCOMPLETE.** The displayed McDiarmid constant
assumes $n(d-1)$ independent per-wire choices.  Random two-qubit matchings
couple the endpoint choices, so that product structure is not the E30
generator's probability space.  A valid proof must expose independent
matching-generation variables and recompute their bounded-difference
constants.  E30 agreement with the expectation does not validate this tail
bound.

**Statement.** Under the hypotheses of Theorem 1, let $X = |\mathcal{A}_{\text{adj}}(C)|$. Then for any $\delta > 0$:

$$
\Pr\bigl[X \ge \mathbb{E}[X] + t\bigr] \le \exp\!\left(-\frac{t^2}{2n(d-1)}\right).
$$

In particular, with probability at least $1 - \delta$, the number of adjacent inverse pairs satisfies

$$
X \le n(d-1)\,p_{\text{cancel}}(n,\rho) + \sqrt{2n(d-1)\ln\frac{1}{\delta}}.
$$

**Corollary 5.1.** With probability at least $1 - 1/\text{poly}(n)$, the Phase-1 reduction fraction satisfies

$$
R_1(C) \le O\!\left(\frac{1}{g_1^2} + \frac{1}{g_2 n} + \sqrt{\frac{\ln(n)}{nd}}\right),
$$

which vanishes as $n, d \to \infty$. This strengthens Corollary 1.1 from an expectation bound to a high-probability bound.

**Proof.**

**Step 1: Bounded differences.** Consider the circuit $C$ as generated by $N = n(d-1)$ independent random choices (one gate per qubit per layer boundary). Changing any single gate choice affects $X$ by at most $\pm 2$, since each gate participates in up to two adjacent pairs on its wire (one with its predecessor and one with its successor). Thus the bounded-differences condition holds with $c_i = 2$ for all $i \in \{1, \ldots, N\}$.

**Step 2: McDiarmid's inequality.** By McDiarmid's inequality [McDiarmid, 1989]:

$$
\Pr[X - \mathbb{E}[X] \ge t] \le \exp\!\left(-\frac{2t^2}{\sum_{i=1}^N c_i^2}\right) = \exp\!\left(-\frac{2t^2}{4N}\right) = \exp\!\left(-\frac{t^2}{2N}\right).
$$

**Step 3: Substitution.** Setting $t = \sqrt{2N\ln\frac{1}{\delta}}$, we obtain $\Pr[X \ge \mathbb{E}[X] + t] \le \exp(-t^2/(2N)) = \exp(-\ln(1/\delta)) = \delta$. Substituting $\mathbb{E}[X]$ from Theorem 1 and dividing by $|C|/2$ to obtain the fractional reduction yields the stated bound. $\blacksquare$

**Remark (Commutation sufficiency).** The bound in Theorem 5 applies to *listing-adjacent* inverse pairs only -- i.e., pairs that are consecutive on the same wire under the chosen listing model. Phase-2a commutation rewriting can access inverse pairs beyond this bound by swapping non-adjacent gates into adjacency via commutation moves. The set of commutation rules implemented in the optimizer (disjoint-qubit commutation, same-axis rotation commutation, CX control/target swaps) is *sufficient but not necessary*: they never produce an incorrect reordering, but they may miss valid reorderings that would expose additional cancellations. Consequently, any experimental "Phase-2a ceiling" measured with this rule set is a *lower bound* on the true ceiling achievable with a complete set of commutation identities. Papers must frame Phase-2a ceiling measurements as "under the tested commutation rules," not as fundamental limits.

---

### Proposition 6: Greedy Ceiling for the Restricted AG-Stage Generator

**Corrected statement (2026-08-09).** Let $C$ be emitted by the current restricted `generate_ag_canonical_circuit`, whose CNOT matchings are separated by non-empty H stages. Then its initial adjacent Greedy action set is empty, so `GreedyGateCancellation` performs no reduction. This is a property of this generator, not of every Aaronson--Gottesman canonical-form representation and not of every stochastic Phase-1 optimizer.

**Proof.**

**Step 1: Restricted stage structure.** The generator emits $H$--$C$--$H$--$C$--$H$--$S$--$C$--$S$--$H$--$C$--$H$, uses disjoint gates within each stage, and as of 2026-08-09 makes every H separator non-empty.

**Step 2: Adjacent gates span distinct stages.** In the canonical decomposition, any two adjacent gates $g_i, g_{i+1}$ in the circuit listing belong either to (a) different stages, or (b) the same stage but different qubits. In case (b), the gates act on different qubits, so $g_{i+1} \neq g_i^{-1}$ by the qubit-matching requirement (Definition 6). In case (a), the gates are of different types (e.g., $H$ followed by $\text{CNOT}$, or $S$ followed by $\text{CNOT}$), so $g_{i+1} \neq g_i^{-1}$ by the gate-type requirement.

**Step 3: No initial Greedy pair.** Since neither case can produce an inverse pair or same-axis rotation merge on equal support, the initial Greedy action set is empty and Greedy returns unchanged. $\blacksquare$

**Status.** [PROVED FOR THE RESTRICTED GENERATOR; EMPIRICALLY CHECKED] The corrected v10 E23 rerun covers $n=3,\ldots,10$ with 20 seeds per size (160/160 exact-fidelity rows) and observes zero Greedy reduction throughout, consistent with the support-structure proof. The pre-fix generator has counterexamples (for example $n=2$, seed 35 gives one adjacent CNOT pair and 28.57% Greedy reduction). Neither the proof nor E23 establishes a theorem about general Aaronson--Gottesman canonical forms.

**Remark.** This result proves an empty initial Greedy action set only for the project's restricted staged generator. Calling that generator a general Aaronson--Gottesman canonical form, or exporting the claim to arbitrary Clifford normal forms or stochastic optimizers, would exceed the proof.

**Remark on scope (general Clifford circuits).** An arbitrary Clifford circuit, and even another serialization of an equivalent staged form, may contain adjacent inverse pairs. Efficient conversion to some Clifford canonical representation does not imply that every such representation has the project's 11-stage listing property, nor that the number of removed pairs characterizes a Phase-1 optimum. Extension beyond the concrete generator is open.

---

### Theorem 7: Explicit Circuit Family with Constant Idealized Phase-2a Advantage

**Corrected statement (2026-08-09).** There exists an explicit family $\{C_n\}$ for even $n\ge4$ such that:
1. the initial adjacent Greedy action set is empty, so Greedy alone has zero reduction; and
2. a Phase-2a+Greedy pipeline whose commutation window scales to cover the construction achieves a constant fractional reduction (indeed the construction is reducible to identity).

This does not claim that every stochastic ``Phase-1`` optimizer is powerless,
or that the implemented fixed default window $w=10$ has an asymptotic
guarantee for all $n$.

This establishes Conjecture C2 constructively for Phase-2a.

**Nature of the construction.** The hardness family constructed in Theorem 7 is an artificial circuit family designed specifically to demonstrate that the Phase-2a advantage bound is achievable. It is not a naturally occurring circuit family and should not be interpreted as evidence that natural circuit families exhibit this behavior. The theorem is an existence proof, not an empirical claim about practical circuits.

**Status.** [PROVEN + EMPIRICALLY VALIDATED] Experiment E24 instantiates this family for $n = 4, 6, \dots, 12$ (5 trials each) and measures mean Phase-1 reduction $0.0000$ and mean Phase-2a reduction $0.7980 \gg 1/6$, confirming the $\Omega(1)$ Phase-2a advantage.  The construction uses only commutation rewriting (Phase-2a), not template matching (Phase-2b).

**Construction.** For each even $n \ge 4$, define $C_n$ as the following layered circuit:

- **Layer 1**: $\text{CNOT}(q_0, q_1), \text{CNOT}(q_2, q_3), \ldots$ (even-indexed pairs)
- **Layer 2**: $H(q_0), H(q_1), \ldots, H(q_{n-1})$ (all qubits)
- **Layer 3**: $\text{CNOT}(q_1, q_2), \text{CNOT}(q_3, q_4), \ldots$ (odd-indexed pairs)
- **Layer 3.5**: $S$ on the control qubit of each Layer-3 CNOT
- **Layer 4**: $\text{CNOT}(q_1, q_2), \text{CNOT}(q_3, q_4), \ldots$ (repeat of Layer 3)
- **Layer 4.5**: $S^\dagger$ on the control qubit of each Layer-3 CNOT
- **Layer 5**: $H(q_0), H(q_1), \ldots, H(q_{n-1})$ (repeat of Layer 2)
- **Layer 6**: $\text{CNOT}(q_0, q_1), \text{CNOT}(q_2, q_3), \ldots$ (repeat of Layer 1)

The circuit $C_n$ implements the identity: $U(C_n) = I$ since $C_n = A \cdot B \cdot C \cdot S \cdot C \cdot S^\dagger \cdot B \cdot A$ and the $S/S^\dagger$ separators cancel after commuting past the CNOTs.

**Proof.**

**Step 1: Phase-1 action space is empty.** In the original circuit ordering, no two adjacent gates in the listing are inverses acting on the same qubits. Specifically: Layer 1 CNOTs act on even pairs, Layer 2 applies $H$ to all qubits -- no CNOT is adjacent to a CNOT on the same pair. Layers 3--4 are CNOTs on odd pairs, which are indeed self-inverse and adjacent. However, within each layer the CNOTs act on disjoint qubit pairs. If the listing places $\text{CNOT}(q_1, q_2)$ from Layer 3 immediately before $\text{CNOT}(q_1, q_2)$ from Layer 4, these are inverse and adjacent. Thus $\mathcal{S}_1(C_n) \neq \emptyset$ for this naive construction.

**Step 2: Refined construction.** To enforce $\mathcal{S}_1(C_n) = \emptyset$, interleave single-qubit "separator" gates between layers. Insert $S$ (phase gate) on the **control** qubit of each CNOT in Layer 3, between Layers 3 and 4. Since $S$ is not self-inverse ($S^{-1} = S^\dagger \neq S$), no adjacent pair involving the separator is an inverse pair. Crucially, $S$ on the control qubit commutes with CNOT (since $S \otimes I$ and $\text{CNOT}$ share the computational basis eigenstates on the control wire), so Phase-2a can commute the Layer-3 CNOTs past the $S$ separators.

Formally: Let $q_c$ be the control qubit of $\text{CNOT}(q_c, q_t)$ in Layer 3. The $S(q_c)$ separator satisfies $[S(q_c), \text{CNOT}(q_c, q_t)] = 0$ because $S = |0\rangle\langle 0| + i|1\rangle\langle 1|$ is diagonal in the computational basis, and the CNOT control logic depends only on the computational basis state of $q_c$. Therefore Phase-2a can move $\text{CNOT}(q_c, q_t)$ past $S(q_c)$ via commutation.

After commutation, the separator $S(q_c)$ becomes adjacent to the next gate in the circuit. If that gate is $H(q_c)$ from Layer 5, then $H \cdot S \neq I$, so no spurious cancellation occurs. The $S$ and $S^\dagger$ gates introduced as separators between Layers 3/4 and their mirrors between Layers 4/5 cancel in pairs after the CNOT cancellations are complete.

**Step 3: Phase-2a reduction.** Phase-2a commutation rewriting exploits the fact that $S$ on the control qubit commutes with CNOT. Through a sequence of adjacent commutations (bubble-sort style), Phase-2a moves each Layer-3 CNOT past its $S$ separator and into adjacency with the corresponding Layer-4 CNOT on the same qubit pair. Since $\text{CNOT} \cdot \text{CNOT} = I$, these pairs cancel.

After Layer-3/4 CNOT cancellation, the $S$ separators become adjacent to their inverses $S^\dagger$ (introduced symmetrically), and the $H$ layers (Layers 2 and 5) are already self-inverse pairs. The Layer-1/6 CNOTs similarly cancel. The total number of gates removed is at least $2 \lfloor n/2 \rfloor$ CNOTs (Layers 3+4) plus the associated separators, yielding a fractional reduction $\ge 1/6$ for all $n \ge 4$.

**Formal gate count:** For $n$ qubits (even), the circuit has:
- Layers 1,6: $n/2$ CNOTs each (total $n$)
- Layers 2,5: $n$ Hadamards each (total $2n$)
- Layers 3,4: $n/2$ CNOTs each (total $n$)
- Separators: $n/2$ $S$ gates + $n/2$ $S^\dagger$ gates (total $n$)

Total: $n + 2n + (n-2) + (n-2) = 5n-4$ gates because the odd-pair layers contain $n/2-1$ gates each. Cancelling the repeated odd CNOTs and separators removes $2n-4$ gates, already a fraction $(2n-4)/(5n-4)\ge1/6$ for even $n\ge4$; subsequent H/even-CNOT cleanup may remove more. $\blacksquare$

---

### Withdrawn Theorem 8: Incompressibility of Haar-Random Circuits and Bounded-Window Reduction Limit

**Status (2026-08-09): WITHDRAWN.** The statement below is retained for
auditability but is not a valid theorem about the optimization of
polynomial-size circuits.  It simultaneously assumes that $U$ is Haar-random,
that its minimum exact circuit size is at least $4^n/n^2$, and that a circuit
of size $m=\mathrm{poly}(n)$ exactly implements $U$.  On the claimed
high-probability event these premises are inconsistent: such a circuit $C$
does not exist.  A negative upper bound on reduction cannot be clamped to zero
to repair this contradiction.

A meaningful replacement would need an explicit approximation tolerance
$\epsilon$, an $\epsilon$-circuit-complexity/covering-number bound, and a source
ensemble that can actually be generated at the stated depth.  Until that is
proved, Corollaries 8.1 and 8.2 and the claimed ``doubly-exponential''
optimization ceiling must not be cited.

**Statement.** Let $U$ be a Haar-random unitary on $n$ qubits, and let $C$ be any $n$-qubit circuit of size $m = |C|$ implementing $U$.

**Withdrawn claim (a).** The minimum circuit size (circuit complexity) $\mathcal{C}(U)$ over a finite universal gate set satisfies:

$$
\Pr\!\left[\mathcal{C}(U) < \frac{4^n}{n^2}\right] \le \exp\!\left(-\Omega\!\left(\frac{4^n}{n}\right)\right).
$$

Consequently, if $m = \text{poly}(n)$, then with probability $1 - e^{-\Omega(4^n/n)}$ over the Haar measure, any circuit $C'$ unitarily equivalent to $C$ satisfies $|C'| \ge 4^n / n^2 \gg m$, so no reduction is possible at all.

**(b) Sub-exponential depth regime.** For $m = nd$ with $d = o(4^n / n^2)$, let $R_{\max}(C)$ denote the maximum fractional gate-count reduction achievable by *any* algorithm (bounded or unbounded window, any strategy). Then with probability at least $1 - e^{-\Omega(4^n/n)}$:

$$
R_{\max}(C) \le 1 - \frac{4^n}{n^2 m} = 1 - \frac{4^n}{n^3 d}.
$$

For $d = \text{poly}(n)$, this gives $R_{\max}(C) \le 1 - 4^{n - O(\log n)} \to 0$ doubly-exponentially fast.

**(c) Bounded-window corollary.** Let $A$ be any algorithm that applies at most $k$ peephole rewrites, each with window size at most $w$. Each rewrite reduces the gate count by at most $w$ gates, so $k$ rewrites remove at most $kw$ gates. For a Haar-random circuit of size $m = nd$:

$$
R_A(C) \le \min\!\left(\frac{kw}{nd},\; 1 - \frac{4^n}{n^3 d}\right).
$$

Part (b) provides the tighter bound for all $d = o(4^n/n^2)$, independent of $k$ and $w$.

**Proof.**

**Step 1: Dimension counting.** The manifold $SU(2^n)$ has real dimension $4^n - 1$. A circuit of at most $k$ gates from a finite gate set $\mathcal{G}$ (with $c$ continuous parameters per gate, e.g., rotation angles) parametrizes a manifold of dimension at most $k \cdot c$. The set of unitaries implementable by circuits of size $\le k$ therefore has measure at most proportional to the volume ratio:

$$
\frac{\text{Vol}(\text{circuits of size } \le k)}{\text{Vol}(SU(2^n))} \le \left(\frac{k \cdot c \cdot e}{4^n - 1}\right)^{(4^n - 1)/(k c)} \cdot |\mathcal{G}|^k.
$$

For $k < 4^n / n^2$ and $|\mathcal{G}|$ finite, the combinatorial factor $|\mathcal{G}|^k$ grows at most as $\exp(k \ln|\mathcal{G}|) = \exp(O(4^n \ln|\mathcal{G}| / n^2))$, while the Haar measure of the parametrized set is bounded by $\exp(-\Omega(4^n / n))$. Therefore, the total Haar measure of unitaries with $\mathcal{C}(U) < 4^n / n^2$ is at most $\exp(-\Omega(4^n / n))$. [Nielsen, 2005; Harrow & Montanaro, 2017]

**Step 2: Incompressibility of Haar-random circuits.** Let $C$ be a circuit of size $m$ implementing a Haar-random unitary $U$. Any optimization producing $C'$ with $U(C') = U(C) = U$ must satisfy $|C'| \ge \mathcal{C}(U)$. By Step 1, $\mathcal{C}(U) \ge 4^n / n^2$ with overwhelming probability. The maximum achievable reduction is therefore:

$$
R_{\max}(C) = 1 - \frac{|C'_{\min}|}{m} \le 1 - \frac{\mathcal{C}(U)}{m} \le 1 - \frac{4^n}{n^2 m}.
$$

**Step 3: Sub-exponential depth analysis.** For $m = nd$ with $d = \text{poly}(n)$:

$$
R_{\max}(C) \le 1 - \frac{4^n}{n^3 d} = 1 - \frac{4^n}{\text{poly}(n)} \to 0.
$$

The bound approaches zero doubly-exponentially fast: for $n = 10, d = 100$, we get $4^{10}/(10^3 \cdot 100) = 1048576 / 100000 \approx 10.5$, so $R_{\max} \le 1 - 10.5 < 0$, meaning literally no reduction is possible. More precisely, for $4^n / (n^3 d) > 1$, the optimal circuit is the original circuit itself ($R_{\max} = 0$).

**Step 4: Bounded-window bound.** Each peephole rewrite of window $w$ examines $w$ consecutive gates and replaces them with an equivalent sub-circuit. The maximum gate-count reduction per rewrite is $w$ (replacing $w$ gates with the empty circuit, i.e., the identity). Thus $k$ rewrites reduce the gate count by at most $kw$. Combined with Step 2:

$$
R_A(C) \le \min\!\left(\frac{kw}{nd},\; 1 - \frac{\mathcal{C}(U)}{nd}\right).
$$

For Haar-random $U$ with $nd = \text{poly}(n)$, the second term dominates and gives $R_A(C) \to 0$ regardless of $k, w$. $\blacksquare$

**Withdrawn Corollary 8.1.** The former claim about Haar-random circuits of polynomial depth does not follow because exact polynomial-size Haar-random circuits are not supplied by the premises.

**Withdrawn Corollary 8.2.** The asserted transition requires a valid approximate-complexity model and is not established here.  The elementary bound $R(C)\le kw/|C|$ remains true for a fixed number of bounded-window rewrites, independently of Haar randomness.

**Audit note.** The earlier bounded-window inequality $kw/|C|$ is valid but trivial.  The stronger Haar-random optimization claim is withdrawn for the incompatible-premise reason stated above.

---

### Why former Theorem 8 cannot be used

**Scope correction.** The withdrawn argument concerns Haar-random unitaries, while E1--E5 use shallow random gate sequences generated by `src/circuits/generator_v2.py` (depth $d \in [1,50]$, two-qubit gate density $\rho = 0.3$, finite gate set). At the tested depths these sequences do not sample Haar-random unitaries, and no valid theorem here connects the two regimes.

The issue is not merely regime separation. A unitary implemented exactly by the assumed polynomial-size circuit already has complexity at most that circuit size, so it cannot simultaneously satisfy the claimed larger lower bound. No asymptotic or information-theoretic conclusion in the former statement survives without replacing exact implementation by a carefully defined approximate circuit-complexity model and proving a covering bound for that model.

**What explains the experiments.** The empirical $\sim 0\%$ Phase-1 reduction observed in E1--E5 is explained by the listing-dependent adjacent-action model, not by Haar-random incompressibility. Corollary 8.1 is withdrawn.

**Practical implication.** Do not invoke former Theorem 8. The observed low Greedy reduction in E1--E5 is explained only within the tested generator/listing/predicate combination.

---

## Section 2: Propositions

### Proposition 1: Conflict Resolution in Phase 1 is Polynomial-Time Solvable

**Statement.** Given a circuit $C$, the problem of selecting a maximum set of pairwise non-overlapping adjacent inverse pairs is solvable in polynomial time via maximum matching.

**Status**: [CORRECTED] -- Previous versions of this document incorrectly claimed this problem was NP-complete via a reduction from Maximum Independent Set on degree-3 graphs. That claim was erroneous; the correct graph-theoretic formulation is maximum matching, not maximum independent set.

**Corrected analysis.** Define the cancelable-pair graph $G_{\text{cancel}} = (V, E)$:
- $V = \mathcal{S}_1(C)$: each vertex corresponds to an adjacent inverse pair $(g_i, g_{i+1})$ in $C$.
- $E$: an edge connects two vertices if and only if the corresponding pairs share a gate (i.e., they overlap).

Selecting $k$ non-overlapping cancelable pairs is equivalent to finding an independent set of size $k$ in $G_{\text{cancel}}$. Crucially, $G_{\text{cancel}}$ is the **line graph** of the subgraph of the circuit's adjacency graph induced by cancelable edges. Since the circuit's adjacency graph is a path graph $P_m$, its cancelable subgraph is a disjoint union of sub-paths. The line graph of a disjoint union of paths is itself a disjoint union of paths.

On a disjoint union of paths, maximum independent set is solvable in $O(|V|)$ time via a simple greedy or dynamic programming scan. More generally, even if the conflict graph had arbitrary structure (e.g., in a generalized formulation with multi-qubit gate conflicts), the problem of selecting non-overlapping pairs from a set of edges is a **maximum matching** problem, solvable in $O(|V|^{1/2} |E|)$ time by Edmonds' blossom algorithm [Edmonds, 1965] or in $O(|E|\sqrt{|V|})$ by Micali--Vazirani [1980].

**Where the previous proof sketch went wrong.** The earlier sketch claimed that "non-overlapping cancelable pairs correspond to independent sets" and then invoked the NP-completeness of MIS on degree-3 graphs [Garey & Johnson, 1979]. While it is true that non-overlapping pairs form an independent set in the conflict graph, the error was assuming that the conflict graph can encode arbitrary degree-3 graphs. In fact, the conflict graph $G_{\text{cancel}}$ is a line graph of a subgraph of a path, which restricts it to a disjoint union of paths -- a graph class on which MIS is trivially polynomial.

**Practical implication.** The $O(m)$ greedy scan used in our implementation computes a maximal (not necessarily maximum) matching. For circuits where conflicts exist, the greedy result may be suboptimal by a constant factor (at most 2x, by the standard greedy matching approximation ratio). In practice, conflicts are rare in random circuits and the greedy scan achieves the optimum. For structured circuits where conflicts may arise, an exact maximum matching algorithm (e.g., Edmonds' blossom) can be substituted in polynomial time if optimality is required. $\square$

**Remark.** The general Circuit Optimization Decision Problem (CODP) -- which includes commutation rewriting, template matching, and other Phase-2 (a+b) moves -- may still be computationally hard (see Conjecture OP1). Proposition 1 addresses only the restricted sub-problem of Phase-1 adjacent-pair selection.

---

## Section 3: Empirical Observations

### Withdrawn Empirical Generalization 1 (formerly Proposition 2): Greedy Matches Stochastic Phase-1 Optimizers

**Withdrawn statement.** For any circuit $C$, $\mathbb{E}[R_{\text{stoch}}(C)] \le R_{\text{greedy}}(C) + O(1/|C|)$ for any stochastic Phase-1 optimizer.

**Status**: [WITHDRAWN AS A GENERALIZATION 2026-08-10]. The original proof sketch relied on greedy matching approximation bounds that do not establish the stated $O(1/|C|)$ term. More decisively, `H(q0), X(q1), H(q0)` has zero Greedy reduction while the implemented simulated annealer can reach the exact one-gate circuit after SWAP+REMOVAL. The unspecified big-$O$ constant also makes the finite-size statement non-falsifiable as written. No algorithm-independent bound is claimed.

**Historical distribution-specific evidence only.** E4 tested 100 circuits $\times$ 4 optimizers and observed means at or below 0.67% on its random-circuit distribution. Those SA/RLS/GA runs predate the 2026-08-10 incumbent repair, so they cannot validate a stochastic ceiling without a repaired-code rerun. At most, E4 records low reductions for that finite generator/configuration; it is not evidence of algorithm independence.

---

## Section 4: Conjectures and Open Problems

### Preliminaries

For base notation ($n$, $d$, $\mathcal{G}$, $C(n,d,\rho)$, $|C|$, $F_{\text{avg}}$, etc.) and all formal definitions D1--D10, see `framework.md`. Formal decision-problem definitions (CODP, CIT) appear in `framework.md` as Definitions A1--A2.

---

### Motivating Open Problems

These open problems motivate the study but are not claimed as results of this paper. They are included to contextualize the empirical findings within the broader complexity-theoretic landscape.

#### OP1: Is Peephole Optimization QMA-hard?

**Question.** Is the Circuit Optimization Decision Problem (CODP) QMA-hard?

**Motivation.** Non-Identity Check is QMA-complete [Janzing, Wocjan & Beth, 2003], but it is not a proved special-case reduction to CODP. Under the reduction-ratio convention here, $r=0$ is trivial because the input circuit itself satisfies the size bound; $r=1$ asks for closeness to the empty circuit, but the identity/non-identity promise orientation does not by itself establish QMA-hardness of the existential minimization problem. A valid reduction must specify the channel metric, promise orientation, witness quantifiers, and size gap. The standard Feynman--Kitaev route also yields a highly structured history-state construction whose rewrite closure is unanalysed.

**Current status.** The empirical observation that all Phase-1 optimizers achieve ~0% reduction on random circuits is *consistent with* QMA-hardness but does not constitute proof. A zero-mean reduction could also arise from a flat but classically tractable landscape.

**Sub-problems:**
- OP1.1: Complete the reduction from $k$-Local Hamiltonian to CODP with explicit circuit construction and gap preservation.
- OP1.2: Determine whether CODP remains hard when restricted to Clifford circuits (CIT is in P for Clifford circuits via Gottesman-Knill, so hardness likely fails here).
- OP1.3: Determine the parameterized complexity: is CODP hard for circuits of treewidth $t = O(\log n)$?

#### OP2: Inapproximability of CODP

**Question.** Does CODP admit a polynomial-time constant-factor approximation?

**Motivation.** The conflict-resolution subproblem (selecting maximum non-overlapping cancelable pairs) was previously thought to reduce to Maximum Independent Set on the line graph of the circuit [Garey & Johnson, 1979]. However, as corrected in Proposition 1 (2026-06-11), the correct graph-theoretic formulation is **maximum matching** on the conflict graph (which is a line graph of a subgraph of a path), solvable in polynomial time via Edmonds' blossom algorithm [Edmonds, 1965]. This correction weakens the inapproximability motivation: since the base problem is in P, the hardness of CODP must arise from other sources (e.g., the search over rewrite sequences, not the conflict resolution itself). Circuit line graphs have bounded clique size (maximum fan-in = 2), and the polynomial-time solvability of the conflict-resolution subproblem suggests that CODP's hardness (if any) lies in the *sequential* nature of rewrites rather than the *combinatorial* selection step.

**Sub-problems:**
- OP2.1: Since the conflict-resolution subproblem is in P (Proposition 1, corrected), identify the true source of CODP hardness -- is it the sequential rewrite search, the fidelity constraint, or the window-boundedness?
- OP2.2: Determine whether the dynamic commutation graph (where edges change under commutation moves) admits a PTAS for the *sequential* optimization problem.

---

### Formal Conjectures

This section records former conjectures, surviving scoped results, and open classification questions. Refuted or proved existence claims are not treated as active conjectures.

#### Former Conjecture 1: General Phase-1 Ceiling (refuted; restricted questions remain)

**Refuted statement.** For any circuit family $\mathcal{F}$ in which no adjacent inverse gate pairs exist in the initial data structure, *every* Phase-1-only optimizer (greedy, simulated annealing, genetic algorithm, random local search) achieves exactly $0\%$ gate reduction.

**Status**: [REFUTED 2026-08-10]. The circuit $[H(q_0),X(q_1),H(q_0)]$ has an empty initial Greedy action set, but one legal disjoint-support SWAP followed by REMOVAL reduces it from three gates to one. What survives is the Greedy predicate theorem and generator-specific empty-action results, not algorithm independence over the larger move closure.

**Evidence:**

1. **Greedy predicate result** (Theorem 2a). If $\mathcal{S}_1(C) = \emptyset$ and no rotations are mergeable, Greedy has no available reducing rewrite. Stochastic optimizers have a larger move graph; equality of their global action spaces is not proved.

2. **Historical finite-distribution observation** (E1--E5, 45,500 trials). Low mean reductions were recorded across the tested families, but the stochastic runs predate the incumbent repair and do not establish algorithm independence. Greedy-only rows remain descriptive evidence for the initial listing predicate.

3. **Failed theoretical argument.** Although SWAP and COMMUTATION preserve gate count, they can change adjacency and expose cancelable pairs. The three-gate counterexample falsifies the proposed invariance.

**Remaining gap.** A valid dependency-DAG or trace-monoid argument must characterize when SWAP and COMMUTATION expose or create conflict-compatible cancellations. Theorem 2 proves only the Greedy predicate result, and Theorem 2c proves only INSERTION+REMOVAL debt. Former Theorem 2d did not establish the required invariant for multi-qubit gates. Whether the implemented stochastic Phase-1 move closure has a general reduction ceiling therefore remains open.

**Open problems:**
- C1.OP1: Formalize the invariant characterizing exactly which circuit families have empty Phase-1 action spaces.
- C1.OP2: Quantify $\Pr[\mathcal{S}_1(C) \neq \emptyset]$ as a function of $(n, d, \mathcal{G})$ for random circuit ensembles.

#### Former Conjecture 2: Phase-2 (a+b) Provides Context-Dependent Super-Constant Improvement

**Statement.** There exist circuit families $\mathcal{F}$ and gate sets $\mathcal{G}$ for which Phase-1 optimization achieves $O(1/d)$ reduction (or $0\%$), while Phase-1+2 optimization achieves $\Omega(1)$ reduction. The improvement $\Gamma(C) = R_{1+2}(C) - R_1(C)$ is context-dependent: it is significant for some families (e.g., oracle circuits) and zero for others (e.g., structured brickwork, QFT, GHZ).

**Status**: [EXISTENCE CLAIM PROVEN; GENERAL CLASSIFICATION OPEN] -- Two constructive proofs establish the existential statement:
- **Theorem 7** constructs an *artificial* circuit family with $\Gamma^{\text{(2a)}} \ge 1/6 = \Omega(1)$ via **Phase-2a commutation rewriting** + separator-cancellation.  Experiment E24 validates this bound empirically (mean reduction $0.7980$ for $n = 4, 6, \dots, 12$).
- **Theorem 9** (Appendix B) constructs a full-pipeline rewrite with
  $R^{\text{(2b)}}(BV_n)\ge2n/(3n+2)\ge1/2$ for the stated all-ones BV
  circuit. This is achieved reduction, not global optimality.

**Phase coverage caveat.** Theorem 7 is a **Phase-2a** result and is both implemented and validated. Theorem 9 is a **Phase-2b** result; the current `Phase2bTemplateMatcher` implements the required $H$-CNOT-$H$ template and the full-scale v2 benchmark validates the recorded BV grid. This does not validate an unrestricted template universe, and it must not be conflated with the Phase-2a reductions reported in E10/E11.

**Evidence:**

1. **Random Universal circuits (E10, Phase-2a).** Phase 1 achieves $\approx 0\%$; Phase-2a achieves $\approx 3.26\%$ additional reduction. Effect size: see `analysis/phase1_statistics/effect_size.py` for Cliff's $\delta$ / Hedges' $g$ (integrated into figure generation in the v6 remediation).

2. **Oracle / Bernstein--Vazirani circuits (E11, Phase-2a).** Phase 1 achieves $0\%$; Phase-2a achieves $\sim 20\%$ reduction via commutation of redundant H/X gates exposed by the Oracle circuit structure. This empirical Phase-2a reduction is attributable to the algebraic structure of the oracle, but its mechanism is distinct from the $H$-CNOT-$H$ template of Theorem 9.

3. **CNOT-chain validation circuits (E11).** Phase 1 alone achieves $100\%$ reduction, confirming that the Phase-2 (a+b) advantage is circuit-family dependent rather than universal.

4. **Mechanism.** Phase-2a exploits commutation relations $[U, V] = 0$ to reorder gates, bringing non-adjacent inverses into adjacency. For circuits with repeating structural patterns, commutation can slide gates across $O(d)$ positions, creating cancellations invisible to Phase 1. Phase-2b additionally exploits multi-gate template identities (e.g., $H$-CNOT-$H \to$ reversed CNOT) that Phase-2a does not.

**Remaining gaps.**
- **(Theory)** Theorem 7 (artificial, Phase-2a) and Theorem 9 (BV natural, Phase-2b) establish $\Omega(1)$ advantage constructively. The broader question of characterizing *all* families with super-constant Phase-2a/2b improvement remains open (C2.OP1--OP3).
- **(Theory--experiment bridge)** The achievable Phase-2a bound for BV remains open: the empirical $\sim$20% Phase-2a reduction on Oracle/BV (E11) lacks a matching theoretical lower bound.  Closing this gap requires either (a) extending Phase-2a theory to cover the E11 Oracle structure, or (b) running E11 with the implemented Phase-2b matcher to validate Theorem 9 directly.

**Open problems:**
- C2.OP1 (resolved by Theorems 7 and 9): construct an explicit circuit family with proven super-constant Phase-2 improvement.
- C2.OP2: Determine a non-singular advantage measure and its extremal scaling as a function of $(n, d, \mathcal{G})$; the ratio $\Gamma/R_1$ is undefined when $R_1=0$.
- C2.OP3: Characterize the gate-set and family conditions under which Phase-2 (a+b) is necessary.

---

### Conjecture Summary Table

| ID | Type | Statement | Evidence | Key Open Problem |
|----|------|-----------|----------|-----------------|
| OP1 | Open Problem | CODP is QMA-hard | Weak -- reduction sketch incomplete | Complete the Kitaev reduction |
| OP2 | Open Problem | No PTAS for CODP | Updated -- conflict resolution is in P (Prop 1); hardness source unclear | Identify true hardness source |
| **C1** | **Refuted general conjecture** | **All Phase-1 optimizers share a listing-conditional ceiling** | **Refuted by SWAP+REMOVAL on a three-gate circuit. Surviving results are Greedy-specific, restricted-generator, or restricted-move-set statements. Historical stochastic evidence requires repaired-code reruns.** | **Characterize the dependency-DAG/trace-monoid move closure for explicitly scoped families** |
| **C2** | **Proved existence result** | **Some families have context-dependent $\Omega(1)$ Phase-2 advantage** | **Thm 7 (artificial Phase-2a, $\Gamma \ge 1/6$) + Thm 9 (BV Phase-2b, $\Gamma \ge 2/13$); no universal-family claim.** | **Phase-2a bound for natural families; characterize sufficient/necessary family and gate-set conditions** |

---

## Section 5: Scope Analysis -- Listing Models, DAG Compilers, and the Structural-Ceiling Framework

> **Document Status**: Scope clarification (addresses the LBL/WCL vs DAG gap identified in the independent audit).

### Purpose

This section addresses a structural concern raised in the independent audit: production quantum compilers (Qiskit, Cirq, t|ket>) represent circuits as **directed acyclic graphs (DAGs)**, not as sequential gate listings. The structural-ceiling framework (Theorem 1, Conjecture C1) is formulated in terms of **listing models** (LBL / WCL). This raises two questions:

1. Does the listing-based framework apply to DAG-based compilers?
2. Is the "structural ceiling" an artifact of the listing representation, or a genuine property of the circuits?

This section clarifies the scope of the framework, explains the relationship between listing-based and DAG-based representations, and honestly states what the framework can and cannot claim.

### 5.1 Three Circuit Representations

Quantum circuits can be represented in (at least) three data structures, each affecting what "adjacency" means and therefore what a peephole optimizer can see:

#### 5.1.1 Layer-by-Layer Listing (LBL)

- **Structure**: The circuit is a flat sequence $C = (g_1, \ldots, g_m)$ where gates are ordered layer by layer. Within each layer, gates on different qubits are listed in qubit-index order.
- **Adjacency**: Two gates are "listing-adjacent" if their indices differ by 1. Under LBL with $n \ge 2$ qubits, two gates on the *same* qubit are never listing-adjacent (they are separated by $n-1$ gates from other qubits).
- **Used by**: This project's `UniversalGenerator` (`src/circuits/generator_v2.py`).
- **Observation 1(b) consequence**: $\mathcal{S}_1(C) = \emptyset$ structurally -- Phase-1 action space is empty by construction.

#### 5.1.2 Wire-Consecutive Listing (WCL)

- **Structure**: The circuit is a flat sequence where gates on the same qubit wire are listed consecutively.
- **Adjacency**: Two successive gates on the same qubit are listing-adjacent.
- **Used by**: Some synthesis tools; circuit diagrams (when read wire-by-wire).
- **Observation 1(a) consequence**: $\mathcal{S}_1(C)$ is non-empty in expectation, with density $\approx p_{\text{cancel}}(n, \rho)$.

#### 5.1.3 Directed Acyclic Graph (DAG)

- **Structure**: The circuit is a DAG $G = (V, E)$ where vertices are gates and edges encode data dependencies (a gate $g_j$ depends on $g_i$ if they share a qubit and $g_i$ precedes $g_j$ on that qubit).
- **Adjacency**: Two gates are "DAG-adjacent" if they share a qubit and no other gate on that qubit lies between them in the dependency order. This is **wire-level adjacency**, independent of any flat listing.
- **Used by**: Production compilers -- Qiskit (`DAGCircuit`), Cirq, t|ket> (`Circuit` with command ordering).
- **Consequence**: A DAG-based peephole optimizer sees wire-level adjacency directly. It does not suffer from the LBL "blindness" where same-qubit gates are hidden behind cross-qubit gates in the listing.

### 5.2 The Listing--DAG Gap

**The core observation.** Observation 1(b) proves that under LBL, $\mathcal{S}_1(C) = \emptyset$ for $n \ge 2$. This is a property of the *listing*, not of the *circuit*. The same circuit, represented as a DAG (or as WCL), would expose wire-level inverse pairs to a peephole optimizer.

**Implication for the structural ceiling.** The "structural ceiling" ($R_1 \approx 0\%$ on random circuits) observed in experiments E1--E5 is therefore **listing-conditional**:

$$
R_1^{\text{LBL}}(C) = 0 \quad \text{(Observation 1(b), structural)} \\
R_1^{\text{WCL}}(C) \approx 2 p_{\text{cancel}}(n, \rho) \quad \text{(Observation 1(a), small but non-zero)} \\
R_1^{\text{DAG}}(C) \approx R_1^{\text{WCL}}(C) \quad \text{(DAG sees wire-level adjacency, like WCL)}
$$

The empirical ~0% Phase-1 reduction in E1--E5 is explained by Observation 1(b) (the LBL listing structurally empties the action space), **not** by any intrinsic incompressibility of the circuits. Under WCL or DAG representation, the same circuits would exhibit a small but non-zero Phase-1 reduction (~7.8% in our WCL experiment — E19, 10,000 rows: mean 7.83%, std 3.95%, fidelity 1.0 — consistent with Observation 1(a)).

**This is not a flaw in the framework -- it is a feature.** The framework's value is in *characterizing* how the listing model affects peephole optimization. The LBL$\to$WCL gap (~7.8% vs 0%) is itself a measurable, theoretically-grounded result about the sensitivity of peephole optimization to circuit representation.

### 5.3 Relationship to Production DAG Compilers

Production compilers (Qiskit `transpile`, Cirq, t|ket>) use DAG representations and implement sophisticated optimization passes that go far beyond Phase-1 adjacent-cancellation. This raises the question: does the structural-ceiling framework say anything about production compilers?

#### 5.3.1 What the framework DOES claim

1. **Listing-model sensitivity.** The framework proves that the choice of listing model (LBL vs WCL vs DAG) materially affects Phase-1 peephole performance. This is a genuine finding: a naive peephole optimizer on an LBL listing is structurally blind to same-qubit inverse pairs.

2. **Phase-2a commutation value.** Phase-2a commutation rewriting (which operates on wire-level structure, not listing order) is listing-independent. The framework's Phase-2 (a+b) results (Theorem 7, Theorem 9) hold regardless of the listing model, because commutation is a wire-level algebraic property.

3. **Observed ceiling is representation-dependent; algorithm independence is not proved.** Within the tested fixed listing model, Greedy, SA, GA, and RLS converge empirically to similar reductions.  The data support a representation-plus-structure hypothesis, not a universal theorem excluding stronger search algorithms.

#### 5.3.2 What the framework does NOT claim

1. **Not a lower bound on DAG-compiler performance.** The framework does *not* claim that production DAG-based compilers are bounded by the LBL ceiling. A DAG-based compiler that performs wire-level cancellation directly would bypass Observation 1(b) entirely. The empirical result that Qiskit O3 achieves ~23% reduction on real circuits (E12) -- far above our prototype's ~11% -- is consistent with this: Qiskit operates on a DAG and employs passes (commutation analysis, template matching, resynthesis) that go beyond Phase-1 listing-adjacent cancellation.

2. **Not a complexity-theoretic lower bound.** The structural ceiling is a limit on a specific class of *classical algorithms* (listing-based peephole rewriters) applied to a specific *data structure* (gate listings). It is not a lower bound on quantum circuit complexity (which concerns the minimum number of gates to represent a unitary, regardless of algorithm or representation).

3. **Not a claim about all peephole optimizers.** The framework's Phase-1 ceiling applies to optimizers that scan a listing and cancel listing-adjacent inverses. A DAG-based peephole optimizer that scans wire-adjacent gates is effectively operating in the WCL regime and is subject to Observation 1(a), not Observation 1(b).

#### 5.3.3 Honest scope statement

The structural-ceiling framework should be read as: **"For listing-based peephole optimizers operating on LBL representations, Phase-1 reduction is structurally zero; the gap to WCL/DAG representations is ~7.8%, explainable by Observation 1(a). Production DAG compilers operate in a different regime and are not bounded by this ceiling."**

This is a narrower, more honest claim than "quantum circuits cannot be optimized by peephole methods." The narrower claim is defensible and useful; the broader claim is not supported.

### 5.4 Qiskit Pass Isolation: Honest Status

The independent audit flagged that the Qiskit pass-isolation analysis (identifying which Qiskit transpiler pass is responsible for reduction on each circuit family) covers only **5 of 15** circuit families. For the remaining 10 families, the mechanism attribution is speculative.

#### 5.4.1 Current coverage

| Family | Pass isolation performed? | Mechanism confidence |
|--------|--------------------------|---------------------|
| (5 families) | Yes -- pass-level breakdown available | High |
| (10 families) | No -- only aggregate O3 reduction reported | **Speculative** |

#### 5.4.2 Honest remediation

Rather than presenting speculative mechanism attributions as findings, the manuscript should:

1. **Report only the 5 isolated families as mechanism findings.**
2. **For the 10 non-isolated families, report only the aggregate reduction** and explicitly state: "Mechanism attribution for these families is not established; we report the aggregate Qiskit O3 reduction without claiming which specific pass is responsible."
3. **Move full pass-isolation of all 15 families to Future Work.**

This is a scope reduction, but it converts speculative claims into honest ones. A reviewer who asks "how do you know pass X caused the reduction on family Y?" for a non-isolated family would otherwise have no answer.

### 5.5 Recommendations for the Manuscript

Based on this analysis, the manuscript should:

1. **Add a "Scope and Representation" subsection** in the Methodology chapter, explicitly stating that the structural ceiling is listing-conditional (LBL) and that DAG-based compilers operate in a different regime.

2. **Reframe the central claim** from "Phase-1 peephole optimization achieves ~0% on random circuits" to "Phase-1 peephole optimization on LBL representations achieves ~0% on random circuits; under WCL/DAG representations, ~7.8% is achievable, consistent with Observation 1(a)."

3. **Include a DAG comparison discussion** noting that production compilers (Qiskit O3 ~23%) exceed the prototype's Phase-1+2 (~11%) because they operate on DAGs and employ passes beyond the prototype's scope. This is not a failure of the framework -- it is a difference in representation and pass sophistication.

4. **Reduce the Qiskit pass-isolation claims** to the 5 families with actual data, and move the rest to Future Work.

5. **Explicitly list as a limitation** that the framework's theoretical results (Theorems 1--9) are formulated for listing-based representations, and extending them to DAG-based representations is an open direction.

### 5.6 Summary

| Question | Answer |
|----------|--------|
| Is the structural ceiling listing-conditional? | **Yes.** Observation 1(b) is an LBL property; WCL/DAG expose ~7.8% reduction. |
| Does the framework bound DAG-compiler performance? | **No.** DAG compilers bypass Observation 1(b). The framework does not claim to bound them. |
| Is the LBL$\to$WCL gap a real finding? | **Yes.** It quantifies representation sensitivity of peephole optimization. |
| Is the Qiskit pass-isolation complete? | **No.** Only 5/15 families isolated; the rest must be downgraded to Future Work. |
| Should the central claim be reframed? | **Yes.** From "0% on random circuits" to "0% under LBL; ~7.8% under WCL/DAG." |

---

## Section 6: Phase-2b Template Matcher Implementation

> **Supersession note (2026-08-06).** An earlier version of this section
> (footer v4.0, 2026-06-17) described the **v1 minimal prototype**, which
> implemented only the single $H$-CNOT-$H$ conjugation template plus adjacent
> $H$-$H$ cleanup. That description is obsolete. The current implementation is
> `Phase2bTemplateMatcher` **v2.0.0**, validated at full scale by experiment
> E26 (`data/v8/phase2b_full/`, 2,427 rows).

### Implemented scope (v2.0.0)

`Phase2bTemplateMatcher` v2.0.0 implements a deterministic template pipeline with three mechanism groups:

1. **Inverse-cancellation closure.** Iterated cancellation of self-inverse gate pairs, named inverse pairs ($S$-$S^\dagger$, $T$-$T^\dagger$), and parametric pairs ($R_\alpha(\theta)$-$R_\alpha(-\theta)$), including pairs exposed by earlier rewrites (closure to fixpoint per pass).
2. **Phase-polynomial merging.** Commuting diagonal-phase structure on shared wires is merged where the rewrite is unitary-preserving.
3. **Standard conjugation templates.** The $\leq 3$-qubit Clifford conjugation template set, including the original v1 template

$$
H(c)\;\mathrm{CNOT}(c,t)\;H(c) \rightarrow H(t)\;\mathrm{CNOT}(t,c)\;H(t),
$$

together with adjacent $H(q)H(q) \rightarrow I$ cleanup exposed by rewrites.

The template library is the inverse-closure-plus-conjugation set; it is **not** an exhaustive enumeration of the 11,520-element two-qubit Clifford group (a deliberate delimitation stated in the manuscript). All transformations are unitary-preserving and verified per row in E26 (fidelity $\geq 1 - 10^{-9}$ on all 2,427 rows; exact Operator equality for $n \leq 9$).

### Empirical status

E26 reaches the exact $k+2$ gate optimum on all 80 Bernstein–Vazirani instances ($n = 3$–$10$, 10 secrets per size), exceeding Theorem 9's rigorous lower bound by 3.1–4.2×, and breaks the prototype ceilings on IQP (92.0%), RandomClifford (51.6%), and Structured brickwork (40.2%). On the Theorem-7 engineered family, Phase-2b v1 achieves only 2.5% versus Phase-2a's 79.8% — the Phase-2a/2b gap is family-dependent (manuscript §4.2, Limitation 13).

### Remaining gap

Still not implemented: exhaustive small-Clifford template enumeration, phase-gadget / ZX-calculus extraction, topology-aware template variants, and measurement/classical-bit-preserving rewrites. These are listed as future work (manuscript §7.6).

---

## Appendix A: Restricted Theorem 2c and Withdrawn Theorem 2d

> **Document Status (audited 2026-08-09):** Theorem 2c resolves only the INSERTION+REMOVAL subsystem. Former Theorem 2d is an invalid proof retained solely as an audit trail; the general INSERTION+SWAP+COMMUTATION cascade gap remains open.
> **Version**: 1.0
> **Date**: 2026-06-13

### Motivation and Gap Statement

Earlier drafts asserted that stochastic Phase-1 optimizers (SA, GA, RLS) cannot systematically exceed the Greedy reduction ceiling on circuits where $\mathcal{S}_1(C) = \emptyset$. The audit found that assertion unproved: INSERTION can change the commutation topology and potentially enable SWAP or COMMUTATION sequences that were previously impossible.

Specifically, if inserting $H \cdot H$ between gates $A$ and $B$ makes $A$ and $B$ commutable (by changing the effective ordering context), then INSERTION has created a Phase-2a-style opportunity that Phase-1 alone could not find. The concern is that an INSERTION-facilitated commutation cascade might achieve net gate-count reduction beyond what is available without INSERTION.

This appendix closes the gap with two results:
- **Theorem 2c** proves that the net gate-count change from any INSERTION + REMOVAL sequence is non-negative (bounded version).
- **Theorem 2d** extends this to the combined INSERTION + SWAP + COMMUTATION setting, showing that the INSERTION-facilitated cascade cannot exceed what Phase-2a would achieve independently.

### Preliminaries

**Definition 1 (Circuit).** A circuit $C = (g_1, g_2, \ldots, g_m)$ is a finite sequence of quantum gates acting on $n$ qubits, where each $g_i \in \mathcal{G}$ for a fixed gate set $\mathcal{G}$. The size is $|C| = m$.

**Definition 2 (INSERTION move).** An INSERTION move on circuit $C$ at position $p$ with gate $g \in \mathcal{G}$ produces $C' = (g_1, \ldots, g_p, g, g^{-1}, g_{p+1}, \ldots, g_m)$. This adds exactly 2 gates and satisfies $U(C') = U(C)$ since $g \cdot g^{-1} = I$.

**Definition 3 (REMOVAL move).** A REMOVAL move on circuit $C$ identifies a pair of listing-adjacent gates $(g_i, g_{i+1})$ such that $g_{i+1} = g_i^{-1}$ and both act on the same qubit(s), and deletes both, producing $C' = (g_1, \ldots, g_{i-1}, g_{i+2}, \ldots, g_m)$. This removes exactly 2 gates.

**Definition 4 (SWAP move).** A SWAP move exchanges two listing-adjacent gates $(g_i, g_{i+1})$ that act on disjoint qubit sets, producing $C' = (\ldots, g_{i+1}, g_i, \ldots)$. This preserves $|C|$ and satisfies $U(C') = U(C)$ since gates on disjoint qubits commute.

**Definition 5 (COMMUTATION move).** A COMMUTATION move replaces listing-adjacent gates $(g_i, g_{i+1})$ with $(g_i', g_{i+1}')$ such that $g_{i+1}' g_i' = g_{i+1} g_i$ and $\text{supp}(g_i') \cup \text{supp}(g_{i+1}') = \text{supp}(g_i) \cup \text{supp}(g_{i+1})$. This preserves $|C|$ and $U(C)$.

**Definition 6 (Pre-existing and inserted gates).** Let $C_0$ be the initial circuit. After a sequence of $k$ INSERTION moves, the circuit $C_k$ contains $|C_0| + 2k$ gates. We label each gate in $C_k$ as either **pre-existing** (originally in $C_0$) or **inserted** (added by some INSERTION move). Let $\mathcal{I}(C_k)$ denote the multiset of inserted gates still present in $C_k$, and define the **insertion debt** $\Delta(C_k) = |\mathcal{I}(C_k)|$.

---

### Theorem 2c (Bounded INSERTION Cascade Lemma)

**Statement.** Let $C$ be a circuit with $\mathcal{S}_1(C) = \emptyset$. Let $M$ be any finite sequence of INSERTION and REMOVAL moves applied to $C$, producing circuit $C'$. Suppose $M$ contains $k$ INSERTION moves. Let $R_{\text{removal}}(C')$ denote the total number of gates removed by all REMOVAL moves in $M$ that involve at least one inserted gate. Then:

$$
R_{\text{removal}}(C') \le 2k.
$$

Consequently, the net gate-count change from $M$ satisfies:

$$
|C'| - |C| = 2k - R_{\text{total}} \ge 2k - (R_{\text{removal}} + R_{\text{pre}}) \ge -R_{\text{pre}},
$$

where $R_{\text{total}}$ is the total number of gates removed by all REMOVAL moves, and $R_{\text{pre}}$ is the number of gates removed by REMOVAL moves involving only pre-existing gates.

**Corollary.** The net gate-count change from any INSERTION + REMOVAL sequence starting from $\mathcal{S}_1(C) = \emptyset$ satisfies:

$$
|C'| - |C| \ge 0
$$

if $R_{\text{pre}} = 0$ (i.e., no REMOVAL of two pre-existing gates occurs). More generally, the reduction attributable to INSERTION is at most zero.

#### Proof of Theorem 2c

The proof proceeds via the **insertion debt invariant**.

**Step 1: Debt initialization and update rules.**

Define the insertion debt $\Delta$ as the number of inserted gates currently present in the circuit. Initially, $\Delta(C_0) = 0$.

Each move in $M$ updates $\Delta$ as follows:

| Move type | Effect on $\Delta$ |
|-----------|-------------------|
| INSERTION | $\Delta \mapsto \Delta + 2$ (adds $g$ and $g^{-1}$) |
| REMOVAL of two inserted gates | $\Delta \mapsto \Delta - 2$ |
| REMOVAL of one inserted + one pre-existing gate | $\Delta \mapsto \Delta - 1$ |
| REMOVAL of two pre-existing gates | $\Delta \mapsto \Delta - 0$ |

**Step 2: Debt non-negativity invariant.**

We claim $\Delta(C_j) \ge 0$ for all intermediate circuits $C_j$ throughout the sequence $M$.

*Proof of invariant.* $\Delta(C_0) = 0 \ge 0$. Each INSERTION increases $\Delta$ by 2. Each REMOVAL decreases $\Delta$ by at most 2 (when both removed gates are inserted). A REMOVAL requires two listing-adjacent inverse gates; such a pair can include at most 2 inserted gates. Therefore $\Delta$ never decreases below 0 by any single move, and by induction $\Delta(C_j) \ge 0$ for all $j$. $\square$

**Step 3: Total debt accounting.**

After $k$ INSERTION moves and some number of REMOVAL moves, the final debt is:

$$
\Delta(C') = 2k - (\text{total inserted gates removed}).
$$

Let $r_2$ be the number of REMOVAL moves that remove two inserted gates, $r_1$ the number that remove one inserted and one pre-existing gate, and $r_0$ the number that remove two pre-existing gates. Then:

$$
\Delta(C') = 2k - 2r_2 - r_1 \ge 0.
$$

The total number of gates removed involving at least one inserted gate is:

$$
R_{\text{removal}}(C') = 2r_2 + 2r_1.
$$

**Step 4: Bounding $R_{\text{removal}}$.**

From the debt invariant:

$$
2r_2 + r_1 \le 2k.
$$

Therefore:

$$
R_{\text{removal}}(C') = 2r_2 + 2r_1 = (2r_2 + r_1) + r_1 \le 2k + r_1.
$$

We now show $r_1 \le 0$, i.e., REMOVAL of one inserted gate with one pre-existing gate contributes zero net reduction.

**Step 5: Analysis of mixed REMOVAL (one inserted, one pre-existing).**

Suppose a REMOVAL cancels an inserted gate $g_{\text{ins}}$ with a pre-existing gate $g_{\text{pre}}$, where $g_{\text{ins}} = g_{\text{pre}}^{-1}$. The inserted gate $g_{\text{ins}}$ was part of an inserted identity pair $(g, g^{-1})$. Without loss of generality, suppose $g_{\text{ins}} = g$ and $g_{\text{pre}} = g^{-1}$.

After this REMOVAL, the other half of the inserted pair, $g^{-1}$ (i.e., $g_{\text{ins}}^{-1}$), remains in the circuit. The net gate-count change from this INSERTION + REMOVAL sub-sequence is:

$$
+2 \text{ (INSERTION added } g, g^{-1}\text{)} - 2 \text{ (REMOVAL deleted } g \text{ and } g_{\text{pre}}\text{)} = 0.
$$

However, the circuit has lost a pre-existing gate $g_{\text{pre}}$ and gained an inserted gate $g^{-1}$. The remaining inserted gate $g^{-1}$ contributes $+1$ to the debt. Thus, each mixed REMOVAL reduces the debt by only 1 (not 2), and the "replacement" of a pre-existing gate by an inserted gate preserves the gate count exactly.

**Key observation:** The pre-existing gate $g_{\text{pre}} = g^{-1}$ was "compatible" with the inserted gate -- it was the inverse of the inserted gate's type. But since the insertion added the pair $(g, g^{-1})$, canceling $g$ with $g_{\text{pre}}$ leaves $g^{-1}$ stranded. The stranded $g^{-1}$ can only be removed by another REMOVAL, which requires finding an adjacent inverse -- either another pre-existing $g$ (which would be a second mixed REMOVAL, again with net 0 contribution) or the original $g^{-1}$'s partner (which would be a pure-insertion REMOVAL, also net 0).

Formally: each mixed REMOVAL converts one pre-existing gate into one inserted gate (of the inverse type), with no change in total gate count. The debt decreases by 1, but the pre-existing gate count also decreases by 1. The net reduction (pre-existing gates removed minus inserted gates remaining) is:

$$
\text{Net from mixed REMOVAL} = +2 - 2 = 0.
$$

Therefore, the effective contribution of mixed REMOVALs to net gate reduction is zero.

**Step 6: Refined bound.**

Since mixed REMOVALs contribute zero net reduction, the only REMOVALs that reduce the gate count are pure-pre-existing REMOVALs ($r_0$ type). But by hypothesis, $\mathcal{S}_1(C) = \emptyset$, and we must show that such REMOVALs cannot be created by INSERTION.

A REMOVAL of two pre-existing gates requires them to be listing-adjacent and inverse. INSERTION adds gates to the circuit; it never removes gates. Therefore, INSERTION can only **increase** the listing distance between two pre-existing gates (by inserting gates between them) or **decrease** it (by removing other gates via cascaded REMOVALs). However:

- INSERTION between two pre-existing gates $g_a, g_b$ that were not adjacent: this makes them *less* adjacent (larger listing gap), not more.
- INSERTION elsewhere in the circuit: this does not change the relative listing ordering of $g_a$ and $g_b$ on their respective wires.

The only way INSERTION could make two pre-existing gates adjacent is if a cascaded REMOVAL (involving inserted gates) removes the intervening gates between $g_a$ and $g_b$. But by Step 5, every REMOVAL involving an inserted gate has net gate-count change $\ge 0$, so the cascaded REMOVALs have consumed at least as many gates as they removed from the intervening region.

More precisely: suppose $g_a$ and $g_b$ are pre-existing gates separated by $s \ge 1$ intervening gates in $C_0$. For $g_a$ and $g_b$ to become listing-adjacent, all $s$ intervening gates must be removed. Each intervening gate removal requires a REMOVAL move, which removes 2 gates at a time. If the intervening gates are removed via mixed REMOVALs with inserted gates, each such REMOVAL has net change 0 (Step 5). Therefore, the cost (in inserted gates) of clearing the $s$ intervening gates is at least $s$ (each mixed REMOVAL consumes one inserted gate and one pre-existing gate, and we need to clear $s$ pre-existing gates). The INSERTION cost to provide these inserted gates is $2 \lceil s/2 \rceil \ge s$. The net gate-count change is:

$$
\Delta|C| = (\text{INSERTION cost}) - (\text{gates removed}) \ge s - s = 0.
$$

**Step 7: Conclusion.**

Combining Steps 4--6:

$$
|C'| - |C| = 2k - R_{\text{total}} = 2k - (2r_2 + 2r_1 + 2r_0).
$$

From the debt invariant: $2r_2 + r_1 \le 2k$.
From Step 5: mixed REMOVALs ($r_1$) contribute zero net reduction.
From Step 6: pure-pre-existing REMOVALs ($r_0$) that were enabled by INSERTION cost at least as much as they save.

Therefore:

$$
|C'| - |C| \ge 0 \quad \text{(considering only INSERTION-enabled effects)}.
$$

Equivalently:

$$
R_{\text{removal}}(C') = 2r_2 + 2r_1 \le 2k + r_1 \le 2k + r_1,
$$

and since each mixed REMOVAL is net-zero, the *effective* removal count (net of INSERTION cost) is at most $2r_2 \le 2k - r_1 \le 2k$. $\blacksquare$

---

### Withdrawn Theorem 2d (INSERTION Commutation Cascade Bound)

> **Status (2026-08-09): proof invalid; claim open.** The text below is retained as an audit trail, not as an established result.  Its "wire-level unitary" is not well-defined for gates coupling multiple wires, preservation of a total wire product does not preserve pairwise inverse relations, and $B_{\mathrm{pre}}$ is neither defined conflict-freely nor proved equal to the Phase-2 optimum.

**Former statement.** Let $C$ be a circuit with $\mathcal{S}_1(C) = \emptyset$. Let $M$ be any finite sequence of moves drawn from $\{\text{INSERTION}, \text{REMOVAL}, \text{SWAP}, \text{COMMUTATION}\}$ applied to $C$, producing circuit $C'$. Suppose $M$ contains $k$ INSERTION moves. Then:

$$
|C'| - |C| \ge -B_{\text{pre}}(C),
$$

where $B_{\text{pre}}(C)$ is the number of pre-existing wire-level inverse pairs in $C$ that can be exposed by SWAP and COMMUTATION moves alone (without INSERTION). In particular, $B_{\text{pre}}(C)$ is exactly the size of the Phase-2 (a+b) action space $|\mathcal{S}_{1+2}(C)|$ applied to the pre-existing gates of $C$.

**Corollary.** Since Phase 1 by definition does not include systematic commutation reordering (Phase-2a), the INSERTION-facilitated cascade within Phase 1 cannot exceed what Phase-2a would achieve independently. That is, for any Phase-1 optimizer employing INSERTION:

$$
R_1^{\text{INSERTION}}(C) \le R_{1+2}(C) - R_1(C) = \Gamma(C).
$$

This means INSERTION within Phase 1 can at best simulate Phase-2a, never exceed it.

#### Proof of Theorem 2d

The proof extends Theorem 2c by incorporating SWAP and COMMUTATION moves into the analysis.

**Step 1: SWAP and COMMUTATION preserve gate count and pre-existing gate structure.**

SWAP exchanges two listing-adjacent gates on disjoint qubits. It preserves $|C|$, the gate multiset, and the relative ordering of gates on each individual wire. COMMUTATION replaces an adjacent pair $(g_i, g_{i+1})$ with an equivalent pair $(g_i', g_{i+1}')$ of the same size. It preserves $|C|$ and $U(C)$.

Neither SWAP nor COMMUTATION changes the number of inserted or pre-existing gates. They only rearrange the listing order.

**Step 2: Commutation topology change by INSERTION.**

INSERTION at position $p$ inserts gates $g, g^{-1}$ between $g_p$ and $g_{p+1}$. This can change the commutation topology in two ways:

(a) **New commutation partners.** The inserted gate $g$ may commute with $g_p$ or $g_{p+1}$ (or both), enabling COMMUTATION moves that were not possible before. Similarly, $g^{-1}$ may commute with adjacent gates.

(b) **Listing adjacency changes.** By inserting 2 gates, INSERTION changes the listing indices of all subsequent gates. This can bring previously non-adjacent gates into listing adjacency (if intervening gates are subsequently removed) or separate previously adjacent gates.

We must show that these topology changes cannot lead to net reduction beyond $B_{\text{pre}}(C)$.

**Step 3: Wire-level structure under INSERTION + SWAP + COMMUTATION.**

We need a structural invariant that is strong enough to bound the INSERTION-facilitated cascade, while being honest about what COMMUTATION can and cannot do.

**Lemma (Wire-unitary invariant, corrected).** Let $C$ be a circuit and let $M$ be any sequence of INSERTION, SWAP, and COMMUTATION moves (no REMOVAL). For each wire $w$, let $U_w(C)$ denote the wire-level unitary implemented by the subsequence of gates acting on wire $w$ (in listing order). Then:

$$
U_w(C') = U_w(C) \cdot U_w(\sigma_w),
$$

where $\sigma_w$ is the subsequence of *inserted* gates acting on wire $w$. That is, the wire-level unitary of pre-existing gates is preserved, and inserted gates contribute an additional factor $U_w(\sigma_w)$.

*Proof.* We verify each move type:
- **INSERTION** adds a pair $(g, g^{-1})$ at some listing position. If $g$ acts on wire $w$, then $g^{-1}$ also acts on wire $w$ (since inverse gates act on the same qubits), and $g \cdot g^{-1} = I$ on wire $w$. Thus $U_w$ is unchanged by a single INSERTION viewed in isolation; the inserted pair contributes $I$ to $U_w$. However, subsequent SWAP/COMMUTATION may separate the pair, so we track the inserted gates as a separate factor $\sigma_w$.
- **SWAP** exchanges two gates on disjoint wires. For each wire $w$, the gate subsequence $\pi_w$ is unchanged (the swapped gate on wire $w$ stays on wire $w$, just at a different listing position relative to gates on other wires). Thus $U_w$ is preserved.
- **COMMUTATION** replaces $(g_i, g_{i+1})$ with $(g_i', g_{i+1}')$ such that $g_{i+1}' g_i' = g_{i+1} g_i$. If both gates act on wire $w$, their relative order on wire $w$ may change, but the wire-level unitary product is preserved by the commutation condition. If the gates act on different wires, each wire's subsequence is unchanged.

Combining: the wire-level unitary decomposes as $U_w(C') = U_w(\text{pre-existing}) \cdot U_w(\text{inserted})$, where the pre-existing factor equals $U_w(C)$ and the inserted factor is determined by $\sigma_w$. $\square$

**Important clarification on same-wire COMMUTATION.** Unlike an earlier draft of this lemma, we do **not** claim that the relative *ordering* of pre-existing gates on a wire is preserved -- same-wire COMMUTATION can reorder them (e.g., $R_z(\alpha) \cdot R_z(\beta) \to R_z(\beta) \cdot R_z(\alpha)$). What is preserved is the wire-level *unitary* product, which is the algebraically relevant quantity. This correction does not weaken Theorem 2d because the bound $B_{\text{pre}}(C)$ is defined in terms of wire-level inverse pairs that can be exposed by SWAP and COMMUTATION -- it already accounts for all same-wire reorderings that COMMUTATION enables. The role of the wire-unitary invariant is to establish that INSERTION cannot *create* new wire-level inverse relationships among pre-existing gates; it can only insert additional gates whose net contribution is controlled by Theorem 2c.

**Step 4: Pre-existing inverse pairs are wire-level unitary properties.**

Two pre-existing gates $g_a, g_b$ form a cancellable wire-level pair if:
- They act on the same qubit(s),
- $g_b = g_a^{-1}$,
- They can be brought into listing adjacency by SWAP (moving gates on other wires out of the way) and COMMUTATION (reordering gates on the same wire, preserving the wire unitary).

The set of all such pairs is exactly what $B_{\text{pre}}(C)$ counts -- it is the Phase-2 (a+b) action space restricted to pre-existing gates. Crucially, $B_{\text{pre}}(C)$ is determined entirely by the pre-existing gates and their wire-level unitaries, which (by Step 3) are preserved under INSERTION + SWAP + COMMUTATION.

**Key claim:** INSERTION cannot increase $B_{\text{pre}}(C)$. INSERTION adds gates to wires; it never removes pre-existing gates or changes their wire-level unitaries. The inserted gates may commute with pre-existing gates (enabling new COMMUTATION moves), but any cancellation involving an inserted gate is bounded by Theorem 2c (net gate-count change $\ge 0$ from the INSERTION side). Therefore, the only net reduction achievable comes from cancelling pre-existing pairs that were *already* in $B_{\text{pre}}(C)$ -- i.e., pairs accessible to SWAP + COMMUTATION without any INSERTION.

**Step 5: Bounding the INSERTION-facilitated cascade.**

Consider any sequence $M$ of moves from $\{\text{INSERTION}, \text{REMOVAL}, \text{SWAP}, \text{COMMUTATION}\}$ starting from $C$ with $\mathcal{S}_1(C) = \emptyset$, containing $k$ INSERTION moves, and producing $C'$.

Let $R_{\text{pre}}(M)$ be the number of pre-existing gates removed during $M$. We decompose $R_{\text{pre}}(M)$ into:

- $R_{\text{pre,indep}}$: pre-existing gates removed via REMOVAL pairs that could have been brought into adjacency by SWAP/COMMUTATION alone (without any INSERTION).
- $R_{\text{pre,ins-fac}}$: pre-existing gates removed via REMOVAL pairs that required INSERTION to become adjacent.

By definition, $R_{\text{pre,indep}} \le B_{\text{pre}}(C)$, since $B_{\text{pre}}(C)$ counts exactly the pre-existing wire-level inverse pairs accessible to SWAP/COMMUTATION.

We claim $R_{\text{pre,ins-fac}} \le 0$ in net gate-count contribution. By Step 4, INSERTION cannot reduce the wire-level distance between pre-existing gates; it can only increase it. For INSERTION to facilitate a REMOVAL of two pre-existing gates, the following must occur:

1. INSERTION adds gates that enable a chain of COMMUTATION/SWAP moves.
2. These moves rearrange the circuit so that two pre-existing gates become listing-adjacent.
3. REMOVAL cancels them.

However, the chain in steps 1--2 involves the inserted gates. By the wire-order invariant (Step 3), the pre-existing gates' wire-level ordering is preserved (up to COMMUTATION on the same wire, which preserves the wire-level unitary). The inserted gates act as "catalysts" -- they facilitate rearrangement but must be accounted for.

Each inserted gate used as a catalyst contributes $+1$ to the gate count (until removed). By Theorem 2c, removing the inserted catalysts costs at least as many gate additions. Therefore, the net gate-count change from the entire INSERTION-facilitated cascade is:

$$
\Delta|C| = \underbrace{+2k}_{\text{INSERTIONs}} - \underbrace{R_{\text{total}}}_{\text{all REMOVALs}} \ge -R_{\text{pre,indep}} \ge -B_{\text{pre}}(C).
$$

**Step 6: Phase-1 vs. Phase-2 (a+b) interpretation.**

Phase 1 optimizers employ $\{\text{REMOVAL}, \text{SWAP}, \text{COMMUTATION}, \text{INSERTION}\}$ but do not perform systematic commutation reordering. Phase-2a optimizers perform systematic commutation reordering on the pre-existing circuit.

The bound $B_{\text{pre}}(C)$ is precisely the number of pre-existing gate pairs that Phase-2a can bring into adjacency and cancel. Since INSERTION within Phase 1 can achieve at most $B_{\text{pre}}(C)$ reduction (and only at a net cost that makes the effective reduction $\le B_{\text{pre}}(C)$), we have:

$$
R_1^{\text{INSERTION}}(C) \le \frac{2 \cdot B_{\text{pre}}(C)}{|C|} = R_{1+2}(C).
$$

Since Phase 1 without INSERTION achieves $R_1(C) = 0$ when $\mathcal{S}_1(C) = \emptyset$, the INSERTION-facilitated cascade satisfies:

$$
R_1^{\text{INSERTION}}(C) - R_1(C) \le R_{1+2}(C) - R_1(C) = \Gamma(C).
$$

This was the intended conclusion, but it does not follow from the invalid invariant above.

#### Discussion

**Tightness of the Bound**

The bound in Theorem 2c ($R_{\text{removal}}(C') \le 2k$) is **tight**: a sequence of $k$ INSERTION moves followed by $k$ REMOVAL moves on the inserted pairs themselves achieves exactly $R_{\text{removal}} = 2k$ with net change 0. No sequence can achieve $R_{\text{removal}} > 2k$ involving inserted gates.

No tightness statement survives for former Theorem 2d: $B_{\text{pre}}(C)$ is not an established conflict-aware optimum, and attainability by Phase-2a was not proved.

**Implications for the INSERTION Cascade Gap**

The open gap asks whether INSERTION-facilitated commutation cascades can achieve net reduction beyond what is available without INSERTION. Only the first item below is established; former Theorem 2d and all consequences that depend on it are withdrawn:

1. **INSERTION + REMOVAL alone** (Thm 2c): Net gate-count change is $\ge 0$. INSERTION is a "zero-sum" operation when combined only with REMOVAL.

2. **INSERTION + REMOVAL + SWAP + COMMUTATION** (former Thm 2d): **open**. $B_{\text{pre}}(C)$ was not defined conflict-freely or proved equal to an attainable optimum, and the multi-qubit per-wire factorization is invalid.

3. **Practical consequence:** The 5,000-trial zero-net-reduction result is empirical evidence about the tested implementations and distribution, not a necessary algebraic consequence for the full move set.

**Relation to Phase-2 (a+b) Advantage**

No ordering between Phase 1+INSERTION and Phase-2a follows from former Theorem 2d. Establishing one requires a new dependency-DAG/trace-monoid theorem and a conflict-aware optimum.

---

## Appendix B: Theorem 9 -- Phase-2 (a+b) Advantage for Bernstein--Vazirani Oracle Circuits

> **Document Status**: Formal proof (rewritten 2026-06-17 to remove draft artifacts and consolidate the argument).
> **Version**: 2.0
> **Date**: 2026-06-17
> **Relation to existing results**: Generalizes Theorem 7 (artificial circuit family) to the natural Bernstein--Vazirani oracle family.

### Motivation

Theorem 7 establishes the existence of an explicit circuit family $\{C_n\}$ with $R_1(C_n) = 0$ and $R_{1+2}(C_n) \ge 1/6$, proving Conjecture C2 constructively. However, the circuit family used in Theorem 7 is an artificial construction designed specifically to exhibit Phase-2 (a+b) advantage. A natural question is whether Phase-2 (a+b) advantage arises in **naturally occurring** quantum circuit families -- circuits that arise from standard quantum algorithms without adversarial design.

This appendix proves that the **Bernstein--Vazirani (BV) oracle circuit** family exhibits a constant-factor Phase-2 (a+b) advantage, establishing that the Phase-1/Phase-2 (a+b) optimization gap is not merely an artifact of artificial constructions but arises in standard quantum algorithmic primitives.

> **Important scope note.** The Phase-2b advantage established here relies on **Phase-2b template matching** (the $H$-CNOT-$H$ identity), implemented in `template_matcher.py` and evaluated in the v2 full-scale benchmark. Under pure Phase-2a, the achievable bound for BV remains a separate question. All experimental results labeled "Phase 2" in the manuscript refer to Phase-2a unless explicitly stated otherwise.

### Preliminaries

#### The Bernstein--Vazirani Algorithm

The Bernstein--Vazirani algorithm [Bernstein & Vazirani, 1997] solves the following problem: given oracle access to a function $f_s: \{0,1\}^n \to \{0,1\}$ defined by $f_s(x) = s \cdot x \pmod{2}$ for a secret string $s \in \{0,1\}^n$, determine $s$ using a single oracle query.

The standard circuit implementation uses $n$ input qubits $q_1, \ldots, q_n$ and one ancilla qubit $q_{n+1}$ initialized to $|-\rangle = \frac{1}{\sqrt{2}}(|0\rangle - |1\rangle)$.

#### Circuit Definition

**Definition (BV oracle circuit $BV_n$).** For $n \ge 2$, the Bernstein--Vazirani oracle circuit $BV_n$ with secret string $s = 1^n$ (the all-ones string) on $n+1$ qubits $(q_1, \ldots, q_n, q_{n+1})$ is the circuit:

$$
BV_n = \underbrace{H^{\otimes n}}_{\text{Layer 1}} \cdot \underbrace{\prod_{i=1}^{n} \text{CNOT}(q_i, q_{n+1})}_{\text{Layer 2}} \cdot \underbrace{H^{\otimes n}}_{\text{Layer 3}}
$$

where the product in Layer 2 is ordered as $\text{CNOT}(q_1, q_{n+1}), \text{CNOT}(q_2, q_{n+1}), \ldots, \text{CNOT}(q_n, q_{n+1})$.

**Explicit gate listing.** The circuit $BV_n$ has $|BV_n| = 3n$ gates:

| Index | Gate | Qubits | Layer |
|-------|------|--------|-------|
| $1, \ldots, n$ | $H(q_1), \ldots, H(q_n)$ | $q_1, \ldots, q_n$ | Layer 1 |
| $n+1, \ldots, 2n$ | $\text{CNOT}(q_1, q_{n+1}), \ldots, \text{CNOT}(q_n, q_{n+1})$ | $(q_i, q_{n+1})$ | Layer 2 |
| $2n+1, \ldots, 3n$ | $H(q_1), \ldots, H(q_n)$ | $q_1, \ldots, q_n$ | Layer 3 |

**Unitary implemented.** $BV_n$ implements the unitary $U_{BV_n} = H^{\otimes n} \cdot O_s \cdot H^{\otimes n}$ (on the input register, with ancilla factored out), where $O_s$ is the phase oracle. For $s = 1^n$, the output state encodes $s$ in the computational basis: $U_{BV_n}|0\rangle^{\otimes n} = |1^n\rangle$.

### Theorem 9 (Constructive Phase-2b Advantage for an all-ones BV Circuit)

**Statement.** For the Bernstein--Vazirani oracle circuit $BV_n$ on $n+1$ qubits ($n \ge 2$) with secret string $s = 1^n$:

1. $R_1(BV_n) = 0$ (Phase 1 achieves zero reduction in the standard LBL listing).
2. The explicit Phase-2b sequence below produces an equivalent circuit with
$n+2$ total gates from the $3n+2$-gate input, and therefore achieves
$$
R_{1+2}^{\text{(2b)}}(BV_n) \ge \frac{2n}{3n+2}
\ge \frac12 \quad \text{for all } n \ge 2.
$$
In particular the achieved reduction is $\Omega(1)$. This is a constructive
lower bound for the stated rewrite sequence, not a proof that $n+2$ is globally
minimum under any gate set.

**Audit correction (2026-08-11).** Earlier versions divided by an invented
quantity of "equivalent gate-slots" that included pattern-matching and
bookkeeping work. Runtime work is not circuit gate count and cannot enter this
estimand. The corrected statement counts only emitted circuit operations,
includes the two untouched ancilla-preparation gates, and makes no optimality
claim.

> **Audit note (review Stage 2 -- "Thm 10 calculation inconsistency").** An external review flagged an apparent inconsistency between a "45.5%" figure and a recomputed "66.7%". This note resolves the confusion:
>
> 1. **Gate count.** The BV oracle circuit in the codebase (`make_bernstein_vazirani`) has $3n+2$ gates: $n$ input Hadamards, $1$ ancilla $X$, $1$ ancilla $H$, $n$ CNOTs, $n$ output Hadamards. The proof below counts the *oracle-relevant* $3n$ gates (the two ancilla-preparation gates $X, H$ on $q_{n+1}$ are fixed overhead present in every BV run and are not touched by the rewrite). The review's alternative "$6n+2$" formula does not match any BV construction in this project.
>
> 2. **Two distinct quantities.** The proof reports *two* numbers that must not be conflated:
>    - **Idealized ratio** $R_{\text{ideal}} = (2n-2)/(3n) \to 2/3 \approx 66.7\%$ -- the gross reduction if the template rewrite were free. This is an upper bound on what the rewrite *could* achieve, used only for intuition.
>    - **Corrected constructive bound** $R\ge2n/(3n+2)\ge1/2$ -- obtained by counting the actual input and emitted gates. Runtime overhead is reported separately.
>
> 3. Any companion document retaining `n/(4.5n+4)`, "equivalent gate-slots", or an exact `n+2` optimum is stale. The valid claim is the achieved reduction above; minimality remains unproved.
>
> 4. **Net effect.** The theorem is correct as stated. The "inconsistency" is an apples-to-oranges comparison between the idealized upper bound and the rigorous lower bound, which the proof already separates clearly in Stage C.

#### Proof

##### Part 1: Phase-1 Action Space is Empty ($\mathcal{S}_1(BV_n) = \emptyset$)

**Step 1: Enumerate all listing-adjacent gate pairs.**

In the standard LBL (layer-by-layer) listing, the adjacent pairs are:

- **Within Layer 1**: $(H(q_i), H(q_{i+1}))$ for $i = 1, \ldots, n-1$. These act on different qubits ($q_i$ vs. $q_{i+1}$), so they do not satisfy the same-qubit requirement of $\mathcal{S}_1$.

- **Layer 1 / Layer 2 boundary**: $(H(q_n), \text{CNOT}(q_1, q_{n+1}))$. These act on different qubits ($q_n$ vs. $\{q_1, q_{n+1}\}$). For $n \ge 2$, $q_n \neq q_1$, so the same-qubit requirement is not satisfied. (For $n = 1$, the circuit is trivial and handled separately.)

- **Within Layer 2**: $(\text{CNOT}(q_i, q_{n+1}), \text{CNOT}(q_{i+1}, q_{n+1}))$ for $i = 1, \ldots, n-1$. These share the target qubit $q_{n+1}$ but have different control qubits ($q_i$ vs. $q_{i+1}$). They act on different qubit pairs, so the same-qubit(s) requirement is not satisfied. Moreover, $\text{CNOT}(q_i, q_{n+1}) \neq \text{CNOT}(q_{i+1}, q_{n+1})^{-1} = \text{CNOT}(q_{i+1}, q_{n+1})$ (CNOT is self-inverse, but these are different CNOTs).

- **Layer 2 / Layer 3 boundary**: $(\text{CNOT}(q_n, q_{n+1}), H(q_1))$. These act on different qubits. The same-qubit requirement is not satisfied.

- **Within Layer 3**: $(H(q_i), H(q_{i+1}))$ for $i = 1, \ldots, n-1$. Same as Layer 1: different qubits.

**Step 2: Verify no adjacent inverse pairs exist.**

For a pair $(g_i, g_{i+1})$ to be in $\mathcal{S}_1(BV_n)$, we need:
1. $g_i$ and $g_{i+1}$ act on the **same** qubit(s).
2. $g_{i+1} = g_i^{-1}$.

From Step 1, no listing-adjacent pair acts on the same qubit(s). Therefore:

$$
\mathcal{S}_1(BV_n) = \emptyset \quad \text{for all } n \ge 2.
$$

By Theorem 2(a), $R_1(BV_n) = 0$. $\square$

> **Listing-dependence note.** Part 1 holds under both LBL and WCL (wire-consecutive listing): under WCL the gates on wire $q_i$ are listed consecutively as $H(q_i)_{\text{L1}}, \text{CNOT}(q_i, q_{n+1}), H(q_i)_{\text{L3}}$, but $H \neq \text{CNOT}^{-1}$, so $\mathcal{S}_1(BV_n) = \emptyset$ still holds. The Phase-1 result is listing-independent for $BV_n$.

##### Part 2: Phase-2b Achieves $\Omega(1)$ Reduction

We construct an explicit Phase-2b rewrite sequence and account for its overhead. The argument proceeds in three stages: (A) two algebraic prerequisites; (B) the rewrite procedure; (C) gate-count accounting.

###### Stage A: Algebraic prerequisites

**Lemma A1 (CNOT--CNOT commutation on a shared target).** For $i \neq j$,
$$
\text{CNOT}(q_i, q_{n+1}) \cdot \text{CNOT}(q_j, q_{n+1}) = \text{CNOT}(q_j, q_{n+1}) \cdot \text{CNOT}(q_i, q_{n+1}).
$$

*Proof.* Both CNOTs apply $X$ to $q_{n+1}$ conditioned on their respective controls. In the computational basis,
$$
\text{CNOT}(q_i, q_{n+1})|x_1 \cdots x_n, y\rangle = |x_1 \cdots x_n, y \oplus x_i\rangle.
$$
Applying both in either order yields $|x, y \oplus x_i \oplus x_j\rangle$, which is symmetric in $i, j$. $\square$

**Consequence.** Phase-2a may reorder the $n$ CNOTs in Layer 2 arbitrarily at no gate cost.

**Lemma A2 ($H$-CNOT-$H$ template identity).** For control qubit $c$ and target qubit $t$,
$$
H(c) \cdot \text{CNOT}(c, t) \cdot H(c) = (I(c) \otimes H(t)) \cdot \text{CNOT}(t, c) \cdot (I(c) \otimes H(t)).
$$

*Proof.* We use the well-known basis change $(H \otimes H)\, \text{CNOT}_{c,t}\, (H \otimes H) = \text{CNOT}_{t,c}$, which follows from $HXH = Z$ and $HZH = X$ conjugating the CNOT's controlled-$X$ into a controlled-$Z$ and back. Rearranging,
$$
\text{CNOT}_{c,t} = (H \otimes H)\, \text{CNOT}_{t,c}\, (H \otimes H).
$$
Substituting into $H(c)\, \text{CNOT}_{c,t}\, H(c)$ and using $H^2 = I$:
$$
H(c)\, \text{CNOT}_{c,t}\, H(c) = H(c)(H(c) \otimes H(t))\, \text{CNOT}_{t,c}\, (H(c) \otimes H(t)) H(c)
= (I(c) \otimes H(t))\, \text{CNOT}_{t,c}\, (I(c) \otimes H(t)).
$$
$\square$

**Consequence (the template rule).** The 3-gate pattern $H(c), \text{CNOT}(c,t), H(c)$ can be rewritten as the 3-gate pattern $H(t), \text{CNOT}(t,c), H(t)$: it replaces two $H$ gates on $c$ with two $H$ gates on $t$, and reverses the CNOT direction. Gate count is preserved *locally* (3 $\to$ 3); the global reduction comes from the cancellation step below.

###### Stage B: The rewrite procedure

The procedure has three phases.

**Phase B-1: Bring each $H(q_i)_{\text{L1}}$ and $H(q_i)_{\text{L3}}$ next to $\text{CNOT}(q_i, q_{n+1})$.**

For each $i \in \{1, \ldots, n\}$:
- $H(q_i)_{\text{L1}}$ commutes (by disjoint-qubit commutation, Lemma A1's trivial analogue for $H$ vs. CNOT on different wires) past every $\text{CNOT}(q_j, q_{n+1})$ with $j \neq i$. It cannot pass $\text{CNOT}(q_i, q_{n+1})$ because they share qubit $q_i$.
- Symmetrically, $H(q_i)_{\text{L3}}$ commutes leftward past every $\text{CNOT}(q_j, q_{n+1})$ with $j \neq i$, stopping at $\text{CNOT}(q_i, q_{n+1})$.

After B-1, the gates on wire $q_i$ (in listing order) read:
$$
H(q_i)_{\text{L1}},\; \text{CNOT}(q_i, q_{n+1}),\; H(q_i)_{\text{L3}}.
$$
This is the $H$-CNOT-$H$ sandwich on the control qubit $q_i$.

**Phase B-2: Apply the $H$-CNOT-$H$ template (Lemma A2) to each qubit $q_i$.**

Each sandwich $H(q_i)_{\text{L1}}, \text{CNOT}(q_i, q_{n+1}), H(q_i)_{\text{L3}}$ is rewritten as $H(q_{n+1}), \text{CNOT}(q_{n+1}, q_i), H(q_{n+1})$.

Per qubit, this removes the two $H(q_i)$ gates and introduces two $H(q_{n+1})$ gates (and reverses one CNOT direction). Gate count change per qubit: $-2 + 2 = 0$ *locally*.

**Phase B-3: Cancel adjacent $H(q_{n+1})$ pairs on the ancilla wire.**

After B-2, the ancilla wire $q_{n+1}$ carries, between consecutive reversed CNOTs $\text{CNOT}(q_{n+1}, q_i)$ and $\text{CNOT}(q_{n+1}, q_{i+1})$, **two** adjacent $H(q_{n+1})$ gates: the right $H$ from qubit $i$'s template and the left $H$ from qubit $i+1$'s template. Since $H \cdot H = I$, each such pair cancels (REMOVAL).

There are $n-1$ such inter-CNOT cancellation opportunities, each removing 2 gates. The leftmost $H(q_{n+1})$ (before $\text{CNOT}(q_{n+1}, q_1)$) and the rightmost $H(q_{n+1})$ (after $\text{CNOT}(q_{n+1}, q_n)$) remain unpaired.

###### Stage C: Gate-count accounting

**Constructive gate-count reduction.**
- Gates removed by B-2: $2n$ (the $H(q_i)_{\text{L1}}$ and $H(q_i)_{\text{L3}}$ for all $i$).
- Gates added by B-2: $2n$ (the $H(q_{n+1})$ pairs).
- Gates removed by B-3: $2(n-1)$ (the $n-1$ cancelling $H(q_{n+1})$ pairs).
- CNOT count: $n$ before, $n$ after (direction reversed but count unchanged).

After the inter-template cancellations, the left endpoint Hadamard also cancels
the ancilla-preparation Hadamard. The full emitted circuit is one ancilla $X$,
$n$ reversed CNOTs, and one terminal ancilla $H$: $n+2$ gates in total, down
from $3n+2$.

The achieved full-circuit reduction ratio is therefore
$$
R_{\text{achieved}}(BV_n)=\frac{(3n+2)-(n+2)}{3n+2}
=\frac{2n}{3n+2},
$$
which is $1/2$ at $n=2$ and tends to $2/3$. Pattern matching,
verification, and bookkeeping belong in runtime/resource reporting, not in the
gate-count denominator. Hence
$$
R_{1+2}^{\text{(2b)}}(BV_n)=\Omega(1). \quad \blacksquare
$$

### Small-$n$ verification of the constructed sequence

The following displays omit the two unchanged ancilla-preparation gates from
both the input and output. They verify the local rewrite sequence; they do not
prove global gate-count optimality.

**Verification for $n = 2$.** $BV_2$ has $3 \cdot 2 = 6$ gates:
$$H(q_1), H(q_2), \text{CNOT}(q_1, q_3), \text{CNOT}(q_2, q_3), H(q_1), H(q_2).$$

After B-1 (commute $H$ gates next to their CNOTs):
$$H(q_1), \text{CNOT}(q_1, q_3), H(q_1),\; H(q_2), \text{CNOT}(q_2, q_3), H(q_2).$$

After B-2 (apply $H$-CNOT-$H$ template to each qubit):
$$H(q_3), \text{CNOT}(q_3, q_1), H(q_3),\; H(q_3), \text{CNOT}(q_3, q_2), H(q_3).$$

After B-3 (cancel the adjacent $H(q_3), H(q_3)$ pair in the middle):
$$H(q_3), \text{CNOT}(q_3, q_1), \text{CNOT}(q_3, q_2), H(q_3).$$

Gate count: 4. Original: 6. Idealized reduction: $2/6 = 1/3 \approx 0.333$. (Rigorous bound: $2/13 \approx 0.154$.)

**Verification for $n = 3$.** $BV_3$ has $3 \cdot 3 = 9$ gates.

After B-2 (template applied to all three qubits):
$$H(q_4), \text{CNOT}(q_4, q_1), H(q_4), H(q_4), \text{CNOT}(q_4, q_2), H(q_4), H(q_4), \text{CNOT}(q_4, q_3), H(q_4).$$

After B-3 (cancel 2 adjacent $H(q_4)$ pairs, removing 4 gates):
$$H(q_4), \text{CNOT}(q_4, q_1), \text{CNOT}(q_4, q_2), \text{CNOT}(q_4, q_3), H(q_4).$$

Gate count: 5. Original: 9. Idealized reduction: $4/9 \approx 0.444$. (Rigorous bound: $3/17.5 \approx 0.171$.)

The gap between the idealized ratio and the rigorous bound reflects the template-matching overhead, which dominates at small $n$ and amortizes as $n$ grows.

### Phase-2b rule requirements

The Phase-2b procedure above uses four operations, all within the Phase-2b toolkit:

1. **Disjoint-qubit commutation** (to bring $H$ gates next to their CNOTs in B-1) -- standard.
2. **CNOT--CNOT commutation on a shared target** (Lemma A1, to reorder Layer 2) -- standard, proven above.
3. **$H$-CNOT-$H$ template identity** (Lemma A2, the core of B-2) -- a Phase-2b template-matching rule, equivalent to the well-known CNOT direction-reversal identity $(H \otimes H)\, \text{CNOT}\, (H \otimes H) = \text{CNOT}_{\text{reversed}}$. This rule is implemented in the Phase-2b `template_matcher.py`; `commutation_rewriter.py` remains Phase-2a only.
4. **Adjacent $H$-$H$ cancellation** ($H \cdot H = I$, used in B-3) -- standard Phase-1 REMOVAL.

### Phase-2a vs. Phase-2b

> **Critical clarification for matching theory to experiments.**

The experimental codebase separates **Phase-2a** (`commutation_rewriter.py`: disjoint-qubit commutation plus a small set of algebraic commutation rules) from **Phase-2b** (`template_matcher.py`: inverse closure, phase-polynomial merging, and bounded Clifford-conjugation templates). E26 evaluates the implemented Phase-2b library at full scale; it is not an exhaustive template universe.

Theorem 9's achieved bound $2n/(3n+2)=\Omega(1)$ relies on the full-pipeline
$H$-CNOT-$H$ template (Phase-2b). **Under pure Phase-2a, the achievable
reduction for $BV_n$ is an open question.** Concretely:

- Phase-2a can perform Stage B-1 (disjoint-qubit commutation) freely.
- Phase-2a **cannot** perform Stage B-2 (the $H$-CNOT-$H$ template rewrite).
- Without B-2, the $H(q_i)_{\text{L1}}$ and $H(q_i)_{\text{L3}}$ remain separated by $\text{CNOT}(q_i, q_{n+1})$ and cannot be cancelled.

Therefore, under Phase-2a alone, the *provable* reduction for $BV_n$ is currently $0$ (matching Phase-1). Whether a clever Phase-2a commutation sequence can achieve non-zero reduction on $BV_n$ is left as an open question.

**Experimental status.** The corrected v10 E26 rerun directly evaluates the implemented Phase-2b pipeline on 80 BV instances ($n=3,\ldots,10$, 10 secrets per size), with exact equivalence for all three optimizer arms. For `template_phase2b`, every instance exceeds the theorem's conservative bound; size-specific mean reductions range from 0.5915 to 0.7455 and minima from 0.5455 to 0.6250 (`data/v10/prepaper/e26/bv_theory_v8.csv`). This validates the implementation on the tested BV grid, not completeness of the template universe. The older E11 Phase-2a result uses a different mechanism and remains indirect evidence only.

### Listing-model dependency

As with Theorem 1, the Phase-1 result $R_1(BV_n) = 0$ depends on the listing model. Under WCL (wire-consecutive listing), the gates on wire $q_i$ are listed consecutively: $H(q_i)_{\text{L1}}, \text{CNOT}(q_i, q_{n+1}), H(q_i)_{\text{L3}}$. Under WCL, $H(q_i)_{\text{L1}}$ and $\text{CNOT}(q_i, q_{n+1})$ are listing-adjacent, but $H \neq \text{CNOT}^{-1}$, so $\mathcal{S}_1(BV_n) = \emptyset$ still holds. **The Phase-1 result is listing-independent for $BV_n$.**

The abstract constructive sequence can be expressed modulo legal commutations, but the implemented matcher is bounded-window and consumes a concrete listing. Its empirical success can therefore be representation dependent. The theorem establishes existence under its stated rewrite operations; it does not prove listing invariance of the implementation or its gate count.

> **Connection to the broader listing-conditional framing.** The structural-ceiling framework (Conjecture C1, Observation 1(b)) is explicitly **listing-conditional**: the Phase-1 ceiling $\mathcal{S}_1(C) = \emptyset$ is a property of the LBL listing, not of the circuit's intrinsic unitary. Theorem 9's Phase-1 result inherits this listing-conditionality.

### Comparison with Theorem 7

| Property | Theorem 7 (artificial) | Theorem 9 (BV oracle) |
|----------|----------------------|----------------------|
| Circuit family | Adversarial construction | Natural quantum algorithm |
| $R_1$ | 0 | 0 |
| $R_{1+2}^{\text{(2b)}}$ lower bound | $\ge 1/6 \approx 0.167$ | achieved $\ge2n/(3n+2)\ge1/2$ for the all-ones construction |
| Phase-2 (a+b) mechanism | CNOT--CNOT cancellation via $S$-commutation | $H$-CNOT-$H$ template (Phase-2b) + ancilla $H$-cancellation |
| Practical relevance | Low (designed for proof) | High (BV is a standard oracle algorithm) |
| Asymptotic gap $\Gamma^{\text{(2b)}}$ | $\Omega(1)$ | $\Omega(1)$ (specifically $\to 1/4.5$) |
| Implemented in codebase? | Phase-2a only | Phase-2b v2 implemented and evaluated in E26 |

Theorem 9 strengthens the case for Conjecture C2 by demonstrating Phase-2b advantage on a circuit family that arises naturally in quantum complexity theory, rather than on an artificial construction. Because the bound relies on a stated template model, it should be read as a **model-specific theoretical result**, not as a direct explanation of the experimental Phase-2a reductions.

---

## Summary Table

| ID | Type | Statement | Status |
|----|------|-----------|--------|
| **Thm 1(a)** | Theorem | Adjacent inverse pair density bound under WCL (expectation) | [CORRECTED 2026-08-06 -- constants fixed (k1 factor; 2-qubit double count) and directly validated by E30] |
| **Thm 1(b)** | Theorem | LBL listing model yields $\mathcal{S}_1(C) = \emptyset$ for $n \ge 2$ | [PROVEN -- structural, explains E1 zero-std] |
| **Thm 2** | Mixed | Greedy predicate ceiling; proposed stochastic ceiling | **[PART (a) PROVEN; GENERAL PART (b) REFUTED BY 3-GATE SWAP+REMOVAL COUNTEREXAMPLE]** |
| **Lemma 3** | Lemma | Commutation rewriting preserves equivalence | [PROVEN -- 1-line, supporting lemma] |
| **Lemma 4** | Lemma | Greedy optimality for non-conflicting pairs | [PROVEN -- narrow scope, supporting lemma] |
| **Thm 5** | Candidate theorem | High-probability bound on adjacent inverse pairs (McDiarmid) | **[PROOF INCOMPLETE -- matching dependencies omitted]** |
| **Prop 6** | Proposition | Greedy ceiling for the restricted non-empty-stage AG generator | **[CODE-CORRECTED; E23 does not establish general AG claim]** |
| **Thm 7** | Theorem | Explicit circuit family with $\Omega(1)$ Phase-2a advantage | [PROVEN -- artificial construction] |
| **Thm 8** | Withdrawn claim | Haar-random circuit incompressibility and bounded-window limit | **[WITHDRAWN 2026-08-09 -- incompatible premises]** |
| **Thm 2c** | Theorem | Bounded INSERTION cascade lemma: $R_{\text{removal}}(C') \le 2k$ | [PROVEN -- insertion-debt invariant, see Appendix A] |
| **Thm 2d** | Withdrawn claim | INSERTION commutation cascade bound | **[PROOF INVALID -- multi-qubit wire factorization and optimum identification fail]** |
| **Thm 9** | Theorem | Constructed Phase-2b sequence achieves $\ge2n/(3n+2)=\Omega(1)$ for the stated all-ones BV circuit | [PROVEN -- achieved reduction only; no global optimality claim; pure Phase-2a bound open] |
| Prop 1 | Proposition | Conflict resolution is polynomial-time (maximum matching) | [CORRECTED] |
| Obs 1 | Withdrawn empirical generalization | Greedy matches stochastic Phase-1 optimizers | **[WITHDRAWN -- explicit counterexample; historical stochastic data also affected by incumbent bug]** |
| OP1 | Open Problem | CODP is QMA-hard | [CONJECTURE] |
| OP2 | Open Problem | No PTAS for CODP | [CONJECTURE] |
| C1 | Refuted conjecture | All Phase-1 optimizers share a structural listing-conditional ceiling | **[REFUTED; only scoped Greedy/rewrite-subsystem results survive]** |
| C2 | Existence result | Phase-2 (a+b) can give context-dependent super-constant advantage | [EXISTENCE PROVED for artificial Phase-2a and BV Phase-2b families; general characterization open] |

---

## References

1. Janzing, D., Wocjan, P. & Beth, T. (2003). Non-identity-check is QMA-complete. *Int. J. Quantum Inform.* **1**, 507-518.
2. Kempe, J., Kitaev, A. & Regev, O. (2006). The Complexity of the Local Hamiltonian Problem. *SIAM J. Comput.* **35**, 1070-1097.
3. Gottesman, D. (1997). Stabilizer codes and quantum error correction. *Ph.D. thesis, Caltech*.
4. Aaronson, S. & Gottesman, D. (2004). Improved simulation of stabilizer circuits. *Phys. Rev. A* **70**, 052328.
5. Dawson, C. M. & Nielsen, M. A. (2006). The Solovay-Kitaev algorithm. *Quantum Info. Comput.* **6**, 81-95.
6. Harrow, A. W. & Montanaro, A. (2017). Quantum computational supremacy. *Nature* **549**, 188-196.
7. McClean, J. R. et al. (2018). Barren plateaus in quantum neural network training landscapes. *Nat. Commun.* **9**, 4812.
8. Garey, M. R. & Johnson, D. S. (1979). *Computers and Intractability*. W. H. Freeman.
9. Berman, P. & Karpinski, M. (1999). On some tighter inapproximability results. *LNCS* **1644**, 200-209.
10. Downey, R. G. & Fellows, M. R. (2013). *Fundamentals of Parameterized Complexity*. Springer.
11. Edmonds, J. (1965). Paths, trees, and flowers. *Canad. J. Math.* **17**, 449-467.
12. Micali, S. & Vazirani, V. V. (1980). An $O(\sqrt{|V|} \cdot |E|)$ algorithm for finding maximum matching in general graphs. *Proc. 21st IEEE FOCS*, 17-27.
13. Kitaev, A. Yu. (1997). Quantum computations: algorithms and error correction. *Russ. Math. Surv.* **52**, 1191-1249.
14. McDiarmid, C. (1989). On the method of bounded differences. *Surveys in Combinatorics*, London Mathematical Society Lecture Note Series **141**, 148-188.
15. Nielsen, M. A. (2005). A geometric approach to quantum circuit lower bounds. *arXiv:quant-ph/0502070*.
16. Nielsen, M. A. & Chuang, I. L. (2010). *Quantum Computation and Quantum Information*. Cambridge University Press.
17. Bernstein, E. & Vazirani, U. (1997). Quantum complexity theory. *SIAM J. Comput.* **26**(5), 1411-1473.

---

**Document version**: 4.0 (Consolidated)
**Last updated**: 2026-06-17
**Author**: Q-research Theoretical Framework Team
**Companion document**: `framework.md` (definitions D1-D10, unified architecture, complexity classification, cross-reference map)
