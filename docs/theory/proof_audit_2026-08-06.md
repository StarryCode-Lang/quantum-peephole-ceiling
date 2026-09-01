# Proof Audit — 2026-08-06

> **Scope**: Independent step-by-step audit of the formal proofs backing the
> manuscript's theory section, requested by the 2026-08-01 publication-
> readiness audit (finding F4: "Thm 5 / Thm 8 require independent proof
> audits"). Auditor: automated review pass (Chloe), with all proofs re-read
> against their statements.
>
> **Method**: Each proof was checked for (i) logical validity of every step,
> (ii) hidden assumptions, (iii) constant factors, (iv) scope/regime
> mismatches with the experiments.

## Verdicts

| Result | File location | Verdict | Notes |
|---|---|---|---|
| Thm 1(a) (Obs 1(a)) | formal_results.md §1 | **CORRECTED 2026-08-06** | Two constant errors found and fixed; corrected formula validated by E30 |
| Thm 1(b) (Obs 1(b)) | formal_results.md §1 | SOUND | Definitional; no gaps |
| Thm 2(a)-(d) | formal_results.md §1 + Appendix A | **PARTIAL / CORRECTED 2026-08-09** | 2(a) sound; 2(c) restricted; 2(b) open; 2(d) proof invalid because multi-qubit gates do not admit the claimed per-wire-unitary factorization and pair counts are not an established optimum |
| Lemma 3 / Lemma 4 | formal_results.md §1 | SOUND | Trivial supporting lemmas |
| Thm 5 | formal_results.md §1 | **PROOF INCOMPLETE 2026-08-09** | Random-matching endpoints are dependent; stated McDiarmid product space is not the generator |
| Thm 6 | formal_results.md §1 | **GENERAL CLAIM REFUTED 2026-08-09** | Counterexample n=2, seed=35; generator fixed and claim narrowed |
| Thm 7 | formal_results.md §1 | SOUND | Constructive; note: bound carried by Phase-2a (E24: phase2b alone 2.5%) |
| Thm 8(a)-(c) | formal_results.md §1 | **WITHDRAWN 2026-08-09** | Incompatible premises: a polynomial-size exact circuit cannot implement a Haar-random unitary on the claimed high-probability event |
| Thm 9 | formal_results.md Appendix B | CORRECTED 2026-08-11 | all-ones rows n=3..10 match achieved $2n/(3n+2)$ construction; `n+2` global optimality is not proved |
| Prop 1 | formal_results.md §2 | CORRECTED earlier (max-matching version) | Status table carries [CORRECTED] |

## Thm 1(a): constant errors found and fixed

The original statement wrote
$p_{\text{cancel}} = (1-\rho)^2/g_1^2 + \rho^2/(g_2(n-1))$ with a claimed
one-qubit bound $p_{\text{inv}}^{(1q)} \leq 2/g_1^2$. Two errors:

1. **Missing discrete-gate factor.** With uniform drawing from a gate set of
   size $g_1$ containing $k_1$ discrete gates, the exact inverse-match
   probability is $\sum_{g \text{ discrete}} (1/g_1)(1/g_1) = k_1/g_1^2$
   (continuous rotations match with probability zero). For the standard
   11-label set, $k_1 = 8$, so the true value is $8/121 \approx 0.066$, while
   the claimed "upper bound" $2/g_1^2 = 2/121 \approx 0.017$ is **not an
   upper bound at all** for any gate set with $k_1 \geq 3$.
2. **Per-wire double counting of two-qubit pairs.** Summing "over $n$ wires"
   counts each two-qubit cancellation once per endpoint wire. The correct
   per-pair expectation uses $\binom{n}{2}$ pairs with coverage probability
   $(\rho/(n-1))^2$ and gate-match probability $1/g_2$, giving the term
   $\rho^2/(2 g_2 (n-1))$ inside $p_{\text{cancel}}$.

**Corrected statement** (even $n$):

$$\mathbb{E}[|\mathcal{A}_{\text{adj}}|] = n(d-1)\left[(1-\rho)^2\frac{k_1}{g_1^2} + \frac{\rho^2}{2 g_2 (n-1)}\right].$$

Odd-$n$ finite-size corrections (unpaired qubit per layer): replace $\rho$ by
$\rho(n-1)/n$ in the one-qubit term and $1/(n-1)$ by $1/n$ in the pair
coverage. **Experimental validation**: E30 (`data/v10/e30/`, 13,500 trials,
27 cells over $n \in \{4,5,8\}$, $d \in \{10,20,40\}$, $\rho \in \{0,0.3,0.6\}$):
max $|z| = 2.86$, median relative error (ρ > 0) = 1.4%. Both the even-$n$
formula and the odd-$n$ corrections are confirmed.

## Thm 5: detailed notes

**Superseding audit (2026-08-09): the application is incomplete.** The proof
does not define an independent product space whose coordinates generate the
actual random matching distribution.

1. **Independence idealization.** The proof models $N = n(d-1)$ independent
   gate-position choices. Under the exact layer model with random-pairing
   two-qubit gates, choices on paired wires are correlated; the correct
   independent variables are the $\approx (n/2)(d-1)$ pair choices plus the
   one-qubit draws.
2. **Bounded-differences constant.** $c_i = 2$ may hold for per-wire-position
   variables (each gate participates in at most two adjacent pairs on its
   wire). For pair-level variables, changing one pair choice touches up to
   four wire adjacencies, suggesting $c_i = 4$ for a suitable exposure
   martingale. But that martingale and its conditional bounds were not
   constructed. The advertised tail inequality therefore remains unproved.

Empirical status: under LBL, $X = 0$ identically, so E1/E3 satisfy the bound
trivially (manuscript Table 19: "MATCH (trivial)").

## Thm 8: detailed notes

**Superseding audit (2026-08-09): the earlier SOUND verdict was incorrect.**
The counting argument may motivate a lower bound for Haar-random unitaries,
but the theorem then assumes an exact implementing circuit with fewer gates
than that same lower bound.  The claimed sub-exponential-depth regime is
therefore empty on the high-probability event.  It cannot support an
optimization-reduction ceiling without an approximate synthesis model.

1. A dimension/covering argument can bound the approximate circuit complexity
   of Haar-random unitaries for a specified gate model and tolerance, but the
   draft did not state that model rigorously.
2. Even granting such a bound, an exact polynomial-size input circuit cannot
   implement a unitary whose minimum exact size exceeds the input size.
3. Clamping the resulting negative reduction bound to zero does not repair the
   contradictory premises.
4. The theorem is withdrawn, not "partial"; experimental regime disclosure is
   irrelevant to this logical defect.

## Thm 2(b) and former C1: superseding counterexample (2026-08-10)

The earlier algorithm-independence interpretation is **refuted**.  For
`H(q0), X(q1), H(q0)`, the initial adjacent Greedy action set is empty, yet a
legal SWAP of the first two disjoint-support gates exposes `H(q0), H(q0)` and a
subsequent REMOVAL yields the exact one-gate circuit `X(q1)`.  Therefore an
empty initial Greedy predicate does not imply a zero ceiling for stochastic
optimizers whose move closure includes gate-count-neutral swaps.

The audit also found an implementation defect in simulated annealing, random
local search, and the genetic algorithm: the exploration fitness (which
includes a cancellation-potential bonus) was reused to choose the returned
"best" circuit.  This could return a larger circuit than the input even when a
smaller fidelity-valid incumbent had already been visited.  The implementations
now track the smallest fidelity-valid incumbent separately; regression coverage
is in `tests/test_stochastic_incumbent.py`.

Consequences: Theorem 2(a), the restricted rewrite-system result 2(c), and
generator-specific empty-action claims survive.  General Theorem 2(b)/former
C1 does not.  Historical SA/RLS/GA outcomes produced before the incumbent fix
cannot be used as evidence for algorithm independence without rerunning the
affected experiment under the repaired code.

## Numbering map (manuscript ↔ formal_results.md)

| Manuscript | formal_results.md | History |
|---|---|---|
| Thm 1(a)/(b) | Observation 1 (formerly Theorem 1) | Renamed to Observation in the formal doc; manuscript keeps Theorem |
| Thm 2(a)-(d) | Theorem 2 + Appendix A (Thm 2c/2d) | Part (b) refuted by the three-gate SWAP+REMOVAL counterexample; 2(c) restricted; 2(d) open after proof invalidation |
| Lemma 3 | Lemma 3 (formerly Theorem 3) | Demoted |
| Lemma 4 | Lemma 4 (formerly Theorem 4) | Demoted |
| Thm 5 | Theorem 5 | |
| Thm 6 | Theorem 6 | |
| Thm 7 | Theorem 7 | |
| Thm 8 | Theorem 8 | |
| Thm 9 | Appendix B Theorem 9 | |
| Obs 1 (Table 19) | Empirical Observation 1 (formerly Proposition 2) | |
| Prop 1 | Proposition 1 [CORRECTED] | Max-matching version |
| C1/C2 | Conjectures 1/2 | |
| OP1/OP2 | Open Problems 1/2 | |

Rule going forward: any new formal result gets a status line and an entry in
both the formal_results.md summary table and this map.
