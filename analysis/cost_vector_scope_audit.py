"""Reconstruct bounded T-depth and audit hardware-aware cost-vector coverage.

This audit deliberately separates three scopes:

* the native Clifford+T E18 panel, where a dependency-preserving circuit
  T-stage depth is meaningful and every emitted circuit can be reconstructed;
* the archived fake-backend calibration-snapshot simulation, where native
  counts and scheduled duration are directly recorded but no real-QPU claim is
  licensed; and
* the fixed-width unitary E31 panel, where all declared input wires are live
  for the complete unitary contract and dynamic/classical costs are out of
  scope rather than silently reported as zero-cost hardware features.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
E18_RESULTS = (
    ROOT
    / "data/v10/prepaper/e18/e18_clifford_t_e18_full_20260809_172558.csv"
)
E18_METADATA = ROOT / "data/v10/prepaper/e18/metadata.json"
HARDWARE_RUNS = (
    ROOT
    / "data/v10/prepaper/hardware_validation/ehw_runs_full_20260811_123958.csv"
)
HARDWARE_METADATA = (
    ROOT
    / "data/v10/prepaper/hardware_validation/ehw_metadata_full_20260811_123958.json"
)
E31_STRUCTURAL = (
    ROOT
    / "data/v11/e31_factorial_pareto/formal_run/"
    "postseal_structural_distribution_metrics/semantic_cell_structural_metrics.csv"
)
DEFAULT_OUTPUT_DIR = ROOT / "data/v10/prepaper/analysis/cost_vector_scope"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dependency_preserving_t_depth(circuit) -> int:
    """Return T/TDG stage depth while preserving all circuit dependencies.

    Clifford operations do not themselves add a T stage, but a multi-qubit
    Clifford propagates the largest predecessor stage to every participating
    wire.  Thus disjoint T gates can share a stage, while a causal T--Clifford--T
    chain cannot.  This is an emitted-circuit schedule metric, not a globally
    minimized synthesis optimum or a surface-code resource estimate.
    """

    stages = [0] * int(circuit.num_qubits)
    maximum = 0
    for instruction in circuit.data:
        qubits = [circuit.find_bit(bit).index for bit in instruction.qubits]
        if not qubits:
            continue
        predecessor = max(stages[index] for index in qubits)
        stage = predecessor + int(
            str(instruction.operation.name).lower() in {"t", "tdg"}
        )
        for index in qubits:
            stages[index] = stage
        maximum = max(maximum, stage)
    return int(maximum)


def _e18_optimizers() -> dict[str, object]:
    from src.optimisation.phase1.greedy import GreedyGateCancellation
    from src.optimisation.phase2.commutation_rewriter import (
        CommutationRewriter,
        HybridCommuteRewrite,
    )

    return {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "commutation_phase2": CommutationRewriter(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }


def reconstruct_e18_t_depth(results_path: Path) -> tuple[pd.DataFrame, dict]:
    from experiments.e18_clifford_t.run import generate_clifford_t_suite
    from src.circuits.real_benchmarks import circuit_sha256

    source = pd.read_csv(results_path)
    required = {
        "circuit_id",
        "circuit_family",
        "optimizer",
        "input_circuit_sha256",
        "output_circuit_sha256",
        "baseline_t_count",
        "optimized_t_count",
        "valid_equivalent_output",
        "status",
    }
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"E18 missing required fields: {missing}")
    if len(source) != 1080 or source.duplicated(["circuit_id", "optimizer"]).any():
        raise ValueError("E18 must contain 1,080 unique circuit x optimizer rows")

    circuits = generate_clifford_t_suite(mode="full", seed=42)
    if len(circuits) != 360:
        raise ValueError("E18 reconstruction did not yield 360 circuits")
    indexed = source.set_index(["circuit_id", "optimizer"], verify_integrity=True)
    rows: list[dict] = []
    for benchmark in circuits:
        input_hash = circuit_sha256(benchmark.circuit)
        baseline_t_depth = dependency_preserving_t_depth(benchmark.circuit)
        for optimizer_name, optimizer in _e18_optimizers().items():
            key = (benchmark.circuit_id, optimizer_name)
            if key not in indexed.index:
                raise ValueError(f"E18 row missing for {key}")
            recorded = indexed.loc[key]
            if input_hash != recorded["input_circuit_sha256"]:
                raise ValueError(f"E18 input hash mismatch for {key}")
            result = optimizer.optimize(benchmark.circuit, target=benchmark.circuit)
            output = result.optimized_circuit
            output_hash = circuit_sha256(output)
            if output_hash != recorded["output_circuit_sha256"]:
                raise ValueError(f"E18 output reconstruction mismatch for {key}")
            if str(recorded["status"]) != "ok" or not bool(
                recorded["valid_equivalent_output"]
            ):
                raise ValueError(f"E18 non-valid row cannot support T-depth: {key}")
            optimized_t_depth = dependency_preserving_t_depth(output)
            rows.append(
                {
                    "circuit_id": benchmark.circuit_id,
                    "circuit_family": benchmark.family,
                    "n_qubits": int(benchmark.circuit.num_qubits),
                    "optimizer": optimizer_name,
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": output_hash,
                    "baseline_t_count": int(recorded["baseline_t_count"]),
                    "optimized_t_count": int(recorded["optimized_t_count"]),
                    "baseline_dependency_t_depth": baseline_t_depth,
                    "optimized_dependency_t_depth": optimized_t_depth,
                    "absolute_dependency_t_depth_change": (
                        optimized_t_depth - baseline_t_depth
                    ),
                    "relative_dependency_t_depth_reduction": (
                        0.0
                        if baseline_t_depth == 0
                        else 1.0 - optimized_t_depth / baseline_t_depth
                    ),
                    "historical_input_hash_reproduced": True,
                    "historical_output_hash_reproduced": True,
                    "recorded_exact_equivalence_valid": True,
                }
            )
    frame = pd.DataFrame(rows)
    if len(frame) != len(source):
        raise ValueError("E18 reconstruction row count differs from sealed results")
    grouped = []
    for optimizer, group in frame.groupby("optimizer", sort=True):
        eligible = group[group["baseline_dependency_t_depth"] > 0]
        grouped.append(
            {
                "optimizer": optimizer,
                "rows": int(len(group)),
                "rows_with_nonzero_baseline_t_depth": int(len(eligible)),
                "mean_baseline_dependency_t_depth": float(
                    group["baseline_dependency_t_depth"].mean()
                ),
                "mean_optimized_dependency_t_depth": float(
                    group["optimized_dependency_t_depth"].mean()
                ),
                "mean_relative_reduction_nonzero_baseline": float(
                    eligible["relative_dependency_t_depth_reduction"].mean()
                ),
                "regression_rows": int(
                    (group["absolute_dependency_t_depth_change"] > 0).sum()
                ),
            }
        )
    return frame, {
        "status": "PASS_RECONSTRUCTED_NATIVE_CLIFFORD_T_DEPENDENCY_DEPTH",
        "definition": (
            "maximum T/TDG stage on any emitted-circuit causal path; Clifford "
            "operations propagate but do not increment the stage"
        ),
        "n_native_clifford_t_inputs": int(frame["circuit_id"].nunique()),
        "n_reconstructed_rows": int(len(frame)),
        "n_families": int(frame["circuit_family"].nunique()),
        "n_qubits_min": int(frame["n_qubits"].min()),
        "n_qubits_max": int(frame["n_qubits"].max()),
        "all_historical_input_hashes_reproduced": True,
        "all_historical_output_hashes_reproduced": True,
        "all_rows_recorded_exact_equivalence_valid": True,
        "optimizer_summaries": grouped,
        "claim_boundary": (
            "This is exact for the recorded emitted-circuit dependency schedule. "
            "It is not globally minimized T-depth, magic-state factory demand, "
            "or a fault-tolerant architecture estimate."
        ),
    }


def audit_hardware_costs(runs_path: Path) -> dict:
    frame = pd.read_csv(runs_path)
    required = {
        "circuit_id",
        "version",
        "backend_name",
        "transpile_optimization_level",
        "seed_transpiler",
        "initial_layout_policy",
        "routing_method",
        "translation_method",
        "transpiled_2q_gates",
        "transpiled_2q_depth",
        "scheduled_duration_seconds",
        "calibration_success_probability",
        "shots",
        "sampler",
        "seed_simulator",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"hardware run missing required fields: {missing}")
    finite_columns = [
        "transpiled_2q_gates",
        "transpiled_2q_depth",
        "scheduled_duration_seconds",
        "calibration_success_probability",
    ]
    if not np.isfinite(frame[finite_columns].to_numpy(dtype=float)).all():
        raise ValueError("hardware cost vector contains non-finite values")
    if (frame["scheduled_duration_seconds"] <= 0).any():
        raise ValueError("scheduled duration must be positive")
    if not frame["calibration_success_probability"].between(0.0, 1.0).all():
        raise ValueError("calibration success probability is outside [0,1]")

    structural_key = [
        "circuit_id",
        "version",
        "backend_name",
        "transpile_optimization_level",
    ]
    structural_fields = [
        "seed_transpiler",
        "initial_layout_policy",
        "routing_method",
        "translation_method",
        "transpiled_2q_gates",
        "transpiled_2q_depth",
        "scheduled_duration_seconds",
        "calibration_success_probability",
    ]
    consistency = frame.groupby(structural_key)[structural_fields].nunique(dropna=False)
    if (consistency > 1).any().any():
        raise ValueError("hardware structural metrics vary across sampling repeats")
    cells = frame.drop_duplicates(structural_key)
    layout_values = sorted(cells["initial_layout_policy"].astype(str).unique())
    routing_values = sorted(cells["routing_method"].astype(str).unique())
    translation_values = sorted(cells["translation_method"].astype(str).unique())
    if layout_values != ["trivial_identity_on_logical_width"]:
        raise ValueError(f"unexpected layout policies: {layout_values}")
    if routing_values != ["sabre"] or translation_values != ["translator"]:
        raise ValueError("hardware comparison did not retain one routing/translation policy")

    return {
        "status": "PASS_BOUNDED_CALIBRATION_SNAPSHOT_COST_VECTOR",
        "run_rows": int(len(frame)),
        "structural_design_cells": int(len(cells)),
        "input_circuits": int(frame["circuit_id"].nunique()),
        "backend_snapshots": sorted(frame["backend_name"].unique()),
        "transpile_levels": sorted(
            int(value) for value in frame["transpile_optimization_level"].unique()
        ),
        "seed_transpiler": sorted(int(value) for value in frame["seed_transpiler"].unique()),
        "initial_layout_policy": layout_values,
        "routing_policy": routing_values,
        "translation_policy": translation_values,
        "native_2q_count_range": [
            int(cells["transpiled_2q_gates"].min()),
            int(cells["transpiled_2q_gates"].max()),
        ],
        "native_2q_depth_range": [
            int(cells["transpiled_2q_depth"].min()),
            int(cells["transpiled_2q_depth"].max()),
        ],
        "scheduled_duration_seconds_range": [
            float(cells["scheduled_duration_seconds"].min()),
            float(cells["scheduled_duration_seconds"].max()),
        ],
        "calibration_success_probability_range": [
            float(cells["calibration_success_probability"].min()),
            float(cells["calibration_success_probability"].max()),
        ],
        "noise_aware_cost_definition": "1 - calibration_success_probability",
        "shots": sorted(int(value) for value in frame["shots"].unique()),
        "sampling_seed_repeats": int(frame["seed_simulator"].nunique()),
        "samplers": sorted(frame["sampler"].unique()),
        "claim_boundary": (
            "Two qiskit fake-provider calibration snapshots and three circuits only; "
            "not a real-QPU, cross-device-transfer, queue-time, pulse, idle-time, "
            "or crosstalk measurement."
        ),
    }


def audit_fixed_unitary_scope(structural_path: Path) -> dict:
    frame = pd.read_csv(structural_path)
    required = {
        "declared_qubits",
        "active_qubits_static",
        "ancilla_qubits",
        "measurement_count",
        "reset_count",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"E31 structural audit missing fields: {missing}")
    no_dynamic = bool(
        (frame["measurement_count"] == 0).all()
        and (frame["reset_count"] == 0).all()
        and (frame["ancilla_qubits"] == 0).all()
    )
    if not no_dynamic:
        raise ValueError("E31 no longer satisfies the fixed-width unitary scope")
    cells_with_idle_declared_wires = int(
        (frame["active_qubits_static"] < frame["declared_qubits"]).sum()
    )
    return {
        "status": "PASS_FIXED_WIDTH_UNITARY_SCOPE_CLASSIFIED",
        "semantic_cells": int(len(frame)),
        "declared_qubit_range": [
            int(frame["declared_qubits"].min()),
            int(frame["declared_qubits"].max()),
        ],
        "cells_with_idle_declared_wires": cells_with_idle_declared_wires,
        "measurement_count_total": int(frame["measurement_count"].sum()),
        "reset_count_total": int(frame["reset_count"].sum()),
        "ancilla_qubits_total": int(frame["ancilla_qubits"].sum()),
        "peak_live_qubits_interpretation": (
            "Within the fixed-width unitary contract, every declared input wire (including "
            "an identity wire with no gates) is part of the input/output Hilbert space and "
            "must be preserved; peak stored live qubits therefore equals declared width."
        ),
        "dynamic_cost_disposition": (
            "classical feed-forward latency and dynamic-branch cost are not applicable "
            "to this benchmark scope; they are not asserted to be zero for dynamic circuits"
        ),
    }


def build_audit(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict:
    for path in (
        E18_RESULTS,
        E18_METADATA,
        HARDWARE_RUNS,
        HARDWARE_METADATA,
        E31_STRUCTURAL,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    metadata = json.loads(E18_METADATA.read_text(encoding="utf-8"))
    current_e18_source = ROOT / "experiments/e18_clifford_t/run.py"
    expected_source = metadata["source_hashes"]["experiments/e18_clifford_t/run.py"]
    if sha256(current_e18_source) != expected_source:
        raise ValueError("E18 experiment source differs from the archived run binding")

    t_depth, t_summary = reconstruct_e18_t_depth(E18_RESULTS)
    hardware = audit_hardware_costs(HARDWARE_RUNS)
    fixed_scope = audit_fixed_unitary_scope(E31_STRUCTURAL)
    output_dir.mkdir(parents=True, exist_ok=True)
    t_path = output_dir / "e18_dependency_t_depth.csv"
    t_depth.to_csv(t_path, index=False)
    report = {
        "schema_version": "1.0.0",
        "status": "PASS_BOUNDED_COST_VECTOR_AND_SCOPE_AUDIT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_bindings": {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in (
                E18_RESULTS,
                E18_METADATA,
                HARDWARE_RUNS,
                HARDWARE_METADATA,
                E31_STRUCTURAL,
                current_e18_source,
            )
        },
        "artifacts": {
            t_path.name: {"sha256": sha256(t_path), "rows": int(len(t_depth))}
        },
        "native_clifford_t": t_summary,
        "hardware_snapshot": hardware,
        "fixed_unitary_scope": fixed_scope,
        "metric_dispositions": {
            "9.08": "PASS: scheduled critical-path duration is directly reported for every bounded hardware design cell",
            "9.18": "PASS: peak live qubits equals declared width under the verified fixed-width unitary contract",
            "9.19": "NA: the evaluated circuits contain no measurement or classical feed-forward",
            "9.20": "NA: the evaluated circuits contain no dynamic branches",
            "9.22": "PASS: dependency-preserving T/TDG depth reconstructed for all 1,080 native Clifford+T rows",
            "14.03": "PASS: one identical initial-layout policy is enforced across compared versions",
            "14.07": "PASS: native two-qubit gate count is reported",
            "14.08": "PASS: native two-qubit depth is reported",
            "14.09": "PASS: scheduled duration is reported",
            "14.12": "PASS: fixed-snapshot product-of-gate-success proxy is reported with limitations",
            "14.13": "PASS: bounded noise-aware cost 1-p_success is defined and finite",
            "14.32": "NA: dynamic circuits are outside the frozen unitary benchmark scope",
        },
        "overall_claim_boundary": (
            "The artifact closes item-specific measurement gaps only in the recorded "
            "Clifford+T, fixed-width unitary, and fake-backend snapshot scopes. It does "
            "not license real-QPU, pulse-level, globally optimal fault-tolerant, or "
            "dynamic-circuit claims."
        ),
    }
    report_path = output_dir / "cost_vector_scope_audit.json"
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
