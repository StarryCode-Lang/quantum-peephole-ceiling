# E31 pre-analysis method erratum (2026-08-24)

## Status and timing

This erratum was written while the frozen E31 schedule was still running and
before the primary factorial contrast or any aggregate treatment effect had been
computed. At the audit boundary, 19,708 of 28,152 rows were checkpointed through
`run_order=19707`; the only inspected aggregate fields were execution status and
checkpoint continuity. The formal protocol and design manifest remain unchanged.

This is a mathematical correction to the interpretation of the planned analysis,
not an outcome-driven change to the treatment grid, estimand, MCID, inclusion
rules, failure semantics, or run order.

## Defect found

Every one of the 391 frozen input hashes receives every treatment cell. In
particular, both WCL and LBL are observed for each input. The seeded
`primary_pair_orientation` column does not assign either listing treatment to an
input; it is analysis metadata only. Therefore it cannot license a design-based
randomization test of the WCL-minus-LBL contrast.

The previously implemented family-restricted sign permutation compared the
observed, fixed-direction contrast with balanced artificial signs. The observed
assignment (all contrasts coded WCL minus LBL) is not a member of that assignment
mechanism. Its p-value consequently has no valid design-randomization
interpretation and must not be reported as confirmatory evidence.

## Corrected interpretation frozen before aggregate analysis

The primary estimand remains exactly the preregistered equal-weight mean over the
3-window by 4-budget grid of

`[(WCL-LBL)_COMMUTATION_PLUS_TEMPLATES -
  (WCL-LBL)_COMMUTATION_ONLY]`.

For estimand A, all potential treatment outcomes needed for this contrast are
observed on the complete frozen finite benchmark. The primary report will therefore
contain:

1. the exact finite-population mean contrast over all 391 unique input hashes;
2. its relation to the unchanged 1 percentage-point MCID;
3. the complete input- and family-level heterogeneity distribution, including
   worst family and leave-one-family-out results;
4. a family-stratified input bootstrap interval only as an empirical stability
   sensitivity analysis, explicitly not as a design-based confidence interval;
5. `design_based_p_value = null` and `design_based_confidence_interval = null`, with
   the reason recorded in machine-readable output.

The exact finite-benchmark effect can support a conditional statement about these
391 hashes under the frozen software and resource contract. It cannot support a
sampling-probability or unseen-family claim.

Estimand B remains an equal-family-weighted, family-cluster analysis using 15 family
means. It remains supportive only and formally blocked for confirmatory new-family
language by the prospective power gate. Its interval is model-based and must be
described as extrapolative because the benchmark families were not probability
sampled from a defined family population.

## Secondary-outcome deviation

The frozen protocol names `time_to_first_valid_seconds` and
`time_to_best_seconds`, but the worker records only total optimizer time and an
iteration trace without per-iteration timestamps. These outcomes cannot be
reconstructed without inventing timing information. They will be reported as
`NOT_MEASURED_IN_FROZEN_RUN`, not imputed or inferred from iteration number. The
available end-to-end wall time, optimizer time, peak RSS, validity, fidelity, and
gate-count outcomes remain analyzable.

## Guardrails

- No scheduled row may be removed because of this erratum.
- Timeout, OOM, error, invalid, and unavailable rows remain in the ITT denominator.
- The protocol, design, worker, optimizer, QASM inputs, resource cap, and MCID are
  not changed.
- The invalid randomization p-value is removed rather than replaced with a more
  favorable post-hoc test.
- Any additional factorial-model p-values are supportive or exploratory according
  to the original hierarchy and receive explicit multiplicity control.
- The final release manifest must include this erratum and the machine-readable
  analysis gate that binds to it.
