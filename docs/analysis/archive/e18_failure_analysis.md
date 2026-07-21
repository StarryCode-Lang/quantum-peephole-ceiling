# E18 Failure-Mode Analysis: Systematic vs. Random Missingness

> **Author:** E18 Data-Quality Repair Agent
> **Date:** 2026-07-17
> **Source data:** `data/v5/e18/e18_clifford_t_e18_full_20260610_052140.csv` (270 rows, 31 columns)
> **Run metadata:** `data/v5/e18/metadata.json` (run_id `e18_full_20260610_052140`, Qiskit 2.4.1, schema 2.0.0)
> **Review item:** H7 — E18 survivorship bias (severity: high; 44.4% failure)

---

## 1. Executive Summary

The E18 missingness is **systematic, not random**. Of 270 attempted rows, 120 (44.4%) fail, driven by two fully separable mechanisms that are each explained by *observable* covariates:

1. **Gate-set incompatibility (78 rows, "decompose_error")** — circuits containing continuous / parameterized rotations (`rz`, `ry`, `p`, `u`, `u1`, `u2`, `u3`, `cp`, `cu1`, `ccx`, `cz`) that Qiskit's `BasisTranslator` cannot map exactly onto the Clifford+T basis `{H,S,Sdg,T,Tdg,CX,X,Y,Z}`. This is a **population-level** selection: eight of fifteen circuit families fail 100%, one fails 70%, and the remaining six never fail.
2. **Fidelity-verification budget exhaustion (42 rows, `fidelity = 0`)** — circuits that *do* decompose but exceed the exact state-vector fidelity budget (`max_qubits_fidelity = 10`); every one of these 42 rows has `n_qubits >= 12`. The fallback `average_gate_fidelity` returns 0 for these wide circuits, flagging them as unverified.

Because both mechanisms are explained by observed variables (circuit family / gate composition and qubit count), the missingness is **MAR (Missing At Random)**, not MCAR. This is the single most important finding for bias correction: it means **multiple imputation conditioned on the observed covariates is statistically valid** for the 42 width-failed rows, and that a transparent sensitivity analysis (rather than silent filtering) is the correct treatment for the 78 gate-type-failed rows.

---

## 2. Cohort Definition

| Category | Definition | Rows | % of 270 |
|---|---|---|---|
| **Valid (analyzable)** | `status == "ok"` AND `fidelity > 0` | 150 | 55.6% |
| Failed — decompose_error | `status` starts with `decompose_error` | 78 | 28.9% |
| Failed — fidelity = 0 | `status == "ok"` AND `fidelity == 0` | 42 | 15.6% |
| **Total failed** | union of the two above | **120** | **44.4%** |

Note on the existing `docs/results/e18_survivor_bias.md`: it labels 192 rows as "successful (ok)" because it counts only `decompose_error` as failure. The 42 `fidelity = 0` rows have `status = "ok"` but carry an unverified (numerically broken) outcome. Treating them as analyzable silently imports the second failure mode into the "survivor" set. This analysis reclassifies them as failed, consistent with the manuscript's stated 44.4% total (Section 5.6.4 / 6.3.5).

At the **circuit level**: 142 unique `circuit_id`s were attempted; 92 (64.8%) produced at least one failure row, confirming the bias is not confined to a handful of rows.

---

## 3. Failure Mechanism 1 — Gate-Set Incompatibility (decompose_error)

### 3.1 Root cause

The experiment calls `qiskit.transpile(circuit, basis_gates=CLIFFORD_T_BASIS, optimization_level=0)`. The `BasisTranslator` raises a `TranspilerError` whenever the input contains a gate with no exact Clifford+T rule in the loaded `EquivalenceLibrary`. The distinct offending gates extracted from the 78 error strings are:

```
ccx, cp, cu1, cx, cz, h, p, ry, rz, u, u1, u2, u3, x
```

Filtering out gates that *are* in the basis (`h, x, cx`), the **genuinely incompatible** gates are: `rz, ry, p, u, u1, u2, u3, cp, cu1, ccx, cz`. These are exactly the continuous / parameterized rotations and multi-controlled gates that require Solovay–Kitaev approximation (O(log(1/ε)) T gates) rather than an exact rewrite.

### 3.2 Per-family failure distribution

| Family | Rows | decomp_error | fail rate | Mechanism |
|---|---|---|---|---|
| HaarRandom | 3 | 3 | 100% | continuous `rz/ry` |
| HardwareEfficient | 11 | 11 | 100% | `rz, ry, cx` |
| IQP | 11 | 11 | 100% | `rz, cz, h` / `p,h,x,cx,u` |
| QAOA | 11 | 11 | 100% | `rz, ry, cx` / `x,ry,cx` |
| QFT | 11 | 11 | 100% | `h, cp` (controlled-phase) |
| QuantumWalk | 8 | 8 | 100% | `rz, h` / `x,ry,cx` |
| UCCSD | 8 | 8 | 100% | `rx/ry` singles + doubles |
| VQE | 8 | 8 | 100% | `x, ry, cx` |
| Grover | 10 | 7 | 70% | `h, x, ry, cx, ccx` (Toffoli) |
| Adder | 24 | 0 | 0% | — |
| CNOT | 33 | 0 | 0% | — |
| GHZ | 33 | 0 | 0% | — |
| Oracle (BV) | 33 | 0 | 0% | — |
| RandomClifford | 33 | 0 | 0% | — |
| SurfaceCode | 33 | 0 | 0% | — |

The dichotomy is **structural and deterministic**: families with a naturally discrete gate inventory (Clifford / CNOT / Toffoli-free) always survive; families built on continuous ansätze (all variational families: VQE, QAOA, UCCSD; all phase-rich families: QFT, IQP, QuantumWalk) always fail. **No random component exists.** The most practically relevant families (VQE, QAOA, UCCSD) are entirely excluded.

### 3.3 Qubit-size independence of this mechanism

decompose_error rows span every qubit size from 2 to 20 (e.g. 1 row at 2 qubits, 7 at 3, 9 at 4, …, 4 at 20). Failure is therefore *not* a width effect — a 3-qubit QFT fails for the same reason a 20-qubit QFT does. This separates mechanism 1 from mechanism 2 cleanly.

---

## 4. Failure Mechanism 2 — Fidelity-Verification Budget Exhaustion (fidelity = 0)

### 4.1 Root cause

After successful decomposition, `run.py` requests the optimizer's reported `fidelity`; if that is `None` or `0.0` it falls back to `average_gate_fidelity(optimized, original, max_qubits=max_qubits_fidelity)` with `max_qubits_fidelity = 10` (run config in `metadata.json`). `average_gate_fidelity` constructs the full unitary / state-vector, which is O(4^n); for `n > 10` it returns `None`, which the fallback coerces to `0.0`. Hence these rows carry `status = "ok"` but `fidelity = 0`, marking them as **numerically unverified** rather than genuinely identity-preserving.

### 4.2 Deterministic width threshold

| n_qubits | fidelity = 0 rows | valid rows |
|---|---|---|
| 3–10 | 0 | 159 |
| 11 | 0 | 6 |
| 12 | 6 | 3 |
| 13 | 6 | 0 |
| 15 | 9 | 0 |
| 16 | 6 | 0 |
| 20 | 9 | 0 |
| 21 | 6 | 0 |

**Every fidelity-zero row has `n_qubits >= 12`; every row with `n_qubits <= 11` that survived decomposition has a valid fidelity.** This is a hard, deterministic threshold set by `max_qubits_fidelity = 10`, not a stochastic outcome. The affected families are exactly the six "simple" families (CNOT, GHZ, Oracle, RandomClifford, SurfaceCode, and partial Grover) — i.e. the families that survive mechanism 1 — at their widest sizes.

### 4.3 Distribution by optimizer

The 42 fidelity-zero rows split evenly across the three real optimizers (14 each for `greedy_phase1`, `commutation_phase2`, `hybrid_phase1_2`) and **zero** for `none` (the baseline never reaches the fidelity step). This even split reflects that the missingness is a property of the *circuit width*, not of the optimizer, confirming MAR with respect to the optimizer dimension.

---

## 5. Formal Missingness Tests

### 5.1 Little's MCAR test

Implemented via EM-estimation of the joint mean/covariance of `[n_qubits, reduction]` followed by the Little statistic over missingness patterns (`reduction` coded missing for all 120 failed rows).

| Statistic | Value |
|---|---|
| Little's d² | **49.96** |
| Degrees of freedom | 1 |
| p-value | **1.6 × 10⁻¹²** |

**Result:** Reject MCAR at any conventional level. The missingness of the reduction outcome is **not** completely at random.

### 5.2 Chi-square tests of independence

| Test | χ² | dof | p-value | Interpretation |
|---|---|---|---|---|
| Failure × circuit family | 135.58 | 14 | 5.4 × 10⁻²² | failure strongly depends on family |
| Failure × qubit bucket (≤4 / 5–8 / 9–10 / >10) | 59.03 | 3 | 9.5 × 10⁻¹³ | failure strongly depends on width |

### 5.3 Welch t-test (n_qubits: valid vs. failed)

| Group | mean n_qubits |
|---|---|
| Valid rows | 6.90 |
| Failed rows | 10.88 |

`t = −7.24`, `p = 2.0 × 10⁻¹¹`. Failed rows are systematically larger, but (per §3.3) this is driven by the width threshold of mechanism 2, not by mechanism 1.

### 5.4 Missingness classification

Combining the evidence:

- Missingness is **not MCAR** (Little's test rejects, p ≪ 0.001).
- Missingness is **fully explained by observed covariates** (`circuit_family` encodes gate-set type; `n_qubits` encodes the width threshold). Once these are conditioned on, no residual missingness mechanism remains.
- Therefore the missingness is **MAR (Missing At Random)** — the most favourable non-MCAR category, and the one for which multiple imputation yields asymptotically unbiased estimates under the standard MAR assumption.

The remaining residual risk is **MNAR-by-principle**: for the 78 decompose-error rows the outcome (`reduction` under Clifford+T optimization) is *structurally undefined* — there is no Clifford+T circuit to optimize. Imputing a scalar "reduction" for these is not a missing-data problem but a population-transfer problem (see strategy doc). The 42 fidelity-zero rows, by contrast, *do* have a Clifford+T circuit; only the verification step failed, so their reduction is genuinely missing-but-imputable.

---

## 6. Implications for the Survivor Subset

The 150 valid rows are **not a random draw** of the 270 attempted rows. They are enriched for:

- discrete-gate families (CNOT, Adder, GHZ, Oracle, RandomClifford, SurfaceCode) — the structurally simplest circuits;
- small-to-mid widths (`n_qubits ≤ 11`).

Consequently, statistics computed on the survivor subset (e.g. mean `reduction = 0.180` pooled over optimizers) **overstate the optimism** of Clifford+T optimization for the general circuit population. The bias is *directional*: survivors are the easiest-to-decompose, hardest-to-verify cases — exactly the cases where local peephole rewriting is most likely to find cancellations. Any headline reduction reported on survivors alone is an **upper bound** on the population mean, not a representative estimate.

---

## 7. Verdict

> **Failure mode: SYSTEMATIC (MAR).** Two deterministic, separable mechanisms: gate-set incompatibility (family-level, 78 rows) and fidelity-budget exhaustion (width-level, 42 rows). Little's MCAR test rejects (p = 1.6 × 10⁻¹²). Silent filtering of these rows introduces survivorship bias; the correct treatment is ITT analysis with multiple imputation (for the 42 MAR-by-width rows) plus sensitivity bounds (for the 78 structurally-undefined rows), as detailed in `e18_bias_strategy.md`.
