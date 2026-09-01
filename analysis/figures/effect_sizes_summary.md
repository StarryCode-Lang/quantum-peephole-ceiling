# Effect Size Report

Bootstrap 95% CIs (10,000 resamples, percentile method) on the difference of means. Paired experiments resample within-circuit differences and report Cohen's dz plus matched rank-biserial; independent experiments report Cohen's d and Cliff's delta.

Source data: `effect_sizes.csv`

## Key Comparisons

| Comparison | Exp | Design | mean_1 | mean_2 | Cohen's d/dz | Cliff's/matched rank-biserial | Bootstrap 95% CI (diff) | n_1 | n_2 |
|---|---|---|---|---|---|---|---|---|---|
| Greedy vs RLS | E4 | paired | 0.0000 | 0.0000 | +nan | +0.000 | [+0.0000, +0.0000] | 100 | 100 |
| Greedy vs SA | E4 | paired | 0.0000 | -0.0155 | +0.480 | +0.963 | [+0.0096, +0.0221] | 100 | 100 |
| Greedy vs GA | E4 | paired | 0.0000 | -0.0023 | +0.267 | +0.868 | [+0.0007, +0.0040] | 100 | 100 |
| Phase-1 vs Phase-2a | E10 | paired | 0.0082 | 0.0593 | -0.424 | -0.946 | [-0.0600, -0.0412] | 635 | 635 |
| Random vs Structured | E14 | independent | 0.0700 | 0.0679 | +0.010 | +0.228 | [-0.0161, +0.0204] | 210 | 1920 |
| WCL vs LBL | E19 | paired | 0.0783 | 0.0000 | +1.981 | +1.000 | [+0.0772, +0.0794] | 5000 | 5000 |

## Magnitude conventions

- **Cohen's d / Hedges' g / Glass's Delta**: negligible < 0.2, small 0.2-0.5, medium 0.5-0.8, large >= 0.8
- **Cliff's delta**: negligible < 0.147, small 0.147-0.33, medium 0.33-0.474, large >= 0.474
- **Glass's Delta denominator**: SD of group 2 (baseline); falls back to group 1 SD when group 2 has zero variance (e.g., LBL Phase-1).

## Supplementary Comparisons (E14 per-family)

| Comparison | Exp | Design | mean_1 | mean_2 | Cohen's d/dz | Cliff's/matched rank-biserial | Bootstrap 95% CI (diff) | n_1 | n_2 |
|---|---|---|---|---|---|---|---|---|---|
| Random vs Adder | E14 | independent | 0.0700 | 0.0000 | +0.791 | +0.362 | [+0.0553, +0.0853] | 210 | 120 |
| Random vs CNOT | E14 | independent | 0.0700 | 0.6667 | -1.840 | -0.546 | [-0.6697, -0.5230] | 210 | 165 |
| Random vs GHZ | E14 | independent | 0.0700 | 0.0000 | +0.844 | +0.362 | [+0.0555, +0.0852] | 210 | 165 |
| Random vs Grover | E14 | independent | 0.0700 | 0.0354 | +0.370 | +0.040 | [+0.0172, +0.0519] | 210 | 120 |
| Random vs HardwareEfficient | E14 | independent | 0.0700 | 0.0000 | +0.844 | +0.362 | [+0.0555, +0.0852] | 210 | 165 |
| Random vs IQP | E14 | independent | 0.0700 | 0.0020 | +0.817 | +0.337 | [+0.0533, +0.0834] | 210 | 165 |
| Random vs Oracle | E14 | independent | 0.0700 | 0.0932 | -0.175 | +0.005 | [-0.0515, +0.0044] | 210 | 165 |
| Random vs QAOA | E14 | independent | 0.0700 | 0.0000 | +0.844 | +0.362 | [+0.0555, +0.0852] | 210 | 165 |
| Random vs QFT | E14 | independent | 0.0700 | 0.0000 | +0.844 | +0.362 | [+0.0555, +0.0852] | 210 | 165 |
| Random vs QuantumWalk | E14 | independent | 0.0700 | 0.0000 | +0.791 | +0.362 | [+0.0553, +0.0853] | 210 | 120 |
| Random vs SurfaceCode | E14 | independent | 0.0700 | 0.0000 | +0.844 | +0.362 | [+0.0555, +0.0852] | 210 | 165 |
| Random vs UCCSD | E14 | independent | 0.0700 | 0.0028 | +0.758 | +0.317 | [+0.0524, +0.0824] | 210 | 120 |
| Random vs VQE | E14 | independent | 0.0700 | 0.0000 | +0.791 | +0.362 | [+0.0553, +0.0853] | 210 | 120 |
