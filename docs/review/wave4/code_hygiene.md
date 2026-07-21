# Wave 4 — Code Hygiene Report (Code Worker)

Date: 2026-07-21. Worker: code-hygiene (Code).
Scope (exclusive): `analysis/qiskit_pass_analysis.py`, `analysis/generate_figures.py`,
`experiments/e23_ag_canonical/run.py`, `scripts/generate_release_manifest.py`,
`data/v6/e21/metadata.json`. Timestamped backups (`*.bak-20260721-084007`) were
created next to every modified file before editing. `release/release_manifest.json`
was NOT touched (regeneration is reserved for the final wave).

## 1. `scripts/generate_release_manifest.py` — stale test entrypoint fixed

- Problem: `reproduction.entrypoints[0]` referenced the non-existent
  `tests/test_core.py` (the suite is pytest-based; there is no `test_core.py`).
- Fix: entrypoint changed to `conda run -n q-research python -m pytest tests/ -q`
  (line 195), matching the CI / `reproduce_all.py --tests` invocation.
- Verification: ran the generator with a temporary output path
  (`--output $TEMP/w4_verify/manifest_check.json`); it completed, listed
  34 datasets / 73,696 rows (identical totals to the current release manifest),
  and the first entrypoint is exactly the pytest command. No remaining
  `test_core.py` reference in either entrypoint list. Temp output deleted; the
  official manifest was not overwritten.
- Note: the manifest's `source_hashes` entry for
  `scripts/generate_release_manifest.py` is now stale by construction; the
  final-wave manifest regeneration will refresh it.

## 2. `analysis/qiskit_pass_analysis.py` — legacy figure functions deprecated

- Problem: the standalone SEM-style plotting functions duplicated Figures
  15–17 in parallel with `generate_figures.py` (two heads for the same
  figures).
- Fix (comments/wrappers only; data functions untouched):
  - Module docstring now carries a DEPRECATION NOTICE naming
    `analysis/generate_figures.py` as the canonical source of Figures 15–17
    (bootstrap 95% CI, Okabe–Ito palette, perceptually uniform colormaps).
  - `generate_fig15_waterfall`, `generate_fig16_heatmap`,
    `generate_fig17_interaction` each emit a `DeprecationWarning` via a new
    `_warn_deprecated_figure()` helper and carry a `.. deprecated::` docstring
    note. They remain callable for backward compatibility.
  - `main()` gained a comment steering manuscript figure production to
    `generate_figures.py`.
- Verification: module import is still side-effect free; data functions
  (`load_data`, `compute_*`) run warning-free; calling a deprecated figure
  function emits exactly one `DeprecationWarning`.

## 3. `analysis/generate_figures.py`

### 3a. E10 Universal Mann–Whitney U dead code — FIXED

- Located (file has shifted since the wave-1 report): the block now sits at
  ~line 957–966. Root cause confirmed against the canonical data
  (`data/v5/e10/e10_expanded_phase1_vs_phase2_20260613_131601.csv`): the code
  filtered `optimizer == 'Greedy'` / `'HybridCommuteRewrite'`, but the actual
  labels are `greedy_phase1` / `commutation_phase2` / `hybrid_phase1_2`. Both
  arrays were therefore empty and the test was silently skipped.
- Fix: literals corrected to `greedy_phase1` vs `hybrid_phase1_2` with an
  explanatory comment block.
- Effect (real, measured): the test now runs. On the canonical E10 Universal
  subset: raw p = 1.758666e-56, BH-adjusted p = 5.627732e-56, significant at
  q = 0.05, Cliff's δ = -0.805 [-0.860, -0.750], Hedges' g = -1.742
  [-1.973, -1.512]. The FDR family grows from 15 to 16 tests;
  `analysis/figures/fdr_correction_results.csv` and `fig08_fdr_correction.pdf`
  reflect this. The manuscript Figure 7 caption says "every registered test"
  (no hard-coded count), so no caption contradiction; the wave-1 review
  document mentions "15 tests" as a historical observation.

### 3b. fig04 optimizer-name mismatch (same bug class) — FIXED

- Found while fixing 3a: fig04 (`fig04_phase1_vs_phase2.pdf`) used the same
  non-existent labels `['Greedy', 'HybridCommuteRewrite']`. The previously
  published figure therefore showed all-zero main bars plus a CNOT inset
  listing raw labels — contradicting its own manuscript caption ("Phase-2
  dominates wherever reduction exists (except CNOT chains)").
- Fix: bars now use the canonical labels `greedy_phase1` /
  `hybrid_phase1_2` with a display-name map (`Greedy (Phase 1)`,
  `Hybrid (Phase 1+2)`, `Commutation (Phase 2)` for the inset).
- Verification: regenerated fig04 shows real values (e.g. Universal hybrid
  mean reduction 2.99%) and display labels; the figure now matches its
  caption.

### 3c. fig05 ↔ phase2_threshold_sensitivity pipeline — documented as independent by design

- Assessment: fig05 recomputes success rates inline from the canonical
  E1/E2/E3/E5 frames over the extended grid {0.1, 0.5, 1, 5, 10, 20, 30 %}
  with log-log presentation; `analysis/phase2_threshold_sensitivity/run.py`
  is a standalone audit pipeline over the protocol grid {1, 5, 10, 20 %}
  writing its own companion products (`threshold_sensitivity.csv/pdf/report.md`).
  Both compute the identical statistic (share of rows with `reduction >= t`)
  from the same canonical CSVs, so no numeric divergence is possible beyond
  the grid choice. Decision: independent by design — added an explanatory
  comment block at the fig05 section (per instructions, no new documentation
  files were created; `docs/reproducibility.md` untouched).

## 4. Full figure regeneration — PASS

- `python analysis/generate_figures.py` (miniforge interpreter) completed in
  ~37 s, exit 0, no errors. All 17 manuscript figures plus
  `fig08b_real_circuit_optimizer_comparison.pdf` regenerated, along with
  `statistical_summary.csv` and `fdr_correction_results.csv`. The only
  warning is the pre-existing, intentionally handled
  `ConstantInputWarning` for E2 (zero-variance reduction under LBL).
- `pytest tests/ -q`: 298 passed, 0 failed (295.8 s).
- `scripts/reproduce_all.py --verify`: 33/34 datasets OK; the single failure
  is `data/v8/phase2b_full/phase2b_full_validation_v8.csv` (SHA-256 mismatch
  vs the manifest). This file is OUTSIDE this worker's scope and was modified
  at 2026-07-21 08:43:39 by another concurrent wave-4 worker (its sibling
  `*.bak-20260721-084339` backups are not mine; my backups are stamped
  084007) after the manifest was generated (01:20). The failure is therefore
  a cross-worker/manifest-staleness issue for the final wave (manifest
  regeneration), not a regression from these changes.

## 5. `data/v6/e21/metadata.json` — provenance notes added (CSV untouched)

Two notes appended (validated JSON; `notes` array now 5 entries):

1. `fidelity_source` misnomer: for n_qubits ∈ {8, 10} the label
   `exact_average_gate_fidelity` is wrong — those runs passed `target=None`,
   so `fidelity = 1.0` is a placeholder. Evidence from the canonical CSV:
   all 560 rows with n ≥ 8 have fidelity exactly 1.0, including 98 rows with
   real gate reduction, while reduced rows at n ≤ 6 show fidelity < 1.0
   (min 0.9999999999999578). Root cause: `fidelity_source()` in
   `experiments/e21_ceiling_aware/run.py` thresholds on the module constant
   `MAX_EXACT_FIDELITY_QUBITS` (= 12) instead of the run parameter.
2. `max_exact_fidelity_qubits` = 12 recorded here is the module constant
   (`src/optimisation/constants.py`), written over the parameter value
   (run.py ~line 478 vs ~275). The threshold actually in effect for this
   dataset was the `run()`/argparse default of 6.

(Recording the mislabel in metadata only, per instructions; the labeling
code in `experiments/e21_ceiling_aware/run.py` is outside this worker's
scope — see Remaining issues.)

## 6. `experiments/e23_ag_canonical/run.py` — canonical CSV overwrite guard

- Added `_canonical_result_sha()` + `_guard_canonical_csv()`: before any
  write to the fixed canonical path, the freshly computed frame is compared
  with the existing file over its deterministic content (excludes
  `runtime_seconds` — wall-clock, legitimately different between identical
  reruns; floats rounded to 12 decimals to absorb CSV round-trip last-bit
  drift). Behavior:
  - file absent → write normally;
  - identical deterministic content → silent pass, file left byte-identical
    (mtime preserved);
  - different content → loud stderr warning with both SHA-256 digests and
    first differing column, then `sys.exit(1)`; nothing is written.
- Verification (sandboxed with `PROJECT_ROOT` redirected to a temp dir; the
  real `data/v7/e23/` was never touched): run 1 wrote the CSV; run 2 passed
  silently (byte-identical SHA, unchanged mtime — confirming cross-run
  determinism of the scientific columns); run 3 against a deliberately
  corrupted CSV exited with code 1, correctly identified `reduction` as the
  differing column, and left the corrupted file untouched.
- Deterministic behavior of the experiment itself is unchanged (same seeds,
  same results; matching rate = 1.0000 in all sandbox runs).

## Changed files (this worker)

- `scripts/generate_release_manifest.py` (1 line: entrypoint)
- `analysis/qiskit_pass_analysis.py` (deprecation docstrings/warnings only)
- `analysis/generate_figures.py` (MWU fix + comments; fig04 label fix; fig05 comment)
- `experiments/e23_ag_canonical/run.py` (overwrite guard)
- `data/v6/e21/metadata.json` (2 provenance notes)
- Regenerated products: `analysis/figures/fig01–fig17*.pdf`, `fig08b*.pdf`,
  `statistical_summary.csv`, `fdr_correction_results.csv` (substantive
  changes: fig04, fig08, fdr CSV; the rest differ only by PDF metadata
  timestamps)
- Backups: `*.bak-20260721-084007` next to each of the 5 edited files

## Remaining issues / hand-offs

1. `data/v8/phase2b_full/phase2b_full_validation_v8.csv` SHA mismatch vs the
   manifest (see §4) — final wave must decide: accept the concurrent worker's
   new CSV and regenerate the manifest, or restore.
2. FDR family grew 15 → 16 tests (new E10 Universal MWU). Check the
   manuscript/supplement for any hard-coded "15 tests" statement (none found
   in `docs/manuscript/manuscript.md`; the mention in
   `docs/review/wave1/statistical_rigor.md` is a historical record).
3. fig04 content changed from (broken) zero bars to real data; it now
   matches its manuscript caption — no text change expected, but the
   integration worker may want to eyeball it.
4. The E21 `fidelity_source` labeling bug (label function uses the module
   constant 12 instead of the run parameter) is fixed in documentation only;
   the code fix belongs to whoever owns `experiments/e21_ceiling_aware/run.py`.
5. `qiskit_pass_analysis.py` standalone execution still regenerates Figures
   15–17 with the legacy style; it now warns. Consider removing the legacy
   plotting path entirely after the release.
