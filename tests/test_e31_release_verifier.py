"""Independent release-verifier tests for sealed E31 evidence."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.verify_prepaper_release_manifest as verifier


@pytest.fixture(autouse=True)
def _stub_full_semantic_replay_verification(monkeypatch: pytest.MonkeyPatch):
    """Keep broad release fixtures small; replay has focused verifier tests."""
    monkeypatch.setattr(verifier, "_verify_e31_semantic_replay", lambda *args: 0)
    monkeypatch.setattr(verifier, "_verify_e31_family_inference", lambda *args: 0)


@pytest.mark.parametrize("value", ["yes", "", "null", float("nan")])
def test_strict_boolean_parser_rejects_noncontract_values(value: object):
    with pytest.raises(RuntimeError, match="invalid serialized boolean"):
        verifier._strict_bool_series(pd.Series([value]), label="test")


def test_strict_boolean_parser_accepts_explicit_contract_encodings():
    parsed = verifier._strict_bool_series(
        pd.Series([True, False, "true", "FALSE", "1", "0"]), label="test"
    )
    assert parsed.tolist() == [True, False, True, False, True, False]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_independent_receipt_rehashes_bindings_and_checks_inference_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    created = "2026-08-27T13:31:28.448163+00:00"
    artifacts: dict[str, dict[str, object]] = {}
    names = {
        "formal_completion_manifest": "seal.json",
        "formal_results": "results.csv",
        "analysis_gate": "analysis.json",
        "family_inference_correction_audit": "family.json",
        "semantic_replay_gate": "semantic_gate.json",
        "semantic_replay_manifest": "semantic_manifest.json",
        "temporal_gate_binding_audit": "temporal.json",
        "independent_verifier_source": "verifier.py",
    }
    for name, relative in names.items():
        target = tmp_path / relative
        if name == "formal_completion_manifest":
            _write_json(target, {
                "status": "FORMAL_COMPLETE_PENDING_INDEPENDENT_RELEASE_VERIFICATION",
                "created_utc": created,
            })
        else:
            target.write_text(name, encoding="utf-8")
        artifacts[name] = {
            "path": relative,
            "sha256": _sha(target),
            "bytes": target.stat().st_size,
        }
    receipt = {
        "schema_version": "1.0.0",
        "status": "PASS_E31_INDEPENDENT_RELEASE_VERIFICATION",
        "created_utc": "2026-08-28T00:00:00+00:00",
        "checked_artifact_count": 34_032,
        "formal_rows": 28_152,
        "success_rows_semantically_replayed": 20_314,
        "unique_semantic_cells_replayed": 6_858,
        "semantic_identity_check": "phase-aligned identity norm and fidelity",
        "outer_inference_cluster": "circuit_family",
        "n_independent_family_clusters": 15,
        "family_cluster_degrees_of_freedom": 14,
        "legacy_input_cluster_inference_valid": False,
        "unseen_family_generalization_status": "BLOCKED",
        "source_provenance_rating": "PARTIAL",
        "temporal_gate_provenance_rating": "PARTIAL",
        "artifacts": artifacts,
    }
    receipt_path = tmp_path / "receipt.json"
    _write_json(receipt_path, receipt)
    assert verifier._verify_e31_independent_receipt(receipt_path) == 24
    receipt["unseen_family_generalization_status"] = "PASS"
    _write_json(receipt_path, receipt)
    with pytest.raises(RuntimeError, match="unseen_family_generalization_status"):
        verifier._verify_e31_independent_receipt(receipt_path)


def _fixture(root: Path) -> Path:
    e31 = root / "data/v11/e31_factorial_pareto"
    final = e31 / "formal_run/final"
    analysis_dir = e31 / "formal_run/analysis"
    final.mkdir(parents=True)
    analysis_dir.mkdir(parents=True)
    (root / "experiments").mkdir()
    protocol = root / "experiments/e31_factorial_pareto_protocol.json"
    design_path = e31 / "design_manifest.csv"
    environment = e31 / "formal_run/environment.json"
    release_gate = e31 / "formal_release_gate.json"
    method_gate = e31 / "preanalysis_method_erratum_gate.json"
    host_gate = e31 / "host_environment_limitation_gate.json"
    transitive_gate = e31 / "transitive_source_provenance_gate.json"
    pareto_gate = e31 / "posthoc_pareto_aggregation_gate.json"
    contrast_gate = e31 / "posthoc_contrast_expansion_gate.json"
    family_correction_gate = e31 / "posthoc_family_inference_correction_gate.json"
    temporal_binding_audit = root / "release/e31_temporal_gate_binding_audit.json"
    host_disclosure = root / "docs/review/e31_host_environment_limitation_2026-08-24.md"
    method_erratum = root / "docs/review/e31_preanalysis_method_erratum_2026-08-24.md"
    for path, payload in (
        (protocol, {
            "experiment_id": "E31-factorial-pareto-v1",
            "semantic_contract": {"fidelity_threshold": 0.999999999},
            "resource_contract": {
                "timeout_grace_seconds": 5.0,
                "memory_budget_mb_per_worker": 3072,
            },
            "analysis_contract": {
                "alpha_two_sided": 0.05,
                "bootstrap_replicates": 100,
                "bootstrap_seed": 20260811,
            },
            "power_gate": {"mcid_pp": 1.0},
        }),
        (environment, {"environment": "frozen"}),
        (release_gate, {"status": "complete"}),
    ):
        _write_json(path, payload)
    design = pd.DataFrame({
        "run_id": [f"run-{i}" for i in range(28152)],
        "run_order": range(28152),
    })
    cells = design["run_order"] % 72
    input_indices = design["run_order"] // 72
    design["input_circuit_sha256"] = input_indices.map(lambda value: f"{int(value):064x}")
    design["circuit_id"] = input_indices.map(lambda value: f"input-{int(value):03d}")
    design["circuit_family"] = input_indices.map(lambda value: f"family-{int(value) % 15:02d}")
    design["listing_model"] = cells.map(
        lambda value: ["LBL", "WCL", "RANDOM_TOPOLOGICAL"][int(value) % 3]
    )
    design["rule_set"] = cells.map(
        lambda value: ["COMMUTATION_ONLY", "COMMUTATION_PLUS_TEMPLATES"][(int(value) // 3) % 2]
    )
    design["window_gates"] = cells.map(lambda value: [4, 16, 64][(int(value) // 6) % 3])
    design["budget_seconds"] = cells.map(
        lambda value: [1, 10, 30, 120][(int(value) // 18) % 4]
    )
    design["primary_pair_orientation"] = input_indices.map(
        lambda value: 1 if int(value) % 2 else -1
    )
    design["protocol_sha256"] = _sha(protocol)
    design.to_csv(design_path, index=False)
    method_erratum.parent.mkdir(parents=True, exist_ok=True)
    method_erratum.write_text("synthetic method erratum", encoding="utf-8")
    _write_json(method_gate, {
        "status": "PREANALYSIS_MATHEMATICAL_ERRATUM_FROZEN_BEFORE_AGGREGATE_EFFECT_ANALYSIS",
        "created_date": "2026-08-24",
        "checkpoint_boundary": {
            "committed_rows": 1,
            "max_run_order": 0,
            "last_committed_utc": "2026-08-24T00:00:00.000000+00:00",
            "inspected_aggregate_fields": ["status", "run_order", "committed_utc"],
            "primary_contrast_computed_before_erratum": False,
        },
        "erratum_path": "docs/review/e31_preanalysis_method_erratum_2026-08-24.md",
        "erratum_sha256": _sha(method_erratum),
        "protocol_sha256": _sha(protocol),
        "design_manifest_sha256": _sha(design_path),
        "changes_to_frozen_execution": False,
        "invalid_inference_removed": "family-restricted artificial-sign randomization p-value",
        "replacement": (
            "exact finite-population contrast plus explicitly non-design-based stratified "
            "stability interval"
        ),
        "unmeasured_secondary_outcomes": [
            "time_to_first_valid_seconds", "time_to_best_seconds",
        ],
    })
    power = e31 / "dual_estimand_power.json"
    _write_json(power, {"status": "synthetic-power-gate"})
    source_relatives = (
        "experiments/e31_formal_orchestrator.py",
        "experiments/e31_listing_phase2b_interaction.py",
        "experiments/e31_resource_smoke.py",
        "experiments/e31_shared_rule_worker.py",
        "src/circuits/real_benchmarks.py",
        "src/optimisation/phase1/wire_traversal.py",
        "src/optimisation/phase2/template_matcher.py",
    )
    for relative in source_relatives:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"synthetic source: {relative}\n", encoding="utf-8")
    guoq_evidence = root / "data/v10/prepaper/external_baselines/guoq/evidence.txt"
    heldout_evidence = root / "data/v10/prepaper/heldout_v2/evidence.txt"
    guoq_evidence.parent.mkdir(parents=True, exist_ok=True)
    heldout_evidence.parent.mkdir(parents=True, exist_ok=True)
    guoq_evidence.write_text("synthetic guoq evidence\n", encoding="utf-8")
    heldout_evidence.write_text("synthetic heldout evidence\n", encoding="utf-8")
    release_gate_payload = {
        "status": "COMPLETE",
        "guoq_status": "COMPLETE",
        "heldout_status": "COMPLETE",
        "protocol_sha256": _sha(protocol),
        "design_manifest_sha256": _sha(design_path),
        "power_sha256": _sha(power),
        "guoq_evidence_sha256": {
            "data/v10/prepaper/external_baselines/guoq/evidence.txt": _sha(guoq_evidence),
        },
        "heldout_evidence_sha256": {
            "heldout_v2/evidence.txt": _sha(heldout_evidence),
        },
    }
    _write_json(release_gate, release_gate_payload)
    _write_json(environment, {
        "protocol_sha256": _sha(protocol),
        "design_manifest_sha256": _sha(design_path),
        "power_sha256": _sha(power),
        "cold_process_per_cell": True,
        "qasm_preflight": {"unique_qasm_inputs_parsed": 391},
        "release_gate": release_gate_payload,
        "source_sha256": {
            relative: _sha(root / relative) for relative in source_relatives
        },
        "thread_limits": {
            "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
            "RAYON_NUM_THREADS": "1",
        },
        "resource_plan_at_start": {
            "workers": 1, "total_rows": 28152, "pending_rows": 28152,
            "completed_rows": 0, "per_worker_memory_cap_mb": 3072,
            "aggregate_memory_cap_mb": 3072,
        },
        "packages": {
            "numpy": "1", "pandas": "1", "psutil": "1", "qiskit": "1", "scipy": "1",
        },
        "python_executable": str(root / "synthetic-python.exe"),
        "python_executable_sha256": "b" * 64,
    })
    transitive_disclosure = (
        root / "docs/review/e31_transitive_source_provenance_limitation_2026-08-24.md"
    )
    transitive_disclosure.write_text("synthetic transitive limitation", encoding="utf-8")
    pareto_disclosure = root / "docs/review/e31_pareto_aggregation_limitation_2026-08-24.md"
    pareto_disclosure.write_text("synthetic Pareto aggregation limitation", encoding="utf-8")
    contrast_disclosure = root / "docs/review/e31_contrast_expansion_limitation_2026-08-24.md"
    contrast_disclosure.write_text("synthetic contrast expansion limitation", encoding="utf-8")
    transitive_relatives = (
        "experiments/e31_factorial_pareto_design.py",
        "src/circuits/__init__.py",
        "src/circuits/generator_v2.py",
        "src/equivalence.py",
        "src/optimisation/__init__.py",
        "src/optimisation/_gate_predicates.py",
        "src/optimisation/base.py",
        "src/optimisation/ceiling_aware.py",
        "src/optimisation/constants.py",
        "src/optimisation/phase1/__init__.py",
        "src/optimisation/phase1/genetic_algorithm.py",
        "src/optimisation/phase1/greedy.py",
        "src/optimisation/phase1/random_local_search.py",
        "src/optimisation/phase1/simulated_annealing.py",
        "src/optimisation/phase2/__init__.py",
        "src/optimisation/phase2/commutation_rewriter.py",
    )
    for relative in transitive_relatives:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(f"synthetic transitive source: {relative}\n", encoding="utf-8")
    _write_json(transitive_gate, {
        "status": "POSTHOC_TRANSITIVE_SOURCE_LIMITATION_FROZEN_BEFORE_AGGREGATE_ANALYSIS",
        "created_date": "2026-08-24",
        "created_utc": "2026-08-24T00:00:00.250000+00:00",
        "protocol_sha256": _sha(protocol),
        "design_manifest_sha256": _sha(design_path),
        "direct_frozen_source_count": 7,
        "omitted_source_count": 16,
        "aggregate_treatment_effects_inspected": False,
        "row_exclusion_or_rerun_authorized": False,
        "historical_environment_rewritten": False,
        "complete_cryptographic_prerun_source_closure": False,
        "static_first_party_source_closure_count": 23,
        "dynamic_imports_not_proven": True,
        "timestamp_evidence_is_cryptographic_commitment": False,
        "interpretation": (
            "Conditional release eligibility with a PARTIAL provenance rating; the post-hoc "
            "gate cannot be represented as a complete cryptographic pre-run source freeze."
        ),
        "environment_path": "data/v11/e31_factorial_pareto/formal_run/environment.json",
        "environment_sha256": _sha(environment),
        "disclosure_path": (
            "docs/review/e31_transitive_source_provenance_limitation_2026-08-24.md"
        ),
        "disclosure_sha256": _sha(transitive_disclosure),
        "checkpoint_boundary": {
            "committed_rows": 1,
            "min_run_order": 0,
            "max_run_order": 0,
            "unique_run_ids": 1,
            "unique_run_orders": 1,
            "status_counts_only": {"success": 1},
            "sqlite_integrity": "ok",
            "first_committed_utc": "2026-08-24T00:00:00.000000+00:00",
            "last_committed_utc": "2026-08-24T00:00:00.000000+00:00",
        },
        "omitted_first_party_import_closure": {
            relative: {
                "sha256": _sha(root / relative),
                "last_write_local": "2026-08-23T00:00:00+00:00",
            }
            for relative in transitive_relatives
        },
    })
    _write_json(pareto_gate, {
        "status": "POSTHOC_PARETO_AGGREGATION_FROZEN_BEFORE_AGGREGATE_ANALYSIS",
        "created_date": "2026-08-24",
        "created_utc": "2026-08-24T00:00:00.500000+00:00",
        "protocol_sha256": _sha(protocol),
        "design_manifest_sha256": _sha(design_path),
        "aggregate_treatment_effects_inspected": False,
        "changes_to_frozen_execution": False,
        "row_exclusion_or_rerun_authorized": False,
        "aggregation_functionals_preregistered_in_protocol": False,
        "primary_descriptive_aggregation": {
            "quality_itt": "mean", "valid_rate": "mean",
            "wall_seconds": "median", "peak_rss_mb": "p95",
        },
        "primary_pareto_inference_role": "EXPLORATORY_POSTHOC_AGGREGATION",
        "redundant_objective": {
            "removed_from_hypervolume": "failure_rate",
            "reason": "failure_rate equals 1 - valid_rate exactly under the frozen row contract",
        },
        "required_sensitivity_grid": {
            "wall_seconds": ["median", "p95"],
            "peak_rss_mb": ["median", "p95"],
            "expected_schemes": 4,
            "expected_treatment_cells_per_scheme": 72,
            "artifact": (
                "data/v11/e31_factorial_pareto/formal_run/analysis/"
                "pareto_aggregation_sensitivity.csv"
            ),
        },
        "checkpoint_boundary": {
            "committed_rows": 1,
            "min_run_order": 0,
            "max_run_order": 0,
            "unique_run_ids": 1,
            "unique_run_orders": 1,
            "status_counts_only": {"success": 1},
            "sqlite_integrity": "ok",
            "first_committed_utc": "2026-08-24T00:00:00.000000+00:00",
            "last_committed_utc": "2026-08-24T00:00:00.000000+00:00",
        },
        "disclosure_path": "docs/review/e31_pareto_aggregation_limitation_2026-08-24.md",
        "disclosure_sha256": _sha(pareto_disclosure),
        "interpretation": (
            "Pareto results are exploratory and aggregation-conditional; disagreement across "
            "the four frozen post-hoc schemes blocks an aggregation-invariant frontier claim."
        ),
    })
    _write_json(contrast_gate, {
        "status": "POSTHOC_CONTRAST_EXPANSION_FROZEN_BEFORE_AGGREGATE_ANALYSIS",
        "created_date": "2026-08-24",
        "created_utc": "2026-08-24T00:00:00.750000+00:00",
        "protocol_sha256": _sha(protocol),
        "design_manifest_sha256": _sha(design_path),
        "aggregate_treatment_effects_inspected": False,
        "changes_to_frozen_execution": False,
        "row_exclusion_or_rerun_authorized": False,
        "fully_preregistered_scalar_contrast_family": False,
        "inference_role": "SUPPORTIVE_POSTHOC_OPERATIONALIZATION_OF_FROZEN_CLASS",
        "factor_order": ["listing_model", "rule_set", "window_gates", "budget_seconds"],
        "reference_levels": {
            "listing_model": "LBL", "rule_set": "COMMUTATION_ONLY",
            "window_gates": 4, "budget_seconds": 1,
        },
        "nuisance_weighting": (
            "equal weight over every level combination of all non-contrast factors and "
            "equal weight over 391 frozen input hashes"
        ),
        "multiplicity_family": {
            "id": "E31_POSTHOC_MARGINAL_30", "method": "Holm", "size": 30,
        },
        "excluded_primary_contrast": (
            "MARGINAL::listing_model[WCL-vs-LBL]:"
            "rule_set[COMMUTATION_PLUS_TEMPLATES-vs-COMMUTATION_ONLY]"
        ),
        "generalized_estimand_b": {
            "included_in_multiplicity_family": False,
            "role": "SUPPORTIVE_MODEL_BASED_EXTRAPOLATION_NO_CONFIRMATORY_CLAIM",
            "reason": (
                "same separately frozen primary contrast under a different population extrapolation"
            ),
        },
        "contrast_labels": verifier._expected_e31_posthoc_marginal_labels(),
        "checkpoint_boundary": {
            "committed_rows": 1,
            "min_run_order": 0,
            "max_run_order": 0,
            "unique_run_ids": 1,
            "unique_run_orders": 1,
            "status_counts_only": {"success": 1},
            "sqlite_integrity": "ok",
            "first_committed_utc": "2026-08-24T00:00:00.000000+00:00",
            "last_committed_utc": "2026-08-24T00:00:00.000000+00:00",
        },
        "disclosure_path": "docs/review/e31_contrast_expansion_limitation_2026-08-24.md",
        "disclosure_sha256": _sha(contrast_disclosure),
    })
    _write_json(family_correction_gate, {"status": "synthetic-bound-correction-gate"})
    _write_json(temporal_binding_audit, {"status": "synthetic-temporal-binding"})
    host_disclosure.parent.mkdir(parents=True, exist_ok=True)
    host_disclosure.write_text("synthetic host limitation", encoding="utf-8")
    _write_json(host_gate, {
        "status": "PREANALYSIS_HOST_LIMITATION_FROZEN",
        "aggregate_treatment_effects_inspected": False,
        "row_exclusion_or_rerun_authorized": False,
        "continuous_host_exclusivity_verified": False,
        "continuous_host_telemetry_recorded": False,
        "checkpoint_boundary": {
            "rows": 1,
            "max_run_order": 0,
            "status_counts_only": {"success": 1},
        },
        "material_drift_thresholds": {
            "quality_itt": 1.0, "valid": 0.05, "timeout": 0.05,
            "wall_budget_fraction": 0.05, "peak_rss_mb": 128.0,
        },
        "temporal_blocks": 20,
        "protocol_sha256": _sha(protocol),
        "design_manifest_sha256": _sha(design_path),
        "disclosure_path": "docs/review/e31_host_environment_limitation_2026-08-24.md",
        "disclosure_sha256": _sha(host_disclosure),
        "interpretation": (
            "Thresholds were frozen before formal aggregate treatment analysis; the "
            "diagnostic can reveal temporal drift but cannot prove its absence."
        ),
    })
    results = design.copy()
    results["design_manifest_sha256"] = _sha(design_path)
    results["status"] = "success"
    results["valid_equivalent_output"] = True
    results["exact_fidelity"] = 1.0
    results["output_circuit_sha256"] = "a" * 64
    input_scale = (input_indices % 7).astype(float) / 10.0
    wcl = results["listing_model"].eq("WCL").astype(float)
    random_listing = results["listing_model"].eq("RANDOM_TOPOLOGICAL").astype(float)
    plus = results["rule_set"].eq("COMMUTATION_PLUS_TEMPLATES").astype(float)
    window_16 = results["window_gates"].eq(16).astype(float)
    window_64 = results["window_gates"].eq(64).astype(float)
    budget_10 = results["budget_seconds"].eq(10).astype(float)
    results["common_basis_gate_reduction_pct"] = (
        1.0 + input_scale + 1.5 * random_listing + 2.0 * wcl + 3.0 * plus
        + (0.5 + (input_indices % 5).astype(float) / 20.0) * wcl * plus
        + 0.8 * window_16 + 1.1 * window_64
        + 0.02 * results["budget_seconds"].astype(float)
        + 0.4 * window_16 * budget_10
    )
    results["original_common_basis_gate_count"] = 100_000_000
    results["optimized_common_basis_gate_count"] = np.rint(
        100_000_000 * (1.0 - results["common_basis_gate_reduction_pct"] / 100.0)
    ).astype(int)
    results["wall_seconds_end_to_end"] = (
        0.2 + 0.001 * results["budget_seconds"].astype(float)
        + 0.03 * window_16 + 0.08 * window_64 + 0.02 * wcl + 0.01 * input_scale
    )
    results["peak_rss_mb"] = (
        90.0 + 4.0 * window_16 + 12.0 * window_64 + 2.0 * plus + input_scale
    )
    timeout = input_indices.mod(19).eq(0) & window_64.eq(1.0) & results["budget_seconds"].eq(1)
    results.loc[timeout, "status"] = "timeout"
    results.loc[timeout, "valid_equivalent_output"] = False
    result_path = final / "formal_results.csv"
    results.to_csv(result_path, index=False)
    snapshot = final / "checkpoint_final.sqlite3"
    connection = sqlite3.connect(snapshot)
    connection.execute(
        "CREATE TABLE results (run_id TEXT PRIMARY KEY, run_order INTEGER NOT NULL, "
        "result_json TEXT NOT NULL, committed_utc TEXT NOT NULL)"
    )
    connection.executemany(
        "INSERT INTO results VALUES (?, ?, ?, ?)",
        (
            (
                str(row["run_id"]), int(row["run_order"]), json.dumps(row),
                f"2026-08-24T00:00:00.{int(row['run_order']):06d}+00:00",
            )
            for row in results.to_dict(orient="records")
        ),
    )
    connection.commit()
    connection.close()
    completion = {
        "status": "FORMAL_COMPLETE_PENDING_INDEPENDENT_RELEASE_VERIFICATION",
        "created_utc": "2026-08-24T00:00:01.000000+00:00",
        "rows": 28152,
        "scheduled_rows": 28152,
        "unique_input_hashes": 391,
        "outer_families": 15,
        "status_counts": {
            str(key): int(value) for key, value in results["status"].value_counts().items()
        },
        "first_committed_utc": "2026-08-24T00:00:00.000000+00:00",
        "last_committed_utc": "2026-08-24T00:00:00.028151+00:00",
        "formal_analysis_gate_passed": True,
        "independent_release_verification_required": True,
        "independent_release_verification_embedded_in_completion": False,
        "source_provenance_rating": "PARTIAL",
        "complete_cryptographic_prerun_source_closure": False,
        "static_first_party_source_closure_count": 23,
        "dynamic_imports_not_proven": True,
        "temporal_gate_provenance_rating": "PARTIAL",
        "pareto_inference_role": "EXPLORATORY_POSTHOC_AGGREGATION",
        "pareto_aggregation_functionals_preregistered": False,
        "release_eligibility_qualification": (
            "eligible only with the full semantic replay and bound post-hoc transitive-source, "
            "contrast-expansion, Pareto-aggregation, and family-inference-correction "
            "limitations disclosed"
        ),
        "marginal_contrast_inference_role": (
            "SUPPORTIVE_POSTHOC_OPERATIONALIZATION_OF_FROZEN_CLASS"
        ),
        "marginal_contrast_family_fully_preregistered": False,
        "marginal_contrast_multiplicity_family_size": 30,
        "legacy_input_cluster_inference_valid": False,
        "family_inference_outer_cluster": "circuit_family",
        "family_inference_n_independent_clusters": 15,
        "family_inference_degrees_of_freedom": 14,
        "family_inference_correction_status": "PASS_POSTHOC_FAMILY_INFERENCE_CORRECTION",
        "unseen_family_generalization_status": "BLOCKED",
        "semantic_replay": {
            "status": "PASS",
            "success_rows_verified_and_bound": int(results["status"].eq("success").sum()),
        },
        "artifacts": {
            result_path.name: {"bytes": result_path.stat().st_size, "sha256": _sha(result_path)},
            snapshot.name: {"bytes": snapshot.stat().st_size, "sha256": _sha(snapshot)},
        },
        "bindings": {
            "protocol_sha256": _sha(protocol),
            "design_manifest_sha256": _sha(design_path),
            "environment_sha256": _sha(environment),
            "formal_release_gate_sha256": _sha(release_gate),
            "preanalysis_method_erratum_gate_sha256": _sha(method_gate),
            "host_environment_limitation_gate_sha256": _sha(host_gate),
            "transitive_source_provenance_gate_sha256": _sha(transitive_gate),
            "posthoc_pareto_aggregation_gate_sha256": _sha(pareto_gate),
            "posthoc_contrast_expansion_gate_sha256": _sha(contrast_gate),
            "posthoc_family_inference_correction_gate_sha256": _sha(
                family_correction_gate
            ),
            "temporal_gate_binding_audit_sha256": _sha(temporal_binding_audit),
        },
    }
    pareto = verifier._recompute_e31_pareto_summary(results)
    pareto_sensitivity = verifier._recompute_e31_pareto_aggregation_sensitivity(results)
    pareto_sensitivity_summary = verifier._summarize_e31_pareto_aggregation_sensitivity(
        pareto_sensitivity
    )
    completion["pareto_frontier_membership_agreement_all_schemes"] = (
        pareto_sensitivity_summary["frontier_membership_agreement_all_schemes"]
    )
    completion["pareto_aggregation_invariant_claim_allowed"] = (
        pareto_sensitivity_summary["bounded_aggregation_invariant_frontier_claim_allowed"]
    )
    completion["pareto_aggregation_disagreement_cell_count"] = (
        pareto_sensitivity_summary["disagreement_cell_count"]
    )
    hypervolume = verifier._recompute_e31_hypervolume(pareto)
    factorial_coefficients, factorial_diagnostics = (
        verifier._recompute_e31_factorial_model(results)
    )
    posthoc_marginal = verifier._recompute_e31_posthoc_marginal_contrasts(results)
    primary_recomputed = verifier._recompute_e31_primary_estimand(
        results,
        alpha=0.05,
        bootstrap_replicates=100,
        bootstrap_seed=20260811,
    )
    hypervolume["deduplicated_protocol_objective"] = {
        "removed": "failure_rate",
        "reason": "failure_rate equals 1 - valid_rate exactly and is not an independent axis",
    }
    hypervolume["interpretation"] = (
        "relative to observed treatment-cell ranges, not an absolute cross-study metric"
    )
    pareto.to_csv(analysis_dir / "equal_budget_pareto_summary.csv", index=False)
    pareto_sensitivity.to_csv(
        analysis_dir / "pareto_aggregation_sensitivity.csv", index=False
    )
    _write_json(analysis_dir / "pareto_hypervolume_audit.json", hypervolume)
    factorial_coefficients.to_csv(
        analysis_dir / "full_factorial_model_coefficients.csv", index=False
    )
    posthoc_marginal.to_csv(
        analysis_dir / "posthoc_marginal_contrasts.csv", index=False
    )
    _write_json(
        analysis_dir / "full_factorial_model_diagnostics.json", factorial_diagnostics
    )
    analysis_gate = analysis_dir / "analysis_gate_audit.json"
    _write_json(analysis_gate, {
        "result_rows": 28152,
        "formal_requested": True,
        "dual_estimand_primary": {
            "primary_contrast": "grid-averaged listing-by-rule-set interaction",
            "fixed_benchmark_A": {
                "population": "frozen unique input hashes",
                "n_input_hashes": 391,
                "families_as_fixed_blocks": 15,
                "estimate_pp": primary_recomputed["estimate_a"],
                "estimand_type": "exact finite-population contrast",
                "mcid_pp": 1.0,
                "distance_from_mcid_pp": primary_recomputed["estimate_a"] - 1.0,
                "meets_or_exceeds_mcid": primary_recomputed["estimate_a"] >= 1.0,
                "design_based_p_value": None,
                "design_based_confidence_interval": None,
                "design_based_inference_status": "NOT_IDENTIFIED_NO_TREATMENT_RANDOMIZATION",
                "stratified_input_bootstrap_stability_interval": primary_recomputed[
                    "bootstrap_interval"
                ],
                "stability_interval_role": "EMPIRICAL_SENSITIVITY_NOT_DESIGN_BASED_CI",
                "bootstrap_replicates": 100,
                "bootstrap_seed": 20260811,
                "input_quantiles_pp": primary_recomputed["quantiles"],
                "family_means_pp": primary_recomputed["family_means"],
                "worst_family": primary_recomputed["worst_family"],
                "worst_family_estimate_pp": primary_recomputed["worst_family_estimate"],
                "leave_one_family_out_estimates_pp": primary_recomputed["lofo"],
                "lofo_sign_stable": primary_recomputed["lofo_sign_stable"],
            },
            "new_family_generalized_B": {
                "population": "potentially unseen families",
                "n_independent_family_clusters": 15,
                "estimate_pp": primary_recomputed["estimate_b"],
                "family_cluster_se_pp": primary_recomputed["se_b"],
                "ci": primary_recomputed["ci_b"],
                "confirmatory_claim_allowed": False,
                "inference_role": "SUPPORTIVE_MODEL_BASED_EXTRAPOLATION_NO_CONFIRMATORY_CLAIM",
                "probability_sample_of_families": False,
            },
        },
        "secondary_outcome_availability": {
            "time_to_first_valid_seconds": {"status": "NOT_MEASURED_IN_FROZEN_RUN"},
            "time_to_best_seconds": {"status": "NOT_MEASURED_IN_FROZEN_RUN"},
        },
        "pareto_hypervolume": hypervolume,
        "pareto_inference_role": "EXPLORATORY_POSTHOC_AGGREGATION",
        "pareto_aggregation_sensitivity": pareto_sensitivity_summary,
        "factorial_model": factorial_diagnostics,
    })
    outcomes = (
        "quality_itt", "valid", "timeout", "wall_seconds",
        "wall_budget_fraction", "peak_rss_mb",
    )
    temporal = verifier._recompute_e31_temporal_diagnostics(results)
    temporal.to_csv(analysis_dir / "run_order_temporal_diagnostics.csv", index=False)
    thresholds = {
        "quality_itt": 1.0, "valid": 0.05, "timeout": 0.05,
        "wall_budget_fraction": 0.05, "peak_rss_mb": 128.0,
    }
    exceeded = {
        outcome: bool(
            temporal[f"{outcome}_adjusted_residual_mean"].abs().max() > threshold
        )
        for outcome, threshold in thresholds.items()
    }
    _write_json(analysis_dir / "host_environment_audit.json", {
        "status": "OBSERVATIONAL_TEMPORAL_SENSITIVITY_ONLY",
        "blocks": 20,
        "rows": 28152,
        "continuous_host_exclusivity_verified": False,
        "continuous_host_telemetry_recorded": False,
        "outcomes": {
            outcome: {
                "max_absolute_block_adjusted_residual_mean": float(
                    temporal[f"{outcome}_adjusted_residual_mean"].abs().max()
                ),
                "last_minus_first_adjusted_residual_mean": float(
                    temporal[f"{outcome}_adjusted_residual_mean"].iloc[-1]
                    - temporal[f"{outcome}_adjusted_residual_mean"].iloc[0]
                ),
            }
            for outcome in outcomes
        },
        "material_drift_thresholds": thresholds,
        "material_drift_threshold_exceeded": exceeded,
        "material_drift_screen_decision": (
            "REVIEW_REQUIRED" if any(exceeded.values()) else "NO_THRESHOLD_EXCEEDED"
        ),
    })
    completion["analysis_artifacts"] = {
        path.name: {"bytes": path.stat().st_size, "sha256": _sha(path)}
        for path in analysis_dir.iterdir()
    }
    family_dir = analysis_dir / "family_inference"
    family_dir.mkdir()
    for name in (
        "fixed_panel_factorial_71_descriptive.csv",
        "fixed_panel_marginal_30_descriptive.csv",
        "family_supportive_factorial_71.csv",
        "family_supportive_marginal_30.csv",
        "per_family_factorial_71_effects.csv",
        "per_family_marginal_30_effects.csv",
        "primary_estimand_validity.json",
        "family_inference_correction_audit.json",
    ):
        (family_dir / name).write_text(
            "{}\n" if name.endswith(".json") else "x\n", encoding="utf-8"
        )
    completion["family_inference_artifacts"] = {
        path.name: {"bytes": path.stat().st_size, "sha256": _sha(path)}
        for path in family_dir.iterdir()
    }
    _write_json(final / "formal_completion_manifest.json", completion)
    return analysis_gate


def test_e31_release_verifier_rechecks_schedule_and_nested_gates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    sensitivity = pd.read_csv(analysis_path.with_name("pareto_aggregation_sensitivity.csv"))
    assert (sensitivity["wall_seconds_median"] != sensitivity["wall_seconds_p95"]).any()
    assert (sensitivity["peak_rss_mb_median"] != sensitivity["peak_rss_mb_p95"]).any()
    marginal = pd.read_csv(analysis_path.with_name("posthoc_marginal_contrasts.csv"))
    assert marginal["estimate_pp"].abs().gt(0).any()
    assert marginal["cluster_robust_se_pp"].isna().all()
    assert marginal["p_value_model_based"].isna().all()
    known_interaction = marginal.loc[
        marginal["coefficient"].eq(
            "MARGINAL::window_gates[16-vs-4]:budget_seconds[10-vs-1]"
        ),
        "estimate_pp",
    ].item()
    assert known_interaction == pytest.approx(0.4)
    disagreement = sensitivity.copy()
    current_flag = verifier._strict_bool_series(
        disagreement["pareto_nondominated"], label="test sensitivity"
    ).iloc[0]
    disagreement.loc[0, "pareto_nondominated"] = not bool(current_flag)
    disagreement_summary = verifier._summarize_e31_pareto_aggregation_sensitivity(
        disagreement
    )
    assert disagreement_summary["disagreement_cell_count"] == 1
    assert disagreement_summary["bounded_aggregation_invariant_frontier_claim_allowed"] is False
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    assert verifier._verify_e31_formal() == 67


def test_e31_release_verifier_rejects_overstated_prerun_source_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["source_provenance_rating"] = "PASS"
    completion["complete_cryptographic_prerun_source_closure"] = True
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="overstates transitive source provenance"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_reintroduced_invalid_randomization_p_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    payload["dual_estimand_primary"]["fixed_benchmark_A"]["design_based_p_value"] = 0.01
    _write_json(analysis_path, payload)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["analysis_artifacts"][analysis_path.name] = {
        "bytes": analysis_path.stat().st_size,
        "sha256": _sha(analysis_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="pre-analysis correction"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_primary_estimate_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    payload["dual_estimand_primary"]["fixed_benchmark_A"]["estimate_pp"] = 9.0
    _write_json(analysis_path, payload)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["analysis_artifacts"][analysis_path.name] = {
        "bytes": analysis_path.stat().st_size,
        "sha256": _sha(analysis_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="primary summary differs"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_bootstrap_interval_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    payload["dual_estimand_primary"]["fixed_benchmark_A"][
        "stratified_input_bootstrap_stability_interval"
    ] = [8.0, 9.0]
    _write_json(analysis_path, payload)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["analysis_artifacts"][analysis_path.name] = {
        "bytes": analysis_path.stat().st_size,
        "sha256": _sha(analysis_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="bootstrap stability interval differs"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_analysis_artifact_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    analysis_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="analysis_gate_audit"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_false_host_exclusivity_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    host_path = analysis_path.with_name("host_environment_audit.json")
    payload = json.loads(host_path.read_text(encoding="utf-8"))
    payload["continuous_host_exclusivity_verified"] = True
    _write_json(host_path, payload)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["analysis_artifacts"][host_path.name] = {
        "bytes": host_path.stat().st_size,
        "sha256": _sha(host_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="host-environment limitation"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_method_erratum_semantic_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    method_gate_path = analysis_path.parents[2] / "preanalysis_method_erratum_gate.json"
    payload = json.loads(method_gate_path.read_text(encoding="utf-8"))
    payload["changes_to_frozen_execution"] = True
    _write_json(method_gate_path, payload)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["bindings"]["preanalysis_method_erratum_gate_sha256"] = _sha(
        method_gate_path
    )
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="method erratum gate"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_noncontiguous_temporal_partition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    temporal_path = analysis_path.with_name("run_order_temporal_diagnostics.csv")
    temporal = pd.read_csv(temporal_path)
    temporal.loc[1, "run_order_min"] += 1
    temporal.to_csv(temporal_path, index=False)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["analysis_artifacts"][temporal_path.name] = {
        "bytes": temporal_path.stat().st_size,
        "sha256": _sha(temporal_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="temporal diagnostic differs"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_pareto_table_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    pareto_path = analysis_path.with_name("equal_budget_pareto_summary.csv")
    pareto = pd.read_csv(pareto_path)
    pareto.loc[0, "quality_itt_mean"] = 9.0
    pareto.to_csv(pareto_path, index=False)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["analysis_artifacts"][pareto_path.name] = {
        "bytes": pareto_path.stat().st_size,
        "sha256": _sha(pareto_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="Pareto table differs"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_pareto_aggregation_sensitivity_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    sensitivity_path = analysis_path.with_name("pareto_aggregation_sensitivity.csv")
    sensitivity = pd.read_csv(sensitivity_path)
    sensitivity.loc[0, "selected_wall_seconds"] = 9.0
    sensitivity.to_csv(sensitivity_path, index=False)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["analysis_artifacts"][sensitivity_path.name] = {
        "bytes": sensitivity_path.stat().st_size,
        "sha256": _sha(sensitivity_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="Pareto aggregation sensitivity differs"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_factorial_coefficient_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    coefficients_path = analysis_path.with_name("full_factorial_model_coefficients.csv")
    coefficients = pd.read_csv(coefficients_path)
    coefficients.loc[0, "estimate_pp"] = 9.0
    coefficients.to_csv(coefficients_path, index=False)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["analysis_artifacts"][coefficients_path.name] = {
        "bytes": coefficients_path.stat().st_size,
        "sha256": _sha(coefficients_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="factorial coefficient differs"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_posthoc_marginal_contrast_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    marginal_path = analysis_path.with_name("posthoc_marginal_contrasts.csv")
    marginal = pd.read_csv(marginal_path)
    marginal.loc[0, "estimate_pp"] = 9.0
    marginal.to_csv(marginal_path, index=False)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["analysis_artifacts"][marginal_path.name] = {
        "bytes": marginal_path.stat().st_size,
        "sha256": _sha(marginal_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="post-hoc marginal contrast differs"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_posthoc_marginal_family_metadata_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    marginal_path = analysis_path.with_name("posthoc_marginal_contrasts.csv")
    marginal = pd.read_csv(marginal_path)
    marginal.loc[0, "multiplicity_family_size"] = 29
    marginal.to_csv(marginal_path, index=False)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["analysis_artifacts"][marginal_path.name] = {
        "bytes": marginal_path.stat().st_size,
        "sha256": _sha(marginal_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="post-hoc marginal metadata differs"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_garbage_boolean_in_sealed_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    result_path = analysis_path.parents[1] / "final/formal_results.csv"
    results = pd.read_csv(result_path)
    results.loc[0, "valid_equivalent_output"] = "corrupt"
    results.to_csv(result_path, index=False)
    completion_path = result_path.with_name("formal_completion_manifest.json")
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["artifacts"][result_path.name] = {
        "bytes": result_path.stat().st_size,
        "sha256": _sha(result_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="invalid serialized boolean"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_hypervolume_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    hypervolume_path = analysis_path.with_name("pareto_hypervolume_audit.json")
    payload = json.loads(hypervolume_path.read_text(encoding="utf-8"))
    payload["hypervolume"] = 0.123
    _write_json(hypervolume_path, payload)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["analysis_artifacts"][hypervolume_path.name] = {
        "bytes": hypervolume_path.stat().st_size,
        "sha256": _sha(hypervolume_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="hypervolume audit differs"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_snapshot_csv_status_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    snapshot_path = analysis_path.parents[1] / "final/checkpoint_final.sqlite3"
    connection = sqlite3.connect(snapshot_path)
    payload = json.loads(connection.execute(
        "SELECT result_json FROM results WHERE run_order = 0"
    ).fetchone()[0])
    payload["status"] = "timeout"
    connection.execute(
        "UPDATE results SET result_json = ? WHERE run_order = 0", (json.dumps(payload),)
    )
    connection.commit()
    connection.close()
    completion_path = snapshot_path.with_name("formal_completion_manifest.json")
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["artifacts"][snapshot_path.name] = {
        "bytes": snapshot_path.stat().st_size,
        "sha256": _sha(snapshot_path),
    }
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="SQLite and CSV status sequences differ"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_runtime_source_hash_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    environment_path = analysis_path.parents[1] / "environment.json"
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    environment["source_sha256"]["experiments/e31_shared_rule_worker.py"] = "0" * 64
    _write_json(environment_path, environment)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["bindings"]["environment_sha256"] = _sha(environment_path)
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="e31-runtime-source"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_transitive_source_hash_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    gate_path = analysis_path.parents[2] / "transitive_source_provenance_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["omitted_first_party_import_closure"][
        "src/optimisation/base.py"
    ]["sha256"] = "0" * 64
    _write_json(gate_path, gate)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["bindings"]["transitive_source_provenance_gate_sha256"] = _sha(gate_path)
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="e31-transitive-source"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_transitive_gate_time_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    gate_path = analysis_path.parents[2] / "transitive_source_provenance_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["created_utc"] = "2026-08-23T23:59:59.000000+00:00"
    _write_json(gate_path, gate)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["bindings"]["transitive_source_provenance_gate_sha256"] = _sha(gate_path)
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="transitive-source gate predates"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_transitive_gate_path_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    gate_path = analysis_path.parents[2] / "transitive_source_provenance_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["environment_path"] = "data/v11/e31_factorial_pareto/formal_release_gate.json"
    gate["environment_sha256"] = _sha(
        analysis_path.parents[2] / "formal_release_gate.json"
    )
    _write_json(gate_path, gate)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["bindings"]["transitive_source_provenance_gate_sha256"] = _sha(gate_path)
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="transitive-source provenance limitation gate"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_pareto_gate_semantic_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    gate_path = analysis_path.parents[2] / "posthoc_pareto_aggregation_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["interpretation"] = "aggregation invariant regardless of sensitivity"
    _write_json(gate_path, gate)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["bindings"]["posthoc_pareto_aggregation_gate_sha256"] = _sha(gate_path)
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="Pareto aggregation limitation gate is invalid"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_contrast_gate_member_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    gate_path = analysis_path.parents[2] / "posthoc_contrast_expansion_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["contrast_labels"][0] = "MARGINAL::tampered"
    _write_json(gate_path, gate)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["bindings"]["posthoc_contrast_expansion_gate_sha256"] = _sha(gate_path)
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="contrast-expansion limitation gate is invalid"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_pareto_disclosure_hash_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    disclosure = tmp_path / "docs/review/e31_pareto_aggregation_limitation_2026-08-24.md"
    disclosure.write_text("tampered disclosure", encoding="utf-8")
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="e31-pareto-aggregation"):
        verifier._verify_e31_formal()


def test_e31_release_verifier_rejects_pareto_boundary_timestamp_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    analysis_path = _fixture(tmp_path)
    gate_path = analysis_path.parents[2] / "posthoc_pareto_aggregation_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["checkpoint_boundary"]["last_committed_utc"] = (
        "2026-08-24T00:00:00.100000+00:00"
    )
    _write_json(gate_path, gate)
    completion_path = analysis_path.parents[1] / "final/formal_completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["bindings"]["posthoc_pareto_aggregation_gate_sha256"] = _sha(gate_path)
    _write_json(completion_path, completion)
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="Pareto aggregation checkpoint timestamps differ"):
        verifier._verify_e31_formal()
