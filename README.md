# Q-research: Boundary Characterization of Quantum Circuit Peephole Optimization

**Project Version**: 6.0.0  
**Date**: 2026-07-07  
**Target Journal**: Quantum (quantum-journal.org) / QCE / TQC

---

## Project Overview

This project characterizes the fundamental boundaries of quantum circuit peephole optimization — specifically the structural limits of Phase 1 (adjacent-search) versus Phase 2 (commutation-enabled) optimization methods.

### Core Scientific Question
> What circuit structures CANNOT be optimized by peephole methods, and why?

### Key Findings (v5.0.0)
1. **Structural Ceiling**: Phase 1 optimizers achieve ~0% reduction on random circuits (45,500 trials)
2. **No Phase Transition**: Reduction remains ~0% across all depths (1–50) and qubit counts (3–10)
3. **Phase 2 Context-Dependent Advantage**: Commutation rewriting adds 3.26% on random circuits, 0% on structured brickwork, ~20% on Oracle/BV
4. **Real-Circuit Divergence**: 10 of 15 circuit families at structural ceiling; Qiskit transpiler achieves additional gains beyond prototype peephole scope on selected families
5. **Fidelity Verified with Caveats**: Optimizations preserve unitary equivalence where exact/scalable fidelity checks are available; E18 includes documented decomposition/fidelity-failure rows that are filtered in analysis

---

## Directory Structure

```
Q-research/
├── src/                          # Source code
│   ├── circuits/                 # Circuit generation (v2.1)
│   ├── optimisation/
│   │   ├── base.py              # Base optimizer class
│   │   ├── phase1/              # Phase 1: Adjacent-search optimizers
│   │   │   ├── greedy.py        # GreedyGateCancellation v3.0.0 (bug-fixed)
│   │   │   ├── simulated_annealing.py
│   │   │   ├── genetic_algorithm.py
│   │   │   └── random_local_search.py
│   │   └── phase2/              # Phase 2: Commutation-based optimizers
│   │       └── commutation_rewriter.py
│   └── provenance.py            # Data provenance tracking
│
├── experiments/                  # Experiment scripts (by ID)
│   ├── e01_phase_transition/    # E1: Phase transition test (25,000 trials)
│   ├── e02_entanglement_density/  # E2: Entanglement density sweep (2,100 trials)
│   ├── e03_scaling/              # E3: Scaling analysis (12,000 trials)
│   ├── e04_algorithm_comparison/ # E4: Algorithm comparison (400 trials)
│   ├── e05_landscape/            # E5: Landscape characterization (6,000 trials)
│   ├── e10_phase1_vs_phase2/     # E10: Phase 1 vs Phase 2 (1,905 canonical rows)
│   ├── e11_real_circuit_benchmark/  # E11: Real-circuit optimizer benchmark (426 trials)
│   ├── e12_compiler_baseline/       # E12: Qiskit compiler baseline (568 trials)
│   ├── e13_structural_ceiling/      # E13: Structural ceiling analysis (56 trials)
│   ├── e14_extended_benchmark/      # E14: Extended benchmark (2,130 trials)
│   ├── e15_multi_compiler/          # E15: Compiler comparison (994 trials)
│   ├── e16_window_scaling/          # E16: Window scaling (696 trials)
│   ├── e17_connectivity/            # E17: Topology constraints (755 trials)
│   └── e18_clifford_t/              # E18: Clifford+T decomposition (270 trials)
│
├── data/                         # Data (versioned)
│   ├── v2_fixed/                # Re-run with fixed Greedy v3.0.0 (E1–E5)
│   ├── v3_extended/             # New experiments (E10)
│   ├── v4/                      # Real-circuit, compiler-baseline, and ceiling outputs (E11–E13)
│   ├── v5/                      # Extended benchmark suite (E10 expanded, E14–E18)
│   └── v6/                      # Preliminary/planned artifacts (E19/E20/E21; not core canonical)
│
├── analysis/                     # Analysis scripts and figures
│   ├── figures/                  # Generated analysis figures (17 vector PDF figures)
│   ├── generate_figures.py       # Figure generation script
│   ├── final_report.md           # Comprehensive experimental report
│   ├── structural_ceiling.py      # Action-space / ceiling analysis utilities
│   ├── finite_size_scaling.py     # Finite-size scaling analysis
│   ├── phase1_statistics/        # Statistical methods toolkit
│   └── phase2_threshold_sensitivity/  # Threshold sensitivity analysis
│
├── docs/                         # Documentation
│   ├── theory/                  # Theoretical framework (definitions, theorems, conjectures, complexity)
│   ├── results/                 # Results documentation (experimental design, analysis summary)
│   ├── references/              # Literature review and unified references
│   ├── manuscript/              # Manuscript and appendix (claims, scope, limitations)
│   ├── supplementary/           # Supplementary materials for manuscript
│   ├── archive/                 # Historical documentation (audit reports, checklists)
│   ├── data_dictionary.md       # Canonical data dictionary
│   ├── 07_optimization_plan.md  # Top-conference submission optimization plan
│   └── 07_optimization_tasks.csv# Executable task list
│
├── scripts/                      # One-command reproduction scripts
│   ├── reproduce_all.py         # Full reproduction pipeline
│   └── generate_release_manifest.py
│
├── release/                      # Machine-readable release manifest
├── environment.yml              # Conda environment specification
├── requirements.txt             # Pip requirements
│
├── logs/                         # Experiment execution logs
├── tests/                        # Core and statistical tests
```

---

## Data Versioning Policy

| Version | Description | Status | Location |
|---------|-------------|--------|----------|
| v1 | Original data (buggy `_are_inverse()`) | ARCHIVED | `archive/old_data/` |
| v2 | Re-run with fixed Greedy v3.0.0 | **ACTIVE** | `data/v2_fixed/` |
| v3 | New experiments (E10) | **ACTIVE** | `data/v3_extended/` |
| v4 | Real-circuit, compiler, ceiling (E11–E13) | **ACTIVE** | `data/v4/` |
| v5 | Extended benchmark suite (E10 expanded, E14–E18) | **ACTIVE** | `data/v5/` |

**Critical Note**: E1–E5 originally used a buggy Greedy optimizer where `_are_inverse()` did not check qubit matching. This was fixed in v3.0.0. All v1 data is archived in `archive/old_data/` for transparency.

---

## Experiment Registry

| ID | Name | Status | Trials | Data Version | Key Result |
|----|------|--------|--------|--------------|------------|
| E1 | Phase Transition | **COMPLETE** | 25,000 | v2 | Mean reduction = 0.0000% at all depths 1–50 |
| E2 | Entanglement Density | **COMPLETE** | 2,100 | v2 | No correlation with entanglement entropy |
| E3 | Scaling | **COMPLETE** | 12,000 | v2 | Mean reduction = 0.0000% for n = 3–10 |
| E4 | Algorithm Comparison | **COMPLETE** | 400 | v2 | All optimizers (Greedy/RLS/SA/GA) ~0% |
| E5 | Landscape | **COMPLETE** | 6,000 | v2 | Flat landscape, rare deep minima (max 26.67%) |
| E10 | Phase 1 vs Phase 2 | **COMPLETE** | 1,905 | v5 | Expanded Phase 1/Phase 2 comparison; supersedes 819-row intermediate run |
| E11 | Real-Circuit Benchmark | **COMPLETE** | 426 | v4 | 15 circuit families × 3 optimizers |
| E12 | Compiler Baseline | **COMPLETE** | 568 | v4 | Qiskit transpiler levels 0–3, all distinct |
| E13 | Structural Ceiling | **COMPLETE** | 56 | v4 | Action-space and local commutation ceiling estimates |
| E14 | Extended Benchmark | **COMPLETE** | 2,130 | v5 | 15 circuit families, extended metrics |
| E15 | Compiler Comparison | **COMPLETE** | 994 | v5 | Custom peephole vs Qiskit transpiler (Cirq/t\|ket> pending — see L8) |
| E16 | Window Scaling | **COMPLETE** | 696 | v5 | Phase-2 window size saturation curves |
| E17 | Connectivity | **COMPLETE** | 755 | v5 | Linear/grid/heavy-hex topology constraints |
| E18 | Clifford+T | **COMPLETE** | 270 | v5 | Fault-tolerant gate-set decomposition |

**Total Canonical Optimizer Trials (E1-E18)**: 53,300. Including held-out validation and Qiskit pass-isolation artifacts: 53,525 rows.

---

## Statistical Protocol (v3.0.0)

1. **Multiple Comparison Correction**: Benjamini-Hochberg FDR control across all experiments
2. **Effect Size Reporting**: Cliff's delta + Cohen's d for all pairwise comparisons
3. **Power Analysis**: Target β > 0.80 for all primary hypotheses
4. **Bootstrap CI**: 10,000 resamples with convergence diagnostics
5. **Fidelity Distribution**: Full distribution reported (min, 25%, median, 75%, max)
6. **Threshold Sensitivity**: All results reported at θ ∈ {1%, 5%, 10%, 20%}

---

## Known Limitations

> **Added 2026-06-11.** For full details, see `docs/results/experimental_design.md` Section 12.

The following limitations should be considered when interpreting results:

| ID | Experiment | Limitation | Severity |
|----|-----------|------------|----------|
| L1 | E10 | N=9 per real-circuit condition (exploratory only) | Medium |
| L2 | E12 | L1/L2/L3 degeneracy when transpiling without backend coupling map | Low |
| L3 | E15 | Cirq and t\|ket> not included in E15 data — comparison is custom vs Qiskit only | High |
| L5 | E18 | ~60% circuit family decomposition failures to Clifford+T | Medium |
| L6 | E3/E11/E18 | 83 total rows with failed fidelity calculation (0.17%) excluded from analysis | Low |
| L7 | All | Random circuits: structural ceiling ~0% (worst-case benchmarks) | Low |
| L8 | E15 | Multi-compiler comparison currently includes only Qiskit + custom; Cirq and t\|ket> not yet tested | High |

**Theoretical corrections (2026-06-11):**
- Proposition 1 (Phase-1 conflict resolution) was corrected: the problem is polynomial-time solvable via maximum matching, not NP-complete as previously claimed.
- Theorem 6 was renamed to reflect its actual scope (Aaronson-Gottesman canonical form for Clifford circuits).
- Supplementary S8.3 was rewritten to remove an invalid connection between peephole optimization and quantum supremacy.

---

## Quick Start

### Option 1: One-Command Reproduction (Recommended)

```bash
# Full reproduction: tests, all experiments, figures, and verification
python scripts/reproduce_all.py --all

# Or run individual components
python scripts/reproduce_all.py --tests --experiments E1 E10 --figures --verify
```

### Option 2: Manual Setup

```bash
# Setup environment
conda env create -f environment.yml
conda activate q-research

# Or use pip
pip install -r requirements.txt

# Run unit tests
python tests/test_core.py

# Run E1 (example)
python experiments/e01_phase_transition/run.py

# Generate figures
python analysis/generate_figures.py

# Verify existing data integrity only (does not rerun experiments)
python scripts/reproduce_all.py --verify

# Run quick smoke benchmarks in the q-research conda env
conda run -n q-research python experiments/e11_real_circuit_benchmark/run.py --mode smoke
conda run -n q-research python experiments/e12_compiler_baseline/run.py --mode smoke
conda run -n q-research python experiments/e13_structural_ceiling/run.py --mode smoke
conda run -n q-research python scripts/generate_release_manifest.py
```

---

## Contact & Attribution

This project aims to provide a reproducible empirical study. Data, code, and analysis scripts are organized for auditability and future manuscript preparation.

**Data Integrity Contact**: See `src/provenance.py` for the data provenance tracking implementation.
