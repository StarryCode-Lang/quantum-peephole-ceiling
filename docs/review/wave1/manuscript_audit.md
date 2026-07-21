# Manuscript Audit — Wave 1 (Narrative & Pitfall Compliance)

> **Role**: 审稿人_Review (Manuscript Narrative & Pitfall Compliance, read-only audit)
> **Date**: 2026-07-20
> **Objects**: `docs/manuscript/manuscript.md` (v7, 792 lines), `docs/manuscript/appendix.md` (582), `docs/supplementary/supplementary_materials.md` (801), `docs/manuscript/claim_evidence_table.csv` (14 claims), `docs/results/analysis_summary.md` (457), `docs/manuscript/_cross_validation.md`, `docs/manuscript/_e18_extension.md`, `docs/manuscript/sections/{contribution5_revised,e18_revised,sota_comparison_tables}.md`, `README.md` (171)
> **Framework**: peer-review four dimensions — Originality / Methodology / Results / Writing — with Major/Minor grading.
> **Data verification**: headline numbers spot-checked against canonical CSVs with pandas (`data/v6/e19`, `data/v6/e21`, `data/v7/e23`, `data/v7/e24`); all verified numbers match the manuscript exactly (details in §8).

---

## Executive Verdict

**Overall: Major Revision.** The v7 restructure is narratively coherent, the core claims are data-backed, and pitfall compliance is largely achieved — but the manuscript is not yet submittable: it is 34–44% below its own target length, contains **zero figures**, lacks a structured abstract and explicit falsifiable hypotheses, and its central taxonomy (the trichotomy classification) is stated **inconsistently across three locations**. Several "pending merge" fragments contain *newer, better* analyses (LOFO CV, E18 ITT, SOTA tables) than what the manuscript currently presents.

| Dimension | Grade | Summary |
|---|---|---|
| Originality | Strong (no Major) | Columnar representation sensitivity + listing-model formalization is a genuine, well-differentiated contribution. |
| Methodology | Major ×2 | No falsifiable hypotheses/decision rules; "predictive model" wording contradicts the paper's own post-hoc caveat and HGC failure. |
| Results | Major ×3 | Trichotomy class membership internally inconsistent (IQP/UCCSD/Adder/Grover/QuantumWalk); family roster differs between §2.6 and §6.3; "7 prototype-limited" over-counts vs own E20 table (5 supported). |
| Writing | Major ×3 | No structured abstract; zero figure references (18 PDFs orphaned); dangling "Table 11"; condensed cross-validation replaces the full 12/3/1 scorecard; reference numbering non-contiguous. |

---

## 1. IMRaD Structure Check (Task 1)

**Length**: 792 lines vs self-declared target 1200–1400 (`manuscript.md:3`). Shortfall: **408–608 lines (−34% to −44%)**.

IMRaD backbone is present: Introduction (§1, lines 17–77), Methods (§5, lines 330–384), Results (§6, lines 388–582), Discussion (§7, lines 586–662), plus Conclusion (§8), Declarations, References. Section map verified via header scan.

**Missing / incomplete elements:**

| # | Missing element | Evidence | Severity |
|---|---|---|---|
| M1 | Structured abstract (Background/Methods/Results/Conclusions) | Abstract is a single narrative paragraph (`manuscript.md:13`) | **Major** — see §2 for rewrite |
| M2 | Explicit falsifiable hypotheses H1/H2/… with decision rules | Only RQ1–RQ3 (lines 43–51) and Conjectures C1/C2 (lines 314, 324); grep for `H1|H2|decision rule|falsifiable` → no hits | **Major** — see §3 |
| M3 | Figures: zero `Fig./Figure` references, zero floats | grep `Fig(ure)?\.?\s*\d+|includegraphics|\.pdf|\.png` → **no matches in 792 lines**; 18 PDFs in `analysis/figures/` uncited | **Major** — see §7 |
| M4 | Numbered tables with captions | All body tables unnumbered; one dangling v6-era pointer: "Circuit-family optimization prescriptions (**Table 11**…)" (`manuscript.md:473`) | **Major** |
| M5 | Full theory-experiment cross-validation scorecard (12 MATCH / 3 PARTIAL / 1 MISMATCH) | Only an 8-row condensed table in §6.6 (lines 556–569); full 16-row table + scorecard live in `docs/results/analysis_summary.md:297–325` | **Major** — see §4 |
| M6 | Formal statement of Theorem 6 | Referenced (lines 61, 324) but never stated; theorem numbering jumps 2 → 7 (Thm 3/4/5/6 absent from body) | Minor |
| M7 | Formal statements of Lemma 3 / Lemma 4 / Prop 1 / Thm 5 / Obs 1 | Lemma 3 invoked at line 342 without statement; the rest exist only in `analysis_summary.md` | Minor |
| M8 | E18 ITT (intention-to-treat) analysis | Revised fragment `sections/e18_revised.md` (156 lines, ITT mean 0.1351 [0.102, 0.169], Little's MCAR p = 1.6×10⁻¹²) marked "Not yet integrated"; manuscript §6.7 still reports survivor-only framing | **Major** (Results) |
| M9 | LOFO cross-validation of the ceiling-aware predictive model | `sections/contribution5_revised.md:66–89` (MAE = 0.0980, Pearson = −0.0147, recommends "confirmed negative result") not integrated; manuscript still cites the older 5-family HGC (MAE = 0.2775, Pearson = NaN) at lines 73, 554, 632 | **Major** (Methodology) |
| M10 | SOTA comparison tables | `sections/sota_comparison_tables.md` (4 tools × 15 families, generated 2026-07-19) not integrated; §2.7 related-work claim ("none of the existing frameworks provides…", line 153) lacks a comparison table | Minor |
| M11 | Keywords / PACS | Absent | Minor |
| M12 | Experiment registry completeness | "23 registered experiments (E1–E25)" (line 362) but table lists 17; E6–E9, E11, E13, E22, E25 absent (E6 noted at line 644; E25 exists per `README.md:90`) | Minor |
| M13 | Author names, affiliations, acknowledgments | Placeholders (lines 9, 692, 698) — acceptable pre-submission | Minor |

**Path to 1200+ lines** (for the integration worker): structured abstract (~15) + hypotheses/decision rules (~30) + 8–10 figure floats with captions (~100) + full 16-row cross-validation (~30) + E18 ITT subsection (~60) + LOFO CV rewrite of §6.5 (~60) + SOTA table (~30) + Thm 6/Lemma statements (~40) + expanded related work (~50) ≈ **+415 lines** → ~1210.

---

## 2. Abstract Audit (Task 2)

**Status**: NOT structured. Single narrative paragraph (`manuscript.md:13`). Content is accurate and pitfall-compliant (trichotomy counts match line 425; HGC not mentioned — acceptable for abstract length), but target venues (PRA allows unstructured; *Quantum*/ACM TQC reviewers increasingly expect structure, and the project's own QA bar demands it).

**Proposed structured rewrite** (drop-in, ~230 words; all numbers already verified against canonical data):

> **Background.** Peephole optimization — local rewriting of bounded gate sequences — is a core pass in every quantum compiler, yet no systematic study has characterized when these passes succeed, why they fail, or how the circuit's data-structural representation constrains them.
> **Methods.** We benchmark 6 optimizer types across 15 circuit families (67,000+ data rows, 27 datasets, experiments E1–E25), prove listing-model ceiling theorems, and validate theory against experiment including production compilers (Qiskit 2.4.1, Cirq 1.6.1, t|ket> 2.18.0).
> **Results.** We identify *columnar representation example sensitivity*: under layer-by-layer listing (LBL), the Phase-1 action space is provably empty for n ≥ 2 (Theorem 1(b)) — exactly 0.0000% gate reduction across 25,000 random circuits (E1); under wire-consecutive listing (WCL), the same circuits yield 7.83% mean reduction (E19, 10,000 rows, fidelity = 1.0). Across 15 families a categorical trichotomy emerges: 100% reduction (CNOT chains), 14–16% via commutation (oracle/Clifford), and ~0% on the remainder — 3 families at genuine structural ceiling confirmed by all compilers, 5 at prototype action-space ceiling where t|ket> achieves 5–63%, the rest unresolved. A ceiling-aware pipeline skips futile passes with bit-identical output (1.6×–228× speedup on training families); its predictive model fails held-out generalization and is reported as a negative result.
> **Conclusions.** Peephole optimization behavior is representation-dependent: the "optimization desert" is a property of the (circuit, listing) pair, not the circuits. Wire-traversal preprocessing and family-aware pass routing are concrete, implementable compiler-design consequences.

Note: the rewrite uses the **corrected** class counts (3 genuine / 5 prototype-limited / rest unresolved) per §6 below — if the integration worker keeps "3 + 7", the abstract and line 425 must instead be reconciled the other way.

---

## 3. Falsifiable Hypotheses & Decision Rules (Task 3)

**Status: ABSENT — Major (Methodology).**

The Introduction motivates via RQ1–RQ3 (lines 47–51) but never converts them into falsifiable hypotheses with pre-registered decision rules. What exists instead: Theorems (proven, not falsifiable), Conjectures C1/C2 (stated with evidence, lines 314/324, but no rejection criteria), and a post-hoc chronology note (line 264: theory was "developed to explain observed experimental patterns, not to make a priori predictions… descriptive rather than predictive"). That note is commendably honest — but it makes the absence of *any* forward-looking falsifiable statement more conspicuous to a reviewer.

**Required addition** (suggested content for the integration worker; each hypothesis maps to existing data, so no new experiments are needed):

| Hypothesis | Statement | Decision rule | Data |
|---|---|---|---|
| H1 | Under LBL, Phase-1 reduction = 0 for all families with n ≥ 2 | Rejected if any LBL trial yields reduction > 0 | E1–E5, E14 (0/45,500+) |
| H2 | WCL preprocessing yields strictly positive mean Phase-1 reduction on random Universal circuits | Rejected if WCL mean ≤ 0 or CI includes 0 | E19 (7.83% ± 3.95%) |
| H3 | Phase-2 commutation advantage Γ(C) > 0 iff the family contains commutation-accessible inverse pairs | Rejected if a family with no commutation path shows Γ > 0 | E10/E14/E16 (Oracle/Clifford > 0; QFT/GHZ/brickwork = 0) |
| H4 | The trichotomy is categorical, not gradual: inter-family reduction levels cluster at {100%, 14–28%, ~0%} | Rejected if ≥3 families show intermediate levels (e.g., 40–80%) | E14/E15 (currently supported) |
| H5 | Ceiling-aware skipping is output-neutral | Rejected if any skipped-run output differs in gate count | E21 (1,140 rows, 100% identical — verified §8) |

Placement: new §1.4 "Hypotheses and decision rules" (current Contributions becomes §1.5), cross-referenced from each Results subsection.

---

## 4. Theory-Experiment Cross-Validation Table (Task 4)

**Status: PARTIALLY PRESENT — Major (Results/Writing).**

- The **full** table — 16 rows with verdicts **12 MATCH / 3 PARTIAL MATCH / 1 MISMATCH / 0 UNTESTED** — exists only in `docs/results/analysis_summary.md:297–325` (scorecard at lines 318–325).
- The manuscript §6.6 (lines 556–569) carries an **8-row condensed** version with a different verdict vocabulary (Consistent ×6 / Exceeds bound ×1 / Partially validated ×1). The 12/3/1 scorecard and the MISMATCH row (Thm 1a, WCL-vs-LBL model mismatch — pedagogically the *most instructive* row) are absent from the manuscript.
- `docs/manuscript/_cross_validation.md` is byte-equivalent to §6.6 yet still carries the header "Not yet integrated into main manuscript. Pending merge." — stale status flag.

**Additional wording defect**: §6.6 closes with "This quantitative agreement across 8 independent observables **validates the framework as a predictive model** for peephole optimization behavior" (line 569). This contradicts (i) the paper's own methodological note ("descriptive rather than predictive", line 264) and (ii) the HGC held-out failure (lines 554, 632). Must be reworded, e.g., "…is quantitatively consistent with the framework's post-dictions across 8 independent observables."

**Action**: import the 16-row table + scorecard into §6.6 (or a float), keep the condensed table as a summary, fix line 569 wording, and clear the stale status header in `_cross_validation.md`.

---

## 5. Limitations Subsection Count vs README (Task 5)

**Status: README POINTER STALE — Minor (Writing), plus content gaps.**

- `README.md:109`: "Full details in `docs/manuscript/manuscript.md` **Section 6.3 (13 subsections)**."
- Reality: manuscript limitations live in **§7.4** (lines 620–644) with **12** numbered items; §6.3 is the trichotomy *results* section. The standalone chapter (`appendix.md` §C, lines 364–476) has **14** items. Three different counts/pointers: README 13 @ §6.3, manuscript 12 @ §7.4, appendix 14.

**Coverage matrix** (appendix §C item → manuscript §7.4 item):

| Appendix §C (14) | Manuscript §7.4 (12) | Status |
|---|---|---|
| §1 Held-out validation failed | #6 HGC | ✓ covered |
| §2 Phase-2a vs Phase-2b gap | — | ✗ **missing as a limitation item** (partially hedged in Thm 9 proof sketch, line 310) |
| §3 Listing-conditional ceiling | #2 WCL validation scope | ✓ |
| §4 Theorem 8 scope | #4 | ✓ |
| §5 Theorem 6 unverified | — | ✓ correctly absent (closed by E23) — appendix text itself is stale here |
| §6 Multi-compiler Qiskit-only | — | ✓ correctly absent (closed by E20) — appendix stale |
| §7 E19 partially completed | #2 | ✓ |
| §8 E18 survivorship bias | #5, #12 | ✓ |
| §9 Under-powered experiments | #10 | ✓ |
| §10 `_gates_commute` conservative lower bound | — | ✗ **missing** (only "sufficient but not necessary" at line 340; not framed as limitation) |
| §11 Noiseless ideal environment | — | ✗ **missing** (future work 7.5.5 mentions noise-aware extension but §7.4 never lists noiselessness as a limitation) |
| §12 Pass isolation 5/15 families | — | ✗ **missing** (§6.4 reports 5-family isolation without flagging the 10-family gap) |
| §13 Raster figures | — | obsolete in repo (18 vector PDFs exist) but see M3 — manuscript has no figures at all |
| §14 E4 single seed | #7 | ✓ |
| (not in appendix) | #8 missing families, #9 no shuffler control, #11 stat-method consistency, #12 gate-set sensitivity | manuscript-only additions — good |

**Actions**: (a) fix README pointer → "Section 7.4 (12 items)" or sync after integration; (b) add the four missing limitation items (§2, §10, §11, §12) to §7.4 → would bring it to 16 items; (c) refresh stale appendix §5/§6 statements during appendix integration.

---

## 6. Pitfall Compliance (Task 6) — itemized with file:line

| # | Pitfall requirement | Verdict | Evidence |
|---|---|---|---|
| P1 | No "Greedy dominates SA/GA" overclaim | ✅ COMPLIANT | grep `dominat` → only `manuscript.md:525` "(dominated by CNOT chain)"; E4 table honestly reports SA = −1.5467% (line 404); conclusion is convergence, not dominance (line 407) |
| P2 | Ceiling wording = "prototype action-space ceiling" | ✅ COMPLIANT (with one violation, P8) | lines 153, 256, 425, 596, 598, 604 all use the qualified phrase; genuine ceilings always carry "confirmed by all (production) compilers" (lines 425, 517) |
| P3 | Ceiling-aware model labeled exploratory + HGC (MAE = 0.2775, Pearson = NaN) | ✅ COMPLIANT | Contribution 3 header "with acknowledged limitations" (line 69); "exploratory observation rather than a validated predictive tool" (line 73); §6.5 "Critical limitation (HGC)… exploratory observation" (line 554); §7.4 #6 (line 632). Note: superseding LOFO analysis pending integration (M9) |
| P4 | E18 carries "(survivorship-biased; 44.4% failure rate)" | ✅ COMPLIANT | §6.7 first mention: "Survivorship-biased: 120/270 rows (44.4%) failed" (line 575); §7.4 #5 (line 630); §7.4 #12 (line 644). Registry row (line 377) unannotated — acceptable for a registry table |
| P5 | E04 single-seed acknowledged (or updated via E29) | ✅ COMPLIANT (acknowledged; E29 rerun data now exists — see Addendum B) | §7.4 #7 (line 634). **Correction to an earlier draft of this cell**: E29 *does* exist in the working tree — `data/v7/e29/e29_multi_seed_e04_full.csv` (800 rows, 10 seeds, completed 2026-07-19, metadata present) — but is referenced nowhere in the manuscript, README, or `docs/results/`. The manuscript-level acknowledgment remains the operative compliance fact; E29 integration is pending |
| P6 | Absence of random gate shuffler control acknowledged | ✅ COMPLIANT (acknowledged; E28 control data exists, uncurated — see Addendum B) | §7.4 #9 (line 638). A gate-shuffle ablation (E28, 2,240 rows, full mode, 8 families, listing variants original/wcl/shuffle_0–4, run 2026-07-18) exists but is currently orphaned under `_agent_work/orphan_outputs/` and referenced nowhere in docs |
| P7 | Phase-2b labeled "fixture-scale" | ✅ COMPLIANT | "implemented with fixture-scale validation (`Phase2bTemplateMatcher`, unit-tested, E10 Phase-2b validation data: 1,017 rows); full canonical-scale Phase-2b benchmarking remains future work" (line 310) |
| P8 | No global-optimality overclaim | ❌ **VIOLATION (Minor)** | line 517: "These circuits are **genuinely gate-count-optimal**." 0% across all *tested* compilers does not prove gate-count optimality (global, all-algorithm claim). Fix: "no tested compiler — including t|ket>'s FullPeepholeOptimise — achieves any reduction on these families." |
| P9 | No "predictive model" self-contradiction | ❌ **VIOLATION (Major)** | line 569: "validates the framework **as a predictive model**…" — contradicts line 264 ("descriptive rather than predictive") and HGC (lines 554, 632). Fix per §4 |
| P10 | No unsupported numeric extrapolation | ❌ **VIOLATION (Minor)** | line 616: for VQE/QAOA/HardwareEfficient workloads "the expected speedup **exceeds 10×**" — its own §6.5 table shows ~9×/~8× for these families (lines 548–549; confirmed by `sections/contribution5_revised.md:33–36`: VQE 9×, QAOA 8×, HardwareEfficient 8×). Fix: "exceeds 8×" or cite the family-wise table |
| P11 | Production-compiler internals claims hedged | ⚠️ BORDERLINE (Minor) | line 254: "**No existing production compiler** (Qiskit, Cirq, or t|ket>) applies this transformation as an explicit pre-pass" — stated as fact while the audit is deferred to future work (line 652). Fix: "To our knowledge / based on public documentation, no production compiler applies…" |

---

## 7. Figure Reference ↔ PDF Mapping (Task 7)

**Manuscript body figure references: ZERO.** grep for `Fig.|Figure \d|includegraphics|.pdf|.png` over all 792 lines → no matches. Consequently there are **no dangling references and no missing PDFs** — the gap is unidirectional: 18 publication-ready vector PDFs exist and none is cited.

Mapping table (claim-evidence-table figure pointers → PDF assets → manuscript status):

| Referenced as (in `claim_evidence_table.csv`) | PDF asset | Exists? | Cited in manuscript? |
|---|---|---|---|
| Fig.1 (C1) | `analysis/figures/fig01_phase_transition.pdf` | ✓ | ✗ |
| Fig.4 (C2) | `analysis/figures/fig04_phase1_vs_phase2.pdf` | ✓ | ✗ |
| Fig.12 (C3) | `analysis/figures/fig12_multi_compiler_comparison.pdf` | ✓ | ✗ |
| Fig.13 (C2, C4) | `analysis/figures/fig13_window_scaling_curves.pdf` | ✓ | ✗ |
| Fig.14 (C5) | `analysis/figures/fig14_connectivity_ceiling.pdf` | ✓ | ✗ |
| Fig.17 (C3) | `analysis/figures/fig17_qiskit_pass_interaction.pdf` | ✓ | ✗ |
| — (uncited by CSV) | fig02_scaling, fig03_algorithm_comparison, fig05_threshold_sensitivity, fig06_fidelity_distribution, fig07_landscape, fig08_fdr_correction, fig08b_real_circuit_optimizer_comparison, fig09_compiler_baseline_comparison, fig10_structural_ceiling_gap, fig11_extended_benchmark_heatmap, fig15_qiskit_pass_waterfall, fig16_qiskit_pass_family_heatmap | ✓ all 12 | ✗ |

**Missing PDFs for any referenced figure: NONE.** Recommended float set for integration (8–10): fig01 (§6.1), fig08b or fig04 (§6.3), fig11 (§6.3), fig12 (§6.4), fig13 (§6.3/E16), fig15–fig17 (§6.4 pass analysis), fig10 (§6.3/§7.1), plus a new WCL-vs-LBL schematic for §3 (no existing PDF covers the E19 flagship — flag to the figures worker if out of my scope).

Also fix the stale note in `appendix.md` §C-13 (lines 462–468) claiming figures are raster PNG — vector PDFs now exist; the limitation has shifted from "raster" to "not included".

---

## 8. Claim-Evidence Mapping: README Six Key Findings (Task 8)

`claim_evidence_table.csv` holds 14 rows (C1–C12, Thm6, Thm7), header "**STATUS: Not yet integrated**…" (line 1), and its `Manuscript_Location` column uses **v6 numbering** (Section 3/5.1/5.3/Fig.1/Table 1…) that does not match v7 (§3 = representation, §4 = theory, §5 = methods, §6 = results) — must be remapped during integration.

README Key Findings (`README.md:15–21`) → evidence → verification:

| KF | Claim | Mapped claims / data | Verdict |
|---|---|---|---|
| 1 | Listing Model Sensitivity (LBL empties S₁; WCL ~7.8%, E19 10,000 rows) | C9; `data/v6/e19/e19_wcl_listing_full_e19_full_20260620_123825.csv` | ✅ **Supported, numerically verified**: pandas → LBL n=5000 mean 0.0000/std 0.0000/max 0.0000/fid 1.0000; WCL n=5000 mean 7.8285/std 3.9516/max 33.3333/fid 1.0000 — matches manuscript (7.83/3.95/33.33/1.0) exactly |
| 2 | Empirical Trichotomy (100% CNOT; 14–16% oracle/Clifford; 3 genuine + 7 prototype ceilings) | C1 (E1–E5, E14), C2 (E10, E14, E16, E24); CSVs present | ⚠️ **Data supported; manuscript presentation inconsistent** — see R1–R4 below |
| 3 | Prototype vs Production: t|ket> 5–63% on **5 of 7** ceiling families | C3/C11; `data/v6/e20/multi_compiler_full.csv` | ✅ Supported for 5 (E20 table lines 504–508: VQE 39.6, HW-eff 35.8, IQP 63.4, UCCSD 22.5, QAOA 5.4); **but README's "5 of 7" contradicts manuscript's "7 are prototype-limited"** (lines 13, 425) → R3 |
| 4 | Theory-Experiment Validation (8 observables; Thm 9 partial, fixture-scale) | C12, Thm6, Thm7; `data/v7/e23` (160 rows, reduction 0.0 everywhere — verified), `data/v7/e24` | ✅ **Verified**: E24 phase2a mean 79.7997% (manuscript 79.80%, range 62.5–89.3 vs CSV 62.5–89.2857 ✓); phase2b 2.5% fixture-scale ✓; E23 0.000% ✓. Full 16-row scorecard missing from body (§4) |
| 5 | Ceiling-Aware exploratory (1.6×–228×, mean 35×, identical reduction; HGC MAE=0.2775 Pearson=NaN) | C10; `data/v6/e21/ceiling_aware_comparison.csv` (1,140 rows) | ✅ **Verified**: naive vs ceiling_aware gate_reduction identical in 100% of 570 paired trials; mean 9.63% both — matches line 538. HGC caveat properly carried (P3). LOFO update pending (M9) |
| 6 | Fidelity verified; E18 survivorship-biased 44.4% failure | C7, C6; `data/v5/e18/` (6 CSVs incl. ITT artifacts) | ✅ Supported and annotated (P4); ITT upgrade pending integration (M8) |

**Unsupported / over-stated claims found (must fix):**

| ID | Location | Claim | Problem |
|---|---|---|---|
| U1 | `manuscript.md:517` | QFT/GHZ/SurfaceCode "genuinely gate-count-optimal" | Global optimality is unprovable from tested compilers (= P8) |
| U2 | `manuscript.md:616` | "expected speedup exceeds 10×" on VQE/QAOA/HardwareEfficient workloads | Own table: 8–9× (= P10) |
| U3 | `manuscript.md:569` | "validates the framework as a predictive model" | Contradicts HGC + line 264 (= P9) |
| U4 | `manuscript.md:254` | "No existing production compiler applies this transformation as an explicit pre-pass" | Unverified internals claim; audit deferred (= P11) |
| U5 | `manuscript.md:13` (abstract) & `:425` | "7 are prototype-limited" | E20 data support 5 (see R3); README says "5 of 7" |

**Results-dimension internal inconsistencies (the audit's most important findings):**

- **R1 — IQP/UCCSD double-classified.** §6.3 line 423 places IQP (~5.6%) and UCCSD (~4.2%) in **Class II** (commutation-enabled); line 425 places both in **Class III** (7 prototype-limited). The E15 table (lines 448–449) labels them "II". Class counts then sum to 1 + 5 + 10 = 16 ≠ 15.
- **R2 — Family roster mismatch.** §2.6's 15-family table (lines 127–141) contains Universal, Clifford, Structured but **no UCCSD, no HaarRandom**; the §6.3 E15 table (lines 444–458) contains UCCSD and HaarRandom but **no Universal, no Structured**. The "15 families" roster differs between sections.
- **R3 — Adder/QuantumWalk/Grover class drift.** Line 425 counts Adder + QuantumWalk among the 7 prototype-limited; the E15 table labels Adder "III (genuine)" (line 456) and QuantumWalk "III (unclear)" (line 457); the E20 table labels Adder "Genuine ceiling" (line 503), QuantumWalk "Unclear" (line 510), and **Grover "Unclear"** (line 509) — while lines 423/447 call Grover Class II. Defensible synthesis from E20 data: 3 genuine (QFT, GHZ, SurfaceCode) + Adder likely genuine + 5 prototype-limited (VQE, HardwareEfficient, IQP, UCCSD, QAOA) + 2 unclear (Grover, QuantumWalk). The "3 + 7" formula survives nowhere except line 425/abstract.
- **R4 — Qiskit blow-up magnitudes differ across tables** (Grover: −819.4% line 447 vs −881.8% line 509 vs −500.5 pooled in `sections/sota_comparison_tables.md:22`; QuantumWalk: −2794.7% vs −2526% vs −1904.7%). Different experiments/aggregations (E15 vs E20 vs pooled), so not necessarily errors — but each table must state its dataset (only line 460 does) or a reviewer will treat them as inconsistencies.

---

## 9. Prioritized Revision List (Task 9)

Sorted by priority. Dimensions: O=Originality, M=Methodology, R=Results, W=Writing. All locations in `docs/manuscript/manuscript.md` unless noted.

| Pri | Dim | Level | Action | Location |
|---|---|---|---|---|
| 1 | R | **Major** | Fix trichotomy class membership to one consistent taxonomy everywhere (suggested: 3 genuine + Adder genuine + 5 prototype-limited + 2 unclear; or justify "3+7" with explicit criteria); reconcile abstract, line 423, line 425, E15 table (448–449, 456–457), E20 table (503–510) | lines 13, 419–460, 493–513 |
| 2 | W | **Major** | Replace narrative abstract with structured Background/Methods/Results/Conclusions abstract (drop-in text in §2 of this audit) | line 13 |
| 3 | M | **Major** | Add §1.4 "Hypotheses and decision rules" — H1–H5 with pre-registered rejection criteria (suggested set in §3 of this audit) | after line 51 |
| 4 | W | **Major** | Insert 8–10 figure floats from `analysis/figures/` (mapping in §7); number all body tables; repair dangling "Table 11" reference | line 473 + all Results subsections |
| 5 | R | **Major** | Import full 16-row cross-validation table + 12/3/1 scorecard into §6.6; reword line 569 ("predictive model" → post-diction consistency); clear stale "pending merge" header in `_cross_validation.md` | lines 556–569 |
| 6 | M | **Major** | Integrate LOFO CV rewrite of ceiling-aware section (`sections/contribution5_revised.md`): downgrade predictive model from "exploratory" to "confirmed negative result" (MAE 0.0980, Pearson −0.0147), keep rule-driven CeilingAwareOptimizer as engineering contribution | §6.5, lines 534–554; §7.4 #6 |
| 7 | R | **Major** | Integrate E18 ITT analysis (`sections/e18_revised.md`): ITT mean 0.1351 [0.102, 0.169], per-cohort treatment, convertibility probabilities; keep survivorship annotation | §6.7, lines 575–582 |
| 8 | W | Minor | Fix family-roster table §2.6 to match the E14/E15 roster (add UCCSD, HaarRandom; state what happened to Universal/Structured reporting) | lines 127–141 |
| 9 | R | Minor | Soften "genuinely gate-count-optimal" → "no reduction under any tested compiler" | line 517 |
| 10 | R | Minor | Fix "exceeds 10×" → family-wise values (8–9×) or cite table | line 616 |
| 11 | W | Minor | Hedge production-compiler internals claim ("to our knowledge…") | line 254 |
| 12 | M | Minor | Add formal statements: Theorem 6, Lemma 3 (invoked line 342); renumber or explain theorem sequence gap (1, 2, 7, 8, 9) | §4 |
| 13 | W | Minor | Add the four missing limitations (Phase-2a/2b gap, `_gates_commute` conservativeness, noiseless environment, pass-isolation 5/15 coverage) to §7.4; fix `README.md:109` pointer (§6.3/13 → §7.4/actual count) | lines 620–644; README.md:109 |
| 14 | W | Minor | Remap `claim_evidence_table.csv` `Manuscript_Location` column to v7 numbering; integrate as Appendix A table; clear "pending merge" header | `docs/manuscript/claim_evidence_table.csv` |
| 15 | W | Minor | Integrate SOTA comparison table (`sections/sota_comparison_tables.md`) into §2.7 or §6.4; label each multi-compiler table with its dataset (E15 vs E20 vs pooled) to preempt R4-style confusion | line 153, lines 440–513 |
| 16 | W | Minor | References: renumber contiguously ([3],[5]–[7],[11],[12],[14],[15],[17]–[19],[23],[24],[26],[31],[34],[36],[37],[44],[49],[52]–[55],[57]–[60],[71]–[77],[79],[80] missing); unify in-text author-year style with the numbered list per venue style | lines 702–792 |
| 17 | W | Minor | Add Keywords; complete experiment registry table or footnote omissions (E6–E9, E11, E13, E22, E25) | after line 13; lines 360–384 |
| 18 | W | Minor | Refresh stale supporting docs before submission: `appendix.md` reviewer-risk table still says E19/E20/E21 "PLANNED, not run" (lines 293–295) and its abstract says "63,300 trials" (line 313); `supplementary_materials.md` S11.2 still says Cirq/t|ket> "not yet been executed" (lines 700–715); appendix §C-§5/§6 closed-by-E23/E20 items; appendix §C-13 raster-figure note obsolete | `appendix.md`, `supplementary_materials.md` |

**Non-issues verified (do not re-flag)**: E19/E21/E23/E24 headline numbers (pandas-verified, §8); pitfall items P1–P7 compliant; E4 single-seed and no-shuffler-control acknowledgments present (with E29/E28 rerun data now existing — Addendum B); no "Greedy dominates SA/GA" language anywhere; E18 survivorship annotation present at every first mention; data directories for all key experiments contain canonical CSVs (spot-checked 13 directories).

---

## Addendum B — Late-Breaking Working-Tree Findings (2026-07-20, post-audit sweep)

This audit was conducted against tracked documents. A final `git status` sweep shows extensive same-day working-tree churn from parallel wave-1 workers (data cleanup, `data/v8/`, release-manifest regeneration, `.bak-*` backups, `_agent_work/`). Two findings materially relevant to this audit's pitfall section:

1. **E29 multi-seed E04 rerun EXISTS** — `data/v7/e29/` (canonical `e29_multi_seed_e04_full.csv`, 800 rows = 4 optimizers × 10 seeds × 20 trials; `derived/e29_multi_seed_statistics.csv`, 44 rows; metadata timestamp 2026-07-19T01:04:07). Spot-check of the statistics file: per-seed means are tightly clustered (e.g., hybrid pooled 4.69% [CI 4.23–5.16], per-seed range 1.9 pp) — the single-seed E04 ranking concern is now addressable with data. **Gap**: not referenced in manuscript, README registry, or `docs/results/`; §7.4 #7 still frames multi-seed as "recommended for future work". Integration worker: update §6.1/E4 discussion + §7.4 #7 to cite E29, and add E28/E29 to the registry table (§5.4) and README.
2. **E28 random-gate-shuffler control EXISTS but is uncurated** — `_agent_work/orphan_outputs/gate_shuffle_ablation_full_20260718_204023.csv` (2,240 rows, experiment_id `E28_gate_shuffle_ablation`, 8 families, listing variants `original`/`wcl`/`shuffle_0`–`shuffle_4`, optimizers `greedy_phase1_lbl` + `commutation_phase2a`, mean reduction 6.33% across rows). This is exactly the control §7.4 #9 declares "not performed". **Gap**: files were orphaned during the same-day data-integrity cleanup; ownership for curation belongs to the data workers, but once canonical, §7.4 #9 and the Discussion must be updated (a shuffler control can either strengthen or undermine the ceiling narrative — the manuscript cannot keep asserting its absence once the run exists).

These do not change any pitfall verdict (compliance is judged on the manuscript as written) but they change the *remediation path* for items #13/§7.4: two of the twelve limitations now have data waiting rather than work to schedule.

---

## Appendix A — Audit Method

1. Full read of `manuscript.md` (792 lines), `appendix.md`, `analysis_summary.md`, `_cross_validation.md`, `_e18_extension.md`, `sections/*.md`, `README.md`, `claim_evidence_table.csv`; structural scan of `supplementary_materials.md` (headers + S11.2).
2. grep audits: figure references, hypothesis keywords, pitfall phrases (`dominat|survivorship|fixture-scale|exploratory|shuffler|single-seed|prototype action-space ceiling`), dangling `Table \d` references, E29.
3. pandas spot-verification against canonical CSVs: E19 (LBL/WCL stats), E21 (pairwise identity + mean), E23 (all-zero), E24 (per-optimizer means) — all match manuscript-reported values.
4. Working-tree sweep (`git status`) + targeted verification of newly discovered artifacts: `data/v7/e29/` (E29 multi-seed E04, 800 rows) and `_agent_work/orphan_outputs/gate_shuffle_ablation_full_20260718_204023.csv` (E28 shuffler control, 2,240 rows) — see Addendum B.
5. No project files modified; this report is the only file written.
