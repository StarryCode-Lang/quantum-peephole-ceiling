# E31 Pareto aggregation limitation and sensitivity contract (2026-08-24)

Status: frozen before inspection of aggregate treatment effects. This document does not modify the running E31 design, execution order, budgets, outcomes, or ITT rules.

## Limitation

The frozen protocol names quality, semantic validity, wall time, peak RSS, and failure as Pareto objectives, but it does not preregister the across-input aggregation functional for wall time or peak RSS. The analysis implementation selected median wall time and P95 peak RSS. Those choices are scientifically defensible but post-hoc and therefore cannot be presented as preregistered confirmatory decisions.

Failure rate is exactly `1 - valid rate` under the frozen row contract, so it is reported but removed from hypervolume as a mathematically redundant axis.

## Frozen post-hoc analysis rule

The primary descriptive frontier uses mean ITT quality, valid rate, median wall time, and P95 peak RSS. It is explicitly exploratory and conditional on these aggregation choices.

Before release, the analysis must also compute all four aggregation schemes formed by:

- wall time: median and P95;
- peak RSS: median and P95.

For every scheme, all 72 treatment cells must be retained and dominance must be recomputed from the sealed 28,152-row ITT table. The sensitivity artifact must expose each cell's nondominated flag, domination counts, and dominance rate. No scheme may be selected after seeing which one favors a treatment.

## Permitted interpretation

Agreement across the four schemes supports robustness to these bounded aggregation choices. Disagreement requires scheme-specific reporting and blocks a single aggregation-invariant Pareto claim. Neither outcome identifies performance on unseen circuit families, hardware, hosts, or budgets.

