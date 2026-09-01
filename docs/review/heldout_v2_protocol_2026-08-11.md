# Held-out v2 sealed-input protocol

## Purpose and boundary

This supplement increases the number of genuinely independent generator
mechanisms without adding seeds to an existing family. It is an outcome-blind
input stage only. No optimizer result may be generated or inspected before the
manifest, fixed-model predictions, generator audit, and `SEALED.json` exist.

The classifier, 12 features, imputation statistics, scaling statistics,
coefficients, intercept, and probability threshold are copied byte-for-byte
from the v1 sealed model. Re-fitting, threshold adjustment, feature selection,
and family removal after generation are prohibited.

## Design

- Eight new generator mechanisms are declared in
  `experiments/heldout_v2_protocol.json`; their family names, mechanism IDs,
  rationales, and normalized source-AST hashes must not duplicate the training
  or v1 held-out generators.
- Each family has `n={4,6,8}` and eight independent instances per size: 192
  execution rows and, by hard gate, 192 distinct normalized circuit hashes.
- The new hashes must have zero intersection with the fixed 520-input training
  manifest and the v1 held-out manifest.
- Deterministic generators that merely repeat the same circuit across seeds are
  rejected before sealing. Renaming a generator or changing only its seed does
  not create a new outer unit.
- Structural features and predictions are computed before any optimizer is
  allowed to consume the new manifest. The seal records UTC time and SHA-256 of
  the protocol, source, manifests, features, model, predictions, and overlap
  audit.

## Analysis boundary for the later outcome stage

The existing eight held-out families remain a separate first sealed cohort.
The v2 cohort adds eight outer generator units. A later analysis may report v2
alone and a prespecified cohort-stratified combination, but must not re-fit the
classifier or select families based on outcomes. Inner repeats cannot substitute
for the 16 total outer families.

Under the rough `1/sqrt(K)` approximation, increasing outer clusters from 8 to
16 reduces sampling-driven interval half-width by about 29% (`sqrt(8/16)`), if
between-family heterogeneity and class identifiability remain comparable. This
is a planning expectation, not a promised confidence interval; an adverse or
single-class family mix can widen or make MCC intervals non-identifiable.
