"""P3 pilot: listing model crossed with Phase-1, Phase-2a, and Phase-2b.

This is supporting evidence, not a canonical experiment. It uses the smoke
benchmark suite and three valid topological listings per circuit (original,
WCL, and randomized topological order). It estimates listing × mechanism
interactions without treating marginal listing or phase effects as an
interaction claim.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import (  # noqa: E402
    average_gate_fidelity,
    circuit_sha256,
    generate_extended_suite,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor  # noqa: E402
from src.optimisation.phase2.commutation_rewriter import Phase2aCommutationRewriter  # noqa: E402
from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher  # noqa: E402

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "v11" / "e31_listing_phase2b"
LISTINGS = ("LBL", "WCL", "SHUFFLE")
PHASES = ("phase1", "phase2a", "phase2b")


def random_topological_listing(circuit, seed: int):
    """Return a random valid topological listing of ``circuit`` gates."""
    gate_qubits: list[set[int]] = []
    qubit_to_gates: dict[int, list[int]] = defaultdict(list)
    for index, instruction in enumerate(circuit.data):
        qubits = {circuit.find_bit(qubit).index for qubit in instruction.qubits}
        gate_qubits.append(qubits)
        for qubit in qubits:
            qubit_to_gates[qubit].append(index)

    successors: dict[int, list[int]] = defaultdict(list)
    indegree = [0] * len(circuit.data)
    edges: set[tuple[int, int]] = set()
    for gates in qubit_to_gates.values():
        for first, second in zip(gates, gates[1:]):
            edges.add((first, second))
    for first, second in edges:
        successors[first].append(second)
        indegree[second] += 1

    rng = random.Random(seed)
    available = [index for index, degree in enumerate(indegree) if degree == 0]
    order: list[int] = []
    while available:
        index = rng.choice(available)
        available.remove(index)
        order.append(index)
        for successor in successors[index]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                available.append(successor)

    if len(order) != len(circuit.data):
        raise ValueError("circuit dependency graph is cyclic")
    relisted = copy.deepcopy(circuit)
    relisted.data = [circuit.data[index] for index in order]
    return relisted


def build_listings(circuit, seed: int) -> dict[str, Any]:
    """Build three semantics-preserving listing variants."""
    variants = {
        "LBL": copy.deepcopy(circuit),
        "WCL": WireTraversalPreprocessor().preprocess(circuit),
        "SHUFFLE": random_topological_listing(circuit, seed=seed),
    }
    for name, variant in variants.items():
        fidelity = average_gate_fidelity(variant, circuit, max_qubits=variant.num_qubits)
        if fidelity < 1.0 - 1e-10:
            raise ValueError(f"listing {name} changed unitary: fidelity={fidelity}")
    return variants


def _optimize(circuit, phase: str):
    if phase == "phase1":
        optimizer = GreedyGateCancellation(success_reduction=0.01)
        return optimizer.optimize(circuit, target=None)
    if phase == "phase2a":
        optimizer = Phase2aCommutationRewriter(success_reduction=0.01, window_size=10)
        return optimizer.optimize(circuit, target=None)
    if phase == "phase2b":
        optimizer = Phase2bTemplateMatcher(success_reduction=0.01, gather_window=64)
        return optimizer.optimize_full_pipeline(circuit, target=None)
    raise ValueError(f"unknown phase: {phase}")


def run(output_dir: Path | str = DEFAULT_OUTPUT_DIR, seed: int = 42) -> pd.DataFrame:
    """Run the smoke-scale P3 listing × phase pilot."""
    output_dir = Path(output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    suite = generate_extended_suite(mode="smoke", seed=seed)
    rows: list[dict[str, Any]] = []

    for circuit_index, benchmark in enumerate(suite):
        variants = build_listings(benchmark.circuit, seed=seed + circuit_index)
        for listing, circuit in variants.items():
            for phase in PHASES:
                result = _optimize(circuit, phase)
                rows.append({
                    "experiment_id": "E31-pilot",
                    "circuit_id": benchmark.circuit_id,
                    "circuit_family": benchmark.family,
                    "n_qubits": circuit.num_qubits,
                    "listing_model": listing,
                    "phase": phase,
                    "original_gate_count": circuit.size(),
                    "optimized_gate_count": result.optimized_circuit.size(),
                    "reduction": result.reduction,
                    "listing_fidelity": average_gate_fidelity(
                        circuit, benchmark.circuit, max_qubits=circuit.num_qubits
                    ),
                    "input_circuit_sha256": circuit_sha256(benchmark.circuit),
                    "listing_circuit_sha256": circuit_sha256(circuit),
                    "optimizer_metadata": json.dumps(result.metadata, sort_keys=True),
                })

    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "e31_listing_phase2b_pilot.csv", index=False)
    metadata = {
        "experiment_id": "E31-pilot",
        "status": "supporting_noncanonical_pilot",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "suite_mode": "smoke",
        "seed": seed,
        "n_source_circuits": len(suite),
        "listings": list(LISTINGS),
        "phases": list(PHASES),
        "n_rows": len(frame),
        "canonical": False,
        "limitations": [
            "Smoke-scale circuits and one seed per source circuit.",
            "No interaction hypothesis is confirmed from this pilot alone.",
            "Full factorial WCL/shuffle x Phase-2b coverage remains open.",
        ],
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    return frame


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    frame = run(args.output_dir, seed=args.seed)
    print(f"E31-pilot complete: {len(frame)} rows -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
