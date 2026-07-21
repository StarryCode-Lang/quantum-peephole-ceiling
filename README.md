# Q-research: Listing Model Sensitivity and Prototype Action-Space Ceilings in Quantum Circuit Optimization

**Project Version**: 9.0.0  
**Date**: 2026-07-21  
**Release ID**: q-research-9.0.0-wave5  

---

## Project Overview

This project characterizes the boundaries of quantum circuit peephole optimization across 15 circuit families and 6 optimizer types, with 82,721 data rows across 36 canonical datasets. The central contribution is the discovery that the circuit listing model (the data-structure ordering of gates) is the key factor governing Phase-1 adjacent-cancellation optimizer behavior.

### Core Scientific Question
> When and why does peephole optimization succeed or fail across diverse circuit families?

### Key Findings (v6.0.0)
1. **Listing Model Sensitivity**: Layer-by-layer listing (LBL) structurally empties the Phase-1 action space for n >= 2 (Observation 1(b)); wire-consecutive listing (WCL) exposes ~7.8% reduction hidden under LBL (E19, 10,000 rows)
2. **Empirical Trichotomy**: CNOT chains achieve 100% Phase-1 reduction; oracle/Clifford circuits yield 14-16% via Phase-2a commutation; 3 of 15 families at genuine structural ceiling (QFT/GHZ/SurfaceCode) + 7 of 15 at prototype action-space ceiling
3. **Prototype vs Production**: Production peephole optimizers (t|ket> FullPeepholeOptimise) achieve 5-63% on 5 of 7 "ceiling" families, confirming the ceiling is prototype-specific, not a structural limit of peephole optimization
4. **Theory-Experiment Validation**: 8 observables cross-validated; Theorem 9 (BV oracle Phase-2b advantage >= n/(4.5n+4)) validated at full scale: Phase-2b v2 reaches the exact k+2 optimum on all 80 BV instances, exceeding the rigorous bound by 3.1-4.2×; IQP 92.0%, Structured 40.2%, RandomClifford 51.6% mean reduction
5. **Ceiling-Aware Optimization (Exploratory)**: 1.6x-228x speedup (aggregate 34.97×) with bitwise-identical reduction on the 15 training families; the original heuristic predictor failed held-out validation (MAE=0.2775, Pearson=NaN), but a repaired hybrid model (mechanism gate + random forest) reaches LOFO MAE 0.0172 [0.0129, 0.0218], pooled r=0.977 -- the gate was selected post hoc on a single dataset, so this is not a validated off-the-shelf predictor (family-mean prediction remains underpowered at n=15 folds; wave-6 20-family robustness: pooled MAE 0.0188, r=0.967, family-mean r=0.780 pure-RF / 0.887 gated, but a RepetitionCode fold failure — MAE 0.303, r=-0.826 — marks the generalization boundary for unseen intermediate-density mechanisms)
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
│   │       └── template_matcher.py      # Phase-2b (full-scale v2)
│   └── provenance.py            # Data provenance tracking
│
├── experiments/                  # Experiment scripts (by ID)
├── data/                         # Data (versioned: v2_fixed through v8)
├── analysis/                     # Analysis scripts, figures, statistics
├── docs/                         # Documentation
│   ├── theory/                  # Theoretical framework + formal results
│   ├── results/                 # Experimental design + analysis summary
│   ├── manuscript/              # Manuscript (active draft) + supporting docs
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
| E22 | Gate Shuffle Ablation | COMPLETE | 2,240 | Shuffle 10.34% > original 6.30% (counterintuitive) |
| E26 | BV Theory Validation | COMPLETE | 4 | Thm 9 bound exceeded 3.1-4.2× on BV n=3..10 |
| E29 | Multi-Seed E04 | COMPLETE | 800 | E04 single-seed estimates not reproduced (RLS -176.5%) |
| E10p2b-v2 | Phase-2b Full v2 | COMPLETE | 2,427 | Full-scale Phase-2b; full-factorial depth grid (56/56, wave 6); pooled reduction 48.5% (95% CI [46.5, 50.5]) |
| EHW | Hardware Validation (noise-model) | COMPLETE | 288 | Noise-model only, NOT real hardware; BV 46.15% logical -> 0% physical L1 |

**Total**: 82,721 data rows across 36 canonical datasets (see `release/release_manifest.json` and `data/DATA_CANONICAL.md` for the exact per-dataset counts).

---

## Statistical Protocol

1. **Multiple Comparison Correction**: Benjamini-Hochberg FDR control (q=0.05)
2. **Effect Size Reporting**: Cliff's delta + Hedges' g (small-sample-corrected Cohen's d) + Glass's Delta; Cliff's delta is the primary metric for near-zero-variance comparisons where parametric effect sizes are undefined
3. **Power Analysis**: Target beta > 0.80; underpowered experiments labeled exploratory
4. **Bootstrap CI**: 10,000 resamples with percentile method
5. **Fidelity Distribution**: Full distribution reported (min, 25%, median, 75%, max)
6. **Threshold Sensitivity**: Results reported at theta in {1%, 5%, 10%, 20%}

---

## Known Limitations

> Full details in `docs/manuscript/manuscript.md` Section 7.5 (20 items).

Key limitations:
- Trichotomy is empirical observation on 15 pre-selected families, not universal law
- Held-out generalization: the original heuristic ceiling-aware model failed (MAE=0.2775, Pearson=NaN); the repaired hybrid model (mechanism gate + random forest) generalizes strongly per-circuit (LOFO MAE 0.0172 [0.0129, 0.0218], pooled r=0.977; gate selected post hoc) but family-mean prediction remains underpowered at n=15 folds (r=0.059; wave-6 20-family check: r=0.780 pure-RF / 0.887 gated, with a RepetitionCode fold failure MAE 0.303 / r=-0.826 as the generalization boundary)
- Phase-2b v2 full-scale validation complete (2,427 rows; BV/IQP/Structured/RandomClifford exceed 30% mean reduction; depth grid closed to the full factorial, 56/56 combos, wave 6); residual limitation: no parity-gadget phase-polynomial templates (QAOA/VQE/HardwareEfficient remain 0%)
- E18 Clifford+T results are survivorship-biased (44.4% failure rate)
- WCL cross-family validation (E19-extended, 960 rows): 7 of 16 families show WCL advantage > 0 (BV +30.8pp, RandomClifford +22.3pp, Structured +12.9pp, UCCSD +10.7pp, IQP +7.2pp, Universal +6.8pp, Grover +3.7pp); the other 9 show no WCL benefit (including CNOT, saturated at 100% under both listings)
- Gate-shuffler control (E22) complete -- counterintuitive: shuffled circuits yield higher greedy Phase-1 reduction than original (10.3% vs 6.3%)
- E04 single-seed results failed E29 ten-seed replication (RLS -176.5%, SA -22.1%, GA -8.3%); E04 conclusions must be qualified as seed/config fragile
- t|ket> RandomClifford correctness caveat: 14 of 30 SOTA outputs fail exact-unitary fidelity verification (see Appendix E)
- Listing-sensitivity coverage complete (wave 6): 15/15 families, 6,652 rows, 168 combos; production compilers 0/126 sensitive, prototype 15/42 (6 sensitive families incl. UCCSD_inspired); honest gap: qwalk_8 has only 3/20 variants and its 12 rows skip the exact unitary check
- Rerun reconciliation (wave 6): 8 experiments rerun under current code (E12-E17, E19, E21) and reconciled; canonical retained for all; IQP commutation/hybrid reductions in canonical E14/E15/E16/E21 are systematically conservative under the strengthened commutation predicate (optimizer-capability enhancement, not a data error); E18/E20 not rerun (budget)

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

## Contact

**Data Integrity**: See `src/provenance.py` for the data provenance tracking implementation.  
**Reproducibility**: See `docs/reproducibility.md` for full reproducibility documentation.  
**Release Manifest**: `release/release_manifest.json` contains SHA-256 checksums for all datasets.
