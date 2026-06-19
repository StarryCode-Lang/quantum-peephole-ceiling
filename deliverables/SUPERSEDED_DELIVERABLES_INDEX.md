# Superseded Deliverables Index — Q-Research

> **Note**: D1–D7 `.docx` files have been **removed from disk** during
> pre-publication cleanup (2026-06-19). This index is retained as an
> audit trail. Only D8 and D9 remain in this directory.

> **Status authority**: This index is the canonical status reference for all
> project deliverables (D1–D9). When a deliverable's `.docx` body conflicts
> with the status recorded here, **this index takes precedence**.
>
> **Last updated**: 2026-06-17
>
> **Why this index exists**: The `.docx` deliverables D1–D4 were written
> **before PHASE-7** and their body text still contains outdated claims
> ("Universal Predictive Law", Cohen's d effect sizes, 100% accuracy) that
> are **contradicted** by the PHASE-7/8 completion reports (D8/D9) and the v6
> manuscript. Because `.docx` is a binary format, the body text cannot be
> safely edited in place; this index provides the bypass protection instead.
> The latest manuscript evidence-scope caveats are: E19 planned/not run,
> E20 metadata-only, E21 smoke-only, E18 survivorship-biased, and Phase-2a
> canonical results are distinct from Phase-2b template-assisted theory/tests.
>
> **Note on prior protection**: An earlier audit expected per-deliverable
> `D*_SUPERSEDED_NOTICE.md` sidecar files in this directory. As of
> 2026-06-17 those sidecar files do **not** exist on disk. This unified
> index supersedes that planned approach and is the single source of truth
> for deliverable status.

---

## At-a-Glance Status Table

| ID | File | Status | Authoritative? |
|----|------|--------|----------------|
| D1 | `D1_Structural_Ceiling_Theory_Report.docx` | **SUPERSEDED** | No |
| D2 | `D2_Candidate_Mathematical_Models.docx` | **SUPERSEDED** (partial — see note) | No |
| D3 | `D3_Feature_Importance_Analysis.docx` | **SUPERSEDED** | No |
| D4 | `D4_Prediction_Framework.docx` | **SUPERSEDED** | No |
| D5 | `D5_Optimize_or_Skip_Framework.docx` | **SUPERSEDED** (pre-PHASE-7 recommendation) | No |
| D6 | `D6_New_Theorems_and_Conjectures.docx` | **SUPERSEDED** (pre-PHASE-7 framing) | No |
| D7 | `D7_Publication_Narrative_Recommendation.docx` | **SUPERSEDED** (pre-PHASE-7 narrative) | No |
| D8 | `D8_PHASE7_Completion_Report.docx` | **CURRENT** | Yes |
| D9 | `D9_PHASE8_Publication_Architecture.docx` | **CURRENT** | Yes |

> **Rule of thumb**: D1–D7 are pre-PHASE-7 artefacts. D8–D9 are the
> PHASE-7/8 completion reports and are the authoritative deliverables.
> For any current claim, cite D8/D9 and the v6 manuscript — never D1–D7.

---

## D1–D4: Detailed Supersession Record

These four deliverables are the primary concern because their bodies make
the strongest outdated claims.

### D1 — Structural Ceiling Theory Report
- **File**: `D1_Structural_Ceiling_Theory_Report.docx`
- **Status**: **SUPERSEDED**
- **Outdated claim in body**: "Universal Predictive Law" — the assertion
  that gate-reduction is governed by a universal, transferable predictive
  law across circuit families.
- **Why superseded**: Held-out (train/test) validation in PHASE-7 **failed**
  — the predictive law did not generalise. The claim is retracted in the
  v6 manuscript Limitations section.
- **Authoritative replacement**:
  - `docs/06_manuscript/v6_scope_limitations_risks.md` (Limitations)
  - `docs/06_manuscript/v6_claim_evidence_map.md` (claim → evidence status)
  - `deliverables/D8_PHASE7_Completion_Report.docx`

### D2 — Candidate Mathematical Models
- **File**: `D2_Candidate_Mathematical_Models.docx`
- **Status**: **SUPERSEDED (partial)**
- **Outdated content in body**: Catalogue of candidate mathematical models
  presented as candidate "laws", with the implication that one would be
  validated as the Universal Predictive Law.
- **Why superseded**: The model-selection exercise was conditional on the
  predictive law holding, which it did not under held-out validation.
  Individual models may still be useful as descriptive fits, but **none**
  is endorsed as a predictive law.
- **Authoritative replacement**:
  - `docs/06_manuscript/v6_manuscript.md` (theory, downgraded framing)
  - `docs/06_manuscript/v6_scope_limitations_risks.md`
  - `deliverables/D8_PHASE7_Completion_Report.docx`

### D3 — Feature Importance Analysis
- **File**: `D3_Feature_Importance_Analysis.docx`
- **Status**: **SUPERSEDED**
- **Outdated claims in body**:
  - Feature-importance rankings reported with **Cohen's d** effect sizes.
  - Implicit 100%-accuracy framing of the predictive model.
- **Why superseded**: (1) The effect-size methodology was updated after D3
  was written; Cohen's d values in D3 are not reproducible with the current
  pipeline. (2) Held-out validation failed, so the "100% accuracy" framing
  is invalid. Feature importance is retained only as **exploratory**.
- **Authoritative replacement**:
  - `docs/06_manuscript/v6_scope_limitations_risks.md`
  - `docs/06_manuscript/v6_claim_evidence_map.md`
  - `deliverables/D8_PHASE7_Completion_Report.docx`

### D4 — Prediction Framework
- **File**: `D4_Prediction_Framework.docx`
- **Status**: **SUPERSEDED**
- **Outdated claims in body**: A Prediction Framework presented as a
  validated, deployable tool for predicting gate reduction.
- **Why superseded**: Held-out validation results:
  - **MAE = 0.2775** (high error)
  - **Pearson r = NaN** (no linear correlation on held-out set)
  The Prediction Framework is therefore **downgraded to exploratory** and
  must not be presented as validated.
- **Authoritative replacement**:
  - `docs/06_manuscript/v6_scope_limitations_risks.md` (held-out failure)
  - `docs/06_manuscript/v6_claim_evidence_map.md`
  - `deliverables/D8_PHASE7_Completion_Report.docx` (PHASE-7 results)

---

## D5–D7: Pre-PHASE-7 Narrative Artefacts

D5–D7 are also pre-PHASE-7 and frame the project around the (now-retracted)
predictive-law narrative. They are superseded by the v6 manuscript and D8/D9.

- **D5** (`D5_Optimize_or_Skip_Framework.docx`): recommendation built on the
  predictive framework that failed held-out validation. **SUPERSEDED.**
- **D6** (`D6_New_Theorems_and_Conjectures.docx`): theorem/conjecture list
  from the pre-PHASE-7 framing. Several items were reframed during PHASE-7.
  **SUPERSEDED** — see v6 manuscript and D8 for current theorem status.
- **D7** (`D7_Publication_Narrative_Recommendation.docx`): publication
  narrative assumes the predictive-law story. **SUPERSEDED** — the v6
  manuscript uses the downgraded, held-out-honest narrative.

---

## D8–D9: Current Authoritative Deliverables

### D8 — PHASE-7 Completion Report
- **File**: `D8_PHASE7_Completion_Report.docx`
- **Status**: **CURRENT** — authoritative
- **Contents**: PHASE-7 completion record, including the held-out validation
  results (MAE=0.2775, Pearson=NaN) that retract the predictive-law claim.

### D9 — PHASE-8 Publication Architecture
- **File**: `D9_PHASE8_Publication_Architecture.docx`
- **Status**: **CURRENT** — authoritative
- **Contents**: PHASE-8 publication architecture and final manuscript plan,
  consistent with the v6 manuscript.

---

## Authoritative Sources for Current Claims

When in doubt, use these sources (in priority order):

1. `docs/06_manuscript/v6_manuscript.md`
2. `docs/06_manuscript/v6_claim_evidence_map.md` — claim → evidence status
3. `docs/06_manuscript/v6_scope_limitations_risks.md` — Limitations & Future Work
4. `deliverables/D8_PHASE7_Completion_Report.docx`
5. `deliverables/D9_PHASE8_Publication_Architecture.docx`

**Do not** cite D1–D7 for any current claim. If a D1–D7 body text conflicts
 with any source above, the source above is correct.
