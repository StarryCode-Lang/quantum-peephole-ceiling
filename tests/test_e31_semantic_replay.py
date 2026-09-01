"""Focused regression tests for the post-hoc E31 semantic replay gate."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest
import pandas as pd
from qiskit import QuantumCircuit, transpile

import scripts.audit_e31_semantic_replay as replay


FIXTURE_QASM = replay.PROJECT_ROOT / "tests/fixtures/e31_semantic_replay_hh.qasm"


def _fixture_bundle() -> tuple[dict, dict]:
    protocol_sha = "a" * 64
    design_sha = "b" * 64
    payload = {
        "run_id": "c" * 64,
        "run_order": 7,
        "protocol_sha256": protocol_sha,
        "input_circuit_sha256": "",
        "circuit_id": "fixture_hh",
        "circuit_family": "Fixture",
        "n_qubits": 1,
        "qasm_path": FIXTURE_QASM.relative_to(replay.PROJECT_ROOT).as_posix(),
        "listing_model": "LBL",
        "listing_seed": 123,
        "rule_set": "COMMUTATION_ONLY",
        "window_gates": 4,
        "budget_seconds": 10,
        "fidelity_threshold": 0.9999999999,
        "common_basis": ["rz", "sx", "x", "cx"],
    }
    original, listed, optimized = replay.reconstruct(payload)
    payload["input_circuit_sha256"] = replay.independent_circuit_sha256(original)
    normalized_input = transpile(
        listed, basis_gates=payload["common_basis"], optimization_level=0
    )
    normalized_output = transpile(
        optimized, basis_gates=payload["common_basis"], optimization_level=0
    )
    initial, final = int(normalized_input.size()), int(normalized_output.size())
    reduction = 100.0 * (1.0 - final / initial) if initial else 0.0
    operator = replay.independent_operator_metrics(original, optimized)
    recorded = {
        **{field: payload[field] for field in replay.IDENTITY_FIELDS},
        "design_manifest_sha256": design_sha,
        "status": "success",
        "valid_equivalent_output": True,
        "output_circuit_sha256": replay.independent_circuit_sha256(optimized),
        "original_common_basis_gate_count": initial,
        "optimized_common_basis_gate_count": final,
        "common_basis_gate_reduction_pct": reduction,
        "exact_fidelity": operator["independent_trace_average_gate_fidelity"],
    }
    return payload, recorded


def test_operator_metrics_are_exact_for_global_phase_and_non_equivalence():
    identity = QuantumCircuit(1)
    phased = QuantumCircuit(1, global_phase=0.731)
    equivalent = replay.independent_operator_metrics(identity, phased)
    assert equivalent["independent_trace_average_gate_fidelity"] == pytest.approx(1.0)
    assert equivalent["phase_aligned_identity_frobenius_norm"] == pytest.approx(
        0.0, abs=3e-8
    )

    x_gate = QuantumCircuit(1)
    x_gate.x(0)
    different = replay.independent_operator_metrics(identity, x_gate)
    assert different["trace_uout_dagger_uin_abs"] == pytest.approx(0.0)
    assert different["phase_aligned_identity_frobenius_norm"] == pytest.approx(2.0)
    assert different["phase_aligned_identity_relative_frobenius_norm"] == pytest.approx(
        math.sqrt(2.0)
    )
    assert different["independent_trace_average_gate_fidelity"] == pytest.approx(1 / 3)


def test_certificate_round_trips_qpy_and_fails_closed_on_record_drift(tmp_path: Path):
    payload, recorded = _fixture_bundle()
    qpy_path = tmp_path / "fixture.qpy"
    certificate = replay.certify_replay(
        payload, recorded, qpy_path, qpy_manifest_path="EPHEMERAL/fixture.qpy"
    )
    assert certificate["status"] == "PASS"
    assert replay.sha256_file(qpy_path) == certificate["qpy_sha256"]
    loaded = replay.load_one_qpy(qpy_path.read_bytes())
    assert replay.independent_circuit_sha256(loaded) == recorded["output_circuit_sha256"]
    assert certificate["replayed_original_common_basis_gate_count"] == recorded[
        "original_common_basis_gate_count"
    ]
    assert certificate["replayed_optimized_common_basis_gate_count"] == recorded[
        "optimized_common_basis_gate_count"
    ]

    for field, replacement, message in (
        ("output_circuit_sha256", "0" * 64, "output logical hash"),
        (
            "original_common_basis_gate_count",
            recorded["original_common_basis_gate_count"] + 1,
            "original common-basis gate count",
        ),
        ("common_basis_gate_reduction_pct", -77.0, "reduction_pct mismatch"),
        ("exact_fidelity", 0.5, "exact_fidelity mismatch"),
    ):
        mutated = copy.deepcopy(recorded)
        mutated[field] = replacement
        with pytest.raises(replay.ReplayFailure, match=message):
            replay.certify_replay(
                payload,
                mutated,
                tmp_path / f"bad_{field}.qpy",
                qpy_manifest_path=f"EPHEMERAL/bad_{field}.qpy",
            )


def test_two_cold_processes_ignore_pythonhashseed(tmp_path: Path):
    payload, recorded = _fixture_bundle()
    certificates = []
    for index, seed in enumerate(("0", "8675309")):
        certificates.append(
            replay.cold_replay(
                payload,
                recorded,
                tmp_path / f"cold_{index}.qpy",
                tmp_path / f"cold_{index}.json",
                python_hash_seed=seed,
                python_executable=Path(replay.sys.executable),
            )
        )
    assert replay.determinism_signature(certificates[0]) == replay.determinism_signature(
        certificates[1]
    )
    assert certificates[0]["qpy_sha256"] == certificates[1]["qpy_sha256"]


def test_replay_checkpoint_is_resumable_and_revalidates_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(replay, "PROJECT_ROOT", tmp_path)
    certificate_path = tmp_path / "certificate.json"
    qpy_path = tmp_path / "output.qpy"
    circuit = QuantumCircuit(1)
    output_hash = replay.independent_circuit_sha256(circuit)
    replay.atomic_json(
        certificate_path,
        {
            "status": "PASS",
            "run_id": "r1",
            "recorded_output_circuit_sha256": output_hash,
        },
    )
    replay.atomic_bytes(qpy_path, replay.qpy_bytes(circuit))
    checkpoint_path = tmp_path / "replay.sqlite3"

    checkpoint = replay.ReplayCheckpoint(checkpoint_path)
    checkpoint.commit_pass("r1", 1, certificate_path, qpy_path)
    checkpoint.close()

    resumed = replay.ReplayCheckpoint(checkpoint_path)
    row = resumed.passed()["r1"]
    replay.validate_pass_artifact(row, output_hash, expected_run_id="r1")
    resumed.close()

    qpy_path.write_bytes(b"drift")
    with pytest.raises(replay.ReplayFailure, match="QPY drift"):
        replay.validate_pass_artifact(row, output_hash, expected_run_id="r1")


def test_semantic_cells_collapse_only_budget_after_exact_invariant_check():
    payload, first = _fixture_bundle()
    first.update({"template_enabled": False, "trace": [{"iteration": 0}]})
    second = copy.deepcopy(first)
    second.update({"run_id": "d" * 64, "run_order": 8, "budget_seconds": 30})
    design = pd.DataFrame(
        [
            {
                **payload,
                "run_id": first["run_id"],
                "run_order": first["run_order"],
                "budget_seconds": first["budget_seconds"],
            },
            {
                **payload,
                "run_id": second["run_id"],
                "run_order": second["run_order"],
                "budget_seconds": second["budget_seconds"],
            },
        ]
    )
    cells = replay.build_semantic_cells(design, [first, second])
    assert len(cells) == 1
    assert cells[0]["successful_budget_seconds"] == [10, 30]
    assert {row["run_id"] for row in cells[0]["members"]} == {
        first["run_id"],
        second["run_id"],
    }

    for field, replacement in (
        ("output_circuit_sha256", "0" * 64),
        ("optimized_common_basis_gate_count", second["optimized_common_basis_gate_count"] + 1),
        ("common_basis_gate_reduction_pct", -1.0),
        ("exact_fidelity", 0.5),
        ("trace", [{"iteration": 999}]),
    ):
        drifted = copy.deepcopy(second)
        drifted[field] = replacement
        with pytest.raises(replay.ReplayFailure, match="cross-budget semantic disagreement"):
            replay.build_semantic_cells(design, [first, drifted])


def test_canary_selection_covers_every_family_listing_rule_window_stratum():
    records = []
    order = 0
    for family in ("A", "B"):
        for listing in ("LBL", "WCL", "RANDOM_TOPOLOGICAL"):
            for rule in ("COMMUTATION_ONLY", "COMMUTATION_PLUS_TEMPLATES"):
                for window in (4, 16, 64):
                    for budget in (1, 10):
                        run_id = f"r{order}"
                        records.append({
                            "run_id": run_id,
                            "run_order": order,
                            "circuit_family": family,
                            "listing_model": listing,
                            "rule_set": rule,
                            "window_gates": window,
                            "budget_seconds": budget,
                            "status": "success",
                        })
                        order += 1
    design = pd.DataFrame(records)
    selected = replay.select_canary_rows(design, records)
    assert len(selected) == 2 * 3 * 2 * 3
    observed = {
        (
            row["circuit_family"], row["listing_model"], row["rule_set"],
            row["window_gates"],
        )
        for row in selected
    }
    assert len(observed) == len(selected)

    missing = [row for row in records if not (
        row["circuit_family"] == "B"
        and row["listing_model"] == "WCL"
        and row["rule_set"] == "COMMUTATION_ONLY"
        and row["window_gates"] == 64
    )]
    with pytest.raises(replay.ReplayFailure, match="family/treatment branch coverage"):
        replay.select_canary_rows(pd.DataFrame(records), missing)


def test_formal_checkpoint_reader_fails_closed_on_sql_json_identity_drift(tmp_path: Path):
    checkpoint = tmp_path / "formal.sqlite3"
    import sqlite3

    connection = sqlite3.connect(checkpoint)
    connection.execute(
        "CREATE TABLE results (run_id TEXT PRIMARY KEY, run_order INTEGER, "
        "result_json TEXT, committed_utc TEXT)"
    )
    connection.execute(
        "INSERT INTO results VALUES (?, ?, ?, ?)",
        ("sql-id", 1, json.dumps({"run_id": "json-id", "run_order": 1}), "now"),
    )
    connection.commit()
    connection.close()
    with pytest.raises(replay.ReplayFailure, match="SQL identity"):
        replay.read_formal_checkpoint(checkpoint)
