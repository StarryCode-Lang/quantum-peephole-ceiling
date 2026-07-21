# Wave 3 — Documentation Consistency Sweep Report

**Worker**: Consistency sweep (wave 3, final-verification wave)
**Date**: 2026-07-21
**Backup tag**: `.bak-20260721-013513` (all overwritten files backed up before editing)
**Scope (exclusive)**: `docs/manuscript/claim_evidence_table.csv`, `docs/data_dictionary.md`,
`docs/manuscript/archive/`, stale scale figures in `docs/theory/*.md` and `docs/results/*.md`,
`README.md` (targeted fixes), `docs/manuscript/manuscript.md` (cross-reference repairs + evidence-based expansion).
All other files treated as read-only.

---

## 1. Claim–evidence table remap (task 1)

`claim_evidence_table.csv` rewritten atomically; header STATUS line documents the remap.
Structure re-validated after the write: **19 data rows × 9 fields**, IDs in sequence
`C1–C12, Thm6, Thm7, C13–C17`; no bare commas inside fields; every `Manuscript_Location`
citation uses the v8 numbering.

Remap summary (v7-era → v8):

| Row | Old location (v7) | New location (v8) | Other corrections |
|---|---|---|---|
| C1 | §5.x generic | §3.2 (Thm 1); §4.1 (Thm 2); §6.1; Fig. 1; Table 7 | — |
| C2 | — | §4.2 (C2); §6.3; Fig. 8; Fig. 11 | — |
| C3 | — | §6.5; Fig. 12; Fig. 16; Table 12 | — |
| C4 | — | §6.3 (E16); Fig. 11; Table 8 | — |
| C5 | — | §6.8; Fig. 18 | — |
| C6 | — | §6.8; Table 20 | — |
| C7 | — | §5.2; §6; Fig. 6 | — |
| C8 | — | §4.1 (Thm 2c/2d); `docs/theory/formal_results.md` Appendix A | — |
| C9 | — | §3.4; §6.2; Table 3 | — |
| C10 | — | §6.6; Table 17 | — |
| C11 | — | §6.5; Tables 12–16; Supplementary S11.2 | — |
| C12 | — | §4.2 (Thm 9); §6.4; Appendix D | — |
| Thm6 | — | §4.2 (Thm 6); §6.7 | — |
| Thm7 | — | §4.2 (Thm 7) | — |
| C13 | §6.3 | §4.2; §6.4 | bound excess 2.7–3.5× → **3.1–4.2×**; "pending manifest" → recorded as added to manifest (`E26_phase2b_full_v8`) |
| C14 | §6.5 | §6.6 | — |
| C15 | — | §7.4; §7.5 | — |
| C16 | — | §6.2; §7.5 item 9 | — |
| C17 | — | §6.1.1; §7.5 item 7 | — |

STATUS header set to **Integrated** (was pending-merge).

## 2. Data dictionary (task 2)

`docs/data_dictionary.md`: "five schema families" → **six schema families** (line 35);
"all three schema families" → "all six"; `schema_version` enumeration extended with
`results_v6` / `results_v7` / `results_v8`; the `results_v8` row now names the
"Phase-2b full v2" payload, aligned with supplementary S5.2.

## 3. Pending-merge fragments archived (task 3)

`docs/manuscript/_cross_validation.md` and `docs/manuscript/_e18_extension.md` were stale
pending-merge fragments whose content is already integrated (§6.7 Table 19; §6.8 Tables 20/20b).
An `ARCHIVED` status note was prepended to each (pointing at the integrating section) and both
were moved to `docs/manuscript/archive/`. The pre-existing `fragments/` directory and
`manuscript_v6_archived.md` were left untouched.

## 4. Stale scale figures swept (task 4)

Canonical anchor used per the task brief: **72,682 rows / 33 canonical datasets**
(matching manuscript/README/supplementary as they stood at wave-3 start). See §7 for the
manifest drift recorded during this sweep.

- `docs/theory/framework.md`: "45,000+" → 72,682 rows / 33 datasets (2 sites);
  E19 effect "~18%" → **~7.8%** (2 sites: lines 168, 209).
- `docs/theory/formal_results.md`: "~18%" → "~7.8%" (7 occurrences, `replace_all`);
  added the E19 anchor (10,000 rows, 7.83%) at line 531.
- `docs/results/hardware_validation.md`: "27 datasets" → 33 canonical datasets, with a note
  that the original audit was written when the registry held 27.
- `docs/results/analysis_summary.md`: Lemma 3 row "45,000+ trials" → fidelity-verified-corpus
  wording with the 72,682/33 anchor and the E18/E21 caveats.
- `docs/results/universal_law_assessment.md`: "45,500" is the exact E1–E5 subtotal
  (25,000+2,100+12,000+400+6,000) — verified correct, **not** changed.
- No stale E20/Cirq numbers found in `docs/results/` outside the corrected
  `sota_compiler_benchmark.md` itself.

## 5. Cross-reference audit (task 5)

- **Figures**: all 18 `analysis/figures/*.pdf` references in the manuscript (fig01–fig17 +
  fig08b) match a real file 1:1; no missing, no unreferenced. Re-verified after the expansion
  (18 unique refs, exact set equality).
- **Tables**: body captions are 1–20, each exactly once, plus lettered auxiliary tables
  **4b** (E22), **20b** (E18 ITT) — both pre-existing wave-2 conventions — and **4c** (E22
  per-family), **5b** (E29 per-seed), **9b** (classification summary), **11b** (BV per-size)
  added in this sweep following the same convention. No renumbering of 1–20 was performed.
- **Appendices**: `docs/manuscript/appendix.md` contains §A (claim–evidence map), §B (scope/
  limitations), §C (limitations/future work), **§D (Phase-2b v2 full-scale validation, 729
  rows)**, **§E (SOTA compiler benchmark update)**, **§F (E22 shuffle + E29 multi-seed)**.
  The v8 body previously cited none of them; this sweep wired: §6.4 → Appendix D, §6.5 →
  Appendix E (×2 incl. pass isolation), §6.1.1 & §6.2 → Appendix F, §7.5 items 13/14 →
  Appendices D/E (final counts: D ×2, E ×3, F ×2).
- **README registry vs manifest** (recorded, not changed): README registry table lists 26
  experiment rows; the release manifest now lists 34 datasets. README totals line still says
  "over 72,000 rows / 33 canonical datasets". See §7.

## 6. Manuscript repairs and evidence-based expansion (task 6)

Length: **1,082 → 1,193 lines** (+111), all additions traced to canonical data or to
`docs/results/experimental_design.md` / `docs/results/sota_compiler_benchmark.md`.

Repairs (small fixes):

1. §6.2 and Table 4 registry: E22 "8 families" → **16 families** (canonical:
   2,240 rows = 2 optimizers × 7 listings × 16 families × 10 trials).
2. §7.2: E22 statistics aligned with §6.2 — shuffle p `3.4×10⁻¹⁵` → `6.8×10⁻¹⁵`
   (recomputed MWU p = 6.82e-15); `0.4623` → `0.462`.
3. §6.4: paired-Wilcoxon p-values recomputed from raw per-instance pairs —
   BV `4×10⁻¹⁵` → **`3.8×10⁻¹⁵`** (n = 80); Structured/IQP/RandomClifford/Universal
   `1×10⁻⁵ / 5×10⁻⁶ / 5×10⁻⁶ / 2×10⁻⁵` → **`7.5×10⁻⁹` each** (one-sided, n = 27,
   the 2⁻²⁷ saturation value; all paired differences positive). Grover 0.016 and
   UCCSD 0.033 were already correct.
4. §4 intro: full proofs now point to `docs/theory/formal_results.md` **and** the
   supplementary materials (the INSERTION-cascade proof lives in formal_results.md).
5. §7.5 item 2 updated: cross-family WCL is no longer purely future work (E19-extended
   provides a first check); residual gap = WCL shuffle and WCL × Phase-2b controls.
6. §7.5 item 9: E22 "8 families" → 16 families.
7. Table 19 (Lemma 3 row): "45,000+ trials" → fidelity-verified corpus
   (72,682 rows, 33 canonical datasets).
8. §1.5 Contribution 3: "aggregate 35×" → **34.97×** (matches §6.6 and README).

Expansions (new evidence content):

| # | Location | Content | Source |
|---|---|---|---|
| E1 | §5.2 | Power-disclosure block + adequacy table (adequate E1–E5/E15–E17; underpowered E10 0.170, E11 0.396, E12 0.154, E13 56 records, E14 0.293, E18 0.679) + interpretation | experimental_design.md §12.8 |
| E2 | §5.2 | Percentile-vs-BCa rationale + pre-registered effect-size thresholds (Cohen's d, Cliff's δ) | experimental_design.md §8.2–8.3 |
| E3 | §6.1 | Per-cell design parameters (E1 500/depth, E2 233/level, E3 1,500/qubit, E4 100/optimizer, E5 1,000/depth) | experimental_design.md §12.8.1 |
| E4 | §6.1.1 | E29 per-seed sign-consistency paragraph + **Table 5b** (10 seeds × 4 optimizers; hybrid +4.00…+5.87% in 10/10 seeds; RLS/SA/GA negative in 10/10) | recomputed from `data/v7/e29/` |
| E5 | §6.2 | E19-extended cross-family block + table (7 of 16 families gain: BV +30.8, RandomClifford +22.3, Structured +12.9, UCCSD +10.7, IQP +7.2, Universal +6.8, Grover +3.7 pp; 9 named families at 0; WCL fidelity min 1−1.1×10⁻¹²) | recomputed from `data/v7/e19_extended/` (960 rows) |
| E6 | §6.2 | **Table 4c** E22 per-family (original / 5-seed shuffle mean / WCL) + interpretation (shuffle benefit family-structured; CNOT 100→95 mirror effect) | recomputed from `data/v7/e22/` |
| E7 | §6.3 | E14 per-family corroboration paragraph (P2a: Oracle 13.98, RandomClifford 13.04, Grover 4.35, UCCSD 0.42, IQP 0.30; P1: CNOT 100 only) | recomputed from `data/v5/e14/` |
| E8 | §6.4 | **Table 11b** BV per-size vs Thm 9 bound (n = 3…10; mean 59.2→74.4%, min 54.5→62.5%, bound 17.1→20.4%; bound met at every size) + Appendix D pointer | `data/v8/phase2b_full/bv_theory_v8.csv` |
| E9 | §4.2 | E24 Theorem-7 validation paragraph + per-size table (75 rows; P2a 62.5→89.3% growing with n; P2b v1 ≤ 12.5%, 0 beyond n = 4; fidelity 1.0) | recomputed from `data/v7/e24/` |
| E10 | §6.5 | Cirq pipeline-correction provenance (CZTargetGateset kwarg-rename silently skipped; QASM sx/sxdg round-trip failure on 100 rows; CNOT 0→100%, RandomClifford 47.4→63.1%, QuantumWalk −382.6→−4547.4%) + Appendix E pointer | sota_compiler_benchmark.md §3 |
| E11 | §6.5 | Pass-isolation paragraph (CommutativeCancellation alone reproduces prototype on CNOT 100.0% / Oracle 32.9% / RandomClifford 25.3% vs 23.8%; Optimize1qGates 0%; 20–45 pp gap = beyond-peephole synergy) | sota_compiler_benchmark.md §9, `data/v5/qiskit_pass_isolation.csv` |
| E12 | §7.1 | **Table 9b** refined classification summary (1+3+3+5+1+2 = 15, evidence pointers) | synthesized from Tables 6–12 |
| E13 | §7.4 | EHW protocol paragraph (FakeManilaV2 5q / FakeNairobiV2 7q calibration snapshots; 8,192 shots × 3 seeds {101,202,303}; transpile L0/L1, seed 12,345; Hellinger/TVD definitions; 288-row full run supersedes 48-row smoke) | `data/v8/hardware_validation/ehw_metadata_full_20260720_150931.json` |
| E14 | §3.4 | E19 WCL distribution breadth (92.7% of 5,000 trials strictly positive; quartiles 5.71/7.92/10.00%) | recomputed from `data/v6/e19/` |
| E15 | §5.4 | Table 4 registry: EHW row added (288 rows, 3 circuits) | manifest + EHW metadata |
| E16 | Declarations | Data Availability now states 33 datasets / 72,682 rows via the manifest | release_manifest.json |
| E17 | Status note | Wave-3 revision line appended (items xiii–xviii) | — |

## 7. Manifest drift recorded during this sweep (not synced — decision needed)

At wave-3 start this worker read `release/release_manifest.json` as **33 datasets / 72,682
rows**. At ~01:20 a parallel data worker updated it to **34 datasets / 73,696 rows**
(SOTA suite 60 → 105 rows; EHW smoke 48 → 288 full run; new `E26_phase2b_full_v8` 729 rows;
disk state matches the new manifest). Per the task brief, all documentation written in this
sweep still anchors on **72,682 / 33**, consistent with the manuscript, README, and
supplementary as they stand. **The total-count sync (72,682 → 73,696; 33 → 34) is left to the
orchestrator as a single coordinated edit across README, manuscript §1.5/§5.4/§8/Declarations,
and supplementary S5.1** — piecemeal edits by one worker would create exactly the
cross-document inconsistency this sweep exists to remove.

## 8. Leftover issues (for orchestrator / other owners)

1. `docs/manuscript/appendix.md` §A claim–evidence table still cites v7 figure/table/section
   numbers (Fig. 1 / Table 1 / Section 5.6.4 etc.) and the file uses lone-`\r` line endings.
   Owner should sync it against the remapped `claim_evidence_table.csv` (§1 above).
2. `docs/supplementary/` S5.1 table still shows the pre-update manifest (SOTA 60, EHW smoke
   48, 33 / 72,682) plus a post-manifest supplement table — not this worker's file.
3. `docs/results/hardware_validation.md` line 36 cites "manuscript.md §15.16" — stale
   cross-reference (v8 has no §15; the noise-aware item is §7.6 item 8). Outside this
   worker's "scale-figures-only" mandate; recorded, not fixed.
4. Wave-1 known mismatch still open: `docs/review/wave1/phase2b.md` quotes 2.7–3.5× vs
   canonical 3.1–4.2× (that file is a review record; owner to decide annotation vs rewrite).
5. `scripts/reproduce_all.py --verify` was not re-run after the parallel worker's manifest
   update (73,696/34); recommend a re-run to confirm it turns PASS.
6. README registry (26 experiment rows) vs manifest (34 datasets) — the registry table is a
   curated subset; recorded for awareness, no change made.

## 9. Verification log

- CSV re-parsed after write: 19 data rows × 9 fields, IDs C1–C12/Thm6/Thm7/C13–C17. PASS
- Figure refs ↔ `analysis/figures/*.pdf`: 18 unique refs, exact set equality. PASS
- Table captions 1–20 unique + aux 4b/4c/5b/9b/11b/20b unique. PASS
- Stale-figure sweep over README, manuscript, data_dictionary, docs/theory, docs/results
  (excluding `.bak*`, `archive/`, `docs/review/`): no remaining instances of "45,000+",
  "2.7–3.5x", "3.4×10⁻¹⁵", "0.4623", "8 of 16", "Section 7.4 (12 items)", "mean 35x",
  "aggregate 35×", "27 datasets", "five/three schema families". PASS
  (two intentional "8 families" remain in `docs/results/e18_survivor_bias.md` — E18's eight
  fully-failing families, correct in context).
- All newly written numbers recomputed from canonical data in this session (E22, E29,
  E19-extended, E14, E24, E19 quartiles, BV per-size, EHW protocol). PASS
- manuscript.md length 1,082 → 1,193 lines. PASS
