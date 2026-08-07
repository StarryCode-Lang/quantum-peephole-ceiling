# E20: Multi-Compiler Full Comparison

**Status**: Canonical full-mode run retained as-executed evidence. The frozen
CSV is listed in `release/release_manifest.json` and contains 1,070 rows.

**Purpose**: Full multi-compiler comparison of Qiskit (opt_level=3), Cirq (optimize_for_target_gateset + eject_z + merge_single_qubit_gates), and t|ket> (FullPeepholeOptimise) on the extended 15-family benchmark suite, with target qubit counts [4, 6, 8] and 10 trials per cell. This experiment addresses the reviewer concern that E15 only included Qiskit in the multi-compiler comparison. E20 adds Cirq and t|ket> as first-class compiler backends with controlled qubit counts and multiple random trials for statistical robustness.

**How to run safely**: use `python experiments/e20_multi_compiler_full/run.py --mode smoke --n-trials 1 --skip-cirq --skip-tket --max-qubits-fidelity 4` for a tiny Qiskit/custom validation. A fully configured Cirq and pytket environment is required for a confirmatory three-compiler comparison. Missing optional compilers are handled gracefully and recorded in metadata; if Qiskit itself is unavailable, metadata and an empty CSV are written with a blocker field.

**Canonical artifacts**:
- `metadata.json` — full experiment specification: compilers, pipeline definitions, circuit parameters, metrics, output file schema.
- Script support for Qiskit, Cirq, t|ket>, and custom optimizers (`greedy_phase1`, `commutation_phase2`, `hybrid_phase1_2`).
- `multi_compiler_full.csv` — canonical as-executed result; Cirq coverage is
  unbalanced because 70/390 Cirq rows retain the historical QASM import error.

**Manuscript treatment**: E20 provides the frozen three-compiler comparison
with its coverage and fidelity caveats. The corrected pipeline uses Cirq 1.6.1
`gateset=` and injects `sx`/`sxdg` OpenQASM definitions. Its 1,070-row rerun is
stored separately under `data/v11/e20_corrected/` and is non-canonical. See
`docs/manuscript/manuscript.md` §6.5 and `docs/analysis/e20_rerun_p13.md`.

**Notes on the generated full run**:
- Custom Phase-1/Phase-2 optimizers were skipped (`--skip-custom`) in the full run to keep the three-compiler comparison tractable.
- t|ket> `FullPeepholeOptimise` was executed only on circuits with `n_qubits <= 6` because the optimiser becomes non-interruptible and can hang on larger instances.
- Cirq was executed only on circuits with `n_qubits <= 8` for the same reason.
- A per-circuit timeout of 60 seconds was enforced for every backend; timeouts are recorded in `compiler_status`.
- Exact average-gate fidelity was computed only for optimized circuits with `n_qubits <= 8` to avoid excessive unitary-simulation cost on heavily expanded circuits.

**References**: `metadata.json` (this directory);
`docs/manuscript/manuscript.md` §6.5 and §7.5;
`docs/review/residual_issue_disposition_2026-08-07.md`;
`docs/analysis/e20_rerun_p13.md`.
