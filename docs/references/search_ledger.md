# Search Ledger — Reproducible Literature Search & Citation Verification Record

> **Nature of this document**: This is a **retroactive reconstruction** of the
> literature search process for the Q-research manuscript. The underlying
> research and citation collection took place over multiple waves between
> 2026-05 and 2026-07; this ledger reconstructs and documents that process
> after the fact, and was executed on **2026-08-06** in response to the
> 2026-08-01 submission-readiness audit, which flagged the absence of a
> reproducible database search ledger as a submission-blocking gap.
>
> **Scope**: The ledger covers the 47 references cited in the manuscript
> (`docs/manuscript/manuscript.md`, references [1]–[47]), plus targeted
> cross-checks of entries in `unified_references.md` and
> `literature_review.md` that were involved in past citation incidents
> (Quartz, SSR, de Beaudrap).
>
> **Authority**: `unified_references.md` remains the single authoritative
> reference list for the manuscript. Where this ledger records a mismatch,
> the correction must be propagated there (see §7 for items still pending).

---

## 1. Databases and Tools

| Database / Tool | Role | Access method (2026-08-06 session) |
|---|---|---|
| arXiv (export.arxiv.org API) | Primary verification of arXiv IDs and titles | `https://export.arxiv.org/api/query?id_list=...` and `search_query=...` |
| Crossref API | DOI resolution (ACM, IOP, Royal Society) | `https://api.crossref.org/works/{doi}` |
| DataCite API | Zenodo DOI resolution (Qiskit) | `https://api.datacite.org/dois/{doi}` |
| Semantic Scholar API | Fallback title search (rate-limited during session) | `api.semanticscholar.org/graph/v1/paper/search` |
| Google web search (WebSearch) | Fallback for non-arXiv items (IEICE, ACM DL, IOP, DBLP records) | keyword queries, see §3 |
| DBLP | Classical CS reference verification (unreachable this session; used web search fallback) | — |

Verification method codes used in §5:
- **arXiv-API**: title/authors checked against arXiv API metadata for the cited ID.
- **DOI**: record resolved via Crossref/DataCite; title/venue/authors compared.
- **web**: title/venue confirmed via web search results (ACM DL / IOP / researchr / DBLP snippets).
- **canonical**: standard book/software reference; existence certain, no primary-source query run this session.

---

## 2. Search Queries by Topic (Reconstructed)

Queries correspond to the coverage of `literature_review.md`. Original search
history was not logged; the queries below are the reconstruction of the topic
coverage actually present in the corpus.

| Topic group | Queries (arXiv / Scholar / web) |
|---|---|
| Classical peephole & superoptimization | `peephole optimization` (McKeeman 1965); `peephole optimization intermediate code` (Tanenbaum 1982); `superoptimizer smallest program` (Massalin 1987) |
| Peephole optimization quantum | `peephole optimization quantum circuits`; `relaxed peephole optimization quantum` (Liu et al. CGO 2021) |
| Quantum compiler benchmark | `quantum circuit benchmark suite`; `MQT Bench`; `QASMBench`; `micro-benchmark NISQ circuit compilers` (Merilehto 2025) |
| Template matching quantum circuits | `template matching quantum circuits` (Maslov 2008); `pattern matching quantum circuit optimization` (Iten et al.); `Clifford circuit optimization templates symbolic Pauli gates` (Bravyi et al. 2021) |
| Phase polynomial / T-count / T-depth | `phase polynomial optimization quantum circuits`; `T-count optimization Reed-Muller` (Amy & Mosca); `T-depth matroid partitioning` (Amy et al. 2014); `meet-in-the-middle depth-optimal quantum circuits` (Amy et al. 2013); `Clifford+T exact synthesis` (Kliuchnikov et al.) |
| ZX calculus optimization | `ZX-calculus circuit simplification` (Duncan et al. 2020); `circuit extraction ZX-diagrams #P-hard` (de Beaudrap et al. ICALP 2022); `reinforcement learning ZX-calculus quantum circuit optimization` (Riu et al. 2025) |
| Equality saturation quantum | `equality saturation quantum circuit optimization` (Yang et al. PLDI 2026) |
| Circuit complexity / QMA-hard | `non-identity check QMA-complete` (Janzing et al. 2003); `local Hamiltonian QMA-complete` (Kempe et al.); `quantum circuit lower bounds geometric` (Nielsen 2005); `parameterized complexity` (Downey & Fellows) |
| Superoptimization / learned optimizers | `Quartz superoptimization quantum circuits`; `Quanto circuit identities`; `Quarl reinforcement learning quantum circuit optimizer`; `AlphaTensor quantum circuit optimization`; `verified optimizer quantum circuits` (VOQC); `swapping sweeping rewriting quantum circuit transformation` (SSR) |
| Compiler frameworks | `Qiskit`, `Cirq`, `t|ket> retargetable compiler NISQ` (Sivarajah et al. 2020) |
| Supporting: random circuits & entanglement | `random quantum circuits unitary designs` (Brandão et al.; Harrow & Low); `barren plateaus` (McClean et al.); `average entropy subsystem` (Page) |
| Supporting: quantum algorithms (manuscript §2) | `QAOA` (Farhi et al.); `variational eigenvalue solver` (Peruzzo et al.); `Grover`; `unitary coupled cluster ansatz` (Romero et al.); `ripple-carry addition circuit` (Cuccaro et al.); `surface codes` (Fowler et al.) |

---

## 3. Inclusion / Exclusion Criteria

**Included**:
- Quantum circuit optimization and compilation (peephole/template/commutation/
  phase-polynomial/ZX/equality-saturation/RL-based/verified optimization).
- Computational complexity of circuit optimization and identity testing
  (QMA-completeness, parameterized complexity).
- Quantum compiler frameworks and benchmark infrastructure.
- Supporting theory used by the manuscript (random circuits, entanglement,
  barren plateaus) and quantum algorithms whose circuits are studied.
- Publication window primarily **2018–2026**, plus foundational/classical
  works without time limit (McKeeman 1965, Massalin 1987, Barenco 1995,
  Shende et al. 2006, Garey & Johnson 1979-class complexity references, etc.).

**Excluded**:
- Quantum error correction hardware/fabrication topics not tied to circuit
  optimization (surface codes retained only as context for fault-tolerant
  gate-cost motivation).
- Pure variational-algorithm application papers with no compilation content.
- Non-archival sources (blog posts, vendor marketing) — except official
  software releases cited as tooling (Qiskit Zenodo, Cirq).
- Records that failed primary-source verification (see §5 mismatches and §6
  historical corrections — fabricated entries were removed rather than kept).

---

## 4. Verification Protocol

For each reference carrying an arXiv ID: fetch arXiv API metadata for the
cited ID and compare title and first author against the cited title.
For DOI-bearing entries: resolve via Crossref/DataCite and compare
title/venue/year. Entries without either are checked by targeted web search
or marked `canonical`. Any ID whose API record resolves to a **different
paper** is a `mismatch`; the correct record is located via title search and
recorded in the table.

---

## 5. Verification Status Table — Manuscript References [1]–[47]

Legend: ✅ verified · ⚠️ mismatch · ❓ unverified.

| # | Short title | arXiv ID / DOI | Method | Result |
|---|---|---|---|---|
| [1] | McKeeman — Peephole optimization (CACM 1965) | DOI 10.1145/364995.365000 | web (ACM DL) | ✅ verified |
| [2] | Tanenbaum et al. — Peephole opt. on intermediate code (TOPLAS 1982) | DOI 10.1145/357153.357155 | web (ACM DL) | ✅ verified |
| [3] | Massalin — Superoptimizer (ASPLOS 1987) | — | canonical | ✅ verified (canonical; no primary query this session) |
| [4] | Barenco et al. — Elementary gates for quantum computation | arXiv:quant-ph/9503016 | arXiv-API | ✅ verified |
| [5] | Nielsen & Chuang — QCQI (CUP 2010) | — | canonical | ✅ verified (canonical book) |
| [6] | Maslov et al. — Synthesis of reversible Toffoli networks (TODAES 2008) | — | web (researchr/Dueck pub list) | ✅ verified |
| [7] | Amy et al. — Meet-in-the-middle, depth-optimal synthesis (TCAD 2013) | cited arXiv:1206.07563 | arXiv-API | ⚠️ **mismatch**: 1206.07563 does not resolve; correct ID is **arXiv:1206.0758** (title/authors confirmed) |
| [8] | Kliuchnikov et al. — Asymptotically optimal approximation (PRL 2013) | arXiv:1212.0822 | arXiv-API | ✅ verified |
| [9] | Amy & Mosca — "Polynomial-time T-depth optimization … matroid partitioning," cited as IEEE TIT 65(10) 2019 | cited arXiv:1606.02729 | arXiv-API | ⚠️ **mismatch (conflated)**: arXiv:1606.02729 resolves to an unrelated astrophysics paper. The cited title belongs to Amy/Maslov/Mosca/Roetteler, **IEEE TCAD 33(10), 2014, arXiv:1303.2042**. Amy & Mosca IEEE TIT 65(8) 2019 is "T-count optimization and Reed-Muller codes," **arXiv:1601.07363**. Entry must be split/corrected. |
| [10] | Duncan et al. — Graph-theoretic simplification with ZX-calculus (Quantum 2020) | arXiv:1902.03178 | arXiv-API | ✅ verified |
| [11] | de Beaudrap, Kissinger, van de Wetering — Circuit extraction for ZX-diagrams can be #P-hard (ICALP 2022) | arXiv:2202.09194 | arXiv-API | ✅ verified (special-check item) |
| [12] | Janzing et al. — Non-identity check is QMA-complete (IJQI 2003) | cited arXiv:quant-ph/0306054 | arXiv-API | ⚠️ **mismatch**: quant-ph/0306054 resolves to "Spatial search by quantum walk" (Childs & Goldstone). Correct ID: **arXiv:quant-ph/0305050** ("Identity check is QMA-complete," Janzing) |
| [13] | Gottesman — Stabilizer codes and quantum error correction (PhD thesis 1997) | arXiv:quant-ph/9705052 | arXiv-API | ✅ verified |
| [14] | Aaronson & Gottesman — Improved simulation of stabilizer circuits (PRA 2004) | arXiv:quant-ph/0406196 | arXiv-API | ✅ verified |
| [15] | Dawson & Nielsen — The Solovay-Kitaev algorithm (QIC 2006) | arXiv:quant-ph/0505030 | arXiv-API | ✅ verified |
| [16] | Harrow & Montanaro — Quantum computational supremacy (Nature 2017) | arXiv:1809.07442 | arXiv-API | ✅ verified |
| [17] | Downey & Fellows — Fundamentals of Parameterized Complexity (Springer 2013) | — | canonical | ✅ verified (canonical book) |
| [18] | Nielsen — Geometric approach to quantum circuit lower bounds | arXiv:quant-ph/0502070 | arXiv-API | ✅ verified |
| [19] | Shende, Bullock, Markov — Synthesis of quantum-logic circuits (TCAD 2006) | arXiv:quant-ph/0406176 | arXiv-API | ✅ verified (note: first author is Vivek V. Shende) |
| [20] | Bernstein & Vazirani — Quantum complexity theory (SICOMP 1997) | DOI 10.1137/S0097539796300921 | web (DBLP/SIAM) | ✅ verified |
| [21] | Farhi et al. — QAOA | arXiv:1411.4028 | arXiv-API | ✅ verified |
| [22] | Peruzzo et al. — Variational eigenvalue solver (Nat. Commun. 2014) | arXiv:1304.3061 | arXiv-API | ✅ verified (arXiv title reads "…on a quantum processor"; published title adds "photonic") |
| [23] | Grover — Fast quantum mechanical algorithm for database search (STOC 1996) | arXiv:quant-ph/9605043 | arXiv-API | ✅ verified |
| [24] | Romero et al. — UCC ansatz strategies (QST 2019) | arXiv:1701.02691 | arXiv-API | ✅ verified |
| [25] | Cuccaro et al. — Quantum ripple-carry addition circuit | arXiv:quant-ph/0410184 | arXiv-API | ✅ verified |
| [26] | Shepherd & Bremner — Temporally unstructured quantum computation | cited Proc. R. Soc. A 475(2225), 2019, arXiv:1807.04084 | DOI + arXiv-API | ⚠️ **mismatch**: arXiv:1807.04084 resolves to an unrelated category-theory paper. Correct record: Proc. R. Soc. A **465**, 1413–1439, **2009**, DOI 10.1098/rspa.2008.0443; preprint **arXiv:0809.0847** ("Instantaneous Quantum Computation") |
| [27] | Qiskit (Zenodo 2024) | DOI 10.5281/zenodo.2562110 | DataCite | ✅ verified (concept DOI; version-year labeling acceptable) |
| [28] | Cirq (Google Quantum AI 2023) | — | canonical | ✅ verified (canonical software release) |
| [29] | Sivarajah et al. — t|ket> (QST 2020) | arXiv:2003.10611 | arXiv-API | ✅ verified |
| [30] | Fowler et al. — Surface codes (PRA 2012) | arXiv:1208.0928 | arXiv-API | ✅ verified |
| [31] | Brandão et al. — Local random circuits are approximate polynomial-designs (CMP 2016) | arXiv:1208.0692 | arXiv-API | ✅ verified |
| [32] | Yamashita & Markov — Fast equivalence-checking for quantum circuits (QIC 10(9–10) 2010) | DOI 10.26421/qic10.9-10-1; arXiv:0909.4119 | web (Rinton Press DOI page, fetched 2026-08-06) | ✅ **verified 2026-08-06**: confirmed as S. Yamashita & I. L. Markov, Quantum Information and Computation vol. 10, no. 9–10, pp. 721–734, 2010. The former IEICE E94-A(1) 2011 record was a venue conflation; manuscript [32] corrected |
| [33] | Iten et al. — Exact and practical pattern matching (ACM TQC 2022) | cited arXiv:1909.09119 | arXiv-API | ⚠️ **mismatch**: 1909.09119 resolves to "Efficient evaluation of quantum observables…" (Hamamura et al.). Correct ID: **arXiv:1909.05270** (TQC 3(1) 2022, DOI 10.1145/3498325 confirmed) |
| [34] | Xu et al. — Quartz: superoptimization of quantum circuits (PACMPL/PLDI 2022) | extended version arXiv:2204.09033 | arXiv-API | ✅ verified (special-check item; see §6 for prior ID incident) |
| [35] | Pointing et al. — Quanto (QST 2024) | DOI 10.1088/2058-9565/ad5b16 | web (IOP) | ✅ verified |
| [36] | Li et al. — Quarl (PACMPL/OOPSLA2 2024) | arXiv:2307.10120 | arXiv-API | ✅ verified |
| [37] | Ruiz et al. — AlphaTensor-Quantum (Nat. Mach. Intell. 2025) | arXiv:2402.14396 | arXiv-API | ✅ verified |
| [38] | Liu et al. — Relaxed peephole optimization (CGO 2021) | arXiv:2012.07711 | arXiv-API | ✅ verified |
| [39] | Riu et al. — ZX-calculus + RL (Quantum 2025) | arXiv:2312.11597 | arXiv-API | ✅ verified |
| [40] | Merilehto — 200-line micro-benchmark suite | arXiv:2509.16205 | arXiv-API | ✅ verified |
| [41] | Quetschlich et al. — MQT Bench (QST 2023) | arXiv:2204.13719 | arXiv-API | ✅ verified |
| [42] | Li et al. — QASMBench (ACM TQC) | arXiv:2005.13018 | arXiv-API | ✅ verified (note: journal volume 4(1) officially published 2023) |
| [43] | Nam et al. — Automated optimization with continuous parameters (npj QI 2018) | arXiv:1710.07345 | arXiv-API | ✅ verified |
| [44] | Bravyi et al. — Clifford circuit optimization with templates and symbolic Pauli gates (Quantum 2021) | arXiv:2105.02291 | arXiv-API | ✅ verified |
| [45] | Hietala et al. — VOQC (PACMPL/POPL 2021) | arXiv:1912.02250 | arXiv-API | ✅ verified |
| [46] | Yang et al. — Equality saturation for quantum circuit optimization (PACMPL/PLDI 2026) | DOI 10.1145/3808254 | Crossref | ✅ verified |
| [47] | Huang et al. — SSR (arXiv preprint 2025) | arXiv:2503.03227; DOI 10.1145/3828549 | arXiv-API + Crossref | ✅ verified — **published venue confirmed**: ACM TODAES, published online 2026-07-04 (see §5.1) |

### 5.1 SSR publication venue — resolved

Crossref resolution of DOI **10.1145/3828549** returns: "SSR: A
Swapping-Sweeping-and-Rewriting Optimizer for Quantum Circuit
Transformation," *ACM Transactions on Design Automation of Electronic
Systems*, published 2026-07-04, authors Huang, Zhou, Meng, Zhu, Luo, Du.
The arXiv preprint is 2503.03227 (2025, v4). **The authoritative publication
venue is TODAES 2026**; the earlier inconsistency (literature_review citing
TODAES 2026 vs. manuscript [47] citing only "arXiv 2025") is resolved in
favor of TODAES 2026. `literature_review.md` [45]/§10.10 has been annotated
accordingly (2026-08-06); manuscript [47] still reads arXiv-only and should
be updated at the next manuscript pass. Note that `unified_references.md`
currently has **no SSR entry** — this is a gap, not an authority to defer to.

---

## 6. Historical Correction Record

| Date | Wave | Correction |
|---|---|---|
| 2026-07 (wave 1) | removal | Two **fabricated citations** were identified and removed from the literature review corpus (recorded in review changelog; entries no longer present in any authoritative list) |
| 2026-07 (wave 1) | ID fix | Quartz arXiv ID corrected from **2205.00125** (an unrelated telecloning paper) to **2204.09033** (verified again in this ledger, §5 [34]) |
| 2026-07-21 (wave 2) | replacement | A cited "de Beaudrap, Glendinning & Zhang — faster resynthesis" entry that **does not exist** (its arXiv number resolved to an unrelated machine-learning paper) was replaced by the real ICALP 2022 extraction-hardness paper (arXiv:2202.09194) in `literature_review.md` |
| 2026-07-21 (wave 2) | venue fix | Kliuchnikov venue corrected (QIC 13(7–8), 607–630); ZX+RL Quantum page 1634→1758 |
| 2026-08-01 (wave 3) | scale resync | Study scale resynced to release-manifest total (then 73,000+ / 34 datasets) |
| 2026-08-06 (this ledger) | scale resync | Study scale resynced to **96,289 rows / 37 canonical datasets (E1–E30)** per `data/DATA_CANONICAL.md` v2.4.0 and `release/release_manifest.json`; `literature_review.md` updated |

---

## 7. Findings of This Verification Pass & Follow-Ups

**Statistics (manuscript [1]–[47])**: ✅ verified 42 · ⚠️ mismatch 5 (corrected in manuscript and propagated to the unified catalog on 2026-08-07) · ❓ unverified 0.

**Mismatches corrected in `unified_references.md` / manuscript:**

1. **[7] / unified [13]** Amy et al. meet-in-the-middle: arXiv ID **1206.07563 → 1206.0758**.
2. **[9]** Amy & Mosca entry was conflated; unified [14] retains the 2014 matroid-partitioning paper and unified [15] now uses **arXiv:1601.07363** for the 2019 Reed–Muller paper.
3. **[12] / unified [25]** Janzing et al.: arXiv ID **quant-ph/0306054 → quant-ph/0305050**.
4. **[26] / unified [45]** Shepherd & Bremner: corrected to Proc. R. Soc. A **465**, 1413–1439, **2009**, DOI 10.1098/rspa.2008.0443, arXiv:0809.0847.
5. **[33] / unified [61]** Iten et al.: arXiv ID **1909.09119 → 1909.05270**.

**Additional cross-checks on `unified_references.md`** (documented only; not part of manuscript [1]–[47]):

- **unified [22]** "de Beaudrap, Glendinning & Zhang — Faster resynthesis with the ZX-calculus, QPL 2022, arXiv:2206.10843": ⚠️ arXiv:2206.10843 resolves to an unrelated NeurIPS 2022 ML paper ("Learning Debiased Classifier with Biased Committee"), and no paper with the claimed title was located on arXiv or the open web. **Suspected same fabrication lineage as the wave-2 incident.** Recommend removing unified [22] or replacing with the verified ICALP 2022 extraction-hardness paper (arXiv:2202.09194), which the manuscript already cites as [11].
- **unified [20]** Amy, Glaudell, Ross (npj QI 2018): the incorrect arXiv:1606.02729 identifier was removed; the article remains catalogued without a preprint ID pending DOI-level primary-source confirmation.
- **unified cross-reference table O** now lists MQT Bench as Quetschlich, Burgholzer, and Wille.
- **unified catalog coverage**: Quasar is normalized to Yang, Raun, Tao, and Gu; SSR is now recorded as unified [89]. VOQC author-list variants remain a catalog-cleanup item; manuscript numbering is independent.

**Resolved 2026-08-06**: manuscript [32] Yamashita — verified against the Rinton Press DOI page as QIC 10(9–10) pp. 721–734 (2010), not IEICE; manuscript corrected. [3] Massalin remains canonical (not re-queried; low risk).

---

*Ledger executed: 2026-08-06. Tooling: arXiv export API, Crossref, DataCite,
web search. Raw API outputs were consumed in-session; queries are fully
specified above and in §2/§4 for re-execution.*
