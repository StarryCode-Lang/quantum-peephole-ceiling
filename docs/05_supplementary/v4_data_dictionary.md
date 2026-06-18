> **DEPRECATED**: This data dictionary is superseded. See
> `docs/data_dictionary.md` for the authoritative version. This file is
> retained in `05_supplementary/` for historical reference only; do not
> cite it as the current data dictionary. All column definitions from this
> document have been merged into `docs/data_dictionary.md`.

# V5 Data Dictionary

> **Version**: 5.0  
> **Date**: 2026-06-10  

> **NOTE: Where this document differs from `docs/data_dictionary.md`, the project-level document takes precedence. Key differences are noted inline.**

> **Note**: This is the publication supplementary version of the data dictionary. For the authoritative project-level data dictionary, see `docs/data_dictionary.md`. Both documents share the same column definitions; where they differ, the project-level document takes precedence.

The release uses three schema families: `legacy_v2_v3` for E1-E5/E10, `results_v1` for E11-E13, and `results_v2` for E14-E18. Reduction values are proportions unless the column name ends in `_pct`.

## Core columns (all schemas)

| Column | Type | Schema | Meaning |
|---|---|---|---|
| schema_version | string | all | Schema version for the row. |
| experiment_id | string | all | Experiment identifier, e.g. E14. |
| run_id | string | results_v1/v2 | Unique run identifier. |
| circuit_id | string | results_v1/v2 | Stable circuit instance identifier. |
| circuit_family | string | results_v1/v2 | High-level family such as QFT, Oracle, VQE, IQP, Grover. |
| circuit_type | string | results_v1/v2 | Fine-grained circuit type. |
| n_qubits | int | all | Number of qubits. |
| depth | int | all | Circuit depth before optimization. |
| gate_count_total | int | results_v1/v2 | Input total gate count. **[diff]** The project-level `docs/data_dictionary.md` uses `original_size` for this column. |
| baseline_gate_count | int | results_v1/v2 | Gate count before optimizer/compiler under comparison. **[diff]** The project-level `docs/data_dictionary.md` uses `original_size` for the equivalent concept. |
| optimized_gate_count | int | results_v1/v2 | Gate count after optimizer/compiler. |
| reduction | float | all | Proportion in [0,1], defined as 1 - optimized/baseline. |
| reduction_pct | float | results_v1/v2 | Percent reduction, 100 * reduction. |
| fidelity | float | all | Average gate fidelity when exact unitary comparison is feasible. |
| success | bool | all | Binary success flag: `reduction >= 0.20 AND fidelity >= 0.99`. **[diff]** Not defined in earlier versions of this document; the project-level `docs/data_dictionary.md` is authoritative for this column's semantics. |
| runtime_seconds | float | all | Wall-clock runtime in seconds. |
| optimizer | string | results_v1/v2 | Optimizer name. |
| input_circuit_sha256 | hex | results_v1/v2 | Stable hash of input circuit instruction stream. |
| output_circuit_sha256 | hex | results_v1/v2 | Stable hash of output circuit instruction stream. |

## Extended metrics (results_v2, E14-E18) — P9

| Column | Type | Meaning |
|---|---|---|
| depth_reduction | float | Proportion reduction in circuit depth. |
| optimized_depth | int | Circuit depth after optimization. |
| two_qubit_reduction | float | Proportion reduction in two-qubit gate count. |
| optimized_2q_gates | int | Two-qubit gate count after optimization. |
| cnot_reduction | float | Proportion reduction in CNOT gate count. |
| optimized_cnot_count | int | CNOT gate count after optimization. |

## Window-size column (E14, E16) — P6

| Column | Type | Meaning |
|---|---|---|
| window_size | int | Phase 2 commutation search window size. |

## Multi-compiler columns (E15) — P3

| Column | Type | Meaning |
|---|---|---|
| compiler | string | Compiler name: custom, qiskit, cirq, or tket. |
| compiler_backend | string | Specific backend: transpiler, built_in_optimizers, FullPeepholeOptimise. |
| compiler_opt_level | int/string | Optimization level (0-3 for Qiskit, default for others). |
| compiler_status | string | Status: ok or error message. |

## Topology columns (E17) — P5

| Column | Type | Meaning |
|---|---|---|
| topology | string | Hardware topology: linear, grid, heavy_hex. |
| n_edges | int | Number of edges in the coupling map. |
| status | string | ok or error description. |

## Clifford+T columns (E18) — P10

| Column | Type | Meaning |
|---|---|---|
| gate_set | string | Gate set used: clifford_t. |
| baseline_t_count | int | T+Tdg gate count before optimization. |
| optimized_t_count | int | T+Tdg gate count after optimization. |
| t_count_reduction | float | Proportion reduction in T-count. |

## Structural ceiling proxy (E13, legacy)

| Column | Type | Meaning |
|---|---|---|
| structural_upper_bound_reduction | float | Local structural ceiling proxy as a proportion. |
| observed_best_reduction | float | Best observed prototype reduction for the same circuit. |
