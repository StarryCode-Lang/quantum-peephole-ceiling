# Theory Documents — Status Index

This directory holds the project's definitions, proofs, proof audits, and
withdrawn-result records. **Not every file here carries an admissible claim.**
Use this index to find the authority before citing anything.

Added 2026-10-16 (science_boost scan) because a reader arriving in
`docs/theory/` previously had to open every file to learn which results are
still live.

## Active

| Document | Role |
|---|---|
| `framework.md` | Central hub: definitions D1–D12, the Phase-1/Phase-2 architecture, complexity classification. **Conceptual framework only** — claim admissibility is controlled by the theory gate below. |
| `formal_results.md` | Authority for every theorem, lemma, proposition, conjecture, and proof appendix. |
| `prepaper_theory_gate_2026-08-10.md` | **Controls claim admissibility.** Conflicts between documents are resolved in favour of this file. |
| `proof_audit_2026-08-06.md` | Proof-status audit record. |
| `v12_rewrite_exposure_theory.md` | Active but bounded: status `conjecture_or_draft_until_e38`. Defines the claim boundary for the v12 representation-robust rewrite-exposure method. |
| `exposability_criterion_2026-10-23.md` | **Active, new 2026-10-23.** Theorem 1: a cancellable pair is reachable by commutation alone iff every intervening gate is independent of both; the crossing distance is the required horizon. Backed by E56 (128/128 certificate replay) and E57. |
| `closure_termination_and_optimality_2026-10-24.md` | **Active, new 2026-10-24.** Lemmas 1-2 (span locality, disjoint spans do not interfere); Thm 2 (a single closure pass is an interval-scheduling problem, greedy by right endpoint is optimal); Cor. 1 (the shipped distance-order key has no optimality proof, with a three-interval counterexample); Thm 3 (termination in <= m0/2 passes, O(m0^2 w)); **Thm 4 (fixpoint certificate: an empty exposable set means no commutation sequence of any length can expose another cancellation)**. Backed by E56/E58/E59/E61. |
| `thm10_horizon_vs_closure_2026-10-22.md` | Superseded in form by Theorem 1 above, but retained: it records the correction from "industry-wide gap" to "bounded horizon vs closure". |
| `thm5_concentration_repair_2026-10-17.md` | Repair note: Thm 5-A/5-B valid, 5-C proposed (Chen–Stein). Priority lowered 2026-10-23 — the closure result does not need concentration. |

## Withdrawn, superseded, or historical — do not cite

| Document | Status | Why it is retained |
|---|---|---|
| `QMA_hardness_draft.md` | **Withdrawn as a proof** (v1.1, 2026-08-09) | Record of an unsuccessful route toward Open Problem OP1. Three fatal defects are documented in its own header. |
| `phase2_lower_bound_strengthening.md` | **Superseded 2026-08-11** | Failed reasoning route (it mixed pattern-matching runtime with gate count through "equivalent gate-slots"). The corrected authority is Theorem 9 in `formal_results.md`. |
| `universal_law_assessment.md` | **Superseded** | Answers whether any formal result rises to a universal law. Its verdict — that the results are representation-conditioned, not universal — is now reflected in `framework.md`'s honest framing note and in the manuscript's scope qualifications. |
| `nontrivial_upgrades.md` | **Historical brainstorming** | Explicitly "not a theorem-status source" in its own header. Any proposal in it that treats Thm 5/6/8/2d as established must be re-derived. |

## Note on `archive/`

`archive/` exists but is intentionally empty. Two of the superseded documents
above (`QMA_hardness_draft.md`, `universal_law_assessment.md`) are **path-bound
in `release/prepaper_release_manifest.json`** — their file paths are part of the
pinned release chain (see `scripts/generate_prepaper_release_manifest.py`).
Moving them would invalidate the manifest, so they stay in place and their
status is recorded here instead. The same reasoning applies to the other two
superseded notes: keeping the set together in one directory is more useful than
splitting it.

## Current admissible claim set (as of 2026-10-11)

Surviving results, per `framework.md` §"Cross-Reference Map" and the
2026-08-09 audit correction:

- **Obs 1(a)** — WCL adjacent-inverse density (birthday-paradox grade, U-trivial)
- **Obs 1(b)** — LBL structural emptiness (definitional, representation-conditioned)
- **Thm 1(a)** — adjacent-inverse-pair density under WCL; constants corrected
  2026-08-06 and validated by E30 (27 cells, max |z| = 2.86, median |rel err| 1.4%)
- **Thm 1(b)** — LBL yields an empty Phase-1 action space for $n \ge 2$
- **Thm 2(a)** — Greedy no-action predicate (narrow)
- **Thm 2(c)** — bounded INSERTION cascade lemma (restricted)
- **Lemma 3/4** — commutation preservation; greedy optimality for non-conflicting
  pairs
- **Thm 7** — explicit Phase-2a advantage (constructive, artificial family)
- **Thm 9** — Phase-2b BV-oracle construction achieving $2n/(3n+2)$; **no global
  optimality claim**
- **Prop 1** — Phase-1 conflict resolution is polynomial-time (maximum matching)

Withdrawn or incomplete: **Thm 5** (proof incomplete), **Thm 6** general
(refuted, $n=2$ seed 35), **Thm 8** (withdrawn, incompatible premises),
**Thm 2(d)** (invalid per-wire factorisation), **QMA-hardness of CODP**
(withdrawn), **Conj. C1** (refuted), **Obs 1** generalisation (withdrawn).
