# Wave-2 Manuscript Integration Report

**File owned:** `docs/manuscript/manuscript.md` (exclusive)
**Date:** 2026-07-21
**Backup before overwrite:** `docs/manuscript/manuscript.md.bak-20260721-003505` (v7, 792 lines)
**Result:** v8 integrated draft, 1,082 lines, 18 figure references, 22 numbered tables, 47 references.

---

## 1. What changed (v7 → v8)

| Area | Change |
|---|---|
| Status note | Added v8 change log; realized length recorded. |
| Abstract | Structured (Background/Methods/Results/Conclusions); lead result = BV $k{+}2$ exact optimum; ceiling-aware claims hedged with LOFO numbers. |
| §1.4 (new) | Falsifiable hypotheses H1–H5 with decision rules and verdicts (Table 1). |
| §1.5 | Contributions rewritten: representation > algorithm ("overturns conventional wisdom" framing), Phase-2b partial refutation, ceiling-aware with honest limitations. |
| §2.6 | Unified 15-family roster (Table 2); HaarRandom≡Universal naming note; Structured/E25 16-family reconciliation. |
| §2.7 | Related work extended with VOQC [45], equality saturation/Quasar [46], SSR [47]. |
| §3.4–3.5 | E19 kept; stale figure cross-ref removed; future-work pointer aligned to §7.6. |
| §4 | Thm 6/Lemma 3 formal statements; Thm 9 updated to full-scale v2 (80/80 BV instances, $k{+}2$ exact, 3.1–4.2× bound, fidelity ≥ 1−2e-13); "fixture-scale" caveat removed. |
| §5 | Registry table (Table 4) gains E22 (2,240), E25 (729), E29 (800); E16 window set fixed to $w\in\{2,5,10,20\}$; data versions corrected to v7 (E22–E24, E29) and v8 (E25, EHW); compiler configs carry fair-mode, Qiskit L0–L2 retest, Cirq-fix and tket-fidelity notes. |
| §6.1 | E4/E5 statistics corrected against canonical FDR table (E4 KW adj $p=1.2\times10^{-11}$, driven by SA/GA inflation; E5 adj $p=1.1\times10^{-10}$; E1–E3 remain adj $p=1.0$). New §6.1.1: E29 multi-seed (hybrid +4.69% [4.23,5.16]; RLS −176.53%; SA −22.15%; GA −8.31%) → E4 exact values downgraded to single-seed indicative. |
| §6.2 | E22 integrated with new Table 4b (greedy LBL 6.30→10.34% shuffle, $p=6.8\times10^{-15}$; WCL 12.20%, $p=1.1\times10^{-12}$; Phase-2a $p=0.462$ listing-robust). |
| §6.3 | Trichotomy unified to five classes (I=1, II=3, IIIa=3, IIIb=5+1 borderline, IIIc=2; sum=15) — identical wording in abstract, §6.3, §7.1. E15 table kept with E15-dataset provenance note; prescriptions table renumbered Table 9 (was dangling "Table 11"). E16: non-reproducible "$p=0.420, d=0.173$" replaced by KW adj $p=1.7\times10^{-7}$ + paired Wilcoxon w10→w20 $p=0.0544$; window set stated as {2,5,10,20} only. |
| §6.4 (new) | E25 Phase-2b full-scale: Table 10 (family results), Table 11 (BV vs Thm 9 bound), pooled bootstrap (P1 1.4% [0.1,3.0], P2a 9.3% [7.6,11.1], P2b 46.5% [42.4,50.5]), per-family Wilcoxon, depth trends, stratified-grid and template-library caveats. |
| §6.5 | Old E20-era multi-compiler table replaced by canonical S1–S5 (Tables 12–16) copied from `sections/sota_table_fragment.md`; tket RC fidelity footnote; Cirq SurfaceCode +8.4% exception; Grover compiler-inflation finding added; pass-isolation and interaction analysis retained; Figures 12–16. |
| §6.6 | Rewritten: Table 17 (per-family speedups, aggregate 34.97×, family-mean 22.64×); "28% of passes" corrected to 114/1140 = 10.0%; symmetric-timing control (0.97–11.48×, aggregate 2.20×) disclosed; Table 18 LOFO repair (mechanism+single-stage MAE 0.0695 [0.0539,0.0865], pooled r 0.722 [0.666,0.794], ρ 0.847, R² 0.393) with all baselines and honest failure modes; "validates the framework as a predictive model" deleted; unified statement adopted. |
| §6.7 | Full 17-row cross-validation (Table 19) from `docs/results/analysis_summary.md` + Thm 9/E25 row; scorecard 13 MATCH / 3 PARTIAL / 1 MISMATCH / 0 UNTESTED; detailed Thm 1a WCL/LBL mismatch discussion added. |
| §6.8 | E17 kept (Figure 18); E18 rewritten around ITT (Table 20: survivor 0.1800 → ITT 0.1351 [0.102,0.169], bracket [0.135,0.187], MCAR $d^2=49.96$, convertibility 71.1%/55.6%) + per-family failure Table 20b. |
| §7 | 7.1 five-class regime; 7.2 hidden variable + E22 + representation-complexity paragraph; 7.3 prescriptions, 8–9× workload framing (was "exceeds 10×"); 7.4 new EHW noise-model results (logical-vs-physical compression, Hellinger +0.0016–0.0047); 7.5 limitations expanded to 18 items (incl. Phase-2b grid, tket correctness, E21 fidelity labeling, noise-model-only hardware, pass-isolation 5/15, conservative `_gates_commute`); 7.6 future work (real-device protocol, phase-gadget/ZX engines, full-factorial P2b, WCL audit, pre-registration). |
| §8 | Conclusion rewritten around 33 datasets/72,682 rows, five-class stratification, BV $k{+}2$ optimum, 17-row scorecard, honest ceiling-aware framing. |
| Declarations | Data availability updated to v1–v8; release v8.0.0. |
| References | Renumbered [1]–[47]; fabricated old [22] replaced by de Beaudrap/Kissinger/van de Wetering ICALP 2022 (arXiv:2202.09194); fabricated old [81] deleted; corrections: [8]→PRL 110, 190502 (2013); [9]→Amy & Mosca IEEE TIT 65(10):6271–6283, 2019; [39]→Quantum 9, 1758; [41]→N. Quetschlich et al., Quantum Sci. Technol. 8, 035027 (2023); [42]→Li/Stein/Krishnamoorthy/Ang, ACM TQC 2022, arXiv:2005.13018; additions [45] VOQC, [46] Yang et al. PLDI 2026 (DOI 10.1145/3808254), [47] Huang et al. SSR arXiv:2503.03227 (both new entries verified via web search this session). Dangling in-text "Wille et al. 2009" (2×) re-pointed to Nam et al. 2018 / Iten et al. 2022; "Qarl"→"Quarl" (3×); in-text author-year fixes (Li et al. 2022, Quetschlich et al. 2023, Amy and Mosca 2019) applied in earlier chunks. |

## 2. Task checklist (12 assigned items)

1. ✅ Structured abstract + keywords.
2. ✅ §1.4 H1–H5 table with decision rules.
3. ✅ Unified trichotomy (1+3+3+5+1+2=15) consistent in abstract/§1.5/§6.3/§7.1/Tables 7, 9, 12.
4. ✅ Thm 9 v2 full-scale update; fixture-scale language removed everywhere.
5. ✅ §6.4 Phase-2b new section (Tables 10–11).
6. ✅ §6.5 S1–S5 integration (Tables 12–16) replacing stale E20 Cirq numbers.
7. ✅ §6.6 ceiling-aware rewrite (Tables 17–18, symmetric-timing caveat, honest LOFO).
8. ✅ §6.7 full cross-validation table + scorecard + Thm 1a discussion.
9. ✅ §6.8 E18 ITT + per-family failure table.
10. ✅ E22/E29 integrated (§6.1.1, §6.2, Table 4b); registry/data-version updates.
11. ✅ 18 figures wired in first-mention order (Fig. 1–18), all files verified to exist; tables numbered 1–20 (+4b, 20b).
12. ✅ References repaired, renumbered [1]–[47]; in-text citation audit completed (no dangling names).

## 3. Numbers re-verified against canonical data this session

- E22 re-computed from `data/v7/e22/e22_gate_shuffle_ablation.csv`: greedy_lbl 6.30%→10.34% (MWU **$p=6.8\times10^{-15}$** — supersedes the 3.4e-15 in my earlier note, which came from a different shuffle pooling); WCL 12.20% ($p=1.1\times10^{-12}$); Phase-2a 3.87%→2.70% ($p=0.462$), WCL 1.00% ($p=0.057$). Manuscript uses the freshly computed values.
- Cross-validation row count: source scorecard (16 rows, 12/3/1) + Thm 9 row = **17 rows, 13/3/1/0**; conclusion and status note corrected accordingly (an intermediate draft said 18/16 — fixed).
- All 18 `analysis/figures/*.pdf` references verified on disk.

## 4. Known issues / handoff notes

1. **BV excess-over-bound discrepancy (recorded, not resolved):** `docs/results/phase2b.md` reports 2.7–3.5×; the canonical per-instance computation gives 3.06–4.24× (manuscript states "3.1–4.2×"). Recommend the results-doc owner reconcile `phase2b.md` against `data/v8/phase2b_full/derived/`.
2. **E15 table vs S1 differences are dataset differences, not errors:** Table 7 keeps E15-era Qiskit O3 numbers (994 rows, `e15_multi_compiler_e15_full_20260611_150934.csv`) and is captioned as such; Table 12 (S1) is the canonical multi-compiler source. Reviewers should not expect the two Qiskit columns to match.
3. **HaarRandom classification:** kept as IIIb borderline (≤6.5 pp production gains) everywhere; note (i) under Table 2 explains the HaarRandom≡Universal naming across experiments.
4. **Length:** realized 1,082 lines vs the 1200–1400 planning estimate. Content completeness was prioritized over padding; all 12 assigned items are integrated. If more length is wanted, legitimate expansion sources exist (per-size BV table from `family_summary_v8.csv`, E14 per-family heatmap numbers).
5. **Not touched (outside my ownership):** `docs/manuscript/_cross_validation.md` and `docs/manuscript/_e18_extension.md` still carry stale "pending merge" headers — both files are now fully merged into §6.7/§6.8; the appendix/supplementary worker may want to archive them. `claim_evidence_table.csv` remapping belongs to the parallel worker.
6. **Table 4b / 20b numbering:** auxiliary tables inserted as "4b" and "20b" to avoid renumbering Tables 5–20; renumber to sequential if the editorial pass prefers.
7. **New references verified by web search this session:** SSR full title ([arXiv:2503.03227](https://arxiv.org/abs/2503.03227)) and Quasar/equality-saturation authorship (G. Yang, P. Raun, R. Tao, R. Gu, PLDI 2026, DOI 10.1145/3808254).
