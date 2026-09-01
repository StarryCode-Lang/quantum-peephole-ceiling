import json
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit, transpile

from experiments import heldout_v2_execute as execute
from experiments.sota_benchmark import load_benchmark_manifest
from src.circuits.real_benchmarks import average_gate_fidelity


def test_execution_protocol_matches_sealed_manifest_and_runner():
    seal, protocol = execute._verify_immutable_packet()
    manifest = pd.read_csv(execute.MANIFEST)
    assert seal["optimizer_outcomes_present_at_seal"] is False
    assert len(manifest) == protocol["expected_rows_per_tool"] == 192
    assert manifest.input_circuit_sha256.nunique() == protocol["required_unique_input_hashes"] == 192
    assert protocol["tool_order"] == ["custom", "qiskit", "cirq", "tket"]
    assert protocol["worker_count"] == 1
    assert protocol["timeout_seconds_per_input"] == 120


def test_execution_protocol_freezes_analysis_without_refit():
    protocol = json.loads(execute.PROTOCOL_PATH.read_text(encoding="utf-8"))
    analysis = protocol["analysis"]
    assert analysis["classifier_threshold"] == 0.5
    assert analysis["refit_allowed"] is False
    assert analysis["feature_change_allowed"] is False
    assert analysis["combined_outer_families"] == 16


def test_completed_combined_packet_satisfies_independent_family_expansion():
    metrics_path = execute.ROOT / "analysis" / "combined_heldout_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["outer_clusters"] == 16
    assert metrics["n_unique_inputs"] == 378
    assert metrics["model_refit"] is False
    assert metrics["feature_or_threshold_change"] is False
    assert metrics["metric_dispositions"]["18.03"].startswith("PASS:")


def test_fresh_metadata_source_contract_is_declared_in_executor():
    source = Path(execute.__file__).read_text(encoding="utf-8")
    assert '"layout_aware_qiskit_final_layout": True' in source
    assert '"reason": "layout_aware_equivalence_rerun"' in source
    assert '"src/equivalence.py": equivalence_sha' in source


def test_sealed_v2_manifest_round_trips_through_shared_runner_loader():
    loaded, manifest_sha = load_benchmark_manifest(execute.MANIFEST)
    assert len(loaded) == 192
    assert manifest_sha == json.loads(execute.SEAL_PATH.read_text(encoding="utf-8"))["manifest_sha256"]
    assert all(item[0].circuit_type != "unspecified" for item in loaded)


def test_exact_fidelity_honors_transpiler_final_layout():
    circuit = QuantumCircuit(4)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.swap(0, 3)
    optimized = transpile(circuit, optimization_level=3, seed_transpiler=19)
    assert optimized.layout is not None
    assert optimized.layout.final_layout is not None
    assert average_gate_fidelity(optimized, circuit) > 1.0 - 1e-10


def test_exact_fidelity_honors_random_output_permutations():
    rng = np.random.default_rng(20260811)
    for n_qubits in (4, 6, 8):
        for trial in range(4):
            circuit = QuantumCircuit(n_qubits)
            for qubit in range(n_qubits):
                circuit.ry(float(rng.uniform(-np.pi, np.pi)), qubit)
            permutation = list(map(int, rng.permutation(n_qubits)))
            current = list(range(n_qubits))
            for destination, value in enumerate(permutation):
                source = current.index(value)
                if source != destination:
                    circuit.swap(destination, source)
                    current[destination], current[source] = current[source], current[destination]
            optimized = transpile(circuit, optimization_level=3, seed_transpiler=trial)
            assert average_gate_fidelity(optimized, circuit) > 1.0 - 1e-10
