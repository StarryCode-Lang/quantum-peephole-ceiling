# Publication Readiness Audit: Quantum Peephole Ceiling

**Audit date:** 2026-08-01  
**Scope:** Full repository review of theory, code, experiments, data, statistics,
reproducibility, manuscript readiness, and cleanup safety.  
**Standard:** Nature/Science-level skepticism first; quantum-software venue
readiness assessed separately.

> **Status (2026-08-07):** The 2026-08-06 revision wave addressed E26 ID
> normalization, corrected Theorem 1(a) validation by E30, the AG-generator
> fix, search-ledger/reference repairs, documentation resync, and project
> infrastructure. This follow-up audit additionally fixes E20's reusable Cirq
> QASM pipeline and active-document drift. Treat the manuscript,
> `data/DATA_CANONICAL.md` (v2.4.0), and `release/release_manifest.json` as the
> current evidence boundary; canonical data remain frozen historical evidence.
> E31 is a non-canonical smoke pilot for the still-open listing x Phase-2b
> factorial and must not be read as a canonical release dataset.

## Executive Verdict

The project contains a potentially valuable quantum-compilation methodology
result, not a Nature/Science-level physics result in its current form. The
strongest defensible contribution is narrower than the current title suggests:

> For a specified class of flat-list peephole rewrites, optimization opportunity
> is conditional on circuit representation and rewrite-library coverage; the
> same circuit can exhibit a near-empty Phase-1 action space under LBL and a
> non-zero action space under valid wire-oriented listings, while Phase-2b
> templates recover large reductions on selected structured families.

This is potentially publishable in quantum software, quantum compilation, or
programming-languages venues after an independent theory audit, active-document
resynchronization, clean provenance release, and a final preregistered held-out
benchmark. It is not ready for Nature or Science because the current evidence is
single-group, simulation-only, largely synthetic, representation/model-specific,
and contains theory and documentation claims that are not yet independently
validated.

## Evidence Snapshot

| Area | Current evidence | Assessment |
|---|---|---|
| Repository scale | 37 listed manifest datasets; 96,289 rows, including 35 active canonical datasets and 2 superseded provenance entries | Large but scale is not a substitute for independent design validity |
| Unit tests | 317 tests passed with the project Python 3.12.12 environment | Strong engineering baseline; dependency deprecation warnings remain |
| Syntax | `python -m compileall -q src experiments scripts analysis` passed | Clean syntax evidence |
| Data integrity | `python scripts/reproduce_all.py --verify` passes all 37 checksums/row counts and structural checks; source-hash drift is warning-only historical provenance | Keep canonical files frozen and cite the reconciliation layer separately |
| Fidelity fallback | Original product-state estimator overestimated an `n=8` local-X mismatch (`~0.347` vs exact `0.0039`) | Critical scientific defect; fixed to global Haar sampling and calibrated |
| Theory | Listing-conditional Phase-1 result is plausible and partly formal; Theorems 5 and 8 require independent proof review | Do not present all labeled theorems as equally established |
| Hardware evidence | Fake-backend noise-model simulation only | Not real-hardware validation |
| External literature | Local literature file exists; `parallel-cli` is unavailable, so current-field verification was not completed in this audit | Submission blocker for a novelty claim |
| Multiagent review | Four lanes attempted; runtime model aliases unavailable | Main-thread audit is fallback, not independent peer review |

## What Is Actually Novel

### External spot-checks

The local bibliography was checked against primary arXiv records for the most
direct comparators. Quartz is arXiv:2204.09033, not arXiv:2205.00125; the latter
is a different telecloning paper. Quarl explicitly uses a graph neural network
state representation and decomposed action space (arXiv:2307.10120). AlphaTensor-
Quantum targets T-count optimization through tensor decomposition and arithmetic
benchmarks (arXiv:2402.14396). SSR uses generalized commutation, circuit sweeping,
and SAT rewriting for connectivity-transformed circuits, with a June 2026 revised
record reporting up to 26.68% depth reduction and 12.18% average in its setting
(arXiv:2503.03227). The ZX-RL citation is Quantum 9, 1758 (2025), not article
1634. These checks strengthen the need for mechanism-level positioning rather
than a broad “first quantum circuit optimizer theory” claim.

Primary records: <https://arxiv.org/abs/2204.09033>,
<https://arxiv.org/abs/2307.10120>, <https://arxiv.org/abs/2402.14396>,
<https://arxiv.org/abs/2503.03227>, and
<https://arxiv.org/abs/2312.11597>.

### Defensible novelty

1. **Representation-conditioned action-space analysis.** The project makes the
   circuit listing a first-class independent variable instead of treating it as
   an implementation detail. The LBL result is close to definitional under the
   stated model, but it is useful because it exposes a reproducibility trap in
   flat-list benchmarking.
2. **Mechanism taxonomy.** The project separates adjacent cancellation,
   commutation exposure, template rewriting, and production-compiler mechanisms.
   The taxonomy is more informative than a single optimizer leaderboard.
3. **Negative-result discipline.** The project records that several apparent
   ceilings disappear after adding templates, while some families remain hard
   for all tested tools. This is scientifically stronger than claiming universal
   optimizer superiority.
4. **Theory-to-experiment bridge for selected constructions.** The BV Phase-2b
   pipeline reaches the stated `k+2` optimum on the recorded instances, and the
   Theorem-7 artificial family gives a controlled Phase-2a separation.
5. **Reproducibility infrastructure.** Canonical files, metadata, SHA-256
   manifests, rerun reconciliation, seed records, and source hashes are useful
   contributions if the remaining drift is made explicit and independently
   replayable.

### Claims that are not currently defensible

1. “First formal theory of peephole optimization limits” is too broad without a
   systematic literature search and a precise comparison against verified
   optimizers, equality saturation, phase-polynomial methods, ZX methods, and
   DAG-based compiler theory.
2. “Columnar representation example sensitivity” is not standard terminology
   and is easy to confuse with columnar storage. Use “listing-model sensitivity”
   or “representation-conditioned peephole ceilings.”
3. The 0% LBL result does not establish a universal limit on quantum circuit
   optimization or on production compilers. It is conditional on the listing,
   gate predicate, window, and rewrite model.
4. The E21 speedup is not a single clean systems result because the original
   timing protocol includes exact-fidelity work that the ceiling-aware path
   excludes. Only the symmetric-accounting result should be foregrounded.
5. The repaired ceiling model is exploratory. Post-hoc mechanism selection,
   family-level small `n`, and the RepetitionCode held-out failure prevent a
   general predictive-law claim.
6. “Hardware validation” must remain “noise-model simulation.” No real device
   experiment is present in the repository.
7. The placeholder Zenodo DOI and placeholder author/contribution declarations
   cannot appear in a submission draft.

## Critical Scientific Findings

### F1. Fidelity fallback was invalid for global average fidelity

Before this audit, `_estimate_fidelity` used tensor products of independently
sampled single-qubit states. Such states are not an n-qubit projective 2-design.
The observed calibration failure was large: for a local `X` mismatch, exact
average fidelity was `1/(2^n+1)`, while the product-state estimate stayed near
`1/3` as `n` increased. This could convert an incorrect optimization into a
false fidelity pass on large circuits.

**Action executed:** `src/optimisation/base.py` now samples globally Haar-random
states via normalized complex Gaussian vectors. Added
`scripts/characterize_fidelity_fallback.py`, checked-in calibration outputs under
`docs/verification/`, and `tests/test_fidelity_estimator.py`.

**Remaining requirement:** do not call the sampled path an exact certificate;
report sample variance or confidence intervals. Existing canonical datasets were
not silently rewritten. Any manuscript number depending on the old path needs a
targeted rerun or an explicit exclusion.

### F2. The release manifest was stale relative to accepted data

The current listing-sensitivity file contains 6,720 rows and qwalk-8 has 20/20
variants. The manifest was regenerated in the 2026-08-06 wave and
`scripts/reproduce_all.py --verify` now passes all 37 checksum and row-count
entries. The qwalk-8 rows intentionally skip exact unitary construction at nine
qubits, as recorded in the active evidence map.

**Release rule:** rerun this gate after any canonical-data change. Non-canonical
corrected reruns, including `data/v11/e20_corrected/`, must not be added to the
manifest without an explicit evidence-version decision.

### F3. Active documents disagree about experiment status

Examples:

- Active theory, manuscript, claim-map, appendix, supplementary, and result
  documents now distinguish Phase-2a from the full-scale E26 Phase-2b evidence.
  Historical snapshots remain explicitly marked as provenance.
- `docs/manuscript/appendix.md` and `docs/supplementary/supplementary_materials.md`
  retain old tables under historical-status notes; they are not active evidence.
- `experiments/EXPERIMENT_GUIDE.md` points current experiments to v6/v6-era
  output directories even though the active Phase-2b and listing artifacts are
  in v8.
- The experiment guide's historical output paths remain a documentation cleanup
  item; the active release paths are defined by `DATA_CANONICAL.md` and the
  manifest.

**Consequence:** active evidence is now routed through the manifest, canonical
data policy, claim map, and manuscript. Historical review files remain useful
as an audit trail but are not release evidence. Independent proof review,
held-out preregistration, and final clean-checkout replication remain open
publication requirements.

### F4. Theory requires independent proof audit

The following results must not be treated as equally secure:

- The LBL emptiness result is a conditional structural statement and should be
  stated with its exact generator assumptions. The current Universal generator
  may emit overlapping CNOTs within a layer, so the prose “one gate per qubit per
  layer” is not literally true for every generated instruction list.
- The WCL expectation formula is an ensemble-specific calculation. It needs a
  direct pair-count experiment and a formal statement of gate sampling,
  two-qubit-pair sampling, and listing validity.
- The McDiarmid bound in Theorem 5 needs a careful dependency and bounded-difference
  audit. The number of independent random choices and the effect of changing one
  choice must match the generator exactly.
- The Haar-random incompressibility theorem is not a direct explanation of the
  shallow finite-gate-sequence experiments. The manuscript acknowledges this, but
  the theorem should be demoted to contextual background unless a specialist
  complexity review validates every measure/dimension step.
- The Phase-1 insertion and stochastic-optimizer claims require a precise move
  closure definition. “Cannot systematically exceed” is weaker than a universal
  upper bound and must be stated accordingly.

**Optimal response:** retain only formally audited statements as theorems in the
main paper; label the remainder as lemmas, empirical observations, conjectures,
or open problems. Do not attempt to repair a proof by prose alone.

### F5. Canonical data and current source code are different evidence layers

The manifest reports source-hash drift for E12-E21 and E25. This is not evidence
of data tampering; it means the canonical outputs were generated by earlier
source snapshots. The current repository contains rerun/reconciliation evidence
under `data/v9/`, including substantive E18 divergence and E21/E14 differences.

**Required paper language:** canonical datasets are frozen historical evidence;
current-code reruns are a separate validation layer; numbers must never be mixed
without a versioned reconciliation table. A clean release should include the
source commit used for every primary table or a reproducible source snapshot.

## Manuscript-Readiness Checklist

| Requirement before submission | Status | Required action |
|---|---|---|
| Single precise title and central claim | Needs revision | Rename around representation-conditioned peephole ceilings; remove “columnar representation example” wording |
| Current literature search | Ledger reconstructed; catalog corrections propagated | Verify at least 3 independent sources for each novelty claim; complete remaining primary-source checks before submission |
| Falsifiable hypotheses | Present but post hoc | Label as post-registered/reanalysis; add a genuinely held-out preregistered phase |
| Theory proof audit | Automated audit complete; external review open | Obtain independent quantum-compilation/complexity review; downgrade unsupported theorems |
| Direct theory-experiment alignment | Partial | Separate Phase-2a, Phase-2b, and full-pipeline results in every table |
| Baselines | Three production compilers present; independent optimizer review open | Keep Qiskit, Cirq, and t|ket> settings explicit; VOQC/Quartz remain unavailable on this environment |
| Realistic hardware validation | Missing | Optional for a software venue; required for any hardware-impact claim. Current EHW is simulator-only |
| Statistical plan | Mostly present | Add cluster-aware treatment of repeated circuits/seeds, pre-specify primary endpoints, and report CIs/effect sizes rather than only p-values |
| Fidelity correctness | Fixed for future runs | Recalibrate or exclude historical rows produced through the old product-state fallback |
| Missingness and survivorship | E18 documented | Keep ITT/MNAR sensitivity as primary; never foreground survivor-only means |
| Held-out generalization | Fails for some mechanisms | Present the failure as a boundary; do not market the model as universal |
| Data manifest | Passing | Re-run after any canonical-data decision; do not regenerate for non-canonical corrected reruns |
| Reproducible clean checkout | Pending final commit gate | Commit source/data/docs, then run tests/verify/figures from the resulting clean checkout |
| Data/code availability | No public archive or repository URL is currently verified | Assign a real public archive URL and DOI after deposit; do not cite the former 404 placeholder |
| Author declarations | Placeholder | Complete authors, contributions, funding, conflicts, and acknowledgements before submission |
| Figure QA | Partial | Render all PDFs, inspect fonts/labels/captions, and ensure every figure maps to current canonical data |
| Independent replication | Missing | Ask a separate researcher to run the clean-checkout protocol and reproduce headline tables |

## Highest-Value Experimental Program

The project should not run every historical experiment again. The optimal
publication program is a small, preregistered, mechanism-focused extension:

1. **Representation factorial:** same circuit instances crossed with LBL, valid
   WCL/topological listings, random valid topological listings, and DAG/compiler
   representations. Record unitary hashes before/after listing conversion and
   count action-space opportunities directly.
2. **Rewrite-library factorial:** Phase-1, Phase-2a, Phase-2b, parity/phase-
   polynomial baseline, and production compilers. Keep the circuit instances,
   seeds, timeout, basis, and cost function identical.
3. **Held-out families:** freeze training families before generating QPE,
   Trotter, QuantumVolume, W-state, repetition-code, and at least one external
   benchmark family. Do not select mechanisms after seeing held-out results.
4. **Cost-vector analysis:** report total gates, two-qubit gates, depth, T-count,
   compilation time, and noise-model output divergence separately. Do not infer
   hardware benefit from total gate count alone.
5. **Exactness tiers:** use exact operator fidelity where feasible; use global
   Haar Monte Carlo with uncertainty for larger circuits; use a scalable formal
   or tensor-network certificate where claims require exact equivalence.
6. **Independent rerun:** give the protocol and clean commit to an independent
   operator. Treat any discrepancy as a result, not as an inconvenience.

## Implementation Work Completed in This Audit

- Added deepwork progress tracking under `.slim/deepwork/` and ignored it from
  the repository release.
- Attempted four independent specialist review lanes; runtime model aliases were
  unavailable, so the main-thread audit is explicitly marked as fallback.
- Detected and documented machine resources: 4 physical CPU cores, 3.07 GB
  available RAM, no GPU; future runs must be bounded and checkpointed.
- Ran syntax compilation successfully.
- Ran the complete test suite: 317 tests passed; only dependency deprecation warnings remain.
- Replaced the invalid product-state fidelity fallback with global Haar sampling.
- Added fidelity fallback calibration script, artifacts, and regression test.
- Added zero-inflated inference summaries, P7 monotone-bound diagnostics, and P10 E30 distribution diagnostics with tests and derived artifacts.
- Fixed the E20 Cirq pipeline and completed a 1,070-row non-canonical corrected rerun under `data/v11/e20_corrected/`.
- Added the non-canonical E31 listing x Phase-2b smoke pilot, paired analysis, and explicit residual-scope report under `data/v11/e31_listing_phase2b/`.
- Regenerated the figure suite successfully: 19 one-page PDF artifacts (18
  numbered figures plus `fig08b`), with no zero-byte files and no `/Type3` font
  markers in the PDF byte streams. Visual spot review of every panel is still a
  human submission step.

## Safe Cleanup Policy

### Retain

- Canonical datasets listed in `release/release_manifest.json`.
- Derived analysis artifacts referenced by the manuscript or data dictionary.
- `data/v9/` rerun and reconciliation artifacts until the active evidence map is
  updated; they explain source drift and should not be discarded as “temporary.”
- Experiment drivers, tests, theory notes, and archived manuscript fragments
  that preserve provenance.

### Delete after final hash verification

- Python `__pycache__/` directories and `*.pyc` files.
- `.omo/` local agent session state.
- Timestamped `.bak-*` files whose prior contents are recoverable from Git or a
  retained canonical/rerun file.
- `partial_backup_20260721_broken.csv` after confirming it is parser-invalid and
  not the only copy of any completed row.

### Do not delete blindly

- `data/v9/*_partial/`, `deferred.json`, and checkpoint scripts: they encode
  incomplete or intentionally deferred computations.
- Historical `docs/review/wave*` files: keep as audit trail, but mark them as
  historical and do not use them as active evidence.
- Any untracked analysis/data file created by the user until it is either
  promoted to canonical evidence or explicitly classified as disposable.

## Release Gate

The project is release-ready only when all of the following commands pass from a
clean checkout and the outputs are archived:

```text
python -m pytest tests/ -q
python -m compileall -q src experiments scripts analysis
python scripts/reproduce_all.py --verify
python analysis/generate_figures.py
python scripts/characterize_fidelity_fallback.py --n-values 3 5 8 --samples 1000
```

The final manuscript must cite the exact release commit and manifest, identify
all approximate fidelity rows, distinguish simulator from hardware evidence,
and include the full negative/failed results.
