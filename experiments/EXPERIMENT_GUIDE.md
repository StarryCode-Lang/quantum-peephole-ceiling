# Experiment Execution Guide

> **Status (2026-08-07):** This document preserves the original review-gap
> protocol. Active dataset status and canonical paths are defined by
> `data/DATA_CANONICAL.md`, `release/release_manifest.json`, and the individual
> experiment scripts. Do not treat v6 output paths below as current release
> paths.

This document preserves four historical review-gap protocols and their
reproduction commands. The gaps have since been closed or narrowed by the
recorded E26, E19-extended, E22, E29, and E30 evidence. The current residual
listing/Phase-2b pilot is E31 and is documented below as non-canonical support.

## Current Evidence Map

| Evidence | Current status | Active artifact |
|---|---|---|
| E26 Phase-2b full validation | Complete; canonical full-scale evidence | `data/v8/phase2b_full/` |
| E19/E19-extended WCL validation | Complete for recorded Universal and cross-family matrices | `data/v6/e19/`, `data/v7/e19_extended/` |
| E22 shuffle control | Complete for Phase-1/Phase-2a | `data/v7/e22/` |
| E29 multi-seed replication | Complete; 800-row run | `data/v7/e29/` |
| E30 corrected Theorem 1(a) validation | Complete; 27 cells / 13,500 trials | `data/v10/e30/` |
| E31 listing x Phase-2b pilot | Non-canonical smoke support only; full factorial remains open | `data/v11/e31_listing_phase2b/` |

Canonical status is governed by `data/DATA_CANONICAL.md` and
`release/release_manifest.json`. E31 must not be added to the manifest without
an explicit evidence-version decision.

## Environment

- **OS**: Windows
- **RAM**: 16 GB
- **GPU**: None (pure CPU quantum simulation)
- **Python**: 3.11+ with Qiskit 2.4.1, numpy, pandas, scipy, tqdm
- **Project root**: `D:/Desktop/Q-research/`

All scripts are self-contained with `main()` functions, `--help` flags,
and CSV output. They use only existing project dependencies (no new
packages required).

---

## Experiment 1: Phase-2b Full 15-Family Validation

**Script**: `experiments/phase2b_full_validation.py`
**Output**: `data/v8/phase2b_full/`
**Review gap closed**: FATAL — E26 now validates the implemented Phase-2b library at full scale; the protocol below is retained for reproduction.

### Purpose

Theorem 9 proves that Phase-2b (template-assisted rewriting) achieves
The all-ones Bernstein--Vazirani construction achieves reduction
2n/(3n+2); this is not a global optimality claim.
The existing fixture-scale validation (E10 Phase-2b, 1,017 rows) only
covers 10 of 15 families and uses a single instance per size. This
experiment:

1. Extends BV oracle validation to n=2..12 with 10 random secrets per
   size for statistical power on the asymptotic bound.
2. Tests Phase-2b template matching on all 15 families (adds Grover,
   Adder, QuantumWalk, IQP, SurfaceCode, UCCSD_inspired — the 6 families
   missing from the fixture validation).
3. Runs Phase-1 (Greedy), Phase-2a (CommutationRewriter), and Phase-2b
   (TemplateMatcher full pipeline) side by side for direct comparison.

### Expected output

- `e26_phase2b_full_{mode}_{timestamp}.csv` — per-circuit results
  (family, n, optimizer, original_size, optimized_size, reduction,
  fidelity, template_rewrites, hh_cancellations, h_reorders, runtime)
- `e26_bv_theory_{timestamp}.csv` — Thm 9 theoretical bounds vs sizes
- `metadata.json`

### Data volume

| Mode | Families | Sizes/family | Trials/family | Optimizers | Total rows |
|------|-----------|-------------|---------------|------------|------------|
| smoke | 15 | 3 (BV: 3) | 5 (random) / 1 (algo) / 3 (BV secrets) | 3 | ~600 |
| full | 15 | 8 (BV: 11) | 50 (random) / 1 (algo) / 10 (BV secrets) | 3 | ~12,000+ |

### Estimated runtime (16GB RAM, no GPU)

| Mode | Estimated time |
|------|---------------|
| smoke | 2-5 minutes |
| full | 45-90 minutes |

The runtime bottleneck is the Phase-2b `optimize_full_pipeline` on
large circuits (n=10), which performs iterative commutation reordering.
The random Universal and Clifford families contribute the most rows.

### Statistical analysis

1. **Thm 9 bound check**: For each BV size n, test whether the empirical
the all-ones Phase-2b row matches 2n/(3n+2). Report that row separately
from descriptive means over other secrets.
2. **One-sample t-test**: For each family, test H0: mean Phase-2b
   reduction = 0 (Phase-2b provides no benefit).
3. **Paired t-test**: Phase-2b reduction vs Phase-1 reduction per family
   (within-circuit paired comparison).
4. **Hedges' g effect size**: Phase-2b vs Phase-1, Phase-2b vs Phase-2a.
5. **Bootstrap 95% CI**: 5000-resample CI on mean reduction per family
   per optimizer.
6. **FDR correction**: Benjamini-Hochberg on the family of 15 p-values
   from the one-sample t-tests.

### Command

```bash
# Quick smoke test
python experiments/phase2b_full_validation.py --mode smoke

# Full run
python experiments/phase2b_full_validation.py --mode full

# Run only specific families
python experiments/phase2b_full_validation.py --mode full --families BV,QFT,GHZ
```

---

## Experiment 2: WCL Full 15-Family Validation

**Script**: `experiments/listing_sensitivity_check.py` plus the checkpointed fill scripts
**Output**: `data/v8/listing_sensitivity/`
**Review gap closed**: MEDIUM→FATAL — WCL validation limited to random Universal

### Purpose

E19 (WCL vs LBL) was run on random Universal circuits (10,000 rows), and
E19-ext adds the first cross-family extension (960 rows). The full listing
space and WCL × Phase-2b interaction remain open.
This experiment:

1. Runs WCL vs LBL comparison across ALL 15 circuit families at sizes
   n=3..10.
2. For random families (Universal, Clifford, Brickwork): 50 trials per
   size with different seeds.
3. For algorithmic families: 10 seeds per size to capture seed-dependent
   parameter variation.
4. Records whether WCL reordering actually changes the listing (structural
   diagnostic: `wcl_listing_reordered` column).

### Expected output

- `e27_wcl_full_{mode}_{timestamp}.csv` — per-circuit results
  (family, n, listing_model, original_size, optimized_size, reduction,
  fidelity, runtime, wcl_listing_reordered)
- `metadata.json`

### Data volume

| Mode | Families | Sizes/family | Trials/family | Listing models | Total rows |
|------|-----------|-------------|---------------|----------------|------------|
| smoke | 15 | 3 | 5 (random) / 2 (algo) | 2 | ~800 |
| full | 15 | 8 | 50 (random) / 10 (algo) | 2 | ~15,000+ |

### Estimated runtime

| Mode | Estimated time |
|------|---------------|
| smoke | 1-3 minutes |
| full | 20-40 minutes |

GreedyGateCancellation is fast (O(m) single pass). The WCL preprocessor
is O(m log m) topological sort. Runtime is dominated by circuit generation
for complex families (Grover, Adder, QuantumWalk at n=10).

### Statistical analysis

1. **Paired t-test**: LBL reduction vs WCL reduction per family (same
   circuit, different listing — paired by construction).
2. **Welch's t-test**: Unpaired comparison for robustness check.
3. **Cliff's delta**: Non-parametric effect size for LBL vs WCL
   (appropriate for zero-inflated distributions under LBL).
4. **Per-family gap analysis**: For each family, compute
   Delta = mean(WCL reduction) - mean(LBL reduction). Flag families
   where |Delta| > 0.001 as "WCL-sensitive."
5. **Listing-reorder diagnostic**: For families where WCL does NOT
   change the listing (wcl_listing_reordered=False), the LBL/WCL
   gap should be exactly 0 (sanity check).
6. **FDR correction**: Benjamini-Hochberg on the 15 family-level p-values.

### Key hypothesis

- H0: WCL does not change the ceiling on any structured family
  (trichotomy is NOT a listing artifact).
- H1: WCL changes the ceiling on at least one structured family
  (trichotomy IS partially a listing artifact).

### Command

```bash
python experiments/listing_sensitivity_check.py --mode smoke
python experiments/listing_sensitivity_check.py --mode full
```

---

## Experiment 3: Gate-Order Shuffle Ablation

**Script**: `experiments/gate_shuffle_ablation.py`
**Output**: `data/v7/e22/`
**Review gap closed**: MEDIUM→FATAL — No random gate shuffler control (Sec 6.3.11)

### Purpose

The manuscript admits: "No random gate shuffler control was performed.
A random permutation of gates (preserving unitary equivalence via
commutation) would test whether the optimizers are doing anything
distinguishable from randomness."

This ablation tests whether the listing-model sensitivity is structural
(H1) or merely a consequence of gate ordering randomness (H0):

1. For each circuit, generate 3 listing variants:
   - **ORIGINAL**: the circuit as generated (natural algorithmic structure)
   - **WCL**: Wire-Consecutive Listing (structured reorder)
   - **SHUFFLE**: random commutation-preserving permutation (5 random
     shuffles per circuit, using dependency-DAG topological sort with
     random priorities)
2. Run Phase-1 (Greedy, LBL mode) and Phase-2a (CommutationRewriter) on
   each variant.
3. Compare: original vs shuffle (is the optimizer exploiting structure
   or just gate order?) and WCL vs shuffle (is WCL's advantage structural
   or just a different random order?).

### Expected output

- `e28_shuffle_ablation_{mode}_{timestamp}.csv` — per-variant results
  (family, n, listing_model, optimizer, original_size, variant_size,
  optimized_size, reduction, fidelity, runtime)
- `metadata.json`

### Data volume

| Mode | Families | Sizes | Trials/family | Shuffles | Listing variants | Optimizers | Total rows |
|------|-----------|-------|---------------|----------|-----------------|------------|------------|
| smoke | 15 | 3 | 5/2 | 2 | 4 (orig+wcl+2shuf) | 2 | ~2,000 |
| full | 15 | 6 | 50/10 | 5 | 7 (orig+wcl+5shuf) | 2 | ~20,000+ |

### Estimated runtime

| Mode | Estimated time |
|------|---------------|
| smoke | 3-8 minutes |
| full | 60-120 minutes |

The CommutationRewriter is O(m^2 * window_size) per iteration and is the
runtime bottleneck. The shuffle itself (topological sort) is O(m log m)
and negligible. With 7 listing variants x 2 optimizers = 14 runs per
circuit, the full mode is the most compute-intensive experiment.

### Statistical analysis

1. **Paired t-test**: Original reduction vs mean-shuffle reduction per
   family (paired by circuit). Tests H0: structure doesn't matter.
2. **Welch's t-test**: WCL reduction vs mean-shuffle reduction per
   family. Tests H0: WCL is just another random order.
3. **Cohen's d / Hedges' g**: Effect size between original and shuffle,
   and between WCL and shuffle.
4. **ANOVA across listing variants**: For each family, F-test on
   {original, WCL, shuffle_0, ..., shuffle_4} — is there a listing
   effect at all?
5. **Variance ratio**: Var(shuffle reductions) / Var(original reductions).
   If shuffle produces high-variance reductions while original is
   near-zero, the structure is the controlling factor.
6. **FDR correction**: Benjamini-Hochberg across 15 families x 2 tests.

### Key hypotheses

- H0: Listing-model sensitivity is a random-order artifact.
  Shuffle reduction == original reduction (p > 0.05, small effect size).
- H1: Listing-model sensitivity is structural.
  Original != shuffle (p < 0.05, medium+ effect size), and
  WCL != shuffle (p < 0.05, medium+ effect size).

If H0 holds for ceiling families (QFT, GHZ, SurfaceCode), the "ceiling"
claim is confirmed but the optimizer's value is undermined. If H1 holds,
the ceiling is a structural property and the optimizer is correctly
reporting structural incompressibility.

### Command

```bash
python experiments/gate_shuffle_ablation.py --mode smoke
python experiments/gate_shuffle_ablation.py --mode full
```

---

## Experiment 4: Multi-Seed E04

**Script**: `experiments/multi_seed_e04.py`
**Output**: `data/v6/e29_multi_seed_e04/`
**Review gap closed**: MEDIUM — E04 single seed, statistical reliability uncertain

### Purpose

E04 compares 4 optimizers (Greedy, RLS, SA, GA) on random Universal
circuits. The reported results use a single base seed (seed=42), providing
no confidence intervals. This experiment:

1. Runs E04 with 10 independent base seeds: [42, 142, 242, ..., 942].
2. 100 trials per seed (matching E04's original trial count).
3. Paired comparison design preserved: all optimizers see the same circuit
   per trial; internal optimizer seeds differ (+10k/+20k/+30k) to decouple
   stochastic trajectories.
4. Greedy is deterministic (seed-independent) — serves as the control.

### Expected output

- `e29_multi_seed_{mode}_{timestamp}.csv` — per-trial results
  (seed_index, seed_base, trial, optimizer, reduction, fidelity, runtime)
- `e29_statistics_{mode}_{timestamp}.csv` — per-optimizer per-seed
  summary statistics with Bootstrap CIs
- `metadata.json`

### Data volume

| Mode | Seeds | Trials/seed | Optimizers | Total rows |
|------|-------|-------------|------------|------------|
| smoke | 2 | 10 | 4 | 80 |
| full | 10 | 100 | 4 | 4,000 |

### Estimated runtime

| Mode | Estimated time |
|------|---------------|
| smoke | < 1 minute |
| full | 15-30 minutes |

SA and GA are the slowest optimizers (iterative stochastic search). Greedy
is O(m) and RLS is O(m * iterations). At n=5, depth=15, each circuit has
~15-30 gates, so individual optimization is fast.

### Statistical analysis

1. **Seed-effect ANOVA**: For each optimizer, F-test across 10 seeds.
   H0: no seed effect (all seeds produce the same mean reduction).
   If p < 0.05, seed-dependent variance is significant and must be
   reported.
2. **Bootstrap 95% CI**: 5000-resample CI on mean reduction per optimizer
   (pooled across seeds) and per seed.
3. **Pairwise optimizer comparison**: Welch's t-test between all 6 pairs
   of optimizers, with Hedges' g effect size.
4. **FDR correction**: Benjamini-Hochberg on 6 pairwise p-values.
5. **Intraclass correlation (ICC)**: Measures the proportion of total
   variance attributable to seed (between-seed) vs trial (within-seed).
   ICC > 0.1 indicates meaningful seed-dependence.
6. **Per-seed mean std**: The standard deviation of per-seed mean
   reductions quantifies seed-to-seed variability.

### Key hypothesis

- H0: Seed choice does not affect mean reduction (single-seed results
  are representative).
- H1: Seed choice significantly affects mean reduction (single-seed
  results are unreliable; CI must be reported).

### Command

```bash
python experiments/multi_seed_e04.py --mode smoke
python experiments/multi_seed_e04.py --mode full
# Custom seeds and trials
python experiments/multi_seed_e04.py --seeds 42,142,242 --n-trials 50
```

---

## Supporting Pilot: E31 Listing x Phase-2b

**Script**: `experiments/e31_listing_phase2b_interaction.py`
**Analysis**: `analysis/e31_listing_phase2b_analysis.py`
**Output**: `data/v11/e31_listing_phase2b/`
**Status**: supporting non-canonical pilot; not a confirmatory interaction test

E31 crosses the original listing, WCL, and one seeded random topological listing
with Phase-1, Phase-2a, and Phase-2b on 44 smoke-scale source circuits. It
checks listing fidelity, preserves source-circuit pairing, and writes
descriptive cell summaries and paired contrasts. It does not estimate the full
listing space or establish a WCL x Phase-2b interaction across families,
qubit counts, depths, and seeds.

```bash
python experiments/e31_listing_phase2b_interaction.py
python analysis/e31_listing_phase2b_analysis.py
```

See `docs/analysis/e31_listing_phase2b_p3.md` for the recorded result and
limitations.

---

## Summary: Review Gaps Closed

| Experiment | Script | Gap | Severity | Status |
|-----------|--------|-----|----------|--------|
| E26 | phase2b_full_validation.py | Phase-2b not at canonical scale | FATAL | Closes gap |
| E19-ext | wcl_full_family.py | WCL limited to random Universal | MEDIUM→FATAL | First cross-family extension; broader listing factorial remains open |
| E22 | gate_shuffle_ablation.py | No random gate shuffler control | MEDIUM→FATAL | Closes gap |
| E29 | multi_seed_e04.py | E04 single seed | MEDIUM | Closes gap (800-row full run) |
| E30 | e30_thm1a_wcl/run.py | Theorem 1(a) WCL density never directly tested | MAJOR | Closes gap (2026-08-06, corrected formula) |
| E31 | e31_listing_phase2b_interaction.py | WCL x Phase-2b interaction | MAJOR | Smoke pilot only; full factorial remains open |

## Running All Experiments

```bash
# Quick smoke test of all 4 experiments (~10 minutes total)
cd D:/Desktop/Q-research
python experiments/phase2b_full_validation.py --mode smoke
python experiments/wcl_full_family.py --mode smoke
python experiments/gate_shuffle_ablation.py --mode smoke
python experiments/multi_seed_e04.py --mode smoke

# Full runs (sequential, ~4-5 hours total)
python experiments/phase2b_full_validation.py --mode full
python experiments/wcl_full_family.py --mode full
python experiments/gate_shuffle_ablation.py --mode full
python experiments/multi_seed_e04.py --mode full

# Supporting non-canonical pilot
python experiments/e31_listing_phase2b_interaction.py
python analysis/e31_listing_phase2b_analysis.py
```

## Statistical Methods Summary

All experiments use the following statistical toolkit (scipy.stats + numpy):

| Method | Use | When |
|--------|-----|------|
| Paired t-test | Within-circuit optimizer comparison | Same circuit, different optimizer/listing |
| Welch's t-test | Unpaired comparison | Robustness check, unequal variances |
| One-way ANOVA | Seed effect / listing effect | Multiple groups (seeds or listing variants) |
| Cohen's d / Hedges' g | Effect size | Standardized mean difference |
| Cliff's delta | Non-parametric effect size | Zero-inflated / non-normal distributions |
| Bootstrap CI (5000 resamples) | Confidence intervals | Mean reduction per optimizer/family |
| Benjamini-Hochberg FDR | Multiple comparison correction | 15 families x k tests family |

### FDR correction procedure

1. Collect all p-values from the family of tests (e.g., 15 one-sample
   t-tests, one per family).
2. Sort p-values in ascending order: p_(1) <= p_(2) <= ... <= p_(m).
3. For each i, compute the BH threshold: q * i / m, where q = 0.05.
4. Find the largest i such that p_(i) <= q * i / m. All tests with
   p_(j) <= p_(i) are declared significant.
5. Report both raw and FDR-adjusted p-values.

### Effect size interpretation

| Cohen's d / Hedges' g | Interpretation |
|----------------------|----------------|
| < 0.2 | Negligible |
| 0.2 - 0.5 | Small |
| 0.5 - 0.8 | Medium |
| > 0.8 | Large |

| Cliff's delta | Interpretation |
|---------------|----------------|
| |d| < 0.147 | Negligible |
| 0.147 <= |d| < 0.33 | Small |
| 0.33 <= |d| < 0.474 | Medium |
| |d| >= 0.474 | Large |
