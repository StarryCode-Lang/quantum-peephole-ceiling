# HIGH Code Issues — Batch Fix Log

**Date**: 2026-06-17
**Scope**: Batch fix of HIGH-severity code issues identified in the project audit.
**Policy**: Code fixes only; no tests were run.

---

## Summary

| # | File / Location | Issue | Status |
|---|----------------|-------|--------|
| 1 | `src/optimisation/base.py` | `_fitness` division guard + reward term | Fixed |
| 2 | `src/optimisation/ceiling_aware.py` | `count_phase2_actions` tolerance mismatch | Fixed |
| 3 | `src/circuits/real_benchmarks.py` | `make_uccsd_ansatz` misnomer | Fixed (renamed) |
| 4 | `experiments/e15_multi_compiler/run.py` | Hardcoded `seed_transpiler=42` | Fixed |
| 5 | `experiments/e18_clifford_t/run.py` | T-count storage | RESOLVED — no fix needed |
| 6 | `experiments/e19_wcl_listing/run.py` | Dead code + arbitrary thresholds | Fixed |
| 7 | `experiments/e17_connectivity/run.py` | Measurement contamination + fake heavy-hex | Fixed |
| 8 | `experiments/e11_real_circuit_benchmark/run.py` | Fidelity fallback unlabeled | Fixed |
| 9 | `experiments/e12_compiler_baseline/run.py` | Fixed coupling map | Fixed |
| 10 | `experiments/e13_structural_ceiling/run.py` | Negative `ceiling_gap` | Fixed |
| 11 | `experiments/e14_extended_benchmark/run.py` | `build_optimizers()` params | RESOLVED — already had params; added `success_reduction` |
| 12 | `experiments/e15_multi_compiler/run.py` | QASM round-trip non-unitary | Fixed (warning + annotation) |
| 13 | `experiments/e16_window_scaling/run.py` | Missing Phase-1-only baseline | Fixed |
| 14 | `experiments/e20_multi_compiler_full/run.py` | Missing custom optimizers | Fixed |
| 15 | `experiments/e10_phase1_vs_phase2/run_expanded.py` | BV n_qubits + hardcoded angles | Fixed |

---

## Detailed Fixes

### 1. `src/optimisation/base.py` — `_fitness` division and reward (line ~600)

**Problem**: The division `circuit.size() / target.size()` was guarded by a fragile inline ternary. The reward term `0.1 * fidelity * penalty` applied even when `reduction = 0` (no-op or circuit grew), potentially rewarding non-reduction.

**Fix**:
- Replaced inline ternary with explicit `if target_size > 0` conditional.
- Guarded the reward term: `reward = 0.1 * fidelity * penalty if reduction > 0.0 else 0.0`, so no-ops and grown circuits receive zero reward.

### 2. `src/optimisation/ceiling_aware.py` — tolerance mismatch (line ~150)

**Problem**: `_PredicateHelper.is_self_inverse_pair` used absolute tolerance `abs(angle_sum) < DEFAULT_PRECISION` for rotation cancellation, while `base.py` used relative tolerance `abs(angle_sum) <= DEFAULT_PRECISION * scale` with `scale = max(1.0, abs(angle1), abs(angle2))`. This caused ceiling_aware to under-count Phase-2 actions for large-angle rotations.

**Fix**: Changed to relative tolerance matching `base.py`:
```python
scale = max(1.0, abs(float(p1[0])), abs(float(p2[0])))
return abs(angle_sum) <= DEFAULT_PRECISION * scale
```

### 3. `src/circuits/real_benchmarks.py` — `make_uccsd_ansatz` rename (line ~453)

**Problem**: Function named `make_uccsd_ansatz` but it does not implement a true UCCSD ansatz (no fermionic excitations, no JW/BK mapping, no SWAP networks).

**Fix**:
- Renamed to `make_parameterized_ansatz`.
- Updated docstring to explicitly state it is NOT a true UCCSD and explain what it actually builds.
- Updated all call sites: `real_benchmarks.py` (self-reference), `tests/test_core.py`, `experiments/e21_ceiling_aware/run.py`, `docs/05_supplementary/supplementary_materials.md`.

### 4. `experiments/e15_multi_compiler/run.py` — hardcoded transpiler seed (line ~56)

**Problem**: `seed_transpiler=42` was hardcoded in `_qiskit_transpile`.

**Fix**:
- Added `seed_transpiler` parameter to `_qiskit_transpile`.
- Passed the experiment's top-level `seed` to all transpiler calls.
- Recorded `qiskit_transpiler_seed` in metadata.

### 5. `experiments/e18_clifford_t/run.py` — T-count storage

**Status**: RESOLVED — no fix needed.

**Reason**: T-count was already stored in three columns: `baseline_t_count`, `optimized_t_count`, `t_count_reduction` (lines 167-169). The recon report confirmed this.

**Additional improvement**: Cleaned up `decompose_error` rows — split the embedded error string into clean `status="decompose_error"` + separate `error_message` and `error_type` fields, and added missing columns (`circuit_type`, `gate_set`, `trial`, `seed`) for DataFrame consistency.

### 6. `experiments/e19_wcl_listing/run.py` — dead code + arbitrary thresholds

**Problem**:
- `WireTraversalPreprocessor` was imported and instantiated (`wcl_preprocessor = WireTraversalPreprocessor()`) but never used. The comment said "record WCL preprocessing alone" but this was never implemented.
- Conclusion thresholds `0.001` and `2` were hardcoded inline.

**Fix**:
- Removed dead import and instantiation.
- Extracted thresholds to named constants: `WCL_SIGNIFICANCE_MIN = 0.001`, `WCL_LBL_RATIO_THRESHOLD = 2.0`.

### 7. `experiments/e17_connectivity/run.py` — measurement contamination + fake heavy-hex

**Problem**:
- `apply_topology_constraint` used `optimization_level=1`, causing the Qiskit transpiler's own gate cancellation/commutation to contaminate the topology-routing measurement.
- `make_heavy_hex` does not generate a true heavy-hex lattice (it's a grid with checkerboard vertical edges).
- `seed_transpiler=42` was hardcoded.

**Fix**:
- Changed to `optimization_level=0` (routing only, no optimization passes).
- Made `seed_transpiler` a parameter, passed from `run()`'s `seed`.
- Updated `make_heavy_hex` docstring to clearly state it is NOT a true heavy-hex lattice and recommend `CouplingMap.from_heavy_hex(d)`.
- Split `transpile_error` status into clean `status` + `error_message` + `error_type`.

### 8. `experiments/e11_real_circuit_benchmark/run.py` — fidelity fallback

**Problem**: When `result.fidelity` was `None` or `0.0`, the code fell back to `average_gate_fidelity`, then back to `result.fidelity` (which could be a structural similarity estimate from `base.py`'s last-resort fallback). The fidelity source was not tracked in the output.

**Fix**: Added `fidelity_method` field to track the source: `optimizer_reported`, `recomputed_exact`, `structural_estimate`, or `unavailable`. Structural similarity estimates are now clearly labeled as `structural_estimate`.

### 9. `experiments/e12_compiler_baseline/run.py` — fixed coupling map

**Problem**: `COUPLING_MAP = CouplingMap.from_heavy_hex(3)` (19 qubits) was hardcoded for all circuits, over-constraining small circuits and unable to fit large ones.

**Fix**:
- Added `_select_coupling_map(n_qubits, heavy_hex_d)` function that dynamically selects the smallest heavy-hex distance that fits the circuit.
- Made coupling map configurable via `--heavy-hex-d` CLI parameter (default 3).
- Updated metadata to record `coupling_map_base_d` and `coupling_map_selection: "dynamic_per_circuit"`.

### 10. `experiments/e13_structural_ceiling/run.py` — negative ceiling_gap

**Problem**: `ceiling_gap = structural_upper_bound_reduction - observed_best_reduction` could be negative when the optimizer exceeded the structural proxy's estimate.

**Fix**:
- Clamped to non-negative: `ceiling_gap = max(0.0, raw_gap)`.
- Added `ceiling_gap_negative` boolean field to flag anomalies where observed reduction exceeded the theoretical upper bound.

### 11. `experiments/e14_extended_benchmark/run.py` — `build_optimizers()` params

**Status**: RESOLVED — partially.

**Reason**: `build_optimizers()` already accepted `window_size` parameter (recon report was inaccurate). The optimizers themselves (`GreedyGateCancellation`, `CommutationRewriter`, `HybridCommuteRewrite`) do not accept `n_qubits` or `gate_set` parameters, so adding those would require modifying the optimizer classes (out of scope).

**Additional improvement**: Added `success_reduction` parameter to `build_optimizers()` to replace the hardcoded `0.01`.

### 12. `experiments/e15_multi_compiler/run.py` — QASM round-trip non-unitary

**Problem**: The Cirq backend converts Qiskit → QASM2 → Cirq → QASM2 → Qiskit. QASM2 round-trip is not unitary-preserving: arbitrary unitary gates must be decomposed, global phase may be lost, and some gate types are unsupported by Cirq's QASM parser.

**Fix**:
- Added detailed WARNING in `_cirq_optimize` docstring explaining the QASM2 round-trip limitation.
- Added `conversion_format` field to all compiler output rows: `native` (Qiskit, t|ket>) or `qasm2_roundtrip` (Cirq).
- Added `conversion_caveat` field to Cirq rows explaining potential unitary loss.

### 13. `experiments/e16_window_scaling/run.py` — missing Phase-1-only baseline

**Problem**: E16 only tested `CommutationRewriter` (Phase-2) and `HybridCommuteRewrite` (Phase-1+2), with no Phase-1-only baseline. Without it, the marginal contribution of Phase-2 window scaling cannot be isolated.

**Fix**: Added `GreedyGateCancellation` as a `phase1_only` baseline optimizer (independent of `window_size`) to the comparison loop.

### 14. `experiments/e20_multi_compiler_full/run.py` — missing custom optimizers

**Problem**: E20 only compared external compilers (Qiskit, Cirq, t|ket>); our custom Phase-1/Phase-2 optimizers were not included.

**Fix**:
- Imported `GreedyGateCancellation`, `CommutationRewriter`, `HybridCommuteRewrite`.
- Added a custom-optimizer section in the per-circuit loop with `compiler="custom"`.
- Updated metadata `compilers_run` to include `"custom"` and updated description.
- Also fixed `_qiskit_transpile` hardcoded `seed_transpiler=42` → passed from `trial_seed`.

### 15. `experiments/e10_phase1_vs_phase2/run_expanded.py` — BV n_qubits + hardcoded angles

**Problem**:
- `make_bernstein_vazirani(n)` correctly uses `n+1` qubits, but results recorded `n_qubits = n` (the parameter) instead of the actual `n+1`.
- `make_qaoa` and `make_vqe_twolocal` used hardcoded angles without documenting that they are fixed-angle benchmarks.

**Fix**:
- Changed `n_qubits` in Part 4 results to `circuit.num_qubits` (actual qubit count). Added `param_n` field to preserve the original parameter for reference.
- Updated `make_bernstein_vazirani` docstring to explicitly state the n+1 qubit convention.
- Updated `make_qaoa` and `make_vqe_twolocal` docstrings to label them as fixed-angle benchmarks and point to `real_benchmarks.py` for parameterized versions.

---

## Files Modified

| File | Lines Changed |
|------|---------------|
| `src/optimisation/base.py` | ~600-625 (_fitness method) |
| `src/optimisation/ceiling_aware.py` | ~145-155 (is_self_inverse_pair tolerance) |
| `src/circuits/real_benchmarks.py` | ~453-493 (rename + docstring), ~555 (call site) |
| `tests/test_core.py` | ~38, ~1153-1158 (import + test) |
| `experiments/e21_ceiling_aware/run.py` | ~47, ~112 (import + call site) |
| `experiments/e15_multi_compiler/run.py` | ~50-63, ~209, ~395, ~250-290, ~360 (seed + QASM warning + conversion_format) |
| `experiments/e18_clifford_t/run.py` | ~113-135 (decompose_error annotation) |
| `experiments/e19_wcl_listing/run.py` | ~49, ~57-66, ~88-89, ~207 (dead code + constants) |
| `experiments/e17_connectivity/run.py` | ~81-95, ~128-150, ~203, ~214 (heavy-hex doc + opt_level + seed + error) |
| `experiments/e11_real_circuit_benchmark/run.py` | ~67-80, ~92 (fidelity_method) |
| `experiments/e12_compiler_baseline/run.py` | ~38-66, ~75-76, ~185-189, ~200-211 (dynamic coupling map) |
| `experiments/e13_structural_ceiling/run.py` | ~50-56, ~81-82 (max(0, gap) + flag) |
| `experiments/e14_extended_benchmark/run.py` | ~42-62 (success_reduction param) |
| `experiments/e16_window_scaling/run.py` | ~30-33, ~63-76, ~123 (Phase-1-only baseline) |
| `experiments/e20_multi_compiler_full/run.py` | ~36-47, ~97-105, ~358, ~577-630 (custom optimizers + seed) |
| `experiments/e10_phase1_vs_phase2/run_expanded.py` | ~68-75, ~89-97, ~110-118, ~305-312 (BV n_qubits + fixed-angle docstrings) |
| `docs/05_supplementary/supplementary_materials.md` | ~597 (function name reference) |
