# Wave-1 Review — Statistical Rigor

**Reviewer role:** Statistical Rigor worker (统计审查员_Stats)
**Date:** 2026-07-20
**Scope:** README 6-point statistical protocol, figure error bars, threshold-sensitivity wiring, Known-Limitation quantification, manuscript statistical claims, outlier scan, E18 survivor-bias consistency.
**Data products (all regenerated this review):** `docs/review/wave1/data/{effect_sizes.csv, effect_sizes_summary.md, power_audit.csv, fidelity_distribution.csv, limitations_impact.csv, outlier_scan.csv}`

---

## 1. README 6-point statistical protocol — verification matrix

| # | Protocol item | Status | Implementation (file:line) | Applied at | Tests |
|---|---------------|--------|----------------------------|------------|-------|
| 1 | BH-FDR q = 0.05 | ✅ implemented + applied | `analysis/phase1_statistics/multiple_comparison.py:16` (Benjamini–Hochberg), `analysis/phase1_statistics/core.py:39` (pipeline integration) | `analysis/generate_figures.py:961` writes `analysis/figures/fdr_correction_results.csv` (15 tests, latest regen 2026-07-20) | `tests/test_statistical_analysis.py` (BH known-answer + edge cases) |
| 2 | Effect sizes: Cliff's δ, Cohen's d, Hedges' g, Glass's Δ | ✅ all four implemented (Glass's Δ **added this review**) | `analysis/phase1_statistics/effect_size.py:14` (Cliff's δ), `:83` (Cohen's d), `:422` (Hedges' g), `:152` (**new** `glass_delta`) | `analysis/generate_effect_sizes.py:27,92,121` (compute), `:262` (CSV column), `:321,346` (summary table) | 10 new tests, `tests/test_statistical_analysis.py:573-690` (§3b) |
| 3 | Power analysis, target β > 0.80 | ✅ module exists; ✅ disclosure now reproducible (**audit script added this review**) | `analysis/phase1_statistics/power_analysis.py:14` (`calculate_power`), `:81` (`required_sample_size`), `:202` (`nonparametric_power_analysis`), `:305` (CLI) | **new** `analysis/power_audit.py` regenerates the `docs/results/experimental_design.md` §12.8 table from canonical CSVs → `docs/review/wave1/data/power_audit.csv` | power tests in `tests/test_statistical_analysis.py` |
| 4 | Bootstrap 10,000 percentile CIs | ✅ implemented + applied | `analysis/phase1_statistics/bootstrap.py:14` (default `n_bootstrap=10000`), `:70-72` (percentile interval) | `analysis/generate_figures.py:74-93` (`bootstrap_ci_errors`), `analysis/generate_effect_sizes.py:38-59` | bootstrap tests in `tests/test_statistical_analysis.py` |
| 5 | Fidelity full distribution (not mean-only) | ✅ module exists; ✅ cross-experiment five-number product **added this review** | `analysis/phase1_statistics/core.py:540`, `analysis/phase1_statistics/fidelity_distribution.py` | **new** `analysis/fidelity_distribution_report.py` → `docs/review/wave1/data/fidelity_distribution.csv` (16 experiments × min/Q1/median/Q3/max/mean/zero-count) | covered via core stats tests |
| 6 | Threshold sensitivity θ ∈ {1%, 5%, 10%, 20%} | ✅ implemented; ⚠️ product chain broken (see §4) | `analysis/phase1_statistics/core.py:626` (default grid), `analysis/phase2_threshold_sensitivity/run.py:61` (same grid) | `run.py` products (`threshold_sensitivity.csv/pdf/report.md`) **absent** from `analysis/figures/`; fig05 does not consume them | sensitivity tests in `tests/test_statistical_analysis.py` |

### 1.1 Glass's Δ gap — found and fixed

README and the manuscript declare Glass's Δ, but `effect_size.py` had no
implementation and `generate_effect_sizes.py` had no `glass_delta` output column
(re-running it would have silently dropped the column present in the legacy CSV).

Fix (this review):

- **`analysis/phase1_statistics/effect_size.py:152`** — new `glass_delta(x, y, control="auto")`.
  `auto` uses the baseline (`y`) SD as denominator; when `y` has zero variance it
  falls back to the `x` SD and records a note; when both have zero variance it
  returns NaN with note `"undefined (zero variance)"`. Includes approximate
  95 % CI (Hedges 1981 SE).
- **`analysis/generate_effect_sizes.py`** — imports the new function, computes it
  per comparison, inserts `"glass_delta"` into `CSV_COLUMNS` (after `hedges_g`),
  adds a Glass column + denominator convention to the summary markdown, and adds
  an `--out-dir` CLI flag (default `analysis/figures`).
- **Verification:** regenerated `docs/review/wave1/data/effect_sizes.csv` (19 rows)
  reproduces the legacy CSV exactly for `cohens_d`, `hedges_g`, `cliffs_delta`,
  and bootstrap CIs; zero-variance rows reproduce the legacy `d/√2` values
  (Greedy vs SA 0.480311, WCL vs LBL 1.981119, Greedy vs GA 0.267079).

⚠️ **Caveat for manuscript/integration:** on rows where the control SD is near-zero
(but non-zero), Glass's Δ inflates — Random vs IQP 0.578 → 6.52, Random vs UCCSD
0.536 → 6.44, Phase-1 vs Phase-2a −0.438 → −0.670. This is inherent to Glass's Δ;
**Cliff's δ should be cited as the primary effect size on those rows.**

---

## 2. Figure error bars use bootstrap CIs, not std — confirmed

`analysis/generate_figures.py` `bootstrap_ci_errors` (`:74-93`) feeds fig01 band
(`:170-184`), E3 (`:239`), E4 (`:301-306`), fig04 (`:389-398`), E15 (`:596-605`),
E17 (`:690-699`). `std` appears only as a *column* in `statistical_summary.csv`
(documented in its header note), never as figure error bars. ✅ No change needed.

## 3. fig05 does not consume the threshold-sensitivity pipeline — broken link

`fig05_threshold_sensitivity` (`analysis/generate_figures.py:427-470`) recomputes
success rates inline from the raw E1/E2/E3/E5 frames
(`df['reduction'].ge(t).mean()`) over a **different grid {0.1, 0.5, 1, 5, 10, 20, 30 %}**
and never reads `analysis/phase2_threshold_sensitivity/run.py` output (whose grid is the
protocol's {1, 5, 10, 20 %}). The run.py products are also absent from
`analysis/figures/`. **Owner: figures worker** (out of my write scope); recorded here
as a confirmed disconnect between protocol item 6 and the published figure.

## 4. Known Limitations — quantified (new `analysis/limitations_impact_audit.py`)

Full per-limitation recomputation in `docs/review/wave1/data/limitations_impact.csv`:

| Limitation | Verdict | Key recomputed numbers |
|---|---|---|
| L-trichotomy (empirical, 15 families) | **PARTIAL** | Data reproduces genuine ceilings {QFT, GHZ, SurfaceCode} ⊂ rule-based genuine set, but **Adder also classifies genuine-by-rule** (all compilers ≤ 0; the manuscript's own table agrees while its text says "3"). Prototype-limited is 5–6 by rule (HaarRandom borderline 6.55 %), **not 7** — manuscript §6.3 is internally inconsistent (L425 lists 7 incl. Adder + QuantumWalk vs table labels "Genuine"/"Unclear" vs "5 families" at L519). |
| L-heldout (ceiling-aware model fails) | consistent | MAE = 0.2775 on n = 125 (5 families: Ising, QAOA_mixer, QML, QPE, Shor); Pearson = NaN (held-out actual reductions all 0 → zero variance). |
| L-phase2b (fixture scale) | quantified | E24: phase1_greedy 0.00 %, phase2a_commutation 79.80 %, phase2b_template 2.50 % (n = 25 each); E10p2b full-validation 624 rows / 16 families. |
| L-e18 (survivor bias) | consistent | 120/270 rows = 44.4 % (78 decompose_error + 42 fidelity = 0); 92/142 circuits = 64.8 %; 7/15 families with surviving rows. See §7. |
| L-wcl (E19 = random Universal only) | quantified | E27 extension covers 16 families; WCL mean reduction > 0 on 8 (CNOT_chain 100 %, BV 30.79 %, RandomClifford 22.51 %, Structured 12.88 %, UCCSD_inspired 10.87 %, IQP 7.22 %, Universal 6.76 %, Grover 3.88 %). |
| L-shuffler (no shuffler control) | **STALE LIMITATION** | E22 control exists (`data/v7/e22`, 2,240 rows, 5 shuffles × 2 optimizers + original + WCL). Shuffle-vs-original MWU: greedy_phase1_lbl p < 1e-4 (shuffles 10.3 % > original 6.3 %!), commutation_phase2a p = 0.4623. README limitation #9 / manuscript 6.3.9 must be updated. |
| L-e04seed (single seed) | **REVIEW — E29 does not reproduce E04** | E29 (200 seeds/optimizer) vs E04 point estimates: RLS 0.00 % → **−176.5 %** (gate inflation at fidelity 1.0), SA −1.6 % → −22.1 %, GA −0.2 % → −8.3 %. E04 conclusions are seed/configuration-fragile (E29 also uses different circuits: n = 5, depth = 15). Any E04-based claim needs qualification. |

Existing per-limitation scripts confirmed present: `scripts/e18_survivor_bias_report.py`,
`experiments/e18_bias_correction.py`, `experiments/phase2b_full_validation.py`,
`experiments/wcl_full_family.py`, `experiments/gate_shuffle_ablation.py`,
`experiments/multi_seed_e04.py`, held-out CSV recomputation.

## 5. Manuscript statistical claims without code / contradicted (manuscript is read-only)

| Location | Claim | Finding |
|---|---|---|
| L407 | "E4 KW p = 1.000 non-significant for reduction" | **Contradicted.** Latest `analysis/figures/fdr_correction_results.csv` (regen 2026-07-20): E4 reduction KW raw p = 6.12e-12, BH-adj p = 1.15e-11 → significant. |
| L411 | "E1–E5 all non-significant after FDR" | **Contradicted.** E4 (1.15e-11) and E5 (1.08e-10) are significant; E1/E2/E3 non-significant. |
| L471 (+ suppl. L643/738) | E16 "power = 0.126, p = 0.420, Cohen's d = 0.173" | **Not reproducible** from canonical E16 data. Closest attempts: w2-vs-w20 all-rows Welch p = 0.0253/d = 0.241; 15-family paired t p = 0.112; Wilcoxon p = 0.043; family-mean Welch p = 0.392/d = 0.317; w10-vs-w20 paired p = 0.169. No analysis code produces 0.420/0.173. Provenance unknown. |
| L640 | "0/5 binomial 95 % CI [0 %, 45 %]" | **No implementation.** No binomial-CI code anywhere in the repo (Clopper–Pearson upper 1 − 0.05^(1/5) = 0.451 matches the number, so it was hand-computed). |
| L316 | E10 Universal "Cohen's d = 1.32" | **No current artifact reproduces it.** Related defect: the E10 Universal MWU in `analysis/generate_figures.py:889-897` is **dead code** — it filters `optimizer == 'Greedy'/'HybridCommuteRewrite'` while canonical E10 uses `greedy_phase1`/`commutation_phase2`/`hybrid_phase1_2`, so the test is silently skipped (absent from the FDR CSV). Owner: figures worker. |
| L348 | "n = 64 per group for d = 0.5" | ✅ Verified: `required_sample_size(0.5, power = 0.8)` → n = 64 (achieved power 0.8015). All §12.8 doc power values reproduce exactly with `calculate_power` (see `power_audit.csv`, column `doc_reproduced_power`). |
| L642 | "Welch's t-test" in canonical pipeline | Welch exists only in `experiments/e10_phase1_vs_phase2/analyze.py:160` and `experiments/multi_seed_e04.py:275`; the canonical FDR pipeline uses KW/MWU/Pearson/Friedman. Consistency note for integration. |

### Power audit detail (supports L348 row)

`docs/review/wave1/data/power_audit.csv`: doc-stated power figures are internally
consistent with the canonical calculator, **but** measured worst-case group sizes
are smaller than the doc's representative n for 4/14 rows: E10 per-family (n = 5,
power ≈ 0.10), E11 per-family (min n = 3, power ≈ 0.07), E14 per cell (min n = 15,
power ≈ 0.25), E18 per family (min n = 3, power ≈ 0.07). These four were already
directionally disclosed as underpowered/exploratory; the audit makes the gap
exact. E12 is the reverse: doc n = 8 vs measured 142 → actually adequate (0.94).

## 6. Outlier scan (new `analysis/outlier_scan.py`)

Scans reduction / fidelity / runtime of 20 canonical CSVs (hard range checks with
1e-9 float tolerance, |z| > 4, 1.5×IQR, column-integrity checks). Full results:
`docs/review/wave1/data/outlier_scan.csv` — **112 finding rows: 80 benign, 24
explainable, 8 needs-attention.**

- **Benign (80):** fidelity 1 + ε float excursions (max ε = 4.4e-15, e.g. 249 rows
  in E22, 96 in E27); heavy-tailed runtimes; in-range statistical tails.
- **Explainable (24):** E18 fidelity = 0 (documented survivor bias, 42 rows);
  E3 fidelity = 0 (38 rows, consistent with disclosed mean 0.9968 = 1 − 38/12000);
  E14 fidelity = 0 (20 rows, success = False at n_qubits ≥ 10); documented
  negative-reduction inflation in E4/E12/E15/E20/E29 (e.g. E20 220 rows, E29 598
  rows, E12 57 rows).
- **Needs-attention (8) — data quality, not physics:** the `success` column is
  **constant across entire files** — uniformly `False` in E1/E2/E3/E4 (v2_fixed
  era) and uniformly `True` in E19/E22/E27/E29 (v6/v7 era). The column carries no
  information and cannot corroborate failure flags; downstream code must not rely
  on it for these datasets. Owner: data worker.

## 7. E18 survivor-bias consistency — verified (read-only pandas recomputation)

270 rows; ok = 192, decompose_error = 78 (28.9 %); fidelity = 0 among ok rows = 42
→ combined 120/270 = **44.4 %** (the 44.4 % headline requires combining both
failure modes; `scripts/e18_survivor_bias_report.py` alone reports only 28.9 %).
Per-family: Grover 7/10; HaarRandom 3/3; HardwareEfficient/IQP/QAOA/QFT 11/11;
QuantumWalk/UCCSD/VQE 8/8; remaining 6 families 0. Per-optimizer: none = 78/78;
all three optimizers 0/64. Circuit-level (incl. fidelity = 0): **92/142 = 64.8 %**
(78/142 = 54.9 % without fidelity = 0). All consistent with
`docs/results/e18_survivor_bias.md` and manuscript L575. ✅

---

## Verification commands and results

| Command | Result |
|---|---|
| `/d/Downloads/miniforge3/python analysis/generate_effect_sizes.py --out-dir docs/review/wave1/data` | ✅ 19 rows; legacy numeric parity + new `glass_delta` column |
| `/d/Downloads/miniforge3/python analysis/power_audit.py` | ✅ 14 rows; all doc powers reproduced; 4 underpowered at worst-case n |
| `/d/Downloads/miniforge3/python analysis/fidelity_distribution_report.py` | ✅ 16 experiments, five-number table written |
| `/d/Downloads/miniforge3/python analysis/limitations_impact_audit.py` | ✅ 7 limitations quantified (verdicts above) |
| `/d/Downloads/miniforge3/python analysis/outlier_scan.py` | ✅ 112 findings (80 benign / 24 explainable / 8 needs-attention) |
| `/d/Downloads/miniforge3/python -m pytest tests/test_statistical_analysis.py tests/test_gate_predicates.py tests/test_wire_traversal.py -q --timeout=600` | ✅ **122 passed** (incl. 10 new Glass's Δ tests) |
| `... pytest tests/test_circuit_generation.py tests/test_commutation_bug_reproduction.py` | ✅ 47 passed |
| `... pytest tests/test_ag_canonical.py tests/test_ceiling_aware.py` | ✅ 21 passed |
| `... pytest tests/test_commutation.py tests/test_hardness_families.py` | ✅ 33 passed |
| `tests/test_optimizers.py`, `tests/test_phase2b_template_matcher.py`, `tests/test_integration.py` | ⏸ not run this session (session timeout) — **rely on CI coverage** |

Known pre-existing quirk (not introduced by this review):
`tests/test_statistical_analysis.py` defines the Holm/BY test functions twice
(~L834-870 and ~L888-931); pytest collects only the later definitions.

## Files changed by this review

- `analysis/phase1_statistics/effect_size.py` — added `glass_delta` (+CI, +notes).
- `analysis/generate_effect_sizes.py` — Glass's Δ end-to-end + `--out-dir`.
- `tests/test_statistical_analysis.py` — 10 new Glass's Δ tests (§3b), registered in `__main__` runner.
- `analysis/power_audit.py` — **new**.
- `analysis/fidelity_distribution_report.py` — **new**.
- `analysis/limitations_impact_audit.py` — **new**.
- `analysis/outlier_scan.py` — **new**.
- `docs/review/wave1/data/*` — regenerated audit products.
- `.review_backups/` — timestamped backups of pre-edit files.

## Unresolved gaps (hand-off)

1. **fig05 ↔ threshold-sensitivity disconnect** (§3) — figures worker.
2. **Stale manuscript claims** L407/L411 (E4/E5 significance), trichotomy counts (§4), shuffler limitation 6.3.9, E04 fragility qualification — integration worker (manuscript is read-only for me).
3. **E16 "p = 0.420, d = 0.173, power = 0.126"** (L471 + supplement) — no code or data reproduces these numbers; provenance unknown. Either locate the original analysis or correct the manuscript.
4. **Binomial CI [0 %, 45 %]** (L640) — no implementation; add Clopper–Pearson to `phase1_statistics` or cite as hand-computed.
5. **E10 Universal MWU dead code** in `generate_figures.py:889-897` (optimizer-name mismatch) — figures worker.
6. **Constant `success` columns** in 8 canonical datasets — data worker decision (fix or document as reserved).
