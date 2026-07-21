# Wave 4 — Finalize Report (收尾提交_Finalize)

**Date:** 2026-07-21
**Worker role:** 收尾提交_Finalize
**Scope:** `docs/manuscript/manuscript.md` (exclusive), plus repo-wide
number sync, E21 label fix, `.bak` cleanup, manifest regeneration,
verify/pytest/Docker/git.

---

## 1. Manuscript integration (docs/manuscript/manuscript.md)

### 1a. V4 ceiling model adopted (mechanism gate + RF hybrid)

All figures sourced from `data/v6/ceiling_repair/regime_intervention_summary.json`
via `docs/review/wave4/model_stretch.md` and the
`docs/theory/universal_law_assessment.md` addendum:

- **Table 18 (§6.6):** the old best row is demoted to
  "Mechanism-informed, single-stage (RF only)" (0.0695 / 0.722 / 0.847 /
  0.393, kept as the comparison baseline) and a new adopted row added:
  **Mechanism gate + RF hybrid — MAE 0.0172 [0.0129, 0.0218], pooled r
  0.977 [0.963, 0.987], ρ 0.853, R² 0.954**.
- **§6.6 prose:** describes the hybrid explicitly (deterministic gate
  `2·d ≥ 1 → min(1, 2d)` firing only on CNOT rows; RF on all other rows),
  records CNOT fold MAE 0.745 → 0.000 as a closed extrapolation failure,
  and keeps the **post-hoc-selection caveat** verbatim in spirit.
- **Abstract, §1.3, §8 conclusion:** "MAE 0.0695 / r = 0.722, modest"
  replaced by the V4 numbers with the hybrid description and the caveat;
  "CNOT-regime extrapolation fails" removed (now closed).
- **§7.5 limitation 6 rewritten:** CNOT limitation closed; the three
  unaffected limits retained (family-mean n = 15, r = 0.059; 11/15
  undefined-Pearson folds; auxiliary classifier F1 = 0.075).
- **§7.3 predictive-component sentence** aligned ("hybrid proof of
  concept whose rule component was selected post hoc").
- Status note (line 3) gained a **Wave-4 revision** entry (xix)–(xxii);
  item (iv)'s historical "729 rows" annotated "735 after the wave-4
  QuantumWalk n=8 fill".
- `docs/theory/universal_law_assessment.md` §4 predictive-model row
  updated to V4 with a pointer to the wave-4 addendum.
- `docs/manuscript/appendix.md` §A row C14, §C wave-4 update note, and
  `docs/manuscript/claim_evidence_table.csv` row C14 synced to V4
  (negative results V1/V2 recorded).

### 1b. Flagship listing-claim scoping

Per `docs/analysis/compiler_listing_audit.md` Sec. 6:

- **§1** (after the methodological recommendation): scope qualification
  added — the listing-model claims characterize *listing-based* peephole
  optimizers; DAG/moment-IR production compilers are flat-listing
  invariant because their windows are wire-relative (WCL-equivalent
  action space by representation).
- **§8 conclusion:** matching qualification added (for production
  compilers the actionable content is the taxonomy/escalation map, not
  relisting).
- **§3 (E19 practical implication):** the "WCL-like reordering is an
  open question" sentence replaced by the audit's answer.
- **§7.6 future-work item 5:** converted from "audit needed" to
  "audit completed; extend coverage".

### 1c. Phase-2b limitation update (729 → 735)

- §1.3 evidence, §5 experiment table (E25 row), §6.4 design paragraph,
  §7.5 item 13, §7.6 item 4: QuantumWalk n = 8 now covered (six rows,
  `fidelity_method=sampled200`, exact via structural-equality fast path;
  exact Operator fidelity ~133 s/row beyond the compute envelope).
- §6.4 pooled bootstrap restated from the refreshed grid:
  Phase-2a 9.3 % → 9.2 % [7.4, 11.1]; Phase-2b 46.5 % → **46.1 %
  [41.9, 50.1]** (source: `data/v8/phase2b_full/bootstrap_ci_v8.csv`).

### 1d. Figure caption / FDR count checks

- **fig04** rendered and eyeballed: real bars now (Universal hybrid
  ≈ 3.0 %, RandomClifford hybrid ≈ 5.0 %, CNOT inset Greedy 100 % /
  Commutation 0 %) — consistent with the caption; caption sharpened to
  "Phase-1 contributes materially only on CNOT chains (≤ 0.1 % mean
  elsewhere)" to match the small RandomClifford Phase-1 bar.
- "15 tests": no hard-coded FDR-family count anywhere in manuscript /
  supplementary (Figure 7 caption says "every registered test"); FDR
  family is now 16 tests in `analysis/figures/fdr_correction_results.csv`
  — no text change required.

## 2. Number sync (729 → 735; 73,696 → 73,702)

Applied in: `docs/manuscript/appendix.md` (incl. Section D header, data
note, fidelity-policy counts 663/60/6 → 663/60/12 with the QuantumWalk
exception, D.4 limitation 1, C13 pooled CI),
`docs/manuscript/claim_evidence_table.csv` (no row counts present; C14
updated per §1a), `docs/supplementary/supplementary_materials.md`
(inventory row + new SHA prefix `2a0a863a657ad8d1…`, total, reconciliation
note), `data/DATA_CANONICAL.md` (header, E10p2b-v2 row, totals),
`README.md` (overview, E10p2b-v2 row + pooled CI, total, status bullets,
plus Release ID → `q-research-8.0.0-wave4`),
`docs/theory/framework.md`, `docs/results/analysis_summary.md` (beyond
the named list, for whole-repo consistency).
Post-sync grep: the only remaining `729` is an arXiv identifier;
`73,696` remains only in wave-1..4 review history (excluded by design)
and in preserved historical comparison rows.

## 3. E21 fidelity_source label bug — code fix

`experiments/e21_ceiling_aware/run.py`:

- `fidelity_source()` now takes the run threshold
  (`max_exact_qubits`, default = module constant) instead of thresholding
  on `MAX_EXACT_FIDELITY_QUBITS` unconditionally; both call sites pass
  the run parameter `max_exact_fidelity_qubits`.
- Metadata now records the run parameter (was overwritten by the module
  constant at the `metadata.update` site).
- Verified: `fidelity_source(8, 1.0, 6)` →
  `base_optimizer_large_circuit_estimate`; `(4, 1.0, 6)` →
  `exact_average_gate_fidelity`; NaN → `unavailable`.
- Canonical CSV deliberately untouched; §7.5 item 15 annotated that the
  labeling logic is fixed for future runs.

## 4. Backup cleanup

All 27 wave-4 `*.bak-20260721-08*` files plus the 9 finalize-pass
`*.bak-20260721-09*` backups deleted. No `.bak-*` files remain in the
repo. Note: the manuscript status note references
`manuscript.md.bak-20260721-003505` as the preserved v7 draft — that
file does **not** exist on disk (pre-existing doc inaccuracy, flagged,
not silently "fixed" by creating a file).

## 5. Manifest regeneration + verify

- `scripts/generate_release_manifest.py --release-id q-research-8.0.0-wave4`:
  34 datasets, 73,702 rows; phase2b entry now `rows: 735`; first
  reproduction entrypoint is the pytest command.
- `scripts/reproduce_all.py --verify` → **PASS** (34/34 SHA-256 + row
  counts + structural checks; E26_phase2b_full_v8 SHA-256 OK, Rows: 735).
  The 11-experiment source-drift warnings are the pre-existing accepted
  ones documented in `docs/reproducibility.md`.
- Manifest committed twice per the repo flow: content commit on a dirty
  tree, then a clean-tree refresh commit so `git.dirty = false`.

## 6. Tests

`pytest tests/ -q --timeout=600` (three segments, foreground 300 s
limit): 126 + 125 + 47 = **298 passed, 0 failed**.

## 7. Docker

**Skipped (recorded, non-blocking):** no Docker CLI available in this
environment — `docker` not on PATH and no `C:\Program Files\Docker`
installation found. `docker build -t q-research .` could not be
attempted within the 10-minute box.

## 8. Commits

| Commit | Subject |
|---|---|
| `f0ba50a` | feat: wave-4 finalize — V4 hybrid ceiling model, Phase-2b grid fill, listing-claim scoping |
| `50019e4` | chore: refresh release manifest on clean tree (git metadata) |
| (this report) | docs: wave-4 finalize report |

## 9. Residual issues / notes

1. The manuscript status note's "v7 draft preserved as
   `manuscript.md.bak-20260721-003505`" pointer is stale (file absent);
   left as-is for owner decision (recreate the archive copy or strike
   the sentence).
2. The release manifest's `git.commit` lags one commit behind by
   construction (self-reference); documented repo flow.
3. Docker image build remains unverified — needs a machine with the
   Docker CLI/daemon.
4. `qiskit_pass_analysis.py` still regenerates Figures 15–17 with the
   legacy style on standalone execution (warns); removal deferred to
   post-release per code-hygiene hand-off.
5. Quantinuum bug report (sota_compiler_benchmark.md Sec. 12.5) remains
   a draft; submission is an owner decision (external action).
