"""
Ceiling Model Repair Script
============================
Leave-one-family-out cross-validated prediction of gate reduction
from circuit structural features.

Uses E21 data (data/v6/e21/ceiling_aware_comparison.csv).
Target: gate_reduction (naive strategy).

Two-stage model:
  1. RandomForestClassifier → predict is_reducible (> 0.1% reduction)
  2. RandomForestRegressor  → predict reduction amount (only for predicted-reducible)

Features (all pre-optimization, no leakage):
  - depth_to_width_ratio: depth / n_qubits
  - inverse_pair_density: ceiling_proxy / total_gates (Phase-1 action density)
  - cnot_fraction: CNOT / total_gates
  - gate_density: gates / n_qubit
  - log_size: log(total_gates)
  - is_ceiling_proxy_binary: (ceiling_proxy == 0) as int
  - depth_times_density: depth_to_width_ratio × inverse_pair_density (interaction)

Output: experiments/outputs/ceiling_model_results.csv
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import (
    mean_absolute_error, r2_score, accuracy_score,
    precision_score, recall_score, f1_score, confusion_matrix,
)
from scipy.stats import pearsonr, sem, spearmanr
from scipy import stats as scipy_stats

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def bootstrap_ci(y_true, y_pred, metric_fn, n_bootstrap=10000, alpha=0.05, rng_seed=42):
    """Bootstrap CI for any metric. Returns (point, lower, upper)."""
    point = metric_fn(y_true, y_pred)
    if np.isnan(point):
        return point, np.nan, np.nan
    rng = np.random.RandomState(rng_seed)
    n = len(y_true)
    vals = []
    for _ in range(n_bootstrap):
        idx = rng.randint(0, n, size=n)
        v = metric_fn(y_true[idx], y_pred[idx])
        if not np.isnan(v):
            vals.append(v)
    if len(vals) < 100:
        return point, np.nan, np.nan
    vals = np.array(vals)
    return point, np.percentile(vals, 100 * alpha / 2), np.percentile(vals, 100 * (1 - alpha / 2))


def _pearsonr(a, b):
    r, _ = pearsonr(a, b)
    return r


def _spearmanr(a, b):
    r, _ = spearmanr(a, b)
    return r


def _r2(a, b):
    return float(r2_score(a, b))


def _mae(a, b):
    return float(mean_absolute_error(a, b))


def run(output_dir: Path | None = None) -> pd.DataFrame:
    csv_path = PROJECT_ROOT / "data" / "v6" / "e21" / "ceiling_aware_comparison.csv"
    df_raw = pd.read_csv(csv_path)

    # Naive strategy rows only = actual reduction
    df = df_raw[df_raw["strategy_name"] == "naive"].copy()
    n_total = len(df)
    n_families = df["family"].nunique()
    print(f"Loaded {n_total} rows, {n_families} families from {csv_path}")

    # Per-family summary
    fam_stats = df.groupby("family").agg(
        n=("gate_reduction", "size"),
        mean_red=("gate_reduction", "mean"),
        std_red=("gate_reduction", "std"),
    )
    print("\nPer-family reduction:")
    for fam, row in fam_stats.iterrows():
        flag = " *REDUCIBLE" if row["mean_red"] > 0.001 else ""
        print(f"  {fam:20s}: mean={row['mean_red']:.4f}  std={row['std_red']:.4f}{flag}")

    # --- Feature engineering -------------------------------------------------
    df["depth_to_width_ratio"] = df["original_depth"] / df["n_qubits"].clip(lower=1)
    df["inverse_pair_density"] = df["ceiling_proxy_value"] / df["original_size"].clip(lower=1)
    df["cnot_fraction"] = df["original_cnot"] / df["original_size"].clip(lower=1)
    df["gate_density"] = df["original_size"] / df["n_qubits"].clip(lower=1)
    df["log_size"] = np.log1p(df["original_size"])
    df["is_ceiling_proxy_binary"] = (df["ceiling_proxy_value"] == 0).astype(int)
    df["depth_times_density"] = df["depth_to_width_ratio"] * df["inverse_pair_density"]

    numeric_features = [
        "depth_to_width_ratio",
        "inverse_pair_density",
        "cnot_fraction",
        "gate_density",
        "log_size",
        "is_ceiling_proxy_binary",
        "depth_times_density",
    ]
    target_col = "gate_reduction"
    binary_target_col = "is_reducible"

    df[binary_target_col] = (df[target_col] > 0.001).astype(int)

    # One-hot encode family
    ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    ohe.fit(df["family"].values.reshape(-1, 1))

    # --- LOFO CV ------------------------------------------------------------
    families = sorted(df["family"].unique())
    rows = []

    for held_out in families:
        train_mask = df["family"] != held_out
        test_mask = df["family"] == held_out

        X_train_num = df.loc[train_mask, numeric_features].values
        X_test_num = df.loc[test_mask, numeric_features].values
        y_train_reg = df.loc[train_mask, target_col].values
        y_test_reg = df.loc[test_mask, target_col].values
        y_train_cls = df.loc[train_mask, binary_target_col].values
        y_test_cls = df.loc[test_mask, binary_target_col].values

        fam_train = ohe.transform(df.loc[train_mask, "family"].values.reshape(-1, 1))
        fam_test = ohe.transform(df.loc[test_mask, "family"].values.reshape(-1, 1))

        X_train = np.column_stack([X_train_num, fam_train])
        X_test = np.column_stack([X_test_num, fam_test])

        n_train = len(y_train_reg)
        n_test = len(y_test_reg)
        n_red_train = int(y_train_cls.sum())
        n_red_test = int(y_test_cls.sum())

        # ---- Stage 1: Classifier ----
        clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=5,
            min_samples_leaf=3,
            class_weight="balanced_subsample",
            random_state=42,
        )
        clf.fit(X_train, y_train_cls)
        y_pred_cls_prob = clf.predict_proba(X_test)[:, 1]
        y_pred_cls = (y_pred_cls_prob >= 0.5).astype(int)

        clf_acc = accuracy_score(y_test_cls, y_pred_cls)
        clf_prec = precision_score(y_test_cls, y_pred_cls, zero_division=0)
        clf_rec = recall_score(y_test_cls, y_pred_cls, zero_division=0)
        clf_f1 = f1_score(y_test_cls, y_pred_cls, zero_division=0)
        cm = confusion_matrix(y_test_cls, y_pred_cls)

        # ---- Stage 2: Regressor (only trained on reducible data) ----
        red_mask_train = y_train_cls == 1
        if red_mask_train.sum() >= 5:
            X_train_red = X_train[red_mask_train]
            y_train_red = y_train_reg[red_mask_train]
            reg = RandomForestRegressor(
                n_estimators=200,
                max_depth=4,
                min_samples_leaf=3,
                random_state=42,
            )
            reg.fit(X_train_red, y_train_red)
            y_pred_reg = reg.predict(X_test)
        else:
            # Not enough reducible training examples → predict 0
            y_pred_reg = np.zeros(n_test, dtype=float)
            reg = None

        # Blend: classifier gate → regressor output
        y_pred_blend = np.where(y_pred_cls == 1, y_pred_reg, 0.0)

        # ---- Metrics ----
        mae_val = float(mean_absolute_error(y_test_reg, y_pred_blend))
        mask_nz = y_test_reg > 0.001
        mae_nz = float(mean_absolute_error(y_test_reg[mask_nz], y_pred_blend[mask_nz])) if mask_nz.sum() > 0 else np.nan

        r_val, r_lo, r_hi = bootstrap_ci(y_test_reg, y_pred_blend, _pearsonr)
        sr_val, sr_lo, sr_hi = bootstrap_ci(y_test_reg, y_pred_blend, _spearmanr)
        r2_val, r2_lo, r2_hi = bootstrap_ci(y_test_reg, y_pred_blend, _r2)

        # Feature importances
        clf_imp = _top_features(clf, numeric_features, ohe, families)
        reg_imp = _top_features(reg, numeric_features, ohe, families) if reg is not None else "N/A"

        status = "REDUCIBLE" if n_red_test > 0 else "CEILING"
        row = {
            "held_out_family": held_out,
            "n_train": n_train,
            "n_test": n_test,
            "n_reducible_train": n_red_train,
            "n_reducible_test": n_red_test,
            "mean_actual": float(y_test_reg.mean()),
            "mean_predicted": float(y_pred_blend.mean()),
            "std_actual": float(y_test_reg.std()),
            "std_predicted": float(y_pred_blend.std()),
            "mae": mae_val,
            "mae_nonzero_actual": mae_nz,
            "pearson_r": r_val,
            "pearson_ci_lower": r_lo,
            "pearson_ci_upper": r_hi,
            "spearman_r": sr_val,
            "spearman_ci_lower": sr_lo,
            "spearman_ci_upper": sr_hi,
            "r2": r2_val,
            "r2_ci_lower": r2_lo,
            "r2_ci_upper": r2_hi,
            "clf_accuracy": clf_acc,
            "clf_precision": clf_prec,
            "clf_recall": clf_rec,
            "clf_f1": clf_f1,
            "confusion_matrix": str(cm.tolist()),
            "clf_top3_features": clf_imp,
            "reg_top3_features": reg_imp,
        }
        rows.append(row)

        mae_str = f"{mae_val:.4f}"
        r_str = f"{r_val:.3f}" if not np.isnan(r_val) else " NaN "
        print(f"  {held_out:20s}: MAE={mae_str}  r={r_str}  "
              f"acc={clf_acc:.2f}  f1={clf_f1:.2f}  [{status}]")

    results = pd.DataFrame(rows)

    # --- Aggregate -----------------------------------------------------------
    print("\n========== AGGREGATE (LOFO CV, 15 folds) ==========")
    mae_vals = results["mae"].dropna()
    r_vals = results["pearson_r"].dropna()
    sr_vals = results["spearman_r"].dropna()
    r2_vals = results["r2"].dropna()
    acc_vals = results["clf_accuracy"].dropna()
    f1_vals = results["clf_f1"].dropna()

    def _report(vals, name):
        if len(vals) == 0:
            print(f"  {name}: No finite values")
            return
        mu = vals.mean()
        se = sem(vals)
        ci = se * scipy_stats.t.ppf(0.975, len(vals) - 1)
        print(f"  {name}: {mu:.4f} ± {ci:.4f}  (n={len(vals)})")

    _report(mae_vals, "MAE")
    _report(r_vals, "Pearson r")
    _report(sr_vals, "Spearman r")
    _report(r2_vals, "R2")
    _report(acc_vals, "Classification accuracy")
    _report(f1_vals, "Classification F1")

    # Concatenated metrics (pool all predictions)
    concat_rows = []
    for held_out in families:
        mask = df["family"] == held_out
        X_t = df.loc[mask, numeric_features].values
        fam_t = ohe.transform(df.loc[mask, "family"].values.reshape(-1, 1))
        X_test = np.column_stack([X_t, fam_t])

        # Retrain model on all data except held_out
        tr_mask = df["family"] != held_out
        X_tr_num = df.loc[tr_mask, numeric_features].values
        fam_tr = ohe.transform(df.loc[tr_mask, "family"].values.reshape(-1, 1))
        X_tr = np.column_stack([X_tr_num, fam_tr])
        y_tr_reg = df.loc[tr_mask, target_col].values
        y_tr_cls = df.loc[tr_mask, binary_target_col].values

        clf_c = RandomForestClassifier(
            n_estimators=200, max_depth=5, min_samples_leaf=3,
            class_weight="balanced_subsample", random_state=42,
        )
        clf_c.fit(X_tr, y_tr_cls)
        y_pc = clf_c.predict(X_test)

        reg_c = None
        red_tr = y_tr_cls == 1
        if red_tr.sum() >= 5:
            reg_c = RandomForestRegressor(
                n_estimators=200, max_depth=4, min_samples_leaf=3, random_state=42,
            )
            reg_c.fit(X_tr[red_tr], y_tr_reg[red_tr])
            y_pr = reg_c.predict(X_test)
        else:
            y_pr = np.zeros(len(X_test))

        y_pred = np.where(y_pc == 1, y_pr, 0.0)
        concat_rows.append(pd.DataFrame({
            "actual": df.loc[mask, target_col].values,
            "predicted": y_pred,
            "family": held_out,
        }))

    all_preds = pd.concat(concat_rows, ignore_index=True)
    r_all, _ = pearsonr(all_preds["actual"], all_preds["predicted"])
    sr_all, _ = spearmanr(all_preds["actual"], all_preds["predicted"])
    mae_all = float(mean_absolute_error(all_preds["actual"], all_preds["predicted"]))
    r2_all = float(r2_score(all_preds["actual"], all_preds["predicted"]))

    print(f"\n  Concatenated (pooled across all folds):")
    print(f"    MAE:         {mae_all:.4f}")
    print(f"    Pearson r:   {r_all:.4f}")
    print(f"    Spearman r:  {sr_all:.4f}")
    print(f"    R2:          {r2_all:.4f}")

    # ---- Comparison to baseline (always-predict-0) ----
    y_all = all_preds["actual"].values
    y_all_zero = np.zeros_like(y_all)
    mae_baseline = float(mean_absolute_error(y_all, y_all_zero))
    print(f"\n  Baseline (always predict 0):")
    print(f"    MAE:         {mae_baseline:.4f}")
    print(f"    R2:          {float(r2_score(y_all, y_all_zero)):.4f}")

    # ---- Save ----
    if output_dir is None:
        output_dir = PROJECT_ROOT / "experiments" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    out_csv = output_dir / "ceiling_model_results.csv"
    results.to_csv(out_csv, index=False)
    print(f"\nPer-fold results: {out_csv}")

    out_preds = output_dir / "ceiling_model_predictions.csv"
    all_preds.to_csv(out_preds, index=False)
    print(f"Per-sample predictions: {out_preds}")

    return results


def _top_features(model, num_features, ohe, families):
    if model is None:
        return "N/A"
    fam_names = list(ohe.get_feature_names_out())
    all_names = list(num_features) + fam_names
    imp = model.feature_importances_
    top3 = np.argsort(imp)[-3:][::-1]
    return "; ".join(f"{all_names[i]}({imp[i]:.3f})" for i in top3)


def main():
    run()


if __name__ == "__main__":
    main()
