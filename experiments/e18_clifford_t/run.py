"""E18: exact native Clifford+T gate-set experiment.

Evaluates optimizer performance on circuits constructed natively in the
Clifford+T universal gate set {H, S, T, CNOT} (and their inverses).
This tests whether Phase 2 commutation rewriting is effective under
the fault-tolerant gate set commonly used in quantum error correction.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit, transpile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.circuits.real_benchmarks import (  # noqa: E402
    average_gate_fidelity,
    circuit_sha256,
    gate_counts,
    BenchmarkCircuit,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase2.commutation_rewriter import (  # noqa: E402
    CommutationRewriter,
    HybridCommuteRewrite,
)
from src.provenance import file_sha256, run_metadata  # noqa: E402

SCHEMA_VERSION = "2.0.0"
EXPERIMENT_ID = "E18"
VERSION = "5.0.0"


def _safe_ratio(o, p):
    """Safe ratio computation: 1 - p/o, or 0.0 if o==0."""
    return 1.0 - p / o if o > 0 else 0.0

# Clifford+T basis gates
CLIFFORD_T_BASIS = ['h', 's', 'sdg', 't', 'tdg', 'cx', 'x', 'y', 'z']
CLIFFORD_T_DECOMPOSED_BASIS = ['h', 's', 'sdg', 't', 'tdg', 'cx']


def decompose_to_clifford_t(circuit: QuantumCircuit) -> QuantumCircuit:
    """Decompose a circuit into the Clifford+T gate set.

    Uses Qiskit transpiler to map arbitrary gates to {H, S, T, CNOT, X, Y, Z}.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        transpiled = transpile(
            circuit,
            basis_gates=CLIFFORD_T_BASIS,
            optimization_level=0,  # no optimization, just decompose
            seed_transpiler=42,
        )
    return transpiled


def count_t_gates(circuit: QuantumCircuit) -> Dict[str, int]:
    """Count T/Tdg gate occurrences."""
    ops = circuit.count_ops()
    return {
        "t_count": ops.get("t", 0),
        "tdg_count": ops.get("tdg", 0),
        "total_t": ops.get("t", 0) + ops.get("tdg", 0),
        "s_count": ops.get("s", 0),
        "sdg_count": ops.get("sdg", 0),
        "h_count": ops.get("h", 0),
        "cx_count": ops.get("cx", 0),
    }


def generate_clifford_t_suite(mode: str, seed: int) -> List[BenchmarkCircuit]:
    """Generate exact Clifford+T instances without approximating rotations.

    The former E18 attempted to transpile arbitrary continuous-angle and Haar
    circuits into a discrete basis.  A finite exact decomposition does not
    generally exist, so this dedicated suite samples only native operations
    (plus exactly decomposable Toffoli blocks).
    """
    sizes = [3] if mode == "smoke" else list(range(3, 9))
    trials = 1 if mode == "smoke" else 10
    suite = f"clifford_t_native_{mode}"
    benches: List[BenchmarkCircuit] = []
    one_q = ("h", "s", "sdg", "t", "tdg", "x", "z")
    inverse_pairs = (("h", "h"), ("s", "sdg"), ("t", "tdg"),
                     ("x", "x"), ("z", "z"))

    def apply_1q(qc, name, qubit):
        getattr(qc, name)(qubit)

    for n in sizes:
        for trial in range(trials):
            trial_seed = seed + 1000 * n + trial
            rng = np.random.default_rng(trial_seed)

            random_native = QuantumCircuit(n)
            for _ in range(6 * n):
                if rng.random() < 0.3:
                    a, b = rng.choice(n, size=2, replace=False)
                    random_native.cx(int(a), int(b))
                else:
                    apply_1q(random_native, one_q[int(rng.integers(len(one_q)))],
                             int(rng.integers(n)))

            adjacent = QuantumCircuit(n)
            for _ in range(3 * n):
                if rng.random() < 0.25:
                    a, b = rng.choice(n, size=2, replace=False)
                    adjacent.cx(int(a), int(b)); adjacent.cx(int(a), int(b))
                else:
                    a, b = inverse_pairs[int(rng.integers(len(inverse_pairs)))]
                    q = int(rng.integers(n))
                    apply_1q(adjacent, a, q); apply_1q(adjacent, b, q)

            commuting = QuantumCircuit(n)
            for q in range(n):
                commuting.t(q)
                for other in range(n):
                    if other != q:
                        commuting.h(other); commuting.h(other)
                commuting.tdg(q)

            parity_phase = QuantumCircuit(n)
            for _ in range(3):
                for q in range(n - 1):
                    parity_phase.cx(q, q + 1)
                parity_phase.t(n - 1)
                for q in reversed(range(n - 1)):
                    parity_phase.cx(q, q + 1)

            toffoli = QuantumCircuit(n)
            for offset in range(max(1, n - 2)):
                a, b, c = offset % n, (offset + 1) % n, (offset + 2) % n
                toffoli.ccx(a, b, c); toffoli.ccx(a, b, c)
            toffoli = decompose_to_clifford_t(toffoli)

            phase_echo = QuantumCircuit(n)
            for q in range(n - 1):
                phase_echo.h(q); phase_echo.cx(q, q + 1)
                phase_echo.t(q + 1); phase_echo.tdg(q + 1)
                phase_echo.cx(q, q + 1); phase_echo.h(q)

            variants = (
                ("NativeRandom", "random_native", random_native),
                ("AdjacentInverse", "adjacent_inverse", adjacent),
                ("CommutingExposure", "commuting_exposure", commuting),
                ("ParityPhase", "parity_phase", parity_phase),
                ("ToffoliBlocks", "toffoli_blocks", toffoli),
                ("PhaseEcho", "phase_echo", phase_echo),
            )
            for family, circuit_type, circuit in variants:
                unsupported = sorted(set(circuit.count_ops()) - set(CLIFFORD_T_BASIS))
                if unsupported:
                    raise ValueError(f"non-Clifford+T operations in {family}: {unsupported}")
                benches.append(BenchmarkCircuit(
                    f"ct_{family.lower()}_n{n}_t{trial}", family, circuit_type,
                    suite, circuit, trial_seed,
                    notes="Natively generated exact Clifford+T benchmark",
                ))
    return benches


def _count_metrics(circuit) -> Dict[str, float]:
    depth = int(circuit.depth() or 0)
    two_q = sum(1 for inst in circuit.data if inst.operation.num_qubits == 2)
    cnot = sum(1 for inst in circuit.data if inst.operation.name in ('cx', 'cnot'))
    t_count = sum(1 for inst in circuit.data if inst.operation.name in ('t', 'tdg'))
    return {"depth": depth, "two_q": two_q, "cnot": cnot, "t_count": t_count}


def run(mode: str, seed: int, max_qubits_fidelity: int,
        output_dir: Path | None = None) -> pd.DataFrame:
    """Run E18 Clifford+T gate-set experiment."""
    run_id = f"e18_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    output_dir = (PROJECT_ROOT / "data" / "v10" / "prepaper" / "e18"
                  if output_dir is None else Path(output_dir).resolve())
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)
    circuits = generate_clifford_t_suite(mode=mode, seed=seed)

    our_optimizers = {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "commutation_phase2": CommutationRewriter(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }

    rows: List[dict] = []
    for trial, bench in enumerate(circuits):
        circuit = bench.circuit

        clifford_t_circuit = circuit

        input_hash = circuit_sha256(clifford_t_circuit)
        orig_counts = clifford_t_circuit.size()
        orig_m = _count_metrics(clifford_t_circuit)
        orig_t = count_t_gates(clifford_t_circuit)

        for opt_name, opt in our_optimizers.items():
            start = time.time()
            try:
                result = opt.optimize(clifford_t_circuit, target=clifford_t_circuit)
            except Exception as exc:
                rows.append({
                    "schema_version": SCHEMA_VERSION, "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id, "circuit_id": bench.circuit_id,
                    "circuit_family": bench.family, "circuit_type": bench.circuit_type,
                    "n_qubits": circuit.num_qubits, "gate_set": "clifford_t",
                    "baseline_gate_count": orig_counts,
                    "optimized_gate_count": float("nan"), "reduction": float("nan"),
                    "fidelity": float("nan"), "fidelity_source": "unavailable",
                    "valid_equivalent_output": False, "success": False,
                    "analysis_reduction_itt": 0.0,
                    "runtime_seconds": time.time() - start, "optimizer": opt_name,
                    "seed": bench.seed, "trial": trial,
                    "source_file": script_path.relative_to(PROJECT_ROOT).as_posix(),
                    "source_sha256": file_sha256(script_path),
                    "input_circuit_sha256": input_hash, "status": "optimizer_error",
                    "error_type": type(exc).__name__, "error_message": str(exc),
                })
                continue
            runtime = time.time() - start

            output_hash = circuit_sha256(result.optimized_circuit)
            opt_m = _count_metrics(result.optimized_circuit)
            opt_t = count_t_gates(result.optimized_circuit)

            exact = average_gate_fidelity(
                result.optimized_circuit, clifford_t_circuit,
                max_qubits=max_qubits_fidelity,
            )
            fidelity = float("nan") if exact is None else exact
            valid_equivalent = bool(
                math.isfinite(fidelity) and fidelity >= opt.fidelity_threshold
            )
            success = bool(
                valid_equivalent and result.reduction >= opt.success_reduction
            )

            rows.append({
                "schema_version": SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "circuit_id": bench.circuit_id,
                "circuit_family": bench.family,
                "circuit_type": bench.circuit_type,
                "n_qubits": circuit.num_qubits,
                "gate_set": "clifford_t",
                "baseline_gate_count": orig_counts,
                "optimized_gate_count": result.optimized_size,
                "reduction": result.reduction,
                "reduction_pct": 100.0 * result.reduction,
                "depth_reduction": _safe_ratio(orig_m["depth"], opt_m["depth"]),
                "two_qubit_reduction": _safe_ratio(orig_m["two_q"], opt_m["two_q"]),
                "cnot_reduction": _safe_ratio(orig_m["cnot"], opt_m["cnot"]),
                "t_count_reduction": _safe_ratio(orig_m["t_count"], opt_m["t_count"]),
                "baseline_t_count": orig_m["t_count"],
                "optimized_t_count": opt_m["t_count"],
                "fidelity": fidelity,
                "fidelity_source": "exact" if math.isfinite(fidelity) else "unavailable",
                "valid_equivalent_output": valid_equivalent,
                "success": success,
                "analysis_reduction_itt": result.reduction if valid_equivalent else 0.0,
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
    csv_path = output_dir / f"e18_clifford_t_{run_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata.update(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "description": "Exact native Clifford+T gate-set optimization experiment",
            "mode": mode,
            "seed": seed,
            "max_qubits_fidelity": max_qubits_fidelity,
            "gate_set": "clifford_t",
            "basis_gates": CLIFFORD_T_BASIS,
            "canonical_data_file": csv_path.name,
            "n_input_circuits": len(circuits),
            "n_rows": len(df),
            "circuit_families": sorted({bench.family for bench in circuits}),
            "protocol_file": "experiments/prepaper_protocol.json",
            "protocol_sha256": file_sha256(PROJECT_ROOT / "experiments/prepaper_protocol.json"),
        }
    )
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)

    print(f"E18 complete: {len(df)} rows -> {csv_path}")
    if "reduction" in df.columns:
        summary = (
            df.dropna(subset=["reduction"])
            .groupby(["optimizer"])
            .agg({
                "reduction": "mean",
                "depth_reduction": "mean",
                "cnot_reduction": "mean",
                "t_count_reduction": "mean",
            })
        )
        print(summary.to_string())
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E18 Clifford+T gate-set experiment")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-qubits-fidelity", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    run(mode=args.mode, seed=args.seed, max_qubits_fidelity=args.max_qubits_fidelity,
        output_dir=args.output_dir)


if __name__ == "__main__":
    main()
