"""Build the separate, fail-closed release manifest for pre-paper evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
EVIDENCE_ROOT = PROJECT_ROOT / "data" / "v10" / "prepaper"
EXCLUDED_PARTS = {
    "preflight_invalid", "smoke", "chunks", "outputs", "qasm",
    "quasar-artifact", "repo", "build", "build-ninja", ".venv", "__pycache__",
}
INCLUDED_SUFFIXES = {".csv", ".json", ".md", ".txt", ".log", ".pdf", ".svg", ".png", ".qasm"}
SUPERSEDED_EVIDENCE = {
    "hardware_validation/ehw_runs_full_20260811_113247.csv",
    "hardware_validation/ehw_summary_full_20260811_113247.csv",
    "hardware_validation/ehw_metadata_full_20260811_113247.json",
    "hardware_validation/ehw_runs_full_20260811_115642.csv",
    "hardware_validation/ehw_summary_full_20260811_115642.csv",
    "hardware_validation/ehw_metadata_full_20260811_115642.json",
    "hardware_validation/ehw_metadata_full_20260811_113247.json",
}
REQUIRED = {
    "E3 corrected": "e03/*_revalidated.csv",
    "E14 corrected": "e14/*_revalidated.csv",
    "E18 corrected": "e18/e18_clifford_t_e18_full_*.csv",
    "E23 corrected": "e23/e23_ag_canonical_results.csv",
    "E26 corrected": "e26/phase2b_full_validation_v8.csv",
    "SOTA input manifest": "sota/inputs/benchmark_manifest.csv",
    "SOTA input metadata": "sota/inputs/benchmark_manifest_metadata.json",
    "SOTA custom raw": "sota/raw/custom_hybrid_*.csv",
    "SOTA Qiskit raw": "sota/raw/qiskit_default_*.csv",
    "SOTA Cirq raw": "sota/raw/cirq_default_*.csv",
    "SOTA tket raw": "sota/raw/tket_default_*.csv",
    "held-out input manifest": "heldout/inputs/benchmark_manifest.csv",
    "held-out seal": "heldout/sealed_predictions/SEALED.json",
    "held-out model": "heldout/sealed_predictions/model.json",
    "held-out frozen predictions": "heldout/sealed_predictions/heldout_predictions.csv",
    "held-out Qiskit raw": "heldout/results/raw/qiskit_default_*.csv",
    "held-out tket raw": "heldout/results/raw/tket_default_*.csv",
    "held-out metrics": "heldout/analysis/heldout_metrics.json",
    "held-out joined outcomes": "heldout/analysis/heldout_predictions_outcomes.csv",
    "held-out nested bootstrap": "heldout/analysis/mcc_nested_bootstrap_10000.csv",
    "Quasar raw final": "external_baselines/quasar/shared_520/quasar_shared_520.csv",
    "Quasar revalidated final": "external_baselines/quasar/shared_520/quasar_shared_520_revalidated.csv",
    "Quasar metadata": "external_baselines/quasar/shared_520/metadata.json",
    "Quartz raw final": "external_baselines/quartz/shared_520/quartz_shared_520.csv",
    "Quartz revalidated final": "external_baselines/quartz/shared_520/quartz_shared_520_revalidated.csv",
    "Quartz metadata": "external_baselines/quartz/shared_520/metadata.json",
    "GUOQ preflight": "external_baselines/guoq/preflight/preflight.json",
    "GUOQ official artifact record": "external_baselines/guoq/preflight/official_artifact_record.json",
    "hardware validation canonical runs": "hardware_validation/ehw_runs_full_20260811_123958.csv",
    "hardware validation canonical summary": "hardware_validation/ehw_summary_full_20260811_123958.csv",
    "hardware validation canonical metadata": "hardware_validation/ehw_metadata_full_20260811_123958.json",
    "hardware validation analysis": "hardware_validation/analysis/hardware_validation_report.json",
    "hardware validation paired cells": "hardware_validation/analysis/paired_noise_aware_cells.csv",
    "held-out v2 input manifest": "heldout_v2/inputs/benchmark_manifest.csv",
    "held-out v2 seal": "heldout_v2/sealed_predictions/SEALED.json",
    "held-out v2 frozen predictions": "heldout_v2/sealed_predictions/heldout_v2_predictions.csv",
    "held-out v2 start gate": "heldout_v2/execution/START_GATE.json",
    "held-out v2 custom raw": "heldout_v2/results/raw/custom_default_*.csv",
    "held-out v2 Qiskit raw": "heldout_v2/results/raw/qiskit_default_*.csv",
    "held-out v2 Cirq raw": "heldout_v2/results/raw/cirq_default_*.csv",
    "held-out v2 tket raw": "heldout_v2/results/raw/tket_default_*.csv",
    "held-out v2 custom metadata": "heldout_v2/results/metadata/custom_default_metadata.json",
    "held-out v2 Qiskit metadata": "heldout_v2/results/metadata/qiskit_default_metadata.json",
    "held-out v2 Cirq metadata": "heldout_v2/results/metadata/cirq_default_metadata.json",
    "held-out v2 tket metadata": "heldout_v2/results/metadata/tket_default_metadata.json",
    "held-out v2 joined outcomes": "heldout_v2/analysis/heldout_v2_predictions_outcomes.csv",
    "held-out v2 unique-input audit": "heldout_v2/analysis/heldout_v1_v2_unique_inputs.csv",
    "held-out v2 nested bootstrap": "heldout_v2/analysis/combined_mcc_nested_bootstrap_10000.csv",
    "held-out v2 generator diagnostics": "heldout_v2/analysis/combined_generator_diagnostics.csv",
    "held-out v2 tool diagnostics": "heldout_v2/analysis/heldout_v2_tool_diagnostics.csv",
    "held-out v2 combined metrics": "heldout_v2/analysis/combined_heldout_metrics.json",
    "held-out v2 execution contract audit": "heldout_v2/analysis/execution_contract_audit.json",
    "held-out v2 layout verifier before-after audit": "heldout_v2/analysis/layout_verifier_before_after.json",
    "GUOQ BQSKit pilot results": "external_baselines/guoq/bqskit_pilot/guoq_bqskit_pilot.csv",
    "GUOQ BQSKit pilot metadata": "external_baselines/guoq/bqskit_pilot/metadata.json",
    "GUOQ BQSKit dependency lock": "external_baselines/guoq/bqskit_pilot/preflight/dependency_lock.json",
    "GUOQ BQSKit preregistration": "external_baselines/guoq/bqskit_pilot/preregistration.json",
    "GUOQ BQSKit local preflight": "external_baselines/guoq/bqskit_pilot/preflight/preflight.json",
    "GUOQ BQSKit metric revalidation": "external_baselines/guoq/bqskit_pilot/metric_revalidation.json",
    "external fidelity revalidation audit": "external_baselines/exact_fidelity_revalidation.json",
    "RQ1 audit": "analysis/rq1/audit.json",
    "RQ1 results": "analysis/rq1/rq1_results.json",
    "RQ3 audit": "analysis/rq3/audit.json",
    "RQ3 tool summary": "analysis/rq3/tool_summary.csv",
    "RQ3 paired tests": "analysis/rq3/pairwise_contrasts.csv",
    "RQ3 quality-runtime Pareto frontier": "analysis/rq3/quality_runtime_pareto_frontier.csv",
    "RQ3 quality-runtime Pareto summary": "analysis/rq3/quality_runtime_pareto_summary.csv",
    "RQ3 quality-runtime Pareto pairwise": "analysis/rq3/quality_runtime_pareto_pairwise.csv",
    "external audit": "analysis/external/audit.json",
    "external summary": "analysis/external/external_summary.csv",
    "external paired tests": "analysis/external/external_pairwise.csv",
    "figure 1 source": "figures/source_data/fig01_rq1_listing_forest.csv",
    "figure 2 source": "figures/source_data/fig02_heldout_generator_rates.csv",
    "figure 3 source": "figures/source_data/fig03_tool_summary.csv",
    "figure 4 source": "figures/source_data/fig04_external_baselines.csv",
    "figure 1 PDF": "figures/fig01_rq1_listing_forest.pdf",
    "figure 2 PDF": "figures/fig02_heldout_generator_rates.pdf",
    "figure 3 PDF": "figures/fig03_tool_summary.pdf",
    "figure 4 PDF": "figures/fig04_external_baselines.pdf",
    "figure 1 SVG": "figures/fig01_rq1_listing_forest.svg",
    "figure 2 SVG": "figures/fig02_heldout_generator_rates.svg",
    "figure 3 SVG": "figures/fig03_tool_summary.svg",
    "figure 4 SVG": "figures/fig04_external_baselines.svg",
    "figure 1 600 dpi PNG": "figures/fig01_rq1_listing_forest.png",
    "figure 2 600 dpi PNG": "figures/fig02_heldout_generator_rates.png",
    "figure 3 600 dpi PNG": "figures/fig03_tool_summary.png",
    "figure 4 600 dpi PNG": "figures/fig04_external_baselines.png",
    "figure mechanical audit": "figures/figure_audit.json",
    "workspace coverage audit": "audit/workspace_coverage.json",
    "workspace file inventory": "audit/workspace_file_inventory.csv",
    "workspace directory inventory": "audit/workspace_directory_inventory.csv",
}
PROJECT_EVIDENCE_FILES = (
    "data/v11/e31_factorial_pareto/formal_run/final/formal_results.csv",
    "data/v11/e31_factorial_pareto/formal_run/final/checkpoint_final.sqlite3",
    "data/v11/e31_factorial_pareto/formal_run/final/formal_completion_manifest.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/equal_budget_pareto_summary.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/full_factorial_model_coefficients.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/full_factorial_model_diagnostics.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/posthoc_marginal_contrasts.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/pareto_aggregation_sensitivity.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/pareto_hypervolume_audit.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/analysis_gate_audit.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/run_order_temporal_diagnostics.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/host_environment_audit.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/fidelity_threshold_sensitivity.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/runtime_outcome_audit.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/basis_weight_sensitivity.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/validity_runtime_frontier/frontier_by_budget.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/validity_runtime_frontier/frontier_audit.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/validity_runtime_frontier/validity_runtime_frontier.png",
    "data/v11/e31_factorial_pareto/formal_run/analysis/validity_runtime_frontier/validity_runtime_frontier.pdf",
    "data/v11/e31_factorial_pareto/formal_run/analysis/specification_influence/specification_curve.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/specification_influence/leave_one_family_out.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/specification_influence/specification_influence_audit.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/specification_influence/specification_curve.png",
    "data/v11/e31_factorial_pareto/formal_run/analysis/specification_influence/specification_curve.pdf",
    "data/v10/prepaper/heldout/analysis/calibration_null/calibration_bins.csv",
    "data/v10/prepaper/heldout/analysis/calibration_null/exact_family_block_label_permutations.csv",
    "data/v10/prepaper/heldout/analysis/calibration_null/calibration_null_audit.json",
    "data/v10/prepaper/heldout/analysis/calibration_null/reliability_diagram.png",
    "data/v10/prepaper/heldout/analysis/calibration_null/reliability_diagram.pdf",
    "data/v10/prepaper/analysis/cost_vector_scope/e18_dependency_t_depth.csv",
    "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
    "data/v10/prepaper/analysis/hardware_routing_overhead/hardware_routing_cells.csv",
    "data/v10/prepaper/analysis/hardware_routing_overhead/hardware_routing_overhead_audit.json",
    "data/v10/prepaper/heldout_v2/analysis/generalization_ood/heldout_instance_domain_distance.csv",
    "data/v10/prepaper/heldout_v2/analysis/generalization_ood/heldout_family_calibration_ood.csv",
    "data/v10/prepaper/heldout_v2/analysis/generalization_ood/heldout_feature_ablation.csv",
    "data/v10/prepaper/heldout_v2/analysis/generalization_ood/training_leave_one_generator_out.csv",
    "data/v10/prepaper/heldout_v2/analysis/generalization_ood/family_distance_calibration.png",
    "data/v10/prepaper/heldout_v2/analysis/generalization_ood/family_distance_calibration.pdf",
    "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/family_inference/fixed_panel_factorial_71_descriptive.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/family_inference/fixed_panel_marginal_30_descriptive.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/family_inference/family_supportive_factorial_71.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/family_inference/family_supportive_marginal_30.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/family_inference/per_family_factorial_71_effects.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/family_inference/per_family_marginal_30_effects.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/family_inference/primary_estimand_validity.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/family_inference/family_inference_correction_audit.json",
    "data/v11/e31_factorial_pareto/formal_run/semantic_replay/canary_gate.json",
    "data/v11/e31_factorial_pareto/formal_run/semantic_replay/semantic_replay_gate.json",
    "data/v11/e31_factorial_pareto/formal_run/semantic_replay/semantic_replay_manifest.json",
    "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/semantic_cell_structural_metrics.csv",
    "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/solution_diversity_by_input.csv",
    "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/distributional_risk_summary.json",
    "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/structural_distribution_audit.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_cells.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/worker_sensitivity.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/same_process_cache_repeats.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_audit.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/fragility_listing/listing_extremes_cells.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/fragility_listing/listing_extremes_by_family.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/fragility_listing/single_input_influence.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/fragility_listing/equal_budget_conclusion_sensitivity.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/fragility_listing/fragility_listing_audit.json",
    "data/v9/e12/version_stack_reconciliation/shared_key_comparison.csv",
    "data/v9/e12/version_stack_reconciliation/version_stack_reconciliation_audit.json",
    "data/v11/compiler_version_sensitivity/frozen_panel.csv",
    "data/v11/compiler_version_sensitivity/all_version_results.csv",
    "data/v11/compiler_version_sensitivity/per_tool_version_comparison.csv",
    "data/v11/compiler_version_sensitivity/compiler_version_sensitivity_audit.json",
    "data/v11/compiler_version_sensitivity/independent_verification.json",
    "data/v11/compiler_version_sensitivity/runs/qiskit-2.3.1/results.csv",
    "data/v11/compiler_version_sensitivity/runs/qiskit-2.3.1/environment.json",
    "data/v11/compiler_version_sensitivity/runs/qiskit-2.3.1/resolved_requirements.txt",
    "data/v11/compiler_version_sensitivity/runs/qiskit-2.4.1/results.csv",
    "data/v11/compiler_version_sensitivity/runs/qiskit-2.4.1/environment.json",
    "data/v11/compiler_version_sensitivity/runs/qiskit-2.4.1/resolved_requirements.txt",
    "data/v11/compiler_version_sensitivity/runs/cirq-1.6.0/results.csv",
    "data/v11/compiler_version_sensitivity/runs/cirq-1.6.0/environment.json",
    "data/v11/compiler_version_sensitivity/runs/cirq-1.6.0/resolved_requirements.txt",
    "data/v11/compiler_version_sensitivity/runs/cirq-1.6.1/results.csv",
    "data/v11/compiler_version_sensitivity/runs/cirq-1.6.1/environment.json",
    "data/v11/compiler_version_sensitivity/runs/cirq-1.6.1/resolved_requirements.txt",
    "data/v11/compiler_version_sensitivity/runs/pytket-2.17.0/results.csv",
    "data/v11/compiler_version_sensitivity/runs/pytket-2.17.0/environment.json",
    "data/v11/compiler_version_sensitivity/runs/pytket-2.17.0/resolved_requirements.txt",
    "data/v11/compiler_version_sensitivity/runs/pytket-2.18.0/results.csv",
    "data/v11/compiler_version_sensitivity/runs/pytket-2.18.0/environment.json",
    "data/v11/compiler_version_sensitivity/runs/pytket-2.18.0/resolved_requirements.txt",
    "data/v11/compiler_version_sensitivity/runs/custom-current/results.csv",
    "data/v11/compiler_version_sensitivity/runs/custom-current/environment.json",
    "data/v11/compiler_version_sensitivity/runs/custom-current/resolved_requirements.txt",
    "data/v11/e31_factorial_pareto/formal_run/analysis/mixed_model_diagnostics/mixed_model_fixed_effects.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/mixed_model_diagnostics/mixed_model_summary.txt",
    "data/v11/e31_factorial_pareto/formal_run/analysis/mixed_model_diagnostics/mixed_model_diagnostics.json",
    "data/v10/prepaper/heldout_v2/analysis/generalization_ood/class_gateset/leave_one_algorithm_class_out.csv",
    "data/v10/prepaper/heldout_v2/analysis/generalization_ood/class_gateset/leave_one_exact_gate_set_out.csv",
    "data/v10/prepaper/heldout_v2/analysis/generalization_ood/class_gateset/algorithm_class_taxonomy.csv",
    "data/v10/prepaper/heldout_v2/analysis/generalization_ood/class_gateset/class_gateset_generalization_audit.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/pyzx_large_semantic/pyzx_large_semantic_cells.csv",
    "data/v11/e31_factorial_pareto/formal_run/analysis/pyzx_large_semantic/pyzx_large_semantic_audit.json",
    "data/v11/e31_factorial_pareto/formal_run/analysis/native_semantic_verifier/native_semantic_verifier.json",
    "data/v11/e31_factorial_pareto/formal_run/environment.json",
    "data/v11/e31_factorial_pareto/input_duplicate_isomorphism_audit.json",
    "data/v10/prepaper/e03/e03_scaling_model_audit.json",
    "data/v11/e31_factorial_pareto/formal_release_gate.json",
    "data/v11/e31_factorial_pareto/preanalysis_method_erratum_gate.json",
    "data/v11/e31_factorial_pareto/host_environment_limitation_gate.json",
    "data/v11/e31_factorial_pareto/transitive_source_provenance_gate.json",
    "data/v11/e31_factorial_pareto/posthoc_pareto_aggregation_gate.json",
    "data/v11/e31_factorial_pareto/posthoc_contrast_expansion_gate.json",
    "data/v11/e31_factorial_pareto/posthoc_family_inference_correction_gate.json",
    "data/v11/e31_factorial_pareto/preflight_invalid/formal_host_interruption_20260813T060308Z/recovery_audit.json",
    "docs/review/e31_preanalysis_method_erratum_2026-08-24.md",
    "docs/review/e31_host_environment_limitation_2026-08-24.md",
    "docs/review/e31_transitive_source_provenance_limitation_2026-08-24.md",
    "docs/review/e31_pareto_aggregation_limitation_2026-08-24.md",
    "docs/review/e31_contrast_expansion_limitation_2026-08-24.md",
    "docs/review/e31_family_inference_correction_2026-08-26.md",
    "docs/review/metric_evidence_registry_2026-08-26.json",
    "docs/review/metric_audit_ledger_2026-08-24.csv",
    "docs/review/metric_audit_summary_2026-08-24.json",
    "docs/review/metric_audit_resolution_2026-08-24.md",
    "docs/review/metric_registry_fragments/sections_01_06.json",
    "docs/review/metric_registry_fragments/sections_07_12.json",
    "docs/review/metric_registry_fragments/sections_13_18.json",
    "release/e31_temporal_gate_binding_audit.json",
    "release/e31_independent_release_verification_receipt.json",
    "release/frozen_e31_receipt/scripts/verify_prepaper_release_manifest.py",
    "release/circuit_semantics_scope_audit.json",
    "release/qubit_permutation_metamorphic_audit.json",
    "release/transformation_failure_localization_audit.json",
    "release/comparator_version_publication_audit.json",
    "release/contribution_independence_audit.json",
    "release/novelty_counterexample_audit.json",
    "release/compiler_integration_audit.json",
    "release/prepaper_capsule_inner_manifest.json",
    "release/prepaper_restore_capsule.zip",
    "release/prepaper_archive_restore_audit.json",
    "release/prepaper_retrospective_binding_audit.json",
    "release/prepaper_external_blockers.csv",
    "release/prepaper_readiness_verdict.json",
)
ADDITIONAL_ARTIFACT_MANIFESTS = (
    "data/v11/e32_telemetry/artifact_manifest.json",
    "data/v11/e33_real_scale/artifact_manifest.json",
    "data/v11/e34_mqt_cross_abstraction/artifact_manifest.json",
    "data/v11/e35_benchpress_stress/artifact_manifest.json",
    "data/v11/e36_pyzx_third_artifact/artifact_manifest.json",
    "data/v11/e37_energy_cost_telemetry/artifact_manifest.json",
)
ADDITIONAL_RELEASE_EVIDENCE = (
    "release/e32_telemetry_independent_verification_receipt.json",
    "release/e33_real_scale_independent_verification_receipt.json",
    "release/e34_mqt_cross_abstraction_independent_verification_receipt.json",
    "release/e35_benchpress_stress_independent_verification_receipt.json",
    "release/e36_pyzx_third_artifact_independent_verification_receipt.json",
    "release/e37_energy_cost_independent_verification_receipt.json",
    "docs/review/e32_telemetry_verifier_erratum_2026-08-31.md",
)
ADDITIONAL_PREFLIGHT_ROOTS = (
    "data/v11/e33_real_scale_preflight_invalid_keyerror_x",
    "data/v11/e34_mqt_cross_abstraction_preflight_invalid_barrier",
    "data/v11/e36_pyzx_third_artifact_preflight_invalid_full_optimize_domain",
    "data/v11/e36_pyzx_third_artifact_preflight_invalid_optimizer_dispatch",
)
CAPSULE_OUTER_FILES = {
    "release/prepaper_capsule_inner_manifest.json",
    "release/prepaper_restore_capsule.zip",
    "release/prepaper_archive_restore_audit.json",
    "release/prepaper_readiness_verdict.json",
}
SOURCE_FILES = (
    "requirements.txt",
    "requirements-lock.txt",
    "pyproject.toml",
    "Dockerfile",
    "experiments/prepaper_protocol.json",
    "experiments/sota_benchmark.py",
    "experiments/prepaper_heldout.py",
    "experiments/external_quasar_benchmark.py",
    "experiments/external_quartz_benchmark.py",
    "experiments/external_guoq_benchmark.py",
    "experiments/external_guoq_bqskit_pilot.py",
    "experiments/guoq_bqskit_server.py",
    "experiments/heldout_v2_protocol.json",
    "experiments/heldout_v2_execution_protocol.json",
    "experiments/heldout_v2_seal.py",
    "experiments/heldout_v2_execute.py",
    "experiments/e31_factorial_pareto_protocol.json",
    "experiments/e31_factorial_pareto_schema.json",
    "experiments/e31_factorial_pareto_design.py",
    "experiments/e31_shared_rule_worker.py",
    "experiments/e31_resource_smoke.py",
    "experiments/e31_resource_profile_worker.py",
    "experiments/e31_formal_orchestrator.py",
    "experiments/e31_recover_interrupted_suffix.py",
    "experiments/e31_listing_phase2b_interaction.py",
    "experiments/e32_telemetry_worker.py",
    "experiments/e32_telemetry_panel.py",
    "experiments/e32_telemetry_protocol.json",
    "experiments/e33_real_scale_panel.py",
    "experiments/e33_real_scale_protocol.json",
    "experiments/e34_mqt_cross_abstraction.py",
    "experiments/e34_mqt_cross_abstraction_protocol.json",
    "experiments/e35_benchpress_stress.py",
    "experiments/e35_benchpress_stress_protocol.json",
    "experiments/e36_pyzx_third_artifact.py",
    "experiments/e36_pyzx_third_artifact_protocol.json",
    "experiments/e37_energy_cost_telemetry.py",
    "experiments/e37_energy_cost_telemetry_protocol.json",
    "experiments/hardware_validation/run.py",
    "experiments/hardware_validation/real_hardware_protocol.py",
    "data/v10/prepaper/external_baselines/quartz/adapter/build_quartz_windows.cmd",
    "data/v10/prepaper/external_baselines/quartz/adapter/quartz_test_optimize_io.patch",
    "analysis/prepaper_rq1_representation.py",
    "analysis/prepaper_rq3_tool_comparison.py",
    "analysis/prepaper_heldout_analysis.py",
    "analysis/prepaper_external_baselines.py",
    "analysis/revalidate_external_exact_fidelity.py",
    "analysis/revalidate_guoq_bqskit_pilot_metrics.py",
    "analysis/prepaper_figures.py",
    "analysis/prepaper_hardware_validation.py",
    "analysis/heldout_v2_combined_analysis.py",
    "analysis/e31_factorial_pareto_analysis.py",
    "analysis/e31_finalize_formal_run.py",
    "analysis/e31_posthoc_family_inference.py",
    "analysis/e31_listing_phase2b_analysis.py",
    "analysis/e31_family_cluster_power.py",
    "analysis/e31_dual_estimand_power.py",
    "analysis/e31_structural_distribution_metrics.py",
    "analysis/e31_fidelity_threshold_sensitivity.py",
    "analysis/circuit_semantics_scope_audit.py",
    "analysis/e31_input_duplicate_isomorphism_audit.py",
    "analysis/qubit_permutation_metamorphic_audit.py",
    "analysis/e03_scaling_model_audit.py",
    "analysis/e31_runtime_outcome_audit.py",
    "analysis/e31_basis_weight_sensitivity.py",
    "analysis/e31_validity_runtime_frontier.py",
    "analysis/e31_specification_influence_audit.py",
    "analysis/heldout_calibration_null_audit.py",
    "analysis/cost_vector_scope_audit.py",
    "analysis/hardware_routing_overhead_audit.py",
    "analysis/heldout_generalization_ood_audit.py",
    "analysis/e31_resource_profile_audit.py",
    "analysis/e31_fragility_listing_audit.py",
    "analysis/e12_version_stack_reconciliation.py",
    "analysis/compiler_version_sensitivity_audit.py",
    "analysis/compiler_version_sensitivity_verifier.py",
    "analysis/rerun_reconciliation.py",
    "experiments/compiler_version_panel_worker.py",
    "analysis/e31_mixed_model_diagnostics.py",
    "analysis/transformation_failure_localization_audit.py",
    "analysis/heldout_class_gateset_generalization_audit.py",
    "analysis/e31_pyzx_large_semantic_audit.py",
    "analysis/e31_native_semantic_verifier.py",
    "analysis/contribution_independence_audit.py",
    "analysis/novelty_counterexample_audit.py",
    "analysis/compiler_integration_audit.py",
    "analysis/prepaper_retrospective_binding_audit.py",
    "scripts/generate_prepaper_external_blockers.py",
    "scripts/generate_prepaper_readiness_verdict.py",
    "scripts/freeze_e32_telemetry_protocol.py",
    "scripts/verify_e32_telemetry_panel.py",
    "scripts/verify_e32_telemetry_panel_v2.py",
    "scripts/freeze_e33_real_scale_protocol.py",
    "scripts/verify_e33_real_scale_panel.py",
    "scripts/verify_e34_mqt_cross_abstraction.py",
    "scripts/verify_e35_benchpress_stress.py",
    "scripts/verify_e36_pyzx_third_artifact.py",
    "scripts/verify_e37_energy_cost_telemetry.py",
    "src/integrations/__init__.py",
    "src/integrations/qiskit_pass.py",
    "scripts/generate_prepaper_release_manifest.py",
    "scripts/generate_e31_formal_release_gate.py",
    "scripts/verify_prepaper_release_manifest.py",
    "scripts/archive_restore_audit.py",
    "scripts/audit_workspace_coverage.py",
    "scripts/audit_direct_dependencies.py",
    "scripts/audit_equivalence_verifier_agreement.py",
    "scripts/audit_semantic_mutation_sentinels.py",
    "scripts/audit_rewrite_properties.py",
    "scripts/audit_rewrite_order_confluence.py",
    "scripts/audit_e31_first_party_import_closure.py",
    "scripts/audit_e31_semantic_replay.py",
    "scripts/audit_e31_temporal_gate_binding.py",
    "scripts/write_e31_independent_verification_receipt.py",
    "scripts/verify_e31_structural_distribution_metrics.py",
    "scripts/generate_metric_audit_ledger.py",
    "scripts/bootstrap_metric_evidence_registry.py",
    "scripts/merge_metric_registry_fragments.py",
    "scripts/verify_metric_audit_ledger.py",
    "scripts/verify_prepaper_figures.py",
    "scripts/generate_sbom.py",
    "scripts/verify_sbom.py",
    "scripts/audit_external_links.py",
    "scripts/repair_capsule_inner_manifest_closure.py",
    "release/sbom.cdx.json",
    "release/external_link_audit.json",
    "release/equivalence_verifier_agreement_audit.json",
    "release/semantic_mutation_sentinel_audit.json",
    "release/rewrite_property_sweep_audit.json",
    "release/rewrite_order_confluence_audit.json",
    "release/e31_first_party_import_closure_audit.json",
    "data/v11/e31_factorial_pareto/design_manifest.csv",
    "data/v11/e31_factorial_pareto/design_metadata.json",
    "data/v11/e31_factorial_pareto/dual_estimand_power.json",
    "src/circuits/__init__.py",
    "src/optimisation/__init__.py",
    "src/optimisation/base.py",
    "src/optimisation/_gate_predicates.py",
    "src/optimisation/ceiling_aware.py",
    "src/optimisation/constants.py",
    "src/equivalence.py",
    "src/optimisation/phase1/simulated_annealing.py",
    "src/optimisation/phase1/random_local_search.py",
    "src/optimisation/phase1/genetic_algorithm.py",
    "src/optimisation/phase1/__init__.py",
    "src/circuits/real_benchmarks.py",
    "src/circuits/generator_v2.py",
    "analysis/structural_ceiling.py",
    "src/optimisation/phase1/greedy.py",
    "src/optimisation/phase1/wire_traversal.py",
    "src/optimisation/phase2/commutation_rewriter.py",
    "src/optimisation/phase2/__init__.py",
    "src/optimisation/phase2/template_matcher.py",
    "tests/test_circuit_generation.py",
    "tests/test_stochastic_incumbent.py",
    "tests/test_prepaper_statistics.py",
    "tests/test_sota_resource_metrics.py",
    "tests/test_fidelity_estimator.py",
    "tests/test_hardware_validation_metrics.py",
    "tests/test_prepaper_hardware_analysis.py",
    "tests/test_external_guoq_benchmark.py",
    "tests/test_external_guoq_bqskit_pilot.py",
    "tests/test_heldout_v2_seal.py",
    "tests/test_heldout_v2_execution.py",
    "tests/test_e31_factorial_pareto.py",
    "tests/test_e31_formal_orchestrator.py",
    "tests/test_e31_recover_interrupted_suffix.py",
    "tests/test_e31_finalize_formal_run.py",
    "tests/test_e31_release_verifier.py",
    "tests/test_archive_restore_audit.py",
    "tests/test_e31_structural_distribution_metrics.py",
    "tests/test_e31_fidelity_threshold_sensitivity.py",
    "tests/test_circuit_semantics_scope_audit.py",
    "tests/test_e31_input_duplicate_isomorphism_audit.py",
    "tests/test_qubit_permutation_metamorphic_audit.py",
    "tests/test_e03_scaling_model_audit.py",
    "tests/test_e31_runtime_outcome_audit.py",
    "tests/test_e31_basis_weight_sensitivity.py",
    "tests/test_e31_validity_runtime_frontier.py",
    "tests/test_e31_specification_influence_audit.py",
    "tests/test_heldout_calibration_null_audit.py",
    "tests/test_cost_vector_scope_audit.py",
    "tests/test_hardware_routing_overhead_audit.py",
    "tests/test_heldout_generalization_ood_audit.py",
    "tests/test_e31_resource_profile_audit.py",
    "tests/test_e31_fragility_listing_audit.py",
    "tests/test_e12_version_stack_reconciliation.py",
    "tests/test_compiler_version_sensitivity_audit.py",
    "tests/test_compiler_version_sensitivity_verifier.py",
    "tests/test_e31_mixed_model_diagnostics.py",
    "tests/test_transformation_failure_localization_audit.py",
    "tests/test_heldout_class_gateset_generalization_audit.py",
    "tests/test_e31_pyzx_large_semantic_audit.py",
    "tests/test_e31_native_semantic_verifier.py",
    "tests/test_comparator_version_publication_audit.py",
    "tests/test_contribution_independence_audit.py",
    "tests/test_novelty_counterexample_audit.py",
    "tests/test_compiler_integration.py",
    "tests/test_equivalence_verifier_agreement_audit.py",
    "tests/test_semantic_mutation_sentinels.py",
    "tests/test_rewrite_property_sweep.py",
    "tests/test_rewrite_order_confluence_audit.py",
    "tests/test_e31_first_party_import_closure_audit.py",
    "tests/test_direct_dependencies.py",
    "tests/test_metric_audit_ledger.py",
    "tests/test_verify_metric_audit_ledger.py",
    "tests/test_listing_phase2b_interaction.py",
    "tests/test_generate_e31_formal_release_gate.py",
    "tests/test_sbom.py",
    "tests/test_external_link_audit.py",
    "tests/test_e32_telemetry_panel.py",
    "tests/test_e33_real_scale_panel.py",
    "tests/test_e34_mqt_cross_abstraction.py",
    "tests/test_e35_benchpress_stress.py",
    "tests/test_e36_pyzx_third_artifact.py",
    "tests/test_e37_energy_cost_telemetry.py",
    "data/DATA_CANONICAL.md",
    "docs/data_dictionary.md",
    "docs/references/literature_review.md",
    "docs/references/search_ledger.md",
    "docs/references/unified_references.md",
    "docs/review/project_audit_2026-08-09.md",
    "docs/review/prepaper_protocol_2026-08-09.md",
    "docs/review/prepaper_novelty_matrix_2026-08-10.md",
    "docs/review/prepaper_novelty_refresh_2026-08-24.md",
    "docs/review/prepaper_forward_negative_citation_audit_2026-08-24.md",
    "docs/review/prepaper_arxiv_publication_version_audit_2026-08-30.md",
    "docs/review/prepaper_external_artifact_disposition_2026-08-10.md",
    "docs/review/prepaper_scholar_eval_gate_2026-08-10.md",
    "docs/review/prepaper_finalization_commands_2026-08-10.md",
    "docs/review/prepaper_figure_visual_audit_2026-08-10.md",
    "docs/review/prepaper_final_audit_2026-08-10.md",
    "docs/review/prepaper_hardware_validation_2026-08-11.md",
    "docs/review/prepaper_guoq_go_no_go_2026-08-11.md",
    "docs/review/prepaper_guoq_bqskit_pilot_2026-08-11.md",
    "docs/review/heldout_v2_protocol_2026-08-11.md",
    "docs/review/e31_factorial_pareto_protocol_2026-08-11.md",
    "docs/review/metric_catalog_2026-08-11.md",
    "docs/review/metric_audit_ledger_2026-08-11.csv",
    "docs/review/metric_audit_resolution_2026-08-11.md",
    "docs/manuscript/claim_evidence_table.csv",
    "docs/theory/prepaper_theory_gate_2026-08-10.md",
    "docs/theory/formal_results.md",
    "docs/theory/proof_audit_2026-08-06.md",
    "docs/theory/framework.md",
    "docs/theory/universal_law_assessment.md",
    "docs/theory/QMA_hardness_draft.md",
    "docs/results/analysis_summary.md",
)


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(path: Path) -> dict[str, object]:
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    entry: dict[str, object] = {
        "file": relative, "bytes": path.stat().st_size, "sha256": _hash(path),
    }
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
        entry.update({"rows": len(frame), "columns": list(frame.columns)})
    elif path.suffix.lower() == ".json":
        json.loads(path.read_text(encoding="utf-8"))
    return entry


def _iter_unexcluded_files():
    """Walk without descending into artifacts, environments, or invalid runs."""
    for current, directories, filenames in os.walk(EVIDENCE_ROOT):
        directories[:] = sorted(name for name in directories if name not in EXCLUDED_PARTS)
        base = Path(current)
        for filename in sorted(filenames):
            yield base / filename


def _evidence_files() -> list[Path]:
    return sorted(
        path for path in _iter_unexcluded_files()
        if path.suffix.lower() in INCLUDED_SUFFIXES
        and path.relative_to(EVIDENCE_ROOT).as_posix() not in SUPERSEDED_EVIDENCE
    )


def _validate_gate() -> dict[str, list[str]]:
    duplicates = sorted({name for name in SOURCE_FILES if SOURCE_FILES.count(name) > 1})
    if duplicates:
        raise RuntimeError(f"duplicate source files: {duplicates}")
    matches: dict[str, list[str]] = {}
    missing = []
    for label, pattern in REQUIRED.items():
        found = sorted(path.relative_to(PROJECT_ROOT).as_posix()
                       for path in EVIDENCE_ROOT.glob(pattern) if path.is_file())
        matches[label] = found
        if not found:
            missing.append(f"{label}: {pattern}")
    checkpoints = sorted(path.relative_to(PROJECT_ROOT).as_posix()
                         for path in _iter_unexcluded_files()
                         if path.name.endswith("_checkpoint.csv"))
    if missing or checkpoints:
        message = []
        if missing:
            message.append("missing required final evidence:\n- " + "\n- ".join(missing))
        if checkpoints:
            message.append("unfinished checkpoints:\n- " + "\n- ".join(checkpoints))
        raise RuntimeError("\n".join(message))
    missing_project_evidence = [
        name for name in PROJECT_EVIDENCE_FILES if not (PROJECT_ROOT / name).is_file()
    ]
    if missing_project_evidence:
        raise RuntimeError(
            "missing E31 formal release evidence:\n- " + "\n- ".join(missing_project_evidence)
        )
    # File presence is insufficient for heldout-v2: archived pre-fix outputs
    # can look complete. Reuse the semantic, hash-bound formal prerequisite gate.
    from scripts.generate_e31_formal_release_gate import validate_heldout
    from scripts.generate_e31_formal_release_gate import validate_guoq
    validate_guoq(EVIDENCE_ROOT / "external_baselines/guoq/bqskit_pilot")
    validate_heldout(EVIDENCE_ROOT / "heldout_v2")
    from scripts.verify_sbom import verify_sbom
    verify_sbom(PROJECT_ROOT / "release/sbom.cdx.json")
    from scripts.audit_e31_first_party_import_closure import verify_audit
    verify_audit(PROJECT_ROOT / "release/e31_first_party_import_closure_audit.json")
    from scripts.audit_direct_dependencies import audit as audit_direct_dependencies
    audit_direct_dependencies(PROJECT_ROOT / "requirements.txt", PROJECT_ROOT)
    from scripts.verify_metric_audit_ledger import verify as verify_metric_ledger
    verify_metric_ledger(
        PROJECT_ROOT / "docs/review/metric_audit_ledger_2026-08-24.csv",
        PROJECT_ROOT / "docs/review/metric_audit_summary_2026-08-24.json",
        PROJECT_ROOT / "docs/review/metric_catalog_2026-08-11.md",
    )
    from scripts.verify_e31_structural_distribution_metrics import verify as verify_structural
    verify_structural()
    from scripts.audit_external_links import extract_links, markdown_files
    link_audit = json.loads((PROJECT_ROOT / "release/external_link_audit.json").read_text(encoding="utf-8"))
    recorded_urls = {record["url"] for record in link_audit.get("records", [])}
    current_urls = set(extract_links(markdown_files()))
    if recorded_urls != current_urls or link_audit.get("status_counts", {}).get("broken", 0):
        raise RuntimeError("external link audit is stale or contains broken links")
    return matches


def _additional_project_evidence_names() -> set[str]:
    """Resolve every nested artifact member and retained invalid preflight."""
    names = set(ADDITIONAL_ARTIFACT_MANIFESTS) | set(ADDITIONAL_RELEASE_EVIDENCE)
    for relative in ADDITIONAL_ARTIFACT_MANIFESTS:
        manifest_path = PROJECT_ROOT / relative
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifacts = payload.get("artifacts", [])
        if len(artifacts) != int(payload.get("artifact_count", -1)):
            raise RuntimeError(f"additional artifact manifest count mismatch: {relative}")
        for artifact in artifacts:
            member = str(artifact.get("path", ""))
            path = PROJECT_ROOT / member
            if not member or not path.is_file():
                raise RuntimeError(f"missing additional artifact member: {member}")
            if int(artifact.get("bytes", -1)) != path.stat().st_size or str(
                artifact.get("sha256", "")
            ) != _hash(path):
                raise RuntimeError(f"drifted additional artifact member: {member}")
            names.add(member)
    for relative in ADDITIONAL_PREFLIGHT_ROOTS:
        root = PROJECT_ROOT / relative
        files = sorted(path for path in root.rglob("*") if path.is_file())
        if not files:
            raise RuntimeError(f"retained preflight root is empty: {relative}")
        names.update(path.relative_to(PROJECT_ROOT).as_posix() for path in files)
    return names


def _assert_global_unique_sections(*sections: list[dict]) -> None:
    paths = [str(entry.get("file", "")) for section in sections for entry in section]
    missing = [path for path in paths if not path]
    duplicates = sorted({path for path in paths if paths.count(path) > 1})
    if missing or duplicates:
        raise RuntimeError(
            f"manifest sections are not a globally unique file closure; "
            f"missing={len(missing)} duplicates={duplicates}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=PROJECT_ROOT / "release" / "prepaper_release_manifest.json")
    parser.add_argument(
        "--capsule-inner",
        action="store_true",
        help="exclude the outer archive, receipt, readiness verdict, and inner manifest itself",
    )
    args = parser.parse_args()
    required_matches = _validate_gate()
    # Some project-level evidence lives below data/v10/prepaper.  Classify it
    # once as project evidence instead of emitting duplicate paths across
    # manifest sections; the fail-closed verifier requires global uniqueness.
    version_qasm_files = sorted(
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (
            PROJECT_ROOT / "data/v11/compiler_version_sensitivity/runs"
        ).glob("*/optimized_qasm/*.qasm")
        if path.is_file()
    )
    semantic_replay_root = (
        PROJECT_ROOT
        / "data/v11/e31_factorial_pareto/formal_run/semantic_replay"
    )
    semantic_replay_closure = sorted(
        path.relative_to(PROJECT_ROOT).as_posix()
        for pattern in ("cells/*.json", "certificates/*.json", "outputs/*.qpy")
        for path in semantic_replay_root.glob(pattern)
        if path.is_file()
    )
    expected_semantic_counts = {
        "cells": 6_858, "certificates": 20_314, "outputs": 6_858,
    }
    observed_semantic_counts = {
        name: len(list((semantic_replay_root / name).glob(pattern)))
        for name, pattern in (
            ("cells", "*.json"),
            ("certificates", "*.json"),
            ("outputs", "*.qpy"),
        )
    }
    if observed_semantic_counts != expected_semantic_counts:
        raise RuntimeError(
            "semantic replay archive closure is incomplete: "
            f"{observed_semantic_counts}"
        )
    additional_names = _additional_project_evidence_names()
    project_evidence_names = (
        set(PROJECT_EVIDENCE_FILES)
        | set(version_qasm_files)
        | set(semantic_replay_closure)
        | (additional_names - set(SOURCE_FILES))
    )
    if args.capsule_inner:
        project_evidence_names -= CAPSULE_OUTER_FILES
    evidence = [
        _entry(path) for path in _evidence_files()
        if path.relative_to(PROJECT_ROOT).as_posix() not in project_evidence_names
    ]
    project_evidence = [
        _entry(PROJECT_ROOT / name) for name in sorted(project_evidence_names)
    ]
    missing_source = [name for name in SOURCE_FILES if not (PROJECT_ROOT / name).is_file()]
    if missing_source:
        raise RuntimeError(f"missing source files: {missing_source}")
    sources = [_entry(PROJECT_ROOT / name) for name in SOURCE_FILES]
    _assert_global_unique_sections(evidence, project_evidence, sources)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_ROOT,
                            capture_output=True, text=True, check=False)
    manifest = {
        "schema_version": "1.0.0-prepaper", "status": "complete",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "pre-paper evidence only; canonical historical release remains separate",
        "required_gate_matches": required_matches,
        "git": {"commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True,
            text=True, check=True).stdout.strip(), "dirty": bool(status.stdout.strip())},
        "evidence": evidence, "project_evidence": project_evidence,
        "source_files": sources,
        "counts": {"evidence_files": len(evidence),
                   "project_evidence_files": len(project_evidence),
                   "source_files": len(sources)},
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(output)
    print(f"Pre-paper release manifest: {len(evidence)} evidence files -> {output}")


if __name__ == "__main__":
    main()
