"""Merge the three independently reviewed metric fragments into registry v2."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs/review/metric_catalog_2026-08-11.md"
OUTPUT = ROOT / "docs/review/metric_evidence_registry_2026-08-26.json"
FRAGMENTS = ROOT / "docs/review/metric_registry_fragments"

# These entries were marked PASS by field/column existence alone even though the
# cited selector does not directly establish the complete catalog question.
# Fail closed to PARTIAL until an item-specific semantic predicate is registered.
CONSERVATIVE_DOWNGRADES = {
    "7.09", "7.10", "7.23", "7.24", "7.26",
    "8.02", "8.03", "8.05", "8.07", "8.08", "8.10", "8.13", "8.14",
    "8.17", "8.18", "8.27", "8.30", "8.31", "8.32", "8.33",
    "9.21", "10.15", "10.30", "11.09", "11.15", "11.25", "11.26",
    "11.35", "11.46", "11.49", "12.08", "12.32",
}

DIRECT_STATUS_OVERLAYS = {
    "4.04": (
        "release/circuit_semantics_scope_audit.json",
        "PASS_EXPLICIT_FAIL_CLOSED_CIRCUIT_SEMANTICS_SCOPE",
        "Declared ancillas are supported within the fixed-width unitary contract; measurement, reset, classical control, and dynamic flow are explicitly rejected fail-closed.",
    ),
    "5.31": (
        "data/v11/e31_factorial_pareto/dual_estimand_power.json",
        "PROSPECTIVE_DUAL_ESTIMAND_SIMULATION",
        "The frozen 391-input primary was prospectively gated at 1 pp MCID and 80% target power; fixed-panel execution passed while unseen-family inference remained blocked.",
    ),
    "5.11": (
        "data/v11/e31_factorial_pareto/input_duplicate_isomorphism_audit.json",
        "PASS_NO_RESIDUAL_EXACT_OR_GLOBAL_QUBIT_RELABEL_DUPLICATES",
        "The 520-row source had 129 repeated logical inputs, all collapsed before E31; the frozen 391-input panel has no residual exact-hash or declared global-qubit-relabel duplicates.",
    ),
    "5.26": (
        "release/rewrite_property_sweep_audit.json",
        "PASS_ALL_GENERATIVE_PROPERTIES",
        "The robustness panel contains 40 unique bound-unitary circuits forcing angles immediately below/above zero, pi, and 2pi across six rule/window configurations; this is boundary stress coverage, not a claim about every singular parameterization.",
    ),
    "6.20": (
        "release/circuit_semantics_scope_audit.json",
        "PASS_EXPLICIT_FAIL_CLOSED_CIRCUIT_SEMANTICS_SCOPE",
        "Barrier is treated as a unitary semantic no-op; measurement and reset return unavailable with explicit blockers.",
    ),
    "4.16": (
        "release/rewrite_order_confluence_audit.json", "PASS_AUDIT_COMPLETE",
        "Bounded rule-order/confluence audit completed with zero semantic, cost, or convergence failures.",
    ),
    "6.22": (
        "release/rewrite_property_sweep_audit.json", "PASS_ALL_GENERATIVE_PROPERTIES",
        "Paired generative property sweep passed 240 rule/window configuration cells.",
    ),
    "6.24": (
        "release/semantic_mutation_sentinel_audit.json", "PASS_ALL_TARGETED_MUTANTS_KILLED",
        "Targeted mutation audit killed every mutant while all equivalent controls passed.",
    ),
    "7.06": (
        "release/circuit_semantics_scope_audit.json",
        "PASS_EXPLICIT_FAIL_CLOSED_CIRCUIT_SEMANTICS_SCOPE",
        "Free-parameter circuits are neither symbolically certified nor checked at finitely chosen points; they fail closed until fully bound.",
    ),
    "7.13": (
        "release/circuit_semantics_scope_audit.json",
        "PASS_EXPLICIT_FAIL_CLOSED_CIRCUIT_SEMANTICS_SCOPE",
        "Large non-Clifford fallback uses normalized complex-Gaussian global Haar draws with full distributional support, while finite coverage remains explicitly probabilistic.",
    ),
    "7.19": (
        "release/qubit_permutation_metamorphic_audit.json",
        "PASS_ALL_QUBIT_PERMUTATION_METAMORPHIC_CHECKS",
        "Forty seeded nonidentity global qubit permutations preserved all 160 equivalent/control decisions.",
    ),
    "9.17": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/basis_weight_sensitivity.json",
        "PASS_E31_COMMON_BASIS_AND_GATE_WEIGHT_SENSITIVITY_COMPLETE",
        "Exact optimization-level-0 translation overhead is reported for all 391 inputs under three universal logical basis schemes, with representation and no-hardware limits explicit.",
    ),
    "9.51": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/validity_runtime_frontier/frontier_audit.json",
        "PASS_E31_VALIDITY_RUNTIME_FRONTIER_AND_BUDGET_AUC_COMPLETE",
        "A log-budget-normalized four-point AUC is reported for validity and ITT reduction; it is explicitly a frozen independent-budget response proxy, not a within-run incumbent trajectory.",
    ),
    "10.26": (
        "data/v10/prepaper/e03/e03_scaling_model_audit.json",
        "PASS_BOUNDED_SCALING_MODEL_CI_AND_EXTRAPOLATION_AUDIT",
        "Paired-trial bootstrap confidence intervals are reported for observed size means, all fitted curves, coefficients, and held-out n=10 mean predictions.",
    ),
    "10.20": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/runtime_outcome_audit.json",
        "PASS_E31_BUDGET_EXHAUSTED_VALID_RATE_MEASURED",
        "The sealed retained-artifact rate is 0/7,838 timeouts; this does not establish whether an uncheckpointed valid incumbent existed before forced termination.",
    ),
    "10.27": (
        "data/v10/prepaper/e03/e03_scaling_model_audit.json",
        "PASS_BOUNDED_SCALING_MODEL_CI_AND_EXTRAPOLATION_AUDIT",
        "Quadratic-polynomial, exponential, and continuous piecewise-hinge scaling models are compared by AICc and leave-one-size-out RMSE; the two selectors disagree.",
    ),
    "10.28": (
        "data/v10/prepaper/e03/e03_scaling_model_audit.json",
        "PASS_BOUNDED_SCALING_MODEL_CI_AND_EXTRAPOLATION_AUDIT",
        "Each model is trained on n=3..9 and evaluated out of range on the held-out n=10 mean; all show material extrapolation fragility.",
    ),
    "10.32": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/validity_runtime_frontier/frontier_audit.json",
        "PASS_E31_VALIDITY_RUNTIME_FRONTIER_AND_BUDGET_AUC_COMPLETE",
        "A verified PNG/PDF frontier plots valid-output rate and ITT reduction against measured mean end-to-end wall time for all four frozen budgets with input-cluster intervals.",
    ),
    "11.29": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/specification_influence/specification_influence_audit.json",
        "PASS_E31_SPECIFICATION_CURVE_AND_FAMILY_INFLUENCE_COMPLETE",
        "A 32-specification post-seal multiverse varies budget inclusion, window inclusion, and fixed-input versus equal-family weighting, with a rendered specification curve and explicit non-confirmatory status.",
    ),
    "11.42": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/specification_influence/specification_influence_audit.json",
        "PASS_E31_SPECIFICATION_CURVE_AND_FAMILY_INFLUENCE_COMPLETE",
        "All 15 leave-one-family-out influence checks are reported; Oracle has the largest absolute shift (0.158 pp) and no omission changes the descriptive sign.",
    ),
    "11.48": (
        "data/v10/prepaper/heldout/analysis/calibration_null/calibration_null_audit.json",
        "PASS_HELDOUT_CALIBRATION_NULL_BASELINE_AND_LABEL_PERMUTATION_COMPLETE",
        "The untouched sealed model now has a 10-bin reliability diagram, ECE, Brier/log loss, and logistic calibration intercept/slope with 95% intervals; the intercept excludes zero, showing material underprediction rather than merely good discrimination.",
    ),
    "12.20": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/fidelity_threshold_sensitivity.json",
        "PASS_E31_FIDELITY_THRESHOLD_SENSITIVITY_COMPLETE",
        "All 6,858 sealed successful semantic cells remain accepted through the frozen 0.9999999999 threshold; stricter near-one numerical sensitivity is reported without redefining the protocol.",
    ),
    "12.22": (
        "release/equivalence_verifier_agreement_audit.json",
        "PASS_ZERO_DISAGREEMENTS",
        "A bounded verifier-path sensitivity audit found zero decision disagreements across the project certificate, Qiskit Operator.equiv, and trace-fidelity calculation; these paths share Qiskit semantics and are not independent implementations.",
    ),
    "12.23": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/basis_weight_sensitivity.json",
        "PASS_E31_COMMON_BASIS_AND_GATE_WEIGHT_SENSITIVITY_COMPLETE",
        "All sealed rows were recomputed under rz/sx/x/cx, u/cx, and rz/sx/x/cz logical bases; the descriptive primary-contrast sign is stable, while every family-t14 interval includes zero.",
    ),
    "12.24": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/basis_weight_sensitivity.json",
        "PASS_E31_COMMON_BASIS_AND_GATE_WEIGHT_SENSITIVITY_COMPLETE",
        "The post-seal sensitivity changes two-qubit weight from 1 to 10 and separately treats RZ as virtual zero-cost.",
    ),
    "12.25": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/basis_weight_sensitivity.json",
        "PASS_E31_COMMON_BASIS_AND_GATE_WEIGHT_SENSITIVITY_COMPLETE",
        "Weighted-cost reductions and fixed-panel/equal-family primary contrasts are reported alongside equal-weight gate count for all 28,152 rows.",
    ),
    "12.29": (
        "data/v10/prepaper/heldout/analysis/calibration_null/calibration_null_audit.json",
        "PASS_HELDOUT_CALIBRATION_NULL_BASELINE_AND_LABEL_PERMUTATION_COMPLETE",
        "The sealed classifier is compared with a constant-prevalence probability and majority-class no-information baseline on all 186 unique held-out inputs.",
    ),
    "12.30": (
        "data/v10/prepaper/heldout/analysis/calibration_null/calibration_null_audit.json",
        "PASS_HELDOUT_CALIBRATION_NULL_BASELINE_AND_LABEL_PERMUTATION_COMPLETE",
        "Because outcomes are constant within each of eight families, the audit rejects a degenerate within-family shuffle and exactly enumerates all 56 whole-family label allocations; AUROC/Brier p=1/56 while MCC p=10/56.",
    ),
}

# Metric-specific outcomes carried by a shared scope audit.  Unlike the legacy
# direct-status overlay, these selectors bind each catalog item to its own
# explicit disposition rather than inferring several questions from one file
# status.  ``NA`` is reserved for frozen-scope inapplicability, not missing work.
DIRECT_DISPOSITION_OVERLAYS = {
    "15.42": (
        "release/external_link_audit.json",
        "PARTIAL: live audit found 0 definite broken links among 60 unique URLs, but 5 URLs remain unverified and future link rot cannot be excluded",
        "PARTIAL",
        "A point-in-time strict live audit finds no definite 404/410 among 60 URLs; five HTTP-403 destinations and three templates remain outside positive verification, and future persistence is not guaranteed.",
    ),
    "18.03": (
        "data/v10/prepaper/heldout_v2/analysis/combined_heldout_metrics.json",
        "PASS: the sealed v1+v2 held-out program contains 16 independent generator families and 378 globally unique inputs, with no model refit or feature/threshold change",
        "PASS",
        "The expansion doubles the outer generator mechanisms from eight to sixteen under the frozen classifier and preserves a family-clustered inferential boundary; it is not evidence of universality to every unseen family.",
    ),
    "7.25": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/pyzx_large_semantic/pyzx_large_semantic_audit.json",
        "PASS: PyZX full-reduce proves equality for all 27 selected sealed E31 cells at widths 9-10, while one X-mutant per family is not proved equal",
        "PASS",
        "A bounded largest-width panel uses PyZX full-reduce identity reduction on one selected successful cell per input; all 27 prove equal and three family-level X mutants are not proved equal. Ten large QuantumWalk inputs lack successful sealed cells and remain explicitly unverified.",
    ),
    "13.10": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/class_gateset/class_gateset_generalization_audit.json",
        "PASS: all four manuscript-defined algorithm classes are left out in turn and every training row receives one cross-fitted diagnostic prediction",
        "PASS",
        "Random, algorithmic, variational, and error-correcting classes are each omitted from fitting in turn; this is post-seal training-packet cross-fitting, not an untouched external test.",
    ),
    "13.11": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/class_gateset/class_gateset_generalization_audit.json",
        "PASS: all 18 observed exact gate-set signatures are left out in turn and every training row receives one cross-fitted diagnostic prediction",
        "PASS",
        "All 18 exact gate-name vocabularies recorded in the training packet are omitted in turn; small/single-outcome folds and the exact-signature definition are disclosed.",
    ),
    "7.22": (
        "release/transformation_failure_localization_audit.json",
        "PARTIAL: five Phase-2b transformation stages have semantic checkpoints that localize injected failures to iteration and stage, but the sealed E31 trace contains aggregate counters rather than one checkpoint per individual rewrite",
        "PARTIAL",
        "Five targeted stage sentinels localize the first semantic failure to an iteration/stage identifier; sealed E31 traces remain aggregate within a stage, so gate-level retrospective localization is unavailable.",
    ),
    "11.32": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/mixed_model_diagnostics/mixed_model_diagnostics.json",
        "PASS: the declared supportive mixed model converged under REML/L-BFGS without an optimizer warning",
        "PASS",
        "The supportive 1,564-observation family random-slope model converged in 12 L-BFGS iterations with warnflag zero; its inferential role remains secondary to family-t14 and wild-cluster procedures.",
    ),
    "11.33": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/mixed_model_diagnostics/mixed_model_diagnostics.json",
        "PARTIAL: convergence is achieved, but the observed Hessian is indefinite and the family random intercept/slope covariance is near singular",
        "PARTIAL",
        "Gradient and covariance diagnostics are reported, but the indefinite Hessian and 0.996 intercept-slope correlation prevent treating the random-effect geometry as routine.",
    ),
    "11.40": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/mixed_model_diagnostics/mixed_model_diagnostics.json",
        "PASS: a family-level random slope for WCL versus LBL is estimated jointly with the family intercept and input variance component",
        "PASS",
        "The supportive model explicitly estimates a family-level WCL random slope and intercept covariance, plus an input variance component; near-singular geometry is disclosed separately.",
    ),
    "12.26": (
        "data/v9/e12/version_stack_reconciliation/version_stack_reconciliation_audit.json",
        "PARTIAL: 560 shared E12 circuit-by-optimization-level keys reproduce scientific outputs across Python/numerical-stack changes, but Qiskit stayed at 2.4.1, eight rows were deferred, runtime changed, and central E31 analyses were not replayed",
        "PARTIAL",
        "Corrected E12 reconciliation uses all 560 shared circuit-by-optimization-level keys and separates volatile runtime; it covers Python/numerical-stack drift only, not tool-version or central E31 conclusion sensitivity.",
    ),
    "8.28": (
        "data/v11/compiler_version_sensitivity/compiler_version_sensitivity_audit.json",
        "PARTIAL: Qiskit, Cirq, and tket each have a two-version frozen 15-family structural panel, but the panel is not the full formal benchmark and external Quasar/Quartz versions are not varied",
        "PARTIAL",
        "A frozen 15-family panel directly compares Qiskit 2.3.1/2.4.1, Cirq 1.6.0/1.6.1, and pytket 2.17.0/2.18.0 in isolated environments; all 90 compiler outputs are valid and structurally identical within tool, while external tools and the full benchmark remain untested across versions.",
    ),
    "18.10": (
        "data/v11/compiler_version_sensitivity/compiler_version_sensitivity_audit.json",
        "PARTIAL: three compiler stacks have two-version evidence on one Windows host, but no Linux or different-CPU execution exists",
        "PARTIAL",
        "Three compiler stacks now have bounded two-version evidence on one frozen 15-family panel, but every execution used the same Windows host and CPU, so the explicit platform-robustness requirement remains open.",
    ),
    "3.18": (
        "release/comparator_version_publication_audit.json",
        "PARTIAL: latest arXiv and formal versions were directly compared for Quartz and GUOQ, but the full manuscript bibliography has not received corpus-wide pairwise version reconciliation",
        "PARTIAL",
        "The two closest executable comparators now have direct arXiv-to-publication reconciliation, including appendix-only material and current-version history; the remaining bibliography still requires a corpus-wide pair audit.",
    ),
    "3.27": (
        "release/contribution_independence_audit.json",
        "PASS: the increment is a standalone empirical research package rather than a single ablation, combining a completed 28,152-row factorial program, independent 16-family held-out validation, and two formal external artifacts",
        "PASS",
        "The evidence supports a standalone empirical methods contribution, while priority, venue acceptance, unseen-family universality, and confirmatory status for post-hoc analyses remain explicitly outside the claim.",
    ),
    "3.13": (
        "release/novelty_counterexample_audit.json",
        "PARTIAL: targeted primary-source searches found close representation, local-optimality, and scalability collisions but no identical minimal counterexample; absence cannot be established exhaustively",
        "PARTIAL",
        "The documented comparator search now answers the item directly without converting failure to find an identical example into proof of absence; broader representation-dependence remains established prior art.",
    ),
    "16.13": (
        "release/compiler_integration_audit.json",
        "PARTIAL: Q-research optimizers now integrate directly as a fail-closed Qiskit TransformationPass, but native Cirq and tket pass adapters are not implemented",
        "PARTIAL",
        "A direct Qiskit PassManager adapter independently certifies returned circuits and rejects a lying invalid-output sentinel; integration remains limited to Qiskit rather than multiple compiler frameworks.",
    ),
    "16.17": (
        "data/v10/prepaper/analysis/hardware_routing_overhead/hardware_routing_overhead_audit.json",
        "PARTIAL: commutation_phase2 and hybrid_phase1_2 each reduce mapped native two-qubit gates in 4 of 12 paired fake-backend cells (maximum 2 gates) with no paired increases, but no real-QPU duration reduction is measured",
        "PARTIAL",
        "Paired replay on two frozen fake-backend snapshots directly shows bounded mapped native-2Q reductions for two optimizer variants; this is compiler evidence, not measured physical duration on a real QPU.",
    ),
    "12.14": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/fragility_listing/fragility_listing_audit.json",
        "PASS: post-seal oracle-best, oracle-worst, and frozen random listings are compared for every complete design cell",
        "PASS",
        "All 9,384 complete input/rule/budget/window cells compare post-seal oracle-best, oracle-worst, and the frozen random-topological listing; oracle envelopes are diagnostic and not deployable selectors.",
    ),
    "17.03": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/fragility_listing/fragility_listing_audit.json",
        "PASS: five declared core descriptive conclusions receive exhaustive leave-one-input-out influence analysis",
        "PASS",
        "Every one of 391 frozen inputs is omitted in turn for five declared descriptive contrasts, with the most sensitive conclusion/input and maximum shift reported and zero sign flips.",
    ),
    "17.07": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/fragility_listing/fragility_listing_audit.json",
        "PARTIAL: every single recorded-timeout deletion is bounded, but no retained incumbent exists to bound hidden timeout outcomes",
        "PARTIAL",
        "Single-record deletion of all 7,838 timeout rows is bounded with no sign flip, but absent retained incumbents prevent sensitivity bounds for unobserved pre-termination outcomes.",
    ),
    "17.08": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/fragility_listing/fragility_listing_audit.json",
        "PASS: all five declared conclusions are recomputed at each equal budget and none reverses sign",
        "PASS",
        "Five declared ITT contrasts are recomputed separately at 1, 10, 30, and 120 seconds; none reverses relative to the all-budget estimate, while the all-timeout one-second tie is explicitly not evidence of equality.",
    ),
    "7.15": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/native_semantic_verifier/native_semantic_verifier.json",
        "PASS: all 6,858 successful E31 semantic cells were independently replayed with native gate matrices and tensor application; widths above six qubits use deterministic finite probes and are therefore probabilistic rather than exact",
        "PASS",
        "The second verifier binds every QPY byte hash, recomputes input/output logical hashes, uses exhaustive basis-state checks through six qubits, and deterministic finite probes above six qubits. Qiskit remains the parser, and this is not external replication or a symbolic proof for every large-width cell.",
    ),
    "9.14": (
        "data/v10/prepaper/analysis/hardware_routing_overhead/hardware_routing_overhead_audit.json",
        "PASS: identity-layout nonlocal two-qubit operation count and excess edge-hop count are directly reported for all 48 bounded design cells",
        "PASS",
        "All 48 frozen fake-backend design cells report logical two-qubit operands at graph distance greater than one and their excess edge hops; 32 cells contain nonlocal operations, with counts from zero to nine.",
    ),
    "9.16": (
        "data/v10/prepaper/analysis/hardware_routing_overhead/hardware_routing_overhead_audit.json",
        "PASS: paired topology-constrained versus all-to-all native two-qubit gate and depth overhead are directly reported for all 48 bounded design cells",
        "PASS",
        "All 48 cells compare the frozen SABRE-routed result against an all-to-all counterfactual with the same native basis, optimization level, and seed; level-0 native two-qubit overhead ranges from zero to nine gates.",
    ),
    "9.08": (
        "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
        "PASS: scheduled critical-path duration is directly reported for every bounded hardware design cell",
        "PASS",
        "Scheduled critical-path duration is finite for all 48 fake-backend design cells; scope is three circuits and two archived calibration snapshots.",
    ),
    "9.18": (
        "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
        "PASS: peak live qubits equals declared width under the verified fixed-width unitary contract",
        "PASS",
        "For all 6,858 E31 semantic cells, fixed-width unitary input/output semantics make peak stored live qubits equal declared width (4 to 10), including identity wires.",
    ),
    "9.19": (
        "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
        "NA: the evaluated circuits contain no measurement or classical feed-forward",
        "NA",
        "Not applicable to the frozen fixed-width unitary benchmark: all 6,858 semantic cells have zero measurements and resets and no classical feed-forward.",
    ),
    "9.20": (
        "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
        "NA: the evaluated circuits contain no dynamic branches",
        "NA",
        "Not applicable to the frozen fixed-width unitary benchmark; dynamic control is rejected by the semantic contract rather than assigned zero branch cost.",
    ),
    "9.22": (
        "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
        "PASS: dependency-preserving T/TDG depth reconstructed for all 1,080 native Clifford+T rows",
        "PASS",
        "All 1,080 rows from 360 native Clifford+T inputs were hash-reconstructed and assigned dependency-preserving emitted-circuit T/TDG depth; this is not globally minimized fault-tolerant T-depth.",
    ),
    "14.03": (
        "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
        "PASS: one identical initial-layout policy is enforced across compared versions",
        "PASS",
        "All bounded hardware comparisons use the same trivial identity initial-layout policy on logical width.",
    ),
    "14.07": (
        "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
        "PASS: native two-qubit gate count is reported",
        "PASS",
        "Native two-qubit gate counts are finite and reported for all 48 fake-backend design cells (range 3 to 29).",
    ),
    "14.08": (
        "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
        "PASS: native two-qubit depth is reported",
        "PASS",
        "Native two-qubit depth is finite and reported for all 48 fake-backend design cells (range 3 to 29).",
    ),
    "14.09": (
        "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
        "PASS: scheduled duration is reported",
        "PASS",
        "Scheduled duration is finite and reported for all bounded fake-backend design cells.",
    ),
    "14.12": (
        "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
        "PASS: fixed-snapshot product-of-gate-success proxy is reported with limitations",
        "PASS",
        "A bounded product-of-reported-gate-success proxy is reported for two fixed calibration snapshots; it is not hardware-output fidelity.",
    ),
    "14.13": (
        "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
        "PASS: bounded noise-aware cost 1-p_success is defined and finite",
        "PASS",
        "The bounded snapshot analysis defines noise-aware cost as one minus the reported calibration-success proxy and records its claim boundary.",
    ),
    "14.32": (
        "data/v10/prepaper/analysis/cost_vector_scope/cost_vector_scope_audit.json",
        "NA: dynamic circuits are outside the frozen unitary benchmark scope",
        "NA",
        "Dynamic circuits are explicitly outside the frozen unitary benchmark and fail closed in semantic validation.",
    ),
    "13.01": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: 15 training and 16 held-out generator families are disjoint, with zero input-hash overlap",
        "PASS",
        "The sealed training packet and combined held-out packet have disjoint generator names and zero input-circuit-hash overlap.",
    ),
    "13.02": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: the sealed model, 12 features, imputation, scaling, and 0.5 threshold replay all 378 probabilities without refit",
        "PASS",
        "All 378 sealed probabilities replay to 1.12e-16 maximum absolute error with the archived features, imputer, scaler, coefficients, intercept, and threshold.",
    ),
    "13.03": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PARTIAL: 16 outer families improve evidence but the clustered MCC 95% interval remains wide at 0.598081",
        "PARTIAL",
        "The combined 16-family clustered MCC interval is [0.361, 0.959] (width 0.598), so the held-out quantity is not yet sufficient for a narrow interval.",
    ),
    "13.04": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PARTIAL: training-derived OOD classification identifies 0 near and 16 far held-out families, so both regimes are not represented",
        "PARTIAL",
        "All 16 held-out families are far under the training-only OOD threshold; the experiment does not jointly cover near- and far-shift regimes.",
    ),
    "13.05": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: nearest-training, shrinkage-Mahalanobis, and training-range excursion distances are reported per input and family",
        "PASS",
        "Domain distance is reported at instance and family levels using three complementary training-bound diagnostics.",
    ),
    "13.06": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: outcomes, probabilities, calibration, distance, prediction intervals, and failure flags are reported for every held-out family",
        "PASS",
        "A complete 16-family table reports outcomes, probabilities, calibration, domain distance, conditional prediction intervals, and failure flags.",
    ),
    "13.07": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: family-level observed rate, mean predicted probability, calibration error, and Brier score are reported",
        "PASS",
        "Family-level calibration is reported for every unseen generator; mean absolute family calibration error is 0.171.",
    ),
    "13.08": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: complete family-level classification failures are explicitly counted (1)",
        "PASS",
        "The audit identifies and retains one held-out family with zero classification accuracy.",
    ),
    "13.09": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: diagnostic leave-one-generator-out refits cover all 15 training generators; this is separate from the sealed held-out test",
        "PASS",
        "All 15 training generators receive a diagnostic leave-one-generator-out refit and evaluation; these folds are not substituted for the sealed test.",
    ),
    "13.12": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "FAIL: held-out qubits span 4 to 8 inside the training range 4 to 10, so no out-of-range qubit extrapolation was tested",
        "FAIL",
        "No cross-qubit-range extrapolation is present: training spans 4-10 qubits and held-out spans only 4-8.",
    ),
    "13.18": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: the audit explicitly limits all 16 held-out generators to synthetic-distribution evidence, not real-world representativeness",
        "PASS",
        "The generalization claim is explicitly limited to unseen synthetic generators and does not claim real-world distribution representativeness.",
    ),
    "15.41": (
        "release/prepaper_archive_restore_audit.json",
        "PASS: a layered release capsule was unpacked into a temporary directory, its inner manifest and complete hash closure were validated, and the restored release verifier passed under isolated Python mode",
        "PASS",
        "The frozen layered capsule (34,685 pinned payload files plus its inner manifest) was restored into a fresh temporary directory, every member was byte/hash re-validated against the inner manifest closure, and the restored release verifier passed under isolated Python mode, including the full 592-row metric ledger re-verification; the receipt is stored outside the ZIP and pins the finished archive hash, avoiding any self-hash cycle. Claim boundary: this proves byte-complete restoration and executable verification of one frozen local release capsule on the current Windows/Python dependency stack, not off-site durability, media longevity, cross-OS disaster recovery, or future dependency availability.",
    ),
    "13.14": (
        "release/prepaper_retrospective_binding_audit.json",
        "PARTIAL: the frozen 7-environment, 15-family, 105-row panel shows all version pairs structurally identical and numerically exact-equivalent (Qiskit 2.3.1/2.4.1, Cirq 1.6.0/1.6.1, pytket 2.17.0/2.18.0), with an independent 105/105 QASM semantic replay, but this is not a full benchmark rerun, not cross-platform, and external tool versions are not varied",
        "PARTIAL",
        "Cross-compiler-version evidence exists and is independently replayed, but it is a bounded 15-family, 4-5-qubit, single-platform panel; it does not establish broad cross-version generalization.",
    ),
    "16.23": (
        "release/prepaper_retrospective_binding_audit.json",
        "PARTIAL: mechanism conclusions are version-stable across the exact tested compiler version pairs on the frozen 15-family panel, but the evidence covers only those versions on one Windows host; custom-current has a single version and future or external versions remain untested",
        "PARTIAL",
        "Mechanism conclusions are stable across the exact tested tool versions, but only those versions on one host are covered; future or external version updates remain untested.",
    ),
    "3.12": (
        "release/prepaper_retrospective_binding_audit.json",
        "PASS: the sealed E31 full factorial is itself a direct listing/order sensitivity experiment; listing_model (LBL/WCL/RANDOM_TOPOLOGICAL) is a first-class factor in all 28,152 rows, with sealed coefficient and post-hoc marginal-contrast tables plus an exhaustive listing fragility audit",
        "PASS",
        "A direct listing/order sensitivity experiment exists: the sealed E31 full factorial varies listing_model as a first-class factor across all 28,152 rows, with sealed coefficient, marginal-contrast, and listing-fragility analyses.",
    ),
    "16.16": (
        "release/prepaper_retrospective_binding_audit.json",
        "PARTIAL: bounded fake-backend routing-overhead evidence shows mapped native two-qubit reductions for two optimizer variants in paired cells, but no real-QPU hardware-aware objective, duration, or calibration is measured",
        "PARTIAL",
        "Bounded fake-backend routing evidence partially answers hardware-aware extension, but no real-QPU hardware-aware objective is measured.",
    ),
    "13.19": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: covariate shift is quantified from training-only feature geometry at instance and family levels",
        "PASS",
        "Covariate shift is quantified from sealed standardized training-feature geometry without held-out threshold tuning.",
    ),
    "13.20": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: conditional Poisson-binomial 95% family outcome-count prediction intervals are reported alongside the clustered MCC confidence interval",
        "PASS",
        "Each family has a conditional 95% Poisson-binomial predicted outcome-count interval; model-parameter uncertainty remains explicitly excluded.",
    ),
    "13.21": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: frozen full-model performance is compared against gate-count-only and size-only refits; unseen family identity is unavailable as a predictor",
        "PASS",
        "The frozen 12-feature model materially outperforms gate-count-only and size-only diagnostics on the untouched combined held-out packet.",
    ),
    "13.22": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: shortcut risk is audited with gate-count-only, size-only, range-excursion, OOD, and feature-ablation diagnostics",
        "PASS",
        "Shortcut risk is directly checked with size-only baselines, feature ablations, training-range excursions, and OOD distance.",
    ),
    "13.23": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: all 12 leave-one-feature-out diagnostic refits are evaluated on the untouched combined held-out packet",
        "PASS",
        "Twelve leave-one-feature-out diagnostic refits plus full and size-only baselines are reported without changing the sealed primary predictions.",
    ),
    "13.24": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PASS: OOD scores and a training leave-one-out 95th-percentile threshold are reported without held-out threshold tuning",
        "PASS",
        "Nearest-training and shrinkage-Mahalanobis OOD scores are reported; the threshold is derived solely from training leave-one-out distances.",
    ),
    "13.25": (
        "data/v10/prepaper/heldout_v2/analysis/generalization_ood/generalization_ood_audit.json",
        "PARTIAL: a training-only abstention rule is implemented, but it rejects all 378 held-out inputs and has zero useful selective coverage",
        "PARTIAL",
        "OOD abstention is implemented and auditable, but the training-only rule rejects 378/378 held-out inputs and is not operationally useful.",
    ),
    "10.02": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_audit.json",
        "PASS: process CPU time is directly measured for every bounded resource-profile cell",
        "PASS",
        "Process CPU time is directly measured for a 36-cell, 15-family diagnostic panel spanning 4-10 qubits.",
    ),
    "10.05": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_audit.json",
        "PASS: process disk read and write bytes are directly measured for every bounded profile cell",
        "PASS",
        "Per-process disk read and write byte deltas are directly recorded for every bounded profile cell.",
    ),
    "10.06": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_audit.json",
        "PARTIAL: managed per-cell profiling-directory storage is measured, but operating-system temporary storage is not captured",
        "PARTIAL",
        "Managed per-cell directory storage is reported, but untracked operating-system and library temporary storage remains outside measurement.",
    ),
    "10.09": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_audit.json",
        "PASS: cold-process import initialization wall and CPU time are directly measured",
        "PASS",
        "Cold-process Python/Qiskit/project import initialization wall and CPU time are directly measured on the diagnostic panel.",
    ),
    "10.10": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_audit.json",
        "PASS: payload and QASM parsing wall and CPU time are directly measured",
        "PASS",
        "Payload JSON and QASM parsing are separately timed in wall and CPU seconds for every diagnostic cell.",
    ),
    "10.11": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_audit.json",
        "PASS: common-basis conversion wall and CPU time are directly measured",
        "PASS",
        "Optimization-level-0 common-basis conversion of input and output is separately timed for every diagnostic cell.",
    ),
    "10.13": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_audit.json",
        "PASS: exact semantic verification wall and CPU time are directly measured",
        "PASS",
        "Exact average-gate-fidelity verification wall and CPU time are separately measured for all semantically valid diagnostic cells.",
    ),
    "10.14": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_audit.json",
        "PASS: substantive result JSON serialization time and byte size are directly probed",
        "PASS",
        "Substantive result JSON encoding time, CPU time, and byte size are directly probed before atomic result write.",
    ),
    "10.24": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_audit.json",
        "PASS: a 4-10 qubit diagnostic peak-RSS scaling exponent with bootstrap interval is reported",
        "PASS",
        "Seven 4-10 qubit scale points yield a diagnostic log-log peak-RSS exponent with a bootstrap interval; interpreter overhead is explicit.",
    ),
    "10.33": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_audit.json",
        "PASS: identical tasks are compared at 1, 2, and 4 workers with deterministic output-hash agreement",
        "PASS",
        "The same eight tasks are profiled at 1, 2, and 4 workers; throughput and RSS are reported and output hash sets agree.",
    ),
    "10.34": (
        "data/v11/e31_factorial_pareto/formal_run/analysis/resource_profile/resource_profile_audit.json",
        "PARTIAL: first versus repeated same-process execution is measured, but operating-system caches are not forcibly flushed",
        "PARTIAL",
        "Five same-process repeats quantify warm-state sensitivity, but the Windows operating-system cache was not forcibly flushed, so a true cold-cache experiment remains.",
    ),
}

DIRECT_REF_OVERLAYS = {
    "4.20": ({
        "path": "release/rewrite_order_confluence_audit.json",
        "selector": {"type": "json_pointer_equals", "pointer": "/structural_cycle_count",
                     "expected": 0},
        "predicate": "sha256_and_json_pointer_equals",
    }, "Bounded multi-order rewrite audit found zero convergence failures or structural cycles."),
    "7.16": ({
        "path": "release/e31_independent_release_verification_receipt.json",
        "selector": {"type": "json_pointer_equals", "pointer": "/semantic_identity_check",
                     "expected": (
                         "exact dense phase-aligned Uout^dagger Uin identity norm plus trace "
                         "average-gate fidelity for every unique successful semantic cell"
                     )},
        "predicate": "sha256_and_json_pointer_equals",
    }, "All 6,858 unique successful E31 semantic cells passed phase-aligned Uout^dagger Uin identity checks."),
    "9.49": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/analysis/equal_budget_pareto_summary.csv",
        "selector": {"type": "csv_columns", "required": [
            "pareto_nondominated", "dominates_n", "dominated_by_n",
            "pareto_dominance_rate", "pareto_dominated_by_rate",
        ]},
        "predicate": "sha256_matches_and_required_csv_columns_exist",
    }, "The sealed 72-cell equal-budget table reports dominance counts and rates."),
    "9.04": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/semantic_cell_structural_metrics.csv",
        "selector": {"type": "csv_columns", "required": ["multi_qubit_gate_count"]},
        "predicate": "sha256_matches_and_required_csv_columns_exist",
    }, "All 6,858 successful semantic cells report exact logical multi-qubit gate counts."),
    "9.07": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/semantic_cell_structural_metrics.csv",
        "selector": {"type": "csv_columns", "required": ["two_qubit_depth"]},
        "predicate": "sha256_matches_and_required_csv_columns_exist",
    }, "All 6,858 successful semantic cells report exact logical two-qubit depth."),
    "9.10": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/semantic_cell_structural_metrics.csv",
        "selector": {"type": "csv_columns", "required": ["ancilla_qubits"]},
        "predicate": "sha256_matches_and_required_csv_columns_exist",
    }, "All 6,858 successful semantic cells report declared ancilla-qubit counts."),
    "9.11": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/semantic_cell_structural_metrics.csv",
        "selector": {"type": "csv_columns", "required": ["measurement_count", "reset_count"]},
        "predicate": "sha256_matches_and_required_csv_columns_exist",
    }, "All 6,858 successful semantic cells report measurement and reset counts."),
    "9.13": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/semantic_cell_structural_metrics.csv",
        "selector": {"type": "csv_columns", "required": ["interaction_graph_pair_edges", "interaction_graph_density"]},
        "predicate": "sha256_matches_and_required_csv_columns_exist",
    }, "All 6,858 successful semantic cells report pairwise interaction-graph density."),
    "9.15": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/semantic_cell_structural_metrics.csv",
        "selector": {"type": "csv_columns", "required": ["swap_count"]},
        "predicate": "sha256_matches_and_required_csv_columns_exist",
    }, "All 6,858 successful semantic cells report logical SWAP counts."),
    "9.23": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/semantic_cell_structural_metrics.csv",
        "selector": {"type": "csv_columns", "required": ["toffoli_ccz_count"]},
        "predicate": "sha256_matches_and_required_csv_columns_exist",
    }, "All 6,858 successful semantic cells report logical CCZ/Toffoli counts."),
    "9.42": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/distributional_risk_summary.json",
        "selector": {"type": "json_pointer_equals", "pointer": "/success_only_reduction_quantiles_pp/q05", "expected": 0.0},
        "predicate": "sha256_and_json_pointer_equals",
    }, "The sealed E31 distributional audit reports lower-tail reduction quantiles; the success-only q05 is 0 pp."),
    "9.44": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/distributional_risk_summary.json",
        "selector": {"type": "json_pointer_equals", "pointer": "/successful_regression_probability", "expected": 0.0},
        "predicate": "sha256_and_json_pointer_equals",
    }, "The sealed E31 audit reports zero successful common-basis gate-count regressions."),
    "9.45": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/distributional_risk_summary.json",
        "selector": {"type": "json_pointer_equals", "pointer": "/successful_expansion_probability_by_threshold/increase_ge_10pct", "expected": 0.0},
        "predicate": "sha256_and_json_pointer_equals",
    }, "The post-seal sensitivity audit reports zero successful outputs with at least 10% common-basis expansion."),
    "9.55": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/postseal_structural_distribution_metrics/distributional_risk_summary.json",
        "selector": {"type": "json_pointer_equals", "pointer": "/solution_diversity/unique_output_circuits_global", "expected": 1802},
        "predicate": "sha256_and_json_pointer_equals",
    }, "The sealed E31 panel contains 1,802 distinct successful output circuits, with per-input diversity also reported."),
    "9.50": ({
        "path": "data/v11/e31_factorial_pareto/formal_run/analysis/pareto_hypervolume_audit.json",
        "selector": {"type": "json_pointer_equals", "pointer": "/method",
                     "expected": "SEEDED_MONTE_CARLO_UNIT_HYPERCUBE"},
        "predicate": "sha256_and_json_pointer_equals",
    }, "The sealed exploratory Pareto packet reports seeded normalized hypervolume and MC error."),
    "12.10": ({
        "path": (
            "data/v11/e31_factorial_pareto/formal_run/analysis/family_inference/"
            "family_supportive_factorial_71.csv"
        ),
        "selector": {"type": "csv_columns", "required": [
            "coefficient", "equal_family_estimate_pp", "family_cluster_se_pp",
            "family_cluster_df", "t14_ci95_low_pp", "t14_ci95_high_pp",
            "wild_cluster_bootstrap_t_p_value", "holm_adjusted_wild_cluster_p",
        ]},
        "predicate": "sha256_matches_and_required_csv_columns_exist",
    }, "The sealed 15-family correction reports estimates and uncertainty for factorial interactions."),
    "15.06": ({
        "path": "release/sbom.cdx.json",
        "selector": {"type": "json_pointer_equals", "pointer": "/bomFormat",
                     "expected": "CycloneDX"},
        "predicate": "sha256_and_json_pointer_equals",
    }, "A verified CycloneDX 1.6 SBOM inventories the project and its dependency graph."),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def merge() -> dict[str, object]:
    fragment_paths = [
        FRAGMENTS / "sections_01_06.json",
        FRAGMENTS / "sections_07_12.json",
        FRAGMENTS / "sections_13_18.json",
    ]
    entries: list[dict[str, object]] = []
    for path in fragment_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "metric-evidence-registry-fragment-v1":
            raise RuntimeError(f"unsupported fragment schema: {path.name}")
        entries.extend(payload["metrics"])
    entries.sort(key=lambda entry: (int(entry["section"]), int(entry["item"])))
    ids = [str(entry["metric_id"]) for entry in entries]
    if len(entries) != 592 or len(set(ids)) != 592:
        raise RuntimeError("metric fragments do not form a unique 592-item inventory")
    if {int(entry["section"]) for entry in entries} != set(range(1, 19)):
        raise RuntimeError("metric fragments do not cover all 18 sections")

    for entry in entries:
        metric_id = str(entry["metric_id"])
        refs = list(entry.get("evidence_refs", []))
        # Remove the sections 13-18 circular pointer to the registry being replaced.
        refs = [
            ref for ref in refs
            if not (
                ref.get("path") in {
                    "docs/review/metric_evidence_registry_2026-08-26.json",
                    "release/prepaper_release_manifest.json",
                }
                or ref.get("predicate")
                == "sha256_and_json_pointer_metric_id_section_item_status_match"
            )
        ]
        status = str(entry["status"])
        if metric_id in CONSERVATIVE_DOWNGRADES and status == "PASS":
            status = "PARTIAL"
            entry["criterion_met"] = False
            entry["observed_value"] = (
                str(entry["observed_value"])
                + " Independent merge audit: the cited field/column existence is indirect and "
                "does not by itself prove the complete catalog question."
            )
            entry["residual"] = (
                "Add a metric-specific semantic selector or executable assertion that proves the "
                "full question; file/field existence alone is insufficient."
            )
        overlay = DIRECT_STATUS_OVERLAYS.get(metric_id)
        if overlay is not None:
            relative, expected_status, observed = overlay
            evidence = ROOT / relative
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            if payload.get("status") != expected_status:
                raise RuntimeError(f"direct overlay is stale: {metric_id}")
            refs.append({
                "role": "satisfaction",
                "metric_id": metric_id,
                "path": relative,
                "sha256": sha256(evidence),
                "selector": {
                    "type": "json_pointer_equals",
                    "pointer": "/status",
                    "expected": expected_status,
                },
                "predicate": "sha256_and_json_pointer_equals",
            })
            status = "PASS"
            entry["criterion_met"] = True
            entry["observed_value"] = observed
            entry["residual"] = (
                "None for the explicitly bounded audit scope; do not generalize beyond its "
                "recorded cases/configurations."
            )
        disposition_overlay = DIRECT_DISPOSITION_OVERLAYS.get(metric_id)
        if disposition_overlay is not None:
            relative, expected_disposition, final_status, observed = disposition_overlay
            evidence = ROOT / relative
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            actual = payload.get("metric_dispositions", {}).get(metric_id)
            if actual != expected_disposition:
                raise RuntimeError(f"metric disposition overlay is stale: {metric_id}")
            refs.append({
                "role": "satisfaction" if final_status == "PASS" else "supporting",
                "metric_id": metric_id,
                "path": relative,
                "sha256": sha256(evidence),
                "selector": {
                    "type": "json_pointer_equals",
                    "pointer": f"/metric_dispositions/{metric_id}",
                    "expected": expected_disposition,
                },
                "predicate": "sha256_and_json_pointer_equals",
            })
            status = final_status
            entry["criterion_met"] = final_status == "PASS"
            entry["observed_value"] = observed
            if final_status == "PASS":
                entry["residual"] = (
                    "None for the explicitly bounded audit scope; retain the recorded claim "
                    "boundary."
                )
            elif final_status == "NA":
                entry["residual"] = (
                    "Not applicable under the frozen unitary scope; reassess if dynamic "
                    "circuits enter the target population."
                )
            else:
                entry["residual"] = (
                    "Complete the residual work stated in the evidence claim boundary before "
                    "upgrading this item to PASS."
                )
        direct_ref_overlay = DIRECT_REF_OVERLAYS.get(metric_id)
        if direct_ref_overlay is not None:
            specification, observed = direct_ref_overlay
            evidence = ROOT / str(specification["path"])
            if not evidence.is_file():
                raise RuntimeError(f"direct evidence overlay is missing: {metric_id}")
            refs.append({
                "role": "satisfaction",
                "metric_id": metric_id,
                "path": specification["path"],
                "sha256": sha256(evidence),
                "selector": specification["selector"],
                "predicate": specification["predicate"],
            })
            status = "PASS"
            entry["criterion_met"] = True
            entry["observed_value"] = observed
            entry["residual"] = (
                "None for the sealed E31/bounded audit scope; retain the recorded exploratory "
                "and generalization limitations."
            )
        for ref in refs:
            role = ref.get("role")
            if role == "satisfaction_evidence":
                ref["role"] = "satisfaction" if status == "PASS" else "supporting"
            elif role in {"item_specific_assessment_evidence", "scope_evidence",
                          "external_action_evidence", "item_specific_assessment"}:
                ref["role"] = "supporting"
            evidence_path = ROOT / str(ref.get("path", ""))
            if not evidence_path.is_file():
                raise RuntimeError(
                    f"metric {metric_id} references missing evidence: {ref.get('path')}"
                )
            # Fragments are reviewer inputs; the merged registry is the current release
            # binding.  Rehash here, while the independent verifier still re-evaluates
            # every selector/predicate against the new bytes.
            ref["sha256"] = sha256(evidence_path)
        # A non-PASS entry must not retain a mechanically passing satisfaction ref.
        if status != "PASS":
            for ref in refs:
                if ref.get("role") == "satisfaction":
                    ref["role"] = "supporting"
        entry["evidence_refs"] = refs
        entry["status"] = status
        entry["criterion_met"] = status == "PASS"
        entry["assessment_predicate"] = {
            "type": "all_satisfaction_evidence_matches",
            "minimum_satisfaction_refs": 1,
            "on_true": "PASS",
            "on_false": "PARTIAL" if status == "PASS" else status,
        }
        entry["legacy_status_is_authoritative"] = False

    return {
        "schema_version": "metric-evidence-registry-v2",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "catalog_path": CATALOG.relative_to(ROOT).as_posix(),
        "catalog_sha256": sha256(CATALOG),
        "source_attachment_sha256": sha256(CATALOG),
        "source_fragments": {
            path.relative_to(ROOT).as_posix(): sha256(path) for path in fragment_paths
        },
        "merge_policy": {
            "circular_registry_evidence_removed": True,
            "section_status_inheritance_allowed": False,
            "pass_requires_item_specific_satisfaction_evidence": True,
            "field_or_column_existence_alone_can_answer_broad_semantic_question": False,
            "conservative_downgrade_metric_ids": sorted(CONSERVATIVE_DOWNGRADES),
        },
        "metrics": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    payload = merge()
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
