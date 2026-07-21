# Ceiling Model Repair Plan

**Date**: 2026-07-17
**Status**: HGC confirmed worse than expected; three strategies evaluated

---

## 1. Problem Recap

LOFO CV with Random Forest + 7 features on 570 E21 rows shows:
- MAE = 0.098 (baseline always-0 = 0.096) — **no improvement**
- Concatenated Pearson r = -0.015 — **random**
- Classification F1 = 0.07 — **cannot identify reducible families**

The model is no better than always predicting zero. This is a negative result.

---

## 2. Strategy A: Feature Engineering + Random Forest [IMPLEMENTED]

### What
Built 7 structural features from the E21 CSV:
- `depth_to_width_ratio`, `inverse_pair_density`, `cnot_fraction`, `gate_density`, `log_size`, `is_ceiling_proxy_binary`, `depth_times_density`
- Two-stage: RandomForestClassifier → RandomForestRegressor
- LOFO CV with bootstrap 95% CI

### Result
**FAILED.** No improvement over always-predict-0 baseline.

### Why
The available features (derivable from the E21 CSV) are insufficient to distinguish circuit families' optimization behavior. The 4 reducible families (CNOT, RandomClifford, Oracle, Grover) each have unique reduction magnitudes with no overlapping structural signatures in the current feature space.

### Verdict
**Feature engineering from the E21 CSV alone is insufficient.** The CSV lacks per-gate-type histograms, commutation graph structure, and entanglement measures that might discriminate families.

---

## 3. Strategy B: Richer Features + Gradient Boosting [PROPOSED]

### What
- Compute per-gate-type histograms from the original QASM/QuantumCircuit objects (NOT from the E21 CSV)
- Add commutation graph descriptors: eigenvalues, clustering coefficient, motif counts
- Add circuit entropy / entanglement measures
- Model: XGBoost or LightGBM with early stopping
- LOFO CV as in Strategy A

### Why it might work
The E21 CSV loses information. The original QuantumCircuit objects contain:
- Gate names and parameters (H, T, S, RX, RY, RZ, CNOT, etc.)
- Qubit connectivity patterns
- Commutation relationships (computable from gate predicates)

These could provide discriminative signals that the 7 CSV-derived features miss.

### Why it might fail
- Still only 4 reducible families
- Each family is structurally unique — no common "reducibility pattern"
- Even rich gate-set features may not generalize across families

### Implementation sketch
```python
# Requires access to QuantumCircuit, not just CSV
for circuit in circuits:
    gate_types = Counter(inst.operation.name for inst in circuit.data)
    n_gates = len(circuit.data)
    features = {
        "h_fraction": gate_types.get("h", 0) / n_gates,
        "cx_fraction": gate_types.get("cx", 0) / n_gates,
        "t_fraction": gate_types.get("t", 0) / n_gates,
        "rz_fraction": sum(v for k, v in gate_types.items()
                          if k.startswith("rz")) / n_gates,
        # ... 20+ gate-type features
    }
```

### Verdict
**Promising but unproven.** Requires re-running circuit generation and feature computation from scratch. Not feasible from the E21 CSV alone.

---

## 4. Strategy C: Switch to Classification [IMPLEMENTED, PARTIAL SUCCESS]

### What
Treat ceiling prediction as binary classification: `is_reducible` (> 0.1% reduction) vs `is_ceiling`.

### Result
- Overall accuracy: 80% (16/20 folds ≥ 80%)
- F1 score: 0.07
- Confusion matrix dominated by "predict ceiling for everything"

### Analysis
80% accuracy sounds OK but is misleading: since 73% of families are ceiling, a "predict always ceiling" baseline achieves 73%. The classifier adds only 7% relative improvement but has 0 precision on the reducible class.

### Improvement path
- SMOTE oversampling of reducible class
- Cost-sensitive learning (class_weight)
- Threshold tuning (currently 0.5)
- Per-family probability calibration

### Expected
With SMOTE + threshold tuning, classification F1 could reach 0.3–0.5 on reducible families. Regression remains difficult due to limited magnitude variation.

### Verdict
**The most realistic short-term path.** Binary classification is an easier problem than regression because it only needs to distinguish "zero" from "nonzero" — a structural signal that may exist.

---

## 5. Recommended Strategy: ABC Hybrid

Sequence of actions, ordered by feasibility:

### Phase 1 (Immediate): Strategy C+ — Upgraded Classification
- SMOTE oversampling
- Class weight tuning
- Threshold optimization via LOFO CV
- Report precision/recall curves
- **Target**: F1 ≥ 0.3 on reducible class

### Phase 2 (Near-term): Strategy B — Richer Features
- Recompute features from original circuit objects
- Gate-type histograms (25+ gate types)
- Commutation graph spectral features
- Circuit shape descriptors (entanglement proxies)
- **Target**: MAE improvement over baseline > 0.02

### Phase 3 (Medium-term): Strategy A+B+C — Full Pipeline
- Gradient Boosting on rich features
- Two-stage (classification → regression)
- LOFO CV with bootstrap CI
- Calibrated probability outputs
- **Target**: PE ≥ 0.4, R² ≥ 0.3, MAE ≤ 0.05

---

## 6. Publication Strategy

### Current status (post-diagnosis)
The predictive model is a **confirmed negative result**: structural features available from the E21 CSV cannot predict gate reduction for unseen circuit families.

### Recommendation
1. **Downgrade from "exploratory" to "negative result"** in the manuscript
2. Report the LOFO CV results transparently as a null finding
3. Frame as:"The empirical correlation model does not generalize to unseen families (LOFO CV: MAE=0.098, Pearson r=-0.015, R²=-0.135). This negative result is itself informative: it establishes a lower bound on the feature complexity required for predictive ceiling analysis — per-circuit gate-type resolution is necessary."
4. Position the regression task as deferred future work requiring richer features
