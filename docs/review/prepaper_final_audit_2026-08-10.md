# Q-research final pre-paper audit (2026-08-10)

> **Superseded as a completeness verdict on 2026-08-11.** The frozen pre-paper
> gates below were satisfied, but the later 592-item metric audit found material
> residual gaps and corrected the independent unit to unique input hashes.
> Current metric authority is `metric_audit_resolution_2026-08-24.md` plus
> `metric_audit_ledger_2026-08-24.csv`. Quantitative held-out, RQ3, and external
> values below are the pre-correction row-weighted estimates.

Status: pre-paper research package audit. No manuscript prose was drafted or
revised in this workstream; `docs/manuscript/manuscript.md` was intentionally
left outside the completion claim.

## Bottom line

The project has advanced from an overclaimed exploratory package to a strong,
auditable pre-paper research package. It now supports a narrower contribution:
flat circuit listing and a specified local-rule/window contract measurably alter
accessible gate reductions; that sensitivity is family-dependent and has
prospectively sealed out-of-family predictive signal. It does **not** support a
universal phase transition, an algorithm-independent local-search ceiling, a
general QMA-hardness result, or a claim of best optimizer performance.

- **Scientific level:** high pre-paper empirical/methodological level. The
  strongest features are frozen estimands, exact failure semantics, corrected
  reruns, cluster-aware uncertainty, independent artifacts, sealed transfer,
  source/hash provenance, and visible refutations. It is not yet a top-tier
  paper because paper construction, hardware validation and peer review remain.
- **Innovation level:** meaningful but conditional rather than paradigm-level.
  The defensible novelty is the frozen flat-listing/rule/window diagnostic,
  family decomposition and sealed out-of-family validation. Representation
  choice, rewrite discovery, relaxed peepholes, graph policies and local
  optimality already have substantial prior art.
- **Research value:** strong diagnostic and reproducibility value. The work can
  help distinguish optimizer weakness from representation/rule-accessibility
  limits and provides a falsifiable evaluation packet. Direct device/compiler
  deployment value is not yet established.

ScholarEval research-package score is 4.33/5.00. This passes the pre-paper gate
only; it is not a manuscript or acceptance probability score.

## Requirement-to-evidence closure

| Requirement | Final action/evidence | Status |
|---|---|---|
| Read every file/folder | Initial tracked-file parse audited 564 files; final byte-read workspace inventory covers every file and directory present at scan start except root `.git` internals and its own output directory | PASS |
| Repair correctness defects | Stochastic valid-incumbent tracking, paired statistics, ITT failure retention, source drift, gate constants, exact fidelity and release traversal corrected with regressions | PASS |
| Retest core experiments | E3 12,000 rows; E14 2,130; E18 1,080; E23 160; E26 2,427; retained null/failure outcomes | PASS |
| Test representation claim | RQ1 canonical multi-family WCL-LBL = 5.901 pp, 95% CI 2.004--10.615, cluster p=0.01770; not equivalent within +/-1 pp | PASS, bounded |
| Prospective generalization | Sealed 240 instances/eight new families: MCC 0.731, nested 95% CI 0.425--1.000; seal hashes verified | PASS, wide CI |
| Strong compiler comparison | Custom/Qiskit/Cirq/tket each receive the same 520 frozen inputs; validity and ITT outcomes include failures | PASS |
| Independent optimizer artifacts | Official Quasar v3 and Quartz commit `c4abf876...` completed 520 inputs; emitted circuits independently revalidated by exact average gate fidelity | PASS |
| Statistical rigor | Family-outer/instance-inner bootstrap, cluster sign permutations, paired tests/effect sizes, Holm, LOFO, MDE/equivalence; mixed-model nonconvergence disclosed | PASS with fallback |
| Theory/claim discipline | General ceiling refuted by counterexample; former Theorem 8 withdrawn; restricted AG result and existence bounds correctly scoped | PASS |
| Publication figures | Four figures each have source CSV, PDF, SVG and 600-dpi PNG; mechanical and manual visual audits pass | PASS |
| Reproducibility/release | Full tests, compile/diff checks, workspace inventory, pre-paper manifest and independent cross-artifact verifier | PASS |

## Frozen quantitative findings

1. RQ1 multi-family estimate: 480 pairs in 16 family clusters, mean WCL-LBL
   5.9009 pp, nested 95% CI [2.0045, 10.6151], cluster sign-permutation
   p=0.01770. The supporting 5,000-pair random-depth result is 7.8285 pp, but
   its depth strata do not replace independent generator-family clusters.
2. Held-out prediction: 240 instances, eight generator families, MCC 0.7307
   [0.4250, 1.0000], accuracy 0.8458, balanced accuracy 0.8767, AUROC 0.9919.
3. Shared tools, exact-valid/520 and ITT common-basis reduction: custom
   509/520 and 12.691%; Qiskit 520/520 and 25.651%; Cirq 519/520 and
   -257.359%; tket 512/520 and -20.189%. These are contract-specific outputs,
   not a universal ranking.
4. External artifacts: Quasar 408/520 exact-valid, 42 timeouts, 50 errors,
   28.296% ITT reduction; Quartz 519/520 exact-valid, no wrapper failure,
   -5.377% ITT reduction. Quasar-Quartz family-cluster Holm p=0.05799 for both
   validity and reduction endpoints, so no confirmatory external winner is
   declared.
5. Negative results remain results: E23's zero Greedy reduction applies only to
   the restricted generator; Quartz has one genuinely invalid output; Quasar
   has 20 emitted but low-fidelity outputs beyond its other failures; RQ1/RQ3
   mixed models did not converge; the old universal correlation claim failed.

## Reproducibility record

- Full pytest: 341 tests passed, exit 0, 217.4 s. Warnings are
  dependency deprecations, one small-sample Wilcoxon approximation warning and
  Qiskit API deprecation; no test failure.
- Python compileall: exit 0. `git diff --check`: exit 0; Windows line-ending
  notices are non-failing working-tree conversion notices.
- Figure verifier: four figures mechanically verified; manual audit records the
  corrected Figure 2 legend and final artifact hashes.
- Workspace byte-read: every file and directory present at scan start; root
  `.git` internals, the self-generated audit-output directory and the generated
  pre-paper manifest itself are the only exclusions. Excluding the manifest
  prevents the subsequent manifest write from invalidating its own workspace
  snapshot. Exact final counts, bytes, line totals and inventory hashes are in
  `data/v10/prepaper/audit/workspace_coverage.json`.
- Pre-paper release manifest: 130 evidence files plus 43 source/protocol files,
  173 pinned files total.
- Independent release verifier: 215,150 CSV rows, 620 numeric columns checked
  for infinity, 28 nested audit hashes and 15 external-lineage checks.
- Historical canonical release chain remains separate and is checked by the
  release-manifest tests; the working tree is intentionally dirty because this
  audit work is not committed by the assistant.

## Residual limitations and evidence that would change the verdict

1. Execute on real hardware or a noise-aware backend with hardware-relevant
   depth/two-qubit/error metrics; a failure to transfer would lower research
   value for compiler deployment but not erase the representation diagnostic.
2. Add independently executable GUOQ/Quarl/OAC-style methods when artifact and
   compute contracts permit. Different family-cluster conclusions could change
   the external-validity assessment.
3. Increase genuinely independent generator families. A narrower held-out MCC
   interval near zero or unstable LOFO signs would weaken generalization.
4. Equalize compute budgets in addition to reporting official configurations.
   A budget-normalized reversal would change performance interpretation.
5. Refresh 2025--2026 literature before drafting/submission. Earlier work with
   the same flat-listing diagnostic and prospective family-transfer design
   would reduce novelty.
6. Draft the manuscript only after choosing a bounded claim hierarchy. The
   manuscript must be separately evaluated for argument, citations and
   presentation; this audit does not pre-approve it.

## Completion decision

Every pre-paper gate defined in the frozen protocol is satisfied by direct
runtime or artifact evidence. There is no remaining required pre-paper repair
inside the authorized scope. The next phase is manuscript drafting, which was
explicitly not performed here and must begin from the bounded claims above.
