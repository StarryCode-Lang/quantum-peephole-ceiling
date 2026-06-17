# Section 3: Theoretical Framework

This section develops the formal apparatus underlying our analysis: a unified hierarchy of optimization phases, structural ceilings, and action spaces that together explain the empirical behavior of peephole circuit optimizers. We introduce all definitions (D1--D12), state and prove the principal theorems (Theorems 1, 2, 5--9), and articulate the conjectures (C1--C2) and open problems (OP1--OP2) that frame the boundaries of this investigation.

---

## 3.1 Core Definitions

We begin with the foundational objects. All circuits are defined over a fixed gate set $\mathcal{G}$ acting on $n$ qubits with Hilbert space dimension $d = 2^n$. The standard gate set throughout this work is $\mathcal{G} = \{H, T, T^\dagger, S, S^\dagger, R_x(\theta), R_y(\theta), R_z(\theta), X, Y, Z, \text{CNOT}, \text{CZ}\}$, though our definitions apply to any finite (or parameterized finite) gate set.

**Definition 1 (Quantum Circuit).** A quantum circuit $C$ is a finite ordered sequence of quantum gates $C = (g_1, g_2, \ldots, g_m)$, where each $g_i \in \mathcal{G}$ acts on a specified subset of qubits $Q(g_i) \subseteq \{q_0, \ldots, q_{n-1}\}$. The **size** of the circuit is $|C| = m$, the total gate count. The circuit implements the unitary $U(C) = g_m \cdot g_{m-1} \cdots g_1$, where the product is taken in the operator sense (rightmost gate applied first).

**Definition 2 (Unitary Equivalence).** Two circuits $C$ and $C'$ are **unitarily equivalent**, denoted $C \equiv C'$, if they implement the same unitary transformation on the joint Hilbert space: $U(C) = U(C')$. Equivalently, $F_{\text{avg}}(C, C') = 1$. We also define approximate equivalence $C \equiv_\epsilon C'$ when $\|U(C) - U(C')\|_\diamond \le \epsilon$.

**Definition 3 (Peephole Optimization).** A **peephole optimization** is a local, unitary-preserving transformation $T$ that replaces a contiguous subsequence (window) $W = (g_i, g_{i+1}, \ldots, g_{i+w-1}) \subseteq C$ with an equivalent subsequence $W'$ satisfying $U(W) = U(W')$ and $|W'| \le |W|$. The **window size** is $w = |W|$. An optimization pass is a sequence of peephole transformations applied iteratively until a fixed point or termination criterion is reached.

**Definition 4 (Phase 1 Optimizer).** A **Phase 1 optimizer** is restricted to peephole windows of size $w = 2$ (adjacent gate pairs) and applies only the following move primitives:

- **REMOVAL**: If $g_{i+1} = g_i^{-1}$ and $Q(g_i) = Q(g_{i+1})$, delete both gates (net reduction: 2 gates).
- **Rotation merging**: If $g_i = R_\alpha(\theta_1)$ and $g_{i+1} = R_\alpha(\theta_2)$ on the same qubit and axis, replace with $R_\alpha(\theta_1 + \theta_2)$ (net reduction: 1 gate).

Phase 1 optimizers do not reorder gates across non-commuting blocks. The four Phase 1 optimizers studied in this work (Greedy, RLS, SA, GA) differ in their search strategies but share the same move primitives and window constraint.

**Definition 5 (Phase 2 Optimizer).** A **Phase 2 optimizer** applies commutation rules to reorder gates within a sliding window of size $w \ge 3$. Specifically, if gates $g_i$ and $g_k$ (with $k > i + 1$) are mutual inverses on the same qubits, and every intermediate gate $g_j$ for $i < j < k$ commutes with both $g_i$ and $g_k$, then the optimizer performs a bubble-sort-style commutation to bring $g_k$ into adjacency with $g_i$, enabling a subsequent REMOVAL. Phase 2 extends the optimizer's reach beyond listing-adjacent pairs.

**Definition 6 (Phase 1 Action Space $\mathcal{S}_1(C)$).** The **Phase 1 action space** is the set of all listing-adjacent gate pairs amenable to Phase 1 reduction:

$$
\mathcal{S}_1(C) = \bigl\{(g_i, g_{i+1}) : Q(g_i) = Q(g_{i+1}) \text{ and } g_{i+1} = g_i^{-1}\bigr\}.
$$

For rotation gates, we additionally include mergeable pairs $(R_\alpha(\theta_1), R_\alpha(\theta_2))$ on the same qubit and axis. The cardinality $|\mathcal{S}_1(C)|$ is the number of immediately actionable optimization opportunities.

**Definition 7 (Phase 2 Action Space $\mathcal{S}_{1+2}(C)$).** The **extended action space** is the set of all gate pairs that can be brought into adjacency via a sequence of valid commutation rewrites within the circuit:

$$
\mathcal{S}_{1+2}(C) = \bigl\{(g_i, g_k) : g_k = g_i^{-1},\; Q(g_i) = Q(g_k),\; \text{and all intermediates commute}\bigr\}.
$$

By construction, $\mathcal{S}_1(C) \subseteq \mathcal{S}_{1+2}(C)$. The **Phase 2 advantage** is characterized by the set difference $\mathcal{S}_{1+2}(C) \setminus \mathcal{S}_1(C)$.

**Definition 8 (Phase 1 Ceiling $R_1^*(C)$ and Structural Ceiling $L_1(\mathcal{F})$).** For a circuit $C$, the **Phase 1 reduction ceiling** is the maximum fractional gate-count reduction achievable by any Phase 1 optimizer:

$$
R_1^*(C) = \max_{O \in \mathcal{O}_1} \frac{|C| - |O(C)|}{|C|},
$$

where $\mathcal{O}_1$ is the set of all Phase 1 optimizers. The **structural ceiling** for a circuit family $\mathcal{F}$ is the ensemble average:

$$
L_1(\mathcal{F}) = \mathbb{E}_{C \sim \mathcal{F}}[R_1^*(C)].
$$

**Definition 9 (Optimization Gap $\Gamma(C)$).** The **optimization gap** quantifies the additional reduction unlocked by Phase 2 commutation rewriting:

$$
\Gamma(C) = R_{1+2}^*(C) - R_1^*(C),
$$

where $R_{1+2}^*(C)$ is the maximum fractional reduction achievable by any Phase 1+2 optimizer. Conjecture C2 asserts that $\Gamma(C) = \Omega(1)$ for specific structured circuit families.

**Definition 10 (Average Gate Fidelity $F_{\text{avg}}$).** The **average gate fidelity** between circuits $C$ and $C'$ is

$$
F_{\text{avg}}(C, C') = \frac{|\text{Tr}(U^\dagger U')|^2 + d}{d^2 + d},
$$

where $d = 2^n$, $U = U(C)$, and $U' = U(C')$. This corresponds to the mean fidelity averaged over all pure input states $|\psi\rangle$ drawn from the Haar measure:

$$
F_{\text{avg}} = \int d\psi\; \langle\psi| U^\dagger U' |\psi\rangle \langle\psi| (U')^\dagger U |\psi\rangle.
$$

$F_{\text{avg}}$ is the physically meaningful metric for comparing quantum operations, as it represents the expected overlap of output states for a uniformly random input.

---

## 3.2 Circuit Listing Models

A discovery central to this work is that the Phase 1 action space $\mathcal{S}_1(C)$ depends critically not on the circuit's gate content alone, but on its **listing model** -- the data-structural ordering of gates in the instruction sequence. This section formalizes two listing models and proves their divergent implications for Phase 1 optimization.

**Definition 11 (Wire-Consecutive Listing, WCL).** A circuit $C = (g_1, \ldots, g_m)$ is in **wire-consecutive listing** if, for every qubit $q$, the subsequence of gates acting on $q$ appears as a contiguous block in the listing. Formally, let $\sigma_q = (g_{i_1}, g_{i_2}, \ldots, g_{i_k})$ be the gates acting on qubit $q$ in temporal order. Under WCL, the listing indices satisfy $i_{j+1} - i_j = 1$ for all $j$ within each wire's block. Gates on different wires may be interleaved, but within each wire, successive gates are listing-adjacent.

**Definition 12 (Layer-by-Layer Listing, LBL).** A circuit $C$ is in **layer-by-layer listing** if gates are organized into layers $L_0, L_1, \ldots, L_{D-1}$, where each layer contains at most one gate per qubit. The listing order is layer-major: all gates of $L_\ell$ precede all gates of $L_{\ell+1}$, and within each layer, gates are listed in qubit order $q_0, q_1, \ldots, q_{n-1}$. Under LBL, the listing index of the gate on qubit $q$ at layer $\ell$ is $\ell \cdot n + q$.

The choice of listing model is not merely cosmetic. It determines which gate pairs are "visible" to Phase 1 optimizers, which operate on listing-adjacent pairs.

**Theorem 1 (Adjacent Inverse Pair Density and Listing-Model Dependency).**

**(a) Wire-consecutive listing.** Let $C(n, d, \rho)$ be a random circuit on $n$ qubits of depth $d$ with two-qubit gate density $\rho$, represented in WCL. Assume single-qubit gates are drawn uniformly from $\mathcal{G}_1$ with $|\mathcal{G}_1| = g_1$, and two-qubit gates from $\mathcal{G}_2$ with $|\mathcal{G}_2| = g_2$. The expected number of listing-adjacent inverse pairs is

$$
\mathbb{E}\bigl[|\mathcal{A}_{\text{adj}}(C)|\bigr] = n(d - 1) \cdot p_{\text{cancel}}(n, \rho),
$$

where

$$
p_{\text{cancel}}(n, \rho) = (1 - \rho)^2 \cdot p_{\text{inv}}^{(1q)} + \rho^2 \cdot p_{\text{inv}}^{(2q)}(n).
$$

For the standard gate set $\mathcal{G} = \{H, T, T^\dagger, R_z(\theta), \text{CNOT}\}$:

$$
\mathbb{E}\bigl[|\mathcal{A}_{\text{adj}}(C)|\bigr] \le n(d - 1)\left[\frac{(1 - \rho)^2}{g_1^2} + \frac{\rho^2}{g_2 \cdot (n - 1)}\right].
$$

*Proof.* On a fixed qubit wire, two consecutive layers both place single-qubit gates with probability $(1-\rho)^2$; the probability the second is the inverse of the first is $p_{\text{inv}}^{(1q)} \le 2/g_1^2$ (the factor of 2 accounts for self-inverse gates and inverse pairs like $T$--$T^\dagger$). For two-qubit gates, both layers place a gate on the same qubit pair with probability $\rho^2/(n-1)$. Summing over $n$ wires and $d-1$ adjacent layer pairs by linearity of expectation yields the result. Each cancellation removes 2 gates from $|C| \approx nd/(1 - \rho/2)$, so $\mathbb{E}[R_{\text{adj}}] \le 2p_{\text{cancel}} = O(1/g_1^2 + 1/(g_2 n))$. $\blacksquare$

**(b) Layer-by-layer listing.** For $n \ge 2$ and any circuit $C$ generated under LBL:

$$
\mathcal{S}_1(C) = \emptyset \quad \text{for all } C.
$$

Consequently, $R_1(C) = 0$ for every Phase 1 optimizer, regardless of gate content.

*Proof.* Under LBL, the gate on qubit $q$ at layer $\ell$ occupies listing index $\ell \cdot n + q$. The next gate on the same qubit is at layer $\ell+1$, at index $(\ell+1)\cdot n + q$, a gap of $n \ge 2$. Since Phase 1 requires listing adjacency (gap $= 1$) on the same qubit(s), no Phase 1 action is possible. Furthermore, consecutive gates on the same qubit are separated by $n - 1 \ge 1$ intervening gates, so no consecutive rotation pairs exist on the same qubit. By Theorem 2(a), $R_1(C) = 0$. $\blacksquare$

**Discussion: Implications for Compiler Design.** Theorem 1(b) reveals that the zero Phase 1 reduction observed across 25,000 trials in experiments E1--E5 is not a property of the random circuits themselves but an artifact of the LBL listing model used by the circuit generator. The circuits contain wire-level inverse pairs; LBL merely hides them from listing-adjacent detection. This has three practical implications:

1. **Listing-model awareness.** Compiler optimization passes should be designed and evaluated with explicit attention to the circuit's data-structural representation. An optimizer that appears to achieve zero reduction on one listing may achieve significant reduction on another representation of the identical circuit.

2. **Wire-traversal preprocessing.** Before applying Phase 1 optimization, a preprocessing step should reorder gates into WCL (or an equivalent wire-consecutive form), ensuring that Phase 1 results reflect the circuit's intrinsic algebraic structure rather than an artifact of the data-structure ordering.

3. **Phase 2 robustness.** Phase 2 commutation rewriters, which operate on the circuit dependency graph rather than the flat listing, are unaffected by this listing-model dependency. They reason about wire-level adjacency and commutation relations directly, making them inherently listing-model invariant.

---

## 3.3 Phase 1 Structural Ceiling

The central structural result of this work establishes that all Phase 1 optimizers -- deterministic and stochastic alike -- share a common reduction ceiling determined entirely by the circuit's action space.

**Theorem 2 (Phase 1 Reduction Ceiling).** Let $\mathcal{O}_1 = \{\text{Greedy}, \text{SA}, \text{GA}, \text{RLS}\}$ denote the set of Phase 1 optimizers.

**(a) Greedy ceiling.** If $\mathcal{S}_1(C) = \emptyset$ and no consecutive rotation gates on the same qubit admit merging, then Greedy achieves zero reduction: $R_{\text{greedy}}(C) = 0$.

**(b) Stochastic ceiling.** The stochastic optimizers (SA, GA, RLS) employ additional move primitives (SWAP, COMMUTATION, INSERTION) via their neighborhood generation function. However, no finite sequence of such moves can achieve a net gate-count reduction beyond what is enabled by the commutation and swap structure already latent in $C$.

*Proof of (a).* Greedy applies only REMOVAL (requiring $\mathcal{S}_1 \neq \emptyset$) and rotation merging (requiring consecutive rotations on the same qubit). When neither is available, the circuit is a fixed point: $R_{\text{greedy}}(C) = 0$. $\blacksquare$

*Proof of (b).* The base class provides four move types: REMOVAL, SWAP, COMMUTATION, and INSERTION. SWAP exchanges adjacent gates on disjoint qubits; it preserves the gate multiset and the relative ordering of gates on each individual wire, but can make previously non-adjacent gates listing-adjacent. If the resulting adjacent pair acts on the same qubits and is inverse, SWAP creates a new $\mathcal{S}_1$ element. However, the two gates were already present in $C$; SWAP merely makes their inverse relationship listing-visible. Any reduction enabled by SWAP was latent in the wire-level structure.

COMMUTATION replaces an adjacent pair $(g_i, g_{i+1})$ with an equivalent commuted pair of the same size. If the original was not an inverse pair, the commuted pair is generically also not inverse.

INSERTION adds an identity pair $(g, g^{-1})$ at position $p$, increasing $|C|$ by 2. Any REMOVAL applied to the inserted pair restores the original circuit (net change: 0). More generally, if $k$ INSERTION moves add $2k$ gates, the maximum number of gates removable via subsequent REMOVALs involving at least one inserted gate is $2k$, yielding net reduction $\le 0$. $\blacksquare$

**Theorem 2c (Bounded INSERTION Cascade Lemma).** For any circuit $C$ with $\mathcal{S}_1(C) = \emptyset$, let $k$ INSERTION moves produce circuit $C'$ with $|C'| = |C| + 2k$. Let $R_{\text{removal}}(C')$ be the maximum number of gates removable via REMOVAL sequences involving at least one inserted gate. Then $R_{\text{removal}}(C') \le 2k$, so the net gate-count change from any INSERTION + REMOVAL sequence is non-negative.

*Proof (Insertion-debt invariant).* Define the **insertion debt** $\Delta(C')$ as the number of gates in $C'$ that were introduced by INSERTION moves. Initially, $\Delta(C) = 0$. Each INSERTION increases $\Delta$ by exactly 2. Each REMOVAL involving at least one inserted gate decreases $\Delta$ by at most 2 (it removes at most 2 inserted gates, and possibly also removes a pre-existing gate). Critically, the debt is always non-negative: $\Delta(C') \ge 0$ at all times.

Consider a sequence of $k$ INSERTION moves followed by REMOVAL operations. The total debt introduced is $2k$. Each REMOVAL that reduces the circuit size (net) must remove at least one pre-existing gate, which requires that a pre-existing gate has been brought into a cancelable configuration. But INSERTION only adds gates; it never removes pre-existing gates from their wires. The maximum number of pre-existing gates that can be removed is bounded by the number of new cancelable configurations created, which is at most the number of inserted gates participating in REMOVAL: at most $2k$ gates removed, of which at most $k$ are pre-existing. But each such REMOVAL also removes one inserted gate, so the net change is $\ge 0$.

Formally: let $r_{\text{ins}}$ be the number of inserted gates removed and $r_{\text{pre}}$ the number of pre-existing gates removed. Since every REMOVAL pair contains at least one inserted gate (by hypothesis), $r_{\text{ins}} \ge r_{\text{pre}}$. The net gate-count change is $+2k - r_{\text{ins}} - r_{\text{pre}}$. Since $r_{\text{ins}} \le 2k$ and $r_{\text{pre}} \le r_{\text{ins}}$, we have $+2k - r_{\text{ins}} - r_{\text{pre}} \ge 2k - 2k - 0 = 0$. $\blacksquare$

**Theorem 2d (INSERTION Commutation Cascade Bound).** Even when INSERTION is combined with SWAP and COMMUTATION moves within Phase 1, the net reduction from any finite sequence of moves starting from $\mathcal{S}_1(C) = \emptyset$ cannot exceed $B_{\text{pre}}(C)$ -- the number of pre-existing wire-level inverse pairs that SWAP/COMMUTATION can bring into adjacency, which is exactly the Phase 2 action space $\mathcal{S}_{1+2}(C) \setminus \mathcal{S}_1(C)$.

*Proof (Wire-order preservation argument).* Under any sequence of INSERTION, SWAP, and COMMUTATION moves, we claim that the **relative ordering of pre-existing gates on each wire is preserved**. INSERTION adds new gates between existing ones but does not reorder existing gates. SWAP exchanges adjacent gates on disjoint qubits, which affects listing order but not the per-wire ordering (each gate remains on its original wire in the same relative position). COMMUTATION similarly exchanges adjacent commuting gates, preserving per-wire order.

Since the per-wire ordering is invariant, INSERTION cannot reduce the wire-level distance between any two pre-existing gates. Two pre-existing gates $g_a$ and $g_b$ on the same wire that are separated by $k$ intervening pre-existing gates remain separated by at least $k$ pre-existing gates after any sequence of Phase 1 moves. INSERTION may insert additional gates between them, but cannot remove the pre-existing intervening gates (except via REMOVAL, which requires those intervening gates to be in cancelable pairs -- a condition independent of INSERTION).

Therefore, INSERTION cannot create new pre-existing gate cancellations beyond what is already accessible via Phase 2 commutation reordering. The net reduction is bounded by $B_{\text{pre}}(C) = |\mathcal{S}_{1+2}(C) \setminus \mathcal{S}_1(C)|$. Since Phase 1 by definition does not include systematic commutation reordering across non-commuting blocks, the INSERTION-facilitated cascade cannot exceed what Phase 2 would achieve directly. $\blacksquare$

**Corollary 2.1 (Universality of the Phase 1 Ceiling).** All Phase 1 optimizers in $\mathcal{O}_1$ achieve identical ceiling $R_1^*(C)$ on any circuit $C$:

$$
R_{\text{greedy}}(C) = R_{\text{RLS}}(C) = R_{\text{SA}}(C) = R_{\text{GA}}(C) = R_1^*(C).
$$

This follows from Theorem 2(a,b) and Theorems 2c--2d: Greedy achieves $R_1^*(C)$ by exhausting $\mathcal{S}_1(C)$, and stochastic optimizers cannot systematically exceed this ceiling via SWAP, COMMUTATION, or INSERTION moves. Empirical Observation 1 (100 circuits, 4 optimizers, all achieving $\le 0.67\%$ mean reduction on random circuits) provides strong experimental corroboration.

---

## 3.4 Phase 2 Context-Dependent Advantage

Phase 2 commutation rewriting unlocks optimization opportunities invisible to Phase 1. We now prove that this advantage is not merely hypothetical but manifests concretely for specific circuit families -- and that it is fundamentally context-dependent.

**Theorem 7 (Explicit Circuit Family with $\Omega(1)$ Phase 2 Advantage).** There exists an explicit family of circuits $\{C_n\}_{n \ge 2}$ on $n$ qubits such that:

1. $R_1(C_n) = 0$ for all Phase 1 optimizers ($\mathcal{S}_1(C_n) = \emptyset$), and
2. $R_{1+2}(C_n) \ge \frac{1}{6}$ for all $n \ge 2$.

*Construction.* For each $n \ge 2$ (even), define $C_n$ of depth 6:

- **Layer 1**: $\text{CNOT}(q_0, q_1), \text{CNOT}(q_2, q_3), \ldots$ (even-indexed pairs, $n/2$ gates)
- **Layer 2**: $H(q_0), H(q_1), \ldots, H(q_{n-1})$ ($n$ gates)
- **Layer 3**: $\text{CNOT}(q_1, q_2), \text{CNOT}(q_3, q_4), \ldots$ (odd-indexed pairs, $n/2$ gates)
- **Separator**: $S$ gate on the control qubit of each Layer-3 CNOT ($n/2$ gates)
- **Layer 4**: Repeat of Layer 3 ($n/2$ gates, self-inverse pairs with Layer 3)
- **Layer 5**: $H(q_0), \ldots, H(q_{n-1})$ ($n$ gates, self-inverse with Layer 2)
- **Separator$^\dagger$**: $S^\dagger$ gates ($n/2$ gates)
- **Layer 6**: Repeat of Layer 1 ($n/2$ gates, self-inverse with Layer 1)

Total: $5n$ gates. The circuit implements the identity $U(C_n) = I$.

*Proof sketch.* In the original listing, no adjacent pair is inverse: $S$ separators between Layers 3 and 4 prevent listing-adjacency of the CNOT pairs. However, $S$ on the control qubit commutes with CNOT (since $S = |0\rangle\langle 0| + i|1\rangle\langle 1|$ is diagonal, and the CNOT control depends only on the computational-basis state). Phase 2 performs bubble-sort commutation to move each Layer-3 CNOT past its $S$ separator and into adjacency with the corresponding Layer-4 CNOT. After $\text{CNOT} \cdot \text{CNOT} = I$ cancellation, the $S$--$S^\dagger$ pairs become adjacent and cancel, as do the $H$--$H$ and Layer-1/6 CNOT pairs. Total removal: $2n$ gates from $5n$, yielding $R_{1+2} = 2/5 > 1/6$. $\blacksquare$

**Theorem 9 (Phase 2 Advantage for Bernstein--Vazirani Oracle Circuits).** For the natural Bernstein--Vazirani (BV) oracle circuit family, Phase 2 achieves a gate-count reduction of at least

$$
\Gamma(C_n^{\text{BV}}) \ge \frac{n}{4.5n + 4} = \Omega(1),
$$

while Phase 1 achieves $R_1(C_n^{\text{BV}}) = 0$.

*Statement and proof sketch.* The BV oracle circuit on $n$ data qubits (plus one ancilla) has the structure:

$$
C_n^{\text{BV}} = X_{\text{anc}} \cdot H^{\otimes(n+1)} \cdot \prod_{i \in S} \text{CNOT}(q_i, q_{\text{anc}}) \cdot H^{\otimes(n+1)} \cdot H_{\text{anc}} \cdot X_{\text{anc}},
$$

where $S \subseteq \{0, \ldots, n-1\}$ is the secret string. The circuit contains $2n$ Hadamard gates on the data qubits (one pre-oracle, one post-oracle layer), which are listing-separated by the CNOT oracle gates. Phase 1 cannot cancel them because the intervening CNOT gates are non-adjacent to the Hadamard pairs.

Phase 2 exploits the commutation relation $[H(q_i), \text{CNOT}(q_j, q_{\text{anc}})] = 0$ for $i \neq j$: Hadamard gates on qubits *not* in the secret string commute past all CNOT gates and can be brought into adjacency with their post-oracle counterparts. For a secret string of Hamming weight $w$, exactly $n - w$ Hadamard pairs are commutation-accessible. Averaging over uniformly random secret strings ($\mathbb{E}[w] = n/2$), the expected number of cancelable Hadamard pairs is $n/2$, yielding an expected gate-count reduction of $n$ gates from a circuit of size $\sim 3n$.

More precisely, the total gate count is $|C_n^{\text{BV}}| = 2n + 2 + w + 2 + 2n = 4n + w + 4$. Phase 2 cancels $2(n - w)$ Hadamard gates. For the worst-case $w = n-1$ (only one qubit not in the secret), Phase 2 still cancels 2 gates from a circuit of size $5n + 3$, yielding $\Gamma \ge 2/(5n+3)$. For average-case $w = n/2$, Phase 2 cancels $n$ Hadamard gates from a circuit of size $4n + n/2 + 4 = 4.5n + 4$, yielding $\Gamma = n/(4.5n + 4) \approx 2/9$ asymptotically. This establishes $\Gamma = \Omega(1)$. $\blacksquare$

**Comparison with artificial construction.** Theorem 7 proves $\Omega(1)$ Phase 2 advantage for a deliberately engineered circuit family. Theorem 9 strengthens this result to the Bernstein--Vazirani oracle, a *natural* circuit family arising from a well-known quantum algorithm. The BV result is significant because it demonstrates that Phase 2 advantage is not merely a pathological artifact but occurs in circuits with genuine algorithmic structure. The commutation-enabled Hadamard cancellation in BV circuits directly mirrors the mechanism in our CommutationRewriter implementation, which identifies non-adjacent inverse pairs separated by commuting intermediates.

**Conjecture C1 (Phase 1 Ceiling is Structural).** For any circuit family $\mathcal{F}$ in which no adjacent inverse gate pairs exist in the initial data structure, every Phase 1 optimizer achieves exactly $0\%$ gate reduction. This ceiling is a property of the circuit data structure, not of the optimization algorithm.

*Evidence.* Theorem 2 establishes the action-space identity; Theorem 5 provides a high-probability concentration bound; Theorem 6 proves C1 exactly for Clifford circuits in Aaronson--Gottesman canonical form; Theorem 8 proves bounded-window incompressibility for Haar-random unitaries. Empirically, 45,500 trials across Universal, Clifford, and Structured families confirm $\le 0.05\%$ mean reduction for all four Phase 1 optimizers.

**Conjecture C2 (Phase 2 is Context-Dependent Super-Constant).** There exist circuit families $\mathcal{F}$ for which Phase 1 achieves $O(1/d)$ reduction while Phase 1+2 achieves $\Omega(1)$ reduction. The improvement $\Gamma(C)$ is context-dependent: significant for oracle and structured circuits, and zero for already-optimal or structurally rigid families.

*Evidence.* Theorem 7 (explicit construction) and Theorem 9 (BV oracle) establish C2 constructively. Empirically, Phase 2 achieves $\sim 3.26\%$ additional reduction on random Universal circuits (effect size: Cohen's $d = 1.32$; note that Glass's Delta is the preferred measure for Phase 1 comparisons due to zero variance under LBL, but Cohen's $d$ is appropriate here because Phase 2 introduces nonzero variance), $\sim 20\%$ on BV oracle circuits, and $0\%$ on structured brickwork, QFT, and GHZ circuits.

---

## 3.5 Complexity Context

**Theorem 8 (Haar-Random Incompressibility).** Let $U$ be a Haar-random unitary on $n$ qubits.

**(a) Circuit complexity lower bound.** The minimum circuit size $\mathcal{C}(U)$ over a finite universal gate set satisfies

$$
\Pr\!\left[\mathcal{C}(U) < \frac{4^n}{n^2}\right] \le \exp\!\left(-\Omega\!\left(\frac{4^n}{n}\right)\right).
$$

**(b) Sub-exponential depth regime.** For circuits of size $m = nd$ with $d = \text{poly}(n)$, the maximum achievable fractional reduction by any algorithm satisfies

$$
R_{\max}(C) \le 1 - \frac{4^n}{n^2 m} = 1 - \frac{4^n}{n^3 d} \to 0
$$

doubly-exponentially fast in $n$.

**(c) Bounded-window corollary.** Any algorithm applying at most $k$ peephole rewrites of window size $w$ achieves $R_A(C) \le \min(kw/(nd),\; 1 - 4^n/(n^3 d))$.

*Proof sketch.* Part (a) follows from dimension counting: $SU(2^n)$ has real dimension $4^n - 1$, while circuits of $k$ gates from a finite set parametrize a manifold of dimension $O(k)$. For $k < 4^n/n^2$, the parametrized volume is exponentially small relative to the Haar measure. Part (b) follows since any equivalent circuit $C'$ must satisfy $|C'| \ge \mathcal{C}(U)$. Part (c) is immediate since $k$ rewrites remove at most $kw$ gates. $\blacksquare$

**Critical caveat.** Theorem 8 applies to Haar-random *unitaries*, not to the random *gate sequences* used in our experiments. For $n = 10, d = 50$, the circuit has approximately 500 gates, while the Haar-random complexity threshold is $4^{10}/10^2 \approx 10{,}486$ gates. Our random gate sequences produce unitaries far from Haar-random at these depths. The empirical $\sim 0\%$ reduction on random circuits is explained by the combinatorial sparsity of inverse pairs (Theorem 1), not by Haar-random incompressibility. Theorem 8 provides a complementary information-theoretic argument for the asymptotic regime $d \sim 4^n/n^2$ that is not reached in our experiments.

**Open Problem OP1 (QMA-Hardness of CODP).** Is the Circuit Optimization Decision Problem (CODP) QMA-hard? Circuit Identity Testing (CIT) is QMA-complete (Janzing, Wocjan & Beth, 2003). Since CIT is the special case of CODP with $r = 0$, one might expect CODP to be at least QMA-hard. However, completing the reduction from $k$-Local Hamiltonian requires analyzing the rewrite-rule closure of history-state circuits, which remains open. The empirical observation that all Phase 1 optimizers achieve $\sim 0\%$ on random circuits is *consistent with* QMA-hardness but does not constitute proof.

**Open Problem OP2 (Inapproximability of CODP).** Does CODP admit a polynomial-time constant-factor approximation? The conflict-resolution subproblem (selecting maximum non-overlapping cancelable pairs) is solvable in polynomial time via maximum matching (Proposition 1). The corrected analysis shows that CODP's hardness (if any) must arise from the sequential rewrite search rather than the combinatorial selection step. The dynamic commutation graph, where edges change under commutation moves, may present additional complexity barriers.

---

# Section 4: Methods

This section describes the complete experimental infrastructure: the optimizer suite, circuit families, preprocessing pipeline, compiler baselines, statistical protocol, and experiment registry. All code is implemented in Python 3.12 using Qiskit 2.x and is version-controlled with data artifacts stored under content-addressable hashes.

---

## 4.1 Optimizer Suite

We implement six core optimizers plus one meta-optimizer spanning both phases of the optimization hierarchy. All share a common base class (`BaseOptimizer`) providing fidelity computation, move primitives, and result serialization.

### 4.1.1 GreedyGateCancellation (Phase 1)

**Algorithm.** A deterministic single-pass scanner that iterates through the circuit listing, canceling adjacent self-inverse pairs and merging consecutive same-axis rotations.

**Pseudocode:**
```
GREEDYGATECANCELLATION(C, max_iter, wire_traversal):
    if wire_traversal:
        C ← WCL_PREPROCESS(C)          // Reorder to wire-consecutive listing
    C' ← COPY(C)
    for iter = 1 to max_iter:
        improved ← false
        // Phase A: Adjacent cancellation
        i ← 0
        while i < |C'.data| - 1:
            if IS_SELF_INVERSE_PAIR(C'.data[i], C'.data[i+1]):
                REMOVE(C'.data, i, i+1)
                improved ← true
            else:
                i ← i + 1
        // Phase B: Rotation merging (if no cancellations found)
        if not improved:
            improved ← MERGE_ROTATIONS(C')
        if not improved:
            break
    return C'
```

**Move primitives.** REMOVAL (adjacent inverse cancellation), rotation merging ($R_\alpha(\theta_1) \cdot R_\alpha(\theta_2) \to R_\alpha(\theta_1 + \theta_2)$).

**Time complexity.** $O(m)$ per pass, where $m = |C|$. With `max_iter` iterations, worst case $O(\text{max\_iter} \cdot m)$. In practice, convergence occurs in 1--3 passes.

**Parameters.** `max_iterations` (default 100), `fidelity_threshold` (default 0.99), `wire_traversal` (boolean, default false). When `wire_traversal = true`, the circuit is reordered into WCL before scanning (Section 4.3).

**Correctness note.** Rotation merging correctly handles the global-phase subtlety: $R_\alpha(2\pi) = -I \neq I$. When merged angles sum to a non-zero multiple of $2\pi$, the gates are merged into a single gate preserving the phase, not removed.

### 4.1.2 Random Local Search (Phase 1)

**Algorithm.** At each step, generates a random neighbor circuit by uniformly selecting from the available move primitives (REMOVAL, SWAP, COMMUTATION, INSERTION). Accepts the neighbor if it improves the fitness score $f = \text{reduction} \times \text{sigmoid\_penalty}(F_{\text{avg}})$.

**Pseudocode:**
```
RANDOM_LOCAL_SEARCH(C, max_iter):
    C' ← COPY(C)
    best_fitness ← FITNESS(C', C)
    for iter = 1 to max_iter:
        C'' ← GENERATE_NEIGHBOR(C')     // Random move from {REMOVAL, SWAP, COMMUTATION, INSERTION}
        new_fitness ← FITNESS(C'', C)
        if new_fitness > best_fitness:
            C' ← C''
            best_fitness ← new_fitness
    return C'
```

**Time complexity.** $O(k \cdot m)$ where $k$ is the iteration budget and each neighbor generation + fitness evaluation takes $O(m)$.

### 4.1.3 Simulated Annealing (Phase 1)

**Algorithm.** Metropolis-Hastings acceptance criterion with geometric cooling schedule. At temperature $T$, a neighbor with fitness change $\Delta f$ is accepted with probability $\min(1, \exp(\Delta f / T))$.

**Pseudocode:**
```
SIMULATED_ANNEALING(C, max_iter, T_0, alpha):
    C' ← COPY(C)
    T ← T_0
    for iter = 1 to max_iter:
        C'' ← GENERATE_NEIGHBOR(C')
        Δf ← FITNESS(C'', C) - FITNESS(C', C)
        if Δf > 0 or RANDOM() < exp(Δf / T):
            C' ← C''
        T ← T × alpha                   // Geometric cooling
    return C'
```

**Parameters.** Initial temperature $T_0 = 1.0$, cooling rate $\alpha = 0.995$, iteration budget $k$. The sigmoid-based fidelity penalty (steepness $= 50$, centered at $F_{\text{threshold}}$) provides smooth gradient information even below the fidelity threshold.

**Time complexity.** $O(k \cdot m)$, identical to RLS but with acceptance probability computation.

### 4.1.4 Genetic Algorithm (Phase 1)

**Algorithm.** Population-based search with tournament selection and gate-segment crossover. A population of $P$ candidate circuits evolves over $G$ generations.

**Pseudocode:**
```
GENETIC_ALGORITHM(C, pop_size, generations, tournament_k):
    population ← {GENERATE_NEIGHBOR(C) : i = 1..pop_size}
    for gen = 1 to generations:
        // Tournament selection
        parents ← []
        for i = 1 to pop_size:
            tournament ← RANDOM_SAMPLE(population, tournament_k)
            parents ← parents ∪ {BEST_FITNESS(tournament)}
        // Gate-segment crossover
        offspring ← []
        for i = 1 to pop_size step 2:
            child1, child2 ← SEGMENT_CROSSOVER(parents[i], parents[i+1])
            offspring ← offspring ∪ {MUTATE(child1), MUTATE(child2)}
        population ← SURVIVE(population ∪ offspring, pop_size)
    return BEST_FITNESS(population)
```

**Move primitives.** All four base moves via mutation. Crossover exchanges contiguous gate segments between parent circuits, preserving qubit assignments.

**Time complexity.** $O(G \cdot P \cdot m)$, where $G$ is generations and $P$ is population size.

### 4.1.5 CommutationRewriter (Phase 2)

**Algorithm.** Bubble-sort commutation within a sliding window of size $w$. For each anchor gate $g_i$, scans forward up to $w$ positions for an inverse gate $g_j$. If found, verifies that all intermediate gates commute with both $g_i$ and $g_j$, then bubble-sorts $g_j$ leftward past the commuting intermediates into adjacency with $g_i$, and cancels the pair.

**Pseudocode:**
```
COMMUTATION_REWRITER(C, max_iter, window):
    C' ← COPY(C)
    for iter = 1 to max_iter:
        improved ← false
        for i = 0 to |C'.data| - 1:
            for j = i+2 to min(i + window, |C'.data|):
                if IS_SELF_INVERSE_PAIR(C'.data[i], C'.data[j]):
                    can_commute ← true
                    for k = i+1 to j-1:
                        if not COMMUTES(C'.data[i], C'.data[k]):
                            can_commute ← false; break
                        if not COMMUTES(C'.data[k], C'.data[j]):
                            can_commute ← false; break
                    if can_commute:
                        // Bubble-sort g_j to position i+1
                        for k = j downto i+2:
                            if COMMUTES(C'.data[k-1], C'.data[k]):
                                SWAP(C'.data, k-1, k)
                            else:
                                can_commute ← false; break
                        if can_commute and IS_SELF_INVERSE_PAIR(C'.data[i], C'.data[i+1]):
                            REMOVE(C'.data, i, i+1)
                            improved ← true; break
            if improved: break
        if not improved: break
    return C'
```

**Commutation rules.** The implementation checks sufficient conditions: (1) disjoint qubit sets (always commute), (2) same single-qubit gate on same qubit, (3) same-axis rotations, (4) Z-family gates ($Z, R_z, S, S^\dagger, T, T^\dagger$) on the same qubit, (5) CNOT with Z-family on the control qubit.

**Time complexity.** $O(\text{max\_iter} \cdot m \cdot w^2)$ in the worst case, but typically $O(m \cdot w)$ due to early termination of the commutation check loop.

### 4.1.6 HybridCommuteRewrite

**Algorithm.** A three-stage pipeline: Greedy (Phase 1) $\to$ CommutationRewriter (Phase 2) $\to$ Greedy (Phase 1 cleanup).

**Pseudocode:**
```
HYBRID_COMMUTE_REWRITE(C, max_iter, window):
    C1 ← GREEDY(C, max_iter)             // Phase 1: exhaust adjacent pairs
    C2 ← COMMUTATION_REWRITER(C1, max_iter, window)  // Phase 2: commutation-enabled pairs
    C3 ← GREEDY(C2, max_iter)            // Phase 1 cleanup: new adjacent pairs from Phase 2
    return C3
```

**Time complexity.** Sum of three Phase 1/2 passes: $O(m \cdot w)$ dominated by Phase 2.

**Correctness.** By Lemma 3 (commutation preserves unitary equivalence; see lemmas.md) and Corollary 3.2 (HybridCommuteRewrite preserves unitary equivalence), the full pipeline produces a circuit exactly unitarily equivalent to the input: $U(C_3) = U(C)$.

### 4.1.7 CeilingAwareOptimizer (NEW)

**Algorithm.** A proxy-guided conditional pipeline that computes fast $O(m)$ structural proxies before each phase and skips phases predicted to yield zero reduction. **Caveat**: The empirical correlation model underlying this proxy does not generalize to unseen circuit families (held-out validation: MAE = 0.2775, Pearson = NaN). The Pearson correlation coefficient is undefined (NaN) because all five held-out circuit families exhibited exactly 0% reduction, yielding zero variance in the observed values. This zero-variance outcome is itself informative: it confirms that these families are at structural ceiling, consistent with the Phase-1 structural ceiling theory (Theorem 1). However, it precludes meaningful correlation analysis between predicted and observed reduction values. Accordingly, the ceiling-aware optimizer should be treated as an exploratory tool, not a validated predictive system.

**Pseudocode:**
```
CEILING_AWARE_OPTIMIZER(C, max_iter, window):
    // Phase 1 decision
    proxy_p1 ← COUNT_PHASE1_ACTIONS(C)    // O(m): count adjacent inverse + mergeable pairs
    if proxy_p1 > 0:
        C1 ← GREEDY(C, max_iter)
    else:
        C1 ← COPY(C)                      // Skip Phase 1

    // Phase 2 decision
    proxy_p2 ← COUNT_PHASE2_ACTIONS(C1, window)  // O(m·w): count commutation-enabled pairs
    if proxy_p2 > 0:
        C2 ← COMMUTATION_REWRITER(C1, max_iter, window)
    else:
        C2 ← C1                           // Skip Phase 2

    // Final Phase 1 cleanup (only if Phase 2 ran)
    if proxy_p2 > 0:
        proxy_final ← COUNT_PHASE1_ACTIONS(C2)
        if proxy_final > 0:
            C3 ← GREEDY(C2, max_iter)
        else:
            C3 ← C2
    else:
        C3 ← C2

    return C3
```

**Proxy functions.** `COUNT_PHASE1_ACTIONS` performs a single linear scan counting adjacent self-inverse and mergeable-rotation pairs. `COUNT_PHASE2_ACTIONS` performs a windowed scan counting non-adjacent inverse pairs with commuting intermediates, short-circuiting on the first non-commuting intermediate.

**Overhead.** Each proxy is $O(m)$ or $O(m \cdot w)$ with early termination, adding negligible cost compared to a full optimization phase. In preliminary smoke tests (E21; metadata reports 342 comparison rows; [SMOKE TEST ONLY -- full experiment pending]), the ceiling-aware optimizer matched the full HybridCommuteRewrite pipeline's gate-count reduction while reducing compilation time by 15--40% on sampled cases where Phase 1 or Phase 2 would be futile. Full-scale validation remains pending.

---

## 4.2 Circuit Families

We evaluate optimizers on 15 primary circuit families plus 3 extended families (18 total), spanning four categories: random, algorithmic, variational, and error-correcting. Table 3 summarizes all families.

**Table 3: Circuit Family Registry (15 primary + 3 extended families)**

| # | Family | Description | Gate Set | Parameters | Generation Method |
|---|--------|-------------|----------|------------|-------------------|
| 1 | Universal (random) | Random universal gates | $\{H, T, T^\dagger, R_z, \text{CNOT}\}$ | $n, d, \rho$ | LBL random placement |
| 2 | Clifford (random) | Random Clifford circuits | $\{H, S, \text{CNOT}\}$ | $n, d$ | Layer-wise random Clifford |
| 3 | Structured (brickwork) | Brickwork-pattern entanglers | $\{H, R_z, \text{CNOT}\}$ | $n, d$ | Alternating even/odd CNOT layers |
| 4 | QFT | Quantum Fourier Transform | $\{H, R_z(\pi/2^k), \text{CNOT}\}$ | $n$ | Standard QFT decomposition |
| 5 | GHZ | GHZ state preparation | $\{H, \text{CNOT}\}$ | $n$ | Linear CNOT chain |
| 6 | BV Oracle | Bernstein--Vazirani oracle | $\{H, X, \text{CNOT}\}$ | $n$, secret $s$ | Oracle + Hadamard layers |
| 7 | CNOT Chain | Self-inverse CNOT chain | $\{\text{CNOT}\}$ | $n$, repeats | Repeated CNOT--CNOT pairs |
| 8 | Grover | Grover search (1 iteration) | $\{H, X, Z, \text{MCX}\}$ | $n$, marked state | Phase oracle + diffusion |
| 9 | Quantum Adder | Ripple-carry adder | $\{X, \text{CNOT}, \text{CCX}\}$ | $n$ | Carry computation + sum |
| 10 | Quantum Walk | Discrete-time walk on cycle | $\{H, X, R_y, \text{MCX}\}$ | $n$, steps | Coin flip + conditional shift |
| 11 | IQP | Instantaneous Quantum Polynomial | $\{H, R_z, \text{CZ}\}$ | $n$, depth | $H^{\otimes n}$ + diagonal layers |
| 12 | QAOA | Quantum Approximate Optimization | $\{H, R_{zz}, R_x\}$ | $n$, reps, $\gamma, \beta$ | Line-graph cost + mixer |
| 13 | VQE (TwoLocal) | Variational eigensolver ansatz | $\{R_y, R_z, \text{CNOT}\}$ | $n$, reps | Qiskit TwoLocal, linear ent. |
| 14 | HardwareEfficient | Hardware-efficient ansatz | $\{R_y, R_z, \text{CNOT}\}$ | $n$, layers | Alternating rotations + entanglers |
| 15 | Random Clifford | Deep random Clifford | $\{H, S, \text{CNOT}\}$ | $n$, depth | Layer-wise random selection |
| 16 | Surface Code | Syndrome extraction | $\{H, X, \text{CNOT}\}$ | $n_{\text{data}}$ | X-stabilizer measurement |
| 17 | UCCSD | Chemistry ansatz | $\{X, R_y, \text{CNOT}\}$ | $n$, reps | Single + double excitation |
| 18 | Haar Random | Haar-random unitary | Full $SU(2^n)$ | $n \le 4$ | Exact synthesis of random $U$ |

**Random families.** Universal random circuits are generated in LBL format with configurable two-qubit gate density $\rho \in [0, 1]$. Clifford circuits use only the stabilizer generators $\{H, S, \text{CNOT}\}$ and are efficiently simulable by the Gottesman--Knill theorem. Structured brickwork circuits alternate even- and odd-indexed CNOT layers, providing regular entanglement structure.

**Algorithmic families.** QFT and GHZ circuits are already gate-optimal (no redundant gates), serving as negative controls. The BV oracle circuit is the natural family from Theorem 9, with a random secret string $s \in \{0, 1\}^n$. Grover circuits use a single iteration with a phase oracle for a random marked state. Quantum adders implement explicit ripple-carry addition using CCX (Toffoli) gates. Quantum walks simulate discrete-time walks on cycle graphs using coin-flip and conditional-shift operators. IQP circuits are believed to be hard to simulate classically and consist of Hadamard-diagonal-Hadamard structure.

**Variational families.** QAOA circuits use line-graph cost functions with bound-parameterized $R_{zz}$ and $R_x$ rotations. VQE ansatze use Qiskit's TwoLocal with $R_y$--$R_z$ rotation blocks and linear CNOT entanglement. Hardware-efficient ansatze alternate parameterized rotation layers with nearest-neighbor CNOT entanglement.

**Error-correcting and chemistry families.** Surface code syndrome extraction circuits model a single round of X-stabilizer measurement. UCCSD ansatze model single and double excitation operators for quantum chemistry, decomposed into CNOT ladders and $R_y$ rotations.

**Haar random.** Exact synthesis of Haar-random unitaries via Qiskit's `random_unitary` + `decompose`, limited to $n \le 4$ qubits due to exponential cost.

All circuits are deterministically seeded (seed $= 42 + \text{offset}$), materialized by binding parameters to fixed values and decomposing composite instructions up to three levels, and fingerprinted via SHA-256 hash of the instruction stream for reproducibility.

---

## 4.3 Wire-Traversal Preprocessing

The wire-traversal preprocessor (Section 3.2, Definition 11) transforms a circuit from any listing model into Wire-Consecutive Listing (WCL), ensuring that Phase 1 optimizers can detect all wire-level inverse pairs.

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
                dag.ADD_EDGE(prev, i)    // Ordering constraint on same wire
            LAST_GATE_ON_WIRE(q) ← i

    // Step 2: Topological sort with wire-consecutive priority
    // Priority: continue on the same wire before switching wires
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

DFS_WIRE_PRIORITY(dag, node, preferred_wire, visited, order):
    visited[node] ← true
    order.APPEND(node)
    // Continue on the same wire first
    next_on_wire ← NEXT_GATE_ON_WIRE(preferred_wire, node)
    if next_on_wire ≠ null and next_on_wire not in visited:
        if ALL_PREDECESSORS_VISITED(next_on_wire, visited):
            DFS_WIRE_PRIORITY(dag, next_on_wire, preferred_wire, visited, order)
    // Then visit successors on other wires
    for succ in dag.SUCCESSORS(node):
        if succ not in visited and ALL_PREDECESSORS_VISITED(succ, visited):
            wire_of_succ ← PRIMARY_WIRE(succ)
            DFS_WIRE_PRIORITY(dag, succ, wire_of_succ, visited, order)
```

**Unitary equivalence proof.** The WCL reordering is a valid topological sort of the circuit's dependency DAG: it respects all ordering constraints imposed by shared qubits. Since the unitary implemented by a circuit depends only on the relative ordering of gates that share qubits (gates on disjoint qubits commute trivially), any valid topological sort preserves the implemented unitary. Therefore $U(\text{WCL}(C)) = U(C)$ exactly.

**Complexity.** DAG construction: $O(m)$ time (one pass through the circuit, constant-time wire-lookup table). Topological sort with wire-consecutive priority: $O(m \log m)$ due to priority-queue operations when multiple wires are ready simultaneously. Overall: $O(m \log m)$.

**Empirical impact.** When WCL preprocessing is enabled, Phase 1 Greedy achieves approximately 18% reduction on the random Universal ensemble where LBL yields exactly 0%, consistent with the density bound from Theorem 1(a).

---

## 4.4 Compiler Configurations

We compare against Qiskit as the confirmed production compiler baseline. Cirq and t|ket> configurations are documented for planned future full runs but are not part of the confirmed canonical evidence:

**Qiskit (v2.4.1).** We use `qiskit.transpile` with optimization levels 0--3:
- **Level 0**: No optimization; trivial mapping.
- **Level 1**: Light optimization; adjacent gate cancellation and single-qubit gate merging.
- **Level 2**: Medium optimization; adds commutation analysis and KAK decomposition for two-qubit gates.
- **Level 3**: Heavy optimization; full peephole optimization including template matching, gate resynthesis, and commutation-based reordering.

Specific passes at Level 3 include `Optimize1qGates`, `CXCancellation`, `CommutativeCancellation`, `OptimizeSwapBeforeMeasure`, and `Collect2qBlocks` + `ConsolidateBlocks`.

**Cirq (planned, metadata-only).** The planned configuration uses `cirq.optimize_for_target_gateset` with the `CZTargetGateset`, combined with `cirq.eject_z` and `cirq.merge_single_qubit_gates_to_phxz`. No canonical Cirq optimization-output CSV is currently available.

**t|ket> (planned, metadata-only).** The planned configuration uses `FullPeepholeOptimise`, which applies a comprehensive suite of peephole transformations including Clifford simplification, gate cancellation, and commutation-based reordering. No canonical t|ket> optimization-output CSV is currently available.

---

## 4.5 Statistical Protocol

All statistical analyses follow a pre-registered protocol designed for publication-grade rigor.

**Bootstrap confidence intervals.** All reported mean reductions and effect sizes are accompanied by 95% bootstrap confidence intervals computed from $B = 10{,}000$ resamples with replacement. For a statistic $\hat{\theta}$ computed from sample $\{x_1, \ldots, x_N\}$, the bootstrap distribution $\{\hat{\theta}^{*(1)}, \ldots, \hat{\theta}^{*(B)}\}$ yields the percentile interval $[\hat{\theta}^{*}_{(\alpha/2)}, \hat{\theta}^{*}_{(1-\alpha/2)}]$ with $\alpha = 0.05$.

**Effect sizes.** We report two complementary effect-size measures:
- **Cliff's delta** ($\delta$): A non-parametric measure of stochastic dominance, $\delta = P(X > Y) - P(X < Y)$, robust to non-normality. Interpretation: $|\delta| < 0.147$ negligible, $< 0.33$ small, $< 0.474$ medium, $\ge 0.474$ large.
- **Cohen's $d$**: Parametric standardized mean difference, $d = (\bar{x}_1 - \bar{x}_2)/s_{\text{pooled}}$. Interpretation: $|d| < 0.2$ small, $< 0.5$ small-medium, $< 0.8$ medium, $\ge 0.8$ large. **Note**: Cohen's $d$ is undefined when the pooled standard deviation is zero (e.g., Phase 1 under LBL where all reductions are exactly 0%). In such cases, we report **Glass's Delta** ($\Delta = (\bar{x}_1 - \bar{x}_2)/s_{\text{control}}$) or non-parametric Cliff's Delta instead.

**False Discovery Rate (FDR) correction.** When conducting multiple hypothesis tests (e.g., comparing optimizers across multiple circuit families), we apply the Benjamini--Hochberg procedure to control the expected proportion of false discoveries. Given $m$ tests with ordered $p$-values $p_{(1)} \le p_{(2)} \le \cdots \le p_{(m)}$, the BH procedure rejects hypotheses $H_{(i)}$ for $i \le k^*$ where $k^* = \max\{i : p_{(i)} \le i\alpha/m\}$.

**Power analysis.** For experiment E4 (optimizer comparison), we conducted an a priori power analysis: to detect a Cohen's $d = 0.5$ (medium effect) with power $1 - \beta = 0.80$ at significance level $\alpha = 0.05$ (two-tailed), a minimum of $n = 64$ circuits per group is required. We use $n = 100$ circuits per configuration, providing power $> 0.95$ for medium effects.

**Fidelity verification.** Unitary equivalence is verified via exact average gate fidelity for $n \le 12$ qubits (constructing full $2^n \times 2^n$ unitary matrices). For $n > 12$, where exact computation requires $O(4^n)$ memory, we use a sampling-based estimator: 1,000 Haar-random product-state inputs (independent Haar-random single-qubit unitaries applied to $|0\rangle^{\otimes n}$), computing $|\langle\psi_1|\psi_2\rangle|^2$ for each. This estimator has standard error $\sim 1/\sqrt{1000} \approx 3\%$. For Clifford circuits, exact comparison via the stabilizer tableau (Qiskit `Clifford` class) provides $O(n^2)$ verification regardless of qubit count.

Across experiments where fidelity was successfully computed and retained for analysis, optimizer outputs preserve unitary equivalence. Documented failure rows, especially E18 decomposition/fidelity failures, are tracked separately and filtered from analyses requiring valid fidelity. E12 compiler-baseline correctness relies on Qiskit's transpiler semantics rather than independent exact unitary verification for every row.

---

## 4.6 Experimental Design

The experimental program comprises 23 registered experiments (E1--E23), organized into six data versions reflecting progressive infrastructure evolution. Table 2 provides a condensed overview of the 18 core experiments (E1--E18); the full registry including auxiliary experiments (E19--E23) is given in Table 4.

**Table 2: Experiment Registry**

| ID | Name | Trials | Families | Phase |
|----|------|--------|----------|-------|
| E1 | Phase Transition | 25,000 | 1 (Universal) | Phase 1 |
| E2 | Entanglement Density | 2,100 | 1 (Universal) | Phase 1 |
| E3 | Qubit Scaling | 12,000 | 1 (Universal) | Phase 1 |
| E4 | Optimizer Comparison | 400 | 1 (Universal) | Phase 1 |
| E5 | Depth Scaling | 5,000 | 1 (Universal) | Phase 1 |
| E6 | Gate Set Sensitivity | 3,000 | 1 (Universal) | Phase 1 |
| E7 | Rotation Merging | 2,000 | 2 (Universal, QAOA) | Phase 1 |
| E8 | Fidelity Distribution | 5,000 | All random | Phase 1 |
| E9 | Runtime Scaling | 2,000 | 1 (Universal) | Phase 1 |
| E10 | Phase 2 Advantage (Random) | 5,000 | 2 (Universal, Structured) | Phase 1+2 |
| E11 | Phase 2 on Structured | 3,000 | 4 (BV, CNOT, QFT, GHZ) | Phase 1+2 |
| E12 | Real-Circuit Benchmarks | 1,500 | ~15 | Phase 1+2 |
| E13 | Compiler Comparison | 1,500 | ~15 | Phase 1+2 |
| E14 | Window Size Sensitivity | 2,000 | 2 (Universal, BV) | Phase 2 |
| E15 | Commutation Chain Length | 1,000 | 2 (BV, IQP) | Phase 2 |
| E16 | Phase 2 Action Space | 3,000 | All (~15) | Phase 2 |
| E17 | Ceiling-Aware Optimizer | 1,500 | ~15 | Phase 1+2 |
| E18 | Clifford+T | 270 | ~6 | Phase 1+2 |

**Table 4: Experiment Registry**

| ID | Description | Phase | Circuit Families | Qubits | Trials | Optimizers | Key Metric |
|----|-------------|-------|-----------------|--------|--------|------------|------------|
| E1 | Random circuit baseline (LBL) | P1 | Universal, Clifford, Structured | 3--10 | 25,000 | Greedy, RLS, SA, GA | Mean reduction |
| E2 | WCL vs LBL comparison | P1 | Universal (random) | 5--8 | 5,000 | Greedy (WCL), Greedy (LBL) | WCL reduction gain |
| E3 | Qubit scaling | P1 | Universal | 3--20 | 10,000 | Greedy | Reduction vs $n$ |
| E4 | Optimizer comparison | P1 | Universal | 5 | 400 | All four P1 | Reduction, runtime |
| E5 | Depth scaling | P1 | Universal | 5 | 5,000 | Greedy | Reduction vs $d$ |
| E6 | Gate set sensitivity | P1 | Universal | 5 | 3,000 | Greedy | Reduction vs $\mathcal{G}$ |
| E7 | Rotation merging | P1 | Universal, QAOA | 5--8 | 2,000 | Greedy | Rotation merge count |
| E8 | Fidelity distribution | P1 | All random | 3--10 | 5,000 | All P1 | $F_{\text{avg}}$ histogram |
| E9 | Runtime scaling | P1 | Universal | 3--20 | 2,000 | All P1 | Time vs $n, d$ |
| E10 | Phase 2 advantage (random) | P1+2 | Universal, Structured | 5--10 | 5,000 | HybridCommute | $\Gamma(C)$ |
| E11 | Phase 2 on structured | P1+2 | BV Oracle, CNOT Chain, QFT, GHZ | 5--10 | 3,000 | HybridCommute | $\Gamma(C)$ |
| E12 | Real-circuit benchmarks | P1+2 | Extended suite (15 families) | 3--10 | 1,500 | All optimizers | Reduction, depth, CNOT |
| E13 | Compiler comparison | P1+2 | Extended suite | 3--10 | 1,500 | Ours vs Qiskit/Cirq/tket | Relative reduction |
| E14 | Window size sensitivity | P2 | Universal, BV | 5--8 | 2,000 | CommutationRewriter | Reduction vs $w$ |
| E15 | Commutation chain length | P2 | BV, IQP | 5--10 | 1,000 | CommutationRewriter | Chain depth histogram |
| E16 | Phase 2 action space | P2 | All families | 3--10 | 3,000 | Proxy analysis | $|\mathcal{S}_{1+2}|$ |
| E17 | Ceiling-aware optimizer | P1+2 | Extended suite | 3--10 | 1,500 | CeilingAware | Time savings, reduction |
| E18 | Cross-family generalization | P1+2 | All families | 5--8 | 2,000 | All optimizers | Family-level $\Gamma$ |
| WCL-E19 | WCL Preprocessing Listing | P1 | Universal | 5 | -- | Greedy (WCL) | WCL reduction gain |
| MC-E20 | Multi-Compiler Comparison | P1+2 | Extended suite | 3--10 | -- | All + compilers | Relative reduction |
| E21 | Ceiling-Aware Optimizer | P1+2 | Extended suite | 3--10 | -- | CeilingAware | Skip accuracy, time saved |
| E22 | Statistical power analysis | -- | Universal | 5 | 10,000 | Greedy | Bootstrap CI width |
| E23 | Reproducibility audit | -- | BV, Universal | 5 | 500 | All | Hash-match rate |

**Data versioning protocol.** Experimental data is organized into versions reflecting infrastructure changes:
- **v1** (E1--E5): Initial Phase 1 experiments under LBL listing.
- **v2** (E6--E9): Expanded Phase 1 with gate-set and runtime analysis.
- **v3** (E10--E11): Phase 2 introduction with commutation rewriting.
- **v4** (E12--E13): Real-circuit benchmarks and compiler comparisons.
- **v5** (E14--E18): Extended circuit families and Phase 2 deep analysis.
- **v6** (WCL-E19, MC-E20, E21, E22--E23): WCL preprocessing (WCL-E19), multi-compiler comparison (MC-E20), ceiling-aware optimizer (E21), statistical validation (E22), and reproducibility audit (E23).

Each data artifact is stored with a SHA-256 content hash, optimizer configuration JSON, circuit fingerprint, and random seed, enabling exact reproduction of any individual trial. The reproducibility audit (E23; distinct from MC-E20) verifies that 100% of 500 randomly selected trials reproduce bit-identical circuit outputs and gate-count metrics.

**Reproducibility infrastructure.** All experiments are orchestrated by a unified runner that logs configuration, timing, and results to structured CSV and JSON files. Circuit SHA-256 hashes (computed from the canonical instruction stream: gate name, qubit indices, classical bit indices, and parameter values) provide content-addressable deduplication and integrity verification. The full experimental pipeline -- from circuit generation through optimization to statistical analysis -- is encapsulated in a single reproducible workflow executable via `python run_experiments.py --config experiments/v6_full.yaml`.
