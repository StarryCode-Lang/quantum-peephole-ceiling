"""Regressions for SOTA schema 1.1 resource and Pareto metrics."""

import inspect

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit

from analysis.prepaper_rq3_tool_comparison import KEY, _pareto_tables
from experiments.sota_benchmark import PersistentOptimizerWorker, build_row, count_metrics


def _small_worker_payload(value):
    # Module-level so Windows multiprocessing spawn can import it by name.
    return value + 1


def test_two_qubit_depth_counts_only_entangling_layers():
    circuit = QuantumCircuit(4)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(2, 3)  # parallel with the preceding CX
    circuit.x(0)
    circuit.cx(0, 2)  # depends on the first layer

    metrics = count_metrics(circuit)

    assert metrics["two_q_count"] == 3
    assert metrics["two_q_depth"] == 2
    assert metrics["depth"] >= metrics["two_q_depth"]


def test_new_resource_fields_default_to_unavailable_not_zero():
    signature = inspect.signature(build_row)
    fields = (
        "parse_elapsed_seconds",
        "input_normalization_elapsed_seconds",
        "verification_elapsed_seconds",
        "output_normalization_elapsed_seconds",
        "optimizer_cpu_seconds",
        "optimizer_peak_rss_bytes",
        "pipeline_elapsed_seconds",
    )
    for field in fields:
        assert np.isnan(signature.parameters[field].default)


def test_worker_reports_cpu_and_sampled_process_tree_rss():
    worker = PersistentOptimizerWorker(_small_worker_payload)
    try:
        payload, elapsed, wall, status, cpu, peak_rss = worker.run(2, timeout=20)
    finally:
        worker.close()
    assert payload == 3
    assert status == "ok"
    assert elapsed >= 0 and wall >= elapsed and cpu >= 0
    assert peak_rss > 0


def test_quality_runtime_pareto_excludes_invalid_and_missing_runtime():
    rows = []
    specs = {
        "custom": (1, 10.0, 2.0),
        "qiskit": (1, 12.0, 1.0),  # dominates custom
        "cirq": (1, 20.0, 3.0),    # quality/runtime trade-off: frontier
        "tket": (0, 0.0, np.nan),  # visible, never imputed or eligible
    }
    for tool, (valid, quality, runtime) in specs.items():
        row = dict(zip(KEY, ["c1", 0, 42, "sha"])); row.update({
            "circuit_family": "F",
            "tool_label": tool,
            "valid": valid,
            "common_reduction_itt": quality,
            "optimizer_elapsed_seconds": runtime,
        })
        rows.append(row)

    frontier, summary, pairwise = _pareto_tables(pd.DataFrame(rows))

    statuses = dict(zip(frontier.tool, frontier.pareto_status))
    assert statuses == {
        "custom": "dominated",
        "qiskit": "frontier",
        "cirq": "frontier",
        "tket": "unavailable_invalid_or_runtime",
    }
    tket = summary.loc[summary.tool == "tket"].iloc[0]
    assert tket.pareto_eligible_n == 0
    qiskit_custom = pairwise[
        (pairwise.tool_first == "qiskit") & (pairwise.tool_second == "custom")
    ].iloc[0]
    assert qiskit_custom.first_dominates_n == 1
