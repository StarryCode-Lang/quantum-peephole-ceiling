# E31 transitive-source provenance limitation

Date: 2026-08-24

## Finding

The formal E31 `environment.json` cryptographically froze seven directly listed runtime source files, and all seven still match their recorded SHA-256 values. It did not freeze the complete first-party import closure. In particular, the orchestrator imports the design validator, and importing the circuit and optimisation submodules executes package initializers that load additional project modules.

This is a provenance limitation, not evidence of outcome drift. It must nevertheless remain visible in every release-eligibility decision. The historical environment record is not amended: adding hashes after execution began would falsely present post-hoc evidence as a pre-run freeze.

## Boundary captured before aggregate treatment analysis

- Checkpoint read: 2026-08-24 04:03:57 UTC.
- Committed rows: 21,366; run orders 0 through 21,365, with unique run IDs and run orders.
- Status counts inspected: 15,433 `success`, 5,933 `timeout`; no treatment-effect aggregate was computed.
- First checkpoint commit: 2026-08-11T12:49:21.790965+00:00.
- Last commit at the captured boundary: 2026-08-24T04:03:53.847310+00:00.
- SQLite integrity result: `ok`.
- No row exclusion, rerun, protocol change, worker change, or source rewrite is authorized by this disclosure.

## Omitted first-party import closure

The post-hoc closure contains 16 files absent from `environment.source_sha256`:

1. `experiments/e31_factorial_pareto_design.py`
2. `src/circuits/__init__.py`
3. `src/circuits/generator_v2.py`
4. `src/optimisation/__init__.py`
5. `src/optimisation/base.py`
6. `src/optimisation/constants.py`
7. `src/equivalence.py`
8. `src/optimisation/_gate_predicates.py`
9. `src/optimisation/ceiling_aware.py`
10. `src/optimisation/phase1/__init__.py`
11. `src/optimisation/phase1/greedy.py`
12. `src/optimisation/phase1/random_local_search.py`
13. `src/optimisation/phase1/simulated_annealing.py`
14. `src/optimisation/phase1/genetic_algorithm.py`
15. `src/optimisation/phase2/__init__.py`
16. `src/optimisation/phase2/commutation_rewriter.py`

The release workflow must also run `scripts/audit_e31_first_party_import_closure.py`. That audit starts from the formal orchestrator and worker, resolves static local import statements and package initializers with Python's AST, and fails unless its 23-file result is exactly the disjoint union of the seven pre-run hashes and these 16 post-hoc hashes. It does not prove that arbitrary dynamic/plugin imports are absent. Its output is required at `release/e31_first_party_import_closure_audit.json`; it is not treated as pre-run evidence.

The latest filesystem write among these files was the design validator at 2026-08-11T20:04:26.4583322+08:00, 44 minutes 55 seconds before the first checkpoint commit. The outcome-relevant optimiser/equivalence files were last written no later than 2026-08-11T19:47:09.1480478+08:00. Session evidence also records the corresponding equivalence and optimiser edits before the first commit. A machine-readable gate pins every current hash and timestamp.

## What this evidence establishes

- The seven sources claimed by the historical environment record have not drifted.
- Every currently identified omitted first-party module has a current hash pinned by the post-hoc gate.
- All post-hoc recorded filesystem timestamp values precede the first committed formal row; the gate does not independently authenticate those timestamps.
- The frozen protocol and design manifest remain SHA-bound, and each E31 cell runs in a cold child process.

## What it cannot establish

- Filesystem timestamps are not a cryptographic pre-run commitment.
- They cannot rule out an edit-and-revert that preserved or reset a timestamp.
- The historical session is supporting evidence, not an independently timestamped transparency log.
- Therefore E31 cannot be described as having a complete cryptographic pre-run freeze of its transitive first-party source closure.

## Release interpretation

E31 remains conditionally release-eligible if the completed schedule, sealed SQLite/CSV identity, all direct frozen hashes, all post-hoc closure hashes, checkpoint-boundary timestamps, semantic verification, temporal-drift diagnostics, and formal analysis gates pass. The provenance metric remains `PARTIAL`, not `PASS`, and the manuscript must disclose this limitation. A future confirmatory rerun should generate and freeze the resolved first-party import closure before row 0.
