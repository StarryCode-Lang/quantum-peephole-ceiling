"""Completion and schedule-identity gates for the E31 final seal."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

import analysis.e31_finalize_formal_run as finalizer
from analysis.e31_finalize_formal_run import read_complete_checkpoint, sqlite_snapshot


def _checkpoint(path: Path, n: int) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE results (run_id TEXT PRIMARY KEY, run_order INTEGER UNIQUE NOT NULL, "
        "result_json TEXT NOT NULL, committed_utc TEXT NOT NULL)"
    )
    for order in range(n):
        result = {"run_id": f"run-{order}", "run_order": order, "status": "success"}
        connection.execute(
            "INSERT INTO results VALUES (?, ?, ?, ?)",
            (result["run_id"], order, json.dumps(result), f"time-{order}"),
        )
    connection.commit()
    connection.close()


def _design(n: int) -> pd.DataFrame:
    return pd.DataFrame({"run_id": [f"run-{i}" for i in range(n)], "run_order": range(n)})


def test_complete_checkpoint_requires_exact_schedule_identity(tmp_path: Path):
    path = tmp_path / "checkpoint.sqlite3"
    _checkpoint(path, 3)
    results, metadata = read_complete_checkpoint(path, _design(3))
    assert results["run_order"].tolist() == [0, 1, 2]
    assert metadata["rows"] == 3
    assert metadata["status_counts"] == {"success": 3}


def test_incomplete_checkpoint_is_never_release_eligible(tmp_path: Path):
    path = tmp_path / "checkpoint.sqlite3"
    _checkpoint(path, 2)
    with pytest.raises(ValueError, match="incomplete"):
        read_complete_checkpoint(path, _design(3))


def test_foreign_run_id_is_rejected_even_with_complete_row_count(tmp_path: Path):
    path = tmp_path / "checkpoint.sqlite3"
    _checkpoint(path, 2)
    design = _design(2)
    design.loc[1, "run_id"] = "different"
    with pytest.raises(ValueError, match="keys differ"):
        read_complete_checkpoint(path, design)


def test_sqlite_snapshot_is_integral_and_complete(tmp_path: Path):
    source = tmp_path / "source.sqlite3"
    destination = tmp_path / "snapshot.sqlite3"
    _checkpoint(source, 4)
    sqlite_snapshot(source, destination)
    connection = sqlite3.connect(destination)
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert connection.execute("SELECT COUNT(*) FROM results").fetchone()[0] == 4
    connection.close()


def test_finalize_binds_analysis_packet_in_the_completion_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    checkpoint = tmp_path / "formal_run/checkpoint.sqlite3"
    checkpoint.parent.mkdir(parents=True)
    _checkpoint(checkpoint, 3)
    design = _design(3)
    design["input_circuit_sha256"] = ["a", "b", "c"]
    design["circuit_family"] = ["f1", "f2", "f3"]
    design_path = tmp_path / "design_manifest.csv"
    design.to_csv(design_path, index=False)
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps({"experiment_id": "E31-test"}), encoding="utf-8")
    gate_root = tmp_path / "data/v11/e31_factorial_pareto"
    gate_root.mkdir(parents=True)
    for path in (
        checkpoint.parent / "environment.json",
        gate_root / "formal_release_gate.json",
        gate_root / "preanalysis_method_erratum_gate.json",
        gate_root / "host_environment_limitation_gate.json",
        gate_root / "transitive_source_provenance_gate.json",
        gate_root / "posthoc_pareto_aggregation_gate.json",
        gate_root / "posthoc_contrast_expansion_gate.json",
        gate_root / "posthoc_family_inference_correction_gate.json",
        tmp_path / "release/e31_temporal_gate_binding_audit.json",
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(finalizer, "ROOT", tmp_path)
    monkeypatch.setattr(finalizer, "refuse_active_formal_processes", lambda: None)
    monkeypatch.setattr(
        finalizer, "validate_runtime_source_provenance",
        lambda checkpoint, results: {
            "resolved_source_count": 23,
            "dynamic_imports_not_proven": True,
        },
    )
    monkeypatch.setattr(
        finalizer, "validate_results",
        lambda design, results, protocol, **kwargs: results,
    )
    monkeypatch.setattr(
        finalizer, "validate_semantic_replay",
        lambda replay_dir, results, metadata: {
            "status": "PASS",
            "success_rows_verified_and_bound": 3,
            "unique_semantic_cells_replayed": 3,
            "artifacts": {
                "semantic_replay_gate.json": {"sha256": "a" * 64, "bytes": 1},
                "semantic_replay_manifest.json": {"sha256": "b" * 64, "bytes": 2},
            },
        },
    )
    temporal_path = tmp_path / "release/e31_temporal_gate_binding_audit.json"
    temporal_path.write_text(json.dumps({
        "status": "PASS_LIMITATION_BOUND_NO_RETROACTIVE_PRECOMMIT_CLAIM",
        "overall_temporal_provenance_rating": "PARTIAL",
        "formal_checkpoint_sha256": finalizer.sha256(checkpoint),
    }), encoding="utf-8")

    def fake_analysis(design, validated, protocol, output_dir, **kwargs):
        output_dir.mkdir(parents=True)
        gate = {
            "result_rows": len(design),
            "formal_requested": True,
            "dual_estimand_primary": {"status": "synthetic"},
            "factorial_model": {"status": "synthetic"},
            "pareto_inference_role": "EXPLORATORY_POSTHOC_AGGREGATION",
            "pareto_aggregation_sensitivity": {
                "status": "FOUR_SCHEME_FRONTIER_MEMBERSHIP_AUDITED",
                "treatment_cells": 72,
                "frontier_membership_agreement_all_schemes": True,
                "bounded_aggregation_invariant_frontier_claim_allowed": True,
                "disagreement_cell_count": 0,
                "disagreement_cells": [],
            },
        }
        for name in finalizer.FORMAL_ANALYSIS_FILENAMES:
            if name.endswith(".csv"):
                (output_dir / name).write_text("metric,value\nsynthetic,1\n", encoding="utf-8")
            else:
                (output_dir / name).write_text("{}", encoding="utf-8")
        (output_dir / "analysis_gate_audit.json").write_text(
            json.dumps(gate), encoding="utf-8"
        )
        return gate

    monkeypatch.setattr(finalizer, "write_analysis_packet", fake_analysis)
    def fake_correction(results, output_dir, **kwargs):
        output_dir.mkdir(parents=True)
        artifact = output_dir / "fixed_panel_factorial_71_descriptive.csv"
        artifact.write_text("coefficient,estimate\nsynthetic,1\n", encoding="utf-8")
        audit = {
            "status": "PASS_POSTHOC_FAMILY_INFERENCE_CORRECTION",
            "legacy_input_cluster_inference_valid": False,
            "n_independent_family_clusters": 15,
            "family_cluster_degrees_of_freedom": 14,
            "unseen_family_generalization_status": "BLOCKED",
            "artifacts": {
                artifact.name: {
                    "sha256": finalizer.sha256(artifact),
                    "bytes": artifact.stat().st_size,
                },
            },
        }
        (output_dir / "family_inference_correction_audit.json").write_text(
            json.dumps(audit), encoding="utf-8"
        )
        return audit

    monkeypatch.setattr(finalizer, "write_correction_packet", fake_correction)
    final_dir = checkpoint.parent / "final"
    analysis_dir = checkpoint.parent / "analysis"
    stale_analysis = analysis_dir.with_name(analysis_dir.name + f".{os.getpid()}.tmp")
    stale_analysis.mkdir()
    (stale_analysis / "stale.txt").write_text("stale", encoding="utf-8")
    manifest_path = finalizer.finalize(
        checkpoint, design_path, protocol_path, final_dir, analysis_dir
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["formal_analysis_gate_passed"] is True
    assert manifest["source_provenance_rating"] == "PARTIAL"
    assert manifest["complete_cryptographic_prerun_source_closure"] is False
    assert manifest["static_first_party_source_closure_count"] == 23
    assert manifest["dynamic_imports_not_proven"] is True
    assert manifest["temporal_gate_provenance_rating"] == "PARTIAL"
    assert manifest["independent_release_verification_required"] is True
    assert manifest["independent_release_verification_embedded_in_completion"] is False
    assert manifest["pareto_inference_role"] == "EXPLORATORY_POSTHOC_AGGREGATION"
    assert manifest["pareto_aggregation_functionals_preregistered"] is False
    assert manifest["pareto_frontier_membership_agreement_all_schemes"] is True
    assert manifest["pareto_aggregation_invariant_claim_allowed"] is True
    assert manifest["pareto_aggregation_disagreement_cell_count"] == 0
    assert manifest["marginal_contrast_family_fully_preregistered"] is False
    assert manifest["marginal_contrast_multiplicity_family_size"] == 30
    assert manifest["legacy_input_cluster_inference_valid"] is False
    assert manifest["family_inference_outer_cluster"] == "circuit_family"
    assert manifest["family_inference_n_independent_clusters"] == 15
    assert manifest["family_inference_degrees_of_freedom"] == 14
    assert manifest["unseen_family_generalization_status"] == "BLOCKED"
    assert manifest["semantic_replay"]["success_rows_verified_and_bound"] == 3
    assert set(manifest["analysis_artifacts"]) == set(finalizer.FORMAL_ANALYSIS_FILENAMES)
    for name, record in manifest["analysis_artifacts"].items():
        path = analysis_dir / name
        assert path.stat().st_size == record["bytes"]
        assert finalizer.sha256(path) == record["sha256"]
    for name, record in manifest["family_inference_artifacts"].items():
        path = analysis_dir / "family_inference" / name
        assert path.stat().st_size == record["bytes"]
        assert finalizer.sha256(path) == record["sha256"]


def test_install_seal_pair_rolls_back_first_move_when_second_move_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    temporary_analysis = tmp_path / "analysis.tmp"
    temporary_final = tmp_path / "final.tmp"
    analysis_dir = tmp_path / "analysis"
    final_dir = tmp_path / "final"
    temporary_analysis.mkdir()
    temporary_final.mkdir()
    (temporary_analysis / "a").write_text("analysis", encoding="utf-8")
    (temporary_final / "f").write_text("final", encoding="utf-8")
    real_replace = os.replace
    calls = 0

    def fail_second(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected second move failure")
        return real_replace(source, destination)

    monkeypatch.setattr(finalizer.os, "replace", fail_second)
    with pytest.raises(OSError, match="injected second move failure"):
        finalizer.install_seal_pair(
            temporary_analysis, analysis_dir, temporary_final, final_dir,
        )
    assert not analysis_dir.exists()
    assert not final_dir.exists()
    assert (temporary_analysis / "a").read_text(encoding="utf-8") == "analysis"
    assert (temporary_final / "f").read_text(encoding="utf-8") == "final"
