"""Leakage-audited analysis of the sealed generator-held-out experiment.

This module never fits or alters the frozen classifier.  It verifies the seal,
constructs the preregistered joint Qiskit/t|ket> outcome, and estimates the
generator-clustered MCC interval with a nested cluster bootstrap.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.provenance import file_sha256

PROTOCOL_PATH = PROJECT_ROOT / "experiments" / "prepaper_protocol.json"
KEY = ["circuit_id", "trial", "seed", "input_circuit_sha256"]


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _as_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().eq("true")


def _mcc(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=np.int8)
    y_pred = np.asarray(y_pred, dtype=np.int8)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return float((tp * tn - fp * fn) / denominator) if denominator else float("nan")


def _load_tool(path: Path, prefix: str, expected_n: int,
               expected_manifest_sha: str) -> pd.DataFrame:
    frame = pd.read_csv(path.resolve())
    if len(frame) != expected_n:
        raise RuntimeError(f"{prefix}: expected {expected_n} rows, got {len(frame)}")
    if frame.duplicated(KEY).any():
        raise RuntimeError(f"{prefix}: duplicate held-out keys")
    required = KEY + [
        "benchmark_manifest_sha256", "valid_equivalent_output",
        "common_gate_reduction_pct", "compiler_status",
    ]
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise RuntimeError(f"{prefix}: missing columns {missing}")
    manifest_shas = set(frame["benchmark_manifest_sha256"].astype(str))
    if manifest_shas != {expected_manifest_sha}:
        raise RuntimeError(f"{prefix}: manifest SHA mismatch {manifest_shas}")
    keep = required + [c for c in (
        "fidelity_source", "exact_fidelity", "analysis_gate_reduction_pct_itt"
    ) if c in frame.columns]
    return frame[keep].rename(columns={
        "valid_equivalent_output": f"{prefix}_valid",
        "common_gate_reduction_pct": f"{prefix}_common_reduction_pct",
        "compiler_status": f"{prefix}_status",
        "fidelity_source": f"{prefix}_fidelity_source",
        "exact_fidelity": f"{prefix}_exact_fidelity",
        "analysis_gate_reduction_pct_itt": f"{prefix}_reduction_itt",
    })


def analyze(root: Path, qiskit_csv: Path, tket_csv: Path,
            replicates: int, seed: int) -> Path:
    seal_path = root / "sealed_predictions" / "SEALED.json"
    model_path = root / "sealed_predictions" / "model.json"
    prediction_path = root / "sealed_predictions" / "heldout_predictions.csv"
    training_path = root / "sealed_predictions" / "training_features_labels.csv"
    manifest_path = root / "inputs" / "benchmark_manifest.csv"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    if seal.get("status") != "SEALED_BEFORE_HELDOUT_OPTIMIZATION":
        raise RuntimeError("held-out packet is not sealed")
    hash_checks = {
        "prediction_sha256": file_sha256(prediction_path),
        "model_sha256": file_sha256(model_path),
        "training_packet_sha256": file_sha256(training_path),
        "heldout_manifest_sha256": file_sha256(manifest_path),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
    }
    mismatches = {k: (seal.get(k), v) for k, v in hash_checks.items()
                  if seal.get(k) != v}
    if mismatches:
        raise RuntimeError(f"sealed hash mismatch: {mismatches}")

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if replicates != int(protocol["bootstrap_replicates"]):
        raise RuntimeError("bootstrap replicate count differs from frozen protocol")
    if seed != int(protocol["bootstrap_seed"]):
        raise RuntimeError("bootstrap seed differs from frozen protocol")
    threshold = float(protocol["heldout"]["headroom_threshold_pct"])

    manifest = pd.read_csv(manifest_path)
    predictions = pd.read_csv(prediction_path)
    expected_n = len(manifest)
    if expected_n != 240 or manifest.duplicated(KEY).any():
        raise RuntimeError("held-out manifest integrity failure")
    if len(predictions) != expected_n or predictions.duplicated(KEY).any():
        raise RuntimeError("sealed prediction key integrity failure")
    manifest_sha = file_sha256(manifest_path)
    qiskit = _load_tool(qiskit_csv, "qiskit", expected_n, manifest_sha)
    tket = _load_tool(tket_csv, "tket", expected_n, manifest_sha)
    data = predictions.merge(
        manifest[KEY + ["circuit_family", "n_qubits"]], on=KEY,
        how="inner", validate="one_to_one", suffixes=("", "_manifest"),
    ).merge(qiskit, on=KEY, how="inner", validate="one_to_one").merge(
        tket, on=KEY, how="inner", validate="one_to_one")
    if len(data) != expected_n:
        raise RuntimeError("held-out outcome/prediction key mismatch")
    if "circuit_family_manifest" in data:
        if not (data.circuit_family == data.circuit_family_manifest).all():
            raise RuntimeError("generator-family mismatch")
        data = data.drop(columns=["circuit_family_manifest"])
    for column in ("qiskit_valid", "tket_valid"):
        data[column] = _as_bool(data[column])
    data["observed_joint_external_headroom"] = (
        data.qiskit_valid & data.tket_valid
        & (data.qiskit_common_reduction_pct > threshold)
        & (data.tket_common_reduction_pct > threshold)
    ).astype(int)
    # Seeds of deterministic generators can produce byte-identical circuits.
    # Retain every execution row in the joined audit artifact, but use each
    # unique circuit once for confirmatory prediction metrics and uncertainty.
    identity = ["circuit_family", "input_circuit_sha256"]
    metric_columns = [
        "observed_joint_external_headroom",
        "predicted_joint_external_headroom",
        "predicted_probability_joint_external_headroom",
    ]
    inconsistent = data.groupby(identity, sort=False)[metric_columns].nunique(dropna=False)
    if (inconsistent > 1).any().any():
        raise RuntimeError("duplicate input hash has inconsistent prediction or outcome")
    unique_data = data.drop_duplicates(identity, keep="first").copy()
    y = unique_data.observed_joint_external_headroom.to_numpy(dtype=np.int8)
    pred = unique_data.predicted_joint_external_headroom.to_numpy(dtype=np.int8)
    probability = unique_data.predicted_probability_joint_external_headroom.to_numpy(float)

    point_mcc = _mcc(y, pred)
    families = np.asarray(sorted(unique_data.circuit_family.unique()), dtype=object)
    groups = {family: np.flatnonzero(unique_data.circuit_family.to_numpy() == family)
               for family in families}
    rng = np.random.default_rng(seed)
    bootstrap = np.full(replicates, np.nan, dtype=float)
    for b in range(replicates):
        sampled_families = rng.choice(families, size=len(families), replace=True)
        sampled_indices = []
        for family in sampled_families:
            indices = groups[family]
            sampled_indices.append(rng.choice(indices, size=len(indices), replace=True))
        take = np.concatenate(sampled_indices)
        bootstrap[b] = _mcc(y[take], pred[take])
    finite = bootstrap[np.isfinite(bootstrap)]
    if len(finite) < int(0.95 * replicates):
        raise RuntimeError("too many non-identifiable bootstrap MCC replicates")
    ci_low, ci_high = np.percentile(finite, [2.5, 97.5])

    metrics = {
        "primary_metric": "generator_clustered_nested_bootstrap_mcc",
        "mcc_point": point_mcc,
        "mcc_ci95_lower": float(ci_low),
        "mcc_ci95_upper": float(ci_high),
        "success_ci_lower_gt_zero": bool(ci_low > 0.0),
        "bootstrap_replicates": replicates,
        "bootstrap_finite_replicates": int(len(finite)),
        "bootstrap_seed": seed,
        "outer_clusters": int(len(families)),
        "n_execution_rows": int(len(data)),
        "n_unique_inputs": int(len(unique_data)),
        "n_instances": int(len(unique_data)),
        "instance_unit": "unique input_circuit_sha256 within generator family",
        "observed_positive_prevalence": float(y.mean()),
        "predicted_positive_prevalence": float(pred.mean()),
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "auroc": float(roc_auc_score(y, probability)) if len(np.unique(y)) == 2 else None,
        "headroom_threshold_pct": threshold,
    }
    family_rows = []
    for family, group in unique_data.groupby("circuit_family", sort=True):
        gy = group.observed_joint_external_headroom.to_numpy(np.int8)
        gp = group.predicted_joint_external_headroom.to_numpy(np.int8)
        family_rows.append({
            "circuit_family": family, "n_unique_inputs": len(group),
            "observed_positive_rate": float(gy.mean()),
            "predicted_positive_rate": float(gp.mean()),
            "mcc": _mcc(gy, gp),
            "accuracy": float(accuracy_score(gy, gp)),
            "qiskit_valid_rate": float(group.qiskit_valid.mean()),
            "tket_valid_rate": float(group.tket_valid.mean()),
        })

    output_dir = root / "analysis"
    merged_path = output_dir / "heldout_predictions_outcomes.csv"
    bootstrap_path = output_dir / "mcc_nested_bootstrap_10000.csv"
    family_path = output_dir / "generator_diagnostics.csv"
    metrics_path = output_dir / "heldout_metrics.json"
    _atomic_text(merged_path, data.to_csv(index=False))
    _atomic_text(bootstrap_path, pd.DataFrame({
        "replicate": np.arange(replicates), "mcc": bootstrap,
    }).to_csv(index=False))
    _atomic_text(family_path, pd.DataFrame(family_rows).to_csv(index=False))
    audit = {
        **metrics,
        "seal_hashes_verified": True,
        "pair_key": KEY,
        "qiskit_result_sha256": file_sha256(qiskit_csv.resolve()),
        "tket_result_sha256": file_sha256(tket_csv.resolve()),
        "merged_sha256": file_sha256(merged_path),
        "bootstrap_sha256": file_sha256(bootstrap_path),
        "generator_diagnostics_sha256": file_sha256(family_path),
        "sealed_prediction_sha256": hash_checks["prediction_sha256"],
        "heldout_manifest_sha256": manifest_sha,
        "protocol_sha256": hash_checks["protocol_sha256"],
        "source_sha256": file_sha256(Path(__file__).resolve()),
    }
    _atomic_text(metrics_path, json.dumps(audit, indent=2, sort_keys=True))
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return metrics_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--qiskit-csv", type=Path, required=True)
    parser.add_argument("--tket-csv", type=Path, required=True)
    parser.add_argument("--replicates", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260809)
    args = parser.parse_args()
    analyze(args.root.resolve(), args.qiskit_csv, args.tket_csv,
            args.replicates, args.seed)


if __name__ == "__main__":
    main()
