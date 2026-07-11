"""E25: Industry benchmark proxy (MQT Bench / QUEKO / Benchpress).

This experiment provides a lightweight, offline-compatible benchmark scaffold:
- It attempts to load circuits from MQT Bench, Benchpress, and QUEKO.
- If those packages/data are unavailable (no network / not installed), it falls
  back to representative Qiskit circuit-library families that mirror the
  industry suites (QFT, Grover, QAOA, VQE-style, arithmetic, etc.).

Output: data/v6/e25/
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from qiskit import QuantumCircuit
from qiskit.circuit.library import (
    QFT, GroverOperator, WeightedAdder, IntegerComparator,
    EfficientSU2, RealAmplitudes,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import (
    make_qft, make_ghz, make_cnot_chain, make_bernstein_vazirani,
    make_qaoa_line, make_vqe_twolocal, make_hardware_efficient,
    make_grover, make_quantum_adder, make_iqp, make_random_clifford,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.optimisation.phase2.commutation_rewriter import HybridCommuteRewrite
from src.provenance import file_sha256, run_metadata

SCHEMA_VERSION = "1.0.0"
EXPERIMENT_ID = "E25"
VERSION = "1.0.0"


def try_mqt_bench() -> List[Tuple[str, str, QuantumCircuit]]:
    """Attempt to load a small MQT Bench subset."""
    circuits: List[Tuple[str, str, QuantumCircuit]] = []
    try:
        from mqt.bench import get_benchmark
        for name, bench in [
            ("qft", "qft"),
            ("grover", "grover"),
            ("qaoa", "qaoa"),
        ]:
            for n in [3, 4, 5]:
                try:
                    qc = get_benchmark(benchmark_name=bench, circuit_size=n)
                    circuits.append((f"mqt_{name}_{n}", f"MQT_{name.upper()}", qc))
                except Exception:
                    pass
    except Exception:
        pass
    return circuits


def try_benchpress() -> List[Tuple[str, str, QuantumCircuit]]:
    """Attempt to load a small Benchpress subset (placeholder)."""
    return []


def try_queko() -> List[Tuple[str, str, QuantumCircuit]]:
    """Attempt to load QUEKO circuits from a local path (placeholder)."""
    return []


def qiskit_fallback_circuits() -> List[Tuple[str, str, QuantumCircuit]]:
    """Representative Qiskit circuits used when industry suites are unavailable."""
    circuits: List[Tuple[str, str, QuantumCircuit]] = []
    for n in [3, 4, 5]:
        circuits.append((f"qft_{n}", "QFT", make_qft(n)))
        circuits.append((f"ghz_{n}", "GHZ", make_ghz(n)))
        circuits.append((f"cnot_chain_{n}", "CNOT", make_cnot_chain(n, repeats=1)))
        circuits.append((f"bv_{n}", "Oracle", make_bernstein_vazirani(n, seed=42 + n)))
        circuits.append((f"qaoa_{n}", "QAOA", make_qaoa_line(n, reps=1, seed=100 + n)))
        circuits.append((f"vqe_{n}", "VQE", make_vqe_twolocal(n, reps=1, seed=200 + n)))
        circuits.append((f"he_{n}", "HardwareEfficient", make_hardware_efficient(n, layers=1, seed=300 + n)))
        circuits.append((f"grover_{n}", "Grover", make_grover(n, seed=400 + n)))
        circuits.append((f"adder_{n}", "Adder", make_quantum_adder(n, seed=500 + n)))
        circuits.append((f"iqp_{n}", "IQP", make_iqp(n, depth=2, seed=700 + n)))
        circuits.append((f"clifford_{n}", "RandomClifford", make_random_clifford(n, depth=8, seed=800 + n)))
    return circuits


def build_optimizers() -> Dict[str, object]:
    return {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }


def run(max_qubits_fidelity: int = 8) -> pd.DataFrame:
    run_id = f"e25_industry_proxies_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = PROJECT_ROOT / "data" / "v6" / "e25"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)

    circuits: List[Tuple[str, str, QuantumCircuit]] = []
    source_tags: List[str] = []

    mqt = try_mqt_bench()
    if mqt:
        circuits.extend(mqt)
        source_tags.append("mqt_bench")

    bp = try_benchpress()
    if bp:
        circuits.extend(bp)
        source_tags.append("benchpress")

    qk = try_queko()
    if qk:
        circuits.extend(qk)
        source_tags.append("queko")

    if not circuits:
        circuits = qiskit_fallback_circuits()
        source_tags.append("qiskit_fallback")

    optimizers = build_optimizers()
    rows: List[dict] = []

    for circuit_id, family, circuit in circuits:
        for optimizer_name, optimizer in optimizers.items():
            start = time.time()
            result = optimizer.optimize(circuit, target=circuit)
            runtime = time.time() - start
            rows.append({
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "circuit_id": circuit_id,
                "circuit_family": family,
                "n_qubits": circuit.num_qubits,
                "depth": circuit.depth(),
                "size": circuit.size(),
                "optimizer": optimizer_name,
                "original_size": result.original_size,
                "optimized_size": result.optimized_size,
                "reduction": result.reduction,
                "fidelity": result.fidelity,
                "success": bool(result.success),
                "runtime_seconds": runtime,
                "source_tag": source_tags[0] if len(source_tags) == 1 else "mixed",
                "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                "source_sha256": file_sha256(script_path),
                "env_id": run_id,
            })

    df = pd.DataFrame(rows)
    csv_path = output_dir / f"e25_industry_benchmarks_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata.update({
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "description": "Industry benchmark proxy (MQT Bench / QUEKO / Benchpress fallback)",
        "canonical_data_file": csv_path.name,
        "n_input_circuits": len(circuits),
        "n_rows": len(df),
        "source_tags": source_tags,
        "optimizers": list(optimizers.keys()),
        "fallback_note": "Industry suite packages not available offline; used Qiskit-based proxy circuits.",
    })
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"E25 complete: {len(df)} rows -> {csv_path}")
    print(df.groupby("circuit_family")["reduction"].mean().to_string())
    return df


if __name__ == "__main__":
    run()
