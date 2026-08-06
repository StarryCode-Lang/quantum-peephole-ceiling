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
| Thm 2(a)-(d) | formal_results.md §1 + Appendix A | SOUND | 2c/2d insertion-debt and wire-order invariants check out |
| Lemma 3 / Lemma 4 | formal_results.md §1 | SOUND | Trivial supporting lemmas |
| Thm 5 | formal_results.md §1 | SOUND (constants loose) | See detailed notes below |
| Thm 6 | formal_results.md §1 | SOUND; VALIDATED (E23) | 160 circuits, matching rate 1.0 |
| Thm 7 | formal_results.md §1 | SOUND | Constructive; note: bound carried by Phase-2a (E24: phase2b alone 2.5%) |
| Thm 8(a)-(c) | formal_results.md §1 | SOUND (asymptotic counting argument) | See detailed notes below |
| Thm 9 | formal_results.md Appendix B | SOUND; VALIDATED (E26) | 80/80 exact k+2 optimum |
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

McDiarmid application is structurally correct. Two looseness items recorded
(they affect constants, not the qualitative bound):

1. **Independence idealization.** The proof models $N = n(d-1)$ independent
   gate-position choices. Under the exact layer model with random-pairing
   two-qubit gates, choices on paired wires are correlated; the correct
   independent variables are the $\approx (n/2)(d-1)$ pair choices plus the
   one-qubit draws.
2. **Bounded-differences constant.** $c_i = 2$ holds for per-wire-position
   variables (each gate participates in at most two adjacent pairs on its
   wire). For pair-level variables, changing one pair choice touches up to
   four wire adjacencies, so $c_i = 4$ there. The exponent therefore shifts
   by at most a constant factor; the high-probability conclusion
   $X \leq \mathbb{E}[X] + \sqrt{O(N \ln(1/\delta))}$ stands.

Empirical status: under LBL, $X = 0$ identically, so E1/E3 satisfy the bound
trivially (manuscript Table 19: "MATCH (trivial)").

## Thm 8: detailed notes

1. **Step 1 (dimension counting)** is the standard parameter-counting
   argument (Nielsen 2005; Harrow–Montanaro 2017). The volume-ratio
   expression in the document is heuristic; the conclusion
   $\Pr[\mathcal{C}(U) < 4^n/n^2] \leq \exp(-\Omega(4^n/n))$ is the accepted
   asymptotic form. No gap beyond the cited literature's own assumptions
   (finite gate set, Haar measure on $SU(2^n)$).
2. **Steps 2–3** follow directly from Step 1; the clamp at $R_{\max} = 0$
   when $4^n/(n^3 d) > 1$ is stated explicitly.
3. **Part (c)** is trivially true for any circuit (bounded-window algebra);
   the document itself labels it so.
4. **Regime disclosure is correct**: no canonical experiment reaches the Haar
   regime ($d \ll 4^n/n^2$ at tested $n$), so Thm 8 remains PARTIAL on the
   cross-validation scorecard. This is a limitation of experimental scope,
   not a proof defect; the manuscript discloses it (Limitation 4).

## Numbering map (manuscript ↔ formal_results.md)

| Manuscript | formal_results.md | History |
|---|---|---|
| Thm 1(a)/(b) | Observation 1 (formerly Theorem 1) | Renamed to Observation in the formal doc; manuscript keeps Theorem |
| Thm 2(a)-(d) | Theorem 2 + Appendix A (Thm 2c/2d) | |
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
