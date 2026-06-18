# Reference Merge Log

**Date**: 2026-06-17  
**Operator**: Academic Editor (automated)  
**Action**: Merged two reference lists into a single authoritative list  

---

## 1. Background

The Q-research project maintained two parallel reference lists with inconsistent counts:

| File | Original Count | Role |
|------|:--------------:|------|
| `docs/02_literature/literature_review.md` | 42 | Narrative literature review (Section 9 references) |
| `docs/02_literature/unified_references.md` | 77 | Consolidated reference list (Version 1.0) |

An independent review identified missing foundational works in quantum circuit optimization. Additionally, `README.md` and `PRE_PAPER_CHECKLIST.md` cited inconsistent reference counts (42 vs. 77).

---

## 2. Merge Procedure

### Step 1: Cross-reference check (literature_review.md → unified_references.md)

All 42 entries in `literature_review.md` were verified against `unified_references.md` via the existing cross-reference map (Section N). **Result**: All 42 narrative-review references are already present in `unified_references.md`. No supplemental additions were required from the literature review.

### Step 2: Foundational literature audit

Six foundational works were checked against `unified_references.md`:

| Work | Status | Notes |
|------|--------|-------|
| Shende, Bullock, Markov (2006) — "Synthesis of Quantum Logic Circuits" | Already present as [35] | No action needed |
| Nam, Ross, Su, Maslov, Brayton (2018) — "Automated optimization of large quantum circuits with continuous parameters" | **MISSING** → added as [78] | Distinct from existing [17] (Nam, Niu, Maslov, QFT) and [18] (Nam, Chen, Roetteler, T-depth) |
| Yamashita, Nakanishi, Ishioka (2010) — "Merging quantum circuits" | **MISSING** → added as [79] | Distinct from existing [56] (Yamashita et al., equivalence checking, 2011) |
| Maslov (2017) — "Advantages of using relative-phase Toffoli gates" | Already present as [19] | Existing entry cites Maslov (2016) in PRA, vol. 93, 032305 — same work; user-supplied metadata (2017, PRL) appears to be a citation variant. No duplicate added. |
| Amy, Azimzadeh, Mosca (2018) — "On the controlled-NOT complexity of controlled-NOT–quantum circuits" | **MISSING** → added as [80] | Distinct from existing Amy entries [13], [14], [15], [20] |
| Patel, Shapira, Markov (2022) — "Quantum circuit optimization" (survey) | **MISSING** → added as [81] | Recent survey; no prior entry |

### Step 3: New reference placement

| New # | Section | Rationale |
|:------:|:--------|:----------|
| [78] | B. Quantum Circuit Optimization (Foundational) | Core circuit optimization work |
| [79] | B. Quantum Circuit Optimization (Foundational) | Foundational circuit-merging technique |
| [80] | B. Quantum Circuit Optimization (Foundational) | CNOT complexity bounds |
| [81] | L. Recent Advances in Quantum Circuit Optimization (2021-2026) | 2022 survey of the field |

---

## 3. Files Modified

| File | Change |
|------|--------|
| `docs/02_literature/unified_references.md` | Header updated with SINGLE AUTHORITATIVE statement; version 1.0 → 2.0; date → 2026-06-17; added [78]-[81] to Sections B and L; Section P summary table extended; footer version updated |
| `docs/02_literature/literature_review.md` | Added top-of-file note: narrative companion, not authoritative for citation count |
| `README.md` | Directory structure comment: "77 references" → "81 references, unified_references.md authoritative" |
| `PRE_PAPER_CHECKLIST.md` | Literature review entry: "42 references" → "42 narrative refs; see unified_references.md for authoritative list of 81 refs" |

---

## 4. Final Reference Count

| Metric | Value |
|--------|:-----:|
| Total entries in `unified_references.md` (authoritative) | **81** |
| Narrative references in `literature_review.md` | 42 (unchanged) |
| Newly added foundational works | 4 ([78], [79], [80], [81]) |
| Existing entries removed | 0 |
| Existing entries modified | 0 (content preserved) |

---

## 5. Consistency Verification

- `README.md` reference count: **81** ✓
- `PRE_PAPER_CHECKLIST.md` reference count: **81** ✓
- `unified_references.md` version: **2.0** (2026-06-17) ✓
- `literature_review.md`: marked as narrative companion ✓
- No existing entries deleted ✓
- Academic citation format consistent (Authors, Year, Title, Journal, Volume/Pages) ✓

---

## 6. Authoritative Source Declaration

`docs/02_literature/unified_references.md` (Version 2.0) is hereby designated the **SINGLE AUTHORITATIVE** reference list for the Q-research project. All manuscript citations must resolve to entries in this file. The `literature_review.md` file is retained as a narrative companion but is NOT authoritative for citation count.

---

*Log created: 2026-06-17*  
*Reference merge completed by: Academic Editor*
