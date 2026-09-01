# E31 host-environment limitation and temporal sensitivity plan (2026-08-24)

Status: pre-analysis operational disclosure. This document does not alter the
frozen treatment design, delete observations, or license a result claim.

## Observed limitation

The frozen machine-readable protocol requires one worker, one thread, a cold
process per cell, an end-to-end timeout, and a 3072-MB process-tree cap. It does
not claim an otherwise idle or continuously exclusive host. The formal runner
rejects pytest, another formal runner, or another E31 worker at startup, but it
does not continuously record or prohibit processes launched later.

During the resumed 2026-08-24 execution, local audit and targeted test commands
were run after the formal runner had started. No continuous host CPU, memory
pressure, or process telemetry was recorded, so host exclusivity cannot be
reconstructed or asserted after the fact.

## Scientific consequence

- Semantic validity and circuit outputs remain subject to the frozen input,
  treatment, hash, and exact-equivalence gates.
- Wall time, timeout, and peak-memory results are conditional on this recorded
  shared Windows host. Transient load can add noise and may change whether a
  boundary cell reaches its timeout.
- The frozen run order is a seeded random permutation, so later host activity
  was not deliberately assigned to a treatment. That reduces the likelihood of
  systematic treatment bias but does not prove its absence.
- No row will be removed or rerun because of its observed outcome.

## Predeclared post-run diagnostic

The formal analysis will split the complete run order into 20 contiguous blocks
and report quality, validity, timeout, wall-time, and peak-RSS means. For each
outcome it will also report block means after adjustment for the saturated
72-cell treatment and input-hash mean, with a within-block residual standard
error. Before formal completion, the following descriptive drift-screen
thresholds are fixed:

- quality ITT adjusted residual: 1 percentage point (the frozen MCID);
- validity or timeout adjusted residual: 5 percentage points;
- wall-time/budget adjusted residual: 5 percentage points;
- peak-RSS adjusted residual: 128 MB.

Exceeding any threshold produces `REVIEW_REQUIRED`; otherwise the screen reports
`NO_THRESHOLD_EXCEEDED`. These are sensitivity thresholds, not hypothesis tests
or multiplicity-adjusted significance claims. The analysis packet must state that this
is an observational temporal sensitivity analysis, not proof of host
exclusivity, and the release verifier will reject any stronger claim.

If the diagnostic shows material temporal drift, resource and Pareto conclusions
will be downgraded to shared-host descriptive evidence or an independently
scheduled exclusive-host replication will be required. A null diagnostic will
not be described as proof that no interference occurred.
