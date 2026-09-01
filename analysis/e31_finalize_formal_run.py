"""Seal a complete E31 checkpoint into release-eligible immutable artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import psutil

from analysis.e31_factorial_pareto_analysis import (
    FORMAL_ANALYSIS_FILENAMES, validate_results, write_analysis_packet,
)
from analysis.e31_posthoc_family_inference import write_correction_packet
from experiments.e31_factorial_pareto_design import file_sha256

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT = ROOT / "data/v11/e31_factorial_pareto/formal_run/checkpoint.sqlite3"
DEFAULT_DESIGN = ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv"
DEFAULT_PROTOCOL = ROOT / "experiments/e31_factorial_pareto_protocol.json"
DEFAULT_FINAL = ROOT / "data/v11/e31_factorial_pareto/formal_run/final"
DEFAULT_ANALYSIS = ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def refuse_active_formal_processes() -> None:
    own_pid = os.getpid()
    active = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        if process.info["pid"] == own_pid:
            continue
        command = " ".join(process.info.get("cmdline") or []).lower()
        name = str(process.info.get("name") or "").lower()
        if "python" in name and (
            "e31_formal_orchestrator.py" in command
            or "e31_shared_rule_worker.py" in command
        ):
            active.append((process.info["pid"], command[:240]))
    if active:
        raise RuntimeError(f"active E31 formal processes prevent sealing: {active}")


def read_complete_checkpoint(checkpoint: Path, design: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Read a consistent checkpoint and require exact frozen-schedule coverage."""
    checkpoint = checkpoint.resolve()
    connection = sqlite3.connect(checkpoint, timeout=30)
    try:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("checkpoint failed SQLite integrity_check")
        records = connection.execute(
            "SELECT run_id, run_order, result_json, committed_utc "
            "FROM results ORDER BY run_order"
        ).fetchall()
    finally:
        connection.close()
    if len(records) != len(design):
        raise ValueError(
            f"checkpoint is incomplete: rows={len(records)}, scheduled={len(design)}"
        )
    observed_orders = [int(record[1]) for record in records]
    if observed_orders != list(range(len(design))):
        raise ValueError("checkpoint run_order is not the complete contiguous schedule")
    expected = design.sort_values("run_order", kind="stable")[["run_id", "run_order"]]
    expected_keys = [
        (str(row.run_id), int(row.run_order)) for row in expected.itertuples(index=False)
    ]
    observed_keys = [(str(record[0]), int(record[1])) for record in records]
    if observed_keys != expected_keys:
        raise ValueError("checkpoint keys differ from the frozen schedule")
    results = pd.DataFrame([json.loads(record[2]) for record in records])
    metadata = {
        "first_committed_utc": str(records[0][3]),
        "last_committed_utc": str(records[-1][3]),
        "rows": len(records),
        "status_counts": {
            str(key): int(value) for key, value in results["status"].value_counts().items()
        },
    }
    return results, metadata


def sqlite_snapshot(source_path: Path, destination_path: Path) -> None:
    """Create a transactionally consistent SQLite backup including WAL state."""
    source = sqlite3.connect(source_path, timeout=30)
    destination = sqlite3.connect(destination_path)
    try:
        source.backup(destination)
        if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("final checkpoint snapshot failed integrity_check")
    finally:
        destination.close()
        source.close()


def validate_semantic_replay(
    replay_dir: Path, results: pd.DataFrame, checkpoint_metadata: dict,
) -> dict[str, object]:
    """Bind the completed all-success-row semantic replay before sealing."""
    gate_path = replay_dir / "semantic_replay_gate.json"
    manifest_path = replay_dir / "semantic_replay_manifest.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    success = results.loc[results["status"].astype(str).eq("success")].sort_values(
        "run_order", kind="stable"
    )
    expected_keys = list(zip(success["run_id"].astype(str), success["run_order"].astype(int)))
    bindings = manifest.get("row_bindings", [])
    observed_keys = [
        (str(record.get("run_id")), int(record.get("run_order", -1)))
        for record in bindings
    ]
    cells = manifest.get("semantic_cells", [])
    boundary = manifest.get("formal_checkpoint_boundary", {})
    if (gate.get("status") != "PASS"
            or gate.get("gate") != "E31_ALL_SUCCESS_ROWS_INDEPENDENT_SEMANTIC_REPLAY"
            or gate.get("semantic_method") != "exact dense operator, not sampled fidelity"
            or gate.get("manifest_sha256") != sha256(manifest_path)
            or manifest.get("status") != "PASS"
            or manifest.get("all_success_rows_passed") is not True
            or manifest.get("budget_dimension_collapsed_only_after_exact_group_invariant_check")
            is not True
            or gate.get("success_rows_verified_and_bound") != len(success)
            or manifest.get("success_rows_verified_and_bound") != len(success)
            or observed_keys != expected_keys
            or len(set(observed_keys)) != len(observed_keys)
            or gate.get("unique_semantic_cells_replayed") != len(cells)
            or manifest.get("unique_semantic_cells_replayed") != len(cells)
            or len({str(record.get("semantic_cell_id")) for record in cells}) != len(cells)
            or boundary.get("committed_rows") != checkpoint_metadata["rows"]
            or boundary.get("first_committed_utc") != checkpoint_metadata["first_committed_utc"]
            or boundary.get("last_committed_utc") != checkpoint_metadata["last_committed_utc"]
            or boundary.get("status_counts") != checkpoint_metadata["status_counts"]):
        raise RuntimeError("E31 semantic replay is incomplete or not bound to the checkpoint")
    return {
        "status": "PASS",
        "success_rows_verified_and_bound": len(success),
        "unique_semantic_cells_replayed": len(cells),
        "artifacts": {
            gate_path.name: {"sha256": sha256(gate_path), "bytes": gate_path.stat().st_size},
            manifest_path.name: {
                "sha256": sha256(manifest_path), "bytes": manifest_path.stat().st_size,
            },
        },
    }


def install_seal_pair(
    temporary_analysis: Path, analysis_dir: Path, temporary_final: Path, final_dir: Path,
) -> None:
    """Install both sibling seal directories, rolling back if the second move fails."""
    os.replace(temporary_analysis, analysis_dir)
    try:
        os.replace(temporary_final, final_dir)
    except BaseException:
        if analysis_dir.exists() and not temporary_analysis.exists():
            os.replace(analysis_dir, temporary_analysis)
        raise


def validate_runtime_source_provenance(
    checkpoint: Path, results: pd.DataFrame,
) -> dict:
    """Require current direct hashes, exact static closure, and checkpoint-bound disclosure."""
    from scripts.audit_e31_first_party_import_closure import build_audit

    audit = build_audit()
    if (audit.get("status")
            != "PASS_EXACT_STATIC_FIRST_PARTY_IMPORT_CLOSURE_RECONSTRUCTED"
            or audit.get("resolved_source_count") != 23
            or audit.get("direct_prerun_frozen_count") != 7
            or audit.get("posthoc_disclosed_count") != 16
            or audit.get("dynamic_imports_not_proven") is not True):
        raise RuntimeError("E31 static runtime-source closure audit is incomplete")
    gate = json.loads(
        (ROOT / "data/v11/e31_factorial_pareto/transitive_source_provenance_gate.json")
        .read_text(encoding="utf-8")
    )
    boundary = gate["checkpoint_boundary"]
    rows = int(boundary["committed_rows"])
    observed_counts = {
        str(key): int(value)
        for key, value in results.sort_values("run_order", kind="stable")
        .iloc[:rows]["status"].astype(str).value_counts().items()
    }
    with sqlite3.connect(checkpoint, timeout=30) as connection:
        first = connection.execute(
            "SELECT committed_utc FROM results WHERE run_order = 0"
        ).fetchone()
        last = connection.execute(
            "SELECT committed_utc FROM results WHERE run_order = ?", (rows - 1,)
        ).fetchone()
    if (observed_counts != boundary.get("status_counts_only")
            or first is None or str(first[0]) != boundary.get("first_committed_utc")
            or last is None or str(last[0]) != boundary.get("last_committed_utc")):
        raise RuntimeError("E31 source-provenance checkpoint boundary is inconsistent")
    return audit


def finalize(
    checkpoint: Path, design_path: Path, protocol_path: Path, final_dir: Path,
    analysis_dir: Path | None = None,
) -> Path:
    checkpoint = checkpoint.resolve()
    design_path = design_path.resolve()
    protocol_path = protocol_path.resolve()
    final_dir = final_dir.resolve()
    analysis_dir = (analysis_dir or checkpoint.parent / "analysis").resolve()
    if final_dir.exists():
        raise FileExistsError(f"final E31 seal already exists: {final_dir}")
    if analysis_dir.exists():
        raise FileExistsError(f"formal E31 analysis already exists: {analysis_dir}")
    if (checkpoint.parent / "formal.lock").exists():
        raise RuntimeError("formal.lock exists; the schedule is still active or uncleanly stopped")
    refuse_active_formal_processes()
    design = pd.read_csv(design_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    results, checkpoint_metadata = read_complete_checkpoint(checkpoint, design)
    validated = validate_results(
        design, results, protocol, formal=True, design_sha256=file_sha256(design_path)
    )
    provenance_audit = validate_runtime_source_provenance(checkpoint, results)
    replay_audit = validate_semantic_replay(
        checkpoint.parent / "semantic_replay", results, checkpoint_metadata,
    )
    temporal_binding_path = ROOT / "release/e31_temporal_gate_binding_audit.json"
    temporal_binding = json.loads(temporal_binding_path.read_text(encoding="utf-8"))
    if (temporal_binding.get("status")
            != "PASS_LIMITATION_BOUND_NO_RETROACTIVE_PRECOMMIT_CLAIM"
            or temporal_binding.get("overall_temporal_provenance_rating") != "PARTIAL"
            or temporal_binding.get("formal_checkpoint_sha256") != sha256(checkpoint)):
        raise RuntimeError("E31 temporal-gate limitation audit is absent or stale")

    temporary = final_dir.with_name(final_dir.name + f".{os.getpid()}.tmp")
    temporary_analysis = analysis_dir.with_name(analysis_dir.name + f".{os.getpid()}.tmp")
    if temporary.exists():
        shutil.rmtree(temporary)
    if temporary_analysis.exists():
        shutil.rmtree(temporary_analysis)
    temporary.mkdir(parents=True)
    result_path = temporary / "formal_results.csv"
    results.sort_values("run_order", kind="stable").to_csv(result_path, index=False)
    snapshot_path = temporary / "checkpoint_final.sqlite3"
    sqlite_snapshot(checkpoint, snapshot_path)
    reread = pd.read_csv(result_path)
    if len(reread) != len(validated) or not reread["run_order"].tolist() == list(range(len(design))):
        raise ValueError("sealed result CSV failed round-trip coverage validation")
    analysis_gate = write_analysis_packet(
        design, validated, protocol, temporary_analysis, formal=True, smoke=False
    )
    missing_analysis = [
        name for name in FORMAL_ANALYSIS_FILENAMES if not (temporary_analysis / name).is_file()
    ]
    if missing_analysis:
        raise RuntimeError(f"formal analysis packet is incomplete: {missing_analysis}")
    family_dir = temporary_analysis / "family_inference"
    correction_gate_path = (
        ROOT / "data/v11/e31_factorial_pareto/posthoc_family_inference_correction_gate.json"
    )
    contrast_expansion_gate_path = (
        ROOT / "data/v11/e31_factorial_pareto/posthoc_contrast_expansion_gate.json"
    )
    correction_audit = write_correction_packet(
        validated,
        family_dir,
        protocol=protocol,
        gate=json.loads(correction_gate_path.read_text(encoding="utf-8")),
        contrast_gate=json.loads(contrast_expansion_gate_path.read_text(encoding="utf-8")),
        results_sha256=sha256(result_path),
    )
    if (correction_audit.get("status") != "PASS_POSTHOC_FAMILY_INFERENCE_CORRECTION"
            or correction_audit.get("legacy_input_cluster_inference_valid") is not False
            or correction_audit.get("n_independent_family_clusters") != 15
            or correction_audit.get("family_cluster_degrees_of_freedom") != 14
            or correction_audit.get("unseen_family_generalization_status") != "BLOCKED"):
        raise RuntimeError("E31 family-level inference correction packet is incomplete")
    persisted_analysis_gate = json.loads(
        (temporary_analysis / "analysis_gate_audit.json").read_text(encoding="utf-8")
    )
    sensitivity_gate = analysis_gate.get("pareto_aggregation_sensitivity", {})
    disagreement_count = sensitivity_gate.get("disagreement_cell_count")
    disagreement_cells = sensitivity_gate.get("disagreement_cells")
    agreement = sensitivity_gate.get("frontier_membership_agreement_all_schemes")
    invariant_claim = sensitivity_gate.get(
        "bounded_aggregation_invariant_frontier_claim_allowed"
    )
    if (persisted_analysis_gate != analysis_gate
            or analysis_gate.get("result_rows") != len(design)
            or analysis_gate.get("formal_requested") is not True
            or not isinstance(analysis_gate.get("dual_estimand_primary"), dict)
            or not isinstance(analysis_gate.get("factorial_model"), dict)
            or analysis_gate.get("pareto_inference_role")
            != "EXPLORATORY_POSTHOC_AGGREGATION"
            or sensitivity_gate.get("status")
            != "FOUR_SCHEME_FRONTIER_MEMBERSHIP_AUDITED"
            or sensitivity_gate.get("treatment_cells") != 72
            or not isinstance(
                invariant_claim, bool,
            )
            or not isinstance(agreement, bool)
            or not isinstance(disagreement_count, int) or isinstance(disagreement_count, bool)
            or disagreement_count < 0
            or not isinstance(disagreement_cells, list)
            or disagreement_count != len(disagreement_cells)
            or agreement is not (disagreement_count == 0)
            or invariant_claim is not agreement):
        raise RuntimeError("formal E31 analysis gate is incomplete or not internally bound")

    environment_path = checkpoint.parent / "environment.json"
    release_gate_path = ROOT / "data/v11/e31_factorial_pareto/formal_release_gate.json"
    method_gate_path = ROOT / "data/v11/e31_factorial_pareto/preanalysis_method_erratum_gate.json"
    host_gate_path = ROOT / "data/v11/e31_factorial_pareto/host_environment_limitation_gate.json"
    transitive_source_gate_path = (
        ROOT / "data/v11/e31_factorial_pareto/transitive_source_provenance_gate.json"
    )
    pareto_aggregation_gate_path = (
        ROOT / "data/v11/e31_factorial_pareto/posthoc_pareto_aggregation_gate.json"
    )
    contrast_expansion_gate_path = (
        ROOT / "data/v11/e31_factorial_pareto/posthoc_contrast_expansion_gate.json"
    )
    manifest = {
        "status": "FORMAL_COMPLETE_PENDING_INDEPENDENT_RELEASE_VERIFICATION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": protocol["experiment_id"],
        **checkpoint_metadata,
        "scheduled_rows": int(len(design)),
        "unique_input_hashes": int(design["input_circuit_sha256"].nunique()),
        "outer_families": int(design["circuit_family"].nunique()),
        "run_order_contiguous": True,
        "schedule_identity_exact": True,
        "formal_analysis_gate_passed": True,
        "independent_release_verification_required": True,
        "independent_release_verification_embedded_in_completion": False,
        "source_provenance_rating": "PARTIAL",
        "complete_cryptographic_prerun_source_closure": False,
        "static_first_party_source_closure_count": provenance_audit[
            "resolved_source_count"
        ],
        "dynamic_imports_not_proven": provenance_audit["dynamic_imports_not_proven"],
        "temporal_gate_provenance_rating": "PARTIAL",
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
        "family_inference_correction_status": correction_audit["status"],
        "unseen_family_generalization_status": "BLOCKED",
        "semantic_replay": replay_audit,
        "pareto_inference_role": "EXPLORATORY_POSTHOC_AGGREGATION",
        "pareto_aggregation_functionals_preregistered": False,
        "pareto_frontier_membership_agreement_all_schemes": sensitivity_gate[
            "frontier_membership_agreement_all_schemes"
        ],
        "pareto_aggregation_invariant_claim_allowed": sensitivity_gate[
            "bounded_aggregation_invariant_frontier_claim_allowed"
        ],
        "pareto_aggregation_disagreement_cell_count": sensitivity_gate[
            "disagreement_cell_count"
        ],
        "artifacts": {
            "formal_results.csv": {"sha256": sha256(result_path), "bytes": result_path.stat().st_size},
            "checkpoint_final.sqlite3": {
                "sha256": sha256(snapshot_path), "bytes": snapshot_path.stat().st_size,
            },
        },
        "analysis_artifacts": {
            name: {
                "sha256": sha256(temporary_analysis / name),
                "bytes": (temporary_analysis / name).stat().st_size,
            }
            for name in FORMAL_ANALYSIS_FILENAMES
        },
        "family_inference_artifacts": {
            **correction_audit["artifacts"],
            "family_inference_correction_audit.json": {
                "sha256": sha256(family_dir / "family_inference_correction_audit.json"),
                "bytes": (family_dir / "family_inference_correction_audit.json").stat().st_size,
            },
        },
        "bindings": {
            "protocol_sha256": file_sha256(protocol_path),
            "design_manifest_sha256": file_sha256(design_path),
            "environment_sha256": sha256(environment_path),
            "formal_release_gate_sha256": sha256(release_gate_path),
            "preanalysis_method_erratum_gate_sha256": sha256(method_gate_path),
            "host_environment_limitation_gate_sha256": sha256(host_gate_path),
            "transitive_source_provenance_gate_sha256": sha256(
                transitive_source_gate_path
            ),
            "posthoc_pareto_aggregation_gate_sha256": sha256(
                pareto_aggregation_gate_path
            ),
            "posthoc_contrast_expansion_gate_sha256": sha256(
                contrast_expansion_gate_path
            ),
            "posthoc_family_inference_correction_gate_sha256": sha256(
                correction_gate_path
            ),
            "temporal_gate_binding_audit_sha256": sha256(temporal_binding_path),
        },
        "release_rule": (
            "only this sealed directory may become release-eligible after the independent "
            "release verifier passes; a live checkpoint CSV is never release-eligible"
        ),
    }
    manifest_path = temporary / "formal_completion_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    install_seal_pair(temporary_analysis, analysis_dir, temporary, final_dir)
    return final_dir / manifest_path.name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--final-dir", type=Path, default=DEFAULT_FINAL)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS)
    args = parser.parse_args()
    print(finalize(
        args.checkpoint, args.design, args.protocol, args.final_dir, args.analysis_dir
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
