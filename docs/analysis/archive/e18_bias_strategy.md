# E18 Survivorship-Bias Handling Strategy

> **Author:** E18 Data-Quality Repair Agent
> **Date:** 2026-07-17
> **Companion analysis:** `docs/analysis/e18_failure_analysis.md`
> **Constraint:** original 270-row dataset must be preserved; all corrections carry an audit trail.

---

## 0. Decision Context

The failure analysis establishes that the 120/270 (44.4%) missing rows are **systematic but MAR** — fully explained by two observable covariates (`circuit_family` ≈ gate-set type; `n_qubits` ≈ width threshold). This rules out two naïve options:

- **Silent filtering (status quo)** — drops the 120 rows, computes survivor-subset statistics. *Directionally biased upward*; survivors are the easiest circuits. This is the defect reviewers will attack.
- **Listwise re-running everything** — infeasible: the 78 decompose-error rows fail by construction (no exact Clifford+T rule exists for continuous rotations); re-running yields the same `TranspilerError`. Only the 42 fidelity-zero rows are *rerunnable* if the fidelity budget is lifted.

The missingness is **heterogeneous**, so no single technique fits all 120 rows. We split the cohort into the two mechanisms and assign each the technique its data-generating process justifies.

| Failed cohort | n | Mechanism | Defining covariate | Imputable? |
|---|---|---|---|---|
| Width-failed (`fidelity = 0`) | 42 | MAR by width | `n_qubits ≥ 12`, within surviving family | **Yes** — Clifford+T circuit exists; only verification failed |
| Gate-type-failed (`decompose_error`) | 78 | "MNAR-by-principle" | continuous-gate family | **No scalar** — no Clifford+T circuit exists to optimize |

---

## 1. Strategy A — Multiple Imputation (MI)

**Applies to:** the 42 width-failed rows.

**Rationale.** Each width-failed row has a known `circuit_family` and `optimizer`. Within that (family × optimizer) cell, the 150 valid rows provide an empirical conditional distribution of `reduction`. Because missingness is MAR on `n_qubits` and `n_qubits` is independent of within-family reduction (families are generated at fixed seeds, not size-stratified on reduction), the conditional distribution `P(reduction | family, optimizer)` estimated on valid rows is a valid imputation model for the missing rows under MAR.

**Procedure.**

1. For each failed row `i` with covariates `(family_f, optimizer_o)`:
2. Let `S_{f,o}` = valid reductions in the same cell (count ≥ 3 for all 42 rows; see failure analysis §4.2 distribution).
3. Draw `m = 50` imputations from a **posterior-predictive** distribution:
   - parametric option: `Beta(α̂, β̂)` fit to `S_{f,o}` by method of moments (reductions are in [0,1]);
   - non-parametric option (preferred for small cells): bootstrap-mean + empirical bootstrap of `S_{f,o}` to propagate within-cell uncertainty.
4. Each imputed dataset yields a cell mean and an overall ITT mean; pool across the 50 imputations by **Rubin's rules** (within-imputation variance + between-imputation variance) to produce a single estimate with 95% CI.
5. Record every draw in an audit column (`imputed_draw_id`) so the imputation is fully reproducible and reversible.

**Why it is honest.** MI does not invent favourable numbers: it propagates the *observed* within-cell variability, so the imputed rows are no more optimistic than the genuine survivors in the same family. It also yields a CI that widens to reflect real uncertainty — the opposite of the survivor subset's false precision.

**Limitation.** Assumes the within-family reduction distribution is width-invariant. Plausible here because the survivor subset already mixes widths 3–11 within each family with no visible width trend in `reduction`; we test this assumption in the correction script (Levene's test of `reduction` across width terciles within each surviving family).

---

## 2. Strategy B — Survival / Right-Censoring Analysis

**Applies to:** the 78 gate-type-failed rows (primary framing), and optionally to the 42 width-failed rows (secondary).

**Rationale.** A decompose-error row is not "missing a reduction"; it is a circuit for which the Clifford+T optimization pipeline **never reached the measurement stage**. This is the textbook definition of **right-censoring**: the event of interest (a non-zero reduction) cannot be observed because the conversion died first. Framing it as survival analysis lets us report a **Kaplan–Meier-style convertibility curve** and a censoring-adjusted mean reduction without pretending the failed circuits were optimizable.

**Procedure.**

1. Define the "event" as `reduction > 0` (a successful, measurable optimization outcome).
2. "Time" is the pipeline stage index: 0 = baseline attempted, 1 = decomposed, 2 = optimized, 3 = fidelity-verified.
   - Valid rows: event observed at stage 3.
   - Width-failed (42): censored at stage 2 (optimized but unverified).
   - Gate-type-failed (78): censored at stage 0 (never decomposed).
3. Report the Kaplan–Meier estimate of the **convertibility probability** `P(decomposable)` and `P(optimizable-and-verifiable)`, plus a log-rank test across circuit-family groups.
4. For the mean reduction, report the **censoring-robust estimate** = E[reduction | event observed] × P(event) — i.e. the ITT mean that assigns 0 to censored cases — with a Turnbull-style confidence interval.

**Why it is honest.** It does not impute a reduction for circuits that have no Clifford+T form; it quantifies how far down the pipeline each cohort got and reports the *convertibility* of the population as a first-class result. This directly answers the reviewer's question "how generalizable is this?" with a probability, not a caveat.

**Limitation.** Survival framing is descriptive, not corrective — it bounds but does not fill the missing cells. We therefore pair it with MI (for the 42) and sensitivity bounds (for the 78).

---

## 3. Strategy C — Sensitivity Analysis (Best / Worst Case Bounds)

**Applies to:** the 78 gate-type-failed rows (mandatory), and as a robustness check on the MI for the 42.

**Rationale.** Because no scalar reduction is imputable for the 78 rows, we instead bound the population ITT mean under two extreme, transparent assumptions about what those rows *would* have yielded had they converted:

- **Best case (optimistic upper bound):** the 78 rows reduce at the **survivor-subset mean** for their would-be optimizer. This is the most favourable reading and equals the current (biased) survivor statistic generalized to the full cohort.
- **Worst case (conservative lower bound):** the 78 rows reduce at **0%** — i.e. Clifford+T conversion is treated as a treatment failure and the optimization contributes nothing. This is the strict ITT reading.

The true population ITT mean lies between these bounds; the **width** of the interval quantifies how much the survivor bias could be moving the headline number.

**Procedure.**

1. Let `μ_S` = mean reduction on the 150 valid rows; `n_V = 150`, `n_F78 = 78`, `n_F42 = 42`.
2. Lower bound (ITT-0): `μ_L = (Σ valid + Σ imputed_42 + 0·78) / 270`.
3. Upper bound (ITT-max): `μ_U = (Σ valid + Σ imputed_42 + μ_S·78) / 270`.
4. Primary estimate (ITT-MI): `μ̂ = (Σ valid + Σ imputed_42 + 0·78) / 270` — i.e. MI fills the 42, the 78 stay at 0 by the strict-ITT convention. Report `μ̂` with Rubin CI plus the `[μ_L, μ_U]` bracket.

**Why it is honest.** Reviewers cannot claim the result was cherry-picked: the manuscript states the full admissible interval and lets the reader judge. If the qualitative conclusion (e.g. "Phase 1 > Phase 2 on survivors") survives even at `μ_L`, the claim is bias-robust; if it flips between `μ_L` and `μ_U`, the manuscript says so explicitly.

---

## 4. Strategy D — Selective Re-run

**Applies to:** the 42 width-failed rows only.

**Rationale.** These rows failed purely because `max_qubits_fidelity = 10` was too small. Re-running with `max_qubits_fidelity` raised (e.g. to 22, the max width in the dataset) would compute the real fidelity for all 42 rows, turning them into observed (not imputed) data. This is strictly better than MI because it replaces assumption with measurement.

**Feasibility check (Windows, 16 GB RAM, no GPU).** State-vector fidelity is O(4^n) in memory and time. The widest failed row is `n_qubits = 21` → 2²¹ amplitudes ≈ 4.2 M complex doubles ≈ 67 MB per state; two states (input + optimized) ≈ 134 MB; well within 16 GB. The 16- and 15-qubit rows are ≈ 4 MB and 1 MB respectively. The cost is CPU time, not memory: a full unitary for 21 qubits is feasible but slow (seconds-to-minutes per row). On 16 GB / no-GPU this is **borderline-feasible** for the 42 rows as a one-off, but not as a recurring experiment.

**Recommendation.** Implement Strategy D as the *gold-standard validation* path inside the fidelity-verification module (`e18_fidelity_verification.py`): a `--rerun-fidelity` mode that recomputes `average_gate_fidelity` for the 42 rows with an enlarged budget, plus a cheaper **state-vector sampling / unitary-distance proxy** for the very widest rows (see fidelity module). Use the re-run results, where available, in place of the MI imputations; fall back to MI for any row that still times out. This makes the 42-row correction measurement-based wherever physics allows, assumption-based only as a last resort.

**Not applicable to the 78.** Re-running decompose-error rows without a Solovay–Kitaev pass reproduces the same `TranspilerError`. A true fix requires implementing SK approximation (future work, README limitation L5) — out of scope for this data-quality pass.

---

## 5. Recommended Composite Strategy

No single strategy is sufficient; the missingness is dual-mechanism. We adopt a **composite**, chosen so that every claim is backed by the weakest assumption compatible with the data:

| Cohort | n | Primary treatment | Rationale |
|---|---|---|---|
| Valid | 150 | Observed (no change) | — |
| Width-failed | 42 | **Strategy D** (re-run fidelity) where feasible; **Strategy A** (MI) as fallback | turns assumption into measurement; MI valid under MAR |
| Gate-type-failed | 78 | **Strategy C** (sensitivity bounds) + **Strategy B** (survival framing) | no scalar imputable; bounds + convertibility probability |
| **All 270** | 270 | **ITT analysis** reporting `μ̂` (MI-filled 42 + 0-filled 78) with `[μ_L, μ_U]` bracket | preserves full cohort; honest about uncertainty |

### Primary headline statistic (ITT)

$$\hat{\mu}_{\text{ITT}} = \frac{1}{270}\Big(\sum_{i \in V} r_i + \sum_{j \in F_{42}} \tilde{r}_j + \sum_{k \in F_{78}} 0\Big), \quad \text{CI via Rubin's rules; bracket } [\mu_L, \mu_U].$$

where `V` = 150 valid, `F_42` = 42 width-failed (MI-filled), `F_78` = 78 gate-type-failed (0 by strict-ITT).

### What changes vs. the status quo

- The survivor subset is **demoted** from "the result" to "the conditional-on-convertibility estimate", reported alongside the ITT mean and the convertibility probability.
- The 44.4% failure is **not hidden**: it is reported as a first-class convertibility curve (Strategy B) and as the width of the sensitivity bracket (Strategy C).
- All 270 rows remain in the analysis with an explicit `correction_method` audit column (`observed` / `imputed_MI` / `rerun_fidelity` / `itt_zero`). No original row is deleted.

---

## 6. Statistical-Reporting Checklist (for the revised section)

1. Little's MCAR test statistic + p-value (failure analysis §5.1).
2. χ² tests of failure × family and failure × width (failure analysis §5.2).
3. Convertibility probability P(decomposable) and P(verifiable) with Kaplan–Meier CI (Strategy B).
4. ITT mean `μ̂_ITT` with Rubin CI and the `[μ_L, μ_U]` sensitivity bracket (Strategies A + C).
5. MAR assumption check: Levene's test of `reduction` across width terciles within each surviving family (Strategy A limitation).
6. Per-optimizer ITT table, not just pooled.
7. Explicit statement that survivor-subset statistics are an **upper bound**, with the lower bound given by strict-ITT.

This composite satisfies the reviewer's data-quality objection (no silent filtering, full cohort retained, missingness mechanism tested and reported) while remaining computable on the stated Windows/16 GB/no-GPU environment.
