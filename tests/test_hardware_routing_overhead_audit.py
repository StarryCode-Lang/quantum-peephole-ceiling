import json

import pandas as pd
from qiskit import QuantumCircuit
from qiskit_ibm_runtime.fake_provider import FakeManilaV2

from analysis.hardware_routing_overhead_audit import (
    DEFAULT_OUTPUT_DIR,
    logical_communication_counts,
)


def test_logical_communication_counts_distinguishes_remote_pair():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 1)
    circuit.cx(0, 3)
    counts = logical_communication_counts(circuit, FakeManilaV2())
    assert counts["logical_2q_gates"] == 2
    assert counts["identity_layout_nonlocal_2q_gates"] == 1
    assert counts["identity_layout_excess_edge_hops"] > 0


def test_generated_hardware_routing_audit_is_complete():
    report = json.loads(
        (DEFAULT_OUTPUT_DIR / "hardware_routing_overhead_audit.json").read_text(
            encoding="utf-8"
        )
    )
    cells = pd.read_csv(DEFAULT_OUTPUT_DIR / "hardware_routing_cells.csv")
    assert report["status"] == "PASS_BOUNDED_FAKE_BACKEND_ROUTING_AUDIT"
    assert report["design"]["design_cells"] == 48
    assert report["design"]["all_archived_routing_cells_replayed_exactly"] is True
    assert len(cells) == 48
    assert (cells.query("transpile_optimization_level == 0")[
        "routing_native_2q_gate_overhead"
    ] >= 0).all()
    assert report["metric_dispositions"]["9.14"].startswith("PASS:")
    assert report["metric_dispositions"]["9.16"].startswith("PASS:")
    physical = report["physical_native_2q_reduction_vs_original"]
    assert physical["paired_cells"] == 36
    assert physical["all_paired_increases_absent"] is True
    by_version = {row["version"]: row for row in physical["by_version"]}
    assert by_version["greedy_phase1"]["reduced_cells"] == 0
    for version in ("commutation_phase2", "hybrid_phase1_2"):
        assert by_version[version]["paired_cells"] == 12
        assert by_version[version]["reduced_cells"] == 4
        assert by_version[version]["equal_cells"] == 8
        assert by_version[version]["increased_cells"] == 0
        assert by_version[version]["reduction_gate_range"] == [0, 2]
    assert report["metric_dispositions"]["16.17"].startswith("PARTIAL:")
