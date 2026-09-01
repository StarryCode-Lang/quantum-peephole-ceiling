"""Audit non-local two-qubit operations and routing overhead on frozen snapshots.

The analysis reconstructs every logical circuit version in the archived E-HW
packet, verifies its recorded circuit hash, and replays the frozen physical
mapping.  For each circuit/version/backend/transpiler-level cell it reports:

* logical two-qubit operations whose endpoints are non-adjacent under the
  declared identity initial layout;
* the corresponding excess shortest-path hop count; and
* a paired routing overhead relative to an all-to-all counterfactual using the
  same native basis, optimization level, and transpiler seed.

This is a deterministic compiler diagnostic on two Qiskit fake-provider
calibration snapshots.  It is not a real-QPU communication, pulse, or latency
measurement and is not extrapolated beyond the three archived circuits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from qiskit import transpile
from qiskit.transpiler import CouplingMap
from qiskit_ibm_runtime.fake_provider import FakeManilaV2, FakeNairobiV2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.hardware_validation.run import (  # noqa: E402
    SEED_TRANSPILER,
    build_circuits,
    build_optimizers,
    circuit_structural_metrics,
)
from src.circuits.real_benchmarks import circuit_sha256  # noqa: E402

RUNS = (
    ROOT
    / "data/v10/prepaper/hardware_validation/ehw_runs_full_20260811_123958.csv"
)
METADATA = (
    ROOT
    / "data/v10/prepaper/hardware_validation/ehw_metadata_full_20260811_123958.json"
)
EXPERIMENT_SOURCE = ROOT / "experiments/hardware_validation/run.py"
DEFAULT_OUTPUT_DIR = ROOT / "data/v10/prepaper/analysis/hardware_routing_overhead"
NATIVE_BASIS = ("rz", "sx", "x", "cx")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _undirected_coupling(backend) -> CouplingMap:
    edges = {tuple(map(int, edge)) for edge in backend.coupling_map}
    undirected = edges | {(target, source) for source, target in edges}
    return CouplingMap(sorted(undirected))


def logical_communication_counts(circuit, backend) -> dict[str, int]:
    """Count non-adjacent 2Q gates under the frozen identity placement."""

    coupling = _undirected_coupling(backend)
    total = 0
    nonlocal_count = 0
    excess_hops = 0
    maximum_distance = 0
    for instruction in circuit.data:
        if instruction.operation.num_qubits != 2:
            continue
        total += 1
        first, second = (
            circuit.find_bit(bit).index for bit in instruction.qubits
        )
        distance = int(coupling.distance(first, second))
        maximum_distance = max(maximum_distance, distance)
        if distance > 1:
            nonlocal_count += 1
            excess_hops += distance - 1
    return {
        "logical_2q_gates": total,
        "identity_layout_nonlocal_2q_gates": nonlocal_count,
        "identity_layout_excess_edge_hops": excess_hops,
        "identity_layout_max_2q_distance": maximum_distance,
    }


def _logical_versions() -> list[dict]:
    circuits, _ = build_circuits()
    optimizers = build_optimizers()
    versions: list[dict] = []
    for circuit_id, family, circuit in circuits:
        versions.append(
            {
                "circuit_id": circuit_id,
                "circuit_family": family,
                "version": "original",
                "circuit": circuit,
            }
        )
        for name, optimizer in optimizers.items():
            result = optimizer.optimize(circuit, target=circuit)
            certificate = result.equivalence_certificate or {}
            if not certificate.get("is_verified", False):
                raise ValueError(f"unverified reconstructed optimizer output: {circuit_id}/{name}")
            versions.append(
                {
                    "circuit_id": circuit_id,
                    "circuit_family": family,
                    "version": name,
                    "circuit": result.optimized_circuit,
                }
            )
    return versions


def build_audit(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict:
    for path in (RUNS, METADATA, EXPERIMENT_SOURCE):
        if not path.is_file():
            raise FileNotFoundError(path)
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    expected_source = metadata["source_hashes"][
        "experiments/hardware_validation/run.py"
    ]
    if sha256(EXPERIMENT_SOURCE) != expected_source:
        raise ValueError("hardware experiment source differs from archived binding")

    archived = pd.read_csv(RUNS)
    key = [
        "circuit_id",
        "version",
        "backend_name",
        "transpile_optimization_level",
    ]
    cells = archived.drop_duplicates(key).set_index(key, verify_integrity=True)
    expected_hashes = (
        archived.groupby(["circuit_id", "version"])["output_sha256"]
        .agg(lambda values: sorted(set(values)))
        .to_dict()
    )
    if any(len(values) != 1 for values in expected_hashes.values()):
        raise ValueError("archived logical output hash varies within a version")

    backends = {
        "FakeManilaV2": FakeManilaV2(),
        "FakeNairobiV2": FakeNairobiV2(),
    }
    rows: list[dict] = []
    for entry in _logical_versions():
        circuit = entry["circuit"]
        logical_hash = circuit_sha256(circuit)
        expected = expected_hashes[(entry["circuit_id"], entry["version"])][0]
        if logical_hash != expected:
            raise ValueError(
                f"logical circuit hash mismatch: {entry['circuit_id']}/{entry['version']}"
            )
        for backend_name, backend in backends.items():
            communication = logical_communication_counts(circuit, backend)
            for level in metadata["transpile_levels"]:
                archive_key = (
                    entry["circuit_id"],
                    entry["version"],
                    backend_name,
                    int(level),
                )
                recorded = cells.loc[archive_key]
                routed = transpile(
                    circuit,
                    backend=backend,
                    optimization_level=int(level),
                    seed_transpiler=int(metadata["seed_transpiler"]),
                    initial_layout=list(range(circuit.num_qubits)),
                    routing_method="sabre",
                    translation_method="translator",
                )
                routed_metrics = circuit_structural_metrics(routed)
                for field, recorded_field in (
                    ("gates", "transpiled_gates"),
                    ("depth", "transpiled_depth"),
                    ("two_qubit_gates", "transpiled_2q_gates"),
                    ("two_qubit_depth", "transpiled_2q_depth"),
                ):
                    if int(routed_metrics[field]) != int(recorded[recorded_field]):
                        raise ValueError(f"archived routing replay mismatch for {archive_key}/{field}")

                # An all-to-all counterfactual isolates the topology constraint
                # while retaining basis, optimizer level, and transpiler seed.
                topology_free = transpile(
                    circuit,
                    basis_gates=list(NATIVE_BASIS),
                    optimization_level=int(level),
                    seed_transpiler=int(metadata["seed_transpiler"]),
                    translation_method="translator",
                )
                free_metrics = circuit_structural_metrics(topology_free)
                overhead_2q = (
                    int(routed_metrics["two_qubit_gates"])
                    - int(free_metrics["two_qubit_gates"])
                )
                overhead_depth = (
                    int(routed_metrics["two_qubit_depth"])
                    - int(free_metrics["two_qubit_depth"])
                )
                rows.append(
                    {
                        "circuit_id": entry["circuit_id"],
                        "circuit_family": entry["circuit_family"],
                        "version": entry["version"],
                        "backend_name": backend_name,
                        "transpile_optimization_level": int(level),
                        "seed_transpiler": int(metadata["seed_transpiler"]),
                        "initial_layout_policy": "trivial_identity_on_logical_width",
                        "logical_output_sha256": logical_hash,
                        **communication,
                        "topology_free_native_2q_gates": int(
                            free_metrics["two_qubit_gates"]
                        ),
                        "routed_native_2q_gates": int(
                            routed_metrics["two_qubit_gates"]
                        ),
                        "routing_native_2q_gate_overhead": overhead_2q,
                        "routing_native_2q_gate_overhead_ratio": (
                            float(overhead_2q / free_metrics["two_qubit_gates"])
                            if free_metrics["two_qubit_gates"]
                            else 0.0
                        ),
                        "topology_free_native_2q_depth": int(
                            free_metrics["two_qubit_depth"]
                        ),
                        "routed_native_2q_depth": int(
                            routed_metrics["two_qubit_depth"]
                        ),
                        "routing_native_2q_depth_overhead": overhead_depth,
                        "archived_routing_replay_exact": True,
                    }
                )

    frame = pd.DataFrame(rows).sort_values(key).reset_index(drop=True)
    if len(frame) != 48:
        raise ValueError(f"expected 48 routing design cells, found {len(frame)}")
    level_zero = frame[frame["transpile_optimization_level"] == 0]
    if (level_zero["routing_native_2q_gate_overhead"] < 0).any():
        raise ValueError("level-0 topology counterfactual produced negative 2Q overhead")

    # Compare every optimized logical version with the original circuit under
    # exactly the same backend snapshot and transpiler optimization level.
    # This answers the physical-native-2Q question directly; routing overhead
    # alone does not establish whether an optimization improves the mapped
    # circuit relative to its own baseline.
    pair_keys = [
        "circuit_id", "backend_name", "transpile_optimization_level",
    ]
    originals = frame.loc[
        frame["version"].eq("original"),
        pair_keys + ["routed_native_2q_gates"],
    ].rename(columns={"routed_native_2q_gates": "original_routed_native_2q_gates"})
    optimized = frame.loc[~frame["version"].eq("original")].merge(
        originals, on=pair_keys, how="left", validate="many_to_one",
    )
    if optimized["original_routed_native_2q_gates"].isna().any() or len(optimized) != 36:
        raise ValueError("physical 2Q comparison lacks a unique original baseline")
    optimized["routed_native_2q_reduction_vs_original"] = (
        optimized["original_routed_native_2q_gates"]
        - optimized["routed_native_2q_gates"]
    ).astype(int)
    physical_2q_by_version = []
    for version, group in optimized.groupby("version", sort=True):
        reductions = group["routed_native_2q_reduction_vs_original"].astype(int)
        physical_2q_by_version.append({
            "version": str(version),
            "paired_cells": int(len(group)),
            "reduced_cells": int((reductions > 0).sum()),
            "equal_cells": int((reductions == 0).sum()),
            "increased_cells": int((reductions < 0).sum()),
            "reduction_gate_range": [int(reductions.min()), int(reductions.max())],
            "mean_reduction_gates": float(reductions.mean()),
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    cells_path = output_dir / "hardware_routing_cells.csv"
    frame.to_csv(cells_path, index=False)
    report = {
        "schema_version": "1.0.0",
        "status": "PASS_BOUNDED_FAKE_BACKEND_ROUTING_AUDIT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_bindings": {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in (RUNS, METADATA, EXPERIMENT_SOURCE)
        },
        "artifact": {
            "path": cells_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(cells_path),
            "rows": int(len(frame)),
        },
        "design": {
            "circuits": int(frame["circuit_id"].nunique()),
            "logical_versions": int(
                frame[["circuit_id", "version"]].drop_duplicates().shape[0]
            ),
            "backend_snapshots": sorted(frame["backend_name"].unique()),
            "transpile_levels": sorted(
                int(value) for value in frame["transpile_optimization_level"].unique()
            ),
            "design_cells": int(len(frame)),
            "all_archived_routing_cells_replayed_exactly": bool(
                frame["archived_routing_replay_exact"].all()
            ),
        },
        "communication_nonlocal_operations": {
            "definition": (
                "logical two-qubit instructions whose operands have undirected "
                "shortest-path distance greater than one under the frozen identity layout"
            ),
            "cells_with_nonlocal_operations": int(
                (frame["identity_layout_nonlocal_2q_gates"] > 0).sum()
            ),
            "nonlocal_2q_count_range": [
                int(frame["identity_layout_nonlocal_2q_gates"].min()),
                int(frame["identity_layout_nonlocal_2q_gates"].max()),
            ],
            "excess_edge_hop_count_range": [
                int(frame["identity_layout_excess_edge_hops"].min()),
                int(frame["identity_layout_excess_edge_hops"].max()),
            ],
            "maximum_logical_2q_distance": int(
                frame["identity_layout_max_2q_distance"].max()
            ),
        },
        "routing_overhead": {
            "counterfactual": (
                "all-to-all connectivity with the same rz/sx/x/cx basis, "
                "transpiler optimization level, and seed"
            ),
            "level_0_native_2q_gate_overhead_range": [
                int(level_zero["routing_native_2q_gate_overhead"].min()),
                int(level_zero["routing_native_2q_gate_overhead"].max()),
            ],
            "level_0_native_2q_gate_overhead_ratio_range": [
                float(level_zero["routing_native_2q_gate_overhead_ratio"].min()),
                float(level_zero["routing_native_2q_gate_overhead_ratio"].max()),
            ],
            "all_level_0_overheads_nonnegative": True,
            "all_levels_native_2q_gate_overhead_range": [
                int(frame["routing_native_2q_gate_overhead"].min()),
                int(frame["routing_native_2q_gate_overhead"].max()),
            ],
            "positive_overhead_cells": int(
                (frame["routing_native_2q_gate_overhead"] > 0).sum()
            ),
        },
        "physical_native_2q_reduction_vs_original": {
            "pairing_key": pair_keys,
            "definition": (
                "original routed native two-qubit gates minus optimized-version "
                "routed native two-qubit gates at the same circuit, backend snapshot, "
                "and transpiler optimization level"
            ),
            "paired_cells": int(len(optimized)),
            "by_version": physical_2q_by_version,
            "versions_with_any_reduction": sorted(
                row["version"] for row in physical_2q_by_version
                if row["reduced_cells"] > 0
            ),
            "all_paired_increases_absent": bool(
                all(row["increased_cells"] == 0 for row in physical_2q_by_version)
            ),
        },
        "metric_dispositions": {
            "9.14": (
                "PASS: identity-layout nonlocal two-qubit operation count and excess "
                "edge-hop count are directly reported for all 48 bounded design cells"
            ),
            "9.16": (
                "PASS: paired topology-constrained versus all-to-all native two-qubit "
                "gate and depth overhead are directly reported for all 48 bounded design cells"
            ),
            "16.17": (
                "PARTIAL: commutation_phase2 and hybrid_phase1_2 each reduce mapped "
                "native two-qubit gates in 4 of 12 paired fake-backend cells (maximum "
                "2 gates) with no paired increases, but no real-QPU duration reduction "
                "is measured"
            ),
        },
        "claim_boundary": (
            "Three reconstructed circuits, four logical versions, two archived fake-backend "
            "snapshots, identity initial layout, SABRE routing, and Qiskit transpiler levels "
            "0/1 only. The all-to-all comparison is a compiler counterfactual; results are "
            "not real-QPU communication, pulse, latency, crosstalk, or broad-topology evidence."
        ),
    }
    report_path = output_dir / "hardware_routing_overhead_audit.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(json.dumps(build_audit(args.output_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
