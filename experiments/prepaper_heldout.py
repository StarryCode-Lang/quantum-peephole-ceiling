"""Sealed out-of-generator validation for the pre-paper protocol.

Phase ``prepare`` is intentionally outcome-blind: it materializes new circuit
families, extracts pre-optimization features, and hashes the inputs.  A later
``seal`` phase will fit the frozen training-only classifier after the balanced
SOTA training results are complete.  Optimizers must not be run on this
manifest until the sealed prediction packet exists.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Dict

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit, qasm2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.predictive_advantage import extract_structural_features
from src.circuits.real_benchmarks import circuit_sha256
from src.provenance import file_sha256

VERSION = "1.0.0"
BASE_SEED = 20260810
SIZES = (4, 6, 8)
TRIALS = 10
OUT_ROOT = PROJECT_ROOT / "data" / "v10" / "prepaper" / "heldout"
PROTOCOL_PATH = PROJECT_ROOT / "experiments" / "prepaper_protocol.json"
FEATURES = [
    "n_qubits", "log1p_n_gates", "inverse_pair_density",
    "wire_inverse_density", "commutation_density", "gate_diversity",
    "rotation_fraction", "clifford_fraction", "t_fraction",
    "multi_q_fraction", "has_multi_controlled", "depth_to_gate_ratio",
]


def _mirror_random(n: int, seed: int) -> QuantumCircuit:
    rng = np.random.default_rng(seed)
    prefix = QuantumCircuit(n)
    one_q = ("h", "s", "t", "x", "z")
    for _ in range(4 * n):
        if rng.random() < 0.35:
            a, b = rng.choice(n, 2, replace=False)
            prefix.cx(int(a), int(b))
        else:
            getattr(prefix, one_q[int(rng.integers(len(one_q)))])(int(rng.integers(n)))
    return prefix.compose(prefix.inverse())


def _separated_inverse(n: int, seed: int) -> QuantumCircuit:
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    pairs = (("t", "tdg"), ("s", "sdg"), ("h", "h"), ("x", "x"))
    for _ in range(3 * n):
        q = int(rng.integers(n))
        a, b = pairs[int(rng.integers(len(pairs)))]
        getattr(qc, a)(q)
        for other in range(n):
            if other != q and rng.random() < 0.55:
                qc.z(other)
        getattr(qc, b)(q)
    return qc


def _pauli_gadget_ladder(n: int, seed: int) -> QuantumCircuit:
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    for layer in range(4):
        for q in range(n - 1):
            qc.cx(q, q + 1)
        qc.rz(float(rng.uniform(-np.pi, np.pi)), n - 1)
        for q in reversed(range(n - 1)):
            qc.cx(q, q + 1)
        if layer % 2 == 0:
            for q in range(0, n, 2):
                qc.h(q)
    return qc


def _cluster_echo(n: int, seed: int) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    for q in range(n):
        qc.h(q)
    for q in range(n - 1):
        qc.cz(q, q + 1)
    for q in range(1, n, 2):
        qc.x(q); qc.x(q)
    for q in reversed(range(n - 1)):
        qc.cz(q, q + 1)
    return qc


def _ising_brickwork(n: int, seed: int) -> QuantumCircuit:
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    for layer in range(5):
        for q in range(layer % 2, n - 1, 2):
            qc.cx(q, q + 1)
            qc.rz(float(rng.uniform(-np.pi, np.pi)), q + 1)
            qc.cx(q, q + 1)
        for q in range(n):
            qc.rx(float(rng.uniform(-np.pi, np.pi)), q)
    return qc


def _fredkin_chain(n: int, seed: int) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    for q in range(n - 2):
        qc.cswap(q, q + 1, q + 2)
    for q in reversed(range(n - 2)):
        qc.cswap(q, q + 1, q + 2)
    return qc


def _controlled_rotation_fanout(n: int, seed: int) -> QuantumCircuit:
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    for target in range(1, n):
        angle = float(rng.uniform(-np.pi, np.pi))
        qc.crz(angle, 0, target)
        qc.rz(-angle / 2, target)
    for target in reversed(range(1, n)):
        qc.cx(0, target); qc.cx(0, target)
    return qc


def _dihedral_alternation(n: int, seed: int) -> QuantumCircuit:
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    for layer in range(6):
        for q in range(n):
            (qc.t if rng.random() < 0.5 else qc.tdg)(q)
        for q in range(layer % 2, n - 1, 2):
            qc.cx(q, q + 1)
        if layer in (2, 5):
            for q in range(n):
                qc.h(q); qc.h(q)
    return qc


GENERATORS: Dict[str, Callable[[int, int], QuantumCircuit]] = {
    "MirrorRandom": _mirror_random,
    "SeparatedInverse": _separated_inverse,
    "PauliGadgetLadder": _pauli_gadget_ladder,
    "ClusterEcho": _cluster_echo,
    "IsingBrickwork": _ising_brickwork,
    "FredkinChain": _fredkin_chain,
    "ControlledRotationFanout": _controlled_rotation_fanout,
    "DihedralAlternation": _dihedral_alternation,
}


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _portable(circuit: QuantumCircuit) -> QuantumCircuit:
    consumed = qasm2.loads(qasm2.dumps(circuit),
                           custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    for _ in range(12):
        names = {inst.operation.name for inst in consumed.data
                 if inst.operation.num_qubits > 3 and inst.operation.definition is not None}
        if not names:
            return consumed
        consumed = consumed.decompose(gates_to_decompose=sorted(names))
    raise RuntimeError("held-out portable decomposition did not converge")


def prepare(output_root: Path) -> Path:
    input_dir = output_root / "inputs"
    qasm_dir = input_dir / "qasm"
    qasm_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows, feature_rows = [], []
    for family, generator in GENERATORS.items():
        for n in SIZES:
            for trial in range(TRIALS):
                seed = BASE_SEED + 10000 * list(GENERATORS).index(family) + 100 * n + trial
                source = generator(n, seed)
                circuit = _portable(source)
                input_sha = circuit_sha256(circuit)
                circuit_id = f"heldout_{family.lower()}_n{n}_t{trial}"
                qasm_path = qasm_dir / f"{circuit_id}_{input_sha[:12]}.qasm"
                _write_atomic(qasm_path, qasm2.dumps(circuit))
                manifest_rows.append({
                    "schema_version": "1.0.0", "trial": trial, "seed": seed,
                    "circuit_id": circuit_id, "circuit_family": family,
                    "circuit_type": family.lower(), "suite": "prepaper_heldout_v1",
                    "n_qubits": circuit.num_qubits,
                    "source_circuit_sha256": circuit_sha256(source),
                    "input_circuit_sha256": input_sha,
                    "qasm_sha256": file_sha256(qasm_path),
                    "qasm_path": qasm_path.relative_to(PROJECT_ROOT).as_posix(),
                    "notes": "Sealed generator-family held-out instance",
                })
                features = extract_structural_features(circuit)
                feature_rows.append({
                    "circuit_id": circuit_id, "circuit_family": family,
                    "trial": trial, "seed": seed,
                    "input_circuit_sha256": input_sha, **features,
                })
    manifest = pd.DataFrame(manifest_rows).sort_values(
        ["circuit_family", "n_qubits", "trial"], kind="stable").reset_index(drop=True)
    features = pd.DataFrame(feature_rows).sort_values(
        ["circuit_family", "n_qubits", "trial"], kind="stable").reset_index(drop=True)
    if len(manifest) != len(GENERATORS) * len(SIZES) * TRIALS:
        raise RuntimeError("held-out row-count mismatch")
    if manifest.duplicated(["circuit_id", "trial", "seed", "input_circuit_sha256"]).any():
        raise RuntimeError("duplicate held-out pair key")
    manifest_path = input_dir / "benchmark_manifest.csv"
    feature_path = input_dir / "preoptimization_features.csv"
    _write_atomic(manifest_path, manifest.to_csv(index=False))
    _write_atomic(feature_path, features.to_csv(index=False))
    metadata = {
        "schema_version": "1.0.0", "version": VERSION,
        "status": "inputs_and_features_only_no_optimizer_outcomes",
        "n_rows": len(manifest), "n_families": len(GENERATORS),
        "families": list(GENERATORS), "sizes": list(SIZES), "trials": TRIALS,
        "base_seed": BASE_SEED,
        "manifest_sha256": file_sha256(manifest_path),
        "features_sha256": file_sha256(feature_path),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "source_sha256": file_sha256(Path(__file__).resolve()),
    }
    _write_atomic(input_dir / "metadata.json", json.dumps(metadata, indent=2, sort_keys=True))
    print(f"Prepared outcome-blind held-out packet: {len(manifest)} rows -> {manifest_path}")
    return manifest_path


def _feature_frame(manifest: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in manifest.to_dict(orient="records"):
        qasm_path = PROJECT_ROOT / str(row["qasm_path"])
        circuit = qasm2.loads(
            qasm_path.read_text(encoding="utf-8"),
            custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
        )
        if circuit_sha256(circuit) != str(row["input_circuit_sha256"]):
            raise RuntimeError(f"feature input SHA mismatch: {qasm_path}")
        feature = extract_structural_features(circuit)
        feature["log1p_n_gates"] = float(np.log1p(feature["n_gates"]))
        rows.append({
            "circuit_id": str(row["circuit_id"]),
            "circuit_family": str(row["circuit_family"]),
            "trial": int(row["trial"]), "seed": int(row["seed"]),
            "input_circuit_sha256": str(row["input_circuit_sha256"]),
            **feature,
        })
    return pd.DataFrame(rows)


def seal(output_root: Path, training_manifest_path: Path,
         qiskit_csv: Path, tket_csv: Path) -> Path:
    """Fit the frozen training-only model and seal held-out predictions."""
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    input_dir = output_root / "inputs"
    prediction_dir = output_root / "sealed_predictions"
    if (output_root / "results").exists() and any((output_root / "results").rglob("*.csv")):
        raise RuntimeError("held-out optimizer outcomes already exist; refusing to seal")
    held_manifest_path = input_dir / "benchmark_manifest.csv"
    held_feature_path = input_dir / "preoptimization_features.csv"
    input_meta = json.loads((input_dir / "metadata.json").read_text(encoding="utf-8"))
    if file_sha256(held_manifest_path) != input_meta["manifest_sha256"]:
        raise RuntimeError("held-out manifest changed since preparation")
    if file_sha256(held_feature_path) != input_meta["features_sha256"]:
        raise RuntimeError("held-out feature file changed since preparation")

    training_manifest_path = training_manifest_path.resolve()
    training_manifest = pd.read_csv(training_manifest_path)
    train_features = _feature_frame(training_manifest)
    key = ["circuit_id", "trial", "seed", "input_circuit_sha256"]

    def load_tool(path: Path, prefix: str) -> pd.DataFrame:
        frame = pd.read_csv(path.resolve())
        if len(frame) != len(training_manifest):
            raise RuntimeError(f"{prefix} row count != training manifest")
        if frame.duplicated(key).any():
            raise RuntimeError(f"duplicate {prefix} training keys")
        keep = key + ["valid_equivalent_output", "common_gate_reduction_pct"]
        return frame[keep].rename(columns={
            "valid_equivalent_output": f"{prefix}_valid",
            "common_gate_reduction_pct": f"{prefix}_common_reduction_pct",
        })

    qiskit = load_tool(qiskit_csv, "qiskit")
    tket = load_tool(tket_csv, "tket")
    training = train_features.merge(qiskit, on=key, validate="one_to_one").merge(
        tket, on=key, validate="one_to_one")
    if len(training) != len(training_manifest):
        raise RuntimeError("training feature/outcome key mismatch")
    for column in ("qiskit_valid", "tket_valid"):
        training[column] = training[column].astype(str).str.lower().eq("true")
    training["label_joint_external_headroom"] = (
        training["qiskit_valid"] & training["tket_valid"]
        & (training["qiskit_common_reduction_pct"] > 1.0)
        & (training["tket_common_reduction_pct"] > 1.0)
    ).astype(int)
    X = training[FEATURES].replace([np.inf, -np.inf], np.nan)
    y = training["label_joint_external_headroom"].to_numpy(dtype=int)

    held = pd.read_csv(held_feature_path)
    held["log1p_n_gates"] = np.log1p(held["n_gates"].astype(float))
    X_held = held[FEATURES].replace([np.inf, -np.inf], np.nan)
    unique_classes = np.unique(y)
    if len(unique_classes) == 2:
        pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                penalty="l2", C=1.0, class_weight="balanced",
                solver="lbfgs", max_iter=2000, random_state=20260809,
            )),
        ])
        pipeline.fit(X, y)
        probability = pipeline.predict_proba(X_held)[:, 1]
        prediction = (probability >= 0.5).astype(int)
        imputer = pipeline.named_steps["imputer"]
        scaler = pipeline.named_steps["scaler"]
        classifier = pipeline.named_steps["classifier"]
        model_record = {
            "model": "L2_logistic_regression", "C": 1.0,
            "class_weight": "balanced", "solver": "lbfgs",
            "threshold": 0.5, "random_state": 20260809,
            "imputer_statistics": imputer.statistics_.tolist(),
            "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(),
            "classes": classifier.classes_.tolist(),
            "coefficients": classifier.coef_.tolist(),
            "intercept": classifier.intercept_.tolist(),
        }
    else:
        constant = int(unique_classes[0])
        probability = np.full(len(held), float(constant))
        prediction = np.full(len(held), constant, dtype=int)
        model_record = {
            "model": "constant_single_training_class_fallback",
            "constant": constant, "threshold": 0.5,
            "confirmatory_mcc_identifiable": False,
        }

    predictions = held[key + ["circuit_family", "n_qubits", "n_gates"]].copy()
    predictions["predicted_probability_joint_external_headroom"] = probability
    predictions["predicted_joint_external_headroom"] = prediction
    prediction_dir.mkdir(parents=True, exist_ok=True)
    prediction_path = prediction_dir / "heldout_predictions.csv"
    training_path = prediction_dir / "training_features_labels.csv"
    model_path = prediction_dir / "model.json"
    _write_atomic(prediction_path, predictions.to_csv(index=False))
    _write_atomic(training_path, training.to_csv(index=False))
    model_record.update({
        "schema_version": "1.0.0", "features": FEATURES,
        "training_n": int(len(training)),
        "training_families": sorted(training.circuit_family.unique().tolist()),
        "training_label_counts": {str(k): int(v) for k, v in zip(*np.unique(y, return_counts=True))},
        "training_manifest_sha256": file_sha256(training_manifest_path),
        "qiskit_csv_sha256": file_sha256(qiskit_csv.resolve()),
        "tket_csv_sha256": file_sha256(tket_csv.resolve()),
        "heldout_manifest_sha256": file_sha256(held_manifest_path),
        "heldout_features_sha256": file_sha256(held_feature_path),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "source_sha256": file_sha256(Path(__file__).resolve()),
    })
    _write_atomic(model_path, json.dumps(model_record, indent=2, sort_keys=True))
    seal_record = {
        "status": "SEALED_BEFORE_HELDOUT_OPTIMIZATION",
        "prediction_sha256": file_sha256(prediction_path),
        "model_sha256": file_sha256(model_path),
        "training_packet_sha256": file_sha256(training_path),
        "heldout_manifest_sha256": file_sha256(held_manifest_path),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
    }
    seal_path = prediction_dir / "SEALED.json"
    _write_atomic(seal_path, json.dumps(seal_record, indent=2, sort_keys=True))
    print(f"Sealed {len(predictions)} held-out predictions -> {seal_path}")
    return seal_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["prepare", "seal"], required=True)
    parser.add_argument("--output-root", type=Path, default=OUT_ROOT)
    parser.add_argument("--training-manifest", type=Path)
    parser.add_argument("--qiskit-csv", type=Path)
    parser.add_argument("--tket-csv", type=Path)
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare(args.output_root.resolve())
    elif args.phase == "seal":
        if not all((args.training_manifest, args.qiskit_csv, args.tket_csv)):
            parser.error("seal requires --training-manifest --qiskit-csv --tket-csv")
        seal(args.output_root.resolve(), args.training_manifest,
             args.qiskit_csv, args.tket_csv)


if __name__ == "__main__":
    main()
