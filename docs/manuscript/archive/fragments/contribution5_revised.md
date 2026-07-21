> **STATUS**: Not yet integrated into main manuscript. Pending merge.

## 5.5 Ceiling-Aware Optimization (Revised)

**Status**: Supplementary observation with confirmed limitations.

The structural-ceiling framework's most direct practical application is ceiling-aware optimization: using a fast proxy to skip futile optimization phases, reducing compilation time without sacrificing output quality. This section presents two distinct but related components:

1. **CeilingAwareOptimizer** (Section 5.5.1) — a rule-driven compiler pass that computes structural proxies at O(m) cost and skips phases with empty action spaces. This is a deterministic decision rule, not a learned model.

2. **Empirical prediction model** (Section 5.5.2) — a machine learning regression model that attempts to predict gate reduction from structural features. **This model fails to generalize to unseen circuit families** and is reclassified as a confirmed negative result.

The distinction is critical: the CeilingAwareOptimizer's correctness is guaranteed by the structural theorems (Theorem 1, Theorem 2), while the prediction model's failure is an empirical finding about the limits of feature-based generalization.

### 5.5.1 Rule-Driven CeilingAwareOptimizer

**Algorithm.** Before each optimization phase, the CeilingAwareOptimizer computes the size of the relevant action space via two O(m) scans:

- `COUNT_PHASE1_ACTIONS`: single pass counting adjacent self-inverse and mergeable-rotation pairs.
- `COUNT_PHASE2_ACTIONS`: windowed scan (default window = 10) counting non-adjacent inverse pairs whose intermediate gates all commute with both endpoints.

If the action-space size is zero, the corresponding phase is skipped. After Phase-2, a final Phase-1 cleanup pass is run if Phase-2 was not skipped.

**Theoretical guarantee.** The rule-driven skip is sound: if `|S(C)| = 0`, then no gate cancellation is possible regardless of optimizer implementation (Theorem 2). The phase skip does not sacrifice achievable reduction.

**E21 results (1,140 rows, 15 families, full mode).** The CeilingAwareOptimizer matches the naive pipeline's gate-count reduction exactly across all 15 training families (mean 9.63% for both), with wall-clock speedup:

| Family | Speedup |
|--------|---------|
| QuantumWalk | 228× |
| HaarRandom | 16× |
| QFT | 14× |
| SurfaceCode | 10× |
| HardwareEfficient | 8× |
| VQE | 9× |
| QAOA | 8× |
| IQP | 9× |
| GHZ | 5× |
| Oracle | 3× |
| Grover | 6× |
| Adder | 11× |
| UCCSD | 8× |
| RandomClifford | 2× |
| CNOT | 2× |

Overall mean: 35× (wall-clock time ratio). Families that skip both phases show the largest speedups; reducible families that skip only one futile phase show smaller speedups (1.6×–3.4×). In aggregate, the CeilingAwareOptimizer executes only 28% of the optimization passes that the naive pipeline runs, while producing bit-identical output circuits.

**Scope.** The correctness guarantee applies only to the 15 training families. For unseen families, the structural proxy's prediction that |S(C)| = 0 is not known a priori — the proxy must be computed at runtime, which the CeilingAwareOptimizer does automatically. The soundness guarantee holds for any circuit for which the proxy is computed; the limitation is that we cannot pre-specify which families are ceiling without computing the proxy.

### 5.5.2 Empirical Prediction Model: Negative Result

A machine learning model was constructed to predict gate reduction from pre-optimization structural features. The goal was to enable ceiling-aware optimization without computing the O(m) proxy at runtime.

**Model.** Two-stage Random Forest (classifier + regressor) with leave-one-family-out (LOFO) cross-validation. Features: depth-to-width ratio, inverse-pair density (from ceiling proxy), CNOT fraction, gate density, log gate count, binary ceiling-proxy flag, and interaction term. Training data: 570 naive-strategy trials across 15 families (E21).

**Features.** All features are derivable from the circuit's gate sequence prior to optimization, ensuring no target leakage:

- *depth-to-width ratio*: circuit depth / number of qubits
- *inverse-pair density*: Phase-1 proxy count / total gates — captures adjacent cancellation potential
- *CNOT fraction*: CNOT gates / total gates — measures two-qubit entanglement density
- *gate density*: total gates / number of qubits — circuit scale proxy
- *log gate count*: log(1 + total gates)
- *binary ceiling-proxy flag*: indicator for proxy = 0
- *depth × density interaction*: product of depth ratio and inverse-pair density

**LOFO cross-validation results.** Each of the 15 families is held out exactly once. The model is trained on the remaining 14 families. Results (aggregated across all folds):

| Metric | LOFO CV | Always-0 Baseline |
|--------|---------|-------------------|
| MAE | 0.0980 | 0.0963 |
| Concatenated Pearson r | −0.0147 | — |
| Spearman r | −0.0029 | — |
| R² | −0.135 | −0.133 |
| Classification accuracy | 80.2% | 73.3% |
| Classification F1 (reducible) | 0.07 | — |

The model is **no better than predicting zero for every circuit**. The 0.002 MAE difference from the trivial baseline is below the measurement noise floor. Pearson and Spearman correlations are effectively zero, confirming no linear or monotonic relationship between predicted and actual reduction. The classifier achieves 80% accuracy but F1 = 0.07, indicating 0 precision on the reducible class — it achieves accuracy by predicting "ceiling" for nearly everything.

**Why it fails.** Four factors conspire to defeat cross-family generalization:

1. **Severe class imbalance.** Ten of 15 families (67%) have exactly 0% reduction. The remaining 5 families have reduction magnitudes spanning four orders of magnitude (0.1% to 100%), with no two families sharing a common magnitude.

2. **Each reducible family is structurally unique.** CNOT chains (100% reduction) are trivially compressible via adjacent H-H and CNOT-CNOT cancellation. Random Clifford circuits (~19%) contain commutation-enabled cancellation opportunities that are invisible to adjacent-pair scanning. Oracle circuits (~16%) combine commutation with structure-specific template matching. Grover (~2%) has sparse, scattered opportunities. No single feature set captures all four mechanisms.

3. **Within-family variance is zero or near-zero.** Ten families have exactly 0% reduction with zero variance. CNOT has exactly 100% with zero variance. RandomClifford is the only reducible family with nonzero variance (std = 0.08). This means LOFO CV cannot compute per-fold Pearson for 13 of 15 families.

4. **Feature space resolution is insufficient.** The available features aggregate over the entire circuit, losing the per-gate-type and per-qubit-connectivity information that distinguishes families. A CNOT chain and a GHZ circuit may have similar depth-to-width ratios but wildly different optimization outcomes.

**Comparison with the original held-out failure.** The original HGC report (appendix.md:364) described a 5-family held-out evaluation with MAE = 0.2775 and Pearson = NaN. The LOFO CV results are worse in an important sense: the original failure could be attributed to a poorly chosen held-out set (all 5 families were at ceiling). The LOFO CV failure is more fundamental — every family fails when held out, including reducible families. The MAE is lower (0.098 vs 0.278) only because the always-0 baseline is lower on the full dataset; the model's predictive power relative to baseline is essentially zero in both cases.

### 5.5.3 Publication Recommendation

Given the confirmed LOFO CV failure, we recommend:

1. **Downgrade the predictive model from "exploratory" to "confirmed negative result."** The empirical correlation model does not generalize to unseen families. This is a null finding with a clear interpretation: pre-optimization structural features at the CSV-available resolution are insufficient for cross-family generalization.

2. **Preserve the CeilingAwareOptimizer as a valid engineering contribution.** The rule-driven pass skipper is distinct from the ML model. Its correctness is guaranteed by structural theorems, and its E21 speedup results are valid for the tested families. The HGC caveat applies only to the *prediction* that a circuit is at ceiling before computing the proxy — but the CeilingAwareOptimizer computes the proxy at runtime, avoiding this generalization problem entirely.

3. **Frame the negative result as a constructive contribution.** The LOFO CV failure establishes a lower bound on feature complexity: per-circuit-family regression requires per-gate-type resolution that is not available from structural density features alone. This finding guides future work (Section 15.5) toward richer feature representations, including Pauli-spectrum descriptors, entanglement entropy proxies, and learned circuit embeddings.
