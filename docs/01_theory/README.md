# Theory Index

> **Version**: 5.3.0 (Thm 1 split into 1a/1b, Thm 3/4 → Lemma 3/4)  
> **Date**: 2026-06-13

This directory contains the theoretical framework for the QIP manuscript.

## Documents

| Document | Content | Key Items |
|----------|---------|-----------|
| `framework.md` | Central hub: definitions, architecture, cross-references, scope framing | D1–D10 (10 core definitions) |
| `conjectures.md` | Formal conjectures + motivating open problems | C1–C2 (conjectures), OP1–OP2 (open problems) |
| `lemmas.md` | Theorems, propositions, and empirical observations | Thm 1–8 (proven), Prop 1 (corrected), Obs 1 (empirical) |
| `complexity.md` | Complexity classification table | CIT, CODP, P1OPT, P12OPT |

## v5.3.0 Changes (from v5.2.0)

- **Split** Theorem 1 into 1(a) wire-consecutive listing model (original formula) and 1(b) layer-by-layer listing model (proves $\mathcal{S}_1(C) = \emptyset$ for $n \ge 2$). This resolves the mismatch between Theorem 1's predictions and the E1 zero-std observation.
- **Downgraded** Theorems 3 and 4 to Lemma 3 and Lemma 4. Thm 3 (1-line proof) and Thm 4 (extremely narrow scope) are more appropriately classified as supporting lemmas.
- **Updated** cross-reference map and summary tables across all documents.

## v5.2.0 Changes (from v5.1.0)

- **Demoted** Prop 2 to Empirical Observation 1: the proof sketch was not rigorous. The observation (Greedy matches stochastic optimizers) is empirically well-supported but lacks a formal proof.
- **Added** honest assessment of theorem depth to `lemmas.md` summary table: only Thm 2 and Thm 8ab are substantive; Thm 1/3/4/8c are elementary/trivial.
- **Added** critical caveat to `framework.md`: Thm 8 applies to Haar-random *unitaries*, not the random *gate sequences* used in experiments.
- **Added** INSERTION cascade gap disclosure to Thm 2 remark: the claim that "cancellations involving only pre-existing gates could have been found without INSERTION" is asserted without proof.
- **Updated** cross-references from "Prop 2" to "Obs 1" across all documents.

## v5.1.0 Changes (from v5.0.0)

- **Corrected** Proposition 1: Phase-1 conflict resolution is polynomial-time solvable (maximum matching), not NP-complete as previously claimed.
- **Renamed** Theorem 6 to "Phase-1 Ceiling is Exact for Clifford Circuits in Aaronson--Gottesman Canonical Form" with an added remark about general (non-canonical) Clifford circuits.
- **Added** "Scope and Nature of the Framework" section to `framework.md` with honest framing about the combinatorial/algebraic (rather than physical) nature of the structural ceiling analysis.

## v5.0.0 Changes (from v4.0.0)

- **Added** Theorems 5–8
- **Updated** Conjecture C1/C2 status
- **Streamlined** all cross-references across documents
