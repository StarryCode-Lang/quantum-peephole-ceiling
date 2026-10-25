# BV k+2 — exact achievability verified, optimality partially proven (2026-10-25)

**Status**: theory document, review grade. Companion verifier:
`scripts/verify_bv_lower_bound.py` (report:
`docs/review/science_boost/2026-10-25_bv_lower_bound/verification_report.json`,
status `ALL_PASS`).

This document supersedes an earlier draft written the same day whose central
identity was **false** (it claimed the E26 listing equals
$\mathrm{CZ}_S H_a X_a$; it does not — H conjugating the *control* of a CNOT
is not H conjugating the *target*). Every statement below is machine-checked
in exact arithmetic; the verifier exists precisely because the hand derivation
failed once. What survives is narrower than the round-13 audit hoped, and it
is stated without decoration.

---

## 1. The E26 family and the true closed form

The E26 generator (`experiments/phase2b_full_validation.py::_make_bv_with_secret`)
emits, on $n$ data qubits plus ancilla $a$ (wire $n$):

$$C_{\text{orig}} = x(a),\, h(a),\, h^{\otimes n},\;
\prod_{i \in S} cx(i \to a),\, h^{\otimes n},
\qquad |S| = k,$$

with $2n + k + 2$ gates. **Verified identity** (all secrets, $n \le 5$, exact
arithmetic — `check_identities` mode, 62/62 pairs):

$$U \;=\; h^{\otimes n}\,\mathrm{CX}_S(d{\to}a)\,h^{\otimes n}\,H_a X_a
\;=\; H_a\,\mathrm{CX}_S(a{\to}d)\,X_a,$$

i.e. the data-Hadamard sandwich around the control-side CNOTs collapses to
**Hadamard pairs on the ancilla with the CNOT direction reversed**. The proof
is two textbook steps: $cx(i{\to}a) = H_a\,cz(i,a)\,H_a$ (H on the *target*
converts CX↔CZ), and $h_i\,cz(i,a)\,h_i = cx(a{\to}i)$ (H on the *control* of
a CZ reverses the CNOT); substituting and cancelling the ancilla Hadamards
gives the identity. The naive intermediate form
$\mathrm{CZ}_S H_a X_a$ is **not** an identity for this listing.

## 2. Achievability: the pipeline's $k{+}2$ is exactly right (machine-verified)

By the identity above, the circuit

$$\big[\,x(a),\; cx(a{\to}i)\ \text{for } i \in S,\; h(a)\,\big]$$

implements $U$ with exactly $k + 2$ gates over $\{h, x, cx\}$. This is the
circuit the Phase-2b pipeline actually emits (verified structurally on
$n \le 2$ and unitarily on all tested instances).

`achievability` mode: the **real** `Phase2bTemplateMatcher.optimize_full_pipeline`
run on 24 BV instances ($n = 3..10$, the all-ones secret plus two seeded
secrets per size) produces outputs of size **exactly $k+2$ in 24/24** cases,
unitarily equivalent to the input — exactly (sympy, up to global phase) for
$n \le 6$, and via Qiskit `Operator.equiv` throughout. The E26 headline
("achieved size exactly $k{+}2$ on 80/80") is therefore reproducible from the
committed code and certificate-checked, not merely recorded.

## 3. Optimality: what is proven, and what is not

**Theorem A (non-monomiality, all $n$).** $U$ is not a permutation matrix of
the computational basis: every column has two non-zero entries (the ancilla
$H_a$ factor). Hence no pure-CNOT circuit implements $U$; at least one 1q
gate is necessary. (Verified `monomial` mode, $n \le 4$; the analytic
argument is immediate.)

**Theorem B (Schmidt bound, all $n$).** Across every single-wire cut
$\{w\}$ with $w \in S \cup \{a\}$, $U$ has Schmidt rank 2 (the gate
$cx(a{\to}w)$ straddles the cut and is the only factor that acts across it);
across cuts $\{w\}$ with $w \notin S$, rank 1. Since a 1q gate has Schmidt
rank 1 across every cut and a $cx$ gate has rank $> 1$ across only the two
cuts at its endpoints, any implementing circuit uses at least
$\lceil (k+1)/2 \rceil$ cx gates, hence at least $\lceil (k+1)/2 \rceil + 1$
total gates.

**Theorem C (Case-B exclusion, $n \le 3$; exhaustive).** For $n \le 3$ there
is **no** circuit with exactly $k$ cx gates and exactly one 1q gate
implementing $U$ (`exhaustive` mode: every $(L_1, L_2)$ pair of CNOT maps
with $\mathrm{len}(L_1)+\mathrm{len}(L_2) = k$ from a BFS of
$GL(n{+}1,2)$, every wire choice for the 1q gate, exact arithmetic; zero
witnesses over all 14 secrets). Together with Theorem A this proves
**total $\ge k+2$ for $n \le 3$** *among circuits whose cx count is at least
$k$*; partitions with fewer cx gates and more 1q gates are covered only by
Theorem B's weaker bound.

**Open (the honest gap).** For $n \ge 4$, a circuit with $< k$ cx gates and
$\ge 2$ one-qubit gates — total still $\le k{+}1$ — is **not excluded** by any
argument in this document. Two structural facts explain why the easy tools
fail, both machine-verified:

- $U^\dagger X_a\,U = -Z_a$, **independent of $S$**; and for $i \in S$,
  $U^\dagger X_i U = \pm X_i$. Every single-Pauli Heisenberg image of $U$
  has wire support $\le 2$ — $U$ is *Pauli-invisible*, so no Clifford-style
  support-walk can recover a $k$-dependent bound.
- The Schmidt bound saturates at $\lceil (k+1)/2 \rceil$ because each
  $cx(a{\to}i)$ straddles two useful cuts.

Resolving the gap needs tools that see the joint entangling structure (e.g.
a KAK/canonical-form argument on $n{+}1$ qubits, or an interaction-number
invariant), which is genuine research work beyond this round. The round-13
audit's "数日内可证" estimate assumed the (false) CZ-form identity; the
corrected problem is harder.

## 4. What this resolves of WL-1, and the writing-time guidance

- The manuscript's "achieved size exactly $k+2$ on 80/80" is now
  **machine-verified and reproducible** (§2) — the empirical half of the
  claim is solid.
- The word **"provable/exact optimum"** (abstract line 43, §6.4 line 772,
  §8 line 1333) must be downgraded at writing time: what is proven is
  Theorems A–C. Suggested wording: "reaches the $k{+}2$ size (verified
  unitarily), which is optimal among $k$-cx circuits for $n \le 3$ and for
  which no smaller circuit is known; general optimality is open (§3)."
- `claim_evidence_table.csv` C13's caveat ("not that n+2 is a global
  gate-count optimum") remains **correct** and should be kept, with the
  verifier report referenced as the precise scope statement.
- Table 11 errata (writing time): (1) "Original size $2n+k$" should read
  $2n+k+2$ (the reduction arithmetic $2n/(3n+2)$ is consistent only with
  $2n+k+2$); (2) the "per-instance excess 3.1–4.2×" range does not follow
  from the stated formulas ($(9n+8)/(3n+2) \in [3.06, 3.18]$ for
  $n \in [3,10]$) and needs a source check.

## 5. Provenance

- Verifier: `scripts/verify_bv_lower_bound.py`, exact sympy arithmetic over
  $\mathbb{Q}(i, \sqrt2)$; report JSON with per-instance records in
  `docs/review/science_boost/2026-10-25_bv_lower_bound/`.
- Modes and outcomes (2026-10-25): `check_identities` 62/62 PASS ($n \le 5$);
  `monomial` PASS ($n \le 4$); `achievability` 24/24 PASS ($n = 3..10$);
  `exhaustive` 14/14 secrets no-witness ($n \le 3$). Status `ALL_PASS`.
- Produced during the 2026-10-25 execution round (P6 theory track) while the
  v16 re-pin compute ran; review grade, outside the release hash chain.
