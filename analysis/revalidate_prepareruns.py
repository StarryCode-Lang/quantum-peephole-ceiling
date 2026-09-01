"""Sequentially revalidate fidelity rows lost to transient memory pressure.

This does not replace unavailable results above a protocol's exact-qubit
limit.  It reconstructs only rows that should have been exact, verifies that
the regenerated optimizer result has identical resource metrics/hash, and
writes a new canonical table with explicit revalidation provenance.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit.quantum_info import Operator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.e14_extended_benchmark.run import build_optimizers
from src.circuits.generator_v2 import CircuitConfig, CircuitFamily, MetricsCalculator, generate_circuit_batch
from src.circuits.real_benchmarks import average_gate_fidelity, circuit_sha256, generate_extended_suite
from src.optimisation.phase1.greedy import GreedyGateCancellation
from src.provenance import file_sha256


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(tmp, index=False)
    tmp.replace(path)


def _close(a: float, b: float, atol: float = 1e-12) -> bool:
    return bool(np.isclose(float(a), float(b), rtol=0.0, atol=atol, equal_nan=True))


def _exact_fidelity_fast(optimized, original) -> float | None:
    """Exact equivalence fast path without a cubic matrix product.

    ``Operator.equiv`` constructs both exact unitary matrices and compares them
    up to global phase in O(d^2).  Only a genuinely non-equivalent pair falls
    back to the O(d^3) average-fidelity product.
    """
    try:
        if Operator(optimized).equiv(Operator(original)):
            return 1.0
    except Exception:
        return None
    return average_gate_fidelity(optimized, original, max_qubits=10)


def revalidate_e3(csv_path: Path) -> tuple[Path, dict]:
    frame = pd.read_csv(csv_path)
    targets = frame.index[(frame["fidelity_source"] == "unavailable") & (frame["n_qubits"] <= 10)]
    optimizer = GreedyGateCancellation()
    metrics = MetricsCalculator()
    failures = []
    for idx in targets:
        row = frame.loc[idx]
        config = CircuitConfig(
            n_qubits=int(row.n_qubits), depth=int(row.depth),
            family=CircuitFamily.UNIVERSAL, seed=int(row.seed),
            entanglement_density=0.3,
        )
        circuit, _ = generate_circuit_batch(config, 1, metrics)[0]
        result = optimizer.optimize(circuit, target=circuit)
        checks = (
            int(result.original_size) == int(row.original_size),
            int(result.optimized_size) == int(row.optimized_size),
            _close(result.reduction, row.reduction),
        )
        if not all(checks):
            failures.append({"index": int(idx), "reason": "resource_metric_mismatch"})
            continue
        fidelity = _exact_fidelity_fast(result.optimized_circuit, circuit)
        if fidelity is None or not math.isfinite(fidelity):
            failures.append({"index": int(idx), "reason": "exact_still_unavailable"})
            continue
        valid = fidelity >= optimizer.fidelity_threshold
        frame.loc[idx, "fidelity"] = fidelity
        frame.loc[idx, "fidelity_source"] = "exact"
        frame.loc[idx, "valid_equivalent_output"] = valid
        frame.loc[idx, "success"] = bool(valid and result.reduction >= optimizer.success_reduction)
        frame.loc[idx, "analysis_reduction_itt"] = result.reduction if valid else 0.0
        frame.loc[idx, "fidelity_revalidation_status"] = "exact_revalidated"
        gc.collect()
    frame["fidelity_revalidation_status"] = frame["fidelity_revalidation_status"].fillna("not_needed")
    output = csv_path.with_name(csv_path.stem + "_revalidated.csv")
    _atomic_csv(frame, output)
    summary = {
        "dataset": "E3", "input_file": csv_path.name, "output_file": output.name,
        "target_rows": int(len(targets)), "revalidated_rows": int((frame.fidelity_revalidation_status == "exact_revalidated").sum()),
        "failures": failures,
    }
    return output, summary


def revalidate_e14(csv_path: Path) -> tuple[Path, dict]:
    frame = pd.read_csv(csv_path)
    frame["fidelity_revalidation_status"] = np.where(
        (frame["fidelity_source"] == "unavailable") & (frame["n_qubits"] > 10),
        "not_attempted_above_exact_limit", "not_needed",
    )
    targets = frame.index[(frame["fidelity_source"] == "unavailable") & (frame["n_qubits"] <= 10)]
    circuits = generate_extended_suite(mode="full", seed=42)
    by_hash = {circuit_sha256(bench.circuit): bench.circuit for bench in circuits}
    failures = []
    for idx in targets:
        row = frame.loc[idx]
        circuit = by_hash.get(str(row.input_circuit_sha256))
        if circuit is None:
            failures.append({"index": int(idx), "reason": "input_hash_not_reconstructed"})
            continue
        optimizer = build_optimizers(int(row.window_size))[str(row.optimizer)]
        result = optimizer.optimize(circuit, target=circuit)
        checks = (
            int(result.original_size) == int(row.baseline_gate_count),
            int(result.optimized_size) == int(row.optimized_gate_count),
            _close(result.reduction, row.reduction),
            circuit_sha256(result.optimized_circuit) == str(row.output_circuit_sha256),
        )
        if not all(checks):
            failures.append({"index": int(idx), "reason": "resource_or_output_hash_mismatch"})
            continue
        fidelity = _exact_fidelity_fast(result.optimized_circuit, circuit)
        if fidelity is None or not math.isfinite(fidelity):
            failures.append({"index": int(idx), "reason": "exact_still_unavailable"})
            continue
        valid = fidelity >= optimizer.fidelity_threshold
        frame.loc[idx, "fidelity"] = fidelity
        frame.loc[idx, "fidelity_source"] = "exact"
        frame.loc[idx, "valid_equivalent_output"] = valid
        frame.loc[idx, "success"] = bool(valid and result.reduction >= optimizer.success_reduction)
        frame.loc[idx, "analysis_reduction_itt"] = result.reduction if valid else 0.0
        frame.loc[idx, "fidelity_revalidation_status"] = "exact_revalidated"
        gc.collect()
    output = csv_path.with_name(csv_path.stem + "_revalidated.csv")
    _atomic_csv(frame, output)
    summary = {
        "dataset": "E14", "input_file": csv_path.name, "output_file": output.name,
        "target_rows": int(len(targets)), "revalidated_rows": int((frame.fidelity_revalidation_status == "exact_revalidated").sum()),
        "above_limit_unavailable_rows": int((frame.fidelity_revalidation_status == "not_attempted_above_exact_limit").sum()),
        "failures": failures,
    }
    return output, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--e3-csv", type=Path, required=True)
    parser.add_argument("--e14-csv", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    outputs = []
    for fn, path in ((revalidate_e3, args.e3_csv), (revalidate_e14, args.e14_csv)):
        output, summary = fn(path.resolve())
        outputs.append(summary)
        print(f"{summary['dataset']}: {summary['revalidated_rows']}/{summary['target_rows']} revalidated -> {output}")
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": Path(__file__).relative_to(PROJECT_ROOT).as_posix(),
        "source_sha256": file_sha256(Path(__file__).resolve()),
        "protocol_sha256": file_sha256(PROJECT_ROOT / "experiments" / "prepaper_protocol.json"),
        "outputs": outputs,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.summary.with_suffix(args.summary.suffix + ".tmp")
    tmp.write_text(json.dumps(record, indent=2), encoding="utf-8")
    tmp.replace(args.summary)


if __name__ == "__main__":
    main()
