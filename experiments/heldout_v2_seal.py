"""Prepare and seal an outcome-blind heldout-v2 input packet.

This file has no optimizer entry point.  It generates new mechanisms, audits
their names/source hashes and circuit hashes against the fixed training and v1
held-out packets, applies the already-sealed v1 classifier parameters, and
seals predictions before any optimizer may consume the manifest.
"""

from __future__ import annotations

import ast
import inspect
import json
import shutil
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit, qasm2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.predictive_advantage import extract_structural_features
from experiments import prepaper_heldout as heldout_v1
from src.circuits.real_benchmarks import circuit_sha256
from src.provenance import file_sha256

VERSION = "2.0.0"
BASE_SEED = 2026081101
SIZES = (4, 6, 8)
TRIALS = 8
OUT_ROOT = PROJECT_ROOT / "data" / "v10" / "prepaper" / "heldout_v2"
PROTOCOL_PATH = PROJECT_ROOT / "experiments" / "heldout_v2_protocol.json"
TRAINING_MANIFEST = PROJECT_ROOT / "data" / "v10" / "prepaper" / "sota" / "inputs" / "benchmark_manifest.csv"
V1_ROOT = PROJECT_ROOT / "data" / "v10" / "prepaper" / "heldout"
V1_MANIFEST = V1_ROOT / "inputs" / "benchmark_manifest.csv"
V1_MODEL = V1_ROOT / "sealed_predictions" / "model.json"
V1_SEAL = V1_ROOT / "sealed_predictions" / "SEALED.json"


def _fermionic_hopping_ring(n: int, seed: int) -> QuantumCircuit:
    """Number-conserving hopping layers on alternating ring matchings."""
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    qc.x(int(rng.integers(n)))
    for layer in range(4):
        for q in range(layer % 2, n - 1, 2):
            theta = float(rng.uniform(0.15, 1.25))
            qc.rxx(theta, q, q + 1)
            qc.ryy(theta, q, q + 1)
        qc.rz(float(rng.uniform(-0.8, 0.8)), layer % n)
    qc.swap(0, n - 1)
    return qc


def _hypergraph_phase_state(n: int, seed: int) -> QuantumCircuit:
    """Random weighted two- and three-body hypergraph phase state."""
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    qc.h(range(n))
    order = rng.permutation(n)
    for i in range(n):
        a, b = int(order[i]), int(order[(i + 1) % n])
        qc.cp(float(rng.uniform(-np.pi, np.pi)), a, b)
    for i in range(max(2, n // 2)):
        controls = [int(order[i % n]), int(order[(i + 1) % n])]
        target = int(order[(i + 2) % n])
        # Express the three-body conditional phase with stable primitive names.
        # Qiskit's OpenQASM 2 exporter otherwise gives repeated ``mcp``
        # definitions process-specific suffixes, breaking cross-process hashes.
        qc.ccx(controls[0], controls[1], target)
        qc.p(float(rng.uniform(-1.2, 1.2)), target)
        qc.ccx(controls[0], controls[1], target)
    return qc


def _reversible_cellular_automaton(n: int, seed: int) -> QuantumCircuit:
    """Staggered local reversible Boolean update rule on a periodic line."""
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    for q in np.flatnonzero(rng.integers(0, 2, size=n)):
        qc.x(int(q))
    for step in range(5):
        for center in range(step % 2, n, 2):
            left, right = (center - 1) % n, (center + 1) % n
            if len({left, center, right}) == 3:
                qc.ccx(left, right, center)
        qc.rz(float(rng.uniform(-0.4, 0.4)), step % n)
    return qc


def _permutation_interferometer(n: int, seed: int) -> QuantumCircuit:
    """Random wire permutation embedded between two phase-sensitive bases."""
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    for q in range(n):
        qc.ry(float(rng.uniform(-np.pi, np.pi)), q)
    permutation = list(map(int, rng.permutation(n)))
    current = list(range(n))
    for destination, value in enumerate(permutation):
        source = current.index(value)
        if source != destination:
            qc.swap(destination, source)
            current[destination], current[source] = current[source], current[destination]
    for q in range(n):
        qc.rz(float(rng.uniform(-np.pi, np.pi)), q)
        qc.h(q)
    return qc


def _signal_processing_sequence(n: int, seed: int) -> QuantumCircuit:
    """Single-signal alternating controlled-rotation phase sequence."""
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    signal = int(rng.integers(n))
    qc.h(signal)
    targets = [q for q in range(n) if q != signal]
    rng.shuffle(targets)
    for repetition in range(3):
        for target in targets:
            qc.cry(float(rng.uniform(-1.5, 1.5)), signal, target)
            qc.crz(float(rng.uniform(-1.5, 1.5)), target, signal)
        qc.rz(float(rng.uniform(-np.pi, np.pi)), signal)
        if repetition % 2 == 0:
            qc.x(signal)
    return qc


def _linear_reversible_network(n: int, seed: int) -> QuantumCircuit:
    """Random full-rank GF(2) row-operation network with phase tags."""
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    for _ in range(5 * n):
        control, target = map(int, rng.choice(n, 2, replace=False))
        qc.cx(control, target)
    for q in range(n):
        if rng.random() < 0.65:
            qc.s(q)
        if rng.random() < 0.35:
            qc.x(q)
    return qc


def _butterfly_mixing_network(n: int, seed: int) -> QuantumCircuit:
    """Long-range radix-two butterfly mixing rather than nearest-neighbour layers."""
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    stride = 1
    while stride < n:
        for start in range(0, n, 2 * stride):
            for offset in range(stride):
                a, b = start + offset, start + offset + stride
                if b < n:
                    qc.h(a)
                    qc.cx(a, b)
                    qc.rz(float(rng.uniform(-np.pi, np.pi)), b)
        stride *= 2
    for q in map(int, rng.permutation(n)):
        qc.t(q) if rng.random() < 0.5 else qc.tdg(q)
    return qc


def _coherent_clause_network(n: int, seed: int) -> QuantumCircuit:
    """Compute-phase-uncompute network for random reversible Boolean clauses."""
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    work = n - 1
    data = list(range(n - 1))
    qc.h(data)
    clauses: list[tuple[int, int]] = []
    for _ in range(max(3, 2 * (n - 2))):
        a, b = map(int, rng.choice(data, 2, replace=False))
        clauses.append((a, b))
        qc.ccx(a, b, work)
        qc.rz(float(rng.uniform(-1.0, 1.0)), work)
    for a, b in reversed(clauses):
        qc.ccx(a, b, work)
    return qc


GENERATORS: dict[str, Callable[[int, int], QuantumCircuit]] = {
    "FermionicHoppingRing": _fermionic_hopping_ring,
    "HypergraphPhaseState": _hypergraph_phase_state,
    "ReversibleCellularAutomaton": _reversible_cellular_automaton,
    "PermutationInterferometer": _permutation_interferometer,
    "SignalProcessingSequence": _signal_processing_sequence,
    "LinearReversibleNetwork": _linear_reversible_network,
    "ButterflyMixingNetwork": _butterfly_mixing_network,
    "CoherentClauseNetwork": _coherent_clause_network,
}


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _portable(circuit: QuantumCircuit) -> QuantumCircuit:
    # Repeated parameterized RXX/RYY definitions receive process-specific
    # OpenQASM gate-name suffixes in Qiskit 2.4.1. Decompose those two gates
    # before serialization so the sealed QASM bytes are reproducible.
    stable = circuit.decompose(gates_to_decompose=["rxx", "ryy"])
    return qasm2.loads(qasm2.dumps(stable), custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)


def _ast_hash(function: Callable[..., QuantumCircuit]) -> str:
    source = textwrap.dedent(inspect.getsource(function))
    normalized = ast.dump(ast.parse(source), annotate_fields=True, include_attributes=False)
    import hashlib
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _fixed_model_predictions(features: pd.DataFrame, model: dict) -> tuple[np.ndarray, np.ndarray]:
    feature_names = list(model["features"])
    matrix = features[feature_names].replace([np.inf, -np.inf], np.nan).to_numpy(float)
    imputer = np.asarray(model["imputer_statistics"], dtype=float)
    missing = np.where(np.isnan(matrix))
    matrix[missing] = imputer[missing[1]]
    standardized = (matrix - np.asarray(model["scaler_mean"], dtype=float)) / np.asarray(
        model["scaler_scale"], dtype=float
    )
    logits = standardized @ np.asarray(model["coefficients"], dtype=float).T
    logits = logits[:, 0] + float(model["intercept"][0])
    probability = 1.0 / (1.0 + np.exp(-np.clip(logits, -700, 700)))
    prediction = (probability >= float(model["threshold"])).astype(np.int8)
    return probability, prediction


def prepare_and_seal(output_root: Path = OUT_ROOT) -> Path:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    v1_seal = json.loads(V1_SEAL.read_text(encoding="utf-8"))
    if v1_seal.get("status") != "SEALED_BEFORE_HELDOUT_OPTIMIZATION":
        raise RuntimeError("v1 model packet is not sealed")
    if file_sha256(V1_MODEL) != str(v1_seal["model_sha256"]):
        raise RuntimeError("v1 model SHA differs from its seal")
    if file_sha256(TRAINING_MANIFEST) != protocol["fixed_inputs"]["training_manifest_sha256"]:
        raise RuntimeError("training manifest changed from heldout-v2 protocol")
    if file_sha256(V1_MANIFEST) != protocol["fixed_inputs"]["v1_heldout_manifest_sha256"]:
        raise RuntimeError("v1 held-out manifest changed from heldout-v2 protocol")
    if file_sha256(V1_MODEL) != protocol["fixed_model"]["sha256"]:
        raise RuntimeError("fixed model changed from heldout-v2 protocol")
    if (output_root / "results").exists():
        raise RuntimeError("optimizer result directory exists; refusing pre-outcome seal")

    training = pd.read_csv(TRAINING_MANIFEST)
    old_heldout = pd.read_csv(V1_MANIFEST)
    old_families = set(training["circuit_family"].astype(str)) | set(
        old_heldout["circuit_family"].astype(str)
    )
    family_overlap = sorted(old_families & set(GENERATORS))
    if family_overlap:
        raise RuntimeError(f"heldout-v2 family-name overlap: {family_overlap}")

    old_ast = {name: _ast_hash(function) for name, function in heldout_v1.GENERATORS.items()}
    new_ast = {name: _ast_hash(function) for name, function in GENERATORS.items()}
    ast_overlap = sorted(set(old_ast.values()) & set(new_ast.values()))
    if ast_overlap:
        raise RuntimeError("heldout-v2 generator AST duplicates a v1 generator")

    old_input_hashes = set(training["input_circuit_sha256"].astype(str)) | set(
        old_heldout["input_circuit_sha256"].astype(str)
    )
    qasm_dir = output_root / "inputs" / "qasm"
    rows: list[dict] = []
    feature_rows: list[dict] = []
    for family_index, (family, generator) in enumerate(GENERATORS.items()):
        for n in SIZES:
            for trial in range(TRIALS):
                seed = BASE_SEED + 10000 * family_index + 100 * n + trial
                circuit = _portable(generator(n, seed))
                input_hash = circuit_sha256(circuit)
                circuit_id = f"heldout_v2_{family.lower()}_n{n}_t{trial}"
                qasm_path = qasm_dir / f"{circuit_id}_{input_hash[:12]}.qasm"
                _atomic_text(qasm_path, qasm2.dumps(circuit))
                row = {
                    "schema_version": "2.0.0",
                    "suite": "prepaper_heldout_v2",
                    "circuit_id": circuit_id,
                    "circuit_family": family,
                    "mechanism_id": protocol["families"][family]["mechanism_id"],
                    "n_qubits": circuit.num_qubits,
                    "trial": trial,
                    "seed": seed,
                    "input_circuit_sha256": input_hash,
                    "qasm_sha256": file_sha256(qasm_path),
                    "qasm_path": qasm_path.relative_to(PROJECT_ROOT).as_posix(),
                }
                rows.append(row)
                extracted = extract_structural_features(circuit)
                extracted["log1p_n_gates"] = float(np.log1p(extracted["n_gates"]))
                feature_rows.append({
                    **{key: row[key] for key in (
                        "circuit_id", "circuit_family", "mechanism_id", "n_qubits",
                        "trial", "seed", "input_circuit_sha256",
                    )},
                    **extracted,
                })

    manifest = pd.DataFrame(rows).sort_values(
        ["circuit_family", "n_qubits", "trial"], kind="stable"
    ).reset_index(drop=True)
    features = pd.DataFrame(feature_rows).sort_values(
        ["circuit_family", "n_qubits", "trial"], kind="stable"
    ).reset_index(drop=True)
    expected = len(GENERATORS) * len(SIZES) * TRIALS
    if len(manifest) != expected:
        raise RuntimeError("heldout-v2 row count mismatch")
    if manifest["input_circuit_sha256"].nunique() != expected:
        duplicates = manifest[manifest.duplicated("input_circuit_sha256", keep=False)]
        raise RuntimeError(f"heldout-v2 input hashes are not globally unique: {len(duplicates)} rows")
    cross_hash_overlap = sorted(set(manifest["input_circuit_sha256"]) & old_input_hashes)
    if cross_hash_overlap:
        raise RuntimeError(f"heldout-v2 input hash overlaps prior packet: {cross_hash_overlap[:3]}")
    if manifest["mechanism_id"].nunique() != len(GENERATORS):
        raise RuntimeError("mechanism IDs are not one-to-one with new families")

    input_dir = output_root / "inputs"
    manifest_path = input_dir / "benchmark_manifest.csv"
    features_path = input_dir / "preoptimization_features.csv"
    _atomic_text(manifest_path, manifest.to_csv(index=False))
    _atomic_text(features_path, features.to_csv(index=False))

    model = json.loads(V1_MODEL.read_text(encoding="utf-8"))
    probability, prediction = _fixed_model_predictions(features, model)
    predictions = features[[
        "circuit_id", "circuit_family", "mechanism_id", "n_qubits", "trial",
        "seed", "input_circuit_sha256", "n_gates",
    ]].copy()
    predictions["predicted_probability_joint_external_headroom"] = probability
    predictions["predicted_joint_external_headroom"] = prediction

    sealed_dir = output_root / "sealed_predictions"
    prediction_path = sealed_dir / "heldout_v2_predictions.csv"
    model_copy = sealed_dir / "model.json"
    _atomic_text(prediction_path, predictions.to_csv(index=False))
    model_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(V1_MODEL, model_copy)

    audit = {
        "status": "PASS_BEFORE_ANY_HELDOUT_V2_OPTIMIZATION",
        "new_family_count": len(GENERATORS),
        "new_families": list(GENERATORS),
        "training_families": sorted(set(training["circuit_family"].astype(str))),
        "v1_heldout_families": sorted(set(old_heldout["circuit_family"].astype(str))),
        "family_name_overlap": family_overlap,
        "generator_ast_overlap": ast_overlap,
        "new_generator_ast_sha256": new_ast,
        "v1_generator_ast_sha256": old_ast,
        "input_hash_overlap_count": len(cross_hash_overlap),
        "new_execution_rows": len(manifest),
        "new_unique_input_hashes": int(manifest["input_circuit_sha256"].nunique()),
        "per_family_unique_inputs": {
            str(key): int(value) for key, value in manifest.groupby("circuit_family")[
                "input_circuit_sha256"
            ].nunique().items()
        },
        "mechanism_rationale": protocol["families"],
    }
    audit_path = sealed_dir / "generator_overlap_audit.json"
    _atomic_text(audit_path, json.dumps(audit, indent=2, sort_keys=True))

    sealed_at = datetime.now(timezone.utc).isoformat()
    seal = {
        "schema_version": "2.0.0",
        "status": "SEALED_BEFORE_HELDOUT_V2_OPTIMIZATION",
        "sealed_at_utc": sealed_at,
        "optimizer_outcomes_present_at_seal": False,
        "manifest_sha256": file_sha256(manifest_path),
        "features_sha256": file_sha256(features_path),
        "predictions_sha256": file_sha256(prediction_path),
        "model_sha256": file_sha256(model_copy),
        "parent_model_sha256": file_sha256(V1_MODEL),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "generator_overlap_audit_sha256": file_sha256(audit_path),
        "source_sha256": file_sha256(Path(__file__).resolve()),
        "training_manifest_sha256": file_sha256(TRAINING_MANIFEST),
        "v1_heldout_manifest_sha256": file_sha256(V1_MANIFEST),
        "n_families": len(GENERATORS),
        "n_rows": len(manifest),
        "n_unique_inputs": int(manifest["input_circuit_sha256"].nunique()),
    }
    seal_path = sealed_dir / "SEALED.json"
    _atomic_text(seal_path, json.dumps(seal, indent=2, sort_keys=True))
    print(json.dumps(seal, indent=2, sort_keys=True))
    return seal_path


def verify_seal(output_root: Path = OUT_ROOT) -> dict:
    """Verify that every sealed input-stage artifact is unchanged."""
    seal_path = output_root / "sealed_predictions" / "SEALED.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    if seal.get("status") != "SEALED_BEFORE_HELDOUT_V2_OPTIMIZATION":
        raise RuntimeError("heldout-v2 seal status is invalid")
    paths = {
        "manifest_sha256": output_root / "inputs" / "benchmark_manifest.csv",
        "features_sha256": output_root / "inputs" / "preoptimization_features.csv",
        "predictions_sha256": output_root / "sealed_predictions" / "heldout_v2_predictions.csv",
        "model_sha256": output_root / "sealed_predictions" / "model.json",
        "protocol_sha256": PROTOCOL_PATH,
        "generator_overlap_audit_sha256": output_root / "sealed_predictions" / "generator_overlap_audit.json",
        "source_sha256": Path(__file__).resolve(),
        "training_manifest_sha256": TRAINING_MANIFEST,
        "v1_heldout_manifest_sha256": V1_MANIFEST,
    }
    mismatches = {
        key: {"sealed": seal.get(key), "actual": file_sha256(path)}
        for key, path in paths.items()
        if seal.get(key) != file_sha256(path)
    }
    if mismatches:
        raise RuntimeError(f"heldout-v2 sealed hash mismatch: {mismatches}")
    manifest = pd.read_csv(paths["manifest_sha256"])
    if len(manifest) != int(seal["n_rows"]):
        raise RuntimeError("heldout-v2 sealed row count mismatch")
    if manifest["input_circuit_sha256"].nunique() != int(seal["n_unique_inputs"]):
        raise RuntimeError("heldout-v2 sealed uniqueness mismatch")
    if (output_root / "results").exists():
        raise RuntimeError("optimizer result directory now exists; sealed-input-only status no longer applies")
    return {
        "status": "VERIFIED_SEALED_INPUT_ONLY",
        "seal_sha256": file_sha256(seal_path),
        "sealed_at_utc": seal["sealed_at_utc"],
        "n_families": int(seal["n_families"]),
        "n_rows": int(seal["n_rows"]),
        "n_unique_inputs": int(seal["n_unique_inputs"]),
    }


if __name__ == "__main__":
    prepare_and_seal()
    print(json.dumps(verify_seal(), indent=2, sort_keys=True))
