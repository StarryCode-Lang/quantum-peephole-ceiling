# Phase-2b Full Implementation — Completion Report (Wave 1)

**Worker:** 算法工程师_Phase2b (Phase-2b Full Implementation)
**Date:** 2026-07-21
**Scope:** `src/optimisation/phase2/template_matcher.py`, `experiments/phase2b_full_validation.py`,
`tests/test_phase2b_template_matcher.py`, `data/v8/phase2b_full/`

---

## 1. Audit of the v1.x template matcher (starting state)

`Phase2bTemplateMatcher` v1.2.0 shipped with a five-rule library:

| Rule | Effect | Gate count |
|---|---|---|
| H–CX–H on control (c<t) | reverse CNOT direction | 3 → 3 |
| H–CX–H on target | CZ | 3 → 1 |
| S–Sdg | identity | 2 → 0 |
| CZ–CZ | identity | 2 → 0 |
| H–H | identity | 2 → 0 |

Identified limitations:

1. **Library coverage.** No CX–CX / CCX–CCX / X–X / Z–Z / T–Tdg inverse
   cancellation (Phase-2b scored **0% on CNOT_chain** while Phase-1 scored
   100% — Phase-2b was not even a superset of Phase-1), no phase-polynomial
   merging (S+S=Z, T+T=S, Rz merges), no H–CZ–H / H–CCX–H / H–MCX–H
   conjugation templates.
2. **Reordering thrash.** `_reorder_h_next_to_cnots` moved H gates next to
   the nearest control-CNOT regardless of whether a sandwich could complete;
   308 moves for an 11-gate BV circuit, and the pipeline stalled after
   ~2 of k template rewrites.  Measured v7 E10 BV mean reduction: **23.8%**
   (bound of Thm 9 is ~20%; the measured optimum k+2 gates implies 55–75%).
3. **Scale.** v7 E10 (`data/v7/e10_phase2b_full/`, 624 rows) covers all 16
   families but only n ∈ {3,5,7,9}, one fixed depth `max(20,2n)`, and the
   v1.x library.  It is a *complete* run of the *old* experiment, so the gap
   is library + grid, not missing rows.

## 2. v2.0.0 implementation

### 2.1 Template library (all identities numerically verified)

* **Conjugation templates (Clifford, ≤3 qubits):** H–CX–H(control, c<t) →
  reversed CNOT (3→3, canonical guard makes oscillation impossible);
  H–CX–H(target) → CZ; H–CZ–H(either qubit) → CX; H–CCX–H(target) → CCZ;
  H–MCX–H(target) → MCZ; H–CCZ–H(any qubit) → CCX (all 3→1).
* **Inverse-cancellation closure:** self-inverse gates H, X, Y, Z, CX, CY,
  CH, CZ, SWAP, CCX, CSWAP, MCX on identical qubits (symmetric gates matched
  as unordered sets); named pairs S↔Sdg, T↔Tdg, SX↔SXdg; parametric pairs
  Rx/Ry/Rz/P/U1(θ)+ (θ) with θ₁+θ₂=0.
* **Phase-polynomial merging:** adjacent P-type gates
  {Z, S, Sdg, T, Tdg, P(θ), U1(θ)} merge by angle addition mod 2π and
  re-emit canonically (0→removed, π→Z, π/2→S, 3π/2→Sdg, π/4→T, 7π/4→Tdg,
  else P(θ)); same-axis Rx/Ry/Rz merge, zero-angle pairs vanish.
  P-type and Rz are **not** cross-merged (they differ by a global phase), so
  every rewrite is exact under `Operator` equality, not just up to phase.
* **Commutation gathering (full pipeline):** targeted H-sandwich exposure
  with candidate priority (target sandwich = direct 3→1 reduction first,
  control sandwich = enabling reversal second; gathering stops once one
  sandwich per gate completes); inverse/mergeable pair gathering across
  provably commuting intermediates, with the rule-based predicate extended
  by mutual diagonality (Z-family rotations, P/U1, CZ, CCZ all mutually
  commute).  This realizes a *restricted* phase-polynomial optimization over
  singleton Z-rotations and CZ/CCZ gadgets; full parity-gadget
  phase-polynomial optimization (Amy–Mosca) remains future work.

Termination: every pass strictly reduces gate count or performs a
guard-protected reversal that fires at most once per CNOT.

### 2.2 Correctness bug found and fixed during validation

The rc1 left-search range admitted index **-1**, which Python wraps to the
*last* gate of the listing.  On Grover(5) an H at the circuit end was
"bubbled" across position 0 — a non-adjacent, unitary-breaking move
(fidelity dropped to 0.667).  Fixed by correcting the range stop and adding
a defensive index guard in `_bubble_gate`; regression test
`test_no_negative_index_wraparound` added.  Post-fix fuzz: **340/340**
instances (BV exhaustive n≤5 + 10 families × 20 seeds) at fidelity exactly
1.0; all 729 benchmark rows have fidelity ≥ 1−2e-13.

## 3. Experiment v8 (`data/v8/phase2b_full/`, 729 rows)

Stratified coverage (compute-bounded; full factorial n=3–10 × depth=20–50
was replaced after a timeout):

| Stratum | Grid |
|---|---|
| BV (Thm 9 family) | **FULL**: n = 3..10 × 10 secrets/size (80 circuits) |
| Depth families (Universal, RandomClifford, Structured, IQP) | n ∈ {3,5,8} × depth ∈ {20,35,50} × 3 seeds |
| Other algorithmic families | n ∈ {3,5,8} × 2 seeds (deterministic: 1); QuantumWalk n ∈ {3,5} only |

QuantumWalk n=8 (9 qubits, 7-controlled MCX) exceeds the exact-fidelity
compute envelope (~280 s for 3 rows) and is excluded — documented in
`metadata.json.coverage`.

Optimizers: `greedy_phase1`, `commutation_phase2a`,
`template_phase2b` (v2.0.0 full pipeline).  Fidelity policy per row
(`fidelity_method` column): exact Operator ≤ 9 qubits (663 rows), exact
Clifford-tableau equality ≥ 10 qubits all-Clifford (60 rows), Haar
product-state sampling (200 samples) otherwise (6 rows).  For unitarily
equivalent circuits the sampled estimator returns exactly 1.0, so no row
can false-pass.

Files: `phase2b_full_validation_v8.csv` (canonical, 729 rows),
`family_summary_v8.csv`, `core_question_v8.csv`, `bv_theory_v8.csv`,
`bootstrap_ci_v8.csv`, `metadata.json`, plus 3 chunk CSVs.

## 4. Core question: on Phase-1 = 0% families, can Phase-2b exceed 30% mean reduction?

**Answer: YES — decisively on 2 of 13 strict Phase-1=0% families (BV,
Structured), and also on both near-zero families (IQP, RandomClifford).**

| Family | Phase-1 | Phase-2a | **Phase-2b v2** | P2b min | >30%? | Wilcoxon p (P2b>P1) |
|---|---|---|---|---|---|---|
| **BV** | 0.000 | 0.145 | **0.692** | 0.545 | **YES** | 4e-15 |
| **Structured** | 0.000 | 0.000 | **0.423** | 0.370 | **YES** | 1e-5 |
| Grover | 0.000 | 0.042 | 0.161 | 0.103 | no | 0.016 |
| Universal | 0.000 | 0.054 | 0.141 | 0.067 | no | 2e-5 |
| UCCSD_inspired | 0.000 | 0.014 | 0.080 | 0.000 | no | 0.033 |
| Adder / GHZ / QFT / QAOA / VQE / HWE / SurfaceCode / QWalk | 0.000 | 0.000 | 0.000 | 0.000 | no | — |
| IQP (P1=0.004) | ~0 | 0.125 | **0.920** | 0.847 | **YES** | 5e-6 |
| RandomClifford (P1=0.009) | ~0 | 0.215 | **0.482** | 0.224 | **YES** | 5e-6 |
| CNOT_chain (control) | 1.000 | 0.000 | **1.000** | 1.000 | (dominance ✓) | — |

Pooled bootstrap 95% CI: Phase-1 1.4% [0.1%, 3.0%], Phase-2a 9.3%
[7.6%, 11.1%], **Phase-2b 46.5% [42.4%, 50.5%]**.

Depth trend (Phase-2b mean by depth): IQP 0.879→0.931→0.949 (20/35/50),
RandomClifford 0.430→0.498→0.518, Structured 0.417→0.424→0.426,
Universal flat ~0.14.  The phase-polynomial rules exploit exactly the
redundancy that accumulates with depth in diagonal/Clifford-heavy families.

## 5. Theorem 9 (BV) validation

The v2 pipeline reaches the **exact k+2 gate optimum on every one of the 80
BV instances** (k = secret Hamming weight):

| n | P2b mean | P2b min | Thm 9 bound n/(4.5n+4) | Verdict |
|---|---|---|---|---|
| 3 | 0.592 | 0.545 | 0.171 | PASS (3.5×) |
| 4 | 0.613 | 0.571 | 0.182 | PASS |
| 5 | 0.695 | 0.588 | 0.189 | PASS |
| 6 | 0.716 | 0.600 | 0.194 | PASS |
| 7 | 0.707 | 0.609 | 0.197 | PASS |
| 8 | 0.727 | 0.615 | 0.200 | PASS |
| 9 | 0.746 | 0.621 | 0.202 | PASS |
| 10 | 0.744 | 0.625 | 0.204 | PASS |

Every instance (not just the mean) exceeds the rigorous bound by 2.7–3.5×;
the empirical asymptote is 2n/(2.5n+2) → 0.8 for random secrets, matching
the k+2 closed form.  Context vs. E24 (Thm 7 hardness family, Phase-2a):
79.8% mean [62.5%, 89.3%] on an *engineered* family; the v8 BV result
(69.2% mean over secrets, 54.5% worst case, natural algorithm family,
Phase-1 = 0%) is the same magnitude on a *natural* family and is therefore
the strongest empirical support for claim C2 in the manuscript.  The v7
fixture-scale statement "5n → n+2" is now validated at canonical scale with
the correct k+2 generalization.

## 6. Verification

* `/d/Downloads/miniforge3/python -m pytest tests/test_phase2b_template_matcher.py -q`
  → **28 passed** (8 legacy + 20 new: library identities all
  `Operator`-verified, BV k+2 optimum, Thm 9 bound, wraparound regression,
  Grover fidelity, oscillation guard).
* Fuzz: 340/340 fidelity = 1.0 (BV exhaustive n ≤ 5; 10 families × 20 seeds).
* Benchmark: 729/729 rows fidelity ≥ 1−2e-13 (`success` = True everywhere).
* Experiment reproducibility: `python experiments/phase2b_full_validation.py
  --chunk {depth|bv|algo}` then `--merge-only`; smoke mode `--mode smoke`
  (102 rows, 2 s).

## 7. Changed files

| File | Change |
|---|---|
| `src/optimisation/phase2/template_matcher.py` | rewritten → v2.0.0 (backup `template_matcher.py.bak-20260720-231522`) |
| `experiments/phase2b_full_validation.py` | rewritten → v8 stratified experiment (backup `…bak-20260720-231522`) |
| `tests/test_phase2b_template_matcher.py` | +20 tests (backup `…bak-20260720-231522`) |
| `data/v8/phase2b_full/` | new canonical dataset (729 rows + 4 analysis CSVs + `metadata.json`) |
| `docs/review/wave1/phase2b.md` | this report |

`commutation_rewriter.py` (also in scope) is unchanged — the Phase-2a
baseline is used as-is.  `docs/manuscript/manuscript.md` untouched per wave
rules; the release manifest was not touched.

## 8. Remaining gaps / honest limitations

1. **Grid coverage is stratified, not full-factorial.**  BV is full
   n=3..10 × 10 secrets; depth families are n={3,5,8} × depth={20,35,50} ×
   3 seeds (27 of 8×4×∞ grid points); algorithmic families n={3,5,8}.
   QuantumWalk n=8 missing (compute envelope: exact 9-qubit fidelity with
   7-controlled MCX).  Extending to full n=3..10 × depth=20..50 is
   mechanical (chunks already parameterized) and costs ~30–60 min.
2. **Phase-polynomial coverage is restricted:** singleton Z-rotation merges
   + CZ/CCZ gadget cancellation via diagonality.  No parity-gadget
   (CX–Rz–CX) phase-polynomial optimization — this is why QAOA (ZZ-gadget
   structure) stays at 0% even for v2.  A real phase-gadget engine (cf.
   Amy–Mosca / PyZX `phase_block`) is the natural next milestone and would
   target QAOA/VQE/HWE specifically.
3. **"All ≤3-qubit Clifford identities"** is realized as the verified
   inverse-cancellation closure + the standard conjugation template set
   (Qiskit/PyZX-grade).  It is not an exhaustive enumeration of the
   11,520-element 2-qubit Clifford group's rewrite presentation; coverage is
   stated explicitly in the module docstring and metadata.
4. **Structured-family mechanism:** the 42.3% brickwork reduction comes from
   phase merges + gathered block duplicates (metadata counters confirm);
   a one-line mechanistic note in the manuscript should attribute it to the
   generator's repeated rotation layers rather than to brickwork structure
   per se.
5. Grover (16.1%) and Universal (14.1%) improved over v7 but stay below
   30%; both are limited by MCX/X-gather blocking (X does not commute with
   controlled-Z), which is structural, not an implementation gap.

---

## 9. Reconciliation note (added 2026-07-21, wave-3 final cleanup)

This report quotes the Theorem-9 bound-excess range as **2.7–3.5×** (§5).
The canonical value — recomputed per instance from the 80 BV rows of
`data/v8/phase2b_full/phase2b_full_validation_v8.csv` (bound
$n/(4.5n+4)$, $n$ = secret length) — is **3.06–4.24×** (min ratio 3.062,
max ratio 4.238). The manuscript (§6.4, §8) and
`docs/manuscript/claim_evidence_table.csv` (claim C13) adopt the canonical
values, rounded to **3.1–4.2×** in the manuscript text. The 2.7–3.5× figure
here dates from a pre-final bound-evaluation draft of this wave-1 report;
the underlying dataset is identical and no other number in this report is
affected. The report body is left unchanged for provenance.

---

## 10. Addendum: QuantumWalk n=8 grid gap closed (added 2026-07-21, wave-4)

**Gap.** The v8 stratified grid originally sampled QuantumWalk at n={3,5}
only: the n=8 walk circuit is 9 qubits with 36 MCX gates (up to 8 controls),
and exact Operator-based fidelity was estimated to exceed the per-chunk
compute envelope.

**Fill run (2026-07-21).** A dedicated gap-fill chunk (`--chunk qw8`, added to
`experiments/phase2b_full_validation.py` in wave 4) ran the missing grid
points with the same seed formula as the algo chunk
(`BASE_SEED + seed*100 + n`):

- 2 grid points (param_n=8, seeds 153 and 253, trials 0/1) x 3 optimizers
  = **6 new rows**, chunk file
  `data/v8/phase2b_full/phase2b_v8_qw8_20260721_084322.csv`; merged table now
  **735 rows** (was 729).
- Circuit: 9 qubits, 106 gates, depth 59 (36 MCX up to 8 controls).

**Fidelity method (honest downgrade, pre-authorized by the experiment's own
policy).** A probe on 2026-07-21 measured exact Operator fidelity at
**~133 s/row** on this MCX-heavy circuit (6 rows ≈ 13+ min), confirming the
envelope concern. The rows therefore use the script's documented
`sampled200` fallback and are labeled `fidelity_method=sampled200`. Note that
for these specific rows the value is *exact*, not an estimate: all three
optimizers leave the circuit unchanged (106 -> 106 gates), so the estimator
resolves via its structural-equality fast path (`circuit == target` -> 1.0).
No row can false-pass through this path.

**Result (as expected, reported as-is).** QuantumWalk at n=8 shows **0.0%
reduction for all three optimizers** (greedy Phase-1, commutation Phase-2a,
template Phase-2b full pipeline), identical to the n={3,5} behavior. The
MCX/X-gather blocking that limits Grover and Universal applies here as well;
the gap is structural, not an implementation defect.

**Merged-analysis deltas (2026-07-21 re-merge).**

- `core_question_v8.csv`: QuantumWalk `n_rows_phase2b` 4 -> 6; means still
  0.0/0.0/0.0; verdict unchanged (`phase1_is_zero=True`, `>30% = False`).
- `family_summary_v8.csv`: QuantumWalk per-optimizer counts 4 -> 6, means
  unchanged at 0.0.
- `bootstrap_ci_v8.csv` (pooled): negligible shifts from 6 added zero rows —
  template_phase2b mean 0.4645 -> 0.4607, 95% CI [0.4194, 0.5014].
- `bv_theory_v8.csv`: unchanged (no BV rows touched); Theorem-9 bound still
  PASS at all n=3..10.

**Final coverage statement (now in `metadata.json`, derived from the merged
data).** "n={3,5,8} x 2 seeds (stratified); QuantumWalk covered at
n=[3, 5, 8] (full stratified grid); n=8 rows use sampled200 fidelity —
exact Operator fidelity measured at ~133 s/row for the 9-qubit, 36-MCX walk
circuit exceeds the compute envelope (wave-4 gap-fill, chunk qw8)."
All 16 families now have complete stratified-grid coverage; the Phase-2b
verdicts elsewhere in this report are unaffected.
