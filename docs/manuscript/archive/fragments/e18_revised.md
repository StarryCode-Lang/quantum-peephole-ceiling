> **STATUS**: Not yet integrated into main manuscript. Pending merge.

## E18 Clifford+T Gate-Set Experiment (Revised with ITT Analysis)

*This section replaces the original E18 results. It introduces an
Intention-to-Treat (ITT) framework to correct the survivorship bias
identified in the original analysis (review item H7).*

---

### E18.1 Experimental Setup

The E18 experiment evaluates optimizer performance on circuits decomposed
into the Clifford+T universal gate set `{H, S, Sdg, T, Tdg, CNOT, X, Y, Z}`.
The benchmark suite comprises 270 circuit-optimizer combinations drawn from
15 circuit families spanning discrete-gate circuits (CNOT chains, GHZ
preparation, Oracle/BV, Random Clifford, Surface Code, Adder), variational
circuits (VQE, QAOA, UCCSD), phase-estimation circuits (QFT, IQP), search
circuits (Grover), random circuits (HaarRandom), and hardware-efficient
circuits (HardwareEfficient).  Three optimizers run on each successfully
decomposed circuit: `greedy_phase1`, `commutation_phase2`, and
`hybrid_phase1_2`; a `none` baseline records the decomposed circuit without
optimization.

### E18.2 Decomposition Failures — Systematic, Not Random

Of the 270 attempted circuit-optimizer combinations, 120 (44.4%) fail to
produce a valid reduction measurement.  These failures arise from two
deterministic mechanisms, each fully explained by observable covariates:

| Mechanism | Rows | Cause |
|---|---|---|
| Gate-set incompatibility | 78 (28.9%) | Circuits contain continuous parameterized rotations (`rz`, `ry`, `p`, `u`, `cp`, `cu1`, `ccx`) that have no exact Clifford+T decomposition rule. Qiskit's `BasisTranslator` raises `TranspilerError`. |
| Fidelity-budget exhaustion | 42 (15.6%) | Circuits exceed `max_qubits_fidelity = 10`; exact state-vector fidelity is computationally intractable for `n_qubits >= 12`, and the fallback returns 0. |

Little's MCAR test rejects the hypothesis that missingness is completely
at random (d² = 49.96, df = 1, p = 1.6 × 10⁻¹²).  Missingness is MAR
(Missing At Random), explained by `circuit_family` and `n_qubits`.

**Eight of fifteen circuit families fail at 100%** because their defining
gate sets include continuous rotations:

| Family | Rows | Failed | Offending gates |
|---|---|---|---|
| QFT | 11 | 11 | `h, cp` (controlled-phase) |
| HaarRandom | 3 | 3 | `rz, ry` |
| HardwareEfficient | 11 | 11 | `rz, ry, cx` |
| IQP | 11 | 11 | `rz, cz, h` / `p, h, x, cx, u` |
| QAOA | 11 | 11 | `rz, ry, cx` |
| QuantumWalk | 8 | 8 | `rz, h` |
| UCCSD | 8 | 8 | `rx, ry` singles + doubles |
| VQE | 8 | 8 | `x, ry, cx` |

Grover fails partially (7/10, 70%) due to Toffoli gates containing
`ry`.  The remaining six families (Adder, CNOT, GHZ, Oracle/BV,
RandomClifford, SurfaceCode) decompose without error because their
inventories are already subsets of the Clifford+T basis.

**Key finding:** failure is systematic (deterministic by circuit family),
not stochastic.  The most practically relevant families — variational
ansätze for near-term quantum computing (VQE, QAOA, UCCSD) — are
entirely excluded from the survivor subset.

### E18.3 Survivorship Bias — ITT Correction

The original analysis drops all 120 failed rows and reports statistics on
the 150 surviving rows.  This introduces **survivorship bias**: the
surviving families are structurally the simplest (discrete-gate, low
entanglement), and their reduction statistics are an upper bound on the
population mean, not a representative estimate.

We adopt a composite ITT correction following the framework in
`docs/analysis/e18_bias_strategy.md`:

| Cohort | n | Treatment |
|---|---|---|
| Valid (analyzable) | 150 | Observed reduction (no change) |
| Width-failed (fidelity = 0) | 42 | Multiple imputation (Rubin-pooled, m = 50, Beta-bootstrap within family × optimizer cell) |
| Gate-type-failed (decompose_error) | 78 | Strict ITT: reduction = 0 (conversion failure yields no optimization benefit) |

**ITT estimate (pooled across optimizers):**

| Metric | Value |
|---|---|
| Survivor-subset mean (150 valid rows) | 0.1800 |
| ITT mean (270 rows, MI for width-failed) | 0.1351 |
| 95% CI | [0.102, 0.169] |
| Sensitivity bracket (lower, upper) | [0.135, 0.187] |

The sensitivity bracket shows that even under the most optimistic
assumption (gate-type-failed rows reduce at the survivor-mean rate of
0.18), the all-optimizer ITT mean reaches only 0.187 — a narrow band
that quantifies the survivorship bias at ~25% of the survivor-mean value.

**Per-optimizer ITT results:**

| Optimizer | n | ITT mean | Survivor mean | Bracket |
|---|---|---|---|---|
| greedy_phase1 | 64 | 0.278 | 0.263 | [0.278, 0.278] |
| commutation_phase2 | 64 | 0.012 | 0.012 | [0.012, 0.012] |
| hybrid_phase1_2 | 64 | 0.280 | 0.265 | [0.280, 0.280] |

Note: per-optimizer brackets are zero-width because all gate-type-failed
rows belong to the `none` baseline optimizer (78 rows), not to the three
real optimizers.  The sensitivity uncertainty is concentrated in the
pooled "ALL" row.

### E18.4 Convertibility (Survival Framing)

Beyond mean reduction, we report the **convertibility probability** —
the fraction of circuits that survive each pipeline stage:

| Stage | P(survive) |
|---|---|
| Decomposable (reach optimization) | 71.1% |
| Optimizable and verifiable (produce valid reduction) | 55.6% |

Circuit-level: 92 of 142 unique circuit IDs (64.8%) have at least one
failure row.  Conclusions about Clifford+T optimization effectiveness
apply strictly to the subset of circuits whose gate sets admit exact
decomposition.

### E18.5 Fidelity Verification

We enhance the original fidelity check with a state-vector verification
(capped at `n_qubits <= 10` due to computational cost) and a measurement
Total Variation Distance (TVD) check.  Results are recorded in
`e18_fidelity_verified.csv`.  All 150 valid rows pass the verification
threshold (`fidelity > 1 - 10⁻⁶`, `TVD < 10⁻⁶`), confirming that the
optimizers preserve circuit identity on the decomposable subset.

### E18.6 Limitations and Recommendations

**Claim scope is restricted.** E18 conclusions — e.g. that Phase 1 gate
cancellation or hybrid Phase 1+2 rewriting achieves mean gate-count
reduction of 0.28 on the decomposable subset — hold **only for circuits
whose gates are already in the Clifford+T basis**.  They do not
generalize to:

- Variational circuits with continuous parameters (VQE, QAOA, UCCSD);
- Phase-estimation circuits with controlled rotations (QFT, IQP);
- Any circuit containing `rz`, `ry`, `p`, `u`, `cp`, `cu1`, or `ccx`.

**Recommended future work.** Implement Solovay–Kitaev approximation in
the transpilation pipeline to extend Clifford+T coverage to 12–13 of the
15 families, enabling approximate (rather than exact) decomposition for
the continuous-rotation families.  This would shrink the ITT sensitivity
bracket and allow the headline reduction claims to cover a broader
circuit population.

**Transparency.** All bias-correction outputs are archived at
`data/v5/e18/`:
- `e18_corrected.csv` — 270 rows with audit columns
- `e18_itt_report.csv` — per-optimizer ITT statistics
- `e18_littles_mcar.json` — Little's MCAR test result
- `e18_bias_report.txt` — human-readable correction report
