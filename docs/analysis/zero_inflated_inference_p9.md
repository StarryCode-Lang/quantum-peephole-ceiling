# P9 Zero-Inflated Inference Protocol

`analysis/phase1_statistics/zero_inflated.py` provides two explicit summaries:

- `summarize_zero_inflated`: finite sample size, zero count/rate, and conditional nonzero mean, median, and standard deviation.
- `compare_zero_inflated`: zero-rate difference and conditional nonzero mean/Cliff's-delta differences.

NaN and infinite values are excluded. Empty finite samples raise an error. No structural zero is imputed, and no Pearson correlation is substituted when a target has zero variance.

## Current release examples

| Dataset | Rows | Zero rate | Conditional nonzero mean |
|---|---:|---:|---:|
| E1 Phase-1 LBL | 25,000 | 1.0000 | not defined (no nonzero rows) |
| E19 WCL/LBL listing study | 10,000 | 0.5367 | 0.084486 |
| E22 gate shuffle | 2,240 | 0.6817 | 0.198776 |

E1 is therefore reported as a structural point mass, not as a failed variance estimate. Conditional summaries describe a different estimand and must not be mixed with the unconditional mean.
