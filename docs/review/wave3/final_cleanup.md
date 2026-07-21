# Wave 3 — Final Cleanup Report (total-count sync + stale-reference sweep)

**Worker**: Final-cleanup engineer (wave 3, closing pass)
**Date**: 2026-07-21
**Backup tag**: `.bak-20260721-021820` (all edited files backed up before editing; edits via atomic write / Edit tool)
**Anchor**: `release/release_manifest.json` — release-id `q-research-8.0.0-wave3`, **34 canonical datasets / 73,696 rows**

---

## 1. Scope

Single coordinated edit to eliminate the drift left by the parallel wave-3
workers: documentation still anchored on the old **33 datasets / 72,682 rows**
while the release manifest already read **34 datasets / 73,696 rows**
(SOTA 60→105, EHW smoke 48→full 288, new `E26_phase2b_full_v8` 729 rows).
Plus the four leftover issues recorded in `docs/review/wave3/consistency_sweep.md` §8
(appendix §A v7 remap, supplementary S5.1, hardware_validation.md stale §15.16,
phase2b.md 2.7–3.5× reconciliation).

## 2. Files changed (11)

| File | Changes |
|---|---|
| `README.md` | Overview + Total line → **73,696 rows / 34 canonical datasets** (exact manifest caliber replaces "over 72,000"); Experiment Registry EHW row 48 → **288**; all 26 registry rows programmatically re-verified against the manifest (all match; manifest IDs `WCL-E19`/`MC-E20` correspond to registry E19/E20). |
| `docs/manuscript/manuscript.md` | 7 sites synced via `replace_all`: "72,682" → "73,696" (×7), "33 canonical datasets" → "34 canonical datasets" (×7) — covering Abstract (§Methods), §1.5 Evidence, §2.7 Related Work, §5.4 Experiment Registry, §6.7 Table 19 (Lemma 3 row), §8 Conclusion, Declarations/Data Availability. |
| `docs/supplementary/supplementary_materials.md` | S5.1 header note → 34 datasets / 73,696 rows; SOTA row 60 → **105** (SHA `bfcaaa47588109fe…`); EHW row → `ehw_runs_full_20260720_150931.csv` **288** rows (SHA `e6537e0ee9b59ca5…`); new `E26_phase2b_full_v8` row (729 rows, SHA `81a0d1f44340e738…`); Total row → **34 / 73,696**; the stale "Post-manifest additions" table + SOTA-manifest warning replaced by a post-manifest reconciliation note (all three additions now in the manifest). |
| `data/DATA_CANONICAL.md` | Header → v2.1.0, 2026-07-21, 34 datasets / 73,696 rows; SOTA row 60 → **105** (note: 7 tool configs × 15 families); EHW row → full 288-row run (smoke superseded); new E10p2b-v2 row (729 rows); Totals line → **34 / 73,696 (2026-07-21)**; v8 version-meaning note + Known Issue #6 updated (full run supersedes smoke). |
| `data/v6/sota_benchmark/README.md` | Canonical dataset 60 → **105 rows** (7 tool configs × 15 families: Qiskit default/L0/L1/L2, Cirq default, t\|ket> default, custom default); `raw/` row now lists the actual analysis inputs incl. `qiskit_level0/1/2_20260720` (520 rows each) and the corrected `cirq_default_20260720` (520 rows), with `cirq_default_20260718` flagged stale (pre-fix pipeline). |
| `docs/manuscript/appendix.md` | **Lone-\r line endings normalized to \n** (746 lines, 0 `\r` remain; atomic .tmp→replace write). §A claim–evidence table remapped to v8 numbering per `claim_evidence_table.csv`: C1 Fig. 1/Table 7; C2 Fig. 8/11; C3 Fig. 12/16/Table 12; C4 Fig. 11/Table 8; C5 Fig. 18; C6 §6.8/Table 20; C7 §5.2/§6/Fig. 6; C8 §4.1 (Thm 2c/2d); C9 §3.4/§6.2/Table 3; C10 §6.6/Table 17; C11 §6.5/Tables 12–16/S11.2; C12 §4.2 (Thm 9)/§6.4/Appendix D. Same remap applied to v7-era cross-references in §B reviewer tables (Fig. 12/16/Table 12; Table 17; §3.4/6.2; Table 12) and §C (§5.5→§6.6, §5.4→§6.5, §5.2→§3.4, §5.4.3→§6.5 ×6, §5.3.1→§6.1.1 ×2, E18 first-mention sections → §6.3/6.5/6.8). "mean 35x" → "34.97×" (×2). Study scale → 73,696/34 (×2). Theorem-9 bound excess 2.7–3.5× → **3.1–4.2×** (×3, matching manuscript/claim table). Stale "Phase-2b full rerun remains future work" caveats → completed (729 rows, Section D). STATUS header now records the v8 remap. |
| `docs/theory/framework.md` | §5 appropriate-interpretation sentence → 73,696 rows / 34 canonical datasets. |
| `docs/results/analysis_summary.md` | Lemma 3 row → current release 34 canonical datasets / 73,696 rows. |
| `docs/results/hardware_validation.md` | Audit consequence 1 → 34 canonical datasets; stale "manuscript.md §15.16" → **§7.6 item 8 (noise-aware ceilings)**, with the EHW noise-model validation itself pointed at **§7.4**; appendix reference clarified (§C item 11 / §15.16 internal). |
| `docs/references/literature_review.md` | Study-scale figures 72,000+ → 73,000+ (×7) and 33 → 34 canonical datasets (×5: comparison table, contributions, §10 microbench discussion, conclusion); v1.2 changelog entry reworded to keep history without asserting the old caliber, plus a v1.3 (wave 3) resync line. |
| `docs/review/wave1/phase2b.md` | New §9 reconciliation note: this report's 2.7–3.5× vs the canonical **3.06–4.24×** (recomputed per instance from the 80 BV rows of `phase2b_full_validation_v8.csv`: min ratio 3.062, max ratio 4.238; manuscript rounds to 3.1–4.2×). Body left unchanged for provenance. |

## 3. Verification

- `scripts/reproduce_all.py --verify` → **PASS** (manifest + structural checks;
  run after all edits, 2026-07-21 02:28).
- Stale-caliber sweep (`grep -rn -E '72,682|33 canonical datasets|33 datasets'`
  over `*.md/*.csv/*.txt/*.json/*.py`, excluding `.bak*`, `archive/`,
  `_agent_work/`, `docs/review/`) → **0 hits**.
- EHW/SOTA stale-artifact sweep (`ehw_runs_smoke` as canonical, "60 rows" SOTA)
  same exclusions → **0 hits**.
- README Experiment Registry re-verified row-by-row against the manifest
  (26/26 match, EHW now 288).
- `docs/review/` files intentionally retain old figures as historical review
  records; `phase2b.md` now carries the §9 reconciliation note explaining the
  one quantitative divergence (2.7–3.5× vs canonical 3.06–4.24×).
- appendix.md: 746 lines before/after; 36 replacement patterns applied with
  expected-count assertions (all matched exactly); no `.tmp` residue.

## 4. Leftover / out-of-scope notes

1. `docs/review/wave3/consistency_sweep.md` §8 items 1–4 are all closed by this
   pass; item 5 (verify re-run) done → PASS; item 6 (README registry 26 rows vs
   manifest 34 datasets) stands as a documented curated-subset decision — every
   listed row matches the manifest.
2. `docs/manuscript/appendix.md` §B/§C still describe E19-ext as "8 of 16
   families with WCL mean reduction > 0" (counts CNOT_chain, saturated at 100%
   under both listings) while the manuscript/README say "7 of 16 gain from WCL"
   (advantage > 0). Different metrics, both arithmetically correct; flagged for
   a future wording pass, not changed here.
3. `docs/manuscript/appendix.md` §A lists C1–C12 only; v8-era claims C13–C17
   live in `claim_evidence_table.csv` and appendix Sections D–F (pointer added
   to the STATUS header).
4. README header still reads "Project Version 6.0.0 / 2026-07-14" — a version
   bump was out of this pass's scope.
