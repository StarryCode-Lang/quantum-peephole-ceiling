"""Tests for listing-preserving P3 pilot helpers."""

from qiskit import QuantumCircuit
import pandas as pd
import pytest

from analysis.e31_listing_phase2b_analysis import compute_contrasts
from experiments.e31_listing_phase2b_interaction import random_topological_listing
from src.circuits.real_benchmarks import average_gate_fidelity


def test_random_topological_listing_preserves_unitary_and_gate_count():
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.x(1)
    circuit.z(0)

    relisted = random_topological_listing(circuit, seed=7)

    assert relisted.size() == circuit.size()
    assert average_gate_fidelity(relisted, circuit, max_qubits=2) == pytest.approx(1.0)


def test_compute_contrasts_uses_paired_phase_differences():
    rows = []
    values = {
        "c1": {
            "LBL": {"phase1": 0.1, "phase2a": 0.2, "phase2b": 0.4},
            "WCL": {"phase1": 0.2, "phase2a": 0.3, "phase2b": 0.7},
            "SHUFFLE": {"phase1": 0.1, "phase2a": 0.2, "phase2b": 0.4},
        },
        "c2": {
            "LBL": {"phase1": 0.2, "phase2a": 0.3, "phase2b": 0.5},
            "WCL": {"phase1": 0.3, "phase2a": 0.5, "phase2b": 0.8},
            "SHUFFLE": {"phase1": 0.2, "phase2a": 0.3, "phase2b": 0.5},
        },
    }
    for circuit_id, listings in values.items():
        for listing_model, phases in listings.items():
            for phase, reduction in phases.items():
                rows.append({
                    "circuit_id": circuit_id,
                    "circuit_family": "Synthetic",
                    "listing_model": listing_model,
                    "phase": phase,
                    "reduction": reduction,
                })

    contrasts = compute_contrasts(pd.DataFrame(rows))
    result = contrasts.query(
        "listing_model == 'WCL' and contrast == 'phase2b_over_phase1'"
    ).iloc[0]

    assert result["n_circuits"] == 2
    assert result["mean"] == pytest.approx(0.2)
