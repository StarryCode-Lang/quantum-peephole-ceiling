> **Status (2026-08-07):** Supporting appendix for the active manuscript. Sections
> D-G contain current evidence and supporting analyses. The machine-readable
> claim map in `docs/manuscript/claim_evidence_table.csv`, the canonical data
> policy in `data/DATA_CANONICAL.md`, and `release/release_manifest.json` are
> authoritative. Superseded V6 claim maps and limitation prose were removed from
> this active appendix; wave reports remain available under `docs/review/` as
> historical provenance.

# Appendix

## A. Active Evidence Routing

The active claim-evidence map is maintained in
`docs/manuscript/claim_evidence_table.csv`. Current quantitative evidence is
partitioned as follows:

| Claim area | Primary evidence | Scope boundary |
|---|---|---|
| Listing-conditioned Phase-1 ceiling | E1-E5, E19, E19-extended, E22, E30 | Validated for recorded listing models and families; an exhaustive listing-potential theory remains open. |
| Phase-2a context dependence | E10, E14, E16, E24 | Phase-2a results do not establish completeness of Phase-2b templates. |
| Production-compiler comparison | E12, E15, E20, SOTA | E20 remains frozen as-executed; corrected rerun is non-canonical under `data/v11/e20_corrected/`. |
| Phase-2b template library | E26, 2,427 canonical rows | Full-scale evidence covers the implemented library, not the complete template universe. |
| Ceiling-model robustness | E21, E27, P7 diagnostic | RepetitionCode exposes a learned-model extrapolation failure; the model remains exploratory. |
| Noise transfer | EHW | Noise-model simulation only; no real-device result is claimed. |
| Listing x Phase-2b interaction | E31, 396 rows | Supporting non-canonical smoke pilot; full family x size/depth/seed factorial remains open. |

Historical claim tables, review waves, and draft fragments are retained only for
audit provenance. They must not override the active map above.

---

## D. Phase-2b v2 Full-Scale Validation (E26, 2,427 rows)

> **Data:** `data/v8/phase2b_full/` (canonical `phase2b_full_validation_v8.csv`,
> 2,427 rows; analysis CSVs `family_summary_v8.csv`, `core_question_v8.csv`,
> `bv_theory_v8.csv`, `bootstrap_ci_v8.csv`; `metadata.json`). **Code:**
> `src/optimisation/phase2/template_matcher.py` v2.0.0,
> `experiments/phase2b_full_validation.py`,
> `tests/test_phase2b_template_matcher.py`. **Reports:**
> `docs/review/wave1/phase2b.md`, `docs/review/wave5/phase2b_fullgrid.md`,
> `docs/review/wave6/phase2b_crossfill.md`.

### D.1 Experiment design

Full-factorial grid, closed in wave 6:

| Stratum | Grid |
|---|---|
| BV (Theorem-9 family) | n = 3..10 x 10 secrets/size (80 circuits) |
| Depth families (Universal, RandomClifford, Structured, IQP) | n = 3..10 x depth in {20,25,...,50} x 3 seeds (56/56 combinations) |
| Other algorithmic families | n in {3,5,8} x 2 seeds; QuantumWalk includes n = 8 gap-fill rows |

Optimizers are `greedy_phase1`, `commutation_phase2a`, and
`template_phase2b`. The v2 pipeline combines inverse-cancellation closure,
restricted phase-polynomial merging, and bounded Clifford-conjugation
templates. Fidelity checks use exact Operator equality where feasible,
Clifford-tableau equality for all-Clifford rows, and global Haar-random state
sampling for the remaining scalable cases. No row falls below the documented
fidelity tolerance.

### D.2 Core question

**Answer:** Phase-2b exceeds 30% mean reduction on BV and Structured, and also
on the near-zero Phase-1 families IQP and RandomClifford.

| Family | Phase-1 | Phase-2a | Phase-2b v2 | P2b min | > 30%? |
|---|---:|---:|---:|---:|:---:|
| BV | 0.000 | 0.145 | 0.692 | 0.545 | yes |
| Structured | 0.000 | 0.000 | 0.402 | 0.358 | yes |
| IQP | ~0 | 0.094 | 0.920 | 0.844 | yes |
| RandomClifford | ~0 | 0.224 | 0.516 | 0.224 | yes |
| CNOT chain | 1.000 | 0.000 | 1.000 | 1.000 | control |

Pooled bootstrap 95% CIs: Phase-1 mean 0.5% [0.1%, 1.0%], Phase-2a mean
9.0% [8.2%, 9.7%], and Phase-2b mean 48.5% [46.5%, 50.5%].

### D.3 Theorem 9 validation

The v2 pipeline reaches the exact `k+2` gate optimum on all 80 BV instances:

| n | Phase-2b mean | Phase-2b minimum | Theorem 9 bound | Verdict |
|---:|---:|---:|---:|---|
| 3 | 0.592 | 0.545 | 0.171 | pass |
| 4 | 0.612 | 0.571 | 0.182 | pass |
| 5 | 0.695 | 0.588 | 0.189 | pass |
| 6 | 0.716 | 0.600 | 0.194 | pass |
| 7 | 0.707 | 0.609 | 0.197 | pass |
| 8 | 0.727 | 0.615 | 0.200 | pass |
| 9 | 0.746 | 0.621 | 0.202 | pass |
| 10 | 0.744 | 0.625 | 0.204 | pass |

Every instance exceeds the rigorous bound by 3.1-4.2x. The result is strong
empirical support for the natural BV family, not evidence that the template
library is complete. Parity-gadget and broader phase-polynomial coverage remain
open.

### D.4 Limitations

1. The recorded depth-family grid is full-factorial; QuantumWalk n = 8 uses the documented structural-preservation fidelity route.
2. The phase-polynomial implementation does not cover general parity gadgets.
3. The Clifford template set is verified but is not an exhaustive enumeration of the two-qubit Clifford rewrite universe.
4. Structured-family gains depend on the repeated rotation layers in the recorded generator.
5. Grover and Universal remain below the 30% threshold in the recorded Phase-2b grid.

---

## E. SOTA Compiler Benchmark Update

> **Data:** `data/v6/sota_benchmark/` contains canonical raw runs and the
> aggregate comparison. **Full results:**
> `docs/results/sota_compiler_benchmark.md`. E20's frozen 1,070-row CSV is
> as-executed evidence; the corrected `gateset=` and `sx`/`sxdg` pipeline is
> reproduced separately in non-canonical `data/v11/e20_corrected/`.

### E.1 Corrected Cirq protocol

Two bugs were corrected in the reusable E20 path: Cirq 1.6.1 requires the
`gateset=` keyword for `optimize_for_target_gateset`, and its OpenQASM 2 export
can emit `sx`/`sxdg` definitions absent from Qiskit's default `qelib1.inc`.
The corrected implementation injects equivalent definitions before QASM import.
Canonical E20 remains unchanged; headline multi-compiler claims use the
corrected SOTA pipeline.

### E.2 Reliability caveats

- E20 canonical Cirq coverage remains unbalanced because 70 of 390 Cirq rows
  retain the historical QASM import error.
- The corrected rerun records 390/390 successful Cirq rows but is non-canonical.
- Fourteen of 30 t|ket> RandomClifford rows fail exact-fidelity verification;
  those rows require the documented caveat and are not silently treated as
  valid reductions.

---

## F. Listing-Control Experiments

### F.1 E22 shuffle ablation

**Data:** `data/v7/e22/e22_gate_shuffle_ablation.csv` (canonical, 2,240 rows,
16 families). **Code:** `experiments/gate_shuffle_ablation.py`.

| Optimizer | Original | Shuffled | WCL | MWU p |
|---|---:|---:|---:|---:|
| greedy Phase-1 | 6.30% | 10.34% | 12.20% | 6.8e-15 |
| commutation Phase-2a | 3.87% | 2.70% | 1.00% | 0.462 |

Shuffling increases greedy Phase-1 reduction relative to the original listing,
while the Phase-2a difference is not significant. This supports a
listing-conditioned interpretation rather than a generic gate-order artifact.

### F.2 E29 multi-seed replication

**Data:** `data/v7/e29/e29_multi_seed_e04_full.csv` (canonical, 800 rows).
**Code:** `experiments/multi_seed_e04.py`.

| Optimizer | E04 single seed | E29 pooled mean |
|---|---:|---:|
| RLS | 0.00% | -176.5% |
| SA | -1.6% | -22.1% |
| GA | -0.2% | -8.3% |
| Hybrid | not in E04 | +4.69% |

E04 point estimates are seed/configuration fragile. The qualitative result is
reported with the E29 qualification wherever E04 is cited.

---

## G. E31 Listing x Phase-2b Pilot

**Data:** `data/v11/e31_listing_phase2b/` (396 rows, non-canonical).
**Code:** `experiments/e31_listing_phase2b_interaction.py`.
**Analysis:** `analysis/e31_listing_phase2b_analysis.py`.

E31 crosses LBL, WCL, and one seeded random topological listing with Phase-1,
Phase-2a, and Phase-2b on 44 smoke-scale source circuits. It verifies listing
fidelity, preserves source-circuit pairing, and reports descriptive cell and
paired-contrast summaries. It does not estimate the full listing space or
establish a confirmatory WCL x Phase-2b interaction. The full family x
size/depth/seed factorial remains open.

```bash
python experiments/e31_listing_phase2b_interaction.py
python analysis/e31_listing_phase2b_analysis.py
```

---

*Active appendix last updated 2026-08-07. Historical wave reports remain under
`docs/review/`; canonical data remain pinned by `release/release_manifest.json`.*
