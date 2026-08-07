# P7 Monotone Mechanism Check

## Scope

P7 asks whether RepetitionCode's held-out failure can be replaced by a mechanism-derived monotone feature. `analysis/monotone_ceiling_p7.py` combines 570 E21 naive-pipeline rows with 122 deduplicated E27 rows. It does not change canonical data or claim that a fitted predictor is universal.

## Protocol

For action density `d`, the analysis evaluates `min(1, 2d)` as a lower-bound candidate. This bound is valid only when counted adjacent opportunities are non-overlapping and each removes two gates. The script therefore checks empirical violations instead of assuming the bound. It also evaluates one-dimensional isotonic regression by leave-one-family-out validation.

## Result

- 692 rows checked; zero empirical violations of `reduction >= min(1, 2d)`.
- Bound MAE across all rows: `0.0216444`.
- RepetitionCode density range: `0.232558` to `0.247934`.
- RepetitionCode bound MAE: `< 1e-15`.
- RepetitionCode structural-upper-bound MAE: `< 1e-15`.
- RepetitionCode isotonic LOFO MAE: `0.152230`.
- Isotonic pooled LOFO MAE: `0.072582`.

## Interpretation

The proposed mechanism feature closes the RepetitionCode failure as a deterministic bound, not as a learned predictive law. Isotonic regression does not solve the held-out family problem. The manuscript should retain RepetitionCode as a generalization boundary and cite the bound as an oracle/mechanism diagnostic. A theorem-level claim requires a formal non-overlap certificate for the opportunity counter and testing beyond this dataset.

Generated artifacts:

- `data/v6/ceiling_repair/p7_monotone_lofo.csv`
- `data/v6/ceiling_repair/p7_monotone_summary.json`
