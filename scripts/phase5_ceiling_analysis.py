#!/usr/bin/env python3
"""
PHASE 5 - Stages 2-4: Root Cause Analysis, Predictability Study, Universal Laws
Quantum Circuit Optimization Research Pipeline
"""

import json
import warnings
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import curve_fit

warnings.filterwarnings('ignore', category=DeprecationWarning, module='qiskit')

# ============================================================
# CONFIGURATION
# ============================================================
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config

BASE = str(config.PROJECT_ROOT)


def _latest_csv(directory: str, prefix: str) -> str:
    """Dynamically resolve the latest CSV in ``directory`` whose name starts
    with ``prefix``. Prefers ``_full_`` runs over ``_smoke_`` runs so the
    script does not break when fresh timestamped data files are generated.
    """
    dirp = Path(directory)
    candidates = sorted(dirp.glob(f"{prefix}*.csv"))
    if not candidates:
        return os.path.join(directory, f"{prefix}_NOT_FOUND.csv")
    full_runs = [f for f in candidates if "_full_" in f.name]
    return str((full_runs or candidates)[-1])


DATA_FILES = {
    "e10": _latest_csv(os.path.join(BASE, "data", "v5", "e10"), "e10_expanded_phase1_vs_phase2"),
    "e11": _latest_csv(os.path.join(BASE, "data", "v4", "e11"), "e11_real_circuit_benchmark_e11_full"),
    "e13": _latest_csv(os.path.join(BASE, "data", "v4", "e13"), "e13_structural_ceiling_e13_full"),
    "e14": _latest_csv(os.path.join(BASE, "data", "v5", "e14"), "e14_extended_benchmark_e14_full"),
    "e16": _latest_csv(os.path.join(BASE, "data", "v5", "e16"), "e16_window_scaling_e16_full"),
    "e17": _latest_csv(os.path.join(BASE, "data", "v5", "e17"), "e17_connectivity_e17_full"),
    "e18": _latest_csv(os.path.join(BASE, "data", "v5", "e18"), "e18_clifford_t_e18_full"),
    "e01": _latest_csv(os.path.join(BASE, "data", "v2_fixed", "e01"), "e01_phase_transition_v2"),
    "e02": _latest_csv(os.path.join(BASE, "data", "v2_fixed", "e02"), "e02_entanglement_density_v2"),
}

OUTPUT_DIR = os.path.join(BASE, "analysis")
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 80)
print("PHASE 5 ANALYSIS PIPELINE - Stages 2-4")
print("=" * 80)

# ============================================================
# STAGE 1: Load all data
# ============================================================
print("\n[STAGE 1] Loading all CSV data files...")
data = {}
for key, path in DATA_FILES.items():
    try:
        df = pd.read_csv(path)
        data[key] = df
        print(f"  {key}: {len(df)} rows, {len(df.columns)} cols - columns: {list(df.columns[:8])}...")
    except Exception as e:
        print(f"  {key}: ERROR - {e}")

# ============================================================
# STAGE 2: Root Cause Analysis
# ============================================================
print("\n" + "=" * 80)
print("[STAGE 2] ROOT CAUSE ANALYSIS")
print("=" * 80)

# --- E13 Structural Features ---
print("\n--- E13: Structural Ceiling Features ---")
e13 = data["e13"].copy()
e13_cols_of_interest = [
    'circuit_family', 'circuit_id', 'n_qubits', 'depth', 'gate_count_total',
    'gate_count_1q', 'gate_count_2q', 'gate_count_multiq',
    'commuting_block_count', 'mean_block_size', 'max_block_size',
    'cancellable_pair_count', 'mergeable_rotation_count',
    'adjacent_commuting_pairs', 'commutation_enabled_inverse_pairs',
    'structural_upper_bound_reduction', 'observed_best_reduction',
    'ceiling_gap'
]
available_e13 = [c for c in e13_cols_of_interest if c in e13.columns]
print(f"  Available columns: {available_e13}")
print(f"  Circuit families: {sorted(e13['circuit_family'].unique())}")

# Per-family aggregation from E13
e13_family = e13.groupby('circuit_family').agg({
    'structural_upper_bound_reduction': 'mean',
    'cancellable_pair_count': 'mean',
    'mergeable_rotation_count': 'mean',
    'commutation_enabled_inverse_pairs': 'mean',
    'commuting_block_count': 'mean',
    'mean_block_size': 'mean',
    'max_block_size': 'mean',
    'n_qubits': 'mean',
    'depth': 'mean',
    'gate_count_total': 'mean',
}).reset_index()
e13_family.columns = [
    'circuit_family', 'structural_upper_bound_reduction',
    'cancellable_pair_count', 'mergeable_rotation_count',
    'commutation_enabled_inverse_pairs',
    'commuting_block_count', 'mean_block_size', 'max_block_size',
    'n_qubits_e13', 'depth_e13', 'gate_count_total_e13'
]
print("\n  E13 Per-Family Structural Features:")
print(e13_family.to_string(index=False))

# --- E14 Benchmark Features ---
print("\n--- E14: Extended Benchmark Features ---")
e14 = data["e14"].copy()
e14_cols = [c for c in ['circuit_family', 'n_qubits', 'depth', 'gate_count_total',
                         'gate_count_1q', 'gate_count_2q', 'gate_count_multiq',
                         'reduction', 'optimizer', 'window_size'] if c in e14.columns]
print(f"  Available columns: {e14_cols}")

# Per (circuit_family, optimizer) aggregation
e14_grouped = e14.groupby(['circuit_family', 'optimizer']).agg({
    'reduction': ['mean', 'std', 'max'],
    'n_qubits': 'mean',
    'depth': 'mean',
    'gate_count_total': 'mean',
    'gate_count_1q': 'mean',
    'gate_count_2q': 'mean',
}).reset_index()
e14_grouped.columns = [
    'circuit_family', 'optimizer',
    'mean_reduction', 'std_reduction', 'max_reduction',
    'n_qubits', 'depth', 'gate_count_total',
    'gate_count_1q', 'gate_count_2q'
]
print(f"\n  E14 grouped shape: {e14_grouped.shape}")
print(f"  Circuit families: {sorted(e14_grouped['circuit_family'].unique())}")
print(f"  Optimizers: {sorted(e14_grouped['optimizer'].unique())}")

# Compute derived features
print("\n--- Computing Derived Features ---")

# Merge E13 + E14 on circuit_family
merged = e14_grouped.merge(e13_family, on='circuit_family', how='left')

# inverse_pair_density
merged['inverse_pair_density'] = merged.apply(
    lambda r: r['cancellable_pair_count'] / r['gate_count_total'] if r['gate_count_total'] > 0 else 0, axis=1)

# commutation_density
merged['commutation_density'] = merged.apply(
    lambda r: r['commutation_enabled_inverse_pairs'] / r['gate_count_total'] if r['gate_count_total'] > 0 else 0, axis=1)

# two_qubit_ratio
merged['two_qubit_ratio'] = merged.apply(
    lambda r: r['gate_count_2q'] / r['gate_count_total'] if r['gate_count_total'] > 0 else 0, axis=1)

print("\n  Merged dataset with derived features:")
display_cols = ['circuit_family', 'optimizer', 'mean_reduction', 'inverse_pair_density',
                'commutation_density', 'two_qubit_ratio', 'structural_upper_bound_reduction']
available_display = [c for c in display_cols if c in merged.columns]
print(merged[available_display].to_string(index=False))

# --- Correlation Analysis ---
print("\n--- Correlation Analysis (Pearson & Spearman) ---")
numeric_features = [
    'n_qubits', 'depth', 'gate_count_total', 'gate_count_1q', 'gate_count_2q',
    'two_qubit_ratio', 'inverse_pair_density', 'commutation_density',
    'cancellable_pair_count', 'mergeable_rotation_count',
    'commutation_enabled_inverse_pairs', 'commuting_block_count',
    'mean_block_size', 'max_block_size', 'structural_upper_bound_reduction'
]
available_features = [f for f in numeric_features if f in merged.columns and merged[f].notna().sum() > 2]
target = 'mean_reduction'

correlation_results = {}
for feat in available_features:
    valid = merged[[target, feat]].dropna()
    if len(valid) >= 3:
        pearson_r, pearson_p = stats.pearsonr(valid[target], valid[feat])
        spearman_r, spearman_p = stats.spearmanr(valid[target], valid[feat])
        correlation_results[feat] = {
            'pearson_r': round(pearson_r, 4),
            'pearson_p': round(pearson_p, 6),
            'spearman_r': round(spearman_r, 4),
            'spearman_p': round(spearman_p, 6),
            'n_samples': len(valid)
        }
        sig_pearson = "***" if pearson_p < 0.001 else "**" if pearson_p < 0.01 else "*" if pearson_p < 0.05 else ""
        sig_spearman = "***" if spearman_p < 0.001 else "**" if spearman_p < 0.01 else "*" if spearman_p < 0.05 else ""
        print(f"  {feat:40s}  Pearson={pearson_r:+.4f}{sig_pearson:3s}  Spearman={spearman_r:+.4f}{sig_spearman:3s}  (n={len(valid)})")

# --- Causal vs Correlated Analysis ---
print("\n--- Causal vs Merely Correlated Analysis ---")
causal_analysis = {}
for feat in available_features:
    valid = merged[[target, feat]].dropna()
    if len(valid) < 3:
        continue

    zero_reduction = valid[valid[target] == 0]
    nonzero_reduction = valid[valid[target] > 0]

    feat_zero_when_zero = zero_reduction[feat].mean() if len(zero_reduction) > 0 else None
    feat_nonzero_when_positive = nonzero_reduction[feat].mean() if len(nonzero_reduction) > 0 else None

    # Causal criterion: feature is ~0 when reduction=0 AND >0 when reduction>0
    is_causal = False
    classification = "insufficient_data"
    if feat_zero_when_zero is not None and feat_nonzero_when_positive is not None:
        if len(zero_reduction) > 0 and len(nonzero_reduction) > 0:
            # Check if feature varies while reduction stays at zero
            feat_var_zero = zero_reduction[feat].std() if len(zero_reduction) > 1 else 0
            if abs(feat_zero_when_zero) < 1e-10 and abs(feat_nonzero_when_positive) > 1e-10:
                is_causal = True
                classification = "potential_causal"
            elif feat_var_zero > 0.01 and abs(feat_nonzero_when_positive - feat_zero_when_zero) < 0.01:
                classification = "merely_correlated"
            elif abs(feat_nonzero_when_positive) > abs(feat_zero_when_zero) * 2 + 0.01:
                classification = "potential_causal"
                is_causal = True
            else:
                classification = "weakly_associated"

    causal_analysis[feat] = {
        'classification': classification,
        'mean_when_reduction_zero': round(feat_zero_when_zero, 6) if feat_zero_when_zero is not None else None,
        'mean_when_reduction_positive': round(feat_nonzero_when_positive, 6) if feat_nonzero_when_positive is not None else None,
        'n_zero': len(zero_reduction),
        'n_positive': len(nonzero_reduction),
    }
    print(f"  {feat:40s}  [{classification:20s}]  zero_red_mean={feat_zero_when_zero}  pos_red_mean={feat_nonzero_when_positive}")

# Save Stage 2 results
root_cause_results = {
    "e13_family_features": e13_family.to_dict(orient='records'),
    "correlation_analysis": correlation_results,
    "causal_analysis": causal_analysis,
    "merged_sample": merged[available_display].head(50).to_dict(orient='records'),
}
with open(os.path.join(OUTPUT_DIR, "phase5_root_cause.json"), 'w') as f:
    json.dump(root_cause_results, f, indent=2, default=str)
print(f"\n  Saved: {os.path.join(OUTPUT_DIR, 'phase5_root_cause.json')}")


# ============================================================
# STAGE 3: Predictability Study
# ============================================================
print("\n" + "=" * 80)
print("[STAGE 3] PREDICTABILITY STUDY")
print("=" * 80)

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline

# Build feature matrix from E14
print("\n--- Building Feature Matrix ---")
# Use per-row E14 data (not grouped) for richer ML
e14_ml = e14.copy()

# Ensure numeric columns
for col in ['reduction', 'n_qubits', 'depth', 'gate_count_total', 'gate_count_1q', 'gate_count_2q']:
    if col in e14_ml.columns:
        e14_ml[col] = pd.to_numeric(e14_ml[col], errors='coerce')

# Add two_qubit_ratio
e14_ml['two_qubit_ratio'] = e14_ml.apply(
    lambda r: r['gate_count_2q'] / r['gate_count_total'] if r['gate_count_total'] > 0 else 0, axis=1)

# One-hot encode circuit_family and optimizer
e14_ml = pd.get_dummies(e14_ml, columns=['circuit_family', 'optimizer'], prefix=['cf', 'opt'], drop_first=True)

# Add window_size if available
if 'window_size' not in e14_ml.columns:
    e14_ml['window_size'] = 10  # default

# Merge E13 structural features
e13_struct = e13_family.copy()
e13_struct_map = {}
for _, row in e13_struct.iterrows():
    e13_struct_map[row['circuit_family']] = row

# Map structural features back to e14 rows via circuit_family column from original
cf_col = [c for c in e14.columns if 'circuit_family' in c.lower()]
original_cf = data["e14"]['circuit_family'] if 'circuit_family' in data["e14"].columns else None

if original_cf is not None:
    for struct_col in ['structural_upper_bound_reduction', 'cancellable_pair_count',
                       'commutation_enabled_inverse_pairs', 'commuting_block_count',
                       'mean_block_size', 'max_block_size', 'mergeable_rotation_count']:
        if struct_col in e13.columns:
            mapping = e13.groupby('circuit_family')[struct_col].mean().to_dict()
            e14_ml[f'e13_{struct_col}'] = original_cf.map(mapping)

# Select features
target_col = 'reduction'
exclude_cols = [target_col, 'circuit_id', 'circuit_type', 'benchmark_suite',
                'baseline_gate_count', 'optimized_gate_count', 'reduction_pct',
                'depth_reduction', 'two_qubit_reduction', 'cnot_reduction',
                'original_depth', 'optimized_depth', 'original_2q_gates',
                'optimized_2q_gates', 'original_cnot_count', 'optimized_cnot_count',
                'fidelity', 'success', 'runtime_seconds', 'optimizer_version',
                'optimizer_config_json', 'seed', 'trial', 'source_file',
                'source_sha256', 'input_circuit_sha256', 'output_circuit_sha256',
                'notes', 'schema_version', 'experiment_id', 'run_id',
                'timestamp_utc', 'env_id', 'gate_count_multiq',
                'gate_counts_json', 'compiler', 'compiler_version',
                'compiler_optimization_level', 'compiler_config_id']

feature_cols = [c for c in e14_ml.columns if c not in exclude_cols
                and e14_ml[c].dtype in ['float64', 'int64', 'float32', 'int32', 'bool', 'uint8']]

print(f"  Target: {target_col}")
print(f"  Feature columns ({len(feature_cols)}): {feature_cols}")
print(f"  Samples: {len(e14_ml)}")

# Clean data
ml_data = e14_ml[feature_cols + [target_col]].dropna()
X = ml_data[feature_cols].values
y = ml_data[target_col].values

print(f"  Clean samples: {len(X)}")

# Standardize
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# --- Train Models ---
print("\n--- Training Models (5-fold CV) ---")

models = {
    'Linear Regression': LinearRegression(),
    'Random Forest (100 trees)': RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
    'Gradient Boosting (100 est)': GradientBoostingRegressor(n_estimators=100, random_state=42),
}

prediction_results = {}
for name, model in models.items():
    print(f"\n  Model: {name}")

    # Use standardized for linear, raw for tree-based
    if 'Linear' in name:
        X_use = X_scaled
    else:
        X_use = X

    # 5-fold CV
    cv_r2 = cross_val_score(model, X_use, y, cv=5, scoring='r2')
    cv_mae = cross_val_score(model, X_use, y, cv=5, scoring='neg_mean_absolute_error')
    cv_rmse = cross_val_score(model, X_use, y, cv=5, scoring='neg_root_mean_squared_error')

    # Fit on full data for feature importance
    model.fit(X_use, y)
    y_pred = model.predict(X_use)
    train_r2 = r2_score(y, y_pred)
    train_mae = mean_absolute_error(y, y_pred)
    train_rmse = np.sqrt(mean_squared_error(y, y_pred))

    result = {
        'cv_r2_mean': round(float(np.mean(cv_r2)), 4),
        'cv_r2_std': round(float(np.std(cv_r2)), 4),
        'cv_mae_mean': round(float(-np.mean(cv_mae)), 4),
        'cv_rmse_mean': round(float(-np.mean(cv_rmse)), 4),
        'train_r2': round(float(train_r2), 4),
        'train_mae': round(float(train_mae), 4),
        'train_rmse': round(float(train_rmse), 4),
    }

    # Feature importance for tree-based models
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        feat_imp = sorted(zip(feature_cols, importances), key=lambda x: -x[1])
        result['feature_importances'] = {k: round(float(v), 6) for k, v in feat_imp}
        print(f"    Top 5 features:")
        for k, v in feat_imp[:5]:
            print(f"      {k:40s}  importance={v:.4f}")

    prediction_results[name] = result
    print(f"    CV R2={np.mean(cv_r2):.4f} +/- {np.std(cv_r2):.4f}")
    print(f"    CV MAE={-np.mean(cv_mae):.4f}  CV RMSE={-np.mean(cv_rmse):.4f}")
    print(f"    Train R2={train_r2:.4f}  MAE={train_mae:.4f}  RMSE={train_rmse:.4f}")

# --- E13 Structural Upper Bound Prediction ---
print("\n--- E13: Predicting structural_upper_bound_reduction ---")
e13_ml = e13.copy()
e13_features = ['n_qubits', 'depth', 'gate_count_total', 'gate_count_1q', 'gate_count_2q']
e13_features = [f for f in e13_features if f in e13_ml.columns]
e13_ml['two_qubit_ratio_e13'] = e13_ml.apply(
    lambda r: r['gate_count_2q'] / r['gate_count_total'] if r['gate_count_total'] > 0 else 0, axis=1)
e13_features.append('two_qubit_ratio_e13')
e13_target = 'structural_upper_bound_reduction'

e13_clean = e13_ml[e13_features + [e13_target]].dropna()
X_e13 = e13_clean[e13_features].values
y_e13 = e13_clean[e13_target].values

print(f"  Samples: {len(X_e13)}, Features: {e13_features}")

e13_models = {
    'Linear': LinearRegression(),
    'RF': RandomForestRegressor(n_estimators=100, random_state=42),
    'GB': GradientBoostingRegressor(n_estimators=100, random_state=42),
}

e13_pred_results = {}
for name, model in e13_models.items():
    cv_r2 = cross_val_score(model, X_e13, y_e13, cv=min(5, len(X_e13)), scoring='r2')
    model.fit(X_e13, y_e13)
    train_r2 = r2_score(y_e13, model.predict(X_e13))
    e13_pred_results[name] = {
        'cv_r2_mean': round(float(np.mean(cv_r2)), 4),
        'train_r2': round(float(train_r2), 4),
    }
    if hasattr(model, 'feature_importances_'):
        e13_pred_results[name]['feature_importances'] = {
            k: round(float(v), 6) for k, v in zip(e13_features, model.feature_importances_)
        }
    print(f"  {name:10s}  CV R2={np.mean(cv_r2):.4f}  Train R2={train_r2:.4f}")

prediction_results['e13_structural_prediction'] = e13_pred_results

# Save Stage 3 results
with open(os.path.join(OUTPUT_DIR, "phase5_prediction_results.json"), 'w') as f:
    json.dump(prediction_results, f, indent=2, default=str)
print(f"\n  Saved: {os.path.join(OUTPUT_DIR, 'phase5_prediction_results.json')}")


# ============================================================
# STAGE 4: Search for Universal Laws
# ============================================================
print("\n" + "=" * 80)
print("[STAGE 4] SEARCH FOR UNIVERSAL LAWS")
print("=" * 80)

# Use merged dataset (family-level aggregated)
# For each circuit family, take best reduction across optimizers
family_best = merged.groupby('circuit_family').agg({
    'mean_reduction': 'max',
    'inverse_pair_density': 'first',
    'commutation_density': 'first',
    'two_qubit_ratio': 'first',
    'n_qubits': 'first',
    'depth': 'first',
    'gate_count_total': 'first',
    'structural_upper_bound_reduction': 'first',
    'cancellable_pair_count': 'first',
    'commutation_enabled_inverse_pairs': 'first',
    'commuting_block_count': 'first',
    'mean_block_size': 'first',
    'max_block_size': 'first',
}).reset_index()

print(f"\n  Family-level dataset ({len(family_best)} families):")
print(family_best[['circuit_family', 'mean_reduction', 'inverse_pair_density',
                  'commutation_density', 'two_qubit_ratio']].to_string(index=False))

# --- Polynomial Regression ---
print("\n--- Polynomial Regression (degree 2) ---")
poly_features_names = ['inverse_pair_density', 'commutation_density', 'two_qubit_ratio',
                       'n_qubits', 'depth', 'structural_upper_bound_reduction']
poly_available = [f for f in poly_features_names if f in family_best.columns and family_best[f].notna().sum() > 0]

poly_data = family_best[poly_available + ['mean_reduction']].dropna()
X_poly_raw = poly_data[poly_available].values
y_poly = poly_data['mean_reduction'].values

if len(X_poly_raw) >= 5:
    poly_transformer = PolynomialFeatures(degree=2, include_bias=False, interaction_only=False)
    X_poly = poly_transformer.fit_transform(X_poly_raw)
    poly_feature_names = poly_transformer.get_feature_names_out(poly_available)

    poly_model = LinearRegression()
    poly_model.fit(X_poly, y_poly)
    y_pred_poly = poly_model.predict(X_poly)
    poly_r2 = r2_score(y_poly, y_pred_poly)

    # Get top 5 terms by coefficient magnitude
    coef_df = pd.DataFrame({
        'term': poly_feature_names,
        'coefficient': poly_model.coef_
    }).sort_values('coefficient', key=abs, ascending=False)

    print(f"  R2 = {poly_r2:.4f}")
    print(f"  Top 10 polynomial terms:")
    for _, row in coef_df.head(10).iterrows():
        print(f"    {row['term']:50s}  coef={row['coefficient']:+.6f}")

    # Build candidate equations
    candidate_equations = []
    for _, row in coef_df.head(5).iterrows():
        candidate_equations.append({
            'term': row['term'],
            'coefficient': round(float(row['coefficient']), 6),
            'r2_contribution': 'top_term'
        })
else:
    candidate_equations = []
    poly_r2 = 0
    print("  Insufficient data for polynomial regression.")

# --- Analytical Form Fitting ---
print("\n--- Analytical Form Fitting ---")

# Use the per-row merged data for more samples
analytical_data = merged[['mean_reduction', 'inverse_pair_density', 'commutation_density',
                          'two_qubit_ratio']].dropna()
x_ipd = analytical_data['inverse_pair_density'].values
x_cd = analytical_data['commutation_density'].values
y_red = analytical_data['mean_reduction'].values

print(f"  Using {len(analytical_data)} samples for analytical fitting")

analytical_results = {}

# Form 1: reduction = a * inverse_pair_density + b
print("\n  Form 1: reduction = a * inverse_pair_density + b")
try:
    def linear_ipd(x, a, b):
        return a * x + b
    popt1, pcov1 = curve_fit(linear_ipd, x_ipd, y_red, p0=[1.0, 0.0], maxfev=10000)
    y_pred1 = linear_ipd(x_ipd, *popt1)
    r2_1 = r2_score(y_red, y_pred1)
    analytical_results['linear_ipd'] = {
        'equation': f"reduction = {popt1[0]:.6f} * inverse_pair_density + {popt1[1]:.6f}",
        'params': {'a': round(float(popt1[0]), 6), 'b': round(float(popt1[1]), 6)},
        'r2': round(float(r2_1), 6)
    }
    print(f"    a={popt1[0]:.6f}, b={popt1[1]:.6f}, R2={r2_1:.4f}")
except Exception as e:
    print(f"    Fit failed: {e}")
    analytical_results['linear_ipd'] = {'error': str(e)}

# Form 2: reduction = a * log(inverse_pair_density + 1) + b
print("\n  Form 2: reduction = a * log(inverse_pair_density + 1) + b")
try:
    def log_ipd(x, a, b):
        return a * np.log(x + 1) + b
    popt2, pcov2 = curve_fit(log_ipd, x_ipd, y_red, p0=[1.0, 0.0], maxfev=10000)
    y_pred2 = log_ipd(x_ipd, *popt2)
    r2_2 = r2_score(y_red, y_pred2)
    analytical_results['log_ipd'] = {
        'equation': f"reduction = {popt2[0]:.6f} * log(inverse_pair_density + 1) + {popt2[1]:.6f}",
        'params': {'a': round(float(popt2[0]), 6), 'b': round(float(popt2[1]), 6)},
        'r2': round(float(r2_2), 6)
    }
    print(f"    a={popt2[0]:.6f}, b={popt2[1]:.6f}, R2={r2_2:.4f}")
except Exception as e:
    print(f"    Fit failed: {e}")
    analytical_results['log_ipd'] = {'error': str(e)}

# Form 3: reduction = a * inverse_pair_density^c
print("\n  Form 3: reduction = a * inverse_pair_density^c")
try:
    # Avoid log(0) issues
    x_ipd_pos = x_ipd.copy()
    mask_pos = x_ipd_pos > 1e-10
    if mask_pos.sum() >= 3:
        def power_ipd(x, a, c):
            return a * np.power(np.maximum(x, 1e-10), c)
        popt3, pcov3 = curve_fit(power_ipd, x_ipd, y_red, p0=[1.0, 1.0], maxfev=10000)
        y_pred3 = power_ipd(x_ipd, *popt3)
        r2_3 = r2_score(y_red, y_pred3)
        analytical_results['power_ipd'] = {
            'equation': f"reduction = {popt3[0]:.6f} * inverse_pair_density^{popt3[1]:.6f}",
            'params': {'a': round(float(popt3[0]), 6), 'c': round(float(popt3[1]), 6)},
            'r2': round(float(r2_3), 6)
        }
        print(f"    a={popt3[0]:.6f}, c={popt3[1]:.6f}, R2={r2_3:.4f}")
    else:
        print("    Insufficient positive samples")
        analytical_results['power_ipd'] = {'error': 'insufficient_positive_samples'}
except Exception as e:
    print(f"    Fit failed: {e}")
    analytical_results['power_ipd'] = {'error': str(e)}

# Form 4: reduction = a * commutation_density + b * inverse_pair_density + c
print("\n  Form 4: reduction = a * commutation_density + b * inverse_pair_density + c")
try:
    def multilinear(x_data, a, b, c):
        return a * x_data[0] + b * x_data[1] + c
    x_multi = np.array([x_cd, x_ipd])
    popt4, pcov4 = curve_fit(multilinear, x_multi, y_red, p0=[1.0, 1.0, 0.0], maxfev=10000)
    y_pred4 = multilinear(x_multi, *popt4)
    r2_4 = r2_score(y_red, y_pred4)
    analytical_results['multilinear'] = {
        'equation': f"reduction = {popt4[0]:.6f} * commutation_density + {popt4[1]:.6f} * inverse_pair_density + {popt4[2]:.6f}",
        'params': {'a': round(float(popt4[0]), 6), 'b': round(float(popt4[1]), 6), 'c': round(float(popt4[2]), 6)},
        'r2': round(float(r2_4), 6)
    }
    print(f"    a={popt4[0]:.6f}, b={popt4[1]:.6f}, c={popt4[2]:.6f}, R2={r2_4:.4f}")
except Exception as e:
    print(f"    Fit failed: {e}")
    analytical_results['multilinear'] = {'error': str(e)}

# Form 5: reduction = a * (1 - exp(-b * inverse_pair_density))
print("\n  Form 5: reduction = a * (1 - exp(-b * inverse_pair_density))")
try:
    def exp_saturation(x, a, b):
        return a * (1 - np.exp(-b * x))
    popt5, pcov5 = curve_fit(exp_saturation, x_ipd, y_red, p0=[0.5, 5.0], maxfev=10000)
    y_pred5 = exp_saturation(x_ipd, *popt5)
    r2_5 = r2_score(y_red, y_pred5)
    analytical_results['exp_saturation'] = {
        'equation': f"reduction = {popt5[0]:.6f} * (1 - exp(-{popt5[1]:.6f} * inverse_pair_density))",
        'params': {'a': round(float(popt5[0]), 6), 'b': round(float(popt5[1]), 6)},
        'r2': round(float(r2_5), 6)
    }
    print(f"    a={popt5[0]:.6f}, b={popt5[1]:.6f}, R2={r2_5:.4f}")
except Exception as e:
    print(f"    Fit failed: {e}")
    analytical_results['exp_saturation'] = {'error': str(e)}

# --- Rank all candidate equations ---
print("\n--- Ranking Candidate Equations ---")
all_candidates = []

# Add polynomial top terms
for eq in candidate_equations:
    all_candidates.append({
        'type': 'polynomial_term',
        'description': f"Poly term: {eq['term']} (coef={eq['coefficient']})",
        'r2': round(float(poly_r2), 6),
        'equation': f"reduction ~ {eq['coefficient']} * {eq['term']} + ..."
    })

# Add analytical forms
for name, result in analytical_results.items():
    if 'error' not in result:
        all_candidates.append({
            'type': 'analytical',
            'description': name,
            'r2': result['r2'],
            'equation': result['equation']
        })

# Sort by R2
all_candidates.sort(key=lambda x: -x['r2'])
print("\n  Ranked candidate equations:")
for i, cand in enumerate(all_candidates):
    print(f"  #{i+1}  R2={cand['r2']:.4f}  [{cand['type']:15s}]  {cand['equation']}")

# Save Stage 4 results
universal_laws_results = {
    'polynomial_regression': {
        'r2': round(float(poly_r2), 6) if 'poly_r2' in dir() else 0,
        'top_terms': candidate_equations,
        'n_features': len(poly_available) if 'poly_available' in dir() else 0,
        'n_samples': len(poly_data) if 'poly_data' in dir() else 0,
    },
    'analytical_forms': analytical_results,
    'ranked_equations': all_candidates,
    'family_data': family_best.to_dict(orient='records'),
}

with open(os.path.join(OUTPUT_DIR, "phase5_universal_laws.json"), 'w') as f:
    json.dump(universal_laws_results, f, indent=2, default=str)
print(f"\n  Saved: {os.path.join(OUTPUT_DIR, 'phase5_universal_laws.json')}")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

print(f"\n  Output files:")
print(f"    1. {os.path.join(OUTPUT_DIR, 'phase5_root_cause.json')}")
print(f"    2. {os.path.join(OUTPUT_DIR, 'phase5_prediction_results.json')}")
print(f"    3. {os.path.join(OUTPUT_DIR, 'phase5_universal_laws.json')}")

print(f"\n  Key Findings:")
print(f"    - Total circuit families analyzed: {len(e13['circuit_family'].unique())}")
print(f"    - E14 benchmark samples: {len(e14)}")
print(f"    - ML models trained: {len(models)}")

if correlation_results:
    strongest = max(correlation_results.items(), key=lambda x: abs(x[1]['spearman_r']))
    print(f"    - Strongest Spearman correlation: {strongest[0]} (r={strongest[1]['spearman_r']})")

if all_candidates:
    best_eq = all_candidates[0]
    print(f"    - Best candidate equation: R2={best_eq['r2']:.4f} - {best_eq['equation']}")

print("\n" + "=" * 80)
print("PIPELINE COMPLETE")
print("=" * 80)
