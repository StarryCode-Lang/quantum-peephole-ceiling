"""Run one frozen compiler-version panel inside an isolated Python environment.

The worker deliberately keeps structural outcomes separate from elapsed time.
It consumes already-materialized QASM inputs and never writes into the sealed
E31 packet.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
from qiskit import qasm2, transpile
from qiskit.quantum_info import Operator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _instruction_fingerprint(circuit) -> str:
    rows = []
    for instruction in circuit.data:
        operation = instruction.operation
        operation_name = (
            "unitary" if operation.name.startswith("unitary_") else operation.name
        )
        semantic_matrix_sha256 = None
        if operation_name == "unitary":
            matrix = np.asarray(Operator(operation).data, dtype=np.complex128)
            rounded = np.stack(
                [np.round(matrix.real, 12), np.round(matrix.imag, 12)], axis=-1
            )
            semantic_matrix_sha256 = hashlib.sha256(rounded.tobytes()).hexdigest()
        rows.append(
            {
                "name": operation_name,
                "qubits": [circuit.find_bit(qubit).index for qubit in instruction.qubits],
                "clbits": [circuit.find_bit(clbit).index for clbit in instruction.clbits],
                "params": [str(parameter) for parameter in operation.params],
                "semantic_matrix_sha256": semantic_matrix_sha256,
            }
        )
    payload = json.dumps(rows, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _canonical_gate_counts(circuit) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, count in circuit.count_ops().items():
        canonical = "unitary" if str(name).startswith("unitary_") else str(name)
        counts[canonical] = counts.get(canonical, 0) + int(count)
    return dict(sorted(counts.items()))


def _qiskit_optimize(circuit):
    return transpile(circuit, optimization_level=3, seed_transpiler=42)


def _cirq_optimize(circuit):
    import cirq
    from cirq.contrib.qasm_import import circuit_from_qasm
    from cirq.transformers import (
        drop_empty_moments,
        drop_negligible_operations,
        eject_z,
        merge_single_qubit_gates_to_phased_x_and_z,
        optimize_for_target_gateset,
    )

    converted = circuit_from_qasm(qasm2.dumps(circuit))
    converted = drop_empty_moments(converted)
    converted = drop_negligible_operations(converted)
    converted = optimize_for_target_gateset(converted, gateset=cirq.CZTargetGateset())
    converted = eject_z(converted)
    converted = merge_single_qubit_gates_to_phased_x_and_z(converted)
    converted = drop_empty_moments(converted)
    for index in range(circuit.num_qubits):
        converted.append(cirq.I(cirq.NamedQubit(f"q_{index}")))
    restored = qasm2.loads(
        cirq.qasm(converted),
        custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
    )
    restored.data = [item for item in restored.data if item.operation.name != "id"]
    return restored


def _tket_optimize(circuit):
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
    from pytket.passes import DecomposeBoxes, FullPeepholeOptimise

    converted = qiskit_to_tk(circuit)
    DecomposeBoxes().apply(converted)
    FullPeepholeOptimise().apply(converted)
    return tk_to_qiskit(converted, replace_implicit_swaps=True)


def _custom_optimize(circuit):
    from src.optimisation.phase1.greedy import GreedyGateCancellation

    result = GreedyGateCancellation(success_reduction=0.01).optimize(
        circuit, target=circuit
    )
    return result.optimized_circuit


OPTIMIZERS = {
    "qiskit": _qiskit_optimize,
    "cirq": _cirq_optimize,
    "tket": _tket_optimize,
    "custom": _custom_optimize,
}


def run(tool: str, panel_path: Path, output_path: Path, environment_id: str) -> int:
    optimizer = OPTIMIZERS[tool]
    with panel_path.open(newline="", encoding="utf-8") as handle:
        panel = list(csv.DictReader(handle))
    rows: list[dict[str, object]] = []
    for item in panel:
        qasm_path = ROOT / item["qasm_path"]
        if _sha256(qasm_path) != item["qasm_sha256"]:
            raise RuntimeError(f"frozen QASM hash mismatch: {qasm_path}")
        original = qasm2.loads(
            qasm_path.read_text(encoding="utf-8"),
            custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
        )
        started = time.perf_counter()
        status = "success"
        error = ""
        optimized = None
        try:
            optimized = optimizer(original)
        except Exception as exc:  # noqa: BLE001 - failures are panel outcomes
            status = "error"
            error = f"{type(exc).__name__}: {exc}"
        elapsed = time.perf_counter() - started
        row: dict[str, object] = {
            "environment_id": environment_id,
            "tool": tool,
            "circuit_family": item["circuit_family"],
            "circuit_id": item["circuit_id"],
            "n_qubits": int(item["n_qubits"]),
            "qasm_sha256": item["qasm_sha256"],
            "status": status,
            "runtime_seconds": elapsed,
            "error": error,
        }
        if optimized is not None:
            qasm_text = qasm2.dumps(optimized)
            qasm_directory = output_path.parent / "optimized_qasm"
            qasm_directory.mkdir(parents=True, exist_ok=True)
            qasm_name = hashlib.sha256(
                f"{item['circuit_family']}\0{item['circuit_id']}".encode("utf-8")
            ).hexdigest()[:20] + ".qasm"
            optimized_qasm_path = qasm_directory / qasm_name
            optimized_qasm_path.write_text(qasm_text, encoding="utf-8")
            # The durable artifact, rather than only the in-memory object, is
            # the object whose semantics and structural fingerprint we record.
            durable_optimized = qasm2.loads(
                qasm_text,
                custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
            )
            dimension = 2 ** original.num_qubits
            overlap = abs(
                np.trace(
                    Operator(original).data.conj().T
                    @ Operator(durable_optimized).data
                )
            ) / dimension
            row.update(
                {
                    "input_gate_count": original.size(),
                    "output_gate_count": durable_optimized.size(),
                    "output_depth": durable_optimized.depth(),
                    "output_gate_counts_json": json.dumps(
                        _canonical_gate_counts(durable_optimized), separators=(",", ":")
                    ),
                    "output_instruction_sha256": _instruction_fingerprint(durable_optimized),
                    "optimized_qasm_path": optimized_qasm_path.relative_to(ROOT).as_posix(),
                    "optimized_qasm_sha256": _sha256(optimized_qasm_path),
                    "unitary_trace_overlap": float(overlap),
                    "unitary_equivalence_tolerance": 1e-10,
                    "numerically_unitary_equivalent": bool(overlap >= 1.0 - 1e-10),
                    "exact_equivalent": bool(overlap >= 1.0 - 1e-10),
                }
            )
        rows.append(row)

    fieldnames = list(rows[0])
    for row in rows[1:]:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(output_path)
    metadata = {
        "environment_id": environment_id,
        "tool": tool,
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {
            name: _package_version(name)
            for name in ("qiskit", "numpy", "scipy", "cirq-core", "pytket", "pytket-qiskit")
        },
        "panel_sha256": _sha256(panel_path),
        "results_sha256": _sha256(output_path),
        "rows": len(rows),
    }
    metadata_path = output_path.with_name("environment.json")
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", required=True, choices=sorted(OPTIMIZERS))
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--environment-id", required=True)
    args = parser.parse_args()
    return run(args.tool, args.panel.resolve(), args.output.resolve(), args.environment_id)


if __name__ == "__main__":
    raise SystemExit(main())
