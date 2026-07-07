# Q-Research Project Summary

**Generated**: 2026-06-14
**Release**: q-research-v5-final-20260614
**Git Commit**: 17569bd (dirty)
**Environment**: q-research (Python 3.10, qiskit 2.4.1)

---

## Experiments Overview

| Experiment | Records | Circuit Families | Mean Reduction | Best Optimizer | Data Version |
|-----------|--------|------------------|----------------|----------------|--------------|
| E1 Phase Transition | 25,000 | Universal (random) | 0.00% | N/A | v2_fixed |
| E2 Entanglement Density | 2,100 | Universal (random) | 0.00% | N/A | v2_fixed |
| E3 Scaling | 12,000 | Universal (random) | 0.00% | N/A | v2_fixed |
| E4 Algorithm Comparison | 400 | Universal (random) | 0.67% | GA | v2_fixed |
| E5 Landscape | 6,000 | Universal (random) | 0.22% | N/A | v2_fixed |
| E10 Phase 1 vs Phase 2 | 1,905 | 5 families | 2.00% | Hybrid | v5 |
| **E11 Real-Circuit Benchmark** | **426** | **15 families** | **11.48%** | **Hybrid** | **v4** |
| **E12 Compiler Baseline** | **568** | **15 families** | **varies** | **Qiskit O3** | **v4** |
| **E13 Structural Ceiling** | **56** | **7 families** | **N/A** | **N/A** | **v4** |
| **E14 Extended Benchmark** | **2,130** | **15 families** | **varies** | **Hybrid** | **v5** |
| **E15 Compiler Comparison** | **994** | **15 families** | **varies** | **Qiskit O3** | **v5** |
| **E16 Window Scaling** | **696** | **15 families** | **varies** | **Hybrid** | **v5** |
| **E17 Connectivity** | **755** | **15 families** | **varies** | **Hybrid** | **v5** |
| **E18 Clifford+T** | **270** | **~6 families*** | **varies** | **Hybrid** | **v5** |

**Total Canonical Optimizer Records (E1-E18)**: 53,300. Including E19 (WCL/LBL listing comparison, 10,000 rows), held-out validation, and Qiskit pass-isolation artifacts: 63,525 rows.

*E18: ~60% of families fail Clifford+T decomposition.

> **Important**: E15 currently compares custom peephole optimizers against Qiskit only. Cirq and t|ket> comparison is pending (see Limitation L8).

---

## Key Findings

### Random Circuits (E1-E5)
- Phase-1 optimizers achieve ~0% reduction on random circuits
- Structural ceiling is empty: adjacent inverse pairs are rare
- No phase transition observed across depths 1-50

### Real Circuits (E11)
| Family | Our Best | Qiskit O3 | Ceiling | Gap |
|--------|----------|-----------|---------|-----|
| CNOT chain | 100.00% | 100.00% | 100.00% | 0.00% |
| GHZ | 0.00% | 0.00% | 0.00% | 0.00% |
| QFT | 0.00% | 0.00% | 0.00% | 0.00% |
| QAOA | 0.00% | 0.00% | 0.00% | 0.00% |
| Oracle (BV) | 20.54% | 43.86% | 20.54% | -23.32% |
| VQE | 0.00% | 39.27% | 0.00% | -39.27% |
| HardwareEfficient | 0.00% | 35.47% | 0.00% | -35.47% |

**Critical Insight**: Our peephole optimizers hit the structural ceiling on CNOT, GHZ, QFT, QAOA, VQE, and HardwareEfficient circuits. Qiskit transpiler outperforms us on Oracle, VQE, and HardwareEfficient by 20-40 percentage points, indicating that our commutation window and gate-set coverage are narrower than a production compiler.

---

## File Structure

```
Q-research/
├── src/
│   ├── circuits/
│   │   ├── generator_v2.py          # Random circuit families
│   │   └── real_benchmarks.py       # Real/algorithm circuits
│   ├── optimisation/
│   │   ├── base.py                  # Abstract base, move primitives
│   │   ├── phase1/
│   │   │   ├── greedy.py
│   │   │   ├── random_local_search.py
│   │   │   ├── simulated_annealing.py
│   │   │   └── genetic_algorithm.py
│   │   └── phase2/
│   │       └── commutation_rewriter.py
│   └── provenance.py                # Metadata, hashes, env capture
├── experiments/
│   ├── e01-e05/                     # Random circuit experiments
│   ├── e10/                         # Phase 1 vs Phase 2
│   ├── e11-e13/                     # Real-circuit, compiler, ceiling (v4)
│   └── e14-e18/                     # Extended benchmark suite (v5)
├── analysis/
│   ├── figures/                     # 17 generated analysis figures
│   ├── generate_figures.py
│   ├── structural_ceiling.py
│   └── phase1_statistics/           # Statistical methods toolkit
├── scripts/
│   ├── reproduce_all.py
│   ├── generate_release_manifest.py
│   └── unified_analysis.py
├── release/
│   └── release_manifest.json        # Machine-readable manifest
├── data/
│   ├── v2_fixed/                    # E1-E5
│   ├── v3_extended/                 # E10
│   ├── v4/                          # E11-E13
│   └── v5/                          # E14-E18
├── docs/                            # Theory, results, manuscript
└── tests/
    └── test_core.py                 # core unit/integration tests
```

---

## Reproduction Entry Points

```bash
# Unit tests
conda run -n q-research python tests/test_core.py

# Data verification (canonical datasets only)
conda run -n q-research python scripts/reproduce_all.py --verify

# Smoke benchmarks
conda run -n q-research python experiments/e11_real_circuit_benchmark/run.py --mode smoke
conda run -n q-research python experiments/e12_compiler_baseline/run.py --mode smoke
conda run -n q-research python experiments/e13_structural_ceiling/run.py --mode smoke

# Full benchmarks
conda run -n q-research python experiments/e11_real_circuit_benchmark/run.py --mode full
conda run -n q-research python experiments/e12_compiler_baseline/run.py --mode full
conda run -n q-research python experiments/e13_structural_ceiling/run.py --mode full
conda run -n q-research python experiments/e14_extended_benchmark/run.py --mode full
conda run -n q-research python experiments/e15_multi_compiler/run.py --mode full
conda run -n q-research python experiments/e16_window_scaling/run.py --mode full
conda run -n q-research python experiments/e17_connectivity/run.py --mode full
conda run -n q-research python experiments/e18_clifford_t/run.py --mode full

# Analysis and manifest
conda run -n q-research python analysis/generate_figures.py
conda run -n q-research python scripts/unified_analysis.py
conda run -n q-research python scripts/generate_release_manifest.py
```

---

## Quality Checklist

- [x] All 149 unit tests pass
- [x] All canonical datasets verify successfully (E1-E18)
- [x] Release manifest generated with SHA256 checksums
- [x] Environment versions pinned (requirements.txt, environment.yml)
- [x] Source code has type hints and docstrings
- [x] No hardcoded absolute paths in active scripts
- [x] Random seeds are recorded per row
- [x] Fidelity is computed exactly for n <= 10
- [x] Compiler baseline (Qiskit) included
- [x] Structural ceiling analysis included
- [x] Theory documents updated to match current data
- [x] README updated with new experiments and entry points
