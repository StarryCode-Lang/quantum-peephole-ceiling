# P13 E20 Rerun Reconciliation

## Finding

P13 is real. Frozen `data/v6/e20/multi_compiler_full.csv` contains 70 Cirq error rows caused by the old `target_gateset=` call and missing `sx`/`sxdg` OpenQASM definitions. The old dataset is valid as an as-executed historical record, but it is not a balanced corrected three-compiler run.

## Fix

`experiments/e20_multi_compiler_full/run.py` now:

- uses Cirq 1.6.1's `gateset=` keyword;
- injects standard OpenQASM 2 `sx`/`sxdg` definitions exactly once;
- accepts `--output-dir`, preventing corrected reruns from overwriting canonical evidence.

## Rerun evidence

The full rerun is stored in `data/v11/e20_corrected/`:

- 1,070 rows, same input hashes as canonical E20;
- 430 Qiskit, 390 Cirq, 250 t|ket> rows;
- 390/390 Cirq rows are `ok`, compared with 320/390 successful canonical Cirq rows;
- corrected Cirq outputs differ on 390 rows because the target-gateset pass now runs, so canonical reduction numbers are not overwritten;
- t|ket> retains 8 rows below the exact-fidelity threshold and remains caveated.

Canonical release status remains unchanged until a deliberate evidence-version decision compares the corrected pipeline against the frozen SOTA dataset.
