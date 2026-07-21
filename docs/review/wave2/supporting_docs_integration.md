# Wave-2 Supporting-Documents Integration — Completion Report

**Worker**: 文档整合师_Support (supporting-docs integrator, wave 2)
**Date**: 2026-07-21
**Scope**: `docs/appendix/appendix.md`, `docs/supplementary/supplementary_materials.md`, `docs/manuscript/claim_evidence_table.csv`, `README.md`, `docs/references/literature_review.md`
**Out of scope (untouched)**: `docs/manuscript/manuscript.md`, `docs/manuscript/sections/`
**Backups**: all five files have `.bak-20260721-002920` copies taken before any edit.

---

## 1. Files changed

### 1.1 `docs/appendix/appendix.md` (completed in the earlier part of this shift)
- Header STATUS rewritten as a wave-2 refresh note.
- C2/C4 window claims corrected: w ∈ {2,5,10,20,50} → {2,5,10,20}; C4 rewritten with traceable numbers (commutation-only family means 0.0/1.0/3.8/4.5 %, hybrid 6.8/7.9/10.6/11.3 % for w = 2/5/10/20) and an explicit note that power = 0.126 / p = 0.420 / d = 0.173 could not be reproduced and has unclear provenance.
- Strengths items 2/5/7, Scope of Multi-Compiler Comparison, reviewer-risk table (E19/E21/E20 PLANNED → completed), and the summary paragraph (63,300 → 33 datasets / 72,000+ rows) updated.
- "Update (2026-07-21, wave 2)" annotations added to §C items 1, 2, 5, 6, 7, 11, 13, 14.
- New §D (Phase-2b v2 full-scale), §E (SOTA multi-compiler, incl. Cirq-fix warning and tket RandomClifford fidelity-failure warning), §F (E22 shuffler control + E29 multi-seed non-reproduction) appended.

### 1.2 `docs/supplementary/supplementary_materials.md`
- S5.1 dataset table replaced by the release-manifest version (33 datasets / 72,682 rows) plus a post-manifest additions table (phase2b_full v8: 729 rows, SHA 81a0d1f4…; EHW full: 288 rows, SHA e6537e0e…) and a stale-SOTA-manifest warning.
- S5.2 schema families aligned to the canonical `docs/data_dictionary.md`: `legacy_v2_v3` = E1–E5 + E10; `results_v6` gains E25, E10p2b, E10-variance, E29-smoke, SOTA, ceiling-repair; `results_v7` = E22–E24, E26, E29, E10p2b-full, E19-extended; **new** `results_v8` = EHW + Phase-2b full v2 (confirmed via `schema_version: "v8"` in `data/v8/phase2b_full/metadata.json`). "5 schema families" → 6; metadata field name corrected `schema` → `schema_version`.
- Header 2026-06-15 disclaimer superseded: Cirq/t|ket> data now exists (E20-full 1,070 rows + v6 SOTA), pointer to S11.2/Appendix E caveats.
- S9.1 window set {2,5,10,20,50} → {2,5,10,20}.
- S9.2 "[NOT YET EXECUTED]" / "PRELIMINARY" blocks removed; replaced with executed status (E20-full + SOTA) and pointer to S11.2.
- S9.3 window set corrected; trend numbers replaced by traceable E16 family means; w = 50 row removed with an explicit correction note; statistical caveat rewritten (old power stats non-reproducible → removed).
- S11.2 fully rewritten: executed Cirq pipeline from `experiments/sota_benchmark.py::cirq_optimize` (drop_empty → drop_negligible → CZTargetGateset → eject_z → merge_1q_phased_xz → drop_empty; 2026-07-20 v1.1.0 fix documented), executed tket pipeline (DecomposeBoxes + FullPeepholeOptimise), tket RandomClifford 14/30 fidelity-failure caveat pointing to Appendix E.
- S12.2 same non-reproducible power-statistics correction.
- "45,000+ trials" → "72,000+ benchmark records" (open-problems section).

### 1.3 `docs/manuscript/claim_evidence_table.csv`
- Five rows appended (IDs C13–C17, index 14–18), all script/data paths verified to exist:
  - C13: Phase-2b v2 full-scale (BV 69.2 %, exact k+2 optimum 80/80, bound exceeded 2.7–3.5×; IQP 92.0 %; Structured 42.3 %; RandomClifford 48.2 %; pooled 46.5 % [42.4; 50.5]) → §4.2/§6.3.
  - C14: ceiling-model repair (LOFO MAE 0.0695, r = 0.722, ρ = 0.847 vs predict-0 baseline 0.0963) → §6.5, with CNOT-fold/underpowered/NaN-Pearson limitations.
  - C15: EHW noise-model validation (BV 46.15 % logical → 0 % at L1 physical; random +Hellinger 0.0016–0.0033 in 4/4 unitary-verified cases) → §7.4/§7.5, **carrying the mandatory "noise-model simulation, NOT real hardware" label**.
  - C16: E22 shuffler control (original 6.30 % vs shuffle 10.34 %, MWU p = 6.8e-15; phase2a p = 0.462 NS) → §6.2/§7.4 item 9.
  - C17: E29 multi-seed non-reproduction of E04 (RLS −176.5 %, SA −22.1 %, GA −8.3 %, hybrid +4.69 % [4.23; 5.16]) → §6.1/§7.4 item 7.
- **Pre-existing bug fixed**: row C1 contained an unquoted comma ("…15 pre-selected families, not universal law…") making it 10 fields vs 9 everywhere else; comma → semicolon. Verified present in the pre-edit backup, i.e., not introduced by this pass.
- Post-edit validation: `csv` module field count = 9 for all rows; `pandas.read_csv(skiprows=2, index_col=0)` parses 19 rows × 8 columns with correct ID sequence and field alignment.

### 1.4 `README.md`
- Limitations pointer fixed: `manuscript.md` Section 6.3 (13 subsections) → Section 7.4 (12 items), matching the current manuscript structure.
- Known Limitations updated: Phase-2b fixture-scale → v2 full-scale complete (729 rows) with residual stratified-grid / no-parity-gadget limitation; shuffler → E22 complete (counterintuitive 10.3 % > 6.3 %); E04 single-seed → E29 ten-seed non-reproduction with numbers; **new** tket RandomClifford correctness item (14/30 fidelity failures); WCL item updated to E19-extended outcome (8/16 families WCL > 0).
- Key Findings item 4: Theorem 9 "partially validated (fixture-scale)" → validated at full scale (k+2 optimum on all 80 BV instances, bound exceeded 2.7–3.5×; IQP 92.0 %, Structured 42.3 %, RandomClifford 48.2 %).
- Experiment Registry: five rows added after E25 — E22 (2,240), E26 (4), E29 (800), E10p2b-v2 (729), EHW (48, noise-model label).
- Statistical Protocol item 2: Cohen's d → Hedges' g (small-sample-corrected Cohen's d), with Cliff's delta noted as primary for near-zero-variance comparisons (verified against `analysis/generate_effect_sizes.py`, which computes d, g, Glass's Δ and Cliff's δ).
- Directory-tree annotations: Phase-2b "(fixture-scale)" → "(full-scale v2)"; data versions "v2_fixed through v7" → "through v8".

### 1.5 `docs/references/literature_review.md` (v1.1 → v1.2)
- §2.2.6 de Beaudrap paragraph rewritten: the cited "de Beaudrap, Glendinning & Zhang — Faster resynthesis with the ZX-calculus (QPL 2022)" paper **does not exist** (its arXiv number resolves to an unrelated ML paper). Replaced with the real de Beaudrap, Kissinger & van de Wetering (2022), "Circuit Extraction for ZX-diagrams can be #P-hard", ICALP 2022, LIPIcs 229, 119:1–119:19, arXiv:2202.09194 — with an explicit correction note and re-positioned "achieved / did NOT do" analysis (extraction is #P-hard in general, the *opposite* of the fabricated "faster resynthesis" claim).
- Ref [13] Kliuchnikov corrected (see decision D5).
- Ref [15] replaced with the real ICALP 2022 entry.
- Ref [41] Riu et al.: *Quantum* 9, 1634 → **1758** (fixed both in §9.7 and in the §10.6 citation line).
- §10 expanded from seven to ten works: new §10.8 VOQC (Hietala, Rand, Hung, Wu & Hicks, PACMPL 5(POPL) 2021, arXiv:1912.02250), §10.9 Quasar equality saturation (Yang, Raun, Tao & Gu, PACMPL/PLDI 2026, DOI 10.1145/3808254), §10.10 SSR (Huang et al., ACM TODAES 2026, DOI 10.1145/3828549; arXiv:2503.03227); old §10.8 Comparative → §10.11, old §10.9 Summary → §10.12; section year range 2021–2025 → 2021–2026.
- Table 5: three rows added (VOQC: formal theory ✓ machine-checked correctness; Quasar: Partial step-limited optimality; SSR: Partial SAT depth-optimality at subcircuit level).
- New refs [43]–[45] added to §9.7.
- §7.2 opening, §10.12 summary text, §11 item 6 synced to the ten-work survey.
- Study-scale figures updated: 45,527 trials → 72,000+ records / 33 canonical datasets (6 occurrences).
- Footer bumped to v1.2 with a change log.

---

## 2. Key decisions

- **D1 — EHW canonical row count**: README/registry and S5.1 keep the manifest's 48-row smoke file as the manifest-tracked count, while S5.1's post-manifest table records the 288-row full file (designated canonical by the hardware worker) and flags the conflict for the data worker. I did not rewrite the manifest — out of scope.
- **D2 — SOTA manifest staleness**: manifest says 60 rows; disk file has 105 rows (post-Cirq-fix regeneration, SHA bfcaaa…). I verified that `scripts/reproduce_all.py --verify` currently **FAILS** on the SOTA_BENCHMARK SHA check. Manifest refresh is the data worker's job; supporting docs carry a warning note only.
- **D3 — E16 power statistics**: power = 0.126 / p = 0.420 / d = 0.173 could not be reproduced from the canonical E16 dataset (wave-1 statistical review; provenance unclear). All three documents (appendix, supplementary S9.3/S12.2) now state this explicitly instead of citing the numbers.
- **D4 — E22 family count**: canonical E22 covers **16** families (one wave-1 audit note said 8); all new text uses the canonical 16-family figures (greedy original 6.30 % vs shuffle 10.34 %, WCL 12.20 %, p = 6.8e-15; phase2a 3.87/2.70/1.00 %, p = 0.462).
- **D5 — Kliuchnikov reference (deviation from handoff)**: the handoff suggested PRL **110**, 190502. Web verification shows that volume/page belongs to a *different* Kliuchnikov–Maslov–Mosca paper ("Asymptotically optimal approximation of single qubit unitaries …", arXiv:1212.0822). The title matching §2.2.5's content ("Fast and efficient exact synthesis of single-qubit unitaries generated by Clifford and T gates", arXiv:1206.5236) was published in **Quantum Information & Computation 13(7–8), 607–630 (2013)** — confirmed by multiple independent reference lists (quantum-journal.org, arXiv). Ref [13] therefore cites QIC, not PRL. If the manuscript worker prefers the PRL paper, the *title* must change accordingly — the two must not be mixed.
- **D6 — VOQC/Quasar/SSR citations verified online**: Quasar (pldi26main-p23-p, DOI 10.1145/3808254) and SSR (ACM TODAES, DOI 10.1145/3828549, online 2026-07-04; arXiv 2025) confirmed via ACM/conference-publishing/arXiv sources; VOQC (POPL 2021, arXiv:1912.02250) is well-established.
- **D7 — Schema-family alignment**: supplementary S5.2 now mirrors `docs/data_dictionary.md` exactly (including E10 → legacy_v2_v3 and E25 → results_v6), since S5.2 itself declares the dictionary canonical.
- **D8 — Lit-review scope note**: the manuscript-side fabricated references ([22], [69] "C. Nitsch", [70] QASMBench authors/arXiv, [81]) are **not** present in literature_review.md; no [69]/[70]/[81] entries exist here. Manuscript-side fixes belong to the manuscript worker.

## 3. Remaining issues (handoff to other workers)

1. **Release manifest refresh (data worker)**: add `data/v8/phase2b_full/` (729 rows) and `data/v8/hardware_validation/` full file (288 rows); update SOTA_BENCHMARK entry (60 → 105 rows, new SHA). Until then `scripts/reproduce_all.py --verify` FAILS — consider noting this in README Quick Start if the refresh is delayed.
2. **claim_evidence_table.csv rows 0–13 (manuscript worker)**: `Manuscript_Location` still uses the old section numbering (e.g., "Section 5.x"); needs remap to the v7 manuscript numbering used by the new rows C13–C17. The file's STATUS line ("Not yet integrated into main manuscript. Pending merge.") was left unchanged — integration is the manuscript worker's call.
3. **data_dictionary.md minor inconsistency (data worker)**: text says "five schema families" but the table lists six (including results_v8); also the results_v8 row mentions only EHW, while `data/v8/phase2b_full/metadata.json` declares `schema_version: "v8"`.
4. **Manuscript cross-reference final check (manuscript worker)**: new rows C13–C17 cite §4.2/§6.1/§6.2/§6.3/§6.5/§7.4/§7.5 of the v7 manuscript; these need final verification against the manuscript after its own wave-2 edits.
5. **45,527→72,000+ style scale claims**: fixed in the five files in scope; other docs (theory/results) were not audited in this pass.

## 4. Verification performed

- `pandas`/`csv` round-trip of claim_evidence_table.csv: 19 rows × 8 columns, uniform 9-field rows, IDs C1–C17 + Thm6/Thm7 in order.
- grep sweeps: no residual `w ∈ {2,5,10,20,50}` window claims, `NOT YET EXECUTED`, `PRELIMINARY — only metadata`, `45,527`, `45,000+`, `1634`, `Glendinning`, or uncorrected `power=0.126` citations in the edited files (remaining occurrences are intentional correction notes).
- All script and data paths cited in new CSV rows and README registry rows verified to exist on disk.
- All new literature citations ([13], [15], [41], [43], [44], [45]) verified against external sources (arXiv, ACM DL, quantum-journal.org) in this session.
