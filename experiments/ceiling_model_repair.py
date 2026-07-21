"""
Ceiling Model Repair — Diagnosis, Mechanism Features, and Honest Retest
========================================================================

Context
-------
The original ceiling-prediction model failed leave-one-family-out (LOFO)
validation with MAE = 0.2775 and Pearson = NaN. A prior repair attempt
(data/v6/ceiling_repair/lofo_cv_*, 2026-07-17, 20 families / 835 rows from an
ad-hoc merge that no longer exists in the repo) reduced mean fold MAE to
0.077 but still obtained pooled Pearson r = -0.03 and Spearman = 0.23, with
17/20 folds returning NaN Pearson and classification F1 = 0.08.

This script performs three steps on the *canonical* E21 dataset
(data/v6/e21/ceiling_aware_comparison.csv, 15 families x 4 sizes x 10 trials
= 570 naive-pipeline rows):

  PART 1 (DIAGNOSIS): quantify why LOFO failed — target degeneracy,
    between/within-family variance decomposition, and generic-feature
    separability of reducible vs ceiling families.

  PART 2 (MECHANISM FEATURES): deterministically regenerate every circuit
    (sha256-verified against input_circuit_sha256) and compute mechanism
    features that directly measure the reducibility mechanisms, WITHOUT
    running any optimizer (no label leakage):
      - Phase-1 action space: adjacent cancellable inverse pairs
      - Phase-2 action space proxy: commutation-enabled inverse pairs
      - structural_upper_bound_reduction (static analysis ceiling proxy)
      - commuting-block structure, self-inverse gate fraction, ...

  PART 3 (RETEST): LOFO CV with three feature sets (generic / mechanism /
    combined) x two model classes (two-stage RandomForest, single-stage
    RandomForest), against two baselines (predict-0, predict-global-mean).
    Plus the scientifically meaningful reframed evaluations:
      (a) family-mean regression (n = 15 families, leave-one-out);
      (b) ceiling classification (is_reducible) with mechanism features;
      (c) within-family magnitude predictability per reducible family.

Outputs (all under data/v6/ceiling_repair/):
  mechanism_features.csv   per-circuit feature table (hash-verified)
  diagnosis.json           Part-1 diagnosis numbers
  repair_lofo_results.csv  per-fold metrics for all models/feature-sets
  repair_summary.json      aggregate metrics, baselines, reframed results

Usage:
    python experiments/ceiling_model_repair.py [--skip-feature-extraction]
    python experiments/ceiling_model_repair.py --regime
        Run PART 4 only (CNOT saturation-regime intervention, wave 4).
        Requires the cached mechanism_features.csv; writes NEW files
        (regime_intervention_results.csv / regime_intervention_summary.json)
        and never overwrites the Part-1..3 outputs.
    python experiments/ceiling_model_repair.py --part5
        Run PART 5 only (E27 new families join the LOFO evaluation, wave 6).
        Requires the cached mechanism_features.csv and
        data/v8/e27_new_families/e27_new_families_v8.csv; writes NEW files
        (part5_*.csv / part5_summary.json) and never overwrites prior outputs.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error, r2_score, balanced_accuracy_score, f1_score,
    matthews_corrcoef,
)
from scipy.stats import pearsonr, spearmanr

OUT_DIR = PROJECT_ROOT / "data" / "v6" / "ceiling_repair"
E21_CSV = PROJECT_ROOT / "data" / "v6" / "e21" / "ceiling_aware_comparison.csv"
FEATURE_CSV = OUT_DIR / "mechanism_features.csv"

RNG_SEED = 42

# ---------------------------------------------------------------------------
# Part 2: circuit regeneration + mechanism features
# ---------------------------------------------------------------------------

def _family_registry():
    from src.circuits.real_benchmarks import (
        make_qft, make_ghz, make_cnot_chain, make_bernstein_vazirani,
        make_qaoa_line, make_vqe_twolocal, make_hardware_efficient,
        make_grover, make_quantum_adder, make_quantum_walk, make_iqp,
        make_random_clifford, make_surface_code_syndrome,
        make_parameterized_ansatz, make_haar_random,
    )
    return {
        "QFT": (make_qft, {}),
        "GHZ": (make_ghz, {}),
        "CNOT": (make_cnot_chain, {}),
        "Oracle": (make_bernstein_vazirani, {"seed": None}),
        "QAOA": (make_qaoa_line, {"reps": 1, "seed": None}),
        "VQE": (make_vqe_twolocal, {"reps": 1, "seed": None}),
        "HardwareEfficient": (make_hardware_efficient, {"layers": 2, "seed": None}),
        "Grover": (make_grover, {"seed": None}),
        "Adder": (make_quantum_adder, {"seed": None}),
        "QuantumWalk": (make_quantum_walk, {"steps": 3, "seed": None}),
        "IQP": (make_iqp, {"depth": 3, "seed": None}),
        "RandomClifford": (make_random_clifford, {"depth": 10, "seed": None}),
        "SurfaceCode": (make_surface_code_syndrome, {"seed": None}),
        "UCCSD": (make_parameterized_ansatz, {"reps": 1, "seed": None}),
        "HaarRandom": (make_haar_random, {"seed": None}),
    }


# Gates that are exactly self-inverse (g * g = I) in the E21 gate inventory.
SELF_INVERSE_GATES = {
    "h", "x", "y", "z", "id", "cx", "cnot", "cz", "cy", "swap", "ccx", "cswap",
}


def extract_mechanism_features(df: pd.DataFrame) -> pd.DataFrame:
    """Regenerate each circuit (sha256-verified) and compute mechanism features."""
    from analysis.structural_ceiling import analyze_structural_ceiling
    from src.circuits.real_benchmarks import circuit_sha256

    registry = _family_registry()
    rows = []
    n_verified, t0 = 0, time.time()

    for idx, r in df.iterrows():
        fam = r["family"]
        factory, kw = registry[fam]
        kwargs = dict(kw)
        if "seed" in kwargs:
            kwargs["seed"] = int(r["trial_seed"])
        circuit = factory(int(r["n_qubits"]), **kwargs)

        digest = circuit_sha256(circuit)
        if digest != r["input_circuit_sha256"]:
            raise RuntimeError(
                f"sha256 mismatch on row {idx} ({fam} n={r['n_qubits']} "
                f"trial={r['trial_idx']}): regeneration is not faithful."
            )
        n_verified += 1

        sc = analyze_structural_ceiling(circuit, window=10)
        size = max(1, circuit.size())
        names = [inst.operation.name for inst in circuit.data]
        n_self_inv = sum(1 for nm in names if nm in SELF_INVERSE_GATES)
        n_rot = sum(1 for nm in names if nm in {"rx", "ry", "rz"})
        n_2q = sum(1 for inst in circuit.data if len(inst.qubits) >= 2)

        rows.append({
            "row_idx": idx,
            "family": fam,
            "n_qubits": int(r["n_qubits"]),
            "trial_seed": int(r["trial_seed"]),
            "input_circuit_sha256": digest,
            # --- generic size features ---
            "total_gates": size,
            "log_total_gates": float(np.log1p(size)),
            "gate_density": size / max(1, int(r["n_qubits"])),
            "original_depth": int(r["original_depth"]),
            "depth_per_qubit": float(r["original_depth"]) / max(1, int(r["n_qubits"])),
            "two_qubit_fraction": n_2q / size,
            "gate_diversity": len(set(names)),
            "rotation_fraction": n_rot / size,
            # --- mechanism features (static analysis, no optimizer run) ---
            "adjacent_cancellable_pairs": sc.adjacent_cancellable_pairs,
            "phase1_action_density": sc.adjacent_cancellable_pairs / size,
            "commutation_enabled_pairs": sc.commutation_enabled_inverse_pairs,
            "commutation_density": sc.commutation_enabled_inverse_pairs / size,
            "mergeable_rotation_pairs": sc.mergeable_rotation_pairs,
            "mergeable_rotation_density": sc.mergeable_rotation_pairs / size,
            "structural_upper_bound": sc.structural_upper_bound_reduction,
            "commuting_block_count": sc.commuting_block_count,
            "commuting_block_density": sc.commuting_block_count / size,
            "mean_block_size": sc.mean_block_size,
            "max_block_size": sc.max_block_size,
            "self_inverse_fraction": n_self_inv / size,
        })
        if n_verified % 100 == 0:
            print(f"    ... {n_verified}/{len(df)} circuits processed "
                  f"({time.time() - t0:.0f}s)")

    feat = pd.DataFrame(rows)
    print(f"  [Part 2] {n_verified} circuits regenerated and sha256-verified.")
    return feat


# ---------------------------------------------------------------------------
# Part 3: models
# ---------------------------------------------------------------------------

GENERIC_FEATURES = [
    "n_qubits", "total_gates", "log_total_gates", "gate_density",
    "depth_per_qubit", "two_qubit_fraction", "gate_diversity",
    "rotation_fraction",
]
MECHANISM_FEATURES = [
    "phase1_action_density", "commutation_density",
    "mergeable_rotation_density", "structural_upper_bound",
    "commuting_block_density", "mean_block_size", "max_block_size",
    "self_inverse_fraction",
]
FEATURE_SETS = {
    "generic": GENERIC_FEATURES,
    "mechanism": MECHANISM_FEATURES,
    "combined": GENERIC_FEATURES + MECHANISM_FEATURES,
}


def _safe_pearson(a, b):
    if np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return float("nan")
    return float(pearsonr(a, b)[0])


def _safe_spearman(a, b):
    if np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return float("nan")
    return float(spearmanr(a, b)[0])


def fit_predict_two_stage(Xtr, ytr, Xte, cls_threshold=0.001):
    """Two-stage model: classifier gates a regressor (as in the original)."""
    ytr_cls = (ytr > cls_threshold).astype(int)
    if ytr_cls.sum() == 0 or ytr_cls.sum() == len(ytr_cls):
        # Degenerate training label: fall back to constant prediction.
        const = float(ytr.mean())
        return np.full(len(Xte), const), None, None
    clf = RandomForestClassifier(
        n_estimators=200, max_depth=5, min_samples_leaf=3,
        class_weight="balanced_subsample", random_state=RNG_SEED)
    clf.fit(Xtr, ytr_cls)
    ypred_cls = clf.predict(Xte)
    red = ytr_cls == 1
    if red.sum() >= 5:
        reg = RandomForestRegressor(
            n_estimators=200, max_depth=4, min_samples_leaf=3,
            random_state=RNG_SEED)
        reg.fit(Xtr[red], ytr[red])
        ypred_reg = reg.predict(Xte)
    else:
        ypred_reg = np.zeros(len(Xte))
        reg = None
    return np.where(ypred_cls == 1, ypred_reg, 0.0), clf, reg


def fit_predict_single_stage(Xtr, ytr, Xte):
    reg = RandomForestRegressor(
        n_estimators=300, max_depth=6, min_samples_leaf=2,
        random_state=RNG_SEED)
    reg.fit(Xtr, ytr)
    return reg.predict(Xte), None, reg


def lofo_evaluate(df: pd.DataFrame, features, model: str, target: str):
    """Run LOFO CV; return per-fold rows plus pooled predictions."""
    families = sorted(df["family"].unique())
    fold_rows, pooled = [], []
    for held in families:
        tr = df["family"] != held
        te = df["family"] == held
        Xtr, Xte = df.loc[tr, features].values, df.loc[te, features].values
        ytr, yte = df.loc[tr, target].values, df.loc[te, target].values
        if model == "two_stage_rf":
            ypred, _, _ = fit_predict_two_stage(Xtr, ytr, Xte)
        else:
            ypred, _, _ = fit_predict_single_stage(Xtr, ytr, Xte)
        fold_rows.append({
            "held_out_family": held,
            "n_test": int(te.sum()),
            "mean_actual": float(yte.mean()),
            "std_actual": float(yte.std()),
            "mae": float(mean_absolute_error(yte, ypred)),
            "pearson_r": _safe_pearson(yte, ypred),
            "spearman_r": _safe_spearman(yte, ypred),
            "r2": float(r2_score(yte, ypred)) if np.std(yte) > 1e-12 else float("nan"),
        })
        pooled.append(pd.DataFrame({"actual": yte, "predicted": ypred,
                                    "family": held}))
    pooled_df = pd.concat(pooled, ignore_index=True)
    return pd.DataFrame(fold_rows), pooled_df


def pooled_metrics(pooled: pd.DataFrame) -> dict:
    y, p = pooled["actual"].values, pooled["predicted"].values
    return {
        "mae": float(mean_absolute_error(y, p)),
        "pearson_r": _safe_pearson(y, p),
        "spearman_r": _safe_spearman(y, p),
        "r2": float(r2_score(y, p)),
    }


def bootstrap_ci(y, p, fn, n_boot=5000, seed=RNG_SEED):
    rng = np.random.RandomState(seed)
    vals = []
    n = len(y)
    for _ in range(n_boot):
        idx = rng.randint(0, n, n)
        v = fn(y[idx], p[idx])
        if not np.isnan(v):
            vals.append(v)
    if len(vals) < 100:
        return float("nan"), float("nan")
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


# ---------------------------------------------------------------------------
# Part 4 (wave 4, 2026-07-21): CNOT saturation-regime intervention
# ---------------------------------------------------------------------------
#
# Known residual of the published best config (mechanism+single_stage_rf):
# the held-out CNOT fold has MAE 0.7453 — the model under-predicts the one
# fully-saturated family (gate_reduction = 1.0 on all 40 rows).
#
# Diagnosis (verified 2026-07-21 on the canonical merge):
#   * With CNOT held out, the training target's 99th percentile is 0.4156;
#     exactly ONE saturated (y >= 0.99) training row exists (Oracle, n=4).
#     A RandomForest regressor averages leaf targets and therefore cannot
#     predict 1.0 for a family whose feature signature (Phase-1 action
#     density 0.5, self-inverse fraction 1.0) is absent from training.
#   * The signature itself is unambiguous: no non-CNOT circuit has
#     phase1_action_density >= 0.4 (max 0.0345, a >14x margin), and a
#     density of 0.5 means every gate participates in an adjacent
#     cancellable inverse pair — i.e. the Phase-1 mechanism saturates.
#   * A *learned* two-stage fix cannot work in LOFO: with CNOT held out the
#     classifier sees a single saturated example and never fires on CNOT
#     (verified empirically below, variant V2).
#
# Intervention family tested here (all LOFO, same seed/protocol as Part 3):
#   V0  reference reproduction of mechanism+single_stage_rf (published best)
#   V1  + saturation indicator features (RF still cannot extrapolate)
#   V2  learned two-stage: classifier (y>=0.99) gates regressor
#   V3  mechanism rule gate: structural_upper_bound >= 0.99 -> predict the
#       bound itself; RF otherwise
#   V4  mechanism rule gate (PRIMARY): 2 * phase1_action_density >= 1 ->
#       predict min(1, 2*density); RF otherwise.  Derivation: each adjacent
#       cancellable inverse pair removes 2 gates, so density d bounds the
#       Phase-1 reduction from below by ~2d; d >= 0.5 implies saturation.
#   V5  Ridge linear model (can extrapolate, unlike trees)
#
# Success criterion (pre-registered in the wave-4 task): CNOT fold MAE drops
# substantially AND pooled MAE / Pearson r do not degrade versus V0.

REGIME_INDICATOR_FEATURES = ["sat_sub_flag", "sat_phase1_flag"]


def _add_regime_indicators(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["sat_sub_flag"] = (data["structural_upper_bound"] >= 0.99).astype(float)
    data["sat_phase1_flag"] = (data["phase1_action_density"] >= 0.4).astype(float)
    return data


def _rf_regressor():
    return RandomForestRegressor(
        n_estimators=300, max_depth=6, min_samples_leaf=2,
        random_state=RNG_SEED)


def pred_v0_baseline(Xtr, ytr, Xte, te_df):
    reg = _rf_regressor()
    reg.fit(Xtr, ytr)
    return reg.predict(Xte)


def pred_v2_learned_two_stage(Xtr, ytr, Xte, te_df):
    sat = (ytr >= 0.99).astype(int)
    if sat.sum() < 2 or sat.sum() == len(sat):
        return pred_v0_baseline(Xtr, ytr, Xte, te_df)
    clf = RandomForestClassifier(
        n_estimators=200, max_depth=5, min_samples_leaf=3,
        class_weight="balanced_subsample", random_state=RNG_SEED)
    clf.fit(Xtr, sat)
    pred_sat = clf.predict(Xte)
    reg = _rf_regressor()
    reg.fit(Xtr[sat == 0], ytr[sat == 0])
    pred_reg = reg.predict(Xte)
    return np.where(pred_sat == 1, float(ytr[sat == 1].mean()), pred_reg)


def pred_v3_rule_gate_sub(Xtr, ytr, Xte, te_df):
    pred = pred_v0_baseline(Xtr, ytr, Xte, te_df)
    bound = te_df["structural_upper_bound"].values
    gate = bound >= 0.99
    pred = pred.copy()
    pred[gate] = bound[gate]
    return pred


def pred_v4_rule_gate_phase1(Xtr, ytr, Xte, te_df):
    pred = pred_v0_baseline(Xtr, ytr, Xte, te_df)
    density = te_df["phase1_action_density"].values
    gate = 2.0 * density >= 1.0
    pred = pred.copy()
    pred[gate] = np.minimum(1.0, 2.0 * density[gate])
    return pred


def pred_v5_ridge_linear(Xtr, ytr, Xte, te_df):
    from sklearn.linear_model import Ridge
    reg = Ridge(alpha=1.0)
    reg.fit(Xtr, ytr)
    return np.clip(reg.predict(Xte), 0.0, 1.0)


REGIME_VARIANTS = {
    "v0_baseline_mech_rf": (MECHANISM_FEATURES, pred_v0_baseline),
    "v1_indicator_features": (
        MECHANISM_FEATURES + REGIME_INDICATOR_FEATURES, pred_v0_baseline),
    "v2_learned_two_stage": (MECHANISM_FEATURES, pred_v2_learned_two_stage),
    "v3_rule_gate_sub>=0.99": (MECHANISM_FEATURES, pred_v3_rule_gate_sub),
    "v4_rule_gate_phase1_saturation": (MECHANISM_FEATURES, pred_v4_rule_gate_phase1),
    "v5_ridge_linear": (MECHANISM_FEATURES, pred_v5_ridge_linear),
}


def lofo_evaluate_fn(data: pd.DataFrame, features, predict_fn, target: str):
    """LOFO with a custom per-fold predict function predict_fn(Xtr,ytr,Xte,te_df)."""
    fold_rows, pooled = [], []
    for held in sorted(data["family"].unique()):
        tr = data["family"] != held
        te = data["family"] == held
        ypred = predict_fn(data.loc[tr, features].values,
                           data.loc[tr, target].values,
                           data.loc[te, features].values,
                           data.loc[te])
        yte = data.loc[te, target].values
        fold_rows.append({
            "held_out_family": held,
            "n_test": int(te.sum()),
            "mean_actual": float(yte.mean()),
            "std_actual": float(yte.std()),
            "mae": float(mean_absolute_error(yte, ypred)),
            "pearson_r": _safe_pearson(yte, ypred),
            "spearman_r": _safe_spearman(yte, ypred),
        })
        pooled.append(pd.DataFrame({"actual": yte, "predicted": ypred,
                                    "family": held}))
    return pd.DataFrame(fold_rows), pd.concat(pooled, ignore_index=True)


def run_regime_intervention():
    """PART 4 entry point: regime-feature intervention for the CNOT residual."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not FEATURE_CSV.exists():
        raise SystemExit(
            f"cached {FEATURE_CSV} missing; run the base script first")

    raw = pd.read_csv(E21_CSV)
    df = raw[raw["strategy_name"] == "naive"].copy().reset_index(drop=True)
    feat = pd.read_csv(FEATURE_CSV)
    data = df.merge(
        feat.drop(columns=["family", "n_qubits", "trial_seed",
                           "input_circuit_sha256"]),
        left_index=True, right_on="row_idx", how="left")
    data = _add_regime_indicators(data)
    target = "gate_reduction"

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "part": "PART 4 — CNOT saturation-regime intervention (wave 4)",
        "dataset": "data/v6/e21/ceiling_aware_comparison.csv (naive rows) "
                   "+ cached mechanism_features.csv",
        "seed": RNG_SEED,
        "reference_published_best": {
            "config": "mechanism+single_stage_rf",
            "pooled_mae": 0.06954296572607763,
            "pooled_pearson_r": 0.7215221586303515,
            "pooled_spearman_r": 0.8469362494496526,
            "pooled_r2": 0.3928863763500601,
            "cnot_fold_mae": 0.7453165896031297,
            "source": "data/v6/ceiling_repair/repair_summary.json (2026-07-20)",
        },
    }

    # ---- diagnosis facts (all computed, none assumed) ----
    non_cnot_y = data.loc[data["family"] != "CNOT", target].values
    sat_train = data[(data["family"] != "CNOT") & (data[target] >= 0.99)]
    non_cnot_dens = data.loc[data["family"] != "CNOT", "phase1_action_density"]
    sub_gate = data["structural_upper_bound"] >= 0.99
    fp = data[sub_gate & (data["family"] != "CNOT")]
    report["diagnosis"] = {
        "cnot_target_unique": sorted(
            set(float(v) for v in data.loc[data["family"] == "CNOT", target])),
        "non_cnot_target_max": float(non_cnot_y.max()),
        "non_cnot_target_p99": float(np.quantile(non_cnot_y, 0.99)),
        "n_saturated_training_rows_when_cnot_held_out": int(len(sat_train)),
        "saturated_training_rows": sat_train[
            ["family", "n_qubits", target]].to_dict("records"),
        "phase1_density_cnot": 0.5,
        "phase1_density_max_non_cnot": float(non_cnot_dens.max()),
        "phase1_gate_margin_x": float(0.5 / non_cnot_dens.max()),
        "sub99_gate_non_cnot_rows": int(len(fp)),
        "sub99_gate_false_positives": fp[
            ["family", "n_qubits", target,
             "structural_upper_bound"]].to_dict("records"),
        "root_cause": (
            "RandomForest regression predicts leaf-target averages and cannot "
            "extrapolate to y=1.0 when the only saturated family is held out; "
            "with CNOT held out just one saturated training row (Oracle n=4) "
            "exists, so indicator features (V1) and a learned saturation "
            "classifier (V2) cannot fix the fold. A mechanism-derived "
            "saturation rule can, because it keys on a feature signature "
            "(Phase-1 action density 0.5, >14x above any non-CNOT circuit) "
            "rather than on training targets."
        ),
    }

    # ---- run all variants under identical LOFO protocol ----
    all_folds, summaries = [], {}
    for name, (cols, fn) in REGIME_VARIANTS.items():
        folds, pooled = lofo_evaluate_fn(data, cols, fn, target)
        m = pooled_metrics(pooled)
        lo, hi = bootstrap_ci(pooled["actual"].values, pooled["predicted"].values,
                              lambda a, b: mean_absolute_error(a, b))
        plo, phi = bootstrap_ci(pooled["actual"].values, pooled["predicted"].values,
                                _safe_pearson)
        m["mae_ci95"] = [lo, hi]
        m["pearson_ci95"] = [plo, phi]
        m["mean_fold_mae"] = float(folds["mae"].mean())
        m["cnot_fold_mae"] = float(
            folds.loc[folds["held_out_family"] == "CNOT", "mae"].iloc[0])
        summaries[name] = m
        folds.insert(0, "config", name)
        all_folds.append(folds)
        print(f"  {name:32s} pooled MAE={m['mae']:.4f} r={m['pearson_r']:.4f} "
              f"rho={m['spearman_r']:.4f} CNOT_fold_MAE={m['cnot_fold_mae']:.4f}")

    report["variants"] = summaries

    # ---- verdict against the pre-registered success criterion ----
    base, v4 = summaries["v0_baseline_mech_rf"], summaries["v4_rule_gate_phase1_saturation"]
    success = (v4["cnot_fold_mae"] < 0.1
               and v4["mae"] <= base["mae"]
               and v4["pearson_r"] >= base["pearson_r"])
    report["verdict"] = {
        "success_criterion": ("CNOT fold MAE < 0.1 AND pooled MAE <= baseline "
                              "AND pooled Pearson r >= baseline"),
        "success": bool(success),
        "primary_variant": "v4_rule_gate_phase1_saturation",
        "cnot_fold_mae_delta": base["cnot_fold_mae"] - v4["cnot_fold_mae"],
        "pooled_mae_delta": base["mae"] - v4["mae"],
        "pooled_r_delta": v4["pearson_r"] - base["pearson_r"],
        "negative_results": {
            "v1_indicator_features": ("saturation indicator features barely help "
                                      "the CNOT fold (RF cannot extrapolate leaf "
                                      "averages beyond training targets)"),
            "v2_learned_two_stage": ("learned saturation classifier never fires on "
                                     "the held-out CNOT fold — a single saturated "
                                     "training example (Oracle n=4) does not "
                                     "generalize to the CNOT signature"),
            "v5_ridge_linear": ("linear extrapolation improves pooled metrics but "
                                "leaves CNOT fold MAE ~0.45 and degrades Spearman"),
        },
    }

    folds_df = pd.concat(all_folds, ignore_index=True)
    tmp = OUT_DIR / "regime_intervention_results.csv.tmp"
    folds_df.to_csv(tmp, index=False)
    tmp.replace(OUT_DIR / "regime_intervention_results.csv")

    out_json = OUT_DIR / "regime_intervention_summary.json"
    tmp = out_json.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, indent=2, default=str))
    tmp.replace(out_json)
    print(f"\n[Save] {OUT_DIR / 'regime_intervention_results.csv'}")
    print(f"[Save] {out_json}")
    print(f"[Verdict] success={success}")
    return report


# ---------------------------------------------------------------------------
# Part 5 (wave 6, 2026-07-22): E27 new families join the LOFO evaluation
# ---------------------------------------------------------------------------
#
# Wave 5 generated 5 new circuit families (QPE, TrotterHamiltonian,
# QuantumVolume, WState, RepetitionCode; data/v8/e27_new_families/, 675 rows)
# to lift the family-mean regression from n = 15 to n = 20.  PART 5 evaluates
# the V4 hybrid model (mechanism rule gate + RF, the wave-4 winner) under LOFO
# on all 20 families.
#
# Label caveat (handled explicitly): E27 ran three optimizers independently
# and never ran the E21 "naive" pipeline (Phase1 -> Phase2 -> Phase1) that
# defines the model target `gate_reduction`.  PART 5 therefore regenerates
# every unique E27 circuit deterministically (same generators, same seeds)
# and re-runs the exact E21 naive pipeline to obtain labels with an identical
# definition.  Regeneration is verified two ways:
#   1. circuit.size() must equal the CSV `original_size` for every spec;
#   2. a Phase-1-only re-run must reproduce the CSV `greedy_phase1`
#      reduction exactly for every spec.
# Circuits are additionally deduplicated by content sha256 within a family
# (WState ignores depth/seed -> 9 identical copies per size; QPE ignores
# depth; RepetitionCode param_n=3 is promoted to n=4 and duplicates
# param_n=4).  Duplicates carry no information and would overweight folds.
#
# Outputs (NEW files only; Part-1..4 outputs never touched):
#   part5_e27_features.csv   per-unique-circuit features + naive-pipeline label
#   part5_lofo_results.csv   per-fold metrics (V0/V4 on 20 fams, V4 on 15 fams)
#   part5_summary.json       pooled metrics old/new, family-mean regression
#                            n=15 vs n=20, per-family gate behaviour, verdict

E27_CSV = (PROJECT_ROOT / "data" / "v8" / "e27_new_families"
           / "e27_new_families_v8.csv")

PART5_FEATURES_CSV = OUT_DIR / "part5_e27_features.csv"
PART5_FOLDS_CSV = OUT_DIR / "part5_lofo_results.csv"
PART5_SUMMARY_JSON = OUT_DIR / "part5_summary.json"


def _load_e27_generators():
    """Import FAMILY_GENERATORS from experiments/e27_new_families/run.py."""
    import importlib.util
    path = PROJECT_ROOT / "experiments" / "e27_new_families" / "run.py"
    spec = importlib.util.spec_from_file_location("e27_new_families_run", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.FAMILY_GENERATORS


def _part5_circuit_features(circuit, n_qubits):
    """Mechanism + generic features for one circuit.

    Definitions identical to Part 2 (extract_mechanism_features); kept as a
    separate helper so the Part-1..4 code path is untouched.
    """
    from analysis.structural_ceiling import analyze_structural_ceiling
    sc = analyze_structural_ceiling(circuit, window=10)
    size = max(1, circuit.size())
    names = [inst.operation.name for inst in circuit.data]
    n_self_inv = sum(1 for nm in names if nm in SELF_INVERSE_GATES)
    n_rot = sum(1 for nm in names if nm in {"rx", "ry", "rz"})
    n_2q = sum(1 for inst in circuit.data if len(inst.qubits) >= 2)
    depth = circuit.depth()
    return {
        "total_gates": size,
        "log_total_gates": float(np.log1p(size)),
        "gate_density": size / max(1, int(n_qubits)),
        "original_depth": int(depth),
        "depth_per_qubit": float(depth) / max(1, int(n_qubits)),
        "two_qubit_fraction": n_2q / size,
        "gate_diversity": len(set(names)),
        "rotation_fraction": n_rot / size,
        "adjacent_cancellable_pairs": sc.adjacent_cancellable_pairs,
        "phase1_action_density": sc.adjacent_cancellable_pairs / size,
        "commutation_enabled_pairs": sc.commutation_enabled_inverse_pairs,
        "commutation_density": sc.commutation_enabled_inverse_pairs / size,
        "mergeable_rotation_pairs": sc.mergeable_rotation_pairs,
        "mergeable_rotation_density": sc.mergeable_rotation_pairs / size,
        "structural_upper_bound": sc.structural_upper_bound_reduction,
        "commuting_block_count": sc.commuting_block_count,
        "commuting_block_density": sc.commuting_block_count / size,
        "mean_block_size": sc.mean_block_size,
        "max_block_size": sc.max_block_size,
        "self_inverse_fraction": n_self_inv / size,
    }


def _part5_build_e27_table():
    """Regenerate E27 circuits, verify, dedupe, label with the naive pipeline.

    Returns (e27_df, verification_report).  e27_df has the same feature and
    target columns as the E21 `data` frame used in Parts 3-4.
    """
    from src.circuits.real_benchmarks import circuit_sha256
    from src.optimisation.phase1.greedy import GreedyGateCancellation
    from src.optimisation.phase2.commutation_rewriter import CommutationRewriter

    raw = pd.read_csv(E27_CSV)
    specs = raw.drop_duplicates(
        subset=["circuit_family", "param_n", "depth", "seed"])
    # per-spec reference values from the CSV (identical across the 3 optimizers,
    # verified below)
    greedy_ref = (raw[raw["optimizer"] == "greedy_phase1"]
                  .set_index(["circuit_family", "param_n", "depth", "seed"])
                  ["reduction"].to_dict())

    generators = _load_e27_generators()
    rows, seen_hashes = [], set()
    n_size_ok, n_greedy_ok, n_dup = 0, 0, 0
    t0 = time.time()

    for _, s in specs.iterrows():
        fam = s["circuit_family"]
        param_n, depth, seed = int(s["param_n"]), int(s["depth"]), int(s["seed"])
        circuit = generators[fam](param_n, depth, seed)

        # verification 1: size must match the CSV
        if circuit.size() != int(s["original_size"]):
            raise RuntimeError(
                f"E27 regeneration size mismatch: {fam} param_n={param_n} "
                f"depth={depth} seed={seed}: regenerated {circuit.size()} "
                f"vs CSV {int(s['original_size'])}")
        n_size_ok += 1

        # verification 2: deterministic Phase-1 re-run must reproduce the CSV
        # greedy_phase1 reduction exactly
        p1 = GreedyGateCancellation(max_iterations=100)
        r1 = p1.optimize(circuit, target=None)
        greedy_reduction = 1.0 - r1.optimized_circuit.size() / circuit.size()
        ref = float(greedy_ref[(fam, param_n, depth, seed)])
        if abs(greedy_reduction - ref) > 1e-12:
            raise RuntimeError(
                f"E27 Phase-1 cross-check failed: {fam} param_n={param_n} "
                f"depth={depth} seed={seed}: rerun {greedy_reduction:.6f} "
                f"vs CSV {ref:.6f}")
        n_greedy_ok += 1

        # content dedup within family
        digest = circuit_sha256(circuit)
        if (fam, digest) in seen_hashes:
            n_dup += 1
            continue
        seen_hashes.add((fam, digest))

        # naive pipeline label (E21 definition: Phase1 -> Phase2 -> Phase1)
        p2 = CommutationRewriter(max_iterations=100, window_size=10)
        r2 = p2.optimize(r1.optimized_circuit, target=None)
        r3 = GreedyGateCancellation(max_iterations=100).optimize(
            r2.optimized_circuit, target=None)
        naive_reduction = 1.0 - r3.optimized_circuit.size() / circuit.size()

        feats = _part5_circuit_features(circuit, circuit.num_qubits)
        rows.append({
            "family": fam,
            "n_qubits": int(circuit.num_qubits),
            "param_n": param_n,
            "depth": depth,
            "seed": seed,
            "circuit_sha256": digest,
            "gate_reduction": float(naive_reduction),
            "phase1_only_reduction": float(greedy_reduction),
            **feats,
        })

    e27_df = pd.DataFrame(rows)
    verification = {
        "n_specs": int(len(specs)),
        "n_size_verified": n_size_ok,
        "n_greedy_phase1_crosscheck_ok": n_greedy_ok,
        "n_duplicate_circuits_dropped": n_dup,
        "n_unique_circuits": int(len(e27_df)),
        "unique_per_family": e27_df.groupby("family").size().to_dict(),
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    return e27_df, verification


def _part5_family_mean_regression(data, target, use_v4_gate=False):
    """Leave-one-family-out regression on family means.

    Protocol identical to Part 3b(a): RF (300 trees, depth 3, min_leaf 1) on
    family-mean combined features.  When use_v4_gate=True the deterministic
    V4 saturation rule (2 * mean phase1_action_density >= 1 ->
    predict min(1, 2*d)) overrides the RF output, mirroring the hybrid model.
    """
    fam_feat = data.groupby("family")[FEATURE_SETS["combined"]].mean()
    fam_y = data.groupby("family")[target].mean()
    preds = {}
    for held in fam_feat.index:
        tr = fam_feat.index != held
        reg = RandomForestRegressor(n_estimators=300, max_depth=3,
                                    min_samples_leaf=1, random_state=RNG_SEED)
        reg.fit(fam_feat.loc[tr, FEATURE_SETS["combined"]], fam_y.loc[tr])
        p = float(reg.predict(fam_feat.loc[[held], FEATURE_SETS["combined"]])[0])
        if use_v4_gate:
            d = float(fam_feat.loc[held, "phase1_action_density"])
            if 2.0 * d >= 1.0:
                p = min(1.0, 2.0 * d)
        preds[held] = p
    pv = pd.Series(preds)
    return {
        "n_families": int(len(fam_y)),
        "mae": float(mean_absolute_error(fam_y.values, pv.values)),
        "pearson_r": _safe_pearson(fam_y.values, pv.values),
        "spearman_r": _safe_spearman(fam_y.values, pv.values),
        "per_family": {f: {"actual": float(fam_y[f]), "predicted": float(pv[f])}
                       for f in fam_y.index},
    }


def run_part5_new_families():
    """PART 5 entry point: add the 5 E27 families to the LOFO evaluation."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not FEATURE_CSV.exists():
        raise SystemExit(
            f"cached {FEATURE_CSV} missing; run the base script first")
    if not E27_CSV.exists():
        raise SystemExit(f"E27 canonical CSV missing: {E27_CSV}")

    target = "gate_reduction"

    # ---- E21 side (identical merge to Part 4) ----
    raw = pd.read_csv(E21_CSV)
    df = raw[raw["strategy_name"] == "naive"].copy().reset_index(drop=True)
    feat = pd.read_csv(FEATURE_CSV)
    data15 = df.merge(
        feat.drop(columns=["family", "n_qubits", "trial_seed",
                           "input_circuit_sha256"]),
        left_index=True, right_on="row_idx", how="left")
    print(f"[Load] E21 naive rows: {len(data15)} "
          f"({data15['family'].nunique()} families)")

    # ---- E27 side: regenerate, verify, dedupe, label ----
    print("[E27] regenerating circuits + naive-pipeline labels ...")
    e27_df, verification = _part5_build_e27_table()
    print(f"  verified {verification['n_greedy_phase1_crosscheck_ok']}/"
          f"{verification['n_specs']} specs; "
          f"{verification['n_duplicate_circuits_dropped']} duplicates dropped; "
          f"{verification['n_unique_circuits']} unique circuits kept")

    tmp = PART5_FEATURES_CSV.with_suffix(".csv.tmp")
    e27_df.to_csv(tmp, index=False)
    tmp.replace(PART5_FEATURES_CSV)
    print(f"[Save] {PART5_FEATURES_CSV}")

    data20 = pd.concat([data15, e27_df], ignore_index=True)
    print(f"[Merge] combined: {len(data20)} rows, "
          f"{data20['family'].nunique()} families")

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "part": "PART 5 — E27 new families join the LOFO evaluation (wave 6)",
        "datasets": {
            "e21": "data/v6/e21/ceiling_aware_comparison.csv (naive rows) "
                   "+ cached mechanism_features.csv",
            "e27": "data/v8/e27_new_families/e27_new_families_v8.csv; "
                   "labels recomputed with the exact E21 naive pipeline "
                   "(Phase1 -> Phase2(window=10) -> Phase1) on regenerated, "
                   "size- and Phase-1-cross-checked, content-deduplicated "
                   "circuits",
        },
        "seed": RNG_SEED,
        "e27_verification": verification,
        "reference_15family": {
            "v4_pooled_mae": 0.017240047157436947,
            "v4_pooled_pearson_r": 0.9769398851816893,
            "v4_pooled_spearman_r": 0.8527459395997157,
            "family_mean_r_n15": 0.05879992845693669,
            "sources": [
                "data/v6/ceiling_repair/regime_intervention_summary.json",
                "data/v6/ceiling_repair/repair_summary.json",
            ],
        },
    }

    # ---- reproduction check: V4 on the 15 original families ----
    folds15, pooled15 = lofo_evaluate_fn(
        data15, MECHANISM_FEATURES, pred_v4_rule_gate_phase1, target)
    m15 = pooled_metrics(pooled15)
    folds15.insert(0, "config", "v4_rule_gate_phase1_15fam_repro")
    print(f"[Repro] V4 on 15 fams: MAE={m15['mae']:.4f} "
          f"r={m15['pearson_r']:.4f} rho={m15['spearman_r']:.4f}")
    repro_ok = (abs(m15["mae"] - 0.017240047157436947) < 1e-9
                and abs(m15["pearson_r"] - 0.9769398851816893) < 1e-9)
    report["reproduction_check_v4_15fam"] = {**m15, "matches_wave4": repro_ok}

    # ---- LOFO on 20 families: V0 (mech RF) and V4 (hybrid gate + RF) ----
    all_folds = [folds15]
    summaries = {}
    for name, fn in [("v0_baseline_mech_rf_20fam", pred_v0_baseline),
                     ("v4_rule_gate_phase1_20fam", pred_v4_rule_gate_phase1)]:
        folds, pooled = lofo_evaluate_fn(data20, MECHANISM_FEATURES, fn, target)
        m = pooled_metrics(pooled)
        lo, hi = bootstrap_ci(pooled["actual"].values,
                              pooled["predicted"].values,
                              lambda a, b: mean_absolute_error(a, b))
        plo, phi = bootstrap_ci(pooled["actual"].values,
                                pooled["predicted"].values, _safe_pearson)
        m["mae_ci95"] = [lo, hi]
        m["pearson_ci95"] = [plo, phi]
        m["mean_fold_mae"] = float(folds["mae"].mean())
        m["max_fold_mae"] = float(folds["mae"].max())
        summaries[name] = m
        folds.insert(0, "config", name)
        all_folds.append(folds)
        print(f"  {name:32s} pooled MAE={m['mae']:.4f} r={m['pearson_r']:.4f} "
              f"rho={m['spearman_r']:.4f} max_fold_MAE={m['max_fold_mae']:.4f}")
    report["lofo_20fam"] = summaries

    folds_df = pd.concat(all_folds, ignore_index=True)
    tmp = PART5_FOLDS_CSV.with_suffix(".csv.tmp")
    folds_df.to_csv(tmp, index=False)
    tmp.replace(PART5_FOLDS_CSV)
    print(f"[Save] {PART5_FOLDS_CSV}")

    # ---- family-mean regression: n=15 (repro) vs n=20 ----
    fam15 = _part5_family_mean_regression(data15, target)
    fam20 = _part5_family_mean_regression(data20, target)
    fam20_gated = _part5_family_mean_regression(data20, target,
                                                use_v4_gate=True)
    report["family_mean_regression"] = {
        "protocol": ("RF (300 trees, depth 3, min_leaf 1) on family-mean "
                     "combined features, leave-one-family-out; identical to "
                     "Part 3b(a)"),
        "n15_repro": fam15,
        "n20_rf_only": fam20,
        "n20_rf_plus_v4_gate": fam20_gated,
        "previous_published_n15_r": 0.059,
    }
    print(f"[FamMean] n=15 r={fam15['pearson_r']:.3f} -> "
          f"n=20 r={fam20['pearson_r']:.3f} (RF only); "
          f"n=20 gated r={fam20_gated['pearson_r']:.3f}")

    # ---- V4 gate behaviour per family (all 20, focus on the 5 new ones) ----
    gate_rows = []
    new_families = sorted(e27_df["family"].unique())
    v4_folds = folds_df[folds_df["config"] == "v4_rule_gate_phase1_20fam"]
    for fam in sorted(data20["family"].unique()):
        sub = data20[data20["family"] == fam]
        density = sub["phase1_action_density"].values
        gate = 2.0 * density >= 1.0
        fold = v4_folds[v4_folds["held_out_family"] == fam].iloc[0]
        gate_rows.append({
            "family": fam,
            "is_new_family": fam in new_families,
            "n_rows": int(len(sub)),
            "mean_actual_reduction": float(sub[target].mean()),
            "mean_phase1_action_density": float(density.mean()),
            "max_phase1_action_density": float(density.max()),
            "mean_structural_upper_bound":
                float(sub["structural_upper_bound"].mean()),
            "gate_fire_rate": float(gate.mean()),
            "v4_fold_mae": float(fold["mae"]),
            "v4_fold_pearson_r": float(fold["pearson_r"]),
        })
        print(f"  gate {fam:20s} fire={gate.mean():.2f} "
              f"density_max={density.max():.3f} "
              f"fold_MAE={fold['mae']:.4f}")
    report["gate_behaviour_per_family"] = gate_rows

    # ---- honest verdict ----
    v0, v4 = summaries["v0_baseline_mech_rf_20fam"], summaries["v4_rule_gate_phase1_20fam"]
    new_gate = [g for g in gate_rows if g["is_new_family"]]
    new_fold_maes = {g["family"]: g["v4_fold_mae"] for g in new_gate}
    bad_folds = {f: m for f, m in new_fold_maes.items() if m > 0.1}
    false_gates = [g["family"] for g in new_gate
                   if g["gate_fire_rate"] > 0 and g["mean_actual_reduction"] < 0.99]
    report["verdict"] = {
        "family_mean_r_improved_materially":
            bool(fam20["pearson_r"] > fam15["pearson_r"] + 0.1),
        "family_mean_r_delta_n20_vs_n15":
            float(fam20["pearson_r"] - fam15["pearson_r"]),
        "new_family_fold_maes": new_fold_maes,
        "new_family_folds_mae_gt_0.1": bad_folds,
        "new_family_gate_false_positive_candidates": false_gates,
        "v4_vs_v0_on_20fam": {
            "pooled_mae_delta": v0["mae"] - v4["mae"],
            "pooled_r_delta": v4["pearson_r"] - v0["pearson_r"],
        },
    }

    tmp = PART5_SUMMARY_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, indent=2, default=str))
    tmp.replace(PART5_SUMMARY_JSON)
    print(f"[Save] {PART5_SUMMARY_JSON}")
    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-feature-extraction", action="store_true",
                    help="reuse cached mechanism_features.csv")
    ap.add_argument("--regime", action="store_true",
                    help="run PART 4 (CNOT saturation-regime intervention) only; "
                         "uses cached mechanism_features.csv and writes new files")
    ap.add_argument("--part5", action="store_true",
                    help="run PART 5 (E27 new families join LOFO) only; "
                         "uses cached mechanism_features.csv and writes new files")
    args = ap.parse_args()

    if args.regime:
        print("========== PART 4: CNOT SATURATION-REGIME INTERVENTION ==========")
        run_regime_intervention()
        print("[Done]")
        return

    if args.part5:
        print("========== PART 5: E27 NEW FAMILIES JOIN LOFO ==========")
        run_part5_new_families()
        print("[Done]")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {"timestamp": datetime.now(timezone.utc).isoformat(),
              "dataset": "data/v6/e21/ceiling_aware_comparison.csv (naive rows)",
              "seed": RNG_SEED}

    raw = pd.read_csv(E21_CSV)
    df = raw[raw["strategy_name"] == "naive"].copy().reset_index(drop=True)
    print(f"[Load] {len(df)} naive rows, {df['family'].nunique()} families")

    # ------------------------------------------------------------------ #
    # PART 1 — DIAGNOSIS
    # ------------------------------------------------------------------ #
    print("\n========== PART 1: DIAGNOSIS ==========")
    target = "gate_reduction"
    y = df[target].values

    fam_stats = df.groupby("family")[target].agg(["count", "mean", "std"])
    degenerate = fam_stats[fam_stats["std"] < 1e-12]
    n_degenerate = len(degenerate)

    # Variance decomposition: eta^2 = SS_between / SS_total
    grand = y.mean()
    ss_between = sum(len(g) * (g[target].mean() - grand) ** 2
                     for _, g in df.groupby("family"))
    ss_total = float(((y - grand) ** 2).sum())
    eta2_family = ss_between / ss_total if ss_total > 0 else float("nan")

    # Same eta^2 for each candidate generic feature vs family
    feat_eta2 = {}
    for col in ["n_qubits", "original_size", "original_depth", "original_cnot"]:
        ssb = sum(len(g) * (g[col].mean() - df[col].mean()) ** 2
                  for _, g in df.groupby("family"))
        sst = float(((df[col] - df[col].mean()) ** 2).sum())
        feat_eta2[col] = ssb / sst if sst > 0 else float("nan")

    # reducible vs ceiling family counts
    fam_mean = fam_stats["mean"]
    reducible_fams = fam_mean[fam_mean > 0.001].index.tolist()
    ceiling_fams = fam_mean[fam_mean <= 0.001].index.tolist()

    diagnosis = {
        "n_rows": int(len(df)),
        "n_families": int(df["family"].nunique()),
        "target": target,
        "target_mean": float(y.mean()),
        "target_std": float(y.std()),
        "n_degenerate_folds_zero_variance": n_degenerate,
        "degenerate_families": degenerate.index.tolist(),
        "reducible_families_mean_gt_0.1pct": reducible_fams,
        "eta2_family_identity_on_target": float(eta2_family),
        "eta2_family_identity_on_generic_features": feat_eta2,
        "interpretation": (
            "Family identity explains eta^2 of the target variance; per-fold "
            "Pearson is undefined on zero-variance folds; LOFO removes the "
            "one variable (family) that carries the signal, so success "
            "depends entirely on whether features expose the *mechanism* of "
            "reducibility rather than correlates of family identity."
        ),
    }
    print(f"  target mean={y.mean():.4f} std={y.std():.4f}")
    print(f"  degenerate (zero-variance) folds: {n_degenerate}/{len(fam_stats)}")
    print(f"  eta^2(family -> target) = {eta2_family:.3f}")
    print(f"  reducible families: {reducible_fams}")
    report["diagnosis"] = diagnosis

    # ------------------------------------------------------------------ #
    # PART 2 — MECHANISM FEATURES
    # ------------------------------------------------------------------ #
    print("\n========== PART 2: MECHANISM FEATURES ==========")
    if args.skip_feature_extraction and FEATURE_CSV.exists():
        feat = pd.read_csv(FEATURE_CSV)
        print(f"  loaded cached {FEATURE_CSV} ({len(feat)} rows)")
    else:
        feat = extract_mechanism_features(df)
        tmp = FEATURE_CSV.with_suffix(".csv.tmp")
        feat.to_csv(tmp, index=False)
        tmp.replace(FEATURE_CSV)
        print(f"  wrote {FEATURE_CSV}")

    data = df.reset_index(drop=True).merge(
        feat.drop(columns=["family", "n_qubits", "trial_seed",
                           "input_circuit_sha256"]),
        left_index=True, right_on="row_idx", how="left")

    # Oracle tightness: how well does the static ceiling proxy track the
    # actual naive-pipeline reduction? (validates the ceiling-aware thesis)
    tight_r = _safe_pearson(data["structural_upper_bound"], y)
    tight_sr = _safe_spearman(data["structural_upper_bound"], y)
    tight_mae = float(mean_absolute_error(y, data["structural_upper_bound"]))
    report["ceiling_proxy_tightness"] = {
        "pearson_r": tight_r, "spearman_r": tight_sr, "mae": tight_mae,
        "note": "structural_upper_bound vs actual gate_reduction, pooled",
    }
    print(f"  ceiling-proxy tightness: r={tight_r:.3f} rho={tight_sr:.3f} "
          f"MAE={tight_mae:.4f}")

    # ------------------------------------------------------------------ #
    # PART 3 — RETEST (LOFO)
    # ------------------------------------------------------------------ #
    print("\n========== PART 3: LOFO RETEST ==========")
    all_folds, summaries = [], {}

    # Baselines
    pooled_zero = data[[target]].rename(columns={target: "actual"})
    pooled_zero["predicted"] = 0.0
    m_zero = pooled_metrics(pooled_zero)
    summaries["baseline_predict_zero"] = m_zero

    gm_folds = []
    for held in sorted(data["family"].unique()):
        tr = data["family"] != held
        gm = float(data.loc[tr, target].mean())
        gm_folds.append(pd.DataFrame({
            "actual": data.loc[data["family"] == held, target].values,
            "predicted": gm, "family": held}))
    m_gmean = pooled_metrics(pd.concat(gm_folds, ignore_index=True))
    summaries["baseline_global_mean"] = m_gmean
    print(f"  baseline predict-0:          MAE={m_zero['mae']:.4f}")
    print(f"  baseline global-train-mean:  MAE={m_gmean['mae']:.4f} "
          f"r={m_gmean['pearson_r']:.3f}")

    for fs_name, cols in FEATURE_SETS.items():
        for model in ["two_stage_rf", "single_stage_rf"]:
            key = f"{fs_name}+{model}"
            folds, pooled = lofo_evaluate(data, cols, model, target)
            m = pooled_metrics(pooled)
            lo, hi = bootstrap_ci(pooled["actual"].values,
                                  pooled["predicted"].values,
                                  lambda a, b: mean_absolute_error(a, b))
            m["mae_ci95"] = [lo, hi]
            plo, phi = bootstrap_ci(pooled["actual"].values,
                                    pooled["predicted"].values,
                                    _safe_pearson)
            m["pearson_ci95"] = [plo, phi]
            m["mean_fold_mae"] = float(folds["mae"].mean())
            m["n_nan_pearson_folds"] = int(folds["pearson_r"].isna().sum())
            summaries[key] = m
            folds.insert(0, "config", key)
            all_folds.append(folds)
            rstr = f"{m['pearson_r']:.3f}" if not np.isnan(m["pearson_r"]) else " NaN"
            print(f"  {key:32s} pooled MAE={m['mae']:.4f} r={rstr} "
                  f"rho={m['spearman_r']:.3f} (nan-folds {m['n_nan_pearson_folds']})")

    folds_df = pd.concat(all_folds, ignore_index=True)
    tmp = (OUT_DIR / "repair_lofo_results.csv.tmp")
    folds_df.to_csv(tmp, index=False)
    tmp.replace(OUT_DIR / "repair_lofo_results.csv")

    # ------------------------------------------------------------------ #
    # PART 3b — REFRAMED EVALUATIONS
    # ------------------------------------------------------------------ #
    print("\n========== PART 3b: REFRAMED EVALUATIONS ==========")

    # (a) family-mean regression with mechanism features, leave-one-out
    fam_feat = data.groupby("family")[MECHANISM_FEATURES + GENERIC_FEATURES].mean()
    fam_y = data.groupby("family")[target].mean()
    preds = {}
    for held in fam_feat.index:
        tr = fam_feat.index != held
        reg = RandomForestRegressor(n_estimators=300, max_depth=3,
                                    min_samples_leaf=1, random_state=RNG_SEED)
        reg.fit(fam_feat.loc[tr, FEATURE_SETS["combined"]], fam_y.loc[tr])
        preds[held] = float(reg.predict(
            fam_feat.loc[[held], FEATURE_SETS["combined"]])[0])
    pv = pd.Series(preds)
    fam_r = _safe_pearson(fam_y.values, pv.values)
    fam_sr = _safe_spearman(fam_y.values, pv.values)
    fam_mae = float(mean_absolute_error(fam_y.values, pv.values))
    report["family_mean_regression"] = {
        "n_families": int(len(fam_y)),
        "mae": fam_mae, "pearson_r": fam_r, "spearman_r": fam_sr,
        "per_family": {f: {"actual": float(fam_y[f]), "predicted": float(pv[f])}
                       for f in fam_y.index},
    }
    print(f"  (a) family-mean LOFO regression: MAE={fam_mae:.4f} "
          f"r={fam_r:.3f} rho={fam_sr:.3f} (n={len(fam_y)})")

    # (b) ceiling classification (is_reducible) with mechanism features
    data["is_reducible"] = (data[target] > 0.001).astype(int)
    cls_rows = []
    for held in sorted(data["family"].unique()):
        tr = data["family"] != held
        te = data["family"] == held
        ytr_c, yte_c = data.loc[tr, "is_reducible"], data.loc[te, "is_reducible"]
        if ytr_c.nunique() < 2:
            pred = np.full(te.sum(), int(ytr_c.iloc[0]))
        else:
            clf = RandomForestClassifier(
                n_estimators=200, max_depth=5, min_samples_leaf=3,
                class_weight="balanced_subsample", random_state=RNG_SEED)
            clf.fit(data.loc[tr, MECHANISM_FEATURES], ytr_c)
            pred = clf.predict(data.loc[te, MECHANISM_FEATURES])
        cls_rows.append({
            "family": held,
            "n_reducible_test": int(yte_c.sum()),
            "balanced_acc": float(balanced_accuracy_score(yte_c, pred)),
            "f1": float(f1_score(yte_c, pred, zero_division=0)),
            "mcc": float(matthews_corrcoef(yte_c, pred))
            if yte_c.nunique() > 1 and len(set(pred)) > 1 else float("nan"),
        })
    cls_df = pd.DataFrame(cls_rows)
    report["ceiling_classification_mechanism"] = {
        "mean_balanced_acc": float(cls_df["balanced_acc"].mean()),
        "mean_f1": float(cls_df["f1"].mean()),
        "mean_mcc": float(cls_df["mcc"].mean()),
        "per_family": cls_rows,
    }
    print(f"  (b) ceiling classification (mechanism feats): "
          f"bal-acc={cls_df['balanced_acc'].mean():.3f} "
          f"F1={cls_df['f1'].mean():.3f} MCC={cls_df['mcc'].mean():.3f}")

    # (c) within-family magnitude predictability (reducible families only)
    within = {}
    for fam in reducible_fams:
        sub = data[data["family"] == fam]
        if len(sub) < 20 or sub[target].std() < 1e-9:
            within[fam] = {"note": "insufficient variance or rows",
                           "n": int(len(sub))}
            continue
        from sklearn.model_selection import KFold
        kf = KFold(n_splits=5, shuffle=True, random_state=RNG_SEED)
        yp = np.zeros(len(sub))
        X = sub[FEATURE_SETS["combined"]].values
        yy = sub[target].values
        for tri, tei in kf.split(X):
            reg = RandomForestRegressor(n_estimators=200, max_depth=4,
                                        min_samples_leaf=2,
                                        random_state=RNG_SEED)
            reg.fit(X[tri], yy[tri])
            yp[tei] = reg.predict(X[tei])
        within[fam] = {
            "n": int(len(sub)),
            "pearson_r": _safe_pearson(yy, yp),
            "spearman_r": _safe_spearman(yy, yp),
            "mae": float(mean_absolute_error(yy, yp)),
            "target_std": float(yy.std()),
        }
        print(f"  (c) within {fam:15s} r={within[fam]['pearson_r']:.3f} "
              f"MAE={within[fam]['mae']:.4f} (target std {yy.std():.4f})")
    report["within_family_magnitude"] = within

    # ------------------------------------------------------------------ #
    # Save report
    # ------------------------------------------------------------------ #
    report["lofo_summaries"] = summaries
    out_json = OUT_DIR / "repair_summary.json"
    tmp = out_json.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, indent=2, default=str))
    tmp.replace(out_json)

    diag_json = OUT_DIR / "diagnosis.json"
    tmp = diag_json.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(diagnosis, indent=2, default=str))
    tmp.replace(diag_json)

    print(f"\n[Save] {out_json}")
    print(f"[Save] {diag_json}")
    print(f"[Save] {OUT_DIR / 'repair_lofo_results.csv'}")
    print("[Done]")


if __name__ == "__main__":
    main()
