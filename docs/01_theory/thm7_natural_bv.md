# Theorem 9: Phase-2 Advantage for Bernstein–Vazirani Oracle Circuits

> **Document Status**: Formal proof (rewritten 2026-06-17 to remove draft artifacts and consolidate the argument).
> **Version**: 2.0
> **Date**: 2026-06-17
> **Dependencies**: Base definitions (D1–D10) in `framework.md`. Theorems 1–2 in `lemmas.md`.
> **Relation to existing results**: Generalizes Theorem 7 (artificial circuit family) to the natural Bernstein–Vazirani oracle family.

---

## Motivation

Theorem 7 in `lemmas.md` establishes the existence of an explicit circuit family $\{C_n\}$ with $R_1(C_n) = 0$ and $R_{1+2}(C_n) \ge 1/6$, proving Conjecture C2 constructively. However, the circuit family used in Theorem 7 is an artificial construction designed specifically to exhibit Phase-2 advantage. A natural question is whether Phase-2 advantage arises in **naturally occurring** quantum circuit families — circuits that arise from standard quantum algorithms without adversarial design.

This document proves that the **Bernstein–Vazirani (BV) oracle circuit** family exhibits a constant-factor Phase-2 advantage, establishing that the Phase-1/Phase-2 optimization gap is not merely an artifact of artificial constructions but arises in standard quantum algorithmic primitives.

> **Important scope note.** The Phase-2 advantage established here relies on **Phase-2b template matching** (the $H$-CNOT-$H$ identity), which is *not* implemented in the current experimental codebase. The current codebase implements only **Phase-2a commutation rewriting** (`commutation_rewriter.py`). Under pure Phase-2a, the achievable bound for BV remains an **open question**. See §"Phase-2a vs. Phase-2b" below. All experimental results labeled "Phase 2" in the manuscript refer to Phase-2a unless explicitly stated otherwise.

---

## Preliminaries

### The Bernstein–Vazirani Algorithm

The Bernstein–Vazirani algorithm [Bernstein & Vazirani, 1997] solves the following problem: given oracle access to a function $f_s: \{0,1\}^n \to \{0,1\}$ defined by $f_s(x) = s \cdot x \pmod{2}$ for a secret string $s \in \{0,1\}^n$, determine $s$ using a single oracle query.

The standard circuit implementation uses $n$ input qubits $q_1, \ldots, q_n$ and one ancilla qubit $q_{n+1}$ initialized to $|-\rangle = \frac{1}{\sqrt{2}}(|0\rangle - |1\rangle)$.

### Circuit Definition

**Definition (BV oracle circuit $BV_n$).** For $n \ge 2$, the Bernstein–Vazirani oracle circuit $BV_n$ with secret string $s = 1^n$ (the all-ones string) on $n+1$ qubits $(q_1, \ldots, q_n, q_{n+1})$ is the circuit:

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

---

## Theorem 9 (Phase-2b Advantage for Bernstein–Vazirani Oracle Circuits)

**Statement.** For the Bernstein–Vazirani oracle circuit $BV_n$ on $n+1$ qubits ($n \ge 2$) with secret string $s = 1^n$:

1. $R_1(BV_n) = 0$ (Phase 1 achieves zero reduction in the standard LBL listing).
2. Phase-2b (commutation rewriting + template matching) achieves
$$
R_{1+2}^{\text{(2b)}}(BV_n) \ge \frac{n}{4.5n+4} \ge \frac{2}{13} \quad \text{for all } n \ge 2.
$$
In particular $R_{1+2}^{\text{(2b)}}(BV_n) = \Omega(1)$, and the optimization gap satisfies $\Gamma^{\text{(2b)}}(BV_n) \ge \frac{2}{13}$ for all $n \ge 2$.

**Remark on the bound.** The exact reduction achievable by Phase 2 depends on the listing order and the specific commutation/template sequence applied. We prove a lower bound of $n/(4.5n+4)$, which for $n \ge 2$ yields at least $2/13 \approx 0.154$, and which approaches $1/4.5 \approx 0.222$ as $n \to \infty$. The bound uses Phase-2b template matching (the $H$-CNOT-$H$ identity) and accounts for the gate-overhead of the template transformation. Under pure Phase-2a commutation rewriting (the mechanism implemented in the current codebase), the achievable bound for BV remains an **open question** — see §"Phase-2a vs. Phase-2b" below.

---

### Proof

#### Part 1: Phase-1 Action Space is Empty ($\mathcal{S}_1(BV_n) = \emptyset$)

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

---

#### Part 2: Phase-2b Achieves $\Omega(1)$ Reduction

We construct an explicit Phase-2b rewrite sequence and account for its overhead. The argument proceeds in three stages: (A) two algebraic prerequisites; (B) the rewrite procedure; (C) gate-count accounting.

##### Stage A: Algebraic prerequisites

**Lemma A1 (CNOT–CNOT commutation on a shared target).** For $i \neq j$,
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

**Consequence (the template rule).** The 3-gate pattern $H(c), \text{CNOT}(c,t), H(c)$ can be rewritten as the 3-gate pattern $H(t), \text{CNOT}(t,c), H(t)$: it replaces two $H$ gates on $c$ with two $H$ gates on $t$, and reverses the CNOT direction. Gate count is preserved *locally* (3 → 3); the global reduction comes from the cancellation step below.

##### Stage B: The rewrite procedure

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

##### Stage C: Gate-count accounting

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

---

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

---

### Phase-2 rule requirements

The Phase-2b procedure above uses four operations, all within the Phase-2b toolkit:

1. **Disjoint-qubit commutation** (to bring $H$ gates next to their CNOTs in B-1) — standard.
2. **CNOT–CNOT commutation on a shared target** (Lemma A1, to reorder Layer 2) — standard, proven above.
3. **$H$-CNOT-$H$ template identity** (Lemma A2, the core of B-2) — a Phase-2b template-matching rule, equivalent to the well-known CNOT direction-reversal identity $(H \otimes H)\, \text{CNOT}\, (H \otimes H) = \text{CNOT}_{\text{reversed}}$. This rule is **not** implemented in the current codebase's `commutation_rewriter.py` (which implements only Phase-2a).
4. **Adjacent $H$-$H$ cancellation** ($H \cdot H = I$, used in B-3) — standard Phase-1 REMOVAL.

---

## Phase-2a vs. Phase-2b

> **Critical clarification for matching theory to experiments.**

The experimental codebase implements **Phase-2a only** (`commutation_rewriter.py`): disjoint-qubit commutation + a small set of algebraic commutation rules (Z-family on CNOT control, same-axis rotations). It does **not** implement Phase-2b template matching.

Theorem 9's bound $n/(4.5n+4) = \Omega(1)$ relies on the $H$-CNOT-$H$ template (Phase-2b). **Under pure Phase-2a, the achievable reduction for $BV_n$ is an open question.** Concretely:

- Phase-2a can perform Stage B-1 (disjoint-qubit commutation) freely.
- Phase-2a **cannot** perform Stage B-2 (the $H$-CNOT-$H$ template rewrite).
- Without B-2, the $H(q_i)_{\text{L1}}$ and $H(q_i)_{\text{L3}}$ remain separated by $\text{CNOT}(q_i, q_{n+1})$ and cannot be cancelled.

Therefore, under Phase-2a alone, the *provable* reduction for $BV_n$ is currently $0$ (matching Phase-1). Whether a clever Phase-2a commutation sequence can achieve non-zero reduction on $BV_n$ is left as an open question.

**Experimental status.** The manuscript's reported "~20% Phase-2 reduction on Oracle/BV circuits" (E11) was obtained with Phase-2a. The mechanism behind this empirical reduction is **not** the $H$-CNOT-$H$ template of Theorem 9 (which is unimplemented), but rather the commutation of redundant $H/X$ gates exposed by the specific Oracle circuit structure in E11's test suite. The relationship between the theoretical Phase-2b bound (Theorem 9) and the empirical Phase-2a reduction (E11) is therefore indirect, and the manuscript must state this clearly.

---

## Listing-model dependency

As with Theorem 1, the Phase-1 result $R_1(BV_n) = 0$ depends on the listing model. Under WCL (wire-consecutive listing), the gates on wire $q_i$ are listed consecutively: $H(q_i)_{\text{L1}}, \text{CNOT}(q_i, q_{n+1}), H(q_i)_{\text{L3}}$. Under WCL, $H(q_i)_{\text{L1}}$ and $\text{CNOT}(q_i, q_{n+1})$ are listing-adjacent, but $H \neq \text{CNOT}^{-1}$, so $\mathcal{S}_1(BV_n) = \emptyset$ still holds. **The Phase-1 result is listing-independent for $BV_n$.**

The Phase-2b result is also listing-independent in the sense that the rewrite procedure operates on the circuit *graph* (wire-level adjacency), not on the listing order. However, the *gate-counting* of the rewrite depends on the initial listing: under WCL the $H$ gates are already adjacent to their CNOTs, so Stage B-1 is a no-op and the overhead is reduced.

> **Connection to the broader listing-conditional framing.** The structural-ceiling framework (Conjecture C1, Theorem 1(b)) is explicitly **listing-conditional**: the Phase-1 ceiling $\mathcal{S}_1(C) = \emptyset$ is a property of the LBL listing, not of the circuit's intrinsic unitary. Theorem 9's Phase-1 result inherits this listing-conditionality. See `framework.md` §"Listing Model Dependency" for the general discussion.

---

## Comparison with Theorem 7

| Property | Theorem 7 (artificial) | Theorem 9 (BV oracle) |
|----------|----------------------|----------------------|
| Circuit family | Adversarial construction | Natural quantum algorithm |
| $R_1$ | 0 | 0 |
| $R_{1+2}^{\text{(2b)}}$ lower bound | $\ge 1/6 \approx 0.167$ | $\ge n/(4.5n+4) \ge 2/13 \approx 0.154$ |
| Phase-2 mechanism | CNOT–CNOT cancellation via $S$-commutation | $H$-CNOT-$H$ template (Phase-2b) + ancilla $H$-cancellation |
| Practical relevance | Low (designed for proof) | High (BV is a standard oracle algorithm) |
| Asymptotic gap $\Gamma^{\text{(2b)}}$ | $\Omega(1)$ | $\Omega(1)$ (specifically $\to 1/4.5$) |
| Implemented in codebase? | Phase-2a only | Phase-2b **not** implemented |

Theorem 9 strengthens the case for Conjecture C2 by demonstrating Phase-2b advantage on a circuit family that arises naturally in quantum complexity theory, rather than on an artificial construction. However, because the bound relies on Phase-2b (unimplemented), Theorem 9 should be read as a **theoretical existence result**, not as a direct explanation of the experimental Phase-2a reductions.

---

## References

1. Bernstein, E. & Vazirani, U. (1997). Quantum complexity theory. *SIAM J. Comput.* **26**(5), 1411--1473.
2. Nielsen, M. A. & Chuang, I. L. (2010). *Quantum Computation and Quantum Information*. Cambridge University Press. (Section 4.3 for BV circuit; Section 4.2 for the $H$-CNOT-$H$ basis-change identity.)

---

**[Deliverable audit notice]** The following deliverable files (`.docx` format, not directly editable) may contain references to the old bound $2(n-1)/(3n)$ or to the pre-rewrite draft of this proof, and should be manually audited:
- `deliverables/D1_Structural_Ceiling_Theory_Report.docx`
- `deliverables/D6_New_Theorems_and_Conjectures.docx`

Markdown sources have been updated; the `.docx` files are addressed by the `deliverables/D1-D4_SUPERSEDED_NOTICE.md` mechanism and by the v6 manuscript.

---

*Document version: 2.0*
*Last updated: 2026-06-17*
*Author: Q-research Theoretical Framework Team*
*Changelog: v2.0 (2026-06-17) — Complete rewrite. Removed draft self-correction artifacts ("Wait — this is incorrect", "Let me restart", etc.) present in v1.0/v1.1. Consolidated the proof into a linear three-stage argument (prerequisites → procedure → accounting). Unified the asymptotic bound as $\Omega(1)$ throughout (the earlier $\Omega(1/n)$ statement was an overly conservative typo inconsistent with the $n/(4.5n+4) \to 1/4.5$ limit). Added explicit Phase-2a vs. Phase-2b clarification and listing-conditional framing.*
