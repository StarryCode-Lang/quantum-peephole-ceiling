# Pre-paper Theory Gate (2026-08-10)

## Purpose

This is a claim-control artifact, not manuscript prose.  A claim may enter a
future paper only if its status below is `admissible` and its stated scope is
preserved.  Existing manuscript text remains frozen during the pre-paper phase.

## Claim-status matrix

| Claim | Audit status | Admissible scope | Authoritative evidence / blocker |
|---|---|---|---|
| Expected adjacent-inverse density under the stated WCL random generator | admissible, corrected | First-moment expectation under the exact generator/gate alphabet only | `formal_results.md`, Observation 1(a); E30 direct validation |
| LBL makes the implemented adjacent Greedy action set empty for `n >= 2` | admissible | Property of the flat listing and rule predicate, not semantic incompressibility | `formal_results.md`, Observation 1(b); E1/E19 |
| Empty Greedy predicate implies zero Greedy reduction | admissible | Greedy only, including the stated rotation-merge clause | `formal_results.md`, Theorem 2(a) |
| Empty initial Greedy predicate implies zero reduction for every Phase-1 optimizer | **refuted** | none | `H(q0), X(q1), H(q0)`; `tests/test_stochastic_incumbent.py`; Theorem 2(b) audit |
| Greedy matches SA/RLS/GA up to `O(1/|C|)` | **withdrawn** | Historical E4 descriptive means only after explicit bug caveat | Counterexample; unspecified big-O constant; pre-fix incumbent selection |
| INSERTION+REMOVAL debt bound | admissible, restricted | Exact rewrite subsystem in Theorem 2(c); no SWAP/COMMUTATION inference | `formal_results.md`, Appendix A |
| INSERTION+SWAP+COMMUTATION global ceiling | **withdrawn/open** | none | Former Theorem 2(d) uses invalid per-wire factorization and does not identify the optimum |
| Concentration bound for random matching generator | **incomplete** | motivation only | Candidate Theorem 5 lacks the required dependent-exposure martingale |
| Zero Greedy reduction for the corrected non-empty-stage AG generator | admissible, restricted | That generator only; not general Aaronson--Gottesman canonical form | Proposition 6; v10 E23 160/160 exact rows; pre-fix `n=2, seed=35` counterexample |
| Constant Phase-2a advantage exists | admissible, family-specific | Artificial Theorem 7 construction and stated rules | Constructive proof; E24 |
| Haar incompressibility yields the claimed bounded-window reduction ceiling | **withdrawn** | none | Theorem 8 assumes an exact input circuit smaller than its own lower bound |
| All-ones BV has the constructed Phase-2b reduction `2n/(3n+2)` | admissible, model-specific | Stated BV listing, full-pipeline template set, and achieved reduction; `n+2` is not asserted globally optimal | Corrected Theorem 9; v10 E26 all-ones row for every `n=3..10` |
| Some families admit context-dependent `Omega(1)` Phase-2 advantage | admissible existence result | Existence only; no general classification | Theorems 7 and 9 |
| Frozen adjacent-pair conflict resolution is polynomial | admissible | Maximum compatible selection for a fixed candidate edge set; not sequential rewrite search | Corrected Proposition 1 |
| Standard Non-Identity / Non-Equivalence Check is QMA-complete | admissible external fact | Only the original promise, norm, phase quotient, thresholds, and orientation | Janzing--Wocjan--Beth original result |
| The project's A2 CIT schema is QMA-complete | **not established** | none until a full promise problem is stated | Missing complementary promise/gap; prior definition used matrix-level diamond norm |
| CODP is QMA-hard or in QMA | **open** | motivating question only | `r=0` is trivial; `r=1` reverses the standard Non-Identity promise; no size-gap reduction or verifier proof |
| General Clifford CODP is in P | **withdrawn** | Exact Clifford equivalence/simulation is in P; optimal synthesis is a separate problem | Gottesman--Knill does not imply minimum-cost synthesis |
| Fully bound unitary equivalence within the executable certificate scope | admissible, method-qualified | Fixed width; up to global phase; structural, Clifford, numerical-unitary, or explicitly sampled evidence only | `src/equivalence.py`; `tests/test_fidelity_estimator.py` |
| Free-parameter circuit equivalence | **not established / fail closed** | None without symbolic proof or a predeclared probability-qualified parameter-domain contract | Certificate returns `unavailable`; finite bindings are instances, not a symbolic proof |
| Measurement/reset/classical-control equivalence | **not established / fail closed** | None without an observational/channel semantics including classical outputs and initialization/discard policy | Certificate returns `unavailable`; unitary fidelity is inapplicable |

## Implementation defect and evidence disposition

Before 2026-08-10, simulated annealing, random local search, and the genetic
algorithm used cancellation-potential-augmented exploration fitness when
choosing the returned circuit.  They could therefore return a larger circuit
after visiting a smaller fidelity-valid circuit.  The repaired implementations
track the minimum-gate valid incumbent independently.

- Regression evidence: `tests/test_stochastic_incumbent.py`.
- Historical Greedy rows: unaffected.
- Historical SA/RLS/GA rows: descriptive only; barred from algorithm-ceiling
  claims until the relevant experiment is rerun under repaired code.
- E3/E14/E18/E23/E26 and the four-tool compiler grid must be interpreted by
  their actual optimizer/configuration; they are not retroactive evidence for
  the withdrawn stochastic theorem.

## Frozen-manuscript blockers

The current `docs/manuscript/manuscript.md` predates this gate and contains at
least the following barred statements.  They are deliberately not rewritten
during the pre-paper phase, but no future manuscript version may retain them:

1. “Corollary 2.1 (Universality of the Phase-1 Ceiling)” and equality of Greedy,
   RLS, SA, and GA.
2. Any use of E4 as confirmation of an optimizer-independent ceiling.
3. Any implication that standard CIT is a valid `r=0` or `r=1` reduction to
   CODP.
4. Any statement that Clifford semantic equivalence in P implies optimal
   Clifford circuit reduction in P.
5. Theorem 5, former Theorem 2(d), or Theorem 8 presented as proved.
6. General Aaronson--Gottesman, Haar-random, or production-compiler conclusions
   inferred from a restricted generator/listing/window theorem.
7. Any claim that finite parameter samples prove parameterized equivalence, or
   that unitary average gate fidelity validates measurement, reset, classical
   control, initialization/discard, or other channel semantics.

## Go / no-go decision

- **GO after statistical/release gates:** empirical representation sensitivity
  for the frozen Greedy/listing protocol; held-out structural diagnosis; fixed
  tool/version/configuration comparisons; scoped Phase-2 constructions.
- **NO-GO:** universal optimization law, algorithm-independent ceiling,
  general stochastic bound, QMA-hardness/completeness of CODP, general
  polynomial Clifford optimization, or unrestricted production-compiler
  superiority.

## Primary external anchors

- Janzing, Wocjan, and Beth, *Non-Identity Check Is QMA-Complete*,
  `arXiv:quant-ph/0305050` / IJQI (promise orientation and norm are essential).
- Peham et al., *Depth-Optimal Synthesis of Clifford Circuits with SAT Solvers*,
  `arXiv:2305.01674` (optimal Clifford synthesis is treated as a separate SAT
  problem, not a corollary of Gottesman--Knill).
- van de Wetering and Amy, *Optimising Quantum Circuits Is Generally Hard*,
  `arXiv:2310.05958` (cost metric and gate set determine hardness; no blanket
  inference from equivalence checking).
