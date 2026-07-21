# Ceiling Model Failure Diagnosis

**Date**: 2026-07-17
**Status**: Confirmed — LOFO CV reproduces HGC with richer features + Random Forest

---

## 1. Executive Summary

The ceiling-aware prediction model fails to generalize to unseen circuit families. A rigorous leave-one-family-out (LOFO) cross-validation using Random Forest with 7 structural features on 570 E21 trials (15 families) yields:

| Metric | LOFO CV | Always-0 Baseline | Original HGC |
|--------|---------|-------------------|--------------|
| MAE | 0.0980 | 0.0963 | 0.2775 |
| Pearson r | -0.0147 | — | NaN |
| R² | -0.135 | -0.133 | — |
| Clf F1 | 0.07 | — | — |

The model is **no better than always predicting zero**. This confirms the HGC is not an artifact of the original 5-family held-out set, but a fundamental limitation: available structural features cannot distinguish reducible from ceiling families when the family itself is unseen.

---

## 2. Data Profile (E21, 570 naive rows)

| Family | n | Mean Reduction | Std Reduction | Reducible? |
|--------|---|---------------|---------------|------------|
| CNOT | 40 | 1.0000 | 0.0000 | Yes |
| RandomClifford | 40 | 0.1936 | 0.0800 | Yes |
| Oracle | 40 | 0.1585 | 0.2330 | Yes |
| Grover | 40 | 0.0194 | 0.0295 | Yes (partial) |
| UCCSD | 40 | 0.0010 | 0.0063 | Borderline |
| Others (10) | 40ea | 0.0000 | 0.0000 | No |

Only 4/15 families have reliably nonzero reduction. The target distribution is heavily zero-inflated (73% ceiling).

---

## 3. Root Cause Analysis

### 3.1 Structural Confirmation of HGC

The original HGC was reported as a 5-family held-out failure. The LOFO CV reveals the problem is **more fundamental**: every family has unique structural properties that the available features cannot capture. When CNOT (100%) is held out, the model sees only Oracle (16%) and RandomClifford (19%) as reducible training examples — it cannot extrapolate to 100%.

Per-fold results:

| Held-out | MAE | Pearson r | Clf Acc | Root Cause |
|----------|-----|-----------|---------|------------|
| CNOT | 1.0000 | NaN | 0.00 | Only family with 100% reduction |
| RandomClifford | 0.1868 | 0.306 | 0.03 | Only family with ~19% moderate reduction |
| Oracle | 0.1585 | NaN | 0.60 | Only family with high-variance reduction |
| Grover | 0.0194 | NaN | 0.60 | Only family with ~2% reduction |
| UCCSD | 0.0055 | 1.000 | 1.00 | 1/40 reducible circuits; lucky guess |
| 10 ceiling families | 0.000-0.027 | NaN | 1.00 | True ceiling — trivial prediction |

### 3.2 Why Pearson = NaN (Per-Fold)

Pearson is undefined when either variable has zero variance. For 13/15 folds, `actual_reduction` has zero variance (all test circuits are either all-ceiling at 0%, or all-reducible with identical reduction like CNOT at exactly 100%). Only RandomClifford (variance due to qubit size variation) and UCCSD (one outlier) have nonzero variance in the test set.

### 3.3 Why MAE = 0.098 (vs baseline 0.096)

The model essentially predicts 0 for everything, same as the baseline. The 0.002 MAE difference is below the noise floor. For reducible families like CNOT, the MAE contribution is 1.0 (predicts 0, actual 1.0 × 40/570 = 0.070), accounting for most of the 0.098 total.

### 3.4 Why Classification F1 = 0.07

The classifier achieves 80% accuracy but F1 = 0.07. This is a classic class imbalance failure: the classifier learns to predict "ceiling" for everything (precision = 0 when it does predict "reducible"), because 73% of training data is ceiling.

---

## 4. Feature Analysis

All features have similar low importance (0.03–0.12 each). The top features are:
- `inverse_pair_density` (ceiling proxy / total gates)
- `is_ceiling_proxy_binary` (binary flag for proxy=0)
- `depth_to_width_ratio`

No single feature dominates — the model cannot find a reliable signal.

---

## 5. Diagnostic Conclusion

The HGC is **confirmed and deeper than previously reported**:

1. **The original held-out failure (MAE=0.2775, Pearson=NaN)** was correctly identified
2. **LOFO CV with richer features reproduces the failure**: MAE=0.098 vs baseline 0.096
3. **Root cause**: The target distribution is zero-inflated (73% ceiling), with only 4 families having nonzero reduction, each at a different magnitude. No family has enough structural similarity to another to enable cross-family generalization.
4. **Implication**: The predictive claim should be downgraded from "exploratory analysis" to "negative result" in the current manuscript framework. Future work requires per-circuit-family regression with within-family variation, not cross-family generalization.
