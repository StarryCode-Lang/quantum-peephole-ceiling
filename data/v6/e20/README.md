# E20: Multi-Compiler Full Comparison — RESULTS GENERATED

**Status**: Full mode executed. `multi_compiler_full.csv` and `metadata.json` have been generated locally. No git commit was made.

**Purpose**: Full multi-compiler comparison of Qiskit (opt_level=3), Cirq (optimize_for_target_gateset + eject_z + merge_single_qubit_gates), and t|ket> (FullPeepholeOptimise) on the extended 15-family benchmark suite, with target qubit counts [4, 6, 8] and 10 trials per cell. This experiment addresses the reviewer concern that E15 only included Qiskit in the multi-compiler comparison. E20 adds Cirq and t|ket> as first-class compiler backends with controlled qubit counts and multiple random trials for statistical robustness.

**How to run safely**: use `python experiments/e20_multi_compiler_full/run.py --mode smoke --n-trials 1 --skip-cirq --skip-tket --max-qubits-fidelity 4` for a tiny Qiskit/custom validation. A fully configured Cirq and pytket environment is required for a confirmatory three-compiler comparison. Missing optional compilers are handled gracefully and recorded in metadata; if Qiskit itself is unavailable, metadata and an empty CSV are written with a blocker field.

**What is committed**:
- `metadata.json` — full experiment specification: compilers, pipeline definitions, circuit parameters, metrics, output file schema.
- Script support for Qiskit, Cirq, t|ket>, and custom optimizers (`greedy_phase1`, `commutation_phase2`, `hybrid_phase1_2`).
- No full-run `multi_compiler_full.csv` should be treated as canonical unless explicitly generated in full mode with compiler availability recorded.

**Manuscript treatment**: The v6 manuscript is corrected to read "Qiskit-only" wherever E15 is invoked as evidence. Cirq and t|ket> numerical values are not reported as confirmed; any projection of their behavior is labeled as pass-mechanism inference, not measurement. See `docs/06_manuscript/limitations_and_future_work.md` §6 (Multi-Compiler Comparison Is Qiskit-Only) and §15.8 (E20: Multi-Compiler Full Comparison future-work item).

**Notes on the generated full run**:
- Custom Phase-1/Phase-2 optimizers were skipped (`--skip-custom`) in the full run to keep the three-compiler comparison tractable.
- t|ket> `FullPeepholeOptimise` was executed only on circuits with `n_qubits <= 6` because the optimiser becomes non-interruptible and can hang on larger instances.
- Cirq was executed only on circuits with `n_qubits <= 8` for the same reason.
- A per-circuit timeout of 60 seconds was enforced for every backend; timeouts are recorded in `compiler_status`.
- Exact average-gate fidelity was computed only for optimized circuits with `n_qubits <= 8` to avoid excessive unitary-simulation cost on heavily expanded circuits.

**References**: `metadata.json` (this directory); `v6_scope_limitations_risks.md` (D-delimitations and reviewer-risk table); `limitations_and_future_work.md` §6 and §15.8.
