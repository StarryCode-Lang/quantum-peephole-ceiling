# Manuscript correction patch — 2026-10-22

**Status:** proposal only. `docs/manuscript/` is read-only for this workflow, so nothing
below has been applied. Each item gives the current text, the replacement, and the
experiment that forces the change. Apply with the owner's normal edit pass.

**Why this is not "writing the paper":** all three items are statements the project's own
evidence packages now contradict. Leaving them in place is a self-refutation risk, not a
stylistic issue.

---

## C1 — "3 families at genuine structural ceiling"

**Current (Abstract, Results):**

> 3 families at genuine structural ceiling (QFT, GHZ, SurfaceCode; no tested compiler
> reduces them), 5 at prototype action-space ceiling where t|ket> achieves 6–64%, …

**Problem:** the parenthetical is falsified by the project's own packages.

| Family | Counter-evidence |
|---|---|
| QFT | E48: PyZX `full_reduce` 34→31 and 148→127, equivalence verified. E53: BQSKit 34/148 (tie). |
| SurfaceCode | E48: `surface_code_8` 10→8 by PyZX. E53: BQSKit 8/8 exactly ties. |
| GHZ | Survives: E48 4 optimizers + E53 BQSKit, n=4…20, 0 violations, 17/17 exactly n. |

**Replacement:**

> 1 family at a genuine structural ceiling under 1-/2-qubit gate sets (GHZ; 5 independent
> optimizers across n = 4…20, zero violations), 1 family whose ceiling survives every
> tested *rewrite* engine but not ZX reduction (SurfaceCode: 7/8 intact, 1 source broken by
> PyZX), and QFT at a library-relative rather than structural ceiling.

**Also required in the theorem statement:** `GHZ_n >= n` holds for (circuit, 1-/2-qubit gate
set). Under a programmable all-to-all multiqubit entangling gate any Clifford sequence costs
<= 4 applications (`2510.20730`), so GHZ_n is 1–2 gates there. State the premise or the
theorem is refuted in review.

---

## C2 — "no prior study has, to our knowledge"

**Current (Introduction §1.1):**

> … yet no prior study has, to our knowledge, systematically characterized *when* these
> passes succeed, *why* they sometimes fail entirely, or what representation-conditional
> limits constrain achievable reductions.

**Problem:** at least five independent 2026 papers argue the same proposition.

| arXiv | Claim |
|---|---|
| `2609.29406` | Pass order in Qiskit determines achievable reduction — the dual coordinate of this project's listing phenomenon. |
| `2609.29210` | Representation-dependent recoverability, with an entropy lower bound. |
| `2610.06142` | Equivalent circuits lose synthesis choices (360/360 conditions). |
| `2601.19738` | Q-PreSyn: local edits are representation-conditioned. |
| `2609.35239` | Complexity of Clifford template compilation. |

**Replacement:**

> Representation-conditioned compiler capability has been established independently in 2026
> by pass-order, recoverability, synthesis-choice, local-edit, and template-complexity
> studies [refs]. What is not established is a *certified* finite-horizon landscape that
> separates an order barrier from a content barrier, nor a statement of which barrier is
> independent of search budget. That is the contribution here.

---

## C3 — percentages without denominators

**Current (Abstract, Results):**

> … exactly **0.0000%** gate reduction across **25,000** random circuits (E1); under
> wire-consecutive listing (WCL), the same circuits yield **7.83%** mean reduction …

**Problem:** E49 (2026-10-21) shows the panel denominator is a *normalised* listing, not the
input circuit. Median reduction is 0.224% vs the frozen baseline and −11.31% vs the source
circuit; 59 of 96 real sources have a certified output larger than their input. A reader who
assumes the denominator is the input circuit will conclude the optimizer inflates circuits.

**Replacement (keep the number, name the denominator):**

> … exactly **0.0000%** reduction in the same normalised `{h, x, rz, cx}` listing across
> 25,000 random circuits (E1); under wire-consecutive listing the same circuits yield
> **7.83%** mean reduction **within that listing** (E19). These are listing-relative
> quantities: measured against the original source circuits the median is −11.31%, because
> normalisation expands 10 of 15 families by 1.0–9.4×.

---

## C4 — escape counts (new, from E52/E54)

**Current:** the abstract and §6.12 report "63 exact escapes / 65 exact local optima" over
128 sources.

**Problem:** E52 shows 50 of the 128 roots bypass greedy optimisation
(`MAX_BASELINE_GATES = 80`), and 49 of the 63 escapes are depth-1 escapes on those
un-optimised baselines. E54 removes the bypass and re-runs the panel.

**Replacement:** use the E54 numbers. Two-layer reporting:

> Of 128 panel sources, N retain a certified improvement after uniform greedy re-baselining
> (`docs/review/science_boost/2026-10-22_d2_rebaseline/`). The previously reported 63
> includes 49 depth-1 escapes that measure an un-optimised baseline, not landscape
> structure; they are reported separately as a baseline-construction artefact.

Fill `N` from `summary.json:part_e_full_panel.escape_count`.

---

## C5 — "certified optimum" wording (new, from E53)

**Current:** §6.12 and the abstract describe `best_cost` as the certified optimum.

**Problem:** E53 shows BQSKit beats `best_cost` on 12 of the 14 genuine escapes (median 12.5
gates, max 22), while the two-qubit count improves on only 5 of 14.

**Replacement:**

> `best_cost` is the optimum **within the declared rule library** (`e44_core_v1`) at the
> declared horizon. It is not a global optimum: numerical resynthesis reduces total gate
> count on 12 of 14 genuine escape cells (median 12.5 gates) while leaving the two-qubit
> count unchanged on 9 of them, i.e. the library already reaches the entangling structure
> but not the single-qubit normal form.

---

## Application checklist

- [ ] C1 abstract + theorem statement (premise)
- [ ] C2 introduction novelty paragraph
- [ ] C3 abstract + §6.2 denominators
- [ ] C4 abstract + §6.12 counts (needs E54 `N`)
- [ ] C5 §6.12 wording + a two-column table (total gates / two-qubit)
- [ ] Re-run `python scripts/verify_prepaper_release_manifest.py` after the edit and
      register any new drift in `docs/review/release_drift_register.json`
