# Q-research: Listing Model Sensitivity and Prototype Action-Space Ceilings in Quantum Circuit Optimization

**Project Version**: 6.0.0  
**Date**: 2026-07-14  
**Target Journal**: Quantum (quantum-journal.org) / ACM TQC / IEEE QCE

---

## Project Overview

This project characterizes the boundaries of quantum circuit peephole optimization across 15 circuit families and 6 optimizer types, with over 67,000 data rows across 27 datasets. The central contribution is the discovery that the circuit listing model (the data-structure ordering of gates) is the key factor governing Phase-1 adjacent-cancellation optimizer behavior.

### Core Scientific Question
> When and why does peephole optimization succeed or fail across diverse circuit families?

### Key Findings (v6.0.0)
1. **Listing Model Sensitivity**: Layer-by-layer listing (LBL) structurally empties the Phase-1 action space for n >= 2 (Observation 1(b)); wire-consecutive listing (WCL) exposes ~7.8% reduction hidden under LBL (E19, 10,000 rows)
2. **Empirical Trichotomy**: CNOT chains achieve 100% Phase-1 reduction; oracle/Clifford circuits yield 14-16% via Phase-2a commutation; 3 of 15 families at genuine structural ceiling (QFT/GHZ/SurfaceCode) + 7 of 15 at prototype action-space ceiling
3. **Prototype vs Production**: Production peephole optimizers (t|ket> FullPeepholeOptimise) achieve 5-63% on 5 of 7 "ceiling" families, confirming the ceiling is prototype-specific, not a structural limit of peephole optimization
4. **Theory-Experiment Validation**: 8 observables cross-validated; Theorem 9 (BV oracle Phase-2b advantage >= n/(4.5n+4)) partially validated via fixture-scale Phase-2b template matching
5. **Ceiling-Aware Optimization (Exploratory)**: 1.6x-228x speedup (mean 35x) with identical reduction on training families; held-out validation failed (MAE=0.2775, Pearson=NaN) -- classified as supplementary observation, not a validated predictive tool
6. **Fidelity Verified**: Optimizations preserve unitary equivalence where exact/scalable checks are available; E18 includes documented decomposition/fidelity-failure rows (44.4% failure rate, survivorship-biased)

---

## Directory Structure

```
Q-research/
├── src/                          # Source code
│   ├── circuits/                 # Circuit generation (v2.1)
│   ├── optimisation/
│   │   ├── base.py              # Base optimizer class
│   │   ├── _gate_predicates.py  # Shared gate predicate functions
│   │   ├── ceiling_aware.py     # Ceiling-aware optimizer
│   │   ├── phase1/              # Phase 1: Adjacent-search optimizers
│   │   │   ├── greedy.py        # GreedyGateCancellation v3.0.0
│   │   │   ├── simulated_annealing.py
│   │   │   ├── genetic_algorithm.py
│   │   │   ├── random_local_search.py
│   │   │   └── wire_traversal.py # WCL preprocessing
│   │   └── phase2/              # Phase 2: Commutation + template matching
│   │       ├── commutation_rewriter.py  # Phase-2a
│   │       └── template_matcher.py      # Phase-2b (fixture-scale)
│   └── provenance.py            # Data provenance tracking
│
├── experiments/                  # Experiment scripts (by ID)
├── data/                         # Data (versioned: v2_fixed through v7)
├── analysis/                     # Analysis scripts, figures, statistics
├── docs/                         # Documentation
│   ├── theory/                  # Theoretical framework + formal results
│   ├── results/                 # Experimental design + analysis summary
│   ├── manuscript/              # Manuscript (v6) + supporting docs
│   ├── supplementary/           # Supplementary materials
│   └── data_dictionary.md       # Canonical data dictionary
├── scripts/                      # Reproduction scripts
├── release/                      # Machine-readable release manifest
├── tests/                        # 268 unit + statistical tests
├── environment.yml              # Conda environment (Python 3.10+)
├── requirements.txt             # Pip requirements
├── Dockerfile                   # Docker container
└── .github/workflows/ci.yml    # CI pipeline
```

---

## Experiment Registry

| ID | Name | Status | Rows | Key Result |
|----|------|--------|------|------------|
| E1 | Phase Transition | COMPLETE | 25,000 | Mean reduction = 0.0000% at all depths 1-50 (LBL) |
| E2 | Entanglement Density | COMPLETE | 2,100 | No correlation with entanglement entropy |
| E3 | Scaling | COMPLETE | 12,000 | Mean reduction = 0.0000% for n = 3-10 |
| E4 | Algorithm Comparison | COMPLETE | 400 | All Phase-1 optimizers converge to ~0% |
| E5 | Landscape | COMPLETE | 6,000 | Flat landscape, rare deep minima (max 26.67%) |
| E10 | Phase 1 vs Phase 2 | COMPLETE | 1,905 | Phase-2a context-dependent advantage |
| E10p2b | Phase-2b Validation | COMPLETE | 1,017 | Fixture-scale Phase-2b template matching |
| E11 | Real-Circuit Benchmark | COMPLETE | 519 | 15 circuit families x 3 optimizers |
| E12 | Compiler Baseline | COMPLETE | 568 | Qiskit transpiler levels 0-3 |
| E13 | Structural Ceiling | COMPLETE | 56 | Prototype action-space ceiling proxy |
| E14 | Extended Benchmark | COMPLETE | 2,130 | 15 circuit families, extended metrics |
| E15 | Compiler Comparison | COMPLETE | 994 | Custom peephole vs Qiskit |
| E16 | Window Scaling | COMPLETE | 696 | Phase-2 window size saturation |
| E17 | Connectivity | COMPLETE | 755 | Linear/grid/heavy-hex topology |
| E18 | Clifford+T | COMPLETE | 270 | Survivorship-biased (44.4% failure) |
| E19 | WCL Listing | COMPLETE | 10,000 | WCL 7.83% vs LBL 0% on random circuits |
| E20 | Multi-Compiler Full | COMPLETE | 1,070 | Qiskit/Cirq/t|ket> on 15 families |
| E21 | Ceiling-Aware | COMPLETE | 1,140 | 1.6x-228x speedup (exploratory) |
| E23 | AG Canonical Form | COMPLETE | 160 | Thm 6: Phase-1 = 0% on AG canonical Clifford |
| E24 | Theorem 7 Hardness | COMPLETE | 75 | Phase-2a reduction = 79.8% (exceeds 1/6 bound) |
| E25 | Industry Benchmarks | COMPLETE | 66 | Industry proxy circuit benchmarks |

**Total**: over 67,000 data rows across 27 datasets.

---

## Statistical Protocol

1. **Multiple Comparison Correction**: Benjamini-Hochberg FDR control (q=0.05)
2. **Effect Size Reporting**: Cliff's delta + Cohen's d + Glass's Delta (for zero-variance comparisons)
3. **Power Analysis**: Target beta > 0.80; underpowered experiments labeled exploratory
4. **Bootstrap CI**: 10,000 resamples with percentile method
5. **Fidelity Distribution**: Full distribution reported (min, 25%, median, 75%, max)
6. **Threshold Sensitivity**: Results reported at theta in {1%, 5%, 10%, 20%}

---

## Known Limitations

> Full details in `docs/manuscript/manuscript.md` Section 6.3 (13 subsections).

Key limitations:
- Trichotomy is empirical observation on 15 pre-selected families, not universal law
- Held-out validation failed (MAE=0.2775, Pearson=NaN) -- ceiling-aware model does not generalize
- Phase-2b template matching validated at fixture scale only; full benchmark pending
- E18 Clifford+T results are survivorship-biased (44.4% failure rate)
- WCL validation (E19) limited to random Universal circuits
- No random gate shuffler control performed
- E04 uses single seed (acknowledged in limitations)

---

## Quick Start

### One-Command Reproduction

```bash
# Verify data integrity (fast, no reruns)
python scripts/reproduce_all.py --verify

# Full reproduction: tests, all experiments, figures, and verification
python scripts/reproduce_all.py --all
```

### Manual Setup

```bash
# Setup environment
conda env create -f environment.yml
conda activate q-research

# Or use pip
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -q

# Run E1 (example)
python experiments/e01_phase_transition/run.py

# Generate figures
python analysis/generate_figures.py
```

### Docker

```bash
docker build -t q-research .
docker run q-research
```

---

## License

MIT License. See `LICENSE` for details.

## Contributors

### Human
- **StarryCode-Lang** -- Conceived the study, designed experiments, implemented optimizers, wrote manuscript, directed all AI-assisted work.

### AI / Agent Assistants
The following AI tools and agent frameworks contributed to code development, review, documentation, and remediation during this project:

- **Claude Code** (Anthropic) -- Code review, refactoring, test generation, academic manuscript editing
- **opencode** (Anomaly) -- Session orchestration, multi-agent task dispatch, integrated review pipeline
- **Codex** (OpenAI) -- Code generation and debugging assistance
- **Hermes** -- Agent infrastructure, skill management, experiment automation
- **QoderWork CN** -- Manuscript polishing, academic paper review skills
- **Trae CN** -- MCP server integration, sequential thinking analysis
- **ZCode** -- CLI plugin support, commit workflow
- **Kimi Code** (Moonshot) -- Literature search, web bridge research
- **Mimocode** -- Configuration management, agent coordination

All AI-generated code was reviewed, tested, and verified by the human authors. AI tools served as assistants; all scientific decisions, claims, and final manuscript content are the responsibility of the human authors.

## Contact

**Data Integrity**: See `src/provenance.py` for the data provenance tracking implementation.  
**Reproducibility**: See `docs/reproducibility.md` for full reproducibility documentation.  
**Release Manifest**: `release/release_manifest.json` contains SHA-256 checksums for all datasets.
