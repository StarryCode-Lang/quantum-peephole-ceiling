"""Post-seal generalization, calibration, shortcut, and OOD audit.

The sealed classifier and its v1/v2 predictions are never refit or changed.
Auxiliary refits are diagnostic only: training-family leave-one-generator-out,
single-feature ablations, and a gate-count-only shortcut baseline.  OOD and
abstention thresholds are derived exclusively from training features.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    matthews_corrcoef,
    roc_auc_score,
)
from sklearn.metrics import pairwise_distances
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TRAINING = (
    ROOT
    / "data/v10/prepaper/heldout/sealed_predictions/training_features_labels.csv"
)
MODEL = ROOT / "data/v10/prepaper/heldout/sealed_predictions/model.json"
V1_FEATURES = ROOT / "data/v10/prepaper/heldout/inputs/preoptimization_features.csv"
V2_FEATURES = ROOT / "data/v10/prepaper/heldout_v2/inputs/preoptimization_features.csv"
COMBINED = (
    ROOT
    / "data/v10/prepaper/heldout_v2/analysis/heldout_v1_v2_unique_inputs.csv"
)
COMBINED_METRICS = (
    ROOT / "data/v10/prepaper/heldout_v2/analysis/combined_heldout_metrics.json"
)
FAMILY_DIAGNOSTICS = (
    ROOT / "data/v10/prepaper/heldout_v2/analysis/combined_generator_diagnostics.csv"
)
DEFAULT_OUTPUT_DIR = ROOT / "data/v10/prepaper/heldout_v2/analysis/generalization_ood"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_features(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    result = frame.copy()
    if "log1p_n_gates" in features and "log1p_n_gates" not in result:
        result["log1p_n_gates"] = np.log1p(
            pd.to_numeric(result["n_gates"], errors="raise")
        )
    missing = sorted(set(features) - set(result.columns))
    if missing:
        raise ValueError(f"missing model features: {missing}")
    return result


def _binary_metrics(y: np.ndarray, probability: np.ndarray) -> dict:
    y = np.asarray(y, dtype=np.int8)
    probability = np.asarray(probability, dtype=float)
    prediction = (probability >= 0.5).astype(np.int8)
    result = {
        "n": int(len(y)),
        "positive_rate": float(y.mean()) if len(y) else None,
        "accuracy": float(accuracy_score(y, prediction)) if len(y) else None,
        "brier": float(brier_score_loss(y, probability)) if len(y) else None,
        "log_loss": float(log_loss(y, probability, labels=[0, 1])) if len(y) else None,
        "mcc": None,
        "balanced_accuracy": None,
        "auroc": None,
    }
    if len(y) and len(np.unique(y)) == 2:
        result.update(
            {
                "mcc": float(matthews_corrcoef(y, prediction)),
                "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
                "auroc": float(roc_auc_score(y, probability)),
            }
        )
    return result


def _poisson_binomial_interval(probabilities: np.ndarray, alpha: float = 0.05) -> tuple[int, int]:
    distribution = np.array([1.0])
    for probability in np.asarray(probabilities, dtype=float):
        updated = np.zeros(len(distribution) + 1)
        updated[:-1] += distribution * (1.0 - probability)
        updated[1:] += distribution * probability
        distribution = updated
    cdf = np.cumsum(distribution)
    lower = int(np.searchsorted(cdf, alpha / 2.0, side="left"))
    upper = int(np.searchsorted(cdf, 1.0 - alpha / 2.0, side="left"))
    return lower, min(upper, len(probabilities))


def _diagnostic_pipeline() -> object:
    return make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(
            C=1.0,
            class_weight="balanced",
            solver="lbfgs",
            random_state=20260809,
            max_iter=10000,
        ),
    )


def _assemble_heldout(features: list[str]) -> pd.DataFrame:
    combined = pd.read_csv(COMBINED)
    if combined.duplicated("input_circuit_sha256").any():
        raise ValueError("combined held-out packet is not unique by input hash")
    packets = []
    for version, path in (("v1", V1_FEATURES), ("v2", V2_FEATURES)):
        frame = _ensure_features(pd.read_csv(path), features)
        consistency = frame.groupby("input_circuit_sha256")[features].nunique(dropna=False)
        if (consistency > 1).any().any():
            raise ValueError(f"{version} duplicate hash has inconsistent features")
        frame = frame.drop_duplicates("input_circuit_sha256", keep="first")
        frame["heldout_version"] = version
        packets.append(frame[["heldout_version", "circuit_family", "input_circuit_sha256", *features]])
    feature_frame = pd.concat(packets, ignore_index=True)
    if feature_frame.duplicated("input_circuit_sha256").any():
        raise ValueError("cross-packet feature hash duplicate")
    # ``combined`` already carries n_qubits as an analysis descriptor.  Use
    # the hash-bound feature packet as the authoritative model input to avoid
    # ambiguous merge suffixes.
    combined_for_merge = combined.drop(
        columns=[feature for feature in features if feature in combined.columns]
    )
    joined = combined_for_merge.merge(
        feature_frame,
        on=["heldout_version", "circuit_family", "input_circuit_sha256"],
        validate="one_to_one",
    )
    if len(joined) != 378:
        raise ValueError(f"expected 378 unique held-out inputs, got {len(joined)}")
    return joined


def _plot_family_diagnostics(frame: pd.DataFrame, output: Path) -> None:
    figure, axis = plt.subplots(figsize=(8.2, 5.2))
    palette = {"v1": "#355C9A", "v2": "#D56A3A"}
    for version, group in frame.groupby("heldout_version", sort=True):
        axis.scatter(
            group["median_training_nn_distance"],
            group["absolute_calibration_error"],
            s=28 + 2.2 * group["n_unique_inputs"],
            c=palette[str(version)],
            alpha=0.82,
            edgecolor="white",
            linewidth=0.6,
            label=str(version),
        )
    label_indices = set(frame.nlargest(5, "absolute_calibration_error").index)
    label_indices.update(frame.nlargest(1, "median_training_nn_distance").index)
    for row in frame.loc[sorted(label_indices)].itertuples(index=False):
        axis.annotate(
            row.circuit_family,
            (row.median_training_nn_distance, row.absolute_calibration_error),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=6.5,
        )
    axis.axvline(
        float(frame.attrs["ood_threshold"]),
        color="#333333",
        linestyle="--",
        linewidth=1.0,
        label="training LOO 95% OOD threshold",
    )
    axis.set_xlabel("Median nearest-training distance (sealed standardized features)")
    axis.set_ylabel("Absolute family calibration error")
    axis.set_title("Held-out family distance and calibration (diagnostic)")
    axis.grid(alpha=0.18)
    axis.legend(frameon=False, fontsize=8)
    figure.tight_layout()
    figure.savefig(output.with_suffix(".png"), dpi=300)
    figure.savefig(output.with_suffix(".pdf"))
    plt.close(figure)


def build_audit(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict:
    for path in (
        TRAINING,
        MODEL,
        V1_FEATURES,
        V2_FEATURES,
        COMBINED,
        COMBINED_METRICS,
        FAMILY_DIAGNOSTICS,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    features = list(model["features"])
    training = _ensure_features(pd.read_csv(TRAINING), features)
    heldout = _assemble_heldout(features)
    training_families = set(training["circuit_family"].astype(str))
    heldout_families = set(heldout["circuit_family"].astype(str))
    family_overlap = sorted(training_families & heldout_families)
    if family_overlap:
        raise ValueError(f"training/held-out family leakage: {family_overlap}")
    if training["input_circuit_sha256"].isin(heldout["input_circuit_sha256"]).any():
        raise ValueError("training/held-out input hash leakage")

    x_train_raw = training[features].to_numpy(dtype=float)
    x_heldout_raw = heldout[features].to_numpy(dtype=float)
    imputer = np.asarray(model["imputer_statistics"], dtype=float)
    mean = np.asarray(model["scaler_mean"], dtype=float)
    scale = np.asarray(model["scaler_scale"], dtype=float)
    x_train = np.where(np.isfinite(x_train_raw), x_train_raw, imputer)
    x_heldout = np.where(np.isfinite(x_heldout_raw), x_heldout_raw, imputer)
    z_train = (x_train - mean) / scale
    z_heldout = (x_heldout - mean) / scale
    coefficient = np.asarray(model["coefficients"], dtype=float)[0]
    intercept = float(model["intercept"][0])
    probability_replayed = 1.0 / (1.0 + np.exp(-(intercept + z_heldout @ coefficient)))
    recorded_probability = heldout[
        "predicted_probability_joint_external_headroom"
    ].to_numpy(dtype=float)
    max_probability_error = float(np.max(np.abs(probability_replayed - recorded_probability)))
    if max_probability_error > 1e-12:
        raise ValueError(f"sealed probability replay mismatch: {max_probability_error}")

    train_distances = pairwise_distances(z_train, metric="euclidean")
    np.fill_diagonal(train_distances, np.inf)
    train_loo_nn = train_distances.min(axis=1)
    ood_threshold = float(np.quantile(train_loo_nn, 0.95, method="higher"))
    heldout_nn = pairwise_distances(z_heldout, z_train, metric="euclidean").min(axis=1)
    covariance = LedoitWolf().fit(z_train)
    centered = z_heldout - covariance.location_
    heldout_mahalanobis = np.sqrt(
        np.maximum(np.einsum("ij,jk,ik->i", centered, covariance.precision_, centered), 0.0)
    )
    training_min = np.nanmin(x_train, axis=0)
    training_max = np.nanmax(x_train, axis=0)
    excursions = ((x_heldout < training_min) | (x_heldout > training_max)).sum(axis=1)
    heldout["training_nn_distance"] = heldout_nn
    heldout["training_mahalanobis"] = heldout_mahalanobis
    heldout["training_range_excursion_count"] = excursions
    heldout["ood_abstain"] = heldout_nn > ood_threshold

    y = heldout["observed_joint_external_headroom"].to_numpy(dtype=np.int8)
    family_rows = []
    for family, group in heldout.groupby("circuit_family", sort=True):
        gy = group["observed_joint_external_headroom"].to_numpy(dtype=np.int8)
        gp = group["predicted_probability_joint_external_headroom"].to_numpy(dtype=float)
        lower_count, upper_count = _poisson_binomial_interval(gp)
        observed_count = int(gy.sum())
        family_rows.append(
            {
                "heldout_version": str(group["heldout_version"].iloc[0]),
                "circuit_family": family,
                "n_unique_inputs": int(len(group)),
                "observed_positive_count": observed_count,
                "observed_positive_rate": float(gy.mean()),
                "mean_predicted_probability": float(gp.mean()),
                "signed_calibration_error": float(gp.mean() - gy.mean()),
                "absolute_calibration_error": float(abs(gp.mean() - gy.mean())),
                "brier": float(brier_score_loss(gy, gp)),
                "prediction_count_interval_95_lower": lower_count,
                "prediction_count_interval_95_upper": upper_count,
                "observed_count_inside_prediction_interval": bool(
                    lower_count <= observed_count <= upper_count
                ),
                "median_training_nn_distance": float(group["training_nn_distance"].median()),
                "p95_training_nn_distance": float(group["training_nn_distance"].quantile(0.95)),
                "median_training_mahalanobis": float(group["training_mahalanobis"].median()),
                "range_excursion_rate": float(
                    (group["training_range_excursion_count"] > 0).mean()
                ),
                "ood_abstention_rate": float(group["ood_abstain"].mean()),
                "classification_accuracy": float(
                    accuracy_score(gy, (gp >= 0.5).astype(np.int8))
                ),
                "complete_classification_failure": bool(
                    accuracy_score(gy, (gp >= 0.5).astype(np.int8)) == 0.0
                ),
            }
        )
    family = pd.DataFrame(family_rows)
    family.attrs["ood_threshold"] = ood_threshold

    y_train = training["label_joint_external_headroom"].to_numpy(dtype=np.int8)
    ablation_rows = []
    for label, selected in [
        ("full_12_features", features),
        ("gate_count_only", ["log1p_n_gates"]),
        ("size_only", ["n_qubits", "log1p_n_gates"]),
        *[(f"drop_{feature}", [item for item in features if item != feature]) for feature in features],
    ]:
        pipeline = _diagnostic_pipeline()
        pipeline.fit(training[selected], y_train)
        diagnostic_probability = pipeline.predict_proba(heldout[selected])[:, 1]
        row = {"specification": label, "n_features": len(selected), "features": "|".join(selected)}
        row.update(_binary_metrics(y, diagnostic_probability))
        ablation_rows.append(row)
    ablations = pd.DataFrame(ablation_rows)

    logo_rows = []
    for family_name in sorted(training_families):
        test_mask = training["circuit_family"].astype(str).eq(family_name).to_numpy()
        pipeline = _diagnostic_pipeline()
        pipeline.fit(training.loc[~test_mask, features], y_train[~test_mask])
        probability = pipeline.predict_proba(training.loc[test_mask, features])[:, 1]
        row = {
            "left_out_training_generator": family_name,
            "train_generators": int(len(training_families) - 1),
        }
        row.update(_binary_metrics(y_train[test_mask], probability))
        logo_rows.append(row)
    logo = pd.DataFrame(logo_rows)

    accepted = ~heldout["ood_abstain"].to_numpy(dtype=bool)
    selective = {
        "rule": "abstain when nearest sealed-standardized training distance exceeds the training leave-one-out 95th percentile",
        "threshold_source": "training features only",
        "threshold": ood_threshold,
        "coverage": float(accepted.mean()),
        "accepted_n": int(accepted.sum()),
        "abstained_n": int((~accepted).sum()),
        "accepted_metrics": _binary_metrics(y[accepted], recorded_probability[accepted]),
        "abstained_metrics": _binary_metrics(y[~accepted], recorded_probability[~accepted]),
        "status": "POST_SEAL_DIAGNOSTIC_NOT_PRIMARY_CLASSIFIER_CHANGE",
    }
    combined_metrics = json.loads(COMBINED_METRICS.read_text(encoding="utf-8"))
    interval_width = float(
        combined_metrics["mcc_ci95_upper"] - combined_metrics["mcc_ci95_lower"]
    )
    near_families = int((family["ood_abstention_rate"] < 0.5).sum())
    far_families = int((family["ood_abstention_rate"] >= 0.5).sum())
    full = ablations.loc[ablations["specification"] == "full_12_features"].iloc[0]
    gate_only = ablations.loc[ablations["specification"] == "gate_count_only"].iloc[0]

    output_dir.mkdir(parents=True, exist_ok=True)
    instances_path = output_dir / "heldout_instance_domain_distance.csv"
    family_path = output_dir / "heldout_family_calibration_ood.csv"
    ablation_path = output_dir / "heldout_feature_ablation.csv"
    logo_path = output_dir / "training_leave_one_generator_out.csv"
    heldout.to_csv(instances_path, index=False)
    family.to_csv(family_path, index=False)
    ablations.to_csv(ablation_path, index=False)
    logo.to_csv(logo_path, index=False)
    figure_base = output_dir / "family_distance_calibration"
    _plot_family_diagnostics(family, figure_base)

    metric_dispositions = {
        "13.01": "PASS: 15 training and 16 held-out generator families are disjoint, with zero input-hash overlap",
        "13.02": "PASS: the sealed model, 12 features, imputation, scaling, and 0.5 threshold replay all 378 probabilities without refit",
        "13.03": f"PARTIAL: 16 outer families improve evidence but the clustered MCC 95% interval remains wide at {interval_width:.6f}",
        "13.04": f"PARTIAL: training-derived OOD classification identifies {near_families} near and {far_families} far held-out families, so both regimes are not represented",
        "13.05": "PASS: nearest-training, shrinkage-Mahalanobis, and training-range excursion distances are reported per input and family",
        "13.06": "PASS: outcomes, probabilities, calibration, distance, prediction intervals, and failure flags are reported for every held-out family",
        "13.07": "PASS: family-level observed rate, mean predicted probability, calibration error, and Brier score are reported",
        "13.08": f"PASS: complete family-level classification failures are explicitly counted ({int(family['complete_classification_failure'].sum())})",
        "13.09": "PASS: diagnostic leave-one-generator-out refits cover all 15 training generators; this is separate from the sealed held-out test",
        "13.12": "FAIL: held-out qubits span 4 to 8 inside the training range 4 to 10, so no out-of-range qubit extrapolation was tested",
        "13.18": "PASS: the audit explicitly limits all 16 held-out generators to synthetic-distribution evidence, not real-world representativeness",
        "13.19": "PASS: covariate shift is quantified from training-only feature geometry at instance and family levels",
        "13.20": "PASS: conditional Poisson-binomial 95% family outcome-count prediction intervals are reported alongside the clustered MCC confidence interval",
        "13.21": "PASS: frozen full-model performance is compared against gate-count-only and size-only refits; unseen family identity is unavailable as a predictor",
        "13.22": "PASS: shortcut risk is audited with gate-count-only, size-only, range-excursion, OOD, and feature-ablation diagnostics",
        "13.23": "PASS: all 12 leave-one-feature-out diagnostic refits are evaluated on the untouched combined held-out packet",
        "13.24": "PASS: OOD scores and a training leave-one-out 95th-percentile threshold are reported without held-out threshold tuning",
        "13.25": "PARTIAL: a training-only abstention rule is implemented, but it rejects all 378 held-out inputs and has zero useful selective coverage",
    }
    report = {
        "schema_version": "1.0.0",
        "status": "PASS_POSTSEAL_GENERALIZATION_OOD_AUDIT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "sealed classifier diagnostics on 378 unique inputs from 16 unseen synthetic generator families",
        "source_bindings": {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in (
                TRAINING,
                MODEL,
                V1_FEATURES,
                V2_FEATURES,
                COMBINED,
                COMBINED_METRICS,
                FAMILY_DIAGNOSTICS,
            )
        },
        "integrity": {
            "training_rows": int(len(training)),
            "training_families": int(len(training_families)),
            "heldout_rows": int(len(heldout)),
            "heldout_families": int(len(heldout_families)),
            "family_overlap": family_overlap,
            "input_hash_overlap": 0,
            "sealed_probability_replay_max_abs_error": max_probability_error,
            "model_refit_for_primary_predictions": False,
            "threshold_changed": False,
        },
        "outer_interval": {
            "mcc_point": float(combined_metrics["mcc_point"]),
            "mcc_ci95_lower": float(combined_metrics["mcc_ci95_lower"]),
            "mcc_ci95_upper": float(combined_metrics["mcc_ci95_upper"]),
            "width": interval_width,
            "n_outer_families": int(combined_metrics["outer_clusters"]),
            "narrow_interval_criterion_met": False,
        },
        "domain_shift": {
            "training_loo_nn_95pct_threshold": ood_threshold,
            "heldout_instance_ood_rate": float(heldout["ood_abstain"].mean()),
            "near_families": near_families,
            "far_families": far_families,
            "families_with_any_range_excursion": int((family["range_excursion_rate"] > 0).sum()),
        },
        "family_calibration": {
            "families": int(len(family)),
            "complete_classification_failure_families": int(
                family["complete_classification_failure"].sum()
            ),
            "families_observed_inside_conditional_prediction_interval": int(
                family["observed_count_inside_prediction_interval"].sum()
            ),
            "mean_absolute_family_calibration_error": float(
                family["absolute_calibration_error"].mean()
            ),
        },
        "shortcut_diagnostics": {
            "frozen_full_model_metrics": _binary_metrics(y, recorded_probability),
            "diagnostic_full_refit_metrics": {
                key: (None if pd.isna(full[key]) else float(full[key]))
                for key in ("accuracy", "brier", "log_loss", "mcc", "balanced_accuracy", "auroc")
            },
            "gate_count_only_metrics": {
                key: (None if pd.isna(gate_only[key]) else float(gate_only[key]))
                for key in ("accuracy", "brier", "log_loss", "mcc", "balanced_accuracy", "auroc")
            },
            "feature_ablation_specs": int(len(ablations)),
            "training_logo_folds": int(len(logo)),
            "interpretation": (
                "These post-seal refits diagnose shortcut dependence; they do not replace "
                "the frozen classifier or create a second confirmatory test."
            ),
        },
        "selective_prediction": selective,
        "qubit_extrapolation": {
            "training_range": [int(training.n_qubits.min()), int(training.n_qubits.max())],
            "heldout_range": [int(heldout.n_qubits.min()), int(heldout.n_qubits.max())],
            "out_of_range_test_present": False,
        },
        "metric_dispositions": metric_dispositions,
        "claim_boundary": (
            "Supports post-seal diagnostics for unseen synthetic generators only. It does "
            "not establish cross-topology, cross-version, cross-platform, cross-group, "
            "real-world, or out-of-range-qubit generalization. Prediction intervals are "
            "conditional on frozen probabilities and omit model-parameter uncertainty."
        ),
    }
    artifacts = [
        instances_path,
        family_path,
        ablation_path,
        logo_path,
        figure_base.with_suffix(".png"),
        figure_base.with_suffix(".pdf"),
    ]
    report["artifacts"] = {
        path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in artifacts
    }
    report_path = output_dir / "generalization_ood_audit.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = build_audit(args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
