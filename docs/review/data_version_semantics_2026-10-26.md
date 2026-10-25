# Data version semantics after v15 (review-grade, 2026-10-26)

**Status:** review-grade documentation. Not hash-bound by any manifest and not
part of the canonical release chain.

**Why this file exists.** On 2026-10-25 the round-13 audit appended v12-v16
version semantics directly to `data/DATA_CANONICAL.md`. That file is bound in
`release/prepaper_release_manifest.json`, so the edit registered as release
drift, and the editor also rewrote every line with CRLF endings, turning a
~35-line content change into a 163-line diff. The edit was reverted on
2026-10-26 to restore the pinned hash; the semantic content is preserved here
instead. The canonical file stays the single authority for v2_fixed..v11; this
note extends its *Version meanings* list to the certified-landscape era.

## Version meanings, v12-v16

- **v12** - E38-E41 rewrite-exposure era (frozen MQT generation, exposure
  scale, requirement-to-evidence binding).
- **v13** - E42-E44 certified-landscape era: Quartz rule import (pinned
  1,474-rule library), landscape oracle, screening grid.
- **v14** - E45 selected-configuration panels: screening rerun, compact exact
  development (`e45_full_development`), IDA* escape (`e45_idastar_escape`),
  all at the frozen `h3_b64_s200k` / 30 s budgets, produced by the pre-fix
  `iter_legal_actions` engine.
- **v15** - integration layer: `e45_landscape_integration`
  (classification-complete derivation over the frozen v14 panels, 94 exact
  best costs including one IDA*-derived) and `e46_window_landscape`
  (76,236 window searches, 0 truncations). Produced by the pre-fix engine.
- **v16** - corrected-engine re-pin (2026-10-25, round-13 audit P1). After the
  successor-generation defect fix, the frozen v14/v15 packages are no longer
  byte-reproducible, so all three panels were re-run at the **exact frozen
  budgets** with the corrected engine:
  - `e45_full_development` (compact): 93 exact best costs (58 H-local + 35
    enumerated escapes), 34 witness-bounded, 1 no-witness truncation;
  - `e45_idastar_escape`: 69 exact, 1 truncated;
  - `e46_window_landscape`: 76,236 windows, 0 truncations, 39,572 escape rows;
  - `e45_landscape_integration`:
    `CLASSIFICATION_COMPLETE_WITH_RESOURCE_BOUNDARY` - 93 enumerated, 34
    bounded, and 1 resource-bounded cell `e39:b2f83603...` whose exact H-local
    claim is neither confirmed nor refuted at the frozen budgets, because the
    corrected engine generates strictly more successors per state.

  The producing engine source hashes are pinned per cell by the
  re-certification package
  `docs/review/science_boost/2026-10-25_engine_successor_fix/`.
  `release/v16_readiness_verdict.json` is the machine-readable verdict.

## Standing rules

1. v14 and v15 remain frozen as the released record. They are not rewritten
   and not re-derived.
2. Any claim that cites a landscape number must state which engine produced
   it. Pre-fix (v14/v15) and post-fix (v16) values differ on 8 of 128 cells,
   with a net of -14 gates.
3. `data/v16/` is a new version directory, not an edit of frozen data. It
   carries its own receipts; it does not enter `release/release_manifest.json`
   until the owner decides the re-pin.
4. Byte-level reproducibility of v14/v15 under the current engine is
   intentionally broken. That break is the evidence that the defect was real;
   do not "repair" it by reverting the engine.
