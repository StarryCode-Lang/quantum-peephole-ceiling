# Environment / Figure / MEDIUM Fixes Log

**Date**: 2026-06-17
**Scope**: Tasks 28 (env sync), 29 (vector figures), 30 (MEDIUM fixes)
**Constraint**: File modifications only — no experiments or tests were executed.

---

## Task A — Sync `requirements.txt` / `environment.yml` + unify Python version (Task 28)

### A.1 Divergence found

| Package        | `requirements.txt` | `environment.yml` |
|----------------|:---:|:---:|
| qiskit         | pip | pip |
| pytket         | pip | **missing** |
| pytket-qiskit  | pip | **missing** |
| pytest         | **missing** | conda |

> Note: the task brief described the pytket/pytest divergence in the opposite
> direction. The actual state was: `pytket`/`pytket-qiskit` were in
> `requirements.txt` but absent from `environment.yml`; `pytest` was in
> `environment.yml` but absent from `requirements.txt`. Both were synced so
> each file now mirrors the other.

### A.2 Changes

**`environment.yml`**
- `python=3.12.12` → `python=3.10` (unified to 3.10 as specified).
- Added `pytket>=1.28.0` and `pytket-qiskit>=0.50.0` to the `pip:` subsection
  (these are pip-installable; kept alongside `qiskit` for consistency).

**`requirements.txt`**
- Added `pytest>=7.0` (mirrored from the conda deps so non-conda users can
  run the test suite).

### A.3 Python version unification (3.12 → 3.10)

All prose references to Python 3.12 were updated to 3.10:

- `PROJECT_SUMMARY.md` line 6: `Python 3.12.12` → `Python 3.10`.
- `docs/06_manuscript/v5_full_manuscript_part2.md` line 262: `Python 3.12` → `Python 3.10`.
- `docs/05_supplementary/supplementary_materials.md` §S6.3 (line 400): `conda create -n q-research python=3.12` → `python=3.10`.
- `docs/05_supplementary/supplementary_materials.md` §S7.3 (line 474): embedded `environment.yml` snippet `python=3.12` → `python=3.10`.

> `release/release_manifest.json` deliberately **keeps** `python: "3.12.12"` in
> its `environment` block: that field is a historical snapshot of the release
> environment actually used at build time, not a forward-looking spec.
> Rewriting it would invalidate the recorded SHA-256 hashes.

### A.4 CI switched to conda

**`.github/workflows/ci.yml`**
- Replaced `actions/setup-python` + `pip install -r requirements.txt` with
  `conda-incubator/setup-miniconda@v3` consuming `environment.yml` and
  activating the `q-research` env. The `test` job steps now run under
  `shell: bash -l {0}` so the conda env is active.
- Matrix / lint `python-version` changed from `"3.12"` to `"3.10"`.
- The `docker-build` job was unchanged: the `Dockerfile` already does
  `conda env create -f environment.yml`, so it was already conda-based.

---

## Task B — Vector figures + blank-figure fixes (Task 29)

### B.1 `analysis/generate_figures.py` — PDF savefigs are now truly vector

All 12 `plt.savefig(..., '.pdf', ...)` calls previously used `dpi=300`, which
only affects rasterised elements and produced PDFs whose vector content was
limited. They were switched from

```python
plt.savefig(OUTPUT_DIR / 'figXX.pdf', dpi=300, bbox_inches='tight')
```

to

```python
plt.savefig(OUTPUT_DIR / 'figXX.pdf', format='pdf', bbox_inches='tight')
```

The `format='pdf'` form makes the vector intent explicit and avoids implying
a raster DPI. PNG copies (`dpi=300`) are still written for quick previewing.

Figures updated: fig01, fig02, fig03, fig04, fig05, fig06, fig07, fig08,
fig11, fig12, fig13, fig14.

### B.2 Figure 5 — log-scale zero-value masking

`fig05_threshold_sensitivity` plots success-rate (%) on a log y-axis. When no
trial meets a threshold the success rate is exactly 0, and `log(0)` is
undefined, so matplotlib silently drops those points. The plotting loop now
masks zero values with `np.nan` so gaps are visible rather than invisible:

```python
success_rates_plot = [s if s > 0 else np.nan for s in success_rates]
ax.plot([t * 100 for t in thresholds], success_rates_plot, 'o-', ...)
```

### B.3 Blank-figure annotations ("No observable effect")

Figures 1–3 display the structural-ceiling zero-reduction baseline for Phase 1
optimizers on random circuits. Figure 1 already carried an explanatory
annotation. Equivalent "No observable effect" annotations were added to the
panels that could otherwise be misread as blank/broken charts:

- **Figure 2 right panel** (E3 success rate vs qubit count): if
  `success_rate` is identically 0 across all qubit counts, a centred
  `"No observable effect (success rate = 0% across all qubit counts)"`
  annotation is drawn.
- **Figure 3 left panel** (E4 mean reduction by optimizer): if
  `mean_reduction` is identically 0 for all optimizers, a centred
  `"No observable effect (mean reduction = 0% for all optimizers)"`
  annotation is drawn.

Both annotations are gated on the actual data being zero so they do not
appear when the panels contain real signal.

### B.4 `scripts/convert_png_to_pdf.py` — raster-embed → vector regenerate

The old implementation read each PNG via `matplotlib.image.imread` and
re-drew it into a PDF canvas with `imshow`. The resulting PDF contained a
300-DPI bitmap as its only content — i.e. a raster-embedded PDF, unsuitable
for publication submission.

The script was rewritten to regenerate the PDFs by re-executing
`analysis/generate_figures.py` (via `runpy.run_path`). Because
`generate_figures.py` now writes PDFs with `format='pdf'`, the output is true
vector graphics. The script also reports per-file size deltas and tags any
legacy raster-embedded PDFs it detects via a `/DCTDecode`/`/Image` heuristic.

---

## Task C — MEDIUM-priority batch fixes (Task 30)

### C.1 Hardcoded timestamps in `scripts/phase5_*.py`

The three phase5 scripts (`phase5_optimize_or_skip.py`,
`phase5_feature_extraction.py`, `phase5_ceiling_analysis.py`) referenced
input CSVs by their full timestamped filenames (e.g.
`e10_phase1_vs_phase2_20260611_191634.csv`). These are *input data-file
references*, not output identifiers, so blindly replacing the date with
`datetime.now().strftime("%Y%m%d")` would break file resolution (no file
with today's date exists).

A `_latest_csv(directory, prefix)` helper was added to each script. It globs
for `{prefix}*.csv`, prefers `_full_` runs over `_smoke_` runs, and returns
the latest match. All `DATA_FILES` / `FILES` entries now resolve dynamically,
so freshly generated timestamped data files are picked up automatically.

This mirrors the `load_latest_csv` pattern already used in
`analysis/generate_figures.py`.

### C.2 std vs SEM comments in `analysis/`

The codebase uses sample standard deviation (`std`, ddof=1) in several places
where the statistically correct quantity for "mean ± error" reporting would
be the standard error of the mean (SEM = std / sqrt(n)). Rather than change
the values (which would alter published figures/CSVs), clarifying comments
were added at the three key sites:

- `analysis/generate_figures.py` Figure 1 `fill_between` band: comment notes
  it visualises trial-to-trial spread (std), not SEM, and how to switch.
- `analysis/generate_figures.py` statistical-summary table `Std_Reduction_%`
  column: comment notes std is reported (not SEM) for schema backwards
  compatibility.
- `analysis/qiskit_pass_analysis.py` per-family error bars: comment notes
  std is used and that SEM would be correct for mean ± error reporting.

### C.3 `tests/test_commutation_bug_reproduction.py` — unittest discovery

The file had 5 `demo_*` functions and 0 `test_*` functions, so
`python -m unittest` could not discover it. A `TestCommutationBugReproduction`
`unittest.TestCase` subclass was added that wraps each demo as a `test_*`
method (delegating to the existing `demo_*` functions, which already contain
the `assert` statements). An aggregate `test_all_demos` method was also
added. The original `demo_*` entry points and the `__main__` demo path are
preserved; `python tests/test_commutation_bug_reproduction.py --unittest`
now also runs the unittest harness.

### C.4 `LICENSE` — vague copyright holder

`Copyright (c) 2026 Q-research Team` → `Copyright (c) 2026 Q-research Project
Contributors`. The new holder is more specific and follows the convention
used by many open-source projects for collective attribution.

### C.5 Held-out / isolation in `release/release_manifest.json`

The manifest already contained `HELDOU` and `ISOLATION` entries, but with
opaque IDs that did not explain they are supplementary datasets outside the
core `E##` experiment series. A `description` field was added to each entry
explicitly noting that these are held-out / Qiskit-pass-isolation datasets
tracked for provenance even though they sit outside the main experiment
registry. (JSON has no comments, so a `description` field is the canonical
way to annotate.)

### C.6 E19/E20 experiment-ID conflict

The experiment registry uses `E19` for *Statistical Power Analysis* and
`E20` for *Reproducibility Audit*, while `experiments/e19_wcl_listing/` and
`experiments/e20_multi_compiler_full/` reuse the same IDs for *WCL
preprocessing* and *Multi-Compiler full comparison* respectively. The
manuscript already disambiguates these as `WCL-E19` and `MC-E20`.

The `EXPERIMENT_ID` constants were updated to match:
- `experiments/e19_wcl_listing/run.py`: `EXPERIMENT_ID = "E19"` → `"WCL-E19"`.
- `experiments/e20_multi_compiler_full/run.py`: `EXPERIMENT_ID = "E20"` → `"MC-E20"`.

Both files use `EXPERIMENT_ID` consistently via the variable, so all
downstream metadata records now carry the disambiguated IDs. Comments
pointing to the manuscript notes (`docs/06_manuscript/v5_full_manuscript_part3.md`)
were added for traceability.

---

## Files modified

| File | Task |
|------|------|
| `requirements.txt` | A |
| `environment.yml` | A |
| `.github/workflows/ci.yml` | A |
| `PROJECT_SUMMARY.md` | A |
| `docs/06_manuscript/v5_full_manuscript_part2.md` | A |
| `docs/05_supplementary/supplementary_materials.md` | A |
| `analysis/generate_figures.py` | B, C.2 |
| `scripts/convert_png_to_pdf.py` | B.4 |
| `scripts/phase5_optimize_or_skip.py` | C.1 |
| `scripts/phase5_feature_extraction.py` | C.1 |
| `scripts/phase5_ceiling_analysis.py` | C.1 |
| `analysis/qiskit_pass_analysis.py` | C.2 |
| `tests/test_commutation_bug_reproduction.py` | C.3 |
| `LICENSE` | C.4 |
| `release/release_manifest.json` | C.5 |
| `experiments/e19_wcl_listing/run.py` | C.6 |
| `experiments/e20_multi_compiler_full/run.py` | C.6 |

## Files NOT modified (deliberate)

| File | Reason |
|------|--------|
| `release/release_manifest.json` `environment.python` field | Historical snapshot of the build env; rewriting would invalidate recorded SHA-256 hashes. |
| `Dockerfile` | Already uses `conda env create -f environment.yml`. |
| `experiments/e19_*/run.py` / `experiments/e20_*/run.py` print strings (`"E19 complete"`) | Cosmetic stdout messages; the actual `experiment_id` written to metadata is now disambiguated via the `EXPERIMENT_ID` variable. |
