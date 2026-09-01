#!/usr/bin/env python3
"""Fail-closed, resumable semantic replay for every successful E31 row.

This is deliberately post-hoc and does not modify the frozen E31 execution
sources.  Each replay runs in a cold Python process, materializes a loadable QPY
output, independently recomputes the common-basis response and exact operator
metrics, and compares them with the append-only formal checkpoint.

The full audit is refused while the formal lock exists or while the formal
checkpoint is incomplete.  A two-process/different-PYTHONHASHSEED canary must
pass before the full replay can start.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from qiskit import qasm2, qpy, transpile
from qiskit.quantum_info import Operator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_PROTOCOL = PROJECT_ROOT / "experiments/e31_factorial_pareto_protocol.json"
DEFAULT_DESIGN = PROJECT_ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv"
DEFAULT_FORMAL = PROJECT_ROOT / "data/v11/e31_factorial_pareto/formal_run"
DEFAULT_OUTPUT = DEFAULT_FORMAL / "semantic_replay"
DEFAULT_ENVIRONMENT = DEFAULT_FORMAL / "environment.json"
DEFAULT_TRANSITIVE_GATE = (
    PROJECT_ROOT / "data/v11/e31_factorial_pareto/transitive_source_provenance_gate.json"
)
SCHEMA_VERSION = "1.0.0"
THREAD_LIMITS = {
    "OPENBLAS_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "RAYON_NUM_THREADS": "1",
}
IDENTITY_FIELDS = (
    "run_id",
    "run_order",
    "protocol_sha256",
    "input_circuit_sha256",
    "circuit_id",
    "circuit_family",
    "listing_model",
    "rule_set",
    "window_gates",
    "budget_seconds",
)
FLOAT_ABS_TOL = 5e-12


class ReplayFailure(RuntimeError):
    """A scientific or provenance invariant failed; never continue silently."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def atomic_json(path: Path, payload: Any) -> None:
    atomic_bytes(path, json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def circuit_payload(circuit) -> dict[str, Any]:
    """Recreate the frozen logical-circuit digest without calling its helper."""
    instructions = []
    for item in circuit.data:
        qubits = tuple(circuit.find_bit(bit).index for bit in item.qubits)
        clbits = tuple(circuit.find_bit(bit).index for bit in item.clbits)
        params = tuple(
            float(value)
            if isinstance(value, (int, float, np.integer, np.floating))
            else str(value)
            for value in item.operation.params
        )
        instructions.append((item.operation.name, qubits, clbits, params))
    return {
        "num_qubits": int(circuit.num_qubits),
        "num_clbits": int(circuit.num_clbits),
        "instructions": instructions,
    }


def independent_circuit_sha256(circuit) -> str:
    payload = json.dumps(circuit_payload(circuit), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def qpy_bytes(circuit) -> bytes:
    stream = io.BytesIO()
    qpy.dump(circuit, stream)
    return stream.getvalue()


def load_one_qpy(payload: bytes):
    circuits = qpy.load(io.BytesIO(payload))
    if len(circuits) != 1:
        raise ReplayFailure(f"QPY certificate contains {len(circuits)} circuits, expected one")
    return circuits[0]


def independent_operator_metrics(original, optimized) -> dict[str, float | int]:
    """Compute trace F_avg and phase-aligned Uout^dagger Uin residual.

    For unitary matrices, ||Uout^dagger Uin - phase*I||_F is exactly equal to
    ||Uin - phase*Uout||_F.  The Hilbert--Schmidt identity therefore gives the
    residual from Tr(Uout^dagger Uin) without materializing an O(d^3) product:
    sqrt(2*d - 2*|trace|).  This is an exact algebraic computation of the
    requested identity norm, not a sampled state-vector surrogate.
    """
    if original.num_qubits != optimized.num_qubits:
        raise ReplayFailure("input/output qubit counts differ")
    u_in = np.asarray(Operator.from_circuit(original).data, dtype=np.complex128)
    u_out = np.asarray(Operator.from_circuit(optimized).data, dtype=np.complex128)
    if u_in.shape != u_out.shape or u_in.ndim != 2 or u_in.shape[0] != u_in.shape[1]:
        raise ReplayFailure("input/output operators have incompatible shapes")
    dimension = int(u_in.shape[0])
    trace_product = complex(np.vdot(u_out, u_in))
    trace_abs = float(abs(trace_product))
    residual_sq = max(0.0, 2.0 * dimension - 2.0 * trace_abs)
    residual = float(math.sqrt(residual_sq))
    relative = float(residual / math.sqrt(dimension))
    f_avg = float((trace_abs * trace_abs + dimension) / (dimension * (dimension + 1)))
    phase = trace_product / trace_abs if trace_abs else complex(1.0, 0.0)
    return {
        "operator_dimension": dimension,
        "trace_uout_dagger_uin_real": float(trace_product.real),
        "trace_uout_dagger_uin_imag": float(trace_product.imag),
        "trace_uout_dagger_uin_abs": trace_abs,
        "phase_alignment_real": float(phase.real),
        "phase_alignment_imag": float(phase.imag),
        "phase_aligned_identity_frobenius_norm": residual,
        "phase_aligned_identity_relative_frobenius_norm": relative,
        "independent_trace_average_gate_fidelity": f_avg,
    }


def _listed_circuit(original, listing_model: str, listing_seed: int):
    # These are the same frozen treatment implementations, but result checking,
    # hashing, counting and semantic verification below are independent.
    from experiments.e31_listing_phase2b_interaction import random_topological_listing
    from src.optimisation.phase1.wire_traversal import WireTraversalPreprocessor

    if listing_model == "LBL":
        return original.copy()
    if listing_model == "WCL":
        return WireTraversalPreprocessor().preprocess(original)
    if listing_model == "RANDOM_TOPOLOGICAL":
        return random_topological_listing(original, int(listing_seed))
    raise ReplayFailure(f"unknown listing model: {listing_model!r}")


def reconstruct(payload: dict[str, Any]) -> tuple[Any, Any, Any]:
    from src.optimisation.phase2.template_matcher import Phase2bTemplateMatcher

    qasm_path = Path(str(payload["qasm_path"]))
    if not qasm_path.is_absolute():
        qasm_path = PROJECT_ROOT / qasm_path
    qasm_path = qasm_path.resolve()
    if not qasm_path.is_relative_to(PROJECT_ROOT) or not qasm_path.is_file():
        raise ReplayFailure(f"QASM path is absent or outside the project: {qasm_path}")
    original = qasm2.load(qasm_path, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    listed = _listed_circuit(
        original, str(payload["listing_model"]), int(payload["listing_seed"])
    )
    rule_set = str(payload["rule_set"])
    if rule_set not in {"COMMUTATION_ONLY", "COMMUTATION_PLUS_TEMPLATES"}:
        raise ReplayFailure(f"unknown rule set: {rule_set!r}")
    engine = Phase2bTemplateMatcher(
        max_iterations=100,
        fidelity_threshold=float(payload["fidelity_threshold"]),
        success_reduction=0.0,
        gather_window=int(payload["window_gates"]),
        template_enabled=rule_set == "COMMUTATION_PLUS_TEMPLATES",
        collect_trace=True,
    )
    optimized = engine.optimize_full_pipeline(listed, target=original).optimized_circuit
    return original, listed, optimized


def _require_close(name: str, observed: float, expected: Any) -> None:
    try:
        expected_float = float(expected)
    except (TypeError, ValueError) as exc:
        raise ReplayFailure(f"recorded {name} is not numeric: {expected!r}") from exc
    if not math.isfinite(observed) or not math.isfinite(expected_float):
        raise ReplayFailure(f"non-finite {name}: replay={observed}, recorded={expected_float}")
    if not math.isclose(observed, expected_float, rel_tol=0.0, abs_tol=FLOAT_ABS_TOL):
        raise ReplayFailure(f"{name} mismatch: replay={observed}, recorded={expected_float}")


def certify_replay(
    payload: dict[str, Any],
    recorded: dict[str, Any],
    qpy_path: Path,
    *,
    qpy_manifest_path: str | None = None,
) -> dict[str, Any]:
    """Reconstruct one successful row and return a complete passing certificate."""
    if recorded.get("status") != "success" or recorded.get("valid_equivalent_output") is not True:
        raise ReplayFailure("semantic replay accepts only recorded valid success rows")
    for field in IDENTITY_FIELDS:
        expected = payload.get(field)
        observed = recorded.get(field)
        if field in {"run_order", "window_gates", "budget_seconds"}:
            expected, observed = int(expected), int(observed)
        else:
            expected, observed = str(expected), str(observed)
        if observed != expected:
            raise ReplayFailure(
                f"recorded/design identity mismatch for {field}: {observed!r} != {expected!r}"
            )

    original, listed, optimized = reconstruct(payload)
    input_hash = independent_circuit_sha256(original)
    listed_hash = independent_circuit_sha256(listed)
    output_hash = independent_circuit_sha256(optimized)
    if input_hash != str(payload["input_circuit_sha256"]):
        raise ReplayFailure("parsed input logical hash differs from frozen design")
    if output_hash != str(recorded.get("output_circuit_sha256", "")):
        raise ReplayFailure("replayed output logical hash differs from formal checkpoint")

    basis = [str(item) for item in payload["common_basis"]]
    normalized_input = transpile(listed, basis_gates=basis, optimization_level=0)
    normalized_output = transpile(optimized, basis_gates=basis, optimization_level=0)
    input_count = int(normalized_input.size())
    output_count = int(normalized_output.size())
    reduction = 100.0 * (1.0 - output_count / input_count) if input_count else 0.0
    if input_count != int(recorded.get("original_common_basis_gate_count", -1)):
        raise ReplayFailure("original common-basis gate count mismatch")
    if output_count != int(recorded.get("optimized_common_basis_gate_count", -1)):
        raise ReplayFailure("optimized common-basis gate count mismatch")
    _require_close(
        "common_basis_gate_reduction_pct",
        reduction,
        recorded.get("common_basis_gate_reduction_pct"),
    )

    operator = independent_operator_metrics(original, optimized)
    _require_close(
        "exact_fidelity",
        float(operator["independent_trace_average_gate_fidelity"]),
        recorded.get("exact_fidelity"),
    )
    threshold = float(payload["fidelity_threshold"])
    if float(operator["independent_trace_average_gate_fidelity"]) < threshold:
        raise ReplayFailure("independent exact fidelity is below the frozen threshold")

    serialized = qpy_bytes(optimized)
    loaded = load_one_qpy(serialized)
    if independent_circuit_sha256(loaded) != output_hash:
        raise ReplayFailure("QPY round-trip changed the logical output circuit")
    atomic_bytes(qpy_path, serialized)
    certificate = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "audit_role": "POSTHOC_INDEPENDENT_DETERMINISTIC_SEMANTIC_REPLAY",
        "run_id": str(payload["run_id"]),
        "run_order": int(payload["run_order"]),
        "protocol_sha256": str(payload["protocol_sha256"]),
        "design_manifest_sha256": str(recorded["design_manifest_sha256"]),
        "input_circuit_sha256": input_hash,
        "listed_circuit_sha256": listed_hash,
        "replayed_output_circuit_sha256": output_hash,
        "recorded_output_circuit_sha256": str(recorded["output_circuit_sha256"]),
        "common_basis": basis,
        "replayed_original_common_basis_gate_count": input_count,
        "recorded_original_common_basis_gate_count": int(
            recorded["original_common_basis_gate_count"]
        ),
        "replayed_optimized_common_basis_gate_count": output_count,
        "recorded_optimized_common_basis_gate_count": int(
            recorded["optimized_common_basis_gate_count"]
        ),
        "reduction_formula": "100 * (1 - optimized_common_basis_count / original_common_basis_count)",
        "replayed_common_basis_gate_reduction_pct": reduction,
        "recorded_common_basis_gate_reduction_pct": float(
            recorded["common_basis_gate_reduction_pct"]
        ),
        **operator,
        "recorded_exact_fidelity": float(recorded["exact_fidelity"]),
        "fidelity_threshold": threshold,
        "operator_metric_method": (
            "exact dense Operator.from_circuit; trace inner product; phase-aligned "
            "Uout^dagger Uin Frobenius identity via Hilbert-Schmidt equality"
        ),
        "qpy_path": qpy_manifest_path or qpy_path.relative_to(PROJECT_ROOT).as_posix(),
        "qpy_sha256": sha256_bytes(serialized),
        "qpy_roundtrip_logical_hash_verified": True,
    }
    return certificate


def determinism_signature(certificate: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "input_circuit_sha256",
        "listed_circuit_sha256",
        "replayed_output_circuit_sha256",
        "replayed_original_common_basis_gate_count",
        "replayed_optimized_common_basis_gate_count",
        "replayed_common_basis_gate_reduction_pct",
        "trace_uout_dagger_uin_real",
        "trace_uout_dagger_uin_imag",
        "phase_aligned_identity_frobenius_norm",
        "independent_trace_average_gate_fidelity",
        "qpy_sha256",
    )
    return {field: certificate[field] for field in fields}


def _worker(payload_path: Path, result_path: Path, qpy_path: Path) -> int:
    try:
        bundle = json.loads(payload_path.read_text(encoding="utf-8"))
        certificate = certify_replay(
            bundle["payload"],
            bundle["recorded"],
            qpy_path,
            qpy_manifest_path=bundle.get("qpy_manifest_path"),
        )
        atomic_json(result_path, {"status": "PASS", "certificate": certificate})
        return 0
    except Exception as exc:  # fail-closed child boundary; parent retains exact class/message
        atomic_json(
            result_path,
            {"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)},
        )
        return 2


def cold_replay(
    payload: dict[str, Any],
    recorded: dict[str, Any],
    qpy_path: Path,
    result_path: Path,
    *,
    python_hash_seed: str,
    python_executable: Path | None = None,
) -> dict[str, Any]:
    python_executable = (python_executable or Path(sys.executable)).resolve()
    bundle_path = result_path.with_suffix(".payload.json")
    try:
        qpy_manifest_path = qpy_path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        # Canary/test outputs are intentionally ephemeral and are never admitted
        # to the full manifest.  Label them explicitly rather than pretending
        # that they are durable project artifacts.
        qpy_manifest_path = f"EPHEMERAL/{qpy_path.name}"
    atomic_json(
        bundle_path,
        {
            "payload": payload,
            "recorded": recorded,
            "qpy_manifest_path": qpy_manifest_path,
        },
    )
    env = os.environ.copy()
    env.update(THREAD_LIMITS)
    env["PYTHONHASHSEED"] = str(python_hash_seed)
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.run(
        [
            str(python_executable),
            str(Path(__file__).resolve()),
            "--worker-payload",
            str(bundle_path),
            "--worker-result",
            str(result_path),
            "--worker-qpy",
            str(qpy_path),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        creationflags=creationflags,
        timeout=None,
    )
    bundle_path.unlink(missing_ok=True)
    if not result_path.is_file():
        raise ReplayFailure(
            f"cold replay produced no result (exit={process.returncode}): {process.stderr[-1000:]}"
        )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if process.returncode != 0 or result.get("status") != "PASS":
        raise ReplayFailure(
            f"cold replay failed (exit={process.returncode}): "
            f"{result.get('error_type')}: {result.get('error')}"
        )
    return result["certificate"]


def read_formal_checkpoint(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=30)
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        raw = connection.execute(
            "SELECT run_id, run_order, result_json, committed_utc "
            "FROM results ORDER BY run_order"
        ).fetchall()
    finally:
        connection.close()
    if integrity != "ok":
        raise ReplayFailure(f"formal checkpoint integrity is {integrity!r}, expected 'ok'")
    rows = []
    for run_id, run_order, result_json, committed_utc in raw:
        row = json.loads(result_json)
        if str(row.get("run_id")) != str(run_id) or int(row.get("run_order", -1)) != int(
            run_order
        ):
            raise ReplayFailure("formal checkpoint SQL identity differs from result_json")
        row["_committed_utc"] = str(committed_utc)
        rows.append(row)
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status"))
        status_counts[status] = status_counts.get(status, 0) + 1
    orders = [int(row["run_order"]) for row in rows]
    return rows, {
        "sqlite_integrity": integrity,
        "committed_rows": len(rows),
        "unique_run_ids": len({str(row["run_id"]) for row in rows}),
        "unique_run_orders": len(set(orders)),
        "min_run_order": min(orders) if orders else None,
        "max_run_order": max(orders) if orders else None,
        "status_counts": dict(sorted(status_counts.items())),
        "first_committed_utc": rows[0]["_committed_utc"] if rows else None,
        "last_committed_utc": rows[-1]["_committed_utc"] if rows else None,
    }


def source_provenance(
    environment_path: Path, transitive_gate_path: Path
) -> dict[str, Any]:
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    transitive = json.loads(transitive_gate_path.read_text(encoding="utf-8"))
    required_gate_checks = {
        "status": transitive.get("status")
        == "POSTHOC_TRANSITIVE_SOURCE_LIMITATION_FROZEN_BEFORE_AGGREGATE_ANALYSIS",
        "partial closure": transitive.get("complete_cryptographic_prerun_source_closure")
        is False,
        "direct count": int(transitive.get("direct_frozen_source_count", -1)) == 7,
        "omitted count": int(transitive.get("omitted_source_count", -1)) == 16,
        "no row exclusion": transitive.get("row_exclusion_or_rerun_authorized") is False,
    }
    failed_gate_checks = [name for name, value in required_gate_checks.items() if not value]
    if failed_gate_checks:
        raise ReplayFailure(f"transitive provenance gate semantic drift: {failed_gate_checks}")
    expected_environment_hash = str(transitive.get("environment_sha256", ""))
    if sha256_file(environment_path) != expected_environment_hash:
        raise ReplayFailure("formal environment hash differs from the post-hoc transitive gate")
    checked: dict[str, str] = {}
    for path_text, expected in environment.get("source_sha256", {}).items():
        path = (PROJECT_ROOT / path_text).resolve()
        if not path.is_relative_to(PROJECT_ROOT) or not path.is_file():
            raise ReplayFailure(f"frozen direct source is absent/outside project: {path_text}")
        observed = sha256_file(path)
        if observed != str(expected):
            raise ReplayFailure(f"frozen direct source drift: {path_text}")
        checked[path_text] = observed
    omitted = transitive.get("omitted_first_party_import_closure", {})
    for path_text, record in omitted.items():
        path = (PROJECT_ROOT / path_text).resolve()
        if not path.is_relative_to(PROJECT_ROOT) or not path.is_file():
            raise ReplayFailure(f"post-hoc transitive source is absent/outside project: {path_text}")
        observed = sha256_file(path)
        if observed != str(record.get("sha256", "")):
            raise ReplayFailure(f"post-hoc transitive source drift: {path_text}")
        checked[path_text] = observed
    return {
        "environment_path": environment_path.relative_to(PROJECT_ROOT).as_posix(),
        "environment_sha256": expected_environment_hash,
        "transitive_gate_path": transitive_gate_path.relative_to(PROJECT_ROOT).as_posix(),
        "transitive_gate_sha256": sha256_file(transitive_gate_path),
        "source_count": len(checked),
        "source_sha256": dict(sorted(checked.items())),
        "provenance_limitation_preserved": (
            transitive.get("complete_cryptographic_prerun_source_closure") is False
        ),
    }


def validate_formal_inputs(
    design_path: Path,
    protocol_path: Path,
    formal_checkpoint_path: Path,
    *,
    require_complete: bool,
) -> tuple[pd.DataFrame, dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    design = pd.read_csv(design_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if not design["protocol_sha256"].astype(str).eq(sha256_file(protocol_path)).all():
        raise ReplayFailure("design is not bound to the current frozen protocol")
    rows, checkpoint_info = read_formal_checkpoint(formal_checkpoint_path)
    design_by_id = design.set_index("run_id", drop=False)
    if design["run_id"].duplicated().any() or design["run_order"].duplicated().any():
        raise ReplayFailure("design has duplicate run identities")
    if require_complete and len(rows) != len(design):
        raise ReplayFailure(
            f"formal checkpoint is incomplete: {len(rows)} / {len(design)} rows"
        )
    for row in rows:
        run_id = str(row["run_id"])
        if run_id not in design_by_id.index:
            raise ReplayFailure(f"formal checkpoint contains foreign run_id {run_id}")
        design_row = design_by_id.loc[run_id]
        if int(row["run_order"]) != int(design_row["run_order"]):
            raise ReplayFailure(f"run_order drift for {run_id}")
        if str(row.get("status")) not in set(protocol["failure_semantics"]["allowed_status"]):
            raise ReplayFailure(f"unrecognized formal status for {run_id}")
    return design, protocol, rows, checkpoint_info


def payload_for(design_row: pd.Series, protocol: dict[str, Any]) -> dict[str, Any]:
    payload = design_row.to_dict()
    payload["fidelity_threshold"] = protocol["semantic_contract"]["fidelity_threshold"]
    payload["common_basis"] = protocol["semantic_contract"]["common_basis"]
    return payload


SEMANTIC_CELL_FIELDS = (
    "input_circuit_sha256",
    "listing_model",
    "rule_set",
    "window_gates",
)
SEMANTIC_RESULT_FIELDS = (
    "output_circuit_sha256",
    "original_common_basis_gate_count",
    "optimized_common_basis_gate_count",
    "common_basis_gate_reduction_pct",
    "exact_fidelity",
    "valid_equivalent_output",
    "template_enabled",
    "trace",
)


def semantic_cell_id(row: dict[str, Any]) -> str:
    key = [str(row[field]) for field in SEMANTIC_CELL_FIELDS]
    return hashlib.sha256("|".join(key).encode("utf-8")).hexdigest()


def build_semantic_cells(
    design: pd.DataFrame, formal_rows: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Collapse only the scientifically inert budget dimension, fail closed.

    ``budget_seconds`` is enforced by the parent process and is never passed to
    the optimizer constructor.  A completed row may therefore share one replay
    with another completed budget only after every semantic output, count,
    fidelity and normalized trace is proven identical.
    """
    success = [row for row in formal_rows if row.get("status") == "success"]
    by_design_id = design.set_index("run_id", drop=False)
    grouped: dict[tuple[str, str, str, int], list[dict[str, Any]]] = {}
    for recorded in success:
        run_id = str(recorded["run_id"])
        if run_id not in by_design_id.index:
            raise ReplayFailure(f"successful row has no design row: {run_id}")
        design_row = by_design_id.loc[run_id]
        # Validate the complete recorded/design identity before it can enter a
        # collapsed semantic cell.
        for field in IDENTITY_FIELDS:
            left, right = recorded.get(field), design_row[field]
            if field in {"run_order", "window_gates", "budget_seconds"}:
                left, right = int(left), int(right)
            else:
                left, right = str(left), str(right)
            if left != right:
                raise ReplayFailure(f"recorded/design identity drift for {run_id}: {field}")
        if recorded.get("valid_equivalent_output") is not True:
            raise ReplayFailure(f"status=success row is not valid_equivalent_output: {run_id}")
        key = (
            str(recorded["input_circuit_sha256"]),
            str(recorded["listing_model"]),
            str(recorded["rule_set"]),
            int(recorded["window_gates"]),
        )
        grouped.setdefault(key, []).append(recorded)

    cells = []
    for key, members in grouped.items():
        members.sort(key=lambda row: int(row["run_order"]))
        representative = members[0]
        reference = {
            field: canonical_json_bytes(representative.get(field))
            for field in SEMANTIC_RESULT_FIELDS
        }
        design_invariants = None
        for member in members:
            run_id = str(member["run_id"])
            for field in SEMANTIC_RESULT_FIELDS:
                if canonical_json_bytes(member.get(field)) != reference[field]:
                    raise ReplayFailure(
                        f"cross-budget semantic disagreement in cell {key}: "
                        f"{run_id} field {field}"
                    )
            design_row = by_design_id.loc[run_id]
            invariants = (
                str(design_row["qasm_path"]),
                int(design_row["listing_seed"]),
                str(design_row["circuit_id"]),
                str(design_row["circuit_family"]),
                str(design_row["protocol_sha256"]),
            )
            if design_invariants is None:
                design_invariants = invariants
            elif invariants != design_invariants:
                raise ReplayFailure(f"cross-budget design disagreement in cell {key}")
        cell_id = semantic_cell_id(representative)
        cells.append(
            {
                "cell_id": cell_id,
                "key": dict(zip(SEMANTIC_CELL_FIELDS, key)),
                "representative": representative,
                "members": members,
                "successful_budget_seconds": sorted(
                    int(member["budget_seconds"]) for member in members
                ),
                "cross_budget_semantic_identity_verified": True,
            }
        )
    cells.sort(key=lambda cell: int(cell["representative"]["run_order"]))
    if sum(len(cell["members"]) for cell in cells) != len(success):
        raise ReplayFailure("semantic-cell partition does not cover every successful row once")
    return cells


def select_canary_rows(
    design: pd.DataFrame, formal_rows: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Select one success from every family/listing/rule/window stratum.

    Budget is deliberately omitted because the full replay separately proves
    exact cross-budget output identity before collapsing duplicate successes.
    Covering all 15 families and all 18 non-budget treatment branches is a
    stronger determinism challenge than one global example per rule branch.
    """
    successes = pd.DataFrame([row for row in formal_rows if row.get("status") == "success"])
    if successes.empty:
        raise ReplayFailure("formal checkpoint has no successful rows for the canary")
    merged = successes.merge(
        design[[
            "run_id", "circuit_family", "listing_model", "rule_set",
            "window_gates", "run_order",
        ]],
        on=[
            "run_id", "circuit_family", "listing_model", "rule_set",
            "window_gates", "run_order",
        ],
        how="inner",
        validate="one_to_one",
    )
    selected = (
        merged.sort_values("run_order", kind="stable")
        .groupby(
            ["circuit_family", "listing_model", "rule_set", "window_gates"],
            sort=True,
            as_index=False,
        )
        .head(1)
        .sort_values("run_order", kind="stable")
    )
    expected = {
        (family, listing, rule, int(window))
        for family in design["circuit_family"].astype(str).unique()
        for listing in design["listing_model"].astype(str).unique()
        for rule in design["rule_set"].astype(str).unique()
        for window in design["window_gates"].astype(int).unique()
    }
    observed = set(zip(
        selected["circuit_family"].astype(str),
        selected["listing_model"].astype(str),
        selected["rule_set"].astype(str),
        selected["window_gates"].astype(int),
    ))
    if observed != expected:
        raise ReplayFailure(f"canary lacks family/treatment branch coverage: {expected - observed}")
    by_id = {str(row["run_id"]): row for row in formal_rows}
    return [by_id[str(run_id)] for run_id in selected["run_id"]]


def run_canary(
    design: pd.DataFrame,
    protocol: dict[str, Any],
    formal_rows: list[dict[str, Any]],
    output_dir: Path,
    provenance: dict[str, Any],
    checkpoint_info: dict[str, Any],
    *,
    python_executable: Path | None = None,
    protocol_sha256: str | None = None,
    design_manifest_sha256: str | None = None,
) -> Path:
    by_id = design.set_index("run_id", drop=False)
    canaries = select_canary_rows(design, formal_rows)
    records = []
    with tempfile.TemporaryDirectory(prefix="e31_semantic_canary_") as temporary_text:
        temporary = Path(temporary_text)
        for index, recorded in enumerate(canaries):
            run_id = str(recorded["run_id"])
            payload = payload_for(by_id.loc[run_id], protocol)
            certificates = []
            for pass_index, seed in enumerate(("0", "8675309")):
                certificate = cold_replay(
                    payload,
                    recorded,
                    temporary / f"{index}_{pass_index}.qpy",
                    temporary / f"{index}_{pass_index}.json",
                    python_hash_seed=seed,
                    python_executable=python_executable,
                )
                certificates.append(certificate)
            first, second = map(determinism_signature, certificates)
            if first != second:
                raise ReplayFailure(
                    f"different PYTHONHASHSEED values changed replay signature for {run_id}"
                )
            records.append(
                {
                    "run_id": run_id,
                    "run_order": int(recorded["run_order"]),
                    "circuit_family": str(recorded["circuit_family"]),
                    "listing_model": str(recorded["listing_model"]),
                    "rule_set": str(recorded["rule_set"]),
                    "window_gates": int(recorded["window_gates"]),
                    "python_hash_seeds": ["0", "8675309"],
                    "cold_processes": 2,
                    "signature": first,
                }
            )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "gate": "E31_SEMANTIC_REPLAY_DETERMINISM_CANARY",
        "created_utc": utc_now(),
        "cold_processes_per_selected_row": 2,
        "different_python_hash_seeds": True,
        "all_family_listing_rule_window_strata_covered": True,
        "selected_strata": len(records),
        "selected_rows": records,
        "protocol_sha256": protocol_sha256 or sha256_file(DEFAULT_PROTOCOL),
        "design_manifest_sha256": design_manifest_sha256 or sha256_file(DEFAULT_DESIGN),
        "formal_checkpoint_boundary": checkpoint_info,
        "replay_script_sha256": sha256_file(Path(__file__).resolve()),
        "source_provenance": provenance,
    }
    gate_path = output_dir / "canary_gate.json"
    atomic_json(gate_path, gate)
    return gate_path


class ReplayCheckpoint:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path, timeout=30)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS passed ("
            "run_id TEXT PRIMARY KEY, run_order INTEGER UNIQUE NOT NULL, "
            "certificate_path TEXT NOT NULL, certificate_sha256 TEXT NOT NULL, "
            "qpy_path TEXT NOT NULL, qpy_sha256 TEXT NOT NULL, committed_utc TEXT NOT NULL)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS failures ("
            "run_id TEXT PRIMARY KEY, run_order INTEGER UNIQUE NOT NULL, "
            "error TEXT NOT NULL, committed_utc TEXT NOT NULL)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS cells ("
            "cell_id TEXT PRIMARY KEY, representative_run_id TEXT NOT NULL, "
            "cell_certificate_path TEXT NOT NULL, cell_certificate_sha256 TEXT NOT NULL, "
            "qpy_path TEXT NOT NULL, qpy_sha256 TEXT NOT NULL, committed_utc TEXT NOT NULL)"
        )
        self.connection.commit()

    def passed(self) -> dict[str, tuple[Any, ...]]:
        return {
            str(row[0]): row
            for row in self.connection.execute(
                "SELECT run_id, run_order, certificate_path, certificate_sha256, "
                "qpy_path, qpy_sha256 FROM passed"
            )
        }

    def failure_ids(self) -> set[str]:
        return {str(row[0]) for row in self.connection.execute("SELECT run_id FROM failures")}

    def cells(self) -> dict[str, tuple[Any, ...]]:
        return {
            str(row[0]): row
            for row in self.connection.execute(
                "SELECT cell_id, representative_run_id, cell_certificate_path, "
                "cell_certificate_sha256, qpy_path, qpy_sha256 FROM cells"
            )
        }

    def clear_failures(self) -> None:
        self.connection.execute("DELETE FROM failures")
        self.connection.commit()

    def commit_pass(
        self, run_id: str, run_order: int, certificate_path: Path, qpy_path: Path
    ) -> None:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.connection.execute(
                "INSERT INTO passed VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    run_order,
                    certificate_path.relative_to(PROJECT_ROOT).as_posix(),
                    sha256_file(certificate_path),
                    qpy_path.relative_to(PROJECT_ROOT).as_posix(),
                    sha256_file(qpy_path),
                    utc_now(),
                ),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def commit_cell_and_rows(
        self,
        cell_id: str,
        representative_run_id: str,
        cell_certificate_path: Path,
        qpy_path: Path,
        row_artifacts: list[tuple[str, int, Path]],
    ) -> None:
        """Atomically bind one reconstructed cell to all of its success rows."""
        cell_certificate_sha = sha256_file(cell_certificate_path)
        qpy_sha = sha256_file(qpy_path)
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.connection.execute(
                "INSERT INTO cells VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    cell_id,
                    representative_run_id,
                    cell_certificate_path.relative_to(PROJECT_ROOT).as_posix(),
                    cell_certificate_sha,
                    qpy_path.relative_to(PROJECT_ROOT).as_posix(),
                    qpy_sha,
                    utc_now(),
                ),
            )
            for run_id, run_order, row_certificate_path in row_artifacts:
                self.connection.execute(
                    "INSERT INTO passed VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        run_order,
                        row_certificate_path.relative_to(PROJECT_ROOT).as_posix(),
                        sha256_file(row_certificate_path),
                        qpy_path.relative_to(PROJECT_ROOT).as_posix(),
                        qpy_sha,
                        utc_now(),
                    ),
                )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def commit_failure(self, run_id: str, run_order: int, error: str) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO failures VALUES (?, ?, ?, ?)",
            (run_id, run_order, error, utc_now()),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


def validate_pass_artifact(
    row: tuple[Any, ...],
    expected_output_hash: str,
    *,
    expected_run_id: str | None = None,
    verify_qpy_roundtrip: bool = True,
) -> None:
    _, _, certificate_text, certificate_sha, qpy_text, qpy_sha = row
    certificate_path = (PROJECT_ROOT / certificate_text).resolve()
    qpy_path = (PROJECT_ROOT / qpy_text).resolve()
    if not certificate_path.is_relative_to(PROJECT_ROOT) or not qpy_path.is_relative_to(
        PROJECT_ROOT
    ):
        raise ReplayFailure("replay checkpoint artifact path escaped the project")
    if not certificate_path.is_file() or sha256_file(certificate_path) != certificate_sha:
        raise ReplayFailure(f"certificate drift or absence: {certificate_text}")
    if not qpy_path.is_file() or sha256_file(qpy_path) != qpy_sha:
        raise ReplayFailure(f"QPY drift or absence: {qpy_text}")
    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    if certificate.get("status") != "PASS":
        raise ReplayFailure(f"row certificate is not PASS: {certificate_text}")
    if expected_run_id is not None and str(certificate.get("run_id")) != expected_run_id:
        raise ReplayFailure(f"row certificate identity drift: {certificate_text}")
    if str(certificate.get("recorded_output_circuit_sha256")) != expected_output_hash:
        raise ReplayFailure(f"row certificate output drift: {certificate_text}")
    if verify_qpy_roundtrip:
        loaded = load_one_qpy(qpy_path.read_bytes())
        if independent_circuit_sha256(loaded) != expected_output_hash:
            raise ReplayFailure(f"QPY logical output drift: {qpy_text}")


def validate_cell_artifact(row: tuple[Any, ...], expected_output_hash: str) -> None:
    _, _, certificate_text, certificate_sha, qpy_text, qpy_sha = row
    certificate_path = (PROJECT_ROOT / certificate_text).resolve()
    qpy_path = (PROJECT_ROOT / qpy_text).resolve()
    if not certificate_path.is_relative_to(PROJECT_ROOT) or not qpy_path.is_relative_to(
        PROJECT_ROOT
    ):
        raise ReplayFailure("semantic-cell artifact path escaped the project")
    if not certificate_path.is_file() or sha256_file(certificate_path) != certificate_sha:
        raise ReplayFailure(f"semantic-cell certificate drift: {certificate_text}")
    if not qpy_path.is_file() or sha256_file(qpy_path) != qpy_sha:
        raise ReplayFailure(f"semantic-cell QPY drift: {qpy_text}")
    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    if certificate.get("replayed_output_circuit_sha256") != expected_output_hash:
        raise ReplayFailure(f"semantic-cell certificate output drift: {certificate_text}")
    loaded = load_one_qpy(qpy_path.read_bytes())
    if independent_circuit_sha256(loaded) != expected_output_hash:
        raise ReplayFailure(f"semantic-cell QPY logical output drift: {qpy_text}")


def row_binding_certificate(
    member: dict[str, Any],
    cell: dict[str, Any],
    cell_certificate_path: Path,
    qpy_path: Path,
) -> dict[str, Any]:
    """Bind a shared semantic-cell replay to one exact formal success row."""
    cell_certificate = json.loads(cell_certificate_path.read_text(encoding="utf-8"))
    if cell_certificate.get("status") != "PASS":
        raise ReplayFailure("cannot bind a row to a non-passing cell certificate")
    if str(member["output_circuit_sha256"]) != str(
        cell_certificate["replayed_output_circuit_sha256"]
    ):
        raise ReplayFailure("row output hash differs from its semantic-cell replay")
    comparisons = {
        "original_common_basis_gate_count": (
            int(member["original_common_basis_gate_count"]),
            int(cell_certificate["replayed_original_common_basis_gate_count"]),
        ),
        "optimized_common_basis_gate_count": (
            int(member["optimized_common_basis_gate_count"]),
            int(cell_certificate["replayed_optimized_common_basis_gate_count"]),
        ),
        "common_basis_gate_reduction_pct": (
            float(member["common_basis_gate_reduction_pct"]),
            float(cell_certificate["replayed_common_basis_gate_reduction_pct"]),
        ),
        "exact_fidelity": (
            float(member["exact_fidelity"]),
            float(cell_certificate["independent_trace_average_gate_fidelity"]),
        ),
    }
    for field, (recorded, replayed) in comparisons.items():
        if isinstance(recorded, int):
            if recorded != replayed:
                raise ReplayFailure(f"row/cell {field} mismatch")
        elif not math.isclose(recorded, replayed, rel_tol=0.0, abs_tol=FLOAT_ABS_TOL):
            raise ReplayFailure(f"row/cell {field} mismatch")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "audit_role": "E31_SUCCESS_ROW_TO_DETERMINISTIC_SEMANTIC_CELL_BINDING",
        "run_id": str(member["run_id"]),
        "run_order": int(member["run_order"]),
        "budget_seconds": int(member["budget_seconds"]),
        "semantic_cell_id": str(cell["cell_id"]),
        "semantic_cell_key": cell["key"],
        "successful_budget_seconds_in_cell": cell["successful_budget_seconds"],
        "cross_budget_semantic_identity_verified": True,
        "recorded_output_circuit_sha256": str(member["output_circuit_sha256"]),
        "recorded_original_common_basis_gate_count": int(
            member["original_common_basis_gate_count"]
        ),
        "recorded_optimized_common_basis_gate_count": int(
            member["optimized_common_basis_gate_count"]
        ),
        "recorded_common_basis_gate_reduction_pct": float(
            member["common_basis_gate_reduction_pct"]
        ),
        "recorded_exact_fidelity": float(member["exact_fidelity"]),
        "cell_certificate_path": cell_certificate_path.relative_to(PROJECT_ROOT).as_posix(),
        "cell_certificate_sha256": sha256_file(cell_certificate_path),
        "qpy_path": qpy_path.relative_to(PROJECT_ROOT).as_posix(),
        "qpy_sha256": sha256_file(qpy_path),
    }


def run_full_replay(
    design: pd.DataFrame,
    protocol: dict[str, Any],
    formal_rows: list[dict[str, Any]],
    output_dir: Path,
    provenance: dict[str, Any],
    checkpoint_info: dict[str, Any],
    *,
    python_executable: Path | None = None,
    max_replay_cells: int | None = None,
    retry_failed: bool = False,
    protocol_sha256: str | None = None,
    design_manifest_sha256: str | None = None,
) -> Path | None:
    successes = [row for row in formal_rows if row.get("status") == "success"]
    successes.sort(key=lambda row: int(row["run_order"]))
    semantic_cells = build_semantic_cells(design, formal_rows)
    by_id = design.set_index("run_id", drop=False)
    checkpoint = ReplayCheckpoint(output_dir / "checkpoint.sqlite3")
    try:
        if retry_failed:
            checkpoint.clear_failures()
        failures = checkpoint.failure_ids()
        if failures:
            raise ReplayFailure(
                f"prior fail-closed rows require explicit --retry-failed: {sorted(failures)[:5]}"
            )
        passed = checkpoint.passed()
        committed_cells = checkpoint.cells()
        expected_ids = {str(row["run_id"]) for row in successes}
        expected_cell_ids = {str(cell["cell_id"]) for cell in semantic_cells}
        if set(passed) - expected_ids:
            raise ReplayFailure("replay checkpoint contains a non-success or foreign run_id")
        if set(committed_cells) - expected_cell_ids:
            raise ReplayFailure("replay checkpoint contains a foreign semantic cell")
        cell_by_id = {str(cell["cell_id"]): cell for cell in semantic_cells}
        for cell_id, cell_row in committed_cells.items():
            expected_cell = cell_by_id[cell_id]
            expected_output = str(expected_cell["representative"]["output_circuit_sha256"])
            if str(cell_row[1]) != str(expected_cell["representative"]["run_id"]):
                raise ReplayFailure(f"semantic-cell representative drift: {cell_id}")
            validate_cell_artifact(cell_row, expected_output)
        for recorded in successes:
            run_id = str(recorded["run_id"])
            if run_id in passed:
                validate_pass_artifact(
                    passed[run_id],
                    str(recorded["output_circuit_sha256"]),
                    expected_run_id=run_id,
                    verify_qpy_roundtrip=False,
                )
        for cell in semantic_cells:
            cell_id = str(cell["cell_id"])
            member_ids = {str(member["run_id"]) for member in cell["members"]}
            bound_ids = member_ids.intersection(passed)
            if (cell_id in committed_cells) != (bound_ids == member_ids):
                raise ReplayFailure(
                    f"non-atomic/partial semantic-cell checkpoint state: {cell_id}"
                )
            if bound_ids and bound_ids != member_ids:
                raise ReplayFailure(f"partial row bindings for semantic cell: {cell_id}")
        pending_cells = [
            cell for cell in semantic_cells if str(cell["cell_id"]) not in committed_cells
        ]
        if max_replay_cells is not None:
            pending_cells = pending_cells[:max_replay_cells]
        for cell in pending_cells:
            recorded = cell["representative"]
            run_id, run_order = str(recorded["run_id"]), int(recorded["run_order"])
            cell_id = str(cell["cell_id"])
            qpy_path = output_dir / "outputs" / f"{cell_id}.qpy"
            child_result = output_dir / "working" / f"{cell_id}.json"
            cell_certificate_path = output_dir / "cells" / f"{cell_id}.json"
            try:
                certificate = cold_replay(
                    payload_for(by_id.loc[run_id], protocol),
                    recorded,
                    qpy_path,
                    child_result,
                    python_hash_seed="0",
                    python_executable=python_executable,
                )
                certificate.update(
                    {
                        "audit_role": "E31_UNIQUE_DETERMINISTIC_SEMANTIC_CELL_REPLAY",
                        "semantic_cell_id": cell_id,
                        "semantic_cell_key": cell["key"],
                        "successful_budget_seconds": cell["successful_budget_seconds"],
                        "formal_success_rows_bound": len(cell["members"]),
                        "cross_budget_semantic_identity_verified": True,
                    }
                )
                atomic_json(cell_certificate_path, certificate)
                row_artifacts = []
                for member in cell["members"]:
                    member_id, member_order = str(member["run_id"]), int(member["run_order"])
                    row_path = (
                        output_dir / "certificates" / f"{member_order:05d}_{member_id}.json"
                    )
                    atomic_json(
                        row_path,
                        row_binding_certificate(
                            member, cell, cell_certificate_path, qpy_path
                        ),
                    )
                    row_artifacts.append((member_id, member_order, row_path))
                checkpoint.commit_cell_and_rows(
                    cell_id,
                    run_id,
                    cell_certificate_path,
                    qpy_path,
                    row_artifacts,
                )
            except Exception as exc:
                checkpoint.commit_failure(run_id, run_order, f"{type(exc).__name__}: {exc}")
                raise

        passed = checkpoint.passed()
        committed_cells = checkpoint.cells()
        if len(passed) != len(successes) or len(committed_cells) != len(semantic_cells):
            return None
        row_entries = []
        for recorded in successes:
            run_id = str(recorded["run_id"])
            row = passed[run_id]
            validate_pass_artifact(
                row,
                str(recorded["output_circuit_sha256"]),
                expected_run_id=run_id,
                verify_qpy_roundtrip=False,
            )
            row_entries.append(
                {
                    "run_id": run_id,
                    "run_order": int(recorded["run_order"]),
                    "certificate_path": row[2],
                    "certificate_sha256": row[3],
                    "qpy_path": row[4],
                    "qpy_sha256": row[5],
                }
            )
        cell_entries = []
        for cell in semantic_cells:
            cell_id = str(cell["cell_id"])
            row = committed_cells[cell_id]
            expected_output = str(cell["representative"]["output_circuit_sha256"])
            validate_cell_artifact(row, expected_output)
            cell_entries.append(
                {
                    "semantic_cell_id": cell_id,
                    "semantic_cell_key": cell["key"],
                    "representative_run_id": row[1],
                    "successful_budget_seconds": cell["successful_budget_seconds"],
                    "formal_success_rows_bound": len(cell["members"]),
                    "cell_certificate_path": row[2],
                    "cell_certificate_sha256": row[3],
                    "qpy_path": row[4],
                    "qpy_sha256": row[5],
                }
            )
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "gate": "E31_ALL_SUCCESS_ROWS_INDEPENDENT_SEMANTIC_REPLAY",
            "created_utc": utc_now(),
            "scope": "every status=success row in the complete frozen 28,152-row E31 schedule",
            "formal_rows": len(formal_rows),
            "success_rows_verified_and_bound": len(successes),
            "unique_semantic_cells_replayed": len(semantic_cells),
            "budget_dimension_collapsed_only_after_exact_group_invariant_check": True,
            "non_success_rows_not_semantically_replayed": len(formal_rows) - len(successes),
            "all_success_rows_passed": True,
            "protocol_sha256": protocol_sha256 or sha256_file(DEFAULT_PROTOCOL),
            "design_manifest_sha256": design_manifest_sha256 or sha256_file(DEFAULT_DESIGN),
            "formal_checkpoint_boundary": checkpoint_info,
            "replay_script_sha256": sha256_file(Path(__file__).resolve()),
            "source_provenance": provenance,
            "semantic_cells": cell_entries,
            "row_bindings": row_entries,
        }
        manifest_path = output_dir / "semantic_replay_manifest.json"
        atomic_json(manifest_path, manifest)
        gate = {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "gate": manifest["gate"],
            "created_utc": manifest["created_utc"],
            "manifest_path": manifest_path.relative_to(PROJECT_ROOT).as_posix(),
            "manifest_sha256": sha256_file(manifest_path),
            "formal_rows": len(formal_rows),
            "success_rows_verified_and_bound": len(successes),
            "unique_semantic_cells_replayed": len(semantic_cells),
            "all_success_rows_passed": True,
            "semantic_method": "exact dense operator, not sampled fidelity",
            "provenance_rating_inherited": "PARTIAL",
        }
        gate_path = output_dir / "semantic_replay_gate.json"
        atomic_json(gate_path, gate)
        return gate_path
    finally:
        checkpoint.close()


def _production_main(args: argparse.Namespace) -> int:
    formal_dir = args.formal_dir.resolve()
    if (formal_dir / "formal.lock").exists():
        raise ReplayFailure("formal E31 execution is active; semantic replay is refused")
    design_path = args.design.resolve()
    protocol_path = args.protocol.resolve()
    checkpoint_path = formal_dir / "checkpoint.sqlite3"
    design, protocol, rows, checkpoint_info = validate_formal_inputs(
        design_path, protocol_path, checkpoint_path, require_complete=True
    )
    provenance = source_provenance(
        args.environment.resolve(), args.transitive_gate.resolve()
    )
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.canary:
        path = run_canary(
            design,
            protocol,
            rows,
            output_dir,
            provenance,
            checkpoint_info,
            python_executable=args.python_executable,
            protocol_sha256=sha256_file(protocol_path),
            design_manifest_sha256=sha256_file(design_path),
        )
        print(path)
        return 0
    canary_path = output_dir / "canary_gate.json"
    if not canary_path.is_file():
        raise ReplayFailure("full replay requires a passing canary_gate.json")
    canary = json.loads(canary_path.read_text(encoding="utf-8"))
    checks = {
        "status": canary.get("status") == "PASS",
        "protocol": canary.get("protocol_sha256") == sha256_file(protocol_path),
        "design": canary.get("design_manifest_sha256") == sha256_file(design_path),
        "script": canary.get("replay_script_sha256") == sha256_file(Path(__file__).resolve()),
        "checkpoint boundary": canary.get("formal_checkpoint_boundary") == checkpoint_info,
        "source provenance": canary.get("source_provenance") == provenance,
    }
    failed = [name for name, valid in checks.items() if not valid]
    if failed:
        raise ReplayFailure(f"canary binding drift: {failed}")
    gate_path = run_full_replay(
        design,
        protocol,
        rows,
        output_dir,
        provenance,
        checkpoint_info,
        python_executable=args.python_executable,
        max_replay_cells=args.max_replay_cells,
        retry_failed=args.retry_failed,
        protocol_sha256=sha256_file(protocol_path),
        design_manifest_sha256=sha256_file(design_path),
    )
    if gate_path is None:
        print("partial replay checkpoint committed; no PASS gate emitted")
    else:
        print(gate_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--canary", action="store_true")
    mode.add_argument("--full", action="store_true")
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--formal-dir", type=Path, default=DEFAULT_FORMAL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--environment", type=Path, default=DEFAULT_ENVIRONMENT)
    parser.add_argument("--transitive-gate", type=Path, default=DEFAULT_TRANSITIVE_GATE)
    parser.add_argument("--python-executable", type=Path)
    parser.add_argument("--max-replay-cells", type=int)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--worker-payload", type=Path)
    parser.add_argument("--worker-result", type=Path)
    parser.add_argument("--worker-qpy", type=Path)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    worker_values = (args.worker_payload, args.worker_result, args.worker_qpy)
    if any(value is not None for value in worker_values):
        if not all(value is not None for value in worker_values):
            parser.error("worker mode requires payload, result, and QPY paths")
        return _worker(args.worker_payload, args.worker_result, args.worker_qpy)
    if not args.canary and not args.full:
        parser.error("choose --canary or --full")
    if args.max_replay_cells is not None and args.max_replay_cells < 0:
        parser.error("--max-replay-cells must be non-negative")
    if args.canary and (args.max_replay_cells is not None or args.retry_failed):
        parser.error("replay-only options cannot be used with --canary")
    try:
        return _production_main(args)
    except ReplayFailure as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
