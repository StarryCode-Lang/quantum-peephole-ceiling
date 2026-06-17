#!/usr/bin/env python3
"""
Phase 5, Stage 7: Optimize-or-Skip Compiler Decision Framework
===============================================================

Given that most quantum circuits cannot be meaningfully optimized by peephole
methods, this script builds a predictor that decides BEFORE running the
optimizer whether optimization is worthwhile.

Key findings driving this work:
  - CNOT_chain: 100% reduction  (always optimize)
  - Oracle:     ~20-28%         (worth optimizing)
  - RandomClifford: ~18-25%     (worth optimizing)
  - Grover:     ~7-13%          (marginal)
  - Universal random: ~3%       (probably not worth it)
  - QFT, QAOA, VQE, GHZ: 0%   (definitely skip)

Data sources:
  E10 - Phase1 vs Phase2 random circuits
  E11 - Real circuit benchmark
  E13 - Structural ceiling analysis
  E14 - Extended benchmark
  E16 - Window scaling

Outputs:
  <project_root>/analysis/phase5_compiler_framework.json
"""

import json
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import cross_val_predict, KFold
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, mean_absolute_error, r2_score,
    confusion_matrix, classification_report
)

warnings.filterwarnings("ignore")

# ============================================================================
# Configuration
# ============================================================================
BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REDUCTION_THRESHOLD = 0.05  # 5% reduction is "worth optimizing"

DATA_FILES = {
    "e10": DATA_DIR / "v3_extended" / "e10" / "e10_phase1_vs_phase2_20260611_191634.csv",
    "e11": DATA_DIR / "v4" / "e11" / "e11_real_circuit_benchmark_e11_full_20260611_114615.csv",
    "e13": DATA_DIR / "v4" / "e13" / "e13_structural_ceiling_e13_full_20260609_043322.csv",
    "e14": DATA_DIR / "v5" / "e14" / "e14_extended_benchmark_e14_full_20260611_114726.csv",
    "e16": DATA_DIR / "v5" / "e16" / "e16_window_scaling_e16_full_20260610_142547.csv",
}

# ============================================================================
# 1. DATA LOADING
# ============================================================================
def load_all_data():
    """Load all CSV files and return raw DataFrames."""
    dfs = {}
    for name, path in DATA_FILES.items():
        if path.exists():
            df = pd.read_csv(path)
            dfs[name] = df
            print(f"  Loaded {name}: {len(df)} rows, {len(df.columns)} cols")
        else:
            print(f"  WARNING: {name} not found at {path}")
    return dfs


# ============================================================================
# 2. FEATURE EXTRACTION
# ============================================================================
def extract_e13_structural_features(df_e13):
    """
    Extract structural features from E13 that can be computed WITHOUT
    running the optimizer. These require scanning the gate list only.
    """
    feat_cols = [
        "circuit_id", "circuit_family", "circuit_type",
        "n_qubits", "depth", "gate_count_total",
        "gate_count_1q", "gate_count_2q", "gate_count_multiq",
        "cancellable_pair_count",
        "mergeable_rotation_count",
        "adjacent_commuting_pairs",
        "commutation_enabled_inverse_pairs",
        "commuting_block_count",
        "mean_block_size",
        "max_block_size",
        "structural_lower_bound",
        "structural_upper_bound_reduction",
    ]
    available = [c for c in feat_cols if c in df_e13.columns]
    features = df_e13[available].copy()

    # Derived features
    gc = features["gate_count_total"].replace(0, np.nan)
    features["two_qubit_ratio"] = features["gate_count_2q"] / gc
    features["multi_qubit_ratio"] = features["gate_count_multiq"] / gc
    features["one_qubit_ratio"] = features["gate_count_1q"] / gc
    features["cancellable_ratio"] = features["cancellable_pair_count"] / gc
    features["mergeable_ratio"] = features["mergeable_rotation_count"] / gc
    features["commutation_ratio"] = features["commutation_enabled_inverse_pairs"] / gc
    features["depth_per_qubit"] = features["depth"] / features["n_qubits"].replace(0, np.nan)
    features["gate_density"] = features["gate_count_total"] / (
        features["n_qubits"] * features["depth"].replace(0, np.nan)
    )

    features = features.fillna(0)
    return features


def get_hybrid_reduction_from_e14(df_e14):
    """Extract hybrid_phase1_2 reduction from E14 (window_size=10 only)."""
    mask = (df_e14["optimizer"] == "hybrid_phase1_2")
    if "window_size" in df_e14.columns:
        mask = mask & (df_e14["window_size"] == 10)
    sub = df_e14.loc[mask, ["circuit_id", "circuit_family", "reduction",
                             "runtime_seconds", "baseline_gate_count",
                             "optimized_gate_count"]].copy()
    sub = sub.rename(columns={
        "reduction": "hybrid_reduction_e14",
        "runtime_seconds": "runtime_e14",
        "baseline_gate_count": "baseline_gc_e14",
        "optimized_gate_count": "optimized_gc_e14",
    })
    # Deduplicate by circuit_id (take first occurrence)
    sub = sub.drop_duplicates(subset="circuit_id", keep="first")
    return sub


def get_hybrid_reduction_from_e11(df_e11):
    """Extract hybrid_phase1_2 reduction from E11."""
    mask = df_e11["optimizer"] == "hybrid_phase1_2"
    sub = df_e11.loc[mask, ["circuit_id", "circuit_family", "reduction",
                             "runtime_seconds", "baseline_gate_count",
                             "optimized_gate_count"]].copy()
    sub = sub.rename(columns={
        "reduction": "hybrid_reduction_e11",
        "runtime_seconds": "runtime_e11",
        "baseline_gate_count": "baseline_gc_e11",
        "optimized_gate_count": "optimized_gc_e11",
    })
    sub = sub.drop_duplicates(subset="circuit_id", keep="first")
    return sub


def get_e10_random_features(df_e10):
    """
    Build feature rows for E10 random circuits.
    E10 has different column names: gate_count, original_size, optimized_size.
    """
    hybrid = df_e10[df_e10["optimizer"] == "hybrid_phase1_2"].copy()
    hybrid = hybrid.rename(columns={
        "gate_count": "gate_count_total",
        "original_size": "baseline_gc",
        "optimized_size": "optimized_gc",
    })

    # E10 doesn't have gate_count_1q / gate_count_2q / structural features
    # We can only use n_qubits, depth, gate_count_total, circuit_family
    feat_cols = ["circuit_family", "circuit_type", "n_qubits", "depth",
                 "gate_count_total", "reduction", "runtime_seconds"]
    available = [c for c in feat_cols if c in hybrid.columns]
    features = hybrid[available].copy()
    features = features.rename(columns={"reduction": "hybrid_reduction_e10",
                                         "runtime_seconds": "runtime_e10"})

    # Derived features
    gc = features["gate_count_total"].replace(0, np.nan)
    features["depth_per_qubit"] = features["depth"] / features["n_qubits"].replace(0, np.nan)
    features = features.fillna(0)

    # Deduplicate: average over trials for same (circuit_family, n_qubits, depth)
    group_cols = ["circuit_family", "circuit_type", "n_qubits", "depth"]
    available_group = [c for c in group_cols if c in features.columns]
    features = features.groupby(available_group, as_index=False).mean(numeric_only=True)
    features["gate_count_total"] = features["gate_count_total"].round().astype(int)

    return features


def get_e16_window_scaling(df_e16):
    """Extract E16 window scaling data for window-size analysis."""
    mask = df_e16["optimizer"] == "hybrid_phase1_2"
    sub = df_e16.loc[mask, ["circuit_id", "circuit_family", "reduction",
                             "window_size", "runtime_seconds"]].copy()
    sub = sub.rename(columns={
        "reduction": "hybrid_reduction_e16",
        "runtime_seconds": "runtime_e16",
    })
    return sub


def build_merged_dataset(dfs):
    """
    Build the main merged dataset for training.
    Primary source: E13 (structural features) joined with E14 (reduction).
    Supplement with E11 where E14 is missing.
    """
    # E13 structural features (one row per circuit)
    e13_features = extract_e13_structural_features(dfs["e13"])

    # E14 hybrid reduction
    e14_reduction = get_hybrid_reduction_from_e14(dfs["e14"])

    # E11 hybrid reduction (fallback)
    e11_reduction = get_hybrid_reduction_from_e11(dfs["e11"])

    # Merge E13 features with E14 reduction
    merged = e13_features.merge(e14_reduction[["circuit_id", "hybrid_reduction_e14",
                                                 "runtime_e14", "baseline_gc_e14"]],
                                 on="circuit_id", how="left")

    # Fill gaps with E11 data
    e11_map = e11_reduction.set_index("circuit_id")[["hybrid_reduction_e11", "runtime_e11"]]
    for idx, row in merged.iterrows():
        if pd.isna(row.get("hybrid_reduction_e14")):
            cid = row["circuit_id"]
            if cid in e11_map.index:
                merged.at[idx, "hybrid_reduction_e14"] = e11_map.loc[cid, "hybrid_reduction_e11"]
                merged.at[idx, "runtime_e14"] = e11_map.loc[cid, "runtime_e11"]

    # Use hybrid_reduction_e14 as the primary target
    merged["reduction"] = merged["hybrid_reduction_e14"]
    merged["runtime"] = merged["runtime_e14"]

    # Binary label: is it worth optimizing?
    merged["worth_optimizing"] = (merged["reduction"] >= REDUCTION_THRESHOLD).astype(int)

    print(f"\n  Merged dataset: {len(merged)} circuits")
    print(f"  Circuits with reduction data: {merged['reduction'].notna().sum()}")
    print(f"  Worth optimizing (>{REDUCTION_THRESHOLD*100}%): {merged['worth_optimizing'].sum()}")
    print(f"  Not worth optimizing: {(1 - merged['worth_optimizing']).sum()}")

    return merged


# ============================================================================
# 3. PREDICTORS
# ============================================================================

class RuleBasedPredictor:
    """
    Rule-based predictor using structural heuristics.
    Fast, interpretable, no training needed.
    """
    NAME = "Rule-Based"

    def predict(self, features_row):
        """Returns dict with decision, expected_gain, confidence."""
        cancellable = features_row.get("cancellable_pair_count", 0)
        commutation = features_row.get("commutation_enabled_inverse_pairs", 0)
        mergeable = features_row.get("mergeable_rotation_count", 0)
        gate_count = max(features_row.get("gate_count_total", 1), 1)
        circuit_family = features_row.get("circuit_family", "Unknown")
        two_qubit_ratio = features_row.get("two_qubit_ratio", 0)
        structural_upper = features_row.get("structural_upper_bound_reduction", 0)

        # Rule 1: Cancellable pairs -> always optimize
        if cancellable > 0:
            expected_gain = min(2.0 * cancellable / gate_count, 1.0)
            return {
                "decision": "OPTIMIZE",
                "expected_gain": round(expected_gain, 4),
                "confidence": 0.95,
                "reason": f"cancellable_pairs={cancellable}",
            }

        # Rule 2: Known high-reduction families
        high_gain_families = {"CNOT", "Oracle", "RandomClifford"}
        if circuit_family in high_gain_families:
            return {
                "decision": "OPTIMIZE",
                "expected_gain": 0.25,
                "confidence": 0.80,
                "reason": f"known_high_gain_family={circuit_family}",
            }

        # Rule 3: Commutation-enabled pairs with sufficient window
        if commutation > 0 and two_qubit_ratio < 0.5:
            expected_gain = min(commutation / gate_count * 0.5, 0.3)
            if expected_gain > REDUCTION_THRESHOLD:
                return {
                    "decision": "OPTIMIZE",
                    "expected_gain": round(expected_gain, 4),
                    "confidence": 0.65,
                    "reason": f"commutation_enabled={commutation}",
                }

        # Rule 4: Mergeable rotations
        if mergeable > 0:
            expected_gain = min(mergeable / gate_count * 0.3, 0.2)
            if expected_gain > REDUCTION_THRESHOLD:
                return {
                    "decision": "OPTIMIZE",
                    "expected_gain": round(expected_gain, 4),
                    "confidence": 0.60,
                    "reason": f"mergeable_rotations={mergeable}",
                }

        # Rule 5: Structural upper bound from E13
        if structural_upper > REDUCTION_THRESHOLD:
            return {
                "decision": "OPTIMIZE",
                "expected_gain": round(structural_upper * 0.5, 4),
                "confidence": 0.55,
                "reason": f"structural_upper_bound={structural_upper:.3f}",
            }

        # Default: skip
        return {
            "decision": "SKIP",
            "expected_gain": 0.0,
            "confidence": 0.85,
            "reason": "no_optimization_signals_detected",
        }


class ThresholdPredictor:
    """
    Threshold-based predictor using a quick proxy score.
    Computes quick_proxy = cancellable_pairs/gate_count +
                           0.3 * commutation_enabled/gate_count +
                           0.2 * mergeable_rotations/gate_count
    If quick_proxy > threshold -> OPTIMIZE, else SKIP.
    Threshold is optimized via ROC analysis.
    """
    NAME = "Threshold"

    def __init__(self, threshold=0.05):
        self.threshold = threshold

    def compute_proxy(self, features_row):
        gate_count = max(features_row.get("gate_count_total", 1), 1)
        cancellable = features_row.get("cancellable_pair_count", 0)
        commutation = features_row.get("commutation_enabled_inverse_pairs", 0)
        mergeable = features_row.get("mergeable_rotation_count", 0)
        structural_upper = features_row.get("structural_upper_bound_reduction", 0)

        proxy = (
            cancellable / gate_count
            + 0.3 * commutation / gate_count
            + 0.2 * mergeable / gate_count
            + 0.5 * structural_upper
        )
        return proxy

    def predict(self, features_row):
        proxy = self.compute_proxy(features_row)
        decision = "OPTIMIZE" if proxy > self.threshold else "SKIP"
        confidence = min(abs(proxy - self.threshold) * 5 + 0.5, 0.99)
        return {
            "decision": decision,
            "expected_gain": round(proxy, 4),
            "confidence": round(confidence, 4),
            "reason": f"proxy={proxy:.4f} vs threshold={self.threshold:.4f}",
        }

    @classmethod
    def find_optimal_threshold(cls, df):
        """Find optimal threshold via ROC analysis."""
        proxies = []
        labels = []
        for _, row in df.iterrows():
            proxy = cls().compute_proxy(row)
            proxies.append(proxy)
            labels.append(row["worth_optimizing"])

        proxies = np.array(proxies)
        labels = np.array(labels)

        if len(np.unique(labels)) < 2:
            return 0.05, {}

        fpr, tpr, thresholds = roc_curve(labels, proxies)
        # Youden's J statistic: maximize (tpr - fpr)
        j_scores = tpr - fpr
        best_idx = np.argmax(j_scores)
        optimal_threshold = thresholds[best_idx] if best_idx < len(thresholds) else 0.05

        auc = roc_auc_score(labels, proxies)
        stats = {
            "auc_roc": round(auc, 4),
            "optimal_threshold": round(float(optimal_threshold), 6),
            "best_j_score": round(float(j_scores[best_idx]), 4),
            "thresholds_scanned": len(thresholds),
        }
        return float(optimal_threshold), stats


class MLPredictor:
    """
    ML predictor using Random Forest.
    Trains on all available features to predict reduction,
    then decides based on predicted_reduction > cost_threshold.
    """
    NAME = "ML-RandomForest"

    def __init__(self, cost_threshold=REDUCTION_THRESHOLD):
        self.cost_threshold = cost_threshold
        self.regressor = RandomForestRegressor(
            n_estimators=200,
            max_depth=6,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
        self.classifier = RandomForestClassifier(
            n_estimators=200,
            max_depth=6,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
        self.feature_cols = None
        self.is_fitted = False

    def _get_feature_cols(self, df):
        exclude = {
            "circuit_id", "circuit_family", "circuit_type",
            "reduction", "worth_optimizing", "runtime",
            "hybrid_reduction_e14", "hybrid_reduction_e11",
            "hybrid_reduction_e10", "runtime_e14", "runtime_e11",
            "runtime_e10", "baseline_gc_e14", "baseline_gc_e11",
            "optimized_gc_e14", "optimized_gc_e11",
        }
        cols = [c for c in df.columns if c not in exclude and df[c].dtype in [
            np.float64, np.int64, np.float32, np.int32, float, int
        ]]
        return cols

    def fit(self, df):
        self.feature_cols = self._get_feature_cols(df)
        X = df[self.feature_cols].values
        y_reg = df["reduction"].values
        y_cls = df["worth_optimizing"].values

        # Cross-validated predictions for honest evaluation
        cv = KFold(n_splits=min(5, len(df)), shuffle=True, random_state=42)

        self.reg_pred = cross_val_predict(self.regressor, X, y_reg, cv=cv)
        self.cls_pred = cross_val_predict(self.classifier, X, y_cls, cv=cv)

        # Now fit on full data for deployment
        self.regressor.fit(X, y_reg)
        self.classifier.fit(X, y_cls)
        self.is_fitted = True

        # Feature importances
        importances = dict(zip(self.feature_cols, self.regressor.feature_importances_))
        self.feature_importances = {
            k: round(v, 4) for k, v in
            sorted(importances.items(), key=lambda x: -x[1])
        }

        return self

    def predict(self, features_row):
        if not self.is_fitted:
            return {"decision": "SKIP", "expected_gain": 0.0,
                    "confidence": 0.0, "reason": "model_not_fitted"}

        X = np.array([[features_row.get(c, 0) for c in self.feature_cols]])
        pred_reduction = float(self.regressor.predict(X)[0])
        pred_class_proba = self.classifier.predict_proba(X)[0]

        # Probability of "worth optimizing" class
        prob_optimize = float(pred_class_proba[1]) if len(pred_class_proba) > 1 else 0.0

        if pred_reduction > self.cost_threshold:
            return {
                "decision": "OPTIMIZE",
                "expected_gain": round(max(pred_reduction, 0), 4),
                "confidence": round(prob_optimize, 4),
                "reason": f"predicted_reduction={pred_reduction:.4f}",
            }
        else:
            return {
                "decision": "SKIP",
                "expected_gain": round(max(pred_reduction, 0), 4),
                "confidence": round(1 - prob_optimize, 4),
                "reason": f"predicted_reduction={pred_reduction:.4f} < threshold",
            }

    def get_cv_metrics(self, df):
        """Get cross-validated metrics."""
        y_reg = df["reduction"].values
        y_cls = df["worth_optimizing"].values

        reg_metrics = {
            "mae": round(float(mean_absolute_error(y_reg, self.reg_pred)), 4),
            "r2": round(float(r2_score(y_reg, self.reg_pred)), 4),
            "corr": round(float(np.corrcoef(y_reg, self.reg_pred)[0, 1]), 4),
        }

        cls_metrics = {
            "precision": round(float(precision_score(y_cls, self.cls_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_cls, self.cls_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_cls, self.cls_pred, zero_division=0)), 4),
        }

        return {"regression": reg_metrics, "classification": cls_metrics}


# ============================================================================
# 4. EVALUATION
# ============================================================================
def evaluate_predictor(predictor, df, name="Predictor"):
    """
    Evaluate a predictor on the dataset.
    Returns precision, recall, F1, and estimated compiler speedup.
    """
    decisions = []
    expected_gains = []
    actual_reductions = []
    actual_labels = []

    for _, row in df.iterrows():
        pred = predictor.predict(row)
        decisions.append(pred["decision"])
        expected_gains.append(pred["expected_gain"])
        actual_reductions.append(row["reduction"])
        actual_labels.append(row["worth_optimizing"])

    decisions = np.array(decisions)
    actual_labels = np.array(actual_labels)
    actual_reductions = np.array(actual_reductions)
    expected_gains = np.array(expected_gains)

    # Predicted labels
    pred_labels = (decisions == "OPTIMIZE").astype(int)

    # Classification metrics
    prec = precision_score(actual_labels, pred_labels, zero_division=0)
    rec = recall_score(actual_labels, pred_labels, zero_division=0)
    f1 = f1_score(actual_labels, pred_labels, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(actual_labels, pred_labels, labels=[0, 1]).ravel()

    # Estimated compiler speedup
    # Assume optimizer cost = 1 unit per gate scanned
    total_gates = df["gate_count_total"].sum()
    always_opt_cost = total_gates  # always run optimizer on everything
    predictor_cost = 0
    skip_savings = 0
    wasted_cost = 0

    for i, (_, row) in enumerate(df.iterrows()):
        gc = row["gate_count_total"]
        if decisions[i] == "OPTIMIZE":
            predictor_cost += gc
            if actual_reductions[i] <= 0:
                wasted_cost += gc
        else:
            skip_savings += gc

    never_opt_cost = 0  # never run = zero cost but zero benefit

    # Net benefit: gates saved by optimization minus optimizer cost
    total_gates_saved = sum(
        actual_reductions[i] * row["gate_count_total"]
        for i, (_, row) in enumerate(df.iterrows())
        if decisions[i] == "OPTIMIZE"
    )
    always_opt_gates_saved = sum(
        actual_reductions[i] * row["gate_count_total"]
        for i, (_, row) in enumerate(df.iterrows())
    )

    # Speedup = fraction of time saved by skipping
    if always_opt_cost > 0:
        speedup_pct = round(skip_savings / always_opt_cost * 100, 1)
    else:
        speedup_pct = 0

    # Efficiency: of the time we DO spend optimizing, how much reduction do we get?
    if predictor_cost > 0:
        efficiency = round(total_gates_saved / predictor_cost * 100, 2)
    else:
        efficiency = 0

    cm = {
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
    }

    results = {
        "predictor": name,
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1_score": round(float(f1), 4),
        "confusion_matrix": cm,
        "compiler_speedup_pct": speedup_pct,
        "optimization_efficiency_pct": efficiency,
        "total_gates_saved": round(float(total_gates_saved), 1),
        "always_optimize_gates_saved": round(float(always_opt_gates_saved), 1),
        "wasted_optimizer_cost": int(wasted_cost),
        "skipped_circuits": int((decisions == "SKIP").sum()),
        "optimized_circuits": int((decisions == "OPTIMIZE").sum()),
    }

    return results


# ============================================================================
# 5. COST-BENEFIT ANALYSIS
# ============================================================================
def cost_benefit_analysis(df, predictor, name="Predictor"):
    """
    Detailed cost-benefit analysis.
    Cost model: optimizer cost = 1 unit per gate scanned.
    Benefit model: gates saved = reduction * gate_count.
    """
    rows = []
    for _, row in df.iterrows():
        pred = predictor.predict(row)
        gc = row["gate_count_total"]
        red = row["reduction"]

        if pred["decision"] == "OPTIMIZE":
            cost = gc  # optimizer scans all gates
            benefit = red * gc  # gates saved
            net = benefit - cost
            strategy_outcome = "OPTIMIZE"
            if red > 0:
                outcome_detail = "productive"
            else:
                outcome_detail = "wasted"
        else:
            cost = 0
            benefit = 0
            net = 0
            strategy_outcome = "SKIP"
            if red > REDUCTION_THRESHOLD:
                outcome_detail = "missed_opportunity"
            else:
                outcome_detail = "correct_skip"

        rows.append({
            "circuit_id": row.get("circuit_id", "unknown"),
            "circuit_family": row.get("circuit_family", "unknown"),
            "gate_count": gc,
            "actual_reduction": red,
            "decision": strategy_outcome,
            "detail": outcome_detail,
            "optimizer_cost": cost,
            "gates_saved": benefit,
            "net_benefit": net,
        })

    result_df = pd.DataFrame(rows)

    # Summary statistics
    total_cost_predictor = result_df["optimizer_cost"].sum()
    total_benefit_predictor = result_df["gates_saved"].sum()
    total_net_predictor = total_benefit_predictor - total_cost_predictor

    # Always-optimize strategy
    total_cost_always = df["gate_count_total"].sum()
    total_benefit_always = (df["reduction"] * df["gate_count_total"]).sum()
    total_net_always = total_benefit_always - total_cost_always

    # Never-optimize strategy
    total_cost_never = 0
    total_benefit_never = 0
    total_net_never = 0

    # Correct decisions
    correct_skips = (result_df["detail"] == "correct_skip").sum()
    productive_opts = (result_df["detail"] == "productive").sum()
    correct_total = correct_skips + productive_opts
    missed_opps = (result_df["detail"] == "missed_opportunity").sum()
    wasted_opts = (result_df["detail"] == "wasted").sum()

    summary = {
        "strategy": name,
        "total_optimizer_cost": int(total_cost_predictor),
        "total_gates_saved": round(float(total_benefit_predictor), 1),
        "net_benefit": round(float(total_net_predictor), 1),
        "comparison": {
            "always_optimize": {
                "total_cost": int(total_cost_always),
                "total_gates_saved": round(float(total_benefit_always), 1),
                "net_benefit": round(float(total_net_always), 1),
            },
            "never_optimize": {
                "total_cost": int(total_cost_never),
                "total_gates_saved": round(float(total_benefit_never), 1),
                "net_benefit": round(float(total_net_never), 1),
            },
        },
        "decision_quality": {
            "correct_skips": int(correct_skips),
            "productive_optimizations": int(productive_opts),
            "correct_decisions_total": int(correct_total),
            "missed_opportunities": int(missed_opps),
            "wasted_optimizations": int(wasted_opts),
            "accuracy": round(correct_total / len(result_df), 4) if len(result_df) > 0 else 0,
        },
        "per_circuit_details": rows,
    }

    return summary


# ============================================================================
# 6. OPTIMIZE-OR-SKIP API CLASS
# ============================================================================
class OptimizeOrSkip:
    """
    Practical Optimize-or-Skip compiler decision API.

    Usage:
        framework = OptimizeOrSkip()
        framework.fit(training_data)
        result = framework.predict(circuit_features)
        # result = {decision: 'OPTIMIZE'|'SKIP', expected_gain: float, confidence: float}
    """

    def __init__(self, strategy="ensemble"):
        """
        strategy: 'rule', 'threshold', 'ml', or 'ensemble'
        """
        self.strategy = strategy
        self.rule_predictor = RuleBasedPredictor()
        self.threshold_predictor = ThresholdPredictor()
        self.ml_predictor = MLPredictor()
        self.is_fitted = False

    def fit(self, df):
        """Train all sub-predictors."""
        # Find optimal threshold
        opt_threshold, threshold_stats = ThresholdPredictor.find_optimal_threshold(df)
        self.threshold_predictor = ThresholdPredictor(threshold=opt_threshold)
        self.threshold_stats = threshold_stats

        # Train ML predictor
        self.ml_predictor.fit(df)

        self.is_fitted = True
        return self

    def predict(self, circuit_features):
        """
        Returns {decision: 'OPTIMIZE'|'SKIP', expected_gain: float, confidence: float}

        Uses an ensemble: majority vote of 3 sub-predictors, weighted by confidence.
        """
        if not self.is_fitted:
            return self.rule_predictor.predict(circuit_features)

        r = self.rule_predictor.predict(circuit_features)
        t = self.threshold_predictor.predict(circuit_features)
        m = self.ml_predictor.predict(circuit_features)

        predictions = [r, t, m]
        names = ["rule", "threshold", "ml"]

        if self.strategy == "rule":
            return r
        elif self.strategy == "threshold":
            return t
        elif self.strategy == "ml":
            return m
        else:
            # Ensemble: weighted vote
            optimize_score = 0
            skip_score = 0
            for p in predictions:
                if p["decision"] == "OPTIMIZE":
                    optimize_score += p["confidence"]
                else:
                    skip_score += p["confidence"]

            avg_gain = np.mean([p["expected_gain"] for p in predictions])
            total_conf = optimize_score + skip_score

            if optimize_score > skip_score:
                decision = "OPTIMIZE"
                confidence = optimize_score / total_conf if total_conf > 0 else 0.5
            else:
                decision = "SKIP"
                confidence = skip_score / total_conf if total_conf > 0 else 0.5

            return {
                "decision": decision,
                "expected_gain": round(float(avg_gain), 4),
                "confidence": round(float(confidence), 4),
                "sub_predictions": {
                    names[i]: {
                        "decision": predictions[i]["decision"],
                        "expected_gain": predictions[i]["expected_gain"],
                        "confidence": predictions[i]["confidence"],
                    }
                    for i in range(3)
                },
                "reason": f"ensemble: optimize_score={optimize_score:.2f} vs skip_score={skip_score:.2f}",
            }


# ============================================================================
# 7. MAIN EXECUTION
# ============================================================================
def main():
    print("=" * 72)
    print("Phase 5 Stage 7: Optimize-or-Skip Compiler Decision Framework")
    print("=" * 72)

    # ----- Load Data -----
    print("\n[1] Loading data files...")
    dfs = load_all_data()

    # ----- Build Merged Dataset -----
    print("\n[2] Building merged dataset...")
    merged = build_merged_dataset(dfs)

    # Drop rows without reduction data
    train_df = merged.dropna(subset=["reduction"]).copy()
    train_df = train_df.reset_index(drop=True)
    print(f"\n  Training set: {len(train_df)} circuits with reduction data")

    # ----- Display data summary -----
    print("\n  Per-family reduction summary:")
    for fam in sorted(train_df["circuit_family"].unique()):
        subset = train_df[train_df["circuit_family"] == fam]
        r = subset["reduction"]
        print(f"    {fam:20s}: n={len(subset):3d}, "
              f"reduction={r.mean():.3f} +/- {r.std():.3f}, "
              f"range=[{r.min():.3f}, {r.max():.3f}]")

    # Also add E10 random circuit data to the analysis
    print("\n[2b] Loading E10 random circuit data...")
    e10_df = get_e10_random_features(dfs["e10"])
    print(f"  E10 random circuits: {len(e10_df)} groups")

    # ----- Feature Extraction Summary -----
    print("\n[3] Feature extraction summary...")
    feature_cols = [c for c in train_df.columns if c not in {
        "circuit_id", "circuit_family", "circuit_type",
        "reduction", "worth_optimizing", "runtime",
        "hybrid_reduction_e14", "hybrid_reduction_e11",
        "runtime_e14", "runtime_e11", "baseline_gc_e14",
    }]
    print(f"  Features ({len(feature_cols)}):")
    for c in feature_cols:
        print(f"    - {c}")

    # ======================================================================
    # Train and Evaluate Predictors
    # ======================================================================
    print("\n" + "=" * 72)
    print("[4] Training and evaluating predictors...")
    print("=" * 72)

    results = {}

    # --- Rule-Based Predictor ---
    print("\n--- Rule-Based Predictor ---")
    rule_pred = RuleBasedPredictor()
    rule_eval = evaluate_predictor(rule_pred, train_df, "Rule-Based")
    rule_cb = cost_benefit_analysis(train_df, rule_pred, "Rule-Based")
    results["rule_based"] = {
        "evaluation": rule_eval,
        "cost_benefit": {k: v for k, v in rule_cb.items() if k != "per_circuit_details"},
    }
    print(f"  Precision: {rule_eval['precision']:.4f}")
    print(f"  Recall:    {rule_eval['recall']:.4f}")
    print(f"  F1:        {rule_eval['f1_score']:.4f}")
    print(f"  Speedup:   {rule_eval['compiler_speedup_pct']:.1f}%")
    print(f"  Efficiency:{rule_eval['optimization_efficiency_pct']:.2f}%")

    # --- Threshold Predictor ---
    print("\n--- Threshold Predictor ---")
    opt_threshold, threshold_stats = ThresholdPredictor.find_optimal_threshold(train_df)
    print(f"  Optimal threshold: {opt_threshold:.6f}")
    print(f"  AUC-ROC: {threshold_stats.get('auc_roc', 'N/A')}")
    thresh_pred = ThresholdPredictor(threshold=opt_threshold)
    thresh_eval = evaluate_predictor(thresh_pred, train_df, "Threshold")
    thresh_cb = cost_benefit_analysis(train_df, thresh_pred, "Threshold")
    results["threshold"] = {
        "evaluation": thresh_eval,
        "roc_analysis": threshold_stats,
        "cost_benefit": {k: v for k, v in thresh_cb.items() if k != "per_circuit_details"},
    }
    print(f"  Precision: {thresh_eval['precision']:.4f}")
    print(f"  Recall:    {thresh_eval['recall']:.4f}")
    print(f"  F1:        {thresh_eval['f1_score']:.4f}")
    print(f"  Speedup:   {thresh_eval['compiler_speedup_pct']:.1f}%")

    # --- ML Predictor ---
    print("\n--- ML Predictor (Random Forest) ---")
    ml_pred = MLPredictor(cost_threshold=REDUCTION_THRESHOLD)
    ml_pred.fit(train_df)
    ml_eval = evaluate_predictor(ml_pred, train_df, "ML-RandomForest")
    ml_cb = cost_benefit_analysis(train_df, ml_pred, "ML-RandomForest")
    ml_cv_metrics = ml_pred.get_cv_metrics(train_df)
    results["ml_random_forest"] = {
        "evaluation": ml_eval,
        "cross_validated_metrics": ml_cv_metrics,
        "feature_importances": ml_pred.feature_importances,
        "cost_benefit": {k: v for k, v in ml_cb.items() if k != "per_circuit_details"},
    }
    print(f"  Precision: {ml_eval['precision']:.4f}")
    print(f"  Recall:    {ml_eval['recall']:.4f}")
    print(f"  F1:        {ml_eval['f1_score']:.4f}")
    print(f"  Speedup:   {ml_eval['compiler_speedup_pct']:.1f}%")
    print(f"  CV MAE:    {ml_cv_metrics['regression']['mae']:.4f}")
    print(f"  CV R^2:    {ml_cv_metrics['regression']['r2']:.4f}")
    print(f"  CV Corr:   {ml_cv_metrics['regression']['corr']:.4f}")
    print(f"\n  Top feature importances:")
    for feat, imp in list(ml_pred.feature_importances.items())[:8]:
        print(f"    {feat:40s}: {imp:.4f}")

    # --- Ensemble Predictor ---
    print("\n--- Ensemble Predictor ---")
    ensemble = OptimizeOrSkip(strategy="ensemble")
    ensemble.fit(train_df)
    ens_eval = evaluate_predictor(ensemble, train_df, "Ensemble")
    ens_cb = cost_benefit_analysis(train_df, ensemble, "Ensemble")
    results["ensemble"] = {
        "evaluation": ens_eval,
        "cost_benefit": {k: v for k, v in ens_cb.items() if k != "per_circuit_details"},
    }
    print(f"  Precision: {ens_eval['precision']:.4f}")
    print(f"  Recall:    {ens_eval['recall']:.4f}")
    print(f"  F1:        {ens_eval['f1_score']:.4f}")
    print(f"  Speedup:   {ens_eval['compiler_speedup_pct']:.1f}%")

    # ======================================================================
    # E16 Window Scaling Analysis
    # ======================================================================
    print("\n" + "=" * 72)
    print("[5] E16 Window Scaling Analysis...")
    print("=" * 72)

    e16_data = get_e16_window_scaling(dfs["e16"])
    window_analysis = {}
    if len(e16_data) > 0:
        for ws in sorted(e16_data["window_size"].unique()):
            subset = e16_data[e16_data["window_size"] == ws]
            avg_red = subset["hybrid_reduction_e16"].mean()
            avg_rt = subset["runtime_e16"].mean()
            n_nonzero = (subset["hybrid_reduction_e16"] > 0).sum()
            window_analysis[f"window_{ws}"] = {
                "n_circuits": len(subset),
                "avg_reduction": round(float(avg_red), 4),
                "avg_runtime_s": round(float(avg_rt), 4),
                "circuits_with_reduction": int(n_nonzero),
            }
            print(f"  Window {ws:3d}: avg_reduction={avg_red:.4f}, "
                  f"n_with_reduction={n_nonzero}/{len(subset)}")
    results["window_scaling_analysis"] = window_analysis

    # ======================================================================
    # E10 Random Circuit Analysis
    # ======================================================================
    print("\n" + "=" * 72)
    print("[6] E10 Random Circuit Baseline...")
    print("=" * 72)

    e10_analysis = {}
    if len(e10_df) > 0:
        for fam in sorted(e10_df["circuit_family"].unique()):
            subset = e10_df[e10_df["circuit_family"] == fam]
            if "hybrid_reduction_e10" in subset.columns:
                avg_red = subset["hybrid_reduction_e10"].mean()
                e10_analysis[fam] = {
                    "n_circuits": len(subset),
                    "avg_reduction": round(float(avg_red), 4),
                }
                print(f"  {fam}: avg_reduction={avg_red:.4f}, n={len(subset)}")
    results["e10_random_baseline"] = e10_analysis

    # ======================================================================
    # Detailed Per-Circuit Predictions
    # ======================================================================
    print("\n" + "=" * 72)
    print("[7] Per-circuit predictions (Ensemble)...")
    print("=" * 72)

    per_circuit = []
    for _, row in train_df.iterrows():
        pred = ensemble.predict(row)
        per_circuit.append({
            "circuit_id": row.get("circuit_id", ""),
            "circuit_family": row.get("circuit_family", ""),
            "gate_count": int(row["gate_count_total"]),
            "actual_reduction": round(float(row["reduction"]), 4),
            "worth_optimizing": bool(row["worth_optimizing"]),
            "predicted_decision": pred["decision"],
            "predicted_gain": pred["expected_gain"],
            "confidence": pred["confidence"],
            "correct": (
                (pred["decision"] == "OPTIMIZE" and row["worth_optimizing"]) or
                (pred["decision"] == "SKIP" and not row["worth_optimizing"])
            ),
        })

    correct_count = sum(1 for p in per_circuit if p["correct"])
    print(f"  Correct decisions: {correct_count}/{len(per_circuit)} "
          f"({100*correct_count/len(per_circuit):.1f}%)")

    for p in per_circuit:
        marker = "OK" if p["correct"] else "XX"
        print(f"    [{marker}] {p['circuit_id']:20s} family={p['circuit_family']:20s} "
              f"red={p['actual_reduction']:.3f} -> {p['predicted_decision']:8s} "
              f"(gain={p['predicted_gain']:.3f}, conf={p['confidence']:.2f})")

    results["per_circuit_predictions"] = per_circuit

    # ======================================================================
    # Comparison Summary
    # ======================================================================
    print("\n" + "=" * 72)
    print("[8] Predictor Comparison Summary")
    print("=" * 72)

    comparison = {}
    print(f"\n  {'Predictor':<15s} {'Precision':>10s} {'Recall':>8s} {'F1':>8s} "
          f"{'Speedup%':>10s} {'Accuracy':>10s}")
    print(f"  {'-'*65}")

    for key in ["rule_based", "threshold", "ml_random_forest", "ensemble"]:
        ev = results[key]["evaluation"]
        cb = results[key]["cost_benefit"]
        acc = cb["decision_quality"]["accuracy"]
        comparison[key] = {
            "precision": ev["precision"],
            "recall": ev["recall"],
            "f1_score": ev["f1_score"],
            "compiler_speedup_pct": ev["compiler_speedup_pct"],
            "decision_accuracy": acc,
        }
        print(f"  {key:<15s} {ev['precision']:10.4f} {ev['recall']:8.4f} "
              f"{ev['f1_score']:8.4f} {ev['compiler_speedup_pct']:10.1f} "
              f"{acc:10.4f}")

    results["predictor_comparison"] = comparison

    # ======================================================================
    # Final recommendation
    # ======================================================================
    # Find best predictor by F1
    best_key = max(comparison, key=lambda k: comparison[k]["f1_score"])
    best = comparison[best_key]

    recommendation = {
        "best_predictor": best_key,
        "best_f1": best["f1_score"],
        "best_precision": best["precision"],
        "best_recall": best["recall"],
        "best_speedup_pct": best["compiler_speedup_pct"],
        "recommendation": (
            f"Use the '{best_key}' predictor. "
            f"It achieves F1={best['f1_score']:.3f} with "
            f"{best['compiler_speedup_pct']:.1f}% compiler speedup "
            f"(by skipping circuits unlikely to benefit from optimization). "
            f"Decision accuracy: {best['decision_accuracy']*100:.1f}%."
        ),
    }
    results["recommendation"] = recommendation
    print(f"\n  RECOMMENDATION: {recommendation['recommendation']}")

    # ======================================================================
    # Save Results
    # ======================================================================
    output_path = OUTPUT_DIR / "phase5_compiler_framework.json"

    # Remove per_circuit_details from cost_benefit for JSON output
    # (already excluded above, but ensure clean output)

    output_json = {
        "metadata": {
            "experiment": "Phase 5 Stage 7: Optimize-or-Skip Compiler Decision Framework",
            "reduction_threshold": REDUCTION_THRESHOLD,
            "n_training_circuits": len(train_df),
            "n_features": len(feature_cols),
            "feature_names": feature_cols,
            "data_sources": list(DATA_FILES.keys()),
        },
        "predictor_results": {
            "rule_based": results["rule_based"],
            "threshold": results["threshold"],
            "ml_random_forest": results["ml_random_forest"],
            "ensemble": results["ensemble"],
        },
        "predictor_comparison": results["predictor_comparison"],
        "window_scaling_analysis": results.get("window_scaling_analysis", {}),
        "e10_random_baseline": results.get("e10_random_baseline", {}),
        "recommendation": results["recommendation"],
        "per_circuit_predictions": results["per_circuit_predictions"],
        "api_usage": {
            "class": "OptimizeOrSkip",
            "strategies": ["rule", "threshold", "ml", "ensemble"],
            "usage_example": (
                "framework = OptimizeOrSkip(strategy='ensemble')\n"
                "framework.fit(training_data)\n"
                "result = framework.predict(circuit_features)\n"
                "# result = {'decision': 'OPTIMIZE'|'SKIP', "
                "'expected_gain': float, 'confidence': float}"
            ),
        },
    }

    with open(output_path, "w") as f:
        json.dump(output_json, f, indent=2, default=str)
    print(f"\n  Results saved to: {output_path}")

    # ======================================================================
    # Also demonstrate the OptimizeOrSkip API
    # ======================================================================
    print("\n" + "=" * 72)
    print("[9] OptimizeOrSkip API Demonstration")
    print("=" * 72)

    framework = OptimizeOrSkip(strategy="ensemble")
    framework.fit(train_df)

    # Test on a few synthetic examples
    test_cases = [
        {
            "name": "CNOT chain (8 qubits, 64 CNOTs)",
            "features": {
                "n_qubits": 8, "depth": 64, "gate_count_total": 64,
                "gate_count_1q": 0, "gate_count_2q": 64, "gate_count_multiq": 0,
                "two_qubit_ratio": 1.0, "multi_qubit_ratio": 0.0,
                "one_qubit_ratio": 0.0, "cancellable_pair_count": 32,
                "mergeable_rotation_count": 0, "adjacent_commuting_pairs": 63,
                "commutation_enabled_inverse_pairs": 3,
                "commuting_block_count": 64, "mean_block_size": 1.0,
                "max_block_size": 2, "structural_lower_bound": 0,
                "structural_upper_bound_reduction": 1.0,
                "cancellable_ratio": 0.5, "mergeable_ratio": 0,
                "commutation_ratio": 0.047, "depth_per_qubit": 8.0,
                "gate_density": 1.0, "circuit_family": "CNOT",
            },
        },
        {
            "name": "QFT (5 qubits, 15 gates)",
            "features": {
                "n_qubits": 5, "depth": 9, "gate_count_total": 15,
                "gate_count_1q": 5, "gate_count_2q": 10, "gate_count_multiq": 0,
                "two_qubit_ratio": 0.667, "multi_qubit_ratio": 0.0,
                "one_qubit_ratio": 0.333, "cancellable_pair_count": 0,
                "mergeable_rotation_count": 0, "adjacent_commuting_pairs": 3,
                "commutation_enabled_inverse_pairs": 0,
                "commuting_block_count": 12, "mean_block_size": 1.25,
                "max_block_size": 2, "structural_lower_bound": 0,
                "structural_upper_bound_reduction": 0.0,
                "cancellable_ratio": 0, "mergeable_ratio": 0,
                "commutation_ratio": 0, "depth_per_qubit": 1.8,
                "gate_density": 0.333, "circuit_family": "QFT",
            },
        },
        {
            "name": "Random Clifford (4 qubits, 28 gates)",
            "features": {
                "n_qubits": 4, "depth": 10, "gate_count_total": 28,
                "gate_count_1q": 24, "gate_count_2q": 4, "gate_count_multiq": 0,
                "two_qubit_ratio": 0.143, "multi_qubit_ratio": 0.0,
                "one_qubit_ratio": 0.857, "cancellable_pair_count": 0,
                "mergeable_rotation_count": 0, "adjacent_commuting_pairs": 24,
                "commutation_enabled_inverse_pairs": 1,
                "commuting_block_count": 4, "mean_block_size": 7.0,
                "max_block_size": 13, "structural_lower_bound": 0,
                "structural_upper_bound_reduction": 0.071,
                "cancellable_ratio": 0, "mergeable_ratio": 0,
                "commutation_ratio": 0.036, "depth_per_qubit": 2.5,
                "gate_density": 0.7, "circuit_family": "RandomClifford",
            },
        },
        {
            "name": "VQE ansatz (5 qubits, 24 gates)",
            "features": {
                "n_qubits": 5, "depth": 8, "gate_count_total": 24,
                "gate_count_1q": 20, "gate_count_2q": 4, "gate_count_multiq": 0,
                "two_qubit_ratio": 0.167, "multi_qubit_ratio": 0.0,
                "one_qubit_ratio": 0.833, "cancellable_pair_count": 0,
                "mergeable_rotation_count": 0, "adjacent_commuting_pairs": 15,
                "commutation_enabled_inverse_pairs": 0,
                "commuting_block_count": 9, "mean_block_size": 2.667,
                "max_block_size": 4, "structural_lower_bound": 0,
                "structural_upper_bound_reduction": 0.0,
                "cancellable_ratio": 0, "mergeable_ratio": 0,
                "commutation_ratio": 0, "depth_per_qubit": 1.6,
                "gate_density": 0.6, "circuit_family": "VQE",
            },
        },
    ]

    for tc in test_cases:
        result = framework.predict(tc["features"])
        print(f"\n  {tc['name']}:")
        print(f"    Decision:      {result['decision']}")
        print(f"    Expected gain: {result['expected_gain']:.4f}")
        print(f"    Confidence:    {result['confidence']:.4f}")
        if "sub_predictions" in result:
            for sub_name, sub_pred in result["sub_predictions"].items():
                print(f"      [{sub_name:10s}] {sub_pred['decision']:8s} "
                      f"(gain={sub_pred['expected_gain']:.4f}, "
                      f"conf={sub_pred['confidence']:.2f})")

    print("\n" + "=" * 72)
    print("DONE. All results saved to:")
    print(f"  {output_path}")
    print(f"  {Path(__file__).resolve()}")
    print("=" * 72)


if __name__ == "__main__":
    main()
