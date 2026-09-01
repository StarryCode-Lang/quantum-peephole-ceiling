# E31 post-hoc family-inference correction

## Status

This correction was frozen on 2026-08-26 while the formal E31 execution was
still resumable and before a sealed formal result packet existed. It changes no
scheduled run, optimizer, timeout, resource cap, output circuit, or row-level
response. It is a post-hoc correction to the interpretation and computation of
uncertainty only. It cannot be relabelled preregistered or confirmatory.

## Defect and scope

The frozen protocol names `circuit_family` as the outer inference cluster for
estimand B and explicitly says that input rows cannot supply cluster degrees of
freedom. The legacy 71 treatment-coded factorial parameters and 30 disclosed
marginal contrasts were computed with `input_circuit_sha256`-clustered
covariance. That covariance addresses repeated treatment cells within an input,
but it does not provide the 15-family sampling uncertainty required for claims
about potentially unseen families.

Accordingly, the following legacy fields are invalid for inferential use in
both the 71- and 30-member tables:

- `cluster_robust_se_pp`
- `ci95_low_pp`
- `ci95_high_pp`
- `p_value_model_based`
- `holm_adjusted_p_within_role`

Their point estimates are not discarded. In the complete balanced 391 by 72
panel, they remain exact descriptive summaries conditional on the frozen input
panel. They must be exported separately with no confidence interval or p-value
and labelled `DESCRIPTIVE_POINT_ESTIMATE_ONLY`.

## Corrected estimands

The correction deliberately reports two different quantities:

1. **Fixed-panel description.** Each of the 71/30 effects is averaged over the
   391 frozen input hashes. This is input-weighted and conditions on the
   observed family composition. It has no design-based p-value or confidence
   interval because treatment assignment was not randomized.
2. **Supportive equal-family analysis.** The effect is first averaged over
   inputs within each circuit family and then averaged over the 15 family
   means. The ordinary model-based standard error is the sample standard
   deviation of those 15 means divided by `sqrt(15)`. The reference
   distribution is Student t with `15 - 1 = 14` degrees of freedom. This tier
   is model-based and nonconfirmatory because the 15 named families are not a
   probability sample of a defensible family super-population.

The 30 disclosed marginal contrasts retain their already disclosed Holm family
of size 30. The 71 treatment-coded parameters are a distinct exploratory Holm
family of size 71. Multiplicity adjustment does not convert either family into
confirmatory evidence.

## Small-cluster sensitivity

Each family-level table also reports a restricted Rademacher wild-cluster
bootstrap-t sensitivity with 19,999 draws and seed 20260826. The null is imposed
at zero and one common reproducible weight matrix is used across each contrast
family. The plus-one Monte Carlo correction is applied. With only 15 clusters,
this is a sensitivity analysis rather than a guarantee: it additionally relies
on an exchangeable, approximately sign-symmetric model for family effects.
Agreement between t(14) and the wild bootstrap strengthens robustness to the
small cluster count; disagreement must be disclosed and cannot be resolved by
selecting the smaller p-value.

## Primary A/B validity

- **Primary estimand A:** the exact 391-input point estimate and its comparison
  with the frozen 1 percentage-point MCID remain valid when computed from the
  sealed complete panel. There is still no design-based p-value or confidence
  interval. The family-stratified input bootstrap remains an empirical
  stability interval, not a design-based CI.
- **Primary estimand B:** the equal-family point estimate and its t(14) interval
  remain usable only as supportive model-based sensitivity. The new correction
  adds the reproducible wild-cluster p-value. No p-value or interval can make
  unseen-family language confirmatory: the protocol's generalized decision
  remains `BLOCK` because only 15 non-probability-sampled families exist.
- **The 71/30 tables:** none contains the single confirmatory A contrast. Their
  old input-cluster p-values and intervals are invalid; only their point
  estimates survive as fixed-panel descriptions.

## Executable evidence

The independent driver is `analysis/e31_posthoc_family_inference.py`. It fails
closed unless it receives exactly 391 unique input hashes, 15 families, and one
complete 72-cell panel per input. It writes separate fixed-panel, per-family,
and family-supportive tables plus a primary-validity audit. It does not import
or modify any frozen execution source. The machine-readable method contract is
`data/v11/e31_factorial_pareto/posthoc_family_inference_correction_gate.json`.

The driver must run only after the formal result CSV has been sealed. Until
then, this document and its tests establish the method correction, not an E31
scientific result.
