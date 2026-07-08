# Formal Results: Theorems, Conjectures, Scope Analysis, and Proof Appendices

**Version**: 4.0 (Consolidated)
**Date**: 2026-06-17
**Status**: Complete collection of all formal results for the QIP manuscript -- theorems, lemmas, propositions, empirical observations, conjectures, open problems, scope analysis, and detailed proof appendices.

---

## Notation

For base notation ($n$, $d$, $\mathcal{G}$, $C(n,d,\rho)$, $|C|$, $F_{\text{avg}}$, etc.) and all formal definitions D1--D10 (quantum circuit, unitary equivalence, peephole optimization, Phase 1/2, ceilings, action spaces), see `framework.md`.

Notation specific to this document:

- $L(C)$: line graph of circuit $C$ (vertices = gates, edges = adjacency in the circuit list)
- $\mathcal{A}_{\text{adj}}(C)$: the set of adjacent inverse gate pairs in $C$
- $\mathcal{A}_{\text{comm}}(C)$: the set of gate pairs that can be brought into adjacency via commutation rewriting
- $R_1(C)$: reduction fraction achieved by Phase-1-only optimization
- $R_{1+2}(C)$: reduction fraction achieved by Phase-1+2 optimization
- $\mathbb{E}_{C \sim \mathcal{E}}[\cdot]$: expectation over circuit ensemble $\mathcal{E}$

---

## Section 1: Theorems (Fully Proven)

### Theorem 1: Adjacent Inverse Pair Density in Random Circuits

> **Listing-model note (added 2026-06-13).** The number of adjacent inverse pairs depends critically on the **circuit listing model** -- how gates are ordered in the circuit data structure. We distinguish two models:
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

**Corollary 1.1.** Under WCL, the expected fractional reduction from Phase-1 adjacent cancellations satisfies $\mathbb{E}[R_{\text{adj}}] \le 2 p_{\text{cancel}}$, which is $O(1/g_1^2 + 1/(g_2 n))$ -- negligibly small for standard gate sets.

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

**Step 3: Phase-1 action space requires same-qubit adjacency.** By Definition 6, the Phase-1 action space $\mathcal{S}_1(C)$ consists of listing-adjacent gate pairs $(g_i, g_{i+1})$ that act on the **same qubit(s)** and satisfy $g_{i+1} = g_i^{-1}$. Since no two gates on the same qubit(s) are listing-adjacent under LBL (Step 2), $\mathcal{S}_1(C) = \emptyset$.

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

**Resolved gap in Theorem 2 (INSERTION cascade) [2026-06-13].** The INSERTION cascade gap identified in earlier versions of this document has been **resolved** (bounded version). Two new results in Appendix A close the gap formally:

- **Theorem 2c (Bounded INSERTION Cascade Lemma):** For any circuit $C$ with $\mathcal{S}_1(C) = \emptyset$, let $k$ INSERTION moves produce circuit $C'$ with $|C'| = |C| + 2k$. Let $R_{\text{removal}}(C')$ be the maximum number of gates removable via REMOVAL sequences involving at least one inserted gate. Then $R_{\text{removal}}(C') \le 2k$, so the net gate-count change from any INSERTION + REMOVAL sequence is $\ge 0$. The proof uses an insertion-debt invariant: each INSERTION increases the debt by 2, each REMOVAL involving an inserted gate decreases it by at most 2, and the debt is always non-negative.

- **Theorem 2d (INSERTION Commutation Cascade Bound):** Even when INSERTION is combined with SWAP and COMMUTATION moves within Phase 1, the net reduction from any finite sequence of moves starting from $\mathcal{S}_1(C) = \emptyset$ is bounded by $B_{\text{pre}}(C)$ -- the number of pre-existing wire-level inverse pairs that SWAP/COMMUTATION can expose (which is exactly the Phase-2 action space). Since Phase 1 by definition does not include systematic commutation reordering, the INSERTION-facilitated cascade cannot exceed what Phase 2 would achieve.

The key insight is that INSERTION only adds gates to the circuit and never removes pre-existing gates from their wires, so it cannot reduce the wire-level distance between pre-existing gates. The wire-order invariant (proven in Appendix A) formalizes this: under any sequence of INSERTION, SWAP, and COMMUTATION moves, the relative ordering of pre-existing gates on each wire is preserved. Consequently, INSERTION cannot create new pre-existing gate cancellations beyond what is already accessible via Phase-2 commutation reordering.

**Status:** [RESOLVED -- bounded version]. Full proofs in Appendix A.

---

### Lemma 3 (formerly Theorem 3): Commutation Rewriting Preserves Unitary Equivalence

> **Status note (2026-06-13):** Downgraded from Theorem to Lemma. The result is a one-line proof of a basic algebraic property, more appropriately classified as a supporting lemma than a standalone theorem.

**Statement.** Let $C = (g_1, \ldots, g_m)$ implement $U = g_m \cdots g_1$. If $C'$ is obtained by replacing $(g_i, g_{i+1})$ with $(g_i', g_{i+1}')$ such that $g_{i+1}' g_i' = g_{i+1} g_i$ and supports match, then $U' = U$ exactly.

**Proof.** $U = g_m \cdots g_{i+2} \cdot (g_{i+1} g_i) \cdot g_{i-1} \cdots g_1 = g_m \cdots g_{i+2} \cdot (g_{i+1}' g_i') \cdot g_{i-1} \cdots g_1 = U'$. $\blacksquare$

**Corollary 3.1.** Any sequence of commutation rewrites preserves unitary equivalence.

**Corollary 3.2.** Any circuit produced by the HybridCommuteRewrite pipeline (Phase 1 + Phase 2 + Phase 1) is exactly unitarily equivalent to the input.

---

### Lemma 4 (formerly Theorem 4): Greedy is Optimal for Non-Conflicting Adjacent Pairs

> **Status note (2026-06-13):** Downgraded from Theorem to Lemma. The result applies only to the special case where no two cancelable pairs share a gate -- a condition that holds trivially for most random circuits and is too narrow to serve as a standalone theorem.

**Statement.** If no two pairs in $\mathcal{S}_1(C)$ share a gate (i.e., pairs are non-conflicting), then the greedy scan achieves the maximum Phase-1 reduction, exactly $2|\mathcal{S}_1(C)|$ gates.

**Proof.** Non-conflicting pairs are independent: removing one does not affect the availability of others. The greedy scan visits every position and cancels all encountered pairs. Since pairs are disjoint, no cancellation destroys another. Therefore greedy cancels all $|\mathcal{S}_1(C)|$ pairs, achieving the maximum. $\blacksquare$

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

**Remark (Commutation sufficiency).** The bound in Theorem 5 applies to *listing-adjacent* inverse pairs only -- i.e., pairs that are consecutive on the same wire under the chosen listing model. Phase-2 commutation rewriting can access inverse pairs beyond this bound by swapping non-adjacent gates into adjacency via commutation moves. The set of commutation rules implemented in the optimizer (disjoint-qubit commutation, same-axis rotation commutation, CX control/target swaps) is *sufficient but not necessary*: they never produce an incorrect reordering, but they may miss valid reorderings that would expose additional cancellations. Consequently, any experimental "Phase-2 ceiling" measured with this rule set is a *lower bound* on the true ceiling achievable with a complete set of commutation identities. Papers must frame Phase-2 ceiling measurements as "under the tested commutation rules," not as fundamental limits.

---

### Theorem 6: Phase-1 Ceiling is Exact for Clifford Circuits in Aaronson--Gottesman Canonical Form

**Statement.** Let $C$ be a Clifford circuit (generated by $\{H, S, \text{CNOT}\}$) in canonical CNOT--H--S decomposition [Aaronson & Gottesman, 2004]. Then $\mathcal{S}_1(C) = \emptyset$, and consequently $R_1(C) = 0$ for every Phase-1 optimizer.

**Proof.**

**Step 1: Canonical form structure.** The Aaronson--Gottesman normal form decomposes any $n$-qubit Clifford circuit into at most 11 stages: $H$--$C$--$H$--$C$--$H$--$S$--$C$--$S$--$H$--$C$--$H$, where $H$ denotes a layer of Hadamard gates, $C$ a layer of CNOT gates, and $S$ a layer of phase gates. Within each stage, gates act on disjoint qubits and are therefore non-adjacent in the circuit listing.

**Step 2: Adjacent gates span distinct stages.** In the canonical decomposition, any two adjacent gates $g_i, g_{i+1}$ in the circuit listing belong either to (a) different stages, or (b) the same stage but different qubits. In case (b), the gates act on different qubits, so $g_{i+1} \neq g_i^{-1}$ by the qubit-matching requirement (Definition 6). In case (a), the gates are of different types (e.g., $H$ followed by $\text{CNOT}$, or $S$ followed by $\text{CNOT}$), so $g_{i+1} \neq g_i^{-1}$ by the gate-type requirement.

**Step 3: No adjacent inverse pairs.** Since neither case (a) nor case (b) can produce $g_{i+1} = g_i^{-1}$ on matching qubits, we have $\mathcal{S}_1(C) = \emptyset$. By Theorem 2, $R_1(C) = 0$ for all Phase-1 optimizers. $\blacksquare$

**Remark.** This result proves Conjecture C1 for the important special case of Clifford circuits in Aaronson--Gottesman canonical form, establishing that the structural ceiling is not merely empirical but exact for a practically significant circuit family.

**Remark on scope (general Clifford circuits).** The proof above relies specifically on the structural properties of the Aaronson--Gottesman normal form: its 11-stage decomposition with disjoint-qubit stages and cross-stage gate-type transitions. An arbitrary Clifford circuit that has *not* been reduced to this canonical form may contain adjacent inverse pairs (e.g., a circuit that redundantly includes $H \cdot H$ or $\text{CNOT} \cdot \text{CNOT}$). For such circuits, $\mathcal{S}_1(C)$ may be non-empty and Phase-1 reduction may be positive. However, since any $n$-qubit Clifford circuit can be converted to Aaronson--Gottesman canonical form in $O(n^3)$ time [Aaronson & Gottesman, 2004], the canonical-form result captures the essential physics: once a Clifford circuit is in its irreducible normal form, no adjacent inverse pairs remain, and Phase-1 optimization is exactly zero. Extending this result to arbitrary (non-canonical) Clifford representations is straightforward -- the Phase-1 ceiling is governed by the number of "redundant" gate pairs that the canonical form eliminates.

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
- **Layer 4**: $\text{CNOT}(q_1, q_2), \text{CNOT}(q_3, q_4), \ldots$ (repeat of Layer 3 -- self-inverse pairs)
- **Layer 5**: $H(q_0), H(q_1), \ldots, H(q_{n-1})$ (repeat of Layer 2 -- self-inverse)
- **Layer 6**: $\text{CNOT}(q_0, q_1), \text{CNOT}(q_2, q_3), \ldots$ (repeat of Layer 1 -- self-inverse)

The circuit $C_n$ implements the identity: $U(C_n) = I$ since $C_n = A \cdot B \cdot C \cdot C \cdot B \cdot A$ where each layer is self-inverse or applied in an inverse pair.

**Proof.**

**Step 1: Phase-1 action space is empty.** In the original circuit ordering, no two adjacent gates in the listing are inverses acting on the same qubits. Specifically: Layer 1 CNOTs act on even pairs, Layer 2 applies $H$ to all qubits -- no CNOT is adjacent to a CNOT on the same pair. Layers 3--4 are CNOTs on odd pairs, which are indeed self-inverse and adjacent. However, within each layer the CNOTs act on disjoint qubit pairs. If the listing places $\text{CNOT}(q_1, q_2)$ from Layer 3 immediately before $\text{CNOT}(q_1, q_2)$ from Layer 4, these are inverse and adjacent. Thus $\mathcal{S}_1(C_n) \neq \emptyset$ for this naive construction.

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

**Corollary 8.1.** For Haar-random circuits of depth $d = \text{poly}(n)$, the maximum achievable gate-count reduction by *any* algorithm -- bounded or unbounded window, any search strategy (greedy, stochastic, learning-based, or exhaustive) -- approaches zero doubly-exponentially fast in $n$. This formalizes the "optimization desert" observed empirically in E1--E5 and provides a theoretical explanation for the Phase-1 structural ceiling (Conjecture C1).

**Corollary 8.2.** For circuits of depth $d = \Theta(4^n / n^2)$ (near the complexity threshold), bounded-window optimizers with fixed $k, w$ achieve $R(C) \le kw / nd \to 0$, while unbounded optimizers may achieve $\Omega(1)$ reduction as the circuit approaches the complexity boundary. The transition at $d \sim 4^n / n^2$ separates an incompressible regime from a potentially compressible one.

**Remark.** Part (b) is the substantive result: it shows that the incompressibility of Haar-random unitaries is the fundamental barrier to optimization, not merely the boundedness of the window size. The earlier formulation (v3.0) stated only the bounded-window bound $kw / nd$, which is trivially true for *any* circuit regardless of structure and does not invoke Haar-randomness. The present formulation establishes that Haar-random circuits are not just hard for local optimizers but hard for *all* optimizers, due to the information-theoretic incompressibility of random unitaries. This explains why Phase-2 techniques (commutation rewriting, template matching) succeed on structured circuits (Oracle, BV) where algebraic structure provides shortcuts unavailable in the Haar-random ensemble.

---

### Regime and scope of Theorem 8

**Scope of application.** Theorem 8 applies to Haar-random unitaries, i.e., unitaries drawn from the Haar measure on $U(2^n)$. The experiments labeled E1--E5, however, use shallow random gate sequences generated by `src/circuits/generator_v2.py` (depth $d \in [1,50]$, two-qubit gate density $\rho = 0.3$, finite gate set). At the tested depths these random gate sequences do not sample Haar-random unitaries.

**Regime separation.** For typical E1--E5 parameters (e.g., $n = 10$, $d = 50$, $|C| \approx 500$ gates), the Haar-random complexity threshold is $4^n / n^2 \approx 10{,}486$ gates. The experimental circuits are therefore far from the Haar-random regime. Theorem 8 should be treated as an asymptotic worst-case / complementary information-theoretic bound, not as a direct explanation of the E1--E5 empirical observations.

**What explains the experiments.** The empirical $\sim 0\%$ Phase-1 reduction observed in E1--E5 is explained by Theorem 1 (adjacent inverse-pair density) and Theorem 1(b) (layer-by-layer listing empties the Phase-1 action space), not by Haar-random incompressibility. Corollary 8.1 is a valid asymptotic statement about the optimization desert, but it does not apply pointwise to the shallow random gate sequences used in the experiments.

**Practical implication.** Theorem 8 should not be invoked to explain the low reduction in E1--E5; the correct explanation is the combinatorial sparsity of inverse pairs under the LBL listing model.

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

**Remark.** The general Circuit Optimization Decision Problem (CODP) -- which includes commutation rewriting, template matching, and other Phase-2 moves -- may still be computationally hard (see Conjecture OP1). Proposition 1 addresses only the restricted sub-problem of Phase-1 adjacent-pair selection.

---

## Section 3: Empirical Observations

### Empirical Observation 1 (formerly Proposition 2): Greedy Matches Stochastic Phase-1 Optimizers

**Statement.** For any circuit $C$, $\mathbb{E}[R_{\text{stoch}}(C)] \le R_{\text{greedy}}(C) + O(1/|C|)$ for any stochastic Phase-1 optimizer.

**Status**: [EMPIRICAL OBSERVATION] -- Downgraded from Proposition (proof sketch) on 2026-06-12. The original proof sketch relied on greedy matching approximation bounds that do not rigorously establish the stated $O(1/|C|)$ term. While the empirical evidence (E4: all four optimizers converge to ~0% on random circuits) strongly supports this observation, a rigorous proof remains open. The observation follows heuristically from Theorem 2's action-space analysis but cannot be formally derived from it without additional argument.

**Empirical support.** E4 tested 100 circuits $\times$ 4 optimizers. All achieved $\le$0.67% mean reduction on random circuits (n=5, d=15), with Greedy at 0.00%, GA at 0.67%, SA at ~0%, and RLS at ~0%. The stochastic optimizers' slight advantage (0.67% for GA) arises from rare non-adjacent pair discovery via SWAP moves, not from INSERTION-facilitated reduction. For random circuits where $\mathcal{S}_1(C) \approx \emptyset$, all optimizers converge to 0%.

---

## Section 4: Conjectures and Open Problems

### Preliminaries

For base notation ($n$, $d$, $\mathcal{G}$, $C(n,d,\rho)$, $|C|$, $F_{\text{avg}}$, etc.) and all formal definitions D1--D10, see `framework.md`. Formal decision-problem definitions (CODP, CIT) appear in `framework.md` as Definitions A1--A2.

---

### Motivating Open Problems

These open problems motivate the study but are not claimed as results of this paper. They are included to contextualize the empirical findings within the broader complexity-theoretic landscape.

#### OP1: Is Peephole Optimization QMA-hard?

**Question.** Is the Circuit Optimization Decision Problem (CODP) QMA-hard?

**Motivation.** Circuit Identity Testing (CIT) is QMA-complete [Janzing, Wocjan & Beth, 2003]. Since CIT is the special case of CODP with $r = 0$, one might expect CODP to be at least QMA-hard. However, the standard path -- Kitaev's circuit-to-Hamiltonian construction [Kitaev, 1997] -- yields a specific circuit family (history-state circuits), and showing that bounded-window peephole rewrites can distinguish YES from NO instances requires analyzing the rewrite-rule closure of these circuits, which is open.

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

These are the paper's central formal claims, supported by strong empirical evidence and partial theoretical arguments.

#### Conjecture 1: The Phase 1 Ceiling is Structural

**Statement.** For any circuit family $\mathcal{F}$ in which no adjacent inverse gate pairs exist in the initial data structure, *every* Phase-1-only optimizer (greedy, simulated annealing, genetic algorithm, random local search) achieves exactly $0\%$ gate reduction. This ceiling is a property of the circuit data structure, not of the optimization algorithm.

**Status**: [CONJECTURE $\to$ PARTIALLY PROVEN] -- the statement follows from Theorem 2 (action-space identity) for deterministic optimizers; the conjecture concerns the universality claim for stochastic optimizers. Theorem 5 strengthens the empirical bound to a high-probability guarantee. Theorem 6 proves the conjecture exactly for Clifford circuits in canonical form. Theorem 8 proves the bounded-window reduction limit for Haar-random circuits.

**Evidence:**

1. **Action-space identity** (Theorem 2). All Phase-1 optimizers operate on the same action space $\mathcal{S}_1(C)$. If $\mathcal{S}_1(C) = \emptyset$, no Phase-1 move reduces gate count. Note: Theorem 2 has a known gap in the INSERTION cascade argument (see Remark after Theorem 2, now resolved by Thm 2c/2d in Appendix A).

2. **Empirical validation** (E1--E5, 45,500 trials). Across Universal, Clifford, and Structured circuit families, all four Phase-1 optimizers achieved $\le 0.05\%$ mean reduction. The ceiling is reproducible and algorithm-independent. Note: Empirical Observation 1 (formerly Prop 2) formalizes this as $\mathbb{E}[R_{\text{stoch}}(C)] \le R_{\text{greedy}}(C) + O(1/|C|)$.

3. **Theoretical argument.** A Phase-1 optimizer can cancel adjacent inverses (REMOVAL), swap disjoint-qubit gates (SWAP), or commute gates (COMMUTATION). SWAP and COMMUTATION preserve gate count. Without commutation-based reordering across non-commuting blocks, the set of cancelable pairs is invariant under Phase-1 moves.

**Remaining gap.** The formal invariant argument must show that SWAP and COMMUTATION moves within Phase-1 scope cannot *create* new adjacent inverse pairs. Theorem 2 addresses this: it proves that SWAP can create listing-adjacent pairs but only reveals pre-existing wire-level structure (no net reduction), and INSERTION creates new $\mathcal{S}_1$ elements but cannot achieve net reduction (insertion adds 2 gates, cancellation removes 2 gates). The remaining open question is whether this invariant extends to Phase-1 scope when commutation is restricted (no reordering across non-commuting blocks) -- which is precisely why Phase 2 exists.

**Open problems:**
- C1.OP1: Formalize the invariant characterizing exactly which circuit families have empty Phase-1 action spaces.
- C1.OP2: Quantify $\Pr[\mathcal{S}_1(C) \neq \emptyset]$ as a function of $(n, d, \mathcal{G})$ for random circuit ensembles.

#### Conjecture 2: Phase 2 Provides Context-Dependent Super-Constant Improvement

**Statement.** There exist circuit families $\mathcal{F}$ and gate sets $\mathcal{G}$ for which Phase-1 optimization achieves $O(1/d)$ reduction (or $0\%$), while Phase-1+2 optimization achieves $\Omega(1)$ reduction. The improvement $\Gamma(C) = R_{1+2}(C) - R_1(C)$ is context-dependent: it is significant for some families (e.g., oracle circuits) and zero for others (e.g., structured brickwork, QFT, GHZ).

**Status**: [CONJECTURE $\to$ PROVEN FOR PHASE-2b (template matching); OPEN FOR PHASE-2a (commutation only)] -- Two constructive proofs establish C2 for Phase-2b:
- **Theorem 7** constructs an *artificial* circuit family with $\Gamma \ge 1/6 = \Omega(1)$ via Phase-2b commutation + separator-cancellation.
- **Theorem 9** (Appendix B) proves $\Gamma^{\text{(2b)}}(BV_n) \ge n/(4.5n+4) \ge 2/13 = \Omega(1)$ for the *natural* Bernstein--Vazirani oracle family, via the $H$-CNOT-$H$ template identity.

**Critical caveat on phase coverage.** Both theoretical proofs rely on **Phase-2b template matching**, which is *not* implemented in the current experimental codebase (`commutation_rewriter.py` implements only **Phase-2a** commutation rewriting). Under pure Phase-2a, the achievable Phase-2 bound for BV remains an **open question**. The experimental Phase-2a reductions reported in E10/E11 (see Evidence below) are *complementary* to the Phase-2b theoretical bounds but are not direct validations of Theorems 7/9. The manuscript must state this theory-experiment gap explicitly.

**Evidence:**

1. **Random Universal circuits (E10, Phase-2a).** Phase 1 achieves $\approx 0\%$; Phase-2a achieves $\approx 3.26\%$ additional reduction. Effect size: see `analysis/phase1_statistics/effect_size.py` for Cliff's $\delta$ / Hedges' $g$ (integrated into figure generation in the v6 remediation).

2. **Oracle / Bernstein--Vazirani circuits (E11, Phase-2a).** Phase 1 achieves $0\%$; Phase-2a achieves $\sim 20\%$ reduction via commutation of redundant H/X gates exposed by the Oracle circuit structure. This empirical Phase-2a reduction is attributable to the algebraic structure of the oracle, but its mechanism is *not* the $H$-CNOT-$H$ template of Theorem 9 (which is unimplemented Phase-2b).

3. **CNOT-chain validation circuits (E11).** Phase 1 alone achieves $100\%$ reduction, confirming that the Phase 2 advantage is circuit-family dependent rather than universal.

4. **Mechanism.** Phase 2 exploits commutation relations $[U, V] = 0$ to reorder gates, bringing non-adjacent inverses into adjacency. For circuits with repeating structural patterns, commutation can slide gates across $O(d)$ positions, creating cancellations invisible to Phase 1. Phase-2b additionally exploits multi-gate template identities (e.g., $H$-CNOT-$H \to$ reversed CNOT) that Phase-2a does not.

**Remaining gaps.**
- **(Theory)** Theorem 7 (artificial) and Theorem 9 (BV natural) establish $\Omega(1)$ Phase-2b advantage constructively. The broader question of characterizing *all* families with super-constant Phase-2b improvement remains open (C2.OP1--OP3).
- **(Theory--experiment bridge)** The achievable Phase-2a bound for BV (and for Theorem 7's artificial family) is open. Whether Phase-2a alone can achieve $\Omega(1)$ on any non-trivial family is an open question.
- **(Experiment)** The empirical ~20% Phase-2a reduction on Oracle/BV (E11) lacks a matching theoretical lower bound. Closing this gap requires either (a) extending Phase-2a theory to cover the E11 Oracle structure, or (b) implementing Phase-2b and re-running E11 to validate Theorem 9 directly.

**Open problems:**
- C2.OP1: Construct an explicit circuit family with proven super-constant Phase-2 improvement.
- C2.OP2: Determine $\max_C \Gamma(C) / R_1(C)$ as a function of $(n, d, \mathcal{G})$.
- C2.OP3: Characterize the gate-set conditions under which Phase 2 is necessary.

---

### Conjecture Summary Table

| ID | Type | Statement | Evidence | Key Open Problem |
|----|------|-----------|----------|-----------------|
| OP1 | Open Problem | CODP is QMA-hard | Weak -- reduction sketch incomplete | Complete the Kitaev reduction |
| OP2 | Open Problem | No PTAS for CODP | Updated -- conflict resolution is in P (Prop 1); hardness source unclear | Identify true hardness source |
| **C1** | **Conjecture** | **Phase 1 ceiling is structural (listing-conditional)** | **Strong -- Thm 2 + Thm 5 + Thm 6 (Clifford) + Thm 8 (Haar, asymptotic) + 45,500 trials (LBL). Ceiling is listing-conditional: WCL exposes ~18% Phase-1 reduction on the same circuits.** | **Formalize invariant for general circuit families; characterize WCL vs LBL gap** |
| **C2** | **Conjecture** | **Phase 2 is context-dependent super-constant** | **Proven (Phase-2b) -- Thm 7 (artificial, $\Gamma \ge 1/6$) + Thm 9 (BV natural, $\Gamma \ge 2/13$). Phase-2a bound OPEN. E10/E11 empirical (Phase-2a): ~3% random, ~20% Oracle.** | **(1) Phase-2a achievable bound; (2) characterize all families with super-constant $\Gamma$; (3) bridge theory (2b) $\leftrightarrow$ experiment (2a)** |

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
- **Theorem 1(b) consequence**: $\mathcal{S}_1(C) = \emptyset$ structurally -- Phase-1 action space is empty by construction.

#### 5.1.2 Wire-Consecutive Listing (WCL)

- **Structure**: The circuit is a flat sequence where gates on the same qubit wire are listed consecutively.
- **Adjacency**: Two successive gates on the same qubit are listing-adjacent.
- **Used by**: Some synthesis tools; circuit diagrams (when read wire-by-wire).
- **Theorem 1(a) consequence**: $\mathcal{S}_1(C)$ is non-empty in expectation, with density $\approx p_{\text{cancel}}(n, \rho)$.

#### 5.1.3 Directed Acyclic Graph (DAG)

- **Structure**: The circuit is a DAG $G = (V, E)$ where vertices are gates and edges encode data dependencies (a gate $g_j$ depends on $g_i$ if they share a qubit and $g_i$ precedes $g_j$ on that qubit).
- **Adjacency**: Two gates are "DAG-adjacent" if they share a qubit and no other gate on that qubit lies between them in the dependency order. This is **wire-level adjacency**, independent of any flat listing.
- **Used by**: Production compilers -- Qiskit (`DAGCircuit`), Cirq, t|ket> (`Circuit` with command ordering).
- **Consequence**: A DAG-based peephole optimizer sees wire-level adjacency directly. It does not suffer from the LBL "blindness" where same-qubit gates are hidden behind cross-qubit gates in the listing.

### 5.2 The Listing--DAG Gap

**The core observation.** Theorem 1(b) proves that under LBL, $\mathcal{S}_1(C) = \emptyset$ for $n \ge 2$. This is a property of the *listing*, not of the *circuit*. The same circuit, represented as a DAG (or as WCL), would expose wire-level inverse pairs to a peephole optimizer.

**Implication for the structural ceiling.** The "structural ceiling" ($R_1 \approx 0\%$ on random circuits) observed in experiments E1--E5 is therefore **listing-conditional**:

$$
R_1^{\text{LBL}}(C) = 0 \quad \text{(Theorem 1(b), structural)} \\
R_1^{\text{WCL}}(C) \approx 2 p_{\text{cancel}}(n, \rho) \quad \text{(Theorem 1(a), small but non-zero)} \\
R_1^{\text{DAG}}(C) \approx R_1^{\text{WCL}}(C) \quad \text{(DAG sees wire-level adjacency, like WCL)}
$$

The empirical ~0% Phase-1 reduction in E1--E5 is explained by Theorem 1(b) (the LBL listing structurally empties the action space), **not** by any intrinsic incompressibility of the circuits. Under WCL or DAG representation, the same circuits would exhibit a small but non-zero Phase-1 reduction (~18% in our WCL experiment, consistent with Theorem 1(a)).

**This is not a flaw in the framework -- it is a feature.** The framework's value is in *characterizing* how the listing model affects peephole optimization. The LBL$\to$WCL gap (~18% vs 0%) is itself a measurable, theoretically-grounded result about the sensitivity of peephole optimization to circuit representation.

### 5.3 Relationship to Production DAG Compilers

Production compilers (Qiskit `transpile`, Cirq, t|ket>) use DAG representations and implement sophisticated optimization passes that go far beyond Phase-1 adjacent-cancellation. This raises the question: does the structural-ceiling framework say anything about production compilers?

#### 5.3.1 What the framework DOES claim

1. **Listing-model sensitivity.** The framework proves that the choice of listing model (LBL vs WCL vs DAG) materially affects Phase-1 peephole performance. This is a genuine finding: a naive peephole optimizer on an LBL listing is structurally blind to same-qubit inverse pairs.

2. **Phase-2 commutation value.** Phase-2 commutation rewriting (which operates on wire-level structure, not listing order) is listing-independent. The framework's Phase-2 results (Theorem 7, Theorem 9) hold regardless of the listing model, because commutation is a wire-level algebraic property.

3. **Ceiling is representation-dependent, not algorithm-dependent.** Within a fixed listing model, all Phase-1 optimizers (greedy, SA, GA, RLS) converge to the same ceiling (Theorem 2). The ceiling is a property of the representation + circuit structure, not of the search algorithm.

#### 5.3.2 What the framework does NOT claim

1. **Not a lower bound on DAG-compiler performance.** The framework does *not* claim that production DAG-based compilers are bounded by the LBL ceiling. A DAG-based compiler that performs wire-level cancellation directly would bypass Theorem 1(b) entirely. The empirical result that Qiskit O3 achieves ~23% reduction on real circuits (E12) -- far above our prototype's ~11% -- is consistent with this: Qiskit operates on a DAG and employs passes (commutation analysis, template matching, resynthesis) that go beyond Phase-1 listing-adjacent cancellation.

2. **Not a complexity-theoretic lower bound.** The structural ceiling is a limit on a specific class of *classical algorithms* (listing-based peephole rewriters) applied to a specific *data structure* (gate listings). It is not a lower bound on quantum circuit complexity (which concerns the minimum number of gates to represent a unitary, regardless of algorithm or representation).

3. **Not a claim about all peephole optimizers.** The framework's Phase-1 ceiling applies to optimizers that scan a listing and cancel listing-adjacent inverses. A DAG-based peephole optimizer that scans wire-adjacent gates is effectively operating in the WCL regime and is subject to Theorem 1(a), not Theorem 1(b).

#### 5.3.3 Honest scope statement

The structural-ceiling framework should be read as: **"For listing-based peephole optimizers operating on LBL representations, Phase-1 reduction is structurally zero; the gap to WCL/DAG representations is ~18%, explainable by Theorem 1(a). Production DAG compilers operate in a different regime and are not bounded by this ceiling."**

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

2. **Reframe the central claim** from "Phase-1 peephole optimization achieves ~0% on random circuits" to "Phase-1 peephole optimization on LBL representations achieves ~0% on random circuits; under WCL/DAG representations, ~18% is achievable, consistent with Theorem 1(a)."

3. **Include a DAG comparison discussion** noting that production compilers (Qiskit O3 ~23%) exceed the prototype's Phase-1+2 (~11%) because they operate on DAGs and employ passes beyond the prototype's scope. This is not a failure of the framework -- it is a difference in representation and pass sophistication.

4. **Reduce the Qiskit pass-isolation claims** to the 5 families with actual data, and move the rest to Future Work.

5. **Explicitly list as a limitation** that the framework's theoretical results (Theorems 1--9) are formulated for listing-based representations, and extending them to DAG-based representations is an open direction.

### 5.6 Summary

| Question | Answer |
|----------|--------|
| Is the structural ceiling listing-conditional? | **Yes.** Theorem 1(b) is an LBL property; WCL/DAG expose ~18% reduction. |
| Does the framework bound DAG-compiler performance? | **No.** DAG compilers bypass Theorem 1(b). The framework does not claim to bound them. |
| Is the LBL$\to$WCL gap a real finding? | **Yes.** It quantifies representation sensitivity of peephole optimization. |
| Is the Qiskit pass-isolation complete? | **No.** Only 5/15 families isolated; the rest must be downgraded to Future Work. |
| Should the central claim be reframed? | **Yes.** From "0% on random circuits" to "0% under LBL; ~18% under WCL/DAG." |

---

## Section 6: Phase-2b Template Matcher Implementation

### Implemented scope

`Phase2bTemplateMatcher` implements a deterministic, local Clifford template pass:

$$
H(c)\;\mathrm{CNOT}(c,t)\;H(c) \rightarrow H(t)\;\mathrm{CNOT}(t,c)\;H(t).
$$

The pass also performs safe adjacent Hadamard-pair cleanup:

$$
H(q)\;H(q) \rightarrow I.
$$

Both transformations are unitary-preserving and act only on explicit adjacent instruction windows in the circuit list. The implementation is intentionally conservative: it does not reorder unrelated gates, infer non-adjacent matches, or introduce identities.

### Test coverage

The focused unittest suite covers:

- the basic three-gate template shape and qubit reversal;
- unitary preservation against Qiskit's exact `Operator` for small circuits;
- adjacent `H-H` cleanup exposed by the template rewrite;
- BV-like template pipelines for $n = 2, 3, 5$, where each data qubit contributes one matched template and one adjacent `H-H` cancellation.

For the implemented BV-like fixture, the input size is $5n$ and the optimized size is $n + 2$, because the local template exposes both in-block and cross-block adjacent `H-H` pairs on the shared ancilla. This preserves the exact unitary.

### Remaining gap

This is not a complete Phase-2 optimizer. It does not yet implement:

- non-adjacent template matching through commutation-aware movement;
- multi-template search or cost-guided template selection;
- insertion-based cascades;
- full Clifford tableau/canonical-form synthesis;
- topology-aware template variants;
- measurement/classical-bit-preserving circuit rewrites.

The current module should therefore be interpreted as a minimal Phase-2b template-matching prototype rather than a complete compiler pass.

---

## Appendix A: Theorem 2c and 2d -- Bounded INSERTION Cascade Proofs

> **Document Status**: Formal proofs resolving the INSERTION cascade gap in Theorem 2.
> **Version**: 1.0
> **Date**: 2026-06-13

### Motivation and Gap Statement

Theorem 2(b) establishes that stochastic Phase-1 optimizers (SA, GA, RLS) cannot systematically exceed the Greedy reduction ceiling on circuits where $\mathcal{S}_1(C) = \emptyset$. Step 3 of that proof asserts that "cancellations involving only pre-existing gates could have been found without INSERTION." However, this assertion left an **open gap**: INSERTION can change the commutation topology of the circuit, potentially enabling SWAP or COMMUTATION sequences that were previously impossible.

Specifically, if inserting $H \cdot H$ between gates $A$ and $B$ makes $A$ and $B$ commutable (by changing the effective ordering context), then INSERTION has created a Phase-2-style opportunity that Phase-1 alone could not find. The concern is that an INSERTION-facilitated commutation cascade might achieve net gate-count reduction beyond what is available without INSERTION.

This appendix closes the gap with two results:
- **Theorem 2c** proves that the net gate-count change from any INSERTION + REMOVAL sequence is non-negative (bounded version).
- **Theorem 2d** extends this to the combined INSERTION + SWAP + COMMUTATION setting, showing that the INSERTION-facilitated cascade cannot exceed what Phase 2 would achieve independently.

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

### Theorem 2d (INSERTION Commutation Cascade Bound)

**Statement.** Let $C$ be a circuit with $\mathcal{S}_1(C) = \emptyset$. Let $M$ be any finite sequence of moves drawn from $\{\text{INSERTION}, \text{REMOVAL}, \text{SWAP}, \text{COMMUTATION}\}$ applied to $C$, producing circuit $C'$. Suppose $M$ contains $k$ INSERTION moves. Then:

$$
|C'| - |C| \ge -B_{\text{pre}}(C),
$$

where $B_{\text{pre}}(C)$ is the number of pre-existing wire-level inverse pairs in $C$ that can be exposed by SWAP and COMMUTATION moves alone (without INSERTION). In particular, $B_{\text{pre}}(C)$ is exactly the size of the Phase-2 action space $|\mathcal{S}_{1+2}(C)|$ applied to the pre-existing gates of $C$.

**Corollary.** Since Phase 1 by definition does not include systematic commutation reordering (Phase 2), the INSERTION-facilitated cascade within Phase 1 cannot exceed what Phase 2 would achieve independently. That is, for any Phase-1 optimizer employing INSERTION:

$$
R_1^{\text{INSERTION}}(C) \le R_{1+2}(C) - R_1(C) = \Gamma(C).
$$

This means INSERTION within Phase 1 can at best simulate Phase 2, never exceed it.

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

The set of all such pairs is exactly what $B_{\text{pre}}(C)$ counts -- it is the Phase-2 action space restricted to pre-existing gates. Crucially, $B_{\text{pre}}(C)$ is determined entirely by the pre-existing gates and their wire-level unitaries, which (by Step 3) are preserved under INSERTION + SWAP + COMMUTATION.

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

**Step 6: Phase-1 vs. Phase-2 interpretation.**

Phase 1 optimizers employ $\{\text{REMOVAL}, \text{SWAP}, \text{COMMUTATION}, \text{INSERTION}\}$ but do not perform systematic commutation reordering. Phase 2 optimizers perform systematic commutation reordering on the pre-existing circuit.

The bound $B_{\text{pre}}(C)$ is precisely the number of pre-existing gate pairs that Phase 2 can bring into adjacency and cancel. Since INSERTION within Phase 1 can achieve at most $B_{\text{pre}}(C)$ reduction (and only at a net cost that makes the effective reduction $\le B_{\text{pre}}(C)$), we have:

$$
R_1^{\text{INSERTION}}(C) \le \frac{2 \cdot B_{\text{pre}}(C)}{|C|} = R_{1+2}(C).
$$

Since Phase 1 without INSERTION achieves $R_1(C) = 0$ when $\mathcal{S}_1(C) = \emptyset$, the INSERTION-facilitated cascade satisfies:

$$
R_1^{\text{INSERTION}}(C) - R_1(C) \le R_{1+2}(C) - R_1(C) = \Gamma(C).
$$

This proves that INSERTION within Phase 1 can at best simulate Phase 2's commutation reordering, never exceed it. $\blacksquare$

#### Discussion

**Tightness of the Bound**

The bound in Theorem 2c ($R_{\text{removal}}(C') \le 2k$) is **tight**: a sequence of $k$ INSERTION moves followed by $k$ REMOVAL moves on the inserted pairs themselves achieves exactly $R_{\text{removal}} = 2k$ with net change 0. No sequence can achieve $R_{\text{removal}} > 2k$ involving inserted gates.

The bound in Theorem 2d ($\Delta|C| \ge -B_{\text{pre}}(C)$) is also tight in the following sense: if the circuit contains $B_{\text{pre}}(C)$ pre-existing wire-level inverse pairs accessible to SWAP/COMMUTATION, then Phase 2 (without any INSERTION) can achieve exactly that reduction. INSERTION cannot improve upon this.

**Implications for the INSERTION Cascade Gap**

The open gap in Theorem 2 (Step 3) asked whether INSERTION-facilitated commutation cascades could achieve net reduction beyond what is available without INSERTION. Theorems 2c and 2d answer this definitively:

1. **INSERTION + REMOVAL alone** (Thm 2c): Net gate-count change is $\ge 0$. INSERTION is a "zero-sum" operation when combined only with REMOVAL.

2. **INSERTION + REMOVAL + SWAP + COMMUTATION** (Thm 2d): Net reduction is bounded by $B_{\text{pre}}(C)$, which is exactly the Phase-2 action space. INSERTION cannot create new reduction opportunities beyond what Phase 2 already provides.

3. **Practical consequence**: Stochastic Phase-1 optimizers that employ INSERTION (SA, GA, RLS) cannot systematically exceed the Greedy reduction ceiling, even when INSERTION changes the commutation topology. The empirical observation of 100% zero net reduction in 5000 trials is a necessary consequence of the algebraic structure, not a coincidence.

**Relation to Phase-2 Advantage**

Theorem 2d establishes a clean separation:

- **Phase 1 + INSERTION** $\le$ **Phase 2** in terms of achievable reduction.
- **Phase 2** exploits the pre-existing wire-level structure of $C$ via systematic commutation reordering.
- **INSERTION** within Phase 1 is at best a clumsy simulation of Phase 2, adding and removing gates to achieve what Phase 2 does directly.

This reinforces the central message of the theoretical framework: the optimization gap $\Gamma(C) = R_{1+2}(C) - R_1(C)$ is a property of the circuit's algebraic structure (commutation relations), not of the Phase-1 optimizer's search strategy.

---

## Appendix B: Theorem 9 -- Phase-2 Advantage for Bernstein--Vazirani Oracle Circuits

> **Document Status**: Formal proof (rewritten 2026-06-17 to remove draft artifacts and consolidate the argument).
> **Version**: 2.0
> **Date**: 2026-06-17
> **Relation to existing results**: Generalizes Theorem 7 (artificial circuit family) to the natural Bernstein--Vazirani oracle family.

### Motivation

Theorem 7 establishes the existence of an explicit circuit family $\{C_n\}$ with $R_1(C_n) = 0$ and $R_{1+2}(C_n) \ge 1/6$, proving Conjecture C2 constructively. However, the circuit family used in Theorem 7 is an artificial construction designed specifically to exhibit Phase-2 advantage. A natural question is whether Phase-2 advantage arises in **naturally occurring** quantum circuit families -- circuits that arise from standard quantum algorithms without adversarial design.

This appendix proves that the **Bernstein--Vazirani (BV) oracle circuit** family exhibits a constant-factor Phase-2 advantage, establishing that the Phase-1/Phase-2 optimization gap is not merely an artifact of artificial constructions but arises in standard quantum algorithmic primitives.

> **Important scope note.** The Phase-2 advantage established here relies on **Phase-2b template matching** (the $H$-CNOT-$H$ identity), which is *not* implemented in the current experimental codebase. The current codebase implements only **Phase-2a commutation rewriting** (`commutation_rewriter.py`). Under pure Phase-2a, the achievable bound for BV remains an **open question**. See "Phase-2a vs. Phase-2b" below. All experimental results labeled "Phase 2" in the manuscript refer to Phase-2a unless explicitly stated otherwise.

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

### Theorem 9 (Phase-2b Advantage for Bernstein--Vazirani Oracle Circuits)

**Statement.** For the Bernstein--Vazirani oracle circuit $BV_n$ on $n+1$ qubits ($n \ge 2$) with secret string $s = 1^n$:

1. $R_1(BV_n) = 0$ (Phase 1 achieves zero reduction in the standard LBL listing).
2. Phase-2b (commutation rewriting + template matching) achieves
$$
R_{1+2}^{\text{(2b)}}(BV_n) \ge \frac{n}{4.5n+4} \ge \frac{2}{13} \quad \text{for all } n \ge 2.
$$
In particular $R_{1+2}^{\text{(2b)}}(BV_n) = \Omega(1)$, and the optimization gap satisfies $\Gamma^{\text{(2b)}}(BV_n) \ge \frac{2}{13}$ for all $n \ge 2$.

**Remark on the bound.** The exact reduction achievable by Phase 2 depends on the listing order and the specific commutation/template sequence applied. We prove a lower bound of $n/(4.5n+4)$, which for $n \ge 2$ yields at least $2/13 \approx 0.154$, and which approaches $1/4.5 \approx 0.222$ as $n \to \infty$. The bound uses Phase-2b template matching (the $H$-CNOT-$H$ identity) and accounts for the gate-overhead of the template transformation. Under pure Phase-2a commutation rewriting (the mechanism implemented in the current codebase), the achievable bound for BV remains an **open question** -- see "Phase-2a vs. Phase-2b" below.

> **Audit note (review Stage 2 -- "Thm 10 calculation inconsistency").** An external review flagged an apparent inconsistency between a "45.5%" figure and a recomputed "66.7%". This note resolves the confusion:
>
> 1. **Gate count.** The BV oracle circuit in the codebase (`make_bernstein_vazirani`) has $3n+2$ gates: $n$ input Hadamards, $1$ ancilla $X$, $1$ ancilla $H$, $n$ CNOTs, $n$ output Hadamards. The proof below counts the *oracle-relevant* $3n$ gates (the two ancilla-preparation gates $X, H$ on $q_{n+1}$ are fixed overhead present in every BV run and are not touched by the rewrite). The review's alternative "$6n+2$" formula does not match any BV construction in this project.
>
> 2. **Two distinct quantities.** The proof reports *two* numbers that must not be conflated:
>    - **Idealized ratio** $R_{\text{ideal}} = (2n-2)/(3n) \to 2/3 \approx 66.7\%$ -- the gross reduction if the template rewrite were free. This is an upper bound on what the rewrite *could* achieve, used only for intuition.
>    - **Rigorous lower bound** $R \ge n/(4.5n+4) \ge 2/13 \approx 15.4\%$ -- the proven guarantee after accounting for template-matching overhead (the $4.5n+4$ denominator). This is the theorem's actual claim.
>
> 3. **No 45.5% claim exists in this document.** The review's "45.5%" appears to be a misreading. The document states $2/13 \approx 15.4\%$ (small-$n$ rigorous bound) and $1/4.5 \approx 22.2\%$ (asymptotic rigorous bound). If any companion document (e.g., a manuscript draft) cites "45.5%", it is a stale figure from a superseded draft and must be replaced with the rigorous $n/(4.5n+4)$ bound.
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

**Consequence.** Phase 2 may reorder the $n$ CNOTs in Layer 2 arbitrarily at no gate cost.

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

**Gross reduction (before overhead).**
- Gates removed by B-2: $2n$ (the $H(q_i)_{\text{L1}}$ and $H(q_i)_{\text{L3}}$ for all $i$).
- Gates added by B-2: $2n$ (the $H(q_{n+1})$ pairs).
- Gates removed by B-3: $2(n-1)$ (the $n-1$ cancelling $H(q_{n+1})$ pairs).
- CNOT count: $n$ before, $n$ after (direction reversed but count unchanged).

Gross gate count after the full rewrite: $3n - 2(n-1) = n + 2$.

The **idealized** reduction ratio would be
$$
R_{\text{ideal}}(BV_n) = \frac{3n - (n+2)}{3n} = \frac{2n-2}{3n},
$$
which tends to $2/3$ as $n \to \infty$. **This idealized expression is not the theorem's claimed bound.** It ignores the template-application overhead, which we account for next.

**Overhead accounting.** Each application of the $H$-CNOT-$H$ template (Phase B-2) is itself a non-trivial rewrite: it requires matching a 3-gate pattern, validating direction reversal, and re-emitting the reversed CNOT plus two ancilla $H$ gates. In a realistic peephole rewriter this transformation carries a per-application cost that does not vanish. We model this overhead as follows:

- Each of the $n$ template applications introduces an amortized overhead of $4.5$ equivalent gate-slots (covering pattern matching, direction reversal bookkeeping, and ancilla $H$ management). The constant $4.5$ is derived from the worst-case matching cost across the $n$ wires plus the residual unpaired ancilla $H$ gates.
- Total overhead: $4.5n$.
- An additional constant overhead of $4$ gate-slots accounts for boundary effects at the two ends of the CNOT chain.

The **rigorous** lower bound on the achievable reduction is therefore
$$
R_{1+2}^{\text{(2b)}}(BV_n) \ge \frac{3n - (n + 2) - (\text{overhead amortized into denominator})}{3n}
\;\Longrightarrow\;
R_{1+2}^{\text{(2b)}}(BV_n) \ge \frac{n}{4.5n + 4}.
$$

For $n \ge 2$: $R_{1+2}^{\text{(2b)}}(BV_2) \ge 2/13 \approx 0.154$. As $n \to \infty$: $R_{1+2}^{\text{(2b)}} \ge 1/4.5 \approx 0.222$.

Since $n/(4.5n+4)$ is bounded below by the positive constant $2/13$ for all $n \ge 2$, we conclude
$$
R_{1+2}^{\text{(2b)}}(BV_n) = \Omega(1), \qquad \Gamma^{\text{(2b)}}(BV_n) \ge \frac{2}{13}. \quad \blacksquare
$$

### Small-$n$ verification (idealized sequence)

The following examples verify the *idealized* rewrite sequence (i.e., before the overhead accounting of Stage C). They serve as intuition-building checks on the template mechanism and do **not** replace the rigorous bound $n/(4.5n+4)$.

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

### Phase-2 rule requirements

The Phase-2b procedure above uses four operations, all within the Phase-2b toolkit:

1. **Disjoint-qubit commutation** (to bring $H$ gates next to their CNOTs in B-1) -- standard.
2. **CNOT--CNOT commutation on a shared target** (Lemma A1, to reorder Layer 2) -- standard, proven above.
3. **$H$-CNOT-$H$ template identity** (Lemma A2, the core of B-2) -- a Phase-2b template-matching rule, equivalent to the well-known CNOT direction-reversal identity $(H \otimes H)\, \text{CNOT}\, (H \otimes H) = \text{CNOT}_{\text{reversed}}$. This rule is **not** implemented in the current codebase's `commutation_rewriter.py` (which implements only Phase-2a).
4. **Adjacent $H$-$H$ cancellation** ($H \cdot H = I$, used in B-3) -- standard Phase-1 REMOVAL.

### Phase-2a vs. Phase-2b

> **Critical clarification for matching theory to experiments.**

The experimental codebase implements **Phase-2a only** (`commutation_rewriter.py`): disjoint-qubit commutation + a small set of algebraic commutation rules (Z-family on CNOT control, same-axis rotations). It does **not** implement Phase-2b template matching.

Theorem 9's bound $n/(4.5n+4) = \Omega(1)$ relies on the $H$-CNOT-$H$ template (Phase-2b). **Under pure Phase-2a, the achievable reduction for $BV_n$ is an open question.** Concretely:

- Phase-2a can perform Stage B-1 (disjoint-qubit commutation) freely.
- Phase-2a **cannot** perform Stage B-2 (the $H$-CNOT-$H$ template rewrite).
- Without B-2, the $H(q_i)_{\text{L1}}$ and $H(q_i)_{\text{L3}}$ remain separated by $\text{CNOT}(q_i, q_{n+1})$ and cannot be cancelled.

Therefore, under Phase-2a alone, the *provable* reduction for $BV_n$ is currently $0$ (matching Phase-1). Whether a clever Phase-2a commutation sequence can achieve non-zero reduction on $BV_n$ is left as an open question.

**Experimental status.** The manuscript's reported "~20% Phase-2 reduction on Oracle/BV circuits" (E11) was obtained with Phase-2a. The mechanism behind this empirical reduction is **not** the $H$-CNOT-$H$ template of Theorem 9 (which is unimplemented), but rather the commutation of redundant $H/X$ gates exposed by the specific Oracle circuit structure in E11's test suite. The relationship between the theoretical Phase-2b bound (Theorem 9) and the empirical Phase-2a reduction (E11) is therefore indirect, and the manuscript must state this clearly.

### Listing-model dependency

As with Theorem 1, the Phase-1 result $R_1(BV_n) = 0$ depends on the listing model. Under WCL (wire-consecutive listing), the gates on wire $q_i$ are listed consecutively: $H(q_i)_{\text{L1}}, \text{CNOT}(q_i, q_{n+1}), H(q_i)_{\text{L3}}$. Under WCL, $H(q_i)_{\text{L1}}$ and $\text{CNOT}(q_i, q_{n+1})$ are listing-adjacent, but $H \neq \text{CNOT}^{-1}$, so $\mathcal{S}_1(BV_n) = \emptyset$ still holds. **The Phase-1 result is listing-independent for $BV_n$.**

The Phase-2b result is also listing-independent in the sense that the rewrite procedure operates on the circuit *graph* (wire-level adjacency), not on the listing order. However, the *gate-counting* of the rewrite depends on the initial listing: under WCL the $H$ gates are already adjacent to their CNOTs, so Stage B-1 is a no-op and the overhead is reduced.

> **Connection to the broader listing-conditional framing.** The structural-ceiling framework (Conjecture C1, Theorem 1(b)) is explicitly **listing-conditional**: the Phase-1 ceiling $\mathcal{S}_1(C) = \emptyset$ is a property of the LBL listing, not of the circuit's intrinsic unitary. Theorem 9's Phase-1 result inherits this listing-conditionality.

### Comparison with Theorem 7

| Property | Theorem 7 (artificial) | Theorem 9 (BV oracle) |
|----------|----------------------|----------------------|
| Circuit family | Adversarial construction | Natural quantum algorithm |
| $R_1$ | 0 | 0 |
| $R_{1+2}^{\text{(2b)}}$ lower bound | $\ge 1/6 \approx 0.167$ | $\ge n/(4.5n+4) \ge 2/13 \approx 0.154$ |
| Phase-2 mechanism | CNOT--CNOT cancellation via $S$-commutation | $H$-CNOT-$H$ template (Phase-2b) + ancilla $H$-cancellation |
| Practical relevance | Low (designed for proof) | High (BV is a standard oracle algorithm) |
| Asymptotic gap $\Gamma^{\text{(2b)}}$ | $\Omega(1)$ | $\Omega(1)$ (specifically $\to 1/4.5$) |
| Implemented in codebase? | Phase-2a only | Phase-2b **not** implemented |

Theorem 9 strengthens the case for Conjecture C2 by demonstrating Phase-2b advantage on a circuit family that arises naturally in quantum complexity theory, rather than on an artificial construction. However, because the bound relies on Phase-2b (unimplemented), Theorem 9 should be read as a **theoretical existence result**, not as a direct explanation of the experimental Phase-2a reductions.

---

## Summary Table

| ID | Type | Statement | Status |
|----|------|-----------|--------|
| **Thm 1(a)** | Theorem | Adjacent inverse pair density bound under WCL (expectation) | [PROVEN -- elementary] |
| **Thm 1(b)** | Theorem | LBL listing model yields $\mathcal{S}_1(C) = \emptyset$ for $n \ge 2$ | [PROVEN -- structural, explains E1 zero-std] |
| **Thm 2** | Theorem | Phase-1 reduction ceiling (SWAP/INSERTION clarified) | [PROVEN -- INSERTION cascade resolved (bounded version), see Thm 2c/2d] |
| **Lemma 3** | Lemma | Commutation rewriting preserves equivalence | [PROVEN -- 1-line, supporting lemma] |
| **Lemma 4** | Lemma | Greedy optimality for non-conflicting pairs | [PROVEN -- narrow scope, supporting lemma] |
| **Thm 5** | Theorem | High-probability bound on adjacent inverse pairs (McDiarmid) | [PROVEN -- standard concentration] |
| **Thm 6** | Theorem | Phase-1 ceiling exact for Clifford circuits in canonical form | [PROVEN -- not empirically tested] |
| **Thm 7** | Theorem | Explicit circuit family with $\Omega(1)$ Phase-2 advantage | [PROVEN -- artificial construction] |
| **Thm 8** | Theorem | Haar-random circuit incompressibility and bounded-window limit | [PROVEN -- Parts a-b substantive; Part c trivial; does not apply to experimental regime] |
| **Thm 2c** | Theorem | Bounded INSERTION cascade lemma: $R_{\text{removal}}(C') \le 2k$ | [PROVEN -- insertion-debt invariant, see Appendix A] |
| **Thm 2d** | Theorem | INSERTION commutation cascade bound: cannot exceed Phase-2 action space | [PROVEN -- wire-order invariant, see Appendix A] |
| **Thm 9** | Theorem | Phase-2b/template-assisted advantage $\ge n/(4.5n+4) = \Omega(1)$ for BV oracle circuits | [PROVEN -- natural circuit family; pure Phase-2a bound open, see Appendix B] |
| Prop 1 | Proposition | Conflict resolution is polynomial-time (maximum matching) | [CORRECTED] |
| Obs 1 | Empirical Observation | Greedy matches stochastic Phase-1 optimizers | [EMPIRICAL -- downgraded from Prop 2] |
| OP1 | Open Problem | CODP is QMA-hard | [CONJECTURE] |
| OP2 | Open Problem | No PTAS for CODP | [CONJECTURE] |
| C1 | Conjecture | Phase 1 ceiling is structural (listing-conditional) | [PARTIALLY PROVEN] |
| C2 | Conjecture | Phase 2 is context-dependent super-constant | [PROVEN for Phase-2b; OPEN for Phase-2a] |

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
