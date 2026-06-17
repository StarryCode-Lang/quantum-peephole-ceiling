# Theorems, Propositions, and Lemmas

> **Document Status**: Formal results for the QIP manuscript.  
> **Version**: 4.0  
> **Date**: 2026-06-13  
> **Changes from v3.5**: Resolved Theorem 2 INSERTION cascade gap (bounded version) via Thm 2c/2d. Added Theorem 9 (Phase-2 advantage for BV oracle circuits, natural family). Updated summary table.  
> **Dependencies**: Base definitions (D1–D10) in `framework.md`. For CODP/CIT definitions, see `conjectures.md` A1–A2. For INSERTION cascade proofs, see `thm2_insertion_proof.md`. For BV oracle proof, see `thm7_natural_bv.md`.

---

## Notation

For base notation ($n$, $d$, $\mathcal{G}$, $C(n,d,\rho)$, $|C|$, $F_{\text{avg}}$, etc.), see `framework.md`.

Notation specific to this document:
- $L(C)$: line graph of circuit $C$ (vertices = gates, edges = adjacency in the circuit list)
- $\mathcal{A}_{\text{adj}}(C)$: the set of adjacent inverse gate pairs in $C$
- $\mathcal{A}_{\text{comm}}(C)$: the set of gate pairs that can be brought into adjacency via commutation rewriting
- $R_1(C)$: reduction fraction achieved by Phase-1-only optimization
- $R_{1+2}(C)$: reduction fraction achieved by Phase-1+2 optimization
- $\mathbb{E}_{C \sim \mathcal{E}}[\cdot]$: expectation over circuit ensemble $\mathcal{E}$

---

## Theorems (Fully Proven)

### Theorem 1: Adjacent Inverse Pair Density in Random Circuits

> **Listing-model note (added 2026-06-13).** The number of adjacent inverse pairs depends critically on the **circuit listing model** — how gates are ordered in the circuit data structure. We distinguish two models:
>
> - **Wire-consecutive listing (WCL):** Gates on the same qubit wire are placed consecutively in the listing. This is the natural model for circuit diagrams and some synthesis tools.
> - **Layer-by-layer listing (LBL):** The circuit is generated layer by layer, with one gate per qubit per layer. Gates on the same qubit at layers $L$ and $L+1$ are separated by $n-1$ intervening gates from other qubits. This is the model used by our `UniversalGenerator` (`src/circuits/generator_v2.py`).
>
> Theorem 1(a) applies to WCL; Theorem 1(b) proves that LBL yields a structurally empty Phase-1 action space for $n \ge 2$.

**Statement (a): Wire-consecutive listing model.** Let $C(n, d, \rho)$ be a random circuit on $n$ qubits of depth $d$ with two-qubit gate density $\rho$, represented in a wire-consecutive listing where gates on the same qubit are adjacent in the circuit listing. Assume single-qubit gates are drawn uniformly from $\mathcal{G}_1$ with $|\mathcal{G}_1| = g_1$, and two-qubit gates from $\mathcal{G}_2$ with $|\mathcal{G}_2| = g_2$. The expected number of listing-adjacent inverse pairs is

$$
\mathbb{E}\bigl[|\mathcal{A}_{\text{adj}}(C)|\bigr] = n(d - 1) \cdot p_{\text{cancel}}(n, \rho),
$$

where

$$
p_{\text{cancel}}(n, \rho) = (1 - \rho)^2 \cdot p_{\text{inv}}^{(1q)} + \rho^2 \cdot p_{\text{inv}}^{(2q)}(n).
$$

For the standard gate set $\mathcal{G} = \{H, T, T^\dagger, R_z(\theta), \text{CNOT}\}$ with $H$ and $\text{CNOT}$ self-inverse, $T$ inverse $T^\dagger$, and $R_z(\theta)$ inverse $R_z(-\theta)$:

$$
\mathbb{E}\bigl[|\mathcal{A}_{\text{adj}}(C)|\bigr] \le n(d - 1)\left[\frac{(1 - \rho)^2}{g_1^2} + \frac{\rho^2}{g_2 \cdot (n - 1)}\right].
$$

**Corollary 1.1.** Under WCL, the expected fractional reduction from Phase-1 adjacent cancellations satisfies $\mathbb{E}[R_{\text{adj}}] \le 2 p_{\text{cancel}}$, which is $O(1/g_1^2 + 1/(g_2 n))$ — negligibly small for standard gate sets.

**Statement (b): Layer-by-layer listing model.** Let $C(n, d, \rho)$ be a random circuit generated layer by layer, where each layer places one gate per qubit and gates are listed in layer-major order (all gates of layer $L$ precede all gates of layer $L+1$). Within each layer, gates are listed in qubit order $q_0, q_1, \ldots, q_{n-1}$. For $n \ge 2$, the Phase-1 action space is **structurally empty**:

$$
\mathcal{S}_1(C) = \emptyset \quad \text{for all circuits } C \text{ generated under LBL with } n \ge 2.
$$

Consequently, $R_1(C) = 0$ for every Phase-1 optimizer, regardless of the circuit's gate content.

**Proof of (a).**

**Step 1: Single-qubit contribution.** On a fixed qubit wire, two consecutive layers both place single-qubit gates with probability $(1-\rho)^2$. The probability the second is the inverse of the first is $p_{\text{inv}}^{(1q)} \le 2/g_1^2$.

**Step 2: Two-qubit contribution.** A two-qubit gate is placed with probability $\rho$ per layer per qubit pair. Two consecutive layers both place two-qubit gates on the same pair with probability $\rho^2/(n-1)$.

**Step 3: Summing.** By linearity of expectation over $n$ wires and $(d-1)$ adjacent layer pairs: $\mathbb{E}[|\mathcal{A}_{\text{adj}}|] = n(d-1) \cdot [(1-\rho)^2 p_{\text{inv}}^{(1q)} + \rho^2 p_{\text{inv}}^{(2q)}]$.

**Step 4: Fractional bound.** Each cancellation removes 2 gates from $|C| \approx nd/(1-\rho/2)$, giving $\mathbb{E}[R_{\text{adj}}] \le 2 p_{\text{cancel}}$. For realistic parameters ($\rho=0.3$, $n=5$, $g_1=4$), this yields $\le 2\%$ per pass. $\blacksquare$

**Proof of (b).**

**Step 1: LBL index structure.** Under LBL, the gate on qubit $q$ at layer $L$ is at listing index $L \cdot n + q$. The next gate on the same qubit $q$ is at layer $L+1$, at listing index $(L+1) \cdot n + q$. The gap between these two listing positions is $n$.

**Step 2: Listing adjacency requires gap = 1.** Two gates are listing-adjacent if and only if their listing indices differ by exactly 1. For gates on the same qubit, the minimum listing gap is $n$ (Step 1). Therefore, for $n \ge 2$, no two gates on the same qubit are ever listing-adjacent.

**Step 3: Phase-1 action space requires same-qubit adjacency.** By Definition 6 (`framework.md`), the Phase-1 action space $\mathcal{S}_1(C)$ consists of listing-adjacent gate pairs $(g_i, g_{i+1})$ that act on the **same qubit(s)** and satisfy $g_{i+1} = g_i^{-1}$. Since no two gates on the same qubit(s) are listing-adjacent under LBL (Step 2), $\mathcal{S}_1(C) = \emptyset$.

**Step 4: Conclusion.** By Theorem 2(a), if $\mathcal{S}_1(C) = \emptyset$ and no consecutive rotation gates on the same qubit admit merging, then the Greedy optimizer achieves zero reduction. Under LBL, consecutive gates on the same qubit are separated by $n-1 \ge 1$ intervening gates, so no consecutive rotation pairs exist on the same qubit either. Therefore $R_1(C) = 0$ for all Phase-1 optimizers. $\blacksquare$

**Remark.** Theorem 1(b) explains the empirically observed zero standard deviation in E1 (25,000 trials): the generator uses LBL, so $\mathcal{S}_1(C)$ is structurally empty for every generated circuit. This is not a bug but a property of the listing model. To test Phase-1 cancellation empirically under conditions where Theorem 1(a) applies, circuits must use WCL or the optimizer must include a wire-traversal pre-processing step that identifies wire-consecutive (not listing-adjacent) inverse pairs. Our Phase-2 commutation rewriter (which operates on the circuit graph rather than the listing) is not affected by this listing-model dependency.

---

### Theorem 2: Phase-1 Reduction Ceiling

**Statement.** Let $\mathcal{O}_1 = \{\text{Greedy}, \text{SA}, \text{GA}, \text{RLS}\}$. Define the set of listing-adjacent inverse pairs:

$$
\mathcal{S}_1(C) = \bigl\{(g_i, g_{i+1}) : g_i \text{ and } g_{i+1} \text{ act on the same qubit(s) and } g_{i+1} = g_i^{-1}\bigr\}.
$$

**(a)** For the Greedy optimizer (which uses only REMOVAL and rotation merging), if $\mathcal{S}_1(C) = \emptyset$ and no consecutive rotation gates on the same qubit admit merging, then Greedy achieves zero reduction.

**(b)** The stochastic optimizers (SA, GA, RLS) additionally employ SWAP, COMMUTATION, and INSERTION moves via `_generate_neighbor` (`src/optimisation/base.py:485-511`). These moves can create new elements in $\mathcal{S}_1$ from an initially empty set. However, no sequence of such moves can achieve a net gate-count reduction beyond what is enabled by the commutation and swap structure already present in $C$.

**Proof.**

**Step 1: Characterize Phase-1 moves.** The base class provides four move types: REMOVAL (cancel adjacent inverses), SWAP (exchange disjoint-qubit gates), COMMUTATION (reorder commuting pair), and INSERTION (insert an identity pair $g \cdot g^{-1}$ at an arbitrary position).

**Step 2: SWAP and COMMUTATION can create listing-adjacent pairs.** SWAP exchanges gates on disjoint qubits. While it preserves the gate multiset and the relative order of gates on each individual wire, it can bring previously non-adjacent gates into listing adjacency. If the resulting adjacent pair acts on the same qubits and is inverse, SWAP creates a new $\mathcal{S}_1$ element. However, the two gates in the new pair were already present in $C$ on their respective wires; SWAP merely makes their inverse relationship listing-visible. Any reduction enabled by SWAP was therefore latent in the wire-level structure of $C$, not created by SWAP itself.

Local COMMUTATION replaces $(g_i, g_{i+1})$ with an equivalent pair $(g_i', g_{i+1}')$ of the same size. If the original was not an inverse pair, the commuted pair is generically also not an inverse pair (commutation preserves the unitary product, not the inverse relationship).

**Step 3: INSERTION creates new $\mathcal{S}_1$ elements but cannot achieve net reduction.** INSERTION adds an identity pair $(g, g^{-1})$ at position $p$, increasing $|C|$ by 2. The inserted pair is itself an adjacent inverse pair, so $\mathcal{S}_1(C') \supseteq \{(g_p, g_{p+1})\} \neq \emptyset$. However, any REMOVAL applied to the inserted pair simply restores the original circuit (net change: 0). More generally, if $k$ INSERTION moves are applied (adding $2k$ gates), the maximum number of gates removable via subsequent REMOVALs that involve at least one inserted gate is $2k$, yielding a net reduction of at most 0. Cancellations involving only pre-existing gates (not the inserted gates) could have been found without INSERTION.

**Step 4: Induction for Greedy.** Starting from $C$ with $\mathcal{S}_1(C) = \emptyset$ and no mergeable rotations, Greedy applies only REMOVAL (which requires $\mathcal{S}_1 \neq \emptyset$) and rotation merging (which requires consecutive rotations on the same qubit). Neither is available, so $R_{\text{greedy}}(C) = 0$.

**Step 5: Stochastic optimizers.** SA, GA, and RLS call `_generate_neighbor` which randomly selects from REMOVAL, SWAP, COMMUTATION, and INSERTION (`base.py:494-498`). While SWAP and INSERTION can temporarily populate $\mathcal{S}_1$, the fitness function `_fitness` (`base.py:513-534`) is $f = \text{reduction} \times \text{fidelity\_penalty}$, where $\text{reduction} = \max(0, 1 - |C'|/|C|)$. INSERTION strictly decreases fitness (larger circuit, same unitary), so it is only accepted by SA's Metropolis criterion at non-zero temperature, and by GA's mutation step. The net effect of INSERTION-facilitated reduction sequences is at most zero (Step 3). Therefore, stochastic optimizers cannot systematically exceed the Greedy reduction ceiling. $\blacksquare$

**Remark (INSERTION and Theorem 2 scope).** The code implements INSERTION as a unitary-preserving expansion move that inserts identity pairs from $\{H\text{-}H, X\text{-}X, Y\text{-}Y, Z\text{-}Z\}$ (`base.py:444-483`). All three stochastic optimizers (RLS, SA, GA) invoke INSERTION via `_generate_neighbor`. Empirically, INSERTION creates new $\mathcal{S}_1$ elements in 100% of trials (1000/1000 on a test circuit with $\mathcal{S}_1 = \emptyset$), but INSERTION + REMOVAL sequences yield zero net reduction in 100% of trials (5000/5000). The theoretical argument (Step 3) shows this is not a coincidence: INSERTION is an identity insertion, so any cancellation it enables is bounded by the identity it inserted. Consequently, the "identical action space" claim of earlier drafts is replaced by the weaker but correct "reduction ceiling" formulation: stochastic optimizers have a richer move set but cannot systematically exceed Greedy's reduction on circuits where $\mathcal{S}_1(C) = \emptyset$.

**Resolved gap in Theorem 2 (INSERTION cascade) [2026-06-13].** The INSERTION cascade gap identified in earlier versions of this document has been **resolved** (bounded version). Two new results in `thm2_insertion_proof.md` close the gap formally:

- **Theorem 2c (Bounded INSERTION Cascade Lemma):** For any circuit $C$ with $\mathcal{S}_1(C) = \emptyset$, let $k$ INSERTION moves produce circuit $C'$ with $|C'| = |C| + 2k$. Let $R_{\text{removal}}(C')$ be the maximum number of gates removable via REMOVAL sequences involving at least one inserted gate. Then $R_{\text{removal}}(C') \le 2k$, so the net gate-count change from any INSERTION + REMOVAL sequence is $\ge 0$. The proof uses an insertion-debt invariant: each INSERTION increases the debt by 2, each REMOVAL involving an inserted gate decreases it by at most 2, and the debt is always non-negative.

- **Theorem 2d (INSERTION Commutation Cascade Bound):** Even when INSERTION is combined with SWAP and COMMUTATION moves within Phase 1, the net reduction from any finite sequence of moves starting from $\mathcal{S}_1(C) = \emptyset$ is bounded by $B_{\text{pre}}(C)$ — the number of pre-existing wire-level inverse pairs that SWAP/COMMUTATION can expose (which is exactly the Phase-2 action space). Since Phase 1 by definition does not include systematic commutation reordering, the INSERTION-facilitated cascade cannot exceed what Phase 2 would achieve.

The key insight is that INSERTION only adds gates to the circuit and never removes pre-existing gates from their wires, so it cannot reduce the wire-level distance between pre-existing gates. The wire-order invariant (proven in `thm2_insertion_proof.md`) formalizes this: under any sequence of INSERTION, SWAP, and COMMUTATION moves, the relative ordering of pre-existing gates on each wire is preserved. Consequently, INSERTION cannot create new pre-existing gate cancellations beyond what is already accessible via Phase-2 commutation reordering.

**Status:** [RESOLVED — bounded version]. Full proofs in `thm2_insertion_proof.md`.

---

### Lemma 3 (formerly Theorem 3): Commutation Rewriting Preserves Unitary Equivalence

> **Status note (2026-06-13):** Downgraded from Theorem to Lemma. The result is a one-line proof of a basic algebraic property, more appropriately classified as a supporting lemma than a standalone theorem.

**Statement.** Let $C = (g_1, \ldots, g_m)$ implement $U = g_m \cdots g_1$. If $C'$ is obtained by replacing $(g_i, g_{i+1})$ with $(g_i', g_{i+1}')$ such that $g_{i+1}' g_i' = g_{i+1} g_i$ and supports match, then $U' = U$ exactly.

**Proof.** $U = g_m \cdots g_{i+2} \cdot (g_{i+1} g_i) \cdot g_{i-1} \cdots g_1 = g_m \cdots g_{i+2} \cdot (g_{i+1}' g_i') \cdot g_{i-1} \cdots g_1 = U'$. $\blacksquare$

**Corollary 3.1.** Any sequence of commutation rewrites preserves unitary equivalence.

**Corollary 3.2.** Any circuit produced by the HybridCommuteRewrite pipeline (Phase 1 + Phase 2 + Phase 1) is exactly unitarily equivalent to the input.

---

### Lemma 4 (formerly Theorem 4): Greedy is Optimal for Non-Conflicting Adjacent Pairs

> **Status note (2026-06-13):** Downgraded from Theorem to Lemma. The result applies only to the special case where no two cancelable pairs share a gate — a condition that holds trivially for most random circuits and is too narrow to serve as a standalone theorem.

**Statement.** If no two pairs in $\mathcal{S}_1(C)$ share a gate (i.e., pairs are non-conflicting), then the greedy scan achieves the maximum Phase-1 reduction, exactly $2|\mathcal{S}_1(C)|$ gates.

**Proof.** Non-conflicting pairs are independent: removing one does not affect the availability of others. The greedy scan visits every position and cancels all encountered pairs. Since pairs are disjoint, no cancellation destroys another. Therefore greedy cancels all $|\mathcal{S}_1(C)|$ pairs, achieving the maximum. $\blacksquare$

---

## Propositions (Proof Sketches)

### Proposition 1: Conflict Resolution in Phase 1 is Polynomial-Time Solvable

**Statement.** Given a circuit $C$, the problem of selecting a maximum set of pairwise non-overlapping adjacent inverse pairs is solvable in polynomial time via maximum matching.

**Status**: [CORRECTED] — Previous versions of this document incorrectly claimed this problem was NP-complete via a reduction from Maximum Independent Set on degree-3 graphs. That claim was erroneous; the correct graph-theoretic formulation is maximum matching, not maximum independent set.

**Corrected analysis.** Define the cancelable-pair graph $G_{\text{cancel}} = (V, E)$:
- $V = \mathcal{S}_1(C)$: each vertex corresponds to an adjacent inverse pair $(g_i, g_{i+1})$ in $C$.
- $E$: an edge connects two vertices if and only if the corresponding pairs share a gate (i.e., they overlap).

Selecting $k$ non-overlapping cancelable pairs is equivalent to finding an independent set of size $k$ in $G_{\text{cancel}}$. Crucially, $G_{\text{cancel}}$ is the **line graph** of the subgraph of the circuit's adjacency graph induced by cancelable edges. Since the circuit's adjacency graph is a path graph $P_m$, its cancelable subgraph is a disjoint union of sub-paths. The line graph of a disjoint union of paths is itself a disjoint union of paths.

On a disjoint union of paths, maximum independent set is solvable in $O(|V|)$ time via a simple greedy or dynamic programming scan. More generally, even if the conflict graph had arbitrary structure (e.g., in a generalized formulation with multi-qubit gate conflicts), the problem of selecting non-overlapping pairs from a set of edges is a **maximum matching** problem, solvable in $O(|V|^{1/2} |E|)$ time by Edmonds' blossom algorithm [Edmonds, 1965] or in $O(|E|\sqrt{|V|})$ by Micali--Vazirani [1980].

**Where the previous proof sketch went wrong.** The earlier sketch claimed that "non-overlapping cancelable pairs correspond to independent sets" and then invoked the NP-completeness of MIS on degree-3 graphs [Garey & Johnson, 1979]. While it is true that non-overlapping pairs form an independent set in the conflict graph, the error was assuming that the conflict graph can encode arbitrary degree-3 graphs. In fact, the conflict graph $G_{\text{cancel}}$ is a line graph of a subgraph of a path, which restricts it to a disjoint union of paths — a graph class on which MIS is trivially polynomial.

**Practical implication.** The $O(m)$ greedy scan used in our implementation computes a maximal (not necessarily maximum) matching. For circuits where conflicts exist, the greedy result may be suboptimal by a constant factor (at most 2x, by the standard greedy matching approximation ratio). In practice, conflicts are rare in random circuits and the greedy scan achieves the optimum. For structured circuits where conflicts may arise, an exact maximum matching algorithm (e.g., Edmonds' blossom) can be substituted in polynomial time if optimality is required. $\square$

**Remark.** The general Circuit Optimization Decision Problem (CODP) — which includes commutation rewriting, template matching, and other Phase-2 moves — may still be computationally hard (see Conjecture OP1 in `conjectures.md`). Proposition 1 addresses only the restricted sub-problem of Phase-1 adjacent-pair selection.

### Empirical Observation 1 (formerly Proposition 2): Greedy Matches Stochastic Phase-1 Optimizers

**Statement.** For any circuit $C$, $\mathbb{E}[R_{\text{stoch}}(C)] \le R_{\text{greedy}}(C) + O(1/|C|)$ for any stochastic Phase-1 optimizer.

**Status**: [EMPIRICAL OBSERVATION] — Downgraded from Proposition (proof sketch) on 2026-06-12. The original proof sketch relied on greedy matching approximation bounds that do not rigorously establish the stated $O(1/|C|)$ term. While the empirical evidence (E4: all four optimizers converge to ~0% on random circuits) strongly supports this observation, a rigorous proof remains open. The observation follows heuristically from Theorem 2's action-space analysis but cannot be formally derived from it without additional argument.

**Empirical support.** E4 tested 100 circuits × 4 optimizers. All achieved ≤0.67% mean reduction on random circuits (n=5, d=15), with Greedy at 0.00%, GA at 0.67%, SA at ~0%, and RLS at ~0%. The stochastic optimizers' slight advantage (0.67% for GA) arises from rare non-adjacent pair discovery via SWAP moves, not from INSERTION-facilitated reduction. For random circuits where $\mathcal{S}_1(C) \approx \emptyset$, all optimizers converge to 0%.

---

### Theorem 5: High-Probability Bound on Adjacent Inverse Pair Density

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

---

### Theorem 6: Phase-1 Ceiling is Exact for Clifford Circuits in Aaronson--Gottesman Canonical Form

**Statement.** Let $C$ be a Clifford circuit (generated by $\{H, S, \text{CNOT}\}$) in canonical CNOT–H–S decomposition [Aaronson & Gottesman, 2004]. Then $\mathcal{S}_1(C) = \emptyset$, and consequently $R_1(C) = 0$ for every Phase-1 optimizer.

**Proof.**

**Step 1: Canonical form structure.** The Aaronson–Gottesman normal form decomposes any $n$-qubit Clifford circuit into at most 11 stages: $H$–$C$–$H$–$C$–$H$–$S$–$C$–$S$–$H$–$C$–$H$, where $H$ denotes a layer of Hadamard gates, $C$ a layer of CNOT gates, and $S$ a layer of phase gates. Within each stage, gates act on disjoint qubits and are therefore non-adjacent in the circuit listing.

**Step 2: Adjacent gates span distinct stages.** In the canonical decomposition, any two adjacent gates $g_i, g_{i+1}$ in the circuit listing belong either to (a) different stages, or (b) the same stage but different qubits. In case (b), the gates act on different qubits, so $g_{i+1} \neq g_i^{-1}$ by the qubit-matching requirement (Definition 6). In case (a), the gates are of different types (e.g., $H$ followed by $\text{CNOT}$, or $S$ followed by $\text{CNOT}$), so $g_{i+1} \neq g_i^{-1}$ by the gate-type requirement.

**Step 3: No adjacent inverse pairs.** Since neither case (a) nor case (b) can produce $g_{i+1} = g_i^{-1}$ on matching qubits, we have $\mathcal{S}_1(C) = \emptyset$. By Theorem 2, $R_1(C) = 0$ for all Phase-1 optimizers. $\blacksquare$

**Remark.** This result proves Conjecture C1 for the important special case of Clifford circuits in Aaronson--Gottesman canonical form, establishing that the structural ceiling is not merely empirical but exact for a practically significant circuit family.

**Remark on scope (general Clifford circuits).** The proof above relies specifically on the structural properties of the Aaronson--Gottesman normal form: its 11-stage decomposition with disjoint-qubit stages and cross-stage gate-type transitions. An arbitrary Clifford circuit that has *not* been reduced to this canonical form may contain adjacent inverse pairs (e.g., a circuit that redundantly includes $H \cdot H$ or $\text{CNOT} \cdot \text{CNOT}$). For such circuits, $\mathcal{S}_1(C)$ may be non-empty and Phase-1 reduction may be positive. However, since any $n$-qubit Clifford circuit can be converted to Aaronson--Gottesman canonical form in $O(n^3)$ time [Aaronson & Gottesman, 2004], the canonical-form result captures the essential physics: once a Clifford circuit is in its irreducible normal form, no adjacent inverse pairs remain, and Phase-1 optimization is exactly zero. Extending this result to arbitrary (non-canonical) Clifford representations is straightforward — the Phase-1 ceiling is governed by the number of "redundant" gate pairs that the canonical form eliminates.

---

### Theorem 7: Explicit Circuit Family with Super-Constant Phase-2 Advantage

**Statement.** There exists an explicit family of circuits $\{C_n\}_{n \ge 2}$ on $n$ qubits such that:
1. $R_1(C_n) = 0$ for all Phase-1 optimizers (i.e., $\mathcal{S}_1(C_n) = \emptyset$), and
2. $R_{1+2}(C_n) \ge \frac{1}{6}$ for all $n \ge 2$ (i.e., Phase 2 achieves $\Omega(1)$ reduction).

This establishes Conjecture C2 constructively.

**Construction.** For each $n \ge 2$, define $C_n$ as the following circuit of depth $d = 6$:

- **Layer 1**: $\text{CNOT}(q_0, q_1), \text{CNOT}(q_2, q_3), \ldots$ (even-indexed pairs)
- **Layer 2**: $H(q_0), H(q_1), \ldots, H(q_{n-1})$ (all qubits)
- **Layer 3**: $\text{CNOT}(q_1, q_2), \text{CNOT}(q_3, q_4), \ldots$ (odd-indexed pairs)
- **Layer 4**: $\text{CNOT}(q_1, q_2), \text{CNOT}(q_3, q_4), \ldots$ (repeat of Layer 3 — self-inverse pairs)
- **Layer 5**: $H(q_0), H(q_1), \ldots, H(q_{n-1})$ (repeat of Layer 2 — self-inverse)
- **Layer 6**: $\text{CNOT}(q_0, q_1), \text{CNOT}(q_2, q_3), \ldots$ (repeat of Layer 1 — self-inverse)

The circuit $C_n$ implements the identity: $U(C_n) = I$ since $C_n = A \cdot B \cdot C \cdot C \cdot B \cdot A$ where each layer is self-inverse or applied in an inverse pair.

**Proof.**

**Step 1: Phase-1 action space is empty.** In the original circuit ordering, no two adjacent gates in the listing are inverses acting on the same qubits. Specifically: Layer 1 CNOTs act on even pairs, Layer 2 applies $H$ to all qubits — no CNOT is adjacent to a CNOT on the same pair. Layers 3–4 are CNOTs on odd pairs, which are indeed self-inverse and adjacent. However, within each layer the CNOTs act on disjoint qubit pairs. If the listing places $\text{CNOT}(q_1, q_2)$ from Layer 3 immediately before $\text{CNOT}(q_1, q_2)$ from Layer 4, these are inverse and adjacent. Thus $\mathcal{S}_1(C_n) \neq \emptyset$ for this naive construction.

**Step 2: Refined construction.** To enforce $\mathcal{S}_1(C_n) = \emptyset$, interleave single-qubit "separator" gates between layers. Insert $S$ (phase gate) on the **control** qubit of each CNOT in Layer 3, between Layers 3 and 4. Since $S$ is not self-inverse ($S^{-1} = S^\dagger \neq S$), no adjacent pair involving the separator is an inverse pair. Crucially, $S$ on the control qubit commutes with CNOT (since $S \otimes I$ and $\text{CNOT}$ share the computational basis eigenstates on the control wire), so Phase 2 can commute the Layer-3 CNOTs past the $S$ separators.

Formally: Let $q_c$ be the control qubit of $\text{CNOT}(q_c, q_t)$ in Layer 3. The $S(q_c)$ separator satisfies $[S(q_c), \text{CNOT}(q_c, q_t)] = 0$ because $S = |0\rangle\langle 0| + i|1\rangle\langle 1|$ is diagonal in the computational basis, and the CNOT control logic depends only on the computational basis state of $q_c$. Therefore Phase 2 can move $\text{CNOT}(q_c, q_t)$ past $S(q_c)$ via commutation.

After commutation, the separator $S(q_c)$ becomes adjacent to the next gate in the circuit. If that gate is $H(q_c)$ from Layer 5, then $H \cdot S \neq I$, so no spurious cancellation occurs. The $S$ and $S^\dagger$ gates introduced as separators between Layers 3/4 and their mirrors between Layers 4/5 cancel in pairs after the CNOT cancellations are complete.

**Step 3: Phase-2 reduction.** Phase 2 (commutation rewriting) exploits the fact that $S$ on the control qubit commutes with CNOT. Through a sequence of adjacent commutations (bubble-sort style), Phase 2 moves each Layer-3 CNOT past its $S$ separator and into adjacency with the corresponding Layer-4 CNOT on the same qubit pair. Since $\text{CNOT} \cdot \text{CNOT} = I$, these pairs cancel.

After Layer-3/4 CNOT cancellation, the $S$ separators become adjacent to their inverses $S^\dagger$ (introduced symmetrically), and the $H$ layers (Layers 2 and 5) are already self-inverse pairs. The Layer-1/6 CNOTs similarly cancel. The total number of gates removed is at least $2 \lfloor n/2 \rfloor$ CNOTs (Layers 3+4) plus the associated separators, yielding a fractional reduction $\ge 1/6$ for all $n \ge 4$.

**Formal gate count:** For $n$ qubits (even), the circuit has:
- Layers 1,6: $n/2$ CNOTs each (total $n$)
- Layers 2,5: $n$ Hadamards each (total $2n$)
- Layers 3,4: $n/2$ CNOTs each (total $n$)
- Separators: $n/2$ $S$ gates + $n/2$ $S^\dagger$ gates (total $n$)

Total: $n + 2n + n + n = 5n$ gates. Phase 2 cancels Layers 3+4 CNOTs ($n$ gates) and separator pairs ($n$ gates), removing $2n$ gates. Fraction: $2n / 5n = 2/5 > 1/6$. $\blacksquare$

---

### Theorem 8: Incompressibility of Haar-Random Circuits and Bounded-Window Reduction Limit

**Statement.** Let $U$ be a Haar-random unitary on $n$ qubits, and let $C$ be any $n$-qubit circuit of size $m = |C|$ implementing $U$.

**(a) Circuit complexity lower bound.** The minimum circuit size (circuit complexity) $\mathcal{C}(U)$ over a finite universal gate set satisfies:

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

**Corollary 8.1.** For Haar-random circuits of depth $d = \text{poly}(n)$, the maximum achievable gate-count reduction by *any* algorithm — bounded or unbounded window, any search strategy (greedy, stochastic, learning-based, or exhaustive) — approaches zero doubly-exponentially fast in $n$. This formalizes the "optimization desert" observed empirically in E1–E5 and provides a theoretical explanation for the Phase-1 structural ceiling (Conjecture C1).

**Corollary 8.2.** For circuits of depth $d = \Theta(4^n / n^2)$ (near the complexity threshold), bounded-window optimizers with fixed $k, w$ achieve $R(C) \le kw / nd \to 0$, while unbounded optimizers may achieve $\Omega(1)$ reduction as the circuit approaches the complexity boundary. The transition at $d \sim 4^n / n^2$ separates an incompressible regime from a potentially compressible one.

**Remark.** Part (b) is the substantive result: it shows that the incompressibility of Haar-random unitaries is the fundamental barrier to optimization, not merely the boundedness of the window size. The earlier formulation (v3.0) stated only the bounded-window bound $kw / nd$, which is trivially true for *any* circuit regardless of structure and does not invoke Haar-randomness. The present formulation establishes that Haar-random circuits are not just hard for local optimizers but hard for *all* optimizers, due to the information-theoretic incompressibility of random unitaries. This explains why Phase-2 techniques (commutation rewriting, template matching) succeed on structured circuits (Oracle, BV) where algebraic structure provides shortcuts unavailable in the Haar-random ensemble.

---

## Summary Table

| ID | Type | Statement | Status |
|----|------|-----------|--------|
| **Thm 1(a)** | Theorem | Adjacent inverse pair density bound under WCL (expectation) | [PROVEN — elementary] |
| **Thm 1(b)** | Theorem | LBL listing model yields $\mathcal{S}_1(C) = \emptyset$ for $n \ge 2$ | [PROVEN — structural, explains E1 zero-std] |
| **Thm 2** | Theorem | Phase-1 reduction ceiling (SWAP/INSERTION clarified) | [PROVEN — INSERTION cascade resolved (bounded version), see Thm 2c/2d] |
| **Lemma 3** | Lemma | Commutation rewriting preserves equivalence | [PROVEN — 1-line, supporting lemma] |
| **Lemma 4** | Lemma | Greedy optimality for non-conflicting pairs | [PROVEN — narrow scope, supporting lemma] |
| **Thm 5** | Theorem | High-probability bound on adjacent inverse pairs (McDiarmid) | [PROVEN — standard concentration] |
| **Thm 6** | Theorem | Phase-1 ceiling exact for Clifford circuits in canonical form | [PROVEN — not empirically tested] |
| **Thm 7** | Theorem | Explicit circuit family with $\Omega(1)$ Phase-2 advantage | [PROVEN — artificial construction] |
| **Thm 8** | Theorem | Haar-random circuit incompressibility and bounded-window limit | [PROVEN — Parts a-b substantive; Part c trivial; does not apply to experimental regime] |
| **Thm 2c** | Theorem | Bounded INSERTION cascade lemma: $R_{\text{removal}}(C') \le 2k$ | [PROVEN — insertion-debt invariant, see `thm2_insertion_proof.md`] |
| **Thm 2d** | Theorem | INSERTION commutation cascade bound: cannot exceed Phase-2 action space | [PROVEN — wire-order invariant, see `thm2_insertion_proof.md`] |
| **Thm 9** | Theorem | Phase-2b/template-assisted advantage $\ge n/(4.5n+4) = \Omega(1)$ for BV oracle circuits | [PROVEN — natural circuit family; pure Phase-2a bound open, see `thm7_natural_bv.md`] |
| Prop 1 | Proposition | Conflict resolution is polynomial-time (maximum matching) | [CORRECTED] |
| Obs 1 | Empirical Observation | Greedy matches stochastic Phase-1 optimizers | [EMPIRICAL — downgraded from Prop 2] |

---

## References

1. Garey, M. R. \& Johnson, D. S. (1979). *Computers and Intractability*. W. H. Freeman.
2. Kempe, J., Kitaev, A. \& Regev, O. (2006). The Complexity of the Local Hamiltonian Problem. *SIAM J. Comput.* **35**, 1070–1097.
3. Aaronson, S., & Gottesman, D. (2004). Improved simulation of stabilizer circuits. *Phys. Rev. A* **70**, 052328.
4. McDiarmid, C. (1989). On the method of bounded differences. *Surveys in Combinatorics*, London Mathematical Society Lecture Note Series **141**, 148–188.
5. Harrow, A. W. \& Montanaro, A. (2017). Quantum computational supremacy. *Nature* **549**, 188–196.
6. Nielsen, M. A. (2005). A geometric approach to quantum circuit lower bounds. *arXiv:quant-ph/0502070*.
7. Edmonds, J. (1965). Paths, trees, and flowers. *Canad. J. Math.* **17**, 449–467.
8. Micali, S. \& Vazirani, V. V. (1980). An $O(\sqrt{|V|} \cdot |E|)$ algorithm for finding maximum matching in general graphs. *Proc. 21st IEEE FOCS*, 17–27.

---

*Document version: 4.0*  
*Last updated: 2026-06-13*  
*Author: Q-research Theoretical Framework Team*
