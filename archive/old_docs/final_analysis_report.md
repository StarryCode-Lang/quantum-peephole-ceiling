# Final Analysis Report: Quantum Circuit Optimization Research

## Overview

This report presents a comprehensive statistical analysis of quantum circuit optimization experiments, covering landscape characterization (E5), Page entropy comparisons, and summary statistics across all experimental configurations with bootstrap-based 95% confidence intervals.

**Date**: 2026-05-30  
**Total data points**: 24660  
**Total (n, depth) configurations**: 301

---

## 1. Experiment 5: Landscape Characterization

### 1.1 Data Summary

- **Dataset**: `exp5_landscape_20260530_102615.csv`
- **Rows**: 6000
- **n_qubits**: 5
- **Depths tested**: [np.int64(3), np.int64(5), np.int64(8), np.int64(10), np.int64(15), np.int64(20)]
- **Columns**: base_entropy, perturbed_entropy, entropy_diff, base_gates, perturbed_gates

### 1.2 Landscape Roughness

Landscape roughness is measured as the standard deviation of entropy_diff (perturbation impact) at each depth:

| Depth | std(entropy_diff) | mean(entropy_diff) | Count |
|-------|-------------------|--------------------|-------|
| 3.0 | 0.000000 | 0.000000 | 1000.0 |
| 5.0 | 0.294079 | 0.192261 | 1000.0 |
| 8.0 | 0.208330 | 0.153171 | 1000.0 |
| 10.0 | 0.257762 | 0.231966 | 1000.0 |
| 15.0 | 0.206519 | 0.146192 | 1000.0 |
| 20.0 | 0.298832 | 0.208271 | 1000.0 |

**Key finding**: Landscape roughness varies with circuit depth, indicating that optimization landscape complexity changes as circuits deepen.

### 1.3 Correlation Analysis

**Overall correlation (base_entropy vs entropy_diff)**:
- Pearson r = 0.252054, p = 1.314330e-87
- Spearman r = 0.249320, p = 1.068246e-85

**Per-depth Pearson correlation**:

| Depth | Pearson r | p-value | n |
|-------|-----------|---------|---|
| 3.0 | -0.2524 | 5.3190e-16 | 1000.0 |
| 5.0 | 0.1525 | 1.2718e-06 | 1000.0 |
| 8.0 | -0.1058 | 8.0704e-04 | 1000.0 |
| 10.0 | 0.4977 | 1.0532e-63 | 1000.0 |
| 15.0 | -0.3999 | 1.0964e-39 | 1000.0 |
| 20.0 | 0.3848 | 1.2338e-36 | 1000.0 |

**Interpretation**: Correlation between base entropy and perturbation impact reveals sensitivity structure of the landscape. Positive correlation indicates high-entropy regions respond more strongly to gate perturbations.

---

## 2. Page Entropy Reference Values

Page entropy for an n-qubit random circuit: S_Page(n) = n/2 * ln(2) - 0.5

| n_qubits | S_page |
|----------|--------|
| 3 | 0.539721 |
| 4 | 0.886294 |
| 5 | 1.232868 |
| 6 | 1.579442 |
| 7 | 1.926015 |
| 8 | 2.272589 |
| 9 | 2.619162 |
| 10 | 2.965736 |

---

## 3. Measured vs Page Entropy Comparison

### 3.1 E5 Landscape (n=5)

Page entropy reference for n=5: **1.232868**

| Depth | Mean Measured Entropy | Page Entropy | Deviation | Relative Deviation |
|-------|----------------------|-------------|-----------|-------------------|
| 3.0 | 0.000000 | 1.232868 | -1.232868 | -100.0000% |
| 5.0 | 0.578068 | 1.232868 | -0.654800 | -53.1119% |
| 8.0 | 0.576457 | 1.232868 | -0.656411 | -53.2426% |
| 10.0 | 0.961817 | 1.232868 | -0.271051 | -21.9854% |
| 15.0 | 1.416743 | 1.232868 | 0.183876 | 14.9145% |
| 20.0 | 1.535290 | 1.232868 | 0.302422 | 24.5300% |

### 3.2 E3 Scaling Experiment

| n_qubits | Mean Measured | Page Entropy | Deviation | Relative Deviation |
|----------|--------------|-------------|-----------|-------------------|
| 3.0 | 0.575950 | 0.539721 | 0.036229 | 6.7125% |
| 4.0 | 0.864306 | 0.886294 | -0.021989 | -2.4810% |
| 5.0 | 1.056255 | 1.232868 | -0.176613 | -14.3253% |
| 6.0 | 1.001948 | 1.579442 | -0.577493 | -36.5631% |
| 7.0 | 1.157543 | 1.926015 | -0.768472 | -39.8996% |
| 8.0 | 1.348934 | 2.272589 | -0.923654 | -40.6433% |
| 9.0 | 1.200825 | 2.619162 | -1.418337 | -54.1523% |
| 10.0 | 1.361889 | 2.965736 | -1.603847 | -54.0792% |

**Interpretation**: Deviations from Page entropy reveal how circuit depth affects approach to random-circuit behavior. Shallow circuits typically show entropy below Page value; deep circuits approach it.

---

## 4. Comprehensive Statistical Summary

All confidence intervals computed via bootstrap resampling (2000 iterations, 95% CI).

### 4.1 Top 10 Configurations by Success Rate

| Experiment | n_qubits | Depth | Success Rate | 95% CI | Mean Reduction | Mean Fidelity |
|------------|----------|-------|-------------|--------|---------------|---------------|
| E3_scaling | 9 | 1 | 0.6000 | [0.4600, 0.7400] | 0.1689 | 1.0000 |
| E3_scaling | 8 | 1 | 0.5600 | [0.4200, 0.7000] | 0.1650 | 1.0000 |
| E3_scaling | 7 | 1 | 0.4600 | [0.3200, 0.6000] | 0.1486 | 1.0000 |
| E3_scaling | 4 | 2 | 0.4400 | [0.3000, 0.5800] | 0.1250 | 1.0000 |
| E3_scaling | 8 | 2 | 0.4200 | [0.2800, 0.5600] | 0.1625 | 1.0000 |
| E3_scaling | 9 | 2 | 0.4200 | [0.3000, 0.5600] | 0.1489 | 1.0000 |
| E3_scaling | 6 | 3 | 0.4000 | [0.2600, 0.5400] | 0.1267 | 1.0000 |
| E3_scaling | 6 | 1 | 0.3800 | [0.2600, 0.5200] | 0.1333 | 1.0000 |
| E3_scaling | 3 | 3 | 0.3600 | [0.2200, 0.5000] | 0.0956 | 1.0000 |
| E3_scaling | 7 | 4 | 0.3600 | [0.2200, 0.5000] | 0.1486 | 1.0000 |

### 4.2 Aggregate Statistics

- **E1 (Phase Transition)**: Success rate = 0.1004, Mean reduction = 0.1402, Mean fidelity = 1.0000
- **E3 (Scaling)**: Success rate = 0.1339, Mean reduction = 0.1382, Mean fidelity = 1.0000

### 4.3 E5 Landscape Summary (roughness as std(entropy_diff))

| Depth | Roughness (std) | 95% CI |
|-------|----------------|--------|
| 3 | 0.000000 | [0.000000, 0.000000] |
| 5 | 0.293932 | [0.284752, 0.301387] |
| 8 | 0.208225 | [0.199080, 0.216902] |
| 10 | 0.257633 | [0.251085, 0.263820] |
| 15 | 0.206416 | [0.199456, 0.212673] |
| 20 | 0.298683 | [0.277916, 0.317747] |

The complete summary table with all 301 configurations is saved to `data/comprehensive_summary.csv`.

---

## 5. Figures

### Figure 5: `figures/fig5_landscape.png`
Four-panel figure:
- **A**: Landscape roughness (std of entropy_diff) by depth
- **B**: Mean perturbation impact by depth
- **C**: Scatter plot of base_entropy vs entropy_diff with correlation annotation
- **D**: Per-depth correlation strength

### Figure 6: `figures/fig6_entropy_comparison.png`
Two-panel figure:
- **A**: E5 measured base_entropy vs Page entropy reference (n=5)
- **B**: E3 measured entanglement entropy vs Page entropy reference (n=3..10)

---

## 6. Key Findings

1. **Landscape Roughness**: std(entropy_diff) varies with circuit depth, quantifying optimization landscape complexity.

2. **Correlation Structure**: Pearson r=0.2521 between base entropy and perturbation impact reveals landscape sensitivity patterns.

3. **Page Entropy Comparison**: Measured entanglement entropy deviates from Page reference, with deviation patterns showing how depth affects approach to random-circuit behavior.

4. **Optimization Success**: Success rates vary across configurations; bootstrap CIs provide robust uncertainty quantification.

5. **Fidelity Preservation**: Mean fidelity remains near 1.0 across most configurations, confirming gate reduction preserves circuit function.

---

## 7. Data Files

| File | Description |
|------|-------------|
| `data/raw/exp5_landscape_20260530_102615.csv` | E5 landscape data (6000 rows) |
| `data/raw/exp1_phase_transition_20260530_095003.csv` | E1 phase transition data |
| `data/raw/exp2_entanglement_density_20260530_112304.csv` | E2 entanglement density data |
| `data/raw/exp3_scaling_20260530_100830.csv` | E3 scaling data |
| `data/raw/exp4_algorithm_comparison_20260530_111458.csv` | E4 algorithm comparison data |
| `data/comprehensive_summary.csv` | Full statistical summary with bootstrap CIs |
| `figures/fig5_landscape.png` | Landscape characterization figure |
| `figures/fig6_entropy_comparison.png` | Entropy comparison figure |

---

*Report generated automatically from experimental data analysis pipeline.*
