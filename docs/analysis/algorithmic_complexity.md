# Algorithmic Complexity & Ablation Analysis

> **Date**: 2026-07-20
> **Scope**: Formal time complexity of every optimizer; ablation contribution
> tables (E04, E10, E22/gate-shuffle, E29); ceiling-aware O(m) runtime
> measurement; verification of the E21 1.6x–228x (mean 35x) speedup claim;
> Phase-2b template-matcher wall-clock measurement (measure-only).
> **Intended consumer**: manuscript integration worker. Every table cites its
> source file and line/row counts. No experiment was re-run at scale; all
> ablation numbers come from canonical CSVs, plus three small measurement
> scripts documented below.

**Notation**: `m` = gate count (`len(circuit.data)`), `n` = qubits, `d = 2^n`,
`a` = max gate arity (≤ 2), `I` = `max_iterations` (default 100),
`P` = population (GA, default 10), `G` = generations (GA, default 10),
`N` = neighborhood size (RLS, default 5), `w` = commutation window (default 10),
`k` = number of templates (Phase-2b v2.0.0: 6 conjugation templates plus an
inverse-cancellation/phase-polynomial closure),
`F` = one exact fidelity evaluation = `O(m·4^n + 8^n)` time / `O(4^n)` memory
for `n ≤ 12` (`MAX_EXACT_FIDELITY_QUBITS`); sampled estimator
`O(S·m·2^n)` beyond that (`src/optimisation/base.py:212`).

---

## 1. Formal complexity per optimizer

Complexity docstrings were added to each optimizer (this wave). The shared
cost model lives in `BaseOptimizer` (`src/optimisation/base.py:126`); the
per-optimizer docstrings reference it.

| Optimizer | Per step | Overall (time) | Space | Source |
|---|---|---|---|---|
| Shared predicates (`_gates_commute`, `_is_self_inverse_pair`, …) | — | `O(a) = O(1)` per call (rule-based; numeric fallback bounded to 4×4 unitaries) | `O(1)` | `src/optimisation/base.py:126`, `src/optimisation/_gate_predicates.py:13-22` |
| `calculate_fidelity` (exact) | — | `O(m·4^n + 8^n)` (`n ≤ 12`); Clifford shortcut `O(m·n²)`; sampling `O(S·m·2^n)` (`n > 12`) | `O(4^n)` | `src/optimisation/base.py:212` |
| Move primitives (REMOVAL/SWAP/COMMUTATION/INSERTION) | `O(m)` scan + deepcopy | `O(m)` per neighbor | `O(m)` | `src/optimisation/base.py:594-705` |
| **GreedyGateCancellation** (Phase-1) | cancellation scan `O((c+1)·m)`, `c` = cancellations in pass; merge scan `O(m)` | `O(m)` per pass, 1–3 passes typical → `O(m)` typical; worst `O(m²)` per pass, `O(m³)` pathological; measured log-log slope ≈ 1.0 (Part A2) | `O(m)` | `src/optimisation/phase1/greedy.py:38-62` |
| **RandomLocalSearch** | `O(N·(m+F))` per iteration | `O(I·N·(m+F))`; early stop after 50 stagnant iterations | `O(N·m)` + fidelity | `src/optimisation/phase1/random_local_search.py:20-46` |
| **SimulatedAnnealing** | `O(m+F)` per iteration | `O(I·(m+F))` | `O(m)` + fidelity | `src/optimisation/phase1/simulated_annealing.py:21-44` |
| **GeneticAlgorithm** | `O(P·(m+F))` per generation (+`O(P·m)` init) | `O(G·P·(m+F))` | `O(P·m)` + fidelity | `src/optimisation/phase1/genetic_algorithm.py:32-63` |
| **WireTraversalPreprocessor** (WCL) | DAG `O(m)`; heap Kahn sort `O(m log m)` | `O(m log m)` | `O(m)` | `src/optimisation/phase1/wire_traversal.py:61-73`; matches `docs/manuscript/manuscript.md:233` |
| **Phase2aCommutationRewriter** (read-only this wave) | bubble-scan `O(m·w)` + `O(w)` commute checks per candidate | `O(I·m·w²)` worst, `O(m·w)` typical (manuscript statement) | `O(m)` | `docs/manuscript/manuscript.md:340`; `src/optimisation/phase2/commutation_rewriter.py` |
| **CeilingAwareOptimizer** | proxies `O(m)` / `O(m·w)` | `O(m·w)` + cost of executed phases only; measured pipeline slope 0.98 (reducible) / 0.99–1.06 (proxies) | `O(m)` | `src/optimisation/ceiling_aware.py:43-49,69-82,164` |
| **Phase2bTemplateMatcher** (measure-only) | `O(k·m)` per template pass (v2.0.0: k = 6 conjugation templates + cancellation/merging closure) | typical 1–3 passes → `O(k·m)`; worst `O(m)` passes with pop term → `O(k·m²)`; measured slope 0.99 (scan) / 1.38 (mass-cancellation pop term) vs m, **no n-dependence** | `O(m)` | `src/optimisation/phase2/template_matcher.py:126,156`; Part C below |

### 1.1 Why the stochastic optimizers are fidelity-bound

For `n ≤ 12` every `_fitness` call costs one exact fidelity evaluation
`O(m·4^n + 8^n)`, so RLS/SA/GA runtimes are dominated by matrix products, not
by circuit scans. Measured on E04 (n=5, m≈75, canonical 400-row file
`data/v2_fixed/e04/e04_algorithm_comparison_v2_20260613_132653.csv`):

| Optimizer | Mean runtime/trial | Fidelity calls per trial (approx.) |
|---|---|---|
| greedy | **2.29 ms** | 1 (final only) |
| sa | **2,384.84 ms** | I+2 ≈ 102 |
| rls | **6,152.98 ms** | I·N+2 ≈ 502 |
| ga | **7,255.10 ms** | G·P + crossovers ≈ 200+ |

This ~1000× gap is exactly the `F` term in the complexity table: it is the
empirical signature of `O(I·(m+F))` vs `O(m)`.

---

## 2. Ceiling-aware O(m) runtime — measured

Script: `docs/analysis/_alg_complexity_runtime_measure.py` (Part A);
raw data `docs/analysis/_alg_complexity_runtime_partA.csv`.
Median of 5–9 repetitions per point, `time.perf_counter`, target=None
(no fidelity cost, matching E21's large-n protocol).

### 2.1 Proxy scaling (A1: UNIVERSAL random circuits, n=5, depth sweep 10→320)

| m (gates) | proxy1 count | proxy2 count | t_proxy1 (ms) | t_proxy2 (ms) |
|---|---|---|---|---|
| 50 | 0 | 0 | 0.336 | 1.437 |
| 100 | 0 | 1 | 0.733 | 4.436 |
| 200 | 0 | 4 | 1.450 | 7.310 |
| 400 | 0 | 10 | 2.881 | 15.466 |
| 800 | 0 | 17 | 5.276 | 32.272 |
| 1600 | 0 | 34 | 10.723 | 64.552 |

**Log-log slopes vs m: proxy1 = 0.99, proxy2 = 1.06** → both confirmed linear
(proxy2's `O(m·w)` worst case behaves as `O(m)` at fixed w=10, as documented at
`src/optimisation/ceiling_aware.py:80-82`).

### 2.2 Full pipeline on a reducible family (A2: CNOT chain, n=6, repeats 4→128)

Phase-1 proxy > 0 (greedy runs), Phase-2a proxy = 0 (skipped).

| m (gates) | proxy1 | t_pipeline (ms) |
|---|---|---|
| 40 | 20 | 1.506 |
| 80 | 40 | 2.096 |
| 160 | 80 | 4.583 |
| 320 | 160 | 8.822 |
| 640 | 320 | 16.532 |
| 1280 | 640 | 44.609 |

**Log-log slope = 0.98** → the full ceiling-aware pipeline is measured `O(m)`
on reducible families. On circuits where Phase-2a actually executes (deep
UNIVERSAL circuits, Part A1 pipeline column), the slope rises to 1.76 — that is
the Phase-2a rewriter's own superlinear cost (`O(I·m·w²)` worst case), not the
proxy's.

---

## 3. E21 speedup claim verification (1.6×–228×, mean 35×)

Claim locations: `docs/manuscript/manuscript.md:71` (Contribution 3),
`docs/manuscript/manuscript.md:538-552` (Section, per-family table),
`docs/manuscript/manuscript.md:616`, `docs/manuscript/manuscript.md:670`.
Primary source data: `data/v6/e21/ceiling_aware_comparison.csv`
(**1,140 rows**, full mode, run_id `e21_full_20260709_085523`;
`data/v6/e21/metadata.json`), paired statistics
`data/v6/e21/e21_paired_summary.json` (moved to `data/v6/e21/derived/` by the
E21 owner worker during this wave; content unchanged).

### 3.1 Verification from canonical data (recomputed from raw rows)

| Family | Naive (ms) | Ceiling-aware (ms) | Speedup | Red. match |
|---|---|---|---|---|
| QuantumWalk | 1524.61 | 6.69 | **227.80×** | ✓ |
| HaarRandom | 138.05 | 8.42 | 16.39× | ✓ |
| QFT | 15.04 | 1.05 | 14.37× | ✓ |
| Adder | 11.04 | 0.98 | 11.28× | ✓ |
| SurfaceCode | 7.66 | 0.79 | 9.73× | ✓ |
| IQP | 15.25 | 1.71 | 8.93× | ✓ |
| VQE | 12.29 | 1.41 | 8.71× | ✓ |
| UCCSD | 18.39 | 2.25 | 8.17× | ✓ |
| QAOA | 12.52 | 1.54 | 8.11× | ✓ |
| HardwareEfficient | 13.04 | 1.68 | 7.78× | ✓ |
| Grover | 88.98 | 15.47 | 5.75× | ✓ |
| GHZ | 2.44 | 0.46 | 5.31× | ✓ |
| Oracle | 7.48 | 2.22 | 3.37× | ✓ |
| CNOT | 4.73 | 2.12 | 2.23× | ✓ |
| RandomClifford | 17.07 | 10.58 | **1.61×** | ✓ |

| Claim | Canonical recomputation | Verdict |
|---|---|---|
| min 1.6× | 1.61× (RandomClifford) | ✓ confirmed |
| max 228× | 227.80× (QuantumWalk) | ✓ confirmed |
| mean 35× | **34.97× as aggregate** `Σt_naive/Σt_ca` (matches `e21_paired_summary.json` `overall_speedup=34.9657`); unweighted family-mean = 22.64×; per-trial mean = 41.80×, median = 3.40× | ✓ confirmed **only under the aggregate definition** — flag definition for integration |
| bit-identical reduction | mean gate reduction identical per family for all 15 families (`np.isclose`, atol 1e-9); overall 0.09631 both (`e21_paired_summary.json`) | ✓ confirmed |
| "executes only 28% of the optimization passes" (`manuscript.md:552`) | per-circuit accounting: 10.0% (2 skippable phases) or 6.7% (3-phase incl. final cleanup); family-mean: 9.5% / 6.4% | ✗ **not reproducible** from the canonical 1140-row file under any accounting tried — flag for integration worker |

### 3.2 Measurement caveat — fidelity-cost asymmetry in E21 timings

E21's naive pipeline passes `target=circuit` for `n ≤ 6`
(`experiments/e21_ceiling_aware/run.py:318`), so each naive phase's
`optimize()` computes one exact fidelity internally, and that cost lands in
`phase*_time_ms`. The ceiling-aware pipeline skips those phases entirely, and
its own final fidelity call happens **after** `total_time_ms` is recorded
(`src/optimisation/ceiling_aware.py:294` vs `:297`).

Measured consequence (this wave, exact E21 seed 687126267,
`make_quantum_walk(6, steps=3, ...)`): a single
`BaseOptimizer.calculate_fidelity` call on the mcx-heavy QuantumWalk circuit
(24 `mcx` + 6 `ccx` gates) costs **2,124.9 ms** — vs 2.6 ms for the greedy
scan itself. E21's QuantumWalk n=6 naive rows (mean 5,746.6 ms, all three
phases ~1.5–2.9 s each, fidelity_source `exact_average_gate_fidelity`) are
therefore dominated by fidelity verification, while the ceiling-aware rows
(mean 3.58 ms) pay only the proxies. **The 228× upper endpoint is real on the
recorded protocol but is driven by avoided fidelity-verification cost, not by
avoided optimization-scan cost.** For n ≥ 8 (target=None in E21), the same
family shows naive 17.6/21.8 ms vs ca 6.7/14.4 ms ≈ 1.5–2.6×.

Related labeling caveat: `fidelity_source` is derived from the module constant
`MAX_EXACT_FIDELITY_QUBITS=12` (`run.py:129-134`), so n=8/10 rows are labeled
`exact_average_gate_fidelity` even though target=None made fidelity a
convention (1.0). Metadata `max_exact_fidelity_qubits: 12` is likewise the
module constant, not necessarily the run parameter (argparse default is 6).
Owner: E21/provenance worker — recorded here because it affects timing
interpretation.

### 3.3 Live re-measurement with symmetric accounting (Part B)

Same phase sequence as E21, but `target=None` everywhere so neither side pays
verification cost. 6 families × n ∈ {4,6,8,10} × 3 trials = 72 paired runs;
raw data `docs/analysis/_alg_complexity_runtime_partB.csv`.

| Family | Naive (ms) | Ceiling-aware (ms) | Live speedup | E21 canonical |
|---|---|---|---|---|
| QFT | 19.08 | 1.66 | **11.48×** | 14.37× |
| VQE | 6.83 | 2.27 | 3.01× | 8.71× |
| QuantumWalk | 11.63 | 6.10 | 1.91× | 227.80× |
| Oracle | 3.38 | 2.45 | 1.38× | 3.37× |
| RandomClifford | 10.39 | 10.10 | 1.03× | 1.61× |
| CNOT | 1.36 | 1.40 | **0.97×** | 2.23× |
| **aggregate** `Σn/Σca` | | | **2.20×** | 34.97× |

Gate reductions were bit-identical on all 72 paired rows (naive_red == ca_red).

**Interpretation for the manuscript**: with verification cost excluded, the
ceiling-aware pipeline still never loses (worst case 0.97× = proxy overhead on
a tiny 24-gate reducible circuit) and gains most where futile scans are long
(QFT 11.5×). The honest defensible wording is: *speedups are
instance-dependent; on the E21 protocol (including per-phase verification) the
range is 1.6×–228× with aggregate 35×; with verification-free accounting on a
6-family subset the range is 0.97×–11.5× with aggregate 2.2×; reductions are
bit-identical in both protocols.*

---

## 4. Ablation contribution tables

### 4.1 E04 — Phase-1 algorithm comparison (canonical, 400 rows)

Source: `data/v2_fixed/e04/e04_algorithm_comparison_v2_20260613_132653.csv`
(single base seed 42, 100 paired trials, UNIVERSAL n=5 depth=15;
`data/DATA_CANONICAL.md:20`).

| Optimizer | n | Mean reduction | Std | Mean fidelity | Mean runtime |
|---|---|---|---|---|---|
| greedy | 100 | 0.0000 | 0.0000 | 1.0000 | 2.29 ms |
| rls | 100 | 0.0000 | 0.0000 | 1.0000 | 6,152.98 ms |
| sa | 100 | **−0.0155** | 0.0322 | 1.0000 | 2,384.84 ms |
| ga | 100 | **−0.0023** | 0.0085 | 0.9999 | 7,255.10 ms |

Contribution summary: on LBL-listed random circuits no Phase-1 optimizer finds
any reduction (consistent with Theorem 1(b)); SA/GA slightly *grow* circuits
via INSERTION moves while preserving fidelity ≈ 1. Schema caveat: this file's
`success` column predates the bug-#5 semantics split (success = fidelity-only),
so it reads 0.0 everywhere (old stricter semantics) — do not compare with
E29's success column directly.

### 4.2 E10 — Phase-1 vs Phase-2 vs hybrid (canonical expanded, 1,905 rows)

Source: `data/v5/e10/e10_expanded_phase1_vs_phase2_20260613_131601.csv`
(`data/DATA_CANONICAL.md:22`). Mean gate reduction:

| Family | greedy_phase1 | commutation_phase2 | hybrid_phase1_2 | Phase-2 marginal gain |
|---|---|---|---|---|
| CNOT_chain | **1.0000** | 0.0000 | 1.0000 | +0.00 pp |
| RandomClifford | 0.0010 | **0.1585** | 0.1607 | **+15.97 pp** |
| Universal | 0.0000 | **0.0299** | 0.0299 | **+2.99 pp** |
| QFT / GHZ / BV / QAOA / VQE / HardwareEfficient / Structured | 0.0000 | 0.0000 | 0.0000 | +0.00 pp |

Contribution summary: Phase-1 alone captures 100% of the reducible-chain
regime; Phase-2a commutation is the *only* contributor on RandomClifford
(+15.97 pp) and Universal (+2.99 pp); hybrid = union of the two with no
measured synergy beyond the union (0.1607 ≈ 0.0010 + 0.1585). n per cell: 200
(RandomClifford/Universal/Structured), 5 (real families).

### 4.3 E22 — gate-order shuffle ablation (canonical v7, 2,240 rows)

Source: `data/v7/e22/e22_gate_shuffle_ablation.csv` (16 families × {original,
5 shuffles, wcl} × {greedy_phase1_lbl, commutation_phase2a};
`data/v7/e22/metadata.json`, seed 48). Overall mean reduction by listing model:

| Listing | greedy_phase1_lbl | commutation_phase2a |
|---|---|---|
| original | 0.0630 | 0.0387 |
| shuffle (mean of 5) | 0.1034 | 0.0270 |
| wcl | **0.1220** | 0.0100 |

Per-family highlights (greedy_phase1_lbl): BV 0.0000 (original) → 0.1972–0.2177
(shuffles) → **0.3349 (wcl)**; CNOT_chain 1.0000 (original) → 0.9200–0.9800
(shuffles) → 1.0000 (wcl). Phase-2a on BV: 0.2854 (original) → 0.0539–0.1178
(shuffles) → 0.0000 (wcl, because Phase-1 already captures the reduction).
All rows fidelity = 1.0 (min 0.9999999999997), success 100%.

Contribution summary: the listing model is a true causal variable — a random
commutation-preserving shuffle moves Phase-1 mean reduction from 6.3% to
10.3%, and structured WCL further to 12.2%; H0 (shuffle ≡ original) is
rejected by the spread between original/shuffle/wcl on BV and CNOT_chain.

### 4.4 E29 — multi-seed E04 (canonical v7, 800 rows)

Source: `data/v7/e29/e29_multi_seed_e04_full.csv` + `e29_multi_seed_statistics.csv`
(10 base seeds × 100 paired trials × 4 optimizers, UNIVERSAL n=5 depth=15;
`data/v7/e29/metadata.json`).

| Optimizer | n | Mean reduction (all rows) | Std | Seed-to-seed std of per-seed means | Mean fidelity |
|---|---|---|---|---|---|
| hybrid (Phase1+2a) | 200 | **+0.0469** | 0.0331 | 0.0054 | 1.0000 |
| ga | 200 | −0.0831 | 0.0318 | 0.0080 | 1.0000 |
| sa | 200 | −0.2215 | 0.0939 | 0.0215 | 1.0000 |
| rls | 200 | **−1.7653** | 0.1055 | 0.0233 | 1.0000 |

Per-seed means are stable (seed std ≤ 2.3 pp), so 10 seeds suffice for the
reported CIs. Contribution summary: across seeds, only the hybrid pipeline
achieves positive mean reduction (+4.69%, from the Phase-2a commutation term,
consistent with E10's Universal +2.99 pp); all three stochastic Phase-1
optimizers *grow* circuits (RLS worst: optimized_size ≈ 2.77× original)
because the cancellation-potential fitness bonus
(`src/optimisation/base.py:775-787`) rewards INSERTION moves that create
adjacent pairs without requiring realized reduction. Fidelity stays 1.0
throughout, so growth is fidelity-compliant — a fitness-design finding, not a
correctness bug. Note E29's larger negative reductions vs E04 (−0.0155 SA)
reflect the post-E04 fitness change; both are reported with their data
versions.

---

## 5. Phase-2b template matcher — wall-clock measurement (measure-only)

Claim under test: `O(k·n·gates)` cost model (k templates, n qubits, gates = m).
Script Part C; raw data `docs/analysis/_alg_complexity_runtime_partC.csv`.
Implementation measured: `src/optimisation/phase2/template_matcher.py`
**v2.0.0** (E26/v8 rewrite by the Phase-2b worker during this wave):
k = 6 conjugation templates plus an inverse-cancellation closure and
phase-polynomial merging (class at `template_matcher.py:126`, `optimize`
`:156`, `optimize_full_pipeline` `:195`, scan loop `_apply_all_templates`
`:311`, `_cancel_inverse_pairs` `:381`). No code was modified by this worker.

### 5.1 Scaling vs m

| Series | Setup | Slope (log-log vs m) |
|---|---|---|
| C1 | RandomClifford n=6, depth 5→160 (m 24→742) | **0.99** |
| C3 | CNOT chain n=6, repeats 8→256 (m 80→2560), mass CX-cancellation | **1.38** |

C1 confirms the linear scan cost. C3's superlinearity is the list-`pop(i)`
term: every cancellation is two O(m) list pops, so a pass with c cancellations
costs `O((c+1)·m)` — the same worst-case term documented for the greedy
optimizer; with c = Θ(m) on the CNOT chain this yields the observed ~1.4
exponent, not a scan-complexity violation.

### 5.2 n-dependence test (fixed m, vary n; v2.0.0)

| Series | n range | m | t/(k·m) spread |
|---|---|---|---|
| CNOT chain, fixed m = 640 | 6 → 21 | 640 | 1.88–2.00 µs (one 3.36 µs outlier at n=17, cancellation-cascade structure) |
| RandomClifford, fixed m ≈ 325–365 | 6 → 18 | 325–365 | **1.92–1.97 µs — flat** |

At fixed m the wall time per `(k·m)` unit is constant while n varies 3×:
**measured cost model is `O(k·m)` per pass, independent of n** — the per-gate
pattern checks are O(1) (≤2-qubit supports, `find_bit` dict lookups). The
`O(k·n·gates)` form is a conservative over-estimate; passes repeat until
fixpoint (typically 1–3; `O(m)` passes worst case → `O(k·m²)` pathological
bound including the pop term).

### 5.3 BV-oracle pipeline (templates fire)

`optimize()` on BV stays ~0.2–0.6 ms for n=4→16 (m 14→45), slope 0.89 vs m.
`optimize_full_pipeline()` grows 1.3 ms (n=4) → 14.5 ms (n=16), slope **1.94**
vs m: the commutation-gathering stage (H bubbling + pair gathering across
commuting intermediates) dominates once sandwiches exist — quadratic-ish over
this range, though the small m range (14→45) limits asymptotic confidence.
Recommend a dedicated sweep if the manuscript wants a full-pipeline exponent.

---

## 6. Reproducibility index

| Artifact | Path | Role |
|---|---|---|
| Ablation summarizer | `docs/analysis/_alg_complexity_data_probe.py` | recomputes Sections 3.1, 4 tables from canonical CSVs |
| Runtime measurement | `docs/analysis/_alg_complexity_runtime_measure.py` | Parts A/B/C measurements |
| Raw measurement CSVs | `docs/analysis/_alg_complexity_runtime_part{A,B,C}.csv` | measured data behind Sections 2, 3.3, 5 |
| E21 canonical | `data/v6/e21/ceiling_aware_comparison.csv` (1,140 rows) | Section 3.1 |
| E04 canonical | `data/v2_fixed/e04/e04_algorithm_comparison_v2_20260613_132653.csv` (400 rows) | Sections 1.1, 4.1 |
| E10 canonical | `data/v5/e10/e10_expanded_phase1_vs_phase2_20260613_131601.csv` (1,905 rows) | Section 4.2 |
| E22 canonical | `data/v7/e22/e22_gate_shuffle_ablation.csv` (2,240 rows) | Section 4.3 |
| E29 canonical | `data/v7/e29/e29_multi_seed_e04_full.csv` (800 rows) | Section 4.4 |

Validation: `pytest tests/test_optimizers.py tests/test_ceiling_aware.py -q`
(62 tests) passes before and after the docstring changes (see completion
report `docs/review/wave1/algorithmic_complexity.md`).
