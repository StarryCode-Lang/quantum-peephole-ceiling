# Review Wave-1 — Figures & Visualization (worker: 图表工程师_Figs)

Date: 2026-07-20. Scope: `analysis/generate_figures.py`, `analysis/figures/**`,
`docs/figures_regeneration.md` (new). Manuscript body left untouched (read-only).

## 1. What was done

### (1) All 17 figure PDFs regenerate from `analysis/generate_figures.py`

- **Baseline audit**: the script already produced fig01-fig14 + fig08b (14 PDFs)
  with no hard-coded paths (paths resolve via `src/config.py`), no missing
  imports, and canonical data selection (`load_latest_csv`, full-mode preferred;
  selections verified against `data/DATA_CANONICAL.md`, incl. the E12
  `nocoupling` fair-comparison file).
- **Gap closed**: fig15-fig17 previously regenerated only from
  `analysis/qiskit_pass_analysis.py`. They are now generated inside
  `generate_figures.py`, reusing that module's data helpers (read-only import;
  the module has no import-time side effects), so all 17 PDFs + 4 companion
  CSVs come from one entry point. The older SEM-based plotting functions in
  `qiskit_pass_analysis.py` remain for compatibility but are no longer the
  canonical figure source.
- **Stale data-reference fix (real bug)**: fig10's fuzzy column match selected
  `ceiling_gap` (identically zero) as the "Ceiling Proxy" series and
  `structural_upper_bound_reduction` as "Observed Max" — labels and data were
  both wrong. Now uses the explicit canonical columns
  `structural_upper_bound_reduction` (proxy) vs `observed_best_reduction`
  (observed), with a data-driven tightness annotation (max |ceiling gap| =
  2.78e-17 across 56 circuits).

### (2) Per-figure quality gate

- **Error bars — bootstrap CI, not std**: fig01-04/12/14 already used
  bootstrap 95% CI (prior M-20 work, verified). Upgraded in this wave:
  fig15 (was **SEM** in `qiskit_pass_analysis.py`), and fig08b/fig09/fig10
  (previously **no error bars at all**). No figure uses plain std anymore.
  Implementation note: `bootstrap_ci_errors()` is now a vectorized percentile
  bootstrap (B = 10,000, seed 42) — statistically equivalent to
  `phase1_statistics.bootstrap.bootstrap_ci` but without its convergence
  diagnostic (~3x cost); this cut full regeneration from >290 s (timed out)
  to ~51 s.
- **Colorblind-safe palette**: all ad-hoc hex colors
  (`#2E86AB/#A23B72/#F18F01/#C73E1D/#5DA9C2/#6A4C93`) replaced by the
  Okabe-Ito palette (Wong 2011) via semantic constants
  (`C_PRIMARY` ... `C_ACCENT`, `CB4`).
- **Colormaps**: fig11 `RdYlGn` (worst choice for CVD) → `cividis`;
  fig08b `husl` → single palette color; fig13 `tab20` → 8-color Okabe-Ito
  cycle x 2 distinct markers (resolves M-21 with redundant encoding);
  fig17 `Blues`/`Greens` → `cividis`/`viridis`; fig16 already `cividis`.
- **LaTeX-capable axis labels**: mathtext enabled project-wide
  (`mathtext.fontset = dejavusans`); verified rendering of `$\alpha$` (fig08)
  and `$\{cx, id, rz, sx, x\}$` (fig09 annotation).
- **Print-legible fonts**: unified `rcParams` (label 11 pt, ticks 9 pt,
  legend 9 pt); previously fig08b/fig09/fig10 used unstyled defaults.
  `pdf.fonttype = 42` added (TrueType embedding — journals reject Type-3).
- **Multi-panel consistency**: fig15-17 rewritten in the fig01-14 idiom
  (same title style, palette, CI annotation); fig15 legend given headroom
  (`ylim` 128) so it no longer overlaps the 100% CNOT-chain bars; fig09
  annotation repositioned clear of clipped-bar labels.
- **fig09 honesty fix**: E12's QuantumWalk/Grover means reach -5,761%
  (basis-translation overhead). Raw-scale plotting made the other 13 families
  unreadable; bars are now clipped to [-110, 110], hatched, annotated with
  true values, and explained in-figure (broken-range convention).

### (3) Manuscript figure-reference cross-check

| Reference | Location | PDF exists? |
|-----------|----------|-------------|
| *(none)* | `docs/manuscript/manuscript.md` (active, 792 lines) | — **zero `Fig.`/`Figure N` references found** (verified by regex; hits for "fig" substrings are `configurable`/`fidelity` false positives) |
| Fig.1, 4, 12, 13, 14, 17 | `docs/manuscript/appendix.md` | all present (fig01, fig04, fig12, fig13, fig14, fig17) |
| Fig.1, 4, 12, 13, 14, 17 | `docs/manuscript/claim_evidence_table.csv` | all present |
| *(none)* | `docs/manuscript/_cross_validation.md`, `_e18_extension.md`, `sections/*.md`, `docs/supplementary/**` | — |

**Missing PDFs: none** — every figure referenced by any active manuscript
file has a corresponding regenerated PDF.

### (4) Numbering-order check

- Active manuscript body: no references, so no ordering to validate.
- `appendix.md` / `claim_evidence_table.csv`: first-mention order is
  Fig.1 → Fig.4 → Fig.13 → Fig.12 → Fig.17 → Fig.14 — **non-monotonic**
  (Fig.13 cited before Fig.12; Fig.14 last). This follows claim numbering
  (C1-C5), not figure order; recorded as an observation for the integration
  worker, not an error in the figure set.
- Archived v6 manuscript (`docs/manuscript/archive/manuscript_v6_archived.md`)
  references Figure 1-17 with non-monotonic first-mention order (Fig.11 in the
  abstract; Fig.10 and Fig.14 first appear late). Archived — no action.
- **Unreferenced by any active manuscript file**: Fig.2, 3, 5, 6, 7, 8, 8b,
  9, 10, 11, 15, 16 (PDFs all exist and regenerate).

### (5) Regeneration documentation

New file `docs/figures_regeneration.md`: exact command, expected runtime,
all inputs (canonical data files), code dependencies, per-figure I/O table,
style conventions, verification checklist, backup policy.

### (6) Full regeneration run

- Old outputs backed up to `analysis/figures/_bak-20260720/` (26 files:
  17 PDFs + 9 CSVs) before re-running.
- `/d/Downloads/miniforge3/python analysis/generate_figures.py` → **exit 0,
  50.6 s**, all 17 PDFs + `statistical_summary.csv`,
  `fdr_correction_results.csv`, `e4_effect_sizes.csv`,
  `qiskit_pass_analysis_summary.csv` regenerated with fresh timestamps.
- Log clean apart from the intentional E2 `ConstantInputWarning`
  (zero-variance reduction; p treated as 1.0 — pre-existing honest handling).

## 2. Verification (spot checks, rendered via PyMuPDF)

| Figure | Check | Result |
|--------|-------|--------|
| fig09 | bootstrap CI bars + Okabe-Ito palette + clipped/hatched QuantumWalk & Grover with true-value annotations + mathtext `$\{cx,id,rz,sx,x\}$` | PASS |
| fig10 | explicit proxy/observed columns (was all-zero mislabel), bootstrap CI bars, tight-proxy annotation | PASS |
| fig11 | cividis replaces RdYlGn; ceiling hatching still legible | PASS |
| fig15 | SEM → bootstrap 95% CI bars; bluish-green full-pipeline reference; legend no longer overlaps bars | PASS |
| fig13 | color x marker redundant encoding for 15 families | PASS |
| fig17 | cividis/viridis panels, consistent style | PASS |
| fig01 | zero-effect baseline + CI band + data-driven annotation | PASS |

(Preview PNGs were rendered to a temp dir, inspected, then removed; PDFs in
`analysis/figures/` are the deliverables.)

## 3. Changed files

| File | Change |
|------|--------|
| `analysis/generate_figures.py` | wave-1 overhaul (palette, rcParams, vectorized bootstrap CI, fig08b/09/10 rewrites, fig10 column fix, fig11/13 colormap fixes, fig15-17 integration) |
| `analysis/figures/*.pdf` (17) | regenerated |
| `analysis/figures/{statistical_summary,fdr_correction_results,e4_effect_sizes,qiskit_pass_analysis_summary}.csv` | regenerated |
| `analysis/figures/_bak-20260720/` | pre-run backup (new dir) |
| `docs/figures_regeneration.md` | new regeneration guide |
| `docs/review/wave1/figures.md` | this report |

## 4. Validation commands

```bash
PY=/d/Downloads/miniforge3/python
$PY -m py_compile analysis/generate_figures.py   # SYNTAX OK
$PY analysis/generate_figures.py                 # exit 0, ~51 s, 17 PDFs listed
```

## 5. Open gaps (handoff)

1. **Active manuscript has zero figure references** — every Fig./Figure
   citation lives in `appendix.md` / `claim_evidence_table.csv`; the 792-line
   `manuscript.md` cites none. 11 of 17 figures are unreferenced in active
   files. Integration worker must wire figure citations into the manuscript
   body (out of my scope: manuscript is read-only this wave).
2. **E16 window sizes**: canonical CSV contains w ∈ {2, 5, 10, 20} only;
   appendix/claim table state w ∈ {2, 5, 10, 20, 50}. Data-vs-manuscript
   mismatch — hand to data/integration worker (fig13 faithfully plots the
   four available sizes).
3. **`qiskit_pass_analysis.py` still contains the old SEM-based fig15**
   plotting code (read-only for me). Both scripts produce fig15-17;
   `generate_figures.py` is now canonical. Recommend the analysis worker
   deprecate or align those plotting functions to avoid future divergence.
4. **E12 negative reductions** are a data-semantics issue (basis-translation
   overhead in the fair no-coupling-map file), visualized honestly via
   clipping + annotation in fig09; any data-side fix belongs to the data
   worker.
5. Figures 15-17 cover only 5 families / 4 passes (100 rows) — limited by
   the pass-isolation dataset, not by plotting.
