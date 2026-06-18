"""E17: Hardware connectivity constraint experiment.

Evaluates optimizer performance when circuits are constrained to
realistic hardware topologies (heavy-hex, grid, linear chain).
Tests whether topology-induced gate overhead affects Phase 1 ceiling
and Phase 2 improvement differently.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit, transpile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import (  # noqa: E402
    average_gate_fidelity,
    circuit_sha256,
    gate_counts,
    generate_extended_suite,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase2.commutation_rewriter import (  # noqa: E402
    CommutationRewriter,
    HybridCommuteRewrite,
)
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "2.0.0"
EXPERIMENT_ID = "E17"
VERSION = "5.0.0"


def _safe_ratio(o, p):
    """Safe ratio computation: 1 - p/o, or 0.0 if o==0."""
    return 1.0 - p / o if o > 0 else 0.0


# ---------------------------------------------------------------------------
# Topology coupling maps
# ---------------------------------------------------------------------------

def make_linear_chain(n_qubits: int) -> List[Tuple[int, int]]:
    """Linear chain: qubit i connected to qubit i+1."""
    return [(i, i + 1) for i in range(n_qubits - 1)]


def make_grid(n_qubits: int) -> List[Tuple[int, int]]:
    """2D grid topology. Places qubits in a sqrt(n) x sqrt(n) grid."""
    side = int(np.ceil(np.sqrt(n_qubits)))
    edges = []
    for r in range(side):
        for c in range(side):
            q = r * side + c
            if q >= n_qubits:
                continue
            # Right neighbor
            if c + 1 < side:
                qr = r * side + (c + 1)
                if qr < n_qubits:
                    edges.append((q, qr))
            # Down neighbor
            if r + 1 < side:
                qd = (r + 1) * side + c
                if qd < n_qubits:
                    edges.append((q, qd))
    return edges


def make_heavy_hex(n_qubits: int) -> List[Tuple[int, int]]:
    """Approximate heavy-hex-inspired topology (IBM-style).

    NOTE: This is *not* a true heavy-hex lattice. A genuine heavy-hex
    topology consists of hexagonal rings with alternating "heavy" edges
    (chains of two qubits replacing single edges), giving every qubit
    degree <= 3. This function instead builds a grid with a checkerboard
    vertical-connectivity pattern that loosely mimics the degree-3
    constraint but does not form actual hexagonal rings. It is retained
    as a "sparse grid" benchmark; for a true heavy-hex topology use
    Qiskit's ``CouplingMap.from_heavy_hex(d)``.

    Falls back to a linear chain for n <= 3.
    """
    if n_qubits <= 3:
        return make_linear_chain(n_qubits)

    edges = []
    # Build a simplified heavy-hex pattern
    # Row-based: each row alternates connectivity
    cols = max(3, int(np.ceil(np.sqrt(n_qubits))))
    rows = int(np.ceil(n_qubits / cols))

    for r in range(rows):
        for c in range(cols):
            q = r * cols + c
            if q >= n_qubits:
                continue
            # Horizontal edge
            if c + 1 < cols:
                qr = r * cols + (c + 1)
                if qr < n_qubits:
                    edges.append((q, qr))
            # Vertical edge (alternating columns per row for heavy-hex)
            if r + 1 < rows:
                should_connect = (r % 2 == 0 and c % 2 == 0) or (r % 2 == 1 and c % 2 == 1)
                if should_connect:
                    qd = (r + 1) * cols + c
                    if qd < n_qubits:
                        edges.append((q, qd))
    return edges if edges else make_linear_chain(n_qubits)


TOPOLOGIES = {
    "linear": make_linear_chain,
    "grid": make_grid,
    "heavy_hex": make_heavy_hex,
}


# ---------------------------------------------------------------------------
# Circuit transpilation with topology constraint
# ---------------------------------------------------------------------------

def apply_topology_constraint(circuit: QuantumCircuit,
                               coupling_map: List[Tuple[int, int]],
                               seed_transpiler: int = 42) -> QuantumCircuit:
    """Transpile a circuit to respect the given coupling map.

    Uses ``optimization_level=0`` so the transpiler performs *only*
    topology routing (SWAP insertion) without applying its own gate
    cancellation or commutation passes.  This prevents the Qiskit
    transpiler's built-in optimizations from contaminating the
    connectivity-constraint measurement.
    """
    from qiskit import transpile as qiskit_transpile
    from qiskit.transpiler import CouplingMap

    cmap = CouplingMap(coupling_map)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        transpiled = qiskit_transpile(
            circuit,
            coupling_map=cmap,
            optimization_level=0,
            basis_gates=['u1', 'u2', 'u3', 'cx'],
            seed_transpiler=seed_transpiler,
        )
    return transpiled


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def _count_metrics(circuit) -> Dict[str, float]:
    depth = int(circuit.depth() or 0)
    two_q = sum(1 for inst in circuit.data if inst.operation.num_qubits == 2)
    cnot = sum(1 for inst in circuit.data if inst.operation.name in ('cx', 'cnot'))
    return {"depth": depth, "two_q": two_q, "cnot": cnot}


def run(mode: str, seed: int, max_qubits_fidelity: int,
        topologies: List[str] | None = None) -> pd.DataFrame:
    """Run E17 connectivity constraint experiment."""
    if topologies is None:
        topologies = list(TOPOLOGIES.keys())

    run_id = f"e17_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v5" / "e17"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    circuits = generate_extended_suite(mode=mode, seed=seed)

    our_optimizers = {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "commutation_phase2": CommutationRewriter(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }

    rows: List[dict] = []
    for trial, bench in enumerate(circuits):
        circuit = bench.circuit
        n = circuit.num_qubits

        for topo_name in topologies:
            topo_fn = TOPOLOGIES[topo_name]
            coupling_map = topo_fn(n)

            try:
                constrained_circuit = apply_topology_constraint(circuit, coupling_map, seed_transpiler=seed)
            except Exception as exc:
                rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "circuit_id": bench.circuit_id,
                    "circuit_family": bench.family,
                    "n_qubits": n,
                    "topology": topo_name,
                    "optimizer": "none",
                    "status": "transpile_error",
                    "error_message": str(exc),
                    "error_type": type(exc).__name__,
                })
                continue

            input_hash = circuit_sha256(constrained_circuit)
            orig_counts = constrained_circuit.size()
            orig_m = _count_metrics(constrained_circuit)

            for opt_name, opt in our_optimizers.items():
                start = time.time()
                result = opt.optimize(constrained_circuit, target=constrained_circuit)
                runtime = time.time() - start

                output_hash = circuit_sha256(result.optimized_circuit)
                opt_m = _count_metrics(result.optimized_circuit)

                fidelity = result.fidelity
                if fidelity is None or fidelity == 0.0:
                    exact = average_gate_fidelity(
                        result.optimized_circuit, constrained_circuit,
                        max_qubits=max_qubits_fidelity,
                    )
                    fidelity = exact if exact is not None else result.fidelity

                rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "circuit_id": bench.circuit_id,
                    "circuit_family": bench.family,
                    "n_qubits": n,
                    "topology": topo_name,
                    "n_edges": len(coupling_map),
                    "baseline_gate_count": orig_counts,
                    "optimized_gate_count": result.optimized_size,
                    "reduction": result.reduction,
                    "reduction_pct": 100.0 * result.reduction,
                    "depth_reduction": _safe_ratio(orig_m["depth"], opt_m["depth"]),
                    "two_qubit_reduction": _safe_ratio(orig_m["two_q"], opt_m["two_q"]),
                    "cnot_reduction": _safe_ratio(orig_m["cnot"], opt_m["cnot"]),
                    "fidelity": fidelity,
                    "runtime_seconds": runtime,
                    "optimizer": opt_name,
                    "seed": bench.seed,
                    "trial": trial,
                    "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                    "source_sha256": file_sha256(script_path),
                    "input_circuit_sha256": input_hash,
                    "output_circuit_sha256": output_hash,
                    "notes": bench.notes,
                    "status": "ok",
                })

    df = pd.DataFrame(rows)
    csv_path = output_dir / f"e17_connectivity_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata.update(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "description": "Hardware connectivity constraint experiment",
            "mode": mode,
            "seed": seed,
            "max_qubits_fidelity": max_qubits_fidelity,
            "topologies": topologies,
            "canonical_data_file": csv_path.name,
            "n_input_circuits": len(circuits),
            "n_rows": len(df),
            "circuit_families": sorted({bench.family for bench in circuits}),
        }
    )
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"E17 complete: {len(df)} rows -> {csv_path}")
    if "reduction" in df.columns:
        summary = (
            df.dropna(subset=["reduction"])
            .groupby(["topology", "optimizer"])
            .agg({"reduction": "mean", "depth_reduction": "mean", "cnot_reduction": "mean"})
        )
        print(summary.to_string())
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E17 connectivity constraints")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-qubits-fidelity", type=int, default=10)
    parser.add_argument(
        "--topologies", nargs="+", choices=list(TOPOLOGIES.keys()),
        default=None, help="Topologies to evaluate",
    )
    args = parser.parse_args()
    run(mode=args.mode, seed=args.seed, max_qubits_fidelity=args.max_qubits_fidelity,
        topologies=args.topologies)


if __name__ == "__main__":
    main()
