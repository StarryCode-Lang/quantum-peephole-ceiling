# E21 — Ceiling-Aware Optimizer Comparison

**Canonical dataset**: `ceiling_aware_comparison.csv` (1,140 rows) — per-trial
comparison of the ceiling-aware optimizer vs the naive pipeline across 15
families, qubit sizes {4, 6, 8, 10}, 10 trials per configuration.

## derived/

| File | Role | Rows |
|------|------|------|
| `derived/ceiling_aware_summary.csv` | Per-family aggregate statistics | 30 |
| `derived/e21_paired_statistics.csv` | Paired statistical tests (per family) | 57 |

Both derived files are produced by `experiments/e21_ceiling_aware/run.py`
(summary) and `experiments/e21_ceiling_aware/analyze.py` (paired statistics)
from the canonical CSV. The generators write next to the canonical file when
re-run; the checked-in copies were archived under `derived/` on 2026-07-20.

**Status**: exploratory. The original held-out heuristic failed; the repaired
mechanism-gate + random-forest analysis improves per-circuit LOFO performance
but remains exploratory. The 20-family check exposes a RepetitionCode fold
failure, so family-mean generalization is not claimed. See
`docs/analysis/monotone_ceiling_p7.md`,
`docs/review/residual_issue_disposition_2026-08-07.md`, and manuscript §6.6.
