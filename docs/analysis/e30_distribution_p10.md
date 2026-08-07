# P10 E30 Distribution Check

## Scope

E30's release claim compares mean adjacent-inverse-pair counts with the corrected Theorem 1(a) expectation. `analysis/e30_distribution_validation.py` adds a discrete Poisson goodness-of-fit diagnostic for the aggregate `a_adj_raw` count in each of 27 cells.

## Protocol

Each cell has 500 trials. Expected frequencies below five are merged before a Pearson chi-square diagnostic. The theoretical mean is fixed from `e30_thm1a_cell_summary.csv`; it is not estimated from the same observations. Benjamini-Hochberg correction covers the 27 cell-level p-values.

## Result

- 27/27 cells testable.
- Median raw p-value: `0.363703`.
- BH-rejected cells at `q = 0.05`: `0/27`.
- Raw p-values below `0.05`: present in individual cells, none survives BH correction.
- Wire-level independence: not tested. E30 stores aggregate counts, not per-wire pair indicators.

## Interpretation

E30 supports the Poisson-like aggregate count model at the declared cell level after multiplicity correction, but it does not establish independence of pair indicators across wires. The active manuscript should retain the mean/z-score validation as primary and cite this result as a distribution diagnostic, not as a complete stochastic-process proof.

Generated artifacts:

- `data/v10/e30/derived/e30_distribution_validation.csv`
- `data/v10/e30/derived/e30_distribution_validation.json`
