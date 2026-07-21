# E29 — Multi-Seed Re-run of E04 (Full)

**Canonical dataset**: `e29_multi_seed_e04_full.csv` (800 rows) — E04 algorithm
comparison extended from a single seed (42) to 10 independent seeds
(42..942), 20 trials per seed, 4 optimizers (hybrid, rls, sa, ga), paired
circuit design (all optimizers see the same circuit per trial).

## derived/

| File | Role | Rows |
|------|------|------|
| `derived/e29_multi_seed_statistics.csv` | Per-optimizer aggregate: mean/std/median/min/max reduction, bootstrap 95% CI, per-seed spread | 44 |

Produced by `experiments/multi_seed_e04.py`; archived under `derived/` on
2026-07-20.

**Supersedes**: `data/v6/e29_multi_seed_e04/` (smoke: 2 seeds, 80 rows), which
is marked `superseded` in `release/release_manifest.json`.

Closes review gap: "E04 uses single seed (seed=42)" — provides confidence
intervals and seed-effect testing.
