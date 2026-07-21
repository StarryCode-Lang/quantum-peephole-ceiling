# E24 — Theorem 7 Hardness Family Validation

**Canonical dataset**: `e24_theorem7_results.csv` (75 rows) — per-trial results
for the Theorem 7 hardness family at n = 4..12 (step 2), 5 trials per size.

## derived/

| File | Role | Rows |
|------|------|------|
| `derived/e24_theorem7_summary.csv` | Per-(n_qubits, optimizer) mean/min reduction aggregate | 15 |

Produced by `experiments/e24_theorem7/run.py` together with the canonical CSV;
archived under `derived/` on 2026-07-20.

Key result (see `metadata.json`): mean Phase-2a reduction 79.8% (all sizes meet
the 1/6 bound); Phase-1 = 0%; Phase-2b 2.5% (does not meet the bound at all
sizes).
