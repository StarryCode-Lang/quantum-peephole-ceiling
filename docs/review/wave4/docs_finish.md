# Wave 4 — Docs Finish Report (文档收尾_Docs)

**Date**: 2026-07-21
**Scope**: README.md, docs/manuscript/appendix.md, docs/manuscript/manuscript.md (small authorized edits only), data/DATA_CANONICAL.md, docs/reproducibility.md
**Backups** (created before any edit, timestamp 20260721-083637):

- `README.md.bak-20260721-083637`
- `docs/manuscript/appendix.md.bak-20260721-083637`
- `docs/manuscript/manuscript.md.bak-20260721-083637`
- `data/DATA_CANONICAL.md.bak-20260721-083637`
- `docs/reproducibility.md.bak-20260721-083637`

## Completed items

1. **README version header** — `Project Version 6.0.0 / 2026-07-14` → `8.0.0 / 2026-07-21`, and added `Release ID: q-research-8.0.0-wave3` (verified against `release/release_manifest.json:263`).

2. **Unified WCL-benefit count** — single phrasing adopted everywhere: *"7 of 16 families gain from WCL (8 of 16 counting the saturated CNOT_chain family)"*. Applied at:
   - `manuscript.md` §7.5 item 2 (was "7 of 16 gain, 9 show no benefit");
   - `appendix.md` Reviewer-Risk Checklist row (was "WCL mean reduction > 0 on 8 of 16");
   - `appendix.md` §7 E19 update note (same wording, per-family numbers preserved).
   Manuscript §6.2 already used the consistent "Seven families … / remaining nine" framing and needed no change.

3. **Effect-size protocol aligned with implementation** (manuscript §5.2, ~line 398). Old text declared "Cliff's delta + Cohen's d (Glass's Delta when pooled SD is zero)"; the implementation computes Cliff's δ + Cohen's d + Hedges' g + Glass's Δ (`analysis/phase1_statistics/effect_size.py`, verified by reading `glass_delta()`). New text: Cliff's δ, Hedges' g (small-sample-corrected Cohen's d), and Glass's Δ (baseline-SD denominator, used when pooled SD is zero), with Cliff's δ primary for near-zero-variance comparisons — matching README Statistical Protocol item 2.

4. **New limitation §7.5 item 19** — E29 RLS −176.5% circuit growth attributed to the cancellation-potential reward term in `BaseOptimizer._fitness` (`src/optimisation/base.py:781-789`, verified in source: `potential_bonus = 0.01 * cancellable * penalty`); INSERTION pairs keep fidelity at 1.0 (appendix F.2 confirms "gate-count inflation at fidelity = 1.0"), so this is a fitness-function design effect, not an optimization failure. SA/GA inflation (−22.2%/−8.3%) noted as the same mechanism at smaller magnitude.

5. **Glass's Δ footnote** (manuscript §5.2, footnote `^1`). Both numbers verified against real artifacts:
   - strict baseline-SD value Δ = 6.52 / 6.44: `docs/review/wave1/data/effect_sizes.csv` (Random vs IQP / Random vs UCCSD);
   - production fallback value 0.578 / 0.536: `analysis/figures/effect_sizes.csv`;
   - fallback trigger verified in code (`control='auto'`: baseline y SD preferred, group-1 SD used only when baseline variance is exactly zero).
   Footnote states the swing is a denominator artifact and names Cliff's δ as authoritative on such rows.

6. **DATA_CANONICAL.md Known Issues item 7** — `success` column is uninformative. **Task brief corrected against ground truth** (full-column scan run this wave, `/d/Downloads/miniforge3/python`):
   - E1–E4: 100% `False`; **E5 is NOT constant** — 5,999 `False` + 1 `True`;
   - v6/v7/v8 datasets carrying the column: **10 datasets** (E19, E25, E29 smoke+full, E10p2b, E10var, E10p2b-full, E19-ext, E22, E10p2b-v2), all 100% `True` — not the 3 (E19/E20/E21) named in the brief; E20/E21/E23/E24/E26/SOTA/CeilingRepair/EHW have **no** `success` column.
   The entry was written to the verified facts ("near-constant", with the E5 exception and the 10-dataset list explicit).

7. **reproducibility.md Current limitations** — new bullet on "source file(s) modified since data generation" warnings. **Task brief corrected against ground truth**: live `--verify` run this wave shows the warning on **11 experiments (E12–E21 and E25)**, 10–11 `src/optimisation/` files each — not only E12/E13/E21/E25. Bullet records the full set, the accepted-as-is rationale, and that canonical data are anchored by manuscript numbers and intentionally not rerun.

8. **Appendix §A claim-evidence table** — rows C13–C17 added after C12, content synced with `docs/manuscript/claim_evidence_table.csv` rows 14–18 and pointing to Sections D (C13), §6.6 (C14), §7.4/7.5 (C15), and Section F (C16, C17).

## Verification

- `scripts/reproduce_all.py --verify` → **PASS** (run after all edits; SHA-256 + row counts + structural checks OK; the 11 source-drift warnings are the pre-existing accepted ones documented in item 7 above).
- Grep-level consistency check: no remaining "8 of 16" without the "7 of 16 gain" qualifier in manuscript.md / appendix.md (archive/ copies untouched by design).
- All numeric claims in the new text traced to canonical CSVs, `effect_size.py` source, or wave-1 audit artifacts (see items 5–7).

## Files changed

| File | Change |
|------|--------|
| `README.md` | version header → 8.0.0 / 2026-07-21 + Release ID line |
| `docs/manuscript/manuscript.md` | §5.2 effect-size protocol + Glass's Δ footnote; §7.5 item 2 WCL count; new §7.5 item 19 (E29 fitness artifact) |
| `docs/manuscript/appendix.md` | 2× WCL count unification; §A table +C13–C17 |
| `data/DATA_CANONICAL.md` | Known Issues +item 7 (`success` column, corrected facts) |
| `docs/reproducibility.md` | Current limitations +source-drift bullet (corrected experiment set) |

## Residual issues / notes for the wrap-up wave

- Brief-vs-truth deltas (both corrected in place, flagged here for the record): the `success`-column brief (8 datasets, E5 constant) and the source-drift brief (4 experiments) did not match the repository; the written docs follow the verified facts.
- Manuscript line count grew by ~4 lines (footnote + limitation 19 + C13–C17 are appendix); no table/figure numbering was touched.
- The `^1` footnote syntax is new to manuscript.md (the file had no prior `[^…]`/`^n` footnotes); if the eventual LaTeX/typesetting pipeline requires a different convention, this is the single spot to convert.
- No git operations performed (per wave rules); five `.bak-20260721-083637` backups remain on disk for the final cleanup wave to remove.
