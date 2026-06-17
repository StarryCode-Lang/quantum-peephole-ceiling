# V5 Reproducibility Checklist

> **Version**: 5.0  
> **Date**: 2026-06-10  

## Environment

- Conda environment: `q-research`
- Python: `3.10+ | packaged by conda-forge`
- Platform: `Windows-10`
- Required packages: qiskit, numpy, scipy, pandas
- Optional packages: cirq, pytket (for E15 multi-compiler)

## Commands

### Core tests
- `python -m pytest tests/test_core.py -v`

### Legacy experiments (E1-E5, E10-E13)
- `python scripts/reproduce_all.py --verify`
- `python experiments/e11_real_circuit_benchmark/run.py --mode smoke`
- `python experiments/e12_compiler_baseline/run.py --mode smoke`
- `python experiments/e13_structural_ceiling/run.py --mode smoke`

### New v5 experiments (E14-E18)
- `python experiments/e14_extended_benchmark/run.py --mode smoke`
- `python experiments/e15_multi_compiler/run.py --mode smoke --skip-cirq --skip-tket`
- `python experiments/e16_window_scaling/run.py --mode smoke --window-sizes 2 5 10`
- `python experiments/e17_connectivity/run.py --mode smoke --topologies linear`
- `python experiments/e18_clifford_t/run.py --mode smoke`

### Full production runs
- `python experiments/e14_extended_benchmark/run.py --mode full --window-sizes 2 5 10 20 50`
- `python experiments/e15_multi_compiler/run.py --mode full`
- `python experiments/e16_window_scaling/run.py --mode full`
- `python experiments/e17_connectivity/run.py --mode full`
- `python experiments/e18_clifford_t/run.py --mode full`

## Expected outputs

### Canonical datasets
- Legacy: 9 datasets (E01-E05, E10-E13)
- New v5: 5 datasets (E14-E18)
- Output directory: `data/v5/{e14,e15,e16,e17,e18}/`

### Key metrics per experiment
- **E14**: 15 circuit families x 3 optimizers x multiple window sizes, with extended metrics
- **E15**: Custom optimizers + Qiskit opt levels 0-3 + optional Cirq/t|ket>
- **E16**: Window sizes {2, 5, 10, 20, 50} x 2 Phase 2 optimizers x 15 families
- **E17**: 3 topologies (linear, grid, heavy-hex) x 3 optimizers x 15 families
- **E18**: Clifford+T decomposed circuits x 3 optimizers, with T-count tracking

## Verification tolerances

- Row counts and SHA256 hashes must match the manifest for frozen release validation.
- Mean fidelities for all canonical data should be 1.000000 up to printed precision.
- Extended metrics (depth_reduction, cnot_reduction, two_qubit_reduction) are deterministic for a fixed source tree and seed policy.
- Window-size parameterization (E16) should show monotonically non-decreasing reduction with increasing w.
