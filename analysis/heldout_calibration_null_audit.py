"""Post-seal calibration, no-information baseline, and label-permutation audit."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    matthews_corrcoef,
    roc_auc_score,
)


ROOT = Path(__file__).resolve().parents[1]
HELDOUT = ROOT / "data/v10/prepaper/heldout"
SOURCE = HELDOUT / "analysis/heldout_predictions_outcomes.csv"
METRICS = HELDOUT / "analysis/heldout_metrics.json"
SEAL = HELDOUT / "sealed_predictions/SEALED.json"
PREDICTIONS = HELDOUT / "sealed_predictions/heldout_predictions.csv"
DEFAULT_OUTPUT_DIR = HELDOUT / "analysis/calibration_null"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _mcc(y: np.ndarray, pred: np.ndarray) -> float:
    return float(matthews_corrcoef(y, pred))


def derive(output_dir: Path = DEFAULT_OUTPUT_DIR, permutations: int = 20000) -> dict[str, object]:
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    if _sha256(SOURCE) != metrics["merged_sha256"]:
        raise RuntimeError("held-out merged analysis hash mismatch")
    if _sha256(PREDICTIONS) != seal["prediction_sha256"]:
        raise RuntimeError("sealed held-out prediction hash mismatch")
    frame = pd.read_csv(SOURCE)
    identity = ["circuit_family", "input_circuit_sha256"]
    required = [
        "observed_joint_external_headroom",
        "predicted_joint_external_headroom",
        "predicted_probability_joint_external_headroom",
    ]
    inconsistent = frame.groupby(identity, sort=False)[required].nunique(dropna=False)
    if (inconsistent > 1).any().any():
        raise RuntimeError("duplicate held-out identity has inconsistent label or prediction")
    unique = frame.drop_duplicates(identity).sort_values(identity).reset_index(drop=True)
    if len(frame) != 240 or len(unique) != 186:
        raise RuntimeError("unexpected held-out execution/unique-input counts")
    y = unique[required[0]].to_numpy(dtype=np.int8)
    pred = unique[required[1]].to_numpy(dtype=np.int8)
    probability = unique[required[2]].to_numpy(dtype=float)
    if not np.all((probability >= 0.0) & (probability <= 1.0)):
        raise RuntimeError("held-out probabilities outside [0, 1]")

    order = np.argsort(probability, kind="stable")
    bins = []
    for index, indices in enumerate(np.array_split(order, 10)):
        bins.append(
            {
                "bin": index + 1,
                "n": len(indices),
                "mean_predicted_probability": float(probability[indices].mean()),
                "observed_positive_rate": float(y[indices].mean()),
            }
        )
    calibration = pd.DataFrame(bins)
    ece = float(
        np.sum(
            calibration["n"]
            / len(y)
            * np.abs(
                calibration["mean_predicted_probability"]
                - calibration["observed_positive_rate"]
            )
        )
    )
    clipped = np.clip(probability, 1e-8, 1 - 1e-8)
    logit = np.log(clipped / (1.0 - clipped))
    calibration_model = sm.GLM(y, sm.add_constant(logit), family=sm.families.Binomial()).fit()
    confint = np.asarray(calibration_model.conf_int(alpha=0.05), dtype=float)

    prevalence = float(y.mean())
    baseline_probability = np.full(len(y), prevalence)
    majority = np.full(len(y), int(prevalence >= 0.5), dtype=np.int8)
    model_metrics = {
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "mcc": _mcc(y, pred),
        "auroc": float(roc_auc_score(y, probability)),
        "brier": float(brier_score_loss(y, probability)),
        "log_loss": float(log_loss(y, probability, labels=[0, 1])),
    }
    baseline_metrics = {
        "definition": "constant observed sealed-panel prevalence probability plus majority class",
        "prevalence_probability": prevalence,
        "accuracy": float(accuracy_score(y, majority)),
        "balanced_accuracy": float(balanced_accuracy_score(y, majority)),
        "mcc": _mcc(y, majority),
        "auroc": 0.5,
        "brier": float(brier_score_loss(y, baseline_probability)),
        "log_loss": float(log_loss(y, baseline_probability, labels=[0, 1])),
    }

    family = unique.groupby("circuit_family", as_index=False).agg(
        observed_label=(required[0], "first"),
        observed_label_levels=(required[0], "nunique"),
        mean_predicted_probability=(required[2], "mean"),
    )
    if len(family) != 8 or not family["observed_label_levels"].eq(1).all():
        raise RuntimeError("unexpected held-out family count")
    family_y = family["observed_label"].to_numpy(dtype=np.int8)
    family_probability = family["mean_predicted_probability"].to_numpy(dtype=float)
    family_pred = (family_probability >= 0.5).astype(np.int8)
    positive_families = int(family_y.sum())
    assignments = list(itertools.combinations(range(len(family)), positive_families))
    permutation_rows = []
    for replicate, positive_indices in enumerate(assignments):
        permuted = np.zeros(len(family), dtype=np.int8)
        permuted[list(positive_indices)] = 1
        permutation_rows.append(
            {
                "replicate": replicate,
                "positive_families": "|".join(family.iloc[list(positive_indices)]["circuit_family"]),
                "mcc": _mcc(permuted, family_pred),
                "auroc": float(roc_auc_score(permuted, family_probability)),
                "brier": float(brier_score_loss(permuted, family_probability)),
            }
        )
    permutation = pd.DataFrame(permutation_rows)
    observed_family_metrics = {
        "mcc": _mcc(family_y, family_pred),
        "auroc": float(roc_auc_score(family_y, family_probability)),
        "brier": float(brier_score_loss(family_y, family_probability)),
    }
    p_values = {
        "mcc_greater_or_equal": float((permutation["mcc"] >= observed_family_metrics["mcc"]).mean()),
        "auroc_greater_or_equal": float((permutation["auroc"] >= observed_family_metrics["auroc"]).mean()),
        "brier_less_or_equal": float((permutation["brier"] <= observed_family_metrics["brier"]).mean()),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    calibration_path = output_dir / "calibration_bins.csv"
    permutation_path = output_dir / "exact_family_block_label_permutations.csv"
    json_path = output_dir / "calibration_null_audit.json"
    png_path = output_dir / "reliability_diagram.png"
    pdf_path = output_dir / "reliability_diagram.pdf"
    calibration.to_csv(calibration_path, index=False)
    permutation.to_csv(permutation_path, index=False)

    fig, axis = plt.subplots(figsize=(6.2, 5.5), constrained_layout=True)
    axis.plot([0, 1], [0, 1], linestyle="--", color="0.35", label="Perfect calibration")
    axis.plot(
        calibration["mean_predicted_probability"],
        calibration["observed_positive_rate"],
        marker="o",
        label="Sealed model (10 equal-count bins)",
    )
    axis.axhline(prevalence, linestyle=":", color="C1", label="No-information prevalence")
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.set_xlabel("Mean predicted probability")
    axis.set_ylabel("Observed positive rate")
    axis.set_title("Generator-held-out reliability diagram (186 unique inputs)")
    axis.grid(alpha=0.25)
    axis.legend(loc="lower right")
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    plt.close(fig)

    payload = {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_HELDOUT_CALIBRATION_NULL_BASELINE_AND_LABEL_PERMUTATION_COMPLETE",
        "source_sha256": _sha256(SOURCE),
        "sealed_prediction_sha256": _sha256(PREDICTIONS),
        "execution_rows": len(frame),
        "unique_inputs": len(unique),
        "families": len(family),
        "observed_positive_prevalence": prevalence,
        "sealed_model_metrics": model_metrics,
        "no_information_baseline": baseline_metrics,
        "calibration": {
            "equal_count_bins": len(calibration),
            "expected_calibration_error": ece,
            "intercept": float(calibration_model.params[0]),
            "intercept_ci95_low": float(confint[0, 0]),
            "intercept_ci95_high": float(confint[0, 1]),
            "slope": float(calibration_model.params[1]),
            "slope_ci95_low": float(confint[1, 0]),
            "slope_ci95_high": float(confint[1, 1]),
            "glm_converged": bool(calibration_model.converged),
        },
        "exact_family_block_label_permutation": {
            "exact_assignments": len(assignments),
            "positive_families_per_assignment": positive_families,
            "requested_monte_carlo_permutations_not_used": permutations,
            "null": "five positive family labels assigned across all choose(8,5)=56 family-block allocations; predictions fixed",
            "observed_equal_family_metrics": observed_family_metrics,
            "exact_inclusive_p_values": p_values,
        },
        "calibration_bins_csv": _artifact_path(calibration_path),
        "calibration_bins_csv_sha256": _sha256(calibration_path),
        "permutation_csv": _artifact_path(permutation_path),
        "permutation_csv_sha256": _sha256(permutation_path),
        "figure_png": _artifact_path(png_path),
        "figure_png_sha256": _sha256(png_path),
        "figure_pdf": _artifact_path(pdf_path),
        "figure_pdf_sha256": _sha256(pdf_path),
        "interpretation": (
            "Predictions, labels, and threshold remain sealed. Calibration and null comparisons "
            "are post-seal diagnostics and do not refit or select the classifier."
        ),
        "limitations": [
            "Only eight held-out generator families and 186 unique circuit hashes are available.",
            "The prevalence baseline uses the sealed evaluation prevalence and is a diagnostic no-information reference, not a deployable prior estimate.",
            "All observed labels are constant within family, so within-family permutation is degenerate; the audit therefore uses exact whole-family label allocation.",
            "The exact null has only 56 allocations, so attainable p-values are discrete and family-level power is limited.",
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--permutations", type=int, default=20000)
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    payload = derive(output, args.permutations)
    print(json.dumps({"output": _artifact_path(output / "calibration_null_audit.json"), "status": payload["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
