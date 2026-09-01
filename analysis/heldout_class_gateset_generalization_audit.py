"""Run diagnostic leave-one-algorithm-class and leave-one-exact-gate-set-out audits."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, matthews_corrcoef, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / "data/v10/prepaper/heldout/sealed_predictions/training_features_labels.csv"
MODEL = ROOT / "data/v10/prepaper/heldout/sealed_predictions/model.json"
TAXONOMY_SOURCE = ROOT / "docs/manuscript/manuscript.md"
OUTPUT_DIR = ROOT / "data/v10/prepaper/heldout_v2/analysis/generalization_ood/class_gateset"
CLASS_MAP = {
    "HaarRandom": "Random", "RandomClifford": "Random",
    "QFT": "Algorithmic", "GHZ": "Algorithmic", "Oracle": "Algorithmic",
    "CNOT": "Algorithmic", "Grover": "Algorithmic", "Adder": "Algorithmic",
    "QuantumWalk": "Algorithmic", "IQP": "Algorithmic",
    "QAOA": "Variational", "VQE": "Variational",
    "HardwareEfficient": "Variational", "UCCSD_inspired": "Variational",
    "SurfaceCode": "Error-correcting",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pipeline() -> object:
    return make_pipeline(
        SimpleImputer(strategy="median"), StandardScaler(),
        LogisticRegression(C=1.0, class_weight="balanced", solver="lbfgs",
                           random_state=20260809, max_iter=10000),
    )


def _metrics(y: np.ndarray, probability: np.ndarray) -> dict[str, object]:
    prediction = (probability >= 0.5).astype(np.int8)
    return {
        "n": int(len(y)), "positive_rate": float(y.mean()),
        "accuracy": float(accuracy_score(y, prediction)),
        "brier": float(brier_score_loss(y, probability)),
        "mcc": float(matthews_corrcoef(y, prediction)) if len(np.unique(y)) == 2 else None,
        "auroc": float(roc_auc_score(y, probability)) if len(np.unique(y)) == 2 else None,
    }


def _crossfit(frame: pd.DataFrame, features: list[str], group_column: str,
              label: str) -> tuple[pd.DataFrame, dict[str, object]]:
    y = frame["label_joint_external_headroom"].to_numpy(dtype=np.int8)
    probabilities = np.full(len(frame), np.nan)
    rows = []
    for group_name in sorted(frame[group_column].astype(str).unique()):
        test = frame[group_column].astype(str).eq(group_name).to_numpy()
        train = ~test
        if len(np.unique(y[train])) != 2:
            raise ValueError(f"{label} fold {group_name} leaves single-class training data")
        pipeline = _pipeline()
        pipeline.fit(frame.loc[train, features], y[train])
        probability = pipeline.predict_proba(frame.loc[test, features])[:, 1]
        probabilities[test] = probability
        row = {f"left_out_{label}": group_name,
               "training_groups": int(frame.loc[train, group_column].nunique())}
        row.update(_metrics(y[test], probability))
        rows.append(row)
    if not np.isfinite(probabilities).all():
        raise ValueError(f"{label} cross-fit did not predict every training row exactly once")
    return pd.DataFrame(rows), _metrics(y, probabilities)


def build_audit(output_dir: Path = OUTPUT_DIR) -> dict[str, object]:
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    features = list(model["features"])
    frame = pd.read_csv(TRAINING)
    if "log1p_n_gates" in features and "log1p_n_gates" not in frame:
        frame["log1p_n_gates"] = np.log1p(frame["n_gates"])
    missing_families = sorted(set(frame["circuit_family"]) - set(CLASS_MAP))
    if missing_families:
        raise ValueError(f"algorithm-class taxonomy incomplete: {missing_families}")
    frame["algorithm_class"] = frame["circuit_family"].map(CLASS_MAP)
    if frame["gate_type_str"].isna().any():
        raise ValueError("exact gate-set signature is missing")
    class_folds, class_pooled = _crossfit(frame, features, "algorithm_class", "algorithm_class")
    gateset_folds, gateset_pooled = _crossfit(frame, features, "gate_type_str", "exact_gate_set")
    taxonomy = frame.groupby(["algorithm_class", "circuit_family"], as_index=False).agg(
        rows=("input_circuit_sha256", "size"),
        exact_gate_set_signatures=("gate_type_str", "nunique"),
        positive_rate=("label_joint_external_headroom", "mean"),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "leave_one_algorithm_class_out.csv": class_folds,
        "leave_one_exact_gate_set_out.csv": gateset_folds,
        "algorithm_class_taxonomy.csv": taxonomy,
    }
    artifacts = {}
    for name, table in outputs.items():
        path = output_dir / name
        table.to_csv(path, index=False)
        artifacts[name] = {"rows": int(len(table)), "sha256": _sha(path)}
    audit = {
        "schema_version": "1.0.0",
        "status": "PASS_DIAGNOSTIC_CLASS_AND_GATESET_GENERALIZATION_AUDIT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "diagnostic cross-fitted refits on the 520-row, 15-family training packet",
        "integrity": {
            "rows": int(len(frame)), "families": int(frame["circuit_family"].nunique()),
            "algorithm_classes": int(frame["algorithm_class"].nunique()),
            "exact_gate_set_signatures": int(frame["gate_type_str"].nunique()),
            "model_features": features,
        },
        "leave_one_algorithm_class_out": {
            "folds": int(len(class_folds)), "classes": sorted(frame["algorithm_class"].unique()),
            "pooled_cross_fitted_metrics": class_pooled,
        },
        "leave_one_exact_gate_set_out": {
            "folds": int(len(gateset_folds)),
            "definition": "exact sorted gate-name vocabulary recorded in gate_type_str",
            "pooled_cross_fitted_metrics": gateset_pooled,
            "smallest_fold_n": int(gateset_folds["n"].min()),
        },
        "metric_dispositions": {
            "13.10": "PASS: all four manuscript-defined algorithm classes are left out in turn and every training row receives one cross-fitted diagnostic prediction",
            "13.11": "PASS: all 18 observed exact gate-set signatures are left out in turn and every training row receives one cross-fitted diagnostic prediction",
        },
        "claim_boundary": (
            "These are post-seal diagnostic refits on the training packet, not changes to the sealed "
            "classifier and not untouched external tests. Algorithm classes follow manuscript Table 2. "
            "Gate-set folds use exact observed vocabularies; some folds are small or single-outcome, "
            "so pooled metrics do not establish broad unseen-basis generalization."
        ),
        "source_bindings": {
            "training_features_labels.csv": _sha(TRAINING), "model.json": _sha(MODEL),
            "docs/manuscript/manuscript.md": _sha(TAXONOMY_SOURCE),
            "analysis/heldout_class_gateset_generalization_audit.py": _sha(Path(__file__)),
        },
        "artifacts": artifacts,
    }
    output = output_dir / "class_gateset_generalization_audit.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(output)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    audit = build_audit(args.output_dir)
    print(json.dumps({"status": audit["status"], "integrity": audit["integrity"],
                      "leave_one_algorithm_class_out": audit["leave_one_algorithm_class_out"],
                      "leave_one_exact_gate_set_out": audit["leave_one_exact_gate_set_out"]},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
