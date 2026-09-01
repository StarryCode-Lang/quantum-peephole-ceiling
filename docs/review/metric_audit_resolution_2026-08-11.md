# Q-research 592-item metric audit and resolution record (2026-08-11)

> **Superseded as the current metric verdict on 2026-08-24.** Retained as an
> audit-history snapshot. Current item statuses and post-baseline evidence are
> generated in `metric_audit_ledger_2026-08-24.csv`,
> `metric_audit_summary_2026-08-24.json`, and
> `metric_audit_resolution_2026-08-24.md`.

Status: pre-paper research audit and implementation record. The manuscript body
was not edited. This document supersedes the 2026-08-10 audit only where that
document called the pre-paper package complete or reported row-weighted
uncertainty as instance-level evidence.

## Coverage result

The user-supplied catalog contains 20 dashboard metrics and 572 numbered audit
questions across 18 domains. `metric_audit_ledger_2026-08-11.csv` contains all
592 items with no unmapped row. Conservative status counts after this pass are:

| Status | Count | Meaning |
|---|---:|---|
| PASS | 238 | verified in the current bounded contract |
| PARTIAL | 177 | evidence exists but a residual condition remains |
| FAIL | 146 | missing, failed, or barred from claims |
| EXTERNAL | 5 | requires hardware, independent people, or live literature evidence |
| NA | 26 | outside the currently stated unitary/logical-circuit model |

This is intentionally not converted into an inflated pass score. A FAIL may be
an unavailable research capability rather than a software defect, but it still
bars the corresponding claim.

Exactly 19 item statuses changed in this regeneration:

- PARTIAL → PASS: `6.26` (checkpoint/resume fault injection), `11.01`
  (experimental unit), `11.11` (randomization inference implementation), `11.15`
  (pre-frozen MCID), `11.23` (prospective power/MDE), `11.24` (power matched to
  the two estimands), `12.33` (shared-engine variable isolation), and `15.23`
  (one-command hash-gated main runner).
- FAIL → PARTIAL: `1.14`, `8.20`, `8.21`, `8.22`, `12.04`, `12.09`, `12.21`,
  `18.02`, and `18.08`, because the equal-budget/full-factorial/Pareto machinery
  now exists but formal results do not; and `18.11`, because checkpoint fault
  injection exists but broad mutation/property/parser coverage remains unfinished.
- PASS → PARTIAL: `1.13`; the older bounded held-out evidence remains recorded,
  but the first heldout-v2 joint packet was invalidated by the exact gate after
  detecting Qiskit layout false negatives in 48/192 v2 inputs. A fresh rerun is
  pending, so cross-family generalization is not treated as complete.

No metric moved to PASS merely because a future run is scheduled. In particular,
the E31-result, broad cross-family generalization, real-QPU, and
independent-reproduction gates remain unmet.

## Directly verifiable ledger candidates not applied in this document-only correction

The ledger was intentionally not regenerated for the heldout-v2 correction.
Read-only inspection found the following new evidence that was not reflected in
its prior statuses; these are candidates for the next deliberate ledger pass,
not status changes made here:

- `14.03` (same initial layout), `14.08` (native 2Q depth), and `14.09`
  (scheduled duration): the completed paired hardware-surrogate packet directly
  records these under a shared layout/routing contract. They are plausible
  FAIL → PASS changes for that bounded surrogate contract only.
- `14.12` (estimated success probability) and `14.13` (noise-aware cost): the
  packet reports a calibration-success product proxy and noisy-simulator output
  metrics, but explicitly excludes correlated error, idling, context, and drift.
  At most FAIL → PARTIAL is directly justified; no real-QPU claim follows.
- `15.06` (SBOM): `release/sbom.cdx.json` is a CycloneDX 1.6 artifact with 72
  components and 73 dependency entries, accompanied by generator, verifier, and
  tests. This is a directly checkable FAIL → PASS candidate.
- `15.42` (link rot): `release/external_link_audit.json` audits 46 unique URLs;
  38 are reachable, three templates are not checked, and five HTTP results remain
  unverified. The audit capability justifies at most FAIL → PARTIAL, not PASS.
- Equivalence metrics need no obvious status change: the new fail-closed
  certificate implementation strengthens the evidence already behind `1.03`,
  `1.04`, `7.01`, `7.02`, `7.07`, and `7.10`, while symbolic parameters,
  large-scale scalable proof, independent-verifier disagreement, and broad gate
  conversion coverage remain incomplete under `7.06`, `7.11`, `7.15`, and
  `7.27`–`7.30`.

## Defects resolved in this pass

1. **Independent-unit pseudoreplication.** The sealed held-out manifest has 240
   execution rows but 186 unique input hashes; the shared 520 grid has 391
   unique inputs. Confirmatory held-out, RQ3, and external bootstrap analyses
   now aggregate within `circuit_family × input_circuit_sha256`. Execution rows
   remain available for operational failure/timeout counts.
2. **Held-out estimate corrected.** Unique-input MCC is 0.80599 with a nested
   95% interval [0.31944, 1.00000], 186 unique inputs and eight outer generator
   families. The direction survives, but the old `n=240` instance claim and
   [0.425, 1.0] interval are retired.
3. **Exact small-cluster randomization.** Family sign randomization now
   enumerates all assignments for at most 16 clusters instead of injecting
   Monte Carlo noise near alpha.
4. **External comparison corrected.** On 391 unique inputs, Quasar exact-valid
   rate is 0.7852 and Quartz 0.9974. Quasar minus Quartz ITT gate reduction is
   46.59 percentage points, family-sign p=0.02222 and Holm p=0.04443. The
   validity family-sign result is not confirmatory (p=0.078125). These remain
   fixed-contract comparisons, not a universal winner claim.
5. **Theorem 9 estimand repaired.** Pattern-matching runtime and bookkeeping are
   no longer converted into circuit "gate-slots". For the stated all-ones BV
   circuit, the current full pipeline is directly verified for n=2..5 to emit
   `X + n reversed CNOT + H`, giving achieved reduction `2n/(3n+2)`. E26's
   all-ones rows match this construction for every n=3..10. No global
   `n+2`-gate optimality is claimed.
6. **Theory authority conflicts repaired.** `framework.md` now defines the
   unitary-only scope, global-phase equivalence, and the adjacent Greedy
   subsystem without claiming all stochastic optimizers share its action set.
   The stale Haar-complexity explanation is withdrawn.
7. **Exact fidelity cost reduced.** The exact trace overlap uses the Frobenius
   inner product instead of materializing `U1†U2`; rotation inverse detection
   now respects 2π periodicity.
8. **Version drift repaired.** README project version now matches pyproject
   version 10.1.0.
9. **E31 independent units and factorial schedule frozen.** The 520 source rows
   collapse to 391 unique input hashes before expansion. Every hash is scheduled
   for all 72 listing × rule-set × window × budget cells, yielding 28,152 unique
   `run_id` rows in the frozen randomized order. This is a design artifact, not a
   completed Pareto experiment.
10. **Rule-set isolation and resource containment implemented.** Commutation-only
    and commutation-plus-templates now share parsing, listing, candidate scheduling,
    termination, and scoring; only `template_enabled` differs. Isolation tests and
    the 2-input × 4-cell non-confirmatory smoke validate identical trace/output when
    no template matches, treatment separation when one does, process-tree timeout,
    and RSS accounting.
11. **Dual estimands and prospective power gate frozen.** One 1-pp-MCID primary
    listing × rule-set interaction was frozen before formal results. Conditional on
    the fixed 391-hash benchmark it passes the prospective power gate; extrapolation
    to new families remains blocked because there are only 15 independent family
    clusters. Other effects remain supportive or exploratory.
12. **Formal checkpoint/resume path implemented.** The orchestrator binds protocol,
    design, and power hashes; dispatches frozen `run_order`; launches a cold capped
    process per cell; commits unique `run_id` rows atomically; and rejects duplicate,
    foreign, or order-drifted resume state. Fault-injection tests cover committed
    crash recovery. Formal launch additionally requires completed GUOQ and heldout
    release gates. The combined formal release gate remains unavailable while
    GUOQ is unfinished and heldout-v2 awaits a clean rerun.

## Claims still barred

- universal or algorithm-independent Phase-1 ceiling;
- CODP QMA-hardness, general Clifford minimum synthesis in P, or Haar-derived
  incompressibility for the sampled circuits;
- global optimality of the BV `n+2` output;
- hardware advantage, real-device value, or a universal optimizer ranking;
- large-circuit verified equivalence where the verifier reports unavailable;
- parameterized symbolic equivalence, dynamic-circuit equivalence, and
  fault-tolerant resource advantage;
- novelty priority, independent cold-start reproducibility, or broad external
  adoption without current external evidence.
- E31 quality–time/memory Pareto values or interaction estimates: the formal
  28,152-cell run has not started and `formal_run/` does not exist;
- broad held-out generalization: the first heldout-v2 joint analysis is an
  **invalidated preliminary packet**, not scientific evidence. The exact gate
  found Qiskit layout false negatives for 48/192 v2 inputs, invalidating the
  merged metrics and their interval. The batch is archived as invalid and a fresh
  rerun is pending; `1.13` remains PARTIAL and no universal/general-family claim
  is allowed;
- GUOQ as a completed third formal baseline: only preflight/smoke/pilot evidence is
  currently available;
- real-QPU benefit and independent reproduction: neither has current evidence.

The frozen `docs/manuscript/manuscript.md` predates these corrections and is not
an admissible claim source. It must be rebuilt later, not polished in place.

## Remaining executable research program

Highest-value unfinished work is: execute the already frozen equal-budget
1/10/30/120-second E31 factorial after the GUOQ and heldout gates complete;
fresh-rerun heldout-v2 after the exact-layout repair and regenerate the joint
analysis; complete a third independent optimizer artifact; symbolic
parameter equivalence; a predeclared
large-circuit verification degradation contract; unscreened noise-aware and
real-hardware validation; cross-version/platform runs; mutation/property/fault
injection tests; SBOM release-manifest integration, data licence, DOI archive;
and non-author cold-start
reproduction. These require new compute, hardware, external coordination, or a
larger experiment design and therefore remain FAIL/EXTERNAL rather than being
papered over with documentation.

## Verification record

Current ledger regeneration performed in this update:

- 592 rows parsed with no unmapped metric;
- counts: 238 PASS, 177 PARTIAL, 146 FAIL, 5 EXTERNAL, 26 NA;
- ledger SHA-256:
  `ddcd4ec7d8af823e203bbc46dba2994b702ed511883ff07f9eaf3e66ea5a74e9`;
- no full test suite or release generation was run during this ledger update.

Current E31 evidence inherited from the immediately preceding implementation
checks is limited to 47 targeted tests, an 8-row non-confirmatory resource smoke,
and orchestrator dry-run. The dry-run reports 28,152 pending rows and zero formal
scientific results. It must not be cited as a completed experiment.

Heldout-v2 is not complete. Its first sealed execution produced a preliminary
joint packet, but the exact gate subsequently detected Qiskit layout false
negatives in 48 of 192 v2 inputs. That entire packet and its derived joint
statistics are invalidated and inadmissible; a fresh rerun is pending.

The following are historical verification records from the preceding audit, not
commands rerun during this ledger-only update:

- Full test suite: 342 passed.
- Python source compilation: passed for `src`, `analysis`, `experiments`,
  `scripts`, and `tests`.
- Figure audit: four figures mechanically verified.
- Release verification: 180 files, 215,772 CSV rows, 28 nested audit hashes,
  15 external-lineage checks, and 628 numeric columns checked for infinity.
- The release remains intentionally marked from a dirty worktree; clean-commit
  reconstruction and non-author cold-start reproduction are not yet satisfied.
