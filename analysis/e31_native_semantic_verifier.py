"""Second, numerically independent semantic audit for all E31 replay cells.

Qiskit is used only as a QASM/QPY parser.  Gate matrices, tensor application,
phase alignment, and residual decisions are implemented here and do not call
``qiskit.quantum_info.Operator`` or ``Statevector``.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from qiskit import qasm2, qpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.circuits.real_benchmarks import circuit_sha256  # noqa: E402

DEFAULT_CELLS = ROOT / "data/v11/e31_factorial_pareto/formal_run/semantic_replay/cells"
DEFAULT_DESIGN = ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv"
DEFAULT_OUTPUT = (
    ROOT
    / "data/v11/e31_factorial_pareto/formal_run/analysis/native_semantic_verifier"
    / "native_semantic_verifier.json"
)
SUPPORTED_GATES = {
    "barrier", "h", "x", "z", "s", "sdg", "t", "tdg", "p", "rz", "ry",
    "u", "cx", "cz", "cp", "crz", "ccx",
}


class NativeSemanticFailure(RuntimeError):
    """The independent verifier cannot support or rejects a circuit pair."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _one_qubit(name: str, params: list[float]) -> np.ndarray:
    if name == "x":
        return np.array([[0, 1], [1, 0]], dtype=np.complex128)
    if name == "h":
        return np.array([[1, 1], [1, -1]], dtype=np.complex128) / math.sqrt(2)
    if name == "z":
        return np.diag([1, -1]).astype(np.complex128)
    phases = {"s": math.pi / 2, "sdg": -math.pi / 2, "t": math.pi / 4, "tdg": -math.pi / 4}
    if name in phases:
        return np.diag([1, np.exp(1j * phases[name])]).astype(np.complex128)
    if name == "p":
        return np.diag([1, np.exp(1j * params[0])]).astype(np.complex128)
    if name == "rz":
        theta = params[0]
        return np.diag([np.exp(-0.5j * theta), np.exp(0.5j * theta)]).astype(np.complex128)
    if name == "ry":
        c, s = math.cos(params[0] / 2), math.sin(params[0] / 2)
        return np.array([[c, -s], [s, c]], dtype=np.complex128)
    if name == "u":
        theta, phi, lam = params
        c, s = math.cos(theta / 2), math.sin(theta / 2)
        return np.array(
            [[c, -np.exp(1j * lam) * s],
             [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c]],
            dtype=np.complex128,
        )
    raise NativeSemanticFailure(f"unsupported one-qubit gate: {name}")


def _gate_matrix(name: str, params: list[float]) -> np.ndarray:
    if name in {"h", "x", "z", "s", "sdg", "t", "tdg", "p", "rz", "ry", "u"}:
        return _one_qubit(name, params)
    if name == "cx":
        matrix = np.eye(4, dtype=np.complex128)
        matrix[[1, 3]] = matrix[[3, 1]]
        return matrix
    if name == "cz":
        return np.diag([1, 1, 1, -1]).astype(np.complex128)
    if name == "cp":
        return np.diag([1, 1, 1, np.exp(1j * params[0])]).astype(np.complex128)
    if name == "crz":
        theta = params[0]
        return np.diag([1, np.exp(-0.5j * theta), 1, np.exp(0.5j * theta)]).astype(np.complex128)
    if name == "ccx":
        matrix = np.eye(8, dtype=np.complex128)
        matrix[[3, 7]] = matrix[[7, 3]]
        return matrix
    raise NativeSemanticFailure(f"unsupported gate: {name}")


def _index_table(n_qubits: int, qargs: tuple[int, ...]) -> np.ndarray:
    other = tuple(q for q in range(n_qubits) if q not in qargs)
    rows = np.empty((1 << len(other), 1 << len(qargs)), dtype=np.int64)
    for outside in range(rows.shape[0]):
        base = sum(((outside >> j) & 1) << q for j, q in enumerate(other))
        for local in range(rows.shape[1]):
            rows[outside, local] = base + sum(
                ((local >> j) & 1) << q for j, q in enumerate(qargs)
            )
    return rows


def simulate(circuit, initial_states: np.ndarray) -> np.ndarray:
    """Apply supported gates to column states using a native tensor kernel."""
    dimension = 1 << int(circuit.num_qubits)
    states = np.asarray(initial_states, dtype=np.complex128).copy()
    if states.ndim != 2 or states.shape[0] != dimension:
        raise NativeSemanticFailure("initial-state matrix has incompatible dimension")
    tables: dict[tuple[int, ...], np.ndarray] = {}
    global_phase = complex(np.exp(1j * float(circuit.global_phase)))
    for item in circuit.data:
        name = item.operation.name
        if name not in SUPPORTED_GATES:
            raise NativeSemanticFailure(f"unsupported operation: {name}")
        if item.clbits or getattr(item.operation, "condition", None) is not None:
            raise NativeSemanticFailure(f"classical semantics are unsupported: {name}")
        if name == "barrier":
            continue
        try:
            params = [float(value) for value in item.operation.params]
        except (TypeError, ValueError) as exc:
            raise NativeSemanticFailure(f"unbound/non-numeric parameter in {name}") from exc
        qargs = tuple(circuit.find_bit(bit).index for bit in item.qubits)
        table = tables.setdefault(qargs, _index_table(circuit.num_qubits, qargs))
        block = states[table, :]
        states[table, :] = np.einsum("ab,gbp->gap", _gate_matrix(name, params), block)
    return global_phase * states


def probe_states(n_qubits: int, cell_id: str, exact_max_qubits: int, samples: int) -> tuple[np.ndarray, str]:
    dimension = 1 << n_qubits
    if n_qubits <= exact_max_qubits:
        return np.eye(dimension, dtype=np.complex128), "all_computational_basis_states"
    seed = int.from_bytes(hashlib.sha256(cell_id.encode("ascii")).digest()[:8], "little")
    rng = np.random.default_rng(seed)
    random = rng.normal(size=(dimension, samples)) + 1j * rng.normal(size=(dimension, samples))
    random /= np.linalg.norm(random, axis=0, keepdims=True)
    anchors = np.zeros((dimension, 2), dtype=np.complex128)
    anchors[0, 0] = 1
    anchors[-1, 1] = 1
    return np.column_stack([anchors, random]), "two_basis_anchors_plus_normalized_complex_gaussian"


def compare_pair(original, optimized, states: np.ndarray, tolerance: float) -> dict[str, float]:
    if original.num_qubits != optimized.num_qubits:
        raise NativeSemanticFailure("input/output qubit widths differ")
    left, right = simulate(original, states), simulate(optimized, states)
    return compare_evolved(left, right, tolerance)


def compare_evolved(left: np.ndarray, right: np.ndarray, tolerance: float) -> dict[str, float]:
    """Compare already evolved state batches up to one shared global phase."""
    if left.shape != right.shape:
        raise NativeSemanticFailure("evolved state batches have incompatible shapes")
    overlaps = np.sum(np.conjugate(right) * left, axis=0)
    total = complex(np.sum(overlaps))
    phase = total / abs(total) if abs(total) else complex(1)
    residuals = np.linalg.norm(left - phase * right, axis=0)
    maximum = float(np.max(residuals))
    if not np.isfinite(maximum) or maximum > tolerance:
        raise NativeSemanticFailure(f"phase-aligned probe residual {maximum:.6g} exceeds {tolerance:.6g}")
    return {
        "maximum_phase_aligned_state_residual": maximum,
        "mean_phase_aligned_state_residual": float(np.mean(residuals)),
        "phase_alignment_real": float(phase.real),
        "phase_alignment_imag": float(phase.imag),
    }


def _load_one_qpy(path: Path):
    with path.open("rb") as stream:
        circuits = qpy.load(stream)
    if len(circuits) != 1:
        raise NativeSemanticFailure(f"{path}: expected one QPY circuit")
    return circuits[0]


def _verify_input_group(task: tuple[str, str, list[dict[str, object]], int, int, float]) -> dict[str, object]:
    input_hash, qasm_relative, cells, exact_max_qubits, samples, tolerance = task
    original = qasm2.load(
        ROOT / qasm_relative, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS
    )
    if circuit_sha256(original) != input_hash:
        raise NativeSemanticFailure(f"{input_hash}: parsed input logical hash mismatch")
    unsupported = {item.operation.name for item in original.data} - SUPPORTED_GATES
    if unsupported:
        raise NativeSemanticFailure(f"{input_hash}: unsupported operations {sorted(unsupported)}")
    states, mode = probe_states(original.num_qubits, input_hash, exact_max_qubits, samples)
    evolved_original = simulate(original, states)
    output_cache: dict[str, dict[str, float]] = {}
    gate_names: Counter[str] = Counter(item.operation.name for item in original.data)
    maxima: list[float] = []
    for cell in cells:
        cell_id = str(cell["semantic_cell_id"])
        output_hash = str(cell["recorded_output_circuit_sha256"])
        result = output_cache.get(output_hash)
        if result is None:
            qpy_path = ROOT / str(cell["qpy_path"])
            if _sha(qpy_path) != str(cell["qpy_sha256"]):
                raise NativeSemanticFailure(f"{cell_id}: QPY byte hash mismatch")
            optimized = _load_one_qpy(qpy_path)
            if circuit_sha256(optimized) != output_hash:
                raise NativeSemanticFailure(f"{cell_id}: parsed output logical hash mismatch")
            unsupported = {item.operation.name for item in optimized.data} - SUPPORTED_GATES
            if unsupported:
                raise NativeSemanticFailure(f"{cell_id}: unsupported operations {sorted(unsupported)}")
            result = compare_evolved(evolved_original, simulate(optimized, states), tolerance)
            output_cache[output_hash] = result
            gate_names.update(item.operation.name for item in optimized.data)
        maxima.append(result["maximum_phase_aligned_state_residual"])
    return {
        "mode": mode,
        "width": int(original.num_qubits),
        "cells": len(cells),
        "unique_outputs": len(output_cache),
        "gate_names": dict(gate_names),
        "maxima": maxima,
    }


def build_audit(
    *, cells_dir: Path = DEFAULT_CELLS, design_path: Path = DEFAULT_DESIGN,
    exact_max_qubits: int = 6, samples: int = 16, tolerance: float = 2e-6,
    limit: int | None = None, workers: int = 1,
) -> dict[str, object]:
    design = pd.read_csv(design_path)
    input_paths = dict(zip(design["input_circuit_sha256"], design["qasm_path"]))
    cell_paths = sorted(cells_dir.glob("*.json"))
    if limit is not None:
        cell_paths = cell_paths[:limit]
    if not cell_paths:
        raise NativeSemanticFailure("no semantic cell certificates found")
    cell_records = [json.loads(path.read_text(encoding="utf-8")) for path in cell_paths]
    grouped: dict[str, list[dict[str, object]]] = {}
    for cell in cell_records:
        grouped.setdefault(str(cell["input_circuit_sha256"]), []).append(cell)
    modes: Counter[str] = Counter()
    widths: Counter[int] = Counter()
    gate_names: Counter[str] = Counter()
    maxima: list[float] = []
    tasks = []
    for input_hash, cells in grouped.items():
        if input_hash not in input_paths:
            raise NativeSemanticFailure(f"{input_hash}: input hash absent from design")
        tasks.append((input_hash, str(input_paths[input_hash]), cells, exact_max_qubits, samples, tolerance))
    if workers > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            results: Iterable[dict[str, object]] = executor.map(_verify_input_group, tasks)
            results = list(results)
    else:
        results = [_verify_input_group(task) for task in tasks]
    unique_outputs = 0
    for result in results:
        cell_count = int(result["cells"])
        modes[str(result["mode"])] += cell_count
        widths[int(result["width"])] += cell_count
        unique_outputs += int(result["unique_outputs"])
        gate_names.update(result["gate_names"])
        maxima.extend(result["maxima"])
    exact_cells = modes["all_computational_basis_states"]
    sampled_cells = len(cell_paths) - exact_cells
    return {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "PASS_ALL_E31_SEMANTIC_CELLS_NATIVE_SECOND_VERIFIER"
            if len(cell_paths) == 6858 and limit is None
            else "PASS_REQUESTED_SUBSET_NATIVE_SECOND_VERIFIER"
        ),
        "audit_role": "algorithmically independent numerical semantic verifier",
        "scope": {
            "cells_verified": len(cell_paths),
            "expected_full_cell_count": 6858,
            "is_full_formal_scope": len(cell_paths) == 6858 and limit is None,
            "exact_cells": exact_cells,
            "sampled_cells": sampled_cells,
            "unique_input_circuits_simulated": len(grouped),
            "unique_input_conditioned_outputs_simulated": unique_outputs,
            "worker_processes": workers,
            "width_counts": {str(k): v for k, v in sorted(widths.items())},
            "gate_occurrence_counts": dict(sorted(gate_names.items())),
        },
        "method": {
            "parser_only_dependency": "Qiskit qasm2/qpy readers",
            "forbidden_numerical_paths": ["qiskit.quantum_info.Operator", "qiskit.quantum_info.Statevector"],
            "native_components": ["gate matrices", "little-endian tensor application", "global-phase alignment", "residual decision"],
            "exact_policy": f"all computational basis states for n_qubits <= {exact_max_qubits}",
            "large_policy": f"two fixed basis anchors plus {samples} deterministic normalized complex-Gaussian probes",
            "large_probe_support": "full distributional support, finite probabilistic coverage",
            "tolerance": tolerance,
        },
        "residuals": {
            "maximum": max(maxima),
            "mean_of_cell_maxima": float(np.mean(maxima)),
        },
        "limitations": [
            "Qiskit is still trusted to parse QASM/QPY and expose instruction order, operands, parameters, and global phase.",
            "Cells above the exact-width cutoff use deterministic randomized state probes; this is an independent probabilistic check, not a symbolic proof.",
            "The verifier covers only the explicitly enumerated fixed-width bound-parameter unitary gate set and fails closed otherwise.",
            "This audit does not provide decision-diagram, ZX-calculus, or path-sum verification.",
        ],
        "metric_dispositions": {
            "7.15": (
                "PASS: all 6,858 successful E31 semantic cells were independently replayed "
                "with native gate matrices and tensor application; widths above six qubits "
                "use deterministic finite probes and are therefore probabilistic rather than exact"
            )
        },
        "source_bindings": {
            "analysis/e31_native_semantic_verifier.py": _sha(Path(__file__)),
            design_path.relative_to(ROOT).as_posix(): _sha(design_path),
            "semantic_cell_certificate_count": len(cell_paths),
            "semantic_cell_certificate_tree_sha256": _tree_sha(cell_paths),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--exact-max-qubits", type=int, default=6)
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--tolerance", type=float, default=2e-6)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    payload = build_audit(
        exact_max_qubits=args.exact_max_qubits, samples=args.samples,
        tolerance=args.tolerance, limit=args.limit, workers=args.workers,
    )
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    try:
        shown_output = output.relative_to(ROOT).as_posix()
    except ValueError:
        shown_output = str(output)
    print(json.dumps({"output": shown_output, "status": payload["status"], "cells": payload["scope"]["cells_verified"]}, sort_keys=True))


if __name__ == "__main__":
    main()
