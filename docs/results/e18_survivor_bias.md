# E18 Clifford+T Decomposition: Survivorship Bias Analysis

> **Date**: 2026-07-12  
> **Data**: `data/v5/e18/e18_clifford_t_e18_full_20260610_052140.csv` (270 rows)  
> **Script**: `scripts/e18_survivor_bias_report.py`  
> **Summary CSV**: `data/v5/e18/e18_survivor_bias_report.csv`

---

## 1. Failure Rate Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| Total rows | 270 | 100% |
| Successful (ok) | 192 | 71.1% |
| Failed (decompose_error) | 78 | 28.9% |

**Note**: An additional 42 rows have fidelity = 0 (numerical precision failure after successful decomposition). Including these, the total failure rate is 120/270 = 44.4%.

---

## 2. Per-Family Failure Distribution

### Families with 0% Failure (6 families, 192 successful rows)
| Family | Total | Failed | Failure Rate |
|--------|-------|--------|--------------|
| Adder | 24 | 0 | 0.0% |
| CNOT | 33 | 0 | 0.0% |
| GHZ | 33 | 0 | 0.0% |
| Oracle (BV) | 33 | 0 | 0.0% |
| RandomClifford | 33 | 0 | 0.0% |
| SurfaceCode | 33 | 0 | 0.0% |

### Families with Partial Failure (1 family)
| Family | Total | Failed | Failure Rate |
|--------|-------|--------|--------------|
| Grover | 10 | 7 | 70.0% |

### Families with 100% Failure (8 families, 78 failed rows)
| Family | Total | Failed | Failure Rate |
|--------|-------|--------|--------------|
| HaarRandom | 3 | 3 | 100% |
| HardwareEfficient | 11 | 11 | 100% |
| IQP | 11 | 11 | 100% |
| QAOA | 11 | 11 | 100% |
| QFT | 11 | 11 | 100% |
| QuantumWalk | 8 | 8 | 100% |
| UCCSD | 8 | 8 | 100% |
| VQE | 8 | 8 | 100% |

---

## 3. Per-Optimizer Failure Rate

All 78 failures occur in the `none` optimizer (baseline, before any optimization). The three optimizers (greedy_phase1, commutation_phase2, hybrid_phase1_2) each have 64 rows with 0 failures, because they only run on circuits where decomposition succeeded.

| Optimizer | Total | Failed | Failure Rate |
|-----------|-------|--------|--------------|
| none (baseline) | 78 | 78 | 100% |
| greedy_phase1 | 64 | 0 | 0% |
| commutation_phase2 | 64 | 0 | 0% |
| hybrid_phase1_2 | 64 | 0 | 0% |

---

## 4. Survivorship Bias Assessment

**WARNING**: The E18 analysis subset of 192/270 rows (71.1%) excludes circuits that failed Clifford+T decomposition. Statistics computed on this subset suffer from **SURVIVOR BIAS**:

1. **Selection effect**: Only 6–7 out of 15 circuit families can be successfully decomposed to Clifford+T. The surviving families (Adder, CNOT, GHZ, Oracle, RandomClifford, SurfaceCode, partial Grover) are structurally simpler circuits with discrete gate sets that naturally admit Clifford+T representation.

2. **Excluded families**: The 8 families that completely fail (QFT, HardwareEfficient, IQP, QAOA, QuantumWalk, UCCSD, VQE, HaarRandom) contain continuous rotation gates (Rz, Ry, Rx with arbitrary angles) that cannot be exactly represented in the Clifford+T gate set without Solovay-Kitaev approximation.

3. **Generalizability**: Conclusions about Clifford+T optimization effectiveness apply ONLY to circuits with naturally discrete gate sets. They do NOT generalize to:
   - Variational circuits (VQE, QAOA, UCCSD) with continuous parameters
   - Arithmetic circuits (QFT, Adder with non-Clifford rotations)
   - Random/hardware-efficient circuits with diverse gate sets

4. **Impact on manuscript claims**: The manuscript MUST:
   - Report the complete failure rate (28.9% decompose_error + 15.6% fidelity=0 = 44.4% total)
   - List which families succeeded and which failed
   - State that E18 conclusions are conditional on successful decomposition
   - Discuss the structural reasons for failure (continuous vs discrete gate sets)
   - Acknowledge that the most practically relevant circuits (VQE, QAOA) are excluded

---

## 5. Recommendations

1. **In the manuscript**: Add a dedicated subsection (e.g., "5.4.4 E18 Limitations: Survivorship Bias") that reports the failure distribution and states the conditional nature of the results.

2. **Future work**: Implement Solovay-Kitaev approximation for the failed families to enable at least approximate Clifford+T decomposition, extending coverage to 12–13 of 15 families.

3. **Data transparency**: The `e18_survivor_bias_report.csv` file should be included in the supplementary materials.
