# E20 Corrected Rerun (Non-Canonical)

This directory contains a current-code rerun of MC-E20 after fixing two Cirq pipeline defects:

- Cirq 1.6.1 requires `gateset=`, not `target_gateset=`.
- Cirq's OpenQASM 2 export can emit `sx`/`sxdg`; E20 now injects equivalent definitions before Qiskit re-import.

Command:

```text
python experiments/e20_multi_compiler_full/run.py --mode full --skip-custom --output-dir data/v11/e20_corrected --timeout 60 --max-qubits-fidelity 10
```

Result: 1,070 rows across 15 families, with 430 Qiskit, 390 Cirq, and 250 t|ket> rows. All 390 Cirq rows are `ok`; the frozen canonical E20 file has 70 Cirq `sx` import errors. Input hashes match canonical E20 for all 1,070 rows. The corrected gateset step changes Cirq scientific outputs, so this dataset is not silently substituted for canonical evidence. Eight t|ket> rows remain below the exact-fidelity threshold and retain the existing t|ket> correctness caveat.

This rerun is supporting evidence only. It is not listed in `release/release_manifest.json` and does not change `data/v6/e20/multi_compiler_full.csv`.
