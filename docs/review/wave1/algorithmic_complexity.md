# Wave-1 Completion Report — Algorithmic Complexity & Ablation (Worker: 算法分析师_Alg)

> **Date**: 2026-07-20
> **Domain**: Algorithmic Complexity & Ablation
> **Main deliverable**: `docs/analysis/algorithmic_complexity.md`
> **Validation**: `pytest tests/test_optimizers.py tests/test_ceiling_aware.py -q` → **62 passed** (baseline 469.89s, post-change 265.87s, EXIT=0)

## 1. Work completed

### (1) Formal complexity docstrings — done

Added per-step and overall time/space complexity (with shared notation
`m/n/d/a/I/P/G/N/w/k/F` defined once in `BaseOptimizer`) to:

| File | What was added |
|---|---|
| `src/optimisation/base.py` | `BaseOptimizer` class-level shared complexity model (predicates O(1), exact fidelity `O(m·4^n+8^n)`/`O(4^n)`, sampling `O(S·m·2^n)`, moves `O(m)`, `_fitness` `O(F+m)`); `calculate_fidelity` complexity paragraph incl. the E21 mcx-fidelity cost caveat |
| `src/optimisation/phase1/greedy.py` | `O((c+1)·m)` per pass, 1–3 passes typical, `O(m³)` pathological, `+O(m log m)` with WCL |
| `src/optimisation/phase1/simulated_annealing.py` | `O(I·(m+F))` with E04 measured dominance note |
| `src/optimisation/phase1/genetic_algorithm.py` | `O(G·P·(m+F))` + `O(P·m)` init |
| `src/optimisation/phase1/random_local_search.py` | `O(I·N·(m+F))`, early-stop note |
| `src/optimisation/phase1/wire_traversal.py` | `O(m log m)` time / `O(m)` space (matches manuscript §3.3) |
| `src/optimisation/ceiling_aware.py` | **Docstring only** (no logic touched): proxy `O(m)`/`O(m·w)`, measured slopes 0.98–1.06, instance-dependent speedup caveat |
| `src/optimisation/_gate_predicates.py` | Module-level O(1)-per-predicate note |

### (2) Ablation contribution tables — done (all from canonical CSVs, no re-runs)

Main doc §4: E04 (400 rows, `data/v2_fixed/e04/…20260613_132653.csv`), E10
phase1-vs-phase2 (1,905 rows, `data/v5/e10/…131601.csv`: Phase-2a marginal gain
+15.97 pp RandomClifford, +2.99 pp Universal, 0 elsewhere; hybrid = union),
E22 gate-shuffle (2,240 rows, `data/v7/e22/`: original 6.30% / shuffle 10.34% /
WCL 12.20% for greedy; H0 rejected), E29 multi-seed (800 rows, `data/v7/e29/`:
hybrid +4.69% only positive; rls −176.5%, sa −22.2%, ga −8.3% — circuit growth
under the cancellation-potential fitness bonus; seed-to-seed std ≤ 2.3 pp).

### (3) Ceiling-aware O(m) runtime + speedup verification — done

- Proxies measured linear: log-log slopes **0.99** (`count_phase1_actions`),
  **1.06** (`count_phase2_actions`); full pipeline on reducible CNOT chain
  **0.98** (main doc §2; raw `docs/analysis/_alg_complexity_runtime_partA.csv`).
- E21 claim verification from the canonical 1,140-row file (main doc §3.1):
  - min 1.61× / max 227.80× → **1.6×–228× confirmed**;
  - "mean 35×" confirmed **only as aggregate** `Σt_naive/Σt_ca = 34.97×`
    (matches `e21_paired_summary.json`); unweighted family-mean = 22.64×,
    per-trial mean = 41.80× / median = 3.40× — definition flagged;
  - bit-identical reductions confirmed for all 15 families;
  - "executes only 28% of passes" (`manuscript.md:552`) **not reproducible**:
    6.4–10.0% under all accountings tried → flagged for integration.
- New finding (main doc §3.2): E21 naive timings include per-phase exact
  fidelity for n ≤ 6 while ceiling-aware's recorded `total_time_ms` excludes
  its final fidelity call (recorded before it). One fidelity call on mcx-heavy
  QuantumWalk n=6 = **2,124.9 ms** (measured, exact E21 seed) — the 228× upper
  endpoint is mostly avoided-verification cost. With symmetric target=None
  accounting (72 paired live runs): family speedups 0.97×–11.48×, aggregate
  2.20×, reductions still bit-identical (main doc §3.3, raw partB CSV).

### (4) Template-matcher wall clock (measure-only) — done

Measured against the current v2.0.0 rewrite (Phase-2b worker landed it
mid-wave; re-measured after their change): scan slope vs m **0.99**
(RandomClifford), mass-cancellation series **1.38** (list-pop `O((c+1)·m)`
term, same worst case as greedy), fixed-m n-independence confirmed
(t/(k·m) = 1.92–1.97 µs flat for n=6→18) → measured model is `O(k·m)` per
pass; `O(k·n·gates)` is a conservative over-estimate (main doc §5, raw partC
CSV). BV full pipeline slope 1.94 vs m (commutation-gathering dominated).

### (5) Analysis document — done

`docs/analysis/algorithmic_complexity.md`: complexity table (7 optimizers +
template matcher), ablation tables, speedup verification, E22/E29 summaries,
full source index with file:line citations (§6).

## 2. Files changed (all inside owned scope)

**Modified (docstrings only, no logic):**
- `src/optimisation/base.py`
- `src/optimisation/_gate_predicates.py`
- `src/optimisation/ceiling_aware.py` (docstring-only, per assignment)
- `src/optimisation/phase1/{greedy,simulated_annealing,genetic_algorithm,random_local_search,wire_traversal}.py`

**Created:**
- `docs/analysis/algorithmic_complexity.md` (main deliverable)
- `docs/analysis/_alg_complexity_data_probe.py` (canonical-CSV summarizer)
- `docs/analysis/_alg_complexity_runtime_measure.py` (Parts A/B/C measurements)
- `docs/analysis/_alg_complexity_runtime_part{A,B,C}.csv` (raw measurements)
- `docs/review/wave1/algorithmic_complexity.md` (this report)

No experiment scripts were modified (canonical data sufficed for all tables).
`src/optimisation/phase2/`, `experiments/phase2b_full_validation.py`, and
`docs/manuscript/manuscript.md` were not touched. No git mutations.

## 3. Verification commands & results

```
PY=/d/Downloads/miniforge3/python
# baseline (before docstring edits): 62 passed in 469.89s
$PY -m pytest tests/test_optimizers.py tests/test_ceiling_aware.py -q
# after edits: 62 passed in 265.87s  (EXIT=0)
$PY -m pytest tests/test_ceiling_aware.py -q          # 17 passed in 0.77s (fast loop check)
# imports + factory smoke: all 8 edited modules import; create_optimizer OK
# measurements:
$PY docs/analysis/_alg_complexity_runtime_measure.py A|B|C
$PY docs/analysis/_alg_complexity_data_probe.py e04|e10|e21|e22|e29
```

## 4. Unresolved gaps / hand-offs for other workers

1. **"mean 35×" definition**: canonical data supports 35× only as aggregate
   `Σt_naive/Σt_ca` (34.97×); family-mean is 22.64×. Integration worker should
   pin the definition in `manuscript.md:71,552,616,670`.
2. **"28% of passes" (`manuscript.md:552`)**: not reproducible from the
   canonical 1,140-row file (actual 6.4–10.0%). Recommend recompute or delete.
3. **E21 timing asymmetry (fidelity accounting)**: naive phase times include
   per-phase exact fidelity (n ≤ 6), ceiling-aware `total_time_ms` excludes
   its final fidelity call. The 228× QuantumWalk figure is mostly
   avoided-verification cost; verification-free re-measurement gives 1.9× for
   that family (aggregate 2.20× on a 6-family subset). Manuscript should state
   the protocol explicitly. Related: `fidelity_source` labels n=8/10 rows
   "exact_average_gate_fidelity" although target=None (label overstates;
   metadata `max_exact_fidelity_qubits: 12` is the module constant, argparse
   default was 6) — owner: E21/provenance worker.
4. **E29 circuit growth**: RLS −176.5% mean reduction (fidelity-compliant)
   traces to the cancellation-potential fitness bonus (`base.py:775-787`);
   fitness-design decision belongs to theory/optimizer workers, not changed here.
5. **Template-matcher full-pipeline exponent**: BV range too small (m 14→45)
   for a reliable asymptotic slope of `optimize_full_pipeline` (1.94 observed);
   suggest a dedicated sweep if the manuscript needs it (Phase-2b worker).
6. C3 mass-cancellation pop term (slope 1.38): documented as the `O((c+1)·m)`
   worst case; if a strictly linear matcher is desired, that is a code change
   for the Phase-2b worker (out of my measure-only mandate).
