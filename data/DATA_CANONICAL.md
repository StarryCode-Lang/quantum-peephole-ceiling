# Canonical Data Files

> **Version**: 1.0  
> **Date**: 2026-06-12  
> **Purpose**: Each experiment has multiple timestamped CSV files from re-runs. This document specifies which file is the **canonical** version used for analysis and manuscript figures.

## Policy

- **Canonical** = latest `full` mode run with the most rows
- **Legacy** = earlier runs, kept for provenance but not used in analysis
- **Smoke** = quick validation runs, never used in analysis

## Canonical Files

| Exp | Canonical File | Rows | Notes |
|-----|---------------|------|-------|
| E1 | `v2_fixed/e01/e01_phase_transition_v2_20260611_195450.csv` | 25,000 | Deterministic; all 3 copies are identical |
| E2 | `v2_fixed/e02/e02_entanglement_density_v2_20260611_191816.csv` | 2,100 | Deterministic; both copies identical |
| E3 | `v2_fixed/e03/e03_scaling_v2_20260611_224540.csv` | 12,000 | v5/e03 is a duplicate (fidelity rounding only) |
| E4 | `v2_fixed/e04/e04_algorithm_comparison_v2_20260611_194858.csv` | 400 | Latest run; SA/GA differ from first run (stochastic) |
| E5 | `v2_fixed/e05/e05_landscape_v2_20260611_191723.csv` | 6,000 | Deterministic |
| E10 | `v5/e10/e10_expanded_phase1_vs_phase2_20260613_131601.csv` | 1,905 | Expanded from v3 (627 rows); supersedes 819-row run |
| E11 | `v4/e11/e11_real_circuit_benchmark_e11_full_20260611_114615.csv` | 426 | Expanded from initial 168-row run |
| E12 | `v4/e12/e12_compiler_baseline_e12_full_20260613_051316.csv` | 568 | Expanded from initial 224-row run; L0/L1/L2/L3 all distinct |
| E13 | `v4/e13/e13_structural_ceiling_e13_full_20260609_043322.csv` | 56 | Only full run |
| E14 | `v5/e14/e14_extended_benchmark_e14_full_20260611_114726.csv` | 2,130 | Expanded from initial 783-row run |
| E15 | `v5/e15/e15_multi_compiler_e15_full_20260611_150934.csv` | 994 | Latest full run; **Qiskit only** (no Cirq/t|ket>) |
| E16 | `v5/e16/e16_window_scaling_e16_full_20260610_142547.csv` | 696 | Only full run |
| E17 | `v5/e17/e17_connectivity_e17_full_20260610_150935.csv` | 755 | Only full run |
| E18 | `v5/e18/e18_clifford_t_e18_full_20260610_052140.csv` | 270 | Includes 78 decompose_error rows AND 42 fidelity=0 rows (120/270 = 44.4% total failure rate) |
| Heldout | `v5/new_families_heldout.csv` | 125 | Phase 7 held-out validation |
| Isolation | `v5/qiskit_pass_isolation.csv` | 100 | Phase 7 Qiskit pass isolation |

## Known Issues

1. **v5/e03 is a duplicate of v2_fixed/e03** — differs only in fidelity float rounding and runtime. Not a new experiment. The canonical version is `v2_fixed/e03`.
2. **E1 has 4 CSV copies** — the greedy optimizer is deterministic with fixed seed, but copies differ in fidelity precision (not bitwise identical).
3. **E18 has 78 decompose_error rows AND 42 fidelity=0 rows** — these are distinct failure modes: decompose_error rows fail at Clifford+T decomposition, while fidelity=0 rows fail at fidelity verification. Total: 120/270 = 44.4% failure rate. The generate_figures.py script filters both failure modes out.
4. **E15 smoke and full data from 20260610 have negative reductions** — legitimate (Qiskit gate inflation on some circuits), not errors.
5. **Total canonical optimizer trial count (E1-E18)**: 53,300. Including held-out validation and Qiskit pass-isolation artifacts, the canonical analysis artifacts contain 53,525 rows. Legacy/smoke duplicates are excluded.

---

## Legacy Data (v1 - Buggy Greedy)

E1-E5 were originally run with a buggy Greedy optimizer (v1.x) where `_are_inverse()` 
did not check qubit matching. This was fixed in Greedy v3.0.0. All v1 data has been 
superseded by `data/v2_fixed/`. The original v1 data files are not included in the 
canonical release but may be available in the git history.

**Bug impact**: The buggy optimizer could incorrectly identify gate pairs on different 
qubits as inverse, leading to invalid circuit modifications. All v2_fixed data uses 
the corrected optimizer.
