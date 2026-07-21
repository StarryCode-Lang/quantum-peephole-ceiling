# Effect Size Report

Bootstrap 95% CIs (10,000 resamples, percentile method) on the difference of means, with Cohen's d (parametric) and Cliff's delta (non-parametric). Positive Cohen's d / positive bootstrap difference means group 1 has the larger mean reduction.

Source data: `effect_sizes.csv`

## Key Comparisons

| Comparison | Exp | mean_1 | mean_2 | Cohen's d | Hedges' g | Glass's Delta | Cliff's delta | Bootstrap 95% CI (diff) | n_1 | n_2 |
|---|---|---|---|---|---|---|---|---|---|---|
| Greedy vs RLS | E4 | 0.0000 | 0.0000 | +nan (undefined (zero variance)) | +nan | +nan | +0.000 (negligible) | [+0.0000, +0.0000] | 100 | 100 |
| Greedy vs SA | E4 | 0.0000 | -0.0155 | +0.679 (medium) | +0.677 | +0.480 | +0.280 (small) | [+0.0096, +0.0221] | 100 | 100 |
| Greedy vs GA | E4 | 0.0000 | -0.0023 | +0.378 (small) | +0.376 | +0.267 | +0.070 (negligible) | [+0.0007, +0.0040] | 100 | 100 |
| Phase-1 vs Phase-2a | E10 | 0.0082 | 0.0593 | -0.619 (medium) | -0.619 | -0.670 | -0.547 (large) | [-0.0599, -0.0414] | 635 | 635 |
| Random vs Structured | E14 | 0.0700 | 0.0679 | +0.010 (negligible) | +0.010 | +0.009 | +0.228 (small) | [-0.0161, +0.0204] | 210 | 1920 |
| WCL vs LBL | E19 | 0.0783 | 0.0000 | +2.802 (large) | +2.802 | +1.981 | +0.927 (large) | [+0.0772, +0.0794] | 5000 | 5000 |

## Magnitude conventions

- **Cohen's d / Hedges' g / Glass's Delta**: negligible < 0.2, small 0.2-0.5, medium 0.5-0.8, large >= 0.8
- **Cliff's delta**: negligible < 0.147, small 0.147-0.33, medium 0.33-0.474, large >= 0.474
- **Glass's Delta denominator**: SD of group 2 (baseline); falls back to group 1 SD when group 2 has zero variance (e.g., LBL Phase-1).

## Supplementary Comparisons (E14 per-family)

| Comparison | Exp | mean_1 | mean_2 | Cohen's d | Hedges' g | Glass's Delta | Cliff's delta | Bootstrap 95% CI (diff) | n_1 | n_2 |
|---|---|---|---|---|---|---|---|---|---|---|
| Random vs Adder | E14 | 0.0700 | 0.0000 | +0.791 | +0.790 | +0.632 | +0.362 | [+0.0553, +0.0853] | 210 | 120 |
| Random vs CNOT | E14 | 0.0700 | 0.6667 | -1.840 | -1.836 | -1.262 | -0.546 | [-0.6697, -0.5230] | 210 | 165 |
| Random vs GHZ | E14 | 0.0700 | 0.0000 | +0.844 | +0.842 | +0.632 | +0.362 | [+0.0555, +0.0852] | 210 | 165 |
| Random vs Grover | E14 | 0.0700 | 0.0354 | +0.370 | +0.369 | +0.680 | +0.040 | [+0.0172, +0.0519] | 210 | 120 |
| Random vs HardwareEfficient | E14 | 0.0700 | 0.0000 | +0.844 | +0.842 | +0.632 | +0.362 | [+0.0555, +0.0852] | 210 | 165 |
| Random vs IQP | E14 | 0.0700 | 0.0020 | +0.817 | +0.815 | +6.521 | +0.337 | [+0.0533, +0.0834] | 210 | 165 |
| Random vs Oracle | E14 | 0.0700 | 0.0932 | -0.175 | -0.174 | -0.149 | +0.005 | [-0.0515, +0.0044] | 210 | 165 |
| Random vs QAOA | E14 | 0.0700 | 0.0000 | +0.844 | +0.842 | +0.632 | +0.362 | [+0.0555, +0.0852] | 210 | 165 |
| Random vs QFT | E14 | 0.0700 | 0.0000 | +0.844 | +0.842 | +0.632 | +0.362 | [+0.0555, +0.0852] | 210 | 165 |
| Random vs QuantumWalk | E14 | 0.0700 | 0.0000 | +0.791 | +0.790 | +0.632 | +0.362 | [+0.0553, +0.0853] | 210 | 120 |
| Random vs SurfaceCode | E14 | 0.0700 | 0.0000 | +0.844 | +0.842 | +0.632 | +0.362 | [+0.0555, +0.0852] | 210 | 165 |
| Random vs UCCSD | E14 | 0.0700 | 0.0028 | +0.758 | +0.756 | +6.445 | +0.317 | [+0.0524, +0.0824] | 210 | 120 |
| Random vs VQE | E14 | 0.0700 | 0.0000 | +0.791 | +0.790 | +0.632 | +0.362 | [+0.0553, +0.0853] | 210 | 120 |
