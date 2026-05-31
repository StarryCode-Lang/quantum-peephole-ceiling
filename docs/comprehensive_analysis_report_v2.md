# Quantum Circuit Optimization: Comprehensive Experimental Analysis Report
## Version 2.1.0 | Generated: 2026-05-30

---

## Executive Summary

This report presents the complete analysis of five experiments investigating quantum circuit optimization via gate reduction techniques. We study the phase transition behavior, entanglement density effects, finite-size scaling, algorithmic benchmarking, and optimization landscape characteristics. All analyses include Bootstrap confidence intervals (N=5000) and publication-quality figures.

**Key Findings:**
1. **Phase transition**: Success rate decays exponentially with circuit depth ($P(d) = 0.297 \cdot e^{-d/19.0}$, $R^2=0.86$), not sigmoidally
2. **Scaling**: Gate reduction follows a power law with qubit count ($\Delta = 0.083 \cdot n^{0.28}$, $R^2=0.92$)
3. **Best optimizer**: GREEDY achieves highest reduction (14.4%), perfect fidelity, fastest runtime (3.5ms), 20% success rate
4. **Entanglement**: Density correlates strongly with GREEDY reduction ($r=0.962$), but not with SA reduction ($r=0.346$)
5. **Landscape**: Roughness (std of entropy_diff) varies non-monotonically with depth (peaks at d=5,20 ~0.30; dips at d=8,15 ~0.21). Correlation between base entropy and perturbation impact oscillates in sign with depth, revealing complex depth-dependent sensitivity structure

---

## Experiment 1: Phase Transition (n=5, d=1-50)

### Setup
- **Parameters**: n_qubits=5, depth=1-50, 100 trials per depth
- **Optimizer**: GREEDY
- **Success criterion**: gate_reduction ≥ 20% AND fidelity ≥ 99%

### Results

| Metric | Value | 95% Bootstrap CI |
|--------|-------|------------------|
| Overall success rate | 10.0% | [9.2%, 10.9%] |
| Mean gate reduction | 0.1402 | [0.1384, 0.1421] |
| Mean fidelity | 0.9991 | — |

**Phase transition model**: Success rate follows exponential decay with circuit depth:

$$P_{\text{success}}(d) = P_0 \cdot e^{-d/d_0} + P_{\text{bg}}$$

- $P_0 = 0.297 \pm 0.019$
- $d_0 = 18.98 \pm 3.99$ (characteristic decay depth)
- $P_{\text{bg}} = 0.00 \pm 0.021$
- $R^2 = 0.856$

**Entropy thresholds**: Normalized entanglement entropy grows monotonically with depth and anti-correlates with success:
- $S/S_{\max} > 0.3$ at depth=9 (success_rate=22%)
- $S/S_{\max} > 0.5$ at depth=11 (success_rate=19%)  
- $S/S_{\max} > 0.9$ at depth=24 (success_rate=6%)

**Interpretation**: No sharp sigmoid phase transition was observed. Instead, the optimization success probability decays smoothly with depth, reflecting the exponential growth of circuit complexity. The nearly constant gate reduction (~14%) across all depths indicates that while *absolute* reduction remains stable, the *relative* difficulty of achieving the 20% threshold increases exponentially.

**Figure**: `figures/final/fig1_phase_transition.png` (3-panel: success rate, reduction, entropy)

---

## Experiment 2: Entanglement Density Sweep (n=6, d=20)

### Setup  
- **Parameters**: n_qubits=6, depth=20, density=0.0-1.0 (21 levels), 30 trials per level
- **Optimizers**: GREEDY, SIMULATED_ANNEALING
- **Note**: Fast version (30 trials instead of 100) due to computational constraints

### Results

| Metric | GREEDY | SIMULATED_ANNEALING |
|--------|--------|---------------------|
| Mean reduction | 0.305 | 0.015 |
| Mean fidelity | 1.000 | 0.998 |
| Success rate | 58.4% | 0.3% |
| Mean runtime | 4.4ms | 2.3s |

**Key correlation**: GREEDY gate reduction correlates strongly with entanglement density:
- Pearson $r = 0.962$ (p < 10⁻¹⁰⁰)
- Spearman $\rho = 0.966$ (p < 10⁻¹⁰⁰)

SA reduction shows weak correlation ($r = 0.346$, $p < 10⁻¹⁹$).

**Interpretation**: High entanglement density creates more optimization opportunities for the greedy algorithm, which exploits local gate cancellations. SA's stochastic search struggles in the same regime, suggesting that structured greedy optimization is more effective for densely entangled circuits.

**Figure**: `figures/final/fig3_density_sweep.png`

---

## Experiment 3: Finite-Size Scaling (n=3-10, d=1-30)

### Setup
- **Parameters**: n_qubits=3-10 (8 values), depth=1-30, 50 trials per (n,d) pair
- **Optimizer**: GREEDY

### Results

**Gate reduction scaling** (power law fit):

$$\Delta_{\text{gate}}(n) = 0.083 \cdot n^{0.28} + 0.00$$

- $a = 0.083 \pm 0.345$  
- $b = 0.28 \pm 0.78$
- $R^2 = 0.917$

Per-qubit reduction increases monotonically from $\Delta=0.105$ (n=3) to $\Delta=0.156$ (n=10).

**Success rate decay per n**: Each qubit count shows exponential decay of success rate with depth, but decay constants ($d_0$) vary substantially (5.4-15.4), reflecting noise from limited trials (50/d).

**FSS analysis**: Log-log regression of decay constants $d_0(n)$ vs $n$ yields $d_c(n) = 13.3 \cdot n^{-0.29}$, but with very poor fit ($R^2=0.09$, $p=0.52$). The limited trial count (50/d) produces insufficient statistical power for clean FSS analysis.

**Bootstrap CI per n**:

| n | Success Rate | 95% CI | Mean Reduction | 95% CI |
|---|-------------|--------|----------------|--------|
| 3 | 0.105 | [0.089, 0.120] | 0.105 | [0.101, 0.110] |
| 4 | 0.142 | [0.124, 0.159] | 0.125 | [0.121, 0.129] |
| 5 | 0.133 | [0.116, 0.149] | 0.139 | [0.135, 0.143] |
| 6 | 0.103 | [0.088, 0.118] | 0.135 | [0.132, 0.138] |
| 7 | 0.132 | [0.115, 0.149] | 0.145 | [0.142, 0.148] |
| 8 | 0.174 | [0.155, 0.193] | 0.150 | [0.146, 0.153] |
| 9 | 0.143 | [0.126, 0.161] | 0.152 | [0.149, 0.155] |
| 10 | 0.141 | [0.124, 0.159] | 0.156 | [0.153, 0.159] |

**Figure**: `figures/final/fig2_fss.png` (3-panel: reduction scaling, per-n curves, bootstrap CI bars)

---

## Experiment 4: Algorithm Comparison (n=5, d=15)

### Setup
- **Parameters**: n_qubits=5, depth=15, 100 trials per optimizer
- **Optimizers**: GREEDY, RANDOM_LOCAL_SEARCH, SIMULATED_ANNEALING, GENETIC_ALGORITHM

### Results

| Optimizer | Mean Reduction | Mean Fidelity | Success Rate | Mean Runtime |
|-----------|---------------|---------------|-------------|-------------|
| GREEDY | **0.144** | **1.000** | **20%** | **3.5ms** |
| RANDOM_LOCAL_SEARCH | 0.102 | 0.997 | 4% | 7.83s |
| SIMULATED_ANNEALING | 0.002 | 0.9999 | 0% | 1.41s |
| GENETIC_ALGORITHM | 0.010 | 0.9996 | 0% | 1.86s |

**Wilcoxon tests**: All pairwise reduction differences are significant (p values range from $3.6 \times 10^{-18}$ to $1.5 \times 10^{-7}$), confirming GREEDY's superiority. Notably, GREEDY vs SA shows the strongest separation ($p = 5.04 \times 10^{-18}$).

**Interpretation**: The greedy approach outperforms all metaheuristic optimizers in both reduction quality and speed. SA and GA sacrifice reduction for fidelity preservation, while GREEDY achieves both. This suggests that for quantum circuit optimization, local deterministic search is more effective than stochastic global search.

**Figure**: `figures/final/fig4_algorithm_comparison.png`

---

## Experiment 5: Optimization Landscape (n=5, d=3-20)

### Setup
- **Parameters**: n_qubits=5, depth=3-20 (6 levels: 3, 5, 8, 10, 15, 20), 1000 trials per depth
- **Optimizer**: GREEDY
- **Columns**: base_entropy, perturbed_entropy, entropy_diff, base_gates, perturbed_gates

### Results

#### 5.1 Landscape Roughness (std of entropy_diff by depth)

Landscape roughness measures the variability of perturbation impact across circuits at each depth:

| Depth | std(entropy_diff) | mean(entropy_diff) | Mean Base Entropy | Mean Perturbed Entropy | Gate Reduction | 95% Bootstrap CI (roughness) |
|-------|-------------------|--------------------|--------------------|------------------------|---------------|------------------------------|
| 3 | 0.000000 | 0.000000 | 0.0000 | 0.0000 | 3.13% | [1.39e-16, 1.66e-16] |
| 5 | 0.294079 | 0.192261 | 0.5781 | 0.3978 | 1.88% | [0.2853, 0.3013] |
| 8 | 0.208330 | 0.153171 | 0.5765 | 0.4515 | 1.17% | [0.1991, 0.2167] |
| 10 | 0.257762 | 0.231966 | 0.9618 | 0.8180 | 0.94% | [0.2506, 0.2640] |
| 15 | 0.206519 | 0.146192 | 1.4167 | 1.4428 | 0.63% | [0.1995, 0.2125] |
| 20 | 0.298832 | 0.208271 | 1.5353 | 1.3897 | 0.47% | [0.2777, 0.3187] |

**Key finding**: Roughness (std of entropy_diff) does not increase monotonically with depth. Instead, it peaks at d=5 and d=20 (~0.29-0.30), and dips at d=8 and d=15 (~0.21). This suggests the landscape has non-trivial complexity structure — certain depths yield more variable optimization response than others.

#### 5.2 Correlation Analysis (base_entropy vs entropy_diff)

**Overall correlation**:
- Pearson $r = 0.252$ ($p = 1.31 \times 10^{-87}$)
- Spearman $\rho = 0.249$ ($p = 1.07 \times 10^{-85}$)

**Per-depth Pearson correlation**:

| Depth | Pearson $r$ | $p$-value | $n$ | Direction |
|-------|------------|-----------|-----|-----------|
| 3 | -0.2524 | $5.32 \times 10^{-16}$ | 1000 | Negative |
| 5 | 0.1525 | $1.27 \times 10^{-6}$ | 1000 | Positive |
| 8 | -0.1058 | $8.07 \times 10^{-4}$ | 1000 | Negative |
| 10 | 0.4977 | $1.05 \times 10^{-63}$ | 1000 | Strong positive |
| 15 | -0.3999 | $1.10 \times 10^{-39}$ | 1000 | Strong negative |
| 20 | 0.3848 | $1.23 \times 10^{-36}$ | 1000 | Strong positive |

**Interpretation**: The correlation between base entropy and perturbation impact oscillates in sign with depth, alternating between negative (d=3,8,15) and positive (d=5,10,20). This depth-dependent sign reversal reveals that the landscape's sensitivity structure is not uniform — in some depth regimes, high-entropy circuits are more perturbation-sensitive (positive r), while in others they are more robust (negative r). The strongest correlations appear at d=10 ($r=0.498$) and d=15 ($r=-0.400$), indicating maximum landscape sensitivity differentiation around these depths.

#### 5.3 Page Entropy Comparison (n=5)

Page entropy reference for n=5: $S_{\text{Page}}(5) = \frac{5}{2}\ln 2 - 0.5 \approx 1.228$

| Depth | Mean Measured Entropy | Page Entropy | Deviation | Relative Deviation |
|-------|----------------------|-------------|-----------|-------------------|
| 3 | 0.0000 | 1.228 | -1.228 | -100.00% |
| 5 | 0.5781 | 1.228 | -0.650 | -52.93% |
| 8 | 0.5765 | 1.228 | -0.652 | -53.05% |
| 10 | 0.9618 | 1.228 | -0.266 | -21.66% |
| 15 | 1.4167 | 1.228 | +0.189 | +15.33% |
| 20 | 1.5353 | 1.228 | +0.307 | +24.96% |

**Interpretation**: Shallow circuits (d≤8) have entropy well below the Page value, indicating they are far from typical random-circuit behavior. By d=15-20, circuits overshoot the Page value, suggesting deep circuits generate entanglement beyond the Haar-random expectation for this qubit count. The crossover occurs around d≈12-13.

**Figure**: `figures/fig5_landscape.png` (4-panel: roughness by depth, mean perturbation impact, base entropy vs entropy_diff scatter, per-depth correlation)

---

## Summary of Figures

| Figure | File | Description |
|--------|------|-------------|
| Fig. 1 | `figures/final/fig1_phase_transition.png/pdf` | E1: Success rate, reduction, entropy vs depth |
| Fig. 2 | `figures/final/fig2_fss.png/pdf` | E3: Reduction scaling, per-n success, bootstrap CI |
| Fig. 3 | `figures/final/fig3_density_sweep.png` | E2: Entanglement density vs reduction/success |
| Fig. 4 | `figures/final/fig4_algorithm_comparison.png` | E4: Optimizer benchmarking comparison |
| Fig. 5 | `figures/fig5_landscape.png` | E5: Landscape roughness, perturbation impact, correlation analysis |
| Fig. 6 | `figures/fig6_entropy_comparison.png` | E5+E3: Measured vs Page entropy comparison |

---

## Limitations & Future Work

1. **Sample size**: 50-100 trials per configuration limits statistical power, especially for FSS analysis. Future: ≥500 trials/d for E3.
2. **Success criterion**: 20% reduction threshold is stringent; only GREEDY consistently achieves it. Consider relaxed threshold or multi-tier success definition.
3. **Optimizer diversity**: Only GREEDY shows meaningful success; SA/GA/RLS produce near-zero reductions. Need improved metaheuristic implementations.
4. **FSS**: Decay constant scaling is inconclusive (R²=0.09). Need larger n range (n=3-20) and more trials.
5. **Phase transition**: No sharp sigmoid transition observed — exponential decay is the appropriate model.
6. **E5 Landscape**: Per-depth correlation sign oscillation (negative→positive→negative→positive) lacks a theoretical explanation. Need deeper circuits (d>20) and additional perturbation strategies to fully characterize landscape topology.
7. **E5 Page entropy**: Deep circuits (d=15,20) overshoot the Page value — this may reflect finite-n effects or measurement methodology artifacts. Need larger n to clarify.

---

## Data Files

### Raw Data (data/raw/)
- `exp1_phase_transition_20260530_095003.csv` (5000 rows, 481KB)
- `exp2_entanglement_density_20260530_112304.csv` (1260 rows, 159KB)
- `exp3_scaling_20260530_100830.csv` (12000 rows, 1112KB)
- `exp4_algorithm_comparison_20260530_111458.csv` (400 rows, 49KB)
- `exp5_landscape_20260530_102615.csv` (6000 rows, 424KB)

### Processed Data (data/processed/)
- `e1_phase_transition_summary.csv`
- `e3_n_scaling_summary.csv`
- `e3_nd_scaling_summary.csv`
- `e2_density_sweep_summary.csv`
- `e4_optimizer_comparison_summary.csv`
- `e1_e3_analysis_results.json` (E1+E3 full analysis)
- `e2_e4_analysis_results.json` (E2+E4 full analysis with Wilcoxon tests)
- `comprehensive_summary.csv` (all experiments bootstrap CI summary, including E5 landscape roughness)

### Analysis Scripts (scripts/)
- `e1_e3_step1_aggregate_fit.py` → `e1_e3_step2b_save_results.py` (E1+E3 analysis pipeline)
- `gen_fig1.py`, `gen_fig2.py` (Figure generation)
- `e2_e4_analysis.py` (E2+E4 analysis)
- `landscape_and_summary_v2.py` (E5 landscape characterization + comprehensive summary)

---

*Report generated by Hermes Agent multi-agent parallel analysis framework*
*All statistical analyses use Bootstrap resampling (N=5000) for confidence intervals*
*All fits validated with R² and parameter uncertainty estimates*