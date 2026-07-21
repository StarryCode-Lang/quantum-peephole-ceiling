# Wave 4 — ModelStretch: CNOT Saturation-Regime Intervention

**Date:** 2026-07-21
**Worker role:** 模型增强_ModelStretch
**Scope (exclusive):** `experiments/ceiling_model_repair.py`,
`data/v6/ceiling_repair/`, `docs/theory/universal_law_assessment.md`
(addendum only)
**Verdict: SUCCESS** on the pre-registered criterion (CNOT fold MAE
significantly reduced; pooled MAE / Pearson r not degraded).

## 1. Starting state (read-only reconnaissance)

- Published best config (`mechanism+single_stage_rf`, LOFO, seed 42):
  pooled MAE 0.0695 [0.0539, 0.0865], pooled r = 0.722 [0.666, 0.794],
  ρ = 0.847, R² = 0.393 — source:
  `data/v6/ceiling_repair/repair_summary.json` (2026-07-20).
- Known residual: held-out CNOT fold MAE = 0.7453 (systematic
  underestimation; CNOT is saturated at gate_reduction = 1.0 on all
  40 rows, std = 0).

## 2. Diagnosis (all facts computed on the canonical merge)

- With CNOT held out, the training target's 99th percentile is **0.4156**;
  exactly **one** saturated (y ≥ 0.99) training row exists (Oracle, n = 4).
  A RandomForest regressor predicts leaf-target averages and therefore
  cannot extrapolate to y = 1.0 for a feature signature absent from
  training → the residual is an **extrapolation failure**, not a
  missing-feature failure.
- The CNOT signature is unambiguous: Phase-1 action density exactly **0.5**
  (every gate in an adjacent cancellable inverse pair) vs max **0.0345**
  across all 530 non-CNOT circuits (>14× margin). Density 0.5 with
  self-inverse fraction 1.0 mechanistically implies full Phase-1 reduction
  (each pair removes 2 gates → 2·d ≥ 1).
- The alternative gate `structural_upper_bound ≥ 0.99` has exactly one
  false positive (RandomClifford, n = 4: bound 1.0, realized 0.345).

## 3. Interventions tested (LOFO, identical protocol/seed as Part 3)

| Variant | Pooled MAE [CI95] | Pooled r [CI95] | ρ | R² | CNOT fold MAE |
|---|---|---|---|---|---|
| V0 baseline = published best | 0.0695 [0.0539, 0.0865] | 0.722 [0.666, 0.794] | 0.847 | 0.393 | 0.7453 |
| V1 + saturation indicator features | 0.0674 [0.0524, 0.0836] | 0.761 [0.705, 0.830] | 0.853 | 0.440 | 0.7125 |
| V2 learned two-stage (classifier → regressor) | 0.0693 [0.0538, 0.0864] | 0.736 [0.690, 0.794] | 0.848 | 0.394 | 0.7453 |
| V3 rule gate: structural bound ≥ 0.99 → predict bound | 0.0176 [0.0130, 0.0225] | 0.974 [0.957, 0.987] | 0.853 | 0.948 | 0.0000 |
| **V4 rule gate: 2·Phase-1 density ≥ 1 → min(1, 2·d)** | **0.0172 [0.0129, 0.0218]** | **0.977 [0.963, 0.987]** | **0.853** | **0.954** | **0.0000** |
| V5 Ridge linear (extrapolating) | 0.0492 [0.0395, 0.0596] | 0.954 [0.912, 0.984] | 0.682 | 0.759 | 0.4495 |

V0 reproduces the published Table 18 row **exactly, including bootstrap
CIs** — protocol fidelity verified.

**Winner: V4.** CNOT fold MAE 0.7453 → 0.0000; pooled MAE 0.0695 → 0.0172;
pooled r 0.722 → 0.977; every non-CNOT fold numerically identical to
baseline (the gate fires only on CNOT rows). V3 rejected in favour of V4
due to its single false positive.

## 4. Negative results (recorded honestly)

- **V1 (indicator features):** barely helps the CNOT fold (0.7453 → 0.7125).
  Tree regressors average leaf targets; indicator columns do not grant
  extrapolation beyond the training target range.
- **V2 (learned two-stage):** complete failure on the target fold (0.7453
  unchanged). With one saturated training example (Oracle n = 4), the
  classifier never fires on the CNOT signature. The task's "classify
  saturated families first" hypothesis is **refuted under LOFO** — a
  learned saturation classifier cannot generalize from n = 1 positives.
- **V5 (Ridge linear):** extrapolates partially (CNOT fold 0.4495) and
  improves pooled MAE/r, but degrades Spearman (0.847 → 0.682); dominated
  by V4.

**Caveat:** the V4 gate is derived from the Phase-1 mechanism (not fitted),
but its *selection* was informed by the observed failure — a post-hoc model
revision validated on a single dataset. Manuscript wording should reflect
this if V4 is adopted.

## 5. Files changed / produced

| File | Action |
|---|---|
| `experiments/ceiling_model_repair.py` | Extended: new PART 4 (`--regime` flag), six LOFO variants, verdict logic. Original Part 1–3 flow untouched. |
| `data/v6/ceiling_repair/regime_intervention_results.csv` | **New.** Per-fold metrics, all 6 variants (90 rows). |
| `data/v6/ceiling_repair/regime_intervention_summary.json` | **New.** Diagnosis facts, pooled metrics + CIs, verdict, negative results. |
| `docs/theory/universal_law_assessment.md` | Addendum appended at end (old/new comparison table for §6.6). Backup: `universal_law_assessment.md.bak-20260721-084224`. |
| `docs/review/wave4/model_stretch.md` | **New.** This report. |

Old files (`repair_summary.json`, `repair_lofo_results.csv`,
`mechanism_features.csv`, `diagnosis.json`, `lofo_cv_*`) untouched —
verified by timestamps. Manuscript **not** modified (per instructions).
Manifest **not** regenerated (per instructions). No git operations.

## 6. Verification

- `python experiments/ceiling_model_repair.py --regime` runs clean
  (~2 min with cached features); verdict `success=True`.
- V0 reproduces published pooled MAE/r and both CI95s exactly.
- V4 per-fold table confirms zero collateral change on the 14 non-CNOT
  folds.
- Reproduction command:
  `/d/Downloads/miniforge3/python experiments/ceiling_model_repair.py --regime`

## 7. Hand-off items for the next wave

1. **§6.6 decision pending:** adopt V4 or keep V0. If adopted, update
   Table 18 best row (MAE 0.0172 [0.0129, 0.0218], r 0.977 [0.963, 0.987],
   ρ 0.853, R² 0.954), the CNOT-fold limitation in §6.6 prose and §7.6
   item 6 (fold MAE 0.745 → 0.000, closed by a deterministic mechanism
   gate — model becomes a hybrid rule + RF and must be described as such),
   and the quoted "MAE 0.0695 / r = 0.722" figures in the abstract, §1.3,
   and conclusion. The full old/new table is in the
   `universal_law_assessment.md` addendum.
2. **Unaffected limitations stand** regardless of the decision:
   family-mean regression (n = 15, r = 0.059), 11/15 undefined-Pearson
   folds, auxiliary classifier F1 = 0.075.
3. If the manuscript adopts V4, cite
   `data/v6/ceiling_repair/regime_intervention_summary.json` as the
   canonical source and keep the post-hoc-selection caveat.
