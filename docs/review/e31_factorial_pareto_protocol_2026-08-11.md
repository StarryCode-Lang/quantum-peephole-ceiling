# E31 full-factorial and equal-budget Pareto frozen protocol

## Status and scope

Status: **protocol frozen before formal execution; formal run active as of
2026-08-24; a running checkpoint is not scientific evidence**.
The existing E31 pilot and the 2-input resource packet remain descriptive and
non-canonical. This document does not upgrade them or modify manuscript claims.

Method-authority update: the original family sign-randomization language below
is superseded by `e31_preanalysis_method_erratum_2026-08-24.md` because
`primary_pair_orientation` is metadata, not randomized treatment assignment.
The formal analysis must report the exact finite-benchmark paired effect with no
design-based p-value or confidence interval; its family-stratified bootstrap is
an empirical stability interval only.

Operational-environment update: `e31_host_environment_limitation_2026-08-24.md`
records that the runner enforces overlap only at startup and has no continuous
host telemetry. Resource and timeout findings are therefore conditional on the
recorded shared host and must include the predeclared run-order sensitivity.

Pre-execution amendment: the first admissible launch was mechanically refused
because the frozen 4096 MB worker cap was a few MB above 80% of available RAM.
Before any admissible formal row existed, the cap was made stricter (3072 MB),
and the protocol, schedule, power report, release gate, and resource smoke were
all regenerated. The treatment grid and estimands did not change. A separate
79-row parser preflight is archived as invalid and cannot be resumed.

Every retained input receives all 72 cells: three listings (LBL, WCL, seeded
random topological), two rule sets (commutation-only and the same engine with
templates enabled), three windows (4, 16, 64), and four end-to-end budgets (1,
10, 30, 120 seconds). Both rule levels use one parser, listing path, gather
window, candidate schedule, fixpoint, termination, and scoring implementation;
`template_enabled` is the only treatment difference. Isolation tests prove that
the output hash and trace agree when no template matches.

## Units, blocking, and resource contract

The independent inner unit is a unique `input_circuit_sha256`. Byte-identical
seed or ID rows are collapsed before expansion. The input hash is the
repeated-measure block. Circuit family is either a fixed blocking/heterogeneity
stratum (estimand A) or the independent outer cluster (estimand B); it is never
replaced by the number of treatment rows.

Run order uses seed `20260811`. The primary-pair orientation metadata is
randomized and balanced within family (absolute imbalance at most one), but is
not treatment assignment and licenses no randomization inference. Runs use one
worker, one thread, a cold process, and a 3072-MB process-tree cap. Parsing and
normalization are inside the time budget. Timeout and OOM cleanup terminate the
full process tree.

## Outcomes and failures

The response is common-basis gate reduction under intention to treat. Timeout,
error, invalid, unavailable, and OOM rows stay in the denominator and receive
zero ITT reduction. A missing `run_id` is fatal. Only exact average gate fidelity
at least `1 - 1e-10` can mark a row valid. Equal-budget Pareto summaries jointly
maximize ITT quality and validity and minimize time, peak RSS, and failure.

## Frozen dual estimands and hypothesis roles

Estimand A is the finite-population paired causal ATE conditional on the frozen
391 input hashes and their observed family composition. Input hash is the paired
block and family is fixed blocking/heterogeneity. Estimand B is the
equal-family-weighted ATE for potentially unseen families; family is then the
independent sampling cluster.

Exactly one contrast is confirmatory: the equal-weight mean over the complete
3-window x 4-budget grid of
`[(WCL-LBL)_commutation+templates - (WCL-LBL)_commutation-only]`. Its MCID is
frozen at 1 percentage point. Other main effects and prespecified two-way
interactions are supportive. Cellwise effects, post-hoc Pareto subgroups, and
three-/four-way interactions are exploratory. None may be relabelled after
formal results. The full 72-cell experiment and full interaction model remain.

The corrected fixed-benchmark analysis uses the exact finite-population paired
effect across the 391 frozen input hashes, its distance from the frozen 1-pp
MCID, and a family-stratified bootstrap stability interval explicitly labelled
non-design-based. No design-based p-value or confidence interval exists because
there was no randomized treatment assignment. The generalized new-family tier
uses 15 family means as a supportive/model-based sensitivity analysis and
remains barred from confirmatory language; input rows do not supply family
cluster degrees of freedom.

## Historical prospective power diagnostic and corrected role

The dual-estimand simulation uses 20,000 null and alternative draws per
scenario, two-sided alpha 0.05, 80% target power, and the unchanged 1 pp MCID.
The earlier paired listing-by-template pilot supplies a prospective variance
anchor. Since correlation among the 12 grid contrasts is unidentified, the
simulation checks correlations 0, 0.5, and 1.

For estimand A, the pre-execution simulation reported power at 1 pp of at least
99.985% and a worst simulated Type-I rate of 5.165% over the sensitivity range.
After the method erratum, these are retained as historical sizing diagnostics
under the superseded inferential model, not as design-based evidential power or
Type-I guarantees. The completed 391-hash grid instead yields the exact bounded
finite-population contrast and MCID decision described above.

For estimand B, the 15 family clusters remain the independent units. Power at
1 pp is about 7%, with Type-I error near 5%. Claims about new or unseen families
therefore remain **blocked until more independent families are collected**. The
391 inputs cannot be borrowed as 391 family replications. This tiering does not
raise the MCID, delete cells, or suppress interactions. Under the conservative
perfect-correlation scenario and the same variance anchor, approximately 539
independent families would be needed for 80% power at 1 pp; this is a planning
diagnostic, not permission to extrapolate from the current 15.

## Artifacts and commands

- Frozen protocol: `experiments/e31_factorial_pareto_protocol.json`
- Result schema: `experiments/e31_factorial_pareto_schema.json`
- Schedule generator: `experiments/e31_factorial_pareto_design.py`
- Analysis gate: `analysis/e31_factorial_pareto_analysis.py`
- Dual power simulation: `analysis/e31_dual_estimand_power.py`
- Shared worker/resource smoke: `experiments/e31_shared_rule_worker.py` and
  `experiments/e31_resource_smoke.py`
- Formal checkpoint/resume runner: `experiments/e31_formal_orchestrator.py`
- Integrated completion, analysis, and hash-bound seal:
  `analysis/e31_finalize_formal_run.py`

Generate the 28,152-row schedule without running optimizers:

```text
python experiments/e31_factorial_pareto_design.py
```

Audit it without creating results:

```text
python analysis/e31_factorial_pareto_analysis.py --design data/v11/e31_factorial_pareto/design_manifest.csv --protocol experiments/e31_factorial_pareto_protocol.json
```

Execution-status update (2026-08-24): the formal 28,152-row schedule is active
under the frozen protocol and resumable SQLite checkpoint. A running prefix is
not scientific evidence and licenses no metric upgrade. The local 2-input x
4-cell packet remains `RESOURCE_SMOKE_NONCONFIRMATORY`; formal evidence exists
only after the integrated finalizer produces and hash-binds the complete result
and analysis packet.

The formal runner defaults to dry-run. Formal execution additionally requires a
hash-bound `formal_release_gate.json` stating that both GUOQ and heldout work are
complete. It dispatches the frozen `run_order`, launches a cold shared worker per
cell, and commits each unique `run_id` to a FULL-synchronous SQLite checkpoint.
Resume validates every committed ID/order against the design; atomic CSV export
is derivative, not the checkpoint authority. SIGINT/SIGTERM kills the active
worker tree without committing the interrupted cell, leaving prior transactions
recoverable. Concurrent formal runners, E31 workers, or test processes are
rejected, and requested worker memory must remain below both physical and
currently available RAM safety limits.

Safe preflight only:

```text
python experiments/e31_formal_orchestrator.py --dry-run --workers 1
```
