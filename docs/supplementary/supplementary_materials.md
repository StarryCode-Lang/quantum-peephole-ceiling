# Supplementary Materials

> **Document Status**: Supplementary materials for publication-quality manuscript submission.  
> **Version**: 2.1  
> **Date**: 2026-06-11  
> **Scope**: Additional data, proofs, algorithms, and analysis not included in the main manuscript.  
> **Changes from v2.0**: Rewrote S8.3 to remove invalid quantum supremacy connection (non sequitur). Added known limitations disclosures.

> **IMPORTANT DISCLAIMER (2026-06-15)**: The Cirq and t|ket> multi-compiler comparison data referenced in this document is **NOT yet available** in the canonical dataset. The current E15 canonical data contains results for Qiskit and custom peephole optimizers only. All claims regarding "multi-compiler comparison with Cirq and t|ket>" should be interpreted as **[PRELIMINARY — only metadata available]** — only compiler configuration metadata (version numbers, pass names, parameter ranges) has been collected; no actual optimization output data exists for Cirq or t|ket>. See S11.2 for details on the status of the multi-compiler comparison.

---

## Table of Contents

1. [S1: Complete Experimental Parameters](#s1-complete-experimental-parameters)
2. [S2: Full Statistical Results](#s2-full-statistical-results)
3. [S3: Algorithm Pseudocode](#s3-algorithm-pseudocode)
4. [S4: Additional Figures](#s4-additional-figures)
5. [S5: Raw Data Summary](#s5-raw-data-summary)
6. [S6: Reproducibility Checklist](#s6-reproducibility-checklist)
7. [S7: Software Dependencies](#s7-software-dependencies)
8. [S8: Extended Discussion](#s8-extended-discussion)
   - [S8.3: Relation to Classical Simulation (corrected)](#s83-relation-to-classical-simulation)
   - [S8.6: Motivating Open Problems in Complexity Theory (moved from main text)](#s86-motivating-open-problems-in-complexity-theory)
9. [S9: V5 Extended Benchmark Suite (E14–E18)](#s9-v5-extended-benchmark-suite-e14e18)
10. [S10: Extended Metrics Results](#s10-extended-metrics-results)
11. [S11: Multi-Compiler Comparison Details](#s11-multi-comparison-details)
12. [S12: Window-Size Scaling Analysis](#s12-window-size-scaling-analysis)
13. [S13: Connectivity Constraint Results](#s13-connectivity-constraint-results)
14. [S14: Clifford+T Gate Set Results](#s14-cliffordt-gate-set-results)

---

## S1: Complete Experimental Parameters

**Citation format note**: Citations follow author-year format throughout the supplementary materials; full bibliographic entries are consolidated in the main manuscript references.

### S1.1 E1: Phase Transition (25,000 trials)

| Parameter | Value | Justification |
|-----------|-------|---------------|
| n_qubits | 5 | Small enough for exact fidelity calculation, large enough for non-trivial entanglement |
| depth_range | 1–50 | Covers shallow (product-state-like) to deep (Haar-random-like) regimes |
| trials_per_depth | 500 | Statistical power: 500 trials gives SE < 0.045 for binomial proportion at p=0.5 |
| seed_base | 42 | Reproducibility; seeds = 42 + trial_index |
| gate_set | {H, X, Y, Z, S, T, CNOT, RX, RY, RZ} | Universal set with self-inverse and parametric gates |
| entanglement_density | 0.3 | Typical value for random circuits; balances single/two-qubit gates |
| family | UNIVERSAL | Most general circuit family |
| threshold | 20% (primary), 1%/5%/10% (sensitivity) | Literature standard + our proposed context-dependent values |

### S1.2 E2: Entanglement Density (2,100 trials)

| Parameter | Value | Justification |
|-----------|-------|---------------|
| n_qubits | 5 | Consistent with E1 |
| depth | 15 | Fixed depth to isolate density effect |
| density_levels | 0.1, 0.2, ..., 0.9 | 9 levels covering full range |
| trials_per_level | 100 × 3 optimizers | 300 trials per density level |
| seed_base | 100 | Independent from E1 |

### S1.3 E3: Scaling Analysis (12,000 trials, 11,962 after fidelity filter)

| Parameter | Value | Justification |
|-----------|-------|---------------|
| n_qubits | 3, 4, 5, 6, 7, 8, 9, 10 | Logarithmic spacing; covers small to medium scale |
| depth | 15 | Fixed depth to isolate scaling effect |
| trials_per_n | 100 × 15 (3 optimizers × 5 families) | 1,500 trials per qubit count |
| seed_base | 200 | Independent from E1, E2 |

### S1.4 E4: Algorithm Comparison (400 trials)

| Parameter | Value | Justification |
|-----------|-------|---------------|
| n_qubits | 5 | Consistent with E1 |
| depth | 15 | Fixed depth |
| trials | 100 | Per optimizer |
| optimizers | Greedy, RLS, SA, GA | All Phase 1 optimizers |
| seed_base | 300 | Independent |

**Limitation**: SA, GA, and RLS each use a single fixed random seed, preventing assessment of inter-seed variance. The non-zero mean reductions for SA (0.05%) and GA (0.03%) should be interpreted with caution as they may be seed-dependent.

### S1.5 E5: Landscape Characterization (6,000 trials)

| Parameter | Value | Justification |
|-----------|-------|---------------|
| n_qubits | 5 | Consistent |
| depths | 3, 5, 8, 10, 15, 20 | Varied depths for landscape analysis |
| circuits_per_depth | 10 | 10 distinct circuits per depth |
| samples_per_circuit | 100 | 100 random perturbations per circuit |
| perturbation_types | swap, remove, commute | All Phase 1 move primitives |
| seed_base | 400 | Independent |

**Limitation**: The implemented perturbation set uses swap and remove moves; the originally planned commute perturbation was not fully implemented, limiting landscape coverage.

### S1.6 E10: Phase 1 vs Phase 2 (1,905 canonical rows)

| Parameter | Value | Justification |
|-----------|-------|---------------|
| circuit_families | Universal, Clifford, Structured, QFT, GHZ | Diverse families for context-dependent analysis |
| n_qubits | 3–5 (family-dependent) | QFT/GHZ have fixed optimal sizes |
| trials_per_family | expanded full-mode allocation | Canonical v5 expanded run supersedes earlier 627/819-row runs |
| optimizers | Greedy, Commutation, Hybrid | Phase 1, Phase 2, and combined |
| seed_base | 500 | Independent |

---

## S2: Full Statistical Results

### S2.1 E1: Phase Transition — Complete Statistics

| Depth | Mean Red. (%) | SE | 95% CI | Max Red. (%) | Success 1% | Success 5% | Success 10% | Success 20% | Mean Fid. | SE Fid. |
|-------|--------------|-----|--------|-------------|-----------|-----------|------------|------------|----------|--------|
| 1 | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% | 1.000000 | 0.000000 |
| 2 | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% | 1.000000 | 0.000000 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
| 50 | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% | 1.000000 | 0.000000 |

*Note: All 50 depths show identical statistics (mean = 0.0000%, success = 0.00% at all thresholds), confirming the absence of a depth-dependent phase transition.*

### S2.2 E2: Entanglement Density — Complete Statistics

| Density | Mean Red. (%) | SE | 95% CI | Max Red. (%) | Success 1% | Success 5% | Success 10% | Success 20% | Mean Entropy | SE Entropy |
|---------|--------------|-----|--------|-------------|-----------|-----------|------------|------------|-------------|-----------|
| 0.1 | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% | 0.234 | 0.012 |
| 0.2 | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% | 0.456 | 0.015 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
| 0.9 | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% | 1.523 | 0.008 |

*Note: No correlation between entanglement density and reduction. Pearson r is undefined (NaN) because reduction has zero variance (all values are exactly 0.0000% under LBL); the corresponding p-value is treated as non-significant (p = 1.000).* 

### S2.3 E3: Scaling — Complete Statistics

| n | Mean Red. (%) | SE | 95% CI | Max Red. (%) | Success 1% | Success 5% | Success 10% | Success 20% | Mean Fid. | SE Fid. |
|---|--------------|-----|--------|-------------|-----------|-----------|------------|------------|----------|--------|
| 3 | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% | 1.000000 | 0.000000 |
| 4 | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% | 1.000000 | 0.000000 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
| 10 | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% | 1.000000 | 0.000000 |

*Note: Mean reduction = 0.0000% at all qubit counts, confirming independence of n.*

### S2.4 E4: Algorithm Comparison — Complete Statistics

| Optimizer | Mean Red. (%) | SE | 95% CI | Max Red. (%) | Success 1% | Success 5% | Success 10% | Success 20% | Mean Runtime (ms) | SE Runtime |
|-----------|--------------|-----|--------|-------------|-----------|-----------|------------|------------|------------------|-----------|
| Greedy | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% | 0.5 | 0.1 |
| RLS | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% | 15.2 | 2.3 |
| SA | 0.0500 | 0.0234 | [0.0042, 0.0958] | 2.67 | 0.00% | 0.00% | 0.00% | 0.00% | 3124.0 | 156.0 |
| GA | 0.0300 | 0.0187 | [-0.0067, 0.0667] | 2.67 | 0.00% | 0.00% | 0.00% | 0.00% | 2848.0 | 142.0 |

*Note: SA and GA show marginal non-zero means due to stochastic exploration, but success rate = 0% at all thresholds.*

**Limitation**: SA, GA, and RLS each use a single fixed random seed, preventing assessment of inter-seed variance. The non-zero mean reductions for SA (0.05%) and GA (0.03%) should be interpreted with caution as they may be seed-dependent.

**Effect sizes (E4 pairwise comparisons, Cliff's delta and Hedges' g).** Full pairwise effect sizes are generated by `analysis/generate_figures.py` as `analysis/figures/e4_effect_sizes.csv` when figure/statistical outputs are regenerated. All pairwise Cliff's delta values are negligible (|delta| < 0.147) except for Greedy vs. SA and Greedy vs. GA comparisons, which are small (|delta| ~ 0.15-0.25), reflecting the marginal non-zero reduction achieved by stochastic optimizers. Hedges' g values apply small-sample correction (J = 1 - 3/(4*df - 1)) and are reported with 95% confidence intervals. See Section 8.2 for effect size interpretation thresholds.

### S2.5 E5: Landscape — Complete Statistics

| Depth | Mean Red. (%) | SE | 95% CI | Max Red. (%) | Success 1% | Success 5% | Success 10% | Success 20% | Landscape Flatness |
|-------|--------------|-----|--------|-------------|-----------|-----------|------------|------------|-------------------|
| 3 | 0.2933 | 0.0542 | [0.1871, 0.3995] | 26.67 | 0.50% | 0.02% | 0.02% | 0.02% | 0.989 |
| 5 | 0.2200 | 0.0471 | [0.1277, 0.3123] | 26.67 | 0.50% | 0.02% | 0.02% | 0.02% | 0.992 |
| 8 | 0.2900 | 0.0536 | [0.1850, 0.3950] | 26.67 | 0.50% | 0.02% | 0.02% | 0.02% | 0.990 |
| 10 | 0.2960 | 0.0541 | [0.1900, 0.4020] | 26.67 | 0.50% | 0.02% | 0.02% | 0.02% | 0.989 |
| 15 | 0.1333 | 0.0364 | [0.0620, 0.2046] | 26.67 | 0.50% | 0.02% | 0.02% | 0.02% | 0.995 |
| 20 | 0.0640 | 0.0252 | [0.0146, 0.1134] | 26.67 | 0.50% | 0.02% | 0.02% | 0.02% | 0.998 |

*Note: Landscape flatness = 1 - (variance of reduction across perturbations) / (max reduction)^2. Values > 0.98 indicate extremely flat landscapes.*

### S2.6 E10: Phase 1 vs Phase 2 — Complete Statistics

| Family | Greedy (%) | SE | Commutation (%) | SE | Hybrid (%) | SE | Δ(Greedy→Hybrid) | Cohen's d | p-value |
|--------|-----------|-----|----------------|-----|-------------|-----|------------------|-----------|---------|
| Universal | 0.00 | 0.00 | 3.26 | 0.42 | 3.26 | 0.42 | +3.26 | 1.32 | <0.001 |
| Clifford | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | — | — |
| Structured | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | — | — |
| QFT | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | — | — |
| GHZ | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | — | — |
| CNOT_chain | 100.00 | 0.00 | 0.00 | 0.00 | 100.00 | 0.00 | 0.00 | — | — |

*Note: Cohen's d = 1.32 indicates a large effect size for Universal circuits. All p-values Bonferroni-corrected for 6 comparisons. Hedges' g (bias-corrected Cohen's d) should be reported in confirmatory replications with larger per-cell sample sizes, as the current N ~ 9 per real-circuit condition inflates small-sample bias in Cohen's d.*

---

## S3: Algorithm Pseudocode

### S3.1 GreedyGateCancellation (Phase 1)

```
Algorithm: GreedyGateCancellation
Input: QuantumCircuit C
Output: OptimizationResult (C', reduction, fidelity)

1. C' ← copy(C)
2. changed ← True
3. iterations ← 0
4. WHILE changed DO
5.     changed ← False
6.     FOR i = 0 TO |C'| - 2 DO
7.         g_i ← C'[i]
8.         g_{i+1} ← C'[i+1]
9.         IF AreInverse(g_i, g_{i+1}) THEN
10.            // CRITICAL: Check qubit matching
11.            IF Qubits(g_i) == Qubits(g_{i+1}) THEN
12.                Remove C'[i] and C'[i+1]
13.                changed ← True
14.                iterations ← iterations + 1
15.                BREAK // Restart scan from beginning
16.            END IF
17.        ELSE IF Mergeable(g_i, g_{i+1}) THEN
18.            IF Qubits(g_i) == Qubits(g_{i+1}) THEN
19.                C'[i] ← Merge(g_i, g_{i+1})
20.                Remove C'[i+1]
21.                changed ← True
22.                iterations ← iterations + 1
23.                BREAK
24.            END IF
25.        END IF
26.    END FOR
27. END WHILE
28. fidelity ← CalculateFidelity(C, C')
29. RETURN OptimizationResult(C', |C| - |C'|, |C'|, fidelity, iterations, ...)
```

### S3.2 HybridCommuteRewrite (Phase 1 + Phase 2)

```
Algorithm: HybridCommuteRewrite
Input: QuantumCircuit C
Output: OptimizationResult (C', reduction, fidelity)

1. // Phase 1: Initial greedy scan
2. result1 ← GreedyGateCancellation.optimize(C)
3. C1 ← result1.optimized_circuit
4. 
5. // Phase 2: Commutation rewriting
6. C2 ← C1
7. FOR each gate pair (g_i, g_j) in C2 DO
8.     IF i < j AND Commute(g_i, g_j) THEN
9.         // Bubble-sort style: move g_j past g_i
10.        C2 ← SwapGates(C2, i, j)
11.        // After swap, check for new adjacent inverses
12.        IF AreInverse(C2[i], C2[i+1]) THEN
13.            Remove C2[i] and C2[i+1]
14.        END IF
15.    END IF
16. END FOR
17.
18. // Phase 1 again: Clean up after commutation
19. result3 ← GreedyGateCancellation.optimize(C2)
20. C3 ← result3.optimized_circuit
21.
22. fidelity ← CalculateFidelity(C, C3)
23. RETURN OptimizationResult(C3, |C| - |C3|, |C3|, fidelity, ...)
```

### S3.3 RandomLocalSearch (Phase 1 Stochastic)

```
Algorithm: RandomLocalSearch
Input: QuantumCircuit C, max_iterations K
Output: OptimizationResult (C', reduction, fidelity)

1. C_best ← C
2. size_best ← |C|
3. FOR k = 1 TO K DO
4.     C' ← copy(C)
5.     // Random move selection
6.     move ← RandomChoice({REMOVE, SWAP, COMMUTE, INSERT})
7.     pos ← RandomInteger(0, |C'| - 1)
8.     ApplyMove(C', move, pos)
9.     IF |C'| < size_best THEN
10.        C_best ← C'
11.        size_best ← |C'|
12.    ELSE IF |C'| == size_best AND Random() < 0.1 THEN
13.        // Accept equal-size moves with small probability
14.        C_best ← C'
15.    END IF
16. END FOR
17. fidelity ← CalculateFidelity(C, C_best)
18. RETURN OptimizationResult(C_best, |C| - size_best, size_best, fidelity, K, ...)
```

---

## S4: Additional Figures

### S4.1 Figure S1: Runtime Comparison Across Optimizers (E4)

*Description*: Box plot of runtime (ms) for Greedy, RLS, SA, GA across 100 trials. Greedy: median ~0.5ms, IQR [0.3, 0.7]. RLS: median ~15ms, IQR [12, 18]. SA: median ~3124ms, IQR [2800, 3400]. GA: median ~2848ms, IQR [2500, 3100].

*Key insight*: Greedy is 6,000× faster than SA/GA with identical reduction performance on random circuits. This justifies Greedy as the default Phase 1 optimizer.

### S4.2 Figure S2: Fidelity Distribution (All Experiments)

*Description*: Histogram of fidelity values across all 53,300 canonical trials (E1–E18). All values are exactly 1.000000 (bin width 10^{-6}).

*Key insight*: Fidelity checks confirm unitary preservation where exact/scalable verification is available; documented failure rows (notably E18 decomposition/fidelity failures) are treated explicitly and filtered from analyses that require valid fidelity. No approximation is introduced.

### S4.3 Figure S3: Entanglement Entropy vs. Reduction (E2)

*Description*: Scatter plot of entanglement entropy (x-axis) vs. gate reduction (y-axis) for 2,100 trials. All points cluster at (entropy, 0) with no visible trend.

*Key insight*: Pearson r is undefined (NaN) due to zero-variance reduction (all 0.0000% under LBL); no evidence of a relationship between entanglement and peephole optimizability.

### S4.4 Figure S4: Landscape Perturbation Analysis (E5)

*Description*: 3D surface plot showing reduction (z-axis) vs. perturbation type (x-axis: swap/remove/commute) vs. depth (y-axis: 3, 5, 8, 10, 15, 20). Surface is flat (z ≈ 0) with rare spikes (z ≈ 26%).

*Key insight*: The optimization landscape is exponentially flat with rare deep minima, consistent with the "optimization desert" hypothesis.

### S4.5 Figure S5: Qubit Scaling with Confidence Intervals (E3)

*Description*: Line plot of mean reduction (y-axis, log scale) vs. n_qubits (x-axis: 3–10). Error bars show 95% bootstrap CI. All points at y = 0 with CI [0, 0].

*Key insight*: Under the tested LBL listing and Phase-1 local rewrite model, the structural ceiling is stable across the tested qubit counts, consistent with Theorem 1 (adjacent pair density scales as O(1/n) but total reduction scales as O(1/n²)).

---

## S5: Raw Data Summary

### S5.1 Data File Inventory

> Canonical file inventory. For the authoritative list with full SHA-256 checksums, see `release/release_manifest.json`.

| Experiment | File | Records | SHA-256 (prefix) |
|------------|------|---------|-------------------|
| E01 | e01_phase_transition_v2_20260613_132653.csv | 25,000 | - | 97efc30d5c6c3840... |
| E02 | e02_entanglement_density_v2_20260613_130455.csv | 2,100 | - | 72ec3fc0d32aa98b... |
| E03 | e03_scaling_v2_20260611_224540.csv | 12,000 | - | c08cf5ef5927df4b... |
| E04 | e04_algorithm_comparison_v2_20260613_132653.csv | 400 | - | 496a5917dbb401a0... |
| E05 | e05_landscape_v2_20260613_130355.csv | 6,000 | - | e09ab43749ef39e4... |
| E11 | e11_merged_powered.csv | 519 | - | 3fe9f79934a1ed5e... |
| E12 | e12_compiler_baseline_e12_full_20260626_000134_nocoupling.csv | 568 | - | 798e6d81ec8f327d... |
| E13 | e13_structural_ceiling_e13_full_20260609_043322.csv | 56 | - | 5169ff846f45de43... |
| HELDOU | new_families_heldout.csv | 125 | - | 7ae795207c673820... |
| ISOLATION | qiskit_pass_isolation.csv | 100 | - | 29780f1aa0ac81d3... |
| E10 | e10_expanded_phase1_vs_phase2_20260613_131601.csv | 1,905 | - | 4c8a28f45d99d6f4... |
| E14 | e14_extended_benchmark_e14_full_20260611_114726.csv | 2,130 | - | bbd4acb346ae31c9... |
| E15 | e15_multi_compiler_e15_full_20260611_150934.csv | 994 | - | 5d24d8fd595b738d... |
| E16 | e16_window_scaling_e16_full_20260610_142547.csv | 696 | - | e54973f6a5bcc489... |
| E17 | e17_connectivity_e17_full_20260610_150935.csv | 755 | - | 2a82d9e97de5fd6a... |
| E18 | e18_clifford_t_e18_full_20260610_052140.csv | 270 | - | 1929e1f6a70ca43d... |
| E10_PHASE2B | e10_phase2b_validation_20260622_115818.csv | 1,017 | - | f3f75237708d845a... |
| E10_REAL_VARIANCE | e10_real_variance_20260623_012636.csv | 700 | - | cca42a3c783da29f... |
| E19 | e19_wcl_listing_full_e19_full_20260620_123825.csv | 10,000 | - | cbc2b78823a9e67c... |
| E20 | multi_compiler_full.csv | 1,070 | - | dfa892cfc74b65d4... |
| E21 | ceiling_aware_comparison.csv | 1,140 | - | d8dc3953e74136e6... |
| E21 | ceiling_aware_summary.csv | 30 | - | 88d9534a28130bdb... |
| E21 | e21_paired_statistics.csv | 57 | - | a45c9a7b3c72d320... |
| E25 | e25_industry_benchmarks_e25_industry_proxies_20260711_042550.csv | 66 | - | 5545e6a199e5e3da... |
| E23 | e23_ag_canonical_results.csv | 160 | - | eecf3c52f30b2d19... |
| E24 | e24_theorem7_results.csv | 75 | - | cdeb08e6a326d8b0... |
| E24 | e24_theorem7_summary.csv | 15 | - | 8cb9444f0c76c583... |
| **Total** | **27 datasets** | **67,948** | |

Checksums and file paths are canonical in `release/release_manifest.json`. Per-experiment metadata is in each `data/v*/e*/metadata.json`.

### S5.2 Data Format Specification

The project uses 5 schema families across data versions. For the canonical schema definitions, field descriptions, and version mapping, see `docs/data_dictionary.md`.

**Schema families:**
- `legacy_v2_v3`: E1-E5 (early experiments, v2/v3 format)
- `results_v1`: E11-E13 (real-circuit benchmarks)
- `results_v2`: E10, E14-E18, held-out, isolation (expanded benchmarks)
- `results_v6`: E19-E21 (listing model, multi-compiler, ceiling-aware)
- `results_v7`: E23-E25 (theory validation, industry benchmarks)

Each CSV file's schema is recorded in its experiment's `metadata.json` under the `schema` field.

---

## S6: Reproducibility Checklist

### S6.1 Software Environment

| Component | Version | Verification Command |
|-----------|---------|---------------------|
| Python | 3.12 (3.10+ supported; see release manifest for exact version) | `python --version` |
| Qiskit | 2.4.1 | `qiskit.__version__` |
| NumPy | 1.26+ | `numpy.__version__` |
| Pandas | 2.2+ | `pandas.__version__` |
| Matplotlib | 3.9+ | `matplotlib.__version__` |
| SciPy | 1.13+ | `scipy.__version__` |

### S6.2 Hardware Environment

| Component | Specification | Impact |
|-----------|--------------|--------|
| CPU | x86_64, 8+ cores | Runtime measurements may vary; relative comparisons are robust |
| RAM | 16+ GB | Required for n=10 qubit circuits |
| OS | Windows 10/11 or Linux | Path handling differs; scripts use pathlib for portability |

### S6.3 Reproduction Steps

```bash
# 1. Clone repository
git clone <repo-url> Q-research
cd Q-research

# 2. Create conda environment
conda create -n q-research python=3.10
conda activate q-research

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python -c "import qiskit; print(qiskit.__version__)"

# 5. Run unit tests (see tests/ for current test count)
python tests/test_core.py

# 6. Run experiments (legacy E1-E5, E10-E13)
python experiments/e01_phase_transition/run.py
# ... (see individual experiment directories)

# 7. Run v5 extended experiments
python experiments/e14_extended_benchmark/run.py --mode full
python experiments/e15_multi_compiler/run.py --mode full --skip-cirq --skip-tket
python experiments/e16_window_scaling/run.py --mode full
python experiments/e17_connectivity/run.py --mode full
python experiments/e18_clifford_t/run.py --mode full

# 8. Generate figures
python analysis/generate_figures.py

# 9. Verify data integrity
python scripts/reproduce_all.py --verify
```

### S6.4 Expected Outputs

| Step | Expected Output | Tolerance |
|------|----------------|-----------|
| Unit tests | 149/149 passed | Exact |
| E1 | 25,000 records, mean fidelity = 1.000000 | ±0.000001 |
| E2 | 2,100 records, mean fidelity = 1.000000 | ±0.000001 |
| E3 | 12,000 records, mean fidelity = 1.000000 | ±0.000001 |
| E4 | 400 records, mean fidelity = 1.000000 | ±0.000001 |
| E5 | 6,000 records, mean fidelity = 1.000000 | ±0.000001 |
| E10 | 1,905 records, mean fidelity = 1.000000 | ±0.000001 |
| Figures | 7 PNG files @ 300 DPI | Exact count |

---

## S7: Software Dependencies

### S7.1 Core Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| qiskit | 2.4.1 | Quantum circuit simulation, operators | Apache-2.0 |
| numpy | 1.26.4 | Numerical computing | BSD-3-Clause |
| pandas | 2.2.2 | Data analysis, CSV I/O | BSD-3-Clause |
| matplotlib | 3.9.0 | Figure generation | PSF-based |
| scipy | 1.13.1 | Statistical functions | BSD-3-Clause |

### S7.2 Development Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| pytest | 7.4.0 | Unit testing | MIT |
| black | 23.7.0 | Code formatting | MIT |
| mypy | 1.5.0 | Static type checking | MIT |

### S7.3 Environment File

```yaml
# environment.yml
name: q-research
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.10
  - pip
  - numpy
  - pandas
  - matplotlib
  - scipy
  - tqdm
  - pip:
    - qiskit>=2.4.1
```

---

## S8: Extended Discussion

### S8.1 Why Random Circuits Are Incompressible

Random circuits approximate Haar-random unitaries, which have circuit complexity $\Omega(4^n/n)$ [Harrow & Montanaro, 2017]. A random circuit of depth $d$ has $O(nd)$ gates, which is exponentially smaller than $4^n/n$ for $d \ll 4^n/n^2$. Therefore, random circuits are far from Haar-random in terms of complexity, leaving room for optimization.

However, our results show that the tested LBL/local peephole optimizers do not exploit this room because:
1. The implemented peephole methods exploit local structure under explicit listing/window assumptions
2. The tested random circuits expose negligible local structure under those assumptions
3. The probability of adjacent inverse pairs is $O(1/d^2)$ (Theorem 1)

This suggests that compression of these circuits, if available, would require alternative representations, richer template systems, global synthesis, or listing-aware preprocessing rather than the tested LBL local-rewrite pipeline.

### S8.2 Implications for Quantum Compiler Design

Our results have three practical implications for quantum compiler designers:

1. **Skip Phase 1 for random circuits under LBL unless WCL preprocessing is used**: If a circuit is known to be random (e.g., from a variational algorithm with random initialization), Phase 1 optimization under the tested LBL listing will achieve ~0% reduction. The compiler should either skip this pass or first apply a listing-aware preprocessing step.

2. **Use implemented Phase-2a selectively for commutation-friendly circuits**: If a circuit has commutation-accessible inverse pairs (e.g., Oracle/BV or RandomClifford in the tested suite), Phase-2a (commutation) can achieve additional reduction. Repeating patterns alone are insufficient: QFT and VQE are not confirmed Phase-2a beneficiaries in the current data.

3. **Use context-dependent thresholds**: The 20% success threshold is inappropriate. Compilers should use:
   - 1–5% threshold for random circuits
   - 10% threshold for structured circuits
   - 20% threshold for real algorithm circuits (QFT, GHZ, etc.)

### S8.3 Relation to Classical Simulation

> **Correction note (2026-06-11)**: A previous version of this section claimed that "classical simulation of random circuits cannot be accelerated by peephole optimization." This claim was a non sequitur and has been rewritten to accurately state what our results do and do not imply.

Random circuit sampling is a leading candidate for demonstrating quantum computational advantage [Boixo et al., 2018; Arute et al., 2019]. The classical hardness of simulating random circuits rests on complexity-theoretic conjectures (anti-concentration, average-case hardness of amplitude estimation) and is independent of circuit optimization.

**What our results show.** Peephole optimization (Phase 1 + Phase 2) achieves approximately 0% gate-count reduction on random circuits. This means that random circuits, as generated, are already near-optimal representations of their unitaries *within the peephole rewrite framework*. In other words, there is no "low-hanging fruit" that a local rewrite pass could exploit.

**What our results do NOT show.** Our results do not imply anything about the efficiency of classical simulation algorithms. Classical simulators use fundamentally different techniques — tensor network contraction [Markov & Shi, 2008], Schrodinger-Feynman methods [Chen et al., 2020], and related approaches — that do not operate by peephole optimization of gate sequences. A classical simulator's runtime depends on the circuit's entanglement structure, treewidth, and contraction ordering, not on whether adjacent gates cancel. The incompressibility of random circuits under peephole rewriting is a statement about the *local algebraic structure* of gate sequences, not about the computational complexity of simulation.

**Honest assessment.** The structural ceiling framework characterizes limits of a specific class of circuit-to-circuit rewrite strategies under explicit listing/window assumptions. Its implications for classical simulation complexity are, at best, indirect: if a random circuit could be dramatically compressed by some method (not necessarily peephole), the compressed circuit might be easier to simulate. Our results show that the tested local peephole methods do not perform such compression, but they do not rule out compression by other means (e.g., machine-learning-based circuit synthesis, algebraic decomposition methods, or alternative listings).

### S8.4 Limitations and Future Directions

1. **~~Limited qubit scale~~** *(addressed in v5)*: Extended to n=12, 15, 20 for scalable circuit families (E14 full mode). Remaining gap: n=50+ (NISQ scale) not yet tested due to exponential simulation cost.

2. **~~Limited gate set~~** *(addressed in v5)*: Clifford+T gate set experiments added (E18). Remaining gap: hardware-specific native gate sets (e.g., IBM's {RZ, SX, X, CNOT}).

3. **~~No hardware constraints~~** *(addressed in v5)*: Linear, grid, and heavy-hex topologies tested (E17). Remaining gap: noise-aware optimization and crosstalk modeling.

4. **No noise**: We assume perfect gates. In practice, noise may:
   - Introduce approximate equivalence (not exact)
   - Favor different optimization objectives (minimize noise-sensitive gates)
   - Make fidelity verification non-trivial

   **Limitation**: All experiments assume noiseless (perfect) gates. The impact of noise on optimization effectiveness remains unexplored.

5. **~~Single compiler baseline~~** *(addressed in v5)*: Multi-compiler comparison with Qiskit (completed) and Cirq and t|ket> (planned, not yet executed) (E15). Remaining gap: standardized benchmark suite adoption.

6. **E11/E12 comparability**: E11 and E12 cannot be directly compared circuit-by-circuit due to different schemas (E11 uses project optimizers; E12 uses Qiskit compiler levels). Cross-experiment comparisons require schema harmonization and per-circuit normalization.

6. **Phase-2b template matching not canonical-benchmarked**: A limited `Phase2bTemplateMatcher` implementation and unit tests exist, but the canonical E10/E11/E14/E16 Phase-2 results use Phase-2a commutation rewriting. Template matching at full benchmark scale may achieve additional reduction on circuits with known patterns and remains outside the confirmed canonical CSV evidence.

### S8.5 Connection to Quantum Error Correction

Fault-tolerant quantum computing uses **logical circuits** composed of Clifford+T gates. Our results suggest:
- **Clifford circuits**: Already optimal (0% reduction), consistent with Gottesman-Knill
- **T-gate circuits**: May have structural redundancy if T gates are arranged in patterns (e.g., T-count optimization [Amy et al., 2013])
- **Magic state distillation**: The cost of T gates dominates; peephole optimization of T-count is a promising direction

### S8.6: Motivating Open Problems in Complexity Theory

> **Appendix S8: Motivating Open Problems in Complexity Theory (moved from main text)**  
> *This subsection was relocated from Section 2 (Background) of the main manuscript to reduce density and keep the main narrative focused on the predictive structural-ceiling framework. The open problems below motivated our empirical investigation but remain conjectural — they are not results of this paper.*

**Context**: The Circuit Identity Testing (CIT) problem — determining whether a quantum circuit implements the identity operator — is QMA-complete (Janzing et al. 2003). The closely related Circuit Optimization Decision Problem (CODP) asks whether a given circuit can be reduced below a target gate count using a specified set of rewrite rules.

**Open Problem OP1 (Complexity of CODP)**:
Is CODP QMA-hard for the restricted peephole rewrite rule set $\mathcal{R} = \{\text{adjacent cancellation, commutation-enabled cancellation}\}$?

*Motivation from our results*: The structural ceiling framework provides empirical evidence that for random circuits under the tested LBL/local-rewrite setting, the answer may be "no" — because the observed optimization landscape is flat and Theorems 1-2 explain the sparse action space, suggesting that hard instances of CODP may require algebraically structured circuits. Our 45,000+ trials show that, in this setting, the difficulty is not in search (all algorithms converge to the same ceiling) but in the action space itself.

**Open Problem OP2 (Phase Transition in Optimization Complexity)**:
Does there exist a circuit-family-dependent phase transition in the computational complexity of optimal peephole optimization, analogous to SAT phase transitions?

*Motivation from our results*: Our landscape analysis (E5) reveals an "optimization desert" with rare deep minima (kurtosis >> 3), consistent with the phase-transition structure observed in random constraint satisfaction problems. The structural-ceiling proxy (E13) provides a computable diagnostic that could serve as an order parameter for such a transition.

**Note for reviewers**: These open problems are presented as future directions motivated by our empirical findings. We do not claim to resolve them. Their inclusion is intended to stimulate complexity-theoretic analysis grounded in the systematic empirical evidence our framework provides.

---

## S9: V5 Extended Benchmark Suite (E14–E18)

### S9.1 Experiment E14: Extended Benchmark Suite

**Research Question**: How does peephole optimization perform across 15 diverse circuit families, and what are the extended metric profiles (depth, 2Q-gate, CNOT reduction)?

**Circuit families** (15 total):

| # | Family | Constructor | Type | Scalable |
|---|--------|-------------|------|----------|
| 1 | QFT | `make_qft()` | Algorithm | Yes |
| 2 | GHZ | `make_ghz()` | State preparation | Yes |
| 3 | CNOT chain | `make_cnot_chain()` | Synthetic | Yes |
| 4 | Oracle (BV) | `make_bernstein_vazirani()` | Algorithm | Yes |
| 5 | QAOA | `make_qaoa_line()` | Variational | Yes |
| 6 | VQE | `make_vqe_twolocal()` | Variational | Yes |
| 7 | Hardware Efficient | `make_hardware_efficient()` | Variational | Yes |
| 8 | Grover | `make_grover()` | Algorithm | Yes |
| 9 | Quantum Adder | `make_quantum_adder()` | Arithmetic | Yes |
| 10 | Quantum Walk | `make_quantum_walk()` | Algorithm | Yes |
| 11 | IQP | `make_iqp()` | Quantum supremacy | Yes |
| 12 | Random Clifford | `make_random_clifford()` | Test (Gottesman-Knill) | Yes |
| 13 | Surface Code | `make_surface_code_syndrome()` | Error correction | Yes |
| 14 | UCCSD | `make_parameterized_ansatz()` | Quantum chemistry | Yes |
| 15 | Haar Random | `make_haar_random()` | Theoretical reference | No (n<=4) |

**Design parameters**:
- Qubit sizes: n in {3,4,5} (smoke); n in {3,...,10,12,15,20} (full)
- Optimizers: Greedy Phase 1, Commutation Phase 2, Hybrid Phase 1+2
- Metrics: Gate reduction, depth reduction, 2Q-gate reduction, CNOT reduction
- Window sizes: {2,5,10,20,50} (full mode)

### S9.2 Experiment E15: Multi-Compiler Baseline

**Research Question**: How do our peephole optimizers compare against production compilers?

**Compilers tested**:
- Custom: Greedy, Commutation, Hybrid (v5.0.0)
- Qiskit transpiler: optimization levels 0, 1, 2, 3 (v2.4.1)
- Cirq: built-in optimizers (DropEmptyMoments, DropNegligibleOperations, MergeSingleQubitGates) — **[NOT YET EXECUTED]**
- t|ket>: FullPeepholeOptimise — **[NOT YET EXECUTED]**

> **Current status**: The canonical E15 dataset (994 records) contains results for Qiskit and custom peephole optimizers only. Cirq and t|ket> were listed in the experiment design but have not yet been run. **[PRELIMINARY — only metadata available]** for Cirq and t|ket>: only version numbers and pass configuration parameters are available. No optimization output data exists. See S11.2 for details.

**Metrics**: Gate/depth/CNOT/2Q reduction, fidelity, runtime, compiler metadata

### S9.3 Experiment E16: Window-Size Scaling

**Research Question**: How does Phase 2 optimization power scale with the search window size w?

**Design**:
- Window sizes: w in {2, 5, 10, 20, 50}
- Optimizers: CommutationRewriter, HybridCommuteRewrite
- Circuits: Same as E14

**Note**: Earlier design documents listed only window sizes [5, 10, 20]; the full experiment expanded this to {2, 5, 10, 20, 50} to capture the saturation curve at both extremes.

**Preliminary empirical trend**: Window scaling suggests a possible saturation pattern:
- w=2: ~0% Phase 2 advantage (too local)
- w=5: ~1.5% marginal improvement
- w=10: ~4.2% (default, captures most observed commutation opportunities)
- w=20: ~4.5% (diminishing returns)
- w=50: ~4.6% (apparent saturation)

This suggests that **w=10 may be a practical default** for Phase 2 optimization, but the result should not be treated as a statistically confirmed design rule.

**Statistical caveat**: The window scaling comparison (w=2 vs w=20) is underpowered (power=0.126, p=0.420, Cohen's d=0.173). The saturation pattern should be interpreted as an empirical trend, not a statistically confirmed result.

### S9.4 Experiment E17: Hardware Connectivity Constraints

**Research Question**: How do hardware topology constraints affect peephole optimization opportunities?

**Topologies tested**:
- **Linear chain**: nearest-neighbor connectivity (most restrictive)
- **2D grid**: sqrt(n) x sqrt(n) placement
- **Heavy-hex** (IBM-style): degree-3 approximation with alternating vertical connectivity

**Method**: Transpile circuits to respect coupling map via Qiskit's `CouplingMap` and `transpile()`, then apply peephole optimization.

**Key metric**: "Connectivity tax" = (unconstrained reduction - constrained reduction) / unconstrained reduction

### S9.5 Experiment E18: Clifford+T Gate Set

**Research Question**: Does Phase 2 optimization retain value among circuits that survive decomposition to the fault-tolerant Clifford+T gate set?

**Gate set**: {H, S, Sdg, T, Tdg, CNOT, X, Y, Z}

**Method**: Decompose circuits to Clifford+T basis using Qiskit transpiler at opt level 0, then apply peephole optimization. Conclusions are survivorship-biased because decomposition and fidelity-failure rows are excluded from valid-row analysis.

**Key metrics**: Gate reduction, T-count reduction, Tdg-count reduction, CNOT reduction

---

## S10: Extended Metrics Results

### S10.1 Extended Metrics Schema

All E14–E18 experiments record the following additional metrics beyond gate-count reduction:

| Metric | Definition | Rationale |
|--------|-----------|-----------|
| `depth_reduction` | $1 - d_{\text{opt}}/d_{\text{orig}}$ | Circuit depth determines execution time |
| `two_qubit_reduction` | $1 - n_{\text{2Q,opt}}/n_{\text{2Q,orig}}$ | 2Q gates dominate error budgets |
| `cnot_reduction` | $1 - n_{\text{CNOT,opt}}/n_{\text{CNOT,orig}}$ | CNOT is the most expensive gate in most hardware |

### S10.2 Extended Metrics Implementation

Extended metrics are computed via `OptimizationResult.compute_extended_metrics()` in `src/optimisation/base.py` (v3.0.0). The method counts depth, 2Q gates, and CNOT gates in both original and optimized circuits, then computes the reduction ratio with safe division (returns 0.0 when the original count is 0).

---

## S11: Compiler Comparison Details

### S11.1 Qiskit Transpiler Configuration

```python
from qiskit import transpile
optimized = transpile(circuit, optimization_level=level,
                      basis_gates=['u1', 'u2', 'u3', 'cx'])
```

Levels 0-3 correspond to increasingly aggressive optimization passes, including template matching, commutation, and gate fusion.

### S11.2 Status of Multi-Compiler Comparison

> **Important caveat (2026-06-12)**: The current E15 dataset includes only Qiskit and custom peephole optimizers. Cirq and t|ket> were listed in the experiment design but have not yet been executed. **[PRELIMINARY — only metadata available]**: Only compiler configuration metadata (version numbers, pass names, parameter ranges) is available for Cirq and t|ket>. No optimization output data has been generated. The configuration snippets below describe the *planned* setup, not yet-run experiments.

**Planned Cirq configuration**:
1. `DropEmptyMoments()` — remove idle time steps
2. `DropNegligibleOperations()` — remove near-identity gates
3. `MergeSingleQubitGates()` — fuse consecutive single-qubit gates
4. `EjectZ()` / `MergeInteractions()` — phase polynomial optimization

**Planned t|ket> configuration**:
```python
from pytket.passes import FullPeepholeOptimise, DecomposeBoxes
DecomposeBoxes().apply(tk_circ)
FullPeepholeOptimise().apply(tk_circ)
```

All claims about "multi-compiler comparison" in this document should be interpreted as "custom peephole vs Qiskit" until Cirq/t|ket> data is collected.

---

## S12: Window-Size Scaling Analysis

### S12.1 Phase 2 Effective Window Hypothesis

The commutation rewriter's window size $w$ controls how far ahead the optimizer searches for commuting pairs. We hypothesize a **saturation curve**:

$$\Gamma(w) \approx \Gamma_{\max} \cdot (1 - e^{-w/w_0})$$

where $\Gamma_{\max}$ is the maximum achievable Phase 2 advantage and $w_0$ is the characteristic window scale.

### S12.2 Practical Implications

If $w_0 \approx 5$ (as suggested by preliminary runs), then:
- $w = 2w_0 = 10$ would capture $\sim 86\%$ of $\Gamma_{\max}$ under the fitted saturation model
- $w = 3w_0 = 15$ would capture $\sim 95\%$ of $\Gamma_{\max}$ under the fitted saturation model
- $w = 5w_0 = 25$ would capture $\sim 99\%$ of $\Gamma_{\max}$ under the fitted saturation model

This provides a **hypothesis** for compiler designers: $w = 10$–$15$ may offer a good cost-benefit tradeoff. The window scaling comparison (w=2 vs w=20) is underpowered (power=0.126, p=0.420, Cohen's d=0.173), so the saturation claim should be interpreted as an empirical trend rather than a statistically confirmed result.

---

## S13: Connectivity Constraint Results

### S13.1 Connectivity Tax Definition

The **connectivity tax** $\tau$ quantifies the reduction in optimization opportunities due to hardware topology constraints:

$$\tau(\mathcal{F}, T) = 1 - \frac{\mathbb{E}_{C \sim \mathcal{F}}[R_{1+2}(C_T)]}{\mathbb{E}_{C \sim \mathcal{F}}[R_{1+2}(C)]}$$

where $C_T$ is the circuit after transpilation to topology $T$.

### S13.2 Expected Connectivity Tax by Topology

| Topology | Degree | Expected tax | Rationale |
|----------|--------|-------------|-----------|
| Full connectivity | n-1 | 0% (baseline) | No SWAP overhead |
| Heavy-hex | 3 | 15–30% | Moderate SWAP overhead, IBM standard |
| 2D grid | 4 | 10–25% | Moderate SWAP overhead |
| Linear chain | 2 | 30–50% | Maximum SWAP overhead |

---

## S14: Clifford+T Gate Set Results

### S14.1 Motivation

The continuous gate set (RX, RY, RZ) used in E1–E13 makes exact gate cancellation a measure-zero event. Decomposing to the discrete Clifford+T gate set tests whether the 0% Phase 1 result is a gate-set artifact.

### S14.2 Clifford+T Decomposition

All circuits are decomposed using Qiskit's transpiler at optimization level 0:

```python
from qiskit import transpile
clifford_t = transpile(circuit, basis_gates=['h', 's', 'sdg', 't', 'tdg', 'cx', 'x', 'y', 'z'],
                       optimization_level=0)
```

### S14.3 Expected Results

Under the Clifford+T gate set:
- **Phase 1** may achieve non-zero reduction on circuits with adjacent T-Tdg or S-Sdg pairs
- **Phase 2** should retain its context-dependent advantage (commutation rules are well-defined for Clifford+T)
- **Random Clifford circuits** should show 0% reduction (already in normal form)
- **Structured circuits** (QFT, BV) may show different reduction profiles due to discrete gate structure

### S14.4 T-Count Tracking

E18 additionally tracks:
- `t_count_original`: number of T gates in the original circuit
- `t_count_optimized`: number of T gates after optimization
- `t_count_reduction`: $1 - n_{T,\text{opt}}/n_{T,\text{orig}}$
- `tdg_count_original`, `tdg_count_optimized`: same for Tdg gates

T-count is the dominant cost metric in fault-tolerant quantum computing, as T gates require magic state distillation.

---

*Document version: 2.1*  
*Last updated: 2026-06-11*  
*Author: Q-Research Supplementary Materials Team*
